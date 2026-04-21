---
title: "Self-Hosted API Gateway: Apache APISIX vs Kong vs Tyk — Complete Guide 2026"
date: 2026-04-13
tags: ["comparison", "guide", "self-hosted", "api", "microservices", "infrastructure"]
draft: false
description: "Compare Apache APISIX, Kong Gateway, and Tyk for self-hosted API management. Installation guides, Docker setups, feature comparison, and performance benchmarks for 2026."
---

If you are running microservices, exposing internal APIs to external consumers, or building a platform that third-party developers integrate with, an API gateway is no longer optional — it is essential. Commercial cloud gateways charge per million requests, lock you into a vendor ecosystem, and add latency by routing your traffic through their infrastructure.

Self-hosting your API gateway gives you full control over routing logic, rate limiting policies, authentication flows, and observability data. In this guide, we compare three of the most capable open-source API gateways available in 2026: **Apache APISIX**, **Kong Gateway**, and **Tyk**.

## Why Self-Host Your API Gateway?

Running an API gateway on your own infrastructure provides concrete advantages that cloud-managed alternatives simply cannot match:

**No per-request pricing.** Cloud API gateways charge based on the number of API calls. At scale, this becomes a significant and unpredictable line item. A self-hosted gateway runs on hardware you already own or rent at a flat rate.

**Zero external latency.** Every hop adds milliseconds. When your gateway sits in the same network as your services, request routing happens in microseconds rather than being routed across regions.

**Full data ownership.** Access logs, request bodies, authentication tokens, and routing decisions never leave your infrastructure. This matters for HIPAA, GDPR, SOC 2, and internal security policies.

**Unlimited customization.** You can write custom plugins in the language of your choice, modify the proxy behavior at the code level, and integrate with any internal system without waiting for vendor support.

**No vendor lock-in.** Your routing rules, plugin configurations, and consumer data belong to you. Migrating between cloud providers never means rebuilding your entire API management layer.

**Horizontal scaling on your terms.** Add nodes when you need capacity, remove them when you do not. You control the scaling policy and the underlying resource allocation.

## What Is an API Gateway?

An API gateway sits between clients and your backend services, acting as a single entry point for all API traffic. Instead of clients connecting directly to dozens of microservices, they connect to the gateway, which handles:

- **Request routing** — forwarding requests to the correct backend service based on path, host, or header
- **Authentication and authorization** — validating JWT tokens, API keys, OAuth2 flows, and mTLS certificates
- **Rate limiting and throttling** — protecting backend services from abuse and ensuring fair resource allocation
- **Request and response transformation** — modifying headers, rewriting URLs, aggregating responses from multiple services
- **Load balancing** — distributing traffic across multiple instances of a backend service
- **Observability** — collecting metrics, traces, and logs for monitoring and debugging
- **Caching** — storing responses to reduce backend load and improve response times

Without a gateway, each of these concerns must be implemented separately in every microservice, leading to duplicated code, inconsistent behavior, and a maintenance nightmare.

## Quick Comparison at a Glance

| Feature | Apache APISIX | Kong Gateway | Tyk |
|---------|:-------------:|:------------:|:---:|
| **Core runtime** | Nginx + LuaJIT | Nginx + Lua | Go |
| **License** | Apache 2.0 | Apache 2.0 (CE) | MPL 2.0 (CE) |
| **Configuration** | etcd / YAML / Admin API | PostgreSQL / Declarative YAML | MongoDB / Redis / Declarative YAML |
| **Hot-reload plugins** | Yes (no restart) | Limited | Yes |
| **Plugin ecosystem** | 80+ built-in | 100+ built-in + marketplace | 50+ built-in |
| **Dashboard (free)** | Community dashboard | Kong Manager (CE) | Tyk Dashboard (paid) |
| **GraphQL support** | Yes | Yes (paid in Kong Konnect) | Yes (CE) |
| **gRPC proxy** | Yes | Yes | Yes |
| **Service mesh (mTLS)** | Yes | Yes | Yes |
| **WAF support** | Yes (built-in) | Yes (via plugin) | Yes (built-in in CE) |
| **Performance (rps)** | ~140,000+ | ~100,000+ | ~70,000+ |
| **Language for plugins** | Lua, Go, Java, Python, Wasm | Lua, Go, Python, Wasm | Go, Python, JavaScript, Wasm |
| **Key advantage** | Highest performance, dynamic config | Largest ecosystem, mature | Go runtime, developer-friendly |
| **Best for** | High-traffic, latency-sensitive workloads | Teams already in Kong ecosystem | Go-centric teams wanting simplicity |

## Apache APISIX — The Performance Leader

Apache APISIX is a cloud-native, high-performance API gateway originally developed by API7 and donated to the Apache Software Foundation. It is built on Nginx and LuaJIT, uses etcd for configuration storage, and supports hot-reloading of plugins without restarting the gateway process.

### Key Strengths

APISIX stands out for raw throughput and dynamic configuration. The etcd-backed architecture means configuration changes propagate across a cluster in milliseconds without requiring a reload. Plugins can be added, removed, or modified on the fly — no service interruption.

The plugin ecosystem is extensive. Built-in plugins cover authentication (JWT, Key Auth, OAuth2, LDAP, OpenID Connect), traffic control (rate limiting, request ID, proxy cache), security (CORS, IP restriction, URI blocker, WAF), observability (Prometheus, SkyWalking, Zipkin, OpenTelemetry), and serverless integrations (AWS Lambda, Apache OpenWhisk).

APISIX also supports Apache APISIX Ingress Controller for [kubernetes](https://kubernetes.io/) environments, making it a natural fit for teams already running K8s.

### [docker](https://www.docker.com/) Deployment

The fastest way to run APISIX locally or in production is with Docker Compose:

```yaml
version: "3.8"

services:
  etcd:
    image: bitnami/etcd:3.5
    environment:
      ALLOW_NONE_AUTHENTICATION: "yes"
      ETCD_ADVERTISE_CLIENT_URLS: "http://etcd:2379"
    volumes:
      - etcd_data:/bitnami/etcd

  apisix:
    image: apache/apisix:3.11.0-debian
    ports:
      - "9080:9080"
      - "9443:9443"
      - "9180:9180"
    environment:
      APISIX_STAND_ALONE: "false"
    depends_on:
      - etcd
    volumes:
      - ./apisix_conf/config.yaml:/usr/local/apisix/conf/config.yaml:ro

volumes:
  etcd_data:
```

The configuration file `apisix_conf/config.yaml` connects APISIX to etcd:

```yaml
deployment:
  role: traditional
  role_traditional:
    config_provider: etcd
  admin:
    allow_admin:
      - 0.0.0.0/0
    admin_key:
      - name: admin
        key: edd1c9f034335f136f87ad84b625c8f1
        role: admin
  etcd:
    host:
      - "http://etcd:2379"
    prefix: "/apisix"
    timeout: 30
```

Start the stack:

```bash
mkdir -p apisix_conf
# Save the config above, then:
docker compose up -d
```

### Creating Your First Route

Once running, add a route via the Admin API:

```bash
curl -i http://127.0.0.1:9180/apisix/admin/routes/1 \
  -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1" \
  -X PUT -d '
{
  "uri": "/api/*",
  "upstream": {
    "type": "roundrobin",
    "nodes": {
      "httpbin.org:80": 1
    }
  },
  "plugins": {
    "limit-count": {
      "count": 100,
      "time_window": 60,
      "rejected_code": 429
    }
  }
}'
```

This routes all requests under `/api/` to httpbin.org with a rate limit of 100 requests per minute.

### Standalone Mode

For simpler deployments, APISIX supports a standalone mode that reads configuration from a local YAML file instead of etcd. This eliminates the etcd dependency entirely:

```yaml
# apisix_conf/config-standalone.yaml
routes:
  - uri: /api/*
    upstream:
      type: roundrobin
      nodes:
        "httpbin.org:80": 1
    plugins:
      limit-count:
        count: 100
        time_window: 60
```

Set `APISIX_STAND_ALONE: "true"` in the Docker Compose environment and mount this file.

## Kong Gateway — The Ecosystem Giant

Kong is the most widely deployed open-source API gateway. Built on Nginx and OpenResty, it has been in production at thousands of organizations since 2015. Kong Gateway Community Edition is free and Apache 2.0 licensed, with an enterprise tier offering additional features through Kong Konnect.

### Key Strengths

Kong's biggest advantage is its maturity and ecosystem. With over a decade of development, it has been battle-tested at massive scale. The plugin marketplace offers both official and community-contributed plugins covering nearly every integration you could imagine.

Kong supports two operational modes:

1. **Database mode** — uses PostgreSQL or Cassandra for configuration persistence. Ideal for multi-node clusters where configuration must be shared.
2. **DB-less mode** — uses a declarative YAML file. Configuration is loaded at startup or via the Admin API with in-memory storage. Simpler to operate, ideal for containerized deployments.

Kong also provides Kong Ingress Controller for Kubernetes, Kong Mesh (service mesh), and Konnect (SaaS management plane) for teams that want a hybrid approach.

### Docker Deployment

Running Kong in DB-less mode is the simplest path:

```yaml
version: "3.8"

services:
  kong:
    image: kong:3.9
    environment:
      KONG_DATABASE: "off"
      KONG_PROXY_ACCESS_LOG: /dev/stdout
      KONG_ADMIN_ACCESS_LOG: /dev/stdout
      KONG_PROXY_ERROR_LOG: /dev/stderr
      KONG_ADMIN_ERROR_LOG: /dev/stderr
      KONG_ADMIN_LISTEN: "0.0.0.0:8001"
      KONG_ADMIN_GUI_URL: "http://localhost:8002"
    ports:
      - "8000:8000"
      - "8443:8443"
      - "8001:8001"
      - "8002:8002"
      - "8444:8444"
    volumes:
      - ./kong.yml:/kong/declarative/kong.yml:ro
```

The declarative configuration file:

```yaml
_format_version: "3.0"

services:
  - name: api-backend
    url: http://httpbin.org
    routes:
      - name: api-route
        paths:
          - /api
    plugins:
      - name: rate-limiting
        config:
          minute: 100
          policy: local
      - name: cors
        config:
          origins:
            - "https://example.com"
          methods:
            - GET
            - POST
            - PUT
            - DELETE
          headers:
            - Accept
            - Content-Type
            - Authorization
```

Start Kong:

```bash
docker compose up -d
```

### Database-Backed Deployment

For production multi-node clusters, use PostgreSQL:

```yaml
version: "3.8"

services:
  kong-database:
    image: postgres:16
    environment:
      POSTGRES_USER: kong
      POSTGRES_DB: kong
      POSTGRES_PASSWORD: kong
    volumes:
      - pg_data:/var/lib/postgresql/data

  kong-migrations:
    image: kong:3.9
    command: kong migrations bootstrap
    environment:
      KONG_DATABASE: postgres
      KONG_PG_HOST: kong-database
      KONG_PG_PASSWORD: kong
    depends_on:
      - kong-database

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
      KONG_ADMIN_LISTEN: "0.0.0.0:8001"
      KONG_PROXY_LISTEN: "0.0.0.0:8000"
    ports:
      - "8000:8000"
      - "8001:8001"
    depends_on:
      - kong-migrations

volumes:
  pg_data:
```

Bootstrap the database and start:

```bash
docker compose run kong-migrations kong migrations bootstrap
docker compose up -d
```

### Managing Services via Admin API

```bash
# Create a service
curl -i -X POST http://localhost:8001/services \
  --data name=my-service \
  --data url=http://backend-service:3000

# Add a route
curl -i -X POST http://localhost:8001/services/my-service/routes \
  --data paths[]=/v1 \
  --data strip_path=true

# Add authentication
curl -i -X POST http://localhost:8001/services/my-service/plugins \
  --data name=key-auth
```

## Tyk — The Go-Native Gateway

Tyk is written entirely in Go, which gives it a different architectural profile compared to the Nginx-based gateways. The Community Edition is MPL 2.0 licensed and provides a solid set of features without requiring a commercial license.

### Key Strengths

Tyk's Go runtime means it is easier to contribute to and extend for teams already comfortable with Go. The plugin architecture supports Go, Python, JavaScript, and WebAssembly plugins, giving developers flexibility in how they extend gateway behavior.

Tyk's configuration model is straightforward — APIs are defined in JSON or YAML, and the gateway reads them from a local directory or from Redis. There is no external database requirement for single-node deployments, and Redis clustering handles multi-node configuration sync.

The built-in dashboard in Tyk is only available in the commercial Pro and Enterprise editions, but the Community Edition can be managed entirely via the REST API and declarative configuration files.

### Docker Deployment

```yaml
version: "3.8"

services:
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  tyk-gateway:
    image: tykio/tyk-gateway:v5.3
    ports:
      - "8080:8080"
    environment:
      TYK_GW_SECRET: "super-secret"
      TYK_GW_NODESECRET: "node-secret"
      TYK_GW_STORAGE_HOST: "redis"
      TYK_GW_STORAGE_PORT: 6379
      TYK_GW_STORAGE_PASSWORD: ""
      TYK_GW_STORAGE_TYPE: "redis"
    volumes:
      - ./tyk.conf:/opt/tyk-gateway/tyk.conf:ro
    depends_on:
      - redis

volumes:
  redis_data:
```

The `tyk.conf` configuration file:

```json
{
  "listen_port": 8080,
  "secret": "super-secret",
  "node_secret": "node-secret",
  "storage": {
    "type": "redis",
    "host": "redis",
    "port": 6379,
    "database": 0
  },
  "enable_analytics": false,
  "enable_health_checks": true,
  "health_check_value_timeouts": 60
}
```

Start the gateway:

```bash
docker compose up -d
```

### Defining APIs with Declarative Files

Tyk loads API definitions from the `/opt/tyk-gateway/apps/` directory. Create a JSON file for each API:

```json
{
  "name": "Public API",
  "api_id": "public-api-001",
  "org_id": "default-org",
  "use_keyless": true,
  "definition": {
    "location": "header",
    "key": "x-api-version"
  },
  "proxy": {
    "listen_path": "/api/",
    "target_url": "http://backend-service:3000/",
    "strip_listen_path": true
  },
  "version_data": {
    "not_versioned": true,
    "versions": {
      "Default": {
        "name": "Default",
        "global_rate_limit": {
          "rate": 100,
          "per": 60
        },
        "extended_paths": {
          "ignored": [],
          "white_list": [],
          "black_list": []
        }
      }
    }
  }
}
```

Mount this file into the container:

```yaml
    volumes:
      - ./tyk.conf:/opt/tyk-gateway/tyk.conf:ro
      - ./apps/:/opt/tyk-gateway/apps/:ro
```

### Managing APIs via REST API

```bash
# Create an API definition
curl -X POST http://localhost:8080/tyk/apis \
  -H "x-tyk-authorization: super-secret" \
  -H "Content-Type: application/json" \
  -d @api-definition.json

# Reload the gateway to apply changes
curl -X POST http://localhost:8080/tyk/reload/group \
  -H "x-tyk-authorization: super-secret"

# Create an API key
curl -X POST http://localhost:8080/tyk/keys/create \
  -H "x-tyk-authorization: super-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "allowance": 1000,
    "rate": 100,
    "per": 60,
    "expires": -1,
    "quota_max": 100000,
    "quota_renews": 1640995200,
    "quota_remaining": 100000,
    "quota_renewal_rate": 3600
  }'
```

## Performance and Architecture Comparison

The architectural differences between these three gateways have real implications for performance, operational com[plex](https://www.plex.tv/)ity, and extensibility.

### Runtime Performance

In independent benchmarks conducted in 2025–2026, Apache APISIX consistently achieves the highest request throughput:

| Gateway | Requests/sec | P99 Latency | CPU Usage |
|---------|:-----------:|:-----------:|:---------:|
| APISIX (4 workers) | ~142,000 | 2.1 ms | 78% |
| Kong (4 workers) | ~104,000 | 3.4 ms | 82% |
| Tyk (4 goroutines) | ~72,000 | 4.8 ms | 65% |

These numbers vary based on workload characteristics — Tyk's Go runtime uses less CPU at lower request volumes but does not scale as aggressively under extreme load. Kong sits in the middle with its mature Nginx+Lua stack. APISIX leads due to its optimized LuaJIT pipeline and etcd-based configuration that avoids disk I/O.

### Configuration Distribution

How each gateway distributes configuration across a cluster matters for operational reliability:

- **APISIX** uses etcd, a strongly consistent distributed key-value store. Configuration changes propagate via etcd's watch mechanism in under 100ms across all nodes. No restart or reload needed.

- **Kong** in database mode relies on PostgreSQL polling for configuration changes, with a configurable interval (default 5 seconds). In DB-less mode, configuration must be redeployed to each node independently.

- **Tyk** uses Redis pub/sub for configuration synchronization across gateway nodes. Changes propagate in 1–2 seconds. A manual or API-triggered reload is required for some changes.

### Extensibility

All three gateways support custom plugins, but the developer experience differs:

- **APISIX** supports Lua, Go (via gRPC plugin runner), Java, Python, and WebAssembly. The Wasm support uses the Proxy-Wasm ABI, making plugins portable across gateways.

- **Kong** supports Lua (native), Go (via go-pluginserver), Python (via Pongo), and WebAssembly (Proxy-Wasm). The Lua plugin API is the most mature and well-documented.

- **Tyk** supports Go (native), Python, JavaScript (Otto VM), and WebAssembly. The Go native plugin support is the most performant of the three, as plugins compile into shared libraries loaded directly into the gateway process.

## Production Deployment Checklist

Regardless of which gateway you choose, these practices apply to production deployments:

**1. Always use TLS termination at the gateway.** Terminate TLS at the gateway layer and use mTLS for internal service-to-service communication. This gives you centralized certificate management and the ability to enforce TLS version and cipher suite policies.

**2. Implement rate limiting at multiple layers.** Set global rate limits at the gateway level, per-consumer rate limits based on API key or OAuth client, and per-route limits for sensitive endpoints. Defense in depth prevents abuse even if one layer is misconfigured.

**3. Enable structured access logging.** Log every request with correlation IDs, upstream response times, and consumer identification. Ship logs to a centralized system (Loki, Elasticsearch, or CloudWatch) for analysis.

**4. Use health checks on upstream services.** Configure active and passive health checks so the gateway can automatically remove unhealthy backends from the load balancing pool and retry requests on healthy instances.

**5. Monitor gateway metrics.** Track request rate, error rate, latency percentiles, and upstream response times. Set alerts on error rate spikes and latency degradation.

**6. Version your API configurations.** Store all gateway configuration in version control. Use declarative configuration files rather than the Admin API for production changes, so you can audit, review, and roll back configuration changes.

**7. Run multiple gateway instances behind a load balancer.** Even a single-region deployment should run at least two gateway instances for high availability. Use a layer-4 load balancer (HAProxy, CloudFlare, or AWS NLB) to distribute traffic across them.

## Which One Should You Choose?

The decision comes down to your team's priorities and existing infrastructure:

**Choose Apache APISIX if** you need maximum throughput, hot-reloadable plugins, and a fully dynamic configuration system. It is the best choice for high-traffic API platforms where every millisecond of latency matters and configuration changes happen frequently.

**Choose Kong Gateway if** you want the most mature ecosystem, the largest plugin marketplace, and a tool that has been proven at massive scale across thousands of organizations. The learning curve is moderate, documentation is excellent, and community support is unmatched.

**Choose Tyk if** your team is Go-centric and values a simpler operational model. The Redis-backed configuration is easy to understand and debug, the Go plugin system is performant, and the API-first design feels natural to developers.

All three are excellent choices for self-hosted API management in 2026. You cannot go wrong with any of them — the key is to start, iterate on your configuration, and let your actual traffic patterns guide your optimization decisions.

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
