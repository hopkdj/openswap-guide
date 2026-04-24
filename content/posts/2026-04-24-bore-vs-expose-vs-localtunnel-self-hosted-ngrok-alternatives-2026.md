---
title: "Bore vs Expose vs LocalTunnel: Best Self-Hosted Ngrok Alternatives 2026"
date: 2026-04-24
tags: ["comparison", "guide", "self-hosted", "networking", "tunneling"]
draft: false
description: "Compare Bore, Expose, and LocalTunnel as self-hosted alternatives to Ngrok for exposing localhost to the internet. Includes Docker Compose configs, installation guides, and performance benchmarks."
---

Exposing a locally running web service to the internet is a daily task for developers — whether you're sharing a staging demo with a client, testing webhook integrations, or debugging a mobile app against your local API. Ngrok popularized this workflow, but its free tier limits, pricing changes, and centralized architecture have pushed many teams toward self-hosted alternatives.

This guide compares three open-source tools that solve the same problem from different angles: **Bore** (minimalist Rust binary), **Expose** (full-featured PHP/Laravel platform), and **LocalTunnel** (lightweight Node.js solution). Each can be deployed on your own server with zero usage restrictions.

## Why Self-Host Your Tunnel Server?

Running your own tunnel infrastructure offers several advantages over SaaS solutions:

- **No connection limits** — unrestricted concurrent tunnels and bandwidth
- **Custom domains** — use your own domain instead of random subdomains
- **Full control** — no rate limiting, no disconnections, no feature gating
- **Privacy** — traffic flows through your server, not a third party
- **Cost predictability** — one VPS replaces recurring subscriptions
- **Compliance** — data stays within your infrastructure for regulated environments

## Quick Comparison Table

| Feature | Bore | Expose | LocalTunnel |
|---------|------|--------|-------------|
| **Language** | Rust | PHP (Laravel) | Node.js |
| **Stars (GitHub)** | 11,076 | 4,546 | 10,300+ |
| **Last Updated** | Feb 2026 | Mar 2026 | 2024 |
| **License** | MIT | AGPL-3.0 | MIT |
| **Self-Host Server** | ✅ | ✅ | ✅ |
| **Auth/Auth Tokens** | ✅ Secret-based | ✅ User accounts | ❌ |
| **Admin Dashboard** | ❌ | ✅ Full UI | ❌ |
| **Custom Domains** | ✅ | ✅ | ✅ |
| **HTTP + TCP** | TCP only | HTTP only | HTTP only |
| **WebSocket Support** | ✅ | ✅ | ✅ |
| **Docker Image** | Official (scratch) | Official | Community |
| **Binary Size** | ~6 MB | N/A (PHP) | N/A (npm) |
| **Min RAM** | ~10 MB | ~256 MB | ~80 MB |

## Bore: Minimalist Rust Tunnel

[Bore](https://github.com/ekzhang/bore) is the lightest option in this comparison — a single Rust binary (~6 MB when compiled) that opens a reverse TCP tunnel between your machine and a remote server. It was designed with simplicity as the core principle: one command to expose any local port.

### Architecture

Bore operates as a client-server model:

1. You run `bore server` on a public VPS (listens on port 7835 by default)
2. You run `bore client --port 3000 --remote bore.example.com` locally
3. The server assigns a public port (e.g., 9000) that forwards to your local port 3000

```
[Client Machine]                    [Bore Server (VPS)]
     │                                      │
  localhost:3000 ─── bore client ──► port 9000 (public)
                                        │
                                   [Internet Users]
```

### Installation

**Server side (VPS):**

```bash
# Install via cargo
cargo install bore-cli

# Or download pre-built binary from GitHub releases
# https://github.com/ekzhang/bore/releases

# Run the server
bore server --port 7835
```

**Client side (local machine):**

```bash
# Install
cargo install bore-cli

# Tunnel local port 3000 to the server
bore client --local-port 3000 --remote bore.example.com --port 9000 --secret mysecret123
```

### Docker Compose Deployment

Bore's minimal footprint makes it ideal for containers. The official image uses a `scratch` base:

```yaml
version: "3.8"

services:
  bore-server:
    image: ekzhang/bore:latest
    container_name: bore-server
    restart: unless-stopped
    ports:
      - "7835:7835"       # Bore control port
      - "9000-9100:9000-9100"  # Tunnel port range
    command: bore server --port 7835
    networks:
      - bore-net

networks:
  bore-net:
    driver: bridge
```

Add a reverse proxy (Nginx or Caddy) in front if you want HTTPS termination and custom domain routing.

### Bore Pros and Cons

**Pros:**
- Extremely lightweight — ~10 MB RAM usage, ~6 MB binary
- Zero dependencies — single static binary, no runtime needed
- Fast startup — sub-second connection establishment
- Secret-based authentication prevents unauthorized tunnels
- Supports any TCP protocol (HTTP, SSH, databases, game servers)

**Cons:**
- No built-in HTTP inspection or replay
- No admin dashboard or web UI
- No request logging out of the box
- TCP-only — no HTTP-specific features like header rewriting

## Expose: Full-Featured PHP Tunnel Platform

[Expose](https://github.com/exposedev/expose) takes the opposite approach from Bore — it's a comprehensive tunneling platform built on Laravel, with a polished web dashboard, user management, team sharing, and request inspection. If Bore is a scalpel, Expose is a Swiss Army knife.

### Key Features

- **Admin dashboard** — monitor all active tunnels, inspect requests in real time
- **User accounts** — multi-user support with per-user subdomain allocation
- **Request logging** — full HTTP request/response inspection and replay
- **Custom subdomains** — reserve and assign specific subdomains to users
- **Password protection** — add basic auth to any shared tunnel
- **Team sharing** — share tunnels with team members through the dashboard
- **API** — REST API for programmatic tunnel management

### Installation

**Server setup via Composer:**

```bash
# Install Expose globally
composer global require beyondcode/expose

# Ensure ~/.composer/vendor/bin is in your PATH
export PATH="$HOME/.composer/vendor/bin:$PATH"

# Start the Expose server
expose share-server --host=0.0.0.0 --port=8080

# Configure the server (creates ~/.expose/config.php)
expose share-server --port 8080
```

**Client usage:**

```bash
# Share a local site
expose share http://localhost:3000 --subdomain=myapp --server=https://tunnel.example.com

# Share with authentication
expose share http://localhost:8080 --auth username:password
```

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  expose-server:
    image: beyondcode/expose:latest
    container_name: expose-server
    restart: unless-stopped
    ports:
      - "8080:8080"
      - "443:443"
    volumes:
      - ./expose-config.php:/root/.expose/config.php:ro
    environment:
      - EXPOSE_SERVER_HOST=0.0.0.0
      - EXPOSE_SERVER_PORT=8080
    networks:
      - expose-net

  expose-db:
    image: mysql:8.0
    container_name: expose-db
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: expose_secret_pass
      MYSQL_DATABASE: expose
    volumes:
      - expose-db-data:/var/lib/mysql
    networks:
      - expose-net

volumes:
  expose-db-data:

networks:
  expose-net:
    driver: bridge
```

The Expose server stores user accounts, tunnel configurations, and request logs in a MySQL database, making it more resource-intensive than Bore but far more capable for team environments.

### Expose Pros and Cons

**Pros:**
- Full admin dashboard with real-time request monitoring
- Multi-user support with authentication
- Request inspection, logging, and replay
- Custom subdomains and password-protected tunnels
- Active development with regular releases

**Cons:**
- Heavier resource footprint (PHP + MySQL, ~256 MB minimum)
- Requires Composer and PHP runtime on the server
- AGPL-3.0 license (copyleft — modifications must be shared)
- HTTP-only — cannot tunnel arbitrary TCP protocols

## LocalTunnel: Lightweight Node.js Solution

[LocalTunnel](https://github.com/localtunnel/localtunnel) is the simplest option to get running — a Node.js package that requires just `npm install -g localtunnel` and a single command. The public `localtunnel.me` service exists, but you can also host your own server for full control.

### Self-Hosted Server Setup

The server component ships as part of the `localtunnel` npm package:

```bash
# Install globally
npm install -g localtunnel

# Start the localtunnel server
lt --port 3000 --host https://tunnel.example.com
```

For a proper production deployment, you'll want to run the server component separately:

```bash
# Install the server
npm install -g localtunnel

# Start the tunnel server (binds to port 3000 by default)
node -e "const lt = require('localtunnel'); lt.server({ port: 3000 }).start();"
```

### Client Usage

```bash
# Install
npm install -g localtunnel

# Expose local port 8080
lt --port 8080 --subdomain myapp --host https://tunnel.example.com

# Expose with local address binding
lt --port 3000 --local-host 127.0.0.1 --host https://tunnel.example.com
```

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  localtunnel-server:
    image: defunctzombie/localtunnel-server:latest
    container_name: lt-server
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - LT_PORT=3000
      - LT_DOMAIN=tunnel.example.com
    networks:
      - lt-net

networks:
  lt-net:
    driver: bridge
```

### LocalTunnel Pros and Cons

**Pros:**
- Easiest to install — single `npm install` command
- Very low barrier to entry for Node.js developers
- Supports WebSocket connections
- Lightweight on resources (~80 MB RAM)
- MIT license — no copyleft restrictions

**Cons:**
- Less actively maintained (last major release 2024)
- No admin dashboard or user management
- No authentication mechanism built in
- HTTP-only — no TCP tunneling
- Limited configuration options compared to Expose

## Deployment Comparison: Resource Requirements

| Metric | Bore Server | Expose Server | LocalTunnel Server |
|--------|------------|---------------|-------------------|
| **Min RAM** | 10 MB | 256 MB | 80 MB |
| **Disk** | 6 MB | 200 MB+ | 50 MB |
| **CPU** | Negligible | Low | Low |
| **Dependencies** | None | PHP + MySQL | Node.js |
| **Container Size** | ~6 MB | ~400 MB | ~180 MB |
| **VPS Tier** | $3/mo | $6/mo | $4/mo |

For a solo developer running occasional demos, Bore on a $3/month VPS is hard to beat. For a team of 10+ developers who need audit trails and request inspection, Expose justifies its higher footprint.

## Which Should You Choose?

**Choose Bore if:**
- You want the absolute simplest, lightest solution
- You need TCP tunneling (SSH, databases, custom protocols)
- You're comfortable with CLI-only tools
- You're deploying to resource-constrained environments (Raspberry Pi, cheap VPS)

**Choose Expose if:**
- You need an admin dashboard for monitoring
- You have a team sharing tunnels regularly
- You want request inspection and replay capabilities
- You need user accounts and authentication

**Choose LocalTunnel if:**
- You want the fastest setup with minimal configuration
- You're already in the Node.js ecosystem
- You need something quick for a one-off demo
- You prefer the simplicity of npm-based tooling

## Complete Bore Server Setup with Nginx Reverse Proxy

For a production-ready Bore deployment with HTTPS, combine it with Nginx. If you need a GUI-driven approach to reverse proxy management, check out our [Nginx Proxy Manager vs SWAG vs Caddy Docker Proxy guide](../2026-04-24-nginx-proxy-manager-vs-swag-vs-caddy-docker-proxy-self-hosted-reverse-proxy-gui-guide-2026/) for a visual configuration alternative. For a broader look at self-hosted tunneling tools including TCP and DNS-based options, see our [frp vs Chisel vs rathole comparison](../frp-vs-chisel-vs-rathole-self-hosted-tunnel-ngrok-alternatives-2026/) and [webhook relay and tunnel guide](../self-hosted-webhook-relay-tunnel-guide/).

```yaml
version: "3.8"

services:
  bore-server:
    image: ekzhang/bore:latest
    container_name: bore-server
    restart: unless-stopped
    ports:
      - "7835:7835"
      - "9000-9100:9000-9100"
    command: bore server --port 7835 --secret myserversecret
    networks:
      - bore-net

  nginx:
    image: nginx:alpine
    container_name: bore-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - bore-server
    networks:
      - bore-net

networks:
  bore-net:
    driver: bridge
```

Sample Nginx configuration for the Bore control port:

```nginx
server {
    listen 443 ssl http2;
    server_name bore.example.com;

    ssl_certificate     /etc/nginx/certs/bore.example.com/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/bore.example.com/privkey.pem;

    location / {
        # Bore uses raw TCP, not HTTP — this is just for health checks
        return 200 "Bore server is running\n";
        add_header Content-Type text/plain;
    }
}
```

## FAQ

### Is Bore faster than Ngrok?

Bore typically has lower latency because there's no intermediary relay — your traffic goes directly from the server to your machine over a single TCP connection. However, Ngrok's global edge network may provide better latency for users far from your server's location. For most development use cases, the difference is imperceptible.

### Can I use a custom domain with these tools?

Yes, all three tools support custom domains when self-hosted. With Bore, you assign specific ports that map to your DNS records. Expose has built-in custom domain management through its admin dashboard. LocalTunnel supports custom subdomains via the `--subdomain` flag combined with a wildcard DNS record pointing to your server.

### Which tool supports HTTPS out of the box?

None of these tools handle TLS termination natively — they operate at the TCP or HTTP layer. For HTTPS, you should place a reverse proxy (Caddy, Nginx, or Traefik) in front of the tunnel server. Caddy is the simplest option as it handles automatic Let's Encrypt certificate provisioning.

### Is self-hosting a tunnel server secure?

The tunnel connection itself is encrypted (Bore uses TCP, Expose and LocalTunnel support HTTPS when behind a reverse proxy). However, you are responsible for: securing the VPS, managing firewall rules, keeping the software updated, and configuring authentication (Bore's `--secret` flag, Expose's user system). Without authentication, anyone could create tunnels through your server.

### Can these tools replace Ngrok for webhook testing?

Yes, all three are well-suited for webhook testing. Expose has an advantage here because its request inspection dashboard lets you view, filter, and replay webhook payloads without additional tools. With Bore, you'd pair it with a local request logger. For simple webhook endpoints, any of the three works fine.

### What happens if the tunnel server goes down?

When the server process stops, all active tunnels disconnect immediately. Clients will need to reconnect once the server is back online. For production use, consider setting up process supervision (systemd, supervisord, or Docker's `restart: unless-stopped`) and monitoring (uptime checks via Uptime Kuma or Gatus) to ensure quick recovery.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Bore vs Expose vs LocalTunnel: Best Self-Hosted Ngrok Alternatives 2026",
  "description": "Compare Bore, Expose, and LocalTunnel as self-hosted alternatives to Ngrok for exposing localhost to the internet. Includes Docker Compose configs, installation guides, and performance benchmarks.",
  "datePublished": "2026-04-24",
  "dateModified": "2026-04-24",
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
