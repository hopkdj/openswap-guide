---
title: "cloudflared vs dnsproxy vs dnscrypt-proxy: Best DoH Forwarder 2026"
date: 2026-04-22
tags: ["comparison", "guide", "self-hosted", "privacy", "dns"]
draft: false
description: "Compare the top DNS-over-HTTPS forwarder proxies for self-hosted setups. Complete deployment guides for cloudflared, AdGuard dnsproxy, and dnscrypt-proxy with Docker configurations."
---

DNS-over-HTTPS (DoH) has become the standard way to encrypt DNS queries between your client and upstream resolver. But how do you actually deploy DoH on your self-hosted server? You need a **DoH forwarder** — a lightweight proxy that accepts plain DNS queries from your local network and forwards them to upstream DoH providers over HTTPS.

This guide compares the three best open-source DoH forwarders available in 2026: **cloudflared**, **AdGuard dnsproxy**, and **dnscrypt-proxy**. Each tool takes a different approach to encrypted DNS forwarding, and the right choice depends on whether you need simplicity, multi-protocol support, or maximum configurability.

## Why Self-Host a DoH Forwarder in 2026

Your ISP, network operator, and anyone with access to your network path can see every DNS query you make in plain text. DNS-over-HTTPS wraps those queries inside regular HTTPS traffic, making them indistinguishable from any other encrypted web request.

Running your own DoH forwarder on a local server gives you three things:

**Privacy for your entire network**: Instead of configuring DoH on each device individually, a single forwarder on your server handles encryption for every device on your LAN. Your Pi-hole, smart TV, phone, and laptop all send plain DNS to the forwarder, which encrypts everything upstream.

**Caching and performance**: Local DNS forwarders cache responses, reducing latency for repeated queries and cutting bandwidth to upstream providers. A well-tuned forwarder can serve most queries from cache in under 1ms.

**Filtering and policy control**: Many DoH forwarders include built-in ad blocking, parental controls, and query logging. You decide what gets blocked, what gets logged, and how long data is retained — no third-party service can change those rules.

## Quick Comparison Table

| Feature | cloudflared | AdGuard dnsproxy | dnscrypt-proxy |
|---|---|---|---|
| **Stars** | 13,912 | 3,071 | 13,222 |
| **Language** | Go | Go | Go |
| **Last Updated** | 2026-04-15 | 2026-04-21 | 2026-04-21 |
| **DoH Support** | Yes | Yes | Yes |
| **DoT Support** | No | Yes | Yes |
| **DoQ Support** | No | Yes | No |
| **DNSCrypt Support** | No | Yes | Yes |
| **DNS Filtering** | No (basic) | Yes (adlist) | Yes (blocklists) |
| **Caching** | Yes (limited) | Yes | Yes |
| **Docker Image** | Official | Official | Community |
| **Best For** | Cloudflare users | Multi-protocol setups | Maximum flexibility |

## cloudflared: Cloudflare's Official DoH Forwarder

[cloudflared](https://github.com/cloudflare/cloudflared) is Cloudflare's official DNS-over-HTTPS proxy. Originally built as the client for Cloudflare Tunnel (formerly Argo Tunnel), it includes a built-in DNS proxy mode that forwards queries to Cloudflare's 1.1.1.1 DoH resolver.

### Key Features

- **Zero-config DoH**: Run `cloudflared proxy-dns` and it immediately starts forwarding to 1.1.1.1 over HTTPS
- **Built-in caching**: Responses are cached locally, reducing repeat query latency
- **HTTP/3 (QUIC) support**: Modern transport layer for faster DoH connections
- **Multi-upstream failover**: Can be configured with multiple DoH upstreams for redundancy

### When to Use cloudflared

Choose cloudflared if you want the simplest possible DoH setup and are comfortable using Cloudflare's 1.1.1.1 as your upstream resolver. It's ideal for home labs and small networks where ease of deployment matters most.

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  cloudflared-dns:
    image: cloudflare/cloudflared:latest
    container_name: cloudflared-dns
    restart: unless-stopped
    command: proxy-dns
    ports:
      - "53:53/udp"
      - "53:53/tcp"
    environment:
      - TUNNEL_DNS_UPSTREAM=https://1.1.1.1/dns-query,https://1.0.0.1/dns-query
      - TUNNEL_DNS_PORT=53
      - TUNNEL_DNS_ADDRESS=0.0.0.0
```

This configuration starts a DoH forwarder listening on port 53, forwarding all queries to Cloudflare's dual DoH endpoints (1.1.1.1 and 1.0.0.1) for redundancy.

### Bare Metal Installation

For Linux systems without Docker:

```bash
# Debian/Ubuntu
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt update && sudo apt install cloudflared

# Verify DoH proxy works
cloudflared proxy-dns --address 0.0.0.0 --port 53
```

### Configuration Options

cloudflared's DNS proxy supports several flags:

```bash
cloudflared proxy-dns \
  --address 0.0.0.0 \
  --port 5300 \
  --upstream https://1.1.1.1/dns-query \
  --upstream https://dns.google/dns-query \
  --metrics 127.0.0.1:9090
```

The `--metrics` flag exposes Prometheus-compatible metrics for monitoring query counts, cache hit rates, and upstream latency.

## AdGuard dnsproxy: Multi-Protocol DNS Forwarder

[AdGuard dnsproxy](https://github.com/AdguardTeam/dnsproxy) is a lightweight DNS proxy that supports **every** encrypted DNS protocol: DoH, DoT (DNS-over-TLS), DoQ (DNS-over-QUIC), and DNSCrypt. It also includes a built-in filtering engine powered by AdGuard's ad-blocking lists.

### Key Features

- **Multi-protocol support**: Accept and forward DoH, DoT, DoQ, and DNSCrypt in a single binary
- **Built-in ad blocking**: Uses AdGuard DNS filter lists to block ads, trackers, and malware domains
- **EDNS Client Subnet (ECS)**: Preserves geolocation hints for CDN optimization
- **Bootstrap DNS**: Resolves DoH/DoT upstream hostnames even when the system resolver is down
- **Per-client configuration**: Different filtering rules for different devices on your network

### When to Use dnsproxy

Choose dnsproxy if you need multi-protocol support (especially DoQ) or want built-in ad blocking without running a separate Pi-hole or AdGuard Home instance. It's the Swiss Army knife of DNS forwarders.

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  dnsproxy:
    image: adguard/dnsproxy:latest
    container_name: dnsproxy
    restart: unless-stopped
    ports:
      - "53:53/udp"
      - "53:53/tcp"
      - "5300:5300/tcp"
      - "5300:5300/udp"
      - "784:784/udp"
      - "8853:8853/udp"
    command: >
      --udp=0.0.0.0:53
      --tcp=0.0.0.0:53
      --tls=0.0.0.0:5300
      --quic=0.0.0.0:784
      --https=0.0.0.0:5300
      --upstream=https://1.1.1.1/dns-query
      --upstream=https://dns.google/dns-query
      --upstream=https://dns.adguard.com/dns-query
      --bootstrap=https://1.1.1.1/dns-query
      --cache-size=4096
      --cache-optimistic
```

This configuration accepts DNS on all four protocols:
- Plain DNS on port 53 (UDP/TCP)
- DoT on port 5300
- DoH on port 5300
- DoQ on port 784

### Blocking Ads and Trackers

dnsproxy can load filtering lists directly:

```bash
dnsproxy \
  --udp=0.0.0.0:53 \
  --upstream=https://1.1.1.1/dns-query \
  --filter-file=/filters/adservers.txt \
  --filter-file=/filters/trackers.txt \
  --blocked-response=0.0.0.0
```

The `--blocked-response=0.0.0.0` sends zero IP addresses for blocked domains, effectively dropping the query.

### Upstream Selection Strategy

dnsproxy supports intelligent upstream selection:

```bash
# Fastest upstream: queries all upstreams in parallel, returns the first response
--upstream-mode=fastest_addr

# Load balancing: distributes queries across upstreams
--upstream-mode=load_balance

# Parallel: send to all, use fastest (default)
--upstream-mode=parallel
```

## dnscrypt-proxy: Maximum Flexibility

[dnscrypt-proxy](https://github.com/DNSCrypt/dnscrypt-proxy) is the most configurable DNS forwarder on this list. Despite its name, it supports far more than just DNSCrypt — it handles DoH, DoT, and plain DNS with an extensive feature set including query logging, cloaking rules, and load balancing across dozens of public resolvers.

### Key Features

- **Resolver auto-discovery**: Ships with a curated list of 100+ public DNS resolvers, automatically tested for speed and reliability
- **Query cloaking**: Map specific domains to specific upstream resolvers (e.g., send Netflix queries to Google DNS)
- **Anonymized DNSCrypt**: Route queries through relay nodes to hide your IP from the resolver
- **Blocklist management**: Load multiple blocklists with automatic updates and custom allow/deny rules
- **Query logging**: Detailed logs in CSV or JSON format, with optional rotation

### When to Use dnscrypt-proxy

Choose dnscrypt-proxy if you need fine-grained control over DNS routing, want to use multiple public resolvers with automatic failover, or need advanced features like cloaking and anonymized DNS. It has the steepest learning curve but the highest ceiling.

### Docker Compose Deployment

dnscrypt-proxy runs best with a bind-mounted configuration file:

```yaml
version: "3.8"

services:
  dnscrypt-proxy:
    image: ghcr.io/dnscrypt/dnscrypt-proxy:latest
    container_name: dnscrypt-proxy
    restart: unless-stopped
    volumes:
      - ./dnscrypt-proxy.toml:/etc/dnscrypt-proxy/dnscrypt-proxy.toml:ro
      - ./cache:/etc/dnscrypt-proxy/cache
      - ./logs:/etc/dnscrypt-proxy/logs
    ports:
      - "53:53/udp"
      - "53:53/tcp"
    network_mode: host
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
```

### Configuration (dnscrypt-proxy.toml)

The TOML configuration file is where dnscrypt-proxy gets its power:

```toml
listen_addresses = ['0.0.0.0:53']

# Use multiple upstream resolvers
server_names = ['cloudflare', 'google', 'quad9-doh-ip4-filter-pri']

# Cloaking rules
[query_meta]
  cloak_ttl = true

# Blocklists
sources = [
  {name = 'example-oisd', urls = ['https://big.oisd.nl/'], format = 'dns'],
  {name = 'example-stevenblack', urls = ['https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts'], format = 'hosts'},
]

# Query logging
[query_log]
  file = '/etc/dnscrypt-proxy/logs/query.log'
  format = 'tsv'

# Cache settings
[local_cache]
  enabled = true
  size = 512
  max_ttl = 86400
  min_ttl = 300
  neg_ttl = 60
  stale_ttl = 60
  cache_responses = true
```

### Automatic Blocklist Updates

dnscrypt-proxy can refresh its blocklists on a schedule:

```bash
# Set refresh interval in the TOML config:
refresh_delay = '72h'

# Blocklists are downloaded and cached automatically.
# To force a manual refresh:
docker exec dnscrypt-proxy dnscrypt-proxy -service install
docker exec dnscrypt-proxy dnscrypt-proxy -service restart
```

### Performance Tuning

For high-traffic setups, tune these settings:

```toml
# Maximum concurrent DNS queries
max_concurrent_queries = 200

# DNSCrypt-specific settings
dnscrypt_ephemeral_keys = true
skip_incompatible = true

# Forwarding rules for specific domains
[static]
  [static.'example-domain']
    stamp = 'sdns://...'
```

## Head-to-Head: Which Should You Choose?

| Scenario | Recommended Tool | Why |
|---|---|---|
| Quick DoH setup on a home server | **cloudflared** | One command, zero config, just works |
| Multi-protocol DNS (DoH + DoT + DoQ) | **dnsproxy** | Single binary handles all encrypted DNS protocols |
| Ad blocking + DNS forwarding combined | **dnsproxy** | Built-in filter engine, no separate Pi-hole needed |
| Fine-grained DNS routing and cloaking | **dnscrypt-proxy** | Per-domain upstream selection, cloaking rules |
| Maximum resolver choice + auto-discovery | **dnscrypt-proxy** | 100+ public resolvers, automatic speed testing |
| Container-first deployment | **cloudflared** | Official Docker image, minimal config |
| Prometheus metrics and monitoring | **cloudflared** | Built-in `/metrics` endpoint |

## Monitoring Your DoH Forwarder

Regardless of which tool you choose, monitoring DNS performance is essential. All three forwarders support different monitoring approaches:

**cloudflared**: Expose metrics on port 9090:

```yaml
command: proxy-dns --metrics 0.0.0.0:9090
```

Scrape with Prometheus:

```yaml
scrape_configs:
  - job_name: cloudflared
    static_configs:
      - targets: ['localhost:9090']
```

**dnsproxy**: Enable verbose logging for analysis:

```bash
--verbose
--log-file=/var/log/dnsproxy.log
```

**dnscrypt-proxy**: Query logs in TSV format:

```toml
[query_log]
  file = '/etc/dnscrypt-proxy/logs/query.log'
  format = 'tsv'
```

Parse with standard tools:

```bash
# Top queried domains
awk -F'\t' '{print $4}' query.log | sort | uniq -c | sort -rn | head -20

# Query latency distribution
awk -F'\t' '{print $6}' query.log | sort -n | tail -5
```

For related reading, see our [complete DNS privacy guide](../self-hosted-dns-privacy-doh-dot-dnscrypt-complete-guide-2026/) for a deeper dive into the protocols these tools support, and the [Pi-hole vs AdGuard Home comparison](../adguard-home-vs-technitium-dns-pihole/) for DNS-level ad blocking alternatives. If you're setting up a full privacy stack, also check our [comprehensive privacy stack guide](../privacy-stack-guide/).

## FAQ

### What is a DNS-over-HTTPS (DoH) forwarder?

A DoH forwarder is a lightweight proxy service that accepts standard DNS queries from your local network and re-encodes them as HTTPS requests to upstream DNS resolvers. This encrypts your DNS traffic, preventing your ISP or network operator from seeing which domains you query.

### Do I need a DoH forwarder if I already use Pi-hole or AdGuard Home?

Pi-hole and AdGuard Home primarily focus on DNS filtering and ad blocking at the network level. While AdGuard Home supports DoH/DoT upstream natively, a dedicated DoH forwarder like dnsproxy or dnscrypt-proxy gives you more protocol options (DoQ, DNSCrypt), better caching, and finer control over upstream selection. You can also run a DoH forwarder behind Pi-hole for the best of both worlds.

### Can I use multiple DoH upstreams for redundancy?

Yes. All three tools support multiple upstream resolvers. cloudflared uses the `--upstream` flag multiple times, dnsproxy supports `--upstream-mode=fastest_addr` for automatic failover, and dnscrypt-proxy maintains a list of server names and automatically switches when one becomes unavailable.

### Which DoH provider should I use as my upstream?

Popular choices include Cloudflare (1.1.1.1), Google (dns.google), Quad9 (9.9.9.9), and AdGuard DNS (dns.adguard.com). Each has different privacy policies and filtering options. For maximum privacy, consider using a no-log provider like Quad9 or running your own recursive resolver.

### How do I verify my DoH forwarder is actually encrypting queries?

Use a packet capture tool to verify:

```bash
sudo tcpdump -i any port 53
```

If your local devices send plain DNS to port 53 on the forwarder, you should see traffic there. Then check the upstream connection — DoH traffic goes to port 443 as regular HTTPS, which tcpdump will show as encrypted TLS traffic. Tools like `dig @127.0.0.1 example.com` test your local forwarder, while `curl -v https://1.1.1.1/dns-query?dns=...` tests the upstream directly.

### Does running a DoH forwarder add significant latency?

Minimal. A well-configured forwarder with caching enabled typically adds 1-5ms of latency on cache misses and sub-millisecond on cache hits. The encryption overhead of HTTPS is negligible on modern hardware. If your forwarder is on the same machine as your clients, latency is essentially zero.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "cloudflared vs dnsproxy vs dnscrypt-proxy: Best DoH Forwarder 2026",
  "description": "Compare the top DNS-over-HTTPS forwarder proxies for self-hosted setups. Complete deployment guides for cloudflared, AdGuard dnsproxy, and dnscrypt-proxy with Docker configurations.",
  "datePublished": "2026-04-22",
  "dateModified": "2026-04-22",
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
