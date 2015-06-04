from datetime import datetime
from xml.etree import ElementTree
import pkgutil
from json import loads as base_loads
from random import choice
import logging
import re
import urlparse

from sleekxmpp import ClientXMPP
from redis import Redis, ConnectionPool
import requests
from humanize import intcomma, naturaltime, intword
from pyzkb import ZKillboard
from eveapi import EVEAPIConnection

from dropbot.map import Map, base_range, ship_class_to_range
from dropbot.utils import EVEAPIRedisCache
from dropbot.stomp_listener import ZKillboardStompListener

urlparse.uses_netloc.append("redis")

zkillboard_regex = re.compile(r'http(s|):\/\/(?P<host>.*)\/kill\/(?P<killID>\d+)\/')


class UnknownCommandException(Exception):
    pass


class DropBot(ClientXMPP):
    def __init__(self, *args, **kwargs):
        self.rooms = kwargs.pop('rooms', [])
        self.nickname = kwargs.pop('nickname', 'Dropbot')
        self.cmd_prefix = kwargs.pop('cmd_prefix', '!')
        self.kos_url = kwargs.pop('kos_url', 'http://kos.cva-eve.org/api/')
        self.hidden_commands = ['cmd_prefix']
        self.last_killdate = datetime.utcnow()
        self.kill_corps = [int(x) for x in kwargs.pop('kill_corps', [])]
        self.kills_disabled = kwargs.pop('kills_disabled', '0') == '1'
        self.kills_muted = False
        self.office_api_key_keyid = kwargs.pop('office_api_keyid', None)
        self.office_api_key_vcode = kwargs.pop('office_api_vcode', None)
        self.market_systems = kwargs.pop('market_systems', ['Jita', 'Amarr', 'Rens', 'Dodixie'])

        if 'redis_url' in kwargs:
            self.redis_pool = ConnectionPool.from_url(kwargs.pop('redis_url', 'redis://localhost:6379/0'))
            self.redis = Redis(connection_pool=self.redis_pool)
        else:
            logging.warning('No DROPBOT_REDIS_URL defined, EVE API calls will not be cached!')
            self.redis = None
        self.map = Map.from_json(pkgutil.get_data('dropbot', 'data/map.json'))

        jid = kwargs.pop('jid', None)
        password = kwargs.pop('password', None)

        super(DropBot, self).__init__(jid, password)

        self.register_plugin('xep_0030')  # Service Discovery
        self.register_plugin('xep_0045')  # Multi-User Chat
        self.register_plugin('xep_0199')  # XMPP Ping

        # Basic bot auto config
        self.auto_subscribe = False
        self.auto_authorize = True

        # Handlers
        self.add_event_handler('session_start', self.handle_session_start)
        self.add_event_handler('message', self.handle_message)

    # Reference Data

    @property
    def types(self):
        if not hasattr(self, '_types'):
            data = pkgutil.get_data('dropbot', 'data/types.json')
            self._types = base_loads(data)
        return self._types

    @property
    def stations(self):
        if not hasattr(self, '_stations'):
            data = pkgutil.get_data('dropbot', 'data/stations.json')
            self._stations = base_loads(data)
            logging.debug('Getting ConquerableStationList')
            for x in self.get_eveapi().eve.ConquerableStationList().outposts:
                self._stations[unicode(x.stationID)] = x.solarSystemID
        return self._stations

    # Command / Connection Handling
    def handle_session_start(self, event):
        self.get_roster()
        self.send_presence()

        # Join the defined MUC rooms
        for room in self.rooms:
            self.plugin['xep_0045'].joinMUC(room, self.nickname, wait=True)

        # Start the killchecker if we have corps to monitor
        if len(self.kill_corps) > 0 and not self.kills_disabled:
            logging.info('Starting ZKB Stomp monitor for corps: {}'.format(', '.join(self.kill_corps)))
            self.stomp = ZKillboardStompListener(self)
            self.stomp.connect('tcp://eve-kill.net:61613')
        else:
            logging.info('Kill monitoring disabled.')

    def call_command(self, command, *args, **kwargs):
        if hasattr(self, 'cmd_%s' % command):
            try:
                resp = getattr(self, 'cmd_%s' % command)(*args, **kwargs)
            except:
                resp = 'Oops, something went wrong...'
                logging.getLogger(__name__).exception('Error handling command')
            if resp:
                if isinstance(resp, tuple) and len(resp) == 2:
                    return resp
                else:
                    return resp, None
            else:
                return None, None
        else:
            raise UnknownCommandException

    def handle_message(self, msg):
        args = msg['body'].split(' ')
        cmd = args[0].lower()
        args.pop(0)
        if msg['type'] == 'groupchat':
            if msg['mucnick'] == self.nickname:
                return
            if msg['body'][0] != self.cmd_prefix:
                # If its not a command, check for ZKB urls
                seen = set([])
                response_lines = []
                for match in zkillboard_regex.finditer(msg['body']):
                    kill_id = match.groupdict()['killID']
                    host = match.groupdict()['host']
                    logging.info('Found Kill ID {}'.format(kill_id))
                    if kill_id in seen:
                        continue
                    body, html = self.call_command('kill', [kill_id], msg, no_url=True, host=host)
                    response_lines.append(body)
                    seen.add(kill_id)
                response_lines = [x for x in response_lines if x]
                if len(response_lines):
                    msg.reply('\n'.join(response_lines)).send()
                return
            # Strip the cmd_prefix
            cmd = cmd[1:]

        # Call the command
        try:
            body, html = self.call_command(cmd, args, msg)
        except UnknownCommandException:
            if msg['type'] != 'groupchat':
                msg.reply('Unknown command, use "help" to list all commands available').send()
            pass
        else:
            if body:
                msg.reply(body).send()

    # Helpers
    def _system_picker(self, name):
        systems = self.map.get_systems(name)
        if len(systems) > 1:
            if len(systems) > 10:
                return 'More than 10 systems match {}, please provide a more complete name'.format(name)
            return 'Did you mean: {}?'.format(', '.join([self.map.get_system_name(x) for x in systems]))
        elif len(systems) == 0:
            return 'No systems found matching {}'.format(name)
        else:
            return systems[0]

    def _item_picker(self, item):
            if item.strip() == '':
                return 'Usage: !price <item>'
            if item.lower() == 'plex':
                return (u"29668", u"30 Day Pilot's License Extension (PLEX)")
            types = dict([(i, v) for i, v in self.types.iteritems() if item.lower() in v.lower()])
            if len(types) == 0:
                return "No items named {} found".format(item)
            elif len(types) > 1:
                for i, v in types.iteritems():
                    if item.lower() == v.lower():
                        return (i, v)
                else:
                    if len(types) > 10:
                        return "More than 10 items found, please narrow down what you want."
                    return "Did you mean: {}?".format(
                        ', '.join(types.itervalues())
                    )
            return types.popitem()

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
        res = self._item_picker(item)
        if isinstance(res, basestring):
            return res
        type_id, type_name = res

        try:
            resp = requests.get('http://api.eve-central.com/api/marketstat?typeid={}&usesystem={}'.format(type_id, system_id))
            root = ElementTree.fromstring(resp.content)
        except:
            return "An error occurred tying to get the price for {}".format(type_name)

        return "{} @ {} | Sell: {} | Buy: {}".format(
            type_name,
            system,
            intcomma(float(root.findall("./marketstat/type[@id='{}']/sell/min".format(type_id))[0].text)),
            intcomma(float(root.findall("./marketstat/type[@id='{}']/buy/max".format(type_id))[0].text)),
        )

    def _get_offices(self, keyid, vcode):
        """Returns a list of offices from a Corp API key"""
        logging.debug('Retreving offices for {}/{}'.format(keyid, vcode))
        if not keyid or not vcode:
            return []
        try:
            assets = self.get_eveapi_auth(keyid, vcode).corp.AssetList()
        except RuntimeError:
            logging.exception('Unable to retrieve asset listing for {}/{}'.format(keyid, vcode))
            return []

        def location_to_station(location_id):
            if location_id >= 67000000:
                return location_id - 6000000
            if location_id >= 66000000:
                return location_id - 6000001
            return location_id

        return [self.stations[unicode(location_to_station(x.locationID))] for x in assets.assets if x.typeID == 27]

    def get_eveapi(self):
        if self.redis:
            return EVEAPIConnection(cacheHandler=EVEAPIRedisCache(self.redis))
        return EVEAPIConnection()

    def get_eveapi_auth(self, keyid, vcode):
        return self.get_eveapi().auth(keyID=keyid, vCode=vcode)

    def check_eveapi_permission(self, keyid, vcode, bit):
        try:
            accessmask = int(self.get_eveapi_auth(keyid, vcode).account.APIKeyInfo().key.accessMask)
            logging.debug('Key ID {} - Access Mask: {}'.format(keyid, accessmask))
        except RuntimeError:
            return False
        mask = 1 << bit
        return (accessmask & mask) > 0

    # Commands

    def cmd_help(self, args, msg):
        if len(args) == 0:
            if msg['type'] == 'groupchat':
                return "Commands: {}\nAll commands are available in private chat without the {} prefix".format(
                    ', '.join([self.cmd_prefix + x[4:] for x in dir(self) if x[:4] == 'cmd_' and x not in self.hidden_commands]),
                    self.cmd_prefix
                )
            else:
                command_lines = ['{}{}: {}'.format(self.cmd_prefix, cmd[4:], getattr(self, cmd).__doc__ or 'No documentation available') for cmd in dir(self) if cmd[:4] == 'cmd_' and cmd not in self.hidden_commands]
                return "Available Commands\n\n{}".format('\n'.join(command_lines))
        cmd = args[0]
        if hasattr(self, 'cmd_%s' % cmd):
            if getattr(self, 'cmd_%s' % cmd).__doc__ is not None:
                return '{}{}: {}'.format(
                    self.cmd_prefix,
                    cmd,
                    getattr(self, 'cmd_%s' % cmd).__doc__
                )
            else:
                return 'This command has no documentation'
        else:
            return 'Unknown command'

    def cmd_bestprice(self, args, msg):
        """Returns the best price for an item out of the current known market hub systems"""
        item = ' '.join(args)
        res = self._item_picker(item)
        if isinstance(res, basestring):
            return res
        type_id, type_name = res

        min_sell = 0
        max_buy = 0
        sell_sys = None
        buy_sys = None

        for name in self.market_systems:
            sys_id = self.map.get_system_id(name)
            if not sys_id:
                continue
            sell, buy = self._get_evecentral_price(type_id, sys_id)
            if (sell < min_sell or min_sell == 0) and sell > 0:
                min_sell = sell
                sell_sys = name
            if buy > max_buy:
                max_buy = buy
                buy_sys = name
        return '{}\nBest Sell: {} @ {} ISK\nBest Buy: {} @ {} ISK'.format(
            type_name,
            sell_sys, intcomma(min_sell),
            buy_sys, intcomma(max_buy)
        )

    def cmd_price(self, args, msg):
        """Returns the price of an item in a particular system"""
        if len(args) < 2:
            return '!price <system name> <item>'
        item = ' '.join(args[1:])
        system_id = self._system_picker(args[0])
        if isinstance(system_id, basestring):
            return system_id
        item = self._item_picker(item)
        if isinstance(item, basestring):
            return item
        type_id, type_name = item
        sell, buy = self._get_evecentral_price(type_id, system_id)
        return '{} @ {} | Sell {} | Buy: {}'.format(
            type_name,
            self.map.get_system_name(system_id),
            intcomma(sell),
            intcomma(buy)
        )

    def cmd_jita(self, args, msg):
        """Returns the price of a item in Jita"""
        return self.cmd_price(['Jita'] + args, msg)

    def cmd_amarr(self, args, msg):
        """Returns the price of a item in Amarr"""
        return self.cmd_price(['Amarr'] + args, msg)

    def cmd_rens(self, args, msg):
        """Returns the price of a item in Rens"""
        return self.cmd_price(['Rens'] + args, msg)

    def cmd_dodixie(self, args, msg):
        """Returns the price of a item in  Dodixie"""
        return self.cmd_price(['Dodixie'] + args, msg)

    def cmd_uh(self, args, msg):
        """Returns the price of a item in U-HVIX"""
        return self.cmd_price(['U-HVIX'] + args, msg)

    def cmd_r(self, args, msg):
        return self.cmd_redditimg(args, msg)

    def cmd_redditimg(self, args, msg):
        """Shows a random picture from imgur.com reddit section"""
        if len(args) == 0:
            return "Usage: !redditimg <subreddit>"
        imgs = []
        for page in range(1, 11):
            for img in requests.get("http://imgur.com/r/%s/top/all/page/%s.json" % (args[0], page)).json()['data']:
                resp = "%s - http://i.imgur.com/%s%s" % (img['title'], img['hash'], img['ext'])
                if img['nsfw']:
                    resp = resp + " :nsfw:"
                imgs.append(resp)
        if len(imgs):
            return choice(imgs)

    def cmd_kos(self, args, msg):
        """Checks the CVA KOS list for a name"""
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
        """Returns a count of the number of systems in jump range from a source system"""
        if len(args) == 0 or len(args) > 2:
            return '!range <system> <ship class>'

        system = args[0]
        if len(args) == 2:
            ship_class = args[1].lower()
        else:
            ship_class = 'blackops'

        if ship_class not in base_range.keys():
            return 'Unknown class {}, please use one of: {}'.format(
                ship_class,
                ', '.join(base_range.keys())
            )

        system_id = self._system_picker(system)
        if isinstance(system_id, basestring):
            return system_id

        res = {}
        systems = self.map.neighbors_jump(system_id, ship_class=ship_class)
        for sys, range in systems:
            if sys['region'] in res:
                res[sys['region']] += 1
            else:
                res[sys['region']] = 1

        return '{} systems in JDC5 {} range of {}:\n'.format(len(systems), ship_class, self.map.get_system_name(system_id)) + '\n'.join(['{} - {}'.format(x, y) for x, y in res.items()])

    def cmd_route(self, args, msg):
        """Shows the shortest route between two sytems"""
        if len(args) != 2:
            return '!route <source> <destination>'
        source, dest = args

        source = self._system_picker(source)
        if isinstance(source, basestring):
            return source
        dest = self._system_picker(dest)
        if isinstance(dest, basestring):
            return dest

        route = self.map.route_gate(source, dest)
        route_names = ' -> '.join(['{} ({})'.format(x['name'], round(x['security'], 2)) for x in [self.map.node[y] for y in route]])

        return '{} jumps from {} to {}\n{}'.format(
            len(route)-1,
            self.map.get_system_name(source),
            self.map.get_system_name(dest),
            route_names
        )

    def cmd_addjb(self, args, msg):
        """Adds a jumpbridge to the internal map for routing purposes"""
        if len(args) != 2:
            return '!addjb <source> <destination>'
        source, dest = args

        source = self._system_picker(source)
        if isinstance(source, basestring):
            return source
        dest = self._system_picker(dest)
        if isinstance(dest, basestring):
            return dest

        self.map.add_jumpbridge(source, dest)
        return "Done"

    def cmd_listjbs(self, args, msg):
        """List all known jumpbridges stored in the map"""
        resp_lines = []
        for u, v, d in self.map.edges_iter(data=True):
            if d['link_type'] == 'bridge':
                line = '{} <-> {} ({}ly)'.format(
                    self.map.get_system_name(u),
                    self.map.get_system_name(v),
                    round(self.map.system_distance(u, v), 2),
                )
                resp_lines.append(line)
        return '\n'.join(resp_lines)

    def cmd_mapstats(self, args, msg):
        """Gives the current overview of the internal map"""
        return '{} systems, {} gate jumps, {} jump bridges'.format(
            len(self.map.nodes()),
            len([u for u, v, d in self.map.edges_iter(data=True) if d['link_type'] == 'gate']),
            len([u for u, v, d in self.map.edges_iter(data=True) if d['link_type'] == 'bridge'])
        )

    def cmd_hit(self, args, msg):
        """Details what class and JDC level is required to jump between two systems"""
        if len(args) != 2:
            return '!hit <source> <destination>'
        source, dest = args

        source = self._system_picker(source)
        if isinstance(source, basestring):
            return source
        dest = self._system_picker(dest)
        if isinstance(dest, basestring):
            return dest

        if self.map.node[dest]['security'] >= 0.5:
            return '{} is a highsec system'.format(self.map.get_system_name(dest))

        ly = self.map.system_distance(source, dest)

        if ly > 6.5 * (1 + (0.25 * 5)):
            return '{} to {} is greater than {}ly (maximum jump range of all ships)'.format(
                self.map.get_system_name(source),
                self.map.get_system_name(dest),
                6.5 * (1 + (0.25 * 5))
            )

        res = []
        for ship_class in base_range.keys():
            res1 = []
            for skill in [4, 5]:
                if ship_class_to_range(ship_class, skill) >= ly:
                    res1.append('JDC{}'.format(skill))
            if len(res1):
                res.append('{}: {}'.format(ship_class, ', '.join(res1)))

        return '{} -> {} ({}ly) Capable Ship Types:\n{}'.format(
            self.map.get_system_name(source),
            self.map.get_system_name(dest),
            round(ly, 2),
            '\n'.join(res)
        )

    def cmd_jump(self, args, msg):
        """Calculates the shortest jump route between two systems"""
        if len(args) < 2:
            return '!jump <source> <destination> (<ship class> <jdc level> <jfc level>)'
        elif len(args) == 2:
            source, dest = args
            ship_class = 'blackops'
            jdc = jfc = 5
        elif len(args) == 3:
            source, dest, ship_class = args
            jdc = jfc = 5
        elif len(args) == 4:
            source, dest, ship_class, jdc = args
            jfc = 5
        else:
            source, dest, ship_class, jdc, jfc = args
        jf = 5

        source = self._system_picker(source)
        if isinstance(source, basestring):
            return source
        dest = self._system_picker(dest)
        if isinstance(dest, basestring):
            return dest

        if ship_class not in base_range.keys():
            return 'Unknown class {}, please use one of: {}'.format(
                ship_class,
                ', '.join(base_range.keys())
            )

        try:
            int(jdc)
            int(jfc)
        except ValueError:
            return 'Invalid JDC/JFC level'

        route = self.map.route_jump(source, dest, ship_class=ship_class)
        if len(route):
            return '{} to {} ({}/{}/{}), {} jumps ({}ly / {} isotopes):\n{}'.format(
                self.map.get_system_name(source),
                self.map.get_system_name(dest),
                ship_class,
                jdc,
                jfc,
                len(route)-1,
                round(self.map.route_jump_distance(route), 2),
                round(self.map.route_jump_isotopes(route, int(jfc), ship_class=ship_class, jf_skill=jf), 0),
                ' -> '.join([self.map.get_system_name(x) for x in route])
            )
        else:
            return 'No route found'

    def cmd_id(self, args, msg):
        """Provides an overview of a character's activity in-game"""
        if len(args) == 0:
            return '!id <character name>'
        char_name = ' '.join(args)

        result = self.get_eveapi().eve.CharacterID(names=char_name.strip())
        char_name = result.characters[0].name
        char_id = result.characters[0].characterID

        if char_id == 0:
            return 'Unknown character {}'.format(char_name)

        headers, res = ZKillboard().characterID(char_id).kills().pastSeconds(60 * 60 * 24 * 7).get()

        from collections import defaultdict, Counter

        kill_types = defaultdict(int)
        ship_types = defaultdict(int)
        alli_assoc = defaultdict(int)
        sum_value = 0.0
        for kill in res:
            kill_type_id = int(kill['victim']['shipTypeID'])
            if kill_type_id > 0:
                kill_types[self.types[unicode(kill_type_id)]] += 1
            sum_value += float(kill['zkb']['totalValue'])
            for attk in kill['attackers']:
                if attk['allianceName'].strip() != '' and attk['allianceName'] is not None:
                    alli_assoc[attk['allianceName']] += 1
                if int(attk['characterID']) == char_id:
                    ship_type_id = int(attk['shipTypeID'])
                    if ship_type_id > 0:
                        ship_types[self.types[unicode(ship_type_id)]] += 1
                    break
        if len(res) == 0:
            return '{} has had no kills in the last week'.format(char_name)

        kill_types = Counter(kill_types).most_common(5)
        ship_types = Counter(ship_types).most_common(5)
        alli_assoc = Counter(alli_assoc).most_common(5)

        return '{}, {} kill(s) ({} ISK) in the last week\nActive Systems: {}\nTop 5 Killed Types: {}\nTop 5 Ship: {}\nTop 5 Associates: {}'.format(
            char_name,
            len(res),
            intcomma(sum_value),
            ', '.join(set([self.map.node[int(x['solarSystemID'])]['name'] for x in res])),
            ', '.join(['{} ({})'.format(x, y) for x, y in kill_types]),
            ', '.join(['{} ({})'.format(x, y) for x, y in ship_types]),
            ', '.join([x for x, y in alli_assoc])
        )

    def cmd_kill(self, args, msg, no_url=False, raw=None, host=None):
        """Returns a summary of a zKillboard killmail"""
        if not raw:
            if len(args) == 0:
                return '!kill <Kill ID/zKillboard URL>'
            kill_id = args[0]
            try:
                kill_id = int(kill_id)
            except ValueError:
                m = zkillboard_regex.match(kill_id)
                if m:
                    kill_id = m.groupdict()['killID']
                    host = m.groupdict()['host']
                else:
                    return 'Invalid kill ID'

            headers, data = ZKillboard(base_url='https://{}/api/'.format(host)).killID(kill_id).get()
            kill = data[0]
        else:
            kill = raw
            kill_id = raw['killID']

        if no_url:
            url = ''
        else:
            url = ' - https://{}/kill/{}/'.format(host, kill_id)

        # Ignore kills over an hour old if they're from stomp
        age = (datetime.utcnow() - datetime.strptime(kill['killTime'], '%Y-%m-%d %H:%M:%S'))
        if age.total_seconds() > 60 * 60 and raw:
            return

        # Drop kills less than 1mil if they've come from stomp
        if raw and float(kill['zkb']['totalValue']) < 1000000:
            return

        if 'zkb' in kill and 'totalValue' in kill['zkb']:
            value_lost = intword(float(kill['zkb']['totalValue']))
        else:
            value_lost = '???'

        return '{} ({}) in {}, {}, {} attacker(s), {} ISK lost{}'.format(
            kill['victim']['characterName'],
            self.types[unicode(kill['victim']['shipTypeID'])],
            self.map.node[int(kill['solarSystemID'])]['name'],
            naturaltime(age),
            len(kill['attackers']),
            value_lost,
            url,
        )

    def cmd_mute(self, args, msg):
        """Mutes killmail broadcast for 30 minutes"""

        self.kills_muted = True

        def unmute(self):
            self.kills_muted = False

        self.schedule('unmute', 30 * 60, unmute, [self])
        return 'Killmails muted, posting will resume automatically in 30 minutes'

    def cmd_nearestoffice(self, args, msg):
        if len(args) != 1:
            return '!nearestoffice <system>'
        source = args[0]

        if not self.office_api_key_keyid or not self.office_api_key_vcode:
            return 'No Corp API key is setup'
        if not self.check_eveapi_permission(self.office_api_key_keyid, self.office_api_key_vcode, 1):
            return "The API key setup doesn't have the correct permissions"

        source = self._system_picker(source)
        if isinstance(source, basestring):
            return source

        min_route = None
        target_office = None
        for office in self._get_offices(self.office_api_key_keyid, self.office_api_key_vcode):
            if office == source:
                return 'An office is in the target system'
            route_length = len(self.map.route_gate(source, office)) - 1
            if not min_route or (route_length) < min_route:
                target_office = office
                min_route = route_length

        if target_office:
            return 'Nearest Office to {} is {}, {} jump(s)'.format(
                self.map.get_system_name(source),
                self.map.get_system_name(target_office),
                min_route,
            )
        return 'No known offices.'

    def cmd_rageping(self, args, msg):
        """Ping spams everyone's name in a room, use with caution"""
        if msg['type'] != 'groupchat':
            return 'This only works in MUC rooms'

        names = self.plugin['xep_0045'].getRoster(msg['from'].bare)
        return 'RAGE PING: {} :frogsiren:'.format(', '.join(names))
