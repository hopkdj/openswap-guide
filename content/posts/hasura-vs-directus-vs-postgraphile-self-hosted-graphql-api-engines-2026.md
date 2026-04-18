---
title: "Hasura vs Directus vs PostGraphile: Self-Hosted GraphQL API Engines 2026"
date: 2026-04-18
tags: ["comparison", "guide", "self-hosted", "graphql", "api", "backend", "database"]
draft: false
description: "Compare three self-hosted GraphQL API engines — Hasura, Directus, and PostGraphile. Learn which tool best fits your project for instant database APIs, real-time subscriptions, and headless CMS capabilities."
---

Building a GraphQL API from scratch requires designing schemas, writing resolvers, implementing authentication, and handling real-time subscriptions. Self-hosted GraphQL API engines eliminate most of this boilerplate by automatically generating APIs directly from your database schema. This guide compares the three leading options: Hasura, Directus, and PostGraphile.

## Why Self-Host Your GraphQL API Engine

Managed GraphQL services lock you into proprietary pricing models, vendor-specific APIs, and opaque data governance. Self-hosting gives you:

- **Full data sovereignty** — your database stays on your infrastructure, behind your firewall
- **Predictable costs** — no per-query or per-seat pricing spikes as your application scales
- **Custom integrations** — wire up custom business logic, webhooks, and data connectors
- **Regulatory compliance** — keep sensitive data in your jurisdiction for GDPR, HIPAA, or SOC 2 requirements
- **Offline resilience** — your API doesn't disappear if a third-party service has an outage

If you are evaluating backend platforms more broadly, our [Appwrite vs Supabase vs Pocketbase comparison](../appwrite-vs-supabase-vs-pocketbase-self-hosted-firebase-alternatives-2026/) covers Firebase alternatives that also include GraphQL capabilities.

## Hasura: Instant Realtime GraphQL APIs

Hasura ([hasura/graphql-engine](https://github.com/hasura/graphql-engine), 31,950 stars) is the most widely adopted open-source GraphQL engine. It connects to PostgreSQL, MySQL, SQL Server, Oracle, Snowflake, and MariaDB, generating a fully-featured GraphQL API in seconds.

**Key features:**

- **Real-time subscriptions** — native GraphQL subscriptions powered by PostgreSQL's LISTEN/NOTIFY mechanism, ideal for live dashboards, chat applications, and collaborative tools
- **Fine-grained access control** — role-based permissions at the row and column level, integrated with JWT, webhooks, and OIDC
- **Remote schemas** — stitch existing REST APIs and microservices into your unified GraphQL graph
- **Event triggers** — automatically invoke webhooks or serverless functions on database changes
- **Data connectors** — query non-SQL data sources (MongoDB, Elasticsearch, REST APIs) alongside your relational data
- **Apollo Federation support** — compose Hasura into a federated supergraph with other GraphQL services

**Best for:** Teams that need real-time data, multi-database support, and enterprise-grade access control without writing boilerplate resolver code.

### Quick Start with Docker Compose

Hasura ships with an official Docker Compose configuration. Here is a production-ready setup:

```yaml
services:
  postgres:
    image: postgres:15
    restart: always
    volumes:
      - db_data:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD: postgrespassword

  graphql-engine:
    image: hasura/graphql-engine:v2.48.16
    ports:
      - "8080:8080"
    restart: always
    environment:
      HASURA_GRAPHQL_METADATA_DATABASE_URL: postgres://postgres:postgrespassword@postgres:5432/postgres
      PG_DATABASE_URL: postgres://postgres:postgrespassword@postgres:5432/postgres
      HASURA_GRAPHQL_ENABLE_CONSOLE: "true"
      HASURA_GRAPHQL_DEV_MODE: "true"
      HASURA_GRAPHQL_ENABLED_LOG_TYPES: startup,http-log,webhook-log,websocket-log,query-log
      HASURA_GRAPHQL_ADMIN_SECRET: your-admin-secret-key
    depends_on:
      - postgres

volumes:
  db_data:
```

Start the stack with `docker compose up -d` and open `http://localhost:8080` to access the built-in GraphQL console.

### Example GraphQL Queries

Once connected to your database, Hasura generates queries automatically. Here is what a typical query looks like:

```graphql
query GetActiveUsers {
  users(where: { status: { _eq: "active" } }, order_by: { created_at: desc }) {
    id
    name
    email
    posts(order_by: { published_at: desc }, limit: 5) {
      title
      published_at
    }
  }
}
```

Real-time subscriptions use the same syntax with `subscription` instead of `query`:

```graphql
subscription LiveOrderUpdates {
  orders(where: { status: { _eq: "pending" } }) {
    id
    total
    status
    updated_at
  }
}
```

## PostGraphile: PostgreSQL-Native GraphQL with Deep Customization

PostGraphile ([graphile/postgraphile](https://github.com/graphile/postgraphile), 12,917 stars) is a PostgreSQL-to-GraphQL API engine that infers your schema from database tables, views, functions, and comments. Unlike Hasura, it is exclusively PostgreSQL-focused, which allows for deeper database-level integration.

**Key features:**

- **Schema inference from PostgreSQL metadata** — uses table descriptions, column comments, and constraints to build a rich, self-documenting GraphQL schema
- **Extensible plugin system** — write custom plugins to add fields, types, or entirely new query patterns
- **Grafast execution engine** — the newer Grafast runtime optimizes query planning, reducing N+1 query problems without requiring DataLoader boilerplate
- **Computed columns** — expose PostgreSQL functions as computed fields on GraphQL types
- **Row-level security integration** — respects PostgreSQL RLS policies for fine-grained access control
- **Lightweight single-process deployment** — no metadata database or sidecar agents required

**Best for:** PostgreSQL-heavy teams that want a lightweight, deeply customizable GraphQL API with minimal infrastructure overhead.

### Running PostGraphile with Docker

PostGraphile runs as a single container connected to your PostgreSQL instance:

```bash
docker run --rm -it \
  -p 5000:5000 \
  ghcr.io/graphile/postgraphile:latest \
  --connection postgres://user:password@host.docker.internal:5432/mydb \
  --schema public \
  --watch \
  --enhance-graphiql \
  --simple-collections both
```

For production, run it behind a reverse proxy with admin secret protection:

```bash
docker run -d \
  --name postgraphile \
  -p 5000:5000 \
  --restart unless-stopped \
  -e DATABASE_URL=postgres://user:password@db:5432/mydb \
  ghcr.io/graphile/postgraphile:latest \
  --connection $DATABASE_URL \
  --schema public \
  --disable-query-log \
  --retry-on-init-fail
```

The `--simple-collections both` flag generates both connection-based ( Relay-style pagination) and simple array-based collections, giving you flexibility in how clients query your data.

### Custom Computed Column Example

PostGraphile's standout feature is computed columns. Define a PostgreSQL function and it becomes a GraphQL field automatically:

```sql
CREATE FUNCTION user_full_name(users_row users)
RETURNS TEXT AS $$
  SELECT users_row.first_name || ' ' || users_row.last_name;
$$ LANGUAGE sql STABLE;
```

After running this migration, `fullName` appears as a computed field on the `User` type in your GraphQL schema.

## Directus: Full-Stack Data Platform with GraphQL

Directus ([directus/directus](https://github.com/directus/directus), 34,823 stars) is more than a GraphQL engine — it is a complete headless CMS and data platform. It wraps any SQL database (PostgreSQL, MySQL, SQLite, MariaDB, MS SQL, Oracle, CockroachDB) with both REST and GraphQL APIs, plus a visual admin panel, file management, and user authentication.

**Key features:**

- **Dual API support** — both REST and GraphQL APIs generated from the same data model
- **Visual admin interface** — no-code content management, user role configuration, and data browsing
- **File and asset management** — built-in image transformations, file storage (local, S3, GCS, Azure), and metadata extraction
- **Role-based access control** — granular permissions for collections, fields, and individual items
- **Webhook and flow automation** — trigger actions on data changes, schedule tasks, and orchestrate workflows
- **Multi-database support** — supports more database engines than any other tool in this comparison

**Best for:** Teams that need a complete content management and data platform with a visual admin UI, not just a raw GraphQL API layer.

For a broader headless CMS comparison, see our [Strapi vs Directus vs Ghost guide](../strapi-vs-directus-vs-ghost-headless-cms-guide/).

### Production Docker Compose

Directus requires a database, optional Redis for caching, and persistent storage for uploads:

```yaml
services:
  database:
    image: postgis/postgis:15-3.4-alpine
    volumes:
      - db_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: directus
      POSTGRES_PASSWORD: directus_password
      POSTGRES_DB: directus
    restart: unless-stopped

  directus:
    image: directus/directus:11
    ports:
      - "8055:8055"
    volumes:
      - ./uploads:/directus/uploads
      - ./extensions:/directus/extensions
    depends_on:
      - database
    environment:
      KEY: your-secret-key-min-32-chars
      SECRET: your-secret-value-min-32-chars
      DB_CLIENT: pg
      DB_HOST: database
      DB_PORT: 5432
      DB_DATABASE: directus
      DB_USER: directus
      DB_PASSWORD: directus_password
      ADMIN_EMAIL: admin@example.com
      ADMIN_PASSWORD: change-me-in-production
      CACHE_ENABLED: "true"
      CACHE_AUTO_PURGE: "true"
      GRAPHQL_COMPRESSION_ENABLED: "true"
    restart: unless-stopped

volumes:
  db_data:
```

The GraphQL endpoint is available at `http://localhost:8055/graphql` and the admin panel at `http://localhost:8055`.

### GraphQL Query Example

Directus auto-generates a GraphQL schema from your collections. Here is how you query items:

```graphql
query GetArticles {
  articles(filter: { status: { _eq: "published" } }, sort: "-date_published", limit: 10) {
    id
    title
    date_published
    author {
      first_name
      last_name
      avatar {
        id
        filename_download
      }
    }
    content
  }
}
```

## Feature Comparison

| Feature | Hasura | PostGraphile | Directus |
|---------|--------|-------------|----------|
| **Primary Database** | PostgreSQL, MySQL, SQL Server, Oracle, Snowflake | PostgreSQL only | PostgreSQL, MySQL, SQLite, MariaDB, MS SQL, Oracle, CockroachDB |
| **GraphQL API** | Yes (primary) | Yes (primary) | Yes (plus REST) |
| **Real-time Subscriptions** | Yes (native) | Limited (via plugins) | Yes (via Server-Sent Events) |
| **Admin UI** | Console (schema management) | GraphiQL (query explorer) | Full CMS admin panel |
| **Access Control** | Row/column-level, JWT, webhooks | PostgreSQL RLS, custom plugins | Role-based, field-level, UI-configured |
| **File Management** | Via remote schemas | No | Built-in with image transforms |
| **Remote Schema Stitching** | Yes | No | No |
| **Event Triggers / Webhooks** | Yes (built-in) | Via plugins | Yes (flows + webhooks) |
| **Deployment Complexity** | Medium (engine + metadata DB) | Low (single container) | Medium (app + database + storage) |
| **GitHub Stars** | 31,950 | 12,917 | 34,823 |
| **Last Updated** | April 2026 | April 2026 | April 2026 |
| **License** | Apache 2.0 (Community), Proprietary (Enterprise) | MIT | BSL 1.1 (GPL after 1 year) |
| **Best Use Case** | Real-time APIs, multi-source data | PostgreSQL-native, lightweight | Full CMS, content teams, multi-DB |

## Choosing the Right GraphQL Engine

**Choose Hasura if:**
- You need real-time subscriptions for live data applications
- You work with multiple database types or need to stitch remote APIs
- You want enterprise-grade access control with row and column permissions
- Your team values the mature ecosystem and extensive documentation

**Choose PostGraphile if:**
- Your stack is exclusively PostgreSQL
- You want the simplest possible deployment — a single container, no metadata database
- You need deep database-level customization through computed columns and custom plugins
- You prefer a lightweight tool that respects PostgreSQL conventions and RLS policies

**Choose Directus if:**
- You need a visual admin panel for non-technical users to manage content
- You want both REST and GraphQL APIs from the same data model
- You need built-in file management, image processing, and user authentication
- You work with multiple database backends and want a unified interface

For teams building API-driven architectures, pairing your GraphQL engine with a proper [API gateway like Kong or APISIX](../self-hosted-api-gateway-apisix-kong-tyk-guide/) adds rate limiting, authentication, and traffic management at the edge.

## FAQ

### Can I use Hasura with databases other than PostgreSQL?

Yes. Hasura supports PostgreSQL, MySQL, SQL Server, Oracle, Snowflake, MariaDB, MongoDB, and any data source exposed through its Data Connector framework. This is one of Hasura's main advantages over PostGraphile, which is PostgreSQL-only.

### Does Directus replace a traditional CMS like WordPress?

For headless content management, yes. Directus provides a visual admin panel, role-based access control, file management, and both REST and GraphQL APIs. However, it does not include front-end templating — you still need to build the presentation layer with your framework of choice (Next.js, Nuxt, Hugo, etc.).

### Is PostGraphile production-ready for high-traffic applications?

PostGraphile is used in production by many organizations. Its newer Grafast execution engine optimizes query planning to minimize database round-trips. For high-traffic scenarios, put PostGraphile behind a caching reverse proxy like Nginx or Caddy and enable database-level connection pooling.

### How do access control models differ between these tools?

Hasura uses a centralized permission model where you define roles and column/row-level rules in its metadata. PostGraphile delegates to PostgreSQL's built-in row-level security (RLS), keeping access logic in the database. Directus uses a UI-configured role system with field-level and item-level permissions managed through the admin panel.

### Can I migrate from one GraphQL engine to another?

Since all three tools read directly from your database, the underlying data never changes. Switching engines primarily means reconfiguring API access patterns, authentication, and permission rules. The migration effort depends on how many customizations (remote schemas, computed columns, event triggers) you have configured.

### Do these tools support GraphQL mutations and not just queries?

All three generate mutations automatically. Hasura creates insert, update, delete, and upsert mutations for every table. PostGraphile generates create, update, and delete mutations following the Relay specification. Directus generates mutations for all CRUD operations on every collection, with batch support.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Hasura vs Directus vs PostGraphile: Self-Hosted GraphQL API Engines 2026",
  "description": "Compare three self-hosted GraphQL API engines — Hasura, Directus, and PostGraphile. Learn which tool best fits your project for instant database APIs, real-time subscriptions, and headless CMS capabilities.",
  "datePublished": "2026-04-18",
  "dateModified": "2026-04-18",
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
