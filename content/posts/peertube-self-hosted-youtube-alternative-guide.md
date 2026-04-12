---
title: "PeerTube: Complete Self-Hosted YouTube Alternative Guide 2026"
date: 2026-04-12
tags: ["comparison", "guide", "self-hosted", "privacy", "video", "federation"]
draft: false
description: "Complete guide to running your own PeerTube video platform in 2026. Docker deployment, federation setup, storage management, and why it's the best open-source YouTube alternative."
---

If you're tired of YouTube's algorithm-driven feed, invasive tracking, unpredictable demonetization, and opaque content policies, it's time to look at **PeerTube** — the open-source, federated video platform that lets you host, share, and stream video on your own terms.

PeerTube is not just a self-hosted video player. It's a full-featured video platform with its own player, transcoding engine, user accounts, channels, playlists, and — most importantly — **federation** via ActivityPub. Your PeerTube instance can talk to other instances, share content, and let followers subscribe across servers. It's the video layer of the fediverse, sitting alongside Mastodon, PixelFed, and Lemmy.

In this guide, we'll cover why PeerTube matters, how to deploy it with Docker, configure storage and transcoding, set up federation, and manage a production instance at scale.

---

## Why Self-Host Your Video Platform

Running your own video server gives you benefits that no centralized platform can match:

### Complete Content Control

No algorithm decides what your audience sees. No surprise demonetization. No opaque community guidelines enforced by a distant moderation team. You set the rules, you own the content, and your viewers choose to watch — not because an algorithm pushed it, but because they subscribed.

### No Tracking or Ads

YouTube tracks every click, pause, rewind, and scroll. PeerTube collects none of this by default. There are no ads, no sponsored content mandates, and no watch-time optimization games. Your viewers watch in peace.

### Data Sovereignty

Your video files, your metadata, your user database — all stored on hardware you control. No risk of platform shutdowns, account suspensions, or policy changes wiping your channel overnight.

### Federation

This is PeerTube's killer feature. A single instance can join a network of thousands of others. Content from your server can appear on remote instances, and vice versa. You get the reach of a centralized platform with the independence of self-hosting.

### Cost Predictability

At small to medium scale, a VPS with decent storage is all you need. No per-view fees, no revenue sharing, no surprise bills. As your audience grows, costs scale linearly and transparently.

---

## PeerTube at a Glance

| Feature | PeerTube | YouTube |
|---------|----------|---------|
| **Cost** | Free (open source, self-hosted) | Free (you are the product) |
| **Open Source** | ✅ Fully (AGPL-3.0) | ❌ Proprietary |
| **Ads** | ❌ None | ✅ Everywhere |
| **Tracking** | ❌ Minimal by design | ✅ Extensive |
| **Algorithm** | ❌ Chronological + subscriptions | ✅ Opaque recommendation engine |
| **Federation** | ✅ ActivityPub (join the fediverse) | ❌ Walled garden |
| **Transcoding** | ✅ Built-in (WebTorrent + HLS) | ✅ Proprietary pipeline |
| **Live Streaming** | ✅ Built-in | ✅ Built-in |
| **Custom Domain** | ✅ Your server, your domain | ❌ youtube.com/yourchannel |
| **Content Policy** | ✅ You decide | ❌ Google decides |
| **Monetization** | ✅ Direct support (Liberapay, Patreon) | ✅ Ad revenue share (platform-controlled) |
| **Storage** | ✅ Your hardware / cloud | ✅ Google's infrastructure |
| **Mobile Apps** | ⚠️ Third-party apps available | ✅ Official apps |

---

## Architecture Overview

PeerTube is a Node.js application backed by PostgreSQL and powered by two key technologies:

1. **WebTorrent** — Peer-to-peer video delivery. When someone watches a video on your instance, their browser also seeds it to other viewers, reducing your bandwidth costs naturally.

2. **ActivityPub** — The W3C federated protocol. Your instance can follow and be followed by other PeerTube instances, as well as Mastodon accounts, PixelFed users, and any ActivityPub-compatible service.

The default stack includes:
- **Node.js** backend (TypeScript)
- **PostgreSQL** database
- **NGINX** as reverse proxy
- **FFmpeg** for video transcoding
- **Redis** for caching and job queues
- **WebTorrent tracker** for P2P delivery

---

## Docker Deployment

The fastest way to get PeerTube running is with Docker Compose. The official repository provides a production-ready compose file.

### Prerequisites

- A server with at least 2 CPU cores and 4 GB RAM (4 cores / 8 GB recommended for transcoding)
- 50+ GB of storage for videos (SSD preferred for the database, HDD for video storage)
- A domain name with DNS records pointing to your server
- Docker and Docker Compose installed

### Step 1: Get the Docker Compose File

```bash
git clone https://github.com/Chocobozzz/PeerTube.git ~/peertube-docker
cd ~/peertube-docker
cp docker-compose.yaml docker-compose.yaml.bak
```

### Step 2: Configure Environment Variables

Create a `.env` file or edit the `docker-compose.yaml` directly. Here's a minimal production setup:

```yaml
version: "3.3"

services:

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: peertube
      POSTGRES_USER: peertube
      POSTGRES_PASSWORD: change_this_to_a_secure_password
    volumes:
      - ./postgres/data:/var/lib/postgresql/data
    restart: always

  redis:
    image: redis:7-alpine
    volumes:
      - ./redis/data:/data
    restart: always

  peertube:
    image: chocobozzz/peertube:production-bullseye
    platform: linux/amd64
    env_file:
      - .env
    environment:
      PEERTUBE_DB_USERNAME: peertube
      PEERTUBE_DB_PASSWORD: change_this_to_a_secure_password
      PEERTUBE_DB_HOSTNAME: postgres
      PEERTUBE_REDIS_HOSTNAME: redis
      PEERTUBE_WEBSERVER_HOSTNAME: video.example.com
      PEERTUBE_WEBSERVER_PORT: 443
      PEERTUBE_WEBSERVER_HTTPS: true
      PEERTUBE_SECRET: generate_a_long_random_secret_here
      PEERTUBE_ADMIN_EMAIL: admin@example.com
      PEERTUBE_SIGNUP_ENABLED: "true"
      PEERTUBE_ADMIN_AFTER_SIGNUP: "true"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker-volume/data:/data
      - ./docker-volume/config:/config
    depends_on:
      - postgres
      - redis
    restart: always
```

### Step 3: Launch

```bash
docker compose up -d
```

PeerTube will initialize the database, generate configuration, and start the application. The first startup takes a few minutes as it runs migrations.

### Step 4: Set Up TLS with NGINX

The PeerTube Docker image includes a built-in NGINX configuration, but for production you'll want proper TLS. The easiest approach is to use a reverse proxy container:

```bash
# Install certbot for Let's Encrypt
apt update && apt install -y certbot

# Generate certificates
certbot certonly --standalone -d video.example.com

# The Docker image auto-detects certificates in:
#   ./docker-volume/certificates/
# Symlink or copy them there:
mkdir -p ./docker-volume/certificates
ln -s /etc/letsencrypt/live/video.example.com/fullchain.pem \
  ./docker-volume/certificates/peertube.pem
ln -s /etc/letsencrypt/live/video.example.com/privkey.pem \
  ./docker-volume/certificates/peertube-key.pem

# Restart to pick up certs
docker compose restart peertube
```

### Step 5: Initial Admin Setup

After startup, PeerTube creates a random admin password. Find it in the logs:

```bash
docker compose logs peertube 2>&1 | grep -i "password"
```

Log in at `https://video.example.com`, change the password immediately, and configure your instance settings under **Administration → Configuration**.

---

## Storage and Transcoding Configuration

Video hosting is storage-intensive. Proper configuration prevents disk-space surprises.

### Transcoding Settings

PeerTube transcodes uploaded videos into multiple resolutions. Configure this under **Administration → Configuration → Video Transcoding**:

| Resolution | Bitrate | Use Case |
|-----------|---------|----------|
| 240p | 250 kbps | Mobile, low bandwidth |
| 360p | 500 kbps | Small screens, slow connections |
| 480p | 1000 kbps | Standard mobile |
| 720p | 2500 kbps | Desktop standard |
| 1080p | 5000 kbps | Full HD |

For a small instance, start with 360p and 720p only. Add more resolutions as your storage budget grows.

```yaml
# In your production.yaml or via environment variables:
PEERTUBE_TRANSCOD_ENABLED: "true"
PEERTUBE_TRANSCOD_THREADS: "2"
PEERTUBE_TRANSCOD_RESOLUTIONS_ENABLED: '{"240":false,"360":true,"480":false,"720":true,"1080":false}'
PEERTUBE_TRANSCOD_FPS_MAX: 30
```

### Storage Quotas

Set per-user and per-video upload limits to prevent any single user from consuming all disk space:

```yaml
PEERTUBE_INSTANCE_DEFAULT_USER_VIDEO_QUOTA: "-1"       # -1 = unlimited
PEERTUBE_IMPORT_VIDEOS_CONCURRENCY: "3"
PEERTUBE_STORAGE_VIDEOS: "/data/videos"                # Custom path
PEERTUBE_STORAGE_LOGS: "/data/logs"
PEERTUBE_STORAGE_TMP_PERSISTENT: "/data/tmp"
```

For multi-disk setups, mount a separate HDD for video storage and keep the SSD for the database and config:

```yaml
volumes:
  - /mnt/hdd/peertube/videos:/data/videos
  - ./docker-volume/config:/config
  - ./docker-volume/data:/data
```

### Cleanup and Maintenance

Enable automatic cleanup of failed uploads and temporary files:

```yaml
PEERTUBE_STORAGE_TMP_PERSISTENT_DURATION: "1h"
PEERTUBE_OBJECT_STORAGE_ENABLED: "false"  # Set true for S3-compatible backends
```

For larger instances, consider offloading video storage to **MinIO** or **Backblaze B2**:

```yaml
PEERTUBE_OBJECT_STORAGE_ENABLED: "true"
PEERTUBE_OBJECT_STORAGE_ENDPOINT: "s3.us-west-002.backblazeb2.com"
PEERTUBE_OBJECT_STORAGE_UPLOAD_ACL_PUBLIC: "public-read"
PEERTUBE_OBJECT_STORAGE_UPLOAD_ACL_PRIVATE: "private"
PEERTUBE_OBJECT_STORAGE_CREDENTIALS_ACCESS_KEY_ID: "your_access_key"
PEERTUBE_OBJECT_STORAGE_CREDENTIALS_SECRET_ACCESS_KEY: "your_secret_key"
PEERTUBE_OBJECT_STORAGE_MAX_UPLOAD_PART: 1073741824  # 1GB parts
```

---

## Federation and the Fediverse

Federation is what makes PeerTube special. Instead of being a standalone island, your instance becomes part of a global network.

### How Federation Works

When you subscribe to a channel on another PeerTube instance, your server periodically polls that remote server for new videos. When someone on a remote instance follows your channel, your server pushes video updates to theirs via ActivityPub.

### Enabling and Configuring Federation

```yaml
PEERTUBE_WEBSERVER_HOSTNAME: video.example.com
PEERTUBE_INSTANCE_NAME: "My Video Platform"
PEERTUBE_INSTANCE_DESCRIPTION: "A self-hosted video platform for our community"
PEERTUBE_INSTANCE_SHORT_DESCRIPTION: "Independent video hosting"
PEERTUBE_TRUST_PROXY: "true"
```

Under **Administration → Configuration → Federation**:

- **Allow following remote accounts**: Enable to let your users follow channels on other instances
- **Allow instance to follow**: Enable to let your instance's admin account follow remote channels
- **Auto-follow index**: Consider following `video.index.fediverse.observer` for content discovery

### PeerTube ↔ Mastodon Integration

PeerTube integrates natively with Mastodon:

1. When you publish a video, PeerTube can auto-post to a linked Mastodon account
2. Mastodon users can follow PeerTube channels and see new videos in their timeline
3. Video embeds appear as rich cards in Mastodon posts

Configure this under **Administration → Configuration → Federation → ActivityPub**:

```yaml
PEERTUBE_INSTANCE_DEFAULT_CHANNEL_NAME: "main"
PEERTUBE_TRAILING_DOMAIN: "video.example.com"
```

### Instance Blocking and Moderation

You control what content appears on your instance:

```yaml
# Block specific instances
PEERTUBE_INSTANCE_FOLLOWERS_INSTANCE_LIST: "spam-instance.example,another-bad.example"

# Block by regex in video titles/descriptions
# Configured via the admin UI: Moderation → Blocklist
```

---

## Performance Tuning

A well-tuned PeerTube instance can serve hundreds of concurrent viewers on modest hardware.

### NGINX Caching

The built-in NGINX configuration already includes basic caching. For higher traffic, add explicit cache headers:

```nginx
# Add to your NGINX config or use the PeerTube config template
location ~ ^/static/(webseed|redundancy)/ {
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

### Database Optimization

For PostgreSQL, tune these settings in `postgresql.conf`:

```ini
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
work_mem = 8MB
max_connections = 100
```

### Redis Configuration

PeerTube uses Redis for job queues and caching. For production:

```yaml
PEERTUBE_REDIS_AUTH: ""           # Set a password if Redis is network-accessible
PEERTUBE_REDIS_DB: 0
PEERTUBE_WORKERS_VIDEOS_TRANSCODING: "2"   # Match CPU cores
PEERTUBE_WORKERS_VIDEOS_LIVE: "1"
PEERTUBE_WORKERS_MISCELLANEOUS: "2"
```

### Monitoring

Use the built-in health check endpoint:

```bash
curl -s https://video.example.com/api/v1/server/health | python3 -m json.tool
```

For comprehensive monitoring, export metrics to Prometheus:

```yaml
# Install the PeerTube Prometheus exporter
pip install peertube-prometheus-exporter

# Add to docker-compose
  exporter:
    image: your-org/peertube-exporter:latest
    environment:
      PEERTUBE_URL: "http://peertube:9000"
    ports:
      - "9100:9100"
```

---

## Backup and Disaster Recovery

Your video content is irreplaceable. Set up automated backups:

### Database Backup

```bash
#!/bin/bash
# backup-db.sh
DATE=$(date +%Y%m%d_%H%M%S)
docker compose exec postgres pg_dump -U peertube peertube | \
  gzip > /backup/peertube-db-${DATE}.sql.gz

# Keep last 30 days
find /backup -name "peertube-db-*.sql.gz" -mtime +30 -delete
```

Add to crontab:
```cron
0 2 * * * /path/to/backup-db.sh
```

### Video File Backup

```bash
# rsync to a backup server
rsync -avz --progress /mnt/hdd/peertube/videos/ \
  backup-server:/mnt/backup/peertube/videos/

# Or use restic for deduplicated encrypted backups
restic -r /backup/peertube-restic backup \
  /mnt/hdd/peertube/videos/ \
  /mnt/hdd/peertube/config/
```

### Full Instance Migration

To move your PeerTube instance to a new server:

1. Stop the current instance: `docker compose down`
2. Copy all volumes: `rsync -avz ./docker-volume/ new-server:/path/`
3. Copy database backup and restore on new server
4. Update DNS to point to the new server IP
5. Start on new server: `docker compose up -d`

The domain name must remain the same for federation to work correctly. ActivityPub URLs are tied to the domain, and changing it breaks all existing followers.

---

## Mobile Access and Third-Party Apps

PeerTube doesn't have official mobile apps, but the fediverse ecosystem provides options:

| App | Platform | Notes |
|-----|----------|-------|
| **TubiTeka** | Android | Dedicated PeerTube client, open source |
| **PeerTube Mobile** | Android | Lightweight viewer with subscription support |
| **Fedilab** | Android | Multi-protocol fediverse app (Mastodon + PeerTube) |
| **Web PWA** | Any | Install PeerTube as a Progressive Web App |
| **Video web embeds** | Any | Embed videos on any website or blog |

To enable PWA support, ensure your NGINX serves the service worker correctly — the default PeerTube configuration handles this automatically.

---

## Common Pitfalls and Troubleshooting

### Video Upload Fails

Check transcoding logs:
```bash
docker compose logs peertube | grep -i "transcode"
```
Common causes: insufficient disk space, FFmpeg not available, or the video format is unsupported.

### Federation Not Working

1. Verify your domain resolves correctly: `dig video.example.com`
2. Check that TLS is valid: `curl -I https://video.example.com`
3. Ensure ActivityPub endpoints are reachable: `curl https://video.example.com/.well-known/webfinger?resource=acct:admin@video.example.com`
4. Check the federation queue in **Administration → Logs**

### High Bandwidth Usage

- Enable WebTorrent P2P — viewers seed to each other, reducing server bandwidth
- Set up redundancy with remote PeerTube instances that mirror your popular videos
- Configure transcoding to fewer resolutions to reduce total file size
- Consider a CDN or object storage for hot content

### Database Growth

Over time, the PostgreSQL database grows with view counts, federation data, and activity logs. Clean up periodically:

```bash
# Via the admin UI: Administration → Logs → Auto-delete logs older than X days
# Or directly:
PEERTUBE_LOG_ROTATION_ENABLED: "true"
PEERTUBE_LOG_ROTATION_MAX_FILE_SIZE: "10mb"
PEERTUBE_LOG_ROTATION_MAX_FILES: "10"
```

---

## When PeerTube Is the Right Choice

PeerTube excels when:

- You want a **YouTube-like experience** without YouTube's downsides
- You value **content independence** — your videos belong to you
- Your community benefits from **federation** and cross-instance discovery
- You need **live streaming** with open-source tooling
- You want **direct monetization** through viewer support rather than ad revenue
- You're building a **community platform** where video is a core feature

It may not be the best fit if:

- You need massive scale (millions of concurrent viewers) — consider a CDN-first architecture
- You require official mobile apps with push notifications
- You want algorithmic content discovery and recommendation

---

## Getting Started Today

The fastest path to your own PeerTube instance:

1. Provision a VPS with 4 CPU cores, 8 GB RAM, and 100 GB storage
2. Point a domain to the server IP
3. Deploy with Docker Compose using the configuration above
4. Set up TLS with Let's Encrypt
5. Create your first channel and upload a video
6. Follow other instances to join the fediverse

The entire setup takes under 30 minutes. Your video platform, your rules, your data.

**PeerTube repository**: [github.com/Chocobozzz/PeerTube](https://github.com/Chocobozzz/PeerTube)
**Official documentation**: [docs.joinpeertube.org](https://docs.joinpeertube.org/)
**Fediverse instance directory**: [instances.joinpeertube.org](https://instances.joinpeertube.org/)
