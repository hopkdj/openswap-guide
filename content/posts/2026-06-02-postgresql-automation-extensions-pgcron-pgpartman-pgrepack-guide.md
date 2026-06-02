---
title: "Self-Hosted PostgreSQL Automation Extensions: pg_cron vs pg_partman vs pg_repack"
date: "2026-06-02"
tags: ["postgresql", "database", "automation", "partitioning", "maintenance", "cron", "pg-repack", "self-hosted"]
draft: false
---

PostgreSQL's extension ecosystem provides powerful automation capabilities that go far beyond what's built into the core database engine. Rather than writing external scripts or cron jobs, you can handle job scheduling, table partitioning, and storage optimization directly within PostgreSQL using purpose-built extensions. This guide compares three essential automation extensions: pg_cron for scheduled job execution, pg_partman for automatic table partitioning, and pg_repack for online table reorganization.

## pg_cron: Scheduled Jobs Inside PostgreSQL

pg_cron brings cron-style job scheduling directly into PostgreSQL, allowing you to run SQL commands, stored procedures, and maintenance tasks on a recurring schedule. Unlike external cron jobs that require shell access and connection management, pg_cron jobs execute inside the database server process with native PostgreSQL authentication.

pg_cron uses the standard cron syntax for scheduling — you define jobs using the familiar five-field format (minute, hour, day of month, month, day of week). Jobs are stored in a `cron.job` metadata table and can be managed entirely through SQL:

```sql
-- Create the pg_cron extension
CREATE EXTENSION pg_cron;

-- Schedule a daily VACUUM ANALYZE at 2:00 AM
SELECT cron.schedule(
  'daily-vacuum',
  '0 2 * * *',
  'VACUUM ANALYZE'
);

-- Schedule partition maintenance every hour
SELECT cron.schedule(
  'partition-maintenance',
  '0 * * * *',
  'SELECT partman.run_maintenance()'
);

-- View all scheduled jobs
SELECT * FROM cron.job;

-- Unschedule a job
SELECT cron.unschedule('daily-vacuum');
```

For Docker deployments, pg_cron is included in the official PostgreSQL image but must be enabled via configuration:

```yaml
# docker-compose.yml for PostgreSQL with pg_cron
version: "3.8"
services:
  postgres:
    image: postgres:16
    container_name: postgres-pgcron
    restart: unless-stopped
    environment:
      POSTGRES_PASSWORD: securepassword
    command: >
      -c shared_preload_libraries=pg_cron
      -c cron.database_name=postgres
    ports:
      - "5432:5432"
    volumes:
      - ./pgdata:/var/lib/postgresql/data

  pgadmin:
    image: dpage/pgadmin4:latest
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@example.com
      PGADMIN_DEFAULT_PASSWORD: adminpass
    ports:
      - "8080:80"
```

## pg_partman: Automatic Table Partitioning

pg_partman (Partition Manager) automates the creation and maintenance of table partitions in PostgreSQL. As tables grow to millions or billions of rows, partitioning becomes essential for query performance and data management. pg_partman handles the tedious work of creating new partitions on schedule, detaching old partitions, and managing retention policies.

pg_partman supports both native PostgreSQL partitioning (declarative) and the older trigger-based partitioning. Key features include:

- **Time-based partitioning**: Create daily, weekly, monthly, or custom interval partitions automatically
- **ID-based partitioning**: Split tables by numeric ID ranges
- **Automatic partition creation**: Pre-creates future partitions according to your premake setting
- **Retention management**: Automatically detaches or drops partitions older than your retention policy
- **Template tables**: Inherit indexes, constraints, and defaults from a template table
- **Background worker**: Runs maintenance as a PostgreSQL background process

Setup and basic partition creation:

```sql
-- Create the extension
CREATE EXTENSION pg_partman;

-- Create a schema for partition management
CREATE SCHEMA partman;

-- Configure a parent table with daily time-based partitioning
SELECT partman.create_parent(
  p_parent_table := 'public.events',
  p_control := 'created_at',
  p_type := 'native',
  p_interval := '1 day',
  p_premake := 7,
  p_start_partition := '2026-01-01'
);

-- Set retention to keep 90 days of data
UPDATE partman.part_config
SET retention = '90 days',
    retention_keep_table = false
WHERE parent_table = 'public.events';

-- Run maintenance manually (or schedule via pg_cron)
SELECT partman.run_maintenance();
```

A production-ready configuration pairs pg_partman with pg_cron for scheduled maintenance:

```yaml
# Docker Compose with both extensions
version: "3.8"
services:
  postgres-partman:
    image: pgpartman/pg_partman:latest
    container_name: postgres-partman
    restart: unless-stopped
    environment:
      POSTGRES_PASSWORD: securepassword
    volumes:
      - ./pgdata-partman:/var/lib/postgresql/data
    ports:
      - "5433:5432"
```

## pg_repack: Online Table Reorganization

pg_repack solves one of PostgreSQL's most persistent operational challenges: table bloat. When rows are updated or deleted, PostgreSQL marks the old row versions as dead but doesn't immediately reclaim the space. Over time, this leads to table and index bloat — wasted disk space, slower queries, and increased I/O.

Unlike `VACUUM FULL` (which takes an exclusive lock and blocks all access) or `CLUSTER` (which also requires an exclusive lock), pg_repack reorganizes tables online with minimal locking. It works by creating a new copy of the table in the background, replicating changes from the original, and then swapping the tables in a brief final step.

```bash
# Install pg_repack
apt-get install -y postgresql-16-repack

# Repack a specific table
pg_repack -t public.events -d mydatabase

# Repack all tables in a database
pg_repack -d mydatabase

# Repack only indexes (faster than full table repack)
pg_repack -d mydatabase --only-indexes

# Repack with specific tablespace for the rebuild
pg_repack -t public.events -d mydatabase --tablespace=ssd_fast
```

For scheduled repacking via pg_cron, create a maintenance job:

```sql
-- Schedule weekly pg_repack via pg_cron (requires pg_repack in PATH)
SELECT cron.schedule(
  'weekly-repack-events',
  '0 3 * * 0',  -- 3 AM every Sunday
  $$SELECT pg_cron.pg_repack('public.events')$$
);
```

Monitoring table bloat before and after repacking:

```sql
-- Check table bloat using pgstattuple extension
CREATE EXTENSION pgstattuple;
SELECT * FROM pgstattuple('public.events');

-- Check dead tuple ratio
SELECT
  schemaname || '.' || relname AS table_name,
  n_dead_tup,
  n_live_tup,
  round(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_ratio
FROM pg_stat_user_tables
WHERE n_dead_tup > 0
ORDER BY n_dead_tup DESC
LIMIT 10;
```

## Comparison Table

| Feature | pg_cron | pg_partman | pg_repack |
|---------|---------|-----------|-----------|
| **Primary Purpose** | Job scheduling | Partition management | Online table reorganization |
| **GitHub Stars** | 3,798+ | 2,719+ | 2,251+ |
| **PostgreSQL Version** | 10+ | 11+ (native), 10+ (trigger) | 12+ |
| **Lock Level** | No table locks | Brief lock on partition creation | Brief exclusive lock at swap |
| **Shared Library** | Required | Optional (background worker) | Required |
| **Docker Support** | Official PG image | Dedicated image | Install via package |
| **Schedule Syntax** | Cron (5-field) | Interval-based + premake | N/A (run on demand or via pg_cron) |
| **Active Development** | Yes (April 2026) | Yes (March 2026) | Yes (May 2026) |
| **Resource Overhead** | Minimal | Moderate (partition management) | High during repack (I/O intensive) |
| **Cloud Compatibility** | AWS RDS, Cloud SQL, Supabase | AWS RDS, Cloud SQL | AWS RDS (limited), self-hosted |

## Why Self-Host Your PostgreSQL Automation Stack?

Database automation is not a luxury — it's a necessity for any production PostgreSQL deployment that handles more than a few gigabytes of data. Manual partition management becomes error-prone as table counts grow, and forgetting to create next month's partitions can cause insert failures at 2 AM. pg_partman eliminates this operational risk by pre-creating partitions and managing retention automatically. When combined with pg_cron for scheduling, you get a hands-off maintenance pipeline that runs partition creation, VACUUM operations, statistics updates, and blob cleanup without human intervention.

The alternative — external cron jobs connecting to PostgreSQL — introduces several failure modes. Network timeouts, authentication token expiration, and dependency on external monitoring all add complexity. By moving scheduling into PostgreSQL with pg_cron, you eliminate the external dependency and simplify your architecture. For broader database monitoring, see our [database monitoring comparison](../2026-04-18-pgwatch2-vs-percona-pmm-vs-pgmonitor-self-hosted-database-monitoring-guide-2026/) that covers comprehensive observability beyond what these extensions provide.

Table bloat is particularly insidious because it degrades performance gradually — queries get slower over weeks or months, and by the time you notice, the database has ballooned to 2-3x its optimal size. pg_repack gives you a surgical tool to reclaim space without downtime. Unlike `VACUUM FULL` which blocks all writes during the operation, pg_repack allows your application to continue running normally while the reorganization happens in the background. For organizations running read-heavy workloads on time-series data, this is the difference between scheduled maintenance windows and continuous operation.

These three extensions work best together as a unified automation layer. pg_cron schedules the maintenance jobs, pg_partman handles partition lifecycle management, and pg_repack ensures optimal storage utilization. This trio transforms PostgreSQL from a database you actively manage into one that largely manages itself. For additional database infrastructure considerations, check our [graph database comparison](../2026-05-02-dgraph-vs-janusgraph-vs-orientdb-self-hosted-graph-databases-guide/) and [time-series database guide](../2026-05-18-m3db-vs-questdb-vs-timescaledb-self-hosted-time-series-databases/) for related database technology choices.

## FAQ

### Does pg_cron work with PostgreSQL on managed cloud services?

Yes — pg_cron is supported on several managed PostgreSQL services including AWS RDS, Google Cloud SQL, and Supabase. On AWS RDS, you enable it via parameter group settings (`shared_preload_libraries=pg_cron`). Some providers restrict which databases can run cron jobs, so check your provider's documentation.

### What happens if pg_partman fails to create a new partition?

If the partition creation fails (e.g., disk full, permission error), pg_partman logs the error and continues processing other tables. The failed partition will be retried on the next maintenance run. However, inserts to the parent table will fail if no matching partition exists, so it's critical to monitor pg_partman's logs and set up alerting for partition creation failures.

### How long does pg_repack take on a large table?

pg_repack time scales with table size and I/O throughput. A 100 GB table on fast SSD storage might take 2-4 hours. During this time, the table is fully accessible for reads and writes. The final swap (where the rebuilt table replaces the original) takes an exclusive lock for a few seconds. pg_repack also requires free disk space equal to the table size during the rebuild process.

### Can I use pg_partman with existing non-partitioned tables?

pg_partman can convert an existing non-partitioned table to a partitioned one, but this is a complex operation that requires creating a new partitioned parent, migrating data, and renaming tables. The recommended approach is to use `partman.partition_data_time()` or `partman.partition_data_id()` functions, which handle the migration automatically. Always test the migration on a staging environment first.

### How do these extensions affect PostgreSQL replication?

pg_repack generates significant WAL (Write-Ahead Log) traffic during the rebuild, which can impact streaming replication if your replicas are already near their I/O limit. pg_partman's partition creation is DDL operations that replicate normally. pg_cron jobs only execute on the primary server by default — if you want cron jobs on replicas, you need to configure `cron.use_background_workers = on` and accept that jobs will run independently on each replica.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted PostgreSQL Automation Extensions: pg_cron vs pg_partman vs pg_repack",
  "description": "In-depth comparison of three essential PostgreSQL automation extensions: pg_cron for scheduled job execution inside the database, pg_partman for automatic table partitioning and retention management, and pg_repack for online table reorganization without downtime. Includes Docker Compose configurations and production deployment patterns.",
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
