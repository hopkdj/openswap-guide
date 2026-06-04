---
title: "Self-Hosted DNS Forwarding & Caching Proxies: dnsmasq vs Unbound vs PowerDNS Recursor"
date: "2026-06-04"
tags: ["dns", "dnsmasq", "unbound", "powerdns", "networking", "dns-caching", "dns-forwarding", "infrastructure", "self-hosted", "privacy"]
draft: false
---

## Introduction

Every application on your network depends on DNS — yet most self-hosted environments run whatever resolver came with the distribution. A properly configured DNS forwarding and caching proxy reduces latency, improves privacy by minimizing upstream queries, and provides local control over name resolution.

This article compares three leading open-source DNS forwarders: dnsmasq (lightweight + DHCP), Unbound (validating recursive resolver), and PowerDNS Recursor (high-performance resolver with scripting). We cover installation, performance characteristics, and deployment configurations for self-hosted environments.

## Understanding DNS Forwarding vs Recursion

Before comparing tools, it is worth clarifying the two modes a DNS proxy can operate in:

- **Forwarding**: The proxy sends all queries to a configured upstream resolver (like 1.1.1.1 or 8.8.8.8) and caches the responses. This is the simplest setup and works behind NAT.
- **Recursive resolution**: The proxy walks the DNS hierarchy itself, starting from the root servers, to resolve names. This provides better privacy (no single upstream sees all your queries) but requires direct internet access.

All three tools support both modes, but they have different strengths depending on which you primarily need.

## Comparison Table

| Feature | dnsmasq | Unbound | PowerDNS Recursor |
|---------|---------|---------|-------------------|
| **Primary Role** | DNS forwarder + DHCP | Validating recursive resolver | High-performance resolver |
| **Caching** | In-memory, TTL-based | In-memory, prefetch, serve-expired | In-memory, packet cache, aggressive NSEC |
| **DNSSEC Validation** | Limited (pass-through) | Full validation | Full validation |
| **DHCP Server** | Built-in | No | No |
| **Upstream Forwarding** | Yes (default mode) | Yes (configurable) | Yes (configurable via `forward-zones`) |
| **RPZ / Filtering** | Via config files | Via RPZ zones, Python module | Via Lua scripting, RPZ |
| **DNS-over-TLS** | Via stubby proxy | Native since 1.7.0 | Native (`dot-to-auth-names`) |
| **DNS-over-HTTPS** | No | Native (DNS-over-HTTPS service) | Via proxy (dnsdist) |
| **Performance** | ~1,000 qps (lightweight) | ~10,000 qps (moderate) | ~100,000+ qps (high performance) |
| **Memory Usage** | ~5-10 MB | ~50-100 MB | ~100-300 MB |
| **Configuration** | Simple config file | YAML / unbound.conf | Lua-based scripting |
| **GitHub Stars** | Community maintained | 3,494+ (NLnet Labs) | 3,941+ (PowerDNS) |

## dnsmasq

dnsmasq is the classic lightweight DNS forwarder and DHCP server found in most home routers, OpenWrt, and many Docker environments. It excels at simplicity and minimal resource consumption.

**Key features:**
- Combined DNS forwarder and DHCP server in a single daemon
- Local DNS record configuration via `/etc/hosts` or custom config files
- DNSSEC trust anchor support (validates responses when forwarding)
- Split-horizon DNS with conditional forwarding rules
- TFTP server for PXE booting
- Active community with packages in all major distributions

**Docker Compose deployment:**

```yaml
version: '3'
services:
  dnsmasq:
    image: jpillora/dnsmasq:latest
    container_name: dnsmasq
    restart: unless-stopped
    ports:
      - "53:53/udp"
      - "53:53/tcp"
      - "8080:8080"
    environment:
      - HTTP_USER=admin
      - HTTP_PASS=securepassword
    volumes:
      - ./dnsmasq.conf:/etc/dnsmasq.conf
    cap_add:
      - NET_ADMIN
```

**Configuration example (`dnsmasq.conf`):**

```ini
# Upstream servers
server=1.1.1.1
server=8.8.8.8

# Cache 1000 entries
cache-size=10000

# Local domain override
address=/myapp.local/192.168.1.100

# Conditional forwarding
server=/internal.example.com/192.168.1.53

# DNSSEC validation
dnssec
trust-anchor=.,20326,8,2,E06D44B80B8F1D39A95C0B0D7C65D08458E880409BBC683457104237C7F8EC8D

# Logging
log-queries
log-facility=/var/log/dnsmasq.log
```

## Unbound

Unbound is a validating, recursive, and caching DNS resolver developed by NLnet Labs. It is the default resolver in FreeBSD and is widely used for privacy-focused DNS configurations. Unbound performs full DNSSEC validation by default, ensuring the integrity of every response.

**Key features:**
- Full recursive resolver with DNSSEC validation (RFC 4033-4035)
- DNS-over-TLS (DoT) upstream forwarding
- DNS-over-HTTPS (DoH) service endpoint
- Response Policy Zones (RPZ) for filtering
- Prefetch and serve-expired for cache optimization
- Redis backend for persistent caching (optional)
- Python module for custom scripting

**Docker Compose deployment:**

```yaml
version: '3'
services:
  unbound:
    image: klutchell/unbound:latest
    container_name: unbound
    restart: unless-stopped
    ports:
      - "53:53/udp"
      - "53:53/tcp"
    volumes:
      - ./unbound.conf:/etc/unbound/unbound.conf:ro
    healthcheck:
      test: ["CMD", "unbound-control", "status"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**Configuration example (`unbound.conf`):**

```yaml
server:
    interface: 0.0.0.0
    port: 53
    access-control: 192.168.0.0/16 allow
    access-control: 127.0.0.0/8 allow
    
    # Cache settings
    cache-min-ttl: 3600
    cache-max-ttl: 86400
    prefetch: yes
    serve-expired: yes
    
    # DNSSEC
    auto-trust-anchor-file: "/etc/unbound/root.key"
    val-clean-additional: yes
    
    # Privacy
    qname-minimisation: yes
    hide-identity: yes
    hide-version: yes

forward-zone:
    name: "."
    forward-tls-upstream: yes
    forward-addr: 1.1.1.1@853#cloudflare-dns.com
    forward-addr: 8.8.8.8@853#dns.google

# RPZ blocking
rpz:
    name: "malware.rpz"
    zonefile: "/etc/unbound/malware.rpz"
```

## PowerDNS Recursor

The PowerDNS Recursor is a high-performance DNS resolver designed for service providers and large-scale deployments. It uses an internal packet cache to achieve extremely high query rates and supports Lua scripting for custom resolution logic.

**Key features:**
- Aggressive NSEC caching for DNSSEC-signed zones
- Lua scripting hooks for custom query processing
- RPZ support with IXFR-based automatic updates
- EDNS Client Subnet handling for CDN-aware responses
- Protobuf logging for analytics pipelines
- Built-in web server for statistics and monitoring
- DNS-over-TLS forwarding to authoritative servers

**Docker Compose deployment:**

```yaml
version: '3'
services:
  pdns-recursor:
    image: powerdns/pdns-recursor-51:latest
    container_name: pdns-recursor
    restart: unless-stopped
    ports:
      - "53:53/udp"
      - "53:53/tcp"
      - "8082:8082"
    environment:
      - PDNS_api_key=changeme
      - PDNS_webserver=yes
      - PDNS_webserver_address=0.0.0.0
      - PDNS_webserver_port=8082
      - PDNS_webserver_allow_from=192.168.0.0/16,127.0.0.0/8
    volumes:
      - ./recursor.conf:/etc/powerdns/recursor.conf:ro
```

**Configuration example (`recursor.conf`):**

```ini
# Network settings
local-address=0.0.0.0
allow-from=192.168.0.0/16,127.0.0.0/8

# Forwarding (optional — default is recursive)
forward-zones=.=1.1.1.1;8.8.8.8
forward-zones-recurse=.=1.1.1.1;8.8.8.8

# Caching
max-cache-entries=1000000
max-packetcache-entries=500000
packetcache-ttl=3600
packetcache-servfail-ttl=60

# DNSSEC
dnssec=validate

# RPZ
rpz-file=/etc/powerdns/rpz.zone

# Lua scripting
lua-config-file=/etc/powerdns/recursor.lua

# Performance
threads=4
distributor-threads=4
```

## Why Self-Host Your DNS Caching Proxy?

Running your own DNS caching proxy provides benefits that go far beyond simple name resolution for your local network.

**Latency Reduction.** Every DNS query that leaves your network takes 20-50 ms round-trip to a public resolver. A local cache serves repeated queries in under 1 ms. For a typical web page that triggers 50-100 DNS lookups, this can save 1-3 seconds of page load time. Over thousands of daily requests, the aggregate time savings are substantial.

**Privacy Protection.** When you forward all DNS queries to a single upstream provider (like Google DNS or Cloudflare), that provider builds a complete profile of every domain your network accesses. With a recursive resolver like Unbound, queries fan out across the global DNS hierarchy — no single entity sees your complete browsing patterns. This is particularly important for self-hosted environments handling sensitive operational data.

**Local Control.** A local DNS proxy lets you override public DNS records for internal services, block malicious domains via RPZ feeds, and create split-horizon configurations where internal clients see different DNS results than external queries. This flexibility is essential for complex self-hosted architectures with multiple internal services and VLANs.

For more DNS infrastructure guidance, check our [DNS-over-TLS resolver guide](../self-hosted-dns-over-tls-resolver-stubby-unbound-knot-2026/) and [DNS TTL optimization article](../2026-05-11-self-hosted-dns-ttl-optimization-cache-tuning-unbound-powerdns-knot-guide/). For broader networking context, see our [DNS CAA record management guide](../2026-05-17-self-hosted-dns-caa-record-management-bind-powerdns-knot-guide/).

## Choosing the Right DNS Proxy

**Choose dnsmasq if:** You need a simple, lightweight forwarder that doubles as a DHCP server. It is ideal for home lab setups, small office networks, and Docker Compose stacks where simplicity matters more than raw performance.

**Choose Unbound if:** Privacy is your primary concern and you want DNSSEC validation out of the box. Unbound excels as a recursive resolver that minimizes information leakage to upstream providers, and its Python module enables custom filtering logic.

**Choose PowerDNS Recursor if:** You serve a large network (50+ clients), need Lua scripting for custom DNS logic, or require >50,000 queries per second. The Recursor's packet cache and threading model are purpose-built for ISP-level query volumes.

## FAQ

### What is the difference between a DNS forwarder and a recursive resolver?

A DNS forwarder sends all queries to one or more configured upstream resolvers (like your ISP's DNS or Cloudflare). A recursive resolver walks the DNS tree from the root servers down, contacting authoritative nameservers directly. Forwarders are simpler to configure; recursive resolvers provide better privacy since queries are distributed across the global DNS infrastructure.

### Can I use dnsmasq and Unbound together?

Yes — this is a common pattern. Run Unbound as your recursive resolver (listening on port 5353) and configure dnsmasq to forward to Unbound on that port. This gives you dnsmasq's DHCP server and lightweight caching plus Unbound's DNSSEC validation and recursive resolution. Many pfSense and OPNsense deployments use this exact architecture.

### How much memory does DNS caching consume?

dnsmasq uses 5-10 MB with a default 10,000-entry cache. Unbound uses 50-100 MB with 100,000+ entries. PowerDNS Recursor uses 100-300 MB depending on the packet cache size. Even the largest cache footprint is negligible on modern hardware — run whichever resolver fits your feature requirements.

### Do these tools support DNS-over-HTTPS (DoH)?

Unbound has native DNS-over-HTTPS support as a service endpoint (clients can query it over HTTPS). For forwarding over DoH to upstream providers, you can use a companion proxy like `dnscrypt-proxy` or `cloudflared`. PowerDNS offers DoH through its companion tool `dnsdist`. dnsmasq does not natively support DoH.

### How do I monitor DNS resolver performance?

All three tools expose metrics. dnsmasq logs query statistics on SIGUSR1. Unbound provides `unbound-control stats_noreset` with detailed cache hit ratios and query types. PowerDNS Recursor has a built-in web API at port 8082 with JSON metrics and a `/metrics` Prometheus endpoint via the `webserver` module.

### Is DNSSEC validation important for a caching proxy?

If you are forwarding to a trusted upstream that validates DNSSEC (like 1.1.1.1 or 9.9.9.9), your local proxy does not need to validate — the upstream handles it. If you are doing recursive resolution, enable DNSSEC validation to protect against cache poisoning attacks. Unbound and PowerDNS Recursor enable validation by default.

---

**💰 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — the world's largest prediction market platform where you can bet on everything from election results to technology regulatory timelines. Unlike gambling, this is a real information market: the more you know, the better your edge. I've already made good money predicting the direction of technology-related events. Sign up with my referral link: [Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DNS Forwarding and Caching Proxies: dnsmasq vs Unbound vs PowerDNS Recursor",
  "description": "Comprehensive comparison of three leading open-source DNS forwarding and caching proxies — dnsmasq, Unbound, and PowerDNS Recursor — for self-hosted network infrastructure, privacy, and performance optimization.",
  "datePublished": "2026-06-04",
  "dateModified": "2026-06-04",
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
