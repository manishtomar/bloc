Partitioning for distributed systems
====================================

Simple single-master RESTful partitioner for building distributed systems that want to equally distribute workload among multiple nodes. It is written on top of Twisted. 

It reliably provides each node with following two pieces of information:

1. Total number of nodes participating
2. This node's index

This information alone is enough in almost all cases to equally distribute work. 

The server at any time remains in either of the two states: ALLOCATING, ALLOCATED. It starts of in ALLOCATING and remains in that state when nodes start joining or leaving. When the nodes remain settled for a configurable time, then it moves to ALLOCATED state and informs the nodes about the total nodes and their respective indexes. 

It provides reliability by nodes continously heartbeating with server. There is timer on both client and server ends that ensure that client is alive and hence occupies the position in the group. If server does not receive heartbeat, it moves to ALLOCATING state and informs the nodes. Once it is settled it moves to ALLOCTED state.
