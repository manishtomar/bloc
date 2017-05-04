"""
Tests for :module:`tap`
"""

from twisted.application.service import MultiService
from twisted.trial.unittest import SynchronousTestCase

from bloc import tap
from bloc.server import Bloc


class ServiceTests(SynchronousTestCase):
    """
    Tests for :obj:`tap.makeService`
    """

    def test_service(self):
        """
        Creates multiservice with Bloc object and its klein resource service in it
        """
        s = tap.makeService({"timeout": "3", "settle": "4", "listen": "tcp:8989"})
        self.assertIsInstance(s, MultiService)
        children = list(s)
        # First child is Bloc instance
        self.assertIsInstance(children[0], Bloc)
        bloc = children[0]
        # second child is service that starts the klein app of Bloc object
        site_service = children[1]   # site_service is StreamServerEndpointService
        self.assertIs(site_service.factory.resource._app, bloc.app)
        # Would like to test the listen part of config but not sure how to inspect
        # IStreamServerEndpoint in site_service.endpoint
