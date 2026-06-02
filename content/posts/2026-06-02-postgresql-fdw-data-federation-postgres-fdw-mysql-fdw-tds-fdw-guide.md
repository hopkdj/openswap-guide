---
title: "Self-Hosted PostgreSQL Data Federation: postgres_fdw vs mysql_fdw vs tds_fdw — Cross-Database Query Guide"
date: "2026-06-02"
tags: ["postgresql", "database", "fdw", "data-federation", "mysql", "mssql", "self-hosted", "sql"]
draft: false
---

## Introduction

Modern self-hosted architectures rarely rely on a single database engine. A typical deployment might use PostgreSQL for transactional data, MySQL for a legacy application, and Microsoft SQL Server for a vendor system. PostgreSQL's Foreign Data Wrapper (FDW) framework enables transparent cross-database queries — you can `JOIN` a local PostgreSQL table with a remote MySQL table in a single SQL statement without ETL pipelines.

This guide compares three production-grade FDWs: the built-in **postgres_fdw** for PostgreSQL-to-PostgreSQL federation, **mysql_fdw** for MySQL/MariaDB access, and **tds_fdw** for Microsoft SQL Server and Sybase connectivity. We cover installation, performance tuning, security, and self-hosted deployment patterns.

## Comparison Table

| Feature | postgres_fdw | mysql_fdw | tds_fdw |
|---------|-------------|-----------|---------|
| Source Database | PostgreSQL 9.6+ | MySQL 5.5+ / MariaDB | MSSQL 2008+ / Sybase |
| Stars | Bundled with PG (21K+) | 596 | 427 |
| Last Update | Continuous | May 2026 | May 2026 |
| Pushdown (WHERE) | Full | Partial | Partial |
| Pushdown (JOIN) | Yes (PG 11+) | No | No |
| Pushdown (Aggregates) | Yes (PG 14+) | No | No |
| Write Support | INSERT/UPDATE/DELETE | INSERT/UPDATE/DELETE | INSERT/UPDATE/DELETE |
| Column Mapping | Automatic | Manual via options | Manual via options |
| SSL/TLS | Native | Via MySQL SSL | Via FreeTDS |
| Import Schema | IMPORT FOREIGN SCHEMA | IMPORT FOREIGN SCHEMA | IMPORT FOREIGN SCHEMA |
| Transaction Support | Yes (2PC optional) | Limited | Limited |

## postgres_fdw: PostgreSQL-to-PostgreSQL Federation

`postgres_fdw` is included in the PostgreSQL core distribution since 9.3 and provides the deepest query pushdown capabilities among all FDWs. It can push down `WHERE` clauses, `JOIN`s, `ORDER BY`, `LIMIT`, and aggregate functions to the remote server, minimizing data transfer.

### Docker Compose Setup

```yaml
version: "3.8"
services:
  postgres-primary:
    image: postgres:17
    container_name: pg-primary
    environment:
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: securepass
      POSTGRES_DB: analytics
    ports:
      - "5432:5432"
    volumes:
      - pg-primary-data:/var/lib/postgresql/data

  postgres-remote:
    image: postgres:17
    container_name: pg-remote
    environment:
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: securepass
      POSTGRES_DB: inventory
    ports:
      - "5433:5432"
    volumes:
      - pg-remote-data:/var/lib/postgresql/data

volumes:
  pg-primary-data:
  pg-remote-data:
```

### Creating and Using postgres_fdw

```sql
-- Enable extension
CREATE EXTENSION postgres_fdw;

-- Define remote server
CREATE SERVER inventory_server
  FOREIGN DATA WRAPPER postgres_fdw
  OPTIONS (host 'pg-remote', port '5432', dbname 'inventory');

-- Create user mapping
CREATE USER MAPPING FOR CURRENT_USER
  SERVER inventory_server
  OPTIONS (user 'admin', password 'securepass');

-- Import remote schema
IMPORT FOREIGN SCHEMA public
  FROM SERVER inventory_server
  INTO public;

-- Cross-database query with JOIN pushdown (PG 11+)
SELECT
    a.order_id,
    a.customer_name,
    i.product_name,
    i.warehouse_location
FROM orders a
JOIN inventory.products i ON a.product_id = i.product_id
WHERE a.order_date > CURRENT_DATE - INTERVAL '30 days';

-- EXPLAIN to verify pushdown
EXPLAIN (VERBOSE, ANALYZE)
SELECT * FROM inventory.products WHERE price > 100;
-- Look for "Foreign Scan" with "Remote SQL" showing pushed-down WHERE clause
```

### Performance Tuning

```sql
-- Increase fetch size for large result sets
ALTER SERVER inventory_server
  OPTIONS (ADD fetch_size '50000');

-- Enable batch inserts
ALTER FOREIGN TABLE inventory.products
  OPTIONS (batch_size '1000');

-- Use async execution (PG 14+)
SET enable_async_append = on;
SET enable_async_foreign_scan = on;

-- Analyze remote table statistics
ALTER FOREIGN TABLE inventory.products
  OPTIONS (analyze 'true');
ANALYZE inventory.products;
```

## mysql_fdw: Bridging MySQL and PostgreSQL

`mysql_fdw` enables PostgreSQL to query MySQL and MariaDB databases. It supports read/write operations and partial query pushdown for `WHERE` clauses.

### Installation

```bash
# Install MySQL client library
sudo apt install libmysqlclient-dev

# Clone and build
git clone https://github.com/EnterpriseDB/mysql_fdw.git
cd mysql_fdw
make USE_PGXS=1
sudo make USE_PGXS=1 install
```

### Configuration & Usage

```sql
CREATE EXTENSION mysql_fdw;

CREATE SERVER mysql_legacy
  FOREIGN DATA WRAPPER mysql_fdw
  OPTIONS (host '10.0.1.50', port '3306');

CREATE USER MAPPING FOR CURRENT_USER
  SERVER mysql_legacy
  OPTIONS (username 'reader', password 'readonly_pass');

-- Create foreign table with column mapping
CREATE FOREIGN TABLE legacy_users (
    user_id     INTEGER OPTIONS (key 'true'),
    full_name   VARCHAR(255),
    email       VARCHAR(255),
    created_at  TIMESTAMP
)
SERVER mysql_legacy
OPTIONS (dbname 'app_db', table_name 'users');

-- Cross-engine JOIN
SELECT
    u.full_name,
    p.plan_name
FROM legacy_users u
JOIN public.subscriptions p ON u.user_id = p.user_id
WHERE u.created_at > '2024-01-01';

-- Write operations
INSERT INTO legacy_users (user_id, full_name, email, created_at)
VALUES (1001, 'Jane Smith', 'jane@example.com', NOW());
```

### SSL/TLS Configuration

```sql
CREATE SERVER mysql_secure
  FOREIGN DATA WRAPPER mysql_fdw
  OPTIONS (
    host 'db.internal',
    port '3306',
    ssl_key '/etc/ssl/private/client-key.pem',
    ssl_cert '/etc/ssl/certs/client-cert.pem',
    ssl_ca '/etc/ssl/certs/ca-cert.pem',
    ssl_cipher 'ECDHE-RSA-AES256-GCM-SHA384'
  );
```

## tds_fdw: SQL Server Integration

`tds_fdw` connects PostgreSQL to Microsoft SQL Server and Sybase databases via the FreeTDS library. It's essential for organizations migrating from MSSQL to PostgreSQL or maintaining hybrid architectures.

### Installation

```bash
# Install FreeTDS
sudo apt install freetds-dev freetds-bin

# Clone and build
git clone https://github.com/tds-fdw/tds_fdw.git
cd tds_fdw
make USE_PGXS=1
sudo make USE_PGXS=1 install
```

### FreeTDS Configuration

```ini
# /etc/freetds/freetds.conf
[mssql-prod]
    host = mssql.corp.internal
    port = 1433
    tds version = 7.4
    encryption = require
    client charset = UTF-8
```

### Usage

```sql
CREATE EXTENSION tds_fdw;

CREATE SERVER mssql_server
  FOREIGN DATA WRAPPER tds_fdw
  OPTIONS (servername 'mssql-prod', database 'erp_db');

CREATE USER MAPPING FOR CURRENT_USER
  SERVER mssql_server
  OPTIONS (username 'report_user', password 'report_pass');

-- Foreign table for SQL Server data
CREATE FOREIGN TABLE erp_orders (
    id          INTEGER OPTIONS (key 'true'),
    order_date  TIMESTAMP,
    total       NUMERIC(12,2),
    status      VARCHAR(50)
)
SERVER mssql_server
OPTIONS (schema_name 'dbo', table_name 'Orders');

-- Hybrid query with data masking
SELECT
    eo.id AS erp_order_id,
    p.sku AS product_code,
    eo.total AS order_amount,
    CASE
        WHEN eo.status = 'SHIPPED' THEN 'Fulfilled'
        ELSE 'Pending'
    END AS order_status
FROM erp_orders eo
JOIN public.products p ON p.mssql_product_ref = eo.id::text
WHERE eo.order_date > CURRENT_DATE - INTERVAL '90 days';
```

## Deployment Architecture

For production deployments, consider this architecture pattern:

```
┌─────────────────────────────────────────────┐
│             Application Layer               │
│      (Connects to PostgreSQL primary)       │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│         PostgreSQL 17 (Primary)             │
│  ┌──────────────────────────────────────┐   │
│  │  postgres_fdw → Remote PG servers   │   │
│  │  mysql_fdw    → MySQL/MariaDB       │   │
│  │  tds_fdw      → MSSQL/Sybase        │   │
│  └──────────────────────────────────────┘   │
└──────┬──────────────┬──────────────┬────────┘
       │              │              │
       ▼              ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│  Remote  │  │  MySQL   │  │  MSSQL   │
│    PG    │  │  Server  │  │  Server  │
└──────────┘  └──────────┘  └──────────┘
```

## Security Best Practices

```sql
-- Use dedicated read-only users on remote servers
CREATE USER fdw_reader WITH PASSWORD 'complex-password';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO fdw_reader;

-- Limit FDW connections per server
ALTER SERVER mssql_server OPTIONS (ADD fdw_connections '5');

-- Enable query timeout
ALTER SERVER mysql_legacy OPTIONS (ADD fdw_timeout '30');

-- Use materialized views for frequently accessed remote data
CREATE MATERIALIZED VIEW mv_remote_summary AS
SELECT date_trunc('day', order_date) AS day,
       COUNT(*), SUM(total)
FROM erp_orders
GROUP BY 1;

REFRESH MATERIALIZED VIEW CONCURRENTLY mv_remote_summary;
```

## Why Self-Host Your Data Federation Layer?

Running your own data federation layer eliminates vendor lock-in for cross-database queries. Cloud providers charge premiums for cross-region or cross-engine query capabilities — AWS Athena Federated Queries costs $5 per TB scanned, and Azure Synapse Link charges per vCore-hour. Self-hosted FDWs run on your existing PostgreSQL instance at zero additional licensing cost.

Data sovereignty is equally important. When your PostgreSQL server queries a remote database, the data flows directly between the two without intermediate cloud services that can log, inspect, or throttle your queries. This is critical for GDPR compliance when personal data spans multiple database systems.

The FDW approach also simplifies migrations. Organizations moving from MSSQL to PostgreSQL can use tds_fdw to keep the old system accessible during a phased migration — applications gradually switch to native PostgreSQL tables while still querying legacy data through foreign tables. For more on database migration strategies, see our [PostgreSQL Backup comparison guide](../pgbackrest-vs-barman-vs-wal-g-self-hosted-postgresql-backup-guide-2026/). Our [PostgreSQL vs MySQL comparison](../postgresql-vs-mysql-mariadb-database-comparison-guide/) covers when each engine is the right choice, and our [PostgreSQL Log Analysis guide](../2026-06-02-postgresql-log-analysis-pgbadger-pgstatstatements-csv-guide/) covers query performance diagnostics.

## FAQ

### What's the performance overhead of FDW queries?

FDWs add network latency overhead. For a remote row count query, expect 2-5ms added latency on local networks. Query pushdown dramatically reduces this — with postgres_fdw pushing down a `WHERE` clause, only matching rows transfer over the network. Without pushdown, the entire table scans locally. Always run `EXPLAIN (ANALYZE, VERBOSE)` to verify which operations are pushed to the remote server.

### Can I use FDWs in high-availability setups?

Yes. Use connection pooling (PgBouncer or Odyssey) in front of the PostgreSQL instance running FDWs. For the remote servers, specify multiple hosts using DNS load balancing or a TCP proxy like HAProxy. postgres_fdw supports `application_name` for connection identification in monitoring tools.

### How do FDWs handle data type differences?

Each FDW maps remote types to PostgreSQL types. postgres_fdw preserves types exactly since both ends are PostgreSQL. mysql_fdw maps MySQL's `DATETIME` to `TIMESTAMP`, `TINYINT` to `SMALLINT`, and `TEXT` to `TEXT`. tds_fdw maps MSSQL's `NVARCHAR` to `VARCHAR` and `MONEY` to `NUMERIC(19,4)`. Check the specific mapping in each FDW's documentation for edge cases.

### Can I combine multiple FDWs in a single query?

Yes. You can JOIN a local table, a postgres_fdw foreign table, and a mysql_fdw foreign table in one query. However, cross-FDW JOINs execute on the local PostgreSQL instance — neither foreign server can push down a JOIN involving a different FDW. For read-heavy cross-FDW queries, consider creating materialized views.

### What about JSON and NoSQL FDWs?

Beyond relational databases, PostgreSQL offers FDWs for MongoDB (`mongo_fdw`), Redis (`redis_fdw`), S3 files (`s3_fdw`), and even CSV files (`file_fdw`). The same access patterns apply — you define a foreign server, user mapping, and foreign tables, then query non-relational data with SQL.

### Are FDWs suitable for real-time applications?

For OLTP workloads requiring sub-millisecond latency, FDWs are not ideal. Each query to a foreign table involves network round trips. Use FDWs for reporting, analytics, ETL, and phased migrations. For real-time cross-database transactions, consider CDC (Change Data Capture) with tools like Debezium instead.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted PostgreSQL Data Federation: postgres_fdw vs mysql_fdw vs tds_fdw — Cross-Database Query Guide",
  "description": "Comprehensive guide to PostgreSQL Foreign Data Wrappers for cross-database queries: postgres_fdw, mysql_fdw, and tds_fdw. Includes Docker Compose configs, performance tuning, and security best practices.",
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
