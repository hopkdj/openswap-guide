---
title: "Plausible Analytics vs Umami: Best Open Source Google Analytics Alternative in 2026"
date: 2026-04-12
tags: ["comparison", "self-hosted", "analytics", "privacy"]
draft: false
description: "In-depth comparison of Plausible Analytics and Umami — two leading open source, privacy-first web analytics platforms. Includes Docker Compose deployment guides, performance benchmarks, and feature breakdown."
---

Looking for a **privacy-friendly Google Analytics alternative** you can self-host in 2026? You're not alone. Thousands of website owners are ditching GA4 for lightweight, cookie-free analytics tools that respect visitor privacy while still delivering actionable insights.

The two most popular open source options are **Plausible Analytics** and **Umami**. Both are privacy-first, GDPR-compliant, and can be deployed with Docker Compose on a single server. But which one should you choose?

In this guide, we break down every feature, compare performance and resource usage, and provide ready-to-use Docker Compose configurations so you can deploy either tool in minutes.

## Quick Comparison Table

| Feature | Plausible Analytics (CE v3.2) | Umami (v3) |
|---|---|---|
| **GitHub Stars** | 24.6k ⭐ | 36.1k ⭐ |
| **License** | AGPL-3.0 | MIT |
| **Language** | Elixir / Phoenix | Node.js / Next.js |
| **Database** | PostgreSQL + ClickHouse | PostgreSQL |
| **Script Size** | ~1 KB (minified) | ~2 KB (minified) |
| **Cookie-Free** | Yes | Yes |
| **GDPR Compliant** | Yes (no consent banner needed) | Yes (no consent banner needed) |
| **Real-Time Dashboard** | Yes | Yes |
| **Event Tracking** | Yes (custom events) | Yes (data-umami-event) |
| **Goal/Funnel Tracking** | Goals ✅ / Funnels ❌ (CE only) | Goals ✅ / Funnels ✅ |
| **Session Replay** | No | Yes |
| **Team Management** | Limited (CE) | Yes |
| **REST API** | Stats API | Full REST API |
| **Shared Dashboard Links** | Yes | Yes |
| **Email Reports** | Yes | No |
| **UTM Tracking** | Yes | Yes |
| **Search Console Integration** | Yes (Cloud only) | No |
| **Minimum RAM** | ~4 GB (ClickHouse) | ~1 GB |
| **Docker Services** | 3 (app + Postgres + ClickHouse) | 2 (app + Postgres) |

## Plausible Analytics (Community Edition)

**Plausible Analytics** is a lightweight, open source web analytics platform built with Elixir and the Phoenix framework. It uses a dual-database architecture — PostgreSQL for site settings and user data, and ClickHouse for high-performance event analytics.

Plausible's philosophy is simplicity: a single-page dashboard that shows all essential metrics at a glance. No complex configurations, no custom report builders — just clean, actionable data.

### Key Features

- **Lightweight tracking script** (~1 KB) — 75x smaller than Google Analytics, keeping your site fast
- **Automatic event tracking** — outbound clicks, file downloads, and form submissions tracked without code changes
- **UTM campaign tracking** — full support for UTM parameters with automatic channel grouping
- **Email reports** — weekly and monthly email summaries delivered automatically
- **Search Console integration** (Cloud) — view organic search queries alongside your traffic data
- **Shared links** — create public or password-protected dashboard URLs for stakeholders
- **Bot filtering** — filters out known bots, referrer spam, and data center traffic
- **40+ country databases** — IP geolocation with optional MaxMind integration for self-hosted

### Docker Compose Deployment

Plausible CE v3.2 requires three services: PostgreSQL, ClickHouse, and the Plausible application itself. The ClickHouse dependency means you'll need at least **4 GB of RAM** for stable operation.

```yaml
services:
  plausible_db:
    image: postgres:16-alpine
    restart: always
    volumes:
      - db-data:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=postgres
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      start_period: 1m

  plausible_events_db:
    image: clickhouse/clickhouse-server:24.12-alpine
    restart: always
    volumes:
      - event-data:/var/lib/clickhouse
      - event-logs:/var/log/clickhouse-server
    ulimits:
      nofile:
        soft: 262144
        hard: 262144
    environment:
      - CLICKHOUSE_SKIP_USER_SETUP=1
    healthcheck:
      test:
        [
          "CMD-SHELL",
          "wget --no-verbose --tries=1 -O - http://127.0.0.1:8123/ping || exit 1",
        ]
      start_period: 1m

  plausible:
    image: ghcr.io/plausible/community-edition:v3.2.0
    restart: always
    command: sh -c "/entrypoint.sh db createdb && /entrypoint.sh db migrate && /entrypoint.sh run"
    depends_on:
      plausible_db:
        condition: service_healthy
      plausible_events_db:
        condition: service_healthy
    ports:
      - "8000:8000"
    volumes:
      - plausible-data:/var/lib/plausible
    environment:
      - BASE_URL=http://localhost:8000
      - SECRET_KEY_BASE=your-secret-key-here-generate-with-openssl-rand-base64-48
      - TOTP_VAULT_KEY=your-totp-key-here
    ulimits:
      nofile:
        soft: 65535
        hard: 65535

volumes:
  db-data:
  event-data:
  event-logs:
  plausible-data:
```

**To deploy:**

```bash
# Create the directory
mkdir plausible-analytics && cd plausible-analytics

# Save the compose file
nano compose.yml  # paste the configuration above

# Generate secret keys
openssl rand -base64 48  # use for SECRET_KEY_BASE

# Start all services
docker compose up -d

# Check logs
docker compose logs -f plausible
```

Open `http://localhost:8000` to access the dashboard. Create your first account, add your website, and paste the tracking script into your site's `<head>` tag.

## Umami

**Umami** is a modern, open source web analytics platform built with Next.js and PostgreSQL. With over **36.1k GitHub stars**, it's one of the most popular self-hosted analytics solutions available. Umami v3 introduced major new features including session replays, funnels, and team management.

Umami's standout advantage is its simplicity — a single PostgreSQL database is all you need, making it significantly lighter on resources than Plausible.

### Key Features

- **Session replay** — watch individual visitor sessions to understand user behavior (Plausible doesn't offer this)
- **Funnels and journeys** — visualize conversion paths and identify drop-off points
- **Team management** — invite team members with role-based access control
- **Retention analysis** — track returning visitors and cohort behavior over time
- **Boards** — create custom dashboards with the metrics that matter to you
- **Full REST API** — programmatic access to all analytics data for custom integrations
- **Performance tracking** — Core Web Vitals monitoring built in
- **Compare mode** — compare date ranges side by side directly in the dashboard
- **Attribution tracking** — understand which channels drive conversions
- **Revenue tracking** — attribute revenue to campaigns and traffic sources

### Docker Compose Deployment

Umami's architecture is simpler — just the application and PostgreSQL. It runs comfortably on servers with **as little as 1 GB of RAM**.

```yaml
services:
  umami:
    image: ghcr.io/umami-software/umami:latest
    ports:
      - "3000:3000"
    environment:
      DATABASE_URL: postgresql://umami:umami@db:5432/umami
      APP_SECRET: replace-me-with-a-random-string
    depends_on:
      db:
        condition: service_healthy
    init: true
    restart: always
    healthcheck:
      test: ["CMD-SHELL", "curl http://localhost:3000/api/heartbeat"]
      interval: 5s
      timeout: 5s
      retries: 5

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: umami
      POSTGRES_USER: umami
      POSTGRES_PASSWORD: umami
    volumes:
      - umami-db-data:/var/lib/postgresql/data
    restart: always
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  umami-db-data:
```

**To deploy:**

```bash
# Create the directory
mkdir umami-analytics && cd umami-analytics

# Save the compose file
nano compose.yml  # paste the configuration above

# Generate a secure secret
openssl rand -hex 32  # use for APP_SECRET

# Start services
docker compose up -d

# Check logs
docker compose logs -f umami
```

Open `http://localhost:3000` and log in with the default credentials:
- **Username:** `admin`
- **Password:** `umami`

**Change the default password immediately** after first login. Add your website, get the tracking script, and embed it in your site's `<head>`.

## Performance & Resource Comparison

### Resource Usage

| Metric | Plausible CE | Umami |
|---|---|---|
| **Minimum RAM** | 4 GB | 1 GB |
| **Disk (idle)** | ~2 GB | ~500 MB |
| **Docker Containers** | 3 | 2 |
| **Database Engines** | 2 (PostgreSQL + ClickHouse) | 1 (PostgreSQL) |
| **Startup Time** | ~30-45 seconds | ~10-15 seconds |

Plausible's ClickHouse requirement is the main differentiator. ClickHouse is incredibly fast for analytical queries — it can process billions of events in milliseconds — but it demands more RAM and disk space. If you're running on a budget VPS with 1-2 GB RAM, Umami is the clear winner.

### Query Performance

- **Plausible** excels at large-scale analytics. ClickHouse can handle **hundreds of millions of events** without breaking a sweat. If your site gets millions of pageviews per month, Plausible's architecture will scale better.
- **Umami** handles moderate traffic volumes well. For most personal and business websites (under 1M pageviews/month), PostgreSQL is more than sufficient. The v3 architecture improved query performance significantly over v2.

### Tracking Script Impact

Both tools use cookie-free, lightweight tracking scripts that have negligible impact on page load times:

- **Plausible:** ~1 KB minified, loads asynchronously, no cookie consent needed
- **Umami:** ~2 KB minified, loads asynchronously, no cookie consent needed

Both are dramatically lighter than Google Analytics (~45 KB+) and won't affect your Core Web Vitals scores.

## Which Should You Choose?

### Choose Plausible Analytics if:
- You need **email reports** for stakeholders
- You want **Search Console integration** (Cloud version)
- You process **high traffic volumes** (millions of pageviews/month)
- You prefer a **simpler, focused dashboard** — one page, all metrics
- You have a server with **4+ GB RAM** available
- You value the **AGPL license** for strong copyleft guarantees

### Choose Umami if:
- You need **session replays** to watch visitor behavior
- You want **funnels and journey analysis** (available in CE)
- You need **team management** with role-based access
- You're on a **budget server** (1-2 GB RAM is enough)
- You want a **simpler Docker setup** (2 services vs 3)
- You prefer the **permissive MIT license**
- You need **custom dashboards** (Boards feature)

## Frequently Asked Questions

### 1. Are Plausible and Umami truly GDPR compliant?

Yes. Both Plausible and Umami are **GDPR compliant out of the box**. They don't use cookies, don't collect personal data, and don't use persistent identifiers. This means you typically **don't need a cookie consent banner** when using either tool. All data processing is anonymous — no IP addresses are stored in full, and no cross-site tracking occurs.

### 2. Can I migrate from Google Analytics to Plausible or Umami?

**Plausible** offers a GA4 import feature (Cloud version) and a CSV import for self-hosted. You can export your GA4 data and import historical stats. **Umami** doesn't have a built-in GA migration tool, but you can use their REST API to programmatically backfill data if needed. For most sites, starting fresh with a privacy-first tool is the recommended approach.

### 3. How much traffic can self-hosted Plausible and Umami handle?

**Plausible CE** with ClickHouse can handle **hundreds of millions of events** per month on a properly sized server (8+ GB RAM). **Umami v3** handles **up to ~5 million pageviews/month** comfortably on a 4 GB RAM server with PostgreSQL. For most personal blogs, small business sites, and portfolios, both tools are more than capable.

### 4. Do I need a reverse proxy to deploy Plausible or Umami?

For production use, **yes** — you should put either tool behind a reverse proxy like Nginx, Caddy, or Traefik to handle HTTPS termination. A typical setup uses:
- **Caddy** (easiest — automatic HTTPS with Let's Encrypt)
- **Nginx + Certbot** (most common)
- **Traefik** (best for Docker-native setups)

Both tools can also run behind Cloudflare for additional caching and DDoS protection.

### 5. Can I use both Plausible and Umami on the same website?

Technically, yes — you can install both tracking scripts simultaneously. However, this adds two HTTP requests to every page load and isn't recommended. Choose the one that best fits your needs. If you need both lightweight dashboards *and* session replays, Umami covers both use cases alone.

### 6. What happens to my data if I stop using Plausible or Umami?

Since you self-host both tools, **you own 100% of your data**. If you stop running the services, the data remains in your PostgreSQL (and ClickHouse for Plausible) databases. You can export data at any time:
- **Plausible:** CSV export via the dashboard
- **Umami:** CSV export and full REST API access

### 7. Is there a managed/cloud version of either tool?

**Plausible** offers official managed hosting starting at $9/month, which includes automatic updates, backups, CDN, and premium features like funnels and SSO. **Umami** has a cloud version (Umami Cloud) with a generous free tier for small sites. Both managed options remove the need to maintain your own infrastructure.

### 8. Can Plausible CE and Umami track single-page applications (SPAs)?

Yes, both support SPA tracking:
- **Plausible:** Automatically detects history API changes (`pushState`/`popState`). For hash-based routing, enable the `hash` option in the tracking script.
- **Umami:** Supports SPA tracking out of the box for React, Vue, Angular, and other frameworks. Just include the standard script and it auto-detects route changes.

## Conclusion

Both **Plausible Analytics** and **Umami** are excellent open source alternatives to Google Analytics that respect user privacy. The right choice depends on your specific needs:

- **For most users**, **Umami** offers the better self-hosted experience in 2026 — simpler deployment (2 Docker services vs 3), lower resource requirements (1 GB RAM), and more features in the free tier including session replays, funnels, and team management.

- **For high-traffic sites**, **Plausible CE** with its ClickHouse backend provides superior query performance at scale, plus email reports that make it easy to share insights with non-technical stakeholders.

Both tools will give you clean, actionable analytics without the complexity and privacy concerns of Google Analytics. Deploy either one with the Docker Compose configurations above, and you'll have a fully functional analytics dashboard running in under 5 minutes.
