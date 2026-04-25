---
title: "Dex vs Kanidm vs Rauthy: Lightweight Self-Hosted SSO & OIDC Guide 2026"
date: 2026-04-25
tags: ["comparison", "guide", "self-hosted", "authentication", "sso", "oidc"]
draft: false
description: "Compare Dex, Kanidm, and Rauthy for self-hosted Single Sign-On and OpenID Connect. Learn which lightweight identity provider fits your infrastructure in 2026."
---

When you run a self-hosted infrastructure with multiple services, managing authentication across every application becomes a pain point quickly. Running separate login systems for Grafana, Gitea, Nextcloud, and your internal tools means separate passwords, separate user databases, and a support nightmare.

That is where a self-hosted Single Sign-On (SSO) provider with OpenID Connect (OIDC) support comes in. Instead of each service managing its own users, they all delegate authentication to a single identity provider you control.

In this guide, we compare three lightweight, open-source options that serve different niches in the self-hosted authentication landscape: **Dex**, **Kanidm**, and **Rauthy**. All three are actively maintained, support OIDC, and can run in Docker containers on a single server.

If you are already familiar with full-featured IAM suites, see our [comparison of Zitadel, Ory, and Keycloak](../zitadel-vs-ory-vs-keycloak-self-hosted-iam-guide/) for enterprise-grade alternatives. For a lighter reverse-proxy authentication approach, check our [OAuth2-Proxy vs Pomerium guide](../oauth2-proxy-vs-pomerium-vs-traefik-forward-auth-2026/).

## Why Self-Host Your Identity Provider

Cloud-based SSO solutions like Okta, Auth0, or Azure AD are convenient, but they come with trade-offs:

- **Vendor lock-in** — migrating away from a cloud IdP is difficult and costly
- **Data privacy** — user credentials and authentication logs leave your infrastructure
- **Downtime risk** — if your cloud IdP goes down, none of your services can authenticate
- **Cost at scale** — per-user pricing adds up quickly for homelabs, small teams, or MSPs

A self-hosted identity provider keeps user data on your servers, eliminates subscription costs, and gives you full control over authentication policies, connectors, and user lifecycle management.

## Dex: The Kubernetes-Native OIDC Connector

**Dex** (github.com/dexidp/dex) is an OpenID Connect identity and OAuth 2.0 provider with pluggable connectors to various upstream identity providers. It was originally developed by CoreOS and is now maintained by the dexidp organization.

**GitHub stats (live):** 10,769 stars | Last updated: April 24, 2026 | Language: Go

### Key Features

- **Connector architecture** — Dex does not store user credentials itself. Instead, it connects to upstream identity providers like LDAP, GitHub, Google, Microsoft, SAML, GitLab, and many more
- **Kubernetes-native** — designed as a sidecar or standalone deployment in Kubernetes clusters, widely used as the authentication layer for ArgoCD and other Kubernetes tools
- **Lightweight** — compiled Go binary, minimal resource footprint (~50MB RAM)
- **Storage backends** — supports SQLite, PostgreSQL, MySQL, etcd, and Kubernetes CRDs
- **Static users** — can also store local users with hashed passwords via the `staticPasswords` config

### What Dex Is NOT

Dex is not a full identity management platform. It does not provide:
- A user self-service portal for password resets
- Group management or role-based access control
- MFA/TOTP support natively (relies on upstream providers)
- An admin UI for managing users

Think of Dex as an **OIDC translation layer** — it takes authentication from your existing identity sources and presents them as a standard OIDC provider to your applications.

### Docker Compose Deployment

Dex provides a Docker image and a sample configuration. Here is a minimal production-ready setup with SQLite storage and a GitHub connector:

```yaml
# docker-compose.yml — Dex with SQLite and GitHub connector
version: "3.8"

services:
  dex:
    image: ghcr.io/dexidp/dex:v2.41.1
    container_name: dex
    restart: unless-stopped
    ports:
      - "5556:5556"
    volumes:
      - ./dex-config.yaml:/etc/dex/config.yaml:ro
      - dex-data:/var/dex
    command: ["dex", "serve", "/etc/dex/config.yaml"]

volumes:
  dex-data:

# dex-config.yaml
issuer: https://auth.example.com/dex

storage:
  type: sqlite3
  config:
    file: /var/dex/dex.db

web:
  http: 0.0.0.0:5556

staticClients:
  - id: grafana
    redirectURIs:
      - 'https://grafana.example.com/login/generic_oauth'
    name: 'Grafana'
    secret: grafana-secret

enablePasswordDB: true
staticPasswords:
  - email: "admin@example.com"
    hash: "$2a$10$2b2cU8CPhOTaGrs1HRQuAueS7JTT5ZHsHSzYiFPnz1leZg7Hzfd9u"
    username: "admin"
    userID: "08a8684b-db88-4b73-90a9-3cd1661f5466"

connectors:
  - type: github
    id: github
    name: GitHub
    config:
      clientID: $GITHUB_CLIENT_ID
      clientSecret: $GITHUB_CLIENT_SECRET
      redirectURI: https://auth.example.com/dex/callback
```

To generate password hashes for `staticPasswords`, use `bcrypt` or Dex's built-in `dex hash-password` command.

## Kanidm: The Modern Rust Identity Platform

**Kanidm** (github.com/kanidm/kanidm) is a simple, secure, and fast identity management platform written in Rust. It is designed as a full replacement for traditional LDAP/Active Directory deployments, providing both LDAP and OIDC interfaces from a single system.

**GitHub stats (live):** 4,868 stars | Last updated: April 24, 2026 | Language: Rust

### Key Features

- **Full identity management** — user self-service, password resets, group management, and role-based access control built in
- **Built-in LDAP** — acts as an LDAP server, making it compatible with legacy applications that require LDAP authentication
- **OAuth2/OIDC provider** — native support for OIDC and OAuth2 flows with a built-in web UI
- **Passkey/WebAuthn support** — modern passwordless authentication via FIDO2 passkeys
- **Credential exchange** — supports TOTP, WebAuthn, and password-based authentication
- **Audit logging** — comprehensive audit trail for all identity operations
- **Access profiles** — fine-grained authorization with service accounts and API tokens

### Kanidm Architecture

Kanidm uses a unique two-process architecture:
- **kanidmd** — the server daemon handling all identity operations
- **kanidm_tools** — the CLI client for administration

The server stores data in an embedded Berkeley DB, eliminating the need for an external database. This simplifies deployment significantly.

### Docker Compose Deployment

Kanidm provides official Docker images. Here is a production deployment:

```yaml
# docker-compose.yml — Kanidm production setup
version: "3.8"

services:
  kanidm:
    image: docker.io/kanidm/server:1.9.4
    container_name: kanidm
    restart: unless-stopped
    volumes:
      - kanidm-db:/data
      - ./kanidm/server.toml:/etc/kanidm/server.toml:ro
      - ./kanidm/certs:/etc/kanidm/certs:ro
    ports:
      - "8443:8443"   # Web UI + API
      - "3636:3636"   # LDAP (optional)
    environment:
      - KANIDM_SSL_CERT_PATH=/etc/kanidm/certs/cert.pem
      - KANIDM_SSL_KEY_PATH=/etc/kanidm/certs/key.pem

  kanidm-cli:
    image: docker.io/kanidm/tools:1.9.4
    container_name: kanidm-cli
    volumes:
      - ./kanidm/cli.toml:/etc/kanidm/cli.toml:ro
      - ./kanidm/certs:/etc/kanidm/certs:ro
    entrypoint: ["sh", "-c", "sleep infinity"]
    profiles: ["cli"]

volumes:
  kanidm-db:

# kanidm/server.toml
bindaddress = "[::]:8443"
ldapbindaddress = "[::]:3636"
origin = "https://idm.example.com:8443"
db_path = "/data/kanidm.db"
tls_chain = "/etc/kanidm/certs/cert.pem"
tls_key = "/etc/kanidm/certs/key.pem"
domain = "idm.example.com"
```

After initial deployment, bootstrap the server with:

```bash
# Enter the container and run initial setup
docker exec -it kanidm /bin/bash

# Reset the system to initial state (first run only)
kanidmd recover-account --config /etc/kanidm/server.toml idm_admin

# Create your first admin user
kanidmd recover-account --config /etc/kanidm/server.toml admin
```

## Rauthy: The Lightweight Rust SSO Server

**Rauthy** (github.com/sebadob/rauthy) is a single sign-on identity and access management solution supporting OpenID Connect, OAuth 2.0, and PAM. Written in Rust, it aims to be a lightweight alternative to heavy IAM platforms while still providing a complete feature set.

**GitHub stats (live):** 1,087 stars | Last updated: April 24, 2026 | Language: Rust

### Key Features

- **Complete SSO platform** — user management, groups, roles, and client applications all built in
- **Web-based admin UI** — full administration interface for managing users, clients, and policies
- **MFA support** — built-in TOTP and passkey/WebAuthn support
- **Email provider integration** — SMTP-based email flows for password resets and verification
- **OIDC and OAuth 2.0** — full standard compliance for modern and legacy applications
- **Single binary** — no external database required (uses embedded SQLite or optional PostgreSQL)
- **API-first design** — RESTful API for automation and integration
- **Branding customization** — customizable login pages with your own logo and colors

### Rauthy Architecture

Rauthy is designed as a single-process application with an embedded database by default. The frontend and backend are bundled together, making deployment straightforward. It supports PostgreSQL for production deployments where SQLite's limitations become a concern.

### Docker Compose Deployment

Rauthy ships with Docker images and bootstrap configuration files. Here is a deployment with PostgreSQL backend:

```yaml
# docker-compose.yml — Rauthy with PostgreSQL
version: "3.8"

services:
  rauthy:
    image: ghcr.io/sebadob/rauthy:0.30.1
    container_name: rauthy
    restart: unless-stopped
    ports:
      - "8443:8443"
    environment:
      - DATABASE_URL=postgresql://rauthy:rauthy@postgres:5432/rauthy
      - RAUTHY_ADMIN_EMAIL=admin@example.com
      - RAUTHY_ISSUER=https://auth.example.com
      - SMTP_URL=smtp://mail.example.com:587
      - SMTP_USERNAME=rauthy@example.com
      - SMTP_PASSWORD=your-smtp-password
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - rauthy-config:/etc/rauthy

  postgres:
    image: postgres:17-alpine
    container_name: rauthy-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: rauthy
      POSTGRES_USER: rauthy
      POSTGRES_PASSWORD: rauthy
    volumes:
      - rauthy-pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U rauthy"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  rauthy-config:
  rauthy-pgdata:
```

After the container starts, access the admin UI at `https://localhost:8443/rauthy/admin` and log in with the admin credentials provided in the container logs.

## Feature Comparison

| Feature | Dex | Kanidm | Rauthy |
|---------|-----|--------|--------|
| **Language** | Go | Rust | Rust |
| **GitHub Stars** | 10,769 | 4,868 | 1,087 |
| **OIDC Provider** | Yes | Yes | Yes |
| **OAuth 2.0** | Yes | Yes | Yes |
| **LDAP Server** | No (client only) | Yes (full server) | No |
| **User Self-Service** | No | Yes | Yes |
| **Admin UI** | No | Yes | Yes |
| **MFA / TOTP** | Via upstream | Built-in | Built-in |
| **Passkey / WebAuthn** | Via upstream | Built-in | Built-in |
| **Password Database** | Static only | Built-in | Built-in |
| **External Connectors** | 15+ (LDAP, GitHub, Google, SAML, etc.) | LDAP sync, SCIM | Email-based |
| **Database Backend** | SQLite, PostgreSQL, MySQL, etcd, K8s CRDs | Embedded Berkeley DB | SQLite, PostgreSQL |
| **Kubernetes Native** | Yes (designed for K8s) | No | No |
| **Docker Image Size** | ~30 MB | ~60 MB | ~45 MB |
| **API** | REST | REST + CLI | REST |
| **Audit Logging** | Basic | Comprehensive | Basic |
| **Email Flows** | No | No | Yes (password reset, verification) |
| **Branding** | Minimal | Moderate | Full customization |

## When to Choose Each

### Choose Dex When

- You already have an identity provider (Active Directory, LDAP, GitHub org, Google Workspace) and just need an OIDC bridge
- You are running Kubernetes and need authentication for ArgoCD, Dashboard, or other K8s tools
- You want the smallest possible footprint and do not need user management features
- Your applications only need OIDC authentication and you handle authorization separately

Dex excels as a **thin OIDC layer** on top of existing identity infrastructure. It is not meant to replace your identity store — it translates it.

### Choose Kanidm When

- You need a complete replacement for Active Directory or OpenLDAP
- You want both LDAP and OIDC from a single system
- You need user self-service, group management, and role-based access control
- You want modern authentication features like passkeys and TOTP out of the box
- You value audit trails and comprehensive identity governance

Kanidm is the **full-featured identity platform** in this comparison. It is opinionated about security defaults and aims to be a drop-in replacement for traditional directory services.

### Choose Rauthy When

- You want a lightweight SSO with a built-in admin UI
- You need email-based flows (password reset, email verification) without adding external services
- You prefer a single binary deployment with optional PostgreSQL
- You want customizable branding and login pages
- You need a middle ground between Dex (too minimal) and Kanidm (too comprehensive)

Rauthy sits in the **practical middle ground** — more features than Dex, lighter than Kanidm, with a focus on ease of deployment and use.

## Integration Examples

### Integrating Grafana with Dex

```yaml
# grafana.ini — OIDC configuration for Dex
[auth.generic_oauth]
enabled = true
name = Dex
client_id = grafana
client_secret = grafana-secret
scopes = openid profile email groups
auth_url = https://auth.example.com/dex/auth
token_url = https://auth.example.com/dex/token
api_url = https://auth.example.com/dex/userinfo
```

### Integrating Nextcloud with Kanidm

```php
// config/config.php — OIDC for Kanidm
'oidc_login_provider_url' => 'https://idm.example.com:8443',
'oidc_login_client_id' => 'nextcloud-client-id',
'oidc_login_client_secret' => 'nextcloud-client-secret',
'oidc_login_auto_redirect' => true,
'oidc_login_redir_fallback' => false,
```

### Integrating Gitea with Rauthy

```ini
# app.ini — OAuth2 configuration for Rauthy
[oauth2]
ENABLED = true
[oauth2.rauthy]
AUTH_URL = https://auth.example.com/authorize
TOKEN_URL = https://auth.example.com/token
PROFILE_URL = https://auth.example.com/oidc/profile
ICON_URL = /img/auth/rauthy.svg
```

## FAQ

### What is the difference between Dex and a full IAM platform like Keycloak?

Dex is an OIDC connector, not a full identity management platform. It does not store user passwords, manage groups, or provide an admin UI. Instead, it connects to existing identity providers (LDAP, GitHub, Google, SAML) and presents them as a unified OIDC provider. Keycloak, by contrast, is a complete IAM suite with user management, admin console, MFA, and social login built in. Choose Dex when you already have an identity source; choose Keycloak when you need to build one from scratch.

### Can Dex handle MFA (multi-factor authentication)?

Dex does not implement MFA natively. It relies on upstream identity providers to handle MFA. If your LDAP server requires TOTP, or your GitHub organization enforces 2FA, Dex passes through that authentication. For native MFA support, consider Kanidm or Rauthy, both of which include TOTP and WebAuthn/passkey support.

### Does Kanidm support Active Directory integration?

Yes. Kanidm can sync users and groups from Active Directory via its LDAP sync feature. It pulls AD data and creates corresponding Kanidm accounts, allowing a gradual migration from AD to Kanidm. You can also keep Kanidm in read-only sync mode if you want AD to remain the source of truth.

### How does Rauthy handle user registration?

Rauthy supports both self-registration (users create their own accounts via the login page) and admin-created accounts. Email verification can be required for self-registered accounts if SMTP is configured. Admin accounts can be pre-populated using the bootstrap configuration files.

### Which of these three is the easiest to deploy on a single server?

Rauthy is the simplest for single-server deployments. A single Docker container with an optional PostgreSQL sidecar gets you a fully functional SSO with admin UI, user management, MFA, and email flows. Dex is also simple to deploy but lacks user management, meaning you still need a separate identity source. Kanidm requires more initial configuration (certificate setup, bootstrap process) but provides the most complete feature set once running.

### Can I migrate users between these systems?

Migration paths vary. Dex has no user database to migrate (users live in upstream providers). Kanidm can import LDAP data and provides tools for bulk user creation. Rauthy supports SCIM 2.0 for programmatic user management. For large migrations, exporting user data from your current system and using each tool's API or import mechanisms is recommended.

## Summary

| | Dex | Kanidm | Rauthy |
|---|---|---|---|
| **Best for** | Kubernetes auth, OIDC bridging | AD/LDAP replacement | Lightweight SSO with UI |
| **Complexity** | Low | Medium | Low-Medium |
| **Feature depth** | Connector-focused | Full IAM platform | Practical SSO |
| **Learning curve** | Gentle (if you know OIDC) | Steep (many concepts) | Gentle |
| **Community size** | Largest (10K+ stars) | Growing (4.8K stars) | Emerging (1K stars) |

For related reading, see our [lightweight LDAP authentication guide](../lldap-vs-glauth-lightweight-ldap-self-hosted-auth-guide/) for alternatives when you need directory services, and our [SSO comparison of Casdoor, Zitadel, and Authentik](../casdoor-vs-zitadel-vs-authentik-lightweight-sso-guide-2026/) for a look at other identity providers in this space.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Dex vs Kanidm vs Rauthy: Lightweight Self-Hosted SSO & OIDC Guide 2026",
  "description": "Compare Dex, Kanidm, and Rauthy for self-hosted Single Sign-On and OpenID Connect. Learn which lightweight identity provider fits your infrastructure in 2026.",
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
