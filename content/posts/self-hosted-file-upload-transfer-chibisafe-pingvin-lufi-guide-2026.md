---
title: "Best Self-Hosted File Upload & Transfer Services 2026: Chibisafe vs Pingvin Share vs Lufi"
date: 2026-04-14
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete guide to self-hosted file upload and transfer services in 2026. Compare Chibisafe, Pingvin Share, and Lufi as alternatives to WeTransfer and Dropbox Transfer."
---

Sharing large files shouldn't require handing your data over to a third-party cloud service. Services like WeTransfer, Dropbox Transfer, and Google Drive impose file size limits, scan your uploads, and often expire files on arbitrary timelines. Self-hosted file upload and transfer solutions give you full control over storage, expiration policies, access permissions, and bandwidth — all while keeping your files on your own infrastructure.

This guide covers the three best open-source self-hosted file upload services available in 2026: **Chibisafe**, **Pingvin Share**, and **Lufi**. Each serves a slightly different use case, and by the end of this guide you'll know exactly which one fits your needs.

## Why Self-Host Your File Transfers?

There are several compelling reasons to move away from hosted file transfer services:

- **No file size limits** — Set your own maximum. Your only constraint is disk space.
- **Privacy by design** — Files never leave your server. No third-party scanning, no data mining.
- **Zero recurring costs** — No monthly subscription fees. You pay for storage and bandwidth, period.
- **Full control over retention** — Define custom expiration policies: hours, days, weeks, or never expire.
- **Custom branding** — Remove all third-party branding and match the upload portal to your organization's identity.
- **Compliance** — Meet data residency requirements (GDPR, HIPAA, etc.) by keeping files within your own infrastructure.
- **API access** — Automate file uploads from scripts, CI/CD pipelines, or desktop applications.

If you regularly send files larger than 2 GB, work with sensitive data, or simply prefer owning your infrastructure, a self-hosted solution is the clear choice.

## Quick Comparison Table

| Feature | Chibisafe | Pingvin Share | Lufi |
|---|---|---|---|
| **Language** | TypeScript (Node.js) | TypeScript (NestJS + Next.js) | Perl (Catalyst) |
| **GitHub Stars** | 2,600+ | 4,600+ | 300+ |
| **End-to-End Encryption** | No | No | **Yes (client-side)** |
| **Max File Size** | Configurable (no hard limit) | Configurable (no hard limit) | Configurable |
| **Password Protection** | Yes | Yes | No (relies on encryption) |
| **Expiration Dates** | Yes | Yes | Yes |
| **User Accounts** | Yes | Optional | No |
| **Docker Support** | Official image | Official image | Community images |
| **Reverse Proxy Ready** | Yes | Yes | Yes |
| **API** | Full REST API | REST API | Web interface only |
| **Best For** | Power users, bulk uploads | General file sharing | Maximum privacy |

## 1. Chibisafe — Blazing Fast File Vault

[Chibisafe](https://github.com/chibisafe/chibisafe) is a high-performance file upload and management platform built with TypeScript and Node.js. Originally forked from lolisafe, it has evolved into a full-featured file vault with a modern web interface, robust API, and excellent documentation.

### Key Features

- **Chunked uploads** — Large files are split into chunks for reliable uploading, even on unstable connections.
- **File management dashboard** — Browse, search, preview, and delete uploaded files from a clean web UI.
- **Embed support** — Generate embed codes for images, videos, and audio files to share directly on websites.
- **Zip downloads** — Download multiple files as a single zip archive.
- **Customizable expiration** — Set per-file or default expiration times ranging from hours to never.
- **Role-based access** — Create user accounts with different permission levels (administrator, user).
- **Mimes and file-type restrictions** — Control which file types can be uploaded.
- **Storage backends** — Store files locally or on S3-compatible object storage (MinIO, Cloudflare R2, Backblaze B2).

### Docker Installation

Chibisafe provides an official Docker image and a bundled `docker-compose.yml` in the repository:

```yaml
version: "3"
services:
  chibisafe:
    image: ghcr.io/chibisafe/chibisafe:latest
    container_name: chibisafe
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - ./uploads:/home/chibisafe/uploads
      - ./logs:/home/chibisafe/logs
      - ./db:/home/chibisafe/db
    environment:
      - TZ=UTC
```

Save this as `docker-compose.yml` and start the service:

```bash
docker compose up -d
```

After startup, visit `http://your-server:3000` to access the web interface. The default admin credentials are created on first launch — follow the on-screen setup wizard.

### Caddy Reverse Proxy Configuration

```caddyfile
files.example.com {
    reverse_proxy localhost:3000
    encode gzip
    header {
        -Server
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
    }
}
```

### Nginx Reverse Proxy Configuration

```nginx
server {
    listen 80;
    server_name files.example.com;
    client_max_body_size 0;  # No size limit — let Chibisafe handle it

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }
}
```

### API Usage Example

Chibisafe's REST API makes it easy to upload files from scripts:

```bash
# Upload a file using the API
curl -X POST "https://files.example.com/api/upload" \
  -H "Authorization: YOUR_API_KEY" \
  -F "file=@large-video.mp4" \
  -F "expires=7d"
```

Response:

```json
{
  "url": "https://files.example.com/uploads/abc123-large-video.mp4",
  "name": "abc123-large-video.mp4",
  "size": 524288000,
  "expiresAt": "2026-04-21T00:00:00.000Z"
}
```

## 2. Pingvin Share — Beautiful and Lightweight

[Pingvin Share](https://github.com/stonith404/pingvin-share) is a self-hosted file sharing platform built with NestJS (backend) and Next.js (frontend). It emphasizes a clean, modern user interface and simplicity. With over 4,600 GitHub stars, it is one of the most popular self-hosted file sharing solutions.

### Key Features

- **Elegant UI** — Polished, responsive interface that works well on desktop and mobile.
- **Share links with passwords** — Protect downloads with a password that recipients must enter.
- **Visitor uploads** — Allow anyone to upload files without creating an account (configurable).
- **Email notifications** — Send download links via email directly from the interface.
- **Reverse proxy integration** — Works seamlessly behind Caddy, Nginx, or Traefik.
- **Quota management** — Set storage quotas per user or globally.
- **One-click share links** — Generate shareable links with customizable expiration times.
- **LDAP support** — Integrate with existing directory services for user authentication.

### Docker Installation

Pingvin Share ships with an official Docker image and a ready-to-use compose file:

```yaml
version: "3.8"
services:
  pingvin-share:
    image: stonith404/pingvin-share
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - "./data:/opt/app/backend/data"
      - "./images:/opt/app/frontend/public/img"
```

```bash
docker compose up -d
```

Visit `http://your-server:3000` to complete the initial setup. You'll create an admin account and configure default settings like maximum file size and default expiration.

### Advanced Configuration with Environment Variables

You can fine-tune Pingvin Share's behavior through environment variables:

```yaml
version: "3.8"
services:
  pingvin-share:
    image: stonith404/pingvin-share
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - "./data:/opt/app/backend/data"
      - "./images:/opt/app/frontend/public/img"
    environment:
      - TRUST_PROXY=true
      - MAX_FILE_SIZE=10737418240  # 10 GB in bytes
      - DEFAULT_EXPIRATION=7d
      - ALLOW_REGISTRATION=false
      - SESSION_SECRET=your-super-secret-key-change-this
```

### Traefik Reverse Proxy Configuration

For users running Traefik as their reverse proxy:

```yaml
version: "3.8"
services:
  pingvin-share:
    image: stonith404/pingvin-share
    restart: unless-stopped
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.pingvin.rule=Host(`share.example.com`)"
      - "traefik.http.routers.pingvin.entrypoints=websecure"
      - "traefik.http.routers.pingvin.tls.certresolver=letsencrypt"
      - "traefik.http.services.pingvin.loadbalancer.server.port=3000"
    volumes:
      - "./data:/opt/app/backend/data"
      - "./images:/opt/app/frontend/public/img"
```

## 3. Lufi — End-to-End Encrypted File Sharing

[Lufi](https://framagit.org/fiat-tux/hardware-projects/lufi) (Let's Upload that File) is a privacy-first file sharing application developed by the Framasoft non-profit organization. What sets Lufi apart from every other solution on this list is **client-side encryption**: files are encrypted in the browser before they are uploaded, meaning the server never sees the unencrypted content.

### Key Features

- **Client-side encryption** — Files are encrypted using AES-GCM in the browser before upload. The server stores only encrypted blobs.
- **Decentralized instances** — Lufi supports a federation model where multiple instances can store files for each other.
- **No account required** — Upload and share files without registering. The download link contains the decryption key.
- **Delayed deletion** — Files are automatically deleted after the chosen expiration period.
- **Minimal server requirements** — Lightweight Perl application that runs on minimal hardware.
- **Open source and auditable** — Developed by Framasoft, a well-known French free software advocacy group.
- **Countdown before download** — Optional delay before a file can be downloaded, adding a layer of abuse prevention.

### How the Encryption Works

The encryption model is the defining feature of Lufi:

1. **File selection** — User selects a file in the browser.
2. **Key generation** — The browser generates a random AES-256-GCM encryption key.
3. **Encryption** — The file is encrypted in the browser using this key.
4. **Upload** — Only the encrypted data is sent to the server.
5. **Link generation** — The download URL includes the decryption key as a URL fragment (`#key=...`).
6. **Download** — The recipient's browser extracts the key from the URL fragment, downloads the encrypted file, and decrypts it locally.

The URL fragment (everything after `#`) is **never sent to the server** by HTTP specification. This means the server literally cannot decrypt the files it stores.

### Docker Installation (Community Image)

While Lufi does not provide an official Docker image, several community-maintained images are available:

```yaml
version: "3"
services:
  lufi:
    image: hamzelot/lufi-docker:latest
    container_name: lufi
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - "./lufi/files:/home/lufi/files"
      - "./lufi/conf:/home/lufi/conf"
    environment:
      - Lufi_Contact=admin@example.com
      - Lufi_Maximum_file_size=10737418240
      - Lufi_Default_expiration=7
```

### Lufi Configuration File

Lufi uses a YAML configuration file (`lufi.conf`):

```yaml
---
# Lufi configuration
secret: "change-this-to-a-random-string"
dbtype: SQLite
dbname: "db/lufi.sqlite"

# Maximum file size in bytes (10 GB)
max_file_size: 10737418240

# Default expiration in days
default_expiration: 7

# Available expiration options (in days)
available_expirations:
  - 1
  - 7
  - 30
  - 365

# Contact email shown on the web interface
contact: admin@example.com

# Admin email for notifications
admin_mail: admin@example.com

# Enable or disable the countdown before download
delay_before_download: 0

# Instance name displayed on the web interface
instance_name: "My Lufi Instance"

# URL of this instance
url: "https://lufi.example.com"
```

### Nginx Configuration for Lufi

```nginx
server {
    listen 80;
    server_name lufi.example.com;

    # Lufi requires large upload size limits
    client_max_body_size 0;
    proxy_read_timeout 600s;
    proxy_send_timeout 600s;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (if needed for real-time features)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## Choosing the Right Solution

Each of these three tools serves a distinct audience. Here's how to decide:

### Choose Chibisafe if:

- You need a **full file vault** with browsing, previewing, and management capabilities
- You want **API access** for automated uploads from scripts or applications
- You plan to store files on **S3-compatible object storage** (MinIO, R2, B2)
- You need **user accounts** with role-based permissions
- You want **embed support** for media files
- You prefer **TypeScript/Node.js** ecosystem

### Choose Pingvin Share if:

- You want the **most polished user interface** out of the box
- You need **password-protected share links**
- You want to allow **anonymous uploads** from visitors
- You need **LDAP integration** for existing user directories
- You want **email notifications** for shared files
- You prefer **NestJS/Next.js** stack with modern web standards

### Choose Lufi if:

- **Maximum privacy** is your top priority
- You want **client-side encryption** so the server never sees unencrypted data
- You prefer a **no-account-required** model
- You want to participate in a **federated network** of Lufi instances
- You are running on **minimal hardware** (Lufi is very lightweight)
- You trust the **Framasoft** ecosystem and philosophy

## Storage Sizing Guide

Before deploying any of these services, plan your storage needs:

| Use Case | Recommended Storage | Notes |
|---|---|---|
| Personal file sharing | 500 GB – 1 TB | Occasional large file transfers between friends/colleagues |
| Team collaboration | 2 – 5 TB | Regular file sharing within a small team |
| Organization-wide | 10+ TB | Large org with many users, consider S3 backend |
| Archive/backup | Unlimited | Pair with external storage or cold archive tier |

For Chibisafe specifically, pairing with MinIO or Cloudflare R2 gives you effectively unlimited storage with lifecycle policies that automatically move older files to cheaper storage tiers.

## Security Best Practices

Regardless of which tool you choose, follow these security guidelines:

1. **Always use HTTPS** — Never serve file uploads over plain HTTP. Use Let's Encrypt for free TLS certificates.
2. **Set file size limits** — Prevent disk exhaustion attacks by configuring maximum upload sizes appropriate for your use case.
3. **Enable expiration** — Don't let files accumulate forever. Set default expiration times and enforce cleanup policies.
4. **Restrict file types** — Block executable uploads (`.exe`, `.sh`, `.bat`) to prevent malware distribution through your server.
5. **Rate limit uploads** — Use your reverse proxy to limit upload rates and prevent abuse.
6. **Regular backups** — Back up both the file data and the database. Without the database, you lose metadata (expiration dates, share links, user accounts).
7. **Monitor disk usage** — Set up alerts when disk usage exceeds 80% to prevent service disruption.
8. **Keep software updated** — All three projects release security updates. Subscribe to their GitHub release feeds or RSS notifications.

## Conclusion

Self-hosting your file transfer infrastructure eliminates the limitations and privacy concerns of services like WeTransfer and Dropbox Transfer. All three tools covered here are production-ready, actively maintained, and free to use:

- **Chibisafe** is the powerhouse — ideal for users who want a full-featured file vault with API access and S3 storage backends.
- **Pingvin Share** is the people's choice — beautiful UI, simple setup, and excellent for team collaboration with password-protected links.
- **Lufi** is the privacy champion — client-side encryption means even the server administrator cannot read your files.

Pick the one that matches your threat model, technical comfort level, and infrastructure. You'll be sharing files on your own terms within minutes of deployment.
