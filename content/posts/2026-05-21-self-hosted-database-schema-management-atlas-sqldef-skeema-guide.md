---
title: "Self-Hosted Database Schema Management: Atlas vs sqldef vs Skeema (2026)"
date: "2026-05-21"
tags: ["database", "schema-management", "ddl", "self-hosted", "mysql", "postgresql", "devops"]
draft: false
---

Managing database schemas across development, staging, and production environments is one of the most persistent challenges in modern software engineering. Schema drift, manual SQL changes, and inconsistent migration practices lead to deployment failures, data loss, and hours of debugging. This guide compares three self-hosted, open-source tools that solve this problem with fundamentally different approaches: **Atlas**, **sqldef**, and **Skeema**.

## The Database Schema Problem

Every database-driven application needs a reliable way to evolve its schema over time. Traditional migration tools use imperative approaches — you write "up" and "down" SQL scripts and trust that running them in order produces the desired state. This works for small teams but breaks down as databases grow: scripts drift from reality, rollbacks become unreliable, and coordinating changes across multiple databases becomes error-prone.

Declarative schema management tools take a different approach. You define the desired schema state, and the tool calculates the diff between your definition and the live database, generating the necessary migration SQL automatically. This eliminates script drift, makes rollbacks predictable, and enables schema-as-code workflows that integrate cleanly with CI/CD pipelines.

For broader database schema comparison and migration frameworks, see our [database schema diff guide](../2026-05-09-self-hosted-database-schema-diff-comparison-sqitch-flyway-liquibase-guide/) and [zero-downtime MySQL schema migration comparison](../2026-04-29-gh-ost-vs-pt-online-schema-change-vs-mariadb-online-ddl-zero-downtime-mysql-schema-migration-2026/).

## Atlas (Ariga)

[Atlas](https://atlasgo.io/) by Ariga is a modern, database-agnostic schema management tool that supports MySQL, PostgreSQL, SQLite, MariaDB, and SQL Server. It uses a declarative "schema-as-code" approach with its own HCL-based schema definition language (HCL), and also supports loading schemas from existing databases or ORM frameworks like Prisma, Ent, and GORM.

**Key Features:**
- **Declarative HCL schema definition** — write schemas in a concise, database-agnostic HCL format
- **`schema apply` and `schema diff`** — apply changes directly or preview the generated SQL
- **Migration directory** — version-controlled migration files with hash-based integrity checking
- **Multi-database support** — MySQL, PostgreSQL, SQLite, MariaDB, SQL Server
- **ORM integration** — automatically load schemas from Prisma, Ent, GORM, and SQLAlchemy
- **Cloud integration** — optional Atlas Cloud for team collaboration and CI/CD

**Installation via Docker:**
```bash
docker run --rm -it arigaio/atlas:latest schema inspect \
  -u "mysql://root:password@localhost:3306/mydb" \
  --format '{{ json . }}'
```

**Example HCL schema:**
```hcl
table "users" {
  schema = schema.public
  column "id" {
    type = bigint
    identity {
      generated = ALWAYS
    }
  }
  column "email" {
    type = varchar(255)
  }
  column "created_at" {
    type    = timestamp
    default = sql("CURRENT_TIMESTAMP")
  }
  primary_key {
    columns = [column.id]
  }
  index "idx_email" {
    columns = [column.email]
    unique  = true
  }
}
```

**Apply schema to live database:**
```bash
atlas schema apply \
  -u "mysql://root:password@localhost:3306/mydb" \
  -f atlas.hcl \
  --dev-url "docker://mysql/8/mydb"
```

The `--dev-url` flag uses a temporary Docker container to safely plan migrations without connecting to your production database.

## sqldef

[sqldef](https://github.com/k0kubun/sqldef) is a lightweight, open-source schema management tool written in Go. It supports MySQL, PostgreSQL, SQLite, SQL Server, and even Redis (for key schema). Unlike Atlas, sqldef uses raw SQL DDL as its source of truth — you write standard `CREATE TABLE` and `ALTER TABLE` statements, and sqldef compares them against the live database.

**Key Features:**
- **SQL-first** — use standard SQL DDL as your schema definition, no new DSL to learn
- **Lightweight binary** — single Go binary with zero dependencies, ~15MB
- **Dry-run mode** — preview the generated SQL without applying changes
- **Export mode** — dump existing database schema as SQL DDL
- **Multi-database support** — MySQL, PostgreSQL, SQLite, SQL Server, Redis
- **CI/CD friendly** — simple CLI, easy to integrate into pipelines

**Installation:**
```bash
# Download the binary
curl -L https://github.com/k0kubun/sqldef/releases/latest/download/mysqldef_linux_amd64.tar.gz \
  -o mysqldef.tar.gz
tar xzf mysqldef.tar.gz
sudo mv mysqldef /usr/local/bin/
```

**Define your schema in a SQL file:**
```sql
CREATE TABLE users (
  id BIGINT NOT NULL AUTO_INCREMENT,
  email VARCHAR(255) NOT NULL,
  name VARCHAR(100),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY idx_email (email)
);

CREATE TABLE posts (
  id BIGINT NOT NULL AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  title VARCHAR(255) NOT NULL,
  body TEXT,
  published_at TIMESTAMP NULL,
  PRIMARY KEY (id),
  INDEX idx_user_id (user_id),
  FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**Apply the schema:**
```bash
# MySQL
mysqldef -u root -p password mydb < schema.sql

# PostgreSQL
psqldef -U postgres -d mydb < schema.sql

# Dry run (preview changes)
mysqldef --dry-run -u root -p password mydb < schema.sql

# Export current schema
mysqldef --export -u root -p password mydb > current_schema.sql
```

sqldef's approach is elegantly simple: write standard SQL, let the tool figure out the diff. There's no migration directory, no version tracking — just the desired state and the live database.

## Skeema

[Skeema](https://github.com/skeema/skeema) is a declarative, pure-SQL schema management tool built specifically for MySQL and MariaDB. Unlike Atlas and sqldef, Skeema is designed for enterprise-scale database operations with complex sharding, multiple environments, and strict governance requirements.

**Key Features:**
- **Pure SQL** — schema files are plain `.sql` files, no custom DSL
- **Directory-based organization** — one directory per database, one file per table
- **Flavor support** — MySQL 5.7+, MySQL 8.0+, MariaDB 10.x
- **Workspace management** — diff across multiple environments simultaneously
- **CI/CD integration** — lint, format, and validate schemas in pipelines
- **Sharding support** — manage schemas across multiple MySQL instances
- **Safe ALTER support** — online DDL with pt-online-schema-change and gh-ost integration

**Installation via Docker:**
```bash
docker run --rm -it skeema/skeema init \
  --host=mysql.example.com \
  --schema=mydb \
  --user=root \
  --password=secret
```

**Directory structure after init:**
```
mydb/
├── .skeema
├── users.sql
├── posts.sql
└── comments.sql
```

**Each `.sql` file contains standard DDL:**
```sql
CREATE TABLE `users` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `email` varchar(255) NOT NULL,
  `name` varchar(100) DEFAULT NULL,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Diff and apply:**
```bash
# Show pending changes
skeema diff --host=mysql.example.com --schema=mydb

# Apply changes
skeema push --host=mysql.example.com --schema=mydb

# Lint schemas (CI/CD)
skeema lint --host=mysql.example.com --schema=mydb

# Format SQL files
skeema format
```

Skeema's `.skeema` configuration file stores connection details per environment, making it easy to manage dev, staging, and production schemas from the same directory tree.

## Comparison Table

| Feature | Atlas | sqldef | Skeema |
|---------|-------|--------|--------|
| **License** | Apache 2.0 (core) | MIT | Apache 2.0 |
| **Database Support** | MySQL, PostgreSQL, SQLite, MariaDB, SQL Server | MySQL, PostgreSQL, SQLite, SQL Server, Redis | MySQL, MariaDB only |
| **Schema Format** | HCL (custom DSL) | Raw SQL DDL | Raw SQL DDL |
| **Migration Tracking** | Versioned migration directory | None (desired state only) | None (desired state only) |
| **ORM Integration** | Prisma, Ent, GORM, SQLAlchemy | None | None |
| **Docker Image** | `arigaio/atlas` | Binary download | `skeema/skeema` |
| **Stars (GitHub)** | 8,400+ | 3,000+ | 1,300+ |
| **Online DDL** | Via dev URL planning | None built-in | pt-osc and gh-ost integration |
| **Multi-Environment** | Via separate HCL files | Manual per-environment | Built-in workspace support |
| **CI/CD Linting** | `atlas schema lint` | None | `skeema lint` |
| **Best For** | Teams wanting schema-as-code + ORM integration | Developers who prefer raw SQL | Enterprise MySQL/MariaDB ops |

## Choosing the Right Tool

**Choose Atlas if:**
- You work with multiple database types (MySQL, PostgreSQL, SQLite)
- Your team uses ORMs (Prisma, Ent, GORM) and wants schema sync
- You want versioned migration directories with integrity checking
- You need a modern, actively developed tool with cloud integration

**Choose sqldef if:**
- You want the simplest possible workflow — just SQL files
- You prefer lightweight tools with zero dependencies
- Your team knows SQL and doesn't want to learn a new DSL
- You need quick schema diffs in CI/CD pipelines

**Choose Skeema if:**
- You run MySQL or MariaDB at scale (sharding, multiple environments)
- You need enterprise features like workspace management and linting
- Your team uses online DDL (pt-osc, gh-ost) for zero-downtime migrations
- You want directory-per-table organization for large schemas

## Docker Compose Deployment

Here's a complete Docker Compose setup for testing all three tools:

```yaml
version: "3.8"
services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: mydb
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql

  postgres:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: pgpass
      POSTGRES_DB: mydb
    ports:
      - "5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data

  atlas:
    image: arigaio/atlas:latest
    depends_on:
      - mysql
    command: >
      schema apply
      -u "mysql://root:rootpass@mysql:3306/mydb"
      -f /schema/atlas.hcl
      --dev-url "docker://mysql/8/mydb"
    volumes:
      - ./atlas.hcl:/schema/atlas.hcl:ro

  skeema:
    image: skeema/skeema
    depends_on:
      - mysql
    command: push --host=mysql --schema=mydb --user=root --password=rootpass
    volumes:
      - ./mydb:/mydb:ro

volumes:
  mysql_data:
  pg_data:
```

## Why Self-Host Schema Management Tools?

Database schema management is a critical part of any software delivery pipeline. Using cloud-hosted or SaaS schema management tools introduces several risks:

**Data sovereignty and compliance:** Your schema definitions contain sensitive information about your data model, including table names, column types, and relationships. For organizations subject to GDPR, HIPAA, or SOC 2 compliance, keeping schema management on-premises ensures that this metadata never leaves your infrastructure.

**CI/CD pipeline integration:** Self-hosted schema tools integrate directly into your existing CI/CD pipelines without requiring API tokens, network access to external services, or vendor-specific authentication. This makes schema validation a native part of your build process rather than an external dependency.

**Cost and vendor lock-in:** Open-source schema management tools are free to use and modify. You're not locked into a vendor's pricing model or feature roadmap. If a tool doesn't meet your needs, you can fork it, contribute upstream, or switch to an alternative without data migration overhead.

**Offline and air-gapped environments:** Many enterprise environments operate in air-gapped or restricted network zones. Self-hosted schema tools work entirely offline once installed, making them suitable for environments where external API calls are prohibited.

For database query routing strategies that complement schema management, see our [database query routing guide](../2026-05-10-database-query-routing-mysql-router-maxscale-proxysql-guide/). For PostgreSQL-specific high-availability patterns, check our [PostgreSQL operators guide](../2026-05-10-self-hosted-postgresql-operators-cloudnativepg-zalando-crunchydata-guide/).

## FAQ

### What is declarative database schema management?
Declarative schema management means you define the desired end state of your database schema (tables, columns, indexes, constraints), and the tool automatically calculates the SQL changes needed to get from the current state to the desired state. This contrasts with imperative migration tools where you manually write each ALTER TABLE statement.

### Can Atlas manage schemas for multiple database types?
Yes. Atlas supports MySQL, PostgreSQL, SQLite, MariaDB, and SQL Server through a unified HCL schema definition language. It also integrates with ORM frameworks (Prisma, Ent, GORM, SQLAlchemy) to automatically load and manage schemas from application code.

### Does sqldef track migration versions?
No. sqldef operates purely on desired-state comparison. You write the complete current schema in a SQL file, and sqldef compares it against the live database to determine what changes are needed. There's no version history or migration directory — this is by design for simplicity.

### Is Skeema suitable for PostgreSQL?
No. Skeema is purpose-built for MySQL and MariaDB only. It leverages MySQL-specific features like the INFORMATION_SCHEMA structure, MySQL's online DDL capabilities, and integration with pt-online-schema-change and gh-ost. For PostgreSQL schema management, consider Atlas or sqldef.

### How do these tools handle production deployments?
Atlas uses a "dev URL" approach — it spins up a temporary Docker container to safely plan migrations without connecting to production. sqldef offers a `--dry-run` flag to preview changes before applying. Skeema supports integration with pt-online-schema-change and gh-ost for zero-downtime schema changes on large MySQL tables.

### Can I use these tools in a CI/CD pipeline?
All three tools are designed for CI/CD integration. Atlas provides `atlas schema lint` and `atlas schema diff` commands for pipeline validation. sqldef is a single binary with simple CLI flags. Skeema includes `skeema lint`, `skeema format`, and `skeema diff` for automated schema checks in build pipelines.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Database Schema Management: Atlas vs sqldef vs Skeema (2026)",
  "description": "Compare three open-source database schema management tools — Atlas (Ariga), sqldef, and Skeema — for declarative DDL, CI/CD integration, and enterprise database operations.",
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
