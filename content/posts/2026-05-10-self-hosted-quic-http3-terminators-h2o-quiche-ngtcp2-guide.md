---
title: "Self-Hosted QUIC & HTTP/3 Terminators: h2o vs quiche vs ngtcp2 Guide 2026"
date: 2026-05-10
tags: ["comparison", "guide", "self-hosted", "networking", "quic", "http3", "proxy", "h2o", "tls"]
draft: false
description: "Compare h2o, quiche, and ngtcp2 for self-hosted QUIC and HTTP/3 termination. Complete deployment guide with configuration examples, TLS setup, and reverse proxy patterns."
---

QUIC (Quick UDP Internet Connections) and HTTP/3 represent the next generation of web transport protocols. QUIC operates over UDP instead of TCP, eliminating head-of-line blocking, reducing connection establishment latency, and improving performance on lossy networks. HTTP/3 is the HTTP semantics layer built on top of QUIC.

For self-hosted infrastructure, deploying a QUIC/HTTP/3 terminator enables your services to benefit from these protocol improvements. In this guide, we compare three open-source QUIC implementations: **h2o** (with built-in QUIC support), **quiche** (Cloudflare's QUIC library), and **ngtcp2** (the native QUIC library for NGINX).

## What Is QUIC and HTTP/3?

QUIC was developed by Google and standardized by the IETF as RFC 9000. It combines TLS 1.3 encryption with reliable, ordered transport in a single protocol — eliminating the separate TCP handshake and TLS negotiation steps that add latency to TCP-based connections.

Key advantages over HTTP/2 over TCP:
- **Faster connection establishment**: 0-RTT resumption for returning clients
- **No head-of-line blocking**: Independent streams within a single connection
- **Improved congestion control**: Modern algorithms tuned for modern networks
- **Connection migration**: Seamless handoff between network interfaces (WiFi to cellular)
- **Built-in encryption**: TLS 1.3 is mandatory, no plaintext mode

## h2o Server with QUIC Support

h2o is a high-performance HTTP server with native QUIC and HTTP/3 support. It is one of the few web servers that provides production-ready HTTP/3 out of the box without requiring patching or third-party modules.

### Installation

Build h2o with QUIC support:

```bash
apt-get update && apt-get install -y cmake build-essential libssl-dev libbrotli-dev zlib1g-dev libyaml-dev

git clone --branch v3.0.0 --recursive https://github.com/h2o/h2o.git
cd h2o
cmake -DWITH_BUNDLED_SSL=on .
make -j$(nproc)
make install
```

### QUIC Configuration

Configure `h2o.conf` for HTTP/3:

```yaml
hosts:
  "example.com:443":
    listen:
      port: 443
      ssl:
        certificate-file: /etc/ssl/certs/example.com.crt
        key-file: /etc/ssl/private/example.com.key
    listen:
      port: 443
      quic: true
      ssl:
        certificate-file: /etc/ssl/certs/example.com.crt
        key-file: /etc/ssl/private/example.com.key
    paths:
      "/":
        file.dir: /var/www/html
        redirect:
          url: /index.html
          internal: YES

access-log: /var/log/h2o/access.log
error-log: /var/log/h2o/error.log
pid-file: /var/run/h2o.pid
```

Start h2o:

```bash
h2o -c /etc/h2o/h2o.conf
```

### h2o Docker Compose

```yaml
version: "3.8"
services:
  h2o-quic:
    image: ghcr.io/h2o/h2o:latest
    container_name: h2o-quic
    ports:
      - "80:80"
      - "443:443/tcp"
      - "443:443/udp"
    volumes:
      - ./h2o.conf:/etc/h2o/h2o.conf:ro
      - ./certs:/etc/ssl/certs:ro
      - ./private:/etc/ssl/private:ro
      - ./www:/var/www/html:ro
    restart: unless-stopped
```

Note that QUIC requires both TCP and UDP on port 443 — the Docker Compose file exposes both.

## quiche (Cloudflare's QUIC Implementation)

quiche is Cloudflare's implementation of QUIC and HTTP/3, written in Rust. It is designed as a library that other projects can integrate rather than a standalone server. Cloudflare uses quiche in their production edge infrastructure.

### Integration Pattern

quiche is not a standalone server — it provides QUIC and HTTP/3 protocol handling that you integrate into your own application. Common integration targets include nginx (via the nginx-quic patch), HAProxy, and custom Rust applications.

### Building nginx with quiche

```bash
# Install dependencies
apt-get install -y build-essential libssl-dev libpcre3-dev zlib1g-dev

# Clone nginx with quic support
git clone --branch quic https://github.com/cloudflare/quiche
cd quiche

# Build quiche
cargo build --release

# Clone and patch nginx
git clone https://github.com/nginx/nginx.git
cd nginx
git checkout quic

# Configure with quiche
./auto/configure   --with-http_ssl_module   --with-http_v2_module   --with-http_v3_module   --with-quiche=../quiche   --prefix=/usr/local/nginx

make -j$(nproc)
make install
```

### nginx HTTP/3 Configuration

```nginx
server {
    listen 443 quic reuseport;
    listen 443 ssl;
    http2 on;
    http3 on;

    ssl_certificate     /etc/ssl/certs/example.com.crt;
    ssl_certificate_key /etc/ssl/private/example.com.key;

    # QUIC-specific settings
    quic_retry on;
    
    # ALPN for HTTP/3
    add_header Alt-Svc 'h3=":443"; ma=86400';

    location / {
        proxy_pass http://backend:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## ngtcp2 (QUIC for NGINX)

ngtcp2 is another QUIC implementation, specifically designed for integration with NGINX. It is maintained by the NGINX community and provides a more modular approach than the Cloudflare quiche integration.

### Building NGINX with ngtcp2

```bash
# Install dependencies
apt-get install -y build-essential libssl-dev libnghttp2-dev

# Clone ngtcp2 and nghttp3
git clone https://github.com/ngtcp2/ngtcp2.git
cd ngtcp2
autoreconf -fi
./configure PKG_CONFIG_PATH=/usr/local/lib/pkgconfig --enable-lib-only
make -j$(nproc)
make install

git clone https://github.com/ngtcp2/nghttp3.git
cd nghttp3
autoreconf -fi
./configure --enable-lib-only
make -j$(nproc)
make install

# Build NGINX with ngtcp2
git clone https://github.com/nginx/nginx.git
cd nginx
./auto/configure   --with-http_ssl_module   --with-http_v2_module   --with-http_v3_module   --with-openssl=../openssl   --with-ngtcp2=../ngtcp2   --with-nghttp3=../nghttp3

make -j$(nproc)
make install
```

### ngtcp2 NGINX Configuration

```nginx
server {
    listen 443 quic;
    listen 443 ssl;
    ssl_protocols TLSv1.3;
    
    ssl_certificate     /etc/ssl/certs/example.com.crt;
    ssl_certificate_key /etc/ssl/private/example.com.key;

    http3 on;
    quic_retry on;

    add_header Alt-Svc 'h3=":443"; ma=86400';
    add_header QUIC-Status $quic;

    location / {
        proxy_pass http://127.0.0.1:3000;
    }
}
```

## QUIC/HTTP/3 Comparison

| Feature | h2o | quiche (nginx) | ngtcp2 (nginx) |
|---------|-----|---------------|----------------|
| Language | C | Rust | C |
| Type | Standalone server | Library | Library |
| QUIC version | RFC 9000 | RFC 9000 | RFC 9000 |
| HTTP/3 support | Native | Via nginx-quic patch | Via nginx module |
| TLS integration | Built-in (picotls) | BoringSSL | OpenSSL 3.x |
| 0-RTT support | Yes | Yes | Yes |
| Connection migration | Yes | Yes | Yes |
| Production use | Yes (Fastly, others) | Yes (Cloudflare) | Yes (community) |
| Docker support | Official image | Custom build | Custom build |
| Configuration | YAML | nginx.conf | nginx.conf |
| Reverse proxy | Built-in | Via nginx upstream | Via nginx upstream |

## Why Self-Host QUIC Terminators?

Deploying QUIC/HTTP/3 termination at the edge of your infrastructure improves latency for all downstream services. A single QUIC terminator can serve HTTP/3 traffic while proxying to backend services that only speak HTTP/1.1 or HTTP/2 — clients get the performance benefits without any application changes.

For reverse proxy setups that complement QUIC termination, see our [shadowsocks vs v2ray vs hysteria proxy guide](../2026-04-22-shadowsocks-vs-v2ray-vs-trojan-vs-hysteria-self-hosted-proxy-guide-2026/). For DNS-over-QUIC infrastructure, check our [Knot Resolver vs blocky vs dnscrypt-proxy guide](../2026-04-21-knot-resolver-vs-blocky-vs-dnscrypt-proxy-self-hosted-dns-over-quic-guide-2026/). And for TLS interception and monitoring, our [mitmproxy vs sslsplit vs bettercap comparison](../2026-04-24-mitmproxy-vs-sslsplit-vs-bettercap-self-hosted-tls-interception-guide-2026/) covers security testing tools.

## TLS Certificate Requirements

QUIC requires TLS 1.3, which means you need valid certificates. For self-hosted infrastructure, use Let's Encrypt or a self-hosted CA:

```bash
# Let's Encrypt with certbot
apt-get install -y certbot
certbot certonly --standalone -d example.com --preferred-challenges http

# Auto-renewal
echo "0 0 * * * certbot renew --quiet && systemctl reload h2o" | crontab -
```

For a self-hosted CA, consider [step-ca](https://smallstep.com/docs/step-ca/) which provides an internal PKI with automatic certificate rotation.

## FAQ

### Do I need QUIC on all my servers?

No. Deploy QUIC termination at the edge (reverse proxy or load balancer) and let backend services communicate over HTTP/2 or HTTP/1.1. The QUIC terminator handles protocol translation, so backend services don't need any changes.

### What ports does QUIC use?

QUIC uses UDP port 443 (the same port number as HTTPS). Your server must listen on both TCP 443 (for HTTP/2 fallback) and UDP 443 (for HTTP/3). Ensure your firewall allows UDP traffic on port 443.

### Is HTTP/3 backward compatible with HTTP/2?

Yes. The `Alt-Svc` header advertised by the server tells clients that HTTP/3 is available on UDP port 443. Clients that support HTTP/3 will use it; others fall back to HTTP/2 over TCP. The same TLS certificate works for both.

### Can I use QUIC with self-signed certificates?

QUIC requires TLS 1.3, but it does not require publicly trusted certificates. Self-signed or internally-signed certificates work for self-hosted deployments. Clients will need to trust the internal CA or accept the certificate manually.

### Does QUIC improve performance on local networks?

On low-latency, reliable networks (LAN), QUIC's advantages are less noticeable than on high-latency, lossy networks (WAN, mobile). The main benefit on LAN is 0-RTT connection resumption for returning clients.

### What is the Alt-Svc header and why is it needed?

The `Alt-Svc` (Alternative Services) header tells HTTP/1.1 and HTTP/2 clients that HTTP/3 is available on a specific port. Without this header, clients cannot discover the HTTP/3 endpoint. The format is: `h3=":443"; ma=86400` (HTTP/3 on port 443, cache for 86400 seconds).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted QUIC & HTTP/3 Terminators: h2o vs quiche vs ngtcp2 Guide 2026",
  "description": "Compare h2o, quiche, and ngtcp2 for self-hosted QUIC and HTTP/3 termination. Complete deployment guide with configuration examples, TLS setup, and reverse proxy patterns.",
  "datePublished": "2026-05-10",
  "dateModified": "2026-05-10",
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
