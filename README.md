dropbot
=======

[![wercker status](https://app.wercker.com/status/76f99d586d9f2fcd532e31fb0de2ab6c/m "wercker status")](https://app.wercker.com/project/bykey/76f99d586d9f2fcd532e31fb0de2ab6c)

A XMPP bot to provide simple services to NOG8S and Predditors in general

License
-------

This repository is licensed under the MIT license.

Setup
-----

Dropbot is designed to run on Heroku, but can be ran locally using ```python dropbot\cli.py -c env```

Docker
------

Dropbot can be run on Docker using the image ``robhaswell/docker``:

``docker run -ti -e DROPBOT_JID='user@server' -e DROPBOT_PASSWORD='password' -e DROPBOT_ROOMS='room@server' robhaswell/dropbot``

Configuration
-------------

The configuration is passed by using environment variables.

* ```DROPBOT_JID``` - JID of the bot account
* ```DROPBOT_PASSWORD``` - Password of the account
* ```DROPBOT_NICKNAME``` - MUC nickname (defaults to Dropbot)
* ```DROPBOT_ROOMS``` - List of MUC rooms to join, seperated by commas
* ```DROPBOT_CMD_PREFIX``` - Prefix of MUC channel commands (defaults to !)
* ```DROPBOT_KOS_URL``` - URL of the CVA KOS API service (defaults to http://kos.cva-eve.org/api/)
