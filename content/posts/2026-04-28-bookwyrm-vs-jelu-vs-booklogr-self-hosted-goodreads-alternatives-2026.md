---
title: "BookWyrm vs Jelu vs BookLogr: Best Self-Hosted Goodreads Alternatives 2026"
date: 2026-04-28
tags: ["comparison", "guide", "self-hosted", "privacy", "books"]
draft: false
description: "Compare BookWyrm, Jelu, and BookLogr — three open-source, self-hosted alternatives to Goodreads for tracking your reading, managing your library, and sharing book reviews without corporate surveillance."
---

Goodreads has dominated the social reading space for over a decade, but its monopoly comes with well-documented downsides: privacy concerns, aggressive data collection, review bombing, and a UI that has barely improved since 2013. If you value control over your reading data and want to avoid corporate platforms mining your reading habits, self-hosted alternatives offer a compelling path forward.

This guide compares three open-source platforms — **BookWyrm**, **Jelu**, and **BookLogr** — each with a distinct approach to replacing Goodreads functionality on your own server.

## Why Self-Host a Reading Tracker

Your reading history reveals a surprising amount about your interests, political leanings, and personal life. A corporate platform like Goodreads monetizes this data through recommendation algorithms, targeted advertising, and data partnerships with publishers. Self-hosting your reading tracker eliminates these concerns entirely:

- **Complete data ownership** — your reading lists, ratings, and reviews never leave your server
- **No algorithmic manipulation** — no sponsored book placements or publisher-influenced rankings
- **Privacy-first design** — no tracking pixels, no cross-site profiling, no data brokering
- **Federation capability** — some platforms (like BookWyrm) connect to the wider fediverse via ActivityPub, letting you interact with readers on other instances without surrendering control
- **Long-term availability** — unlike cloud services that can shut down or change terms overnight, your self-hosted instance persists as long as you maintain it

For related reading, see our guide to [self-hosted ebook and audiobook library management](../self-hosted-ebook-audiobook-library-guide/) and [media tracker comparison](../yamtrack-vs-mediatracker-vs-movary-self-hosted-media-tracker-guide-2026/).

## BookWyrm: Decentralized Social Reading Platform

**BookWyrm** ([bookwyrm-social/bookwyrm](https://github.com/bookwyrm-social/bookwyrm), 2,690 stars) is the most ambitious Goodreads replacement in the self-hosted space. Built with Python/Django, it implements the ActivityPub protocol, enabling your instance to federate with other BookWyrm servers and compatible fediverse platforms.

### Key Features

- **ActivityPub federation** — follow users on other BookWyrm instances, share reviews across the fediverse, and participate in a decentralized reading community
- **Full social network** — status updates, reading goals, book shelves, ratings, reviews, and reading status (want to read, currently reading, finished)
- **Import from Goodreads** — bulk import your existing Goodreads shelves and reading history via CSV export
- **Edition management** — connects to OpenLibrary and ISBN databases to resolve book metadata automatically
- **Customizable themes** — supports multiple visual themes and branding options
- **Built-in bot protection** — integrates Anubis CAPTCHA to prevent spam registrations

### Architecture

BookWyrm is the most complex of the three tools, requiring multiple services:

- **Django web application** — the core Python backend
- **Celery workers** — asynchronous task processing for imports, email, and federation
- **PostgreSQL** — relational database for user data, books, and social interactions
- **Redis** — message broker for Celery and caching
- **Nginx** — reverse proxy with optional Let's Encrypt (certbot) integration
- **Anubis** — bot protection service

### Best For

Readers who want the closest experience to Goodreads — full social features, community interaction, and the ability to connect with readers across the fediverse. If you run a reading club, book review blog, or community library, BookWyrm provides the richest feature set.

## Jelu: Streamlined Book Tracker with OPDS Support

**Jelu** ([bayang/jelu](https://github.com/bayang/jelu), 677 stars) takes a more focused approach. Written in Kotlin, it prioritizes personal reading tracking with excellent metadata import capabilities and OPDS server support for connecting to ebook readers.

### Key Features

- **Automatic metadata import** — uses embedded fetch-ebook-metadata to resolve book details from title, author, or ISBN without manual entry
- **OPDS server** — serves your book collection to compatible ebook readers (KOReader, Calibre, etc.) over the network
- **Multi-user support** — create separate accounts for family members, each with private reading lists
- **Reading statistics** — track pages read, reading pace, and time spent per book
- **Cover art management** — automatic cover fetching and manual upload support
- **Import/export** — supports CSV and OPF file imports for migrating from other platforms
- **REST API** — programmatic access for integrations and automation

### Architecture

Jelu has a simpler deployment than BookWyrm:

- **Single Kotlin application** — runs on any JVM, no additional services required
- **H2 or PostgreSQL database** — embedded H2 for simple setups, PostgreSQL for production
- **Built-in web UI** — responsive interface accessible from any browser

### Best For

Readers who want a clean, focused personal tracker without the social network overhead. If your priority is cataloging your library, tracking reading progress, and connecting to your ebook reader via OPDS, Jelu hits the sweet spot between features and simplicity.

## BookLogr: Minimalist Personal Library Manager

**BookLogr** ([Mozzo1000/booklogr](https://github.com/Mozzo1000/booklogr), 526 stars) is the simplest option — a straightforward JavaScript-based service for tracking books you've read, want to read, or are currently reading. It favors ease of deployment and a lightweight footprint over advanced features.

### Key Features

- **Three-state tracking** — mark books as Read, Currently Reading, or Want to Read
- **Personal library view** — visual overview of your collection with cover art
- **Google authentication** — optional Google login for easier account management
- **Simple REST API** — clean API endpoints for the web frontend and third-party integrations
- **Lightweight deployment** — just two containers (API + web frontend) with a SQLite database
- **Demo mode** — try before you deploy with a public demo instance

### Architecture

BookLogr has the simplest deployment of all three:

- **API service** — Node.js backend with SQLite database
- **Web frontend** — static SPA served via a lightweight web container
- **No external dependencies** — no database server, no message broker, no cache layer

### Best For

Users who want a no-frills, easy-to-deploy reading tracker. If you just need to log what you've read and maintain a want-to-read list without social features or federation, BookLogr gets the job done with minimal infrastructure.

## Comparison Table

| Feature | BookWyrm | Jelu | BookLogr |
|---|---|---|---|
| **GitHub Stars** | 2,690 | 677 | 526 |
| **Language** | Python (Django) | Kotlin (Spring Boot) | JavaScript (Node.js) |
| **Social Features** | Full (ActivityPub) | None | None |
| **Federation** | ActivityPub/fediverse | No | No |
| **Goodreads Import** | CSV import | CSV/OPF import | No |
| **OPDS Server** | No | Yes | No |
| **Database** | PostgreSQL | H2 / PostgreSQL | SQLite |
| **Multi-User** | Yes | Yes | No (single user) |
| **Docker Compose** | 6+ services | Single container | 2 containers |
| **Resource Usage** | High (1-2 GB RAM) | Low (256-512 MB) | Minimal (128-256 MB) |
| **API** | Yes | REST API | REST API |
| **Authentication** | Local, email | Local | Google OAuth |
| **Cover Art** | OpenLibrary | Auto-fetch | Manual/API |
| **Last Updated** | April 2026 | April 2026 | April 2026 |
| **Complexity** | Advanced | Moderate | Beginner |

## Installation Guides

### Deploying BookWyrm with Docker Compose

BookWyrm requires the most infrastructure. The official `docker-compose.yml` deploys six services behind Nginx with automatic TLS via certbot:

```yaml
services:
  web:
    image: bookwyrm-social/bookwyrm:latest
    restart: unless-stopped
    depends_on:
      - db
      - redis
      - celery
    environment:
      - DOMAIN=${DOMAIN}
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=postgresql://bookwyrm:${DB_PASS}@db:5432/bookwyrm
      - REDIS_ACTIVITY_URL=redis://redis:6379
      - EMAIL_HOST=mail.example.com
      - EMAIL_PORT=587
    volumes:
      - static_volume:/app/static
      - media_volume:/app/images

  db:
    image: postgres:16
    environment:
      - POSTGRES_USER=bookwyrm
      - POSTGRES_PASSWORD=${DB_PASS}
      - POSTGRES_DB=bookwyrm
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  celery:
    image: bookwyrm-social/bookwyrm:latest
    command: ./celery_worker.sh
    depends_on:
      - db
      - redis
    environment:
      - DATABASE_URL=postgresql://bookwyrm:${DB_PASS}@db:5432/bookwyrm
      - REDIS_ACTIVITY_URL=redis://redis:6379

  nginx:
    image: nginx:1.28.1
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf
      - ./certbot/conf:/etc/nginx/ssl
      - static_volume:/app/static
      - media_volume:/app/images

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:
```

Create a `.env` file with your domain, secret key, and database credentials, then run:

```bash
docker compose up -d
```

The first startup runs database migrations automatically. After the containers are healthy, visit `https://your-domain.com` to create the admin account.

### Deploying Jelu with Docker

Jelu's simplicity shines with its single-container deployment. The official Docker image on Docker Hub (`wabayang/jelu`) includes the fetch-ebook-metadata tool for automatic book metadata resolution:

```yaml
services:
  jelu:
    image: wabayang/jelu:latest
    container_name: jelu
    restart: unless-stopped
    volumes:
      - ./config:/config
      - ./database:/database
      - ./files/images:/files/images
      - ./files/imports:/files/imports
      - /etc/timezone:/etc/timezone:ro
    ports:
      - "11111:11111"
    environment:
      - TZ=UTC
      # Optional: configure PostgreSQL instead of embedded H2
      # - SPRING_DATASOURCE_URL=jdbc:postgresql://db:5432/jelu
      # - SPRING_DATASOURCE_USERNAME=jelu
      # - SPRING_DATASOURCE_PASSWORD=secret
```

Jelu defaults to an embedded H2 database, making it ideal for single-user setups. For production with multiple users, swap to PostgreSQL by uncommenting the datasource variables. Access the web UI at `http://your-server:11111`.

### Deploying BookLogr with Docker Compose

BookLogr splits into two containers — an API backend and a web frontend — communicating over a shared network:

```yaml
services:
  booklogr-api:
    image: mozzo/booklogr:v1.9.0
    container_name: booklogr-api
    restart: unless-stopped
    env_file:
      - .env
    ports:
      - "5000:5000"
    volumes:
      - ./data:/app/instance

  booklogr-web:
    image: mozzo/booklogr-web:v1.9.0
    container_name: booklogr-web
    restart: unless-stopped
    environment:
      - BL_API_ENDPOINT=http://your-server:5000/
      - BL_GOOGLE_ID=
      - BL_DEMO_MODE=false
    ports:
      - "5150:80"
```

The `.env` file configures the SQLite database path and any application secrets. After starting the containers, the web interface is available at `http://your-server:5150`.

For readers looking to complement their book tracking with a full media library, our [Audiobookshelf vs Kavita vs Calibre-Web comparison](../2026-04-19-audiobookshelf-vs-kavita-vs-calibre-web-self-hosted-ebook-audiobook-server-2026/) covers the best self-hosted ebook servers that pair well with these trackers.

## Which Should You Choose?

**Choose BookWyrm if** you want the full Goodreads experience — social feeds, community reviews, following other readers, and federating with the wider fediverse. It requires the most infrastructure (PostgreSQL, Redis, Celery workers, Nginx), but delivers the most complete replacement for Goodreads. The ActivityPub federation means your instance isn't an island; you can discover and interact with readers on any compatible server worldwide.

**Choose Jelu if** you want a personal reading tracker with excellent metadata import and OPDS support for connecting to your ebook reader. It strikes a balance between features and simplicity — no social network, but robust personal tracking, multi-user support, and a clean REST API. The embedded H2 database option means you can run it on a low-end VPS or Raspberry Pi.

**Choose BookLogr if** you want the simplest possible setup for tracking your reading. Two containers, SQLite, and a responsive web UI — you can have it running in under five minutes. It lacks the advanced features of the other two, but for a personal "what did I read" log, it's hard to beat the deployment simplicity.

## FAQ

### Can I import my Goodreads data into these platforms?

Yes. BookWyrm supports Goodreads CSV export import — go to Goodreads Settings > Import/Export > Export Library and upload the CSV to BookWyrm. Jelu supports both CSV and OPF (Calibre) imports. BookLogr currently does not have a Goodreads import feature, so you would need to manually add your books or use the API.

### Do I need a separate server for each platform?

No. All three platforms can run on the same server if resources allow. BookWyrm is the most resource-intensive (1-2 GB RAM minimum due to multiple services), while Jelu and BookLogr are lightweight enough to coexist on a small VPS. Use a reverse proxy like Nginx or Caddy to route different domains or subdomains to each service.

### Can these platforms work offline or without internet access?

Jelu and BookLogr function fully offline once deployed — all data is stored locally. BookWyrm requires internet access for its ActivityPub federation features and for fetching book metadata from OpenLibrary, though the core reading tracker works without connectivity.

### Is BookWyrm's ActivityPub federation safe?

BookWyrm includes built-in bot protection via the Anubis service, which adds a CAPTCHA-like challenge to block automated spam. Instance administrators can also configure moderation tools, block lists, and account approval requirements to control who joins and interacts with their server.

### Which platform has the best mobile experience?

All three provide responsive web interfaces that work on mobile browsers. Jelu additionally offers OPDS server support, meaning you can connect ebook reading apps like KOReader or Lithium directly to your Jelu instance for seamless access to your book collection from mobile devices.

### Can I use these platforms for non-book media tracking?

These platforms are specifically designed for books. For tracking TV shows, movies, anime, or video games, check out our [Yamtrack vs MediaTracker vs Movary comparison](../yamtrack-vs-mediatracker-vs-movary-self-hosted-media-tracker-guide-2026/) which covers self-hosted alternatives for those media types.

### How do I back up my reading data?

BookWyrm uses PostgreSQL — use `pg_dump` for logical backups or filesystem-level snapshots of the data directory. Jelu's H2 database is a single file you can copy, or use PostgreSQL backup tools if you configured it that way. BookLogr stores everything in a SQLite database file in the `data` volume, which can be copied directly or exported via the `sqlite3` CLI tool.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "BookWyrm vs Jelu vs BookLogr: Best Self-Hosted Goodreads Alternatives 2026",
  "description": "Compare BookWyrm, Jelu, and BookLogr — three open-source, self-hosted alternatives to Goodreads for tracking your reading, managing your library, and sharing book reviews without corporate surveillance.",
  "datePublished": "2026-04-28",
  "dateModified": "2026-04-28",
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
