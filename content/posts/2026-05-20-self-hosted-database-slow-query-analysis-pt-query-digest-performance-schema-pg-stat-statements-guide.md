---
title: "Self-Hosted Database Slow Query Analysis: pt-query-digest vs MySQL Performance Schema vs pg_stat_statements"
date: "2026-05-20"
tags: ["database", "mysql", "postgresql", "performance", "monitoring"]
draft: false
---

Slow database queries are the most common cause of application performance degradation. Identifying which queries are slow, how often they run, and what resources they consume is critical for database administrators and DevOps engineers. While most database engines log slow queries, raw slow query logs are difficult to analyze at scale.

This guide compares three approaches to database slow query analysis: **Percona Toolkit's pt-query-digest** for MySQL/MariaDB, **MySQL Performance Schema** for real-time query profiling, and **PostgreSQL's pg_stat_statements** extension for Postgres query statistics.

## Understanding Slow Query Analysis

Database slow query analysis involves capturing queries that exceed a defined time threshold, aggregating their execution patterns, and identifying the most resource-intensive operations. Effective analysis reveals:

- **Top offenders**: The queries consuming the most CPU, I/O, or execution time
- **Query fingerprints**: Grouping similar queries with different parameter values
- **Execution patterns**: How often a query runs, its variance in response time
- **Index usage**: Whether queries are using indexes effectively or performing full table scans
- **Lock contention**: Queries blocked by other transactions

## Tool Comparison Overview

| Feature | pt-query-digest | MySQL Performance Schema | pg_stat_statements |
|---------|----------------|-------------------------|-------------------|
| **Database** | MySQL/MariaDB | MySQL 5.6+ | PostgreSQL 9.2+ |
| **Language** | Perl | C (built-in) | C (extension) |
| **Collection Method** | Parse slow log / processlist | Instrumentation API | Extension module |
| **Overhead** | None (offline analysis) | 5-15% CPU | 1-5% CPU |
| **Query Fingerprinting** | Yes (automatic) | Yes (digests) | Yes (normalized) |
| **Historical Data** | Log-based | In-memory (volatile) | Persistent (shared_buffers) |
| **Real-time Monitoring** | No | Yes | Yes |
| **Aggregation** | Time-window based | Continuous | Continuous |
| **Granularity** | Per-query, per-user | Per-query, per-thread | Per-query, per-user, per-database |
| **Setup Complexity** | Low (CLI tool) | Medium (config change) | Low (extension) |

## pt-query-digest (Percona Toolkit)

**pt-query-digest** is the most widely used MySQL slow query analysis tool. It parses MySQL slow query logs, general logs, or processlist output and produces detailed reports ranking queries by total execution time, query count, lock time, and rows examined.

### Key Features

- **Automatic fingerprinting**: Normalizes queries with different parameter values into a single fingerprint
- **Multiple input sources**: Slow log, general log, processlist, tcpdump
- **Flexible filtering**: Filter by host, user, database, fingerprint, or time range
- **Detailed reports**: Per-query statistics including execution time distribution, lock wait times, rows examined
- **Trend analysis**: Compare slow query logs from different time periods
- **Review database**: Store query analysis results in a MySQL table for historical tracking

### Installation

```bash
# Install from Percona repository (Debian/Ubuntu)
apt-get update && apt-get install -y percona-toolkit

# Install from Percona repository (RHEL/CentOS)
yum install -y percona-toolkit

# Or install via CPAN
cpanm DBD::mysql
cpanm Term::ReadKey
```

### Usage Examples

Analyze the MySQL slow query log:

```bash
pt-query-digest /var/log/mysql/slow.log
```

Filter by a specific database and show the top 10 queries:

```bash
pt-query-digest --filter '$event->{db} eq "production"'   --limit 10   /var/log/mysql/slow.log > slow_query_report.txt
```

Compare two time periods to identify regressions:

```bash
pt-query-digest --since "2026-01-01" --until "2026-01-07"   /var/log/mysql/slow.log > week1_report.txt

pt-query-digest --since "2026-01-08" --until "2026-01-14"   /var/log/mysql/slow.log > week2_report.txt
```

Review mode — store analysis in a database for historical tracking:

```bash
pt-query-digest --review h=localhost,D=percona,t=query_review   --no-report /var/log/mysql/slow.log
```

### Docker Compose Setup

```yaml
version: "3.8"
services:
  mysql:
    image: percona:8.0
    container_name: mysql-slow
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
    volumes:
      - mysql_data:/var/lib/mysql
      - ./slow.cnf:/etc/mysql/conf.d/slow.cnf
      - ./slow.log:/var/log/mysql/slow.log
    ports:
      - "3306:3306"

  percona-toolkit:
    image: percona/percona-toolkit:latest
    container_name: pt-query-digest
    volumes:
      - ./slow.log:/var/log/mysql/slow.log:ro
      - ./reports:/reports
    command: >
      sh -c "pt-query-digest /var/log/mysql/slow.log > /reports/slow_analysis.txt"
    depends_on:
      - mysql

volumes:
  mysql_data:
```

Slow query log configuration (`slow.cnf`):

```ini
[mysqld]
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 1
log_queries_not_using_indexes = 1
```

## MySQL Performance Schema

**MySQL Performance Schema** is a built-in instrumentation framework that monitors server execution in real-time. Unlike pt-query-digest which analyzes log files post-facto, Performance Schema captures query statistics as they happen with minimal overhead.

### Key Features

- **Real-time data**: Query statistics are available immediately, no log parsing needed
- **Low overhead**: Configurable instrumentation with minimal CPU impact
- **Comprehensive metrics**: Wait events, stage events, statement events, memory usage
- **Historical tables**: Configurable retention in memory tables
- **Built-in**: No external tools required — ships with MySQL 5.6+

### Configuration

Enable Performance Schema and statement instrumentation:

```ini
[mysqld]
performance_schema = ON
performance-schema-instrument = 'statement/%=ON'
performance-schema-consumer-events-statements-history-long = ON
performance-schema-consumer-events-statements-summary-by-digest = ON
```

### Querying Performance Schema

Get the top 10 queries by total execution time:

```sql
SELECT
    DIGEST_TEXT AS query,
    COUNT_STAR AS executions,
    ROUND(SUM_TIMER_WAIT / 1000000000000, 2) AS total_time_sec,
    ROUND(AVG_TIMER_WAIT / 1000000000000, 6) AS avg_time_sec,
    ROUND(MAX_TIMER_WAIT / 1000000000000, 6) AS max_time_sec,
    SUM_ROWS_EXAMINED AS rows_examined,
    SUM_ROWS_SENT AS rows_sent
FROM performance_schema.events_statements_summary_by_digest
ORDER BY SUM_TIMER_WAIT DESC
LIMIT 10;
```

Reset statistics to start a fresh measurement period:

```sql
UPDATE performance_schema.events_statements_summary_by_digest
SET COUNT_STAR = 0;
```

### Docker Compose Setup

```yaml
version: "3.8"
services:
  mysql-pfs:
    image: mysql:8.0
    container_name: mysql-perf-schema
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
    volumes:
      - ./pfs.cnf:/etc/mysql/conf.d/pfs.cnf
    ports:
      - "3307:3306"
    command: >
      mysqld
      --performance-schema=ON
      --performance-schema-consumer-events-statements-history-long=ON
```

## pg_stat_statements (PostgreSQL)

**pg_stat_statements** is a PostgreSQL extension that tracks execution statistics of all SQL statements executed by a server. It is the PostgreSQL equivalent of MySQL's Performance Schema digest tables and is the standard tool for Postgres query analysis.

### Key Features

- **Persistent storage**: Statistics survive server restarts (stored in shared memory + flat files)
- **Normalized queries**: Parameterized queries are grouped by their normalized form
- **Comprehensive stats**: Calls, total time, min/max/mean time, rows, shared/local/temp buffers
- **Low overhead**: Typically 1-5% CPU overhead
- **Built into PostgreSQL**: Ships with PostgreSQL, just needs to be enabled

### Configuration

Enable the extension in `postgresql.conf`:

```ini
shared_preload_libraries = 'pg_stat_statements'
pg_stat_statements.track = all
pg_stat_statements.max = 10000
pg_stat_statements.track_utility = on
```

Create the extension in your database:

```sql
CREATE EXTENSION pg_stat_statements;
```

### Querying pg_stat_statements

Get the top 10 queries by total execution time:

```sql
SELECT
    query,
    calls,
    ROUND(total_exec_time::numeric, 2) AS total_time_ms,
    ROUND(mean_exec_time::numeric, 2) AS mean_time_ms,
    ROUND(max_exec_time::numeric, 2) AS max_time_ms,
    rows,
    ROUND(100.0 * shared_blks_hit / NULLIF(shared_blks_hit + shared_blks_read, 0), 2) AS hit_percent
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;
```

Reset statistics:

```sql
SELECT pg_stat_statements_reset();
```

Find queries with the lowest cache hit ratio (potential index issues):

```sql
SELECT
    query,
    calls,
    ROUND(mean_exec_time::numeric, 2) AS avg_ms,
    shared_blks_hit,
    shared_blks_read,
    ROUND(100.0 * shared_blks_hit / NULLIF(shared_blks_hit + shared_blks_read, 0), 2) AS hit_pct
FROM pg_stat_statements
WHERE shared_blks_hit + shared_blks_read > 0
ORDER BY (shared_blks_hit::float / NULLIF(shared_blks_hit + shared_blks_read, 0)) ASC
LIMIT 10;
```

### Docker Compose Setup

```yaml
version: "3.8"
services:
  postgres:
    image: postgres:16
    container_name: postgres-pgss
    environment:
      POSTGRES_PASSWORD: postgres
    volumes:
      - pg_data:/var/lib/postgresql/data
      - ./postgresql.conf:/etc/postgresql/postgresql.conf
    ports:
      - "5432:5432"
    command: >
      postgres
      -c shared_preload_libraries=pg_stat_statements
      -c pg_stat_statements.track=all
      -c pg_stat_statements.max=10000

volumes:
  pg_data:
```

## Why Self-Host Database Query Analysis?

Database performance issues are often the bottleneck in application response times. Without proper slow query analysis, problems go undetected until they cause outages or severe degradation. Self-hosted query analysis tools give you full visibility into database performance without sending query data to third-party services.

### Proactive Performance Management

Continuous slow query monitoring identifies performance regressions before they impact users. When a new deployment introduces an inefficient query, tools like pg_stat_statements or Performance Schema flag it within minutes — not hours or days after users start complaining.

### Cost Optimization

Inefficient queries consume CPU, memory, and I/O resources. On cloud databases (RDS, Cloud SQL), this translates directly to higher costs. Identifying and optimizing the top 5 most expensive queries can reduce database CPU utilization by 30-50%, potentially allowing you to downsize your database instance.

### Compliance and Auditing

For regulated industries, tracking query patterns and execution times provides an audit trail of database activity. pt-query-digest's review mode stores historical analysis in a database, creating a permanent record of query performance over time.

For database monitoring, see our [database monitoring tools comparison](../2026-04-18-pgwatch2-vs-percona-pmm-vs-pgmonitor-self-hosted-database-monitoring-guide/) and [PostgreSQL backup guide](../pgbackrest-vs-barman-vs-wal-g-self-hosted-postgresql-backup-guide-2026/). For replication strategies, check our [data replication guide](../2026-04-26-symmetricds-vs-debezium-vs-canal-self-hosted-data-replication-guide-2026/).

## Choosing the Right Query Analysis Tool

**Choose pt-query-digest** if you're running MySQL/MariaDB and want the most comprehensive offline analysis. Its ability to parse logs, processlist, and tcpdump output, combined with fingerprinting and review mode, makes it the gold standard for MySQL query analysis.

**Choose MySQL Performance Schema** if you need real-time query monitoring without external tools. Built into MySQL, it provides continuous statistics with configurable overhead. It's ideal for production environments where log parsing latency is unacceptable.

**Choose pg_stat_statements** if you're running PostgreSQL. It's the standard query analysis extension for Postgres, with persistent statistics, low overhead, and comprehensive metrics. Every production PostgreSQL server should have it enabled.

## FAQ

### Does pt-query-digest work with PostgreSQL?
No. pt-query-digest is designed specifically for MySQL/MariaDB slow query logs. For PostgreSQL, use pg_stat_statements or tools like pgBadger which parse PostgreSQL log files.

### How much overhead does Performance Schema add?
Performance Schema typically adds 5-15% CPU overhead when fully enabled. You can reduce this by selectively enabling only the instruments you need. In MySQL 8.0, the overhead is significantly lower than in earlier versions.

### Do pg_stat_statements statistics persist across restarts?
Yes. pg_stat_statements stores statistics in shared memory and periodically flushes them to a flat file on disk. After a clean shutdown, statistics are restored on restart. However, a crash will lose statistics since the last flush.

### Can I analyze slow queries without enabling slow query logging?
pt-query-digest can analyze the processlist output in real-time without slow query logging: `pt-query-digest --processlist h=localhost,u=root,p=password`. For Performance Schema and pg_stat_statements, no slow log is needed — they instrument queries directly.

### How do I identify missing indexes from slow query analysis?
Look for queries with high `rows_examined` relative to `rows_sent`. If a query examines 1 million rows but returns only 10, it likely needs an index. Both Performance Schema and pg_stat_statements provide rows examined/sent metrics.

### Can I automate slow query alerting?
Yes. For pt-query-digest, parse its output and alert when top queries exceed thresholds. For Performance Schema and pg_stat_statements, query their tables on a schedule (via cron or your monitoring system) and alert on regressions. Prometheus exporters exist for pg_stat_statements metrics.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Database Slow Query Analysis: pt-query-digest vs MySQL Performance Schema vs pg_stat_statements",
  "description": "Compare three database query analysis approaches — pt-query-digest, MySQL Performance Schema, and pg_stat_statements — with Docker Compose configs and real query examples.",
  "datePublished": "2026-05-20",
  "dateModified": "2026-05-20",
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
