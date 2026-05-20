---
title: "Self-Hosted Redis Migration Tools: RedisShake vs Redis Port vs Redis Dump Go (2026)"
date: "2026-05-21"
tags: ["redis", "data-migration", "database-management", "self-hosted"]
draft: false
---

Migrating data between Redis (or Valkey) instances is a common challenge when upgrading infrastructure, switching providers, or consolidating clusters. While Redis provides basic commands like `MIGRATE` and `DUMP`, production-grade migrations require tools that handle high throughput, data type fidelity, and minimal downtime.

In this guide, we compare three self-hosted Redis migration tools: **RedisShake** from Alibaba's Tair team, **Redis Port** from the Codis project, and **Redis Dump Go** — a fast Go-based backup and restore utility. Each takes a different approach to the migration problem, from real-time replication to offline dump-and-restore workflows.

## Comparison Overview

| Feature | RedisShake | Redis Port | Redis Dump Go |
|---------|-----------|------------|---------------|
| GitHub Stars | 4,369 | 637 | 343 |
| Last Updated | May 2026 | Apr 2018 | Jul 2024 |
| Language | Go | Go | Go |
| Real-Time Sync | Yes | Yes | No (offline only) |
| Data Filtering | Yes (regex, key prefix) | Yes | No |
| Data Transformation | Yes (rewrite rules) | No | No |
| Cluster Support | Yes | Partial | Yes |
| Docker Deployable | Yes | Manual | Yes |
| Redis Protocol | RESP2/RESP3 | RESP2 | RESP2 |
| Valkey Support | Yes | No | Yes |

## RedisShake: Full-Featured Migration Platform

**RedisShake** (github.com/tair-opensource/RedisShake) is the most capable tool in this comparison. Originally developed by Alibaba for their Tair managed Redis service, it supports real-time data synchronization between source and target instances with filtering, transformation, and rewriting capabilities.

### Key Features

- **Real-time replication**: Reads from the source's replication stream (psync) and applies changes to the target with minimal lag, supporting both full sync and incremental sync phases.
- **Data filtering**: Filter keys by regex patterns, key prefixes, or database index — essential when migrating only a subset of data.
- **Data rewriting**: Transform data during migration — rename key prefixes, convert data types, or apply custom Lua scripts.
- **Multi-mode sync**: Supports SYNC (legacy), PSYNC (Redis 2.8+), and cluster-aware migration.
- **Valkey compatibility**: Fully compatible with Valkey, the open-source Redis fork backed by the Linux Foundation.

### Docker Deployment

RedisShake ships with an official Dockerfile and can be deployed with a simple compose configuration:

```yaml
version: "3.8"
services:
  redisshake:
    image: redisshake/redisshake:latest
    container_name: redisshake
    volumes:
      - ./redisshake.toml:/etc/redisshake/redisshake.toml
    restart: unless-stopped
    networks:
      - migration-net

networks:
  migration-net:
    driver: bridge
```

Configuration file (`redisshake.toml`):

```toml
[sync_reader]
  cluster = false
  address = "source-redis:6379"
  password = "source-password"
  tls = false

[redis_writer]
  cluster = false
  address = "target-redis:6379"
  password = "target-password"
  tls = false

[sync]
  # Filter only keys matching this pattern
  # filter_key = ["user:*", "session:*"]
  rewrite = false
```

### When to Use RedisShake

- **Live migrations**: Zero-downtime cutover from old to new Redis instance
- **Active-active setups**: Bidirectional replication between two Redis clusters
- **Data filtering**: Migrating only specific namespaces or databases
- **Valkey migration**: Moving from proprietary Redis to open-source Valkey

## Redis Port: Lightweight Replication Tool

**Redis Port** (github.com/CodisLabs/redis-port) was built as part of the Codis distributed Redis proxy project. While the Codis project itself is no longer actively maintained, Redis Port remains a useful standalone tool for straightforward replication tasks.

### Key Features

- **Fast RDB parsing**: Uses a custom RDB parser written in Go for high-throughput data extraction.
- **Real-time replication**: Supports full sync followed by command-level incremental replication.
- **Decode mode**: Can decode RDB files into human-readable format for auditing or debugging.
- **Restore mode**: Restores data from RDB dumps into a target Redis instance.
- **Simple CLI**: Single binary with clear subcommands for sync, decode, restore, and dump.

### Installation and Usage

Redis Port is distributed as a single Go binary:

```bash
# Build from source
git clone https://github.com/CodisLabs/redis-port.git
cd redis-port
make

# Full sync + incremental replication
./redis-port sync --from=source-redis:6379 --to=target-redis:6379 --parallel=4

# Decode RDB to human-readable format
./redis-port decode --input=dump.rdb --output=dump.json

# Restore from RDB file
./redis-port restore --target=target-redis:6379 --input=dump.rdb
```

### Docker Deployment

While Redis Port doesn't ship an official Dockerfile, you can containerize it easily:

```dockerfile
FROM golang:1.21-alpine AS builder
RUN apk add --no-cache git make
RUN git clone https://github.com/CodisLabs/redis-port.git /src &&     cd /src && make

FROM alpine:3.19
COPY --from=builder /src/bin/redis-port /usr/local/bin/
ENTRYPOINT ["redis-port"]
```

### When to Use Redis Port

- **Simple replication**: Quick one-way sync between two Redis instances
- **RDB auditing**: Decoding RDB dumps for inspection
- **Legacy environments**: Works with Redis 2.8+ without requiring newer features
- **Minimal overhead**: Single binary with no dependencies

## Redis Dump Go: Fast Backup and Restore

**Redis Dump Go** (github.com/yannh/redis-dump-go) takes a different approach — instead of real-time replication, it performs a fast offline dump of all keys from a Redis server and can restore them to another instance. It's written in Go and optimized for speed using pipelined commands.

### Key Features

- **Fast dump**: Uses SCAN + pipelined GET commands for efficient extraction — significantly faster than the original Node.js redis-dump.
- **Fast restore**: Pipelines SET commands for high-throughput data loading.
- **JSON export**: Exports data in JSON format for portability and version control.
- **Selective DB**: Can target specific Redis database numbers.
- **No running sync**: Operates as a point-in-time snapshot — ideal for backups or offline migrations.

### Installation

```bash
# Using Go
go install github.com/yannh/redis-dump-go@latest

# Or download pre-built binaries from GitHub releases
```

### Usage Examples

```bash
# Dump all keys from source to JSON file
redis-dump-go -host source-redis -port 6379 -db 0 > backup.json

# Restore from JSON file to target
cat backup.json | redis-dump-go -restore -host target-redis -port 6379 -db 0

# Dump specific database
redis-dump-go -host source-redis -port 6379 -db 3 > db3_backup.json

# With authentication
redis-dump-go -host source-redis -port 6379 -password mypassword -db 0 > backup.json
```

### Docker Deployment

```yaml
version: "3.8"
services:
  redis-dump:
    image: golang:1.21-alpine
    container_name: redis-dump-go
    command: >
      sh -c "
        go install github.com/yannh/redis-dump-go@latest &&
        redis-dump-go -host source-redis -port 6379 -db 0 > /data/backup.json
      "
    volumes:
      - ./backup-data:/data
    networks:
      - migration-net

networks:
  migration-net:
    driver: bridge
```

### When to Use Redis Dump Go

- **Scheduled backups**: Automated point-in-time snapshots
- **Offline migrations**: When downtime is acceptable
- **Data export**: Exporting Redis data for analysis or archival
- **Small-to-medium datasets**: Best for datasets under 10GB where scan-based extraction is fast enough

## Choosing the Right Migration Tool

| Scenario | Recommended Tool |
|----------|-----------------|
| Zero-downtime live migration | RedisShake |
| Active-active replication | RedisShake |
| Migrating to Valkey | RedisShake |
| Quick one-way sync | Redis Port |
| Auditing RDB contents | Redis Port (decode mode) |
| Scheduled backups | Redis Dump Go |
| Offline migration with downtime | Redis Dump Go |
| Key filtering during migration | RedisShake |
| Data transformation during sync | RedisShake |
| Minimal setup, single binary | Redis Port |

## Why Self-Host Your Redis Migration Tools?

Running migration tools on your own infrastructure gives you several advantages over managed migration services:

**Data sovereignty**: Your Redis data never leaves your network during migration. This is critical for compliance with regulations like GDPR, HIPAA, or PCI-DSS, where data residency requirements prohibit transferring sensitive information through third-party systems.

**Cost savings**: Managed Redis migration services from cloud providers often charge per GB of data transferred. Self-hosted tools like RedisShake and Redis Port are open-source and free — you only pay for the compute resources to run the migration process itself.

**No vendor lock-in**: Open-source migration tools work with any Redis-compatible server — Redis Enterprise, Valkey, Dragonfly, KeyDB, or Garnet. You're not tied to a specific vendor's migration ecosystem.

**Customization**: Self-hosted tools can be modified to fit your specific needs — adding custom data transformation logic, integrating with your monitoring stack, or building automated migration pipelines that run on your CI/CD infrastructure.

**Repeatability**: Migration configurations can be version-controlled and tested in staging before production cutover. This is especially important for large-scale migrations where retry and rollback procedures need to be well-defined.

For Redis management and administration, see our [Redis GUI tools comparison](../2026-04-23-redis-commander-vs-redis-insight-vs-ardm-self-hosted-redis-gui-2026/). For high availability setups, check our [Redis HA guide](../2026-05-15-self-hosted-redis-high-availability-sentinel-cluster-keydb-guide/). For Kubernetes deployments, our [Redis operators article](../2026-05-10-self-hosted-redis-operators-kubernetes-ot-container-kit-spotahome-ibm-guide/) covers operator-based deployments.

## FAQ

### What is the fastest way to migrate Redis data?

For large datasets requiring zero downtime, **RedisShake** is the fastest option. It uses the PSYNC replication protocol to perform an initial full RDB sync followed by incremental command replay, keeping source and target in near-real-time sync during the migration window. For smaller datasets where downtime is acceptable, Redis Dump Go's pipelined approach can complete in seconds.

### Can RedisShake migrate between different Redis versions?

Yes. RedisShake supports migrating between any Redis versions that support the PSYNC protocol (Redis 2.8+). It also supports migrating from Redis to Valkey, since Valkey maintains full protocol compatibility with Redis 7.2+.

### Does Redis Port support Redis Cluster?

Redis Port has partial cluster support. It can sync from a cluster node but does not automatically handle cluster topology changes or slot migration. For full cluster-aware migration, RedisShake is the better choice as it understands cluster slot assignments and can migrate data accordingly.

### Can I filter specific keys during migration?

RedisShake supports key filtering via regex patterns, key prefixes, and database index selection in its configuration file. Redis Port does not support key-level filtering — it syncs all data from the source. Redis Dump Go also lacks built-in filtering.

### Is Redis Dump Go suitable for production backups?

Redis Dump Go is suitable for small-to-medium datasets where SCAN-based extraction completes within your backup window. For large production datasets, consider using RedisShake for continuous replication or Redis Port's RDB-based approach, which is faster for bulk data transfer.

### What happens to TTLs and expiration during migration?

RedisShake preserves TTLs during both full sync and incremental replication, as TTLs are part of the Redis replication stream. Redis Port also preserves TTLs when using its sync mode. Redis Dump Go exports TTLs in its JSON format and restores them during the import phase.

### How do I verify data integrity after migration?

After migration, use the `DBSIZE` and `INFO keyspace` commands on both source and target to compare key counts. For detailed verification, RedisShake includes a built-in audit mode, and Redis Port's decode mode lets you compare RDB contents. For production migrations, consider running a comparison script that samples random keys from both instances.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Redis Migration Tools: RedisShake vs Redis Port vs Redis Dump Go (2026)",
  "description": "Compare the best open-source Redis migration tools: RedisShake for real-time sync, Redis Port for lightweight replication, and Redis Dump Go for fast backup and restore.",
  "datePublished": "2026-05-21",
  "dateModified": "2026-05-21",
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
