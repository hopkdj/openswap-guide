---
title: "Self-Hosted OpenTelemetry Collector: Complete Observability Pipeline Guide 2026"
date: 2026-04-17
tags: ["opentelemetry", "observability", "self-hosted", "monitoring", "telemetry"]
draft: false
description: "Build a self-hosted observability pipeline with the OpenTelemetry Collector. Learn deployment patterns, configuration strategies, and backend integrations for metrics, traces, and logs in 2026."
---

Modern infrastructure generates three streams of telemetry data: metrics, traces, and logs. For years, teams routed each stream through separate agents and pipelines — Fluentd for logs, Prometheus exporters for metrics, and Jaeger agents for traces. This fragmented approach created operational overhead, inconsistent data, and vendor lock-in at every layer.

The OpenTelemetry Collector changed that equation. It is a single, vendor-agnostic binary that receives, processes, and exports telemetry data of all types. Deploy it once, configure it with YAML, and route your entire observability pipeline through one piece of infrastructure. This guide walks you through deploying the OpenTelemetry Collector in a self-hosted environment, integrating it with open-source backends, and optimizing it for production workloads in 2026.

## Why Self-Host the OpenTelemetry Collector

Running your own observability pipeline offers advantages that managed services cannot match:

**Complete data ownership.** Telemetry data often contains sensitive information — database queries, user IDs, internal service names, and infrastructure topology. Self-hosting ensures this data never leaves your network. Compliance frameworks like GDPR, HIPAA, and SOC 2 frequently require strict data residency controls that managed observability platforms struggle to guarantee.

**Zero per-telemetry pricing.** Managed observability platforms charge by the gigabyte ingested, by the host monitored, or by the number of custom metrics. At scale, these costs compound quickly. A cluster running the OpenTelemetry Collector and open-source backends costs the same whether it ingests 10 GB or 10 TB per day — your infrastructure cost, nothing more.

**Flexible routing and processing.** The Collector lets you sample traces, aggregate metrics, filter logs, and route different data types to different backends — all within a single configuration. You can send high-cardinality metrics to a specialized time-series database while routing error-level logs to a separate retention pipeline. Managed platforms typically lock you into their processing model.

**Resilience and independence.** When your observability provider experiences an outage, you lose visibility at the worst possible moment. A self-hosted pipeline runs on your infrastructure, giving you control over availability zones, redundancy, and disaster recovery. You decide the SLA.

**Protocol standardization.** OpenTelemetry has become the industry standard for telemetry collection. Major vendors — AWS, Google Cloud, Datadog, New Relic, Honeycomb — all support OTLP (OpenTelemetry Protocol) as a first-class ingestion format. By standardizing on OTLP at the collection layer, you keep your options open for any backend, present or future.

## Understanding the OpenTelemetry Collector Architecture

The Collector is built around a pipeline model. Every deployment consists of three layers:

**Receivers** — Entry points for telemetry data. The Collector supports OTLP (gRPC and HTTP), Prometheus scraping, Jaeger, Zipkin, StatsD, Fluent Forward, Kafka, and dozens of other protocols. A single Collector instance can run multiple receivers simultaneously.

**Processors** — Transform and filter data in flight. Common processors handle batch export, sampling, attribute modification, metric aggregation, log filtering, and resource detection. Processors run in order, giving you fine-grained control over data transformation.

**Exporters** — Output destinations. The Collector can export to OTLP-compatible backends (Signoz, Grafana, Tempo, Jaeger), Prometheus-compatible storage (VictoriaMetrics, Mimir), Elasticsearch, Kafka, file systems, and many other destinations.

The architecture looks like this:

```
Applications ──┐
               │
Services   ────┤──► Receivers ──► Processors ──► Exporters ──► Backends
               │
Logs       ────┤
               │
Infra      ────┘
```

### Collector Distributions

Two official distributions exist:

- **OTel Collector Core** — The base distribution with essential receivers, processors, and exporters. Suitable for most deployments.
- **OTel Collector Contrib** — Includes all components from Core plus community-contributed components. Adds support for additional protocols, databases, and cloud integrations. Recommended for production unless you specifically need a minimal binary.

The Contrib distribution is the right choice for most self-hosted deployments because it includes the components you will likely need without requiring custom builds.

## Deploying the OpenTelemetry Collector with Docker Compose

The fastest path to a working deployment is Docker Compose. This setup runs the Collector alongside three open-source backends: Grafana for dashboards, Prometheus-compatible VictoriaMetrics for metrics, and Tempo for traces.

### Step 1: Create the Collector Configuration

Save this file as `otel-collector-config.yaml`:

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

  prometheus:
    config:
      scrape_configs:
        - job_name: 'node-exporter'
          scrape_interval: 15s
          static_configs:
            - targets: ['node-exporter:9100']
        - job_name: 'collector-self'
          scrape_interval: 10s
          static_configs:
            - targets: ['otel-collector:8888']

  filelog:
    include:
      - /var/log/containers/*.log
    start_at: beginning
    include_file_path: true
    include_file_name: false

processors:
  batch:
    timeout: 10s
    send_batch_size: 8192

  memory_limiter:
    check_interval: 1s
    limit_mib: 1024
    spike_limit_mib: 256

  resourcedetection:
    detectors: [env, system, docker]
    timeout: 5s
    override: false

  attributes:
    actions:
      - key: deployment.environment
        value: production
        action: upsert
      - key: service.namespace
        value: backend
        action: upsert

  filter:
    logs:
      log_record:
        - 'attributes["level"] == "DEBUG"'

exporters:
  otlphttp/metrics:
    endpoint: http://victoriametrics:8428
    tls:
      insecure: true

  otlp/traces:
    endpoint: http://tempo:4317
    tls:
      insecure: true

  otlphttp/logs:
    endpoint: http://loki:3100/otlp
    tls:
      insecure: true

  debug:
    verbosity: detailed
    sampling_initial: 5
    sampling_thereafter: 200

service:
  pipelines:
    metrics:
      receivers: [otlp, prometheus]
      processors: [memory_limiter, resourcedetection, attributes, batch]
      exporters: [otlphttp/metrics, debug]
    traces:
      receivers: [otlp]
      processors: [memory_limiter, resourcedetection, batch]
      exporters: [otlp/traces, debug]
    logs:
      receivers: [otlp, filelog]
      processors: [memory_limiter, attributes, filter, batch]
      exporters: [otlphttp/logs, debug]

  telemetry:
    metrics:
      address: 0.0.0.0:8888
    logs:
      level: info
```

### Step 2: Create the Docker Compose File

Save this as `docker-compose.yaml`:

```yaml
version: "3.8"

services:
  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.124.1
    container_name: otel-collector
    restart: unless-stopped
    command: ["--config=/etc/otel/config.yaml"]
    volumes:
      - ./otel-collector-config.yaml:/etc/otel/config.yaml:ro
      - /var/log/containers:/var/log/containers:ro
    ports:
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP
      - "8888:8888"   # Collector metrics
      - "9411:9411"   # Zipkin (optional)
    networks:
      - observability
    mem_limit: 1g
    deploy:
      resources:
        limits:
          cpus: "1.0"

  victoriametrics:
    image: victoriametrics/victoria-metrics:v1.125.0
    container_name: victoriametrics
    restart: unless-stopped
    command:
      - "--retentionPeriod=30d"
      - "--storageDataPath=/vm-data"
      - "--httpListenAddr=:8428"
    volumes:
      - vm-data:/vm-data
    ports:
      - "8428:8428"
    networks:
      - observability

  tempo:
    image: grafana/tempo:2.7.1
    container_name: tempo
    restart: unless-stopped
    command: ["-config.file=/etc/tempo/config.yaml"]
    volumes:
      - ./tempo-config.yaml:/etc/tempo/config.yaml:ro
      - tempo-data:/tmp/tempo
    ports:
      - "3200:3200"
      - "4317"  # internal OTLP
    networks:
      - observability

  loki:
    image: grafana/loki:3.4.2
    container_name: loki
    restart: unless-stopped
    command: ["-config.file=/etc/loki/config.yaml"]
    volumes:
      - ./loki-config.yaml:/etc/loki/config.yaml:ro
      - loki-data:/loki
    ports:
      - "3100:3100"
    networks:
      - observability

  grafana:
    image: grafana/grafana:11.5.2
    container_name: grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_INSTALL_PLUGINS=grafana-opensearch-datasource
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana-datasources.yaml:/etc/grafana/provisioning/datasources/datasources.yaml:ro
    networks:
      - observability

  node-exporter:
    image: prom/node-exporter:v1.9.1
    container_name: node-exporter
    restart: unless-stopped
    command: ["--path.rootfs=/host"]
    volumes:
      - /:/host:ro,rslave
      - /sys:/host/sys:ro
      - /proc:/host/proc:ro
    ports:
      - "9100:9100"
    networks:
      - observability

volumes:
  vm-data:
  tempo-data:
  loki-data:
  grafana-data:

networks:
  observability:
    driver: bridge
```

### Step 3: Configure Tempo

Save `tempo-config.yaml`:

```yaml
server:
  http_listen_port: 3200

distributor:
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: "0.0.0.0:4317"

ingester:
  max_block_duration: 5m

compactor:
  compaction:
    block_retention: 72h

storage:
  trace:
    backend: local
    local:
      path: /tmp/tempo/traces
    wal:
      path: /tmp/tempo/wal
```

### Step 4: Configure Loki

Save `loki-config.yaml`:

```yaml
auth_enabled: false

server:
  http_listen_port: 3100
  grpc_listen_port: 9096

common:
  instance_addr: 127.0.0.1
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
    - from: "2024-01-01"
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h

limits_config:
  allow_structured_metadata: true
  otlp_config:
    resource_attributes:
      - from_context: service.name
      - from_context: service.namespace
      - from_context: deployment.environment

query_range:
  results_cache:
    cache:
      embedded_cache:
        enabled: true
        max_size_mb: 128
```

### Step 5: Provision Grafana Data Sources

Save `grafana-datasources.yaml`:

```yaml
apiVersion: 1

datasources:
  - name: VictoriaMetrics
    type: prometheus
    access: proxy
    url: http://victoriametrics:8428
    isDefault: true
    editable: true

  - name: Tempo
    type: tempo
    access: proxy
    url: http://tempo:3200
    uid: tempo
    editable: true
    jsonData:
      tracesToLogsV2:
        datasourceUid: loki
        spanStartTimeShift: -1h
        spanEndTimeShift: 1h

  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    uid: loki
    editable: true
```

### Step 6: Start Everything

```bash
docker compose up -d
```

Verify the Collector is running and accepting data:

```bash
# Check OTLP gRPC endpoint
docker exec otel-collector grpcurl -plaintext localhost:4317 list

# Check Collector self-metrics
curl -s http://localhost:8888/metrics | head -20

# Check VictoriaMetrics ingestion
curl -s http://localhost:8428/api/v1/status/tsdb

# Check Tempo readiness
curl -s http://localhost:3200/ready

# Check Loki readiness
curl -s http://localhost:3100/ready
```

Access Grafana at `http://localhost:3000` with credentials `admin/admin`. You should see VictoriaMetrics, Tempo, and Loki provisioned as data sources.

## Instrumenting Applications to Send Telemetry

With the Collector running, applications send telemetry directly to it using the OTLP protocol. Here is how to instrument services in different languages.

### Python Application

```bash
pip install opentelemetry-distro opentelemetry-exporter-otlp-proto-grpc
opentelemetry-bootstrap -a install
```

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

resource = Resource.create({
    "service.name": "payment-service",
    "service.version": "2.1.0",
    "deployment.environment": "production"
})

provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(
    OTLPSpanExporter(endpoint="otel-collector:4317", insecure=True)
)
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("process-payment") as span:
    span.set_attribute("payment.amount", 49.99)
    span.set_attribute("payment.currency", "USD")
    # business logic here
```

### Go Application

```go
package main

import (
    "context"
    "log"

    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
    "go.opentelemetry.io/otel/sdk/resource"
    sdktrace "go.opentelemetry.io/otel/sdk/trace"
    semconv "go.opentelemetry.io/otel/semconv/v1.26.0"
)

func initTracer() func() {
    ctx := context.Background()

    exp, err := otlptracegrpc.New(ctx,
        otlptracegrpc.WithInsecure(),
        otlptracegrpc.WithEndpoint("otel-collector:4317"),
    )
    if err != nil {
        log.Fatal(err)
    }

    res, _ := resource.New(ctx,
        resource.WithAttributes(
            semconv.ServiceName("order-service"),
            semconv.ServiceVersion("1.4.2"),
        ),
    )

    tp := sdktrace.NewTracerProvider(
        sdktrace.WithBatcher(exp),
        sdktrace.WithResource(res),
    )
    otel.SetTracerProvider(tp)

    return func() { tp.Shutdown(ctx) }
}
```

### Kubernetes Deployment (Sidecar Pattern)

For Kubernetes clusters, deploy the Collector as a DaemonSet so every node runs a local instance. Applications send telemetry to `localhost:4317`, avoiding network hops.

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: otel-collector
  namespace: observability
spec:
  selector:
    matchLabels:
      app: otel-collector
  template:
    metadata:
      labels:
        app: otel-collector
    spec:
      containers:
        - name: otel-collector
          image: otel/opentelemetry-collector-contrib:0.124.1
          args: ["--config=/etc/otel/config.yaml"]
          ports:
            - containerPort: 4317
              hostPort: 4317
              protocol: TCP
            - containerPort: 4318
              hostPort: 4318
              protocol: TCP
          volumeMounts:
            - name: config
              mountPath: /etc/otel
            - name: varlog
              mountPath: /var/log/containers
              readOnly: true
          resources:
            limits:
              cpu: 500m
              memory: 512Mi
            requests:
              cpu: 200m
              memory: 256Mi
      volumes:
        - name: config
          configMap:
            name: otel-collector-config
        - name: varlog
          hostPath:
            path: /var/log/containers
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: otel-collector-config
  namespace: observability
data:
  config.yaml: |
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
        send_batch_size: 4096
      k8sattributes:
        extract:
          metadata:
            - k8s.namespace.name
            - k8s.deployment.name
            - k8s.pod.name
            - k8s.container.name

    exporters:
      otlphttp/metrics:
        endpoint: http://victoriametrics.observability:8428
      otlp/traces:
        endpoint: http://tempo.observability:4317
      otlphttp/logs:
        endpoint: http://loki.observability:3100/otlp

    service:
      pipelines:
        metrics:
          receivers: [otlp]
          processors: [k8sattributes, batch]
          exporters: [otlphttp/metrics]
        traces:
          receivers: [otlp]
          processors: [k8sattributes, batch]
          exporters: [otlp/traces]
        logs:
          receivers: [otlp]
          processors: [k8sattributes, batch]
          exporters: [otlphttp/logs]
```

## Production Configuration Strategies

The configuration above works for getting started. Production deployments require additional considerations.

### Memory and Resource Management

The Collector runs unbuffered by default, meaning slow exporters can cause memory to grow. Always deploy the `memory_limiter` processor:

```yaml
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 2048       # Hard limit
    spike_limit_mib: 512  # Allowed burst above limit
```

Set `limit_mib` to roughly 80% of your container memory allocation. The `spike_limit_mib` should be about 25% of `limit_mib`. When memory approaches the limit, the Collector rejects incoming data rather than crashing.

### Batch Processing

The `batch` processor is essential for throughput. Without it, every span, metric, or log line generates an individual export request:

```yaml
processors:
  batch:
    timeout: 5s              # Flush after this duration
    send_batch_size: 8192    # Or this many items
    send_batch_max_size: 16384  # Hard cap on batch size
```

For high-throughput environments, increase `send_batch_size` to 16384 or higher. The trade-off is slightly higher latency — data waits up to `timeout` seconds before export.

### Trace Sampling

In production, capturing 100% of traces wastes storage and processing power. Use the `probabilisticsampler` processor:

```yaml
processors:
  probabilistic_sampler:
    sampling_percentage: 10  # Keep 10% of all traces
    hash_seed: 42            # Consistent sampling across restarts
```

For error-focused sampling, combine probabilistic sampling with a tail-sampling processor:

```yaml
processors:
  tail_sampling:
    decision_wait: 10s
    num_traces: 50000
    expected_new_traces_per_sec: 1000
    policies:
      - name: errors
        type: status_code
        status_code:
          status_codes: [ERROR]
      - name: slow-traces
        type: latency
        latency:
          threshold_ms: 2000
      - name: random-sample
        type: probabilistic
        probabilistic:
          sampling_percentage: 5
```

This configuration keeps 100% of error traces and slow traces while sampling 5% of normal traffic.

### Data Redaction and Privacy

Telemetry data can leak sensitive information through span attributes and log bodies. Use the `transform` processor to redact:

```yaml
processors:
  transform:
    error_mode: ignore
    trace_statements:
      - context: span
        statements:
          - replace_pattern(attributes["http.url"], "(password=)[^&]*", "$$1[REDACTED]")
          - replace_pattern(attributes["db.statement"], "(?i)(SELECT|INSERT|UPDATE|DELETE)", "[SQL]")
    log_statements:
      - context: log
        statements:
          - replace_pattern(body, "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b", "[EMAIL]")
          - delete_key(attributes, "authorization")
```

## Comparing Backend Options

The OpenTelemetry Collector exports to any OTLP-compatible backend. Here is how the leading open-source options compare:

| Feature | VictoriaMetrics | Prometheus | Grafana Mimir | InfluxDB OSS |
|---------|----------------|------------|---------------|--------------|
| OTLP native | Yes | Via Remote Write | Yes | Via plugin |
| Storage engine | Custom TSDB | Local TSDB | Cortex-based | TSM engine |
| Horizontal scaling | Single + cluster | Federation | Built-in | Limited |
| Long-term retention | Excellent (months/years) | Limited (local) | Excellent | Good |
| Prometheus API compatible | Yes | Native | Yes | Partial |
| Resource usage | Low | Medium | High | Medium |
| Best for | Production metrics | Small deployments | Enterprise scale | Time-series analytics |

| Feature | Grafana Tempo | Jaeger | Signoz | Uptrace |
|---------|--------------|--------|--------|---------|
| Storage backend | Object store / local | Elasticsearch / Cassandra | ClickHouse | ClickHouse |
| OTLP native | Yes | Yes | Yes | Yes |
| Trace-to-metrics | Yes (via Grafana) | Limited | Built-in | Built-in |
| Trace-to-logs | Yes (via Grafana) | Limited | Built-in | Built-in |
| UI quality | Grafana integration | Jaeger UI | Custom UI | Custom UI |
| Scalability | High | Medium | High | Medium |
| Best for | Large-scale tracing | Legacy deployments | Full observability | Lightweight APM |

| Feature | Grafana Loki | Elasticsearch | OpenSearch | SigNoz Logs |
|---------|-------------|---------------|------------|-------------|
| Index strategy | Label-based | Full-text | Full-text | ClickHouse |
| Storage cost | Low | High | High | Medium |
| Query language | LogQL | Lucene / DSL | Lucene / DSL | SQL-like |
| OTLP ingestion | Via OTLP endpoint | Via plugin | Via plugin | Native |
| Scalability | High | High | High | High |
| Best for | Log aggregation | Search-heavy | AWS-compatible | Unified observability |

For a balanced self-hosted stack, the combination of **VictoriaMetrics + Tempo + Loki + Grafana** provides the best price-performance ratio. All four projects are actively maintained, support OTLP natively, and integrate seamlessly through Grafana's unified interface.

## Monitoring the Collector Itself

The Collector exposes its own metrics on port 8888. These metrics let you monitor the health and performance of the pipeline:

```bash
# Key metrics to track
curl -s http://localhost:8888/metrics | grep -E "otelcol_|process_"

# Process metrics
process_resident_memory_bytes    # Memory usage
process_cpu_seconds_total        # CPU consumption

# Collector pipeline metrics
otelcol_receiver_accepted_spans      # Spans received
otelcol_receiver_refused_spans       # Spans rejected (backpressure)
otelcol_exporter_sent_spans          # Spans exported successfully
otelcol_exporter_enqueue_failed_spans # Spans dropped due to queue overflow
otelcol_processor_batch_batch_send_size # Batch sizes

# Queue metrics
otelcol_exporter_queue_capacity     # Queue size limit
otelcol_exporter_queue_size         # Current queue depth
```

Set up alerting on these critical thresholds:

- `otelcol_receiver_refused_spans > 0` — The Collector is rejecting data due to memory pressure
- `otelcol_exporter_enqueue_failed_spans > 0` — Export queues are full, data is being dropped
- `process_resident_memory_bytes > limit_mib` — Memory limit exceeded
- `otelcol_exporter_queue_size / otelcol_exporter_queue_capacity > 0.8` — Queue nearing capacity

Configure Grafana to scrape port 8888 and create dashboards for pipeline health. The official OpenTelemetry Collector repository includes pre-built Grafana dashboards that you can import directly.

## Performance Tuning for High-Throughput Environments

When the Collector handles more than 50,000 spans per second, several optimizations become important:

**Increase GOMAXPROCS.** The Collector respects the `GOMAXPROCS` environment variable. Set it to match your CPU core count for optimal parallelism:

```yaml
environment:
  - GOMAXPROCS=4
```

**Use persistent queues.** The Collector can buffer exported data to disk, surviving restarts without data loss:

```yaml
exporters:
  otlp/traces:
    endpoint: http://tempo:4317
    sending_queue:
      enabled: true
      storage: file_storage/traces
      queue_size: 10000
    retry_on_failure:
      enabled: true
      initial_interval: 5s
      max_interval: 30s
      max_elapsed_time: 300s

extensions:
  file_storage/traces:
    directory: /var/lib/otelcol/traces
```

**Split telemetry types across Collector instances.** For very large deployments, run separate Collector instances for metrics, traces, and logs. This isolates resource consumption and allows independent scaling:

```yaml
# metrics-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 10s
    send_batch_size: 16384

exporters:
  otlphttp/metrics:
    endpoint: http://victoriametrics:8428

service:
  pipelines:
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlphttp/metrics]
```

Deploy three such configurations — one for metrics, one for traces, and one for logs — with independent resource allocations and scaling policies.

## Migration from Legacy Agents

If you currently run Fluentd, Prometheus exporters, or Jaeger agents, migrate incrementally:

1. **Deploy the Collector alongside existing agents.** Configure it to receive from the same sources but do not remove the old agents yet.
2. **Validate data parity.** Compare metrics and traces from both pipelines to confirm the Collector produces equivalent output.
3. **Redirect applications to OTLP.** Update application instrumentation to send directly to the Collector's OTLP endpoint.
4. **Remove legacy agents.** Once all applications send through the Collector, decommission the old agents.

The Collector supports receiving from legacy protocols (Prometheus scrape, StatsD, Jaeger Thrift, Zipkin) so you can migrate applications one at a time without disrupting your entire infrastructure.

## Summary

The OpenTelemetry Collector transforms observability from a fragmented collection of tools into a unified, programmable pipeline. Self-hosting it gives you complete control over data flow, processing, and storage — without per-telemetry pricing or vendor dependencies.

The key takeaways for production deployments:

- Always deploy the `memory_limiter` and `batch` processors for stability and throughput
- Use tail-based sampling to keep important traces while reducing storage costs
- Redact sensitive data at the processor level before export
- Monitor the Collector's own metrics to detect backpressure and data loss early
- Split telemetry types across separate Collector instances for large-scale environments
- Migrate incrementally from legacy agents using the Collector's protocol compatibility

With VictoriaMetrics, Tempo, and Loki as backends, you get a complete observability stack that costs nothing in licensing fees, scales horizontally, and keeps every byte of telemetry data under your control.
