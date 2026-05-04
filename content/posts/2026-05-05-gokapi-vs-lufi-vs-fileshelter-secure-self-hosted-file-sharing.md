---
title: "GoKAPI vs Lufi vs FileShelter: Secure Self-Hosted File Sharing 2026"
date: 2026-05-05
tags: ["comparison", "guide", "self-hosted", "file-sharing", "privacy", "security"]
draft: false
description: "Compare GoKAPI, Lufi, and FileShelter for secure one-time file sharing. Docker Compose deployment guides for privacy-focused file transfer alternatives to WeTransfer."
---

Sending large files securely is a common challenge. Commercial services like WeTransfer, Dropbox links, or Google Drive shared folders work, but they give the hosting provider access to your files and metadata. For sensitive documents, confidential project assets, or any data you would rather not entrust to a third party, a self-hosted file sharing service is the answer.

This guide compares three purpose-built self-hosted file sharing platforms: **GoKAPI**, a lightweight Firefox Send alternative with S3 support; **Lufi**, a privacy-focused encrypted file sharing service; and **FileShelter**, a minimal one-time file upload tool. Each addresses the same problem with different security models and feature sets.

## Why Self-Host File Sharing?

Commercial file transfer services log IP addresses, scan files for content, retain metadata, and may comply with data requests from authorities. For organizations handling sensitive documents — legal contracts, financial records, medical data, or proprietary code — these practices are unacceptable.

A self-hosted file sharing service eliminates third-party exposure. Files never leave your infrastructure, download links expire automatically, and no persistent storage of access logs is required. You control the retention policy, access restrictions, and encryption settings.

Self-hosted file sharing also avoids the size limits and bandwidth throttling of free commercial tiers. A modest VPS with 100 GB of storage can serve thousands of file transfers per month with no per-transfer fees or upload caps.

## GoKAPI

GoKAPI is a lightweight, self-hosted file sharing service written in Go. It is designed as a Firefox Send replacement, offering one-time or time-limited file downloads with no public upload capability — only authenticated users can share files.

**Key Features:**
- One-time downloads (file deleted after first download)
- Time-based expiration (delete after N hours/days)
- Password-protected downloads
- AWS S3 backend support for scalable storage
- No public upload — only authenticated users can share
- Clean, responsive web interface
- REST API for programmatic file uploads
- QR code generation for download links

GoKAPI is ideal for teams that need a private, controlled file sharing service. The authentication requirement prevents abuse, while the S3 backend support means you can store files on cheap object storage without filling your application server disk.

### Docker Compose Setup

```yaml
version: "3.8"
services:
  gokapi:
    image: docker.io/forceu/gokapi:latest
    container_name: gokapi
    restart: unless-stopped
    ports:
      - "53842:53842"
    volumes:
      - gokapi-data:/app/data
      - gokapi-files:/app/files
    environment:
      - GOKAPI_ADMIN_USER=admin
      - GOKAPI_ADMIN_PASSWORD=changeme

volumes:
  gokapi-data:
  gokapi-files:
```

For S3 backend configuration, edit the config file in the data volume and set the S3 bucket credentials. GoKAPI will automatically route file storage to S3 while keeping the web interface and database local.

## Lufi

Lufi (Let's Upload Files, Idiot) is a privacy-focused file sharing application written in Perl with Mojolicious. Its defining feature is client-side encryption: files are encrypted in the browser before upload, so the server never sees the plaintext content.

**Key Features:**
- Client-side AES-256 encryption (server never sees plaintext)
- One-time or limited downloads
- Time-based expiration
- No user accounts needed
- Password-protected downloads
- Minimal server storage footprint
- Can be deployed as a single Perl application
- Federation support (share between Lufi instances)

Lufi is the most privacy-focused option in this comparison. Because encryption happens in the browser, even a compromised server cannot access file contents. The download link contains the decryption key as a URL fragment, which is never sent to the server.

### Docker Compose Setup

```yaml
version: "3.8"
services:
  lufi:
    image: docker.io/fiatlufi/lufi:latest
    container_name: lufi
    restart: unless-stopped
    ports:
      - "8080:80"
    volumes:
      - lufi-data:/var/lib/lufi
    environment:
      - LUFI_SECRET=$(openssl rand -hex 64)
      - LUFI_MAX_FILE_SIZE=10737418240

volumes:
  lufi-data:
```

Generate a secret key for the first run and store it permanently — losing it invalidates all existing upload links.

## FileShelter

FileShelter is a minimal file sharing service written in C++. It is designed for simplicity: upload a file, get a link, and the file is automatically deleted after a configurable number of downloads or time period.

**Key Features:**
- Ultra-lightweight C++ implementation (~5 MB binary)
- One-time or limited downloads
- Time-based expiration (configurable max age)
- File size limits per upload
- Minimal resource usage
- No database required — file metadata stored on disk
- Simple web interface
- No user authentication (suitable for trusted networks)

FileShelter is the lightest option by far. Its tiny binary size and lack of database dependencies make it ideal for resource-constrained environments like Raspberry Pi or small VPS instances. The tradeoff is that it lacks advanced features like S3 backends or client-side encryption.

### Docker Compose Setup

```yaml
version: "3.8"
services:
  fileshelter:
    image: docker.io/epoupon/fileshelter:latest
    container_name: fileshelter
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - fileshelter-data:/var/lib/fileshelter
    environment:
      - FSL_SHELTER_DURATION=24
      - FSL_MAX_UPLOAD_SIZE=1073741824

volumes:
  fileshelter-data:
```

## Feature Comparison

| Feature | GoKAPI | Lufi | FileShelter |
|---------|--------|------|-------------|
| Language | Go | Perl (Mojolicious) | C++ |
| Encryption | Server-side | Client-side AES-256 | None |
| One-time download | Yes | Yes | Yes |
| Time expiration | Yes | Yes | Yes |
| Password protection | Yes | Yes | No |
| S3 backend | Yes | No | No |
| Auth required | Yes (upload) | No | No |
| Database | SQLite | SQLite | None (disk) |
| File size limit | Configurable | Configurable | Configurable |
| Federation | No | Yes | No |
| Binary size | ~15 MB | ~50 MB | ~5 MB |
| RAM usage | ~20 MB | ~80 MB | ~5 MB |
| Docker image | Official | Community | Official |

## Which Should You Choose?

**Choose GoKAPI** if you need authenticated, controlled file sharing with S3 backend support. It is ideal for teams that want to track who uploads files and integrate with cloud storage for large-scale deployments.

**Choose Lufi** if privacy is your top priority. Client-side encryption means the server never sees your file contents, making it the best choice for highly sensitive documents.

**Choose FileShelter** if you need a lightweight, no-frills file sharing service for a trusted network. Its minimal resource footprint makes it perfect for small servers or edge devices.

For peer-to-peer file sharing without a server, see our [browser-based file sharing guide](../pairdrop-vs-snapdrop-vs-filepizza-self-hosted-browser-file-sharing/). For network file sharing protocols like SMB and WebDAV, check our [file sharing protocols comparison](../2026-04-24-samba-vs-nfs-vs-webdav-self-hosted-file-sharing-guide-2026/).

## FAQ

### How does client-side encryption in Lufi work?

Lufi encrypts files in the browser using AES-256 before uploading them to the server. The encryption key is included in the download URL as a hash fragment (after the `#` symbol), which browsers never send to the server. This means the server stores only encrypted ciphertext and cannot decrypt the files.

### Can I set files to auto-delete after a certain time?

Yes. All three tools support time-based expiration. GoKAPI allows setting expiration in hours or days per upload. Lufi supports configurable maximum file age. FileShelter uses the `FSL_SHELTER_DURATION` environment variable to set the maximum file lifetime.

### Is GoKAPI suitable for public file sharing?

No. GoKAPI requires authentication to upload files, which prevents abuse and spam. It is designed for teams and organizations where only trusted users can share files. If you need public uploads, consider Lufi or FileShelter instead.

### How large a file can I share?

File size limits are configurable in all three tools. GoKAPI and Lufi can handle files up to your storage capacity (S3 for GoKAPI, local for Lufi). FileShelter limits are set by the `FSL_MAX_UPLOAD_SIZE` environment variable. For very large files (10+ GB), GoKAPI with S3 backend is the most scalable option.

### Can I integrate these tools into my existing workflow via API?

GoKAPI provides a REST API for uploading files programmatically, making it suitable for CI/CD pipelines and automated workflows. Lufi and FileShelter are designed for manual web-based uploads and do not have official APIs.

### What happens if I lose the Lufi secret key?

The Lufi secret key is used to sign upload tokens. If you lose it, all existing upload links become invalid, but the encrypted files remain on disk. You can generate a new secret key, but you will need to re-upload any files you want to share again.

### Do these tools support mobile access?

All three provide responsive web interfaces that work on mobile browsers. None offer dedicated mobile apps, but the web interface is sufficient for uploading and downloading files from smartphones and tablets.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "GoKAPI vs Lufi vs FileShelter: Secure Self-Hosted File Sharing 2026",
  "description": "Compare GoKAPI, Lufi, and FileShelter for secure one-time file sharing. Docker Compose deployment guides for privacy-focused file transfer alternatives to WeTransfer.",
  "datePublished": "2026-05-05",
  "dateModified": "2026-05-05",
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
