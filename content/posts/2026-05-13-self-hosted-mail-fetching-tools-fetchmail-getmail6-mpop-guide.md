---
title: "Self-Hosted Mail Fetching Tools: Fetchmail vs Getmail6 vs mpop"
date: "2026-05-13"
tags: ["email", "fetchmail", "getmail", "pop3", "imap"]
draft: false
---

Mail fetching tools retrieve email from remote POP3 or IMAP servers and deliver it to your local mail system. They are essential when you have external email accounts (Gmail, Yahoo, corporate mailboxes) but want to consolidate all mail into a single self-hosted mail server.

This guide compares three self-hosted mail fetching tools: **Fetchmail**, **Getmail6** (the Python 3 continuation of Getmail), and **mpop** (a lightweight POP3 client).

## Overview of Mail Fetching Tools

A mail fetcher connects to remote mail servers, downloads new messages, and hands them off to a local MDA or MTA. This is different from IMAP synchronization tools — fetchers typically pull mail in one direction (remote to local) rather than keeping two mailboxes in sync.

| Feature | Fetchmail | Getmail6 | mpop |
|---------|-----------|----------|------|
| Primary Language | C | Python 3 | C |
| Protocol Support | POP3, IMAP, ETRN, ODMR | POP3, IMAP | POP3 only |
| Active Development | Yes (mature, stable) | Yes (Python 3 fork, 159 stars) | Yes (active) |
| SSL/TLS Support | Yes | Yes | Yes |
| Docker Support | Community images | Community images | Community images |
| Config Syntax | .fetchmailrc (declarative) | .getmailrc (INI-style) | .mpoprc (INI-style) |
| Bounce Detection | Yes (SMTP error parsing) | Yes | Limited |
| Multiple Accounts | Yes | Yes | Yes |
| Maildir Delivery | Yes | Yes | Yes |
| Message Filtering | Via external MDA | Via external MDA | Limited |

## Fetchmail — The Classic Mail Retriever

Fetchmail has been the standard mail retrieval tool on Unix-like systems since 1996. It supports POP3, IMAP, ETRN, and ODMR protocols, making it the most versatile option for fetching mail from diverse remote servers.

### Key Features

- Support for POP3, IMAP, ETRN, and ODMR protocols
- Forwarding to SMTP or local MDA
- Anti-spam features (suppressing loop detection)
- Multi-drop mailbox support (fetching for multiple users from one account)
- Daemon mode for periodic polling

### Docker Compose Configuration

```yaml
version: "3.8"

services:
  fetchmail:
    image: catatnight/postfix:latest
    container_name: fetchmail
    restart: unless-stopped
    volumes:
      - ./fetchmail/fetchmailrc:/etc/fetchmailrc:ro
      - ./fetchmail/log:/var/log/fetchmail
    environment:
      - FETCHMAIL_POLL=300
    command: ["fetchmail", "-f", "/etc/fetchmailrc", "-d", "300", "-v"]
    networks:
      - mailnet

networks:
  mailnet:
    driver: bridge
```

### Fetchmail Configuration

```fetchmailrc
# /etc/fetchmailrc
set syslog
set logfile "/var/log/fetchmail.log"
set daemon 300
set no bouncemail

# Gmail account via IMAP
poll imap.gmail.com protocol IMAP
    user "you@gmail.com" there with password "app-password"
    is localuser here
    ssl
    sslcertck
    sslcertpath /etc/ssl/certs
    mda "/usr/bin/procmail -d %T"
    keep

# Corporate mailbox via POP3
pop mail.corp.com protocol POP3
    user "you@corp.com" there with password "secret"
    is localuser here
    ssl
    fetchall
    mda "/usr/bin/dovecot-lda -d %T"
```

## Getmail6 — Modern Python 3 Mail Retrieval

Getmail6 is the Python 3 continuation of the original Getmail project. It provides a clean INI-style configuration format and supports both POP3 and IMAP retrieval with flexible delivery options.

### Key Features

- Clean INI-style configuration files
- POP3 and IMAP support
- Built-in message filtering and rewriting
- Support for multiple destinations per account
- Python 3 codebase with active maintenance
- MD5 and SSL certificate verification

### Docker Compose Configuration

```yaml
version: "3.8"

services:
  getmail6:
    image: ghcr.io/getmail6/getmail6:latest
    container_name: getmail6
    restart: unless-stopped
    volumes:
      - ./getmail6/getmailrc:/root/.getmail/getmailrc:ro
      - ./getmail6/mail:/var/mail
    environment:
      - GETMAIL_INTERVAL=300
    networks:
      - mailnet

networks:
  mailnet:
    driver: bridge
```

### Getmail6 Configuration

```ini
# /root/.getmail/getmailrc

[retriever]
type = SimpleIMAPSSLRetriever
server = imap.gmail.com
username = you@gmail.com
password = app-password

[destination]
type = Maildir
path = /var/mail/localuser/

[options]
read_all = false
delivered_to = false
received = false
verbose = 2
message_log = /var/log/getmail.log
```

For multiple accounts, create separate `.getmailrc` files and use getmail6's `--rcfile` option.

## mpop — Lightweight POP3 Client

mpop is a small, fast POP3 mail retriever written in C. It focuses on simplicity and speed, making it ideal for systems where you only need POP3 fetching without IMAP complexity.

### Key Features

- Minimal resource footprint
- Fast POP3 retrieval
- TLS/STARTTLS support
- Multiple account support
- Maildir and mbox delivery
- Simple INI-style configuration

### Docker Compose Configuration

```yaml
version: "3.8"

services:
  mpop:
    image: alpine:latest
    container_name: mpop
    restart: unless-stopped
    volumes:
      - ./mpop/mpoprc:/etc/mpoprc:ro
      - ./mpop/mail:/var/mail
    command: ["mpop", "-d"]
    networks:
      - mailnet

networks:
  mailnet:
    driver: bridge
```

### mpop Configuration

```ini
# /etc/mpoprc

defaults
    tls on
    tls_starttls on
    delivery maildir "/var/mail/%u/"

account gmail
    host imap.gmail.com
    port 995
    user "you@gmail.com"
    password "app-password"
    tls on
    delivery mda "/usr/bin/procmail -d %T"

account corporate
    host mail.corp.com
    port 995
    user "you@corp.com"
    password "secret"
    tls on
    delivery mda "/usr/sbin/dovecot-lda -d %T"
```

## Why Self-Host Your Own Mail Fetching?

Using a self-hosted mail fetcher gives you complete control over how external email enters your infrastructure. Rather than relying on your email provider's web interface or mobile app, you can consolidate all mail into a single mailbox that you fully control.

This is especially valuable for organizations that use multiple email providers — different departments, acquired companies, or personal accounts used for business. A mail fetcher pulls everything into one place where unified filtering, archiving, and backup policies can be applied.

For email archiving, see our [complete email archiving guide](../2026-04-18-self-hosted-email-archiving-mailpiler-dovecot-stalwart-guide-2026/). For IMAP synchronization between servers, our [IMAP migration guide](../2026-05-10-self-hosted-imap-synchronization-migration-imapsync-offlineimap3-dovecot-dsync/) covers bidirectional sync tools. If you need SMTP relay capabilities, check our [SMTP relay comparison](../2026-04-26-postal-vs-stalwart-vs-haraka-self-hosted-smtp-relay-guide-2026/).

### Security Best Practices

- Always use TLS/SSL connections to remote mail servers
- Store passwords in separate credential files with restricted permissions (chmod 600)
- Use application-specific passwords when available (e.g., Google App Passwords)
- Configure `sslcertck` in Fetchmail to verify server certificates
- Run the fetcher under a dedicated, unprivileged user account
- Monitor logs for authentication failures and connection errors

## Choosing the Right Mail Fetcher

| Use Case | Recommended Tool | Reason |
|----------|-----------------|--------|
| IMAP + POP3 from many providers | Fetchmail | Broadest protocol support |
| Python-based setup, easy config | Getmail6 | Clean INI format, active Python 3 development |
| POP3-only, minimal footprint | mpop | Small, fast, simple configuration |
| Multi-drop mailbox | Fetchmail | Built-in multi-drop support |
| Docker-native deployment | Getmail6 | Available on GHCR with maintained images |
| Legacy system compatibility | Fetchmail | Installed on virtually all Unix systems |


### When to Choose Each Tool

**Choose Fetchmail when:**
- You need to fetch from both POP3 and IMAP servers in the same configuration
- You are managing multi-drop mailboxes where one remote account delivers to multiple local users
- You need ETRN or ODMR protocol support for on-demand mail queue processing
- You want the most battle-tested mail fetcher with decades of production use

**Choose Getmail6 when:**
- You prefer a clean, readable INI-style configuration over Fetchmail's declarative syntax
- You are deploying in a Docker environment and want a maintained Python 3 container image
- You need built-in message filtering and header rewriting capabilities
- You are migrating from Getmail 4 or 5 and want a drop-in Python 3 replacement

**Choose mpop when:**
- You only need POP3 retrieval and want the smallest possible footprint
- You are running on resource-constrained hardware (embedded systems, low-memory VPS)
- You prefer a statically compiled C binary over a Python runtime dependency
- You need a simple, single-purpose tool without the complexity of IMAP support

## FAQ

### What is the difference between mail fetching and IMAP synchronization?

Mail fetching tools (Fetchmail, Getmail6, mpop) pull messages from a remote server to a local mailbox in one direction. IMAP synchronization tools (like imapsync or OfflineIMAP3) keep two mailboxes in sync bidirectionally — changes on either side are reflected on the other. Use fetchers to consolidate external mail; use sync tools for mailbox migration or backup.

### Does Fetchmail support OAuth2 authentication?

Modern versions of Fetchmail support OAuth2 authentication for services that require it, including Gmail and Microsoft 365. This requires configuring an OAuth2 client ID and refresh token. Application-specific passwords are a simpler alternative for most use cases.

### Can I use Getmail6 with Gmail?

Yes. Getmail6 supports IMAP with SSL, which works with Gmail. You will need to enable IMAP in your Gmail settings and use an application-specific password rather than your regular account password.

### Is mpop suitable for production use?

mpop is well-suited for production environments where you only need POP3 retrieval. It is small, stable, and has been in use for many years. However, if you need IMAP support, choose Fetchmail or Getmail6 instead.

### How often should I poll for new mail?

A polling interval of 300 seconds (5 minutes) is a good balance between timeliness and server load. Most providers do not rate-limit reasonable polling intervals. Avoid intervals shorter than 60 seconds to prevent triggering abuse detection.

### Can I run multiple mail fetchers simultaneously?

Yes, but each fetcher should be configured to handle different accounts or use locking to prevent conflicts. Running two fetchers against the same account can result in duplicate deliveries or missed messages.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Mail Fetching Tools: Fetchmail vs Getmail6 vs mpop",
  "description": "Compare three self-hosted mail fetching tools for consolidating external email: Fetchmail with broad protocol support, Getmail6 with Python 3 and clean configuration, and mpop for lightweight POP3 retrieval. Includes Docker configs.",
  "datePublished": "2026-05-13",
  "dateModified": "2026-05-13",
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
