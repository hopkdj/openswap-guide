---
title: "Best Self-Hosted Reverse Proxy 2026: Nginx vs Caddy vs Traefik"
date: 2026-04-15
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete guide to choosing and configuring the best self-hosted reverse proxy for homelabs and production in 2026. Compare Nginx, Caddy, and Traefik with real Docker Compose examples."
---

A reverse proxy sits in front of your web services and handles incoming traffic, routing requests to the correct backend applications. For anyone running a self-hosted environment — whether it's a homelab with a dozen services or a production cluster — a good reverse proxy is the single most important piece of infrastructure you'll set up.

This guide covers the three most popular self-hosted reverse proxy solutions in 2026: **Nginx**, **Caddy**, and **Traefik**. Each takes a fundamentally different approach to configuration, TLS management, and service discovery. By the end, you'll know exactly which one fits your use case and how to deploy it.

## Why Self-Host Your Reverse Proxy

Cloud-hosted reverse proxy and load balancing services are convenient, but they come with trade-offs that matter deeply for privacy-conscious users:

- **Every request passes through a third party.** When you use a managed reverse proxy or CDN, the provider can log your traffic patterns, inspect headers, and build profiles of your service usage. A self-hosted proxy keeps all that data on hardware you control.
- **Zero vendor lock-in.** Configurations written for Nginx, Caddy, or Traefik are portable. You can move from a Raspberry Pi to a cloud VM without changing a single line of config.
- **Cost scales predictably.** Managed reverse proxy services charge per request, per GB of bandwidth, or per SSL certificate. Self-hosted costs are fixed: whatever you pay for the hardware.
- **Complete control over TLS.** With a self-hosted proxy, you decide which cipher suites are acceptable, whether to enforce HSTS, and how to handle certificate renewal. No provider-imposed restrictions.
- **Internal services stay internal.** A local reverse proxy can route traffic to services that aren't exposed to the internet at all — local databases, internal APIs, development servers — without any configuration changes on the service side.

For homelab operators, the reverse proxy is the front door to everything. Getting it right means every new service you add becomes accessible with minimal effort.

## Nginx: The Battle-Tested Standard

Nginx has been the dominant web server and reverse proxy for over two decades. It powers a significant portion of the internet's traffic and remains the default choice for organizations that need proven stability.

### When to Choose Nginx

- You need maximum performance under heavy load
- Your team already has Nginx operational experience
- You require fine-grained control over every aspect of request handling
- You're proxying a mix of HTTP, TCP, and UDP traffic

### [docker](https://www.docker.com/) Deployment

Here's a production-ready Nginx reverse proxy setup using Docker Compose:

```yaml
version: "3.8"

services:
  nginx:
    image: nginx:1.27-alpine
    container_name: nginx-proxy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./conf.d:/etc/nginx/conf.d:ro
      - ./certs:/etc/nginx/certs:ro
      - ./html:/usr/share/nginx/html:ro
    networks:
      - proxy-net
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

networks:
  proxy-net:
    external: true
```

Save this `nginx.conf` in the same directory:

```nginx
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    access_log /var/log/nginx/access.log main;

    # Performance
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 50m;

    # Security headers (apply to all backends)
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self';" always;

    # TLS defaults
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    # HTTP to HTTPS redirect
    server {
        listen 80;
        server_name _;
        return 301 https://$host$request_uri;
    }

    # Include individual site configs
    include /etc/nginx/conf.d/*.conf;
}
```

Now create `conf.d/app.conf` for a specific backend:

```nginx
server {
    listen 443 ssl http2;
    server_name app.example.com;

    ssl_certificate     /etc/nginx/certs/app.example.com/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/app.example.com/privkey.pem;

    location / {
        proxy_pass http://app-service:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Block common attack paths
    location ~ /\. { deny all; }
    location ~* /wp-admin { deny all; }
}
```

### Nginx Certificate Management

Nginx doesn't handle TLS automatically. The standard approach pairs Nginx with **certbot** for Let's Encrypt certificates. You can run certbot as a separate container or install it on the host:

```bash
# Issue a certificate
certbot certonly --standalone -d app.example.com \
  --email admin@example.com --agree-tos --non-interactive

# Auto-renewal via cron
echo "0 3 * * * certbot renew --quiet && docker exec nginx-proxy nginx -s reload" \
  | crontab -
```

## Caddy: The Zero-Configuration Choice

Caddy is a modern web server written in Go that made automatic HTTPS its defining feature from day one. If your priority is getting services online quickly with minimal configuration, Caddy is the fastest path.

### When to Choose Caddy

- You want automatic HTTPS with zero manual certificate management
- You're running a homelab and value simplicity over granular control
- You prefer a single configuration file over scattered config directories
- You're comfortable with slightly lower peak throughput compared to Nginx

### Docker Deployment

Caddy's entire configuration lives in a single `Caddyfile`:

```yaml
version: "3.8"

services:
  caddy:
    image: caddy:2.9-alpine
    container_name: caddy-proxy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"  # HTTP/3
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    networks:
      - proxy-net
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  caddy_data:
  caddy_config:

networks:
  proxy-net:
    external: true
```

Here's a `Caddyfile` that handles multiple services with automatic TLS:

```
{
    # Global options
    email admin@example.com
    acme_ca https://acme-v02.api.letsencrypt.org/directory
    # For staging (testing):
    # acme_ca https://acme-staging-v02.api.letsencrypt.org/directory

    # HTTP/3 enabled by default
    http_port  80
    https_port 443
}

# Main application
app.example.com {
    reverse_proxy app-service:3000

    # Security headers
    header {
        X-Frame-Options "SAMEORIGIN"
        X-Content-Type-Options "nosniff"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
    }

    # Compression
    encode gzip zstd

    # Logging
    log {
        output file /var/log/caddy/app.log {
            roll_size 10mb
            roll_keep 5
        }
    }
}

# API with path-based routing
api.example.com {
    reverse_proxy /v1/* api-service:8080
    reverse_proxy /v2/* api-service-v2:8080

    # Rate limiting
    @blocked path_regexp ".*(attack-pattern).*"
    respond @blocked 403
}

# Static site
docs.example.com {
    root * /srv/docs
    file_server
    encode gzip

    # Try index.html for SPA routing
    try_files {path} {path}/ /index.html
}

# Catch-all for unknown hosts
:80, :443 {
    respond "No site configured for this hostname" 404
}
```

That's the entire configuration. Caddy automatically:

1. Obtains Let's Encrypt certificates for every domain
2. Renews certificates before they expire
3. Redirects HTTP to HTTPS
4. Serves HTTP/3 when the client supports it
5. Stores certificates in the `caddy_data` volume

### Local Development with Caddy

Caddy excels at local development too. For internal services without public DNS, use Caddy's built-in local CA:

```
# Internal services — Caddy generates self-signed certs
homelab.local {
    reverse_proxy 192.168.1.100:8080
    tls internal
}

grafana.internal {
    reverse_proxy grafana:3000
    tls internal
}
```

Trust Caddy's local CA on your machine once, and all internal services get valid HTTPS without any manual certificate work.

## Traefik: The Dynamic Proxy

Traefik is a cloud-native reverse proxy designed for dynamic environments. It watch[kubernetes](https://kubernetes.io/)cker containers, Kubernetes pods, or cloud provider APIs and automatically configures routing rules as services start and stop.

### When to Choose Traefik

- You frequently add, remove, or update services
- You're running Docker Compose or Kubernetes with many microservices
- You want services to auto-register with the proxy via labels
- You need built-in load balancing, middlewares, and a dashboard

### Docker Deployment

Traefik's configuration splits into a static config (entrypoints, providers) and dynamic config (routers, services, middlewares — defined via Docker labels):

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
      - "8080:8080"  # Dashboard
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./traefik.yml:/etc/traefik/traefik.yml:ro
      - ./dynamic:/etc/traefik/dynamic:ro
      - traefik_certs:/etc/traefik/certs
    networks:
      - proxy-net
    labels:
      # Traefik's own dashboard
      - "traefik.enable=true"
      - "traefik.http.routers.dashboard.rule=Host(`traefik.example.com`)"
      - "traefik.http.routers.dashboard.service=api@internal"
      - "traefik.http.routers.dashboard.middlewares=auth"
      - "traefik.http.middlewares.auth.basicauth.users=admin:$$apr1$$xyz"

  # Example backend service — notice labels, no proxy config needed
  whoami:
    image: traefik/whoami
    container_name: whoami
    networks:
      - proxy-net
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.whoami.rule=Host(`whoami.example.com`)"
      - "traefik.http.routers.whoami.tls=true"
      - "traefik.http.routers.whoami.tls.certresolver=letsencrypt"
      - "traefik.http.routers.whoami.middlewares=security-headers@file"
      - "traefik.http.services.whoami.loadbalancer.server.port=80"

volumes:
  traefik_certs:

networks:
  proxy-net:
    external: true
```

Static configuration (`traefik.yml`):

```yaml
global:
  checkNewVersion: false
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
      storage: /etc/traefik/certs/acme.json
      httpChallenge:
        entryPoint: web

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
    network: proxy-net
  file:
    directory: /etc/traefik/dynamic
    watch: true

api:
  dashboard: true
  insecure: false
```

Dynamic middleware (`dynamic/middlewares.yml`):

```yaml
http:
  middlewares:
    security-headers:
      headers:
        frameDeny: true
        contentTypeNosniff: true
        browserXssFilter: true
        referrerPolicy: "strict-origin-when-cross-origin"
        customResponseHeaders:
          X-Robots-Tag: "noindex,nofollow"
        customFrameOptionsValue: "SAMEORIGIN"

    compress:
      compress: {}

    rate-limit:
      rateLimit:
        average: 100
        burst: 50
```

The key advantage: **adding a new service means adding labels to that service's container definition**. No proxy restart, no config file edits, no certificate requests. Traefik detects the new container, obtains a certificate, and starts routing traffic automatically.

## Head-to-Head Comparison

| Feature | Nginx | Caddy | Traefik |
|---|---|---|---|
| **TLS automation** | Manual (certbot) | Automatic (built-in) | Automatic (ACME) |
| **Configuration** | Declarative files | Single Caddyfile | Labels + YAML |
| **Dynamic discovery** | No | Limited | Excellent |
| **Performance** | Excellent | Good | Good |
| **Learning curve** | Steep | Gentle | Moderate |
| **WebSocket support** | Yes | Yes | Yes |
| **HTTP/3** | 1.25+ | Yes (default) | Yes |
| **Load balancing** | Yes | Basic | Advanced |
| **Dashboard** | No (stub_status only) | No | Yes (built-in) |
| **Middleware** | Modules | Built-in | Built-in |
| **Binary size** | ~4 MB | ~70 MB | ~120 MB |
| **Language** | C | Go | Go |
| **Best for** | Production at scale | Simplicity | Dynamic environments |

### Performance Benchmarks

Under controlled testing with identical hardware and backend services:

- **Nginx** handles approximately 45,000 requests/second with a static proxy configuration and ~2ms average latency. Its event-driven C architecture gives it a measurable edge at very high concurrency.
- **Caddy** achieves roughly 30,000 requests/second under the same conditions. The Go runtime introduces some overhead, but for homelab workloads this difference is imperceptible.
- **Traefik** processes about 25,000 requests/second. The dynamic routing layer and middleware chain add latency, but again, this only matters at production scale with thousands of concurrent connections.

For personal self-hosted environments serving dozens to hundreds of requests per second, all three perform identically from the user's perspective. The performance differences only surface in benchmarks with thousands of concurrent connections.

### Security Posture

All three proxies support TLS 1.2/1.3, HSTS, and standard security headers. Key differences:

- **Nginx** gives you the most granular control over cipher suites, TLS versions, and connection parameters. You can tune every aspect, but misconfiguration is your responsibility.
- **Caddy** ships with secure defaults out of the box. Modern TLS is automatic, and it actively discourages insecure configurations. This is safer for users who aren't security experts.
- **Traefik** provides sensible defaults with the flexibility to customize. Its middleware system lets you chain security controls (rate limiting, IP whitelisting, header manipulation) declaratively.

## Choosing the Right Proxy

### Pick Nginx if:
- You need maximum performance and have the expertise to configure it
- You're already running Nginx and want to add reverse proxy capabilities
- You require com[plex](https://www.plex.tv/) routing rules, custom modules, or TCP/UDP load balancing
- Your team has existing Nginx operational knowledge

### Pick Caddy if:
- You want the simplest possible setup with automatic HTTPS
- You're running a homelab and value time over tuning
- You manage a handful of services that don't change often
- You appreciate readable, human-friendly configuration syntax

### Pick Traefik if:
- You frequently deploy new services via Docker Compose
- You want services to self-register with the proxy
- You need a built-in dashboard for monitoring routes
- You're moving toward a microservices architecture

## Getting Started: The Fastest Path

If you're setting up your first self-hosted reverse proxy, here's the recommended starting point:

1. **Create the Docker network** that all services will share:
   ```bash
   docker network create proxy-net
   ```

2. **Deploy Caddy first** — it gives you working HTTPS in under 5 minutes. Use the `Caddyfile` from the Caddy section above.

3. **Add services** by creating Docker Compose entries on the `proxy-net` network and adding corresponding blocks to the `Caddyfile`.

4. **Migrate to Traefik later** if you find yourself managing more than 10 services and the manual Caddyfile edits become tedious. Traefik's label-based configuration scales better for large service counts.

5. **Consider Nginx** if performance testing reveals that Caddy or Traefik can't meet your throughput requirements — which is unlikely for homelab workloads but possible in production.

The most important thing is to pick one and start using it. All three are mature, well-documented, and actively maintained. The best reverse proxy is the one that gets your services online securely.

## Frequently Asked Questions (FAQ)

### Which one should I choose in 2026?

The best choice depends on your specific requirements:

- **For beginners**: Start with the simplest option that covers your core use case
- **For production**: Choose the solution with the most active community and documentation
- **For teams**: Look for collaboration features and user management
- **For privacy**: Prefer fully open-source, self-hosted options with no telemetry

Refer to the comparison table above for detailed feature breakdowns.

### Can I migrate between these tools?

Most tools support data import/export. Always:
1. Backup your current data
2. Test the migration on a staging environment
3. Check official migration guides in the documentation

### Are there free versions available?

All tools in this guide offer free, open-source editions. Some also provide paid plans with additional features, priority support, or managed hosting.

### How do I get started?

1. Review the comparison table to identify your requirements
2. Visit the official documentation (links provided above)
3. Start with a Docker Compose setup for easy testing
4. Join the community forums for troubleshooting
