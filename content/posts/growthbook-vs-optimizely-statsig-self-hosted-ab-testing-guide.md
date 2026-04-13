---
title: "GrowthBook vs Optimizely vs Statsig: Best Open-Source A/B Testing 2026"
date: 2026-04-13
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete guide to self-hosted A/B testing and experimentation platforms in 2026. GrowthBook Docker deployment, feature comparison with Optimizely and Statsig, and production setup guide."
---

## Why Self-Host A/B Testing in 2026?

A/B testing and experimentation platforms let you run controlled experiments on your product — comparing two or more variants to determine which performs better against defined metrics. In 2026, data-driven product decisions are table stakes for any team that ships software.

Commercial A/B testing platforms like **Optimizely**, **Statsig**, and **LaunchDarkly Experiments** are powerful but come with significant trade-offs:

- **Per-event pricing** that explodes as your traffic grows — Statsig and Optimizely both charge based on monthly active users and experiment evaluations
- **Your experiment data lives on their servers** — including user behavior patterns, conversion rates, and proprietary metrics
- **Vendor lock-in** — migrating experiment history, user segment definitions, and statistical configurations between providers is painful
- **Latency concerns** — every experiment evaluation is a network call to an external service, adding milliseconds to your page load
- **Compliance risk** — storing user-level experimentation data with third parties complicates GDPR, CCPA, and data residency requirements

Self-hosting your experimentation platform solves every one of these problems. You own the data, eliminate per-user pricing, reduce latency by running evaluation locally, and maintain full control over your experimentation infrastructure.

## What Is GrowthBook?

[GrowthBook](https://growthbook.io) is an open-source A/B testing and feature flag platform that provides a self-hosted alternative to Optimizely, Statsig, and LaunchDarkly Experiments. With over 6,800 GitHub stars and backing from a commercial company that maintains a strong open-source commitment, GrowthBook has become the leading open-source choice for product teams that want full control over their experimentation stack.

GrowthBook provides:

- **A/B/n testing** with Bayesian and Frequentist statistical engines
- **Multivariate experiments** testing multiple variables simultaneously
- **Feature flags** for gradual rollouts and kill switches
- **SDKs** for every major platform: JavaScript, React, Python, Go, Ruby, PHP, Java, Kotlin, Swift, Flutter, and more
- **SQL-based metric definitions** — connect directly to your warehouse (PostgreSQL, MySQL, Snowflake, BigQuery, Redshift, ClickHouse)
- **Visual experiment editor** for no-code experiments on web pages
- **User segmentation** with targeting rules based on attributes, cookies, and custom properties
- **Experiment dashboards** with automatic significance calculations and guardrail metrics

### GrowthBook Architecture

GrowthBook follows a **feature evaluation + warehouse analytics** architecture:

1. **Feature flags and targeting rules** are served from the GrowthBook API or evaluated locally via SDKs
2. **Experiment assignments** are determined using hash-based bucketing (consistent per user)
3. **Metrics are computed** by querying your existing data warehouse — no separate event pipeline needed
4. **Results are displayed** in the GrowthBook dashboard with statistical significance, confidence intervals, and Bayesian probabilities

This architecture is fundamentally different from Optimizely and Statsig, which require you to send all experiment events through their event ingestion pipeline. GrowthBook reads data you already have, which simplifies setup and keeps data under your control.

## Quick Comparison: GrowthBook vs Optimizely vs Statsig

| Feature | **GrowthBook** | **Optimizely** | **Statsig** |
|---|---|---|---|
| **License** | MIT (open source) | Proprietary SaaS | Proprietary SaaS |
| **Pricing** | Free (self-hosted) / Cloud from $20/mo | From $50k/year | From $1,500/mo |
| **Self-Hosted** | ✅ Full | ❌ No | ❌ No |
| **Statistical Engine** | Bayesian + Frequentist | Frequentist (default) | Bayesian (default) |
| **Multivariate Tests** | ✅ | ✅ | ✅ |
| **Feature Flags** | ✅ | ✅ (separate product) | ✅ |
| **Visual Editor** | ✅ | ✅ | ❌ No |
| **Data Warehouse Query** | ✅ Direct SQL | ❌ Event pipeline only | ❌ Event pipeline required |
| **Holdout Groups** | ✅ | ✅ | ✅ |
| **CUPED Variance Reduction** | ✅ | ❌ | ✅ |
| **Sequential Testing** | ✅ | ✅ | ✅ |
| **SDKs** | 13+ platforms | 10+ platforms | 15+ platforms |
| **API Access** | ✅ Full REST API | ✅ REST API | ✅ REST + GraphQL |
| **SSO / SAML** | ✅ (Enterprise) | ✅ | ✅ |
| **Data Residency** | ✅ Your server | ❌ US-based | ❌ US-based |
| **Latency** | ~0ms (local eval) | 20-50ms (network call) | 10-30ms (network call) |

## Installation Guide

### Method 1: Quick Start with Docker Compose

The fastest way to get GrowthBook running is with Docker Compose. This deploys the GrowthBook app, MongoDB (for configuration storage), and a demo data source.

```bash
mkdir growthbook && cd growthbook

cat > docker-compose.yml << 'EOF'
version: "3.8"

services:
  growthbook:
    image: growthbook/growthbook:latest
    ports:
      - "3000:3000"
      - "3100:3100"
    environment:
      - MONGO_URI=mongodb://mongo:27017/growthbook
      - APP_ORIGIN=http://localhost:3000
      - API_HOST=http://localhost:3100
      - SECRET=my-secret-key-change-in-production
      - IS_CLOUD=false
      - DISABLE_TELEMETRY=true
    depends_on:
      - mongo
    restart: unless-stopped

  mongo:
    image: mongo:7
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db
    restart: unless-stopped

volumes:
  mongo_data:
    driver: local
EOF

docker compose up -d
```

After the containers start, open `http://localhost:3000` and create your admin account. The first-time setup wizard will guide you through connecting a data source.

### Method 2: Production Deployment with PostgreSQL Backend

For production, GrowthBook supports multiple backend configurations. Here is a more complete setup with reverse proxy, persistent storage, and proper resource limits:

```yaml
version: "3.8"

services:
  growthbook-app:
    image: growthbook/growthbook:latest
    ports:
      - "3000:3000"
      - "3100:3100"
    environment:
      - MONGO_URI=mongodb://mongo:27017/growthbook
      - APP_ORIGIN=https://growthbook.yourdomain.com
      - API_HOST=http://localhost:3100
      - SECRET=${GB_SECRET}
      - SMTP_HOST=smtp.yourdomain.com
      - SMTP_PORT=587
      - SMTP_USER=noreply@yourdomain.com
      - SMTP_PASS=${SMTP_PASSWORD}
      - EMAIL_FROM=noreply@yourdomain.com
      - IS_CLOUD=false
    volumes:
      - gb-uploads:/usr/local/src/app/packages/back-end/uploads
    depends_on:
      mongo:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "2.0"

  mongo:
    image: mongo:7
    environment:
      - MONGO_INITDB_ROOT_USERNAME=${MONGO_USER}
      - MONGO_INITDB_ROOT_PASSWORD=${MONGO_PASS}
    volumes:
      - mongo_data:/data/db
      - ./mongo-init.js:/docker-entrypoint-initdb.d/mongo-init.js:ro
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  reverse-proxy:
    image: caddy:2
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    restart: unless-stopped

volumes:
  mongo_data:
  gb-uploads:
  caddy_data:
  caddy_config:
```

The `Caddyfile` for automatic TLS:

```
growthbook.yourdomain.com {
    reverse_proxy localhost:3000
    encode gzip
}
```

### Method 3: Kubernetes Deployment

For teams running Kubernetes, GrowthBook provides Helm chart support:

```bash
# Add the GrowthBook Helm repository
helm repo add growthbook https://charts.growthbook.io
helm repo update

# Install with custom values
helm install growthbook growthbook/growthbook \
  --namespace growthbook \
  --create-namespace \
  --set appOrigin=https://growthbook.yourdomain.com \
  --set mongodb.auth.rootPassword=$(openssl rand -base64 32) \
  --set secretKey=$(openssl rand -base64 32) \
  --set ingress.enabled=true \
  --set ingress.hostname=growthbook.yourdomain.com \
  --set ingress.tls=true
```

## Configuring Your First A/B Test

### Step 1: Connect Your Data Source

GrowthBook queries your existing database to compute experiment metrics. No separate event tracking pipeline is needed.

1. Go to **Settings > Data Sources**
2. Select your database type (PostgreSQL, MySQL, BigQuery, Snowflake, Redshift, ClickHouse)
3. Enter connection credentials
4. GrowthBook will scan your database schema and suggest tables

Define your metrics using SQL. For example, a conversion metric:

```sql
SELECT
  user_id,
  CAST(TRUE AS BOOLEAN) as converted,
  timestamp
FROM orders
WHERE timestamp BETWEEN DATE('{{start}}') AND DATE('{{end}}')
```

### Step 2: Install the SDK

Add the GrowthBook SDK to your application. Here is the JavaScript/TypeScript example:

```javascript
import { GrowthBook } from "@growthbook/growthbook";

const gb = new GrowthBook({
  apiHost: "https://growthbook.yourdomain.com",
  clientKey: "sdk-abc123def456",
  enableDevMode: true,
  attributes: {
    id: user.id,
    companySize: user.companySize,
    plan: user.plan,
    country: user.country,
  },
});

await gb.loadFeatures();

// Use a feature flag
const checkoutVariant = gb.getFeatureValue("checkout-page-redesign", "control");

if (checkoutVariant === "variant-a") {
  renderCheckoutA();
} else if (checkoutVariant === "variant-b") {
  renderCheckoutB();
} else {
  renderCheckoutControl();
}

// Track experiment viewing
gb.track("checkout_viewed", { value: 1 });
```

### Step 3: Create the Experiment

1. Navigate to **Experiments > New Experiment**
2. Set the experiment name and hypothesis
3. Choose your primary metric (e.g., "Purchase Conversion")
4. Add guardrail metrics (e.g., "Page Load Time", "Error Rate")
5. Configure traffic allocation — e.g., 50/50 split between control and variant
6. Set targeting rules (e.g., only logged-in users, specific countries)
7. Launch the experiment

GrowthBook will automatically track assignments and compute results as data accumulates.

## Statistical Engines Explained

GrowthBook supports two statistical approaches, and understanding the difference matters for how you interpret results.

### Frequentist Approach

The traditional method used by most experimentation platforms. It calculates a p-value representing the probability of observing your results if there were truly no difference between variants.

- **Decision rule**: p-value < 0.05 means "statistically significant"
- **Sample size**: Must pre-calculate and commit to a fixed sample size
- **Interpretation**: Does NOT tell you the probability that variant B is better

### Bayesian Approach

GrowthBook defaults to Bayesian analysis, which provides more intuitive results:

- **Output**: "Variant B has an 87% probability of being better than control"
- **No fixed sample size needed**: You can check results at any time
- **Expected loss**: Shows the potential downside of choosing the wrong variant
- **Credible intervals**: Range where the true effect likely falls

The Bayesian approach is particularly useful for teams that want to make decisions without rigid sample size commitments and want results phrased in natural probability terms rather than p-values.

## Performance Optimization

### Local Feature Evaluation

GrowthBook SDKs download feature definitions at initialization and cache them locally. This means feature flag evaluations happen **in-process** with zero network latency:

```javascript
// The SDK downloads features once at startup
await gb.loadFeatures();

// All subsequent evaluations are instant — no network call
const value = gb.getFeatureValue("dark-mode", false);
```

The SDK checks for updates periodically (default: every 60 seconds) and refreshes the cache in the background. If the GrowthBook API is temporarily unavailable, the SDK falls back to the last cached configuration.

### Stale Feature Handling

For critical applications, configure fallback defaults:

```javascript
const gb = new GrowthBook({
  apiHost: "https://growthbook.yourdomain.com",
  clientKey: "sdk-abc123",
  // If the API is unreachable, use these defaults
  features: {
    "checkout-redesign": { defaultValue: "control" },
    "new-pricing-page": { defaultValue: false },
  },
  onFeatureUsage: (featureKey, result) => {
    // Optional: send usage events to your analytics
    analytics.track("feature_used", { featureKey, value: result.value });
  },
});
```

### CDN Distribution for Feature Definitions

For high-traffic applications, put the GrowthBook API behind a CDN:

```nginx
# Nginx CDN configuration for GrowthBook API
server {
    listen 443 ssl;
    server_name api.growthbook.yourdomain.com;

    # Cache feature definitions for 60 seconds
    location /api/features/ {
        proxy_pass http://growthbook-app:3100;
        proxy_cache_valid 200 60s;
        add_header X-Cache-Status $upstream_cache_status;
        proxy_cache_key "$scheme$request_method$host$request_uri";
    }

    # Do NOT cache experiment results
    location /api/ {
        proxy_pass http://growthbook-app:3100;
        proxy_no_cache 1;
        proxy_cache_bypass 1;
    }
}
```

## Migration from SaaS Platforms

### Moving from Optimizely

1. **Export your experiments**: Use Optimizely's REST API to download experiment configurations
2. **Recreate metrics in GrowthBook**: Write SQL queries that match your Optimizely metric definitions
3. **Update SDK calls**: Replace `optimizely.allDecisionVariables()` with `gb.getFeatureValue()`
4. **Run a shadow experiment**: Run GrowthBook alongside Optimizely for one cycle to verify results match
5. **Switch traffic**: Update your feature flag evaluation to use GrowthBook exclusively

### Moving from Statsig

1. **Export gate configs**: Use Statsig's Admin API to download all feature gates and dynamic configs
2. **Map segment definitions**: Statsig segments map directly to GrowthBook targeting attributes
3. **Migrate event mappings**: Statsig's event-driven metrics need to be translated into GrowthBook SQL metrics
4. **Test SDK integration**: GrowthBook's SDK API is similar to Statsig's — `statsig.checkGate()` becomes `gb.isFeatureOn()`

## Production Checklist

Before running GrowthBook in production:

- [ ] Set a strong `SECRET` environment variable (minimum 32 characters)
- [ ] Enable HTTPS with a valid TLS certificate
- [ ] Configure SMTP for email notifications and password resets
- [ ] Set up MongoDB backups (daily snapshots, 30-day retention)
- [ ] Configure resource limits (minimum 2 GB RAM for the app container)
- [ ] Add monitoring alerts for the GrowthBook API health endpoint
- [ ] Set up SSO/SAML if your organization requires it
- [ ] Configure audit logging for experiment changes
- [ ] Test SDK fallback behavior with the GrowthBook API offline
- [ ] Define a data retention policy for experiment results
- [ ] Restrict API access to your internal network or use API keys
- [ ] Set up regular GrowthBook version upgrades (subscribe to release notes)

## When GrowthBook Is the Right Choice

**Choose GrowthBook when:**
- You already have a data warehouse and want to leverage existing data
- You want full data ownership and residency compliance
- Your traffic volume makes SaaS pricing prohibitive
- You need both feature flags and A/B testing in one platform
- You want to run experiments without adding external service latency
- Your team values open-source software and wants to avoid vendor lock-in

**Consider alternatives when:**
- You need managed support and do not want to operate infrastructure
- You require advanced machine learning-powered experiment optimization
- Your experiments need integration with specific third-party marketing tools
- You are a small team running fewer than 5 experiments per year

## Conclusion

GrowthBook has matured into a genuinely production-ready open-source A/B testing and feature flag platform. Its warehouse-native architecture — reading metrics directly from your existing databases rather than requiring a separate event pipeline — is a genuine architectural advantage that simplifies setup and keeps data under your control.

For teams spending thousands of dollars per month on Optimizely or Statsig, self-hosting GrowthBook can reduce costs to near-zero while providing equivalent statistical rigor, more deployment flexibility, and complete data sovereignty.

The combination of Bayesian statistics, local SDK evaluation, SQL-based metrics, and the MIT license makes GrowthBook the strongest open-source option for product teams serious about experimentation in 2026.
