---
title: "Best Self-Hosted Rate Limiting & API Throttling Solutions 2026"
date: 2026-04-15
tags: ["comparison", "guide", "self-hosted", "privacy", "api", "security"]
draft: false
description: "Compare Nginx, Traefik, Envoy, and Kong for self-hosted rate limiting and API throttling. Includes Docker setups, configuration examples, and a detailed feature comparison."
---

Rate limiting is one of the most underrated pieces of infrastructure. Whether you are protecting a public API from abuse, preventing brute-force login attempts, or ensuring fair resource allocation across tenants, a good rate limiter sits between your users and your services — and you want full control over it.

Commercial API gateways charge by the request. Cloud WAFs add rate limiting as a premium feature. But every tool you need to throttle, shape, and police API traffic is available as open-source software you can run on your own hardware.

## Why Self-Host Your Rate Limiting

Running your own rate limiting layer gives you advantages that managed services cannot match:

- **No per-request pricing** — Cloud rate limiting costs scale with your traffic. Self-hosted solutions cost the same whether you handle 1,000 or 10 million requests per day.
- **Custom policies** — You are not locked into predefined tiers or fixed windows. Write per-endpoint, per-user, per-IP, or even per-header rules that match your exact business logic.
- **Data stays on your infrastructure** — Rate limiting decisions require inspecting every request. With a self-hosted solution, request metadata never leaves your network.
- **Works alongside any backend** — Whether your services run on bare metal, Kubernetes, or a mix of both, these tools slot in front of them without requiring code changes.
- **Defense in depth** — Rate limiting is not just about abuse prevention. It protects your database connection pools, prevents cascading failures during traffic spikes, and gives you time to auto-scale before things break.

The four solutions covered here — Nginx, Traefik, Envoy, and Kong — all handle rate limiting, but they approach it differently. Each excels in specific scenarios.

---

## Nginx: The Simple, Battle-Tested Choice

Nginx has been the default reverse proxy for over a decade. Its rate limiting is built on a leaky bucket algorithm backed by a shared memory zone. It is simple, fast, and handles millions of requests per second on modest hardware.

### How Nginx Rate Limiting Works

Nginx uses two directives:

- `limit_req_zone` — Defines a shared memory zone and the key to track (usually `$binary_remote_addr` for per-IP limiting).
- `limit_req` — Applies the rate limit within a location or server block.

The shared memory zone is a fixed-size slab allocated at startup. Each unique key gets an entry with a timestamp. Nginx checks timestamps against the configured rate and either passes the request, delays it, or rejects it with a 503.

### Docker Setup

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
      - ./ssl:/etc/nginx/ssl:ro
    restart: unless-stopped
    networks:
      - internal

  api-backend:
    image: your-api:latest
    networks:
      - internal

networks:
  internal:
    driver: bridge
```

### Configuration Example

```nginx
# Define rate limit zones
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/m;
limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;
limit_req_zone $http_api_key zone=per_api_key:10m rate=100r/s;

# Status codes for rejected requests
limit_req_status 429;

# Custom error response
limit_req_log_level warn;

server {
    listen 80;
    server_name api.example.com;

    # General API rate limit — 30 requests per minute per IP
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        limit_req_status 429;

        proxy_pass http://api-backend:8080;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Strict login rate limit — 5 attempts per minute
    location /api/auth/login {
        limit_req zone=login_limit burst=3 nodelay;
        limit_req_status 429;

        proxy_pass http://api-backend:8080;
    }

    # Per-API-key rate limit — 100 requests per second
    location /api/v2/ {
        limit_req zone=per_api_key burst=50 nodelay;

        proxy_pass http://api-backend:8080;
    }

    # Return a JSON error instead of HTML 503
    error_page 429 = @rate_limited;
    location @rate_limited {
        default_type application/json;
        return 429 '{"error":"rate_limit_exceeded","retry_after":60}';
    }
}
```

### Advanced: Nginx Plus Dynamic Rate Limiting

If you can run Nginx Plus (commercial), you get dynamic zone resizing via the API:

```bash
# Increase a zone's rate at runtime
curl -X POST -d '{"max_rate": 200}' \
  http://localhost:8080/api/6/http/limit_req_zones/api_limit
```

For the open-source version, you must reload Nginx to change rates.

### When to Use Nginx for Rate Limiting

- You already run Nginx as your reverse proxy
- You need per-IP or per-header rate limiting with burst support
- Your requirements are straightforward: fixed windows, leaky bucket, simple keying
- You want the lowest possible latency overhead (Nginx adds sub-millisecond latency)

Nginx does not natively support sliding window counters, distributed rate limiting across multiple nodes, or dynamic rules based on upstream response codes. For those, you need something more advanced.

---

## Traefik: Rate Limiting for Dynamic Environments

Traefik is a cloud-native edge router designed for dynamic infrastructure. Its rate limiting is configured as middleware and works seamlessly with Docker, Kubernetes, and service mesh setups.

### How Traefik Rate Limiting Works

Traefik uses a fixed-window counter approach with configurable time windows. Unlike Nginx's per-request delay model, Traefik simply counts requests within each window and rejects anything over the limit. This makes it easier to reason about but less flexible for burst handling.

Traefik supports multiple middleware strategies:

- **IPWhiteList / RateLimit** — Basic per-IP limiting
- **Plugins** — Extended rate limiting via community plugins (sliding window, token bucket, etc.)
- **ForwardAuth integration** — Delegate rate limiting decisions to an external service

### Docker Setup

```yaml
version: "3.8"

services:
  traefik:
    image: traefik:v3.2
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"  # Dashboard
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./traefik.yml:/etc/traefik/traefik.yml:ro
      - ./dynamic.yml:/etc/traefik/dynamic.yml:ro
    restart: unless-stopped
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.traefik.rule=Host(`traefik.example.com`)"
      - "traefik.http.routers.traefik.service=api@internal"
      - "traefik.http.routers.traefik.middlewares=admin-auth"

  api-backend:
    image: your-api:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api.rule=Host(`api.example.com`)"
      - "traefik.http.routers.api.middlewares=api-ratelimit"
      - "traefik.http.services.api.loadbalancer.server.port=8080"
```

### Configuration

`traefik.yml` (static config):

```yaml
api:
  dashboard: true

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

providers:
  docker:
    exposedByDefault: false
  file:
    filename: /etc/traefik/dynamic.yml
```

`dynamic.yml` (dynamic config with rate limiting):

```yaml
http:
  middlewares:
    api-ratelimit:
      rateLimit:
        average: 100       # Average requests per second
        burst: 50          # Allow bursts up to 50 above average
        period: 1s         # Time window
        sourceCriterion:
          ipStrategy:
            depth: 2       # Trust X-Forwarded-For up to 2 proxies

    strict-login-limit:
      rateLimit:
        average: 5
        burst: 2
        period: 1m
        sourceCriterion:
          requestHeaderName: X-Forwarded-For
```

### Kubernetes Ingress Example

```yaml
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata:
  name: api-rate-limit
  namespace: production
spec:
  rateLimit:
    average: 200
    burst: 100
    period: 1s
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  annotations:
    traefik.ingress.kubernetes.io/router.middlewares: production-api-rate-limit@kubernetescrd
spec:
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: api-service
                port:
                  number: 8080
```

### When to Use Traefik for Rate Limiting

- You run services in Docker or Kubernetes and want rate limiting that auto-discovers backends
- You prefer configuration via Docker labels or Kubernetes CRDs
- You need Let's Encrypt TLS automation built in
- Your rate limiting needs are moderate (fixed windows are sufficient)

Traefik's built-in rate limiting is less granular than Nginx or Kong. The real power comes from its plugin ecosystem, where you can add sliding window algorithms, Redis-backed distributed counters, and more.

---

## Envoy: Distributed Rate Limiting at Scale

Envoy is a high-performance service proxy originally built by Lyft. It is the data plane for Istio service mesh and powers the edge routing at companies like Airbnb, Dropbox, and Stripe. Its rate limiting architecture is fundamentally different from Nginx or Traefik.

### How Envoy Rate Limiting Works

Envoy separates the rate limiting decision from the proxy itself. The proxy sends rate limit check requests to a dedicated **Rate Limit Service (RLS)**, which can be any gRPC service that implements the Envoy RLS protocol. The reference implementation is `envoyproxy/ratelimit`, a Redis-backed service.

This architecture means:

- Rate limiting state is centralized in Redis, so multiple Envoy instances share the same counters
- You can implement arbitrary algorithms (fixed window, sliding window, token bucket) in the RLS
- You can change rate limits at runtime by updating the RLS configuration without touching the proxy

### Docker Setup

```yaml
version: "3.8"

services:
  envoy:
    image: envoyproxy/envoy:v1.32
    ports:
      - "80:80"
      - "9901:9901"  # Admin interface
    volumes:
      - ./envoy.yaml:/etc/envoy/envoy.yaml:ro
    depends_on:
      - ratelimit
      - redis

  ratelimit:
    image: envoyproxy/ratelimit:master
    ports:
      - "8081:8081"
      - "6070:6070"
    environment:
      - USE_REDIS_QUOTE=1
      - REDIS_SOCKET_TYPE=tcp
      - REDIS_URL=redis:6379
      - RUNTIME_ROOT=/data
      - RUNTIME_SUBDIRECTORY=
      - RUNTIME_WATCH_ROOT=false
      - LOG_LEVEL=info
    volumes:
      - ./ratelimit-config:/data
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data

  api-backend:
    image: your-api:latest

volumes:
  redis-data:
```

### Envoy Configuration

```yaml
# envoy.yaml
static_resources:
  listeners:
    - name: listener_0
      address:
        socket_address:
          address: 0.0.0.0
          port_value: 80
      filter_chains:
        - filters:
            - name: envoy.filters.network.http_connection_manager
              typed_config:
                "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
                stat_prefix: ingress_http
                route_config:
                  name: local_route
                  virtual_hosts:
                    - name: backend
                      domains: ["*"]
                      routes:
                        - match:
                            prefix: "/api/"
                          route:
                            cluster: api_service
                          typed_per_filter_config:
                            envoy.filters.http.ratelimit:
                              "@type": type.googleapis.com/envoy.extensions.filters.http.ratelimit.v3.RateLimitPerRoute
                              rate_limits:
                                - actions:
                                    - remote_address: {}
                                - actions:
                                    - header_value_match:
                                        descriptor_value: "auth_endpoint"
                                        expect_match: true
                                        headers:
                                          - name: ":path"
                                            string_match:
                                              prefix: "/api/auth/"
                http_filters:
                  - name: envoy.filters.http.ratelimit
                    typed_config:
                      "@type": type.googleapis.com/envoy.extensions.filters.http.ratelimit.v3.RateLimit
                      domain: production
                      failure_mode_deny: true
                      timeout: 50ms
                      rate_limit_service:
                        grpc_service:
                          envoy_grpc:
                            cluster_name: rate_limit_cluster
                  - name: envoy.filters.http.router
                    typed_config:
                      "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router

  clusters:
    - name: api_service
      connect_timeout: 5s
      type: STRICT_DNS
      lb_policy: ROUND_ROBIN
      load_assignment:
        cluster_name: api_service
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    socket_address:
                      address: api-backend
                      port_value: 8080

    - name: rate_limit_cluster
      connect_timeout: 5s
      type: STRICT_DNS
      lb_policy: ROUND_ROBIN
      http2_protocol_options: {}
      load_assignment:
        cluster_name: rate_limit_cluster
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    socket_address:
                      address: ratelimit
                      port_value: 8081
```

### Rate Limit Service Configuration

Create `ratelimit-config/config.yaml`:

```yaml
domain: production
descriptors:
  # Default: 100 requests per minute per IP
  - key: remote_address
    rate_limit:
      unit: minute
      requests_per_unit: 100

  # Login endpoint: 10 requests per minute per IP
  - key: remote_address
    rate_limit:
      unit: minute
      requests_per_unit: 10
    descriptors:
      - key: header_value_match
        value: auth_endpoint
```

### When to Use Envoy for Rate Limiting

- You run a microservice architecture with multiple proxy instances
- You need distributed, consistent rate limiting across all nodes
- You want sliding window or token bucket algorithms backed by Redis
- You are already using Envoy or Istio
- You need runtime-configurable rate limits without restarts

Envoy's architecture is the most powerful of the four options but also the most complex. The separation between proxy and RLS means more moving parts to manage. It is the right choice when you are operating at scale with dozens or hundreds of service instances.

---

## Kong: The Full API Management Platform

Kong is built on top of Nginx and Lua, but it adds a plugin ecosystem, a REST API for configuration, and a database-backed configuration store. Its rate limiting plugin is one of the most feature-complete available.

### How Kong Rate Limiting Works

Kong provides multiple rate limiting plugins:

- **Rate Limiting** — Fixed-window counter per consumer, per IP, per service, or per route
- **Rate Limiting (Advanced)** — Sliding window with configurable time windows, supports Redis cluster for distributed state
- **Request Size Limiting** — Rejects requests over a maximum body size
- **Request Termination** — Blocks specific IPs or user agents entirely

All plugins can be applied at three levels: globally, per-service, or per-route. This gives you fine-grained control over which endpoints are rate limited and how.

### Docker Setup

```yaml
version: "3.8"

services:
  kong:
    image: kong:3.9
    environment:
      KONG_DATABASE: postgres
      KONG_PG_HOST: kong-database
      KONG_PG_PASSWORD: kong
      KONG_PROXY_ACCESS_LOG: /dev/stdout
      KONG_ADMIN_ACCESS_LOG: /dev/stdout
      KONG_PROXY_ERROR_LOG: /dev/stderr
      KONG_ADMIN_ERROR_LOG: /dev/stderr
      KONG_ADMIN_LISTEN: 0.0.0.0:8001
      KONG_ADMIN_GUI_URL: http://localhost:8002
    ports:
      - "80:8000"   # Proxy
      - "443:8443"  # Proxy SSL
      - "8001:8001" # Admin API
      - "8002:8002" # Kong Manager GUI
    depends_on:
      - kong-database
    restart: unless-stopped

  kong-database:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: kong
      POSTGRES_PASSWORD: kong
      POSTGRES_DB: kong
    volumes:
      - kong-data:/var/lib/postgresql/data

  konga:  # Optional admin UI
    image: pantsel/konga
    environment:
      NODE_ENV: production
    ports:
      - "1337:1337"
    depends_on:
      - kong

volumes:
  kong-data:
```

### Configuration via Admin API

```bash
# Bootstrap Kong database (first run only)
docker exec -it kong kong migrations bootstrap

# Create a service
curl -X POST http://localhost:8001/services \
  --data name=api-service \
  --data url=http://api-backend:8080

# Create a route
curl -X POST http://localhost:8001/services/api-service/routes \
  --data name=api-route \
  --data paths[]=/api/

# Apply rate limiting: 100 requests per minute per consumer
curl -X POST http://localhost:8001/services/api-service/plugins \
  --data name=rate-limiting \
  --data config.minute=100 \
  --data config.policy=redis \
  --data config.redis.host=redis-server \
  --data config.redis.port=6379 \
  --data config.limit_by=consumer \
  --data config.hide_client_headers=false

# Apply strict login rate limiting: 10 requests per minute per IP
curl -X POST http://localhost:8001/routes/api-route/plugins \
  --data name=rate-limiting \
  --data config.minute=10 \
  --data config.policy=cluster \
  --data config.limit_by=ip
```

### Declarative Configuration (DB-less Mode)

For simpler deployments, Kong can run without a database using a declarative config file:

```yaml
# kong.yaml
_format_version: "3.0"

services:
  - name: api-service
    url: http://api-backend:8080
    routes:
      - name: api-route
        paths:
          - /api/
        plugins:
          - name: rate-limiting
            config:
              minute: 100
              policy: local  # In-memory, no Redis needed
              limit_by: ip
              hide_client_headers: false

  - name: auth-service
    url: http://auth-backend:8080
    routes:
      - name: login-route
        paths:
          - /api/auth/login
        plugins:
          - name: rate-limiting
            config:
              minute: 10
              policy: local
              limit_by: ip
          - name: request-size-limiting
            config:
              allowed_payload_size: 1  # 1 MB max
```

Start Kong in DB-less mode:

```bash
docker run -d --name kong \
  -p 80:8000 -p 443:8443 -p 8001:8001 \
  -e KONG_DATABASE=off \
  -e KONG_DECLARATIVE_CONFIG=/kong.yaml \
  -v $(pwd)/kong.yaml:/kong.yaml \
  kong:3.9
```

### When to Use Kong for Rate Limiting

- You need a full API management platform (rate limiting, authentication, transformation, logging) in one tool
- You want to manage configuration via REST API or declarative YAML
- You need per-consumer rate limiting tied to API keys or JWT tokens
- You want built-in observability with Prometheus metrics
- You need the flexibility of Nginx plus a plugin ecosystem

Kong's main trade-off is resource usage. Running PostgreSQL for configuration adds overhead compared to Nginx or Traefik. In DB-less mode, this is less of a concern, but you lose dynamic configuration updates.

---

## Feature Comparison

| Feature | Nginx | Traefik | Envoy | Kong |
|---|---|---|---|---|
| **Algorithm** | Leaky bucket | Fixed window | Any (via RLS) | Fixed / Sliding window |
| **Distributed state** | No (per-node) | No (per-node) | Yes (Redis-backed) | Yes (Redis cluster) |
| **Per-IP limiting** | Yes | Yes | Yes | Yes |
| **Per-consumer limiting** | Manual (via header) | Via middleware | Via RLS descriptor | Native (API key / JWT) |
| **Burst handling** | Yes (`burst` + `nodelay`) | Yes (`burst` param) | Via RLS logic | Yes (`burst` param) |
| **Runtime config changes** | No (reload required) | Yes (hot reload) | Yes (RLS config update) | Yes (Admin API) |
| **Custom response codes** | Yes (429) | Yes (429) | Yes (configurable) | Yes (429) |
| **Dashboard / GUI** | No | Built-in | Admin interface | Kong Manager |
| **Kubernetes support** | Ingress annotations | Native CRDs | Envoy Gateway | Kong Ingress Controller |
| **Setup complexity** | Low | Low | High | Medium |
| **Resource usage** | Minimal | Low | Medium | Medium-High |
| **Plugin ecosystem** | Limited | Growing | Extensive | Extensive |
| **Best for** | Simple, high-performance | Docker/K8s environments | Microservices at scale | Full API management |

---

## Choosing the Right Solution

The best rate limiter depends on what you are protecting and how you operate.

**For a single server or small cluster**, Nginx is hard to beat. It adds virtually no latency, the configuration is straightforward, and it handles everything you need for per-IP rate limiting. If you already run Nginx as your reverse proxy, there is zero reason to add another component.

**For Docker or Kubernetes environments** where services come and go, Traefik's auto-discovery and label-based configuration save hours of manual setup. The rate limiting is not as sophisticated as Envoy or Kong, but it is more than adequate for most APIs and internal services.

**For microservice architectures with many proxy instances**, Envoy's distributed rate limiting is the only choice that gives you globally consistent counters. If you are running Istio or planning to, Envoy is already your data plane — just add the RLS.

**For organizations that want a complete API management platform**, Kong offers rate limiting alongside authentication, request transformation, response caching, logging, and monitoring. It is the most feature-complete option, and its Admin API makes it easy to integrate rate limiting into CI/CD pipelines or internal tooling.

A practical migration path many teams follow: start with Nginx for basic rate limiting, move to Traefik when container orchestration becomes necessary, adopt Envoy when distributed counters become a requirement, and layer Kong on top when API management needs grow beyond simple rate limiting.

Whichever tool you choose, the most important step is to actually deploy rate limiting before you need it. The time to set up login brute-force protection is not during the brute-force attack.
