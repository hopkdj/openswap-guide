---
title: "Vitess vs Citus vs ShardingSphere: Self-Hosted Database Sharding Guide 2026"
date: 2026-04-25
tags: ["comparison", "guide", "self-hosted", "database", "scaling", "sharding"]
draft: false
description: "Compare Vitess, Citus, and Apache ShardingSphere for self-hosted database sharding. Complete guide with Docker Compose configs, architecture comparison, and decision framework."
---

When a single database instance can no longer handle your query load or data volume, sharding becomes the natural next step. Rather than paying for managed database services at hyperscale pricing, you can deploy battle-tested sharding infrastructure on your own hardware. This guide compares three leading open-source solutions — **Vitess**, **Citus**, and **Apache ShardingSphere** — to help you choose the right self-hosted database sharding platform for your workload.

## Why Self-Host Database Sharding

Database sharding splits a large dataset across multiple independent database instances (shards), distributing read/write load and enabling horizontal scaling that a single server cannot achieve.

**Self-hosting sharding infrastructure offers several advantages:**

- **Cost control** — Managed sharding services (Amazon Aurora, Azure Cosmos DB, Google Cloud Spanner) charge premium per-query or per-node pricing. Self-hosted solutions run on commodity hardware or standard cloud VMs.
- **Data sovereignty** — Keep all data within your own infrastructure, meeting compliance requirements like GDPR, HIPAA, or SOC 2 without relying on third-party data processors.
- **No vendor lock-in** — Open-source sharding tools let you migrate between cloud providers or on-premises environments without changing your application layer.
- **Full observability** — Direct access to query logs, performance metrics, and internal state without paying for enterprise monitoring add-ons.

The trade-off is operational complexity: you need to provision, monitor, and maintain the sharding layer yourself. The three tools below each approach this challenge differently.

## Vitess: MySQL Horizontal Scaling at Scale

**Vitess** (20,930 GitHub stars) was born at YouTube to solve their MySQL scaling problem. It sits between your application and MySQL instances, providing automatic sharding, connection pooling, query rewriting, and live resharding without downtime.

**Key capabilities:**

- Automatic query routing to the correct shard based on a VSchema (Vitess Schema) definition
- Connection pooling via VTGate, reducing MySQL connection overhead by orders of magnitude
- Live resharding — split or merge shards while the database remains fully online
- Support for horizontal and vertical sharding (splitting tables vs. splitting databases)
- Built-in topology service (etcd, Consul, or ZooKeeper) for cluster coordination
- MySQL-compatible protocol — existing MySQL drivers work without modification

**Architecture overview:**

Vitess uses a three-layer architecture:
1. **VTGate** — stateless proxy that receives application queries and routes them to the correct VTTablet
2. **VTTablet** — manages individual MySQL instances, handles query serving, health checks, and failover
3. **VTController / VTOrc** — manages topology, automated failover, and resharding operations

For related reading on MySQL scaling strategies, see our [Vitess MySQL horizontal scaling guide](../vitess-self-hosted-mysql-horizontal-scaling-guide-2026/).

### Vitess Docker Compose Configuration

Vitess provides an official `vitess/examples/compose` setup. Below is a minimal single-node configuration for testing:

```yaml
version: "3.8"

services:
  etcd:
    image: vitess/lite:v21.0
    command: etcd -name etcd -listen-client-urls http://0.0.0.0:2379 -advertise-client-urls http://etcd:2379
    ports:
      - "2379:2379"

  vtctld:
    image: vitess/lite:v21.0
    command:
      - --cluster_id=local
      - --cell=local
      - --service_map=grpc-vtctl
      - --topo_implementation=etcd2
      - --topo_global_server_address=etcd:2379
      - --topo_global_root=/vitess/global
      - --logtostderr=true
    ports:
      - "15000:15000"
      - "15999:15999"
    depends_on:
      - etcd

  vtgate:
    image: vitess/lite:v21.0
    command:
      - --topo_implementation=etcd2
      - --topo_global_server_address=etcd:2379
      - --topo_global_root=/vitess/global
      - --cell=local
      - --mysql_server_port=15306
      - --mysql_auth_server_impl=none
      - --gateway_implementation=tabletgateway
      - --logtostderr=true
    ports:
      - "15306:15306"
      - "15001:15001"
    depends_on:
      - etcd
      - vtctld
```

Connect to Vitess using any MySQL client on port `15306`:

```bash
mysql -h 127.0.0.1 -P 15306
```

## Citus: Distributed PostgreSQL as an Extension

**Citus** (12,444 GitHub stars) takes a fundamentally different approach. Instead of a separate proxy layer, Citus is a PostgreSQL extension that transforms any PostgreSQL instance into a distributed (sharded) database coordinator node. Your application connects directly to PostgreSQL with Citus loaded — no additional proxy is needed.

**Key capabilities:**

- Standard PostgreSQL wire protocol — use any PostgreSQL driver, ORM, or tool
- Distributed tables (sharded by a distribution column) and reference tables (replicated to all workers)
- Distributed query execution — the coordinator parallelizes queries across all workers
- Columnar storage extension for analytical workloads (Citus Columnar)
- Multi-tenant SaaS optimizations: tenant isolation, row-level security integration
- Seamless upgrades — Citus is versioned alongside PostgreSQL

**Architecture overview:**

Citus uses a coordinator-worker model:
1. **Coordinator node** — receives queries, distributes them to workers, aggregates results. This is a regular PostgreSQL instance with the Citus extension loaded.
2. **Worker nodes** — standard PostgreSQL instances that store shard data. Each worker holds one or more shards from distributed tables.

### Citus Docker Compose Configuration

Citus provides an official Docker image on Docker Hub. Here is a coordinator + two worker setup:

```yaml
version: "3.8"

services:
  coordinator:
    image: citusdata/citus:12.1
    environment:
      POSTGRES_PASSWORD: secretpassword
    ports:
      - "5432:5432"
    command: >
      postgres -c shared_preload_libraries=citus
    depends_on:
      - worker1
      - worker2

  worker1:
    image: citusdata/citus:12.1
    environment:
      POSTGRES_PASSWORD: secretpassword
    command: >
      postgres -c shared_preload_libraries=citus

  worker2:
    image: citusdata/citus:12.1
    environment:
      POSTGRES_PASSWORD: secretpassword
    command: >
      postgres -c shared_preload_libraries=citus
```

After starting the cluster, register workers on the coordinator:

```sql
-- Connect to the coordinator node
psql -h localhost -p 5432 -U postgres

-- Register worker nodes
SELECT citus_add_node('worker1', 5432);
SELECT citus_add_node('worker2', 5432);

-- Create a distributed table
CREATE TABLE events (
    tenant_id   INT NOT NULL,
    event_id    BIGSERIAL,
    event_type  TEXT,
    payload     JSONB,
    created_at  TIMESTAMP DEFAULT now()
);

-- Distribute by tenant_id (hash sharding)
SELECT create_distributed_table('events', 'tenant_id');
```

## Apache ShardingSphere: Database-Agnostic Sharding Middleware

**Apache ShardingSphere** (20,714 GitHub stars) is the most flexible of the three tools. Rather than targeting a specific database engine, ShardingSphere sits as a proxy layer above *any* relational database — MySQL, PostgreSQL, Oracle, or SQL Server — and provides sharding, read/write splitting, encryption, and shadow database testing.

**Key capabilities:**

- **Database agnostic** — works with MySQL, PostgreSQL, and other RDBMS backends
- **Multiple deployment modes** — Proxy mode (standalone server), JDBC mode (embedded in your app), or Sidecar mode (Kubernetes)
- **Rich sharding algorithms** — hash-based, range-based, inline (expression), time-based, and custom algorithms
- **Read/write splitting** — automatic routing of reads to replicas and writes to primaries
- **Data encryption** — transparent column-level encryption at the proxy layer
- **Distributed transactions** — support for XA, Seata, and BASE transaction patterns
- **Shadow database** — route production traffic to shadow tables for safe testing

**Architecture overview:**

ShardingSphere-Proxy acts as a database proxy:
1. **ShardingSphere-Proxy** — accepts connections using MySQL or PostgreSQL wire protocol, applies sharding rules, and routes queries to backend database instances
2. **Backend databases** — any supported RDBMS instance, no special extensions required
3. **Configuration Center** — ZooKeeper or etcd for cluster coordination and dynamic rule updates

For database connection management across shards, see our [database connection pooling guide](../pgbouncer-vs-proxysql-vs-odyssey-self-hosted-database-connection-pooling-guide-2/).

### ShardingSphere Docker Compose Configuration

ShardingSphere-Proxy runs as a standalone server. Here is a configuration with two MySQL backend shards:

```yaml
version: "3.8"

services:
  shardingsphere-proxy:
    image: apache/shardingsphere-proxy:5.5.1
    ports:
      - "3307:3307"
    volumes:
      - ./sharding-config:/opt/shardingsphere-proxy/conf
    environment:
      MYSQL_ROOT_PASSWORD: root
      JAVA_OPTS: "-Xms256m -Xmx512m"
    depends_on:
      - mysql-shard1
      - mysql-shard2

  mysql-shard1:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: ds_0
    ports:
      - "3308:3306"

  mysql-shard2:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: ds_1
    ports:
      - "3309:3306"
```

Create the ShardingSphere configuration file at `./sharding-config/config-sharding.yaml`:

```yaml
rules:
  - !SHARDING
    tables:
      t_order:
        actualDataNodes: ds_${0..1}.t_order_${0..1}
        tableStrategy:
          standard:
            shardingColumn: order_id
            shardingAlgorithmName: t_order_inline
        keyGenerateStrategy:
          column: order_id
          keyGeneratorName: snowflake
    defaultDatabaseStrategy:
      standard:
        shardingColumn: user_id
        shardingAlgorithmName: database_inline
    defaultTableStrategy:
      none:
    shardingAlgorithms:
      database_inline:
        type: INLINE
        props:
          algorithm-expression: ds_${user_id % 2}
      t_order_inline:
        type: INLINE
        props:
          algorithm-expression: t_order_${order_id % 2}
    keyGenerators:
      snowflake:
        type: SNOWFLAKE
```

## Head-to-Head Comparison

| Feature | Vitess | Citus | ShardingSphere |
|---------|--------|-------|----------------|
| **Primary database** | MySQL | PostgreSQL | Any (MySQL, PostgreSQL, etc.) |
| **Architecture** | Proxy layer (VTGate) | PostgreSQL extension | Proxy + JDBC + Sidecar |
| **Language** | Go | C (PostgreSQL extension) | Java |
| **GitHub stars** | 20,930 | 12,444 | 20,714 |
| **License** | Apache 2.0 | AGPL-3.0 / Commercial | Apache 2.0 |
| **Live resharding** | Yes (automated) | Yes (manual rebalancing) | No (manual) |
| **Connection pooling** | Built-in (VTGate) | Via pgbouncer (external) | None (external needed) |
| **Sharding strategies** | Hash, range, custom | Hash, append, reference | Hash, range, inline, time, custom |
| **Read/write splitting** | Yes | Yes (via PostgreSQL streaming) | Yes (built-in) |
| **Distributed transactions** | 2PC (two-phase commit) | 2PC via coordinator | XA, Seata, BASE |
| **Cloud native** | Kubernetes operator | Azure Database for Citus | Kubernetes sidecar mode |
| **Multi-tenant support** | Good | Excellent (native) | Good |
| **Operational complexity** | High (many components) | Low (PostgreSQL native) | Medium (proxy + config) |
| **Best for** | Large MySQL deployments | PostgreSQL workloads | Multi-database environments |

## When to Choose Which Tool

**Choose Vitess if:**
- Your primary database is MySQL and you need production-grade horizontal scaling at scale
- You need automated live resharding (split/merge shards without downtime)
- You already run etcd or Consul for service discovery
- You want built-in connection pooling alongside sharding
- Your team has experience with Kubernetes (Vitess operator is production-ready)

**Choose Citus if:**
- You are a PostgreSQL shop and want the simplest sharding setup
- You need standard PostgreSQL compatibility — all tools, ORMs, and extensions work out of the box
- You run multi-tenant SaaS and need tenant-level data distribution
- You want analytical capabilities (Citus Columnar) alongside OLTP sharding
- You prefer minimal operational overhead — Citus is just a PostgreSQL extension

**Choose ShardingSphere if:**
- You need database-agnostic sharding across MySQL, PostgreSQL, or mixed environments
- You want flexible deployment modes — proxy server, embedded JDBC library, or Kubernetes sidecar
- You need features beyond sharding: data encryption, shadow database testing, and read/write splitting
- You are comfortable with Java-based infrastructure
- You need custom sharding algorithms expressed as inline expressions

For teams managing database schema changes across sharded environments, our [database migration tools guide](../bytebase-vs-flyway-vs-liquibase-self-hosted-database-migration-guide-2026/) covers Flyway, Liquibase, and Bytebase for handling versioned migrations on distributed databases.

## FAQ

### What is database sharding and when do I need it?

Database sharding splits a single logical database across multiple physical instances (shards), each holding a subset of the data. You need sharding when a single database instance can no longer handle your write throughput, storage capacity, or query latency requirements. Typical triggers include: tables exceeding 100 GB, write QPS over 5,000, or connection counts hitting the database limit.

### Can I migrate from a single database to a sharded setup without downtime?

Vitess supports live resharding, allowing you to split or merge shards while the database remains fully operational. Citus supports adding new workers and redistributing data, but rebalancing existing data requires manual coordination. ShardingSphere does not have built-in live migration — you need to script the data redistribution and cutover process yourself.

### Does sharding affect my application code?

With Vitess and ShardingSphere-Proxy, your application connects to a standard MySQL or PostgreSQL endpoint, so no code changes are required if you already use a compatible driver. With Citus, your application connects to PostgreSQL directly — again, no code changes. However, you should design your distribution/sharding keys carefully to avoid cross-shard queries, which can significantly impact performance.

### How do I choose a sharding (distribution) key?

The sharding key should have high cardinality (many distinct values), be frequently used in query predicates, and align with your access patterns. For multi-tenant applications, the tenant ID is a natural choice. Avoid keys that would cause uneven data distribution (e.g., boolean flags) or require frequent cross-shard joins.

### Is there a performance overhead from the sharding proxy?

Yes, any proxy adds a small amount of latency (typically 1-5 ms for Vitess and ShardingSphere). Citus avoids this overhead entirely since it runs inside PostgreSQL. However, the trade-off is that sharding dramatically increases total throughput by distributing load across multiple machines, which far outweighs the proxy latency for high-volume workloads.

### Can I use sharding with an ORM like Django, Hibernate, or Prisma?

Yes. All three tools use standard database wire protocols (MySQL or PostgreSQL), so any ORM that supports those protocols will work. The key consideration is ensuring your ORM queries use the sharding key in WHERE clauses to enable efficient single-shard routing.

### What happens when a shard goes down?

Vitess provides automated failover through VTOrc (Vitess Orchestrator), which detects unhealthy tablets and promotes replicas. Citus relies on PostgreSQL streaming replication and manual or scripted failover. ShardingSphere does not handle failover at the proxy layer — you need to configure backend database high availability separately (e.g., MySQL Group Replication or PostgreSQL Patroni).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Vitess vs Citus vs ShardingSphere: Self-Hosted Database Sharding Guide 2026",
  "description": "Compare Vitess, Citus, and Apache ShardingSphere for self-hosted database sharding. Complete guide with Docker Compose configs, architecture comparison, and decision framework.",
  "datePublished": "2026-04-25",
  "dateModified": "2026-04-25",
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
