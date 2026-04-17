---
title: "Bytebase vs Flyway vs Liquibase: Best Self-Hosted Database Migration Tools 2026"
date: 2026-04-17
tags: ["comparison", "guide", "self-hosted", "database", "devops"]
draft: false
description: "Complete comparison of Bytebase, Flyway, and Liquibase for self-hosted database schema migrations. Includes Docker setup, configuration examples, and best practices for teams in 2026."
---

Managing database schema changes across multiple environments is one of the most error-prone aspects of software development. Without a proper migration strategy, teams risk data loss, downtime, and inconsistent database states between development, staging, and production. This guide compares three leading open-source database migration tools — Bytebase, Flyway, and Liquibase — and shows you how to set each one up in a self-hosted environment.

## Why Self-Host Your Database Migration Tool?

Database migration tools sit at the critical junction between your codebase and your data. Here is why running them on your own infrastructure matters:

- **Schema security:** Your database schema often reveals business logic, data relationships, and architectural decisions. Keeping migrations on your own servers prevents third-party exposure.
- **Network access:** Migration tools need direct connectivity to your databases. Self-hosting eliminates the need to open database ports to external SaaS platforms.
- **Compliance:** Industries like healthcare and finance require audit trails and data residency controls that only self-hosted solutions can guarantee.
- **No vendor lock-in:** Open-source migration tools store your schema history in plain files or your own database, giving you full ownership of the migration process.
- **Cost predictability:** Self-hosted solutions eliminate per-user or per-database licensing fees that scale unpredictably with team growth.

## Overview: Three Approaches to Database Migrations

Each tool represents a different philosophy for managing schema changes.

**Flyway** takes the simplest approach: plain SQL migration files executed in order. It is lightweight, fast, and works with almost any SQL you can write. Flyway is ideal for teams that want minimal abstraction and maximum control over their SQL.

**Liquibase** uses declarative changelog files in XML, YAML, JSON, or SQL format. It abstracts database-specific SQL behind a common format, making it easier to support multiple database engines from a single changelog. Liquibase also offers rollback capabilities and detailed change tracking.

**Bytebase** goes beyond file-based migrations to provide a full database DevOps platform. It includes a web UI for reviewing and approving schema changes, built-in SQL review policies, environment management, and GitOps integration. Bytebase is designed for teams that need governance and collaboration around database changes.

## Feature Comparison

| Feature | Flyway | Liquibase | Bytebase |
|---------|--------|-----------|----------|
| **Primary format** | SQL files | XML/YAML/JSON/SQL | SQL + UI + GitOps |
| **Web UI** | No (Flyway Teams only) | No (Liquibase Pro only) | Yes (open-source) |
| **Database support** | 13+ databases | 14+ databases | 15+ databases |
| **Rollback support** | Community: limited | Full rollback tags | Built-in undo |
| **SQL review** | No | No | Yes (built-in) |
| **Approval workflows** | No | No | Yes |
| **Environment management** | Via config files | Via contexts/labels | Visual environment UI |
| **GitOps integration** | Via CI/CD scripts | Via CI/CD scripts | Native GitOps sync |
| **Schema drift detection** | No | Limited (Diff command) | Yes (continuous) |
| **Audit log** | Migration history table | Database changelog table | Full audit trail in UI |
| **License** | Apache 2.0 (core) | Apache 2.0 (core) | MIT |
| **Docker image** | flyway/flyway | liquibase/liquibase | bytebase/bytebase |

## Flyway: SQL-First Migrations

### Installation via Docker

The quickest way to run Flyway is through its official Docker image:

```bash
docker run --rm \
  -v $(pwd)/migrations:/flyway/sql \
  -v $(pwd)/flyway.conf:/flyway/conf/flyway.conf \
  flyway/flyway:10 migrate
```

### Docker Compose Setup

For a production-ready setup with PostgreSQL:

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: appdb
      POSTGRES_USER: appuser
      POSTGRES_PASSWORD: changeme123
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  flyway:
    image: flyway/flyway:10
    command: -url=jdbc:postgresql://postgres:5432/appdb -user=appuser -password=changeme123 migrate
    volumes:
      - ./migrations:/flyway/sql
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  pgdata:
```

### Migration File Structure

Flyway migrations follow a strict naming convention: `V<version>__<description>.sql`

```
migrations/
├── V1__create_users_table.sql
├── V2__add_email_index.sql
├── V3__create_orders_table.sql
└── V4__add_order_status_column.sql
```

Example migration file (`V1__create_users_table.sql`):

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
```

### Configuration

Create `flyway.conf` for reusable settings:

```properties
flyway.url=jdbc:postgresql://localhost:5432/appdb
flyway.user=appuser
flyway.password=changeme123
flyway.locations=filesystem:./migrations
flyway.table=schema_version
flyway.baselineOnMigrate=true
flyway.validateOnMigrate=true
```

### CI/CD Integration

A GitHub Actions workflow for Flyway:

```yaml
name: Database Migrations

on:
  push:
    paths:
      - 'migrations/**'

jobs:
  migrate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Flyway Migrate
        uses: docker://flyway/flyway:10
        with:
          args: >-
            -url=${{ secrets.DB_URL }}
            -user=${{ secrets.DB_USER }}
            -password=${{ secrets.DB_PASSWORD }}
            migrate

      - name: Validate Schema
        uses: docker://flyway/flyway:10
        with:
          args: >-
            -url=${{ secrets.DB_URL }}
            -user=${{ secrets.DB_USER }}
            -password=${{ secrets.DB_PASSWORD }}
            validate
```

### When to Choose Flyway

- You prefer writing raw SQL and want zero abstraction overhead
- Your team works primarily with one database engine
- You need a lightweight tool that integrates easily into existing CI/CD pipelines
- Your migration workflow is linear (no complex branching or rollback needs)

## Liquibase: Multi-Database Changelogs

### Installation via Docker

```bash
docker run --rm \
  -v $(pwd)/changelog:/liquibase/changelog \
  liquibase/liquibase:4.27 \
  --url=jdbc:postgresql://host.docker.internal:5432/appdb \
  --username=appuser \
  --password=changeme123 \
  --changelog-file=changelog/main.yaml \
  update
```

### Docker Compose Setup

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: appdb
      POSTGRES_USER: appuser
      POSTGRES_PASSWORD: changeme123
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U appuser"]
      interval: 5s
      retries: 5

  liquibase:
    image: liquibase/liquibase:4.27
    command: >
      --url=jdbc:postgresql://postgres:5432/appdb
      --username=appuser
      --password=changeme123
      --changelog-file=changelog/main.yaml
      update
    volumes:
      - ./changelog:/liquibase/changelog
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  pgdata:
```

### Changelog Structure

Liquibase uses a master changelog that includes individual change files:

```
changelog/
├── main.yaml
└── changes/
    ├── 001-create-users.yaml
    ├── 002-create-products.yaml
    └── 003-add-foreign-keys.yaml
```

Master changelog (`changelog/main.yaml`):

```yaml
databaseChangeLog:
  - include:
      file: changes/001-create-users.yaml
  - include:
      file: changes/002-create-products.yaml
  - include:
      file: changes/003-add-foreign-keys.yaml
```

### Example Changeset (YAML format)

```yaml
# changes/001-create-users.yaml
databaseChangeLog:
  - changeSet:
      id: 001-create-users
      author: dev-team
      changes:
        - createTable:
            tableName: users
            columns:
              - column:
                  name: id
                  type: int
                  autoIncrement: true
                  constraints:
                    primaryKey: true
              - column:
                  name: username
                  type: varchar(255)
                  constraints:
                    nullable: false
                    unique: true
              - column:
                  name: email
                  type: varchar(255)
                  constraints:
                    nullable: false
                    unique: true
              - column:
                  name: created_at
                  type: timestamp
                  defaultValueComputed: CURRENT_TIMESTAMP

        - addUniqueConstraint:
            tableName: users
            columnNames: email
            constraintName: uq_users_email
```

### Rollback Configuration

One of Liquibase's strongest features is its rollback support:

```yaml
  - changeSet:
      id: 004-add-user-status
      author: dev-team
      changes:
        - addColumn:
            tableName: users
            columns:
              - column:
                  name: status
                  type: varchar(20)
                  defaultValue: active
      rollback:
        - dropColumn:
            tableName: users
            columnName: status
```

### Liquibase Properties File

Create `liquibase.properties` for reusable configuration:

```properties
url: jdbc:postgresql://localhost:5432/appdb
username: appuser
password: changeme123
changelogFile: changelog/main.yaml
defaultSchemaName: public
```

### Generate Diff from Existing Database

Liquibase can compare two databases and generate a changelog:

```bash
docker run --rm \
  -v $(pwd)/changelog:/liquibase/changelog \
  liquibase/liquibase:4.27 \
  --referenceUrl=jdbc:postgresql://prod-host:5432/appdb \
  --referenceUsername=appuser \
  --referencePassword=changeme123 \
  --url=jdbc:postgresql://staging-host:5432/appdb \
  --username=appuser \
  --password=changeme123 \
  diffChangeLog --changelog-file=changelog/diff-output.yaml
```

### When to Choose Liquibase

- Your application supports multiple database engines and you want a single changelog format
- You need reliable rollback capabilities for schema changes
- Your team prefers declarative changelog files over raw SQL
- You want to generate diffs between database states automatically

## Bytebase: Database DevOps Platform

### Installation via Docker

Bytebase provides a full web-based UI for managing database changes:

```bash
docker run --init \
  --name bytebase \
  --restart always \
  --publish 8080:8080 \
  --health-cmd "curl -f http://localhost:8080/healthz || exit 1" \
  --health-interval 5m \
  --health-timeout 60s \
  --volume $(pwd)/bbdata:/var/opt/bytebase \
  bytebase/bytebase:2.27.0 \
  --data /var/opt/bytebase \
  --port 8080
```

### Docker Compose with External PostgreSQL

For production, use an external PostgreSQL database for Bytebase's own metadata:

```yaml
version: "3.9"

services:
  bytebase-db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: bytebase
      POSTGRES_USER: bbadmin
      POSTGRES_PASSWORD: bytebase_secret_pass
    volumes:
      - bbdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U bbadmin"]
      interval: 10s
      retries: 5

  bytebase:
    image: bytebase/bytebase:2.27.0
    ports:
      - "8080:8080"
    volumes:
      - ./bb-data:/var/opt/bytebase
    command: [
      "--data", "/var/opt/bytebase",
      "--port", "8080",
      "--external-db-host", "bytebase-db",
      "--external-db-port", "5432",
      "--external-db-username", "bbadmin",
      "--external-db-password", "bytebase_secret_pass",
      "--external-db-name", "bytebase"
    ]
    depends_on:
      bytebase-db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/healthz"]
      interval: 30s
      retries: 3

volumes:
  bbdata:
```

### Setting Up Your First Project

After starting Bytebase, access the web UI at `http://localhost:8080`. The initial setup wizard will guide you through:

1. Creating an admin account
2. Adding your first database instance (PostgreSQL, MySQL, MongoDB, etc.)
3. Creating a project and assigning environments (dev, staging, prod)
4. Connecting a Git repository for GitOps-based migrations

### GitOps Mode

Bytebase's GitOps mode syncs SQL migration files from your Git repository to managed databases. Create a `.bytebase` configuration file at the root of your repository:

```yaml
# .bytebase/config.yaml
environments:
  - name: dev
    databases:
      - host: dev-db.internal
        name: appdb
        port: 5432
  - name: staging
    databases:
      - host: staging-db.internal
        name: appdb
        port: 5432
  - name: prod
    databases:
      - host: prod-db.internal
        name: appdb
        port: 5432
```

Then organize your SQL files by environment:

```
database-migrations/
├── dev/
│   └── V001__initial_schema.sql
├── staging/
│   └── V001__initial_schema.sql
└── prod/
    └── V001__initial_schema.sql
```

### SQL Review Policies

Bytebase includes a built-in SQL review engine. You can configure policies such as:

```
# In the Bytebase UI → Settings → SQL Review

Policy: Require INDEX on foreign key columns
Severity: ERROR
Engine: MySQL, PostgreSQL
Description: All foreign key columns must have an index

Policy: Prevent DROP TABLE in production
Severity: ERROR
Engine: All
Environment: prod

Policy: Limit row count on SELECT without WHERE
Severity: WARNING
Engine: PostgreSQL
MaxRows: 10000
```

### Approval Workflow

Bytebase supports multi-stage approval workflows for production changes:

1. Developer creates a migration issue in the UI or pushes SQL to a Git branch
2. The SQL review policy automatically validates the change
3. A designated reviewer approves the migration
4. Bytebase executes the migration during the approved maintenance window
5. The audit log records who approved what, when, and the execution result

### API Integration

Bytebase provides a REST API for automation:

```bash
# Create a new issue for a schema change
curl -X POST http://localhost:8080/v1/issues \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project": "projects/my-project",
    "type": "DATABASE_CHANGE",
    "database": "instances/prod/databases/appdb",
    "statement": "ALTER TABLE users ADD COLUMN phone VARCHAR(20);",
    "description": "Add phone column for user profiles"
  }'
```

### When to Choose Bytebase

- You need a visual interface for managing database changes across multiple teams
- SQL review and approval workflows are required for compliance
- You want GitOps integration with automatic sync from Git to databases
- Schema drift detection between environments is important
- You manage many databases and need centralized oversight

## Choosing the Right Tool

| Scenario | Recommended Tool |
|----------|-----------------|
| Solo developer, simple SQL migrations | Flyway |
| Multi-database application with rollback needs | Liquibase |
| Team with compliance and governance requirements | Bytebase |
| CI/CD pipeline with minimal overhead | Flyway |
| Database-agnostic changelog management | Liquibase |
| Visual database administration and collaboration | Bytebase |
| GitOps-driven database changes | Bytebase |
| Fast migrations with zero runtime dependencies | Flyway |
| Automatic diff generation between databases | Liquibase |

## Best Practices for Self-Hosted Database Migrations

### Version Control Everything

Store all migration files in your version control system. Never apply ad-hoc SQL directly to production. Every schema change should have a corresponding migration file with a clear description.

### Use Transactions for Migrations

Wrap your migration SQL in transactions when your database supports it. This ensures that failed migrations do not leave your schema in a partially applied state:

```sql
-- PostgreSQL supports transactional DDL
BEGIN;

CREATE TABLE user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    theme VARCHAR(50) DEFAULT 'dark',
    notifications_enabled BOOLEAN DEFAULT true
);

ALTER TABLE users ADD COLUMN preferences JSONB;

COMMIT;
```

### Test Migrations Against a Copy of Production Data

Before running migrations in production, test them against a sanitized copy of your production database. This catches issues that unit tests might miss, such as data type incompatibilities or constraint violations.

### Use Separate Migration Runs per Environment

Never share migration state between environments. Each environment should have its own migration history table and its own execution of the migration tool. This prevents a migration that works in development from failing silently in production.

### Monitor Migration Execution Time

Large tables can make schema changes slow. Track how long each migration takes and set up alerts for migrations that exceed expected durations:

```bash
# Flyway: check migration timing
docker run --rm \
  -v $(pwd)/migrations:/flyway/sql \
  flyway/flyway:10 \
  -url=jdbc:postgresql://localhost:5432/appdb \
  -user=appuser -password=changeme123 \
  info
```

### Back Up Before Major Migrations

Always create a database backup before running destructive migrations:

```bash
# PostgreSQL backup before migration
pg_dump -h localhost -U appuser -d appdb -F c -f backup_$(date +%Y%m%d).dump

# Run migration
flyway migrate

# If something goes wrong, restore
pg_restore -h localhost -U appuser -d appdb backup_$(date +%Y%m%d).dump
```

## Conclusion

The choice between Bytebase, Flyway, and Liquibase comes down to your team's workflow and governance needs. Flyway is the simplest option for teams comfortable writing raw SQL. Liquibase provides database-agnostic changelog management with strong rollback support. Bytebase offers a complete database DevOps platform with visual management, SQL review, and approval workflows.

All three tools can be self-hosted via Docker, giving you full control over your migration infrastructure. Start with the tool that matches your current complexity, and migrate to a more feature-rich option as your team and database estate grow.
