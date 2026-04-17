---
title: "Self-Hosted OpenTelemetry Collector: Build an Observability Pipeline in 2026"
date: 2026-04-17
tags: ["comparison", "guide", "self-hosted", "privacy", "observability"]
draft: false
description: "Complete guide to self-hosting the OpenTelemetry Collector as a vendor-agnostic observability pipeline. Learn architecture, deployment patterns, configuration, and integration with Prometheus, Jaeger, Loki, and more."
---

Observability is no longer optional for modern infrastructure. The challenge is not collecting data — it is deciding where that data goes, how to process it, and how to avoid vendor lock-in. The OpenTelemetry (OTel) Collector solves exactly this problem. It is a vendor-agnostic, open-source telemetry data plane that receives, processes, and exports traces, metrics, and logs from any source to any backend.

This guide walks you through self-hosting the OpenTelemetry Collector, building a complete observability pipeline, and connecting it to popular open-source backends like Prometheus, Jaeger, Grafana Loki, and ClickHouse.

## Why Self-Host the OpenTelemetry Collector?

Running the OTel Collector yourself gives you capabilities that cloud-hosted alternatives simply cannot match:

**Vendor independence.** The Collector decouples your applications from any specific observability backend. Switch from Jaeger to Tempo, or from Prometheus to VictoriaMetrics, without touching a single line of application code. Your apps send OTLP; the Collector handles routing.

**Data privacy and compliance.** Telemetry data often contains sensitive information — request headers, user identifiers, database queries. Self-hosting keeps this data within your infrastructure, satisfying GDPR, HIPAA, and SOC 2 requirements without relying on third-party data processing agreements.

**Cost control at scale.** Cloud observability platforms charge by ingestion volume, retention period, and query count. At high cardinality or high throughput, these costs explode. Self-hosting with the OTel Collector plus open-source backends gives you predictable infrastructure costs.

**Pre-processing and data filtering.** The Collector can drop noisy spans, redact sensitive attributes, sample high-volume traces, and enrich telemetry with metadata before it reaches your backend. This reduces storage costs and query noise significantly.

**Centralized management.** Instead of configuring dozens of agents across your fleet, you deploy the Collector as a gateway and push configuration centrally. All telemetry flows through a single control plane.

**Reliability and buffering.** The Collector supports persistent queues that buffer data when backends are unavailable. Your applications never drop telemetry during backend maintenance or network outages.

## Architecture: How the Collector Works

The OpenTelemetry Collector has a three-stage pipeline model:

```
[Receivers] → [Processors] → [Exporters]
```

Each stage is modular and configurable:

### Receivers

Receivers ingest telemetry data. They can be push-based (waiting for data to arrive) or pull-based (scraping endpoints). Common receivers:

- **`otlp`** — The standard OTLP receiver. Accepts gRPC (port 4317) and HTTP (port 4318) protocols. This is the primary receiver for modern applications instrumented with OpenTelemetry SDKs.
- **`prometheus`** — Acts as a Prometheus scraper, pulling metrics from `/metrics` endpoints on a configurable interval.
- **`jaeger`** — Accepts Jaeger-native protocols (Thrift HTTP, Thrift Compact, Thrift Binary, gRPC) for backward compatibility with existing Jaeger agents.
- **`zipkin`** — Accepts Zipkin v2 JSON/Thrift format for teams migrating from Zipkin.
- **`hostmetrics`** — Collects system-level metrics (CPU, memory, disk, network) directly from the host OS, replacing node_exporter for basic infrastructure monitoring.
- **`filelog`** — Reads and parses log files from the filesystem, providing a self-contained log shipping capability.

### Processors

Processors transform, filter, and enrich telemetry data in-flight:

- **`batch`** — Batches telemetry before export. This is the single most important processor for performance — it reduces network round trips and backend write amplification.
- **`memory_limiter`** — Prevents the Collector from consuming excessive memory. It drops data or sends backpressure when memory thresholds are exceeded.
- **`filter`** — Drops or keeps telemetry based on attribute matching. Essential for reducing noise from health checks and internal endpoints.
- **`attributes`** — Add, update, delete, or hash span and metric attributes. Use this to redact PII or normalize tag values.
- **`probabilistic_sampler`** — Samples a percentage of traces at the Collector level, reducing storage costs while maintaining statistical representativeness.
- **`transform`** — A powerful OTTL (OpenTelemetry Transformation Language) processor that can modify any field of any telemetry signal using a SQL-like query language.
- **`resource`** — Modify resource-level attributes (service.name, deployment.environment, etc.) across all telemetry.

### Exporters

Exporters send processed data to backends:

- **`otlp`** — Sends OTLP data to another Collector or any OTLP-compatible backend.
- **`prometheusremotewrite`** — Exports metrics in Prometheus remote write format to Prometheus, VictoriaMetrics, Cortex, or Mimir.
- **`jaeger`** / **`tempo`** — Export traces to Jaeger or Grafana Tempo.
- **`loki`** — Export logs to Grafana Loki.
- **`clickhouse`** — Export all three signal types to ClickHouse for unified storage.
- **`debug`** — Prints telemetry to stdout/stderr. Useful for development and troubleshooting.
- **`file`** — Writes telemetry to local files in OTLP JSON format. Good for archival or offline analysis.

## Deployment Patterns

The Collector supports three deployment topologies. Most production setups use a combination.

### Pattern 1: Agent (DaemonSet)

Deploy one Collector instance per host (Kubernetes DaemonSet or systemd service). The agent collects local telemetry and forwards it to a gateway.

```yaml
# docker-compose.yml — Agent mode
services:
  otel-agent:
    image: otel/opentelemetry-collector-contrib:0.122.1
    container_name: otel-agent
    restart: unless-stopped
    volumes:
      - ./otel-agent-config.yaml:/etc/otelcol/config.yaml
      - /var/log:/var/log:ro
      - /:/hostfs:ro
    ports:
      - "4317:4317"
      - "4318:4318"
    environment:
      - OTEL_COLLECTOR_HOST=0.0.0.0
    command: ["--config", "/etc/otelcol/config.yaml"]
```

### Pattern 2: Gateway

Deploy one or more Collector instances as a centralized gateway. All agents forward data here. The gateway does heavy processing (enrichment, sampling, fan-out) and exports to backends.

```yaml
# docker-compose.yml — Gateway mode
services:
  otel-gateway:
    image: otel/opentelemetry-collector-contrib:0.122.1
    container_name: otel-gateway
    restart: unless-stopped
    volumes:
      - ./otel-gateway-config.yaml:/etc/otelcol/config.yaml
    ports:
      - "4317:4317"
      - "4318:4318"
      - "8888:8888"
      - "8889:8889"
    command: ["--config", "/etc/otelcol/config.yaml"]
```

### Pattern 3: Agent + Gateway (Production Standard)

Agents collect and batch locally; the gateway processes and exports. This is the recommended production pattern.

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│  App Node 1 │────▶│             │     │              │
└─────────────┘     │             │────▶│   Gateway    │────▶ Prometheus
┌─────────────┐     │   Agent     │     │   Collector  │────▶ Jaeger
│  App Node 2 │────▶│  Collector  │────▶│              │────▶ Loki
└─────────────┘     │             │     │              │────▶ ClickHouse
┌─────────────┐     └─────────────┘     └──────────────┘
│  App Node 3 │────▶
└─────────────┘
```

## Complete Configuration Examples

### Minimal Agent Configuration

This configuration collects host metrics, reads application logs, receives OTLP from local apps, and forwards everything to a gateway.

```yaml
# otel-agent-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

  hostmetrics:
    collection_interval: 10s
    scrapers:
      cpu: {}
      memory: {}
      disk: {}
      network: {}
      filesystem: {}
      load: {}

  filelog:
    include:
      - /var/log/syslog
      - /var/log/*.log
    start_at: end
    operators:
      - type: regex_parser
        regex: '^(?P<timestamp>\w+\s+\d+\s+\d+:\d+:\d+)\s+(?P<hostname>\S+)\s+(?P<service>\S+?)(?:\[(?P<pid>\d+)\])?:\s+(?P<body>.*)$'

processors:
  batch:
    send_batch_size: 8192
    timeout: 200ms

  memory_limiter:
    check_interval: 1s
    limit_mib: 512
    spike_limit_mib: 128

  resource:
    attributes:
      - key: deployment.environment
        value: production
        action: upsert
      - key: host.hostname
        from_attribute: host.name
        action: upsert

exporters:
  otlp:
    endpoint: otel-gateway:4317
    tls:
      insecure: true
    sending_queue:
      enabled: true
      num_consumers: 4
      queue_size: 10000
    retry_on_failure:
      enabled: true
      initial_interval: 5s
      max_interval: 30s
      max_elapsed_time: 300s

service:
  telemetry:
    logs:
      level: info
    metrics:
      address: 0.0.0.0:8888
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, resource, batch]
      exporters: [otlp]
    metrics:
      receivers: [otlp, hostmetrics]
      processors: [memory_limiter, resource, batch]
      exporters: [otlp]
    logs:
      receivers: [otlp, filelog]
      processors: [memory_limiter, resource, batch]
      exporters: [otlp]
```

### Full Gateway Configuration

The gateway receives from agents, applies advanced processing, and exports to multiple backends.

```yaml
# otel-gateway-config.yaml
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
        - job_name: 'otel-collector'
          scrape_interval: 10s
          static_configs:
            - targets: ['localhost:8888']
        - job_name: 'node-exporter'
          scrape_interval: 15s
          static_configs:
            - targets: ['node-exporter:9100']

processors:
  batch:
    send_batch_size: 8192
    timeout: 500ms

  memory_limiter:
    check_interval: 1s
    limit_mib: 2048
    spike_limit_mib: 512

  filter:
    traces:
      span:
        - 'attributes["http.route"] == "/healthz"'
        - 'attributes["http.route"] == "/ready"'
    metrics:
      metric:
        - 'name == "http.server.duration" and attributes["http.status_code"] == 200'

  attributes:
    actions:
      - key: "http.request.header.authorization"
        action: delete
      - key: "db.statement"
        action: hash
      - key: "net.peer.ip"
        action: delete

  probabilistic_sampler:
    sampling_percentage: 25
    hash_seed: 42

  transform:
    error_mode: ignore
    trace_statements:
      - context: span
        statements:
          - set(attributes["service.version"], resource.attributes["service.version"]) where attributes["service.version"] == nil
          - replace_pattern(attributes["http.url"], "\\?.*", "")
    log_statements:
      - context: log
        statements:
          - set(severity_text, "INFO") where severity_number < 9
          - set(severity_text, "ERROR") where severity_number >= 17

exporters:
  # Metrics to Prometheus via remote write
  prometheusremotewrite:
    endpoint: "http://prometheus:9090/api/v1/write"
    resource_to_telemetry_conversion:
      enabled: true

  # Traces to Jaeger
  jaeger:
    endpoint: jaeger:14250
    tls:
      insecure: true

  # Traces to Tempo (alternative)
  otlp/tempo:
    endpoint: tempo:4317
    tls:
      insecure: true

  # Logs to Loki
  loki:
    endpoint: "http://loki:3100/loki/api/v1/push"
    default_labels_enabled:
      job: true
      instance: true

  # All signals to ClickHouse for unified storage
  clickhouse:
    endpoint: "tcp://clickhouse:9000"
    database: otel
    ttl_days: 30
    timeout: 10s
    retry_on_failure:
      enabled: true
      initial_interval: 5s
      max_interval: 30s

  # Debug exporter for troubleshooting
  debug:
    verbosity: detailed
    sampling_initial: 5
    sampling_thereafter: 200

service:
  telemetry:
    logs:
      level: info
    metrics:
      address: 0.0.0.0:8889
      level: detailed
  pipelines:
    traces/primary:
      receivers: [otlp]
      processors: [memory_limiter, filter, attributes, probabilistic_sampler, transform, batch]
      exporters: [jaeger, clickhouse, debug]
    traces/tempo:
      receivers: [otlp]
      processors: [memory_limiter, filter, batch]
      exporters: [otlp/tempo]
    metrics:
      receivers: [otlp, prometheus]
      processors: [memory_limiter, batch]
      exporters: [prometheusremotewrite, clickhouse]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, transform, batch]
      exporters: [loki, clickhouse, debug]
```

## Full Infrastructure Deployment

Here is a complete docker-compose setup that runs the entire observability stack:

```yaml
# docker-compose.yml — Full observability stack
services:
  # === OpenTelemetry Gateway ===
  otel-gateway:
    image: otel/opentelemetry-collector-contrib:0.122.1
    container_name: otel-gateway
    restart: unless-stopped
    volumes:
      - ./otel-gateway-config.yaml:/etc/otelcol/config.yaml
    ports:
      - "4317:4317"
      - "4318:4318"
      - "8889:8889"
    command: ["--config", "/etc/otelcol/config.yaml"]
    depends_on:
      - jaeger
      - loki
      - clickhouse
    networks:
      - observability

  # === Prometheus ===
  prometheus:
    image: prom/prometheus:v3.2.1
    container_name: prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - prometheus-data:/prometheus
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.retention.time=30d"
      - "--web.enable-lifecycle"
      - "--enable-feature=remote-write-receiver"
    networks:
      - observability

  # === Jaeger ===
  jaeger:
    image: jaegertracing/all-in-one:1.64.0
    container_name: jaeger
    restart: unless-stopped
    environment:
      - COLLECTOR_OTLP_ENABLED=true
      - QUERY_BASE_PATH=/jaeger
    ports:
      - "16686:16686"
      - "14250:14250"
      - "14268:14268"
    volumes:
      - jaeger-data:/badger
    networks:
      - observability

  # === Grafana Loki ===
  loki:
    image: grafana/loki:3.4.2
    container_name: loki
    restart: unless-stopped
    ports:
      - "3100:3100"
    volumes:
      - loki-data:/loki
      - ./loki-config.yaml:/etc/loki/config.yaml
    command: ["-config.file=/etc/loki/config.yaml"]
    networks:
      - observability

  # === ClickHouse ===
  clickhouse:
    image: clickhouse/clickhouse-server:25.3
    container_name: clickhouse
    restart: unless-stopped
    ports:
      - "9000:9000"
      - "8123:8123"
    volumes:
      - clickhouse-data:/var/lib/clickhouse
      - ./otel-schema.sql:/docker-entrypoint-initdb.d/otel-schema.sql
    environment:
      - CLICKHOUSE_DB=otel
    networks:
      - observability

  # === Grafana (unified dashboard) ===
  grafana:
    image: grafana/grafana:11.5.2
    container_name: grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=changeme
      - GF_INSTALL_PLUGINS=grafana-clickhouse-datasource
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana-datasources.yaml:/etc/grafana/provisioning/datasources/datasources.yaml
    depends_on:
      - prometheus
      - jaeger
      - loki
      - clickhouse
    networks:
      - observability

volumes:
  prometheus-data:
  jaeger-data:
  loki-data:
  clickhouse-data:
  grafana-data:

networks:
  observability:
    driver: bridge
```

## Data Routing and Multi-Tenant Patterns

### Routing by Service

Route telemetry from different services to different backends:

```yaml
processors:
  routing:
    default_pipelines: [traces/clickhouse]
    table:
      - value: "payment-service"
        pipelines: [traces/jaeger, traces/clickhouse]
      - value: "frontend"
        pipelines: [traces/tempo, traces/clickhouse]
      - value: "internal-api"
        pipelines: [traces/clickhouse]

exporters:
  otlp/jaeger:
    endpoint: jaeger:14250
  otlp/tempo:
    endpoint: tempo:4317
  clickhouse:
    endpoint: tcp://clickhouse:9000

service:
  pipelines:
    traces/jaeger:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlp/jaeger]
    traces/tempo:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlp/tempo]
    traces/clickhouse:
      receivers: [otlp]
      processors: [batch]
      exporters: [clickhouse]
```

### Tail-Based Sampling

Keep only interesting traces — errors, slow requests, specific services:

```yaml
processors:
  tail_sampling:
    decision_wait: 10s
    num_traces: 100000
    expected_new_traces_per_sec: 1000
    policies:
      - name: keep-errors
        type: status_code
        status_code:
          status_codes: [ERROR]
      - name: keep-slow-traces
        type: latency
        latency:
          threshold_ms: 2000
      - name: keep-payment-service
        type: string_attribute
        string_attribute:
          key: service.name
          values: ["payment-service", "checkout-service"]
      - name: probabilistic-sample
        type: probabilistic
        probabilistic:
          sampling_percentage: 10
```

## Monitoring the Collector Itself

The Collector exposes its own metrics on a configurable endpoint. Monitor it to ensure your pipeline is healthy:

```yaml
service:
  telemetry:
    metrics:
      address: 0.0.0.0:8888
      level: detailed
    logs:
      level: info

  extensions: [health_check, pprof, zpages]

extensions:
  health_check:
    endpoint: 0.0.0.0:13133
  pprof:
    endpoint: 0.0.0.0:1777
  zpages:
    endpoint: 0.0.0.0:55679
```

Key metrics to alert on:

| Metric | Alert Condition | Meaning |
|--------|----------------|---------|
| `otelcol_receiver_accepted_spans` | Rate drop > 50% | Data ingestion stopped |
| `otelcol_exporter_send_failed_spans` | Rate > 0 | Backend unreachable |
| `otelcol_processor_batch_batch_send_size` | Distribution shift | Batch size changed |
| `otelcol_process_memory_rss` | > 80% of limit | Memory pressure |
| `otelcol_process_cpu_seconds` | Spike | Processing bottleneck |

## Performance Tuning

For production workloads, tune these parameters:

```yaml
processors:
  batch:
    # Tune based on your throughput and latency requirements
    send_batch_size: 8192        # Larger = fewer exports, higher latency
    send_batch_max_size: 16384   # Hard cap to prevent memory spikes
    timeout: 200ms               # Flush interval even if batch not full

  memory_limiter:
    check_interval: 1s
    limit_mib: 4096              # Set to ~80% of available container memory
    spike_limit_mib: 1024        # Reserve headroom for burst handling

exporters:
  otlp:
    sending_queue:
      enabled: true
      num_consumers: 8           # Parallel export workers
      queue_size: 50000          # Buffer size in telemetry items
      storage: file_storage      # Persistent queue survives restarts
    retry_on_failure:
      enabled: true
      initial_interval: 5s
      max_interval: 30s
      max_elapsed_time: 300s
```

For high-throughput environments (>100k spans/sec), consider:

- Running multiple gateway instances behind a load balancer
- Using the `loadbalancing` exporter to distribute traces across multiple backend instances
- Enabling the `file_storage` extension for persistent queue disk overflow
- Setting `GOMAXPROCS` to match container CPU limits

## Security Best Practices

Self-hosting the Collector means securing the pipeline yourself:

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
        tls:
          cert_file: /etc/otelcol/certs/server.crt
          key_file: /etc/otelcol/certs/server.key
          client_ca_file: /etc/otelcol/certs/ca.crt
      http:
        endpoint: 0.0.0.0:4318
        tls:
          cert_file: /etc/otelcol/certs/server.crt
          key_file: /etc/otelcol/certs/server.key

exporters:
  otlp:
    endpoint: backend:4317
    tls:
      cert_file: /etc/otelcol/certs/client.crt
      key_file: /etc/otelcol/certs/client.key
      ca_file: /etc/otelcol/certs/ca.crt
```

- Always enable TLS for inter-Collector and Collector-to-backend communication
- Use mutual TLS (mTLS) for production deployments
- Rotate certificates using cert-manager in Kubernetes
- Never use `insecure: true` in production
- Set `limit_mib` to prevent denial-of-service through memory exhaustion
- Use the `filter` processor to drop telemetry from untrusted sources

## Migration Path from Existing Tools

### From Fluentd/Fluent Bit

```yaml
# Replace fluentd forwarding with OTel
receivers:
  fluentforward:
    endpoint: 0.0.0.0:24224

  filelog:
    include:
      - /var/log/containers/*.log

processors:
  transform:
    log_statements:
      - context: log
        statements:
          # Replicate fluentd record_transformer behavior
          - set(attributes["kubernetes.pod_name"], resource.attributes["k8s.pod.name"])
          - set(attributes["docker.container_id"], resource.attributes["container.id"])

exporters:
  loki:
    endpoint: "http://loki:3100/loki/api/v1/push"
```

### From StatsD

```yaml
receivers:
  statsd:
    endpoint: 0.0.0.0:8125
    aggregation_interval: 10s

processors:
  # Convert StatsD types to OTel metric types automatically

exporters:
  prometheusremotewrite:
    endpoint: "http://prometheus:9090/api/v1/write"
```

## Getting Started Checklist

1. **Install the Collector** — Use the official Docker image (`otel/opentelemetry-collector-contrib`) for the broadest receiver/exporter support. The core distribution is lighter but lacks many community plugins.

2. **Start with a simple pipeline** — One receiver (`otlp`), two processors (`memory_limiter`, `batch`), one exporter (`debug`). Verify telemetry flows end-to-end.

3. **Add your backend** — Replace the `debug` exporter with your actual backend (Jaeger, Prometheus, Loki, ClickHouse).

4. **Deploy as agent + gateway** — Run agents on every host, forward to a centralized gateway.

5. **Add processing** — Layer in filtering, sampling, and attribute reduction once the pipeline is stable.

6. **Monitor the Collector** — Set up alerts on the Collector's own metrics. If the pipeline breaks, your monitoring goes blind.

7. **Test failover** — Kill your backend and verify the persistent queue buffers data. Restart the backend and confirm replay.

The OpenTelemetry Collector is the most flexible building block in the modern observability stack. By self-hosting it, you gain complete control over your telemetry pipeline — from ingestion to export — without locking into any single vendor's ecosystem.
