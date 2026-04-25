---
title: "SpamAssassin vs Rspamd vs Amavis: Best Self-Hosted Spam Filtering 2026"
date: 2026-04-26
tags: ["comparison", "guide", "self-hosted", "email", "spam-filtering", "security"]
draft: false
description: "Compare the top open-source spam filtering solutions for self-hosted email servers — SpamAssassin, Rspamd, and Amavis — with Docker Compose configs, scoring systems, and deployment guides."
---

If you run a self-hosted email server, spam filtering is not optional — it's the difference between a usable inbox and an unusable one. Every day, over 300 billion emails are sent worldwide, and roughly half of them are spam. Without a proper filtering layer, your Postfix or Dovecot setup will be overwhelmed within hours.

The three most widely used open-source spam filtering solutions are **Apache SpamAssassin**, **Rspamd**, and **Amavis** (AMaViS — A Mail Virus Scanner). Each takes a different architectural approach, and the choice depends on your throughput requirements, integration preferences, and operational complexity tolerance.

This guide compares all three, with real Docker Compose configurations and deployment instructions, so you can pick the right spam filter for your mail server.

## Why Self-Hosted Spam Filtering Matters

Cloud email providers like Gmail and Outlook handle spam detection transparently — you never think about it. But when you self-host your own mail server using Postfix, Dovecot, or Stalwart, you're responsible for every layer of the email stack, including filtering unwanted messages.

A self-hosted spam filter gives you:

- **Full control over filtering rules** — whitelist, blacklist, and custom scoring that fits your organization
- **No data leakage** — emails never leave your infrastructure for analysis
- **Customizable sensitivity** — tune false positive/negative tradeoffs to your needs
- **Integration with local threat intelligence** — combine with RBLs, DNSWL, and local blocklists
- **Transparency** — understand exactly why a message was scored as spam, with full header analysis

For anyone running a self-hosted email server — whether for personal use, small business, or enterprise — investing in a robust spam filtering solution is one of the highest-impact infrastructure decisions you can make.

## Apache SpamAssassin: The Veteran

**Apache SpamAssassin** has been the gold standard in open-source spam filtering since 2001. Now maintained by the Apache Software Foundation, it uses a Bayesian statistical approach combined with a vast collection of scoring rules to evaluate incoming email.

| Attribute | Value |
|---|---|
| **GitHub Stars** | 331 |
| **Primary Language** | Perl |
| **Last Updated** | April 2026 |
| **License** | Apache 2.0 |
| **Website** | [spamassassin.apache.org](https://spamassassin.apache.org) |

### How SpamAssassin Works

SpamAssassin evaluates each email against hundreds of tests. Each test contributes a positive or negative score. If the total score exceeds a configurable threshold (default: 5.0), the message is flagged as spam.

Tests include:

- **Header analysis** — suspicious `From`, `Subject`, or `Received` headers
- **Body pattern matching** — regex-based detection of spam-like content
- **Bayesian filtering** — statistical analysis based on trained ham/spam corpora
- **Network checks** — DNS blocklists (DNSBL), SPF, DKIM, and Razor/Pyzor/DCC distributed checksums
- **URIBL lookups** — checking URLs in the message body against known spam domains

### SpamAssassin Configuration

Here's a minimal `local.cf` configuration for a production deployment:

```
# /etc/spamassassin/local.cf

# Required score to mark as spam
required_score 5.0

# Enable Bayesian filtering
use_bayes 1
use_bayes_rules 1
bayes_auto_learn 1

# Enable network checks
skip_rbl_checks 0
use_razor2 1
use_pyzor 1

# Add headers
rewrite_header Subject ***** SPAM *****
report_safe 0

# Whitelist/Blacklist
whitelist_from *@mycompany.com
blacklist_from *@known-spammer.example
```

### Deploying SpamAssassin with Docker

While SpamAssassin doesn't have an official Docker image, the community-maintained image from LinuxServer.io works well:

```yaml
services:
  spamassassin:
    image: lscr.io/linuxserver/spamassassin:latest
    container_name: spamassassin
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    volumes:
      - ./config:/config
      - ./mail:/mail
    ports:
      - 783:783
    restart: unless-stopped
```

For integration with Postfix, configure `master.cf` to pipe incoming mail through SpamAssassin's `spamd` daemon:

```
smtp      inet  n       -       y       -       -       smtpd
  -o content_filter=spamassassin
spamassassin unix -     n       n       -       -       pipe
  user=spamd argv=/usr/bin/spamc -f -e /usr/sbin/sendmail -oi -f ${sender} ${recipient}
```

## Rspamd: The Modern Challenger

**Rspamd** is a high-performance, modular spam filtering system written in C. It was designed from the ground up as a replacement for SpamAssassin, offering significantly faster processing speeds and a more modern feature set.

| Attribute | Value |
|---|---|
| **GitHub Stars** | 2,439 |
| **Primary Language** | C |
| **Last Updated** | April 2026 |
| **License** | Apache 2.0 (BSD for some modules) |
| **Website** | [rspamd.com](https://rspamd.com) |

### Why Rspamd Is Faster

Rspamd's performance advantage comes from several architectural decisions:

- **C implementation** — native code vs. Perl interpreter
- **Asynchronous I/O** — all network operations are non-blocking
- **Hyperscan integration** — regex matching using Intel's high-performance regex engine
- **Lua scripting** — lightweight, embeddable scripting for custom rules
- **Built-in caching** — frequent operations are cached in memory

In real-world benchmarks, Rspamd processes messages **5-10x faster** than SpamAssassin, making it the preferred choice for high-volume mail servers.

### Rspamd Architecture

Rspamd uses a worker-based architecture:

- **Normal worker** — handles email scanning requests
- **Controller worker** — provides the web UI and HTTP API
- **Proxy worker** — sits in front of normal workers for load balancing

The system integrates with Redis for Bayesian databases, fuzzy storage, and rate limiting.

### Official Docker Compose Configuration

Here's the official Rspamd Docker Compose setup (sourced from the [rspamd-docker repository](https://github.com/rspamd/rspamd-docker)):

```yaml
services:
  rspamd:
    build:
      context: "."
      dockerfile: "Dockerfile.rspamd"
    container_name: rspamd
    depends_on:
      - unbound
      - redis
    environment:
      - RSPAMD_DNS_SERVERS=round-robin:192.0.2.254:53
      - RSPAMD_REDIS_SERVERS=rspamd-redis
      - RSPAMD_USE_BAYES=1
    networks:
      - rspamd
    ports:
      - "127.0.0.1:11332:11332"
      - "127.0.0.1:11333:11333"
      - "127.0.0.1:11334:11334"
    volumes:
      - rspamd-db:/var/lib/rspamd

  redis:
    container_name: rspamd-redis
    command: "redis-server --save 60 1 --loglevel warning"
    image: "redis:latest"
    networks:
      - rspamd
    volumes:
      - redis-data:/data

  unbound:
    container_name: rspamd-unbound
    image: "mvance/unbound:latest"
    networks:
      rspamd:
        ipv4_address: 192.0.2.254

networks:
  rspamd:
    ipam:
      config:
        - subnet: 192.0.2.0/24

volumes:
  redis-data:
  rspamd-db:
```

### Rspamd Web UI

One of Rspamd's standout features is its built-in web dashboard. Access it at `http://your-server:11334` to:

- View scanning statistics and score distributions
- Inspect individual message headers and rule matches
- Manage symbol scores and custom maps
- Monitor throughput and worker status

### Custom Rule Example

Rspamd uses Lua for custom rules. Here's an example that scores messages with suspicious `Reply-To` headers:

```lua
-- /etc/rspamd/local.d/suspicious_replyto.lua
local rspamd_util = require "rspamd_util"

rspamd_config.SUSPICIOUS_REPLYTO = {
  description = "Suspicious Reply-To header detected",
  score = 3.0,
  callback = function(task)
    local reply_to = task:get_header('Reply-To')
    local from = task:get_header('From')
    if reply_to and from and reply_to ~= from then
      return true
    end
    return false
  end
}
```

## Amavis: The Content Filter Framework

**Amavis** (A Mail Virus Scanner) is a high-performance interface between mail transfer agents (MTAs) and content checkers. Unlike SpamAssassin and Rspamd, Amavis is not a spam filter by itself — it's a framework that orchestrates multiple content analysis tools.

| Attribute | Value |
|---|---|
| **GitHub Stars** | No official GitHub repo (hosted on amavis.org) |
| **Primary Language** | Perl |
| **License** | GPL 2.0+ |
| **Website** | [amavis.org](https://www.amavis.org) |

### How Amavis Works

Amavis acts as a middleware between your MTA (Postfix, Exim, Sendmail) and one or more content checkers:

```
Email → MTA → Amavis → [SpamAssassin, ClamAV, DKIM, ARC, ...] → MTA → Delivery
```

The typical Amavis deployment combines:
- **SpamAssassin** for spam scoring
- **ClamAV** for virus/malware scanning
- **OpenDKIM** for DKIM signing and verification
- **ARC** for Authenticated Received Chain handling

This means Amavis provides a **unified interface** for all content filtering, not just spam detection.

### Amavis Configuration

Here's a production-ready `amavisd.conf` configuration:

```perl
# /etc/amavis/conf.d/50-user

use strict;

# Hostname and domain
$myhostname = 'mail.example.com';
$mydomain = 'example.com';

# Listening address
$inet_socket_port = [10024, 10026];

# Enable spam and virus checking
@bypass_virus_checks_maps = (
   \%bypass_virus_checks, \@bypass_virus_checks_acl, \$bypass_virus_checks_re);

@bypass_spam_checks_maps = (
   \%bypass_spam_checks, \@bypass_spam_checks_acl, \$bypass_spam_checks_re);

# SpamAssassin integration
$sa_spam_subject_tag = '***SPAM*** ';
$sa_tag_level_deflt  = 2.0;    # Add spam info headers if at or above this level
$sa_tag2_level_deflt = 6.31;   # Add 'spam detected' headers at or above this level
$sa_kill_level_deflt = 6.31;   # Triggers spam evasive actions
$sa_dsn_cutoff_level = 10;     # Spam level beyond which no DSN is returned

# Quarantine
$virus_quarantine_method = 'local:virus-quarantine';
$spam_quarantine_method = 'local:spam-quarantine';

# Logging
$log_level = 1;

1;  # Ensure a defined return
```

### Deploying Amavis with Docker

Amavis doesn't have an official Docker image, but the mlan/docker-postfix-amavis community image provides a working setup:

```yaml
services:
  mailserver:
    image: mlan/postfix-amavis:latest
    container_name: mailserver
    hostname: mail.example.com
    environment:
      - MY_HOSTNAME=mail.example.com
      - MY_DOMAIN=example.com
      - MY_NETWORKS=172.0.0.0/8
      - POSTFIX_INET_PROTOCOLS=ipv4
    ports:
      - "25:25"
      - "587:587"
      - "10024:10024"
    volumes:
      - ./maildata:/var/mail
      - ./config:/etc/amavis/conf.d
    restart: unless-stopped
```

### Postfix Integration

Configure Postfix to send mail through Amavis by editing `master.cf`:

```
smtp      inet  n       -       y       -       -       smtpd
  -o content_filter=smtp-amavis:[127.0.0.1]:10024

smtp-amavis unix -      -       y       -       2       smtp
  -o smtp_data_done_timeout=1200
  -o smtp_send_xforward_command=yes
  -o disable_dns_lookups=yes

127.0.0.1:10025 inet n  -       y       -       -       smtpd
  -o content_filter=
  -o local_recipient_maps=
  -o relay_recipient_maps=
  -o smtpd_restriction_classes=
  -o smtpd_client_restrictions=
  -o smtpd_helo_restrictions=
  -o smtpd_sender_restrictions=
  -o smtpd_recipient_restrictions=permit_mynetworks,reject
  -o mynetworks=127.0.0.0/8
  -o smtpd_authorized_xforward_hosts=127.0.0.0/8
```

## Feature Comparison Table

| Feature | SpamAssassin | Rspamd | Amavis |
|---|---|---|---|
| **Primary Language** | Perl | C | Perl |
| **Architecture** | Monolithic filter | Modular worker system | Content filter framework |
| **Built-in Web UI** | No (via MailWatch) | Yes | No |
| **HTTP API** | No | Yes | No |
| **Bayesian Filtering** | Yes | Yes | Via SpamAssassin plugin |
| **DNSBL Integration** | Yes | Yes | Via SpamAssassin plugin |
| **Virus Scanning** | No (via external) | Via external modules | Yes (ClamAV native) |
| **DKIM Support** | Via external | Yes (built-in) | Yes (built-in) |
| **ARC Support** | No | Yes | Yes |
| **Rate Limiting** | No | Yes (Redis-based) | No |
| **Greylisting** | Via Milter | Yes (built-in) | Via Milter |
| **Elasticsearch Output** | No | Yes | No |
| **Throughput** | ~100 msg/sec | ~500-1000 msg/sec | ~100 msg/sec |
| **Memory Usage** | Medium (~200MB) | Low (~100MB) | Medium (~300MB+) |
| **Docker Image** | Community (LSIO) | Official | Community |
| **Learning Curve** | Medium | Low | High |
| **Community Activity** | Steady | Very Active | Slow |

## Which One Should You Choose?

### Choose Rspamd if:
- You need **high performance** — it's 5-10x faster than SpamAssassin
- You want a **modern web UI** for monitoring and management
- You need **built-in DKIM signing** and ARC support
- You're running a **high-volume mail server** (hundreds of messages per minute)
- You want **greylisting and rate limiting** out of the box

Rspamd is the best choice for most new self-hosted email deployments in 2026. Its active development, superior performance, and comprehensive feature set make it the default recommendation.

### Choose SpamAssassin if:
- You have an **existing Postfix/Exim setup** already using SpamAssassin
- You need the **largest rule set** (hundreds of community-contributed rules)
- You rely on **Razor, Pyzor, or DCC** distributed checksum networks
- Your mail volume is **low to moderate** (under 100 messages per minute)
- You prefer a **mature, well-documented** solution with decades of battle testing

SpamAssassin remains a solid choice for personal mail servers and small deployments. Its extensive rule ecosystem and proven track record mean it catches spam effectively, even if it's slower than Rspamd.

### Choose Amavis if:
- You need a **unified content filtering** solution (spam + virus + DKIM in one)
- You want to **orchestrate multiple checkers** through a single interface
- You're running a **legacy mail server** that already uses Amavis
- You need **quarantine management** with Amavis's built-in quarantine system
- You're comfortable with **Perl configuration** and don't need a web UI

Amavis fills a unique niche as a content filter orchestrator. If you want spam filtering AND virus scanning AND DKIM signing through a single pipe, Amavis is the right architecture. But for spam-only filtering, Rspamd or SpamAssassin are simpler choices.

## Recommended Architecture for 2026

For most self-hosted email server setups in 2026, we recommend this architecture:

```
Internet → Postfix → Rspamd (port 11332) → Postfix (port 10025) → Dovecot
                           ↓
                       Redis (Bayesian DB)
                           ↓
                    Unbound (DNS resolver)
```

This setup gives you:
1. **Fast scanning** — Rspamd processes each message in under 50ms
2. **Bayesian learning** — Redis stores trained ham/spam databases
3. **DNS security** — Unbound provides DNSSEC-validating resolution for DNSBL lookups
4. **Web monitoring** — Rspamd's built-in UI at port 11334
5. **Simple integration** — Postfix content_filter directive points to Rspamd

For environments that need virus scanning, add ClamAV as a sidecar:

```yaml
services:
  clamav:
    image: clamav/clamav:latest
    container_name: clamav
    ports:
      - "3310:3310"
    volumes:
      - clamav-db:/var/lib/clamav
    restart: unless-stopped
```

Then configure Rspamd's `external_services.conf` to use ClamAV:

```
# /etc/rspamd/local.d/external_services.conf
clamav {
  servers = "clamav:3310";
  symbol = "CLAM_VIRUS";
  type = "clamav";
  log_clean = false;
  scan_mime_parts = false;
  scan_text_mime = false;
  scan_image_mime = false;
  max_size = 20000000;
}
```

## Tuning Spam Scores

Regardless of which filter you choose, tuning is essential. Start with these principles:

1. **Set an initial threshold** — 5.0 for SpamAssassin, 6-8 for Rspamd
2. **Monitor false positives** for 2-4 weeks before adjusting
3. **Whitelist known good senders** — your customers, partners, and internal systems
4. **Use greylisting** to reduce spam volume by 50-80% before it reaches the filter
5. **Train Bayesian databases** with at least 1,000 ham and 1,000 spam messages
6. **Review score distributions** weekly to identify rules that are too aggressive or too lenient

For Rspamd, use the web UI to view score distributions:

```bash
# View top-scoring symbols from the CLI
curl -s http://localhost:11334/statistics | python3 -m json.tool
```

For SpamAssassin, use `sa-learn` to train the Bayesian filter:

```bash
# Train on ham (good email)
sa-learn --ham /path/to/inbox/cur/

# Train on spam
sa-learn --spam /path/to/spam/cur/

# Report statistics
sa-learn --dump magic
```

## Migrating Between Filters

If you're switching from SpamAssassin to Rspamd (the most common migration):

1. **Run both in parallel** for 1-2 weeks to compare results
2. **Export SpamAssassin's whitelist/blacklist** to Rspamd's multimap format
3. **Train Rspamd's Bayesian database** using the same corpus as SpamAssassin
4. **Adjust Rspamd's symbol scores** to match your current false positive rate
5. **Switch the Postfix content_filter** to point to Rspamd once confident
6. **Monitor for 48 hours** before decommissioning SpamAssassin

For Amavis-to-Rspamd migrations, note that Rspamd handles DKIM signing and ARC natively, so you may be able to simplify your pipeline by removing Amavis entirely and using Rspamd for content filtering plus DKIM.

## FAQ

### Which spam filter has the best detection rate?

Rspamd generally achieves the best detection rate in 2026 due to its modern rule set, Hyperscan-based pattern matching, and active development. Independent benchmarks typically show Rspamd catching 97-99% of spam with false positive rates below 0.1%. SpamAssassin follows closely at 95-98% with slightly higher false positives. Amavis depends entirely on the SpamAssassin plugin it uses, so its detection rate mirrors SpamAssassin's.

### Can I run multiple spam filters together?

Yes. Some administrators run Amavis as a content filter framework with SpamAssassin as one of its plugins, while also running Rspamd at the MTA level. However, this adds latency and complexity. For most deployments, a single well-tuned filter is sufficient and preferable.

### How much RAM does each filter need?

SpamAssassin typically uses 150-250MB of RAM, depending on the number of loaded rules and the size of the Bayesian database. Rspamd is more efficient at 80-150MB, plus whatever Redis uses for its databases. Amavis uses 200-400MB since it runs as a Perl process and may spawn multiple child processes for concurrent scanning.

### Does Rspamd support the same DNSBLs as SpamAssassin?

Yes, Rspamd supports all common DNSBLs (Spamhaus, SURBL, URIBL, etc.) plus additional ones like SBL and XBL. The configuration syntax is different — Rspamd uses `rbl` groups in its configuration files — but the coverage is equivalent or better.

### How do I train the Bayesian filter?

For Rspamd, use the `rspamc` CLI tool:
```bash
rspamc learn_spam < spam_messages/
rspamc learn_ham < ham_messages/
```
For SpamAssassin, use `sa-learn`:
```bash
sa-learn --spam spam_dir/
sa-learn --ham ham_dir/
```
Both filters need at least 1,000 examples of each category for effective Bayesian classification.

### Is Rspamd compatible with Postfix and Exim?

Yes. Rspamd works with both Postfix (via `content_filter` or `milter` integration) and Exim (via the `acl_smtp_data` hook). The Postfix milter integration is the recommended approach for new deployments, as it provides better performance than the content_filter pipe method.

### Can I use these filters with Docker mailserver solutions?

Absolutely. LinuxServer.io provides Docker images for SpamAssassin. Rspamd has official Docker images via the `rspamd/rspamd-docker` repository. For Mail-in-a-Box or Docker Mailserver solutions, Rspamd is typically the default or recommended spam filter due to its performance and Docker-native design.

### What about virus scanning?

Neither SpamAssassin nor Rspamd performs virus scanning natively. SpamAssassin can integrate ClamAV via external plugins, and Rspamd supports virus scanning through its `external_services` module (supporting ClamAV, SavAPI, and others). Amavis natively integrates ClamAV as part of its content filtering pipeline. For a complete email security solution, pair your spam filter with ClamAV running as a separate service.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "SpamAssassin vs Rspamd vs Amavis: Best Self-Hosted Spam Filtering 2026",
  "description": "Compare the top open-source spam filtering solutions for self-hosted email servers — SpamAssassin, Rspamd, and Amavis — with Docker Compose configs, scoring systems, and deployment guides.",
  "datePublished": "2026-04-26",
  "dateModified": "2026-04-26",
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

For related reading, see our [complete self-hosted email server guide with Postfix, Dovecot, and Rspamd](../self-hosted-email-server-postfix-dovecot-rspamd-complete-guide-2026/) and [DMARC analysis and email authentication guide](../self-hosted-dmarc-analysis-email-authentication-parsedmarc-opendmarc-guide-2026/). If you're also looking to protect your inbox from phishing, check our [self-hosted email alias guide](../2026-04-20-simplelogin-vs-anonaddy-vs-forwardemail-self-hosted-email-alias-guide-2026/).
