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
        for attacker in kill['attackers']:
            if int(attacker['corporationID']) in self.bot.kill_corps:
                break
        else:
            if int(kill['victim']['corporationID']) not in self.bot.kill_corps:
                return

        print message
        body, html = self.bot.call_command('kill', [], None, no_url=False, raw=kill)
        text = 'New Kill: {}'.format(body)
        for room in self.bot.rooms:
            self.bot.send_message(room, text, mtype='groupchat')


    def connect(self, url):
        url = urlparse.urlparse(url)
        self.conn = stomp.Connection([(url.hostname, url.port)])
        self.conn.set_listener('', self)
        self.conn.start()
        self.conn.connect('guest', 'guest')
        self.conn.subscribe(destination='/topic/kills', ack='auto', id=1)