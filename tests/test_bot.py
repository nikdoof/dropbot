import os
import unittest
import mock
from unittest import TestCase
from dropbot.bot import DropBot


class DropBotTestCase(TestCase):

    def setUp(self):
        self.bot = DropBot('test@test.com', 'testpassword')

    def call_command(self, command, args=[]):
        """Fakes a call to a bot command"""
        msg = {'type': 'groupchat'}
        return self.bot.call_command(command, args, msg)

    def test_simple_bot(self):
        self.assertIsNotNone(self.bot)

    def test_system_picker(self):
        self.assertEquals(self.bot._system_picker('Jita'), 30000142)
        self.assertEquals(self.bot._system_picker('Jit'), 30000142)
        self.assertIs(type(self.bot._system_picker('J')), str)
        self.assertEqual(self.bot._system_picker('J'), 'More than 10 systems match J, please provide a more complete name')
        self.assertEqual(self.bot._system_picker('GE-'), 'Did you mean: GE-94X, GE-8JV?')
        self.assertEqual(self.bot._system_picker('asdasd'), 'No systems found matching asdasd')

    @unittest.skipIf(os.environ.get('NO_NETWORK', '0') == '1', 'No networking, skipping test')
    def test_get_evecentral_price(self):
        self.assertIs(self.bot._get_evecentral_price(1,1), None)
        self.assertIs(type(self.bot._get_evecentral_price(22430, 30000142)), tuple)

    def test_cmd_help(self):
        res = self.call_command('help')
        self.assertIsInstance(res, tuple)
        self.assertIsInstance(res[0], basestring)

    @unittest.skipIf(os.environ.get('NO_NETWORK', '0') == '1', 'No networking, skipping test')
    def test_cmd_bestprice(self):
        res = self.call_command('bestprice', ['rifter'])
        self.assertIsInstance(res, tuple)
        self.assertIsInstance(res[0], basestring)

    @unittest.skipIf(os.environ.get('NO_NETWORK', '0') == '1', 'No networking, skipping test')
    def test_cmd_price(self):
        res = self.call_command('price', args=['jita', 'rifter'])
        self.assertIsInstance(res, tuple)
        self.assertIsInstance(res[0], basestring)

    @unittest.skipIf(os.environ.get('NO_NETWORK', '0') == '1', 'No networking, skipping test')
    def test_cmd_jita(self):
        res = self.call_command('jita', ['rifter'])
        self.assertIsInstance(res, tuple)
        self.assertIsInstance(res[0], basestring)

    @unittest.skipIf(os.environ.get('NO_NETWORK', '0') == '1', 'No networking, skipping test')
    def test_cmd_amarr(self):
        res = self.call_command('amarr', ['rifter'])
        self.assertIsInstance(res, tuple)
        self.assertIsInstance(res[0], basestring)

    @unittest.skipIf(os.environ.get('NO_NETWORK', '0') == '1', 'No networking, skipping test')
    def test_cmd_rens(self):
        res = self.call_command('rens', ['rifter'])
        self.assertIsInstance(res, tuple)
        self.assertIsInstance(res[0], basestring)

    @unittest.skipIf(os.environ.get('NO_NETWORK', '0') == '1', 'No networking, skipping test')
    def test_cmd_dodixie(self):
        res = self.call_command('dodixie', ['rifter'])
        self.assertIsInstance(res, tuple)
        self.assertIsInstance(res[0], basestring)

    @unittest.skipIf(os.environ.get('NO_NETWORK', '0') == '1', 'No networking, skipping test')
    def test_cmd_uh(self):
        res = self.call_command('uh', ['rifter'])
        self.assertIsInstance(res, tuple)
        self.assertIsInstance(res[0], basestring)

    @unittest.skipIf(os.environ.get('NO_NETWORK', '0') == '1', 'No networking, skipping test')
    def test_cmd_hek(self):
        res = self.call_command('hek', ['rifter'])
        self.assertIsInstance(res, tuple)
        self.assertIsInstance(res[0], basestring)

    def test_cmd_r(self):
        pass

    def test_cmd_redditimg(self):
        pass

    @unittest.skipIf(os.environ.get('NO_NETWORK', '0') == '1', 'No networking, skipping test')
    def test_cmd_kos(self):
        res = self.call_command('kos', ['Palkark'])
        self.assertIsInstance(res, tuple)
        self.assertIsInstance(res[0], basestring)

    def test_cmd_range(self):
        res = self.call_command('range', ['U-HVIX'])
        self.assertIsInstance(res, tuple)
        self.assertIsInstance(res[0], basestring)

    def test_cmd_route(self):
        res = self.call_command('route', ['Jita', 'Amarr'])
        self.assertIsInstance(res, tuple)
        self.assertIsInstance(res[0], basestring)

    def test_cmd_addjb(self):
        res = self.call_command('addjb', ['Jita', 'Amarr'])
        self.assertIsInstance(res, tuple)
        self.assertIsInstance(res[0], basestring)
        self.assertEqual(res[0], 'Done')

    def test_cmd_listjbs(self):
        res = self.call_command('listjbs')
        self.assertIsInstance(res, tuple)
        self.assertIsNone(res[0], None)

        self.call_command('addjb', ['Jita', 'Amarr'])
        res = self.call_command('listjbs')
        self.assertIsInstance(res, tuple)
        self.assertIsInstance(res[0], basestring)

    def test_cmd_mapstats(self):
        res = self.call_command('mapstats')
        self.assertIsInstance(res, tuple)
        self.assertIsInstance(res[0], basestring)

    def test_cmd_hit(self):
        pass

    def test_cmd_jump(self):
        pass

    @unittest.skipIf(os.environ.get('NO_NETWORK', '0') == '1', 'No networking, skipping test')
    def test_cmd_id(self):
        pass

    @unittest.skipIf(os.environ.get('NO_NETWORK', '0') == '1', 'No networking, skipping test')
    def test_cmd_kill(self):
        pass

    def test_cmd_mute(self):
        self.assertEqual(self.bot.kills_muted, False)
        res = self.call_command('mute')
        self.assertIsInstance(res, tuple)
        self.assertIsInstance(res[0], basestring)
        self.assertEqual(res[0], 'Killmails muted, posting will resume automatically in 30 minutes')
        self.assertEqual(self.bot.kills_muted, True)

    @unittest.skipIf(os.environ.get('NO_NETWORK', '0') == '1', 'No networking, skipping test')
    def test_cmd_nearestoffice(self):
        pass

    def test_cmd_rageping(self):
        pass

    def test_jackdaw(self):
        """
        The items in the Carnyx release can be found.
        """
        self.assertEqual(self.bot._item_picker("Jackdaw"), (u'34828', u'Jackdaw'))

    def test_carnyx_plex(self):
        self.assertEqual(self.bot._item_picker("plex"), (u"29668", "30 Day Pilot's License Extension (PLEX)"))
