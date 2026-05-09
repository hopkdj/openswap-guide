---
title: "Self-Hosted PostgreSQL Logical Replication: pglogical vs wal2json vs pgoutput"
date: "2026-05-10"
tags: ["postgresql", "replication", "logical-replication", "wal", "database", "cdc", "pglogical", "wal2json"]
draft: false
---

PostgreSQL offers two replication paradigms: **physical (streaming) replication**, which copies entire database clusters byte-for-byte, and **logical replication**, which replicates individual tables, rows, and columns at the SQL level. While physical replication is ideal for read scaling and disaster recovery, logical replication enables selective data synchronization, multi-master setups, zero-downtime migrations, and change data capture (CDC) pipelines.

PostgreSQL's logical replication is powered by **logical decoding output plugins** — extensions that transform Write-Ahead Log (WAL) records into consumable change streams. Three output plugins dominate the self-hosted PostgreSQL ecosystem: **pglogical** for active-active replication, **wal2json** for JSON-based change streams, and **pgoutput** (built-in) for standard logical replication.

In this guide, we compare these three approaches, provide deployment configurations, and explain when to use each one.

## Understanding PostgreSQL Logical Replication

PostgreSQL's Write-Ahead Log (WAL) records every data modification before it's applied to disk. Logical decoding reads these WAL records and transforms them into a structured format that external consumers can process.

The logical replication flow works like this:

1. **WAL generation**: A data change (INSERT, UPDATE, DELETE) is written to WAL
2. **Logical decoding**: An output plugin reads the WAL record and transforms it into a change event
3. **Publication**: The change event is sent to subscribers via PostgreSQL's built-in logical replication protocol
4. **Application**: The subscriber receives the change and applies it to its local copy of the data

The output plugin determines the format and granularity of the change events, which influences how consumers process them.

## Comparison Table

| Feature | pglogical | wal2json | pgoutput |
|---------|-----------|----------|----------|
| **Type** | Extension (active replication) | Output plugin (CDC stream) | Built-in (since PG 10) |
| **GitHub** | 2ndQuadrant/pglogical | eulerto/wal2json | PostgreSQL core |
| **Stars** | ~1,216 | ~1,493 | N/A (core) |
| **Last Updated** | Feb 2026 | Apr 2026 | Ongoing (PG releases) |
| **Replication Mode** | Active-active (bidirectional) | One-way (CDC output) | One-way (subscriber) |
| **Conflict Resolution** | Built-in (last-writer-wins, custom) | None (stream only) | None (stream only) |
| **Output Format** | Internal protocol | JSON | PostgreSQL logical protocol |
| **Row Filtering** | Yes (per-table, per-column) | No (all changes) | Yes (publication filters) |
| **DDL Replication** | Yes (schema changes) | No (data only) | No (data only) |
| **Multi-master** | Yes | No | No |
| **External Consumers** | Limited (PostgreSQL only) | Any (Kafka, Redis, HTTP) | Any (via logical decoding) |
| **Installation** | Extension (`CREATE EXTENSION`) | Plugin (`shared_preload_libraries`) | Built-in (no install) |
| **PostgreSQL Version** | 9.4+ | 9.4+ | 10+ |

## pglogical

pglogical is a full-featured logical replication extension developed by 2ndQuadrant (now part of EDB). Unlike standard PostgreSQL logical replication, pglogical provides **active-active (bidirectional) replication** with built-in conflict resolution, making it suitable for multi-master database setups.

### Architecture

pglogical operates as a PostgreSQL extension that provides:

- **Replication sets**: Groups of tables to replicate together, with per-table and per-column filtering
- **Subscriptions**: Connections to remote databases that consume replication sets
- **Conflict resolution**: Configurable strategies (last writer wins, first writer wins, custom PL/pgSQL functions)
- **DDL replication**: Automatic propagation of schema changes (ALTER TABLE, CREATE INDEX) across nodes
- **Replication slots**: Persistent WAL tracking that ensures no changes are lost during subscriber outages

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  postgres-node1:
    image: postgres:16
    restart: always
    environment:
      POSTGRES_USER: repl_user
      POSTGRES_PASSWORD: repl_password
      POSTGRES_DB: maindb
    ports:
      - "5432:5432"
    volumes:
      - pg1_data:/var/lib/postgresql/data
      - ./init-node1.sql:/docker-entrypoint-initdb.d/init.sql
    command: >
      postgres
      -c wal_level=logical
      -c max_replication_slots=10
      -c max_wal_senders=10
      -c shared_preload_libraries=pglogical

  postgres-node2:
    image: postgres:16
    restart: always
    environment:
      POSTGRES_USER: repl_user
      POSTGRES_PASSWORD: repl_password
      POSTGRES_DB: maindb
    ports:
      - "5433:5432"
    volumes:
      - pg2_data:/var/lib/postgresql/data
      - ./init-node2.sql:/docker-entrypoint-initdb.d/init.sql
    command: >
      postgres
      -c wal_level=logical
      -c max_replication_slots=10
      -c max_wal_senders=10
      -c shared_preload_libraries=pglogical

volumes:
  pg1_data:
  pg2_data:
```

### Configuration

```sql
-- Initialize pglogical on both nodes
CREATE EXTENSION pglogical;

-- Node 1: Create provider
SELECT pglogical.create_node(
    node_name := 'node1',
    dsn := 'host=postgres-node1 port=5432 dbname=maindb user=repl_user password=repl_password'
);

-- Create a replication set (all tables by default)
SELECT pglogical.create_replication_set('default_set');

-- Add all tables to the replication set
SELECT pglogical.replication_set_add_all_tables('default_set', ARRAY['public']);

-- Node 2: Create subscriber
SELECT pglogical.create_node(
    node_name := 'node2',
    dsn := 'host=postgres-node2 port=5432 dbname=maindb user=repl_user password=repl_password'
);

-- Subscribe to node1's replication set
SELECT pglogical.create_subscription(
    subscription_name := 'sub_node1',
    provider_dsn := 'host=postgres-node1 port=5432 dbname=maindb user=repl_user password=repl_password'
);
```

### Bidirectional Replication

```sql
-- On Node 1, subscribe to Node 2
SELECT pglogical.create_subscription(
    subscription_name := 'sub_node2',
    provider_dsn := 'host=postgres-node2 port=5432 dbname=maindb user=repl_user password=repl_password'
);

-- Configure conflict resolution (last writer wins by timestamp)
ALTER SYSTEM SET pglogical.conflict_resolution = 'last_update_wins';
```

pglogical is the only solution in this comparison that supports **true multi-master replication** with automatic conflict resolution. If you need to write to multiple PostgreSQL nodes simultaneously and have changes propagate bidirectionally, pglogical is the right choice.

## wal2json

wal2json is a logical decoding output plugin that transforms WAL records into JSON format. Unlike pglogical, it doesn't provide replication management — instead, it exposes a JSON stream of changes that any external system can consume, making it the go-to choice for CDC pipelines.

### Architecture

wal2json reads WAL records and produces JSON objects representing each change:

```json
{
  "change": [
    {
      "kind": "insert",
      "schema": "public",
      "table": "users",
      "columnnames": ["id", "name", "email"],
      "columntypes": ["integer", "text", "text"],
      "columnvalues": [1, "Alice", "alice@example.com"]
    }
  ],
  "xid": 12345,
  "timestamp": "2026-05-10 14:30:00.000000+00",
  "lsn": "0/1A2B3C4"
}
```

This format is easily consumed by Kafka, Redis, HTTP webhooks, or custom applications.

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  postgres-wal2json:
    image: ghcr.io/eulerto/wal2json:latest
    restart: always
    environment:
      POSTGRES_USER: app_user
      POSTGRES_PASSWORD: app_password
      POSTGRES_DB: appdb
    ports:
      - "5432:5432"
    volumes:
      - pg_wal2json_data:/var/lib/postgresql/data
    command: >
      postgres
      -c wal_level=logical
      -c max_replication_slots=10
      -c max_wal_senders=10
      -c shared_preload_libraries=wal2json

volumes:
  pg_wal2json_data:
```

### Building from Source

```bash
# Clone the repository
git clone https://github.com/eulerto/wal2json.git
cd wal2json

# Build and install
make
sudo make install

# Or with pgxs
USE_PGXS=1 make
USE_PGXS=1 sudo make install

# Add to postgresql.conf
echo "shared_preload_libraries = 'wal2json'" >> /etc/postgresql/16/main/postgresql.conf
```

### Consuming Changes via pg_recvlogical

```bash
# Create a replication slot
psql -c "SELECT pg_create_logical_replication_slot('my_slot', 'wal2json');"

# Stream changes
pg_recvlogical -d appdb --slot my_slot --start   -f - --option pretty-print=1 --option include-timestamp=1
```

wal2json's strength is its **universal output format**. Because changes are emitted as JSON, any system that can parse JSON can consume them — Kafka Connect, Debezium, custom microservices, or even simple log processors.

## pgoutput

pgoutput is PostgreSQL's built-in logical decoding output plugin, available since PostgreSQL 10. It uses PostgreSQL's native logical replication protocol and doesn't require any external plugins or extensions to be installed.

### Architecture

pgoutput is the default output plugin for PostgreSQL's `CREATE PUBLICATION` / `CREATE SUBSCRIPTION` commands. It transmits changes using PostgreSQL's binary replication protocol, which is more efficient than JSON-based formats for PostgreSQL-to-PostgreSQL replication.

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  postgres-publisher:
    image: postgres:16
    restart: always
    environment:
      POSTGRES_USER: pub_user
      POSTGRES_PASSWORD: pub_password
      POSTGRES_DB: maindb
    ports:
      - "5432:5432"
    volumes:
      - pub_data:/var/lib/postgresql/data
    command: >
      postgres
      -c wal_level=logical
      -c max_replication_slots=10
      -c max_wal_senders=10

  postgres-subscriber:
    image: postgres:16
    restart: always
    environment:
      POSTGRES_USER: sub_user
      POSTGRES_PASSWORD: sub_password
      POSTGRES_DB: maindb
    ports:
      - "5433:5432"
    volumes:
      - sub_data:/var/lib/postgresql/data
    command: >
      postgres
      -c wal_level=logical
      -c max_replication_slots=10
      -c max_wal_senders=10

volumes:
  pub_data:
  sub_data:
```

### Configuration

```sql
-- On the publisher (no plugins needed)
CREATE PUBLICATION mypub FOR TABLE users, orders, products;

-- On the subscriber
CREATE SUBSCRIPTION mysub
  CONNECTION 'host=publisher port=5432 dbname=maindb user=pub_user password=pub_password'
  PUBLICATION mypub;

-- Verify replication status
SELECT * FROM pg_stat_subscription;
SELECT * FROM pg_stat_replication;
```

### Row-Level Filtering (PostgreSQL 15+)

```sql
-- Publish only active users
CREATE PUBLICATION active_users_pub
  FOR TABLE users WHERE (status = 'active');

-- Publish specific columns only
CREATE PUBLICATION user_names_pub
  FOR TABLE users (id, name);
```

pgoutput's built-in status means **zero additional software** is required. It's the simplest solution for PostgreSQL-to-PostgreSQL replication and is the foundation upon which pglogical is built.

## Choosing the Right Solution

**Choose pglogical if:**
- You need bidirectional (active-active) replication between PostgreSQL nodes
- Conflict resolution is required for multi-master setups
- DDL replication (schema changes) needs to propagate automatically
- You are building a distributed PostgreSQL cluster

**Choose wal2json if:**
- You need to stream changes to external systems (Kafka, Redis, HTTP)
- JSON output format is required for downstream processing
- You are building CDC pipelines, audit logs, or event-driven architectures
- Your consumers are non-PostgreSQL systems

**Choose pgoutput if:**
- You need simple PostgreSQL-to-PostgreSQL replication
- Zero additional software installation is preferred
- You want the best performance for same-database replication
- Row-level and column-level filtering is sufficient (PG 15+)

For related reading, see our [PostgreSQL Backup comparison](../pgbackrest-vs-barman-vs-wal-g-self-hosted-postgresql-backup-guide-2026/) and [SQL Database comparison](../2026-04-25-firebird-vs-postgresql-vs-mariadb-self-hosted-sql-database-guide-2026/).

## Why Self-Host PostgreSQL Replication Infrastructure?

Running your own PostgreSQL logical replication setup gives you full control over data flow, security, and performance. Cloud-managed replication services are convenient but introduce several limitations that self-hosting eliminates.

**Data sovereignty and compliance**: When replicating sensitive data across regions, cloud-managed services may route traffic through infrastructure you don't control. Self-hosted replication lets you define exact network paths, encryption boundaries, and data residency policies. This is critical for GDPR, HIPAA, and financial services compliance where data movement must be auditable.

**Cost optimization at scale**: Cloud providers charge for replication bandwidth, storage on read replicas, and cross-region data transfer. For organizations replicating terabytes of data across multiple regions, self-hosted logical replication on commodity hardware can reduce costs by 60-80% compared to managed equivalents.

**Multi-vendor flexibility**: Self-hosted logical replication works identically across all PostgreSQL distributions — upstream PostgreSQL, EDB Postgres, Citus, TimescaleDB, and cloud distributions like Amazon RDS for PostgreSQL. You're not locked into a single vendor's replication API or tooling.

**Custom CDC pipelines**: Logical replication enables real-time data synchronization to analytics platforms, search indexes, cache layers, and microservice databases. Self-hosted wal2json streams can feed Kafka topics that power real-time dashboards, anomaly detection systems, and event-driven microservice architectures.

**Zero-downtime migrations**: Logical replication allows you to migrate between PostgreSQL versions or hardware platforms with minimal downtime. Set up replication from the old server to the new one, let it catch up, then switch over in seconds rather than hours of scheduled maintenance windows.

## FAQ

### What is the difference between physical and logical replication in PostgreSQL?

Physical replication copies the entire database at the byte level (WAL shipping), requiring identical versions and full cluster replication. Logical replication operates at the row and table level, allowing selective replication of specific tables, different PostgreSQL versions between source and target, and transformations during replication.

### Does logical replication impact database performance?

Logical replication adds some overhead because the server must decode WAL records into logical changes. Typical overhead is 5-15% CPU on the publisher for moderate write loads. The impact is proportional to the write rate — read-heavy workloads see minimal impact.

### Can I use logical replication for real-time analytics?

Yes. wal2json combined with a message broker (Kafka, RabbitMQ) enables real-time data streaming from PostgreSQL to analytics platforms like ClickHouse, Elasticsearch, or Apache Druid. Changes appear in the analytics system within milliseconds of being committed in PostgreSQL.

### How do I handle schema changes with logical replication?

pglogical supports automatic DDL replication, propagating ALTER TABLE and CREATE INDEX commands to subscribers. pgoutput does not replicate DDL — you must apply schema changes manually on each node. wal2json doesn't handle DDL at all, as it only outputs data changes.

### Can I replicate between different PostgreSQL versions?

Yes. Logical replication works across different PostgreSQL major versions (e.g., PG 14 to PG 16). This is one of its key advantages over physical replication, which requires identical versions. However, replicating from an older version to a newer one is more reliable than the reverse.

### What happens if a subscriber goes offline?

PostgreSQL's replication slots ensure that WAL records are retained on the publisher until all subscribers have consumed them. If a subscriber goes offline, changes accumulate on the publisher. If the subscriber stays offline too long, WAL files may fill disk space — monitor `pg_replication_slots` and set `max_slot_wal_keep_size` to prevent disk exhaustion.

### Is logical replication a replacement for backups?

No. Logical replication creates a copy of data but does not protect against accidental data deletion or corruption — these changes are also replicated. Always maintain separate backup strategies (pgBackRest, Barman) alongside replication.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted PostgreSQL Logical Replication: pglogical vs wal2json vs pgoutput",
  "description": "Compare PostgreSQL logical replication solutions: pglogical, wal2json, and pgoutput. Learn about architecture, Docker Compose deployment, and when to use each.",
  "datePublished": "2026-05-10",
  "dateModified": "2026-05-10",
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
