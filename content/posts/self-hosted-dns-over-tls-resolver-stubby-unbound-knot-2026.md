---
title: "Complete Guide to Self-Hosted DNS-over-TLS Resolvers 2026"
date: 2026-04-16
tags: ["comparison", "guide", "self-hosted", "privacy", "dns", "dot"]
draft: false
description: "Compare Stubby, Unbound, and Knot Resolver for running your own DNS-over-TLS (DoT) resolvers. Includes Docker configs, setup guides, and performance benchmarks."
---

Every DNS query your devices send travels in plain text by default. That means your ISP, network administrator, or anyone with access to the network path can see every domain you look up. DNS-over-TLS (DoT) fixes this by encrypting the entire DNS conversation inside a TLS tunnel on port 853, the same cryptographic protection you get from HTTPS.

While public DoT providers like [cloudflare](https://www.cloudflare.com/) (1.1.1.1) and Google (8.8.8.8) offer encrypted DNS, running your own DoT resolver gives you full control over query logging, filtering policies, upstream providers, and caching behavior. This guide walks through three production-ready open-source options: **Stubby**, **Unbound**, and **Knot Resolver**.

## Why Run Your Own DNS-over-TLS Resolver

Public DNS services are convenient, but a self-hosted DoT resolver offers several concrete advantages:

- **No query logging by third parties** — your DNS data never leaves your network except as encrypted queries to upstreams you choose
- **Custom filtering** — block ads, malware domains, and trackers at the DNS level before they reach any device
- **Improved caching** — local resolvers cache responses for your specific query patterns, reducing latency for repeated lookups
- **Resilience** — if an upstream provider goes down, your resolver can failover to alternatives automatically
- **Split-horizon DNS** — serve different responses for internal vs. external domains, essential for homelab setups
- **Compliance** — some regulations require that DNS data never be processed by external commercial providers

The difference between DoT and the more commonly discussed DNS-over-HTTPS (DoH) is subtle but important. DoT uses a dedicated port (853) with standard TLS, making it easier for network equipment to identify and manage. DoH runs on port 443 alongside regular HTTPS traffic, which makes it harder to distinguish from normal web browsing but also harder for restrictive networks to block. For a self-hosted resolver, DoT is often the simpler choice since the protocol is purpose-built for DNS encryption.

## Stubby: Lightweight DoT Stub Resolver

Stubby is a minimal DNS stub resolver that acts as a local DoT client. It sits between your applications and upstream DoT servers, converting plain DNS queries from localhost into encrypted DoT requests. Stubby does not perform recursive resolution itself — it forwards queries to upstream resolvers over TLS.

Stubby was originally developed as part of the getdns API project and is maintained by the same team. It is designed to be a drop-in local resolver for desktop and server systems.

### Key Features

- Minimal resource footprint — typically under 10 MB of RAM
- Supports multiple upstream DoT servers with automatic failover
- DNSSEC validation passthrough (relies on upstream for validation)
- Configuration via a simple YAML file
- Available in most Linux distribution repositories

### [docker](https://www.docker.com/) Deployment

```yaml
# docker-compose.yml for Stubby
services:
  stubby:
    image: ghcr.io/getdnsapi/stubby:latest
    container_name: stubby
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./stubby.yml:/etc/stubby/stubby.yml:ro
      - ./stubby-resolv.conf:/etc/stubby-resolv.conf
    cap_add:
      - NET_BIND_SERVICE
```

The accompanying configuration file:

```yaml
# stubby.yml
resolution_type: GETDNS_RESOLUTION_STUB
dns_transport_list:
  - GETDNS_TRANSPORT_TLS
tls_authentication: GETDNS_AUTHENTICATION_REQUIRED
tls_query_padding_blocksize: 128
edns_client_subnet_private: 1
idle_timeout: 10000
listen_addresses:
  - 127.0.0.1@53
  - 0.0.0.0@53
dnssec:
  dnssec_return_status: GETDNS_EXTENSION_TRUE
upstream_recursive_servers:
  - address_data: 1.1.1.1
    tls_auth_name: "cloudflare-dns.com"
  - address_data: 1.0.0.1
    tls_auth_name: "cloudflare-dns.com"
  - address_data: 9.9.9.9
    tls_auth_name: "dns.quad9.net"
  - address_data: 149.112.112.112
    tls_auth_name: "dns.quad9.net"
  - address_data: 8.8.8.8
    tls_auth_name: "dns.google"
    tls_pubkey_pinset:
      - digest: "sha256"
        value: /4YFhPzDlMJMAtC2D5r2e3jEeHPz5Cz7bQmXvJvq0Q=
```

### Testing Your Stubby Setup

```bash
# Install drill (from ldns package) for DoT testing
sudo apt install ldnsutils

# Query through local stubby
dig @127.0.0.1 example.com

# Check which upstream was used (enable stubby logging)
sudo journalctl -u stubby -f

# Verify encryption with stubby-status
stubby -i
```

Stubby is ideal for single-machine setups where you want encrypted upstream DNS with minimal configuration overhead. It is not a full recursive resolver, so it depends on the DNSSEC validation quality of your chosen upstream servers.

## Unbound: Full Recursive Resolver with DoT Forwarding

Unbound is a validating, recursive, and caching DNS resolver developed by NLnet Labs. It is one of the most widely deployed open-source DNS resolvers and has supported DNS-over-TLS forwarding since version 1.9.0. Unlike Stubby, Unbound can operate as a full recursive resolver — walking the DNS hierarchy from root servers to authoritative nameservers — or as a forwarding resolver that sends queries to upstream DoT servers.

### Key Features

- Full recursive DNS resolution with DNSSEC validation
- DoT forwarding to upstream servers with configurable authentication
- Advanced caching with prefetch and serve-expired options
- Local zone definitions for split-horizon DNS
- Python module support for custom query processing
- RPZ (Response Policy Zone) support for DNS-based filtering
- Extensive statistics and monitoring via `unbound-control`
- Active development with regular security updates

### Docker Deployment

```yaml
# docker-compose.yml for Unbound with DoT
services:
  unbound:
    image: mvance/unbound:latest
    container_name: unbound
    restart: unless-stopped
    ports:
      - "53:53/tcp"
      - "53:53/udp"
    volumes:
      - ./unbound.conf:/opt/unbound/etc/unbound/unbound.conf:ro
    healthcheck:
      test: ["CMD", "drill", "@127.0.0.1", "example.com"]
      interval: 30s
      timeout: 10s
      retries: 3
```

```conf
# unbound.conf — DoT forwarding configuration
server:
    # Listen on all interfaces (restrict with interface: if needed)
    interface: 0.0.0.0
    port: 53
    do-ip4: yes
    do-ip6: no
    do-udp: yes
    do-tcp: yes

    # Access control — allow local network only
    access-control: 127.0.0.0/8 allow
    access-control: 192.168.0.0/16 allow
    access-control: 10.0.0.0/8 allow
    access-control: 172.16.0.0/12 allow

    # DNSSEC validation
    auto-trust-anchor-file: "/var/lib/unbound/root.key"

    # Privacy settings
    hide-identity: yes
    hide-version: yes
    qname-minimisation: yes

    # Caching tuning
    cache-min-ttl: 300
    cache-max-ttl: 86400
    prefetch: yes
    serve-expired: yes
    num-threads: 2

    # Logging
    verbosity: 1

forward-zone:
    name: "."
    # Cloudflare DoT
    forward-addr: 1.1.1.1@853#cloudflare-dns.com
    forward-addr: 1.0.0.1@853#cloudflare-dns.com
    # Quad9 DoT
    forward-addr: 9.9.9.9@853#dns.quad9.net
    forward-addr: 149.112.112.112@853#dns.quad9.net
    # Google DoT
    forward-addr: 8.8.8.8@853#dns.google
    forward-addr: 8.8.4.4@853#dns.google
```

### Advanced: Running Unbound as Full Recursive Resolver

For maximum privacy, configure Unbound to perform full recursion without forwarding to any upstream provider. This means your resolver queries root servers, TLD servers, and authoritative nameservers directly — all over TLS where supported.

```conf
server:
    interface: 0.0.0.0
    port: 53
    do-ip4: yes
    do-ip6: no

    auto-trust-anchor-file: "/var/lib/unbound/root.key"

    # Use root hints for full recursion
    root-hints: "/var/lib/unbound/root.hints"

    # Harden against DNS attacks
    harden-referral-path: yes
    harden-algo-downgrade: yes
    harden-short-bufsize: yes
    harden-large-queries: yes
    hide-identity: yes
    hide-version: yes

    # Minimal logging for privacy
    verbosity: 0

    # No forward zone — full recursion
```

Unbound's full recursion mode gives you the highest level of DNS independence. You are not trusting any third-party resolver with your queries. The tradeoff is slightly higher resource usage and the need to maintain root hints and trust anchor files.

## Knot Resolver: High-Performance Resolver with Module System

Knot Resolver, developed by CZ.NIC, is a modern DNS resolver built on the Knot DNS library. It supports DoT natively both for inbound client connections and outbound upstream queries. Its distinguishing feature is a Lua-based module system that enables deep customization of DNS processing without recompiling the resolver.

### Key Features

- High-performance recursive resolution with multi-threading
- Native DoT support for both client-facing and upstream connections
- Lua module system for custom DNS logic (filtering, rewriting, logging)
- Built-in DNSSEC validation
- LRU cache with [prometheus](https://prometheus.io/)le size limits
- Prometheus metrics export for monitoring
- Support for DNS-over-HTTPS (DoH) in addition to DoT
- Active development backed by CZ.NIC, operator of the .cz TLD

### Docker Deployment

```yaml
# docker-compose.yml for Knot Resolver
services:
  knot-resolver:
    image: cznic/knot-resolver:latest
    container_name: knot-resolver
    restart: unless-stopped
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "853:853/tcp"       # DoT port for clients
    volumes:
      - ./kresd.conf:/etc/knot-resolver/kresd.conf:ro
      - knot-cache:/var/cache/knot-resolver
      - knot-keys:/etc/knot-resolver/keys
    cap_add:
      - NET_BIND_SERVICE
    security_opt:
      - no-new-privileges:true

volumes:
  knot-cache:
  knot-keys:
```

```lua
-- kresd.conf — Knot Resolver configuration
-- Listen on standard DNS port
net.listen({'0.0.0.0'}, 53, { kind = 'dns' })

-- Enable DNS-over-TLS on port 853
net.listen({'0.0.0.0'}, 853, { kind = 'tls' })
tls.cert('/etc/knot-resolver/certs/server.crt')
tls.key('/etc/knot-resolver/certs/server.key')

-- Cache configuration
cache.size = 500 * MB

-- DNSSEC validation
trust_anchors.config('/etc/knot-resolver/keys/root.keys')

-- Policy: use specific upstream DoT servers
policy.add(policy.TLS('1.1.1.1', 'cloudflare-dns.com'))
policy.add(policy.TLS('9.9.9.9', 'dns.quad9.net'))

-- Enable Prometheus metrics
modules = {
    'policy',
    'hints',
    'stats',
    'predict'
}

-- Custom Lua module: block known malware domains
-- Load an external blocklist
local blocklist = policy.list('/etc/knot-resolver/blocklist.txt')
policy.add(policy.suffix(policy.DENY, blocklist))

-- Verbose logging (set to false in production)
verbose(false)
```

### Generating Self-Signed TLS Certificates for Knot

For inbound DoT connections from clients on your network, you need a TLS certificate. In a homelab environment, a self-signed certificate works if you distribute the CA to client machines:

```bash
# Generate a private key
openssl genrsa -out server.key 2048

# Generate a self-signed certificate
openssl req -new -x509 -sha256 \
  -key server.key \
  -out server.crt \
  -days 365 \
  -subj "/CN=dns.home.arpa" \
  -addext "subjectAltName=DNS:dns.home.arpa,DNS:*.home.arpa"

# Place in the Knot Resolver volume
cp server.key server.crt /path/to/knot-volumes/certs/
```

For production deployments, use certificates from Let's Encrypt or your internal PKI.

## Comparison: Stubby vs Unbound vs Knot Resolver

| Feature | Stubby | Unbound | Knot Resolver |
|---|---|---|---|
| **Type** | Stub/forwarding | Recursive + forwarding | Recursive |
| **DoT client** | Yes | Yes | Yes |
| **DoT server** | No | No (forwarding only) | Yes (native) |
| **DNSSEC validation** | Upstream-dependent | Built-in | Built-in |
| **Full recursion** | No | Yes | Yes |
| **Caching** | Minimal | Advanced with prefetch | LRU with prediction |
| **Custom modules** | No | Python (limited) | Lua (extensive) |
| **RPZ support** | No | Yes | Via Lua modules |
| **DoH support** | No | Yes (since 1.13) | Yes (native) |
| **Prometheus metrics** | No | Via unbound-exporter | Built-in |
| **Memory footprint** | ~5-10 MB | ~50-200 MB | ~100-300 MB |
| **Configuration** | YAML | BIND-style config | Lua scripts |
| **Best for** | Single-machine DoT client | Full self-hosted resolver | Custom DNS logic, high perf |

## Choosing the Right Resolver for Your Setup

The right choice depends on your specific requirements and infrastructure:

**Use Stubby if** you want the simplest path to encrypted DNS on a single machine. Stubby requires almost no maintenance, uses negligible resources, and provides reliable DoT forwarding. It is the best option for desktop systems and small servers where you just want to ensure your DNS queries are encrypted without running a full resolver.

**Use Unbound if** you want a battle-tested, full-featured recursive resolver. Unbound has been the gold standard for open-source DNS resolvers for years. Its combination of DNSSEC validation, RPZ support, split-horizon DNS, and mature caching makes it ideal for homelab gateways, small office networks, and any situation where you want complete DNS independence. The extensive documentation and large user community mean you will find answers to almost any configuration question.

**Use Knot Resolver if** you need high-performance DNS with programmable behavior. The Lua module system is unique among open-source resolvers and enables capabilities like dynamic query rewriting, custom logging, real-time blocklist updates, and integration with external APIs. If you are running DNS at scale or need behavior that goes beyond standard resolver functionality, Knot Resolver is the most flexible option.

## Production Best Practices

Regardless of which resolver you choose, follow these guidelines for a robust self-hosted DoT setup:

### 1. Use Multiple Upstream Providers

Never rely on a single upstream DoT server. Configure at least two providers from different organizations to ensure resilience:

```yaml
# Example: mix of Cloudflare, Quad9, and Google
upstream_recursive_servers:
  - address_data: 1.1.1.1    # Cloudflare primary
    tls_auth_name: "cloudflare-dns.com"
  - address_data: 9.9.9.9    # Quad9 primary
    tls_auth_name: "dns.quad9.net"
  - address_data: 8.8.8.8    # Google primary
    tls_auth_name: "dns.google"
```

### 2. Pin TLS Public Keys

For critical deployments, pin the TLS public keys of your upstream servers. This prevents man-in-the-middle attacks even if a certificate authority is compromised:

```yaml
tls_pubkey_pinset:
  - digest: "sha256"
    value: <base64-encoded-public-key-hash>
```

### 3. Enable DNSSEC Everywhere

DNSSEC prevents DNS spoofing and cache poisoning by cryptographically signing DNS records. All three resolvers support DNSSEC — make sure it is enabled and that trust anchors are kept up to date.

### 4. Monitor Resolver Health

Set up monitoring for your resolver's query volume, cache hit rate, upstream latency, and error rates. Unbound provides `unbound-control stats`, Knot Resolver exports Prometheus metrics, and Stubby can be monitored through system logs and query timing.

### 5. Keep Software Updated

DNS resolvers are security-critical infrastructure. Subscribe to security mailing lists for your chosen resolver and apply updates promptly. CVEs in DNS software are rare but impactful when they occur.

## Summary

Running your own DNS-over-TLS resolver is one of the highest-impact privacy upgrades you can make for your network. Stubby gives you encrypted upstream DNS with almost zero overhead. Unbound provides a complete, independent recursive resolver with years of proven reliability. Knot Resolver offers unmatched programmability for advanced use cases.

All three are free, open-source, and can be deployed with Docker in minutes. The best choice depends on whether you prioritize simplicity (Stubby), completeness (Unbound), or flexibility (Knot Resolver).

## Frequently Asked Questions (FAQ)

### Which one should I choose in 2026?

The best choice depends on your specific requirements:

- **For beginners**: Start with the simplest option that covers your core use case
- **For production**: Choose the solution with the most active community and documentation
- **For teams**: Look for collaboration features and user management
- **For privacy**: Prefer fully open-source, self-hosted options with no telemetry

Refer to the comparison table above for detailed feature breakdowns.

### Can I migrate between these tools?

Most tools support data import/export. Always:
1. Backup your current data
2. Test the migration on a staging environment
3. Check official migration guides in the documentation

### Are there free versions available?

All tools in this guide offer free, open-source editions. Some also provide paid plans with additional features, priority support, or managed hosting.

### How do I get started?

1. Review the comparison table to identify your requirements
2. Visit the official documentation (links provided above)
3. Start with a Docker Compose setup for easy testing
4. Join the community forums for troubleshooting
