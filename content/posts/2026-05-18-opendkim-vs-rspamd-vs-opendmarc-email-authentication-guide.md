---
title: "OpenDKIM vs Rspamd vs OpenDMARC: Self-Hosted Email Authentication & DKIM Signing Guide 2026"
date: "2026-05-08"
tags: ["email", "security", "dkim", "dmarc", "spf", "authentication", "rspamd", "opendkim", "self-hosted"]
draft: false
---

Email authentication is no longer optional — major providers like Gmail, Yahoo, and Outlook now **require** SPF, DKIM, and DMARC for bulk senders. Without proper email authentication, your self-hosted mail server's messages will land in spam folders or be rejected entirely. This guide compares three leading open-source tools for implementing email authentication: **OpenDKIM**, **Rspamd**, and **OpenDMARC**.

## Why Email Authentication Matters

Three protocols work together to verify that an email actually came from who it claims:

- **SPF (Sender Policy Framework)** — DNS TXT record listing which servers are authorized to send email for your domain
- **DKIM (DomainKeys Identified Mail)** — Cryptographic signature added to outgoing emails, verified by the recipient's server
- **DMARC (Domain-based Message Authentication, Reporting & Conformance)** — Policy that tells receivers what to do when SPF or DKIM fails (reject, quarantine, or monitor)

Without DKIM signing, even a correctly configured Postfix server cannot prove that outgoing messages are authentic. Without DMARC, you cannot control how receivers handle spoofed emails claiming to be from your domain.

## Comparison Table

| Feature | OpenDKIM | Rspamd | OpenDMARC |
|---------|----------|--------|-----------|
| **GitHub Stars** | 110+ | 2,440+ | 180+ |
| **Last Active** | 2024 | 2026 | 2024 |
| **Primary Purpose** | DKIM signing & verification | Full spam filtering with DKIM | DMARC policy enforcement |
| **DKIM Signing** | Yes (primary function) | Yes (built-in module) | No |
| **DKIM Verification** | Yes (milter) | Yes (built-in module) | No |
| **DMARC Processing** | No | Yes (built-in module) | Yes (primary function) |
| **SPF Checking** | No | Yes (built-in module) | Yes (dependency) |
| **Installation Complexity** | Medium (milter setup) | Medium (standalone service) | Medium (requires libopendmarc) |
| **Docker Support** | Official images available | Official images available | Community images |
| **Integration** | Postfix/Sendmail milter | Postfix/Exim milter or proxy | Postfix/Sendmail milter |
| **Reporting** | Basic logging | Full web UI with Rspamd WebUI | Aggregate/forensic reports |
| **Performance** | Lightweight, single-purpose | Feature-rich, higher resource usage | Lightweight, single-purpose |
| **Maintenance Status** | Stable, slow updates | Very active | Stable, slow updates |

## OpenDKIM: The Dedicated DKIM Solution

OpenDKIM is the reference implementation of the DKIM standard. It runs as a milter (mail filter) daemon that integrates with Postfix or Sendmail to sign outgoing messages and verify incoming DKIM signatures.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  opendkim:
    image: ghcr.io/servercontainers/opendkim:latest
    container_name: opendkim
    restart: unless-stopped
    volumes:
      - ./keys:/etc/opendkim/keys
      - ./opendkim.conf:/etc/opendkim/opendkim.conf
    ports:
      - "8891:8891"
    networks:
      - mailnet

networks:
  mailnet:
    external: true
```

```conf
# opendkim.conf
Syslog          yes
UMask           002
Socket          inet:8891@0.0.0.0
Canonicalization relaxed/simple
Mode            sv
SubDomains      no
OversignHeaders  From

# Trust internal hosts
ExternalIgnoreList refile:/etc/opendkim/TrustedHosts
InternalHosts    refile:/etc/opendkim/TrustedHosts

# Key table and signing table
KeyTable        refile:/etc/opendkim/KeyTable
SigningTable    refile:/etc/opendkim/SigningTable

# Add your domain
Domain          example.com
Selector        default
KeyFile         /etc/opendkim/keys/example.com/default.private
```

```conf
# /etc/opendkim/TrustedHosts
127.0.0.1
localhost
192.168.1.0/24
```

After deploying, generate a DKIM key pair:

```bash
# Generate DKIM key
opendkim-genkey -s default -d example.com -D /etc/opendkim/keys/example.com/

# Extract the public key for DNS
cat /etc/opendkim/keys/example.com/default.txt
# Returns: default._domainkey IN TXT "v=DKIM1; k=rsa; p=MIGfMA0GCSq..."
```

Add the public key as a DNS TXT record at `default._domainkey.example.com`, then configure Postfix:

```conf
# /etc/postfix/main.cf
smtpd_milters = inet:127.0.0.1:8891
non_smtpd_milters = inet:127.0.0.1:8891
milter_default_action = accept
```

## Rspamd: All-in-One Email Filtering with DKIM

Rspamd is a fast, modular spam filtering system that includes built-in DKIM signing, DKIM verification, SPF checking, and DMARC enforcement. For many self-hosted email setups, Rspamd replaces OpenDKIM, OpenDMARC, and SpamAssassin in a single package.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  rspamd:
    image: rspamd/rspamd:latest
    container_name: rspamd
    restart: unless-stopped
    volumes:
      - ./rspamd.conf:/etc/rspamd/rspamd.conf
      - ./local.d:/etc/rspamd/local.d
      - ./dkim-keys:/var/lib/rspamd/dkim
    ports:
      - "11332:11332"  # Controller (WebUI)
      - "11333:11333"  # Worker
    networks:
      - mailnet

networks:
  mailnet:
    external: true
```

```conf
# local.d/dkim_signing.conf
path = "/var/lib/rspamd/dkim/$domain.$selector.key";
selector = "default";

# local.d/dmarc.conf
enabled = true;
reporting = true;
```

```conf
# Postfix integration
# /etc/postfix/main.cf
smtpd_milters = inet:127.0.0.1:11332
non_smtpd_milters = inet:127.0.0.1:11332
milter_default_action = accept
```

Rspamd's advantage is consolidation — one service handles DKIM, SPF, DMARC, spam scoring, bayesian filtering, and rate limiting. The built-in WebUI provides real-time statistics, symbol scores, and DKIM key management.

## OpenDMARC: DMARC Policy Enforcement

OpenDMARC implements the DMARC specification as a milter for Postfix or Sendmail. It checks incoming messages against the sender's DMARC policy and can reject or quarantine messages that fail authentication.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  opendmarc:
    image: docker.io/linuxserver/opendmarc:latest
    container_name: opendmarc
    restart: unless-stopped
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Etc/UTC
    volumes:
      - ./opendmarc.conf:/etc/opendmarc.conf
      - ./opendmarc.trusted.hosts:/etc/opendmarc/TrustedHosts
      - ./opendmarc.reports:/etc/opendmarc/Reports
    ports:
      - "8893:8893"
    networks:
      - mailnet

networks:
  mailnet:
    external: true
```

```conf
# /etc/opendmarc.conf
AuthservID OpenDMARC
FailureReports false
HistoryFile /var/run/opendmarc/opendmarc.dat
IgnoreAuthenticatedClients true
RejectFailures false
SPFSelfValidate true
Syslog true
TrustedAuthservIDs HOSTNAME
UMask 002

Socket inet:8893@0.0.0.0

# Required: path to OpenDKIM socket for SPF verification
OversignHeaders From
```

OpenDMARC is typically deployed alongside OpenDKIM. OpenDKIM handles DKIM signing/verification, while OpenDMARC enforces DMARC policies based on the combined SPF+DKIM results.

## Choosing the Right Email Authentication Stack

| Scenario | Recommended Stack |
|----------|------------------|
| Minimal setup, DKIM only | OpenDKIM |
| Full email filtering + DKIM + DMARC | Rspamd (single service) |
| Best-of-breed, separate concerns | OpenDKIM + OpenDMARC |
| High-volume mail server | Rspamd (better performance) |
| Compliance-focused environment | OpenDKIM + OpenDMARC (separate audit trails) |
| Simple self-hosted mail server | Rspamd (easiest single-service setup) |

## Why Self-Host Email Authentication?

Managing your own email authentication infrastructure means:

- **Complete control over DKIM keys** — rotate selectors, manage multiple domains, and set key lengths (2048-bit or 4096-bit RSA) without relying on third-party email services. Enterprise email providers often limit DKIM key management to paid tiers, while self-hosted solutions give you unrestricted key lifecycle management.
- **Custom DMARC policies** — gradually move from `p=none` (monitoring mode) to `p=quarantine` (spam folder) to `p=reject` (full block) at your own pace, with full visibility into aggregate reports showing which senders are passing and failing authentication checks.
- **Full visibility into authentication results** — see exactly which messages pass or fail SPF, DKIM, and DMARC checks at the raw protocol level. SaaS email providers often limit access to authentication logs or charge extra for detailed reporting.
- **Cost savings** — enterprise email authentication services like Proofpoint, Mimecast, and Barracuda charge per mailbox per month, typically $3-8 per user. Open-source tools run on your existing server infrastructure at zero additional licensing cost, making them ideal for small businesses and homelabs.
- **Compliance and audit requirements** — many regulated industries including HIPAA healthcare, GDPR data protection, SOX financial reporting, and PCI DSS payment processing require demonstrable email authentication controls. Running your own DKIM/DMARC infrastructure provides auditable logs and configuration histories that satisfy compliance reviewers.
- **No vendor lock-in** — when you manage your own DKIM keys and DMARC policies, you can switch email providers, add secondary mail servers, or implement hybrid cloud and on-premises email routing without changing your authentication setup. Your domain's email authentication belongs to you, not your email vendor.

### Security Best Practices for Email Authentication

- **Use 2048-bit or larger DKIM keys** — 1024-bit keys are considered weak. Generate new keys with `opendkim-genkey -b 2048`.
- **Rotate DKIM selectors annually** — publish a new key under a new selector (e.g., `2026`), switch signing, then remove the old DNS record after 30 days.
- **Start DMARC at `p=none`** — monitor for 2-4 weeks to identify all legitimate mail sources before moving to `p=quarantine` or `p=reject`.
- **Align SPF and DKIM domains** — DMARC requires domain alignment. Ensure your SPF record includes all sending IPs and your DKIM selector matches your From: domain.
- **Monitor DMARC reports** — use tools like DMARCian or self-hosted parsers to analyze aggregate reports and identify unauthorized senders.

For a complete self-hosted email setup, pair your authentication stack with [lightweight SMTP servers](../2026-04-18-maddy-vs-chasquid-vs-opensmtpd-lightweight-smtp-servers/) for message delivery, [email alias management](../2026-04-20-simplelogin-vs-anonaddy-vs-forwardemail-self-hosted-email-alias-guide/) for privacy, and [spam filtering](../2026-04-26-spamassassin-vs-rspamd-vs-amavis-self-hosted-spam-filt/) for inbound protection.

## FAQ

### Do I need both OpenDKIM and OpenDMARC?

OpenDKIM handles DKIM signing and verification. OpenDMARC enforces DMARC policies. You need OpenDKIM (or an equivalent like Rspamd's DKIM module) to sign outgoing messages. OpenDMARC is needed only if you want to enforce DMARC policies on incoming mail. For outbound-only signing, OpenDKIM alone is sufficient.

### What is the difference between DKIM and SPF?

SPF specifies which IP addresses are authorized to send email for your domain (verified via DNS TXT record). DKIM adds a cryptographic signature to each email header (verified using a public key in DNS). Both are complementary — SPF checks the envelope sender, DKIM checks the message content integrity. DMARC ties them together with a policy.

### Can Rspamd replace both OpenDKIM and OpenDMARC?

Yes. Rspamd includes built-in DKIM signing, DKIM verification, SPF checking, and DMARC policy enforcement. For many self-hosted email setups, Rspamd alone can handle all three authentication protocols, eliminating the need for separate OpenDKIM and OpenDMARC installations.

### How do I generate DKIM keys for multiple domains?

Each domain needs its own key pair and DNS record. With OpenDKIM, create separate directories per domain:
```bash
mkdir -p /etc/opendkim/keys/domain1.com
mkdir -p /etc/opendkim/keys/domain2.com
opendkim-genkey -s default -d domain1.com -D /etc/opendkim/keys/domain1.com/
opendkim-genkey -s default -d domain2.com -D /etc/opendkim/keys/domain2.com/
```
Add entries to the KeyTable and SigningTable files for each domain.

### What DMARC policy should I start with?

Start with `p=none` (monitoring mode) to collect aggregate reports without affecting delivery. After 2-4 weeks of analyzing reports and confirming all legitimate mail sources pass authentication, move to `p=quarantine` (send to spam), then eventually `p=reject` (block entirely). This gradual approach prevents legitimate mail from being rejected due to misconfiguration.

### How often should I rotate DKIM keys?

Best practice is to rotate DKIM keys every 6-12 months. Use multiple selectors (e.g., `default` and `2026`) to enable seamless rotation: publish the new key under a new selector, switch signing to the new selector, wait for the old key's signatures to expire from in-flight messages, then remove the old DNS record.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "OpenDKIM vs Rspamd vs OpenDMARC: Self-Hosted Email Authentication & DKIM Signing Guide 2026",
  "description": "Compare OpenDKIM, Rspamd, and OpenDMARC for self-hosted email authentication. Learn DKIM signing, DMARC enforcement, and SPF configuration for your mail server.",
  "datePublished": "2026-05-08",
  "dateModified": "2026-05-08",
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
