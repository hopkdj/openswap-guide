---
title: "Self-Hosted SMTP TLS Enforcement: Postfix vs Haraka vs Exim"
date: "2026-05-13"
tags: ["email", "security", "tls", "smtp", "mta"]
draft: false
---

Transport Layer Security (TLS) for SMTP is no longer optional — it is a fundamental requirement for secure email delivery. Without enforced TLS, email content travels in plaintext across the internet, vulnerable to interception, modification, and credential theft. Yet many self-hosted mail servers are configured with opportunistic TLS (STARTTLS when available, plaintext fallback), leaving a significant portion of email traffic unencrypted.

This guide compares three leading open-source mail transfer agents — Postfix, Haraka, and Exim — for implementing strict SMTP TLS enforcement, including MTA-STS, DANE, and TLS reporting.

## Understanding SMTP TLS Enforcement Levels

SMTP TLS operates at three enforcement levels:

- **Opportunistic (default)** — Attempt STARTTLS, fall back to plaintext if the remote server does not support it. Protects against passive eavesdropping but not active downgrade attacks.
- **Verified (DANE/MTA-STS)** — Require TLS and verify the remote server's certificate against DNS-based Authentication of Named Entities (DANE) or MTA Strict Transport Security (MTA-STS) policies. Protects against active MITM attacks.
- **Strict (Fingerprint)** — Require TLS and verify the remote server's certificate fingerprint. The strongest level, but requires prior knowledge of the recipient's certificate.

Each MTA implements these levels differently, with varying degrees of configuration complexity and flexibility.

## Comparison Table

| Feature | Postfix | Haraka | Exim |
|---------|---------|--------|------|
| GitHub/Project | Official (ISC) | haraka/haraka (4,000+ stars) | exim/exim (1,100+ stars) |
| Language | C | JavaScript (Node.js) | C |
| Opportunistic TLS | Yes (default) | Yes (default) | Yes (default) |
| Verified TLS (DANE) | Yes | Via plugin | Yes |
| MTA-STS | Yes (3.7+) | Via plugin | Via policy |
| TLS Reporting | Yes | Via plugin | Yes |
| Certificate Fingerprint | Yes (tls_verify) | Via plugin | Yes (hosts_require) |
| Configuration Style | main.cf | config/plugins | exim.conf (complex) |
| Docker Image | Official (linuxserver) | Official | Community |
| Active Development | Very Active | Active | Active |
| License | IPL (IBM Public) | MIT | GPL-3.0 |

## Postfix

Postfix is the most widely deployed open-source MTA, known for its security-focused design and straightforward configuration. TLS enforcement in Postfix is controlled through `smtp_tls_security_level` and per-domain policy maps.

### Postfix Docker Compose

```yaml
version: "3.8"
services:
  postfix:
    image: linuxserver/postfix:latest
    container_name: postfix-tls
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    volumes:
      - ./main.cf:/config/main.cf:ro
      - ./tls_policy:/config/tls_policy:ro
      - ./certs:/etc/ssl/mail:ro
    ports:
      - "25:25"
      - "587:587"
      - "465:465"
    restart: unless-stopped
```

### Postfix TLS Enforcement Configuration

```ini
# /etc/postfix/main.cf
# Global TLS settings
smtp_tls_security_level = verify
smtp_tls_CAfile = /etc/ssl/certs/ca-certificates.crt
smtp_tls_loglevel = 1
smtp_tls_note_starttls_offer = yes

# Per-domain TLS policy
smtp_tls_policy_maps = hash:/etc/postfix/tls_policy

# Require TLS for specific domains
# /etc/postfix/tls_policy
gmail.com        verify
outlook.com      verify
company.com      encrypt
partner.org      fingerprint match=SHA256:AB:CD:EF:...
```

```ini
# For outgoing mail with strict enforcement
smtp_tls_mandatory_protocols = >=TLSv1.2
smtp_tls_mandatory_ciphers = high
smtp_tls_exclude_ciphers = aNULL, eNULL, EXPORT, DES, RC4, MD5, PSK, aECDH, EDH-DSS-DES-CBC3-SHA, EDH-RSA-DES-CBC3-SHA, KRB5-DE5, CBC3-SHA

# MTA-STS policy lookup
smtp_tls_mandatory_exclude_ciphers = aNULL, MD5
tls_server_sni_maps = hash:/etc/postfix/sni_map
```

Postfix's policy map system allows granular per-domain TLS enforcement. You can require encryption for banking partners while allowing opportunistic TLS for less critical recipients. The `verify` level enforces DANE when DNSSEC is available.

## Haraka

Haraka is a modern, plugin-based SMTP server written in Node.js. Its architecture makes TLS enforcement highly customizable through plugins, though it requires more initial setup than traditional MTAs.

### Haraka Docker Compose

```yaml
version: "3.8"
services:
  haraka:
    image: haraka/haraka:latest
    container_name: haraka-tls
    volumes:
      - ./config:/haraka/config:ro
      - ./plugins:/haraka/plugins:ro
      - ./tls:/haraka/config/tls:ro
    ports:
      - "25:25"
      - "587:587"
    restart: unless-stopped
```

### Haraka TLS Configuration

```ini
# /haraka/config/tls.ini
[main]
key=tls/key.pem
cert=tls/cert.pem
ca=tls/ca.pem

[no_starttls_hosts]
; Domains that should skip STARTTLS
; legacy-partner.com

[outbound]
tls_opts=
  minVersion=TLSv1.2
  ciphers=HIGH:!aNULL:!MD5:!RC4

; Enable TLS enforcement plugin
```

```ini
# /haraka/config/plugins
tls
outbound-tls-require
mta-sts
```

```javascript
// /haraka/plugins/outbound-tls-require.js
// Custom plugin for strict TLS enforcement
exports.hook_init_outbound = function (next, hmail) {
    const requireTLS = this.config.get('tls_required_domains', 'list');
    hmail.todo.require_tls_domains = requireTLS;
    next();
};

exports.hook_get_mx = function (next, hmail, domain) {
    if (hmail.todo.require_tls_domains.includes(domain)) {
        hmail.todo.force_tls = true;
    }
    next();
};
```

Haraka's plugin architecture means TLS enforcement behavior is entirely programmable. You can integrate with external APIs to check domain TLS policies, implement custom certificate pinning, or build adaptive enforcement rules that evolve based on delivery patterns.

## Exim

Exim is a highly flexible MTA with extensive TLS configuration options. Its router and transport configuration allows sophisticated per-domain TLS policies, though the configuration syntax is notoriously complex.

### Exim Docker Compose

```yaml
version: "3.8"
services:
  exim:
    image: devture/exim:latest
    container_name: exim-tls
    volumes:
      - ./exim.conf:/etc/exim/exim.conf:ro
      - ./tls:/etc/exim/tls:ro
    ports:
      - "25:25"
      - "587:587"
    restart: unless-stopped
```

### Exim TLS Enforcement Configuration

```ini
# /etc/exim/exim.conf - TLS configuration
tls_certificate = /etc/exim/tls/server.crt
tls_privatekey = /etc/exim/tls/server.key

# Outbound transport with TLS enforcement
remote_smtp:
  driver = smtp
  hosts_require_tls = gmail.com : outlook.com : *.company.com
  hosts_require_ocsp = *
  tls_verify_hosts = *
  tls_verify_certificates = /etc/ssl/certs/ca-certificates.crt
  openssl_options = +no_sslv2 +no_sslv3 +no_tlsv1 +no_tlsv1_1

# Per-domain TLS policy via router
tls_policy_router:
  driver = manualroute
  domains = lsearch;/etc/exim/tls_domains
  transport = tls_strict_smtp
  route_data = ${lookup{$domain}lsearch{/etc/exim/tls_routes}}

tls_strict_smtp:
  driver = smtp
  hosts_require_tls = *
  tls_verify_certificates = /etc/ssl/certs/ca-certificates.crt
```

```
# /etc/exim/tls_domains
gmail.com
outlook.com
yahoo.com
company.com
```

Exim's `hosts_require_tls` directive accepts colon-separated domain lists, CIDR ranges, and wildcard patterns. Combined with its powerful string expansion syntax, you can implement highly sophisticated TLS enforcement policies that adapt based on recipient domain, message headers, or authentication status.

## Choosing the Right MTA for TLS Enforcement

**Choose Postfix if:** You want the most straightforward path to verified TLS enforcement. Its policy map system is well-documented, widely understood, and integrates seamlessly with MTA-STS and DANE. Postfix is the best choice for organizations that need reliable, standards-compliant TLS enforcement without custom development.

**Choose Haraka if:** You need programmable TLS enforcement with custom logic. Its Node.js plugin system lets you integrate TLS decisions with external APIs, threat intelligence feeds, or business rules. Best suited for development teams comfortable with JavaScript who need flexibility beyond standard MTA capabilities.

**Choose Exim if:** You require the most granular control over TLS parameters per route, per transport, or per recipient. Exim's configuration complexity is its strength when you need multi-layered TLS policies with conditional logic based on message attributes.

## Why Self-Host with Enforced SMTP TLS?

Email interception remains one of the most practical attack vectors for both state-level and criminal actors. Without TLS enforcement, login credentials, password reset tokens, financial documents, and sensitive personal data travel across the internet in readable form. Self-hosting your MTA with strict TLS enforcement ensures that outbound email from your organization is always encrypted, regardless of the recipient's mail server configuration.

Regulatory compliance increasingly requires email encryption. HIPAA mandates encryption for protected health information in transit. GDPR requires appropriate technical measures to protect personal data. PCI-DSS requires encryption of cardholder data during transmission over open networks. A self-hosted MTA with verified TLS enforcement provides auditable proof of encryption for compliance assessments.

MTA-STS and DANE represent the next generation of email security. MTA-STS allows domain owners to publish a policy declaring that all inbound mail must use TLS, while DANE leverages DNSSEC to bind TLS certificates to domain names via DNS records. Both protocols protect against STARTTLS downgrade attacks — where an active attacker strips the STARTTLS capability to force plaintext delivery. Self-hosting an MTA that supports these protocols ensures your email infrastructure is prepared for the post-opportunistic-TLS era.

For related reading, see our [MTA-STS and DANE email security guide](2026-04-28-self-hosted-mta-sts-smtp-dane-email-security-guide/) for implementing domain-level TLS policies, the [Postfix vs Exim MTA comparison](2026-04-29-postfix-vs-exim-self-hosted-mta-comparison-guide/) for choosing the right mail transfer agent, and our [SMTP relay guide](2026-04-26-postal-vs-stalwart-vs-haraka-self-hosted-smtp-relay-guide/) for setting up outbound mail routing.

For related reading, see our [MTA-STS and DANE email security guide](../2026-04-28-self-hosted-mta-sts-smtp-dane-email-security-guide/) for implementing domain-level TLS policies, the [Postfix vs Exim MTA comparison](../2026-04-29-postfix-vs-exim-self-hosted-mta-comparison-guide/) for choosing the right mail transfer agent, and our [SMTP relay guide](../2026-04-26-postal-vs-stalwart-vs-haraka-self-hosted-smtp-relay-guide/) for setting up outbound mail routing.

## FAQ

### What is the difference between opportunistic and enforced TLS?

Opportunistic TLS attempts to use STARTTLS but falls back to plaintext if the remote server does not support it. This protects against passive eavesdropping but is vulnerable to active downgrade attacks. Enforced TLS requires an encrypted connection and rejects delivery if TLS cannot be established, providing protection against both passive and active attacks.

### How does DANE protect SMTP TLS?

DANE (DNS-based Authentication of Named Entities) uses DNSSEC-signed TLSA records to specify which certificates are valid for a mail server. When a sending MTA performs a DANE lookup, it can verify that the certificate presented by the receiving server matches the DNS-published record. This prevents attackers from using fraudulent certificates in MITM attacks, since they cannot forge DNSSEC-signed records.

### What is MTA-STS and how does it differ from DANE?

MTA-STS (MTA Strict Transport Security) is an HTTP-based policy mechanism. Domain owners publish a policy file at `mta-sts.domain.com/.well-known/mta-sts.json` declaring that inbound mail must use TLS. The policy is also advertised via DNS TXT records. Unlike DANE, MTA-STS does not require DNSSEC. However, DANE provides stronger security because it binds specific certificates to the domain, while MTA-STS only requires TLS without certificate verification.

### Can I enforce TLS for all outbound email?

Yes, but with caveats. Enforcing TLS for all domains will cause delivery failures to recipients whose mail servers do not support STARTTLS (estimated at 5-10% of global mail servers). The recommended approach is to enforce TLS for known partners and domains that support it, while using opportunistic TLS for unknown recipients. Monitor TLS usage with SMTP TLS Reporting to identify which domains support encryption.

### What is SMTP TLS Reporting?

SMTP TLS Reporting (RFC 8460) allows receiving mail servers to send aggregate reports about TLS connection attempts to the sending domain. These reports include statistics on successful and failed TLS connections, cipher suites used, and certificate validation results. Postfix, Exim, and Haraka all support generating TLS reports when configured with the appropriate policy domains.

### Does TLS encryption protect against phishing and spam?

No. TLS encrypts the transport channel but does not validate message content or sender identity. For phishing and spam protection, you need additional mechanisms: SPF (Sender Policy Framework), DKIM (DomainKeys Identified Mail), and DMARC (Domain-based Message Authentication, Reporting and Conformance). These protocols work alongside TLS to provide comprehensive email security.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted SMTP TLS Enforcement: Postfix vs Haraka vs Exim",
  "description": "Compare Postfix, Haraka, and Exim for enforcing SMTP TLS encryption with MTA-STS, DANE, and TLS reporting. Includes Docker compose configs and per-domain TLS policies.",
  "datePublished": "2026-05-13",
  "dateModified": "2026-05-13",
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
