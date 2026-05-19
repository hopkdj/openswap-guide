---
title: "Self-Hosted IMAP Servers — Dovecot vs Cyrus IMAP vs Courier IMAP"
date: "2026-05-19"
tags: ["email", "imap", "mail-server", "self-hosted", "dovecot"]
draft: false
---

The IMAP (Internet Message Access Protocol) server is the backbone of any self-hosted email infrastructure. It stores mailboxes, handles client connections, manages access control lists, and provides the interface through which email clients like Thunderbird, Outlook, or mobile apps retrieve messages. Choosing the right IMAP server impacts performance, scalability, and the features available to your users.

This guide compares three mature, open-source IMAP server implementations: **Dovecot**, **Cyrus IMAP**, and **Courier IMAP**. Each has a different architecture, feature set, and operational profile suited to different deployment scales.

## Quick Comparison

| Feature | Dovecot | Cyrus IMAP | Courier IMAP |
|---------|---------|------------|--------------|
| GitHub Stars | 1,204 | 632 | N/A (SourceForge) |
| Development Status | Very Active | Active | Maintenance |
| Storage Format | Maildir, mbox | Cyrus native (skiplist) | Maildir, Maildir++ |
| Virtual Users | Yes (SQL, LDAP, PAM) | Yes ( Cyrus DB) | Yes (authlib) |
| Sieve Support | Yes (built-in) | Yes (built-in) | No |
| Full-Text Search | Yes (FTS plugins) | Yes (built-in) | No |
| Replication | Yes (dsync) | Yes (Murder/sync) | No |
| Clustering | Yes (director) | Yes (Murder) | No |
| JMAP Protocol | Yes (experimental) | Yes (production) | No |
| LMTP Support | Yes | Yes | No |
| Quota Support | Yes | Yes | Yes |
| ACL Support | Yes | Yes | No |
| License | MIT/LGPL-2.1 | BSD | GPL |

## Dovecot — The Modern IMAP Standard

**Dovecot** is the most widely deployed open-source IMAP server in production today. It powers mail systems for millions of users worldwide and is the default IMAP server in most Linux distributions.

### Installation

```bash
# Debian/Ubuntu
sudo apt install dovecot-core dovecot-imapd dovecot-lmtpd dovecot-sieve dovecot-managesieved

# RHEL/CentOS
sudo dnf install dovecot

# Docker
docker run -d --name dovecot   -p 143:143 -p 993:993   -v ./dovecot.conf:/etc/dovecot/dovecot.conf   -v /var/mail:/var/mail   docker.io/dovecot/dovecot:latest
```

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  dovecot:
    image: docker.io/dovecot/dovecot:latest
    container_name: dovecot
    ports:
      - "143:143"
      - "993:993"
      - "4190:4190"
    volumes:
      - ./config/dovecot:/etc/dovecot:ro
      - ./mail:/var/mail:rw
      - ./ssl:/etc/ssl:ro
    environment:
      - DOVECOT_HOSTNAME=mail.example.com
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "dovecot", "stats"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Key Configuration

```conf
# /etc/dovecot/dovecot.conf
protocols = imap lmtp sieve
listen = *, ::

# Mail location
mail_location = maildir:/var/mail/%d/%n

# Authentication
passdb {
  driver = sql
  args = /etc/dovecot/dovecot-sql.conf.ext
}

userdb {
  driver = sql
  args = /etc/dovecot/dovecot-sql.conf.ext
}

# Sieve for server-side filtering
plugin {
  sieve = file:~/sieve;active=~/.dovecot.sieve
  sieve_before = /var/lib/dovecot/sieve/before/
}

# Full-text search with Solr
plugin {
  fts = solr
  fts_solr = url=http://localhost:8983/solr/dovecot
}
```

### Key Features

- **Sieve filtering**: Server-side email filtering with the Sieve language, supporting rules, vacation responders, and automatic sorting
- **Full-text search**: Pluggable FTS backends (Solr, Elasticsearch, Lucene) for fast message body searches
- **Replication**: Real-time mailbox replication between servers using dsync, enabling high availability
- **Director**: Built-in load balancer that routes users to the same backend server consistently
- **JMAP support**: Experimental but functional JMAP (JSON Meta Application Protocol) for modern client access

## Cyrus IMAP — The Enterprise Choice

**Cyrus IMAP** is designed for large-scale deployments. Its native storage format and architecture are optimized for servers handling hundreds of thousands of mailboxes with strict consistency guarantees.

### Installation

```bash
# Debian/Ubuntu
sudo apt install cyrus-imapd cyrus-admin

# Docker Compose
cat > docker-compose.yml << 'EOF'
version: "3.8"
services:
  cyrus:
    image: docker.io/cyrusimap/cyrus-imapd:latest
    ports:
      - "143:143"
      - "993:993"
      - "4190:4190"
    volumes:
      - ./config:/etc/imapd:ro
      - ./data:/var/lib/imap:rw
      - ./mail:/var/spool/imap:rw
    restart: unless-stopped
EOF
```

### Key Configuration

```conf
# /etc/imapd/imapd.conf
configdirectory: /var/lib/imap
partition-default: /var/spool/imap
sievedir: /var/lib/imap/sieve
admins: cyrus admin

# Authentication
sasl_pwcheck_method: saslauthd
sasl_mech_list: PLAIN LOGIN

# Mailbox settings
defaultpartition: default
virtdomains: yes
unixhierarchysep: yes

# Quotas
quotawarn: 90
quotawarnscript: /usr/local/bin/quota_warn

# TLS
tls_cert_file: /etc/ssl/certs/server.pem
tls_key_file: /etc/ssl/private/server.key
```

### Key Features

- **Native storage format**: Cyrus uses its own skiplist-based storage, optimized for high IOPS and concurrent access
- **Murder clustering**: Native distributed architecture for multi-server deployments with automatic mailbox distribution
- **JMAP production support**: Full JMAP protocol implementation for modern email clients
- **Sieve with CalDAV/CardDAV**: Unified messaging, calendar, and contacts server in a single platform
- **Strict consistency**: ACID-compliant operations ensure no message loss even during crashes

## Courier IMAP — The Lightweight Alternative

**Courier IMAP** is one of the oldest open-source IMAP implementations. While no longer in active development, it remains in use in legacy systems and smaller deployments where simplicity is valued over advanced features.

### Installation

```bash
# Debian/Ubuntu
sudo apt install courier-imap courier-authlib courier-authlib-mysql

# Installation requires courier-authlib as a dependency
# The authentication library provides user backend support
```

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  courier-imap:
    image: lscr.io/linuxserver/courier:latest
    ports:
      - "143:143"
      - "993:993"
    volumes:
      - ./config:/config:rw
      - ./mail:/mail:rw
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    restart: unless-stopped
```

### Key Features

- **Maildir++ format**: Extended Maildir supporting subfolders within the Maildir structure
- **Simple architecture**: Single-process-per-connection model that is easy to understand and debug
- **Shared folders**: Support for shared mailboxes between users (limited compared to Dovecot/Cyrus)
- **Courier authentication library**: Pluggable authentication supporting MySQL, PostgreSQL, LDAP, and PAM

## Why Self-Host Your IMAP Server?

Running your own IMAP server means your email never leaves your infrastructure. Cloud email providers scan message contents for advertising, enforce their own retention policies, and can suspend accounts at their discretion. With a self-hosted IMAP server, you control access, retention, and data handling policies entirely.

Privacy and regulatory compliance are critical drivers. GDPR requires data controllers to know where personal data is stored and processed. When you self-host, every email byte resides on hardware you own or lease, with audit logs you control. This eliminates the data processing agreements and cross-border transfer complications inherent in using third-party email services.

Cost efficiency scales dramatically with user count. Commercial email hosting typically charges $3-10 per user per month. For a 50-user organization, that is $1,800-6,000 annually. A self-hosted IMAP server on a $20/month VPS handles that load with room to grow, paying for itself within the first month.

For organizations building a complete email infrastructure, the IMAP server sits alongside other critical components. Our [email archiving comparison](../2026-04-18-self-hosted-email-archiving-mailpiler-dovecot-stalwart-guide-2026/) covers archive solutions that work with all three IMAP servers, while our [MTA guide](../2026-04-29-postfix-vs-exim-self-hosted-mta-comparison-guide-2026/) explains how to configure the mail delivery layer. For migrating between IMAP servers, our [IMAP synchronization article](../2026-05-10-self-hosted-imap-synchronization-migration-imapsync-offlineimap3-dovecot-dsync/) provides detailed migration procedures.

## Choosing the Right IMAP Server

**Choose Dovecot if:** You need the best overall feature set, Sieve filtering, or are building a new deployment from scratch. Dovecot is the default choice for most self-hosted email setups due to its active development, excellent documentation, and broad protocol support.

**Choose Cyrus IMAP if:** You operate at enterprise scale with hundreds of thousands of mailboxes, need JMAP for modern client access, or require strict ACID guarantees for message storage. Cyrus is the choice of ISPs and large hosting providers.

**Choose Courier IMAP if:** You are maintaining a legacy system that already uses Courier, or have specific compatibility requirements with older mail clients. For new deployments, Dovecot or Cyrus are strongly recommended.

## FAQ

### Can Dovecot handle millions of mailboxes?

Yes. Dovecot's director-based architecture and dsync replication enable horizontal scaling across multiple backend servers. Large hosting providers run Dovecot clusters handling millions of mailboxes with sub-second login times.

### Does Cyrus IMAP work with standard Maildir format?

No. Cyrus uses its own native storage format (skiplist-based), not Maildir. This is a deliberate design choice for performance and consistency. Migration from or to Maildir requires conversion tools like `mb2md` or `mb2md-rh`.

### Which IMAP server supports server-side filtering?

Dovecot and Cyrus IMAP both support Sieve filtering. Courier IMAP does not support Sieve — users must configure client-side filtering rules instead. Sieve is important because it processes mail before the client retrieves it, enabling automatic sorting, spam handling, and vacation responses.

### How do I migrate mailboxes between IMAP servers?

The `imapsync` tool is the standard approach for mailbox migration between any IMAP servers. It connects to both source and destination servers via IMAP and copies messages while preserving flags, folder structure, and timestamps. For Dovecot-to-Dovecot migration, `dsync` provides faster, native replication.

### Do these servers support mobile push notifications?

None of these servers implement push natively over IMAP (IDLE is the closest IMAP equivalent). For true push notifications on mobile devices, consider running a JMAP-capable server (Cyrus has production JMAP support) or using a synchronization bridge like `zpush` for Exchange ActiveSync compatibility.

### What is the performance difference between the three?

For small deployments (under 1,000 users), all three perform similarly. At scale (10,000+ users), Cyrus IMAP generally leads in raw I/O performance due to its native storage format, while Dovecot excels in feature-rich deployments where Sieve, FTS, and replication are needed. Courier IMAP does not scale well beyond a few hundred concurrent users.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted IMAP Servers — Dovecot vs Cyrus IMAP vs Courier IMAP",
  "description": "Compare three open-source IMAP server implementations: Dovecot, Cyrus IMAP, and Courier IMAP. Learn which is best for your self-hosted email infrastructure.",
  "datePublished": "2026-05-19",
  "dateModified": "2026-05-19",
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
