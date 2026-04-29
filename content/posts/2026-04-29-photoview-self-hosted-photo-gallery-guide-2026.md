---
title: "Photoview Self-Hosted Photo Gallery Guide 2026"
date: 2026-04-29
tags: ["comparison", "guide", "self-hosted", "photoview", "photo-gallery"]
draft: false
description: "Complete guide to setting up Photoview, a fast and lightweight self-hosted photo gallery. Docker deployment, configuration, and comparison with Immich, PhotoPrism, and Piwigo for 2026."
---

## Why Self-Host Your Photo Gallery?

Commercial cloud photo storage services — Google Photos, iCloud, Amazon Photos — charge $2–$10 per month for storage tiers and retain full access to your image metadata. Self-hosting a photo gallery gives you:

- **Complete data ownership** — your photos never leave your server or NAS
- **Zero subscription fees** — run unlimited galleries with only hardware costs
- **Full-resolution originals** — no compression or quality loss from cloud providers
- **Privacy control** — no automated photo scanning, no facial recognition on third-party servers, no targeted ads
- **Hardware acceleration** — use your server's GPU for fast video transcoding and thumbnail generation

While full-featured platforms like Immich and PhotoPrism offer comprehensive photo management with automated tagging and machine learning features, they require significant resources. For users who want a focused, lightweight gallery that indexes existing photo libraries and serves them quickly, [Photoview](https://photoview.github.io/) is an excellent choice. With 6,400+ GitHub stars and active development as of April 2026, it is one of the most popular self-hosted photo gallery options available.

## What Is Photoview?

[Photoview](https://github.com/photoview/photoview) is an open-source, self-hosted photo gallery built for personal servers and homelabs. Unlike cloud-sync platforms that manage your entire photo lifecycle, Photoview indexes photos from directories you specify on your server and generates a browsable web gallery with thumbnails, EXIF data, and video playback.

### Key Features

- **Fast thumbnail generation** — uses libvips for rapid image processing, significantly faster than ImageMagick-based alternatives
- **Video transcoding** — converts videos to browser-friendly formats with hardware acceleration support (Intel QSV, Nvidia NVENC, AMD VA-API)
- **EXIF metadata** — extracts and displays camera model, aperture, ISO, focal length, GPS coordinates, and shooting date
- **Map integration** — displays photos on an interactive map using EXIF GPS data (requires free Mapbox token)
- **User accounts** — multi-user support with per-user media libraries and sharing capabilities
- **Multiple database backends** — SQLite for simple setups, MySQL/MariaDB or PostgreSQL for production
- **Read-only media access** — the original photo files are never modified, only indexed and cached

### Photoview vs Other Photo Galleries

| Feature | Photoview | Piwigo | Lychee | Immich |
|---------|-----------|--------|--------|--------|
| **Focus** | Gallery/indexer | Traditional gallery | Minimal gallery | Full photo management |
| **Storage model** | Read-only index | Upload/import | Upload/import | Cloud-sync with mobile app |
| **Thumbnail engine** | libvips (fast) | ImageMagick | Imagick | Custom + ML |
| **Video support** | Yes (transcoding) | Limited | No | Yes |
| **Multi-user** | Yes | Yes | No (single) | Yes |
| **Mobile app** | No (PWA) | Yes (3rd party) | No | Yes (official) |
| **Smart features** | None | Plugins | None | Facial recognition, search |
| **Resource usage** | Low (~200MB RAM) | Low (~150MB RAM) | Low (~100MB RAM) | High (~2GB+ RAM) |
| **Map view** | Yes (Mapbox) | Plugin | No | Yes |
| **Database** | SQLite/MySQL/PostgreSQL | MySQL | PostgreSQL/SQLite | PostgreSQL |
| **GitHub Stars** | 6,400+ | 3,200+ | 10,000+ | 50,000+ |

Photoview occupies a unique niche: it is lighter than Immich and PhotoPrism (no machine learning dependencies, no mobile sync) but more modern and faster than Piwigo's traditional gallery approach. If you have a large collection of photos already stored on a NAS or file server and want a web gallery to browse them, Photoview is purpose-built for that workflow.

For a broader comparison of self-hosted photo management platforms, see our [Immich vs LibrePhotos vs PhotoPrism guide](../2026-04-28-librephotos-vs-immich-vs-photoprism-self-hosted-photo-management-guide-2026/). If you are looking for a simpler gallery focused on curated albums rather than full library indexing, our [Piwigo vs Lychee vs Chevereto comparison](../self-hosted-image-gallery-piwigo-lychee-chevereto-guide/) covers those options in detail.

## Installation and Deployment

### Prerequisites

- Docker and Docker Compose installed on your server
- At least 512 MB RAM (more for large libraries)
- Storage space for media cache (thumbnails and video transcodes)
- Your photo collection on a local drive or mounted network share

### Docker Compose Setup

Photoview provides an official production-ready Docker Compose configuration. The following setup uses MariaDB as the database backend and includes automatic updates via Watchtower:

```yaml
services:
  photoview-prepare:
    image: photoview/photoview:2
    network_mode: "none"
    user: root
    entrypoint: []
    command: /bin/bash -c "sleep 1 && chown -R photoview:photoview /home/photoview/media-cache"
    cap_add:
      - CHOWN
    volumes:
      - "/etc/localtime:/etc/localtime:ro"
      - "/etc/timezone:/etc/timezone:ro"
      - "${HOST_PHOTOVIEW_LOCATION}/storage:/home/photoview/media-cache"

  photoview:
    image: photoview/photoview:2
    restart: unless-stopped
    networks:
      - ui_net
      - api_db_net
    ports:
      - "8000:80"
    depends_on:
      photoview-prepare:
        condition: service_completed_successfully
      mariadb:
        condition: service_healthy
    security_opt:
      - seccomp:unconfined
      - apparmor:unconfined
    environment:
      PHOTOVIEW_DATABASE_DRIVER: ${PHOTOVIEW_DATABASE_DRIVER}
      PHOTOVIEW_MYSQL_URL: "${MARIADB_USER}:${MARIADB_PASSWORD}@tcp(photoview-mariadb)/${MARIADB_DATABASE}"
      PHOTOVIEW_LISTEN_IP: "0.0.0.0"
      MAPBOX_TOKEN: ${MAPBOX_TOKEN}
      PHOTOVIEW_VIDEO_HARDWARE_ACCELERATION: ${PHOTOVIEW_VIDEO_HARDWARE_ACCELERATION}
    volumes:
      - "/etc/localtime:/etc/localtime:ro"
      - "/etc/timezone:/etc/timezone:ro"
      - "${HOST_PHOTOVIEW_LOCATION}/storage:/home/photoview/media-cache"
      - "${HOST_PHOTOVIEW_MEDIA_ROOT}:/photos:ro"

  mariadb:
    image: mariadb:lts
    restart: unless-stopped
    networks:
      - api_db_net
    environment:
      MARIADB_AUTO_UPGRADE: "1"
      MARIADB_DATABASE: ${MARIADB_DATABASE}
      MARIADB_USER: ${MARIADB_USER}
      MARIADB_PASSWORD: ${MARIADB_PASSWORD}
      MARIADB_ROOT_PASSWORD: ${MARIADB_ROOT_PASSWORD}
    volumes:
      - "/etc/localtime:/etc/localtime:ro"
      - "/etc/timezone:/etc/timezone:ro"
      - "${HOST_PHOTOVIEW_LOCATION}/database/mariadb:/var/lib/mysql"
    healthcheck:
      test: healthcheck.sh --connect --innodb_initialized
      interval: 1m
      timeout: 5s
      retries: 5
      start_period: 3m

networks:
  ui_net:
    driver: bridge
  api_db_net:
    internal: true
```

Create a `.env` file alongside the compose file with your configuration:

```bash
# Photoview location on host
HOST_PHOTOVIEW_LOCATION=/opt/photoview
HOST_PHOTOVIEW_MEDIA_ROOT=/mnt/photos

# Database driver: mysql, sqlite, or postgres
PHOTOVIEW_DATABASE_DRIVER=mysql

# MariaDB credentials
MARIADB_DATABASE=photoview
MARIADB_USER=photoview
MARIADB_PASSWORD=your-secure-password
MARIADB_ROOT_PASSWORD=your-root-password

# Mapbox token for map features (free at mapbox.com)
MAPBOX_TOKEN=

# Hardware acceleration: qsv, vaapi, nvenc (optional)
PHOTOVIEW_VIDEO_HARDWARE_ACCELERATION=

# Watchtower settings
WATCHTOWER_POLL_INTERVAL=86400
WATCHTOWER_TIMEOUT=30s
WATCHTOWER_CLEANUP=true
```

Deploy with:

```bash
docker compose up -d
```

After the first run, access Photoview at `http://your-server:8000` and complete the initial setup wizard. You will need to specify the media path inside the container — by default this is `/photos`, which maps to your `HOST_PHOTOVIEW_MEDIA_ROOT` directory.

### SQLite Simplified Setup

For smaller collections or testing, you can use SQLite instead of MariaDB. This removes the database service entirely:

```yaml
services:
  photoview:
    image: photoview/photoview:2
    restart: unless-stopped
    ports:
      - "8000:80"
    environment:
      PHOTOVIEW_DATABASE_DRIVER: sqlite
      PHOTOVIEW_SQLITE_PATH: /home/photoview/database/photoview.db
    volumes:
      - "${HOST_PHOTOVIEW_LOCATION}/storage:/home/photoview/media-cache"
      - "${HOST_PHOTOVIEW_LOCATION}/database:/home/photoview/database"
      - "${HOST_PHOTOVIEW_MEDIA_ROOT}:/photos:ro"
```

This single-service setup uses about 150 MB of RAM and is ideal for libraries under 50,000 photos.

### Reverse Proxy Configuration

For production use behind a reverse proxy, configure your web server to forward traffic to Photoview. Here is an Nginx example:

```nginx
server {
    listen 443 ssl http2;
    server_name photos.example.com;

    ssl_certificate /etc/letsencrypt/live/photos.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/photos.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

If you need a full-featured reverse proxy with a web-based management UI, consider [Nginx Proxy Manager or SWAG](../2026-04-24-nginx-proxy-manager-vs-swag-vs-caddy-docker-proxy-self-hosted-reverse-proxy-gui-guide-2026/) for easier SSL certificate management.

## Hardware Acceleration for Video Transcoding

Photoview can leverage GPU hardware acceleration to speed up video transcoding. This is especially useful for servers with large video libraries. Three acceleration methods are supported:

### Intel QuickSync (QSV)

```yaml
services:
  photoview:
    # ... other config ...
    environment:
      PHOTOVIEW_VIDEO_HARDWARE_ACCELERATION: qsv
    devices:
      - "/dev/dri:/dev/dri"
```

### Nvidia NVENC

```yaml
services:
  photoview:
    # ... other config ...
    environment:
      PHOTOVIEW_VIDEO_HARDWARE_ACCELERATION: nvenc
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              capabilities: [gpu]
```

### AMD VA-API

```yaml
services:
  photoview:
    # ... other config ...
    environment:
      PHOTOVIEW_VIDEO_HARDWARE_ACCELERATION: vaapi
    devices:
      - "/dev/dri:/dev/dri"
```

## Performance Tuning

### Thumbnail Cache Location

Photoview stores generated thumbnails in the `media-cache` directory. For large libraries (100,000+ photos), place this on an SSD for fast access:

```bash
# In .env file
HOST_PHOTOVIEW_LOCATION=/mnt/ssd/photoview
```

### Database Optimization

For MySQL/MariaDB, the default `innodb-buffer-pool-size` in Photoview's compose file is set to 512 MB. Increase this to 1-2 GB for libraries over 200,000 photos:

```yaml
services:
  mariadb:
    command: mariadbd --innodb-buffer-pool-size=2G --transaction-isolation=READ-COMMITTED
```

### Initial Scan Time

The first scan of a large photo library can take hours. Photoview processes photos sequentially for thumbnail generation and EXIF extraction. You can monitor progress in the web UI. Subsequent scans only process new files and are much faster.

For automated container updates that handle Photoview upgrades alongside your other services, see our [Watchtower vs Diun vs DockCheck guide](../watchtower-vs-diun-vs-dockcheck-docker-container-update-tools/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Photoview Self-Hosted Photo Gallery Guide 2026",
  "description": "Complete guide to setting up Photoview, a fast and lightweight self-hosted photo gallery. Docker deployment, configuration, and comparison with Immich, PhotoPrism, and Piwigo.",
  "datePublished": "2026-04-29",
  "dateModified": "2026-04-29",
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

## FAQ

### Is Photoview free to use?

Yes, Photoview is fully open-source under the GNU General Public License v3.0. There are no paid tiers, premium features, or subscription requirements. You can run it on any hardware you own.

### Does Photoview sync photos from my phone?

No, Photoview does not have a mobile app or automatic photo sync. It indexes photos from directories already stored on your server. For automatic mobile sync, consider platforms like Immich or Nextcloud Photos, which upload new photos from your device to the server.

### What database should I use?

For libraries under 50,000 photos, SQLite is sufficient and requires no additional services. For larger collections, MariaDB or PostgreSQL provides better concurrency and performance. Photoview's official Docker Compose includes MariaDB by default.

### Can Photoview handle RAW image files?

Yes, Photoview supports RAW formats from major camera manufacturers including Canon (.CR2, .CR3), Nikon (.NEF), Sony (.ARW), Fujifilm (.RAF), and Adobe DNG. Thumbnails are generated from the embedded JPEG preview in the RAW file.

### Does Photoview support video files?

Yes, Photoview can transcode video files (MP4, MKV, MOV, AVI) to browser-friendly formats using FFmpeg. Hardware acceleration via Intel QuickSync, Nvidia NVENC, or AMD VA-API significantly speeds up transcoding.

### How does Photoview compare to Immich?

Immich is a full photo management platform with mobile sync, facial recognition, and automated search. Photoview is a focused gallery indexer — it reads existing photo directories and serves them via a web interface. Choose Immich if you want a Google Photos replacement; choose Photoview if you want a lightweight gallery for a server-based photo collection.

### Can multiple users access Photoview?

Yes, Photoview supports multi-user accounts. Each user has their own media library, and administrators can share albums across users. User management is handled through the web interface.

### Does Photoview modify my original photos?

No, Photoview accesses your media in read-only mode. All generated thumbnails, video transcodes, and EXIF data are stored separately in the media-cache directory. Your original files remain untouched.
