---
title: "HashiCorp Vault vs Infisical vs Passbolt: Self-Hosted Secrets Rotation Guide 2026"
date: 2026-04-25
tags: ["comparison", "guide", "self-hosted", "security", "secrets"]
draft: false
description: "Complete guide to self-hosted automated secrets rotation. Compare HashiCorp Vault, Infisical, and Passbolt for rotating database credentials, API keys, TLS certificates, and SSH keys automatically."
---

## Why Automated Secrets Rotation Matters

Manual credential rotation is one of the most common causes of security incidents in self-hosted infrastructure. Database passwords shared across services, API keys that never expire, and TLS certificates that outlive their owners — these are not theoretical risks. They are the root cause of real breaches.

Automated secrets rotation eliminates the human factor. Credentials expire, renew, and propagate without any manual intervention. Every service gets fresh, unique credentials on a predictable schedule. Old credentials are invalidated before they can be abused.

This guide compares three self-hosted platforms — **HashiCorp Vault**, **Infisical**, and **Passbolt** — specifically through the lens of automated secrets rotation. While our [broader secrets management comparison](../best-self-hosted-secret-management-vault-infisical-passbolt-2026/) covers storage and access control, this article dives deep into **how rotation actually works**, what each tool supports, and how to deploy rotation pipelines with Docker Compose.

For teams also managing secrets in version control, see our [guide to encrypting secrets in Git with SOPS, git-crypt, and age](../mozilla-sops-vs-git-crypt-vs-age-self-hosted-secrets-encryption-git-guide-2026/).

## What Is Secrets Rotation?

Secrets rotation is the process of periodically replacing credentials with new values while maintaining uninterrupted service access. There are three primary approaches:

| Approach | How It Works | Best For |
|---|---|---|
| **Dynamic Secrets** | Credentials are generated on-demand, with a TTL. No shared passwords exist. | Cloud APIs, database connections, service accounts |
| **Scheduled Rotation** | Existing credentials are replaced at fixed intervals (hourly, daily, weekly). | API keys, service tokens, SSH keys |
| **On-Demand Rotation** | Credentials are rotated manually or triggered by events (breach detection, staff departure). | Emergency response, compliance requirements |

A rotation strategy without a centralized secrets platform means writing custom cron jobs, updating configuration files across dozens of servers, and hoping nothing breaks. With a proper rotation engine, the entire lifecycle is automated: generate, distribute, revoke, and audit.

## HashiCorp Vault — Dynamic Secrets Engine

Vault is the industry standard for secrets rotation, with over 35,000 GitHub stars and adoption across Fortune 500 companies. Its rotation capability is built around the **secrets engine** architecture — each engine handles a specific type of credential with its own rotation logic.

**GitHub**: [hashicorp/vault](https://github.com/hashicorp/vault) — 35,493 stars · Last updated April 2026 · Written in Go

### Database Credential Rotation

Vault's database secrets engine creates unique database users for each application request. When a service needs database access, Vault generates a PostgreSQL user with a 1-hour TTL. The user is automatically dropped when the lease expires.

```hcl
# Enable the database secrets engine
vault secrets enable database

# Configure the PostgreSQL connection
vault write database/config/my-postgres-db \
    plugin_name=postgresql-database-plugin \
    allowed_roles="app-role" \
    connection_url="postgresql://{{username}}:{{password}}@postgres:5432/mydb?sslmode=disable" \
    username="vault-admin" \
    password="admin-password"

# Create a role with a 1-hour TTL
vault write database/roles/app-role \
    db_name=my-postgres-db \
    creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
    default_ttl="1h" \
    max_ttl="24h"
```

Every application instance gets a unique database credential. No shared passwords. No manual rotation. When the TTL expires, Vault revokes the user automatically.

### Cloud Provider Key Rotation

Vault integrates with AWS, Azure, and GCP to rotate IAM credentials and service account keys on schedule:

```bash
# Enable AWS secrets engine
vault secrets enable aws

# Configure the IAM role
vault write aws/config/root \
    access_key="AKIA..." \
    secret_key="SECRET..." \
    region="us-east-1"

# Create a role with 30-minute rotation
vault write aws/roles/deploy-role \
    credential_type=iam_user \
    policy_document=-<<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject"],
      "Resource": "arn:aws:s3:::my-bucket/*"
    }
  ]
}
EOF

# Request temporary credentials (auto-rotated)
vault read aws/creds/deploy-role
```

### Docker Compose Deployment

Vault requires initialization and unsealing in production. For development and testing, a single-node setup with file storage works:

```yaml
version: "3"
services:
  vault:
    image: hashicorp/vault:latest
    container_name: vault-server
    restart: unless-stopped
    cap_add:
      - IPC_LOCK
    ports:
      - "8200:8200"
    environment:
      VAULT_ADDR: "http://0.0.0.0:8200"
      VAULT_API_ADDR: "http://0.0.0.0:8200"
    volumes:
      - vault-data:/vault/file
      - ./vault-config.hcl:/vault/config/vault.hcl
    command: "vault server -config=/vault/config/vault.hcl"

volumes:
  vault-data:
```

With a `vault.hcl` configuration:

```hcl
storage "file" {
  path = "/vault/file"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1
}

api_addr = "http://localhost:8200"
```

For production deployments, replace file storage with Consul or integrated Raft storage, and enable TLS on the listener.

## Infisical — Modern Secrets Platform with Rotation

Infisical is an open-source secrets management platform built for modern development teams. It combines a developer-friendly UI with API-first architecture and built-in rotation capabilities.

**GitHub**: [Infisical/infisical](https://github.com/Infisical/infisical) — 26,191 stars · Last updated April 2026 · Written in TypeScript

### Secrets Rotation Architecture

Infisical's rotation system works by connecting to external services and replacing credentials on a configurable schedule:

- **Database rotation** — Connects to PostgreSQL, MySQL, or MongoDB and rotates credentials via the Infisical API
- **API key rotation** — Supports AWS, Stripe, and custom API endpoints
- **Certificate rotation** — Integrates with Let's Encrypt and internal PKI for TLS certificate renewal
- **Custom rotation** — Use webhooks to trigger external rotation scripts

The rotation pipeline is event-driven: when a scheduled rotation fires, Infisical generates new credentials, stores them, and notifies connected applications via webhook or SDK polling.

### Docker Compose Deployment

Infisical ships with a production-ready Docker Compose file:

```yaml
version: "3"

services:
  backend:
    container_name: infisical-backend
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    image: infisical/infisical:latest
    pull_policy: always
    env_file: .env
    ports:
      - "80:8080"
    environment:
      - NODE_ENV=production
    networks:
      - infisical

  redis:
    image: redis
    container_name: infisical-redis
    env_file: .env
    restart: always
    networks:
      - infisical
    volumes:
      - redis_data:/data

  db:
    container_name: infisical-db
    image: postgres:14-alpine
    restart: always
    env_file: .env
    volumes:
      - pg_data:/var/lib/postgresql/data
    networks:
      - infisical
    healthcheck:
      test: "pg_isready --username=${POSTGRES_USER} && psql --username=${POSTGRES_USER} --list"
      interval: 5s
      timeout: 10s
      retries: 10

volumes:
  pg_data:
    driver: local
  redis_data:
    driver: local

networks:
  infisical:
    driver: bridge
```

The `.env` file configures encryption keys, database credentials, and SMTP settings. Once deployed, the web UI at port 80 provides a full secrets management dashboard with rotation policy configuration.

### Setting Up Rotation Policies

Through the Infisical dashboard or API:

```bash
# Create a rotation policy via API
curl -X POST https://infisical.example.com/api/v1/secrets/rotation \
  -H "Authorization: Bearer $INFISICAL_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "secretName": "DB_PASSWORD",
    "environment": "production",
    "projectId": "my-project-id",
    "rotationType": "database",
    "rotationSchedule": "0 */6 * * *",
    "rotationProvider": "postgresql",
    "connectionString": "postgresql://admin:password@db:5432/myapp"
  }'
```

This rotates the `DB_PASSWORD` secret every 6 hours. The new password is injected into connected services via Infisical's SDK or webhook notifications.

## Passbolt — Team Password Management with Rotation

Passbolt is an open-source password manager designed for teams. While its primary focus is password sharing and access control, it includes rotation capabilities for shared credentials.

**GitHub**: [passbolt/passbolt_api](https://github.com/passbolt/passbolt_api) — 5,862 stars · Last updated April 2026 · Written in PHP

### How Passbolt Handles Rotation

Passbolt's rotation model differs from Vault and Infisical:

- **Manual rotation** — Administrators can manually rotate any shared password through the web UI or browser extension
- **API-driven rotation** — Use the REST API to programmatically update shared credentials
- **Audit trail** — Every rotation is logged with user attribution, providing a complete chain of custody
- **GPG-based encryption** — All secrets are encrypted with per-user GPG keys, ensuring only authorized users can access rotated credentials

Passbolt does not generate dynamic secrets or auto-rotate on a schedule out of the box. Instead, it provides the secure storage and access control layer, while rotation is triggered through the API or browser extension. This makes it ideal for teams that need human-in-the-loop rotation — where a security policy requires manual approval before credentials change.

### Docker Compose Deployment

Passbolt's official Docker Compose setup uses MariaDB for storage:

```yaml
services:
  db:
    image: mariadb:10.11
    restart: unless-stopped
    environment:
      MYSQL_RANDOM_ROOT_PASSWORD: "true"
      MYSQL_DATABASE: "passbolt"
      MYSQL_USER: "passbolt"
      MYSQL_PASSWORD: "P4ssb0lt_SecureChangeMe"
    volumes:
      - database_volume:/var/lib/mysql

  passbolt:
    image: passbolt/passbolt:latest-ce
    restart: unless-stopped
    depends_on:
      - db
    environment:
      APP_FULL_BASE_URL: https://passbolt.example.com
      DATASOURCES_DEFAULT_HOST: "db"
      DATASOURCES_DEFAULT_USERNAME: "passbolt"
      DATASOURCES_DEFAULT_PASSWORD: "P4ssb0lt_SecureChangeMe"
      DATASOURCES_DEFAULT_DATABASE: "passbolt"
      EMAIL_TRANSPORT_DEFAULT_HOST: "smtp.example.com"
      EMAIL_TRANSPORT_DEFAULT_PORT: 587
    volumes:
      - gpg_volume:/etc/passbolt/gpg
      - jwt_volume:/etc/passbolt/jwt
    command:
      [
        "/usr/bin/wait-for.sh",
        "-t", "0",
        "db:3306",
        "--",
        "/docker-entrypoint.sh",
      ]
    ports:
      - "80:80"
      - "443:443"

volumes:
  database_volume:
  gpg_volume:
  jwt_volume:
```

After the initial setup wizard, administrators configure GPG keys and invite team members. The rotation workflow happens through the web interface or REST API.

### Programmatic Rotation via API

```bash
# Get a secret by ID
curl -s "https://passbolt.example.com/secrets.json?api-version=v2" \
  -H "Authorization: Bearer $PASSBOLT_API_KEY"

# Update (rotate) a password
curl -X PUT "https://passbolt.example.com/secrets/abc123.json?api-version=v2" \
  -H "Authorization: Bearer $PASSBOLT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "password": {
      "data": "encrypted-new-password-data",
      "user_id": "admin-user-id"
    }
  }'
```

Passbolt's API requires GPG-encrypted payloads, which adds a security layer but increases integration complexity compared to Vault or Infisical.

## Feature Comparison

| Feature | HashiCorp Vault | Infisical | Passbolt |
|---|---|---|---|
| **Dynamic Secrets** | Full support (DB, AWS, Azure, GCP, SSH, PKI) | Database credentials, custom providers | No |
| **Auto Rotation** | Built-in engine with configurable TTLs | Scheduled + event-driven rotation | Manual via API only |
| **Rotation Schedule** | Per-secret TTL (minutes to months) | Cron-based scheduling | N/A |
| **Audit Log** | Complete audit trail for every operation | Full rotation history with user attribution | Complete audit with GPG signing |
| **API Access** | REST + CLI + SDK (Go, Python, Java) | REST + SDK (JS, Python) | REST API (PHP-based) |
| **Database Support** | PostgreSQL, MySQL, MSSQL, MongoDB, Cassandra, Oracle | PostgreSQL, MySQL, MongoDB | N/A (password storage only) |
| **Cloud Integration** | AWS, Azure, GCP, Kubernetes | AWS, custom webhooks | None |
| **Certificate Rotation** | PKI secrets engine (ACME, internal CA) | Let's Encrypt integration | None |
| **Self-Hosted** | Yes (Apache 2.0 / BSL) | Yes (AGPL-3.0) | Yes (AGPL-3.0) |
| **Web UI** | Basic (admin interface) | Full-featured dashboard | Full-featured (browser extension) |
| **Team Access Control** | ACL policies, entity aliases, MFA | Role-based access, groups | GPG-based per-user encryption |
| **GitHub Stars** | 35,493 | 26,191 | 5,862 |
| **Language** | Go | TypeScript | PHP |

## Choosing the Right Rotation Strategy

The choice depends on your infrastructure complexity and rotation requirements:

**Use HashiCorp Vault when**:
- You need dynamic secrets that are generated on-demand and auto-expire
- You manage cloud credentials (AWS, Azure, GCP) that need regular rotation
- You operate at scale with dozens of services requiring database access
- You want industry-standard tooling with the widest ecosystem support

**Use Infisical when**:
- You want a modern, developer-friendly interface with scheduled rotation
- You need webhook-based notification when credentials rotate
- Your team prefers TypeScript/Node.js ecosystem tooling
- You want a balance between automation ease and self-hosted control

**Use Passbolt when**:
- Your organization requires human approval before any credential change
- You need GPG-encrypted password sharing with rotation audit trails
- Your primary use case is team password management (not infrastructure automation)
- Compliance requires manual sign-off on credential changes

## Migration Considerations

When migrating from manual rotation to automated systems, follow a phased approach:

1. **Inventory all credentials** — Catalog every database password, API key, and TLS certificate
2. **Identify rotation candidates** — Start with non-critical services (monitoring, logging)
3. **Set up the secrets platform** — Deploy with Docker Compose in staging first
4. **Configure rotation policies** — Begin with generous TTLs (24h+), then tighten
5. **Monitor and audit** — Watch for rotation failures in application logs
6. **Expand coverage** — Gradually rotate production credentials once staging is stable

For teams also managing SSH access, consider combining secrets rotation with an [SSH bastion server setup](../self-hosted-ssh-bastion-jump-server-teleport-guacamole-trysail-guide-2026/) for complete access credential lifecycle management.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "HashiCorp Vault vs Infisical vs Passbolt: Self-Hosted Secrets Rotation Guide 2026",
  "description": "Complete guide to self-hosted automated secrets rotation. Compare HashiCorp Vault, Infisical, and Passbolt for rotating database credentials, API keys, TLS certificates, and SSH keys automatically.",
  "datePublished": "2026-04-25",
  "dateModified": "2026-04-25",
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

## FAQ

### What is the difference between secrets rotation and secrets management?

Secrets management covers the entire lifecycle: storage, encryption, access control, sharing, and rotation. Secrets rotation is one specific aspect — the process of periodically replacing old credentials with new ones. Think of rotation as the "refresh" mechanism within the broader management system. A platform can manage secrets without rotating them, but rotation requires some form of secrets management to store and distribute the new values.

### How often should database credentials be rotated?

The optimal rotation frequency depends on your threat model and operational tolerance. For high-security environments (financial services, healthcare), database credentials should rotate every 1–6 hours. For standard production environments, a 24-hour rotation cycle is common. For low-risk internal tools, weekly rotation may be acceptable. HashiCorp Vault's dynamic secrets engine can rotate credentials as frequently as every minute without any operational overhead, while Passbolt requires manual or API-triggered rotation.

### Can Vault rotate credentials for databases it does not natively support?

Vault's database secrets engine supports PostgreSQL, MySQL, MSSQL, MongoDB, Cassandra, Oracle, ElasticSearch, Redis, and InfluxDB out of the box. For unsupported databases, Vault provides a generic plugin interface. You can write a custom database plugin that implements the rotation protocol for your specific database (e.g., CockroachDB, ClickHouse, or a legacy system). The plugin handles credential creation, revocation, and renewal according to your database's authentication model.

### Does Infisical support rotation of API keys for services like Stripe or AWS?

Yes. Infisical supports rotating AWS IAM credentials natively. For services like Stripe, GitHub, or other APIs with key rotation endpoints, you can configure custom rotation providers that call the service's API to generate new keys. The rotation is triggered on a cron schedule you define, and the new secret is automatically pushed to all connected environments.

### What happens if a secrets rotation fails?

When rotation fails, the behavior depends on the platform:

- **Vault**: If a database credential cannot be revoked (e.g., the database is unreachable), Vault logs the error and retries. The old lease remains valid until the issue is resolved. Vault's audit log records the failure for investigation.
- **Infisical**: Failed rotations trigger webhook notifications and appear in the dashboard. The previous secret remains active, and the rotation can be retried manually.
- **Passbolt**: Since rotation is manual or API-driven, failures are immediately visible to the operator. The API returns an error response that can be caught and handled programmatically.

In all cases, a failed rotation should trigger an alert. Never silently ignore rotation failures — they indicate that old credentials remain active longer than intended, which is a security risk.

### Is Passbolt suitable for infrastructure automation and service-to-service secrets?

Passbolt is primarily designed for human team members who need to share and rotate passwords. While its API can be used for programmatic access, the GPG encryption requirement adds complexity for service-to-service communication. For infrastructure automation (CI/CD pipelines, container orchestration, microservices), HashiCorp Vault or Infisical are better suited because they support API key authentication, dynamic secrets, and direct integration with deployment tools. Passbolt excels at team password sharing, not machine-to-machine credential management.
