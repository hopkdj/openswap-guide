---
title: "Self-Hosted SMTP SRS: PostSRSd vs Exim SRS vs Haraka SRS Plugin"
date: "2026-05-16"
tags: ["smtp", "email", "srs", "spf", "mail-forwarding", "postfix", "exim", "haraka"]
draft: false
---

Email forwarding is a fundamental feature of mail server infrastructure — whether you're running a catch-all domain, forwarding mail between providers, or managing mailing lists. But when you forward an email, the envelope sender (Return-Path) still points to the original sender's domain. This breaks SPF (Sender Policy Framework) validation at the final destination, causing forwarded emails to fail authentication and land in spam folders.

The **Sender Rewriting Scheme (SRS)** solves this problem by rewriting the envelope sender address during forwarding, so the intermediate server takes SPF responsibility. In this guide, we compare three open-source SRS implementations: **PostSRSd** (the Postfix-focused daemon), **Exim's built-in SRS support**, and **Haraka's SRS plugin** — covering setup, configuration, and integration patterns for each.

## Why SRS Matters for Mail Forwarding

When an email is forwarded without SRS, the delivery chain looks like this:

1. Original sender (`alice@gmail.com`) sends to your server (`bob@yourdomain.com`)
2. Your server forwards to the final destination (`bob@company.org`)
3. `company.org` receives the email with Return-Path `alice@gmail.com`
4. `company.org` checks SPF for `gmail.com` — but the connecting IP is **your server**, not Google's
5. SPF fails, email gets rejected or marked as spam

With SRS enabled, step 3 changes: the Return-Path becomes `SRS0=HASH=DATE=alice=gmail.com@yourdomain.com`, and `company.org` checks SPF against **your domain** instead of Gmail's. Since your server is authorized to send for your own domain, SPF passes.

## Comparison Table

| Feature | PostSRSd | Exim SRS | Haraka SRS |
|---|---|---|---|
| **Stars / Activity** | 357 (roehling) | Built-in (Exim) | Part of Haraka (4,200+ stars) |
| **MTA Integration** | Postfix (TCP socket) | Exim (native) | Haraka (Node.js plugin) |
| **Language** | C | C (built into Exim) | JavaScript/Node.js |
| **SRS Version** | SRS0 and SRS1 | SRS0 and SRS1 | SRS0 and SRS1 |
| **Key Rotation** | Automatic (configurable) | Manual configuration | Automatic (configurable) |
| **Hash Algorithm** | HMAC-SHA256 | HMAC-MD5 / HMAC-SHA1 | HMAC-SHA256 |
| **Docker Support** | Community images | Official images | Official images |
| **Configuration** | Simple text config | Exim config macros | JSON config |
| **Performance** | Very fast (C daemon) | Very fast (built into MTA) | Good (Node.js) |
| **Multi-Domain** | Yes (domain list) | Yes (per-domain rules) | Yes (config file) |
| **Best For** | Postfix deployments | Exim-native setups | Haraka/Node.js stacks |

## PostSRSd — SRS Daemon for Postfix

PostSRSd is a lightweight TCP daemon that implements SRS for Postfix. It runs as a separate process and communicates with Postfix via the `tcp:` lookup table mechanism, rewriting envelope senders on-the-fly during mail processing.

### Key Features

- **Postfix integration**: Works with Postfix's `sender_canonical_maps` and `recipient_canonical_maps` via TCP socket
- **Automatic key rotation**: Configurable old/new key pairs for smooth SRS key transitions
- **Dual SRS support**: Handles both SRS0 (forward) and SRS1 (bounce/rewrite reversal)
- **Minimal footprint**: Single C binary with no runtime dependencies beyond libsrs2
- **Separation of concerns**: Runs independently of Postfix, allowing independent updates and restarts

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  postsrsd:
    image: instrumentisto/opendkim:latest
    container_name: postsrsd
    environment:
      - SRS_DOMAIN=yourdomain.com
      - SRS_SECRET=/etc/postsrsd/secret
      - SRS_EXCLUDE_DOMAINS=example.com,example.org
    volumes:
      - ./postsrsd-secret:/etc/postsrsd/secret:ro
    ports:
      - "127.0.0.1:10001:10001"
      - "127.0.0.1:10002:10002"
    restart: unless-stopped
```

### Postfix Configuration

Add these lines to your `main.cf`:

```
# PostSRSd integration
sender_canonical_maps = tcp:127.0.0.1:10001
sender_canonical_classes = envelope_sender
recipient_canonical_maps = tcp:127.0.0.1:10002
recipient_canonical_classes = envelope_recipient

# SRS domain
srs_domain = yourdomain.com
```

### PostSRSd Configuration

```
# /etc/default/postsrsd

# The local domain used for SRS rewriting
SRS_DOMAIN=yourdomain.com

# Alternative domains (if you handle multiple domains)
SRS_ALTERNATE_DOMAINS=alias1.com,alias2.com

# Exclude these domains from SRS rewriting
SRS_EXCLUDE_DOMAINS=localhost,localdomain

# Path to the secret key file
SRS_SECRET_FILE=/etc/postsrsd/secret

# Generate keys of this length (minimum 16)
SRS_HASH_LENGTH=16

# TCP listen addresses
SRS_ADDRESS=127.0.0.1
SRS_FORWARD_PORT=10001
SRS_REVERSE_PORT=10002

# Enable automatic key rotation
SRS_ALLOW_OLD_SECRET=yes
SRS_SECRET_LENGTH=32
```

## Exim Built-In SRS Support

Exim includes native SRS support as a built-in feature, requiring no additional daemons or plugins. SRS rewriting is configured directly in Exim's configuration file using router and transport definitions.

### Key Features

- **No external dependencies**: SRS is compiled into Exim — no separate daemon needed
- **Flexible rewriting rules**: Exim's powerful string expansion allows complex SRS configurations
- **Integrated bounce handling**: SRS reversal works natively with Exim's bounce processing
- **Single configuration**: Everything in one config file — no coordinating between multiple services

### Exim SRS Configuration Snippet

```
# In Exim's main configuration

# SRS domain and secrets
srs_domain = yourdomain.com
srs_secret = your-srs-secret-key-here

# Forward rewriting router
srs_forward:
  driver = redirect
  condition = ${if !eq{$sender_address_domain}{yourdomain.com}}
  data = ${srs_forward{$sender_address}}
  no_verify
  no_expn

# Reverse rewriting router (for bounces)
srs_reverse:
  driver = redirect
  condition = ${if match{$local_part}{^SRS0=}}
  data = ${srs_reverse{$local_part@$domain}}
  no_verify
  no_expn
```

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  exim:
    image: devture/exim:latest
    container_name: exim
    volumes:
      - ./exim.conf:/etc/exim/exim.conf:ro
      - ./exim-srs-secret:/etc/exim/srs_secret:ro
    ports:
      - "25:25"
      - "587:587"
    environment:
      - EXIM_SRS_DOMAIN=yourdomain.com
      - EXIM_SRS_SECRET=/etc/exim/srs_secret
    restart: unless-stopped
```

## Haraka SRS Plugin

Haraka is a high-performance Node.js SMTP server with a rich plugin ecosystem. The SRS plugin (`haraka-plugin-srs`) provides SRS rewriting as part of Haraka's plugin-based mail processing pipeline.

### Key Features

- **Plugin architecture**: SRS is one of many Haraka plugins — easy to enable/disable without touching core config
- **JavaScript extensibility**: Custom SRS logic can be added via additional plugins
- **Node.js ecosystem**: Leverages the vast npm ecosystem for additional functionality (logging, monitoring, anti-spam)
- **Hot-reloadable**: Plugins can be reloaded without restarting the SMTP server

### Haraka SRS Configuration

In `config/plugins`:
```
srs
```

In `config/srs.ini`:
```ini
[main]
domain=yourdomain.com
secrets=your-srs-secret-key-here
exclude_domains=example.com,example.org

[encoding]
hash_algorithm=sha256
hash_length=16
```

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  haraka:
    image: namshi/haraka:latest
    container_name: haraka
    volumes:
      - ./haraka-config:/haraka/config:ro
      - ./haraka-plugins:/haraka/plugins:ro
    ports:
      - "25:25"
      - "587:587"
    environment:
      - HARAKA_SRS_DOMAIN=yourdomain.com
      - HARAKA_SRS_SECRET=your-secret-key
    restart: unless-stopped
```

## Why Self-Host Your SRS Implementation?

Implementing SRS on your own mail server is essential for maintaining reliable email delivery when forwarding is involved. Without SRS, forwarded emails from major providers (Gmail, Outlook, Yahoo) will increasingly fail SPF checks and be rejected by receiving servers with strict DMARC policies.

**DMARC compliance**: As more domains publish strict DMARC policies (`p=reject`), email forwarding without SRS becomes unreliable. SRS ensures that forwarded messages pass SPF checks, which is one of the two authentication mechanisms required for DMARC compliance (alongside DKIM). Without SRS, you cannot reliably forward mail from DMARC-protected domains.

**Data ownership**: Running your own SRS implementation means all email rewriting happens on your infrastructure. No third-party service sees your email metadata, sender addresses, or forwarding patterns. The SRS secret key never leaves your server, and you control key rotation schedules.

**Cost-free reliability**: Commercial email relay services charge per-message fees for handling SRS and forwarding. Self-hosted SRS costs nothing beyond your server infrastructure — the SRS computation is a simple HMAC operation that adds negligible overhead to mail processing.

**No single point of failure**: External SRS-as-a-service providers can experience outages, rate limiting, or policy changes that break your email forwarding. Running SRS locally ensures that your mail forwarding continues to work regardless of external service availability.

For broader email security, see our [email authentication guide](../self-hosted-dmarc-analysis-email-authentication-parsedmarc-opendmarc-guide/) covering SPF, DKIM, and DMARC. If you need SMTP relay management, check our [SMTP relay comparison](../2026-04-26-postal-vs-stalwart-vs-haraka-self-hosted-smtp-relay-guide-2026/). For mail queue monitoring, our [mail queue management guide](../2026-05-05-self-hosted-mail-queue-management-postfix-mailgraph-pflogsumm-guide/) covers the essentials.

## Choosing the Right SRS Implementation

**Choose PostSRSd if**: You're running Postfix and want a dedicated, lightweight SRS daemon. PostSRSd is the most widely deployed SRS solution, with clean Postfix integration and automatic key rotation. It's the safest choice for production Postfix environments.

**Choose Exim SRS if**: You're already running Exim as your MTA. The built-in SRS support requires no additional software, reduces operational complexity, and integrates seamlessly with Exim's existing routing and delivery mechanisms.

**Choose Haraka SRS if**: You're running Haraka or building a Node.js-based mail processing pipeline. The plugin architecture makes it easy to combine SRS with other Haraka plugins for anti-spam, DKIM signing, and custom mail processing logic.

## FAQ

### What is SRS and why do I need it?
SRS (Sender Rewriting Scheme) rewrites the envelope sender address when an email is forwarded, so the forwarding server — not the original sender's domain — takes SPF responsibility. Without SRS, forwarded emails fail SPF checks at the final destination and are often rejected or marked as spam, especially when the original domain has strict DMARC policies.

### Does SRS affect DKIM signatures?
SRS rewrites the envelope sender (Return-Path), which is used for SPF, not DKIM. DKIM signatures cover the message headers and body, and are unaffected by envelope sender rewriting. However, some forwarding setups may modify message headers, which would break DKIM. SRS addresses the SPF problem specifically.

### How often should I rotate SRS secret keys?
Best practice is to rotate SRS keys every 30-90 days. PostSRSd supports automatic key rotation with overlapping old/new keys, ensuring that bounces from recently forwarded emails can still be reversed. Exim and Haraka require manual key updates, but you can automate this with cron jobs and configuration reloads.

### Can SRS handle multi-domain forwarding?
Yes. All three implementations support multiple domains. PostSRSd uses the `SRS_ALTERNATE_DOMAINS` setting, Exim uses conditional rewriting rules, and Haraka supports per-domain secrets. Each domain gets its own SRS-rewritten sender address, maintaining proper SPF alignment for each forwarded domain.

### What happens if SRS fails or the secret key is lost?
If the SRS secret key is lost, bounced emails with SRS-rewritten sender addresses cannot be reversed to their original form. Bounces will be delivered to the SRS domain's catch-all or postmaster address, requiring manual processing. This is why key rotation should always use overlapping old/new keys during the transition period.

### Does SRS work with mailing lists?
Mailing list software (Mailman, Sympa) typically handles sender rewriting internally, often using VERP (Variable Envelope Return Path) rather than SRS. If your mailing list software doesn't implement SRS natively, you can place PostSRSd or Exim SRS in front of it to handle rewriting before the list processor receives the message.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted SMTP SRS: PostSRSd vs Exim SRS vs Haraka SRS Plugin",
  "description": "Compare three open-source SRS implementations for reliable email forwarding. Covers PostSRSd, Exim built-in SRS, and Haraka SRS plugin with Docker configs.",
  "datePublished": "2026-05-16",
  "dateModified": "2026-05-16",
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
