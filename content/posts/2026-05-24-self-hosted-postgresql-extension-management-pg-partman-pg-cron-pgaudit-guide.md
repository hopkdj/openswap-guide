---
title: "Self-Hosted PostgreSQL Extension Management: pg_partman vs pg_cron vs pgAudit"
date: "2026-05-24"
tags: ["postgresql", "database", "extensions", "self-hosted", "database-management"]
draft: false
---

PostgreSQL's extension ecosystem is one of its greatest strengths. Rather than bloating the core database with niche features, PostgreSQL delegates specialized functionality to extensions that can be installed, configured, and managed independently. This modular architecture lets database administrators add partitioning, scheduling, auditing, and dozens of other capabilities without upgrading to a commercial fork.

In this guide, we compare three essential PostgreSQL extensions that solve different operational challenges: **pg_partman** for automated table partitioning, **pg_cron** for in-database job scheduling, and **pgAudit** for detailed audit logging. We'll cover installation, configuration, Docker deployment, and when to choose each extension.

## What Are PostgreSQL Extensions?

PostgreSQL extensions are self-contained packages of SQL objects — functions, types, operators, and more — that extend the database's capabilities. Unlike MySQL plugins or Oracle options, PostgreSQL extensions integrate directly into the database's object namespace, allowing them to hook into the query planner, executor, and transaction system.

Extensions are managed through simple SQL commands:

```sql
-- Install an extension
CREATE EXTENSION pg_partman;
CREATE EXTENSION pg_cron;
CREATE EXTENSION pgaudit;

-- List installed extensions
SELECT * FROM pg_extension;

-- Remove an extension
DROP EXTENSION pg_cron;
```

This SQL-native approach means extensions can be versioned, upgraded, and scripted alongside your database schema, making them ideal for infrastructure-as-code workflows.

## pg_partman: Automated Table Partitioning

[pg_partman](https://github.com/pgpartman/pg_partman) (PostgreSQL Partition Manager) automates the creation and maintenance of table partitions based on time or serial ID ranges. With 2,714+ GitHub stars and active maintenance, it is the most popular partitioning extension for PostgreSQL.

### Why Partition Tables?

Table partitioning splits a large logical table into smaller physical tables (partitions) while maintaining a single query interface. Benefits include:

- **Query performance**: The query planner can skip irrelevant partitions (partition pruning), dramatically reducing I/O for time-range queries.
- **Maintenance efficiency**: Dropping old partitions is an instant `DROP TABLE` operation, far faster than `DELETE FROM` on millions of rows.
- **Vacuum optimization**: Each partition is vacuumed independently, reducing lock contention and improving autovacuum behavior.
- **Storage tiering**: Older partitions can be moved to slower, cheaper storage while keeping recent data on fast SSDs.

### Installation and Setup

Install pg_partman via your OS package manager or from source:

```bash
# Debian/Ubuntu
apt-get install postgresql-16-partman

# From source
git clone https://github.com/pgpartman/pg_partman.git
cd pg_partman
make && make install
```

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: myapp
    volumes:
      - pg_data:/var/lib/postgresql/data
      - ./init-partman.sql:/docker-entrypoint-initdb.d/01-partman.sql
    ports:
      - "5432:5432"

volumes:
  pg_data:
```

The init script:

```sql
-- init-partman.sql
CREATE EXTENSION IF NOT EXISTS pg_partman;

-- Create a parent table with monthly partitions
SELECT partman.create_parent(
    p_parent_table := 'public.events',
    p_control := 'created_at',
    p_type := 'native',
    p_interval := 'monthly',
    p_premake := 3
);
```

### Key Configuration Options

```sql
-- Create a time-based partitioned table
CREATE TABLE public.events (
    id bigint GENERATED ALWAYS AS IDENTITY,
    event_type text NOT NULL,
    payload jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
) PARTITION BY RANGE (created_at);

-- Set up automatic partition management
SELECT partman.create_parent(
    p_parent_table := 'public.events',
    p_control := 'created_at',
    p_type := 'native',
    p_interval := 'monthly',
    p_premake := 3,
    p_start_partition := '2026-01-01'
);

-- Run maintenance via pg_cron (see below) or external scheduler
SELECT partman.run_maintenance('public.events');
```

The `p_premake` parameter controls how many future partitions are pre-created. Setting it to 3 ensures partitions exist for the next three months, preventing insert failures if the maintenance job is delayed.

### Partition Retention and Drop

```sql
-- Automatically drop partitions older than 12 months
UPDATE partman.part_config
SET retention = '12 months',
    retention_keep_table = false
WHERE parent_table = 'public.events';
```

Setting `retention_keep_table = false` ensures old partitions are dropped entirely rather than just detached. For compliance scenarios where data must be preserved, set it to `true` and archive detached tables separately.

## pg_cron: In-Database Job Scheduling

[pg_cron](https://github.com/citusdata/pg_cron) brings cron-style job scheduling directly into PostgreSQL. With 3,790+ GitHub stars and maintenance by Citus Data (now part of Microsoft), it provides reliable in-database scheduling without external dependencies.

### Why Use pg_cron?

External schedulers (system cron, Airflow, Jenkins) require separate infrastructure, authentication, and error handling. pg_cron runs inside PostgreSQL, giving you:

- **Zero external dependencies**: No separate scheduler service to manage.
- **Database context**: Jobs run with full database access, no connection pooling needed.
- **Centralized logging**: Job history stored in `cron.job_run_details`.
- **Transaction safety**: Jobs participate in PostgreSQL's transaction model.

### Installation

```bash
# Debian/Ubuntu
apt-get install postgresql-16-cron

# From source
git clone https://github.com/citusdata/pg_cron.git
cd pg_cron
make && make install
```

Add to `postgresql.conf`:

```ini
shared_preload_libraries = 'pg_cron'
cron.database_name = 'myapp'
```

### Docker Compose with pg_cron

```yaml
version: "3.8"
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: myapp
    volumes:
      - pg_data:/var/lib/postgresql/data
      - ./postgresql.conf:/etc/postgresql/postgresql.conf
    command: ["postgres", "-c", "config_file=/etc/postgresql/postgresql.conf"]
    ports:
      - "5432:5432"

volumes:
  pg_data:
```

### Scheduling Jobs

```sql
-- Create the extension
CREATE EXTENSION pg_cron;

-- Run vacuum every day at 2 AM
SELECT cron.schedule(
    'daily-vacuum',
    '0 2 * * *',
    'VACUUM ANALYZE public.events'
);

-- Run pg_partman maintenance every 15 minutes
SELECT cron.schedule(
    'partman-maintenance',
    '*/15 * * * *',
    'SELECT partman.run_maintenance()'
);

-- Archive old data weekly on Sunday at 3 AM
SELECT cron.schedule(
    'weekly-archive',
    '0 3 * * 0',
    $$
    INSERT INTO events_archive
    SELECT * FROM events
    WHERE created_at < now() - interval '1 year';
    DELETE FROM events
    WHERE created_at < now() - interval '1 year';
    $$
);
```

### Monitoring Job Execution

```sql
-- View all scheduled jobs
SELECT * FROM cron.job;

-- Check recent job execution history
SELECT jobid, run_status, return_message, start_time, end_time
FROM cron.job_run_details
ORDER BY end_time DESC
LIMIT 10;

-- View failed jobs
SELECT jobid, job_name, return_message, start_time
FROM cron.job_run_details
WHERE run_status != 'succeeded'
ORDER BY start_time DESC;
```

## pgAudit: Detailed Audit Logging

[pgAudit](https://github.com/pgaudit/pgaudit) provides detailed session and object-level audit logging for PostgreSQL. With 1,642+ GitHub stars and active development by the PostgreSQL community, it is the standard solution for compliance-driven audit requirements.

### Why Audit Database Access?

Regulatory frameworks (SOC 2, HIPAA, PCI DSS, GDPR) require detailed records of who accessed what data and when. PostgreSQL's default logging only captures connections and errors — pgAudit fills the gap by logging:

- **DDL operations**: CREATE, ALTER, DROP statements
- **DML operations**: INSERT, UPDATE, DELETE
- **SELECT queries**: Configurable at table or column level
- **Role changes**: GRANT, REVOKE, CREATE ROLE
- **Function calls**: EXECUTE statements

### Installation

```bash
# Debian/Ubuntu
apt-get install postgresql-16-audit

# From source
git clone https://github.com/pgaudit/pgaudit.git
cd pgaudit
make && make install
```

Add to `postgresql.conf`:

```ini
shared_preload_libraries = 'pgaudit'
pgaudit.log = 'write,ddl'
pgaudit.log_relation = on
pgaudit.log_level = log
```

### Docker Compose with pgAudit

```yaml
version: "3.8"
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: myapp
    volumes:
      - pg_data:/var/lib/postgresql/data
      - ./postgresql.conf:/etc/postgresql/postgresql.conf
    command: ["postgres", "-c", "config_file=/etc/postgresql/postgresql.conf"]
    ports:
      - "5432:5432"

volumes:
  pg_data:
```

### Audit Configuration

```sql
-- Create the extension
CREATE EXTENSION pgaudit;

-- Set audit level for the session
SET pgaudit.log = 'read,write,ddl';

-- Audit all SELECT, INSERT, UPDATE, DELETE on specific tables
ALTER TABLE public.users SET (pgaudit.log = 'read,write');

-- Role-based auditing
ALTER ROLE auditor SET pgaudit.log = 'all';
```

### Audit Log Output

pgAudit writes to PostgreSQL's standard log output with structured fields:

```
LOG:  AUDIT: SESSION,1,1,READ,SELECT,TABLE,public.users,"SELECT * FROM users WHERE id = 42",<not logged>
LOG:  AUDIT: SESSION,1,1,DDL,CREATE,TABLE,public.audit_log,"CREATE TABLE audit_log (id int)",<not logged>
```

For centralized log management, pipe PostgreSQL logs to [Grafana Loki](../2026-05-24-self-hosted-log-collector-agents-grafana-loki-promtail-vs-fluent-bit-vs-vector-guide/) or [Fluent Bit](../2026-05-09-self-hosted-log-forwarding-fluent-bit-vector-otel-collector/).

## Comparison Table

| Feature | pg_partman | pg_cron | pgAudit |
|---------|-----------|---------|---------|
| **Purpose** | Table partitioning | Job scheduling | Audit logging |
| **GitHub Stars** | 2,714+ | 3,790+ | 1,642+ |
| **Installation** | `CREATE EXTENSION` | `CREATE EXTENSION` | `CREATE EXTENSION` |
| **Requires shared_preload_libraries** | No | Yes | Yes |
| **Maintenance Required** | Regular run_maintenance() calls | None (background worker) | None (background worker) |
| **Docker Support** | Via Postgres image | Via Postgres image | Via Postgres image |
| **Compliance Use** | Data retention policies | Scheduled compliance jobs | Audit trail generation |
| **Performance Impact** | Minimal (partition pruning helps) | Low (background worker) | Moderate (extra logging I/O) |
| **Best For** | Time-series data, log tables | Automated maintenance, archiving | SOC 2, HIPAA, PCI DSS |

## Choosing the Right Extension

These three extensions serve fundamentally different purposes and are often deployed together:

- **Use pg_partman** when managing tables with millions of rows that grow over time (event logs, metrics, sensor data). Partition pruning alone can improve query performance by 10-100x for time-range queries.
- **Use pg_cron** when you need reliable in-database scheduling for maintenance tasks, data archiving, or report generation. It eliminates the need for external cron infrastructure.
- **Use pgAudit** when compliance requirements demand detailed records of database access patterns. It provides session-level and object-level logging that default PostgreSQL logging cannot match.

A typical production setup combines all three: pg_partman manages partitioned tables, pg_cron schedules partition maintenance and vacuum operations, and pgAudit logs all access for compliance reporting.

## Why Self-Host PostgreSQL Extensions?

Managing PostgreSQL extensions on self-hosted infrastructure gives you complete control over your data lifecycle, compliance posture, and operational costs. Unlike managed database services that limit extension availability to a curated list, self-hosted PostgreSQL lets you install any extension from the PostgreSQL Extension Network (PGXN) or compile from source.

**Data sovereignty**: Extensions like pgAudit generate audit trails that must remain within your infrastructure for compliance. Cloud-managed databases may route audit logs through third-party services, creating compliance gaps for regulated industries.

**Cost control**: Managed PostgreSQL services charge premiums for storage, compute, and audit log retention. Self-hosting with pg_partman's partition-based retention and pgAudit's configurable logging levels lets you optimize costs by moving old data to cheaper storage tiers.

**No vendor lock-in**: PostgreSQL extensions are open-source and standardized. Moving from a self-hosted deployment to a managed service (or vice versa) requires no schema changes — the same `CREATE EXTENSION` commands work everywhere.

For comprehensive PostgreSQL administration tools, see our [PostgreSQL management UI comparison](../2026-05-11-self-hosted-postgresql-management-ui-pgadmin-pgweb-temboard/). If you need high availability, our [PostgreSQL HA on Kubernetes guide](../2026-05-21-self-hosted-postgresql-ha-kubernetes-stolon-spilo-patroni-guide/) covers Stolon, Spilo, and Patroni. For backup strategies, check our [PostgreSQL backup tools comparison](../pgbackrest-vs-barman-vs-wal-g-self-hosted-postgresql-backup-guide-2026/).

## FAQ

### What is the difference between pg_partman and native PostgreSQL partitioning?

PostgreSQL 10+ includes native declarative partitioning. pg_partman is a management layer that automates partition creation, maintenance, and retention. Without pg_partman, you must manually create future partitions and drop old ones. pg_partman handles this automatically via its `run_maintenance()` function, which can be scheduled with pg_cron or an external scheduler.

### Does pg_cron replace system cron?

Not entirely. pg_cron is designed for database-specific tasks — vacuum, archiving, maintenance procedures. System cron remains necessary for OS-level tasks (backups, log rotation, system updates). pg_cron's advantage is that it runs within the database context, eliminating connection overhead and authentication complexity for database jobs.

### Can pgAudit log the actual SQL query text?

Yes. By default, pgAudit logs the statement text. For parameterized queries (prepared statements), the actual parameter values are not logged unless `pgaudit.log_parameter = on` is set in `postgresql.conf`. Note that logging parameter values may expose sensitive data in logs, so this setting should be used carefully in production environments.

### How much performance overhead does pgAudit add?

pgAudit's overhead depends on the audit scope. Session-level auditing (logging all commands) adds approximately 5-15% overhead on write-heavy workloads. Object-level auditing (auditing specific tables) adds minimal overhead since only targeted operations are logged. For read-heavy workloads with `pgaudit.log = 'ddl,write'` (excluding reads), the overhead is typically under 3%.

### Can I use pg_partman with pg_cron together?

Yes, this is the recommended pattern. pg_cron can schedule `partman.run_maintenance()` at regular intervals to ensure new partitions are created and old ones are dropped automatically. A typical setup runs maintenance every 15 minutes for high-volume tables and daily for lower-volume ones.

### How do I upgrade a PostgreSQL extension without data loss?

PostgreSQL extensions support version upgrades via `ALTER EXTENSION extension_name UPDATE`. For pg_partman, pg_cron, and pgAudit, the upgrade process is:

```sql
ALTER EXTENSION pg_partman UPDATE;
ALTER EXTENSION pg_cron UPDATE;
ALTER EXTENSION pgaudit UPDATE;
```

Always test extension upgrades in a staging environment first. For extensions that require `shared_preload_libraries` (pg_cron, pgAudit), a PostgreSQL restart is needed after updating the extension files on disk.

### Is pgAudit sufficient for HIPAA compliance?

pgAudit provides the technical audit logging capability required by HIPAA, but compliance involves more than logging. You must also implement access controls, encryption at rest and in transit, backup procedures, and breach notification processes. pgAudit is one component of a broader compliance strategy.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted PostgreSQL Extension Management: pg_partman vs pg_cron vs pgAudit",
  "description": "Compare three essential PostgreSQL extensions: pg_partman for partitioning, pg_cron for scheduling, and pgAudit for audit logging. Includes Docker deployment, configuration guides, and compliance considerations.",
  "datePublished": "2026-05-24",
  "dateModified": "2026-05-24",
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
