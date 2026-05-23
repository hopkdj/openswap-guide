---
title: "Self-Hosted SPF Validation Tools: pypolicyd-spf vs policyd-spf-perl vs spf-engine"
date: "2026-05-23"
tags: ["email", "security", "spf", "self-hosted"]
draft: false
---

Sender Policy Framework (SPF) is a DNS-based email authentication mechanism that helps prevent email spoofing. While SPF records are published in DNS, the actual validation happens at the receiving mail server. A self-hosted SPF validator checks incoming mail against the sender's published SPF record and assigns a pass/fail/softfail result that your mail server can use to accept, flag, or reject the message.

This guide compares three open-source SPF validation tools for Postfix: **pypolicyd-spf**, **policyd-spf-perl**, and **spf-engine** — each implementing the same protocol but with different performance characteristics, configuration approaches, and feature sets.

## How SPF Works

SPF works through DNS TXT records. A domain publishes an SPF record listing the mail servers authorized to send email on its behalf:

```
v=spf1 mx ip4:203.0.113.0/24 include:_spf.google.com -all
```

When a mail server receives a message claiming to be from `user@example.com`, it:

1. **Extracts the envelope sender domain** — `example.com`
2. **Queries DNS for the SPF record** — Looks up the TXT record
3. **Evaluates the policy** — Checks if the connecting IP matches any authorized mechanism
4. **Returns a result** — `pass`, `fail`, `softfail`, `neutral`, `none`, or `temperror`

The receiving mail server then uses this result to decide how to handle the message.

## Comparison Overview

| Feature | pypolicyd-spf | policyd-spf-perl | spf-engine |
|---------|--------------|-----------------|------------|
| **Language** | Python | Perl | Python |
| **License** | GPLv2 | Artistic/GPL | MIT |
| **GitHub Stars** | 180+ (forks) | CPAN package | 45+ |
| **Postfix Integration** | Policy daemon | Policy daemon | Policy daemon |
| **SPFv1 Support** | Full | Full | Full |
| **RFC 7208 Compliance** | Yes | Yes | Yes |
| **Skip HELO Check** | Configurable | Configurable | Configurable |
| **Whitelist Support** | Yes (config file) | Yes (config file) | Yes (config file) |
| **Rate Limiting** | No | No | No |
| **Logging** | Syslog | Syslog | Syslog |
| **Caching** | DNS TTL-based | DNS TTL-based | DNS TTL-based |
| **Dependencies** | `pyspf`, `py3dns` | `Mail::SPF` | `pyspf`, `py3dns` |
| **Docker Deployment** | Custom image | Custom image | Custom image |
| **Best For** | Python-based mail servers | Perl-based environments | Lightweight Python setup |

## pypolicyd-spf

[pypolicyd-spf](https://github.com/sdgathman/pypolicyd-spf) is a Python-based Postfix policy daemon that performs SPF validation. It uses the `pyspf` library for core SPF evaluation and integrates cleanly with Postfix's policy delegation protocol.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  policyd-spf:
    image: python:3.12-slim
    container_name: policyd-spf
    restart: unless-stopped
    volumes:
      - ./policyd-spf.cfg:/etc/postfix-policyd-spf-python/policyd-spf.conf:ro
      - ./policyd-spf.py:/usr/local/bin/policyd-spf:ro
    entrypoint: ["python3", "-u", "/usr/local/bin/policyd-spf"]
    networks:
      - postfix-net

networks:
  postfix-net:
    external: true
```

### Installation and Configuration

```bash
# Install dependencies
pip3 install pyspf py3dns

# Download policyd-spf
curl -o /usr/local/bin/policyd-spf   https://raw.githubusercontent.com/sdgathman/pypolicyd-spf/master/policyd-spf

chmod +x /usr/local/bin/policyd-spf
```

### Configuration File (policyd-spf.conf)

```ini
# /etc/postfix-policyd-spf-python/policyd-spf.conf

# Debug level: 0=normal, 1=verbose, 2=debug
debugLevel = 0

# Default SPF result for domains without SPF records
SPF_Not_Found = neutral

# Skip SPF check for HELO identities
skip_addresses = 127.0.0.0/8,::ffff:127.0.0.0/104,::1

# Maximum number of DNS lookups (RFC 7208 limit: 10)
max_dns_lookups = 10

# Whitelist: skip SPF check for trusted senders
whitelist = 203.0.113.0/24, 198.51.100.0/24

# HELO identity: use HELO domain if no MAIL FROM domain
HELO_relay_domains = relay.example.com

# Expose SPF result in Received-SPF header
Received-SPF_Header = yes
```

### Postfix Integration

Add to `/etc/postfix/main.cf`:

```ini
smtpd_recipient_restrictions =
    permit_mynetworks,
    permit_sasl_authenticated,
    reject_unauth_destination,
    check_policy_service unix:private/policyd-spf
```

And in `/etc/postfix/master.cf`:

```ini
policyd-spf  unix  -    n  n  -  0  spawn
    user=nobody argv=/usr/local/bin/policyd-spf
```

### How pypolicyd-spf Processes Mail

1. Postfix receives an incoming SMTP connection and extracts the envelope sender
2. Postfix delegates to pypolicyd-spf via the policy service interface
3. pypolicyd-spf queries DNS for the sender domain's SPF record
4. The `pyspf` library evaluates the SPF policy against the connecting IP
5. pypolicyd-spf returns the result to Postfix (`DUNNO`, `REJECT`, or `PREPEND`)
6. Postfix applies the result to the mail handling decision

## policyd-spf-perl

[policyd-spf-perl](https://metacpan.org/pod/Mail::SPF) is the Perl implementation of a Postfix SPF policy daemon, built on the `Mail::SPF` CPAN module. It's the original and most mature SPF validation tool for Postfix, with the widest deployment in production mail servers.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  policyd-spf-perl:
    image: perl:5.38-slim
    container_name: policyd-spf-perl
    restart: unless-stopped
    volumes:
      - ./policyd-spf.conf:/etc/postfix-policyd-spf-perl/policyd-spf.conf:ro
    command: >
      sh -c "cpanm Mail::SPF NetAddr::IP &&
             /usr/local/bin/policyd-spf /etc/postfix-policyd-spf-perl/policyd-spf.conf"
    networks:
      - postfix-net

networks:
  postfix-net:
    external: true
```

### Installation

```bash
# Install via CPAN
cpanm Mail::SPF NetAddr::IP Sys::Hostname

# Download the policy daemon script
curl -o /usr/sbin/policyd-spf   https://metacpan.org/release/MDOM/Mail-SPF-v2.9.0/source/script/policyd-spf

chmod +x /usr/sbin/policyd-spf
```

### Configuration File

```ini
# /etc/postfix-policyd-spf-perl/policyd-spf.conf

# Skip SPF checking for these IP ranges (trusted relays)
skip_addresses = 127.0.0.1/8

# HELO identities to check (relay domains)
HELO_relay_domains = example.com

# Whitelist addresses that bypass SPF
whitelist = 10.0.0.0/8

# Action for SPF fail (default: DUNNO = no action)
default_accept_action = DUNNO

# Action when SPF record has a temporary error
tempfail_action = DUNNO

# Debug logging
debug_level = 0
```

### Postfix Integration

Same as pypolicyd-spf — add to `main.cf`:

```ini
smtpd_recipient_restrictions =
    permit_mynetworks,
    permit_sasl_authenticated,
    reject_unauth_destination,
    check_policy_service unix:private/policyd-spf-perl
```

And in `master.cf`:

```ini
policyd-spf-perl  unix  -  n  n  -  0  spawn
    user=nobody argv=/usr/sbin/policyd-spf /etc/postfix-policyd-spf-perl/policyd-spf.conf
```

### Key Advantages

- **Mature and stable** — Deployed in thousands of production mail servers
- **Excellent DNS error handling** — Graceful handling of DNS timeouts, SERVFAIL, and NXDOMAIN responses
- **HELO identity checking** — Validates both MAIL FROM and HELO/EHLO identities
- **CPAN integration** — Easy installation and updates via the Perl package ecosystem
- **Well-documented** — Extensive man pages and configuration examples

## spf-engine

[spf-engine](https://github.com/SpinDriftTech/spf-engine) is a lightweight Python-based SPF validation engine designed for simplicity and easy integration with Postfix. It follows the same policy daemon protocol as the other tools but with a more minimal codebase and configuration.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  spf-engine:
    build: .
    container_name: spf-engine
    restart: unless-stopped
    volumes:
      - ./spf-engine.conf:/etc/spf-engine.conf:ro
    networks:
      - postfix-net

networks:
  postfix-net:
    external: true
```

### Dockerfile

```dockerfile
FROM python:3.12-slim
RUN pip install pyspf py3dns daemonize
COPY spf-engine.py /usr/local/bin/spf-engine
COPY spf-engine.conf /etc/spf-engine.conf
EXPOSE 10023
ENTRYPOINT ["python3", "/usr/local/bin/spf-engine"]
```

### Configuration File

```ini
# /etc/spf-engine.conf

[spf-engine]
# Bind address and port for Postfix policy daemon
bind_address = 127.0.0.1
bind_port = 10023

# Log level: DEBUG, INFO, WARNING, ERROR
log_level = INFO

# DNS lookup timeout (seconds)
dns_timeout = 5

# Maximum DNS lookups per SPF evaluation
max_lookups = 10

# Trusted relay networks (skip SPF check)
trusted_networks = 127.0.0.0/8, ::1

[whitelist]
# IP addresses that bypass SPF validation
skip = 203.0.113.0/24

[headers]
# Add Received-SPF header to passing messages
add_header = yes
```

### Integration with Postfix

```ini
# main.cf
smtpd_recipient_restrictions =
    permit_mynetworks,
    permit_sasl_authenticated,
    reject_unauth_destination,
    check_policy_service inet:127.0.0.1:10023
```

## SPF Result Actions in Postfix

Once an SPF validator returns a result, you need to decide how Postfix handles it. The typical approach uses `postfix-policyd-spf` results in `header_checks` or `smtpd_recipient_restrictions`:

```ini
# /etc/postfix/main.cf
smtpd_recipient_restrictions =
    permit_mynetworks,
    permit_sasl_authenticated,
    reject_unauth_destination,
    check_policy_service unix:private/policyd-spf

# Add SPF result to message headers
header_checks = regexp:/etc/postfix/header_checks

# /etc/postfix/header_checks
/^Received-SPF: fail/    WARN SPF check failed
/^Received-SPF: softfail/ WARN SPF softfail
```

For stricter enforcement, you can reject messages that fail SPF:

```ini
# In the policy daemon config or via milter
# Return REJECT for SPF fail
default_action = REJECT 450 4.7.25 SPF check failed
```

## Choosing the Right SPF Validator

**Use pypolicyd-spf when:**
- Your mail server stack is already Python-based
- You prefer Python for maintenance and customization
- You want good RFC 7208 compliance with a clean codebase

**Use policyd-spf-perl when:**
- You want the most mature and widely deployed solution
- Your system already has Perl installed (most Linux distributions)
- You need robust DNS error handling and HELO identity checking
- You prefer CPAN-based package management

**Use spf-engine when:**
- You want the simplest possible Python implementation
- You need a lightweight policy daemon with minimal dependencies
- You're building a custom mail handling pipeline

## Why Self-Host SPF Validation?

Running your own SPF validation gives you control over email filtering policies. Commercial email services (Gmail, Outlook) perform SPF checks internally, but when you host your own mail server, you need to implement validation yourself to protect against spoofing.

SPF is one pillar of email authentication, alongside DKIM (DomainKeys Identified Mail) and DMARC (Domain-based Message Authentication). Together, these three protocols form a defense-in-depth strategy against email spoofing and phishing. SPF validates the envelope sender, DKIM signs the message content, and DMARC ties them together with a published policy.

For organizations running mail servers, SPF validation is essential for compliance with email deliverability best practices. Major mailbox providers increasingly require senders to implement SPF, DKIM, and DMARC — and receivers should validate incoming mail against these standards.

For email security, see our [SPF vs DKIM vs DMARC guide](../2026-04-28-self-hosted-email-authentication-spf-dkim-dmarc-complete-guide-2026/). For lightweight SMTP servers, check our [Maddy vs Chasquid vs OpenSMTPD comparison](../2026-04-18-maddy-vs-chasquid-vs-opensmtpd-lightweight-smtp-servers-2026/). For milter-based mail filtering, our [SMTP milter management guide](../2026-04-18-self-hosted-smtp-milter-management-milter-manager-rspamd-opendkim-guide-2026/) covers advanced mail processing.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted SPF Validation Tools: pypolicyd-spf vs policyd-spf-perl vs spf-engine",
  "description": "Compare open-source SPF validation tools for Postfix: pypolicyd-spf, policyd-spf-perl, and spf-engine. Docker configs and Postfix integration.",
  "datePublished": "2026-05-23",
  "dateModified": "2026-05-23",
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

## FAQ

### What's the difference between SPF pass, fail, and softfail?

- **pass** — The sending IP is explicitly authorized by the domain's SPF record (`+all` or matching mechanisms)
- **fail** — The sending IP is explicitly NOT authorized (`-all`), and the message should be rejected
- **softfail** — The sending IP is likely not authorized (`~all`), but the domain owner is not requesting rejection. Mark the message as suspicious but typically still deliver it
- **neutral** — The domain owner makes no assertion (`?all`)
- **none** — The domain has no SPF record published

### Can SPF validation break legitimate email forwarding?

Yes, this is a known limitation called "SPF breakage." When email is forwarded through an intermediary server, the connecting IP changes to the forwarder's IP, which may not be in the original sender's SPF record. Solutions include: SRS (Sender Rewriting Scheme), which rewrites the envelope sender during forwarding, or using DKIM (which survives forwarding) as the primary authentication method.

### Should I reject mail that fails SPF?

It depends on your risk tolerance. Rejecting SPF-fail mail eliminates spoofed messages from that domain but may cause false positives if the domain's SPF record is misconfigured or if legitimate forwarding is in use. A common approach is to use `softfail` results to tag messages with a warning header rather than rejecting them outright, then let spam filters use the SPF result as one signal among many.

### How do SPF, DKIM, and DMARC work together?

SPF validates the envelope sender (the MAIL FROM address in SMTP). DKIM adds a cryptographic signature to the message header and body. DMARC requires that either SPF or DKIM (or both) align with the From: header visible to the user, and publishes a policy (`none`, `quarantine`, or `reject`) for what receivers should do when alignment fails. All three should be implemented together for comprehensive email authentication.

### Do I need SPF validation if I already use Rspamd or SpamAssassin?

Rspamd and SpamAssassin can perform SPF checks as part of their scoring pipeline, but dedicated SPF policy daemons offer more granular control. They allow you to configure per-domain policies, whitelist trusted senders, and return explicit Postfix actions (REJECT, WARN) before the message enters the spam filter. Using both together provides defense-in-depth: the policy daemon for early rejection and the spam filter for comprehensive analysis.

### How many DNS lookups does SPF allow?

RFC 7208 limits SPF evaluation to a maximum of 10 DNS lookups. This includes mechanisms like `include`, `a`, `mx`, `ptr`, `exists`, and `redirect`. If a domain's SPF record requires more than 10 lookups, the result is `permerror` (permanent error). The `all` mechanism and modifiers (`exp`, `redirect`) do not count toward the lookup limit.

