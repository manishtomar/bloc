bloc
====

.. image:: https://travis-ci.org/manishtomar/bloc.svg?branch=master
   :target: https://travis-ci.org/manishtomar/bloc
   :alt: CI Status

.. image:: https://codecov.io/github/manishtomar/bloc/branch/master/graph/badge.svg
   :target: https://codecov.io/github/manishtomar/bloc
   :alt: Test Coverage

Simple single-master group membership framework that helps in partitioning workloads or
stateless data amoing multiple nodes.

It reliably provides each node with following two pieces of information:

1. Total number of nodes participating
2. This node's index

This information alone is enough in almost all cases to equally distribute work. 

The server at any time remains in either of the two states: SETTLING, SETTLED. It starts of in
SETTLING and remains in that state when nodes start joining or leaving. When the nodes stop having
activity (no more joins / leaving) for configurable time, it then transitions to SETTLED state at
which time it assigns each node an index and informs them about it.

It provides reliability by nodes continously heartbeating with server. There is timer on both client
and server ends that ensure that client is alive and hence occupies the position in the group.
If server does not receive heartbeat within a given time, it removes the corresponding client and
moves to SETTLING state and informs the nodes. Once it is settled it moves to SETTLING state. This
way nodes can be added and removed on demand without any issues.
