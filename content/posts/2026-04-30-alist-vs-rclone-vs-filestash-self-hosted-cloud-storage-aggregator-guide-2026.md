---
title: "Alist vs Rclone vs Filestash: Self-Hosted Cloud Storage Aggregator 2026"
date: 2026-04-30
tags: ["comparison", "guide", "self-hosted", "cloud-storage", "webdav", "file-management"]
draft: false
description: "Compare Alist, Rclone, and Filestash for self-hosted cloud storage aggregation. Learn how to unify S3, Google Drive, OneDrive, and more behind a single WebDAV interface."
---

Managing files across multiple cloud storage providers — Google Drive, OneDrive, Amazon S3, Dropbox, and Backblaze B2 — quickly becomes a headache. Each service has its own API, authentication flow, and web interface. A self-hosted cloud storage aggregator solves this by presenting a unified file management layer over all your backends, accessible through a single WebDAV endpoint or web UI.

In this guide, we compare three leading open-source options: **Alist**, **Rclone** (with its serve/rclone rcd mode), and **Filestash**. Each takes a different approach to the same problem, and choosing the right one depends on whether you prioritize a modern web interface, raw syncing power, or a universal data access layer.

## Why Self-Host a Cloud Storage Aggregator

Cloud storage lock-in is real. You might have personal photos on Google Drive, project files on OneDrive, backups on Backblaze B2, and archives on S3. Switching providers means migrating gigabytes — or terabytes — of data. An aggregator lets you keep everything where it is while accessing it through one unified interface.

Self-hosting gives you several advantages over commercial multi-cloud managers:

- **No subscription fees** — all three tools are free and open-source
- **Full data control** — your credentials and tokens never leave your server
- **WebDAV mounting** — mount all your cloud storage as a single local filesystem on any device
- **Custom integrations** — connect to Kodi, Plex, file managers, or backup tools via standard protocols
- **No rate-limit surprises** — commercial aggregators often throttle; self-hosted solutions use your own API quotas

## Alist: Unified File List with WebDAV

[Alist](https://github.com/alist-org/alist) is the most popular self-hosted cloud storage aggregator, with over 49,000 GitHub stars. Built with Gin (Go backend) and Solid.js (frontend), it provides a polished web interface for browsing and managing files across 30+ storage backends.

**Key features:**

- Supports 30+ storage drivers: S3, Google Drive, OneDrive, Dropbox, WebDAV, FTP, SFTP, Alibaba Cloud OSS, Tencent COS, Baidu NetDisk, and more
- Built-in WebDAV server for mounting as a local drive
- File preview for images, videos, documents, and audio
- User authentication with admin and guest roles
- Offline download support
- API for programmatic access
- SSO/OAuth2 integration

**GitHub stats:** 49,391 stars · last updated April 2026

## Rclone: The Swiss Army Knife of Cloud Storage

[Rclone](https://github.com/rclone/rclone) is the veteran tool in this space — "rsync for cloud storage" — with nearly 57,000 stars. While it's primarily a command-line sync tool, its `rclone serve` and `rclone rcd` (remote control daemon) modes turn it into a capable cloud storage aggregator.

**Key features:**

- Supports 70+ storage providers — more than any other tool in this comparison
- Bidirectional sync, copy, move, and delete across providers
- `rclone serve webdav` exposes any backend as a WebDAV server
- `rclone serve http` provides a basic HTTP file browser
- Encryption support (crypt remote) for client-side encrypted storage
- Bandwidth limiting, transfer scheduling, and retry logic
- Mature, battle-tested codebase since 2014
- Mount mode (via FUSE) for direct filesystem access

**GitHub stats:** 56,932 stars · last updated April 2026

## Filestash: Universal Data Access Layer

[Filestash](https://github.com/mickael-kerjean/filestash) takes a different approach — it's a file management platform designed as a universal data access layer. With over 14,000 stars, it provides a rich web UI with file preview, editing, and sharing capabilities across multiple backends.

**Key features:**

- Connects to SFTP, S3, SMB, FTP, WebDAV, Git, LDAP, and more
- Built-in file editor with syntax highlighting
- File sharing with expiring links and access control
- Image and document preview
- Plugin architecture for extending functionality
- LDAP/Active Directory authentication
- Search across connected backends
- Docker-first deployment

**GitHub stats:** 14,121 stars · last updated April 2026

## Feature Comparison

| Feature | Alist | Rclone (serve) | Filestash |
|---------|-------|----------------|-----------|
| Storage backends | 30+ | 70+ | 15+ |
| Web interface | Modern, responsive | Basic HTTP browser | Rich, full-featured |
| WebDAV server | Built-in | Via `rclone serve webdav` | Via plugin |
| File preview | Images, video, docs, audio | Limited | Images, docs, code |
| User management | Built-in (admin/guest) | None (single user) | LDAP, built-in |
| API | REST API | Remote control API | REST API |
| Encryption | No | Built-in (crypt) | No |
| Offline download | Yes | Via sync commands | No |
| File sharing links | No | No | Yes (expiring links) |
| Docker support | Official image | Official image | Official image |
| FUSE mount | No | Yes | No |
| License | GPL-3.0 | MIT | AGPL-3.0 |

## Docker Deployment

All three tools can be deployed with Docker Compose. Here are production-ready configurations.

### Alist Docker Compose

Alist uses the official `xhofe/alist` image and stores configuration in a mounted volume:

```yaml
version: '3.3'
services:
  alist:
    image: xhofe/alist:latest
    container_name: alist
    restart: always
    ports:
      - '5244:5244'
      - '5245:5245'
    volumes:
      - /opt/alist/data:/opt/alist/data
    environment:
      - PUID=1000
      - PGID=1000
      - UMASK=022
      - TZ=UTC
```

After starting the container, get the initial admin password:

```bash
docker exec alist ./alist admin random
```

Then access the web UI at `http://your-server:5244`. From the admin panel, add storage backends through **Manage → Storage → Add**. Each backend type has its own configuration fields — for Google Drive, you'll need OAuth credentials; for S3, just access keys.

### Rclone Docker Compose

Rclone's Docker image requires a configuration directory and exposes both the WebDAV server and the remote control API:

```yaml
version: '3.8'
services:
  rclone:
    image: rclone/rclone:latest
    container_name: rclone
    restart: always
    ports:
      - '8080:8080'   # WebDAV
      - '5572:5572'   # Remote control API
    volumes:
      - /opt/rclone/config:/config/rclone
      - /opt/rclone/cache:/cache
    command: >
      serve webdav
      --addr :8080
      --rc
      --rc-addr :5572
      --rc-user=admin
      --rc-pass=changeme
      --read-only=false
    environment:
      - TZ=UTC
```

Configure your remotes before starting:

```bash
docker run --rm -it -v /opt/rclone/config:/config/rclone rclone/rclone config
```

This launches the interactive configuration wizard where you add each cloud provider. Once configured, the WebDAV endpoint at `http://your-server:8080` serves all your remotes under a unified namespace.

### Filestash Docker Compose

Filestash's official image is straightforward — it just needs a data volume for persistence:

```yaml
version: '3.8'
services:
  filestash:
    image: machines/filestash:latest
    container_name: filestash
    restart: always
    ports:
      - '8334:8334'
    volumes:
      - /opt/filestash/data:/app/data
    environment:
      - APPLICATION_URL=http://your-server:8334
      - TZ=UTC
```

On first access at `http://your-server:8334`, you'll set up an admin account and then connect storage backends through the web interface. Filestash supports S3, SFTP, SMB, and FTP out of the box, with additional connectors available as plugins.

## Configuration Examples

### Adding Google Drive to Alist

```bash
# 1. Create OAuth credentials in Google Cloud Console
# 2. Add storage via Alist admin panel:
#    Manage → Storage → Add → Google Drive
# 3. Fill in:
#    - Client ID: your-oauth-client-id
#    - Client Secret: your-oauth-client-secret
#    - Refresh Token: generate via OAuth flow
# 4. Click "Add" and the drive appears in your file list
```

For headless setups, you can also configure via the API:

```bash
curl -X POST http://localhost:5244/api/admin/storage \
  -H "Content-Type: application/json" \
  -H "Authorization: <admin-token>" \
  -d '{
    "driver": "GoogleDrive",
    "mount_path": "/gdrive",
    "addition": {
      "client_id": "your-client-id",
      "client_secret": "your-client-secret",
      "refresh_token": "your-refresh-token"
    }
  }'
```

### Mounting Rclone WebDAV as Local Drive

Once Rclone's WebDAV server is running, mount it on any Linux system:

```bash
sudo apt install davfs2
sudo mkdir /mnt/cloud-storage
sudo mount -t davfs http://your-server:8080 /mnt/cloud-storage \
  -o username=admin,password=changeme
```

Or add to `/etc/fstab` for automatic mounting:

```
http://your-server:8080 /mnt/cloud-storage davfs rw,user,username=admin,password=changeme 0 0
```

On macOS, use the Finder's **Go → Connect to Server** (Cmd+K) and enter `http://your-server:8080` as a WebDAV URL.

### Filestash with S3 and SFTP

Filestash lets you connect multiple backends and browse them from a single interface. After initial setup:

1. Navigate to **Admin → Connections → Add**
2. Select **S3** as the backend type
3. Enter your bucket name, region, access key, and secret key
4. Save and repeat for SFTP, providing hostname, port, username, and key file
5. Both backends now appear in your file browser sidebar

You can share files across backends — copy from S3 to SFTP, download from any source, or preview documents without downloading.

## Which One Should You Choose?

**Choose Alist if:** You want the best balance of features, ease of use, and visual polish. It has a modern web UI, supports 30+ backends, and its WebDAV server works out of the box. It's the best choice for personal use — mounting your cloud storage on your desktop, accessing files from a phone browser, or serving media to Kodi.

**Choose Rclone if:** You need maximum backend coverage (70+ providers), bidirectional sync, encryption, or FUSE mounting. Rclone is the power user's choice — ideal for automated backup pipelines, data migration between providers, or when you need crypt-level encryption for sensitive data. The tradeoff is a less polished web interface.

**Choose Filestash if:** You need a full-featured file management platform with sharing, editing, and LDAP authentication. Filestash excels as a team collaboration tool — its expiring share links, built-in file editor, and access control make it suitable for small teams that need a self-hosted alternative to Google Drive's collaboration features.

## Internal Resources

For related infrastructure guides, check out our [WebDAV file sharing setup](../2026-04-24-samba-vs-nfs-vs-webdav-self-hosted-file-sharing-guide-2026/) for configuring WebDAV clients across platforms, our [web file manager comparison](../filebrowser-vs-filegator-vs-cloud-commander-self-hosted-web-file-managers-2026/) for local file browsing, and our [document sharing platforms guide](../2026-04-27-papermark-vs-filestash-vs-pingvin-share-self-hosted-document-sharing-2026/) which covers Filestash in the context of secure file distribution.

## FAQ

### What is a cloud storage aggregator?

A cloud storage aggregator is a self-hosted service that connects to multiple cloud storage providers (Google Drive, S3, OneDrive, etc.) and presents them through a single unified interface. Instead of logging into five different services, you access everything through one web UI or WebDAV endpoint.

### Do I need to move my files to use Alist or Rclone?

No. These tools connect to your existing cloud storage accounts via APIs. Your files stay in their original locations — Alist and Rclone simply provide a unified access layer. There's no data migration required.

### Which tool supports the most storage providers?

Rclone supports 70+ storage providers, far more than Alist (30+) or Filestash (15+). If you need to connect to an obscure or enterprise storage system, Rclone is most likely to support it.

### Can I mount cloud storage as a local drive?

Yes. Alist and Rclone both expose WebDAV endpoints that can be mounted as network drives on Windows, macOS, and Linux. Additionally, Rclone supports FUSE mounting (`rclone mount`) which provides a native filesystem interface with on-demand downloading.

### Is it safe to store cloud credentials on my server?

All three tools store credentials server-side, encrypted at rest. Since you control the server, this is generally more secure than using commercial multi-cloud services where your tokens pass through third-party infrastructure. Use a dedicated user account with minimal permissions for each connected storage provider.

### Can these tools replace Google Drive entirely?

For file storage and access, yes — especially when combined with multiple backends. However, they don't replace Google Docs' real-time collaboration features. Filestash comes closest with its built-in file editor, but none of these tools offer simultaneous multi-user document editing like Google Workspace.

### How do I back up my aggregator configuration?

For Alist, back up the `/opt/alist/data` directory. For Rclone, back up `/opt/rclone/config/rclone.conf`. For Filestash, back up `/opt/filestash/data`. Store these backups on a separate storage backend not managed by the aggregator itself.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Alist vs Rclone vs Filestash: Self-Hosted Cloud Storage Aggregator 2026",
  "description": "Compare Alist, Rclone, and Filestash for self-hosted cloud storage aggregation. Learn how to unify S3, Google Drive, OneDrive, and more behind a single WebDAV interface.",
  "datePublished": "2026-04-30",
  "dateModified": "2026-04-30",
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
