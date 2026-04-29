---
title: "Promxy vs VictoriaMetrics vmagent vs Grafana Mimir: Self-Hosted Metric Relay Guide 2026"
date: 2026-04-29
tags: ["comparison", "guide", "self-hosted", "monitoring", "prometheus", "metrics"]
draft: false
description: "Compare the best open-source tools for self-hosted Prometheus metric relay, federation, and aggregation. Complete guide to Promxy, VictoriaMetrics vmagent, and Grafana Mimir for scalable metrics infrastructure."
---

Running a single Prometheus instance works fine for small environments, but once you scale beyond a handful of nodes you hit hard limits: storage capacity, query latency, and single points of failure. The solution is metric relay and federation — collecting, aggregating, and forwarding metrics across multiple instances so you can scale horizontally without losing visibility.

This guide compares three mature open-source approaches to self-hosted Prometheus metric relay: **Promxy**, **VictoriaMetrics vmagent**, and **Grafana Mimir**. Each solves the problem differently, and choosing the right one depends on your scale, existing stack, and operational preferences.

For a deeper look at long-term metric storage options, see our [VictoriaMetrics vs Thanos vs Cortex comparison](../victoriametrics-vs-thanos-vs-cortex-self-hosted-metrics-storage-guide-2026/).

## Why Self-Host Metric Relay

Cloud-hosted metrics platforms charge per million ingested samples and often throttle query throughput. Self-hosting metric relay gives you full control over ingestion, retention, and routing:

- **Unlimited retention** — store metrics for months or years without per-gigabyte fees
- **No vendor lock-in** — use standard Prometheus query language across your entire stack
- **Multi-cluster federation** — aggregate metrics from dozens of Kubernetes clusters, edge sites, or on-prem data centers into a single query layer
- **Cost isolation** — separate metric storage from compute, scaling each independently
- **Data sovereignty** — keep all telemetry data on your own infrastructure for compliance

If you're also evaluating monitoring stacks from scratch, our [HertzBeat vs Prometheus vs Netdata guide](../2026-04-25-hertzbeat-vs-prometheus-vs-netdata-self-hosted-monitoring-guide-2026/) covers the broader landscape.

## Tools Compared at a Glance

| Feature | Promxy | VictoriaMetrics vmagent | Grafana Mimir |
|---|---|---|---|
| **Primary Role** | Aggregating proxy for HA Prometheus | Metrics collector + relay agent | Horizontally scalable metrics backend |
| **GitHub Stars** | 1,300+ | 16,900+ (VictoriaMetrics) | 5,000+ |
| **Language** | Go | Go | Go |
| **License** | Apache 2.0 | Apache 2.0 | AGPL v3 |
| **Federation Model** | Query-time aggregation | Remote write forwarding | Distributed ingestion + querier |
| **Multi-tenant** | No | Yes | Yes |
| **Long-term Storage** | No (queries downstream) | Yes (VictoriaMetrics) | Yes (built-in object store) |
| **Horizontal Scaling** | Proxy layer only | Yes (vmagent cluster) | Yes (microservices architecture) |
| **Prometheus Compatible** | Full read path | Full write + scrape | Full read + write + scrape |
| **Last Updated** | 2026-04-24 | 2026-04-29 | 2026-04-29 |

## Promxy: Aggregating Proxy for HA Prometheus

[Promxy](https://github.com/jacksontj/promxy) is a lightweight aggregating proxy that sits in front of multiple Prometheus (or VictoriaMetrics) instances. It does not store metrics itself — instead, it receives PromQL queries, fans them out to all configured downstream servers, aggregates the results, and returns a single unified response.

### When to Choose Promxy

- You already run multiple Prometheus servers and need a **single query endpoint**
- You want **high availability** without the complexity of federated storage
- You need to **aggregate metrics across separate Prometheus clusters** (e.g., per-region or per-team)
- Your storage layer is already handled elsewhere and you only need the **query aggregation layer**

### Key Features

- **Dual aggregation strategies** — merge (union of all series) and aggregate (deduplication with configurable resolution)
- **PromQL passthrough** — full compatibility with existing Grafana dashboards and alerting rules
- **Health checking** — automatically removes unhealthy downstream targets from queries
- **Lightweight footprint** — single binary, no external dependencies, runs in ~50MB RAM
- **Live reload** — update configuration without restarting the process

### Docker Compose Setup

Promxy is often deployed alongside VictoriaMetrics. Here is a production-ready compose configuration adapted from the official deployment examples:

```yaml
services:
  promxy:
    container_name: promxy
    image: quay.io/jacksontj/promxy:latest
    ports:
      - "8082:8082"
    volumes:
      - ./config.yaml:/config/promxy.yaml:ro
    command:
      - --config=/config/promxy.yaml
      - --web.enable-lifecycle
      - --log-level=info
    restart: unless-stopped

  victoriametrics:
    container_name: victoriametrics
    image: victoriametrics/victoria-metrics:latest
    ports:
      - "8428:8428"
    volumes:
      - vmdata:/storage
    command:
      - --storageDataPath=/storage
      - --httpListenAddr=:8428
    restart: unless-stopped

volumes:
  vmdata:
```

Promxy configuration file (`config.yaml`) defining downstream targets:

```yaml
global:
  evaluation_interval: 30s

promxy_server:
  - static_configs:
      - targets:
          - "victoriametrics:8428"
          - "prometheus-secondary:9090"
    labels:
      env: production
    anti_affinity: 10s
    path_prefix: /api/v1
    scheme: http
```

## VictoriaMetrics vmagent: Metrics Collector and Relay

[VictoriaMetrics](https://github.com/VictoriaMetrics/VictoriaMetrics) ships with **vmagent**, a purpose-built metrics collector that can scrape Prometheus-compatible endpoints, apply relabeling rules, and forward metrics to any number of remote storage backends simultaneously. Unlike Promxy, vmagent actively collects and stores metrics, making it both a relay and a storage solution.

### When to Choose VictoriaMetrics vmagent

- You need to **collect and forward metrics to multiple destinations** (e.g., primary + backup storage)
- You want a **drop-in Prometheus replacement** with significantly lower resource usage
- You require **high-cardinality metrics** handling without memory pressure
- You need **built-in remote write buffering** to survive network partitions
- You plan to scale to **millions of time series** across many scrape targets

### Key Features

- **Multi-destination forwarding** — send the same metrics to VictoriaMetrics, Thanos, Cortex, or any Prometheus remote write endpoint simultaneously
- **Service discovery** — native support for Kubernetes, Consul, EC2, file-based, and static targets
- **Relabeling** — full Prometheus-compatible relabeling pipeline for filtering, dropping, and modifying metrics in flight
- **On-disk buffering** — persists unsent data to disk during network outages, replaying on reconnect
- **Cluster mode** — vmagent can run as a cluster for horizontal scrape scaling
- **Minimal resource usage** — typically uses 5-10x less memory than Prometheus for equivalent scrape loads

### Docker Compose Setup

VictoriaMetrics provides an official single-node compose configuration with vmagent:

```yaml
services:
  vmagent:
    image: victoriametrics/vmagent:v1.142.0
    depends_on:
      - "victoriametrics"
    ports:
      - "8429:8429"
    volumes:
      - vmagentdata:/vmagentdata
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    command:
      - "--promscrape.config=/etc/prometheus/prometheus.yml"
      - "--remoteWrite.url=http://victoriametrics:8428/api/v1/write"
    restart: unless-stopped

  victoriametrics:
    image: victoriametrics/victoria-metrics:v1.142.0
    ports:
      - "8428:8428"
      - "8089:8089"
      - "2003:2003"
    volumes:
      - vmdata:/storage
    command:
      - "--storageDataPath=/storage"
      - "--graphiteListenAddr=:2003"
      - "--httpListenAddr=:8428"
    restart: unless-stopped

  grafana:
    image: grafana/grafana:12.2.0
    depends_on:
      - "victoriametrics"
    ports:
      - "3000:3000"
    volumes:
      - grafanadata:/var/lib/grafana
    restart: unless-stopped

volumes:
  vmagentdata:
  vmdata:
  grafanadata:
```

The scrape configuration (`prometheus.yml`) uses standard Prometheus format:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "victoriametrics"
    static_configs:
      - targets: ["victoriametrics:8428"]

  - job_name: "node-exporter"
    static_configs:
      - targets: ["node-exporter:9100"]
```

## Grafana Mimir: Horizontally Scalable Metrics Backend

[Grafana Mimir](https://github.com/grafana/mimir) is a fully distributed, horizontally scalable Prometheus-compatible metrics backend. It handles ingestion, storage, and querying through a microservices architecture, making it suitable for massive multi-tenant deployments where thousands of tenants each ingest millions of samples per second.

### When to Choose Grafana Mimir

- You operate at **enterprise scale** — hundreds of Prometheus instances, millions of time series
- You need **multi-tenancy** — isolate metrics and queries per team, namespace, or customer
- You want **object store-based storage** — S3, GCS, or Azure Blob for durable, cost-effective retention
- You need a **fully managed open-source alternative** to Grafana Cloud Metrics
- You require **ruler-based alerting** at scale with deduplication across replicas

### Key Features

- **Microservices architecture** — separate components for ingestion (distributor), storage (ingester), querying (querier), and alerting (ruler), each independently scalable
- **Object store backend** — stores block data in S3-compatible storage, separating compute from storage costs
- **Multi-tenant isolation** — tenant ID passed via HTTP header, full data isolation between tenants
- **Horizontal query federation** — queriers automatically parallelize queries across all ingesters and store gateways
- **Built-in ruler** — evaluate alerting and recording rules across all tenants with native deduplication
- **Continuous profiling** — optional Pyroscope integration for performance analysis

### Docker Compose Setup (Single-Binary Mode)

For evaluation and smaller deployments, Mimir can run in single-binary mode:

```yaml
services:
  mimir:
    image: grafana/mimir:2.15.0
    ports:
      - "9009:9009"
    volumes:
      - mimir-data:/data
      - ./mimir.yaml:/etc/mimir/mimir.yaml:ro
    command:
      - "-config.file=/etc/mimir/mimir.yaml"
      - "-target=all"
    restart: unless-stopped

  grafana:
    image: grafana/grafana:12.2.0
    depends_on:
      - "mimir"
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_INSTALL_PLUGINS=grafana-mimir-datasource
    volumes:
      - grafana-data:/var/lib/grafana
    restart: unless-stopped

volumes:
  mimir-data:
  grafana-data:
```

Mimir configuration (`mimir.yaml`) for single-binary mode with local storage:

```yaml
multitenancy_enabled: false

limits:
  max_global_series_per_user: 100000
  max_global_series_per_metric: 100000

blocks_storage:
  backend: filesystem
  filesystem:
    dir: /data/blocks

compactor:
  data_dir: /data/compactor

ruler_storage:
  backend: filesystem
  filesystem:
    dir: /data/ruler
```

For production, Mimir's distributed mode requires separate deployments of distributor, ingester, querier, store-gateway, and ruler — typically orchestrated via Helm on Kubernetes.

## Architecture Comparison

```
Promxy Architecture:
  [Grafana] ──► [Promxy:8082] ──┬──► [Prometheus-A:9090]
                                ├──► [Prometheus-B:9090]
                                └──► [VictoriaMetrics:8428]

vmagent Architecture:
  [Targets] ──► [vmagent:8429] ──► [VictoriaMetrics:8428]
                                ──► [Thanos Receiver]
                                ──► [Cortex]

Grafana Mimir Architecture:
  [Prometheus/Agents] ──► [Distributor] ──► [Ingester] ──► [S3/Object Store]
                                                  │
  [Grafana] ──► [Querier] ───────────────────────┘
```

**Promxy** is query-time only — it does not collect or store metrics. It sits between your dashboard and existing Prometheus instances, aggregating results on demand.

**vmagent** is a collection and forwarding agent — it scrapes targets, applies relabeling, buffers data on disk, and pushes to remote storage. It replaces Prometheus's scrape layer while offloading storage elsewhere.

**Mimir** is a complete metrics platform — it handles ingestion, long-term storage, querying, and alerting in one integrated system, designed to replace Prometheus entirely at scale.

## Choosing the Right Tool

| Scenario | Recommended Tool |
|---|---|
| You have 2-5 Prometheus instances and need a unified query endpoint | Promxy |
| You want to replace Prometheus with a more efficient collector + forwarder | VictoriaMetrics vmagent |
| You need enterprise-scale multi-tenant metrics with object store | Grafana Mimir |
| You need to forward metrics to multiple remote write destinations | VictoriaMetrics vmagent |
| You want the simplest possible setup for a single cluster | VictoriaMetrics vmagent |
| You already use Grafana Cloud and want an on-prem equivalent | Grafana Mimir |
| You need PromQL aggregation across heterogeneous backends | Promxy |
| You need ruler-based alerting with deduplication at scale | Grafana Mimir |

For teams already using Prometheus exporters in their stack, our [HAProxy management with Prometheus exporter guide](../2026-04-24-haproxy-dataplane-api-vs-prometheus-exporter-vs-runtime-api-self-hosted-haproxy-management-guide-2026/) shows how to integrate metrics collection into your existing infrastructure.

## FAQ

### What is Prometheus metric federation?

Prometheus federation is the process of scraping metrics from one Prometheus server into another, allowing hierarchical aggregation of metrics across multiple instances. Metric relay extends this concept by using specialized proxies or agents (like Promxy, vmagent, or Mimir) to collect, forward, and aggregate metrics more efficiently than native Prometheus federation.

### Can Promxy store metrics long-term?

No. Promxy is purely a query aggregation proxy. It does not ingest, store, or retain any metrics. It forwards PromQL queries to configured downstream servers (Prometheus, VictoriaMetrics, Thanos, etc.), aggregates the results, and returns them. You still need a storage backend behind the downstream servers.

### How does vmagent differ from Prometheus?

VictoriaMetrics vmagent is designed as a drop-in replacement for Prometheus's scrape layer. It uses the same `prometheus.yml` configuration format, supports all Prometheus service discovery mechanisms, and applies identical relabeling rules. The key differences: vmagent uses 5-10x less memory, supports multi-destination remote write, and includes on-disk buffering for resilience during network outages.

### Is Grafana Mimir a direct Prometheus replacement?

Yes, but at a different scale. Mimir is Prometheus-compatible — it accepts the same scrape configs, remote write format, and PromQL queries. However, it is designed for environments where a single Prometheus instance cannot handle the load (millions of time series, hundreds of scrape targets, or multi-tenant requirements). For small deployments, single-node VictoriaMetrics or plain Prometheus is simpler.

### Can I use these tools together?

Yes. A common pattern is running vmagent as a scrape/relay agent that forwards metrics to Mimir for storage, with Promxy as a query layer on top if you have multiple Mimir read replicas. VictoriaMetrics itself can also serve as the storage backend behind Promxy.

### Which tool has the lowest resource requirements?

Promxy is the lightest — a single binary with no storage, typically running in under 50MB of RAM. vmagent is next, using significantly less memory than Prometheus for equivalent scrape loads. Mimir has the highest requirements due to its microservices architecture, though single-binary mode reduces this for smaller deployments.

### Does Mimir support multi-tenancy?

Yes, Mimir was designed for multi-tenancy from the ground up. Each tenant is identified by an `X-Scope-OrgID` HTTP header. All data ingestion, storage, querying, and alerting is isolated by tenant ID. Promxy and vmagent do not have native multi-tenant support.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Promxy vs VictoriaMetrics vmagent vs Grafana Mimir: Self-Hosted Metric Relay Guide 2026",
  "description": "Compare the best open-source tools for self-hosted Prometheus metric relay, federation, and aggregation. Complete guide to Promxy, VictoriaMetrics vmagent, and Grafana Mimir for scalable metrics infrastructure.",
  "datePublished": "2026-04-29",
  "dateModified": "2026-04-29",
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
