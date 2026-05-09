---
title: "Self-Hosted Mail Reputation Monitoring 2026: Postfwd vs Rspamd vs Policyd"
date: "2026-05-09"
tags: ["email", "mail-server", "reputation", "spam-filtering", "postfix", "security"]
draft: false
---

Email deliverability depends heavily on your server's reputation. Major mailbox providers like Gmail, Outlook, and Yahoo track sending patterns, complaint rates, and authentication signals to determine whether your messages reach the inbox or the spam folder. Monitoring and protecting your mail server's reputation requires tools that analyze sending behavior, enforce policies, and detect abuse before it impacts your domain's standing.

## What Is Mail Reputation Monitoring?

Mail reputation monitoring involves tracking multiple signals that affect how receiving servers evaluate your email:

- **IP reputation**: Historical sending patterns associated with your server's IP address.
- **Domain reputation**: SPF, DKIM, and DMARC alignment rates for your sending domains.
- **Complaint rates**: The percentage of recipients marking your messages as spam.
- **Bounce rates**: Hard bounce ratios that indicate list quality problems.
- **Volume patterns**: Sudden spikes in sending volume that trigger rate limiting.

Self-hosted reputation monitoring tools integrate with your mail server (Postfix, Exim) to analyze traffic in real-time, enforce sending policies, and generate alerts when reputation-affecting patterns emerge.

## Rspamd

[Rspamd](https://github.com/rspamd/rspamd) is a fast, modular spam filtering and reputation analysis system. It's the most widely deployed open-source mail filtering solution, replacing SpamAssassin in many production environments.

### Key Features

- **Real-time scoring**: Messages are scored against hundreds of rules in milliseconds using compiled Lua bytecode.
- **Reputation module**: Tracks sending patterns per IP, domain, and user to identify anomalous behavior.
- **Bayesian learning**: Automatic classification learning from user feedback (spam/ham flags).
- **DKIM signing**: Built-in DKIM signing and verification with automatic key rotation.
- **Web interface**: Dashboard showing message statistics, rule hit rates, and reputation scores.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  rspamd:
    image: rspamd/rspamd:latest
    ports:
      - "11332:11332"  # Controller (web UI)
      - "11333:11333"  # Worker
      - "11334:11334"  # Normal worker
    volumes:
      - ./rspamd.conf:/etc/rspamd/rspamd.conf
      - ./local.d:/etc/rspamd/local.d
      - ./dkim:/var/lib/rspamd/dkim
      - rspamd_data:/var/lib/rspamd
    environment:
      - TZ=UTC

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

volumes:
  rspamd_data:
  redis_data:
```

### Reputation Configuration

The reputation module in Rspamd tracks per-sender and per-domain statistics:

```lua
# /etc/rspamd/local.d/reputation.conf
rules {
    DKIM_REPUTATION {
        dkim = true;
        spf = true;
    }
    FROM_REPUTATION {
        selector = "from";
        min_records = 10;
        positive_multiplier = 1.5;
        negative_multiplier = 2.0;
    }
}
```

### Strengths and Limitations

Rspamd excels at real-time message analysis with extremely low latency. The reputation module provides granular tracking of sending patterns. The web interface offers visibility into filtering decisions. However, Rspamd's configuration complexity can be daunting for administrators new to mail filtering.

## Postfwd

[Postfwd](https://github.com/postfwd/postfwd) is a Postfix policy daemon that enforces sending rules based on configurable criteria. It acts as a gatekeeper between your MTA and the outside world, evaluating each message against policy rules before acceptance.

### Key Features

- **Rule-based filtering**: Define complex policies using a simple configuration language with AND/OR logic.
- **Rate limiting**: Enforce per-user, per-domain, or per-IP sending rate limits to prevent abuse.
- **Greylisting**: Temporary rejection of unknown senders to reduce spam volume.
- **Postfix integration**: Seamless integration as a `check_policy_service` in Postfix.
- **Caching**: Built-in caching for frequently evaluated rules to minimize latency.

### Configuration Example

```perl
# /etc/postfwd.cf
# Rate limit: max 50 messages per hour per sender
id=RATE001;
    sender=@.*;
    action=rate(50/1h/450 Too many messages from this sender);

# Block known bad patterns
id=SPAM001;
    subject=~/(viagra|cialis|lottery)/i;
    action=reject(550 Message rejected due to content policy);

# Allow authenticated users higher limits
id=AUTH001;
    sasl_username=.*;
    action=rate(500/1h/450 Rate limit exceeded);

# Require DKIM for outbound mail
id=DKIM001;
    sender_domain=yourdomain.com;
    dkim=none;
    action=reject(550 Outbound mail must be DKIM signed);
```

### Postfix Integration

```bash
# /etc/postfix/main.cf
smtpd_recipient_restrictions =
    check_policy_service inet:127.0.0.1:10040,
    permit_sasl_authenticated,
    reject_unauth_destination

# /etc/postfix/master.cf
postfwd   unix  -       -       n       -       1       spawn
    user=nobody argv=/usr/sbin/postfwd --config=/etc/postfwd.cf
```

### Strengths and Limitations

Postfwd is lightweight and tightly integrated with Postfix. The rule language is straightforward for administrators familiar with Postfix configuration. Rate limiting is its strongest feature, preventing individual accounts from sending volumes that could damage domain reputation. However, Postfwd only works with Postfix and provides no spam scoring or content analysis.

## Policyd (Cluebringer)

[Policyd](https://github.com/policyd/policyd) (also known as Cluebringer) is a comprehensive policy daemon that provides quota management, access control, and reputation tracking for Postfix and other MTAs.

### Key Features

- **Quota management**: Track message counts, sizes, and recipients per user, domain, or IP with configurable limits.
- **Access control**: Fine-grained sender/recipient filtering with wildcard support.
- **Reputation tracking**: Historical data on sender behavior with automated reputation scoring.
- **Web administration**: PHP-based admin panel for managing policies, quotas, and viewing statistics.
- **Database backend**: MySQL/PostgreSQL storage for persistent policy data and historical reporting.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  policyd:
    image: policyd:latest
    ports:
      - "10031:10031"  # Policy service
      - "80:80"        # Web admin
    volumes:
      - ./policyd.conf:/etc/policyd/policyd.conf
      - ./webui:/var/www/policyd
    depends_on:
      - db

  db:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=policydpass
      - MYSQL_DATABASE=policyd
      - MYSQL_USER=policyd
      - MYSQL_PASSWORD=policydpass
    volumes:
      - policyd_data:/var/lib/mysql

volumes:
  policyd_data:
```

### Quota Configuration

```sql
-- Create a quota: max 100 messages per hour per sender
INSERT INTO quotas (name, track, period, verp, data)
VALUES ('Hourly Sender Limit', 'Sender:user@domain', 3600, 0, 100);

-- Create a quota: max 500 recipients per day per sender
INSERT INTO quotas (name, track, period, verp, data)
VALUES ('Daily Recipient Limit', 'Sender:user@domain', 86400, 0, 500);
```

### Strengths and Limitations

Policyd's quota management is the most comprehensive of the three tools. The web admin panel makes it easy to create and manage policies without editing configuration files. The database backend provides historical data for trend analysis. However, Policyd requires a database server, which adds operational complexity, and its development has slowed compared to Rspamd.

## Comparison Table

| Feature | Rspamd | Postfwd | Policyd |
|---------|--------|---------|---------|
| **Primary Function** | Spam filtering + reputation | Policy enforcement | Quota + access control |
| **MTA Support** | Postfix, Exim, others | Postfix only | Postfix, Exim |
| **Reputation Tracking** | Built-in module | Via rate rules | Database-backed scoring |
| **Rate Limiting** | Via ratelimit module | Native (strongest feature) | Via quotas |
| **Content Analysis** | 100+ scoring rules | Pattern matching only | None |
| **DKIM Support** | Signing + verification | Policy enforcement only | Policy enforcement only |
| **Web Interface** | Built-in dashboard | None | PHP admin panel |
| **Database Required** | Redis (recommended) | No | MySQL/PostgreSQL |
| **Min RAM** | 512MB | 128MB | 1GB |
| **Learning Curve** | Steep | Moderate | Moderate |
| **License** | Apache 2.0 | MIT | GPLv2 |
| **GitHub Stars** | ~2,400+ | ~200+ | ~100+ |

## Why Protect Your Mail Server's Reputation?

A damaged mail server reputation affects all outbound communications — transactional emails, marketing campaigns, and user notifications alike. Gmail and Yahoo's 2024 requirements mandate strict SPF/DKIM/DMARC alignment and low spam complaint rates. Without reputation monitoring, you won't know your scores are declining until messages start bouncing.

Self-hosted monitoring tools catch problems before they escalate. Rspamd's reputation module flags senders whose patterns change suddenly — a potential sign of compromised accounts. Postfwd's rate limits prevent a single user from sending volumes that trigger ISP throttling. Policyd's quotas provide hard caps that no sender can exceed.

For teams running full [email servers](../self-hosted-email-server-postfix-dovecot-rspamd-complete-guide-2026/), combining Rspamd for content filtering with Postfwd or Policyd for rate limiting provides defense in depth. Organizations managing multiple mail domains can also reference our guide on [email authentication](../2026-05-18-self-hosted-email-authentication-opendkim-rspamd-opendmarc-guide/) for comprehensive SPF, DKIM, and DMARC configuration.

When implementing reputation monitoring alongside existing mail infrastructure, consider how these tools integrate with your [WAF and bot protection](../self-hosted-waf-bot-protection-modsecurity-coraza-crowdsec-2026/) layer — both address different aspects of abuse prevention. For organizations managing [email deliverability](../self-hosted-email-deliverability-inbox-placement-guide-2026/), reputation monitoring provides the early warning system that prevents inbox placement problems before they occur.

## FAQ

### What is a good email sender reputation score?

Most mailbox providers don't publish exact scores, but industry benchmarks suggest: spam complaint rate below 0.1%, hard bounce rate below 2%, consistent sending volume, and 100% SPF/DKIM/DMARC alignment. Rspamd's internal scoring uses a scale where negative scores indicate spam likelihood — well-configured servers should see legitimate mail scoring below 5.0.

### How quickly does mail reputation recover after a problem?

Reputation recovery is gradual. Minor issues (brief spike in complaints) typically resolve within 1-2 weeks of normal sending. Major problems (being listed on a DNSBL) can take 2-4 weeks after delisting requests. Consistent good behavior over 30-90 days is usually needed for full recovery at major providers like Gmail.

### Can Rspamd replace a dedicated reputation monitoring service?

Rspamd's reputation module provides good internal tracking of your server's sending patterns. However, it doesn't monitor your reputation at external providers (Google Postmaster Tools, Microsoft SNDS). For comprehensive monitoring, combine Rspamd with external reputation checkers and feedback loop registrations.

### How do I set up rate limits that won't disrupt legitimate users?

Start with conservative limits: 100 messages per hour per authenticated user, 500 recipients per day. Monitor your traffic patterns for a week, then adjust limits to 2-3x the typical peak volume. This provides a safety margin for legitimate spikes (newsletter sends) while catching compromised accounts that send thousands of messages.

### Should I use Rspamd, Postfwd, or both?

They serve different purposes and work well together. Rspamd handles content analysis and spam scoring, while Postfwd enforces sending policies and rate limits. Run Rspamd as a milter (content filter) and Postfwd as a policy daemon (pre-queue check). This combination catches spam while preventing reputation damage from abuse.

### How do I check if my server's IP is on a DNS blacklist?

Use command-line tools like `dig` to query common DNSBLs: `dig +short 1.0.0.127.zen.spamhaus.org` (reverse your server's IP). Alternatively, use Rspamd's `rspamadm dnsbl` command or check via web services like MXToolbox. Self-hosted monitoring should include automated DNSBL checks at regular intervals.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Mail Reputation Monitoring 2026: Postfwd vs Rspamd vs Policyd",
  "description": "Compare Rspamd, Postfwd, and Policyd for self-hosted mail reputation monitoring and spam filtering. Includes Docker Compose configs and Postfix integration.",
  "datePublished": "2026-05-09",
  "dateModified": "2026-05-09",
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
