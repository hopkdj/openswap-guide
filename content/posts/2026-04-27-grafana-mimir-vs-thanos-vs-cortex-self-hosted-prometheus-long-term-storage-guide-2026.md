---
title: "Grafana Mimir vs Thanos vs Cortex: Best Prometheus Long-Term Storage 2026"
date: 2026-04-27
tags: ["comparison", "guide", "self-hosted", "monitoring", "prometheus", "metrics"]
draft: false
description: "Compare Grafana Mimir, Thanos, and Cortex for self-hosted Prometheus long-term storage. Learn architecture, deployment with Docker Compose, and which solution fits your scale."
---

Prometheus is the de facto standard for metrics collection, but it was never designed for long-term storage. Its local TSDB keeps data for a limited window before old samples are discarded. For teams that need months or years of historical metrics, three open-source solutions dominate the landscape: **Grafana Mimir**, **Thanos**, and **Cortex**.

Each project takes a different architectural approach to the same problem. Cortex pioneered the multi-tenant, horizontally scalable model. Thanos added sidecar-based long-term storage with a global query layer on top of existing Prometheus instances. Mimir, forked from Cortex by Grafana Labs in 2022, has since become the fastest-growing option with production-hardened defaults and tight Grafana integration.

This guide compares all three solutions side by side, with real Docker Compose configurations pulled from their official repositories, so you can deploy and evaluate each one yourself.

## Why Self-Host Prometheus Long-Term Storage

Running Prometheus without long-term storage means you lose data whenever the retention window expires. Self-hosting a long-term storage backend solves several problems:

- **Historical analysis** — Compare current metrics against last quarter or last year without data gaps
- **Compliance and auditing** — Retain infrastructure metrics for months or years to meet regulatory requirements
- **Capacity planning** — Trend analysis requires data spans that exceed Prometheus's default 15-day retention
- **Cost control** — Avoid the per-GB fees of managed monitoring platforms by storing metrics on your own S3-compatible storage
- **Full data ownership** — Keep metric data in your own infrastructure, not a third-party SaaS tenant

All three solutions store compressed metric blocks in object storage (S3, GCS, MinIO) and provide query interfaces that transparently fetch both recent data from local Prometheus and historical data from the remote store.

## Quick Comparison Table

| Feature | Grafana Mimir | Thanos | Cortex |
|---|---|---|---|
| **GitHub Stars** | 5,062 | 14,039 | 5,791 |
| **Last Updated** | Apr 27, 2026 | Apr 23, 2026 | Apr 27, 2026 |
| **Language** | Go | Go | Go |
| **Origin** | Cortex fork (Grafana Labs) | CNCF Incubating | Weaveworks / Grafana |
| **Multi-tenancy** | Yes (native) | No (single tenant) | Yes (native) |
| **Query API** | PromQL-compatible | PromQL-compatible | PromQL-compatible |
| **Deployment Modes** | Monolithic, Microservices | Sidecar, Receive, Store Gateway | Single binary, Microservices |
| **Object Storage** | S3, GCS, Azure, Swift, FileSystem | S3, GCS, Azure, Swift, COS | S3, GCS, Azure, Swift |
| **Compaction** | Built-in compactor | Built-in compactor | Built-in compactor |
| **Ruler (Alerting)** | Yes | Yes (separate component) | Yes |
| **Grafana Integration** | Native data source | Via Thanos query endpoint | Via Prometheus-compatible endpoint |
| **Helm Chart** | Official (grafana/mimir-distributed) | Official (thanos/thanos) | Community maintained |
| **Learning Curve** | Medium | Low (sidecar model) | High |

## Grafana Mimir: The Modern Cortex Successor

Grafana Mimir was created in May 2022 when Grafana Labs forked Cortex and rebuilt it with production-ready defaults, simplified operations, and tighter integration with the Grafana ecosystem. The name "Mimir" comes from Norse mythology — the wise being who guards the well of knowledge.

### Architecture

Mimir supports two deployment modes:

1. **Monolithic mode** — Single binary that runs all Mimir components (distributor, ingester, querier, compactor, ruler) in one process. Ideal for small to medium deployments where operational simplicity matters more than horizontal scaling.

2. **Microservices mode** — Each component runs as an independent process, allowing you to scale distributors, ingesters, and query-frontend instances independently. Designed for multi-tenant SaaS platforms and large enterprises.

Both modes share the same data path: metrics flow through the distributor to the ingester, which writes compressed TSDB blocks to object storage. The compactor merges and downsamples blocks for efficient querying. Queriers fetch data from both the ingester (in-memory) and object storage (historical) to provide a unified PromQL API.

### Key Advantages

- **Active development** — Grafana Labs employs a dedicated team of full-time engineers working on Mimir. The project receives weekly releases with new features and bug fixes.
- **Grafana native** — Grafana includes a built-in Mimir data source with optimized query routing, instant query federation, and tenant-aware dashboards.
- **Tenant isolation** — Each tenant gets its own series limit, ingestion rate limit, and storage quota, making Mimir suitable for multi-tenant monitoring-as-a-service platforms.
- **Built-in alerting** — The ruler component evaluates Prometheus recording and alerting rules directly against stored data, without needing a separate Prometheus server.

### Docker Compose — Monolithic Mode

This configuration is pulled directly from Mimir's official `development/mimir-monolithic-mode/docker-compose.yml` repository. It runs Mimir in single-binary mode with Consul for service discovery and MinIO for object storage:

```yaml
services:
  consul:
    image: consul:1.15
    command: ["agent", "-dev", "-client=0.0.0.0", "-log-level=info"]
    ports:
      - "8510:8500"

  minio:
    image: minio/minio:RELEASE.2025-05-24T17-08-30Z
    command: ["server", "--console-address", ":9101", "/data"]
    environment:
      - MINIO_ROOT_USER=mimir
      - MINIO_ROOT_PASSWORD=supersecret
    ports:
      - "9100:9000"
      - "9101:9101"
    volumes:
      - .data-minio:/data

  mimir:
    image: grafana/mimir:latest
    command: [
      "-config.file=/etc/mimir/mimir.yaml",
      "-target=all",
      "-server.http-listen-port=8080"
    ]
    ports:
      - "8080:8080"
    depends_on:
      - consul
      - minio
    volumes:
      - ./config:/etc/mimir
      - .data-mimir:/data

  prometheus:
    image: prom/prometheus:v3.11.2
    command: ["--config.file=/etc/prometheus/prometheus.yaml"]
    volumes:
      - ./config:/etc/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:12.4.3
    environment:
      - GF_AUTH_ANONYMOUS_ENABLED=true
      - GF_AUTH_ANONYMOUS_ORG_ROLE=Admin
    ports:
      - "3000:3000"
    volumes:
      - ./config/datasource-mimir.yaml:/etc/grafana/provisioning/datasources/mimir.yaml
```

The Mimir configuration file (`config/mimir.yaml`) for monolithic mode:

```yaml
multitenancy_enabled: false

blocks_storage:
  backend: s3
  s3:
    endpoint: minio:9000
    access_key_id: mimir
    secret_access_key: supersecret
    insecure: true
    bucket_name: mimir-tsdb
  tsdb:
    dir: /data/tsdb

compactor:
  data_dir: /data/compactor
  sharding_ring:
    kvstore:
      store: memberlist

distributor_ring:
  kvstore:
    store: memberlist

ingester_ring:
  kvstore:
    store: memberlist

ruler:
  enable_api: true
  enable_sharding: false
  storage:
    type: local
    local:
      directory: /data/rules
  rule_path: /data/rules-tmp

server:
  http_listen_port: 8080
  log_level: info

store_gateway:
  sharding_ring:
    kvstore:
      store: memberlist
```

### Docker Compose — Microservices Mode

For production deployments requiring horizontal scaling, Mimir's microservices mode runs each component independently:

```yaml
services:
  consul:
    image: consul:1.15
    command: ["agent", "-dev", "-client=0.0.0.0"]
    ports:
      - "8500:8500"

  minio:
    image: minio/minio
    command: ["server", "/data"]
    environment:
      - MINIO_ROOT_USER=mimir
      - MINIO_ROOT_PASSWORD=supersecret
    ports:
      - "9000:9000"
    volumes:
      - .data-minio:/data

  distributor:
    image: grafana/mimir:latest
    command: [
      "-config.file=/etc/mimir/mimir.yaml",
      "-target=distributor",
      "-server.http-listen-port=8080"
    ]
    ports:
      - "8080:8080"
    depends_on:
      - consul
      - minio
    volumes:
      - ./config:/etc/mimir

  ingester:
    image: grafana/mimir:latest
    command: [
      "-config.file=/etc/mimir/mimir.yaml",
      "-target=ingester",
      "-server.http-listen-port=8080"
    ]
    depends_on:
      - consul
      - minio
    volumes:
      - ./config:/etc/mimir

  querier:
    image: grafana/mimir:latest
    command: [
      "-config.file=/etc/mimir/mimir.yaml",
      "-target=querier",
      "-server.http-listen-port=8080"
    ]
    ports:
      - "8081:8080"
    depends_on:
      - consul
      - minio
    volumes:
      - ./config:/etc/mimir

  compactor:
    image: grafana/mimir:latest
    command: [
      "-config.file=/etc/mimir/mimir.yaml",
      "-target=compactor",
      "-server.http-listen-port=8080"
    ]
    depends_on:
      - consul
      - minio
    volumes:
      - ./config:/etc/mimir

  ruler:
    image: grafana/mimir:latest
    command: [
      "-config.file=/etc/mimir/mimir.yaml",
      "-target=ruler",
      "-server.http-listen-port=8080"
    ]
    depends_on:
      - consul
      - minio
    volumes:
      - ./config:/etc/mimir
```

## Thanos: The Sidecar Approach to Long-Term Storage

Thanos, a CNCF Incubating project, takes a fundamentally different approach. Instead of replacing Prometheus, it augments existing Prometheus instances with a **sidecar** container that uploads TSDB blocks to object storage and exposes them via a gRPC store API. A centralized **Thanos Query** component aggregates data from all sidecars, store gateways, and receive endpoints into a single PromQL-compatible view.

### Architecture

Thanos components work together as a modular toolkit:

- **Thanos Sidecar** — Runs alongside each Prometheus instance, uploading TSDB blocks to object storage and providing a real-time query interface for in-memory data.
- **Thanos Store Gateway** — Exposes historical blocks from object storage via the Thanos Store API.
- **Thanos Query** — Aggregates data from multiple sources (sidecars, store gateways, receive endpoints) with deduplication and fan-out.
- **Thanos Receive** — Accepts remote write from Prometheus, stores blocks locally, and uploads to object storage.
- **Thanos Compactor** — Applies retention policies, downsamples data, and deduplicates blocks.
- **Thanos Ruler** — Evaluates recording and alerting rules against the aggregated data.

### Key Advantages

- **No Prometheus changes** — Your existing Prometheus configuration stays intact. The sidecar is a separate container that doesn't modify how Prometheus collects or stores data.
- **Global view** — Thanos Query provides a unified PromQL endpoint across all Prometheus instances, regardless of geographic location or cluster boundary.
- **Deduplication** — When multiple Prometheus servers scrape the same targets, Thanos automatically deduplicates overlapping time series using external labels.
- **High availability** — Pair Prometheus HA with Thanos Query's `--query.replica-label` flag for automatic failover between replicas.
- **Largest community** — With over 14,000 GitHub stars, Thanos has the largest user community of the three projects.

### Docker Compose — Thanos Sidecar + Query Setup

Thanos does not ship an official Docker Compose file, but here is a production-ready setup based on the architecture documented in the official Thanos tutorials:

```yaml
services:
  prometheus:
    image: prom/prometheus:v3.11.2
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--storage.tsdb.retention.time=6h"
      - "--web.enable-lifecycle"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus

  thanos-sidecar:
    image: quay.io/thanos/thanos:v0.37.2
    command:
      - "sidecar"
      - "--tsdb.path=/prometheus"
      - "--prometheus.url=http://prometheus:9090"
      - "--objstore.config-file=/etc/thanos/objstore.yaml"
      - "--http-address=0.0.0.0:19191"
      - "--grpc-address=0.0.0.0:19090"
    volumes:
      - prometheus-data:/prometheus:ro
      - ./objstore.yaml:/etc/thanos/objstore.yaml
    depends_on:
      - prometheus
      - minio

  minio:
    image: minio/minio
    command: ["server", "/data", "--console-address", ":9001"]
    environment:
      - MINIO_ROOT_USER=thanos
      - MINIO_ROOT_PASSWORD=supersecret
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - .data-minio:/data

  thanos-store:
    image: quay.io/thanos/thanos:v0.37.2
    command:
      - "store"
      - "--objstore.config-file=/etc/thanos/objstore.yaml"
      - "--http-address=0.0.0.0:19191"
      - "--grpc-address=0.0.0.0:19090"
      - "--data-dir=/data"
    volumes:
      - ./objstore.yaml:/etc/thanos/objstore.yaml
      - .data-store:/data
    depends_on:
      - minio

  thanos-query:
    image: quay.io/thanos/thanos:v0.37.2
    command:
      - "query"
      - "--http-address=0.0.0.0:19192"
      - "--store=thanos-sidecar:19090"
      - "--store=thanos-store:19090"
    ports:
      - "19192:19192"
    depends_on:
      - thanos-sidecar
      - thanos-store

  thanos-compactor:
    image: quay.io/thanos/thanos:v0.37.2
    command:
      - "compact"
      - "--objstore.config-file=/etc/thanos/objstore.yaml"
      - "--data-dir=/data"
      - "--http-address=0.0.0.0:19191"
    volumes:
      - ./objstore.yaml:/etc/thanos/objstore.yaml
      - .data-compactor:/data
    depends_on:
      - minio

volumes:
  prometheus-data:
```

The `objstore.yaml` configuration for MinIO:

```yaml
type: s3
config:
  bucket: thanos
  endpoint: minio:9000
  access_key: thanos
  secret_key: supersecret
  insecure: true
```

## Cortex: The Original Scalable Prometheus

Cortex was created by Weaveworks in 2017 and later donated to the CNCF. It was the first project to provide a horizontally scalable, multi-tenant Prometheus-compatible storage layer. Grafana Mimir is a direct fork of Cortex, so the two projects share significant architectural DNA.

### Architecture

Cortex supports two deployment modes:

1. **Single binary** — All components run in one process, similar to Mimir's monolithic mode. Good for evaluation and small deployments.

2. **Microservices** — Each component (distributor, ingester, querier, compactor, ruler, query-frontend) runs as an independent service, scaled behind a load balancer. Uses Consul or a ring-based membership protocol for service discovery.

The data flow mirrors Mimir: Prometheus remote-writes to the distributor, which fans out to ingesters. Ingesters buffer metrics in memory and periodically flush compressed TSDB blocks to object storage. The compactor merges and downsamples blocks.

### Key Advantages

- **Proven at scale** — Cortex powers the monitoring infrastructure for companies like Grafana Cloud (before the Mimir fork) and numerous enterprises.
- **Mature multi-tenancy** — Per-tenant ingestion limits, series limits, and query timeouts prevent noisy-neighbor problems.
- **Flexible storage backends** — Supports S3, GCS, Azure Blob Storage, OpenStack Swift, and local filesystem.
- **CNCF project** — As a CNCF-hosted project, Cortex benefits from the foundation's governance, security audits, and community events.

### Docker Compose — Single Binary Setup

This configuration is based on Cortex's official `development/tsdb-blocks-storage-s3-single-binary/docker-compose.yml`:

```yaml
services:
  consul:
    image: consul:1.15.4
    command: ["agent", "-dev", "-client=0.0.0.0", "-log-level=info"]
    ports:
      - "8500:8500"

  minio:
    image: minio/minio
    command: ["server", "/data"]
    environment:
      - MINIO_ACCESS_KEY=cortex
      - MINIO_SECRET_KEY=supersecret
    ports:
      - "9000:9000"
    volumes:
      - .data-minio:/data

  prometheus:
    image: prom/prometheus:v2.54.1
    command:
      - "--config.file=/etc/prometheus/prometheus.yaml"
      - "--storage.tsdb.retention.time=6h"
    volumes:
      - ./config:/etc/prometheus
    ports:
      - "9090:9090"

  cortex-1:
    image: quay.io/cortexproject/cortex:v1.19.0
    command: [
      "-config.file=/etc/cortex/cortex.yaml",
      "-target=all",
      "-server.http-listen-port=8080"
    ]
    ports:
      - "8080:8080"
    depends_on:
      - consul
      - minio
    volumes:
      - ./config:/etc/cortex
      - .data-cortex-1:/data

  cortex-2:
    image: quay.io/cortexproject/cortex:v1.19.0
    command: [
      "-config.file=/etc/cortex/cortex.yaml",
      "-target=all",
      "-server.http-listen-port=8081"
    ]
    ports:
      - "8081:8081"
    depends_on:
      - consul
      - minio
    volumes:
      - ./config:/etc/cortex
      - .data-cortex-2:/data
```

The Cortex configuration file (`config/cortex.yaml`):

```yaml
auth_enabled: false

server:
  http_listen_port: 8080
  grpc_listen_port: 9095
  log_level: info

ingester:
  lifecycler:
    address: 127.0.0.1
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
    final_sleep: 0s
  chunk_idle_period: 1h
  chunk_retain_period: 30s

blocks_storage:
  backend: s3
  s3:
    endpoint: minio:9000
    access_key_id: cortex
    secret_access_key: supersecret
    insecure: true
    bucket_name: cortex-tsdb
  tsdb:
    dir: /data/tsdb

compactor:
  data_dir: /data/compactor
  shared_store: s3

schema_config_store:
  configs:
    - from: "2024-01-01"
      store: tsdb
      object_store: s3
      schema: v13
      index:
        prefix: cortex_
        period: 24h

storage_config:
  tsdb_shipper:
    active_index_gateway: true

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h
```

## Performance and Resource Comparison

| Metric | Mimir (Monolithic) | Thanos (Sidecar + Query) | Cortex (Single Binary) |
|---|---|---|---|
| **Memory (baseline)** | 512 MB – 2 GB | 256 MB (sidecar) + 1 GB (query) | 512 MB – 2 GB |
| **CPU (idle)** | 0.2 – 0.5 cores | 0.1 (sidecar) + 0.3 (query) | 0.2 – 0.5 cores |
| **Storage overhead** | TSDB blocks + compaction temp | TSDB blocks + compaction temp | TSDB blocks + compaction temp |
| **Max tenants** | Unlimited | N/A (single tenant) | Unlimited |
| **Max series** | Millions (tested at 10M+) | Limited by individual Prometheus | Millions |
| **Query latency** | Low (ingester cache) | Medium (remote fetch from store) | Low (ingester cache) |
| **Scaling granularity** | Per component (microservices) | Per Prometheus instance | Per component (microservices) |

## Migration Paths Between Solutions

If you are already running one of these solutions and want to switch, the good news is that all three use the same underlying TSDB block format. The migration path is straightforward:

1. **Cortex to Mimir** — Minimal changes required. Mimir's configuration is a superset of Cortex's. Most `cortex.yaml` files work as `mimir.yaml` with minor key adjustments. Point the new Mimir deployment to the same S3 bucket as Cortex.

2. **Thanos to Mimir** — Thanos uses the same TSDB block format as Cortex/Mimir. You can point Mimir's store gateway to the same Thanos S3 bucket and use Thanos Querier as a data source during the transition.

3. **Mimir to Thanos** — Run Thanos sidecars alongside your Prometheus instances pointing to the same S3 bucket. Mimir and Thanos can coexist reading from the same object storage.

4. **Prometheus only to any solution** — Add the Thanos sidecar or configure Prometheus remote-write to Mimir/Cortex. Both approaches work, but remote-write is simpler to set up initially.

## Decision Framework

Choose **Grafana Mimir** if:
- You use Grafana and want the most integrated experience
- You need multi-tenant metric storage (SaaS, managed services)
- You want the most actively developed project with Grafana Labs backing
- You need built-in alerting rules evaluation without separate Prometheus servers

Choose **Thanos** if:
- You want to keep your existing Prometheus instances unchanged
- You have geographically distributed Prometheus servers that need a global query view
- You prefer the sidecar model that doesn't replace Prometheus
- You want the largest community and most adoption

Choose **Cortex** if:
- You need CNCF governance and vendor-neutral project stewardship
- You already have Cortex running and are satisfied with it
- You want the original battle-tested multi-tenant architecture
- Your organization has an existing investment in the Cortex ecosystem

## FAQ

### Can Grafana Mimir and Thanos read from the same S3 bucket?

Yes. Both Mimir and Thanos use the same Prometheus TSDB block format for long-term storage. You can configure both to read from the same S3 bucket simultaneously, which makes migration and coexistence straightforward. The compactor in each project handles block deduplication independently.

### Do I need Consul or memberlist for single-node deployments?

For Mimir and Cortex single binary deployments, you can use the `inmemory` ring store instead of Consul. This removes the external dependency entirely. Memberlist (gossip protocol) is recommended for multi-node deployments but is not required for evaluation or small-scale setups. Thanos does not require any service discovery — the Query component connects directly to sidecar and store gRPC endpoints.

### What is the minimum Prometheus retention window when using long-term storage?

A 2-6 hour local retention window is typically recommended. This keeps recent metrics available in Prometheus's fast local TSDB while the sidecar or remote-write ships blocks to object storage. The long-term storage backend handles everything older than the local retention window.

### How does multi-tenancy work in Mimir and Cortex?

Both Mimir and Cortex support multi-tenancy via an `X-Scope-OrgID` HTTP header on the remote-write endpoint. Each tenant gets isolated data, separate series limits, and independent ingestion rate limits. Thanos does not support multi-tenancy — it is designed as a single-tenant global query layer.

### Can I use Thanos with existing HA Prometheus pairs?

Yes. Thanos Query supports automatic deduplication of HA Prometheus pairs using the `--query.replica-label` flag. When two Prometheus servers scrape the same targets with the same external labels but different replica labels, Thanos Query automatically picks one source per time series and discards duplicates.

### Which solution has the lowest operational complexity?

Thanos has the lowest initial complexity because it augments existing Prometheus instances without replacing them. You add a sidecar container and a query component, and your existing Prometheus setup continues to work. Mimir's monolithic mode is similarly simple for new deployments. Cortex and Mimir microservices mode require managing more independent components and service discovery.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Grafana Mimir vs Thanos vs Cortex: Best Prometheus Long-Term Storage 2026",
  "description": "Compare Grafana Mimir, Thanos, and Cortex for self-hosted Prometheus long-term storage. Learn architecture, deployment with Docker Compose, and which solution fits your scale.",
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

For related reading, see our [VictoriaMetrics vs Thanos vs Cortex comparison](../victoriametrics-vs-thanos-vs-cortex-self-hosted-metrics-storage-guide-2026/), [HertzBeat vs Prometheus vs NetData monitoring guide](../2026-04-25-hertzbeat-vs-prometheus-vs-netdata-self-hosted-monitoring-guide-2026/), and [Coroot vs SigNoz vs HyperDX observability guide](../2026-04-27-coroot-vs-signoz-vs-hyperdx-self-hosted-observability-guide-2026/).
