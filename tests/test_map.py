from unittest import TestCase
from dropbot.map import Map, ship_class_to_range
import pkgutil

class MapTestCase(TestCase):

    def setUp(self):
        self.map = Map.from_json(pkgutil.get_data('dropbot', 'data/map.json'))

    def test_load_from_package_data(self):
        m = Map.from_json(pkgutil.get_data('dropbot', 'data/map.json'))
        self.assertIsNotNone(m)

    def test_get_system_name(self):
        self.assertEquals(self.map.get_system_name(123), None)
        self.assertEqual(self.map.get_system_name(30000142), 'Jita')

    def test_get_system_id(self):
        self.assertEqual(self.map.get_system_id('Llamatron'), None)
        self.assertEqual(self.map.get_system_id('Jita'), 30000142)

    def test_get_systems(self):
        self.assertEquals(len(self.map.get_systems('Jita')), 1)
        self.assertEquals(len(self.map.get_systems('Ji')), 7)
        self.assertEquals(len(self.map.get_systems('J')), 2660)
        self.assertEquals(len(self.map.get_systems('123435345345')), 0)
        self.assertEquals(len(self.map.get_systems('jita')), 1)
        self.assertEquals(len(self.map.get_systems('JITA')), 1)
        self.assertEquals(len(self.map.get_systems('JiTa')), 1)

    def test_system_distance(self):
        self.assertEqual(self.map.system_distance(30000142, 30000144), 2.10268108033618)
        self.assertEqual(self.map.system_distance(30000142, 30000222), 9.334275248404591)
        self.assertEqual(self.map.system_distance(30000142, 30000536), 39.15289747780095)
        self.assertRaises(Exception, self.map.system_distance, (1, 2))

    def test_route_gate(self):
        r = self.map.route_gate(30001161, 30001198)
        self.assertEqual(len(r), 9)
        self.assertListEqual(r, [30001161, 30001158, 30001160, 30001154, 30001157, 30001155, 30001156, 30001162, 30001198])

    def test_route_jump(self):
        pass

    def test_route_jump_distance(self):
        pass

    def test_route_jump_isotopes(self):
        pass

    def test_neighbors_gate(self):
        pass

    def test_neighbors_jump(self):
        pass

    def test_jump_bridge_addition(self):
        # HED-GP to GE-8
        self.assertGreater(len(self.map.route_gate(30001161, 30001198)), 2)
        self.map.add_jumpbridge(30001161, 30001198)
        r = self.map.route_gate(30001161, 30001198)
        self.assertEqual(len(r), 2)
        self.assertListEqual(r, [30001161, 30001198])

    # Jump ranges taken from devblog:
    # http://community.eveonline.com/news/dev-blogs/phoebe-travel-change-update/

    def test_jump_distance_titan(self):
        """
        The maximum jump range of a titan is 5LY.
        """
        self.assertEquals(ship_class_to_range('titan', 5), 5)

    def test_jump_distance_supercarrier(self):
        """
        The maximum jump range of a supercarrier is 5LY.
        """
        self.assertEquals(ship_class_to_range('supercarrier', 5), 5)

    def test_jump_distance_carrier(self):
        """
        The maximum jump range of a carrier is 5LY.
        """
        self.assertEquals(ship_class_to_range('carrier', 5), 5)

    def test_jump_distance_dreadnought(self):
        """
        The maximum jump range of a dread is 5LY.
        """
        self.assertEquals(ship_class_to_range('dreadnought', 5), 5)

    def test_jump_distance_industrial(self):
        """
        The maximum jump range of a rorqual is 5LY.
        """
        self.assertEquals(ship_class_to_range('industrial', 5), 5)

    def test_jump_distance_jumpfreighter(self):
        """
        The maximum jump range of a JF is 5LY.
        """
        self.assertEquals(ship_class_to_range('jumpfreighter', 5), 10)

    def test_jump_distance_blackops(self):
        """
        The maximum jump range of a bloops is 8LY.
        """
        self.assertEquals(ship_class_to_range('blackops', 5), 8)
