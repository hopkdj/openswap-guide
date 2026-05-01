---
title: "H2O vs OpenLiteSpeed vs Caddy — Self-Hosted HTTP/3 Web Servers (2026)"
date: 2026-05-01T09:30:00+00:00
tags: ["web-server", "http3", "reverse-proxy", "self-hosted", "performance", "docker"]
draft: false
---

Choosing the right web server for your self-hosted infrastructure directly impacts page load times, TLS negotiation speed, and server resource consumption. In 2026, HTTP/3 (QUIC) support has moved from experimental to production-ready, making it a key differentiator between modern web servers.

This guide compares three HTTP/3-capable web servers you can self-host: **H2O**, **OpenLiteSpeed**, and **Caddy**. We'll cover architecture, performance, Docker deployment, configuration complexity, and use-case fit.

## Quick Comparison

| Feature | H2O | OpenLiteSpeed | Caddy |
|---|---|---|---|
| **GitHub Stars** | 11,448 | 1,432 | 71,974 |
| **Language** | C | C++ | Go |
| **HTTP/3 (QUIC)** | ✅ Native | ✅ Native (QUIC) | ✅ Native (quic-go) |
| **Automatic HTTPS** | ❌ Manual | ❌ Manual | ✅ Built-in (ACME) |
| **Config Format** | YAML | Web GUI / Conf | Caddyfile (declarative) |
| **Reverse Proxy** | ✅ | ✅ | ✅ |
| **Load Balancing** | ✅ mruby handler | ✅ | ✅ |
| **Docker Image** | Official | Official (litespeedtech) | Official (caddy) |
| **Last Updated** | 2026-04-30 | 2026-04-25 | 2026-04-30 |
| **Best For** | HTTP/3 performance, low-level control | PHP hosting, shared hosting environments | Simplicity, automatic TLS, modern stacks |

## H2O — The Optimized HTTP Server

[H2O](https://github.com/h2o/h2o) is a high-performance web server written in C, developed by Kazuho Oku (a key contributor to the HTTP/2 and HTTP/3 standards). It is designed to minimize latency for HTTP/2 and HTTP/3 traffic, making it an excellent choice for performance-critical deployments.

**Key strengths:**
- Industry-leading HTTP/3/QUIC implementation
- Low memory footprint with efficient event-driven architecture
- Built-in support for mruby scripting for dynamic request handling
- FastCGI and proxy support for backend applications

**H2O Docker Compose deployment:**

```yaml
version: "3"
services:
  h2o:
    image: ghcr.io/h2o/h2o:latest
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"  # QUIC requires UDP
    volumes:
      - ./h2o.conf:/etc/h2o/h2o.conf:ro
      - ./certs:/etc/h2o/certs:ro
    restart: unless-stopped
    networks:
      - web

networks:
  web:
    driver: bridge
```

**Sample H2O configuration (`h2o.conf`):**

```yaml
hosts:
  "example.com:443":
    listen:
      port: 443
      ssl:
        certificate-file: /etc/h2o/certs/fullchain.pem
        key-file: /etc/h2o/certs/privkey.pem
    paths:
      "/":
        file.dir: /var/www/html
        redirect:
          url: /index.html
          internal: YES
      "/api/":
        proxy.reverse.url: http://backend:8080/

access-log: /dev/stdout
error-log: /dev/stderr

http2-repaste-priority: YES
http3: ON
```

## OpenLiteSpeed — PHP-Optimized Web Server

[OpenLiteSpeed](https://github.com/litespeedtech/openlitespeed) is the open-source edition of LiteSpeed Web Server, developed by LiteSpeed Technologies. It is optimized for PHP workloads and includes a built-in web-based administration interface.

**Key strengths:**
- Drop-in Apache replacement with `.htaccess` compatibility
- Built-in page caching (LSCache) for WordPress and other CMS platforms
- Web-based admin GUI for configuration management
- Event-driven architecture with excellent PHP processing via LSAPI

**OpenLiteSpeed Docker Compose deployment:**

```yaml
version: "3"
services:
  openlitespeed:
    image: litespeedtech/openlitespeed:latest
    ports:
      - "80:80"
      - "443:443"
      - "7080:7080"  # Admin GUI
      - "443:443/udp"  # QUIC
    volumes:
      - ./html:/usr/local/lsws/Example/html
      - ./conf:/usr/local/lsws/conf
      - ./logs:/usr/local/lsws/logs
    environment:
      - TZ=UTC
    restart: unless-stopped
```

OpenLiteSpeed's admin interface (port 7080) provides a point-and-click configuration experience, making it ideal for teams that prefer GUI management over text-based config files. For production, the QUIC listener must be enabled through the web admin panel or configuration files.

## Caddy — The Modern Web Server with Automatic HTTPS

[Caddy](https://github.com/caddyserver/caddy) is a modern, extensible web server written in Go. Its standout feature is **automatic HTTPS** — it obtains and renews TLS certificates from Let's Encrypt (or any ACME CA) with zero configuration.

**Key strengths:**
- Automatic HTTPS via ACME (Let's Encrypt, ZeroSSL, Google Trust Services)
- Simple, human-readable Caddyfile configuration syntax
- Native HTTP/3 support via the quic-go library
- Built-in reverse proxy, load balancing, and compression
- Extensible via Caddy modules (written in Go)

**Caddy Docker Compose deployment:**

```yaml
version: "3"
services:
  caddy:
    image: caddy:latest
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"  # HTTP/3 QUIC
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    restart: unless-stopped
    networks:
      - web

volumes:
  caddy_data:
  caddy_config:

networks:
  web:
    driver: bridge
```

**Sample Caddyfile:**

```
example.com {
    encode gzip zstd

    reverse_proxy /api/* backend:8080

    handle_path /static/* {
        root * /srv/static
        file_server
    }

    handle {
        root * /srv/www
        file_server
    }

    @blocked {
        path *.env *.git*
    }
    respond @blocked 403
}
```

## Performance Benchmarks

HTTP/3 performance is where these servers differ most. Here is a summary of how they compare across key metrics:

| Metric | H2O | OpenLiteSpeed | Caddy |
|---|---|---|---|
| **HTTP/1.1 req/s** | ~220K | ~180K | ~90K |
| **HTTP/2 req/s** | ~180K | ~160K | ~85K |
| **HTTP/3 req/s** | ~120K | ~100K | ~70K |
| **Memory (idle)** | ~8 MB | ~12 MB | ~25 MB |
| **TLS 1.3 Handshake** | ~0.8ms | ~1.2ms | ~1.5ms |
| **0-RTT Resumption** | ✅ | ✅ | ✅ |

*Benchmarks are approximate, based on community testing with `wrk` and `h2load` on equivalent hardware. Your results will vary based on workload, hardware, and configuration.*

**H2O** leads in raw performance due to its C implementation and highly optimized event loop. It was designed from the ground up for HTTP/2 and HTTP/3, with techniques like stream prioritization and connection coalescing built into the core.

**OpenLiteSpeed** sits in the middle, trading some raw throughput for PHP integration and admin GUI features. Its LSAPI provides significantly faster PHP processing than traditional FastCGI.

**Caddy** has the lowest raw throughput but compensates with ease of use, automatic TLS, and a rich plugin ecosystem. For most self-hosted workloads, the performance difference is negligible — your application backend will be the bottleneck, not the web server.

## When to Choose Each

### Choose H2O When:
- You need maximum HTTP/3 performance and lowest latency
- You're comfortable with YAML configuration and mruby scripting
- You're deploying at scale (CDN edge, API gateway)
- You want fine-grained control over HTTP/2 stream prioritization

### Choose OpenLiteSpeed When:
- You're hosting PHP applications (WordPress, Laravel, Magento)
- You want a web-based admin interface for configuration
- You need `.htaccess` compatibility for easy migration from Apache
- You want built-in page caching (LSCache) without additional plugins

### Choose Caddy When:
- You want automatic HTTPS with zero manual certificate management
- You value simple, readable configuration over raw performance
- You need a reverse proxy with built-in load balancing
- You're deploying a modern stack (Go, Node.js, Python) and want seamless integration

## HTTP/3 Migration Considerations

Migrating to HTTP/3 requires more than just choosing a new web server. Consider these infrastructure changes:

1. **UDP port 443 must be open** — QUIC runs over UDP, not TCP. Many firewalls block UDP 443 by default.
2. **Load balancer compatibility** — If you run behind a load balancer (HAProxy, NGINX), verify it supports QUIC passthrough or termination.
3. **CDN support** — Most CDNs (Cloudflare, Fastly) already proxy HTTP/3 traffic. Verify your CDN doesn't downgrade connections.
4. **Monitoring** — HTTP/3 metrics differ from HTTP/2. Ensure your monitoring stack (Prometheus, Grafana) can track QUIC-specific metrics like 0-RTT success rates and connection migration events.

## Why Self-Host Your Web Server?

Running your own web server gives you full control over TLS configuration, HTTP protocol versions, caching strategies, and security policies. Self-hosting eliminates dependency on managed hosting providers that may delay HTTP/3 adoption or impose restrictive configuration limits.

For organizations running reverse proxies, API gateways, or static content delivery, a self-hosted HTTP/3-capable server provides:

- **Full QUIC control** — Configure QUIC parameters, CID rotation, and connection migration policies
- **Custom TLS stacks** — Deploy specific TLS versions and cipher suites for compliance requirements
- **Zero vendor lock-in** — Migrate between cloud providers without changing your web server configuration
- **Cost savings** — Eliminate per-GB egress fees from managed CDN providers for internal traffic

For TLS configuration best practices, see our [mutual TLS (mTLS) guide covering NGINX, Caddy, Traefik, and Envoy](../2026-04-24-self-hosted-mutual-tls-mtls-nginx-caddy-traefik-envoy-guide-2026/). If you need a GUI-managed reverse proxy, check our [NGINX Proxy Manager vs SWAG vs Caddy Docker Proxy comparison](../2026-04-24-nginx-proxy-manager-vs-swag-vs-caddy-docker-proxy-self-hosted-reverse-proxy-gui-guide-2026/). For SNI-based TLS routing, our [SNI proxy guide with Caddy and HAProxy](../2026-04-26-sniproxy-vs-haproxy-vs-caddy-self-hosted-sni-proxy-tls-routing-guide-2026/) covers the details.

## FAQ

### Is HTTP/3 ready for production use?
Yes. As of 2026, all major browsers (Chrome, Firefox, Safari, Edge) support HTTP/3. Both H2O and Caddy have stable, production-ready QUIC implementations. OpenLiteSpeed's QUIC support is also mature and used in production by LiteSpeed's commercial customers.

### Does Caddy support HTTP/3 out of the box?
Yes. Caddy 2.x includes HTTP/3 support via the quic-go library. Simply open UDP port 443 alongside TCP 443, and Caddy will automatically serve HTTP/3 to compatible clients. No additional configuration is needed.

### Can H2O replace NGINX in my stack?
H2O can serve as a reverse proxy and static file server, similar to NGINX. However, H2O's configuration syntax (YAML + mruby) differs significantly from NGINX's. If you rely heavily on NGINX-specific modules (njs, stream, mail), migration requires effort. For pure HTTP/HTTPS proxying, H2O is a capable replacement.

### Does OpenLiteSpeed support automatic SSL certificate renewal?
No. OpenLiteSpeed does not have built-in ACME support like Caddy. You need to use an external tool like Certbot to obtain and renew certificates, then configure OpenLiteSpeed to use them. Some community scripts automate this process, but it is not a native feature.

### Which server uses the least memory?
H2O has the smallest memory footprint (~8 MB idle), followed by OpenLiteSpeed (~12 MB) and Caddy (~25 MB). For resource-constrained environments (Raspberry Pi, low-end VPS), H2O is the most efficient choice.

### Can I run multiple web servers on the same machine?
Yes, but they must listen on different ports. A common pattern is running Caddy as the edge TLS terminator (handling automatic HTTPS and HTTP/3) and proxying to H2O or OpenLiteSpeed on localhost for application serving. This combines Caddy's ease of TLS management with another server's performance or feature strengths.

### How do I test if HTTP/3 is working?
Use `curl --http3-only https://your-domain.com` (curl 7.66+ with HTTP/3 support) or check the Network tab in browser DevTools — look for `h3` in the Protocol column. Online tools like [http3check.net](https://http3check.net) can also verify your server's HTTP/3 support remotely.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "H2O vs OpenLiteSpeed vs Caddy — Self-Hosted HTTP/3 Web Servers (2026)",
  "description": "Compare three HTTP/3-capable self-hosted web servers: H2O, OpenLiteSpeed, and Caddy. Includes Docker Compose configs, performance benchmarks, and migration guidance.",
  "datePublished": "2026-05-01",
  "dateModified": "2026-05-01",
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
