---
title: "AzuraCast vs LibreTime vs Icecast: Self-Hosted Internet Radio Stations 2026"
date: 2026-04-19
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Run your own internet radio station with AzuraCast, LibreTime, or Icecast. Complete comparison with Docker setup guides, streaming configurations, and broadcast automation."
---

Running your own internet radio station gives you complete control over what your audience hears. No corporate playlists, no algorithmic recommendations, no licensing restrictions on what you can broadcast. Whether you want to share music, host talk shows, or run a community station, self-hosted radio software handles everything from playlist scheduling to live DJ connections and listener analytics.

This guide compares three of the most capable open-source options for building a self-hosted radio station — **AzuraCast**, **LibreTime**, and **Icecast** — with practical [docker](https://www.docker.com/) deployment instructions so you can go live in under an hour.

## Why Self-Host an Internet Radio Station

Broadcasting your own radio station from your own server offers advantages that cloud-hosted platforms simply cannot match:

- **Full content control** — Play whatever you want, whenever you want. No content guidelines, no algorithmic interference, no forced ads.
- **Unlimited listeners** — Your only constraint is your server's bandwidth. No tiered plans that cap your audience at 100 or 1,000 concurrent listeners.
- **No monthly fees** — All three tools covered here are free and open source. Your only cost is the server hardware or VPS hosting.
- **Privacy for listeners** — No third-party tracking, no listener data sold to advertisers, no profiling.
- **Custom branding** — Your station, your domain, your visual identity. No forced platform logos or watermarks.
- **Live DJ support** — Connect from anywhere using standard broadcasting software (BUTT, Mixxx) to take over the stream in real time.
- **AutoDJ functionality** — When no live DJ is connected, your station keeps running automatically with scheduled playlists, jingles, and station IDs.
- **Multiple mount points** — Run several channels or shows from a single server, each with its own playlist and schedule.

If you've explored self-hosted media servers like [Navidrome for music streaming](../navidrome-vs-funkwhale-vs-airsonic-self-hosted-music-guide/) or [Owncast for live video streaming](../self-hosted-live-[nginx](https://nginx.org/)ming-owncast-mediamtx-nginx-rtmp-guide-2026/), an internet radio station is the natural audio-only complement to your self-hosted media stack.

## The Three Contenders at a Glance

| Feature | AzuraCast | LibreTime | Icecast |
|---|---|---|---|
| **Primary Language** | PHP | PHP | C |
| **GitHub Stars** | 3,813 | 924 | 539 |
| **Last Updated** | April 2026 | April 2026 | January 2026 |
| **AutoDJ** | Built-in | Built-in | No (external source needed) |
| **Live DJ Support** | Yes (Icecast/KH + SHOUTcast) | Yes (via Liquidsoap) | Yes (source client) |
| **Web Interface** | Full admin dashboard | Schedule + admin UI | Minimal admin |
| **Multi-Station** | Yes | Single station | Yes (mount points) |
| **Listener Analytics** | Built-in charts | Basic stats | Basic via admin |
| **Scheduling** | Playlist-based + advanced | Show-based calendar | No (external) |
| **Streaming Backend** | Liquidsoap | Liquidsoap | Icecast core |
| **Database** | MariaDB | PostgreSQL | None (file-based) |
| **Docker Support** | Official, turnkey | Official compose | Community images |
| **Best For** | Full radio management | Broadcast automation | Minimal streaming server |

## AzuraCast: The All-in-One Radio Platform

AzuraCast is the most complete self-hosted radio solution available. It bundles everything you need into a single Docker deployment: the streaming server (Icecast-KH), the AutoDJ engine (Liquidsoap), a web-based management dashboard, and listener analytics. The result is a turnkey radio station you can deploy in minutes.

### Key Features

- **Multi-station support** — Run dozens of independent stations from one server, each with its own DJs, playlists, and branding.
- **AutoDJ with intelligent queuing** — Plays your music library automatically, handles crossfades, station IDs, and jingles. When a live DJ connects, AutoDJ gracefully hands off the stream.
- **Playlist scheduling** — Weight-based playlists, time-based schedules, and advanced rotation rules. Set different playlists for different times of day.
- **Web DJ** — Broadcast directly from the browser without installing additional software.
- **REST API** — Integrate with external tools, now-playing widgets, or custom mobile apps.
- **SFTP access** — Upload media files securely via SFTP directly into your station's media library.

### Docker Deployment

AzuraCast uses an installer script that generates a customized `docker-compose.yml`. The recommended approach:

```bash
# Create installation directory
mkdir -p /opt/azuracast && cd /opt/azuracast

# Download the installer
curl -fsSL https://raw.githubusercontent.com/AzuraCast/AzuraCast/main/docker.sh -o docker.sh

# Run the installer (prompts for ports, letsencrypt, etc.)
chmod a+x docker.sh
./docker.sh install
```

The installer creates a production-ready stack with the following services:

```yaml
# Simplified overview of AzuraCast's docker-compose structure
name: azuracast

services:
  web:
    image: ghcr.io/azuracast/azuracast:latest
    ports:
      - '80:80'
      - '443:443'
      - '2022:2022'    # SFTP for media uploads
      - '8000:8000'    # Icecast streaming port
      - '8005:8005'    # SHOUTcast streaming port
    volumes:
      - letsencrypt:/etc/letsencrypt
      - shoutcast2:/var/azuracast/servers/shoutcast2
      - geoip:/var/azuracast/geoip
      - stations:/var/azuracast/stations
      - backups:/var/azuracast/backups

  mariadb:
    image: mariadb:10.11
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: azuracast
      MYSQL_USER: azuracast
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
    volumes:
      - mariadb_data:/var/lib/mysql

  influxdb:
    image: influxdb:2.7
    volumes:
      - influxdb_data:/var/lib/influxdb2
```

The `stations` volume stores all uploaded media, playlists, and configuration per station. The installer handles SSL certificates via Let's Encrypt automatically.

### Resource Requirements

- **Minimum**: 1 vCPU, 1 GB RAM for a single station with AutoDJ
- **Recommended**: 2 vCPU, 2 GB RAM for multiple stations
- **Storage**: Depends on your music library — a typical 10,000-song library uses ~50 GB

## LibreTime: The Broadcast Automation Platform

LibreTime is the open-source successor to Sourcefabric's Airtime, designed specifically for radio broadcast automation. Where AzuraCast focuses on the complete radio station experience, LibreTime excels at scheduling and program management — making it ideal for community radio stations with multiple shows and volunteer DJs.

### Key Features

- **Show-based scheduling** — Build a weekly schedule with shows, recurring programs, and special events. Each show has its own playlist and host assignments.
- **Calendar interface** — Visual drag-and-drop calendar for programming your station's lineup.
- **Live assistant** — Web-based DJ interface for hosts to manage playback, queue tracks, and introduce segments during live shows.
- **Media library with metadata** — Full library management with tagging, cue points, and track analysis.
- **Rebroadcast support** — Record live shows and automatically rebroadcast them during off-hours.
- **Podcast export** — Automatically publish recorded shows as podcasts.

### Docker Deployment

LibreTime provides an official Docker Compose configuration. Create the following directory structure and files:

```bash
mkdir -p /opt/libretime && cd /opt/libretime
```

Create the `docker-compose.yml`:

```yaml
services:
  postgres:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-libretime}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-libretime}
    healthcheck:
      test: pg_isready -U libretime

  rabbitmq:
    image: rabbitmq:3.13-alpine
    environment:
      RABBITMQ_DEFAULT_VHOST: /libretime
      RABBITMQ_DEFAULT_USER: libretime
      RABBITMQ_DEFAULT_PASS: libretime
    healthcheck:
      test: nc -z 127.0.0.1 5672

  playout:
    image: ghcr.io/libretime/libretime-playout:latest
    init: true
    depends_on:
      - rabbitmq
    volumes:
      - ./config.yml:/etc/libretime/config.yml:ro
      - libretime_playout:/app
    environment:
      LIBRETIME_GENERAL_PUBLIC_URL: http://localhost:8080

  liquidsoap:
    image: ghcr.io/libretime/libretime-playout:latest
    command: /usr/local/bin/libretime-liquidsoap
    init: true
    ports:
      - 8001:8001
      - 8002:8002
    depends_on:
      - rabbitmq
    volumes:
      - ./config.yml:/etc/libretime/config.yml:ro
      - libretime_playout:/app

  analyzer:
    image: ghcr.io/libretime/libretime-analyzer:latest
    init: true
    depends_on:
      - rabbitmq
    volumes:
      - ./config.yml:/etc/libretime/config.yml:ro
      - libretime_storage:/srv/libretime

  worker:
    image: ghcr.io/libretime/libretime-worker:latest
    init: true
    depends_on:
      - rabbitmq
    volumes:
      - ./config.yml:/etc/libretime/config.yml:ro
      - libretime_storage:/srv/libretime

  legacy:
    image: ghcr.io/libretime/libretime-legacy:latest
    init: true
    ports:
      - 8080:80
    depends_on:
      - postgres
      - rabbitmq
    volumes:
      - ./config.yml:/etc/libretime/config.yml:ro
      - libretime_storage:/srv/libretime

  nginx:
    image: ghcr.io/libretime/libretime-nginx:latest
    ports:
      - 80:8080
    depends_on:
      - legacy

volumes:
  postgres_data:
  libretime_playout:
  libretime_storage:
```

Create the `.env` file with your passwords:

```bash
POSTGRES_PASSWORD=your-secure-password
LIBRETIME_GENERAL_SECRET_KEY=your-secret-key
```

Start the stack:

```bash
docker compose up -d
```

Then visit `http://your-server-ip` to complete the setup wizard. The web interface will guide you through creating your first show, uploading media, and configuring the broadcast output.

### Resource Requirements

- **Minimum**: 2 vCPU, 2 GB RAM (LibreTime runs more services: PostgreSQL, RabbitMQ, multiple containers)
- **Recommended**: 4 vCPU, 4 GB RAM for production use with media analysis
- **Storage**: Media library + PostgreSQL data — plan for at least 100 GB

## Icecast: The Minimal Streaming Server

Icecast is the foundational streaming server that powers many radio platforms — including both AzuraCast and LibreTime. If you want the simplest possible setup with minimal overhead, or you're building a custom radio pipeline with external tools, Icecast is the core component.

### Key Features

- **Lightweight** — Written in C, Icecast uses minimal CPU and memory. A single-core VPS with 512 MB RAM can serve hundreds of concurrent listeners.
- **Multiple mount points** — Each mount point (`/live`, `/music`, `/talk`) acts as an independent stream with its own listener count and metadata.
- **SHOUTcast and Icecast protocol support** — Compatible with virtually all broadcasting software.
- **Relay/chaining** — Cascade streams from one Icecast server to another for load distribution.
- **XSLT customization** — Customize the web interface and status pages with XSLT templates.
- **No built-in AutoDJ** — Icecast only serves streams. You need a separate source client to feed it content.

### Source Clients (Required)

Since Icecast has no AutoDJ, you need a source client to feed audio to the server:

| Source Client | Purpose | Platform |
|---|---|---|
| **BUTT** | Live DJ broadcasting | Windows, macOS, Linux |
| **Mixxx** | Live DJ with mixing | Windows, macOS, Linux |
| **Liquidsoap** | AutoDJ / playlist automation | Linux, cross-platform |
| **Darkice** | Live audio input encoding | Linux |
| **EZStream** | Playlist-based AutoDJ | Linux |

### Docker Deployment

Use the community-maintained Icecast image:

```yaml
services:
  icecast:
    image: castlabs/icecast:latest
    ports:
      - "8000:8000"
    volumes:
      - ./icecast.xml:/etc/icecast2/icecast.xml:ro
      - icecast_logs:/var/log/icecast2
    restart: unless-stopped

volumes:
  icecast_logs:
```

Create a basic `icecast.xml` configuration:

```xml
<icecast>
    <limits>
        <clients>100</clients>
        <sources>2</sources>
        <queue-size>524288</queue-size>
        <client-timeout>30</client-timeout>
        <header-timeout>15</header-timeout>
        <source-timeout>10</source-timeout>
    </limits>

    <authentication>
        <source-password>hackme</source-password>
        <relay-password>hackme</relay-password>
        <admin-user>admin</admin-user>
        <admin-password>admin</admin-password>
    </authentication>

    <hostname>your-server-domain.com</hostname>

    <listen-socket>
        <port>8000</port>
    </listen-socket>

    <mount>
        <mount-name>/live</mount-name>
        <max-listeners>100</max-listeners>
        <charset>UTF-8</charset>
    </mount>

    <fileserve>1</fileserve>

    <paths>
        <logdir>/var/log/icecast2</logdir>
        <webroot>/usr/share/icecast2/web</webroot>
        <adminroot>/usr/share/icecast2/admin</adminroot>
        <alias source="/" dest="/status.xsl"/>
    </paths>

    <logging>
        <accesslog>access.log</accesslog>
        <errorlog>error.log</errorlog>
        <loglevel>3</loglevel>
    </logging>

    <security>
        <chroot>0</chroot>
    </security>
</icecast>
```

Start Icecast and connect a source client like BUTT or Liquidsoap to `your-server-domain.com:8000` with the source password. Listeners connect to `http://your-server-domain.com:8000/live`.

### Resource Requirements

- **Minimum**: 1 vCPU, 512 MB RAM (can handle 100+ concurrent listeners)
- **Recommended**: 1 vCPU, 1 GB RAM for multiple mount points
- **Storage**: Minimal — only logs. No media storage needed on the server itself.

## Choosing the Right Tool

The decision depends on your use case:

- **Choose AzuraCast** if you want a complete, ready-to-go radio station. It handles everything from media upload to AutoDJ to listener analytics. The single-station minimum footprint is reasonable, and multi-station support makes it ideal for networks.

- **Choose LibreTime** if you run a community radio station with scheduled shows and volunteer DJs. The calendar-based scheduling and show management are unmatched. It requires more resources but delivers professional broadcast automation.

- **Choose Icecast** if you need a lightweight streaming endpoint and already have your own AutoDJ pipeline (like a custom Liquidsoap setup or a playlist script). It's the building block, not the complete solution.

### Quick Decision Matrix

| Need | AzuraCast | LibreTime | Icecast |
|---|---|---|---|
| Quick setup (under 30 min) | ✅ | ⚠️ | ✅ |
| Multiple stations | ✅ | ❌ | ⚠️ (mounts) |
| Visual schedule/calendar | ❌ | ✅ | ❌ |
| AutoDJ out of the box | ✅ | ✅ | ❌ |
| Minimal resource usage | ⚠️ | ❌ | ✅ |
| Community radio shows | ⚠️ | ✅ | ❌ |
| Custom streaming pipeline | ⚠️ | ⚠️ | ✅ |
| Listener analytics dashboard | ✅ | ⚠️ | ⚠️ |

## Reverse Proxy Setup

For production use, place your radio server behind a reverse proxy to handle SSL termination and domain routing. If you're using AzuraCast, it includes built-in Nginx with Let's Encrypt support. For LibreTime or standalone Icecast, configure a reverse proxy l[caddy](https://caddyserver.com/)Traefik or Nginx Proxy Manager](../nginx-vs-caddy-vs-traefik-self-hosted-web-server-guide-2026/) to handle HTTPS.

Example Nginx configuration for Icecast:

```nginx
server {
    listen 443 ssl;
    server_name radio.example.com;

    ssl_certificate /etc/letsencrypt/live/radio.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/radio.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## FAQ

### Can I run a radio station on a cheap VPS?

Yes. A $5-10/month VPS with 1-2 vCPUs and 1-2 GB RAM is sufficient for a single AzuraCast or Icecast station serving up to 100 concurrent listeners. LibreTime requires slightly more resources due to its additional services (PostgreSQL, RabbitMQ).

### What audio formats do these tools support?

AzuraCast and LibreTime both support MP3, OGG Vorbis, AAC, and FLAC streams. Icecast natively supports MP3, OGG Vorbis, WebM, and Opus. The format depends on your source client's encoding settings.

### How do I connect as a live DJ?

Download [BUTT (Broadcast Using This Tool)](https://danielnoethen.de/butt/) — it's free and works on Windows, macOS, and Linux. Configure it with your server's hostname, port (usually 8000), mount point (e.g., `/live`), and source password. Click "Connect" and you're broadcasting live. Mixxx is another free option that adds mixing capabilities.

### Is it legal to stream music on my own radio station?

Music licensing laws vary by country. In most jurisdictions, streaming copyrighted music publicly (even over the internet) requires a license from performing rights organizations. Check your local regulations. Creative Commons and royalty-free music can be streamed without licensing concerns.

### Can I relay my station to other platforms?

Yes. Both AzuraCast and Icecast support stream relays. You can forward your Icecast mount to other servers for redundancy, or use AzuraCast's built-in relay feature to broadcast to multiple downstream servers simultaneously.

### How do I add music to my station?

AzuraCast provides SFTP access — connect with any SFTP client (FileZilla, WinSCP) using the credentials shown in the station management panel. LibreTime allows media uploads through its web interface. For Icecast, you'll need to configure your source client (like Liquidsoap or EZStream) with a local music directory path.

### Can these tools handle 24/7 broadcasting?

Absolutely. All three tools are designed for continuous operation. AzuraCast and LibreTime's AutoDJ ensures the stream never goes silent, even when no live DJ is connected. Icecast stays running as long as a source client is feeding it audio — pair it with Liquidsoap for unattended 24/7 playback.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "AzuraCast vs LibreTime vs Icecast: Self-Hosted Internet Radio Stations 2026",
  "description": "Run your own internet radio station with AzuraCast, LibreTime, or Icecast. Complete comparison with Docker setup guides, streaming configurations, and broadcast automation.",
  "datePublished": "2026-04-19",
  "dateModified": "2026-04-19",
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
