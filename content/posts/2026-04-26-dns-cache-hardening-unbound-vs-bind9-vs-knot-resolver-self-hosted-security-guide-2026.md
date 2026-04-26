---
title: "DNS Cache Hardening: Unbound vs BIND 9 vs Knot Resolver - Self-Hosted Security Guide 2026"
date: 2026-04-26
tags: ["comparison", "guide", "self-hosted", "dns", "security", "privacy"]
draft: false
description: "Compare DNS cache hardening features in Unbound, BIND 9, and Knot Resolver. Learn how to protect your self-hosted DNS resolver from cache poisoning and spoofing attacks with practical Docker deployment configs."
---

## Why DNS Cache Hardening Matters for Self-Hosted Infrastructure

Every DNS query your network makes passes through a recursive resolver. That resolver caches answers to speed up subsequent lookups — but the cache itself is a high-value attack surface. DNS cache poisoning attacks can redirect your users to malicious servers, intercept encrypted traffic, and silently compromise your entire network.

A hardened DNS resolver mitigates these risks through multiple defense layers: DNSSEC validation, QNAME minimization, cache segregation, source port randomization, and aggressive cache-ttl policies. The three most mature open-source recursive resolvers — **Unbound**, **BIND 9**, and **Knot Resolver** — each take different approaches to cache security.

This guide compares their hardening features side by side and provides production-ready Docker deployment configurations so you can deploy a hardened resolver in minutes.

## Understanding DNS Cache Poisoning

DNS cache poisoning exploits the fact that DNS was designed without authentication. An attacker who can spoof a DNS response before the legitimate reply arrives can inject false records into your resolver's cache. The classic Kaminsky attack (2008) demonstrated how attackers could poison any record by flooding the resolver with forged responses during the brief window between query and response.

Modern resolvers defend against this through several mechanisms:

- **DNSSEC validation** — cryptographically verifies answer authenticity
- **Source port randomization** — makes it harder to guess the query ID + port combination
- **QNAME minimization** — sends only the minimum necessary query to upstream servers, reducing information leakage
- **Cache-minimize mode** — avoids caching unnecessary referral data that could be poisoned
- **Aggressive use of NSEC/NSEC3** — securely proves non-existence of domains, preventing wildcard spoofing
- **Strict cache TTL enforcement** — prevents attackers from keeping poisoned entries alive

## Unbound: Security-First DNS Resolver

[Unbound](https://github.com/NLnetLabs/unbound) (4,469 GitHub stars, last updated April 2026) was designed from the ground up with security as its primary goal. Developed by NLnet Labs and maintained by the OSS community, it is the default recursive resolver on OpenBSD and widely recommended for hardened DNS deployments.

### Cache Hardening Features

Unbound's cache hardening configuration options are among the most comprehensive of any open-source resolver:

```yaml
# unbound.conf — DNS cache hardening configuration
server:
  # DNSSEC validation — non-negotiable for cache security
  auto-trust-anchor-file: "/var/lib/unbound/root.key"

  # Minimize query names sent to upstream servers
  qname-minimisation: yes
  qname-minimisation-strict: yes

  # Harden against DNS spoofing
  harden-glue: yes
  harden-dnssec-stripped: yes
  harden-below-nxdomain: yes
  harden-algo-downgrade: yes
  harden-short-bufsize: yes

  # Cache minimization — only cache what's needed
  cache-minimize: yes

  # Aggressive NSEC use — prevents spoofed NXDOMAIN
  aggressive-nsec: yes

  # Prefetch popular entries to reduce cache window
  prefetch: yes
  prefetch-key: yes

  # Restrict access to authorized networks only
  access-control: 192.168.1.0/24 allow
  access-control: 127.0.0.1 allow
  access-control: 0.0.0.0/0 refuse

  # Hide server identity
  hide-identity: yes
  hide-version: yes

  # Rate limiting to prevent amplification attacks
  ratelimit: 1000
  ratelimit-below-domain: 100
```

Key strengths of Unbound's approach:

- **`harden-*` flags** — seven separate hardening toggles that independently validate and restrict cache behavior
- **`cache-minimize`** — prevents the resolver from caching unnecessary NS/A records that could be poisoned
- **`aggressive-nsec`** — uses DNSSEC proof-of-nonexistence to answer negative queries from cache, reducing upstream queries
- **`qname-minimisation-strict`** — sends only the rightmost label to root servers, progressively revealing more as needed

### Docker Deployment

```yaml
version: "3.8"
services:
  unbound:
    image: mvance/unbound:latest
    container_name: unbound-hardened
    restart: unless-stopped
    ports:
      - "53:53/tcp"
      - "53:53/udp"
    volumes:
      - ./unbound.conf:/opt/unbound/etc/unbound/unbound.conf:ro
      - unbound-root-keys:/var/lib/unbound
    networks:
      dns-net:
        ipv4_address: 172.20.0.2

networks:
  dns-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24

volumes:
  unbound-root-keys:
```

## BIND 9: The Battle-Tested Resolver

[BIND 9](https://gitlab.isc.org/isc-projects/bind9) is maintained by the Internet Systems Consortium (ISC). The GitHub mirror shows 739 stars but is archived — primary development moved to GitLab. BIND 9 has been the reference DNS implementation since 1998 and ships with most Linux distributions.

### Cache Hardening Features

BIND 9's hardening options focus on DNSSEC validation and query/response control:

```named.conf
// named.conf — BIND 9 cache hardening configuration
options {
  directory "/var/cache/bind";

  // DNSSEC validation
  dnssec-validation auto;

  // QNAME minimization (BIND 9.17+)
  qname-minimization yes;

  // Harden cache behavior
  minimal-responses yes;
  minimal-any yes;

  // Restrict recursion to trusted networks only
  recursion yes;
  allow-recursion { trusted-nets; };
  allow-query { any; };

  // Rate limiting
  rate-limit {
    responses-per-second 10;
    window 5;
    slip 2;
    errors-per-second 5;
    all-per-second 20;
  };

  // Disable unnecessary features
  version "not disclosed";
  hostname "not disclosed";
  server-id "disabled";

  // Listen only on designated interfaces
  listen-on port 53 { 127.0.0.1; 192.168.1.10; };
  listen-on-v6 { none; };
};

acl trusted-nets {
  127.0.0.0/8;
  192.168.1.0/24;
};
```

BIND 9's approach differs from Unbound:

- **`dnssec-validation auto`** — automatically manages trust anchors, similar to Unbound
- **`minimal-responses`** — reduces the amount of data in responses, limiting poisoning surface
- **`minimal-any`** — prevents ANY query amplification attacks
- **`rate-limit`** — built-in response rate limiting (RRL) to mitigate amplification
- BIND 9 does **not** have a direct equivalent to Unbound's `aggressive-nsec` or `cache-minimize` flags

The resolver's strength lies in its maturity and the extensive `rate-limit` block, which provides fine-grained control over response rates per client, per domain, and globally.

### Docker Deployment

```yaml
version: "3.8"
services:
  bind9:
    image: ubuntu/bind9:latest
    container_name: bind9-hardened
    restart: unless-stopped
    ports:
      - "53:53/tcp"
      - "53:53/udp"
    environment:
      - BIND9_USER=bind
    volumes:
      - ./named.conf:/etc/bind/named.conf:ro
      - ./named.conf.options:/etc/bind/named.conf.options:ro
      - ./zones:/etc/bind/zones:ro
      - bind-cache:/var/cache/bind
    networks:
      dns-net:
        ipv4_address: 172.20.0.3

networks:
  dns-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24

volumes:
  bind-cache:
```

## Knot Resolver: Modern and Extensible

[Knot Resolver](https://github.com/CZ-NIC/knot-resolver) (434 GitHub stars, last updated April 2026) is developed by CZ.NIC, the Czech national domain registry operator. It is built on top of the Knot DNS library and uses the Lua scripting language for policy modules — making it the most programmable of the three resolvers.

### Cache Hardening Features

Knot Resolver's approach is module-based, allowing you to compose security features as Lua policy modules:

```lua
-- kresd.conf — Knot Resolver cache hardening configuration

-- Load core modules
modules = {
  'policy',      -- Request/response policy filtering
  'stats',       -- Query statistics
  'hints',       -- Static DNS hints
}

-- DNSSEC validation (enabled by default)
-- trust_anchors.add_file('/etc/knot-resolver/root.keys')

-- QNAME minimization (enabled by default)

-- Cache hardening via policy module
policy.add(policy.all(policy.TLS_FORWARD({
  -- Forward to upstream servers over TLS
  {'1.1.1.1'},
  {'9.9.9.9'},
})))

-- Block known malicious domains via RPZ-style policies
policy.add(policy.suffix(policy.DENY,
  {todname('malware.example.com.')}))

-- Rate limiting via policy
-- policy.add(policy.RATE_LIMIT(100))

-- Cache configuration
cache.size = 100 * MB

-- Hide resolver identity
net.listen({'127.0.0.1', '192.168.1.0/24'}, 53)

-- Aggressive NSEC (enabled when DNSSEC is active)
-- policy.add(policy.AGGRESSIVE_NSEC)
```

Knot Resolver's unique advantages:

- **Lua policy modules** — write custom security policies in Lua, enabling fine-grained control over every query and response
- **DNSSEC enabled by default** — unlike Unbound and BIND 9 which require explicit configuration
- **QNAME minimization enabled by default** — another security feature active out of the box
- **`policy.TLS_FORWARD`** — forwards all queries over TLS, protecting against upstream interception
- **Built-in RPZ-style filtering** — deny specific domains, block categories, and redirect queries via policy rules

### Docker Deployment

```yaml
version: "3.8"
services:
  knot-resolver:
    image: cznic/knot-resolver:latest
    container_name: knot-hardened
    restart: unless-stopped
    ports:
      - "53:53/tcp"
      - "53:53/udp"
    volumes:
      - ./kresd.conf:/etc/knot-resolver/kresd.conf:ro
      - knot-cache:/var/cache/knot-resolver
    command: ["kresd", "-c", "/etc/knot-resolver/kresd.conf"]
    networks:
      dns-net:
        ipv4_address: 172.20.0.4

networks:
  dns-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24

volumes:
  knot-cache:
```

## Feature Comparison Table

| Feature | Unbound | BIND 9 | Knot Resolver |
|---------|---------|--------|---------------|
| DNSSEC Validation | ✅ auto-trust-anchor | ✅ `dnssec-validation auto` | ✅ Enabled by default |
| QNAME Minimization | ✅ `qname-minimisation` | ✅ `qname-minimization` (9.17+) | ✅ Enabled by default |
| Aggressive NSEC | ✅ `aggressive-nsec` | ❌ Not supported | ✅ Via policy module |
| Cache Minimize | ✅ `cache-minimize` | ❌ Not supported | ⚠️ Partial via modules |
| Harden Glue | ✅ `harden-glue` | ⚠️ Implicit | ⚠️ Via policy |
| Rate Limiting | ✅ `ratelimit` | ✅ `rate-limit` (RRL) | ✅ `policy.RATE_LIMIT` |
| Strict Hardening | ✅ 7 `harden-*` flags | ⚠️ Limited | ✅ Via policy modules |
| TLS Upstream | ✅ `forward-tls-upstream` | ❌ Requires Stunnel | ✅ `policy.TLS_FORWARD` |
| Custom Policies | ❌ No scripting | ❌ No scripting | ✅ Lua modules |
| Docker Image | ✅ `mvance/unbound` | ✅ `ubuntu/bind9` | ✅ `cznic/knot-resolver` |
| Default Security | ⚠️ Requires config | ⚠️ Requires config | ✅ Secure defaults |
| GitHub Stars | 4,469 | 739 (mirror) | 434 |

## Performance and Resource Comparison

| Metric | Unbound | BIND 9 | Knot Resolver |
|--------|---------|--------|---------------|
| Memory (idle) | ~50 MB | ~100 MB | ~80 MB |
| Memory (heavy cache) | ~200 MB | ~500 MB | ~300 MB |
| Queries/sec (single core) | ~250K | ~150K | ~200K |
| Configuration language | YAML-style | BIND9 zone format | Lua |
| Learning curve | Low | Medium | Medium-High |

Unbound is the lightest and fastest for pure DNS resolution. BIND 9 uses the most memory but offers the deepest feature set for complex deployments. Knot Resolver sits in the middle, trading some raw performance for programmability.

## Which Resolver Should You Choose?

**Choose Unbound if:**
- You want the most hardened resolver with the least configuration effort
- You need maximum cache hardening flags out of the box
- Resource efficiency is a priority (low memory footprint)
- You are deploying on OpenBSD, pfSense, or OPNsense (it is the default)

**Choose BIND 9 if:**
- You need authoritative and recursive DNS in a single process
- Your environment requires RRL (Response Rate Limiting) with fine-grained controls
- You are already managing BIND 9 authoritative zones and want to consolidate
- Your organization has existing BIND 9 expertise

**Choose Knot Resolver if:**
- You want programmable security policies via Lua scripting
- You need DNSSEC and QNAME minimization enabled by default
- You want built-in TLS forwarding without external dependencies
- You need RPZ-style filtering with custom logic

For most self-hosted homelab users, **Unbound** offers the best balance of security, simplicity, and performance. Its seven hardening flags are the most comprehensive defense against cache poisoning available in any open-source resolver.

## FAQ

### What is DNS cache poisoning and how does it work?

DNS cache poisoning is an attack where a forged DNS response is injected into a resolver's cache, causing the resolver to return incorrect IP addresses for domain names. The attacker sends a spoofed response that arrives before the legitimate answer from the authoritative server. If the resolver accepts the forged response, it caches the false record and serves it to all subsequent clients, redirecting them to attacker-controlled servers.

### Is DNSSEC enough to prevent cache poisoning?

DNSSEC is the single most effective defense against cache poisoning because it cryptographically validates every answer. However, it is not sufficient on its own. DNSSEC only protects zones that are signed (most major TLDs and domains are, but not all). Cache hardening features like QNAME minimization, aggressive NSEC, and rate limiting provide additional layers of defense that protect against attacks even when DNSSEC validation is not possible.

### Can I use multiple hardened resolvers together?

Yes. A common architecture is to run Unbound as the primary resolver with BIND 9 or Knot Resolver as a secondary/failover resolver. You can also stack them — for example, use Knot Resolver with TLS forwarding to upstream Unbound instances, creating a defense-in-depth pipeline. Docker Compose makes this topology straightforward to deploy.

### How often should I rotate DNSSEC trust anchors?

DNSSEC trust anchors (root keys) are automatically managed by all three resolvers through RFC 5011 automatic key rollover. You should still periodically verify that the root key file is valid. In Unbound, check `/var/lib/unbound/root.key`. In BIND 9, check `managed-keys-directory`. In Knot Resolver, trust anchors are managed internally and updated automatically.

### Does running a hardened resolver slow down DNS resolution?

The performance impact is negligible. DNSSEC validation adds approximately 5-15ms per query (only for the first lookup — subsequent queries are served from cache). QNAME minimization may add one extra round-trip for some queries. Aggressive NSEC actually *improves* performance for negative queries by answering them from cache instead of querying upstream. In practice, a properly configured hardened resolver is indistinguishable in speed from a non-hardened one for end users.

### What is QNAME minimization and why does it matter?

QNAME minimization reduces the amount of query information sent to upstream DNS servers. Instead of sending the full domain name (e.g., `mail.example.com`) to the root server, the resolver sends only the top-level domain (`com`) and progressively reveals more labels as it descends the DNS hierarchy. This prevents upstream servers from learning your full query patterns, which improves privacy and reduces the attack surface for targeted poisoning attacks.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "DNS Cache Hardening: Unbound vs BIND 9 vs Knot Resolver - Self-Hosted Security Guide 2026",
  "description": "Compare DNS cache hardening features in Unbound, BIND 9, and Knot Resolver. Learn how to protect your self-hosted DNS resolver from cache poisoning and spoofing attacks with practical Docker deployment configs.",
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

For related reading, see our [PowerDNS vs BIND 9 vs NSD vs Knot authoritative DNS guide](../2026-04-18-powerdns-vs-bind9-vs-nsd-vs-knot-self-hosted-authoritative-dns-2026/) and [DNSSEC management with OpenDNSSEC vs Knot DNS vs BIND](../opendnssec-vs-knot-dns-vs-bind-self-hosted-dnssec-management-guide-2026/).
