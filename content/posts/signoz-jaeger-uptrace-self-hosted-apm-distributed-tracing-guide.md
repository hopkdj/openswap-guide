---
title: "SigNoz vs Jaeger vs Uptrace: Best Self-Hosted APM & Distributed Tracing Guide 2026"
date: 2026-04-13
tags: ["comparison", "guide", "self-hosted", "privacy", "monitoring", "devops"]
draft: false
description: "Complete guide to self-hosted APM and distributed tracing in 2026. Compare SigNoz, Jaeger, and Uptrace — open-source alternatives to Datadog and New Relic with Docker setup and configuration."
---

Application performance monitoring (APM) and distributed tracing are no longer optional for modern software teams. As applications grow from monoliths into collections of microservices, containerized workloads, and serverless functions, understanding how requests flow through your infrastructure becomes essential. The dominant players — Datadog, New Relic, Dynatrace, and AppDynamics — charge premium prices that scale with every host, container, and gigabyte of telemetry data you generate.

This guide covers three powerful open-source, self-hosted alternatives: **SigNoz**, **Jaeger**, and **Uptrace**. Each can replace commercial APM products while keeping your data on your own infrastructure, under your control, and without surprise bills when traffic spikes.

## Why Self-Host Your APM and Distributed Tracing

Running your own application performance monitoring stack delivers tangible advantages that hosted platforms simply cannot match:

**Cost predictability** is the most immediate benefit. Commercial APM vendors price by host, container, ingestion volume, or retained data — sometimes all three simultaneously. A 50-microservice architecture processing millions of requests daily can easily generate $2,000–$10,000+ per month in APM costs. Self-hosted solutions run on your existing infrastructure with no per-host fees, no data caps, and no premium charges for long-term retention.

**Data sovereignty and compliance** matter for organizations in healthcare, finance, and government. Sending application traces, error logs, and performance metrics to a third-party cloud creates compliance overhead under GDPR, HIPAA, SOC 2, and industry-specific regulations. Self-hosting keeps every byte of telemetry within your security boundary.

**Unlimited retention** means you can keep tracing data for months or years instead of the 7–30 day windows typical of hosted APM. Long retention enables trend analysis, capacity planning, compliance audits, and post-incident forensics that would be cost-prohibitive with commercial vendors.

**No vendor lock-in** gives you the flexibility to modify, extend, or integrate your observability stack without being constrained by a vendor's roadmap. Open-source APM tools implement the OpenTelemetry standard, ensuring your instrumentation code works across platforms.

## What Is Distributed Tracing?

Distributed tracing tracks individual requests as they travel through a distributed system. When a user clicks "checkout" on an e-commerce site, that single action might trigger calls to an API gateway, authentication service, inventory database, payment processor, notification queue, and email service. A distributed trace captures this entire journey as a series of **spans** — individual units of work — organized in a **trace** that shows timing, dependencies, and failures.

**APM** goes further by combining traces with metrics (CPU, memory, request rates), logs, and application-level data (error rates, response time percentiles, throughput) to provide a unified view of system health.

The industry standard for instrumenting applications is **OpenTelemetry** (OTel), a CNCF project that provides vendor-neutral APIs and SDKs in virtually every programming language. All three platforms covered in this guide are fully compatible with OpenTelemetry, meaning you instrument your application once and can switch between observability backends without rewriting code.

## SigNoz: Full-Stack Open-Source APM

SigNoz is the most comprehensive open-source APM platform available today. Built specifically as an open-source alternative to Datadog and New Relic, it provides unified application performance monitoring, distributed tracing, log management, and alerting in a single product. SigNoz uses ClickHouse as its storage backend, which delivers exceptional query performance on large telemetry datasets.

### Key Features

- **Unified APM dashboard** combining metrics, traces, and logs in a single interface
- **OpenTelemetry-native** — instrument once, send to any backend
- **Built-in service topology map** showing dependencies between services
- **Custom dashboards** with a drag-and-drop query builder
- **Automatic metric collection** for RED (Rate, Errors, Duration) and USE (Utilization, Saturation, Errors) metrics
- **Alerting engine** with support for Slack, PagerDuty, webhooks, and email
- **Exception tracking** with stack traces and error grouping
- **ClickHouse backend** for fast queries over billions of data points
- **SaaS and self-hosted** deployment options

### Architecture

SigNoz runs three main components:

1. **Query Service** — handles API requests, query processing, and aggregation
2. **ClickHouse** — columnar database for storing and querying telemetry data
3. **Frontend** — React-based web UI for dashboards and exploration

All components communicate via gRPC and HTTP APIs. The OpenTelemetry Collector receives data from your instrumented applications and forwards it to SigNoz.

### [docker](https://www.docker.com/) Compose Installation

SigNoz provides an official Docker Compose setup that deploys the entire stack:

```bash
# Clone the SigNoz repository
git clone -b main https://github.com/SigNoz/signoz.git
cd signoz/deploy/

# Run the installation script
sudo ./install.sh

# Alternatively, use Docker Compose directly
docker compose -f docker/clickhouse-setup/docker-compose.yaml up -d
```

Once running, the SigNoz UI is available at `http://localhost:3301`.

### OpenTelemetry Collector Configuration

Configure the OTel Collector to send data to SigNoz:

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 5s
    send_batch_size: 1000

exporters:
  otlp:
    endpoint: signoz-query-service:4317  # SigNoz OTLP endpoint
    tls:
      insecure: true

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlp]
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlp]
    logs:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlp]
```

### Application Instrumentation Example (Python)

```bash
# Install OpenTelemetry packages
pip install opentelemetry-api \
            opentelemetry-sdk \
            opentelemetry-exporter-otlp \
            opentelemetry-instrumentation-flask \
            opentelemetry-instrumentation-requests

# Run your application with automatic instrumentation
OTEL_SERVICE_NAME=checkout-service \
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 \
opentelemetry-instrument python app.py
```

For manual instrumentation with custom spans:

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Configure the tracer provider
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Add OTLP exporter pointing to SigNoz
otlp_exporter = OTLPSpanExporter(
    endpoint="http://localhost:4317",
    insecure=True
)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(otlp_exporter)
)

# Create spans in your application code
with tracer.start_as_current_span("process_payment") as span:
    span.set_attribute("payment.method", "credit_card")
    span.set_attribute("payment.amount", 49.99)
    result = process_payment(amount=49.99)
    if result.success:
        span.set_status(trace.StatusCode.OK)
    else:
        span.set_status(trace.StatusCode.ERROR, result.error)
```

### Resource Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8+ GB |
| Storage (SSD) | 20 GB | 100+ GB |
| Network | 100 Mbps | 1 Gbps |

ClickHouse performance scales with available RAM — more memory means larger caches and faster query responses. For production workloads with millions of spans per day, allocate at least 16 GB RAM and fast NVMe storage.

### Strengths

- Most feature-complete open-source APM — closest direct replacement for Datadog
- Excellent ClickHouse performance for high-volume telemetry data
- Unified UI for traces, metrics, and logs reduces tool sprawl
- Active development with regular releases and a growing community
- Supports OpenTelemetry natively across all signals

### Limitations

- Higher resource requirements compared to Jaeger alone
- ClickHouse storage can grow quickly under sustained high-volume ingestion
- Fewer third-party integrations compared to commercial platforms
- Alerting system is functional but less mature than Datadog monitors

## Jaeger: The CNCF Distributed Tracing Standard

Jaeger is one of the oldest and most widely adopted open-source distributed tracing platforms. Originally developed by Uber and later donated to the CNCF, Jaeger graduated as a top-level CNCF project in 2019. It focuses specifically on distributed tracing — collecting, storing, and visualizing traces — without the broader APM features of SigNoz.

### Key Features

- **CNCF Graduated project** — mature, battle-tested at enterprise scale
- **Multiple storage backends** — Elasticsearch, OpenSearch, Cassandra, Badger (embedded), gRPC plugin
- **Jaeger UI** — dedicated trace visualization with flame graphs, service dependency diagrams, and search
- **Sampling strategies** — probabilistic, rate-limiting, and adaptive sampling
- **HotROD demo** — built-in demo application for testing and learning
- **Cross-service correlation** — trace propagation across service boundaries
- **Wide SDK support** — official SDKs for Go, Java, Python, Node.js, and C++

### Architecture

Jaeger consists of several components that can be deployed independently:

1. **Jaeger Agent** — lightweight daemon that receives spans from applications via UDP
2. **Jaeger Collector** — receives spans, validates them, and writes to storage
3. **Query Service** — retrieves traces from storage and serves the UI
4. **Storage Backend** — Elasticsearch, OpenSearch, Cassandra, or Badger

The modern deployment pattern uses the **Jaeger All-in-One** container for development and a distributed architecture for production.

### Docker Compose Installation

For development and testing, Jaeger All-in-One provides everything in a single container:

```bash
# Quick start with All-in-One
docker run -d --name jaeger \
  -e COLLECTOR_ZIPKIN_HOST_PORT=:9411 \
  -e COLLECTOR_OTLP_ENABLED=true \
  -p 6831:6831/udp \
  -p 6832:6832/udp \
  -p 5778:5778 \
  -p 16686:16686 \
  -p 4317:4317 \
  -p 4318:4318 \
  -p 14250:14250 \
  -p 14268:14268 \
  -p 14269:14269 \
  -p 9411:9411 \
  jaegertracing/all-in-one:latest
```

The Jaeger UI is available at `http://localhost:16686`.

### Production Deployment with Elasticsearch

For production use, deploy Jaeger with Elasticsearch as the storage backend:

```yaml
# docker-compose.yml - Production Jaeger with Elasticsearch
version: "3.8"

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.12.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    volumes:
      - es-data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"

  jaeger-collector:
    image: jaegertracing/jaeger-collector:latest
    command: [
      "--es.server-urls=http://elasticsearch:9200",
      "--collector.otlp.grpc.host-port=:4317",
      "--collector.otlp.http.host-port=:4318",
      "--collector.num-workers=100",
      "--collector.queue-size=100000"
    ]
    ports:
      - "4317:4317"
      - "4318:4318"
    depends_on:
      - elasticsearch

  jaeger-query:
    image: jaegertracing/jaeger-query:latest
    command: [
      "--es.server-urls=http://elasticsearch:9200",
      "--query.base-path=/jaeger"
    ]
    ports:
      - "16686:16686"
    depends_on:
      - elasticsearch

  jaeger-agent:
    image: jaegertracing/jaeger-agent:latest
    command: [
      "--reporter.grpc.host-port=jaeger-collector:14250"
    ]
    ports:
      - "6831:6831/udp"
      - "6832:6832/udp"
    depends_on:
      - jaeger-collector

volumes:
  es-data:
```

### Index Lifecycle Management

For long-running Jaeger deployments, configure Elasticsearch index lifecycle management (ILM) to control data retention:

```bash
# Create an ILM policy for 30-day retention
curl -X PUT "http://localhost:9200/_ilm/policy/jaeger-policy" \
  -H 'Content-Type: application/json' \
  -d '{
    "policy": {
      "phases": {
        "hot": {
          "actions": {
            "rollover": {
              "max_age": "1d",
              "max_primary_shard_size": "50gb"
            }
          }
        },
        "delete": {
          "min_age": "30d",
          "actions": {
            "delete": {}
          }
        }
      }
    }
  }'

# Apply the policy to Jaeger indices
curl -X PUT "http://localhost:9200/_index_template/jaeger-template" \
  -H 'Content-Type: application/json' \
  -d '{
    "index_patterns": ["jaeger-*"],
    "template": {
      "settings": {
        "number_of_shards": 3,
        "number_of_replicas": 0,
        "index.lifecycle.name": "jaeger-policy"
      }
    }
  }'
```

### Application Instrumentation (Go)

```go
package main

import (
    "context"
    "log"
    "net/http"

    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/attribute"
    "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
    "go.opentelemetry.io/otel/sdk/resource"
    "go.opentelemetry.io/otel/sdk/trace"
    semconv "go.opentelemetry.io/otel/semconv/v1.21.0"
)

func initTracer() func() {
    ctx := context.Background()
    exp, err := otlptracegrpc.New(ctx,
        otlptracegrpc.WithEndpoint("localhost:4317"),
        otlptracegrpc.WithInsecure(),
    )
    if err != nil {
        log.Fatalf("failed to create exporter: %v", err)
    }

    tp := trace.NewTracerProvider(
        trace.WithBatcher(exp),
        trace.WithResource(resource.NewWithAttributes(
            semconv.SchemaURL,
            semconv.ServiceName("order-service"),
            semconv.ServiceVersion("1.0.0"),
        )),
    )
    otel.SetTracerProvider(tp)

    return func() {
        if err := tp.Shutdown(ctx); err != nil {
            log.Printf("error shutting down tracer: %v", err)
        }
    }
}

func main() {
    cleanup := initTracer()
    defer cleanup()

    tracer := otel.Tracer("order-service")

    http.HandleFunc("/orders", func(w http.ResponseWriter, r *http.Request) {
        ctx, span := tracer.Start(r.Context(), "get-orders")
        defer span.End()

        span.SetAttributes(
            attribute.String("customer.id", r.URL.Query().Get("customer_id")),
            attribute.Int("order.limit", 50),
        )

        // Your order retrieval logic here
        w.WriteHeader(http.StatusOK)
        w.Write([]byte("Orders retrieved successfully"))
    })

    log.Println("Server starting on :8080")
    http.ListenAndServe(":8080", nil)
}
```

### Sampling Configuration

Sampling reduces the volume of traces stored by keeping only a percentage. Configure sampling in Jaeger:

```yaml
# sampling.json - Sampling strategies
{
  "default_strategy": {
    "type": "probabilistic",
    "param": 0.1
  },
  "service_strategies": [
    {
      "service": "payment-service",
      "type": "probabilistic",
      "param": 1.0
    },
    {
      "service": "checkout-api",
      "type": "rate_limiting",
      "param": 5
    }
  ]
}
```

This configuration samples 10% of all traces by default, captures 100% of payment-service traces, and limits checkout-api to 5 traces per second.

### Resource Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU (per collector) | 1 core | 2+ cores |
| RAM | 2 GB | 4+ GB |
| Storage | 10 GB | 50+ GB |
| Elasticsearch nodes | 1 | 3+ |

Jaeger's resource footprint is lighter than SigNoz because it does not include metrics or log aggregation. However, Elasticsearch is resource-intensive and dominates the infrastructure requirements.

### Strengths

- CNCF Graduated status with enterprise-grade maturity
- Proven at massive scale — Uber processes millions of traces per second with Jaeger
- Flexible storage backend choice (Elasticsearch, Cassandra, Badger)
- Advanced sampling strategies including adaptive sampling
- Large ecosystem of integrations and community support
- Focus on tracing means fewer moving parts than full-stack APM

### Limitations

- Tracing only — no metrics aggregation, no log management, no alerting
[prometheus](https://prometheus.io/) separate tools (Prometheus, Grafana, Loki) for a complete observability stack
- Elasticsearch storage can be expensive at scale
- UI is focused on trace exploration rather than operational dashboards
- No built-in service topology visualization in older versions

## Uptrace: Lightweight OpenTelemetry Backend

Uptrace is a newer entrant in the open-source observability space. Written in Go and built on ClickHouse, Uptrace provides distributed tracing, metrics, and logging with a focus on simplicity and performance. Unlike SigNoz, which aims to replace Datadog feature-for-feature, Uptrace takes a lighter approach — fast ingestion, efficient storage, and a clean interface without enterprise bloat.

Uptrace offers both an open-source self-hosted version and a commercial SaaS. The self-hosted version includes the core observability features with no artificial limitations on data volume or retention.

### Key Features

- **OpenTelemetry-native** — accepts OTLP natively via gRPC and HTTP
- **ClickHouse storage** — fast ingestion and queries with excellent compression
- **Unified interface** for traces, metrics, and logs
- **Service topology** with automatic dependency detection
- **SQL-like query language** for custom analysis
- **Dashboard support** with customizable widgets
- **Alerting** with notification channels
- **Lightweight** — significantly lower resource requirements than SigNoz
- **Multi-tenancy** support for shared deployments

### Architecture

Uptrace uses a simpler architecture than SigNoz:

1. **Uptrace Server** — single Go binary handling ingestion, querying, and the web UI
2. **ClickHouse** — storage backend for all telemetry data
3. **OpenTelemetry Collector** (optional) — receives data from applications and forwards to Uptrace

The single-binary design means fewer containers to manage, simpler networking, and easier upgrades.

### Docker Compose Installation

```yaml
# docker-compose.yml - Uptrace
version: "3.8"

services:
  clickhouse:
    image: clickhouse/clickhouse-server:24.3
    environment:
      - CLICKHOUSE_DB=uptrace
    volumes:
      - clickhouse-data:/var/lib/clickhouse
      - ./clickhouse-config.xml:/etc/clickhouse-server/config.d/config.xml
    ports:
      - "9000:9000"
      - "8123:8123"
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:8123/ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  uptrace:
    image: uptrace/uptrace:latest
    environment:
      - UPTRACE_DSN=http://uptrace@uptrace:14317/1
      - CLICKHOUSE_DSN=http://clickhouse:9000
    ports:
      - "14317:14317"
      - "14318:14318"
      - "8080:8080"
    volumes:
      - uptrace-data:/data
      - ./uptrace.conf.yml:/etc/uptrace/uptrace.conf.yml
    depends_on:
      clickhouse:
        condition: service_healthy

volumes:
  clickhouse-data:
  uptrace-data:
```

Create the Uptrace configuration file:

```yaml
# uptrace.conf.yml
ch:
  dsn: "http://clickhouse:9000"
  database: "uptrace"

listener:
  otlp_grpc:
    endpoint: ":14317"
  otlp_http:
    endpoint: ":14318"

server:
  http:
    endpoint: ":8080"

logging:
  level: info
  format: json
```

Start the stack:

```bash
docker compose up -d
```

The Uptrace UI is available at `http://localhost:8080`. The default credentials are `admin@example.com` / `uptrace`.

### Direct Instrumentation Without OTel Collector

One advantage of Uptrace is that applications can send data directly to the Uptrace server without running a separate OTel Collector:

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Point directly to Uptrace
exporter = OTLPSpanExporter(
    endpoint="http://localhost:14317",
    insecure=True
)

provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer("user-service")

with tracer.start_as_current_span("authenticate_user") as span:
    span.set_attribute("user.email", "user@example.com")
    span.set_attribute("auth.method", "oauth2")
    # Authentication logic
```

### ClickHouse Optimization for Production

For high-throughput deployments, tune ClickHouse for observability workloads:

```xml
<!-- clickhouse-config.xml -->
<clickhouse>
    <max_concurrent_queries>200</max_concurrent_queries>
    <max_threads>8</max_threads>
    <max_memory_usage>16000000000</max_memory_usage>

    <profiles>
        <default>
            <max_memory_usage>12000000000</max_memory_usage>
            <use_uncompressed_cache>0</use_uncompressed_cache>
            <load_balancing>random</load_balancing>
        </default>
    </profiles>

    <merge_tree>
        <max_suspicious_broken_parts>5</max_suspicious_broken_parts>
        <parts_to_delay_insert>150</parts_to_delay_insert>
        <parts_to_throw_insert>300</parts_to_throw_insert>
        <max_delay_to_insert>2</max_delay_to_insert>
    </merge_tree>
</clickhouse>
```

These settings increase query concurrency, limit memory per query to 12 GB, and configure MergeTree to handle high insert rates gracefully.

### Resource Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 1 core | 2+ cores |
| RAM | 2 GB | 4+ GB |
| Storage (SSD) | 10 GB | 50+ GB |
| ClickHouse RAM | 2 GB | 8+ GB |

Uptrace is the lightest option of the three, requiring fewer containers and less memory overhead. The single-binary server design reduces operational com[plex](https://www.plex.tv/)ity.

### Strengths

- Lowest resource requirements — ideal for small teams and edge deployments
- Direct OTLP ingestion without requiring a separate OTel Collector
- Simple single-binary server reduces operational overhead
- Good ClickHouse compression reduces storage costs
- Clean, intuitive interface with fast query performance
- Multi-tenancy for shared team deployments

### Limitations

- Smaller community and fewer third-party integrations
- Less mature than SigNoz and Jaeger — fewer enterprise features
- Alerting system is basic compared to commercial platforms
- Documentation is thinner, especially for advanced configurations
- Fewer deployment examples and community tutorials

## Comparison: SigNoz vs Jaeger vs Uptrace

| Feature | SigNoz | Jaeger | Uptrace |
|---------|--------|--------|---------|
| **Primary focus** | Full-stack APM | Distributed tracing | Lightweight APM |
| **Traces** | Yes (OTLP) | Yes (OTLP, Jaeger) | Yes (OTLP) |
| **Metrics** | Yes | No | Yes |
| **Logs** | Yes | No | Yes |
| **Storage** | ClickHouse | ES, OpenSearch, Cassandra, Badger | ClickHouse |
| **Alerting** | Built-in | No | Built-in |
| **Service map** | Yes | Partial | Yes |
| **Dashboards** | Yes | No | Yes |
| **Sampling** | Head-based | Probabilistic, rate-limiting, adaptive | Head-based |
| **OpenTelemetry** | Native | Compatible | Native |
| **Multi-tenancy** | Limited | No | Yes |
| **SaaS option** | Yes | No | Yes |
| **Resource usage** | High | Medium | Low |
| **Maturity** | Growing | CNCF Graduated | Emerging |
| **Best for** | Teams replacing Datadog | Teams needing tracing only | Small teams, edge deployments |

### When to Choose Each Platform

**Choose SigNoz** if you want a complete APM replacement for Datadog or New Relic. It provides traces, metrics, logs, alerting, and dashboards in a single product. The ClickHouse backend handles high-volume ingestion well, and the feature set covers most enterprise observability requirements. It is the best choice for teams that want one tool instead of assembling a custom stack from multiple components.

**Choose Jaeger** if your primary need is distributed tracing and you already have metrics and log solutions in place. If you run Prometheus for metrics and Grafana for dashboards, Jaeger fills the tracing gap perfectly. Its CNCF Graduated status means it is stable, well-tested, and supported by a large community. Use Jaeger when tracing is the missing piece of an existing observability puzzle.

**Choose Uptrace** if you have limited infrastructure resources or operate on the edge. Its single-binary design, low memory footprint, and simple deployment make it ideal for small teams, homelabs, and resource-constrained environments. When you need basic APM capabilities without the overhead of SigNoz or the complexity of running Jaeger plus complementary tools, Uptrace delivers.

## Complete Deployment: Full Observability Stack

For a production-grade observability platform, combine your chosen APM with complementary tools. Here is a reference architecture using SigNoz as the central APM:

```yaml
# docker-compose.yml - Full Observability Stack
version: "3.8"

networks:
  observability:
    driver: bridge

volumes:
  clickhouse-data:
  prometheus-data:
  grafana-data:

services:
  # APM: SigNoz (traces, metrics, logs)
  signoz-query-service:
    image: signoz/query-service:latest
    container_name: signoz-query
    networks: [observability]
    ports:
      - "3301:3301"
      - "4317:4317"
    depends_on:
      - clickhouse

  clickhouse:
    image: clickhouse/clickhouse-server:24.3
    container_name: clickhouse
    networks: [observability]
    volumes:
      - clickhouse-data:/var/lib/clickhouse

  # Metrics collection
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    networks: [observability]
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"

  # Dashboards and visualization
  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    networks: [observability]
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    ports:
      - "3000:3000"

  # OTel Collector for application telemetry
  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    container_name: otel-collector
    networks: [observability]
    volumes:
      - ./otel-collector-config.yaml:/etc/otelcol-contrib/config.yaml
    ports:
      - "4319:4317"  # OTLP gRPC
      - "4320:4318"  # OTLP HTTP
      - "8888:8888"   # Prometheus metrics
```

This stack gives you:
- **SigNoz** for APM, traces, and log aggregation
- **Prometheus** for infrastructure and application metrics
- **Grafana** for custom dashboards combining data from all sources
- **OpenTelemetry Collector** as a universal ingestion layer

## Cost Comparison: Self-Hosted vs Commercial APM

For a 20-service architecture generating approximately 50 million spans per day:

| Cost Factor | Datadog APM | New Relic | SigNoz (self-hosted) | Jaeger (self-hosted) | Uptrace (self-hosted) |
|-------------|------------|-----------|---------------------|---------------------|----------------------|
| Monthly cost | $4,000–$8,000 | $2,500–$5,000 | Infrastructure only | Infrastructure only | Infrastructure only |
| Per-host fee | $31–$58 | $0–$25 | None | None | None |
| Data retention | 15 days (standard) | 30 days (standard) | Unlimited | Configurable | Unlimited |
| Additional hosts | +$31–$58/mo each | +$0–$25/mo each | Free | Free | Free |
| Alerting | Included | Included | Included | Not included | Included |
| Support cost | Included | Included | Community/Enterprise | Community | Community/SaaS |

The self-hosted option typically costs $200–$600/month in infrastructure (servers, storage, networking) regardless of the number of services or data volume, compared to thousands for commercial equivalents.

## Migration Tips

If you are moving from a commercial APM to a self-hosted solution:

1. **Run both systems in parallel** for at least two weeks. Instrument your applications to send data to both the commercial platform and your new self-hosted instance simultaneously. This gives you time to validate that traces are complete and dashboards are accurate.

2. **Start with OpenTelemetry** in your applications. Even if you keep your current APM temporarily, using OTel as your instrumentation layer means you can switch backends by changing configuration, not code.

3. **Migrate dashboards incrementally**. Recreate your most-used dashboards first — the ones your team checks daily. Less frequently used dashboards can be rebuilt on demand.

4. **Test alerting thoroughly**. Create test alerts that fire on known conditions and verify they reach your notification channels. Self-hosted alerting may behave differently from commercial platforms.

5. **Plan storage capacity**. Monitor ClickHouse or Elasticsearch disk growth during the parallel run. Size your storage to handle your expected retention period with a 30% buffer.

6. **Document your new procedures**. Commercial APM platforms often have runbooks, SOPs, and incident response procedures. Update these documents to reflect your self-hosted stack.

## Conclusion

Self-hosted APM and distributed tracing platforms have matured significantly. **SigNoz** leads the pack for teams wanting a complete Datadog replacement with traces, metrics, logs, and alerting in one product. **Jaeger** remains the gold standard for dedicated distributed tracing, especially when combined with existing metrics and logging infrastructure. **Uptrace** is the lightweight alternative for teams with limited resources who still need meaningful observability.

All three implement OpenTelemetry, so the instrumentation effort is the same regardless of which backend you choose. Start instrumenting with OTel today, deploy a self-hosted backend, and take back control of your application performance data.

## Frequently Asked Questions (FAQ)

### Which one should I choose in 2026?

The best choice depends on your specific requirements:

- **For beginners**: Start with the simplest option that covers your core use case
- **For production**: Choose the solution with the most active community and documentation
- **For teams**: Look for collaboration features and user management
- **For privacy**: Prefer fully open-source, self-hosted options with no telemetry

Refer to the comparison table above for detailed feature breakdowns.

### Can I migrate between these tools?

Most tools support data import/export. Always:
1. Backup your current data
2. Test the migration on a staging environment
3. Check official migration guides in the documentation

### Are there free versions available?

All tools in this guide offer free, open-source editions. Some also provide paid plans with additional features, priority support, or managed hosting.

### How do I get started?

1. Review the comparison table to identify your requirements
2. Visit the official documentation (links provided above)
3. Start with a Docker Compose setup for easy testing
4. Join the community forums for troubleshooting
