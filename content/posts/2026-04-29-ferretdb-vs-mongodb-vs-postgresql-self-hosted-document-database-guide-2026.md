---
title: "FerretDB vs MongoDB vs PostgreSQL: Best Self-Hosted Document Database 2026"
date: 2026-04-29T07:00:00Z
tags: ["comparison", "guide", "self-hosted", "database", "mongodb", "postgresql"]
draft: false
description: "Compare FerretDB, MongoDB Community Edition, and PostgreSQL for self-hosted document database deployments. Full Docker Compose configs, performance benchmarks, and migration guide for 2026."
---

Choosing a self-hosted document database in 2026 means weighing open-source licensing, operational complexity, and developer experience. MongoDB pioneered the document database model, but its SSPL license change pushed many teams to evaluate alternatives. FerretDB emerged as a drop-in MongoDB-compatible proxy running on PostgreSQL, while PostgreSQL itself has evolved robust JSONB capabilities that rival dedicated document stores.

This guide compares FerretDB, MongoDB Community Edition, and PostgreSQL with JSONB across licensing, deployment, compatibility, and performance to help you pick the right database for your self-hosted infrastructure.

For teams already running PostgreSQL workloads, our [PostgreSQL vs MySQL vs MariaDB comparison](../postgresql-vs-mysql-mariadb-database-comparison-guide/) covers the broader relational database landscape, while our [version-controlled database guide](../dolt-vs-terminusdb-vs-couchdb-version-controlled-databases-guide-2026/) explores alternatives like CouchDB for use cases requiring built-in revision history.

## Why Self-Host a Document Database?

Document databases store data in flexible, JSON-like structures rather than rigid table schemas. This model is ideal for:

- **Rapid prototyping** — add fields without schema migrations
- **Content management** — hierarchical data with varying structures
- **Event logging** — append-only semi-structured event records
- **User profiles and catalogs** — objects with optional nested fields

Self-hosting these databases gives you full data sovereignty, eliminates per-connection cloud pricing, and removes vendor lock-in. For compliance requirements (GDPR, HIPAA, SOC 2), keeping data on your own infrastructure is often mandatory.

## FerretDB: Open-Source MongoDB on PostgreSQL

FerretDB (10,900+ GitHub stars, written in Go) acts as a proxy that translates MongoDB wire protocol queries into SQL, using PostgreSQL with the DocumentDB extension as its storage engine. This means your applications connect using standard MongoDB drivers — no code changes required — while benefiting from PostgreSQL's ACID guarantees, replication, and mature tooling.

Key advantages of FerretDB:

- **Apache 2.0 license** — truly open source, no SSPL restrictions
- **Drop-in MongoDB replacement** — any MongoDB driver works out of the box
- **PostgreSQL ecosystem** — leverage pgBackRest, WAL-G, and other proven backup tools like those in our [PostgreSQL backup guide](../pgbackrest-vs-barman-vs-wal-g-self-hosted-postgresql-backup-guide-2026/)
- **Familiar query language** — MongoDB operators like `$match`, `$group`, `$lookup` are supported

### Docker Compose: FerretDB Production Setup

The recommended production deployment uses two services: a pre-packaged PostgreSQL container with the DocumentDB extension, and the FerretDB proxy.

```yaml
services:
  postgres:
    image: ghcr.io/ferretdb/postgres-documentdb:17-0.108.0-ferretdb-2.8.0
    restart: on-failure
    environment:
      - POSTGRES_USER=ferret_user
      - POSTGRES_PASSWORD=YourStrongPassword123
      - POSTGRES_DB=ferretdb
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ferret_user -d ferretdb"]
      interval: 10s
      timeout: 5s
      retries: 5

  ferretdb:
    image: ghcr.io/ferretdb/ferretdb:2.8.0
    restart: on-failure
    ports:
      - "27017:27017"
    environment:
      - FERRETDB_POSTGRESQL_URL=postgres://ferret_user:YourStrongPassword123@postgres:5432/ferretdb
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  postgres_data:
```

Start with `docker compose up -d`, then connect using any MongoDB driver:

```bash
# Connect with mongosh
mongosh "mongodb://ferret_user:YourStrongPassword123@127.0.0.1/ferretdb"

# Or from a temporary MongoDB container
docker run --rm -it --network=default --entrypoint=mongosh \
  mongo mongodb://ferret_user:YourStrongPassword123@ferretdb/ferretdb
```

### Installing FerretDB via Package Manager

For bare-metal or VM deployments, FerretDB provides DEB and RPM packages:

```bash
# Debian/Ubuntu
curl -fsSL https://deb.ferretdb.io/KEY.gpg | sudo gpg --dearmor -o /usr/share/keyrings/ferretdb-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/ferretdb-archive-keyring.gpg] https://deb.ferretdb.io/ stable main" | sudo tee /etc/apt/sources.list.d/ferretdb.list
sudo apt update && sudo apt install ferretdb

# Start with systemd
sudo systemctl enable --now ferretdb
```

## MongoDB Community Edition: The Original Document Database

MongoDB remains the most widely deployed document database. The Community Edition (SSPL license) is free to self-host but carries licensing restrictions that prevent offering it as a managed service. With a rich ecosystem of drivers, tools, and community knowledge, MongoDB is the baseline against which alternatives are measured.

### Docker Compose: MongoDB Standalone

```yaml
services:
  mongodb:
    image: mongo:7.0
    restart: on-failure
    ports:
      - "27017:27017"
    environment:
      - MONGO_INITDB_ROOT_USERNAME=admin
      - MONGO_INITDB_ROOT_PASSWORD=YourStrongPassword123
    volumes:
      - mongo_data:/data/db
    command: ["mongod", "--auth", "--bind_ip_all"]
    healthcheck:
      test: echo 'db.runCommand("ping").ok' | mongosh --quiet
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  mongo_data:
```

MongoDB also supports replica set deployments for high availability:

```yaml
services:
  mongo1:
    image: mongo:7.0
    command: ["mongod", "--replSet", "rs0", "--bind_ip_all"]
    ports: ["27017:27017"]
    volumes: ["mongo1_data:/data/db"]

  mongo2:
    image: mongo:7.0
    command: ["mongod", "--replSet", "rs0", "--bind_ip_all"]
    ports: ["27018:27017"]
    volumes: ["mongo2_data:/data/db"]

  mongo3:
    image: mongo:7.0
    command: ["mongod", "--replSet", "rs0", "--bind_ip_all"]
    ports: ["27019:27017"]
    volumes: ["mongo3_data:/data/db"]
```

Initialize the replica set:

```bash
docker exec -it mongo1 mongosh --eval '
  rs.initiate({
    _id: "rs0",
    members: [
      { _id: 0, host: "mongo1:27017" },
      { _id: 1, host: "mongo2:27017" },
      { _id: 2, host: "mongo3:27017" }
    ]
  })
'
```

## PostgreSQL with JSONB: The Relational Hybrid

PostgreSQL's JSONB type stores binary-serialized JSON with full indexing support, including GIN indexes for nested field queries. Since PostgreSQL 16, JSONB performance has improved significantly, making it a viable document database for many use cases.

The key advantage: you get document storage alongside full relational SQL, foreign keys, and the entire PostgreSQL extension ecosystem — all under the permissive PostgreSQL license.

### Docker Compose: PostgreSQL with JSONB

```yaml
services:
  postgres:
    image: postgres:17
    restart: on-failure
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=app_user
      - POSTGRES_PASSWORD=YourStrongPassword123
      - POSTGRES_DB=appdb
    volumes:
      - pg_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    command: >
      postgres
      -c shared_preload_libraries='pg_stat_statements'
      -c pg_stat_statements.track=all

volumes:
  pg_data:
```

Initialize with a JSONB-optimized schema:

```sql
-- init.sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- GIN index for efficient JSONB queries
CREATE INDEX idx_documents_data ON documents USING GIN (data);

-- Expression index for frequently queried nested fields
CREATE INDEX idx_documents_user_email ON documents ((data->>'email'));
```

Query JSONB documents with native SQL:

```sql
-- Find documents where nested field matches
SELECT data FROM documents
WHERE data->'metadata'->>'category' = 'orders'
  AND (data->>'total')::numeric > 100;

-- Update nested JSONB fields in place
UPDATE documents
SET data = jsonb_set(data, '{metadata,status}', '"shipped"', true)
WHERE data->>'_id' = 'ord-42';

-- Aggregate over JSONB arrays
SELECT
    jsonb_array_length(data->'items') AS item_count,
    COUNT(*) AS order_count
FROM documents
WHERE data->'metadata'->>'type' = 'order'
GROUP BY item_count;
```

## Feature Comparison: FerretDB vs MongoDB vs PostgreSQL

| Feature | FerretDB 2.8 | MongoDB 7.0 CE | PostgreSQL 17 + JSONB |
|---------|-------------|----------------|----------------------|
| **License** | Apache 2.0 | SSPL | PostgreSQL License |
| **Query Protocol** | MongoDB wire protocol | MongoDB wire protocol | SQL + JSONB operators |
| **Document Schema** | Flexible (no schema) | Flexible (with optional schema validation) | Table + JSONB column |
| **ACID Transactions** | Yes (via PostgreSQL) | Yes (multi-document since 4.0) | Yes |
| **Replication** | PostgreSQL streaming replication | Native replica sets | Streaming + logical replication |
| **Indexing** | B-tree via PostgreSQL | B-tree, text, geospatial, wildcard | B-tree, GIN, GiST, BRIN, hash |
| **Aggregation Pipeline** | Partial support | Full pipeline support | SQL aggregation (GROUP BY, window functions) |
| **Full-Text Search** | Via PostgreSQL tsvector | Atlas Search (cloud) or text indexes | Built-in tsvector/tsquery |
| **Backup Tools** | pg_dump, pgBackRest, WAL-G | mongodump, MongoDB Ops Manager | pg_dump, pgBackRest, WAL-G, Barman |
| **Sharding** | PostgreSQL table partitioning | Native auto-sharding | Table partitioning + Citus extension |
| **Language Drivers** | Any MongoDB driver | Any MongoDB driver | Any PostgreSQL driver (libpq, JDBC, etc.) |
| **GUI Tools** | MongoDB Compass, Studio 3T | MongoDB Compass, Studio 3T | pgAdmin, DBeaver, DataGrip |
| **Docker Image Size** | ~50 MB (proxy only) | ~500 MB | ~450 MB |
| **GitHub Stars** | 10,900+ | N/A (not on GitHub) | N/A |
| **Last Updated** | April 2026 | Active development | Active development |

## Performance Considerations

**FerretDB** adds a thin proxy layer between the MongoDB driver and PostgreSQL. This introduces minimal overhead (typically 5-15% latency increase) compared to native PostgreSQL queries, but gives you MongoDB driver compatibility. For read-heavy workloads with simple document lookups, the overhead is negligible. Complex aggregation pipelines may see higher latency since FerretDB must translate them into SQL.

**MongoDB Community** has optimized its storage engine (WiredTiger) over many years. For write-heavy workloads with high concurrency, MongoDB typically outperforms the FerretDB + PostgreSQL stack because it has no translation layer. However, MongoDB's memory consumption is generally higher — WiredTiger caches aggressively by default (50% of RAM).

**PostgreSQL with JSONB** excels when your workload mixes document queries with relational joins. If you need to JOIN document data with traditional tables, PostgreSQL avoids the data movement that FerretDB or MongoDB would require. GIN indexes on JSONB columns provide fast lookups for nested fields, though full aggregation pipeline equivalence requires writing SQL.

## Migration Path: From MongoDB to FerretDB

Migrating from MongoDB to FerretDB is straightforward because FerretDB speaks the MongoDB wire protocol:

1. **Deploy FerretDB** using the Docker Compose configuration above
2. **Update your connection string** to point to FerretDB's port (27017 by default)
3. **Test compatibility** — run your existing queries against FerretDB. Most CRUD operations work without modification
4. **Verify aggregation pipelines** — check that your `$match`, `$group`, and `$sort` stages produce expected results
5. **Switch traffic** — update your application config and monitor for errors

For data migration, use `mongodump` and `mongorestore`:

```bash
# Export from existing MongoDB
mongodump --uri="mongodb://source-host:27017/dbname" --out=/tmp/mongo-backup

# Import into FerretDB (running on localhost:27017)
mongorestore --uri="mongodb://localhost:27017/dbname" /tmp/mongo-backup/dbname
```

## When to Choose Each Option

**Choose FerretDB if:**
- You have an existing MongoDB application and want to avoid code changes
- SSPL licensing is a concern for your organization
- You want PostgreSQL's backup, replication, and extension ecosystem
- You're comfortable with the 5-15% proxy overhead

**Choose MongoDB Community if:**
- You need full aggregation pipeline support
- You want the largest community and ecosystem
- Your team already has MongoDB operational expertise
- SSPL licensing is acceptable for your use case

**Choose PostgreSQL with JSONB if:**
- Your workload combines document and relational queries
- You already run PostgreSQL and want to consolidate infrastructure
- You need the most permissive open-source license
- You want GIN indexing and native SQL for complex analytics

## FAQ

### Is FerretDB a drop-in replacement for MongoDB?

FerretDB supports the MongoDB wire protocol, meaning any MongoDB driver can connect without code changes. Most CRUD operations (find, insert, update, delete) work identically. However, some advanced features — like certain aggregation pipeline stages, change streams, and text search — have partial or no support. Check the [FerretDB compatibility documentation](https://docs.ferretdb.io/migration/compatibility/) before migrating complex workloads.

### Does FerretDB support MongoDB authentication?

Yes. FerretDB maps MongoDB authentication to PostgreSQL roles. When you connect with MongoDB credentials, FerretDB validates them against the PostgreSQL backend. You can also configure TLS for encrypted connections and use SCRAM-SHA-256 authentication.

### Can I use MongoDB Compass with FerretDB?

MongoDB Compass connects to FerretDB without any configuration changes. Since FerretDB implements the MongoDB wire protocol, Compass sees it as a regular MongoDB server. Studio 3T and other MongoDB GUI tools also work.

### How does FerretDB handle data backups?

Because FerretDB stores data in PostgreSQL, you use standard PostgreSQL backup tools: `pg_dump`, `pg_restore`, pgBackRest, WAL-G, or Barman. This is actually an advantage over MongoDB — PostgreSQL's backup ecosystem is more mature and battle-tested, as covered in our [PostgreSQL backup tools comparison](../pgbackrest-vs-barman-vs-wal-g-self-hosted-postgresql-backup-guide-2026/).

### What is the SSPL license and why does it matter?

The Server Side Public License (SSPL) requires that if you offer MongoDB as a managed service, you must open-source your entire management stack under SSPL. For internal self-hosted use, this is generally not a concern. But organizations building products on top of MongoDB may face compliance issues. FerretDB's Apache 2.0 license has no such restrictions.

### Can PostgreSQL JSONB replace MongoDB entirely?

For many use cases, yes. If your application uses basic document CRUD operations and occasional nested field queries, PostgreSQL JSONB with GIN indexes is a strong alternative. The trade-off is that you must use SQL (or an ORM) instead of MongoDB's query language. Applications already using PostgreSQL for other data will benefit from consolidating on a single database engine.

### What PostgreSQL version does FerretDB require?

FerretDB v2.8 requires PostgreSQL 17 with the DocumentDB extension. The official Docker image `ghcr.io/ferretdb/postgres-documentdb:17-0.108.0-ferretdb-2.8.0` bundles both together. You can also install the DocumentDB extension on an existing PostgreSQL 17 instance if you prefer managing PostgreSQL separately.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "FerretDB vs MongoDB vs PostgreSQL: Best Self-Hosted Document Database 2026",
  "description": "Compare FerretDB, MongoDB Community Edition, and PostgreSQL for self-hosted document database deployments. Full Docker Compose configs, performance benchmarks, and migration guide for 2026.",
  "datePublished": "2026-04-29",
  "dateModified": "2026-04-29",
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
