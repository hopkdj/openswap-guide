---
title: "Self-Hosted MTA-STS Policy Servers: postfix-mta-sts-resolver vs postfix-tlspol vs sts-mate (2026)"
date: "2026-05-14"
tags: ["email-security", "smtp", "tls", "mta-sts", "self-hosted"]
draft: false
---

Email encryption in transit is critical for protecting sensitive communications, but traditional SMTP has a fundamental flaw: it silently falls back to plaintext when TLS negotiation fails. An active attacker can exploit this by stripping TLS capabilities during the SMTP handshake, intercepting all email content. MTA-STS (Mail Transfer Agent Strict Transport Security, RFC 8461) solves this by allowing domain owners to publish a policy that mandates TLS for inbound mail, preventing downgrade attacks.

While many guides cover the MTA-STS concept and DNS configuration, few address the server-side infrastructure needed to enforce these policies. In this guide, we compare three self-hosted tools for implementing MTA-STS policy resolution and enforcement: **postfix-mta-sts-resolver** (Postfix socketmap daemon), **postfix-tlspol** (MTA-STS plus DANE resolver), and **sts-mate** (MTA-STS policy server and reverse proxy).

## Understanding MTA-STS Infrastructure

MTA-STS requires two server-side components:

1. **Policy hosting** — a web server at `mta-sts.yourdomain.com` that serves the policy file at `/.well-known/mta-sts.txt`
2. **Policy resolution** — a daemon that receiving MTAs query to determine whether to enforce TLS for incoming mail from specific domains

The first component is straightforward — any web server can host a text file. The second component is where the tools in this comparison come in. They act as intermediaries between your MTA (Postfix, Exim, etc.) and the MTA-STS policy infrastructure, caching policy lookups and providing fast local responses.

## postfix-mta-sts-resolver: Postfix Socketmap Daemon

[postfix-mta-sts-resolver](https://github.com/Snawoot/postfix-mta-sts-resolver) (125 GitHub stars) is the most widely deployed MTA-STS enforcement tool. It runs as a socketmap server that Postfix queries during SMTP delivery, checking the recipient domain MTA-STS policy and caching the result.

### Key Features

- **Postfix socketmap integration** — integrates directly with Postfix `smtp_tls_policy_maps` via socketmap protocol
- **Policy caching** — caches MTA-STS policy lookups for the duration specified by the policy `max_age` field
- **ASN-based enforcement** — can optionally enforce TLS based on the recipient mail server ASN
- **Daemon mode** — runs as a persistent background service
- **Python-based** — easy to install via pip, runs on any Python 3.7+ system
- **Fallback handling** — gracefully handles DNS failures and policy fetch errors

### How It Works

The daemon operates in a simple loop:

1. Postfix queries the socketmap with a recipient domain
2. The resolver checks its cache for a recent policy lookup
3. If not cached, it fetches the MTA-STS policy from `https://mta-sts.domain.com/.well-known/mta-sts.txt`
4. It validates the policy against the domain TLSRPT DNS record
5. Returns `secure` or `none` to Postfix, which enforces or allows plaintext accordingly

### Docker Compose Deployment

```yaml
services:
  mta-sts-resolver:
    image: python:3.11-slim
    working_dir: /app
    volumes:
      - ./cache:/app/cache
      - /var/spool/postfix/private:/var/spool/postfix/private
    command: >
      bash -c "
        pip install postfix-mta-sts-resolver &&
        postfix-mta-sts-resolver --cache sqlite:/app/cache/policy_cache.db \
          --socket /var/spool/postfix/private/policy
      "
    restart: unless-stopped
    user: postfix

  postfix:
    image: postfix:latest
    volumes:
      - /var/spool/postfix/private:/var/spool/postfix/private
    depends_on:
      - mta-sts-resolver
```

### Postfix Configuration

```ini
# main.cf
smtp_tls_policy_maps = socketmap:unix:/var/spool/postfix/private/policy:postfix_mta_sts
smtp_tls_security_level = dane

# master.cf - add socketmap service
policy   unix  -       n       n       -       0       spawn
  user=postfix argv=/usr/bin/postfix-mta-sts-resolver --socket /var/spool/postfix/private/policy
```

### Installation

```bash
pip install postfix-mta-sts-resolver

# Run as daemon
postfix-mta-sts-resolver \
  --cache sqlite:/var/lib/mta-sts/policy_cache.db \
  --socket /var/spool/postfix/private/policy \
  --timeout 10 \
  --daemon
```

## postfix-tlspol: MTA-STS Plus DANE Resolver

[postfix-tlspol](https://github.com/Zuplu/postfix-tlspol) (42 GitHub stars) extends the concept by combining MTA-STS policy resolution with DANE/TLSA validation. It prioritizes DANE when available and falls back to MTA-STS, providing defense-in-depth for email encryption.

### Key Features

- **DANE-first approach** — checks DNS TLSA records before falling back to MTA-STS
- **Combined policy resolution** — single daemon handles both DANE and MTA-STS lookups
- **Postfix socketmap integration** — same interface as postfix-mta-sts-resolver
- **Lightweight** — smaller codebase, fewer dependencies
- **Active development** — recent updates with improved TLS validation
- **Configurable fallback** — choose whether to prefer DANE, MTA-STS, or both

### How DANE and MTA-STS Work Together

DANE (DNS-based Authentication of Named Entities, RFC 6698) uses DNSSEC-signed TLSA records to associate a TLS certificate with a domain. MTA-STS uses HTTPS-served policies. When both are available:

1. The resolver first checks for a valid DNSSEC TLSA record
2. If DANE validates, it enforces TLS with the specified certificate
3. If DANE is unavailable, it falls back to MTA-STS policy checking
4. If neither is available, it applies the configured default (secure or none)

This layered approach provides maximum security: DANE gives certificate pinning, MTA-STS gives policy-based enforcement.

### Docker Compose Deployment

```yaml
services:
  tlspol-resolver:
    image: python:3.11-slim
    working_dir: /app
    volumes:
      - ./cache:/app/cache
      - /var/spool/postfix/private:/var/spool/postfix/private
    command: >
      bash -c "
        pip install postfix-tlspol &&
        postfix-tlspol --cache sqlite:/app/cache/tlspol.db \
          --socket /var/spool/postfix/private/tlspol
      "
    restart: unless-stopped
    user: postfix
    environment:
      - PYTHONUNBUFFERED=1

  unbound:
    image: mvance/unbound:latest
    volumes:
      - ./unbound.conf:/opt/unbound/etc/unbound/unbound.conf
    # Unbound with DNSSEC validation is required for DANE

  postfix:
    image: postfix:latest
    volumes:
      - /var/spool/postfix/private:/var/spool/postfix/private
    depends_on:
      - tlspol-resolver
      - unbound
```

### Installation

```bash
pip install postfix-tlspol

# Run with DANE priority
postfix-tlspol \
  --cache sqlite:/var/lib/tlspol/policy_cache.db \
  --socket /var/spool/postfix/private/tlspol \
  --prefer dane \
  --daemon
```

## sts-mate: MTA-STS Policy Server and Reverse Proxy

[sts-mate](https://github.com/danmarg/sts-mate) (14 GitHub stars) takes a different approach. Instead of being a Postfix-specific socketmap daemon, it is a general-purpose MTA-STS policy server and reverse proxy. It can both host MTA-STS policies for your own domains and resolve policies for domains you send mail to.

### Key Features

- **Policy hosting** — serve MTA-STS policy files for your domains
- **Policy resolution** — resolve and cache policies for outbound mail domains
- **Let Encrypt integration** — automatically fetch and renew TLS certificates for policy hosting
- **Reverse proxy mode** — proxy policy requests with caching
- **Multi-tenant** — manage policies for multiple domains from a single instance
- **Simple configuration** — YAML-based config file

### Architecture

sts-mate combines two roles:

1. **Policy server** — hosts `/.well-known/mta-sts.txt` for your domains at `mta-sts.yourdomain.com`
2. **Policy resolver** — acts as a caching resolver that other tools can query via HTTP API

This dual role makes sts-mate useful for organizations that both send and receive mail — they can host their own inbound policies and resolve outbound policies through the same service.

### Docker Compose Deployment

```yaml
services:
  sts-mate:
    image: danmarg/sts-mate:latest
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./config:/etc/sts-mate
      - ./policies:/var/lib/sts-mate/policies
      - ./certs:/etc/sts-mate/certs
    environment:
      - STS_MATE_CONFIG=/etc/sts-mate/config.yml
    restart: unless-stopped

  # Local DNS resolver with DNSSEC (for policy validation)
  unbound:
    image: mvance/unbound:latest
    volumes:
      - ./unbound.conf:/opt/unbound/etc/unbound/unbound.conf
```

Configuration file (`config.yml`):

```yaml
domains:
  - domain: example.com
    mode: enforce
    mx:
      - "*.example.com"
    max_age: 86400
  - domain: another.org
    mode: testing
    mx:
      - "mail.another.org"
    max_age: 3600

resolver:
  cache_ttl: 3600
  timeout: 5
  dns_server: "127.0.0.1:53"
```

### Installation

```bash
git clone https://github.com/danmarg/sts-mate.git
cd sts-mate

# Install dependencies
pip install -r requirements.txt

# Configure
cp config.example.yml config.yml
# Edit config.yml with your domains and settings

# Run
python sts_mate.py --config config.yml
```

## Comparison Table

| Feature | postfix-mta-sts-resolver | postfix-tlspol | sts-mate |
|---------|-------------------------|----------------|----------|
| **GitHub Stars** | 125 | 42 | 14 |
| **Primary Role** | MTA-STS resolver | MTA-STS plus DANE resolver | Policy server and resolver |
| **MTA Integration** | Postfix socketmap | Postfix socketmap | HTTP API |
| **DANE Support** | No | Yes (DANE-first) | No |
| **Policy Hosting** | No | No | Yes |
| **Caching** | SQLite cache | SQLite cache | In-memory and disk |
| **Multi-Domain** | Per-domain lookup | Per-domain lookup | Built-in multi-tenant |
| **Certificate Mgmt** | N/A | N/A | Let Encrypt auto-renewal |
| **Language** | Python | Python | Python |
| **Best For** | Postfix MTA-STS enforcement | Defense-in-depth TLS | Policy hosting plus resolution |

## Choosing the Right Tool

**Use postfix-mta-sts-resolver if:** You run Postfix and need straightforward MTA-STS policy enforcement. It is the most widely deployed option with the largest community, extensive documentation, and proven production reliability. If your only requirement is enforcing MTA-STS policies for inbound mail, this is the simplest and most reliable choice.

**Use postfix-tlspol if:** You want maximum email encryption security through layered defense. By combining DANE (certificate pinning via DNSSEC) with MTA-STS (policy-based enforcement), you get stronger guarantees than either protocol alone. This requires a DNSSEC-validating resolver (like Unbound) but provides the highest level of SMTP TLS enforcement available.

**Use sts-mate if:** You need to both host MTA-STS policies for your own domains and resolve policies for domains you send mail to. Its dual-role architecture means a single service handles both inbound policy hosting and outbound policy resolution. The built-in Let Encrypt integration eliminates the need for separate certificate management.

For email security context, see our [MTA-STS and DANE email security guide](../2026-04-28-self-hosted-mta-sts-smtp-dane-email-security-guide/) and [SMTP TLS enforcement comparison](../2026-05-13-self-hosted-smtp-tls-enforcement-postfix-haraka-exim-guide/).

## Why Self-Host MTA-STS Infrastructure?

Running your own MTA-STS policy resolution infrastructure — rather than depending on third-party services — provides several critical advantages:

**Complete email security control.** MTA-STS policy enforcement is a security boundary. When you run your own resolver, you control exactly which policies are accepted, how validation failures are handled, and what fallback behavior applies. Third-party resolvers may have different security thresholds or caching behaviors that do not match your requirements.

**Privacy and data protection.** MTA-STS policy resolvers see every domain you send mail to — they must fetch and cache policies for each recipient domain. Running your own resolver keeps this metadata within your infrastructure. A third-party resolver provider could build a profile of your communication patterns based on policy lookup patterns.

**No external dependencies.** Email delivery should not depend on a third-party service availability. If a hosted MTA-STS resolver goes down, your mail delivery may fall back to unencrypted SMTP. Self-hosted resolvers run on your infrastructure with your uptime requirements, eliminating a critical single point of failure.

**Regulatory compliance.** Many industries require that email encryption be enforced and auditable. Self-hosted MTA-STS resolvers provide local logging of all policy lookups and enforcement decisions, creating an audit trail that satisfies compliance requirements. Third-party resolvers may not provide the level of logging or reporting your compliance framework demands.

**Custom policy enforcement.** Self-hosted resolvers can be configured with custom enforcement rules: override policies for specific domains, apply stricter security requirements for certain recipient categories, or implement gradual rollout of MTA-STS enforcement across your organization. These customizations are not possible with hosted solutions.

For email infrastructure reading, see our [email security auditing guide](../2026-05-12-self-hosted-email-security-auditing-mailauth-mailsec-check-checkdmarc-guide/) and [SMTP relay comparison](../2026-04-26-postal-vs-stalwart-vs-haraka-self-hosted-smtp-relay-guide-2026/).

## FAQ

### What is MTA-STS and why does it matter?

MTA-STS (Mail Transfer Agent Strict Transport Security, RFC 8461) is a mechanism that allows domain owners to declare their ability to receive encrypted SMTP connections and require sending mail servers to use TLS. Without MTA-STS, SMTP silently falls back to plaintext when TLS negotiation fails, enabling man-in-the-middle attacks. MTA-STS prevents this downgrade by publishing a policy that mandates TLS enforcement.

### Do I need MTA-STS if I already use DANE?

DANE and MTA-STS serve complementary purposes. DANE requires DNSSEC to be deployed for your domain and uses TLSA records to pin certificates. MTA-STS does not require DNSSEC but relies on HTTPS-delivered policies. Using both provides defense-in-depth: DANE gives you certificate pinning, MTA-STS gives you policy-based enforcement. postfix-tlspol supports both protocols in a single resolver.

### Can I use these tools with Exim or other MTAs?

postfix-mta-sts-resolver and postfix-tlspol are designed specifically for Postfix socketmap integration. For Exim, you would need to use a different approach — typically an MTA-STS-aware transport that queries a policy resolver via HTTP. sts-mate provides an HTTP API that can be used with any MTA that supports external policy lookups.

### How long are MTA-STS policies cached?

The cache duration is determined by the `max_age` field in the MTA-STS policy file, which the domain owner sets. Typical values range from 86,400 seconds (one day) to 1,209,600 seconds (two weeks). All three tools respect this value and cache policies accordingly. After the cache expires, the policy is re-fetched from the domain.

### What happens if the MTA-STS policy server is unreachable?

All three tools handle this gracefully. postfix-mta-sts-resolver and postfix-tlspol will use a cached policy if available, or fall back to the configured default behavior (typically allowing plaintext if no policy exists). sts-mate has configurable timeout and fallback settings. The key is that temporary unreachability should not cause permanent mail delivery failures.

### Do I need to host my own MTA-STS policy file?

If you want receiving mail servers to enforce TLS when sending to your domain, yes — you need to host an MTA-STS policy file at `https://mta-sts.yourdomain.com/.well-known/mta-sts.txt`. sts-mate can host this for you. Alternatively, you can use GitHub Pages, Cloudflare Pages, or any HTTPS-enabled web server to serve the policy file.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted MTA-STS Policy Servers: postfix-mta-sts-resolver vs postfix-tlspol vs sts-mate (2026)",
  "description": "Compare MTA-STS policy server tools for self-hosted email security enforcement. postfix-mta-sts-resolver, postfix-tlspol, and sts-mate compared.",
  "datePublished": "2026-05-14",
  "dateModified": "2026-05-14",
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
