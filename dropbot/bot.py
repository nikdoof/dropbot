from xml.etree import ElementTree

from sleekxmpp import ClientXMPP
from redis import Redis
import requests
from humanize import intcomma
import pkgutil
from json import loads as base_loads
from random import choice


class DropBot(ClientXMPP):
    def __init__(self, **kwargs):
        print kwargs
        self.rooms = kwargs.pop('rooms', [])
        self.nickname = kwargs.pop('nickname', 'Dropbot')
        self.cmd_prefix = kwargs.pop('cmd_prefix', '!')
        super(DropBot, self).__init__(**kwargs)
        self.redis_conn = Redis()

        self.register_plugin('xep_0030')  # Service Discovery
        self.register_plugin('xep_0045')  # Multi-User Chat
        self.register_plugin('xep_0199')  # XMPP Ping

        # Handlers
        self.add_event_handler('session_start', self.handle_session_start)
        self.add_event_handler('groupchat_message', self.handle_muc_message)
        self.add_event_handler('message', self.handle_private_message)

    # Reference Data

    @property
    def types(self):
        if not hasattr(self, '_types'):
            data = pkgutil.get_data('dropbot', 'data/types.json')
            self._types = base_loads(data)
        return self._types


    # Command / Connection Handling

    def handle_session_start(self, event):
        self.get_roster()
        self.send_presence()

        # Join the defined MUC rooms
        for room in self.rooms:
            self.plugin['xep_0045'].joinMUC(room, self.nickname, wait=True)

    def handle_muc_message(self, msg):
        if msg['mucnick'] == self.nickname or msg['body'][0] != self.cmd_prefix:
            return
        args = msg['body'].split(' ')
        cmd = args[0][1:].lower()
        args.pop(0)

        # Call the command
        if hasattr(self, 'cmd_%s' % cmd):
            resp = getattr(self, 'cmd_%s' % cmd)(args, msg)
            if resp:
                if isinstance(resp, tuple) and len(resp) == 2:
                    bdy, html = resp
                else:
                    bdy, html = resp, None
                self.send_message(msg['from'].bare, mbody=bdy, mhtml=html, mtype='groupchat')

    def handle_private_message(self, msg):
        if msg['type'] == 'groupchat':
            return
        args = msg['body'].split(' ')
        cmd = args[0].lower()
        args.pop(0)

        # Call the command
        if hasattr(self, 'cmd_%s' % cmd):
            resp = getattr(self, 'cmd_%s' % cmd)(args, msg)
            if resp:
                if isinstance(resp, tuple) and len(resp) == 2:
                    bdy, html = resp
                else:
                    bdy, html = resp, None
                self.send_message(msg['from'], mbody=bdy, mhtml=html, mtype=msg['type'])

    # Commands

    def cmd_jita(self, args, msg):
        item = ' '.join(args)
        if item.strip() == '':
            return 'Usage: !jita <item>'
        if item.lower() == 'plex':
            item = '30 Day'
        types = dict([(i, v) for i, v in self.types.iteritems() if item.lower() in v.lower()])
        if len(types) > 1:
            for i, v in types.iteritems():
                if item.lower() == v.lower():
                    typeid, name = i, v
                    break
            else:
                if len(types) > 10:
                    return "More than 10 items found, please narrow down what you want."
                return "Did you mean: {}?".format(
                    ', '.join(types.itervalues())
                )
        else:
            typeid, name = types.popitem()

        try:
            resp = requests.get('http://api.eve-central.com/api/marketstat?typeid={}&usesystem=30000142'.format(typeid))
            root = ElementTree.fromstring(resp.content)
        except:
            return "An error occured tying to get the price for {}".format(name)

        return "{} | Sell: {} | Buy: {}".format(
            name,
            intcomma(float(root.findall("./marketstat/type[@id='{}']/sell/min".format(typeid))[0].text)),
            intcomma(float(root.findall("./marketstat/type[@id='{}']/buy/max".format(typeid))[0].text)),
        )

    def cmd_redditimg(self, args, msg):
        """Shows a random picture from imgur.com reddit section"""
        if len(args) == 0:
            return "Usage: !redditimg <subreddit>"
        imgs = []
        page = choice(xrange(0, 100))
        for img in requests.get("http://imgur.com/r/%s/top/all/page/%s.json" % (args[0], page)).json()['data']:
            resp = "%s - http://i.imgur.com/%s%s" % (img['title'], img['hash'], img['ext'])
            if img['nsfw']:
                resp = resp + " :nsfw:"
            imgs.append(resp)
        if len(imgs):
            return choice(imgs)


