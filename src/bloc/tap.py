"""
Twisted application plugin for bloc
"""

from bloc.server import Bloc

from twisted.application.strports import service
from twisted.python import usage
from twisted.web.server import Site


class Options(usage.Options):
    """
    Options for bloc
    """
    optParameters = [
        ['listen', 'l', 'tcp:8989', 'The endpoint to listen on.'],
        ['timeout', 't', None, "Number of seconds to wait before timing out client heartbeats"],
        ['settle', 's', None, "Number of seconds to wait before settling the group"]
    ]


def makeService(config):
    """
    Set up the service.
    """
    from twisted.internet import reactor
    site = Site(Bloc(reactor, float(config["timeout"]), float(config["settle"])).app.resource())
    site.displayTracebacks = False

    # The Twisted code currently (v16.6.0, 17.1.0) compares the type of
    # this argument to 'str' in order to determine how to handle it.
    description = str(config['listen'])
    return service(description, site)
