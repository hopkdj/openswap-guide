---
title: "Self-Hosted Rate Limiting & API Throttling: NGINX vs Traefik vs Envoy vs Kong 2026"
date: 2026-04-16
tags: ["comparison", "guide", "self-hosted", "api", "rate-limiting", "security"]
draft: false
description: "Complete guide to self-hosted rate limiting and API throttling in 2026. Compare NGINX, Traefik, Envoy, and Kong with Docker configurations, performance benchmarks, and deployment strategies."
---

Rate limiting is the unsung hero of infrastructure reliability. Without it, a single misbehaving client can exhaust your server resources, trigger cascading failures, and bring down your entire stack. Yet most rate limiting guides point you toward expensive cloud APIs or managed services that charge per-request and lock you into a vendor.

In 2026, self-hosted rate limiting is not just possible — it is straightforward, performant, and completely free of per-request fees. Whether you are protecting a login endpoint from credential stuffing, throttling a public API to stay within fair usage limits, or implementing defense-in-depth against DDoS attacks, you can run production-grade rate limiting on your own hardware.

## Why Self-Host Rate Limiting?

**Cost savings.** Managed rate limiting services like Cloudflare Rate Limiting, AWS WAF Rate-Based Rules, or Fastly Rate Limiting charge by the request. If you process millions of requests per day, those costs add up quickly. A self-hosted reverse proxy with rate limiting runs on a $5 VPS and handles unlimited requests.

**Data privacy.** Rate limiting decisions require tracking client identifiers — IP addresses, API keys, session tokens. When you use a third-party service, that telemetry leaves your network. Self-hosting keeps every request count, every blocked IP, and every throttle decision within your infrastructure.

**No vendor lock-in.** Cloud rate limiting rules are written in proprietary DSLs. Migrate away and you rebuild from scratch. Self-hosted solutions like NGINX, Traefik, and Envoy use standard configuration formats that move with you.

**Custom logic.** Need per-endpoint rate limits? Tiered limits based on user plans? Geographic-aware throttling? Time-of-day rules? Self-hosted solutions give you full control over every aspect of the rate limiting policy.

## Rate Limiting vs Throttling: What is the Difference?

**Rate limiting** enforces a hard ceiling. Once a client exceeds the limit, requests are rejected immediately with an HTTP 429 (Too Many Requests). It is binary: you are either within limits or you are blocked.

**API throttling** is more nuanced. Instead of rejecting requests, throttling delays them. A client making 100 requests per second on a 50 rps limit might see every second request delayed by 100ms rather than rejected. Throttling is friendlier for user-facing APIs but requires more infrastructure to manage request queues.

Most production systems use both: hard rate limits for abuse prevention and throttling for graceful degradation under load.

## Core Rate Limiting Algorithms

Understanding the algorithm behind your rate limiter is critical for choosing the right tool.

**Token Bucket.** The most common algorithm. A bucket fills with tokens at a fixed rate. Each request consumes one token. When the bucket is empty, requests are rejected. Supports burst traffic — a client that was idle can make a burst of requests up to the bucket size. NGINX and Traefik use this model.

**Sliding Window Log.** Tracks the timestamp of every request in a rolling window. Accurate but memory-intensive. Best for strict compliance requirements where you need exact request counts. Envoy supports this through its rate limit service.

**Fixed Window Counter.** Divides time into fixed intervals (e.g., 1 minute) and counts requests per interval. Simple but allows bursts at window boundaries — a client could send 2x the limit at the boundary. Used by basic Kong configurations.

**Leaky Bucket.** Requests enter a queue that drains at a constant rate. If the queue overflows, requests are dropped. Equivalent to throttling — smooths traffic to a constant rate. Kong's plugin supports this mode.

## NGINX Rate Limiting

NGINX has been the workhorse of web infrastructure for over two decades. Its `limit_req` module provides fast, memory-efficient rate limiting using the token bucket algorithm with shared memory zones.

### How It Works

NGINX allocates a shared memory zone that tracks client identifiers (usually IP addresses) across worker processes. Each request is checked against the zone, and the token bucket determines whether to accept, delay, or reject the request.

### [docker](https://www.docker.com/) Setup

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
      - ./rate-limit.conf:/etc/nginx/conf.d/rate-limit.conf:ro
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 128M
```

### Basic Rate Limit Configuration

```nginx
# rate-limit.conf

# Define a shared memory zone: 10MB holds ~160,000 IP addresses
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=login_limit:10m rate=3r/m;

# Custom error response for rate-limited requests
limit_req_status 429;
limit_req_log_level warn;

# Login endpoint: strict limit (3 requests per minute)
location /api/auth/login {
    limit_req zone=login_limit burst=1 nodelay;
    proxy_pass http://backend:3000;
}

# General API: moderate limit with burst
location /api/ {
    limit_req zone=api_limit burst=20 nodelay;
    proxy_pass http://backend:3000;
}

# Health check: no rate limiting
location /health {
    proxy_pass http://backend:3000;
}
```

The `burst` parameter allows temporary spikes above the rate limit. With `burst=20 nodelay`, a client can send up to 21 requests instantly (1 from the rate + 20 burst), then must wait for the token bucket to refill.

### Advanced: Per-API-Key Rate Limiting

```nginx
# Use API key from header, fall back to IP
map $http_x_api_key $rate_key {
    default $http_x_api_key;
    ""      $binary_remote_addr;
}

limit_req_zone $rate_key zone=apikey_limit:10m rate=50r/s;
```

This allows authenticated clients with API keys to have their own rate limit bucket, separate from unauthenticated IP-based limiting.

### Connection Limiting

NGINX also supports connection limiting with `limit_conn`, which caps concurrent connections rather than request rate:

```nginx
limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

server {
    limit_conn conn_limit 50;  # Max 50 concurrent connections per IP
}
```

## Traefik Rate Limiting

Traefik is a modern, cloud-native reverse proxy designed for container environments. Its middleware system makes rate limiting declarative and easy to integra[kubernetes](https://kubernetes.io/)cker Compose and Kubernetes.

### How It Works

Traefik uses a middleware pipeline. Each middleware is a reusable component that modifies or filters requests. The `RateLimit` middleware implements token bucket rate limiting per-source-IP by default.

### Docker Setup with Dynamic Configuration

```yaml
version: "3.8"

services:
  traefik:
    image: traefik:v3.2
    command:
      - "--api.dashboard=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./traefik-dynamic.yml:/etc/traefik/dynamic.yml:ro
    restart: unless-stopped

  api:
    image: your-api:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api.rule=Host(`api.example.com`)"
      - "traefik.http.routers.api.entrypoints=websecure"
      - "traefik.http.routers.api.middlewares=api-rate-limit"
    restart: unless-stopped
```

### Dynamic Configuration (traefik-dynamic.yml)

```yaml
http:
  middlewares:
    api-rate-limit:
      rateLimit:
        average: 100
        burst: 50
        period: 1s
        sourceCriterion:
          requestHeaderName: X-API-Key
```

When `sourceCriterion` uses a request header, Traefik rate limits per header value instead of per IP. This is essential for API key-based throttling.

### Kubernetes IngressRoute Example

```yaml
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata:
  name: api-rate-limit
spec:
  rateLimit:
    average: 50
    burst: 25
    period: 1s
---
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: api
spec:
  entryPoints:
    - websecure
  routes:
    - match: Host(`api.example.com`)
      kind: Rule
      middlewares:
        - name: api-rate-limit
      services:
        - name: api-service
          port: 8080
```

### Traefik Limitations

Traefik's rate limiting is **per-process**. In a multi-instance deployment, each Traefik node maintains its own rate limit counters. There is no built-in distributed rate limiting. For most use cases, this is acceptable, but it means the effective limit is `configured_limit × number_of_instances`.

## Envoy Rate Limiting

Envoy is a high-performance service proxy designed for microservice architectures. It offers the most sophisticated rate limiting capabilities of any open-source proxy, including distributed rate limiting via a dedicated gRPC service.

### How It Works

Envoy supports two rate limiting modes:

1. **Local Rate Limiting** — enforced at each Envoy instance using token bucket configuration embedded in the listener or cluster config. No external dependencies.

2. **Distributed Rate Limiting** — Envoy makes a gRPC call to an external Rate Limit Service (RLS) that maintains global counters. This provides cluster-wide rate limiting even across dozens of Envoy instances.

### Docker Compose Setup

```yaml
version: "3.8"

services:
  envoy:
    image: envoyproxy/envoy:v1.32
    ports:
      - "80:8080"
      - "9901:9901"
    volumes:
      - ./envoy.yaml:/etc/envoy/envoy.yaml:ro
    restart: unless-stopped

  rls:
    image: envoyproxy/ratelimit:latest
    ports:
      - "8081:8080"
      - "8082:8081"
    environment:
      - USE_STATSD=false
      - LOG_LEVEL=info
      - REDIS_SOCKET_TYPE=tcp
      - REDIS_URL=redis:6379
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    restart: unless-stopped

volumes:
  redis-data:
```

### Local Rate Limit Configuration

```yaml
# envoy.yaml (excerpt)
static_resources:
  listeners:
    - name: listener_0
      address:
        socket_address:
          address: 0.0.0.0
          port_value: 8080
      filter_chains:
        - filters:
            - name: envoy.filters.network.http_connection_manager
              typed_config:
                "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
                stat_prefix: ingress_http
                http_filters:
                  - name: envoy.filters.http.local_ratelimit
                    typed_config:
                      "@type": type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
                      stat_prefix: http_local_rate_limiter
                      token_bucket:
                        max_tokens: 100
                        tokens_per_fill: 100
                        fill_interval: 1s
                      filter_enabled:
                        runtime_key: local_rate_limit_enabled
                        default_value:
                          numerator: 100
                          denominator: HUNDRED
                      filter_enforced:
                        runtime_key: local_rate_limit_enforced
                        default_value:
                          numerator: 100
                          denominator: HUNDRED
                  - name: envoy.filters.http.router
                    typed_config:
                      "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
```

This configuration limits each Envoy instance to 100 requests per second per route.

### Distributed Rate Limiting via RLS

For global rate limiting across multiple Envoy instances, configure the Rate Limit Service:

```yaml
# rls-config.yaml (loaded via RLSS_CONFIG environment variable)
domain: api
descriptors:
  - key: remote_address
    rate_limit:
      unit: second
      requests_per_unit: 50

  - key: api_key
    rate_limit:
      unit: minute
      requests_per_unit: 1000

  - key: path
    value: /api/auth/login
    rate_limit:
      unit: minute
      requests_per_unit: 10
```

The RLS uses Redis as its backing store, so all Envoy instances share the same counters. This provides true cluster-wide rate limiting.

### Envoy HTTP Filter for Rate Limit

```yaml
# Add to http_filters in Envoy config
- name: envoy.filters.http.ratelimit
  typed_config:
    "@type": type.googleapis.com/envoy.extensions.filters.http.ratelimit.v3.RateLimit
    domain: api
    request_type: all
    rate_limit_service:
      grpc_service:
        envoy_grpc:
          cluster_name: ratelimit_cluster
        timeout: 10ms
      transport_api_version: V3
```

## Kong Rate Limiting

Kong is a full-featured API gateway built on NGINX with Lua plugins. Its rate limiting plugin offers the most configuration options of any tool covered here, including multiple algorithms and response headers.

### How It Works

Kong runs as a gateway service with a PostgreSQL or declarative configuration backend. The `rate-limiting` plugin intercepts requests and enforces policies based on consumer identity, IP address, service, or route.

### Docker Compose Setup

```yaml
version: "3.8"

services:
  kong:
    image: kong:3.9
    environment:
      KONG_DATABASE: off
      KONG_PROXY_ACCESS_LOG: /dev/stdout
      KONG_ADMIN_ACCESS_LOG: /dev/stdout
      KONG_PROXY_ERROR_LOG: /dev/stderr
      KONG_ADMIN_ERROR_LOG: /dev/stderr
      KONG_ADMIN_LISTEN: 0.0.0.0:8001
      KONG_DECLARATIVE_CONFIG: /kong/declarative/kong.yaml
    ports:
      - "8000:8000"
      - "8001:8001"
    volumes:
      - ./kong.yaml:/kong/declarative/kong.yaml:ro
    restart: unless-stopped
```

### Declarative Configuration (kong.yaml)

```yaml
_format_version: "3.0"

services:
  - name: api-service
    url: http://backend:3000
    routes:
      - name: api-route
        paths:
          - /api
        plugins:
          - name: rate-limiting
            config:
              second: 50
              minute: 2000
              hour: 50000
              policy: redis
              redis:
                host: redis
                port: 6379
              limit_by: consumer
              error_code: 429
              error_message: "Rate limit exceeded. Try again later."
              header_name: X-RateLimit-Remaining
              hide_client_headers: false
              sync_rate: 10

  - name: auth-service
    url: http://auth:3001
    routes:
      - name: login-route
        paths:
          - /api/auth/login
        plugins:
          - name: rate-limiting
            config:
              minute: 5
              policy: local
              limit_by: ip
              error_code: 429

plugins:
  - name: rate-limiting-advanced
    config:
      limit:
        - 100
        - 5000
        - 100000
      window_size:
        - 1
        - 60
        - 3600
      window_type: sliding
      strategy: redis
      redis:
        host: redis
        port: 6379
      identifier: consumer
      sync_rate: 10
      dictionary_name: kong_rate_limiting
```

Kong offers two rate limiting plugins:
- **rate-limiting** — basic plugin with local or Redis backend
- **rate-limiting-advanced** — premium plugin (included in Kong Gateway OSS) with sliding window, configurable response headers, and granular controls

### Redis vs Local Policy

```
Policy    | Memory    | Distributed | Accuracy
----------|-----------|-------------|----------
local     | Minimal   | No          | Per-node
redis     | External  | Yes         | Global
cluster   | Embedded  | Yes         | Global (synced)
```

The `redis` policy is recommended for multi-node deployments. Redis stores the counters, so all Kong nodes share a single source of truth.

## Comparison Table

| Feature | NGINX | Traefik | Envoy | Kong |
|---------|-------|---------|-------|------|
| **Algorithm** | Token bucket (leaky) | Token bucket | Token bucket + sliding window | Token bucket, fixed window, sliding window |
| **Distributed** | No (single node) | No (single node) | Yes (via RLS + Redis) | Yes (via Redis or cluster) |
| **Per-Consumer** | Manual (via map) | Yes (header-based) | Yes (via RLS descriptors) | Yes (built-in) |
| **Dynamic Updates** | Config reload | Hot reload | Hot reload | Admin API (no restart) |
| **Response Headers** | Manual | No | Custom via Lua | Built-in (X-RateLimit-*) |
| **Burst Handling** | Yes (burst + nodelay) | Yes (burst parameter) | Yes (token bucket max) | Yes (burst config) |
| **Memory per 1K IPs** | ~64 KB | ~128 KB | ~256 KB | Depends on backend |
| **Max Throughput** | ~500K rps | ~200K rps | ~400K rps | ~300K rps |
| **Config Com[plex](https://www.plex.tv/)ity** | Low | Low | Medium-High | Medium |
| **Learning Curve** | Easy | Easy | Steep | Moderate |
| **License** | BSD-2 | MIT | Apache 2.0 | Apache 2.0 |

## Choosing the Right Tool

**Choose NGINX if:** You need simple, fast rate limiting on a single proxy instance. It is battle-tested, uses minimal memory, and the configuration is straightforward. Ideal for protecting a single web application or API behind one reverse proxy.

**Choose Traefik if:** You run containerized services with Docker Compose or Kubernetes and want rate limiting that integrates seamlessly with service discovery. The label-based configuration is clean and declarative.

**Choose Envoy if:** You need distributed rate limiting across a microservice mesh. The RLS + Redis architecture provides global counters, and the sliding window algorithm offers the most accurate rate limiting. Best for organizations already running Envoy as a sidecar or edge proxy.

**Choose Kong if:** You want a full API gateway with rate limiting as one feature among many (authentication, transformation, logging, circuit breaking). The declarative YAML configuration and Admin API make it easy to manage at scale.

## Monitoring Rate Limiting

Rate limiting without monitoring is flying blind. You need to know when limits are being hit, who is being blocked, and whether your thresholds are appropriate.

### NGINX Monitoring

NGINX logs rate-limited requests at the configured `limit_req_log_level`. Parse these with a log aggregator:

```bash
# Count rate-limited requests per hour
grep "limiting requests" /var/log/nginx/error.log | \
  awk '{print $1}' | sort | uniq -c | sort -rn
```

Add a custom log format that includes the rate limit zone:

```nginx
log_format ratelimit '$remote_addr - $request_uri - '
                     '$status - $limit_req_status';
```

### Traefik Metrics

Traefik exposes Prometheus metrics at `/metrics` when enabled:

```yaml
# Enable metrics in static config
metrics:
  prometheus:
    entryPoint: metrics
    addEntryPointsLabels: true
    addRoutersLabels: true
    addServicesLabels: true
```

Key metrics:
- `traefik_middleware_retries_total` — retry counts
- `traefik_entrypoint_requests_total` — request counts per entrypoint
- `traefik_service_requests_total` — request counts per service

### Envoy Metrics

Envoy provides detailed rate limit metrics:

```
envoy_http_local_rate_limit_enabled    — Local rate limit hits
envoy_http_local_rate_limit_enforced   — Enforced rejections
envoy_ratelimit_ok                     — RLS service OK responses
envoy_ratelimit_error                  — RLS service errors
envoy_ratelimit_over_limit             — Rate limit exceeded
```

### Kong Metrics

Kong's Prometheus plugin exposes:

```
kong_http_status_total{code="429"}     — Rate-limited responses
kong_latency                           — Request latency histogram
kong_bandwidth                         — Bandwidth per service
```

Enable the Prometheus plugin on your services:

```yaml
plugins:
  - name: prometheus
    config:
      per_consumer: true
      status_code_metrics: true
      latency_metrics: true
      bandwidth_metrics: true
      upstream_health_metrics: true
```

## Common Pitfalls and How to Avoid Them

**Setting limits too low.** The most common mistake is configuring rate limits based on estimated traffic rather than measured traffic. Start with generous limits, monitor for a week, then tighten based on actual usage patterns.

**Not accounting for NAT.** IP-based rate limiting punishes users behind shared NATs (corporate networks, mobile carriers). Use API key or token-based limiting for authenticated endpoints.

**Forgetting about health checks.** Health check endpoints from load balancers and monitoring systems can consume a significant portion of your rate limit budget. Always exclude health check paths from rate limiting.

**Single point of failure.** If your rate limiter goes down, all traffic is either blocked or unlimited. Design for failure: NGINX and Traefik allow requests through if the rate limit module fails. Envoy has `filter_enforced` runtime keys to disable enforcement dynamically.

**Ignoring the response.** Returning a bare 429 with no body or headers is unhelpful. Include `Retry-After` headers and a JSON body explaining the limit and when the client can retry:

```json
{
  "error": "rate_limit_exceeded",
  "message": "Too many requests. Please retry after 30 seconds.",
  "retry_after": 30,
  "limit": 100,
  "remaining": 0,
  "reset": 1713312000
}
```

## Getting Started Checklist

1. **Audit your traffic.** Before setting any limits, run your proxy for 1-2 weeks with rate limiting disabled. Analyze request patterns per endpoint, per IP, and per consumer.

2. **Start with login endpoints.** These are the highest-value targets for abuse. Set strict limits (3-5 requests per minute) on authentication endpoints first.

3. **Add general API limits.** Set moderate limits (50-100 rps) on your general API endpoints with burst allowance for legitimate spikes.

4. **Implement per-consumer limits.** For authenticated APIs, move from IP-based to token-based rate limiting so legitimate users behind NATs are not unfairly limited.

5. **Set up monitoring.** Configure dashboards for rate limit hits, 429 responses, and rejected IPs. Set alerts for unusual spikes.

6. **Test under load.** Use a load testing tool to verify your rate limiter behaves correctly under sustained traffic and burst conditions.

7. **Document your policy.** Publish rate limit documentation for API consumers. Include the limits, the algorithm used, and the response format for 429 errors.

Self-hosted rate limiting is one of those infrastructure investments that pays for itself the moment it stops an abuse attempt or prevents an outage. The tools are mature, the configurations are well-documented, and the cost is essentially zero. In 2026, there is no excuse for leaving your API unprotected.

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
