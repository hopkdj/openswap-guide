---
title: "Best Self-Hosted Low-Code Platforms 2026: Appsmith vs Budibase vs ToolJet"
date: 2026-04-12
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Compare the best open-source low-code platforms for building internal tools, admin panels, and dashboards in 2026. Full Docker deployment guides, feature comparisons, and hands-on setup instructions."
---

Building internal tools, admin panels, and operational dashboards is one of the most common needs for engineering teams. Commercial solutions like Retool, Internal.io, and Superblocks charge per user and store your data on their infrastructure. For teams that need full control over their data, network access, and deployment, self-hosted open-source alternatives are the answer.

This guide compares the three leading open-source low-code platforms: **Appsmith**, **Budibase**, and **ToolJet**. We'll cover features, deployment, integrations, pricing, and walk through production-ready Docker setups for each.

## Why Self-Host Your Internal Tool Platform?

Internal tools often connect to your most sensitive data sources: production databases, customer records, financial systems, and operational infrastructure. Handing that access to a third-party SaaS provider introduces several risks:

- **Data sovereignty**: Your queries, credentials, and result sets pass through external servers. Many industries (healthcare, finance, government) have strict compliance requirements that SaaS platforms cannot satisfy.
- **Network access**: Self-hosting lets your tool platform sit inside your private network with direct access to databases, APIs, and services that are not exposed to the internet.
- **Cost at scale**: SaaS pricing is typically per-user, per-month. A 30-person ops team can easily cost $900–$1,500/month on a commercial platform. Self-hosted alternatives eliminate per-seat fees entirely.
- **Customization limits**: SaaS platforms restrict what you can build. Self-hosted platforms let you modify the source code, add custom widgets, and integrate with any internal system.
- **Vendor lock-in**: Building your tooling on a platform you own means you're never forced to migrate when pricing changes or features get deprecated.

The three platforms covered here are all open-source, Docker-deployable, and production-ready. Each takes a slightly different approach to the same problem.

## Platform Overview

### Appsmith

Appsmith is the most mature and widely adopted open-source internal tool builder. With over 35,000 GitHub stars, it offers a drag-and-drop UI builder, JavaScript-based query language, and extensive integration support. It closely mirrors Retool's workflow, making it familiar to developers who have used commercial platforms.

Appsmith uses a widget-based canvas where you place inputs, tables, charts, and forms. Each widget is bound to queries and JavaScript expressions. The platform supports SQL databases, REST APIs, GraphQL, and many third-party connectors out of the box.

### Budibase

Budibase takes a different approach by providing a full-stack application builder. Rather than just wiring UI to existing data, Budibase includes its own internal database layer, a visual automation/workflow engine, and a built-in design system. It feels more like a rapid application development platform than a simple internal tool builder.

Budibase excels at CRUD applications, approval workflows, and data-driven portals. Its automation engine can trigger actions on data changes, schedule tasks, and integrate with external services via webhooks.

### ToolJet

ToolJet is the lightweight, extensible option. It supports a wide range of data sources and uses JavaScript for logic, similar to Appsmith, but with a simpler architecture and a strong plugin system. ToolJet's open-source edition includes core functionality for free, with enterprise features available in a paid tier.

ToolJet stands out for its extensibility: you can write custom plugins in JavaScript to connect to virtually any API or data source. It also has a multi-environment feature that helps manage development, staging, and production workflows.

## Feature Comparison

| Feature | Appsmith | Budibase | ToolJet |
|---|---|---|---|
| **License** | Apache 2.0 | GPL v3 | GPL v3 |
| **GitHub Stars** | 35,000+ | 21,000+ | 28,000+ |
| **UI Builder** | Drag-and-drop canvas | Drag-and-drop + design system | Drag-and-drop canvas |
| **Internal Database** | No (relies on external sources) | Yes (built-in CouchDB-based) | No (relies on external sources) |
| **Automation/Workflows** | Via JS queries and webhooks | Visual automation engine | Limited (JS queries) |
| **Custom Components** | Yes (React-based) | Yes (custom plugins) | Yes (JS plugins) |
| **Version Control** | Git integration (EE) | Git-based | Git integration |
| **Role-Based Access** | Yes | Yes | Yes (EE) |
| **SSO / SAML** | Enterprise only | Community + Enterprise | Enterprise only |
| **Mobile Responsive** | Manual layout control | Auto-responsive layouts | Manual layout control |
| **Audit Logging** | Enterprise only | Community | Enterprise only |
| **Multi-Environment** | Enterprise only | Built-in | Built-in |
| **Real-time Collaboration** | No | No | No |

## Data Source Support

All three platforms connect to the standard set of data sources, but with notable differences in depth and ease of setup.

| Data Source | Appsmith | Budibase | ToolJet |
|---|---|---|---|
| PostgreSQL | Native | Native | Native |
| MySQL / MariaDB | Native | Native | Native |
| MongoDB | Native | Native | Native |
| Redis | Native | Via plugin | Via plugin |
| REST APIs | Native | Native | Native |
| GraphQL | Native | Via plugin | Native |
| Google Sheets | Native | Native | Native |
| SMTP / Email | Via JS | Native automation | Via plugin |
| S3-compatible storage | Native | Via plugin | Via plugin |
| Elasticsearch | Native | Via plugin | Native |
| Snowflake | Native | Via plugin | Via plugin |

## Self-Hosted Deployment with Docker

### Appsmith

Appsmith provides a single Docker Compose file that handles everything. The self-hosted edition is fully functional for teams that don't need enterprise features like SSO or audit logs.

**Step 1: Create the deployment directory**

```bash
mkdir -p /opt/appsmith && cd /opt/appsmith
```

**Step 2: Create docker-compose.yml**

```yaml
services:
  appsmith:
    image: index.docker.io/appsmith/appsmith-ce:latest
    container_name: appsmith
    restart: unless-stopped
    ports:
      - "8080:80"
      - "443:443"
    volumes:
      - ./stacks:/appsmith-stacks
    environment:
      - APPSMITH_DISABLE_EMBEDDED_KEYCLOAK=1
    # For custom domain with TLS, set these:
    # - APPSMITH_CUSTOM_DOMAIN=tools.yourdomain.com
    # - APPSMITH_LETSENCRYPT_EMAIL=admin@yourdomain.com
```

**Step 3: Start Appsmith**

```bash
docker compose up -d
```

**Step 4: Access and configure**

Open `http://your-server:8080` in your browser. You'll be prompted to create an admin account. After signup, you can start building applications immediately.

**Production considerations for Appsmith:**

- Mount the `./stacks` volume to a persistent drive. All your applications, queries, and settings are stored here.
- Set up a reverse proxy (Nginx or Caddy) for TLS termination in production.
- For high availability, Appsmith's enterprise edition supports horizontal scaling with a shared database backend.
- Backup the `./stacks` directory regularly — it contains all application definitions.

```bash
# Backup script example
#!/bin/bash
BACKUP_DIR="/backups/appsmith/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"
tar czf "$BACKUP_DIR/appsmith-stacks.tar.gz" -C /opt/appsmith stacks
# Keep only last 30 days
find /backups/appsmith -mtime +30 -delete
```

### Budibase

Budibase's architecture is more distributed: it runs separate containers for the app worker, miniOS (internal database), CouchDB, and MinIO (object storage).

**Step 1: Install the Budibase CLI (recommended)**

```bash
npm install -g @budibase/cli
bb init
```

The CLI guides you through the setup process and generates the Docker Compose configuration automatically.

**Step 2: Manual Docker Compose (alternative)**

```yaml
services:
  app-service:
    image: budibase.docker.scarf.sh/budibase/apps:latest
    restart: unless-stopped
    environment:
      - SELF_HOSTED=1
      - COUCH_DB_URL=http://couchdb-service:5984
      - MINIO_URL=http://minio-service:9000
      - MINIO_ACCESS_KEY=budi
      - MINIO_SECRET_KEY=budibase
      - INTERNAL_API_KEY=your-secret-key-here
      - BUDIBASE_ENVIRONMENT=PRODUCTION
    depends_on:
      - worker-service
      - couchdb-service
      - minio-service
    ports:
      - "10000:4002"

  worker-service:
    image: budibase.docker.scarf.sh/budibase/worker:latest
    restart: unless-stopped
    environment:
      - SELF_HOSTED=1
      - COUCH_DB_URL=http://couchdb-service:5984
      - MINIO_URL=http://minio-service:9000
      - MINIO_ACCESS_KEY=budi
      - MINIO_SECRET_KEY=budibase
      - INTERNAL_API_KEY=your-secret-key-here
      - BUDIBASE_ENVIRONMENT=PRODUCTION
      - CLUSTER_PORT=10000
    depends_on:
      - couchdb-service
      - minio-service

  couchdb-service:
    image: budibase.docker.scarf.sh/budibase/couchdb:latest
    restart: unless-stopped
    environment:
      - COUCHDB_USER=budi
      - COUCHDB_PASSWORD=budibase
    volumes:
      - couchdb_data:/opt/couchdb/data

  minio-service:
    image: minio/minio:latest
    restart: unless-stopped
    environment:
      - MINIO_ROOT_USER=budi
      - MINIO_ROOT_PASSWORD=budibase
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data

volumes:
  couchdb_data:
  minio_data:
```

**Step 3: Start Budibase**

```bash
docker compose up -d
```

**Step 4: Access and configure**

Open `http://your-server:10000`. Budibase will guide you through initial setup, including admin account creation.

**Production considerations for Budibase:**

- Budibase's internal CouchDB stores all application data. Regular backups of the `couchdb_data` volume are critical.
- The `INTERNAL_API_KEY` should be a strong random string. Generate one with: `openssl rand -hex 32`
- MinIO stores file attachments and uploads. Ensure the `minio_data` volume has adequate disk space.
- Budibase supports horizontal scaling in enterprise mode with a shared Redis and PostgreSQL backend.

```bash
# Backup Budibase volumes
#!/bin/bash
BACKUP_DIR="/backups/budibase/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Backup CouchDB
docker exec budibase-couchdb-service-1 bash -c \
  "curl -s http://budi:budibase@127.0.0.1:5984/_all_dbs" | \
  while read db; do
    docker exec budibase-couchdb-service-1 bash -c \
      "curl -s http://budi:budibase@127.0.0.1:5984/$db/_all_docs?limit=10000" \
      > "$BACKUP_DIR/$db.json"
  done

# Backup MinIO data
docker run --rm -v budibase_minio_data:/data -v "$BACKUP_DIR":/backup \
  alpine tar czf /backup/minio-data.tar.gz -C /data .
```

### ToolJet

ToolJet uses a simpler two-container architecture: the main application and a PostgreSQL database.

**Step 1: Create the deployment directory**

```bash
mkdir -p /opt/tooljet && cd /opt/tooljet
```

**Step 2: Create docker-compose.yml**

```yaml
services:
  tooljet:
    image: tooljet/tooljet-ce:latest
    restart: unless-stopped
    ports:
      - "8082:80"
    environment:
      - LOCKBOX_MASTER_KEY=your-master-key-here
      - SECRET_KEY_BASE=your-secret-key-here
      - SERVICE_ENV=production
      - PG_HOST=tooljet-db
      - PG_PORT=5432
      - PG_USER=tooljet
      - PG_PASS=tooljet_password
      - PG_DB=tooljet
      - DEPLOYMENT_PLATFORM=docker
      - TOOLJET_HOST=http://localhost:8082
    depends_on:
      tooljet-db:
        condition: service_healthy

  tooljet-db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      - POSTGRES_USER=tooljet
      - POSTGRES_PASSWORD=tooljet_password
      - POSTGRES_DB=tooljet
    volumes:
      - tj_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U tooljet"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  tj_postgres_data:
```

**Step 3: Generate secure keys**

```bash
# Generate master key (for Lockbox encryption)
openssl rand -hex 32

# Generate secret key base
openssl rand -hex 64
```

Replace the placeholder values in the compose file with the generated keys.

**Step 4: Start ToolJet**

```bash
docker compose up -d
```

**Step 5: Access and configure**

Open `http://your-server:8082`. Create your admin account and start building.

**Production considerations for ToolJet:**

- PostgreSQL stores all application definitions and metadata. Set up regular `pg_dump` backups.
- The `LOCKBOX_MASTER_KEY` encrypts stored credentials. If lost, all saved data source credentials become unrecoverable.
- ToolJet supports custom plugins written in JavaScript. Place them in a mounted volume for persistence across container rebuilds.
- For multi-environment setups, use ToolJet's built-in environment management to promote applications from dev to prod.

```bash
# Automated PostgreSQL backup
#!/bin/bash
BACKUP_DIR="/backups/tooljet"
mkdir -p "$BACKUP_DIR"

docker exec tooljet-tooljet-db-1 pg_dump -U tooljet tooljet | \
  gzip > "$BACKUP_DIR/tooljet-$(date +%Y%m%d-%H%M%S).sql.gz"

# Keep last 14 days
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +14 -delete
```

## Performance and Resource Requirements

| Metric | Appsmith | Budibase | ToolJet |
|---|---|---|---|
| **Minimum RAM** | 2 GB | 4 GB | 2 GB |
| **Recommended RAM** | 4 GB | 8 GB | 4 GB |
| **Disk (base)** | ~1 GB | ~3 GB | ~1 GB |
| **CPU (idle)** | ~5% | ~10% | ~5% |
| **Startup time** | ~30s | ~60s | ~20s |
| **Containers** | 1 | 4+ | 2 |

Budibase has the highest resource requirements because it bundles its own database (CouchDB) and object storage (MinIO). For teams with limited server resources, ToolJet or Appsmith are lighter options.

## When to Choose Which Platform

### Choose Appsmith if:

- You need the most mature platform with the largest community and plugin ecosystem.
- Your team is comfortable with JavaScript for query logic and widget bindings.
- You primarily build dashboards and admin panels that read from existing data sources.
- You want the closest open-source equivalent to Retool's workflow and UX.
- You need extensive third-party integrations out of the box.

### Choose Budibase if:

- You need a built-in internal database without managing a separate database server.
- You want visual automation workflows (approvals, notifications, data sync) without writing code.
- You build CRUD applications and data entry portals frequently.
- Auto-responsive layouts matter for teams accessing tools on various screen sizes.
- You want a more "opinionated" platform that handles more of the infrastructure for you.

### Choose ToolJet if:

- You want the simplest deployment with the fewest moving parts.
- Your team values extensibility and custom plugin development.
- You need multi-environment support (dev/staging/prod) in the open-source edition.
- You prefer a lighter-weight platform that's easier to maintain and upgrade.
- Resource constraints are a concern on your deployment server.

## Security Best Practices for Self-Hosted Deployments

Regardless of which platform you choose, follow these security practices:

**1. Never expose the platform directly to the internet without a reverse proxy and TLS:**

```nginx
# Example Nginx configuration
server {
    listen 443 ssl http2;
    server_name tools.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/tools.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tools.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }
}
```

**2. Restrict database access:** Ensure your internal tools platform can only reach the databases it needs. Use database-level role restrictions — create read-only users for dashboard queries and limit write access to specific tables.

**3. Enable network-level access controls:** Use firewall rules to restrict access to the internal tools platform. Only allow connections from your office network or VPN:

```bash
# UFW example — only allow access from your office subnet
ufw allow from 10.0.0.0/24 to any port 8080
ufw deny 8080
```

**4. Regular backups:** Set up automated backups for both application definitions (the platform's database) and any user-generated data. Test your restore procedure quarterly.

**5. Keep platforms updated:** Subscribe to the GitHub release feeds for your chosen platform and test updates in a staging environment before applying to production.

## Migration from SaaS Platforms

If you're currently using Retool or a similar SaaS platform, migration requires manual effort since there's no direct import/export between platforms. However, the patterns translate well:

- **Retool → Appsmith**: The closest migration path. Both use JavaScript for bindings and have similar widget sets. Expect 70–80% of your Retool apps to port over with minimal changes.
- **Retool → Budibase**: Requires more restructuring. Budibase's internal database and automation engine may actually simplify some apps that required custom Retool backend logic.
- **Retool → ToolJet**: Similar to Appsmith but with fewer built-in widgets. You may need to build custom components for specialized UI elements.

Plan migration in phases: start with read-only dashboards, then move internal CRUD tools, and finally migrate complex workflow applications.

## Conclusion

The self-hosted internal tools landscape in 2026 offers mature, production-ready options for every team size and use case. Appsmith leads in maturity and ecosystem size, Budibase excels at full-stack application building with automation, and ToolJet offers the simplest and most extensible deployment.

All three platforms eliminate per-seat licensing costs, keep your data under your control, and run on commodity hardware. The best choice depends on your team's technical skills, infrastructure constraints, and the complexity of the tools you need to build.

For most teams starting their self-hosted journey, **Appsmith** provides the gentlest learning curve and the most community support. Teams that need built-in database management and visual workflows should lean toward **Budibase**. And teams that prioritize simplicity and extensibility will find **ToolJet** the most comfortable fit.
