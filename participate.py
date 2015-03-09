import json

from klein import Klein

from twisted.internet import task
from twisted.python import log as default_log


# @attributes(['id', 'index'])
class Session(object):
    pass


def start_partitioning(clock, settle):
    """
    Returns deferred that does not fire. Has to be cancelled
    """


def add_participant():
    pass


class EmptyLogger(object):
    def msg(*a, **k):
        pass
    def err(*a, **k):
        pass


class Partitioner(object):
    """
    Partitions a set among participants in memory
    """

    def __init__(self, clock, settle=15, log=EmptyLogger()):
        self._clock = clock
        self._settle = settle
        self._participants = set()
        self._allocated = False
        self._timer = None
        self._splits = {}
        self.log = log

    def _reset_timer(self):
        if self._timer is not None and self._timer.active():
            self._timer.cancel()
        self._timer = self._clock.callLater(self._settle, self._settled)
        self._allocated = False
        self._splits = {}
        self.log.msg('reset timer')

    def _settled(self):
        self._splits = {p: i + 1 for i, p in enumerate(self._participants)}
        self._allocated = True
        self.log.msg('settled')

    def add_participant(self, participant):
        """
        Add participant to the partitioner
        """
        self._participants.add(participant)
        self._reset_timer()

    def remove_participant(self, participant):
        self._participants.remove(participant)
        self._reset_timer()

    def get_participant_index(self, participant):
        """
        Return index of the participant
        """
        return self._splits[participant]

    def __len__(self):
        return len(self._splits)

    @property
    def allocated(self):
        return self._allocated


def extract_client(request):
    """
    Return session id from the request
    """
    _id = request.requestHeaders.getRawHeaders('X-Session-ID', None)
    return _id[0] if _id is not None else None


class Participate(object):
    """
    Main application object
    """

    app = Klein()

    def __init__(self, clock, timeout, settle, interval=1, log=EmptyLogger()):
        self._clock = clock
        self._partitioner = Partitioner(self._clock, settle, log)
        self._timeout = timeout

        self._clients = {}
        self._loop = task.LoopingCall(self._check_clients)
        self._loop.clock = self._clock
        # TODO: Call this from from another func
        self._loop.start(interval, False)

        self.log = log

    def _add_client(self, client):
        self._partitioner.add_participant(client)
        self._heartbeat_client(client)
        self.log.msg('Added client', client)

    def _remove_client(self, client):
        del self._clients[client]
        self._partitioner.remove_participant(client)
        self.log.msg('Removed client', client)

    def _check_clients(self):
        now = self._clock.seconds()
        clients_to_remove = []
        for client, last_active in self._clients.iteritems():
            if now - last_active > self._timeout:
                self.log.msg('Client {} timed out'.format(client))
                clients_to_remove.append(client)
        [self._remove_client(c) for c in clients_to_remove]

    def _heartbeat_client(self, client):
        self._clients[client] = self._clock.seconds()

    @app.route('/disconnect', methods=['POST'])
    def cancel_session(self, request):
        client = extract_client(request)
        if client:
            self._remove_client(client)

    @app.route('/index', methods=['GET'])
    def get_index(self, request):
        client = extract_client(request)
        if client in self._clients:
            self._heartbeat_client(client)
        else:
            self._add_client(client)
        if self._partitioner.allocated:
            return json.dumps(
                {'status': 'ALLOCATED',
                 'index': self._partitioner.get_participant_index(client),
                 'total': len(self._partitioner)})
        else:
            return json.dumps({'status': 'ALLOCATING'})


if __name__ == '__main__':
    from twisted.internet import reactor
    Participate(reactor, 6, 10, log=default_log).app.run('localhost', 8080)
