import math
import networkx
from networkx.readwrite.json_graph import node_link_data, node_link_graph
from json import loads, dumps


def calc_distance(sys1, sys2):
    """Calculate the distance in lightyears between two sets of 3d coordinates"""
    EVE_LY = 9460000000000000  # EVE's definition of a ly in KM
    return math.sqrt(sum((a - b)**2 for a, b in zip(sys1, sys2))) / EVE_LY


class Map(networkx.Graph):

    def load_sde_data(self, db_conn):
        for id, name, region_name, x, y, z in db_conn.execute("""
            SELECT solarSystemID, solarSystemName, regionName, mapSolarSystems.x, mapSolarSystems.y, mapSolarSystems.z
            FROM mapSolarSystems
            INNER JOIN mapRegions ON mapSolarSystems.regionID = mapRegions.regionID
            WHERE mapSolarSystems.regionID < 11000001"""):
            self.add_node(id, system_id=id, name=name, region=region_name, coords=(x, y, z))
        for from_id, to_id in db_conn.execute("SELECT fromSolarSystemID, toSolarSystemID FROM mapSolarSystemJumps"):
            self.add_edge(from_id, to_id)

    def to_json(self):
        return dumps(node_link_data(self))

    @staticmethod
    def from_json(json):
        return Map(data=node_link_graph(loads(json)))

    def systemid_to_name(self, system_id):
        return self.node[system_id]['name']

    def name_to_systemid(self, name):
        for k, v in self.nodes_iter(data=True):
            if 'name' in v and v['name'].lower() == name.lower():
                return k

    def system_distance(self, source, destination):
        return calc_distance(self.node[source], self.node[destination])

    def route_gate(self, source, destination):
        return networkx.astar_path(self, source, destination)

    def route_jump(self, source, destination):
        return networkx.astar_path(self, source, destination, self.system_distance)

    def neighbors_gate(self, system_id):
        return self.neighbors(system_id)

    def neighbors_jump(self, system_id, range):
        source = self.node[system_id]

        destinations = []
        for destination_id, destination_data in self.nodes_iter(data=True):
            distance = calc_distance(source['coords'], destination_data['coords'])
            if distance <= range and destination_id != system_id:
                destinations.append((destination_data, distance))
        return destinations