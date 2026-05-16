---
title: "Self-Hosted PostgreSQL Admin Tools: pgCenter vs pg_stat_monitor vs pg_stat_statements (2026-05-17)"
date: "2026-05-17"
tags: ["postgresql", "database-admin", "monitoring", "performance", "self-hosted"]
draft: false
---

PostgreSQL ships with powerful built-in statistics views, but navigating raw `pg_stat_*` tables in production is cumbersome. Specialized admin tools bridge this gap by providing real-time query analysis, connection monitoring, and performance diagnostics. This guide compares three distinct approaches: **pgCenter** (terminal-based admin dashboard), **pg_stat_monitor** (enhanced query statistics extension from Percona), and **pg_stat_statements** (PostgreSQL's built-in query performance tracker). Each serves a different role in the PostgreSQL observability stack.

## What Each Tool Does

| Feature | pgCenter | pg_stat_monitor | pg_stat_statements |
|---|---|---|---|
| **Type** | CLI admin dashboard | PostgreSQL extension | PostgreSQL extension (built-in) |
| **Interface** | Terminal (ncurses) | SQL views | SQL views |
| **Real-time Monitoring** | Yes (live refresh) | No (accumulated stats) | No (accumulated stats) |
| **Query Profiling** | Yes (live) | Yes (with histograms) | Yes (basic) |
| **Connection Tracking** | Yes (per-connection detail) | Partial | No |
| **Lock Analysis** | Yes (blocking queries) | No | No |
| **Replication Monitoring** | Yes (lag, WAL stats) | No | No |
| **Table/Index Stats** | Yes (live) | No | No |
| **Query Histograms** | No | Yes (bucketed response times) | No |
| **Client IP Tracking** | Yes | Yes | No |
| **Query Plans** | No | No | No |
| **Installation** | Standalone binary | `CREATE EXTENSION` | `CREATE EXTENSION` (contrib) |
| **Overhead** | None (reads system catalogs) | Low (query parsing) | Low (query hashing) |
| **PostgreSQL Versions** | 12+ | 13+ | 9.2+ |
| **GitHub Stars** | 1,600+ | 570+ | Built into PostgreSQL |

## pgCenter: Terminal Admin Dashboard

pgCenter is a real-time administrative tool that provides an ncurses-based dashboard for monitoring PostgreSQL server health. Unlike extensions that modify query execution, pgCenter reads existing system catalogs and statistics views — meaning zero overhead on your production workload.

### What You Can Monitor

- **Activity** — Live query list with duration, state, and blocking information
- **Tables** — I/O statistics, row operations, and index usage per table
- **Indexes** — Scan counts, tuple reads, and bloat estimation
- **Replication** — Streaming replication lag, WAL generation rate, and standby status
- **Configuration** — Runtime parameter values with diff detection on reload
- **Filespaces** — Table size, index size, and toast table usage

### Docker Compose Setup

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_PASSWORD: "postgres"
      POSTGRES_DB: "appdb"
    ports:
      - "5432:5432"
    volumes:
      - pg-data:/var/lib/postgresql/data

  pgcenter:
    image: lesovsky/pgcenter:latest
    command: pgcenter top -d postgresql://postgres:postgres@postgres:5432/appdb
    depends_on:
      - postgres
    stdin_open: true
    tty: true

volumes:
  pg-data:
```

### Using pgCenter in Production

```bash
# Connect to a remote server
pgcenter top -h db.example.com -p 5432 -U postgres -d appdb

# Record statistics to a file for later analysis
pgcenter record -h localhost -d appdb -f /tmp/pgcenter-record.csv

# View configuration changes
pgcenter config -h localhost -d appdb
```

## pg_stat_monitor: Enhanced Query Statistics

pg_stat_monitor is a Percona-developed PostgreSQL extension that extends the capabilities of pg_stat_statements with additional metrics. It captures query execution statistics grouped into time buckets, enabling trend analysis and performance regression detection.

### Key Enhancements Over pg_stat_statements

- **Time-bucketed statistics** — Stats are grouped into configurable time windows (default: 1 minute), enabling trend analysis
- **Query histograms** — Response time distribution across configurable buckets
- **Client information** — Application name, database user, and client IP address per query
- **Query relationships** — Parent-child query tracking for stored procedures
- **Plans and relations** — Tables and indexes accessed by each query pattern
- **Top query tracking** — Identifies the most resource-intensive queries per time bucket

### Installation and Configuration

```sql
-- Add to postgresql.conf
shared_preload_libraries = 'pg_stat_monitor'

-- Restart PostgreSQL, then create the extension
CREATE EXTENSION pg_stat_monitor;

-- Configure bucket size and count
ALTER SYSTEM SET pg_stat_monitor.pgsm_bucket_time = 60;  -- 1-minute buckets
ALTER SYSTEM SET pg_stat_monitor.pgsm_max_buckets = 10;  -- Keep 10 buckets
ALTER SYSTEM SET pg_stat_monitor.pgsm_query_max_len = 4096;
SELECT pg_reload_conf();
```

### Querying Performance Data

```sql
-- Top 10 queries by total execution time in the current bucket
SELECT query, calls, total_exec_time, mean_exec_time,
       min_exec_time, max_exec_time, stddev_exec_time
FROM pg_stat_monitor
ORDER BY total_exec_time DESC
LIMIT 10;

-- Query response time histogram
SELECT bucket, userid, datname, query,
       resp_calls  -- Array of call counts per response time bucket
FROM pg_stat_monitor
WHERE query LIKE 'SELECT%';

-- Queries with client information
SELECT query, calls, client_ip, application_name,
       total_exec_time, mean_exec_time
FROM pg_stat_monitor
WHERE client_ip IS NOT NULL
ORDER BY calls DESC
LIMIT 20;
```

### Docker Compose with pg_stat_monitor

```yaml
version: "3.8"

services:
  postgres-pgsm:
    image: percona/postgresql:16
    environment:
      POSTGRES_PASSWORD: "postgres"
    ports:
      - "5432:5432"
    command: >
      postgres
      -c shared_preload_libraries=pg_stat_monitor
      -c pg_stat_monitor.pgsm_enable=on
      -c pg_stat_monitor.pgsm_bucket_time=60
    volumes:
      - pgsm-data:/var/lib/postgresql/data

volumes:
  pgsm-data:
```

## pg_stat_statements: Built-In Query Tracking

pg_stat_statements is the most widely used PostgreSQL performance extension, included in the `contrib` package. It tracks execution statistics for all SQL statements executed by the server, providing a foundation for query performance analysis.

### What It Tracks

- Call count and total/mean/min/max execution time
- Rows returned and shared/local/temp block I/O statistics
- Temporary file usage and WAL generation per query pattern
- Query plan identification via normalized query fingerprinting

### Configuration

```sql
-- Add to postgresql.conf
shared_preload_libraries = 'pg_stat_statements'

-- Tunable parameters
ALTER SYSTEM SET pg_stat_statements.track = 'all';  -- Track all statements including inside functions
ALTER SYSTEM SET pg_stat_statements.max = 10000;     -- Max distinct query patterns tracked
ALTER SYSTEM SET pg_stat_statements.track_utility = 'on';
SELECT pg_reload_conf();

-- Create extension
CREATE EXTENSION pg_stat_statements;
```

### Essential Queries

```sql
-- Top 10 slowest queries by mean execution time
SELECT query, calls, total_exec_time, mean_exec_time,
       rows, shared_blks_hit, shared_blks_read
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Queries with highest I/O
SELECT query, calls,
       shared_blks_read + shared_blks_written AS total_io,
       temp_blks_read + temp_blks_written AS temp_io
FROM pg_stat_statements
ORDER BY total_io DESC
LIMIT 10;

-- Reset statistics (after analyzing)
SELECT pg_stat_statements_reset();
```

## Performance Overhead Comparison

| Metric | pgCenter | pg_stat_monitor | pg_stat_statements |
|---|---|---|---|
| **CPU overhead** | None (read-only) | ~1-3% | ~1-2% |
| **Memory overhead** | None | 50-200 MB (shared memory) | 20-100 MB (shared memory) |
| **I/O overhead** | None | None | None |
| **Query latency impact** | None | < 1ms per query | < 0.5ms per query |

## Why Self-Host PostgreSQL Admin Tools?

Running your own PostgreSQL admin tools on dedicated infrastructure eliminates the per-database licensing fees charged by enterprise APM vendors. Tools like pgCenter provide the same real-time diagnostics that Datadog or New Relic offer for database monitoring, but without per-host pricing or data egress charges. For teams managing dozens of PostgreSQL instances, self-hosted admin tools pay for themselves within months.

Self-hosted PostgreSQL tooling also integrates seamlessly with existing infrastructure monitoring. Combine pgCenter with Prometheus node exporters, Grafana dashboards, and centralized log aggregation for comprehensive database observability. The zero-overhead design of pgCenter means it can run continuously on production servers without affecting query latency.

Running PostgreSQL admin tools on your own infrastructure means query performance data never leaves your network. This is essential for compliance with data protection regulations that restrict where performance telemetry can be stored. Self-hosted tools also avoid the per-database or per-query pricing models of cloud-based monitoring services.

For teams managing multiple PostgreSQL instances, combining pgCenter for real-time diagnostics with pg_stat_monitor for historical trend analysis provides comprehensive coverage without the cost of enterprise APM platforms. For related reading, see our [PostgreSQL performance dashboards guide](../2026-05-13-self-hosted-postgresql-performance-dashboards-pghero-pgwatch2-pg-stat-monitor/) and [database query profiling tools](../2026-04-23-self-hosted-database-query-profiling-optimization-tools-guide/). If you need connection pooling alongside monitoring, our [connection pooler comparison](../pgbouncer-vs-proxysql-vs-odyssey-self-hosted-database-connection-pooling-guide-2026/) covers PgBouncer, ProxySQL, and Odyssey.

## FAQ

### Should I use pg_stat_statements or pg_stat_monitor?
Start with pg_stat_statements — it is built into PostgreSQL, has zero external dependencies, and covers the most common query analysis needs. Upgrade to pg_stat_monitor if you need time-bucketed statistics for trend analysis, query response time histograms, or client IP tracking. pg_stat_monitor is a superset of pg_stat_statements functionality.

### Does pgCenter require installing a PostgreSQL extension?
No. pgCenter reads from PostgreSQL's built-in statistics views (`pg_stat_activity`, `pg_stat_user_tables`, etc.) and system catalogs. It requires no extensions, no shared preload libraries, and no server restart. The only requirement is a database user with sufficient privileges to read these views.

### Can I use pg_stat_monitor alongside pg_stat_statements?
Yes, but not simultaneously in the same `shared_preload_libraries` configuration. pg_stat_monitor provides all the functionality of pg_stat_statements plus additional metrics, so you should use one or the other. Using both would create redundant tracking and unnecessary overhead.

### How do I identify blocking queries with pgCenter?
In pgCenter's activity view (accessed via `pgcenter top`), blocked queries are highlighted with their blocking PID displayed. The tool shows lock type, wait duration, and the blocking query text. This makes it easy to identify long-running transactions that are preventing other queries from proceeding.

### What is the recommended shared memory allocation for pg_stat_monitor?
Percona recommends starting with `pg_stat_monitor.pgsm_query_shared_buffers = 100` (100 MB) for small databases and increasing to 500 MB or more for high-traffic production systems. Monitor the `pg_stat_monitor` view for query truncation warnings, which indicate the buffer is too small.

### How often should I reset pg_stat_statements statistics?
Reset statistics after major deployments or configuration changes to establish a fresh baseline. In continuous monitoring setups, most teams reset weekly or monthly. Use `SELECT pg_stat_statements_reset()` to clear accumulated data. Note that resetting loses historical data, so export important metrics before resetting.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted PostgreSQL Admin Tools: pgCenter vs pg_stat_monitor vs pg_stat_statements",
  "description": "Compare pgCenter, pg_stat_monitor, and pg_stat_statements for PostgreSQL query analysis and administration. Docker configs and performance guides.",
  "datePublished": "2026-05-17",
  "dateModified": "2026-05-17",
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
