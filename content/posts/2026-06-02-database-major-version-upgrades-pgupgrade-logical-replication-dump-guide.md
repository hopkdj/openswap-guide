---
title: "Self-Hosted Database Major Version Upgrades: pg_upgrade vs Logical Replication vs Dump/Restore"
date: "2026-06-02"
tags: ["postgresql", "mysql", "database", "migration", "upgrade", "devops", "administration"]
draft: false

---

## Introduction

Every database administrator eventually faces the same challenge: upgrading to a new major version without disrupting production traffic. PostgreSQL releases a new major version annually, MySQL/MariaDB follow their own cadence, and each upgrade brings performance improvements, new features, and security fixes. But upgrading a production database holding terabytes of data is not a trivial task — the wrong approach can mean hours (or days) of downtime.

This guide compares three upgrade strategies for self-hosted databases: **pg_upgrade** (fast in-place upgrades using binary compatibility), **logical replication** (near-zero downtime through online migration), and **dump/restore** (the traditional, most reliable method). Each has different trade-offs in downtime, complexity, and risk — understanding when to use each one is critical for maintaining uptime SLAs.

## Comparison Table

| Feature | pg_upgrade | Logical Replication | Dump/Restore |
|---------|-----------|-------------------|-------------|
| **Downtime** | Minutes (regardless of DB size) | Near-zero (seconds for cutover) | Hours to days (proportional to size) |
| **Complexity** | Low (single command) | High (replication setup, monitoring) | Medium (scripted export/import) |
| **Disk Space** | Minimal (uses existing data) | 2x (full copy on new version) | 2-3x (dump file + restored DB) |
| **Validation** | Built-in checks | Application-level testing | Full validation during import |
| **Risk Level** | Medium (binary incompatibility) | Low (old version stays online) | Low (original untouched) |
| **Rollback** | Requires backup restore | Instant (switch back to old server) | Instant (original untouched) |
| **Works For** | PostgreSQL only | PostgreSQL 10+, MySQL 8.0+ | All databases |
| **Best When** | Same architecture, same OS | Cannot tolerate downtime | Small DBs, changing architecture |

## pg_upgrade: In-Place Binary Upgrade

[pg_upgrade](https://www.postgresql.org/docs/current/pgupgrade.html) is PostgreSQL's built-in tool for in-place major version upgrades. It works by reusing the existing data files and only upgrading the system catalog — this means a 5 TB database can be upgraded in minutes, regardless of data size.

### How It Works

pg_upgrade operates in two modes:

1. **Link mode** (`--link`): Creates hard links to the old data files in the new cluster's directory. Data files are shared between old and new versions. **Fastest, but you cannot roll back** (changes in the new cluster will affect the old one's files).

2. **Copy mode**: Copies data files from old to new cluster. Slower (time proportional to data size) but safer — the old cluster remains untouched.

### Step-by-Step Upgrade (Link Mode)

```bash
# 1. Install the new PostgreSQL version
apt-get install postgresql-17

# 2. Stop both clusters
pg_ctlcluster 16 main stop
pg_ctlcluster 17 main stop

# 3. Run pg_upgrade in link mode
/usr/lib/postgresql/17/bin/pg_upgrade     --old-datadir=/var/lib/postgresql/16/main     --new-datadir=/var/lib/postgresql/17/main     --old-bindir=/usr/lib/postgresql/16/bin     --new-bindir=/usr/lib/postgresql/17/bin     --link     --check

# 4. If --check passes, re-run without --check
/usr/lib/postgresql/17/bin/pg_upgrade     --old-datadir=/var/lib/postgresql/16/main     --new-datadir=/var/lib/postgresql/17/main     --old-bindir=/usr/lib/postgresql/16/bin     --new-bindir=/usr/lib/postgresql/17/bin     --link

# 5. Start the new cluster
pg_ctlcluster 17 main start

# 6. Update statistics
psql -c "ANALYZE VERBOSE"

# 7. If successful, remove old cluster
pg_dropcluster 16 main
```

### Pre-Upgrade Checklist

```sql
-- Check for incompatible data types
SELECT DISTINCT typname FROM pg_type WHERE typname LIKE 'abstime%' 
UNION SELECT 'regclass' WHERE EXISTS (SELECT 1 FROM pg_class WHERE reltype IN 
    (SELECT oid FROM pg_type WHERE typname = 'regclass'));

-- Ensure no prepared transactions
SELECT * FROM pg_prepared_xacts;

-- Check for invalid objects
SELECT * FROM pg_class WHERE relkind = 'v' AND NOT relispartition 
    AND relnamespace NOT IN (SELECT oid FROM pg_namespace WHERE nspname IN ('pg_catalog', 'information_schema'));
```

pg_upgrade is the gold standard for PostgreSQL upgrades when you can afford 5-15 minutes of scheduled downtime. For high-availability requirements, consider logical replication instead.

## Logical Replication: Near-Zero Downtime Migration

Logical replication allows you to set up a new PostgreSQL cluster running the target version, replicate all data from the old cluster, and then cut over with seconds of downtime. This approach gives you **near-zero downtime** because the old database continues serving traffic during the entire migration.

### Setup Process

```sql
-- On OLD cluster (PostgreSQL 16):
-- 1. Configure wal_level for logical replication
-- postgresql.conf: wal_level = logical

-- 2. Create a publication for all tables
CREATE PUBLICATION upgrade_pub FOR ALL TABLES;

-- 3. Create a replication slot (prevents WAL cleanup)
SELECT pg_create_logical_replication_slot('upgrade_slot', 'pgoutput');
```

```sql
-- On NEW cluster (PostgreSQL 17):
-- 1. Restore schema only from old cluster
-- pg_dumpall --schema-only | psql

-- 2. Create subscriptions for each database
CREATE SUBSCRIPTION upgrade_sub
    CONNECTION 'host=old-host port=5432 dbname=mydb'
    PUBLICATION upgrade_pub
    WITH (copy_data = true, create_slot = false);
```

### Monitoring Replication Lag

```sql
-- Check subscription status
SELECT 
    subname,
    pg_size_pretty(pg_current_wal_lsn() - received_lsn) AS replication_lag,
    latest_end_lsn,
    last_msg_send_time
FROM pg_stat_subscription;

-- Wait for catch-up
SELECT pg_current_wal_lsn() - received_lsn AS lag_bytes
FROM pg_stat_subscription 
WHERE subname = 'upgrade_sub';
```

When lag approaches zero, you're ready for cutover:

```bash
# 1. Stop application traffic to old database
# 2. Wait for final catch-up
psql -c "ALTER SUBSCRIPTION upgrade_sub REFRESH PUBLICATION"
# 3. Promote new cluster as primary
# 4. Update connection strings
# 5. Drop subscription and publication
```

### MySQL/MariaDB Logical Upgrade

For MySQL, the equivalent approach uses MySQL 8.0's binary log replication:

```sql
-- On OLD server (MySQL 5.7):
CHANGE MASTER TO MASTER_HOST='new-host', MASTER_USER='repl', 
    MASTER_PASSWORD='password', MASTER_LOG_FILE='mysql-bin.000001', 
    MASTER_LOG_POS=4;
START SLAVE;

-- Monitor until Seconds_Behind_Master = 0
SHOW SLAVE STATUS\G
```

For a detailed look at replication monitoring tools, see our [PostgreSQL logical replication guide](../2026-05-10-postgresql-logical-replication-pglogical-wal2json-pgoutput-guide/).

## Dump/Restore: The Traditional Safety Net

The dump/restore method is the most time-consuming but also the most reliable — it works across any PostgreSQL version, architecture, or operating system. It creates a complete logical copy of the database, giving you an opportunity to validate data integrity during the restore.

### pg_dumpall for Full Cluster Migration

```bash
# Export entire cluster (roles, tablespaces, databases)
pg_dumpall -h old-host -U postgres     --roles-only > roles.sql

pg_dumpall -h old-host -U postgres     --globals-only > globals.sql

# Export each database in parallel
for db in $(psql -h old-host -U postgres -Atc "SELECT datname FROM pg_database WHERE datistemplate = false"); do
    pg_dump -h old-host -U postgres -Fd -j 4 -f "${db}_dump" "$db" &
done
wait

# Restore to new cluster
psql -h new-host -U postgres -f roles.sql
psql -h new-host -U postgres -f globals.sql

for dump_dir in *_dump; do
    db_name=$(basename "$dump_dir" _dump)
    createdb -h new-host -U postgres "$db_name"
    pg_restore -h new-host -U postgres -d "$db_name" -j 4 "$dump_dir"
done
```

### Performance Optimization

```bash
# Speed up pg_dump with custom format and parallel jobs
pg_dump -Fd -j 8 -f /backup/mydb_dump mydb

# Speed up restore by disabling WAL and constraints temporarily
psql -c "ALTER SYSTEM SET fsync = off; SELECT pg_reload_conf();"
psql -c "ALTER SYSTEM SET full_page_writes = off; SELECT pg_reload_conf();"

# Restore with maintenance_work_mem boosted
pg_restore -j 8 --maintenance-work-mem=2GB -d mydb /backup/mydb_dump

# Re-enable safety settings after restore
psql -c "ALTER SYSTEM SET fsync = on; SELECT pg_reload_conf();"
psql -c "ALTER SYSTEM SET full_page_writes = on; SELECT pg_reload_conf();"
```

## Why Self-Host Your Upgrades

Managing your own database upgrades gives you total control over timing and methodology. Cloud-managed databases often enforce upgrade windows, restrict available methods (many don't support pg_upgrade's link mode), or charge for additional replicas needed during migration. With a self-hosted setup, you can schedule upgrades during your lowest-traffic period, run multiple dry-run tests on staging replicas, and choose the exact upgrade strategy that balances your downtime tolerance against complexity.

Version flexibility is another advantage. PostgreSQL 16 users who want to test the new incremental backup features in PostgreSQL 17 can spin up a logical replica, validate their workload, and roll back if issues surface — all on their existing hardware. Cloud services typically prevent downgrades and may not support the latest major version for weeks after release. To ensure you can recover from any upgrade failure, pair this guide with our [PostgreSQL backup tools comparison](../pgbackrest-vs-barman-vs-wal-g-self-hosted-postgresql-backup-guide-2026/) — a tested backup is your safety net before any major version change.

For organizations running PostgreSQL at scale, the pg_upgrade link mode on a 10 TB database means 8 minutes of downtime versus 12+ hours for dump/restore. That difference alone can justify self-hosting: you get access to the fastest upgrade paths without cloud provider restrictions on filesystem-level operations. If you're running PostgreSQL on Kubernetes, check our [PostgreSQL operators guide](../2026-05-10-postgresql-operators-kubernetes-cloudnativepg-zalando-crunchydata-guide/) for operator-specific upgrade strategies.

## Choosing the Right Strategy

| Scenario | Recommended Method |
|----------|-------------------|
| PostgreSQL upgrade, same server, < 1 TB | pg_upgrade (link mode) |
| PostgreSQL upgrade, different server | Logical replication |
| Cannot tolerate > 1 min downtime | Logical replication |
| Changing OS architecture (x86 → ARM) | Dump/restore |
| Major PG version jump (14 → 17) | Dump/restore or logical |
| Database < 50 GB, validation needed | Dump/restore |
| Must keep old version online as fallback | Logical replication |
| MySQL/MariaDB upgrade | Replication or dump/restore |

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Database Major Version Upgrades: pg_upgrade vs Logical Replication vs Dump/Restore",
  "description": "Compare pg_upgrade, logical replication, and dump/restore for self-hosted database major version upgrades — minimize downtime when migrating PostgreSQL and MySQL to new versions.",
  "datePublished": "2026-06-02",
  "dateModified": "2026-06-02",
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

## FAQ

### Can I use pg_upgrade to upgrade from PostgreSQL 13 to 17 directly?

pg_upgrade supports upgrading from any version ≥ 9.2 to any newer version. However, skipping three major versions (13 → 17) increases the risk of catalog incompatibilities. The safest approach is upgrading one major version at a time (13→14→15→16→17), but if you must go directly, run with `--check` first and carefully review the output. Always have a verified backup before attempting multi-version jumps.

### How do I handle extensions during pg_upgrade?

pg_upgrade does NOT migrate extensions automatically. You must install the new PostgreSQL version of every extension BEFORE running pg_upgrade. After the upgrade, run `ALTER EXTENSION ... UPDATE` for each extension. Common extensions like PostGIS, pg_stat_statements, and pgcrypto publish packages for new PG versions — install them with apt/yum before upgrading. Run `SELECT * FROM pg_available_extensions` on the new cluster to verify all required extensions are available.

### What happens if logical replication falls behind during the migration?

Logical replication can fall behind if the old cluster processes more WAL than the new cluster can apply. Monitor `pg_stat_subscription` for lag. If lag grows, you can speed up the subscriber by: (1) increasing `max_logical_replication_workers` and `max_sync_workers_per_subscription`, (2) temporarily pausing heavy write workloads, or (3) adding a second subscription that splits tables across workers. As a last resort, delete the subscription, restore a fresh pg_dump snapshot, and re-subscribe.

### How long does a dump/restore typically take?

As a rough estimate, `pg_dump -Fd -j 4` processes 50-100 GB per hour on spinning disks, and 100-200 GB per hour on SSDs. Restore (`pg_restore -j 4`) is generally 30-50% slower because it must rebuild indexes. A 500 GB database on NVMe storage might complete in 4-6 hours total (dump + restore). You can monitor progress: `pg_dump` shows table names as it processes them; `pg_restore` with `-v` provides detailed progress. For PostgreSQL 15+, `pg_stat_progress_copy` shows restore progress in real-time.

### Is it safe to disable fsync and full_page_writes during restore?

Disabling `fsync` and `full_page_writes` during a bulk restore can improve throughput by 2-5x. This is safe ONLY if: (1) you're restoring into a fresh, non-production cluster where data loss from a crash during restore is acceptable (just re-run pg_restore), and (2) you re-enable both settings before accepting production traffic. Never disable these on a live cluster — a power failure would corrupt the database.

---

**💡 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到 AI 监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测 AI 相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
