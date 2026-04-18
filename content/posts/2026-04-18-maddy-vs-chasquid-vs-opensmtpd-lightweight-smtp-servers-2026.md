---
title: "Maddy vs Chasquid vs OpenSMTPD: Best Lightweight Self-Hosted SMTP Servers 2026"
date: 2026-04-18
tags: ["comparison", "guide", "self-hosted", "email"]
draft: false
description: "Compare three lightweight SMTP server alternatives — Maddy, Chasquid, and OpenSMTPD — to Postfix and Exim. Includes Docker setup, configuration examples, and deployment guides for 2026."
---

Running your own mail server has traditionally meant wrestling with Postfix or Exim — powerful but notoriously complex tools with decades of accumulated configuration options. If you've ever lost an afternoon debugging a `main.cf` or deciphering a cryptic Exim ACL error, you know the pain.

Enter a new generation of lightweight SMTP servers designed from scratch with simplicity, security, and modern deployment patterns in mind. This guide compares three of the best alternatives: **[Maddy](https://maddy.email)**, **[Chasquid](https://blitiri.com.ar/p/chasquid/)**, and **[OpenSMTPD](https://opensmtpd.org/)**.

## Why Choose a Lightweight SMTP Server?

Postfix handles roughly 75% of the world's email traffic. It's battle-tested, incredibly flexible, and can handle virtually any mail routing scenario. But that flexibility comes at a cost:

- **Configuration complexity**: Postfix ships with 300+ configuration parameters. Even a minimal working setup requires careful tuning.
- **Security surface**: Decades of code means decades of edge cases. Hardening Postfix for production takes significant expertise.
- **Docker unfriendly**: Postfix was designed as a system daemon, not a containerized microservice. Running it in Docker often means wrestling with multiple daemons and stateful volumes.
- **Overkill for small deployments**: If you're running email for a handful of domains or a single application, Postfix is like using a sledgehammer to hang a picture.

Lightweight SMTP servers address these problems by:

- Providing sane defaults that work out of the box
- Using modern programming languages (Go, C) with smaller codebases
- Supporting container-native deployment patterns
- Focusing on the common use cases rather than every possible edge case

## Maddy: The All-in-One Mail Server

**GitHub**: [foxcpp/maddy](https://github.com/foxcpp/maddy) | **Stars**: 5,935 | **Language**: Go | **Last Updated**: April 2026

Maddy takes a radically different approach from traditional MTAs. Instead of being "just an SMTP server," it aims to be a complete mail server in a single binary. Maddy handles:

- SMTP (incoming and outgoing)
- IMAP (mailbox access)
- DNS records (DKIM, SPF, DMARC validation)
- TLS certificate management (ACME/Let's Encrypt integration)
- Virtual user domains

### Architecture

Maddy uses a modular pipeline architecture. Each module handles one concern — authentication, storage, DKIM signing — and you compose them in a unified configuration file. This makes it easy to understand exactly what your server does.

```conf
# Minimal maddy.conf - incoming mail with DKIM validation
$(hostname) = mail.example.com
$(primary_domain) = example.com

# TLS configuration (auto-managed via ACME)
tls file:///etc/maddy/tls/$(hostname)-fullchain.pem \
    file:///etc/maddy/tls/$(hostname)-privkey.pem

# SMTP listener - accepts mail on port 25
smtp tcp://0.0.0.0:25 {
    hostname $(hostname)

    # Validate incoming mail
    check {
        require tls
        require spf
        require dkim
    }

    # Store mail in local mailboxes
    deliver_to &mailboxes
}

# Mailbox storage
local_mailboxes mailboxes {
    path /var/lib/maddy/mailboxes
}
```

### Docker Deployment

Maddy ships with an official Dockerfile and a Docker-specific configuration template. Here's a production-ready Docker Compose setup:

```yaml
services:
  maddy:
    image: ghcr.io/foxcpp/maddy:latest
    container_name: maddy
    restart: unless-stopped
    ports:
      - "25:25"    # SMTP
      - "143:143"  # IMAP
      - "993:993"  # IMAPS
      - "587:587"  # Submission
    volumes:
      - ./config:/etc/maddy
      - ./data:/var/lib/maddy
      - ./tls:/etc/maddy/tls
    environment:
      - MADDY_HOSTNAME=mail.example.com
      - MADDY_DOMAIN=example.com
    networks:
      - mailnet

networks:
  mailnet:
    driver: bridge
```

### Key Features

| Feature | Details |
|---------|---------|
| Protocol | SMTP, IMAP, LMTP |
| Language | Go (single binary, no external dependencies) |
| Storage | Local mailbox (Maildir), SQLite for metadata |
| TLS | ACME/Let's Encrypt auto-renewal |
| Auth | Integrated credentials management |
| DKIM | Automatic signing and verification |
| Docker | Official image with Docker-specific config |
| License | LGPL-3.0 |

### When to Choose Maddy

- You want a **complete mail server** in one binary — SMTP + IMAP + DKIM + ACME
- You're deploying with Docker and want something designed for it
- You prefer Go-based tools with clean configuration syntax
- You need virtual domain hosting without the Postfix virtual-mailbox complexity

## Chasquid: Simplicity and Security First

**GitHub**: [albertito/chasquid](https://github.com/albertito/chasquid) | **Stars**: 962 | **Language**: Go | **Last Updated**: April 2026

Chasquid was built with a clear philosophy: do SMTP well, do it securely, and make it hard to misconfigure. It handles only SMTP — no IMAP, no POP3 — and integrates cleanly with Dovecot for mailbox storage and authentication.

### Architecture

Chasquid is intentionally narrow in scope. It focuses on being the best possible SMTP server and delegates everything else to specialized tools:

- **Dovecot** for authentication (SASL) and mailbox delivery (LMTP)
- **systemd** or supervisor for process management
- Standard Linux tooling for TLS certificates

This separation of concerns means each component does exactly what it's designed for.

```conf
# /etc/chasquid/chasquid.conf

# Listening addresses
smtp_address: ":25"
submission_address: ":587"
submission_over_tls_address: ":465"

# Monitoring endpoint (localhost only)
monitoring_address: "127.0.0.1:1099"

# Authenticate via Dovecot
dovecot_auth: true

# Deliver mail via LMTP to Dovecot
mail_delivery_agent_bin: "/usr/bin/mda-lmtp"
mail_delivery_agent_args: "--addr"
mail_delivery_agent_args: "/run/dovecot/lmtp"
mail_delivery_agent_args: "-f"
mail_delivery_agent_args: "%from%"
mail_delivery_agent_args: "-d"
mail_delivery_agent_args: "%to%"

# Data storage
data_dir: "/var/lib/chasquid/data"
mail_log_path: "/var/lib/chasquid/mail.log"
```

### Docker Deployment

Chasquid provides an experimental Docker setup in its `docker/` directory. The image pairs Chasquid with Dovecot using supervisord:

```yaml
services:
  chasquid:
    build:
      context: .
      dockerfile: https://raw.githubusercontent.com/albertito/chasquid/master/docker/Dockerfile
    container_name: chasquid
    restart: unless-stopped
    ports:
      - "25:25"
      - "587:587"
      - "465:465"
    volumes:
      - ./chasquid-data:/data/chasquid
      - ./dovecot-data:/var/mail
      - ./certs:/etc/ssl/certs
    environment:
      - TZ=UTC
    networks:
      - mailnet

networks:
  mailnet:
    driver: bridge
```

For production use, the Chasquid documentation recommends native installation over Docker. The Docker setup is labeled as experimental.

### Installation on Debian/Ubuntu

```bash
# Install from Debian/Ubuntu repos
sudo apt update
sudo apt install chasquid dovecot-imapd dovecot-lmtpd

# Enable and start
sudo systemctl enable chasquid
sudo systemctl start chasquid

# Verify it's listening
sudo ss -tlnp | grep chasquid
```

### Key Features

| Feature | Details |
|---------|---------|
| Protocol | SMTP only (delegates IMAP to Dovecot) |
| Language | Go (single binary) |
| Storage | Delegates to Dovecot (Maildir, mdbox) |
| TLS | Standard certificate files, no built-in ACME |
| Auth | Dovecot SASL |
| Monitoring | HTTP metrics endpoint |
| Docker | Experimental (Debian + Dovecot + supervisord) |
| License | Apache 2.0 |

### When to Choose Chasquid

- You want a **focused SMTP server** without the bloat of a full mail suite
- You already run Dovecot and want a clean MTA replacement for Postfix
- Security and simplicity are your top priorities
- You prefer native installation over containerized deployment

## OpenSMTPD: The OpenBSD Approach

**GitHub**: [OpenSMTPD/OpenSMTPD](https://github.com/OpenSMTPD/OpenSMTPD) | **Stars**: 568 | **Language**: C | **Last Updated**: March 2026

OpenSMTPD is the SMTP server from the OpenBSD project, known for its clean code, strong security auditing, and readable configuration syntax. It originated as the default mail server in OpenBSD but has a portable version that runs on Linux, FreeBSD, and other systems.

### Philosophy

OpenSMTPD inherits OpenBSD's design principles:

- **Readable configuration**: The config file reads almost like English
- **Minimal attack surface**: The codebase is actively security-audited
- **Principle of least privilege**: Each component runs with minimal permissions
- **Sensible defaults**: Works correctly with minimal configuration

### Configuration

OpenSMTPD's configuration is famously clean. Here's a typical setup:

```conf
# /etc/smtpd.conf

# Table definitions
table aliases file:/etc/mail/aliases
table virtuals file:/etc/mail/virtuals
table secrets file:/etc/mail/secrets

# Listen on all interfaces
listen on eth0 tls pki mail.example.com
listen on eth0 port 587 tls-require pki mail.example.com \
    auth <secrets>

# PKI (TLS certificates)
pki mail.example.com cert "/etc/ssl/mail.example.com.crt"
pki mail.example.com key  "/etc/ssl/private/mail.example.com.key"

# Rules
accept from any for domain "example.com" \
    virtual <virtuals> \
    deliver to maildir "/var/mail/%{dest.user}"

accept from local for any \
    relay via tls+auth://user@smtp.relay.example.com:587 \
    auth <secrets>
```

### Docker Deployment

There is no official Docker image, but the portable version runs well in a container:

```yaml
services:
  opensmtpd:
    image: linuxserver/opensmtpd:latest
    container_name: opensmtpd
    restart: unless-stopped
    ports:
      - "25:25"
      - "587:587"
    volumes:
      - ./config:/config
      - ./mail:/var/mail
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    networks:
      - mailnet

networks:
  mailnet:
    driver: bridge
```

### Key Features

| Feature | Details |
|---------|---------|
| Protocol | SMTP (with relay and filtering) |
| Language | C (security-audited) |
| Storage | Maildir, with support for LMTP delivery |
| TLS | Standard certificate files |
| Auth | Credentials tables (bcrypt) |
| Filtering | Built-in table-based filtering |
| Docker | Community image (LinuxServer.io) |
| License | ISC |

### When to Choose OpenSMTPD

- You value **security auditing** and clean code above all else
- You want the simplest possible configuration syntax
- You're running on OpenBSD or a BSD-family system
- You need a reliable relay MTA with minimal attack surface

## Head-to-Head Comparison

| Feature | Maddy | Chasquid | OpenSMTPD |
|---------|-------|----------|-----------|
| **Language** | Go | Go | C |
| **GitHub Stars** | 5,935 | 962 | 568 |
| **Scope** | Full mail server (SMTP + IMAP) | SMTP only | SMTP only |
| **Config Syntax** | Custom DSL | YAML-like | English-like |
| **Docker Support** | Official image | Experimental | Community (LinuxServer.io) |
| **TLS Management** | Built-in ACME | Manual cert files | Manual cert files |
| **IMAP Support** | Built-in | Via Dovecot | Via Dovecot or other LDA |
| **DKIM** | Built-in signing/verification | Via rspamd or amavis | Via rspamd or dkim-milter |
| **Auth Backend** | Integrated credentials | Dovecot SASL | Credentials tables |
| **Monitoring** | No dedicated endpoint | HTTP metrics | Logs only |
| **License** | LGPL-3.0 | Apache 2.0 | ISC |
| **Best For** | All-in-one Docker deployment | Simple, secure SMTP | Security-audited relay |

## Which One Should You Choose?

### For a complete self-hosted email setup → Maddy

If you want to go from zero to running email with a single Docker Compose file, Maddy is the winner. It handles SMTP, IMAP, DKIM, and TLS certificates without needing any additional services. The unified configuration means you manage one file, not a web of Postfix, Dovecot, rspamd, and certbot configs.

### For a Postfix replacement on an existing Dovecot setup → Chasquid

If you already have Dovecot running for IMAP and just want a simpler, more secure MTA, Chasquid is the natural choice. The Dovecot integration is seamless — authentication, LMTP delivery, and mailbox management all work exactly as before, just with a cleaner SMTP layer.

### For a security-critical relay → OpenSMTPD

If you're deploying on a BSD system or need a relay MTA with the strongest possible security guarantees, OpenSMTPD wins. Its codebase is actively audited by the OpenBSD security team, and the ISC license means zero restrictions on commercial use.

For related reading, see our [complete email server setup guide with Postfix and Dovecot](../self-hosted-email-server-postfix-dovecot-rspamd-complete-guide-2026/) and [email marketing platforms comparison](../self-hosted-email-marketing-listmonk-mautic-postal-guide/) if you need to send bulk email from your mail server.

## FAQ

### Is it safe to self-host an SMTP server in 2026?

Yes, with proper configuration. All three servers in this guide support TLS encryption, SPF/DKIM/DMARC validation, and authentication. The key security requirements are: keep software updated, use strong TLS certificates, configure reverse DNS (PTR records), and set up proper SPF, DKIM, and DMARC DNS records.

### Can these replace Postfix on my existing server?

Chasquid and OpenSMTPD are designed as drop-in Postfix replacements for the SMTP layer. Maddy replaces Postfix entirely since it also includes IMAP and mailbox storage. Note that you'll need to migrate your existing mail queues and reconfigure any applications that send mail through `sendmail` or `postfix` commands.

### Do I need a static IP to self-host email?

Technically no, but practically yes. Many receiving mail servers check the sending IP's reverse DNS (PTR record), which typically requires a static IP. Without it, your mail has a higher chance of being marked as spam. Some ISPs also block port 25 on residential connections.

### Which is easiest to set up with Docker?

Maddy, by a significant margin. It ships with an official Docker image and a Docker-specific configuration template that handles hostname and domain setup via environment variables. Chasquid's Docker setup is labeled experimental, and OpenSMTPD relies on a community-maintained LinuxServer.io image.

### Can I use these as a relay only (not receive mail)?

Yes. All three can be configured as outbound-only relay servers. This is useful for sending notifications from applications without running a full mail server. OpenSMTPD's `relay via` directive and Chasquid's queue-forwarding make this particularly straightforward.

### How do these handle large volumes of email?

For moderate volumes (hundreds to thousands of messages per day), all three perform well. Maddy's Go architecture handles concurrent connections efficiently. Chasquid's queue management is designed for reliability under load. OpenSMTPD has been production-tested on OpenBSD for years. For high-volume sending (10,000+ emails/day), consider a dedicated transactional email service instead.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Maddy vs Chasquid vs OpenSMTPD: Best Lightweight Self-Hosted SMTP Servers 2026",
  "description": "Compare three lightweight SMTP server alternatives — Maddy, Chasquid, and OpenSMTPD — to Postfix and Exim. Includes Docker setup, configuration examples, and deployment guides for 2026.",
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
      "url": "https://hopkdj.github.io/openswap-guide/logo.png"
    }
  }
}
</script>
