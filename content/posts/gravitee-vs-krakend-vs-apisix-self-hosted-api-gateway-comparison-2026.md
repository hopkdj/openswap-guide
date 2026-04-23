---
title: "Gravitee vs KrakenD vs Apache APISix: Best Self-Hosted API Gateway 2026"
date: 2026-04-23
tags: ["comparison", "guide", "self-hosted", "api", "microservices", "infrastructure"]
draft: false
description: "Compare Gravitee.io, KrakenD, and Apache APISix for self-hosted API gateway deployment. Full Docker setups, feature comparison, configuration examples, and performance analysis for 2026."
---

If you are exposing APIs to external developers, routing traffic between microservices, or need rate limiting, authentication, and transformation at the edge — you need an API gateway. Cloud-managed gateways like Amazon API Gateway or Azure API Management charge per million requests, lock you into a single provider, and add latency by bouncing your traffic through their infrastructure.

Self-hosted API gateways give you full control, zero per-request fees, and the ability to run entirely on your own servers. In this guide, we compare three leading open-source options: **Gravitee.io API Management**, **KrakenD**, and **Apache APISix** — evaluating architecture, deployment complexity, feature sets, and performance to help you pick the right gateway for your stack.

For readers already familiar with the API gateway landscape, our [APISix vs Kong vs Tyk comparison](../self-hosted-api-gateway-apisix-kong-tyk-guide/) covers two additional enterprise-grade options. If you are looking for related infrastructure, our [rate limiting and API throttling guide](../self-hosted-rate-limiting-api-throttling-nginx-traefik-envoy-kong-2026/) covers how to protect your APIs from abuse.

## Why Self-Host an API Gateway?

Running your own API gateway gives you several advantages over managed alternatives:

- **No per-request pricing** — Managed gateways charge $1-5 per million API calls. At scale, this adds up quickly. Self-hosted gateways cost only your server infrastructure.
- **Data sovereignty** — All API traffic, logs, and analytics stay within your network. No third-party access to request metadata or payload data.
- **Custom plugins and transformations** — Self-hosted gateways let you write custom plugins in any supported language without going through a vendor approval process.
- **No vendor lock-in** — You control the configuration format, deployment model, and upgrade cadence. Switching between self-hosted gateways is a configuration exercise, not a migration project.
- **Lower latency** — Running the gateway on the same network as your backend services eliminates the extra network hop that cloud gateways introduce.

## Gravitee.io API Management

Gravitee.io is a full-featured API Management platform built in Java. It provides not just a gateway but a complete API lifecycle management system: design, deploy, secure, monitor, and monetize APIs through a unified web console.

| Attribute | Details |
|---|---|
| **Language** | Java |
| **License** | Apache 2.0 |
| **GitHub Stars** | 406 (gravitee-api-management) |
| **Last Update** | April 2026 |
| **Architecture** | Gateway + Management API + Management UI + Developer Portal |
| **Dependencies** | MongoDB, Elasticsearch |
| **Docker Images** | `graviteeio/apim-gateway`, `graviteeio/apim-management-api`, `graviteeio/apim-management-ui`, `graviteeio/apim-portal-ui` |

### Architecture

Gravitee uses a multi-component architecture:

- **Gateway** — The runtime proxy that handles all API traffic, applies policies, and routes requests to backends.
- **Management API** — REST API for configuring APIs, plans, subscriptions, and policies.
- **Management UI** — Web console for administrators to manage the entire API lifecycle.
- **Developer Portal** — Self-service portal where developers can discover APIs, subscribe to plans, and access documentation.

All components share configuration through MongoDB (for API definitions, subscriptions, and metadata) and Elasticsearch (for analytics and health monitoring).

### Docker Compose Deployment

Gravitee provides an official Docker Compose setup that deploys the full stack with MongoDB and Elasticsearch:

```yaml
version: '3.5'

networks:
  frontend:
    name: frontend
  storage:
    name: storage

volumes:
  data-elasticsearch:
  data-mongo:

services:
  mongodb:
    image: mongo:6.0.8
    container_name: gio_apim_mongodb
    restart: always
    volumes:
      - data-mongo:/data/db
    networks:
      - storage

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.8.1
    container_name: gio_apim_elasticsearch
    restart: always
    volumes:
      - data-elasticsearch:/usr/share/elasticsearch/data
    environment:
      - discovery.type=single-node
    networks:
      - storage

  gateway:
    image: graviteeio/apim-gateway:4
    container_name: gio_apim_gateway
    restart: always
    ports:
      - "8082:8082"
    depends_on:
      - mongodb
      - elasticsearch
    environment:
      - gravitee_management_mongodb_uri=mongodb://mongodb:27017/gravitee
      - gravitee_ratelimit_mongodb_uri=mongodb://mongodb:27017/gravitee
      - gravitee_analytics_elasticsearch_endpoints_0=http://elasticsearch:9200
    networks:
      - frontend
      - storage

  management_api:
    image: graviteeio/apim-management-api:4
    container_name: gio_apim_management_api
    restart: always
    ports:
      - "8083:8083"
    depends_on:
      - mongodb
    environment:
      - gravitee_management_mongodb_uri=mongodb://mongodb:27017/gravitee
      - gravitee_analytics_elasticsearch_endpoints_0=http://elasticsearch:9200
    networks:
      - frontend
      - storage

  management_ui:
    image: graviteeio/apim-management-ui:4
    container_name: gio_apim_management_ui
    restart: always
    ports:
      - "8084:8080"
    environment:
      - MGMT_API_URL=http://localhost:8083/management/
    networks:
      - frontend

  portal_ui:
    image: graviteeio/apim-portal-ui:4
    container_name: gio_apim_portal_ui
    restart: always
    ports:
      - "8085:8080"
    environment:
      - PORTAL_API_URL=http://localhost:8083/portal/
    networks:
      - frontend
```

Start the full stack with:

```bash
docker-compose up -d
```

After startup, access the Management UI at `http://localhost:8084`, the Developer Portal at `http://localhost:8085`, and the Gateway at `http://localhost:8082`.

### Key Features

- **Full API lifecycle** — Design, publish, version, deprecate, and retire APIs through the web console.
- **Policy chain** — 50+ built-in policies including rate limiting, JWT validation, OAuth2, IP filtering, content transformation, caching, and logging.
- **Developer Portal** — Auto-generated API documentation, interactive testing console, and subscription management.
- **Analytics dashboard** — Request metrics, response times, error rates, and usage analytics powered by Elasticsearch.
- **Multi-tenancy** — Support for multiple organizations with isolated API catalogs and user management.
- **Alerting** — Configurable alerts for error rates, latency spikes, and traffic anomalies.

## KrakenD

KrakenD is a high-performance, stateless API gateway written in Go. Unlike Gravitee, KrakenD focuses on being an API gateway and aggregation layer — it does not include a management UI, developer portal, or API lifecycle tools. Configuration is entirely file-based using a declarative JSON format.

| Attribute | Details |
|---|---|
| **Language** | Go |
| **License** | Apache 2.0 |
| **GitHub Stars** | 2,600 (krakend-ce) |
| **Last Update** | April 2026 |
| **Architecture** | Single binary, stateless |
| **Dependencies** | None (optional: external logging/metrics) |
| **Docker Image** | `devopsfaith/krakend:latest` or `krakend/krakend-ce:latest` |

### Architecture

KrakenD's architecture is deliberately simple: a single stateless binary that reads a JSON configuration file and proxies/aggregates API requests. There is no database, no management API, and no UI in the Community Edition. This design makes KrakenD extremely fast and easy to deploy, but it means all configuration changes require editing the JSON file and restarting the process (or hot-reloading via SIGHUP).

KrakenD excels at **API aggregation** — combining responses from multiple backend services into a single response, reducing client-side round trips. It also supports response transformation, request manipulation, and comprehensive security policies.

### Docker Deployment

KrakenD's simplicity means you only need a single container. First, create a configuration file:

```json
{
  "$schema": "https://www.krakend.io/schema/krakend.json",
  "version": 3,
  "name": "My API Gateway",
  "port": 8080,
  "host": ["http://backend-service:8080"],
  "endpoints": [
    {
      "endpoint": "/api/users/{id}",
      "method": "GET",
      "backend": [
        {
          "url_pattern": "/users/{id}",
          "host": ["http://user-service:3000"]
        }
      ],
      "extra_config": {
        "validation/cel": [
          {
            "check_expr": "req_params.Id matches '^\\\\d+$'"
          }
        ]
      }
    },
    {
      "endpoint": "/api/dashboard",
      "method": "GET",
      "backend": [
        {
          "url_pattern": "/user/{resp0.id}/profile",
          "host": ["http://user-service:3000"],
          "mapping": {"name": "user_name"}
        },
        {
          "url_pattern": "/user/{resp0.id}/orders",
          "host": ["http://order-service:3000"],
          "mapping": {"orders": "user_orders"},
          "group": "orders"
        }
      ]
    }
  ],
  "extra_config": {
    "security/cors": {
      "allow_origins": ["*"],
      "allow_methods": ["GET", "POST", "PUT", "DELETE"],
      "allow_headers": ["Authorization", "Content-Type"]
    }
  }
}
```

Run KrakenD with Docker:

```bash
docker run -d \
  -p 8080:8080 \
  -v $(pwd)/krakend.json:/etc/krakend/krakend.json \
  krakend/krakend-ce:latest run -c /etc/krakend/krakend.json
```

For a Docker Compose setup with hot-reload support:

```yaml
version: '3.8'

services:
  krakend:
    image: krakend/krakend-ce:latest
    container_name: krakend_gateway
    restart: always
    ports:
      - "8080:8080"
    volumes:
      - ./krakend.json:/etc/krakend/krakend.json:ro
    command: ["run", "-c", "/etc/krakend/krakend.json"]
```

Reload configuration without restarting:

```bash
docker kill -s HUP krakend_gateway
```

### Key Features

- **API aggregation** — Combine multiple backend responses into a single client response, reducing network round trips.
- **Stateless architecture** — No database dependency. Scale horizontally by adding more instances behind a load balancer.
- **Declarative configuration** — Everything defined in a single JSON file. Version-controllable and reviewable via pull requests.
- **High performance** — Written in Go with minimal overhead. Benchmarks show 20,000+ requests per second on a single core.
- **Content transformation** — Response mapping, field filtering, query parameter manipulation, and header rewriting.
- **Security** — CORS, JWT validation, rate limiting, HSTS, and custom CEL (Common Expression Language) validations.
- **No vendor lock-in** — Standard JSON configuration that is portable and human-readable.

## Apache APISIX

Apache APISIX is a cloud-native, high-performance API gateway built on NGINX and Lua. It uses etcd as its configuration store, enabling dynamic routing changes without reloading the gateway process. APISIX supports both traditional API gateway features and newer capabilities like serverless functions and gRPC proxying.

| Attribute | Details |
|---|---|
| **Language** | Lua (runs on NGINX via OpenResty) |
| **License** | Apache 2.0 |
| **GitHub Stars** | 16,503 |
| **Last Update** | April 2026 |
| **Architecture** | Gateway + etcd + optional Dashboard |
| **Dependencies** | etcd (required) |
| **Docker Image** | `apache/apisix` |

### Architecture

APISIX runs on OpenResty (NGINX + LuaJIT), with etcd as the configuration backend. This combination gives APISIX two key advantages:

1. **Hot reloading** — Configuration changes are pushed to etcd and picked up by all gateway nodes within milliseconds. No process restart needed.
2. **Distributed coordination** — Multiple APISIX instances share configuration through etcd, enabling seamless horizontal scaling.

The optional APISIX Dashboard provides a web UI for managing routes, services, consumers, and plugins.

### Docker Compose Deployment

APISIX provides an official Docker Compose setup:

```yaml
version: "3"

services:
  apisix:
    image: apache/apisix:latest
    container_name: apisix_gateway
    restart: always
    volumes:
      - ./apisix_conf/config.yaml:/usr/local/apisix/conf/config.yaml:ro
    depends_on:
      - etcd
    ports:
      - "9080:9080"
      - "9443:9443"
      - "9180:9180"
    networks:
      apisix:

  etcd:
    image: bitnami/etcd:3.5
    container_name: apisix_etcd
    restart: always
    environment:
      ETCD_ENABLE_V2: "true"
      ALLOW_NONE_AUTHENTICATION: "yes"
      ETCD_ADVERTISE_CLIENT_URLS: "http://etcd:2379"
      ETCD_LISTEN_CLIENT_URLS: "http://0.0.0.0:2379"
    ports:
      - "2379:2379"
    networks:
      apisix:

networks:
  apisix:
    driver: bridge
```

Create the APISIX configuration file at `apisix_conf/config.yaml`:

```yaml
apisix:
  node_listen: 9080
  ssl:
    enable: true
    listen: 9443

deployment:
  admin:
    allow_admin:
      - 0.0.0.0/0
    admin_key:
      - name: "admin"
        key: edd1c9f034335f136f87ad84b625c8f1
        role: admin

  etcd:
    host:
      - "http://etcd:2379"
    prefix: "/apisix"
    timeout: 30
```

Start the gateway:

```bash
docker-compose up -d
```

Create your first route via the Admin API:

```bash
curl http://127.0.0.1:9180/apisix/admin/routes/1 \
  -H 'X-API-KEY: edd1c9f034335f136f87ad84b625c8f1' \
  -X PUT \
  -d '{
    "uri": "/api/*",
    "upstream": {
      "type": "roundrobin",
      "nodes": {
        "backend-service:8080": 1
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

### Key Features

- **Hot reloading** — Route and plugin changes take effect in milliseconds without restarting the gateway process.
- **100+ plugins** — Authentication (JWT, OAuth2, Key Auth, LDAP), rate limiting, traffic splitting, request/response rewriting, logging, observability, and serverless functions.
- **Dynamic routing** — Match on URI, host, HTTP method, headers, variables, and custom Lua expressions.
- **Protocol support** — HTTP, HTTPS, HTTP/2, HTTP/3 (QUIC), gRPC, WebSocket, and TCP/UDP.
- **Serverless functions** — Run custom Lua functions directly within the gateway process for request/response manipulation.
- **Service discovery** — Native integration with Consul, Nacos, Eureka, DNS, and Kubernetes.
- **APISIX Dashboard** — Web UI for managing routes, upstreams, SSL certificates, and consumers.
- **Active health checks** — Monitor backend health and automatically remove unhealthy nodes from the routing pool.

## Feature Comparison

| Feature | Gravitee.io | KrakenD CE | Apache APISIX |
|---|---|---|---|
| **Language** | Java | Go | Lua (OpenResty) |
| **Architecture** | Multi-component | Single binary | Gateway + etcd |
| **Management UI** | Yes (built-in) | No | Yes (separate dashboard) |
| **Developer Portal** | Yes | No | No |
| **Configuration** | Web console + REST API | JSON file | Admin API + etcd + Dashboard |
| **Hot Reload** | Yes | SIGHUP signal | Yes (millisecond-level) |
| **Database Required** | MongoDB + Elasticsearch | None | etcd |
| **API Aggregation** | Basic | Excellent | Via plugins |
| **Rate Limiting** | Yes (distributed) | Yes | Yes (multiple algorithms) |
| **JWT/OAuth2** | Yes | Yes (via plugins) | Yes (multiple plugins) |
| **gRPC Support** | Yes | Via plugins | Yes (native) |
| **WebSocket** | Yes | No | Yes |
| **GraphQL** | Yes | Via plugins | Via plugins |
| **Observability** | Elasticsearch analytics | Prometheus/Metrics endpoint | Prometheus, SkyWalking, Zipkin |
| **Multi-tenancy** | Yes (organizations) | No | Via workspaces (enterprise) |
| **Kubernetes Ingress** | Via Helm chart | Via Helm chart | Native ingress controller |
| **Community Size** | Moderate | Growing | Large (Apache project) |
| **Best For** | Full API lifecycle management | High-performance aggregation | Dynamic cloud-native routing |

## Performance and Resource Usage

Performance characteristics vary significantly between the three gateways due to their different architectures:

**KrakenD** delivers the highest raw throughput. Because it is a single stateless Go binary with no database dependency, it can process 20,000+ requests per second on a single CPU core. Memory footprint is typically 50-100 MB. This makes KrakenD ideal for high-traffic API aggregation scenarios where you need minimal latency.

**Apache APISIX** sits in the middle. Running on OpenResty, it handles 15,000-18,000 requests per second per core with a memory footprint of 100-200 MB. The etcd dependency adds a small amount of latency for configuration writes but does not affect request routing performance.

**Gravitee.io** has the highest resource requirements. The full stack (Gateway + Management API + MongoDB + Elasticsearch) needs at least 4 GB of RAM and multiple CPU cores. The gateway itself handles 8,000-12,000 requests per second. This is still sufficient for most use cases, but Gravitee trades raw performance for feature completeness.

## Choosing the Right Gateway

### Choose Gravitee.io if:

- You need a complete API management platform with developer portal, analytics, and API lifecycle tools.
- Your team includes non-technical users who need a web console to manage APIs.
- You want multi-tenancy with isolated organizations, API catalogs, and user management.
- You need built-in alerting, analytics dashboards, and subscription management.

### Choose KrakenD if:

- You need maximum performance and minimum latency for API aggregation.
- You prefer declarative, file-based configuration that lives in your version control system.
- You want a stateless architecture that scales horizontally with zero coordination overhead.
- Your team is comfortable managing configuration through JSON files and Git workflows.
- You do not need a management UI or developer portal (or you build your own).

### Choose Apache APISIX if:

- You need dynamic routing changes without any downtime or process restarts.
- You want a large plugin ecosystem with 100+ ready-to-use plugins.
- You are running in Kubernetes and want a native ingress controller.
- You need broad protocol support including HTTP/3, gRPC, and WebSocket.
- You want the backing of the Apache Software Foundation with a large contributor community.

## FAQ

### Which API gateway is easiest to set up?

KrakenD is the simplest to deploy — it requires only a single container and a JSON configuration file. No databases or external services are needed. Apache APISix requires etcd as a dependency, and Gravitee.io requires both MongoDB and Elasticsearch. If you want a quick proof-of-concept running in under 5 minutes, KrakenD is the fastest path.

### Can I run these gateways in production on a single server?

Yes, but with caveats. KrakenD runs comfortably on a single core with 512 MB of RAM. Apache APISix needs about 1 GB of RAM (including etcd). Gravitee.io requires at least 4 GB because it runs MongoDB, Elasticsearch, and multiple Java processes. For production workloads, all three benefit from horizontal scaling behind a load balancer.

### Do these gateways support mutual TLS (mTLS)?

Apache APISix has native mTLS support through its SSL plugin. Gravitee.io supports mTLS for both incoming and outgoing connections. KrakenD Community Edition does not include built-in mTLS — you would need to terminate mTLS at a reverse proxy (like NGINX or Caddy) in front of KrakenD, or use the Enterprise Edition.

### How do I migrate from one gateway to another?

Migration depends on your current configuration complexity. For simple routing rules, you can recreate routes in the target gateway within a few hours. For complex plugin chains (authentication, rate limiting, transformation), expect 1-2 weeks of work. The file-based configuration of KrakenD and the Admin API of APISix make programmatic migration scripts feasible. Gravitee's web console means you would need to recreate configurations manually or use their REST API.

### Which gateway has the best Kubernetes support?

Apache APISix has a dedicated Kubernetes Ingress Controller (`apisix-ingress-controller`) that is actively maintained and used in production by many organizations. Gravitee provides a Helm chart for Kubernetes deployment but does not have a native ingress controller. KrakenD offers a Helm chart and can be configured as a sidecar or deployment, but it requires manual configuration of Kubernetes Ingress resources to route traffic to it.

### Can these gateways handle WebSocket and Server-Sent Events (SSE)?

Apache APISix supports both WebSocket and SSE natively. Gravitee.io supports WebSocket connections through its gateway component. KrakenD Community Edition does not support WebSocket or long-lived connections because of its stateless, request-response architecture — each request is processed independently without connection state.

## Related Reading

For readers exploring the broader API gateway landscape, our [APISix vs Kong vs Tyk guide](../self-hosted-api-gateway-apisix-kong-tyk-guide/) covers three additional enterprise-grade options with detailed Docker setups. If you are concerned about API abuse, our [rate limiting and API throttling guide](../self-hosted-rate-limiting-api-throttling-nginx-traefik-envoy-kong-2026/) compares rate limiting strategies across multiple gateway and proxy solutions. For load balancing at the network layer, our [HAProxy vs Envoy vs NGINX guide](../haproxy-vs-envoy-vs-nginx-load-balancer-guide/) covers the infrastructure that sits in front of your API gateway.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Gravitee vs KrakenD vs Apache APISix: Best Self-Hosted API Gateway 2026",
  "description": "Compare Gravitee.io, KrakenD, and Apache APISix for self-hosted API gateway deployment. Full Docker setups, feature comparison, configuration examples, and performance analysis for 2026.",
  "datePublished": "2026-04-23",
  "dateModified": "2026-04-23",
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
