import stomp
import urlparse
import json

urlparse.uses_netloc.append('tcp')

class ZKillboardStompListener(object):

    def __init__(self, bot):
        self.bot = bot
        self.conn = None

    def on_error(self, headers, message):
        pass

    def on_message(self, headers, message):
        kill = json.loads(message)
        kill_type = None

        # Tag kills
        for attacker in kill['attackers']:
            if int(attacker['corporationID']) in self.bot.kill_corps:
                kill_type = 'KILL'
                break

        # Tag losses
        if int(kill['victim']['corporationID']) in self.bot.kill_corps:
            kill_type = 'LOSS'

        if not kill_type:
            return

        body, html = self.bot.call_command('kill', [], None, no_url=False, raw=kill)
        if body:
            text = '[{}] {}'.format(kill_type, body)
            if not self.bot.kills_muted:
                for room in self.bot.rooms:
                    self.bot.send_message(room, text, mtype='groupchat')


    def connect(self, url):
        url = urlparse.urlparse(url)
        self.conn = stomp.Connection([(url.hostname, url.port)])
        self.conn.set_listener('', self)
        self.conn.start()
        self.conn.connect('guest', 'guest')
        self.conn.subscribe(destination='/topic/kills', ack='auto', id=1)