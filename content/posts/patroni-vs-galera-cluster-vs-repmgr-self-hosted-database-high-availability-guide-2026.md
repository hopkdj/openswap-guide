---
title: "Patroni vs Galera Cluster vs repmgr: Best Self-Hosted Database High Availability 2026"
date: 2026-04-17
tags: ["comparison", "guide", "self-hosted", "database", "high-availability"]
draft: false
description: "Complete guide to self-hosted database high availability in 2026. Compare Patroni, Galera Cluster, and repmgr for PostgreSQL and MySQL with Docker Compose setups, failover strategies, and production deployment best practices."
---

## Why Self-Host Database High Availability?

Every production system eventually faces the same reality: a single database node is a single point of failure. When that node crashes, your application goes down, transactions are lost, and users walk away. The traditional answer has been to pay a premium for managed database services that handle replication and failover automatically. But managed services come with steep costs, opaque pricing models, and limited control over how your data is actually protected.

Self-hosting database high availability puts you back in the driver's seat. You choose the replication topology, control the failover behavior, decide where data lives, and avoid the vendor markup that can triple your infrastructure bill at scale. Whether you're running a SaaS platform, an e-commerce storefront, or an internal tooling stack, the open-source HA solutions covered in this guide give you enterprise-grade resilience without the enterprise price tag.

Key benefits of self-hosting database HA:

- **Full control over failover logic** — tune RPO and RTO to your exact requirements instead of accepting a provider's defaults
- **Transparent costs** — no per-connection fees, storage premiums, or cross-region data transfer charges
- **Data sovereignty** — keep every byte within your own infrastructure, satisfying GDPR, HIPAA, and SOC 2 mandates
- **Custom replication topologies** — build cascading replicas, cross-region clusters, or hybrid read/write setups
- **No lock-in** — open-source tools that work with standard PostgreSQL and MySQL/MariaDB, not proprietary extensions

In this guide, we compare the three most widely deployed open-source database HA solutions: **Patroni** for PostgreSQL, **Galera Cluster** for MySQL and MariaDB, and **repmgr** for PostgreSQL. Each takes a fundamentally different approach to keeping your database online, and understanding those differences is critical for building a resilient architecture.

---

## How Database High Availability Works

Before diving into specific tools, it helps to understand the two broad strategies for database replication:

**Asynchronous replication** sends changes to replica nodes without waiting for confirmation. The primary node continues processing immediately, which means fast write performance but the risk of losing unreplicated transactions if the primary crashes. The replication lag is typically measured in milliseconds but can spike under heavy load.

**Synchronous replication** waits for at least one replica to confirm receipt of each transaction before committing. This guarantees zero data loss (RPO = 0) but adds latency to every write operation. Most production setups use synchronous replication for the nearest replica and asynchronous for distant ones.

The third key concept is **automatic failover**: when the primary node becomes unreachable, a promotion process elevates a replica to primary status, reconfigures the remaining replicas, and redirects application traffic. The speed and reliability of this process determines your Recovery Time Objective (RTO).

| Concept | Definition | Typical Target |
|---|---|---|
| RPO (Recovery Point Objective) | Maximum acceptable data loss | 0 (sync) to seconds (async) |
| RTO (Recovery Time Objective) | Maximum acceptable downtime | 10–60 seconds |
| Quorum | Minimum nodes needed for consensus | Majority (N/2 + 1) |
| Split brain | Two primaries accepting writes | Must be prevented at all costs |

---

## Patroni: PostgreSQL HA with Distributed Consensus

Patroni is widely considered the gold standard for PostgreSQL high availability. Originally developed by Zalando, it has become the go-to solution for production PostgreSQL clusters. Patroni uses a distributed consensus store — etcd, Consul, ZooKeeper, or [kubernetes](https://kubernetes.io/) — to manage cluster state and coordinate leader elections.

### Architecture

Patroni runs as a daemon alongside each PostgreSQL instance. The cluster elects one node as the **leader** (primary) using a distributed lock in the consensus store. The leader holds a TTL-based lease; if it fails to renew the lease within the configured timeout, the lease expires and a new leader election begins.

Replication is handled by PostgreSQL's native streaming replication (physical) or logical replication. Patroni manages the entire lifecycle: initializing replicas, promoting a new leader, reconfiguring `postgresql.conf` and `pg_hba.conf` dynamically, and running custom scripts on state transitions.

### [docker](https://www.docker.com/) Compose Setup

Here is a production-ready Patroni cluster with three PostgreSQL nodes and a three-node etcd quorum:

```yaml
version: "3.8"

services:
  etcd1:
    image: quay.io/coreos/etcd:v3.5.12
    command: >
      etcd
      --name etcd1
      --listen-client-urls http://0.0.0.0:2379
      --listen-peer-urls http://0.0.0.0:2380
      --advertise-client-urls http://etcd1:2379
      --initial-advertise-peer-urls http://etcd1:2380
      --initial-cluster etcd1=http://etcd1:2380,etcd2=http://etcd2:2380,etcd3=http://etcd3:2380
      --initial-cluster-state new
    volumes:
      - etcd1-data:/etcd-data
    networks:
      - ha-net

  etcd2:
    image: quay.io/coreos/etcd:v3.5.12
    command: >
      etcd
      --name etcd2
      --listen-client-urls http://0.0.0.0:2379
      --listen-peer-urls http://0.0.0.0:2380
      --advertise-client-urls http://etcd2:2379
      --initial-advertise-peer-urls http://etcd2:2380
      --initial-cluster etcd1=http://etcd1:2380,etcd2=http://etcd2:2380,etcd3=http://etcd3:2380
      --initial-cluster-state new
    volumes:
      - etcd2-data:/etcd-data
    networks:
      - ha-net

  etcd3:
    image: quay.io/coreos/etcd:v3.5.12
    command: >
      etcd
      --name etcd3
      --listen-client-urls http://0.0.0.0:2379
      --listen-peer-urls http://0.0.0.0:2380
      --advertise-client-urls http://etcd3:2379
      --initial-advertise-peer-urls http://etcd3:2380
      --initial-cluster etcd1=http://etcd1:2380,etcd2=http://etcd2:2380,etcd3=http://etcd3:2380
      --initial-cluster-state new
    volumes:
      - etcd3-data:/etcd-data
    networks:
      - ha-net

  patroni1:
    image: ghcr.io/zalando/patroni:3.3
    environment:
      PATRONI_NAME: patroni1
      PATRONI_SCOPE: pg-cluster
      PATRONI_RESTAPI_LISTEN: 0.0.0.0:8008
      PATRONI_RESTAPI_CONNECT_ADDRESS: patroni1:8008
      PATRONI_POSTGRESQL_LISTEN: 0.0.0.0:5432
      PATRONI_POSTGRESQL_CONNECT_ADDRESS: patroni1:5432
      PATRONI_ETCD3_HOSTS: etcd1:2379,etcd2:2379,etcd3:2379
      PATRONI_SUPERUSER_USERNAME: postgres
      PATRONI_SUPERUSER_PASSWORD: admin-secret
      PATRONI_REPLICATION_USERNAME: replicator
      PATRONI_REPLICATION_PASSWORD: repl-secret
      PATRONI_POSTGRESQL_DATA_DIR: /var/lib/postgresql/data/pgdata
      PATRONI_TAGS_DATA_DIR: /var/lib/postgresql/data/patroni
    volumes:
      - pg1-data:/var/lib/postgresql/data
    networks:
      - ha-net
    depends_on:
      - etcd1
      - etcd2
      - etcd3

  patroni2:
    image: ghcr.io/zalando/patroni:3.3
    environment:
      PATRONI_NAME: patroni2
      PATRONI_SCOPE: pg-cluster
      PATRONI_RESTAPI_LISTEN: 0.0.0.0:8008
      PATRONI_RESTAPI_CONNECT_ADDRESS: patroni2:8008
      PATRONI_POSTGRESQL_LISTEN: 0.0.0.0:5432
      PATRONI_POSTGRESQL_CONNECT_ADDRESS: patroni2:5432
      PATRONI_ETCD3_HOSTS: etcd1:2379,etcd2:2379,etcd3:2379
      PATRONI_SUPERUSER_USERNAME: postgres
      PATRONI_SUPERUSER_PASSWORD: admin-secret
      PATRONI_REPLICATION_USERNAME: replicator
      PATRONI_REPLICATION_PASSWORD: repl-secret
      PATRONI_POSTGRESQL_DATA_DIR: /var/lib/postgresql/data/pgdata
      PATRONI_TAGS_DATA_DIR: /var/lib/postgresql/data/patroni
    volumes:
      - pg2-data:/var/lib/postgresql/data
    networks:
      - ha-net
    depends_on:
      - etcd1
      - etcd2
      - etcd3

  patroni3:
    image: ghcr.io/zalando/patroni:3.3
    environment:
      PATRONI_NAME: patroni3
      PATRONI_SCOPE: pg-cluster
      PATRONI_RESTAPI_LISTEN: 0.0.0.0:8008
      PATRONI_RESTAPI_CONNECT_ADDRESS: patroni3:8008
      PATRONI_POSTGRESQL_LISTEN: 0.0.0.0:5432
      PATRONI_POSTGRESQL_CONNECT_ADDRESS: patroni3:5432
      PATRONI_ETCD3_HOSTS: etcd1:2379,etcd2:2379,etcd3:2379
      PATRONI_SUPERUSER_USERNAME: postgres
      PATRONI_SUPERUSER_PASSWORD: admin-secret
      PATRONI_REPLICATION_USERNAME: replicator
      PATRONI_REPLICATION_PASSWORD: repl-secret
      PATRONI_POSTGRESQL_DATA_DIR: /var/lib/postgresql/data/pgdata
      PATRONI_TAGS_DATA_DIR: /var/lib/postgresql/data/patroni
    volumes:
      - pg3-data:/var/lib/postgresql/data
    networks:
      - ha-net
    depends_on:
      - etcd1
      - etcd2
      - etcd3

  haproxy:
    image: haproxy:2.9
    ports:
      - "5432:5432"
      - "8404:8404"
    volumes:
      - ./haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
    networks:
      - ha-net
    depends_on:
      - patroni1
      - patroni2
      - patroni3

volumes:
  etcd1-data:
  etcd2-data:
  etcd3-data:
  pg1-data:
  pg2-data:
  pg3-data:

networks:
  ha-net:
    driver: bridge
```

The HAProxy configuration routes writes to the leader and reads to all replicas:

```cfg
global
    log stdout format raw local0
    stats socket /run/haproxy/admin.sock mode 660 level admin

defaults
    log     global
    mode    tcp
    option  tcplog
    timeout connect 5s
    timeout client  30s
    timeout server  30s

frontend fe_postgresql
    bind *:5432
    default_backend be_postgresql_write

backend be_postgresql_write
    option httpchk GET /leader
    http-check expect status 200
    default-server inter 3s fall 3 rise 2 on-marked-down shutdown-sessions
    server patroni1 patroni1:5432 check port 8008
    server patroni2 patroni2:5432 check port 8008
    server patroni3 patroni3:5432 check port 8008

backend be_postgresql_read
    option httpchk GET /replica
    http-check expect status 200
    default-server inter 3s fall 3 rise 2 on-marked-down shutdown-sessions
    server patroni1 patroni1:5432 check port 8008
    server patroni2 patroni2:5432 check port 8008
    server patroni3 patroni3:5432 check port 8008
```

### Key Patroni Features

- **Automatic failover** in 10–30 seconds using distributed consensus
- **Dynamic configuration** — change PostgreSQL settings without restarting via the REST API
- **Custom scripts** — run shell scripts on leader change, restart, or switchover events
- **Standby cluster** support for cross-region disaster recovery
- **pgBackRest and WAL-G integration** for automated backup management
- **Kubernetes native** — the Patroni Operator runs directly on K8s without etcd

### Monitoring and Operations

Patroni exposes a REST API on port 8008 with health endpoints:

```bash
# Check cluster health
curl -s http://patroni1:8008/cluster | python3 -m json.tool

# Trigger a manual switchover
curl -X POST http://patroni1:8008/switchover \
  -d '{"leader": "patroni1", "candidate": "patroni2"}'

# Check individual node status
curl -s http://patroni2:8008/patroni | python3 -m json.tool

# Reload configuration without restart
curl -X POST http://patroni1:8008/reload
```

---

## Galera Cluster: Synchronous Multi-Master for MySQL and MariaDB

Galera Cluster takes a fundamentally different approach from Patroni. Instead of a single primary with read replicas, Galera provides **true multi-master replication** — every node can accept writes simultaneously, and changes are synchronously replicated across the cluster using a certification-based replication protocol.

### Architecture

Galera integrates directly into MySQL and MariaDB through a wsrep (write-set replication) plugin. When a transaction commits on any node, the write set is broadcast to all other nodes via group communication. Each node independently certifies the write set against its local state — if the certification passes, the transaction is applied locally; if it fails (due to a conflict), the transaction is rolled back on the originating node.

This model eliminates the need for leader elections entirely. Every node is equal, and the cluster continues operating as long as a majority of nodes remain connected.

### Docker Compose Setup

A three-node Galera Cluster with MariaDB:

```yaml
version: "3.8"

services:
  galera1:
    image: mariadb:11.4
    environment:
      MARIADB_ROOT_PASSWORD: root-secret
      MARIADB_DATABASE: appdb
      MARIADB_GALERA_CLUSTER_NAME: galera-cluster
      MARIADB_GALERA_CLUSTER_ADDRESS: gcomm://
      MARIADB_GALERA_NODE_NAME: galera1
      MARIADB_GALERA_MARIABACKUP_USER: mariabackup
      MARIADB_GALERA_MARIABACKUP_PASSWORD: backup-secret
    command: >
      --wsrep_on=ON
      --wsrep_provider=/usr/lib/galera/libgalera_smm.so
      --wsrep_cluster_address=gcomm://galera1,galera2,galera3
      --wsrep_cluster_name=galera-cluster
      --wsrep_node_name=galera1
      --wsrep_node_address=galera1
      --wsrep_sst_method=mariabackup
      --binlog_format=ROW
      --innodb_autoinc_lock_mode=2
      --innodb_flush_log_at_trx_commit=2
    ports:
      - "3306:3306"
      - "4567:4567"
      - "4568:4568"
      - "4444:4444"
    volumes:
      - galera1-data:/var/lib/mysql
    networks:
      - galera-net

  galera2:
    image: mariadb:11.4
    environment:
      MARIADB_ROOT_PASSWORD: root-secret
      MARIADB_GALERA_CLUSTER_NAME: galera-cluster
      MARIADB_GALERA_CLUSTER_ADDRESS: gcomm://galera1,galera2,galera3
      MARIADB_GALERA_NODE_NAME: galera2
      MARIADB_GALERA_MARIABACKUP_USER: mariabackup
      MARIADB_GALERA_MARIABACKUP_PASSWORD: backup-secret
    command: >
      --wsrep_on=ON
      --wsrep_provider=/usr/lib/galera/libgalera_smm.so
      --wsrep_cluster_address=gcomm://galera1,galera2,galera3
      --wsrep_cluster_name=galera-cluster
      --wsrep_node_name=galera2
      --wsrep_node_address=galera2
      --wsrep_sst_method=mariabackup
      --binlog_format=ROW
      --innodb_autoinc_lock_mode=2
      --innodb_flush_log_at_trx_commit=2
    volumes:
      - galera2-data:/var/lib/mysql
    networks:
      - galera-net

  galera3:
    image: mariadb:11.4
    environment:
      MARIADB_ROOT_PASSWORD: root-secret
      MARIADB_GALERA_CLUSTER_NAME: galera-cluster
      MARIADB_GALERA_CLUSTER_ADDRESS: gcomm://galera1,galera2,galera3
      MARIADB_GALERA_NODE_NAME: galera3
      MARIADB_GALERA_MARIABACKUP_USER: mariabackup
      MARIADB_GALERA_MARIABACKUP_PASSWORD: backup-secret
    command: >
      --wsrep_on=ON
      --wsrep_provider=/usr/lib/galera/libgalera_smm.so
      --wsrep_cluster_address=gcomm://galera1,galera2,galera3
      --wsrep_cluster_name=galera-cluster
      --wsrep_node_name=galera3
      --wsrep_node_address=galera3
      --wsrep_sst_method=mariabackup
      --binlog_format=ROW
      --innodb_autoinc_lock_mode=2
      --innodb_flush_log_at_trx_commit=2
    volumes:
      - galera3-data:/var/lib/mysql
    networks:
      - galera-net

  haproxy:
    image: haproxy:2.9
    ports:
      - "3306:3306"
    volumes:
      - ./haproxy-galera.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
    networks:
      - galera-net

volumes:
  galera1-data:
  galera2-data:
  galera3-data:

networks:
  galera-net:
    driver: bridge
```

For the Galera HAProxy configuration, all nodes accept writes, so the backend is simple round-robin:

```cfg
global
    log stdout format raw local0

defaults
    log     global
    mode    tcp
    option  tcplog
    timeout connect 5s
    timeout client  30s
    timeout server  30s

frontend fe_mysql
    bind *:3306
    default_backend be_galera

backend be_galera
    option httpchk
    http-check send meth GET uri /
    http-check expect string ok
    default-server inter 3s fall 3 rise 2
    server galera1 galera1:3306 check
    server galera2 galera2:3306 check
    server galera3 galera3:3306 check
```

### Key Galera Features

- **True multi-master** — every node accepts reads and writes simultaneously
- **Synchronous replication** — zero data loss guarantee (RPO = 0)
- **Automatic node provisioning** — new nodes sync via SST (State Snapshot Transfer) using MariaDB Backup or rsync
- **Parallel replication** — Galera 4 supports parallel apply for improved throughput
- **Flow control** — automatically throttles fast writers if replicas fall behind
- **No single point of failure** — no leader election, no consensus store required

### Monitoring Galera

```bash
# Check cluster status from any node
docker exec galera1 mariadb -uroot -proot-secret \
  -e "SHOW GLOBAL STATUS LIKE 'wsrep_%';"

# Key metrics to watch:
# wsrep_cluster_size        — number of nodes in the cluster
# wsrep_local_state_comment — Synced / Joiner / Donor / Desync
# wsrep_ready               — ON (healthy) / OFF (problem)
# wsrep_connected           — ON / OFF
# wsrep_flow_control_paused — replication throttling ratio (0.0 = no throttling)

# Check for replication conflicts
docker exec galera1 mariadb -uroot -proot-secret \
  -e "SHOW GLOBAL STATUS LIKE 'wsrep_local_cert_failures';"
```

---

## repmgr: PostgreSQL Replication Manager

repmgr is the traditional PostgreSQL replication management tool, developed by 2ndQuadrant (now part of EDB). Unlike Patroni's distributed consensus approach, repmgr manages replication through a **metadata schema** stored inside the PostgreSQL cluster itself, combined with a monitoring daemon that watches node health.

### Architecture

repmgr registers each node in a dedicated `repmgr` database that tracks the cluster topology: which node is primary, which are standbys, and their replication relationships. The `repmgrd` daemon runs on each node, monitoring the upstream connection and triggering failover when the primary becomes unreachable.

The key distinction from Patroni is that repmgr's failover requires a **witness node** or a tie-breaking mechanism to prevent split brain, and the failover process relies on monitoring daemons rather than a distributed consensus protocol.

### Docker Compose Setup

```yaml
version: "3.8"

services:
  primary:
    image: bitnami/postgresql-repmgr:16
    environment:
      POSTGRESQL_POSTGRES_PASSWORD: admin-secret
      POSTGRESQL_USERNAME: repmgr
      POSTGRESQL_PASSWORD: repmgr-secret
      POSTGRESQL_DATABASE: appdb
      REPMGR_PRIMARY_HOST: primary
      REPMGR_PARTNER_NODES: primary,standby1,standby2
      REPMGR_NODE_NAME: node1
      REPMGR_NODE_NETWORK_NAME: primary
      REPMGR_PORT_NUMBER: 5432
      REPMGR_LOG_LEVEL: NOTICE
      REPMGR_CONNECT_TIMEOUT: 5
      REPMGR_REPLICATION_TIMEOUT: 30s
      REPMGR_START_TIMEOUT: 30s
      REPMGR_PROMOTE_TIMEOUT: 30s
    ports:
      - "5432:5432"
    volumes:
      - primary-data:/bitnami/postgresql
    networks:
      - repmgr-net

  standby1:
    image: bitnami/postgresql-repmgr:16
    environment:
      POSTGRESQL_POSTGRES_PASSWORD: admin-secret
      POSTGRESQL_USERNAME: repmgr
      POSTGRESQL_PASSWORD: repmgr-secret
      POSTGRESQL_DATABASE: appdb
      REPMGR_PRIMARY_HOST: primary
      REPMGR_PARTNER_NODES: primary,standby1,standby2
      REPMGR_NODE_NAME: node2
      REPMGR_NODE_NETWORK_NAME: standby1
      REPMGR_PORT_NUMBER: 5432
      REPMGR_LOG_LEVEL: NOTICE
      REPMGR_CONNECT_TIMEOUT: 5
    volumes:
      - standby1-data:/bitnami/postgresql
    networks:
      - repmgr-net
    depends_on:
      - primary

  standby2:
    image: bitnami/postgresql-repmgr:16
    environment:
      POSTGRESQL_POSTGRES_PASSWORD: admin-secret
      POSTGRESQL_USERNAME: repmgr
      POSTGRESQL_PASSWORD: repmgr-secret
      POSTGRESQL_DATABASE: appdb
      REPMGR_PRIMARY_HOST: primary
      REPMGR_PARTNER_NODES: primary,standby1,standby2
      REPMGR_NODE_NAME: node3
      REPMGR_NODE_NETWORK_NAME: standby2
      REPMGR_PORT_NUMBER: 5432
      REPMGR_LOG_LEVEL: NOTICE
      REPMGR_CONNECT_TIMEOUT: 5
    volumes:
      - standby2-data:/bitnami/postgresql
    networks:
      - repmgr-net
    depends_on:
      - primary

volumes:
  primary-data:
  standby1-data:
  standby2-data:

networks:
  repmgr-net:
    driver: bridge
```

### Key repmgr Features

- **Simple topology management** — register, unregister, and follow commands for manual control
- **Built-in monitoring daemon** — `repmgrd` watches the primary and can auto-promote
- **Standby cloning** — `repmgr standby clone` creates replicas from any healthy node
- **Witness server** — a lightweight node that breaks ties during failover without holding data
- **Event notifications** — hook scripts for failover, switchover, and node state changes
- **Lower com[plex](https://www.plex.tv/)ity** — no external consensus store required, just PostgreSQL itself

### Operations with repmgr

```bash
# Show cluster status
docker exec primary repmgr -f /etc/repmgr.conf cluster show

# Register a new standby
docker exec standby1 repmgr -f /etc/repmgr.conf standby register --force

# Manual switchover
docker exec standby1 repmgr -f /etc/repmgr.conf standby switchover --siblings-follow

# Manual failover (when primary is down)
docker exec standby1 repmgr -f /etc/repmgr.conf standby promote

# Rejoin a former primary as a standby
docker exec primary repmgr -f /etc/repmgr.conf node rejoin \
  -d "host=standby1 dbname=repmgr user=repmgr" --force-rewind
```

---

## Head-to-Head Comparison

| Feature | Patroni | Galera Cluster | repmgr |
|---|---|---|---|
| **Database** | PostgreSQL only | MySQL / MariaDB | PostgreSQL only |
| **Replication Model** | Primary + async/sync replicas | Multi-master (all nodes RW) | Primary + async streaming |
| **Consensus** | etcd / Consul / ZooKeeper / K8s | Built-in (group communication) | repmgr metadata DB + witness |
| **Failover Time** | 10–30 seconds | Instant (no failover needed) | 30–60 seconds |
| **Data Loss Risk** | Depends on sync config | Zero (synchronous) | Depends on sync config |
| **Write Scalability** | Single writer | All nodes accept writes | Single writer |
| **Read Scalability** | N-1 replicas | All N nodes | N-1 replicas |
| **Network Partitions** | Handled by consensus quorum | Cluster may split; needs bootstrap | Manual intervention often needed |
| **External Dependencies** | Yes (consensus store) | None | None (optional witness) |
| **Configuration Complexity** | Medium (YAML + etcd) | Medium (my.cnf + wsrep) | Low (repmgr.conf) |
| **Automatic Rejoin** | Yes (former primary becomes replica) | N/A (all nodes equal) | Manual or via hook scripts |
| **Backup Integration** | pgBackRest, WAL-G, Barman | Mariabackup, mysqldump, XtraBackup | pgBackRest, WAL-G, Barman |
| **Kubernetes Support** | Excellent (native operator) | Moderate (StatefulSet) | Moderate (custom operator) |
| **Geographic Distribution** | Good (standby cluster mode) | Poor (latency-sensitive sync) | Moderate (cascading replicas) |
| **License** | MIT | GPLv2 (Galera) + GPL (MariaDB) | PostgreSQL License |
| **Best For** | Production PostgreSQL, K8s | MySQL/MariaDB, multi-master workloads | Simpler PostgreSQL setups |

---

## Choosing the Right Solution

### Choose Patroni if:

- You run PostgreSQL and need production-grade automatic failover
- You are deploying on Kubernetes (the Patroni Operator is excellent)
- You want the ability to dynamically reconfigure PostgreSQL at runtime
- You need geographic distribution with standby clusters
- You already operate etcd or Consul for other services

Patroni is the safest choice for most PostgreSQL deployments. The distributed consensus approach eliminates split-brain scenarios, and the REST API enables deep automation. The learning curve comes from managing the consensus store, but that investment pays off in operational reliability.

### Choose Galera Cluster if:

- You run MySQL or MariaDB and need multi-master write capability
- Your application writes to multiple nodes simultaneously (e.g., geographically distributed writes)
- Zero data loss is non-negotiable and you can tolerate the write latency
- You want HA without external dependencies like etcd
- Your workload is read-heavy with moderate write volume

Galera excels when you need every node to accept writes. However, be aware that write-heavy workloads with large transactions will experience certification conflicts and rollbacks. The synchronous replication also means that network latency between nodes directly impacts write performance — keep nodes in the same data center or use low-latency connections.

### Choose repmgr if:

- You want the simplest possible PostgreSQL HA setup
- You do not want to manage an external consensus store
- Your team is already familiar with PostgreSQL administration
- You prefer manual or semi-automatic failover with explicit control
- You are running a small cluster (2–3 nodes) where the overhead of etcd is unjustified

repmgr is the most straightforward option but requires more operational discipline. Without a consensus store, you need to be careful about split-brain scenarios and ensure your witness node or tie-breaking strategy is properly configured.

---

## Production Best Practices

Regardless of which tool you choose, these practices are essential for production database HA:

**1. Test failover regularly.** Schedule quarterly failover drills. Automated monitoring tells you when things are broken, but only an actual failover test proves your recovery process works.

**2. Monitor replication lag continuously.** Use built-in replication delay metrics and alert when lag exceeds your RPO threshold. For Patroni, check `pg_stat_replication`. For Galera, monitor `wsrep_flow_control_paused`.

```sql
-- PostgreSQL replication lag (Patroni, repmgr)
SELECT client_addr,
       state,
       sent_lsn - write_lsn AS write_lag_bytes,
       write_lsn - flush_lsn AS flush_lag_bytes,
       flush_lsn - replay_lsn AS replay_lag_bytes
FROM pg_stat_replication;
```

**3. Use connection pooling.** Place PgBouncer or ProxySQL in front of your cluster to handle connection management, failover re-routing, and connection limits. Applications should never connect directly to database nodes in an HA setup.

**4. Separate WAL/binlog from data.** Store transaction logs on a different physical disk or volume than the data directory. This prevents I/O contention and simplifies backup strategies.

**5. Plan your backup strategy.** HA is not a backup strategy. You still need point-in-time recovery capable backups. For PostgreSQL, use WAL-G or pgBackRest with off-site storage. For MariaDB, use Mariabackup with incremental backups.

**6. Size your consensus store properly.** If using Patroni with etcd, run at least three etcd nodes on separate failure domains. The etcd cluster should have dedicated fast storage (SSD) since it handles frequent write operations for leader lease renewal.

**7. Document your runbook.** When the primary fails at 3 AM, your team should not be reading documentation for the first time. Maintain a runbook with step-by-step recovery procedures, including manual promotion commands, DNS update steps, and application reconnection procedures.

---

## Summary

| Scenario | Recommended Tool |
|---|---|
| PostgreSQL on Kubernetes | Patroni (with K8s operator) |
| PostgreSQL, simple setup | repmgr |
| PostgreSQL, production-grade | Patroni + etcd + HAProxy |
| MySQL/MariaDB, multi-master writes | Galera Cluster |
| MySQL/MariaDB, standard HA | MariaDB primary + replicas (no Galera) |
| Cross-region PostgreSQL | Patroni with standby cluster |
| Lowest operational complexity | repmgr |
| Highest availability guarantee | Patroni or Galera (depending on database) |

Database high availability is not a set-and-forget concern. The tools covered here give you the building blocks, but achieving reliable HA requires testing, monitoring, and ongoing operational discipline. Start with the setup that matches your team's expertise, test failover thoroughly before going live, and iterate as your requirements evolve.

## Frequently Asked Questions (FAQ)

### Which one should I choose in 2026?

The best choice depends on your specific requirements:

- **For beginners**: Start with the simplest option that covers your core use case
- **For production**: Choose the solution with the most active community and documentation
- **For teams**: Look for collaboration features and user management
- **For privacy**: Prefer fully open-source, self-hosted options with no telemetry

Refer to the comparison table above for detailed feature breakdowns.

### Can I migrate between these tools?

Most tools support data import/export. Always:
1. Backup your current data
2. Test the migration on a staging environment
3. Check official migration guides in the documentation

### Are there free versions available?

All tools in this guide offer free, open-source editions. Some also provide paid plans with additional features, priority support, or managed hosting.

### How do I get started?

1. Review the comparison table to identify your requirements
2. Visit the official documentation (links provided above)
3. Start with a Docker Compose setup for easy testing
4. Join the community forums for troubleshooting
