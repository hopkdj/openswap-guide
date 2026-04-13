---
title: "Best Self-Hosted Error Tracking: GlitchTip vs Sentry vs Signoz 2026"
date: 2026-04-13
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete guide to self-hosted error tracking in 2026. Compare GlitchTip, Sentry alternatives, Signoz, and more. Includes Docker setup, configuration tips, and migration strategies."
---

Error tracking is one of the most critical pieces of infrastructure for any software team. When your application crashes in production, you need to know exactly what happened, who was affected, and how to fix it — fast.

For years, Sentry has been the default answer. But relying on a third-party SaaS for your error data comes with real costs: unpredictable pricing that scales with every error, data residency concerns, and limited control over retention policies. In 2026, self-hosted error tracking has never been more viable.

This guide covers the best open-source error tracking solutions you can run on your own infrastructure, with practical setup instructions and a detailed comparison to help you choose.

## Why Self-Host Your Error Tracking?

Before diving into tools, let's establish why running error tracking on your own servers makes sense:

**Cost predictability.** SaaS error trackers charge by event volume. A single misconfigured retry loop can generate millions of errors overnight, resulting in surprise bills. Self-hosted solutions cost the same whether you capture ten errors or ten million.

**Data privacy and compliance.** Error reports often contain stack traces, user IDs, request payloads, and occasionally sensitive data in context variables. For teams handling health data (HIPAA), financial records (PCI DSS), or EU citizen data (GDPR), keeping error data on-premises eliminates a major compliance risk.

**Unlimited retention.** SaaS plans typically cap error retention at 30–90 days unless you pay enterprise rates. Self-hosted, you decide how long to keep data. Need to investigate a regression from six months ago? It's still there.

**Custom integrations.** Running the software yourself means you can modify the codebase, add custom plugins, integrate with internal tools, and control the entire pipeline from error capture to alerting.

**No vendor lock-in.** Your error data is yours. If you ever want to change tools or migrate, nothing is held hostage behind a proprietary API.

## GlitchTip: The Drop-in Sentry Alternative

[GlitchTip](https://glitchtip.com) is the most direct self-hosted alternative to Sentry. It implements a compatible API, meaning you can point your existing Sentry SDKs at a GlitchTip instance with zero code changes.

### Architecture

GlitchTip is built on Python/Django with PostgreSQL for storage and Redis for caching and task queues. The frontend is a single-page application. It supports the full Sentry SDK ecosystem — Python, JavaScript, Go, Ruby, Rust, PHP, and more.

### Docker Compose Setup

The fastest way to get GlitchTip running is with Docker Compose:

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: glitchtip
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-secret}
      POSTGRES_DB: glitchtip
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U glitchtip"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  web:
    image: glitchtip/glitchtip:latest
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://glitchtip:${POSTGRES_PASSWORD:-secret}@postgres:5432/glitchtip
      SECRET_KEY: ${SECRET_KEY:-change-me-to-a-random-string}
      EMAIL_URL: consolemail://
      GLITCHTIP_DOMAIN: http://localhost:8000
      DEFAULT_FROM_EMAIL: admin@yourdomain.com
      CELERY_WORKER_AUTOSCALE: 1,3
      CELERY_WORKER_MAX_TASKS_PER_CHILD: 10000
    restart: unless-stopped

  worker:
    image: glitchtip/glitchtip:latest
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://glitchtip:${POSTGRES_PASSWORD:-secret}@postgres:5432/glitchtip
      SECRET_KEY: ${SECRET_KEY:-change-me-to-a-random-string}
      EMAIL_URL: consolemail://
      CELERY_WORKER_AUTOSCALE: 1,3
    command: ./bin/run-celery-with-beat.sh
    restart: unless-stopped

  migrate:
    image: glitchtip/glitchtip:latest
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://glitchtip:${POSTGRES_PASSWORD:-secret}@postgres:5432/glitchtip
      SECRET_KEY: ${SECRET_KEY:-change-me-to-a-random-string}
    command: "./manage.py migrate"
    restart: "no"

volumes:
  pgdata:
```

Save this as `docker-compose.yml`, generate a secret key, and launch:

```bash
export POSTGRES_PASSWORD=$(openssl rand -base64 32)
export SECRET_KEY=$(openssl rand -base64 48)
docker compose up -d
```

After the containers start, create an admin user:

```bash
docker compose exec web ./manage.py create_user \
  --email admin@yourdomain.com \
  --password 'YourSecurePassword123!'
```

### SDK Configuration

In your existing applications, you only need to change the DSN. If you previously used:

```python
import sentry_sdk
sentry_sdk.init(dsn="https://abc123@sentry.io/123")
```

Point it at your GlitchTip instance:

```python
import sentry_sdk
sentry_sdk.init(
    dsn="https://abc123@errors.yourdomain.com/123",
    # Optional: add custom tags for environment tracking
    environment="production",
    traces_sample_rate=1.0,
)
```

That's it. All Sentry SDK features — breadcrumbs, user context, performance traces, release tracking — work identically.

### Resource Requirements

For a small to medium team (up to 50 projects, ~100k events/day):

| Component | CPU | RAM | Storage |
|-----------|-----|-----|---------|
| PostgreSQL | 2 cores | 2 GB | 50 GB SSD |
| Redis | 1 core | 512 MB | Minimal |
| Web + Worker | 2 cores | 2 GB | Minimal |

Total: ~4 CPU cores, 4.5 GB RAM.

## SigNoz: Full-Stack Observability with Error Tracking

[SigNoz](https://signoz.io) takes a different approach. Rather than being a dedicated error tracker, it's a full observability platform that combines error tracking, distributed tracing, metrics, and logs into a single pane of glass. It's built on OpenTelemetry, the open-source observability standard backed by the CNCF.

### When to Choose SigNoz

SigNoz shines when you need more than just error tracking. If your team also wants:

- Distributed tracing across microservices
- Application performance metrics (APM)
- Log aggregation and full-text search
- Custom dashboards with arbitrary queries

...then SigNoz consolidates multiple tools into one. The trade-off is higher resource consumption and a steeper learning curve.

### Docker Compose Setup

SigNoz provides an official install script, but you can also run it manually:

```bash
# Clone the official repository
git clone -b main https://github.com/SigNoz/signoz.git
cd signoz/deploy/

# Start everything (ClickHouse, Query Service, Frontend, OTel Collector)
docker compose -f docker/clickhouse-setup/docker-compose.yaml up -d
```

For production deployments, SigNoz recommends Kubernetes via their Helm chart:

```bash
helm repo add signoz https://charts.signoz.io
helm install my-release signoz/signoz \
  --namespace platform \
  --create-namespace \
  --set clickhouse.enabled=true
```

### Instrumenting Your Application

SigNoz uses the OpenTelemetry SDK natively. Here's how to instrument a Python application:

```bash
# Install OpenTelemetry packages
pip install opentelemetry-distro opentelemetry-exporter-otlp

# Auto-instrument your app (wraps it with OTel)
opentelemetry-bootstrap -a install

# Run your application with OTLP exporter pointing to SigNoz
OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317" \
OTEL_RESOURCE_ATTRIBUTES="service.name=my-python-app" \
opentelemetry-instrument python app.py
```

For Node.js applications:

```bash
npm install @opentelemetry/api @opentelemetry/sdk-node \
  @opentelemetry/auto-instrumentations-node \
  @opentelemetry/exporter-trace-otlp-grpc
```

```javascript
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
```

### Resource Requirements

SigNoz is more resource-intensive due to ClickHouse and the full observability stack:

| Component | CPU | RAM | Storage |
|-----------|-----|-----|---------|
| ClickHouse | 4 cores | 8 GB | 200 GB SSD |
| Query Service | 2 cores | 2 GB | Minimal |
| Frontend | 1 core | 512 MB | Minimal |
| OTel Collector | 1 core | 1 GB | Minimal |

Total: ~8 CPU cores, 11.5 GB RAM for a production setup.

## Highlight: Open-Source Session Replay + Error Tracking

[Highlight](https://highlight.io) offers a unique approach: it combines error tracking with full session replay. When an error occurs, you don't just see a stack trace — you see exactly what the user was doing, with a video-like recording of their session (captured via DOM mutation tracking, not screen recording).

### Docker Setup

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: highlight
      POSTGRES_USER: highlight
      POSTGRES_PASSWORD: ${HIGHLIGHT_DB_PASSWORD:-highlight_pass}
    volumes:
      - highlight-pg:/var/lib/postgresql/data

  clickhouse:
    image: clickhouse/clickhouse-server:23.8
    environment:
      CLICKHOUSE_DB: highlight
      CLICKHOUSE_USER: highlight
      CLICKHOUSE_PASSWORD: ${HIGHLIGHT_CH_PASSWORD:-highlight_pass}
    volumes:
      - highlight-ch:/var/lib/clickhouse

  frontend:
    image: highlight/front-end:latest
    ports:
      - "8080:8080"
    environment:
      FRONTEND_PORT: 8080
      HIGHLIGHT_BEHIND_PROXY: "true"
    depends_on:
      - postgres
      - clickhouse

volumes:
  highlight-pg:
  highlight-ch:
```

### SDK Integration

```bash
npm install @highlight-run/browser
```

```javascript
import { H } from '@highlight-run/browser';

H.init('<YOUR_PROJECT_ID>', {
  tracingOrigins: true,
  networkRecording: {
    enabled: true,
    recordHeadersAndBody: true,
    urlBlocklist: ['/health', '/metrics'],
  },
});

// Capture errors manually
window.onerror = function (msg, url, line, col, error) {
  H.consumeError(error);
};
```

## Comparison Table

Here's a side-by-side comparison of the three main options:

| Feature | GlitchTip | SigNoz | Highlight |
|---------|-----------|--------|-----------|
| **Primary Focus** | Error tracking | Full observability | Session replay + errors |
| **Sentry SDK Compatible** | Yes | No | No |
| **Distributed Tracing** | No | Yes (OpenTelemetry) | Limited |
| **Session Replay** | No | No | Yes |
| **Log Aggregation** | No | Yes | Basic |
| **Metrics/APM** | Basic | Full | Basic |
| **Data Store** | PostgreSQL | ClickHouse | PostgreSQL + ClickHouse |
| **Min. RAM (prod)** | ~4.5 GB | ~11.5 GB | ~6 GB |
| **Multi-tenancy** | Yes (organizations/projects) | Yes (workspaces) | Yes (projects) |
| **Alerting** | Email, Slack, Webhook | Email, Slack, Webhook, PagerDuty | Email, Slack, Webhook |
| **License** | MIT | Apache 2.0 | Apache 2.0 |
| **GitHub Stars** | 3.5k+ | 16k+ | 6k+ |
| **Migration from Sentry** | Drop-in | Manual (re-instrument) | Manual (re-instrument) |
| **Active Development** | Steady | Very active | Very active |

## Choosing the Right Tool

### Pick GlitchTip if:
- You already use Sentry SDKs and want a drop-in replacement
- You want the simplest setup with the lowest resource requirements
- Your primary need is error tracking, not full observability
- You need multi-tenant support (agencies, SaaS providers)

### Pick SigNoz if:
- You want errors, traces, metrics, and logs in one platform
- Your team uses or plans to adopt OpenTelemetry
- You're running microservices and need distributed tracing
- You have the infrastructure budget for ClickHouse

### Pick Highlight if:
- You want to see exactly what users were doing when errors occurred
- Session replay would significantly speed up your debugging workflow
- You're building a customer-facing web application
- You want a visual debugging experience for your support team

## Production Hardening Checklist

Regardless of which tool you choose, follow these steps before running in production:

### 1. Add a Reverse Proxy with TLS

```nginx
server {
    listen 80;
    server_name errors.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name errors.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/errors.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/errors.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 50m;
    }
}
```

### 2. Configure Automated Backups

```bash
#!/bin/bash
# backup.sh — PostgreSQL backup for GlitchTip
BACKUP_DIR="/opt/backups/error-tracking"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

docker compose exec -T postgres pg_dump -U glitchtip glitchtip | \
  gzip > "$BACKUP_DIR/glitchtip_${DATE}.sql.gz"

# Remove old backups
find "$BACKUP_DIR" -name "glitchtip_*.sql.gz" -mtime +${RETENTION_DAYS} -delete

echo "Backup completed: glitchtip_${DATE}.sql.gz"
```

Add to cron:

```cron
0 2 * * * /opt/scripts/backup.sh >> /var/log/error-tracking-backup.log 2>&1
```

### 3. Set Up Resource Monitoring

Monitor the key metrics that predict capacity issues:

```bash
# PostgreSQL connection count (GlitchTip)
docker compose exec postgres psql -U glitchtip -c \
  "SELECT count(*) FROM pg_stat_activity;"

# ClickHouse disk usage (SigNoz)
docker compose exec clickhouse clickhouse-client --query \
  "SELECT formatReadableSize(total_bytes) FROM system.tables WHERE database='signoz_traces';"

# Error ingestion rate
docker compose exec worker celery -A glitchtip inspect active --timeout=5
```

### 4. Configure Alert Rules

Set up alerts for infrastructure-level issues before they affect error tracking:

- **Database disk usage > 80%** — prevents ingestion failures
- **Error ingestion queue depth > 1000** — indicates processing bottleneck
- **Worker process crashes** — ensures error processing stays healthy
- **SSL certificate expiry < 30 days** — prevents SDK connection failures

## Migration from SaaS Sentry to Self-Hosted

If you're currently using Sentry's hosted service, GlitchTip offers the smoothest migration path:

```bash
# Step 1: Install GlitchTip alongside existing Sentry (no disruption)
# Step 2: Create matching project structure in GlitchTip
# Step 3: Update DSNs in your applications (deploy gradually)
# Step 4: Verify error ingestion in GlitchTip
# Step 5: Cancel Sentry subscription after confirming everything works

# For historical data, Sentry does NOT support exporting raw error data.
# You'll need to keep Sentry accessible for historical lookups during a
# transition period, or use their REST API to export issue summaries:
curl -H "Authorization: Bearer $SENTRY_TOKEN" \
  "https://sentry.io/api/0/organizations/myorg/issues/?project=123&query=is:unresolved"
```

## Final Recommendations

Self-hosted error tracking in 2026 is mature, well-documented, and production-ready. The key insight is that you don't need to choose between "powerful" and "self-hosted" anymore.

For most teams migrating from Sentry, **GlitchTip** is the right starting point. It respects your existing SDK investments, runs on modest hardware, and gives you full control over your error data. If your needs expand into full observability later, you can always layer SigNoz on top or run both in parallel — GlitchTip for error triage, SigNoz for performance analysis.

The only question is whether you'll keep paying a SaaS premium for error data that you could own outright.
