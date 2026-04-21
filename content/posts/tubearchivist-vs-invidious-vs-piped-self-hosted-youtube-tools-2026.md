---
title: "Tube Archivist vs Invidious vs Piped: Self-Hosted YouTube Tools 2026"
date: 2026-04-21
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Compare three self-hosted YouTube tools in 2026: Tube Archivist for archiving, Invidious for private viewing, and Piped for a lightweight alternative front-end. Complete Docker setup guides."
---

YouTube is the world's largest video platform, but using it directly comes with a well-documented cost: invasive tracking, aggressive advertising, sponsored content injected into recommendations, and zero control over your own viewing history. Every watch, every search, every pause is logged and used to build a profile that advertisers pay to target.

Self-hosting your YouTube infrastructure changes that equation entirely. Whether you want to permanently archive videos you care about, watch YouTube without being tracked, or run a lightweight alternative front-end for your household, there is an open-source tool for each approach. This guide covers the three most popular self-hosted YouTube utilities in 2026: **Tube Archivist**, **Invidious**, and **Piped**.

Each project takes a fundamentally different approach:

- **Tube Archivist** downloads and stores YouTube videos locally, giving you a permanent personal media library with full-text search.
- **Invidious** acts as a proxy — you watch videos through its interface while it strips tracking, ads, and telemetry before they reach your browser.
- **Piped** provides a similar proxy experience but with a modern Vue.js front-end, SponsorBlock integration, and a focus on performance.

Let's dive into each one and see which fits your needs.

## Why Self-Host Your YouTube Experience

The arguments for running your own YouTube tools extend well beyond ad blocking:

**Permanent access.** Videos disappear constantly — channel deletions, copyright strikes, geo-blocking, and platform policy changes. When you self-host and archive content, you decide what stays available. If a video matters to you, it stays on your server regardless of what happens on YouTube's end.

**Privacy by default.** YouTube's tracking infrastructure is among the most extensive on the internet. It correlates your viewing habits with your Google account, device fingerprints, IP addresses, and behavioral patterns across Google's entire advertising network. Self-hosted tools eliminate this telemetry at the source — your watch history never leaves your server.

**No algorithm manipulation.** YouTube's recommendation engine is designed to maximize engagement, not serve your best interests. Self-hosted interfaces either remove recommendations entirely or let you control how they work. You search for what you want, not what the algorithm decides you should see.

**Household-wide benefits.** A single self-hosted instance serves your entire household. Kids get an ad-free experience, everyone's history stays local, and you can even set up content filtering at the server level. One $5/month VPS or a Raspberry Pi at home handles this for multiple users.

**Bandwidth efficiency.** If you frequently rewatch the same videos, downloading them once (Tube Archivist) or caching them locally (Invidious/Piped with proxy caching) saves significant bandwidth over time.

## Tube Archivist: Your Personal YouTube Archive

[Tube Archivist](https://tubearchivist.com/) is a self-hosted YouTube media server written in Python. It downloads videos from YouTube (and supported channels/playlists), stores them permanently on your server, and provides a clean web interface for browsing, searching, and playing your collection. With **7,811 stars** on GitHub and regular updates (last commit: April 2026), it is the leading open-source YouTube archiving solution.

### Key Features

- **Full YouTube metadata preservation** — titles, descriptions, thumbnails, subtitles, and chapters are all downloaded alongside the video
- **Full-text search** — powered by Elasticsearch, search across video titles, descriptions, and channel names instantly
- **Channel and playlist subscriptions** — automatically download new uploads from your subscribed channels on a schedule
- **Video player with watch tracking** — built-in player that remembers your watch progress per video
- **Multi-user support** — user accounts with individual watch histories and subscriptions
- **REST API** — programmatic access for integrations and automation

### Architecture

Tube Archivist runs three services: the main application, Elasticsearch for search, and Redis for task queuing. The Elasticsearch component means you need at least 2GB of RAM for comfortable operation.

### Docker Installation

```yaml
# docker-compose.yml for Tube Archivist
services:
  tubearchivist:
    container_name: tubearchivist
    restart: unless-stopped
    image: bbilly1/tubearchivist
    ports:
      - "8000:8000"
    volumes:
      - media:/youtube
      - cache:/cache
    environment:
      - ES_URL=http://archivist-es:9200
      - REDIS_CON=redis://archivist-redis:6379
      - TA_HOST=http://your-server-ip:8000
      - TA_USERNAME=admin
      - TA_PASSWORD=your-secure-password
      - ELASTIC_PASSWORD=your-es-password
      - TZ=UTC
    depends_on:
      - archivist-es
      - archivist-redis

  archivist-redis:
    image: redis
    container_name: archivist-redis
    restart: unless-stopped
    expose:
      - "6379"
    volumes:
      - redis:/data
    depends_on:
      - archivist-es

  archivist-es:
    image: bbilly1/tubearchivist-es
    container_name: archivist-es
    restart: unless-stopped
    environment:
      - ELASTIC_PASSWORD=your-es-password
      - ES_JAVA_OPTS=-Xms1g -Xmx1g
      - xpack.security.enabled=true
      - discovery.type=single-node
    ulimits:
      memlock:
        soft: -1
        hard: -1
    volumes:
      - es:/usr/share/elasticsearch/data

volumes:
  media:
  cache:
  redis:
  es:
```

After deploying, access the web interface at `http://your-server:8000`, log in with the credentials you set, and start adding channel subscriptions or individual videos to download.

### Best Use Case

Tube Archivist is ideal when you want to **own a permanent copy** of YouTube content. Researchers, educators, content curators, and anyone who values long-term access to specific videos benefit most from this approach. The trade-off is disk space — a single 1080p video can consume 500MB to 2GB.

## Invidious: Privacy-First YouTube Front-End

[Invidious](https://invidious.io/) is an alternative YouTube front-end written in Crystal. Instead of downloading videos, it proxies YouTube's content through its own interface, stripping ads, trackers, and Google's JavaScript telemetry before it reaches your browser. With **18,923 stars** on GitHub (making it the most popular project in this comparison) and active development, Invidious is the mature, battle-tested option.

### Key Features

- **Zero tracking** — no Google cookies, no device fingerprinting, no watch history sent to YouTube
- **Ad-free playback** — server-side ad stripping means you never see pre-roll, mid-roll, or banner ads
- **No account required** — subscriptions and preferences are stored locally on the Invidious instance
- **Lightweight interface** — minimal HTML/CSS, no heavy JavaScript frameworks, fast on any device
- **Import/export subscriptions** — migrate your YouTube subscriptions in seconds
- **Audio-only mode** — stream just the audio track, saving bandwidth
- **API** — full programmatic access for building custom clients

### Docker Installation

```yaml
# docker-compose.yml for Invidious (production)
services:
  invidious:
    image: quay.io/invidious/invidious:latest
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      INVIDIOUS_CONFIG: |
        db:
          dbname: invidious
          user: kemal
          password: change-me-to-a-secure-password
          host: invidious-db
          port: 5432
        check_tables: true
        hmac_key: "generate-a-random-32-character-hmac-key"
    depends_on:
      invidious-db:
        condition: service_healthy

  invidious-db:
    image: docker.io/library/postgres:14
    restart: unless-stopped
    volumes:
      - postgresdata:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: invidious
      POSTGRES_USER: kemal
      POSTGRES_PASSWORD: change-me-to-a-secure-password
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]

volumes:
  postgresdata:
```

**Important**: The production Invidious setup requires running database initialization SQL scripts on first launch. The official documentation at [docs.invidious.io](https://docs.invidious.io/installation/) provides the complete `init-invidious-db.sh` script and SQL files that must be mounted into the database container. The simplified compose above handles the service wiring — you will need to add the init script from the Invidious repository for a working first-run.

### Best Use Case

Invidious is ideal when you want a **private viewing experience without consuming extra disk space**. You get ad-free, tracker-free YouTube viewing through a clean interface, but the actual video files remain on YouTube's servers. It is lightweight (PostgreSQL + a single Crystal binary) and runs comfortably on a $5/month VPS with 1GB of RAM.

## Piped: Modern, Fast YouTube Proxy

[Piped](https://piped.video/) is a newer alternative YouTube front-end built with Vue.js. It shares Invidious's goal of ad-free, tracker-free viewing but takes a different technical approach: instead of proxying through its own backend, Piped uses the SponsorBlock API for skipping sponsored segments, integrates with the LibreTranslate API for captions, and offers a modern, responsive interface. The project has **9,909 stars** on GitHub and sees frequent updates.

### Key Features

- **SponsorBlock integration** — automatically skip sponsored segments, intros, outros, and self-promotion sections
- **Modern UI** — Vue.js-based responsive design that works well on mobile devices
- **Multiple instance support** — connect to any public Piped instance or host your own
- **No Google account needed** — subscriptions and preferences stored on your instance
- **Lightweight backend** — the backend is a Kotlin/Ktor service with PostgreSQL, requiring minimal resources
- **Return YouTube Dislike** — shows dislike counts restored via the RYD API

### Docker Installation

Piped requires two components: the backend (Ktor service) and optionally a separate front-end. The backend handles all YouTube API interactions.

```yaml
# docker-compose.yml for Piped (backend + database)
services:
  piped-backend:
    image: 1337kavin/piped:latest
    restart: unless-stopped
    ports:
      - "127.0.0.1:8080:8080"
    volumes:
      - ./config.properties:/app/config.properties
    depends_on:
      - postgres

  postgres:
    image: postgres:17-alpine
    restart: unless-stopped
    volumes:
      - ./data/db:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=piped
      - POSTGRES_USER=piped
      - POSTGRES_PASSWORD=your-secure-postgres-password
```

Create a `config.properties` file alongside the compose file:

```properties
# Piped backend configuration
compromisedPasswordFile=
proxyHostname=
frontendUrl=http://your-server-ip
hibernate.connection.url=jdbc:postgresql://postgres:5432/piped
hibernate.connection.username=piped
hibernate.connection.password=your-secure-postgres-password
```

The Piped front-end can be served separately via Nginx, or you can use one of the many public Piped instances and only self-host the backend for privacy.

### Best Use Case

Piped is ideal when you want a **modern, feature-rich viewing experience** with SponsorBlock integration. If you frequently watch tech reviews, tutorials, or creator content where sponsored segments are common, Piped's automatic skipping saves significant time. The Vue.js front-end feels more like a modern web app compared to Invidious's minimal interface.

## Head-to-Head Comparison

| Feature | Tube Archivist | Invidious | Piped |
|---|---|---|---|
| **Approach** | Download & store locally | Proxy front-end | Proxy front-end |
| **Language** | Python | Crystal | Vue.js + Kotlin/Ktor |
| **Database** | Elasticsearch + Redis | PostgreSQL | PostgreSQL |
| **Disk Space** | High (stores videos) | Low (no local storage) | Low (no local storage) |
| **Ads** | N/A (local playback) | Stripped server-side | Stripped server-side |
| **SponsorBlock** | No | No | Yes (built-in) |
| **Offline Access** | Full (videos on disk) | No (requires internet) | No (requires internet) |
| **Min RAM** | ~2GB (Elasticsearch) | ~512MB | ~512MB |
| **Stars** | 7,811 | 18,923 | 9,909 |
| **Last Updated** | April 2026 | April 2026 | April 2026 |
| **Best For** | Permanent archive | Lightweight privacy | Modern UI + SponsorBlock |

## Choosing the Right Tool

Your choice depends on what problem you are trying to solve:

**Choose Tube Archivist** if you want to permanently own YouTube content. This is the only option that gives you offline access and protects against video deletion. The storage requirements are the trade-off — plan for at least 100GB if you intend to archive channels regularly.

**Choose Invidious** if you want the most mature, resource-efficient privacy solution. It has the largest community, the most public instances to choose from, and runs on minimal hardware. The Crystal-based backend is fast and the interface is clean, if minimalist.

**Choose Piped** if you value a modern interface and SponsorBlock integration. The Vue.js front-end feels polished, and the ability to skip sponsored segments automatically is a genuine productivity booster. The project is younger than Invidious but growing rapidly.

You can also **combine approaches** — run Invidious or Piped for daily viewing and Tube Archivist for channels you want to preserve long-term. They serve different purposes and complement each other well.

## FAQ

### Can I use Tube Archivist, Invidious, and Piped together?

Yes. They serve different purposes and can coexist on the same server. You might use Invidious or Piped for casual viewing and Tube Archivist to permanently save videos from specific channels. Just ensure your server has enough resources — Tube Archivist alone needs about 2GB RAM for Elasticsearch.

### Does self-hosting these tools violate YouTube's Terms of Service?

YouTube's ToS restricts automated downloading and circumvention of their advertising system. Running a private instance for personal use is a gray area that has not been legally tested in most jurisdictions. If you are concerned about compliance, Tube Archivist's local download approach carries more risk than Invidious or Piped's proxy model. Always check your local laws and YouTube's current ToS.

### How much storage does Tube Archivist need?

Storage depends on your archiving habits. A single 1080p video typically uses 500MB to 2GB. Archiving a moderately active channel (2 videos per week) consumes roughly 4-8GB per month. A 1TB drive gives you room for approximately 500-1,000 videos at 1080p quality.

### Can Invidious and Piped bypass geo-blocked videos?

Yes, if your self-hosted instance is in a region where the video is available. The proxy server fetches the video from YouTube's CDN, so the geographic location of your server determines what content is accessible. Deploying your instance on a VPS in a different country can unlock region-restricted content.

### Which tool is easiest to set up?

Piped has the simplest Docker compose — just two services (backend and PostgreSQL) with minimal configuration. Invidious requires running database initialization scripts on first launch, which adds a step. Tube Archivist is the most complex with three services (app, Elasticsearch, Redis) and higher resource requirements.

### Do any of these tools support YouTube Music?

Tube Archivist can download YouTube Music videos like any other YouTube content. Invidious has experimental YouTube Music support in some instances. Piped's backend supports music.youtube.com routing. For dedicated self-hosted music streaming, consider tools like Navidrome or Funkwhale instead.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Tube Archivist vs Invidious vs Piped: Self-Hosted YouTube Tools 2026",
  "description": "Compare three self-hosted YouTube tools in 2026: Tube Archivist for archiving, Invidious for private viewing, and Piped for a lightweight alternative front-end. Complete Docker setup guides.",
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

For related reading, see our [PeerTube self-hosted YouTube alternative guide](../peertube-self-hosted-youtube-alternative-guide/) for building your own video platform, our [Jellyfin vs Plex vs Emby comparison](../jellyfin-vs-plex-vs-emby/) for self-hosted media servers, and the [Overseerr vs Jellyseerr vs Ombi guide](../2026-04-21-overseerr-vs-jellyseerr-vs-ombi-self-hosted-media-requests-guide-2026/) for managing media requests in your home lab.
