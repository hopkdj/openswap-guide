---
title: "mtail vs grok_exporter vs Vector: Self-Hosted Log Parsing Guide 2026"
date: 2026-04-28
tags: ["comparison", "guide", "self-hosted", "monitoring", "logging", "prometheus"]
draft: false
description: "Compare mtail, grok_exporter, and Vector for self-hosted log parsing and metric extraction. Complete guide with Docker Compose configs, Grok patterns, and Prometheus integration."
---

When your applications generate logs, the raw text is full of useful signals — response times, error rates, request counts, and queue depths. But Prometheus and Grafana can't read raw log files. You need a log parser to extract metrics from unstructured text and expose them in a format your monitoring stack understands.

This guide compares three self-hosted log parsing tools: **mtail** (Google's log-to-metrics extractor), **grok_exporter** (Prometheus exporter with Grok pattern matching), and **Vector** (high-performance observability pipeline). Each can transform your application logs into actionable Prometheus metrics without shipping the entire log payload to a central aggregator.

For a broader look at log aggregation architecture, see our [rsyslog vs syslog-ng vs Vector comparison](../rsyslog-vs-syslog-ng-vs-vector-self-hosted-syslog-log-aggregation-guide-2026/) and [Prometheus vs Grafana vs VictoriaMetrics overview](../prometheus-vs-grafana-vs-victoriametrics/).

## Why Self-Host Log Parsing?

Cloud-based log management services charge by ingestion volume. If you're generating gigabytes of logs daily, sending everything to a SaaS platform gets expensive fast. Self-hosted log parsing lets you:

- **Extract only the metrics you need** — parse logs locally and discard the raw text after extraction
- **Reduce storage costs** — store structured metrics (kilobytes) instead of raw logs (gigabytes)
- **Maintain full data sovereignty** — logs never leave your infrastructure
- **Integrate with existing Prometheus/Grafana stacks** — no new monitoring platform required
- **React to log patterns in real time** — trigger alerts based on parsed log events, not just raw text searches

## Quick Comparison

| Feature | mtail | grok_exporter | Vector |
|---------|-------|---------------|--------|
| **GitHub Stars** | 4,007 | 930 | 21,730 |
| **Last Updated** | March 2026 | November 2023 | April 2026 |
| **Developer** | Google | Community (fstab) | Datadog (open source) |
| **Language** | Go | Go | Rust |
| **Pattern Syntax** | Custom mtail language | Grok (Logstash-compatible) | VRL (Vector Remap Language) |
| **Output Format** | Prometheus metrics, stdout | Prometheus metrics | 40+ sinks (Prometheus, Loki, etc.) |
| **Docker Image** | `google/mtail` | `fstab/grok_exporter` | `timberio/vector` |
| **Resource Usage** | Low | Low | Low to Medium |
| **Learning Curve** | Medium | Low (if you know Grok) | Medium |
| **Best For** | Simple log-to-metrics extraction | Teams already using Grok patterns | Full observability pipeline |

## mtail — Google's Log-to-Metrics Extractor

[mtail](https://github.com/google/mtail) is Google's open-source tool for extracting metrics from application logs. It uses a custom pattern language that's purpose-built for log parsing. mtail watches log files (or receives data via stdin) and applies your program to extract counters, gauges, and histograms.

### Key Features

- **Purpose-built pattern language** — the mtail language is designed specifically for log parsing, with regex, state machines, and time extraction built in
- **Prometheus-native** — exposes a `/metrics` endpoint that Prometheus scrapes directly
- **Low resource footprint** — runs as a lightweight sidecar alongside your applications
- **Google production-tested** — used internally at Google for monitoring thousands of services

### Docker Compose Setup

```yaml
services:
  mtail:
    image: google/mtail:latest
    container_name: mtail
    restart: unless-stopped
    ports:
      - "3903:3903"
    volumes:
      - ./mtail_programs:/etc/mtail/programs:ro
      - /var/log/app:/var/log/app:ro
    command:
      - "--progs=/etc/mtail/programs"
      - "--logs=/var/log/app/*.log"
      - "--port=3903"
      - "--emit_metric_timestamp"
    networks:
      - monitoring

networks:
  monitoring:
    external: true
```

### Example mtail Program

Here's an mtail program that parses Nginx access logs and extracts HTTP status code counts and response time histograms:

```mtail
# nginx.mtail - Parse Nginx access logs for Prometheus metrics

counter http_requests_total by status, method
histogram http_response_time_seconds by status buckets 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5

/^(?P<remote>[^ ]+) (?P<ident>[^ ]+) (?P<user>[^ ]+) \[(?P<timestamp>[^\]]+)\] "(?P<method>\w+) (?P<path>[^ ]+) (?P<proto>[^"]+)" (?P<status>\d+) (?P<size>\d+) "(?P<referer>[^"]*)" "(?P<agent>[^"]*)" (?P<response_time>[\d.]+)$/ {
    http_requests_total[$status][$method]++
    http_response_time_seconds[$status] = $response_time / 1000
}
```

### Installation (Binary)

```bash
# Download latest mtail release
wget https://github.com/google/mtail/releases/download/v3.0.0-rc52/mtail_3.0.0-rc52_linux_amd64.tar.gz
tar xzf mtail_*.tar.gz
sudo mv mtail /usr/local/bin/

# Run with a program file and log path
mtail --progs /etc/mtail/programs --logs /var/log/nginx/access.log --port 3903
```

## grok_exporter — Prometheus Exporter with Grok Patterns

[grok_exporter](https://github.com/fstab/grok_exporter) is a Prometheus exporter that uses Grok patterns (the same syntax used by Logstash) to parse unstructured log data. If your team already uses Grok patterns for Logstash or Elasticsearch, grok_exporter lets you reuse them directly for Prometheus metrics.

### Key Features

- **Grok pattern compatibility** — reuse existing Logstash/Elasticsearch Grok patterns without rewriting
- **Simple YAML configuration** — define metrics, patterns, and labels in a single config file
- **Multiple metric types** — supports counters, gauges, histograms, and summaries
- **File and stdin input** — can tail log files or receive data via standard input

> **Note:** grok_exporter's last commit was in November 2023. While it remains functional for stable use cases, the project is no longer actively maintained. For new deployments, Vector is the recommended alternative with active development.

### Docker Compose Setup

```yaml
services:
  grok_exporter:
    image: fstab/grok_exporter:latest
    container_name: grok_exporter
    restart: unless-stopped
    ports:
      - "9144:9144"
    volumes:
      - ./grok_exporter_config.yml:/grok_exporter/config.yml:ro
      - /var/log/app:/var/log/app:ro
    command:
      - "-config=/grok_exporter/config.yml"
    networks:
      - monitoring

networks:
  monitoring:
    external: true
```

### Example Configuration

```yaml
global:
  config_version: 3

input:
  type: files
  path: /var/log/app/*.log
  readall: false

grok:
  patterns_dir: ./patterns

metrics:
  - type: counter
    name: http_requests_total
    help: Total HTTP requests by status code and method
    match: '%{COMBINEDAPACHELOG}'
    labels:
      status: '{{.status}}'
      method: '{{.verb}}'

  - type: histogram
    name: http_response_size_bytes
    help: HTTP response size distribution
    match: '%{COMBINEDAPACHELOG}'
    value: '{{.bytes}}'
    buckets: [100, 1000, 10000, 100000, 1000000]

export:
  type: prometheus
  port: 9144
```

### Custom Grok Pattern

For logs that don't match built-in patterns, you can define custom ones:

```
# patterns/custom.patterns
CUSTOM_APP_LOG %{TIMESTAMP_ISO8601:timestamp} \[%{LOGLEVEL:level}\] %{DATA:component} - %{GREEDYDATA:message} %{NUMBER:duration:float}s
```

### Installation (Binary)

```bash
# Download latest release
wget https://github.com/fstab/grok_exporter/releases/download/v0.2.8/grok_exporter-0.2.8.linux-amd64.tar.gz
tar xzf grok_exporter-*.tar.gz
sudo mv grok_exporter-*/grok_exporter /usr/local/bin/

# Run with config
grok_exporter -config /etc/grok_exporter/config.yml
```

## Vector — High-Performance Observability Pipeline

[Vector](https://github.com/vectordotdev/vector) is a high-performance observability data pipeline built in Rust. While mtail and grok_exporter focus solely on log-to-metrics extraction, Vector can collect, transform, and route logs, metrics, and traces to 40+ destinations. Its VRL (Vector Remap Language) provides powerful log parsing capabilities.

### Key Features

- **All-in-one pipeline** — collect, transform, and route logs, metrics, and traces in a single tool
- **VRL (Vector Remap Language)** — purpose-built transformation language with regex, JSON parsing, and conditional logic
- **40+ sinks** — output to Prometheus, Loki, Elasticsearch, S3, Kafka, and many more
- **Rust performance** — handles millions of events per second with minimal CPU and memory
- **Active development** — backed by Datadog with a large open-source community

### Docker Compose Setup

```yaml
services:
  vector:
    image: timberio/vector:latest
    container_name: vector
    restart: unless-stopped
    ports:
      - "9090:9090"
      - "8686:8686"
    volumes:
      - ./vector.toml:/etc/vector/vector.toml:ro
      - /var/log/app:/var/log/app:ro
    environment:
      - VECTOR_LOG=info
    networks:
      - monitoring

networks:
  monitoring:
    external: true
```

### Example Vector Configuration (TOML)

```toml
[sources.app_logs]
type = "file"
include = ["/var/log/app/*.log"]
read_from = "beginning"

[transforms.parse_logs]
type = "remap"
inputs = ["app_logs"]
source = '''
parsed = parse_regex!(.message, r'^(?P<remote>[^ ]+) (?P<ident>[^ ]+) \[(?P<timestamp>[^\]]+)\] "(?P<method>\w+) (?P<path>[^ ]+) [^"]+" (?P<status>\d+) (?P<bytes>\d+)')
.status = parsed.status
.method = parsed.method
.path = parsed.path
.bytes = to_int!(parsed.bytes)
'''

[transforms.aggregate]
type = "log_to_metric"
inputs = ["parse_logs"]

  [[transforms.aggregate.metrics]]
  type = "counter"
  field = "status"
  name = "http_requests_total"
  tags.status = "{{status}}"
  tags.method = "{{method}}"

  [[transforms.aggregate.metrics]]
  type = "histogram"
  field = "bytes"
  name = "http_response_size_bytes"
  tags.status = "{{status}}"

[sinks.prometheus]
type = "prometheus_exporter"
inputs = ["aggregate"]
address = "0.0.0.0:9090"
```

### Installation (Binary)

```bash
# Install via official script
curl -sSf https://sh.vector.dev | bash
sudo mv ~/.vector/bin/vector /usr/local/bin/

# Or install from package manager (Debian/Ubuntu)
curl -1sLf 'https://repositories.timber.io/public/vector/cfg.deb/setup.deb.sh' | sudo bash
sudo apt install vector

# Run with config
vector --config /etc/vector/vector.toml
```

## Performance Comparison

| Metric | mtail | grok_exporter | Vector |
|--------|-------|---------------|--------|
| **Throughput** | ~50K lines/sec | ~30K lines/sec | ~500K+ lines/sec |
| **Memory Usage** | ~20 MB | ~15 MB | ~50-100 MB |
| **CPU Usage** | Low | Low | Low to Medium |
| **Startup Time** | < 1s | < 1s | 1-2s |
| **Regex Performance** | Good (RE2 engine) | Good (Oniguruma) | Excellent (Rust regex) |

*Note: Performance numbers are approximate and depend on pattern complexity, log format, and hardware.*

## When to Use Each Tool

### Choose mtail if:
- You want a simple, focused tool for log-to-metrics extraction
- Your team is comfortable writing custom parsing programs
- You need Prometheus metrics with minimal overhead
- You're monitoring Google Cloud Platform services (mtail integrates well)

### Choose grok_exporter if:
- You already have a library of Grok patterns from Logstash/Elasticsearch
- Your log parsing needs are straightforward and stable
- You want a quick drop-in Prometheus exporter for existing log formats
- You don't need active maintenance (project is in maintenance mode)

### Choose Vector if:
- You need a full observability pipeline (logs, metrics, traces)
- Performance is critical (millions of events per second)
- You want to route data to multiple destinations simultaneously
- You need active development and community support
- You want to transform and enrich data before sending it to your monitoring stack

## Frequently Asked Questions

### What is the difference between log parsing and log aggregation?

Log parsing extracts structured data (metrics, fields) from unstructured log text. Log aggregation collects and centralizes log data from multiple sources. Tools like mtail and grok_exporter focus on parsing — they turn raw logs into Prometheus metrics. Tools like Vector can do both: parse logs into metrics AND aggregate/ship raw logs to central storage.

### Can I use Grok patterns with mtail?

No, mtail uses its own custom pattern language. However, the concepts are similar — both use regex-based pattern matching with named capture groups. If you have existing Grok patterns, you'll need to translate them to mtail syntax. Vector supports both Grok-like regex and its own VRL language.

### Is grok_exporter still maintained?

The last commit to grok_exporter was in November 2023. The project is functional and stable for existing use cases, but it is not actively developed. For new deployments, Vector is recommended as it offers Grok-compatible parsing with active maintenance and a broader feature set.

### Can these tools parse JSON logs?

Yes, all three can handle JSON-formatted logs. mtail can parse JSON using its regex capabilities. grok_exporter has a `JSON` input type. Vector has native JSON parsing via `parse_json!()` in VRL, making it the most straightforward option for JSON log formats.

### How do I integrate parsed metrics with Prometheus?

All three tools expose a `/metrics` HTTP endpoint that Prometheus scrapes. Add a scrape configuration to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'mtail'
    static_configs:
      - targets: ['mtail:3903']

  - job_name: 'grok_exporter'
    static_configs:
      - targets: ['grok_exporter:9144']

  - job_name: 'vector'
    static_configs:
      - targets: ['vector:9090']
```

For related reading, see our [Prometheus alerting guide](../prometheus-alertmanager-vs-moira-vs-victoriametrics-vmalert-self-hosted-alerting-2026/) and [container monitoring comparison](../cadvisor-vs-dozzle-vs-netdata-self-hosted-docker-container-monitoring-guide-2026/).

### Do I need to restart these tools when log files rotate?

mtail handles log rotation automatically — it detects when a file is rotated and switches to the new file. grok_exporter also handles log rotation natively. Vector's file source supports log rotation detection out of the box. No manual restart is needed for any of these tools.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "mtail vs grok_exporter vs Vector: Self-Hosted Log Parsing Guide 2026",
  "description": "Compare mtail, grok_exporter, and Vector for self-hosted log parsing and metric extraction. Complete guide with Docker Compose configs, Grok patterns, and Prometheus integration.",
  "datePublished": "2026-04-28",
  "dateModified": "2026-04-28",
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
