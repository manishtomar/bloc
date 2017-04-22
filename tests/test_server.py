"""
Tests for :module:`bloc.server`
"""

import json
import operator

from twisted.internet.task import Clock
from twisted.trial.unittest import SynchronousTestCase
from twisted.web.http import Headers, Request
from twisted.web.test.requesthelper import DummyChannel

from bloc.server import (
    SettlingGroup, NotSettled, extract_client, HeartbeatingClients, Bloc)


class SettlingGroupTests(SynchronousTestCase):
    """
    Tests for :func:`bloc.SettlingGroup`
    """

    def setUp(self):
        self.clock = Clock()
        self.g = SettlingGroup(self.clock, 10)

    def _check_settled(self, length):
        self.assertTrue(self.g.settled)
        self.assertEqual(len(self.g), length)

    def test_add_and_settle(self):
        """
        Add a member and see if it settles after 10 seconds
        """
        self.g.add('m1')
        self.assertFalse(self.g.settled)
        self.clock.advance(10)
        self._check_settled(1)
        self.assertEqual(self.g.index_of('m1'), 1)

    def test_add_remove_before_timer(self):
        """
        Add members, move the clock, remove one member and check
        if it settles after 10 seconds has passed from the last removal
        """
        self.g.add('m1')
        self.g.add('m2')
        self.assertFalse(self.g.settled)

        self.clock.advance(5)
        self.assertFalse(self.g.settled)
        self.g.remove('m1')
        self.assertFalse(self.g.settled)

        # Still not settled since timer got reset
        self.clock.advance(6)
        self.assertFalse(self.g.settled)

        self.clock.advance(4)
        self._check_settled(1)
        self.assertEqual(self.g.index_of('m2'), 1)

    def test_add_existing(self):
        """
        Adding existing member to a settled group does nothing. The group
        remains settled
        """
        self.test_add_and_settle()
        self.g.add("m1")
        self._check_settled(1)

    def test_remove_error(self):
        """
        Removing unknown member raises `KeyError`
        """
        self.assertRaises(KeyError, self.g.remove, "bad")

    def test_notsettled_error(self):
        """
        Getting index when not settled raises `NotSettled` error
        """
        self.g.add('m1')
        self.assertRaises(NotSettled, self.g.index_of, 'm1')


def request_with_session(sid, method="GET"):
    r = Request(DummyChannel(), False)
    r.method = method
    r.requestHeaders = Headers({'Bloc-Session-ID': [sid]})
    return r


class ExtractClientTests(SynchronousTestCase):

    def test_with_header(self):
        self.assertEqual(extract_client(request_with_session('s1')), 's1')

    def test_without_header(self):
        self.assertIsNone(extract_client(Request(DummyChannel(), False)))


class HeartbeatingClientsTests(SynchronousTestCase):
    """
    Tests for :obj:`HeartbeatingClients`
    """
    def setUp(self):
        self.clock = Clock()
        self.removed_clients = set()
        self.c = HeartbeatingClients(self.clock, 5, 1, self.removed_clients.add)

    def test_all(self):
        """
        Only clients that has not hearbeat will be removed. Others will remain
        """
        self.c.startService()
        self.c.heartbeat("c1")
        self.c.heartbeat("c2")
        self.clock.advance(1)
        self.c.heartbeat("c3")
        self.clock.pump([1] * 4)
        self.c.heartbeat("c3")
        self.clock.pump([1] * 2)
        self.assertNotIn("c1", self.c)
        self.assertNotIn("c2", self.c)
        self.assertEqual(self.removed_clients, set(["c1", "c2"]))

    def test_remove(self):
        """
        Client removed via `self.remove` is not checked anymore
        """
        self.c.startService()
        self.c.heartbeat("c1")
        self.c.heartbeat("c2")
        self.c.remove("c1")
        self.assertNotIn("c1", self.c)
        self.clock.pump([1] * 6)
        self.assertNotIn("c1", self.removed_clients)


class BlocTests(SynchronousTestCase):
    """
    Tests for :obj:`Bloc`
    """
    def setUp(self):
        self.clock = Clock()
        self.b = Bloc(self.clock, 3, 10)
        self.b.startService()

    def test_get_index_settling(self):
        """
        `get_index` heartbeats and adds client to the group and returns settling
        json if group is settling
        """
        r = self.b.get_index(request_with_session('c'))
        self.assertIn("c", self.b._group)
        self.assertIn("c", self.b._clients)
        self.assertEqual(json.loads(r.decode("utf-8")), {'status': 'SETTLING'})

    def test_get_index_settled(self):
        """
        `get_index` heartbeats and adds client to the group and returns settled
        json with index and total if group has settled
        """
        for i in range(int(11 / 3) + 1):
            self.b.get_index(request_with_session('s'))
            self.clock.pump([1] * 3)
        r = self.b.get_index(request_with_session('s'))
        self.assertEqual(
            json.loads(r.decode("utf-8")),
            {'status': 'SETTLED', 'index': 1, 'total': 1})

    def test_disconnect(self):
        """
        Disconnects session by removing it
        """
        self.b.get_index(request_with_session('new'))
        r = self.b.cancel_session(request_with_session("new", "DELETE"))
        self.assertEqual(r.decode("utf-8"), "{}")
        self.assertNotIn('new', self.b._group)
        self.assertNotIn('new', self.b._clients)

    def test_timeout_removed(self):
        """
        On timeout HeartbeatingClients removes client from SettlingGroup
        """
        self.b.get_index(request_with_session('s'))
        self.clock.pump([1] * 4)
        self.assertNotIn("s", self.b._group)
        self.assertNotIn("s", self.b._clients)
