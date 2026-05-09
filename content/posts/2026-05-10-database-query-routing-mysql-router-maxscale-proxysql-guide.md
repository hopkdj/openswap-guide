---
title: "Self-Hosted Database Query Routing: MySQL Router vs MariaDB MaxScale vs ProxySQL (2026)"
date: "2026-05-10"
tags: ["database", "mysql", "mariadb", "proxy", "routing", "high-availability"]
draft: false
---

Database query routing is a critical layer in any production database architecture. Unlike connection pooling, which focuses on reusing existing connections to reduce overhead, **query routing** intelligently directs individual SQL queries to the most appropriate backend server based on query type, schema, user role, or data locality. Whether you need read/write splitting for MySQL replication setups, load distribution across database nodes, or schema-aware request forwarding, a dedicated query router sits between your application and database cluster to optimize traffic flow.

This guide compares three leading open-source database query routing solutions: **MySQL Router**, **MariaDB MaxScale**, and **ProxySQL**. Each takes a different architectural approach to query routing, and the right choice depends on your database engine, routing requirements, and operational complexity tolerance.

## What Is Database Query Routing?

A database query router is a middleware component that intercepts SQL queries from application clients and forwards them to the most suitable database server. Unlike a simple load balancer that distributes connections round-robin, a query router:

- **Parses SQL queries** to determine whether they are reads or writes
- **Routes read queries** to replica servers and **write queries** to the primary
- **Filters queries** based on user permissions, schema, or regex patterns
- **Performs load balancing** across multiple backends using weighted algorithms
- **Provides failover** by detecting backend failures and rerouting traffic automatically
- **Rewrites queries** on-the-fly to optimize execution plans

This capability is essential for horizontal database scaling, as it allows applications to interact with a single endpoint while the router handles the complexity of multi-node database topologies behind the scenes.

## MySQL Router

**MySQL Router** is Oracle's official lightweight proxy for MySQL. It is included with the MySQL Server distribution and designed primarily for InnoDB Cluster deployments. MySQL Router provides automatic routing by leveraging the metadata service built into MySQL's Group Replication.

### Key Features

- **Zero-configuration bootstrapping** for InnoDB Cluster — automatically discovers topology
- **Read/write splitting** based on query type detection
- **Connection failover** with automatic reconnection to healthy nodes
- **Lightweight design** — minimal CPU and memory overhead
- **Plugin architecture** — supports REST API, HTTP, and protocol-based routing
- **Native MySQL integration** — uses the metadata server for real-time topology awareness

### Architecture

MySQL Router operates in two modes:

1. **Classic mode** (deprecated in MySQL 8.4+) — legacy protocol routing
2. **X Protocol mode** — MySQL X Protocol (mysqlx) with plugin-based routing

The router maintains a local cache of the cluster topology and refreshes it periodically from the MySQL metadata server. When a backend fails, the metadata service updates the topology, and the router adapts without requiring manual reconfiguration.

```yaml
# docker-compose.yml for MySQL Router
services:
  mysql-router:
    image: mysql/mysql-server:8.0
    container_name: mysql-router
    command:
      - mysqlrouter
      - --bootstrap=mysql-primary:3306
      - --directory=/router
      - --user=root
      - --conf-use-sockets
    ports:
      - "6446:6446"   # Read/Write port
      - "6447:6447"   # Read-Only port
    depends_on:
      - mysql-primary
    networks:
      - db-network

  mysql-primary:
    image: mysql/mysql-server:8.0
    container_name: mysql-primary
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_ROOT_HOST: '%'
    ports:
      - "3306:3306"
    networks:
      - db-network

networks:
  db-network:
    driver: bridge
```

### Installation (Native)

```bash
# Install MySQL Router on Debian/Ubuntu
sudo apt install mysql-router

# Bootstrap against an InnoDB Cluster
sudo mysqlrouter --bootstrap root@primary-host:3306   --directory /etc/mysqlrouter --user mysqlrouter

# Start the router
sudo systemctl start mysqlrouter
```

## MariaDB MaxScale

**MariaDB MaxScale** is an advanced database proxy developed by MariaDB Corporation. It goes far beyond simple query routing, offering intelligent query classification, statement-based replication filtering, and a rich plugin ecosystem that handles everything from firewalls to data masking.

### Key Features

- **Intelligent query classification** — parses SQL to identify read/write/DDL/DML
- **Read/write splitting** with configurable replication lag thresholds
- **Schema-based routing** — direct queries to different backends based on database/schema
- **Query rewriting** — modify queries on-the-fly with regex or Lua scripts
- **Built-in firewall** — block dangerous queries, enforce rate limits
- **Data masking** — redact sensitive columns in query results
- **Load balancing algorithms** — weighted round-robin, least connections, topological
- **Monitoring and alerting** — built-in health checks for all backends

### Architecture

MaxScale uses a modular plugin architecture with four component types:

| Component | Purpose | Examples |
|-----------|---------|----------|
| Protocol | Communication with clients/backends | MariaDBClient, HTTP, Cassandra |
| Service | Logical database service | ReadWriteSplit, ReadConnRoute |
| Server | Backend database connection | Individual MariaDB/MySQL nodes |
| Monitor | Health checking and topology discovery | MariaDB-Monitor, Galera-Monitor |

```yaml
# docker-compose.yml for MariaDB MaxScale
services:
  maxscale:
    image: mariadb/maxscale:latest
    container_name: maxscale
    ports:
      - "4000:4000"   # Read/Write service port
      - "4008:4008"   # REST API / Admin
      - "6603:6603"   # Monitor port
    volumes:
      - ./maxscale.cnf:/etc/maxscale.cnf.d/maxscale.cnf
    depends_on:
      - mariadb-primary
      - mariadb-replica
    networks:
      - db-network

  mariadb-primary:
    image: mariadb:11
    container_name: mariadb-primary
    environment:
      MARIADB_ROOT_PASSWORD: rootpass
      MARIADB_REPLICATION_MODE: master
      MARIADB_REPLICATION_USER: repl
      MARIADB_REPLICATION_PASSWORD: replpass
    ports:
      - "3306:3306"
    networks:
      - db-network

  mariadb-replica:
    image: mariadb:11
    container_name: mariadb-replica
    environment:
      MARIADB_ROOT_PASSWORD: rootpass
      MARIADB_REPLICATION_MODE: slave
      MARIADB_REPLICATION_USER: repl
      MARIADB_REPLICATION_PASSWORD: replpass
      MARIADB_MASTER_HOST: mariadb-primary
    depends_on:
      - mariadb-primary
    networks:
      - db-network

networks:
  db-network:
    driver: bridge
```

### MaxScale Configuration

```ini
[maxscale]
threads=auto

[MariaDB-Monitor]
type=monitor
module=mariadbmon
servers=primary,replica
user=maxscale_user
password=maxscale_pass
monitor_interval=2000

[ReadWriteSplit-Service]
type=service
router=readwritesplit
servers=primary,replica
user=maxscale_user
password=maxscale_pass
max_slave_connections=255
max_replication_lag=5s

[ReadWriteSplit-Listener]
type=listener
service=ReadWriteSplit-Service
protocol=MariaDBClient
port=4000
```

## ProxySQL

**ProxySQL** is a high-performance, open-source SQL proxy that has become one of the most popular database routing solutions. Originally designed for MySQL, it now supports Percona Server, MariaDB, and even has experimental PostgreSQL support. ProxySQL excels at query routing with its rule-based engine that matches queries against regex patterns and routes them to specific hostgroups.

### Key Features

- **Rule-based query routing** — regex matching on SQL text with priority ordering
- **Query caching** — cache frequently executed read queries at the proxy layer
- **Connection multiplexing** — decouple frontend connections from backend connections
- **Query rewrite** — transform queries before forwarding to backends
- **Query mirroring** — send copies of queries to secondary servers for testing
- **Real-time statistics** — detailed query-level metrics via admin interface
- **Dynamic configuration** — change routing rules at runtime without restart
- **Built-in connection pooling** — eliminates the need for a separate pooler

### Architecture

ProxySQL has a unique three-layer architecture:

1. **Runtime** — the active configuration used for query processing
2. **Memory** — the staging area where changes are applied before committing
3. **Disk** — the persistent SQLite database storing configuration and statistics

This design allows for zero-downtime configuration changes — you modify settings in the memory layer, test them, then push to runtime.

```yaml
# docker-compose.yml for ProxySQL
services:
  proxysql:
    image: percona/proxysql:latest
    container_name: proxysql
    ports:
      - "6032:6032"   # Admin interface
      - "6033:6033"   # MySQL client port
    volumes:
      - ./proxysql.cnf:/etc/proxysql.cnf
    environment:
      CLUSTER_NAME: proxysql-cluster
    networks:
      - db-network

  mysql-primary:
    image: mysql:8.0
    container_name: mysql-primary
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: appdb
    ports:
      - "3306:3306"
    networks:
      - db-network

  mysql-replica:
    image: mysql:8.0
    container_name: mysql-replica
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: appdb
      MYSQL_REPLICATE_FROM: mysql-primary
    depends_on:
      - mysql-primary
    networks:
      - db-network

networks:
  db-network:
    driver: bridge
```

### ProxySQL Routing Configuration

```sql
-- Connect to ProxySQL admin interface
mysql -u admin -padmin -h 127.0.0.1 -P 6032

-- Configure backend servers
INSERT INTO mysql_servers (hostgroup_id, hostname, port, weight, max_connections)
VALUES (10, 'mysql-primary', 3306, 1, 1000);
INSERT INTO mysql_servers (hostgroup_id, hostname, port, weight, max_connections)
VALUES (20, 'mysql-replica', 3306, 1, 1000);

-- Route SELECT queries to read hostgroup (20)
INSERT INTO mysql_query_rules (rule_id, active, match_pattern, destination_hostgroup, apply)
VALUES (1, 1, '^SELECT .* FOR UPDATE$', 10, 1);
INSERT INTO mysql_query_rules (rule_id, active, match_pattern, destination_hostgroup, apply)
VALUES (2, 1, '^SELECT ', 20, 1);

-- Set default hostgroup for writes
INSERT INTO mysql_users (username, password, default_hostgroup, transaction_persistent)
VALUES ('appuser', 'apppass', 10, 1);

-- Apply changes
LOAD MYSQL SERVERS TO RUNTIME;
LOAD MYSQL QUERY RULES TO RUNTIME;
LOAD MYSQL USERS TO RUNTIME;
SAVE MYSQL SERVERS TO DISK;
SAVE MYSQL QUERY RULES TO DISK;
SAVE MYSQL USERS TO DISK;
```

## Comparison Table

| Feature | MySQL Router | MariaDB MaxScale | ProxySQL |
|---------|-------------|------------------|----------|
| **Primary Use Case** | InnoDB Cluster routing | Advanced MariaDB proxy | Universal MySQL routing |
| **Query Parsing** | Basic read/write | Deep SQL analysis | Regex-based rule engine |
| **Read/Write Splitting** | Yes (automatic) | Yes (configurable) | Yes (rule-based) |
| **Query Rewriting** | No | Yes (regex + Lua) | Yes (rule-based) |
| **Query Caching** | No | No | Yes |
| **Connection Pooling** | No | Yes | Yes (built-in) |
| **Load Balancing** | Round-robin | Weighted, least-conn | Weighted, least-conn |
| **Failover** | Automatic (via metadata) | Automatic (via monitors) | Automatic (via monitors) |
| **Admin Interface** | CLI only | REST API + CLI | SQL-based admin (port 6032) |
| **Protocol Support** | MySQL classic + X Protocol | MariaDB, Cassandra, S3 | MySQL, experimental PG |
| **Configuration** | File-based + bootstrap | File-based (CNF) | Dynamic SQL commands |
| **Docker Image** | mysql/mysql-server | mariadb/maxscale | percona/proxysql |
| **GitHub Stars** | Part of MySQL (12K+) | 1,494 (MaxScale) | 6,729 (ProxySQL) |
| **License** | GPL v2 | Business Source License | GPL v3 |

## Choosing the Right Query Router

### Use MySQL Router When:
- You run an **InnoDB Cluster** with Group Replication
- You want **zero-configuration** setup with automatic topology discovery
- Your routing needs are **simple read/write splitting**
- You prefer **minimal overhead** and native MySQL integration

### Use MariaDB MaxScale When:
- You run **MariaDB** servers and want deep integration
- You need **intelligent query classification** beyond basic read/write
- You want **data masking, firewall, or query rewriting** capabilities
- You value a **rich plugin ecosystem** for extensibility

### Use ProxySQL When:
- You need **fine-grained query routing** with regex rules
- You want **query caching** at the proxy layer
- You manage **mixed MySQL/Percona/MariaDB** environments
- You need **dynamic configuration** without restarting the proxy
- You want **query mirroring** for testing or benchmarking

## Why Self-Host Your Database Query Router?

Running a query router as part of your self-hosted infrastructure gives you complete control over how database traffic is managed. When you deploy a query router on your own servers, you maintain full visibility into query patterns, routing decisions, and connection statistics — data that is invaluable for database performance tuning and capacity planning.

Self-hosting also eliminates vendor lock-in. While managed database services from cloud providers often include built-in proxy layers, they tie you to that provider's specific implementation and pricing model. With an open-source query router, you can migrate between database providers, change topologies, or adjust routing strategies without depending on any single cloud platform's proprietary tools.

For organizations running MySQL replication setups across multiple data centers, a self-hosted query router provides a single point of configuration for complex routing policies. Read queries from European users can be directed to local replicas, while write queries route to the primary in the US — all transparently handled by the router without application-level changes.

The cost savings are significant for high-traffic applications. By offloading query routing from application servers to a dedicated proxy layer, you reduce the number of database connections each application needs to maintain, lowering memory consumption on database servers and improving overall throughput. ProxySQL's query caching alone can reduce database load by 30-50% for read-heavy workloads.

For disaster recovery scenarios, having the query routing logic under your control means you can reconfigure traffic flows during an outage without waiting for support tickets or platform-specific procedures. MaxScale's monitor modules can automatically promote a replica to primary and update routing rules — a process that can be fully automated in your self-hosted environment.


## Why Self-Host Your Database Security and Routing Infrastructure?

For related reading, see our [MySQL replication topology management guide](../2026-05-09-self-hosted-mysql-replication-topology-management-orchestrator-pmm-shell-guide/) for setting up read replicas that these routers depend on. If you need database connection pooling alongside query routing, our [PgBouncer vs ProxySQL vs Odyssey comparison](../pgbouncer-vs-proxysql-vs-odyssey-self-hosted-database-connection-pooling-guide-2026/) covers complementary solutions. For horizontal database scaling, our [Vitess vs Citus vs ShardingSphere guide](../2026-04-25-vitess-vs-citus-vs-shardingsphere-self-hosted-database-sharding-guide-2026/) explores sharding strategies.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Database Query Routing: MySQL Router vs MariaDB MaxScale vs ProxySQL (2026)",
  "description": "Compare MySQL Router, MariaDB MaxScale, and ProxySQL for self-hosted database query routing. Learn read/write splitting, query caching, and failover configuration.",
  "datePublished": "2026-05-10",
  "dateModified": "2026-05-10",
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

### What is the difference between database query routing and connection pooling?

Query routing inspects and directs individual SQL queries to the most appropriate backend server, while connection pooling focuses on reusing existing database connections to reduce the overhead of establishing new ones. A query router can include connection pooling (like ProxySQL), but they solve different problems — routing optimizes *where* queries go, while pooling optimizes *how* connections are managed.

### Can ProxySQL be used with MariaDB?

Yes. ProxySQL supports Percona Server, MySQL, and MariaDB. While it was originally designed for MySQL, it works with MariaDB through the MySQL-compatible protocol. However, MariaDB-specific features like Galera Cluster monitoring may require additional configuration compared to using MaxScale, which has native MariaDB integration.

### Does MySQL Router support custom query routing rules?

No. MySQL Router is designed primarily for automatic InnoDB Cluster topology-based routing. It does not support custom regex-based query routing rules, query rewriting, or query caching. If you need fine-grained control over how specific queries are routed, MaxScale or ProxySQL are better choices.

### How does MaxScale handle replication lag in read/write splitting?

MaxScale's ReadWriteSplit router monitors replication lag on each replica through its MariaDB-Monitor module. You can configure a maximum replication lag threshold (e.g., `max_replication_lag=5s`), and MaxScale will automatically exclude replicas that exceed this threshold from receiving read queries, ensuring applications only read from sufficiently up-to-date servers.

### Can I run multiple query routers for high availability?

Yes. All three solutions support running multiple instances. MySQL Router can run in multiple instances with a load balancer in front. MaxScale and ProxySQL both support clustering configurations. ProxySQL has a native cluster sync feature that replicates configuration changes across nodes, while MaxScale supports active-passive configurations with keepalived for failover.

### Is ProxySQL's query caching compatible with MySQL 8.0?

Yes. ProxySQL's query cache operates at the proxy layer, independent of the MySQL version. It caches query results based on the query text and can serve cached responses without hitting the database. However, you need to carefully configure cache invalidation rules to avoid serving stale data for queries on frequently updated tables.

