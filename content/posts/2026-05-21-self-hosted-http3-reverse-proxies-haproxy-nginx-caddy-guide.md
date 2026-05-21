---
title: "Self-Hosted HTTP/3 Reverse Proxies: HAProxy vs NGINX QUIC vs Caddy (2026)"
date: "2026-05-21"
tags: ["http3", "quic", "reverse-proxy", "load-balancer", "web-server", "self-hosted", "networking", "docker"]
draft: false
---

HTTP/3 represents the biggest evolution in web transport protocols in over a decade. Built on QUIC (Quick UDP Internet Connections), it replaces TCP with UDP to eliminate head-of-line blocking, reduce connection establishment latency, and improve performance on lossy networks. But adopting HTTP/3 requires reverse proxies and load balancers that understand the protocol. This guide compares three popular self-hosted solutions: **HAProxy with QUIC support**, **NGINX with QUIC**, and **Caddy with native HTTP/3**.

## Why HTTP/3 Matters

HTTP/3 solves several fundamental limitations of HTTP/2 over TCP:

**Head-of-line blocking elimination:** In HTTP/2, a single lost TCP packet blocks all streams multiplexed over that connection. HTTP/3's QUIC transport handles each stream independently at the UDP level, so packet loss on one stream doesn't affect others.

**Faster connection establishment:** QUIC combines the TLS handshake with the transport handshake, reducing the round trips needed to establish a secure connection from 3 (TCP + TLS) to 1. This dramatically improves page load times, especially on high-latency mobile networks.

**Connection migration:** QUIC connections are identified by a connection ID rather than IP/port pairs. When a client switches from WiFi to cellular, the connection persists without re-establishment — no dropped WebSocket connections, no interrupted file downloads.

For traditional reverse proxy setups and GUI management tools, see our [NGINX Proxy Manager vs SWAG vs Caddy Docker Proxy comparison](../2026-04-24-nginx-proxy-manager-vs-swag-vs-caddy-docker-proxy-self-hosted-reverse-proxy-gui-guide/). For Kubernetes ingress controllers, our [Traefik vs NGINX Ingress vs Contour guide](../2026-04-22-traefik-vs-nginx-ingress-vs-contour-kubernetes-ingress-controller-guide/) covers ingress-level load balancing. For mTLS configurations, check our [mutual TLS with NGINX, Caddy, Traefik, and Envoy guide](../2026-04-24-self-hosted-mutual-tls-mtls-nginx-caddy-traefik-envoy-guide/).

## HAProxy with QUIC Support

[HAProxy](https://www.haproxy.org/) is the industry-standard load balancer known for its performance, reliability, and advanced traffic management features. QUIC/HTTP/3 support was added in HAProxy 2.6+ and has been continuously improved.

**Key Features:**
- **Production-grade load Balancing** — Layer 4 and Layer 7 load balancing with health checks
- **QUIC/HTTP/3 support** — native QUIC listener with HTTP/3 frontend (HAProxy 2.6+)
- **Advanced routing** — ACL-based routing, content switching, header manipulation
- **SSL/TLS termination** — certificate management, SNI-based routing, OCSP stapling
- **Stick tables** — session persistence, rate limiting, DDoS mitigation
- **Runtime API** — dynamic configuration changes without reload
- **Observability** — Prometheus exporter, detailed logging, stats page

**HAProxy Docker deployment with QUIC:**
```yaml
version: "3.8"
services:
  haproxy:
    image: haproxy:2.9
    ports:
      - "443:443/tcp"
      - "443:443/udp"    # QUIC requires UDP
      - "80:80/tcp"
      - "8404:8404/tcp"  # Stats page
    volumes:
      - ./haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
      - ./certs:/etc/haproxy/certs:ro
    restart: unless-stopped
```

**HAProxy configuration for HTTP/3:**
```
global
    log stdout format raw local0
    ssl-default-bind-ciphersuites TLS_AES_128_GCM_SHA256:TLS_AES_256_GCM_SHA384
    ssl-default-bind-options prefer-client-ciphers no-sslv3 no-tlsv10 no-tlsv11

defaults
    mode http
    log     global
    option  httplog
    timeout connect 5s
    timeout client  30s
    timeout server  30s

frontend https_front
    bind *:443 ssl crt /etc/haproxy/certs/site.pem alpn h2,http/1.1
    bind *:443 quic crt /etc/haproxy/certs/site.pem alpn h3
    http-request redirect scheme https unless { ssl_fc }

    default_backend web_servers

backend web_servers
    balance roundrobin
    option httpchk GET /health
    server web1 10.0.0.1:8080 check
    server web2 10.0.0.2:8080 check
    server web3 10.0.0.3:8080 check
```

The critical configuration element is the dual `bind` directive — one for TCP-based HTTP/2 and HTTP/1.1, and one for QUIC-based HTTP/3. Both share the same certificate and port.

## NGINX with QUIC

[NGINX](https://nginx.org/) added QUIC/HTTP/3 support as an experimental feature in NGINX 1.25+ (open source) and has been available in NGINX Plus since R28. The implementation is maturing rapidly and production deployments are now viable.

**Key Features:**
- **QUIC/HTTP/3 support** — experimental in open-source, production-ready in NGINX Plus
- **BoringSSL dependency** — requires BoringSSL for QUIC support (not OpenSSL)
- **Advanced caching** — proxy cache, FastCGI cache, microcaching
- **Dynamic modules** — extend functionality with third-party modules
- **Rate limiting** — request rate limiting, connection limiting, bandwidth throttling
- **gRPC support** — native gRPC proxying and load balancing
- **WebSocket proxy** — real-time application support

**Building NGINX with QUIC support:**
```bash
# Install BoringSSL
git clone https://boringssl.googlesource.com/boringssl
cd boringssl && mkdir build && cd build
cmake .. && make

# Build NGINX with QUIC
wget https://nginx.org/download/nginx-1.25.3.tar.gz
tar xzf nginx-1.25.3.tar.gz
cd nginx-1.25.3
./configure \
  --with-http_v3_module \
  --with-http_quic_module \
  --with-openssl=../boringssl \
  --with-stream_quic_module \
  --prefix=/etc/nginx
make && sudo make install
```

**NGINX HTTP/3 configuration:**
```nginx
server {
    listen 443 ssl;
    listen 443 quic reuseport;
    http2 on;
    http3 on;

    ssl_certificate     /etc/nginx/certs/site.pem;
    ssl_certificate_key /etc/nginx/certs/site.key;

    # Alt-Svc header for HTTP/3 discovery
    add_header Alt-Svc 'h3=":443"; ma=86400';

    # QUIC-specific settings
    quic_retry on;
    quic_gso on;

    location / {
        proxy_pass http://backend_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /health {
        access_log off;
        return 200 'ok';
    }
}

upstream backend_servers {
    server 10.0.0.1:8080;
    server 10.0.0.2:8080;
    server 10.0.0.3:8080;
}
```

The `Alt-Svc` header is essential — it tells browsers that HTTP/3 is available on port 443, enabling the browser to establish a QUIC connection on subsequent requests.

## Caddy with Native HTTP/3

[Caddy](https://caddyserver.com/) is a modern web server with automatic HTTPS and native HTTP/3 support out of the box. Unlike HAProxy and NGINX, which require specific versions and configurations for HTTP/3, Caddy enables it by default with zero additional configuration.

**Key Features:**
- **Automatic HTTPS** — zero-config TLS certificate provisioning via Let's Encrypt
- **Native HTTP/3** — enabled by default, no special build or configuration needed
- **Caddyfile** — simple, human-readable configuration syntax
- **Dynamic configuration** — JSON API for runtime configuration changes
- **Reverse proxy** — built-in load balancing, health checks, circuit breakers
- **Plugin ecosystem** — extend with Go plugins and third-party modules
- **Single binary** — no dependencies, self-contained executable

**Caddy Docker deployment:**
```yaml
version: "3.8"
services:
  caddy:
    image: caddy:2.8
    ports:
      - "80:80"
      - "443:443/tcp"
      - "443:443/udp"    # HTTP/3 requires UDP
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    restart: unless-stopped

volumes:
  caddy_data:
  caddy_config:
```

**Caddyfile configuration:**
```
example.com {
    reverse_proxy backend_servers

    # HTTP/3 is enabled by default — no special directive needed
    # To explicitly configure HTTP/3 settings:
    # server {
    #     protocols h1 h2 h3
    # }
}

backend_servers {
    to 10.0.0.1:8080 10.0.0.2:8080 10.0.0.3:8080
    lb_policy round_robin
    health_uri /health
    health_interval 10s
}
```

Caddy's approach is refreshingly simple: HTTP/3 is always on, certificates are always managed, and the configuration file reads like plain English.

## Comparison Table

| Feature | HAProxy | NGINX QUIC | Caddy |
|---------|---------|------------|-------|
| **License** | GPLv2 (open source) | BSD 2-clause | Apache 2.0 |
| **HTTP/3 Support** | Native (2.6+) | Experimental (1.25+) | Native (default) |
| **UDP Port Required** | Yes (443/udp) | Yes (443/udp) | Yes (443/udp) |
| **QUIC Library** | picotls / quictls | BoringSSL | quic-go (pure Go) |
| **Auto HTTPS** | Manual | Manual | Automatic (Let's Encrypt) |
| **Load Balancing** | Advanced (L4+L7) | Advanced (L7) | Built-in (L7) |
| **Configuration** | Complex, powerful | Complex, flexible | Simple Caddyfile |
| **Dynamic Reload** | Runtime API (zero-downtime) | `nginx -s reload` (brief) | JSON API (zero-downtime) |
| **Performance** | Highest throughput | High throughput | Good (Go runtime) |
| **Docker Image** | `haproxy:2.9` | Build from source | `caddy:2.8` |
| **GitHub Stars** | 6,500+ | 30,000+ | 72,000+ |
| **Best For** | High-traffic production load balancing | Organizations already on NGINX | Rapid deployment with zero config |

## Choosing the Right HTTP/3 Reverse Proxy

**Choose HAProxy if:**
- You need the highest throughput and most advanced load balancing features
- You're already using HAProxy and want to add HTTP/3 support
- You need Layer 4 (TCP/UDP) and Layer 7 (HTTP) load balancing in one tool
- You require runtime API for zero-downtime configuration changes

**Choose NGINX QUIC if:**
- Your organization is already standardized on NGINX
- You need NGINX-specific features (advanced caching, gRPC proxying, dynamic modules)
- You're willing to build from source with BoringSSL for QUIC support
- You need the flexibility of NGINX's module ecosystem

**Choose Caddy if:**
- You want HTTP/3 enabled by default with zero configuration
- Automatic HTTPS certificate management is a priority
- You prefer simple, readable configuration over complex tuning
- You're deploying smaller-scale services where ease of use matters more than peak throughput

## Docker Compose Full Stack

Here's a complete Docker Compose setup comparing all three HTTP/3 proxies with backend services:

```yaml
version: "3.8"
services:
  backend1:
    image: nginx:alpine
    volumes:
      - ./backend/index.html:/usr/share/nginx/html/index.html:ro

  backend2:
    image: nginx:alpine
    volumes:
      - ./backend/index.html:/usr/share/nginx/html/index.html:ro

  haproxy:
    image: haproxy:2.9
    ports:
      - "8080:443/tcp"
      - "8080:443/udp"
    volumes:
      - ./haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
    depends_on:
      - backend1
      - backend2

  caddy:
    image: caddy:2.8
    ports:
      - "8443:443/tcp"
      - "8443:443/udp"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
    depends_on:
      - backend1
      - backend2

volumes:
  caddy_data:
```

## Why Self-Host HTTP/3 Reverse Proxies?

Deploying HTTP/3 on your own infrastructure provides several advantages over relying on CDN-provided HTTP/3:

**Full protocol control:** Self-hosted HTTP/3 proxies let you configure QUIC parameters (idle timeout, initial congestion window, maximum stream count) to optimize for your specific network conditions and application patterns. CDN-provided HTTP/3 uses standardized defaults that may not match your workload.

**End-to-end optimization:** When you terminate HTTP/3 at your own proxy, you can optimize the entire request path — from QUIC connection establishment through backend routing, caching, and response delivery. CDN-terminated HTTP/3 may add latency if the CDN edge is geographically distant from your origin.

**Compliance and data sovereignty:** HTTP/3 proxy logs contain detailed information about client connections, request patterns, and response times. For organizations subject to data retention regulations, keeping this telemetry on-premises ensures compliance without relying on third-party audit processes.

**Cost efficiency:** High-traffic websites processing millions of HTTP/3 requests daily can save significantly by running their own reverse proxy infrastructure rather than paying CDN egress fees and per-request charges.

For HAProxy-specific management and monitoring, see our [HAProxy dataplane API and management tools guide](../2026-04-24-haproxy-dataplane-api-vs-prometheus-exporter-vs-runtime-api-self-hosted-haproxy-management-guide/). For mutual TLS configurations across multiple proxy options, check our [mTLS with NGINX, Caddy, Traefik guide](../2026-04-24-self-hosted-mutual-tls-mtls-nginx-caddy-traefik-envoy-guide/).

## FAQ

### What is HTTP/3 and how does it differ from HTTP/2?
HTTP/3 replaces TCP with QUIC (Quick UDP Internet Connections) as its transport protocol. Unlike HTTP/2 over TCP, where a single lost packet blocks all multiplexed streams, HTTP/3 handles each stream independently at the QUIC level. It also combines the TLS handshake with the transport handshake, reducing connection establishment from 3 round trips to 1.

### Do I need to open a UDP port for HTTP/3?
Yes. HTTP/3 runs over UDP port 443 (the same port number as HTTPS over TCP). Your firewall must allow both TCP and UDP traffic on port 443. Without UDP access, clients will fall back to HTTP/2 over TCP.

### Is HTTP/3 production-ready in all three tools?
Caddy has had stable HTTP/3 support since version 2.0 and enables it by default. HAProxy added production-ready QUIC/HTTP/3 support in version 2.6. NGINX's HTTP/3 support is still experimental in the open-source version (1.25+) but production-ready in NGINX Plus R28+.

### How do browsers discover HTTP/3 support?
Browsers discover HTTP/3 through the `Alt-Svc` (Alternative Services) HTTP header, which tells the browser that HTTP/3 is available on a specific port. After the first HTTPS connection (over HTTP/2 or HTTP/1.1), the browser reads this header and establishes a QUIC connection for subsequent requests. Caddy sends this header automatically; NGINX requires manual configuration; HAProxy includes it in its QUIC frontend.

### Can I run HTTP/3 behind a CDN like Cloudflare?
Yes, but the CDN terminates HTTP/3 at its edge, not at your origin. If you want end-to-end HTTP/3 (client-to-origin QUIC connection), you need to bypass the CDN or configure it to forward QUIC traffic to your origin. Most CDNs convert HTTP/3 to HTTP/2 for the origin connection.

### Does HTTP/3 improve performance for all websites?
HTTP/3 provides the most benefit on high-latency or lossy networks (mobile connections, satellite links, international routes). On low-latency, low-loss networks (datacenter-to-datacenter, LAN), the performance difference between HTTP/2 and HTTP/3 is marginal. For public-facing websites with global audiences, HTTP/3 typically improves page load times by 10-30%.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted HTTP/3 Reverse Proxies: HAProxy vs NGINX QUIC vs Caddy (2026)",
  "description": "Compare three self-hosted HTTP/3 reverse proxy solutions — HAProxy with QUIC, NGINX QUIC, and Caddy with native HTTP/3 — covering deployment, configuration, and performance.",
  "datePublished": "2026-05-21",
  "dateModified": "2026-05-21",
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
