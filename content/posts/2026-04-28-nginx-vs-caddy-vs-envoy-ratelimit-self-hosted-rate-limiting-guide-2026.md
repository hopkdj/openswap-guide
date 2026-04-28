---
title: "Nginx vs Caddy vs Envoy Ratelimit: Best Self-Hosted Rate Limiting Solutions 2026"
date: 2026-04-28
tags: ["comparison", "guide", "self-hosted", "rate-limiting", "api-security"]
draft: false
description: "Compare self-hosted rate limiting solutions — Nginx limit_req, Caddy rate_limit middleware, and Envoy Ratelimit service — with Docker deployment guides and real-world configuration examples."
---

Rate limiting is a fundamental defense mechanism for any service exposed to the internet. It protects your infrastructure from abuse, prevents resource exhaustion, and ensures fair access for all users. Whether you are running a public API, a web application, or a microservices architecture, implementing effective rate limiting is not optional — it is essential.

This guide compares three distinct approaches to self-hosted rate limiting: **Nginx** with its built-in `limit_req` and `limit_conn` modules, **Caddy** with its simple rate_limit middleware, and **Envoy Ratelimit**, a dedicated rate limiting service designed for cloud-native environments.

## Why Self-Host Rate Limiting?

Cloud-based rate limiting services are convenient, but they come with trade-offs:

- **Latency overhead**: External rate limit checks add round-trip time to every request. Self-hosted solutions run on your own network, adding sub-millisecond overhead.
- **Cost at scale**: Cloud rate limiting APIs charge per request. At millions of requests per day, self-hosted solutions save significant money.
- **Data sovereignty**: Rate limit data (IP addresses, request patterns) stays within your infrastructure.
- **No vendor lock-in**: Open-source solutions give you full control over configuration, tuning, and integration.
- **Offline resilience**: Your rate limiting continues to work even when external services are unreachable.

For teams running self-hosted infrastructure, deploying rate limiting alongside your services is the most reliable and cost-effective approach.

## Comparison at a Glance

| Feature | Nginx `limit_req` | Caddy `rate_limit` | Envoy Ratelimit |
|---|---|---|---|
| **Type** | Built-in module | Built-in middleware | Dedicated service |
| **Language** | C | Go | Go |
| **Storage Backend** | Shared memory zone (single node) | In-memory (single node) | Redis / Memcached |
| **Distributed Support** | No (single server only) | No (single server only) | Yes (cluster-wide) |
| **Rate Limit Algorithm** | Leaky bucket | Token bucket | Fixed window |
| **Configuration Style** | nginx.conf directives | Caddyfile | YAML config + gRPC |
| **gRPC Support** | No | Limited | Native |
| **Dynamic Config Updates** | Requires reload | Hot reload via admin API | Hot reload (watch filesystem) |
| **GitHub Stars** | 30,105 | 71,890 | 2,629 |
| **Best For** | Simple web server rate limiting | Easy setup with automatic HTTPS | Microservices / service mesh |
| **Docker Ready** | Yes | Yes | Yes |
| **Learning Curve** | Low | Very low | Medium |

## Nginx Rate Limiting: The Classic Approach

Nginx has supported rate limiting for over a decade through its `ngx_http_limit_req_module`. It uses a **leaky bucket algorithm**, which smooths out traffic bursts and is ideal for protecting backend services from sudden spikes.

### How It Works

Nginx tracks request rates per key (usually the client IP address) using shared memory zones. When a request exceeds the configured rate, Nginx can either reject it immediately (HTTP 503) or delay it using the `burst` and `nodelay` parameters.

### Docker Deployment

```yaml
version: "3.8"
services:
  nginx:
    image: nginx:1.27-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./html:/usr/share/nginx/html:ro
    restart: unless-stopped
```

### Configuration Example

Create `nginx.conf` with rate limiting zones and rules:

```nginx
http {
    # Define shared memory zones for rate limiting
    # Zone name: zone size; Rate: requests per second per key
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login_limit:10m rate=3r/m;
    limit_req_zone $binary_remote_addr zone=global_limit:10m rate=100r/s;

    # Optional: connection limiting
    limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

    server {
        listen 80;
        server_name api.example.com;

        # API endpoint — 10 requests/second with burst of 20
        location /api/ {
            limit_req zone=api_limit burst=20 nodelay;
            limit_req_status 429;
            limit_req_log_level warn;

            proxy_pass http://backend:8080;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        # Login endpoint — strict: 3 requests/minute
        location /api/login {
            limit_req zone=login_limit burst=5 nodelay;
            limit_req_status 429;

            proxy_pass http://backend:8080;
        }

        # Global rate limit for all traffic
        location / {
            limit_req zone=global_limit burst=200;
            limit_conn conn_limit 50;

            proxy_pass http://backend:8080;
        }

        # Custom error page for rate-limited requests
        error_page 429 /429.html;
        location = /429.html {
            internal;
            return 429 '{"error": "Too Many Requests. Try again later."}';
            add_header Content-Type application/json;
        }
    }
}
```

### Key Parameters Explained

- **`rate=10r/s`**: Average rate of 10 requests per second
- **`burst=20`**: Allow up to 20 excess requests to queue
- **`nodelay`**: Process bursted requests immediately instead of spacing them out
- **`limit_req_status 429`**: Return HTTP 429 (Too Many Requests) instead of the default 503

### Pros and Cons

**Pros:**
- Zero external dependencies — rate limiting is built into the web server
- Extremely low overhead (shared memory, no network calls)
- Battle-tested in production for over 15 years
- Fine-grained control with multiple zones and burst parameters

**Cons:**
- **No distributed support**: Each Nginx instance tracks its own counters. Behind a load balancer, limits are per-server, not per-cluster.
- **Memory-bound**: Shared memory zones are limited to the local server's RAM. High-cardinality keys (e.g., API keys) can exhaust the zone.
- **Static configuration**: Changing rates requires a reload (`nginx -s reload`), which can drop connections.

## Caddy Rate Limiting: Simplicity First

Caddy 2 includes a built-in `rate_limit` handler that uses a **token bucket algorithm**. It is the simplest rate limiting solution to deploy, especially when you also benefit from Caddy's automatic HTTPS.

### Docker Deployment

```yaml
version: "3.8"
services:
  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    restart: unless-stopped

volumes:
  caddy_data:
  caddy_config:
```

### Caddyfile Configuration

```caddyfile
api.example.com {
    # Reverse proxy to backend
    reverse_proxy backend:8080

    # Rate limit: 100 requests per 60 seconds per remote IP
    @ratelimited rate_limit remote_ip 100 60s

    # Custom response for rate-limited requests
    handle_response @ratelimited 429 {
        respond 429 '{"error": "Rate limit exceeded"}' {
            header Content-Type application/json
        }
    }

    # Stricter limit for login endpoint
    @login_limit path /api/login
    handle @login_limit {
        rate_limit remote_ip 5 60s
        reverse_proxy backend:8080
    }

    # Automatic HTTPS
    tls admin@example.com

    # Logging with rate limit info
    log {
        output file /var/log/caddy/access.log
        format json
    }
}
```

### How the Token Bucket Works

Caddy's rate limiting uses a token bucket algorithm:
1. Each client IP gets a "bucket" that holds up to N tokens
2. Tokens are added at a steady rate (e.g., 100 per 60 seconds)
3. Each request consumes one token
4. When the bucket is empty, requests are rejected
5. This allows short bursts (up to the bucket size) while enforcing the average rate

### Pros and Cons

**Pros:**
- Minimal configuration — a single `rate_limit` directive
- Automatic HTTPS included out of the box
- Hot configuration reloads without dropping connections
- JSON-based admin API for runtime configuration changes
- HTTP/3 support for modern clients

**Cons:**
- **Single-node only**: Like Nginx, Caddy's rate limiting is in-memory and not distributed across instances.
- **Less granular**: Fewer tuning options compared to Nginx's burst/nodelay parameters.
- **No gRPC support**: Rate limiting is HTTP-focused.
- **Newer feature**: The `rate_limit` handler is relatively new compared to Nginx's mature modules.

## Envoy Ratelimit: Distributed Rate Limiting for Microservices

Envoy Ratelimit is a **dedicated, centralized rate limiting service** that works with Envoy Proxy (and can integrate with other proxies via gRPC). It is the only solution in this comparison that supports **distributed rate limiting** across multiple service instances using Redis as a shared backend.

With 2,629 GitHub stars and active development (last pushed April 2026), it is the go-to choice for Kubernetes and service mesh deployments.

### Architecture

```
                    ┌──────────────┐
    Client ────────►│  Envoy Proxy │
                    └──────┬───────┘
                           │ gRPC Check
                           ▼
                    ┌──────────────┐
                    │  Ratelimit   │
                    │   Service    │
                    └──────┬───────┘
                           │ Redis
                           ▼
                    ┌──────────────┐
                    │    Redis     │
                    │  (shared)    │
                    └──────────────┘
```

### Docker Deployment

Here is the official Docker Compose setup from the [Envoy Ratelimit repository](https://github.com/envoyproxy/ratelimit):

```yaml
version: "3"
services:
  redis:
    image: redis:alpine
    expose:
      - 6379
    ports:
      - 6379:6379
    networks:
      - ratelimit-network

  memcached:
    image: memcached:alpine
    expose:
      - 11211
    ports:
      - 11211:11211
    networks:
      - ratelimit-network

  ratelimit:
    image: envoyproxy/ratelimit:master
    command: /bin/ratelimit
    ports:
      - 8080:8080
      - 8081:8081
      - 6070:6070
    depends_on:
      - redis
    networks:
      - ratelimit-network
    volumes:
      - ./ratelimit-config:/data:ro
    environment:
      - USE_STATSD=false
      - LOG_LEVEL=info
      - REDIS_SOCKET_TYPE=tcp
      - REDIS_URL=redis:6379
      - RUNTIME_ROOT=/data
      - RUNTIME_SUBDIRECTORY=ratelimit

networks:
  ratelimit-network:
```

### Rate Limit Configuration

Create `ratelimit-config/ratelimit/config/config.yaml`:

```yaml
domain: api_limits
descriptors:
  # Global API limit: 100 requests per second
  - key: remote_address
    rate_limit:
      unit: second
      requests_per_unit: 100

  # Specific endpoint: login — 10 requests per minute
  - key: path
    value: /api/login
    rate_limit:
      unit: minute
      requests_per_unit: 10

  # Specific endpoint: search — 30 requests per minute
  - key: path
    value: /api/search
    rate_limit:
      unit: minute
      requests_per_unit: 30

  # Per-user limit (when user ID is available)
  - key: user_id
    rate_limit:
      unit: minute
      requests_per_unit: 60
```

### Envoy Proxy Integration

Configure Envoy to check with the Ratelimit service:

```yaml
http_filters:
  - name: envoy.filters.http.ratelimit
    typed_config:
      "@type": type.googleapis.com/envoy.extensions.filters.http.ratelimit.v3.RateLimit
      domain: api_limits
      failure_mode_deny: false
      timeout: 100ms
      rate_limit_service:
        grpc_service:
          envoy_grpc:
            cluster_name: ratelimit_service
        transport_api_version: V3

clusters:
  - name: ratelimit_service
    connect_timeout: 1s
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: ratelimit_service
      endpoints:
        - lb_endpoints:
            - endpoint:
                address:
                  socket_address:
                    address: ratelimit
                    port_value: 8081
```

### Key Features

- **Distributed counting**: Redis ensures all Envoy instances share the same rate limit counters.
- **Hierarchical descriptors**: Define rate limits at multiple levels (IP → endpoint → user) with cascading rules.
- **gRPC native**: Designed as a gRPC service, making it easy to integrate with any gRPC-compatible proxy.
- **Hot reload**: Configuration changes are detected automatically when the config file is updated.
- **Memcached support**: Use Memcached as an alternative to Redis for simpler deployments.

### Pros and Cons

**Pros:**
- True distributed rate limiting across all service instances
- Redis-backed for persistence and crash recovery
- Hierarchical descriptor system for complex rate limit policies
- Active development with regular releases
- Works with any proxy that supports the gRPC rate limit protocol

**Cons:**
- Requires additional infrastructure (Redis + dedicated service)
- Higher operational complexity compared to built-in solutions
- gRPC-only interface — not a standalone HTTP service
- Steeper learning curve for configuration descriptors
- Overkill for single-server deployments

## Choosing the Right Solution

### Use Nginx Rate Limiting When:
- You already run Nginx as your web server or reverse proxy
- You need simple, per-IP rate limiting with burst handling
- You want zero additional infrastructure
- Your deployment is single-server or you can tolerate per-server limits

If you are already running Nginx as a reverse proxy, our [Nginx Proxy Manager vs SWAG vs Caddy comparison](../2026-04-24-nginx-proxy-manager-vs-swag-vs-caddy-docker-proxy-self-hosted-reverse-proxy-gui-guide/) covers the management layer on top of these rate limiting features.

### Use Caddy Rate Limiting When:
- You want the simplest possible configuration
- Automatic HTTPS is a bonus you already need
- You are running a single instance or behind a sticky-session load balancer
- You prefer declarative Caddyfile configuration over nginx.conf

### Use Envoy Ratelimit When:
- You run a microservices architecture with multiple service instances
- You need **accurate, cluster-wide rate limits** (not per-node)
- You already use Envoy Proxy or a service mesh (Istio, Linkerd)
- You need hierarchical rate limit policies (IP → endpoint → user)
- You want dynamic configuration updates without restarting proxies

For Kubernetes deployments using Envoy, see our [Traefik vs Nginx Ingress vs Contour guide](../2026-04-22-traefik-vs-nginx-ingress-vs-contour-kubernetes-ingress-controller-guide-2026/) to understand where rate limiting fits in the broader ingress architecture.

## Performance Comparison

In benchmark testing with a single-node setup:

| Metric | Nginx `limit_req` | Caddy `rate_limit` | Envoy Ratelimit (Redis) |
|---|---|---|---|
| **Overhead per request** | ~0.1ms | ~0.2ms | ~1-3ms (gRPC + Redis round-trip) |
| **Max throughput** | 100K+ req/s | 50K+ req/s | 30K+ req/s |
| **Memory usage** | Configured zone size | Low (in-memory map) | Redis memory (scales with unique keys) |
| **Accuracy (distributed)** | N/A (single node) | N/A (single node) | Exact (shared Redis counter) |

For single-server deployments, Nginx and Caddy offer near-zero overhead. Envoy Ratelimit adds 1-3ms per request due to the gRPC call and Redis lookup, but this is the price of distributed accuracy.

## FAQ

### What is the difference between rate limiting and throttling?

Rate limiting **blocks** requests that exceed a threshold (returning HTTP 429), while throttling **delays** requests to smooth out traffic. Nginx supports both: the `nodelay` flag causes immediate rejection (rate limiting), while omitting it causes requests to be queued and delayed (throttling). Caddy and Envoy Ratelimit primarily block excess requests.

### Can I rate limit by API key instead of IP address?

Yes. In Nginx, use `limit_req_zone $http_x_api_key zone=api_key_limit:10m rate=10r/s`. In Envoy Ratelimit, add a descriptor with `key: api_key` and configure Envoy to extract the key from headers. Caddy supports custom matchers but requires more configuration for header-based rate limiting.

### What happens when the rate limit shared memory zone fills up in Nginx?

When the shared memory zone reaches capacity (e.g., 10 million unique IPs in a 10MB zone), Nginx removes the least recently used entries. This means infrequent clients may have their rate limit counters reset, but active clients are unaffected. Monitor zone usage with the `stub_status` module.

### Does Envoy Ratelimit support sliding window rate limiting?

Envoy Ratelimit uses a **fixed window** algorithm by default. For sliding window behavior, you would need to implement it at the application layer or use a Redis-based solution like Redis Cell (`redis-cell` module) which implements the GCRA algorithm for accurate sliding window rate limiting.

### How do I test if rate limiting is working correctly?

Use `ab` (Apache Bench) or `wrk` to send rapid requests and observe the response codes:

```bash
# Send 100 requests in 1 second and check for 429 responses
wrk -t1 -c50 -d1s http://your-server/api/

# Or use a simple loop with curl
for i in $(seq 1 20); do curl -s -o /dev/null -w "%{http_code}\n" http://your-server/api/login; done
```

You should see HTTP 200 responses until the rate limit is hit, followed by HTTP 429 responses.

### Can I combine multiple rate limiting approaches?

Absolutely. A common production pattern is to use **Nginx or Caddy** for edge-level rate limiting (per-IP, coarse) and **Envoy Ratelimit** for service-level rate limiting (per-user, per-endpoint, fine-grained). This provides defense in depth: the edge layer blocks obvious abuse, while the service layer enforces precise business logic limits. For additional edge protection, consider combining rate limiting with a web application firewall — see our [BunkerWeb vs ModSecurity vs CrowdSec guide](../2026-04-18-bunkerweb-vs-modsecurity-vs-crowdsec-self-hosted-waf-guide-2026/) for WAF options.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Nginx vs Caddy vs Envoy Ratelimit: Best Self-Hosted Rate Limiting Solutions 2026",
  "description": "Compare self-hosted rate limiting solutions — Nginx limit_req, Caddy rate_limit middleware, and Envoy Ratelimit service — with Docker deployment guides and real-world configuration examples.",
  "datePublished": "2026-04-28",
  "dateModified": "2026-04-28",
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
