---
title: "Revolt vs Discord: Best Self-Hosted Chat Platform 2026"
date: 2026-04-12
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete guide to self-hosting Revolt as an open source Discord alternative in 2026. Includes Docker Compose deployment, configuration, bot development, and migration tips."
---

If you run a community, manage a team, or simply value control over your communication tools, the idea of hosting your own chat platform is compelling. Discord dominates the group chat space, but it comes with trade-offs: closed source, opaque data practices, arbitrary server limits, and the risk of sudden bans or policy changes.

**Revolt** is an open source, self-hostable chat platform designed from the ground up to look and feel like Discord while giving you full ownership of your data, your infrastructure, and your community. In this guide, we'll cover what Revolt is, why you'd want to self-host it, and how to get a production-ready instance running with Docker Compose.

## Why Self-Host Your Chat Platform

Running someone else's service is convenient until it isn't. Here's why taking control of your chat infrastructure makes sense:

- **Full data ownership.** Your messages, files, and user data live on your server. No third-party analytics, no advertising, no data mining.
- **No arbitrary limits.** Free Discord servers cap at 500 members unless you pay for boosts. Self-hosted Revolt has no such restrictions — your hardware is the only limit.
- **Privacy compliance.** If you operate in a jurisdiction with strict data protection laws (GDPR, CCPA), self-hosting gives you complete control over data retention, encryption, and access logs.
- **Customization.** Modify the client, add features, integrate with internal tools, or white-label the entire platform. Open source means no walls.
- **Resilience.** Discord outages take down millions of communities simultaneously. Your self-hosted instance is independent — it's up when you need it.
- **Cost predictability.** For large communities, Discord Nitro and boost costs add up. A $10–20/month VPS hosts Revolt for thousands of users with no per-feature charges.

## What Is Revolt?

Revolt is a free, open source user-facing chat platform with an architecture inspired by Discord. It features servers, channels (text and voice), roles and permissions, custom emojis, bots, and a polished web and desktop client — all under the GNU AGPLv3 license.

Key characteristics:

| Feature | Details |
|---------|---------|
| **License** | GNU AGPLv3 |
| **Backend** | Rust (high performance, low memory) |
| **Frontend** | React + Svelte web client |
| **Database** | MongoDB |
| **Caching** | Redis |
| **Real-time** | WebSocket-based messaging |
| **Voice** | WebRTC voice channels |
| **Bots** | REST + WebSocket bot API |
| **Mobile** | Community-built Android and iOS apps |
| **Self-hosting** | Fully supported via Docker |

The project is split into several components:

- **revolt.js** — Client library for web and desktop
- **autumn** — File/attachment upload service
- **january** — Embed/proxy service for links and images
- **quark** — Image manipulation and rendering
- **delta** — Core API and WebSocket server
- **web app** — The browser-based chat interface

## Revolt vs Discord: Feature Comparison

Before we dive into deployment, let's see how Revolt stacks up against Discord:

| Feature | Revolt (Self-Hosted) | Discord |
|---------|---------------------|---------|
| **Cost** | Free (your server cost) | Free tier limited; Nitro for perks |
| **Source Code** | Fully open (AGPLv3) | Closed source |
| **Data Ownership** | You control everything | Discord's servers, Discord's rules |
| **Server Member Limit** | Unlimited | 500 (free), up to 5000 with boosts |
| **File Upload Limit** | Configurable (you set it) | 25 MB (free), 500 MB (Nitro) |
| **Custom Emojis** | Unlimited | 50–250 depending on level |
| **Voice Channels** | WebRTC-based | Proprietary |
| **Bot API** | REST + WebSocket, open | REST + WebSocket, documented |
| **End-to-End Encryption** | Not built-in (self-hosting helps) | Not available |
| **Moderation Tools** | Built-in roles, permissions, bans | Advanced AutoMod, audit logs |
| **Screen Sharing** | Via WebRTC voice channels | Yes, up to 4K with Nitro |
| **Server Folders** | Supported | Nitro-only feature |
| **Mobile Apps** | Community-built | Official apps |
| **API Documentation** | Open source, community-maintained | Official docs |

**Where Discord still leads:** Discord has a massive user base, polished mobile apps, superior moderation tooling (AutoMod), and seamless screen sharing. If your community depends on reaching people where they already are, Discord's network effect is hard to beat.

**Where Revolt wins:** Complete self-hosting, no limits, no vendor lock-in, full data ownership, and the peace of mind that comes with running open source infrastructure you can audit and modify.

## Deploying Revolt with Docker Compose

The recommended way to run Revolt is with Docker Compose. This setup includes all required services: the core API, file uploads, embed proxy, MongoDB, Redis, and the web client.

### Prerequisites

- A Linux server with at least 2 GB RAM (4 GB recommended)
- Docker and Docker Compose installed
- A domain name (e.g., `chat.example.com`) with DNS pointing to your server
- TLS certificates (we'll use Caddy for automatic HTTPS)

### Step 1: Create the Project Directory

```bash
mkdir -p ~/revolt && cd ~/revolt
```

### Step 2: Create the Docker Compose File

Create a `docker-compose.yml` that defines all Revolt services:

```yaml
version: "3.8"

services:
  revolt-api:
    image: revolt.chat/delta:latest
    restart: unless-stopped
    ports:
      - "5000:8000"
    environment:
      AUTUMN_URL: "http://autumn:8000"
      JANUARY_URL: "http://january:8000"
      VOSKO_URL: ""
      MONGO_DATABASE_URL: "mongodb://mongo:27017/revolt"
      REDIS_URL: "redis://redis:6379"
      RABBITMQ_URL: ""
      SENTRY_DSN: ""
      FRONTEND_URL: "https://app.example.com"
      REVOLT_EXTERNAL_URL: "https://api.example.com"
      VITE_API_URL: "https://api.example.com"
      VITE_WS_URL: "wss://api.example.com"
    depends_on:
      - mongo
      - redis
      - autumn
      - january
    networks:
      - revolt-net

  autumn:
    image: revolt.chat/autumn:latest
    restart: unless-stopped
    ports:
      - "5001:8000"
    volumes:
      - ./autumn:/autumn/files
    environment:
      AUTUMN_FILESIZE_LIMIT: 26214400
    networks:
      - revolt-net

  january:
    image: revolt.chat/january:latest
    restart: unless-stopped
    ports:
      - "5002:8000"
    environment:
      JANUARY_MAX_CONTENT_LENGTH: 20971520
    networks:
      - revolt-net

  mongo:
    image: mongo:7
    restart: unless-stopped
    volumes:
      - mongo-data:/data/db
    environment:
      MONGO_INITDB_DATABASE: revolt
    networks:
      - revolt-net

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis-data:/data
    networks:
      - revolt-net

  revolt-web:
    image: revolt.chat/client:latest
    restart: unless-stopped
    ports:
      - "5003:5000"
    environment:
      VITE_API_URL: "https://api.example.com"
      VITE_WS_URL: "wss://api.example.com"
      VITE_AUTUMN_URL: "https://autumn.example.com"
    depends_on:
      - revolt-api
    networks:
      - revolt-net

  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy-data:/data
      - caddy-config:/config
    networks:
      - revolt-net

volumes:
  mongo-data:
  redis-data:
  caddy-data:
  caddy-config:

networks:
  revolt-net:
    driver: bridge
```

### Step 3: Configure Caddy for TLS

Create a `Caddyfile` for automatic HTTPS:

```
api.example.com {
    reverse_proxy revolt-api:8000
}

autumn.example.com {
    reverse_proxy autumn:8000
}

app.example.com {
    reverse_proxy revolt-web:5000
}
```

Replace `example.com` with your actual domain. Caddy automatically obtains and renews TLS certificates from Let's Encrypt.

### Step 4: Launch the Stack

```bash
docker compose up -d
```

Wait for all containers to start:

```bash
docker compose ps
```

You should see all seven services running. Check the logs if anything looks off:

```bash
docker compose logs -f revolt-api
```

### Step 5: Create Your First Admin Account

Revolt's first user registered automatically becomes the instance administrator. Visit `https://app.example.com` and create an account — that user will have full administrative access to the platform.

Alternatively, if you want to create the admin via the API:

```bash
curl -X POST https://api.example.com/auth/account/create \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "username": "admin",
    "password": "your-secure-password-here",
    "invite": null,
    "captcha": null
  }'
```

### Step 6: Configure Instance Settings

Access the Revolt API to configure instance-wide settings. You'll need the admin user's session token:

```bash
# After logging in, get your session token from browser dev tools
# or use the API directly

# Set instance-wide upload limits
curl -X PATCH https://api.example.com/admin/instance/file_size \
  -H "x-bot-token: YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"file_size_limit": 52428800}'
```

## Advanced Configuration

### Customizing the Web Client

The Revolt web client supports environment variables for deep customization:

```yaml
  revolt-web:
    image: revolt.chat/client:latest
    environment:
      VITE_API_URL: "https://api.example.com"
      VITE_WS_URL: "wss://api.example.com"
      VITE_AUTUMN_URL: "https://autumn.example.com"
      VITE_JANUARY_URL: "https://january.example.com"
      VITE_THEMING_PRESET: "dark"
      VITE_CUSTOM_BRANDING: "My Community Chat"
      VITE_CUSTOM_CSS_URL: "https://example.com/custom.css"
```

You can inject custom CSS to rebrand the client with your community colors and logo.

### Running Behind an Existing Reverse Proxy

If you already use Nginx or Traefik, skip the Caddy container and configure proxying manually. Here's an Nginx example:

```nginx
server {
    listen 443 ssl;
    server_name api.example.com;

    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support — critical for real-time messaging
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**Important:** WebSocket proxying is non-negotiable. Without proper `Upgrade` and `Connection` headers, real-time messaging will fail and users will see constant disconnects.

### Bot Development

Revolt has a straightforward bot API. Here's a simple Python bot using the `revolt.py` library:

```python
from revolt import Client, Message

class MyBot(Client):
    async def on_message(self, message: Message):
        if message.content == "!ping":
            await message.channel.send("Pong! 🏓")

        if message.content == "!uptime":
            import time
            await message.channel.send(f"Uptime: {time.time() - start_time:.0f}s")

        if message.content == "!help":
            await message.channel.send(
                "Available commands:\n"
                "`!ping` — Check if bot is alive\n"
                "`!uptime` — Show bot uptime\n"
                "`!help` — Show this message"
            )

start_time = __import__("time").time()

bot = MyBot(bot_token="YOUR_BOT_TOKEN")
bot.run()
```

Install the library:

```bash
pip install revolt.py
```

The bot API supports event listeners for messages, member joins, role changes, server creation, and more. You can also interact with the REST API directly:

```bash
# Send a message as a bot
curl -X POST "https://api.example.com/channels/CHANNEL_ID/messages" \
  -H "x-bot-token: YOUR_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello from the API!"}'
```

### Database Backups

Never skip backups. MongoDB and Redis both support live snapshots:

```bash
#!/bin/bash
# backup.sh — Run this daily via cron

BACKUP_DIR="/backups/revolt/$(date +%Y-%m-%d)"
mkdir -p "$BACKUP_DIR"

# MongoDB dump
docker exec revolt-mongo-1 mongodump \
  --archive="$BACKUP_DIR/mongo.dump" \
  --gzip

# Redis snapshot
docker cp revolt-redis-1:/data/dump.rdb "$BACKUP_DIR/redis.rdb"

# Keep only the last 7 days
find /backups/revolt -maxdepth 1 -type d -mtime +7 -exec rm -rf {} \;

echo "Backup complete: $BACKUP_DIR"
```

Add to crontab for daily execution:

```bash
0 3 * * * /home/user/revolt/backup.sh >> /var/log/revolt-backup.log 2>&1
```

## Migration Strategies from Discord

Moving an entire community from Discord to Revolt requires planning. Here's a practical approach:

### Phase 1: Parallel Operation (Week 1–2)

Run both platforms simultaneously. Set up Revolt with matching server and channel names. Announce the new platform in Discord and encourage early adopters to join.

### Phase 2: Content Migration

While there's no official migration tool, you can programmatically export Discord data (via the Discord API or your data download) and import it into Revolt's API. Focus on:

- Server and channel structure (names, categories)
- Role definitions and permissions
- Static content like rules, welcome messages, and pinned posts

User passwords and message history cannot be directly migrated due to platform differences.

### Phase 3: Transition (Week 3–4)

Move community-critical bots first. Announce a cutover date. After the transition, set the Discord server to read-only mode for reference.

## Performance and Scaling

Revolt's Rust-based backend is lightweight. Here are realistic resource expectations:

| Scale | CPU | RAM | Notes |
|-------|-----|-----|-------|
| **Small (1–50 users)** | 1 core | 512 MB | Single-core VPS sufficient |
| **Medium (50–500 users)** | 2 cores | 1 GB | Comfortable headroom |
| **Large (500–5000 users)** | 4 cores | 2–4 GB | Consider Redis clustering |
| **Very Large (5000+)** | 8 cores | 4–8 GB | MongoDB replica set recommended |

For the largest deployments:

- **MongoDB:** Use a replica set for high availability
- **Redis:** Enable persistence and consider Redis Sentinel
- **Load balancing:** Deploy multiple `delta` instances behind a reverse proxy
- **CDN:** Put Caddy behind Cloudflare or a similar CDN for edge caching of static assets
- **File storage:** Mount autumn's file directory on a separate volume or S3-compatible storage

## Troubleshooting

### WebSocket Connections Failing

This is the most common issue. Check:

```bash
# Verify WebSocket upgrade works
wscat -c wss://api.example.com/

# Check if delta is listening
curl -v https://api.example.com/health

# Review Caddy logs for TLS issues
docker compose logs caddy
```

### High MongoDB Memory Usage

MongoDB uses available memory for caching by design. Limit it if needed:

```yaml
  mongo:
    image: mongo:7
    command: ["--wiredTigerCacheSizeGB", "1"]
```

### Files Not Uploading

Check the autumn service and ensure volume mounts are correct:

```bash
docker compose logs autumn
ls -la ./autumn/
```

Ensure the `AUTUMN_FILESIZE_LIMIT` matches your expectations (value is in bytes — 26214400 = 25 MB).

## Alternatives to Consider

Revolt isn't the only self-hosted chat option. Depending on your needs, these alternatives may be worth evaluating:

| Platform | Best For | Language | Complexity |
|----------|----------|----------|------------|
| **Matrix/Element** | Federation, E2E encryption | Rust + Python | Medium |
| **Mattermost** | Enterprise, Slack-like UX | Go | Medium |
| **Rocket.Chat** | Omnichannel, integrations | TypeScript/Node.js | Medium |
| **Zulip** | Threaded conversations | Python | Medium |
| **Revolt** | Discord-like experience | Rust | Low–Medium |

Matrix excels at federation and encryption but has a steeper learning curve. Mattermost is polished and enterprise-ready but heavier on resources. Zulip's unique threading model is powerful but unfamiliar to Discord users. Revolt's advantage is familiarity — it looks and works like Discord, so your community members adapt instantly.

## Conclusion

Revolt is the most straightforward path to a self-hosted, Discord-like chat platform in 2026. It gives you the familiar server-and-channel model with none of the vendor lock-in, rate limits, or data concerns. With Docker Compose, a production instance takes under 10 minutes to deploy.

The trade-offs are real: smaller ecosystem, fewer third-party integrations, and community-built mobile apps that lag behind Discord's polish. But for communities that value sovereignty over convenience, Revolt is the best option available today.

**Your data, your server, your rules.** That's the entire point.
