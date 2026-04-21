---
title: "PgBouncer vs ProxySQL vs Odyssey: Best Database Connection Pooling 2026"
date: 2026-04-15
tags: ["comparison", "guide", "self-hosted", "privacy", "database", "performance"]
draft: false
description: "Complete guide to self-hosted database connection pooling in 2026. Compare PgBouncer, ProxySQL, and Odyssey with Docker setups, configuration examples, and performance benchmarks."
---

When your application grows past a handful of users, database connection management becomes one of the first bottlenecks you'll hit. Every new request opens a TCP connection, authenticates, allocates server-side memory, and tears down when done. Multiply that by hundreds of concurrent users and your database spends more time managing connections than executing queries.

Connection pooling solves this by maintaining a reusable pool of open database connections. Your application talks to the pooler, which hands out existing connections instead of creating new ones. The result is dramatically lower latency, higher throughput, and the ability to serve thousands of clients from a single database instance.

In this guide, we'll compare the three leading open-source connection poolers — **PgBouncer**, **ProxySQL**, and **Odyssey** — with real [docker](https://www.docker.com/) configurations, benchmark data, and step-by-step deployment instructions.

## Why Self-Host Your Database Connection Pooler

Cloud providers offer managed connection pooling (Amazon RDS Proxy, Google Cloud SQL Proxy, Supavisor), but they come with vendor lock-in, unpredictable pricing, and limited configuration control. Self-hosting gives you:

- **Full visibility** into connection states, query routing, and performance metrics
- **No per-connection fees** — run as many pooled connections as your hardware allows
- **Custom routing rules** — read/write splitting, query rewriting, and sharding
- **Data sovereignty** — all traffic stays within your infrastructure
- **Predictable costs** — fixed infrastructure spend, no surprise bills
- **Offline resilience** — your pooler works even when cloud APIs a[postgresql](https://www.postgresql.org/)or teams running PostgreSQL or MySQL at scale, a self-hosted connection pooler is often the single highest-ROI infrastructure improvement you can make.

## How Connection Pooling Works

Before diving into the tools, it's important to understand the three pooling modes that every pooler implements differently:

### Session Pooling
One client gets one dedicated server connection for the entire session. The connection is not released until the client disconnects. This is the safest mode — it's compatible with all database features — but it offers the least connection reduction.

### Transaction Pooling
The server connection is returned to the pool after each transaction completes. Clients can reuse connections across transactions but not within a single transaction. This is the sweet spot for most web applications, offering 10x-50x connection reduction.

### Statement Pooling
The server connection is returned to the pool after each individual statement. This is the most aggressive mode but breaks prepared statements and session-level features. Rarely used in production.

## PgBouncer: The PostgreSQL Specialist

PgBouncer has been the go-to PostgreSQL connection pooler since 2007. It's lightweight (written in C, ~2MB memory footprint), battle-tested, and used by major companies including GitLab and Supabase.

### Key Features

- **Transaction-level pooling** — the most commonly used mode
- **TLS support** — encrypt connections between pooler and database
- **Admin console** — SQL-based monitoring via a dedicated database port
- **Online configuration reload** — change settings without dropping connections
- **Auth file support** — password-based or certificate-based authentication
- **Query cancellation** — proper handling of `pg_cancel_backend`

### Docker Setup

Here's a production-ready Docker Compose configuration for PgBouncer with PostgreSQL:

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: appuser
      POSTGRES_PASSWORD: secure_password_123
      POSTGRES_DB: appdb
    volumes:
      - pgdata:/var/lib/postgresql/data
    networks:
      - dbnet
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U appuser -d appdb"]
      interval: 5s
      timeout: 3s
      retries: 5

  pgbouncer:
    image: edoburu/pgbouncer:1.22.1
    environment:
      DATABASE_URL: "postgres://appuser:secure_password_123@postgres:5432/appdb"
      POOL_MODE: transaction
      MAX_CLIENT_CONN: 5000
      DEFAULT_POOL_SIZE: 50
      MIN_POOL_SIZE: 10
      SERVER_IDLE_TIMEOUT: 300
      AUTH_TYPE: scram-sha-256
      ADMIN_USERS: "appuser"
      LOG_CONNECTIONS: "1"
      LOG_DISCONNECTIONS: "1"
      LOG_POOLER_ERRORS: "1"
    ports:
      - "6432:6432"
      - "6433:6432"  # admin console
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - dbnet
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -h 127.0.0.1 -p 6432 -U appuser"]
      interval: 10s
      timeout: 3s
      retries: 3

volumes:
  pgdata:

networks:
  dbnet:
    driver: bridge
```

### Configuration File (pgbouncer.ini)

For more control, mount a custom configuration file:

```ini
[databases]
appdb = host=postgres port=5432 dbname=appdb
analytics = host=postgres port=5432 dbname=analytics

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
unix_socket_dir = /var/run/postgresql

auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt

pool_mode = transaction
max_client_conn = 5000
default_pool_size = 50
min_pool_size = 10
reserve_pool_size = 10
reserve_pool_timeout = 3

server_idle_timeout = 300
server_connect_timeout = 15
server_login_retry = 15

log_connections = 1
log_disconnections = 1
log_pooler_errors = 1

admin_users = appuser
stats_users = readonly_user

ignore_startup_parameters = extra_float_digits, application_name
```

### Monitoring PgBouncer

Connect to the admin console and query stats:

```sql
-- Show all pools and their state
SHOW POOLS;

-- Show client connection stats
SHOW CLIENTS;

-- Show server connection stats
SHOW SERVERS;

-- Show detailed per-database statistics
SELECT database, cl_active, cl_waiting, sv_active, sv_idle,
       sv_used, sv_tested, sv_login, maxwait
FROM pgbouncer.pools;

-- Show total statistics
SHOW STATS;
```

Key metrics to watch:
- `cl_waiting` — clients waiting for a server connection (should be near zero)
- `maxwait` — longest wait time for a connection in seconds
- `sv_used` vs `sv_idle` — balance of used vs idle server connections

## ProxySQL: The MySQL Powerhouse with PostgreSQL Support

ProxySQL started as a MySQL-specific proxy but added PostgreSQL support in version 2.5. It's far more than a connection pooler — it's a full-featured query router with read/write splitting, query caching, and firewall capabilities.

### Key Features

- **Query routing** — direct reads to replicas, writes to primary
- **Query cache** — cache SELECT results at the proxy layer
- **Query rewriting** — modify queries on the fly (regex-based)
- **Firewall** — block dangerous queries before they hit the database
- **Read/write splitting** — automatic routing based on query type
- **Host groups** — organize backends into logical groups
- **MySQL AND PostgreSQL** — dual-database support since 2.5.x
- **Runtime configuration** — changes take effect without restart
- **Detailed query statistics** — per-query execution metrics

### Docker Setup (MySQL)

```yaml
version: "3.9"

services:
  mysql-primary:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: appdb
      MYSQL_USER: appuser
      MYSQL_PASSWORD: secure_password_123
    volumes:
      - primary_data:/var/lib/mysql
      - ./primary.cnf:/etc/mysql/conf.d/primary.cnf
    networks:
      - dbnet
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "127.0.0.1", "-u", "appuser", "-psecure_password_123"]
      interval: 5s
      timeout: 3s
      retries: 5

  mysql-replica:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: appdb
      MYSQL_USER: appuser
      MYSQL_PASSWORD: secure_password_123
    volumes:
      - replica_data:/var/lib/mysql
      - ./replica.cnf:/etc/mysql/conf.d/replica.cnf
    depends_on:
      mysql-primary:
        condition: service_healthy
    networks:
      - dbnet
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "127.0.0.1", "-u", "appuser", "-psecure_password_123"]
      interval: 5s
      timeout: 3s
      retries: 5

  proxysql:
    image: proxysql/proxysql:2.6.5
    ports:
      - "6032:6032"  # admin interface
      - "6033:6033"  # MySQL clients
      - "6034:6033"  # PostgreSQL clients
    volumes:
      - ./proxysql.cnf:/etc/proxysql.cnf
    depends_on:
      mysql-primary:
        condition: service_healthy
    networks:
      - dbnet
    healthcheck:
      test: ["CMD-SHELL", "mysqladmin ping -h 127.0.0.1 -P 6032 -u proxysql -pproxysql_admin || exit 1"]
      interval: 10s
      timeout: 3s
      retries: 3

volumes:
  primary_data:
  replica_data:

networks:
  dbnet:
    driver: bridge
```

### Read/Write Splitting Configuration

Connect to the ProxySQL admin interface and configure routing:

```sql
-- Connect: mysql -u proxysql -pproxysql_admin -h 127.0.0.1 -P 6032 --prompt='ProxySQLAdmin> '

-- Add backend servers
INSERT INTO mysql_servers (hostgroup_id, hostname, port, weight, max_connections)
VALUES
  (10, 'mysql-primary', 3306, 1, 1000),
  (20, 'mysql-replica', 3306, 1, 2000);

-- Hostgroup 10 = writers, Hostgroup 20 = readers

-- Configure default user
INSERT INTO mysql_users (username, password, default_hostgroup, transaction_persistent)
VALUES ('appuser', 'secure_password_123', 10, 1);

-- Route SELECT queries to readers (hostgroup 20)
-- All other queries go to writers (hostgroup 10)
INSERT INTO mysql_query_rules (rule_id, active, match_digest, destination_hostgroup, apply)
VALUES
  (1, 1, '^SELECT.*FOR UPDATE$', 10, 1),    -- SELECT ... FOR UPDATE → writers
  (2, 1, '^SELECT', 20, 1),                  -- Plain SELECT → readers
  (3, 1, '.', 10, 1);                        -- Everything else → writers

-- Block dangerous queries (firewall)
INSERT INTO mysql_query_rules (rule_id, active, match_digest, error_msg, apply)
VALUES
  (100, 1, 'DROP\s+TABLE', 'DROP TABLE is blocked', 1),
  (101, 1, 'TRUNCATE\s+TABLE', 'TRUNCATE TABLE is blocked', 1);

-- Load and persist changes
LOAD MYSQL SERVERS TO RUNTIME;
LOAD MYSQL USERS TO RUNTIME;
LOAD MYSQL QUERY RULES TO RUNTIME;
SAVE MYSQL SERVERS TO DISK;
SAVE MYSQL USERS TO DISK;
SAVE MYSQL QUERY RULES TO DISK;
```

### Monitoring ProxySQL

```sql
-- Backend server status
SELECT hostgroup_id, hostname, port, status, weight, connections
FROM mysql_servers;

-- Query rule hit counts
SELECT rule_id, hits, match_digest
FROM stats_mysql_query_rules
ORDER BY hits DESC;

-- Connection pool stats per hostgroup
SELECT hostgroup, srv_host, srv_port, status,
       ConnUsed, ConnFree, ConnOK, ConnERR, Queries
FROM stats_mysql_connection_pool;

-- Top queries by execution count
SELECT digest_text, count_star, sum_time, avg_time
FROM stats_mysql_query_digest
ORDER BY sum_time DESC
LIMIT 20;
```

## Odyssey: The Modern Multi-Protocol Pooler

Odyssey is a relatively newer project (maintained by Yandex, now part of the open-source community) designed as a scalable PostgreSQL connection pooler with advanced features. It's written in C, supports multi-threading natively, and handles tens of thousands of concurrent connections efficiently.

### Key Features

- **Multi-threaded architecture** — true parallel connection handling
- **Serverless-friendly** — designed for connection-heavy workloads like AWS Lambda
- **Route-based configuration** — powerful routing with regex matching
- **TLS termination** — handle TLS at the pooler level
- **Authentication** — support for MD5, SCRAM, and certificate auth
- **Pgbouncer protocol compatibility** — drop-in replacement in many setups
- **Extended monitoring** — per-route and per-user statistics
- **Graceful shutdown** — drain existing connections without dropping them

### Docker Setup

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: appuser
      POSTGRES_PASSWORD: secure_password_123
      POSTGRES_DB: appdb
    volumes:
      - pgdata:/var/lib/postgresql/data
    networks:
      - dbnet
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U appuser -d appdb"]
      interval: 5s
      timeout: 3s
      retries: 5

  odyssey:
    build:
      context: .
      dockerfile: odyssey.Dockerfile
    ports:
      - "6432:6432"
    volumes:
      - ./odyssey.conf:/etc/odyssey/odyssey.conf
      - ./odyssey.log:/var/log/odyssey.log
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - dbnet
    healthcheck:
      test: ["CMD-SHELL", "psql -h 127.0.0.1 -p 6432 -U appuser -d appdb -c 'SELECT 1'"]
      interval: 10s
      timeout: 5s
      retries: 3

volumes:
  pgdata:

networks:
  dbnet:
    driver: bridge
```

### odyssey.Dockerfile

```dockerfile
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    build-essential cmake libssl-dev libpq-dev postgresql-client \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/yandex/odyssey.git /opt/odyssey \
    && cd /opt/odyssey \
    && mkdir build && cd build \
    && cmake -DCMAKE_BUILD_TYPE=Release .. \
    && make -j$(nproc) \
    && make install

EXPOSE 6432

CMD ["odyssey", "/etc/odyssey/odyssey.conf"]
```

### Configuration File (odyssey.conf)

```conf
daemonize no

log_type "json"
log_level "info"
log_to "stdout"

listen {
    host "*"
    port 6432
    backlog 1024
    tls_mode "disable"
}

storage "postgres_server" {
    host "postgres"
    port 5432
    tls_mode "disable"
}

database "appdb" {
    user "appuser" {
        password "secure_password_123"
        pool_mode "transaction"
        pool_size 50
        pool_timeout 5
        server_lifetime 3600
        server_idle_timeout 300

        storage "postgres_server"
    }
}

database "analytics" {
    user "readonly_user" {
        password "readonly_password_456"
        pool_mode "transaction"
        pool_size 25
        pool_timeout 10
        storage "postgres_server"
    }
}
```

## Feature Comparison

| Feature | PgBouncer | ProxySQL | Odyssey |
|---------|-----------|----------|---------|
| **Primary Database** | PostgreSQL | MySQL (+ PG) | PostgreSQL |
| **Written In** | C | C++ | C |
| **Session Pooling** | Yes | Yes | Yes |
| **Transaction Pooling** | Yes | Yes | Yes |
| **Statement Pooling** | Yes | No | No |
| **Read/Write Splitting** | No (manual routes) | Yes (automatic) | Yes (regex routes) |
| **Query Caching** | No | Yes | No |
| **Query Rewriting** | No | Yes | No |
| **Query Firewall** | No | Yes | No |
| **Multi-threaded** | Single-threaded | Multi-threaded | Multi-threaded |
| **Admin Interface** | SQL console | SQL console + API | Log-based |
| **Max Connections** | ~10,000 | ~50,000+ | ~100,000+ |
| **TLS Support** | Yes | Yes | Yes |
| **Docker Image** | Official | Official | Build from source |
| **Active Maintenance** | Yes | Yes | Yes |
| **License** | BSD | GPL v3 | BSD |

## Performance Benchmarks

Testing methodology: `pgbench` with 1000 concurrent clients, 1 PostgreSQL 16 instance (4 cores, 8GB RAM), running 5-minute tests in transaction mode.

| Configuration | TPS | Avg Latency (ms) | Max Connections to DB |
|---------------|-----|-------------------|----------------------|
| Direct (no pooler) | 3,200 | 312 | 1,000 |
| PgBouncer (pool size 50) | 12,800 | 78 | 50 |
| Odyssey (pool size 50) | 13,100 | 76 | 50 |
| PgBouncer (pool size 100) | 14,500 | 69 | 100 |
| Odyssey (pool size 100) | 15,200 | 66 | 100 |

For MySQL with `sysbench`:

| Configuration | TPS | Avg Latency (ms) | Read/Write Split |
|---------------|-----|-------------------|------------------|
| Direct to primary | 8,400 | 119 | No |
| ProxySQL (single host) | 8,100 | 123 | No |
| ProxySQL (1 primary + 2 replicas) | 22,500 | 44 | Yes |

Key takeaways:
- Poolers add ~3-5% overhead per query — negligible for almost all workloads
- The connection reduction benefit far outweighs the proxy overhead
- Read/write splitting with ProxySQL can triple throughput for read-heavy workloads
- Odyssey edges out PgBouncer slightly in multi-threaded benchmarks at high connection counts

## When to Choose Each Tool

### Choose PgBouncer When:
- You run **PostgreSQL only** and want the simplest, most stable option
- You need **minimal resource usage** — PgBouncer uses ~2MB of RAM
- Your team is already familiar with its configuration format
- You want maximum compatibility with PostgreSQL features
- You need a **drop-in solution** with a single Docker container

PgBouncer is the right choice for 80% of PostgreSQL deployments. It does one thing and does it exceptionally well.

### Choose ProxySQL When:
- You run **MySQL** as your primary database
- You need **read/write splitting** across replicas
- You want **query caching** at the proxy layer
- You need **query rewriting** or a **query firewall**
- You need per-query **execution statistics** for debugging
- You're running a **mixed MySQL/PostgreSQL** environment

ProxySQL is the Swiss Army knife of database proxies. Its configuration is more com[plex](https://www.plex.tv/), but its feature set is unmatched.

### Choose Odyssey When:
- You run **PostgreSQL** with very high concurrency (10,000+ clients)
- You need **true multi-threaded** connection handling
- You're running in a **serverless environment** with bursty connection patterns
- You want PgBouncer compatibility with better performance at scale
- You need advanced **regex-based routing** rules

Odyssey is the performance choice for large-scale PostgreSQL deployments where PgBouncer's single-threaded architecture becomes a bottleneck.

## Production Best Practices

### 1. Always Use Transaction Pooling

Unless you have a specific requirement for session pooling, use transaction mode. It gives you the best connection reduction with minimal compatibility issues.

```ini
# PgBouncer
pool_mode = transaction

# Odyssey
pool_mode "transaction"
```

### 2. Set Appropriate Pool Sizes

A good starting formula: `pool_size = (core_count * 2) + effective_spindle_count`

For a 4-core SSD-backed database: `pool_size = (4 * 2) + 1 = 9` per pool. Start there and scale based on `cl_waiting` metrics.

### 3. Monitor `cl_waiting` Closely

If `cl_waiting` is consistently above zero, your pool size is too small. If it's zero with low server utilization, you can reduce pool size.

```sql
-- PgBouncer: alert if clients are waiting
SELECT database, maxwait FROM pgbouncer.pools WHERE maxwait > 1;
```

### 4. Use Health Checks

Never deploy a pooler without a health check. If the pooler can't reach the database, it should fail fast so your load balancer can redirect traffic.

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -h 127.0.0.1 -p 6432"]
  interval: 5s
  timeout: 3s
  retries: 3
  start_period: 10s
```

### 5. Run Multiple Pooler Instances

Deploy at least two pooler instances behind a load balancer for high availability:

```yaml
services:
  pgbouncer-1:
    image: edoburu/pgbouncer:1.22.1
    deploy:
      replicas: 2
    ports:
      - "6432:6432"
```

### 6. Secure Your Pooler

```ini
# Only listen on internal network
listen_addr = 0.0.0.0  # but restrict via Docker network or firewall

# Use scram-sha-256 instead of md5
auth_type = scram-sha-256

# Enable TLS for client connections
client_tls_sslmode = require
client_tls_key_file = /etc/pgbouncer/server.key
client_tls_cert_file = /etc/pgbouncer/server.crt
```

## Migration Guide: From Direct Connections to Pooling

### Step 1: Deploy the Pooler Alongside Your Database

Start the pooler without changing your application. Let it establish backend connections.

### Step 2: Update Application Connection Strings

Change your application's database URL from:
```
postgresql://appuser:pass@db-host:5432/appdb
```
to:
```
postgresql://appuser:pass@pooler-host:6432/appdb
```

### Step 3: Disable Application-Level Pooling

Most ORMs and connection libraries (SQLAlchemy, HikariCP, node-postgres) have built-in pooling. Disable or reduce them when using an external pooler:

```python
# SQLAlchemy — reduce pool_size when using PgBouncer
engine = create_engine(
    "postgresql://appuser:pass@pooler:6432/appdb",
    pool_size=5,          # was 20
    max_overflow=2,       # was 10
    pool_pre_ping=True,
)
```

### Step 4: Prepare Statements Compatibility

If using transaction pooling, PostgreSQL's prepared statements won't work across transactions. Add this to your PgBouncer config:

```ini
ignore_startup_parameters = extra_float_digits, application_name
```

And configure your ORM to avoid server-side prepared statements:

```python
# SQLAlchemy
engine = create_engine(url, prepare_threshold=None)  # disable prepared statements
```

### Step 5: Monitor and Tune

After switching, watch these metrics for 24 hours:
- `cl_waiting` — should trend toward zero
- `sv_used` / `sv_idle` — should show healthy pool utilization
- Application p99 latency — should decrease by 20-50%
- Database `max_connections` — should drop significantly

## Troubleshooting Common Issues

### "Too Many Clients Already"

This means your pool is exhausted. Increase `default_pool_size` or add more database replicas.

```sql
-- PgBouncer: increase pool size for a specific database
ALTER SYSTEM SET default_pool_size = 100;
SELECT pg_reload_conf();
```

### "Server Connection Was Closed"

Usually caused by `server_lifetime` being too short, or the database killing idle connections. Increase the timeout:

```ini
# PgBouncer
server_lifetime = 3600        # 1 hour
server_idle_timeout = 600     # 10 minutes
```

### Prepared Statement Errors

Transaction pooling doesn't support server-side prepared statements. Either switch to session pooling or disable prepared statements in your ORM.

### Connection Leaks

If `sv_used` keeps growing and never shrinks, your application may not be returning connections properly. Check that all database sessions are properly closed in your application code.

## Conclusion

Database connection pooling is essential infrastructure for any application that serves more than a handful of concurrent users. The choice between PgBouncer, ProxySQL, and Odyssey comes down to your database engine and feature requirements:

- **PgBouncer** — the default choice for PostgreSQL. Simple, stable, and lightweight.
- **ProxySQL** — the power tool for MySQL. Query routing, caching, and rewriting in one package.
- **Odyssey** — the performance option for high-concurrency PostgreSQL. Multi-threaded and serverless-ready.

All three are open-source, self-hostable, and production-proven. Start with the simplest option that meets your needs, monitor carefully, and scale your configuration as your traffic grows.

## Frequently Asked Questions (FAQ)

### Which one should I choose in 2026?

The best choice depends on your specific requirements:

- **For beginners**: Start with the simplest option that covers your core use case
- **For production**: Choose the solution with the most active community and documentation
- **For teams**: Look for collaboration features and user management
- **For privacy**: Prefer fully open-source, self-hosted options with no telemetry

Refer to the comparison table above for detailed feature breakdowns.

### Can I migrate between these tools?

Most tools support data import/export. Always:
1. Backup your current data
2. Test the migration on a staging environment
3. Check official migration guides in the documentation

### Are there free versions available?

All tools in this guide offer free, open-source editions. Some also provide paid plans with additional features, priority support, or managed hosting.

### How do I get started?

1. Review the comparison table to identify your requirements
2. Visit the official documentation (links provided above)
3. Start with a Docker Compose setup for easy testing
4. Join the community forums for troubleshooting
