---
title: "Self-Hosted Greylisting Servers: Postgrey vs Sqlgrey vs Rspamd Greylisting"
date: "2026-05-10T08:00:00+00:00"
tags: ["email-security", "greylisting", "spam-filtering", "postgrey", "sqlgrey", "rspamd", "postfix", "email"]
draft: false
---

Greylisting is one of the simplest yet most effective anti-spam techniques available to self-hosted mail administrators. By temporarily rejecting email from unknown senders and expecting legitimate mail servers to retry delivery, greylisting blocks the vast majority of spam at the SMTP level — before the message body is even accepted.

Unlike content-based spam filtering (which analyzes message content, headers, and attachments), greylisting works at the protocol level. Spambots typically do not implement SMTP retry logic, while legitimate MTAs (Postfix, Exim, Sendmail) automatically queue and retry delivery after a delay. This makes greylisting a low-overhead, high-impact spam defense.

This guide compares three greylisting implementations for self-hosted mail servers: **Postgrey** (the classic Postfix policy daemon), **Sqlgrey** (a Perl-based alternative with a web interface), and **Rspamd's built-in greylisting module** (integrated into the modern Rspamd spam filtering platform).

## How Greylisting Works

When an email arrives from an unknown sender-recipient pair (called a "triplet" — sender IP, sender address, recipient address), the greylisting server returns a temporary SMTP 450/451 rejection with a message like "try again later." Legitimate mail servers queue the message and retry after a configurable delay (typically 5-15 minutes). On retry, the triplet is recognized as "seen before" and the message is accepted.

The effectiveness comes from the fact that most spam sources:
- Do not implement RFC-compliant retry logic
- Use disposable infrastructure that cannot track retry state
- Prioritize sending volume over delivery reliability

Studies consistently show greylisting blocks 70-90% of spam with zero false positives for legitimate mail. The tradeoff is a delivery delay of 5-15 minutes for first-time senders.

## Postgrey

Postgrey is the most widely deployed greylisting daemon for Postfix, written in C and Perl with a simple Berkeley DB backend. With 170+ GitHub stars, it is a mature, stable solution that has been the default greylisting tool for Debian and Ubuntu mail server setups for over a decade.

### Key Features

- **Postfix policy daemon** — integrates seamlessly via Postfix's `check_policy_service`
- **Berkeley DB backend** — lightweight, no database server required
- **Auto-whitelist** — automatically whitelists triplets after successful delivery (configurable threshold)
- **Debian/Ubuntu packaged** — available in default repositories
- **Minimal resource usage** — runs as a single daemon process with low memory footprint
- **DNSWL integration** — can skip greylisting for senders on the DNS Whitelist

### Installation and Configuration

```bash
# Install on Debian/Ubuntu
apt install postgrey

# Enable and start
systemctl enable postgrey
systemctl start postgrey
```

Configure Postfix to use Postgrey as a policy service:

```ini
# /etc/postfix/main.cf
smtpd_recipient_restrictions =
    permit_mynetworks,
    permit_sasl_authenticated,
    reject_unauth_destination,
    check_policy_service inet:127.0.0.1:10023
```

Tune Postgrey's behavior:

```bash
# /etc/default/postgrey
POSTGREY_OPTS="--inet=10023 --delay=120 --max-age=35 --auto-whitelist-clients=5"

# --delay=120: require 2-minute retry delay
# --max-age=35: forget triplets older than 35 days
# --auto-whitelist-clients=5: whitelist after 5 successful deliveries
```

Add DNSWL exceptions to reduce delays for known-good senders:

```bash
POSTGREY_OPTS="$POSTGREY_OPTS --greylist-action=defer_if_permit"
```

### Docker Deployment

```yaml
version: '3.8'

services:
  postgrey:
    image: mwaeckerlin/postgrey:latest
    ports:
      - "10023:10023"
    environment:
      - POSTGREY_DELAY=120
      - POSTGREY_MAX_AGE=35
      - POSTGREY_AUTO_WHITELIST_CLIENTS=5
    volumes:
      - postgrey-data:/var/lib/postgrey
    restart: unless-stopped

volumes:
  postgrey-data: {}
```

## Sqlgrey

Sqlgrey (SQL Greylist) is a Postfix policy daemon written in Perl that stores greylisting data in a SQL database (MySQL, PostgreSQL, or SQLite). This makes it suitable for high-volume mail servers where the Berkeley DB backend of Postgrey becomes a bottleneck.

### Key Features

- **SQL backend** — MySQL, PostgreSQL, or SQLite for scalable triplet storage
- **Web interface** — Greyface and SQLgreyGUI provide web-based management
- **Fine-grained control** — per-domain, per-recipient, and per-sender policies
- **Whitelist management** — web-based whitelist editing with domain patterns
- **Statistics** — built-in reporting on greylist hits, passes, and deferrals
- **Domain-based greylisting** — enable/disable greylisting per recipient domain

### Installation and Configuration

```bash
# Install dependencies
apt install sqlgrey libdbd-mysql-perl

# Configure database
# Edit /etc/sqlgrey/sqlgrey.conf
```

```ini
# /etc/sqlgrey/sqlgrey.conf
[main]
user = sqlgrey
group = sqlgrey
listen = 127.0.0.1:2501

[db]
# MySQL configuration
db_type = mysql
db_host = 127.0.0.1
db_port = 3306
db_name = sqlgrey
db_user = sqlgrey
db_pass = sqlgrey_password

[greylisting]
initial_delay = 180
max_age = 35
auto_whitelist_threshold = 3
```

Configure Postfix:

```ini
# /etc/postfix/main.cf
smtpd_recipient_restrictions =
    permit_mynetworks,
    permit_sasl_authenticated,
    reject_unauth_destination,
    check_policy_service inet:127.0.0.1:2501
```

### Web Interface (SQLgreyGUI)

```yaml
version: '3.8'

services:
  sqlgrey:
    image: linuxserver/sqlgrey:latest
    ports:
      - "2501:2501"
    environment:
      - TZ=UTC
      - DB_TYPE=mysql
      - DB_HOST=db
      - DB_NAME=sqlgrey
      - DB_USER=sqlgrey
      - DB_PASS=sqlgrey_password
    volumes:
      - sqlgrey-config:/config
    depends_on:
      - db

  db:
    image: mariadb:11
    environment:
      - MYSQL_ROOT_PASSWORD=root_password
      - MYSQL_DATABASE=sqlgrey
      - MYSQL_USER=sqlgrey
      - MYSQL_PASSWORD=sqlgrey_password
    volumes:
      - sqlgrey-db:/var/lib/mysql

volumes:
  sqlgrey-config: {}
  sqlgrey-db: {}
```

## Rspamd Greylisting Module

Rspamd is a modern, high-performance spam filtering platform (2,450+ GitHub stars) that includes a built-in greylisting module. Unlike standalone greylisting daemons, Rspamd's greylisting is integrated into a comprehensive spam scoring system that also checks DKIM, SPF, DMARC, Bayesian filtering, and neural network-based spam detection.

### Key Features

- **Integrated platform** — greylisting is one module within a full spam filtering stack
- **Redis backend** — fast, distributed greylisting state storage
- **Configurable scoring** — greylisting adds to the overall spam score rather than hard-rejecting
- **Per-user settings** — greylisting can be enabled/disabled per mailbox
- **SURBL integration** — checks URIs against real-time blocklists
- **Neural network support** — machine learning-based spam classification
- **Web UI** — built-in web interface for monitoring and management

### Configuration

Rspamd's greylisting module is enabled by default. Configure it in the module settings:

```lua
# /etc/rspamd/local.d/greylist.conf
greylist {
    # Enable greylisting
    enabled = true;
    
    # Greylisting period (5 minutes)
    expire = 5min;
    
    # Whitelist expiry (36 days)
    whitelist_expire = 36d;
    
    # Minimum SPF pass score to skip greylisting
    skip_authenticated = true;
    
    # Redis backend
    backend = "redis";
    servers = "127.0.0.1:6379";
    
    # Greylist only if message score would be ambiguous
    greylist_min_score = 2;
    greylist_max_score = 6;
}
```

Integrate Rspamd with Postfix via milter:

```ini
# /etc/postfix/main.cf
smtpd_milters = inet:127.0.0.1:11332
non_smtpd_milters = inet:127.0.0.1:11332
milter_protocol = 6
milter_default_action = accept
```

### Docker Compose

```yaml
version: '3.8'

services:
  rspamd:
    image: rspamd/rspamd:latest
    ports:
      - "11332:11332"  # milter port
      - "11334:11334"  # HTTP API / WebUI
    volumes:
      - ./rspamd/local.d:/etc/rspamd/local.d:ro
      - rspamd-data:/var/lib/rspamd
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --save 300 1 --save 60 100
    volumes:
      - redis-data:/data
    restart: unless-stopped

volumes:
  rspamd-data: {}
  redis-data: {}
```

## Comparison: Greylisting Solutions

| Feature | Postgrey | Sqlgrey | Rspamd Greylisting |
|---------|----------|---------|-------------------|
| **Backend** | Berkeley DB | MySQL/PostgreSQL/SQLite | Redis |
| **Language** | C/Perl | Perl | C (Lua config) |
| **Web Interface** | No | Yes (SQLgreyGUI) | Yes (built-in) |
| **Spam Filtering** | Greylisting only | Greylisting only | Full suite (DKIM, SPF, DMARC, Bayes, NN) |
| **Scalability** | Single-server | Multi-server (SQL backend) | Distributed (Redis backend) |
| **Per-Domain Control** | No | Yes | Yes |
| **Auto-Whitelist** | Yes | Yes | Yes |
| **DNSWL Support** | Yes | Manual | Yes (via RBL module) |
| **Docker Image** | Community | Community/LinuxServer | Official |
| **Resource Usage** | Very Low | Low-Moderate | Moderate |
| **Best For** | Simple Postfix setups | High-volume with web UI | Full spam filtering stack |
| **GitHub Stars** | 170+ | 7+ (mirrors) | 2,450+ |

## Why Self-Host Greylisting?

Spam is an ongoing problem for anyone running their own mail server. Cloud-based email providers handle spam filtering at massive scale, but when you self-host, you need your own defenses. Greylisting provides a powerful first line of defense that works independently of content analysis — it blocks spam based on sender behavior, not message content.

Running greylisting locally gives you complete control over the delay threshold, whitelist policies, and exception rules. You can fine-tune the behavior for your specific traffic patterns, whitelist your business partners, and adjust the greylisting period based on your tolerance for delivery delays. Unlike cloud filtering services, your greylisting data never leaves your server, preserving sender privacy.

For mail server administrators, combining greylisting with other anti-spam techniques creates a defense-in-depth strategy. For related reading, see our [spam filtering comparison](../2026-04-26-spamassassin-vs-rspamd-vs-amavis-self-hosted-spam-filtering-guide-2026/), [SMTP relay guide](../2026-04-26-postal-vs-stalwart-vs-haraka-self-hosted-smtp-relay-guide-2026/), and [MTA comparison](../2026-04-29-postfix-vs-exim-self-hosted-mta-comparison-guide-2026/).

For related reading, see our [spam filtering comparison](../2026-04-26-spamassassin-vs-rspamd-vs-amavis-self-hosted-spam-filtering-guide-2026/) and [SMTP relay guide](../2026-04-26-postal-vs-stalwart-vs-haraka-self-hosted-smtp-relay-guide-2026/). If you need mail admin tools, our [mail admin comparison](../2026-04-26-postfixadmin-vs-modoboa-vs-iredadmin-self-hosted-mail-admin-guide-2026/) covers web-based mail management.

## FAQ

### How much does greylisting delay email delivery?
For first-time senders, greylisting adds a delay of 2-5 minutes (configurable). Legitimate mail servers retry automatically, so the sender does not need to take any action. After the first successful delivery, the sender-recipient pair is whitelisted (either temporarily or permanently) and subsequent messages pass immediately. Most greylisting setups auto-whitelist after 3-5 successful deliveries.

### Does greylisting block legitimate email?
Greylisting has virtually zero false positives because all RFC-compliant mail servers implement retry logic. The only exceptions are poorly configured MTAs and some automated notification systems that do not retry on temporary failures. You can work around this by whitelisting specific sender domains or IP ranges that you know deliver time-sensitive notifications.

### Can I use greylisting with mail servers other than Postfix?
Postgrey and Sqlgrey are Postfix-specific policy daemons. However, Rspamd supports integration with Exim, Sendmail, and other MTAs via its milter or proxy interfaces. Additionally, you can implement greylisting logic directly in Exim's ACLs or in a custom policy daemon for any MTA that supports external policy services.

### Should I use greylisting together with other spam filters?
Absolutely. Greylisting is most effective as part of a layered spam defense strategy. Use greylisting as the first filter (blocks 70-90% of spam at the protocol level), then pass remaining messages through content-based filters like Rspamd or SpamAssassin. This combination catches spam that retries delivery (which greylisting alone would miss) while keeping the overall resource usage low.

### How does the auto-whitelist feature work?
The auto-whitelist tracks successful delivery attempts for each sender-recipient triplet. After a configurable number of successful deliveries (typically 3-5), the sender is added to the whitelist and future messages bypass greylisting entirely. The whitelist has an expiration time (typically 30-36 days) after which the sender must be greylisted again, catching any new spam sources that may have compromised a previously legitimate sender.

### What happens to email during a greylisting server outage?
If the greylisting daemon is down, Postfix will typically treat the policy service failure as a temporary error and defer delivery, causing the sending MTA to retry. This is actually safe behavior — email is not lost, just delayed. For high-availability setups, run multiple greylisting instances behind a load balancer, or use Rspamd with a Redis backend that supports clustering.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Greylisting Servers: Postgrey vs Sqlgrey vs Rspamd Greylisting",
  "description": "Compare Postgrey, Sqlgrey, and Rspamd greylisting for self-hosted email servers. Learn how greylisting blocks 70-90% of spam, Docker deployment, and configuration guides.",
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
