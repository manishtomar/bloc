import random
import uuid

import treq

from twisted.internet import task
from twisted.python import log as tlog


def check_status(resp, statuses):
    if resp.code not in statuses:
        raise ValueError('unexpected resp code: {}'.format(resp.code))
    return resp


class ParticipateClient(object):
    """
    Client to connect to participate server
    """

    def __init__(self, reactor, url, interval, log=tlog, treq=treq, _uuid=uuid):
        self.reactor = reactor
        self.url = url

        self._allocated = False
        self._index = 0
        self._total = 0
        self._interval = interval

        self._loop = task.LoopingCall(self._heartbeat)
        self._loop.clock = self.reactor
        self._session_id = str(_uuid.uuid1())

        self.log = log
        self.treq = treq

    def start(self):
        """
        Start getting the index and effectively heartbeating
        """
        self._loop.start(self._interval, True)

    def _set_index(self, content):
        if content['status'] == 'ALLOCATED':
            self._allocated = True
            self._index = content['index']
            self._total = content['total']
        else:
            self._allocated = False

    def _error_allocating(self, f):
        self._allocated = False
        self.log.err(f, 'Error getting index')

    def _heartbeat(self):
        d = self.treq.get('{}/index'.format(self.url.rstrip('/')),
                          headers={'X-Session-ID': [self._session_id]})
        d.addCallback(check_status, [200])
        d.addCallback(treq.json_content)
        d.addCallback(self._set_index)
        d.addErrback(self._error_allocating)
        return d

    def stop(self):
        """
        Stop heartbeating
        """

    def get_index_total(self):
        """
        Return (index, total) tuple if allocated, None if allocating.
        Note that this returns internal state last updated.
        Maybe raises some exception on error?
        """
        if not self._allocated:
            return None
        return (self._index, self._total)


def print_index(p):
    print 'index', p.get_index_total()


def test():
    from twisted.internet import reactor
    p = ParticipateClient(reactor, 'http://localhost:8080', 3, log=tlog)
    p.start()
    task.LoopingCall(print_index, p).start(5)
    reactor.run()


if __name__ == '__main__':
    test()
