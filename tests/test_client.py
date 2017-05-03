"""
Tests for :module:`client`
"""

import json

from treq.testing import RequestSequence, StringStubbingResource, StubTreq, HasHeaders

from twisted.internet.defer import Deferred
from twisted.internet.task import Clock
from twisted.trial.unittest import SynchronousTestCase
from twisted.web.util import DeferredResource

from bloc.client import BlocClient


class BlocClientTests(SynchronousTestCase):
    """
    Tests for :obj:`client.BlocClient`
    """

    def setUp(self):
        self.clock = Clock()
        self.client = BlocClient(self.clock, 'server:8989', 3, session_id='sid')

    def setup_treq(self, code=200, body={}):
        self.async_failures = []
        self.stubs = RequestSequence(
            [((b"get", "http://server:8989/index", {},
               HasHeaders({"Bloc-Session-ID": ["sid"]}), b''),
              (code, {}, json.dumps(body).encode("utf-8")))],
            self.async_failures.append)
        self.client.treq = StubTreq(StringStubbingResource(self.stubs))

    def test_settled(self):
        """
        When getting index returns SETTLED then it is set and is returned in `get_index_total`
        """
        self.setup_treq(body={"status": "SETTLED", "index": 1, "total": 1})
        self.client.startService()
        with self.stubs.consume(self.fail):
            self.assertEqual(self.client.get_index_total(), (1, 1))
            self.assertTrue(self.client._settled)
        self.assertEqual(self.async_failures, [])

    def test_settling(self):
        """
        When getting index returns SETTLING, then get_index_total returns None
        """
        self.setup_treq(body={"status": "SETTLING"})
        self.client.startService()
        with self.stubs.consume(self.fail):
            self.assertIsNone(self.client.get_index_total())
        self.assertEqual(self.async_failures, [])

    def test_get_errors(self):
        """
        If get index errors, then get_index_total will return None
        """
        self.setup_treq(code=500)
        self.client.startService()
        with self.stubs.consume(self.fail):
            self.assertIsNone(self.client.get_index_total())
        self.assertEqual(self.async_failures, [])

    def test_get_times_out(self):
        """
        If get index times out then get_index_total will return None
        """
        # lets start with settled
        self.test_settled()
        # setup client that does not return
        self.client.treq = StubTreq(DeferredResource(Deferred()))
        # next heartbeat to get index again
        self.clock.advance(3)
        # no response
        self.clock.advance(5)
        self.assertIsNone(self.client.get_index_total())

    def test_sequence(self):
        """
        Test sequence of changes from server:
        TODO: this should probably be done via hypothesis
        SETTLING -> SETTLED -> ERRORS -> SETTLING -> SETTLED
        """
        # settling
        self.setup_treq(body={"status": "SETTLING"})
        self.client.startService()
        with self.stubs.consume(self.fail):
            self.assertIsNone(self.client.get_index_total())

        # settled
        self.setup_treq(body={"status": "SETTLED", "index": 1, "total": 3})
        self.clock.advance(3)
        with self.stubs.consume(self.fail):
            self.assertEqual(self.client.get_index_total(), (1, 3))

        # errors
        self.setup_treq(code=500)
        self.clock.advance(3)
        with self.stubs.consume(self.fail):
            self.assertIsNone(self.client.get_index_total())

        # settling
        self.setup_treq(body={"status": "SETTLING"})
        self.clock.advance(3)
        with self.stubs.consume(self.fail):
            self.assertIsNone(self.client.get_index_total())

        # settled
        self.setup_treq(body={"status": "SETTLED", "index": 3, "total": 4})
        self.clock.advance(3)
        with self.stubs.consume(self.fail):
            self.assertEqual(self.client.get_index_total(), (3, 4))
        self.assertEqual(self.async_failures, [])

    def test_stopservice_deletes_session(self):
        """
        :func:`stopService` will delete the session and will stop the loop
        """
        self.test_settled()
        stubs = RequestSequence(
            [((b"delete", "http://server:8989/session", {},
               HasHeaders({"Bloc-Session-ID": ["sid"]}), b''),
              (200, {}, b''))],
            self.fail)
        self.client.treq = StubTreq(StringStubbingResource(stubs))
        with stubs.consume(self.fail):
            d = self.client.stopService()
            self.assertIsNone(self.successResultOf(d))
            # Moving time would fail treq if it tried to heartbeat
            self.clock.advance(4)

    def test_stopservice_ignores_delete_session(self):
        """
        :func:`stopService` will try deleting the session for 1 second and will stop the loop
        """
        self.test_settled()
        self.client.treq = StubTreq(DeferredResource(Deferred()))
        d = self.client.stopService()
        self.assertNoResult(d)
        self.clock.advance(1)
        self.assertIsNone(self.successResultOf(d))
        # Moving time would fail treq if it tried to heartbeat
        self.clock.advance(4)
