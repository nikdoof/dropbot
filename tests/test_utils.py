import mock
from unittest import TestCase
from dropbot.utils import decimal_minutes_to_hms


class DecimalToHMSTest(TestCase):
    """
    Tests the decimal_minutes_to_hms function
    """

    def test_seconds_only(self):
        """Check seconds are calculated correctly"""
        self.assertEqual(decimal_minutes_to_hms(0.5), '30s')
        self.assertEqual(decimal_minutes_to_hms(0.75), '45s')
        self.assertEqual(decimal_minutes_to_hms(0.25), '15s')
        self.assertEqual(decimal_minutes_to_hms(0.56), '34s')
        self.assertEqual(decimal_minutes_to_hms(0.57), '34s')
        self.assertEqual(decimal_minutes_to_hms(0.58), '35s')

    def test_full_minutes(self):
        """Check minutes are correclty output"""
        self.assertEqual(decimal_minutes_to_hms(1), '1m')
        self.assertEqual(decimal_minutes_to_hms(10), '10m')
        self.assertEqual(decimal_minutes_to_hms(30), '30m')

    def test_minutes_and_seconds(self):
        """Check minutes and seconds are correctly output"""
        self.assertEqual(decimal_minutes_to_hms(1.5), '1m 30s')
        self.assertEqual(decimal_minutes_to_hms(59.5), '59m 30s')
        self.assertEqual(decimal_minutes_to_hms(5.25), '5m 15s')

    def test_full_hours(self):
        """Check hours are correctly output"""
        self.assertEqual(decimal_minutes_to_hms(60), '1h')
        self.assertEqual(decimal_minutes_to_hms(120), '2h')
        self.assertEqual(decimal_minutes_to_hms(1440), '24h')

    def test_hour_minutes_and_seconds(self):
        """Check HMS are correctly output in the correct situations"""
        self.assertEqual(decimal_minutes_to_hms(61.5), '1h 1m 30s')

    def test_partial_seconds(self):
        """Check that partial seconds are rounded to the nearest second"""
        self.assertEqual(decimal_minutes_to_hms(4.56), '4m 34s')
        self.assertEqual(decimal_minutes_to_hms(4.57), '4m 34s')
        self.assertEqual(decimal_minutes_to_hms(4.58), '4m 35s')

    def test_large_numbers(self):
        self.assertEqual(decimal_minutes_to_hms(300000000000000), '5000000000000h')
        self.assertEqual(decimal_minutes_to_hms(3000023423234.4), '50000390387h 14m 24s')

    def test_negative_numbers(self):
        self.assertEqual(decimal_minutes_to_hms(-1), '1m')
        self.assertEqual(decimal_minutes_to_hms(-1.2), '1m 12s')

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            decimal_minutes_to_hms('dsd')
        with self.assertRaises(ValueError):
            decimal_minutes_to_hms(mock.Mock())