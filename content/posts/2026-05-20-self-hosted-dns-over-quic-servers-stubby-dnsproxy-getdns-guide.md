---
title: "Self-Hosted DNS-over-QUIC Servers: Stubby vs dnsproxy vs getdns (2026)"
date: "2026-05-20"
tags: ["dns", "quic", "privacy", "dns-over-quic", "networking", "encryption"]
draft: false
---

DNS-over-QUIC (DoQ, RFC 9250) is the newest protocol for encrypted DNS resolution, combining the security of TLS 1.3 with QUIC's zero-RTT connection establishment and improved performance over TCP-based DoT. While DNS-over-TLS and DNS-over-HTTPS are widely deployed, DoQ represents the next generation of encrypted DNS with lower latency and better connection resilience.

## Understanding DNS-over-QUIC (DoQ)

DNS-over-QUIC encapsulates DNS queries inside QUIC streams, providing the same encryption guarantees as DoT (TLS 1.3) with significant performance benefits:

- **Zero-RTT resumption** — cached connections skip the TLS handshake for faster query resolution
- **No head-of-line blocking** — each DNS query runs on an independent QUIC stream
- **Connection migration** — queries survive network interface changes (WiFi to cellular)
- **UDP-like performance with TCP reliability** — QUIC runs over UDP but provides reliable, ordered delivery

Self-hosted DoQ servers let you run your own encrypted DNS resolver, protecting query privacy from ISP surveillance and man-in-the-middle attacks while maintaining full control over DNS policy and caching.

## Stubby: The Reference DoT/DoQ Client

[Stubby](https://github.com/getdnsapi/stubby) is the reference implementation for DNS-over-TLS and DNS-over-QUIC client functionality, built on the getdns API. While primarily a client/stub resolver, it is essential infrastructure for DoQ deployments — forwarding local DNS queries to upstream DoQ resolvers with encryption and privacy guarantees.

**Key Features:**
- DNS-over-QUIC (RFC 9250) client support
- DNS-over-TLS (RFC 7858) with multiple upstream resolver support
- Round-robin and order-based upstream selection
- DNSSEC validation via getdns
- Low-latency query forwarding
- Integration with systemd-resolved and dnsmasq
- Lightweight C implementation

### Installation

```bash
# Debian/Ubuntu
apt-get install stubby getdns-api

# Arch Linux
pacman -S stubby

# Build from source
git clone https://github.com/getdnsapi/stubby.git
cd stubby
mkdir build && cd build
cmake ..
make && make install
```

### Configuration for DoQ

```yaml
# /etc/stubby/stubby.yml
appdata_directory: /var/cache/stubby
dns_transport_list:
  - QUIC
  - TLS
  - TCP
  - UDP

upstream_recursive_servers:
  # Cloudflare DoQ resolver
  - address_data: 2606:4700:4700::1111
    tls_port: 853
    tls_auth_name: "cloudflare-dns.com"
  - address_data: 1.1.1.1
    tls_port: 853
    tls_auth_name: "cloudflare-dns.com"
  # Google DoQ resolver
  - address_data: 2001:4860:4860::8888
    tls_port: 853
    tls_auth_name: "dns.google"
  - address_data: 8.8.8.8
    tls_port: 853
    tls_auth_name: "dns.google"

listen_addresses:
  - 127.0.0.1@53000
  - 0::1@53000
```

Start the service:

```bash
systemctl enable --now stubby
# Test DoQ resolution
getdns_query -s @127.0.0.1 -p 53000 example.com A
```

## dnsproxy: The Universal DNS Proxy

[dnsproxy](https://github.com/AdguardTeam/dnsproxy) by AdGuard is a versatile DNS proxy supporting DoQ, DoH, DoT, and plain DNS. It can act as both a client (forwarding to upstream DoQ resolvers) and a server (accepting DoQ queries from downstream clients), making it a complete DoQ solution.

**Key Features:**
- Full DNS-over-QUIC server and client support
- DNS-over-HTTPS (DoH) and DNS-over-TLS (DoT) support
- Ad blocking via filter lists
- DNS caching with configurable TTL
- Rate limiting and query logging
- Bootstrap DNS for resolver discovery
- EDNS Client Subnet (ECS) support
- Cross-platform binary (Go)

### Docker Deployment

```yaml
version: "3.8"
services:
  dnsproxy:
    image: adguard/dnsproxy:latest
    container_name: dnsproxy
    ports:
      - "53:53/udp"
      - "53:53/tcp"
      - "853:853/tcp"
      - "853:853/udp"
      - "784:784/udp"
    volumes:
      - ./dnsproxy-cache:/opt/dnsproxy-cache
    command: >
      --udp=0.0.0.0:53
      --tcp=0.0.0.0:53
      --tls-port=853
      --quic-port=853
      --https-port=784
      --tls-crt=/certs/server.crt
      --tls-key=/certs/server.key
      --upstream="quic://dns.adguard.com"
      --upstream="quic://one.one.one.one"
      --cache --cache-size=4096
      --cache-optimistic
    restart: unless-stopped
    volumes:
      - ./certs:/certs:ro
```

### Generate TLS Certificates for DoQ Server

```bash
# Self-signed certificate for local DoQ server
openssl req -x509 -newkey rsa:2048 -nodes   -keyout server.key -out server.crt   -days 365 -subj "/CN=dns.example.com"   -addext "subjectAltName=DNS:dns.example.com,IP:192.168.1.1"

# Place certs and restart dnsproxy
cp server.crt server.key ./certs/
docker compose restart dnsproxy
```

## getdns: The DNS API Library

[getdns](https://github.com/getdnsapi/getdns) is a modern DNS API library that provides the foundation for Stubby and other DNS privacy tools. It supports DNS-over-QUIC, DNS-over-TLS, and DNSSEC validation through a unified, asynchronous API.

**Key Features:**
- Modern asynchronous DNS API
- DNS-over-QUIC, DNS-over-TLS, DNS-over-HTTPS support
- DNSSEC validation built-in
- Multiple backend support (libuv, libevent, systemd)
- Python, C, and command-line interfaces
- Stub and recursive resolver modes
- Connection pooling and retry logic

### Python API Example

```python
import getdns

# Create context with DoQ upstream
ctx = getdns.Context()
ctx.upstream_recursive_servers = [
    { "address_data": "1.1.1.1", "tls_port": 853 }
]
ctx.dns_transport_list = [getdns.TRANSPORT_QUIC]

# Resolve a query
result = ctx.general("example.com", getdns.RRTYPE_A)
for answer in result.replies_tree:
    print(f"{answer['name']}: {answer['rdata']['ipv4_address']}")
```

### Docker Compose with getdns

```yaml
version: "3.8"
services:
  getdns:
    image: ghcr.io/getdnsapi/getdns:latest
    container_name: getdns
    ports:
      - "53000:53/udp"
      - "53000:53/tcp"
    command: >
      getdns_server_start -c /etc/getdns.conf
    volumes:
      - ./getdns.conf:/etc/getdns.conf:ro
    restart: unless-stopped
```

## Comparison Table

| Feature | Stubby | dnsproxy | getdns |
|---------|--------|----------|--------|
| GitHub Stars | 1,000+ | 1,100+ | 500+ |
| DoQ Client | Yes | Yes | Yes |
| DoQ Server | No | Yes | No |
| DoH Support | No | Yes | Yes |
| DoT Support | Yes | Yes | Yes |
| Ad Blocking | No | Yes | No |
| DNS Caching | No | Yes | Yes |
| DNSSEC | Via getdns | Via upstream | Built-in |
| Language | C | Go | C |
| Docker Image | No official | adguard/dnsproxy | ghcr.io/getdnsapi |
| Config Format | YAML | CLI flags | YAML/JSON |
| Best For | DoQ client/stub | Full DoQ server | DNS API development |

## Why Self-Host DNS-over-QUIC?

Encrypted DNS is no longer optional — it is a fundamental privacy and security requirement for modern infrastructure.

**Protect DNS Query Privacy.** Without encryption, every DNS query traverses your network in plaintext, visible to ISPs, network operators, and anyone with access to your traffic. DoQ encrypts both the query and response using TLS 1.3, preventing eavesdropping and tampering. Self-hosting means you control the resolver — queries never leave your infrastructure unless you choose to forward them.

**Better Performance Than DoT.** QUIC's zero-RTT connection resumption means repeated DNS queries to the same resolver skip the TLS handshake entirely. In benchmarks, DoQ achieves 20-40% lower latency than DoT for cached connections. The independent stream model also eliminates head-of-line blocking — a slow query does not delay others.

**Resilience to Network Changes.** QUIC's connection migration allows DNS sessions to survive network interface changes. This is particularly valuable for mobile deployments, edge computing nodes, and any infrastructure that may switch between WiFi, cellular, or wired connections without dropping active DNS sessions.

**Defense Against DNS Manipulation.** Many ISPs and network operators manipulate DNS responses — redirecting NXDOMAIN to advertising pages, injecting tracking pixels, or blocking access to certain domains. DoQ ensures that the responses you receive are exactly what the authoritative resolver returned, unmodified in transit.

**Regulatory Compliance.** GDPR, CCPA, and other privacy regulations require organizations to protect user data in transit. DNS queries reveal browsing patterns and can be considered personal data. Deploying DoQ demonstrates due diligence in protecting user privacy.

For DNS privacy with DNSCrypt, see our [DNS privacy comparison](../2026-04-21-self-hosted-dns-privacy-doh-dot-dnscrypt-guide/). If you need DNS ad blocking, our [AdGuard Home vs Pi-hole guide](../2026-04-15-adguard-home-vs-pihole-comparison/) covers the options. For DNS load balancing with dnsdist, check our [DNS load balancing article](../2026-05-14-self-hosted-dns-load-balancing-dnsdist-powerdns-knot-guide/).



**Simplified Operations.** Traditional DNS infrastructure requires managing separate resolver chains for plaintext, DoT, and DoH traffic. DoQ consolidates encrypted DNS into a single protocol stack — the same QUIC listener handles all encrypted query types when paired with a capable proxy like dnsproxy. This reduces operational complexity, minimizes the attack surface, and eliminates the need to maintain parallel resolver configurations for different encryption protocols.

**Future-Proof Infrastructure.** As QUIC adoption grows across the internet (HTTP/3 is already QUIC-based), DNS-over-QUIC positions your infrastructure to take advantage of improvements in the QUIC ecosystem. QUIC's ongoing standardization in the IETF means continuous security improvements, performance optimizations, and broader client support — all of which benefit DoQ deployments automatically.

## FAQ

### What is DNS-over-QUIC and how does it differ from DoT?

DNS-over-QUIC (DoQ, RFC 9250) encrypts DNS queries using QUIC (a UDP-based transport protocol with built-in TLS 1.3), while DNS-over-TLS (DoT, RFC 7858) uses TCP with TLS. DoQ provides faster connection resumption (zero-RTT), no head-of-line blocking, and connection migration — making it more performant and resilient than DoT.

### Is DNS-over-QUIC widely supported?

Major DNS providers support DoQ: Cloudflare (quic://1.1.1.1:853), Google (quic://8.8.8.8:853), and AdGuard (quic://dns.adguard.com). Client support is growing — Stubby, dnsproxy, and getdns all support DoQ. However, adoption is still lower than DoH and DoT.

### Can I run a DoQ server for my network?

Yes. dnsproxy supports running as a DoQ server, accepting encrypted QUIC connections from downstream clients. You need TLS certificates (self-signed or from Let's Encrypt) and a UDP port (typically 853) configured for QUIC traffic.

### Does DoQ work with DNSSEC?

Yes, DoQ and DNSSEC are complementary. DoQ encrypts the transport layer (preventing in-transit tampering), while DNSSEC validates the authenticity of DNS responses (preventing upstream spoofing). Tools like getdns and Stubby support both simultaneously.

### What port does DNS-over-QUIC use?

DoQ uses UDP port 853, the same port number as DNS-over-TLS but with a different transport protocol. Some implementations also support DoQ on port 443 for firewall traversal compatibility.

### Is DoQ faster than plain DNS (UDP 53)?

For uncached connections, DoQ has slightly higher latency due to the TLS handshake. For cached connections with zero-RTT resumption, DoQ is comparable to plain DNS. The encryption overhead is minimal on modern hardware, and the performance benefits of QUIC's stream model often offset the cryptographic cost.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DNS-over-QUIC Servers: Stubby vs dnsproxy vs getdns (2026)",
  "description": "Compare Stubby, dnsproxy, and getdns for self-hosted DNS-over-QUIC server and client deployments. Includes Docker configs, TLS setup, and production guides.",
  "datePublished": "2026-05-20",
  "dateModified": "2026-05-20",
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
