---
title: "SpiceDB vs OpenFGA vs Permify: Self-Hosted Authorization Engines 2026"
date: 2026-04-18
tags: ["comparison", "guide", "self-hosted", "authorization", "security", "permissions"]
draft: false
description: "Compare SpiceDB, OpenFGA, and Permify — three Zanzibar-inspired open-source authorization engines for fine-grained, self-hosted permissions. Includes Docker setup, ReBAC modeling, and performance benchmarks."
---

When you move beyond simple role-based access control (RBAC), permissions get complicated fast. "Can user X view document Y, but only if they're in the same organization, haven't been blocked by user Z, and the document hasn't expired?" Hard-coding that logic into your application is a recipe for bugs, security holes, and endless refactoring.

Enter the Zanzibar model — Google's 2019 paper describing a global, consistent authorization system that handles billions of permission checks per second. Three open-source projects have brought this architecture to the self-hosted world: **SpiceDB**, **OpenFGA**, and **Permify**. All three let you define fine-grained permissions as data, query them at scale, and keep them decoupled from your application code.

This guide compares all three, covers how to deploy each with [docker](https://www.docker.com/), and shows you how to model real-world authorization schemas.

## Why Self-Host Your Authorization Engine?

Cloud-hosted authorization services like Auth0 FGA or Oso Cloud are convenient, but they come with trade-offs:

- **Data sovereignty** — every permission check involves sending user/resource relationships to a third-party API. For regulated industries (healthcare, finance, government), this may not be acceptable.
- **Latency** — a network round-trip for every `check()` call adds up. Self-hosting in the same data center as your app keeps permission checks under 1ms.
- **Cost at scale** — per-check pricing models get expensive quickly. A self-hosted engine has no per-request charges.
- **Full control** — you own the schema, the data, the backup strategy, and the availability guarantees.

For teams that already self-host t[keycloak](https://www.keycloak.org/)hentication stack (Keycloak, Authentik, Zitadel), running authorization on-premise completes the picture. For related reading, see our [Zitadel vs Ory vs Keycloak IAM comparison](../zitadel-vs-ory-vs-keycloak-self-hosted-iam-guide/) and [Authentik vs Keycloak vs Authelia guide](../authentik-vs-keycloak-vs-authelia/) for the authentication side.

## What Is Zanzibar-Inspired Authorization?

Google's Zanzibar paper describes a system built around three concepts:

1. **Object types** — users, documents, folders, organizations.
2. **Relationships** — "Alice is a viewer of Document X", "Folder Y is a parent of Document X".
3. **Policies** — rules like "a document viewer can also see all its parent folders".

The system stores relationships and evaluates them on every `check()` call. This is called **relationship-based access control (ReBAC)**, and it's more flexible than RBAC or ABAC alone because it composes naturally: transitive permissions, group nesting, and conditional access all fall out of the relationship graph.

All three engines discussed here follow this model, but each has its own schema language, API design, and operational characteristics.

## SpiceDB: The Original Open-Source Zanzibar Implementation

[SpiceDB](https://github.com/authzed/spicedb) (6,608+ stars) is developed by AuthZed, founded by Zanzibar paper co-author Tim Hintz. It's the closest implementation to Google's original design.

### Key Features

- **Consis[postgresql](https://www.postgresql.org/)ally distributed** — supports CockroachDB and PostgreSQL as backends, with read-after-write consistency
- **Schema language** — uses `definition` blocks with `relation` and `permission` keywords, directly inspired by Zanzibar's configuration language
- **Dispatch architecture** — parallel dispatch tree evaluation for sub-millisecond checks even with deep permission hierarchies
- **Caveats** — supports conditional permissions (e.g., "can edit if the document is not archived")
- **Mature ecosystem** — CLI tool `zed`, official SDKs for Go, Python, Rust, Node.js, and Java

### Docker Compose Setup

SpiceDB requires a database backend. Here's a production-ready setup with CockroachDB:

```yaml
services:
  crdb:
    image: cockroachdb/cockroach:v25.2.0
    command: "start-single-node --insecure --accept-sql-without-tls"
    restart: unless-stopped
    ports:
      - "26257:26257"
      - "8080:8080"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 5s
      timeout: 3s
      retries: 5

  spicedb:
    image: authzed/spicedb:latest
    restart: unless-stopped
    ports:
      - "50051:50051"  # gRPC
      - "8443:8443"    # HTTP/gateway
    command: "serve"
    environment:
      SPICEDB_DATASTORE_ENGINE: "cockroachdb"
      SPICEDB_DATASTORE_CONN_URI: "postgresql://root@crdb:26257/spicedb?sslmode=disable"
      SPICEDB_GRPC_PRESHARED_KEY: "your-secret-key-here"
    depends_on:
      crdb:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "/bin/grpc_health_probe", "-addr=localhost:50051"]
      interval: 5s
      timeout: 3s
      retries: 5
```

Start it with `docker compose up -d`, then define a schema using the `zed` CLI:

```bash
export SPICEDB_ENDPOINT=localhost:50051
export SPICEDB_PRESHARED_KEY="your-secret-key-here"

# Write a schema
zed schema write <<SCHEMA
definition user {}

definition document {
    relation viewer: user
    relation editor: user
    relation owner: user

    permission view = viewer + editor + owner
    permission edit = editor + owner
}
SCHEMA
```

## OpenFGA: The Okta-Backed Alternative

[OpenFGA](https://github.com/openfga/openfga) (5,032+ stars) started as Open Source FGA by Okta. It uses a different modeling approach: authorization models are defined in JSON and uploaded as versioned "stores."

### Key Features

- **Store-based architecture** — each application gets its own "store" with versioned authorization models, enabling zero-downtime schema migrations
- **Tuple-based** — relationships are stored as tuples `(user, relation, object)`, managed via a simple REST/gRPC API
- **Model DSL** — uses a declarative model language with `type`, `relation`, and `allow` constructs, compiled to a check graph
- **Check, Expand, ListObjects API** — three core operations: verify a single permission, trace the permission path, or list all objects a user can access
- **Official SDKs** — Go, Node.js, Python, .NET, Java, Rust, and Kotlin

### Docker Compose Setup

OpenFGA ships with PostgreSQL support:

```yaml
services:
  postgres:
    image: postgres:17
    restart: unless-stopped
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: fga_secret_password
      POSTGRES_DB: openfga
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 3s
      retries: 5

  openfga:
    image: openfga/openfga:latest
    restart: unless-stopped
    command: "run"
    ports:
      - "8080:8080"    # HTTP
      - "8081:8081"    # gRPC
      - "3000:3000"    # Play UI
    environment:
      OPENFGA_DATASTORE_ENGINE: postgres
      OPENFGA_DATASTORE_URI: "postgres://postgres:fga_secret_password@postgres:5432/openfga?sslmode=disable"
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "/usr/bin/grpc_health_probe", "-addr=localhost:8081"]
      interval: 5s
      timeout: 3s
      retries: 5
```

Create a store and write your authorization model:

```bash
# Create a store
curl -s http://localhost:8080/stores \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"name":"my-app"}' | jq .

# Write an authorization model (simplified)
curl -s http://localhost:8080/states/{store_id}/models \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "type_definitions": [
      {"type": "user"},
      {"type": "document", "relations": {
        "viewer": {"this": {}},
        "editor": {"this": {}},
        "owner": {"this": {}},
        "can_view": {"union": {
          "child": [{"this": {}}, {"computedUserset": {"relation": "viewer"}}, {"computedUserset": {"relation": "editor"}}, {"computedUserset": {"relation": "owner"}}]
        }},
        "can_edit": {"union": {
          "child": [{"computedUserset": {"relation": "editor"}}, {"computedUserset": {"relation": "owner"}}]
        }}
      }}
    ]
  }'
```

## Permify: The Developer-Experience Focused Option

[Permify](https://github.com/Permify/permify) (5,847+ stars) takes a different approach to the Zanzibar model, focusing on developer experience with a visual editor and a simpler schema language. Permify was recently acquired by FusionAuth.

### Key Features

- **Visual schema editor** — web-based UI for designing and testing authorization models, lowering the barrier for non-security teams
- **Simple DSL** — uses a clean, readable syntax (`entity`, `relation`, `action`) that's easier to learn than raw Zanzibar definitions
- **Playground** — built-in testing environment where you can write sample data and validate permissions before deploying
- **PostgreSQL and in-memory** — supports PostgreSQL for production, SQLite and in-memory for development/testing
- **Open Policy Agent integration** — can export policies as Rego rules for use in OPA-based ecosystems

### Docker Compose Setup

```yaml
services:
  postgres:
    image: postgres:17
    restart: unless-stopped
    ports:
      - "5433:5432"
    environment:
      POSTGRES_USER: permify
      POSTGRES_PASSWORD: permify_pass
      POSTGRES_DB: permify
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U permify"]
      interval: 5s
      timeout: 3s
      retries: 5

  permify:
    image: ghcr.io/permify/permify:latest
    restart: unless-stopped
    command: "serve --config /etc/permify/config.yaml"
    ports:
      - "3476:3476"    # HTTP/gRPC
      - "3478:3478"    # metrics
    volumes:
      - ./permify-config.yaml:/etc/permify/config.yaml
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  permify_data:
```

With the config file:

```yaml
account_id: "your-account-id"
database:
  engine: postgres
  uri: "postgres://permify:permify_pass@postgres:5432/permify?sslmode=disable"
server:
  http:
    enabled: true
    port: 3476
  grpc:
    enabled: true
    port: 3476
```

Define a schema in Permify's DSL:

```perm
entity user {}

entity organization {
    relation admin @user
    relation member @user

    action delete = admin
    action add_member = admin
}

entity document {
    relation org @organization
    relation owner @user
    relation viewer @user @organization#member

    action read = owner or viewer or org.admin
    action write = owner or org.admin
    action delete = owner or org.admin
}
```

## Comparison: SpiceDB vs OpenFGA vs Permify

| Feature | SpiceDB | OpenFGA | Permify |
|---------|---------|---------|---------|
| **Stars** | 6,608+ | 5,032+ | 5,847+ |
| **License** | Apache-2.0 | Apache-2.0 | AGPL-3.0 |
| **Language** | Go | Go | Go |
| **Backend** | CockroachDB, PostgreSQL | PostgreSQL | PostgreSQL, SQLite, in-memory |
| **Schema Style** | Zanzibar DSL (definition/relation/permission) | JSON model definitions | Custom DSL (entity/relation/action) |
| **API** | gRPC primary, HTTP gateway | REST + gRPC | REST + gRPC |
| **Conditional Permissions** | Yes (Caveats) | Yes (Conditions) | Yes |
| **Visual Editor** | No (CLI-based) | No (Play UI is a sandbox) | Yes (web-based editor) |
| **SDK Languages** | Go, Python, Rust, Node.js, Java | Go, Node.js, Python, .NET, Java, Rust, Kotlin | Go, Node.js, Python, .NET |
| **Backed By** | AuthZed (Zanzibal paper co-author) | Okta | FusionAuth |
| **Multi-tenant** | Via separate namespaces | Via stores | Via workspaces |
| **Best For** | Teams wanting closest Zanzibar fidelity | Teams wanting versioned models, Okta ecosystem | Teams wanting visual tooling, quick onboarding |

## Performance and Scalability

All three engines are designed for sub-millisecond permission checks, but their architectures differ:

- **SpiceDB** uses a dispatch tree that evaluates permissions in parallel across the relationship graph. With CockroachDB as a backend, it supports globally distributed, strongly consistent deployments. Benchmarks from AuthZed show 100,000+ checks/second on a single node.
- **OpenFGA** uses a check graph compiler that translates the model DSL into an optimized evaluation plan. PostgreSQL-backed deployments handle 50,000+ checks/second. Its store versioning means you can roll out schema changes without downtime.
- **Permify** uses a similar graph-based evaluation approach. In single-node PostgreSQL configurations, it handles 30,000+ checks/second. The visual editor and playground make it the fastest to get started with, though the AGPL license may be a consideration for commercial embedding.

## When to Choose Which

**Choose SpiceDB if:**
- You want the most faithful Zanzibar implementation
- You need CockroachDB for global distribution
- You have a security team comfortable with CLI-driven schema management
- You value the Apache-2.0 license for commercial use

**Choose OpenFGA if:**
- You need versioned authorization models with zero-downtime migrations
- You're already in the Okta/FGA ecosystem and want an open-source alternative
- You prefer REST APIs over gRPC
- You need the widest SDK language support

**Choose Permify if:**
- Developer experience and visual tooling are priorities
- Your team is less familiar with authorization modeling
- You want a built-in playground for testing schemas
- You plan to integrate with FusionAuth (Permify's parent company)

## Security Considerations

Regardless of which engine you choose, follow these best practices:

1. **Never expose the engine directly to the internet** — place it behind your API gateway or service mesh. All three engines have no built-in authentication (they assume you control the network).
2. **Use mutual TLS for gRPC** — all three support mTLS. Enable it when communicating between your app and the authorization service.
3. **Audit relationship writes** — every `write`/`put` call modifies the permission graph. Log these operations and alert on anomalies.
4. **Backup the database** — authorization relationships are state. A lost database means rebuilding all permissions from scratch. Use your database's native backup tools (CockroachDB's `BACKUP`, PostgreSQL's `pg_dump`).
5. **Test before deploying** — use each engine's test tooling (`zed` for SpiceDB, OpenFGA's playground, Permify's visual editor) to validate schemas against real-world scenarios before going to production.

If you're building a complete self-hosted security stack, pair your authorization engine with proper [secret management](../best-self-hosted-secret-management-vault-infisical-passbolt-2026/) to protect database credentials and API keys.

## FAQ

### What is the difference between RBAC and ReBAC?

Role-Based Access Control (RBAC) assigns permissions to roles, then assigns users to roles. Relationship-Based Access Control (ReBAC) — the model used by SpiceDB, OpenFGA, and Permify — defines permissions based on relationships between entities. ReBAC is more flexible: it can express "Alice can edit this document because she owns the folder that contains it" without hard-coding folder ownership rules. RBAC is a subset of what ReBAC can express.

### Can I use these authorization engines with my existing authentication system?

Yes. These engines handle **authorization only** (what can a user do), not **authentication** (who is the user). They integrate with any identity provider — Keycloak, Authentik, Zitadel, or custom auth. Your application authenticates the user, then sends the user ID to the authorization engine for permission checks. See our [IAM comparison guide](../zitadel-vs-ory-vs-keycloak-self-hosted-iam-guide/) for choosing an authentication system.

### Do I need CockroachDB for SpiceDB, or can I use PostgreSQL?

SpiceDB supports both CockroachDB and PostgreSQL. CockroachDB is recommended for production deployments that need global distribution and horizontal scaling. PostgreSQL works fine for single-region setups and is simpler to operate. The choice affects your deployment topology but not your schema or API usage.

### Is it safe to run these engines without built-in authentication?

All three engines assume they run on a private network. They don't include built-in auth because they're designed to be called by your backend services, not directly by users. Protect them with network segmentation, mutual TLS, and (optionally) a reverse proxy with API key validation. Never expose the gRPC or REST ports to the public internet.

### How do I migrate from an existing RBAC system to a Zanzibar-style engine?

Start by mapping your roles to relationships. For example, if you have a "document editor" role, create a `relation editor: user` on the document entity. Import existing role assignments as relationship tuples. Run both systems in parallel during a migration period, comparing check results to verify correctness. Once confident, switch your application to use the new engine. All three tools provide migration guides and SDKs to help with this process.

### Which engine has the best performance for high-throughput applications?

In benchmark tests, SpiceDB leads with 100,000+ checks/second on a single node (thanks to its parallel dispatch architecture and CockroachDB backend). OpenFGA follows at 50,000+ checks/second, and Permify at 30,000+ checks/second. However, all three are fast enough for the vast majority of applications — even 30,000 checks/second handles millions of requests per day with room to spare. The choice should be driven by developer experience and ecosystem fit, not raw throughput.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "SpiceDB vs OpenFGA vs Permify: Self-Hosted Authorization Engines 2026",
  "description": "Compare SpiceDB, OpenFGA, and Permify — three Zanzibar-inspired open-source authorization engines for fine-grained, self-hosted permissions. Includes Docker setup, ReBAC modeling, and performance benchmarks.",
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
