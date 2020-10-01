# Overview

The Apache Cassandra database is the right choice when you need scalability
and high availability without compromising performance. Linear scalability
and proven fault-tolerance on commodity hardware or cloud infrastructure
make it the perfect platform for mission-critical data. Cassandra's support
for replicating across multiple datacenters is best-in-class, providing lower
latency for your users and the peace of mind of knowing that you can survive
regional outages.

See [cassandra.apache.org](http://cassandra.apache.org) for more information.


# Editions

This charm supports Apache Cassandra 3.x

# Deployment

Cassandra deployments are relatively simple in that they consist of a set of
Cassandra nodes which seed from each other to create a ring of servers:
    
    juju bootstrap microk8s k8s-cloud
    juju add-model cassandramodel
    juju deploy -n3 cs:narindergupta/k8s-cassandra cassandra

The service units will deploy and will form a single ring.

New nodes can be added to scale up:

    juju add-unit cassandra


/!\ *Nodes must be manually decommissioned before dropping a unit.*

    microk8s.kubectl exec -n cassandramodel -it cassandra-2 -- nodetool decommission
    # Wait until Mode is DECOMMISSIONED
    microk8s.kubectl exec -n cassandramodel -it cassandra-2 -- nodetool netstats
    juju remove-unit cassandra/2

It is recommended to deploy at least 3 nodes and configure all your
keyspaces to have a replication factor of three. Using fewer nodes or
neglecting to set your keyspaces' replication settings means that your
data is at risk and availability lower, as a failed unit may take the
only copy of data with it.

Production systems will normally want to set `max_heap_size` and
`heap_newsize` to the empty string, to enable automatic memory size
tuning. The defaults have been chosen to be suitable for development
environments but will perform poorly with real workloads.


## Planning

- Do not attempt to store too much data per node. If you need more space,
  add more nodes. Most workloads work best with a capacity under 1TB
  per node, so take care with larger deployments. Recommended capacities
  are vague and version dependent.  

- You need to keep 50% of your disk space free for Cassandra maintenance
  operations. If you expect your nodes to hold 500GB of data each, you
  will need a 1TB partition. Using non-default compaction such as
  LeveledCompactionStrategy can lower this waste.

- Much more information can be found in the [Cassandra 2.2 documentation](http://docs.datastax.com/en/cassandra/2.2/cassandra/planning/planPlanningAbout.html)


# Usage

To relate the Cassandra charm to a service that understands how to talk to
Cassandra using Thrift or the native Cassandra protocol::

    juju deploy cs:~cassandra-charmers/cqlsh
    juju add-relation cqlsh cassandra:database


Alternatively, if you require a superuser connection, use the
`database-admin` relation instead of `database`::

    juju deploy cs:~cassandra-charmers/cqlsh cqlsh-admin
    juju add-relation cqlsh-admin cassandra:database-admin

The cluster is configured to use the recommended 'snitch'
(GossipingPropertyFileSnitch), so you will need to configure replication of
your keyspaces using the NetworkTopologyStrategy replica placement strategy.
The datacenter is set in the Cassandra charm configuration, and provided
by the client interface if clients need to do this programatically. For
example, using the default datacenter named 'DC1':

    CREATE KEYSPACE IF NOT EXISTS mydata WITH REPLICATION =
    { 'class': 'NetworkTopologyStrategy', 'DC1': 3};


Although authentication is configured using the standard
PasswordAuthentication, by default no authorization is configured
and the provided credentials will have access to all data on the cluster.
For more granular permissions, you will need to set the authorizer
in the service configuration to CassandraAuthorizer and manually grant
permissions to the users.


# Contact Information

## General

[The Juju mailing list](https://lists.ubuntu.com/mailman/listinfo/juju)

## Charm

- [Cassandra Charm homepage](https://launchpad.net/cassandra-charm/)
- [Source Code](https://code.launchpad.net/~cassandra-charmers/cassandra-charm/+git/cassandra-charm)
- [Bug Reports](https://bugs.launchpad.net/cassandra-charm/)

## Cassandra

- [Apache Cassandra homepage](http://cassandra.apache.org/)
- [Cassandra Getting Started](http://wiki.apache.org/cassandra/GettingStarted)

## DataStax Enterprise

- [DataStax homepage](https://www.datastax.com)
