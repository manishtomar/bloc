"""
Tests for :module:`participate`
"""

import json
import operator

from twisted.internet.task import Clock
from twisted.trial.unittest import SynchronousTestCase
from twisted.web.http import Headers, Request
from twisted.web.test.requesthelper import DummyChannel

from participate import (
    GroupParticipants, NotAllocated, Participate, extract_client)


class GroupParticipantsTests(SynchronousTestCase):
    """
    Tests for :func:`participate.GroupParticipants`
    """

    def setUp(self):
        self.clock = Clock()
        self.p = GroupParticipants(self.clock, 10)

    def _check_allocated(self, length):
        self.assertTrue(self.p.allocated)
        self.assertEqual(len(self.p), length)

    def test_add_part_and_settle(self):
        """
        Add a participant and see if it settles after 10 seconds
        """
        self.p.add_participant('p1')
        self.assertFalse(self.p.allocated)
        self.clock.advance(10)
        self._check_allocated(1)
        self.assertEqual(self.p['p1'], 1)

    def test_add_remove_part_before_timer(self):
        """
        Add participants, move the clock, remove one participant and check
        if it settles after 10 seconds has passed from the last removal
        """
        self.p.add_participant('p1')
        self.p.add_participant('p2')
        self.assertFalse(self.p.allocated)

        self.clock.advance(5)
        self.assertFalse(self.p.allocated)
        self.p.remove_participants(['p1'])
        self.assertFalse(self.p.allocated)

        # Still not allocated since timer got reset
        self.clock.advance(6)
        self.assertFalse(self.p.allocated)

        self.clock.advance(4)
        self._check_allocated(1)
        self.assertEqual(self.p['p2'], 1)

    def test_not_allocated_error(self):
        """
        Getting index when not allocated raises `NotAllocated` error
        """
        self.p.add_participant('p1')
        self.assertRaises(NotAllocated, operator.getitem, self.p, 'p1')


def request_with_session(sid, method="GET"):
    r = Request(DummyChannel(), False)
    r.method = method
    r.requestHeaders = Headers({'X-Session-ID': [sid]})
    return r


class ExtractClientTests(SynchronousTestCase):

    def test_with_header(self):
        self.assertEqual(extract_client(request_with_session('s1')), 's1')

    def test_without_header(self):
        self.assertIsNone(extract_client(Request(DummyChannel(), False)))


class FakeGroup(object):
    def __init__(self, *a):
        self.items = {}
        self.allocated = False
    def add_participant(self, p):
        self.items[p] = len(self.items) + 1
    def remove_participants(self, ps):
        for p in ps:
            del self.items[p]
    def __getitem__(self, p):
        return self.items[p]
    def __len__(self):
        return len(self.items)


class ParticipateTests(SynchronousTestCase):
    """
    Tests for :obj:`Participate`
    """
    def setUp(self):
        self.clock = Clock()
        self.p = Participate(self.clock, 3, 10, GroupParticipants=FakeGroup)

    def test_get_index_allocating(self):
        """
        `get_index` returns allocating json if group is allocating
        """
        self.p._group.allocated = False
        r = self.p.get_index(request_with_session('s'))
        self.assertEqual(json.loads(r), {'status': 'ALLOCATING'})

    def test_get_index_allocated(self):
        """
        `get_index` returns allocated json with index and total if group
        is allocated
        """
        self.p._group.allocated = False
        self.p._group.items = {'s': 1}
        r = self.p.get_index(request_with_session('s'))
        self.assertEqual(
            json.loads(r),
            {'status': 'ALLOCATED', 'index': 1, 'total': 1})

    def test_get_index_new_client(self):
        """
        `get_index` adds new client to the group
        """
        self.p.get_index(request_with_session('s'))
        self.assertEqual(self.p._group.items.keys(), ['s'])

    def test_get_index_existing_client(self):
        """
        `get_index` stores clock seconds for existing client
        """
        # this will create and heartbeat it
        self.p.get_index(request_with_session('new'))
        self.assertEqual(self.p._clients['new'], 0)
        self.clock.advance(8)
        # this will heartbeat
        self.p.get_index(request_with_session('new'))
        self.assertEqual(self.p._clients['new'], 8)

    def test_timeout(self):
        """
        Times out client after inactive time
        """
        self.p.get_index(request_with_session('new'))
        self.assertIn('new', self.p._group.items)
        self.clock.pump([1] * 4)
        self.assertNotIn('new', self.p._group.items)

    def test_client_active(self):
        """
        If client sends request within interval, it remains active
        """
        self.p.get_index(request_with_session('new'))
        self.assertIn('new', self.p._group.items)
        self.clock.pump([1] * 2)
        self.p.get_index(request_with_session('new'))
        self.assertIn('new', self.p._group.items)

    def test_disconnect(self):
        """
        Disconnects session by removing it
        """
        self.p.get_index(request_with_session('new'))
        self.assertIn('new', self.p._group.items)
        r = self.p.cancel_session(request_with_session("new", "POST"))
        self.assertEqual(r, "{}")
        self.assertNotIn('new', self.p._group.items)
        self.assertNotIn('new', self.p._clients)

    def test_disconnect_unknown(self):
        """
        /disconnect does nothing if session is not found
        """
        r = self.p.cancel_session(request_with_session("unknown", "POST"))
        self.assertEqual(r, "{}")
        self.assertNotIn('unknown', self.p._group.items)
        self.assertNotIn('unknown', self.p._clients)

    def test_disconnect_no_header(self):
        """
        /disconnect does nothing if session info is not there in header
        """
        r = self.p.cancel_session(Request(DummyChannel(), False))
        self.assertEqual(r, "{}")
