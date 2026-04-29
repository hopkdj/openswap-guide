---
title: "OpenResty vs Nginx vs Caddy: Best Self-Hosted Web Server for Dynamic Apps 2026"
date: 2026-04-29
tags: ["comparison", "guide", "self-hosted", "web-server"]
draft: false
description: "Compare OpenResty, Nginx, and Caddy as self-hosted web servers for dynamic applications. OpenResty adds LuaJIT scripting to Nginx for powerful API and dynamic content serving. Includes Docker Compose configs and deployment guides."
---

When you need a web server that does more than serve static files — when you need dynamic routing, API handling, authentication logic, or real-time content generation — the choice of web server becomes critical. Three options dominate this space in 2026: **OpenResty**, **Nginx**, and **Caddy**. Each takes a fundamentally different approach to serving dynamic content, and picking the right one can save you from writing an entire backend service.

| Feature | OpenResty | Nginx | Caddy |
|---------|-----------|-------|-------|
| **Core Language** | C + LuaJIT | C | Go |
| **Dynamic Scripting** | Lua (built-in) | None (modules only) | Caddy modules (Go) |
| **GitHub Stars** | 13,768 | 30,116 | 71,906 |
| **License** | BSD-2-Clause | BSD-2-Clause | Apache 2.0 |
| **Automatic HTTPS** | Manual (certbot) | Manual (certbot) | Built-in (ACME) |
| **Configuration** | Nginx + Lua | Nginx config | Caddyfile (declarative) |
| **Docker Image** | `openresty/openresty` | `nginx` | `caddy` |
| **Hot Reload** | Yes (lua-resty) | Graceful reload | Live reload (caddy reload) |
| **WebSocket** | Full support | Full support | Full support |
| **gRPC Support** | Via lua-resty-grpc | Native (1.13.10+) | Native |
| **Best For** | Custom APIs, edge logic | Static + proxy, scale | Simplicity, auto-TLS |

## Why Choose a Dynamic Web Server Over a Full Backend Framework?

Running a full backend framework like Django, Rails, or Express for simple routing, authentication, or API aggregation is overkill. A dynamic web server sits at the edge of your infrastructure and can:

- **Handle authentication** before requests hit your application
- **Route and transform** API responses from multiple backends
- **Serve cached dynamic content** without hitting a database
- **Rate limit and throttle** abusive requests at the edge
- **Rewrite URLs and proxy** to different backends based on headers or cookies

By pushing logic to the web server layer, you reduce latency, simplify your application code, and centralize cross-cutting concerns. The question is which server gives you the right balance of power and simplicity.

## OpenResty: Nginx Supercharged with Lua

[OpenResty](https://openresty.org/) bundles Nginx with LuaJIT — a just-in-time compiler for Lua that runs at near-C speed. The result is a web server where you can write custom request-handling logic directly in the configuration layer, without needing a separate application backend.

### Key Strengths

- **lua-nginx-module**: Execute Lua code at every phase of the HTTP request lifecycle (rewrite, access, content, log)
- **OpenResty Package Manager (opm)**: Install community Lua modules for Redis, MySQL, PostgreSQL, memcached, and more
- **ngx.timer**: Run background tasks (cron-like jobs, health checks) without blocking requests
- **Shared dictionaries**: In-memory key-value stores shared across worker processes
- **Cosocket API**: Non-blocking I/O for database queries, HTTP requests, and Redis operations — all from Lua

### Real GitHub Stats (as of April 2026)

- **Stars**: 13,768
- **Last Updated**: April 19, 2026
- **Description**: "High Performance Web Platform Based on Nginx and LuaJIT"

### Docker Compose Deployment

OpenResty's official Docker image (`openresty/openresty`) is one of the most pulled web server images on Docker Hub with over 73 million pulls. Here is a production-ready setup:

```yaml
version: "3.8"

services:
  openresty:
    image: openresty/openresty:alpine-fat
    container_name: openresty
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/usr/local/openresty/nginx/conf/nginx.conf:ro
      - ./lua/:/etc/openresty/lua/:ro
      - ./certs/:/etc/openresty/certs/:ro
      - openresty_logs:/var/log/openresty
    networks:
      - app-network
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    container_name: openresty-redis
    restart: unless-stopped
    volumes:
      - redis_data:/data
    networks:
      - app-network

volumes:
  openresty_logs:
  redis_data:

networks:
  app-network:
    driver: bridge
```

### Sample Lua Configuration: API Rate Limiting + Auth

This example shows how OpenResty handles rate limiting and token authentication directly in the web server layer — no backend needed:

```nginx
http {
    lua_shared_dict rate_limit 10m;
    lua_shared_dict api_keys 1m;

    init_by_lua_block {
        -- Load API keys from Redis at startup
        local redis = require "resty.redis"
        local red = redis:new()
        red:set_timeout(1000)
        local ok, err = red:connect("redis", 6379)
        if ok then
            local keys = red:smembers("valid_api_keys")
            local api_keys = ngx.shared.api_keys
            for _, key in ipairs(keys) do
                api_keys:set(key, true)
            end
            red:close()
        end
    }

    server {
        listen 80;
        server_name api.example.com;

        location /api/ {
            access_by_lua_block {
                -- Check API key
                local api_keys = ngx.shared.api_keys
                local key = ngx.req.get_headers()["X-API-Key"]
                if not key or not api_keys:get(key) then
                    return ngx.exit(ngx.HTTP_UNAUTHORIZED)
                end

                -- Rate limit: 100 requests per minute per key
                local limit = ngx.shared.rate_limit
                local count, err = limit:incr(key, 1)
                if not count then
                    limit:set(key, 1, 60)
                    count = 1
                end
                if count > 100 then
                    return ngx.exit(ngx.HTTP_TOO_MANY_REQUESTS)
                end
            }

            proxy_pass http://backend-service;
        }
    }
}
```

This single configuration handles authentication, rate limiting, and proxying — tasks that would normally require a separate middleware layer in your application.

## Nginx: The Battle-Tested Standard

[Nginx](https://nginx.org/) is the world's most widely deployed web server, powering over 30% of all websites. While OpenResty extends Nginx with scripting, stock Nginx focuses on doing a few things exceptionally well: serving static content, reverse proxying, and load balancing.

### Key Strengths

- **Mature module ecosystem**: Hundreds of third-party modules for caching, security, and protocol support
- **Nginx Plus**: Commercial version with active health checks, dynamic reconfiguration, and enhanced monitoring
- **Performance**: Handles 10,000+ concurrent connections with minimal memory footprint
- **Stability**: Decades of production use in high-traffic environments

### Real GitHub Stats (as of April 2026)

- **Stars**: 30,116
- **Last Updated**: April 24, 2026
- **Description**: "Official repository for NGINX"

### Docker Compose Deployment

Nginx's official Docker image (`nginx:alpine`) is lightweight and battle-tested:

```yaml
version: "3.8"

services:
  nginx:
    image: nginx:alpine
    container_name: nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./conf.d/:/etc/nginx/conf.d/:ro
      - ./html/:/usr/share/nginx/html/:ro
      - ./certs/:/etc/nginx/certs/:ro
      - nginx_logs:/var/log/nginx
    networks:
      - app-network

volumes:
  nginx_logs:

networks:
  app-network:
    driver: bridge
```

### Nginx Configuration: Load Balancing with Health Checks

```nginx
upstream backend_pool {
    least_conn;
    server 10.0.0.1:8080 weight=3;
    server 10.0.0.2:8080 weight=2;
    server 10.0.0.3:8080 backup;
    server 10.0.0.4:8080 down;
}

server {
    listen 80;
    server_name app.example.com;

    # Gzip compression
    gzip on;
    gzip_types text/plain application/json application/javascript text/css;
    gzip_min_length 1000;

    location / {
        proxy_pass http://backend_pool;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 5s;
        proxy_read_timeout 30s;
        proxy_send_timeout 10s;
    }

    # Static file caching
    location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
        root /usr/share/nginx/html;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

## Caddy: The Zero-Configuration Modern Server

[Caddy](https://caddyserver.com/) is written in Go and takes a radically different approach. Its defining feature is **automatic HTTPS** — it obtains and renews TLS certificates from Let's Encrypt without any manual configuration. The Caddyfile format is also significantly simpler than Nginx's configuration syntax.

### Key Strengths

- **Automatic HTTPS**: Zero-config TLS with ACME protocol support (Let's Encrypt, ZeroSSL)
- **Caddyfile**: Human-readable configuration that is easier to learn than Nginx syntax
- **Go modules**: Extend functionality with a growing ecosystem of Caddy plugins
- **HTTP/3 support**: First-class QUIC/HTTP/3 support out of the box
- **JSON API**: Programmatically configure and reload via REST API

### Real GitHub Stats (as of April 2026)

- **Stars**: 71,906
- **Last Updated**: April 28, 2026
- **Description**: "Fast and extensible multi-platform HTTP/1-2-3 web server with automatic HTTPS"

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  caddy:
    image: caddy:alpine
    container_name: caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - ./site/:/srv/:ro
      - caddy_data:/data
      - caddy_config:/config
    networks:
      - app-network

volumes:
  caddy_data:
  caddy_config:

networks:
  app-network:
    driver: bridge
```

### Caddyfile: Simple Reverse Proxy with Automatic HTTPS

```
example.com {
    # Automatic HTTPS is enabled by default
    encode gzip zstd

    # Reverse proxy to backend
    reverse_proxy /api/* http://backend:8080 {
        header_up X-Real-IP {remote_host}
    }

    # Serve static files
    handle /static/* {
        file_server browse
        header Cache-Control "public, max-age=86400"
    }

    # Catch-all: serve from /srv
    handle {
        root * /srv
        file_server
    }
}
```

That entire configuration — including TLS, gzip compression, reverse proxying, and static file serving — fits in 20 lines. With Nginx, the same setup requires separate blocks for each feature and manual certbot configuration.

## Head-to-Head Comparison

### Performance

| Metric | OpenResty | Nginx | Caddy |
|--------|-----------|-------|-------|
| Static file throughput | ~200K req/s | ~200K req/s | ~120K req/s |
| Memory per worker | ~5 MB | ~5 MB | ~15 MB |
| Dynamic content (Lua) | ~50K req/s | N/A | ~80K req/s (Go) |
| HTTP/3 support | Via module | Via module | Native |

OpenResty and Nginx share the same event-driven C core, so raw static file performance is essentially identical. Caddy trades some throughput for developer ergonomics and built-in features. For dynamic content, OpenResty's LuaJIT delivers near-C performance, while Caddy's Go runtime is fast but carries higher memory overhead.

### Developer Experience

OpenResty requires learning both Nginx configuration and Lua — two syntaxes that interact in non-obvious ways. The `lua-nginx-module` documentation is extensive but scattered across wiki pages and GitHub repos. Nginx configuration is well-documented but verbose for complex setups. Caddy's Caddyfile is the easiest to learn, and its automatic HTTPS removes the most common setup pain point.

### Ecosystem and Community

Nginx has the largest ecosystem by far — every web hosting control panel, CDN, and cloud provider supports it. OpenResty's ecosystem is smaller but highly focused on edge computing and API gateway use cases. Caddy's ecosystem is growing rapidly, particularly in the self-hosting and homelab communities.

### Security

All three servers receive regular security patches. OpenResty's Lua scripting introduces a larger attack surface — poorly written Lua code can expose sensitive data or cause denial of service. Nginx and Caddy have smaller surface areas when used without third-party modules. Caddy's default HTTPS posture means sites are encrypted out of the box, reducing the risk of misconfigured TLS.

## When to Use Each

### Choose OpenResty When:
- You need custom request-handling logic at the edge (authentication, rate limiting, A/B testing)
- You want to build an API gateway without deploying a separate service
- You need to integrate with Redis, PostgreSQL, or MySQL directly from the web server
- Your team has Lua experience or is willing to learn it

### Choose Nginx When:
- You need the most battle-tested, widely supported web server available
- Your use case is primarily static content serving and reverse proxying
- You want maximum performance with minimal resource usage
- You need compatibility with existing Nginx tooling and monitoring dashboards

### Choose Caddy When:
- You want automatic HTTPS without managing certbot or ACME clients
- You prefer simple, readable configuration over maximum flexibility
- You need HTTP/3 support without compiling custom modules
- You are running a small-to-medium self-hosted environment and value developer experience

For related reading on securing and extending your web server setup, see our [BunkerWeb vs ModSecurity vs CrowdSec WAF guide](../2026-04-18-bunkerweb-vs-modsecurity-vs-crowdsec-self-hosted-waf-guide-2026/) for web application firewall options, the [Nginx vs Caddy vs Envoy rate limiting guide](../2026-04-28-nginx-vs-caddy-vs-envoy-ratelimit-self-hosted-rate-limiting-guide-2026/) for API throttling strategies, and our [reverse proxy comparison](../reverse-proxy-comparison/) for broader infrastructure context.

## FAQ

### Is OpenResty just Nginx with Lua?

OpenResty is more than Nginx plus a Lua module. It bundles Nginx with LuaJIT, the `lua-nginx-module`, `ngx_lua` for asynchronous I/O, and a package manager (opm) with hundreds of community modules for databases, caching, and protocol support. The integration is deep enough that Lua code runs at every phase of the HTTP request lifecycle, enabling patterns like in-memory caching, request aggregation, and authentication that would require a separate backend service with stock Nginx.

### Can Caddy do everything Nginx does?

Not quite. Caddy excels at static file serving, reverse proxying, and automatic TLS. However, it lacks Nginx's extensive third-party module ecosystem, fine-grained load balancing algorithms, and the ability to execute custom logic at the request level (like OpenResty's Lua scripting). For standard web serving and proxying, Caddy is a great choice. For complex edge computing or API gateway use cases, Nginx or OpenResty remain the better options.

### Does OpenResty support HTTP/2 and HTTP/3?

OpenResty supports HTTP/2 out of the box (inherited from Nginx). HTTP/3 (QUIC) support is available through the `ngx_http_v3_module` in newer Nginx versions, but integration with OpenResty's Lua modules requires careful configuration. Caddy has the most seamless HTTP/3 support — it is enabled by default and requires no additional modules.

### How do I migrate from Nginx to OpenResty?

OpenResty is a drop-in replacement for Nginx. The configuration syntax is identical, so your existing `nginx.conf` files work without modification. To migrate:

1. Install OpenResty (or switch your Docker image to `openresty/openresty`)
2. Copy your existing Nginx configuration files
3. Test with `openresty -t` to verify syntax
4. Reload with `openresty -s reload`
5. Gradually add Lua directives to specific locations as needed

No changes are required until you want to use Lua features.

### Is Caddy production-ready for high-traffic sites?

Caddy handles millions of requests in production at companies like Cloudflare and Fastly. Its Go runtime means it uses more memory than Nginx per connection, but it scales well horizontally. For sites with tens of thousands of concurrent connections, Nginx or OpenResty may be more resource-efficient. For the vast majority of self-hosted and small-to-medium production workloads, Caddy is more than capable.

### What is the learning curve for each server?

Caddy has the shallowest learning curve — the Caddyfile is intuitive, and automatic HTTPS removes the most complex setup step. Nginx requires understanding its directive hierarchy and event-driven model, which takes a few days to master. OpenResty adds Lua scripting on top of Nginx, requiring knowledge of both systems and the `lua-nginx-module` API. Expect a week or more to become productive with OpenResty if you are new to Lua.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "OpenResty vs Nginx vs Caddy: Best Self-Hosted Web Server for Dynamic Apps 2026",
  "description": "Compare OpenResty, Nginx, and Caddy as self-hosted web servers for dynamic applications. OpenResty adds LuaJIT scripting to Nginx for powerful API and dynamic content serving. Includes Docker Compose configs and deployment guides.",
  "datePublished": "2026-04-29",
  "dateModified": "2026-04-29",
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
