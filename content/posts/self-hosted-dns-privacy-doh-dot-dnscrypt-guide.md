---
title: "Complete Guide to Self-Hosted DNS Privacy (DoH/DoT/DNSCrypt) 2026"
date: 2026-04-13
tags: ["comparison", "guide", "self-hosted", "privacy", "dns"]
draft: false
description: "Encrypt your DNS traffic with self-hosted DNS-over-HTTPS, DNS-over-TLS, and DNSCrypt. Complete setup guides for stubby, cloudflared, and dnscrypt-proxy with Docker."
---

## Why Encrypt Your DNS Traffic?

Every time you visit a website, your device performs a DNS lookup to translate the domain name into an IP address. By default, these lookups travel in **plain text** — anyone on your network (your ISP, a coffee shop Wi-Fi operator, or a malicious actor) can see every site you visit, block access to specific domains, or even redirect you to fraudulent sites through DNS spoofing.

Encrypting DNS traffic solves all three problems:

- **Privacy**: Your ISP and network observers can no longer see which domains you're looking up. They only see encrypted connections to your DNS resolver.
- **Integrity**: DNS-over-HTTPS (DoH), DNS-over-TLS (DoT), and DNSCrypt use cryptographic verification to ensure responses haven't been tampered with in transit.
- **Censorship resistance**: Encrypted DNS bypasses many forms of DNS-based blocking and filtering, giving you control over which resolver you trust.

Self-hosting your own encrypted DNS proxy gives you the best of both worlds: you pick the upstream resolvers you trust, you control the caching and filtering behavior, and every device on your network benefits from encrypted lookups without needing individual configuration.

## Three Protocols, Three Tools

Three protocols dominate encrypted DNS, each with a leading open-source implementation:

| Protocol | How It Works | Leading Tool | Port |
|----------|-------------|-------------|------|
| **DNS-over-HTTPS (DoH)** | DNS queries wrapped in HTTPS requests | `cloudflared` | 443 |
| **DNS-over-TLS (DoT)** | DNS queries over a dedicated TLS connection | `stubby` | 853 |
| **DNSCrypt v2** | DNS queries encrypted with NaCl cryptography | `dnscrypt-proxy` | 443 |

### DNS-over-HTTPS (DoH)

DoH sends DNS queries as standard HTTPS requests to a resolver endpoint. The biggest advantage is that DoH traffic is **indistinguishable from regular HTTPS** — firewalls and deep packet inspection systems cannot tell it apart from browsing a website. Cloudflare, Google, and Quad9 all operate public DoH resolvers.

### DNS-over-TLS (DoT)

DoT uses a dedicated port (853) with TLS encryption. It's simpler to implement than DoH since it doesn't need to speak HTTP, but the dedicated port makes it easy for network administrators to block. Most modern operating systems support DoT natively.

### DNSCrypt v2

DNSCrypt is a protocol designed specifically for DNS encryption. Unlike DoH and DoT, DNSCrypt provides **authenticated encryption** — you cryptographically verify the identity of the resolver, not just the transport. The `dnscrypt-proxy` tool supports multiple resolvers, automatic fallback, and built-in filtering.

## Setting Up cloudflared (DoH)

Cloudflared is Cloudflare's official DoH proxy. It listens on a local port, forwards queries to Cloudflare's DoH endpoint over HTTPS, and caches responses.

### [docker](https://www.docker.com/) Compose Setup

Create a directory for your DoH proxy:

```bash
mkdir -p ~/dns-proxy/cloudflared
cd ~/dns-proxy/cloudflared
```

Create `docker-compose.yml`:

```yaml
version: "3.8"

services:
  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: cloudflared-doh
    restart: unless-stopped
    command: proxy-dns
    ports:
      - "5053:5053/udp"
      - "5053:5053/tcp"
    environment:
      - TUNNEL_DNS_UPSTREAM=https://cloudflare-dns.com/dns-query,https://dns.quad9.net/dns-query
      - TUNNEL_DNS_PORT=5053
      - TUNNEL_DNS_METRICS_PORT=49312
    logging:
      driver: json-file
      options:
        max-size: "1m"
        max-file: "3"
```

Start the service:

```bash
docker compose up -d
```

Verify it's working:

```bash
dig @127.0.0.1 -p 5053 example.com +short
```

You should see an IP address returned. To confirm encryption is working, check the metrics endpoint:

```bash
curl -s http://127.0.0.1:49312/metrics | grep cloudflared_dns_upstream
```

### Multiple Upstream Resolvers

For resilience, configure multiple upstream DoH providers. cloudflared will query all configured resolvers and use the fastest response:

```yaml
environment:
  - TUNNEL_DNS_UPSTREAM=https://cloudflare-dns.com/dns-query,https://dns.quad9.net/dns-query,https://dns.google/resolve,https://doh.dns.sb/dns-query
```

### Making It System-Wide

Configure your system to use the local proxy as its DNS resolver. Edit `/etc/systemd/resolved.conf`:

```ini
[Resolve]
DNS=127.0.0.1
Domains=~.
```

Then restart the resolver:

```bash
systemctl restart systemd-resolved
```

## Setting Up stubby (DoT)

Stubby is developed by the GetDNS project and is the reference implementation for DNS-over-TLS. It's lightweight, supports strict TLS verification, and can round-robin across multiple upstream resolvers.

### Docker Compose Setup

Create the configuration directory:

```bash
mkdir -p ~/dns-proxy/stubby
cd ~/dns-proxy/stubby
```

Create `stubby.yml` — the main configuration file:

```yaml
resolution_type: GETDNS_RESOLUTION_STUB
round_robin_upstreams: 1
appdata_dir: "/var/cache/stubby"
tls_authentication: GETDNS_AUTHENTICATION_REQUIRED
tls_query_padding_blocksize: 128
edns_client_subnet:
  opaque_bit: 0
  address: 0.0.0.0

upstream_recursive_servers:
  # Cloudflare DoT
  - address_data: 1.1.1.1
    tls_auth_name: "cloudflare-dns.com"
  - address_data: 1.0.0.1
    tls_auth_name: "cloudflare-dns.com"

  # Quad9 DoT
  - address_data: 9.9.9.9
    tls_auth_name: "dns.quad9.net"
  - address_data: 149.112.112.112
    tls_auth_name: "dns.quad9.net"

  # Google DoT
  - address_data: 8.8.8.8
    tls_auth_name: "dns.google"
  - address_data: 8.8.4.4
    tls_auth_name: "dns.google"

listen_addresses:
  - 127.0.0.1@5300
  - 0::1@5300
```

Key configuration notes:

- `round_robin_upstreams: 1` distributes queries evenly across resolvers for load balancing
- `tls_query_padding_blocksize: 128` pads queries to obscure their exact size, adding a layer of privacy
- `tls_auth_name` ensures the TLS certificate matches the expected hostname, preventing man-in-the-middle attacks

Create `docker-compose.yml`:

```yaml
version: "3.8"

services:
  stubby:
    image: getdnsapi/stubby:latest
    container_name: stubby-dot
    restart: unless-stopped
    volumes:
      - ./stubby.yml:/etc/stubby/stubby.yml:ro
    ports:
      - "5300:5300/udp"
      - "5300:5300/tcp"
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    security_opt:
      - no-new-privileges:true
    logging:
      driver: json-file
      options:
        max-size: "1m"
        max-file: "3"
```

Start and test:

```bash
docker compose up -d
dig @127.0.0.1 -p 5300 example.com +short
```

### Verifying TLS Is Active

To confirm queries are actually encrypted, use `stubby`'s built-in status check:

```bash
# Get container ID
CONTAINER=$(docker ps -q -f name=stubby-dot)

# Check stubby logs for TLS connections
docker logs $CONTAINER 2>&1 | grep -i "tls" | tail -5
```

You should see lines confirming TLS handshakes with your configured upstream servers.

## Setting Up dnscrypt-proxy

`dnscrypt-proxy` is the most feature-rich option. It supports DNSCrypt v2, DoH, and DoT simultaneously, with built-in caching, load balancing, filtering, and cloaking.

### Docker Compose Setup

```bash
mkdir -p ~/dns-proxy/dnscrypt
cd ~/dns-proxy/dnscrypt
```

Create `dnscrypt-proxy.toml`:

```toml
listen_addresses = ['0.0.0.0:5400']

# Use multiple strategies for resilience
server_names = ['cloudflare', 'quad9', 'google']

# Minimum number of servers required
require_dnssec = true
require_nolog = true
require_nofilter = true

# Performance
cache = true
cache_size = 4096
cache_min_ttl = 60
cache_max_ttl = 86400
cache_neg_min_ttl = 60
cache_neg_max_ttl = 600

# Privacy: hide client subnet from upstream
dnscrypt_ephemeral_keys = true
tls_disable_session_tickets = true
ignore_system_dns = true

# Query logging (optional, set to false for max privacy)
[query_log]
  file = '/var/log/dnscrypt-proxy/query.log'

[nx_log]
  file = '/var/log/dnscrypt-proxy/nx.log'

[log]
  level = 2
  file = '/var/log/dnscrypt-proxy/dnscrypt-proxy.log'
```

Create `docker-compose.yml`:

```yaml
version: "3.8"

services:
  dnscrypt-proxy:
    image: klutchell/dnscrypt-proxy:latest
    container_name: dnscrypt-proxy
    restart: unless-stopped
    volumes:
      - ./dnscrypt-proxy.toml:/etc/dnscrypt-proxy/dnscrypt-proxy.toml:ro
    ports:
      - "5400:5400/udp"
      - "5400:5400/tcp"
    logging:
      driver: json-file
      options:
        max-size: "1m"
        max-file: "3"
```

Start and test:

```bash
docker compose up -d
dig @127.0.0.1 -p 5400 example.com +short
```

### Using the Built-in Blocklist

One of dnscrypt-proxy's strongest features is its built-in ad and malware blocking. Add this to your configuration:

```toml
[blocked_names]
  blocked_names_file = '/etc/dnscrypt-proxy/blocked-names.txt'
  log_file = '/var/log/dnscrypt-proxy/blocked.log'

[sources]
  [sources.'public-resolvers']
    urls = ['https://download.dnscrypt.info/resolvers-list/v2/public-resolvers.md']
    cache_file = '/etc/dnscrypt-proxy/public-resolvers.md'
    minisign_key = 'RWQf6LRCGA9i53mlYecO4IzT51TGPpvWucNSCh1CBM0QTaL7ikOB'
    refresh_delay = 72

  [sources.'relays']
    urls = ['https://download.dnscrypt.info/resolvers-list/v2/relays.md']
    cache_file = '/etc/dnscrypt-proxy/relays.md'
    minisign_key = 'RWQf6LRCGA9i53mlYecO4IzT51TGPpvWucNSCh1CBM0QTaL7ikOB'

  [sources.'oisd-basic']
    urls = ['https://big.oisd.nl/domainswild']
    format = 'domains'
    cache_file = '/etc/dnscrypt-proxy/oisd-basic.txt'
    refresh_delay = 72
    prefix = 'ads-'

  [sources.'malware-domain-list']
  [gitlab](https://about.gitlab.com/) = ['https://malware.gitlab.io/-/raw/main/output/domains-md.txt']
    format = 'domains'
    cache_file = '/etc/dnscrypt-proxy/malware.txt'
    refresh_delay = 72
    prefix = 'malware-'
```

This automatically downloads and maintains blocklists from OISD (one of the best community-maintained blocklists) and a malware domain list, refreshing every 72 hours.

## Comparison: Which Tool Should You Use?

| Feature | cloudflared | stubby | dnscrypt-proxy |
|---------|------------|--------|----------------|
| **Protocols** | DoH only | DoT only | DNSCrypt v2, DoH, DoT |
| **Ease of Setup** | Easiest | Easy | Moderate |
| **Multiple Upstreams** | Yes (fastest wins) | Yes (round-robin) | Yes (LB + fallback) |
| **Built-in Caching** | Basic | No (relies on system) | Advanced (TTL control) |
| **Ad Blocking** | No | No | Yes (blocklist support) |
| **Cloaking** | No | No | Yes |
| **IPv6** | Yes | Yes | Yes |
| **Query Logging** | Metrics only | Logs | Full query/NX logs |
| **Binary Size** | ~30 MB | ~2 MB | ~8 MB |
| **Memory Usage** | ~40 MB | ~5 MB | ~15 MB |
| **Best For** | Quick DoH setup | Minimal DoT | Full-featured proxy |

### Quick Decision Guide

- **Choose cloudflared** if you want the simplest possible DoH setup and already trust Cloudflare's infrastructure. It's essentially a "set and forget" solution.

- **Choose stubby** if you want a minimal, purpose-built DoT proxy with the smallest footprint. It's ideal for resource-constrained environments like a Raspberry Pi running alongside other services.

- **Choose dnscrypt-proxy** if you want the most features — protocol flexibility, caching, ad blocking, cloaking, and detailed logging. It's the Swiss Army knife of encrypted DNS.

## Integrating with Pi-hole or [adguard home](https://adguard.com/en/adguard-home/overview.html)

The most powerful setup combines encrypted DNS upstream with a local DNS filter. Here's how to chain them together.

### With Pi-hole

Edit `/etc/pihole/setupVars.conf` and set the upstream DNS to your encrypted proxy:

```bash
PIHOLE_DNS_1=127.0.0.1#5400
PIHOLE_DNS_2=127.0.0.1#5053
```

Then restart Pi-hole:

```bash
pihole restartdns
```

In this chain: Pi-hole handles ad blocking and local DNS → forwards to dnscrypt-proxy/cloudflared → which encrypts the query to the upstream resolver.

### With AdGuard Home

In the AdGuard Home web interface, go to **Settings → DNS Settings** and set your upstream servers:

```
127.0.0.1:5400
127.0.0.1:5053
```

Or edit `AdGuardHome.yaml` directly:

```yaml
dns:
  upstream_dns:
    - 127.0.0.1:5400
    - 127.0.0.1:5053
  bootstrap_dns:
    - 1.1.1.1
    - 9.9.9.9
```

This gives you the full stack: client → AdGuard Home (filtering) → encrypted proxy (DoH/DoT/DNSCrypt) → upstream resolver.

### With a Single Docker Compose

You can run the entire stack in one compose file:

```yaml
version: "3.8"

services:
  adguard-home:
    image: adguard/adguardhome:latest
    container_name: adguard-home
    restart: unless-stopped
    ports:
      - "53:53/udp"
      - "53:53/tcp"
      - "3000:3000/tcp"
    volumes:
      - ./adguard/work:/opt/adguardhome/work
      - ./adguard/conf:/opt/adguardhome/conf
    depends_on:
      - dnscrypt

  dnscrypt-proxy:
    image: klutchell/dnscrypt-proxy:latest
    container_name: dnscrypt-proxy
    restart: unless-stopped
    volumes:
      - ./dnscrypt/dnscrypt-proxy.toml:/etc/dnscrypt-proxy/dnscrypt-proxy.toml:ro
    expose:
      - "5400/udp"
      - "5400/tcp"

networks:
  default:
    driver: bridge
```

Configure AdGuard Home's upstream to `dnscrypt-proxy:5400` using Docker's internal DNS resolution.

## Choosing Trustworthy Upstream Resolvers

Encryption protects your queries in transit, but the upstream resolver can still see them. Choose resolvers based on their privacy policies:

| Resolver | Protocol | No-Log Policy | Location |
|----------|----------|---------------|----------|
| **Cloudflare (1.1.1.1)** | DoH, DoT | Yes (audited by KPMG) | Global |
| **Quad9 (9.9.9.9)** | DoH, DoT, DNSCrypt | Yes | Switzerland |
| **Google (8.8.8.8)** | DoH, DoT | Limited logging | Global |
| **DNS.SB** | DoH, DoT | Yes | Iceland |
| **NextDNS** | DoH, DoT | Configurable | Global (customizable) |
| **Mullvad DNS** | DoH, DoT | Yes | Sweden |

For maximum privacy, use a combination of Quad9 (Swiss jurisdiction, strong privacy) and Mullvad (no-account DNS with no persistent logs).

## Common Pitfalls and Troubleshooting

### DNS Resolution Fails After Switching

If your system can't resolve domains after pointing to the local proxy, check:

```bash
# Verify the proxy is running
docker ps | grep -E "cloudflared|stubby|dnscrypt"

# Test direct resolution
dig @127.0.0.1 -p 5400 example.com

# Check if systemd-resolved is conflicting
resolvectl status
```

A common issue is systemd-resolved still pointing to the old DNS servers. Fix it with:

```bash
sudo ln -sf /run/systemd/resolve/resolv.conf /etc/resolv.conf
```

### Slow Resolution Times

If queries feel slow, the issue is usually one of:

1. **No local caching** — stubby has no built-in cache. Pair it with `unbound` or switch to dnscrypt-proxy which caches by default.
2. **Geographic distance to upstream** — pick resolvers with points of presence near you. Use `dig` to measure latency:
   ```bash
   dig @1.1.1.1 example.com | grep "Query time"
   dig @9.9.9.9 example.com | grep "Query time"
   ```
3. **IPv6 fallback delays** — if IPv6 is configured but not working, disable it in your proxy config.

### Docker Network Conflicts

If your containers can't reach upstream resolvers, ensure outbound DNS isn't blocked by Docker's default bridge:

```yaml
# Add to your compose file
networks:
  default:
    driver: bridge
    driver_opts:
      com.docker.network.bridge.enable_ip_masquerade: "true"
```

## Conclusion

Encrypting your DNS traffic is one of the highest-impact privacy improvements you can make with minimal effort. The three tools covered here — cloudflared, stubby, and dnscrypt-proxy — each serve different needs, from the simplest possible setup to a fully-featured encrypted DNS proxy with caching and filtering.

The recommended path for most homelab users is **dnscrypt-proxy paired with Pi-hole or AdGuard Home**: the filter handles ad blocking and local DNS, while dnscrypt-proxy encrypts all upstream queries and adds an additional layer of blocklist protection on top. Run both in Docker, point your router's DNS to the filter, and every device on your network gets encrypted DNS without any client-side configuration.

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
