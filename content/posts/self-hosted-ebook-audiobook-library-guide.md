---
title: "Self-Hosted Ebook & Audiobook Library: Calibre-Web vs Kavita vs Audiobookshelf 2026"
date: 2026-04-12
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Build your own digital library with Calibre-Web, Kavita, and Audiobookshelf. Complete setup guide with Docker configs, metadata management, and remote access."
---

If you collect ebooks, audiobooks, comics, or manga, relying on proprietary platforms means your library lives on someone else's servers. They can change pricing, remove titles, or shut down entirely. A self-hosted reading server puts you back in control: every file stays on your hardware, metadata belongs to you, and access works from any device on your network or over the internet.

This guide covers three of the best self-hosted options for managing and serving your digital book collection — **Calibre-Web**, **Kavita**, and **Audiobookshelf** — with practical setup instructions so you can deploy a working server in under an hour.

## Why Self-Host Your Book Library

Running your own book server solves problems that cloud platforms create:

- **No vendor lock-in** — Your files live in standard formats (EPUB, PDF, MOBI, M4B, CBZ) on storage you control. Migrate or switch servers at any time.
- **Complete metadata ownership** — Edit descriptions, covers, series order, and custom tags without platform restrictions.
- **Privacy** — Reading habits, annotations, and bookmarks never leave your network.
- **Unlimited storage** — Only limited by your disk space, not subscription tiers.
- **Family sharing** — One server serves every household member with individual accounts, reading progress, and preferences.
- **Works offline** — Once synced, your reading apps function without an internet connection.
- **Cost** — All three tools covered here are free and open source. No monthly fees, no per-book charges.

## The Three Contenders at a Glance

| Feature | Calibre-Web | Kavita | Audiobookshelf |
|---|---|---|---|
| **Primary Focus** | Ebooks (EPUB, PDF, MOBI, CBZ) | Ebooks, Comics, Manga (EPUB, PDF, CBZ, CBR) | Audiobooks & Podcasts (M4B, MP3, FLAC) |
| **Ebook Reading** | Built-in web reader | Built-in web reader | No (audio-focused) |
| **Audiobook Support** | Limited (basic playback) | No | Full (chapter navigation, playback speed, sleep timer) |
| **Comic/Manga** | Basic (CBZ/CBR display) | Excellent (page-by-page viewer) | No |
| **Multi-user** | Yes (with roles) | Yes | Yes |
| **OPDS Catalog** | Yes (OPDS v1 & v2) | Yes (OPDS v1.2) | Yes (OPDS v1.2) |
| **Metadata Source** | Calibre database | Built-in scraper | Audnexus, Google Books, Open Library |
| **Mobile Apps** | None (use OPDS + third-party) | None (use OPDS + third-party) | Official Android & iOS apps |
| **Podcast Support** | No | No | Yes (subscribe, download, sync) |
| **Language** | Python | C# (.NET) | Node.js (Vue.js frontend) |
| **Active Development** | Yes | Yes | Very active |

## Calibre-Web: The Calibre Ecosystem Extension

**Best for:** Users who already manage their library with the desktop Calibre application and want a web interface to browse, read, and download books from any device.

Calibre-Web is not a standalone library manager. It reads an existing Calibre database (`metadata.db`) and serves it through a clean, responsive web UI. If your workflow already revolves around Calibre's powerful desktop client for editing metadata, converting formats, and organizing collections, this is the natural complement.

### Key Features

- Clean, Material Design-inspired web interface
- Built-in EPUB reader with font and theme customization
- Kobo device synchronization (Kobo Sync API)
- OPDS feed for mobile reading apps
- User management with read-only, download, edit, upload, and admin roles
- Book upload via web interface
- Public shelf creation and curation
- Content restriction by category, tag, or series

### Docker Setup

```yaml
services:
  calibre-web:
    image: ghcr.io/linuxserver/calibre-web:latest
    container_name: calibre-web
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=America/New_York
      - DOCKER_MODS=linuxserver/mods:universal-calibre
    volumes:
      - ./config:/config
      - ./books:/books
    ports:
      - "8083:8083"
    restart: unless-stopped
```

Save this as `docker-compose.yml`, then run:

```bash
mkdir -p calibre-web/{config,books}
cd calibre-web
docker compose up -d
```

After the container starts, navigate to `http://your-server:8083`. The default login is **admin** with password **admin123** — change it immediately.

### Initial Configuration

The critical step is pointing Calibre-Web at your Calibre database. Set the **Calibre database location** to:

```
/books
```

This directory must contain a valid `metadata.db` file from Calibre's desktop application. If you're starting fresh, create the database by launching Calibre desktop, adding a few books, then copying the entire library folder to the `./books` volume.

Enable the **Allow uploads** setting if you want to add books directly through the web interface without touching the desktop client. Uploaded books will be added to the Calibre database automatically.

### Kobo Sync

One of Calibre-Web's standout features is native Kobo Sync support. Configure it in the admin panel:

1. Generate an API key in **Admin → Configuration → Kobo Sync**
2. On your Kobo device, go to Settings → Accounts → Sign In → Other → Kobo Sync
3. Enter the sync URL: `http://your-server:8083/kobo/{auth_token}`
4. Your reading progress, bookmarks, and library sync automatically

This transforms any Kobo e-reader into a client for your self-hosted library with zero cloud dependency.

---

## Kavita: The Modern Manga & Comic Server

**Best for:** Readers who consume manga, comics, and graphic novels alongside traditional ebooks. Kavita's page-by-page viewer and series organization make it the strongest choice for visual reading material.

Kavita was built from scratch as a self-hosted manga and comic reader that also handles traditional ebooks. Unlike Calibre-Web, it does not depend on an external database or desktop application. It manages everything internally, making it a fully standalone solution.

### Key Features

- Dedicated manga and comic readers with double-page, single-page, and long-strip modes
- Series and volume organization with automatic parsing from folder names
- Built-in metadata fetching from multiple sources (Komga, MAL, AniList, ComicVine)
- Reading lists for curated collections
- Scheduled library scans for automatic content discovery
- Multiple reading progress tracking per user
- Transcoding for image optimization on slow connections
- REST API for integration with external tools
- Dark theme by default

### Docker Setup

```yaml
services:
  kavita:
    image: jvmilazz0/kavita:latest
    container_name: kavita
    volumes:
      - ./data:/kavita/config
      - ./manga:/manga
      - ./comics:/comics
      - ./books:/books
    ports:
      - "5000:5000"
    restart: unless-stopped
```

```bash
mkdir -p kavita/{data,manga,comics,books}
cd kavita
docker compose up -d
```

Access the web interface at `http://your-server:5000`. The first login creates the admin account.

### Library Organization

Kavita expects a specific folder structure for optimal organization:

```
/manga/
├── Series Name/
│   ├── Volume 1/
│   │   ├── Chapter 001.cbz
│   │   └── Chapter 002.cbz
│   └── Volume 2/
│       └── Chapter 003.cbz
└── Another Series/
    └── Volume 1/
        └── Chapter 001.cbr

/comics/
└── Batman/
    └── Issue 001.cbz

/books/
├── Author Name/
│   └── Book Title.epub
```

Kavita automatically parses folder and file names to build series, volumes, and chapters. For manga, the double-page reader mode provides an authentic tankobon reading experience.

### Metadata Management

Kavita includes a built-in metadata scraper. In **Administration → Libraries → Edit → Metadata**, enable:

- **ComicVine** for comic book metadata and cover art
- **AniList** or **MyAnimeList** for manga metadata
- **Google Books** for traditional ebook metadata

Run a library scan after enabling scrapers. Kavita will fetch covers, summaries, genres, and publication data for your entire collection in the background.

---

## Audiobookshelf: The Audiobook & Podcast Powerhouse

**Best for:** Audiobook listeners and podcast subscribers who want a unified server with official mobile apps, chapter navigation, and seamless progress sync.

Audiobookshelf is purpose-built for audio content. It handles audiobooks with full chapter support, variable playback speed, and sleep timers. It also manages podcast subscriptions with automatic episode downloads. This is the only option of the three with official mobile applications on both Android and iOS.

### Key Features

- Official Android and iOS apps with full sync
- Audiobook playback with chapter navigation, bookmarks, and sleep timer
- Podcast subscription management with auto-download
- Multi-user support with per-user listening progress
- OPDS feed for third-party podcast and audiobook apps
- Audiobook metadata from Audnexus, Google Books, and Open Library
- Chapter extraction and editing for M4B files
- Podcast episode deduplication
- Listening statistics and progress reports
- Chromecast and AirPlay support

### Docker Setup

```yaml
services:
  audiobookshelf:
    image: ghcr.io/advplyr/audiobookshelf:latest
    container_name: audiobookshelf
    volumes:
      - ./config:/config
      - ./metadata:/metadata
      - ./audiobooks:/audiobooks
      - ./podcasts:/podcasts
    ports:
      - "13378:80"
    environment:
      - TZ=America/New_York
    restart: unless-stopped
```

```bash
mkdir -p audiobookshelf/{config,metadata,audiobooks,podcasts}
cd audiobookshelf
docker compose up -d
```

Access the interface at `http://your-server:13378`. Create your admin account on first visit.

### Audiobook Folder Structure

Audiobookshelf recognizes several naming conventions. The most reliable structure:

```
/audiobooks/
├── Author Name/
│   ├── Series Name - Book 1/
│   │   ├── Cover.jpg
│   │   ├── Chapter 01 - The Beginning.mp3
│   │   ├── Chapter 02 - The Journey.mp3
│   │   └── metadata.opf
│   └── Standalone Book/
│       ├── Cover.jpg
│       └── Book Name.m4b
```

For single-file audiobooks (M4B with embedded chapters), simply place the file in the appropriate author or series folder. Audiobookshelf extracts chapters automatically from M4B metadata.

### Podcast Setup

Adding podcasts is straightforward:

1. Go to **Libraries → Add Library → Podcast**
2. Point it to your `/podcasts` directory
3. Search for a podcast in the **Add Podcast** dialog
4. Set download preferences (auto-download new episodes, keep limit)

Audiobookshelf checks for new episodes on a schedule and downloads them automatically. Your podcast queue syncs across all devices through the official apps.

### Mobile App Configuration

Install the **Audiobookshelf** app from the Google Play Store or Apple App Store. On first launch:

1. Enter your server address: `http://your-server:13378` (or your domain if using a reverse proxy)
2. Log in with your credentials
3. Your entire library appears, ready for streaming or downloading

The app supports background playback, download for offline listening, and variable speed from 0.5x to 3x. Listening progress syncs instantly — switch from your phone to your desktop browser mid-chapter without missing a beat.

---

## Choosing the Right Tool for Your Collection

The decision comes down to what you read and listen to most:

**Use Calibre-Web if:**
- You already use Calibre desktop for library management
- Your collection is primarily ebooks (EPUB, PDF, MOBI)
- You own a Kobo e-reader and want native sync
- You prefer a traditional library catalog interface

**Use Kavita if:**
- You read manga, comics, or graphic novels
- You want the best visual reading experience with multiple display modes
- You prefer a standalone solution without external dependencies
- Your collection mixes manga, comics, and traditional ebooks

**Use Audiobookshelf if:**
- Your primary content is audiobooks or podcasts
- You want official mobile apps with full feature parity
- You need chapter navigation, bookmarks, and sleep timers
- You listen across multiple devices and need progress sync

**Combine them for a complete library:**
Many self-hosters run all three. They coexist peacefully on the same server since each uses different default ports. A reverse proxy like Nginx Proxy Manager or Caddy routes traffic based on domain or path:

```yaml
services:
  caddy:
    image: caddy:latest
    container_name: caddy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    restart: unless-stopped

volumes:
  caddy_data:
  caddy_config:
```

```
# Caddyfile
books.example.com {
    reverse_proxy calibre-web:8083
}

manga.example.com {
    reverse_proxy kavita:5000
}

audio.example.com {
    reverse_proxy audiobookshelf:80
}
```

Caddy handles TLS certificate provisioning automatically via Let's Encrypt. Each service gets its own subdomain, and all traffic is encrypted.

## OPDS Integration with Third-Party Apps

All three servers support OPDS (Open Publication Distribution System), which lets them serve as catalogs for dedicated reading and listening apps:

- **Calibre-Web + KOReader**: Point KOReader's OPDS catalog to `http://your-server:8083/opds` for ebook downloads to your e-ink device.
- **Kavita + Panels (iOS)**: Use Kavita's OPDS feed in Panels for a polished comic reading experience on iPad.
- **Audiobookshelf + Podcast Addict**: Audiobookshelf's OPDS feed works with any OPDS-compatible podcast client as an alternative to the official app.

OPDS turns your self-hosted server into a universal content source that any compatible app can browse and download from, similar to how a podcast app discovers feeds.

## Backup and Disaster Recovery

Your book collection is only as safe as your backup strategy. Here's a minimal backup approach using restic:

```bash
#!/bin/bash
# backup-books.sh

export RESTIC_REPOSITORY="/backup/books-repo"
export RESTIC_PASSWORD="your-backup-password"

restic backup \
  /path/to/calibre-web/books \
  /path/to/kavita/data \
  /path/to/audiobookshelf/config \
  /path/to/audiobookshelf/metadata \
  --tag automated \
  --exclude='*.tmp'

# Keep daily backups for 7 days, weekly for 4 weeks, monthly for 6 months
restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune
```

Schedule this with a cron job to run daily. Restic's deduplication means only changed data is stored, making daily backups lightweight even for large libraries.

For the Calibre database specifically, export periodically from the desktop application: **File → Export/import → Export all book metadata**. This creates a portable backup of your entire catalog that can be reimported into any Calibre instance.

## Remote Access Considerations

If you want to access your library from outside your home network, you have several options:

- **Reverse proxy with TLS** (recommended): Use Caddy or Nginx Proxy Manager as shown above. Requires a domain name and port forwarding on your router.
- **Tailscale**: Zero-config VPN that makes your server accessible from any Tailscale-connected device without opening ports. Install Tailscale on both server and client devices.
- **Cloudflare Tunnel**: Free tunnel service that exposes your local server through Cloudflare's network without port forwarding. Works well with the `cloudflared` daemon.

Never expose these services directly to the internet without authentication and TLS encryption. All three tools have built-in user management, but a reverse proxy adds an essential encryption layer for credentials and content in transit.

## Conclusion

Self-hosting your digital library is one of the most practical first steps into the self-hosted world. The services covered here run on minimal hardware — a Raspberry Pi 4 with an external USB drive handles thousands of ebooks and hundreds of audiobooks without breaking a sweat. Start with the tool that matches your primary content type, and expand as your collection grows. Your books, your server, your rules.
