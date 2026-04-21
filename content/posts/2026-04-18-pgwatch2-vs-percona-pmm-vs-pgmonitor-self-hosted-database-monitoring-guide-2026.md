---
title: "pgWatch2 vs Percona PMM vs pgMonitor: Best Self-Hosted Database Monitoring 2026"
date: 2026-04-18
tags: ["comparison", "guide", "self-hosted", "postgresql", "monitoring", "observability"]
draft: false
description: "Compare the top self-hosted database monitoring tools — pgWatch2, Percona PMM, and pgMonitor. Deployment guides, feature comparison, and Docker configs for PostgreSQL and multi-database observability."
---

Database performance directly impacts every layer of your application stack. When queries slow down, connection pools exhaust, or replication falls behind, you need visibility — not guesswork. Self-hosted database monitoring gives you complete control over metrics, retention, and alerting without sending sensitive query data to third-party clouds.

In this guide, we compare three leading open-source solutions: **pgWatch2** (PostgreSQL-focused), **Percona Monitoring and Management** (multi-database observability), and **pgMonitor** (Crunchy Data's PostgreSQL monitoring stack). Each takes a different approach to the same problem — helping you keep your databases healthy, fast, and reliable.

For related reading, see our [PostgreSQL vs MySQL comparison](../postgresql-vs-mysql-mariadb-database-comparison-guide/) and [database benchmarking guide](../pgbench-sysbench-hammerdb-self-hosted-database-benchmarking-guide-2026/) for understanding the databases these tools monitor.

## Why Self-Host Database Monitoring

Cloud-based monitoring services like Datadog, New Relic, and AWS RDS Performance Insights are convenient, but they come with significant trade-offs:

- **Data privacy**: Query text, table names, and schema details leave your infrastructure
- **Cost at scale**: Per-host pricing escalates quickly as you add database instances
- **Vendor lock-in**: Historical metrics and dashboards are tied to the provider's platform
- **Limited retention**: Free tiers typically cap data retention at 7-14 days
- **Network dependency**: Monitoring stops working when your connection to the cloud drops

Self-hosted alternatives run entirely within your infrastructure. Your metrics never leave your servers, retention is limited only by your storage capacity, and you can customize every dashboard, alert threshold, and metric collector to your exact needs.

## pgWatch2 — PostgreSQL-Focused Metrics Dashboard

[pgWatch2](https://github.com/cybertec-postgresql/pgwatch2) is a specialized PostgreSQL monitoring solution developed by Cybertec. It collects over 100 metrics from PostgreSQL instances and presents them through Grafana dashboards backed by a metrics database (PostgreSQL, InfluxDB, or TimescaleDB).

| Attribute | Details |
|---|---|
| **GitHub Stars** | ~1,800 |
| **Primary Language** | PL/pgSQL, Go |
| **Last Updated** | December 2024 |
| **License** | Apache 2.0 |
| **Databases** | PostgreSQL only |
| **Metrics Database** | PostgreSQL, InfluxDB, TimescaleDB |
| **Dashboards** | 50+ pre-built Grafana dashboards |
| **Alerting** | Built-in alerting with multiple channels |

### Key Features

- **Zero-instrumentation monitoring**: Uses PostgreSQL's built-in statistics views (`pg_stat_statements`, `pg_stat_activity`, `pg_stat_replication`) — no agent required on monitored instances
- **Automatic discovery**: Detects new databases and tables, adjusting metric collection automatically
- **Presets**: Comes with predefined monitoring configurations (Lite, Default, Exhaustive, Dangerous) tailored to different workload types
- **Top SQL tracking**: Identifies the most resource-intensive queries with execution time, rows affected, and call frequency
- **Bloat analysis**: Monitors table and index bloat, helping you schedule timely `VACUUM` and `REINDEX` operations

### Architecture

pgWatch2 uses a daemon-based architecture:

1. **Daemon** connects to target PostgreSQL instances and collects metrics
2. **Metrics database** stores time-series data (PostgreSQL, InfluxDB, or TimescaleDB)
3. **Grafana** reads from the metrics database and renders 50+ pre-configured dashboards
4. **Web UI** provides configuration management for monitored databases and presets

### When to Choose pgWatch2

- You run **PostgreSQL exclusively** and need deep, database-specific insights
- You want a **low-overhead** monitoring solution with no agents on database servers
- You need **quick setup** — the [docker](https://www.docker.com/) Compose deployment gets you running in minutes
- Your team already uses **Grafana** and wants pre-built PostgreSQL dashboards

## Percona Monitoring and Management (PMM) — Multi-Database Observability

[Percona PMM](https://github.com/percona/pmm) is a comprehensive, open-source database monitoring platform that supports PostgreSQL, MySQL, MariaDB, MongoDB, and ProxySQL. It integrates Prometheus for metrics collection, Grafana for visualization, and includes specialized exporters for each database type.

| Attribute | Details |
|---|---|
| **GitHub Stars** | ~1,000 |
| **Primary Language** | Go |
| **Last Updated** | April 2026 (active) |
| **License** | AGPL v3 |
| **Databases** | PostgreSQL, MySQL, MariaDB, MongoDB, ProxySQL |
| **Metrics Backend** | Prometheus + VictoriaMetrics |
| **Dashboards** | 60+ pre-built Grafana dashboards |
| **Alerting** | Alertmanager with customizable rules |

### Key Features

- **Multi-database support**: Monitor PostgreSQL, MySQL, MariaDB, and MongoDB from a single dashboard
- **Query analytics**: Slow query log analysis with execution plans, latency histograms, and load profiling
- **Performance schema integration**: Deep MySQL/PostgreSQL internals visibility through `performance_schema` and `pg_stat_statements`
- **Advisors**: Built-in checks that flag security issues, misconfigurations, and performance anti-patterns
- **Custom dashboards**: Full Grafana integration for building custom visualizations
- **PMM Agent**: Lightweight Go-based agent installed on each monitored host

### Architecture

PMM uses a client-server model:

1. **PMM Server** runs Prometheus, Grafana, VictoriaMetrics, ClickHouse (for query analytics), and Alertmanager
2. **PMM Agent** runs on each monitored host, collecting OS-level metrics (CPU, memory, disk I/O, network)
3. **Exporters** (`postgresql_exporter`, `mysqld_exporter`, `mongodb_exporter`) collect database-specific metrics
4. **QAN Agent** captures and analyzes slow query logs for performance profiling

### When to Choose PMM

- You manage a **mixed database environment** (PostgreSQL + MySQL + MongoDB)
- You need **query-level analytics** with slow query profiling and execution plan analysis
- You want **Advisor checks** that automatically flag common misconfigurations
- Your team values **Percona's expertise** and enterprise-grade support options

## pgMonitor — Crunchy Data's PostgreSQL Monitoring Stack

[pgMonitor](https://github.com/CrunchyData/pgmonitor) is a collection of monitoring configurations, Grafana dashboards, and alerting rules specifically designed for PostgreSQL, maintained by Crunchy Data. Unlike pgWatch2 and PMM, pgMonitor is not a standalone application — it's a framework that configures existing open-source tools (Prometheus, Grafana, node_exporter, postgres_exporter) into a cohesive PostgreSQL monitoring stack.

| Attribute | Details |
|---|---|
| **GitHub Stars** | ~700 |
| **Primary Language** | PL/pgSQL, Shell |
| **Last Updated** | February 2026 |
| **License** | Apache 2.0 |
| **Databases** | PostgreSQL only |
| **Metrics Backend** | Prometheus |
| **Dashboards** | 20+ PostgreSQL-focused Grafana dashboards |
| **Alerting** | Prometheus Alertmanager rules |

### Key Features

- **Production-tested configurations**: Developed and refined by Crunchy Data through years of running PostgreSQL in production environments
- **Crunchy Postgres integration**: Designed to work seamlessly with Crunchy's PostgreSQL distribution and operator (PGO)
- **PostgreSQL-specific alerts**: Pre-configured Alertmanager rules for replication lag, connection exhaustion, long-running queries, and checkpoint frequency
- **Lightweight footprint**: Uses standard Prometheus exporters — no additional daemo[kubernetes](https://kubernetes.io/)ase required
- **Kubernetes-native**: Works well in containerized and Kubernetes environments
- **Modular design**: Pick and choose which components (postgres_exporter, node_exporter, pgbadger) to deploy

### Architecture

pgMonitor is a configuration framework, not a standalone application:

1. **postgres_exporter** collects PostgreSQL metrics via SQL queries
2. **node_exporter** collects OS-level metrics (CPU, memory, disk, network)
3. **Prometheus** scrapes and stores metrics with configurable retention
4. **Grafana** renders pre-configured PostgreSQL dashboards
5. **Alertmanager** sends alerts based on Crunchy Data's recommended thresholds
6. **pgBadger** provides detailed PostgreSQL log analysis reports

### When to Choose pgMonitor

- You already run **Prometheus and Grafana** in your infrastructure
- You use **Crunchy PostgreSQL** or the Crunchy PGO operator on Kubernetes
- You want a **modular, composable** monitoring stack you can customize
- Your team prefers **configuration-as-code** over GUI-based configuration

## Feature Comparison

| Feature | pgWatch2 | Percona PMM | pgMonitor |
|---|---|---|---|
| **PostgreSQL Support** | Excellent | Excellent | Excellent |
| **MySQL/MariaDB** | No | Yes | No |
| **MongoDB** | No | Yes | No |
| **ProxySQL** | No | Yes | No |
| **Zero-Agent Mode** | Yes | No (agent required) | Yes (exporters only) |
| **Query Analytics** | Top queries via pg_stat_statements | Full slow query analysis | Via pgBadger |
| **Dashboard Count** | 50+ | 60+ | 20+ |
| **Metrics Backend** | PostgreSQL/InfluxDB/TimescaleDB | Prometheus/VictoriaMetrics | Prometheus |
| **Alerting** | Built-in | Alertmanager | Alertmanager |
| **Docker Deployment** | docker-compose.yml | docker pull + volume | Manual setup |
| **Kubernetes Support** | Basic | Basic | Excellent (via PGO) |
| **Setup Com[plex](https://www.plex.tv/)ity** | Low | Medium | Medium-High |
| **Active Development** | Moderate (Dec 2024) | Very Active (Apr 2026) | Active (Feb 2026) |
| **License** | Apache 2.0 | AGPL v3 | Apache 2.0 |

## Installation & Deployment

### Deploying pgWatch2 with Docker Compose

pgWatch2 provides an official `docker-compose.yml` that deploys the full stack — PostgreSQL, the monitoring daemon, and the web UI:

```yaml
version: "3"
services:
  postgres:
    image: postgres:14
    ports:
      - "15432:5432"
    environment:
      POSTGRES_HOST_AUTH_METHOD: trust

  db-bootstrapper-configdb:
    image: cybertec/pgwatch2-db-bootstrapper:latest
    environment:
      PGHOST: postgres
      BOOTSTRAP_TYPE: configdb
      BOOTSTRAP_DATABASE: pgwatch2
      BOOTSTRAP_ADD_TEST_MONITORING_ENTRY: 1
    depends_on:
      - postgres

  db-bootstrapper-metricsdb:
    image: cybertec/pgwatch2-db-bootstrapper:latest
    environment:
      PGHOST: postgres
      BOOTSTRAP_TYPE: metricsdb
      BOOTSTRAP_DATABASE: pgwatch2_metrics
      BOOTSTRAP_METRICSDB_SCHEMA_TYPE: metric-time
    depends_on:
      - postgres

  webui:
    image: cybertec/pgwatch2-webui:latest
    ports:
      - "8080:8080"
    depends_on:
      - postgres
```

Deploy with:

```bash
git clone https://github.com/cybertec-postgresql/pgwatch2.git
cd pgwatch2
docker compose up -d
```

Access the web UI at `http://localhost:8080` to configure monitored databases and select monitoring presets.

### Deploying Percona PMM with Docker

PMM runs as a single Docker container with a persistent data volume:

```bash
# Create a persistent volume
docker volume create pmm-data

# Run PMM Server
docker run -d \
  -p 443:443 \
  --volume pmm-data:/srv \
  --name pmm-server \
  --restart always \
  percona/pmm-server:2

# Get the initial admin password
docker logs pmm-server 2>&1 | grep -i password
```

After the container starts, access the web interface at `https://localhost` and log in with the credentials from the logs. Add monitored instances through the PMM UI or CLI:

```bash
# Install pmm-admin on a monitored host
sudo apt install pmm2-client

# Connect to PMM Server
pmm-admin config --server-insecure-tls --server-url=https://admin:admin@localhost:443

# Add PostgreSQL monitoring
pmm-admin add postgresql --username=monitor --password=secret my-pg-db
```

### Deploying pgMonitor

pgMonitor requires setting up Prometheus, Grafana, and exporters manually. Here's a production-ready deployment pattern:

```bash
# Clone the pgMonitor repository
git clone https://github.com/CrunchyData/pgmonitor.git
cd pgmonitor

# Install postgres_exporter
# Download from https://github.com/prometheus-community/postgres_exporter/releases
tar xzf postgres_exporter-*.linux-amd64.tar.gz
sudo cp postgres_exporter-*.linux-amd64/postgres_exporter /usr/local/bin/

# Create a monitoring user in PostgreSQL
psql -U postgres -c "CREATE USER pgmonitor WITH PASSWORD 'secure_password';"
psql -U postgres -c "GRANT pg_monitor TO pgmonitor;"

# Start postgres_exporter with pgMonitor's queries
export DATA_SOURCE_NAME="postgresql://pgmonitor:secure_password@localhost:5432/postgres?sslmode=disable"
postgres_exporter --extend.query-path=/path/to/pgmonitor/postgres_exporter/queries.yml &

# Start Prometheus with pgMonitor's configuration
prometheus --config.file=/path/to/pgmonitor/prometheus/prometheus.yml &

# Import pgMonitor's Grafana dashboards
# Copy JSON dashboard files from pgmonitor/grafana/ to your Grafana instance
```

For Kubernetes deployments using the Crunchy PGO operator, pgMonitor configurations are applied automatically when you enable the `monitoring` section in your `PostgresCluster` resource.

## Which Tool Should You Choose?

### Choose pgWatch2 if:
- You need a **PostgreSQL-only** monitoring solution with the fastest setup time
- You want pre-built dashboards that cover **every aspect** of PostgreSQL performance
- Your team prefers a **centralized web UI** for configuring monitored databases and presets
- You value **multiple metrics backend options** (PostgreSQL, InfluxDB, or TimescaleDB)

### Choose Percona PMM if:
- You manage a **heterogeneous database fleet** (PostgreSQL + MySQL + MongoDB)
- You need **deep query analytics** with slow query profiling and execution plan analysis
- You want **Advisor checks** that proactively flag misconfigurations and security issues
- You need **OS-level monitoring** alongside database metrics in a single platform

### Choose pgMonitor if:
- You already run **Prometheus and Grafana** and want PostgreSQL-specific configurations
- You use **Crunchy PostgreSQL** or deploy databases on **Kubernetes with PGO**
- You prefer a **modular, configuration-driven** approach over an all-in-one platform
- You want alerting rules **battle-tested by Crunchy Data** in production environments

For teams looking to complete their observability stack, consider pairing your database monitoring with our [Prometheus vs Grafana vs VictoriaMetrics comparison](../prometheus-vs-grafana-vs-victoriametrics/) or the [complete observability pipeline guide](../self-hosted-opentelemetry-collector-observability-pipeline-2026/).

## FAQ

### What is the difference between pgWatch2 and pgMonitor?

pgWatch2 is a standalone monitoring application with its own daemon, web UI, and metrics database. It collects PostgreSQL metrics and presents them through Grafana dashboards with minimal configuration. pgMonitor, on the other hand, is a collection of configuration files, Grafana dashboards, and alerting rules that you apply to an existing Prometheus + Grafana stack. pgWatch2 is an all-in-one solution; pgMonitor is a configuration framework.

### Can Percona PMM monitor both PostgreSQL and MySQL?

Yes. PMM supports PostgreSQL, MySQL, MariaDB, MongoDB, and ProxySQL from a single server instance. Each database type has its own exporter and dedicated dashboards. You can add different database types to the same PMM Server and view all metrics through a unified Grafana interface.

### Does pgWatch2 require installing agents on database servers?

No. pgWatch2 uses a pull-based approach — the pgWatch2 daemon connects directly to the PostgreSQL instance and queries system views (`pg_stat_statements`, `pg_stat_activity`, etc.). This means no software installation is required on the monitored database servers, reducing the attack surface and operational overhead.

### How much overhead does database monitoring add to PostgreSQL?

The overhead is minimal. pgWatch2 and pgMonitor query PostgreSQL's built-in statistics views, which are already maintained by the database engine. Typical CPU overhead is under 1% for standard monitoring intervals (60-second collection). Query Analytics features that parse `pg_stat_statements` or slow query logs add slightly more overhead — usually 1-3% depending on query volume.

### Which tool provides the best alerting capabilities?

All three tools support alerting, but they differ in approach. pgWatch2 has built-in alerting with configurable thresholds and multiple notification channels (email, Slack, PagerDuty). PMM and pgMonitor both use Prometheus Alertmanager, which offers more advanced features like alert grouping, silencing, inhibition rules, and routing to different receivers based on severity. For teams already using Prometheus, Alertmanager provides the most flexible alerting system.

### Can I migrate from one monitoring tool to another?

Yes, but it requires reconfiguration. Since all three tools use Grafana for dashboards and Prometheus-compatible metrics exporters (except pgWatch2's optional InfluxDB backend), you can reuse some dashboard configurations. However, each tool stores metrics in different formats and uses different collection mechanisms. Plan for a parallel monitoring period where both tools run simultaneously to validate that alerts and dashboards work correctly before decommissioning the old system.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "pgWatch2 vs Percona PMM vs pgMonitor: Best Self-Hosted Database Monitoring 2026",
  "description": "Compare the top self-hosted database monitoring tools — pgWatch2, Percona PMM, and pgMonitor. Deployment guides, feature comparison, and Docker configs for PostgreSQL and multi-database observability.",
  "datePublished": "2026-04-18",
  "dateModified": "2026-04-18",
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
