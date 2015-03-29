import os
import logging
from json import load
import requests
from optparse import OptionParser

from dropbot.bot import DropBot


def main():
    # Setup the command line arguments.
    optp = OptionParser()

    # Output verbosity options.
    optp.add_option('-q', '--quiet', help='set logging to ERROR',
                    action='store_const', dest='loglevel',
                    const=logging.ERROR, default=logging.INFO)
    optp.add_option('-d', '--debug', help='set logging to DEBUG',
                    action='store_const', dest='loglevel',
                    const=logging.DEBUG, default=logging.INFO)
    optp.add_option('-v', '--verbose', help='set logging to COMM',
                    action='store_const', dest='loglevel',
                    const=5, default=logging.INFO)

    # JID and password options.
    optp.add_option("-c", "--config", dest="config",
                    help="Configuration file to use")

    opts, args = optp.parse_args()

    # Load config
    if opts.config == 'env':
        # Parse the environment for config
        config = dict([(k[8:].lower(), v) for k, v in os.environ.items() if 'DROPBOT_' in k])
        # Split out array type configs
        for key in ['rooms', 'admins', 'kill_corps', 'market_systems']:
            if key in config:
                config[key] = [x.strip() for x in config[key].split(',')]
    elif opts.config.lower().startswith('http'):
        try:
            config = requests.get(opts.config).json()
        except:
            print "Unable to download configuration from %s" % opts.config
            return 1
    else:
        cfg = os.path.expanduser(os.path.expandvars(opts.config))
        if not os.path.exists(cfg):
            print "Configuration file %s does not exist" % cfg
            return 1
        with open(os.path.expanduser(cfg), 'r') as f:
            config = load(f)

    # Setup logging.
    logging.basicConfig(level=opts.loglevel,
                        format='%(levelname)-8s %(message)s')

    xmpp = DropBot(**config)

    # Connect to the XMPP server and start processing XMPP stanzas.
    if xmpp.connect():
        xmpp.process(block=True)
        print("Done")
    else:
        print("Unable to connect.")


if __name__ == '__main__':
    main()