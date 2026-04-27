---
title: "GreptimeDB vs InfluxDB vs VictoriaMetrics: Best Self-Hosted Time-Series Databases 2026"
date: 2026-04-27
tags: ["comparison", "guide", "self-hosted", "time-series", "monitoring", "metrics"]
draft: false
description: "Compare GreptimeDB, InfluxDB, and VictoriaMetrics — the top self-hosted time-series databases for metrics, logs, and observability in 2026. Includes Docker Compose configs and deployment guides."
---

Time-series databases (TSDBs) are the backbone of modern observability stacks. Whether you're tracking server metrics, application performance, IoT sensor readings, or business KPIs, you need a database optimized for timestamped data ingestion and fast range queries.

In 2026, three open-source projects dominate the self-hosted time-series database space — each with a different architectural philosophy. **GreptimeDB** (Rust-based, Observability 2.0) unifies metrics, logs, and traces into a single engine. **InfluxDB** (the veteran, now rewritten in Rust) offers a mature ecosystem with the TSM storage engine and Flux query language. **VictoriaMetrics** (Go-based) delivers extreme performance with Prometheus compatibility and minimal resource footprint.

This guide compares all three across architecture, performance, deployment, and ease of use — with real Docker Compose configurations you can deploy today.

## Why Self-Host a Time-Series Database

Cloud-hosted monitoring services are convenient, but they come with trade-offs:

- **Cost at scale**: SaaS pricing models charge per metric, per host, or per GB ingested. At 10M+ data points per day, bills become unpredictable.
- **Data sovereignty**: Regulations like GDPR, HIPAA, and industry requirements often mandate that telemetry data stays on-premises.
- **Vendor lock-in**: Migrating terabytes of time-series data between platforms is painful. Self-hosting keeps you in control.
- **Custom retention policies**: Self-hosted databases let you define granular data retention rules without paying premium tiers.

If you run more than a handful of servers, self-hosting a TSDB pays for itself within months. For self-hosted monitoring stacks that feed data into these databases, see our guides on [HertzBeat vs Prometheus vs Netdata](../hertzbeat-vs-prometheus-vs-netdata-self-hosted-monitoring-guide/) and [Nagios vs Icinga vs Cacti](../nagios-vs-icinga-vs-cacti-self-hosted-infrastructure-monitoring-guide/).

## GreptimeDB: The Rust-Based Observability 2.0 Database

[GreptimeDB](https://github.com/GreptimeTeam/greptimedb) is the newest entrant, written entirely in Rust and designed from the ground up as a unified observability platform.

| Metric | Value |
|---|---|
| GitHub Stars | 6,211+ |
| Language | Rust |
| Last Updated | April 2026 |
| License | Apache 2.0 |
| Protocols | Prometheus Remote Write, OpenTelemetry, MySQL, PostgreSQL, gRPC, HTTP |

### Architecture

GreptimeDB uses a distributed architecture with three component types:

- **Frontend**: Handles client connections and query routing (MySQL, PostgreSQL, gRPC, HTTP)
- **MetaSrv**: Cluster metadata and coordination (backed by etcd)
- **DataNode**: Stores and processes time-series data

The key differentiator is its **unified storage engine** — it accepts metrics, logs, and traces through the same ingestion pipeline, eliminating the need to run separate Prometheus, Loki, and Elasticsearch clusters.

### Standalone Deployment

For development or small-scale deployments, GreptimeDB runs as a single binary:

```bash
docker run -d \
  --name greptimedb \
  -p 4000:4000 \
  -p 4001:4001 \
  -p 4002:4002 \
  -p 4003:4003 \
  -v /tmp/greptimedb-data:/tmp/greptimedb \
  greptime/greptimedb standalone start \
  --http-addr 0.0.0.0:4000 \
  --rpc-addr 0.0.0.0:4001 \
  --mysql-addr 0.0.0.0:4002 \
  --postgres-addr 0.0.0.0:4003 \
  --data-home /tmp/greptimedb
```

This exposes:
- Port 4000: HTTP API and dashboard
- Port 4001: gRPC
- Port 4002: MySQL protocol
- Port 4003: PostgreSQL protocol

### Cluster Deployment with Docker Compose

For production, GreptimeDB uses etcd for coordination:

```yaml
services:
  etcd0:
    image: quay.io/coreos/etcd:v3.5.10
    container_name: etcd0
    ports:
      - 2379:2379
    command:
      - --name=etcd0
      - --data-dir=/var/lib/etcd
      - --initial-advertise-peer-urls=http://etcd0:2380
      - --listen-peer-urls=http://0.0.0.0:2380
      - --listen-client-urls=http://0.0.0.0:2379
      - --advertise-client-urls=http://etcd0:2379
      - --initial-cluster=etcd0=http://etcd0:2380
      - --initial-cluster-state=new
    volumes:
      - etcd-data:/var/lib/etcd
    healthcheck:
      test: ["CMD", "etcdctl", "--endpoints=http://etcd0:2379", "endpoint", "health"]
      interval: 5s
      timeout: 3s
      retries: 5

  metasrv:
    image: greptime/greptimedb:latest
    container_name: metasrv
    ports:
      - 3002:3002
      - 3000:3000
    command:
      - metasrv
      - start
      - --grpc-bind-addr=0.0.0.0:3002
      - --store-addrs=etcd0:2379
      - --http-addr=0.0.0.0:3000
    depends_on:
      etcd0:
        condition: service_healthy

  datanode:
    image: greptime/greptimedb:latest
    container_name: datanode
    ports:
      - 3001:3001
      - 5000:5000
    command:
      - datanode
      - start
      - --node-id=0
      - --data-home=/data
      - --grpc-bind-addr=0.0.0.0:3001
      - --metasrv-addrs=metasrv:3002
      - --http-addr=0.0.0.0:5000
    volumes:
      - data-node-data:/data
    depends_on:
      metasrv:
        condition: service_started

  frontend:
    image: greptime/greptimedb:latest
    container_name: frontend
    ports:
      - 4000:4000
      - 4002:4002
      - 4003:4003
    command:
      - frontend
      - start
      - --metasrv-addrs=metasrv:3002
      - --http-addr=0.0.0.0:4000
      - --mysql-addr=0.0.0.0:4002
      - --postgres-addr=0.0.0.0:4003
    depends_on:
      datanode:
        condition: service_started

volumes:
  etcd-data: {}
  data-node-data: {}
```

### Querying Data

GreptimeDB supports SQL (PostgreSQL/MySQL dialect), PromQL, and its native GreptimeQL:

```sql
-- SQL query via MySQL/PostgreSQL connection
SELECT 
  hostname,
  avg(cpu_usage) as avg_cpu,
  max(cpu_usage) as max_cpu
FROM metrics
WHERE time > now() - INTERVAL '1 hour'
GROUP BY hostname
ORDER BY avg_cpu DESC;
```

```
# PromQL via HTTP (Prometheus-compatible endpoint)
curl 'http://localhost:4000/v1/promql?query=up{job="node_exporter"}'
```

## InfluxDB: The Mature Time-Series Platform

[InfluxDB](https://github.com/influxdata/influxdb) is the most widely adopted open-source time-series database. Originally written in Go, the v3 core has been completely rewritten in Rust for dramatically improved performance.

| Metric | Value |
|---|---|
| GitHub Stars | 31,466+ |
| Language | Rust (v3) |
| Last Updated | April 2026 |
| License | MIT / InfluxDB Enterprise (proprietary) |
| Protocols | HTTP/HTTPS (Line Protocol), gRPC, SQL (v3), Flux |

### Architecture

InfluxDB 3.x introduces the **IOx storage engine** built on Apache Arrow and Apache Parquet:

- **Apache Arrow**: In-memory columnar format for fast analytics
- **Apache Parquet**: Disk-based storage with efficient compression
- **Flight SQL**: Database protocol for SQL queries over Arrow

The architecture separates compute from storage, allowing horizontal scaling of query processing independently from data storage.

### Deployment with Docker Compose

InfluxDB 3 runs as a single process, making deployment straightforward:

```yaml
services:
  influxdb:
    image: influxdb:3-core
    container_name: influxdb
    ports:
      - 8181:8181
    environment:
      - INFLUXDB_DB_NAME=mydb
    volumes:
      - influxdb-data:/var/lib/influxdb3
    command:
      - serve
    restart: unless-stopped

volumes:
  influxdb-data: {}
```

### Initial Setup and Data Ingestion

After starting, create a token and set up your first bucket:

```bash
# Connect to InfluxDB 3 and set up
influxctl create database mydb

# Write data using Line Protocol
curl -X POST "http://localhost:8181/api/v2/write?db=mydb&precision=s" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d 'cpu,host=server01,region=us-east usage=45.2 1714204800'

# Query with SQL
curl -X POST "http://localhost:8181/api/v3/query_sql" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"db": "mydb", "q": "SELECT mean(usage) FROM cpu WHERE time > now() - 1h GROUP BY host"}'
```

### Telegraf Integration

The companion Telegraf agent handles metric collection from 300+ plugins:

```toml
# telegraf.conf
[agent]
  interval = "10s"
  round_interval = true

[[outputs.influxdb_v2]]
  urls = ["http://influxdb:8181"]
  token = "${INFLUXDB_TOKEN}"
  organization = "myorg"
  bucket = "mydb"

[[inputs.cpu]]
  percpu = true
  totalcpu = true

[[inputs.mem]]
  fielddrop = ["active", "inactive"]

[[inputs.disk]]
  mount_points = ["/"]

[[inputs.docker]]
  endpoint = "unix:///var/run/docker.sock"
```

## VictoriaMetrics: The Performance Champion

[VictoriaMetrics](https://github.com/VictoriaMetrics/VictoriaMetrics) is a high-performance, cost-effective monitoring solution written in Go. It's fully compatible with the Prometheus query language (PromQL) and can serve as a drop-in replacement for Prometheus long-term storage.

| Metric | Value |
|---|---|
| GitHub Stars | 16,875+ |
| Language | Go |
| Last Updated | April 2026 |
| License | Apache 2.0 (OSS) / Enterprise |
| Protocols | Prometheus Remote Write/Read, InfluxDB Line Protocol, Graphite, OpenTSDB |

### Architecture

VictoriaMetrics has two deployment modes:

- **Single-node**: A single binary handling ingestion, storage, and querying — ideal for small to medium deployments
- **Cluster**: Distributed architecture with vmstorage (storage), vminsert (ingestion), and vmselect (querying) — for horizontal scaling

The storage engine uses a custom merge-tree design optimized for time-series data with columnar compression, achieving 10x-30x better compression than Prometheus.

### Single-Node Deployment with Docker Compose

```yaml
services:
  victoriametrics:
    image: victoriametrics/victoria-metrics:v1.141.0
    container_name: victoriametrics
    ports:
      - 8428:8428
      - 8089:8089
      - 8089:8089/udp
      - 2003:2003
    volumes:
      - vmdata:/storage
    command:
      - "--storageDataPath=/storage"
      - "--httpListenAddr=:8428"
      - "--graphiteListenAddr=:2003"
      - "--influxListenAddr=:8089"
    restart: unless-stopped

  vmagent:
    image: victoriametrics/vmagent:v1.141.0
    container_name: vmagent
    depends_on:
      - "victoriametrics"
    ports:
      - 8429:8429
    volumes:
      - vmagent-data:/vmagent-data
      - ./scrape.yml:/etc/prometheus/prometheus.yml
    command:
      - "--promscrape.config=/etc/prometheus/prometheus.yml"
      - "--remoteWrite.url=http://victoriametrics:8428/api/v1/write"
    restart: unless-stopped

  grafana:
    image: grafana/grafana:12.2.0
    container_name: grafana
    depends_on:
      - "victoriametrics"
    ports:
      - 3000:3000
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
    restart: unless-stopped

volumes:
  vmdata: {}
  vmagent-data: {}
  grafana-data: {}
```

### Scrape Configuration

```yaml
# scrape.yml — Prometheus-compatible scrape config
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "node"
    static_configs:
      - targets: ["localhost:9100"]

  - job_name: "docker"
    static_configs:
      - targets: ["localhost:9323"]

  - job_name: "cadvisor"
    static_configs:
      - targets: ["localhost:8080"]
```

### Querying with PromQL

VictoriaMetrics uses PromQL natively, making migration from Prometheus seamless:

```
# Average CPU usage across all hosts over 5 minutes
avg_over_time(node_cpu_seconds_total{mode="idle"}[5m]) * 100

# Top 10 hosts by memory usage
topk(10, node_memory_Active_bytes / node_memory_MemTotal_bytes * 100)

# Rate of HTTP requests with 5xx errors
rate(http_requests_total{status=~"5.."}[5m])
```

## Head-to-Head Comparison

| Feature | GreptimeDB | InfluxDB 3.x | VictoriaMetrics |
|---|---|---|---|
| **Language** | Rust | Rust (IOx engine) | Go |
| **GitHub Stars** | 6,211 | 31,466 | 16,875 |
| **License** | Apache 2.0 | MIT (OSS) / Proprietary (Enterprise) | Apache 2.0 |
| **Query Languages** | SQL, PromQL, GreptimeQL | SQL, Flux, InfluxQL | PromQL, MetricsQL |
| **Prometheus Compatible** | Yes (Remote Write/Read) | Partially (via plugin) | Yes (full drop-in) |
| **Protocols** | MySQL, PostgreSQL, gRPC, HTTP, OTLP | HTTP, gRPC, Flight SQL | HTTP, Graphite, InfluxDB, OpenTSDB |
| **Clustering** | etcd-based, active-active | Compute/storage separation | vmstorage/vminsert/vmselect |
| **Built-in UI** | Yes (dashboard at :4000) | Yes (chronograf embedded) | No (pairs with Grafana) |
| **Data Compression** | Columnar (Parquet-based) | Parquet + Arrow | Custom merge-tree |
| **Log Storage** | Yes (unified engine) | Limited (via v3 logs) | No (metrics only) |
| **Trace Storage** | Yes (OpenTelemetry) | Limited | No |
| **Retention Policies** | Yes (TTL per table) | Yes (per bucket) | Yes (via retention period flag) |
| **Resource Usage** | Moderate (Rust, etcd dep.) | Moderate-High (Arrow memory) | Very Low (Go, single binary) |
| **Best For** | Unified observability platform | Rich query ecosystem + Telegraf | Maximum performance, Prometheus replacement |

## Choosing the Right Time-Series Database

### Choose GreptimeDB if:
- You want a **single platform for metrics, logs, and traces** instead of running separate tools
- You prefer **SQL queries** over time-series data (MySQL/PostgreSQL compatibility)
- You're building a new observability stack from scratch
- You value Rust's memory safety and performance guarantees

### Choose InfluxDB if:
- You need the **most mature ecosystem** with 300+ Telegraf input plugins
- Your team already knows **Flux or InfluxQL**
- You want **Apache Arrow integration** for downstream analytics
- You need commercial support from InfluxData

### Choose VictoriaMetrics if:
- **Performance and resource efficiency** are top priorities
- You want a **drop-in Prometheus replacement** with long-term storage
- You prefer **PromQL/MetricsQL** for all queries
- You need horizontal scaling with minimal operational complexity

For related reading on building a complete self-hosted observability stack, check out our [OpenObserve vs Quickwit vs Siglens observability guide](../openobserve-vs-quickwit-vs-siglens-self-hosted-observability-guide-2026/) for log management alternatives, and [Grafana Pyroscope vs Parca vs Profefe](../grafana-pyroscope-vs-parca-vs-profefe-self-hosted-continuous-profiling-guide-2026/) for continuous profiling tools.

## FAQ

### Which time-series database uses the least memory?
VictoriaMetrics is the most memory-efficient of the three. Its Go-based single binary typically uses 2-5x less RAM than comparable InfluxDB deployments and has no external dependencies (no etcd, no database). GreptimeDB requires etcd for clustering, adding overhead. For memory-constrained environments, VictoriaMetrics is the clear winner.

### Can I migrate data from Prometheus to these databases?
VictoriaMetrics offers the smoothest migration path — it's fully compatible with Prometheus Remote Write/Read APIs. You can point Prometheus remote_write to VictoriaMetrics and query everything through the VictoriaMetrics PromQL endpoint. GreptimeDB also supports Prometheus Remote Write. InfluxDB requires the `influxdb-prometheus` plugin or Telegraf as a bridge.

### Do any of these support SQL queries natively?
GreptimeDB and InfluxDB 3.x both support SQL. GreptimeDB speaks PostgreSQL and MySQL wire protocols, so you can connect standard SQL clients (DBeaver, psql, MySQL CLI). InfluxDB 3.x uses Flight SQL (Apache Arrow protocol). VictoriaMetrics does not support SQL — it uses PromQL and its extended MetricsQL.

### How do these databases handle data retention and downsampling?
All three support configurable retention. GreptimeDB sets TTL per table. InfluxDB manages retention per bucket. VictoriaMetrics uses the `-retentionPeriod` flag (default: 1 month). For downsampling, GreptimeDB uses continuous aggregates, InfluxDB uses tasks with the Flux scheduler, and VictoriaMetrics uses recording rules via vmalert.

### Which database is best for IoT workloads?
For IoT, consider ingestion protocol support. GreptimeDB accepts OpenTelemetry, MQTT (via gateway), and SQL — making it flexible for diverse IoT devices. InfluxDB has the broadest protocol support through Telegraf (MQTT, CoAP, Modbus plugins). VictoriaMetrics supports Graphite, InfluxDB Line Protocol, and OpenTSDB, covering most IoT use cases. VictoriaMetrics' low resource footprint also makes it suitable for edge deployments.

### Can these databases run on a Raspberry Pi or similar edge hardware?
VictoriaMetrics is the most suitable for edge hardware — its single binary runs comfortably on 512MB RAM and low-CPU environments. GreptimeDB's Rust core is efficient but etcd dependency increases resource needs. InfluxDB 3.x with the Arrow engine requires more memory and is better suited for servers with 2GB+ RAM.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "GreptimeDB vs InfluxDB vs VictoriaMetrics: Best Self-Hosted Time-Series Databases 2026",
  "description": "Compare GreptimeDB, InfluxDB, and VictoriaMetrics — the top self-hosted time-series databases for metrics, logs, and observability in 2026. Includes Docker Compose configs and deployment guides.",
  "datePublished": "2026-04-27",
  "dateModified": "2026-04-27",
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
