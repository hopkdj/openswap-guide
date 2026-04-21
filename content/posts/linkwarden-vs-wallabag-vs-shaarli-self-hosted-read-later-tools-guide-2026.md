---
title: "Linkwarden vs Wallabag vs Shaarli: Self-Hosted Read-Later Tools 2026"
date: 2026-04-21
tags: ["comparison", "guide", "self-hosted", "privacy", "bookmarks", "read-later"]
draft: false
description: "Compare Linkwarden, Wallabag, and Shaarli — three self-hosted solutions for saving, organizing, and reading web content later. Full Docker deployment guides included."
---

If you've ever bookmarked a page and never returned to it, you know the problem: browser bookmarks are disorganized, they don't preserve content when pages go offline, and there's no way to search across thousands of saved links. Self-hosted read-later tools solve this by archiving full page content, providing full-text search, and giving you complete control over your data.

In this guide, we compare three open-source options — **Linkwarden**, **Wallabag**, and **Shaarli** — each representing a different philosophy for managing saved web content.

## Why Self-Host Your Read-Later Library

Cloud services like Pocket, Instapaper, and Raindrop.io are convenient, but they come with real drawbacks:

- **Content can disappear** — if the service shuts down or removes a saved article, your library loses data
- **Privacy concerns** — these services read and index everything you save, building profiles from your reading habits
- **Feature limitations** — free tiers cap how many articles you can save or which features you can access
- **Vendor lock-in** — migrating thousands of saved articles between services is painful at best

Running your own read-later server on a home machine or VPI gives you permanent storage, full-text search across every saved page, and zero data sharing with third parties.

## The Three Contenders

### Linkwarden — Collaborative Link Archive

**GitHub:** [linkwarden/linkwarden](https://github.com/linkwarden/linkwarden) | **⭐ 18,056 stars** | **Last updated: 2026-04-01** | **Language: TypeScript**

Linkwarden is a modern, collaborative bookmark manager built for teams and individuals who want to collect, annotate, and preserve web content. It supports full page screenshots, PDF generation, nested collections, and real-time search powered by Meilisearch. Multiple users can share collections, making it ideal for research teams, study groups, or families.

Key features include full-text search with Meilisearch integration, collaborative collection sharing, automatic screenshot capture, PDF export for every saved page, browser extensions for Chrome and Firefox, and REST API access for integrations.

### Wallabag — Feature-Rich Read-Later Server

**GitHub:** [wallabag/wallabag](https://github.com/wallabag/wallabag) | **⭐ 12,638 stars** | **Last updated: 2026-04-20** | **Language: PHP**

Wallabag is the most mature read-later application in this comparison. It extracts the readable content from web pages, strips away ads and clutter, and presents articles in a clean reading view. With over a decade of development, it supports e-reader exports (EPUB, MOBI), tagging with automatic suggestions, mobile apps for Android and iOS, and a robust API that integrates with hundreds of third-party tools.

Its content extraction engine is based on Graby and Mozilla's Readability, providing reliable article parsing even from complex pages. Wallabag also supports tagging rules, starred articles, reading time estimates, and full-text search.

### Shaarli — Minimalist Bookmark Manager

**GitHub:** [shaarli/Shaarli](https://github.com/shaarli/Shaarli) | **⭐ 3,842 stars** | **Last updated: 2026-03-26** | **Language: PHP**

Shaarli takes a radically different approach: no database, no heavy dependencies, just a flat-file bookmark manager that runs on almost any PHP host. It is designed for speed and simplicity, making it the lightest option by far. You get tags, permalinks, private and public sharing, a REST API, and browser bookmarklets — all in a package that installs in under a minute.

The trade-off is that Shaarli does not archive page content or extract readable text. It stores URLs, titles, descriptions, and tags. If the original page goes offline, the link is gone. For users who need simple, fast bookmarking without the overhead of content extraction, Shaarli is unmatched.

## Head-to-Head Comparison

| Feature | Linkwarden | Wallabag | Shaarli |
|---|---|---|---|
| **Content archiving** | Full page + screenshot + PDF | Extracted readable text | URL only |
| **Database** | PostgreSQL | PostgreSQL / MySQL / SQLite | Flat file (no DB) |
| **Full-text search** | Yes (Meilisearch) | Yes | No |
| **Collaboration** | Multi-user, shared collections | Multi-user | Single user |
| **Mobile apps** | Web-responsive | Android + iOS apps | Web-responsive |
| **Browser extension** | Chrome, Firefox | Chrome, Firefox, others | Bookmarklet |
| **E-reader export** | No | EPUB, MOBI | No |
| **Tags** | Yes | Yes + auto-tagging rules | Yes |
| **REST API** | Yes | Yes | Yes |
| **Docker support** | Official image | Official image | Official image (GHCR) |
| **Reverse proxy** | Nginx, Caddy, Traefik | Nginx, Caddy, Apache | Nginx, Caddy, Apache |
| **Resource usage** | Medium (3 containers) | Medium-High (2-3 containers) | Minimal (1 container) |
| **Setup complexity** | Moderate | Moderate-High | Easy |

## Deploying Linkwarden with Docker

Linkwarden runs as a three-container stack: the app, PostgreSQL, and Meilisearch for full-text search.

### Step 1: Create the Docker Compose file

Create a `.env` file with your configuration:

```bash
# .env
NEXTAUTH_SECRET=your-secret-key-here
NEXTAUTH_URL=http://localhost:3000
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/postgres
MEILI_MASTER_KEY=your-meilisearch-master-key
MEILI_URL=http://meilisearch:7700
```

Then create `docker-compose.yml`:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    env_file: .env
    restart: always
    volumes:
      - ./pgdata:/var/lib/postgresql/data

  meilisearch:
    image: getmeili/meilisearch:v1.12.8
    restart: always
    env_file: .env
    volumes:
      - ./meili_data:/meili_data

  linkwarden:
    image: ghcr.io/linkwarden/linkwarden:latest
    env_file: .env
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/postgres
      - MEILI_URL=http://meilisearch:7700
    restart: always
    ports:
      - "3000:3000"
    volumes:
      - ./data:/data/data
    depends_on:
      - postgres
      - meilisearch
```

### Step 2: Start the service

```bash
docker compose up -d
```

Open `http://your-server-ip:3000` and create your admin account. The Meilisearch integration provides instant full-text search across all saved pages, including the content of PDFs and screenshots.

### Step 3: Install the browser extension

Linkwarden provides browser extensions for Chrome and Firefox that add a save button directly to your toolbar. When you click it, the page is archived with a screenshot and PDF copy, and added to your default collection.

### Step 4: Set up reverse proxy

For production access, put Linkwarden behind a reverse proxy. Here is a Caddy configuration:

```caddyfile
links.yourdomain.com {
    reverse_proxy localhost:3000
    encode gzip
}
```

## Deploying Wallabag with Docker

Wallabag requires more configuration but offers the deepest feature set of any open-source read-later tool.

### Step 1: Create the Docker Compose file

For a production setup with PostgreSQL:

```yaml
services:
  wallabag:
    image: wallabag/wallabag:latest
    container_name: wallabag
    restart: unless-stopped
    ports:
      - "8081:80"
    environment:
      - SYMFONY__ENV__DOMAIN_NAME=http://your-server-ip:8081
      - SYMFONY__ENV__SERVER_NAME=Wallabag
      - SYMFONY__ENV__DATABASE_DRIVER=pdo_pgsql
      - SYMFONY__ENV__DATABASE_HOST=postgres
      - SYMFONY__ENV__DATABASE_PORT=5432
      - SYMFONY__ENV__DATABASE_NAME=wallabag
      - SYMFONY__ENV__DATABASE_USER=wallabag
      - SYMFONY__ENV__DATABASE_PASSWORD=wallabag_secure_pass
      - SYMFONY__ENV__MAILER_DSN=smtp://mail.example.com:587
      - SYMFONY__ENV__FROM_EMAIL=wallabag@example.com
      - SYMFONY__ENV__SECRET=a-very-long-random-secret-string
    depends_on:
      - postgres

  postgres:
    image: postgres:16-alpine
    container_name: wallabag-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_USER=wallabag
      - POSTGRES_PASSWORD=wallabag_secure_pass
      - POSTGRES_DB=wallabag
    volumes:
      - ./postgres-data:/var/lib/postgresql/data
```

For a simpler test setup, you can use SQLite by changing the database driver to `pdo_sqlite` and removing the PostgreSQL container entirely. However, production deployments should always use PostgreSQL for reliability and concurrent access.

### Step 2: Initialize the admin user

After starting the containers, create the admin account:

```bash
docker exec -it wallabag /var/www/wallabag/bin/console wallabag:install --env=prod
docker exec -it wallabag /var/www/wallabag/bin/console wallabag:user:create admin admin@example.com password --env=prod
```

### Step 3: Configure article extraction

Wallabag uses Graby for content extraction. You can fine-tune extraction rules for specific sites by adding site configuration files to `data/site-config/`. This is useful for sites that are not parsed correctly out of the box.

### Step 4: Set up reverse proxy

Here is an Nginx configuration for Wallabag:

```nginx
server {
    listen 80;
    server_name read.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Deploying Shaarli with Docker

Shaarli is the simplest to deploy — it runs as a single container with no external database.

### Step 1: Create the Docker Compose file

```yaml
services:
  shaarli:
    image: ghcr.io/shaarli/shaarli:latest
    container_name: shaarli
    restart: unless-stopped
    ports:
      - "8082:80"
    volumes:
      - ./shaarli-data:/var/www/shaarli/data
      - ./shaarli-cache:/var/www/shaarli/cache
    environment:
      - TZ=UTC
      - SHAARLI_VIRTUAL_HOST=bookmarks.yourdomain.com
```

### Step 2: Start and configure

```bash
docker compose up -d
```

Open `http://your-server-ip:8082` and complete the setup wizard. You will create an admin account, set the instance name, and choose whether to make your bookmarks public or private.

### Step 3: Install the bookmarklet

Shaarli provides a bookmarklet that you drag to your browser toolbar. When you are on any page, click the bookmarklet to instantly save the URL with its title and a short description.

### Step 4: Import existing bookmarks

Shaarli can import bookmarks from Netscape HTML format (the standard browser export format), Delicious, Pocket CSV, and other Shaarli instances. Go to **Tools → Import** and upload your export file.

## Performance and Resource Comparison

On a minimal VPS with 1 GB of RAM:

- **Shaarli** uses approximately 30-50 MB of RAM as a single PHP process. It handles thousands of bookmarks without slowdown because there is no database query overhead.
- **Linkwarden** uses approximately 300-500 MB across its three containers (app, PostgreSQL, Meilisearch). Meilisearch is the largest consumer but provides instant search across all archived content.
- **Wallabag** uses approximately 250-400 MB with PostgreSQL. The PHP application itself is lightweight, but article extraction can spike CPU usage when processing complex pages.

For a Raspberry Pi or low-end VPS, Shaarli runs without issue. Linkwarden and Wallabag work fine on a Pi 4 with 4 GB of RAM or any $5/month cloud VPS.

## How to Choose

**Choose Linkwarden if** you need collaborative collections, full page archiving with screenshots and PDFs, and powerful search. It is the best choice for teams, researchers, and anyone who wants a visual record of saved pages. The Meilisearch integration makes finding old bookmarks effortless.

**Choose Wallabag if** your primary goal is reading articles later. Its content extraction engine produces the cleanest reading experience, and the EPUB/MOBI export lets you read saved articles on any e-reader. The mature plugin ecosystem connects Wallabag to email, RSS readers, note-taking apps, and automation tools.

**Choose Shaarli if** you want the simplest, fastest bookmark manager with zero infrastructure overhead. It is ideal for personal use, requires no database, runs on the cheapest hosting, and gets the job done without complexity. The trade-off is no content archiving — if a page goes offline, only the URL and your notes remain.

## Migration Paths

### From Pocket to Wallabag

Wallabag has a built-in Pocket importer. Go to **Settings → Import**, select Pocket, authorize the connection, and Wallabag will pull your entire Pocket library including tags and favorites.

### From browser bookmarks to any tool

All three tools accept Netscape HTML bookmark exports. In Chrome or Firefox, go to **Bookmarks → Export Bookmarks** to get an HTML file, then import it through the tool's admin panel.

### From Linkding to Linkwarden

If you are using Linkding, you can export bookmarks as a Netscape HTML file and import them into Linkwarden. Both tools support tags, so your organization structure transfers cleanly.

## Backup Strategies

Every self-hosted service needs a backup plan. Here is how to back up each tool:

```bash
#!/bin/bash
# backup-read-later.sh

# Linkwarden backup
docker exec linkwarden-postgres pg_dump -U postgres postgres > backups/linkward_db_$(date +%F).sql
tar czf backups/linkwarden_data_$(date +%F).tar.gz ./data ./meili_data

# Wallabag backup
docker exec wallabag-postgres pg_dump -U wallabag wallabag > backups/wallabag_db_$(date +%F).sql
tar czf backups/wallabag_data_$(date +%F).tar.gz ./postgres-data

# Shaarli backup
tar czf backups/shaarli_$(date +%F).tar.gz ./shaarli-data ./shaarli-cache

# Keep last 7 days of backups
find backups/ -name "*.sql" -mtime +7 -delete
find backups/ -name "*.tar.gz" -mtime +7 -delete
```

Run this script daily via cron to maintain rolling backups. Store copies off-site using rclone or a similar tool for disaster recovery.

## FAQ

### Can I use these tools without a dedicated server?

Yes. Shaarli runs on any shared PHP hosting for as little as $2/month. Linkwarden and Wallabag need a VPS with at least 1 GB of RAM — a $5/month DigitalOcean or Hetzner droplet is sufficient for personal use. You can also run all three on a home server or Raspberry Pi.

### Which tool offers the best reading experience?

Wallabag has the most polished reading interface. It strips ads, sidebars, and navigation elements from pages, leaving clean article text with proper typography. Linkwarden preserves the full page including screenshots, which is better for reference but not as clean for reading. Shaarli does not extract content at all.

### Can multiple people use the same instance?

Linkwarden and Wallabag both support multi-user setups with per-user collections and libraries. Shaarli is designed for a single user, though you can run multiple instances side by side for different users.

### How do I migrate from Pocket or Instapaper?

Wallabag has direct importers for both Pocket and Instapaper. For Linkwarden and Shaarli, export your bookmarks from Pocket as a Netscape HTML file (via a third-party tool like pocket-export) and then import them through the respective tool's import page.

### Do these tools work offline?

Wallabag stores extracted article content locally, so you can read saved articles even if the original pages go offline or you lose internet access. Linkwarden stores full page screenshots and PDFs locally. Shaarli only stores URLs, so you need internet access to view the actual pages.

### Can I access my library from mobile devices?

Wallabag offers official Android and iOS apps with offline reading support. Linkwarden has a responsive web interface that works well on mobile browsers. Shaarli also has a responsive design but no dedicated mobile app.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Linkwarden vs Wallabag vs Shaarli: Self-Hosted Read-Later Tools 2026",
  "description": "Compare three open-source self-hosted read-later and bookmark management tools — Linkwarden, Wallabag, and Shaarli — with full Docker deployment guides.",
  "datePublished": "2026-04-21",
  "dateModified": "2026-04-21",
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

For related reading, check out our [complete bookmark manager comparison with Linkding](../self-hosted-bookmark-managers-linkding-shaarli-wallabag/), the [self-hosted RSS reader guide](../self-hosted-rss-readers/), and the [web archiving tutorial with ArchiveBox](../self-hosted-web-archiving-archivebox-guide-2026/).
