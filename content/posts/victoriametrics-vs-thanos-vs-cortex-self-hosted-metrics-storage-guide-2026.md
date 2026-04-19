---
title: "VictoriaMetrics vs Thanos vs Cortex: Best Self-Hosted Metrics Storage 2026"
date: 2026-04-19
tags: ["comparison", "guide", "self-hosted", "monitoring", "prometheus"]
draft: false
description: "Compare VictoriaMetrics, Thanos, and Cortex — the top three self-hosted distributed metrics storage backends for Prometheus. Includes Docker Compose configs, architecture comparisons, and deployment guides."
---

When running Prometheus at scale, you eventually hit the limits of local storage. Metrics accumulate fast, retention policies become critical, and you need horizontal scalability and high availability. That is where distributed metrics storage backends come in.

The three leading open-source solutions are **VictoriaMetrics**, **Thanos**, and **Cortex**. Each extends Prometheus with long-term storage, but they take fundamentally different architectural approaches. This guide compares all three with real deployment configurations so you can pick the right one for your infrastructure.

## Why Self-Host Your Metrics Storage

Cloud-hosted monitoring platforms charge per million ingested data points, and costs escalate quickly once you are scraping hundreds of targets across multiple clusters. Self-hosting your metrics storage gives you:

- **Cost control** — commodity hardware or cheap object storage (S3, GCS, MinIO) instead of per-metric pricing
- **Data sovereignty** — metrics stay on your infrastructure, critical for regulated environments
- **Custom retention** — keep raw metrics for weeks and downsampled data for years without vendor limits
- **No vendor lock-in** — all three projects use open storage formats and expose Prometheus-compatible APIs

For teams already running Prometheus, adding a distributed storage backend is the most natural scaling path. If you are still evaluating your monitoring stack from scratch, our [Prometheus vs Grafana vs VictoriaMetrics comparison](../prometheus-vs-grafana-vs-victoriametrics/) covers the broader monitoring landscape before you hit scaling limits.

## Quick Comparison Table

| Feature | VictoriaMetrics | Thanos | Cortex |
|---|---|---|---|
| **GitHub Stars** | 16,800+ | 14,000+ | 5,700+ |
| **Language** | Go | Go | Go |
| **Deployment Modes** | Single binary, cluster | Sidecar, receive, store gateway | Single binary, microservices |
| **Storage Backend** | Custom LSM-tree, S3, GCS, Azure, filesystem | Object storage (S3, GCS, Azure, Swift) | Object storage (S3, GCS, Azure, Swift, filesystem) |
| **Multi-tenancy** | Yes (cluster mode) | No (native) | Yes (core design goal) |
| **Prometheus Compatibility** | Full (drop-in replacement) | Extensions to existing Prometheus | Full (Prometheus-derived) |
| **High Availability** | Built-in replication | Deduplication via sidecar pairs | Ring-based replication |
| **Downsampling** | Automatic (5m, 1h, 1d) | Via compactor component | Via compactor component |
| **Query Language** | PromQL + MetricsQL | PromQL (with extensions) | PromQL |
| **Resource Efficiency** | Very high (optimized storage) | Moderate (depends on object storage) | Moderate to high |
| **Learning Curve** | Low | Moderate | High |
| **Best For** | Teams wanting simplicity and performance | Teams already using Prometheus at scale | Multi-tenant SaaS and large orgs |

## VictoriaMetrics: High-Performance Single Binary with Cluster Option

VictoriaMetrics (16,800+ stars, last updated April 2026) is the most performance-focused of the three. It was built from scratch as a drop-in replacement for Prometheus storage, using a custom LSM-tree data structure optimized for time-series data. The result is significantly lower disk I/O and memory usage compared to Thanos and Cortex.

### Architecture

VictoriaMetrics offers two deployment modes:

- **Single-binary** (`victoria-metrics`) — one process handles ingestion, storage, and querying. Ideal for small to medium deployments.
- **Cluster mode** — separates components into `vmstorage` (data shards), `vminsert` (ingestion routing), `vmselect` (query fan-out), and `vmagent`/`vmauth` (collection and auth). Scales horizontally.

### Key Advantages

- **Single binary deployment** — get started with one container, scale to a cluster later
- **Superior compression** — custom storage format reduces disk usage by 2-7x compared to TSDB-based solutions
- **Automatic downsampling** — retains raw, 5-minute, and 1-hour rollups without manual compaction rules
- **vmagent** — lightweight, Prometheus-compatible scraper with better resource efficiency than Prometheus itself
- **MetricsQL** — extended PromQL with additional functions (`histogram_quantile`, `topk_avg`, rate over rate)

### Docker Compose — Single Node Setup

The official VictoriaMetrics repo ships with production-ready compose files. Here is a simplified single-node deployment:

```yaml
services:
  vmagent:
    image: victoriametrics/vmagent:v1.140.0
    ports:
      - "8429:8429"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    command:
      - "--promscrape.config=/etc/prometheus/prometheus.yml"
      - "--remoteWrite.url=http://victoriametrics:8428/api/v1/write"
    restart: always

  victoriametrics:
    image: victoriametrics/victoria-metrics:v1.140.0
    ports:
      - "8428:8428"
    volumes:
      - vmdata:/storage
    command:
      - "--storageDataPath=/storage"
      - "--retentionPeriod=30d"
    restart: always

  grafana:
    image: grafana/grafana:12.2.0
    ports:
      - "3000:3000"
    environment:
      - GF_SERVER_ROOT_URL=http://localhost:3000
    volumes:
      - grafanadata:/var/lib/grafana
    restart: always

volumes:
  vmdata:
  grafanadata:
```

### Docker Compose — Cluster Mode

For production-scale deployments, VictoriaMetrics cluster mode separates concerns:

```yaml
services:
  vmagent:
    image: victoriametrics/vmagent:v1.140.0
    ports:
      - "8429:8429"
    command:
      - "--promscrape.config=/etc/prometheus/prometheus.yml"
      - "--remoteWrite.url=http://vmauth:8427/insert/0/prometheus/api/v1/write"
    restart: always

  vmauth:
    image: victoriametrics/vmauth:v1.140.0
    ports:
      - "8427:8427"
    command:
      - "--auth.config=/etc/vmauth/auth.yml"
    volumes:
      - ./auth.yml:/etc/vmauth/auth.yml:ro
    restart: always

  vminsert:
    image: victoriametrics/vminsert:v1.140.0-cluster
    ports:
      - "8480:8480"
    command:
      - "--storageNode=vmstorage-1:8400"
      - "--storageNode=vmstorage-2:8400"
    restart: always

  vmselect:
    image: victoriametrics/vmselect:v1.140.0-cluster
    ports:
      - "8481:8481"
    command:
      - "--storageNode=vmstorage-1:8400"
      - "--storageNode=vmstorage-2:8400"
      - "--search.cacheTimestampOffset=5m"
    restart: always

  vmstorage-1:
    image: victoriametrics/vmstorage:v1.140.0-cluster
    volumes:
      - strgdata-1:/storage
    command:
      - "--storageDataPath=/storage"
      - "--retentionPeriod=30d"
    restart: always

  vmstorage-2:
    image: victoriametrics/vmstorage:v1.140.0-cluster
    volumes:
      - strgdata-2:/storage
    command:
      - "--storageDataPath=/storage"
      - "--retentionPeriod=30d"
    restart: always

volumes:
  strgdata-1:
  strgdata-2:
```

## Thanos: Prometheus-Native Long-Term Storage

Thanos (14,000+ stars, CNCF Incubating, last updated April 2026) was designed to extend existing Prometheus deployments without replacing them. Rather than building a new storage engine, Thanos adds components around Prometheus: a sidecar uploads blocks to object storage, a query layer aggregates results, and a compact handles downsampling.

### Architecture

Thanos is composed of several independent services:

- **Thanos Sidecar** — runs alongside each Prometheus instance, uploads TSDB blocks to object storage and exposes a gRPC Store API for real-time querying
- **Thanos Query** — aggregates PromQL results from multiple sidecars and store gateways, performs deduplication for HA Prometheus pairs
- **Thanos Store Gateway** — serves historical data from object storage blocks
- **Thanos Compactor** — handles downsampling, retention, and block deduplication
- **Thanos Ruler** — evaluates recording rules and alerting rules across the entire Thanos stack
- **Thanos Receiver** — accepts remote-write data from Prometheus, useful for multi-cluster setups

### Key Advantages

- **Works with existing Prometheus** — no migration required, just add sidecars
- **CNCF incubating** — strong community backing and enterprise adoption
- **HA deduplication** — built-in dedup for replicated Prometheus pairs using external labels
- **Global view** — query across multiple Prometheus instances and clusters through a single endpoint
- **Object storage native** — stores data as immutable TSDB blocks, compatible with any S3-compatible backend

### Docker Compose — Sidecar + Query Setup

```yaml
services:
  prometheus:
    image: prom/prometheus:v3.1.0
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--storage.tsdb.retention.time=2d"
      - "--web.enable-lifecycle"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    restart: always

  thanos-sidecar:
    image: quay.io/thanos/thanos:v0.37.2
    command:
      - "sidecar"
      - "--tsdb.path=/prometheus"
      - "--prometheus.url=http://prometheus:9090"
      - "--objstore.config-file=/config/bucket.yml"
      - "--grpc-address=0.0.0.0:10901"
      - "--http-address=0.0.0.0:10902"
    volumes:
      - ./bucket.yml:/config/bucket.yml:ro
    depends_on:
      - prometheus
      - minio
    restart: always

  thanos-query:
    image: quay.io/thanos/thanos:v0.37.2
    command:
      - "query"
      - "--grpc-address=0.0.0.0:10903"
      - "--http-address=0.0.0.0:10904"
      - "--store=thanos-sidecar:10901"
      - "--store=thanos-store-gateway:10901"
    ports:
      - "10904:10904"
    depends_on:
      - thanos-sidecar
    restart: always

  thanos-store-gateway:
    image: quay.io/thanos/thanos:v0.37.2
    command:
      - "store"
      - "--objstore.config-file=/config/bucket.yml"
      - "--grpc-address=0.0.0.0:10901"
      - "--http-address=0.0.0.0:10902"
    volumes:
      - ./bucket.yml:/config/bucket.yml:ro
    restart: always

  thanos-compact:
    image: quay.io/thanos/thanos:v0.37.2
    command:
      - "compact"
      - "--objstore.config-file=/config/bucket.yml"
      - "--http-address=0.0.0.0:10905"
      - "--wait"
    volumes:
      - ./bucket.yml:/config/bucket.yml:ro
    restart: always

  minio:
    image: minio/minio:latest
    command: "server /data --console-address :9001"
    environment:
      MINIO_ROOT_USER: thanos
      MINIO_ROOT_PASSWORD: thanos-secret
    volumes:
      - minio-data:/data
    ports:
      - "9000:9000"
      - "9001:9001"

volumes:
  minio-data:
```

## Cortex: Multi-Tenant Horizontally Scalable Metrics Platform

Cortex (5,700+ stars, last updated April 2026) was originally built by Weaveworks and Grafana Labs to provide a multi-tenant, horizontally scalable Prometheus. It uses a microservices architecture with a distributed hash table (ring) for data routing and replication. Unlike VictoriaMetrics and Thanos, multi-tenancy is a core design principle in Cortex, not an afterthought.

### Architecture

Cortex can run in two modes:

- **Single binary** — all Cortex services in one process, suitable for testing and small deployments
- **Microservices mode** — individual components scaled independently:
  - **Distributor** — receives and validates incoming writes, routes to ingesters via the ring
  - **Ingester** — stores metrics in-memory and flushes blocks to object storage
  - **Querier** — queries both in-memory ingesters and object storage
  - **Query Frontend** — splits large queries, caches results, provides tenant-aware rate limiting
  - **Ruler** — evaluates recording and alerting rules per tenant
  - **Compactor** — handles block compaction and retention per tenant
  - **Alertmanager** — per-tenant alert routing

### Key Advantages

- **True multi-tenancy** — isolate data and queries per tenant with a single deployment
- **Horizontally scalable** — add ingesters and distributors as write volume grows
- **Ring-based replication** — data replicated across multiple ingesters for fault tolerance
- **Prometheus-derived** — inherits years of Prometheus battle-testing and code maturity
- **Strong query federation** — split queries across time ranges and parallelize execution

### Docker Compose — Single Binary Setup

The Cortex project provides a getting-started compose with Cortex, Grafana, Prometheus, and object storage:

```yaml
services:
  cortex:
    image: quay.io/cortexproject/cortex:v1.19.0
    command:
      - "-config.file=/config/cortex-config.yaml"
    volumes:
      - ./cortex-config.yaml:/config/cortex-config.yaml:ro
    ports:
      - "9009:9009"
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://127.0.0.1:9009/ready"]
      interval: 10s
      timeout: 10s
      retries: 3
    restart: on-failure

  grafana:
    image: grafana/grafana:12.2.0
    environment:
      - GF_AUTH_ANONYMOUS_ENABLED=true
      - GF_AUTH_ANONYMOUS_ORG_ROLE=Admin
    volumes:
      - ./grafana-datasource.yaml:/etc/grafana/provisioning/datasources/ds.yaml:ro
    ports:
      - "3000:3000"
    restart: always

  prometheus:
    image: prom/prometheus:v3.1.0
    command:
      - "--config.file=/config/prometheus-config.yaml"
      - "--enable-feature=remote-write-receiver"
    volumes:
      - ./prometheus-config.yaml:/config/prometheus-config.yaml:ro
    ports:
      - "9090:9090"
    restart: always

  minio:
    image: minio/minio:latest
    command: "server /data --console-address :9001"
    environment:
      MINIO_ROOT_USER: cortex
      MINIO_ROOT_PASSWORD: cortex-secret
    volumes:
      - minio-data:/data
    ports:
      - "9000:9000"
    restart: always

volumes:
  minio-data:
```

### Cortex Configuration Example

A minimal `cortex-config.yaml` for single-binary mode with local filesystem storage:

```yaml
auth_enabled: false

server:
  http_listen_port: 9009

common:
  path_prefix: /data
  storage:
    filesystem:
      chunks_directory: /data/chunks
      rules_directory: /data/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: "2020-10-24"
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h

ruler:
  alertmanager_url: http://localhost:9009
```

## Performance and Resource Comparison

In independent benchmarks, VictoriaMetrics consistently uses the least disk space and memory for the same ingestion rate. Its custom LSM-tree format compresses time-series data more efficiently than the Prometheus TSDB blocks used by Thanos and Cortex.

| Metric | VictoriaMetrics | Thanos | Cortex |
|---|---|---|---|
| **Disk usage (per 1M samples)** | ~5-15 MB | ~15-30 MB | ~15-30 MB |
| **Memory (single-node, moderate load)** | 200-500 MB | 500-1000 MB | 500-1500 MB |
| **Query latency (p99, 1B samples)** | < 100ms | 100-500ms | 200-800ms |
| **Ingestion throughput (per node)** | 1-5M samples/sec | 500K-2M samples/sec | 500K-2M samples/sec |

These numbers vary based on hardware, cardinality, and query patterns, but the relative ordering is consistent: VictoriaMetrics is optimized for raw performance, while Thanos and Cortex trade some efficiency for architectural flexibility and multi-tenancy.

## Migration Paths

If you are already running Prometheus and want to add long-term storage, the path of least resistance is **Thanos**. Adding a sidecar requires zero changes to your existing Prometheus configuration. For setting up the collection layer, our [guide to self-hosted metrics collectors](../self-hosted-metrics-collectors-telegraf-statsd-vector-collectd-guide/) covers Telegraf, StatsD, and Vector as alternatives to Prometheus scraping.

If you are evaluating from scratch or want to replace Prometheus entirely, **VictoriaMetrics** offers the simplest deployment model. Its single binary accepts remote-write data and can even scrape targets directly via `vmagent`, potentially eliminating Prometheus altogether.

If you are running a multi-tenant environment (SaaS platform, shared infrastructure for multiple teams), **Cortex** is purpose-built for this use case. Its tenant isolation, per-tenant rate limits, and per-tenant alerting rules are unmatched by the other two. For the alerting layer, see our [Alertmanager vs Moira vs vmalert comparison](../prometheus-alertmanager-vs-moira-vs-victoriametrics-vmalert-self-hosted-alerting-2026/) which covers the notification side of the monitoring stack.

## Decision Framework

Choose **VictoriaMetrics** if:
- You want the best performance with the least operational complexity
- You are comfortable with a single-vendor solution (the VictoriaMetrics ecosystem)
- You need automatic downsampling and long retention without manual compaction setup
- Resource efficiency is a priority

Choose **Thanos** if:
- You want to extend existing Prometheus deployments without replacing them
- You value CNCF governance and a large, diverse contributor base
- You need a global query view across multiple independent Prometheus instances
- You prefer the flexibility of choosing your own compaction and retention policies

Choose **Cortex** if:
- You need true multi-tenant isolation in a single deployment
- You are building a metrics-as-a-service platform
- You want horizontal scalability with ring-based data distribution
- You need per-tenant configuration and rate limiting

## FAQ

### Can VictoriaMetrics query Thanos or Cortex data?

VictoriaMetrics can read Prometheus remote-read protocol, so it can query data from Thanos Querier (which exposes a Prometheus-compatible API). It cannot natively read Cortex's internal storage format. For Thanos, point `vmselect` at the Thanos Query HTTP endpoint using VictoriaMetrics' external datasource feature.

### Does Thanos support multi-tenancy?

Thanos does not have native multi-tenancy. All data in Thanos is visible through a single query endpoint. Some organizations achieve isolation by running separate Thanos stacks per tenant, but this increases operational overhead. If multi-tenancy is a hard requirement, Cortex is the better choice.

### How do these projects handle data retention?

VictoriaMetrics uses a `--retentionPeriod` flag (e.g., `30d`, `12m`) applied at the storage component level. Thanos handles retention through the Compactor component with a `--retention.resolution-raw` flag. Cortex configures retention per-tenant via the `limits.yaml` configuration file with `retention_period`.

### Can I run Thanos and VictoriaMetrics together?

Yes. A common pattern is to use Thanos for the global query layer (aggregating data from multiple Prometheus instances) while using VictoriaMetrics as a high-performance long-term storage backend. VictoriaMetrics can serve as a Thanos Store Gateway by exposing its storage via the gRPC Store API.

### Which project has the most active development?

All three projects are actively maintained as of April 2026. VictoriaMetrics has the highest star count (16,800+) and frequent releases. Thanos is a CNCF Incubating project with strong enterprise backing. Cortex has a smaller but dedicated community, with major contributions from Grafana Labs and Red Hat.

### Do these projects support remote write from Prometheus?

Yes, all three accept Prometheus remote-write protocol. VictoriaMetrics accepts it directly on its HTTP endpoint (`/api/v1/write`). Thanos Receiver accepts remote-write and stores data alongside sidecar-uploaded blocks. Cortex ingests remote-write data through its Distributor component, which routes to ingesters via the ring.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "VictoriaMetrics vs Thanos vs Cortex: Best Self-Hosted Metrics Storage 2026",
  "description": "Compare VictoriaMetrics, Thanos, and Cortex — the top three self-hosted distributed metrics storage backends for Prometheus. Includes Docker Compose configs, architecture comparisons, and deployment guides.",
  "datePublished": "2026-04-19",
  "dateModified": "2026-04-19",
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
