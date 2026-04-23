---
title: "Self-Hosting Bluesky PDS: Complete Guide to Your Own AT Protocol Server 2026"
date: 2026-04-23
tags: ["comparison", "guide", "self-hosted", "privacy", "social"]
draft: false
description: "Complete guide to self-hosting a Bluesky Personal Data Server (PDS) using Docker. Compare with Mastodon, configure the AT Protocol, and take control of your social data."
---

Decentralized social networking is no longer a niche concept. With Bluesky's rapid growth — surpassing 30 million users in 2026 — the AT Protocol (Authenticated Transfer Protocol) has emerged as a compelling alternative to ActivityPub-based platforms like Mastodon. The key differentiator? Bluesky lets you **self-host your own Personal Data Server (PDS)**, giving you full ownership of your social graph, posts, and identity.

This guide walks you through setting up a Bluesky PDS from scratch using Docker, explains how the AT Protocol works, and compares self-hosting Bluesky against other decentralized social platforms.

## Why Self-Host a Bluesky PDS?

When you create a Bluesky account, your data lives on Bluesky's servers by default. Self-hosting a PDS changes that equation entirely:

- **Full data ownership** — Your posts, follows, likes, and media are stored on your own server
- **Portable identity** — Move your handle and social graph to any other PDS without losing connections
- **No algorithmic manipulation** — Your feed is governed by the feeds you choose, not a corporate algorithm
- **Custom domain handles** — Use `@you.yourdomain.com` instead of `@you.bsky.social`
- **Censorship resistance** — Your content cannot be removed by a centralized authority
- **Federation with the wider ATProto network** — Interact with users on any PDS, including bluesky.social

For anyone who values digital sovereignty, a self-hosted PDS is the most direct way to participate in the decentralized social web without surrendering control of your data.

## What Is the AT Protocol?

The AT Protocol is the open networking technology that powers Bluesky. Unlike ActivityPub (used by Mastodon, Pixelfed, and Lemmy), which federates at the **server level**, the AT Protocol federates at the **individual account level**. This architectural difference has significant implications:

| Feature | AT Protocol (Bluesky) | ActivityPub (Mastodon) |
|---|---|---|
| Federation level | Per-account identity | Per-server identity |
| Account portability | Move accounts between servers seamlessly | Account migration is manual and limited |
| Identity system | DIDs (Decentralized Identifiers) + handles | `@user@instance.domain` |
| Feed algorithm | User-selectable custom feeds | Chronological, server-curated |
| Content moderation | Labelers + user-chosen moderation stacks | Server-level moderation policies |
| Repo model | Each user has a signed data repository (CAR files) | Posts stored in server database |
| Handle system | DNS-based or `.bsky.social` subdomains | Tied to server hostname |

The AT Protocol's account-level federation means your identity is not bound to a single server. You can migrate your entire social graph from a self-hosted PDS to any other PDS provider — or back again — without rebuilding your network from scratch.

## Bluesky PDS vs Mastodon: Which Should You Self-Host?

Both platforms offer self-hosting options, but they serve different needs. Here's a detailed comparison:

| Criteria | Bluesky PDS | Mastodon |
|---|---|---|
| **Primary focus** | Individual identity portability | Community-run servers |
| **GitHub stars** | 2,475 (pds repo) | 49,855 |
| **Last update** | April 2026 | April 2026 |
| **Language** | Shell/TypeScript | Ruby |
| **Resource requirements** | ~512MB RAM, 1 vCPU | ~2GB RAM, 2 vCPU minimum |
| **Docker complexity** | 3 containers (PDS, Caddy, Watchtower) | 6+ containers (web, streaming, sidekiq, Redis, PostgreSQL, optional Elasticsearch) |
| **Database** | SQLite (built-in) | PostgreSQL (required) |
| **Setup time** | ~15 minutes | ~1-2 hours |
| **Reverse proxy** | Built-in Caddy with auto-TLS | Manual Nginx/Traefik configuration |
| **Auto-updates** | Watchtower included | Manual or external tool required |
| **Content types** | Posts, images, embeds | Posts, images, polls, video (via extensions) |
| **Federation** | ATProto network | ActivityPub/Fediverse |
| **Custom domain** | Native DNS handle support | Requires additional configuration |

**Choose Bluesky PDS if:** You want a lightweight, individual-focused server with automatic TLS, simple Docker setup, and portable identity.

**Choose Mastodon if:** You want to run a community server with fine-grained moderation tools, custom themes, and a large existing ecosystem of plugins and integrations.

For personal use with minimal maintenance overhead, Bluesky PDS is the more streamlined option. For building a community with dozens or hundreds of users, Mastodon's feature set is more comprehensive.

## Prerequisites

Before setting up your Bluesky PDS, ensure you have:

- A **VPS or dedicated server** with at least 512MB RAM and 10GB disk (1 vCPU minimum, 2 recommended)
- A **domain name** with DNS access (required for your custom handle)
- **Docker** and **Docker Compose** installed
- **Root or sudo access** to the server
- Ports **80 and 443** open (for Caddy's automatic TLS)
- A valid **email address** (for account recovery notifications)

```bash
# Install Docker on Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose plugin
sudo apt-get install -y docker-compose-plugin

# Verify installation
docker --version
docker compose version
```

## Step-by-Step PDS Installation

The official Bluesky PDS ships as a Docker Compose stack that includes Caddy for automatic HTTPS and Watchtower for auto-updates. Here is the complete setup process.

### Step 1: Create the Directory Structure

```bash
# Create base directory
sudo mkdir -p /pds/caddy/data
sudo mkdir -p /pds/caddy/etc/caddy
sudo mkdir -p /pds
sudo chown -R $USER:$USER /pds
```

### Step 2: Create the Environment File

Create `/pds/pds.env` with your configuration:

```bash
cat > /pds/pds.env << 'ENVEOF'
PDS_HOSTNAME=bsky.yourdomain.com
PDS_JWT_SECRET=$(openssl rand -base64 32)
PDS_ADMIN_PASSWORD=$(openssl rand -base64 24)
PDS_DID_PLC_URL=https://plc.directory
PDS_BSKY_APP_VIEW_URL=https://api.bsky.app
PDS_BSKY_APP_VIEW_DID=did:web:api.bsky.app
PDS_REPORT_SERVICE_URL=https://api.bsky.app/xrpc
PDS_REPORT_SERVICE_DID=did:web:api.bsky.app
ENVEOF

# Generate secure secrets
sed -i "s/PDS_JWT_SECRET=.*/PDS_JWT_SECRET=$(openssl rand -base64 32)/" /pds/pds.env
sed -i "s/PDS_ADMIN_PASSWORD=.*/PDS_ADMIN_PASSWORD=$(openssl rand -base64 24)/" /pds/pds.env

# Verify the file
cat /pds/pds.env
```

### Step 3: Create the Docker Compose File

The official compose file from the [bluesky-social/pds repository](https://github.com/bluesky-social/pds) (2,475 stars, last updated April 2026):

```yaml
version: '3.9'
services:
  caddy:
    container_name: caddy
    image: caddy:2
    network_mode: host
    depends_on:
      - pds
    restart: unless-stopped
    volumes:
      - type: bind
        source: /pds/caddy/data
        target: /data
      - type: bind
        source: /pds/caddy/etc/caddy
        target: /etc/caddy

  pds:
    container_name: pds
    image: ghcr.io/bluesky-social/pds:0.4
    network_mode: host
    restart: unless-stopped
    volumes:
      - type: bind
        source: /pds
        target: /pds
    env_file:
      - /pds/pds.env

  watchtower:
    container_name: watchtower
    image: ghcr.io/nicholas-fedor/watchtower:latest
    network_mode: host
    volumes:
      - type: bind
        source: /var/run/docker.sock
        target: /var/run/docker.sock
    restart: unless-stopped
    environment:
      WATCHTOWER_CLEANUP: true
      WATCHTOWER_SCHEDULE: "@midnight"
```

Save this as `/pds/compose.yaml`.

### Step 4: Configure DNS

Add an **A record** pointing your subdomain to the server's IP address:

```
Type    Name              Value
A       bsky              YOUR_SERVER_IP
```

For IPv6, also add an **AAAA record**. DNS propagation typically takes 5-15 minutes.

### Step 5: Launch the PDS

```bash
cd /pds
docker compose up -d

# Verify containers are running
docker compose ps

# Check logs
docker compose logs -f pds
```

The PDS should start within 30 seconds. Caddy will automatically obtain a TLS certificate via Let's Encrypt.

### Step 6: Create Your Account

Use the `pdsadmin` CLI tool included in the PDS container:

```bash
# Enter the PDS container
docker exec -it pds bash

# Inside the container, create your account
pdsadmin account create \
  --handle bsky.yourdomain.com \
  --email your@email.com \
  --password YourSecurePassword123!

# Exit the container
exit
```

### Step 7: Verify Your Server

```bash
# Check the PDS health endpoint
curl -s https://bsky.yourdomain.com/health | python3 -m json.tool

# Expected output:
# {
#     "version": "0.4.x",
#     "name": "pds"
# }

# Verify TLS certificate
curl -sI https://bsky.yourdomain.com | head -5
```

## Managing Your Self-Hosted PDS

### Updating the Server

Watchtower handles automatic updates by default. For manual updates:

```bash
cd /pds
docker compose pull
docker compose up -d
docker image prune -f
```

### Creating Additional Accounts

```bash
docker exec -it pds pdsadmin account create \
  --handle user2.yourdomain.com \
  --email user2@email.com \
  --password AnotherSecurePassword!
```

### Resetting a Password

```bash
docker exec -it pds pdsadmin account reset-password \
  --handle bsky.yourdomain.com
```

### Backing Up Your Data

Your PDS data lives in `/pds`. Back it up regularly:

```bash
# Create a compressed backup
tar czf /backup/pds-backup-$(date +%Y%m%d).tar.gz /pds

# Or use rsync to a remote server
rsync -avz /pds/ backup-server:/backups/pds/

# Automate with cron (daily at 2 AM)
echo "0 2 * * * tar czf /backup/pds-backup-\$(date +\%Y\%m\%d).tar.gz /pds" | crontab -
```

### Monitoring Resource Usage

```bash
# Check disk usage
du -sh /pds

# Monitor container resource usage
docker stats pds --no-stream

# Check available disk space
df -h /pds
```

## Alternative Self-Hosted Social Platforms

If Bluesky's AT Protocol doesn't fit your needs, several other decentralized social platforms are worth considering:

| Platform | Protocol | Best For | Min RAM | Docker Containers |
|---|---|---|---|---|
| **Bluesky PDS** | ATProto | Individual users, portable identity | 512MB | 3 |
| **Mastodon** | ActivityPub | Community servers, rich features | 2GB | 6+ |
| **Misskey** | ActivityPub | Feature-rich microblogging (11,130 stars) | 1GB | 5+ |
| **GoToSocial** | ActivityPub | Lightweight single-user server | 256MB | 1 |
| **Pixelfed** | ActivityPub | Photo sharing (Instagram alternative) | 1GB | 4+ |
| **WriteFreely** | ActivityPub | Long-form blogging | 256MB | 1 |

For users who want the simplest possible self-hosted social presence, GoToSocial (Go-based, single binary) or [WriteFreely](../writefreely-self-hosted-blogging-platform-guide/) (minimal blogging) offer lighter alternatives. For community building, Mastodon remains the most mature option with the largest user base — see our [complete fediverse guide](../self-hosted-fediverse-mastodon-pixelfed-lemmy-guide/) for a broader overview of ActivityPub-based platforms.

The AT Protocol's unique advantage is **account portability** — no other decentralized social platform lets you migrate your entire identity and social graph between servers as seamlessly. If you're also interested in decentralized video hosting, check out our [PeerTube self-hosting guide](../peertube-self-hosted-youtube-alternative-guide/).

## FAQ

### What is a Bluesky PDS and do I need to self-host one?

A Bluesky PDS (Personal Data Server) is your personal data repository on the AT Protocol network. You don't *need* to self-host one — you can use the default `bsky.social` servers. However, self-hosting gives you complete ownership of your data, a custom domain handle, and independence from any single provider's policies or uptime.

### How much does it cost to run a Bluesky PDS?

Running a personal PDS is very lightweight. A $5/month VPS with 1 vCPU and 512MB RAM is sufficient for a single user with moderate posting activity. Storage grows slowly — most personal accounts use less than 2GB even after months of active posting.

### Can I migrate my existing Bluesky account to a self-hosted PDS?

Yes. The AT Protocol's design allows account migration between PDS instances. You can move from `bsky.social` to your self-hosted PDS while retaining your followers, following list, and handle (if using a custom domain). The migration process preserves your DID (Decentralized Identifier), which is your permanent identity on the network.

### Do I need a domain name to self-host a Bluesky PDS?

Yes, a domain name is required. The PDS uses your domain for your handle (e.g., `bsky.yourdomain.com`) and for automatic TLS certificate provisioning via Caddy. You'll need to add an A record pointing to your server's IP address. Domain names typically cost $10-15/year from registrars like Namecheap or Cloudflare.

### How does moderation work on a self-hosted PDS?

The AT Protocol uses a **labeler system** rather than server-level moderation. You can subscribe to community labelers (including Bluesky's default moderation service) to filter unwanted content. Your PDS is only for your own account — you control what labelers you trust. This differs from Mastodon, where server admins moderate all users on their instance.

### Can multiple users share a single self-hosted PDS?

Yes. The official PDS supports multiple accounts on a single server. Each user gets their own handle under your domain (e.g., `alice.yourdomain.com`, `bob.yourdomain.com`). However, the PDS is designed for personal/small-group use. For larger communities with hundreds of users, Mastodon's multi-user architecture is more appropriate.

### How do I back up and restore my PDS data?

All PDS data is stored in the `/pds` directory. Regular backups can be done with `tar` or `rsync`. To restore, extract the backup to `/pds` on a new server and restart the Docker Compose stack. The SQLite database, user repositories (CAR files), and Caddy TLS certificates are all included in the `/pds` directory.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosting Bluesky PDS: Complete Guide to Your Own AT Protocol Server 2026",
  "description": "Complete guide to self-hosting a Bluesky Personal Data Server (PDS) using Docker. Compare with Mastodon, configure the AT Protocol, and take control of your social data.",
  "datePublished": "2026-04-23",
  "dateModified": "2026-04-23",
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
