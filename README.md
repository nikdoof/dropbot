dropbot
=======

[![wercker status](https://app.wercker.com/status/76f99d586d9f2fcd532e31fb0de2ab6c/m "wercker status")](https://app.wercker.com/project/bykey/76f99d586d9f2fcd532e31fb0de2ab6c)

A XMPP bot to provide simple services to NOG8S and Predditors in general

License
-------

This repository is licensed under the MIT license.

Requirements
------------

Python requirements are covered in ```requirements.txt```, in addition a working Redis server is needed to enable API caching from the EVE Online API server. Redis is not essential to the operation of Dropbot but without caching you may get into hot water with CCP.

Setup
-----

Dropbot is designed to run on Heroku, but can be ran locally using ```python dropbot\cli.py -c env```

Docker
------

Dropbot can be run on Docker using the image ``robhaswell/docker``:

    docker run -ti -e DROPBOT_JID='user@server' -e DROPBOT_PASSWORD='password' -e DROPBOT_ROOMS='room@server' robhaswell/dropbot

Configuration
-------------

The configuration is passed by using environment variables.

* ```DROPBOT_JID``` - JID of the bot account
* ```DROPBOT_PASSWORD``` - Password of the account
* ```DROPBOT_NICKNAME``` - MUC nickname (defaults to Dropbot)
* ```DROPBOT_ROOMS``` - List of MUC rooms to join, seperated by commas
* ```DROPBOT_REDIS_URL``` - 12 factor style URL of the Redis server to use (defaults to redis://localhost:6379/0)
* ```DROPBOT_CMD_PREFIX``` - Prefix of MUC channel commands (defaults to !)
* ```DROPBOT_KOS_URL``` - URL of the CVA KOS API service (defaults to http://kos.cva-eve.org/api/)
* ```DROPBOT_MARKET_SYSTEMS``` - A comma seperated list of systems to be used for the best price checker (defaults to Jita, Amarr, Rens, Dodixie)
* ```DROPBOT_KILL_CORPS``` - List of Corp IDs to track for kills
* ```DROPBOT_KILLS_DISABLED``` - Disables the streaming of zKillboard kills to the channels (default to 0)
* ```DROPBOT_OFFICE_API_KEYID``` - API KeyID to use for the nearest office finder.
* ```DROPBOT_OFFICE_API_VCODE``` - API vCode to use for the nearest office finder.

Updating the SDE data
---------------------

To update the SDE data in the bot, use the ```gen_reference_data.py``` with a copy of the Sqlite conversion of the SDE, this will produce three json files that need to be copied to the data directory witthin the ```dropbot``` package.

The SDE conversion is usually available here: https://www.fuzzwork.co.uk/dump/

    $ wget https://www.fuzzwork.co.uk/dump/sqlite-latest.sqlite.bz2
    $ python gen_reference_data.py sqlite-latest.sqlite.bz2
    Importing Types...
    Importing Stations...
    Importing Map...
    $ ls *.json
    map.json
    stations.json
    types.json
    $ cp -i map.json stations.json types.json dropbot/data/
