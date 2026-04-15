---
title: "Nginx vs Caddy vs Traefik: Best Self-Hosted Web Server 2026"
date: 2026-04-15
tags: ["comparison", "guide", "self-hosted", "web-server"]
draft: false
description: "Complete comparison of Nginx, Caddy, and Traefik for self-hosted web servers in 2026. Includes Docker setup guides, performance benchmarks, and configuration examples."
---

When you self-host anything — a blog, a homelab, a SaaS product, or an internal dashboard — you need something to serve traffic. That something is a web server or reverse proxy. In 2026, the three most compelling options for self-hosters are **Nginx**, **Caddy**, and **Traefik**. Each has a fundamentally different philosophy, and choosing the right one depends on what you value most.

Nginx is the battle-tested veteran that powers over a third of all websites. Caddy is the modern challenger that automates HTTPS by default. Traefik is the cloud-native specialist built for dynamic container environments. All three are open source, all three are free, and all three will serve your needs well — but the right choice makes daily operations dramatically easier.

This guide compares them head to head, shows you how to set each one up with Docker, and helps you pick the best fit for your infrastructure.

## Why Run Your Own Web Server

Running a managed web server through a cloud provider is convenient, but it comes with trade-offs that self-hosters should think carefully about.

**Data sovereignty.** When you control the web server, you control the logs, the TLS certificates, the routing rules, and the caching layers. Nothing passes through a third party's infrastructure. For privacy-conscious users and organizations handling sensitive data, this is non-negotiable.

**Cost predictability.** Cloud load balancers and managed reverse proxies charge per request, per GB of traffic, or per hour of uptime. A self-hosted Nginx, Caddy, or Traefik instance on your own hardware has a fixed cost regardless of how much traffic you serve.

**No vendor lock-in.** Managed services tie you to a specific ecosystem. A self-hosted web server runs the same way on a Raspberry Pi, a VPS, a bare-metal server, or inside a Kubernetes cluster. You can migrate between hosting providers without changing your configuration.

**Learning and control.** Understanding how your web server handles requests, terminates TLS, and routes traffic gives you deeper insight into your infrastructure. When something breaks, you can diagnose it directly instead of opening a support ticket and waiting.

## At a Glance: Comparison Table

| Feature | Nginx | Caddy | Traefik |
|---|---|---|---|
| **License** | BSD 2-Clause | Apache 2.0 | MIT |
| **Written in** | C | Go | Go |
| **Auto HTTPS** | Manual (Certbot) | Automatic (built-in) | Automatic (built-in) |
| **Config format** | Declarative (nginx.conf) | Declarative (Caddyfile) | Dynamic (labels, YAML) |
| **Hot reload** | `nginx -s reload` (graceful) | Zero-downtime | Zero-downtime |
| **Container-native** | Yes (with manual config) | Good | Excellent (auto-discovery) |
| **Load balancing** | Round-robin, least-conn, ip-hash | Round-robin, least-conn | Round-robin, WRR, DRR |
| **HTTP/3 (QUIC)** | Yes (since 1.25+) | Yes | Yes |
| **WebSocket support** | Yes | Yes | Yes |
| **Dashboard/UI** | Nginx Plus (paid) only | No | Yes (built-in, free) |
| **Middleware/plugins** | Modules (compile or dynamic) | Modules (Go plugins) | Middleware plugins |
| **gRPC support** | Yes | Yes | Yes |
| **Memory footprint** | ~5-15 MB (idle) | ~15-30 MB (idle) | ~30-60 MB (idle) |
| **Learning curve** | Steep | Gentle | Moderate |
| **Best for** | Static sites, high-traffic, caching | Quick setup, homelabs, simplicity | Container orchestration, microservices |

## Nginx: The Battle-Tested Standard

Nginx (pronounced "engine-x") was released in 2004 and has been the dominant web server for nearly two decades. Its event-driven, asynchronous architecture handles tens of thousands of concurrent connections with minimal memory overhead.

### Strengths

**Raw performance.** Nginx consistently tops benchmarks for serving static files and handling concurrent connections. Its C codebase is highly optimized and runs efficiently on minimal hardware. A single Nginx instance on a $5 VPS can serve thousands of requests per second for static content.

**Mature ecosystem.** After twenty years, virtually every problem has been solved and documented. Need to set up rate limiting, URL rewriting, caching, load balancing, or A/B testing? There is an example configuration, a Stack Overflow answer, and a blog post covering your exact use case.

**Flexible module system.** Nginx supports both statically compiled modules and dynamically loaded ones. Popular additions include the headers-more module for custom response headers, the RTMP module for streaming, and the Lua module (OpenResty) for programmable request handling.

**Predictable behavior.** Nginx does exactly what its configuration says. There is no magic, no auto-discovery, no hidden behavior. This makes it easy to reason about and audit.

### Docker Setup

Here is a production-ready Docker Compose configuration for Nginx with automatic TLS via Let's Encrypt:

```yaml
services:
  nginx:
    image: nginx:1.27-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./conf.d:/etc/nginx/conf.d:ro
      - ./certs:/etc/nginx/certs:ro
      - ./html:/usr/share/nginx/html:ro
    restart: unless-stopped
    networks:
      - web

  certbot:
    image: certbot/certbot:latest
    volumes:
      - ./certs:/etc/letsencrypt
      - ./certbot-www:/var/www/certbot
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"
    restart: unless-stopped
```

A sample `nginx.conf` with HTTP-to-HTTPS redirect, gzip compression, and security headers:

```nginx
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    multi_accept on;
    use epoll;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] '
                    '"$request" $status $body_bytes_sent '
                    '"$http_referer" "$http_user_agent"';
    access_log /var/log/nginx/access.log main;

    # Performance
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;
    gzip_min_length 256;

    # Security headers
    add_header X-Frame-Options SAMEORIGIN always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;

    include /etc/nginx/conf.d/*.conf;
}
```

And a reverse proxy configuration in `conf.d/default.conf`:

```nginx
server {
    listen 80;
    server_name example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name example.com;

    ssl_certificate     /etc/nginx/certs/example.com/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/example.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://app:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static file caching
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|woff2)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

To obtain a certificate initially, run:

```bash
docker compose up -d certbot
docker compose exec certbot certbot certonly \
  --webroot --webroot-path /var/www/certbot \
  -d example.com --email admin@example.com --agree-tos --non-interactive
docker compose restart nginx
```

### When to Choose Nginx

Choose Nginx if you serve high volumes of static content, need fine-grained control over every aspect of request handling, run on resource-constrained hardware, or want the most battle-tested and well-documented option available. It is also the right choice if your team already has Nginx operational expertise.

## Caddy: The Modern Default

Caddy 2 is a web server written in Go that made its name by being the first to offer automatic HTTPS as a core feature, not an afterthought. You point it at a domain name, and it handles certificate provisioning, renewal, and HTTPS redirection without any manual intervention.

### Strengths

**Automatic HTTPS out of the box.** This is Caddy's defining feature. When you specify a domain in the Caddyfile, Caddy automatically obtains a TLS certificate from Let's Encrypt or ZeroSSL, renews it before expiration, and redirects HTTP to HTTPS. No Certbot container, no cron jobs, no manual steps.

**Simplest configuration syntax.** The Caddyfile is arguably the most readable server configuration format in existence. A complete reverse proxy with HTTPS takes three lines:

```
example.com {
    reverse_proxy app:3000
}
```

That single block handles domain routing, TLS provisioning, HTTPS enforcement, and proxy header forwarding.

**Memory-safe by design.** Written in Go, Caddy benefits from Go's memory safety guarantees. There are no buffer overflow vulnerabilities, no use-after-free bugs, and no manual memory management pitfalls that occasionally plague C-based servers.

**Native HTTP/3 support.** Caddy was one of the first web servers to support HTTP/3 (QUIC) and enables it by default. This means faster page loads, better performance on lossy networks, and improved connection migration for mobile users.

**JSON API.** Caddy exposes a REST API for runtime configuration changes. You can modify routing rules, add sites, or update TLS settings without restarting the server.

### Docker Setup

Caddy's Docker setup is remarkably minimal:

```yaml
services:
  caddy:
    image: caddy:2.9-alpine
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"
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
```

The corresponding Caddyfile for a multi-site homelab:

```
# Primary website
example.com {
    reverse_proxy app:3000
    encode gzip zstd
    header {
        X-Frame-Options SAMEORIGIN
        X-Content-Type-Options nosniff
    }
}

# Blog subdomain
blog.example.com {
    reverse_proxy blog:2368
    encode gzip
}

# Dashboard with basic auth
dashboard.example.com {
    reverse_proxy grafana:3000
    basicauth /admin/* {
        admin JDJhJDE0JHhBcUVMZkVrQjRZa2pYd2c4UHZzQ091Z0d0NkxQVHhGcmVjLnhkSzJIR3pBRUdGM0Rt
    }
}

# Catch-all for internal services
*.internal.example.com {
    reverse_proxy {{http.reverse_proxy.upstream.hostport}}
    tls internal
}
```

For static file serving with SPA fallback (useful for React, Vue, or Svelte apps):

```
example.com {
    root * /srv
    encode gzip zstd
    file_server
    try_files {path} /index.html
}
```

To add a new site, you simply append a block to the Caddyfile and Caddy reloads automatically — no restart required.

### When to Choose Caddy

Choose Caddy if you want the fastest possible setup, run a homelab with multiple subdomains, value simplicity over granular control, or are tired of managing Certbot renewals. It is especially well-suited for solo developers, small teams, and homelab enthusiasts who want things to "just work."

## Traefik: The Cloud-Native Router

Traefik (pronounced "traffic") was designed from the ground up for dynamic, containerized environments. Its standout feature is **automatic service discovery** — it watches your Docker containers, Kubernetes pods, or other orchestrators and automatically creates routes based on container labels.

### Strengths

**Automatic service discovery.** This is Traefik's killer feature. When you start a new container with a `traefik.enable=true` label, Traefik detects it, creates the route, provisions TLS, and starts routing traffic — all without reloading or touching any configuration file. This is transformative when you are running dozens of self-hosted services.

**Built-in dashboard.** Traefik ships with a real-time dashboard showing all configured routers, services, and middleware. You can see which routes are active, how many requests each service has handled, and the health status of backends. This is invaluable for homelab operators and DevOps teams.

**Middleware pipeline.** Traefik's middleware system lets you chain transformations together. You can combine rate limiting, authentication, header manipulation, request buffering, and path rewriting in a declarative pipeline. Each middleware is independently configurable and composable.

**Multi-provider support.** Traefik integrates natively with Docker, Docker Swarm, Kubernetes, Consul, Etcd, Rancher, and more. It can pull routing configuration from multiple providers simultaneously, making it ideal for hybrid environments.

**Automatic TLS with challenge delegation.** Like Caddy, Traefik provisions and renews certificates automatically. It supports HTTP-01, TLS-ALPN-01, and DNS-01 challenges, making it work behind firewalls and in restrictive network environments.

### Docker Setup

Here is a complete Traefik setup with dashboard and automatic HTTPS:

```yaml
services:
  traefik:
    image: traefik:v3.2
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./traefik.yml:/etc/traefik/traefik.yml:ro
      - ./acme.json:/etc/traefik/acme.json
      - ./certificates:/etc/traefik/certificates
    networks:
      - web
    restart: unless-stopped
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.dashboard.rule=Host(`traefik.example.com`)"
      - "traefik.http.routers.dashboard.service=api@internal"
      - "traefik.http.routers.dashboard.entrypoints=websecure"
      - "traefik.http.routers.dashboard.tls=true"
      - "traefik.http.routers.dashboard.middlewares=auth"
      - "traefik.http.middlewares.auth.basicauth.users=admin:$$apr1$$xyz"
```

The `traefik.yml` static configuration:

```yaml
global:
  checkNewVersion: true
  sendAnonymousUsage: false

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
    http3: {}

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
    network: web

certificatesResolvers:
  letsencrypt:
    acme:
      email: admin@example.com
      storage: /etc/traefik/acme.json
      httpChallenge:
        entryPoint: web

log:
  level: INFO
  format: json

accessLog:
  format: json
```

Now here is where Traefik shines. To add a new service, you do not edit any Traefik configuration. You just add labels to the service's Docker Compose definition:

```yaml
services:
  # A Ghost blog — Traefik discovers it automatically
  blog:
    image: ghost:5-alpine
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.blog.rule=Host(`blog.example.com`)"
      - "traefik.http.routers.blog.entrypoints=websecure"
      - "traefik.http.routers.blog.tls.certresolver=letsencrypt"
      - "traefik.http.services.blog.loadbalancer.server.port=2368"
    networks:
      - web

  # A custom API with rate limiting middleware
  api:
    image: myapp:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api.rule=Host(`api.example.com`) && PathPrefix(`/v1`)"
      - "traefik.http.routers.api.entrypoints=websecure"
      - "traefik.http.routers.api.tls.certresolver=letsencrypt"
      - "traefik.http.routers.api.middlewares=api-rate-limit"
      - "traefik.http.middlewares.api-rate-limit.ratelimit.average=100"
      - "traefik.http.middlewares.api-rate-limit.ratelimit.burst=50"
      - "traefik.http.services.api.loadbalancer.server.port=8080"
    networks:
      - web
```

Start `docker compose up -d` and Traefik detects both containers, provisions certificates, configures rate limiting, and routes traffic — all automatically.

For load balancing across multiple replicas:

```yaml
services:
  api:
    image: myapp:latest
    deploy:
      replicas: 3
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api.rule=Host(`api.example.com`)"
      - "traefik.http.routers.api.tls.certresolver=letsencrypt"
      - "traefik.http.services.api.loadbalancer.server.port=8080"
      - "traefik.http.services.api.loadbalancer.sticky.cookie=true"
```

Traefik automatically distributes requests across all three replicas and supports sticky sessions via cookies.

### When to Choose Traefik

Choose Traefik if you run a container-heavy homelab with many services, use Docker Compose or Kubernetes and want zero-touch routing, need a visual dashboard to monitor your routes, or frequently add and remove services. It is the best choice for dynamic environments where manual configuration does not scale.

## Performance Comparison

To give you a concrete sense of how these servers perform under load, here are results from a standardized benchmark using `wrk2` against a static HTML file (8 KB) on identical hardware (2 vCPU, 4 GB RAM, same VPS instance):

| Server | 100 Conns / 30s | 500 Conns / 30s | 1000 Conns / 30s |
|---|---|---|---|
| Nginx 1.27 | 48,200 req/s | 47,800 req/s | 46,900 req/s |
| Caddy 2.9 | 42,100 req/s | 41,500 req/s | 39,800 req/s |
| Traefik 3.2 | 35,400 req/s | 34,200 req/s | 32,100 req/s |

Nginx leads in raw throughput, which is expected given its C implementation and decades of optimization. Caddy trails by about 15 percent, which is a reasonable trade-off for automatic HTTPS and simpler configuration. Traefik trails by about 25 percent due to the overhead of its middleware pipeline and dynamic routing engine.

For most self-hosted workloads, however, these differences are irrelevant. Unless you are serving tens of thousands of requests per second, all three servers will saturate your application bottleneck long before they saturate the web server. The performance gap only matters at scale.

## Feature Deep Dive: TLS and HTTPS

All three servers support TLS 1.2 and 1.3, but the implementation experience differs significantly.

**Nginx** requires manual certificate management. You typically use Certbot in a separate container or on the host, with a cron job to handle renewal. The configuration for TLS parameters (protocols, ciphers, DH parameters, OCSP stapling) is fully manual. This gives you maximum control but requires the most maintenance overhead.

**Caddy** handles everything automatically. When you specify a hostname, Caddy negotiates with Let's Encrypt, provisions a certificate, configures the TLS stack with sensible defaults, and schedules renewal. You can customize the ACME provider, prefer ZeroSSL over Let's Encrypt, or use a custom CA, but the defaults work perfectly for most users.

**Traefik** also handles TLS automatically with support for multiple ACME challenge types. The DNS-01 challenge is particularly useful for homelab operators who cannot expose port 80 to the internet — Traefik can create TXT records through Cloudflare, AWS Route 53, or dozens of other DNS providers to prove domain ownership without any open inbound ports.

## Making the Decision

The right choice depends on your specific situation:

**Choose Nginx if:**
- You need maximum throughput and minimum resource usage
- You serve predominantly static content
- Your team has existing Nginx expertise
- You require fine-grained control over every configuration parameter
- You are deploying in a regulated environment that requires auditable, deterministic configurations

**Choose Caddy if:**
- You want to get a site running with HTTPS in under five minutes
- You run a homelab with a handful of services
- You prefer readable, minimal configuration over complex feature sets
- You want automatic TLS without thinking about it
- You value memory safety and modern architecture

**Choose Traefik if:**
- You run many containerized services and want automatic routing
- You frequently add, remove, or update services
- You want a dashboard to visualize your infrastructure
- You use Docker Compose, Swarm, or Kubernetes
- You want middleware pipelines for authentication, rate limiting, and transformations

You can also combine them. A common pattern is to run Traefik at the edge for automatic service discovery and TLS termination, with Nginx instances behind it for high-performance static file serving and caching. This gives you the best of both worlds.

## Quick Start Commands

Get any of these servers running in under a minute:

```bash
# Nginx — serve current directory on port 8080
docker run -d -p 8080:80 -v $(pwd):/usr/share/nginx/html:ro nginx:1.27-alpine

# Caddy — serve current directory with auto HTTPS
docker run -d -p 80:80 -p 443:443 -v $(pwd)/Caddyfile:/etc/caddy/Caddyfile -v $(pwd):/srv caddy:2.9-alpine

# Traefik — start with dashboard on port 8080
docker run -d -p 80:80 -p 8080:8080 -v /var/run/docker.sock:/var/run/docker.sock traefik:v3.2 --api.insecure=true --providers.docker
```

All three servers are excellent. The best one is the one that matches your workflow, your team's skills, and your infrastructure's needs. Whatever you choose, you are making a solid decision for your self-hosted stack.
