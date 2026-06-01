---
title: "Self-Hosted PostgreSQL Log Analysis: pgBadger vs pg_stat_statements vs CSV Log Analysis"
date: "2026-06-02"
tags: ["postgresql", "database", "logging", "monitoring", "performance", "devops"]
draft: false
---

## Introduction

PostgreSQL generates a wealth of diagnostic data through its logging system — query execution times, error messages, connection events, checkpoint statistics, and autovacuum activity. However, raw PostgreSQL logs are verbose plaintext files that can reach gigabytes per day on busy systems. Making sense of this data requires specialized analysis tools.

In this guide, we compare three approaches to PostgreSQL log analysis: **pgBadger**, the industry-standard log analyzer that produces rich HTML reports; **pg_stat_statements**, PostgreSQL's built-in query performance aggregator; and **direct CSV log analysis** using shell scripts and SQL for custom diagnostics. Each approach serves different use cases — from executive-friendly dashboards to deep forensic investigations.

## Comparison Table

| Feature | pgBadger | pg_stat_statements | CSV Log Analysis |
|---------|----------|-------------------|-----------------|
| **Purpose** | HTML log reports & dashboards | Query performance aggregation | Custom log investigation |
| **Type** | Standalone Perl tool | PostgreSQL extension | Shell + SQL scripts |
| **Stars** | 4,023+ | Built-in (core PG) | N/A (custom) |
| **Last Updated** | June 2026 | Active (PG 17) | N/A |
| **Output Format** | HTML, JSON, TSV | SQL queries | Custom (CSV, JSON) |
| **Disk Overhead** | None (processes existing logs) | ~1-5% shared_buffers | Minimal |
| **Setup Complexity** | Low (single binary) | Very low (CREATE EXTENSION) | Medium (writing scripts) |
| **Granularity** | Per-query, per-session, per-database | Aggregated by query fingerprint | Fully customizable |
| **Best For** | Daily/weekly reports, trend analysis | Real-time query monitoring | Forensic debugging, custom metrics |

## pgBadger: Rich Log Analysis Reports

[pgBadger](https://github.com/darold/pgbadger) is the gold standard for PostgreSQL log analysis. It parses PostgreSQL log files and generates detailed HTML reports covering query performance, connection statistics, error rates, checkpoint activity, vacuum operations, and temporary file usage. Its single-binary design (Perl) makes it trivial to deploy.

### Installation

```bash
# Install via package manager
apt-get install pgbadger

# Or download the latest release
wget https://github.com/darold/pgbadger/releases/latest/download/pgbadger
chmod +x pgbadger
```

### PostgreSQL Logging Configuration

pgBadger requires PostgreSQL to log in a compatible format. Add these settings to `postgresql.conf`:

```ini
# Log format for pgBadger
log_destination = 'stderr'
logging_collector = on
log_directory = 'pg_log'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_line_prefix = '%t [%p]: user=%u,db=%d,app=%a,client=%h '

# Essential log settings for analysis
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on
log_temp_files = 0
log_autovacuum_min_duration = 0
log_min_duration_statement = 1000  # Log queries slower than 1s

# For per-query analysis (adjust based on traffic)
log_statement = 'none'
log_duration = off
```

### Docker Compose Setup

```yaml
version: "3.8"
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: securepass
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./pg_log:/var/log/postgresql
      - ./pgbadger_reports:/reports
    command: >
      postgres -c log_destination=stderr 
               -c logging_collector=on
               -c log_directory=/var/log/postgresql
               -c log_min_duration_statement=1000
               -c log_checkpoints=on
               -c log_connections=on
               -c log_disconnections=on
               -c log_lock_waits=on
               -c log_temp_files=0

  pgbadger:
    image: dalibo/pgbadger:latest
    volumes:
      - ./pg_log:/logs:ro
      - ./pgbadger_reports:/reports
    entrypoint: ["/bin/sh", "-c", "while true; do pgbadger /logs/*.log -o /reports/report.html -f stderr; sleep 3600; done"]

volumes:
  pgdata:
```

### Generating Reports

```bash
# Basic report from today's logs
pgbadger /var/log/postgresql/postgresql-*.log -o report.html

# Incremental report (processes only new log entries)
pgbadger /var/log/postgresql/postgresql-*.log -o report.html --incremental

# JSON output for further processing
pgbadger /var/log/postgresql/postgresql-*.log -o report.json -f json

# Focus on slow queries only
pgbadger /var/log/postgresql/postgresql-*.log -o slow_queries.html --top 50
```

pgBadger's HTML reports include: hourly query volume charts, slowest queries ranked by duration, most frequent queries, connection spikes, checkpoint timing, autovacuum activity, error distribution, and temporary file usage. This makes it ideal for weekly performance reviews and identifying trends over time.

## pg_stat_statements: Real-Time Query Monitoring

[pg_stat_statements](https://www.postgresql.org/docs/current/pgstatstatements.html) is PostgreSQL's built-in query performance extension. Unlike pgBadger (which analyzes log files after the fact), pg_stat_statements **aggregates query statistics in real-time** within the database itself. It normalizes queries (replacing literals with `$1`, `$2`, etc.), groups identical query patterns, and tracks execution counts, total time, rows returned, shared block hits/reads, and more.

### Enabling pg_stat_statements

```sql
-- In postgresql.conf:
-- shared_preload_libraries = 'pg_stat_statements'

CREATE EXTENSION pg_stat_statements;

-- Reset statistics to start fresh
SELECT pg_stat_statements_reset();
```

### Key Queries

```sql
-- Top 10 slowest queries by average time
SELECT 
    queryid,
    LEFT(query, 120) AS query_preview,
    calls,
    ROUND(total_exec_time::numeric, 2) AS total_ms,
    ROUND(mean_exec_time::numeric, 2) AS avg_ms,
    ROUND((shared_blks_hit::numeric / NULLIF(shared_blks_hit + shared_blks_read, 0) * 100), 1) AS cache_hit_pct
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Queries with high I/O (poor cache hit ratio)
SELECT 
    LEFT(query, 120) AS query_preview,
    calls,
    shared_blks_read,
    ROUND((shared_blks_hit::numeric / NULLIF(shared_blks_hit + shared_blks_read, 0) * 100), 1) AS cache_hit_pct
FROM pg_stat_statements
WHERE calls > 100
  AND shared_blks_read > 1000
ORDER BY shared_blks_read DESC
LIMIT 10;

-- Most frequently executed queries
SELECT 
    LEFT(query, 120) AS query_preview,
    calls,
    ROUND(mean_exec_time::numeric, 2) AS avg_ms,
    rows
FROM pg_stat_statements
ORDER BY calls DESC
LIMIT 10;
```

pg_stat_statements is perfect for real-time dashboards: you can poll these queries every 30 seconds and feed them into Grafana, Prometheus, or a custom monitoring stack. For comprehensive PostgreSQL monitoring, see our [PostgreSQL monitoring comparison](../2026-04-18-pgwatch2-vs-percona-pmm-vs-pgmonitor-self-hosted-database-monitoring-guide-2026/).

## CSV Log Analysis: Custom Forensic Investigation

For ad-hoc debugging or when you need metrics that neither pgBadger nor pg_stat_statements provides, direct CSV log analysis gives you complete flexibility. PostgreSQL can write logs in CSV format, which is easily importable into PostgreSQL itself for SQL-based analysis.

### Enabling CSV Logging

```ini
log_destination = 'csvlog'
logging_collector = on
log_directory = 'pg_log'
```

### Importing CSV Logs into PostgreSQL

```sql
-- Create a table matching the CSV log structure
CREATE TABLE postgres_log (
    log_time timestamp(3) with time zone,
    user_name text,
    database_name text,
    process_id integer,
    connection_from text,
    session_id text,
    session_line_num bigint,
    command_tag text,
    session_start_time timestamp with time zone,
    virtual_transaction_id text,
    transaction_id bigint,
    error_severity text,
    sql_state_code text,
    message text,
    detail text,
    hint text,
    internal_query text,
    internal_query_pos integer,
    context text,
    query text,
    query_pos integer,
    location text,
    application_name text,
    backend_type text
);

-- Import with COPY
COPY postgres_log FROM '/var/log/postgresql/postgresql-2026-06-02.csv' WITH CSV;

-- Find queries with the longest execution times
SELECT 
    log_time,
    user_name,
    database_name,
    LEFT(message, 150) AS log_entry,
    LEFT(query, 200) AS sql_preview
FROM postgres_log
WHERE message LIKE 'duration%'
ORDER BY log_time DESC
LIMIT 20;

-- Count errors by severity
SELECT 
    error_severity,
    COUNT(*) AS error_count
FROM postgres_log
WHERE error_severity IS NOT NULL
GROUP BY error_severity
ORDER BY error_count DESC;

-- Analyze connections per hour
SELECT 
    date_trunc('hour', log_time) AS hour,
    COUNT(DISTINCT session_id) AS unique_sessions
FROM postgres_log
WHERE command_tag = 'authentication'
GROUP BY hour
ORDER BY hour DESC;
```

This approach shines when you're investigating a specific incident — for example, tracking down which user ran a destructive query at 3 AM, or identifying a connection flood pattern that doesn't show up in aggregated statistics.

## Why Self-Host Your Log Analysis

Running pgBadger and pg_stat_statements on your own infrastructure means you own your query performance data. Unlike managed PostgreSQL services that may meter or restrict access to log files, self-hosting gives you unlimited historical retention at the cost of your own storage. A busy PostgreSQL instance can generate 50-100 GB of logs per month — on a cloud service, that might mean choosing between high storage costs or losing diagnostic data.

For businesses handling sensitive data, log files contain query text that may include PII or business logic. Keeping logs on-premises eliminates the risk of exposing this data to a third-party analytics service. With pgBadger, you can even configure it to hash or anonymize query literals before generating reports, giving you performance insights without data leakage.

The open-source ecosystem also means flexibility. If pgBadger's default reports don't cover your specific needs, you can use its JSON output mode and pipe the data into your own visualization stack. For a complete PostgreSQL observability setup, pair pgBadger with our [PostgreSQL admin tools guide](../2026-05-17-self-hosted-postgresql-admin-tools-pgcenter-pgstatmonitor-pgstatstatements/). If you're optimizing database performance, our [database tuning guide](../2026-05-03-self-hosted-database-tuning-mysqltuner-pgtune-pgtune-ng-guide/) covers the complementary task of configuration optimization.

## Integration: A Complete Log Analysis Pipeline

For a comprehensive setup, use all three tools together:

1. **Real-time monitoring** — pg_stat_statements feeding a Grafana dashboard with 30-second refresh for immediate query performance alerts.
2. **Daily reports** — pgBadger cron job processing yesterday's logs and emailing the HTML report to the team.
3. **Forensic investigation** — CSV log import for ad-hoc analysis when debugging specific incidents.

```bash
#!/bin/bash
# Daily pgBadger report generation
REPORT_DIR="/var/www/pgbadger"
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)

pgbadger /var/log/postgresql/postgresql-${YESTERDAY}*.log     -o ${REPORT_DIR}/report-${YESTERDAY}.html     -f stderr     --exclude-query "^(BEGIN|COMMIT|SET|SHOW)"     --top 100

# Clean up reports older than 90 days
find ${REPORT_DIR} -name "report-*.html" -mtime +90 -delete
```

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted PostgreSQL Log Analysis: pgBadger vs pg_stat_statements vs CSV Log Analysis",
  "description": "Comprehensive guide to PostgreSQL log analysis tools: pgBadger for rich HTML reports, pg_stat_statements for real-time query monitoring, and CSV log analysis for custom forensic diagnostics.",
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

### How much overhead does pg_stat_statements add?

pg_stat_statements adds minimal overhead — typically 1-5% of shared_buffers for storing query texts and statistics. The CPU cost is negligible because it only hashes and normalizes each query once. On modern hardware handling 10,000+ queries per second, the overhead is typically less than 2%. The extension has been battle-tested in production at companies like Instagram, Heroku, and GitLab.

### Can pgBadger handle logs from multiple PostgreSQL instances?

Yes. pgBadger can process logs from multiple servers simultaneously if you prefix log lines with the server name. Use the `%a` format specifier in `log_line_prefix` to include an application name, or set `syslog_ident` to distinguish instances. Then feed all log files to pgBadger at once — it will group statistics by server in the report.

### How long should I retain PostgreSQL logs?

This depends on your compliance requirements and available storage. For performance analysis, 30-90 days is typical — enough to identify weekly/monthly patterns. For security auditing, you may need 1-7 years depending on regulations. pgBadger reports compress well (a month of logs becomes a ~5-20 MB HTML report), so retaining historical reports is cheap even if you rotate the raw logs.

### What if my queries contain sensitive data in the log?

Use PostgreSQL 13+ `log_parameter_max_length_on_error` to control how much parameter data appears in error logs. For pg_stat_statements, the extension normalizes literals automatically (replaces `'john@example.com'` with `$1`). pgBadger can hash query parameters via `--anonymize`. For CSV logs, filter sensitive columns during import: `COPY (SELECT log_time, error_severity, message FROM postgres_log) TO ...`.

### Is pg_stat_statements enough, or do I need pgBadger too?

pg_stat_statements gives you **real-time query-level aggregation** but doesn't capture session-level metrics (connection counts, disconnection times), checkpoint timing, autovacuum details, or error distributions. pgBadger excels at these broader operational metrics and produces shareable reports. For a complete picture, use both: pg_stat_statements for immediate query tuning, pgBadger for daily/weekly operational reviews.

---

**💡 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到 AI 监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测 AI 相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
