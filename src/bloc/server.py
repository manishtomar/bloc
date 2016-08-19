import json

from klein import Klein

from twisted.internet import task
from twisted.python import log as default_log


class EmptyLogger(object):
    def msg(self, *a, **k):
        pass
    err = default_log.err


class NotAllocated(Exception):
    """
    Raised when getting participent index when group
    is not allocated
    """


class GroupParticipants(object):
    """
    Manages group of participants. A group is allocated when `settle` time
    has passed after adding/removing participants. Otherwise it is allocating

    :param IReactorTime clock: A twisted time provider
    :param float settle: Number of seconds to wait before allocating
    :param log: Twisted logger
    """
    def __init__(self, clock, settle, log=EmptyLogger()):
        self._clock = clock
        self._settle = settle
        self._participants = set()  # dict when allocated, set when not
        self._allocated = False
        self._timer = None
        self.log = log

    def _reset_timer(self):
        if self._timer is not None and self._timer.active():
            self._timer.cancel()
        self._timer = self._clock.callLater(self._settle, self._settled)
        self._allocated = False
        self.log.msg('reset timer')

    def _settled(self):
        self._participants = {p: i + 1 for i, p in enumerate(self._participants)}
        self._allocated = True
        self.log.msg('settled')

    def add_participant(self, participant):
        """
        Add participant to the group
        """
        if self._allocated:
            self._participants = set(self._participants.keys()) | {participant}
        else:
            self._participants.add(participant)
        self._reset_timer()

    def remove_participants(self, participants):
        """
        Remove participants from the group
        """
        participants = set(participants)
        if self._allocated:
            self._participants = set(self._participants.keys()) - participants
        else:
            self._participants -= participants
        self._reset_timer()

    def index_of(self, participant):
        """
        Return index of the participant
        """
        if not self._allocated:
            raise NotAllocated(participant)
        return self._participants[participant]

    def __len__(self):
        return len(self._participants)

    @property
    def allocated(self):
        """
        Is it allocated?
        """
        return self._allocated

    def __str__(self):
        s = 'allocated' if self._allocated else 'allocating'
        return 'GroupParticipants: {}, {}'.format(s, str(self._participants))


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

    def __init__(self, clock, timeout, settle, interval=1, log=EmptyLogger(),
                 GroupParticipants=GroupParticipants):
        self._clock = clock
        self._group = GroupParticipants(self._clock, settle, log)
        self._timeout = timeout

        self._clients = {}
        self._loop = task.LoopingCall(self._check_clients)
        self._loop.clock = self._clock
        # TODO: Call this from from another func
        self._loop.start(interval, False)

        self.log = log

    def _add_client(self, client):
        self._group.add_participant(client)
        self._heartbeat_client(client)
        self.log.msg('Added client', client)

    def _remove_clients(self, clients):
        for client in clients:
            del self._clients[client]
        self._group.remove_participants(clients)

    def _check_clients(self):
        now = self._clock.seconds()
        clients_to_remove = []
        for client, last_active in self._clients.iteritems():
            inactive = now - last_active
            if inactive > self._timeout:
                self.log.msg(
                    'Client {} timed out after {} seconds'.format(client,
                                                                  inactive))
                clients_to_remove.append(client)
        if clients_to_remove:
            self._remove_clients(clients_to_remove)

    def _heartbeat_client(self, client):
        self._clients[client] = self._clock.seconds()

    @app.route('/disconnect', methods=['POST'])
    def cancel_session(self, request):
        client = extract_client(request)
        if client in self._clients:
            self._remove_clients([client])
        return "{}"

    @app.route('/index', methods=['GET'])
    def get_index(self, request):
        client = extract_client(request)
        if client in self._clients:
            self._heartbeat_client(client)
        else:
            self._add_client(client)
        if self._group.allocated:
            return json.dumps(
                {'status': 'ALLOCATED',
                 'index': self._group.index_of(client),
                 'total': len(self._group)})
        else:
            return json.dumps({'status': 'ALLOCATING'})


if __name__ == '__main__':
    from twisted.internet import reactor
    Participate(reactor, 6, 10, log=default_log).app.run('localhost', 8080)
