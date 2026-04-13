---
title: "Flipt vs Unleash vs Flagsmith: Best Self-Hosted Feature Flags 2026"
date: 2026-04-13
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete comparison of the top 3 open-source self-hosted feature flag management platforms in 2026 — Flipt, Unleash, and Flagsmith. Docker setup, feature comparison, and production deployment guide."
---

## Feature Flags: Why Self-Host in 2026?

Feature flags (also called feature toggles) let you enable or disable functionality in your applications without deploying new code. In 2026, they are a standard practice across teams of every size — used for gradual rollouts, A/B testing, kill switches, and operational control.

SaaS feature flag providers like LaunchDarkly are powerful but come with trade-offs: vendor lock-in, per-seat pricing that scales painfully, and — critically — your feature flag data and rollout decisions live on someone else's servers.

Self-hosting feature flag infrastructure solves these problems. You own your data, avoid per-developer pricing, and keep your feature management inside your own network. When your CI/CD pipeline depends on feature flags being available, running them on your own infrastructure removes a single point of failure controlled by a third party.

In this guide, we compare the three leading open-source, self-hostable feature flag platforms: **Flipt**, **Unleash**, and **Flagsmith**. We cover architecture, feature comparisons, Docker deployment, and production hardening.

## What Are Feature Flags and Why Do You Need Them?

Feature flags decouple deployment from release. Instead of merging code directly into production visibility, you ship code behind a flag and control its visibility through configuration. This enables:

- **Gradual rollouts**: Enable a feature for 10% of users, monitor metrics, then ramp up
- **Kill switches**: Instantly disable a problematic feature without redeploying
- **A/B testing**: Serve different variants to different user segments
- **Environment-specific config**: Enable features in staging before production
- **Permission-based access**: Gate features behind user roles or subscription tiers

The architecture is simple: your application queries a flag service (or evaluates flags locally from a cached snapshot), and the flag service returns boolean or variant values based on user context, targeting rules, and percentages.

## The Three Platforms at a Glance

### Flipt

Flipt is a lightweight, GitOps-friendly feature flag service written in Go. It stores flags in a SQLite or PostgreSQL database and exposes a clean REST and gRPC API. Flipt's philosophy is simplicity: it focuses on doing feature flags well without becoming a full product management platform. It supports boolean flags, variant flags, segment targeting, and flag snapshots for offline evaluation.

Flipt stands out for its CLI tool and strong GitOps integration. You can export flags as YAML, version them in Git, and sync changes via CI/CD pipelines. Its small resource footprint makes it ideal for small teams and homelab setups.

### Unleash

Unleash is the most mature open-source feature flag platform. Written in Node.js with a PostgreSQL backend, it offers an extensive feature set: A/B testing, gradual rollouts, kill switches, scheduled rollouts, and a full-featured admin UI. Unleash has SDKs for over 15 programming languages and supports edge caching for high-throughput environments.

Unleash's open-source core is generous — most features that LaunchDarkly charges for are available in the free version. The paid enterprise version adds additional capabilities like SSO, audit logs, and change requests, but the self-hosted open-source version is fully functional for most teams.

### Flagsmith

Flagsmith positions itself as a complete feature flag and remote configuration platform. Written in Python (Django) with a PostgreSQL backend, it offers feature flags, remote config, A/B testing, identity management, and segment targeting. Flagsmith's edge proxy architecture is designed for high availability — you can deploy edge proxies in multiple regions that cache flag state locally.

Flagsmith's self-hosted version includes most core features. It supports multi-environment flag management out of the box, which is valuable for teams running staging, QA, and production environments from a single instance.

## Feature Comparison

| Feature | Flipt | Unleash | Flagsmith |
|---------|-------|---------|-----------|
| **Language** | Go | Node.js | Python (Django) |
| **Database** | SQLite / PostgreSQL | PostgreSQL | PostgreSQL |
| **Flag Types** | Boolean, Variant | Boolean, Variant, Experiment | Boolean, Multivariate, Remote Config |
| **Segment Targeting** | Yes | Yes | Yes |
| **Gradual Rollout** | Yes | Yes | Yes |
| **Scheduled Rollout** | No | Yes | Yes |
| **A/B Testing** | Manual | Built-in | Built-in |
| **Edge Caching** | Flag snapshots | Edge server | Edge proxy |
| **Multi-Environment** | Manual (namespaces) | Built-in (projects) | Built-in (environments) |
| **SDK Languages** | 10+ | 15+ | 12+ |
| **GitOps Support** | Excellent (CLI + YAML) | Limited | Limited |
| **gRPC API** | Yes | No | No |
| **REST API** | Yes | Yes | Yes |
| **Admin UI** | Yes | Yes (polished) | Yes |
| **Docker Compose** | Yes | Yes | Yes |
| **Resource Usage** | ~30MB RAM | ~200MB RAM | ~150MB RAM |
| **License** | Apache 2.0 | Apache 2.0 | BSD 3-Clause |

## Choosing the Right Platform

**Pick Flipt if:**
- You want the smallest resource footprint
- GitOps and CLI-first workflows are important to you
- You need gRPC for performance-critical services
- You run a homelab or small team

**Pick Unleash if:**
- You want the most mature, battle-tested platform
- Scheduled rollouts and experiments are core to your workflow
- You need SDKs for niche languages
- Your team prefers a polished, enterprise-grade UI

**Pick Flagsmith if:**
- You need remote configuration alongside feature flags
- Multi-environment management is critical
- You want edge proxy architecture for multi-region deployment
- Python/Django ecosystems are already part of your stack

## Deployment Guide: Docker Compose

### Deploying Flipt

Flipt is the simplest to deploy thanks to its Go binary and optional SQLite backend.

**Basic single-container deployment (SQLite):**

```yaml
# docker-compose.yml
services:
  flipt:
    image: flipt/flipt:latest
    container_name: flipt
    restart: unless-stopped
    ports:
      - "8080:8080"   # HTTP API
      - "9000:9000"   # gRPC
    environment:
      FLIPT_LOG_LEVEL: "info"
    volumes:
      - flipt_data:/var/opt/flipt
    healthcheck:
      test: ["CMD", "/flipt", "health"]
      interval: 30s
      timeout: 5s
      retries: 3

volumes:
  flipt_data:
```

Start it:

```bash
docker compose up -d
```

The admin UI is available at `http://localhost:8080`.

**Production deployment with PostgreSQL:**

```yaml
services:
  flipt:
    image: flipt/flipt:latest
    container_name: flipt
    restart: unless-stopped
    ports:
      - "8080:8080"
      - "9000:9000"
    environment:
      FLIPT_LOG_LEVEL: "info"
      FLIPT_DB_URL: "postgres://flipt:flipt_password@postgres:5432/flipt?sslmode=disable"
      FLIPT_DB_PROTOCOL: "postgres"
      FLIPT_TRACING_ENABLED: "false"
      FLIPT_CACHE_ENABLED: "true"
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "/flipt", "health"]
      interval: 30s
      timeout: 5s
      retries: 3

  postgres:
    image: postgres:16-alpine
    container_name: flipt-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: flipt
      POSTGRES_PASSWORD: flipt_password
      POSTGRES_DB: flipt
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U flipt"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

### Deploying Unleash

Unleash requires PostgreSQL and runs on Node.js.

```yaml
services:
  unleash:
    image: unleashorg/unleash-server:latest
    container_name: unleash
    restart: unless-stopped
    ports:
      - "4242:4242"
    environment:
      DATABASE_URL: "postgres://unleash:unleash_password@postgres:5432/unleash"
      DATABASE_SSL: "false"
      LOG_LEVEL: "warn"
      INIT_FRONTEND_API_TOKENS: "default:development.unleash-insecure-frontend-api-token"
      INIT_CLIENT_API_TOKENS: "default:development.unleash-insecure-api-token"
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:4242/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  postgres:
    image: postgres:16-alpine
    container_name: unleash-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: unleash
      POSTGRES_PASSWORD: unleash_password
      POSTGRES_DB: unleash
    volumes:
      - unleash_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U unleash"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  unleash_postgres_data:
```

```bash
docker compose up -d
```

The admin UI is at `http://localhost:4242`. Default credentials are `admin` / `unleash4all`.

### Deploying Flagsmith

Flagsmith's architecture consists of an API server, a web UI, PostgreSQL, and an optional edge proxy.

```yaml
services:
  flagsmith-api:
    image: flagsmith/flagsmith-api:latest
    container_name: flagsmith-api
    restart: unless-stopped
    environment:
      DATABASE_URL: "postgresql://flagsmith:flagsmith_password@postgres:5432/flagsmith"
      SECRET_KEY: "your-secret-key-change-this-in-production"
      ENV: "production"
      DJANGO_ALLOWED_HOSTS: "*"
      ENABLE_ADMIN_ACCESS_USER_PASS: "true"
      PREVENT_SIGNUP: "true"
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "/app/scripts/healthcheck.py"]
      interval: 30s
      timeout: 10s
      retries: 3

  flagsmith-ui:
    image: flagsmith/flagsmith-frontend:latest
    container_name: flagsmith-ui
    restart: unless-stopped
    environment:
      API_URL: "http://localhost:8000/api/v1/"
      ENV: "production"
    depends_on:
      - flagsmith-api
    ports:
      - "8000:8000"

  postgres:
    image: postgres:16-alpine
    container_name: flagsmith-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: flagsmith
      POSTGRES_PASSWORD: flagsmith_password
      POSTGRES_DB: flagsmith
    volumes:
      - flagsmith_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U flagsmith"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  flagsmith_postgres_data:
```

```bash
docker compose up -d
```

The admin UI is at `http://localhost:8000`. Create an admin account on first login (unless `PREVENT_SIGNUP` is set, then use the admin interface via `flagsmith-api` container).

## Integrating Feature Flags into Your Application

### Using Flipt in Go

Flipt's Go SDK evaluates flags natively with optional snapshot-based offline evaluation:

```go
package main

import (
    "context"
    "fmt"
    flipt "go.flipt.io/flipt/grpc"
    "google.golang.org/grpc"
    "google.golang.org/grpc/credentials/insecure"
)

func main() {
    conn, err := grpc.NewClient("localhost:9000",
        grpc.WithTransportCredentials(insecure.NewCredentials()),
    )
    if err != nil {
        panic(err)
    }
    defer conn.Close()

    client := flipt.NewFliptClient(conn)
    
    resp, err := client.Evaluate(context.Background(), &flipt.EvaluationRequest{
        NamespaceKey: "default",
        FlagKey:      "new-checkout-flow",
        EntityId:     "user-123",
        Context: map[string]string{
            "email":  "user@example.com",
            "plan":   "premium",
        },
    })
    if err != nil {
        panic(err)
    }

    if resp.Match {
        fmt.Println("Flag enabled, showing new checkout")
    } else {
        fmt.Println("Flag disabled, showing legacy checkout")
    }
}
```

### Using Unleash in Node.js

```javascript
const { initialize } = require('unleash-client');

const unleash = initialize({
  url: 'http://localhost:4242/api/',
  appName: 'my-web-app',
  customHeaders: {
    Authorization: 'default:development.unleash-insecure-api-token',
  },
});

unleash.on('ready', () => {
  const enabled = unleash.isEnabled('new-checkout-flow', {
    userId: 'user-123',
    sessionId: 'session-456',
    properties: { plan: 'premium' },
  });

  if (enabled) {
    console.log('New checkout flow is active');
  }
});
```

### Using Flagsmith in Python

```python
from flagsmith import Flagsmith

flagsmith = Flagsmith(
    environment_key="your-env-key",
    api_url="http://localhost:8000/api/v1/",
)

flags = flagsmith.get_identity_flags("user-123", traits={"plan": "premium"})

if flags.is_feature_enabled("new_checkout_flow"):
    print("New checkout flow is active")
    checkout_variant = flags.get_feature_value("checkout_variant")
    print(f"Using variant: {checkout_variant}")
```

## Production Hardening Checklist

Regardless of which platform you choose, follow these production deployment practices:

**1. Use PostgreSQL over SQLite**
SQLite works for development and small homelab setups, but PostgreSQL is essential for production. It provides connection pooling, WAL-based replication, and proper concurrent access handling.

**2. Add a Reverse Proxy with TLS**
Put your feature flag service behind a reverse proxy with TLS termination:

```nginx
server {
    listen 443 ssl http2;
    server_name flags.example.com;

    ssl_certificate /etc/letsencrypt/live/flags.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/flags.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # gRPC support (Flipt)
    location /flipt.Flipt/ {
        grpc_pass grpc://127.0.0.1:9000;
        grpc_set_header Host $host;
    }
}
```

**3. Enable Database Backups**
Feature flag state is configuration — losing it means losing your rollout state. Automate backups:

```bash
#!/bin/bash
# flipt-backup.sh
BACKUP_DIR="/opt/backups/flipt"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

docker exec flipt-postgres pg_dump -U flipt flipt | gzip > "$BACKUP_DIR/flipt_$TIMESTAMP.sql.gz"

# Keep last 30 days
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete
```

Add to crontab:
```
0 2 * * * /opt/scripts/flipt-backup.sh
```

**4. Monitor Flag Evaluation Latency**
Feature flag lookups should be fast — ideally under 5ms. Monitor your evaluation endpoint:

```yaml
# Prometheus scrape config for Flipt
- job_name: 'flipt'
  scrape_interval: 15s
  static_configs:
    - targets: ['localhost:9000']
  metrics_path: '/metrics'
```

**5. Use API Tokens, Not Admin Credentials**
Application services should use read-only API tokens, not admin credentials. Rotate tokens regularly. All three platforms support token-based authentication with scoped permissions.

**6. Implement Flag Hygiene**
Feature flags accumulate over time. Establish a process for removing stale flags:
- Add expiration dates to flag descriptions
- Review unused flags monthly
- Delete flags 30 days after a feature reaches 100% rollout
- Use the platform's analytics to find flags with zero evaluations

## Migration and Upgrade Strategy

When upgrading any of these platforms:

```bash
# 1. Backup the database first
docker exec flipt-postgres pg_dump -U flipt flipt > backup.sql

# 2. Pull the new image version
docker compose pull

# 3. Check the changelog for breaking changes
# Flipt: https://github.com/flipt-io/flipt/releases
# Unleash: https://github.com/Unleash/unleash/releases
# Flagsmith: https://github.com/Flagsmith/flagsmith/releases

# 4. Restart services (migrations run automatically)
docker compose up -d

# 5. Verify health
curl http://localhost:8080/api/v1/meta/health  # Flipt
curl http://localhost:4242/health              # Unleash
curl http://localhost:8000/api/v1/health       # Flagsmith
```

## Performance Considerations

**Flipt** is the lightest option. A single Go process uses roughly 30MB of RAM and handles thousands of evaluations per second via gRPC. Its snapshot feature allows applications to download flag state and evaluate locally with zero network latency — ideal for latency-critical services.

**Unleash** has the most extensive SDK ecosystem. Its SDKs include built-in client-side caching and periodic polling, so flag evaluations are typically served from memory after the initial fetch. The Unleash edge server pattern can further reduce latency by deploying read-only flag caches close to your application.

**Flagsmith** offers edge proxies that serve flag state from local caches. This is particularly useful for multi-region deployments where you want flag evaluation to stay within each region's network boundary. The Flagsmith SDK also supports local evaluation mode for reduced latency.

## Conclusion

Self-hosting feature flags gives you full control over your rollout infrastructure. The choice between Flipt, Unleash, and Flagsmith depends on your specific needs:

- **Flipt** wins on simplicity, resource efficiency, and GitOps workflows
- **Unleash** wins on maturity, SDK breadth, and enterprise features in the free tier
- **Flagsmith** wins on remote configuration capabilities and multi-region edge proxy architecture

All three are production-ready, actively maintained, and can be deployed with Docker Compose in under five minutes. Start with the one that aligns with your team's existing technology stack, and migrate later if your requirements evolve — all three provide REST APIs and import/export tools that make migration manageable.

The most important step is getting started. Every feature flag you add reduces deployment risk and increases your team's ability to ship confidently.
