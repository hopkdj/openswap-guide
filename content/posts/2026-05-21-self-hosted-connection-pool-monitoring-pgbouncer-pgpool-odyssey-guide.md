---
title: "Self-Hosted Database Connection Pool Monitoring: PgBouncer Exporters vs Pool Metrics Tools"
date: "2026-05-21"
tags: ["database", "monitoring", "postgresql", "performance"]
draft: false
---

Database connection pools sit between your application and the database server, managing connection lifecycle, reducing overhead, and preventing resource exhaustion. But when a pool runs out of connections or leaks them silently, the impact cascades across every service depending on that database. This guide covers the best tools for monitoring database connection pool health, with a focus on PostgreSQL connection poolers like PgBouncer, Odyssey, and PgPool-II, plus their associated monitoring exporters and metrics integrations.

## Why Connection Pool Monitoring Matters

A database connection pool is a finite resource. When applications exhaust available connections, new requests queue up — or fail entirely. Without visibility into pool utilization, you won't know you're approaching capacity until users start seeing errors. Connection pool monitoring tracks key metrics like active versus idle connections, queue depth, connection wait times, and pool exhaustion events, enabling proactive capacity planning and incident detection.

## PgBouncer Metrics Exporter

PgBouncer is the most widely used PostgreSQL connection pooler. While it exposes statistics via its admin console, Prometheus integration requires an exporter to scrape and transform those stats into time-series metrics.

### The pgbouncer_exporter

The community-maintained `pgbouncer_exporter` connects to PgBouncer's admin database and exposes Prometheus-compatible metrics:

```bash
# Install pgbouncer_exporter
go install github.com/prometheus-community/pgbouncer_exporter@latest

# Run with PgBouncer admin connection
pgbouncer_exporter   --pgbouncer.connection-string="postgres://pgbouncer:password@localhost:6432/pgbouncer?sslmode=disable"   --web.listen-address=":9127"
```

Key metrics exposed include `pgbouncer_pools_server_active`, `pgbouncer_pools_server_idle`, `pgbouncer_pools_client_waiting`, and `pgbouncer_pools_pool_mode`. The exporter polls PgBouncer's `SHOW POOLS`, `SHOW LISTS`, and `SHOW STATS` admin commands and maps them to Prometheus gauge and counter metrics.

### Prometheus Configuration

```yaml
scrape_configs:
  - job_name: pgbouncer
    static_configs:
      - targets: ["localhost:9127"]
    metrics_path: /metrics
    scrape_interval: 15s
```

### Grafana Dashboard

The exporter supports standard Grafana dashboard templates. Key panels to configure:

- **Pool utilization**: `(pgbouncer_pools_server_active / pgbouncer_pools_server_max) * 100`
- **Client wait queue depth**: `pgbouncer_pools_client_waiting`
- **Connection rate**: `rate(pgbouncer_stats_total_xact_count[5m])`
- **Average query duration**: `rate(pgbouncer_stats_total_query_time[5m]) / rate(pgbouncer_stats_total_query_count[5m])`

### Docker Compose Deployment

```yaml
services:
  pgbouncer:
    image: edoburu/pgbouncer:latest
    container_name: pgbouncer
    ports:
      - "6432:6432"
    environment:
      DATABASE_URL: "postgres://db:5432/appdb"
      ADMIN_USERS: "pgbouncer"
      AUTH_TYPE: "md5"
      POOL_MODE: "transaction"
      MAX_CLIENT_CONN: "200"
      DEFAULT_POOL_SIZE: "20"
    volumes:
      - ./pgbouncer.ini:/etc/pgbouncer/pgbouncer.ini
    restart: unless-stopped

  pgbouncer-exporter:
    image: prometheuscommunity/pgbouncer-exporter:latest
    container_name: pgbouncer-exporter
    ports:
      - "9127:9127"
    environment:
      PGBOUNCER_EXPORTER_CONNECTION_STRING: "postgres://pgbouncer:password@pgbouncer:6432/pgbouncer?sslmode=disable"
    depends_on:
      - pgbouncer
    restart: unless-stopped
```

## PgPool-II Statistics and Monitoring

PgPool-II provides connection pooling alongside load balancing and replication features. Its statistics system is built-in and accessible via SQL queries against the `pg_pool_status` and `pg_backend_status` views.

### Built-in Statistics

PgPool-II exposes pool state through its SQL interface:

```sql
-- Show pool configuration
SHOW pool_status;

-- Show active connections per node
SELECT node_id, hostname, status, role,
       pg_pool_count(node_id) AS connections
FROM pg_pool_nodes;

-- Show per-pool statistics
SELECT pool_id, backend_id, active_connections,
       idle_connections, waiting_clients
FROM pg_pool_status;
```

### Watchdog Monitoring

PgPool-II's watchdog subsystem provides cluster-level health monitoring, tracking which nodes are active, which are in standby, and detecting failover events:

```bash
# Check watchdog status
pcp_watchdog_info -h localhost -U pcp

# Monitor failover events
tail -f /var/log/pgpool/pgpool.log | grep -i failover
```

### Docker Compose Deployment

```yaml
services:
  pgpool:
    image: bitnami/pgpool:latest
    container_name: pgpool-ii
    ports:
      - "5432:5432"
      - "9898:9898"
    environment:
      PGPOOL_BACKEND_NODES: "0:postgres-primary:5432,1:postgres-standby:5432"
      PGPOOL_POSTGRES_USERNAME: postgres
      PGPOOL_POSTGRES_PASSWORD: postgres
      PGPOOL_ADMIN_USERNAME: admin
      PGPOOL_ADMIN_PASSWORD: admin
    volumes:
      - ./pgpool.conf:/opt/bitnami/pgpool/conf/pgpool.conf
    restart: unless-stopped
```

## Odyssey Proxy Monitoring

Odyssey is a scalable PostgreSQL connection pooler from Yandex, designed for high-concurrency environments. It exposes metrics via its built-in statistics interface.

### Statistics Interface

Odyssey provides real-time pool statistics through its admin console, similar to PgBouncer but with additional metrics for multi-tenant environments:

```sql
-- Connect to Odyssey admin console
psql -h localhost -p 6432 -U admin

-- Show all route statistics
SHOW STATS;

-- Show per-database pool state
SHOW DATABASES;

-- Show per-client connection details
SHOW CLIENTS;
```

### Prometheus Integration

Ododysey's metrics can be exported to Prometheus using the generic database exporter pattern, or by scraping its built-in HTTP stats endpoint (if enabled in configuration):

```ini
# odyssey.conf
storage "postgres" {
  type "remote"
  address "*"
  port 6432
}

log_stats = yes
log_format = "json"
```

The JSON-formatted stats can be piped to a log aggregator like Loki or parsed by a custom exporter for Prometheus integration.

### Docker Compose Deployment

```yaml
services:
  odyssey:
    image: yandex/odyssey:latest
    container_name: odyssey
    ports:
      - "6432:6432"
    volumes:
      - ./odyssey.conf:/etc/odyssey/odyssey.conf
    restart: unless-stopped
```

## Comparison Table

| Feature | PgBouncer + Exporter | PgPool-II | Odyssey |
|---------|---------------------|-----------|---------|
| **Native Metrics** | Admin SQL console | SQL views (SHOW pool_status) | Admin SQL + JSON logging |
| **Prometheus Exporter** | pgbouncer_exporter (official) | Custom scripts needed | Log-based or custom |
| **Pool Modes** | Session, transaction, statement | Session, transaction | Session, transaction |
| **Connection Limit** | Configurable (max_client_conn) | Configurable (num_init_children) | Configurable |
| **HA Support** | Single instance + keepalived | Built-in watchdog + failover | Single instance |
| **Load Balancing** | No | Yes (read/write split) | No |
| **Replication Aware** | No | Yes | No |
| **Multi-Tenant** | No | Limited | Yes (routes) |
| **GitHub Stars** | 700+ (exporter) | 100+ (pgpool) | 2,200+ |
| **License** | ISC | BSD | Apache 2.0 |

## Setting Up Pool Monitoring Alerts

Effective connection pool monitoring requires alerting on conditions that precede pool exhaustion:

```yaml
# Prometheus alerting rules for PgBouncer
groups:
  - name: connection_pool_alerts
    rules:
      - alert: PgbouncerPoolHighUtilization
        expr: (pgbouncer_pools_server_active / pgbouncer_pools_server_max) > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "PgBouncer pool {{ $labels.pool }} utilization above 80%"

      - alert: PgbouncerClientWaitQueue
        expr: pgbouncer_pools_client_waiting > 10
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "{{ $labels.client_count }} clients waiting for PgBouncer connections"

      - alert: PgbouncerPoolExhaustion
        expr: pgbouncer_pools_server_active >= pgbouncer_pools_server_max
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "PgBouncer pool {{ $labels.pool }} is fully exhausted"
```

## Why Self-Host Connection Pool Monitoring?

Self-hosted connection pool monitoring gives you full control over metric collection, retention, and alerting thresholds. When you depend on a managed database provider's built-in monitoring, you're limited by their metric granularity, alerting rules, and dashboard customization. Self-hosted monitoring with PgBouncer exporter and Prometheus lets you define custom thresholds tied to your application's SLOs, correlate pool metrics with application latency, and maintain historical data for capacity planning.

For database connection pooling fundamentals, see our [PgBouncer vs ProxySQL vs Odyssey comparison](../pgbouncer-vs-proxysql-vs-odyssey-self-hosted-database-connection-pooling-guide-2026/). For PostgreSQL performance monitoring, check our [PostgreSQL performance dashboards guide](../2026-05-13-self-hosted-postgresql-performance-dashboards-pghero-pgwatch2-guide/). For database high availability, see our [PostgreSQL HA on Kubernetes guide](../2026-05-21-self-hosted-postgresql-ha-kubernetes-stolon-spilo-patroni-guide/).

## Security Best Practices for Connection Pool Monitoring

Monitoring database connection pools introduces additional attack surfaces that require careful consideration. The metrics endpoint exposed by exporters like `pgbouncer_exporter` reveals internal connection state that could help an attacker understand your database topology and connection patterns. Always bind the metrics endpoint to a private network interface and use Prometheus mTLS authentication to scrape it.

Network-level access controls should restrict who can query the PgBouncer admin console. The admin port (6432 by default) exposes pool statistics, client lists, and server state — information that could reveal application architecture. Configure `admin_users` in PgBouncer to limit access to specific authenticated users, and use `listen_addr` to restrict the admin interface to localhost only when possible.

For PgPool-II, the PCP (PgPool Control Protocol) interface on port 9898 provides administrative access to pool configuration and statistics. Protect PCP connections with MD5 authentication and firewall rules that restrict access to monitoring hosts only. The `pcp.conf` file should contain hashed passwords for all PCP users.

Connection pool logs often contain sensitive information including SQL query patterns and client IP addresses. Configure log levels to minimize sensitive data exposure — `log_connections` and `log_disconnections` are useful for debugging but should be disabled in production unless required for compliance auditing. When logs are required, route them to a centralized log management system with appropriate access controls.

Regularly audit connection pool configurations against security baselines. Verify that `pool_mode` is set to `transaction` rather than `session` to prevent connection hijacking, that TLS is enabled for all database connections, and that password authentication is required for all clients. Automated configuration scanning tools can detect drift from approved security baselines and alert operators when unauthorized changes are made.


## FAQ

### What is the most important connection pool metric to monitor?

Pool utilization percentage — the ratio of active connections to maximum connections. When utilization consistently exceeds 80%, you should increase pool size or investigate connection leaks. A sudden spike to 100% means clients are being rejected.

### How do I detect connection leaks in a pool?

Monitor the `client_waiting` metric. If it's consistently growing while `server_active` stays constant, connections are being held open by applications and not released back to the pool. Also watch for idle connections that never return to the pool.

### What is the difference between session and transaction pool mode?

Session mode assigns a dedicated backend connection to each client for the duration of the session. Transaction mode returns the connection to the pool after each transaction completes, allowing more efficient connection reuse. Transaction mode is recommended for most web applications.

### Can I monitor connection pools without Prometheus?

Yes — PgBouncer's admin console provides real-time statistics via `SHOW POOLS`, `SHOW LISTS`, and `SHOW STATS`. PgPool-II exposes pool state through SQL views. However, without a time-series database, you lose historical trending, alerting, and dashboard capabilities.

### How many PgBouncer connections should I configure?

Start with `default_pool_size` set to 2-4x your database's `max_connections` divided by the number of application instances. Monitor utilization and adjust. A common starting point is 20-50 connections per pool for web applications.

### Does PgBouncer support connection health checks?

PgBouncer validates connections by sending a simple query when a connection is first used from the pool. The `server_check_query` and `server_check_delay` parameters control this behavior. Setting `server_check_delay` to a low value ensures stale connections are detected quickly.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Database Connection Pool Monitoring: PgBouncer Exporters vs Pool Metrics Tools",
  "description": "Monitor database connection pool health with PgBouncer Prometheus exporter, PgPool-II statistics, and Odyssey proxy metrics — including Docker Compose deployments and alerting rules.",
  "datePublished": "2026-05-21",
  "dateModified": "2026-05-21",
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
