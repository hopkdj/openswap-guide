---
title: "Self-Hosted Email Bounce Management: Postal vs Stalwart vs Haraka (2026)"
date: "2026-05-24"
tags: ["email", "bounce-management", "postal", "stalwart", "haraka", "mta", "self-hosted", "mail-server"]
draft: false
---

Email bounces are inevitable in any email-sending operation. Whether you're running a newsletter, transactional email system, or marketing platform, understanding and managing bounce rates is critical for deliverability. Hard bounces (permanent delivery failures) damage your sender reputation, while soft bounces (temporary issues) require intelligent retry logic.

In this guide, we compare three open-source email platforms that handle bounce management differently: **Postal** (dedicated bounce processing with webhooks), **Stalwart Mail** (full mail server with bounce classification), and **Haraka** (modular MTA with bounce plugins). Each offers a different approach to bounce detection, classification, and handling.

## Comparison Table

| Feature | Postal | Stalwart Mail | Haraka |
|---------|--------|--------------|--------|
| **GitHub Stars** | 16,505+ | 2,300+ | 3,300+ |
| **Type** | Mail delivery platform | Full mail server | Modular MTA (Node.js) |
| **Bounce Detection** | Webhook-based, real-time | Built-in DSN parsing | Plugin-based |
| **Bounce Classification** | Hard vs soft with reasons | DSN code analysis | Custom plugin logic |
| **Automatic Retry** | Configurable retry schedules | Built-in queue retry | Queue plugin |
| **Webhook Integration** | Yes (extensive API) | Yes (REST API) | Yes (via plugins) |
| **Dashboard UI** | Full web interface | Web admin panel | None (CLI/web plugin) |
| **Docker Support** | Official compose setup | Official Docker image | Official Docker image |
| **Programming Language** | Ruby | Rust | JavaScript/Node.js |
| **License** | MIT | EUPL-1.2 | MIT |
| **Best For** | Transactional email platforms | Full mail server replacement | Custom MTA pipelines |

## Postal

Postal is a complete open-source mail delivery platform designed as a self-hosted alternative to SendGrid and Mailgun. It includes comprehensive bounce management with real-time webhook notifications, detailed bounce analytics, and automatic suppression list management.

### Bounce Processing Architecture

Postal processes bounces through its **Message Server** component, which:
1. Receives bounce messages (DSN — Delivery Status Notifications) via its inbound MX
2. Parses the bounce headers to classify hard vs soft bounces
3. Triggers webhook events to your application
4. Automatically adds hard-bounced addresses to suppression lists

### Docker Compose Setup

```yaml
version: '3.8'
services:
  postal:
    image: ghcr.io/postalserver/postal:latest
    container_name: postal
    ports:
      - "5000:5000"
      - "25:25"
      - "443:443"
    environment:
      - POSTAL_DB_HOST=mysql
      - POSTAL_DB_USER=postal
      - POSTAL_DB_PASSWORD=postal
      - POSTAL_DB_NAME=postal
      - POSTAL_RABBITMQ_HOST=rabbitmq
    depends_on:
      - mysql
      - rabbitmq
    volumes:
      - postal-config:/opt/postal/config

  mysql:
    image: mariadb:10.11
    environment:
      - MYSQL_ROOT_PASSWORD=postal
      - MYSQL_DATABASE=postal
      - MYSQL_USER=postal
      - MYSQL_PASSWORD=postal
    volumes:
      - mysql-data:/var/lib/mysql

  rabbitmq:
    image: rabbitmq:3.12-alpine
    volumes:
      - rabbitmq-data:/var/lib/rabbitmq

volumes:
  postal-config:
  mysql-data:
  rabbitmq-data:
```

### Handling Bounce Webhooks

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/webhooks/bounce', methods=['POST'])
def handle_bounce():
    data = request.json
    event_type = data.get('event')  # 'bounce', 'softbounce', 'hardbounce'
    
    if event_type == 'hardbounce':
        email = data.get('address')
        reason = data.get('reason')
        # Add to suppression list
        print(f"Hard bounce for {email}: {reason}")
        # Update your database to suppress this address
    elif event_type == 'softbounce':
        # Track retry count
        email = data.get('address')
        print(f"Soft bounce for {email}, will retry")
    
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(port=8080)
```

## Stalwart Mail

Stalwart Mail is a modern, Rust-based mail server that combines MTA, IMAP, and Sieve capabilities in a single binary. Its bounce management leverages RFC-compliant DSN (Delivery Status Notification) parsing and classification.

### Bounce Classification

Stalwart Mail classifies bounces by parsing DSN response codes:
- **5.x.x** codes → Hard bounces (permanent failure)
- **4.x.x** codes → Soft bounces (temporary failure)
- Specific codes (550, 554, 552) → Categorize by reason (user unknown, policy rejection, mailbox full)

### Docker Compose Setup

```yaml
version: '3.8'
services:
  stalwart:
    image: stalwartlabs/mail-server:latest
    container_name: stalwart-mail
    ports:
      - "25:25"       # SMTP
      - "465:465"     # SMTPS
      - "587:587"     # Submission
      - "993:993"     # IMAPS
      - "8080:8080"   # JMAP/Admin UI
    volumes:
      - stalwart-data:/opt/stalwart-mail/data
      - stalwart-config:/etc/stalwart-mail
    environment:
      - STALWART_ADMIN_SECRET=your-secret-key

volumes:
  stalwart-data:
  stalwart-config:
```

### Configuration for Bounce Handling

```toml
# /etc/stalwart-mail/stalwart.toml
[session.inbound]
max_message_size = 52428800  # 50MB

[queue]
retry_interval = "5m"
max_retries = 8
retry_backoff = "exponential"

[queue.dsn]
enabled = true
send_on_failure = true
send_on_success = false
```

## Haraka

Haraka is a highly modular, plugin-based MTA written in Node.js. Its bounce handling is entirely plugin-driven, giving you complete control over how bounces are detected, classified, and processed.

### Bounce Processing with Plugins

Haraka uses several plugins for bounce management:
- **bounce** — Core bounce detection and processing
- **bounce.handler** — Custom bounce classification logic
- **queue/smtp_forward** — Routes bounced messages to processing queues
- **dnsbl** — Rejects mail from known bad sources before bounce generation

### Docker Compose Setup

```yaml
version: '3.8'
services:
  haraka:
    image: haraka/haraka:latest
    container_name: haraka-mta
    ports:
      - "25:25"
      - "587:587"
    volumes:
      - ./haraka-config:/haraka/config
      - ./haraka-plugins:/haraka/plugins
    environment:
      - HARAKA_HOSTLIST=mail.example.com

  # Optional: Redis for queue management
  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data

volumes:
  redis-data:
```

### Custom Bounce Handler Plugin

```javascript
// plugins/bounce_handler.js
exports.hook_bounce = function(next, connection, params) {
    const bounce_msg = params;
    const original_recipient = bounce_msg.original_recipient;
    const bounce_code = bounce_msg.code;
    
    // Classify bounce type
    if (bounce_code >= 500) {
        // Hard bounce - permanent failure
        connection.loginfo(this, `Hard bounce: ${original_recipient} (${bounce_code})`);
        // Add to suppression list
        this.add_to_suppression(original_recipient);
    } else if (bounce_code >= 400) {
        // Soft bounce - temporary failure
        connection.loginfo(this, `Soft bounce: ${original_recipient} (${bounce_code})`);
        // Queue for retry
        this.queue_for_retry(original_recipient, bounce_code);
    }
    
    next();
};

exports.add_to_suppression = function(email) {
    // Store in Redis or database
    const redis = require('redis');
    const client = redis.createClient();
    client.sAdd('bounce:hard', email);
};
```

## Why Email Bounce Management Matters for Self-Hosted Infrastructure

Managing email bounces is one of the most overlooked aspects of self-hosted email operations. Without proper bounce handling, your mail server continues sending to invalid addresses, which triggers spam filters, damages sender reputation, and can eventually result in IP blacklisting.

### The Cost of Ignoring Bounces

When your mail server sends to a non-existent address, the receiving server generates a bounce message (DSN). If you don't process these bounces, several problems accumulate:
- **Sender reputation decay**: ISPs track bounce rates. Consistently high bounce rates (>5%) cause your emails to be flagged as spam or rejected outright.
- **Wasted resources**: Each bounced message consumes CPU, bandwidth, and queue space on your mail server.
- **Blocklist risk**: Organizations like Spamhaus monitor bounce rates. Excessive bounces from your IP can trigger blocklist listings, affecting all email from your domain.
- **Delayed delivery issues**: Soft bounces that aren't retried appropriately mean legitimate messages may never reach recipients whose mailboxes were temporarily unavailable.

### Self-Hosting Advantages for Bounce Processing

When you self-host your email infrastructure, you have complete control over bounce processing logic. Commercial platforms like SendGrid and Mailgun offer bounce handling as a managed feature, but self-hosted solutions give you:
- **Custom classification rules**: Define your own thresholds for retry attempts, suppression criteria, and escalation logic.
- **Data privacy**: Bounce data (including recipient email addresses and error codes) stays on your infrastructure.
- **No rate limits**: Process unlimited bounce events without per-message or per-hour caps.
- **Integration flexibility**: Connect bounce events directly to your application's user management, CRM, or analytics systems.

## Choosing the Right Bounce Management Solution

**Choose Postal when:**
- You need a complete mail delivery platform with built-in bounce management
- Real-time webhook notifications are critical for your workflow
- You want a SendGrid/Mailgun replacement with full control
- Your application needs suppression list management

**Choose Stalwart Mail when:**
- You need a full mail server (SMTP + IMAP + Sieve) in a single binary
- Rust-based performance and memory safety matter
- You want RFC-compliant DSN parsing without external dependencies
- You prefer a single-binary deployment over multi-service stacks

**Choose Haraka when:**
- You need maximum flexibility in bounce processing logic
- Your team is comfortable with Node.js and plugin development
- You want to integrate bounce handling with custom business logic
- You're building a specialized MTA pipeline with unique requirements

For more on self-hosted email infrastructure, see our [SMTP relay comparison](../2026-04-26-postal-vs-stalwart-vs-haraka-self-hosted-smtp-relay-guide-2026/) and [email encryption with PGP and S/MIME](../2026-05-02-self-hosted-email-encryption-pgp-smime-solutions-guide/).

## FAQ

### What is the difference between a hard bounce and a soft bounce?

A **hard bounce** is a permanent delivery failure — the recipient address doesn't exist, the domain is invalid, or the recipient's server permanently rejected your message. Hard bounces should result in immediate address suppression. A **soft bounce** is a temporary failure — the recipient's mailbox is full, their server is down, or your message was temporarily throttled. Soft bounces warrant retry attempts before eventual suppression.

### How many retry attempts should I configure for soft bounces?

A common pattern is 3-5 retry attempts with exponential backoff: retry after 15 minutes, then 1 hour, then 4 hours, then 12 hours. After the final retry, classify the soft bounce as a hard bounce and suppress the address. Postal's default retry schedule follows this pattern, while Stalwart Mail lets you configure `max_retries` and `retry_backoff` in its queue settings.

### How does bounce handling affect sender reputation?

High bounce rates (above 5%) damage your sender reputation with receiving mail servers and blocklist operators. Gmail, Yahoo, and Outlook all factor bounce rates into their spam filtering decisions. Promptly suppressing hard-bounced addresses and implementing proper bounce classification is essential for maintaining deliverability. Tools like Postal make this automatic through their suppression list features.

### Can I use Haraka as a bounce processor for another MTA?

Yes. Haraka's plugin architecture allows it to process bounce messages received from any MTA. Configure your primary MTA to forward bounce messages to Haraka's inbound port, then use Haraka's bounce plugins to parse, classify, and route the bounce data to your application via webhooks or database updates.

### Does Stalwart Mail support bounce webhook notifications?

Stalwart Mail provides a REST API for server management and monitoring. While it doesn't have built-in bounce webhooks like Postal, you can configure it to write bounce events to its log files or JMAP event stream, which your application can poll or stream-process. For real-time webhook-based bounce handling, Postal is the more suitable choice.

### What DSN codes should I watch for?

Key DSN codes include: **550** (mailbox unavailable/user unknown — hard bounce), **552** (mailbox full — soft bounce), **554** (transaction failed/policy rejection — hard bounce), **450** (mailbox temporarily unavailable — soft bounce), and **451** (local error/processing failure — soft bounce). Both Postal and Stalwart Mail automatically parse these codes and classify bounces accordingly.


<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Email Bounce Management: Postal vs Stalwart vs Haraka",
  "description": "Compare three open-source email platforms for bounce management: Postal (webhook-based), Stalwart Mail (DSN parsing), and Haraka (plugin-driven MTA). Includes Docker Compose configs and bounce handling code.",
  "datePublished": "2026-05-24",
  "dateModified": "2026-05-24",
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

