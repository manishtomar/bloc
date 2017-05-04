bloc
====

.. image:: https://img.shields.io/pypi/v/bloc.svg
   :target: https://pypi.org/project/bloc
   :alt: PyPI package

.. image:: https://travis-ci.org/manishtomar/bloc.svg?branch=master
   :target: https://travis-ci.org/manishtomar/bloc
   :alt: CI Status

.. image:: https://codecov.io/github/manishtomar/bloc/branch/master/graph/badge.svg
   :target: https://codecov.io/github/manishtomar/bloc
   :alt: Test Coverage

Simple single-master group membership framework based on Twisted that helps in partitioning workloads or
stateless data among multiple nodes. It consists of 2 components: 

1) Standalone TCP server provided as a twisted plugin that keeps track of the group. Currently the protocol
   is HTTP but it may change in future.
2) Twisted based client library talking to the above server (Other language libraries çan be implemented on demand)

It provides failure detection based on heartbeats. However, since it is single master the server is
a single point of failure. But since the server is completely stateless it can be easily restarted without any issues.

It works on Python 2.7 and 3.6.

Installation
------------
``pip install bloc`` on both server and client nodes. 

Usage
-----
On server run ``twist -t 4 -s 6`` where 4 is client heartbeat timeout and 6 is settling timeout (explained below).
This will start HTTP server on port 8989 by default. One can give different port via ``-l tcp:port`` option.

On client, to equally partition ``items`` among multiple nodes, create ``BlocClient`` and call ``get_index_total``
on regular basis. Following is sample code:

.. code-block:: python

    from functools import partial
    from twisted.internet import task
    from twisted.internet.defer import inlineCallbacks, gatherResults

    @inlineCallbacks
    def do_stuff(bc):
        """ Process items based on index and total got from BlocClient """
        # get_index_total returns this node's index and total number of nodes in the group
        index_total = bc.get_index_total()
        if index_total is None:
            return
        index, total = index_total
        items = yield get_items_to_process()
        my_items = filter(partial(is_my_item, index, total), items)
        yield gatherResults([process_item(item) for item in my_items])

    def is_my_item(index, total, item):
        """ Can I process this item? """
        return hash(item) % total + 1 == index

    @task.react
    def main(reactor):
        bc = BlocClient(reactor, "server_ip:8989", 3)
        bc.startService()
        # Call do_stuff every 2 seconds
        return task.LoopingCall(do_stuff, bc).start(2)

Here, the important function is ``is_my_item`` which decides whether the item can be processed by
this node based on the index and total. It works based on item's hash. Needless to say, it is important
to have stable hash function implemented for your item. Ideally, there shouldn't be any necessity for item
to be anything other than some kind of key (string). This function will guarantee that only one node
will process a particular item provided bloc server provides a unique index to each node which it does.

As an example, say node A and B are running above code talking to same bloc server and items is following
list of userids being processed::

    1. 365f54e9-5de8-4509-be16-38e0c37f5fe9
    2. f6a6a396-d0bf-428a-b63b-830f98874b6c
    3. 6bec3551-163d-4eb8-b2d8-1f2c4b106d33
    4. b6691e16-1d95-42de-8ad6-7aa0c81fe080

If node A's ``get_item_index`` returns ``(1, 2)`` then ``is_my_item`` will return ``True`` for userid 1 and 3
and in node B's ``get_item_index`` returns ``(2, 2)`` and ``is_my_item`` will return ``True`` for userid 2 and 4.
This way you can partition the user ids among multiple nodes.

The choice of hash function and keyspace may decide how equally the workload is distributed across the nodes.

The above code assumes that ``items`` is dynamic which will be true if it is based on your application
data like users. However, there are situations where it can be a fixed number if your data is already
partitioned among fixed number of buckets in which case you can use bloc to assign buckets to each node.
An example of this is `otter's scheduling feature <https://github.com/rackerlabs/otter/blob/master/otter/scheduler.py>`_
which partitions events to be executed among a fixed set of 10 buckets and distributes the buckets
within < 10 nodes. Another example is kafka's partitioned topic. Each node can consume a particular
partition based on index and total provided.

``get_index_total`` returns ``None`` when there is no index assigned which can happen when nodes are added/removed
or when the client cannot talk to the server due to any networking issues. The client must stop doing its work
when this happens because next time the node could have different index assigned. This is why the
client's processing based on the index must be stateless.

index and total are internally updated on interval provided when creating ``BlocClient``. They can change 
over time but only after ``get_index_total`` returns ``None`` for settling period (provided when starting server).
Hence, ``get_index_total`` must be called at least once during the settling period to always have the latest value
and not accidentally work with incorrect index.

You would have noticed ``bc.startService`` in above code which is required to be called before calling
``get_index_total``. If you are setting up twisted server using service hierarchy then it is best
to add ``BlocClient`` object as a child service. This way Twisted will start and stop the service when required.

How does it work:
-----------------

The server at any time remains in either of the two states: SETTLING or SETTLED. It starts of in
SETTLING and remains in that state when nodes start to join or leave. When the nodes stop having
activity (no more joins / leaving) for configurable time (called settling time given when starting server),
it then transitions to SETTLED state at which time it assigns each node an index and informs them about it.
The settling time is provided with ``-s`` option when starting the server and should generally be few seconds
greater than heartbeat interval. This way the server avoids unnecessarily assigning indexes when
multiple nodes are joining/leaving at close times.

Client hearbeats to the server at interval provided when creating ``BlocClient``. The server keeps
track of clients based on this heartbeat and removes any client that does not heartbeat in configured
time. This time is provided as ``-t`` option when starting the server. The heartbeat timeout provided
in server should be a little more than the heartbeat interval provided in client to take into account
latency or temporary network glitches. In example above, server times out after 4 seconds and client
heartbeats every 3 seconds. This hearbeat mechanism provides failure detection. If any of the nodes
is bad that node will just stop processing work.

Some things to know:
--------------------

* **No security**: Currently the server does not authenticate the client and accepts from any client.
  The connection is also not encrypted. Depending on demand I am planning to add mutual TLS authentication
* **No benchmarks done**. However, since its all in memory and Twisted it should easily scale to
  few hundred clients. I'll do some testing and update later.
* By default ``twist`` logging is at info level and due to heartbeats in HTTP every request is logged.
  You can give ``--log-level=warn`` option to avoid it.
