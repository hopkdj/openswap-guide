---
title: "Self-Hosted Database Query Rewrite — pg_hint_plan vs MySQL Query Rewrite vs MaxScale Query Rewrite"
date: "2026-05-15"
tags: ["database", "query-optimization", "postgresql", "mysql", "performance-tuning"]
draft: false
---

Database query performance is one of the most common bottlenecks in production systems. Sometimes the query optimizer makes sub-optimal choices — selecting a sequential scan when an index scan would be faster, or joining tables in the wrong order. **Query rewrite tools** let you override or redirect problematic queries without modifying application code.

In this guide, we compare three self-hosted query rewrite solutions: PostgreSQL's `pg_hint_plan` extension, MySQL's built-in Query Rewrite Plugin, and MariaDB MaxScale's query rewrite filter.

## Why Query Rewrite Matters

When a database's query optimizer produces a poor execution plan, the traditional fixes are:
1. **Rewrite the application SQL** — requires code changes, testing, and deployment
2. **Add optimizer hints** — couples hints to application code
3. **Use a query rewrite layer** — intercept and modify queries transparently at the database or proxy level

Query rewrite tools solve the problem at the infrastructure level. You can redirect a poorly performing query to an optimized version, force specific index usage, or add missing `WHERE` clauses — all without touching application code.

## PostgreSQL: pg_hint_plan

`pg_hint_plan` is a PostgreSQL extension that allows you to specify optimizer hints using special comments in SQL queries. It overrides the planner's decisions for specific queries.

### Installation

```bash
# Debian/Ubuntu
sudo apt-get install postgresql-16-hintplan

# From source
git clone https://github.com/ossc-db/pg_hint_plan.git
cd pg_hint_plan
make USE_PGXS=1
sudo make USE_PGXS=1 install
```

### Configuration

```sql
-- Enable the extension in your database
CREATE EXTENSION pg_hint_plan;

-- Add to postgresql.conf
shared_preload_libraries = 'pg_hint_plan'
```

### Usage Examples

```sql
-- Force a sequential scan
/*+ SeqScan(table1) */
SELECT * FROM table1 WHERE column1 = 'value';

-- Force index scan on a specific index
/*+ IndexScan(table1 idx_column1) */
SELECT * FROM table1 WHERE column1 = 'value';

-- Specify join order
/*+ Leading(table1 table2 table3) NestLoop(table1 table2) */
SELECT * FROM table1
JOIN table2 ON table1.id = table2.ref_id
JOIN table3 ON table2.id = table3.ref_id;

-- Set parallel workers for a query
/*+ Parallel(table1 4) */
SELECT COUNT(*) FROM table1;

-- Force hash join instead of nested loop
/*+ HashJoin(table1 table2) */
SELECT * FROM table1 JOIN table2 ON table1.id = table2.id;
```

### pg_hint_plan Docker Compose

```yaml
# docker-compose-pg-hint-plan.yml
version: "3.8"
services:
  postgres:
    image: postgres:16
    container_name: postgres-hintplan
    environment:
      POSTGRES_PASSWORD: secure_password
      POSTGRES_INITDB_ARGS: "--encoding=UTF8"
    volumes:
      - pg_data:/var/lib/postgresql/data
      - ./pg_hba.conf:/etc/postgresql/pg_hba.conf
      - ./init-hintplan.sql:/docker-entrypoint-initdb.d/01-init.sql
    command: >
      postgres
      -c shared_preload_libraries=pg_hint_plan
      -c custom_variable_classes=pg_hint_plan
    ports:
      - "5432:5432"
    restart: unless-stopped

volumes:
  pg_data:
```

```sql
-- init-hintplan.sql
CREATE EXTENSION IF NOT EXISTS pg_hint_plan;
-- Enable debug mode to log which hints were applied
ALTER SYSTEM SET pg_hint_plan.debug_print = 'on';
```

## MySQL Query Rewrite Plugin

MySQL 5.7+ includes a built-in Query Rewrite Plugin that allows you to replace incoming queries with rewritten versions based on pattern matching.

### Installation

```bash
# The plugin scripts are included with MySQL installation
mysql < /usr/share/mysql/install_rewriter.sql
```

### Usage

```sql
-- Verify the plugin is active
SELECT * FROM information_schema.plugins
WHERE PLUGIN_NAME = 'rewriter';

-- Add a rewrite rule
INSERT INTO query_rewrite.rewrite_rules (pattern, replacement, pattern_database)
VALUES (
  'SELECT * FROM orders WHERE status = ?',
  'SELECT * FROM orders WHERE status = ? AND created_at > DATE_SUB(NOW(), INTERVAL 90 DAY)',
  'ecommerce'
);

-- Reload the rules into memory
CALL query_rewrite.flush_rewrite_rules();

-- View active rules
SELECT * FROM query_rewrite.rewrite_rules;
```

### Advanced Pattern Matching

```sql
-- Redirect expensive aggregation to a summary table
INSERT INTO query_rewrite.rewrite_rules (pattern, replacement, pattern_database)
VALUES (
  'SELECT COUNT(*), SUM(amount) FROM sales WHERE date >= ? AND date <= ?',
  'SELECT total_count, total_amount FROM sales_summary WHERE period_start >= ? AND period_end <= ?',
  'analytics'
);

-- Force covering index usage via hint injection
INSERT INTO query_rewrite.rewrite_rules (pattern, replacement, pattern_database)
VALUES (
  'SELECT name, email FROM users WHERE last_login > ?',
  'SELECT /*+ INDEX(users idx_last_login_name_email) */ name, email FROM users WHERE last_login > ?',
  'app'
);

CALL query_rewrite.flush_rewrite_rules();
```

### MySQL Query Rewrite Docker Compose

```yaml
# docker-compose-mysql-rewrite.yml
version: "3.8"
services:
  mysql:
    image: mysql:8.0
    container_name: mysql-rewrite
    environment:
      MYSQL_ROOT_PASSWORD: secure_password
      MYSQL_DATABASE: app
    volumes:
      - mysql_data:/var/lib/mysql
      - ./init-rewrite.sql:/docker-entrypoint-initdb.d/01-rewrite.sql
    ports:
      - "3306:3306"
    restart: unless-stopped

volumes:
  mysql_data:

# init-rewrite.sql
SOURCE /usr/share/mysql/install_rewriter.sql;
USE query_rewrite;
INSERT INTO rewrite_rules (pattern, replacement, pattern_database) VALUES
  ('SELECT * FROM users WHERE id = ?', 'SELECT id, name, email, status FROM users WHERE id = ?', 'app');
CALL flush_rewrite_rules();
```

## MariaDB MaxScale Query Rewrite

MaxScale is MariaDB's database proxy that includes a powerful query rewrite and filter module. It operates at the proxy level, making it database-agnostic.

### MaxScale Configuration

```ini
# /etc/maxscale.cnf
[maxscale]
threads=auto

[query_rewrite]
type=filter
module=queryrewrite
rules=/etc/maxscale/rewrite_rules.json

[mariadb-backend]
type=server
address=192.168.1.100
port=3306
protocol=MariaDBBackend

[query-service]
type=service
router=readconnroute
servers=mariadb-backend
user=maxscale_user
passwd=secure_password
filters=query_rewrite

[query-listener]
type=listener
service=query-service
protocol=MariaDBClient
port=4006
```

### Rewrite Rules JSON

```json
[
  {
    "match": "SELECT * FROM products WHERE category = :cat",
    "replace": "SELECT id, name, price, stock FROM products WHERE category = :cat AND active = 1",
    "replace_vars": ["cat"]
  },
  {
    "match": "SELECT COUNT(*) FROM logs WHERE timestamp > :ts",
    "replace": "SELECT COUNT(*) FROM logs WHERE timestamp > :ts AND severity >= 3",
    "replace_vars": ["ts"]
  }
]
```

### MaxScale Docker Compose

```yaml
# docker-compose-maxscale.yml
version: "3.8"
services:
  maxscale:
    image: mariadb/maxscale:23.08
    container_name: maxscale-rewrite
    volumes:
      - ./maxscale.cnf:/etc/maxscale.cnf:ro
      - ./rewrite_rules.json:/etc/maxscale/rewrite_rules.json:ro
    ports:
      - "4006:4006"
      - "8989:8989"
    restart: unless-stopped
```

## Comparison: Query Rewrite Tools

| Feature | pg_hint_plan (PostgreSQL) | MySQL Query Rewrite Plugin | MaxScale Query Rewrite |
|---------|--------------------------|---------------------------|----------------------|
| **Database** | PostgreSQL only | MySQL 5.7+ | MariaDB/MySQL/PostgreSQL |
| **Method** | SQL comment hints | Pattern-based replacement | Proxy-level rewriting |
| **No App Changes** | Partial (needs hints in SQL) | Yes (transparent) | Yes (transparent) |
| **Rule Storage** | In SQL comments | MySQL table | JSON file |
| **Hot Reloading** | Yes (per-query) | Yes (`flush_rewrite_rules()`) | Yes (`maxctrl`) |
| **Pattern Matching** | N/A (exact query) | Wildcard with `?` params | Named variables (`:var`) |
| **Performance Impact** | Minimal (planner override) | Low (pattern match per query) | Low (proxy overhead) |
| **Debug Logging** | Yes (`debug_print`) | Yes (rewritten column) | Yes (log files) |
| **Docker Support** | Community images | Official MySQL image | Official MaxScale image |
| **License** | PostgreSQL License | GPL v2 | BSL (MariaDB) |

## Choosing the Right Query Rewrite Tool

**For PostgreSQL users**, `pg_hint_plan` is the go-to solution. It provides fine-grained control over the query planner, allowing you to force specific join methods, index usage, and scan types. The main limitation is that hints must be embedded in the SQL as comments, which may require application code changes or a query-intercepting proxy.

**For MySQL users**, the built-in Query Rewrite Plugin is the simplest option. Pattern-based rules can redirect or modify any incoming query without application changes. The `?` wildcard matching makes it easy to handle parameterized queries.

**For mixed-database environments**, MaxScale provides the most flexibility. As a database proxy, it can rewrite queries for any backend database type. The named variable system (`:var`) is more expressive than MySQL's positional `?` parameters.

## Why Self-Host Query Rewrite?

**Immediate performance gains.** A single poorly optimized query can cascade into system-wide slowdowns. Query rewrite tools let you fix performance issues immediately by intercepting and optimizing problematic queries, without waiting for application deployment cycles.

**Zero-downtime optimization.** When a query plan regression occurs after a database upgrade, query rewrite provides an immediate rollback mechanism. You can redirect the affected queries back to their previous execution paths while investigating the root cause.

**Centralized query management.** Instead of scattering optimizer hints across dozens of application services, a query rewrite layer keeps all optimization rules in one place. This makes it easier to audit, version-control, and manage query performance policies.

**Testing and debugging.** Query rewrite tools allow you to experiment with different execution plans in production without modifying application code. You can force specific indexes, change join orders, or add covering index hints to measure the performance impact before making permanent changes.

For related reading, see our [database monitoring guide](../2026-04-18-pgwatch2-vs-percona-pmm-vs-pgmonitor-self-hosted-database-monitoring-guide-2026/), [PostgreSQL high availability](../patroni-vs-galera-cluster-vs-repmgr-self-hosted-database-hig/), and [connection pooler comparison](../pgbouncer-vs-proxysql-vs-odyssey-self-hosted-database-connec/).

## FAQ

### Does pg_hint_plan work with prepared statements?

Yes, `pg_hint_plan` works with prepared statements in PostgreSQL. The hint comment must appear at the beginning of the SQL text passed to `PREPARE` or `EXECUTE`. For JDBC prepared statements, the hint is included in the original SQL string before parameter substitution.

### Can MySQL Query Rewrite handle complex multi-table JOIN queries?

Yes, but pattern matching becomes more complex. The `?` wildcard matches any single token, so you need to construct the pattern to match the exact structure of the query. For very complex queries, consider using MaxScale's named variable approach which is more flexible.

### Is there a performance penalty for using query rewrite?

The overhead is minimal. `pg_hint_plan` adds negligible cost since hints are parsed during the planning phase. MySQL's Query Rewrite Plugin performs pattern matching on each incoming query, adding approximately 0.1-0.5ms per query depending on the number of active rules. MaxScale adds proxy-level latency of about 0.2ms.

### How do I audit which queries were rewritten?

For `pg_hint_plan`, enable `pg_hint_plan.debug_print = 'on'` to log hint application in PostgreSQL logs. For MySQL Query Rewrite, the `rewritten` column in `query_rewrite.rewrite_rules` shows how many times each rule matched. For MaxScale, enable query logging in the service configuration to capture rewritten queries.

### Can query rewrite fix missing index problems?

Query rewrite cannot create indexes, but it can work around missing indexes by forcing the optimizer to use alternative access paths. `pg_hint_plan` can force index scans even on suboptimal indexes, and MySQL's Query Rewrite Plugin can inject `USE INDEX` hints into the rewritten SQL. The proper fix is still to add the correct index.

### Does MaxScale Query Rewrite work with PostgreSQL backends?

Yes, MaxScale supports PostgreSQL backends through its PostgreSQL protocol module. The query rewrite filter works at the proxy level, independent of the backend protocol. This makes MaxScale the only tool in this comparison that can rewrite queries for both MySQL and PostgreSQL.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Database Query Rewrite — pg_hint_plan vs MySQL Query Rewrite vs MaxScale Query Rewrite",
  "description": "Compare database query rewrite tools: pg_hint_plan for PostgreSQL, MySQL Query Rewrite Plugin, and MariaDB MaxScale. Includes configs, Docker Compose, and deployment guides.",
  "datePublished": "2026-05-15",
  "dateModified": "2026-05-15",
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
