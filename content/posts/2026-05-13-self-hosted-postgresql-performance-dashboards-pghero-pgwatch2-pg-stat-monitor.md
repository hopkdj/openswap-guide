---
title: "Self-Hosted PostgreSQL Performance Dashboards: pgHero vs pgwatch2 vs pg_stat_monitor"
date: "2026-05-13"
tags: ["database", "postgresql", "monitoring", "self-hosted", "comparison", "guide"]
draft: false
---

PostgreSQL is one of the most popular open-source relational databases, but identifying slow queries, index bloat, and connection bottlenecks requires specialized tooling. This guide compares three leading open-source PostgreSQL performance monitoring solutions: **pgHero**, **pgwatch2**, and **pg_stat_monitor** — each offering unique approaches to database observability.

## Why Monitor PostgreSQL Performance?

Database performance issues are often the bottleneck for application responsiveness. Without dedicated monitoring tools, slow queries go unnoticed until users report problems, index inefficiencies waste storage and memory, and connection pool exhaustion causes cascading failures.

**Proactive query optimization.** The most impactful database optimization is identifying and tuning slow queries. Performance dashboards surface queries by execution time, total time consumed, and frequency, allowing DBAs to focus optimization efforts on the queries that actually impact user experience. A single unindexed query running thousands of times per minute can consume more resources than the entire rest of the database workload.

**Index health monitoring.** PostgreSQL indexes degrade over time through insert, update, and delete operations. Unused indexes waste disk space and slow down write operations. Performance dashboards track index usage statistics, sequential scan ratios, and index bloat, enabling data-driven decisions about which indexes to rebuild, remove, or add.

**Connection and resource management.** PostgreSQL uses a process-per-connection architecture, meaning each connection consumes significant memory and CPU. Monitoring connection counts, idle connections, and temporary file creation helps right-size connection poolers and identify application-level connection leaks before they cause production outages.

**Capacity planning and trend analysis.** Historical performance data reveals growth patterns in query execution times, table sizes, and connection counts. Trend analysis enables capacity planning decisions — when to add read replicas, when to increase shared_buffers, or when to partition large tables — based on actual usage data rather than guesswork.

For database connectivity, see our [PgBouncer vs Odyssey vs Pgpool-II guide](../pgbouncer-vs-odyssey-vs-pgpool-self-hosted-database-connection-pooler-2026/). For logical replication monitoring, our [pglogical vs wal2json vs pgoutput comparison](../2026-05-10-self-hosted-postgresql-logical-replication-pglogical-wal2json-pgoutput-guide/) covers replication health. For broader database management, our [database connection pooler comparison](../pgbouncer-vs-proxysql-vs-odyssey-self-hosted-database-connection-pooler-guide/) provides additional context.

## Comparison Overview

| Feature | pgHero | pgwatch2 | pg_stat_monitor |
|---------|--------|----------|-----------------|
| Primary Focus | Single-server dashboard | Multi-server monitoring | Query-level metrics |
| GitHub Stars | 8,860 | 1,843 | 578 |
| Deployment | Docker, Ruby gem | Docker Compose | PostgreSQL extension |
| Multi-DB Support | Limited (one per instance) | ✅ Unlimited | Per-server extension |
| Historical Data | Basic | ✅ Full time-series | Query-level aggregation |
| Real-time Queries | ✅ Live pg_stat_activity | ✅ Live + historical | ✅ Extension-based |
| Index Analysis | ✅ Unused indexes, bloat | ✅ Index usage stats | Via queries |
| Alerting | No | ✅ Built-in alerts | No (requires external) |
| Grafana Integration | No | ✅ Pre-built dashboards | Via pg_stat_statements |
| Overhead | Low | Low-Medium | Very Low |
| License | MIT | Apache-2.0 | Apache-2.0 |
| Last Updated | Active (2026) | Active (2026) | Active (2026) |

## pgHero: Simple, Effective PostgreSQL Dashboard

pgHero is a lightweight PostgreSQL performance dashboard that provides an intuitive web interface for monitoring query performance, index usage, and database health. Created by Andrew Kane (ankane), it prioritizes simplicity and actionable insights over complex configuration.

**Architecture:** pgHero connects to a single PostgreSQL database and queries the built-in `pg_stat_*` views to generate its dashboard. It runs as a Ruby on Rails application and can be deployed via Docker, as a gem in an existing Rails app, or as a standalone process.

**Key Features:**
- Query performance analysis with execution time rankings
- Unused and duplicate index detection
- Table bloat estimation and vacuum recommendations
- Connection count monitoring with idle connection identification
- Space analysis showing largest tables and indexes
- Sequential scan detection (missing indexes)
- EXPLAIN plan visualization for slow queries
- Clean, minimal web interface with zero configuration

**Docker Compose deployment:**

```yaml
version: '3.8'
services:
  pghero:
    image: ankane/pghero:latest
    ports:
      - "8080:80"
    environment:
      DATABASE_URL: postgres://postgres:password@postgres:5432/mydb
    depends_on:
      - postgres

  postgres:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: password
      POSTGRES_DB: mydb
    ports:
      - "5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data
    command: >
      postgres -c shared_preload_libraries=pg_stat_statements
               -c pg_stat_statements.track=all

volumes:
  pg_data:
```

**Configuration for maximum insight:**

```sql
-- Enable pg_stat_statements for query tracking
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Grant pghero access
GRANT EXECUTE ON FUNCTION pg_stat_statements_reset() TO pghero;
GRANT EXECUTE ON FUNCTION pg_stat_statements(showtext boolean) TO pghero;
```

**Best for:** Teams running a single PostgreSQL instance who want a zero-configuration dashboard that immediately surfaces the most impactful performance issues. The intuitive interface makes it accessible to developers without DBA expertise.

## pgwatch2: Enterprise-Grade PostgreSQL Monitoring

pgwatch2 is a comprehensive PostgreSQL monitoring platform developed by Cybertec that supports multi-database monitoring, historical metrics collection, alerting, and Grafana integration.

**Architecture:** pgwatch2 uses a modular architecture with a collector daemon that gathers metrics from PostgreSQL instances, a metrics storage backend (PostgreSQL or TimescaleDB), and a web UI for configuration and dashboard viewing. It ships with 80+ pre-configured metrics covering every aspect of PostgreSQL performance.

**Key Features:**
- Multi-database monitoring from a single instance
- 80+ pre-configured metric collections
- Historical time-series data storage
- Built-in alerting with configurable thresholds
- Grafana integration with pre-built dashboards
- Real-time pg_stat_activity monitoring
- Query explain plan capture
- Custom metric definitions via SQL
- Preset profiles: basic, exhaustive, recommended

**Docker Compose deployment:**

```yaml
version: '3.8'
services:
  pgwatch2:
    image: cybertecpostgresql/pgwatch2:latest
    ports:
      - "8080:80"
      - "3000:3000"  # Grafana
    environment:
      PW2_WEBUSER: admin
      PW2_WEBPASSWORD: admin
    volumes:
      - pw2_config:/etc/pgwatch2

  pgwatch2-db:
    image: cybertecpostgresql/pgwatch2-db:latest
    environment:
      POSTGRES_PASSWORD: pgwatch2admin
    volumes:
      - pw2_db_data:/var/lib/postgresql/data

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    depends_on:
      - pgwatch2

volumes:
  pw2_config:
  pw2_db_data:
```

**Best for:** Organizations managing multiple PostgreSQL instances who need centralized monitoring, historical trend analysis, and alerting capabilities. The Grafana integration makes it ideal for NOC dashboards.

## pg_stat_monitor: Query-Level Performance Extension

pg_stat_monitor is a PostgreSQL extension developed by Percona that enhances the built-in `pg_stat_statements` with richer query-level metrics, including query plans, client IP addresses, and time-based bucketing.

**Architecture:** pg_stat_monitor replaces or supplements `pg_stat_statements` as a `shared_preload_libraries` extension. It intercepts query execution at the executor level and collects detailed statistics that are exposed through the `pg_stat_monitor` view.

**Key Features:**
- Query execution time with min, max, mean, stddev
- Query plan capture (when enabled)
- Client IP address and application name tracking
- Time-based bucketing for trend analysis
- Query normalization with parameter tracking
- Rows affected, blocks hit/read statistics
- Temporary file creation tracking
- Works with any PostgreSQL version 11+

**Installation and configuration:**

```sql
-- Add to postgresql.conf
-- shared_preload_libraries = 'pg_stat_monitor'

-- Or via ALTER SYSTEM
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_monitor';
SELECT pg_reload_conf();

-- Create the extension
CREATE EXTENSION pg_stat_monitor;

-- Query the most time-consuming queries
SELECT
    substr(query, 1, 100) AS query,
    calls,
    total_exec_time,
    mean_exec_time,
    rows
FROM pg_stat_monitor
ORDER BY total_exec_time DESC
LIMIT 10;
```

**Best for:** DBAs who need detailed query-level performance data without deploying a separate monitoring application. The extension integrates directly with PostgreSQL and has minimal overhead.

## Choosing the Right PostgreSQL Monitoring Tool

| Criteria | Choose pgHero | Choose pgwatch2 | Choose pg_stat_monitor |
|----------|--------------|-----------------|----------------------|
| Quick single-DB overview | ✅ Best option | Overkill | Limited UI |
| Multi-DB monitoring | No | ✅ Best option | Per-server install |
| Historical trends | Basic | ✅ Full time-series | Buckets |
| Alerting | No | ✅ Built-in | No |
| Grafana dashboards | No | ✅ Pre-built | Manual setup |
| Query plan capture | EXPLAIN only | Yes | ✅ Native extension |
| Developer-friendly UI | ✅ Excellent | Good | SQL only |
| Setup complexity | Lowest | Medium | Low |

## FAQ

### What is the difference between pg_stat_statements and pg_stat_monitor?
`pg_stat_statements` is PostgreSQL's built-in query statistics extension. pg_stat_monitor is a Percona-developed extension that extends it with additional metrics like query plans, client IPs, application names, and time-based bucketing. pg_stat_monitor is backward-compatible and can replace pg_stat_statements.

### Does pgHero work with multiple databases?
pgHero is designed for a single database connection. To monitor multiple databases, deploy separate pgHero instances (or separate Docker containers) for each database. For centralized multi-DB monitoring, pgwatch2 is the better choice.

### How much overhead does pg_stat_monitor add?
pg_stat_monitor adds approximately 1-3% overhead on query execution — negligible for most workloads. The extension collects statistics in shared memory and writes to disk only during checkpoint operations. For write-heavy workloads, consider increasing the `pg_stat_monitor.max` parameter to reduce hash collisions.

### Can I use these tools with managed PostgreSQL services?
Yes. pgHero works with any PostgreSQL-compatible service (AWS RDS, Google Cloud SQL, Azure Database for PostgreSQL). pgwatch2 requires network access to the database endpoint. pg_stat_monitor requires the ability to modify `shared_preload_libraries`, which is supported on most managed services with a parameter group change.

### Which tool is best for identifying slow queries?
All three tools can identify slow queries, but they differ in approach. pgHero shows slow queries in a ranked web interface. pgwatch2 captures them in time-series data with historical comparison. pg_stat_monitor provides the most granular data including execution time distributions and query plan information.

### How often should I review PostgreSQL performance metrics?
For production databases, review dashboards daily for anomalies (spike in connections, new slow queries) and perform deep analysis weekly (index usage trends, table bloat, query plan changes). pgwatch2's alerting can automate anomaly detection, while pgHero and pg_stat_monitor require manual review.

## Choosing the Right PostgreSQL Performance Dashboard

For **single-database teams** wanting quick insights, pgHero provides the simplest path to actionable performance data. The web interface makes database health visible to the entire development team without SQL expertise.

For **multi-database organizations** needing centralized monitoring, alerting, and historical trend analysis, pgwatch2 offers the most comprehensive feature set with Grafana integration and 80+ pre-configured metrics.

For **DBA-focused teams** who prefer extension-based monitoring with minimal infrastructure, pg_stat_monitor provides the richest query-level data directly within PostgreSQL, with the option to build custom dashboards on top of its view.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted PostgreSQL Performance Dashboards: pgHero vs pgwatch2 vs pg_stat_monitor",
  "description": "Compare three leading PostgreSQL performance monitoring tools: pgHero, pgwatch2, and pg_stat_monitor for database observability and query optimization.",
  "datePublished": "2026-05-13",
  "dateModified": "2026-05-13",
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
