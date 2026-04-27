---
title: "SQLPad vs CloudBeaver vs Adminer: Best Self-Hosted Web SQL Query Editors 2026"
date: 2026-04-27
tags: ["comparison", "guide", "self-hosted", "database", "sql"]
draft: false
description: "Compare SQLPad, CloudBeaver, and Adminer — the top self-hosted web-based SQL query editors. Includes Docker Compose configs, feature comparison, and setup guides for running database query tools on your own server."
---

Managing multiple databases across a team often means installing desktop clients on every machine. A self-hosted web-based SQL query editor solves this: a single server instance, accessible from any browser, with shared saved queries and team collaboration. In this guide, we compare three of the most popular open-source options — SQLPad, CloudBeaver, and Adminer — to help you pick the right tool for your infrastructure.

## Why Self-Host a Web SQL Query Editor?

Desktop database clients like DBeaver, DataGrip, or TablePlus work well for individual developers, but they create friction in team environments:

- **No shared query library** — saved queries live on local machines
- **Access management** — granting database access means distributing credentials
- **Version drift** — team members run different client versions
- **Remote access** — connecting to databases inside a private network requires VPN or SSH tunnels

A self-hosted web SQL editor centralizes access control, provides a shared query library, and works from any device with a browser. All three tools we cover support Docker deployment, making setup straightforward.

## Tool Overview

| Feature | SQLPad | CloudBeaver | Adminer |
|---|---|---|---|
| **GitHub Stars** | 5,187 | 4,828 | N/A (SourceForge) |
| **Last Updated** | Aug 2025 | Apr 2026 | Apr 2026 |
| **Primary Focus** | SQL query writing & sharing | Full database management | Lightweight DB admin |
| **Multi-Database** | PostgreSQL, MySQL, SQL Server, Oracle, SQLite, ClickHouse | PostgreSQL, MySQL, SQLite, Oracle, SQL Server, MongoDB, Redis | PostgreSQL, MySQL, SQLite, Oracle, SQL Server, Elasticsearch, MongoDB |
| **User Management** | Built-in (admin, editor, viewer roles) | Built-in (RBAC, SSO) | Single user per instance |
| **Saved Queries** | Yes, with sharing | Yes, per user | No (manual export) |
| **Collaborative Features** | Query sharing, team workspaces | User permissions, shared connections | None |
| **Charting** | Built-in charts from query results | No native charts | No native charts |
| **Docker Support** | Official image (`sqlpad/sqlpad:5`) | Official image (`dbeaver/cloudbeaver`) | Official image (`adminer`) |
| **Backend Storage** | SQLite, PostgreSQL, MySQL | Embedded H2, external PostgreSQL/MySQL | None (stateless) |
| **License** | MIT | Apache 2.0 | Apache 2.0 / GPL |
| **Language** | Node.js / React | Java | PHP |

## SQLPad: The Collaborative SQL Editor

SQLPad is a Node.js-based web application designed specifically for writing, running, and sharing SQL queries. Its standout feature is the collaborative query workspace — team members can save queries, share them with colleagues, and visualize results as charts.

### Key Features

- **Multi-database support** — Connect to PostgreSQL, MySQL, Microsoft SQL Server, Oracle, SQLite, ClickHouse, and more via a unified interface
- **Query history** — Every executed query is saved and searchable
- **Visualization** — Turn query results into bar charts, line graphs, and scatter plots directly in the browser
- **Team workspaces** — Organize connections and queries by project or team
- **API access** — Programmatic query execution via REST API
- **Seed data support** — Pre-populate demo data for testing

### Docker Compose Setup (with PostgreSQL backend)

SQLPad stores its metadata (saved queries, users, connections) in a backend database. Here is a production-ready compose configuration:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_USER: sqlpad
      POSTGRES_PASSWORD: sqlpad_secure_password
    volumes:
      - sqlpad-db-data:/var/lib/postgresql/data

  sqlpad:
    image: sqlpad/sqlpad:5
    restart: always
    hostname: sqlpad
    ports:
      - "3000:3000"
    environment:
      SQLPAD_ADMIN: "admin@yourdomain.com"
      SQLPAD_ADMIN_PASSWORD: "strong_admin_password"
      SQLPAD_APP_LOG_LEVEL: info
      SQLPAD_WEB_LOG_LEVEL: warn
      SQLPAD_DB_TYPE: postgres
      SQLPAD_DB_HOST: postgres
      SQLPAD_DB_PORT: 5432
      SQLPAD_DB_NAME: sqlpad
      SQLPAD_DB_USERNAME: sqlpad
      SQLPAD_DB_PASSWORD: sqlpad_secure_password
    depends_on:
      - postgres

volumes:
  sqlpad-db-data:
```

Start the stack:

```bash
docker compose up -d
```

Access SQLPad at `http://localhost:3000`. Log in with the admin credentials defined in the environment.

### Adding Database Connections

Once logged in, navigate to **Admin → Connections** and add your databases. SQLPad supports connection variables for multi-tenant setups:

```
SQLPAD_CONNECTIONS__pgprod__name: Production PostgreSQL
SQLPAD_CONNECTIONS__pgprod__driver: postgres
SQLPAD_CONNECTIONS__pgprod__host: db.internal
SQLPAD_CONNECTIONS__pgprod__database: myapp
SQLPAD_CONNECTIONS__pgprod__username: readonly_user
SQLPAD_CONNECTIONS__pgprod__password: ${DB_PASSWORD}
```

## CloudBeaver: Full-Featured Database Management in the Browser

CloudBeaver is the web-based version of the popular DBeaver desktop client. It brings the full DBeaver feature set to the browser, making it ideal for teams that need comprehensive database management — not just query execution.

### Key Features

- **Wide database support** — PostgreSQL, MySQL, SQLite, Oracle, SQL Server, MongoDB, Redis, Cassandra, and 20+ other drivers
- **DBeaver compatibility** — Same interface and features as the desktop client
- **User management** — Role-based access control with admin, manager, and user roles
- **SSO integration** — SAML, LDAP, and OAuth2 authentication
- **Metadata browsing** — Explore schemas, tables, indexes, and procedures visually
- **Data editing** — View and edit table data directly in the browser
- **ER diagrams** — Visual database schema diagrams
- **Task scheduler** — Schedule recurring database tasks

### Docker Compose Setup

```yaml
services:
  cloudbeaver:
    image: dbeaver/cloudbeaver:latest
    restart: always
    ports:
      - "8978:8978"
    volumes:
      - cloudbeaver-data:/opt/cloudbeaver/workspace

volumes:
  cloudbeaver-data:
```

For a production setup with an external PostgreSQL backend:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_USER: cbuser
      POSTGRES_PASSWORD: cb_secure_pass
    volumes:
      - cb-db-data:/var/lib/postgresql/data

  cloudbeaver:
    image: dbeaver/cloudbeaver:latest
    restart: always
    ports:
      - "8978:8978"
    volumes:
      - cloudbeaver-data:/opt/cloudbeaver/workspace
      - ./cloudbeaver.conf:/opt/cloudbeaver/conf/cloudbeaver.conf:ro
    environment:
      CB_SERVER_NAME: "CloudBeaver Server"
      CB_SERVER_URL: "http://localhost:8978"
      CB_DATASOURCES: "postgresql://cbuser:cb_secure_pass@postgres:5432/cloudbeaver"
    depends_on:
      - postgres

volumes:
  cloudbeaver-data:
  cb-db-data:
```

Start and access:

```bash
docker compose up -d
# Access at http://localhost:8978
```

The initial admin login is `admin` / `admin`. Change the password immediately after first login.

## Adminer: The Lightweight, Stateless Option

Adminer (formerly phpMinAdmin) is a single-file PHP database management tool. It is the lightest option of the three — a single PHP file that you drop onto any web server with PHP. Despite its simplicity, it supports many database systems.

### Key Features

- **Single file deployment** — One `adminer.php` file, no installation wizard
- **Minimal resource usage** — Runs on the smallest VPS or container
- **Database support** — MySQL, PostgreSQL, SQLite, Oracle, SQL Server, Elasticsearch, MongoDB, ClickHouse, Firebird, and more via plugins
- **Theme support** — Multiple themes and custom CSS
- **Plugin system** — Extend functionality with plugins (table structure, dump, edit, etc.)
- **Import/Export** — SQL dump import and export in multiple formats
- **Keyboard shortcuts** — Fast navigation for power users

### Docker Compose Setup

Adminer is stateless — it does not store any data. Here is the simplest possible deployment:

```yaml
services:
  adminer:
    image: adminer:latest
    restart: always
    ports:
      - "8080:8080"
```

That is it. Start with `docker compose up -d` and access at `http://localhost:8080`. Enter your database credentials directly in the login form — no pre-configuration needed.

### Nginx Reverse Proxy with HTTPS

For production use, put Adminer behind a reverse proxy:

```nginx
server {
    listen 443 ssl http2;
    server_name db.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/db.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/db.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://adminer:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Adminer Plugins

Adminer's plugin system adds significant functionality. Download the full Adminer package (not just the single file) to access plugins:

```php
<?php
// adminer.php with plugins
function adminer_object() {
    require_once 'plugins/plugin.php';

    class Adminer extends AdminerPlugin {
        function login($login, $password) {
            // Restrict to specific IP range
            if ($_SERVER['REMOTE_ADDR'] !== '10.0.0.1') {
                return false;
            }
            return true;
        }
    }

    return new Adminer([
        new AdminerLoginServers(['Primary' => 'db-primary:3306', 'Replica' => 'db-replica:3306']),
    ]);
}

require 'adminer-4.8.1.php';
```

## Feature Comparison: Detailed Breakdown

### Query Execution and Results

| Capability | SQLPad | CloudBeaver | Adminer |
|---|---|---|---|
| Multi-statement queries | Yes | Yes | Yes |
| Query history | Yes (searchable) | Yes (per user) | No |
| Result pagination | Yes | Yes | Yes |
| Export results (CSV, JSON) | Yes | Yes | Yes |
| Result visualization (charts) | Yes | No | No |
| Query plan / EXPLAIN | No | Yes | Partial |

### Collaboration and Access Control

| Capability | SQLPad | CloudBeaver | Adminer |
|---|---|---|---|
| Multi-user support | Yes | Yes | Single user |
| Role-based access | Yes (3 roles) | Yes (granular RBAC) | No |
| Query sharing | Yes | Per-user only | No |
| SSO / SAML | No | Yes | No |
| LDAP integration | No | Yes | No |
| Audit logging | No | Yes | No |

### Deployment and Maintenance

| Capability | SQLPad | CloudBeaver | Adminer |
|---|---|---|---|
| Resource requirements | ~256MB RAM | ~512MB RAM | ~64MB RAM |
| Backend dependency | SQLite or PostgreSQL | Embedded H2 or external DB | None |
| Upgrade process | Pull new image | Pull new image | Replace PHP file |
| Backup strategy | Backup backend DB | Backup workspace volume | Stateless (no backup) |
| Horizontal scaling | Yes (shared backend DB) | No (stateful workspace) | Yes (stateless) |

## Which One Should You Choose?

**Choose SQLPad if:**
- Your team needs a shared SQL query workspace with saved queries and charts
- You want built-in user roles and query sharing
- You prefer a Node.js-based application

**Choose CloudBeaver if:**
- You need full database management (ER diagrams, data editing, schema browsing)
- You require SSO/LDAP integration for enterprise authentication
- Your team already uses DBeaver desktop and wants the web equivalent
- You need to manage diverse database types (including MongoDB, Redis, Cassandra)

**Choose Adminer if:**
- You want the simplest possible deployment (single container, no backend)
- Resource constraints are tight (runs on minimal hardware)
- You need a quick, temporary database management interface
- You prefer PHP-based tooling

For most teams, **CloudBeaver** offers the best balance of features and usability. For SQL-focused teams that primarily write and share queries, **SQLPad** provides the best collaborative experience. For quick, lightweight access, **Adminer** cannot be beat.

## FAQ

### Can these tools connect to databases inside a private network?

Yes. Since the tools run on a server inside your network, the web application connects to databases via internal hostnames or IP addresses. Users access the web UI through a browser, which only needs network reachability to the server hosting the SQL editor — not to the databases directly.

### Is it safe to expose these tools to the internet?

SQLPad and CloudBeaver have built-in user authentication, but exposing any database tool to the public internet carries risk. Best practice is to place the tool behind a reverse proxy with TLS termination, restrict access by IP address, and use strong passwords or SSO. Adminer is especially risky to expose publicly since it has no built-in authentication — always put it behind a proxy with HTTP Basic Auth or similar.

### Can I migrate saved queries between tools?

Not directly. Each tool stores queries in its own format. SQLPad stores queries in its backend database (SQLite or PostgreSQL), CloudBeaver in its workspace storage, and Adminer does not save queries. You can export results as SQL files and re-import them manually, but there is no automated migration path.

### Do these tools support read-only database connections?

Yes. All three tools can connect to databases using read-only credentials. This is the recommended approach for query editor instances — create a dedicated read-only database user and use those credentials in the connection configuration. This prevents accidental data modification through the web interface.

### How do I back up SQLPad's saved queries?

SQLPad stores its data (users, connections, saved queries) in its backend database. If you are using the default SQLite backend, back up the SQLite file. If you are using PostgreSQL (as shown in the Docker Compose example above), use `pg_dump`:

```bash
docker compose exec postgres pg_dump -U sqlpad sqlpad > sqlpad-backup.sql
```

Restore with:

```bash
docker compose exec -T postgres psql -U sqlpad sqlpad < sqlpad-backup.sql
```

## Further Reading

For related database management tools, see our [self-hosted database GUI comparison](../self-hosted-database-gui-tools-cloudbeaver-adminer-dbeaver-g/) covering CloudBeaver, Adminer, and DBeaver in a broader context. If you are evaluating database engines, our [PostgreSQL vs MariaDB vs Firebird comparison](../firebird-vs-postgresql-vs-mariadb-self-hosted-sql-database-guide-2026/) provides a detailed breakdown of open-source relational databases.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "SQLPad vs CloudBeaver vs Adminer: Best Self-Hosted Web SQL Query Editors 2026",
  "description": "Compare SQLPad, CloudBeaver, and Adminer — the top self-hosted web-based SQL query editors. Includes Docker Compose configs, feature comparison, and setup guides for running database query tools on your own server.",
  "datePublished": "2026-04-27",
  "dateModified": "2026-04-27",
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
