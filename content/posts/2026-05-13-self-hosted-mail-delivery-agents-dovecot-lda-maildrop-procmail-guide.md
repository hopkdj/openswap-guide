---
title: "Self-Hosted Mail Delivery Agents: Dovecot LDA vs Maildrop vs Procmail"
date: "2026-05-13"
tags: ["email", "mail-server", "dovecot", "procmail", "maildrop"]
draft: false
---

Mail delivery agents (MDAs) are the final step in the email processing pipeline. After an MTA like Postfix or Exim accepts an incoming message, the MDA takes over — filtering, sorting, and delivering the message to the user's mailbox. Choosing the right MDA affects how you handle spam filtering, auto-sorting, vacation responders, and mailbox format compatibility.

This guide compares three self-hosted MDAs: **Dovecot LDA** (Local Delivery Agent), **Maildrop**, and **Procmail** — covering features, configuration, Docker deployment, and use-case recommendations.

## Overview of Mail Delivery Agents

An MDA sits between the MTA and the mailbox. It receives messages via STDIN (piped from the MTA) or via LMTP (Local Mail Transfer Protocol), applies filtering rules, and writes the message to disk in Maildir or mbox format.

| Feature | Dovecot LDA | Maildrop | Procmail |
|---------|-------------|----------|----------|
| Primary Language | C | C | C |
| Delivery Protocol | LMTP, direct pipe | Pipe from MTA | Pipe from MTA |
| Mailbox Format | Maildir, mbox | Maildir, mbox | Maildir, mbox |
| Sieve Support | Yes (built-in) | No | No |
| Active Development | Yes (1,200+ GitHub stars) | Yes (community forks) | Legacy (unmaintained) |
| Docker Support | Official image | Community images | Community images |
| Config Syntax | Sieve (RFC 5228) | Maildrop filter language | Procmailrc rules |
| Vacation/Auto-reply | Yes (via Sieve) | Via external tools | Via external scripts |
| Quota Support | Yes (native) | Limited | No |

## Dovecot LDA — Modern, Sieve-Powered Delivery

Dovecot LDA is part of the broader Dovecot ecosystem, one of the most widely deployed IMAP/POP3 servers. It integrates seamlessly with Dovecot's Sieve filtering system, making it the most feature-rich option for modern mail setups.

### Key Features

- Native Sieve scripting for filtering, forwarding, and auto-replies
- Built-in quota enforcement
- LMTP protocol support for reliable delivery
- Integration with Dovecot's authentication and user database
- Maildir and mbox format support

### Docker Compose Configuration

```yaml
version: "3.8"

services:
  dovecot:
    image: dovecot/dovecot:latest
    container_name: dovecot-lda
    restart: unless-stopped
    ports:
      - "2424:2424"  # LMTP
      - "143:143"    # IMAP
      - "993:993"    # IMAPS
    volumes:
      - ./dovecot/conf:/etc/dovecot
      - ./dovecot/mail:/var/mail
      - ./dovecot/sieve:/var/lib/dovecot/sieve
    environment:
      - DOVECOT_MAIL_LOCATION=maildir:/var/mail/%u
    networks:
      - mailnet

networks:
  mailnet:
    driver: bridge
```

### Sieve Filter Example

Dovecot's Sieve scripting is standardized and human-readable:

```sieve
require ["fileinto", "reject", "vacation"];

# Move spam to Junk folder
if header :contains "X-Spam-Flag" "YES" {
    fileinto "Junk";
    stop;
}

# Auto-reply for vacation
vacation :days 7
    :subject "Out of Office"
    "I am currently away and will respond when I return.";

# Sort mailing lists
if header :contains "List-Id" "<dev.example.org>" {
    fileinto "Lists.Devel";
}

# Default delivery
keep;
```

### Postfix Integration

Configure Postfix to pipe mail to Dovecot LDA via LMTP:

```
# /etc/postfix/main.cf
mailbox_transport = lmtp:unix:private/dovecot-lmtp
```

## Maildrop — Flexible Filtering with Regex Power

Maildrop is a mail delivery agent with a powerful filtering language based on regular expressions. Originally developed as part of the Courier Mail Server, it has been forked and maintained by the community. It offers fine-grained control over message routing.

### Key Features

- Pattern-matching filter language with full regex support
- Support for external programs in filter rules
- Maildir and mbox delivery
- Carbon copy (Cc) to additional addresses
- Message body inspection capabilities

### Docker Compose Configuration

```yaml
version: "3.8"

services:
  maildrop:
    image: linuxserver/maildrop:latest
    container_name: maildrop
    restart: unless-stopped
    volumes:
      - ./maildrop/filters:/etc/maildrop
      - ./maildrop/mail:/var/mail
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

### Maildrop Filter Example

```maildrop
# /etc/maildroprc

# Log file
logfile "/var/log/maildrop.log"

# Reject messages over 10MB
if ( $SIZE > 10485760 )
{
    echo "Message too large"
    exit 77
}

# Sort by sender
if ( /^From:.*@spam-domain\.com/ )
{
    to "$HOME/Maildir/.Spam/"
}

# CC to archive
if ( /^Subject:.*Invoice/ )
{
    cc "$HOME/Maildir/.Archive/Invoices/"
}

# Default delivery
to "$HOME/Maildir/"
```

## Procmail — The Legacy Standard

Procmail was the dominant MDA for decades. While no longer actively maintained, it remains installed on countless systems and is still referenced in documentation worldwide. Understanding Procmail is valuable for maintaining legacy systems and appreciating the evolution of mail filtering.

### Key Features

- Extremely lightweight and fast
- Powerful recipe-based filtering
- Wide availability on Unix/Linux systems
- Extensive historical documentation
- Compatible with virtually any MTA

### Docker Compose Configuration

```yaml
version: "3.8"

services:
  procmail:
    image: catatnight/postfix:latest
    container_name: procmail-mda
    restart: unless-stopped
    volumes:
      - ./procmail/procmailrc:/etc/procmailrc
      - ./procmail/mail:/var/mail
    environment:
      - MAIL_USER=user@example.com
      - MAIL_PASS=secret
    networks:
      - mailnet

networks:
  mailnet:
    driver: bridge
```

### Procmail Recipe Example

```procmail
# /etc/procmailrc

MAILDIR=$HOME/Maildir
DEFAULT=$MAILDIR/
LOGFILE=/var/log/procmail.log

# Reject large messages
:0
* ^Content-Length:.*[0-9][0-9][0-9][0-9][0-9][0-9][0-9]
/dev/null

# Sort mailing lists
:0:
* ^List-Id:.*dev\.example\.org
.lists.devel/

# Forward urgent mail to mobile
:0 c
* ^Subject:.*URGENT
! mobile@example.com

# Default delivery
:0:
$MAILDIR/
```

## Why Self-Host Your Own Mail Delivery Agent?

Running your own MDA gives you complete control over how incoming mail is processed, filtered, and stored. Cloud email providers apply their own filtering rules, which may miss important messages, misclassify spam, or lack the customization your organization needs.

With a self-hosted MDA, you define exactly which messages get delivered, where they go, and what actions are taken. This is essential for organizations handling sensitive communications, developers managing mailing lists, or anyone who needs precise control over their mail flow. Data ownership is another critical factor — when you control the delivery pipeline, you control the data.

For mail server administration, see our [Postfix mail admin panel comparison](../2026-04-26-postfixadmin-vs-modoboa-vs-iredadmin-self-hosted-mail-admin-guide-2026/). If you need a lightweight SMTP server, our [MTA comparison guide](../2026-04-18-maddy-vs-chasquid-vs-opensmtpd-lightweight-smtp-servers-2026/) covers modern alternatives. For email aliasing and forwarding, check our [email alias guide](../2026-04-20-simplelogin-vs-anonaddy-vs-forwardemail-self-hosted-email-alias-guide-2026/).

### Security Considerations

When running an MDA, follow these security best practices:

- Run the MDA under a dedicated, unprivileged user account
- Use Maildir format instead of mbox to prevent file locking issues
- Enable quota enforcement to prevent disk exhaustion
- Keep filter rules in version control for auditability
- Regularly update the MDA package to patch security vulnerabilities
- Use Sieve (with Dovecot) for standardized, validated filter rules

## Choosing the Right MDA

| Use Case | Recommended MDA | Reason |
|----------|----------------|--------|
| Modern mail server with Sieve | Dovecot LDA | Native Sieve support, active development |
| Custom regex filtering | Maildrop | Powerful pattern matching, flexible rules |
| Legacy system maintenance | Procmail | Widely available, well-documented |
| Multi-user environment | Dovecot LDA | Quota support, user isolation |
| Simple forwarding rules | Procmail | Lightweight, easy recipes |
| High-volume mail processing | Dovecot LDA | LMTP reliability, performance |

## FAQ

### What is the difference between an MTA and an MDA?

An MTA (Mail Transfer Agent) like Postfix or Exim handles routing and delivery of messages between servers over SMTP. An MDA (Mail Delivery Agent) takes the message from the MTA and delivers it to the user's local mailbox, applying filtering and sorting rules along the way. They work together in the mail processing pipeline.

### Does Dovecot LDA support Sieve filtering?

Yes. Dovecot LDA has built-in Sieve support via the Dovecot Sieve plugin (formerly Pigeonhole). Sieve is an RFC-standardized filtering language (RFC 5228) that is easier to write, validate, and manage than Procmail or Maildrop filter syntax. Many MTA implementations can validate Sieve scripts before deploying them.

### Is Procmail still safe to use in 2026?

Procmail has not seen a major release since 2001 and is considered legacy software. While it is still functional and installed on many systems, it lacks modern security hardening and active vulnerability patching. For new deployments, Dovecot LDA or Maildrop are recommended. Procmail is suitable for maintaining existing legacy configurations.

### Can Maildrop handle large messages?

Yes. Maildrop can be configured to reject or redirect messages exceeding a size threshold using the `$SIZE` variable in filter rules. This is useful for preventing mailbox overflow and blocking oversized attachments.

### Which mailbox format should I use: Maildir or mbox?

Maildir is the recommended format for modern deployments. It stores each message as a separate file, eliminating file locking issues and enabling concurrent access. mbox stores all messages in a single file, which can cause performance and corruption problems with high-volume mail servers.

### How do I migrate from Procmail to Dovecot LDA?

Procmail recipes can be translated to Sieve scripts. Tools like `procmail2sieve` exist for automated conversion, though manual review is recommended. The key differences are: Procmail uses regex-based "recipes" while Sieve uses structured conditional blocks. Sieve is more restrictive but also more portable and easier to validate.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Mail Delivery Agents: Dovecot LDA vs Maildrop vs Procmail",
  "description": "Compare three self-hosted mail delivery agents for email filtering and local delivery: Dovecot LDA with Sieve support, Maildrop with regex filtering, and legacy Procmail. Includes Docker Compose configs and migration guides.",
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
