---
title: "PasswordPusher vs PrivateBin vs Bitwarden Send: Best Self-Hosted Password Sharing 2026"
date: 2026-05-03
tags: ["self-hosted", "security", "passwords", "sharing", "privacy", "docker"]
draft: false
---

Sharing passwords, API keys, and other sensitive credentials over email or chat is a security risk that most teams still practice daily. Self-hosted password sharing tools solve this problem by letting you send time-limited, view-limited links that self-destruct after reading — with zero trace on any third-party server.

In this guide, we compare three leading open-source solutions for self-hosted secret sharing: **PasswordPusher** (pwpush), **PrivateBin**, and **Bitwarden Send**. Each takes a different approach to secure credential sharing, and the right choice depends on whether you need simplicity, encryption strength, or ecosystem integration.

## What Is Self-Hosted Password Sharing?

Self-hosted password sharing tools let you create a link containing sensitive information (passwords, API tokens, SSH keys, configuration snippets) that:

- **Expires after a set number of views** (usually 1)
- **Expires after a time limit** (1 hour to 30 days)
- **Self-destructs** — the data is permanently deleted from the server
- **Never passes through a third party** — you control the server

This is fundamentally different from email (permanent, logged, forwardable) or password managers (require the recipient to have the same tool installed). The "one-time link" model is ideal for onboarding new team members, sharing database credentials with contractors, or sending API keys to external partners.

## Comparison at a Glance

| Feature | PasswordPusher | PrivateBin | Bitwarden Send |
|---------|---------------|------------|----------------|
| **GitHub Stars** | 2,986 | 3,100+ | 12,000+ (Vaultwarden) |
| **Language** | Ruby | PHP | Rust (Vaultwarden) |
| **Encryption** | Server-side AES | Client-side zero-knowledge | Client-side zero-knowledge |
| **View Limits** | Yes (1–100) | Yes (1 burn) | Yes (1–unlimited) |
| **Time Expiry** | 5 min – 30 days | 1 min – 1 month | 1 hour – 30 days |
| **Audit Logs** | Full audit trail | None | Basic (Vaultwarden) |
| **File Attachments** | Yes (Pro) | Yes (optional) | Yes (up to 500MB) |
| **Docker Support** | Official compose | Official image | Community (Vaultwarden) |
| **Database** | SQLite/PostgreSQL/MySQL | File-based | SQLite/MySQL/PostgreSQL |
| **API** | REST API | None | REST API |
| **Branding** | Customizable | Minimal | Bitwarden branded |
| **Best For** | Teams needing audit trails | Maximum privacy | Bitwarden ecosystem users |

## PasswordPusher (pwpush)

[PasswordPusher](https://github.com/pglombardo/PasswordPusher) is a Rails application purpose-built for sharing passwords and sensitive text with automatic expiration. It's the most feature-complete option for teams that need audit trails, delivery tracking, and a polished web interface.

**Key features:**

- **Full audit logging** — track who created each push, when it was accessed, and from which IP address
- **Configurable expiration** — set limits by view count (1–100) or time (5 minutes to 30 days)
- **Payload previews** — show the first few characters before revealing the full secret
- **Retrieval step** — require an additional click to reveal the secret (prevents accidental opens)
- **REST API** — integrate with CI/CD pipelines, onboarding scripts, or chat bots
- **Multi-language UI** — 30+ translations built in
- **File attachments** — share configuration files alongside credentials (premium feature)

### Docker Compose Setup

PasswordPusher ships with an official `docker-compose.yml` that includes automatic TLS via Let's Encrypt:

```yaml
version: "3"
services:
  pwpush:
    image: pglombardo/pwpush:latest
    container_name: pwpush
    restart: unless-stopped
    ports:
      - "5100:5100"
    environment:
      DATABASE_URL: "sqlite3:/app/storage/database/production.sqlite3"
      PWPUSH_MASTER_KEY: "your-32-character-random-master-key-here"
      TLS_DOMAIN: "pwpush.example.com"
    volumes:
      - pwpush-data:/app/storage

volumes:
  pwpush-data:
```

Generate a master key with `openssl rand -hex 32` and set `TLS_DOMAIN` to your domain. The container automatically provisions HTTPS certificates.

### Advanced Configuration with PostgreSQL

For production deployments with many users, PostgreSQL provides better concurrency:

```yaml
version: "3"
services:
  pwpush:
    image: pglombardo/pwpush:latest
    container_name: pwpush
    restart: unless-stopped
    ports:
      - "5100:5100"
    environment:
      DATABASE_URL: "postgresql://pwpush:secret@db:5432/pwpush_production"
      PWPUSH_MASTER_KEY: "your-master-key-here"
    depends_on:
      - db
    volumes:
      - pwpush-data:/app/storage

  db:
    image: postgres:16-alpine
    container_name: pwpush-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: pwpush
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: pwpush_production
    volumes:
      - postgres-data:/var/lib/postgresql/data

volumes:
  pwpush-data:
  postgres-data:
```

## PrivateBin

[PrivateBin](https://github.com/PrivateBin/PrivateBin) takes a fundamentally different approach: **client-side zero-knowledge encryption**. The server never sees your data in plaintext — encryption and decryption happen entirely in the browser. This means even if the server is compromised, the attacker only gets encrypted blobs.

**Key features:**

- **Zero-knowledge encryption** — data is encrypted in the browser using AES-256-GCM before being sent to the server
- **Burn-after-reading** — secrets are permanently deleted after one view
- **Discussion threads** — optional encrypted comment threads attached to each paste
- **Password protection** — require a password to decrypt the paste (double encryption)
- **File attachments** — upload files alongside text (optional, configurable)
- **Syntax highlighting** — 150+ programming languages supported
- **Simple deployment** — single PHP application, runs on any LAMP/LEMP stack

### Docker Compose Setup

PrivateBin runs from a single Docker image with a volume for data storage:

```yaml
version: "3"
services:
  privatebin:
    image: privatebin/nginx-fpm-alpine:latest
    container_name: privatebin
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - privatebin-data:/srv/data
      - privatebin-cfg:/srv/cfg

volumes:
  privatebin-data:
  privatebin-cfg:
```

Customize behavior by mounting a `conf.php` into `/srv/cfg/`:

```php
<?php
return [
    'main' => [
        'name' => 'PrivateBin',
        'discussion' => true,
        'opendiscussion' => false,
        'password' => true,
        'fileupload' => true,
        'burnafterreadingselected' => true,
        'defaultformatter' => 'plaintext',
        'sizelimit' => 10485760,
    ],
    'expire' => [
        'default' => '1week',
    ],
];
```

## Bitwarden Send (via Vaultwarden)

[Bitwarden Send](https://bitwarden.com/products/send/) is a feature of the Bitwarden ecosystem that allows sharing secrets with expiration controls. The official Bitwarden server is proprietary, but [Vaultwarden](https://github.com/dani-garcia/vaultwarden) provides a fully compatible, open-source Rust implementation that includes Send support.

**Key features:**

- **Client-side encryption** — secrets are encrypted before leaving the browser
- **Seamless integration** — works with the official Bitwarden browser extension and mobile apps
- **File sharing** — attach files up to 500MB (Vaultwarden default)
- **Password protection** — optional password for additional security
- **Full Bitwarden ecosystem** — combine with password vault, organization management, and SSO
- **Deletion on schedule** — set expiration from 1 hour to 30 days, or manual deletion

### Docker Compose Setup

Vaultwarden with Send enabled requires minimal configuration:

```yaml
version: "3"
services:
  vaultwarden:
    image: vaultwarden/server:latest
    container_name: vaultwarden
    restart: unless-stopped
    ports:
      - "8080:80"
    environment:
      WEBSOCKET_ENABLED: "true"
      SIGNUPS_ALLOWED: "false"
      SEND_ALLOWED: "true"
      SEND_EXPIRES_ON_MAX: "true"
      DOMAIN: "https://vaultwarden.example.com"
      ADMIN_TOKEN: "your-admin-token-here"
    volumes:
      - vw-data:/data

volumes:
  vw-data:
```

Add a reverse proxy (Caddy, Nginx) in front for HTTPS termination. The Vaultwarden admin panel at `/admin` lets you manage users and monitor Send usage.

## When to Use Each Tool

### Choose PasswordPusher When:

- You need **audit trails** to track who accessed shared credentials and when
- You're managing **team onboarding** and want to track which credentials were delivered
- You need a **REST API** for automation (CI/CD pipelines, chat bot integrations)
- You want **custom branding** and a polished user experience
- You need **configurable view counts** (not just burn-after-reading)

### Choose PrivateBin When:

- **Maximum privacy** is your top priority — zero-knowledge means the server operator cannot read your data
- You need a **lightweight, simple** deployment with minimal resource requirements
- You want **syntax highlighting** for sharing code snippets
- You need **encrypted discussion threads** attached to shared secrets
- You're running on a **budget VPS** with limited resources

### Choose Bitwarden Send (Vaultwarden) When:

- Your team already uses **Bitwarden** for password management
- You want a **unified platform** for both vault storage and secret sharing
- You need **file sharing** alongside text secrets
- You want **browser extension integration** for one-click secret retrieval
- You need **organization-level management** with user directories

## Why Self-Host Password Sharing?

Using a third-party service like Pastebin.com or a cloud-based secret sharing tool means your credentials pass through servers you don't control. Self-hosting gives you complete ownership of the data lifecycle.

**Data ownership matters** — when you share database credentials, API keys, or SSH private keys, those are the master keys to your infrastructure. Trusting a third-party service with that data introduces risk: a breach at the service provider, a misconfigured retention policy, or legal compulsion could expose your secrets. With self-hosted tools, deletion is immediate and verifiable.

**Cost savings** are significant compared to enterprise SaaS alternatives. Bitwarden Send in the cloud requires a paid Teams plan. PasswordPusher's premium features (file attachments, advanced analytics) also require a subscription. Self-hosting both tools is free and unlimited.

**No vendor lock-in** — if a cloud service shuts down or changes pricing, your workflow breaks. Self-hosted tools run on your infrastructure indefinitely. If you need to migrate, the data is yours to export.

For more on self-hosted security tooling, see our [secrets management comparison](../best-self-hosted-secret-management-vault-infisical-passbolt-2026/) and [password manager guide](../vaultwarden-vs-passbolt-vs-psono/). If you also need secure file sharing, our [document sharing guide](../2026-04-27-papermark-vs-filestash-vs-pingvin-share-self-hosted-documen/) covers complementary tools.

## FAQ

### Is it safe to use self-hosted password sharing tools?

Yes, if configured correctly. The security model relies on three pillars: HTTPS (encryption in transit), strong random expiration values (limiting exposure window), and server-side deletion (removing data after use). For maximum security, use tools with client-side encryption like PrivateBin, where the server never sees plaintext data. Always run these services behind a reverse proxy with HTTPS.

### Can the server admin see the passwords I share?

It depends on the tool. With **PrivateBin**, the answer is definitively no — encryption happens in the browser before data reaches the server. With **PasswordPusher**, the data is encrypted at rest using your master key, so a database dump without the key is useless. With **Vaultwarden**, encryption is client-side (AES-256-CBC), so the server cannot read secrets. However, server-level access could allow an admin to intercept data in transit if HTTPS is misconfigured.

### How long should I set the expiration for shared credentials?

For one-time credential sharing (onboarding, contractor access), use **burn-after-reading (1 view)** with a **1-hour time limit** as a safety net. For credentials that may need re-reading by the same person, use **3–5 views** with a **24-hour limit**. Never set expiration beyond 7 days for active credentials — if someone hasn't used them by then, they should request a new link.

### Can I use these tools to share files, not just passwords?

**PasswordPusher** supports file attachments in its premium tier. **PrivateBin** has an optional file upload feature (configurable max size). **Vaultwarden** supports file attachments up to 500MB with Send. If your primary need is file sharing (not passwords), consider dedicated file sharing tools instead — they handle large files more efficiently.

### Do I need a database to run these tools?

**PasswordPusher** defaults to SQLite (single file, no database server needed) but supports PostgreSQL and MySQL for production. **PrivateBin** stores encrypted data in flat files on disk — no database at all. **Vaultwarden** uses SQLite by default, with optional MySQL/PostgreSQL backends. For small teams, SQLite is perfectly adequate for all three tools.

### How do I prevent abuse (spam, malicious links) on my self-hosted instance?

All three tools have anti-abuse features: **PasswordPusher** supports reCAPTCHA and rate limiting. **PrivateBin** has built-in rate limiting and a spam filter. **Vaultwarden** can restrict signups (`SIGNUPS_ALLOWED: "false"`) and limit Send creation to authenticated users. Additionally, run all instances behind a reverse proxy with rate limiting (e.g., `fail2ban` or Nginx `limit_req`).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "PasswordPusher vs PrivateBin vs Bitwarden Send: Best Self-Hosted Password Sharing 2026",
  "description": "Compare PasswordPusher, PrivateBin, and Bitwarden Send (Vaultwarden) for self-hosted secure password sharing. Includes Docker Compose configs, feature comparison, and deployment guides.",
  "datePublished": "2026-05-03",
  "dateModified": "2026-05-03",
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
