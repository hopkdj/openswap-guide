---
title: "Best Self-Hosted Secret Management: HashiCorp Vault vs Infisical vs Passbolt 2026"
date: 2026-04-13
tags: ["comparison", "guide", "self-hosted", "security", "devops"]
draft: false
description: "Compare HashiCorp Vault, Infisical, and Passbolt for self-hosted secret management. Complete Docker setup guides, feature comparison, and best practices for securing API keys, credentials, and application secrets in 2026."
---

## Why Self-Host Your Secret Management?

Every modern application stack runs on secrets: API keys, database credentials, TLS certificates, OAuth tokens, and encryption keys. Storing these in environment files, hardcoding them in configuration, or scattering them across Slack messages and wikis is one of the most common security failures in both homelabs and production environments.

Self-hosting a dedicated secret management system solves these problems at their root:

- **No more `.env` file sprawl** — every project, service, and environment pulls secrets from a single authoritative source
- **Centralized access control** — define exactly which users and services can read, write, or rotate each secret
- **Automatic rotation** — credentials expire and renew on schedule without manual intervention
- **Full audit trail** — every secret access, modification, and deletion is logged with timestamps and identity
- **Zero cloud dependency** — your most sensitive data never leaves your infrastructure, eliminating third-party breach exposure
- **Free at any scale** — open-source secret managers impose no limits on the number of secrets, users, or environments

For homelab operators managing dozens of services, development teams deploying across staging and production, and anyone serious about operational security, a self-hosted secret manager is the single highest-impact security improvement you can make.

## Three Approaches to Secret Management

The self-hosted secret management landscape spans three distinct design philosophies, each optimized for different workflows and team sizes:

| Feature | HashiCorp Vault | Infisical | Passbolt |
|---------|-----------------|-----------|----------|
| **Primary Focus** | Enterprise-grade secrets engine | Developer experience & CI/CD | Password & credential sharing |
| **License** | BSL 1.1 (free self-hosted) | AGPL-3.0 | AGPL-3.0 |
| **Secret Types** | KV, databases, PKI, SSH, transit, cloud IAM | KV, files, dynamic DB creds | Passwords, files, TOTP |
| **Dynamic Secrets** | ✅ Full support (DB, AWS, Azure, GCP, RabbitMQ) | ✅ Database credentials | ❌ Static only |
| **Auto Rotation** | ✅ Built-in engine | ✅ Built-in | ❌ Manual |
| **Auth Methods** | 15+ (LDAP, OIDC, JWT, Kubernetes, AppRole, TLS certs, GitHub, GitLab, AWS IAM, etc.) | 8+ (LDAP, OIDC, SAML, SSO, service tokens) | 4 (Email, LDAP, SAML, SSO) |
| **UI Quality** | Functional but dated | Modern, polished, excellent UX | Clean, functional |
| **CLI Quality** | Excellent, full-featured | Excellent, developer-friendly | Good |
| **API** | REST + Go SDK | REST + SDKs (JS, Python, Go, CLI) | REST API |
| **CI/CD Integration** | Via CLI, API, or agent | Native GitHub, GitLab, CircleCI, generic | Via API/CLI |
| **High Availability** | ✅ Raft consensus + integrated storage | ✅ Replicated state | ✅ Enterprise only |
| **Audit Logging** | ✅ Comprehensive | ✅ Full history | ✅ Activity log |
| **Learning Curve** | Steep | Low | Low |
| **Best For** | Large teams, complex infra | Dev teams, startups | Credential sharing, IT teams |

## 1. HashiCorp Vault — The Industry Standard

**Best for**: Complex infrastructure, enterprise teams, dynamic secrets, and environments requiring maximum security controls.

Vault is the most powerful and widely deployed secret management system in existence. It does not merely store secrets — it generates them dynamically, rotates them automatically, encrypts data in transit and at rest, manages PKI certificates, issues SSH credentials, and integrates with virtually every cloud provider and identity system.

### Key Features

- **Dynamic secrets**: Vault creates database credentials, cloud API keys, and service accounts on demand. Each request gets unique, short-lived credentials that automatically expire.
- **Secret leasing and renewal**: Every secret has a TTL. Applications must renew leases, giving you visibility into which services are actively using which credentials.
- **PKI secrets engine**: Run your own certificate authority. Issue and revoke TLS certificates automatically, replacing manual Let's Encrypt workflows for internal services.
- **Transit encryption**: Encrypt and decrypt data without handling keys yourself. Useful for encrypting backups, database columns, or application data.
- **Identity-based access**: Integrate with LDAP, OIDC, Kubernetes service accounts, cloud IAM roles, and more. No shared API keys needed.
- **Raft storage**: Built-in high-availability storage with no external database dependency.

### Docker Compose Deployment

```yaml
# docker-compose.yml
services:
  vault:
    image: hashicorp/vault:1.19
    container_name: vault
    cap_add:
      - IPC_LOCK
    restart: unless-stopped
    ports:
      - "8200:8200"
    environment:
      VAULT_ADDR: "http://0.0.0.0:8200"
      VAULT_API_ADDR: "http://0.0.0.0:8200"
    volumes:
      - vault-data:/vault/file
      - ./vault-config.hcl:/vault/config/vault.hcl
    entrypoint: vault server -config=/vault/config/vault.hcl

volumes:
  vault-data:
```

```hcl
# vault-config.hcl
storage "raft" {
  path    = "/vault/file"
  node_id = "node1"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1  # Put a reverse proxy with TLS in front
}

api_addr     = "http://127.0.0.1:8200"
cluster_addr = "https://127.0.0.1:8201"

ui = true
```

### Initial Setup

```bash
# Start Vault and initialize
docker compose up -d

# Initialize (save the output — root token and unseal keys!)
docker exec vault vault operator init

# Unseal (run 3 times with 3 different unseal keys)
docker exec vault vault operator unseal <unseal-key-1>
docker exec vault vault operator unseal <unseal-key-2>
docker exec vault vault operator unseal <unseal-key-3>

# Login with root token
docker exec vault vault login <root-token>

# Enable the KV v2 secrets engine
docker exec vault vault secrets enable -path=secrets kv-v2

# Write your first secret
docker exec vault vault kv put secrets/myapp/database   username="app_user"   password="s3cretP@ss"   host="db.internal"

# Read it back
docker exec vault vault kv get secrets/myapp/database
```

### Production Best Practices

For production deployments, never use the root token for regular operations. Set up AppRole authentication for services and OIDC for human users:

```bash
# Enable AppRole for service authentication
docker exec vault vault auth enable approle

# Create a policy for your application
docker exec vault vault policy write myapp - <<EOF
path "secrets/data/myapp/*" {
  capabilities = ["read"]
}
path "secrets/metadata/myapp/*" {
  capabilities = ["list"]
}
EOF

# Create an AppRole with the policy
docker exec vault vault write auth/approle/role/myapp   token_policies="myapp"   token_ttl=1h   token_max_ttl=4h

# Get the role ID and secret ID
docker exec vault vault read auth/approle/role/myapp/role-id
docker exec vault vault write -f auth/approle/role/myapp/secret-id
```

Services authenticate with the role ID and secret ID to receive short-lived tokens.

### Dynamic Database Credentials (The Killer Feature)

```bash
# Enable the database secrets engine
docker exec vault vault secrets enable database

# Configure PostgreSQL connection
docker exec vault vault write database/config/postgres   plugin_name=postgresql-database-plugin   allowed_roles="myapp"   connection_url="postgresql://{{username}}:{{password}}@db.internal:5432/mydb?sslmode=disable"   username="vault_admin"   password="admin_password"

# Create a role that generates credentials
docker exec vault vault write database/roles/myapp   db_name=postgres   creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD \"{{password}}\" VALID UNTIL \"{{expiration}}\"; GRANT SELECT ON ALL TABLES IN SCHEMA public TO \"{{name}}\";"   default_ttl=1h   max_ttl=24h

# Get a dynamic credential
docker exec vault vault read database/creds/myapp
```

Every call generates a unique database user that automatically expires. No shared database passwords, no manual rotation, no stale credentials lingering after a service is decommissioned.

---

## 2. Infisical — The Developer-First Secret Manager

**Best for**: Development teams, startups, and anyone who wants a modern UI with seamless CI/CD integration.

Infisical was built from the ground up with developer experience as the primary goal. It features a polished web interface, native integrations with GitHub Actions and GitLab CI, and SDKs that inject secrets directly into your applications at runtime.

### Key Features

- **Environments**: Separate secrets per environment (dev, staging, production) with easy promotion workflows
- **Secret versioning**: Every change is tracked, and you can roll back to any previous version
- **Native CI/CD integrations**: First-class GitHub Actions, GitLab CI, and CircleCI support
- **SDK injection**: Secrets injected into Node.js, Python, Go, and other applications without code changes
- **Secret scanning**: Detect hardcoded secrets in your codebase before they reach production
- **Access controls**: Role-based permissions per project and environment
- **Audit logs**: Complete history of every secret access and modification

### Docker Compose Deployment

```yaml
# docker-compose.yml
services:
  infisical:
    image: infisical/infisical:latest
    container_name: infisical
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      NODE_ENV: production
      SITE_URL: "https://secrets.yourdomain.com"
      ENCRYPTION_KEY: "your-32-char-encryption-key-here!!"
      AUTH_SECRET: "your-jwt-auth-secret-here!!!"
      DB_CONNECTION_URI: "postgresql://infisical:password@postgres:5432/infisical"
      REDIS_URL: "redis://redis:6379"
      SMTP_HOST: "smtp.yourdomain.com"
      SMTP_PORT: "587"
      SMTP_SECURE: "false"
      SMTP_USERNAME: "noreply@yourdomain.com"
      SMTP_PASSWORD: "smtp_password"
      SMTP_ADDRESS: "noreply@yourdomain.com"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started

  postgres:
    image: postgres:17-alpine
    container_name: infisical-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: infisical
      POSTGRES_PASSWORD: password
      POSTGRES_DB: infisical
    volumes:
      - pg-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U infisical"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: infisical-redis
    restart: unless-stopped
    volumes:
      - redis-data:/data

volumes:
  pg-data:
  redis-data:
```

### Using the CLI

```bash
# Install the CLI
npm install -g @infisical/cli

# Login to your self-hosted instance
infisical login --domain https://secrets.yourdomain.com

# Initialize a project in your codebase
infisical init

# Inject secrets into any command
infisical run --env=production -- npm start

# View secrets for the current environment
infisical secrets --env=production

# Set a new secret
infisical secrets set DATABASE_URL --value "postgres://user:pass@db:5432/app" --env=production
```

### GitHub Actions Integration

```yaml
# .github/workflows/deploy.yml
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Fetch secrets from Infisical
        uses: infisical/secrets-action@main
        with:
          client-id: ${{ secrets.INFISICAL_CLIENT_ID }}
          client-secret: ${{ secrets.INFISICAL_CLIENT_SECRET }}
          domain: https://secrets.yourdomain.com
          env-slug: production

      - name: Deploy
        run: |
          echo "Deploying with secrets already injected"
          # All secrets are available as environment variables
```

### Python SDK Integration

```python
from infisical import InfisicalClient

# Initialize the client
client = InfisicalClient(
    domain="https://secrets.yourdomain.com",
    identity_id="your-service-identity"
)

# Fetch all secrets for an environment
secrets = client.list_secrets(environment="production")

# Fetch a specific secret
db_password = client.get_secret("DATABASE_PASSWORD", environment="production")
```

---

## 3. Passbolt — Password and Credential Management

**Best for**: IT teams, system administrators, and organizations that need shared password management with strong encryption and access auditing.

Passbolt is purpose-built for teams that need to share credentials securely. Unlike personal password managers, it is designed from the ground up for organizational use with role-based access, group sharing, and comprehensive audit trails.

### Key Features

- **End-to-end encryption**: Secrets are encrypted client-side using OpenPGP before reaching the server
- **Granular sharing**: Share individual credentials or entire folders with users and groups
- **Permission levels**: Read-only, read-write, and ownership controls per secret
- **TOTP storage**: Store two-factor authentication seeds alongside passwords
- **Password generator**: Built-in generator with configurable length and complexity rules
- **Import/export**: Migrate from LastPass, Bitwarden, 1Password, KeePass, or CSV
- **Browser extensions**: Chrome, Firefox, Edge, and Brave extensions for autofill
- **Mobile apps**: iOS and Android applications with biometric unlock

### Docker Compose Deployment

```yaml
# docker-compose.yml
services:
  passbolt:
    image: passbolt/passbolt:latest-ce
    container_name: passbolt
    restart: unless-stopped
    ports:
      - "8443:443"
      - "8080:80"
    environment:
      APP_FULL_BASE_URL: "https://passbolt.yourdomain.com"
      DATASOURCES_DEFAULT_HOST: "mariadb"
      DATASOURCES_DEFAULT_USERNAME: "passbolt"
      DATASOURCES_DEFAULT_PASSWORD: "secure_db_password"
      DATASOURCES_DEFAULT_DATABASE: "passbolt"
      EMAIL_TRANSPORT_DEFAULT_HOST: "smtp.yourdomain.com"
      EMAIL_TRANSPORT_DEFAULT_PORT: "587"
      EMAIL_TRANSPORT_DEFAULT_USERNAME: "noreply@yourdomain.com"
      EMAIL_TRANSPORT_DEFAULT_PASSWORD: "smtp_password"
      EMAIL_TRANSPORT_DEFAULT_TLS: "true"
      EMAIL_DEFAULT_FROM: "noreply@yourdomain.com"
    volumes:
      - gpg_volume:/etc/passbolt/gpg
      - jwt_volume:/etc/passbolt/jwt
    depends_on:
      - mariadb

  mariadb:
    image: mariadb:11
    container_name: passbolt-db
    restart: unless-stopped
    environment:
      MYSQL_RANDOM_ROOT_PASSWORD: "true"
      MYSQL_DATABASE: "passbolt"
      MYSQL_USER: "passbolt"
      MYSQL_PASSWORD: "secure_db_password"
    volumes:
      - db-data:/var/lib/mysql

volumes:
  gpg_volume:
  jwt_volume:
  db-data:
```

### Setup and Configuration

After starting the containers, complete the setup:

```bash
# Run the install script inside the container
docker exec passbolt su -m -c "/usr/share/php/passbolt/bin/cake   passbolt install --no-admin" -s /bin/sh www-data

# Create the first admin user
docker exec passbolt su -m -c "/usr/share/php/passbolt/bin/cake   passbolt register_user   -u admin@yourdomain.com   -f Admin   -l User   -r admin" -s /bin/sh www-data

# The command outputs a registration URL — open it in your browser
# to complete account setup and generate your GPG key
```

### Organizing Secrets with Folders and Tags

```bash
# List all resources (passwords)
docker exec passbolt su -m -c "/usr/share/php/passbolt/bin/cake passbolt   resources_view_all" -s /bin/sh www-data

# Create a folder via the web UI:
# 1. Navigate to Items > Create folder
# 2. Set permissions (which users/groups can access)
# 3. Move existing credentials into the folder

# Bulk import from CSV:
# 1. Settings > Import passwords
# 2. Upload CSV with columns: name, uri, username, password, description
# 3. Map fields and confirm import
```

---

## Choosing the Right Tool

The decision comes down to your use case, team size, and technical complexity:

### Choose HashiCorp Vault If:
- You manage complex infrastructure with databases, cloud providers, and PKI needs
- You need dynamic secrets that rotate automatically
- Your team has DevOps experience and can handle a steeper learning curve
- You require the most granular access control policies available
- You need integration with Kubernetes, Terraform, or Ansible

### Choose Infisical If:
- You are a development team shipping applications regularly
- You want the best developer experience with SDKs and CI/CD plugins
- You need environment-specific secrets with promotion workflows
- You prefer a modern, polished UI over terminal-based workflows
- You want built-in secret scanning to prevent hardcoded credentials

### Choose Passbolt If:
- Your primary need is shared password and credential management
- Your team includes non-technical members who need browser extension support
- You require end-to-end encryption with client-side key management
- You need to replace a commercial password manager with a self-hosted alternative
- Your use case centers on sharing login credentials across an IT or ops team

## Migration and Integration Tips

Regardless of which tool you choose, follow these practices:

1. **Start with non-critical secrets** — migrate staging credentials first, validate the workflow, then move production
2. **Never commit secrets to version control** — use pre-commit hooks like `gitleaks` or `detect-secrets` to catch accidental commits
3. **Audit access regularly** — review who has access to what, and remove unused credentials quarterly
4. **Back up your secret manager** — Vault Raft snapshots, Infisical database dumps, and Passbolt GPG keys must all be backed up securely and encrypted at rest
5. **Use short-lived tokens where possible** — prefer dynamic secrets and auto-expiring credentials over permanent API keys
6. **Document your setup** — every team member should know how to retrieve secrets, what the access process is, and how to respond if the secret manager becomes unavailable

## Final Recommendation

For most homelab users and small development teams in 2026, **Infisical** offers the best balance of power and usability. The modern interface, native CI/CD integrations, and SDK support make it the fastest path from "secrets scattered everywhere" to "secrets managed centrally."

For larger organizations with complex infrastructure, **HashiCorp Vault** remains unmatched in capability. The dynamic secrets engine, PKI management, and deep cloud integrations justify the steeper learning curve.

For teams focused on credential sharing with strong encryption, **Passbolt** fills the gap between personal password managers and enterprise secret management systems.

All three are open-source, self-hostable, and free for unlimited use. Pick the one that matches your workflow and start centralizing your secrets today.
