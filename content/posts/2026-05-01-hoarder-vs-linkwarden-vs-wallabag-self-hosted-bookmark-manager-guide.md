---
title: "Hoarder vs Linkwarden vs Wallabag — Self-Hosted Bookmark Managers (2026)"
date: 2026-05-01T02:30:00Z
tags: ["bookmark-manager", "self-hosted", "read-later", "knowledge-management", "docker"]
draft: false
---

If you are drowning in browser tabs, saved links, and "I will read this later" bookmarks, a self-hosted bookmark manager is the answer. This guide compares **Hoarder** (the rising star with AI tagging), **Linkwarden** (collaborative link collection), and **Wallabag** (the mature read-later workhorse) so you can pick the right tool for your workflow.

Hoarder ([github.com/hoarder-app/hoarder](https://github.com/hoarder-app/hoarder)) has **24,900+ GitHub stars** and was last updated in April 2026, making it one of the fastest-growing self-hosted bookmark tools in the ecosystem.

---

## What Is a Self-Hosted Bookmark Manager?

A self-hosted bookmark manager is a web application you run on your own server that stores, organizes, and retrieves your saved links, articles, and notes. Unlike browser bookmarks or cloud services (Pocket, Raindrop.io), self-hosted tools give you full data ownership, no subscription fees, and the ability to add custom integrations.

## Quick Comparison Table

| Feature | Hoarder | Linkwarden | Wallabag |
|---------|---------|------------|----------|
| **GitHub Stars** | 24,900+ | 8,800+ | 10,800+ |
| **License** | AGPL-3.0 | AGPL-3.0 | MIT |
| **Language** | TypeScript/Next.js | TypeScript | PHP |
| **Database** | SQLite/PostgreSQL | PostgreSQL | PostgreSQL/MySQL/SQLite |
| **Full-Text Search** | Yes (Meilisearch) | Yes | Yes |
| **AI Tagging** | Yes (built-in) | No | No |
| **Screenshot Capture** | Yes | Yes | No |
| **Collaboration** | No | Yes (collections) | No |
| **REST API** | Yes | Yes | Yes |
| **Mobile Apps** | Community | Community | Official iOS/Android |
| **Docker Support** | Official compose | Official compose | Official image |
| **Archive Formats** | PDF, screenshot, text | PDF, screenshot | PDF, text |

## Hoarder — AI-Powered Bookmark Everything

Hoarder is the newest entrant and arguably the most ambitious. It goes beyond traditional bookmarking by combining link saving, note-taking, image archiving, and **automatic AI-based tagging** in a single interface.

### Key Features

- **Automatic AI tagging** — saves bookmarks and assigns tags using an LLM (OpenAI, Ollama, or any OpenAI-compatible endpoint)
- **Full-text search** via Meilisearch — find anything instantly across all saved content
- **Screenshot capture** — uses headless Chrome to take full-page screenshots of saved pages
- **Three archive formats** — saves each bookmark as PDF, screenshot, and extracted text
- **Chrome/Firefox extension** — one-click save from the browser
- **Tags and lists** — organize with automatic AI-generated tags plus manual categorization

### Docker Compose Setup

```yaml
services:
  web:
    image: ghcr.io/hoarder-app/hoarder:release
    restart: unless-stopped
    volumes:
      - data:/data
    ports:
      - 3000:3000
    env_file:
      - .env
    environment:
      MEILI_ADDR: http://meilisearch:7700
      BROWSER_WEB_URL: http://chrome:9222
      DATA_DIR: /data
  chrome:
    image: gcr.io/zenika-hub/alpine-chrome:124
    restart: unless-stopped
    command:
      - --no-sandbox
      - --disable-gpu
      - --disable-dev-shm-usage
      - --remote-debugging-address=0.0.0.0
      - --remote-debugging-port=9222
      - --hide-scrollbars
  meilisearch:
    image: getmeili/meilisearch:v1.41.0
    restart: unless-stopped
    env_file:
      - .env
    environment:
      MEILI_NO_ANALYTICS: "true"
    volumes:
      - meilisearch:/meili_data

volumes:
  meilisearch:
  data:
```

The `.env` file should contain your Meilisearch master key and optional `OPENAI_API_KEY` for AI tagging. Without an AI key, Hoarder still works — you just lose automatic tagging.

### When to Choose Hoarder

- You want the most modern UI with AI-powered organization
- Screenshot archiving matters to you (visual bookmarks)
- You are comfortable with a newer, actively developed project

## Linkwarden — Collaborative Link Collection

Linkwarden focuses on collaborative knowledge gathering. It lets teams and individuals create shared collections of links with full-page archives.

### Key Features

- **Collections** — organize bookmarks into shareable groups
- **Team collaboration** — multiple users can contribute to shared collections
- **Full-page archival** — saves PDF and screenshot of every link
- **Tagging and search** — manual tags with full-text search across archives
- **Browser extension** — Chrome and Firefox support
- **Public sharing** — share collections via public URLs

### Docker Compose Setup

```yaml
services:
  linkwarden:
    image: ghcr.io/linkwarden/linkwarden:latest
    restart: unless-stopped
    ports:
      - 3000:3000
    environment:
      DATABASE_URL: postgresql://linkwarden:password@postgres:5432/linkwarden
      NEXTAUTH_SECRET: your-secret-key-here
      NEXTAUTH_URL: http://localhost:3000
    depends_on:
      - postgres
    volumes:
      - lwd-data:/data/data

  postgres:
    image: postgres:16
    restart: unless-stopped
    environment:
      POSTGRES_USER: linkwarden
      POSTGRES_PASSWORD: password
      POSTGRES_DB: linkwarden
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  lwd-data:
  pgdata:
```

### When to Choose Linkwarden

- You need team collaboration on shared bookmark collections
- You want a polished, modern UI with public sharing
- PostgreSQL as the database is a requirement for your infrastructure

## Wallabag — The Mature Read-Later Workhorse

Wallabag has been around since 2013 and is the most battle-tested option. It is a self-hosted alternative to Pocket with a strong focus on content readability.

### Key Features

- **Content extraction** — strips ads and clutter, presents clean readable articles
- **Full-text search** — search across all saved article content
- **Tagging system** — manual tags with annotation support
- **Official mobile apps** — native iOS and Android applications
- **RSS feeds** — generate RSS feeds from your saved articles
- **EPUB/PDF export** — export articles for offline reading
- **REST API** — extensive API for integrations
- **Multiple database support** — PostgreSQL, MySQL, or SQLite

### Docker Compose Setup

```yaml
services:
  wallabag:
    image: wallabag/wallabag:latest
    restart: unless-stopped
    ports:
      - 80:80
    environment:
      - SYMFONY__ENV__DATABASE_DRIVER=pdo_sqlite
      - SYMFONY__ENV__DOMAIN_NAME=http://localhost
    volumes:
      - wallabag-data:/var/www/wallabag/data
      - wallabag-images:/var/www/wallabag/web/assets/images

volumes:
  wallabag-data:
  wallabag-images:
```

### When to Choose Wallabag

- You want the most mature, stable platform with years of development
- Official mobile apps are important to your workflow
- You need EPUB export for e-reader compatibility
- SQLite-only deployment keeps things simple

## Advanced: Reverse Proxy Configuration

For production deployments, put your bookmark manager behind a reverse proxy with HTTPS. Here is a Traefik configuration example for Hoarder:

```yaml
services:
  web:
    image: ghcr.io/hoarder-app/hoarder:release
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.hoarder.rule=Host(`hoarder.example.com`)"
      - "traefik.http.routers.hoarder.tls=true"
      - "traefik.http.routers.hoarder.tls.certresolver=letsencrypt"
      - "traefik.http.services.hoarder.loadbalancer.server.port=3000"
    networks:
      - proxy
```

For more reverse proxy options, see our [guide on Caddy vs Traefik vs Nginx Proxy Manager](../2026-04-24-nginx-proxy-manager-vs-swag-vs-caddy-docker-proxy-self-hosted-reverse-proxy-gui-guide/). For note-taking integration, see our [Joplin vs Trilium vs Affine guide](../2026-04-21-joplin-vs-trilium-vs-affine-self-hosted-note-taking-guide-2026/).

## Why Self-Host Your Bookmarks?

Cloud bookmark services like Pocket and Raindrop.io are convenient, but they come with trade-offs. Your reading history, saved links, and personal notes live on someone else's servers. Self-hosting eliminates these concerns:

- **Data ownership** — every saved link, tag, and note is on your server
- **No subscription fees** — run indefinitely without monthly charges
- **No service shutdown risk** — remember when Google Reader died? Self-hosted tools do not get discontinued by corporate decisions
- **Custom integrations** — hook into your existing homelab with webhooks and APIs
- **Privacy** — your browsing history and interests are not tracked or monetized

For a broader look at self-hosted privacy tools, see our [complete privacy stack guide](../privacy-stack-guide/). If you are building a home server to run these tools, check our [CasaOS vs Umbrel vs Yunohost comparison](../2026-04-21-casaos-vs-umbrel-vs-yunohost-self-hosted-home-server-os-guide/) for the easiest starting point.

## FAQ

### Q: Is Hoarder safe to self-host for production use?

A: Hoarder is relatively new compared to Wallabag, but it has 24,900+ GitHub stars and active development. For personal use it is perfectly fine. For mission-critical production, Wallabag has a longer track record.

### Q: Can Hoarder work without an OpenAI API key?

A: Yes. Hoarder functions fully as a bookmark manager without AI. The AI tagging is an optional enhancement. You can also use local models via Ollama or any OpenAI-compatible endpoint to avoid API costs.

### Q: Which bookmark manager has the best mobile support?

A: Wallabag wins here with official iOS and Android apps. Hoarder and Linkwarden rely on community-built mobile apps or the responsive web interface.

### Q: Can I import bookmarks from my browser or Pocket?

A: All three tools support importing HTML bookmark exports from browsers. Wallabag also has a dedicated Pocket importer. Hoarder and Linkwarden support importing from other bookmark services via their import tools.

### Q: Do any of these support annotation and highlighting?

A: Wallabag supports article annotations. Linkwarden supports notes on individual links. Hoarder supports notes on saved items. None provide full highlighting like Hypothesis, but all allow you to add personal notes to saved content.

### Q: Which is the most resource-efficient?

A: Wallabag with SQLite uses the least resources — a single container with no external database. Hoarder requires Meilisearch and Chrome containers for full functionality. Linkwarden needs PostgreSQL. For low-resource environments, Wallabag is the lightest option.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Hoarder vs Linkwarden vs Wallabag — Self-Hosted Bookmark Managers (2026)",
  "description": "Compare Hoarder, Linkwarden, and Wallabag — three open-source self-hosted bookmark managers. Features, Docker setup, and when to choose each.",
  "datePublished": "2026-05-01",
  "dateModified": "2026-05-01",
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
