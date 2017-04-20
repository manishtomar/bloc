import json

import attr
from attr.validators import instance_of as iof

from klein import Klein

from twisted.internet.interfaces import IReactorTime
from twisted.internet import task
from twisted.python import log as default_log


class NotSettled(Exception):
    """
    Raised when getting index of a member when group is not settled
    """


@attr.s
class SettlingGroup(object):
    """
    A group that "settles" down when there is no activity for `settle` seconds.

    :param clock: A twisted time provider that implements :obj:`IReactorTime`
    :param float settle: Number of seconds to wait before settling
    :param log: Twisted logger
    """
    clock = attr.ib(validator=attr.validators.provides(IReactorTime))
    settle = attr.ib(convert=float)
    _members = attr.ib(default=attr.Factory(dict))
    _settled = attr.ib(default=False)
    _timer = attr.ib(default=None)

    def _reset_timer(self):
        if self._timer is not None and self._timer.active():
            self._timer.cancel()
        self._timer = self.clock.callLater(self.settle, self._do_settling)
        self._settled = False
        #self.log.msg('reset timer')

    def _do_settling(self):
        self._members = {p: i + 1 for i, p in enumerate(self._members.keys())}
        self._settled = True
        #self.log.msg('settled')

    def add(self, member):
        """
        Add member to the group
        """
        if member in self._members:
            return
        self._members[member] = None
        self._reset_timer()

    def remove(self, member):
        """
        Remove member from the group.

        :raises: ``KeyError` if member is not in the group
        """
        del self._members[member]
        self._reset_timer()

    def index_of(self, member):
        """
        Return index allocated for the given member if group has settled

        :raises: :obj:`NotSettled` if group is not settled
        """
        if not self._settled:
            raise NotSettled(member)
        return self._members[member]

    def __len__(self):
        return len(self._members)

    def __contains__(self, member):
        return member in self._members

    @property
    def settled(self):
        """
        Is it settled?
        """
        return self._settled


@attr.s
class HeartbeatingClients(object):
    """
    Group of clients that will heartbeat to remain active
    """
    clock = attr.ib(validator=attr.validators.provides(IReactorTime))
    timeout = attr.ib(convert=float)
    interval = attr.ib(convert=float)
    _remove_cb = attr.ib()
    _clients = attr.ib(default=attr.Factory(dict))

    def __attrs_post_init__(self):
        self._loop = task.LoopingCall(self._check_clients)
        self._loop.clock = self.clock
        # TODO: Call this from from another func
        self._loop.start(self.interval, False)
        #self.log = log

    def remove(self, client):
        del self._clients[client]

    def _check_clients(self):
        # This is O(n). May have issues when (say) 1000+ clients connect. See if a heap can be used
        # instead
        now = self.clock.seconds()
        clients_to_remove = []
        for client, last_active in self._clients.items():
            inactive = now - last_active
            if inactive > self.timeout:
                #self.log.msg('Client {} timed out after {} seconds'.format(client, inactive))
                clients_to_remove.append(client)
        for client in clients_to_remove:
            self.remove(client)
            self._remove_cb(client)

    def heartbeat(self, client):
        #if client not in self._clients:
        #    self.log.msg('Adding client', client)
        self._clients[client] = self.clock.seconds()

    def __contains__(self, client):
        return client in self._clients


def extract_client(request):
    """
    Return session id from the request
    """
    _id = request.requestHeaders.getRawHeaders('Bloc-Session-ID', None)
    return _id[0] if _id is not None else None


class Bloc(object):
    """
    Main server object that clients talk to
    """

    app = Klein()

    def __init__(self, clock, timeout, settle, interval=1):
        """
        Create Bloc object

        :param clock: A twisted time provider that implements :obj:`IReactorTime`. Typically main
            twisted reactor object.
        :param float timeout: Maximum number of seconds to wait for a client to hearbeat before
            removing it from the group and change it to SETTLING.
        :param float settle: Number of seconds to wait before settling. Ensures that all clients
            are settled for this much time before marking the group as SETTLED
        :param float interval: Internal interval to check all clients heartbeat status. Defaults to
            1 second. Mostly, this doesn't need to be changed.
        """
        self._group = SettlingGroup(clock, settle)
        self._clients = HeartbeatingClients(clock, timeout, interval, self._group.remove)

    @app.route('/session', methods=['DELETE'])
    def cancel_session(self, request):
        client = extract_client(request)
        self._clients.remove(client)
        self._group.remove(client)
        return "{}".encode("utf-8")

    @app.route('/index', methods=['GET'])
    def get_index(self, request):
        client = extract_client(request)
        self._clients.heartbeat(client)
        self._group.add(client)
        if self._group.settled:
            return json.dumps(
                {'status': 'SETTLED',
                 'index': self._group.index_of(client),
                 'total': len(self._group)}).encode("utf-8")
        else:
            return json.dumps({'status': 'SETTLING'}).encode("utf-8")


if __name__ == '__main__':
    from twisted.internet import reactor
    Bloc(reactor, 6, 10).app.run('localhost', 8989)
