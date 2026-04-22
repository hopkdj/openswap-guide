---
title: "Watchtower vs Diun vs Dockcheck: Best Docker Container Update Tools 2026"
date: 2026-04-22
tags: ["comparison", "guide", "self-hosted", "docker", "containers"]
draft: false
description: "Compare Watchtower, Diun, and Dockcheck — the top self-hosted Docker container update tools. Find out which approach (auto-update, notification-only, or semi-automatic with backups) fits your home server."
---

Keeping Docker containers up to date is one of the most tedious tasks in self-hosting. New images with security patches and bug fixes are published daily, but manually checking and updating dozens of containers quickly becomes unmanageable. That is where Docker container update tools come in.

This guide compares three popular open-source solutions: **Watchtower**, **Diun**, and **Dockcheck**. Each takes a fundamentally different approach — from fully automatic updates to notification-only alerts — so you can pick the one that matches your risk tolerance and workflow.

## Why You Need a Container Update Tool

Running outdated containers is one of the most common security mistakes self-hosters make. When a vulnerability is disclosed in a base image (Alpine, Debian, Ubuntu), every container built on top of it inherits that risk. The fix is to pull the updated image and recreate the container — but doing this manually for 20+ services every week is not sustainable.

A container update tool automates or at least assists with this process. The question is not *whether* to automate, but *how much* automation you are comfortable with. Do you want:

- **Full automation** — the tool pulls and restarts containers without asking?
- **Notifications only** — you get alerted, but you decide when to update?
- **Semi-automatic** — the tool checks, backs up old images, and updates only the containers you approve?

The three tools below cover all three approaches.

## Watchtower: Fully Automatic Container Updates

**GitHub:** [containrrr/watchtower](https://github.com/containrrr/watchtower)
**Stars:** 24,584 | **Language:** Go | **Last Update:** December 2025

Watchtower is the most well-known Docker container auto-update tool. It monitors your running containers, checks for new images on the registry, and automatically pulls and restarts containers when updates are available — all without human intervention.

### How It Works

Watchtower runs as a container itself. It connects to the Docker socket, periodically polls for new image digests, and when it detects a change, it gracefully stops the old container, pulls the new image, and recreates the container with the same configuration.

### Docker Compose Configuration

The simplest production-ready setup:

```yaml
services:
  watchtower:
    image: containrrr/watchtower:latest
    container_name: watchtower
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - WATCHTOWER_POLL_INTERVAL=3600
      - WATCHTOWER_CLEANUP=true
      - WATCHTOWER_INCLUDE_RESTARTING=true
    restart: unless-stopped
```

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `WATCHTOWER_POLL_INTERVAL` | Seconds between checks | 86400 (24h) |
| `WATCHTOWER_CLEANUP` | Remove old images after update | false |
| `WATCHTOWER_INCLUDE_RESTARTING` | Include containers in restarting state | false |
| `WATCHTOWER_MONITOR_ONLY` | Monitor without updating | false |
| `WATCHTOWER_SCHEDULE` | Cron expression for check timing | Every 24h |

### Updating Specific Containers

By default, Watchtower monitors all running containers. To limit it to specific services:

```yaml
services:
  watchtower:
    image: containrrr/watchtower:latest
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: watchtower container1 container2 container3 --interval 3600
    restart: unless-stopped
```

Or use labels to include/exclude individual containers:

```yaml
services:
  myapp:
    image: myapp:latest
    labels:
      - "com.centurylinklabs.watchtower.enable=true"
  stable-service:
    image: stable-service:latest
    labels:
      - "com.centurylinklabs.watchtower.enable=false"
```

### Notifications

Watchtower supports notifications via Shoutrrr, which integrates with Slack, Discord, Telegram, Gotify, email, and more:

```yaml
environment:
  - WATCHTOWER_NOTIFICATIONS=shoutrrr
  - "WATCHTOWER_NOTIFICATION_URL=discord://token@channel"
  - "WATCHTOWER_NOTIFICATION_URL=telegram://token@telegram?channels=chatid"
```

## Diun: Notification-Only Docker Image Monitoring

**GitHub:** [crazy-max/diun](https://github.com/crazy-max/diun)
**Stars:** 4,592 | **Language:** Go | **Last Update:** April 2026

Diun takes a fundamentally different approach from Watchtower. Instead of updating containers automatically, it monitors Docker registries and sends notifications when new image versions are available. You stay in control — Diun tells you what changed, and you decide when and how to update.

This is the safer approach for production environments or for self-hosters who want to review changelogs before applying updates.

### How It Works

Diun connects to the Docker socket (or Docker Swarm, or Kubernetes), reads the currently running containers, and checks their registries for new image manifests. When a new version is detected, it sends a notification through your chosen channel with details about the old and new image digests.

### Docker Compose Configuration

```yaml
name: diun

services:
  diun:
    image: ghcr.io/crazy-max/diun:latest
    container_name: diun
    command: serve
    volumes:
      - "./diun-data:/data"
      - "/var/run/docker.sock:/var/run/docker.sock"
    environment:
      - "TZ=UTC"
      - "DIUN_WATCH_WORKERS=20"
      - "DIUN_WATCH_SCHEDULE=0 */6 * * *"
      - "DIUN_WATCH_JITTER=30s"
      - "DIUN_PROVIDERS_DOCKER=true"
      - "DIUN_NOTIF_GOTIFY_ENDPOINT=https://gotify.example.com"
      - "DIUN_NOTIF_GOTIFY_TOKEN=app-token"
    labels:
      - "diun.enable=true"
    restart: unless-stopped
```

Key configuration options:

| Variable | Description | Default |
|----------|-------------|---------|
| `DIUN_WATCH_SCHEDULE` | Cron expression for checks | Every 6 hours |
| `DIUN_WATCH_WORKERS` | Parallel registry check workers | 20 |
| `DIUN_WATCH_JITTER` | Random delay to avoid thundering herd | 30s |
| `DIUN_PROVIDERS_DOCKER` | Enable Docker provider | false |
| `DIUN_PROVIDERS_SWARM` | Enable Docker Swarm provider | false |
| `DIUN_PROVIDERS_KUBERNETES` | Enable Kubernetes provider | false |

### Notification Providers

Diun supports a wide range of notification backends:

- **Gotify** — self-hosted push notifications
- **Mail** — SMTP email
- **Discord** — webhook notifications
- **Slack** — webhook or bot
- **Telegram** — bot notifications
- **Ntfy** — self-hosted notification service
- **Mattermost** — team messaging
- **Rocketchat** — self-hosted chat

Example with multiple notification channels:

```yaml
environment:
  - "DIUN_NOTIF_GOTIFY_ENDPOINT=https://gotify.example.com"
  - "DIUN_NOTIF_GOTIFY_TOKEN=abc123"
  - "DIUN_NOTIF_MAIL_HOST=smtp.example.com"
  - "DIUN_NOTIF_MAIL_PORT=587"
  - "DIUN_NOTIF_MAIL_USERNAME=diun@example.com"
  - "DIUN_NOTIF_MAIL_PASSWORD=secret"
  - "DIUN_NOTIF_MAIL_TO=me@example.com"
  - "DIUN_NOTIF_MAIL_FROM=diun@example.com"
```

### Per-Container Labels

Like Watchtower, Diun uses labels to control which containers are monitored:

```yaml
services:
  critical-db:
    image: postgres:16
    labels:
      - "diun.enable=true"
      - "diun.watch_repo=true"
  experimental:
    image: myapp:dev
    labels:
      - "diun.enable=false"
```

The `diun.watch_repo=true` label tells Diun to check all tags in the repository, not just the one currently in use.

## Dockcheck: Semi-Automatic Updates with Image Backups

**GitHub:** [mag37/dockcheck](https://github.com/mag37/dockcheck)
**Stars:** 2,290 | **Language:** Shell | **Last Update:** April 2026

Dockcheck is a bash-based CLI tool that strikes a balance between Watchtower and Diun. It checks for updates, can notify you, supports automatic image backups for rollback, and offers both interactive and unattended modes. It is lightweight — no container needed, just a shell script — and has built-in Docker Hub pull limit awareness.

### How It Works

Dockcheck scans running containers, compares their current image digests against the registry, and presents a summary. In interactive mode, you choose which containers to update. In automatic mode (`-a` or `-y`), it updates everything (or a filtered subset) while optionally backing up old images first for easy rollback.

### Installation and Usage

Dockcheck is a standalone script:

```bash
# Download the latest release
curl -sL https://raw.githubusercontent.com/mag37/dockcheck/main/dockcheck.sh -o dockcheck.sh
chmod +x dockcheck.sh
./dockcheck.sh
```

Or run it from a Docker container using a volume mount:

```bash
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /path/to/config:/config \
  ghcr.io/mag37/dockcheck:latest
```

### Configuration File

Dockcheck uses a `default.config` file for persistent settings:

```ini
# Notification settings (Apprise format)
NOTIFY=
# Exclude containers from checks
EXCLUDE=
# Include only specific containers
INCLUDE=
# Max concurrent registry checks
MAXPROC=1
# Timeout per container check (seconds)
TIMEOUT=10
```

### Common Commands

| Command | Description |
|---------|-------------|
| `./dockcheck.sh` | Interactive check — lists updates, prompts to apply |
| `./dockcheck.sh -n` | Check only, no updates |
| `./dockcheck.sh -a` | Automatic update for all containers |
| `./dockcheck.sh -b 30` | Enable backups, keep for 30 days |
| `./dockcheck.sh -e nextcloud,heimdall` | Exclude specific containers |
| `./dockcheck.sh -i` | Check and send notification |
| `./dockcheck.sh -d 7` | Only update images 7+ days old (avoid breaking changes) |
| `./dockcheck.sh -c /path/to/dir` | Export Prometheus metrics |

### Automation with Cron

Run Dockcheck daily via cron and get notified only when updates are available:

```bash
# /etc/cron.d/dockcheck
0 3 * * * root /opt/dockcheck/dockcheck.sh -a -i -b 14 >> /var/log/dockcheck.log 2>&1
```

This updates automatically (`-a`), sends a notification (`-i`), and keeps 14-day image backups (`-b 14`).

## Feature Comparison Table

| Feature | Watchtower | Diun | Dockcheck |
|---------|------------|------|-----------|
| **Primary function** | Auto-update | Notify only | Check + optional update |
| **Language** | Go | Go | Shell |
| **GitHub Stars** | 24,584 | 4,592 | 2,290 |
| **Last Updated** | Dec 2025 | Apr 2026 | Apr 2026 |
| **Runs as container** | Yes | Yes | Optional |
| **Auto-update** | Yes (default) | No | Optional (`-a`) |
| **Image backup/rollback** | No | No | Yes (`-b N`) |
| **Exclude/Include containers** | Labels or CLI args | Labels | CLI args or config |
| **Notification support** | Shoutrrr (20+ providers) | 10+ built-in providers | Apprise (60+ providers) |
| **Docker Hub rate limit aware** | No | No | Yes |
| **Cron scheduling** | Built-in | Built-in | External (crontab) |
| **Docker Swarm support** | No | Yes | No |
| **Kubernetes support** | No | Yes | No |
| **Age-based filtering** | No | No | Yes (`-d N`) |
| **Prometheus metrics** | Yes (with flag) | No | Yes (`-c`) |
| **Compose stack awareness** | Basic | No | Yes (`-F`) |

## Which Tool Should You Choose?

### Choose Watchtower if:

- You want **set-and-forget** automation
- Your workloads are stateless or well-backed up
- You run a small home lab where occasional breakage is acceptable
- You prefer a single container that handles everything

Watchtower is the "it just works" option. For most hobby self-hosters running standard containers (media servers, dashboards, reverse proxies), it is the simplest path to always-running latest versions.

### Choose Diun if:

- You want **full control** over when updates are applied
- You run production or business-critical services
- You want to review changelogs before updating
- You use Docker Swarm or Kubernetes

Diun is the conservative choice. It never touches your containers — it only alerts you. Pair it with a simple update script or your [Docker Compose guide](../docker-compose-guide/) workflow, and you have a safe, reviewable update pipeline.

### Choose Dockcheck if:

- You want **the best of both worlds** — check first, update optionally
- You want **image backups** for easy rollback
- You want to avoid Docker Hub rate limits during checks
- You prefer a lightweight script over running another container

Dockcheck is the pragmatic middle ground. The `-d 7` flag (wait 7 days before updating) alone makes it safer than Watchtower for most use cases, because it lets early adopters catch breaking changes before they reach your server.

## Combining Tools for Maximum Safety

A popular pattern among experienced self-hosters is to **combine Diun + Dockcheck**:

1. **Diun** monitors all containers and sends notifications about new images
2. **Dockcheck** runs daily via cron with `-a -b 14` to auto-update with 14-day backups
3. If an update breaks something, roll back by retagging the backed-up image

This gives you notifications for awareness, automatic updates for convenience, and image backups as a safety net. The full setup:

```yaml
name: update-pipeline

services:
  diun:
    image: ghcr.io/crazy-max/diun:latest
    command: serve
    volumes:
      - "./diun-data:/data"
      - "/var/run/docker.sock:/var/run/docker.sock"
    environment:
      - "DIUN_WATCH_SCHEDULE=0 */6 * * *"
      - "DIUN_PROVIDERS_DOCKER=true"
      - "DIUN_NOTIF_GOTIFY_ENDPOINT=https://gotify.example.com"
      - "DIUN_NOTIF_GOTIFY_TOKEN=your-token"
    restart: unless-stopped
```

```bash
# Cron entry for Dockcheck (runs daily at 3 AM)
0 3 * * * root /opt/dockcheck/dockcheck.sh -a -b 14 -i >> /var/log/dockcheck.log 2>&1
```

## Related Reading

For a complete container management setup, pair your update tool with a management dashboard. See our [Portainer vs Dockge vs Yacht guide](../self-hosted-container-management-dashboards-portainer-dockge-yacht-guide/) for container UI options, and our [Harbor vs Distribution vs Zot comparison](../harbor-vs-distribution-vs-zot-self-hosted-container-registry-guide/) for managing private registries. If you use Docker Compose heavily, check our [complete Docker Compose guide](../docker-compose-guide/) for best practices on structuring multi-container stacks that work well with auto-updates.

## FAQ

### Is Watchtower safe for production use?

Watchtower auto-updates containers without testing, which can cause downtime if a new image has breaking changes. For production, consider Watchtower's `WATCHTOWER_MONITOR_ONLY=true` mode (notify without updating), or switch to Diun for notification-only monitoring. Always ensure you have backups before enabling full auto-update.

### What is the difference between Watchtower and Diun?

Watchtower automatically pulls new images and restarts containers. Diun only notifies you when new images are available — it never modifies running containers. Watchtower is for hands-off automation; Diun is for controlled, human-reviewed updates.

### Can Dockcheck run inside a Docker container?

Yes. While Dockcheck is primarily a standalone bash script, you can run it as a Docker container by mounting the Docker socket: `docker run --rm -v /var/run/docker.sock:/var/run/docker.sock:ro ghcr.io/mag37/dockcheck:latest`. However, the standalone script approach is more common and avoids the overhead of an extra container.

### How do I avoid Docker Hub pull rate limits when checking for updates?

Dockcheck is specifically designed to avoid triggering Docker Hub rate limits — it checks registry metadata (HTTP HEAD requests) without pulling full images. Diun does the same by checking manifest digests. Watchtower, however, may trigger rate limits if it pulls many images simultaneously. For Docker Hub users, consider mirroring images through a local registry like Harbor or using a pull-through cache.

### How do I roll back a container if an auto-update breaks it?

With Dockcheck, use the `-b N` flag to keep image backups for N days. To roll back, retag the backed-up image and recreate the container:
```bash
docker tag myimage:backup-20260422 myimage:latest
docker compose up -d myservice
```
Without backups, check Docker image history with `docker images --filter "dangling=true"` to find the old image ID, then retag it.

### Does Watchtower support Docker Compose stacks?

Watchtower can update individual containers but does not have native awareness of Docker Compose stack dependencies. If container B depends on container A and both need updating, Watchtower may restart them out of order. Dockcheck's `-F` flag addresses this by updating only the specific container rather than the whole compose stack, and Dockcheck's `-f` flag force-restarts the entire stack after updates.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Watchtower vs Diun vs Dockcheck: Best Docker Container Update Tools 2026",
  "description": "Compare Watchtower, Diun, and Dockcheck — the top self-hosted Docker container update tools. Find out which approach (auto-update, notification-only, or semi-automatic with backups) fits your home server.",
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
