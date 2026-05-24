---
title: "Self-Hosted MySQL Monitoring & Observability: PMM vs mysqld_exporter vs MySQL Enterprise Monitor (2026)"
date: "2026-05-25"
tags: ["mysql", "database-monitoring", "observability", "percona", "prometheus"]
draft: false
---

MySQL powers millions of production databases worldwide, but without proper monitoring, performance degradation, slow queries, and resource exhaustion can go undetected until they cause outages. Self-hosted monitoring tools give you full control over your database observability pipeline — no data leaves your infrastructure, no subscription fees, and deep customization for your specific workload patterns.

This guide compares the leading open-source MySQL monitoring solutions: **Percona Monitoring and Management (PMM)**, **mysqld_exporter with Prometheus/Grafana**, and **MySQL Enterprise Monitor**. We'll cover deployment, features, dashboards, alerting, and which tool fits your operational needs.

## Comparison Overview

| Feature | Percona PMM | mysqld_exporter + Prometheus | MySQL Enterprise Monitor |
|---------|-------------|------------------------------|-------------------------|
| License | Apache 2.0 | Apache 2.0 / GPL | Commercial (Oracle) |
| Deployment | Docker, apt, yum | Docker, binary | Commercial installer |
| Query Analytics | Built-in (QAN) | Via custom exporters | Built-in |
| Dashboard | Pre-built Grafana | Custom Grafana | Proprietary UI |
| Alert Rules | 50+ built-in | Custom PromQL | Custom rules |
| Performance Schema | Full integration | Partial | Full integration |
| Cost | Free | Free | Paid subscription |
| GitHub Stars | 2,800+ | 2,440+ | N/A |

## Percona Monitoring and Management (PMM)

Percona PMM is the most comprehensive open-source database monitoring platform. It bundles Prometheus, Grafana, and custom exporters into a unified observability stack designed specifically for MySQL, PostgreSQL, and MongoDB.

### Key Features

- **Query Analytics (QAN)**: Visualizes slow queries, identifies top consumers of resources, and tracks query performance over time.
- **Metrics Dashboard**: Pre-built Grafana dashboards covering InnoDB buffers, replication lag, connection pools, and I/O throughput.
- **Alert Management**: 50+ built-in alert rules with configurable thresholds for CPU, memory, disk, and query metrics.
- **Performance Schema Integration**: Leverages MySQL's Performance Schema for deep query-level insights without additional instrumentation.

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  pmm-server:
    image: percona/pmm-server:2
    container_name: pmm-server
    hostname: pmm-server
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - pmm-data:/srv
    environment:
      - PERCONA_TEST_DBAAS=1
      - ENABLE_DBAAS=1
      - ENABLE_ALERTING=1

volumes:
  pmm-data:
    driver: local
```

After deployment, access the web UI at `http://your-server:80`. Register your MySQL instances using:

```bash
docker exec -it pmm-server pmm-admin add mysql --username=pmm --password=secret --query-source=perfschema my-mysql-instance 192.168.1.10:3306
```

### When to Choose PMM

- You need a turnkey monitoring solution with zero configuration
- Query-level analytics are critical for your workload
- You manage multiple database types (MySQL, PostgreSQL, MongoDB)
- You want pre-built dashboards and alert rules out of the box

## mysqld_exporter with Prometheus and Grafana

The mysqld_exporter is the official Prometheus exporter for MySQL. It scrapes Performance Schema, global status variables, and replication metrics, exposing them in Prometheus format for visualization in Grafana.

### Key Features

- **Lightweight**: Single binary with minimal resource footprint (~50MB RAM)
- **Prometheus Native**: Integrates seamlessly with existing Prometheus/Grafana stacks
- **Custom Metrics**: Collects InnoDB buffer pool stats, connection counts, query throughput, and replication status
- **Community Dashboards**: Grafana dashboard #7362 provides comprehensive MySQL visualization

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  mysqld-exporter:
    image: prom/mysqld-exporter:latest
    container_name: mysqld-exporter
    restart: unless-stopped
    ports:
      - "9104:9104"
    environment:
      - DATA_SOURCE_NAME=exporter:password@(mysql-host:3306)/
    command:
      - "--collect.info_schema.processlist"
      - "--collect.info_schema.innodb_metrics"
      - "--collect.perf_schema.eventsstatements"
      - "--collect.perf_schema.tablelocks"
      - "--collect.perf_schema.file_events"
      - "--collect.binlog_size"

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.retention.time=30d"

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

volumes:
  prometheus-data:
  grafana-data:
```

Prometheus configuration (`prometheus.yml`):

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: "mysql"
    static_configs:
      - targets: ["mysqld-exporter:9104"]
    metrics_path: "/metrics"
```

### When to Choose mysqld_exporter

- You already run Prometheus and Grafana for infrastructure monitoring
- You want a lightweight, single-purpose exporter
- You prefer building custom dashboards tailored to your specific metrics
- You need to monitor hundreds of MySQL instances with minimal overhead

## MySQL Enterprise Monitor

Oracle's MySQL Enterprise Monitor is the commercial-grade monitoring solution. It includes the MySQL Enterprise Monitor Service Manager and MySQL Enterprise Monitor Agents.

### Key Features

- **Advisors**: 100+ built-in rules covering security, performance, and availability
- **Query Analyzer**: Full query profiling with execution plan visualization
- **Event Management**: Automated alerts with escalation policies
- **Support**: Backed by Oracle's commercial support SLA

### Installation

```bash
# Download from Oracle
wget https://dev.mysql.com/get/Downloads/MySQL-Enterprise-Monitor/mysqlmonitor-8.0.36-linux-x86_64-installer.bin
chmod +x mysqlmonitor-8.0.36-linux-x86_64-installer.bin
sudo ./mysqlmonitor-8.0.36-linux-x86_64-installer.bin
```

### When to Choose MySQL Enterprise Monitor

- You have an existing Oracle support contract
- You need commercial SLA-backed monitoring
- Your compliance requirements mandate vendor-supported tooling

## Why Self-Host Your MySQL Monitoring?

Running MySQL monitoring in-house gives you direct control over data retention, alert sensitivity, and dashboard customization. When monitoring lives in your own infrastructure, query patterns and performance metrics never leave your network — a critical consideration for regulated industries like finance and healthcare.

Self-hosted solutions also eliminate per-node licensing costs. With PMM or the mysqld_exporter stack, you can monitor dozens or hundreds of MySQL instances without incremental charges. This cost efficiency scales dramatically as your fleet grows, making open-source monitoring the preferred choice for organizations managing large MySQL deployments.

The flexibility to customize alert thresholds, build workload-specific dashboards, and integrate with your existing incident management tools means your monitoring evolves alongside your application architecture. Unlike SaaS alternatives with fixed metric retention periods, self-hosted stacks let you define retention policies that match your compliance and troubleshooting requirements.

For broader database monitoring strategies, see our [PostgreSQL monitoring comparison](../2026-04-18-pgwatch2-vs-percona-pmm-vs-pgmonitor-self-hosted-database-monitoring-guide-2026/) and our [Prometheus exporter ecosystem guide](../2026-04-24-haproxy-dataplane-api-vs-prometheus-exporter-vs-runtime-api-self-hosted-haproxy-management-guide-2026/). If you're optimizing MySQL performance, our [database tuning tools comparison](../2026-05-03-self-hosted-database-tuning-mysqltuner-pgtune-pgtune-ng-guide-2026/) covers complementary profiling utilities.

## Choosing the Right MySQL Monitoring Tool

Your choice depends on operational maturity and team size. For teams starting with MySQL monitoring, PMM offers the lowest barrier to entry — deploy a single Docker container and start collecting metrics immediately. For organizations with established Prometheus infrastructure, adding mysqld_exporter is a natural extension that leverages existing Grafana dashboards and alert routing.

For enterprise environments requiring vendor accountability, MySQL Enterprise Monitor provides Oracle-backed support and a comprehensive advisor system. However, the licensing cost scales with instance count, making it less economical for large fleets.


## MySQL Monitoring Best Practices

Regardless of which monitoring tool you choose, following these best practices will ensure your MySQL observability stack catches issues before they become incidents.

**Set Baseline Metrics First**: Before configuring alerts, run your monitoring tool for at least one week to establish normal performance baselines. Query throughput, connection counts, and buffer pool hit ratios vary significantly between daytime and nighttime workloads. Setting static thresholds without baseline data leads to either alert fatigue or missed incidents.

**Monitor Replication Lag Separately**: If you run MySQL replicas, replication lag deserves its own alerting tier. A lag of 1-2 seconds is often acceptable, but spikes beyond 10 seconds indicate either network issues, heavy write loads on the primary, or resource contention on the replica. PMM includes dedicated replication lag dashboards; with mysqld_exporter, track `mysql_slave_status_seconds_behind_master` and `mysql_slave_sql_running_state`.

**Track Slow Query Trends, Not Just Counts**: A sudden increase in slow queries often precedes a full performance degradation event. Configure your monitoring to alert when the 95th percentile query execution time exceeds a threshold, rather than just counting queries that exceed `long_query_time`. This catches gradual performance degradation before users notice.

**Correlate Database Metrics with Application Metrics**: Database slowdowns often manifest as increased application response times first. Ensure your MySQL monitoring tool integrates with your APM or application-level monitoring so you can correlate slow queries with specific application endpoints, user sessions, or transaction types.

**Review and Rotate Audit Logs**: If you enable query-level auditing, audit logs grow rapidly. Configure log rotation to compress and archive logs older than 30 days, and delete logs older than your compliance-mandated retention period. Both PMM and the mysqld_exporter stack support configurable retention policies.


## FAQ

### What is the best free MySQL monitoring tool?

Percona PMM is widely considered the best free MySQL monitoring tool. It includes Query Analytics, pre-built Grafana dashboards, 50+ alert rules, and Performance Schema integration — all at no cost under the Apache 2.0 license.

### How does mysqld_exporter differ from PMM?

The mysqld_exporter is a single-purpose Prometheus exporter that collects MySQL metrics. PMM bundles the exporter (plus many others) with a Prometheus server, Grafana instance, and custom Query Analytics engine. Use mysqld_exporter if you already have Prometheus/Grafana; use PMM for a complete out-of-the-box solution.

### Can I monitor MySQL replication lag with these tools?

Yes. All three tools monitor replication metrics. PMM includes dedicated replication lag dashboards and alert rules. mysqld_exporter exposes `mysql_slave_status_seconds_behind_master` as a Prometheus metric. MySQL Enterprise Monitor provides real-time replication topology visualization.

### Do these tools support MySQL 8.0 and 8.4?

PMM supports MySQL 5.7 through 8.4. The mysqld_exporter supports MySQL 5.6 and newer. MySQL Enterprise Monitor supports all actively maintained MySQL versions including 8.0 LTS and 8.4 LTS.

### How many MySQL instances can PMM monitor?

A single PMM server can comfortably monitor 50-100 MySQL instances on standard hardware (4 CPU, 16GB RAM). For larger deployments, PMM supports horizontal scaling with additional query analysis nodes.

### Is MySQL Enterprise Monitor worth the cost?

For organizations with Oracle support contracts, the included monitoring may be cost-effective. For teams without existing contracts, PMM provides comparable functionality at zero cost, making the commercial license harder to justify unless you need vendor SLAs.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted MySQL Monitoring & Observability: PMM vs mysqld_exporter vs MySQL Enterprise Monitor (2026)",
  "description": "Compare the leading open-source MySQL monitoring solutions: Percona PMM, mysqld_exporter with Prometheus/Grafana, and MySQL Enterprise Monitor. Includes Docker Compose configs, feature comparisons, and deployment guides.",
  "datePublished": "2026-05-25",
  "dateModified": "2026-05-25",
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
