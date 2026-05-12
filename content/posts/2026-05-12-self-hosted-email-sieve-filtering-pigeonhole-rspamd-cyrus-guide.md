---
title: "Self-Hosted Email Sieve Filtering: Pigeonhole vs Rspamd Sieve vs Cyrus Sieve"
date: "2026-05-12"
tags: ["email", "comparison", "guide", "self-hosted", "sieve", "dovecot", "rspamd"]
draft: false
---

Email filtering is a critical component of any self-hosted mail infrastructure. While spam filters like Rspamd and SpamAssassin handle the initial wave of unwanted messages, the [Sieve](https://en.wikipedia.org/wiki/Sieve_(mail_filtering_language)) filtering language provides a standardized, server-side mechanism for organizing, tagging, redirecting, and manipulating email after delivery. Sieve scripts run on the IMAP/LDA server, enabling users to create sophisticated rules for sorting newsletters into folders, auto-forwarding critical messages, rejecting specific senders, and much more — all without relying on client-side filtering.

In this guide, we compare three of the most widely used Sieve implementations for self-hosted environments: **Dovecot Pigeonhole**, **Rspamd Sieve integration**, and **Cyrus IMAP Sieve**. Each takes a different approach to Sieve filtering, from full-featured plugins to lightweight interpreters and deep integrations.

## What Is Sieve Filtering?

Sieve is an IETF-standardized email filtering language (RFC 5228) that runs on the mail server, not the client. Unlike client-side filters (which require the mail client to be running), Sieve scripts execute during message delivery, making them ideal for:

- **Automatic folder sorting** — newsletters, promotions, and transactional emails go to their own folders
- **Auto-replies and vacations** — out-of-office responses sent server-side
- **Header manipulation** — add custom headers, rewrite subjects, or tag messages
- **Redirect and forward** — route specific messages to alternate addresses
- **Reject and discard** — block unwanted senders before they reach the inbox
- **Include and extension support** — use `fileinto`, `vacation`, `envelope`, `regex`, and more

Sieve is supported by most modern mail servers, but the quality of the implementation varies significantly. Let's compare the three leading options.

## Dovecot Pigeonhole

Pigeonhole is the official Sieve plugin for [Dovecot](https://dovecot.org/), the world's most popular open-source IMAP server. It integrates directly with Dovecot's Local Delivery Agent (LDA) and LMTP server, making Sieve scripts a first-class citizen of the Dovecot ecosystem.

**Key features:**
- Full RFC 5228 compliance plus numerous extensions (`fileinto`, `reject`, `vacation`, `envelope`, `regex`, `subaddress`, `imap4flags`, `editheader`, `vnd.dovecot.*`)
- Per-user and global Sieve scripts
- ManageSieve protocol support for remote script management (RFC 5804)
- Integration with Dovecot's quota, ACL, and full-text search
- Script compilation for fast execution

Dovecot Pigeonhole is the default choice for most self-hosted mail servers that use Dovecot as the IMAP backend, which includes the vast majority of modern mail stack deployments.

### Docker Compose Configuration

```yaml
services:
  dovecot:
    image: dovecot/dovecot:latest
    container_name: dovecot
    restart: unless-stopped
    ports:
      - "143:143"
      - "993:993"
      - "4190:4190"  # ManageSieve
    volumes:
      - ./dovecot/conf:/etc/dovecot
      - ./mail:/var/mail
      - ./sieve:/var/lib/dovecot/sieve
    environment:
      - DOVECOT_HOSTNAME=mail.example.com
```

Dovecot's `90-sieve.conf` configuration:

```conf
plugin {
  sieve = file:~/sieve;active=~/.dovecot.sieve
  sieve_default = /var/lib/dovecot/sieve/default.sieve
  sieve_global_dir = /var/lib/dovecot/sieve/global/
  sieve_before = /var/lib/dovecot/sieve/before.d/
  sieve_after = /var/lib/dovecot/sieve/after.d/
}

protocol sieve {
  managesieve_max_line_length = 65536
  managesieve_implementation_string = Dovecot Pigeonhole
}
```

Sample Sieve script for folder sorting:

```sieve
require ["fileinto", "mailbox", "regex"];

# Sort newsletters
if header :regex "List-Id" ".*newsletter.*" {
  fileinto :create "Newsletters";
  stop;
}

# Tag and file important senders
if address :is "From" "boss@company.com" {
  addflag "\Flagged";
  fileinto :create "Important";
  stop;
}

# Vacation response
require ["vacation"];
vacation :days 7 :subject "Out of Office"
  "I am currently away and will respond upon my return.";
```

## Rspamd Sieve Integration

Rspamd is a high-performance spam filtering system that includes Sieve as part of its action framework. Rather than a standalone Sieve interpreter, Rspamd uses Sieve scripts as **actions** triggered by its scoring engine. When Rspamd assigns a spam score that crosses a threshold, it can apply Sieve actions to rewrite headers, add tags, redirect, or reject messages.

**Key features:**
- Sieve actions triggered by spam score thresholds
- Integration with Rspamd's advanced classification (Bayesian, fuzzy hashes, DNSBL, DKIM, SPF, DMARC)
- Can apply Sieve rules conditionally based on complex scoring
- Works alongside Dovecot Pigeonhole for layered filtering
- Lua scripting for custom actions

Rspamd's Sieve integration is best understood as a **pre-delivery filter** that complements Dovecot's post-delivery Sieve processing. The two can work together: Rspamd handles spam/virus detection and applies initial Sieve actions, while Pigeonhole handles user-defined folder organization.

### Docker Compose Configuration

```yaml
services:
  rspamd:
    image: rspamd/rspamd:latest
    container_name: rspamd
    restart: unless-stopped
    ports:
      - "11332:11332"  # Normal worker
      - "11333:11333"  # Controller (web UI)
      - "11334:11334"  # Redis
    volumes:
      - ./rspamd/conf:/etc/rspamd
      - ./rspamd/lua:/etc/rspamd/lua
      - ./rspamd/data:/var/lib/rspamd
    depends_on:
      - redis

  redis:
    image: redis:alpine
    container_name: rspamd-redis
    restart: unless-stopped
    volumes:
      - redis-data:/data

volumes:
  redis-data:
```

Rspamd local.d/actions.conf for Sieve-based actions:

```conf
reject = 15;
"add_header" = 8;
"rewrite_subject" = 6;
sieve = {
  priority = 5;
  script = <<EOD
    require ["fileinto"];
    if header :contains "X-Spam-Flag" "YES" {
      fileinto :create "Spam";
    }
    if header :contains "X-Rspamd-Action" "sieve" {
      fileinto :create "Rspamd-Filtered";
    }
  EOD;
};
```

## Cyrus IMAP Sieve

Cyrus IMAP is a fully-featured, enterprise-grade mail server with built-in Sieve support. Unlike Dovecot (which requires the Pigeonhole plugin), Cyrus includes Sieve as a core component of its IMAP implementation. Cyrus has been the standard for large-scale institutional email deployments for decades.

**Key features:**
- Sieve built into the core Cyrus IMAP server (no plugin needed)
- Full RFC 5228 compliance with extensive extension support
- Per-user Sieve scripts stored in the Cyrus mailbox database
- ManageSieve support for remote script management
- Deep integration with Cyrus's powerful quota, ACL, and replication systems
- Supports CalDAV and CardDAV alongside email

Cyrus IMAP is best suited for organizations that need a complete mail server solution with Sieve filtering built in. It's more complex to configure than Dovecot but offers enterprise features like replication and multi-domain support.

### Docker Compose Configuration

```yaml
services:
  cyrus:
    image: cyrusimap/cyrus-imapd:latest
    container_name: cyrus-imap
    restart: unless-stopped
    ports:
      - "143:143"
      - "993:993"
      - "2000:2000"  # Sieve (Cyrus uses port 2000 by default)
      - "24:24"     # SMTP (LMTP)
    volumes:
      - ./cyrus/conf:/etc/imapd
      - ./cyrus/mailbox:/var/imap
      - ./cyrus/data:/var/spool/imap
    environment:
      - CYRUS_HOSTNAME=mail.example.com
```

Cyrus Sieve configuration in `imapd.conf`:

```conf
sieve_maxscripts: 50
sieve_maxscriptsize: 512
sieve_extensions: fileinto reject vacation imapflags notify include envelope relational regex subaddress editheader duplicate vnd.cmu.jmap
sieve_default: /etc/imapd/sieve/default.sieve
```

Cyrus Sieve script example:

```sieve
require ["fileinto", "vacation", "imap4flags", "envelope"];

# Auto-file messages from mailing lists
if envelope :detail "To" ["list", "newsletter"] {
  fileinto :create "Lists";
  stop;
}

# Flag messages from VIP senders
if address :contains "From" ["ceo@company.com", "director@company.com"] {
  addflag "\Flagged";
}
```

## Comparison Table

| Feature | Dovecot Pigeonhole | Rspamd Sieve | Cyrus IMAP Sieve |
|---------|-------------------|--------------|------------------|
| **Implementation** | Plugin for Dovecot | Spam filter action | Built-in core feature |
| **RFC 5228 Compliance** | Full | Partial (action-based) | Full |
| **ManageSieve (RFC 5804)** | Yes | No | Yes |
| **Per-User Scripts** | Yes | No (system-wide) | Yes |
| **Vacation Extension** | Yes | No | Yes |
| **Regex Support** | Yes | Yes (via Lua) | Yes |
| **Spam Integration** | Separate (works with Rspamd) | Native (core feature) | Separate |
| **Container Image** | dovecot/dovecot | rspamd/rspamd | cyrusimap/cyrus-imapd |
| **Setup Complexity** | Low | Medium | High |
| **Best For** | Most self-hosted setups | Spam-heavy environments | Enterprise/large-scale |
| **GitHub Stars** | 1,200 (dovecot/core) | 2,450+ | 632+ |

## Choosing the Right Sieve Implementation

**Choose Dovecot Pigeonhole if:**
- You already use Dovecot as your IMAP server (most common setup)
- You need ManageSieve for remote script management via email clients like Thunderbird
- You want per-user scripts with global defaults
- You need the widest extension support in the self-hosted space

**Choose Rspamd Sieve if:**
- Your primary concern is spam and phishing detection
- You want Sieve actions triggered by dynamic spam scores
- You need Lua scripting for custom filtering logic
- You're running Rspamd as your spam filter anyway and want to leverage its action framework

**Choose Cyrus IMAP Sieve if:**
- You need a complete enterprise mail server with Sieve built in
- You require multi-domain hosting and mailbox replication
- You want the most mature, battle-tested Sieve implementation
- You're deploying for an organization with hundreds or thousands of mailboxes

## Why Self-Host Email Sieve Filtering?

Self-hosting your email filtering infrastructure gives you complete control over how messages are processed, sorted, and delivered. When you rely on cloud-based email providers (Gmail, Outlook.com, etc.), your filtering rules are at the mercy of their policies, rate limits, and feature availability. With self-hosted Sieve filtering:

**Data sovereignty and privacy**: Your email filtering rules and the messages they process never leave your server. This is critical for organizations handling sensitive communications — legal firms, healthcare providers, and government agencies all benefit from keeping filtering logic in-house. Cloud providers often scan email content for advertising or analytics purposes; self-hosting eliminates this entirely.

**No vendor lock-in**: Sieve is an IETF standard (RFC 5228), meaning your scripts work across any compliant server implementation. If you migrate from Dovecot to Cyrus, or from Pigeonhole to a different Sieve interpreter, your scripts remain largely compatible. This is in stark contrast to proprietary filter languages used by Gmail or Outlook, which lock you into their ecosystems.

**Performance at scale**: Sieve scripts execute during the mail delivery process, before messages are written to disk. This is significantly faster than client-side filtering, which requires downloading messages and then running filter rules locally. For mail servers handling thousands of messages per hour, server-side Sieve filtering reduces bandwidth and improves delivery times.

**Customization without limits**: Cloud email providers impose strict limits on filter rules (Gmail allows 20 filters per account). With self-hosted Sieve, you can create unlimited scripts, use complex regex patterns, and chain multiple conditions together. For power users managing dozens of mailing lists, newsletters, and automated notifications, this flexibility is essential.

For setting up a complete self-hosted mail server, see our [MTA comparison guide](../2026-04-18-maddy-vs-chasquid-vs-opensmtpd-lightweight-smtp-servers/). If you need spam filtering to complement your Sieve rules, our [SpamAssassin vs Rspamd vs Amavis comparison](../2026-04-26-spamassassin-vs-rspamd-vs-amavis-self-hosted-spam-filtering-guide/) covers the top options. For mail server administration, check our [PostfixAdmin vs Modoboa vs iRedAdmin guide](../2026-04-26-postfixadmin-vs-modoboa-vs-iredadmin-self-hosted-mail-admin-guide/).

## FAQ

### What is Sieve email filtering?
Sieve is a standardized email filtering language (RFC 5228) that runs on the mail server during message delivery. It allows you to create rules for sorting, tagging, forwarding, rejecting, and manipulating email messages without requiring a mail client to be running. Sieve scripts are stored on the server and execute automatically when new mail arrives.

### Can Sieve replace spam filters like Rspamd?
No. Sieve and spam filters serve different purposes. Spam filters (Rspamd, SpamAssassin) analyze message content, headers, and reputation to detect unwanted mail. Sieve applies rules based on message headers, sender addresses, and content patterns. They work best together: use a spam filter to score and classify messages, then use Sieve to organize them into folders based on those scores.

### Do I need ManageSieve?
ManageSieve (RFC 5804) is a protocol that allows email clients like Thunderbird, Roundcube, and SquirrelMail to manage Sieve scripts remotely. If you want users to create and edit their own filter rules through a web interface or desktop client, you need ManageSieve support. Dovecot Pigeonhole and Cyrus IMAP both support ManageSieve. Without it, users must edit scripts directly on the server.

### Which Sieve implementation is best for a home server?
For most home and small office setups, **Dovecot Pigeonhole** is the best choice. It's the most widely used, has the best documentation, integrates seamlessly with Dovecot IMAP (which is already the most popular IMAP server), and supports the widest range of Sieve extensions. The ManageSieve support means users can manage their own filter rules through Roundcube or Thunderbird.

### Can I use Sieve with Gmail or other cloud providers?
Gmail does not support server-side Sieve filtering. It uses its own proprietary filter system. If you're self-hosting mail with Dovecot, Cyrus, or similar servers, Sieve is available. For cloud providers that support Sieve, check their documentation — some providers like Fastmail offer Sieve scripting through their web interface.

### How do I debug Sieve scripts?
Most Sieve implementations provide debugging tools. Dovecot Pigeonhole has `sieve_trace` and logs compilation errors to the mail log. You can also use `sievec` to compile scripts manually and check for syntax errors. Rspamd logs Sieve action execution in its worker logs. Cyrus IMAP provides `sieve_test` for script validation. Always test scripts with sample messages before deploying them to production.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Email Sieve Filtering: Pigeonhole vs Rspamd Sieve vs Cyrus Sieve",
  "description": "Compare three leading Sieve email filtering implementations for self-hosted mail servers: Dovecot Pigeonhole, Rspamd Sieve integration, and Cyrus IMAP Sieve.",
  "datePublished": "2026-05-12",
  "dateModified": "2026-05-12",
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
