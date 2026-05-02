---
title: "Sing-Box vs Xray-Core vs Hysteria2: Best Self-Hosted Universal Proxy Platform 2026"
date: 2026-05-03
tags: ["self-hosted", "proxy", "networking", "privacy", "docker", "vpn"]
draft: false
---

A universal proxy platform handles multiple protocols — SOCKS, HTTP, Shadowsocks, VMess, VLESS, Trojan, Hysteria, TUIC, and WireGuard — in a single binary. Rather than running separate services for each protocol, a unified proxy platform gives you one configuration, one process, and one point of control for all your network routing needs.

[Sing-Box](https://github.com/SagerNet/sing-box) has emerged as the leading open-source universal proxy platform, with over 33,000 GitHub stars and weekly active development. In this guide, we compare it against two strong competitors: **Xray-Core** (the Project X continuation of V2Ray) and **Hysteria2** (a QUIC-based high-performance proxy).

## What Is a Universal Proxy Platform?

A universal proxy platform acts as both a client and server for multiple proxy protocols simultaneously. It receives incoming connections, applies routing rules based on destination, protocol, or geo-IP, and forwards traffic through the appropriate outbound channel. Key capabilities include:

- **Multi-protocol support** — handle different proxy types through a single endpoint
- **Rule-based routing** — send domestic traffic direct, foreign traffic through the proxy
- **TLS multiplexing** — disguise proxy traffic as normal HTTPS connections
- **Load balancing** — distribute traffic across multiple upstream servers
- **DNS resolution** — built-in DNS with DoH, DoT, and DNS-over-QUIC support

This architecture is ideal for self-hosters who need flexible network routing without managing a stack of single-purpose proxy tools.

## Comparison at a Glance

| Feature | Sing-Box | Xray-Core | Hysteria2 |
|---------|----------|-----------|-----------|
| **GitHub Stars** | 33,338 | 22,000+ | 7,500+ |
| **Language** | Go | Go | Go |
| **Protocols** | 12+ | 8+ | 2 (Hysteria/Hysteria2) |
| **Configuration** | JSON | JSON | YAML + config file |
| **QUIC Support** | Yes (built-in) | Partial | Native (core feature) |
| **TLS Fragment** | Yes | Yes (reality) | No |
| **DNS Resolver** | Built-in (DoH/DoT/DoQ) | External (needs v2ray-dns) | External |
| **Routing Rules** | Domain, IP, protocol, port | Domain, IP, protocol | Port-based only |
| **IPv6** | Full support | Full support | Full support |
| **gRPC Transport** | Yes | Yes | No |
| **WireGuard** | Built-in inbound/outbound | Via plugin | No |
| **Memory Usage** | ~15MB idle | ~25MB idle | ~10MB idle |
| **Client Apps** | Official (Android/iOS/macOS/Windows) | Third-party | Official |
| **Best For** | All-in-one proxy routing | V2Ray ecosystem users | High-latency networks |

## Sing-Box: The Universal Proxy Platform

Sing-Box was designed from the ground up to be protocol-agnostic. Unlike tools that started as a single protocol and added others over time, Sing-Box treats every protocol as a first-class inbound and outbound option. This means you can mix and match any combination — SOCKS5 in, VMess out; Trojan in, WireGuard out; Hysteria in, direct out — all configured in one file.

**Key features:**

- **Unified configuration** — one `config.json` defines inbounds, outbounds, routing, and DNS
- **Experimental clash API** — REST API for runtime configuration changes
- **GeoIP and GeoSite databases** — route traffic based on country or domain category
- **TLS fragment support** — split TLS ClientHello packets to evade deep packet inspection
- **Built-in DNS server** — resolve DNS through the proxy or independently
- **Cross-platform** — runs on Linux, macOS, Windows, FreeBSD, and Android

### Docker Compose Setup

Sing-Box doesn't ship an official compose file, but the Docker image is straightforward:

```yaml
version: "3"
services:
  sing-box:
    image: ghcr.io/sagernet/sing-box:latest
    container_name: sing-box
    restart: unless-stopped
    network_mode: "host"
    volumes:
      - ./config.json:/etc/sing-box/config.json:ro
      - ./geoip.db:/etc/sing-box/geoip.db:ro
      - ./geosite.db:/etc/sing-box/geosite.db:ro
    cap_add:
      - NET_ADMIN
```

A minimal server configuration with a Trojan inbound and direct outbound:

```json
{
  "log": {
    "level": "info",
    "timestamp": true
  },
  "inbounds": [
    {
      "type": "trojan",
      "tag": "trojan-in",
      "listen": "0.0.0.0",
      "listen_port": 443,
      "users": [
        {
          "name": "user1",
          "password": "your-strong-password"
        }
      ],
      "tls": {
        "enabled": true,
        "server_name": "your-domain.com",
        "certificate_path": "/etc/sing-box/cert.pem",
        "key_path": "/etc/sing-box/key.pem"
      }
    }
  ],
  "outbounds": [
    {
      "type": "direct",
      "tag": "direct"
    }
  ],
  "route": {
    "rules": [
      {
        "domain": ["geosite:cn"],
        "outbound": "direct"
      }
    ]
  }
}
```

### Advanced Routing with GeoIP

For production use, GeoIP-based routing lets you send domestic traffic directly while proxying international traffic:

```json
{
  "route": {
    "geoip": {
      "path": "/etc/sing-box/geoip.db",
      "download_url": "https://github.com/SagerNet/sing-geoip/releases/latest/download/geoip.db"
    },
    "geosite": {
      "path": "/etc/sing-box/geosite.db",
      "download_url": "https://github.com/SagerNet/sing-geosite/releases/latest/download/geosite.db"
    },
    "rules": [
      {
        "geoip": ["cn"],
        "outbound": "direct"
      },
      {
        "geosite": ["category-ads-all"],
        "outbound": "block"
      },
      {
        "protocol": ["dns"],
        "outbound": "dns-out"
      }
    ]
  },
  "outbounds": [
    { "type": "direct", "tag": "direct" },
    { "type": "block", "tag": "block" },
    {
      "type": "dns",
      "tag": "dns-out"
    }
  ]
}
```

## Xray-Core: The Project X Continuation

[Xray-Core](https://github.com/XTLS/Xray-core) is the most widely deployed proxy core in the V2Ray ecosystem. It's a fork of the original V2Ray that adds the XTLS protocol (REALITY), improved performance, and broader protocol support. If you're already invested in the V2Ray/Xray ecosystem with existing client configurations, Xray-Core is the natural choice.

**Key features:**

- **REALITY protocol** — TLS-based proxy that mimics legitimate websites (no certificate needed)
- **VLESS protocol** — lightweight, stateless protocol with minimal overhead
- **XTLS direct mode** — near-native TLS performance for encryption
- **Large ecosystem** — compatible with dozens of third-party clients and management panels
- **Active development** — regular updates with new protocol features

### Docker Compose Setup

```yaml
version: "3"
services:
  xray:
    image: teddysun/xray:latest
    container_name: xray
    restart: unless-stopped
    network_mode: "host"
    volumes:
      - ./config.json:/etc/xray/config.json:ro
      - ./certs:/etc/xray/certs:ro
```

A VLESS + REALITY configuration (no certificate required):

```json
{
  "inbounds": [
    {
      "port": 443,
      "protocol": "vless",
      "settings": {
        "clients": [
          {
            "id": "your-uuid-here",
            "flow": "xtls-rprx-vision"
          }
        ],
        "decryption": "none"
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "dest": "www.microsoft.com:443",
          "serverNames": ["www.microsoft.com"],
          "privateKey": "your-private-key",
          "shortId": [""]
        }
      }
    }
  ],
  "outbounds": [
    {
      "protocol": "freedom",
      "tag": "direct"
    }
  ]
}
```

## Hysteria2: High-Performance QUIC Proxy

[Hysteria2](https://github.com/apernet/hysteria) is fundamentally different from Sing-Box and Xray-Core. Rather than supporting many protocols, it focuses on doing one thing exceptionally well: delivering high throughput over lossy, high-latency networks using the QUIC protocol.

**Key features:**

- **QUIC-based transport** — UDP protocol with built-in congestion control
- **Bandwidth estimation** — automatically adapts to network conditions
- **Obfuscation** — optional password-based obfuscation layer
- **Simplicity** — minimal configuration, single binary
- **Performance** — consistently outperforms TCP-based proxies on lossy connections

### Docker Compose Setup

```yaml
version: "3"
services:
  hysteria2:
    image: ghcr.io/apernet/hysteria:latest
    container_name: hysteria2
    restart: unless-stopped
    network_mode: "host"
    volumes:
      - ./config.yaml:/etc/hysteria/config.yaml:ro
      - ./cert.pem:/etc/hysteria/cert.pem:ro
      - ./key.pem:/etc/hysteria/key.pem:ro
```

```yaml
# Hysteria2 server config (YAML)
listen: :443
obfs:
  type: salamander
  salamander:
    password: "your-obfs-password"
auth:
  type: password
  password: "your-auth-password"
tls:
  cert: /etc/hysteria/cert.pem
  key: /etc/hysteria/key.pem
quic:
  initStreamReceiveWindow: 8388608
  maxStreamReceiveWindow: 8388608
  initConnReceiveWindow: 20971520
  maxConnReceiveWindow: 20971520
bandwidth:
  up: 100 mbps
  down: 100 mbps
```

## When to Use Each Platform

### Choose Sing-Box When:

- You need **multiple protocols** running from a single instance
- You want **built-in DNS resolution** without a separate DNS server
- You need **GeoIP/GeoSite routing** for domestic vs. international traffic
- You want **official client apps** across all platforms (Android, iOS, desktop)
- You prefer a **clean, well-documented** codebase in Go

### Choose Xray-Core When:

- You're already in the **V2Ray/Xray ecosystem** with existing setups
- You need **REALITY protocol** for certificate-less TLS disguise
- You use **third-party management panels** (3X-UI, X-UI) that support Xray
- You want the **largest community** and most troubleshooting resources
- You need **XTLS** for near-native TLS performance

### Choose Hysteria2 When:

- You're on a **high-latency, lossy network** (satellite, mobile, international)
- You want the **simplest possible configuration**
- You need **maximum throughput** over a single connection
- You don't need multi-protocol support — just one fast tunnel
- You're willing to trade protocol variety for raw performance

## Why Self-Host a Proxy Platform?

Running your own proxy server gives you full control over your network traffic. Commercial VPN services log your activity, inject ads, or sell bandwidth. Self-hosted proxy platforms eliminate these concerns — you control the server, the logs, and the encryption.

**No traffic logging** means no company can sell your browsing habits or hand them over to third parties. With a self-hosted proxy, the only person who can see your traffic is you (and the server admin, which is also you).

**Protocol flexibility** is the key advantage of universal platforms like Sing-Box. Instead of deploying separate Shadowsocks, Trojan, and WireGuard instances — each with its own config, port, and maintenance overhead — one binary handles everything. This reduces attack surface, simplifies firewall rules, and makes troubleshooting easier.

**Performance control** lets you tune buffer sizes, concurrency limits, and transport parameters for your specific network. Commercial services use generic settings optimized for the average user; self-hosting lets you optimize for your actual conditions.

For related network routing topics, see our [Shadowsocks vs V2Ray vs Trojan vs Hysteria comparison](../2026-04-22-shadowsocks-vs-v2ray-vs-trojan-vs-hysteria-self-hosted-prox/) and our [Gost vs 3proxy vs Microsocks guide](../2026-04-27-gost-vs-3proxy-vs-microsocks-self-hosted-proxy-servers-guid/). For VPN management interfaces, our [WireGuard management comparison](../wg-easy-vs-wireguard-ui-vs-wg-gen-web-self-hosted-wireguard-management/) covers setup tools.

## FAQ

### What is the difference between Sing-Box and V2Ray/Xray?

Sing-Box is a universal proxy platform designed from scratch to support multiple protocols with a unified configuration model. V2Ray/Xray started as a VMess-focused tool and added protocols over time. Sing-Box has cleaner architecture, official client apps, and built-in DNS resolution. Xray-Core has a larger ecosystem and the REALITY protocol for certificate-less TLS disguise.

### Is Sing-Box legal to self-host?

The software itself is open-source and legal in most jurisdictions. However, using a proxy to bypass government censorship or access geo-restricted content may violate local laws. Always check your jurisdiction's regulations before deploying a proxy server. The tool is commonly used for legitimate purposes like securing public WiFi traffic, accessing home lab services remotely, or testing network configurations.

### How do I get TLS certificates for my proxy server?

Use Let's Encrypt with cert-manager or acme.sh for free, automated certificates. Sing-Box requires the certificate and key paths in its TLS configuration. For REALITY protocol (Xray-Core), no certificate is needed — the proxy mimics a real website's TLS handshake. For Hysteria2, you need a valid certificate since QUIC requires TLS.

### Can Sing-Box replace my VPN?

For individual use, yes — Sing-Box can route all your traffic through a self-hosted server, providing the same encryption and IP masking as a commercial VPN. However, it lacks some VPN features like split tunneling at the OS level (beyond what the app provides) and kill switch integration. For multi-user scenarios, consider pairing Sing-Box with a proper VPN management interface.

### How much bandwidth does a self-hosted proxy use?

The proxy itself uses minimal bandwidth for overhead (typically under 1% of total traffic). Your actual bandwidth consumption depends on what you route through it. Streaming video through a proxy uses the same bandwidth as streaming directly — the proxy adds negligible overhead. However, if you're on a metered VPS connection, monitor your usage carefully.

### Can I run Sing-Box behind a reverse proxy like Nginx or Caddy?

Yes, but with limitations. Sing-Box can handle TLS termination directly, which is the recommended approach for most protocols. However, if you're sharing port 443 with a web server, you can use SNI-based routing (e.g., Caddy or HAProxy) to direct traffic to the correct backend based on the requested domain name. Our [SNI proxy guide](../2026-04-26-sniproxy-vs-haproxy-vs-caddy-self-hosted-sni-proxy-tls-rout/) covers this pattern in detail.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Sing-Box vs Xray-Core vs Hysteria2: Best Self-Hosted Universal Proxy Platform 2026",
  "description": "Compare Sing-Box, Xray-Core, and Hysteria2 as self-hosted universal proxy platforms. Includes Docker Compose configs, protocol comparison, and routing setup guides.",
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
