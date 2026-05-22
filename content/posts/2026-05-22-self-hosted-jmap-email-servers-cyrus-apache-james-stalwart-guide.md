---
title: "Self-Hosted JMAP Email Servers: Cyrus JMAP vs Apache James vs Stalwart Mail"
date: "2026-05-22"
tags: ["jmap", "email", "self-hosted", "comparison", "imap", "smtp"]
draft: false
description: "Compare self-hosted JMAP email server implementations: Cyrus JMAP, Apache James, and Stalwart Mail. Full Docker Compose configs, feature comparisons, and deployment guides."
---

The JSON Meta Application Protocol (JMAP) is a modern, RESTful replacement for IMAP, SMTP, and CalDAV. Designed by the IETF (RFC 8620 for data, RFC 8621 for core), JMAP uses JSON over HTTPS to provide a cleaner, more efficient email API — eliminating the IMAP idle/poll cycle, simplifying authentication, and enabling real-time push notifications natively.

For self-hosted email infrastructure, JMAP offers significant advantages over traditional protocols: reduced connection overhead, simpler client development, and unified access to email, contacts, and calendar data through a single API. Three major open-source projects now provide JMAP server implementations: Cyrus JMAP (an extension of the venerable Cyrus IMAP server), Apache James (a full-featured Java mail server), and Stalwart Mail (a modern Rust-based all-in-one mail server).

This guide compares all three JMAP implementations, covering architecture, Docker deployment, feature sets, and production readiness.

## What Is JMAP and Why Use It?

JMAP was designed to solve the fundamental limitations of IMAP and SMTP for modern applications:

- **HTTP/JSON-native** — Uses standard HTTPS with JSON request/response bodies, eliminating the need for specialized IMAP/SMTP client libraries
- **Stateless design** — Each request is independent, enabling horizontal scaling without connection state synchronization
- **Push notifications** — Built-in state comparison API lets clients detect changes efficiently, replacing IMAP IDLE
- **Unified protocol** — Single API for email, contacts, calendars, and tasks, replacing IMAP + CalDAV + CardDAV
- **Reduced bandwidth** — Differential updates and batched operations minimize data transfer compared to IMAP's verbose text protocol

For self-hosted deployments, JMAP's HTTP-native design means you can use existing reverse proxy infrastructure (Nginx, Traefik, Caddy) without specialized protocol handling. Combined with TLS termination at the proxy layer, JMAP provides end-to-end encrypted email access with standard web infrastructure.

## Cyrus JMAP

Cyrus JMAP extends the Cyrus IMAP server (originally developed at Carnegie Mellon University) with JMAP protocol support. It shares the same storage backend as Cyrus IMAP, meaning you can run both IMAP and JMAP on the same mailbox data.

**GitHub**: `cyrusimap/cyrus-imapd` | **Stars**: 630+ | **Language**: C

### Architecture

Cyrus JMAP runs as a separate daemon (`jmap`) alongside the Cyrus IMAP daemon (`imapd`). Both access the same mailbox database (Berkeley DB or lmdb), enabling protocol-agnostic mail storage.

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  cyrus-jmap:
    image: docker.io/cyrusimap/cyrus-imapd:3.10
    container_name: cyrus-jmap
    restart: unless-stopped
    ports:
      - "8080:8080"
      - "993:993"
    volumes:
      - ./cyrus-config:/etc/imapd.d
      - ./cyrus-mail:/var/lib/imap
      - ./cyrus-sieve:/var/lib/imap/sieve
    environment:
      - CYRUS_ADMIN_USER=admin
      - CYRUS_ADMIN_PASSWORD=admin_secret
    networks:
      - mail-net

  cyrus-sasl:
    image: docker.io/cyrusimap/cyrus-sasl:3.10
    container_name: cyrus-sasl
    restart: unless-stopped
    volumes:
      - ./sasl-config:/etc/sasl2
    networks:
      - mail-net

networks:
  mail-net:
    driver: bridge
```

### Configuration

The Cyrus JMAP configuration in `imapd.conf`:

```
jmapenabled: 1
jmapdownloadurl: https://mail.example.com/download
jmapuploadurl: https://mail.example.com/upload
jmapwsurl: wss://mail.example.com/ws
httpmodules: jmap caldav carddav
```

### Pros and Cons

| Feature | Status |
|---------|--------|
| JMAP RFC 8620/8621 compliance | Full |
| IMAP coexistence | Yes, shared storage |
| CalDAV/CardDAV support | Yes |
| Sieve filtering | Yes |
| Multi-tenancy | No (single server) |
| Docker image | Official |
| Active development | Yes |
| Maturity | High (30+ years) |

## Apache James

Apache James (Java Apache Mail Enterprise Server) is a full-featured mail server with JMAP, IMAP, SMTP, and LMTP support. Written in Java, it provides enterprise-grade mail processing with a modular architecture.

**GitHub**: `apache/james-project` | **Stars**: 1,010+ | **Language**: Java

### Architecture

Apache James uses a modular architecture with separate components for mailbox storage, mail queue, JMAP API, SMTP/LMTP listeners, and Sieve processing. It supports multiple storage backends (JPA, Cassandra, distributed storage).

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  james-jmap:
    image: docker.io/apache/james-memory:3.9.0
    container_name: james-jmap
    restart: unless-stopped
    ports:
      - "80:80"
      - "25:25"
      - "143:143"
    volumes:
      - ./james-config:/root/conf
      - ./james-data:/root/var
    environment:
      - JAMES_DOMAINS=example.com
    networks:
      - mail-net

  james-smtp:
    image: docker.io/apache/james-memory:3.9.0
    container_name: james-smtp
    restart: unless-stopped
    ports:
      - "587:587"
    volumes:
      - ./james-config:/root/conf
    networks:
      - mail-net

networks:
  mail-net:
    driver: bridge
```

### JMAP Configuration

Apache James JMAP is enabled by default in recent versions. Configure `jmap.properties`:

```
jmap.enabled=true
jmap.cors.allowedOrigins=https://webmail.example.com
jmap.authentication=enabled
jmap.upload.maxSize=52428800
```

### Pros and Cons

| Feature | Status |
|---------|--------|
| JMAP RFC 8620/8621 compliance | Full |
| IMAP coexistence | Yes |
| CalDAV/CardDAV support | No (email only) |
| Sieve filtering | Yes |
| Multi-tenancy | Yes (domain-based) |
| Docker image | Official |
| Active development | Yes |
| Maturity | High (20+ years) |

## Stalwart Mail

Stalwart Mail is a modern, all-in-one mail server written in Rust. It provides JMAP, IMAP, SMTP, CalDAV, CardDAV, and WebDAV in a single binary with a strong focus on security and performance.

**GitHub**: `stalwartlabs/mail-server` | **Stars**: 12,800+ | **Language**: Rust

### Architecture

Stalwart uses a single-process architecture with all protocols (JMAP, IMAP, SMTP, CalDAV) handled by the same binary. Storage backends include RocksDB, S3-compatible storage, and SQL databases (PostgreSQL, MySQL, SQLite).

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  stalwart-mail:
    image: docker.io/stalwartlabs/mail-server:latest
    container_name: stalwart-mail
    restart: unless-stopped
    ports:
      - "8080:8080"
      - "993:993"
      - "587:587"
      - "25:25"
    volumes:
      - ./stalwart-config:/etc/stalwart
      - ./stalwart-data:/var/lib/stalwart
    environment:
      - STALWART_HTTP_BIND_ADDR=0.0.0.0:8080
      - STALWART_JMAP_ENABLED=true
      - STALWART_SMTP_BIND_ADDR=0.0.0.0:587
    networks:
      - mail-net

networks:
  mail-net:
    driver: bridge
```

### Configuration

Stalwart uses TOML configuration (`/etc/stalwart/stalwart.toml`):

```toml
[server.listener.jmap]
bind = "[::]:8080"
protocol = "jmap"
tls = false

[jmap]
enabled = true
max-upload-size = 52428800
max-requests-per-call = 16

[jmap.accounts]
default = "local"

[storage]
backend = "rocksdb"
```

### Pros and Cons

| Feature | Status |
|---------|--------|
| JMAP RFC 8620/8621 compliance | Full |
| IMAP coexistence | Yes |
| CalDAV/CardDAV support | Yes |
| Sieve filtering | Yes |
| Multi-tenancy | Yes (tenant-based) |
| Docker image | Official |
| Active development | Very active |
| Maturity | Medium (2020+) |

## Feature Comparison

| Feature | Cyrus JMAP | Apache James | Stalwart Mail |
|---------|-----------|-------------|---------------|
| JMAP Core (RFC 8621) | Yes | Yes | Yes |
| JMAP Mail (RFC 8620) | Yes | Yes | Yes |
| JMAP Calendar | Yes | No | Yes |
| JMAP Contacts | Yes | No | Yes |
| SMTP Server | No (external) | Yes | Yes |
| IMAP Server | Yes (same codebase) | Yes | Yes |
| CalDAV | Yes | No | Yes |
| CardDAV | Yes | No | Yes |
| Sieve Filtering | Yes | Yes | Yes |
| Multi-tenancy | No | Yes (domains) | Yes (tenants) |
| Storage Backend | Berkeley DB/lmdb | JPA/Cassandra | RocksDB/S3/SQL |
| Language | C | Java | Rust |
| Memory Footprint | Low | Medium-High | Low |
| Docker Support | Official | Official | Official |
| Web Admin UI | No | Yes | Yes (built-in) |
| Active Development | Yes | Yes | Very Active |

## Choosing the Right JMAP Server

**Choose Cyrus JMAP** if you have an existing Cyrus IMAP deployment and want to add JMAP support without migrating mailboxes. The shared storage backend means zero-downtime protocol migration. Cyrus is also the best choice for high-volume mail servers with decades of battle-tested stability.

**Choose Apache James** if you need Java integration, enterprise multi-tenancy with domain-based routing, or plan to extend the server with custom Java mail processing modules. James excels in environments requiring complex mail routing, DKIM signing, and spam filtering pipelines.

**Choose Stalwart Mail** if you want a modern, all-in-one solution with minimal resource usage. Stalwart's Rust implementation provides memory safety, excellent performance, and a single-binary deployment model. Its built-in web admin UI and JMAP-first design make it ideal for new self-hosted email deployments.

## Why Self-Host Your Email Server?

Running your own email server with JMAP gives you full control over your communication infrastructure. Unlike proprietary email services, self-hosted JMAP servers provide:

- **Data sovereignty** — All email data stays on your infrastructure, accessible via standard APIs you control. No vendor lock-in or data mining concerns.
- **Protocol modernization** — JMAP replaces decades-old IMAP with a clean JSON API, simplifying client development and enabling modern features like real-time sync without polling.
- **Unified communication** — JMAP covers email, contacts, calendars, and tasks in a single protocol, eliminating the need to maintain separate IMAP, CalDAV, and CardDAV servers.
- **Cost efficiency** — Open-source JMAP servers eliminate per-user licensing fees. Stalwart Mail runs on minimal hardware, and Cyrus JMAP shares infrastructure with existing IMAP deployments.
- **Custom integrations** — The RESTful JMAP API integrates easily with custom applications, web portals, and automation workflows that would be complex with IMAP's text-based protocol.

For email authentication and security hardening, see our [OpenDKIM vs Rspamd vs OpenDMARC guide](../2026-05-18-opendkim-vs-rspamd-vs-opendmarc-email-authentication-guide/). If you need webmail access alongside JMAP, our [Roundcube vs Snappy Mail vs Cypht comparison](../roundcube-vs-snappymail-vs-cypht-self-hosted-webmail-guide-2026/) covers the best options. For general mail server management, the [PostfixAdmin vs Modoboa vs iRedAdmin guide](../2026-04-26-postfixadmin-vs-modoboa-vs-iredadmin-self-hosted-mail-admin-guide-2026/) provides admin UI comparisons.

## FAQ

### What is JMAP and how does it differ from IMAP?

JMAP (JSON Meta Application Protocol) is a modern email access protocol that uses JSON over HTTPS instead of IMAP's text-based protocol. It provides stateless request/response semantics, built-in push notifications, and batched operations, making it more efficient for modern applications than IMAP's connection-state model.

### Can I run JMAP and IMAP on the same server?

Yes. Cyrus JMAP shares the same mailbox storage as Cyrus IMAP, so both protocols serve the same mailboxes simultaneously. Apache James and Stalwart Mail also support both protocols, allowing gradual migration from IMAP clients to JMAP clients.

### Do I need a separate SMTP server for JMAP?

Cyrus JMAP does not include SMTP — you need a separate SMTP server (Postfix, Exim). Apache James and Stalwart Mail both include built-in SMTP servers, providing complete mail infrastructure in a single deployment.

### Is JMAP supported by email clients?

JMAP client support is growing but not yet universal. Apple Mail (iOS 16+, macOS Ventura+) has native JMAP support. Fastmail has supported JMAP since its inception. Webmail clients like Roundcube can integrate with JMAP via plugins. Stalwart Mail includes a built-in webmail interface.

### Can JMAP handle large mailboxes?

Yes. Cyrus JMAP leverages Cyrus IMAP's proven mailbox storage (supporting millions of messages). Stalwart Mail uses RocksDB or S3-backed storage for scalability. Apache James supports distributed storage backends including Cassandra for enterprise-scale deployments.

### What are the hardware requirements for a self-hosted JMAP server?

For small deployments (up to 100 users): Cyrus JMAP requires 1-2 GB RAM, Apache James needs 2-4 GB (Java heap), and Stalwart Mail runs comfortably on 512 MB-1 GB RAM due to its Rust implementation. All three can run on a single CPU core for moderate workloads.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted JMAP Email Servers: Cyrus JMAP vs Apache James vs Stalwart Mail",
  "description": "Compare self-hosted JMAP email server implementations: Cyrus JMAP, Apache James, and Stalwart Mail. Full Docker Compose configs, feature comparisons, and deployment guides.",
  "datePublished": "2026-05-22",
  "dateModified": "2026-05-22",
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
