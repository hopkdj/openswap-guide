---
title: "Sonarr vs Radarr vs Prowlarr vs Bazarr vs Lidarr: Complete Media Automation Guide 2026"
date: 2026-04-22
tags: ["comparison", "guide", "self-hosted", "media", "automation"]
draft: false
description: "Complete guide to the *arr media automation stack — Sonarr, Radarr, Prowlarr, Bazarr, Lidarr, and Readarr. Learn how to set up a fully automated self-hosted media server with Docker in 2026."
---

Building a self-hosted media server is one of the most popular projects in the home lab community. But manually searching for new TV episodes, movies, music albums, and subtitles is tedious. That's where the **\*arr stack** comes in — a family of open-source automation tools that handle the entire media lifecycle: discovery, download, renaming, and library organization.

In this guide, we'll cover every tool in the *arr ecosystem, compare their features side by side, and show you how to deploy the entire stack with a single Docker Compose file.

## Why Self-Host Media Automation

Cloud-based media services are convenient, but they come with limitations: content licensing varies by region, libraries shrink when contracts expire, and you have zero control over quality or metadata. A self-hosted media automation stack solves all of these problems:

- **Full library control** — you decide what stays, what quality you want, and how it's organized
- **Zero recurring costs** — no monthly subscriptions for content management
- **Privacy** — your viewing habits and library stay on your own hardware
- **Automation** — new episodes and movies appear automatically without any manual intervention
- **Custom quality profiles** — prioritize file size, resolution, audio codecs, or subtitle availability

The *arr tools work by monitoring RSS feeds and indexers for new releases of the media you want. When a match is found, they send the release to your download client (like [Sabnzbd or qBittorrent](../sabnzbd-vs-nzbget-vs-nzbhydra2-self-hosted-usenet-downloaders-guide/)), then rename and organize the finished file into your media library.

## The *arr Ecosystem at a Glance

Each tool in the *arr family handles a specific media type or function. They share a common architecture built on the .NET/ReactJS stack, giving them a consistent web interface and API design.

### Sonarr — TV Shows

| Detail | Value |
|--------|-------|
| **GitHub** | [Sonarr/Sonarr](https://github.com/Sonarr/Sonarr) |
| **Stars** | 13,689 |
| **Last Updated** | April 21, 2026 |
| **Language** | C# |
| **Purpose** | TV series PVR — monitors, downloads, and organizes TV episodes |

Sonarr is the original and most mature tool in the stack. It monitors RSS feeds for new episodes of your tracked TV shows, grabs them via your configured download client, renames them according to your preferred pattern (S01E01, 1x01, etc.), and places them in your media folder. It supports both Usenet and BitTorrent protocols.

Key features include calendar views, quality profiles (e.g., "prefer 1080p BluRay with AAC audio"), custom format scoring, episode-level manual search, and series-level automation rules.

### Radarr — Movies

| Detail | Value |
|--------|-------|
| **GitHub** | [Radarr/Radarr](https://github.com/Radarr/Radarr) |
| **Stars** | 13,498 |
| **Last Updated** | April 19, 2026 |
| **Language** | C# |
| **Purpose** | Movie collection manager — monitors, downloads, and organizes films |

Radarr is essentially Sonarr's sibling, retooled for movies instead of TV series. It tracks movies by their TMDb (The Movie Database) ID, monitors for new releases matching your quality preferences, and handles the download-rename-organize pipeline.

Key features include multiple movie collections, upgrade handling (e.g., replace a 720p release when a 4K version becomes available), custom format scoring, automatic movie metadata fetching, and collection-level quality profiles.

### Lidarr — Music

| Detail | Value |
|--------|-------|
| **GitHub** | [Lidarr/Lidarr](https://github.com/Lidarr/Lidarr) |
| **Stars** | 5,246 |
| **Last Updated** | April 19, 2026 |
| **Language** | C# |
| **Purpose** | Music collection manager — monitors, downloads, and organizes albums |

Lidarr brings the same automation model to music. It tracks artists via MusicBrainz, monitors for new album releases, and downloads them through your configured indexer/download client chain.

Music has unique challenges compared to video — albums are smaller, release formats vary (FLAC vs MP3, various bitrates), and metadata accuracy matters more for library browsing. Lidarr handles these with genre filters, release type controls (album vs single vs EP), and MusicBrainz-based metadata matching.

### Bazarr — Subtitles

| Detail | Value |
|--------|-------|
| **GitHub** | [morpheus65535/bazarr](https://github.com/morpheus65535/bazarr) |
| **Stars** | 3,941 |
| **Last Updated** | April 21, 2026 |
| **Language** | Python |
| **Purpose** | Subtitle management companion for Sonarr and Radarr |

Bazarr is the only tool in the stack not written in C#. It integrates directly with Sonarr and Radarr to automatically search for and download subtitles for your downloaded media. You can configure language preferences, subtitle provider priorities, and per-series or per-movie subtitle settings.

Bazarr supports dozens of subtitle providers including OpenSubtitles, Subscene, Podnapisi, and many more. It can also score existing subtitle files against your video files to ensure proper sync.

### Prowlarr — Indexer Management

| Detail | Value |
|--------|-------|
| **GitHub** | [Prowlarr/Prowlarr](https://github.com/Prowlarr/Prowlarr) |
| **Stars** | 6,398 |
| **Last Updated** | April 12, 2026 |
| **Language** | C# |
| **Purpose** | Centralized indexer manager and proxy for all *arr applications |

Prowlarr is the glue that holds the entire stack together. Instead of configuring the same torrent trackers and Usenet indexers separately in Sonarr, Radarr, and Lidarr, you configure them once in Prowlarr and it syncs them across all connected *arr apps via API.

Prowlarr supports both Torznab (torrent) and Newznab (Usenet) indexer formats, plus raw RSS feeds. It includes indexer health monitoring, category mapping, and release profile management. For self-hosters running a [download manager like pyLoad or JDownloader](../pyload-vs-aria2-vs-jdownloader-self-hosted-download-manager-2026/), Prowlarr provides the search results that feed into those tools.

### Readarr — Books

| Detail | Value |
|--------|-------|
| **GitHub** | [Readarr/Readarr](https://github.com/Readarr/Readarr) |
| **Stars** | 3,452 |
| **Last Updated** | June 27, 2025 |
| **Language** | C# |
| **Purpose** | eBook and audiobook collection manager |

Readarr extends the *arr model to books. It tracks authors and books via metadata providers, monitors for new releases, and automates downloads. It supports both eBook (EPUB, MOBI, PDF) and audiobook formats.

Note that Readarr is still in active development and considered less mature than the other *arr tools, but it's fully functional for most use cases.

## Comparison Table

| Feature | Sonarr | Radarr | Lidarr | Bazarr | Prowlarr | Readarr |
|---------|--------|--------|--------|--------|----------|---------|
| **Media Type** | TV Shows | Movies | Music | Subtitles | Indexers | Books |
| **Language** | C# | C# | C# | Python | C# | C# |
| **GitHub Stars** | 13,689 | 13,498 | 5,246 | 3,941 | 6,398 | 3,452 |
| **Usenet Support** | Yes | Yes | Yes | N/A | Yes | Yes |
| **Torrent Support** | Yes | Yes | Yes | N/A | Yes | Yes |
| **Quality Profiles** | Yes | Yes | Yes | N/A | N/A | Yes |
| **Custom Formats** | Yes | Yes | Partial | N/A | N/A | Partial |
| **Calendar View** | Yes | Partial | Yes | Yes | Yes | Yes |
| **Metadata Source** | TheTVDB | TMDb | MusicBrainz | N/A | N/A | Goodreads |
| **Subtitle Support** | Via Bazarr | Via Bazarr | N/A | Native | N/A | N/A |
| **Docker Image** | linuxserver | linuxserver | linuxserver | linuxserver | linuxserver | linuxserver |
| **Maturity** | Stable | Stable | Stable | Stable | Stable | Develop |

## Which Tools Do You Actually Need?

Not every self-hosted media server needs the full stack. Here are common configurations:

**Minimal setup (movies + TV only):**
- Sonarr + Radarr + Prowlarr + a download client

**Complete media stack:**
- Sonarr + Radarr + Lidarr + Bazarr + Prowlarr + Readarr + download client

**TV-focused setup:**
- Sonarr + Bazarr + Prowlarr + download client

Prowlarr is recommended in all setups because it eliminates redundant indexer configuration across tools. If you only use one *arr app, you can skip Prowlarr and configure indexers directly.

## Docker Compose Setup

None of the *arr projects ship official Docker Compose files in their repositories. However, the [LinuxServer.io](https://linuxserver.io/) community maintains excellent, well-documented Docker images for every tool in the stack. They use a consistent configuration pattern with `PUID`, `PGID`, and `TZ` environment variables.

Here's a complete Docker Compose file that deploys the core *arr stack:

```yaml
services:
  sonarr:
    image: lscr.io/linuxserver/sonarr:latest
    container_name: sonarr
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    volumes:
      - ./sonarr/config:/config
      - ./media/tv:/tv
      - ./downloads:/downloads
    ports:
      - "8989:8989"
    restart: unless-stopped

  radarr:
    image: lscr.io/linuxserver/radarr:latest
    container_name: radarr
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    volumes:
      - ./radarr/config:/config
      - ./media/movies:/movies
      - ./downloads:/downloads
    ports:
      - "7878:7878"
    restart: unless-stopped

  lidarr:
    image: lscr.io/linuxserver/lidarr:latest
    container_name: lidarr
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    volumes:
      - ./lidarr/config:/config
      - ./media/music:/music
      - ./downloads:/downloads
    ports:
      - "8686:8686"
    restart: unless-stopped

  bazarr:
    image: lscr.io/linuxserver/bazarr:latest
    container_name: bazarr
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    volumes:
      - ./bazarr/config:/config
      - ./media/movies:/movies
      - ./media/tv:/tv
    ports:
      - "6767:6767"
    restart: unless-stopped

  prowlarr:
    image: lscr.io/linuxserver/prowlarr:latest
    container_name: prowlarr
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    volumes:
      - ./prowlarr/config:/config
    ports:
      - "9696:9696"
    restart: unless-stopped

  readarr:
    image: lscr.io/linuxserver/readarr:develop
    container_name: readarr
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    volumes:
      - ./readarr/config:/config
      - ./media/books:/books
      - ./downloads:/downloads
    ports:
      - "8787:8787"
    restart: unless-stopped
```

To start everything:

```bash
mkdir -p {sonarr,radarr,lidarr,bazarr,prowlarr,readarr}/config
mkdir -p media/{tv,movies,music,books}
mkdir -p downloads/{complete,incomplete}
docker compose up -d
```

Default web interface ports:

| Application | URL | Default Port |
|-------------|-----|-------------|
| Sonarr | `http://localhost:8989` | 8989 |
| Radarr | `http://localhost:7878` | 7878 |
| Lidarr | `http://localhost:8686` | 8686 |
| Bazarr | `http://localhost:6767` | 6767 |
| Prowlarr | `http://localhost:9696` | 9696 |
| Readarr | `http://localhost:8787` | 8787 |

## Setting Up Prowlarr as Your Indexer Hub

Prowlarr should be your first configuration step. Here's the recommended order:

1. **Add indexers in Prowlarr** — configure your torrent trackers and/or Usenet indexers
2. **Connect Prowlarr to each *arr app** — in each app's Settings → Indexers, select "Prowlarr" and enter the API key
3. **Configure download clients** — set up Sabnzbd, qBittorrent, or your preferred downloader in each *arr app
4. **Add media** — search for TV shows in Sonarr, movies in Radarr, artists in Lidarr

Each *arr app communicates with Prowlarr via its REST API. When you add or remove an indexer in Prowlarr, the change propagates automatically to all connected apps within minutes.

For users who want to let family and friends request media, consider adding a request manager on top. Our guide to [Overseerr vs Jellyseerr vs Ombi](../2026-04-21-overseerr-vs-jellyseerr-vs-ombi-self-hosted-media-requests-guide-2026/) covers the best options for adding a user-facing request layer to your *arr stack.

## Configuration Best Practices

### Quality Profiles

Set up quality profiles that match your storage capacity and network speed:

```
Profile: 1080p Preferred
  - Upgrade allowed: Yes
  - Minimum quality: WEBDL-720p
  - Preferred quality: WEBDL-1080p, Bluray-1080p
  - Maximum size: 8 GB per movie / 3 GB per episode
```

### File Naming

Consistent file naming makes everything work smoothly with media servers like Jellyfin, Plex, or Emby:

```
# Sonarr (TV Shows)
Series Name (Year)/Season XX/Series Name (Year) - SXXEXX - Episode Title.ext

# Radarr (Movies)
Movie Title (Year)/Movie Title (Year) [Quality-Group].ext

# Lidarr (Music)
Artist/Album (Year)/Artist - Album.ext
```

### Reverse Proxy with Nginx

If you're exposing any of these services externally, put them behind a reverse proxy:

```nginx
server {
    listen 443 ssl;
    server_name sonarr.example.com;

    ssl_certificate /etc/letsencrypt/live/sonarr.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sonarr.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8989;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Managing Your Stack from a Dashboard

With six different web interfaces to manage, a centralized dashboard becomes invaluable. Our [self-hosted homepage dashboard guide](../self-hosted-homepage-dashboards-homepage-dashy-homarr-guide/) covers Homepage, Dashy, and Homarr — all of which integrate beautifully with the *arr APIs to show download status, disk usage, and upcoming releases at a glance.

## Frequently Asked Questions

### What is the *arr stack?

The *arr stack is a collection of open-source media automation tools that share a common architecture and naming convention. Each tool ends in "arr" — Sonarr (TV), Radarr (movies), Lidarr (music), Bazarr (subtitles), Prowlarr (indexers), and Readarr (books). Together they automate the entire media lifecycle: discovery, download, renaming, and library organization.

### Do I need all six *arr applications?

No. Start with the tools that match your media needs. If you only watch TV and movies, Sonarr + Radarr + Prowlarr is enough. Add Lidarr if you collect music, Bazarr if you need subtitles, and Readarr if you manage an eBook library. Prowlarr is recommended for any setup with two or more *arr apps because it centralizes indexer management.

### Can the *arr tools work with both Usenet and torrents?

Yes. Sonarr, Radarr, Lidarr, and Readarr all support both Usenet (via NZB) and BitTorrent protocols. You can configure multiple download clients in each app and set priority rules (e.g., "prefer Usenet over torrents when both are available"). Prowlarr manages indexers for both protocol types in a single interface.

### Is the *arr stack legal to use?

The *arr applications themselves are legal, open-source software. They are media management tools — similar to how a web browser is a legal tool regardless of what websites you visit. However, what you download through them is subject to the copyright laws in your jurisdiction. Always ensure you have the legal right to download and store any media content.

### How do I update the *arr applications?

If you're using Docker (recommended), updating is straightforward:

```bash
docker compose pull
docker compose up -d
```

This pulls the latest LinuxServer.io images and restarts all containers with minimal downtime. Your configuration and library data persist in the mounted volumes, so nothing is lost during updates.

### Can I use the *arr stack without Prowlarr?

Yes. Before Prowlarr existed, users configured indexers directly in each *arr app. However, this means duplicating configuration across Sonarr, Radarr, Lidarr, etc. When you add or remove an indexer, you must update every app individually. Prowlarr eliminates this redundancy by acting as a single source of truth for indexer configuration.

### What download clients work with the *arr stack?

For Usenet: **Sabnzbd** and **NZBGet** are the most popular. For torrents: **qBittorrent**, **Transmission**, and **rTorrent** are well-supported. The *arr apps handle sending release information to the download client, monitoring download progress, and processing completed files. You can find detailed comparisons of Usenet downloaders in our [Sabnzbd vs NZBGet guide](../2026-04-21-sabnzbd-vs-nzbget-vs-nzbhydra2-self-hosted-usenet-downloaders-guide/).

### How much disk space do I need?

This depends entirely on your media library size and quality preferences. A rough estimate:

- **TV Shows**: ~1-2 GB per episode at 1080p, ~500 MB at 720p
- **Movies**: ~4-8 GB per movie at 1080p, ~15-25 GB at 4K
- **Music**: ~100 MB per album in FLAC, ~80 MB in 320kbps MP3

Plan for at least 2-4 TB if you're building a substantial media library. Consider using a separate disk for downloads (incomplete files) and media (final organized library) to avoid fragmentation.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Sonarr vs Radarr vs Prowlarr vs Bazarr vs Lidarr: Complete Media Automation Guide 2026",
  "description": "Complete guide to the *arr media automation stack — Sonarr, Radarr, Prowlarr, Bazarr, Lidarr, and Readarr. Learn how to set up a fully automated self-hosted media server with Docker in 2026.",
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
