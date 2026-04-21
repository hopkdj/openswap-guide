---
title: "Matomo vs Plausible vs Umami: Best Self-Hosted Web Analytics 2026"
date: 2026-04-13
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Compare Matomo, Plausible, and Umami for self-hosted web analytics. Complete setup guides, feature comparison, and migration tips for 2026."
---

## Why Self-Host Your Web Analytics?

Third-party analytics services like Google Analytics track your visitors across the web, harvest personal data, and subject you to increasingly com[plex](https://www.plex.tv/) compliance requirements. Self-hosting your analytics gives you full control:

- **Complete data ownership**: Every event, every session, every metric stays on your infrastructure
- **GDPR and privacy compliance**: No cross-site tracking, no fingerprinting, no cookie banners needed
- **No data sampling**: Get accurate numbers even at high traffic volumes
- **Cost predictability**: No surprise bills when your traffic spikes
- **Custom integrations**: Connect analytics to your internal dashboards, databases, and alerting systems
- **Ad-blocker resistance**: When analytics runs on your own domain, ad blockers can't distinguish it from your website

For blogs, e-commerce stores, SaaS products, and internal dashboards, self-hosted analytics is no longer a luxury — it's a sensible default.

## At a Glance: Matomo vs Plausible vs Umami

| Feature | Matomo | Plausible | Umami |
|---------|--------|-----------|-------|
| **Type** | Full analytics suite | Lightweight analytics | Minimalist analytics |
| **License** | GPL-3.0 (core) | AGPL-3.0 | MIT |
| **Backend** | PHP + MySQL/MariaDB | Elixir + PostgreSQL + ClickHouse | Node.js + PostgreSQL |
| **Frontend** | Vue.js / PHP | React | Next.js |
| **Cookie-based tracking** | Optional | No (cookieless) | No (cookieless) |
| **Script size** | ~40 KB | ~1 KB | ~2 KB |
| **Custom events** | Yes | Yes | Yes |
| **E-commerce tracking** | Yes | Yes (Business) | No |
| **Heatmaps** | Yes (plugin) | No | No |
| **A/B testing** | Yes (plugin) | No | No |
| **Multi-site** | Yes | Yes | Yes |
| **REST API** [docker](https://www.docker.com/)| Yes | Yes |
| **Docker support** | Yes | Yes | Yes |
| **Resource usage** | High (300-500 MB RAM) | Medium (150-300 MB) | Low (50-150 MB) |
| **Best for** | Enterprise, complex needs | Privacy-first blogs and SaaS | Personal projects and small sites |

## Matomo: The Full-Featured Analytics Powerhouse

Matomo (formerly Piwik) is the most comprehensive open-source web analytics platform available. It's a direct replacement for Google Analytics, offering nearly every feature you'd expect from a commercial analytics product — and then some.

### Key Strengths

Matomo's feature set is unmatched in the open-source analytics space. It includes real-time visitor maps, goal tracking, funnel analysis, e-commerce reports, custom dimensions, segment builder, user flow visualization, and an extensive plugin marketplace with over 100 extensions. Heatmaps, session recordings, A/B testing, and form analytics are all available as plugins.

For organizations migrating from Google Analytics, Matomo offers an import tool that brings your historical GA data directly into Matomo, preserving year-over-year comparisons.

### Docker Setup for Matomo

Matomo requires a PHP backend, a MySQL or MariaDB database, and optionally a Redis cache. Here's a production-ready Docker Compose configuration:

```yaml
version: "3.8"

services:
  db:
    image: mariadb:11
    command: --max-allowed-packet=64MB --innodb-buffer-pool-size=256M
    restart: unless-stopped
    volumes:
      - matomo-db:/var/lib/mysql
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: matomo
      MYSQL_USER: matomo
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
    healthcheck:
      test: ["CMD", "healthcheck.sh", "--connect", "--innodb_initialized"]
      interval: 10s
      timeout: 5s
      retries: 3

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --maxmemory 128mb --maxmemory-policy allkeys-lru
    volumes:
      - matomo-redis:/data

  matomo:
    image: matomo:5-apache
    restart: unless-stopped
    ports:
      - "8080:80"
    volumes:
      - matomo-data:/var/www/html
    environment:
      MATOMO_DATABASE_HOST: db
      MATOMO_DATABASE_ADAPTER: mysql
      MATOMO_DATABASE_TABLES_PREFIX: matomo_
      MATOMO_DATABASE_USERNAME: matomo
      MATOMO_DATABASE_PASSWORD: ${MYSQL_PASSWORD}
      MATOMO_DATABASE_DBNAME: matomo
      MATOMO_GENERAL_REDIS_CACHE: redis:6379
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started

volumes:
  matomo-db:
  matomo-redis:
  matomo-data:
```

Save this as `docker-compose.yml`, create a `.env` file with your passwords, and start the stack:

```bash
# Generate secure passwords
MYSQL_ROOT_PASSWORD=$(openssl rand -base64 32)
MYSQL_PASSWORD=$(openssl rand -base64 32)

# Create .env file
cat > .env << EOF
MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}
MYSQL_PASSWORD=${MYSQL_PASSWORD}
EOF

# Start the stack
docker compose up -d
```

After the containers start, visit `http://your-server:8080` to run the web-based installer. The setup wizard will guide you through creating the initial admin account and adding your first website.

### Tracking Code

Once configured, Matomo provides a JavaScript snippet to embed on every page:

```html
<!-- Matomo Analytics -->
<script>
  var _paq = window._paq = window._paq || [];
  _paq.push(['trackPageView']);
  _paq.push(['enableLinkTracking']);
  (function() {
    var u = "//analytics.yourdomain.com/";
    _paq.push(['setTrackerUrl', u + 'matomo.php']);
    _paq.push(['setSiteId', '1']);
    var d = document, g = d.createElement('script'),
        s = d.getElementsByTagName('script')[0];
    g.async = true;
    g.src = u + 'matomo.js';
    s.parentNode.insertBefore(g, s);
  })();
</script>
```

For cookieless tracking, add this line before `trackPageView`:

```[nginx](https://nginx.org/)cript
_paq.push(['disableCookies']);
```

### Nginx Reverse Proxy Configuration

Matomo works best behind a reverse proxy with HTTPS. Here's an Nginx configuration that also serves the tracking script from your own domain, making it invisible to ad blockers:

```nginx
server {
    listen 443 ssl http2;
    server_name analytics.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/analytics.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/analytics.yourdomain.com/privkey.pem;

    # Proxy to Matomo container
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Block access to sensitive paths
    location ~ /(\.git|config|temp) {
        deny all;
    }
}
```

## Plausible: Lightweight and Privacy-First

Plausible takes the opposite approach from Matomo. Instead of offering every possible feature, it focuses on doing one thing exceptionally well: providing clear, actionable website statistics without collecting personal data.

The tracking script is under 1 KB (minified and gzipped), making it one of the lightest analytics scripts available. Plausible uses no cookies, no persistent identifiers, and no cross-site tracking. All data is aggregated, meaning you get useful insights without individual visitor profiling.

### Key Strengths

Plausible excels at simplicity. The dashboard shows everything at a glance: total visitors, page views, bounce rate, session duration, top pages, referral sources, device breakdown, and geographic distribution — all on a single page. There are no nested menus, no configuration wizards, and no learning curve.

For teams, Plausible offers shared dashboard links, Slack and Discord email reports, and Google Search Console integration. The goal tracking and custom event support cover most use cases without complexity.

### Docker Setup for Plausible

Plausible requires PostgreSQL and ClickHouse as data backends. The official Plausible hosting image bundles everything:

```yaml
version: "3.8"

services:
  plausible_db:
    image: postgres:16-alpine
    restart: unless-stopped
    volumes:
      - plausible-db-data:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_USER: plausible
      POSTGRES_DB: plausible

  plausible_clickhouse:
    image: clickhouse/clickhouse-server:24.3
    restart: unless-stopped
    volumes:
      - plausible-clickhouse-data:/var/lib/clickhouse
      - plausible-clickhouse-config:/etc/clickhouse-server
    ulimits:
      nofile:
        soft: 262144
        hard: 262144

  plausible_events_db:
    image: altinity/clickhouse-server:24.3
    restart: unless-stopped
    volumes:
      - plausible-events-data:/var/lib/clickhouse
    depends_on:
      - plausible_clickhouse

  plausible:
    image: ghcr.io/plausible/community-edition:v2.1.5
    restart: unless-stopped
    ports:
      - "8000:8000"
    depends_on:
      - plausible_db
      - plausible_events_db
    environment:
      BASE_URL: https://analytics.yourdomain.com
      SECRET_KEY_BASE: ${SECRET_KEY_BASE}
      TOTP_VAULT_KEY: ${TOTP_VAULT_KEY}
      DATABASE_URL: postgresql://plausible:${DB_PASSWORD}@plausible_db:5432/plausible
      CLICKHOUSE_DATABASE_URL: http://plausible_events_db:8123/plausible_events_db

volumes:
  plausible-db-data:
  plausible-clickhouse-data:
  plausible-clickhouse-config:
  plausible-events-data:
```

Generate the required secrets:

```bash
# Generate secure keys
SECRET_KEY_BASE=$(openssl rand -base64 64)
TOTP_VAULT_KEY=$(openssl rand -base64 32)
DB_PASSWORD=$(openssl rand -base64 32)

cat > .env << EOF
SECRET_KEY_BASE=${SECRET_KEY_BASE}
TOTP_VAULT_KEY=${TOTP_VAULT_KEY}
DB_PASSWORD=${DB_PASSWORD}
EOF

docker compose up -d
```

Register your admin account:

```bash
docker compose exec plausible /entrypoint.sh db created-admin \
  --email "admin@yourdomain.com" \
  --password "your-secure-password" \
  --name "Admin User"
```

### Plausible Tracking Script

The Plausible script is remarkably simple:

```html
<script defer data-domain="yourdomain.com"
  src="https://analytics.yourdomain.com/js/script.js">
</script>
```

For outbound link and file download tracking:

```html
<script defer data-domain="yourdomain.com"
  src="https://analytics.yourdomain.com/js/script.outbound-links.js">
</script>
```

To proxy through your own domain (ad-blocker resistant), configure Nginx:

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    # Proxy Plausible analytics script
    location /analytics/js/script.js {
        proxy_pass http://127.0.0.1:8000/js/script.js;
        proxy_set_header Host analytics.yourdomain.com;
    }

    location /analytics/api/event {
        proxy_pass http://127.0.0.1:8000/api/event;
        proxy_set_header Host analytics.yourdomain.com;
    }
}
```

Then update your tracking script to use the proxied path:

```html
<script defer data-domain="yourdomain.com"
  src="https://yourdomain.com/analytics/js/script.js">
</script>
```

## Umami: Minimalist Analytics That Just Works

Umami is the simplest self-hosted analytics solution available. Built with Next.js and PostgreSQL, it offers a clean, modern dashboard with essential metrics and a tracking script under 2 KB. The MIT license means you can use it anywhere without restrictions.

### Key Strengths

Umami's standout feature is its simplicity. Installation takes minutes, the dashboard is intuitive, and the tracking script is tiny. It supports custom events, team sharing, and website-level access controls. The built-in share URLs let you publish public analytics dashboards — perfect for open-source projects and transparent companies.

Umami also offers real-time visitor tracking, device and browser breakdowns, OS detection, country-level geolocation, and referrer tracking. The event tracking API lets you record any custom action.

### Docker Setup for Umami

Umami has the simplest setup of the three. It only needs PostgreSQL:

```yaml
version: "3.8"

services:
  umami-db:
    image: postgres:16-alpine
    restart: unless-stopped
    volumes:
      - umami-db-data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: umami
      POSTGRES_USER: umami
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U umami -d umami"]
      interval: 5s
      timeout: 3s
      retries: 5

  umami:
    image: ghcr.io/umami-software/umami:postgresql-v2.16.0
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      DATABASE_URL: postgresql://umami:${DB_PASSWORD}@umami-db:5432/umami
      DATABASE_TYPE: postgresql
      HASH_SALT: ${HASH_SALT}
      TRACKER_SCRIPT_NAME: script.js
      DISABLE_TELEMETRY: "true"
    depends_on:
      umami-db:
        condition: service_healthy

volumes:
  umami-db-data:
```

Set up your environment and launch:

```bash
# Generate secrets
DB_PASSWORD=$(openssl rand -base64 32)
HASH_SALT=$(openssl rand -base64 32)

cat > .env << EOF
DB_PASSWORD=${DB_PASSWORD}
HASH_SALT=${HASH_SALT}
EOF

docker compose up -d
```

The default login credentials are `admin` / `umami`. **Change these immediately** after first login.

### Umami Tracking Script

Umami provides a simple tracking snippet:

```html
<script defer src="https://analytics.yourdomain.com/script.js"
  data-website-id="your-website-uuid">
</script>
```

You can customize the script endpoint name during setup to avoid ad-blocker detection:

```yaml
environment:
  TRACKER_SCRIPT_NAME: analytics.js  # or any name you prefer
```

For custom event tracking, use the `data-track-*` attributes:

```html
<button data-track-event="signup" data-track-label="homepage">
  Sign Up
</button>
```

Or use the JavaScript API for more complex scenarios:

```javascript
umami.track('download', { filename: 'report.pdf', size: '2.4MB' });
```

## Performance and Resource Comparison

Understanding resource requirements is critical when choosing an analytics stack. Here's how the three platforms compare under realistic load (approximately 100,000 page views per month):

| Metric | Matomo | Plausible | Umami |
|--------|--------|-----------|-------|
| **Idle RAM** | 300-500 MB | 150-300 MB | 50-150 MB |
| **Disk (1M events)** | 2-5 GB | 500 MB - 1 GB | 200-500 MB |
| **CPU during peak** | 1-2 cores | 0.5-1 core | 0.25-0.5 core |
| **Startup time** | 30-60 seconds | 15-30 seconds | 5-10 seconds |
| **Database queries per page view** | 5-10 | 1-2 | 1-2 |
| **VPS minimum** | 2 GB RAM | 1 GB RAM | 512 MB RAM |

For personal blogs and small projects, Umami runs comfortably on a $5/month VPS. Plausible needs slightly more headroom due to ClickHouse. Matomo requires the most resources but delivers the richest feature set in return.

## Migration from Google Analytics

If you're moving away from Google Analytics, here's how each platform handles the transition:

**Matomo** offers the most complete migration path. Its Google Analytics Importer plugin connects to your GA property via API, pulls historical data, and maps it to Matomo's data model. This includes campaign data, custom dimensions, goals, and e-commerce transactions. The import runs as a background process and can take several hours for large properties.

**Plausible** does not offer a direct import tool. However, you can run Plausible alongside Google Analytics during a transition period, using the `data-domain` attribute on the tracking script to maintain separate data streams. After a few months of parallel collection, you can confidently retire Google Analytics.

**Umami** similarly lacks a migration tool. The recommended approach is identical to Plausible: run both analytics systems simultaneously and phase out Google Analytics once you have sufficient Umami data.

## Which Should You Choose?

The decision comes down to your specific needs:

**Choose Matomo if:**
- You need comprehensive analytics comparable to Google Analytics
- E-commerce tracking, heatmaps, or session recordings are essential
- You have a dedicated server or VPS with at least 2 GB RAM
- Your team requires advanced segmentation, funnel analysis, and custom reports
- You want to import historical Google Analytics data

**Choose Plausible if:**
- You value simplicity and a clean dashboard over feature breadth
- Privacy compliance is a primary concern (GDPR, CCPA, PECR)
- You want cookieless analytics that works without consent banners
- You need team collaboration features and scheduled email reports
- Your site gets moderate to high traffic (10K-1M+ page views/month)

**Choose Umami if:**
- You want the simplest possible setup and maintenance
- You're running a personal blog, portfolio, or small business site
- You need a tiny tracking script that won't impact page load times
- You want to publish public analytics dashboards
- You're running on minimal hardware (512 MB RAM VPS or Raspberry Pi)

All three platforms are excellent open-source choices. The best approach is to spin up a Docker instance of your preferred option, add the tracking script to a staging version of your site, and evaluate the dashboard after a week of real traffic data.

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
