---
title: "SurrealDB Self-Hosted Multi-Model Database: Complete Guide 2026"
date: 2026-04-21
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete guide to self-hosting SurrealDB, the open-source multi-model document-graph database built in Rust. Covers installation, Docker deployment, SurrealQL queries, authentication, clustering, and production configuration."
---

SurrealDB is a modern, open-source database that blurs the line between document stores, graph databases, and relational systems. Built entirely in Rust, it lets you store, query, and manage data using a single unified query language — SurrealQL — while supporting real-time subscriptions, row-level permissions, and distributed clustering out of the box.

With over 31,000 stars on GitHub and weekly releases from an active development team, SurrealDB has matured into a viable production database for applications that need flexible data modeling without juggling multiple database systems.

This guide covers everything you need to self-host SurrealDB: installation methods, Docker deployment, SurrealQL fundamentals, authentication setup, and production clustering configuration.

## Why Self-Host SurrealDB

Running your own SurrealDB instance gives you capabilities that hosted database services cannot match:

**Full data control.** Your application data — including user records, session tokens, and business logic — stays on infrastructure you own. No third-party database operator can access, monetize, or restrict your data.

**Unified data model.** Traditional architectures require a document database for flexible JSON storage, a graph database for relationship queries, and a relational database for transactions. SurrealDB handles all three patterns in a single engine, reducing operational complexity and eliminating inter-database synchronization.

**Cost predictability.** Managed database services charge per read, per write, per gigabyte stored, and per compute hour. A self-hosted SurrealDB instance on a $15/month VPS handles millions of records with predictable resource usage.

**Real-time subscriptions.** SurrealDB supports live queries that push changes to connected clients over WebSockets. Self-hosting means you control the WebSocket endpoint, connection limits, and authentication — no middleware proxy required.

**Edge deployment.** Because SurrealDB runs as a single binary with no external dependencies, you can deploy it on edge servers, Raspberry Pi devices, or containers in remote locations where managed database connectivity is unreliable.

## Architecture Overview

SurrealDB's architecture differs fundamentally from traditional databases:

| Feature | Traditional RDBMS | Document DB + Graph DB | SurrealDB |
|---------|-------------------|----------------------|-----------|
| Data model | Tables with fixed schemas | Separate JSON docs + graph nodes | Unified records with flexible schemas |
| Query language | SQL | Multiple (MongoDB query, Cypher, Gremlin) | SurrealQL (single language) |
| Relationships | JOINs with foreign keys | Manual graph traversal | First-class record links with `RELATE` |
| Real-time | Polling or separate message queue | Separate WebSocket layer | Built-in `LIVE SELECT` subscriptions |
| Permissions | Row/column-level grants | Application-level enforcement | Built-in `DEFINE ACCESS` rules |
| Deployment | Single-primary or primary-replica | Separate clusters per engine | Single binary, embeddable or distributed |
| Storage engines | Limited choices | Engine-specific | RocksDB, TiKV, FoundationDB, SurrealKV, memory |

SurrealDB stores data as **records** — each record has a unique table-and-ID identifier (e.g., `person:john`), can contain nested JSON-like fields, and can reference other records directly. This unified model means a single query can traverse relationships, filter on nested fields, and aggregate results without joining across separate systems.

## Installation Methods

### Binary Installation

SurrealDB ships as a single static binary. Install it directly on your server:

```bash
curl -sSf https://install.surrealdb.com | sh
```

Or use your system package manager:

```bash
# Debian/Ubuntu
curl -sSf https://deb.surrealdb.com/surrealdb.gpg | gpg --dearmor -o /usr/share/keyrings/surrealdb.gpg
echo "deb [signed-by=/usr/share/keyrings/surrealdb.gpg] https://deb.surrealdb.com/deb all main" > /etc/apt/sources.list.d/surrealdb.list
apt update && apt install surrealdb

# macOS (Homebrew)
brew install surrealdb
```

### Docker Deployment

The official Docker image supports multiple storage backends. Here is a production-ready Docker Compose configuration:

```yaml
services:
  surrealdb:
    image: surrealdb/surrealdb:latest
    container_name: surrealdb
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - surrealdb-data:/data
    command: >
      start
      --log info
      --user root
      --pass ${SURREAL_ROOT_PASS:-changeme}
      --bind 0.0.0.0:8000
      file:/data/surrealdb.db
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  # Optional: SurrealDB Studio (web UI)
  surrealdb-studio:
    image: surrealdb/surrealdb-studio:latest
    container_name: surrealdb-studio
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - SURREALDB_URL=http://surrealdb:8000
    depends_on:
      surrealdb:
        condition: service_healthy

volumes:
  surrealdb-data:
    driver: local
```

Deploy with:

```bash
export SURREAL_ROOT_PASS=$(openssl rand -base64 32)
docker compose up -d
```

This configuration mounts a named volume for persistence, sets a health check, and includes the optional SurrealDB Studio web interface for database management.

### Embedded Mode

For applications that need a database without a separate server process, SurrealDB embeds directly into your application:

```python
# Python example with surrealdb library
from surrealdb import Surreal

async def main():
    async with Surreal("ws://localhost:8000/rpc") as db:
        await db.signin({"user": "root", "pass": "changeme"})
        await db.use("test", "namespace")

        # Create a record
        person = await db.create("person", {
            "name": "Tobie",
            "email": "tobie@example.com",
            "age": 30
        })

        # Query with conditions
        adults = await db.query(
            "SELECT * FROM person WHERE age >= $min_age",
            {"min_age": 18}
        )
        print(f"Found {len(adults)} adults")
```

## SurrealQL Fundamentals

SurrealQL is the unified query language that powers all data operations. It combines familiar SQL syntax with graph traversal and document manipulation capabilities.

### Creating Records

Records in SurrealDB have explicit identifiers. You can let the database generate IDs or specify your own:

```sql
-- Generate a random ID
CREATE person SET name = 'Alice', email = 'alice@example.com';

-- Specify an explicit ID
CREATE person:john SET name = 'John', email = 'john@example.com', active = true;

-- Create multiple records at once
CREATE person:alice, person:bob SET active = true;
```

### Querying with Relations

The `RELATE` statement creates graph-style connections between records:

```sql
-- Create a relationship
RELATE person:john->knows->person:alice SET since = time::now();

-- Query through relationships: find everyone John knows
SELECT ->knows->person FROM person:john;

-- Query with conditions on the relationship
SELECT ->knows->person.* FROM person:john
WHERE ->knows.since > time::now() - 365d;

-- Find people who know each other (bidirectional)
SELECT * FROM person WHERE ->knows->person = person:alice;
```

### Schema Definition

SurrealDB supports both schemaless and schema-defined tables:

```sql
-- Define a schema-enforced table
DEFINE TABLE user SCHEMAFULL;
DEFINE FIELD name ON TABLE user TYPE string ASSERT string::len($value) > 0;
DEFINE FIELD email ON TABLE user TYPE string ASSERT string::is::email($value) UNIQUE;
DEFINE FIELD created ON TABLE user VALUE time::now() DEFAULT time::now();
DEFINE FIELD updated ON TABLE user VALUE time::now() DEFAULT time::now();

-- Create an index for fast lookups
DEFINE INDEX email_idx ON TABLE user COLUMNS email;

-- Schemaless table (accepts any fields)
DEFINE TABLE session SCHEMALESS;
```

### Live Subscriptions

Real-time data push without separate WebSocket infrastructure:

```sql
-- Subscribe to all changes on the user table
LIVE SELECT * FROM user;

-- Subscribe with conditions
LIVE SELECT * FROM order WHERE status = 'pending';

-- The server pushes a notification for every INSERT, UPDATE, or DELETE
-- that matches the query criteria
```

## Authentication and Permissions

SurrealDB has a built-in, multi-layered permission system that eliminates the need for application-level authorization middleware.

### Root and Namespace Access

```sql
-- Root access (server-level admin)
-- Set via command-line: --user root --pass <password>

-- Namespace-level access
DEFINE ACCESS admin ON DATABASE NAMESPACE SCOPE admin
    WITH JWT EXPIRE 24h
    ALGORITHM HS512
    KEY "your-jwt-secret-key";
```

### Scope-Based Authentication

Scopes define authentication flows for different user types:

```sql
-- Define a user scope (for application-level authentication)
DEFINE SCOPE user
    SESSION 24h
    SIGNUP (
        CREATE user SET name = $name, email = $email, pass = crypto::argon2::generate($pass)
    )
    SIGNIN (
        SELECT * FROM user WHERE email = $email AND crypto::argon2::compare(pass, $pass)
    );

-- Define an admin scope with stricter rules
DEFINE SCOPE admin
    SESSION 1h
    SIGNIN (
        SELECT * FROM admin_user WHERE email = $email AND pass = crypto::argon2::generate($pass)
    );
```

### Table-Level Permissions

Fine-grained access control at the record level:

```sql
-- Only authenticated users can read their own records
DEFINE TABLE user PERMISSIONS
    FOR select WHERE id = $auth.id
    FOR create, update, delete WHERE id = $auth.id;

-- Public read, authenticated write
DEFINE TABLE product PERMISSIONS
    FOR select NONE
    FOR create, update WHERE $auth.role = 'admin'
    FOR delete WHERE $auth.role = 'admin';
```

## Production Deployment

### Clustering with TiKV

For high-availability production deployments, use TiKV as the distributed storage engine:

```yaml
services:
  surrealdb-1:
    image: surrealdb/surrealdb:latest
    command: >
      start
      --log info
      --user root
      --pass ${SURREAL_ROOT_PASS}
      --bind 0.0.0.0:8000
      tikv:pd-1:2379,pd-2:2379,pd-3:2379
    ports:
      - "8001:8000"
    networks:
      - surreal-net

  surrealdb-2:
    image: surrealdb/surrealdb:latest
    command: >
      start
      --log info
      --user root
      --pass ${SURREAL_ROOT_PASS}
      --bind 0.0.0.0:8000
      tikv:pd-1:2379,pd-2:2379,pd-3:2379
    ports:
      - "8002:8000"
    networks:
      - surreal-net

  surrealdb-3:
    image: surrealdb/surrealdb:latest
    command: >
      start
      --log info
      --user root
      --pass ${SURREAL_ROOT_PASS}
      --bind 0.0.0.0:8000
      tikv:pd-1:2379,pd-2:2379,pd-3:2379
    ports:
      - "8003:8000"
    networks:
      - surreal-net

networks:
  surreal-net:
    driver: bridge
```

### Reverse Proxy Configuration

Place SurrealDB behind a reverse proxy for TLS termination and rate limiting:

```nginx
server {
    listen 443 ssl http2;
    server_name db.example.com;

    ssl_certificate /etc/ssl/certs/db.example.com.crt;
    ssl_certificate_key /etc/ssl/private/db.example.com.key;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support for live queries
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }
}
```

### Backup and Restore

SurrealDB supports native export and import:

```bash
# Export the entire database
surreal export --ns test --db myapp --user root --pass changeme backup.surql

# Export a single table
surreal export --ns test --db myapp --user root --pass changeme --table user users_backup.surql

# Import from a backup
surreal import --ns test --db myapp --user root --pass changeme backup.surql
```

For automated backups, combine with a cron job:

```bash
# /etc/cron.d/surrealdb-backup
0 2 * * * root surreal export --ns production --db app --user root --pass $PASS /backups/surreal-$(date +\%Y\%m\%d).surql && find /backups -name "surreal-*.surql" -mtime +30 -delete
```

## When to Use SurrealDB vs Other Databases

SurrealDB excels in specific scenarios and is less suited for others:

| Scenario | Recommended | Reason |
|----------|-------------|--------|
| Rapid prototyping with flexible schemas | SurrealDB | Schemaless mode, no migrations needed |
| Social network with complex relationships | SurrealDB | First-class graph traversal in SurrealQL |
| Real-time collaborative applications | SurrealDB | Built-in live subscriptions over WebSockets |
| High-throughput OLTP (100K+ writes/sec) | PostgreSQL / CockroachDB | SurrealDB is still optimizing write throughput |
| Existing PostgreSQL ecosystem investment | PostgreSQL | SurrealDB uses its own query language |
| Time-series data ingestion | TimescaleDB / InfluxDB | Not SurrealDB's primary optimization target |
| Multi-model with single database | SurrealDB | Eliminates need for separate document + graph stores |

If you are already running a distributed SQL cluster like [CockroachDB, YugabyteDB, or TiDB](../cockroachdb-vs-yugabyte-vs-tidb-distributed-sql-guide-2026/), SurrealDB can serve as a complementary real-time layer for user-facing features while your primary cluster handles transactional workloads. For applications that need graph queries alongside document storage, SurrealDB replaces the need to run [separate graph and document databases](../self-hosted-graph-databases-neo4j-arangodb-nebulagraph-guide-2026/).

## FAQ

### Is SurrealDB production-ready in 2026?

SurrealDB reached version 2.0 and has been used in production by companies handling millions of records. The core engine is stable, and the team maintains a regular release cadence with weekly updates. For distributed clustering, TiKV and FoundationDB storage engines are production-tested. The newer SurrealKV engine is maturing but recommended for evaluation before large-scale production use.

### What is the difference between SurrealDB and a traditional SQL database?

Traditional SQL databases use fixed table schemas, require explicit JOIN syntax for relationships, and store data in rows and columns. SurrealDB uses a flexible record model where each record has a unique ID, can contain nested JSON data, and can link to other records natively. SurrealQL supports both SQL-like queries and graph traversal, eliminating the need for separate query languages for different data patterns.

### Can I migrate from MongoDB or PostgreSQL to SurrealDB?

Yes. SurrealDB provides import tools for JSON, CSV, and SurrealQL formats. For MongoDB, you can export collections as JSON and import them directly — SurrealDB's document model maps naturally to MongoDB's structure. For PostgreSQL, you can export as CSV or use migration scripts. However, complex stored procedures and triggers will need to be rewritten as SurrealDB event definitions.

### Does SurrealDB support ACID transactions?

Yes. SurrealDB supports full ACID transactions at the record and table level. When using distributed storage engines like TiKV or FoundationDB, transactions span across multiple nodes with strong consistency guarantees. Single-node deployments with SurrealKV or file storage also provide ACID semantics within a single instance.

### How does SurrealDB handle horizontal scaling?

SurrealDB scales horizontally through its distributed storage engine layer. With TiKV, data is automatically sharded and replicated across nodes. With FoundationDB, it leverages that database's proven multi-node transactional layer. The SurrealDB compute layer is stateless — you can add or remove compute nodes without data migration. For smaller deployments, the embedded mode runs as a single process with no clustering overhead.

### What programming languages have official SurrealDB drivers?

Official drivers exist for JavaScript/TypeScript (npm), Python (pip), Rust (crates.io), Go (go get), Java (Maven), .NET (NuGet), and PHP (Composer). Community-maintained drivers are available for Kotlin, Swift, Dart, and Elixir. All official drivers support the full SurrealQL feature set including live queries, authentication scopes, and parameterized queries.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "SurrealDB Self-Hosted Multi-Model Database: Complete Guide 2026",
  "description": "Complete guide to self-hosting SurrealDB, the open-source multi-model document-graph database built in Rust. Covers installation, Docker deployment, SurrealQL queries, authentication, clustering, and production configuration.",
  "datePublished": "2026-04-21",
  "dateModified": "2026-04-21",
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
