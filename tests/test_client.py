"""
Tests for :module:`client`
"""

import json
import operator

import mock

from treq.testing import StubTreq

from twisted.internet.defer import Deferred
from twisted.internet.task import Clock
from twisted.trial.unittest import SynchronousTestCase
from twisted.web.http import Headers, Request
from twisted.web.resource import Resource
from twisted.web.test.requesthelper import DummyChannel
from twisted.web.util import DeferredResource

from bloc.client import ParticipateClient
from bloc.server import extract_client


class IndexResource(Resource):
    isLeaf = True
    def __init__(self, test):
        self.test = test
        self.resp = None
        self.code = 200
        self.exp_session_id = None
    def render_GET(self, request):
        self.test.assertEqual(request.path, "/index")
        self.test.assertEqual(extract_client(request), self.exp_session_id)
        request.setResponseCode(self.code)
        return json.dumps(self.resp)


class ParticipateClientTests(SynchronousTestCase):
    """
    Tests for :obj:`client.ParticipateClient`
    """

    def setUp(self):
        self.clock = Clock()
        self.resource = IndexResource(self)
        self.resource.exp_session_id = 'sid'
        self.client = ParticipateClient(
            self.clock, 'http://url', 10, 3,
            treq=StubTreq(self.resource), session_id='sid')

    def test_allocated(self):
        """
        When getting index returns ALLOCATED then it is set and is returned
        in `get_index_total`
        """
        self.resource.resp = {"status": "ALLOCATED", "index": 1, "total": 1}
        self.client.start()
        self.assertEqual(self.client.get_index_total(), (1, 1))

    def test_allocating(self):
        """
        When getting index returns ALLOCATING, then get_index_total returns
        None
        """
        self.resource.resp = {"status": "ALLOCATING"}
        self.client.start()
        self.assertIsNone(self.client.get_index_total())

    def test_get_errors(self):
        """
        If get index errors, then get_index_total will return None
        """
        self.resource.code = 500
        self.client.start()
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
        self.resource.resp = {"status": "ALLOCATING"}
        self.client.start()
        self.assertIsNone(self.client.get_index_total())
        # allocated
        self.resource.resp = {"status": "ALLOCATED", "index": 1, "total": 3}
        self.clock.advance(10)
        self.assertEqual(self.client.get_index_total(), (1, 3))
        # errors
        self.resource.code = 500
        self.clock.advance(10)
        self.assertIsNone(self.client.get_index_total())
        # allocating
        self.resource.code = 200
        self.resource.resp = {"status": "ALLOCATING"}
        self.clock.advance(10)
        self.assertIsNone(self.client.get_index_total())
        # allocated
        self.resource.resp = {"status": "ALLOCATED", "index": 3, "total": 4}
        self.clock.advance(10)
        self.assertEqual(self.client.get_index_total(), (3, 4))
