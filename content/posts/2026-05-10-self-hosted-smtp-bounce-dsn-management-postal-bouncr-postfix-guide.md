---
title: "Self-Hosted SMTP Bounce & DSN Management: Postal vs bouncr vs Postfix Bounce Handling"
date: "2026-05-10"
tags: ["email", "smtp", "bounce", "dsn", "postal", "postfix", "mail-server"]
draft: false
---

When email fails to reach its recipient, the receiving server generates a Delivery Status Notification (DSN) — commonly called a "bounce." Managing these bounces effectively is critical for maintaining sender reputation, keeping mailing lists clean, and diagnosing delivery problems.

This guide compares three approaches to self-hosted bounce and DSN management: **Postal** (full mail platform with built-in bounce handling), **bouncr** (dedicated bounce processing microservice), and **Postfix**'s native bounce handling (MTA-level processing).

## Understanding Bounce Types and DSN

Before comparing tools, it's important to understand what bounces are and how they work:

### Hard Bounces vs Soft Bounces

| Type | Cause | SMTP Code | Action |
|------|-------|-----------|--------|
| **Hard bounce** | Permanent failure | 5.x.x | Remove address from list |
| **Soft bounce** | Temporary failure | 4.x.x | Retry, then escalate |
| **Block bounce** | IP/domain blocked | 5.7.1 | Investigate reputation |
| **Mailbox full** | Recipient quota exceeded | 4.2.2 | Retry later |
| **Domain not found** | DNS failure | 5.1.2 | Remove or verify domain |

### DSN Format

Delivery Status Notifications follow RFC 3464 and contain:
- **Original message headers**: What was being delivered
- **Diagnostic code**: SMTP status code (e.g., `550 5.1.1 User unknown`)
- **Action**: `failed`, `delayed`, `delivered`, `relayed`, `expanded`
- **Status**: Extended status code (e.g., `5.1.1` = bad destination mailbox)
- **Remote MTA**: The server that generated the bounce

## Bounce Management Tool Comparison

| Feature | Postal | bouncr | Postfix Native |
|---------|--------|--------|----------------|
| **Type** | Full mail platform | Bounce microservice | MTA built-in |
| **Bounce parsing** | Automatic | Automatic | Manual (log parsing) |
| **Webhook support** | Yes | Yes | No (requires add-ons) |
| **Dashboard UI** | Full web UI | CLI/API only | None |
| **List hygiene** | Automatic suppression | Via callback | Manual |
| **Retry logic** | Built-in | Configurable | Native (queue-based) |
| **Multi-MTA support** | Yes | Yes | N/A (single MTA) |
| **Open-source** | Yes (MIT) | Yes (MIT) | Yes (IPL) |
| **Docker support** | Official compose | Community | Yes |
| **Best for** | Full mail infrastructure | Bounce processing pipeline | Simple setups |

### Postal: The Complete Mail Platform

**Postal** is a full-featured, self-hosted mail delivery platform that includes comprehensive bounce handling as part of its core feature set. It manages the entire email sending pipeline — from SMTP relay to bounce processing to list hygiene.

Key bounce features:
- Automatic DSN parsing and classification
- Per-domain bounce rate tracking
- Automatic suppression of hard-bounced addresses
- Webhook notifications for bounce events
- Detailed delivery analytics and reporting
- Built-in IP warmup and reputation management

### bouncr: The Dedicated Bounce Processor

**bouncr** is a lightweight Python microservice dedicated to parsing bounce messages and triggering callbacks. It sits between your MTA and your application, converting raw bounce emails into structured events.

Key bounce features:
- Parses DSN, ARF (abuse reports), and raw bounces
- Classifies bounce type (hard, soft, complaint)
- Sends structured webhook payloads to your application
- Supports multiple MTA backends (Postfix, Exim, Sendmail)
- Stateless design — easy to scale horizontally
- Python 3 with simple configuration

### Postfix Native Bounce Handling

**Postfix** handles bounces at the MTA level through its bounce daemon and queue management. While it doesn't provide application-level bounce classification, it forms the foundation that Postal and bouncr build on top of.

Key bounce features:
- Automatic bounce generation for undeliverable mail
- Configurable bounce message content and headers
- Queue management for retry and defer handling
- `bounce` and `defer` notification addresses
- Log-based tracking via `mail.log`
- `postqueue` and `postsuper` for queue management

## Deployment and Configuration

### Postal Docker Setup

Postal requires several services:

```yaml
version: "3.8"
services:
  postal:
    image: ghcr.io/postalserver/postal:latest
    container_name: postal
    restart: unless-stopped
    ports:
      - "25:25"
      - "5000:5000"
    depends_on:
      - mariadb
      - rabbitmq
    environment:
      - POSTAL_CONFIG_PATH=/opt/postal/config/postal.yml
    volumes:
      - ./postal-config:/opt/postal/config:rw
      - ./postal-data:/opt/postal/data:rw

  mariadb:
    image: mariadb:10.11
    container_name: postal-db
    restart: unless-stopped
    environment:
      - MYSQL_ROOT_PASSWORD=postal_root_pass
      - MYSQL_DATABASE=postal
      - MYSQL_USER=postal
      - MYSQL_PASSWORD=postal_pass
    volumes:
      - mariadb-data:/var/lib/mysql

  rabbitmq:
    image: rabbitmq:3.12-management
    container_name: postal-rabbitmq
    restart: unless-stopped

volumes:
  mariadb-data:
```

Postal's bounce handling is configured per mail server in the web UI. Each server can define:
- Bounce webhook URL (receives structured bounce events)
- Hard bounce threshold (auto-suppress after N bounces)
- Soft bounce retry policy
- Spam complaint handling

### bouncr Configuration

bouncr runs as a standalone service:

```yaml
version: "3.8"
services:
  bouncr:
    image: ghcr.io/mailgun/bouncr:latest
    container_name: bouncr
    restart: unless-stopped
    ports:
      - "8025:8025"
    environment:
      - BOUNCR_CONFIG_PATH=/etc/bouncr/config.yml
    volumes:
      - ./bouncr-config:/etc/bouncr:ro
```

Configuration (`config.yml`):

```yaml
server:
  port: 8025
  host: 0.0.0.0

parsers:
  - type: dsn
    enabled: true
  - type: arf
    enabled: true
  - type: generic
    enabled: true

webhooks:
  - url: "https://app.example.com/api/bounces"
    events: ["hard_bounce", "soft_bounce", "complaint"]
    method: POST
    headers:
      Authorization: "Bearer your-secret-token"

classification:
  hard_bounce_codes:
    - "5.1.1"  # User unknown
    - "5.1.2"  # Domain not found
    - "5.2.1"  # Mailbox disabled
  soft_bounce_codes:
    - "4.2.2"  # Mailbox full
    - "4.7.1"  # Greylisting
  max_soft_bounces: 3
```

### Postfix Bounce Configuration

Configure Postfix for detailed bounce handling:

```ini
# /etc/postfix/main.cf

# Bounce notification settings
bounce_notice_recipient = postmaster
bounce_queue_lifetime = 5d
maximal_queue_lifetime = 5d

# Bounce message content
bounce_template_file = /etc/postfix/bounce.cf

# DSN support
smtpd_delay_reject = yes
smtpd_helo_required = yes
delay_warning_time = 4h

# Soft bounce mode (for testing)
# soft_bounce = yes

# Address verification (reject unknown recipients)
address_verify_map = btree:/var/lib/postfix/verify_cache
```

Custom bounce template (`/etc/postfix/bounce.cf`):

```ini
# Custom bounce message template
failure_template = <<EOF
Charset: us-ascii
From: MAILER-DAEMON (Mail Delivery System)
Subject: Undelivered Mail Returned to Sender
Postmaster-Subject: Postmaster Copy: Undelivered Mail

This is the mail system at host $myhostname.

Your message to the following recipients could not be delivered:

%x

--x.x.x.xx
Diagnostic information:

%x
EOF
```

Monitor Postfix bounces via logs:

```bash
# Watch bounce activity in real-time
tail -f /var/log/mail.log | grep -i "bounce\|status=bounced"

# Count bounces by domain
awk '/status=bounced/ {print $NF}' /var/log/mail.log | sort | uniq -c | sort -rn

# Monitor deferred queue
postqueue -p | tail -1
```

## Bounce Processing Pipeline Architecture

A complete self-hosted bounce management pipeline typically looks like this:

```
[Application] → [Postal/bouncr] → [Postfix] → [Recipient MTA]
     ↑                                    |
     └──── Bounce Webhook ←─── DSN ───────┘
```

1. **Application sends email** through Postal's SMTP relay or bouncr's MTA integration
2. **Postal/Postfix delivers** the message to the recipient's MTA
3. **Recipient MTA generates DSN** if delivery fails
4. **Postal parses DSN automatically** or bouncr receives the bounce email
5. **Webhook fires** to your application with structured bounce data
6. **Application updates** subscriber status (suppress hard bounces, retry soft bounces)

## Monitoring and Alerting

### Postal Dashboard

Postal's web UI provides:
- Real-time delivery statistics per domain
- Bounce rate graphs (hard vs soft vs complaints)
- Per-recipient delivery history
- IP reputation tracking
- Automatic alerts when bounce rates exceed thresholds

### bouncr Metrics

bouncr exposes metrics via its API:

```bash
# Check bouncr status
curl http://localhost:8025/health

# View bounce statistics
curl http://localhost:8025/stats
# Returns: {"total_processed": 15420, "hard_bounces": 2341, "soft_bounces": 892, "complaints": 45}
```

### Postfix Log-Based Monitoring

```bash
#!/bin/bash
# Daily bounce report
echo "=== Bounce Report for $(date -d yesterday +%Y-%m-%d) ==="
echo ""
echo "Total bounces:"
grep "status=bounced" /var/log/mail.log | grep "$(date -d yesterday +%b %e)" | wc -l
echo ""
echo "Top bounce reasons:"
grep "status=bounced" /var/log/mail.log | grep "$(date -d yesterday +%b %e)" | \
  grep -oP 'status=\S+ \(\S+\)' | sort | uniq -c | sort -rn | head -10
echo ""
echo "Deferred messages:"
postqueue -p | grep -c "^[A-F0-9]"
```

## Why Self-Host Your Bounce Management?

Managing email bounces on your own infrastructure provides critical advantages:

- **Full data ownership**: Bounce data contains recipient addresses and failure reasons — sensitive information that shouldn't be shared with third-party email services. Self-hosted processing keeps all bounce data within your network.

- **No per-email costs**: Cloud email services charge per email sent or per API call. When managing large mailing lists (100K+ subscribers), bounce processing can represent millions of API calls per month. Self-hosted tools eliminate these per-event costs.

- **Custom bounce classification**: Cloud services use fixed bounce categorization. Self-hosted tools let you define custom rules — for example, treating certain "mailbox full" bounces as soft bounces with extended retry windows, or classifying specific error codes based on your business logic.

- **Integration with existing systems**: Self-hosted bounce tools integrate directly with your CRM, mailing list database, or ticketing system via webhooks or direct database access. Cloud services often have limited integration options.

- **Compliance and auditing**: When you need to prove compliance with anti-spam regulations (CAN-SPAM, GDPR), having complete bounce logs under your own control simplifies audits. You can demonstrate that bounced addresses were suppressed within the required timeframes.

- **Reputation protection**: High bounce rates damage your sending reputation and can lead to IP blacklisting. Self-hosted bounce management ensures rapid suppression of invalid addresses, keeping your bounce rate below the 2-5% threshold that triggers spam filters.

For related email infrastructure, see our [SMTP relay comparison](../2026-04-26-postal-vs-stalwart-vs-haraka-self-hosted-smtp-relay-guide/) and [mail queue management guide](../2026-05-05-self-hosted-mail-queue-management-postfix-mailgraph-pflogsumm-guide/). For email authentication and deliverability, check our [email authentication guide](../2026-05-18-opendkim-vs-rspamd-vs-opendmarc-email-authentication-guide/) and [MTA STS guide](../2026-04-28-self-hosted-mta-sts-smtp-dane-email-security-guide-2026/).

## FAQ

### What is the difference between a hard bounce and a soft bounce?

A hard bounce (SMTP 5.x.x codes) indicates a permanent delivery failure — the recipient address doesn't exist, the domain is invalid, or the mailbox is disabled. Hard-bounced addresses should be removed from mailing lists immediately. A soft bounce (SMTP 4.x.x codes) indicates a temporary failure — the mailbox is full, the server is temporarily unavailable, or greylisting is active. Soft bounces should trigger retries before being escalated to hard bounces.

### How does DSN (Delivery Status Notification) work?

When an MTA cannot deliver a message, it generates a DSN email back to the envelope sender (the Return-Path address). The DSN contains the original message headers, a diagnostic code explaining the failure, and an extended status code (RFC 3464 format like `5.1.1`). Tools like Postal and bouncr parse these DSN emails to extract structured bounce data.

### How many soft bounces before an address should be suppressed?

A common practice is to suppress after 3-5 consecutive soft bounces for the same address. This balances giving legitimate temporary issues (mailbox full, server maintenance) a chance to resolve while preventing endless retries to permanently invalid addresses.

### Can Postfix automatically handle bounce webhooks?

No, Postfix doesn't have built-in webhook support for bounces. It logs bounce events to syslog and generates DSN emails. To add webhook functionality, you need either a tool like bouncr that sits between the MTA and your application, or a log parser (like GoAccess or custom scripts) that monitors mail logs and triggers webhooks.

### How do I prevent my server from being blacklisted due to bounces?

Keep your hard bounce rate below 2-5% by: (1) using double opt-in for mailing lists, (2) verifying email addresses before adding them (SMTP VRFY or API validation), (3) immediately suppressing hard-bounced addresses, (4) implementing a feedback loop with major providers, and (5) monitoring bounce rates with tools like Postal's dashboard or custom log analysis.

### What is an ARF (Abuse Reporting Format) bounce?

ARF (RFC 5965) is a standardized format for abuse complaints — when a recipient marks your email as spam. ARF reports contain the original message headers and are sent to the abuse address specified in your domain's DNS. Tools like bouncr parse ARF reports alongside DSN bounces, allowing you to suppress addresses that have filed spam complaints.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted SMTP Bounce & DSN Management: Postal vs bouncr vs Postfix Bounce Handling",
  "description": "Compare Postal, bouncr, and Postfix for self-hosted email bounce processing, DSN parsing, and delivery status management.",
  "datePublished": "2026-05-10",
  "dateModified": "2026-05-10",
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
