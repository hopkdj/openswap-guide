---
title: "Self-Hosted PostgreSQL Index Optimization: HypoPG vs pg_qualstats vs pg_stat_user_indexes"
date: "2026-06-02"
tags: ["postgresql", "database", "performance", "optimization", "indexing", "devops"]
draft: false
---

## Introduction

PostgreSQL's performance is heavily dependent on proper indexing. A single missing index can turn a millisecond query into a multi-second table scan, while unused indexes waste disk space, slow down writes, and bloat your buffer cache. For self-hosted PostgreSQL deployments, having the right tools to analyze, test, and optimize your index strategy is essential.

In this guide, we compare three powerful open-source tools for PostgreSQL index optimization: **HypoPG** for hypothetical index testing, **pg_qualstats** for predicate-based index recommendations, and **pg_stat_user_indexes** (built into PostgreSQL) for tracking actual index usage. Each tool addresses a different phase of the index lifecycle — from discovery to validation to cleanup.

## Comparison Table

| Feature | HypoPG | pg_qualstats | pg_stat_user_indexes |
|---------|--------|-------------|---------------------|
| **Purpose** | Test hypothetical indexes | Find missing indexes | Monitor existing indexes |
| **Type** | PostgreSQL extension | PostgreSQL extension | Built-in system view |
| **Stars** | 1,654+ | 331+ | N/A (core PostgreSQL) |
| **Last Updated** | May 2026 | May 2026 | Active (PostgreSQL 17) |
| **Performance Impact** | Near-zero (virtual) | ~2-5% overhead | None (built-in stats) |
| **Installation** | `CREATE EXTENSION` | `CREATE EXTENSION` | Always available |
| **Best For** | Validating index candidates | Discovering WHERE clause gaps | Finding unused indexes |
| **Docker Support** | Yes (official PGXN) | Yes (pgxn tools) | Built into PG images |
| **License** | PostgreSQL | PostgreSQL | PostgreSQL |

## HypoPG: Testing Indexes Without Creating Them

[HypoPG](https://github.com/HypoPG/hypopg) is a PostgreSQL extension that lets you create **hypothetical indexes** — indexes that exist only in the query planner's memory. The database never writes them to disk, yet you can run `explain` to see if the planner would use them. This is invaluable for testing index candidates on production-sized schemas without the risk of a long `CREATE INDEX` operation.

### Installation

```bash
# Install HypoPG via apt (Debian/Ubuntu)
apt-get install postgresql-16-hypopg

# Or install from source
git clone https://github.com/HypoPG/hypopg.git
cd hypopg
make install
```

### Docker Compose Setup

```yaml
version: "3.8"
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: securepass
      POSTGRES_DB: appdb
    volumes:
      - pgdata:/var/lib/postgresql/data
    command: >
      sh -c "apt-get update && apt-get install -y postgresql-16-hypopg && 
             docker-entrypoint.sh postgres"
    ports:
      - "5432:5432"

volumes:
  pgdata:
```

After connecting, enable the extension:

```sql
CREATE EXTENSION IF NOT EXISTS hypopg;
```

### Usage Example

```sql
-- Check a slow query's plan
explain SELECT * FROM orders WHERE customer_id = 42 AND status = 'pending';

-- Create a hypothetical index
SELECT hypopg_create_index('CREATE INDEX ON orders (customer_id, status)');

-- Re-check the plan — does the planner use it?
explain SELECT * FROM orders WHERE customer_id = 42 AND status = 'pending';

-- View all hypothetical indexes
SELECT * FROM hypopg_list_indexes;

-- Clean up when done
SELECT hypopg_reset();
```

HypoPG is especially useful when combined with `explain (ANALYZE, BUFFERS)` to compare the estimated cost reduction. Since hypothetical indexes never touch disk, you can safely test dozens of candidates in seconds.

## pg_qualstats: Finding What the WHERE Clause Misses

[pg_qualstats](https://github.com/powa-team/pg_qualstats) takes a different approach: instead of testing what you *think* you need, it **observes** your actual queries and reports which WHERE clause predicates could benefit from indexes. It samples query predicates and their selectivity (how many rows each filter eliminates), then recommends missing indexes.

### Installation

```bash
apt-get install postgresql-16-pg-qualstats
```

Enable in the target database:

```sql
CREATE EXTENSION pg_qualstats;
```

### Key Queries

```sql
-- Top predicate patterns missing indexes
SELECT 
    relid::regclass AS table_name,
    attnames,
    possible_types,
    execution_count
FROM pg_qualstats_by_query
ORDER BY execution_count DESC
LIMIT 20;

-- Predicates with poor selectivity (most rows scanned)
SELECT 
    relid::regclass AS table_name,
    attnames,
    qualname,
    execution_count,
    filter_ratio
FROM pg_qualstats 
WHERE filter_ratio > 0.5
ORDER BY execution_count DESC;
```

The `filter_ratio` column is critical — a value of 0.95 means 95% of scanned rows are discarded by the filter. This is a strong signal that an index would help.

pg_qualstats is designed to run continuously on production databases with minimal overhead (~2-5% CPU). Unlike HypoPG's manual hypothesis approach, qualstats builds evidence from real workloads.

## pg_stat_user_indexes: Cleaning Up Unused Indexes

PostgreSQL's built-in `pg_stat_user_indexes` view tracks how often each index is used. It's the most direct way to identify indexes that are wasting space and slowing down writes.

```sql
-- Find indexes never used for scans
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND indexrelid NOT IN (
    SELECT conindid FROM pg_constraint 
    WHERE contype IN ('p', 'u')
  )
ORDER BY pg_relation_size(indexrelid) DESC;

-- Find indexes with low usage relative to size
SELECT 
    schemaname || '.' || tablename AS table_name,
    indexname,
    idx_scan,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size,
    CASE 
        WHEN idx_scan = 0 THEN 'UNUSED'
        WHEN idx_scan < 100 THEN 'RARELY USED'
        ELSE 'ACTIVE'
    END AS status
FROM pg_stat_user_indexes
WHERE idx_scan < 1000
  AND pg_relation_size(indexrelid) > 1048576  -- > 1MB
ORDER BY pg_relation_size(indexrelid) DESC;
```

**Important:** `idx_scan` resets on server restart and on statistics reset. Use `pg_stat_reset()` to start fresh tracking, or combine with `pg_stat_statements` for longer-term analysis.

### Automated Index Cleanup Script

```bash
#!/bin/bash
# Generate DROP INDEX statements for unused indexes
psql -d mydb -Atc "
SELECT 'DROP INDEX CONCURRENTLY ' || indexrelid::regclass || ';'
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND indexrelid NOT IN (
    SELECT conindid FROM pg_constraint WHERE contype IN ('p', 'u')
  );
" > drop_unused_indexes.sql

echo "Review drop_unused_indexes.sql before running!"
```

## Why Self-Host Your Index Optimization?

Self-hosting your index optimization workflow gives you **complete control** over your performance data. Unlike cloud-managed PostgreSQL services that may limit access to system catalogs or charge extra for query analytics, a self-hosted setup with HypoPG, pg_qualstats, and pg_stat_user_indexes gives you unfiltered access to every statistic. You can run these tools 24/7 without per-query pricing, store unlimited historical data, and customize the analysis pipeline to match your exact schema patterns.

Data sovereignty is another advantage: all query statistics and predicate analysis data stays on your infrastructure. For organizations handling sensitive user data or operating in regulated industries (healthcare, finance, government), keeping query telemetry in-house eliminates compliance concerns that arise with third-party monitoring services.

The open-source nature also means you're not locked into a single vendor's tooling. If your needs grow beyond what HypoPG and pg_qualstats offer, you can integrate with pg_stat_statements, pgBadger, or the broader Postgres ecosystem — all running on your own hardware. For a comprehensive PostgreSQL backup strategy, check our [PostgreSQL backup tools guide](../pgbackrest-vs-barman-vs-wal-g-self-hosted-postgresql-backup-guide-2026/). For monitoring your database health, see our [PostgreSQL monitoring comparison](../2026-04-18-pgwatch2-vs-percona-pmm-vs-pgmonitor-self-hosted-database-monitoring-guide-2026/). If you're managing connection pools, our [PgBouncer vs ProxySQL vs Odyssey comparison](../pgbouncer-vs-proxysql-vs-odyssey-self-hosted-database-connection-pooling-guide-2026/) provides essential guidance for scaling your connection layer.

Finally, running these tools locally means instant feedback. When a developer asks "would an index on `(customer_id, created_at)` help this query?", you can test it with HypoPG in seconds — no ticket needed, no cloud console login, no waiting for managed service dashboards to refresh. This tight feedback loop is invaluable for development teams that ship frequently.

## Workflow: Putting All Three Tools Together

Here's a practical workflow for index optimization:

1. **Monitor** — Run pg_qualstats for a week on your production workload to identify predicate patterns that lack index coverage.
2. **Hypothesize** — For each missing-index candidate from qualstats, use HypoPG to test whether the PostgreSQL planner would actually use it.
3. **Create** — Deploy the validated index candidates with `CREATE INDEX CONCURRENTLY` (non-blocking).
4. **Verify** — After a few days, check pg_stat_user_indexes to confirm the new indexes are being used.
5. **Clean** — Periodically review pg_stat_user_indexes and drop indexes with `idx_scan = 0` (excluding primary keys and unique constraints).

This loop — discover, test, deploy, verify, clean — forms a complete index lifecycle management strategy.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted PostgreSQL Index Optimization: HypoPG vs pg_qualstats vs pg_stat_user_indexes",
  "description": "Compare HypoPG, pg_qualstats, and pg_stat_user_indexes for PostgreSQL index optimization — discover missing indexes, test hypothetical indexes, and clean up unused indexes on your self-hosted database.",
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

### How much performance overhead do these tools add?

HypoPG has **zero overhead** on actual queries — hypothetical indexes exist only in memory and don't affect real query execution. pg_qualstats adds approximately 2-5% CPU overhead because it inspects every query's WHERE clause predicates. pg_stat_user_indexes has **no measurable overhead** since PostgreSQL already tracks index usage statistics by default.

### Can I use HypoPG and pg_qualstats together on the same database?

Yes — they complement each other perfectly. Install both extensions on your staging or development database. Use pg_qualstats to discover WHERE clause gaps, then use HypoPG to validate whether proposed indexes would actually be used by the planner. On production, you may want to only run pg_qualstats (for its low overhead) while using HypoPG on a replica or staging copy.

### How do I know if dropping an unused index is safe?

Always check two things before dropping: (1) Is the index backing a constraint? Primary key and unique constraint indexes are never truly "unused" — they enforce data integrity. Filter them out with `contype IN ('p', 'u')`. (2) Has `idx_scan` been reset recently? If you just restarted PostgreSQL or ran `pg_stat_reset()`, the counters may not reflect actual usage. Wait at least 1-2 weeks after a reset before trusting zero-scan statistics.

### What's the difference between pg_stat_user_indexes and pg_statio_user_indexes?

`pg_stat_user_indexes` tracks **logical** index usage (how many times the index was scanned for queries). `pg_statio_user_indexes` tracks **physical** I/O (how many blocks were read from the index). Use both together: `idx_scan = 0` but high `idx_blks_read` may indicate the index is being used but statistics were reset. Conversely, high `idx_scan` with high `idx_blks_read` suggests the index is heavily used and may benefit from being in a faster storage tier.

### Should I run these tools on production or staging?

pg_qualstats is designed for production with minimal overhead, so it's safe to run there. HypoPG is best on staging or a production replica — while it has zero overhead on real queries, you want to test hypothetical indexes on a dataset that matches production scale for accurate planner estimates. pg_stat_user_indexes is always available on every PostgreSQL instance.

---

**💡 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到 AI 监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测 AI 相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
