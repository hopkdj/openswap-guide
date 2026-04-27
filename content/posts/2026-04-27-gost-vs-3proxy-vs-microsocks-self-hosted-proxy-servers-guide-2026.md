
---
title: "Gost vs 3proxy vs Microsocks: Best Self-Hosted Proxy Servers 2026"
date: 2026-04-27
tags: ["comparison", "guide", "self-hosted", "proxy", "networking", "privacy"]
draft: false
description: "Compare three lightweight self-hosted proxy servers — Gost, 3proxy, and Microsocks. Includes Docker Compose configs, deployment guides, and a feature comparison table for running your own SOCKS5 and HTTP proxy in 2026."
---

Running your own proxy server gives you full control over network traffic routing, privacy, and access policies. Whether you need a SOCKS5 proxy for secure tunneling, an HTTP forward proxy for web access control, or a multi-protocol gateway that handles both, there are excellent open-source options available.

In this guide, we compare three of the most popular lightweight proxy servers: **Gost** (the GO Simple Tunnel), **3proxy** (a universal multi-protocol proxy), and **Microsocks** (a minimal SOCKS5 server). Each serves a different use case — from full-featured multi-protocol routing to bare-bones SOCKS5 service — and we'll show you exactly how to deploy all three with Docker.

For a broader look at self-hosted proxy options, check out our [web proxy guide covering Squid, Tinyproxy, and Caddy](../self-hosted-web-proxy-squid-tinyproxy-caddy-guide/), as well as our [comparison of tunnel alternatives like frp and chisel](../frp-vs-chisel-vs-rathole-self-hosted-tunnel-ngrok-alternatives-2026/). If you're interested in censorship-resistant proxy protocols, our [Shadowsocks vs V2Ray vs Trojan vs Hysteria guide](../shadowsocks-vs-v2ray-vs-trojan-vs-hysteria-self-hosted-proxy-guide-2026/) covers those in depth.

## Why Run Your Own Proxy Server?

Self-hosting a proxy server offers several advantages over commercial alternatives:

- **Complete data privacy** — No third-party logging your browsing habits, connection metadata, or DNS queries.
- **Protocol flexibility** — Run SOCKS5, HTTP, HTTPS, TCP relay, or UDP relay on the same server.
- **Cost control** — No per-GB or per-user pricing. Run on a $5/month VPS with unlimited bandwidth.
- **Custom routing rules** — Route specific domains, IPs, or applications through different upstream proxies.
- **No vendor lock-in** — Open-source software means you control the configuration, upgrades, and migration path.

## Gost: The Multi-Protocol Swiss Army Knife

[Gost](https://github.com/ginuerzh/gost) (GO Simple Tunnel) is the most feature-rich option in this comparison. Written in Go, it supports an impressive range of protocols including SOCKS5, HTTP/HTTPS, TCP relay, UDP relay, port forwarding, and tunnel chaining. It also supports transport-level encryption (TLS, KCP, QUIC, WebSocket, HTTP/2) and can chain multiple proxy hops together.

The original repository has **17,880 stars** on GitHub, and there is also an actively maintained fork at [go-gost/gost](https://github.com/go-gost/gost) with **6,708 stars** that continues development.

### Key Features

- **Multi-protocol support**: SOCKS5, HTTP, HTTPS, TCP, UDP, SNI proxy
- **Transport encryption**: TLS, KCP, QUIC, WebSocket, HTTP/2, gRPC
- **Proxy chaining**: Chain multiple proxy nodes for multi-hop routing
- **Load balancing**: Distribute traffic across multiple upstream proxies
- **Port forwarding**: Local and remote port forwarding (like SSH -L/-R)
- **Traffic sniffing**: Built-in traffic analysis and logging
- **Single binary**: No runtime dependencies — one static Go binary

### Docker Deployment

Gost does not ship an official docker-compose.yml, but the official Docker image makes deployment straightforward. Here is a complete compose setup for running Gost as a SOCKS5 proxy:

```yaml
version: "3.8"

services:
  gost:
    image: gogost/gost:latest
    container_name: gost-proxy
    restart: unless-stopped
    ports:
      - "1080:1080"   # SOCKS5
      - "8080:8080"   # HTTP proxy
    command: >
      -L=socks5://:1080
      -L=http://:8080
      -L=tcp://:8443/destination.example.com:443
    environment:
      - TZ=UTC
    volumes:
      - ./gost-config:/etc/gost
      - ./certs:/etc/gost/certs:ro
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

For authenticated access, you can pass credentials directly in the listener string:

```yaml
    command: >
      -L=socks5://admin:secret@:1080
      -L=http://admin:secret@:8080
```

### Advanced: TLS-Encrypted SOCKS5 Proxy

Gost can wrap SOCKS5 in TLS for encrypted transport — useful when running a proxy over an untrusted network:

```yaml
    command: >
      -L=socks5+tls://:1080?cert=/etc/gost/certs/server.crt&key=/etc/gost/certs/server.key
      -L=http+tls://:8080?cert=/etc/gost/certs/server.crt&key=/etc/gost/certs/server.key
```

### Proxy Chaining Example

One of Gost's standout features is the ability to chain proxies. Here is how to configure a two-hop chain:

```bash
gost -L=:1080 -F=socks5://node1:1080 -F=socks5://node2:1080
```

This routes traffic through `node1` and then `node2` before reaching the destination — useful for privacy or bypassing geo-restrictions.

## 3proxy: The Universal Proxy Server

[3proxy](https://github.com/z3APA3A/3proxy) is a compact, multi-protocol proxy server written in C. Despite its small footprint, it supports a wide range of proxy types: SOCKS4/SOCKS5, HTTP, HTTPS, FTP, POP3, SMTP, and TCP port mapping. It has **5,115 GitHub stars** and is actively maintained — the repository was updated as recently as April 2026.

### Key Features

- **Protocol diversity**: SOCKS4/5, HTTP/HTTPS, FTP, POP3, SMTP proxy
- **ACL support**: Access control lists with IP, time, and user-based rules
- **Bandwidth limiting**: Per-user and per-connection bandwidth throttling
- **Transparent proxy**: Can operate as a transparent proxy with iptables redirection
- **Plugin architecture**: Extensible via loadable modules (SSLPlugin, SOCKS plugin, etc.)
- **Low memory footprint**: Runs comfortably on 64 MB of RAM
- **Cross-platform**: Compiles and runs on Linux, Windows, FreeBSD, and macOS

### Docker Deployment

3proxy provides two Docker images: a minimal busybox-based build and a fully-featured distroless build. Here is a production-ready Docker Compose setup using the full image:

```yaml
version: "3.8"

services:
  3proxy:
    image: 3proxy/3proxy:latest
    container_name: 3proxy
    restart: unless-stopped
    read_only: true
    ports:
      - "3128:3128"   # HTTP proxy
      - "1080:1080"   # SOCKS5 proxy
    volumes:
      - ./3proxy.cfg:/etc/3proxy/3proxy.cfg:ro
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

The configuration file (`3proxy.cfg`) is where all the magic happens:

```cfg
# /etc/3proxy/3proxy.cfg

# DNS resolver (required for the minimal image)
nserver 8.8.8.8
nserver 1.1.1.1

# DNS cache
nscache 65536

# Timeouts
timeouts 1 5 30 60 180 1800 15 60

# Log to stdout
log

# Run as daemon
daemon

# HTTP proxy on port 3128
proxy -p3128

# SOCKS5 proxy on port 1080
socks -p1080

# Access control: allow all (restrict in production)
allow * * * 80-88,8080-8088,443,8443,1080,3128 HTTP,SOCKS

# Bandwidth limit: 1 MB/s per connection
bandlimin 1000000 * * *
```

### Docker Run Command (Quick Start)

For a quick test without compose files, you can pipe configuration directly into the container:

```bash
printf "nserver 8.8.8.8\nlog\nproxy -p3128\nsocks -p1080\nallow *\n" | \
  docker run --read-only -i -p 3128:3128 -p 1080:1080 \
  --name 3proxy 3proxy/3proxy:latest
```

### Transparent Proxy Setup

3proxy can operate as a transparent proxy, intercepting traffic via iptables without requiring client-side configuration:

```bash
# Redirect all HTTP traffic to 3proxy
iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 3128
iptables -t nat -A PREROUTING -p tcp --dport 443 -j REDIRECT --to-port 3128
```

Add `transparent` to the proxy line in the config:

```cfg
proxy -p3128 -a -n
```

## Microsocks: The Minimal SOCKS5 Server

[Microsocks](https://github.com/rofl0r/microsocks) takes a different philosophy: do one thing and do it with minimal overhead. It is a multithreaded SOCKS5 server written in C, designed to be as lightweight as possible. At **2,084 GitHub stars**, it is the smallest project in this comparison, but it excels at its single purpose.

### Key Features

- **Extremely lightweight**: Uses minimal RAM and CPU — ideal for resource-constrained environments
- **Thread-per-client model**: Each connection gets a dedicated thread with low stack allocation
- **Authentication**: Supports username/password SOCKS5 authentication
- **IPv6 support**: Full IPv6 compatibility
- **No configuration files**: All settings passed via command-line arguments
- **Portable**: Compiles on virtually any Unix-like system
- **Single binary**: No dependencies, no runtime, just one executable

### Docker Deployment

Microsocks does not have an official Docker image on Docker Hub, but building one is trivial. Here is a complete Docker Compose setup that builds from source:

```yaml
version: "3.8"

services:
  microsocks:
    build:
      context: .
      dockerfile: Dockerfile.microsocks
    container_name: microsocks
    restart: unless-stopped
    ports:
      - "1080:1080"
    environment:
      - MS_USER=proxyuser
      - MS_PASS=proxypass
      - MS_PORT=1080
    logging:
      driver: json-file
      options:
        max-size: "1m"
        max-file: "2"
```

The corresponding Dockerfile (`Dockerfile.microsocks`):

```dockerfile
FROM alpine:3.20 AS builder

RUN apk add --no-cache build-base git
RUN git clone https://github.com/rofl0r/microsocks.git /src && \
    cd /src && make

FROM alpine:3.20
RUN apk add --no-cache libgcc
COPY --from=builder /src/microsocks /usr/local/bin/microsocks

ENV MS_PORT=1080
EXPOSE 1080

ENTRYPOINT ["microsocks"]
CMD ["-1", "-p", "${MS_PORT}"]
```

### Quick Start with Pre-built Image

A community Docker image is available that simplifies deployment:

```bash
docker run -d --name microsocks \
  -p 1080:1080 \
  --restart unless-stopped \
  ghcr.io/rofl0r/microsocks:latest \
  -1 -p 1080 -u proxyuser -P proxypass
```

The flags mean:
- `-1`: Single-hop mode (no upstream chaining)
- `-p 1080`: Listen on port 1080
- `-u proxyuser`: Set SOCKS5 username
- `-P proxypass`: Set SOCKS5 password

### Resource Usage

Microsocks is designed for environments where every megabyte counts:

- **Memory**: ~2 MB RSS for the main process, ~128 KB per client thread
- **CPU**: Near-zero idle usage; scales linearly with active connections
- **Disk**: ~50 KB binary size

This makes it ideal for embedded devices, containers with strict resource limits, or situations where you just need a SOCKS5 endpoint with no frills.

## Head-to-Head Comparison

| Feature | Gost | 3proxy | Microsocks |
|---|---|---|---|
| **Protocols** | SOCKS5, HTTP, HTTPS, TCP, UDP, SNI | SOCKS4/5, HTTP, FTP, POP3, SMTP | SOCKS5 only |
| **Transport Encryption** | TLS, KCP, QUIC, WS, HTTP/2, gRPC | SSL (via plugin) | None |
| **Proxy Chaining** | Yes (multi-hop) | Yes (via parent) | No |
| **Load Balancing** | Yes | No | No |
| **Access Control** | CLI flags / config | Full ACL system | Username/password only |
| **Bandwidth Limiting** | Yes | Yes | No |
| **Transparent Proxy** | Yes | Yes | No |
| **Official Docker Image** | Yes (`gogost/gost`) | Yes (`3proxy/3proxy`) | No (community only) |
| **Docker Compose** | Create your own | Create your own | Create your own |
| **Binary Size** | ~30 MB (static Go) | ~500 KB | ~50 KB |
| **Memory Usage** | ~20 MB idle | ~4 MB idle | ~2 MB idle |
| **GitHub Stars** | 17,880 | 5,115 | 2,084 |
| **Last Updated** | Dec 2024 | Apr 2026 | Feb 2025 |
| **License** | MIT | Mixed | MIT |

## Choosing the Right Proxy Server

### Choose Gost When:

- You need **multiple protocols** on a single server (SOCKS5 + HTTP + TCP relay)
- **Transport encryption** matters — you want TLS, QUIC, or WebSocket wrapping
- You need **proxy chaining** for multi-hop routing
- You want **load balancing** across multiple upstream proxies
- You prefer a **single Go binary** with no system dependencies

### Choose 3proxy When:

- You need **SOCKS4 support** alongside SOCKS5
- You want **FTP, POP3, or SMTP proxy** capabilities
- You need **fine-grained ACLs** with IP, user, and time-based rules
- **Transparent proxy** mode is required for network-level interception
- You want a **battle-tested C implementation** that runs on minimal hardware

### Choose Microsocks When:

- You need **only SOCKS5** and nothing else
- **Resource constraints** are critical (embedded devices, minimal containers)
- You want the **smallest possible attack surface**
- Configuration simplicity is preferred over feature depth
- You just need a quick SOCKS5 endpoint for SSH-like tunneling

## Production Deployment Tips

### Reverse Proxy with Nginx

If you want to expose your proxy over HTTPS, put it behind Nginx:

```nginx
server {
    listen 443 ssl http2;
    server_name proxy.example.com;

    ssl_certificate /etc/ssl/certs/proxy.crt;
    ssl_certificate_key /etc/ssl/private/proxy.key;

    location / {
        proxy_pass http://127.0.0.1:1080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Rate Limiting with iptables

Protect your proxy from abuse with connection rate limiting:

```bash
# Limit new connections to 10 per minute per source IP
iptables -A INPUT -p tcp --dport 1080 -m state --state NEW \
  -m recent --set --name SOCKS
iptables -A INPUT -p tcp --dport 1080 -m state --state NEW \
  -m recent --update --seconds 60 --hitcount 10 --name SOCKS -j DROP
```

### Monitoring Proxy Usage

All three proxies log connection metadata. For centralized log collection, forward logs to your preferred log aggregator. See our guides on [self-hosted log management with Loki and Graylog](../self-hosted-log-management-loki-graylog-opensearch/) and [log shipping with Vector, Fluent Bit, and Logstash](../self-hosted-log-shipping-vector-fluentbit-logstash-guide-2026/) for production-ready setups.

## Conclusion

The choice between Gost, 3proxy, and Microsocks comes down to your specific needs. Gost is the feature powerhouse — if you need multi-protocol support, encryption, and chaining, it is the clear winner. 3proxy strikes a balance between breadth and efficiency, offering the widest protocol support in a compact package. Microsocks is the specialist — if all you need is SOCKS5, nothing comes close in terms of resource efficiency.

All three can be deployed with Docker in under five minutes, making it easy to test each one in your environment before committing to a production setup.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Gost vs 3proxy vs Microsocks: Best Self-Hosted Proxy Servers 2026",
  "description": "Compare three lightweight self-hosted proxy servers — Gost, 3proxy, and Microsocks. Includes Docker Compose configs, deployment guides, and a feature comparison table for running your own SOCKS5 and HTTP proxy in 2026.",
  "datePublished": "2026-04-27",
  "dateModified": "2026-04-27",
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

## FAQ

### What is the difference between Gost, 3proxy, and Microsocks?

Gost is a multi-protocol tunnel and proxy written in Go that supports SOCKS5, HTTP, HTTPS, TCP/UDP relay, proxy chaining, and transport encryption. 3proxy is a compact C-based universal proxy supporting SOCKS4/5, HTTP, FTP, POP3, SMTP, and transparent proxy mode. Microsocks is a minimal SOCKS5-only server focused on extremely low resource usage.

### Can I use Gost or 3proxy as a transparent proxy?

Yes. Both Gost and 3proxy support transparent proxy mode. With 3proxy, add the `-a -n` flags to the proxy line in the config. With Gost, use the `-L=redirect` listener type. Microsocks does not support transparent proxy mode — it only handles explicit SOCKS5 connections.

### Do I need a TLS certificate to run these proxies?

No, but it is recommended. Gost can generate self-signed certificates or use Let's Encrypt certificates for TLS-wrapped connections. 3proxy supports SSL via its SSLPlugin. Microsocks has no built-in TLS support — if you need encryption, place it behind a reverse proxy like Caddy or Nginx.

### How do I add authentication to my proxy server?

Gost supports authentication via the listener string (e.g., `-L=socks5://user:pass@:1080`). 3proxy uses `users` directives in the config file with supported authentication methods. Microsocks uses the `-u` and `-P` flags for SOCKS5 username/password authentication.

### Which proxy server is best for a low-RAM VPS?

Microsocks is the lightest, using approximately 2 MB of RAM idle. 3proxy uses about 4 MB. Gost, being a Go binary, uses around 20 MB idle. For a VPS with 256 MB or less RAM, Microsocks or 3proxy are the best choices.

### Can I chain multiple proxy servers together?

Gost has built-in proxy chaining with the `-F` flag, supporting unlimited hops. 3proxy supports parent proxy chaining via the `parent` directive. Microsocks does not support chaining — it is a single-hop SOCKS5 server only.
