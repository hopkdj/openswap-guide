---
title: "Self-Hosted Encrypted Note-Taking: Standard Notes vs Joplin vs Cryptee Alternatives (2026)"
date: "2026-05-09"
tags: ["comparison", "guide", "self-hosted", "privacy", "note-taking", "encryption"]
draft: false
description: "Compare self-hosted encrypted note-taking solutions with end-to-end encryption. Docker Compose deployments for Standard Notes, Joplin Server, and privacy-focused alternatives."
---

End-to-end encrypted note-taking ensures that only you can read your notes — not the service provider, not system administrators, and not anyone who gains access to the server's database. For privacy-conscious users, journalists, legal professionals, and anyone handling sensitive information, self-hosted encrypted notes provide the highest level of data protection.

This guide compares three leading approaches to self-hosted encrypted note-taking: **Standard Notes** (self-hosted server), **Joplin** with self-hosted sync server, and **Cryptee** alternatives. We cover deployment, encryption models, feature comparison, and security considerations.

## Platform Overview

| Feature | Standard Notes | Joplin Server | Cryptee (Self-Hosted) |
|---------|---------------|---------------|----------------------|
| Encryption Model | End-to-end (client-side) | TLS + optional E2EE | End-to-end (client-side) |
| Language | TypeScript / Node.js | Node.js / PostgreSQL | JavaScript / Node.js |
| Self-Hosted Server | Yes (official) | Yes (official) | Limited (source available) |
| Docker Support | Official image | Official image | Community Docker |
| Sync Protocol | Proprietary | Joplin Data API | Proprietary |
| File Attachments | Yes (paid extension) | Yes (built-in) | Yes |
| Markdown Support | Yes | Yes | Yes |
| Mobile Apps | iOS, Android | iOS, Android, Desktop | Web-only |
| Open Source | Core is MIT | Fully Apache 2.0 | Source available |
| Best For | Privacy-first notes | Open-source sync | Privacy photos + notes |

**Standard Notes** pioneered encrypted note-taking with a strong focus on privacy. The self-hosted server component handles encrypted data storage, while the client applications perform all encryption and decryption locally.

**Joplin** is a fully open-source note-taking application with a self-hosted sync server. While the default sync uses TLS encryption, Joplin also supports end-to-end encryption for notes synchronized to any backend, including the self-hosted server.

**Cryptee** is a privacy-focused platform for notes, photos, and files with client-side encryption. While Cryptee's primary offering is a hosted service, the source is available for self-hosting with some limitations.

## Installation with Docker Compose

### Standard Notes (Self-Hosted Server)

Standard Notes provides an official Docker image for the server component:

```yaml
version: '3.8'

services:
  sn-db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: standard_notes
      POSTGRES_USER: sn_user
      POSTGRES_PASSWORD: sn_secure_password
    volumes:
      - sn_db:/var/lib/postgresql/data
    restart: unless-stopped

  sn-redis:
    image: redis:7-alpine
    restart: unless-stopped

  sn-server:
    image: standardnotes/server:latest
    ports:
      - "3100:3000"
    environment:
      DATABASE_URL: postgresql://sn_user:sn_secure_password@sn-db:5432/standard_notes
      REDIS_URL: redis://sn-redis:6379
      SECRET_KEY_BASE: your-64-character-secret-key-base-here-change-this
      AUTH_JWT_SECRET: your-jwt-secret-key-change-this
      SUBSCRIPTIONS_ENABLED: "false"
    depends_on:
      - sn-db
      - sn-redis
    restart: unless-stopped

volumes:
  sn_db:
```

After starting with `docker compose up -d`, configure your Standard Notes client to point to `http://localhost:3100` as the sync server. All note content is encrypted client-side before being sent to the server.

### Joplin Server

Joplin's self-hosted server is straightforward to deploy:

```yaml
version: '3.8'

services:
  joplin-db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: joplin
      POSTGRES_USER: joplin
      POSTGRES_PASSWORD: joplin_password
    volumes:
      - joplin_db:/var/lib/postgresql/data
    restart: unless-stopped

  joplin-app:
    image: joplin/server:latest
    ports:
      - "22300:22300"
    environment:
      APP_PORT: 22300
      APP_BASE_URL: http://localhost:22300
      DB_CLIENT: pg
      POSTGRES_DATABASE: joplin
      POSTGRES_USER: joplin
      POSTGRES_PASSWORD: joplin_password
      POSTGRES_HOST: joplin-db
    depends_on:
      - joplin-db
    restart: unless-stopped

volumes:
  joplin_db:
```

Start with `docker compose up -d`. The admin panel is available at `http://localhost:22300` with default credentials `admin@localhost` / `admin`. In the Joplin desktop or mobile client, configure synchronization to use "Joplin Server" with your server URL.

### Enabling End-to-End Encryption in Joplin

Joplin's self-hosted server stores data encrypted in transit (TLS) but not at rest by default. To enable end-to-end encryption:

1. Open Joplin desktop client → **Tools** → **Options** → **Encryption**
2. Click **Enable encryption** and set a master password
3. All notes are encrypted locally before syncing to the server
4. The server only stores encrypted blobs — it cannot read your notes

This encryption applies regardless of the sync backend (self-hosted server, Dropbox, S3, etc.), making Joplin flexible for hybrid deployments.

## Encryption Model Comparison

### Standard Notes: Zero-Knowledge Architecture

Standard Notes uses a zero-knowledge encryption model. The encryption key is derived from your password using a key derivation function (PBKDF2 or Argon2). The server never sees your password or encryption key — only an encrypted authentication token. All note content, tags, and metadata are encrypted before leaving your device.

```
Client Device                          Server
┌──────────────┐     Encrypted     ┌──────────────┐
│  Plaintext   │ ────────────────► │  Ciphertext   │
│  + Key Deriv │                   │  (stored)     │
└──────────────┘                   └──────────────┘
```

### Joplin: Optional End-to-End Encryption

Joplin's default mode encrypts data in transit via TLS and stores plaintext on the server. When E2EE is enabled, notes are encrypted with AES-256-GCM using a master password. The sync server (self-hosted or cloud) only stores encrypted data. However, notebook structure, tags, and some metadata may remain visible to the server depending on configuration.

### Cryptee: Client-Side Encryption with Zero-Knowledge Photos

Cryptee extends encryption beyond notes to include photos, documents, and file storage. The entire platform is built on a zero-knowledge model where encryption keys never leave the client browser. Self-hosting Cryptee is possible but requires more setup than Standard Notes or Joplin.

## Feature Comparison

### Editing Experience

Standard Notes offers a clean, minimal editor with support for Markdown, rich text, and code editing through extensions. Joplin provides a more traditional note-taking experience with notebook organization, tag support, and a built-in Markdown editor with live preview. Cryptee focuses on a minimalist writing experience with support for text, photos, and files in a unified interface.

### Search Capabilities

Search is the primary trade-off with client-side encryption. Since the server cannot read your notes, full-text search must happen on the client device. Standard Notes indexes encrypted content locally. Joplin downloads and decrypts notes for search. Both approaches work well for moderate note collections but may slow down with thousands of notes.

### Sharing and Collaboration

Standard Notes supports sharing encrypted notes through public links (with decryption handled client-side). Joplin does not natively support note sharing from the self-hosted server — notes are synced to individual clients. Cryptee allows sharing of individual notes and photos through encrypted links.

## Self-Hosting Considerations

### Backup Strategy

For encrypted note servers, your backup strategy must account for the encryption model:

- **Database backups**: Regularly back up the PostgreSQL database using `pg_dump`. Store backups encrypted with the same key derivation parameters.
- **File attachments**: Back up attachment directories separately. For Joplin, the resource directory contains encrypted blobs.
- **Encryption keys**: Back up your master password and any recovery keys. Without them, encrypted data is permanently unrecoverable.
- **Version control**: Consider running backup restoration tests quarterly to ensure your recovery process works.

### High Availability

For production deployments, consider:

- Running multiple application server instances behind a load balancer
- Using PostgreSQL streaming replication for database redundancy
- Deploying Redis in clustered mode for Standard Notes session management
- Implementing regular health checks on the sync endpoints

For organizations already running self-hosted infrastructure, integrating a note server with existing [authentication systems](../authentik-vs-keycloak-vs-authelia/) simplifies access management.

## Security Best Practices

1. **Use strong master passwords** — The encryption strength depends entirely on your password. Use a passphrase of 20+ characters or a randomly generated password stored in a password manager.
2. **Enable two-factor authentication** — Both Standard Notes and Joplin Server support 2FA for the admin panel.
3. **Keep clients updated** — Encryption implementations evolve. Always use the latest client versions to benefit from security improvements.
4. **Audit server access** — Monitor server logs for unusual access patterns. Even with encrypted data, metadata (access times, request sizes) can reveal information.
5. **Use HTTPS exclusively** — Never expose your self-hosted note server over plain HTTP. Use a reverse proxy with TLS termination.

For additional guidance on securing self-hosted services, see our [comprehensive guide on self-hosted authentication](../authentik-vs-keycloak-vs-authelia/) and [WAF deployment patterns](../2026-04-18-bunkerweb-vs-modsecurity-vs-crowdsec-self-hosted-waf-guide-2026/).

## Why Self-Host Encrypted Notes?

Self-hosting encrypted note-taking combines the privacy benefits of client-side encryption with the control of owning your infrastructure:

**Complete Data Sovereignty**: Your encrypted notes reside on hardware you control. No third-party company can access, analyze, or monetize your data. This is essential for legal professionals handling attorney-client privileged information, journalists protecting source communications, and healthcare workers managing patient notes.

**No Subscription Lock-In**: Hosted encrypted note services typically charge monthly subscriptions. Self-hosting eliminates recurring costs — you only pay for the server hardware or VPS. The open-source server components have no licensing fees.

**Customization and Integration**: Self-hosted note servers can integrate with your existing infrastructure — internal authentication providers, backup systems, monitoring dashboards, and custom extensions. You control the feature roadmap, not a vendor.

**Offline Access and Reliability**: Self-hosted sync servers work on your own network, providing fast sync speeds and offline availability when your internet connection is unstable. This is particularly valuable for field workers and remote teams.

**Auditability**: With access to the server source code and database schema, you can independently verify the encryption implementation and data handling practices. This transparency is impossible with closed-source hosted services.

## FAQ

### Is Standard Notes free to self-host?

The Standard Notes server is open source and free to self-host. However, some client features (extensions, themes, file attachments) require a paid subscription even with a self-hosted server. The core note-taking functionality — creating, editing, and syncing encrypted notes — works without a subscription.

### Can I migrate notes from Evernote or OneNote to Joplin?

Yes. Joplin provides import tools for ENEX files (Evernote export format), Markdown files, and raw text. The import process preserves note content, tags, and notebook structure. After importing, you can enable end-to-end encryption to protect all imported notes.

### What happens if I forget my Joplin encryption master password?

Your encrypted notes are permanently unrecoverable. Joplin uses AES-256-GCM encryption with a key derived from your master password — there is no backdoor or recovery mechanism. This is by design for a zero-knowledge system. Always back up your master password securely.

### Does Standard Notes support file attachments when self-hosted?

File attachments require the paid File Attachments extension, regardless of whether you use the hosted or self-hosted server. The self-hosted server provides the sync infrastructure, but premium features are licensed separately through the Standard Notes subscription.

### Can multiple users share a self-hosted Joplin server?

Yes. Joplin Server supports multi-user deployments with separate accounts and isolated note collections. Each user has their own authentication credentials and encrypted note storage. Admin-level access is required to manage user accounts.

### How do I back up my self-hosted note server?

For both Standard Notes and Joplin, back up the PostgreSQL database with `pg_dump` and any file attachment directories. For encrypted notes, also ensure you have secure backups of your master password or encryption key. Test your restore procedure regularly to verify backup integrity.

### Can I use my self-hosted server with the mobile apps?

Yes. Both Standard Notes and Joplin mobile apps support custom sync server URLs. In Standard Notes, go to Account → Change Server to point to your self-hosted instance. In Joplin, configure the sync target to "Joplin Server" and enter your server URL and credentials.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Encrypted Note-Taking: Standard Notes vs Joplin vs Cryptee Alternatives (2026)",
  "description": "Compare self-hosted encrypted note-taking solutions with end-to-end encryption. Docker Compose deployments for Standard Notes, Joplin Server, and privacy-focused alternatives.",
  "datePublished": "2026-05-09",
  "dateModified": "2026-05-09",
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
