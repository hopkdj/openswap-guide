---
title: "Ackee vs Fathom vs GoatCounter: Lightweight Privacy-Focused Web Analytics 2026"
date: 2026-04-22
tags: ["comparison", "guide", "self-hosted", "privacy", "analytics"]
draft: false
description: "Compare Ackee, Fathom, and GoatCounter — three lightweight, privacy-focused, self-hosted web analytics tools. Docker setup, feature comparison, and deployment guide for 2026."
---

If you want to understand your website visitors without invading their privacy, cookie consent banners, or bloated tracking scripts, self-hosted lightweight analytics tools are the answer. Unlike Google Analytics or even heavier self-hosted options like Matomo, tools like **Ackee**, **Fathom**, and **GoatCounter** prioritize minimalism, GDPR compliance by design, and low resource consumption.

In this guide, we compare these three privacy-focused analytics platforms — examining their architectures, features, Docker deployment, and which one is the best fit for your use case in 2026.

## Why Choose Lightweight Privacy Analytics?

The standard analytics stack — Google Analytics, Adobe Analytics, or even full-featured self-hosted solutions — collects enormous amounts of personal data: IP addresses, device fingerprints, browsing histories, and more. This creates three problems:

1. **Legal compliance**: GDPR, CCPA, and ePrivacy regulations require explicit consent for tracking cookies. Heavy analytics platforms need cookie banners.
2. **Performance**: Tracking scripts add latency. Google Analytics alone adds 30-60KB of JavaScript to every page load.
3. **User trust**: Visitors increasingly distrust sites that track them extensively.

Lightweight privacy analytics solve all three:
- **No cookies required** — they use anonymized identifiers or no identifiers at all
- **Tiny tracking scripts** — typically under 1KB, often just a single `<script>` tag
- **Self-hosted** — you own all the data, no third-party data sharing
- **GDPR compliant by design** — no consent banner needed when configured correctly

For related reading on building a complete privacy-focused self-hosted stack, see our [SearXNG vs Whoogle privacy search engines guide](../searxng-vs-whoogle-vs-librex-self-hosted-privacy-search-engines/) and the broader [privacy stack overview](../privacy-stack-guide/). If you're comparing heavier analytics platforms, check our [Matomo vs Plausible vs Umami comparison](../matomo-vs-plausible-vs-umami-web-analytics-guide/).

## Quick Comparison Table

| Feature | Ackee | Fathom Lite | GoatCounter |
|---------|-------|-------------|-------------|
| **Language** | Node.js (JavaScript) | Go + Preact | Go |
| **Database** | MongoDB | MySQL/MariaDB/SQLite | SQLite/PostgreSQL |
| **GitHub Stars** | 4,645 | 8,006 | 5,642 |
| **Last Updated** | April 2026 | March 2026 | April 2026 |
| **Tracking Script** | ~1.5 KB | ~1 KB | ~600 bytes |
| **Cookie-Free** | Yes | Yes | Yes |
| **Real-Time Dashboard** | Yes | Yes | Yes |
| **Geolocation** | Yes (approximate) | Yes (country-level) | Yes (country-level) |
| **Custom Events** | Yes | Yes | Yes (manual counting) |
| **API Access** | GraphQL API | REST API | JSON API |
| **Multi-Site Support** | Yes | Yes | Yes |
| **Shared/Public Dashboard** | Yes | Yes | Yes |
| **Resource Footprint** | Moderate (Node + Mongo) | Low (single Go binary) | Very Low (single Go binary) |
| **Docker Image Size** | ~300 MB | ~25 MB | ~15 MB |
| **License** | MIT | MIT | MIT / AGPLv3 |

## Ackee — Modern Node.js Analytics with GraphQL API

[Ackee](https://github.com/electerious/Ackee) is a self-hosted analytics tool built on Node.js with MongoDB. It features a sleek, modern dashboard and a GraphQL API for programmatic access. With over 4,600 GitHub stars and active development through 2026, it remains a popular choice for developers who want a polished analytics experience.

### Key Features

- **GraphQL API** — query your analytics data programmatically using GraphQL
- **Real-time dashboard** — watch visitors arrive in real-time with a clean UI
- **Custom events** — track specific user interactions beyond page views
- **Domain-based tracking** — manage multiple websites from one instance
- **No cookies** — uses a unique anonymized identifier per visit
- **Shared dashboards** — generate public links to share analytics

### Docker Compose Deployment

Ackee requires MongoDB as its data store. Here is the official Docker Compose configuration:

```yaml
services:
  ackee:
    image: electerious/ackee
    container_name: ackee
    restart: always
    ports:
      - '3000:3000'
    environment:
      - ACKEE_MONGODB=mongodb://mongo:27017/ackee
      - ACKEE_USERNAME=admin
      - ACKEE_PASSWORD=your-secure-password
    depends_on:
      - mongo

  mongo:
    image: mongo:7
    container_name: ackee-mongo
    restart: always
    volumes:
      - ackee-mongo-data:/data/db

volumes:
  ackee-mongo-data:
```

Start it with:

```bash
docker compose up -d
```

Then access the dashboard at `http://your-server:3000`. The default port is 3000 — change it in the compose file or put it behind a reverse proxy.

### Tracking Script

Add this to your website's `<head>` section:

```html
<script async src="https://your-ackee-domain.com/tracker.js"
        data-ackee-server="https://your-ackee-domain.com"
        data-ackee-domain-id="your-domain-id"></script>
```

### Resource Requirements

Ackee runs a Node.js application and a MongoDB instance. Expect roughly **200-400 MB of RAM** total. The MongoDB database grows with traffic — plan for approximately **1 GB per million page views** per month.

## Fathom Lite — Simple, Fast Go-Based Analytics

[Fathom Lite](https://github.com/usefathom/fathom) is the open-source, self-hosted version of the commercial Fathom Analytics service. Written in Go, it compiles to a single binary and has an extremely small resource footprint. With over 8,000 GitHub stars, it is the most starred of the three tools.

### Key Features

- **Single binary** — no external dependencies, just one executable
- **Tiny tracking script** — under 1 KB, loads instantly
- **MySQL/SQLite backend** — choose the database that fits your infrastructure
- **Built-in dashboard** — clean, minimal UI with real-time visitor counts
- **Custom events** — track goals, downloads, and form submissions
- **Public dashboard sharing** — share read-only analytics with anyone

### Docker Compose Deployment

Fathom Lite pairs with MySQL (or you can use SQLite for single-binary simplicity). Here is the official Docker Compose configuration:

```yaml
services:
  fathom:
    image: usefathom/fathom:latest
    container_name: fathom
    ports:
      - "8080:8080"
    environment:
      - FATHOM_SERVER_ADDR=:8080
      - FATHOM_DATABASE_DRIVER=mysql
      - FATHOM_DATABASE_NAME=fathom
      - FATHOM_DATABASE_USER=fathom
      - FATHOM_DATABASE_PASSWORD=strong-password-here
      - FATHOM_DATABASE_HOST=mysql:3306
      - FATHOM_SECRET=a-random-secret-key-here
    depends_on:
      - mysql
    restart: always

  mysql:
    image: mysql:8
    container_name: fathom-mysql
    volumes:
      - fathom-mysql-data:/var/lib/mysql
    environment:
      - MYSQL_DATABASE=fathom
      - MYSQL_USER=fathom
      - MYSQL_PASSWORD=strong-password-here
      - MYSQL_ROOT_PASSWORD=root-password-here
    restart: always

volumes:
  fathom-mysql-data:
```

Create the admin user on first run:

```bash
docker compose exec fathom ./fathom user add --email="admin@example.com" --password="your-admin-password"
```

### SQLite Alternative (Single Binary)

For low-traffic sites, Fathom can run with SQLite — no database server needed:

```yaml
services:
  fathom:
    image: usefathom/fathom:latest
    container_name: fathom
    ports:
      - "8080:8080"
    environment:
      - FATHOM_SERVER_ADDR=:8080
      - FATHOM_DATABASE_DRIVER=sqlite3
      - FATHOM_DATABASE_NAME=/app/fathom.db
      - FATHOM_SECRET=your-secret-key
    volumes:
      - fathom-data:/app
    restart: always

volumes:
  fathom-data:
```

### Tracking Script

```html
<script src="https://your-fathom-domain.com/script.js"
        data-site="YOUR-SITE-ID"
        defer></script>
```

### Resource Requirements

Fathom Lite with MySQL uses approximately **100-200 MB of RAM**. The SQLite mode uses even less — the entire process runs in **under 50 MB**. The Docker image is only ~25 MB.

## GoatCounter — Minimalist, No-Nonsense Analytics

[GoatCounter](https://github.com/arp242/goatcounter) takes minimalism to the extreme. Written in Go, it offers a straightforward dashboard with a tiny tracking script (~600 bytes), making it the lightest option of the three. It supports both SQLite and PostgreSQL backends, and its single-binary distribution makes deployment trivial.

### Key Features

- **Ultra-lightweight** — tracking script is only ~600 bytes
- **Single binary** — written in Go, no runtime dependencies
- **SQLite or PostgreSQL** — choose based on your scale needs
- **Built-in multi-tenancy** — host analytics for multiple domains from one instance
- **Public shared dashboards** — publish analytics data as a public page
- **API access** — RESTful JSON API for data export
- **Automatic IP anonymization** — privacy by design
- **Referrer tracking** — see where your visitors come from

### Docker Compose Deployment

GoatCounter offers both SQLite and PostgreSQL configurations. Here is the PostgreSQL version:

```yaml
services:
  goatcounter:
    image: arp242/goatcounter:latest
    container_name: goatcounter
    ports:
      - "8080:8080"
    environment:
      - GOATCOUNTER_DB=postgresql://goatcounter:your-password@postgres:5432/goatcounter?sslmode=disable
    depends_on:
      - postgres
    restart: always

  postgres:
    image: postgres:17-alpine
    container_name: goatcounter-postgres
    volumes:
      - goatcounter-pg-data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=goatcounter
      - POSTGRES_PASSWORD=your-password
      - POSTGRES_DB=goatcounter
    restart: always

volumes:
  goatcounter-pg-data:
```

For SQLite (single-container, simplest setup):

```yaml
services:
  goatcounter:
    image: arp242/goatcounter:latest
    container_name: goatcounter
    ports:
      - "8080:8080"
    volumes:
      - goatcounter-data:/home/goatcounter/goatcounter-data
    command: ["-automigrate", "-listen", "0.0.0.0:8080", "-db", "sqlite:///home/goatcounter/goatcounter-data/goatcounter.db"]
    restart: always

volumes:
  goatcounter-data:
```

Initialize the first site:

```bash
docker compose exec goatcounter goatcounter create -domain your-domain.com -email admin@example.com
```

### Tracking Script

```html
<script data-goatcounter="https://your-goatcounter-domain.com/count"
        async src="https://your-goatcounter-domain.com/count.js"></script>
```

### Resource Requirements

GoatCounter with SQLite uses **under 30 MB of RAM** — the lightest of all three options. The Docker image is approximately **15 MB**. With PostgreSQL, expect **100-150 MB** total.

## Architecture Comparison

| Aspect | Ackee | Fathom Lite | GoatCounter |
|--------|-------|-------------|-------------|
| **Runtime** | Node.js 18+ | Go (compiled) | Go (compiled) |
| **Database** | MongoDB | MySQL or SQLite | SQLite or PostgreSQL |
| **Frontend** | React dashboard | Preact SPA | Server-rendered HTML |
| **Data Retention** | Unlimited | Unlimited | Unlimited (configurable) |
| **Concurrent Users** | Moderate | High | High |
| **Horizontal Scaling** | Yes (stateless app) | Yes (stateless app) | Limited (SQLite) / Yes (PostgreSQL) |
| **Backup Complexity** | MongoDB dump | SQL dump | Single file (SQLite) / SQL dump |

Ackee's MongoDB architecture provides excellent read performance for dashboard queries but requires more operational knowledge. Fathom and GoatCounter's Go-based single-binary approach is simpler to deploy and maintain.

## Reverse Proxy Configuration (Nginx)

All three tools should sit behind a reverse proxy with TLS termination. Here is an Nginx configuration template:

```nginx
server {
    listen 443 ssl http2;
    server_name analytics.your-domain.com;

    ssl_certificate /etc/letsencrypt/live/analytics.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/analytics.your-domain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Replace `8080` with `3000` for Ackee's default port.

## Which One Should You Choose?

**Choose Ackee if:**
- You want a polished, modern dashboard with real-time updates
- You need GraphQL API access for custom integrations
- You already run MongoDB in your infrastructure
- You value UI aesthetics and don't mind higher resource usage

**Choose Fathom Lite if:**
- You want a balance between simplicity and features
- You prefer MySQL/SQLite over MongoDB
- You want the most popular option (8,000+ GitHub stars)
- You need a small Docker footprint (~25 MB image)

**Choose GoatCounter if:**
- You want the absolute lightest analytics tool possible
- You prefer SQLite for simplicity or PostgreSQL for scale
- You want the smallest tracking script (~600 bytes)
- You value simplicity over dashboard aesthetics

## FAQ

### Do these tools require cookie consent banners?

No. All three tools — Ackee, Fathom, and GoatCounter — are designed to be privacy-compliant without cookies. They use anonymized identifiers that cannot be linked back to individual users. Under GDPR and ePrivacy regulations, this means you typically do **not** need a cookie consent banner. However, you should still include a privacy policy explaining what data you collect.

### Can I migrate data between these tools?

Direct migration is not straightforward because each tool uses a different database schema and data model. However, all three offer APIs for data export and import. The most practical approach is to run your preferred tool going forward and keep historical data in the old system for reference.

### How much traffic can these tools handle?

GoatCounter with SQLite can comfortably handle **100,000+ page views per month** on a small VPS. Fathom Lite with MySQL scales to **millions of page views** with proper indexing. Ackee's MongoDB backend can handle high traffic but may need indexing tuning for very large datasets. For extremely high-traffic sites (10M+ page views/month), consider the PostgreSQL backend for GoatCounter or a dedicated MySQL instance for Fathom.

### Can I track multiple websites with one instance?

Yes, all three tools support multi-site tracking. You create separate "sites" or "domains" within a single installation, and each gets its own tracking script with a unique identifier. The dashboard lets you switch between sites.

### Are these tools GDPR compliant?

Yes, by design. All three tools anonymize IP addresses, do not set tracking cookies, and do not collect personally identifiable information. This puts them in the "legitimate interest" category under GDPR, meaning no explicit consent is required. However, you should still disclose analytics usage in your privacy policy and offer an opt-out mechanism if required by local law.

### What happens if I self-host on a low-resource VPS?

GoatCounter with SQLite is the best choice for resource-constrained environments. It runs in under 30 MB of RAM and uses a single SQLite file for storage. A $5/month VPS with 1 GB RAM can easily run GoatCounter alongside other services. Fathom Lite with SQLite is the second-lightest option at under 50 MB.

### Do these tools support custom event tracking?

Yes. Ackee supports custom events through its GraphQL API — you can track any action by calling the API. Fathom Lite supports custom events through its tracking script's `trackGoal()` function. GoatCounter supports custom events through manual API calls or by using its counting endpoint with custom paths.

### Can I share analytics dashboards publicly?

All three tools support public dashboard sharing. You can generate a public URL that displays your analytics data without requiring a login. This is useful for transparency reports, open-source project metrics, or sharing with stakeholders.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Ackee vs Fathom vs GoatCounter: Lightweight Privacy-Focused Web Analytics 2026",
  "description": "Compare Ackee, Fathom, and GoatCounter — three lightweight, privacy-focused, self-hosted web analytics tools. Docker setup, feature comparison, and deployment guide for 2026.",
  "datePublished": "2026-04-22",
  "dateModified": "2026-04-22",
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
