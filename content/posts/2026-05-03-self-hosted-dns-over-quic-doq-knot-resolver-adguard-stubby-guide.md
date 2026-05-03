---
title: "Self-Hosted DNS-over-QUIC (DoQ) Server Guide: Knot Resolver, AdGuard Home, and Stubby 2026"
date: 2026-05-03
tags: ["guide", "self-hosted", "dns", "privacy", "security", "DoQ"]
draft: false
description: "Complete guide to deploying DNS-over-QUIC (DoQ) servers for encrypted DNS resolution. Compare Knot Resolver, AdGuard Home, and Stubby with Docker configurations and setup instructions."
---

## What Is DNS-over-QUIC?

DNS-over-QUIC (DoQ) is the latest protocol for encrypting DNS queries, standardized in RFC 9250. It combines the encryption guarantees of DNS-over-TLS (DoT) with the performance benefits of the QUIC transport protocol — the same protocol that powers HTTP/3. Unlike DoT, which runs over TCP with TLS, DoQ runs over QUIC/UDP, eliminating head-of-line blocking and reducing connection establishment latency through 0-RTT resumption.

The result is encrypted DNS that is faster than DoT and more resistant to blocking than DNS-over-HTTPS (DoH). For privacy-conscious infrastructure operators, deploying a local DoQ resolver is the strongest way to ensure DNS queries never leave your network in plaintext.

For a broader look at encrypted DNS options, see our [complete DNS privacy guide](../self-hosted-dns-privacy-doh-dot-dnscrypt-guide/) covering DoH, DoT, and DNSCrypt. If you need DNS filtering alongside encryption, our [AdGuard Home vs Pi-hole comparison](../adguard-home-vs-technitium-dns-pihole/) covers ad-blocking resolvers. For DNS-over-TLS specifically, check our [DoT resolver guide](../self-hosted-dns-over-tls-resolver-stubby-unbound-knot-2026/).

## Quick Comparison Table

| Feature | Knot Resolver | AdGuard Home | Stubby |
|---|---|---|---|
| **Project** | CZ.NIC / Knot DNS | AdGuard | getdns |
| **Primary Role** | Authoritative + Recursive resolver | DNS filtering + recursive | DoT/DoQ stub resolver |
| **DoQ Server** | ✅ Full server | ✅ Server + client | ❌ Client only (stub) |
| **DoT Support** | ✅ | ✅ | ✅ |
| **DoH Support** | ✅ | ✅ | ❌ |
| **DNSCrypt** | ❌ | ✅ | ❌ |
| **Ad Blocking** | ❌ (via modules) | ✅ Built-in | ❌ |
| **Parental Controls** | ❌ | ✅ | ❌ |
| **Caching** | ✅ Aggressive caching | ✅ | ❌ (forwards to upstream) |
| **Web UI** | ❌ (CLI only) | ✅ Full dashboard | ❌ (CLI config) |
| **Docker Support** | ✅ Official image | ✅ Official image | ❌ (package install) |
| **Platform** | Linux | Cross-platform | Linux/macOS/Windows |
| **License** | GPL-3.0 | GPL-3.0 | BSD-3-Clause |

## Knot Resolver: Full-Featured DoQ Server

Knot Resolver, developed by CZ.NIC (the operators of the .cz TLD), is a high-performance caching DNS resolver with native support for DNS-over-QUIC, DNS-over-TLS, and DNS-over-HTTPS. It is built on the Knot DNS library and is designed for operators who need a production-grade recursive resolver.

**Key strengths:**

- **Native QUIC support** — one of the first resolvers to implement DoQ per RFC 9250, with mature and well-tested code
- **High performance** — event-driven architecture handles tens of thousands of queries per second on modest hardware
- **Policy engine** — powerful Lua-based policy system for DNS rewriting, blocking, and traffic steering
- **DNSSEC validation** — full DNSSEC validation with automatic trust anchor management
- **Modular architecture** — extensive module system for custom functionality (DNS64, RPZ, Prometheus metrics)
- **Minimal resource usage** — typically uses under 100 MB RAM for a home or small-office deployment

**Best for:** Network operators, ISPs, and privacy enthusiasts who need a full recursive resolver with DoQ support.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  knot-resolver:
    image: cznic/knot-resolver:latest
    restart: unless-stopped
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "853:853/tcp"
      - "853:853/udp"
      - "443:443/tcp"
      - "443:443/udp"
    volumes:
      - ./kresd-config:/etc/knot-resolver
      - kresd-data:/var/lib/knot-resolver
    cap_add:
      - NET_BIND_SERVICE

volumes:
  kresd-data:
```

Configuration for DoQ in `kresd-config/kresd.conf`:

```lua
-- Enable DNS-over-QUIC on port 853
tls.cert = '/etc/knot-resolver/tls/server.crt'
tls.key = '/etc/knot-resolver/tls/server.key'
policy.add(policy.quic({'::', 853}))

-- Forward upstream queries
policy.add(policy.forward('1.1.1.1', {protocol = 'tls'}))
policy.add(policy.forward('9.9.9.9', {protocol = 'tls'}))

-- Enable DNSSEC validation
trust_anchors.add('.')
```

Generate a self-signed or Let's Encrypt certificate for the TLS/QUIC endpoints. Knot Resolver requires valid certificates for both DoT and DoQ connections.

## AdGuard Home: DoQ with Filtering

AdGuard Home is best known as a network-wide ad-blocking DNS server, but it also supports DNS-over-QUIC as both a server and client. This makes it an attractive option for users who want encrypted DNS with content filtering in a single package.

**Key strengths:**

- **Ad and tracker blocking** — built-in filter lists with custom rule support, blocking ads, trackers, and malicious domains at the DNS level
- **DoQ server and client** — can serve DoQ to clients and forward queries to upstream DoQ resolvers
- **Web dashboard** — comprehensive management UI with query logs, statistics, and filter configuration
- **Parental controls** — safe search enforcement and age-restricted content blocking
- **Per-client configuration** — different filtering rules and upstream servers for different devices
- **Easy setup** — one-command installation with a guided web-based wizard

**Best for:** Home users, small offices, and families who want encrypted DNS with ad blocking and parental controls.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  adguard-home:
    image: adguard/adguardhome:latest
    restart: unless-stopped
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "853:853/tcp"
      - "853:853/udp"
      - "3000:3000/tcp"
    volumes:
      - adguard-work:/opt/adguardhome/work
      - adguard-conf:/opt/adguardhome/conf

volumes:
  adguard-work:
  adguard-conf:
```

After initial setup via the web interface at `http://localhost:3000`, enable DoQ in Settings → DNS Settings → Encrypted DNS:

```yaml
# Encryption settings in AdGuard Home UI:
# - Enable DNS-over-QUIC
# - Server address: :853
# - Server name: dns.yourdomain.example
# - Path to certificate: /opt/adguardhome/conf/server.crt
# - Path to private key: /opt/adguardhome/conf/server.key
```

AdGuard Home also supports DoQ as an upstream resolver. Add `quic://dns.adguard-dns.com` to your upstream DNS servers to resolve queries through a remote DoQ provider.

## Stubby: Lightweight DoQ Stub Resolver

Stubby is not a full DNS resolver — it is a stub resolver that sits between your applications and upstream DNS servers, encrypting all outbound queries via DoT or DoQ. It uses the getdns API and is designed as a drop-in replacement for system resolvers like systemd-resolved or dnsmasq.

**Key strengths:**

- **Lightweight** — minimal footprint, designed to run on resource-constrained systems
- **Transparent operation** — intercepts local DNS queries and forwards them encrypted without changing application configuration
- **Multiple upstream support** — can rotate between multiple upstream DoT/DoQ servers for redundancy
- **Strict privacy mode** — does not log queries and does not expose your IP to the upstream resolver beyond what is necessary
- **Cross-platform** — runs on Linux, macOS, and Windows

**Limitation:** Stubby is a client/stub resolver, not a server. It encrypts outbound queries but does not serve DNS to other devices on your network.

**Best for:** Single-machine privacy setups where you want to encrypt all DNS queries from the local system without running a full recursive resolver.

### Installation (No Docker)

Stubby is typically installed via package manager rather than Docker, as it needs to bind to port 53 on the host:

```bash
# Ubuntu/Debian
sudo apt install stubby

# Configure upstream DoQ servers
sudo nano /etc/stubby/stubby.yml
```

Example `stubby.yml` configuration with DoQ upstreams:

```yaml
appdata_dir: /var/cache/stubby
dnssec:
  status: enforce
tls_authentication:
  status: enforce
  tls_port: 853
upstreams:
  - address_data: dns.adguard-dns.com
    tls_port: 853
    tls_auth_name: "dns.adguard-dns.com"
  - address_data: dns.quad9.net
    tls_port: 853
    tls_auth_name: "dns.quad9.net"
  - address_data: one.one.one.one
    tls_port: 853
    tls_auth_name: "one.one.one.one"
listen_addresses:
  - 127.0.0.1
  - ::1
```

Then configure your system to use Stubby as the local resolver:

```bash
# Update resolv.conf to use localhost
echo "nameserver 127.0.0.1" | sudo tee /etc/resolv.conf

# Restart Stubby
sudo systemctl restart stubby
sudo systemctl enable stubby
```

## Why Encrypt DNS with QUIC?

Traditional DNS sends queries in plaintext over UDP port 53. This means any intermediary — your ISP, a coffee shop Wi-Fi operator, or a nation-state firewall — can see every domain you look up, block specific domains, or inject false responses (DNS spoofing).

DNS-over-QUIC solves these problems:

**Encryption.** QUIC encrypts the entire DNS query and response, preventing eavesdropping and man-in-the-middle attacks.

**Performance.** Unlike DNS-over-TLS, which suffers from TCP head-of-line blocking, QUIC runs over UDP and supports multiplexed streams. A single QUIC connection can carry multiple DNS queries concurrently without waiting for previous responses.

**0-RTT resumption.** QUIC supports zero round-trip time connection resumption, meaning repeat queries to the same server are faster than DoT, which requires a full TLS handshake for each new connection.

**Firewall resistance.** QUIC traffic on UDP port 853 is harder to selectively block than DoH on TCP 443, since port 443 carries all HTTPS traffic and blocking it breaks the entire web.

For a broader comparison of encrypted DNS protocols, see our [DNS privacy overview](../self-hosted-dns-privacy-doh-dot-dnscrypt-guide/).

## FAQ

### Is DNS-over-QUIC better than DNS-over-HTTPS?

DoQ and DoH both encrypt DNS queries, but they use different transport protocols. DoQ runs over QUIC/UDP which has lower latency than DoH's TCP/TLS stack. However, DoH benefits from blending in with regular HTTPS traffic, making it harder for firewalls to detect and block. For most home deployments, DoQ is faster. For environments with aggressive firewalls, DoH may be more reliable.

### Can I use DNS-over-QUIC with Pi-hole?

Pi-hole does not natively support DNS-over-QUIC as a server. However, you can run Stubby or dnscrypt-proxy alongside Pi-hole to encrypt outbound queries. AdGuard Home, which is similar to Pi-hole, does support DoQ natively as both server and client.

### Do I need a TLS certificate for DNS-over-QUIC?

Yes. Both Knot Resolver and AdGuard Home require a valid TLS certificate (and matching private key) to serve DoQ. You can use a free Let's Encrypt certificate or a self-signed certificate (though self-signed certs require clients to explicitly trust them). The certificate must match the hostname that clients will use to connect.

### What port does DNS-over-QUIC use?

The IANA-assigned port for DNS-over-QUIC is 853 (TCP and UDP). This is the same port used by DNS-over-TLS, but the QUIC protocol is negotiated during the QUIC handshake. Some implementations also support DoQ on port 443 for firewall traversal.

### Is DNS-over-QUIC supported by public DNS providers?

Yes. Several public DNS providers support DoQ: AdGuard DNS (`dns.adguard-dns.com`), Quad9 (`dns.quad9.net`), and Cloudflare (`cloudflare-dns.com`). You can configure Knot Resolver or AdGuard Home to forward queries to these providers over QUIC.

### How do I test if my DoQ server is working?

Use the `kdig` tool (part of Knot DNS) to test DoQ connectivity:

```bash
kdig @your-server.example +tls +tls-ca=+ca.crt example.com AAAA
```

Or use `getdns_query` from the getdns package:

```bash
getdns_query -s -l -L @your-server.example#853 example.com A
```

Successful responses with no errors confirm your DoQ server is operational.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DNS-over-QUIC (DoQ) Server Guide: Knot Resolver, AdGuard Home, and Stubby 2026",
  "description": "Complete guide to deploying DNS-over-QUIC (DoQ) servers for encrypted DNS resolution. Compare Knot Resolver, AdGuard Home, and Stubby with Docker configurations.",
  "datePublished": "2026-05-03",
  "dateModified": "2026-05-03",
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
