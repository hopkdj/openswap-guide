---
title: "Papermark vs Filestash vs Pingvin Share: Best Self-Hosted Document Sharing 2026"
date: 2026-04-27
tags: ["comparison", "guide", "self-hosted", "document-sharing", "file-sharing", "privacy"]
draft: false
description: "Compare Papermark, Filestash, and Pingvin Share — three open-source, self-hosted document and file sharing platforms. Includes Docker Compose configs, feature comparison, and deployment guides."
---

Sharing documents and files externally is a daily requirement for teams, freelancers, and organizations. Cloud services like DocSend, WeTransfer, and Google Drive dominate this space, but they come with privacy concerns, vendor lock-in, and recurring subscription costs. Self-hosted alternatives give you full control over your data, branding, and access policies — without handing your documents to a third party.

In this guide, we compare three leading open-source, self-hosted document and file sharing platforms: **Papermark**, **Filestash**, and **Pingvin Share**. Each takes a different approach to the problem, and the right choice depends on whether you prioritize analytics, universal file access, or simple elegant sharing.

## Why Self-Host Your Document Sharing?

Before diving into the tools, here is why self-hosting document sharing makes sense for many organizations:

- **Data sovereignty**: Your documents never leave your infrastructure. This is critical for legal, healthcare, and financial sectors subject to GDPR, HIPAA, or SOC 2 compliance.
- **No vendor lock-in**: You are not dependent on a SaaS provider's pricing changes, feature removals, or service outages.
- **Custom branding**: Present documents under your own domain with your logo and colors — essential for client-facing materials like pitch decks, proposals, and contracts.
- **Cost savings**: Eliminate per-user or per-document licensing fees. Most self-hosted solutions are free and open-source.
- **Access control**: Define exactly who can view, download, or forward your documents with expiring links, password protection, and IP restrictions.

For related reading, see our [file sync and sharing comparison](../self-hosted-file-sync-sharing-nextcloud-seafile-syncthing-guide/) and [web-based file manager roundup](../filebrowser-vs-filegator-vs-cloud-commander-self-hosted-web-file-managers-2026/).

## Overview of the Three Platforms

| Feature | Papermark | Filestash | Pingvin Share |
|---|---|---|---|
| **Primary Purpose** | DocSend alternative with analytics | Universal file management platform | Simple file sharing service |
| **GitHub Stars** | 8,195 | 14,109 | 4,664 |
| **Last Updated** | April 26, 2026 | April 27, 2026 | June 29, 2025 |
| **License** | AGPL v3 | AGPL v3 | BSD-2-Clause |
| **Language** | TypeScript (Next.js) | Go | TypeScript (Next.js) |
| **Database** | PostgreSQL | None (stateless config) | SQLite |
| **Analytics** | Built-in (page views, time spent) | None | None |
| **Custom Domains** | Yes | No | No |
| **Password Protection** | Yes | Via backend auth | Yes |
| **Link Expiration** | Yes | No | Yes |
| **Download Limits** | Yes | No | Yes |
| **Office Preview** | PDF-focused | Full (via Collabora) | PDF, images, video |
| **API** | Yes (REST) | Yes (REST) | Yes (REST) |
| **Docker Support** | Manual compose needed | Official docker-compose | Official docker-compose |
| **S3 Storage** | Required (AWS S3, Vercel Blob) | Via plugins | Local storage only |

### Papermark — The DocSend Alternative

[Papermark](https://github.com/mfts/papermark) is purpose-built as an open-source replacement for DocSend. It focuses on **document sharing with analytics**: track who viewed your document, how long they spent on each page, and whether they downloaded it. Custom domain support lets you brand share links under your own domain (e.g., `docs.yourcompany.com/deck`).

Papermark uses a modern Next.js frontend with a PostgreSQL database and requires S3-compatible blob storage for file uploads. It is ideal for sales teams, founders, and agencies that need to track engagement on pitch decks, proposals, and client documents.

### Filestash — The Universal Data Access Layer

[Filestash](https://github.com/mickael-kerjean/filestash) is a self-hosted file management platform that connects to virtually any storage backend: S3, SFTP, FTP, WebDAV, SMB, LDAP, and more. Think of it as a web-based file manager that sits on top of your existing infrastructure.

Filestash includes built-in document preview (PDF, images, text), code editing, video playback, and even office document editing via Collabora Online integration. It is ideal for organizations that need a unified access layer across multiple storage systems without moving or syncing data.

### Pingvin Share — The Elegant File Sharing Service

[Pingvin Share](https://github.com/stonith404/pingvin-share) is a lightweight, self-hosted file sharing platform designed as an open-source alternative to WeTransfer. It focuses on **simplicity**: upload a file, get a shareable link, and set expiration or download limits.

Pingvin Share uses SQLite for configuration and stores files locally. It features a clean, modern UI, password-protected shares, QR code generation for mobile sharing, and optional ClamAV integration for malware scanning. It is ideal for individuals and small teams that need quick, secure file sharing without complex setup.

## How to Deploy Each Platform

### Papermark — Docker Compose Deployment

Papermark does not ship an official `docker-compose.yml`, but you can self-host it with the following configuration. This setup includes Papermark (built from source), PostgreSQL, and MinIO as an S3-compatible storage backend:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: papermark
      POSTGRES_PASSWORD: papermark_secret
      POSTGRES_DB: papermark
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U papermark"]
      interval: 5s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minio_secret
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"

  papermark:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      DATABASE_URL: "postgresql://papermark:papermark_secret@postgres:5432/papermark"
      AWS_ACCESS_KEY_ID: minioadmin
      AWS_SECRET_ACCESS_KEY: minio_secret
      AWS_REGION: us-east-1
      BUCKET_NAME: papermark-uploads
      AWS_ENDPOINT_URL: http://minio:9000
      NEXTAUTH_URL: http://localhost:3000
      NEXTAUTH_SECRET: your-nextauth-secret-here
      RESEND_API_KEY: your-resend-api-key
    depends_on:
      postgres:
        condition: service_healthy
      minio:
        condition: service_started

volumes:
  pg_data:
  minio_data:
```

**Key environment variables to configure:**
- `DATABASE_URL` — PostgreSQL connection string
- `AWS_*` — S3 credentials and endpoint (MinIO or AWS S3)
- `NEXTAUTH_SECRET` — Random string for session encryption
- `RESEND_API_KEY` — Email delivery (required for user registration)

After starting the containers, initialize the database:

```bash
docker compose exec papermark npx prisma db push
docker compose exec papermark npx prisma generate
```

### Filestash — Docker Compose Deployment

Filestash ships an official Docker Compose file in its `docker/` directory. Here is a simplified version for production use:

```yaml
services:
  filestash:
    image: machines/filestash:latest
    container_name: filestash
    restart: unless-stopped
    ports:
      - "8334:8334"
    environment:
      - APPLICATION_URL=https://files.yourdomain.com
    volumes:
      - filestash_data:/app/data/state/

volumes:
  filestash_data:
```

For office document editing, Filestash can integrate with Collabora Online:

```yaml
services:
  filestash:
    image: machines/filestash:latest
    restart: unless-stopped
    ports:
      - "8334:8334"
    environment:
      - APPLICATION_URL=https://files.yourdomain.com
      - OFFICE_URL=http://collabora:9980
    volumes:
      - filestash_data:/app/data/state/

  collabora:
    image: collabora/code:24.04.10.2.1
    restart: unless-stopped
    ports:
      - "9980:9980"
    environment:
      - extra_params=--o:ssl.enable=false

volumes:
  filestash_data:
```

On first access, Filestash prompts you to configure storage backends through its web UI — no config files needed.

### Pingvin Share — Docker Compose Deployment

Pingvin Share has the simplest deployment of the three. Its official `docker-compose.yml` is a single service:

```yaml
services:
  pingvin-share:
    image: stonith404/pingvin-share
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - TRUST_PROXY=true
    volumes:
      - ./data:/opt/app/backend/data
      - ./data/images:/opt/app/frontend/public/img
```

If you run behind a reverse proxy (Nginx, Traefik, Caddy), set `TRUST_PROXY=true`. For malware scanning, add ClamAV:

```yaml
services:
  pingvin-share:
    image: stonith404/pingvin-share
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - TRUST_PROXY=true
      - CLAMAV_HOST=clamav
    volumes:
      - ./data:/opt/app/backend/data
      - ./data/images:/opt/app/frontend/public/img
    depends_on:
      - clamav

  clamav:
    image: clamav/clamav:latest
    restart: unless-stopped
```

## Detailed Feature Comparison

### Document Analytics

| Metric | Papermark | Filestash | Pingvin Share |
|---|---|---|---|
| Page view tracking | Yes | No | No |
| Time spent per page | Yes | No | No |
| Download tracking | Yes | No | No |
| Viewer location (IP) | Yes | Yes (audit log) | No |
| Unique visitor count | Yes | No | No |
| Real-time dashboard | Yes | No | No |

Papermark is the clear winner here. Its analytics dashboard shows exactly who opened your document, which pages they viewed, and how long they spent — the kind of intelligence sales teams rely on to gauge deal progress.

### Storage Backends

| Backend | Papermark | Filestash | Pingvin Share |
|---|---|---|---|
| Local filesystem | No | Yes | Yes |
| Amazon S3 | Yes | Yes (plugin) | No |
| MinIO | Yes | Yes (plugin) | No |
| Google Drive | No | Yes (plugin) | No |
| Dropbox | No | Yes (plugin) | No |
| SFTP | No | Yes (plugin) | No |
| WebDAV | No | Yes (plugin) | No |
| SMB/CIFS | No | Yes (plugin) | No |
| LDAP/AD Auth | No | Yes (plugin) | No |

Filestash dominates in storage backend diversity. It supports over 10 different backends through its plugin system, making it a true universal data access layer. Papermark is locked to S3-compatible storage, and Pingvin Share uses only local disk.

### Access Control and Security

| Feature | Papermark | Filestash | Pingvin Share |
|---|---|---|---|
| Password-protected links | Yes | Via backend auth | Yes |
| Link expiration | Yes | No | Yes |
| Download limits | Yes | No | Yes |
| Email-gated access | Yes | No | No |
| IP restriction | No | Via reverse proxy | No |
| Watermarking | Yes | No | No |
| Disable download | Yes | No | No |
| QR code for links | No | No | Yes |
| Malware scanning | No | No | Yes (ClamAV) |

Papermark offers the most granular access controls for document sharing: email-gated access, watermarking, and the ability to disable downloads entirely. Pingvin Share compensates with QR code generation and optional ClamAV scanning.

## Which Should You Choose?

**Choose Papermark if:**
- You need document analytics (who viewed, how long, which pages)
- You share pitch decks, proposals, or client-facing materials
- You want custom branded domains for share links
- You have S3 storage available and are comfortable with Next.js deployment

**Choose Filestash if:**
- You need to access files across multiple storage backends from one interface
- You want office document editing (via Collabora) in the browser
- You need a web-based file manager for SFTP, S3, SMB, or WebDAV servers
- You prefer a stateless, plugin-based architecture

**Choose Pingvin Share if:**
- You want a simple WeTransfer-like experience
- You need quick file sharing with expiration and download limits
- You prefer minimal setup (single Docker container, SQLite, no external dependencies)
- You want QR code sharing and optional malware scanning

For teams managing sensitive documents at scale, Papermark provides the most professional feature set. For IT teams managing diverse storage infrastructure, Filestash is unmatched. For individuals and small teams needing quick, secure file sharing, Pingvin Share is the easiest to deploy and use.

## FAQ

### Can Papermark be self-hosted without S3 storage?

No. Papermark requires an S3-compatible blob storage backend for file uploads. You can use AWS S3, Vercel Blob, or a self-hosted MinIO instance. The MinIO approach described above keeps all data on your own infrastructure.

### Does Filestash store files locally or just access remote backends?

Filestash is primarily a data access layer — it does not store uploaded files itself. Instead, it connects to your existing storage backends (S3, SFTP, FTP, WebDAV, SMB, etc.) and provides a unified web interface. Any file operations are performed directly on the connected backend.

### Is Pingvin Share actively maintained?

Pingvin Share's last commit was in June 2025. While the project is stable and functional for its intended use case, the lack of recent activity means new features and security patches may be delayed. For production-critical deployments, consider Papermark (updated daily) or Filestash (updated weekly) as more actively maintained alternatives.

### Can I use a reverse proxy with these tools?

Yes, all three platforms support reverse proxy deployment. For Papermark and Pingvin Share, set the appropriate trust proxy headers (`TRUST_PROXY=true` for Pingvin Share). Filestash uses the `APPLICATION_URL` environment variable to construct correct redirect URLs. See our [reverse proxy comparison guide](../nginx-proxy-manager-vs-swag-vs-caddy-docker-proxy-self-hosted-reverse-proxy-gui-guide-2026/) for proxy configuration details.

### How do these compare to Nextcloud for file sharing?

Nextcloud is a full cloud suite with file sync, calendar, contacts, and apps. Papermark, Filestash, and Pingvin Share are focused specifically on document/file sharing. If you only need to share documents externally with tracking, Papermark is lighter and more purpose-built than Nextcloud. For a complete file management platform with sharing, Nextcloud offers more features but requires more resources. See our [Nextcloud vs Seafile comparison](../self-hosted-file-sync-sharing-nextcloud-seafile-syncthing-guide/) for a deeper dive.

### What file formats does each platform support for preview?

Papermark focuses on PDF documents with page-by-page tracking. Filestash supports PDF, images, text, code, video, audio, and office documents (via Collabora Online integration). Pingvin Share supports PDF, images, video, and common file types for download, but does not offer in-browser document editing.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Papermark vs Filestash vs Pingvin Share: Best Self-Hosted Document Sharing 2026",
  "description": "Compare Papermark, Filestash, and Pingvin Share — three open-source, self-hosted document and file sharing platforms. Includes Docker Compose configs, feature comparison, and deployment guides.",
  "datePublished": "2026-04-27",
  "dateModified": "2026-04-27",
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
