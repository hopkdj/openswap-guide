---
title: "Self-Hosted API Versioning Management: Kong vs APISIX vs Tyk (2026 Guide)"
date: "2026-05-21"
tags: ["api-gateway", "version-management", "kong", "apisix", "tyk", "api-versioning"]
draft: false
---

Managing multiple API versions is one of the hardest challenges for growing engineering teams. When you break backward compatibility, you need a clean migration path — and that means running v1, v2, and sometimes v3 of the same API simultaneously. Doing this without a dedicated API gateway quickly becomes a nightmare of custom middleware, routing rules, and documentation drift.

This guide compares three leading open-source API gateways — **Kong**, **APISIX**, and **Tyk** — specifically focused on their API versioning capabilities. We will cover version routing strategies, backward compatibility patterns, deprecation workflows, and provide production-ready Docker Compose configurations for each.

## Why API Versioning Matters

API versioning is not just about adding `/v1/` to your URL path. It encompasses a complete lifecycle management strategy:

- **Backward compatibility**: When you introduce breaking changes, old clients must continue working until they migrate.
- **Traffic splitting**: Gradually shift traffic from v1 to v2 using weighted routing to catch issues before full migration.
- **Deprecation policies**: Communicate sunset dates, return deprecation headers, and eventually route old versions to a dead-end.
- **Documentation synchronization**: Each API version needs its own documentation, and the gateway should serve the correct docs based on the requested version.
- **Authentication and rate limiting per version**: Newer versions may have different auth requirements or rate limits.

Without a centralized gateway, these concerns scatter across individual microservices. A dedicated API versioning layer consolidates routing, policies, and observability in one place.

For teams managing multiple APIs at scale, see our [API lifecycle management guide](../2026-04-26-self-hosted-api-lifecycle-management-kong-apisix-tyk-gravitee-krakend-guide/) for broader coverage of Kong, APISIX, and Tyk beyond versioning. We also compare these same tools as general-purpose gateways in our [API gateway management article](../2026-05-19-self-hosted-api-gateway-management-kong-tyk-gravitee-guide/).

## Quick Comparison Table

| Feature | Kong | APISIX | Tyk |
|---------|------|--------|-----|
| **Stars** | 43,419 | 16,620 | 10,723 |
| **Version Routing** | Route matching by path/header | Dynamic routing plugins | URL versioning middleware |
| **Traffic Splitting** | Weighted round-robin | Traffic split plugin | Version-specific rate limits |
| **Deprecation Headers** | Custom plugin / response transformer | serverless-functions plugin | Middleware-based |
| **Rate Limiting per Version** | Built-in (key-auth + rate-limit) | Built-in (limit-count) | Built-in (per-service quota) |
| **API Documentation** | Kong Konnect (cloud), Insomnia | APISIX Dashboard (open-source) | Tyk Dashboard (open-source UI) |
| **Configuration** | Declarative (YAML) + Admin API | Declarative (YAML) + Admin API + Dashboard | Declarative (YAML) + Dashboard |
| **Plugin Ecosystem** | 100+ plugins (open-source + enterprise) | 100+ plugins (open-source) | 50+ middleware (open-source) |
| **Language** | Lua (OpenResty) | Lua (OpenResty) | Go |
| **Hot Reload** | Yes | Yes (dynamic, no restart) | Yes |
| **Docker Compose** | Official images available | docker/compose/ directory | Official docker-compose.yml |
| **License** | Apache 2.0 | Apache 2.0 | MPL 2.0 |

## Kong: Versioning with Routes and Services

Kong models API versioning using a hierarchy: **Services** represent your upstream application, and **Routes** define how requests match to those services. For versioning, you create separate Routes (or Services) for each version.

### Docker Compose Setup

```yaml
version: "3.8"
services:
  kong:
    image: kong:3.9
    environment:
      KONG_DATABASE: "off"
      KONG_DECLARATIVE_CONFIG: /usr/local/kong/declarative/kong.yml
      KONG_PROXY_ACCESS_LOG: /dev/stdout
      KONG_ADMIN_ACCESS_LOG: /dev/stdout
      KONG_PROXY_ERROR_LOG: /dev/stderr
      KONG_ADMIN_ERROR_LOG: /dev/stderr
      KONG_ADMIN_LISTEN: "0.0.0.0:8001"
    ports:
      - "8000:8000"
      - "8443:8443"
      - "8001:8001"
    volumes:
      - ./kong.yml:/usr/local/kong/declarative/kong.yml:ro

  kong-migrations:
    image: kong:3.9
    command: kong migrations bootstrap
    environment:
      KONG_DATABASE: "off"
    depends_on:
      - kong
```

### Declarative Version Routing Configuration

```yaml
_format_version: "3.0"

services:
  - name: my-api-v1
    url: http://my-api-v1:8080
    routes:
      - name: my-api-v1-route
        paths:
          - /v1/
        strip_path: true
    plugins:
      - name: rate-limiting
        config:
          minute: 100
          policy: local

  - name: my-api-v2
    url: http://my-api-v2:8080
    routes:
      - name: my-api-v2-route
        paths:
          - /v2/
        strip_path: true
    plugins:
      - name: rate-limiting
        config:
          minute: 200
          policy: local
      - name: request-transformer
        config:
          add:
            headers:
              - X-API-Version:v2
              - Deprecation:false
```

This configuration routes `/v1/*` requests to the v1 backend and `/v2/*` to v2, each with independent rate limits. You can add a `response-transformer` plugin to inject `Sunset` and `Deprecation` headers for API version sunset policies.

### Traffic Splitting for Gradual Migration

Kong supports weighted round-robin load balancing across upstream targets:

```bash
# Add v1 and v2 targets with weights
curl -s -X POST http://localhost:8001/services/my-api/upstreams   --data name=my-api-weighted

curl -s -X POST http://localhost:8001/upstreams/my-api-weighted/targets   --data target="my-api-v1:8080" --data weight=80

curl -s -X POST http://localhost:8001/upstreams/my-api-weighted/targets   --data target="my-api-v2:8080" --data weight=20
```

This sends 80% of traffic to v1 and 20% to v2 — ideal for canary deployments during version migration.

## APISIX: Dynamic Version Routing Without Restarts

APISIX excels at API versioning because it supports **fully dynamic configuration** — every route, upstream, and plugin update takes effect immediately without restarting the gateway process. This is powered by its etcd-backed configuration store.

### Docker Compose Setup

APISIX provides an official Docker Compose configuration in its repository:

```yaml
version: "3.8"
services:
  apisix:
    image: apache/apisix:3.11.0
    ports:
      - "9080:9080"
      - "9443:9443"
      - "9180:9180"
    volumes:
      - ./apisix_conf/config.yaml:/usr/local/apisix/conf/config.yaml:ro
    depends_on:
      - etcd

  etcd:
    image: bitnami/etcd:3.5
    environment:
      ETCD_ENABLE_V2: "true"
      ALLOW_NONE_AUTHENTICATION: "yes"
      ETCD_ADVERTISE_CLIENT_URLS: "http://etcd:2379"
    ports:
      - "2379:2379"
```

### API Version Routing via Admin API

```bash
# Create upstreams for each version
curl http://localhost:9180/apisix/admin/upstreams/1 -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1" -X PUT -d '
{
  "name": "my-api-v1",
  "type": "roundrobin",
  "nodes": { "my-api-v1:8080": 1 }
}'

curl http://localhost:9180/apisix/admin/upstreams/2 -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1" -X PUT -d '
{
  "name": "my-api-v2",
  "type": "roundrobin",
  "nodes": { "my-api-v2:8080": 1 }
}'

# Create version-based routes
curl http://localhost:9180/apisix/admin/routes/1 -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1" -X PUT -d '
{
  "uri": "/v1/*",
  "upstream_id": 1,
  "plugins": {
    "limit-count": {
      "count": 100,
      "time_window": 60,
      "rejected_code": 429
    },
    "response-rewrite": {
      "headers": {
        "X-API-Version": "v1"
      }
    }
  }
}'

curl http://localhost:9180/apisix/admin/routes/2 -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1" -X PUT -d '
{
  "uri": "/v2/*",
  "upstream_id": 2,
  "plugins": {
    "limit-count": {
      "count": 200,
      "time_window": 60,
      "rejected_code": 429
    },
    "response-rewrite": {
      "headers": {
        "X-API-Version": "v2",
        "Deprecation": "false"
      }
    }
  }
}'
```

### Traffic Splitting with APISIX

APISIX provides a dedicated `traffic-split` plugin for weighted version migration:

```bash
curl http://localhost:9180/apisix/admin/routes/3 -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1" -X PUT -d '
{
  "uri": "/api/*",
  "plugins": {
    "traffic-split": {
      "rules": [
        {
          "weighted_upstreams": [
            { "upstream_id": 1, "weight": 70 },
            { "upstream_id": 2, "weight": 30 }
          ]
        }
      ]
    }
  },
  "upstream_id": 1
}'
```

This sends 70% of `/api/*` traffic to v1 and 30% to v2 — all without restarting APISIX.

## Tyk: Middleware-Based Version Management

Tyk takes a different architectural approach — it is written in Go (not Lua/OpenResty like Kong and APISIX) and uses a middleware pipeline model. Each API definition includes a versioning section that controls how versions are handled.

### Docker Compose Setup

```yaml
version: "3.8"
services:
  tyk-gateway:
    image: tykio/tyk-gateway:5.4
    ports:
      - "8080:8080"
    volumes:
      - ./tyk/tyk.conf:/opt/tyk-gateway/tyk.conf:ro
      - ./tyk/apps:/opt/tyk-gateway/apps:ro
    depends_on:
      - redis

  tyk-dashboard:
    image: tykio/tyk-dashboard:5.4
    ports:
      - "3000:3000"
    volumes:
      - ./tyk/tyk_analytics.conf:/opt/tyk-dashboard/tyk_analytics.conf:ro
    depends_on:
      - redis
      - mongo

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  mongo:
    image: mongo:7
    ports:
      - "27017:27017"
```

### Tyk API Definition with Versioning

```json
{
  "name": "My API",
  "api_id": "my-api",
  "org_id": "default",
  "use_keyless": true,
  "version_data": {
    "not_versioned": false,
    "default_version": "v2",
    "versions": {
      "v1": {
        "name": "v1",
        "expires": "2026-12-31 23:59",
        "override_target": "",
        "global_headers": {
          "X-API-Version": "v1",
          "Sunset": "Sat, 31 Dec 2026 23:59:59 GMT"
        },
        "paths": {
          "ignored": [],
          "white_list": [],
          "black_list": []
        }
      },
      "v2": {
        "name": "v2",
        "expires": "",
        "override_target": "",
        "global_headers": {
          "X-API-Version": "v2"
        }
      }
    }
  },
  "proxy": {
    "listen_path": "/my-api/",
    "target_url": "http://my-api-backend:8080",
    "strip_listen_path": true
  }
}
```

Tyk's version system supports version-specific expiration dates (`expires`), which automatically enforce deprecation policies. When a version expires, requests to that version return a configurable error response.

## Versioning Strategy Comparison

| Strategy | Kong | APISIX | Tyk |
|----------|------|--------|-----|
| **URL path versioning** | Route path matching | URI matching | Version definitions |
| **Header-based versioning** | Route header matching | Route header matching | Version header override |
| **Gradual migration** | Weighted upstreams | traffic-split plugin | Load balancing targets |
| **Sunset/Deprecation** | Response transformer plugin | response-rewrite plugin | Version expires field |
| **Per-version rate limits** | Plugin per route | Plugin per route | Quota per version |
| **Per-version auth** | Plugin per route | Plugin per route | Auth per version def |
| **Admin API for updates** | Yes | Yes (dynamic, no restart) | Yes |
| **Dashboard UI** | Kong Konnect (paid) | APISIX Dashboard (open-source) | Tyk Dashboard (open-source) |

## Choosing the Right API Versioning Gateway

**Choose Kong if** you need a mature, production-proven gateway with the largest plugin ecosystem. Kong's declarative configuration makes version management reproducible via GitOps. It is ideal for teams already invested in the Kong ecosystem or those running Kong Enterprise.

**Choose APISIX if** you need dynamic configuration without restarts. APISIX is the best choice for high-velocity teams that deploy new API versions frequently and cannot afford gateway restarts. The `traffic-split` plugin provides sophisticated gradual migration capabilities out of the box.

**Choose Tyk if** you prefer a Go-based architecture with a built-in versioning model. Tyk's `version_data` structure is the most purpose-built for API versioning among the three — with native support for version expiration dates, default versions, and per-version policies. The open-source dashboard provides version management UI without extra cost.

## Why Self-Host Your API Gateway?

Self-hosting an API gateway gives you complete control over your versioning infrastructure. When you manage version routing on-premises or in your own cloud, you avoid vendor-imposed rate limits on API calls, maintain full audit logs for compliance, and can customize version deprecation policies to match your organization's SLA requirements.

Self-hosted gateways also eliminate the risk of third-party API gateway outages affecting your version migration timelines. You control the upgrade schedule, plugin selection, and can implement custom versioning strategies that cloud gateways may not support — such as header-based version routing combined with traffic splitting and deprecation headers.

For related reading on API infrastructure, see our [complete API gateway comparison](../self-hosted-api-gateway-apisix-kong-tyk-guide/) and [API gateway observability guide](../2026-05-07-self-hosted-api-gateway-observability-kong-vitals-vs-tyk-pulsar-guide/).

## FAQ

### Q: What is the best API versioning strategy — URL path, headers, or query parameters?

URL path versioning (e.g., `/v1/resource`, `/v2/resource`) is the most widely adopted and easiest to debug. Header-based versioning (e.g., `Accept: application/vnd.myapi.v2+json`) is cleaner but harder for clients to implement. Query parameter versioning (`?version=2`) is generally discouraged because parameters can be cached independently. All three gateways support URL path versioning natively; APISIX and Kong additionally support header-based matching.

### Q: How do I gracefully deprecate an API version?

The standard approach is a three-phase deprecation: (1) Add `Deprecation: true` and `Sunset` response headers to the old version. (2) Monitor traffic to the old version using gateway analytics. (3) When traffic drops below a threshold (e.g., 1% of total), return HTTP 410 Gone or redirect to the new version. Tyk's `expires` field automates phase 3. Kong and APISIX require a scheduled plugin update or route removal.

### Q: Can I run multiple API versions on the same backend?

Yes. You do not need separate deployments for each version. A single backend can serve multiple versions, with the gateway handling routing. This is useful during migration when v1 and v2 are served by the same codebase using feature flags or version-specific handlers. The gateway routes requests and applies version-specific rate limits and transformations.

### Q: How do I test API version changes before going live?

Use the gateway's traffic splitting capability to route a small percentage of live traffic (1-5%) to the new version while keeping 95-99% on the stable version. Monitor error rates, latency, and business metrics. If the new version performs well, gradually increase the weight. All three gateways support this pattern — Kong via weighted upstreams, APISIX via the traffic-split plugin, and Tyk via load balancing target weights.

### Q: Which gateway has the best API versioning documentation features?

APISIX includes the open-source APISIX Dashboard, which provides a web UI for managing routes, upstreams, and version configurations. Tyk Dashboard also provides version management visualization. Kong requires Kong Konnect (paid) for its GUI, though the open-source Kong Manager provides basic route management. For API documentation portals, consider pairing any of these gateways with a dedicated documentation tool.

### Q: Is APISIX really fully dynamic — no restart needed for any config change?

Yes. APISIX stores all configuration in etcd and uses a pub-sub mechanism to propagate changes to gateway instances. Route additions, plugin updates, and upstream changes take effect within milliseconds without any process restart. This is a significant operational advantage over Kong, which requires a reload (brief, but not instant) when using declarative configuration files.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted API Versioning Management: Kong vs APISIX vs Tyk (2026 Guide)",
  "description": "Compare Kong, APISIX, and Tyk for self-hosted API versioning management. Covers version routing, traffic splitting, deprecation policies, and Docker Compose configs.",
  "datePublished": "2026-05-21",
  "dateModified": "2026-05-21",
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
