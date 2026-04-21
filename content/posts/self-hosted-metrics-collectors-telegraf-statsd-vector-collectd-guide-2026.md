---
title: "Best Self-Hosted Metrics Collectors 2026: Telegraf vs StatsD vs Vector vs collectd"
date: 2026-04-17
tags: ["comparison", "guide", "self-hosted", "monitoring", "observability", "metrics"]
draft: false
description: "Compare the top self-hosted metrics collection agents in 2026. Complete guide to Telegraf, StatsD, Vector, and collectd with Docker setup, configuration examples, and head-to-head comparison."
---

Every self-hosted monitoring stack starts with the same foundational question: **how do you get metrics from your servers, containers, and applications into your time-series database?** The answer is a metrics collector — a lightweight agent that runs alongside your services, gathers system and application statistics, and forwards them to your backend of choice.

In 2026, the landscape of open-source metrics collectors is diverse. **Telegraf** leads in plugin breadth with over 300 input plugins. **Vector** dominates in performance with its Rust-based pipeline. **StatsD** pioneered the simple UDP metrics protocol still used everywhere. **collectd** remains the battle-tested C daemon for system-level statistics. This guide compares all four with complete [docker](https://www.docker.com/)-based setup instructions.

## Why Self-Host Your Metrics Collection Pipeline

Running your own metrics collection infrastructure instead of depending on a SaaS monitoring service delivers several advantages:

**Full data ownership and privacy.** Every metric from your servers, databases, and applications stays within your infrastructure. No third-party vendor sees your resource utilization, traffic patterns, or business-critical metrics. This matters for compliance requirements (GDPR, HIPAA, SOC 2) and for organizations handling sensitive workloads.

**No vendor lock-in.** Self-hosted collectors output to standard protocols — Prometheus exposition format, InfluxDB line protocol, Graphite plaintext, OpenTelemetry — so you can swap backends without changing your collection layer.

**Cost savings at scale.** SaaS monitoring services typically charge per metric, per host, or per data volume. At 50+ servers generating thousands of metrics each, monthly bills easily exceed $500–2,000. Self-hosted collection costs only the compute to run the agents and the storage for your time-series database.

**Custom metrics without restrictions.** SaaS platforms often limit custom metric cardinality, drop high-cardinality labels, or charge extra for them. With a self-hosted collector, you define exactly what to measure and at what resolution.

For a complete monitoring stack overview, see our [Datadog alternatives guide](../self-hosted-datadog-alternative-signoz-grafana-hyperdx-2026/) and [VictoriaMetrics alerting comparison](../prometheus-alertmanager-vs-moira-vs-victoriametrics-vmalert-self-hosted-alerting-2026/).

## Telegraf: The Plugin Powerhouse

[Telegraf](https://github.com/influxdata/telegraf) by InfluxData is the most widely deployed metrics collection agent in the open-source ecosystem. Written in Go, it offers **300+ input plugins**, **70+ output plugins**, and native support for Prometheus, InfluxDB, Kafka, MQTT, and dozens of other protocols.

**GitHub stats:** 16,837 stars · Go · Last updated April 2026

### Key Strengths

- **Unmatched plugin ecosystem** — CPU, memo[kubernetes](https://kubernetes.io/)network, Docker, Kubernetes, PostgreSQL, MySQL, Redis, Nginx, HAProxy, SNMP, JMX, and hundreds more out of the box
- **Processor and aggregator plugins** — transform, filter, aggregate, and tag metrics before they leave the agent
- **Native Prometheus support** — scrape Prometheus endpoints and convert to InfluxDB line protocol (or vice versa)
- **Multi-output capability** — send the same metrics to multiple backends simultaneously

### Docker Compose Setup

```yaml
version: "3.8"
services:
  telegraf:
    image: docker.io/library/telegraf:1.33
    container_name: telegraf
    restart: unless-stopped
    user: telegraf
    volumes:
      - ./telegraf.conf:/etc/telegraf/telegraf.conf:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /:/hostfs:ro
      - /var/run/utmp:/var/run/utmp:ro
    environment:
      - HOST_ETC=/hostfs/etc
      - HOST_PROC=/hostfs/proc
      - HOST_SYS=/hostfs/sys
      - HOST_VAR=/hostfs/var
      - HOST_RUN=/hostfs/run
      - HOST_MOUNT_PREFIX=/hostfs
    network_mode: host
    pid: host
```

### Minimal Configuration

```toml
# telegraf.conf

[agent]
  interval = "10s"
  round_interval = true
  metric_batch_size = 1000
  metric_buffer_limit = 10000
  flush_interval = "10s"
  omit_hostname = false

# Collect system metrics from the host
[[inputs.cpu]]
  percpu = true
  totalcpu = true
  collect_cpu_time = false
  report_active = false

[[inputs.mem]]

[[inputs.disk]]
  ignore_fs = ["tmpfs", "devtmpfs", "devfs", "iso9660", "overlay", "aufs", "squashfs"]

[[inputs.net]]

[[inputs.docker]]
  endpoint = "unix:///var/run/docker.sock"

# Output to Prometheus-compatible backend
[[outputs.prometheus_client]]
  listen = ":9273"
  path = "/metrics"

# Also send to InfluxDB
[[outputs.influxdb_v2]]
  urls = ["http://influxdb:8086"]
  token = "${INFLUXDB_TOKEN}"
  organization = "monitoring"
  bucket = "telegraf"
```

Telegraf is the best choice when you need to collect metrics from a wide variety of sources — databases, web servers, message queues, cloud APIs — and route them to one or more backends. The trade-off is higher memory usage compared to simpler agents.

## StatsD: The Simple UDP Metrics Daemon

[StatsD](https://github.com/statsd/statsd) by Etsy originated the now-ubiquitous StatsD protocol: send metrics over UDP in simple text format, and the daemon aggregates them into time-bucketed statistics (counters, gauges, timers, sets) before flushing to a backend like Graphite.

**GitHub stats:** 18,027 stars · JavaScript/Node.js · Last updated May 2025

### Key Strengths

- **Dead simple protocol** — `metric.name:value|type` sent over UDP, no authentication or com[plex](https://www.plex.tv/) configuration needed
- **Language-agnostic** — client libraries exist for virtually every programming language (Python, Go, Ruby, Java, .NET, PHP)
- **Application-level metrics** — designed specifically for tracking custom application counters, timings, and gauges from within your code
- **Lightweight** — minimal resource footprint, runs comfortably on a Raspberry Pi

### How the StatsD Protocol Works

```
# Counter (increments by value each flush interval)
page.views:1|c

# Gauge (absolute value)
temperature:22|g

# Timer (histogram statistics computed by StatsD)
response.time:320|ms

# Set (count of unique values)
unique.users:abc123|s
```

### Docker Compose Setup with Graphite

```yaml
version: "3.8"
services:
  statsd:
    image: docker.io/etsy/statsd
    container_name: statsd
    restart: unless-stopped
    volumes:
      - ./statsd-config.js:/etc/statsd/localConfig.js:ro
    ports:
      - "8125:8125/udp"
      - "8126:8126"
    depends_on:
      - carbon

  carbon:
    image: docker.io/graphiteapp/graphite-statsd
    container_name: carbon
    restart: unless-stopped
    ports:
      - "80:80"
      - "2003:2003"
      - "2004:2004"
    volumes:
      - carbon_data:/opt/graphite/storage

volumes:
  carbon_data:
```

### StatsD Configuration (JavaScript)

```javascript
// statsd-config.js
{
  graphitePort: 2003,
  graphiteHost: "carbon",
  port: 8125,
  flushInterval: 10000,
  deleteIdleStats: false,
  deleteGauges: false,
  deleteTimers: false,
  deleteSets: false,
  calculateRate: true,
  rateCalculationInterval: 10000,
  timers: {
    percentile: true,
    threshold: 0.99,
    histograms: [{
      name: "response_time",
      bins: [0, 50, 100, 200, 500, 1000, 2000],
      binsuffix: "ms"
    }]
  },
  backends: ["graphite"]
}
```

StatsD excels when your primary need is **application-level custom metrics** — tracking request rates, error counts, response time percentiles from your own code. It is not a system metrics collector (use Telegraf or collectd for that). The Node.js-based implementation means it is single-threaded and may struggle under very high metric volumes (>50K metrics/sec).

## Vector: The High-Performance Rust Pipeline

[Vector](https://github.com/vectordotdev/vector) (now part of Datadog but fully open-source under MPL 2.0) is a high-performance observability data pipeline written in Rust. Unlike traditional metrics collectors, Vector treats metrics, logs, and traces as unified "events" flowing through a configurable pipeline of sources, transforms, and sinks.

**GitHub stats:** 21,669 stars · Rust · Last updated April 2026

### Key Strengths

- **Extreme performance** — Rust-based, zero-copy event processing, handles millions of events per second on modest hardware
- **Unified pipeline** — collects metrics, logs, and traces in a single agent with a consistent configuration model
- **Reliability guarantees** — disk-buffered delivery, exactly-once semantics, automatic retry with backoff
- **Rich transform language** — VRL (Vector Remap Language) for powerful metric manipulation, filtering, and enrichment
- **Native OpenTelemetry support** — receives and forwards OTLP metrics, logs, and traces

### Docker Compose Setup

```yaml
version: "3.8"
services:
  vector:
    image: docker.io/timberio/vector:0.46.0-distroless-libc
    container_name: vector
    restart: unless-stopped
    volumes:
      - ./vector.yaml:/etc/vector/vector.yaml:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /var/log:/var/log:ro
    ports:
      - "9090:9090"
      - "8081:8081"
    environment:
      - VECTOR_LOG=RUST_LOG=info
```

### Vector Configuration (YAML)

```yaml
# vector.yaml

# Collect host metrics via Prometheus scraping
sources:
  host_metrics:
    type: host_metrics
    scrape_interval_secs: 10

  docker_metrics:
    type: docker_logs
    # Collect container resource usage

  prometheus_input:
    type: prometheus_scrape
    endpoints:
      - http://app-server:9090/metrics
    scrape_interval_secs: 15

# Transform: add environment tag, filter out noisy metrics
transforms:
  add_env_tag:
    type: remap
    inputs:
      - host_metrics
      - prometheus_input
    source: |
      .env = "production"
      del(.kubernetes)

  filter_idle:
    type: filter
    inputs:
      - add_env_tag
    condition: |
      !starts_with(.name, "idle_cpu_")

# Send to multiple backends
sinks:
  prometheus_exporter:
    type: prometheus_exporter
    inputs:
      - filter_idle
    address: "0.0.0.0:9090"

  loki:
    type: loki
    inputs:
      - add_env_tag
    endpoint: "http://loki:3100"
    encoding:
      codec: json
```

Vector is the top choice for teams that want a **single agent for all observability data** — metrics, logs, and traces — with the highest possible throughput and delivery guarantees. The Rust foundation means it uses significantly less memory than Go-based agents at equivalent throughput.

## collectd: The Battle-Tested System Statistics Daemon

[collectd](https://github.com/collectd/collectd) is one of the oldest open-source metrics collectors, written in C and running on virtually every Unix-like system since 2005. It collects system and application performance statistics at configurable intervals and stores or forwards them.

**GitHub stats:** 3,350 stars · C · Last updated December 2025

### Key Strengths

- **Extremely low resource usage** — written in C, typically uses <10 MB of RAM
- **100+ plugins** — CPU, memory, disk, network, processes, users, nginx, MySQL, PostgreSQL, Redis, Docker, and many more
- **Stable and mature** — two decades of production deployments, minimal bugs, well-understood behavior
- **Network plugin** — can forward metrics to a central collectd instance for aggregation

### Docker Compose Setup

```yaml
version: "3.8"
services:
  collectd:
    image: docker.io/linuxserver/collectd
    container_name: collectd
    restart: unless-stopped
    volumes:
      - ./collectd.conf:/config/collectd.conf:ro
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
    environment:
      - TZ=UTC
    network_mode: host
```

### collectd Configuration

```apache
# collectd.conf

Hostname "server-01"
FQDNLookup true
Interval 10
Timeout 2
ReadThreads 2
WriteThreads 4

# Load core plugins
LoadPlugin cpu
LoadPlugin memory
LoadPlugin load
LoadPlugin disk
LoadPlugin interface
LoadPlugin network
LoadPlugin processes
LoadPlugin uptime

# CPU plugin configuration
<Plugin cpu>
  ReportByCpu true
  ReportByState true
  ValuesPercentage true
</Plugin>

# Disk plugin configuration
<Plugin disk>
  Disk "/^[sv]d[a-z]/"
  IgnoreSelected false
</Plugin>

# Network plugin — send to Graphite via collectd-write_graphite
<Plugin write_graphite>
  <Node "graphite">
    Host "graphite-server"
    Port "2003"
    Protocol "tcp"
    LogSendErrors true
    Prefix "collectd."
    StoreRates true
    AlwaysAppendDS false
    EscapeCharacter "_"
  </Node>
</Plugin>
```

collectd shines in **resource-constrained environments** — embedded devices, IoT gateways, old hardware, or any situation where every megabyte of RAM counts. Its plugin ecosystem is smaller than Telegraf's and it lacks native Prometheus support, but for pure system metrics on bare metal or VMs, it remains incredibly effective.

## Head-to-Head Comparison

| Feature | Telegraf | StatsD | Vector | collectd |
|---------|----------|--------|--------|----------|
| **Language** | Go | JavaScript/Node.js | Rust | C |
| **GitHub Stars** | 16,837 | 18,027 | 21,669 | 3,350 |
| **Last Updated** | April 2026 | May 2025 | April 2026 | December 2025 |
| **Input Plugins** | 300+ | Protocol-level | 40+ sources | 100+ plugins |
| **Data Types** | Metrics, logs | Metrics only | Metrics, logs, traces | Metrics only |
| **Prometheus Support** | Native (scrape + expose) | Via export | Native (scrape + expose) | Via write_prometheus |
| **OpenTelemetry** | Via plugin | No | Native OTLP | No |
| **Disk Buffering** | Yes | No | Yes (guaranteed delivery) | Via write plugins |
| **Memory Footprint** | ~50–150 MB | ~20–50 MB | ~30–80 MB | ~5–15 MB |
| **Max Throughput** | ~100K events/sec | ~50K metrics/sec | ~1M+ events/sec | ~50K metrics/sec |
| **Configuration** | TOML | JavaScript | YAML | Apache-style |
| **Best For** | Multi-source collection | App-level custom metrics | Unified observability pipeline | Low-resource system metrics |

## When to Choose Which Collector

**Choose Telegraf when:**
- You need to collect from many different sources (databases, web servers, cloud APIs, SNMP devices)
- You want to send metrics to multiple backends simultaneously
- Your stack uses InfluxDB or needs InfluxDB line protocol output
- You need processor plugins to transform or aggregate metrics at the edge

**Choose StatsD when:**
- Your primary need is application-level custom metrics (counters, timers, gauges)
- You want the simplest possible protocol for instrumenting code
- You already have or plan to use Graphite as your backend
- You need client libraries for many programming languages

**Choose Vector when:**
- You want a single agent for metrics, logs, and traces
- Performance and resource efficiency are critical
- You need guaranteed delivery with disk buffering
- Your organization is adopting OpenTelemetry
- You want powerful metric transformation capabilities via VRL

**Choose collectd when:**
- You are running on resource-constrained hardware (embedded, IoT, old servers)
- You need maximum stability and minimal overhead
- Your use case is purely system-level metrics (CPU, memory, disk, network)
- You prefer a mature, well-understood daemon over a newer agent

## Which Backend to Pair With Your Collector

Your metrics collector is only half the equation — you need a time-series database to store and query the data. Popular open-source backends include:

- **Prometheus** — pull-based model, excellent for Kubernetes environments, pairs well with Telegraf's Prometheus output or Vector's Prometheus exporter
- **InfluxDB** — purpose-built time-series database, native integration with Telegraf via the TICK stack
- **VictoriaMetrics** — high-performance Prometheus-compatible storage, handles millions of active time series
- **Graphite** — the original time-series store, the natural backend for StatsD and collectd

For a deeper comparison of storage options, see our [time-series database guide](../influxdb-vs-questdb-vs-timescaledb-self-hosted-time-series-database-guide-2026/) and [Prometheus vs Grafana vs VictoriaMetrics comparison](../prometheus-vs-grafana-vs-victoriametrics/). If you need log collection alongside metrics, our [log shipping guide](../self-hosted-log-shipping-vector-fluentbit-logstash-guide-2026/) covers Vector, Fluent Bit, and Logstash.

## FAQ

### What is the difference between a metrics collector and a monitoring system?

A metrics collector is an agent that runs on your servers or containers and gathers raw statistics — CPU usage, memory consumption, request counts, response times. A monitoring system is the complete stack: collectors gather data, a time-series database stores it, and a visualization tool (like Grafana) displays it. The collector is the data source; the monitoring system is the full pipeline.

### Can I run multiple metrics collectors on the same host?

Yes, it is common to run different collectors for different purposes. For example, you might run collectd for lightweight system-level metrics and a separate StatsD instance for application-level custom metrics. The key is to avoid collecting the same metric twice, which wastes resources and creates duplicate data in your backend.

### How often should metrics be collected?

The standard interval is 10–60 seconds. System metrics (CPU, memory, disk) are typically collected every 10–30 seconds. Application metrics (request rates, response times) may be collected every 1–10 seconds for high-traffic services. Collecting more frequently than every second usually provides diminishing returns and increases storage costs significantly.

### Does Vector replace Prometheus?

No. Vector is a data pipeline that collects, transforms, and forwards metrics. Prometheus is a time-series database with a built-in scraper and query language. They serve different purposes. Vector can scrape Prometheus endpoints and forward the data elsewhere, or it can expose metrics in Prometheus format for Prometheus to scrape. They are complementary, not interchangeable.

### Which collector has the lowest memory footprint?

collectd uses the least memory, typically 5–15 MB, because it is written in C and has no garbage collector. Vector (Rust) follows at 30–80 MB. StatsD (Node.js) uses 20–50 MB. Telegraf (Go) is the heaviest at 50–150 MB, though this is still modest for most server environments.

### Can these collectors run inside Docker containers?

Yes, all four collectors have official or community Docker images. The key configuration is mounting the host's `/proc`, `/sys`, and `/var/run/docker.sock` into the container so it can access host-level metrics. See the Docker Compose examples above for each tool.

### How do I choose between Telegraf and Vector?

If you need broad plugin coverage (300+ inputs) and use the InfluxDB ecosystem, Telegraf is the better fit. If you need maximum throughput, guaranteed delivery, or want a unified agent for metrics + logs + traces with OpenTelemetry support, Vector is the stronger choice. Both are excellent — the decision comes down to your specific ecosystem and performance requirements.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Best Self-Hosted Metrics Collectors 2026: Telegraf vs StatsD vs Vector vs collectd",
  "description": "Compare the top self-hosted metrics collection agents in 2026. Complete guide to Telegraf, StatsD, Vector, and collectd with Docker setup, configuration examples, and head-to-head comparison.",
  "datePublished": "2026-04-17",
  "dateModified": "2026-04-17",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>
