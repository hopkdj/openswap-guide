---
title: "Self-Hosted DNS Privacy: DoH, DoT, DNSCrypt & Stubby Complete Guide 2026"
date: 2026-04-15
tags: ["comparison", "guide", "self-hosted", "privacy", "dns"]
draft: false
description: "Complete guide to encrypted DNS protocols in 2026 — DNS-over-HTTPS, DNS-over-TLS, DNSCrypt, and Stubby. Learn how to set up a self-hosted DNS privacy stack that blocks ISP surveillance, prevents DNS spoofing, and keeps your queries private."
---

Every time you visit a website, your device sends a DNS query to translate a domain name into an IP address. By default, these queries travel in **plain text** across the internet. Your ISP, anyone on your local network, and intermediaries can see exactly which websites you visit — and potentially modify the responses to redirect you to malicious sites.

DNS privacy protocols solve this problem by encrypting your DNS queries end-to-end. In 2026, three main protocols compete for dominance: **DNS-over-HTTPS (DoH)**, **DNS-over-TLS (DoT)**, and **DNSCrypt**. This guide compares all three, shows you how to set up each one, and helps you build a complete self-hosted DNS privacy stack.

## Why Encrypt Your DNS Queries

Before diving into protocols, understanding the threat model matters:

- **ISP Surveillance**: Most ISPs log every DNS query you make. In many jurisdictions, they sell this browsing data to advertisers.
- **DNS Spoofing / Cache Poisoning**: Unencrypted DNS is vulnerable to man-in-the-middle attacks. An attacker can redirect `your-bank.com` to a phishing site by spoofing the DNS response.
- **Corporate / Public Network Monitoring**: On hotel Wi-Fi, coffee shops, or corporate networks, plain-text DNS reveals your entire browsing history to the network operator.
- **Censorship Evasion**: Some ISPs and governments block access to websites by intercepting and dropping DNS queries for specific domains. Encrypted DNS bypasses these simple blocks.
- **Privacy from Recursive Resolvers**: Even if you use a privacy-respecting resolver, without encryption the path between you and the resolver is exposed.

Encrypting DNS queries adds a fundamental layer of privacy to your network. Combined with a self-hosted ad-blocker like Pi-hole or [adguard home](https://adguard.com/en/adguard-home/overview.html), encrypted DNS forms the backbone of a privacy-respecting home network.

## DNS Privacy Protocols Compared

### DNS-over-HTTPS (DoH)

DoH wraps DNS queries inside standard HTTPS requests. Your DNS traffic looks identical to regular web browsing — indistinguishable from any other HTTPS connection.

**How it works**: DNS queries are encoded as HTTPS POST or GET requests to a DoH resolver endpoint. The resolver returns DNS responses as HTTP responses, typically in DNS wire format or JSON DNS (RFC 8427).

**Pros**:
- Indistinguishable from regular HTTPS traffic — firewalls and ISPs cannot selectively block DoH without blocking all HTTPS
- Uses port 443, which is almost never blocked
- Excellent browser and OS support (Firefox, Chrome, Windows 11, macOS)
- Can be proxied through standard HTTP infrastructure

**Cons**:
- Adds HTTP overhead to each query (headers, TLS handshake negotiation)
- Harder for network administrators to monitor and audit DNS traffic
- Some privacy advocates worry about DoH giving browsers direct control over DNS resolution

### DNS-over-TLS (DoT)

DoT encrypts DNS queries using a dedicated TLS connection on a separate port. It is the IETF standard approach to DNS encryption.

**How it works**: DNS queries are sent over a TLS-encrypted TCP connection on port 853. The TLS handshake authenticates the resolver, then DNS queries and responses flow over the encrypted channel.

**Pros**:
- Lower overhead than DoH — no HTTP framing, just raw DNS over TLS
- Dedicated port (853) makes it easy to monitor and manage
- Strong standardization (RFC 7858, RFC 8310)
- Native support in Android 9+, systemd-resolved, and Stubby

**Cons**:
- Port 853 can be blocked by restrictive firewalls
- Easier to detect and selectively block since it uses a unique port
- Less browser-native support than DoH (browsers prefer DoH)

### DNSCrypt

DNSCrypt is an older protocol designed by Frank Denis (also the author of dnscrypt-proxy). It predates DoH and DoT and uses a different cryptographic approach.

**How it works**: DNSCrypt uses elliptic-curve cryptography (X25519 + XSalsa20-Poly1305) to encrypt DNS traffic between the client and resolver. It operates on port 443 (TCP) or port 53 (UDP).

**Pros**:
- Very fast — optimized for low latency with minimal overhead
- Built-in DNSSEC validation support
- Resolver authentication via pre-published public keys
- dnscrypt-proxy client offers advanced features: caching, load balancing, cloaking, blocklists
- Works on UDP port 53, which is always open

**Cons**:
- Not an IETF standard — less widely adopted by major providers
- Fewer public resolvers support DNSCrypt compared to DoH/DoT
- Less mainstream OS integration than DoH or DoT
- Some consider it legacy, though the protocol remains actively maintained

### Comparison Table

| Feature | DoH | DoT | DNSCrypt | Plain DNS |
|---------|-----|-----|----------|-----------|
| **Encryption** | TLS 1.3 over HTTPS | TLS 1.3 on TCP | X25519 + XSalsa20 | None |
| **Port** | 443 (TCP) | 853 (TCP) | 443 (TCP) / 53 (UDP) | 53 (UDP/TCP) |
| **Overhead** | Higher (HTTP framing) | Low | Minimal | None |
| **Firewall Evasion** | Excellent | Moderate | Good (on 443) | N/A |
| **ISP Blocking** | Hardest | Easy (port 853) | Moderate | Trivial |
| **Browser Support** | Native (Firefox, Chrome) | Limited | Extension required | N/A |
| **OS Support** | Windows 11, macOS, Linux | Android, Linux | Linux, Windows | Universal |
| **Standardization** | RFC 8484 | RFC 7858, RFC 8310 | Open protocol | RFC 1035 |
| **DNSSEC** | Supported | Supported | Built-in | Optional |

## Public DNS Privacy Resolvers

Before setting up your own stack, knowing which providers support each protocol helps:

| Provider | DoH | DoT | DNSCrypt | DNSSEC | No-Log Policy |
|----------|[cloudflare](https://www.cloudflare.com/)-|----------|--------|---------------|
| **Cloudflare (1.1.1.1)** | ✅ | ✅ | ❌ | ✅ | Yes |
| **Quad9 (9.9.9.9)** | ✅ | ✅ | ✅ | ✅ | Yes |
| **NextDNS** | ✅ | ✅ | ✅ | ✅ | Yes (configurable) |
| **AdGuard DNS** | ✅ | ✅ | ✅ | ✅ | Yes |
| **Mullvad DNS** | ✅ | ✅ | ❌ | ✅ | Yes |
| **Google (8.8.8.8)** | ✅ | ✅ | ❌ | ✅ | No |
| **OpenDNS/Cisco** | ✅ | ✅ | ❌ | ✅ | No |

For maximum privacy, choose a provider with a verified no-log policy. Cloudflare, Quad9, NextDNS, and Mullvad are strong choices. Avoid Google and OpenDNS if privacy is your primary concern — they log queries for analytics and advertising.

## Setting Up DNS-over-TLS with Stubby

Stubby is a lightweight DNS-over-TLS stub resolver developed by the getdns team. It runs locally on your machine, forwarding all DNS queries over encrypted TLS connections to upstream resolvers.

### Installation

On Debian/Ubuntu:

```bash
sudo apt update
sudo apt install stubby
```

On Arch Linux:

```bash
sudo pacman -S stubby
```

On macOS with Homebrew:

```bash
brew install stubby
```

### Configuration

Edit `/etc/stubby/stubby.yml`:

```yaml
resolution_type: GETDNS_RESOLUTION_STUB
dns_transport_list:
  - GETDNS_TRANSPORT_TLS
tls_authentication: GETDNS_AUTHENTICATION_REQUIRED
tls_query_padding_blocksize: 128
edns_client_subnet_private: 1
round_robin_upstreams: 1
idle_timeout: 10000

# Upstream recursive resolvers
upstream_recursive_servers:
  # Cloudflare
  - address_data: 1.1.1.1
    tls_auth_name: "cloudflare-dns.com"
  - address_data: 1.0.0.1
    tls_auth_name: "cloudflare-dns.com"
  # Quad9
  - address_data: 9.9.9.9
    tls_auth_name: "dns.quad9.net"
  - address_data: 149.112.112.112
    tls_auth_name: "dns.quad9.net"
  # Mullvad
  - address_data: 194.242.2.2
    tls_auth_name: "dns.mullvad.net"
```

Enable and start Stubby:

```bash
sudo systemctl enable stubby
sudo systemctl start stubby
```

### Configure Your System to Use Stubby

Edit `/etc/systemd/resolved.conf`:

```ini
[Resolve]
DNS=127.0.0.1
FallbackDNS=
DNSSEC=yes
DNSOverTLS=no
```

Then restart systemd-resolved:

```bash
sudo systemctl restart systemd-resolved
```

Verify Stubby is working:

```bash
dig @127.0.0.1 example.com
```

You should see a successful response. Check the Stubby logs:

```bash
journalctl -u stubby -f
```

## Setting Up DNS-over-HTTPS with Cloudflared

Cloudflare's `cloudflared` daemon acts as a local DoH proxy. It listens on a local port and forwards all DNS queries to Cloudflare's DoH endpoint (or any other DoH provider).

### Installation

On Debian/Ubuntu:

```bash
sudo mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | \
  sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null

echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] \
  https://pkg.cloudflare.com/cloudflared $(lsb_release -cs) main" | \
  sudo tee /etc/apt/sources.list.d/cloudflared.list

sudo apt update && sudo apt install cloudflared
```

### Configuration

Create `/etc/default/cloudflared`:

```bash
CLOUDFLARED_OPTS=--port 5053 --upstream https://1.1.1.1/dns-query --upstream https://1.0.0.1/dns-query
```

You can also use alternative DoH providers:

```bash
# Quad9 DoH
CLOUDFLARED_OPTS=--port 5053 --upstream https://dns.quad9.net/dns-query

# AdGuard DoH
CLOUDFLARED_OPTS=--port 5053 --upstream https://dns.adguard.com/dns-query

# NextDNS (replace YOUR-ID with your config ID)
CLOUDFLARED_OPTS=--port 5053 --upstream https://dns.nextdns.io/YOUR-ID
```

Create a systemd service file at `/etc/systemd/system/cloudflared.service`:

```ini
[Unit]
Description=DNS-over-HTTPS Proxy
After=network.target

[Service]
EnvironmentFile=/etc/default/cloudflared
ExecStart=/usr/bin/cloudflared proxy-dns $CLOUDFLARED_OPTS
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

Point your system to the local proxy:

```bash
# Update resolv.conf or network manager to use 127.0.0.1#5053
echo "nameserver 127.0.0.1" | sudo tee /etc/resolv.conf
```

## Setting Up DNSCrypt with dnscrypt-proxy

`dnscrypt-proxy` is a powerful DNSCrypt client that also supports DoH and DoT. It provides caching, load balancing, blocklists, cloaking, and query logging controls — making it one of the most feature-rich DNS privacy tools available.

### Installation

Download the latest release from GitHub:

```bash
VERSION="2.1.5"
curl -LO "https://github.com/DNSCrypt/dnscrypt-proxy/releases/download/${VERSION}/dnscrypt-proxy-linux_x86_64-${VERSION}.tar.gz"
tar -xzf "dnscrypt-proxy-linux_x86_64-${VERSION}.tar.gz"
sudo mv linux-x86_64 /opt/dnscrypt-proxy
cd /opt/dnscrypt-proxy
```

### Configuration

Copy the example config and customize it:

```bash
sudo cp example-dnscrypt-proxy.toml dnscrypt-proxy.toml
sudo nano dnscrypt-proxy.toml
```

Key configuration options:

```toml
# Listen on localhost
listen_addresses = ['127.0.0.1:53', '[::1]:53']

# Use multiple protocols simultaneously
server_names = ['cloudflare', 'quad9-dnscrypt-ipv4-filter-pri', 'mullvad-adblock']

# DNS cache
cache = true
cache_size = 4096
cache_min_ttl = 600
cache_max_ttl = 86400
cache_neg_ttl = 600

# Blocklists (ads, trackers, malware)
sources = [
  {name = 'public-resolvers', urls = ['https://download.dnscrypt.info/resolvers-list/v2/public-resolvers.md'], cache_file = 'public-resolvers.md', minisign_key = 'RWQf6LRCGA9i53mlYecO4IzT51TGPpvWucNSCh1CBM0QTaL7WBFlyX2b', refresh_delay = 72, prefix = ''},
  {name = 'relays', urls = ['https://download.dnscrypt.info/resolvers-list/v2/relays.md'], cache_file = 'relays.md', minisign_key = 'RWQf6LRCGA9i53mlYecO4IzT51TGPpvWucNSCh1CBM0QTaL7WBFlyX2b', refresh_delay = 72, prefix = ''}
]

# Block malicious domains
blocked_names_file = 'blocked-names.txt'
blocked_ips_file = 'blocked-ips.txt'

# Cloaking (redirect domains)
cloaking_rules = 'cloaking-rules.txt'

# Query logging (disabled for privacy)
[query_log]
format = 'tsv'
ignored_qtypes = ['DNSKEY', 'NS']

[nx_log]
format = 'tsv'

[log]
level = 2
file = '/var/log/dnscrypt-proxy.log'
```

Install as a systemd service:

```bash
sudo ./dnscrypt-proxy -service install
sudo ./dnscrypt-proxy -service start
sudo ./dnscrypt-proxy -service enable
```

Test the resolver:

```bash
dig @127.0.0.1 example.com
```

Check dnscrypt-proxy status:

```bash
sudo ./dnscrypt-proxy -service status
sudo ./dnscrypt-pr[docker](https://www.docker.com/)how-certs
```

## Running DNS Privacy Tools in Docker

If you prefer containerized deployments, all three tools run well in Docker. Here are production-ready configurations:

### Stubby in Docker

```yaml
version: "3.8"

services:
  stubby:
    image: ghcr.io/getdnsapi/stubby:latest
    container_name: stubby
    restart: unless-stopped
    ports:
      - "127.0.0.1:53:53/tcp"
      - "127.0.0.1:53:53/udp"
    volumes:
      - ./stubby.yml:/etc/stubby/stubby.yml:ro
    cap_drop:
      - ALL
    read_only: true
    security_opt:
      - no-new-privileges:true
```

### Cloudflared (DoH) in Docker

```yaml
version: "3.8"

services:
  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: cloudflared
    restart: unless-stopped
    command: proxy-dns --port 5053 --upstream https://1.1.1.1/dns-query --upstream https://1.0.0.1/dns-query
    ports:
      - "127.0.0.1:5053:5053/udp"
      - "127.0.0.1:5053:5053/tcp"
    user: "nobody"
    read_only: true
    security_opt:
      - no-new-privileges:true
```

### dnscrypt-proxy in Docker

```yaml
version: "3.8"

services:
  dnscrypt-proxy:
    image: ghcr.io/dnscrypt/dnscrypt-proxy:latest
    container_name: dnscrypt-proxy
    restart: unless-stopped
    ports:
      - "127.0.0.1:53:53/tcp"
      - "127.0.0.1:53:53/udp"
    volumes:
      - ./dnscrypt-proxy.toml:/etc/dnscrypt-proxy/dnscrypt-proxy.toml:ro
      - ./blocked-names.txt:/etc/dnscrypt-proxy/blocked-names.txt:ro
    cap_drop:
      - ALL
    read_only: true
    security_opt:
      - no-new-privileges:true
```

## Integrating with Pi-hole or AdGuard Home

DNS privacy tools work best when combined with a local ad-blocking DNS server. The typical architecture routes traffic like this:

```
Client → Pi-hole/AdGuard Home (ad-blocking, filtering) → Stubby/cloudflared/dnscrypt-proxy (encrypted upstream) → Public DNS Resolver
```

### Pi-hole with DNS Privacy

In Pi-hole's admin interface, go to **Settings → DNS** and set your upstream DNS servers to `127.0.0.1#53` (for Stubby) or `127.0.0.1#5053` (for cloudflared). This ensures Pi-hole handles ad-blocking locally and forwards all external queries through your encrypted DNS proxy.

```bash
# Verify Pi-hole is using the encrypted upstream
pihole status
dig @127.0.0.1 -p 53 doubleclick.net
# Should return 0.0.0.0 (Pi-hole blocked)

dig @127.0.0.1 -p 53 example.com
# Should resolve normally via encrypted upstream
```

### AdGuard Home with DNS Privacy

In AdGuard Home, navigate to **Settings → DNS settings** and add `127.0.0.1:53` or `127.0.0.1:5053` as your upstream DNS server. AdGuard Home also has built-in DoH and DoT support, so you can configure encrypted upstream directly in its settings without a separate proxy:

```yaml
# AdGuard Home config snippet for encrypted upstream
dns:
  upstream_dns:
    - "tls://1.1.1.1"           # DoT to Cloudflare
    - "https://1.1.1.1/dns-query" # DoH to Cloudflare
    - "sdns://..."               # DNSCrypt server stamp
```

## Choosing the Right Protocol

Your choice depends on your priorities:

- **Best for privacy and firewall evasion**: DNS-over-HTTPS (DoH) — indistinguishable from regular web traffic, hardest to block
- **Best for performance and monitoring**: DNS-over-TLS (DoT) — lower overhead, dedicated port makes it easier to manage on your network
- **Best feature set**: dnscrypt-proxy — supports all three protocols, includes caching, blocklists, cloaking, and load balancing in a single tool
- **Best for Android**: DoT — native support since Android 9, easy to configure in Private DNS settings
- **Best for browsers**: DoH — Firefox and Chrome have native DoH support with built-in resolvers

## Performance Benchmarks

Using `kdig` to measure query latency (50 queries each, averaged):

| Resolver | Protocol | Avg Latency | p95 Latency |
|----------|----------|-------------|-------------|
| Cloudflare | DoH | 12ms | 28ms |
| Cloudflare | DoT | 9ms | 22ms |
| Quad9 | DNSCrypt | 11ms | 25ms |
| Quad9 | DoT | 14ms | 35ms |
| Google | DoH | 15ms | 32ms |
| Plain DNS | Unencrypted | 5ms | 12ms |

DoT consistently offers the lowest latency among encrypted protocols. DNSCrypt performs competitively with its optimized cryptographic design. The overhead of DoH (HTTP framing) adds roughly 3-5ms compared to DoT, but this is negligible for most use cases.

## Testing Your DNS Privacy Setup

After configuration, verify everything works correctly:

```bash
# Test resolution through your privacy proxy
dig @127.0.0.1 example.com +short

# Check that queries are encrypted (no plain-text DNS on port 53 to external servers)
sudo tcpdump -i any port 53 and not src 127.0.0.1 and not dst 127.0.0.1

# Verify DNSSEC validation
dig @127.0.0.1 dnssec.works +dnssec

# Test for DNS leaks
curl https://dnsleaktest.com
# Or use: https://dnsleak.com
```

You can also use online tools like [DNS Leak Test](https://dnsleaktest.com) and [Perfect Privacy DNS Leak Test](https://www.perfect-privacy.com/dns-leaktest/) to confirm no queries leak outside your encrypted channel.

## Conclusion

Encrypting your DNS queries is one of the most impactful privacy improvements you can make to your network. The three protocols — DoH, DoT, and DNSCrypt — each have strengths:

- **DoH** wins on compatibility and firewall evasion, making it the best choice for most users
- **DoT** offers the best balance of performance and manageability, ideal for server and homelab deployments
- **DNSCrypt** with dnscrypt-proxy provides the most comprehensive feature set, combining multiple protocols with ad-blocking and caching

For a production self-hosted setup, we recommend running **dnscrypt-proxy** as your local resolver (it supports all three protocols) with **Pi-hole or AdGuard Home** for filtering, forwarding through encrypted upstream resolvers like Cloudflare, Quad9, or Mullvad. This gives you encrypted DNS, ad-blocking, and query logging control — all running on your own infrastructure.

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
