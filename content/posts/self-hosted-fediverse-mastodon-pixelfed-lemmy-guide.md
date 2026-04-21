---
title: "Self-Hosted Fediverse: Mastodon vs Pixelfed vs Lemmy — Complete Guide 2026"
date: 2026-04-12
tags: ["comparison", "guide", "self-hosted", "privacy", "social", "fediverse"]
draft: false
description: "Learn how to self-host decentralized social networks with the Fediverse. Compare Mastodon, Pixelfed, and Lemmy as open-source alternatives to Twitter, Instagram, and Reddit with full data control."
---

The age of centralized social media monopolies is ending. Every year brings new headlines about data breaches, algorithmic manipulation, censorship debates, and platform instability. Users are tired of being the product, and communities are tired of arbitrary rule changes that can destroy years of engagement overnight.

The answer has arrived, and it is decentralized. The Fediverse — a network of interconnected, open-source social platforms — lets you run your own server, own your data, and still communicate with millions of users across the broader network. Whether you want a Twitter alternative, an Instagram replacement, or a self-hosted Reddit, the tools exist, they are mature, and they work.

This guide covers the three most popular self-hosted Fediverse platforms: **Mastodon** (microblogging), **Pixelfed** (photo sharing), and **Lemmy** (link aggregation/discussion). We will compare them, show you how to deploy each one with [docker](https://www.docker.com/), and explain why running your own instance is the single most impactful step you can take toward digital sovereignty.

## Why Self-Host Your Social Network

Centralized social platforms have fundamental conflicts of interest. Their revenue depends on advertising, which depends on engagement, which depends on algorithms designed to maximize time-on-site rather than user well-being. When you self-host, these incentives disappear.

**Complete data ownership.** Every post, follower relationship, media file, and configuration setting lives on hardware you control. No corporation can scan your direct messages for ad targeting, and no acquisition deal can suddenly change your privacy policy.

**Community governance.** You set the rules. Your instance can be a private space for friends and family, a moderated community around a specific topic, or an open public server. You decide what content is allowed, what features are enabled, and how moderation works.

**Federation without lock-in.** This is the critical insight: self-hosting does not mean isolation. Every Fediverse platform uses ActivityPub, a W3C-standard protocol that lets your instance communicate with any other. A user on your Mastodon server can follow accounts on other Mastodon servers, interact with Pixelfed photographers, and discover Lemmy communities — all without leaving their home server.

**Resilience and longevity.** When a company shuts down a platform (as Google has done dozens of times), everyone loses their content and connections simultaneously. Your self-hosted instance persists as long as you maintain it. There is no board of directors that can decide your community is not profitable enough to keep running.

**Performance and customization.** Public instances often impose rate limits, storage quotas, and feature restrictions. Your own server has no such artificial limits. You can adjust post length caps, enable experimental features, customize the theme, and tune performance for your specific community size.

## Mastodon: The Microblogging Standard

Mastodon is the largest and most mature Fediverse platform, with over 10 million registered accounts across thousands of instances. It is the direct open-source alternative to X (formerly Twitter), offering short-form posts, timelines, content warnings, polls, and a robust following system.

### Architecture Overview

Mastodon consists of four main components:

- **Web app** — Ruby on Rails backend serving the API and web interface
- **Streaming API** — Node.js service handling real-time timeline updates via WebSockets
- **Sidekiq workers** — Background job processors for federation, email delivery, and media processing
- **PostgreSQL + Redis** — Primary database and caching/message queue

A typical small-to-medium instance (up to a few thousand users) runs comfortably on a server with 4 CPU cores, 8 GB RAM, and 100 GB storage.

### Docker Compose Deployment

```yaml
version: "3.9"

services:
  db:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_DB: mastodon
      POSTGRES_USER: mastodon
      POSTGRES_PASSWORD: ${DB_PASS}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: pg_isready -U mastodon
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: always
    volumes:
      - redis_data:/data
    healthcheck:
      test: redis-cli ping
      interval: 10s
      timeout: 5s
      retries: 5

  web:
    image: ghcr.io/mastodon/mastodon:v4.3.3
    restart: always
    env_file: .env.production
    command: bash -c "rm -f /mastodon/tmp/pids/server.pid; bundle exec rails s -p 3000"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - mastodon_assets:/mastodon/public/assets
      - mastodon_system:/mastodon/public/system
    healthcheck:
      test: curl -f http://localhost:3000/health
      interval: 10s
      timeout: 5s
      retries: 5

  streaming:
    image: ghcr.io/mastodon/mastodon:v4.3.3
    restart: always
    env_file: .env.production
    command: node ./streaming
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  sidekiq:
    image: ghcr.io/mastodon/mastodon:v4.3.3
    restart: always
    env_file: .env.production
    command: bundle exec sidekiq
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - mastodon_system:/mastodon/public/system

volumes:
  postgres_data:
  redis_data:
  mastodon_assets:
  mastodon_system:
```

Environment configuration (`.env.production`):

```bash
LOCAL_DOMAIN=your-domain.example
LOCAL_HTTPS=true
DB_HOST=db
DB_PORT=5432
DB_NAME=mastodon
DB_USER=mastodon
DB_PASS=your-secure-database-password
REDIS_HOST=redis
REDIS_PORT=6379
SECRET_KEY_BASE=$(openssl rand -hex 64)
OTP_SECRET=$(openssl rand -hex 64)
VAPID_PRIVATE_KEY=$(docker compose run --rm web bundle exec rake mastodon:webpush:generate_vapid_key | grep PRIVATE | cut -d= -f2)
VAPID_PUBLIC_KEY=$(docker compose run --rm web bundle exec rake mastodon:webpush:generate_vapid_key | grep PUBLIC | cut -d= -f2)
SMTP_SERVER=smtp.your-provider.com
SMTP_PORT=587
SMTP_LOGIN=noreply@your-domain.example
SMTP_PASSWORD=your-smtp-password
SMTP_FROM_ADDRESS=noreply@your-domain.example
```

After placing the files, run the initial database setup:

```bash
docker compose run --rm web bundle exec rake db:migrate
docker compose run --rm web bundle exec rake assets:precompile
docker compose up -d
```

Th[nginx](https://nginx.org/)t up a reverse proxy (Nginx, Caddy, or Traefik) to handle SSL termination and route traffic to the web (port 3000) and streaming (port 4000) services.

### Key Configuration Options

Once your instance is running, access the admin panel at `your-domain.example/admin` to configure:

- **Site settings** — name, description, rules, and custom CSS
- **Registration** — open, approval-required, or invite-only
- **Federation** — full federation, allowlist (only federate with specific instances), or blocklist (defederation from specific instances)
- **Storage** — configure object storage (S3-compatible) for media files to reduce local disk usage
- **Rate limits** — protect against abuse with configurable API and account creation limits

## Pixelfed: Decentralized Photo Sharing

Pixelfed is the Fediverse answer to Instagram. It provides photo uploads, filters, albums, stories, and a familiar timeline-based browsing experience — all without tracking, targeted ads, or algorithmic feed manipulation.

### Architecture Overview

Pixelfed is built on Laravel (PHP) with the following components:

- **Web application** — PHP/Laravel serving the UI and ActivityPub federation
- **MySQL/MariaDB or PostgreSQL** — relational database
- **Redis** — caching, queues, and session storage
- **Image processing** — GD or Imagick for thumbnail generation and filters

Pixelfed is lighter than Mastodon and can run on modest hardware: 2 CPU cores, 4 GB RAM, and 50 GB storage is sufficient for a personal or small community instance.

### Docker Compose Deployment

```yaml
version: "3.9"

services:
  db:
    image: mariadb:11
    restart: always
    environment:
      MARIADB_DATABASE: pixelfed
      MARIADB_USER: pixelfed
      MARIADB_PASSWORD: ${DB_PASS}
      MARIADB_ROOT_PASSWORD: ${ROOT_PASS}
    volumes:
      - db_data:/var/lib/mysql
    healthcheck:
      test: mysqladmin ping -h localhost -u pixelfed -p${DB_PASS}
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: always
    volumes:
      - redis_data:/data
    healthcheck:
      test: redis-cli ping
      interval: 10s
      timeout: 5s
      retries: 5

  worker:
    image: pixelfed/pixelfed:latest
    restart: always
    env_file: .env
    command: gosu www-data php artisan horizon
    volumes:
      - pixelfed_storage:/var/www/storage
      - pixelfed_public:/var/www/public
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  app:
    image: pixelfed/pixelfed:latest
    restart: always
    env_file: .env
    ports:
      - "127.0.0.1:8080:8080"
    volumes:
      - pixelfed_storage:/var/www/storage
      - pixelfed_public:/var/www/public
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
      worker:
        condition: service_started

volumes:
  db_data:
  redis_data:
  pixelfed_storage:
  pixelfed_public:
```

Environment configuration (`.env`):

```bash
APP_NAME="My Photo Gallery"
APP_URL=https://your-domain.example
APP_DEBUG=false
DB_CONNECTION=mysql
DB_HOST=db
DB_PORT=3306
DB_DATABASE=pixelfed
DB_USERNAME=pixelfed
DB_PASSWORD=your-database-password
REDIS_HOST=redis
REDIS_PASSWORD=null
REDIS_PORT=6379
MAIL_MAILER=smtp
MAIL_HOST=smtp.your-provider.com
MAIL_PORT=587
MAIL_USERNAME=noreply@your-domain.example
MAIL_PASSWORD=your-smtp-password
MAIL_FROM_ADDRESS=noreply@your-domain.example
ACTIVITY_PUB=true
AP_REMOTE_FOLLOW=true
OPEN_REGISTRATION=false
MAX_PHOTO_SIZE=15000
MAX_CAPTION_LENGTH=500
MAX_ALBUM_LENGTH=10
ENFORCE_ACCOUNT_LIMITS=false
```

Initialize the application:

```bash
docker compose run --rm app php artisan key:generate
docker compose run --rm app php artisan migrate --force
docker compose run --rm app php artisan storage:link
docker compose run --rm app php artisan passport:keys
docker compose up -d
```

### Standout Features

Pixelfed includes several features that differentiate it from Instagram:

- **No algorithmic feed** — chronological timeline only, no engagement-optimizing algorithms
- **EXIF data control** — choose whether to strip or preserve EXIF metadata in uploaded photos
- **Collection albums** — curate photos into thematic collections that others can follow
- **Import/Export** — download all your photos and metadata at any time
- **Stories** — 24-hour ephemeral photo posts (optional, can be disabled)
- **Content warnings** — blur images behind user-defined warnings, useful for artistic or sensitive content

## Lemmy: Community-Driven Link Aggregation

Lemmy is the Fediverse equivalent of Reddit. It organizes content into communities (subreddits), supports threaded discussions, voting, and moderation — all running on open-source software you control.

### Architecture Overview

Lemmy is written in Rust with a focus on performance and resource efficiency:

- **Lemmy server** — Rust backend (Actix web framework) serving the API and ActivityPub federation
- **Lemmy UI** — Svelte-based web interface
- **PostgreSQL** — primary database
- **Pictrs** — image hosting service for thumbnails and uploads

Lemmy is remarkably lightweight. A small instance can run on 2 CPU cores and 2 GB RAM. The Rust backend handles federation efficiently, and the binary distribution makes deployment straightforward.

### Docker Compose Deployment

```yaml
version: "3.9"

services:
  lemmy:
    image: dessalines/lemmy:0.19.6
    restart: always
    environment:
      - RUST_LOG=warn
    volumes:
      - ./config.hjson:/config/config.hjson
    depends_on:
      postgres:
        condition: service_healthy
      pictrs:
        condition: service_started
    networks:
      - lemmy-net
    ports:
      - "127.0.0.1:8536:8536"

  lemmy-ui:
    image: dessalines/lemmy-ui:0.19.6
    restart: always
    environment:
      - LEMMY_EXTERNAL_HOST=your-domain.example
      - LEMMY_INTERNAL_HOST=lemmy:8536
      - LEMMY_HTTPS=true
      - LEANRATE_FRONTEND_ENDPOINT=http://localhost:8540
      - LEMMY_UI_LEMMY_INTERNAL_HOST=lemmy:8536
      - LEMMY_UI_LEMMY_EXTERNAL_HOST=your-domain.example
    depends_on:
      - lemmy
    networks:
      - lemmy-net
    ports:
      - "127.0.0.1:1234:1234"

  pictrs:
    image: asonix/pictrs:0.5.0-rc.4
    restart: always
    environment:
      - PICTRS_ADDRESS=0.0.0.0:8080
      - PICTRS_OPENTELEMETRY_URL=http://otel:4137
      - PICTRS__API_KEY=your-pictrs-api-key-here
      - PICTRS__MEDIA__VIDEO_CODEC=vp9
      - PICTRS__MEDIA__GIF__MAX_WIDTH=256
      - PICTRS__MEDIA__GIF__MAX_HEIGHT=256
      - PICTRS__MEDIA__GIF__MAX_AREA=65536
      - PICTRS__MEDIA__GIF__MAX_FRAME_COUNT=400
    user: 991:991
    volumes:
      - pictrs_data:/mnt
    networks:
      - lemmy-net

  postgres:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_USER: lemmy
      POSTGRES_PASSWORD: your-db-password
      POSTGRES_DB: lemmy
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - lemmy-net
    healthcheck:
      test: pg_isready -U lemmy
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  pictrs_data:
  postgres_data:

networks:
  lemmy-net:
```

Configuration file (`config.hjson`):

```hjson
{
  database: {
    url: "postgresql://lemmy:your-db-password@postgres/lemmy"
    pool_size: 5
  }
  hostname: "your-domain.example"
  pictrs: {
    url: "http://pictrs:8080"
    api_key: "your-pictrs-api-key-here"
  }
  email: {
    smtp_server: "smtp.your-provider.com:587"
    smtp_login: "noreply@your-domain.example"
    smtp_password: "your-smtp-password"
    smtp_from_address: "noreply@your-domain.example"
    tls_type: "starttls"
  }
  rate_limit: {
    message: 180
    message_per_second: 60
    post: 6
    post_per_second: 60
    register: 3
    register_per_second: 3600
    image: 6
    image_per_second: 3600
    comment: 6
    comment_per_second: 3600
    search: 60
    search_per_second: 600
  }
  federation: {
    enabled: true
    sign_fetch: true
    slur_filter: ""
    allowed_instances: []
    blocked_instances: []
  }
}
```

Start the instance:

```bash
docker compose up -d
```

### Community Features

Lemmy provides comprehensive community tools:

- **Hierarchical comments** — nested, threaded discussions with collapse/expand
- **Community moderation** — multiple moderator roles with granular permissions
- **Post types** — links, text posts, image uploads, and URL previews
- **Sorting** — hot, active, new, top (day/week/month/year/all), controversial
- **Cross-community federation** — users can subscribe to communities on other Lemmy instances
- **Content filtering** — instance-level and user-level filters for tags and keywords
- **Admin tools** — site-wide announcements, registration mode control, instance allow/block lists

## Comparison: Mastodon vs Pixelfed vs Lemmy

| Feature | Mastodon | Pixelfed | Lemmy |
|---|---|---|---|
| **Replaces** | X (Twitter) | Instagram | Reddit |
| **Language** | Ruby | PHP (Laravel) | Rust |
| **Database** | PostgreSQL | MySQL/MariaDB | PostgreSQL |
| **Protocol** | ActivityPub | ActivityPub | ActivityPub |
| **Min. RAM** | 8 GB | 4 GB | 2 GB |
| **Min. CPU** | 4 cores | 2 cores | 2 cores |
| **Media Focus** | Images + text | Photos (primary) | Links + discussion |
| **Post Length** | 500 chars (configurable) | Captions + albums | No limit |
| **Federation** | Full ActivityPub | Full ActivityPub | Full ActivityPub |
| **Mobile Apps** | Tusky, Mona, Ice Cubes | Official + many third-party | Voyager, Jerboa, Thunder |
| **Cross-Platform** | Follows Pixelfed/Lemmy accounts | Follows Mastodon accounts | Follows Mastodon communities |
| **Setup Com[plex](https://www.plex.tv/)ity** | High | Medium | Medium |
| **Community Size** | Largest (~10M+ users) | Growing (~300K+ users) | Growing (~100K+ users) |
| **Best For** | General social networking | Photography communities | Forum-style discussions |

### Which Should You Choose?

**Start with Mastodon if** you want the broadest reach and most active ecosystem. It has the largest user base, the most third-party apps, and the most mature moderation tools. It is the best choice for a general-purpose social server.

**Choose Pixelfed if** your community centers around visual content. Photographers, artists, and creative communities benefit from the album features, EXIF handling, and chronological feed. It is also the lightest to run if you already have a web server with PHP support.

**Pick Lemmy if** you want structured, topic-based discussions. The community-and-subreddit model works well for hobby groups, technical communities, and any scenario where long-form discussion and link sharing matter more than short personal updates.

You can also run multiple platforms on the same infrastructure. A single VPS with 8 cores and 16 GB RAM can comfortably host all three simultaneously, giving your community the full Fediverse experience.

## Reverse Proxy Setup

All three platforms need a reverse proxy for SSL termination and routing. Here is a Caddy configuration that handles all three on a single domain using subdomains:

```caddyfile
mastodon.your-domain.example {
    reverse_proxy localhost:3000
    encode gzip
}

mastodon.your-domain.example {
    reverse_proxy localhost:4000
    @stream {
        path /api/v1/streaming/*
    }
}

pixelfed.your-domain.example {
    reverse_proxy localhost:8080
    encode gzip
}

lemmy.your-domain.example {
    reverse_proxy localhost:1234
    encode gzip
}
```

Caddy automatically obtains and renews Let's Encrypt certificates. No additional SSL configuration is needed.

If you prefer Nginx, the configuration follows the standard pattern:

```nginx
server {
    listen 443 ssl http2;
    server_name mastodon.your-domain.example;

    ssl_certificate /etc/letsencrypt/live/mastodon.your-domain.example/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mastodon.your-domain.example/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/v1/streaming {
        proxy_pass http://127.0.0.1:4000;
        proxy_set_header Host $host;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## Maintenance and Best Practices

Running a Fediverse instance is a commitment, but the operational overhead is manageable with good habits.

**Regular backups.** Export your database daily and store copies off-site. Mastodon provides `pg_dump`, Pixelfed uses `mysqldump`, and Lemmy uses `pg_dump`. Include the storage volumes (uploaded media) in your backup rotation.

```bash
# Mastodon/Lemmy (PostgreSQL)
docker compose exec db pg_dump -U mastodon mastodon > backup-$(date +%F).sql

# Pixelfed (MariaDB)
docker compose exec db mysqldump -u pixelfed -p pixelfed > backup-$(date +%F).sql
```

**Monitor federation health.** Check the admin panel regularly for federation errors. Some instances may defederate from yours if they detect spam, and you may want to proactively block instances that host harmful content.

**Keep software updated.** Fediverse platforms receive frequent updates for security and protocol compatibility. Subscribe to each project's release announcements and test updates on a staging copy before deploying to production.

**Storage management.** Media files grow quickly. Configure automatic cleanup for remote media cache (federated content from other instances that your users have interacted with). Mastodon handles this with `tootctl media remove`, and Pixelfed has a built-in cache expiration setting.

**Email deliverability.** Set up proper SPF, DKIM, and DMARC records for your domain. Without these, your invitation and notification emails will land in spam folders, blocking new user registration.

## The Fediverse Is the Future

Self-hosting your social network is no longer a niche hobby. The tools are production-ready, the communities are growing, and the protocol standards are stable. ActivityPub has been adopted by major platforms beyond the Fediverse, and the network effect continues to expand.

When you self-host, you are not just running software — you are participating in a movement toward a more open, user-controlled internet. Every instance is a small declaration of independence from the surveillance capitalism model that has dominated social media for two decades.

Start with one platform, learn the ropes, and expand as your community grows. The Fediverse welcomes newcomers, and the knowledge you gain from running your first instance will serve you well across the entire decentralized web.

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
