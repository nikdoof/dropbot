from unittest import TestCase
from dropbot.bot import DropBot


class DropBotTestCase(TestCase):

    def setUp(self):
        self.bot = DropBot('test@test.com', 'testpassword')

    def test_simple_bot(self):
        self.assertIsNotNone(self.bot)

    def test_system_picker(self):
        self.assertEquals(self.bot._system_picker('Jita'), 30000142)
        self.assertEquals(self.bot._system_picker('Jit'), 30000142)
        self.assertIs(type(self.bot._system_picker('J')), str)
        self.assertEqual(self.bot._system_picker('J'), 'More than 10 systems match J, please provide a more complete name')
        self.assertEqual(self.bot._system_picker('GE-'), 'Did you mean: GE-94X, GE-8JV?')
        self.assertEqual(self.bot._system_picker('asdasd'), 'No systems found matching asdasd')

    def test_get_evecentral_price(self):
        self.assertIs(self.bot._get_evecentral_price(1,1), None)
        self.assertIs(type(self.bot._get_evecentral_price(22430, 30000142)), tuple)