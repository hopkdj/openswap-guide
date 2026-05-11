---
title: "Self-Hosted PostgreSQL Table Maintenance: pg_repack vs pg_squeeze vs pgcompacttable 2026"
date: "2026-05-11"
tags: ["comparison", "guide", "self-hosted", "postgresql", "database", "maintenance", "performance"]
draft: false
description: "Compare pg_repack, pg_squeeze, and pgcompacttable for online PostgreSQL table maintenance. Reclaim bloat and rebuild indexes without exclusive locks or downtime."
---

PostgreSQL's MVCC (Multi-Version Concurrency Control) architecture means that every UPDATE and DELETE leaves behind dead tuples. Over time, these dead tuples accumulate as table bloat, degrading query performance and wasting disk space. While PostgreSQL's autovacuum daemon handles basic cleanup, it cannot rebuild tables or indexes without acquiring exclusive locks that block all reads and writes.

For production databases that cannot afford downtime, three specialized tools provide online table reorganization: [pg_repack](https://github.com/reorg/pg_repack), [pg_squeeze](https://github.com/cybertec-postgresql/pg_squeeze), and [pgcompacttable](https://github.com/dataegret/pgcompacttable). Each uses a different approach to reclaim bloat and rebuild indexes without blocking concurrent queries.

This guide compares these tools for self-hosted PostgreSQL deployments, covering their architecture, performance characteristics, and operational requirements.

## Understanding PostgreSQL Table Bloat

Before diving into the tools, it helps to understand why bloat occurs:

- **MVCC dead tuples**: UPDATE and DELETE operations mark old row versions as dead rather than removing them immediately
- **Autovacuum limitations**: Autovacuum marks dead space as reusable but does not physically shrink tables or rebuild indexes
- **VACUUM FULL**: Rebuilds the table from scratch but takes an ACCESS EXCLUSIVE lock, blocking all access
- **Index bloat**: B-tree indexes grow with every INSERT and are only partially cleaned by autovacuum

For databases with heavy write loads, bloat can consume 30-70% of table size. A 100 GB table with 50% bloat means you're storing 50 GB of dead data, and queries must scan through it unnecessarily.

## pg_repack: The Battle-Tested Solution

**GitHub**: [reorg/pg_repack](https://github.com/reorg/pg_repack) · 2,242 stars · Active development

pg_repack is the most widely deployed online table reorganization tool for PostgreSQL. Originally developed by the PostgreSQL Global Development Group, it uses a trigger-based approach to rebuild tables and indexes concurrently.

### How pg_repack Works

1. Creates a shadow copy of the target table with the same structure
2. Attaches triggers to the original table to capture all INSERT/UPDATE/DELETE operations
3. Copies existing rows to the shadow table
4. Replays captured changes from the trigger log
5. Swaps the shadow table with the original using a brief exclusive lock (typically < 1 second)
6. Drops the old table

### Installing pg_repack

```bash
# Debian/Ubuntu
apt-get install postgresql-16-repack

# From source
git clone https://github.com/reorg/pg_repack.git
cd pg_repack
make && sudo make install

# Enable the extension in your database
psql -d yourdb -c "CREATE EXTENSION pg_repack;"
```

### Docker Compose with pg_repack

```yaml
version: "3.8"
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: secretpassword
      POSTGRES_DB: production
    volumes:
      - pgdata:/var/lib/postgresql/data
    command: >
      postgres
      -c shared_preload_libraries=pg_repack
      -c log_min_duration_statement=1000
    ports:
      - "5432:5432"

  repack-runner:
    image: postgres:16
    depends_on:
      - postgres
    entrypoint: ["sh", "-c", "sleep 5 && pg_repack -h postgres -U postgres -d production --no-order --all"]

volumes:
  pgdata:
```

### Running pg_repack

```bash
# Repack all tables in a database
pg_repack -d production -U postgres

# Repack specific table
pg_repack -d production -t public.large_table -U postgres

# Repact with verbose logging
pg_repack -d production --no-order --verbose -U postgres

# Dry run — check what would be repacked
pg_repack -d production --dry-run -U postgres
```

### pg_repack Limitations

| Constraint | Detail |
|------------|--------|
| Primary key required | Tables without PK or UNIQUE NOT NULL columns cannot be repacked |
| Superuser access | Requires superuser or pg_repack role membership |
| Disk space | Needs approximately 2x table size for the shadow copy |
| No DDL during repack | ALTER TABLE on the target table during repack will fail |
| TOAST tables | Supported since pg_repack 1.4.4 |

## pg_squeeze: The Modern Alternative

**GitHub**: [cybertec-postgresql/pg_squeeze](https://github.com/cybertec-postgresql/pg_squeeze) · 666 stars

pg_squeeze, developed by Cybertec, takes a fundamentally different approach from pg_repack. Instead of using triggers, it leverages PostgreSQL's logical decoding to capture changes during the copy process.

### How pg_squeeze Works

1. Creates a shadow table copy
2. Uses logical decoding (via `test_decoding` output plugin) to capture changes during the copy
3. Replays captured changes into the shadow table
4. Acquires a brief lock to swap tables
5. Optionally removes unnecessary free space (the "squeeze" aspect)

### Installing pg_squeeze

```bash
# From source
git clone https://github.com/cybertec-postgresql/pg_squeeze.git
cd pg_squeeze
make && sudo make install

# Enable in postgresql.conf
# shared_preload_libraries = 'squeeze'
# wal_level = logical (required for logical decoding)
```

### PostgreSQL Configuration for pg_squeeze

```ini
# postgresql.conf additions for pg_squeeze
shared_preload_libraries = 'squeeze'
wal_level = logical
max_replication_slots = 10
max_wal_senders = 10
```

### Docker Compose with pg_squeeze

```yaml
version: "3.8"
services:
  postgres-squeeze:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: secretpassword
    volumes:
      - pgdata_squeeze:/var/lib/postgresql/data
    command: >
      postgres
      -c shared_preload_libraries=squeeze
      -c wal_level=logical
      -c max_replication_slots=10
    ports:
      - "5433:5432"

volumes:
  pgdata_squeeze:
```

### Running pg_squeeze

```sql
-- Configure squeeze thresholds
SELECT squeeze.squeeze_table(
    schema_name := 'public',
    table_name := 'large_table',
    free_space_threshold := 0.3,
    lock_timeout := 5000
);

-- Check squeeze status
SELECT * FROM squeeze.log;
```

### pg_squeeze Advantages Over pg_repack

- **No triggers**: Logical decoding has lower overhead than row-level triggers on heavily written tables
- **Configurable thresholds**: Only rebuilds tables exceeding a specified bloat percentage
- **Automatic scheduling**: Built-in scheduler runs maintenance on a configurable interval
- **Better free space management**: Actively squeezes free space, not just reorganizes

## pgcompacttable: The Lightweight Script

**GitHub**: [dataegret/pgcompacttable](https://github.com/dataegret/pgcompacttable) · 356 stars

pgcompacttable is a Python script developed by Data Egret that takes a different approach entirely. Rather than creating shadow tables, it incrementally reduces bloat by running targeted VACUUM operations on individual pages.

### How pgcompacttable Works

1. Analyzes table bloat using pg_stat_user_tables
2. Runs VACUUM on tables exceeding the bloat threshold
3. Uses small, incremental operations to avoid long locks
4. Monitors lock wait times and backs off if contention is detected

### Installing pgcompacttable

```bash
# Clone and install
git clone https://github.com/dataegret/pgcompacttable.git
cd pgcompacttable
pip install -r requirements.txt

# Run directly
python3 pgcompacttable.py \
    --host localhost \
    --port 5432 \
    --username postgres \
    --dbname production \
    --bloat-percentage 20
```

### Docker Compose with pgcompacttable

```yaml
version: "3.8"
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: secretpassword
    ports:
      - "5434:5432"

  pgcompacttable:
    image: python:3.11-slim
    depends_on:
      - postgres
    working_dir: /app
    command: >
      bash -c "
        pip install psycopg2-binary &&
        git clone https://github.com/dataegret/pgcompacttable.git &&
        cd pgcompacttable &&
        python3 pgcompacttable.py
          --host postgres
          --port 5432
          --username postgres
          --dbname production
          --bloat-percentage 20
          --verbose
      "
```

### pgcompacttable Characteristics

| Feature | Detail |
|---------|--------|
| Lock impact | Minimal — uses standard VACUUM with lock timeout awareness |
| Effectiveness | Moderate — reduces bloat incrementally, doesn't fully rebuild |
| Setup complexity | Low — no extensions or preload libraries required |
| Primary key needed | No |
| Disk overhead | None — works in-place |

## Comprehensive Comparison

| Feature | pg_repack | pg_squeeze | pgcompacttable |
|---------|----------|-----------|----------------|
| Approach | Trigger-based shadow copy | Logical decoding shadow copy | Incremental VACUUM |
| Table rebuild | Full rebuild | Full rebuild | Partial reduction |
| Bloat elimination | Complete | Complete | Incremental |
| Index rebuild | Yes | Yes | No (relies on VACUUM) |
| Required extension | Yes (pg_repack) | Yes (squeeze) | No |
| PostgreSQL config | shared_preload_libraries | shared_preload_libraries + wal_level=logical | None |
| Primary key required | Yes | No | No |
| Lock duration | ~1 second swap | ~1 second swap | None (uses VACUUM) |
| Disk overhead | 2x table size | 2x table size | None |
| Maturity | Very mature (since 2012) | Modern (active since 2019) | Moderate (2017, slower updates) |

## Choosing the Right Maintenance Tool

**Use pg_repack when:**
- You need complete table and index rebuilds
- Your tables have primary keys or unique NOT NULL constraints
- You want the most battle-tested solution
- You have sufficient disk space for shadow copies

**Use pg_squeeze when:**
- You want automated, threshold-based maintenance
- Trigger overhead on busy tables is a concern
- You need maintenance without primary key constraints
- You're running PostgreSQL 12+ with logical decoding support

**Use pgcompacttable when:**
- You cannot install extensions (shared hosting, managed services)
- You need a zero-overhead solution that works in-place
- Incremental bloat reduction is acceptable
- You want a simple Python script with minimal dependencies

## Why Self-Host PostgreSQL Maintenance Tools?

Running PostgreSQL maintenance tools on your own infrastructure ensures that database optimization happens on your schedule, not your cloud provider's. Self-hosted PostgreSQL gives you direct access to the database server for running pg_repack, pg_squeeze, or pgcompacttable without API limitations or maintenance windows imposed by managed service providers.

For organizations with large PostgreSQL deployments, self-hosting maintenance tools provides predictable performance characteristics, full control over scheduling, and the ability to tune maintenance operations based on your specific workload patterns. You can integrate these tools with your existing monitoring stack to trigger maintenance automatically when bloat thresholds are exceeded.

For related PostgreSQL management, see our [PostgreSQL backup guide](../pgbackrest-vs-barman-vs-wal-g-self-hosted-postgresql-backup-guide-2026/) for comprehensive backup strategies and [PostgreSQL high availability setup](../patroni-vs-galera-cluster-vs-repmgr-self-hosted-database-high-availability-guide-2026/) for production deployments.

## FAQ

### Does pg_repack block reads and writes during table rebuild?

No. pg_repack uses triggers to capture changes while building a shadow copy. Reads and writes continue normally during the copy phase. Only the final table swap requires an ACCESS EXCLUSIVE lock, which typically lasts less than one second. This is dramatically faster than VACUUM FULL, which blocks all access for the entire rebuild duration.

### Can I run pg_repack on tables without a primary key?

No. pg_repack requires either a primary key or a UNIQUE NOT NULL constraint to identify rows during the trigger-based change capture. If your table lacks both, you'll need to add one before running pg_repack, or use pgcompacttable which has no such requirement.

### How much disk space does pg_repack need?

Approximately twice the table size. pg_repack creates a complete shadow copy of the table, including all indexes. For a 50 GB table, you'll need about 50 GB of free space for the shadow copy. After the swap, the old table is dropped and space is reclaimed.

### Is pg_squeeze production-ready?

Yes. pg_squeeze has been in active development since 2019 and is used in production by Cybertec's clients. It requires PostgreSQL 12+ with logical decoding enabled (`wal_level = logical`). The main consideration is the additional WAL generation during the copy phase, which may impact replication lag on busy systems.

### Can I automate table maintenance on a schedule?

Yes. pg_squeeze has a built-in scheduler that runs maintenance on configurable intervals. For pg_repack, you can use cron, systemd timers, or Kubernetes CronJobs to schedule periodic runs. pgcompacttable can be wrapped in a cron job with the desired bloat threshold parameters.

### What happens if pg_repack is interrupted mid-operation?

If the process is killed during the copy phase, pg_repack cleans up the shadow table and removes its triggers. No data is lost — the original table remains intact. If interrupted during the final swap, the operation can be retried. However, it's important to monitor disk space during large repack operations to prevent failures.

### Should I disable autovacuum when using these tools?

No. Autovacuum and these tools serve different purposes. Autovacuum handles routine dead tuple cleanup and prevents transaction ID wraparound. Tools like pg_repack and pg_squeeze address structural bloat that autovacuum cannot fix. Keep autovacuum enabled and use these tools as supplementary maintenance on a weekly or monthly schedule.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted PostgreSQL Table Maintenance: pg_repack vs pg_squeeze vs pgcompacttable 2026",
  "description": "Compare pg_repack, pg_squeeze, and pgcompacttable for online PostgreSQL table maintenance. Reclaim bloat and rebuild indexes without exclusive locks or downtime.",
  "datePublished": "2026-05-11",
  "dateModified": "2026-05-11",
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
