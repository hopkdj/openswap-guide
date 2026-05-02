---
title: "Self-Hosted Secrets Rotation & Credential Lifecycle Management — Vault vs Infisical vs External Secrets Operator"
date: 2026-05-02T08:38:00Z
tags: ["secrets-management", "security", "vault", "docker", "kubernetes", "self-hosted"]
draft: false
---

Managing static credentials is one of the most common security risks in modern infrastructure. When API keys, database passwords, and TLS certificates never change, a single breach exposes your entire system. **Secrets rotation** — the automated, periodic replacement of credentials — eliminates this risk by ensuring that compromised credentials have a limited blast radius.

In this guide, we compare three self-hosted platforms for secrets rotation and credential lifecycle management: **HashiCorp Vault**, **Infisical**, and **External Secrets Operator**. While our [Kubernetes secrets management comparison](../2026-04-20-external-secrets-operator-vs-sealed-secrets-vs-vault-secrets-operator-kubernetes-secrets-management-2026/) covers deployment options, this article focuses specifically on automated rotation capabilities, credential lifecycle workflows, and integration patterns.

## Why Secrets Rotation Matters

Static credentials are a security liability. When a developer leaves, a server is compromised, or a dependency is breached, rotating credentials manually is slow, error-prone, and often skipped entirely. Automated rotation solves this by:

- **Limiting credential lifetime** — secrets expire and are replaced automatically
- **Reducing blast radius** — compromised credentials become useless within hours
- **Meeting compliance requirements** — SOC 2, PCI-DSS, and HIPAA mandate credential rotation
- **Eliminating human error** — no more forgotten password changes after team departures

## Comparison Table

| Feature | HashiCorp Vault | Infisical | External Secrets Operator |
|---------|----------------|-----------|--------------------------|
| **GitHub Stars** | 35,552 | 26,435 | 2,585 |
| **Primary Model** | Secrets-as-a-Service platform | Developer-first secrets manager | Kubernetes-native sync |
| **Auto-Rotation** | Built-in rotation engine | Built-in rotation with webhooks | Sync + triggers rotation |
| **Rotation Targets** | Databases, cloud providers, PKI | Databases, APIs, SSH keys | Kubernetes Secrets |
| **Rotation Scheduling** | TTL-based, renewable | Cron-based, configurable | Kubernetes CronJob triggers |
| **Dynamic Secrets** | Yes (database, cloud, SSH, PKI) | Yes (limited providers) | No (syncs static secrets) |
| **Audit Logging** | Comprehensive | Full audit trail | Kubernetes events |
| **Web UI** | Limited (CLI-first) | Full dashboard | No (Kubernetes-native) |
| **API** | REST + CLI | REST + CLI | Kubernetes CRDs |
| **Deployment** | Docker, Kubernetes, binary | Docker Compose, Kubernetes | Kubernetes only (Helm) |
| **Encryption** | Shamir's Secret Sharing | AES-256-GCM | Kubernetes encryption at rest |
| **Cloud Integration** | AWS, GCP, Azure, K8s | AWS, GCP, Azure, K8s | AWS, GCP, Azure, Vault |

## HashiCorp Vault

Vault is the industry-standard secrets management platform. Its rotation engine is built around **dynamic secrets** — credentials generated on-demand with automatic expiration — and a powerful **rotation daemon** that can periodically rotate credentials for databases, cloud providers, and SSH keys.

**Key rotation features:**
- **Database rotation** — automatically rotates database credentials on a schedule, creating new users and passwords without downtime
- **Cloud credential rotation** — generates short-lived AWS IAM, GCP service account, and Azure managed identity credentials
- **PKI rotation** — manages certificate authorities with automatic certificate renewal before expiration
- **SSH rotation** — generates SSH key pairs and signed certificates with configurable TTLs
- **Transform secrets engine** — rotates encryption keys for tokenized data

**When to use:** Enterprise environments requiring comprehensive secrets rotation across multiple platforms with strict audit and compliance requirements.

### Docker Compose Deployment

```yaml
version: '3.8'
services:
  vault:
    image: hashicorp/vault:latest
    container_name: vault
    cap_add:
      - IPC_LOCK
    ports:
      - "8200:8200"
    environment:
      VAULT_ADDR: "http://0.0.0.0:8200"
      VAULT_API_ADDR: "http://0.0.0.0:8200"
    volumes:
      - vault-data:/vault/file
      - ./vault-config:/vault/config
    command: "vault server -config=/vault/config/vault.hcl"
    restart: unless-stopped

volumes:
  vault-data:

networks:
  default:
    driver: bridge
```

Vault configuration (`vault-config/vault.hcl`):

```hcl
storage "file" {
  path = "/vault/file"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1
}

ui = true
```

Configure database credential rotation:

```bash
# Initialize and unseal
vault operator init
vault operator unseal

# Enable database secrets engine
vault secrets enable database

# Configure PostgreSQL connection with rotation
vault write database/config/postgresql \
  plugin_name=postgresql-database-plugin \
  connection_url="postgresql://{{username}}:{{password}}@postgres:5432/mydb" \
  allowed_roles="readonly" \
  username="vault" \
  password="vault-password"

# Create rotation role (credentials rotate every 24h)
vault write database/roles/readonly \
  db_name=postgresql \
  creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; GRANT SELECT ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
  default_ttl="1h" \
  max_ttl="24h"

# Get rotated credentials
vault read database/creds/readonly
```

## Infisical

Infisical is a developer-first secrets management platform with a focus on ease of use. It provides automated secrets rotation with a clean web UI, SDK integrations, and support for rotating database credentials, API keys, and SSH keys.

**Key rotation features:**
- **Secret rotation with webhooks** — triggers webhooks when secrets rotate, enabling downstream systems to update
- **Folder-level access control** — granular permissions for who can view, edit, or rotate secrets
- **Secret versioning** — full history of all secret changes with rollback capability
- **SDK integration** — rotate secrets programmatically via Python, Node.js, Go, and Rust SDKs
- **Environment-scoped secrets** — different rotation schedules per environment (dev, staging, prod)

**When to use:** Development teams wanting a user-friendly secrets manager with rotation capabilities and SDK integrations.

### Docker Compose Deployment

```yaml
version: '3.8'
services:
  infisical-postgres:
    image: postgres:16-alpine
    container_name: infisical-postgres
    environment:
      POSTGRES_DB: infisical
      POSTGRES_USER: infisical
      POSTGRES_PASSWORD: infisical-password
    volumes:
      - infisical-db:/var/lib/postgresql/data
    networks:
      - infisical-network

  infisical-redis:
    image: redis:7-alpine
    container_name: infisical-redis
    networks:
      - infisical-network

  infisical-backend:
    image: infisical/backend:latest
    container_name: infisical-backend
    depends_on:
      - infisical-postgres
      - infisical-redis
    environment:
      NODE_ENV: production
      MONGO_URI: "mongodb://infisical-mongo:27017"
      POSTGRES_DB: infisical
      POSTGRES_HOST: infisical-postgres
      POSTGRES_USER: infisical
      POSTGRES_PASSWORD: infisical-password
      REDIS_URL: "redis://infisical-redis:6379"
      SITE_URL: "http://localhost:8080"
    ports:
      - "8080:8080"
    networks:
      - infisical-network
    restart: unless-stopped

volumes:
  infisical-db:

networks:
  infisical-network:
    driver: bridge
```

## External Secrets Operator

External Secrets Operator (ESO) is a Kubernetes operator that synchronizes secrets from external secret managers into Kubernetes Secret objects. While ESO itself doesn't rotate secrets, it integrates with Vault, AWS Secrets Manager, and other rotation-capable backends to ensure rotated credentials are automatically synced to your cluster.

**Key rotation integration features:**
- **Refresh interval** — configurable sync intervals that pick up rotated secrets from backends
- **Secret store abstraction** — rotate secrets in your backend (Vault, AWS) and ESO syncs automatically
- **Controller-based** — no cron jobs needed; the operator watches for changes and syncs in real-time
- **Composition** — combine secrets from multiple backends into a single Kubernetes Secret

**When to use:** Kubernetes-native teams that already use an external secrets manager and want automatic sync of rotated credentials to pods.

### Kubernetes Deployment

ESO is deployed via Helm and configured with Custom Resource Definitions:

```yaml
# ExternalSecret that syncs from Vault with rotation
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: database-credentials
  namespace: production
spec:
  refreshInterval: "1h"  # Pick up rotated credentials every hour
  secretStoreRef:
    name: vault-store
    kind: ClusterSecretStore
  target:
    name: db-credentials
    creationPolicy: Owner
  data:
    - secretKey: username
      remoteRef:
        key: database/creds/readonly
        property: username
    - secretKey: password
      remoteRef:
        key: database/creds/readonly
        property: password
```

## Building a Rotation Pipeline

A production-ready secrets rotation pipeline combines all three approaches:

1. **Vault** generates and rotates database credentials on a 24-hour schedule
2. **Infisical** manages API keys with webhook-triggered rotation when thresholds are reached
3. **External Secrets Operator** syncs the latest credentials from Vault to Kubernetes pods every hour

This layered approach ensures credentials are rotated at the source, tracked in a developer-friendly UI, and automatically distributed to consuming applications.

## Why Self-Host Secrets Rotation?

Cloud-managed secrets services (AWS Secrets Manager, Azure Key Vault) charge per secret and per API call. At scale, costs add up quickly. Self-hosted rotation gives you unlimited secrets, no per-operation pricing, and full audit control. For [secrets encryption in Git workflows](../2026-04-23-mozilla-sops-vs-git-crypt-vs-age-self-hosted-secrets-encryption-git-guide-2026/), combining rotation with encrypted-in-repo secrets provides both operational agility and version-controlled audit trails. Organizations managing [container security](../2026-04-24-self-hosted-container-image-scanning-trivy-grype-clair-anchore-guide-2026/) should also rotate image registry credentials to prevent supply chain compromise.

## FAQ

### What is the difference between secrets management and secrets rotation?

Secrets management covers storing, accessing, and distributing credentials. Secrets rotation is a subset — the automated process of periodically replacing credentials with new ones. A secrets manager may not support rotation (it just stores), but a rotation-capable platform generates new credentials and deactivates old ones on a schedule.

### How often should I rotate secrets?

For database credentials: every 24 hours to 7 days. For API keys: every 30 to 90 days. For TLS certificates: before expiration (typically 90 days for Let's Encrypt). Critical infrastructure secrets (root database passwords, CA private keys) should be rotated less frequently with careful planning.

### Can Vault rotate secrets for databases it doesn't natively support?

Vault's database secrets engine supports PostgreSQL, MySQL, MongoDB, Cassandra, Oracle, MSSQL, Elasticsearch, and more via plugins. For unsupported databases, you can write a custom plugin using Vault's database plugin SDK, or use the generic key-value rotation with custom scripts.

### Does External Secrets Operator rotate secrets itself?

No. ESO is a synchronization layer — it copies secrets from external managers (Vault, AWS Secrets Manager, etc.) into Kubernetes. The actual rotation happens in the backend system. ESO's role is to ensure rotated secrets reach your pods within the configured refresh interval.

### What happens to applications during credential rotation?

With dynamic secrets, Vault generates new credentials on each request, so there's no "during" — applications always use current credentials. With static secret rotation, there's a brief window where old and new credentials coexist. Applications should implement retry logic and credential refresh mechanisms to handle this transition gracefully.

### Can I rotate secrets without restarting my applications?

Yes. Most modern applications support hot-reloading credentials. Database connection pools (PgBouncer, HikariCP) can refresh connections with new credentials. HTTP clients can reload API keys from environment variables or config files. The key is designing applications to detect and use updated credentials without requiring a full restart.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Secrets Rotation & Credential Lifecycle Management — Vault vs Infisical vs External Secrets Operator",
  "description": "Compare HashiCorp Vault, Infisical, and External Secrets Operator for automated secrets rotation and credential lifecycle management in self-hosted infrastructure.",
  "datePublished": "2026-05-02",
  "dateModified": "2026-05-02",
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
