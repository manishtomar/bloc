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

1) Standalone TCP server provided as a twisted plugin that keeps track of the group. Currently the protocol
   is HTTP but it may change in future.
2) Twisted based client library talking to the above server (Other language libraries çan be implemented on demand)

Installation
------------
``pip install bloc`` on both server and client nodes. 

Usage
-----
On server run ``twist -t 4 -s 6`` where 4 is client heartbeat timeout and 6 is settling timeout (explained below).
This will start HTTP server on port 8989 by default. One can give different port via ``-l tcp:port`` option.

On client to equally partition ``items`` among multiple nodes, create ``BlocClient`` and call ``get_index_total``
on regular basis. Following is sample code:: 

    from functools import partial
    from twisted.internet import task
    from twisted.internet.defer import inlineCallbacks, gatherResults

    @inlineCallbacks
    def do_stuff(bc):
        index_total = bc.get_index_total()
        if index_total is None:
            return
        index, total = index_total
        items = yield get_items_to_process()
        my_items = filter(partial(is_my_item, index, total), items)
        yield gatherResults([process_item(item) for item in my_items])

    def is_my_item(index, total, item):
        return hash(item) % total + 1 == index

    @task.react
    def main(reactor):
        bc = BlocClient(reactor, "server_ip:8989",
                        3   # Heartbeat interval
                        )
        bc.startService()
        # Call do_stuff every 2 seconds
        return LoopingCall(do_stuff, bc).start(2)

Here, the important function is ``is_my_item`` which decides whether the item can be processed by
this node based on the index and total. It works based on item's hash. Needless to say it is important
to have stable hash function implemented for your item. IMHO there is no necessity for item
to be anything other than some kind of key (string). This function will guarantee that only one node
will process a particular item provided bloc server provides unique index to each node which it does.

The above code assumes that ``items`` is dynamic which will be true if it is based on your application
data like users. However, there are situations where it can be a fixed number if your data is already
parititioned among fixed number of buckets in which case you can use bloc to assign buckets to each node.
An example of this is `otter's scheduling feature<https://github.com/rackerlabs/otter/blob/master/otter/scheduler.py>_`
which partitions events to be executed among fixed set of 10 buckets and distributes the buckets
among < 10 nodes. Another example is kafka's partitioned topic. Each node can consume a particular
partition based on index and total provided.

``get_index_total`` returns ``None`` when there is no index assigned which can happen when nodes are added / removed
or when client cannot talk to the server due to any networking issues. The client must stop doing its work
when this happens because next time the node could have different index assigned. This is why the
client's processing based on the index must be stateless.

index and total is internally updated on interval provided when creating ``BlocClient``. Hence,
``get_index_total`` must be called at least once during that interval to always have the latest value
and not accidentally working with incorrect index.

You would have noticed ``bc.startService`` in above code which is required to be called before calling
``get_index_total``. If you are setting up twisted server using service hierarchy then it is best
to add ``BlocClient`` object as a child service. This way Twisted will start and stop the service when required.

How does it work:
----------------

The server at any time remains in either of the two states: SETTLING or SETTLED. It starts of in
SETTLING and remains in that state when nodes start to join or leave. When the nodes stop having
activity (no more joins / leaving) for configurable time, it then transitions to SETTLED state at
which time it assigns each node an index and informs them about it.

It provides reliability by nodes continously heartbeating with server. There is timer on both client
and server ends that ensure that client is alive and hence occupies the position in the group.
If server does not receive heartbeat within a given time, it removes the corresponding client and
moves to SETTLING state and informs the nodes. Once it is settled it moves to SETTLING state. This
way nodes can be added and removed on demand without any issues.
