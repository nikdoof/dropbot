import sys
import sqlite3
from json import dumps

def main():
    if len(sys.argv) > 1:
        dbfile = sys.argv[1]
        try:
            conn = sqlite3.connect(dbfile)
            conn.text_factory = str
        except:
            print("Unable to open the SDE file at %s\n" % dbfile)
    else:
        sys.stderr.write("Usage: {} <db file>\n".format(sys.argv[0]))
        return 1

    sys.stderr.write("Importing Types...\n")
    data = {}
    for row in conn.execute("""SELECT typeID, typeName FROM invTypes"""):
        pk, name = row
        try:
            x = name.decode('utf8')
        except:
            continue
        data[long(pk)] = name

    with open('types.json', 'wb') as f:
        f.write(dumps(data))

    sys.stderr.write("Importing Stations...\n")
    data = {}
    for row in conn.execute("""SELECT stationID, solarSystemID FROM staStations"""):
        pk, val = row
        data[long(pk)] = long(val)

    with open('stations.json', 'wb') as f:
        f.write(dumps(data))

    sys.stderr.write("Importing Map...\n")

    from dropbot.map import Map
    map = Map()
    map.from_sde(conn)

    with open('map.json', 'wb') as f:
        f.write(map.to_json())

if __name__ == '__main__':
    main()