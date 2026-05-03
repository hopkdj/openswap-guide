---
title: "Self-Hosted API Composition: GraphQL Federation vs API Mesh vs Schema Stitching 2026"
date: 2026-05-03T16:00:00+00:00
tags: ["api", "graphql", "microservices", "self-hosted", "api-gateway", "developer-tools", "federation"]
draft: false
---

In microservices architectures, each service typically exposes its own API. As the number of services grows, clients face a growing problem: they need to make requests to multiple services, aggregate the responses, and handle failures across service boundaries. This leads to the "N+1 API call problem" where a single user action requires dozens of backend requests.

API composition solves this by creating a unified API layer that sits between clients and backend services. Instead of clients calling multiple services directly, they make a single request to the composition layer, which aggregates, transforms, and returns the data. This pattern is implemented through **API federation**, **schema stitching**, and **API mesh** architectures.

In this guide, we compare the leading self-hosted API composition platforms: **Apollo Federation** (GraphQL subgraph federation), **GraphQL Mesh** (by The Guild), and **Hasura Remote Schemas** (data federation). We'll cover architecture, configuration, Docker deployment, and help you choose the right approach for your microservices.

## Why API Composition Matters

Without a composition layer, a typical microservices application looks like this:

```
Client → [UserService] + [OrderService] + [ProductService] + [PaymentService]
```

The client must know about every service endpoint, handle authentication for each, and manage partial failures. With API composition:

```
Client → [API Composition Layer] → [UserService] + [OrderService] + [ProductService] + [PaymentService]
```

The client makes one request to the composition layer, which handles service discovery, authentication, data aggregation, and error handling.

## Comparison Overview

| Feature | Apollo Federation | GraphQL Mesh | Hasura Remote Schemas |
|---------|-------------------|--------------|----------------------|
| Primary Approach | Subgraph federation | API transformation mesh | Remote schema stitching |
| Protocol | GraphQL only | GraphQL + REST + gRPC + more | GraphQL + REST |
| Self-Hosted Router | Apollo Router (Rust) | GraphQL Mesh CLI | Hasura GraphQL Engine |
| GitHub Stars (Router) | 3,100+ (router) | 3,800+ (mesh) | 31,000+ (engine) |
| Schema Composition | Server-side (at router) | Build-time or runtime | Runtime (Hasura Engine) |
| DataSource Support | GraphQL subgraphs | REST, GraphQL, gRPC, OpenAPI, databases | PostgreSQL, REST, GraphQL |
| Caching | Built-in (APQ, CDN) | Built-in (DataLoader) | Built-in (query cache) |
| Authorization | Subgraph-level policies | Transform-level policies | Row/column-level permissions |
| Performance | Compiled query plans | Runtime transformation | Runtime query planning |
| License | ELv2 (Elastic License) | MIT | Apache 2.0 |

## Apollo Federation

Apollo Federation is the industry-standard approach to GraphQL composition. It lets you split a large GraphQL schema into independent **subgraphs** — each owned by a different team or service — and compose them into a unified **supergraph** at the router level.

**Key features:**
- Decentralized schema ownership — each team owns its subgraph
- Server-side composition at the router (not build-time)
- Query plan optimization across subgraphs
- Built-in caching with Automatic Persisted Queries (APQ)
- Subgraph-level authorization policies
- Federation 2.0 supports entity references across subgraphs

### Apollo Router Docker Compose Deployment

```yaml
# docker-compose-apollo.yaml
services:
  router:
    image: ghcr.io/apollographql/router:v1.45.0
    ports:
      - "4000:4000"
    volumes:
      - ./supergraph.graphql:/dist/supergraph.graphql:ro
      - ./router.yaml:/dist/router.yaml:ro
    environment:
      - APOLLO_ROUTER_SUPERGRAPH_PATH=/dist/supergraph.graphql
      - APOLLO_ROUTER_CONFIG_PATH=/dist/router.yaml
      - APOLLO_KEY=${APOLLO_KEY:-dev-key}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4000/.well-known/apollo/server-health"]
      interval: 10s
      timeout: 5s
      retries: 3

  subgraph-users:
    image: your-registry/user-service:latest
    ports:
      - "4001:4000"
    environment:
      - DATABASE_URL=postgres://user:pass@postgres:5432/users

  subgraph-orders:
    image: your-registry/order-service:latest
    ports:
      - "4002:4000"
    environment:
      - DATABASE_URL=postgres://user:pass@postgres:5432/orders

  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

```yaml
# router.yaml
supergraph:
  listen: 0.0.0.0:4000

health_check:
  listen: 0.0.0.0:8088
  path: /health

# Subgraph endpoints
subgraphs:
  users:
    routing_url: http://subgraph-users:4000/graphql
    schema:
      subgraph_url: http://subgraph-users:4000/graphql
  orders:
    routing_url: http://subgraph-orders:4000/graphql
    schema:
      subgraph_url: http://subgraph-orders:4000/graphql
```

## GraphQL Mesh

GraphQL Mesh by The Guild is a flexible API composition layer that can combine virtually any data source — REST APIs, GraphQL services, gRPC endpoints, OpenAPI specs, databases, and even Kafka streams — into a single unified GraphQL schema.

**Key features:**
- Supports REST, GraphQL, gRPC, OpenAPI, SOAP, databases, and more as sources
- Build-time schema composition (generates a single GraphQL schema)
- Powerful transforms: renaming, filtering, rate limiting, caching, custom resolvers
- SDK generation for TypeScript, React, and other languages
- Works as a standalone server or embedded library
- No vendor lock-in — outputs a standard GraphQL schema

### GraphQL Mesh Docker Compose Deployment

```yaml
# docker-compose-mesh.yaml
services:
  mesh:
    image: ghcr.io/graphql-mesh/graphql-mesh:latest
    ports:
      - "4000:4000"
    volumes:
      - .meshrc.yaml:/app/.meshrc.yaml:ro
    command: ["yarn", "graphql-mesh", "serve", "--dir", "/app"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4000/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  # REST API source
  rest-api:
    image: your-registry/rest-service:latest
    ports:
      - "3001:3000"

  # GraphQL subgraph source
  graphql-api:
    image: your-registry/graphql-service:latest
    ports:
      - "4001:4000"
```

```yaml
# .meshrc.yaml
sources:
  - name: UsersREST
    handler:
      openapi:
        source: http://rest-api:3000/openapi.json
        operationHeaders:
          Authorization: "Bearer {context.headers.authorization}"

  - name: OrdersGraphQL
    handler:
      graphql:
        endpoint: http://graphql-api:4000/graphql
        operationHeaders:
          Authorization: "Bearer {context.headers.authorization}"

serve:
  port: 4000
  playground: true

transforms:
  - namingConvention:
      includeSources:
        - UsersREST
      mode: wrap

cache:
  local:
    ttl: 60
```

## Hasura Remote Schemas

Hasura's approach to API composition centers on its GraphQL Engine, which auto-generates a GraphQL API from PostgreSQL (and other databases) and allows you to **stitch** remote GraphQL schemas into the unified schema. This lets you combine database-driven queries with custom business logic exposed via remote GraphQL services.

**Key features:**
- Auto-generated GraphQL API from PostgreSQL, SQL Server, BigQuery, and more
- Remote schema stitching — merge external GraphQL APIs into the unified schema
- Row-level and column-level authorization via Hasura permissions
- Event triggers and webhook subscriptions
- Built-in query caching and query plan optimization
- Real-time subscriptions with PostgreSQL notify/listen

### Hasura Docker Compose Deployment

```yaml
# docker-compose-hasura.yaml
services:
  hasura:
    image: hasura/graphql-engine:v2.39.0
    ports:
      - "8080:8080"
    environment:
      HASURA_GRAPHQL_DATABASE_URL: postgres://user:pass@postgres:5432/app
      HASURA_GRAPHQL_ENABLE_CONSOLE: "true"
      HASURA_GRAPHQL_DEV_MODE: "true"
      HASURA_GRAPHQL_ADMIN_SECRET: ${HASURA_ADMIN_SECRET:-myadminsecret}
      HASURA_GRAPHQL_UNAUTHORIZED_ROLE: public
      HASURA_GRAPHQL_ENABLED_LOG_TYPES: startup, http-log, webhook-log
    depends_on:
      - postgres

  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: app
    volumes:
      - pgdata:/var/lib/postgresql/data

  # Remote GraphQL service (stitched into Hasura)
  remote-service:
    image: your-registry/remote-graphql:latest
    ports:
      - "4001:4000"

volumes:
  pgdata:
```

**Adding a remote schema (via Hasura Console or CLI):**
```bash
# Using Hasura CLI
hasura metadata apply

# Remote schema is defined in metadata:
# remote_schemas:
#   - name: orders_service
#     definition:
#       url: http://remote-service:4000/graphql
#       timeout_seconds: 10
```

## Choosing the Right Approach

### Use Apollo Federation when:
- You have multiple GraphQL services (subgraphs) owned by different teams
- You need server-side composition with runtime query planning
- You want the most mature federation ecosystem with strong tooling
- Your entire API surface is GraphQL

### Use GraphQL Mesh when:
- You need to compose heterogeneous data sources (REST + GraphQL + gRPC + databases)
- You want build-time schema generation with maximum flexibility
- You need powerful transforms (renaming, filtering, custom resolvers)
- You want to generate SDKs for frontend clients

### Use Hasura Remote Schemas when:
- Your primary data source is a relational database (PostgreSQL)
- You want auto-generated CRUD GraphQL APIs with minimal code
- You need fine-grained row/column-level authorization
- You want event triggers and real-time subscriptions built-in

## Why Self-Host API Composition?

Self-hosting your API composition layer gives you full control over query execution, caching behavior, and data routing. Managed GraphQL and API composition services can become expensive at scale — pricing is often based on query volume or number of schemas. Self-hosted solutions run on your infrastructure with predictable resource costs.

For regulated industries, keeping API composition in-house ensures that query patterns, data access logs, and schema definitions never leave your network. You also avoid vendor lock-in — your composition layer is not tied to a specific cloud provider's ecosystem.

For related API tooling, see our [API mocking guide](../self-hosted-api-mocking-testing-tools-wiremock-mockoon-mocks-server-guide-2026/) and [ingress controller comparison](../2026-04-22-traefik-vs-nginx-ingress-vs-contour-kubernetes-ingress-guide-2026/). For service discovery, check our [etcd vs Consul vs ZooKeeper guide](../etcd-vs-consul-vs-zookeeper-self-hosted-service-discovery-guide-2026.md).

## FAQ

### What is the difference between API federation and schema stitching?

API federation (like Apollo Federation) composes schemas at runtime in a router — each subgraph is queried independently and results are merged. Schema stitching (like Hasura Remote Schemas) merges multiple schemas into a single schema at configuration time, then queries are executed against the unified schema. Federation is more flexible for team ownership; stitching is simpler for monolithic composition.

### Can I combine REST APIs with GraphQL using these tools?

GraphQL Mesh is specifically designed for this — it treats REST APIs (via OpenAPI specs) as first-class sources alongside GraphQL, gRPC, and databases. Apollo Federation requires all subgraphs to be GraphQL. Hasura can stitch remote GraphQL schemas but doesn't natively consume REST APIs as sources.

### How does API composition affect latency?

Every API composition layer adds a network hop. However, well-designed composition reduces total latency by parallelizing requests to backend services and eliminating the client-side N+1 call problem. Apollo Router uses compiled query plans to minimize overhead. GraphQL Mesh adds minimal latency with its DataLoader batching. Hasura's query planner optimizes database and remote queries together.

### Do these tools support real-time data (subscriptions)?

Apollo Federation supports subscriptions across subgraphs (requires each subgraph to support them). Hasura has built-in real-time subscriptions via PostgreSQL notify/listen. GraphQL Mesh supports subscriptions if the underlying source provides them (e.g., GraphQL sources with subscription endpoints).

### Can I use these tools with existing REST microservices?

Yes, but with different effort levels. GraphQL Mesh can consume REST APIs directly via OpenAPI specs. Hasura requires you to either wrap REST services as remote GraphQL schemas or use Hasura's built-in RESTified GraphQL from databases. Apollo Federation requires converting your REST services to GraphQL subgraphs first.

### What happens if a subgraph goes down?

Apollo Router can be configured with fallback strategies — return partial data, cached data, or error responses for the affected subgraph. GraphQL Mesh handles source failures based on its configuration (skip, error, or fallback). Hasura returns errors for the remote schema portion while still serving data from the database portion of the query.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted API Composition: GraphQL Federation vs API Mesh vs Schema Stitching 2026",
  "description": "Compare Apollo Federation, GraphQL Mesh, and Hasura Remote Schemas for self-hosted API composition. Docker Compose deployment configs and architecture guide.",
  "datePublished": "2026-05-03",
  "dateModified": "2026-05-03",
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
