from xml.etree import ElementTree

from sleekxmpp import ClientXMPP
from redis import Redis
import requests
from humanize import intcomma
import pkgutil
from json import loads as base_loads
from random import choice
from dropbot.map import Map


market_systems = [
    ('Jita', 30000142),
    ('Amarr', 30002187),
    ('Rens', 30002510),
    ('Dodixie', 30002659),
    ('HED-GP', 30001161),
    ('GE-8JV', 30001198),
]


class DropBot(ClientXMPP):
    def __init__(self, **kwargs):
        self.rooms = kwargs.pop('rooms', [])
        self.nickname = kwargs.pop('nickname', 'Dropbot')
        self.cmd_prefix = kwargs.pop('cmd_prefix', '!')
        self.kos_url = kwargs.pop('kos_url', 'http://kos.cva-eve.org/api/')

        self.redis_conn = Redis()
        self.map = Map.from_json(pkgutil.get_data('dropbot', 'data/map.json'))

        super(DropBot, self).__init__(**kwargs)
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

    # Helpers

    def _get_evecentral_price(self, type_id, system_id):
        try:
            resp = requests.get('http://api.eve-central.com/api/marketstat?typeid={}&usesystem={}'.format(type_id, system_id))
            root = ElementTree.fromstring(resp.content)
        except:
            return None

        return (float(root.findall("./marketstat/type[@id='{}']/sell/min".format(type_id))[0].text),
                float(root.findall("./marketstat/type[@id='{}']/buy/max".format(type_id))[0].text))

    def _system_price(self, args, msg, system, system_id):
        item = ' '.join(args)
        if item.strip() == '':
            return 'Usage: !{} <item>'.format(system.lower())
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
            resp = requests.get('http://api.eve-central.com/api/marketstat?typeid={}&usesystem={}'.format(typeid, system_id))
            root = ElementTree.fromstring(resp.content)
        except:
            return "An error occurred tying to get the price for {}".format(name)

        return "{} @ {} | Sell: {} | Buy: {}".format(
            name,
            system,
            intcomma(float(root.findall("./marketstat/type[@id='{}']/sell/min".format(typeid))[0].text)),
            intcomma(float(root.findall("./marketstat/type[@id='{}']/buy/max".format(typeid))[0].text)),
        )

    # Commands

    def cmd_price(self, args, msg):
        item = ' '.join(args)
        if item.strip() == '':
            return 'Usage: !price <item>'
        if item.lower() == 'plex':
            item = '30 Day'
        types = dict([(i, v) for i, v in self.types.iteritems() if item.lower() in v.lower()])
        if len(types) > 1:
            for i, v in types.iteritems():
                if item.lower() == v.lower():
                    type_id, type_name = i, v
                    break
            else:
                if len(types) > 10:
                    return "More than 10 items found, please narrow down what you want."
                return "Did you mean: {}?".format(
                    ', '.join(types.itervalues())
                )
        else:
            type_id, type_name = types.popitem()

        min_sell = 0
        max_buy = 0
        sell_sys = None
        buy_sys = None

        for name, sys_id in market_systems:
            sell, buy = self._get_evecentral_price(type_id, sys_id)
            print name, sell, buy
            if (sell < min_sell or min_sell == 0) and sell > 0:
                min_sell = sell
                sell_sys = name
            if buy > max_buy:
                max_buy = buy
                buy_sys = name

        print min_sell
        return '{}\nBest Sell: {} @ {} ISK\nBest Buy: {} @ {} ISK'.format(
            type_name,
            sell_sys, intcomma(min_sell),
            buy_sys, intcomma(max_buy)
        )

    def cmd_jita(self, args, msg):
        return self._system_price(args, msg, 'Jita', 30000142)

    def cmd_amarr(self, args, msg):
        return self._system_price(args, msg, 'Amarr', 30002187)

    def cmd_rens(self, args, msg):
        return self._system_price(args, msg, 'Rens', 30002510)

    def cmd_dodixie(self, args, msg):
        return self._system_price(args, msg, 'Dodixie', 30002659)

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

    def cmd_kos(self, args, msg):
        arg = ' '.join(args)
        resp = requests.get(self.kos_url, params={
            'c': 'json',
            'q': arg,
            'type': 'unit',
            'details': None
        })
        if resp.status_code != requests.codes.ok:
            return "Something went wrong (Error %s)" % resp.status_code
        try:
            data = resp.json()
        except:
            return "KOS API returned invalid data."
        if data['message'] != 'OK':
            return "KOS API returned an error."
        if data['total'] == 0:
            return "KOS returned no results (Not on KOS)"

        results = []
        for result in data['results']:
            text = '{} ({}) - {}'.format(
                result['label'],
                result['type'],
                'KOS' if result['kos'] else 'Not KOS'
            )
            results.append(text)
        return '\n'.join(results)

    def cmd_range(self, args, msg):
        if len(args) != 1:
            return '!range <system>'
        system = args[0]

        system_id = self.map.get_system_id(system)
        if not system_id:
            return 'Unknown system %s' % system

        res = {}
        systems = self.map.neighbors_jump(system_id, ship_class='blackops')
        for sys, range in systems:
            if sys['region'] in res:
                res[sys['region']] += 1
            else:
                res[sys['region']] = 1

        return '{} systems in JDC5 Blops range of {}:\n'.format(len(systems), self.map.get_system_name(system_id)) + '\n'.join(['{} - {}'.format(x, y) for x, y in res.items()])