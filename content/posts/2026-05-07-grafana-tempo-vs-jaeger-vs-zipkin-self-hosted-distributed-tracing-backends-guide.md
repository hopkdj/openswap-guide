---
title: "Grafana Tempo vs Jaeger vs Zipkin: Best Self-Hosted Distributed Tracing Backends 2026"
date: "2026-05-07"
tags: ["comparison", "guide", "self-hosted", "observability", "devops", "monitoring"]
draft: false
description: "Compare Grafana Tempo, Jaeger, and Zipkin — the three leading open-source distributed tracing backends. Learn which self-hosted tracing platform fits your scale, budget, and infrastructure needs."
---

Distributed tracing has become essential for understanding how requests flow through modern microservice architectures. When a single user action triggers calls across dozens of services, databases, and message queues, traditional monitoring tools cannot tell you where latency originates or why requests fail. Tracing fills that gap by connecting the dots across service boundaries with unique trace IDs.

The three dominant open-source tracing backends are Grafana Tempo, Jaeger, and Zipkin. Each takes a different architectural approach to storing and querying trace data, with distinct tradeoffs in cost, scalability, and operational complexity. This guide compares them head-to-head and provides Docker-based deployment configurations so you can run any of them in your own infrastructure.

## What Is a Distributed Tracing Backend?

A distributed tracing backend receives, stores, and serves trace data collected by instrumented applications. The standard data model comes from OpenTelemetry, which defines spans (individual operations) organized into traces (end-to-end requests). The backend's job is to ingest spans at high throughput, store them efficiently, and enable fast queries for analysis.

The key differences between tracing backends come down to storage architecture, query capabilities, resource requirements, and ecosystem integrations. A good tracing backend should handle millions of spans per day, support trace-level and span-level queries, integrate with your existing observability stack, and remain affordable as your data volume grows.

## Comparison Table

| Feature | Grafana Tempo | Jaeger | Zipkin |
|---------|--------------|--------|--------|
| **Maintainer** | Grafana Labs | CNCF (Apache 2.0) | CNCF (Apache 2.0) |
| **GitHub Stars** | 5,200+ | 22,700+ | 17,400+ |
| **Primary Storage** | Object storage (S3, GCS) | Elasticsearch, Cassandra, Badger | Elasticsearch, Cassandra, MySQL |
| **Query Language** | TraceQL (built-in) | Jaeger Query UI | Zipkin Query UI |
| **Sampling** | Head-based, tail-based via OTel | Probabilistic, rate-limited, adaptive | Probabilistic, rate-limited |
| **Metrics Integration** | Native Grafana | Via Prometheus metrics | Via Prometheus exporters |
| **Log Integration** | Grafana Loki (native) | Via external tools | Via external tools |
| **Resource Footprint** | Low (no index required) | High (Elasticsearch cluster) | Medium (Elasticsearch or MySQL) |
| **Multi-tenant** | Yes | Limited | No |
| **Long-term Retention** | Excellent (object storage) | Good (depends on ES cluster) | Good (depends on ES cluster) |
| **Docker Image** | `grafana/tempo` | `jaegertracing/all-in-one` | `openzipkin/zipkin` |
| **Best For** | High-volume, cost-sensitive | Full-featured, mature ecosystem | Simple, lightweight deployments |

## Grafana Tempo

Tempo is the newest of the three, launched by Grafana Labs in 2020. Its defining architectural choice is storing traces directly in object storage (S3, GCS, Azure Blob) without a searchable index. Instead of indexing every span attribute, Tempo uses TraceQL to query traces at read time.

### Key Features

- **No-index architecture**: Writes traces directly to object storage, eliminating the expensive Elasticsearch cluster that Jaeger requires. This reduces operational costs by 70-90% compared to index-based backends.
- **TraceQL**: A purpose-built query language for searching traces without indexes. Supports filtering by span attributes, duration, service names, and hierarchical relationships.
- **Native Grafana integration**: Tempo datasources in Grafana enable unified dashboards combining traces, metrics, and logs.
- **Tail-based sampling**: Works with the OpenTelemetry Collector's tail sampling processor to keep only traces that meet specific criteria (errors, slow requests, specific services).
- **Multi-tenancy**: Built-in tenant isolation for multi-team or multi-customer environments.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  tempo:
    image: grafana/tempo:latest
    command: ["-config.file=/etc/tempo.yaml"]
    volumes:
      - ./tempo-config.yaml:/etc/tempo.yaml
      - tempo-data:/tmp/tempo
    ports:
      - "14268:14268"   # Jaeger ingest
      - "4317:4317"     # OTLP gRPC
      - "4318:4318"     # OTLP HTTP
      - "3200:3200"     # Tempo HTTP API
    networks:
      - tracing

  grafana:
    image: grafana/grafana:latest
    volumes:
      - ./grafana-datasources.yaml:/etc/grafana/provisioning/datasources/datasources.yaml
      - grafana-data:/var/lib/grafana
    ports:
      - "3000:3000"
    networks:
      - tracing

volumes:
  tempo-data:
  grafana-data:

networks:
  tracing:
    driver: bridge
```

```yaml
# tempo-config.yaml
server:
  http_listen_port: 3200

distributor:
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: "0.0.0.0:4317"
        http:
          endpoint: "0.0.0.0:4318"
    jaeger:
      thrift_http:
        endpoint: "0.0.0.0:14268"

storage:
  trace:
    backend: local
    wal:
      path: /tmp/tempo/wal
    local:
      path: /tmp/tempo/blocks

metrics_generator:
  registry:
    external_labels:
      source: tempo
  storage:
    path: /tmp/tempo/wal
  traces_storage:
    path: /tmp/tempo/generator
```

### When to Choose Tempo

Tempo is the best choice when you need cost-effective trace storage at scale. The no-index architecture means your storage cost scales linearly with trace volume, not with the number of indexed attributes. If you already use Grafana for metrics and Loki for logs, Tempo completes the observability triad with minimal integration work.

## Jaeger

Jaeger is the most mature tracing backend, originally developed by Uber and donated to the CNCF in 2017. It achieved graduated status in 2019 and remains the most widely deployed open-source tracing system.

### Key Features

- **Mature ecosystem**: Extensive documentation, community support, and integrations with virtually every programming language and framework.
- **Flexible storage backends**: Supports Elasticsearch, OpenSearch, Cassandra, and Badger (embedded) for different scale requirements.
- **Adaptive sampling**: Automatically adjusts sampling rates based on traffic patterns to maintain representative trace coverage.
- **Rich query UI**: The Jaeger Query interface provides trace search, service dependency graphs, and latency distribution analysis.
- **CNCF graduation**: Production-grade stability with regular security audits and a large contributor community.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    environment:
      - COLLECTOR_OTLP_ENABLED=true
      - COLLECTOR_OTLP_GRPC_HOST_PORT=0.0.0.0:4317
      - COLLECTOR_OTLP_HTTP_HOST_PORT=0.0.0.0:4318
      - SPAN_STORAGE_TYPE=badger
      - BADGER_EPHEMERAL=false
      - BADGER_DIRECTORY_VALUE=/badger/data
      - BADGER_DIRECTORY_KEY=/badger/key
    volumes:
      - jaeger-data:/badger
    ports:
      - "16686:16686"   # Jaeger UI
      - "4317:4317"     # OTLP gRPC
      - "4318:4318"     # OTLP HTTP
      - "14250:14250"   # gRPC collector
    networks:
      - tracing

volumes:
  jaeger-data:

networks:
  tracing:
    driver: bridge
```

For production deployments, Jaeger requires a separate storage backend. The Elasticsearch-based architecture provides full-text search across all span fields:

```yaml
version: "3.8"
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - es-data:/usr/share/elasticsearch/data
    networks:
      - tracing

  jaeger-collector:
    image: jaegertracing/jaeger-collector:latest
    environment:
      - SPAN_STORAGE_TYPE=elasticsearch
      - ES_SERVER_URLS=http://elasticsearch:9200
      - COLLECTOR_OTLP_ENABLED=true
    ports:
      - "14268:14268"
      - "4317:4317"
    networks:
      - tracing

  jaeger-query:
    image: jaegertracing/jaeger-query:latest
    environment:
      - SPAN_STORAGE_TYPE=elasticsearch
      - ES_SERVER_URLS=http://elasticsearch:9200
    ports:
      - "16686:16686"
    networks:
      - tracing

volumes:
  es-data:

networks:
  tracing:
    driver: bridge
```

### When to Choose Jaeger

Jaeger is the right choice when you need a battle-tested tracing platform with maximum flexibility. The mature storage plugins, adaptive sampling, and extensive community make it suitable for organizations that want a proven solution with long-term support.

## Zipkin

Zipkin is the original open-source distributed tracing system, created by Twitter and now maintained as a CNCF project. It pioneered the trace/span data model that Jaeger and Tempo adopted.

### Key Features

- **Simplicity**: Zipkin has the simplest deployment model. A single Docker container handles ingestion, storage, and query.
- **Multiple storage options**: Supports Elasticsearch, Cassandra, MySQL, and in-memory storage for development.
- **Language support**: Official libraries for Java, Go, Ruby, JavaScript, and more.
- **Lightweight footprint**: Requires significantly fewer resources than Jaeger with Elasticsearch.
- **CNCF incubation**: Active maintenance with regular releases.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  zipkin:
    image: openzipkin/zipkin:latest
    environment:
      - STORAGE_TYPE=mem
    ports:
      - "9411:9411"
    networks:
      - tracing

networks:
  tracing:
    driver: bridge
```

For production with persistent storage using MySQL:

```yaml
version: "3.8"
services:
  zipkin-mysql:
    image: openzipkin/zipkin-mysql:latest
    environment:
      - MYSQL_ROOT_PASSWORD=***
    volumes:
      - mysql-data:/var/lib/mysql
    networks:
      - tracing

  zipkin:
    image: openzipkin/zipkin:latest
    environment:
      - STORAGE_TYPE=mysql
      - MYSQL_HOST=zipkin-mysql
      - MYSQL_USER=root
      - MYSQL_PASS=zipkin
    ports:
      - "9411:9411"
    depends_on:
      - zipkin-mysql
    networks:
      - tracing

volumes:
  mysql-data:

networks:
  tracing:
    driver: bridge
```

### When to Choose Zipkin

Zipkin excels when you need a simple, lightweight tracing backend for small to medium deployments. The single-process architecture is easy to operate, and the MySQL storage option avoids the complexity of running an Elasticsearch cluster.

## Performance and Scalability Comparison

| Metric | Tempo | Jaeger (ES) | Zipkin (ES) | Zipkin (MySQL) |
|--------|-------|-------------|-------------|-----------------|
| **Ingest throughput** | 100K+ spans/s | 50K+ spans/s | 30K+ spans/s | 10K+ spans/s |
| **Query latency (P95)** | 200-500ms | 100-300ms | 150-400ms | 500-2000ms |
| **Storage cost (1B spans)** | ~50 GB | ~200 GB | ~180 GB | ~250 GB |
| **Min. RAM** | 512 MB | 4 GB (ES) + 1 GB (Jaeger) | 2 GB (ES) + 512 MB (Zipkin) | 1 GB (MySQL) + 512 MB (Zipkin) |
| **Horizontal scale** | Excellent (stateless) | Good (ES cluster) | Good (ES cluster) | Limited (MySQL master) |

## Architecture Deep Dive

### Tempo: Write-Optimized Object Storage

Tempo writes spans directly to compressed blocks in object storage. When a query arrives, Tempo scans the relevant blocks and applies TraceQL filters at read time. This approach eliminates the indexing overhead that dominates Jaeger and Zipkin storage costs. The tradeoff is that complex attribute queries can be slower since they require block scanning rather than index lookups.

### Jaeger: Index-Based Search

Jaeger indexes every span field in Elasticsearch, enabling fast arbitrary queries. This provides a richer search experience but requires significant Elasticsearch resources. The index grows proportionally with the number of unique attribute values, which can become expensive at scale.

### Zipkin: Simple and Direct

Zipkin uses a straightforward data model with minimal indexing. It is designed for teams that need basic trace search and dependency analysis without the complexity of full-text indexing.

## Why Self-Host Your Tracing Backend?

Running your own tracing backend gives you complete control over data retention, sampling policies, and access controls. SaaS observability platforms charge based on data ingestion volume, and tracing data grows quickly as you instrument more services. Self-hosted backends let you retain traces for months or years without per-gigabyte fees.

For organizations already running Grafana for metrics and Loki for logs, adding Tempo creates a unified observability stack managed by a single team. For teams invested in Elasticsearch, Jaeger integrates naturally with existing ELK infrastructure. And for smaller teams, Zipkin provides a low-friction entry point into distributed tracing.

For a complete observability strategy, see our [Grafana observability guide](../2026-04-27-coroot-vs-signoz-vs-hyperdx-self-hosted-observability-guide/) and [Prometheus long-term storage comparison](../2026-04-27-grafana-mimir-vs-thanos-vs-cortex-self-hosted-prometheus-long-term-storage-guide-2026/) for complementary monitoring tools.

## Frequently Asked Questions

### Which tracing backend should I choose for a small team?

Start with Zipkin if you need simplicity and low resource usage. A single Zipkin container with in-memory storage is enough for development and small production deployments. If you need persistent traces, add the MySQL backend. For teams already running Grafana, Tempo is a better long-term choice.

### Can I switch from Jaeger to Tempo?

Yes. Both support the OpenTelemetry Protocol (OTLP), so you can send traces to both backends simultaneously and compare results before switching. Tempo also supports the Jaeger Thrift protocol for backward compatibility.

### How much storage do I need for distributed traces?

For Tempo with object storage, expect approximately 50 MB per million spans. Jaeger with Elasticsearch requires about 200 MB per million spans due to indexing overhead. Zipkin with MySQL falls between 100-150 MB per million spans. Actual sizes depend on span attribute count and payload size.

### Does Tempo support the same query features as Jaeger?

Tempo uses TraceQL, which covers most common query patterns: filtering by service name, operation name, duration, span attributes, and trace structure. It does not support full-text search across arbitrary span fields the way Jaeger with Elasticsearch does. For most operational use cases, TraceQL is sufficient.

### Can I use head-based sampling to reduce trace volume?

Yes. All three backends work with the OpenTelemetry Collector's sampling processors. Head-based sampling (probabilistic, rate-limited) discards spans before they reach the backend. Tail-based sampling evaluates complete traces and keeps only those meeting specific criteria, which is more efficient for catching rare errors.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Grafana Tempo vs Jaeger vs Zipkin: Best Self-Hosted Distributed Tracing Backends 2026",
  "description": "Compare Grafana Tempo, Jaeger, and Zipkin - the three leading open-source distributed tracing backends for self-hosted observability.",
  "datePublished": "2026-05-07",
  "dateModified": "2026-05-07",
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
