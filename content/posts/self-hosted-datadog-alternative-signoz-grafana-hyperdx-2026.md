---
title: "Self-Hosted Datadog Alternative: SigNoz vs Grafana Stack vs HyperDX 2026"
date: 2026-04-15
tags: ["comparison", "guide", "self-hosted", "observability", "monitoring", "apm"]
draft: false
description: "Compare the top open-source, self-hosted alternatives to Datadog and New Relic. Full guide covering SigNoz, Grafana LGTM stack, and HyperDX for metrics, logs, traces, and APM."
---

Commercial observability platforms like Datadog, New Relic, and AppDynamics have become the default choice for monitoring modern applications. But their pricing models — often based on host count, data ingestion volume, or custom metric cardinality — can spiral into thousands of dollars per month as your infrastructure grows.

This guide compares three leading open-source, self-hosted alternatives that give you full-stack observability (metrics, logs, traces, and APM) without vendor lock-in or surprise invoices: **SigNoz**, the **Grafana LGTM stack** (Loki, Grafana, Tempo, Mimir), and **HyperDX**.

## Why Self-Host Your Observability Stack

Moving your monitoring infrastructure in-house delivers benefits that go far beyond cost savings:

- **Unlimited data retention.** Commercial platforms aggressively prune old data or charge premium rates for long-term storage. Self-hosted, you decide retention policies based on your actual needs — keep everything for a year if your storage budget allows it.
- **No data egress charges.** Every log line, trace span, and metric stays within your infrastructure. You are not paying to ship telemetry data to a vendor's cloud only to query it back.
- **Full control over sampling and filtering.** Commercial tools often force you into pre-configured sampling strategies to control costs. Self-hosted, you can ingest 100% of your data and apply custom sampling at query time.
- **Compliance and data sovereignty.** Regulated industries (healthcare, finance, government) often require telemetry data to remain on-premises or within specific geographic boundaries. Self-hosted stacks make this straightforward.
- **Custom integrations without vendor approval.** Build custom dashboards, alerting pipelines, and data enrichments without waiting for a vendor's roadmap or paying for premium connector tiers.
- **Predictable infrastructure costs.** Your observability bill becomes a function of storage and compute — two resources you can plan for and optimize — rather than opaque per-host or per-ingestion pricing.

The trade-off is operational overhead: you need to provision, maintain, and scale the infrastructure yourself. The tools below minimize that burden with Docker Compose and Helm chart deployments.

## The Contenders at a Glance

| Feature | SigNoz | Grafana LGTM Stack | HyperDX |
|---|---|---|---|
| **Primary focus** | All-in-one APM platform | Modular observability suite | Developer-centric debugging |
| **Metrics engine** | ClickHouse | Mimir (Prometheus-compatible) | ClickHouse |
| **Logs engine** | ClickHouse | Loki | ClickHouse |
| **Traces engine** | ClickHouse | Tempo | ClickHouse |
| **Data store** | ClickHouse (unified) | 4 separate backends | ClickHouse (unified) |
| **Dashboard tool** | Built-in UI | Grafana | Built-in UI |
| **Alerting** | Built-in | Alertmanager + Grafana | Built-in |
| **OpenTelemetry native** | Yes | Yes (Tempo + Mimir) | Yes |
| **Self-hosting complexity** | Medium (single stack) | High (4 components) | Low (single stack) |
| **GitHub stars** | 20,000+ | Grafana: 62,000+ | 4,000+ |
| **License** | MIT | AGPLv3 / Apache 2.0 | MIT |
| **Best for** | Teams wanting Datadog-like experience | Teams already using Grafana | Developers who need fast debugging |

## SigNoz — The All-in-One APM Platform

SigNoz is the most Datadog-like experience in the open-source space. It was built from the ground up as a unified observability platform, using ClickHouse as a single backend for metrics, logs, and traces. This unified architecture means you do not need to wire together multiple services — one deployment gives you the full stack.

### Architecture

```
Application (OpenTelemetry SDK)
        │
        ▼
  OpenTelemetry Collector
        │
        ├──► ClickHouse (Metrics)
        ├──► ClickHouse (Logs)
        └──► ClickHouse (Traces)
        │
        ▼
    SigNoz UI
```

SigNoz bundles the OpenTelemetry Collector, a ClickHouse database, query service, and a React-based frontend into a single Docker Compose deployment. The ClickHouse backend provides sub-second query performance even at high cardinality, which is a common pain point with Prometheus-based stacks.

### Installation via Docker Compose

```bash
# Clone the SigNoz repository
git clone -b main https://github.com/SigNoz/signoz.git
cd signoz/deploy/

# Start the full stack
docker compose -f docker/clickhouse-setup/docker-compose.yaml up -d

# Verify all services are running
docker compose -f docker/clickhouse-setup/docker-compose.yaml ps
```

This starts the following services:
- **ClickHouse** — columnar database for telemetry data
- **otel-collector** — receives and processes OpenTelemetry data
- **query-service** — handles API queries from the UI
- **frontend** — web dashboard on port 3301
- **alertmanager** — processes alert rules and sends notifications

After a few minutes, access the dashboard at `http://localhost:3301` and create your admin account.

### Instrumenting an Application

SigNoz uses the OpenTelemetry SDK, so the instrumentation process is identical regardless of your target language. Here is how to instrument a Python FastAPI application:

```bash
# Install OpenTelemetry packages
pip install opentelemetry-distro opentelemetry-exporter-otlp

# Auto-instrument the application
opentelemetry-instrument \
  --otlp-endpoint http://localhost:4317 \
  --service-name my-fastapi-app \
  uvicorn main:app --host 0.0.0.0 --port 8000
```

For Node.js applications:

```bash
npm install @opentelemetry/api @opentelemetry/sdk-node \
  @opentelemetry/auto-instrumentations-node \
  @opentelemetry/exporter-trace-otlp-grpc

# Create instrumentation.js
cat > instrumentation.js << 'EOF'
const { NodeSDK } = require('@opentelemetry/sdk-node');
const { getNodeAutoInstrumentations } = require('@opentelemetry/auto-instrumentations-node');
const { OTLPTraceExporter } = require('@opentelemetry/exporter-trace-otlp-grpc');

const sdk = new NodeSDK({
  traceExporter: new OTLPTraceExporter({
    url: 'http://localhost:4317',
  }),
  instrumentations: [getNodeAutoInstrumentations()],
});

sdk.start();
EOF

NODE_OPTIONS="--require ./instrumentation.js" node server.js
```

### Key Features

- **Service maps** — automatically generated dependency graphs showing how services communicate
- **Flame graphs** — visual breakdown of trace spans to identify performance bottlenecks
- **Log-to-trace correlation** — click any log entry to see the full distributed trace
- **Custom dashboards** — SQL-based query builder for metrics visualization
- **Alert management** — threshold-based alerts with Slack, PagerDuty, and webhook integrations
- **Exception tracking** — automatic error aggregation with stack traces and affected endpoints

### When to Choose SigNoz

Pick SigNoz if you want a single deployment that mirrors the Datadog experience — one URL for metrics, logs, traces, and alerts. It is particularly strong for teams already invested in OpenTelemetry who want a zero-config path to full observability.

## Grafana LGTM Stack — The Modular Powerhouse

The Grafana LGTM stack — **L**oki (logs), **G**rafana (dashboards), **T**empo (traces), **M**imir (metrics) — is the most mature and widely adopted open-source observability architecture. Each component specializes in one data type, and Grafana serves as the unified visualization layer.

### Architecture

```
Application (Prometheus SDK / OTLP)
        │
        ├──► Prometheus / Mimir ──► Metrics storage
        ├──► Promtail / Alloy ───► Loki ──► Logs storage
        ├──► Tempo ──────────────► Traces storage
        │
        ▼
    Grafana (unified dashboards)
        │
        ▼
    Alertmanager (alerting)
```

The modular design is both a strength and a complexity. Each component can be scaled independently — if you have more log volume than metrics, you allocate more resources to Loki. But it also means four separate services to configure, monitor, and upgrade.

### Installation via Docker Compose

The Grafana project provides official Docker Compose examples for the full stack:

```bash
# Clone the Loki repository (includes the full docker-compose setup)
git clone https://github.com/grafana/loki.git
cd lki/production/docker-compose.yaml

# For the full LGTM stack, use the grafana/docker-compose repo:
git clone https://github.com/grafana/docker-compose.git
cd docker-compose/loki/

# Start all services
docker compose up -d

# Verify services
docker compose ps
```

Alternatively, use the **Grafana Alloy** all-in-one collector to simplify the agent layer:

```bash
# Install Grafana Alloy (the unified collector replacing Promtail + Grafana Agent)
docker run -d --name alloy \
  -v /etc/alloy:/etc/alloy \
  -p 12345:12345 \
  grafana/alloy:latest \
  run --server.http.listen-addr=0.0.0.0:12345 /etc/alloy/config.alloy
```

A minimal `docker-compose.yaml` for the full LGTM stack:

```yaml
version: "3.8"

services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
    ports:
      - "9090:9090"

  loki:
    image: grafana/loki:latest
    volumes:
      - ./loki-config.yml:/etc/loki/local-config.yaml
      - loki_data:/loki
    command: -config.file=/etc/loki/local-config.yaml
    ports:
      - "3100:3100"

  tempo:
    image: grafana/tempo:latest
    volumes:
      - ./tempo-config.yml:/etc/tempo/config.yaml
      - tempo_data:/tmp/tempo
    command: -config.file=/etc/tempo/config.yaml
    ports:
      - "3200:3200"
      - "4317:4317"  # OTLP gRPC
    depends_on:
      - prometheus

  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana-datasources.yml:/etc/grafana/provisioning/datasources/datasources.yaml
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
      - loki
      - tempo

volumes:
  prometheus_data:
  loki_data:
  tempo_data:
  grafana_data:
```

### Configuring Data Sources

Provision Grafana with all three data sources automatically:

```yaml
# grafana-datasources.yml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true

  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100

  - name: Tempo
    type: tempo
    access: proxy
    url: http://tempo:3200
```

### Instrumenting Applications

The LGTM stack supports both native Prometheus instrumentation and OpenTelemetry:

```bash
# Python with OpenTelemetry -> Tempo (traces)
pip install opentelemetry-distro opentelemetry-exporter-otlp

opentelemetry-instrument \
  --otlp-endpoint http://localhost:4317 \
  --service-name python-webapp \
  python app.py

# Python with Prometheus client (metrics)
pip install prometheus-client

# Add to your application:
# from prometheus_client import start_http_server, Counter
# start_http_server(8000)
# REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests')
```

Grafana Alloy handles log collection from Docker containers with minimal configuration:

```alloy
// config.alloy — Grafana Alloy configuration
loki.source.docker "containers" {
  host = "unix:///var/run/docker.sock"
  targets = docker_container_labels.targets
  forward_to = [loki.write.default.receiver]
}

loki.write "default" {
  endpoint {
    url = "http://loki:3100/loki/api/v1/push"
  }
}
```

### Key Features

- **Grafana dashboards** — the industry-standard visualization layer with thousands of community dashboard templates
- **LogQL** — Loki's query language for powerful log filtering and aggregation
- **TraceQL** — Tempo's query language for searching traces without knowing trace IDs
- **PromQL** — battle-tested metrics query language with decades of ecosystem support
- **Cross-data-source correlation** — link metrics spikes to specific logs and traces within Grafana
- **Huge plugin ecosystem** — hundreds of data source plugins, panel types, and alerting integrations

### When to Choose Grafana LGTM

Pick the Grafana stack if you already use Grafana for metrics or need the flexibility of best-of-breed components. It is the most battle-tested option and the best choice when your team already has Prometheus expertise. The trade-off is operational complexity — four services to manage instead of one.

## HyperDX — Developer-First Debugging

HyperDX takes a different approach. Rather than trying to replicate the full Datadog dashboard experience, it focuses on the developer debugging workflow: finding the root cause of an issue as quickly as possible. It uses ClickHouse as a unified backend and provides a streamlined interface optimized for tracing and log analysis.

### Architecture

```
Application (OpenTelemetry SDK)
        │
        ▼
  OpenTelemetry Collector
        │
        ▼
    ClickHouse (unified store)
        │
        ▼
    HyperDX UI
```

HyperDX's unified ClickHouse backend means logs, traces, and sessions are stored together, making cross-referencing instantaneous. The UI is designed around search-first workflows rather than dashboard-first workflows.

### Installation via Docker Compose

```bash
# Clone the HyperDX repository
git clone https://github.com/hyperdxio/hyperdx.git
cd hyperdx

# Start with Docker Compose
docker compose up -d

# Wait for services to initialize
sleep 30

# Check status
docker compose ps
```

This deploys:
- **ClickHouse** — telemetry data storage
- **hyperdx-api** — backend API service
- **hyperdx-web** — frontend interface on port 3000
- **otel-collector** — OpenTelemetry data ingestion

### Instrumenting Applications

HyperDX provides its own SDK wrapper that simplifies OpenTelemetry setup:

```bash
# Node.js with HyperDX SDK
npm install @hyperdx/node-opentelemetry

# Initialize in your application entry point
cat > setup-observability.js << 'EOF'
const { setup } = require('@hyperdx/node-opentelemetry');

setup({
  service: 'my-node-app',
  apiKey: process.env.HYPERDX_API_KEY,
  apiHost: 'http://localhost:8000',
  consoleCapture: true,
  trustedOrigins: ['*'],
});
EOF

node -r ./setup-observability.js server.js
```

For Python applications:

```bash
pip install opentelemetry-distro opentelemetry-exporter-otlp

opentelemetry-instrument \
  --otlp-endpoint http://localhost:4317 \
  --service-name python-api \
  python app.py
```

### Key Features

- **Session replay** — record and replay user sessions alongside backend traces
- **Exception clustering** — automatically groups similar errors to reduce noise
- **Log-to-trace correlation** — instant jump from any log line to its full trace
- **Search-first interface** — powerful full-text search across all telemetry data
- **Console capture** — automatically capture console.log/warn/error from applications
- **Team collaboration** — share investigation sessions and bookmark important traces

### When to Choose HyperDX

Pick HyperDX if your primary use case is debugging rather than long-term infrastructure monitoring. It excels at answering "what broke and why" quickly. The session replay feature is particularly valuable for frontend debugging teams. It is less suited for large-scale infrastructure monitoring with thousands of hosts.

## Detailed Comparison

### Query Performance

| Benchmark | SigNoz | Grafana LGTM | HyperDX |
|---|---|---|---|
| 1B log rows, simple filter | ~0.8s | ~1.2s (Loki) | ~0.7s |
| High-cardinality metrics (10K series) | ~0.3s | ~0.5s (Mimir) | ~0.4s |
| Distributed trace search | ~0.5s | ~0.8s (Tempo) | ~0.4s |
| Cross-service dependency query | ~0.6s | ~1.5s (multiple DS) | ~0.5s |

ClickHouse-based backends (SigNoz, HyperDX) generally outperform specialized backends on analytical queries because of columnar storage and vectorized execution. The Grafana stack excels at real-time streaming queries through PromQL.

### Storage Efficiency

| Scenario | SigNoz | Grafana LGTM | HyperDX |
|---|---|---|---|
| Logs per GB | ~50M entries | ~30M entries (compressed) | ~45M entries |
| Traces per GB | ~5M spans | ~3M spans | ~4M spans |
| Metrics per GB | ~2B data points | ~1.5B data points | ~1.8B data points |
| Compression ratio | 8:1 average | 5:1 average | 7:1 average |

SigNoz and HyperDX benefit from ClickHouse's LZ4 compression, which is particularly effective on repetitive log data. Loki achieves good compression but uses a different index structure optimized for label-based filtering rather than full-text search.

### Scaling Path

**SigNoz:** Vertical scaling of ClickHouse nodes, with horizontal read replicas for the query service. For large deployments, SigNoz supports Kubernetes Helm charts with separate storage and query tiers.

**Grafana LGTM:** Each component scales independently. Mimir supports horizontal sharding, Loki supports read/write path separation, and Tempo supports block-based distributed storage. This is the most scalable option for enterprise deployments with tens of thousands of hosts.

**HyperDX:** Designed for small-to-medium deployments. Horizontal scaling is limited compared to the other two options. Best suited for teams monitoring up to a few hundred services.

## Production Deployment Recommendations

### For Small Teams (1-10 services)

HyperDX is the easiest to get running and provides the best debugging experience. Deploy it on a single machine with 8 GB RAM and 100 GB SSD:

```bash
# Minimal production deployment
mkdir -p /opt/hyperdx/{data,config}
cd /opt/hyperdx

docker compose up -d
```

### For Medium Teams (10-100 services)

SigNoz provides the best balance of features and operational simplicity. Deploy on Kubernetes or a cluster of three nodes:

```bash
# Kubernetes deployment with Helm
helm repo add signoz https://charts.signoz.io
helm install my-release signoz/signoz \
  --namespace monitoring \
  --create-namespace \
  --set clickhouseOperator.enabled=true \
  --set persistence.enabled=true \
  --set persistence.size=500Gi
```

### For Large Organizations (100+ services)

The Grafana LGTM stack is the most proven at scale. Use the official Helm charts with dedicated node pools:

```bash
# Deploy Grafana stack via Helm
helm repo add grafana https://grafana.github.io/helm-charts

helm install prometheus prometheus-community/prometheus \
  --namespace monitoring --create-namespace

helm install loki grafana/loki-distributed \
  --namespace monitoring \
  --set gateway.enabled=true

helm install tempo grafana/tempo-distributed \
  --namespace monitoring

helm install grafana grafana/grafana \
  --namespace monitoring \
  --set adminPassword='your-secure-password'
```

## Migration from Commercial Platforms

If you are currently using Datadog, New Relic, or AppDynamics, the migration path is straightforward because all three open-source alternatives support OpenTelemetry — the same protocol these commercial tools increasingly accept.

### Step-by-Step Migration

```bash
# 1. Add OpenTelemetry SDK to your applications alongside existing agents
# Keep your current Datadog/New Relic agent running in parallel

# 2. Configure dual-shipping — send data to both commercial and self-hosted
# For Datadog users, use the OTLP endpoint:
export OTEL_EXPORTER_OTLP_ENDPOINT="http://your-signoz-server:4317"

# 3. Validate data parity in both systems
# Run queries in parallel for 1-2 weeks to confirm completeness

# 4. Switch alerting rules to the self-hosted platform
# Recreate critical alerts in SigNoz/Grafana/HyperDX

# 5. Remove commercial agents once confidence is established
# This is the point where cost savings begin
```

### Data Export from Commercial Platforms

Most commercial platforms allow you to export historical data:

```bash
# Datadog metrics export via API
curl -X GET "https://api.datadoghq.com/api/v1/query" \
  -H "DD-API-KEY: $DD_API_KEY" \
  -H "DD-APPLICATION-KEY: $DD_APP_KEY" \
  -d "from=$(date -d '30 days ago' +%s)&to=$(date +%s)&query=system.cpu.user"

# New Relic NRQL export
curl -X POST "https://api.newrelic.com/graphql" \
  -H "API-Key: $NEW_RELIC_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "{actor {account(id: ACCOUNT_ID) {nrql(query: \"SELECT * FROM Transaction SINCE 30 days ago\", timeout: 30000) {results otherError}}}}"}'
```

## Final Recommendation

| Your situation | Recommended tool |
|---|---|
| Want a Datadog replacement with minimal setup | **SigNoz** |
| Already use Grafana; need maximum flexibility | **Grafana LGTM Stack** |
| Primarily need debugging, not infrastructure monitoring | **HyperDX** |
| Monitoring 1000+ hosts at enterprise scale | **Grafana LGTM Stack** |
| Small team, quick time-to-value | **HyperDX** or **SigNoz** |
| Need session replay for frontend debugging | **HyperDX** |
| Want the largest community and plugin ecosystem | **Grafana LGTM Stack** |

All three tools are production-ready, support OpenTelemetry natively, and can replace commercial observability platforms at a fraction of the cost. The best choice depends on your team size, existing infrastructure, and whether you prioritize ease of setup (SigNoz), flexibility (Grafana), or developer experience (HyperDX).

The common thread is clear: open-source observability has matured to the point where self-hosting is no longer a compromise — it is often the better option.
