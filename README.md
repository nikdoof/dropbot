dropbot
=======

A XMPP bot to provide simple services to NOG8S and Predditors in general

Setup
-----

Dropbot is designed to run on Heroku, but can be ran locally using ```python dropbot\cli.py -c env```

Configuration
-------------

The configuration is passed by using environment variables.

* ```DROPBOT_JID``` - JID of the bot account
* ```DROPBOT_PASSWORD``` - Password of the account
* ```DROPBOT_NICKNAME``` - MUC nickname (defaults to Dropbot)
* ```DROPBOT_ROOMS``` - List of MUC rooms to join, seperated by commas
* ```DROPBOT_CMD_PREFIX``` - Prefix of MUC channel commands (defaults to !)
* ```DROPBOT_KOS_URL``` - URL of the CVA KOS API service (defaults to http://kos.cva-eve.org/api/)
