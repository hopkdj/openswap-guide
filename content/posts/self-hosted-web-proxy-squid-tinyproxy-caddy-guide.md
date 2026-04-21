---
title: "Best Self-Hosted Web Proxy in 2026: Squid vs Tinyproxy vs Caddy"
date: 2026-04-16
tags: ["comparison", "guide", "self-hosted", "privacy", "proxy"]
draft: false
description: "Complete guide to self-hosted web proxies in 2026. Compare Squid, Tinyproxy, and Caddy for caching, filtering, anonymizing, and reverse proxying with Docker deployment examples."
---

Running your own web proxy gives you full control over how your network traffic flows. Whether you want to cache frequently accessed content to reduce bandwidth, filter outbound requests for compliance, anonymize your browsing traffic, or reverse-proxy multiple backend services behind a single entry point, a self-hosted proxy is the cornerstone of a well-managed network.

In this guide, we'll compare three leading open-source web proxy solutions — **Squid**, **Tinyproxy**, and **Caddy** — and show you exactly how to deploy each one using [docker](https://www.docker.com/).

## Why Run Your Own Web Proxy?

A web proxy sits between your clients and the internet, intercepting and forwarding HTTP/HTTPS traffic according to rules you define. Here's why self-hosting matters:

- **Bandwidth savings** — Cache static assets (images, CSS, JavaScript) locally so repeat requests never leave your network. For a team of 50 developers pulling from the same package repositories, this can cut outbound traffic by 30–60%.
- **Content filtering** — Block ads, malware domains, or inappropriate categories at the network level, covering every device without installing browser extensions.
- **Privacy protection** — Strip tracking headers, hide your real IP from destination servers, and prevent DNS leaks by routing all traffic through your own infrastructure.
- **Compliance and auditing** — Log every request for regulatory purposes, enforce acceptable-use policies, and generate reports on bandwidth consumption per user or department.
- **Reverse proxying** — Route incoming requests to different backend services based on domain, path, or headers, while handling TLS termination and load balancing.

Commercial proxy services charge per gigabyte or per user. A self-hosted proxy on a $5/month VPS handles the same workload at a fraction of the cost, with zero data leaving your control.

## Squid: The Enterprise-Grade Forward Proxy

Squid is the most mature and feature-rich open-source web proxy available. First released in 1996, it remains the gold standard for organizations that need granular control over caching, access policies, and traffic inspection.

### When to Choose Squid

- You need hierarchical or sibling cache arrays for distributed caching across multiple sites.
- You want ICAP (Internet Content Adaptation Protocol) integration for antivirus scanning or content modification.
- You require detailed per-user, per-URL, or per-MIME-type access control lists (ACLs).
- You're running a medium-to-large network (20+ users) and need production-grade caching.

### Docker Deployment

Create a directory for your Squid configuration:

```bash
mkdir -p ~/squid-proxy/config
cd ~/squid-proxy
```

Write a `squid.conf` file in `config/`:

```
# squid.conf — Squid 6.x configuration

http_port 3128

# Allow local network
acl localnet src 192.168.1.0/24
acl localnet src 10.0.0.0/8
acl localnet src 172.16.0.0/12

# Allowed ports
acl Safe_ports port 80          # HTTP
acl Safe_ports port 443         # HTTPS
acl Safe_ports port 21          # FTP
acl Safe_ports port 1025-65535  # Unregistered ports

http_access deny !Safe_ports
http_access allow localnet
http_access deny all

# Caching
cache_dir ufs /var/spool/squid 4096 16 256
cache_mem 256 MB
maximum_object_size 512 MB

# Logging
access_log /var/log/squid/access.log squid
cache_log /var/log/squid/cache.log

# Hide client identity
forwarded_for delete
via off
request_header_access Referer deny all
request_header_access X-Forwarded-For deny all
```

Create the `docker-compose.yml`:

```yaml
version: "3.8"
services:
  squid:
    image: ubuntu/squid:latest
    container_name: squid-proxy
    restart: unless-stopped
    ports:
      - "3128:3128"
    volumes:
      - ./config/squid.conf:/etc/squid/squid.conf:ro
      - squid-cache:/var/spool/squid
      - squid-logs:/var/log/squid
    environment:
      - TZ=UTC

volumes:
  squid-cache:
  squid-logs:
```

Start the proxy:

```bash
docker compose up -d
```

Verify it's working:

```bash
curl -x http://localhost:3128 -I https://example.com
```

You should see HTTP headers returned through the proxy. If you want authentication, add these lines to `squid.conf`:

```
auth_param basic program /usr/lib/squid/basic_ncsa_auth /etc/squid/passwords
auth_param basic children 5
auth_param basic realm Squid Proxy
acl authenticated proxy_auth REQUIRED
http_access allow authenticated
```

Generate the password file with:

```bash
docker exec -it squid-proxy htpasswd -c /etc/squid/passwords proxyuser
```

### Performance Tips

Squid's cache size is defined by the `cache_dir` directive. The three numbers mean: storage type (ufs), total size in MB (4096), number of first-level directories (16), and second-level directories (256). For a busy proxy, bump `cache_mem` to 512 MB or higher and set `maximum_object_size` to accommodate the largest files you expect to cache (video files, ISO images, etc.).

For monitoring, enable SNMP in `squid.conf` and use `squidclient` for real-time stats:

```bash
squidclient -p 3128 mgr:info
```

## Tinyproxy: Lightweight and Simple

Tinyproxy is a minimal HTTP/HTTPS proxy designed for situations where Squid is overkill. Written in C with a tiny memory footprint (often under 5 MB of RAM), it's ideal for home labs, Raspberry Pi deployments, or small teams that need basic proxy functionality without com[plex](https://www.plex.tv/)ity.

### When to Choose Tinyproxy

- You're running on constrained hardware (Raspberry Pi, low-memory VPS).
- You need a simple forward proxy with minimal configuration.
- You don't need advanced caching — Tinyproxy focuses on forwarding, not storage.
- You want a quick setup for testing or temporary access.

### Docker Deployment

```bash
mkdir -p ~/tinyproxy/config
cd ~/tinyproxy
```

Create `tinyproxy.conf`:

```
# tinyproxy.conf

Port 8888

# Bind to all interfaces inside the container
Listen 0.0.0.0

# Allow all local traffic (restrict in production)
Allow 127.0.0.1
Allow 192.168.0.0/16
Allow 10.0.0.0/8

# Disable Via header for privacy
DisableViaHeader Yes

# Logging
Logfile "/var/log/tinyproxy/tinyproxy.log"
LogLevel Info

# Optional: block specific domains
# Filter "/etc/tinyproxy/filter"
# FilterURLs On

# Optional: custom header
AddHeader "X-Proxy-By" "Tinyproxy"
```

The `docker-compose.yml`:

```yaml
version: "3.8"
services:
  tinyproxy:
    image: monokal/tinyproxy:latest
    container_name: tinyproxy
    restart: unless-stopped
    ports:
      - "8888:8888"
    volumes:
      - ./config/tinyproxy.conf:/etc/tinyproxy/tinyproxy.conf:ro
    environment:
      - TZ=UTC
```

Start it:

```bash
docker compose up -d
```

Test the connection:

```bash
curl -x http://localhost:8888 -I https://httpbin.org/ip
```

### Domain Filtering

Tinyproxy supports URL-based filtering. Create a filter file:

```bash
echo -e "(\.google-analytics\.com)\n(\.facebook\.com)\n(\.doubleclick\.net)" > ~/tinyproxy/config/filter
```

Then add these lines to `tinyproxy.conf`:

```
Filter "/etc/tinyproxy/filter"
FilterURLs On
FilterDefaultDeny No
```

`FilterDefaultDeny No` means the listed patterns are blocked while everything else passes. Set it to `Yes` for a whitelist-only approach where only matching domains are allowed.

### Limitations

Tinyproxy does not cache content. Every request goes through to the origin server, so you won't see bandwidth savings. It also lacks authentication, ICAP support, and hierarchical caching. For these reasons, it's best suited for small-scale or temporary deployments.

## Caddy: The Modern Reverse Proxy

Caddy has rapidly become the go-to reverse proxy for modern web infrastructure. Its defining feature is **automatic HTTPS** — it obtains and renews TLS certificates from Let's Encrypt (or any ACME-compatible CA) with zero configuration. Combined with a clean, human-readable config syntax, Caddy is the easiest way to expose self-hosted services to the internet securely.

### When to Choose Caddy

- You need a reverse proxy to route traffic to multiple backend services.
- You want automatic TLS certificate management without Let's Encrypt manual renewals.
- You prefer a declarative, easy-to-read configuration file over verbose XML or INI-style configs.
- You're running a home lab, small business, or developer environment with multiple services on one server.

### Docker Deployment

```bash
mkdir -p ~/caddy-proxy/{config,data,sites}
cd ~/caddy-proxy
```

Create `Caddyfile`:

```
# Caddyfile — Reverse proxy configuration

# Global options
{
    email admin@example.com
    acme_ca https://acme-v02.api.letsencrypt.org/directory
    admin off
}

# Main domain — reverse proxy to a backend service
app.example.com {
    reverse_proxy backend-app:8080

    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
    }

    # Encode responses
    encode zstd gzip
}

# API subdomain with rate limiting
api.example.com {
    reverse_proxy backend-api:3000

    @blocked path /admin/* /debug/*
    respond @blocked 403
}

# Static site with file serving
docs.example.com {
    root * /srv/docs
    file_server
    encode gzip
}

# Fallback — handle anything else
:80 {
    respond "No site configured" 404
}
```

Create `docker-compose.yml`:

```yaml
version: "3.8"
services:
  caddy:
    image: caddy:2-alpine
    container_name: caddy-proxy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - ./data:/data
      - ./config:/config
      - ./sites:/srv/docs:ro
    networks:
      - proxy-net
    environment:
      - TZ=UTC

networks:
  proxy-net:
    driver: bridge
```

Start Caddy:

```bash
docker compose up -d
```

Caddy will automatically request TLS certificates for any domains defined in the Caddyfile that point to your server's IP. You can verify certificate status with:

```bash
docker exec caddy-proxy caddy list-certs
```

### The Caddyfile Advantage

Caddy's configuration language is intentionally simple. A reverse proxy takes one line:

```
example.com {
    reverse_proxy lo[nginx](https://nginx.org/)st:8080
}
```

Compare that to the equivalent Nginx configuration, which requires 10–15 lines including `server`, `listen`, `location`, `proxy_pass`, `proxy_set_header`, and various buffer settings. Caddy handles all of this automatically, including HTTP-to-HTTPS redirects.

For more complex routing, Caddy supports matchers, handle blocks, and named routes:

```
example.com {
    @api path /api/*
    @web not path /api/*

    handle @api {
        reverse_proxy api-server:3000
    }

    handle @web {
        reverse_proxy web-server:80
    }
}
```

### Built-in Features Worth Knowing

- **Automatic HTTPS renewal** — Caddy tracks certificate expiry and renews at 30 days before expiration. No cron jobs needed.
- **Compression** — The `encode` directive applies gzip or zstd compression to text-based responses, reducing bandwidth by 60–80%.
- **Header manipulation** — Add, remove, or modify response headers with the `header` directive.
- **Basic authentication** — Built-in `basicauth` directive with bcrypt password hashes.
- **Request rewriting** — `rewrite`, `uri`, and `redir` directives for URL manipulation.
- **Load balancing** — `reverse_proxy` accepts multiple backends with round-robin or least-connections strategies.

## Head-to-Head Comparison

| Feature | Squid | Tinyproxy | Caddy |
|---------|-------|-----------|-------|
| **Primary role** | Forward proxy + cache | Lightweight forward proxy | Reverse proxy |
| **Caching** | Full HTTP caching with disk storage | None | Static file serving only |
| **HTTPS/TLS** | TLS interception with manual cert setup | CONNECT tunneling (no interception) | Automatic Let's Encrypt |
| **Authentication** | Basic, Digest, NTLM, Kerberos | None built-in | Basic auth, headers |
| **Access control** | ACLs (IP, user, URL, time, method) | IP-based allow/deny | Matchers, path, headers |
| **Content filtering** | URL regex, ICAP, eCAP | URL regex filter | Path matching, respond |
| **Config complexity** | High (50+ directives) | Low (~15 directives) | Very low (declarative) |
| **Memory usage** | 50–200 MB typical | 2–5 MB | 20–60 MB |
| **Load balancing** | No | No | Yes (round-robin, least-conn) |
| **Compression** | No | No | gzip + zstd |
| **HTTP/3 support** | No | No | Yes (QUIC) |
| **Docker image size** | ~150 MB | ~10 MB | ~45 MB |
| **Best for** | Enterprise forward proxying | Home lab, Raspberry Pi | Modern reverse proxying |

## Choosing the Right Proxy

The choice depends on what you're trying to accomplish:

**Use Squid** when you need a forward proxy with aggressive caching, per-user access control, or ICAP integration. It's the right tool for organizations that want to reduce outbound bandwidth, enforce content policies, or provide authenticated proxy access to employees. The configuration overhead is real, but the payoff in caching efficiency and policy granularity is unmatched.

**Use Tinyproxy** when you need a simple forward proxy on a low-resource device. A Raspberry Pi running Tinyproxy costs less than $2/month in electricity and handles a family's worth of browsing without breaking a sweat. It won't save bandwidth through caching, but it will provide a centralized exit point for outbound traffic, making it easy to apply firewall rules, logging, and domain filtering in one place.

**Use Caddy** when you need to expose self-hosted services to the internet. Automatic HTTPS alone is worth it — manual certificate management is a recurring source of outages that Caddy eliminates entirely. Combined with its readable config syntax, built-in compression, and HTTP/3 support, Caddy is the most modern and developer-friendly option for reverse proxying.

## Production Checklist

Regardless of which proxy you choose, follow these best practices before exposing your setup to production:

1. **Restrict access** — Only allow trusted IP ranges or require authentication. An open proxy is a liability.
2. **Enable logging** — Store access logs on a separate volume and rotate them with `logrotate` to prevent disk exhaustion.
3. **Monitor cache hit rates** — For Squid, aim for 40%+ cache hit ratio on repetitive traffic. Below 20%, your cache size or TTL settings need adjustment.
4. **Keep images updated** — Proxy software occasionally has security vulnerabilities. Set up automated rebuilds or use tools like Watchtower to pull fresh images.
5. **Test TLS configuration** — For Caddy, run your domain through SSL Labs after deployment. You should score an A or A+.
6. **Back up configuration** — Version-control your `squid.conf`, `tinyproxy.conf`, or `Caddyfile` in a private Git repository. Changes to proxy rules should be tracked and auditable.
7. **Set resource limits** — Use Docker's `deploy.resources` or systemd cgroups to prevent a misconfigured proxy from consuming all available memory or CPU.

## Conclusion

Squid, Tinyproxy, and Caddy represent three distinct approaches to web proxying. Squid is the heavyweight champion of forward proxying and caching. Tinyproxy is the minimalist's choice for simple, resource-efficient forwarding. Caddy is the modern reverse proxy that handles TLS automatically and exposes services with minimal configuration.

None of them requires a subscription, none of them phones home, and all three run perfectly in Docker containers. Pick the one that matches your use case, deploy it with the examples above, and take back control of your network traffic.

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
