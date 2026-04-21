---
title: "Self-Hosted Email Archiving 2026: MailPiler vs Dovecot vs Stalwart"
date: 2026-04-18
tags: ["comparison", "guide", "self-hosted", "email", "compliance", "privacy"]
draft: false
description: "Compare self-hosted email archiving solutions in 2026: MailPiler, Dovecot archiving plugin, and Stalwart Mail Server. Complete Docker setups and deployment guides for regulatory-compliant email retention."
---

## Why Self-Host Your Email Archive?

Every organization — from a solo freelancer to a mid-sized company — generates email trails that matter. Contracts negotiated over email. Support requests that need audit trails. Regulatory records that must be preserved for years. Handing all of that to Gmail, Microsoft 365, or any third-party archiving SaaS means **someone else controls your retention policy, your search capability, and your legal hold**.

Self-hosted email archiving gives you:

- **Regulatory compliance** — meet GDPR, HIPAA, SOX, and FINRA retention requirements on your own infrastructure
- **Full-text search** — index every message, attachment, and header across your entire mail history
- **Legal hold** — prevent deletion of specific messages during litigation or investigations
- **No per-mailbox fees** — commercial archiving services charge $3-15/month per user; self-hosted scales at hardware cost
- **Data sovereignty** — email archives never leave your server, satisfying strict data residency laws
- **Centralized journaling** — capture all inbound and outbound mail from every account in one searchable repository

In 2026, three approaches dominate the self-hosted email archiving space: **MailPiler** (dedicated archiving application), **Dovecot's built-in archiving plugin** (IMAP-level solution), and **[stalwart](https://stalw.art/) Mail Server** (all-in-one server with native journaling). Let's compare them.

For related reading, see our [complete self-hosted email server guide with Postfix, Dovecot, and Rspamd](../self-hosted-email-server-postfix-dovecot-rspamd-complete-guide-2026/) and the [Stalwart vs [mailcow](https://mailcow.email/) vs Mailu comparison](../stalwart-vs-mailcow-vs-mailu/) for broader email server alternatives.

## Quick Comparison Table

| Feature | MailPiler | Dovecot Archiving Plugin | Stalwart Mail Server |
|---------|-----------|-------------------------|---------------------|
| **Type** | Dedicated archiving app | IMAP server plugin | All-in-one mail server |
| **License** | GPLv3 | MIT/LGPL | AGPLv3 |
| **Written In** | PHP + C | C | Rust |
| **GitHub Stars** | 295 | Part of Dovecot (1,200+) | 12,357 |
| **Last Updated** | April 2026 | April 2026 | April 2026 |
| **Min RAM** | ~1 GB (with Manticore) | ~256 MB | ~128 MB |
| **Full-Text Search** | ✅ Manticore Search | ✅ FTS with Lucene/Solr | ✅ Built-in |
| **Deduplication** | ✅ SHA-256 content hash | ❌ Manual | ❌ Not built-in |
| **Web Interface** | ✅ Full web UI | ❌ IMAP only | ✅ Built-in admin + JMAP web |
| **REST API** | ✅ Full API | ❌ CLI only (doveadm) | ✅ REST + JMAP |
| **Journaling/BCC** | ✅ SMTP-level journaling | ❌ Requires Sieve + BCC | ✅ Built-in journaling |
| **Retention Policies** | ✅ Configurable per-user/per-domain | ❌ Manual (cron + doveadm) | ✅ Configurable |
| **Legal Hold** | ✅ Tag-based | ❌ Not supported | ⚠️ Via retention rules |
| **E-Discovery Export** | ✅ PST/EML export | ❌ Manual export | ✅ JMAP export |
| **[docker](https://www.docker.com/) Support** | ✅ Official compose | ⚠️ Community images | ✅ Official Docker image |
| **Best For** | Compliance-focused teams | Existing Dovecot deployments | New mail server setups |

---

## 1. MailPiler — Dedicated Email Archiving Application

**Best for**: Organizations that need a purpose-built, compliance-ready email archiving system with full-text search, deduplication, and e-discovery capabilities.

### Key Features

MailPiler ([github.com/jsuto/piler](https://github.com/jsuto/piler), 295 stars, PHP) is the most mature open-source email archiving solution. It sits between your mail server and users, capturing every message via SMTP journaling and storing it in a searchable archive with full-text indexing powered by **Manticore Search** (a MySQL-compatible full-text search engine).

- **SHA-256 deduplication** — identical messages sent to multiple recipients are stored only once, dramatically reducing storage
- **Full-text search** — index body text, headers, and attachments via Manticore Search
- **SMTP-level journaling** — configure Postfix or Exim to BCC all mail to the archiver, capturing both inbound and outbound
- **Web UI** — search, view, tag, and export archived messages from a browser
- **REST API** — programmatic access for integration with compliance workflows
- **Retention policies** — automatic cleanup of messages past their retention period
- **Multi-domain support** — archive mail for multiple domains with per-domain policies
- **Note import/export** — add context to archived messages and export to EML/PST format

### Docker Compose Deployment

MailPiler ships with an official Docker Compose configuration that orchestrates four services: MariaDB for metadata, Manticore Search for full-text indexing, Memcached for caching, and the Piler application itself.

```yaml
# docker-compose.yml — MailPiler Email Archive
services:
  mysql:
    image: mariadb:12.0.2
    container_name: piler-mysql
    restart: unless-stopped
    cap_drop:
      - ALL
    cap_add:
      - dac_override
      - setuid
      - setgid
    environment:
      - MYSQL_DATABASE=piler
      - MYSQL_USER=piler
      - MYSQL_PASSWORD=ChangeMePilerDB
      - MYSQL_RANDOM_ROOT_PASSWORD=yes
    command: --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci
    volumes:
      - db_data:/var/lib/mysql
      - ./piler.cnf:/etc/mysql/conf.d/piler.cnf:ro

  manticore:
    image: manticoresearch/manticore:14.1.0
    container_name: piler-manticore
    restart: unless-stopped
    volumes:
      - ./manticore.conf:/etc/manticoresearch/manticore.conf
      - piler_manticore:/var/lib/manticore
    deploy:
      resources:
        reservations:
          memory: 512M
        limits:
          memory: 512M

  memcached:
    image: memcached:latest
    container_name: piler-memcached
    command: -m 64

  piler:
    image: sutoj/piler:1.4.8
    container_name: piler
    init: true
    environment:
      - MANTICORE_HOSTNAME=piler-manticore
      - MEMCACHED_HOSTNAME=piler-memcached
      - MYSQL_HOSTNAME=piler-mysql
      - MYSQL_DATABASE=piler
      - MYSQL_USER=piler
      - MYSQL_PASSWORD=ChangeMePilerDB
      - PILER_HOSTNAME=archive.example.com
      - RT=1
    ports:
      - "25:25"       # SMTP journaling endpoint
      - "80:80"       # Web UI
    volumes:
      - piler_etc:/etc/piler
      - piler_store:/var/piler/store
    depends_on:
      - mysql
      - manticore
      - memcached

volumes:
  db_data:
  piler_manticore:
  piler_etc:
  piler_store:
```

### Postfix Journaling Configuration

To capture all mail, configure Postfix to send a blind carbon copy of every message to the archiver:

```bash
# /etc/postfix/main.cf
always_bcc = archive@piler.example.com

# Or per-domain journaling
recipient_bcc_maps = hash:/etc/postfix/recipient_bcc
sender_bcc_maps = hash:/etc/postfix/sender_bcc
```

```bash
# /etc/postfix/recipient_bcc
@example.com    archive@piler.example.com

postmap /etc/postfix/recipient_bcc
systemctl reload postfix
```

### Resource Requirements

MailPiler's four-service architecture requires more resources than a simple plugin:
- **RAM**: ~1 GB minimum (512 MB for Manticore, 256 MB for MariaDB, 64 MB for Memcached, ~256 MB for Piler)
- **Storage**: Depends on mail volume. With deduplication, expect ~50-100 MB per 1,000 messages (text only). Attachments add significantly more.
- **CPU**: 2 cores recommended for search indexing during peak ingestion

---

## 2. Dovecot Archiving Plugin — IMAP-Level Solution

**Best for**: Teams already running Dovecot as their IMAP server who want a lightweight, zero-dependency archiving approach without adding a separate application.

### Key Features

Dovecot ([dovecot.org](https://www.dovecot.org/), 1,200+ stars on GitLab) is the world's most widely deployed open-source IMAP server. Its archiving capabilities come through a combination of the **mail archive plugin**, **doveadm** CLI tools, and the **FTS (Full-Text Search) subsystem**.

- **IMAP-level archiving** — move or copy messages to a dedicated archive namespace using IMAP commands
- **Full-text search** — integrate with Lucene, Solr, or OCG (On-Disk CLucene) for message body search
- **doveadm tools** — command-line utilities for bulk operations: search, copy, delete, and export messages
- **Zero additional services** — runs within the existing Dovecot process, no separate database or search engine needed
- **Sieve integration** — automate archiving rules using Sieve scripts (e.g., "archive all messages older than 90 days from Inbox")
- **Namespace-based organization** — separate archive namespaces keep archived mail distinct from active mailboxes

### Installation and Configuration

```bash
# Ubuntu/Debian
apt install dovecot-core dovecot-imapd dovecot-lucene
```

Configure an archive namespace in `/etc/dovecot/dovecot.conf`:

```conf
namespace archive {
  separator = /
  prefix = Archive/
  location = maildir:/var/mail/archive
  inbox = no
  hidden = no
  list = yes
  subscriptions = no
}

# Enable FTS (Full-Text Search) with Lucene
plugin {
  fts = lucene
  fts_autoindex = yes
  fts_autoindex_exclude = \Trash
}
```

Automate archiving with a Sieve script (`~/.dovecot.sieve`):

```sieve
require ["fileinto", "imap4flags", "date", "relational"];

# Auto-archive messages older than 180 days from INBOX
if currentdate :value "lt" "received" "180" {
  fileinto "Archive/INBOX";
  stop;
}
```

Compile and activate:

```bash
sievec ~/.dovecot.sieve
systemctl reload dovecot
```

Bulk operations with doveadm:

```bash
# Search and export all messages from a specific sender in 2025
doveadm search -u user@example.com mailbox INBOX FROM "legal@partner.com"

# Copy messages matching a search to the archive namespace
doveadm copy -u user@example.com -S "mailbox INBOX BEFORE 2025-06-01" Archive/INBOX

# Expunge messages older than 2 years from Trash
doveadm expunge -A mailbox Trash BEFORE 2024-04-18
```

### Resource Requirements

- **RAM**: ~256 MB additional (Lucene FTS indexing adds ~128 MB)
- **Storage**: Same as your existing Dovecot maildir — no deduplication
- **CPU**: Minimal overhead for FTS indexing during off-peak hours

---

## 3. Stalwart Mail Server — All-in-One with Native Journaling

**Best for**: Organizations setting up a new mail server that want archiving built in from day one, without managing separate components.

### Key Features

Stalwart ([github.com/stalwartlabs/mail-server](https://github.com/stalwartlabs/mail-server), 12,357 stars, Rust) is a modern all-in-one mail server that includes native email journaling as a core feature. Written in Rust, it handles SMTP, IMAP, JMAP, CalDAV, and CardDAV in a single binary — and its archiving is built into the SMTP delivery pipeline.

- **Native SMTP journaling** — configure journaling rules at the SMTP level, capturing all inbound/outbound mail without Postfix BCC tricks
- **Built-in full-text search** — no external search engine needed; Stalwart indexes messages as they arrive
- **JMAP-native** — modern JSON-based mail access protocol (RFC 8620) with efficient search and pagination
- **Retention policies** — configurable per-domain and per-user retention rules
- **Single binary** — no separate database, search engine, or cache to manage
- **Memory-safe** — Rust eliminates buffer overflows and use-after-free vulnerabilities
- **Minimal resource footprint** — runs comfortably on 128 MB RAM for small deployments

### Docker Compose Deployment

```yaml
# docker-compose.yml — Stalwart Mail Server with Journaling
services:
  stalwart:
    image: stalwartlabs/mail-server:latest
    container_name: stalwart-mail
    restart: unless-stopped
    ports:
      - "25:25"       # SMTP inbound
      - "465:465"     # SMTPS (implicit TLS)
      - "587:587"     # SMTP submission (STARTTLS)
      - "993:993"     # IMAPS
      - "8080:8080"   # HTTP (JMAP + admin UI)
      - "443:443"     # HTTPS (ACME)
    environment:
      - SERVER_HOSTNAME=mail.example.com
      - SERVER_ADMIN=admin@example.com
    volumes:
      - stalwart-data:/opt/stalwart-mail
      - ./stalwart.toml:/etc/stalwart/stalwart.toml:ro

volumes:
  stalwart-data:
```

Configure journaling in `stalwart.toml`:

```toml
[journaling]
enabled = true
address = "journal@mail.example.com"

[journaling.rules]
# Journal all inbound and outbound mail for the domain
domain = "example.com"
direction = "both"

[storage]
# Retention: keep archived mail for 7 years (compliance)
retention = "7y"
```

### Resource Requirements

- **RAM**: ~128 MB minimum (single binary, no external dependencies)
- **Storage**: Depends on mail volume — no built-in deduplication
- **CPU**: 1 core sufficient for small deployments (up to ~10,000 messages/day)

---

## Which Solution Should You Choose?

**Choose MailPiler if:**
- You need compliance-grade archiving with deduplication, legal hold, and e-discovery export
- You already have a mail server (Postfix, Exim, Exchange) and want to add archiving without replacing it
- Your organization has regulatory requirements (GDPR, HIPAA, SOX) that demand auditable retention policies
- You need a web UI for non-technical staff to search and retrieve archived messages

**Choose Dovecot Archiving if:**
- You're already running Dovecot as your IMAP server
- You want the simplest possible setup with zero additional services
- Your archiving needs are straightforward (move old messages to a separate namespace)
- You prefer command-line tools over web interfaces

**Choose Stalwart if:**
- You're setting up a new mail server and want archiving included from day one
- You value minimal resource usage and a single-binary architecture
- You want modern protocol support (JMAP) alongside traditional IMAP/SMTP
- You're comfortable with TOML configuration instead of a GUI

For more on building a complete self-hosted email stack, check out our [self-hosted email marketing guide covering Listmonk, Mautic, and Postal](../self-hosted-email-marketing-listmonk-mautic-postal-guide/).

## FAQ

### What is email journaling and how does it differ from backup?

Email journaling captures every message (inbound, outbound, and internal) at the SMTP level before delivery. A backup copies existing mailboxes on a schedule. Journaling ensures **no message is ever missed** — even if a user immediately deletes an email, the journal copy remains. Backups only preserve what exists at backup time. For compliance, journaling is the gold standard.

### Does MailPiler support attachment indexing and search?

Yes. MailPiler indexes attachments through its Manticore Search integration. Common formats (PDF, DOCX, TXT, HTML) are extracted and searchable. Binary attachments are stored by SHA-256 hash for deduplication but may require external tools for content extraction. You can configure attachment filters in `piler.conf` to index specific MIME types.

### Can I use Dovecot archiving with an existing Postfix mail server?

Absolutely. Dovecot is commonly paired with Postfix (Postfix handles SMTP delivery, Dovecot handles IMAP access). The archiving plugin works within this setup — you configure archive namespaces in Dovecot and optionally use Postfix's `always_bcc` to feed messages into the archive. This is actually one of the most common self-hosted email server configurations.

### How much storage do I need for email archiving?

For text-only email, expect approximately **50-100 MB per 1,000 messages** with deduplication (MailPiler). Without deduplication (Dovecot, Stalwart), expect **100-200 MB per 1,000 messages**. Attachments dominate storage — a single 10 MB PDF sent to 50 recipients would consume 500 MB without deduplication but only ~10 MB with MailPiler's SHA-256 dedup. For a 100-user organization averaging 50 messages/day, plan for 20-40 GB per year of archive storage.

### Is self-hosted email archiving compliant with GDPR and HIPAA?

Self-hosted archiving gives you the **technical capability** to meet retention and deletion requirements under both regulations. GDPR's "right to be forgotten" requires the ability to delete personal data on request — all three solutions support message deletion. HIPAA requires 6-year retention of certain communications — MailPiler's retention policies can enforce this automatically. However, compliance also requires documented procedures, access controls, and audit logging — the software alone does not make you compliant.

### Can I migrate from a commercial archiving service to a self-hosted solution?

Yes. MailPiler supports importing EML and PST files, which are the standard export formats from commercial services like Mimecast, Barracuda, and Google Vault. You can export from your current provider and import into MailPiler's archive store. Dovecot's `doveadm import` command also supports Maildir and mbox formats. Plan for sufficient storage during the migration period, as you'll need space for both the old and new archives simultaneously.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Email Archiving 2026: MailPiler vs Dovecot vs Stalwart",
  "description": "Compare self-hosted email archiving solutions in 2026: MailPiler, Dovecot archiving plugin, and Stalwart Mail Server. Complete Docker setups and deployment guides for regulatory-compliant email retention.",
  "datePublished": "2026-04-18",
  "dateModified": "2026-04-18",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>
