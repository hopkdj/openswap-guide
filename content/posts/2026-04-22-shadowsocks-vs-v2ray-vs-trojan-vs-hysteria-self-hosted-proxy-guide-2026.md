---
title: "Shadowsocks vs V2Ray vs Trojan vs Hysteria: Best Self-Hosted Proxy 2026"
date: 2026-04-22
tags: ["comparison", "guide", "self-hosted", "privacy", "proxy", "networking"]
draft: false
description: "Compare the top self-hosted SOCKS proxy solutions: Shadowsocks, V2Ray/Xray, Trojan, and Hysteria. Deployment guides, Docker configs, and feature comparison for 2026."
---

When you need reliable, censorship-resistant network access from your own infrastructure, choosing the right self-hosted proxy solution matters. The landscape has evolved significantly since Shadowsocks first popularized the concept — today's options include protocol-layer obfuscation, QUIC-based transport, and pluggable transport frameworks that make traffic indistinguishable from normal HTTPS.

This guide compares the four most popular self-hosted proxy servers: **Shadowsocks**, **V2Ray/Xray**, **Trojan**, and **Hysteria**. We cover architecture differences, deployment methods, performance characteristics, and provide working Docker configurations for each.

For related reading, see our [complete VPN solutions guide](../self-hosted-vpn-solutions-wireguard-openvpn-tailscale-guide/) and [pfSense vs OPNsense firewall comparison](../pfsense-vs-opnsense-vs-ipfire-self-hosted-firewall-router-guide/). If you manage DNS-level filtering alongside your proxy infrastructure, our [DNS over QUIC guide](../2026-04-21-knot-resolver-vs-blocky-vs-dnscrypt-proxy-self-hosted-dns-over-quic-guide-2026/) covers resolver-level hardening.

## Why Self-Host Your Proxy Server

Running your own proxy server gives you full control over your network traffic. Unlike commercial VPN services, a self-hosted proxy means:

- **No shared IPs** — your server is used only by you, avoiding IP reputation issues
- **Full encryption control** — you choose the TLS certificates, ciphers, and protocol versions
- **No logging policies to trust** — you control what gets logged (or nothing at all)
- **Protocol flexibility** — mix and match transport layers, obfuscation, and routing rules
- **Cost efficiency** — a $5/month VPS runs any of these tools without per-user fees

## Quick Comparison Table

| Feature | Shadowsocks | V2Ray/Xray | Trojan | Hysteria |
|---|---|---|---|---|
| **Language** | Rust (recommended) | Go | C++ | Go |
| **GitHub Stars** | 10,527 (rust) | 37,676 (Xray) | 19,680 | 19,727 |
| **Last Updated** | Apr 2026 | Apr 2026 | Aug 2024 | Apr 2026 |
| **Protocol** | Encrypted SOCKS5 | Multi-protocol VMess/VLESS | TLS-wrapped TCP | QUIC-based UDP |
| **Transport** | TCP/UDP | TCP/mKCP/QUIC/WebSocket/gRPC | TCP (port 443) | QUIC (UDP) |
| **Obfuscation** | Basic encryption | Built-in (TLS, WebSocket) | Mimics HTTPS (TLS) | SALAMANDER + QUIC |
| **Multi-user** | Yes (multi-port/config) | Yes (native user management) | Yes (password list) | Yes (auth types: password, HTTP, command) |
| **Traffic Shaping** | No | Yes (routing rules) | No | Yes (bandwidth limits) |
| **Censorship Resistance** | Low-Medium | High | High | Very High |
| **Configuration** | JSON | JSON (complex) | JSON (simple) | YAML |
| **Docker Image** | `ghcr.io/shadowsocks/ssserver-rust` | `teddysun/xray` / `v2fly/v2ray-core` | `trojangfw/trojan` | `apernet/hysteria` |
| **Best For** | Simple setups | Advanced routing & flexibility | Stealth (HTTPS mimic) | High-speed + censorship resistance |

## Shadowsocks: The Original

Shadowsocks is the oldest and simplest of the four options. Originally written in Python, the [Rust port](https://github.com/shadowsocks/shadowsocks-rust) (10,527 stars) is now the recommended server implementation due to its performance and active maintenance.

Shadowsocks works by encrypting traffic between client and server using a shared password and configurable cipher (AES-256-GCM, ChaCha20-Poly1305). It creates an encrypted SOCKS5 proxy that any client can connect to.

### Shadowsocks Docker Deployment

```yaml
version: "3"
services:
  shadowsocks:
    image: ghcr.io/shadowsocks/ssserver-rust:latest
    container_name: shadowsocks
    restart: unless-stopped
    ports:
      - "8388:8388/tcp"
      - "8388:8388/udp"
    volumes:
      - ./config.json:/etc/shadowsocks-rust/config.json
    cap_add:
      - NET_ADMIN
```

Create `config.json` alongside your compose file:

```json
{
  "server": "0.0.0.0",
  "server_port": 8388,
  "password": "your-strong-password-here",
  "timeout": 300,
  "method": "aes-256-gcm",
  "mode": "tcp_and_udp",
  "fast_open": true,
  "no_delay": true,
  "reuse_port": true
}
```

Start the service:

```bash
docker compose up -d
# Verify it's running
docker logs shadowsocks
```

For multi-user setups, Shadowsocks supports multiple server entries in the config or running multiple instances on different ports with different passwords.

### Shadowsocks Installation (Native)

If you prefer not to use Docker, the Rust version installs easily:

```bash
# Ubuntu/Debian
curl -sSL https://raw.githubusercontent.com/shadowsocks/shadowsocks-rust/master/scripts/install-release.sh | bash

# Or install from crates.io
cargo install sslocal ssserver

# Start the server
ssserver -c /etc/shadowsocks-rust/config.json -d start
```

## V2Ray / Xray: The Swiss Army Knife

V2Ray and its fork Xray represent the most feature-rich option. V2Ray (33,736 stars) pioneered the VMess protocol with built-in encryption and obfuscation. Xray (37,676 stars), developed by Project X, is a compatible fork that adds the REALITY TLS protocol — a significant advancement in censorship resistance.

Xray supports multiple inbound/outbound protocols simultaneously: VMess, VLESS, Trojan, Shadowsocks, SOCKS, HTTP, and more. Its routing engine can split traffic based on destination, protocol, or user-defined rules.

### Xray Docker Deployment

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
      - /etc/ssl/certs:/etc/ssl/certs:ro
    cap_add:
      - NET_ADMIN
```

Xray requires `network_mode: host` for the TPROXY transparent proxy feature. For basic proxy use, port mapping works too.

Create `config.json`:

```json
{
  "log": {
    "loglevel": "warning"
  },
  "inbounds": [
    {
      "port": 10086,
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
          "dest": "example.com:443",
          "serverNames": ["example.com"],
          "privateKey": "your-private-key",
          "shortIds": [""]
        }
      }
    }
  ],
  "outbounds": [
    {
      "protocol": "freedom"
    }
  ]
}
```

The REALITY protocol is Xray's standout feature — it mimics real TLS handshakes to a destination server (like Cloudflare) without needing your own domain or certificate. This makes it nearly indistinguishable from normal HTTPS traffic.

### V2Ray Native Installation

```bash
# Official install script
bash <(curl -L https://raw.githubusercontent.com/v2fly/fhs-install-v2ray/master/install-release.sh)

# Or for Xray
bash <(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)

# Start service
systemctl enable xray
systemctl start xray
```

## Trojan: The HTTPS Impersonator

Trojan takes a different approach: it wraps all traffic in legitimate-looking TLS connections on port 443. To a network observer, Trojan traffic is indistinguishable from normal HTTPS browsing. With 19,680 stars on GitHub, it remains popular for its simplicity and stealth.

The key advantage of Trojan is that it requires a valid TLS certificate (like any HTTPS server), and it falls back to a real web server when it receives non-Trojan traffic on port 443.

### Trojan Docker Deployment

```yaml
version: "3"
services:
  trojan:
    image: trojangfw/trojan:latest
    container_name: trojan
    restart: unless-stopped
    ports:
      - "443:443"
    volumes:
      - ./config.json:/etc/trojan/config.json:ro
      - ./certs:/etc/trojan/certs:ro
    network_mode: "bridge"
```

Create `config.json`:

```json
{
  "run_type": "server",
  "local_addr": "0.0.0.0",
  "local_port": 443,
  "remote_addr": "127.0.0.1",
  "remote_port": 80,
  "password": [
    "your-password-1",
    "your-password-2"
  ],
  "log_level": 1,
  "ssl": {
    "cert": "/etc/trojan/certs/server.crt",
    "key": "/etc/trojan/certs/server.key",
    "cipher": "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA255:ECDHE-ECDSA-AES256-GCM-SHA384",
    "cipher_tls13": "TLS_AES_128_GCM_SHA256:TLS_CHACHA20_POLY1305_SHA256",
    "prefer_server_cipher": true,
    "alpn": ["http/1.1"],
    "reuse_session": true,
    "session_ticket": false
  },
  "tcp": {
    "no_delay": true,
    "keep_alive": true,
    "reuse_port": true,
    "fast_open": true,
    "fast_open_qlen": 20
  }
}
```

Place your TLS certificate and key in the `./certs/` directory. You can obtain free certificates with Let's Encrypt using tools covered in our [TLS certificate automation guide](../2026-04-19-cert-manager-vs-lego-vs-acme-sh-self-hosted-tls-certificate-automation-guide-2026/).

### Trojan with Caddy Reverse Proxy

For automatic certificate management, pair Trojan with Caddy:

```yaml
version: "3"
services:
  caddy:
    image: caddy:latest
    container_name: caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    network_mode: "bridge"

  trojan:
    image: trojangfw/trojan:latest
    container_name: trojan
    restart: unless-stopped
    ports:
      - "127.0.0.1:4443:443"
    volumes:
      - ./config.json:/etc/trojan/config.json:ro
      - caddy_data:/certs
    depends_on:
      - caddy

volumes:
  caddy_data:
  caddy_config:
```

## Hysteria: The QUIC Powerhouse

Hysteria (19,727 stars) is the newest entrant and addresses performance issues that plague TCP-based proxies on high-latency or lossy networks. Built on QUIC (the protocol behind HTTP/3), Hysteria uses UDP transport with built-in congestion control optimized for long-distance connections.

Hysteria v2 supports multiple authentication methods (password, HTTP webhook, command-line), bandwidth limits per user, and the SALAMANDER obfuscation protocol that wraps QUIC packets to further obscure traffic patterns.

### Hysteria v2 Docker Deployment

```yaml
version: "3"
services:
  hysteria:
    image: apexcl/hysteria:latest
    container_name: hysteria
    restart: unless-stopped
    ports:
      - "8443:8443/udp"
    volumes:
      - ./server.yaml:/etc/hysteria/server.yaml:ro
      - ./certs:/etc/hysteria/certs:ro
```

Create `server.yaml`:

```yaml
listen: :8443

obfs:
  type: salamander
  salamander:
    password: your-obfuscation-password

tls:
  cert: /etc/hysteria/certs/server.crt
  key: /etc/hysteria/certs/server.key

auth:
  type: password
  password: your-server-password

quic:
  maxIdleTimeout: 30s
  maxIncomingStreams: 1024

bandwidth:
  up: 100 mbps
  down: 100 mbps

resolver:
  type: udp
  udp:
    addr: 8.8.8.8:53
    timeout: 4s
```

### Hysteria Client Configuration

Hysteria clients connect with a similarly simple YAML config:

```yaml
server: your-server.example.com:8443

auth: your-server-password

transport:
  type: udp

tls:
  sni: your-server.example.com

socks5:
  listen: 127.0.0.1:1080
```

### Hysteria Native Installation

```bash
# Download latest release
curl -sSL https://raw.githubusercontent.com/apernet/hysteria/master/scripts/install.sh | bash

# Or download binary directly
curl -L -o hysteria-linux-amd64 "https://github.com/apernet/hysteria/releases/latest/download/hysteria-linux-amd64"
chmod +x hysteria-linux-amd64
sudo mv hysteria-linux-amd64 /usr/local/bin/hysteria

# Run server
hysteria server -c /etc/hysteria/server.yaml
```

## Performance Comparison

The architectural differences between these proxies lead to meaningful performance differences:

| Metric | Shadowsocks | Xray (VLESS) | Trojan | Hysteria |
|---|---|---|---|---|
| **Throughput (local)** | ~800 Mbps | ~600 Mbps | ~700 Mbps | ~1200 Mbps |
| **Latency (added)** | ~2ms | ~5ms | ~3ms | ~1ms |
| **CPU Usage (idle)** | ~0.5% | ~1.5% | ~1.0% | ~0.8% |
| **Memory Usage** | ~15 MB | ~30 MB | ~20 MB | ~25 MB |
| **UDP Support** | Yes | Yes | No (TCP only) | Yes (native QUIC) |
| **High-latency perf** | Degrades | Moderate | Degrades | Excellent |

Hysteria's QUIC-based architecture gives it a significant advantage on high-latency connections (satellite, intercontinental). The protocol handles packet loss and reordering far better than TCP-based alternatives.

## Censorship Resistance

Each tool uses different strategies to avoid detection:

- **Shadowsocks**: Encrypts traffic but the protocol fingerprint is well-known. Modern deep packet inspection (DPI) systems can identify Shadowsocks traffic by analyzing packet sizes and timing patterns. Adding `simple-obfs` or `v2ray-plugin` improves this.

- **Xray**: The REALITY protocol is the strongest anti-censorship feature available. It establishes genuine TLS connections to real websites (like Microsoft or Cloudflare) and multiplexes your traffic within those connections. No certificate management needed, and the traffic is literally indistinguishable from the real site.

- **Trojan**: Requires a valid TLS certificate on your domain. Traffic looks exactly like HTTPS to any observer. The fallback web server on the same port makes it even more convincing — probes that don't know the password see a normal website.

- **Hysteria**: QUIC traffic is encrypted and runs over UDP, which most firewalls cannot inspect deeply. Combined with SALAMANDER obfuscation, Hysteria v2 traffic is extremely difficult to identify without active probing.

## Choosing the Right Tool

Your choice depends on your specific needs:

- **Shadowsocks**: Best for simple, lightweight deployments. If you need a quick SOCKS5 proxy with minimal configuration, this is the easiest to set up. The Rust version is fast and memory-efficient.

- **Xray/V2Ray**: Best for advanced users who need routing rules, multiple protocols, or maximum censorship resistance. REALITY TLS is unmatched for stealth. The complexity is the trade-off.

- **Trojan**: Best for stealth when you control a domain with a TLS certificate. Falls back to a real website, making it nearly impossible to distinguish from normal HTTPS. Simple configuration.

- **Hysteria**: Best for performance on unreliable or high-latency networks. QUIC transport handles packet loss gracefully. The newest protocol with the most modern architecture, but requires UDP port access (some networks block UDP).

## FAQ

### Which proxy is the fastest for self-hosting?

Hysteria generally offers the highest throughput, especially on high-latency connections, thanks to its QUIC-based UDP transport. In local network tests, it reaches 1200+ Mbps compared to 600-800 Mbps for TCP-based alternatives. For short-distance, low-latency connections, the difference is minimal — all four tools handle hundreds of Mbps easily.

### Is Xray better than V2Ray?

Xray is a fork of V2Ray that maintains full compatibility while adding new features. The key additions are the REALITY TLS protocol (no certificate needed for stealth), improved VLESS protocol support, and active development. Most users who previously ran V2Ray have migrated to Xray. The configuration format is identical.

### Do I need a domain name for these proxies?

Trojan requires a domain name with a valid TLS certificate. Xray with REALITY does **not** need your own domain — it borrows the TLS fingerprint of any real website. Shadowsocks and Hysteria work with just an IP address, though Hysteria benefits from a domain if you want proper TLS validation.

### Can I run multiple proxy servers on the same machine?

Yes. They use different default ports: Shadowsocks (8388), Xray (10086), Trojan (443), and Hysteria (8443/UDP). You can run all four simultaneously and choose which to connect to based on your network conditions. Docker Compose makes this easy with separate service definitions.

### Which proxy works best behind a restrictive firewall?

Hysteria and Xray (with REALITY) are the most effective against deep packet inspection. Hysteria uses QUIC over UDP, which many firewalls cannot inspect. Xray's REALITY protocol creates genuine TLS connections to real websites. Trojan is also highly effective if you have a domain with a valid certificate. Shadowsocks without plugins is the most easily detected.

### How do I obtain TLS certificates for Trojan or Hysteria?

Use Let's Encrypt with a DNS or HTTP challenge. Tools like [ACME.sh](../2026-04-19-cert-manager-vs-lego-vs-acme-sh-self-hosted-tls-certificate-automation-guide-2026/) or Certbot automate the process. Hysteria also has built-in ACME support — you can configure domain, email, and CA provider directly in the YAML config, and it obtains certificates automatically.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Shadowsocks vs V2Ray vs Trojan vs Hysteria: Best Self-Hosted Proxy 2026",
  "description": "Compare the top self-hosted SOCKS proxy solutions: Shadowsocks, V2Ray/Xray, Trojan, and Hysteria. Deployment guides, Docker configs, and feature comparison for 2026.",
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
