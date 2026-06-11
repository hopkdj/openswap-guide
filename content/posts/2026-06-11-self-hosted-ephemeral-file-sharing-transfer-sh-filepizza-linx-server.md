---
title: "Self-Hosted Ephemeral File Sharing: transfer.sh vs FilePizza vs Linx Server"
date: "2026-06-11"
tags: ["file-sharing", "self-hosted", "privacy", "docker", "web-tools", "file-transfer", "collaboration"]
draft: false
---

## Introduction

Sending files securely has become a basic need for teams, developers, and privacy-conscious users. While cloud services like WeTransfer and Google Drive dominate, they come with data ownership concerns, file size limits, and privacy compromises. Self-hosted ephemeral file sharing tools offer a compelling alternative: you control the data, set your own retention policies, and keep files on your own infrastructure.

In this guide, we compare three leading open-source ephemeral file sharing platforms — **transfer.sh**, **FilePizza**, and **Linx Server** — each representing a fundamentally different approach to temporary file exchange.

## Comparison Table

| Feature | transfer.sh | FilePizza | Linx Server |
|---------|-------------|-----------|-------------|
| **Transfer Method** | HTTP upload/download | WebRTC peer-to-peer | HTTP upload with share links |
| **File Storage** | Server-side (temp) | Browser-to-browser (no server storage) | Server-side (configurable expiry) |
| **Max File Size** | 10GB (configurable) | Limited by browser memory | Configurable (default 4GB) |
| **Encryption** | TLS in transit | End-to-end (WebRTC DTLS) | TLS in transit |
| **CLI Support** | Native (`curl` upload) | Browser-only | API + Web UI |
| **Docker Support** | Official image available | Community Dockerfile | Official Docker image |
| **Expiry Control** | Configurable max days | Immediate (session-based) | Per-file expiry settings |
| **Authentication** | None (public by design) | None (P2P) | Optional API keys |
| **GitHub Stars** | 15,800+ | 10,000+ | 1,500+ |
| **Language** | Go | JavaScript/Node.js | Go |

## transfer.sh: The CLI-First Classic

[transfer.sh](https://github.com/dutchcoders/transfer.sh) is one of the most popular self-hosted file sharing tools, with over 15,800 GitHub stars. Written in Go, it's designed for simplicity and speed — upload a file via `curl` and get back a shareable URL that automatically expires.

### Key Features

- **Zero-dependency binary**: Single Go binary, no external database needed
- **Native CLI workflow**: Upload with `curl --upload-file ./myfile.txt https://transfer.example.com/myfile.txt`
- **Encryption support**: Files can be encrypted before upload with `gpg` and decrypted on download
- **Configurable retention**: Set maximum file age in days (default 14 days)
- **S3-compatible storage**: Back files to S3, Google Cloud Storage, or local filesystem
- **Virus scanning**: Optional ClamAV integration for uploaded files

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  transfer-sh:
    image: dutchcoders/transfer.sh:latest
    container_name: transfer-sh
    ports:
      - "8080:8080"
    environment:
      - LISTENER=:8080
      - MAX-UPLOAD-SIZE=10737418240
      - PURGE-DAYS=7
      - PROVIDER=local
      - BASEDIR=/data
    volumes:
      - ./data:/data
    restart: unless-stopped
```

```bash
# Upload a file via CLI
curl --upload-file report.pdf https://files.yourdomain.com/report.pdf

# Upload with a password (optional encryption)
cat secret.txt | gpg -c --passphrase yourpassword |   curl --upload-file "-" https://files.yourdomain.com/secret.txt.gpg
```

## FilePizza: Peer-to-Peer Browser Transfers

[FilePizza](https://github.com/kern/filepizza) takes a fundamentally different approach — it uses **WebRTC** to establish a direct peer-to-peer connection between the sender's and receiver's browsers. The server only facilitates the initial handshake; files never touch the server's disk.

### Key Features

- **True P2P transfer**: Files stream directly between browsers via WebRTC data channels
- **Zero server storage**: The server acts only as a signaling relay — no files stored at rest
- **No file size limits**: Limited only by available browser memory and connection speed
- **End-to-end encryption**: WebRTC uses DTLS-SRTP encryption by default
- **Torrent-style seeding**: The sender "seeds" the file; multiple recipients can download simultaneously
- **No upload step**: The sender selects a file locally and generates a "room" link for recipients

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  filepizza:
    image: kern/filepizza:latest
    container_name: filepizza
    ports:
      - "3000:3000"
    environment:
      - PORT=3000
      - NODE_ENV=production
      - STUN_URL=stun:stun.l.google.com:19302
      - TURN_URL=turn:your-turn-server:3478
      - TURN_USERNAME=youruser
      - TURN_CREDENTIAL=yourpass
    restart: unless-stopped
```

**Important**: FilePizza requires STUN/TURN servers for NAT traversal. You can use free public STUN servers (like Google's) but should deploy your own TURN server (like [coturn](https://github.com/coturn/coturn)) for reliable connectivity behind restrictive firewalls.

### How It Works

1. Sender opens FilePizza and selects a file
2. A unique "room" link is generated (e.g., `https://pizza.yourdomain.com/#abc123`)
3. Recipient opens the link — browsers establish a direct WebRTC connection
4. File transfers directly, never touching the server

## Linx Server: Clean Self-Hosted File & Media Sharing

[Linx Server](https://github.com/andreimarcu/linx-server) is a lightweight, privacy-focused file sharing server written in Go. It combines clean URL generation with flexible expiry, optional access keys, and built-in media previews.

### Key Features

- **Clean, short URLs**: Files get random or custom slugs — no tracking parameters
- **Configurable expiry**: Set per-file expiration from minutes to never
- **Optional access keys**: Restrict uploads to users with an API key
- **Built-in media previews**: Images and videos get inline preview pages
- **Syntax highlighting**: Code and text snippets are rendered with syntax highlighting
- **S3 backend support**: Store files on S3-compatible storage
- **No JavaScript required**: Clean HTML interface works without JS
- **File metadata**: Shows size, type, expiry info on download pages

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  linx-server:
    image: andreimarcu/linx-server:latest
    container_name: linx-server
    ports:
      - "8080:8080"
    environment:
      - LINX_SITE_NAME=My File Drop
      - LINX_SITE_URL=https://drop.yourdomain.com
      - LINX_MAX_SIZE=4294967296
      - LINX_MAX_EXPIRY=604800
      - LINX_BASENAME=drop
      - LINX_NO_DELETE=false
      - LINX_ALLOW_DELETION=true
      - LINX_REAL_IP=true
    volumes:
      - ./files:/data/files
      - ./meta:/data/meta
    restart: unless-stopped
```

```bash
# Upload with custom expiry (1 hour = 3600 seconds)
curl -F "file=@document.pdf" -F "expiry=3600" https://drop.yourdomain.com/upload

# Upload with access key
curl -H "Linx-Api-Key: your-key" -F "file=@data.csv" https://drop.yourdomain.com/upload
```

## Deployment Architecture: Behind a Reverse Proxy

For production deployments, serve all three tools behind a reverse proxy with TLS termination. Here's a production-ready Caddy configuration:

```caddy
files.yourdomain.com {
    reverse_proxy transfer-sh:8080
    encode gzip
}

pizza.yourdomain.com {
    reverse_proxy filepizza:3000
    header WebSocket
}

drop.yourdomain.com {
    reverse_proxy linx-server:8080
    encode gzip
    header X-Real-IP {remote_host}
    header X-Forwarded-For {remote_host}
}
```

## Why Self-Host Your File Sharing?

When you use commercial file sharing services, you're trusting a third party with potentially sensitive documents, proprietary code, or personal data. Many free services monetize through data collection, and some retain files indefinitely on their infrastructure.

Self-hosting gives you complete control over data residency — your files stay on servers you own or rent, in jurisdictions you choose. For businesses handling client data, this addresses compliance requirements under GDPR, HIPAA, or local data protection laws.

The tools compared here are particularly valuable for development teams: transfer.sh integrates seamlessly into CI/CD pipelines for sharing build artifacts; FilePizza enables instant large-file transfers during remote pairing sessions without cluttering shared storage; and Linx Server provides a polished, permanent-ish file drop for ongoing team collaboration.

For organizations already running [self-hosted file synchronization tools](../2026-04-26-rsync-vs-rclone-vs-lsyncd-self-hosted-file-sync-tools-guide-2026/), ephemeral sharing tools fill a different need — one-time transfers where you want files to automatically disappear after a set period. Similarly, if you need [resumable uploads for large files](../2026-05-02-self-hosted-resumable-file-upload-servers-tusd-tus-node-server-tusdotnet-guide/), you might combine TUS protocol servers with one of these sharing frontends.

For teams requiring encrypted secret sharing specifically (passwords, tokens, API keys), our [guide to self-hosted password sharing tools](../2026-05-03-passwordpusher-vs-privatebin-vs-bitwarden-send-self-hosted-password-sharing-guide/) covers the specialized solutions in that space.

## Choosing the Right Tool

**Choose transfer.sh if:**
- You need CLI-first workflows and scripting integration
- You want a battle-tested, minimal-dependency solution
- Your team primarily shares via terminal/curl
- You need S3-compatible storage backend

**Choose FilePizza if:**
- Privacy is paramount — you don't want files on any server disk
- You frequently share very large files (GBs to 10s of GBs)
- Both sender and receiver have modern browsers
- You can deploy a TURN server for NAT traversal

**Choose Linx Server if:**
- You want the cleanest, most polished web interface
- Built-in media previews and syntax highlighting matter
- You need per-file expiry control and optional authentication
- Your team prefers web uploads over CLI

For maximum flexibility, many organizations run **transfer.sh for developer/CLI use** and **Linx Server for web-based team sharing**. FilePizza complements both for privacy-sensitive P2P transfers.

## FAQ

### Are my files encrypted on the server?

transfer.sh and Linx Server store files in plaintext on the server's filesystem unless you encrypt before upload. FilePizza uses end-to-end WebRTC encryption by default and never stores files on the server. For maximum security, use client-side GPG encryption before uploading to any server-side storage tool.

### What happens to expired files?

All three tools support automatic file expiry. transfer.sh runs a periodic purge process that deletes files older than the configured maximum age. Linx Server checks file expiry on access and can be configured to actively clean up. FilePizza files exist only during the active WebRTC session and disappear when the browser tab closes.

### Can I implement access controls?

transfer.sh is intentionally public — anyone with the URL can download. Linx Server supports optional API keys for upload authentication and can be placed behind HTTP basic auth. FilePizza requires the unique room link to join a transfer. For stronger access control, place any of these tools behind an authenticating reverse proxy like [OAuth2 Proxy](https://oauth2-proxy.github.io/oauth2-proxy/).

### Which tool handles the largest files?

FilePizza handles the largest files in theory — since data never touches the server, the only limit is browser memory and network speed. However, WebRTC can struggle with files over 2-4GB in practice. transfer.sh defaults to 10GB but can be configured higher if your storage backend supports it. Linx Server defaults to 4GB.

### Can I use these tools in CI/CD pipelines?

transfer.sh is purpose-built for pipeline integration — it works with a single `curl` command and can be scripted into any CI system. Linx Server has a REST API but requires multipart form uploads. FilePizza is browser-only and unsuitable for automated pipelines.

### Do these tools support custom branding?

Linx Server supports custom site names and branding via environment variables. transfer.sh can be customized by forking and modifying the HTML templates. FilePizza uses React and supports theming with environment variables.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Ephemeral File Sharing: transfer.sh vs FilePizza vs Linx Server",
  "description": "Compare transfer.sh, FilePizza, and Linx Server for self-hosted ephemeral file sharing. Covers Docker deployment, CLI workflows, P2P WebRTC transfers, and security features.",
  "datePublished": "2026-06-11",
  "dateModified": "2026-06-11",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
