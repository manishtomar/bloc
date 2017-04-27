"""
Sample test client for bloc server
"""

from __future__ import print_function

from bloc.client import BlocClient

from twisted.internet import task


def print_index(b):
    print('index', b.get_index_total())


def test(reactor):
    b = BlocClient(reactor, 'http://localhost:8989', 3)
    b.startService()
    return task.LoopingCall(print_index, b).start(5)


if __name__ == '__main__':
    task.react(test)
