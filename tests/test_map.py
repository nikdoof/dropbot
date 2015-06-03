from unittest import TestCase
from dropbot.map import Map, ship_class_to_range
import pkgutil

class MapTestCase(TestCase):

    def setUp(self):
        self.map = Map.from_json(pkgutil.get_data('dropbot', 'data/map.json'))

    def test_load_from_package_data(self):
        """Check the package data can be correctly loaded into the map"""
        m = Map.from_json(pkgutil.get_data('dropbot', 'data/map.json'))
        self.assertIsNotNone(m)

    def test_get_system_name(self):
        """Test looking up system names from IDs"""
        self.assertEquals(self.map.get_system_name(123), None)
        self.assertEqual(self.map.get_system_name(30000142), 'Jita')

    def test_get_system_id(self):
        """Test looking up system ID by name"""
        self.assertEqual(self.map.get_system_id('Llamatron'), None)
        self.assertEqual(self.map.get_system_id('Jita'), 30000142)

    def test_get_systems(self):
        """Check partial matching of system names works correctly"""
        self.assertEquals(len(self.map.get_systems('Jita')), 1)
        self.assertEquals(len(self.map.get_systems('Ji')), 7)
        self.assertEquals(len(self.map.get_systems('J')), 2765)
        self.assertEquals(len(self.map.get_systems('123435345345')), 0)
        self.assertEquals(len(self.map.get_systems('jita')), 1)
        self.assertEquals(len(self.map.get_systems('JITA')), 1)
        self.assertEquals(len(self.map.get_systems('JiTa')), 1)

    def test_system_distance(self):
        """Test the distance calculator"""
        self.assertEqual(self.map.system_distance(30000142, 30000144), 2.10268108033618)
        self.assertEqual(self.map.system_distance(30000142, 30000222), 9.334275248404591)
        self.assertEqual(self.map.system_distance(30000142, 30000536), 39.15289747780095)
        self.assertRaises(Exception, self.map.system_distance, (1, 2))

    def test_route_gate(self):
        """Test the gate routing system"""
        r = self.map.route_gate(30001161, 30001198)
        self.assertEqual(len(r), 9)
        self.assertListEqual(r, [30001161, 30001158, 30001160, 30001154, 30001157, 30001155, 30001156, 30001162, 30001198])

    def test_route_jump(self):
        pass

    def test_route_jump_distance(self):
        pass

    def test_route_jump_isotopes(self):
        pass

    def test_jump_fatigue_standard(self):
        """Test jump fatigue calculator, 4.119ly jump, no bonus"""
        sys1 = self.map.get_system_id('U-HVIX')
        sys2 = self.map.get_system_id('V-IUEL')
        cooldown, new_fatigue = self.map.jump_fatigue(0, sys1, sys2)
        self.assertEqual(cooldown, 5.12)
        self.assertEqual(new_fatigue, 51.19)

    def test_jump_fatigue_covertops(self):
        """Test jump fatigue calculator, 4.119ly jump, covertops being bridged by titan"""
        sys1 = self.map.get_system_id('U-HVIX')
        sys2 = self.map.get_system_id('V-IUEL')
        cooldown, new_fatigue = self.map.jump_fatigue(0, sys1, sys2, ship_class='covertops')
        self.assertEqual(cooldown, 5.12)
        self.assertEqual(new_fatigue, 51.19)

    def test_jump_fatigue_covertops_covertcyno(self):
        """Test jump fatigue calculator, 4.119ly jump, covertops being bridged by blops"""
        sys1 = self.map.get_system_id('U-HVIX')
        sys2 = self.map.get_system_id('V-IUEL')
        cooldown, new_fatigue = self.map.jump_fatigue(0, sys1, sys2, ship_class='covertops', jump_type='covert')
        self.assertEqual(cooldown, 3.06)
        self.assertEqual(new_fatigue, 30.59)

    def test_route_jump_fatigue_covertops_covertcyno(self):
        """Test jump fatigue calculator, 4.119ly jump, covertops being bridged by blops"""
        sys1 = self.map.get_system_id('U-HVIX')
        sys2 = self.map.get_system_id('V-IUEL')
        res = self.map.route_jump_fatigue([sys1, sys2], 0, ship_class='covertops', jump_type='covert')
        self.assertListEqual(res, [
            {'source': sys1, 'target': sys2, 'cooldown': 3.06, 'fatigue': 30.59,}
        ])

    def test_route_jump_fatigue_covertops_covertcyno_two_jumps(self):
        """Test route jump fatigue calculator, covertops being bridged by blops for two jumps"""
        sys1 = self.map.get_system_id('U-HVIX')
        sys2 = self.map.get_system_id('RMOC-W')
        sys3 = self.map.get_system_id('Podion')
        res = self.map.route_jump_fatigue([sys1, sys2, sys3], 0, ship_class='covertops', jump_type='covert')
        self.assertListEqual(res, [
            {'source': sys1, 'target': sys2, 'cooldown': 4.77, 'fatigue': 47.72, },
            {'source': sys2, 'target': sys3, 'cooldown': 4.77, 'fatigue': 222.91, },
        ])

    def test_route_jump_fatigue_covertops_covertcyno_three_jumps(self):
        """Test route jump fatigue calculator, covertops being bridged by blops for three jumps"""
        sys1 = self.map.get_system_id('U-HVIX')
        sys2 = self.map.get_system_id('RMOC-W')
        sys3 = self.map.get_system_id('Podion')
        sys4 = self.map.get_system_id('Hothomouh')
        res = self.map.route_jump_fatigue([sys1, sys2, sys3, sys4], 0, ship_class='covertops', jump_type='covert')
        self.assertListEqual(res, [
            {'source': sys1, 'target': sys2, 'cooldown': 4.77, 'fatigue': 47.72, },
            {'source': sys2, 'target': sys3, 'cooldown': 4.77, 'fatigue': 222.91, },
            {'source': sys3, 'target': sys4, 'cooldown': 22.29, 'fatigue': 786.39, },
        ])

    def test_neighbors_gate(self):
        pass

    def test_neighbors_jump(self):
        pass

    def test_jump_bridge_addition(self):
        """Test addition of a jump bridge"""
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
        The maximum jump range of a JF is 10LY.
        """
        self.assertEquals(ship_class_to_range('jumpfreighter', 5), 10)

    def test_jump_distance_blackops(self):
        """
        The maximum jump range of a bloops is 8LY.
        """
        self.assertEquals(ship_class_to_range('blackops', 5), 8)

    def test_jump_distance_skills_titan(self):
        """
        Test the correct range for titans for each JDC skill level
        """
        ship_ranges = [2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
        for skill in range(0, 6):
            jump_range = ship_ranges[skill]
            self.assertEquals(ship_class_to_range('titan', skill), jump_range)

    def test_jump_distance_skills_supercarrier(self):
        """
        Test the correct range for titans for each JDC skill level
        """
        ship_ranges = [2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
        for skill in range(0, 6):
            jump_range = ship_ranges[skill]
            self.assertEquals(ship_class_to_range('supercarrier', skill), jump_range)

    def test_jump_distance_skills_carrier(self):
        """
        Test the correct range for supercarriers for each JDC skill level
        """
        ship_ranges = [2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
        for skill in range(0, 6):
            jump_range = ship_ranges[skill]
            self.assertEquals(ship_class_to_range('carrier', skill), jump_range)

    def test_jump_distance_skills_dreadnought(self):
        """
        Test the correct range for dreadnoughts for each JDC skill level
        """
        ship_ranges = [2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
        for skill in range(0, 6):
            jump_range = ship_ranges[skill]
            self.assertEquals(ship_class_to_range('dreadnought', skill), jump_range)

    def test_jump_distance_skills_industrial(self):
        """
        Test the correct range for industrials for each JDC skill level
        """
        ship_ranges = [2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
        for skill in range(0, 6):
            jump_range = ship_ranges[skill]
            self.assertEquals(ship_class_to_range('industrial', skill), jump_range)

    def test_jump_distance_skills_jumpfreighter(self):
        """
        Test the correct range for jump freighters for each JDC skill level
        """
        ship_ranges = [5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        for skill in range(0, 6):
            jump_range = ship_ranges[skill]
            self.assertEquals(ship_class_to_range('jumpfreighter', skill), jump_range)
