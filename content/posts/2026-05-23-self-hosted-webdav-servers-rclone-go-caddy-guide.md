---
title: "Self-Hosted WebDAV Servers: rclone serve vs go-webdav vs Caddy WebDAV"
date: "2026-05-23"
tags: ["webdav", "file-sharing", "cloud-storage", "self-hosted"]
draft: false
---

WebDAV (Web Distributed Authoring and Versioning) extends HTTP to enable collaborative file editing and remote content management. While many self-hosted file sharing solutions exist, running a dedicated WebDAV server gives you a lightweight, protocol-standard way to expose directories over HTTP — accessible by virtually any operating system or application.

This guide compares three popular approaches to self-hosting WebDAV servers: **rclone serve**, **go-webdav**, and the **Caddy WebDAV module**. Each targets a different use case, from quick cloud storage mounting to production-grade reverse-proxy deployments.

## What Is WebDAV and Why Use It?

WebDAV extends HTTP/1.1 with methods like `PROPFIND`, `PROPPATCH`, `MKCOL`, `COPY`, `MOVE`, `LOCK`, and `UNLOCK`. Unlike plain file sharing protocols (SMB, NFS), WebDAV works over standard HTTP/HTTPS ports (80/443), traverses NAT and firewalls naturally, and integrates with TLS for encryption.

Common use cases include:

- **Remote file access** — mount WebDAV shares as network drives on Windows, macOS, and Linux
- **Document collaboration** — LibreOffice, Microsoft Office, and many mobile apps support WebDAV natively
- **Backup targets** — Duplicati, Restic, and Kopia can push backups to WebDAV endpoints
- **Calendar and contacts sync** — CalDAV and CardDAV are built on WebDAV
- **CMS integration** — many content management systems use WebDAV for remote file management

## Comparison Overview

| Feature | rclone serve webdav | go-webdav | Caddy WebDAV Module |
|---------|---------------------|-----------|---------------------|
| **GitHub Stars** | 57,300+ (rclone core) | 479 | Part of Caddy (72,600+) |
| **Language** | Go | Go | Go |
| **License** | MIT | MIT | Apache 2.0 |
| **Backend Storage** | 70+ cloud providers, local, SFTP | Local filesystem, S3 | Local filesystem |
| **Authentication** | Basic Auth, htpasswd | Basic Auth, htpasswd | Basic Auth, API token |
| **TLS Support** | Via rclone serve flag | Via reverse proxy | Native (automatic HTTPS) |
| **Docker Image** | `rclone/rclone:latest` | Custom build | `caddy:latest` + xcaddy |
| **Reverse Proxy Ready** | Yes | Yes | Yes (built-in) |
| **Range Requests** | Yes | Yes | Yes |
| **Locking Support** | Partial | Yes | Yes |
| **Best For** | Cloud storage access | Lightweight standalone | Production deployments |

## rclone serve webdav

[rclone](https://github.com/rclone/rclone) is best known as a cloud storage sync tool, but its `serve webdav` subcommand turns it into a full WebDAV server. The key advantage: you can expose any of rclone's 70+ supported backends (S3, Google Drive, Dropbox, Backblaze B2, local filesystem) as a WebDAV endpoint.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  rclone-webdav:
    image: rclone/rclone:latest
    container_name: rclone-webdav
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./rclone.conf:/config/rclone/rclone.conf:ro
      - ./data:/data:rw
    command: >
      serve webdav remote:local/data
        --addr :8080
        --user admin
        --pass yourhashedpassword
        --read-only
```

Generate the password hash with `rclone password` and create a minimal `rclone.conf`:

```ini
[remote]
type = local
```

### Key Features

- **Multi-backend support** — Serve files from S3, Google Drive, OneDrive, or local disk through a single WebDAV endpoint
- **Bandwidth limiting** — `--bwlimit` flag caps upload/download speeds
- **VFS caching** — `--vfs-cache-mode writes` enables local caching for improved performance
- **Read-only mode** — `--read-only` flag prevents clients from modifying files
- **CORS support** — `--header "Access-Control-Allow-Origin: *"` for browser access

### Installation (Native)

```bash
# Install rclone
curl https://rclone.org/install.sh | sudo bash

# Create config directory
mkdir -p ~/.config/rclone

# Start WebDAV server
rclone serve webdav /path/to/data \
  --addr :8080 \
  --user admin \
  --pass "$(rclone obscure mypassword)" \
  --tls-cert /etc/ssl/certs/webdav.crt \
  --tls-key /etc/ssl/private/webdav.key
```

## go-webdav

[go-webdav](https://github.com/studio-b12/go-webdav) (also available at `emersion/go-webdav` as a library) provides a lightweight, standalone WebDAV server focused on simplicity and standards compliance. It implements the full RFC 4918 specification including locking, property management, and collection operations.

### Docker Compose Configuration

Since go-webdav is primarily a Go library, the standalone server requires a custom Docker image:

```dockerfile
FROM golang:1.22-alpine AS builder
RUN go install github.com/studio-b12/go-webdav/cmd/webdav@latest

FROM alpine:3.20
COPY --from=builder /go/bin/webdav /usr/local/bin/webdav
RUN mkdir -p /data
VOLUME ["/data"]
EXPOSE 8080
ENTRYPOINT ["webdav", "-addr", ":8080", "-prefix", "/data"]
```

```yaml
version: "3.8"
services:
  go-webdav:
    build: .
    container_name: go-webdav
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./data:/data:rw
    environment:
      - WEBDAV_USERNAME=admin
      - WEBDAV_PASSWORD=secretpassword
```

### Key Features

- **Full RFC 4918 compliance** — Complete WebDAV protocol implementation
- **Locking support** — Exclusive and shared locks for collaborative editing
- **Property management** — Custom metadata via `PROPPATCH`/`PROPFIND`
- **Lightweight footprint** — Minimal binary size, low memory usage
- **Standards-first design** — Compatible with any RFC-compliant WebDAV client

### Reverse Proxy with nginx

```nginx
server {
    listen 443 ssl http2;
    server_name webdav.example.com;

    ssl_certificate /etc/ssl/certs/webdav.crt;
    ssl_certificate_key /etc/ssl/private/webdav.key;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebDAV-specific headers
        proxy_set_header Authorization $http_authorization;
        proxy_pass_request_headers on;
    }
}
```

## Caddy WebDAV Module

[Caddy](https://github.com/caddyserver/caddy) with the WebDAV module (`github.com/mholt/caddy-webdav`) provides a production-ready WebDAV server with automatic HTTPS, built-in reverse proxy capabilities, and a comprehensive plugin ecosystem.

### Building Caddy with WebDAV Module

```bash
# Install xcaddy
go install github.com/caddyserver/xcaddy/cmd/xcaddy@latest

# Build Caddy with WebDAV plugin
xcaddy build --with github.com/mholt/caddy-webdav
```

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  caddy-webdav:
    image: caddy:2.8-builder
    container_name: caddy-webdav
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"
    volumes:
      - ./data:/srv/webdav:rw
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    environment:
      - ACME_AGREE=true

volumes:
  caddy_data:
  caddy_config:
```

### Caddyfile Configuration

```
webdav.example.com {
    root * /srv/webdav
    file_server browse

    webdav / {
        prefix /srv/webdav
    }

    basicauth / {
        admin JDJhJDE0$yourhashedpassword
    }

    tls admin@example.com
    encode gzip
    log {
        output file /var/log/caddy/access.log
    }
}
```

### Key Features

- **Automatic HTTPS** — Zero-config TLS certificate provisioning via Let's Encrypt
- **HTTP/3 support** — QUIC protocol for faster connections
- **Admin API** — Runtime configuration changes without restarts
- **Plugin ecosystem** — Extensible with dozens of Caddy modules
- **Structured logging** — JSON log output for integration with log aggregators

## Performance Comparison

| Metric | rclone serve | go-webdav | Caddy WebDAV |
|--------|-------------|-----------|--------------|
| **Binary Size** | ~90 MB | ~8 MB | ~85 MB (with module) |
| **Memory Usage** | ~50 MB | ~15 MB | ~40 MB |
| **Small File Throughput** | High (with VFS cache) | Medium | High |
| **Large File Streaming** | Excellent | Good | Excellent |
| **Concurrent Connections** | 100+ | 50+ | 1000+ |
| **TLS Overhead** | Manual config | Via proxy | Automatic |

## Choosing the Right WebDAV Server

**Use rclone serve webdav when:**
- You need to expose cloud storage (S3, Google Drive, Dropbox) as WebDAV
- You already use rclone for backup or sync workflows
- You want VFS caching for improved read performance

**Use go-webdav when:**
- You need a minimal, standards-compliant WebDAV server
- You're embedding WebDAV into a Go application
- Resource constraints require a lightweight binary

**Use Caddy WebDAV when:**
- You need automatic HTTPS without manual certificate management
- You want HTTP/3 support out of the box
- You're already running Caddy as a reverse proxy
- You need structured logging and an admin API

## Security Best Practices

1. **Always use TLS** — WebDAV transmits credentials in Basic Auth headers. Never expose it over plain HTTP on untrusted networks.
2. **Use strong passwords** — Generate passwords with `rclone obscure` or `htpasswd -B` for bcrypt hashing.
3. **Limit access by IP** — Add firewall rules or reverse proxy IP restrictions for internal-only WebDAV services.
4. **Enable read-only mode** — If clients only need to download files, use `--read-only` (rclone) or equivalent restrictions.
5. **Set rate limits** — Prevent abuse with bandwidth limiting (`--bwlimit`) or reverse proxy rate limiting.
6. **Monitor access logs** — Track failed authentication attempts and unusual file access patterns.

## Why Self-Host a WebDAV Server?

Running your own WebDAV server gives you complete control over file access, authentication, and data residency. Unlike commercial cloud storage services, you decide where your files live, who can access them, and how they're encrypted in transit.

For teams using document editing suites like LibreOffice or OnlyOffice, WebDAV provides a standardized protocol that works across platforms without requiring proprietary client software. Calendar and contact synchronization via CalDAV and CardDAV (built on WebDAV) lets you run a complete personal information server without depending on Google or Apple.

When combined with automated backup tools, a self-hosted WebDAV endpoint becomes a reliable backup target. Tools like Duplicati, Restic, and Kopia support WebDAV as a storage backend, enabling encrypted, incremental backups to your own infrastructure.

For organizations managing distributed teams, WebDAV offers a firewall-friendly file sharing protocol that works over standard HTTPS ports. Unlike SMB or NFS, it requires no special port forwarding or VPN configuration — just a TLS certificate and basic authentication.

For broader file sharing options, see our [Samba vs NFS vs WebDAV comparison](../2026-04-24-samba-vs-nfs-vs-webdav-self-hosted-file-sharing-guide-2026/). If you need file synchronization rather than live mounting, our [rsync vs rclone vs lsyncd guide](../2026-04-26-rsync-vs-rclone-vs-lsyncd-self-hosted-file-sync-tools-guide-2026/) covers the alternatives. For reverse proxy setups that can front your WebDAV server, check our [Caddy Docker proxy guide](../2026-04-24-nginx-proxy-manager-vs-swag-vs-caddy-docker-proxy-self-hosted-reverse-proxy-gui-guide-2026/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted WebDAV Servers: rclone serve vs go-webdav vs Caddy WebDAV",
  "description": "Compare self-hosted WebDAV server solutions: rclone serve, go-webdav, and Caddy WebDAV module. Docker Compose configs, performance comparison, and security best practices.",
  "datePublished": "2026-05-23",
  "dateModified": "2026-05-23",
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

### Can I use WebDAV with Windows File Explorer?

Yes. In Windows, open File Explorer, right-click "This PC," select "Add a network location," and enter your WebDAV URL (e.g., `https://webdav.example.com`). Windows will mount it as a network drive. For more reliable mounting, consider using the `net use` command or third-party clients like RaiDrive.

### Does WebDAV support file locking?

Yes, WebDAV implements both exclusive and shared locks per RFC 4918. Exclusive locks prevent other users from modifying a file, while shared locks allow multiple readers. rclone serve provides partial locking support, while go-webdav and Caddy WebDAV implement full locking.

### Can WebDAV replace Dropbox or Google Drive?

WebDAV provides the file access protocol but not the full feature set of commercial cloud services. You'll need to pair it with a frontend application (like Nextcloud or ownCloud) for features like file versioning, sharing links, and collaborative editing. However, for simple file access and backup, a standalone WebDAV server is sufficient.

### Is WebDAV secure enough for production use?

WebDAV over HTTPS (TLS 1.2+) is secure for production use. The protocol itself doesn't add security risks beyond standard HTTP. The key requirements are: valid TLS certificates, strong authentication (Basic Auth over TLS or OAuth via reverse proxy), and proper access controls on the underlying filesystem.

### How do I migrate from SMB/NFS to WebDAV?

WebDAV uses HTTP semantics, so the migration involves: (1) setting up a WebDAV server pointing to your existing data directory, (2) configuring authentication, (3) updating client configurations to use WebDAV URLs instead of SMB/NFS paths, and (4) testing file operations before decommissioning the old protocol. The data itself doesn't need to move — only the access method changes.

### Can I use WebDAV with mobile devices?

Yes. iOS and Android both support WebDAV natively. On iOS, the Files app can connect to WebDAV servers directly. On Android, apps like Solid Explorer, CX File Explorer, and FolderSync support WebDAV. Many calendar and contact apps also use WebDAV-based CalDAV/CardDAV for sync.

