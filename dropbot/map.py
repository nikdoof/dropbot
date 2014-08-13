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

isotope_usage = {
    'carrier': 1500,
    'dreadnought': 1500,
    'industrial': 1500,
    'jumpfreighter': 5000,
    'supercarrier': 1500,
    'titan': 1500,
    'blackops': 450,
}


EVE_LY = 9460000000000000  # EVE's definition of a ly in KM

def calc_distance(sys1, sys2):
    """Calculate the distance in light years between two sets of 3d coordinates"""
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

    def add_jumpbridge(self, source_id, destination_id):
        self.add_edge(source_id, destination_id, weight=1, link_type='bridge')

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
        return calc_distance(self.node[source]['coords'], self.node[destination]['coords'])

    def route_gate(self, source, destination, filter=None):
        """Route between two systems using gates (fastest)"""

        # TODO: add EVE routing options (highsec/lowsec/fastest)

        g = networkx.Graph(data=[(u, v) for u, v, d in self.edges_iter(data=True) if d['link_type'] == 'gate' or d['link_type'] == 'bridge'])
        return networkx.astar_path(self, source, destination)

    def _route_jump_fast(self, source, destination, range=None, hull=None, ship_class=None, station_only=False, avoid_systems=[]):
        """A fast but error prone route calculation between two systems using jumps"""
        print source, destination
        route = [source]
        current_system = source
        while not destination in route:
            next_distance = None
            next_system = None
            # Iterate through jump neighbour systems to find the best candidate
            for system, system_distance in self.neighbors_jump(current_system, range, hull, ship_class):
                if system['security'] >= 0.45:
                    continue
                if station_only and not system['station']:
                    continue
                if system['system_id'] in avoid_systems:
                    continue
                if system['system_id'] == destination:
                    route.append(destination)
                    return route

                # Use heuristics to identify the best candidate (one that gets us closest to the target)
                distance_to_target = self.system_distance(system['system_id'], destination)
                if distance_to_target < next_distance or not next_distance:
                    next_distance = distance_to_target
                    next_system = system['system_id']
            route.append(next_system)
            current_system = next_system
            
    def route_jump(self, source, destination, range=None, hull=None, ship_class=None, station_only=False, avoid_systems=[]):
        """Calculate a jump route between two systems"""
        closed = set()
        open = set([source])
        route = {}
        g_score = {source: 0}
        f_score = {source: g_score[source] + self.system_distance(source, destination)}
        
        while len(open):
            current = min([x for x in f_score.items() if x[0] in open], key=lambda x: x[1])[0]
            if current == destination:
            
                def build_path(route, current):
                    if current in route:
                        p = build_path(route, route[current])
                        p.append(current)
                        return p
                    return [current] 
                    
                return build_path(route, destination)
            open.remove(current)
            closed.add(current)
            for neighbor, distance in self.neighbors_jump(current, range, hull, ship_class):
                neighbor_id = neighbor['system_id']
                if neighbor_id in closed or \
                   neighbor['security'] >= 0.45 or \
                   (station_only and not neighbor['station']) or \
                   neighbor_id in avoid_systems:
                    continue
                    
                score = g_score[current] + self.system_distance(current, neighbor_id)
                if neighbor_id not in open or score < g_score[neighbor_id]:
                    route[neighbor_id] = current
                    g_score[neighbor_id] = score
                    f_score[neighbor_id] = score + self.system_distance(neighbor_id, destination)
                    if neighbor_id not in open:
                        open.add(neighbor_id)

    def route_jump_distance(self, route):
        """Calculate the total ly distance of a route"""
        source = route[0]
        ly = 0.0
        for destination in route[1:]:
            if destination == source:
                return ly
            ly += self.system_distance(source, destination)
            source = destination
        return ly
        
    def route_jump_isotopes(self, route, jfc_skill, jf_skill=None, hull=None, ship_class=None):
        """Calculate the total number of isotopes needed for a route"""
        if not hull and not ship_class:
            raise ValueError('No hull or ship class provided')
        if hull:
            ship_class = hull_classes[hull]
        if ship_class == 'jumpfreighter' and not jf_skill:
            raise ValueError('No Jump Freighter skill level provided for a jump freighter ship')
            
        multi = 1 - (.1 * jfc_skill)
        if ship_class == 'jumpfreighter':
            multi = multi * (1 - (.1 * jf_skill))
        base = isotope_usage[ship_class] *  multi
        ly = self.route_jump_distance(route) 
        return round(ly * base, 0)
              
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
              
        # Calculate the max coords for the jump radius, avoiding costly calc_distance calls
        range_x = (source['coords'][0] + (range * EVE_LY), source['coords'][0] - (range * EVE_LY))
        range_y = (source['coords'][1] + (range * EVE_LY), source['coords'][1] - (range * EVE_LY))
        range_z = (source['coords'][2] + (range * EVE_LY), source['coords'][2] - (range * EVE_LY))
        
        destinations = []
        for destination_id, destination_data in self.nodes_iter(data=True):
            if destination_data['coords'][0] > range_x[0] or destination_data['coords'][0] < range_x[1] or \
               destination_data['coords'][1] > range_y[0] or destination_data['coords'][1] < range_y[1] or \
               destination_data['coords'][2] > range_z[0] or destination_data['coords'][2] < range_z[1]:
                  continue
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
