---
title: "PsiTransfer vs Magic Wormhole vs FileShelter: Self-Hosted File Sharing Guide 2026"
date: 2026-04-23
tags: ["comparison", "guide", "self-hosted", "file-sharing", "privacy"]
draft: false
description: "Compare PsiTransfer, Magic Wormhole, and FileShelter for self-hosted secure file sharing. Includes Docker setup, configuration guides, and a detailed comparison table for 2026."
---

Sending large files between computers shouldn't require trusting a third-party cloud service. Commercial platforms like Dropbox, WeTransfer, and Google Drive scan your data, impose file size limits, and can suspend your account at any time. Self-hosted file sharing tools give you full control: no accounts, no tracking, no arbitrary limits, and files stored on your own infrastructure.

In this guide, we compare three distinct approaches to self-hosted file sharing — **PsiTransfer**, **Magic Wormhole**, and **FileShelter** — each with different strengths depending on your use case. Whether you need a web-based portal for sending files to clients, a secure CLI tool for peer-to-peer transfers, or a lightweight one-click uploader, this comparison will help you choose.

## Why Self-Host Your File Sharing

Sending files through commercial services means accepting their terms, their storage limits, and their data handling policies. Self-hosted alternatives address these concerns:

- **Complete data sovereignty**: Files never leave your server. No third-party scanning, no advertising profiling, no government subpoenas handed to cloud providers.
- **No file size limits**: Your storage is your limit. Transfer multi-gigabyte video files, database dumps, or VM images without paying premium tiers.
- **Expiring links with zero trace**: Set automatic deletion timers so files are permanently removed after download or after a time window expires.
- **No registration required**: Most self-hosted tools require no accounts for senders or recipients — upload a file, share the link, done.
- **Auditability**: Open-source code means you can verify exactly how files are handled, stored, and deleted.

## PsiTransfer: Simple Web-Based File Sharing

[PsiTransfer](https://github.com/psi-4ward/psitransfer) is a Node.js-based self-hosted file sharing solution designed as a drop-in replacement for services like WeTransfer. It features a clean, responsive web interface and requires zero configuration for basic use. With over 1,800 GitHub stars, it is one of the most popular self-hosted file transfer tools.

### Key Features

- **No accounts or logins**: Anyone with the URL can upload or download files
- **Resumable transfers**: Built on the [tus.io](https://tus.io) protocol for resumable uploads and downloads, critical for large files on unstable connections
- **One-time download links**: Files are deleted immediately after the configured number of downloads
- **Time-based expiry**: Set expiration from 10 minutes to 1 year
- **Admin dashboard**: Password-protected admin interface to manage active shares
- **Multi-file uploads**: Upload entire directories with drag-and-drop
- **Responsive UI**: Works well on mobile devices

### PsiTransfer Docker Setup

PsiTransfer has an official Docker image (`psitrax/psitransfer`) on Docker Hub. Here is a production-ready Docker Compose configuration:

```yaml
version: "3.8"
services:
  psitransfer:
    image: psitrax/psitransfer:2
    container_name: psitransfer
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - PSITRANSFER_ADMIN_PASS=YourSecureAdminPassword
      - PSITRANSFER_UPLOAD_DIR=/data
      - PSITRANSFER_ONETIME_URLS=false
    volumes:
      - ./data:/data
    user: "1000:1000"
```

After creating this `docker-compose.yml`, deploy with:

```bash
# Create the data directory and set correct ownership
mkdir -p data
sudo chown -R 1000:1000 data

# Start the service
docker compose up -d

# Check logs
docker compose logs -f psitransfer
```

The web interface will be available at `http://your-server:3000`. The admin dashboard is at `http://your-server:3000/admin` using the password you set in `PSITRANSFER_ADMIN_PASS`.

### Configuration Options

PsiTransfer supports several environment variables for customization:

```bash
# Core settings
PSITRANSFER_ADMIN_PASS=secret          # Admin password (required)
PSITRANSFER_UPLOAD_DIR=/data           # Upload storage directory
PSITRANSFER_ONETIME_URLS=true          # Enable one-time download links
PSITRANSFER_MAX_UPLOAD_SIZE=10737418240  # Max upload size in bytes (10 GB)
PSITRANSFER_DEFAULT_EXPIRE=1d          # Default expiration time
PSITRANSFER_LANG=en                    # Interface language

# Advanced settings
PSITRANSFER_BUCKET_ALGORITHM=s3        # Use S3-compatible storage backend
PSITRANSFER_ACCESS_KEY_ID=your-key     # S3 access key
PSITRANSFER_SECRET_ACCESS_KEY=your-secret  # S3 secret key
PSITRANSFER_BUCKET_NAME=my-bucket      # S3 bucket name
```

For large-scale deployments, PsiTransfer can use an S3-compatible backend (MinIO, AWS S3, Cloudflare R2) instead of local disk storage. This enables horizontal scaling and separates compute from storage.

### Reverse Proxy Configuration (Nginx)

For production use behind a reverse proxy with TLS:

```nginx
server {
    listen 443 ssl http2;
    server_name files.example.com;

    ssl_certificate /etc/letsencrypt/live/files.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/files.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Support large file uploads
        client_max_body_size 0;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
```

## Magic Wormhole: Secure Peer-to-Peer File Transfer

[Magic Wormhole](https://github.com/magic-wormhole/magic-wormhole) takes a fundamentally different approach. Instead of uploading to a server and sharing a link, it establishes a direct encrypted connection between two computers using a short, human-readable "wormhole code." With over 22,000 GitHub stars, it is by far the most popular tool in this comparison.

The concept is simple: the sender generates a code like `7-crossover-smoke`, the receiver types it in, and the files transfer directly between the two machines. No persistent server storage, no lingering files, no web interface.

### Key Features

- **End-to-end encryption**: Uses PAKE (Password-Authenticated Key Exchange) — the wormhole code acts as both identifier and encryption key
- **No intermediate storage**: Files flow directly between machines (or through a transit relay if NAT traversal fails)
- **Human-readable codes**: Short codes like `5-verb-staple` are easy to communicate verbally or over chat
- **Single-use codes**: Each code works exactly once, preventing replay attacks
- **CLI-first design**: Ideal for developers and sysadmins comfortable with the terminal
- **Python-based**: Easy to install via pip on any system with Python 3.10+

### Installation

```bash
# Install via pip (recommended)
pip3 install magic-wormhole

# Or via package manager on Debian/Ubuntu
apt install magic-wormhole

# Or on macOS
brew install magic-wormhole
```

### Usage Examples

**Send a file:**

```bash
# Send a single file
wormhole send report.pdf
# Output: Sending 2.4 MB file named 'report.pdf'
# Wormhole code is: 7-crossover-smoke

# Send a directory
wormhole send /path/to/project/

# Send text
wormhole send --text "Server credentials: backup-db-01 / p@ssw0rd"
```

**Receive a file:**

```bash
# Receive with the code provided by sender
wormhole receive 7-crossover-smake
# Output: Receiving file (2.4 MB) named 'report.pdf'
# ok? (y/N): y
# Receiving (<File|172.16.0.5:4001>)..
# 100%|████████████████████| 2.4 MB/2.4 MB [00:03<00:00, 800 kB/s]
# Received file written to report.pdf
```

### Self-Hosting the Wormhole Mailbox Server

By default, Magic Wormhole uses the project's public mailbox server. For full self-hosting, you can run your own mailbox server and transit relay:

```bash
# Install the mailbox server
pip3 install magic-wormhole-mailbox-server

# Start the mailbox server
twist -n wormhole-mailbox --usage-db=usage.sqlite --blur-usage=3600

# Install the transit relay
pip3 install magic-wormhole-transit-relay

# Start the transit relay
twist -n transit-relay --usage-db=transit-usage.sqlite
```

Then configure your local wormhole client to use your own servers:

```bash
# Create or edit ~/.wormhole.conf
[wormhole]
relay_url = ws://your-server:4000/v1
transit_helper = tcp:your-server:4001
```

### Docker Compose for Self-Hosted Wormhole Infrastructure

```yaml
version: "3.8"
services:
  mailbox:
    image: ghcr.io/magic-wormhole/magic-wormhole-mailbox-server:latest
    container_name: wormhole-mailbox
    restart: unless-stopped
    ports:
      - "4000:4000"
    volumes:
      - ./mailbox-data:/data
    command: ["twist", "-n", "wormhole-mailbox", "--usage-db=/data/usage.sqlite"]

  transit:
    image: ghcr.io/magic-wormhole/magic-wormhole-transit-relay:latest
    container_name: wormhole-transit
    restart: unless-stopped
    ports:
      - "4001:4001"
    volumes:
      - ./transit-data:/data
    command: ["twist", "-n", "transit-relay", "--usage-db=/data/usage.sqlite"]
```

## FileShelter: Lightweight One-Click File Sharing

[FileShelter](https://github.com/epoupon/fileshelter) is a C++-based web application focused on simplicity and low resource usage. The entire demo instance runs on a Raspberry Pi. With 536 GitHub stars, it is smaller in community but offers a polished, feature-rich experience with minimal overhead.

### Key Features

- **One-click sharing**: Upload files and instantly get a shareable URL
- **Password protection**: Optional passwords for both download and upload actions
- **Configurable expiry**: Set validity from 1 hour to several years
- **UUID-based links**: Practically unguessable share URLs
- **On-the-fly ZIP**: Multiple files are compressed into a ZIP for download
- **Terms of Service support**: Customizable ToS page for compliance
- **CLI management tool**: `fileshelter-cmd` to list, create, and destroy shares from the terminal
- **Low resource usage**: Runs comfortably on a Raspberry Pi with under 100 MB RAM
- **Multi-language**: Interface available in multiple languages

### FileShelter Docker Setup

FileShelter provides official Docker images. Here is a Docker Compose configuration:

```yaml
version: "3.8"
services:
  fileshelter:
    image: epoupon/fileshelter:latest
    container_name: fileshelter
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./data:/var/fileshelter
      - ./config/fileshelter.conf:/etc/fileshelter.conf:ro
    environment:
      - TZ=UTC
```

Create the configuration file at `./config/fileshelter.conf`:

```ini
[share]
# Maximum upload size in bytes (100 MB)
max-size = 104857600

# Maximum number of files per share
max-files = 20

# Default share duration in seconds (24 hours)
default-duration = 86400

[server]
# Listening port
port = 8080

# Number of worker threads
threads = 4

[security]
# Require password for downloads
download-password = false

# Enable upload password
upload-password = true
```

Deploy with:

```bash
mkdir -p data config
# Place fileshelter.conf in config/
docker compose up -d
```

### Command Line Management

FileShelter includes `fileshelter-cmd` for managing shares from the terminal:

```bash
# List all active shares
fileshelter-cmd --config /etc/fileshelter.conf list

# Create a new share from local files
fileshelter-cmd --config /etc/fileshelter.conf create --duration 7d report.pdf data.csv

# Destroy an expired or sensitive share
fileshelter-cmd --config /etc/fileshelter.conf destroy <share-id>
```

## Comparison Table

| Feature | PsiTransfer | Magic Wormhole | FileShelter |
|---|---|---|---|
| **GitHub Stars** | 1,874 | 22,554 | 536 |
| **Language** | JavaScript (Node.js) | Python | C++ |
| **Interface** | Web UI | CLI only | Web UI + CLI |
| **Transfer Mode** | Server-stored | Direct P2P | Server-stored |
| **File Expiry** | Time or download count | Immediate (no storage) | Time-based |
| **Password Protection** | Admin access only | Code-based (PAKE) | Download + upload |
| **Resumable Transfers** | Yes (tus.io protocol) | No | No |
| **Max File Size** | Unlimited (disk-limited) | Limited by RAM/disk | Configurable |
| **Storage Backend** | Local disk or S3 | None (P2P) | Local disk |
| **Self-Hosted Server** | Yes | Yes (mailbox + relay) | Yes |
| **Docker Image** | `psitrax/psitransfer` | Community images | `epoupon/fileshelter` |
| **Min Hardware** | 256 MB RAM | 128 MB RAM | 64 MB RAM (Raspberry Pi) |
| **Multi-file Upload** | Yes (drag-and-drop) | Yes (directory) | Yes |
| **One-time Links** | Yes | Yes (single-use code) | No |
| **Admin Dashboard** | Yes | No | No (CLI only) |
| **Terms of Service** | No | No | Yes |
| **Best For** | Web-based file portal | Secure P2P transfers | Lightweight sharing |

## Which Tool Should You Choose?

### Choose PsiTransfer When:
- You want a **WeTransfer-like experience** on your own server
- Recipients are non-technical and need a simple web interface
- You need **resumable uploads** for files larger than a few gigabytes
- You want S3-compatible storage for scale and redundancy
- An admin dashboard to monitor active shares is important

PsiTransfer is the most straightforward option for teams that regularly share large files with external parties. The tus.io protocol support means interrupted uploads can resume rather than restart — a critical feature when sending 10+ GB files.

### Choose Magic Wormhole When:
- **Maximum security** is your priority — PAKE encryption means the server never sees your files
- You transfer files between your own machines regularly
- You work from the terminal and prefer CLI tools
- You don't want files stored on any server, even temporarily
- You need to send files to someone over a phone call (read the code verbally)

Magic Wormhole is the most secure option because it eliminates the server-as-middleman entirely. Files flow directly between endpoints. The mailbox server only coordinates the handshake; it never touches file content.

### Choose FileShelter When:
- You have **limited server resources** (Raspberry Pi, low-end VPS)
- You want password-protected shares with minimal setup
- You need a Terms of Service page for compliance
- You prefer a C++ application over Node.js or Python for performance
- You want CLI tools for automated share management

FileShelter's C++ foundation means it uses the least memory and CPU of the three options. If you are running a homelab on a Raspberry Pi or a $5/month VPS, FileShelter is the most resource-efficient choice.

## Security Considerations

Regardless of which tool you choose, follow these security best practices:

1. **Always use TLS/HTTPS**: Place a reverse proxy (Nginx, Caddy, or Traefik) in front of the service. Never expose file sharing over plain HTTP.
2. **Set reasonable file size limits**: Even with self-hosting, you should cap upload sizes to prevent disk exhaustion attacks. PsiTransfer supports `PSITRANSFER_MAX_UPLOAD_SIZE`, FileShelter uses `max-size` in its config.
3. **Use short expiry times**: Files should not live forever. Set the shortest expiry that meets your workflow needs. One-time download links provide the strongest guarantee.
4. **Restrict network access**: If the tool is only for internal use, bind to localhost and use a VPN or reverse proxy with authentication.
5. **Monitor disk usage**: Automated cleanup is essential. PsiTransfer and FileShelter both delete expired files automatically, but monitor your data volume to ensure cleanup is working.

For related reading, see our [Nextcloud vs ownCloud comparison](../nextcloud-vs-owncloud/) for a full-featured file sync and collaboration platform, the [MinIO self-hosted S3 storage guide](../minio-self-hosted-s3-object-storage-guide-2026/) if you need object storage backends, and our guide on [Mozilla SOPS vs git-crypt vs Age](../2026-04-23-mozilla-sops-vs-git-crypt-vs-age-self-hosted-secrets-encryp/) for encrypting sensitive files before sharing.

## FAQ

### Is self-hosted file sharing more secure than cloud services like Dropbox?

Self-hosted file sharing eliminates the third-party risk. With commercial services, your files are stored on servers you don't control, subject to the provider's privacy policy, and potentially accessible to employees or law enforcement. Self-hosted tools keep files on your own infrastructure, encrypted at rest if you choose, with access controlled entirely by you. Magic Wormhole goes further by storing nothing at all — files transfer directly between endpoints.

### Can these tools handle files larger than 10 GB?

PsiTransfer handles files of any size limited only by your disk space, and the tus.io protocol ensures resumable uploads even for very large files. FileShelter supports configurable size limits via its `max-size` configuration. Magic Wormhole transfers files directly between machines, so the limit is your available RAM and network bandwidth, though extremely large files may be slower due to the lack of resumable transfer support.

### Do recipients need to install anything to download files?

For PsiTransfer and FileShelter, recipients only need a web browser — no software installation required. They open the shared URL and download directly. Magic Wormhole requires both sender and receiver to have the `wormhole` CLI tool installed, making it best for technical users who transfer files frequently.

### How do I add TLS/HTTPS to my self-hosted file sharing service?

The recommended approach is to place a reverse proxy like Nginx or Caddy in front of the service. Use Let's Encrypt for free TLS certificates. For PsiTransfer running on port 3000, configure your reverse proxy to forward `https://files.example.com` to `http://127.0.0.1:3000`. Caddy can automate this entirely with a single line: `reverse_proxy 127.0.0.1:3000`.

### Can I use an S3-compatible backend for PsiTransfer?

Yes, PsiTransfer supports S3-compatible storage backends including AWS S3, MinIO, and Cloudflare R2. Set `PSITRANSFER_BUCKET_ALGORITHM=s3` along with your access key, secret key, and bucket name. This is useful for production deployments where you want to separate the application server from storage, enable horizontal scaling, or use cheaper object storage for infrequently accessed files.

### What happens to files after the expiry time?

Both PsiTransfer and FileShelter automatically delete files after the configured expiry period. FileShelter waits approximately two hours after expiry before deleting files, ensuring that an active download in progress is not interrupted. Magic Wormhole stores no files at all — the transfer is direct and ephemeral, so there is nothing to clean up.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "PsiTransfer vs Magic Wormhole vs FileShelter: Self-Hosted File Sharing Guide 2026",
  "description": "Compare PsiTransfer, Magic Wormhole, and FileShelter for self-hosted secure file sharing. Includes Docker setup, configuration guides, and a detailed comparison table for 2026.",
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
