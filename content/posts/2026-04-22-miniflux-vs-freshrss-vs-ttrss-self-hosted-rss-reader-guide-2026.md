---
title: "Miniflux vs FreshRSS vs Tiny Tiny RSS: Best Self-Hosted RSS Reader 2026"
date: 2026-04-22
tags: ["comparison", "guide", "self-hosted", "rss", "feed-reader", "privacy"]
draft: false
description: "Compare the top three self-hosted RSS readers: Miniflux, FreshRSS, and Tiny Tiny RSS. Full Docker deployment guides, feature comparison, and performance benchmarks."
---

RSS feeds remain one of the most reliable ways to stay informed without relying on algorithmic timelines or tracking-heavy platforms. When you self-host an RSS reader, you control your data, eliminate ads, and build a personalized news pipeline that no corporation can interrupt.

This guide compares three mature, open-source self-hosted RSS readers: **Miniflux**, **FreshRSS**, and **Tiny Tiny RSS (TTRSS)**. Each has a distinct philosophy — from Miniflux's minimalist approach to FreshRSS's feature-rich ecosystem to TTRSS's long-standing community fork.

## Quick Comparison

| Feature | Miniflux | FreshRSS | Tiny Tiny RSS |
|---------|----------|----------|---------------|
| **Language** | Go | PHP | PHP |
| **Database** | PostgreSQL | SQLite / MySQL / PostgreSQL | PostgreSQL / MySQL |
| **GitHub Stars** | 9,104 | 14,832 | 705 (official) / 2,595 (fork) |
| **Last Updated** | April 2026 | April 2026 | April 2026 |
| **License** | Apache 2.0 | AGPL-3.0 | GPL-3.0 |
| **Mobile Apps** | Yes (iOS, Android, F-Droid) | Yes (iOS, Android, F-Droid) | Yes (via API) |
| **Themes** | Built-in dark/light | 20+ user-contributed themes | Community themes |
| **Extensions** | No | Yes (plugin system) | Yes (plugin system) |
| **API** | REST + Fever | Google Reader API / Fever | TTRSS API |
| **Resource Usage** | Very Low (Go binary) | Moderate (PHP + web server) | Moderate (PHP + web server) |
| **Best For** | Minimalists, low-resource servers | Power users, team collaboration | Long-time TTRSS ecosystem users |

## Why Self-Host an RSS Reader?

Commercial feed aggregators like Feedly, Inoreader, and The Old Reader have improved over the years, but they come with trade-offs:

- **Privacy concerns**: They track which articles you read, how long you linger, and build reading profiles
- **Feature limits**: Free tiers cap feeds, folders, and refresh frequency
- **Shutdown risk**: Google Reader's 2013 closure affected millions; smaller services disappear regularly
- **Algorithmic filtering**: Some platforms prioritize "engagement" over chronology
- **Vendor lock-in**: Exporting OPML is easy, but bookmarks, annotations, and reading history are not

Self-hosting solves all of these. Your reader runs on your server, your feeds refresh on your schedule, and your reading data never leaves your infrastructure. With Docker, setup takes minutes.

## Miniflux — Minimalist and Opinionated

Miniflux is built on a clear philosophy: do one thing well. Written in Go, it runs as a single binary with PostgreSQL as its only dependency. The interface is clean, fast, and free of clutter.

**Key strengths:**

- Extremely lightweight — uses under 50MB RAM on a typical instance
- Built-in Fever API and native REST API for third-party clients
- Keyboard-driven navigation (vim-style j/k keys)
- Full-text fetch option for sites that only provide summaries
- Native integration with services like Pinboard, Wallabag, and Nominatim
- Automatic YouTube video embedding for video feed entries
- OPML import/export for easy migration

**Drawbacks:**

- No plugin or extension system — what you see is what you get
- Requires PostgreSQL (no SQLite support)
- Minimal theming options
- No built-in user registration (admin creates accounts)

### Miniflux Docker Compose Deployment

Miniflux requires a PostgreSQL database. Here is a complete deployment:

```yaml
version: "3"

services:
  miniflux-db:
    image: postgres:16-alpine
    container_name: miniflux-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: miniflux
      POSTGRES_PASSWORD: miniflux-secret-change-me
      POSTGRES_DB: miniflux
    volumes:
      - miniflux-db:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "miniflux"]
      interval: 10s
      start_period: 30s

  miniflux:
    image: miniflux/miniflux:latest
    container_name: miniflux
    restart: unless-stopped
    depends_on:
      miniflux-db:
        condition: service_healthy
    ports:
      - "8080:8080"
    environment:
      DATABASE_URL: postgres://miniflux:miniflux-secret-change-me@miniflux-db/miniflux?sslmode=disable
      RUN_MIGRATIONS: "1"
      CREATE_ADMIN: "1"
      ADMIN_USERNAME: admin
      ADMIN_PASSWORD: admin-secret-change-me
    healthcheck:
      test: ["CMD", "/usr/bin/miniflux", "-healthcheck", "auto"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  miniflux-db:
```

After starting with `docker compose up -d`, Miniflux runs its database migrations automatically, creates the admin account, and is accessible at `http://localhost:8080`.

To add a reverse proxy with Caddy:

```yaml
  caddy:
    image: caddy:2-alpine
    container_name: miniflux-caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config

volumes:
  caddy_data:
  caddy_config:
```

With this `Caddyfile`:

```
rss.example.com {
    reverse_proxy miniflux:8080
}
```

## FreshRSS — Feature-Rich and Extensible

FreshRSS is the most popular self-hosted RSS reader by GitHub stars, and for good reason. It supports multiple databases, offers a rich plugin ecosystem, and provides a polished web interface that rivals commercial alternatives.

**Key strengths:**

- Supports SQLite, MySQL, and PostgreSQL — choose based on your infrastructure
- Extensive extension system with 50+ community plugins
- Google Reader API compatibility (works with most RSS apps)
- Built-in feed discovery and OPML import
- User management with registration (open or closed)
- Custom CSS themes and WebSub (PubSubHubbub) support
- Bookmarking, tagging, and article filtering
- Cron-based or PSHB-based feed refresh

**Drawbacks:**

- Heavier resource footprint than Miniflux (PHP + web server required)
- Plugin quality varies — some are unmaintained
- Web interface can feel busy with many feeds
- Database schema changes occasionally require manual intervention

### FreshRSS Docker Compose Deployment

FreshRSS provides official Docker Compose files in its `Docker/freshrss/` directory. Here is a complete stack with PostgreSQL:

```yaml
volumes:
  freshrss-data:
  freshrss-extensions:
  freshrss-db:

services:
  freshrss-db:
    image: postgres:18
    container_name: freshrss-db
    restart: unless-stopped
    volumes:
      - freshrss-db:/var/lib/postgresql
    environment:
      POSTGRES_DB: freshrss
      POSTGRES_USER: freshrss
      POSTGRES_PASSWORD: freshrss-secret-change-me
    command:
      - -c
      - shared_buffers=512MB
      - -c
      - work_mem=16MB

  freshrss:
    image: freshrss/freshrss:latest
    container_name: freshrss
    restart: unless-stopped
    volumes:
      - freshrss-data:/var/www/FreshRSS/data
      - freshrss-extensions:/var/www/FreshRSS/extensions
    environment:
      TZ: UTC
      CRON_MIN: '5,35'
      TRUSTED_PROXY: 172.16.0.0/12 192.168.0.0/16
      CRON_TOKEN: change-this-cron-token
    depends_on:
      - freshrss-db
    labels:
      traefik.enable: true
      traefik.http.routers.freshrss.rule: Host(`rss.example.com`)
      traefik.http.routers.freshrss.tls: true
```

FreshRSS uses a cron-based feed refresh by default (configured via `CRON_MIN`). For real-time updates, enable WebSub support in the settings.

To configure FreshRSS via the web installer, navigate to `http://localhost:80` (or your proxy URL) and follow the setup wizard. Alternatively, use the CLI:

```bash
docker exec freshrss ./cli/do-install.php \
  --default_user admin \
  --password admin-secret-change-me \
  --api_enabled 1 \
  --base_url https://rss.example.com
```

## Tiny Tiny RSS — The Community Fork

Tiny Tiny RSS (TTRSS) is one of the oldest self-hosted readers, originally created by Andrew Dolgov. The official repository (`tt-rss/tt-rss`, 705 stars) remains active but development has slowed. The community-maintained fork by HenryQW (`Awesome-TTRSS`, 2,595 stars) is the recommended deployment path, offering Docker images, Mercury full-text extraction, and RSS-Bridge integration.

**Key strengths:**

- Mature codebase with over a decade of development
- Active community fork with regular Docker image updates
- Mercury integration for full-text extraction of partial feeds
- Multi-user support with per-user themes and plugins
- Fever and Google Reader API compatibility
- Plugin ecosystem for filtering, auto-tagging, and more

**Drawbacks:**

- The official project has slower development velocity
- Community fork is maintained by a single developer
- Interface feels dated compared to FreshRSS
- Plugin API changes between versions can break extensions
- Heavier setup than Miniflux

### TTRSS Docker Compose Deployment

The HenryQW/Awesome-TTRSS fork provides a complete multi-service stack:

```yaml
volumes:
  cache:
  database.postgres:

networks:
  public_access:
  service_only:
  database_only:

services:
  service.ttrss:
    image: wangqiru/ttrss:nightly
    container_name: ttrss
    ports:
      - "181:80"
    environment:
      - SELF_URL_PATH=https://rss.example.com
      - DB_PASS=ttrss-secret-change-me
      - PUID=1000
      - PGID=1000
    volumes:
      - cache:/var/www/cache/
    networks:
      - public_access
      - service_only
      - database_only
    depends_on:
      - database.postgres
    restart: always

  database.postgres:
    image: postgres:16-alpine
    container_name: postgres
    environment:
      - POSTGRES_PASSWORD=ttrss-secret-change-me
    volumes:
      - database.postgres:/var/lib/postgresql/data
    networks:
      - database_only
    restart: always

  service.mercury:
    image: wangqiru/mercury-parser-api:latest
    container_name: mercury
    networks:
      - service_only
    expose:
      - "3000"
    restart: always

  service.opencc:
    image: wangqiru/opencc-api-server:latest
    container_name: opencc
    environment:
      - SERVER_PORT=3000
    networks:
      - service_only
    expose:
      - "3000"
    restart: always
```

This stack includes Mercury Parser for full-text extraction and OpenCC for Chinese text conversion. For most users, the Mercury service is the most useful addition.

## Performance and Resource Comparison

Resource consumption matters when running services on low-cost VPS instances or Raspberry Pi devices.

| Metric | Miniflux | FreshRSS | TTRSS |
|--------|----------|----------|-------|
| **Idle RAM** | ~30MB | ~120MB (PHP-FPM + Nginx) | ~100MB (PHP-FPM + Nginx) |
| **Docker Image Size** | ~30MB (distroless) | ~250MB (Alpine PHP) | ~350MB (with Mercury) |
| **Feed Refresh (100 feeds)** | ~2 seconds | ~8 seconds | ~10 seconds |
| **Database Size (10K articles)** | ~50MB | ~80MB | ~70MB |
| **Startup Time** | < 1 second | ~3 seconds | ~5 seconds |

Miniflux is the clear winner for resource-constrained environments. Its Go binary starts instantly and consumes minimal memory. FreshRSS and TTRSS require a PHP runtime and web server, adding overhead but providing more features.

## Choosing the Right Reader

**Pick Miniflux if:**
- You want the simplest, most reliable setup
- You run on limited hardware (Raspberry Pi, low-cost VPS)
- You prefer keyboard navigation and minimal interfaces
- You only need core RSS functionality without extensions

**Pick FreshRSS if:**
- You want a polished, feature-complete web interface
- You need user registration and multi-user support
- You value the plugin ecosystem and theme variety
- You want Google Reader API compatibility for mobile apps

**Pick TTRSS if:**
- You are already invested in the TTRSS ecosystem
- You need Mercury full-text extraction built in
- You want the most mature plugin architecture
- You prefer the community fork's Docker convenience

For related reading, see our [Huginn vs n8n automation guide](../huginn-vs-n8n-vs-activepieces-self-hosted-ifttt-alternatives-2026/) for automating feed-based workflows, our [privacy search engines comparison](../searxng-vs-whoogle-vs-librex-self-hosted-privacy-search-engines-2026/) for a complete privacy stack, and our [privacy stack guide](../privacy-stack-guide/) for building a full self-hosted privacy toolkit.

## FAQ

### What is the difference between RSS and Atom feeds?

Both are XML-based formats for publishing frequently updated content. RSS (Really Simple Specification) is more widely supported and comes in versions 0.91, 1.0, and 2.0. Atom is a newer standard (IETF RFC 4287) that addresses some RSS limitations, such as better date handling and more explicit content types. All three readers support both formats transparently.

### Can I migrate from Feedly or Inoreader to a self-hosted reader?

Yes. Both Feedly and Inoreader support OPML export, which is the standard format for importing feeds into any RSS reader. Export your OPML file from your current service, then import it into Miniflux, FreshRSS, or TTRSS. Your reading history and bookmarks will not transfer, but all your feed subscriptions will.

### Do these readers support podcasts and video feeds?

All three readers handle media enclosures in feeds. Miniflux has built-in YouTube video playback within the reader. FreshRSS supports podcast feeds with audio playback through its web interface. TTRSS handles media attachments and can display them with the appropriate plugins. For dedicated podcast management, consider pairing your RSS reader with a podcast-specific client that connects via the Fever or Google Reader API.

### How often do self-hosted readers check for new feeds?

Feed refresh frequency is configurable. FreshRSS uses cron intervals (default: every 5 and 35 minutes). Miniflux runs a built-in scheduler that checks feeds based on your configured interval (default: every 60 minutes). TTRSS uses `update_daemon_interval` in its configuration, typically set to 30-60 minutes. For real-time updates, FreshRSS supports WebSub (PubSubHubbub) which allows feed publishers to push updates immediately.

### Can multiple users share a single self-hosted RSS instance?

FreshRSS and TTRSS support multi-user setups with separate accounts, preferences, and feed subscriptions. Miniflux also supports multiple users but requires the admin to create each account manually — there is no self-registration by default. For household or team use, FreshRSS offers the most convenient user management with optional open registration.

### How do I back up my self-hosted RSS reader?

For Miniflux, back up the PostgreSQL database with `pg_dump`. For FreshRSS, back up the `data` volume and the database. For TTRSS, back up the PostgreSQL volume. All readers support OPML export, which is useful for portable feed list backups. A simple cron job running `docker exec <db-container> pg_dump` on a schedule provides automated database backups.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Miniflux vs FreshRSS vs Tiny Tiny RSS: Best Self-Hosted RSS Reader 2026",
  "description": "Compare the top three self-hosted RSS readers: Miniflux, FreshRSS, and Tiny Tiny RSS. Full Docker deployment guides, feature comparison, and performance benchmarks.",
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
