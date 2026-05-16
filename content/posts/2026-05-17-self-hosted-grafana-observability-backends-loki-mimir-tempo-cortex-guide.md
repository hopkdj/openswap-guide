---
title: "Self-Hosted Grafana Observability Backends: Loki vs Mimir vs Tempo vs Cortex (2026-05-17)"
date: "2026-05-17"
tags: ["observability", "monitoring", "grafana", "self-hosted", "devops", "logging"]
draft: false
---

Grafana's LGTM stack (Loki, Grafana, Tempo, Mimir) has become the de facto open-source observability platform, but understanding when to use each backend component — and how they relate to older projects like Cortex — is essential for building a production-grade monitoring system. This guide breaks down each tool's role, compares their architectures, and provides Docker Compose configurations for self-hosted deployment.

## The Observability Pillars

Modern observability rests on three pillars, each handled by a different Grafana Labs project:

| Pillar | Tool | Purpose | Data Type |
|---|---|---|---|
| **Logs** | Loki | Log aggregation and search | Unstructured/structured log lines |
| **Metrics** | Mimir / Cortex | Time-series metrics storage | Prometheus-compatible time series |
| **Traces** | Tempo | Distributed tracing | OpenTelemetry/Jaeger/Zipkin traces |

## Loki vs Mimir vs Tempo: Architecture Comparison

| Feature | Loki | Mimir | Tempo | Cortex |
|---|---|---|---|---|
| **Primary Data** | Logs | Metrics | Traces | Metrics |
| **Storage Backend** | Object storage (S3, GCS, filesystem) | Object storage + blocks | Object storage | Object storage + blocks |
| **Query Language** | LogQL | PromQL | TraceQL | PromQL |
| **Index Strategy** | Label-based (minimal index) | Time-series index | Trace ID index | Time-series index |
| **Scalability** | Horizontal (microservices mode) | Horizontal (microservices mode) | Horizontal (microservices mode) | Horizontal (microservices mode) |
| **Single-Binary Mode** | Yes | Yes | Yes | Yes |
| **Multi-Tenancy** | Yes (X-Scope-OrgID) | Yes (X-Scope-OrgID) | Yes (X-Scope-OrgID) | Yes (X-Scope-OrgID) |
| **Compression** | Snappy + chunk encoding | TSDB block compression | Parquet-like columnar | TSDB block compression |
| **Cost per GB** | Very low (no full-text index) | Low (block compression) | Low (columnar) | Low (block compression) |
| **Retention** | Configurable per tenant | Configurable per tenant | Configurable per tenant | Configurable per tenant |
| **Docker Image** | `grafana/loki` | `grafana/mimir` | `grafana/tempo` | `cortexproject/cortex` |
| **GitHub Stars** | 28,000+ | 5,000+ | 5,200+ | 5,800+ |
| **Relationship** | Grafana Labs project | Successor to Cortex (Grafana Labs) | Grafana Labs project | CNCF graduated (original Grafana metrics backend) |

## Loki: Log Aggregation Without the Index Tax

Loki is designed around the principle that you should not pay an indexing cost for log data you rarely query. Instead of indexing full log content, Loki indexes only labels (like Kubernetes pod name, namespace, or application name) and stores compressed log chunks in object storage.

### Key Design Decisions

- **Label-only indexing** — Only log labels are indexed. Log content is searched at query time using grep-like operations on compressed chunks.
- **Chunk-based storage** — Logs are grouped into time-ordered chunks (default: 1 hour), compressed with Snappy, and stored in object storage.
- **LogQL** — Query language inspired by PromQL with label selectors, filter expressions, and aggregation functions.
- **Promtail / Alloy** — Log shippers that collect, enrich with labels, and push to Loki.

### Docker Compose for Loki (Single-Binary)

```yaml
version: "3.8"

services:
  loki:
    image: grafana/loki:3.0.0
    ports:
      - "3100:3100"
    volumes:
      - ./loki-config.yaml:/etc/loki/local-config.yaml
      - loki-data:/loki
    command: -config.file=/etc/loki/local-config.yaml

volumes:
  loki-data:
```

**loki-config.yaml:**
```yaml
auth_enabled: false

server:
  http_listen_port: 3100

common:
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: 2024-01-01
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h

limits_config:
  retention_period: 744h  # 31 days
```

### Collecting Logs with Promtail

```yaml
# promtail-config.yaml
server:
  http_listen_port: 9080

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
```

## Mimir: Scalable Metrics Storage

Mimir is Grafana Labs' long-term storage backend for Prometheus metrics. It is the successor to Cortex, rebuilt with lessons learned from operating Cortex at scale. Mimir provides horizontal scalability, multi-tenancy, and efficient long-term retention of time-series data.

### Key Features

- **Prometheus-compatible API** — Drop-in replacement for Prometheus remote storage. Query with PromQL via Grafana.
- **Block-based storage** — Uses Prometheus TSDB blocks for efficient compression and fast queries.
- **Rule evaluation** — Native recording rules and alerting rules evaluated server-side.
- **Continuous compaction** — Blocks are compacted over time for storage efficiency.

### Docker Compose for Mimir

```yaml
version: "3.8"

services:
  mimir:
    image: grafana/mimir:2.13.0
    ports:
      - "9009:9009"
    volumes:
      - ./mimir-config.yaml:/etc/mimir/config.yaml
      - mimir-data:/mimir
    command: -config.file=/etc/mimir/config.yaml

volumes:
  mimir-data:
```

**mimir-config.yaml:**
```yaml
multitenancy_enabled: false

limits_defaults:
  compactor_blocks_retention_period: 31d

blocks_storage:
  backend: filesystem
  filesystem:
    dir: /mimir/blocks

compactor:
  data_dir: /mimir/compactor
  sharding_ring:
    kvstore:
      store: memberlist

ruler_storage:
  backend: filesystem
  filesystem:
    dir: /mimir/rules

server:
  http_listen_port: 9009

store_gateway:
  sharding_ring:
    kvstore:
      store: memberlist
```

### Configuring Prometheus to Remote-Write to Mimir

```yaml
# prometheus.yml
remote_write:
  - url: http://mimir:9009/api/v1/push
    queue_config:
      max_samples_per_send: 5000
      capacity: 10000
```

## Tempo: Distributed Tracing at Scale

Tempo is Grafana Labs' distributed tracing backend, designed to handle millions of traces per second with minimal infrastructure. It stores traces in object storage using a columnar format optimized for trace ID lookups.

### Key Features

- **TraceQL** — Query language for searching traces by span attributes, duration, and hierarchical relationships.
- **No index required** — Like Loki, Tempo avoids expensive indexing by using trace ID-based lookups and streaming search.
- **Multi-protocol ingestion** — Accepts Jaeger, Zipkin, OpenTelemetry, and Kafka protocols.
- **Trace-to-metrics** — Generate metrics from trace data (RED method: Rate, Errors, Duration).

### Docker Compose for Tempo

```yaml
version: "3.8"

services:
  tempo:
    image: grafana/tempo:2.4.2
    ports:
      - "3200:3200"   # Tempo API
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP
      - "9411:9411"   # Zipkin
    volumes:
      - ./tempo-config.yaml:/etc/tempo/config.yaml
      - tempo-data:/tmp/tempo
    command: -config.file=/etc/tempo/config.yaml

volumes:
  tempo-data:
```

**tempo-config.yaml:**
```yaml
stream_over_http_enabled: true

server:
  http_listen_port: 3200

distributor:
  receivers:
    otlp:
      protocols:
        grpc:
        http:
    zipkin:

storage:
  trace:
    backend: local
    local:
      path: /tmp/tempo/blocks

compactor:
  compaction:
    block_retention: 48h
```

## Cortex: The Original Metrics Backend

Cortex was the first horizontally scalable, multi-tenant Prometheus storage system. Now a CNCF graduated project, it remains a viable option for organizations that prefer a vendor-neutral, community-governed metrics backend.

### Cortex vs Mimir

| Aspect | Cortex | Mimir |
|---|---|---|
| **Governance** | CNCF graduated | Grafana Labs |
| **Active development** | Community-driven | Grafana Labs-driven |
| **Feature velocity** | Slower, stable | Faster, frequent releases |
| **Query federation** | Basic | Advanced (query splitting, caching) |
| **Alertmanager** | Built-in | Built-in |
| **Continuous compaction** | Yes | Yes (improved algorithm) |
| **Object storage** | S3, GCS, Azure, filesystem | S3, GCS, Azure, filesystem |

For most new deployments, Mimir is the recommended choice unless CNCF graduation is a hard requirement.

### Docker Compose for Cortex

```yaml
version: "3.8"

services:
  cortex:
    image: cortexproject/cortex:v1.18.1
    ports:
      - "9009:9009"
    volumes:
      - ./cortex-config.yaml:/etc/cortex/cortex.yaml
      - cortex-data:/cortex
    command: -config.file=/etc/cortex/cortex.yaml

volumes:
  cortex-data:
```

## Why Self-Host Your Observability Backend?

Cloud observability platforms charge by data volume — logs ingested, metrics stored, traces analyzed. For teams generating terabytes of telemetry data, these costs can exceed infrastructure spend. Self-hosting the LGTM stack on commodity hardware with object storage (MinIO, Ceph, or S3-compatible) typically costs 80-90% less than equivalent managed services.

Self-hosted observability also keeps sensitive log data and trace information within your network perimeter. This matters for healthcare, finance, and government workloads where telemetry data may contain PII or classified information. For related reading, see our [log forwarding comparison](../2026-05-01-self-hosted-log-forwarding-fluent-bit-vector-otel/) and [distributed tracing backends guide](../2026-05-12-self-hosted-distributed-tracing-backends-grafana-tempo-jaeger-zipkin/). If you need alerting on top of these backends, our [alert routing comparison](../2026-05-12-self-hosted-alert-routing-prometheus-alertmanager-ntfy-gotify/) covers the notification layer.

## FAQ

### Should I use Mimir or Cortex for metrics storage?
For new deployments, use Mimir. It is actively developed by Grafana Labs with faster feature releases, improved query performance, and better integration with the rest of the LGTM stack. Cortex remains a solid choice if you need a CNCF-graduated project with vendor-neutral governance. Both use the same TSDB block storage format, so migration is possible.

### Can Loki handle high-volume log ingestion?
Yes. Loki's microservices mode scales horizontally across distributors, ingesters, queriers, and compactor components. Production deployments at companies like Grafana Labs ingest millions of log lines per second. The key bottleneck is usually label cardinality — keep labels selective (pod name, namespace, app) and avoid high-cardinality labels like user ID or request ID.

### Does Tempo require a separate search index like Elasticsearch?
No. Tempo is designed to work without a full-text search index. Traces are looked up by trace ID (direct object storage fetch) or searched using TraceQL (streaming scan of blocks). This makes Tempo significantly cheaper to operate than Elasticsearch-based tracing backends, which require expensive index infrastructure.

### How do the three tools integrate with Grafana?
All three expose Prometheus-compatible APIs that Grafana natively understands. Configure Loki as a log data source, Mimir/Cortex as a metrics data source (Prometheus-compatible), and Tempo as a tracing data source (Jaeger-compatible). Grafana provides unified dashboards that correlate logs, metrics, and traces from all three backends.

### What is the minimum hardware for running the full LGTM stack?
For a small homelab or development environment, each component can run in single-binary mode with 2 GB RAM and 1 CPU core. For production, plan for 4+ GB RAM per component and SSD storage. The storage requirement depends on retention period and data volume — Loki and Tempo benefit from large object storage backends, while Mimir/Cortex need fast local storage for the write path.

### How does Loki differ from Elasticsearch for log management?
Loki indexes only labels, not log content. This means ingestion is cheaper (no full-text index to build) and storage is smaller (compressed chunks vs. inverted index). The tradeoff is that log content searches are slower — Loki scans compressed chunks at query time rather than consulting a pre-built index. For teams that filter logs by label first (e.g., "show me logs from pod X where level=error"), Loki is dramatically more cost-efficient.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Grafana Observability Backends: Loki vs Mimir vs Tempo vs Cortex",
  "description": "Compare Loki, Mimir, Tempo, and Cortex for self-hosted observability. Docker compose configs for logs, metrics, and distributed tracing backends.",
  "datePublished": "2026-05-17",
  "dateModified": "2026-05-17",
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
