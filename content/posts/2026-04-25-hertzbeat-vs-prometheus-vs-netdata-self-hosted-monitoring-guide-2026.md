---
title: "HertzBeat vs Prometheus vs Netdata: Self-Hosted Monitoring Guide 2026"
date: 2026-04-25
tags: ["comparison", "guide", "self-hosted", "monitoring", "observability"]
draft: false
description: "Compare HertzBeat, Prometheus, and Netdata for self-hosted infrastructure monitoring. Learn how to deploy each with Docker, configure alerts, and choose the right observability stack for your stack in 2026."
---

When it comes to self-hosted infrastructure monitoring, the landscape has grown well beyond simple uptime pings and CPU graphs. Modern teams need agentless discovery, multi-protocol metric collection, real-time alerting, and unified dashboards — all without shipping telemetry to a third-party cloud. Three tools dominate this space today, each with a fundamentally different philosophy: **HertzBeat**, an agentless multi-protocol observability system; **Prometheus**, the cloud-native pull-based metrics standard; and **Netdata**, a real-time per-second monitoring agent with instant dashboards.

This guide compares all three in depth, provides Docker deployment configurations fetched from official repositories, and helps you choose the right tool for your infrastructure.

## Why Self-Host Your Monitoring Stack

Running your own monitoring server gives you complete control over data retention, alert routing, and dashboard customization. Self-hosted monitoring avoids vendor lock-in, eliminates per-host pricing, and keeps sensitive infrastructure metrics inside your network. For teams managing dozens of servers, databases, and microservices, a self-hosted observability platform pays for itself quickly.

For related background on setting up monitoring infrastructure, see our [Prometheus vs Grafana vs VictoriaMetrics comparison](../prometheus-vs-grafana-vs-victoriametrics/) and [Nagios vs Icinga vs Cacti infrastructure monitoring guide](../nagios-vs-icinga-vs-cacti-self-hosted-infrastructure-monitoring-guide-2026/).

## HertzBeat: Agentless Multi-Protocol Monitoring

[HertzBeat](https://github.com/dromara/hertzbeat) (7,100+ GitHub stars) is an open-source, real-time observability system developed under the Apache Software Foundation's Dromara project. Its standout feature is **zero-agent monitoring** — it connects to targets over standard protocols (HTTP, SSH, JDBC, SNMP, JMX, Redis, MongoDB, and 100+ others) without installing anything on the monitored host.

**Key features:**

- **Agentless architecture** — No daemons or exporters needed on target systems
- **100+ built-in monitoring templates** — Pre-configured for MySQL, PostgreSQL, Redis, Elasticsearch, Nginx, Docker, Kubernetes, and more
- **Multi-protocol support** — HTTP, ICMP, SSH, TELNET, JDBC, SNMP, JMX, POP3, IMAP, SMTP, FTP, WebSocket, gRPC
- **Custom threshold alerts** — Email, DingTalk, WeChat, Slack, Telegram, Discord, Webhook, SMS
- **Multi-tenant and multi-language** — English, Chinese, Japanese support out of the box
- **Apache 2.0 licensed** — Enterprise-friendly

**Architecture:** HertzBeat consists of three main components:
- **Manager** — Web UI and REST API for configuration and dashboard management
- **Collector** — Distributed metric collection engine (can be deployed on multiple nodes)
- **Warehouse** — Metrics storage (supports MySQL, PostgreSQL, TDengine, VictoriaMetrics, GreptimeDB)

## Prometheus: Cloud-Native Pull-Based Metrics

[Prometheus](https://github.com/prometheus/prometheus) (63,700+ GitHub stars) is the de facto standard for cloud-native monitoring, originally built at SoundCloud and now a CNCF graduated project. It uses a **pull-based model** where the server scrapes metrics from endpoints at regular intervals.

**Key features:**

- **Pull-based scraping** — Server initiates connections to exporters
- **PromQL query language** — Powerful time-series query and aggregation
- **Service discovery** — Kubernetes, EC2, DNS, Consul, and static configs
- **Alertmanager** — Dedicated alerting component with deduplication and grouping
- **Huge ecosystem** — Thousands of exporters for virtually every service
- **CNCF graduated** — Production-proven at scale

**Architecture:** Prometheus follows a modular design:
- **Prometheus Server** — Scrapes and stores time-series data
- **Exporters** — HTTP endpoints exposing metrics (Node Exporter, Blackbox Exporter, etc.)
- **Alertmanager** — Handles alerts, routing, deduplication, and notification
- **Pushgateway** — Accepts metrics from short-lived jobs that can't be scraped

## Netdata: Real-Time Per-Second Monitoring

[Netdata](https://github.com/netdata/netdata) (78,600+ GitHub stars) is a distributed, real-time monitoring platform that collects metrics at **one-second granularity** with zero configuration. Each Netdata agent acts as both a collector and a dashboard, with an optional central cloud for multi-node aggregation.

**Key features:**

- **1-second granularity** — Real-time metrics with sub-second resolution
- **Zero configuration** — Auto-detects services and starts collecting immediately
- **400+ collectors** — Built-in modules for system, container, database, and application metrics
- **Instant dashboards** — Beautiful, responsive web UI on every node
- **Low resource footprint** — Typically uses 1-3% CPU and ~150MB RAM per node
- **Anomaly detection** — Built-in ML-based anomaly detection for each metric

**Architecture:** Netdata uses a distributed agent model:
- **Netdata Agent** — Runs on each node, collecting and serving metrics locally
- **Netdata Cloud** (optional) — Central aggregation, alerting, and multi-node dashboards
- **Parent-Child streaming** — Child nodes stream metrics to parent nodes for aggregation

## Feature Comparison Table

| Feature | HertzBeat | Prometheus | Netdata |
|---------|-----------|------------|---------|
| **Monitoring Model** | Agentless polling | Pull-based scraping | Agent-based collection |
| **Granularity** | Configurable (default 60s) | Configurable (default 15s) | 1 second |
| **Setup Complexity** | Low — web UI configuration | Medium — requires exporter setup | Minimal — auto-detection |
| **Protocols** | 100+ built-in templates | HTTP/metrics endpoint | 400+ collectors |
| **Storage** | MySQL/PostgreSQL/TDengine/VM | Local TSDB (WAL-based) | SQLite/Tiered storage |
| **Query Language** | SQL-based via API | PromQL | SQL-like (Netdata queries) |
| **Alerting** | Built-in, multi-channel | Alertmanager (separate) | Built-in health checks |
| **Dashboards** | Web UI with templates | Grafana (external) | Built-in per-node UI |
| **Resource Usage** | ~500MB RAM (Java) | ~200MB RAM (Go) | ~150MB RAM (C) |
| **Language** | Java | Go | C |
| **License** | Apache 2.0 | Apache 2.0 | GPL 3.0 |
| **Distributed Collectors** | Yes (native) | Federation/Remote Write | Parent-Child streaming |
| **Kubernetes Support** | Yes (via templates) | Native (first-class) | Yes (via Helm charts) |
| **GitHub Stars** | 7,100+ | 63,700+ | 78,600+ |

## When to Choose Each Tool

**Choose HertzBeat when:**
- You want agentless monitoring across diverse infrastructure types
- Your team prefers GUI-based configuration over YAML files
- You need to monitor legacy systems where installing agents isn't feasible
- You want out-of-the-box templates for databases, APIs, and network devices
- Multi-tenant monitoring is a requirement

**Choose Prometheus when:**
- You run Kubernetes or cloud-native infrastructure
- Your team already uses Grafana for dashboards
- You need the industry-standard time-series database
- Service discovery and dynamic target management are critical
- You want the largest community and exporter ecosystem

**Choose Netdata when:**
- You need real-time (per-second) metrics for troubleshooting
- You want zero-configuration monitoring that works immediately
- You have many heterogeneous servers and need uniform monitoring
- Anomaly detection without manual threshold tuning is important
- Per-node standalone dashboards are preferred over centralized ones

For teams managing complex endpoint monitoring scenarios, combining HertzBeat with dedicated endpoint checkers is also effective — see our [Gatus vs Blackbox Exporter vs Smokeping guide](../gatus-vs-blackbox-exporter-vs-smokeping-self-hosted-endpoint-monitoring-2026/) for complementary tools.

## Docker Deployment: HertzBeat

HertzBeat requires a database and a time-series backend. The official Docker Compose configuration uses MariaDB for metadata and VictoriaMetrics for time-series storage. Here is the production-ready setup fetched from the [official HertzBeat repository](https://github.com/dromara/hertzbeat):

```yaml
version: "3.7"

networks:
  hertzbeat:
    driver: bridge

services:
  mysql:
    image: mariadb:11.7
    container_name: hertzbeat-mysql
    restart: always
    healthcheck:
      test: ["CMD", "healthcheck.sh", "--connect", "--innodb_initialized"]
      interval: 10s
      retries: 5
      start_period: 30s
    ports:
      - '13306:3306'
    environment:
      MARIADB_ROOT_PASSWORD: hertzbeat-secret
    volumes:
      - mysql-data:/var/lib/mysql/
    networks:
      - hertzbeat

  victoria-metrics:
    image: victoriametrics/victoria-metrics:v1.95.1
    container_name: hertzbeat-vm
    restart: always
    healthcheck:
      test: ["CMD", "wget", "-q", "-O", "-", "http://victoria-metrics:8428/-/healthy"]
      interval: 10s
      retries: 5
      timeout: 5s
      start_period: 30s
    ports:
      - "18428:8428"
    volumes:
      - vm-data:/victoria-metrics-data
    networks:
      - hertzbeat

  hertzbeat:
    image: apache/hertzbeat:1.8.0
    container_name: hertzbeat
    restart: always
    environment:
      HERTZBEAT_COLLECTOR_MYSQL_QUERY_ENGINE: auto
      LANG: en_US.UTF-8
    depends_on:
      mysql:
        condition: service_healthy
      victoria-metrics:
        condition: service_healthy
    volumes:
      - ./conf/application.yml:/opt/hertzbeat/config/application.yml
      - ./conf/sureness.yml:/opt/hertzbeat/config/sureness.yml
      - ./logs:/opt/hertzbeat/logs
    ports:
      - "1157:1157"
      - "1158:1158"
    networks:
      - hertzbeat

volumes:
  mysql-data:
  vm-data:
```

Deploy with:

```bash
mkdir -p conf logs
# Copy your application.yml and sureness.yml into conf/
docker compose up -d
```

Access the web UI at `http://your-server:1157`. Default credentials are `admin/hertzbeat`.

### Quick-Start Single Container (Testing Only)

For evaluation purposes, HertzBeat can run with embedded H2 database (no external database needed):

```bash
docker run -d --name hertzbeat \
  -p 1157:1157 -p 1158:1158 \
  -v ./logs:/opt/hertzbeat/logs \
  apache/hertzbeat:1.8.0
```

## Docker Deployment: Prometheus

Prometheus is simpler to deploy since it uses a single binary with embedded storage:

```yaml
version: "3.7"

services:
  prometheus:
    image: prom/prometheus:v2.51.0
    container_name: prometheus
    restart: always
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
      - '--web.enable-lifecycle'

  node-exporter:
    image: prom/node-exporter:latest
    container_name: node-exporter
    restart: always
    pid: host
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--path.rootfs=/rootfs'

volumes:
  prometheus-data:
```

Create `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]

  - job_name: "node"
    static_configs:
      - targets: ["node-exporter:9100"]
```

Deploy with `docker compose up -d`. Access the Prometheus UI at `http://your-server:9090`.

## Docker Deployment: Netdata

Netdata runs as a single container with privileged access for full system visibility:

```yaml
version: "3.7"

services:
  netdata:
    image: netdata/netdata:latest
    container_name: netdata
    restart: always
    hostname: my-server
    cap_add:
      - SYS_PTRACE
    security_opt:
      - apparmor:unconfined
    volumes:
      - netdata-config:/etc/netdata
      - netdata-lib:/var/lib/netdata
      - netdata-cache:/var/cache/netdata
      - /etc/passwd:/host/etc/passwd:ro
      - /etc/group:/host/etc/group:ro
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /etc/os-release:/host/etc/os-release:ro
      - /var/log:/host/var/log:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    ports:
      - "19999:19999"
    environment:
      - DOCKER_HOST=unix:///var/run/docker.sock

volumes:
  netdata-config:
  netdata-lib:
  netdata-cache:
```

Deploy with `docker compose up -d`. Access the Netdata dashboard at `http://your-server:19999`. No configuration is required — Netdata auto-detects services immediately.

## Configuration & Alert Setup

### HertzBeat Alert Configuration

HertzBeat supports multiple alert channels configured through its web UI or API. Here is an example webhook alert configuration via the REST API:

```bash
# Create a webhook alert channel
curl -X POST http://localhost:1157/api/alert/define \
  -H "Content-Type: application/json" \
  -d '{
    "name": "High CPU Alert",
    "monitorId": "your-monitor-id",
    "threshold": {
      "metric": "cpuUsage",
      "operator": ">",
      "threshold": "80",
      "times": 3
    },
    "noticeType": "WEBHOOK",
    "webhook": {
      "url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
      "body": "{\"text\":\"Alert: CPU > 80% on {{monitor.name}}\"}"
    }
  }'
```

### Prometheus Alertmanager Configuration

Alertmanager handles Prometheus alerts with routing, grouping, and silencing:

```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'instance']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'slack-notifications'

receivers:
  - name: 'slack-notifications'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
        channel: '#alerts'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
```

### Netdata Alert Configuration

Netdata alerts are defined in configuration files under `/etc/netdata/health.d/`. Here is a custom CPU usage alert:

```ini
# /etc/netdata/health.d/cpu.conf
template: cpu_usage_alert
      on: system.cpu
   lookup: average -1m percentage
every: 30s
    warn: $this > 75
  critical: $this > 90
    info: CPU utilization over threshold
      to: webhook
```

## Performance and Resource Comparison

| Metric | HertzBeat | Prometheus | Netdata |
|--------|-----------|------------|---------|
| **Idle RAM** | ~500 MB | ~200 MB | ~150 MB |
| **CPU (idle)** | ~0.5% | ~0.2% | ~0.3% |
| **100 Monitors** | ~800 MB | ~400 MB | ~250 MB |
| **1000 Monitors** | ~1.5 GB | ~1.2 GB | N/A (distributed) |
| **Storage/day (100 targets)** | ~200 MB (MySQL + VM) | ~500 MB (TSDB) | ~1 GB (compressed) |
| **Startup Time** | ~15 seconds | ~3 seconds | ~5 seconds |

Netdata's distributed architecture means resource usage scales linearly per node rather than centrally. Prometheus storage growth depends heavily on scrape interval and cardinality. HertzBeat storage is efficient when paired with VictoriaMetrics or TDengine.

## FAQ

### Is HertzBeat really agentless?

Yes. HertzBeat connects to targets using standard protocols (HTTP, SSH, JDBC, SNMP, JMX, etc.) without requiring any software installation on the monitored host. This is its primary differentiator from Prometheus (which needs exporters) and Netdata (which requires an agent on each node).

### Can I use HertzBeat with VictoriaMetrics for long-term storage?

Yes. HertzBeat officially supports VictoriaMetrics as a metrics backend. The Docker Compose configuration in this guide pairs HertzBeat with VictoriaMetrics for time-series storage and MariaDB for configuration data. You can also use TDengine, GreptimeDB, or PostgreSQL as alternatives.

### How does Prometheus compare to Netdata for real-time troubleshooting?

Netdata excels at real-time troubleshooting with 1-second metric granularity and instant dashboards. Prometheus uses configurable scrape intervals (typically 15-60 seconds) and is better suited for trend analysis and alerting. For interactive debugging, Netdata provides faster insights. For historical analysis and alerting, Prometheus with Grafana is more powerful.

### Which tool is easiest to set up for a small team?

Netdata requires the least configuration — install the agent and it auto-detects services immediately. HertzBeat's web UI provides a GUI for adding monitors without writing YAML. Prometheus requires the most initial setup (writing scrape configs, deploying exporters) but offers the most flexibility once configured.

### Can I run multiple monitoring tools together?

Yes. A common pattern is using Netdata for per-node real-time dashboards, Prometheus for centralized metrics aggregation and alerting, and HertzBeat for agentless monitoring of external services and databases that don't support exporter installation. Each tool complements the others without conflict.

### Does HertzBeat support custom monitoring templates?

Yes. HertzBeat allows you to create custom monitoring templates using YAML definitions. You can define new protocols, metric paths, threshold rules, and alert conditions for any service that exposes data over a supported protocol. The template marketplace also provides community-contributed monitors for popular services.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "HertzBeat vs Prometheus vs Netdata: Self-Hosted Monitoring Guide 2026",
  "description": "Compare HertzBeat, Prometheus, and Netdata for self-hosted infrastructure monitoring. Learn how to deploy each with Docker, configure alerts, and choose the right observability stack.",
  "datePublished": "2026-04-25",
  "dateModified": "2026-04-25",
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
