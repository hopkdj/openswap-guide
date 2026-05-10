---
title: "Self-Hosted SMTP Milter Management: milter-manager vs rspamd vs OpenDKIM"
date: "2026-05-10"
tags: ["email", "smtp", "milter", "spam-filtering", "postfix", "security"]
draft: false
---

The Milter (Mail Filter) API is Sendmail and Postfix protocol that allows external programs to inspect and modify email messages during the SMTP transaction. Milters are the backbone of server-side email security — handling spam detection, DKIM signing, virus scanning, content filtering, and policy enforcement. This guide compares three open-source milter implementations: **milter-manager** (unified milter framework), **rspamd** (high-performance spam filter with milter interface), and **OpenDKIM** (DKIM signing and verification via milter).

## Why Use Milters for Email Security?

Running an email server without milters is like running a web server without a firewall. Milters operate at the SMTP protocol level, meaning they can reject spam and malicious messages before they are accepted into your mail queue — saving storage, bandwidth, and processing time. Unlike post-delivery filters (like Sieve scripts), milters act during the SMTP conversation itself, allowing senders to receive immediate rejection responses rather than bounce messages hours later.

Self-hosting your milter stack gives you complete control over email filtering rules, DKIM key management, and spam scoring thresholds. You are not subject to the false-positive rates of third-party filtering services, and your email content never leaves your servers.

The three tools we compare represent different approaches to the milter ecosystem:

| Feature | milter-manager | rspamd | OpenDKIM |
|---------|---------------|--------|----------|
| **Primary Purpose** | Unified milter framework | Spam and malware filtering | DKIM signing and verification |
| **Type** | Milter aggregator/spawner | Full-featured spam filter | DKIM milter |
| **Language** | Ruby (core), C (plugins) | C (highly optimized) | C |
| **Spam Filtering** | Via child milters (SpamAssassin, etc.) | Yes (built-in, Rspamd-specific) | No |
| **DKIM Support** | Via child milters | Yes (built-in) | Yes (primary function) |
| **Virus Scanning** | Via child milters (ClamAV) | Yes (built-in ClamAV integration) | No |
| **Bayesian Filtering** | Via child milters | Yes (built-in) | No |
| **Web Interface** | No | Yes (rspamd web UI) | No |
| **GitHub Stars** | 57 | 2,440+ | 113 |
| **Last Updated** | May 2026 | Active | Jul 2024 |
| **License** | MIT | Apache 2.0 / BSD | BSD |

## milter-manager: Unified Milter Framework

milter-manager is a framework that simplifies the deployment and management of multiple milters. Instead of configuring each milter separately with Postfix, you configure milter-manager once, and it spawns and manages child milter processes.

### Key Features

- **Centralized milter management**: One configuration file controls all child milters
- **Automatic process management**: Spawns, monitors, and restarts child milter processes
- **Policy-based milter selection**: Apply different milter chains based on sender, recipient, or message characteristics
- **Performance optimization**: Runs milters in parallel when possible, with configurable connection pooling
- **Status monitoring**: Built-in health checks and status reporting
- **Ruby configuration**: Flexible, expressive configuration syntax

### Docker Compose Deployment

```yaml
version: '3.8'
services:
  milter-manager:
    image: milter-manager/milter-manager:latest
    ports:
      - "10025:10025"
    volumes:
      - ./milter-manager.conf:/etc/milter-manager/milter-manager.conf:ro
      - ./run:/var/run/milter-manager
    environment:
      - MILTER_MANAGER_LOG_LEVEL=info
    depends_on:
      - rspamd
      - clamav

  rspamd:
    image: rspamd/rspamd:latest
    ports:
      - "11332:11332"
      - "11334:11334"
    volumes:
      - ./rspamd.conf:/etc/rspamd/rspamd.conf:ro
      - ./rspamd-local.d:/etc/rspamd/local.d:ro

  clamav:
    image: clamav/clamav:latest
    volumes:
      - ./clamav-data:/var/lib/clamav

volumes:
  clamav-data:
```

### Configuration Example

```ruby
# /etc/milter-manager/milter-manager.conf

# Define the milter-manager listening socket
define_milter("milter-manager") do |milter|
  milter.connection_spec = "inet:10025@localhost"
  milter.add_unix_listener("/var/run/milter-manager/milter-manager.sock")
end

# Add rspamd as a child milter
define_milter("rspamd") do |milter|
  milter.connection_spec = "inet:11332@localhost"
  milter.enabled = true
  milter.applicable_conditions = ["Reject"]
  milter.fallback_status = "accept"
end

# Add ClamAV for virus scanning
define_milter("clamav-milter") do |milter|
  milter.connection_spec = "inet:3310@localhost"
  milter.enabled = true
  milter.applicable_conditions = ["Reject"]
  milter.fallback_status = "accept"
end
```

### Postfix Integration

```bash
# In /etc/postfix/main.cf
smtpd_milters = inet:localhost:10025
non_smtpd_milters = inet:localhost:10025
milter_default_action = accept
milter_protocol = 6
```

## rspamd: High-Performance Spam Filter

rspamd is a fast, modular spam filtering system written in C. It is significantly faster than SpamAssassin (the traditional choice) and includes built-in milter support, making it easy to integrate with Postfix and other MTAs.

### Key Features

- **High performance**: C-based architecture handles millions of messages per day
- **Modular design**: DNSBL, SPF, DKIM, DMARC, Bayesian, fuzzy hash, and neural network modules
- **Built-in milter mode**: Direct milter interface — no wrapper needed
- **Web UI**: Real-time statistics, symbol inspection, and manual training interface
- **Machine learning**: Neural network-based spam detection that improves over time
- **Redis integration**: Fast caching and shared state across multiple workers
- **Custom rule engine**: Write filtering rules in Lua with full access to message content

### Docker Compose Deployment

```yaml
version: '3.8'
services:
  rspamd:
    image: rspamd/rspamd:latest
    ports:
      - "11332:11332"
      - "11333:11333"
      - "11334:11334"
    volumes:
      - ./rspamd/local.d:/etc/rspamd/local.d:ro
      - ./rspamd/override.d:/etc/rspamd/override.d:ro
      - rspamd-data:/var/lib/rspamd
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  postfix:
    image: postfix-mta:latest
    ports:
      - "25:25"
    environment:
      - RSPAMD_HOST=rspamd
      - RSPAMD_PORT=11332

volumes:
  rspamd-data:
```

### rspamd Local Configuration

```lua
# /etc/rspamd/local.d/milter_headers.conf
use = ["x-spam-flag", "x-spam-status", "authentication-results"]

# /etc/rspamd/local.d/dkim_signing.conf
path = "/var/lib/rspamd/dkim/$domain.$selector.key"
selector = "dkim"

# /etc/rspamd/local.d/redis.conf
servers = "redis:6379";

# /etc/rspamd/local.d/classifier-bayes.conf
backend = "redis";
```

### Postfix Integration

```bash
# In /etc/postfix/main.cf
smtpd_milters = inet:rspamd:11332
non_smtpd_milters = inet:rspamd:11332
milter_default_action = accept
milter_protocol = 6
```

## OpenDKIM: DKIM Signing and Verification

OpenDKIM implements the DomainKeys Identified Mail (DKIM) standard, providing cryptographic signing and verification of email messages. While it does not filter spam directly, it is essential infrastructure for email deliverability — messages signed with DKIM are far less likely to land in spam folders.

### Key Features

- **DKIM signing**: Automatically signs outgoing messages with your domain key
- **DKIM verification**: Verifies signatures on incoming messages and adds Authentication-Results headers
- **Key management**: Supports multiple domains and selectors with automatic key rotation
- **Trusted Hosts list**: Controls which senders get their messages signed
- **Canonicalization**: Supports both relaxed and strict canonicalization modes
- **Postfix/Sendmail integration**: Native milter interface for both MTAs

### Docker Compose Deployment

```yaml
version: '3.8'
services:
  opendkim:
    image: linuxserver/opendkim:latest
    ports:
      - "8891:8891"
    volumes:
      - ./opendkim-keys:/etc/opendkim/keys
      - ./opendkim.conf:/etc/opendkim.conf:ro
      - ./opendkim-trusted:/etc/opendkim/trusted
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Etc/UTC

  postfix:
    image: postfix-mta:latest
    ports:
      - "25:25"
    environment:
      - OPENDKIM_HOST=opendkim
      - OPENDKIM_PORT=8891
```

### OpenDKIM Configuration

```bash
# /etc/opendkim.conf
Syslog                  yes
SyslogSuccess           yes
LogWhy                  yes
Canonicalization        relaxed/simple
Mode                    sv
SubDomains              no
OversignHeaders         From

# Socket for Postfix milter connection
Socket                  inet:8891@localhost

# Signing table
SigningTable            refile:/etc/opendkim/SigningTable

# Key table
KeyTable                refile:/etc/opendkim/KeyTable

# Trusted hosts
ExternalIgnoreList      refile:/etc/opendkim/trusted
InternalHosts           refile:/etc/opendkim/trusted
```

### Key Generation and DNS

```bash
# Generate a DKIM key pair
opendkim-genkey -s default -d example.com -D /etc/opendkim/keys/example.com/

# The DNS TXT record to publish:
# default._domainkey.example.com IN TXT "v=DKIM1; k=rsa; p=MIGfMA0GCSq..."

# Add to signing table:
# *@example.com default._domainkey.example.com

# Add to key table:
# default._domainkey.example.com example.com:default:/etc/opendkim/keys/example.com/default.private
```

## Choosing the Right Milter Solution

These three tools serve different but complementary roles in a complete email security stack:

**Use milter-manager when:**
- You need to orchestrate multiple milters (rspamd, ClamAV, OpenDKIM, custom filters)
- You want a single point of configuration and management
- You need policy-based milter routing (different filter chains for different message types)
- You run a medium-to-large mail server with complex filtering requirements

**Use rspamd when:**
- You need high-performance spam and malware filtering
- You want a modern replacement for SpamAssassin
- You need a web UI for monitoring and manual training
- You require DKIM, SPF, and DMARC checks as part of your scoring pipeline

**Use OpenDKIM when:**
- You need DKIM signing for outbound email deliverability
- You want a lightweight, dedicated DKIM solution
- You prefer a simple, well-understood tool with decades of production use

**Best practice for production:** Run rspamd as your primary spam filter (in milter mode), OpenDKIM for DKIM signing/verification, and optionally milter-manager as the orchestrator if you have additional milters to manage. Many organizations run rspamd and OpenDKIM directly in Postfix without milter-manager, using separate `smtpd_milters` entries.

For email server setup fundamentals, see our [Postfix vs Exim MTA comparison](../2026-04-29-postfix-vs-exim-self-hosted-mta-comparison-guide/) and our [complete email server guide](../self-hosted-email-server-postfix-dovecot-rspamd-complete-guide-2026/). For spam filtering alternatives, check our [SpamAssassin vs rspamd vs Amavis guide](../2026-04-26-spamassassin-vs-rspamd-vs-amavis-self-hosted-spam-filtering-guide/).

## FAQ

### What is the difference between a milter and a content filter?

A milter operates during the SMTP transaction, allowing it to inspect and modify messages before they are accepted into the mail queue. A content filter (like procmail or Sieve) processes messages after delivery. Milters can reject messages at the SMTP level, saving resources and providing immediate feedback to senders.

### Can I run rspamd and OpenDKIM together?

Yes, and you should. rspamd handles spam filtering, scoring, and some DKIM verification, while OpenDKIM provides dedicated DKIM signing for outbound mail. Configure both in Postfix `smtpd_milters` as comma-separated values, or use milter-manager to orchestrate them.

### Is rspamd a drop-in replacement for SpamAssassin?

Functionally yes — rspamd provides the same spam filtering capabilities — but the configuration syntax and architecture are completely different. rspamd is significantly faster and includes a web UI, but migrating requires rewriting filter rules and adjusting scoring thresholds.

### How often should I rotate DKIM keys?

Best practice is to rotate DKIM keys every 6-12 months. OpenDKIM supports multiple selectors simultaneously, allowing you to publish a new key in DNS while the old key remains active, then switch the signing table entry and remove the old DNS record after a transition period.

### Does milter-manager add significant overhead?

milter-manager introduces minimal overhead — it primarily acts as a proxy and process manager. The actual filtering work is done by the child milters. In benchmarks, milter-manager adds less than 10 milliseconds per message compared to direct milter connections.

### Can rspamd replace OpenDKIM entirely?

rspamd includes DKIM signing and verification capabilities, so for many deployments it can replace OpenDKIM. However, OpenDKIM remains the reference implementation and is preferred when you need fine-grained control over DKIM key management, canonicalization modes, or compliance with specific DKIM policy requirements.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted SMTP Milter Management: milter-manager vs rspamd vs OpenDKIM",
  "description": "Compare milter-manager, rspamd, and OpenDKIM for self-hosted SMTP email filtering. Learn about milter configuration, DKIM signing, spam detection, and Postfix integration.",
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
