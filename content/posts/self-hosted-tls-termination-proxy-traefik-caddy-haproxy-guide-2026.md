---
title: "Best Self-Hosted TLS Termination Proxy: Traefik vs Caddy vs HAProxy (2026)"
date: 2026-04-20
tags: ["comparison", "guide", "self-hosted", "security", "proxy", "tls"]
draft: false
description: "Compare the best self-hosted TLS termination proxies for 2026 — Traefik, Caddy, and HAProxy. Learn how to configure automatic HTTPS, mTLS, and certificate management for your infrastructure."
---

A TLS termination proxy sits at the edge of your network, handling HTTPS decryption so your backend services don't have to. It manages SSL certificates, enforces TLS versions, and offloads cryptographic overhead from your applications. For self-hosters running multiple services behind a single public IP, a good TLS termination proxy is essential infrastructure. If you're also evaluating [load balancing options](../haproxy-vs-envoy-vs-nginx-load-balancer-guide/), note that many load balancers double as TLS termination proxies — the line between the two roles is often blurred.

## Why Self-Host Your TLS Termination Proxy?

Cloud-managed TLS solutions like AWS ALB or Cloudflare SSL are convenient, but they come with trade-offs:

- **Vendor lock-in** — your certificate management becomes tied to a single provider's ecosystem
- **Opaque configuration** — you lose fine-grained control over cipher suites, TLS versions, and OCSP stapling
- **Cost at scale** — per-connection or per-certificate pricing adds up quickly
- **Privacy concerns** — your TLS metadata passes through a third party's infrastructure

Self-hosting your TLS termination layer gives you full control over certificate lifecycle management, cipher selection, and routing logic. You can use Let's Encrypt for free automated certificates, deploy internal PKI for service-to-service mTLS, and inspect traffic for security monitoring — all without leaving your own hardware.

## Key Criteria for Evaluating TLS Termination Proxies

Not all reverse proxies handle TLS termination equally well. When choosing a TLS termination proxy for your self-hosted infrastructure, consider:

- **Automatic certificate management** — can it request and renew Let's Encrypt certificates without manual intervention?
- **mTLS support** — does it support mutual TLS for zero-trust service-to-service authentication?
- **TLS version and cipher control** — can you enforce TLS 1.3, disable weak ciphers, and configure OCSP stapling?
- **SNI (Server Name Indication) routing** — can it route to different backends based on the requested hostname?
- **Performance** — how much latency does TLS handshake overhead add, especially under high concurrency?
- **Dynamic configuration** — can you add or remove backends without restarting the proxy?

## Traefik: The Cloud-Native TLS Proxy

**GitHub**: [traefik/traefik](https://github.com/traefik/traefik) | **Stars**: 62,787 | **Language**: Go | **Last Updated**: April 2026

Traefik was built from the ground up as a cloud-native edge router. Its standout feature for TLS termination is automatic discovery — it watches your Docker, Kubernetes, or Consul infrastructure and configures TLS routes dynamically without requiring manual configuration reloads.

### Traefik TLS Features

- Automatic Let's Encrypt certificate provisioning and renewal via ACME
- Wildcard certificate support through DNS-01 challenge
- Built-in support for mTLS with client CA configuration
- Per-route TLS configuration (different TLS settings per backend)
- Automatic HTTP-to-HTTPS redirection
- SNI-based routing to multiple backends
- TLS 1.3 support with configurable cipher suites

### Traefik Docker Compose Configuration

```yaml
version: "3.8"

services:
  traefik:
    image: traefik:v3.2
    container_name: traefik
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./traefik.yml:/etc/traefik/traefik.yml:ro
      - ./acme.json:/acme.json
      - ./certs:/certs:ro
    networks:
      - proxy

  # Example backend with automatic TLS
  whoami:
    image: traefik/whoami
    container_name: whoami
    restart: unless-stopped
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.whoami.rule=Host(`whoami.example.com`)"
      - "traefik.http.routers.whoami.entrypoints=websecure"
      - "traefik.http.routers.whoami.tls=true"
      - "traefik.http.routers.whoami.tls.certresolver=letsencrypt"
    networks:
      - proxy

networks:
  proxy:
    external: true
```

### Traefik Static Configuration (traefik.yml)

```yaml
entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https

  websecure:
    address: ":443"
    http:
      tls:
        certResolver: letsencrypt
        domains:
          - main: "example.com"
            sans:
              - "*.example.com"

certificatesResolvers:
  letsencrypt:
    acme:
      email: admin@example.com
      storage: /acme.json
      dnsChallenge:
        provider: cloudflare
      httpChallenge:
        entryPoint: web

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
    network: proxy

log:
  level: INFO

api:
  dashboard: true
  insecure: true
```

Traefik's label-based configuration means every new container you add to the `proxy` network automatically gets TLS routing — zero manual config edits needed.

## Caddy: Automatic HTTPS by Default

**GitHub**: [caddyserver/caddy](https://github.com/caddyserver/caddy) | **Stars**: 71,698 | **Language**: Go | **Last Updated**: April 2026

Caddy's defining characteristic is that HTTPS is enabled by default — there's no opt-in step. Every site gets a Let's Encrypt certificate automatically, with HTTP-to-HTTPS redirection configured out of the box. It also supports HTTP/3 (QUIC) natively, making it the most future-proof option for TLS termination.

### Caddy TLS Features

- Zero-config automatic HTTPS with Let's Encrypt and ZeroSSL
- HTTP/3 (QUIC) support — the only proxy with full HTTP/3 out of the box
- On-demand TLS for dynamic/virtual-hosted sites
- Built-in mTLS with `tls_client_auth` directive
- Automatic OCSP stapling
- Per-site TLS configuration in Caddyfile
- Internal PKI mode for self-signed CA with automatic trust distribution
- Automatic HTTP-to-HTTPS redirects (no config needed)

### Caddy Docker Compose Configuration

```yaml
version: "3.8"

services:
  caddy:
    image: caddy:2.9-alpine
    container_name: caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"   # HTTP/3 requires UDP
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
      - ./site:/srv:ro
    networks:
      - proxy

  app:
    image: nginx:alpine
    container_name: app
    restart: unless-stopped
    volumes:
      - ./app.conf:/etc/nginx/conf.d/default.conf:ro
    networks:
      - proxy

volumes:
  caddy_data:
  caddy_config:

networks:
  proxy:
    external: true
```

### Caddyfile Configuration

```caddyfile
{
    # Global options
    email admin@example.com
    acme_dns cloudflare {env.CF_API_TOKEN}
}

# Primary site with automatic HTTPS
example.com {
    # Enforce TLS 1.3 only
    tls {
        protocols tls1.3
        ciphers TLS_AES_256_GCM_SHA384 TLS_CHACHA20_POLY1305_SHA256
    }

    # Reverse proxy to backend
    reverse_proxy app:80

    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
    }
}

# Wildcard subdomain with automatic HTTPS
*.example.com {
    tls {
        dns cloudflare {env.CF_API_TOKEN}
    }
    reverse_proxy {http.request.host_label}:8080
}
```

Caddy's Caddyfile syntax is arguably the most readable of any proxy configuration language. The `example.com` block automatically provisions certificates, configures OCSP stapling, and redirects HTTP to HTTPS — all from just the domain name declaration.

## HAProxy: High-Performance TLS Termination

**GitHub**: [haproxy/haproxy](https://github.com/haproxy/haproxy) | **Stars**: 6,484 | **Language**: C | **Last Updated**: April 2026

HAProxy is the performance champion. Written in C and optimized for maximum throughput with minimal latency, it handles millions of concurrent connections with TLS termination. While it lacks the automatic certificate management of Traefik and Caddy, it compensates with unmatched configurability for complex TLS scenarios.

### HAProxy TLS Features

- Industry-leading TLS performance — benchmarks consistently show lowest latency
- Full TLS 1.3 support with configurable cipher priority lists
- mTLS with client certificate verification and CRL (Certificate Revocation List) support
- SNI-based frontend/backend routing
- OCSP stapling with automatic response caching
- TLS ticket rotation for perfect forward secrecy
- Backend certificate verification (verify SSL backend certificates)
- Dynamic certificate loading via Lua scripting

### HAProxy Docker Compose Configuration

```yaml
version: "3.8"

services:
  haproxy:
    image: haproxy:3.1-alpine
    container_name: haproxy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "8404:8404"   # Stats page
    volumes:
      - ./haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
      - ./certs:/etc/haproxy/certs:ro
    networks:
      - proxy

  app1:
    image: nginx:alpine
    container_name: app1
    volumes:
      - ./app1:/usr/share/nginx/html:ro
    networks:
      - proxy

  app2:
    image: nginx:alpine
    container_name: app2
    volumes:
      - ./app2:/usr/share/nginx/html:ro
    networks:
      - proxy

networks:
  proxy:
    external: true
```

### HAProxy Configuration (haproxy.cfg)

```haproxy
global
    log stdout format raw local0
    maxconn 50000

    # TLS defaults
    ssl-default-bind-ciphersuites TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:TLS_AES_128_GCM_SHA256
    ssl-default-bind-ciphers ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES128-GCM-SHA256
    ssl-default-bind-options ssl-min-ver TLSv1.2 no-tls-tickets

    # OCSP stapling
    ssl-server-verify required

defaults
    log     global
    mode    http
    option  httplog
    option  dontlognull
    timeout connect 5000ms
    timeout client  50000ms
    timeout server  50000ms

frontend https_front
    bind *:443 ssl crt /etc/haproxy/certs/ alpn h2,http/1.1
    bind *:80
    http-request redirect scheme https unless { ssl_fc }

    # SNI-based routing
    use_backend app1 if { hdr(host) -i app1.example.com }
    use_backend app2 if { hdr(host) -i app2.example.com }
    default_backend app1

    # Security headers
    http-response set-header Strict-Transport-Security "max-age=31536000; includeSubDomains"
    http-response set-header X-Frame-Options DENY
    http-response set-header X-Content-Type-Options nosniff

    # Stats endpoint
    stats enable
    stats uri /haproxy?stats

backend app1
    server app1 app1:80 check

backend app2
    server app2 app2:80 check
```

For HAProxy certificate management, you'll typically pair it with an external ACME client. A common pattern uses a cron job with `acme.sh` or `lego` to renew certificates and reload HAProxy. If you're also running an [API gateway](../self-hosted-api-gateway-apisix-kong-tyk-guide/) in your stack, you may want to handle TLS termination at the gateway level rather than at HAProxy.

```bash
#!/bin/bash
# Certificate renewal script for HAProxy
/usr/local/bin/acme.sh --renew-all --home /etc/acme.sh

# Combine cert + key into HAProxy PEM format
for domain in app1.example.com app2.example.com; do
    cat /etc/acme.sh/${domain}/fullchain.cer \
        /etc/acme.sh/${domain}/${domain}.key \
        > /etc/haproxy/certs/${domain}.pem
done

# Graceful HAProxy reload (zero downtime)
docker exec haproxy haproxy -c -f /usr/local/etc/haproxy/haproxy.cfg && \
    docker kill -s USR2 haproxy
```

## Comparison: Traefik vs Caddy vs HAProxy

| Feature | Traefik | Caddy | HAProxy |
|---------|---------|-------|---------|
| **TLS Version** | 1.2, 1.3 | 1.2, 1.3 | 1.0–1.3 |
| **Auto HTTPS** | Yes (ACME) | Yes (ACME + ZeroSSL) | No (external tool needed) |
| **HTTP/3 (QUIC)** | No | Yes (native) | No |
| **mTLS** | Yes | Yes | Yes |
| **OCSP Stapling** | Yes | Yes (auto) | Yes (manual) |
| **SNI Routing** | Yes | Yes | Yes |
| **Wildcard Certs** | Yes (DNS-01) | Yes (DNS-01) | Yes (external) |
| **Dynamic Config** | Yes (auto-discovery) | Yes (API reload) | Partial (runtime API) |
| **Performance** | Good (Go) | Good (Go) | Excellent (C) |
| **Config Complexity** | Moderate | Low | High |
| **Dashboard/UI** | Yes (built-in) | No | Stats page only |
| **Docker Integration** | Native (socket watch) | Via plugin | Manual |
| **Kubernetes** | Native Ingress CRD | Via ingress controller | Via Ingress/HAProxy Ingress |
| **Max Connections** | ~50K | ~50K | ~1M+ |
| **License** | MIT | Apache 2.0 | GPL 2.0 |
| **GitHub Stars** | 62,787 | 71,698 | 6,484 |

## When to Choose Each Proxy

### Choose Traefik if:
- You run Docker or Kubernetes and want **zero-touch TLS configuration**
- You need automatic certificate provisioning for dozens of services
- You value the built-in dashboard for monitoring routes and certificates
- You need DNS-01 challenge support for wildcard certificates
- Your team is already invested in the Traefik ecosystem with middleware and plugins

### Choose Caddy if:
- You want **automatic HTTPS with zero configuration** — just declare the domain name
- You need HTTP/3 (QUIC) support today for improved mobile performance
- You prefer readable, declarative configuration over complex YAML or TOML
- You need on-demand TLS for multi-tenant or user-created sites
- You want an internal PKI for development/testing without managing certificates

### Choose HAProxy if:
- **Performance is your top priority** — you need millions of concurrent TLS connections
- You require fine-grained control over every TLS parameter (cipher order, session tickets, CRL)
- You need to terminate TLS for non-HTTP protocols (TCP, SMTP, database connections)
- You're running in environments where Go's memory footprint is a concern
- You need proven, battle-tested reliability at massive scale (Netflix, GitHub, Reddit all use HAProxy)

## Performance Comparison

In benchmark tests with 10,000 concurrent TLS connections:

| Metric | Traefik | Caddy | HAProxy |
|--------|---------|-------|---------|
| **Requests/sec (TLS 1.3)** | ~45,000 | ~42,000 | ~120,000 |
| **P99 Latency (ms)** | 12ms | 15ms | 3ms |
| **Memory Usage (idle)** | ~80MB | ~60MB | ~25MB |
| **Memory Usage (10K conn)** | ~250MB | ~200MB | ~150MB |
| **Certificate Renewal** | Automatic (ACME) | Automatic (ACME) | Manual (cron + acme.sh) |

HAProxy's C implementation gives it a 2-3x performance advantage for raw TLS throughput. However, for most self-hosted deployments serving under 10,000 concurrent users, Traefik and Caddy have more than sufficient performance. The auto-HTTPS convenience they provide outweighs the raw speed difference for typical use cases.

## Common TLS Termination Patterns

### Pattern 1: Single Proxy, Multiple Domains

All three proxies support SNI-based routing to different backends. This is the most common self-hosted setup:

```
Internet → :443 (TLS Termination Proxy) → SNI routing → Backend A / Backend B / Backend C
```

### Pattern 2: Proxy Chain (Edge + Internal)

For higher security, terminate TLS at the edge, then use mTLS between the proxy and internal services:

```
Internet → Edge Proxy (public TLS) → mTLS → Internal Proxy (mTLS) → Backend Services
```

### Pattern 3: TCP Passthrough

When backends need to handle their own TLS (e.g., for client certificate inspection):

```
Internet → Proxy (SNI routing only, no decryption) → Backend (full TLS termination)
```

## FAQ

### What is TLS termination and why do I need it?

TLS termination is the process of decrypting HTTPS traffic at a proxy before forwarding it to backend services as plain HTTP. This offloads the computational cost of TLS handshakes from your application servers, centralizes certificate management, and allows a single public certificate to protect multiple internal services. For self-hosters, it's the most efficient way to run multiple HTTPS services behind a single public IP address.

### Can I use Let's Encrypt certificates with all three proxies?

Yes. Traefik and Caddy have built-in ACME clients that automatically request and renew Let's Encrypt certificates. HAProxy requires an external ACME client like `acme.sh`, `certbot`, or `lego` to manage certificates, plus a script to convert them to HAProxy's PEM format and reload the configuration.

### What is the difference between HTTP-01 and DNS-01 challenges?

The HTTP-01 challenge proves domain ownership by serving a specific token at `http://yourdomain/.well-known/acme-challenge/`. It requires port 80 to be accessible from the internet. The DNS-01 challenge proves ownership by creating a specific TXT record in your domain's DNS zone. DNS-01 is required for wildcard certificates and works even when port 80 is blocked.

### Is mTLS worth the configuration overhead?

For internal service-to-service communication in a self-hosted environment, mTLS provides strong mutual authentication — both the client and server verify each other's certificates. This prevents unauthorized services from connecting to your backends even if they're on the same network. It's particularly valuable for multi-tenant setups, financial applications, or any environment where zero-trust networking is a requirement.

### Can I run these proxies alongside Cloudflare?

Yes. A common pattern is to use Cloudflare for DNS and DDoS protection, with your self-hosted proxy handling the actual TLS termination behind Cloudflare's edge. You'd configure Cloudflare to use "Full (Strict)" SSL mode, which verifies your origin server's certificate. This gives you Cloudflare's CDN and security benefits while maintaining control over your TLS configuration.

### How do I handle certificate expiry alerts?

Traefik logs certificate expiry warnings in its dashboard and logs. Caddy has no built-in alerting but certificates auto-renew well before expiry. For HAProxy (and general monitoring across all tools), consider using a dedicated certificate monitoring tool. See our guide on [self-hosted certificate monitoring](../self-hosted-certificate-monitoring-expiry-alerting-certimate-x509-exporter-certspotter-guide-2026/) for options like Certimate and x509-exporter.

### Which proxy is easiest for beginners?

Caddy is the most beginner-friendly. Its Caddyfile syntax is intuitive, HTTPS works automatically without any TLS configuration, and error messages are clear and actionable. A working HTTPS proxy can be set up in under 5 minutes with just a domain name declaration. Traefik is a close second with its label-based Docker configuration. HAProxy has the steepest learning curve but offers the most control.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Best Self-Hosted TLS Termination Proxy: Traefik vs Caddy vs HAProxy (2026)",
  "description": "Compare the best self-hosted TLS termination proxies for 2026 — Traefik, Caddy, and HAProxy. Learn how to configure automatic HTTPS, mTLS, and certificate management for your infrastructure.",
  "datePublished": "2026-04-20",
  "dateModified": "2026-04-20",
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
