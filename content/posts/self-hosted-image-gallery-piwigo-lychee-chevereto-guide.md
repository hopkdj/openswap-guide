---
title: "Best Self-Hosted Image Gallery & Photo Hosting 2026: Piwigo vs Lychee vs Chevereto"
date: 2026-04-13
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete guide to self-hosted image galleries in 2026. Compare Piwigo, Lychee, and Chevereto for photo hosting, portfolio sites, and community image sharing with Docker setups."
---

Whether you are a professional photographer building a portfolio, a community manager running a shared image board, or a hobbyist who wants full ownership of every photo, running your own image gallery gives you something cloud services never will: complete control. No algorithmic feeds, no compression artifacts, no surprise account suspensions, and no data mining.

In 2026, the open-source image gallery ecosystem is more mature than ever. Three projects stand out as the most practical options for different use cases: **Piwigo**, **Lychee**, and **Chevereto**. Each takes a different approach to photo management, and choosing the right one depends on whether you value extensibility, aesthetics, or commercial-grade features.

## Why Self-Host Your Image Gallery

Before comparing tools, it is worth understanding why self-hosting an image gallery matters:

**Data ownership.** Your photos are your intellectual property. Cloud platforms can change their terms of service, shut down, or lock your account at any time. When you self-host, the files live on your hardware or your VPS, and you control the backup strategy.

**Privacy for client work.** Photographers who share private galleries with clients need encryption, password protection, and audit trails. Self-hosted solutions let you set granular access controls without handing client data to a third party.

**No compression.** Most free cloud services aggressively compress uploads. Self-hosted galleries serve full-resolution originals or let you configure the exact quality level for derived thumbnails.

**Cost at scale.** Storing thousands of high-resolution images on Google Photos or Dropbox gets expensive quickly. A $5/month VPS with a mounted object storage bucket can host hundreds of thousands of images for a fraction of the price.

**Custom branding.** Your gallery, your domain, your CSS. Self-hosted tools let you remove all third-party branding and match the gallery to your existing website design.

## Piwigo — The Extensible Powerhouse

Piwigo has been around since 2002 and is arguably the most feature-complete open-source gallery available. It supports over 200 plugins and 50+ themes, making it suitable for everything from personal archives to professional photography businesses.

### Key Features

- **Hierarchical albums** with unlimited nesting depth
- **User management** with per-album permissions (guests, contacts, webmasters, admins)
- **Plugin ecosystem** covering watermarks, e-commerce, social sharing, and SEO
- **Batch upload** via desktop sync tools, mobile apps, and FTP
- **EXIF/IPTC metadata** parsing and display
- **Multi-size derivatives** (thumbnails, medium, HD) generated automatically
- **REST API** for integration with external applications

### [docker](https://www.docker.com/) Deployment

```yaml
version: "3.8"

services:
  piwigo_db:
    image: mariadb:11
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: piwigo_root
      MYSQL_DATABASE: piwigo
      MYSQL_USER: piwigo
      MYSQL_PASSWORD: piwigo_pass
    volumes:
      - piwigo_db_data:/var/lib/mysql

  piwigo:
    image: linuxserver/piwigo:latest
    restart: always
    depends_on:
      - piwigo_db
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    volumes:
      - ./piwigo/config:/config
      - ./piwigo/data:/data
    ports:
      - "8080:80"

volumes:
  piwigo_db_data:
```

After the containers start, visit `http://localhost:8080` and complete the web installer. Point it at the `piwigo_db` service using hostname `piwigo_db`, database `piwigo`, user `piwigo`, and password `piwigo_pass`.

### Performance Tuning

Piwigo generates image derivatives on first view by default. For galleries with thousands of photos, pre-generate them during off-peak hours:

```bash
# Install the command-line tool
docker exec piwigo apt-get update && \
  docker exec piwigo apt-get install -y php-cli

# Pre-generate all derivatives
docker exec piwigo php /app/www/include/cli.php \
  --category=global \
  --action=generate_derivatives
```

Add an Nginx reverse proxy with caching for the `/i/` and `/upload/` paths to serve derivatives directly from disk without invoking PHP:

```nginx
location ~* \.(jpg|jpeg|png|webp|gif|avif)$ {
    expires 30d;
    add_header Cache-Control "public, immutable";
    try_files $uri $uri/ =404;
}
```

## Lychee — The Minimalist Beauty

Lychee takes the opposite philosophy from Piwigo. Instead of endless configuration options, it delivers a single, polished experience focused on visual quality and simplicity. If you want a gallery that looks stunning out of the box with zero customization, Lychee is the answer.

### Key Features

- **Clean, modern UI** with full-screen photo viewing and keyboard navigation
- **Smart albums** that auto-organize by tags, dates, or camera model
- **Photo sharing** via public links with optional password protection and expiration dates
- **Native WebP and AVIF support** for next-generation image formats
- **Import from URL, server, or Dropbox** without manual uploads
- **Face recognition** plugin for automatic people grouping
- **Multi-user support** with album-level sharing

### Docker Deployment

```yaml
version: "3.8"

services:
  lychee_db:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_DB: lychee
      POSTGRES_USER: lychee
      POSTGRES_PASSWORD: lychee_secret
    volumes:
      - lychee_pg_data:/var/lib/postgresql/data

  lychee:
    image: lycheeorg/lychee:latest
    restart: always
    depends_on:
      - lychee_db
    environment:
      - DB_CONNECTION=pgsql
      - DB_HOST=lychee_db
      - DB_PORT=5432
      - DB_DATABASE=lychee
      - DB_USERNAME=lychee
      - DB_PASSWORD=lychee_secret
      - APP_URL=http://localhost:8081
      - APP_ENV=production
      - APP_DEBUG=false
      - UPLOAD_LIMIT=100M
      - PHP_TIMEZONE=UTC
    volumes:
      - ./lychee/uploads:/uploads
      - ./lychee/sym:/sym
      - ./lychee/conf:/conf
    ports:
      - "8081:80"

volumes:
  lychee_pg_data:
```

Lychee uses PostgreSQL by default, which handles large photo collections more gracefully than SQLite. The first visit to `http://localhost:8081` triggers the database migration automatically.

### Bulk Import from Existing Archives

Lychee includes a CLI tool for importing from directories:

```bash
# Import an entire directory tree
docker exec lychee php artisan lychee:sync \
  /uploads/archive \
  --album-id=0 \
  --skip-duplicates

# Import from a remote URL
docker exec lychee php artisan lychee:upload-url \
  https://example.com/photos/2026-shoot.zip
```

For large archives, increase PHP memory and execution time in the container:

```bash
docker exec lychee sh -c '
  echo "memory_limit = 512M" >> /usr/local/etc/php/conf.d/zz-custom.ini
  echo "max_execution_time = 600" >> /usr/local/etc/php/conf.d/zz-custom.ini
'
docker restart lychee
```

## Chevereto — The Commercial-Grade Platform

Chevereto occupies a different niche entirely. It is designed as an image hosting platform in the tradition of Imgur or Flickr — built for communities where users upload, share, and discover images together. Since version 4, Chevereto offers both a free core and a paid tier with advanced features.

### Key Features

- **Multi-user image hosting** with per-user storage quotas
- **Embed codes** for forums, blogs, and external websites
- **Content moderation** tools including flagging, approval queues, and keyword filters
- **Monetization support** with ad placement and premium membership tiers
- **Custom fields** for metadata, licensing, and source attribution
- **S3-compatible storage** for offloading images to Backb[minio](https://min.io/)B2, Cloudflare R2, or MinIO
- **API-first design** with full CRUD operations over REST

### Docker Deployment

```yaml
version: "3.8"

services:
  chevereto_db:
    image: mariadb:11
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: chevereto_root
      MYSQL_DATABASE: chevereto
      MYSQL_USER: chevereto
      MYSQL_PASSWORD: chevereto_pass
    volumes:
      - chevereto_db_data:/var/lib/mysql

  chevereto:
    image: ghcr.io/chevereto/chevereto:4
    restart: always
    depends_on:
      - chevereto_db
    environment:
      - CHEVERETO_DB_HOST=chevereto_db
      - CHEVERETO_DB_USER=chevereto
      - CHEVERETO_DB_PASS=chevereto_pass
      - CHEVERETO_DB_NAME=chevereto
      - CHEVERETO_HTTP_HOST=localhost
      - CHEVERETO_HTTP_HOST_PORT=8082
      - CHEVERETO_INSTALL_SOURCE=dist
    volumes:
      - ./chevereto/images:/var/www/html/images
      - ./chevereto/content:/var/www/html/content
    ports:
      - "8082:80"

volumes:
  chevereto_db_data:
```

After starting the stack, visit `http://localhost:8082` and run the installer. Chevereto will validate your database connection and create the initial admin account.

### Configuring S3-Compatible Storage

One of Chevereto's strongest features is transparent integration with object storage. This lets you keep the application lightweight while storing millions of images on cheap S3-compatible backends:

```bash
# In the Chevereto dashboard, go to Settings > Storage > External
# Or configure via environment variables:
environment:
  - CHEVERETO_STORAGE_DRIVER=external
  - CHEVERETO_STORAGE_EXTERNAL_SERVICE=s3
  - CHEVERETO_STORAGE_EXTERNAL_BUCKET=chevereto-images
  - CHEVERETO_STORAGE_EXTERNAL_REGION=us-east-1
  - CHEVERETO_STORAGE_EXTERNAL_KEY=YOUR_ACCESS_KEY
  - CHEVERETO_STORAGE_EXTERNAL_SECRET=YOUR_SECRET_KEY
  - CHEVERETO_STORAGE_EXTERNAL_ENDPOINT=https://s3.us-east-1.backblazeb2.com
```

With external storage configured, new uploads go directly to the S3 bucket while the local filesystem only caches recently accessed images. This architecture scales to millions of images without filling your server disk.

## Detailed Comparison

| Feature | Piwigo | Lychee | Chevereto |
|---------|--------|--------|-----------|
| **Best For** | Personal archives, photography businesses | Minimalist portfolios, visual-first galleries | Community image hosting, social sharing |
| **License** | GPL v2 | MIT | Mixed (core free, premium paid) |
| **Database** | MySQL/MariaDB | PostgreSQL, MySQL, SQLite | MySQL/MariaDB |
| **Max Photos** | Unlimited (tested with 500K+) | ~100K recommended | Unlimited with S3 offload |
| **Plugins/Themes** | 200+ plugins, 50+ themes | ~15 extensions | Marketplace with paid extensions |
| **User Management** | Role-based per-album | Multi-user with album sharing | Full multi-user with quotas |
| **Mobile Apps** | Official iOS and Android | Third-party only | Web-only (responsive) |
| **Video Support** | Via plugin | Native (MP4, WebM) | Native |
| **API** | REST | GraphQL | REST |
| **S3 Integration** | Via plugin | No | Native |
| **Docker Image** | linuxserver/piwigo | lycheeorg/lychee | ghcr.io/chevereto/chevereto |
| **Resource Usage** | Moderate (PHP-heavy) | Light | Moderate |
| **Setup Com[plex](https://www.plex.tv/)ity** | Medium (many options) | Low (works immediately) | Medium (richer config) |

## Choosing the Right Gallery

### Pick Piwigo if:
- You have an existing photo archive spanning years of albums
- You need granular per-album permissions for family, clients, and public viewers
- You want to extend functionality with plugins (watermarking, e-commerce, SEO)
- You plan to use desktop sync tools like digiKam or Lightroom plugins
- You value a mature, stable project with two decades of development

### Pick Lychee if:
- Visual presentation is your top priority
- You want a gallery that looks professional immediately after installation
- You prefer PostgreSQL and clean database architecture
- You need smart albums and auto-organization features
- You share images via expiring, password-protected links
- You want the lightest possible resource footprint

### Pick Chevereto if:
- You are building a community where multiple users upload images
- You need content moderation tools (flagging, approval queues)
- You want to monetize through ads or premium memberships
- You need S3-compatible storage for cost-effective scaling
- You require embed codes for external forums and websites
- You need an API for building custom integrations

## Security Hardening for Any Gallery

Regardless of which platform you choose, follow these baseline security practices:

### TLS Termination

Never serve an image gallery over plain HTTP. Images are visible metadata, and upload credentials must be encrypted:

```nginx
server {
    listen 443 ssl http2;
    server_name gallery.example.com;

    ssl_certificate     /etc/letsencrypt/live/gallery.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/gallery.example.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Limit upload size
        client_max_body_size 100M;
    }
}
```

### Fail2Ban Integration

Image galleries with user registration attract brute-force login attempts. Protect them with Fail2Ban:

```ini
# /etc/fail2ban/filter.d/gallery.conf
[Definition]
failregex = ^<HOST> .* "POST .*/login.*" 401
            ^<HOST> .* "POST .*/auth.*" 403

[gallery]
enabled  = true
port     = http,https
filter   = gallery
logpath  = /var/log/nginx/gallery_access.log
maxretry = 5
bantime  = 3600
```

### Regular Backups

Automate database and image backups with a simple cron script:

```bash
#!/bin/bash
# /etc/cron.daily/gallery-backup.sh

BACKUP_DIR="/backup/gallery/$(date +%Y-%m-%d)"
mkdir -p "$BACKUP_DIR"

# Database dump
docker exec piwigo_db mysqldump -u piwigo -ppiwigo_pass piwigo \
  > "$BACKUP_DIR/database.sql"

# Image data
rsync -a ./piwigo/data/ "$BACKUP_DIR/images/"

# Compress and ship to remote
tar czf "$BACKUP_DIR.tar.gz" -C "$BACKUP_DIR" .
rclone copy "$BACKUP_DIR.tar.gz" remote:backups/gallery/

# Clean up local files older than 7 days
find /backup/gallery -maxdepth 1 -mtime +7 -delete
```

Add to crontab with `echo "0 2 * * * /etc/cron.daily/gallery-backup.sh" | crontab -`.

## Storage Planning

Image galleries grow fast. Plan your storage architecture before uploading your first photo:

| Collection Size | Recommended Setup | Monthly Cost |
|----------------|-------------------|-------------|
| Under 10,000 photos (50 GB) | Single VPS with local SSD | $5–10 |
| 10,000–100,000 photos (500 GB) | VPS + mounted block storage | $15–30 |
| 100,000–1,000,000 photos (5 TB) | VPS + S3-compatible storage (Backblaze B2, Cloudflare R2) | $10–25 |
| Unlimited | CDN + S3 + edge caching | $25+ |

For large collections, offload derivative images (thumbnails, medium) to object storage while keeping originals on a local RAID array. This gives you fast local access for editing and cheap remote storage for web delivery.

## Migration From Cloud Services

Moving from Google Photos, Flickr, or SmugMug to a self-hosted gallery requires careful extraction. Most services let you download your data, but the format varies:

**Google Takeout** exports albums as flat directories with JSON metadata files. Use a script to parse the JSON and extract dates, locations, and album names:

```python
#!/usr/bin/env python3
"""Reorganize Google Takeout exports for Piwigo import."""
import json
import os
import shutil
from pathlib import Path

takeout_dir = Path("/data/google-takeout/Photos")
output_dir = Path("/data/organized-photos")

for item in takeout_dir.iterdir():
    if item.suffix in (".jpg", ".jpeg", ".png", ".webp"):
        json_path = item.with_suffix(".json")
        if json_path.exists():
            meta = json.loads(json_path.read_text())
            # Extract creation date from metadata
            date_str = meta.get("photoTakenTime", {}).get("formatted", "unknown")
            year = date_str.split(", ")[-1] if date_str != "unknown" else "undated"
            dest = output_dir / year
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest / item.name)

print(f"Organized photos into {output_dir}")
```

Run this script, then use Piwigo's batch manager or Lychee's CLI sync to import the organized directories into albums.

## Conclusion

The choice between Piwigo, Lychee, and Chevereto comes down to your primary use case. Piwigo is the most flexible and extensible, making it ideal for photographers who need fine-grained control. Lychee delivers the best visual experience with the simplest setup, perfect for portfolios and personal galleries. Chevereto provides the infrastructure for multi-user image communities with monetization and moderation built in.

All three support Docker deployment, can sit behind a reverse proxy with TLS, and give you complete ownership of your images. The real question is not whether to self-host — it is which tool best matches your workflow.

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
