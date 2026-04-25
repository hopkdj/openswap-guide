---
title: "GraphQL Mesh vs WunderGraph Cosmo vs Apollo Router: Self-Hosted GraphQL Gateway Guide 2026"
date: 2026-04-25
tags: ["comparison", "guide", "self-hosted", "graphql", "api-gateway", "federation"]
draft: false
description: "Compare the top three self-hosted GraphQL gateway solutions — GraphQL Mesh, WunderGraph Cosmo, and Apollo Router — with Docker deployment guides, feature comparisons, and production-ready configurations."
---

As organizations adopt GraphQL across multiple services, a critical question emerges: how do you unify disparate APIs into a single, coherent GraphQL endpoint? Whether you need to federate microservice subgraphs, compose REST and gRPC backends into GraphQL, or build a full self-hosted GraphQL platform with analytics and observability, the gateway layer is your most important infrastructure decision.

In this guide, we compare the three leading self-hosted GraphQL gateway solutions: **GraphQL Mesh**, **WunderGraph Cosmo**, and **Apollo Router**. Each takes a fundamentally different approach to the problem, and the right choice depends on your architecture, team size, and existing stack.

For related reading, check out our [GraphQL API engines comparison](../hasura-vs-directus-vs-postgraphile-self-hosted-graphql-api-engines-2026/) for tools that generate GraphQL from databases, or our [API gateway comparison](../gravitee-vs-krakend-vs-apisix-self-hosted-api-gateway-comparison-2026/) for traditional REST API gateways.

## Why Self-Host a GraphQL Gateway?

Before diving into the tools, let's clarify why you'd want to self-host a GraphQL gateway rather than use a managed service like Apollo GraphOS:

- **Data sovereignty**: GraphQL schemas expose your entire data model. Keeping the gateway in your own infrastructure means no third party sees your query patterns or schema structure.
- **Cost control**: Managed GraphQL platforms charge per query or per seat. At scale, self-hosting can reduce costs by 60–80%.
- **Custom integrations**: Self-hosted gateways let you add custom middleware — rate limiting, request logging, coprocessor hooks, auth plugins — without vendor lock-in.
- **Compliance requirements**: Healthcare, finance, and government organizations often cannot route API traffic through external SaaS platforms.

The GraphQL gateway sits between your clients and your backend services. It handles schema composition, query planning, request routing, response merging, and often cross-cutting concerns like caching, authentication, and monitoring.

## What Is GraphQL Federation?

GraphQL Federation (also called Federation v2) is an architecture where multiple GraphQL services (called "subgraphs") each own a portion of a larger schema. The gateway — sometimes called the "supergraph router" — composes these subgraphs into a unified schema and routes incoming queries to the right subgraph(s), then merges the results.

Federation solves a real problem: as your organization grows, a single monolithic GraphQL server becomes impossible to maintain. Different teams own different domains (users, orders, products, payments). Federation lets each team deploy its own GraphQL service while presenting a single unified API to frontend clients.

There are two main approaches to building a GraphQL gateway:

1. **Schema composition from non-GraphQL sources** — tools like GraphQL Mesh can build a unified GraphQL schema from REST APIs, OpenAPI specs, gRPC services, SOAP endpoints, and databases.
2. **Federation of existing GraphQL subgraphs** — tools like Apollo Router and Cosmo Router compose multiple GraphQL services that already use the Federation spec into a supergraph.

The three tools we're comparing span both categories, and some overlap.

## GraphQL Mesh: The Universal API Composer

**GraphQL Mesh** (by The Guild) is an open-source framework that lets you build a unified GraphQL schema from virtually any API source — REST, OpenAPI/Swagger, gRPC, SOAP, GraphQL, databases, and more. It acts as a translation layer, wrapping non-GraphQL APIs in a GraphQL schema and composing them together.

- **GitHub**: [ardatan/graphql-mesh](https://github.com/ardatan/graphql-mesh)
- **Stars**: 3,498
- **Language**: TypeScript
- **Last updated**: April 24, 2026
- **License**: MIT

### Key Features

- **Multi-source composition**: REST, OpenAPI, gRPC, SOAP, GraphQL, OData, PostgreSQL, MongoDB, and more
- **Schema stitching and federation**: Can both stitch disparate schemas and act as a Federation v2 gateway
- **TypeScript-first**: Fully typed output with automatic TypeScript code generation
- **Handler plugins**: Extensible architecture with 20+ source handlers
- **Transform plugins**: Built-in transforms for renaming, filtering, prefixing, caching, and rate limiting
- **Edge deployment**: Can run on Cloudflare Workers, Vercel Edge, and AWS Lambda

### When to Choose GraphQL Mesh

Choose GraphQL Mesh when you need to compose GraphQL from non-GraphQL sources, particularly REST APIs and OpenAPI specs. It's the strongest option when your backend services aren't yet GraphQL-native. It's also ideal for teams that want to gradually migrate to GraphQL without rewriting existing services.

### Docker Deployment

GraphQL Mesh runs as a Node.js application. Here's a minimal Docker Compose configuration:

```yaml
version: "3.8"
services:
  graphql-mesh:
    image: ghcr.io/ardatan/graphql-mesh:latest
    ports:
      - "4000:4000"
    volumes:
      - ./.meshrc.yaml:/app/.meshrc.yaml:ro
    environment:
      - NODE_ENV=production
    restart: unless-stopped
```

The `.meshrc.yaml` configuration file defines your sources and transforms:

```yaml
sources:
  - name: UsersAPI
    handler:
      openapi:
        source: ./users-openapi.json
  - name: OrdersService
    handler:
      graphql:
        endpoint: http://orders-service:4001/graphql
        method: POST
  - name: InventoryREST
    handler:
      openapi:
        source: ./inventory-swagger.json
        operationHeaders:
          Authorization: "Bearer {env.INVENTORY_TOKEN}"

serve:
  port: 4000
  playground: true

transforms:
  - namingConvention:
      mode: "convert"
      typeNames: pascalCase
      fieldNames: camelCase
```

This configuration composes three different sources — an OpenAPI-defined Users API, a GraphQL Orders service, and a REST Inventory API — into a single unified GraphQL endpoint.

## WunderGraph Cosmo: The Full GraphQL Platform

**WunderGraph Cosmo** (formerly WunderGraph) is a comprehensive open-source GraphQL Federation platform. It includes not just a router, but also a control plane with schema registry, analytics, monitoring, and a web dashboard — making it the closest self-hosted alternative to Apollo GraphOS.

- **GitHub**: [wundergraph/cosmo](https://github.com/wundergraph/cosmo)
- **Stars**: 1,203
- **Language**: TypeScript (router in Go)
- **Last updated**: April 24, 2026
- **License**: Apache 2.0

### Key Features

- **Complete platform**: Router + control plane + web dashboard + schema registry
- **Federation v2**: Full support for Apollo Federation v2 subgraph composition
- **Real-time analytics**: Query latency, error rates, usage metrics built in
- **Schema change detection**: Automatic breaking change detection and schema checks in CI/CD
- **Custom claims and authentication**: Built-in JWT validation and claim mapping
- **High performance**: Router written in Go with optimized query planning
- **Observability**: OpenTelemetry-native tracing, metrics, and logging
- **Apollo GraphOS alternative**: Drop-in replacement for managed Apollo Platform

### When to Choose Cosmo

Choose WunderGraph Cosmo when you need a full-featured GraphQL Federation platform with a web UI, schema registry, analytics, and team collaboration features — essentially when you want the Apollo GraphOS experience but self-hosted. It's the strongest option for organizations with multiple teams contributing subgraphs.

### Docker Deployment

Cosmo requires several services. Here's a production-oriented Docker Compose setup:

```yaml
version: "3.8"
services:
  postgres:
    image: postgres:15.3
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-changeme}
      POSTGRES_DB: controlplane
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  keycloak:
    image: ghcr.io/wundergraph/cosmo/keycloak:latest
    environment:
      KC_DB_URL_HOST: postgres
      KC_DB_URL_DATABASE: keycloak
      KC_DB_USERNAME: postgres
      KC_DB_PASSWORD: ${POSTGRES_PASSWORD:-changeme}
      KC_BOOTSTRAP_ADMIN_USERNAME: admin
      KC_BOOTSTRAP_ADMIN_PASSWORD: ${KEYCLOAK_PASSWORD:-changeme}
    ports:
      - "8080:8080"
    depends_on:
      - postgres
    restart: unless-stopped

  clickhouse:
    image: clickhouse/clickhouse-server:24.3
    environment:
      CLICKHOUSE_DB: cosmo
      CLICKHOUSE_USER: default
      CLICKHOUSE_PASSWORD: ${CLICKHOUSE_PASSWORD:-changeme}
    volumes:
      - clickhouse_data:/var/lib/clickhouse
    ports:
      - "8123:8123"
    restart: unless-stopped

  router:
    image: ghcr.io/wundergraph/cosmo/router:latest
    environment:
      CONTROLPLANE_URL: http://controlplane:3001
      ROUTER_REGISTRATION: "true"
      GRAPH_API_TOKEN: ${GRAPH_API_TOKEN}
    ports:
      - "3002:3002"
    depends_on:
      - controlplane
    restart: unless-stopped

  controlplane:
    image: ghcr.io/wundergraph/cosmo/controlplane:latest
    environment:
      DB_URL: postgresql://postgres:${POSTGRES_PASSWORD:-changeme}@postgres:5432/controlplane
      CLICKHOUSE_DSN: http://default:${CLICKHOUSE_PASSWORD:-changeme}@clickhouse:8123/cosmo
      AUTH_REDIRECT_URI: http://localhost:8080/realms/cosmo/protocol/openid-connect/token
    ports:
      - "3001:3001"
    depends_on:
      - postgres
      - clickhouse
    restart: unless-stopped

volumes:
  postgres_data:
  clickhouse_data:
```

## Apollo Router: The Reference Implementation

**Apollo Router** (by Apollo GraphQL) is the official reference implementation for Apollo Federation v2. Written in Rust, it's designed for maximum performance and configurability as a high-throughput routing layer.

- **GitHub**: [apollographql/router](https://github.com/apollographql/router)
- **Stars**: 957
- **Language**: Rust
- **Last updated**: April 25, 2026
- **License**: Elastic License 2.0

### Key Features

- **Rust performance**: Built for low latency and high throughput, leveraging Rust's async runtime
- **Federation v2 native**: First-class support for Federation v2 directives, @link, and entity resolution
- **Coprocessor framework**: Extensible hooks for request/response modification, auth, and custom logic
- **Telemetry**: Built-in OpenTelemetry, Prometheus, and Datadog integration
- **Query planning**: Optimized query planner with cost-based execution
- **Caching**: Entity caching with Redis support
- **Preview features**: Incremental delivery (@defer, @stream), persisted queries

### Important Licensing Note

Apollo Router uses the **Elastic License 2.0 (ELv2)**, which is source-available but not OSI-approved open source. You can use it freely for internal purposes and to provide a managed service to your own customers, but you cannot offer it as a competing managed service. For fully open-source alternatives, consider GraphQL Mesh (MIT) or Cosmo (Apache 2.0).

### When to Choose Apollo Router

Choose Apollo Router when you're already invested in the Apollo ecosystem (Apollo Client, Apollo Studio, subgraph libraries) and want the reference implementation with the strongest Federation v2 support. The Rust runtime also makes it a strong choice for high-throughput scenarios where every millisecond matters.

### Docker Deployment

Apollo Router runs as a single binary. Here's a production Docker Compose configuration:

```yaml
version: "3.8"
services:
  router:
    image: ghcr.io/apollographql/router:v2.0
    ports:
      - "4000:4000"
    volumes:
      - ./router.yaml:/dist/router.yaml:ro
      - ./supergraph.graphql:/dist/supergraph.graphql:ro
    environment:
      - APOLLO_ROUTER_CONFIG_PATH=/dist/router.yaml
      - APOLLO_ROUTER_SUPERGRAPH_PATH=/dist/supergraph.graphql
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  redis_data:
```

The `router.yaml` configuration:

```yaml
supergraph:
  listen: 0.0.0.0:4000
  introspection: true
  preview_graphql_validation: true

cors:
  origins:
    - https://myapp.example.com
  methods:
    - GET
    - POST
    - OPTIONS

telemetry:
  exporters:
    tracing:
      common:
        service_name: "apollo-router"
        resource:
          attributes:
            environment: "production"
      otlp:
        enabled: true
        endpoint: http://jaeger:4317

coprocessor:
  url: http://auth-service:8080/hooks
  supergraph:
    request:
      headers: true
      context: true

include_subgraph_errors:
  all: true
```

And the supergraph is built using `rover supergraph compose`:

```bash
rover supergraph compose --config supergraph.yaml > supergraph.graphql
```

Where `supergraph.yaml` references your subgraphs:

```yaml
federation_version: 2
subgraphs:
  users:
    routing_url: http://users-service:4001/graphql
    schema:
      file: ./subgraphs/users.graphql
  products:
    routing_url: http://products-service:4002/graphql
    schema:
      file: ./subgraphs/products.graphql
  orders:
    routing_url: http://orders-service:4003/graphql
    schema:
      file: ./subgraphs/orders.graphql
```

## Feature Comparison

| Feature | GraphQL Mesh | WunderGraph Cosmo | Apollo Router |
|---|---|---|---|
| **Primary focus** | Multi-source API composition | Full Federation platform | Federation v2 router |
| **Language** | TypeScript | Go (router) + TypeScript (platform) | Rust |
| **License** | MIT | Apache 2.0 | Elastic License 2.0 |
| **Stars** | 3,498 | 1,203 | 957 |
| **REST/OpenAPI sources** | ✅ Native | ❌ Subgraphs only | ❌ Subgraphs only |
| **gRPC sources** | ✅ Native | ❌ Subgraphs only | ❌ Subgraphs only |
| **Federation v2** | ✅ Yes | ✅ Yes | ✅ Reference impl |
| **Web dashboard** | ❌ CLI only | ✅ Full platform | ❌ (Apollo Studio) |
| **Schema registry** | ❌ | ✅ Built-in | ❌ (Apollo Studio) |
| **Analytics** | ❌ | ✅ Built-in | ❌ (via telemetry export) |
| **Redis caching** | ✅ Plugin | ✅ Built-in | ✅ Built-in |
| **OpenTelemetry** | ✅ Plugin | ✅ Native | ✅ Native |
| **Coprocessor hooks** | ✅ Transform API | ✅ Webhook hooks | ✅ Coprocessor SDK |
| **Edge deployment** | ✅ CF Workers | ❌ | ❌ |
| **Query planner** | Basic | Advanced | Cost-based optimizer |
| **Incremental delivery** | ❌ | ❌ | ✅ @defer/@stream |

## Performance Considerations

The choice of runtime language matters for latency-sensitive deployments:

- **Apollo Router (Rust)**: Typically achieves sub-5ms p99 latency for simple queries due to Rust's zero-cost abstractions and tokio async runtime. The query planner uses cost-based optimization to minimize subgraph fan-out.
- **Cosmo Router (Go)**: Go's goroutine model provides excellent concurrency for high-throughput scenarios. Benchmarks show comparable p50 latency to Apollo Router with slightly higher p99 under extreme load.
- **GraphQL Mesh (TypeScript/Node.js)**: Higher baseline latency due to JavaScript runtime overhead, but the gap narrows significantly when the bottleneck is external API calls (which is the common case for mesh compositions). For edge deployment on Cloudflare Workers, Mesh has unique advantages the others can't match.

## Choosing the Right GraphQL Gateway

The decision tree is straightforward:

1. **Do you need to compose GraphQL from REST, gRPC, or OpenAPI sources?** → **GraphQL Mesh** is the only choice. It's the universal adapter for APIs.

2. **Do you need a complete self-hosted platform with dashboard, schema registry, and analytics?** → **WunderGraph Cosmo** is the closest self-hosted alternative to Apollo GraphOS.

3. **Are you already in the Apollo ecosystem and need maximum Federation v2 compatibility?** → **Apollo Router** is the reference implementation with the most mature Federation support.

4. **Do you need fully open-source licensing?** → GraphQL Mesh (MIT) and Cosmo (Apache 2.0) are OSI-approved. Apollo Router's ELv2 license restricts competitive use.

5. **Do you need edge deployment?** → Only GraphQL Mesh supports Cloudflare Workers and similar edge runtimes.

Many organizations end up combining tools: using GraphQL Mesh to wrap legacy REST services into GraphQL subgraphs, then feeding those subgraphs into Cosmo or Apollo Router for federation.

## FAQ

### What is the difference between GraphQL Mesh and Apollo Router?

GraphQL Mesh composes GraphQL schemas from non-GraphQL sources like REST APIs, OpenAPI specs, gRPC services, and databases. Apollo Router is a Federation v2 gateway that composes existing GraphQL subgraphs into a supergraph. They solve different problems — Mesh is an API translator, while the Router is a Federation orchestrator. However, Mesh can also act as a Federation gateway, so there is some overlap.

### Is Apollo Router truly open source?

Apollo Router is licensed under the Elastic License 2.0 (ELv2), which is source-available but not OSI-approved open source. You can use it freely internally and to serve your own customers, but you cannot offer it as a competing managed service. If you need a fully open-source license, choose GraphQL Mesh (MIT) or WunderGraph Cosmo (Apache 2.0).

### Can I use GraphQL Mesh with Apollo Federation?

Yes. GraphQL Mesh supports Federation v2 and can act as both a subgraph and a supergraph gateway. You can use Mesh to compose your schema from various sources and then federate that composed schema alongside other Federation subgraphs managed by Apollo Router or Cosmo.

### How does WunderGraph Cosmo compare to Apollo GraphOS?

Cosmo is designed as a self-hosted alternative to Apollo GraphOS. It provides a schema registry, analytics dashboard, schema change detection, team management, and CI/CD integrations — all the features of GraphOS but running on your own infrastructure. The router component is written in Go for performance, while the control plane is TypeScript.

### Can I run these GraphQL gateways behind a reverse proxy?

Yes. All three gateways expose standard HTTP endpoints and work seamlessly behind NGINX, Traefik, Caddy, or any other reverse proxy. You should configure your proxy to handle TLS termination, gzip/Brotli compression, and optionally rate limiting. See our [rate limiting guide](../self-hosted-rate-limiting-api-throttling-nginx-traefik-envoy-kong-2026/) for details on protecting your gateway from abuse.

### What is the overhead of adding a GraphQL gateway?

For simple pass-through queries, expect 2–10ms of additional latency depending on the runtime. The gateway's query planner can actually reduce total latency compared to naive client-side N+1 queries by batching and parallelizing subgraph requests. The real performance benefit comes from query planning optimization and response caching, not from the gateway being a "fast proxy."

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "GraphQL Mesh vs WunderGraph Cosmo vs Apollo Router: Self-Hosted GraphQL Gateway Guide 2026",
  "description": "Compare the top three self-hosted GraphQL gateway solutions — GraphQL Mesh, WunderGraph Cosmo, and Apollo Router — with Docker deployment guides, feature comparisons, and production-ready configurations.",
  "datePublished": "2026-04-25",
  "dateModified": "2026-04-25",
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
