---
title: "Self-Hosted HTTP/3 Reverse Proxies: Caddy vs H2O vs Nginx (2026)"
date: "2026-05-20"
tags: ["http3", "quic", "reverse-proxy", "web-server", "tls", "networking", "self-hosted", "performance"]
draft: false
---

HTTP/3 represents the next evolution of web transport, replacing TCP with QUIC (Quick UDP Internet Connections) to eliminate head-of-line blocking, reduce connection establishment latency, and improve performance on lossy networks. For self-hosted infrastructure, deploying an HTTP/3-capable reverse proxy means faster page loads, better mobile performance, and future-proof web delivery.

In this guide, we compare three open-source HTTP/3 reverse proxy solutions: **Caddy**, the automatic HTTPS web server with native HTTP/3; **H2O**, the optimized HTTP server with pioneering HTTP/3 support; and **Nginx**, the industry-standard reverse proxy with HTTP/3 via the quiche library.

## What Is HTTP/3 and Why Does It Matter?

HTTP/3 is the third major version of the HTTP protocol. Unlike HTTP/1.1 (TCP-based, sequential) and HTTP/2 (TCP-based, multiplexed), HTTP/3 uses **QUIC over UDP**, which provides:

- **No head-of-line blocking**: Lost packets in one stream don't block others
- **Faster connection setup**: 0-RTT resumption for returning visitors
- **Better mobile performance**: Connection migration when switching networks (WiFi to cellular)
- **Built-in encryption**: TLS 1.3 is mandatory in QUIC, not optional

For self-hosted services, HTTP/3 can reduce page load times by 10-30% on lossy or high-latency connections, with the most dramatic improvements on mobile networks.

## Comparison Overview

| Feature | Caddy | H2O | Nginx + quiche |
|---------|-------|-----|----------------|
| GitHub Stars | 72,602+ | 11,463+ | 30,414+ |
| HTTP/3 Support | Native (built-in) | Native (built-in) | Via quiche module |
| QUIC Library | quic-go (Go) | picotls + quicly (C) | Cloudflare quiche (C++) |
| Automatic HTTPS | Yes (ACME built-in) | Manual configuration | Manual configuration |
| Configuration | Caddyfile (simple) | YAML/Perl-style | nginx.conf (mature) |
| Reverse Proxy | Yes | Yes | Yes (industry standard) |
| Load Balancing | Yes | Yes | Yes (most mature) |
| gRPC Support | Yes | Yes | Yes |
| WebSocket | Yes | Yes | Yes |
| Cache | Limited | Yes (fastcgi cache) | Yes (proxy cache) |
| Lua/Scripting | No | Yes (mruby) | Yes (Lua/OpenResty) |
| Memory Usage | Moderate (~50MB idle) | Low (~20MB idle) | Low (~10MB idle) |
| Last Updated | May 2026 | May 2026 | May 2026 |

## Caddy

Caddy is the easiest HTTP/3 reverse proxy to deploy — it enables HTTP/3 automatically when TLS is configured, with zero additional configuration needed.

### Installation

```bash
# Install Caddy
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy
```

### HTTP/3 Configuration

```caddyfile
example.com {
    reverse_proxy localhost:8080
    
    # HTTP/3 is enabled by default when TLS is active
    # No additional directives needed
}

# Multiple backends with load balancing
api.example.com {
    reverse_proxy {
        to backend1:3000 backend2:3000 backend3:3000
        lb_policy round_robin
    }
}

# With custom QUIC parameters
example.com {
    reverse_proxy localhost:8080
    
    # Fine-tune HTTP/3
    {
        servers {
            protocol {
                experimental_http3
            }
        }
    }
}
```

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"  # Required for HTTP/3 QUIC
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    restart: unless-stopped

volumes:
  caddy_data:
  caddy_config:
```

**Key point**: The UDP port 443 binding is essential for HTTP/3. Without it, Caddy falls back to HTTP/2 over TCP.

### Key Advantages

- **Zero-config HTTP/3**: Enabled automatically with TLS — no flags or modules needed
- **Automatic HTTPS**: ACME certificate provisioning and renewal built-in
- **Simple configuration**: The Caddyfile is human-readable and intuitive
- **Active development**: The quic-go library is one of the most mature QUIC implementations

## H2O

H2O is a performance-optimized HTTP server with pioneering HTTP/3 support. It was one of the first servers to implement HTTP/3 and remains one of the fastest.

### Installation

```bash
# Install from package
sudo apt install h2o

# Build from source with HTTP/3 support
git clone https://github.com/h2o/h2o.git
cd h2o
cmake -DWITH_MRUBY=on -DWITH_BROTLI=on .
make && sudo make install
```

### HTTP/3 Configuration

```yaml
hosts:
  "example.com:443":
    listen:
      port: 443
      ssl:
        certificate-file: /etc/ssl/certs/example.com.crt
        key-file: /etc/ssl/private/example.com.key
    paths:
      "/":
        proxy.reverse.url: http://localhost:8080
    http3: on  # Enable HTTP/3

listen:
  port: 80
  # Redirect HTTP to HTTPS
```

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  h2o:
    image: ghcr.io/h2o/h2o:latest
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"
    volumes:
      - ./h2o.conf:/etc/h2o/h2o.conf:ro
      - ./certs:/etc/ssl:ro
    restart: unless-stopped
```

### Key Advantages

- **Performance**: Consistently benchmarks as the fastest HTTP/3 server
- **mruby scripting**: Embedded Ruby for custom request/response processing
- **FastCGI support**: Native integration with PHP-FPM and other FastCGI backends
- **Pioneering HTTP/3**: The H2O team contributed significantly to the QUIC standard

## Nginx with HTTP/3 (quiche)

Nginx supports HTTP/3 through a patch built on Cloudflare's quiche library. This requires either compiling from source or using a pre-built package.

### Installation

```bash
# Build Nginx with quiche module
git clone --recursive https://github.com/cloudflare/quiche.git
cd quiche

# Build Nginx with the quiche patch
./quiche/apps/nghttpx --help  # Verify build

# Or use OpenResty with HTTP/3 support
# OpenResty bundles HTTP/3 support in recent versions
```

For production, most users deploy Nginx with the `--with-http_v3_module` flag:

```bash
./configure \
  --with-http_v3_module \
  --with-http_quic_module \
  --with-stream_quic_module \
  --with-cc-opt="-I../quiche/quiche/include" \
  --with-ld-opt="-L../quiche/target/release"
make && sudo make install
```

### HTTP/3 Configuration

```nginx
server {
    listen 443 quic reuseport;
    listen 443 ssl;
    
    ssl_certificate /etc/ssl/certs/example.com.crt;
    ssl_certificate_key /etc/ssl/private/example.com.key;
    
    # HTTP/3 specific settings
    http3 on;
    quic_retry on;
    
    # Alt-Svc header to advertise HTTP/3 support
    add_header Alt-Svc 'h3=":443"; ma=86400';
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  nginx:
    image: nginx:quic  # Official quic-enabled image
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/ssl:ro
    restart: unless-stopped
```

### Key Advantages

- **Industry standard**: The most widely deployed reverse proxy with the largest ecosystem
- **Lua/OpenResty**: Extensive scripting capabilities for custom logic
- **Mature caching**: The most advanced proxy caching system available
- **Large community**: Extensive documentation, tutorials, and third-party modules

## Why Deploy HTTP/3?

Deploying HTTP/3 on your self-hosted infrastructure delivers measurable improvements:

**Performance**: HTTP/3 eliminates head-of-line blocking inherent in TCP-based protocols. On networks with even 1% packet loss, HTTP/3 can deliver 2-3x throughput compared to HTTP/2.

**Mobile Experience**: QUIC's connection migration means users switching from WiFi to cellular don't lose their connections. This is critical for self-hosted services accessed by mobile users.

**Security**: HTTP/3 mandates TLS 1.3, providing the strongest encryption available. The QUIC protocol also encrypts more of the connection metadata than TCP+TLS.

**Future-proofing**: Major browsers (Chrome, Firefox, Safari) now support HTTP/3, and CDN providers (Cloudflare, Fastly) are pushing adoption. Deploying HTTP/3 ensures your services remain competitive.

For comprehensive reverse proxy management, see our [Nginx Proxy Manager vs Traefik vs Caddy comparison](../reverse-proxy-comparison/). For load balancing strategies, our [TCP load balancing guide](../2026-05-20-self-hosted-tcp-load-balancing-haproxy-nginx-envoy-guide/) covers HAProxy, Nginx, and Envoy.

## Choosing the Right HTTP/3 Reverse Proxy

**Caddy** is the best choice for most self-hosted setups. Its automatic HTTPS and zero-config HTTP/3 make it the easiest to deploy and maintain. If you want HTTP/3 working out of the box, Caddy is the answer.

**H2O** is the performance champion. If you need the absolute lowest latency and highest throughput for HTTP/3 traffic, H2O's optimized implementation consistently beats competitors in benchmarks.

**Nginx** is the right choice when you need the mature ecosystem of modules, Lua scripting, or integration with existing Nginx-based infrastructure. The HTTP/3 support, while requiring more setup, benefits from Nginx's battle-tested reverse proxy capabilities.

## FAQ

### What port does HTTP/3 use?

HTTP/3 uses UDP port 443 (the same port number as HTTPS, but over UDP instead of TCP). You must configure your firewall and reverse proxy to accept UDP traffic on port 443 in addition to TCP.

### Do I need a special SSL certificate for HTTP/3?

No. HTTP/3 uses the same TLS 1.3 certificates as HTTPS. Any valid SSL certificate works with HTTP/3. The difference is in the transport protocol (QUIC over UDP vs TCP), not the certificate.

### Can HTTP/3 and HTTP/2 run on the same server?

Yes. Most HTTP/3 servers listen on both TCP port 443 (for HTTP/2/TLS) and UDP port 443 (for HTTP/3/QUIC). The server advertises HTTP/3 support via the `Alt-Svc` header in HTTP/2 responses, allowing clients to upgrade on subsequent requests.

### Is HTTP/3 supported by all browsers?

As of 2026, Chrome, Firefox, Safari, and Edge all support HTTP/3. Browser support has been stable since 2023. The primary requirement is that the server must have a valid TLS certificate (self-signed certificates may not trigger HTTP/3 in some browsers).

### How do I verify HTTP/3 is working?

Use `curl` with the `--http3` flag: `curl --http3 -I https://example.com`. You can also use browser developer tools — the Network tab will show `h3` as the protocol for HTTP/3 connections. Online tools like `https://http3check.net` can also verify your server's HTTP/3 support.

### What is the Alt-Svc header?

The `Alt-Svc` (Alternative Service) header tells browsers that the server supports HTTP/3 on a specific port. Example: `Alt-Svc: h3=":443"; ma=86400` means "HTTP/3 is available on port 443 for the next 86400 seconds (24 hours)." Without this header, browsers won't attempt HTTP/3 connections.

### Does HTTP/3 work with reverse proxy chains?

Yes, but each proxy in the chain must support HTTP/3. A typical setup has the edge proxy (Caddy/Nginx) handling HTTP/3 from clients and forwarding to upstream services over HTTP/2 or HTTP/1.1. The client-to-proxy leg benefits from HTTP/3 while the internal network uses standard HTTP.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted HTTP/3 Reverse Proxies: Caddy vs H2O vs Nginx",
  "description": "Compare HTTP/3 reverse proxy solutions — Caddy, H2O, and Nginx with QUIC support for self-hosted web infrastructure.",
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
