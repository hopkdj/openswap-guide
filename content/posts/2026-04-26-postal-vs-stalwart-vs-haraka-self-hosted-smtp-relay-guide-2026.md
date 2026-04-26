---
title: "Postal vs Stalwart vs Haraka: Best Self-Hosted SMTP Relay 2026"
date: 2026-04-26T08:00:00Z
tags: ["comparison", "guide", "self-hosted", "email", "smtp"]
draft: false
description: "Compare Postal, Stalwart, and Haraka — three powerful open-source SMTP relay and mail delivery solutions. Includes Docker Compose configs, feature comparison, and deployment guides for 2026."
---

If you're sending transactional emails, running a mailing list, or building a self-hosted mail infrastructure, relying on commercial SMTP providers like SendGrid, Mailgun, or Amazon SES means giving up control over your email pipeline — and paying per-message fees that add up quickly. Self-hosted SMTP relay solutions put you back in charge: no per-email costs, full data privacy, and complete control over deliverability, routing, and compliance.

In this guide, we compare three mature open-source options for self-hosted SMTP relay and mail delivery: **Postal** (full-featured mail delivery platform), **Stalwart Mail Server** (modern all-in-one Rust mail server), and **Haraka** (fast, plugin-driven Node.js SMTP server). Each takes a different approach, and the right choice depends on whether you need a SendGrid replacement, a full mail server, or a lightweight extensible SMTP daemon.

## Why Self-Host an SMTP Relay?

Commercial email APIs offer convenience, but they come with significant trade-offs:

- **Cost at scale** — SendGrid charges $15/month for 50,000 emails. Postal and Stalwart cost nothing beyond your server.
- **Vendor lock-in** — Migrating away from a commercial provider means reconfiguring every application that sends email.
- **Data privacy** — Every email passes through third-party servers. Self-hosting keeps message content on your infrastructure.
- **Deliverability control** — You manage your own IP reputation, SPF/DKIM/DMARC records, and feedback loops.
- **No rate limits** — Commercial APIs throttle sending based on your tier. Self-hosted solutions are limited only by your hardware and IP reputation.

For organizations sending thousands of emails daily — transactional receipts, password resets, notifications, or marketing campaigns — a self-hosted SMTP relay quickly pays for itself in reduced costs and increased control. For setting up your complete email authentication stack, our [self-hosted DMARC analysis guide](../self-hosted-dmarc-analysis-email-authentication-parsedmarc-opendmarc-guide-2026/) covers SPF, DKIM, and DMARC configuration in detail.

## Postal — Full-Featured Mail Delivery Platform

**GitHub:** [postalserver/postal](https://github.com/postalserver/postal) · 16,475 stars · Last updated April 2026 · Ruby

Postal is the closest open-source equivalent to SendGrid or Mailgun. It's a complete mail delivery platform designed for incoming and outgoing email, with a web interface, API, and per-domain sending controls. Unlike a traditional MTA (Mail Transfer Agent) like Postfix, Postal sits on top of standard SMTP servers and adds organization-level features: multiple mail servers, message tracking, webhooks, and detailed analytics.

### Key Features

- **Organization-based multi-tenancy** — create separate organizations, each with their own mail servers, domains, and credentials
- **Full message tracking** — track deliveries, bounces, opens, clicks, and spam complaints per message
- **Webhook integration** — receive real-time events for deliveries, bounces, opens, and clicks via HTTP POST
- **API-driven** — REST API for sending messages, managing domains, and retrieving statistics
- **Web interface** — clean dashboard for monitoring message flow, managing domains, and viewing logs
- **SMTP relay support** — route outgoing mail through upstream providers (SendGrid, Mailgun, or your own Postfix server)
- **Message archives** — retain copies of all sent and received messages for compliance

Postal requires MariaDB/MySQL, RabbitMQ, and optionally Redis. It's designed for production-scale email operations where you need to manage multiple sending domains, track deliverability, and integrate email events into your application pipeline. If you need a full mail server with IMAP and calendar support alongside SMTP, our [Stalwart vs Mailcow vs Mailu comparison](../stalwart-vs-mailcow-vs-mailu/) covers the all-in-one alternatives.

### Docker Compose Setup

```yaml
services:
  mariadb:
    image: mariadb:11
    restart: always
    environment:
      MARIADB_ROOT_PASSWORD: postal
      MARIADB_DATABASE: postal
    volumes:
      - mariadb_data:/var/lib/mysql

  rabbitmq:
    image: rabbitmq:3-management
    restart: always
    environment:
      RABBITMQ_DEFAULT_USER: postal
      RABBITMQ_DEFAULT_PASS: postal

  redis:
    image: redis:7-alpine
    restart: always

  postal:
    image: ghcr.io/postalserver/postal:latest
    restart: always
    depends_on:
      - mariadb
      - rabbitmq
      - redis
    ports:
      - "5000:5000"
    environment:
      POSTAL_INITIALIZE_DB: "true"
      POSTAL_REGISTER_ADMIN: "true"
      POSTAL_CONFIG_MAIL_SERVER_ADDRESS: "mail.yourdomain.com"
      POSTAL_CONFIG_DATABASE_HOST: mariadb
      POSTAL_CONFIG_DATABASE_USERNAME: root
      POSTAL_CONFIG_DATABASE_PASSWORD: postal
      POSTAL_CONFIG_DATABASE_DATABASE: postal
      POSTAL_CONFIG_DNS_MX_RECORDS: "mail.yourdomain.com"
      POSTAL_CONFIG_DNS_SPF_INCLUDE: "spf.postal.yourdomain.com"
    volumes:
      - postal_config:/postal/config

volumes:
  mariadb_data:
  postal_config:
```

After starting the stack with `docker compose up -d`, access the web interface at `http://your-server:5000` and complete the initial setup wizard. You'll need to configure DNS records (MX, SPF, DKIM) for your sending domain before messages will deliver reliably.

## Stalwart Mail Server — All-in-One Modern Rust Solution

**GitHub:** [stalwartlabs/mail-server](https://github.com/stalwartlabs/mail-server) · 12,505 stars · Last updated April 2026 · Rust

Stalwart is a modern, all-in-one mail and collaboration server written in Rust. Unlike Postal (which is a mail delivery platform that sits on top of an MTA), Stalwart handles the entire mail stack: SMTP, IMAP, JMAP, CalDAV, CardDAV, and WebDAV — all from a single binary. It's designed to replace a full Postfix + Dovecot + Roundcube stack with one piece of software.

### Key Features

- **All-in-one** — SMTP, IMAP, JMAP, CalDAV, CardDAV, WebDAV in a single server process
- **Rust-powered** — memory-safe, low resource footprint, high performance
- **Built-in webmail** — JMAP-based web interface, no separate frontend needed
- **Multiple storage backends** — SQLite (embedded), PostgreSQL, MySQL, or RocksDB
- **Full-text search** — native search across mailboxes with indexed content
- **Sieve filtering** — server-side email filtering with the Sieve language
- **Anti-spam built-in** — DNSBL, SPF, DKIM, DMARC verification out of the box
- **Active Directory / LDAP integration** — authenticate users against existing directories
- **Cluster-ready** — supports multi-node deployment with shared storage

Stalwart's architecture is fundamentally different from Postal. Where Postal is a mail delivery management layer, Stalwart is a complete mail server that can handle both sending and receiving. It's an excellent choice if you want to consolidate multiple mail services into a single, well-maintained binary.

### Docker Compose Setup

```yaml
services:
  stalwart:
    image: ghcr.io/stalwartlabs/mail-server:latest
    restart: always
    ports:
      - "25:25"       # SMTP
      - "143:143"     # IMAP
      - "443:443"     # HTTPS (JMAP, CalDAV, CardDAV)
      - "587:587"     # SMTP submission
      - "993:993"     # IMAPS
    volumes:
      - ./stalwart-config:/etc/stalwart
      - stalwart-data:/var/lib/stalwart
    environment:
      - SMTP_HOSTNAME=mail.yourdomain.com
      - ADMIN_USER=admin
      - ADMIN_PASSWORD=changeme
      - STORAGE_TYPE=sqlite
      - STORAGE_PATH=/var/lib/stalwart/db

volumes:
  stalwart-data:
```

For a production setup, mount a custom configuration file at `/etc/stalwart/main.toml` and use PostgreSQL as the storage backend for multi-user deployments. The default SQLite storage is sufficient for single-user or small-team installations.

## Haraka — Fast Plugin-Driven Node.js SMTP Server

**GitHub:** [haraka/haraka](https://github.com/haraka/haraka) · 5,564 stars · Last updated April 2026 · JavaScript

Haraka is a highly extensible, event-driven SMTP server built on Node.js. It was designed from the ground up to be fast and modular — every aspect of SMTP processing (connection, HELO, MAIL FROM, RCPT TO, DATA, queue) is handled by plugins that can be mixed and matched. This makes Haraka the most customizable option of the three, but also the one requiring the most configuration.

### Key Features

- **Plugin architecture** — 200+ community plugins for spam filtering, authentication, logging, routing, and more
- **High throughput** — handles thousands of concurrent connections with Node.js's async event loop
- **Cluster mode** — native support for multi-core systems with automatic worker distribution
- **Flexible queue** — multiple queue backends including `qmail-queue`, `smtp-forward`, and `lmtp`
- **Custom routing** — route mail based on sender, recipient, domain, or any custom logic via plugins
- **SMTP relay** — forward mail to upstream servers with per-domain routing rules
- **Hot-reloadable config** — change configuration and plugins without restarting the server
- **JavaScript ecosystem** — tap into the vast npm plugin ecosystem for custom functionality

Haraka excels in scenarios where you need custom email processing logic: content-based routing, custom spam scoring, integration with external APIs during SMTP transactions, or building a mail relay layer for a SaaS product. Its plugin system is unmatched for flexibility, but the trade-off is a steeper learning curve compared to Postal's ready-to-use web interface.

### Docker Compose Setup

```yaml
services:
  haraka:
    image: ghcr.io/haraka/haraka:latest
    restart: always
    ports:
      - "25:25"
      - "587:587"
    volumes:
      - ./haraka-config:/haraka/config
      - ./haraka-plugins:/haraka/plugins
    environment:
      - HARAKA_HOSTLIST=mail.yourdomain.com
      - HARAKA_ME=mail.yourdomain.com
      - NODE_ENV=production
```

Haraka's configuration lives in `/haraka/config/`. Key files to set up:

- `config/host_list` — domains this server accepts mail for
- `config/plugins` — ordered list of active plugins
- `config/smtp.ini` — listen addresses and port configuration
- `config/dkim/sign/` — DKIM signing keys per domain

A minimal production setup typically enables plugins like `tls`, `auth/flat_file`, `dnsbl`, `helo.checks`, `mail_from.is_resolvable`, and `spf` for baseline security and deliverability.

## Feature Comparison

| Feature | Postal | Stalwart | Haraka |
|---|---|---|---|
| **Type** | Mail delivery platform | All-in-one mail server | Extensible SMTP server |
| **Language** | Ruby | Rust | JavaScript (Node.js) |
| **Web Interface** | Yes (admin dashboard) | Yes (webmail + admin) | No (plugin-based) |
| **SMTP Sending** | Yes (with upstream relay) | Yes (native) | Yes (native) |
| **SMTP Receiving** | Yes (incoming mail) | Yes (native) | Yes (native) |
| **IMAP/JMAP** | No | Yes | No |
| **API** | REST API | REST API (JMAP) | Plugin API |
| **Message Tracking** | Full (open, click, bounce) | Basic | Plugin-dependent |
| **Webhooks** | Yes (delivery events) | No | Plugin-dependent |
| **Multi-tenancy** | Organizations + servers | Multiple domains | Plugin-dependent |
| **Queue Management** | Yes | Yes | Plugin-based |
| **Spam Filtering** | Via upstream/plugins | Built-in (DNSBL, SPF, DKIM) | Via plugins |
| **Storage Backend** | MariaDB/MySQL | SQLite, PostgreSQL, MySQL | File system |
| **CalDAV/CardDAV** | No | Yes | No |
| **Stars** | 16,475 | 12,505 | 5,564 |
| **Last Updated** | April 2026 | April 2026 | April 2026 |
| **Docker Image** | `ghcr.io/postalserver/postal` | `ghcr.io/stalwartlabs/mail-server` | `ghcr.io/haraka/haraka` |

## Choosing the Right SMTP Relay

The decision comes down to your use case:

**Choose Postal if:**
- You need a SendGrid/Mailgun replacement with a web dashboard
- You manage multiple sending domains and need per-domain analytics
- You need webhook integration for delivery events
- You want message-level tracking (opens, clicks, bounces)
- You're building a SaaS product that sends email on behalf of customers

**Choose Stalwart if:**
- You want a complete mail server replacement (SMTP + IMAP + webmail)
- You value a single binary with no external database requirements
- You need calendar (CalDAV) and contacts (CardDAV) alongside email
- You prefer Rust for security and performance
- You want built-in anti-spam without additional configuration

**Choose Haraka if:**
- You need maximum customizability with a plugin architecture
- You want to build custom email processing pipelines
- You need content-based routing or dynamic SMTP transaction logic
- You're comfortable with Node.js and JavaScript development
- You want hot-reloadable configuration without server restarts

## FAQ

### What is the difference between an SMTP relay and a mail server?

An SMTP relay focuses on routing and delivering outgoing mail — it accepts messages from applications and forwards them to recipient mail servers. A full mail server handles both sending (SMTP) and receiving/storing (IMAP/POP3) mail, and often includes webmail, calendar, and contacts. Postal is primarily a delivery platform, Stalwart is a full mail server, and Haraka is a flexible SMTP server that can act as either relay or receiving server depending on configuration.

### Can I use these self-hosted SMTP solutions for marketing emails?

Yes, but deliverability depends on your IP reputation, not the software. All three solutions handle SMTP sending; the key to inbox placement is proper DNS configuration (SPF, DKIM, DMARC), warm-up of new IP addresses, and maintaining low bounce/complaint rates. See our [email deliverability guide](../self-hosted-email-deliverability-inbox-placement-guide-2026/) for best practices on maintaining good sender reputation.

### Which solution is easiest to set up?

Stalwart is the simplest for a quick start — a single Docker container with SQLite requires zero external dependencies. Postal requires three services (Postal, MariaDB, RabbitMQ) plus DNS configuration. Haraka requires the most manual setup, as you need to configure individual plugins for authentication, TLS, spam filtering, and queue management.

### Can I migrate from SendGrid or Mailgun to a self-hosted solution?

Yes. All three solutions support SMTP authentication and can accept connections from applications configured to use SendGrid/Mailgun. For Postal, you can configure it as an SMTP relay that forwards through your existing provider during a transition period. Update your application's SMTP credentials, point them to your self-hosted server, and monitor delivery rates before fully switching over.

### Do I need a separate MTA like Postfix with any of these?

Postal typically runs on top of a traditional MTA (Postfix or Exim) for the actual SMTP delivery layer, while Postal itself manages the control plane (tracking, webhooks, domains). Stalwart and Haraka are standalone SMTP servers — they do not require a separate MTA. Haraka can be configured to deliver directly or relay through upstream servers.

### How do I handle IP reputation with self-hosted SMTP?

IP reputation is managed at the network level, not the software level. Use a dedicated IP address for mail sending, warm up the IP by gradually increasing volume, configure reverse DNS (PTR records) for your mail server, and maintain consistent sending patterns. Monitor your IP on DNS blacklists and use tools like MXToolbox to check your reputation. For spam filtering on the receiving side, see our [Rspamd vs SpamAssassin comparison](../spamassassin-vs-rspamd-vs-amavis-self-hosted-spam-filtering-guide-2026/).

### Which solution scales best for high-volume sending?

Haraka's Node.js architecture handles thousands of concurrent connections efficiently and is designed for high-throughput scenarios. Stalwart's Rust implementation is also performant but is designed more as a full mail server than a dedicated high-volume relay. Postal scales horizontally by adding more mail server instances per organization, but the underlying delivery speed depends on the MTA it's paired with.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Postal vs Stalwart vs Haraka: Best Self-Hosted SMTP Relay 2026",
  "description": "Compare Postal, Stalwart, and Haraka — three powerful open-source SMTP relay and mail delivery solutions. Includes Docker Compose configs, feature comparison, and deployment guides.",
  "datePublished": "2026-04-26",
  "dateModified": "2026-04-26",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "Pi Stack",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>
