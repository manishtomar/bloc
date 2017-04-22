from __future__ import print_function

import uuid

import treq

from twisted.application.service import Service
from twisted.internet import task
from twisted.logger import Logger

from bloc.utils import check_status


class BlocClient(Service):
    """
    Client to connect to bloc server
    """

    def __init__(self, clock, url, interval, treq=treq, session_id=None):
        """
        Create a BlocClient instance

        :param clock: An implementation of :obj:`IReactorTime`. Typically will be main twisted
            reactor.
        :param str url: URL of Bloc server being connected to
        :param float interval: Frequency of heartbeat in seconds
        """
        self.clock = clock
        self.url = url

        self._settled = False
        self._index = 0
        self._total = 0
        self._interval = interval

        self._loop = task.LoopingCall(self._heartbeat)
        self._loop.clock = self.clock
        if session_id is None:
            self._session_id = str(uuid.uuid1())
        else:
            self._session_id = session_id

        self.log = Logger()
        self.treq = treq

    def startService(self):
        """
        Start getting the index and effectively heartbeating
        """
        super(BlocClient, self).startService()
        self._loop.start(self._interval, True)

    def _set_index(self, content):
        if content['status'] == 'SETTLED':
            self._settled = True
            self._index = content['index']
            self._total = content['total']
        else:
            self._settled = False

    def _url(self, segment):
        return '{}/{}'.format(self.url.rstrip('/'), segment)

    def _get_index(self):
        d = self.treq.get(self._url("index"), headers={'Bloc-Session-ID': [self._session_id]})
        d.addCallback(check_status, [200])
        return d.addCallback(treq.json_content)

    def _error_allocating(self, f):
        self._settled = False
        self.log.error("Error getting index: {f}", f=f)

    def _heartbeat(self):
        d = self._get_index()
        d.addCallback(self._set_index)
        d.addTimeout(self._interval, self.clock)
        d.addErrback(self._error_allocating)
        return d

    def stopService(self):
        """
        Delete session and stop heartbeating
        """
        super(BlocClient, self).stopService()
        # Delete session before shutdown but do not worry about response if it not received
        # within 1 second because we don't want to block shutdown of twisted app and server will
        # anyway cancel the session without next heartbeat
        d = self.treq.delete(self._url("session"), headers={'Bloc-Session-ID': [self._session_id]})
        d.addTimeout(1, self.clock)
        return d.addBoth(lambda r: self._loop.stop())

    def get_index_total(self):
        """
        Return (index, total) tuple if settled, None if settling.
        Note that this returns internal state last updated every "interval" seconds
        seconds.
        """
        if not self._settled:
            return None
        return (self._index, self._total)


def print_index(p): # noqa
    print('index', p.get_index_total())


def test(): # noqa
    from twisted.internet import reactor
    p = BlocClient(reactor, 'http://localhost:8989', 3)
    p.startService()
    task.LoopingCall(print_index, p).start(5)
    reactor.run()


if __name__ == '__main__':
    test()
