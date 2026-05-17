---
title: "Self-Hosted SMTP Relay Pool: Postal vs Haraka vs Stalwart Mail"
date: "2026-05-17"
tags: ["email", "smtp", "mail-server", "relay", "high-availability"]
draft: false
---

An SMTP relay pool routes outgoing email through multiple mail servers, providing redundancy, load distribution, and improved deliverability. When a single relay goes down or gets rate-limited, traffic automatically fails over to the next available server. For self-hosted email infrastructure, a relay pool is essential for maintaining consistent mail delivery.

This guide compares three open-source mail platforms that can serve as SMTP relay pool components: **Postal** (full mail platform with routing), **Haraka** (high-performance SMTP server with plugin architecture), and **Stalwart Mail** (modern all-in-one mail server). We'll cover installation, Docker Compose deployment, relay configuration, and failover strategies.

## Why Self-Host an SMTP Relay Pool?

Running multiple SMTP relays provides critical benefits for self-hosted email infrastructure:

- **Redundancy and failover** — If one relay is blocked, rate-limited, or goes offline, email continues flowing through alternate servers
- **Load distribution** — Spread sending volume across multiple IPs to improve throughput and avoid per-IP rate limits
- **Deliverability optimization** — Route different message types (transactional, marketing, notifications) through dedicated relays with appropriate reputations
- **IP reputation management** — Isolate high-volume senders from transactional mail to protect sender reputation
- **Cost optimization** — Mix self-hosted relays with paid services (SendGrid, SES) for cost-effective overflow handling
- **Compliance and data sovereignty** — Keep email routing within your infrastructure, avoiding third-party data processing

For organizations sending thousands of emails daily — from application notifications to marketing campaigns — a well-configured relay pool ensures messages reach recipients even during infrastructure incidents.

## Postal: Full-Featured Mail Platform

[Postal](https://github.com/postalhq/postal) (15,000+ GitHub stars) is a comprehensive open-source mail delivery platform with built-in SMTP relay, message tracking, and routing rules. It supports multiple sending domains, IP pools, and detailed analytics.

**Key features:**
- Multi-domain and multi-IP pool management
- Built-in SMTP relay with routing rules
- Webhook-based event tracking (delivered, bounced, complained)
- Message queuing with retry logic
- Per-domain and per-IP reputation tracking
- Web-based management interface

### Postal Docker Compose Setup

```yaml
version: "3.8"
services:
  postal-db:
    image: mariadb:10.11
    container_name: postal-mariadb
    environment:
      MARIADB_DATABASE: postal
      MARIADB_USER: postal
      MARIADB_PASSWORD: PostalDBPass!
      MARIADB_ROOT_PASSWORD: PostalRootPass!
    volumes:
      - postal-db-data:/var/lib/mysql
    restart: unless-stopped

  postal-rabbitmq:
    image: rabbitmq:3.12-management
    container_name: postal-rabbitmq
    environment:
      RABBITMQ_DEFAULT_USER: postal
      RABBITMQ_DEFAULT_PASS: PostalRabbitPass!
    volumes:
      - postal-rmq-data:/var/lib/rabbitmq
    restart: unless-stopped

  postal:
    image: ghcr.io/postalhq/postal:latest
    container_name: postal
    environment:
      POSTAL_CONFIG_DATABASE_HOST: postal-db
      POSTAL_CONFIG_DATABASE_USERNAME: postal
      POSTAL_CONFIG_DATABASE_PASSWORD: PostalDBPass!
      POSTAL_CONFIG_MESSAGE_QUEUE_HOST: postal-rabbitmq
      POSTAL_CONFIG_MESSAGE_QUEUE_USERNAME: postal
      POSTAL_CONFIG_MESSAGE_QUEUE_PASSWORD: PostalRabbitPass!
    ports:
      - "5000:5000"   # Web interface
      - "25:25"       # SMTP
      - "443:443"     # HTTPS
    volumes:
      - postal-config:/opt/postal/config
      - postal-data:/opt/postal/data
    depends_on:
      - postal-db
      - postal-rabbitmq
    restart: unless-stopped

volumes:
  postal-db-data:
  postal-rmq-data:
  postal-config:
  postal-data:
```

### Postal Relay Pool Configuration

```yaml
# Configure multiple IP pools in Postal web interface
# Pool: transactional-pool
#   - IP: 203.0.113.10 (primary)
#   - IP: 203.0.113.11 (backup)

# Pool: marketing-pool
#   - IP: 203.0.113.20 (primary)
#   - IP: 203.0.113.21 (backup)

# Routing rules via Postal CLI
postal configure routes create \
  --domain example.com \
  --pattern "transactional-*" \
  --ip-pool transactional-pool

postal configure routes create \
  --domain example.com \
  --pattern "marketing-*" \
  --ip-pool marketing-pool
```

## Haraka: High-Performance Plugin-Based SMTP Server

[Haraka](https://github.com/haraka/haraka) (4,400+ GitHub stars) is a Node.js-based SMTP server designed for high throughput. Its plugin architecture makes it ideal for building custom relay routing logic, including multi-relay failover.

**Key features:**
- Node.js-based, handling 10,000+ concurrent connections
- Extensive plugin ecosystem (SPF, DKIM, DMARC, queue, relay)
- Custom relay routing via plugins
- Built-in connection throttling and rate limiting
- Low resource footprint
- Hot-reloadable configuration

### Haraka Docker Compose Setup

```yaml
version: "3.8"
services:
  haraka:
    image: home/haraka:latest
    container_name: haraka-relay
    ports:
      - "25:25"
      - "587:587"
    volumes:
      - ./config/:/haraka/config/
      - ./plugins/:/haraka/plugins/
    environment:
      - TZ=UTC
    restart: unless-stopped
```

### Haraka Relay Plugin Configuration

```ini
# config/smtp.ini
listen=[0.0.0.0]:25
listen=[0.0.0.0]:587
daemonize=false
loglevel=info

# config/plugins
# Enable relay and routing plugins
relay-all
relay-forward
queue/smtp_forward

# config/smtp_forward.ini
host=relay1.example.com
port=587
auth_type=plain
auth_user=relay_user
auth_password=relay_pass
enable_tls=true

# config/relay_failover.ini
# Primary relay
[primary]
host=relay1.example.com
port=587
max_attempts=3

# Secondary relay
[secondary]
host=relay2.example.com
port=587
max_attempts=3

# Tertiary relay (fallback)
[tertiary]
host=relay3.example.com
port=25
max_attempts=5
```

### Custom Haraka Failover Plugin

```javascript
// plugins/relay-failover.js
const net = require('net');

const RELAYS = [
    { host: 'relay1.example.com', port: 587 },
    { host: 'relay2.example.com', port: 587 },
    { host: 'relay3.example.com', port: 25 },
];

exports.hook_queue = function (next, connection) {
    const transaction = connection.transaction;
    let relayIndex = 0;

    const tryRelay = () => {
        if (relayIndex >= RELAYS.length) {
            return next(DENYSOFT, 'All relays unavailable');
        }
        const relay = RELAYS[relayIndex];
        const socket = net.createConnection(relay.port, relay.host);

        socket.on('connect', () => {
            connection.loginfo(this, `Relay ${relay.host}:${relay.port} available`);
            // Forward transaction to this relay
            next(OK);
        });

        socket.on('error', () => {
            connection.logerror(this, `Relay ${relay.host} failed, trying next`);
            relayIndex++;
            tryRelay();
        });

        socket.setTimeout(5000);
    };

    tryRelay();
};
```

## Stalwart Mail: Modern All-in-One Mail Server

[Stalwart Mail](https://github.com/stalwartlabs/mail-server) (3,000+ GitHub stars) is a modern Rust-based mail server supporting SMTP, IMAP, JMAP, and sieve filtering. It includes built-in relay configuration and multi-tenant support.

**Key features:**
- Written in Rust for memory safety and performance
- SMTP, IMAP, JMAP, and CalDAV/CardDAV support
- Built-in relay and smart host configuration
- Multi-tenant architecture with domain isolation
- Web-based administration console
- ACME/Let's Encrypt integration

### Stalwart Mail Docker Compose Setup

```yaml
version: "3.8"
services:
  stalwart:
    image: stalwartlabs/mail-server:latest
    container_name: stalwart-mail
    ports:
      - "25:25"
      - "587:587"
      - "993:993"
      - "443:443"
      - "8080:8080"
    volumes:
      - ./stalwart.toml:/etc/stalwart/stalwart.toml
      - stalwart-data:/var/lib/stalwart-mail
    environment:
      STALWART_ADMIN_TOKEN: "admin-secret-token"
    restart: unless-stopped

volumes:
  stalwart-data:
```

### Stalwart Mail Relay Configuration

```toml
# stalwart.toml
[server]
hostname = "mail.example.com"
domain = "example.com"

[smtp.relay]
enabled = true
hosts = [
    { host = "relay1.example.com", port = 587, tls = "required" },
    { host = "relay2.example.com", port = 587, tls = "required" },
    { host = "relay3.example.com", port = 25, tls = "optional" },
]
strategy = "failover"  # failover, round-robin, or weighted
credentials = { username = "relay_user", password = "relay_pass" }
max_retries = 3
retry_interval = "300s"

[smtp.relay.dkim]
enabled = true
selector = "default"
private_key = "/etc/stalwart/dkim/private.pem"

[smtp.auth]
enabled = true
mechanisms = ["plain", "login"]
require_tls = true

[storage]
type = "sqlite"
path = "/var/lib/stalwart-mail/data"
```

## Comparison: Postal vs Haraka vs Stalwart Mail

| Feature | Postal | Haraka | Stalwart Mail |
|---------|--------|--------|---------------|
| GitHub Stars | 15,000+ | 4,400+ | 3,000+ |
| Language | Ruby | Node.js | Rust |
| SMTP Relay | Built-in | Via plugins | Built-in |
| IMAP/POP3 | No | No | Yes |
| Web UI | Yes | No | Yes (admin) |
| Multi-Tenant | Yes | Via plugins | Yes |
| Relay Failover | IP pools + routing | Custom plugins | Configured (failover/round-robin) |
| Event Tracking | Webhooks | Plugins | Built-in |
| DKIM/SPF/DMARC | Built-in | Plugins | Built-in |
| Rate Limiting | Built-in | Built-in | Built-in |
| JMAP Support | No | No | Yes |
| Resource Usage | High (Ruby+RMQ) | Low | Low (Rust) |
| Docker Support | Yes (ghcr.io) | Yes (community) | Yes (stalwartlabs) |
| Learning Curve | Moderate | Moderate | Low |

## Choosing the Right SMTP Relay Platform

**Choose Postal if:**
- You need a complete mail platform with web UI, tracking, and analytics
- Multi-IP pool management with per-domain routing is essential
- You want built-in webhook-based event tracking for delivery monitoring
- You manage multiple sending domains and need centralized management

**Choose Haraka if:**
- You need maximum throughput (10,000+ concurrent connections)
- Custom relay routing logic is required (write Node.js plugins)
- You already use Node.js and want to integrate relay management into existing tooling
- Low resource footprint is a priority

**Choose Stalwart Mail if:**
- You want a modern, memory-safe mail server in Rust
- You need both SMTP relay and IMAP/CalDAV in a single platform
- Multi-tenant support with domain isolation is required
- You prefer declarative TOML configuration over imperative setup

## Best Practices for SMTP Relay Pools

1. **Use dedicated IPs per message type** — Separate transactional, marketing, and notification traffic across different relay IPs to protect sender reputation.

2. **Monitor relay health** — Implement health checks for each relay node. Use Haraka's connection monitoring or Postal's dashboard to detect degraded relays before they impact delivery.

3. **Configure retry policies** — Set appropriate retry intervals and maximum attempts. For transactional email, use shorter retry windows (30 seconds). For bulk mail, longer intervals (5-15 minutes) prevent overwhelming failing relays.

4. **Implement TLS everywhere** — Require STARTTLS for relay connections. Configure DKIM signing on all outgoing messages to improve deliverability.

5. **Track bounce rates per relay** — Monitor bounce and complaint rates for each relay IP. If a relay's bounce rate exceeds thresholds, automatically remove it from the pool.

6. **Plan for IP warmup** — When adding new relay IPs, gradually increase sending volume over 2-4 weeks. Sudden high-volume sending from new IPs triggers spam filters.

## Why Self-Host SMTP Relay Infrastructure?

Managing your own SMTP relay pool gives you complete control over email routing, deliverability optimization, and data privacy. For organizations with strict compliance requirements, high email volumes, or complex routing needs, self-hosted relay infrastructure avoids the costs and limitations of third-party email services.

Combined with proper DNS configuration (SPF, DKIM, DMARC), a self-hosted relay pool provides enterprise-grade email delivery capability. For organizations running internal mail servers, pairing relay infrastructure with mail filtering solutions creates a complete email stack.

For related email infrastructure, see our [SMTP relay guide](../2026-04-29-msmtp-vs-nullmailer-vs-dma-lightweight-email-rela/), [MTA comparison](../2026-04-26-postal-vs-stalwart-vs-haraka-self-hosted-smtp-rel/), and [email sieve filtering guide](../2026-05-12-self-hosted-email-sieve-filtering-pigeonhole-rspa/).

## FAQ

### What is an SMTP relay pool?
An SMTP relay pool is a group of mail servers that handle outgoing email delivery. Messages are distributed across multiple relays using strategies like round-robin, weighted distribution, or failover. If one relay becomes unavailable, traffic automatically routes to the next available server.

### How do I prevent relay abuse (open relay)?
Always require authentication (SMTP AUTH) before allowing relay. Configure IP-based access control lists (ACLs) to restrict relay access to trusted networks. Use DKIM signing to verify outgoing message authenticity. Never configure a relay that accepts mail from any source without authentication.

### What is the difference between failover and round-robin relay strategies?
Failover sends all mail through the primary relay until it fails, then switches to the next relay. Round-robin distributes mail evenly across all relays. Failover is simpler but underutilizes backup relays. Round-robin maximizes throughput but requires all relays to be healthy.

### Can I mix self-hosted relays with cloud services?
Yes. A common pattern uses self-hosted relays for normal traffic and cloud services (SendGrid, AWS SES, Mailgun) as overflow or backup relays. Configure your relay pool to try self-hosted servers first, then fall back to cloud providers when self-hosted relays are rate-limited or unavailable.

### How do I monitor relay pool health?
Use Postal's built-in dashboard, Haraka's plugin logging, or Stalwart's admin console. Set up external monitoring that periodically sends test messages through each relay. Track delivery rates, bounce rates, and response times. Alert when any relay's error rate exceeds a threshold (typically 5%).

### What causes SMTP relay failures?
Common causes include: IP blacklisting (relay IP added to spam blocklists), rate limiting (recipient mail servers reject high-volume senders), network connectivity issues, TLS certificate expiration, and relay server resource exhaustion (CPU, memory, disk space). Monitor each potential failure mode and configure automatic failover.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted SMTP Relay Pool: Postal vs Haraka vs Stalwart Mail",
  "description": "Build an SMTP relay pool for high-availability email delivery using Postal, Haraka, and Stalwart Mail. Includes Docker Compose configs and failover strategies.",
  "datePublished": "2026-05-17",
  "dateModified": "2026-05-17",
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
