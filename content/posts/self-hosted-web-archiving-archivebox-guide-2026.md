---
title: "Self-Hosted Web Archiving with ArchiveBox: Complete Guide 2026"
date: 2026-04-14
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "A complete guide to self-hosted web archiving with ArchiveBox in 2026. Learn how to build your own personal Wayback Machine, archive web pages automatically, and preserve digital content on your own infrastructure."
---

The internet loses millions of pages every year. Link rot is real — studies show that over 50% of URLs referenced in academic papers from the early 2000s are now dead. Social media posts vanish, news articles get paywalled, documentation sites restructure, and entire platforms shut down without warning. If you rely on the web for research, compliance, or personal knowledge management, you need a strategy to preserve content before it disappears.

While the Internet Archive's Wayback Machine is the most well-known web archiving service, it has limitations: you cannot control what gets archived, you cannot search your private archives efficiently, and you are at the mercy of a third party's infrastructure and policies. Self-hosting your own web archiving solution gives you full ownership, instant access, searchable storage, and complete control over what you preserve.

## Why Self-Host Your Web Archive

There are compelling reasons to run your own web archiving infrastructure instead of relying on external services.

**Complete ownership of your data.** When you archive pages to your own server, the content never leaves your control. You decide retention policies, access controls, and backup strategies. This is especially critical for legal compliance, research data, and sensitive business intelligence.

**Full-text search across your entire archive.** Most third-party archiving services do not provide robust search capabilities across your saved pages. With a self-hosted solution, you can build a personal knowledge base where every archived page is searchable by content, tag, date, or source.

**Archive anything, including private pages.** The Wayback Machine cannot archive pages behind authentication, paywalls, or corporate intranets. Your own archiving server can be configured with credentials to capture content from any source you have access to.

**No rate limits or quotas.** External archiving services impose limits on how many pages you can save and how frequently. A self-hosted instance lets you archive as much as your storage and bandwidth allow.

**Preserve interactive and dynamic content.** Modern web pages rely heavily on JavaScript, WebAssembly, and dynamic loading. Self-hosted archiving tools can be configured to wait for JavaScript execution, capture screenshots, and save multiple output formats to ensure you preserve the page as it appeared.

## What Is ArchiveBox?

[ArchiveBox](https://github.com/ArchiveBox/ArchiveBox) is the most comprehensive open-source self-hosted web archiving solution available. It takes a URL and captures a full snapshot of the page in multiple formats:

- **HTML** — raw page source and cleaned DOM output
- **Wget mirror** — complete recursive download with all assets
- **SingleFile** — entire page saved as a single self-contained HTML file
- **PDF** — rendered page output via headless browser
- **Screenshot** — PNG capture of the page viewport
- **WARC** — raw HTTP response archive (the web archiving standard)
- **Media** — embedded video and audio extraction via yt-dlp
- **Git** — repository clones for GitHub, GitLab, and similar hosts
- **DOM** — post-JavaScript-rendered HTML snapshot

ArchiveBox is not just a downloader — it is a full-featured archiving platform with a web interface, REST API, scheduling capabilities, and support for importing bookmarks from browser export files, Pocket, Pinboard, Raindrop, Shaarli, Delicious, and many other sources.

### ArchiveBox vs Alternative Archiving Tools

| Feature | ArchiveBox | Wayback Machine | SingleFile CLI | warcprox | Browsh |
|---------|-----------|-----------------|----------------|----------|--------|
| Self-hosted | ✅ Yes | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| Multi-format capture | ✅ 9 formats | ✅ Limited | ✅ Single HTML | ✅ WARC only | ❌ Browser only |
| Web UI | ✅ Built-in | ✅ Web only | ❌ CLI only | ❌ CLI only | ✅ Built-in |
| Scheduling/cron | ✅ Built-in | ❌ No | ❌ Manual | ❌ No | ❌ No |
| Full-text search | ✅ Yes | ✅ Yes | ❌ No | ❌ No | ❌ No |
| API access | ✅ REST API | ✅ API | ❌ No | ❌ No | ❌ No |
| Bookmark import | ✅ 15+ sources | ❌ No | ❌ No | ❌ No | ❌ No |
| JavaScript rendering | ✅ Headless Chrome | ✅ Yes | ✅ Via extension | ❌ No | ✅ Yes |
| Media extraction | ✅ yt-dlp | ❌ No | ❌ No | ❌ No | ❌ No |
| Docker support | ✅ Official image | ❌ N/A | ✅ Community | ✅ Yes | ✅ Yes |
| Active development | ✅ Very active | ✅ Active | ✅ Active | ⚠️ Low activity | ⚠️ Low activity |

For most users who want a complete self-hosted web archiving solution, ArchiveBox is the clear choice. It combines the capture capabilities of multiple tools into a single platform with a polished interface and active community.

## Prerequisites

Before deploying ArchiveBox, ensure your server meets these requirements:

- **CPU:** 2+ cores recommended (headless browser rendering is CPU-intensive)
- **RAM:** 4 GB minimum, 8 GB recommended for concurrent archiving
- **Storage:** Depends on archive size. A typical page takes 2-10 MB across all formats. Plan for at least 100 GB for serious archiving.
- **OS:** Linux (Ubuntu 22.04+, Debian 12+, or any distro with Docker)
- **Docker and Docker Compose** installed

The following commands assume an Ubuntu/Debian server. Adjust package names for your distribution.

## Installation: Docker Compose (Recommended)

The Docker Compose deployment is the fastest and most reliable way to run ArchiveBox. It bundles all dependencies — Python, Chromium, Node.js, yt-dlp, and SingleFile — into a single container.

### Step 1: Create the Project Directory

```bash
mkdir -p ~/archivebox && cd ~/archivebox
```

### Step 2: Write the Docker Compose File

Create a `docker-compose.yml` file:

```yaml
version: "3.8"

services:
  archivebox:
    image: ghcr.io/archivebox/archivebox:latest
    container_name: archivebox
    restart: unless-stopped
    ports:
      - "8080:8000"
    volumes:
      - ./data:/data
    environment:
      - TZ=UTC
      - ALLOWED_HOSTS=*
      - CSRF_TRUSTED_ORIGINS=http://localhost:8080
      # Optional: increase concurrency for faster archiving
      - SEARCH_BACKEND=sonic
    cap_add:
      - SYS_CHROOT
    security_opt:
      - no-new-privileges:true
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: "2.0"
```

The `SYS_CHROOT` capability is required for Chromium to run in sandboxed mode inside the container. The volume mount persists all archived data on your host filesystem.

### Step 3: Initialize the Archive

```bash
# Create the data directory and initialize the database
docker compose run archivebox init --setup
```

This command creates the SQLite database, sets up the admin user, and generates the initial configuration. You will be prompted to create an admin username, email, and password.

### Step 4: Start the Service

```bash
docker compose up -d
```

ArchiveBox is now running at `http://your-server-ip:8080`. Log in with the admin credentials you created during initialization.

### Step 5: Verify the Installation

```bash
docker compose exec archivebox archivebox status
```

This should display your archive statistics, including the number of snapshots, total disk usage, and configured extractors.

## Configuration and Optimization

Out of the box, ArchiveBox works well for casual use. For production deployments with heavy archiving loads, you should tune several settings.

### Core Configuration Options

Configuration is managed through the web UI or via environment variables in your `docker-compose.yml`. Key settings include:

```yaml
environment:
  - TZ=UTC
  - ALLOWED_HOSTS=archive.example.com
  - CSRF_TRUSTED_ORIGINS=https://archive.example.com
  # Archiving behavior
  - CHROME_TIME_LIMIT=120
  - WGET_TIMEOUT=120
  - YOUTUBEDL_TIMEOUT=120
  # Content filtering
  - IGNORE_ARCHIVE_ERRORS=True
  - SAVE_FAVICON=True
  - SAVE_ARCHIVE_DOT_ORG=False
  # Performance
  - CHROME_HEADLESS=True
  - RESOLUTION=1440,2000
```

| Setting | Default | Recommended | Description |
|---------|---------|-------------|-------------|
| `CHROME_TIME_LIMIT` | 60s | 120s | Max time for headless browser rendering per page |
| `WGET_TIMEOUT` | 60s | 120s | Max time for wget download per page |
| `YOUTUBEDL_TIMEOUT` | 60s | 120s | Max time for media extraction |
| `RESOLUTION` | 1440,2000 | 1440,2000 | Browser viewport for screenshots and PDFs |
| `SAVE_ARCHIVE_DOT_ORG` | True | False | Disable submitting to Internet Archive (self-hosted only) |
| `CHROME_HEADLESS` | True | True | Run Chrome in headless mode |
| `SAVE_FAVICON` | True | True | Download site favicons for visual identification |
| `RESOLUTION` | 1440,2000 | 1920,1080 | Screenshot and PDF viewport size |

### Adding Full-Text Search with Sonic

For archives with thousands of pages, the default SQLite search can become slow. ArchiveBox supports Sonic, a lightweight full-text search backend:

```yaml
services:
  archivebox:
    image: ghcr.io/archivebox/archivebox:latest
    environment:
      - SEARCH_BACKEND=sonic
      - SONIC_HOSTNAME=sonic
      - SONIC_PORT=1491
      - SONIC_PASSWORD=SecretPassword123
    depends_on:
      - sonic

  sonic:
    image: valeriansaliou/sonic:latest
    container_name: sonic
    restart: unless-stopped
    volumes:
      - ./sonic_data:/var/lib/sonic/store
    environment:
      - SONIC_PASSWORD=SecretPassword123
```

After adding Sonic, rebuild the search index:

```bash
docker compose exec archivebox archivebox manage createsuperuser
docker compose exec archivebox archivebox search --reindex
```

## Using ArchiveBox

### Adding URLs via the Web UI

The web interface is the simplest way to archive pages. Log in and use the "Add URL" button in the top right corner. You can:

- Add a single URL
- Paste multiple URLs (one per line)
- Import a bookmark export file (HTML, JSON, or Netscape format)

ArchiveBox immediately begins processing and shows real-time progress.

### Archiving via the CLI

For automation and scripting, the CLI is more powerful:

```bash
# Archive a single URL
docker compose exec archivebox archivebox add 'https://example.com/article'

# Archive multiple URLs from a file
docker compose exec archivebox archivebox add < urls.txt

# Archive with custom tag
docker compose exec archivebox archivebox add 'https://example.com' --tag 'research,important'

# Re-archive an existing URL (update snapshot)
docker compose exec archivebox archivebox update 'https://example.com'

# Remove a snapshot
docker compose exec archivebox archivebox remove 'https://example.com' --delete
```

### Importing Bookmarks

ArchiveBox can import bookmarks from virtually any source:

```bash
# From browser HTML export (Chrome, Firefox, Edge)
docker compose exec archivebox archivebox add < bookmarks.html

# From Pocket CSV export
docker compose exec archivebox archivebox add < pocket_export.csv

# From Pinboard JSON export
docker compose exec archivebox archivebox add < pinboard_backup.json

# From Raindrop.io (via their export feature)
docker compose exec archivebox archivebox add < raindrop_export.json

# From a public RSS/Atom feed
docker compose exec archivebox archivebox add 'https://example.com/feed.xml'

# From a Reddit subreddit
docker compose exec archivebox archivebox add 'https://www.reddit.com/r/selfhosted/top/?t=year'
```

### Scheduling Regular Archives

Set up automatic archiving with cron jobs on your host machine:

```bash
# Edit the host crontab
crontab -e

# Archive a news site every 6 hours
0 */6 * * * cd ~/archivebox && docker compose exec -T archivebox archivebox add 'https://news.ycombinator.com' --tag 'hn-daily'

# Archive a RSS feed daily at 2 AM
0 2 * * * cd ~/archivebox && docker compose exec -T archivebox archivebox add 'https://feeds.example.com/blog' --tag 'blog-feed'

# Re-archive all pages tagged 'critical' weekly
0 3 * * 0 cd ~/archivebox && docker compose exec -T archivebox archivebox update --tag 'critical'

# Clean up snapshots older than 1 year (monthly)
0 4 1 * * cd ~/archivebox && docker compose exec -T archivebox archivebox remove --before=$(date -d '1 year ago' +%s)
```

## Advanced Use Cases

### Archiving Pages Behind Authentication

To archive content behind login walls, configure ArchiveBox with browser cookies:

```bash
# Export cookies from your browser using a cookie editor extension
# Save as Netscape format: cookies.txt

# Copy cookies into the ArchiveBox data directory
cp cookies.txt ~/archivebox/data/

# Archive with cookies
docker compose exec archivebox archivebox add 'https://example.com/private-article' \
  --chrome-proxy-cookies=/data/cookies.txt
```

For more complex authentication flows, you can configure a browser user data directory with saved sessions:

```yaml
volumes:
  - ./data:/data
  - ./chrome_profile:/home/archivebox/.config/chromium
```

### Archiving Entire Sites

For comprehensive site archiving, use wget's recursive mode through ArchiveBox:

```bash
# Enable recursive wget in config
docker compose exec archivebox archivebox config --set SAVE_WGET=True
docker compose exec archivebox archivebox config --set SAVE_WGET_WARC=True

# Archive a site with depth limit
docker compose exec archivebox archivebox add 'https://docs.example.com' --tag 'documentation'
```

For large sites, consider using `wget` directly with ArchiveBox as the post-processor:

```bash
wget --mirror --convert-links --adjust-extension \
  --page-requisites --no-parent \
  --wait=1 --random-wait \
  -P ~/archivebox/data/archive/mirrors/ \
  https://docs.example.com/
```

### Integrating with Your Existing Stack

ArchiveBox provides a REST API for integration with other tools:

```bash
# Add a URL via the API
curl -X POST http://localhost:8080/add/ \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -d "url=https://example.com/article" \
  -d "tag=research" \
  -d "depth=0"

# List all archived URLs
curl -X GET http://localhost:8080/api/core/snapshots/ \
  -H "Authorization: Bearer YOUR_API_TOKEN"

# Search archived content
curl -X GET "http://localhost:8080/api/core/snapshots/?search=keyword" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

### Browser Extension for One-Click Archiving

Install the [ArchiveBox browser extension](https://github.com/ArchiveBox/ArchiveBox/wiki/Browser-Extension) for Chrome or Firefox to archive any page with a single click. The extension sends the current tab's URL directly to your ArchiveBox instance.

Configure it by setting the ArchiveBox URL and API token in the extension settings. After that, clicking the extension icon immediately queues the current page for archiving.

### Monitoring and Maintenance

Keep your archive healthy with these maintenance tasks:

```bash
# Check archive statistics
docker compose exec archivebox archivebox status

# List all snapshots with their status
docker compose exec archivebox archivebox list

# Find and fix broken snapshots
docker compose exec archivebox archivebox update --index-only

# Re-run all extractors on existing snapshots
docker compose exec archivebox archivebox update --resume --overwrite

# Export your archive index as JSON
docker compose exec archivebox archivebox list --json --html > archive_export.json

# Run the built-in health check
docker compose exec archivebox archivebox manage check
```

Set up monitoring with Uptime Kuma or similar tools to track ArchiveBox availability:

```yaml
# Add a healthcheck to your docker-compose.yml
services:
  archivebox:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 60s
      timeout: 10s
      retries: 3
      start_period: 30s
```

## Reverse Proxy Setup with HTTPS

For production use, you should put ArchiveBox behind a reverse proxy with TLS. Here is an NGINX configuration:

```nginx
server {
    listen 443 ssl http2;
    server_name archive.example.com;

    ssl_certificate /etc/letsencrypt/live/archive.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/archive.example.com/privkey.pem;

    client_max_body_size 100M;
    proxy_read_timeout 300s;
    proxy_connect_timeout 300s;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
    }

    location /static/ {
        alias /home/archivebox/data/static/;
        expires 30d;
    }
}
```

With this configuration and Let's Encrypt certificates, your archive is accessible at `https://archive.example.com` with full encryption.

## Backup Strategy

Your archive is only as valuable as your backup strategy. ArchiveBox stores everything in the `data/` directory, making backups straightforward:

```bash
#!/bin/bash
# backup-archivebox.sh
BACKUP_DIR="/backup/archivebox/$(date +%Y-%m-%d)"
mkdir -p "$BACKUP_DIR"

# Stop the service for a consistent backup
cd ~/archivebox
docker compose down

# Archive the data directory
tar czf "$BACKUP_DIR/archivebox-data.tar.gz" ./data

# Also export the database as JSON
docker compose run archivebox archivebox list --json > "$BACKUP_DIR/archive-index.json"

# Restart
docker compose up -d

# Sync to remote storage (optional)
rclone sync "$BACKUP_DIR" remote:backups/archivebox/

# Keep only the last 30 days of backups
find /backup/archivebox -type d -mtime +30 -exec rm -rf {} \;
```

Run this script daily via cron. For larger archives, consider using `restic` or `borg` for deduplicated backups.

## Storage Management

Web archives grow quickly. Here are strategies to manage storage:

```bash
# Check disk usage per snapshot
docker compose exec archivebox archivebox status

# Remove low-value formats to save space
docker compose exec archivebox archivebox config --set SAVE_MEDIA=False
docker compose exec archivebox archivebox config --set SAVE_WARC=False

# Compress old archives
find ~/archivebox/data/archive -name "*.warc" -mtime +90 -exec gzip {} \;

# Remove duplicate snapshots
docker compose exec archivebox archivebox list | sort | uniq -d
```

A practical approach is to archive everything in full for the first 30 days, then keep only the PDF and SingleFile formats for long-term storage, discarding heavier WARC and full wget mirrors.

## Conclusion

Self-hosted web archiving with ArchiveBox gives you a personal Wayback Machine that you fully control. Whether you are a researcher preserving source material, a compliance officer maintaining records, or simply someone who values digital preservation, ArchiveBox provides a robust, open-source foundation for building your own archive.

The combination of multi-format capture, full-text search, bookmark importing, REST API, and scheduling makes it the most complete self-hosted web archiving solution available. With Docker deployment, you can have a working instance running in under five minutes.

Start arching today — the page you bookmark now might be gone tomorrow.
