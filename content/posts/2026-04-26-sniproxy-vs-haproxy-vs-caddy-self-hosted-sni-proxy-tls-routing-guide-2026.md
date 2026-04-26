---
title: "sniproxy vs HAProxy vs Caddy: Self-Hosted SNI Proxy & TLS Routing Guide 2026"
date: 2026-04-26
tags: ["comparison", "guide", "self-hosted", "networking", "tls", "reverse-proxy"]
draft: false
description: "Compare sniproxy, HAProxy, and Caddy for self-hosted SNI proxy and TLS routing. Learn how to route encrypted traffic based on hostname without decrypting, with Docker Compose configs and production-ready setups."
---

When you run multiple services behind a single public IP address, you quickly run into the port 443 problem. Every HTTPS service wants its own TLS connection on the same port, and a traditional reverse proxy needs the certificates for every backend. SNI (Server Name Indication) solves this by letting the client announce which hostname it wants during the TLS handshake — allowing a proxy to route the connection to the correct backend **without ever decrypting the traffic**.

This guide compares three approaches to self-hosted SNI proxying: the dedicated **sniproxy** tool, the versatile **HAProxy** in SNI routing mode, and the all-in-one **Caddy** web server. Each has distinct strengths depending on your infrastructure needs.

## Why Use SNI Proxy Routing?

SNI proxy routing is essential in several common scenarios:

- **Multiple HTTPS backends on a single IP**: Route `app1.example.com`, `app2.example.com`, and `api.example.com` to different internal servers, each handling its own TLS termination.
- **Passthrough TLS to backend services**: When backend services (like self-hosted databases with TLS, or email servers) need to receive encrypted connections directly.
- **Compliance requirements**: Some environments require end-to-end encryption where the proxy cannot inspect content. SNI routing achieves this by forwarding raw TCP/TLS streams.
- **Simplified certificate management**: Let each backend manage its own certificates rather than centralizing them on a reverse proxy.
- **Load distribution across data centers**: Route users to geographically different backends based on hostname without adding TLS overhead at the edge.

Unlike a full reverse proxy (which terminates TLS and re-encrypts to backends), an SNI proxy operates at the TCP layer, forwarding encrypted traffic based solely on the hostname embedded in the TLS ClientHello message. If you're looking for a full reverse proxy with GUI management instead, check out our [comparison of Nginx Proxy Manager, SWAG, and Caddy Docker Proxy](../nginx-proxy-manager-vs-swag-vs-caddy-docker-proxy-self-hosted-reverse-proxy-gui-guide-2026/).

## Comparison Overview

| Feature | sniproxy | HAProxy (SNI mode) | Caddy |
|---------|----------|---------------------|-----|
| **Primary purpose** | Dedicated SNI/TLS proxy | Full load balancer with SNI support | Web server with auto-TLS |
| **GitHub stars** | ~2,700 | ~6,500 | ~71,800 |
| **Language** | C | C | Go |
| **Docker support** | Community images | Official image (`haproxy:latest`) | Official image (`caddy:latest`) |
| **TLS termination** | No (passthrough only) | Yes (SNI + termination modes) | Yes (automatic Let's Encrypt) |
| **Config complexity** | Low | Medium | Low |
| **HTTP/2 support** | No (TCP passthrough) | Yes (when terminating) | Yes |
| **Automatic HTTPS** | No | No | Yes |
| **Health checks** | No | Yes (TCP/HTTP) | Yes |
| **WebSocket passthrough** | Yes | Yes | Yes |
| **Last updated** | Sep 2025 | Apr 2026 | Apr 2026 |
| **Best for** | Simple TLS passthrough | Enterprise routing + load balancing | All-in-one HTTPS server |

## sniproxy: Dedicated SNI Proxy

**sniproxy** is a lightweight, purpose-built daemon that proxies incoming HTTP and TLS connections based on the hostname in the initial request. It does not terminate TLS — it simply reads the SNI hostname and forwards the raw TCP connection to the appropriate backend.

### When to Choose sniproxy

- You need **TLS passthrough only** — no certificate management on the proxy
- You want the **smallest possible footprint** for SNI routing
- Your backends handle their own TLS certificates
- You don't need health checks, load balancing, or HTTP features

### Docker Compose Configuration

sniproxy does not provide an official Docker image, but the community-maintained image works well:

```yaml
version: "3.8"
services:
  sniproxy:
    image: docker.io/joelpearce/sniproxy:latest
    container_name: sniproxy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./sniproxy.conf:/etc/sniproxy.conf:ro
    network_mode: host
```

### sniproxy Configuration

Create a `sniproxy.conf` file:

```
pidfile /tmp/sniproxy.pid

user sniproxy

table {
    # Route by hostname to different backends
    # Format: hostname regex destination:port
    
    # Web applications
    app1\.example\.com 192.168.1.10:443
    app2\.example\.com 192.168.1.11:443
    
    # API backend
    api\.example\.com 192.168.1.20:443
    
    # Email services (passthrough TLS)
    mail\.example\.com 192.168.1.30:465
    
    # Fallback - route to default server
    .* 192.168.1.10:443
}

listener 0.0.0.0:443 {
    proto tls
    table table
    access-log {
        filename /var/log/sniproxy/access.log
        priority notice
    }
}

listener 0.0.0.0:80 {
    proto http
    table table
}
```

### Installing sniproxy Bare-Metal

For production deployments without Docker:

```bash
# Ubuntu/Debian
apt-get update
apt-get install -y autotools-dev cdbs debhelper dh-autoreconf dpkg-dev \
    gettext libev-dev libpcre3-dev libudns-dev pkg-config fakeroot devscripts

git clone https://github.com/dlundquist/sniproxy.git
cd sniproxy
./autogen.sh && ./configure && make deb
dpkg -i ../sniproxy_*.deb
systemctl enable sniproxy
systemctl start sniproxy
```

## HAProxy: Enterprise SNI Routing

**HAProxy** is the industry-standard load balancer that supports SNI-based routing as one of many modes. While sniproxy only does SNI passthrough, HAProxy can operate in multiple modes: pure SNI routing (tcp mode with SNI ACLs), TLS termination, or hybrid setups.

### When to Choose HAProxy

- You need **both SNI passthrough and TLS termination** on the same proxy
- You want **health checks** and active backend monitoring
- You need **load balancing** (round-robin, least-conn, etc.) across backends
- You require **rate limiting**, connection queuing, or DDoS protection features
- You need detailed **statistics and monitoring** via the HAProxy stats page

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  haproxy:
    image: haproxy:3.1
    container_name: haproxy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "8404:8404"
    volumes:
      - ./haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
      - ./certs:/etc/haproxy/certs:ro
    networks:
      - frontend
      - backend

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
```

### HAProxy SNI Configuration

Create `haproxy.cfg` with SNI-based TCP routing:

```
global
    log stdout format raw local0
    maxconn 4096

defaults
    log     global
    mode    tcp
    option  tcplog
    timeout connect 5s
    timeout client  30s
    timeout server  30s
    retries 3

# Frontend: inspect SNI and route accordingly
frontend ft_sni
    bind *:443
    mode tcp
    
    # Extract SNI hostname from TLS ClientHello
    tcp-request inspect-delay 5s
    tcp-request content accept if { req.ssl_hello_type 1 }
    
    # Route based on SNI hostname
    use_backend bk_app1 if { req.ssl_sni -m end app1.example.com }
    use_backend bk_app2 if { req.ssl_sni -m end app2.example.com }
    use_backend bk_api   if { req.ssl_sni -m end api.example.com }
    use_backend bk_mail  if { req.ssl_sni -m end mail.example.com }
    
    default_backend bk_default

# Backend definitions
backend bk_app1
    server app1 192.168.1.10:443 check

backend bk_app2
    server app2 192.168.1.11:443 check

backend bk_api
    server api1 192.168.1.20:443 check
    server api2 192.168.1.21:443 check

backend bk_mail
    server mail 192.168.1.30:465 check

backend bk_default
    server default 192.168.1.10:443 check

# Optional: Stats page
frontend stats
    bind *:8404
    mode http
    stats enable
    stats uri /
    stats refresh 10s
```

### HAProxy Hybrid Mode: SNI + TLS Termination

For domains where you want the proxy to terminate TLS:

```
frontend ft_https
    bind *:443 ssl crt /etc/haproxy/certs/
    mode http
    
    # Terminate TLS for specific domains
    use_backend bk_web if { hdr(host) -i web.example.com }
    
    # Or switch to TCP mode for passthrough
    # (requires separate frontend for tcp mode)
```

## Caddy: All-in-One with Automatic TLS

**Caddy** takes a fundamentally different approach: rather than passthrough routing, it terminates TLS for every domain and uses automatic Let's Encrypt certificate provisioning. For SNI routing specifically, Caddy can route based on hostname at the HTTP layer after TLS termination, or use the `reverse_proxy` directive with TLS passthrough.

### When to Choose Caddy

- You want **automatic HTTPS** — zero certificate management
- You need a **single binary** that handles TLS, routing, and serving static files
- You prefer **simple, declarative configuration** (Caddyfile)
- You're okay with the proxy **terminating TLS** for all traffic
- You want built-in **HTTP/3 (QUIC) support**

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  caddy:
    image: caddy:2.9
    container_name: caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    networks:
      - caddy_net

volumes:
  caddy_data:
  caddy_config:

networks:
  caddy_net:
    driver: bridge
```

### Caddyfile Configuration

Create a `Caddyfile` for hostname-based routing with automatic TLS:

```
{
    # Global options
    email admin@example.com
    acme_ca https://acme-v02.api.letsencrypt.org/directory
}

# Automatic HTTPS with Let's Encrypt
app1.example.com {
    reverse_proxy 192.168.1.10:8080
    
    # Enable HTTP/3
    encode gzip
    
    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
    }
}

app2.example.com {
    reverse_proxy 192.168.1.11:8080
}

api.example.com {
    reverse_proxy 192.168.1.20:3000 {
        health_uri /healthz
        health_interval 10s
    }
}

# TLS passthrough mode (raw TCP proxy)
mail.example.com {
    handle {
        reverse_proxy 192.168.1.30:465
    }
}
```

### Caddy with Internal CA (No Let's Encrypt)

For internal networks where Let's Encrypt isn't accessible:

```
{
    local_certs
}

*.internal.example.com {
    reverse_proxy 192.168.1.0/24:8080
}
```

This uses Caddy's built-in CA to generate certificates signed by a local root CA. Distribute the root CA certificate to clients to avoid browser warnings.

## Performance Comparison

| Metric | sniproxy | HAProxy | Caddy |
|--------|----------|---------|-------|
| **Connections/sec** | ~50,000 | ~100,000 | ~40,000 |
| **Memory footprint** | ~5 MB | ~15 MB | ~25 MB |
| **Latency overhead** | < 0.1 ms | < 0.2 ms | < 0.5 ms |
| **Max concurrent** | Unlimited (kernel) | ~500,000 | ~200,000 |
| **CPU usage (idle)** | Near zero | Low | Low |

*Note: sniproxy benchmarks from community testing. HAProxy figures from haproxy.org. Caddy figures from caddyserver.com docs. Actual performance depends on hardware and configuration.*

## Security Considerations

### SNI Privacy

SNI hostnames are sent in **plaintext** during the TLS handshake, even when the rest of the connection is encrypted. This means:

- Network observers can see which hostnames clients are connecting to
- Use **ECH (Encrypted Client Hello)** when available to encrypt the SNI field
- All three tools support ECH when clients and backends are configured for it

### TLS Passthrough vs Termination

When choosing between passthrough (sniproxy, HAProxy tcp mode) and termination (Caddy, HAProxy http mode):

- **Passthrough**: End-to-end encryption, backend manages certs, no inspection at proxy
- **Termination**: Proxy manages certs, enables HTTP features (compression, caching, WAF), adds a trust boundary at the proxy

### Hardening Tips

For any SNI proxy deployment:

```bash
# Set connection limits to prevent resource exhaustion
# HAProxy example:
maxconn 10000 per server

# Rate-limit new connections (iptables example):
iptables -A INPUT -p tcp --dport 443 -m connlimit \
    --connlimit-above 50 --connlimit-mask 32 -j DROP

# Monitor for SNI abuse:
# Log all SNI hostnames and alert on unexpected domains
```

## Migration Guide

### From a Single-Certificate Reverse Proxy to SNI Routing

1. **Inventory all hostnames** currently served by your reverse proxy
2. **Identify which backends** can handle their own TLS certificates
3. **Deploy the SNI proxy** alongside your existing reverse proxy
4. **Migrate hostnames one at a time**, starting with non-critical services
5. **Verify TLS certificates** on each backend match the expected hostname
6. **Remove the old reverse proxy** once all traffic has been migrated

### From sniproxy to HAProxy

If you outgrow sniproxy and need health checks or load balancing:

1. Export your sniproxy table to HAProxy `use_backend` rules
2. Add `check` parameters to each backend server line
3. Enable the stats frontend for monitoring
4. Test with `haproxy -c -f /etc/haproxy/haproxy.cfg` before deploying
5. Swap the listening port and verify connectivity

## Choosing the Right Tool

**Choose sniproxy if:**
- You need a dead-simple TLS passthrough proxy
- Your infrastructure is small (under 10 hostnames)
- You want minimal resource usage
- Each backend already handles its own TLS

**Choose HAProxy if:**
- You need enterprise-grade reliability with health checks
- You want a mix of SNI passthrough and TLS termination
- You need load balancing across multiple backend instances
- You require detailed metrics and the stats dashboard
- You're already using HAProxy for other load balancing needs

**Choose Caddy if:**
- You want zero-effort automatic HTTPS certificates
- You prefer simple, readable configuration over complex ACLs
- You need a unified tool for TLS termination, routing, and static file serving
- You're building a new infrastructure from scratch
- You want built-in HTTP/3 support

For most production environments, **HAProxy** offers the most flexibility with SNI passthrough, TLS termination, and load balancing in a single tool. For simple deployments where backends manage their own certificates, **sniproxy** is the lightest option. And for teams that want to eliminate certificate management entirely, **Caddy**'s automatic HTTPS is unmatched.

For related reading on TLS infrastructure, see our [TLS certificate automation guide](../cert-manager-vs-lego-vs-acme-sh-self-hosted-tls-certificate-automation-guide-2026/) and [load balancer comparison](../haproxy-vs-envoy-vs-nginx-load-balancer-guide/). If you need mutual TLS between services, our [mTLS configuration guide](../self-hosted-mutual-tls-mtls-nginx-caddy-traefik-envoy-guide-2026/) covers end-to-end certificate-based authentication.

## FAQ

### What is SNI and why does it matter for self-hosting?

SNI (Server Name Indication) is a TLS extension that allows a client to specify which hostname it wants to connect to during the initial TLS handshake. This matters for self-hosting because it lets you route multiple HTTPS services through a single IP address and port 443, with each service using its own TLS certificate on the backend.

### Can sniproxy terminate TLS connections?

No. sniproxy is a pure TCP passthrough proxy. It reads the SNI hostname from the TLS ClientHello message and forwards the entire encrypted connection to the backend. If you need TLS termination (decrypting and re-encrypting traffic), use HAProxy or Caddy instead.

### Does HAProxy SNI mode require certificates on the proxy?

Not in TCP mode. When HAProxy operates in `mode tcp` with SNI ACLs (`req.ssl_sni`), it inspects the hostname in the TLS handshake without decrypting the traffic. Certificates are only needed on the proxy when using `mode http` with `ssl crt` for TLS termination.

### Can I use Let's Encrypt certificates with sniproxy?

sniproxy itself does not manage certificates. However, you can use certbot or acme.sh on your backend servers to obtain Let's Encrypt certificates. The SNI proxy simply forwards the encrypted connection — it doesn't care about the certificates.

### How does SNI proxying differ from a reverse proxy?

A reverse proxy (like Nginx or Caddy in standard mode) terminates the TLS connection, inspects the HTTP request, and creates a new connection to the backend. SNI proxying operates at the TCP layer — it reads the SNI hostname during the TLS handshake and forwards the raw encrypted stream to the correct backend without ever decrypting it.

### Is SNI passthrough secure?

SNI passthrough provides end-to-end encryption between the client and backend. However, the SNI hostname itself is visible in plaintext during the TLS handshake. For most use cases this is acceptable, but if you need to hide the hostname from network observers, look into ECH (Encrypted Client Hello), which is supported by modern browsers and servers.

### Can I run multiple SNI proxies for high availability?

Yes. You can deploy two SNI proxy instances behind a layer-4 load balancer (using keepalived with VRRP, or a cloud load balancer). Each proxy uses the same configuration, and the load balancer distributes incoming TCP connections between them. For HAProxy, you can also use its built-in active/active clustering features.

### What happens if a client doesn't support SNI?

Very old clients (Internet Explorer on Windows XP, Java 6) do not support SNI. When an SNI proxy receives a connection without SNI data, it routes to the `default_backend`. For modern clients (anything from the last decade), SNI is universally supported.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "sniproxy vs HAProxy vs Caddy: Self-Hosted SNI Proxy & TLS Routing Guide 2026",
  "description": "Compare sniproxy, HAProxy, and Caddy for self-hosted SNI proxy and TLS routing. Learn how to route encrypted traffic based on hostname without decrypting, with Docker Compose configs and production-ready setups.",
  "datePublished": "2026-04-26",
  "dateModified": "2026-04-26",
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
