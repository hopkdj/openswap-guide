---
title: "Self-Hosted Lightweight Database Migrations: Goose vs dbmate vs Atlas (2026)"
date: "2026-05-14"
tags: ["database", "migration", "devops", "schema-management", "self-hosted"]
draft: false
---

Database schema migration is one of those problems that seems simple until you are managing it in production across multiple environments, teams, and database engines. Enterprise tools like Flyway and Liquibase solve the problem but bring significant overhead: XML configuration, JVM dependencies, and steep learning curves. For teams that want database migrations without the enterprise baggage, lightweight CLI-first tools offer a refreshing alternative.

In this guide, we compare three leading lightweight database migration tools: **Goose** (Go-based, SQL and Go migrations), **dbmate** (language-agnostic, multi-database support), and **Atlas** (declarative, schema-as-code approach). Each serves the same core purpose — evolving your database schema safely — but with distinctly different philosophies.

## What Makes a Migration Tool "Lightweight"?

The term "lightweight" in this context means:

- **No JVM required** — Go, Rust, or native binaries instead of Java dependencies
- **Single binary** — install one executable, no package managers or runtime environments
- **SQL-first** — write migrations in plain SQL, not XML or custom DSLs
- **Minimal configuration** — convention over configuration, zero-config defaults
- **CI/CD friendly** — easy to integrate into pipelines, Docker containers, and automated workflows

Enterprise tools like Flyway (JVM-based) and Liquibase (XML/YAML-heavy) require runtime environments and configuration files. The tools in this comparison run as single binaries with minimal setup.

## Goose: SQL and Go Migrations

[Goose](https://github.com/pressly/goose) (10,663 GitHub stars) is a database migration tool written in Go, originally developed by Pressly (now acquired by Bitmovin). It supports both SQL migration files and Go function migrations, making it uniquely flexible for teams that need programmatic migration logic.

### Key Features

- **Dual migration format** — write migrations in plain SQL or Go functions
- **Multi-database support** — PostgreSQL, MySQL, SQLite, ClickHouse, SQL Server, Redshift, YQL, and more
- **Sequential and timestamp-based versioning** — choose your version numbering scheme
- **Embedded migrations** — use Go embed to bundle migration files into your binary
- **Go library API** — import as a Go package for programmatic control
- **CLI and library mode** — use as a standalone tool or embed in your application

### Migration File Format

Goose uses a simple SQL file format with up/down directives:

```sql
-- +goose Up
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);

-- +goose Down
DROP INDEX idx_users_email;
DROP TABLE users;
```

Go function migrations allow complex logic:

```go
package migrations

import (
    "database/sql"
    "github.com/pressly/goose/v3"
)

func init() {
    goose.AddMigration(Up001, Down001)
}

func Up001(tx *sql.Tx) error {
    // Complex migration logic
    _, err := tx.Exec("ALTER TABLE users ADD COLUMN role VARCHAR(50)")
    return err
}

func Down001(tx *sql.Tx) error {
    _, err := tx.Exec("ALTER TABLE users DROP COLUMN role")
    return err
}
```

### Docker Deployment

Goose does not ship an official Docker image, but it is trivial to containerize:

```yaml
services:
  goose-migrate:
    image: pressly/goose:latest
    environment:
      GOOSE_DRIVER: postgres
      GOOSE_DBSTRING: postgres://user:pass@db:5432/mydb
    volumes:
      - ./migrations:/migrations:ro
    command: ["goose", "-dir", "/migrations", "up"]
    depends_on:
      - db

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: mydb
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
```

### Installation and Usage

```bash
# Install
go install github.com/pressly/goose/v3/cmd/goose@latest

# Create a new migration
goose create add_users_table sql -dir ./migrations

# Run migrations
GOOSE_DRIVER=postgres GOOSE_DBSTRING="postgres://user:pass@localhost:5432/mydb" goose -dir ./migrations up

# Check status
goose -dir ./migrations status
```

## dbmate: Language-Agnostic Database Migrations

[dbmate](https://github.com/amacneil/dbmate) (6,893 GitHub stars) is a lightweight, framework-agnostic database migration tool written in Go. It focuses on simplicity: one binary, multiple databases, plain SQL migrations, and zero configuration. dbmate is the simplest option in this comparison.

### Key Features

- **Language-agnostic** — works with any programming language, no language-specific dependencies
- **Multi-database support** — PostgreSQL, MySQL, SQLite, ClickHouse, BigQuery, Spanner, Netezza, and more
- **Plain SQL migrations** — no custom DSL, just SQL files with `-- migrate:up` and `-- migrate:down` comments
- **Zero configuration** — database URL via environment variable, migrations directory defaults to `./db/migrations`
- **Automatic schema table** — creates and manages a `schema_migrations` table for tracking
- **Concurrent migration safety** — advisory locks prevent race conditions in CI/CD environments

### Migration File Format

dbmate uses a straightforward SQL file format:

```sql
-- migrate:up
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- migrate:down
DROP TABLE products;
```

Files are sorted alphabetically, so the naming convention `20260514000000_create_products.sql` ensures correct ordering.

### Docker Compose Deployment

dbmate provides an official Dockerfile:

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: mydb
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - pgdata:/var/lib/postgresql/data

  migrate:
    image: ghcr.io/amacneil/dbmate:latest
    environment:
      DATABASE_URL: postgres://user:pass@db:5432/mydb?sslmode=disable
    volumes:
      - ./db/migrations:/db/migrations:ro
    command: ["dbmate", "-d", "/db/migrations", "up"]
    depends_on:
      - db

  app:
    build: .
    environment:
      DATABASE_URL: postgres://user:pass@db:5432/mydb?sslmode=disable
    depends_on:
      migrate:
        condition: service_completed_successfully

volumes:
  pgdata:
```

### Installation and Usage

```bash
# Install (macOS)
brew install amacneil/dbmate/dbmate

# Install (Go)
go install github.com/amacneil/dbmate/v2@latest

# Install (binary)
curl -fsSL https://github.com/amacneil/dbmate/releases/latest/download/dbmate-linux-amd64 -o /usr/local/bin/dbmate
chmod +x /usr/local/bin/dbmate

# Create migration
dbmate new create_products_table

# Run migrations
DATABASE_URL="postgres://user:pass@localhost:5432/mydb" dbmate up

# Rollback last migration
DATABASE_URL="postgres://user:pass@localhost:5432/mydb" dbmate down
```

## Atlas: Declarative Schema-as-Code

[Atlas](https://github.com/ariga/atlas) (8,378 GitHub stars) takes a fundamentally different approach from Goose and dbmate. Instead of writing migration files (imperative), you declare your desired schema (declarative) and Atlas calculates the diff to get there. This "schema-as-code" approach is similar to Terraform for databases.

### Key Features

- **Declarative migrations** — declare the desired schema, Atlas calculates the diff
- **HCL schema definition** — define schemas in HashiCorp Configuration Language
- **Multi-database support** — MySQL, PostgreSQL, MariaDB, SQLite, TiDB, CockroachDB, SQL Server, ClickHouse, and more
- **SQL generation** — automatically generates migration SQL from schema diffs
- **Linting** — detect destructive changes (DROP COLUMN, ALTER TYPE) before applying
- **Versioned and declarative modes** — choose between migration files or desired-state application
- **Integration with ORMs** — works with Prisma, Ent, GORM, and other ORMs

### Schema Definition (HCL)

```hcl
table "users" {
  schema = schema.public

  column "id" {
    type = serial
  }

  column "email" {
    type = varchar(255)
  }

  column "role" {
    type    = varchar(50)
    default = "viewer"
  }

  primary_key {
    columns = [column.id]
  }

  index "idx_users_email" {
    unique  = true
    columns = [column.email]
  }
}

table "products" {
  schema = schema.public

  column "id" {
    type = uuid
    default = sql("gen_random_uuid()")
  }

  column "name" {
    type = varchar(255)
  }

  column "price" {
    type = decimal(10, 2)
  }

  primary_key {
    columns = [column.id]
  }
}
```

### Docker Deployment

Atlas provides an official Docker image:

```yaml
services:
  atlas:
    image: arigaio/atlas:latest
    working_dir: /atlas
    volumes:
      - ./schema:/atlas/schema:ro
      - ./migrations:/atlas/migrations
    command: >
      atlas migrate diff initial \
        --env dev \
        --to file:///atlas/schema \
        --dev-url "docker://postgres/16/dev"
```

### Installation and Usage

```bash
# Install
curl -sSf https://atlasgo.sh | sh

# Inspect current database schema
atlas schema inspect -u "postgres://user:pass@localhost:5432/mydb?sslmode=disable"

# Generate migration from desired schema
atlas migrate diff create_users \
  --to "file://schema.hcl" \
  --dev-url "docker://postgres/16/dev"

# Apply migrations
atlas migrate apply \
  --url "postgres://user:pass@localhost:5432/mydb?sslmode=disable"

# Lint for destructive changes
atlas migrate lint \
  --dev-url "docker://postgres/16/dev" \
  --latest 1
```

## Comparison Table

| Feature | Goose | dbmate | Atlas |
|---------|-------|--------|-------|
| **Approach** | Imperative (SQL files) | Imperative (SQL files) | Declarative (HCL schema) |
| **GitHub Stars** | 10,663 | 6,893 | 8,378 |
| **Language** | Go | Go | Go |
| **Migration Format** | SQL or Go functions | Plain SQL | HCL schema definition |
| **Databases** | 10+ | 8+ | 9+ |
| **Rollback** | Yes (down migration) | Yes (down migration) | Yes (computed diff) |
| **Linting** | No | No | Yes (destructive change detection) |
| **Docker Image** | Community | Official (GHCR) | Official (Docker Hub) |
| **ORM Integration** | Go embed only | None | Prisma, Ent, GORM |
| **Best For** | Go teams, complex migrations | Multi-language teams, simplicity | Schema-as-code, safety |

## Choosing the Right Tool

**Use Goose if:** Your team writes Go and you need the flexibility of both SQL and programmatic (Go function) migrations. Goose Go function migrations allow complex logic — data transformations, conditional schema changes, and multi-step operations — that are impossible in plain SQL. It is the most mature option with the largest community.

**Use dbmate if:** You want the simplest possible tool that works with any programming language. dbmate has zero configuration, plain SQL migrations, and a single binary. It is ideal for polyglot teams where different services use different languages but share a database. The migration format is so simple that anyone on the team can write and review migration files.

**Use Atlas if:** You prefer declarative infrastructure management (like Terraform) over writing individual migration files. Atlas approach — declare your desired schema and let the tool compute the diff — catches destructive changes before they reach production. The built-in linting and ORM integrations make it the safest option for teams that prioritize correctness over simplicity.

For database management context, see our [database query routing guide](../2026-05-10-database-query-routing-mysql-router-maxscale-proxysql-guide/) and [schema diff tools comparison](../2026-05-09-self-hosted-database-schema-diff-comparison-sqitch-flyway-liquibase-guide/).

## Why Self-Host Database Migrations?

Running database migrations as part of your self-hosted infrastructure — rather than relying on managed database platform features — provides several critical advantages:

**Full control over migration timing.** Managed database platforms often tie migration execution to their deployment pipeline, forcing you into their release cadence. Self-hosted migration tools let you run migrations on your own schedule — before, during, or after application deployments. This is essential for zero-downtime deployment strategies like expand-and-contract.

**Database engine independence.** When you use a cloud provider migration tool, you are locked into that provider database engine. Self-hosted migration tools like dbmate and Goose work across PostgreSQL, MySQL, SQLite, and more. If you ever need to migrate between database engines — or run different engines in different environments — a tool-agnostic migration layer is essential.

**Audit trail and version control.** Self-hosted migration tools store migration files in Git alongside your application code. Every schema change is version-controlled, reviewed through pull requests, and traceable to a specific commit. This creates an immutable audit trail that satisfies compliance requirements and makes debugging schema issues straightforward.

**CI/CD pipeline integration.** Lightweight migration tools integrate seamlessly into automated pipelines. Run schema validation on every pull request, apply migrations to staging automatically, and gate production deployments on successful migration execution. The single-binary nature of these tools means no JVM startup overhead in your CI runners.

**Cost efficiency.** Enterprise migration platforms (Flyway Teams, Liquibase Pro) charge per-developer or per-database licensing. Goose, dbmate, and Atlas are all open-source with no licensing costs. For teams managing dozens of databases across environments, the cost savings are significant.

For database management reading, see our [database migration guide](../bytebase-vs-flyway-vs-liquibase-self-hosted-database-migration-guide-2026/) and [zero-downtime MySQL schema migration](../2026-04-29-gh-ost-vs-pt-online-schema-change-vs-mariadb-online-ddl-zero-downtime-mysql-schema-migration-2026/).

## FAQ

### What is the difference between imperative and declarative migrations?

Imperative migrations (Goose, dbmate) describe the steps to change the schema: CREATE TABLE, ADD COLUMN, etc. You write each step explicitly. Declarative migrations (Atlas) describe the desired end state of the schema, and the tool calculates the diff between the current and desired state. Imperative gives you precise control; declarative gives you safety through automatic diff calculation.

### Can I use these tools with multiple databases simultaneously?

Yes. All three tools support running migrations against different database engines using different connection strings. Goose uses the `GOOSE_DRIVER` environment variable, dbmate uses `DATABASE_URL` with engine-specific prefixes, and Atlas uses the `--url` flag. You can maintain the same migration files across PostgreSQL (production), SQLite (testing), and MySQL (staging).

### How do Goose and dbmate handle concurrent migrations?

Both tools use database-level locking to prevent race conditions. Goose uses advisory locks on PostgreSQL and GET_LOCK on MySQL. dbmate uses similar database-specific locking mechanisms. This ensures that if two CI/CD pipeline instances try to run migrations simultaneously, only one proceeds while the other waits.

### Is Atlas backwards compatible with SQL migration files?

Atlas supports both declarative (HCL) and versioned (SQL migration files) modes. You can start with versioned migrations (similar to Goose/dbmate) and gradually migrate to declarative mode. The `atlas migrate apply` command works with standard SQL migration directories, and `atlas migrate diff` generates new migration files from schema changes.

### How do I rollback a migration with these tools?

Goose and dbmate both support rollback through down migrations. Each migration file contains both up and down sections. Run `goose down` or `dbmate down` to revert the last migration. Atlas computes the reverse diff — if you change your HCL schema to remove a table, Atlas generates a DROP TABLE migration. For destructive rollbacks, Atlas lint will warn you before applying.

### Which tool has the smallest binary size?

dbmate and Goose are both single Go binaries, typically 15-25 MB. Atlas is slightly larger at 30-40 MB due to its additional features (HCL parser, linting engine, multiple database drivers). All three are significantly smaller than Flyway (JVM, 200+ MB) or Liquibase (JVM with dependencies, 300+ MB).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Lightweight Database Migrations: Goose vs dbmate vs Atlas (2026)",
  "description": "Compare lightweight database migration tools: Goose, dbmate, and Atlas. Learn which CLI-first tool fits your schema management workflow.",
  "datePublished": "2026-05-14",
  "dateModified": "2026-05-14",
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
