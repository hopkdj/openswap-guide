---
title: "Self-Hosted Log Collector Agents for Grafana Loki: Promtail vs Fluent Bit vs Vector (2026)"
date: "2026-05-24"
tags: ["loki", "logging", "observability", "grafana", "promtail", "fluent-bit", "vector"]
draft: false
---

Grafana Loki has become the go-to log aggregation platform for self-hosted observability stacks, but getting logs from your servers and containers into Loki requires a collector agent. Three dominant options compete for this role: **Promtail** (the native Loki agent), **Fluent Bit** (the lightweight universal processor), and **Vector** (the high-performance data pipeline). Each has different strengths in resource usage, processing capabilities, and operational complexity.

This guide compares all three agents head-to-head, with real Docker Compose configurations, to help you pick the right log collector for your Loki deployment.

## Understanding the Log Collector Role

Before comparing tools, it helps to understand what a log collector agent does in a Loki stack:

- **Discovery**: Finds log sources (files, journald, Docker containers, syslog)
- **Collection**: Reads log lines efficiently without missing data or consuming excessive resources
- **Processing**: Parses, filters, transforms, and enriches log data before shipping
- **Shipping**: Sends structured log batches to Loki's push API with proper labeling
- **Resilience**: Handles network outages with local buffering and retry logic

The right choice depends on your environment size, log volume, processing needs, and existing infrastructure.

## Promtail: The Native Loki Agent

Promtail is Grafana Labs' official log collector for Loki. It shares architecture with Prometheus — using the same service discovery, relabeling, and push model — making it the most natural fit for Loki.

### Key Features

- **Native Loki integration** — understands Loki's label system and stream format
- **Service discovery** — reuses Prometheus SD mechanisms (Consul, Kubernetes, EC2, Docker)
- **Journal source** — reads systemd journal entries with full metadata
- **File tailing** — watches log files with position tracking
- **Pipeline stages** — regex, JSON, logfmt, timestamp, and label extraction
- **Relabeling** — identical to Prometheus relabel_configs

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  promtail:
    image: grafana/promtail:latest
    container_name: promtail
    volumes:
      - /var/log:/var/log:ro
      - /etc/promtail/config.yml:/etc/promtail/config.yml:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
    command: -config.file=/etc/promtail/config.yml
    restart: unless-stopped

networks:
  default:
    name: loki-stack
```

### Promtail Configuration

```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: system
    static_configs:
      - targets:
          - localhost
        labels:
          job: varlogs
          __path__: /var/log/*.log

  - job_name: journal
    journal:
      max_age: 12h
      labels:
        job: systemd-journal
    relabel_configs:
      - source_labels: ["__journal__systemd_unit"]
        target_label: "unit"
```

### When to Use Promtail

Promtail shines when you are already running Prometheus and Loki together. Its relabeling pipeline mirrors Prometheus exactly, so teams familiar with Prometheus service discovery will feel at home. It is lightweight enough for edge deployments and handles Loki's label cardinality model natively.

**Best for**: Small to medium Loki deployments, teams already using Prometheus, simple log collection with basic parsing.

**Limitations**: Pipeline stages are less powerful than Fluent Bit or Vector for complex transformations. No output to destinations other than Loki.

## Fluent Bit: The Universal Lightweight Processor

Fluent Bit (now part of the CNCF Fluent ecosystem) is a high-performance log processor and forwarder written in C. It supports Loki as one of many output destinations, making it ideal for multi-destination log pipelines.

### Key Features

- **100+ plugins** — inputs, filters, parsers, and outputs for almost every source and destination
- **Low resource footprint** — typically 10-30 MB RAM, ideal for edge and IoT deployments
- **Multi-destination** — send logs to Loki, Elasticsearch, stdout, files, Kafka, and more simultaneously
- **Stream processing** — Lua scripting, regex parsing, JSON manipulation, record modification
- **Built-in parsers** — Docker, JSON, syslog, regex, logfmt out of the box
- **Hot reload** — configuration changes without restart

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  fluent-bit:
    image: fluent/fluent-bit:latest
    container_name: fluent-bit
    volumes:
      - /var/log:/var/log:ro
      - ./fluent-bit.conf:/fluent-bit/etc/fluent-bit.conf:ro
      - ./parsers.conf:/fluent-bit/etc/parsers.conf:ro
    restart: unless-stopped

networks:
  default:
    name: loki-stack
```

### Fluent Bit Configuration

```ini
[SERVICE]
    Flush        5
    Daemon       Off
    Log_Level    info
    Parsers_File parsers.conf

[INPUT]
    Name         tail
    Path         /var/log/*.log
    Parser       docker
    Tag          host.*
    Refresh_Interval 10

[INPUT]
    Name         systemd
    Tag          systemd.*
    Systemd_Filter _SYSTEMD_UNIT=docker.service

[FILTER]
    Name         grep
    Match        *
    Regex        level (error|warn|critical)

[FILTER]
    Name         modify
    Match        *
    Add          environment production
    Add          region us-east-1

[OUTPUT]
    Name         loki
    Match        *
    Url          http://loki:3100
    Labels       job=fluent-bit, environment=production
    Auto_Kubernetes_Labels false
    Line_Format  json
```

### Fluent Bit Parsers

```ini
[PARSER]
    Name        docker
    Format      json
    Time_Key    time
    Time_Format %Y-%m-%dT%H:%M:%S.%L
    Time_Keep   On

[PARSER]
    Name        syslog-rfc5424
    Format      regex
    Regex       ^\<(?<pri>[0-9]+)\>(?<time>[^ ]+) (?<host>[^ ]+) (?<ident>[^ ]+) (?<pid>[0-9]+) (?<msgid>[^ ]+) (?<extradata>(?:\[.*?\]|-)) (?<message>.+)$
```

### When to Use Fluent Bit

Fluent Bit is the right choice when you need multi-destination output, complex log processing, or extremely low resource usage. Its plugin ecosystem covers virtually every log source and destination, making it the most versatile agent in this comparison.

**Best for**: Multi-destination log pipelines, edge deployments with tight memory limits, complex log parsing and transformation needs.

**Limitations**: Configuration syntax differs significantly between versions (v2 vs v3). Lua scripting has a learning curve.

## Vector: The High-Performance Data Pipeline

Vector (by Datadog, open-source under MPL 2.0) is a high-performance observability data pipeline written in Rust. It positions itself as a unified replacement for multiple agents — collecting, transforming, and routing logs, metrics, and traces.

### Key Features

- **VRL (Vector Remap Language)** — powerful data transformation language with type checking
- **Multi-signal** — handles logs, metrics, and traces in a single pipeline
- **Topology-first** — sources, transforms, and sinks connected in explicit data flow graphs
- **Performance** — Rust-based, typically faster than Promtail and competitive with Fluent Bit
- **Built-in testing** — unit test your VRL transforms before deploying
- **Wide protocol support** — HTTP, gRPC, Kafka, NATS, AWS Kinesis, and more

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  vector:
    image: timberio/vector:latest
    container_name: vector
    volumes:
      - /var/log:/var/log:ro
      - ./vector.toml:/etc/vector/vector.toml:ro
    environment:
      - VECTOR_LOG=/dev/null
    restart: unless-stopped

networks:
  default:
    name: loki-stack
```

### Vector Configuration (vector.toml)

```toml
[sources.host_logs]
type = "file"
include = ["/var/log/*.log"]
read_from = "beginning"

[sources.journal]
type = "journald"
current_boot_only = false

[transforms.parse_json]
type = "remap"
inputs = ["host_logs"]
source = """
structured = parse_json!(.message) ?? {}
. = merge(., structured)
"""

[transforms.add_labels]
type = "remap"
inputs = ["parse_json"]
source = """
.environment = "production"
.service = .container_name ?? "unknown"
"""

[sinks.loki]
type = "loki"
inputs = ["add_labels"]
endpoint = "http://loki:3100"
encoding.codec = "json"

[sinks.loki.labels]
job = "{{ service }}"
env = "{{ environment }}"
```

### VRL Transform Examples

```toml
# Filter out health check noise
[transforms.filter_health]
type = "filter"
inputs = ["host_logs"]
condition = """
!contains(string!(.message), "healthcheck", case_sensitive: false)
"""

# Extract error codes from log messages
[transforms.extract_errors]
type = "remap"
inputs = ["filter_health"]
source = """
error_code = parse_regex(.message, r'error_code=(?P<code>[0-9]+)') ?? null
if error_code != null {
  .error_code = error_code.code
}
"""
```

### When to Use Vector

Vector is ideal when you want a unified pipeline for logs, metrics, and traces, or when you need complex data transformations with type safety. VRL gives you programmatic control over data shapes that goes beyond what Promtail's pipeline stages or Fluent Bit's filters offer.

**Best for**: Teams wanting a single pipeline for all observability data, complex transformation requirements, performance-critical deployments.

**Limitations**: Heavier resource usage than Fluent Bit. TOML config can be verbose. VRL has a learning curve.

## Head-to-Head Comparison

| Feature | Promtail | Fluent Bit | Vector |
|---------|----------|------------|--------|
| **Language** | Go | C | Rust |
| **RAM Usage** | 50-150 MB | 10-30 MB | 80-200 MB |
| **Loki Output** | Native | Plugin | Native |
| **Multi-Destination** | No (Loki only) | Yes (100+ outputs) | Yes (50+ sinks) |
| **Service Discovery** | Prometheus SD | Limited | Limited |
| **Processing** | Pipeline stages | Filters + Lua | VRL (Remap) |
| **Multi-Signal** | Logs only | Logs + Metrics | Logs + Metrics + Traces |
| **Configuration** | YAML | INI/JSON/YAML | TOML |
| **Docker Image Size** | ~100 MB | ~50 MB | ~150 MB |
| **GitHub Stars** | 1,200+ | 7,800+ | 21,900+ |
| **CNCF Status** | Part of Grafana Labs | CNCF Graduated | CNCF Sandbox |
| **Best Use Case** | Pure Loki stacks | Edge / multi-output | Unified observability |

## Deployment Architecture Recommendations

### Small Stack: Promtail

For a simple homelab or small team running Loki + Grafana, Promtail is the easiest choice. Zero additional dependencies, native Loki labels, and configuration that mirrors your existing Prometheus setup.

### Medium Stack: Fluent Bit

When you need to send logs to multiple destinations (Loki for querying, Elasticsearch for compliance, stdout for debugging), Fluent Bit's multi-output capability makes it the most practical choice.

### Large Stack: Vector

For enterprise-scale deployments processing millions of log lines per second, Vector's Rust performance and VRL transformation power justify the additional configuration complexity.

## Why Self-Host Your Log Collection?

Self-hosting your log collection layer gives you complete control over data flow, processing, and retention. Unlike SaaS log management services that charge by ingestion volume, self-hosted collectors send data to your own Loki instance with no per-GB fees.

For teams managing sensitive data — financial records, healthcare logs, or security audit trails — keeping log processing entirely within your own infrastructure eliminates data exfiltration risk. You control the parsing rules, the label cardinality, and the retention policies.

For cost comparison with other observability stacks, see our [Grafana Mimir vs Thanos vs Cortex guide](../2026-04-27-grafana-mimir-vs-thanos-vs-cortex-self-hosted-prometheus-long-term-storage-guide/). For broader log aggregation options, our [rsyslog vs syslog-ng vs Vector comparison](../2026-04-18-rsyslog-vs-syslog-ng-vs-vector-self-hosted-syslog-log-aggregation-guide-2026/) covers syslog-level collection. For log parsing strategies, check our [mtail vs grok-exporter vs Vector guide](../2026-04-28-mtail-vs-grok-exporter-vs-vector-self-hosted-log-parsing-guide/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Log Collector Agents for Grafana Loki: Promtail vs Fluent Bit vs Vector (2026)",
  "description": "Compare Promtail, Fluent Bit, and Vector as log collector agents for Grafana Loki. Includes Docker Compose configs and deployment recommendations.",
  "datePublished": "2026-05-24",
  "dateModified": "2026-05-24",
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

### Which log collector uses the least resources?

Fluent Bit has the smallest resource footprint, typically consuming 10-30 MB of RAM. It is written in C and designed specifically for edge deployments and resource-constrained environments. Promtail follows at 50-150 MB, while Vector uses 80-200 MB depending on pipeline complexity.

### Can I use Fluent Bit instead of Promtail with Loki?

Yes. Fluent Bit has a native Loki output plugin that sends logs to Loki's push API. You lose Promtail's native service discovery integration, but gain multi-destination support and more processing plugins.

### Is Vector production-ready for high-volume log collection?

Yes. Vector is used in production at scale by organizations like Datadog (its parent company) and many enterprises. Its Rust foundation provides memory safety and high throughput. The CNCF sandbox status means it is still maturing but is stable for production use.

### Can I run multiple collector agents simultaneously?

You can, but it is not recommended. Running two agents on the same host would duplicate log ingestion, increasing load on both the host and Loki. Pick one agent and configure it properly.

### How do I handle log rotation with these agents?

All three agents handle log rotation gracefully. Promtail tracks file positions using a positions file. Fluent Bit uses inode tracking to follow rotated files. Vector maintains checkpoints in its disk buffer directory. None of them will lose log lines during rotation.

### Which agent is best for Kubernetes log collection?

For Kubernetes, all three work well. Promtail benefits from native Kubernetes service discovery and label extraction. Fluent Bit has a dedicated Kubernetes filter that enriches logs with pod metadata. Vector supports Kubernetes metadata enrichment through its remap language.

## Frequently Asked Questions

### Do these agents support TLS encryption to Loki?

Yes. All three agents support TLS for communication with Loki. Promtail and Vector support TLS natively in their client configuration. Fluent Bit supports TLS in its Loki output plugin with certificate verification options.

### How do I monitor the health of my log collector?

Promtail exposes Prometheus metrics on port 9080. Fluent Bit has a built-in HTTP monitor on port 2020. Vector exposes metrics via its Prometheus sink or internal metrics endpoint. All three integrate with Grafana dashboards for operational visibility.

### Can I filter logs before sending them to Loki?

Yes. Promtail uses pipeline stages for filtering. Fluent Bit has grep and rewrite filters. Vector has filter transforms and VRL conditionals. Filtering at the agent level reduces Loki storage costs and query complexity.

## Choosing the Right Log Collector for Loki

The decision comes down to your operational requirements:

- **Choose Promtail** if you want the simplest setup with native Loki integration and already run Prometheus.
- **Choose Fluent Bit** if you need multi-destination output, edge deployment, or complex log processing with minimal resource usage.
- **Choose Vector** if you want a unified observability pipeline handling logs, metrics, and traces with powerful VRL transformations.

Each agent can reliably deliver logs to your Loki instance. The best choice aligns with your team's existing skills, infrastructure complexity, and performance requirements.
