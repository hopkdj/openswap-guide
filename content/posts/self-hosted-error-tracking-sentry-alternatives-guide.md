---
title: "Self-Hosted Error Tracking: Best Sentry Alternatives 2026"
date: 2026-04-15
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Compare HyperDX, SigNoz, and GlitchTip as self-hosted Sentry alternatives. Full installation guides, feature comparisons, and pricing breakdowns for complete error tracking ownership in 2026."
---

Error tracking is one of the most critical pieces of infrastructure for any software team. When production breaks, you need to know exactly what happened, where, and why — within seconds, not hours. For years, [Sentry](https://sentry.io) has been the dominant player in this space. But its cloud-only pricing model, data residency concerns, and aggressive event throttling on free tiers have pushed many teams to look for self-hosted alternatives.

In 2026, the self-hosted error tracking landscape has matured significantly. You no longer need to compromise between powerful debugging features and data sovereignty. This guide covers three of the best self-hosted error tracking and observability platforms — **HyperDX**, **SigNoz**, and **GlitchTip** — with complete installation guides, feature comparisons, and real-world deployment advice.

## Why Self-Host Your Error Tracking

The arguments for self-hosting error tracking are stronger in 2026 than ever:

### Complete Data Ownership
Error logs contain stack traces, IP addresses, user session data, and sometimes Personally Identifiable Information (PII) — request bodies, cookies, headers. When you use a cloud provider, that data lives on their servers, subject to their retention policies and potential data breaches. Self-hosting means the data never leaves your infrastructure.

### No Event Throttling
Cloud error trackers notoriously drop events when you exceed your plan's quota. A traffic spike during an incident — exactly when you need the most visibility — is precisely when cloud providers start discarding your data. Self-hosted platforms let you capture every single error without artificial caps.

### Cost Predictability at Scale
Sentry's pricing is based on event volume. For high-traffic applications, this can easily reach thousands of dollars per month. Self-hosted alternatives typically cost a fraction of that — your only expense is the infrastructure to run them.

### Regulatory Compliance
GDPR, HIPAA, SOC 2, and other compliance frameworks often require strict control over where data is stored and who can access it. Self-hosting eliminates the third-party risk and makes compliance audits straightforward.

### Deep Integration with Existing Stack
When you control the entire stack, you can integrate error tracking with your internal tools — Slack channels, PagerDuty, custom dashboards, internal wikis — without waiting for official integrations or dealing with webhook rate limits.

## HyperDX: Full-Stack Observability Platform

HyperDX positions itself as an open-source observability platform that unifies logs, metrics, traces, and error tracking in a single interface. Rather than being a pure error tracker, it provides comprehensive visibility into application behavior, with error correlation as a core feature.

### Key Features

- **Unified observability** — logs, metrics, traces, and errors in one place
- **Session replay** — replay user sessions to reproduce bugs
- **Automatic error grouping** — smart fingerprinting to deduplicate errors
- **OpenTelemetry native** — uses OTLP protocol, works with any OTel-compatible SDK
- **Full-text search** — search across all logs and errors with Lucene syntax
- **Alerting** — configure alerts based on error rate, latency, or custom queries

### Architecture

HyperDX is built on ClickHouse for storage, providing fast aggregation and search over large volumes of data. The architecture consists of three main components:

1. **API Server** — handles incoming OTLP data and serves the web interface
2. **ClickHouse** — columnar storage engine for logs and traces
3. **Web UI** — React-based dashboard for querying and analysis

### [docker](https://www.docker.com/) Installation

Create a `docker-compose.yml` file:

```yaml
version: "3.8"

services:
  clickhouse:
    image: clickhouse/clickhouse-server:24.3
    container_name: hyperdx-clickhouse
    environment:
      CLICKHOUSE_DB: default
      CLICKHOUSE_USER: default
      CLICKHOUSE_PASSWORD: ""
    volumes:
      - clickhouse_data:/var/lib/clickhouse
      - ./clickhouse-config.xml:/etc/clickhouse-server/config.d/custom.xml
    ports:
      - "9000:9000"
      - "8123:8123"
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:8123/ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  hyperdx:
    image: ghcr.io/hyperdxio/hyperdx:latest
    container_name: hyperdx-api
    depends_on:
      clickhouse:
        condition: service_healthy
    environment:
      CLICKHOUSE_HOST: clickhouse
      CLICKHOUSE_PORT: 9000
      PORT: 8080
      HYPERDX_SECRET_KEY: "your-secret-key-here-change-this"
    ports:
      - "8080:8080"
    volumes:
      - hyperdx_data:/var/lib/hyperdx
    restart: unless-stopped

volumes:
  clickhouse_data:
  hyperdx_data:
```

Start the stack:

```bash
docker compose up -d
```

Wait about 30 seconds for ClickHouse to initialize, then open `http://localhost:8080` in your browser.

### SDK Integration

HyperDX uses the OpenTelemetry SDK. For a Node.js application:

```bash
npm install @opentelemetry/api @opentelemetry/sdk-node @opentelemetry/auto-instrumentations-node
```

```javascript
const { NodeSDK } = require("@opentelemetry/sdk-node");
const { getNodeAutoInstrumentations } = require("@opentelemetry/auto-instrumentations-node");
const { OTLPTraceExporter } = require("@opentelemetry/exporter-trace-otlp-http");

const sdk = new NodeSDK({
  traceExporter: new OTLPTraceExporter({
    url: "http://localhost:8080/v1/traces",
  }),
  instrumentations: [getNodeAutoInstrumentations()],
});

sdk.start();

// Errors are automatically captured and correlated with traces
process.on("uncaughtException", (err) => {
  console.error("Uncaught exception:", err);
});
```

For Python applications:

```bash
pip install opentelemetry-distro opentelemetry-exporter-otlp-proto-http
opentelemetry-bootstrap -a install
```

```bash
# Run with auto-instrumentation
OTEL_SERVICE_NAME=my-app \
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:8080 \
opentelemetry-instrument python app.py
```

### Best Use Cases

HyperDX excels when you need more than just error tracking. If your team wants unified observability — combining error monitoring with log management and distributed tracing — HyperDX provides the best value. The session replay feature is particularly valuable for frontend debugging.

## SigNoz: Open-Source APM and Error Tracking

SigNoz is an open-source Application Performance Monitoring (APM) tool that was built as a direct alternative to Datadog and New Relic. It includes robust error tracking as part of its broader observability suite, making it suitable for teams that want a comprehensive replacement for multiple SaaS tools.

### Key Features

- **APM with distributed tracing** — trace requests across microservices
- **Error tracking and alerting** — automatic exception capture with grouping
- **Metrics and dashboards** — built-in dashboard builder with pre-built templates
- **Log management** — centralized log aggregation with query builder
- **Service maps** — visualize service dependencies and bottlenecks
- **Custom alerts** — alert on error rates, p99 latency, and custom metrics
- **Multi-tenancy** — support for multiple teams and projects

### Architecture

SigNoz uses a modern, scalable architecture:

1. **OpenTelemetry Collector** — receives data via OTLP from instrumented applications
2. **ClickHouse** — primary storage for logs, traces, and metrics
3. **SigNoz Query Service** — processes queries and aggregates data
4. **Frontend** — React-based UI with customizable dashboards

### Docker Installation

SigNoz provides an official installation script, but here's a manual Docker Compose setup:

```yaml
version: "3"

services:
  signoz-otel-collector:
    image: signoz/signoz-otel-collector:0.110.0
    container_name: signoz-otel-collector
    command:
      - "--config=/etc/otel-collector-config.yaml"
    volumes:
      - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml
    ports:
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP
    depends_on:
      clickhouse:
        condition: service_healthy

  clickhouse:
    image: clickhouse/clickhouse-server:24.1.2-alpine
    container_name: signoz-clickhouse
    environment:
      CLICKHOUSE_DB: signoz_metrics
    volumes:
      - signoz_clickhouse:/var/lib/clickhouse/
      - ./clickhouse-config.xml:/etc/clickhouse-server/config.d/custom.xml
    ports:
      - "9000:9000"
      - "8123:8123"
      - "9009:9009"
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:8123/ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  signoz-query-service:
    image: signoz/query-service:0.61.0
    container_name: signoz-query-service
    depends_on:
      clickhouse:
        condition: service_healthy
    environment:
      ClickHouseUrl: tcp://clickhouse:9000
      DASHBOARDS_PATH: /etc/signoz/dashboards
    volumes:
      - signoz_data:/var/lib/signoz/
    ports:
      - "8080:8080"

volumes:
  signoz_clickhouse:
  signoz_data:
```

Create the OTel collector config (`otel-collector-config.yaml`):

```yaml
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
  clickhouse:
    dsn: tcp://clickhouse:9000
    database: signoz_traces
    low_cardinal_exception_grouping: true

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [clickhouse]
    logs:
      receivers: [otlp]
      processors: [batch]
      exporters: [clickhouse]
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [clickhouse]
```

Start the stack:

```bash
docker compose up -d
```

Access the UI at `http://localhost:8080`. The default credentials are typically set on first launch.

### Quick Install Alternative

SigNoz also provides a one-liner install script:

```bash
git clone -b main https://github.com/SigNoz/signoz.git && cd signoz/deploy/
./inst[kubernetes](https://kubernetes.io/)

This sets up a Kubernetes-based deployment with Helm charts, suitable for production environments.

### SDK Integration

For a Go application:

```bash
go get go.opentelemetry.io/otel \
       go.opentelemetry.io/otel/sdk \
       go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc
```

```go
package main

import (
    "context"
    "log"
    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
    "go.opentelemetry.io/otel/sdk/resource"
    sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

func main() {
    ctx := context.Background()

    exporter, err := otlptracegrpc.New(ctx,
        otlptracegrpc.WithInsecure(),
        otlptracegrpc.WithEndpoint("localhost:4317"),
    )
    if err != nil {
        log.Fatalf("Failed to create exporter: %v", err)
    }

    tp := sdktrace.NewTracerProvider(
        sdktrace.WithBatcher(exporter),
        sdktrace.WithResource(resource.NewWithAttributes(
            "service.name", "my-service",
        )),
    )
    defer tp.Shutdown(ctx)
    otel.SetTracerProvider(tp)

    // Your application code — errors are captured automatically
    // when using instrumented frameworks like Gin, Echo, or net/http
}
```

### Best Use Cases

SigNoz is the right choice when you need to replace multiple SaaS observability tools at once. If you're currently paying for Datadog, New Relic, or a combination of error tracking + APM + log management tools, SigNoz can consolidate them into a single self-hosted platform. Its service maps and distributed tracing are particularly strong for microservice architectures.

## GlitchTip: Lightweight Sentry-Compatible Error Tracking

GlitchTip takes a different approach. Rather than building a comprehensive observability platform, it focuses exclusively on error tracking and is designed to be a lightweight, drop-in replacement for Sentry. It uses Sentry's own SDK and API protocol, meaning you can point existing Sentry integrations at GlitchTip with minimal changes.

### Key Features

- **Sentry-compatible** — uses the same SDK and API, zero code changes needed
- **Lightweight** — minimal resource requirements, runs on a small VPS
- **Project management** — organize errors by project, team, and environment
- **Email and webhook alerts** — notify on new or regressed errors
- **Source maps** — deobfuscate JavaScript errors automatically
- **Release tracking** — correlate errors with specific deployments
- **User feedback** — collect error reports directly from end users
- **Simple UI** — clean, focused interface without feature bloat

### Architecture

GlitchTip is a Django application with a PostgreSQL database and Redis for caching. Its simplicity is its biggest advantage:

1. **Django Web App** — serves the UI and API
2. **PostgreSQL** — relational database for error data and project metadata
3. **Redis** — caching and task queue for email notifications
4. **Celery Workers** — process incoming events and send alerts

### Docker Installation

GlitchTip provides an official Docker Compose file. Here's a production-ready configuration:

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:16-alpine
    container_name: glitchtip-postgres
    environment:
      POSTGRES_USER: glitchtip
      POSTGRES_PASSWORD: "secure-db-password-change-this"
      POSTGRES_DB: glitchtip
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U glitchtip"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: glitchtip-redis
    command: redis-server --requirepass "secure-redis-password"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "secure-redis-password", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  web:
    image: glitchtip/glitchtip:latest
    container_name: glitchtip-web
    environment:
      DATABASE_URL: postgres://glitchtip:secure-db-password-change-this@postgres:5432/glitchtip
      REDIS_URL: redis://:secure-redis-password@redis:6379
      SECRET_KEY: "django-secret-key-change-this-now"
      GLITCHTIP_DOMAIN: "http://localhost:8000"
      DEFAULT_FROM_EMAIL: "alerts@yourdomain.com"
      EMAIL_URL: "consolemail://"
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  worker:
    image: glitchtip/glitchtip:latest
    container_name: glitchtip-worker
    environment:
      DATABASE_URL: postgres://glitchtip:secure-db-password-change-this@postgres:5432/glitchtip
      REDIS_URL: redis://:secure-redis-password@redis:6379
      SECRET_KEY: "django-secret-key-change-this-now"
      GLITCHTIP_DOMAIN: "http://localhost:8000"
    command: ./bin/run-celery-with-beat.sh
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

volumes:
  postgres_data:
  redis_data:
```

Start the stack:

```bash
docker compose up -d
```

Run the initial migration and create a superuser:

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py create_user \
  --email admin@yourdomain.com \
  --password "admin-password" \
  --name Administrator
```

Access the UI at `http://localhost:8000`.

### SDK Integration — Zero Changes from Sentry

This is where GlitchTip shines. If you're already using Sentry, switching requires changing a single configuration value.

For JavaScript:

```javascript
import * as Sentry from "@sentry/browser";

Sentry.init({
  dsn: "http://your-dsn@localhost:8000/1",  // Point to your GlitchTip instance
  environment: "production",
  tracesSampleRate: 1.0,
});
```

For Python (Django):

```python
# settings.py
SENTRY_DSN = "http://your-dsn@localhost:8000/2"

INSTALLED_APPS = [
    # ...
    "glitchtip",  # Optional: GlitchTip-specific integrations
]

# Everything else stays the same — the Sentry SDK works identically
```

For Ruby on Rails:

```ruby
# config/initializers/sentry.rb
Sentry.init do |config|
  config.dsn = "http://your-dsn@localhost:8000/3"
  config.environment = "production"
  config.enabled_environments = %w[production staging]
  config.breadcrumbs_logger = [:active_support_logger, :http_logger]
end
```

### Best Use Cases

GlitchTip is ideal for teams that want Sentry's error tracking capabilities without the cloud pricing or infrastructure overhead. If your primary need is error monitoring (not full APM or log management), GlitchTip provides the most direct migration path from Sentry with the smallest resource footprint.

## Feature Comparison

| Feature | HyperDX | SigNoz | GlitchTip |
|---------|---------|--------|-----------|
| **Primary Focus** | Unified observability | APM + observability | Error tracking |
| **Data Storage** | ClickHouse | ClickHouse | PostgreSQL |
| **Protocol** | OpenTelemetry (OTLP) | OpenTelemetry (OTLP) | Sentry SDK/Protocol |
| **Error Grouping** | Smart fingerprinting | Automatic grouping | Sentry-compatible |
| **Distributed Tracing** | Yes | Yes | Limited |
| **Log Management** | Yes | Yes | No |
| **Metrics** | Yes | Yes | No |
| **Session Replay** | Yes | No | No |
| **Service Maps** | Basic | Advanced | No |
| **Dashboards** | Query-based | Visual builder | Basic |
| **Alerting** | Yes | Yes | Email + webhooks |
| **Source Maps** | Yes | Yes | Yes |
| **Sentry SDK Compatible** | No | No | Yes |
| **Sentry Migration Effort** | High | High | Minimal |
| **Min. RAM** | 4 GB | 4 GB | 1 GB |
| **Open Source License** | AGPL-3.0 | AGPL-3.0 | MIT |
| **GitHub Stars** | 3.5k+ | 19k+ | 1.5k+ |

## Deployment Considerations

### Resource Requirements

Each platform has different infrastructure needs:

- **GlitchTip** is the lightest — a single $10/month VPS with 2 GB RAM handles moderate traffic. PostgreSQL and Redis can run on the same machine.
- **HyperDX** needs at least 4 GB RAM due to ClickHouse's memory usage. For production, separate the API server from ClickHouse for better performance.
- **SigNoz** has similar requirements to HyperDX but can scale to Kubernetes for large deployments. The Helm chart supports horizontal scaling of all components.

### Data Retention

With self-hosted platforms, you control retention policies:

```yaml
# SigNoz retention configuration (in ClickHouse)
# Set log retention to 90 days
ALTER TABLE signoz_logs ON CLUSTER cluster
  MODIFY SETTING ttl_only_drop_parts = 1;

# HyperDX retention — configure via environment variables
# hyperdx service in docker-compose.yml:
#   environment:
#     LOG_RETENTION_DAYS: "90"
#     TRACE_RETENTION_DAYS: "30"
```

GlitchTip uses PostgreSQL's table partitioning for cleanup:

```sql
-- Clean up error events older than 180 days
DELETE FROM glitchtip_event
WHERE datetime < NOW() - INTERVAL '180 days';
```

### Reverse Proxy Setup

For production deployme[nginx](https://nginx.org/)put the UI behind a reverse proxy with TLS:

```nginx
# /etc/nginx/sites-available/error-tracking
server {
    listen 443 ssl http2;
    server_name errors.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/errors.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/errors.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;  # GlitchTip
        # proxy_pass http://127.0.0.1:8080;  # HyperDX or SigNoz

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Increase body size for large stack traces
        client_max_body_size 50m;
    }
}
```

## Making Your Choice

The right platform depends on your specific needs:

**Choose GlitchTip if:**
- You're currently using Sentry and want the easiest migration
- You only need error tracking (not full observability)
- You have limited infrastructure budget or a small team
- You want the simplest possible setup and maintenance
- MIT licensing is important to your organization

**Choose HyperDX if:**
- You want error tracking plus session replay
- Your team needs unified logs, traces, and errors in one tool
- You're already using OpenTelemetry in your stack
- You value full-text search across all observability data
- You want the best developer experience for debugging

**Choose SigNoz if:**
- You're replacing Datadog, New Relic, or multiple SaaS tools
- You need advanced APM features like service maps
- You run a microservice architecture with distributed tracing
- You want customizable dashboards with a visual builder
- You need enterprise features like multi-tenancy and RBAC

All three platforms are open source, free to self-host, and actively maintained. You can even run multiple platforms side by side during a migration period to compare them with your actual workload before committing.

## Getting Started Today

The fastest way to evaluate these tools is with Docker. Here's a quick-start summary:

```bash
# GlitchTip — Sentry-compatible, lightweight
git clone https://github.com/glitchtip/glitchtip.git
cd glitchtip
docker compose up -d

# HyperDX — unified observability
curl -fsSL https://get.hyperdx.io | bash

# SigNoz — APM + error tracking
git clone -b main https://github.com/SigNoz/signoz.git
cd signoz/deploy/
./install.sh
```

Each platform provides a web UI within minutes of starting the containers. Create a test project, integrate the SDK into a development application, trigger some test errors, and evaluate the debugging experience firsthand.

Self-hosting your error tracking puts you in control of your data, your costs, and your incident response workflow. In 2026, there's no reason to settle for a cloud provider's limitations when powerful, production-ready alternatives are just a `docker compose up` away.

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
