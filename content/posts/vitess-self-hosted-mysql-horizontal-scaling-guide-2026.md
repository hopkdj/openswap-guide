---
title: "Vitess: Self-Hosted MySQL Horizontal Scaling Guide 2026"
date: 2026-04-18
tags: ["comparison", "guide", "self-hosted", "database", "mysql", "scalability"]
draft: false
description: "Complete guide to deploying Vitess for horizontal MySQL scaling. Learn sharding, connection pooling, and production deployment with Docker Compose."
---

When a single MySQL server can no longer handle your traffic, you face a critical decision: vertical scaling (bigger hardware) or horizontal scaling (more servers). [Vitess](https://vitess.io/) — the open-source database clustering system originally built at YouTube — makes horizontal MySQL scaling practical for self-hosted deployments. With over 20,900 GitHub stars and active development by a vibrant community, Vitess has proven itself at petabyte scale in production environments worldwide.

This guide covers what Vitess is, how its architecture works, and how to deploy a sharded MySQL cluster using Docker Compose.

## Why Self-Host MySQL at Scale

MySQL is the world's most popular open-source relational database, but as your application grows, a single instance hits bottlenecks:

- **Connection limits** — MySQL caps concurrent connections, and connection-heavy apps exhaust them quickly
- **Storage ceilings** — Even with NVMe SSDs, a single node's IOPS and capacity become limiting factors
- **Write throughput** — Read replicas help with reads, but write scaling requires actual sharding
- **Operational complexity** — Manual sharding, rebalancing, and failover are error-prone without a coordination layer

Managed solutions like Amazon Aurora or PlanetScale handle this complexity for you, but they come with vendor lock-in, unpredictable pricing, and data residency constraints. Self-hosting with Vitess gives you full control over your database infrastructure while providing the same horizontal scaling capabilities.

For a broader look at distributed SQL alternatives, check out our [CockroachDB vs YugabyteDB vs TiDB comparison](../cockroachdb-vs-yugabyte-vs-tidb-distributed-sql-guide-2026/) — Vitess takes a fundamentally different approach by keeping MySQL as the storage engine and adding a coordination layer on top.

## What Is Vitess?

Vitess is a database clustering system for horizontal scaling of MySQL (and compatible databases like MariaDB and Percona Server). It was created at YouTube in 2010 to handle their massive database growth, open-sourced in 2014, and became a Cloud Native Computing Foundation (CNCF) graduated project in 2021 — the same tier as Kubernetes, Prometheus, and Envoy.

### Key Capabilities

| Feature | Description |
|---------|-------------|
| **Transparent Sharding** | Split tables across multiple MySQL instances without changing application code |
| **Connection Pooling** | Reduce MySQL connection overhead with built-in pooling (like a proxy) |
| **Online DDL** | Run schema migrations without downtime using `gh-ost` integration |
| **Resharding** | Split or merge shards while the database remains online |
| **Topology Management** | Automate MySQL replication, failover, and backup coordination |
| **VTGate Proxy** | SQL-aware proxy that routes queries to the correct shard |
| **VTAdmin Dashboard** | Web-based UI for cluster management and monitoring |

### Architecture Overview

Vitess uses several components that work together:

- **VTGate** — A stateless proxy layer that receives application connections and routes queries to the right shard. Applications connect to VTGate as if it were a regular MySQL server.
- **VTTablet** — Runs alongside each MySQL instance, managing queries, connection pooling, and health checks.
- **VTCTLD** — The control plane daemon for topology management, schema tracking, and orchestration commands.
- **VTORC** — Orchestrator for MySQL topology management, handling failover and replication health.
- **VTAdmin** — Web-based administrative UI for cluster visualization and management.
- **Topology Service** — Usually etcd or ZooKeeper, stores cluster metadata and coordinates distributed state.

## Getting Started with Vitess Using Docker Compose

The easiest way to experiment with Vitess is the official Docker Compose example in the `examples/compose` directory. Here's a simplified setup that demonstrates the core architecture.

### Prerequisites

```bash
# Ensure you have Docker and Docker Compose installed
docker --version
docker compose version

# Clone the Vitess repository
git clone https://github.com/vitessio/vitess.git
cd vitess/examples/compose
```

### Docker Compose Configuration

The official compose file defines the full Vitess stack. Here are the core services:

```yaml
name: vitess-example

services:
  etcd:
    image: quay.io/coreos/etcd:v3.5.21
    command:
      - etcd
      - --data-dir=/etcd-data
      - --listen-client-urls=http://0.0.0.0:2379
      - --advertise-client-urls=http://etcd:2379
    healthcheck:
      test: ["CMD", "etcdctl", "endpoint", "health"]
      interval: 5s
      timeout: 3s
      retries: 30

  vtctld:
    image: vitess/vitess:latest
    command: ["/vt/scripts/vtctld-up.sh"]
    ports:
      - "15000:15000"   # VTCTLD web UI
      - "15999:15999"   # gRPC
    depends_on:
      etcd:
        condition: service_healthy

  vtgate:
    image: vitess/vitess:latest
    command: ["/vt/scripts/vtgate-up.sh"]
    ports:
      - "15306:15306"   # MySQL protocol port (connect here)
      - "15001:15001"   # HTTP status
    depends_on:
      vtctld:
        condition: service_healthy

  vtorc:
    image: vitess/vitess:latest
    command: ["/vt/scripts/vtorc-up.sh"]
    ports:
      - "16000:16000"   # VTORC web UI
    depends_on:
      vtctld:
        condition: service_healthy

  vtadmin:
    image: vitess/vitess:latest
    command: ["/vt/scripts/vtadmin-up.sh"]
    ports:
      - "14200:14200"   # VTAdmin API
    depends_on:
      vtctld:
        condition: service_healthy
```

### Initialize the Cluster

```bash
# Start etcd (topology service)
docker compose up -d etcd

# Wait for etcd to be healthy, then start the control plane
docker compose up -d vtctld

# Initialize the cluster
./101_initial_cluster.sh

# Start VTGate (the application-facing proxy)
docker compose up -d vtgate

# Start VTORC (topology orchestrator)
docker compose up -d vtorc
```

### Connect to Vitess

Once running, connect to VTGate on port 15306 using any MySQL client:

```bash
# Connect using the mysql CLI
mysql -h 127.0.0.1 -P 15306 -u user

# Or connect from your application
# MySQL connection string: mysql://user:password@localhost:15306/commerce
```

VTGate speaks the MySQL protocol, so your application code needs zero changes — just point your connection string at VTGate instead of a direct MySQL instance.

## Vitess vs Alternative Scaling Approaches

When scaling MySQL, you have several architectural options. Here's how they compare:

| Feature | Vitess | TiDB | ProxySQL + Manual Sharding | MySQL Group Replication |
|---------|--------|------|---------------------------|------------------------|
| **Storage Engine** | MySQL (InnoDB) | TiKV (custom) | MySQL (InnoDB) | MySQL (InnoDB) |
| **Horizontal Writes** | Yes (sharding) | Yes (distributed) | No (read scaling only) | Limited |
| **Sharding** | Automatic, online | Automatic | Manual application logic | N/A |
| **Online Resharding** | Yes | Yes | No | No |
| **Connection Pooling** | Built-in (VTGate) | Built-in | ProxySQL required | No |
| **Online DDL** | Yes (gh-ost) | Yes | No | Partial |
| **MySQL Compatibility** | 100% | MySQL syntax | 100% | 100% |
| **Learning Curve** | Moderate | Moderate | Low (per node) | Moderate |
| **Production Users** | YouTube, Slack, Square | PingCAP customers | Thousands of companies | MySQL Enterprise users |
| **GitHub Stars** | 20,900+ | 36,000+ | 5,300+ | N/A (in MySQL) |
| **License** | Apache 2.0 | Apache 2.0 | GPL 3.0 | GPL 2.0 |

Vitess's key advantage is that it lets you keep MySQL as your storage engine — no migration to a different database system, no query compatibility concerns, and the ability to leverage existing MySQL tooling and expertise. If you want to compare distributed SQL databases more broadly, our [CockroachDB vs YugabyteDB vs TiDB guide](../cockroachdb-vs-yugabyte-vs-tidb-distributed-sql-guide-2026/) covers that landscape in depth.

## Sharding Strategy and VSchema

Vitess uses a **VSchema** (Vitess Schema) to define how tables are distributed across shards. Here's a typical vschema configuration:

```json
{
  "sharded": true,
  "vindexes": {
    "hash": {
      "type": "hash"
    }
  },
  "tables": {
    "users": {
      "column_vindexes": [
        {
          "column": "user_id",
          "name": "hash"
        }
      ]
    },
    "orders": {
      "column_vindexes": [
        {
          "column": "user_id",
          "name": "hash"
        }
      ]
    },
    "products": {
      "column_vindexes": [
        {
          "column": "id",
          "name": "hash"
        }
      ]
    }
  }
}
```

This configuration shards `users`, `orders`, and `products` tables by a hash of their primary key. The hash vindex ensures even distribution across shards and avoids hotspotting.

### Online Resharding

One of Vitess's most powerful features is online resharding — splitting or merging shards without downtime:

```bash
# Split shard -80- into -40 and 40-80
vtctlclient SplitShard -splits=2 commerce/0

# Wait for copy to complete, then switch traffic
vtctlclient MigrateServedReads commerce/-40
vtctlclient MigrateServedWrites commerce/-40
```

During resharding, Vitess copies data from the source shard to the destination shards while continuing to serve reads and writes. Once the copy is complete, traffic is switched atomically.

For database high availability patterns beyond sharding, see our [Patroni vs Galera Cluster vs repmgr guide](../patroni-vs-galera-cluster-vs-repmgr-self-hosted-database-high-availability-guide-2026/) — Vitess handles horizontal scaling while those tools focus on vertical HA within a single shard.

## Production Deployment Considerations

### Resource Planning

A minimum production Vitess deployment requires:

| Component | CPU | Memory | Storage |
|-----------|-----|--------|---------|
| VTGate (per instance) | 2 cores | 4 GB | Minimal |
| VTTablet (per MySQL) | 4 cores | 8 GB | Depends on data |
| VTCTLD | 2 cores | 4 GB | Minimal |
| etcd (3 nodes) | 2 cores | 4 GB | 10-50 GB SSD |
| MySQL (per shard) | 4-8 cores | 16-32 GB | SSD required |

### Connection Pooling Configuration

VTGate's built-in connection pooling dramatically reduces the number of connections to MySQL backend servers:

```yaml
# vtgate startup flags for connection pooling
vtgate:
  - -queryserver-config-pool-size=16       # Pool size per tablet
  - -queryserver-config-stream-pool-size=8 # Streaming pool
  - -queryserver-config-transaction-cap=20 # Transaction pool
  - -queryserver-config-query-timeout=30s  # Query timeout
  - -queryserver-config-idle-timeout=1800s # Idle connection timeout
```

This is particularly valuable for connection-heavy applications. If you're already using connection pooling tools, our [ProxySQL vs PgBouncer vs Odyssey comparison](../pgbouncer-vs-proxysql-vs-odyssey-self-hosted-database-connection-pooling-guide-2026/) covers alternatives — though VTGate's pooling is tightly integrated with Vitess's routing logic.

### Monitoring and Observability

Vitess exposes Prometheus metrics on all components:

```bash
# VTGate metrics endpoint
curl http://localhost:15001/debug/vars

# VTTablet metrics (example tablet)
curl http://localhost:15100/debug/vars

# VTAdmin dashboard for cluster overview
open http://localhost:14201
```

Key metrics to monitor: query latency by shard, connection pool utilization, replication lag, and QPS per VTGate instance.

## When to Choose Vitess

**Use Vitess when:**
- Your MySQL database has outgrown a single node
- You need automatic sharding with online resharding
- You want to keep MySQL compatibility (no query rewrites)
- Your team has MySQL expertise but needs horizontal scale
- You want to avoid vendor lock-in from managed database services

**Consider alternatives when:**
- You need distributed transactions across shards (Vitess has limited support)
- Your workload is read-heavy and read replicas suffice (use MySQL Group Replication)
- You're starting from scratch with a small dataset (premature optimization)
- You need full ACID across distributed nodes (consider TiDB or CockroachDB)

## FAQ

### Is Vitess production-ready?

Yes. Vitess is a CNCF graduated project (the highest maturity level) and has been used in production at YouTube, Slack, Square, and many other companies since 2010. It handles billions of queries per day at its largest deployments.

### Does Vitess replace MySQL?

No. Vitess sits on top of MySQL and uses standard MySQL (InnoDB) as its storage engine. You keep full MySQL compatibility, and your existing MySQL tools, backups, and expertise all remain applicable. Vitess adds a coordination and routing layer.

### Can I migrate an existing MySQL database to Vitess?

Yes. Vitess supports online migration using its `MoveTables` workflow. You can run your existing MySQL database alongside Vitess, copy data while the source remains live, and switch traffic with minimal downtime.

### What MySQL versions does Vitess support?

Vitess supports MySQL 8.0 and 8.4, as well as compatible forks like Percona Server and MariaDB (with some limitations). Always check the latest Vitess documentation for the specific version compatibility matrix.

### How many shards can Vitess handle?

Vitess has been tested with hundreds of shards in production. The practical limit depends on your topology service (etcd or ZooKeeper) and the number of VTGate instances. Most deployments operate comfortably with 8-64 shards.

### Does Vitess support cross-shard queries?

Yes, but with caveats. VTGate can execute cross-shard scatter-gather queries (querying all shards and merging results), but these are slower than single-shard queries. For optimal performance, design your schema to minimize cross-shard joins by choosing appropriate vindexes.

### What is the difference between Vitess and PlanetScale?

PlanetScale is a managed database service built on top of Vitess. When you use PlanetScale, you're using Vitess under the hood, but PlanetScale handles all the infrastructure, monitoring, and operations. Self-hosting Vitess gives you full control but requires you to manage the infrastructure yourself.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Vitess: Self-Hosted MySQL Horizontal Scaling Guide 2026",
  "description": "Complete guide to deploying Vitess for horizontal MySQL scaling. Learn sharding, connection pooling, and production deployment with Docker Compose.",
  "datePublished": "2026-04-18",
  "dateModified": "2026-04-18",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://hopkdj.github.io/openswap-guide/logo.png"
    }
  }
}
</script>
