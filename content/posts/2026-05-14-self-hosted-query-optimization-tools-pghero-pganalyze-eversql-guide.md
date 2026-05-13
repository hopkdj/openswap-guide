---
title: "Self-Hosted Query Optimization Tools: pghero vs pganalyze vs EverSQL"
date: "2026-05-14"
tags: ["database", "postgresql", "query-optimization", "performance", "monitoring", "self-hosted"]
draft: false
---

Query performance is the backbone of any database-driven application. Slow queries cascade into degraded user experiences, increased infrastructure costs, and frustrated development teams. This guide compares three self-hosted query optimization tools that help identify, analyze, and resolve database performance bottlenecks without sending sensitive SQL data to external services.

When databases grow beyond a few tables with simple queries, performance optimization becomes a specialized discipline. Database administrators spend significant time analyzing execution plans, identifying missing indexes, and rewriting problematic queries. The tools compared in this guide automate and streamline that process, providing actionable recommendations through intuitive web interfaces rather than raw command-line output.


## Why Self-Host Query Optimization?

Database query plans contain sensitive information about your data model, access patterns, and business logic. Cloud-based query analyzers require sending EXPLAIN output and query fingerprints to external services, creating a compliance risk for organizations handling regulated data. Self-hosted tools keep all analysis within your infrastructure while providing the same optimization insights.

Keeping query analysis on-premises eliminates the risk of sensitive schema information leaking to third-party services. For organizations processing financial transactions, healthcare records, or personal data, this control is not optional. Self-hosted query tools also eliminate recurring per-query pricing that scales unpredictably as your database grows.

Database performance data reveals which tables are accessed most frequently, how users search for data, and what relationships exist between entities. This information becomes a valuable target for competitors and a compliance concern for regulated industries. Organizations under GDPR, HIPAA, or PCI-DSS requirements must demonstrate control over where their database performance data flows. Self-hosted tools satisfy these requirements by keeping all analysis within the organizational network perimeter.

## pghero

PgHero is a performance dashboard for PostgreSQL created by Andrew Kane. It provides a clean web interface for monitoring query performance, index usage, and database health metrics.

### Key Features

- Query performance dashboard that identifies slow queries and provides execution statistics
- Index analysis that detects unused and missing indexes with actionable recommendations
- Connection monitoring that tracks active connections and identifies connection pool issues
- Table bloat detection that identifies tables that need VACUUM or reindexing
- Space analysis showing table and index sizes with growth trends
- Rails integration with native support for Ruby on Rails applications

### Installation

```bash
docker run -d --name pghero -p 8080:8080 \
  -e DATABASE_URL=postgres://user:pass@host:5432/dbname \
  ankane/pghero
```

### Docker Compose

```yaml
version: "3.8"
services:
  pghero:
    image: ankane/pghero:latest
    ports:
      - "8080:8080"
    environment:
      DATABASE_URL: postgres://app:secret@postgres:5432/production
    depends_on:
      - postgres
  postgres:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: production
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:
```

### Configuration

PgHero requires pg_stat_statements to be loaded in your PostgreSQL configuration. Add shared_preload_libraries equals pg_stat_statements to postgresql.conf and set pg_stat_statements.track to all for complete query tracking.

## pganalyze

Pganalyze offers a self-hosted collector paired with a dashboard. The collector runs locally and gathers comprehensive database metrics including query plans, lock information, and system-level statistics.

### Key Features

- Log insights that parse PostgreSQL logs to surface slow queries and errors
- EXPLAIN plan analysis that captures and stores actual execution plans
- Index recommendation engine that suggests new indexes based on observed query patterns
- Lock monitoring that detects blocking chains and deadlock risks
- Schema change impact tracking that measures performance before and after migrations

### Docker Compose

```yaml
version: "3.8"
services:
  pganalyze-collector:
    image: pganalyze/collector:latest
    environment:
      DB_HOST: postgres
      DB_USERNAME: pganalyze
      DB_PASSWORD: secret
      DB_NAME: production
      PGA_API_KEY: your-api-key
    depends_on:
      - postgres
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: pganalyze
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: production
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:
```

## EverSQL

EverSQL is a database optimization platform that offers query tuning recommendations using pattern matching against a large database of known query optimization patterns. Its API can be integrated into self-hosted CI/CD pipelines for automated query review.

### Key Features

- Automated query optimization that analyzes queries and suggests rewrites
- Index recommendations that identify optimal indexes for slow queries
- Query comparison that compares execution plans before and after optimization
- CI/CD integration for automated query review in deployment pipelines
- MySQL and PostgreSQL support covering the two most popular open-source databases

## Comparison Table

| Feature | PgHero | pganalyze | EverSQL |
|---------|--------|-----------|---------|
| Primary Focus | Performance dashboard | Deep query analysis | Automated optimization |
| Database Support | PostgreSQL only | PostgreSQL only | PostgreSQL + MySQL |
| Self-Hosted | Full | Collector only | API integration |
| Query Recommendations | Basic | Advanced | Automated rewrites |
| EXPLAIN Plan Visualization | No | Yes | Yes |
| Index Recommendations | Yes | Yes | Yes |
| Lock Monitoring | No | Yes | No |
| Web UI | Yes (simple) | Yes (dashboard) | Web-based |
| Cost | Free (open-source) | Free collector + paid | Paid per-query |

## Choosing the Right Query Optimization Tool

Use PgHero if you need a free, open-source PostgreSQL performance dashboard with a clean web interface. It is ideal for teams that want quick visibility into slow queries, index usage, and table bloat without complex setup.

Use pganalyze if you need deep query analysis with actual EXPLAIN plan capture and index recommendations. The self-hosted collector keeps all data local while providing enterprise-grade analysis capabilities.

Use EverSQL if you want automated query rewrite recommendations and CI/CD pipeline integration. Its API-first approach fits naturally into automated deployment workflows.

For PostgreSQL connection pooling strategies that complement query optimization, see our [database connection pooling guide](../pgbouncer-vs-proxysql-vs-odyssey-self-hosted-database-connection-pooling-guide-2026/). If you need help with PostgreSQL high availability alongside query optimization, our [PostgreSQL HA guide](../patroni-vs-galera-cluster-vs-repmgr-self-hosted-database-high-availability-guide-2026/) covers clustering options. For database migration tools that help restructure schemas based on query optimization findings, our [schema diff guide](../self-hosted-database-schema-diff-comparison-sqitch-liquibase-flyway-guide-2026/) covers version-controlled migration workflows.

## Security Best Practices for Query Optimization

When running query analysis on production databases, security considerations are as important as the optimization results themselves. Query execution plans expose your complete data model, including table structures, column names, and index configurations. This information alone is valuable to attackers mapping your system architecture.

First, restrict access to the optimization tool's web interface to your internal network. PgHero supports HTTP basic authentication via web server configuration, while pganalyze offers role-based access controls. Never expose these dashboards to the public internet, even with authentication, as they provide a direct window into your database's most performance-sensitive operations.

Second, use read-only database credentials for all analysis connections. PgHero requires only SELECT access to pg_stat_statements and system catalogs. pganalyze needs pg_stat_activity and pg_stat_statements access. Neither tool requires write access to your application tables. Creating a dedicated read-only role limits the blast radius if credentials are compromised.

Third, configure log retention policies that align with your compliance requirements. Query logs containing slow-query data and execution plans should be stored encrypted at rest and retained only as long as necessary for performance analysis. Most organizations find a 30-day retention window sufficient for identifying recurring performance issues without accumulating sensitive data indefinitely.

Finally, implement alerting thresholds that trigger when query performance degrades beyond acceptable limits. Both pganalyze and pgHero support configurable alerting for slow query detection. Set thresholds based on your application's SLA requirements rather than absolute query duration values. A 500ms query may be acceptable for batch processing but catastrophic for a checkout page.


## FAQ

### What is the difference between query optimization and query monitoring?

Query monitoring identifies which queries are slow and tracks performance trends over time. Query optimization goes further by analyzing execution plans, suggesting index changes, and sometimes automatically rewriting queries for better performance. Monitoring tells you what is slow; optimization tells you how to fix it.

### Do I need pg_stat_statements for PostgreSQL query optimization?

Yes, pg_stat_statements is essential for any PostgreSQL query optimization tool. It tracks execution statistics for all SQL statements, including total time, calls, rows returned, and shared buffer hits. Without it, tools can only analyze individual queries in isolation.

### Can these tools optimize queries automatically?

PgHero and pganalyze provide recommendations that you apply manually. EverSQL can generate optimized query rewrites automatically through its API. No tool should automatically deploy query changes to production without human review.

### How do I know if a recommended index is actually helping?

After applying a recommended index, use EXPLAIN ANALYZE on the original query to compare execution plans. Look for reduced execution time, fewer sequential scans, and lower buffer read counts.

### Are self-hosted query tools suitable for production databases?

Yes, all three tools are designed for production use. They use read-only queries and do not modify your database.

### How often should I review query performance?

For most applications, weekly review is sufficient. During high-traffic periods or after major releases, increase the frequency to daily.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Query Optimization Tools: pghero vs pganalyze vs EverSQL",
  "description": "Compare self-hosted database query optimization tools for PostgreSQL and MySQL. Learn to deploy pghero, pganalyze, and EverSQL with Docker for secure, on-premises SQL performance analysis.",
  "datePublished": "2026-05-14",
  "dateModified": "2026-05-14",
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
