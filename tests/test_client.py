"""
Tests for :module:`client`
"""

import json
import operator

import mock

from treq.testing import RequestSequence, StringStubbingResource, StubTreq, HasHeaders

from twisted.internet.defer import Deferred
from twisted.internet.task import Clock
from twisted.trial.unittest import SynchronousTestCase
from twisted.web.http import Headers, Request
from twisted.web.resource import Resource
from twisted.web.test.requesthelper import DummyChannel
from twisted.web.util import DeferredResource

from bloc.client import BlocClient


class BlocClientTests(SynchronousTestCase):
    """
    Tests for :obj:`client.BlocClient`
    """

    def setUp(self):
        self.clock = Clock()
        self.client = BlocClient(self.clock, 'http://url', 10, 3, session_id='sid')

    def setup_treq(self, code=200, body={}):
        self.stubs = RequestSequence(
            [(("get", "http://url/index", {}, HasHeaders({"X-Session-ID": ["sid"]}), b''),
              (code, {}, json.dumps(body)))],
            self.fail)
        self.client.treq = StubTreq(StringStubbingResource(self.stubs))

    def test_allocated(self):
        """
        When getting index returns ALLOCATED then it is set and is returned
        in `get_index_total`
        """
        self.setup_treq(body={"status": "ALLOCATED", "index": 1, "total": 1})
        self.client.start()
        with self.stubs.consume(self.fail):
            self.assertEqual(self.client.get_index_total(), (1, 1))
            self.assertTrue(self.client._allocated)

    def test_allocating(self):
        """
        When getting index returns ALLOCATING, then get_index_total returns
        None
        """
        self.setup_treq(body={"status": "ALLOCATING"})
        self.client.start()
        with self.stubs.consume(self.fail):
            self.assertIsNone(self.client.get_index_total())

    def test_get_errors(self):
        """
        If get index errors, then get_index_total will return None
        """
        self.setup_treq(code=500)
        self.client.start()
        with self.stubs.consume(self.fail):
            self.assertIsNone(self.client.get_index_total())

    def test_get_times_out(self):
        """
        If get index times out then get_index_total will return None
        """
        # lets start with allocated
        self.test_allocated()
        # setup client that does not return
        self.client.treq = StubTreq(DeferredResource(Deferred()))
        # next heartbeat to get index again
        self.clock.advance(10)
        # no response
        self.clock.advance(3)
        self.assertIsNone(self.client.get_index_total())

    def test_sequence(self):
        """
        Test sequence of changes from server:
        TODO: this should probably be done via hypothesis
        ALLOCATING -> ALLOCATED -> ERRORS -> ALLOCATING -> ALLOCATED
        """
        # allocating
        self.setup_treq(body={"status": "ALLOCATING"})
        self.client.start()
        with self.stubs.consume(self.fail):
            self.assertIsNone(self.client.get_index_total())

        # allocated
        self.setup_treq(body={"status": "ALLOCATED", "index": 1, "total": 3})
        self.clock.advance(10)
        with self.stubs.consume(self.fail):
            self.assertEqual(self.client.get_index_total(), (1, 3))

        # errors
        self.setup_treq(code=500)
        self.clock.advance(10)
        with self.stubs.consume(self.fail):
            self.assertIsNone(self.client.get_index_total())

        # allocating
        self.setup_treq(body={"status": "ALLOCATING"})
        self.clock.advance(10)
        with self.stubs.consume(self.fail):
            self.assertIsNone(self.client.get_index_total())

        # allocated
        self.setup_treq(body={"status": "ALLOCATED", "index": 3, "total": 4})
        self.clock.advance(10)
        with self.stubs.consume(self.fail):
            self.assertEqual(self.client.get_index_total(), (3, 4))
