bloc
====

.. image:: https://travis-ci.org/manishtomar/bloc.svg?branch=master
   :target: https://travis-ci.org/manishtomar/bloc
   :alt: CI Status

.. image:: https://codecov.io/github/manishtomar/bloc/branch/master/graph/badge.svg
   :target: https://codecov.io/github/manishtomar/bloc
   :alt: Test Coverage

Simple single-master group membership framework based on Twisted that helps in partitioning workloads or
stateless data among multiple nodes. It consists of 2 components: 

1) Standalone HTTP server provided as a twisted plugin that keeps track of the group
2) Twisted based client library talking to the above server (Other language libraries çan be implemented on demand)

Installation
------------
``pip install bloc`` on both server and client nodes. 

Usage
-----
On server run ``twist -t 4 -s 6`` where 3 is client heartbeat timeout and 6 is settling timeout (both in seconds). Each is explained below.node 

On client sample code:: 

    from twisted.internet import task

    def do_stuff(bc):
        index_total = bc.get_index_total()
        if index_total is None:
            return
        index, total = index_totalk

    @task.react
    def main(reactor):
        bc = BlocClient(reactor, "http://server_ip:8989/", 3)
        bc.startService()
        return LoopingCall(do_stuff, (bc,)).start(2)
   

How does it work:
----------------

It reliably provides each node with following two pieces of information:

1. Total number of nodes participating
2. This node's index

This information alone is enough in almost all cases to equally distribute work. 

The server at any time remains in either of the two states: SETTLING or SETTLED. It starts of in
SETTLING and remains in that state when nodes start to join or leave. When the nodes stop having
activity (no more joins / leaving) for configurable time, it then transitions to SETTLED state at
which time it assigns each node an index and informs them about it.

It provides reliability by nodes continously heartbeating with server. There is timer on both client
and server ends that ensure that client is alive and hence occupies the position in the group.
If server does not receive heartbeat within a given time, it removes the corresponding client and
moves to SETTLING state and informs the nodes. Once it is settled it moves to SETTLING state. This
way nodes can be added and removed on demand without any issues.

