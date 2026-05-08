---
title: "Self-Hosted gNMI Telemetry Streaming: Telegraf vs OpenTelemetry Collector vs gNMIc (2026)"
date: "2026-05-09"
tags: ["comparison", "guide", "self-hosted", "networking", "telemetry", "monitoring"]
draft: false
description: "Compare Telegraf, OpenTelemetry Collector, and gNMIc for self-hosted gNMI telemetry streaming from network devices. Complete setup guides for real-time network monitoring."
---

## Introduction

Modern network infrastructure generates massive amounts of operational data — interface counters, CPU utilization, routing table changes, BGP session states, and temperature readings. Traditional SNMP polling is too slow and resource-intensive for real-time visibility into networks with hundreds of devices.

**gNMI (gRPC Network Management Interface)** is a modern protocol that enables streaming telemetry from network devices over efficient gRPC connections. Instead of polling devices every 30 seconds, gNMI streams push real-time data changes as they happen — reducing bandwidth usage and providing sub-second monitoring granularity.

In this guide, we compare three open-source tools for collecting and processing gNMI telemetry: **Telegraf**, **OpenTelemetry Collector**, and **gNMIc**.

## What Is gNMI Telemetry?

gNMI is a gRPC-based protocol defined by the OpenConfig working group. It provides three core operations:

- **Capabilities** — discover what a device supports (models, encodings, data types)
- **Get/Set** — read and configure device state (similar to NETCONF)
- **Subscribe** — stream telemetry data in real-time (the key differentiator from SNMP)

Unlike SNMP, which polls devices on a fixed interval, gNMI subscriptions push data only when values change or at configurable sample intervals. This reduces network overhead and provides near-real-time visibility.

### Why Self-Host gNMI Collection?

Commercial network telemetry platforms (Cisco DNA Center, Juniper Paragon) require expensive licensing and cloud connectivity. Self-hosted gNMI collection gives you:

- **No per-device licensing** — collect telemetry from unlimited devices
- **Full data ownership** — all metrics stay in your infrastructure
- **Custom processing pipelines** — route data to any time-series database
- **Vendor-agnostic** — works with Cisco, Juniper, Arista, Nokia, and open-source NOS

## Project Overview

### Telegraf

Telegraf (github.com/influxdata/telegraf, 15,000+ stars) is a plugin-driven server agent for collecting and sending metrics. Its gNMI input plugin connects to network devices, subscribes to OpenConfig telemetry paths, and outputs to InfluxDB, Prometheus, or 200+ other destinations.

**Strengths:**
- Mature gNMI plugin with extensive testing
- 200+ output plugins (InfluxDB, Prometheus, Kafka, etc.)
- Simple TOML configuration
- Active development by InfluxData
- Built-in metric transformation and aggregation

**Weaknesses:**
- Less flexible pipeline than OpenTelemetry
- Tied to InfluxData ecosystem (though supports many outputs)
- Limited data normalization across vendors

### OpenTelemetry Collector

OpenTelemetry Collector (github.com/open-telemetry/opentelemetry-collector, 10,000+ stars) is a vendor-agnostic telemetry collection agent. While primarily designed for application tracing and logs, its gNMI receiver (via the opentelemetry-collector-contrib distribution) supports network telemetry collection.

**Strengths:**
- Vendor-neutral, CNCF-backed project
- Unified pipeline for metrics, traces, and logs
- Extensible processor chain (filtering, aggregation, enrichment)
- Growing ecosystem of receivers and exporters
- Strong Kubernetes integration

**Weaknesses:**
- gNMI support is newer and less mature than Telegraf
- Steeper learning curve for configuration
- Fewer network-specific features (no built-in device discovery)
- Requires contrib distribution for gNMI receiver

### gNMIc

gNMIc (github.com/karimra/gnmic, 1,500+ stars) is a purpose-built gNMI client and collector. Unlike Telegraf and OpenTelemetry (which are general-purpose collectors), gNMIc is designed specifically for gNMI operations — subscription, get, set, and capabilities.

**Strengths:**
- Purpose-built for gNMI — deepest protocol support
- CLI tool for interactive device debugging
- Subscription multiplexing (one process, many devices)
- Built-in Prometheus exporter
- YAML-based configuration with templating support
- Lightweight binary, no dependencies

**Weaknesses:**
- Smaller community and ecosystem
- Fewer output destinations than Telegraf
- No built-in metric transformation (relies on Prometheus for processing)
- Less mature than the other two options

## Feature Comparison

| Feature | Telegraf | OpenTelemetry Collector | gNMIc |
|---|---|---|---|
| GitHub Stars | 15,000+ | 10,000+ | 1,500+ |
| Primary Purpose | General metrics collector | Unified telemetry pipeline | gNMI-specific client |
| gNMI Maturity | High | Medium | High |
| Output Destinations | 200+ | 50+ | Prometheus, file, stdout |
| Configuration Format | TOML | YAML | YAML |
| Device Discovery | Manual config | Manual config | Manual config |
| Metric Transformation | Built-in processors | Processor chain | External (Prometheus) |
| CLI Debugging | No | No | Yes (full gNMI CLI) |
| Kubernetes Native | Yes (DaemonSet) | Yes (Operator) | Yes (sidecar) |
| Docker Image | Official | Official | Official |
| Vendor Normalization | Partial | Partial | Manual mapping |
| Subscription Types | ON_CHANGE, SAMPLE, TARGET_DEFINED | SAMPLE, ON_CHANGE | ALL types |
| TLS/mTLS Support | Yes | Yes | Yes |
| Active Development | Yes | Yes | Yes |

## Docker Deployment

### Telegraf with gNMI

```yaml
version: "3"
services:
  telegraf:
    image: telegraf:1.30
    container_name: telegraf-gnmi
    restart: unless-stopped
    volumes:
      - ./telegraf.conf:/etc/telegraf/telegraf.conf:ro
      - ./certs:/etc/telegraf/certs:ro
    ports:
      - "9273:9273"
    networks:
      - monitoring

  influxdb:
    image: influxdb:2
    container_name: influxdb
    restart: unless-stopped
    volumes:
      - influxdb-data:/var/lib/influxdb2
    ports:
      - "8086:8086"
    environment:
      - DOCKER_INFLUXDB_INIT_MODE=setup
      - DOCKER_INFLUXDB_INIT_USERNAME=admin
      - DOCKER_INFLUXDB_INIT_PASSWORD=secretpassword
      - DOCKER_INFLUXDB_INIT_ORG=openswap
      - DOCKER_INFLUXDB_INIT_BUCKET=telemetry

volumes:
  influxdb-data:
```

```toml
# telegraf.conf - gNMI input plugin
[[inputs.gnmi]]
  addresses = ["switch01:57400", "switch02:57400", "router01:57400"]
  username = "telemetry"
  password = "telemetry_pass"
  redial = "30s"
  tls_enable = true
  tls_cert = "/etc/telegraf/certs/client.crt"
  tls_key = "/etc/telegraf/certs/client.key"

  [[inputs.gnmi.subscription]]
    name = "interface_counters"
    origin = "openconfig-interfaces"
    path = "/interfaces/interface/state/counters"
    subscription_mode = "sample"
    sample_interval = "10s"

  [[inputs.gnmi.subscription]]
    name = "cpu_usage"
    origin = "openconfig-system"
    path = "/system/state/cpu"
    subscription_mode = "sample"
    sample_interval = "5s"

[[outputs.influxdb_v2]]
  urls = ["http://influxdb:8086"]
  token = "your-influxdb-token"
  organization = "openswap"
  bucket = "telemetry"
```

### OpenTelemetry Collector with gNMI

```yaml
version: "3"
services:
  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    container_name: otel-gnmi
    restart: unless-stopped
    volumes:
      - ./otel-config.yaml:/etc/otelcol-contrib/config.yaml:ro
      - ./certs:/etc/otelcol-contrib/certs:ro
    ports:
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP
      - "8888:8888"   # Prometheus metrics
    networks:
      - monitoring
```

```yaml
# otel-config.yaml
receivers:
  gnmi:
    endpoints:
      - switch01:57400
      - switch02:57400
    username: telemetry
    password: telemetry_pass
    tls:
      cert_file: /etc/otelcol-contrib/certs/client.crt
      key_file: /etc/otelcol-contrib/certs/client.key
    subscriptions:
      - name: interface-counters
        path: /interfaces/interface/state/counters
        mode: sample
        sample_interval: 10s

processors:
  batch:
    timeout: 10s
  filter:
    metrics:
      exclude:
        match_type: strict
        metric_names:
          - "unwanted_metric"

exporters:
  prometheus:
    endpoint: "0.0.0.0:8888"

service:
  pipelines:
    metrics:
      receivers: [gnmi]
      processors: [batch, filter]
      exporters: [prometheus]
```

### gNMIc with Prometheus

```yaml
version: "3"
services:
  gnmic:
    image: ghcr.io/karimra/gnmic:latest
    container_name: gnmic-collector
    restart: unless-stopped
    volumes:
      - ./gnmic.yaml:/etc/gnmic/gnmic.yaml:ro
      - ./certs:/etc/gnmic/certs:ro
    ports:
      - "57161:57161"  # Prometheus metrics
    command: ["--config", "/etc/gnmic/gnmic.yaml", "subscribe"]

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    restart: unless-stopped
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"

volumes:
  prometheus-data:
```

```yaml
# gnmic.yaml
username: telemetry
password: telemetry_pass
tls:
  ca-file: /etc/gnmic/certs/ca.crt
  cert-file: /etc/gnmic/certs/client.crt
  key-file: /etc/gnmic/certs/client.key

targets:
  switch01:
    address: switch01:57400
  switch02:
    address: switch02:57400

subscriptions:
  interface-counters:
    paths:
      - /interfaces/interface/state/counters
    sample-interval: 10s
    mode: sample

outputs:
  prometheus:
    type: prometheus
    listen: :57161
    path: /metrics
```

## CLI Debugging with gNMIc

One unique advantage of gNMIc is its interactive CLI for debugging gNMI connections:

```bash
# Discover device capabilities
gnmic --address switch01:57400 --username admin --password admin capabilities

# Get specific data path
gnmic --address switch01:57400 --username admin --password admin get \
  --path /interfaces/interface/state

# Subscribe to streaming telemetry
gnmic --address switch01:57400 --username admin --password admin subscribe \
  --path /interfaces/interface/state/counters \
  --mode sample \
  --sample-interval 5s

# Set a configuration value
gnmic --address switch01:57400 --username admin --password admin set \
  --update-path /interfaces/interface/config/enabled \
  --update-value true
```

## Choosing the Right gNMI Collector

**Choose Telegraf if:**
- You already use the TIG stack (Telegraf, InfluxDB, Grafana)
- You need maximum output flexibility (200+ destinations)
- You want the most mature and tested gNMI plugin
- Your team is familiar with TOML configuration

**Choose OpenTelemetry Collector if:**
- You want a unified pipeline for metrics, traces, and logs
- You are building a CNCF-compliant observability stack
- You need advanced metric processing (filtering, enrichment, aggregation)
- You are deploying on Kubernetes

**Choose gNMIc if:**
- gNMI is your primary telemetry protocol
- You need interactive CLI debugging of gNMI connections
- You want the most lightweight collector
- You are already using Prometheus for metrics storage

## Why Self-Host Your Network Telemetry?

Running your own gNMI telemetry pipeline instead of relying on vendor-provided tools offers significant advantages:

**Complete Data Ownership:** Network telemetry data reveals your infrastructure topology, traffic patterns, capacity utilization, and failure modes. When you send this data to vendor clouds, you lose control over who can access it. Self-hosted collection keeps all operational data within your security perimeter.

**No Per-Device Licensing:** Cisco DNA Center, Juniper Paragon, and Arista CloudVision charge per-device licensing fees that scale with network size. Self-hosted gNMI collection using open-source tools has zero licensing cost regardless of how many devices you monitor.

**Vendor Agnosticism:** Commercial telemetry platforms are optimized for their own hardware. A self-hosted pipeline treats all gNMI-capable devices equally — Cisco, Juniper, Arista, Nokia, and open-source network operating systems all stream data through the same collectors.

**Custom Alerting and Processing:** Self-hosted pipelines let you build custom processing logic — correlating interface errors with BGP session drops, detecting microbursts, or triggering automated remediation scripts. Commercial platforms limit you to their predefined alert templates.

**Cost Predictability:** Cloud telemetry pricing is unpredictable — it scales with data volume, retention period, and query complexity. Self-hosted infrastructure has fixed costs (hardware, power, storage) that do not fluctuate with traffic spikes or monitoring granularity changes.

For network monitoring infrastructure, see our [Zabbix vs LibreNMS vs NetData comparison](../zabbix-vs-librenms-vs-netdata-network-monitoring-guide/).
For SNMP-based monitoring, check our [SNMP Collectors guide](../2026-04-26-snmp-collectors-snmp-exporter-snmpcollector-telegraf-self-hosted-guide-2026/).
For distributed tracing backends, our [Grafana Tempo vs Jaeger vs Zipkin guide](../2026-05-18-grafana-tempo-vs-jaeger-vs-zipkin-distributed-tracing-guide/) covers the full observability stack.

## Frequently Asked Questions

### What network devices support gNMI?

Most modern enterprise network devices support gNMI: Cisco IOS-XR and NX-OS, Juniper Junos (with OpenConfig), Arista EOS, Nokia SR OS, and Cumulus Linux. Open-source NOS like FRRouting and SONiC also support gNMI. Check your device documentation for gNMI port configuration (typically port 57400 for gNMI over TLS).

### Can gNMI replace SNMP entirely?

Not yet. While gNMI is superior for streaming telemetry, SNMP is still needed for legacy devices, some MIB-based queries, and trap reception. Most organizations run both protocols in parallel — gNMI for real-time streaming on modern devices, SNMP for legacy equipment and broad compatibility.

### How does gNMI compare to streaming telemetry?

gNMI is one implementation of streaming telemetry. Other protocols include gRPC-based dial-out (Cisco's native implementation) and OpenConfig telemetry over TCP. gNMI is the most standardized and vendor-agnostic option, making it the recommended choice for multi-vendor environments.

### Is TLS required for gNMI?

TLS is strongly recommended for production deployments. gNMI credentials and telemetry data are sensitive — running without encryption exposes them to network sniffing. All three collectors support TLS with client certificate authentication (mTLS) for mutual authentication between collector and device.

### Can I collect gNMI telemetry from cloud-managed switches?

It depends on the device and its configuration mode. Cloud-managed switches (like Meraki or Aruba Central) often disable local gNMI access in favor of cloud-based management. For self-hosted telemetry, use devices that support local management mode or run open-source NOS like SONiC.

### How much storage does gNMI telemetry require?

Streaming telemetry generates significantly more data than SNMP polling. A single interface with 10-second sampling produces ~8,640 data points per day. For a 100-device network with 48 ports each, that is approximately 41 million data points daily. Plan for 50-100 GB/day of time-series storage depending on sampling intervals and retention policies.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted gNMI Telemetry Streaming: Telegraf vs OpenTelemetry Collector vs gNMIc (2026)",
  "description": "Compare Telegraf, OpenTelemetry Collector, and gNMIc for self-hosted gNMI telemetry streaming from network devices.",
  "datePublished": "2026-05-09",
  "dateModified": "2026-05-09",
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
