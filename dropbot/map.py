import math
import networkx
from networkx.readwrite.json_graph import node_link_data, node_link_graph
from json import loads, dumps

hull_classes = {
    'chimera': 'carrier',
    'archon': 'carrier',
    'nidhoggur': 'carrier',
    'thanatos': 'carrier',
    'wyvern': 'supercarrier',
    'aeon': 'supercarrier',
    'hel': 'supercarrier',
    'nyx': 'supercarrier',
    'revenant': 'supercarrier',
    'phoenix': 'dreadnought',
    'revelation': 'dreadnought',
    'naglfar': 'dreadnought',
    'moros': 'dreadnought',
    'widow': 'blackops',
    'redeemer': 'blackops',
    'panther': 'blackops',
    'sin': 'blackops',
    'charon': 'jumpfreighter',
    'ark': 'jumpfreighter',
    'nomad': 'jumpfreighter',
    'anshar': 'jumpfreighter',
    'leviathan': 'titan',
    'avatar': 'titan',
    'ragnarok': 'titan',
    'erebus': 'titan',
    'rorqual': 'industrial',
}

base_range = {
    'carrier': 6.5,
    'dreadnought': 5.0,
    'industrial': 5.0,
    'jumpfreighter': 5.0,
    'supercarrier': 4.0,
    'titan': 3.5,
    'blackops': 3.5,
}

def calc_distance(sys1, sys2):
    """Calculate the distance in light years between two sets of 3d coordinates"""
    EVE_LY = 9460000000000000  # EVE's definition of a ly in KM
    return math.sqrt(sum((a - b)**2 for a, b in zip(sys1, sys2))) / EVE_LY

def hull_to_range(hull, jdc_skill):
    """Returns the jump range of a provided ship hull and Jump Drive Calibration skill"""
    if hull.lower() not in hull_classes:
        raise ValueError('Unknown hull class {}'.format(hull))
    return ship_class_to_range(hull_classes[hull.lower()], jdc_skill)
    
def ship_class_to_range(ship_class, jdc_skill):
    """Returns the jump range of a provided ship class and Jump Drive Calibration skill"""
    if ship_class.lower() not in base_range:
        raise ValueError('Unknown ship class {}'.format(ship_class))
    base = base_range[ship_class]
    jump_range = base * (1 + (0.25 * jdc_skill))
    return jump_range


class Map(networkx.Graph):
    """
    A in-memory representation of the EVE Universe map, using NetworkX
    """

    def from_sde(self, db_conn):
        """Load map data from a EVE SDE Sqlite DB"""
        for id, name, region_name, x, y, z, security in db_conn.execute("""
            SELECT solarSystemID, solarSystemName, regionName, mapSolarSystems.x, mapSolarSystems.y, mapSolarSystems.z, mapSolarSystems.security
            FROM mapSolarSystems
            INNER JOIN mapRegions ON mapSolarSystems.regionID = mapRegions.regionID
            WHERE mapSolarSystems.regionID < 11000001"""):
            self.add_node(id, system_id=id, name=name, region=region_name, coords=(x, y, z), security=security)
        for from_id, to_id in db_conn.execute("SELECT fromSolarSystemID, toSolarSystemID FROM mapSolarSystemJumps"):
            self.add_edge(from_id, to_id, weight=1, link_type='gate')

    def build_jumps(self):
        """Constructs the possible jump network"""
        max_jump = 6.5 * (1 + (0.25 * 5))
        
        for source_id, source_data in self.nodes_iter(data=True):
            for destination_data, destination_range in self.neighbors_jump(source_id, max_jump):
                if destination_data['security'] < 0.5:
                    self.add_edge(source_id, destination_data['system_id'], weight=destination_range, link_type='jump')
            
    def to_json(self):
        """Dump map data to a Node Link JSON output"""
        return dumps(node_link_data(self))

    @staticmethod
    def from_json(json):
        """Load map data from a Node Link JSON output"""
        return Map(data=node_link_graph(loads(json)))

    def get_system_name(self, system_id):
        """Returns the name of the provided system id"""
        return self.node[system_id]['name']

    def get_system_id(self, name):
        """Returns the system id of the named system"""
        for k, v in self.nodes_iter(data=True):
            if 'name' in v and v['name'].lower() == name.lower():
                return k

    def get_systems(self, name):
        """Returns a list of systems by a partial system name"""
        return [k for k, v in self.nodes_iter(data=True) if name.lower() in v['name'].lower()]
                
    def system_distance(self, source, destination):
        """Calculates the distance in ly between two systems"""
        return calc_distance(self.node[source], self.node[destination])

    def route_gate(self, source, destination, filter=None):
        """Route between two systems using gates (fastest)"""

        # TODO: add EVE routing options (highsec/lowsec/fastest)

        g = networkx.Graph(data=[(u, v) for u, v, d in self.edges_iter(data=True) if d['link_type'] == 'gate'])
        return networkx.astar_path(self, source, destination)

    def route_jump(self, source, destination, range=None, hull=None, ship_class=None):
        """Route between two systems using jumps"""
        g = networkx.Graph(data=[(u, v) for u, v, d in self.edges_iter(data=True) if d['link_type'] == 'jump' and d['weight'] <= range])
        return networkx.dijkstra_path(g, source, destination)

    def neighbors_gate(self, system_id):
        """List systems that are connected to a system by gates"""
        return self.neighbors(system_id)

    def neighbors_jump(self, system_id, range=None, hull=None, ship_class=None):
        """List all systems within a jump radius"""
        source = self.node[system_id]

        if not range:
            if hull:
                range = hull_to_range(hull, 5)
            elif ship_class:
                range = ship_class_to_range(ship_class, 5)
            else:
                raise ValueError('No range, hull, or ship class provided')
        
        destinations = []
        for destination_id, destination_data in self.nodes_iter(data=True):
            distance = calc_distance(source['coords'], destination_data['coords'])
            if distance <= range and destination_id != system_id:
                destinations.append((destination_data, distance))
        return destinations
        
        
if __name__ == '__main__':

    from sqlite3 import connect
    
    with connect('eve.db') as db_conn:
        m = Map()
        print("Loading data from SDE...")
        m.from_sde(db_conn)
    print("Writing output")
    with open('output.json', 'wb') as f:
        f.write(m.to_json())