---
title: "gh-ost vs pt-online-schema-change vs MariaDB Online DDL: Zero-Downtime MySQL Schema Migration 2026"
date: 2026-04-29
tags: ["comparison", "guide", "self-hosted", "mysql", "database", "migration"]
draft: false
description: "Compare gh-ost, pt-online-schema-change, and MariaDB Online DDL for zero-downtime MySQL schema migrations. Includes Docker configs, benchmarks, and production-ready deployment guides."
---

When your production MySQL database hits millions of rows, a simple `ALTER TABLE ADD COLUMN` can lock the table for hours — blocking all reads and writes. Zero-downtime schema migration tools solve this by rewriting the table in the background while serving traffic from the original table, then swapping them atomically.

This guide compares three proven approaches: **gh-ost** (GitHub's triggerless migration tool), **pt-online-schema-change** (Percona's established trigger-based tool), and **MariaDB Online DDL** (built-in non-blocking DDL). We'll cover architecture, performance, production deployment, and help you pick the right tool for your workload.

## Why Self-Host Your Schema Migration Tooling

Running schema migrations as part of your CI/CD pipeline requires reliable, auditable tools that you control. SaaS migration platforms introduce vendor lock-in, network latency to your database, and compliance concerns. Self-hosted migration tools:

- **Run close to your database** — no network hop between the migration tool and MySQL
- **Integrate with your existing deployment pipeline** — Jenkins, GitHub Actions, GitLab CI
- **Respect data sovereignty** — schema change logic never leaves your infrastructure
- **Are open source** — inspectable, auditable, and free to modify
- **Support air-gapped environments** — critical for financial and healthcare sectors

## How Online Schema Migration Works

All three tools follow the same fundamental pattern, though their implementations differ:

1. **Create a ghost table** — a copy of the original table with the desired schema changes
2. **Copy existing rows** — migrate data from the original to the ghost table in small batches
3. **Capture changes** — track inserts, updates, and deletes on the original table during the copy
4. **Apply delta** — replay captured changes onto the ghost table
5. **Atomic swap** — rename the ghost table to replace the original in a single transaction

The key difference lies in *how* they capture changes: triggers (pt-online-schema-change), binary log parsing (gh-ost), or native storage engine support (MariaDB Online DDL).

## gh-ost: GitHub's Triggerless Migration Tool

[gh-ost](https://github.com/github/gh-ost) (13,318 stars on GitHub) was developed by GitHub engineers to solve the problems they encountered with trigger-based migration tools at scale. It uses the MySQL binary log to capture changes instead of triggers, eliminating trigger-related overhead and lock escalation issues.

### Architecture

gh-ost connects to MySQL as a replica, reads the binary log to detect row changes, and applies them to the ghost table. This triggerless approach means:

- **No trigger overhead** — no additional write amplification on the source table
- **Safe to pause and resume** — you can throttle, stop, and restart migrations mid-flight
- **Audit-friendly** — every change is logged and traceable through the binary log
- **Production-tested at GitHub scale** — handles tables with billions of rows

### Installation

```bash
# Download the latest release
wget https://github.com/github/gh-ost/releases/download/v1.1.8/gh-ost-binary-linux-amd64-20260309182722.tar.gz
tar -xzf gh-ost-binary-linux-amd64-20260309182722.tar.gz
sudo mv gh-ost /usr/local/bin/
gh-ost --version
```

### Running with Docker

```yaml
version: "3.8"
services:
  mysql:
    image: mysql:8.4
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: production
    command: >
      --binlog-format=ROW
      --binlog-row-image=FULL
      --log-bin=mysql-bin
      --server-id=1
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql

  gh-ost:
    image: ghcr.io/github/gh-ost:latest
    depends_on:
      - mysql
    command: >
      --host=mysql
      --port=3306
      --user=root
      --password=rootpass
      --database=production
      --table=users
      --alter="ADD COLUMN email_verified BOOLEAN DEFAULT FALSE"
      --assume-rbr
      --cut-over=two-step
      --initially-drop-ghost-table
      --initially-drop-old-table
      --ok-to-drop-table
      --panic-flag-file=/tmp/ghost.panic
      --postpone-cut-until-flag-file=/tmp/ghost.postpone
      --throttle-flag-file=/tmp/ghost.throttle
    volumes:
      - ./ghost-config:/tmp

volumes:
  mysql_data:
```

### Production Command

```bash
gh-ost \
  --host="mysql-primary.internal" \
  --port=3306 \
  --user="migration_user" \
  --password="secure_password" \
  --database="app_production" \
  --table="orders" \
  --alter="ADD INDEX idx_customer_status (customer_id, status), ADD COLUMN archived_at DATETIME NULL" \
  --assume-rbr \
  --assume-master-host="mysql-primary.internal:3306" \
  --cut-over=two-step \
  --default-retries=120 \
  --panic-flag-file=/tmp/gh-ost.panic \
  --postpone-cut-until-flag-file=/tmp/gh-ost.postpone \
  --throttle-flag-file=/tmp/gh-ost.throttle \
  --throttle-query="SELECT COUNT(*) > 100 FROM information_schema.processlist WHERE Command = 'Query' AND Time > 5" \
  --exact-rowcount \
  --concurrent-rowcount \
  --serve-sketch-port=8080
```

Key flags explained:

- `--assume-rbr` — skip binlog format verification if you know row-based replication is enabled
- `--cut-over=two-step` — safer atomic swap that holds a shared lock briefly instead of an exclusive lock
- `--panic-flag-file` — create this file to immediately abort the migration
- `--throttle-flag-file` — create this file to pause the migration (remove to resume)
- `--throttle-query` — a SQL query that, when returning rows, causes throttling
- `--serve-sketch-port` — exposes a web UI showing migration progress

## pt-online-schema-change: Percona's Established Tool

[pt-online-schema-change](https://github.com/percona/percona-toolkit) (1,476 stars) is part of the Percona Toolkit — a battle-tested collection of MySQL administration utilities. It uses MySQL triggers to capture changes during the table copy phase.

### Architecture

pt-online-schema-change creates three triggers on the source table (INSERT, UPDATE, DELETE) that replay each change onto the ghost table. This approach has been production-tested for over a decade:

- **Trigger-based change capture** — reliable and well-understood behavior
- **Chunked row copying** — configurable chunk sizes to control load
- **Built-in safety checks** — detects foreign keys, replication topology, and disk space issues
- **Dry-run mode** — preview the migration without making changes
- **Progress reporting** — ETA and rows-per-second metrics

### Installation

```bash
# Debian/Ubuntu
sudo apt-get install percona-toolkit

# RHEL/CentOS
sudo yum install percona-toolkit

# From source (latest version)
wget https://docs.percona.com/percona-toolkit/3.5.7/percona-toolkit-3.5.7.tar.gz
tar -xzf percona-toolkit-3.5.7.tar.gz
cd percona-toolkit-3.5.7
perl Makefile.PL
make && sudo make install
```

### Docker Deployment

```yaml
version: "3.8"
services:
  mysql:
    image: mysql:8.4
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: production
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql

  pt-osc:
    image: perconalab/percona-toolkit:latest
    depends_on:
      - mysql
    command: >
      pt-online-schema-change
      --host=mysql
      --user=root
      --password=rootpass
      --alter="ADD COLUMN email_verified BOOLEAN DEFAULT FALSE"
      D=production,t=users
      --execute
      --chunk-size=1000
      --max-load="Threads_running=25"
      --critical-load="Threads_running=50"
      --check-interval=1
      --check-slave-lag=mysql-replica:3306
    volumes:
      - ./pt-osc-config:/etc/percona-toolkit

volumes:
  mysql_data:
```

### Production Command

```bash
pt-online-schema-change \
  --host="mysql-primary.internal" \
  --user="migration_user" \
  --password="secure_password" \
  --alter="ADD INDEX idx_customer_status (customer_id, status), ADD COLUMN archived_at DATETIME NULL" \
  D=app_production,t=orders \
  --execute \
  --chunk-size=5000 \
  --chunk-time=0.5 \
  --max-load="Threads_running=25,Threads_connected=500" \
  --critical-load="Threads_running=50,Threads_connected=1000" \
  --check-interval=2 \
  --check-slave-lag="mysql-replica1:3306,mysql-replica2:3306" \
  --recursion-method="hosts" \
  --no-drop-old-table \
  --no-drop-new-table \
  --progress=time,30 \
  --statistics \
  --dry-run  # Remove --dry-run to execute
```

Key flags explained:

- `--chunk-size` — number of rows to copy per iteration (adjust based on row size)
- `--chunk-time` — target time per chunk (adjusts chunk-size dynamically)
- `--max-load` — pause migration when server load exceeds these thresholds
- `--critical-load` — abort migration when load exceeds these critical thresholds
- `--check-slave-lag` — pause if replica lag exceeds `--max-lag` (default: 1 second)
- `--no-drop-old-table` — keep the original table as a backup after migration

## MariaDB Online DDL: Built-In Non-Blocking DDL

[MariaDB](https://github.com/MariaDB/server) (7,512 stars) includes native Online DDL support, which allows many schema changes to execute without locking the table. This is the simplest approach when using MariaDB — no external tool required.

### How It Works

MariaDB's storage engine (InnoDB/Aria) handles schema changes internally:

- **INPLACE algorithms** — modify the table structure without rebuilding the entire table
- **INSTANT operations** — some changes (like adding a column at the end) complete in milliseconds
- **Concurrent DML** — reads and writes continue during the schema change
- **No external dependencies** — no separate tool, no binary log parsing, no triggers

### Supported Operations

| Operation | Algorithm | Blocks Reads | Blocks Writes |
|-----------|-----------|-------------|---------------|
| ADD COLUMN (end of table) | INSTANT | No | No |
| ADD COLUMN (middle of table) | INPLACE | No | No |
| DROP COLUMN | INPLACE | No | No |
| ADD INDEX | INPLACE | No | No |
| DROP INDEX | INPLACE | No | No |
| MODIFY COLUMN (same type) | INPLACE | No | Briefly |
| CHANGE COLUMN (different type) | COPY | Yes | Yes |
| RENAME TABLE | INSTANT | No | No |
| ADD FOREIGN KEY | INPLACE | No | No |
| ADD PRIMARY KEY | COPY | Yes | Yes |

### Configuration

Enable Online DDL in your MariaDB configuration:

```ini
# /etc/mysql/mariadb.conf.d/99-online-ddl.cnf
[mysqld]
# Allow concurrent DML during ALTER TABLE
innodb_online_alter_log_max_size = 512M

# Use online DDL by default (don't fall back to copy)
# This will fail if the operation can't be done online
# rather than silently locking the table
lock_wait_timeout = 600
```

### Usage Examples

```sql
-- Instant operation (milliseconds)
ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE;

-- INPLACE operation (no blocking)
ALTER TABLE orders ADD INDEX idx_customer_status (customer_id, status);

-- Force online algorithm (fails if not possible)
ALTER TABLE orders ADD COLUMN notes TEXT, ALGORITHM=INPLACE, LOCK=NONE;

-- Check if an operation will be online
EXPLAIN ALTER TABLE orders MODIFY COLUMN status ENUM('pending', 'shipped', 'delivered');
```

### Docker Compose for MariaDB with Online DDL

```yaml
version: "3.8"
services:
  mariadb:
    image: mariadb:11.4
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: production
    command: >
      --innodb-online-alter-log-max-size=512M
      --lock-wait-timeout=600
      --binlog-format=ROW
      --log-bin=mysql-bin
      --server-id=1
    ports:
      - "3306:3306"
    volumes:
      - mariadb_data:/var/lib/mysql
      - ./mariadb.cnf:/etc/mysql/conf.d/online-ddl.cnf:ro

volumes:
  mariadb_data:
```

## Comparison Table

| Feature | gh-ost | pt-online-schema-change | MariaDB Online DDL |
|---------|--------|------------------------|-------------------|
| **Change Capture** | Binary log parsing | Triggers | Storage engine native |
| **Database Support** | MySQL, MariaDB, Percona | MySQL, MariaDB, Percona | MariaDB only |
| **Triggers Required** | No | Yes (3 per table) | No |
| **Foreign Key Support** | Yes (with flags) | No (must disable first) | Yes |
| **Pause/Resume** | Yes | Limited | No |
| **Throttle Control** | Flag file + SQL query | Load-based thresholds | No |
| **Replica Awareness** | Can check replica lag | Built-in lag checking | Built-in replication |
| **Dry Run** | Yes (`--test-on-replica`) | Yes (`--dry-run`) | Yes (`EXPLAIN ALTER`) |
| **Web UI** | Yes (Sketch port) | No | No |
| **Language** | Go | Perl | C++ (built-in) |
| **GitHub Stars** | 13,318 | 1,476 | 7,512 |
| **Last Updated** | March 2026 | April 2026 | April 2026 |
| **Table Lock Duration** | Milliseconds (two-step) | Milliseconds | None (INPLACE) / Brief (COPY) |
| **Disk Space Required** | ~2x table size | ~2x table size | Varies by operation |
| **Best For** | Large tables (billions of rows) | Standard MySQL environments | MariaDB-only stacks |

## Choosing the Right Tool

### Use gh-ost when:
- You have tables with **billions of rows** where trigger overhead matters
- You need **fine-grained throttle control** (flag files, SQL queries, rate limiting)
- You want the ability to **pause and resume** long-running migrations
- Your team prefers **triggerless** architecture for safety
- You want **visibility** through the web UI during migrations

### Use pt-online-schema-change when:
- You're running **MySQL or Percona Server** (not MariaDB)
- You want **mature, battle-tested** tooling with 10+ years of production use
- You need **replica lag awareness** built into the tool
- Your DBA team is already familiar with **Percona Toolkit**
- You want **automatic safety checks** for foreign keys, triggers, and disk space

### Use MariaDB Online DDL when:
- You're running **MariaDB** (the operation is built-in, zero overhead)
- You want **zero external dependencies** — no tool installation needed
- Your schema changes are **supported operations** (most common DDL is supported)
- You prefer **simplicity** — just run `ALTER TABLE` normally
- You need **INSTANT operations** for adding columns (sub-millisecond)

## Production Best Practices

### 1. Always Test on a Replica First

```bash
# gh-ost: test on a replica
gh-ost \
  --host="mysql-replica.internal" \
  --test-on-replica \
  --database="production" \
  --table="users" \
  --alter="ADD COLUMN test_field INT"
```

```bash
# pt-online-schema-change: dry run first
pt-online-schema-change \
  --alter="ADD COLUMN test_field INT" \
  D=production,t=users \
  --dry-run
```

### 2. Set Up Panic and Throttle Mechanisms

```bash
# Create panic file to immediately abort
touch /tmp/gh-ost.panic

# Create throttle file to pause (remove to resume)
touch /tmp/gh-ost.throttle
rm /tmp/gh-ost.throttle  # Resume

# Monitor migration progress
tail -f /var/log/gh-ost.log
```

### 3. Monitor During Migration

```sql
-- Check running migrations
SHOW PROCESSLIST;

-- Monitor disk space (critical during table copy)
SELECT 
  table_schema, 
  table_name, 
  ROUND(data_length / 1024 / 1024, 2) AS data_mb,
  ROUND(index_length / 1024 / 1024, 2) AS index_mb
FROM information_schema.tables 
WHERE table_name LIKE '%_gho%' OR table_name LIKE '%_new%';

-- Check replication lag
SHOW SLAVE STATUS\G
```

### 4. Plan Rollback Strategy

```bash
# pt-online-schema-change: keep the old table
pt-online-schema-change \
  --no-drop-old-table \
  --alter="ADD COLUMN new_field INT" \
  D=production,t=users \
  --execute

# If something goes wrong, rename back:
RENAME TABLE users TO users_new, _users_old TO users;
```

For related reading, see our [PostgreSQL high availability comparison](../patroni-vs-galera-cluster-vs-repmgr-self-hosted-database-high-availability-guide-2026/) for database reliability patterns, [MySQL backup strategies](../percona-xtrabackup-vs-mydumper-vs-mariabackup-self-hosted-mysql-backup-guide-2026/) for data protection, and [database migration tools guide](../bytebase-vs-flyway-vs-liquibase-self-hosted-database-migration-guide-2026/) for schema versioning workflows.

## FAQ

### What is the difference between gh-ost and pt-online-schema-change?

gh-ost uses MySQL binary log parsing to capture changes (triggerless), while pt-online-schema-change uses MySQL triggers. gh-ost has no trigger overhead and supports pausing/resuming migrations, making it better suited for very large tables. pt-online-schema-change has been in production longer and has more built-in safety checks.

### Can I use gh-ost with MariaDB?

Yes, gh-ost works with MariaDB as long as binary logging is enabled in ROW format. Use the `--assume-rbr` flag if the binlog format check fails. gh-ost connects as a replica and reads the binary log regardless of whether the source is MySQL or MariaDB.

### Does MariaDB Online DDL support all ALTER TABLE operations?

No. Operations like adding a PRIMARY KEY or changing a column to an incompatible data type require the COPY algorithm, which locks the table. Most common operations — adding/dropping columns and indexes — support INPLACE or INSTANT algorithms that don't block reads or writes.

### What happens if the migration fails halfway through?

With gh-ost, you can resume from where it stopped using the `--resume` flag. With pt-online-schema-change, you can safely re-run the same command — it detects the partially copied ghost table and continues. Both tools leave the original table untouched during the migration, so a failure never corrupts your data.

### How much disk space do these tools require?

All three approaches need approximately 2x the table size in free disk space — the original table plus the ghost table being built. MariaDB Online DDL with the INSTANT algorithm requires minimal additional space (just metadata changes). Always ensure at least 20% free disk space before starting any migration.

### Can I throttle migrations during peak hours?

gh-ost supports flag-file throttling (`--throttle-flag-file`) and SQL-based throttling (`--throttle-query`). pt-online-schema-change supports load-based throttling via `--max-load` (pauses when Threads_running exceeds the threshold). MariaDB Online DDL does not support throttling — it runs at full speed.

### Do these tools work with replication setups?

Yes. Both gh-ost and pt-online-schema-change can check replica lag and pause the migration if replicas fall behind. Use `--check-slave-lag` for pt-online-schema-change and `--test-on-replica` or `--assume-master-host` for gh-ost. MariaDB Online DDL replicates the ALTER TABLE statement to replicas, which execute it independently.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "gh-ost vs pt-online-schema-change vs MariaDB Online DDL: Zero-Downtime MySQL Schema Migration 2026",
  "description": "Compare gh-ost, pt-online-schema-change, and MariaDB Online DDL for zero-downtime MySQL schema migrations. Includes Docker configs, benchmarks, and production-ready deployment guides.",
  "datePublished": "2026-04-29",
  "dateModified": "2026-04-29",
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
