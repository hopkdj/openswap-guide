---
title: "Self-Hosted Identity & SSO 2026: Authentik vs Keycloak vs Authelia"
date: 2026-04-12
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "A complete comparison of the top self-hosted identity providers and SSO solutions in 2026. Docker deployments, feature breakdowns, and which one to choose for your homelab or organization."
---

## Why Self-Host Your Identity Provider?

Identity is the new perimeter. Every application, API, and service in your infrastructure needs to know who is calling it and what they are allowed to do. Relying on third-party identity providers — Google, Microsoft Entra ID, Okta — means handing over the master key to your digital ecosystem. You depend on their uptime, their pricing changes, their data retention policies, and their increasingly aggressive telemetry collection.

Self-hosting an identity provider puts authentication and authorization entirely under your control. Your user data never leaves your servers. You define the password policies, the session lifetimes, the multi-factor requirements, and the audit trail. For homelab users, it means a single sign-on experience across dozens of services without relying on external accounts. For organizations, it means compliance with data residency laws, elimination of per-user SaaS fees, and the ability to integrate with internal directories and HR systems.

The self-hosted identity landscape in 2026 is dominated by three projects, each with a distinct philosophy: **Authentik**, **Keycloak**, and **Authelia**. They range from lightweight reverse-proxy-based auth to full-featured enterprise identity platforms. This guide compares all three across architecture, protocols, deployment complexity, and usability — and provides production-ready Docker configurations so you can deploy the right solution for your stack.

---

## The Contenders at a Glance

| Feature | Authentik | Keycloak | Authelia |
|---------|-----------|----------|----------|
| **Language / Stack** | Python (Django) + Go workers | Java (Quarkus) | Go |
| **Database** | PostgreSQL | PostgreSQL, MySQL/MariaDB, MSSQL | SQLite, MySQL, PostgreSQL |
| **License** | Mozilla Public License 2.0 | Apache 2.0 | Apache 2.0 |
| **Protocols** | OIDC, OAuth2, SAML2, LDAP, SCIM | OIDC, OAuth2, SAML2, LDAP, Kerberos | OIDC, OAuth2 (limited), headers-based |
| **Multi-Factor Auth** | TOTP, WebAuthn, Duo, static TOTP, SMS | TOTP, WebAuthn, OTP, SMS, email | TOTP, WebAuthn, Duo, mobile push |
| **Social / External Login** | Google, Microsoft, Apple, Discord, GitHub, GitLab, OIDC, SAML | Google, GitHub, Facebook, Twitter, LinkedIn, OIDC, SAML, LDAP | Limited — mainly internal auth |
| **User Self-Service** | Full portal (password reset, device management) | Full account console | Minimal — no self-service portal |
| **Admin UI** | Modern single-page app | Keycloak Admin Console (recently redesigned) | YAML configuration + minimal web UI |
| **High Availability** | Multi-instance with shared PostgreSQL | Multi-node cluster mode | Single instance (designed for simplicity) |
| **Resource Footprint** | ~500 MB RAM (minimal) | ~1–2 GB RAM (minimal) | ~50–100 MB RAM |
| **Best For** | Homelab to mid-size org (500+ users) | Enterprise, large organizations, compliance | Lightweight homelab, reverse-proxy auth |

---

## Authentik: The Modern All-Rounder

Authentik has become the go-to identity provider for homelab enthusiasts and small-to-medium organizations since its initial release. It balances enterprise-grade protocol support with a modern, intuitive interface that does not require a degree in identity management to operate.

### Key Strengths

**Protocol coverage.** Authentik supports OIDC, OAuth2, SAML2, LDAP, and SCIM out of the box. This means it integrates with virtually any application — from Nextcloud and Gitea to Grafana and Kubernetes. The SAML2 support is particularly useful for legacy enterprise applications that do not support modern OIDC flows.

**Flexible authentication flows.** Authentik uses a visual flow designer that lets you chain authentication stages together. You can require MFA only for external networks, skip it for trusted IP ranges, or inject additional verification steps based on user risk scores. This stage-based architecture is more granular than what Keycloak offers through its native configuration.

**Built-in proxy provider.** For applications that lack native OIDC or SAML support, Authentik can act as a forward authentication proxy. It injects user identity into HTTP headers (`X-Authentik-Username`, `X-Authentik-Groups`) that the backend application reads. This bridges the gap between modern identity protocols and legacy apps without requiring a separate reverse proxy.

**SCIM provisioning.** Authentik supports SCIM 2.0 for automated user provisioning and de-provisioning. When integrated with an external HR system or directory, user accounts are created, updated, and disabled automatically — critical for organizations with frequent onboarding and offboarding cycles.

### Docker Deployment

Authentik consists of three components: a PostgreSQL database, the core server, and a worker process that handles background tasks (email delivery, cleanup, event processing).

```yaml
# docker-compose.yml for Authentik
services:
  postgresql:
    image: docker.io/library/postgres:17-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: authentik
      POSTGRES_PASSWORD: "change-me-to-a-secure-password"
      POSTGRES_DB: authentik
    volumes:
      - authentik-db:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U authentik"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: docker.io/library/redis:7-alpine
    restart: unless-stopped
    volumes:
      - authentik-redis:/data

  server:
    image: ghcr.io/goauthentik/server:2025.4.2
    restart: unless-stopped
    command: server
    environment:
      AUTHENTIK_REDIS__HOST: redis
      AUTHENTIK_POSTGRESQL__HOST: postgresql
      AUTHENTIK_POSTGRESQL__USER: authentik
      AUTHENTIK_POSTGRESQL__PASSWORD: "change-me-to-a-secure-password"
      AUTHENTIK_POSTGRESQL__NAME: authentik
      AUTHENTIK_SECRET_KEY: "generate-a-50-char-random-string-here"
    volumes:
      - ./media:/media
      - ./custom-templates:/templates
    ports:
      - "9000:9000"
    depends_on:
      - postgresql
      - redis

  worker:
    image: ghcr.io/goauthentik/server:2025.4.2
    restart: unless-stopped
    command: worker
    environment:
      AUTHENTIK_REDIS__HOST: redis
      AUTHENTIK_POSTGRESQL__HOST: postgresql
      AUTHENTIK_POSTGRESQL__USER: authentik
      AUTHENTIK_POSTGRESQL__PASSWORD: "change-me-to-a-secure-password"
      AUTHENTIK_POSTGRESQL__NAME: authentik
      AUTHENTIK_SECRET_KEY: "generate-a-50-char-random-string-here"
    user: root
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./media:/media
      - ./certs:/certs
      - ./custom-templates:/templates
    depends_on:
      - postgresql
      - redis

volumes:
  authentik-db:
    driver: local
  authentik-redis:
    driver: local
```

Generate a secure secret key before deploying:

```bash
openssl rand -base64 60
```

After starting the stack with `docker compose up -d`, visit `http://your-server:9000/if/flow/initial-setup/` to complete the initial configuration wizard. The setup creates your admin account and configures the default authentication flow.

### Configuring an OIDC Application

Once Authentik is running, adding an application is straightforward:

1. Navigate to **Applications → Providers** and create an **OAuth2/OpenID Provider**.
2. Set the **Authorization flow** to `default-provider-authorization-implicit-consent` (for interactive apps) or `implicit-consent` (for headless/automated flows).
3. Configure **Redirect URIs/Origins** — these must exactly match your application's callback URL.
4. Navigate to **Applications → Applications** and create a new application, linking it to the provider you just created.
5. The provider generates a **Client ID** and **Client Secret** that you paste into your application's configuration.

For a Grafana integration, the Grafana configuration looks like this:

```ini
[auth.generic_oauth]
enabled = true
name = Authentik
client_id = your-client-id
client_secret = your-client-secret
scopes = openid profile email
auth_url = https://auth.yourdomain.com/application/o/authorize/
token_url = https://auth.yourdomain.com/application/o/token/
api_url = https://auth.yourdomain.com/application/o/userinfo/
```

### When Authentik Shines

Authentik is the best choice when you need broad protocol support with a modern interface and reasonable resource requirements. It handles the full lifecycle — user registration, authentication, authorization, provisioning, and audit logging — without requiring additional components. The flow designer gives you flexibility that neither Keycloak nor Authelia can match for conditional authentication logic.

Its primary limitation is that it is still evolving rapidly. While the core functionality is stable, some advanced enterprise features (fine-grained SCIM attribute mapping, complex SAML attribute transformations) may require workarounds or custom stages.

---

## Keycloak: The Enterprise Standard

Keycloak (now maintained by Red Hat under the upstream project) is the most feature-complete open-source identity provider available. It has been the foundation of enterprise identity infrastructure for over a decade and remains the reference implementation for many OIDC and SAML features.

### Key Strengths

**Unmatched protocol depth.** Keycloak supports OIDC, OAuth2, SAML 2.0, LDAP, and Kerberos. Its SAML implementation is the most thoroughly tested in the open-source ecosystem, making it the natural choice for organizations with legacy enterprise applications that require SAML assertions with specific attribute formats, name ID policies, or encryption requirements.

**User federation.** Keycloak can synchronize users from external LDAP directories (Active Directory, OpenLDAP), Kerberos realms, and custom user storage SPIs. This means you can gradually migrate from an existing identity infrastructure without requiring users to create new accounts. The LDAP sync can run on a schedule or in real-time, and Keycloak supports both read-through and write-through modes.

**Fine-grained authorization.** Keycloak's Authorization Services implement UMA 2.0 (User-Managed Access), allowing resource owners to define fine-grained permissions on individual resources. This goes well beyond simple role-based access control — you can define policies based on user attributes, time of day, IP address, and even custom JavaScript expressions.

**Built-in account management.** Users get a self-service portal where they can manage their profile, configure MFA devices, view active sessions, review login history, and grant or revoke application consents. This reduces the administrative burden on IT teams.

**Admin REST API.** Every operation available in the admin console is also accessible via a comprehensive REST API. This enables automation, infrastructure-as-code management, and integration with external provisioning systems.

### Docker Deployment

Keycloak runs on the Quarkus framework and requires a relational database. The minimal production deployment:

```yaml
# docker-compose.yml for Keycloak
services:
  postgresql:
    image: docker.io/library/postgres:17-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: keycloak
      POSTGRES_PASSWORD: "change-me-to-a-secure-password"
      POSTGRES_DB: keycloak
    volumes:
      - keycloak-db:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U keycloak"]
      interval: 10s
      timeout: 5s
      retries: 5

  keycloak:
    image: quay.io/keycloak/keycloak:26.2
    restart: unless-stopped
    command: start
    environment:
      KC_DB: postgres
      KC_DB_URL: jdbc:postgresql://postgresql:5432/keycloak
      KC_DB_USERNAME: keycloak
      KC_DB_PASSWORD: "change-me-to-a-secure-password"
      KC_HOSTNAME: auth.yourdomain.com
      KC_HOSTNAME_STRICT: "true"
      KC_PROXY: edge
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: "change-me-to-a-secure-admin-password"
      KC_FEATURES: token-exchange,impersonation
    ports:
      - "8080:8080"
    volumes:
      - keycloak-themes:/opt/keycloak/providers
    depends_on:
      postgresql:
        condition: service_healthy

volumes:
  keycloak-db:
    driver: local
  keycloak-themes:
    driver: local
```

For production, you should run Keycloak behind a reverse proxy with TLS termination. The `KC_PROXY: edge` setting tells Keycloak to trust the `X-Forwarded-*` headers from your proxy.

Initialize the admin user and start the server:

```bash
docker compose up -d
# Keycloak starts on http://localhost:8080
# Admin console: http://localhost:8080/admin
```

### Importing a Realm via CLI

Managing Keycloak through the UI is fine for exploration, but production deployments should use infrastructure-as-code. Keycloak supports realm imports:

```bash
# Export your current realm for backup
docker exec keycloak-container \
  /opt/keycloak/bin/kc.sh export \
  --dir /opt/keycloak/data/import \
  --realm your-realm

# Import a realm from a JSON file
docker compose exec keycloak \
  /opt/keycloak/bin/kc.sh import \
  --file /opt/keycloak/data/import/your-realm-realm.json
```

A minimal realm import file defines clients, roles, users, and identity providers in a single JSON structure. This enables version-controlled identity configuration and reproducible deployments.

### Integrating with an Application

For a typical OIDC integration with a self-hosted application:

1. Log into the admin console at `http://localhost:8080/admin`.
2. Create a new **Realm** (or use `master` for simple setups).
3. Navigate to **Clients → Create client** and select **OpenID Connect**.
4. Configure **Valid redirect URIs** with your application's callback URL.
5. Set **Client authentication** to **On** to enable client secrets.
6. Copy the **Client ID** and **Client secret** from the **Credentials** tab.
7. In your application's configuration, set the OIDC issuer to `https://auth.yourdomain.com/realms/your-realm`.

### When Keycloak Shines

Keycloak is the right choice when you need enterprise-grade identity infrastructure: complex user federation with Active Directory, fine-grained authorization policies, comprehensive audit logging, or SAML integrations with legacy systems. It is also the best option when your organization already has Java expertise and can invest in the operational complexity.

The tradeoff is resource consumption and learning curve. Keycloak's Java runtime requires significant memory (1–2 GB minimum), startup times are measured in tens of seconds, and the configuration surface is enormous. For a homelab with a handful of applications, Keycloak is overkill.

---

## Authelia: Lightweight Reverse-Proxy Authentication

Authelia takes a fundamentally different approach. Rather than being a full identity provider, Authelia is a lightweight authentication server designed to sit behind a reverse proxy (Traefik, Nginx, Caddy, or HAProxy). It verifies user identity and passes the result to the backend via HTTP headers — a pattern known as **forward authentication** or **auth request**.

### Key Strengths

**Minimal resource footprint.** Written in Go, Authelia uses 50–100 MB of RAM and starts in under a second. It is designed to run on resource-constrained hardware — Raspberry Pi, low-end VPS instances, or alongside dozens of other containers on a single machine.

**Simple configuration model.** Authelia is configured through a single YAML file. There is no database schema to manage, no admin console to learn, and no realm hierarchy to understand. You define users, access control rules, and authentication methods in one declarative file.

**Strong focus on security defaults.** Authelia enforces secure-by-default configurations: password hashing with Argon2, mandatory HTTPS for all endpoints, rate limiting on authentication attempts, and automatic lockout after repeated failures. It also supports one-time passwords (TOTP) and hardware security keys (WebAuthn/FIDO2) out of the box.

**Pairing with reverse proxies.** Authelia is designed to work with Traefik ForwardAuth, Nginx `auth_request`, Caddy `forward_auth`, or HAProxy `http-request auth-request`. This means you protect any HTTP-based application — even ones with no authentication support at all — by placing them behind the proxy. The proxy delegates authentication to Authelia, which returns allow/deny decisions.

### Docker Deployment

Authelia pairs naturally with Traefik. Here is a complete stack:

```yaml
# docker-compose.yml for Authelia + Traefik
services:
  traefik:
    image: docker.io/library/traefik:v3.3
    restart: unless-stopped
    command:
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--entrypoints.web.http.redirections.entryPoint.to=websecure"
      - "--entrypoints.web.http.redirections.entryPoint.scheme=https"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
      - "--certificatesresolvers.letsencrypt.email=you@yourdomain.com"
      - "--certificatesresolvers.letsencrypt.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - traefik-certs:/letsencrypt

  authelia:
    image: docker.io/authelia/authelia:4.38
    restart: unless-stopped
    volumes:
      - ./authelia-config:/config
    environment:
      - AUTHELIA_IDENTITY_PROVIDERS_OIDC_HMAC_SECRET=your-hmac-secret-at-least-32-chars
      - AUTHELIA_IDENTITY_PROVIDERS_OIDC_ISSUER_PRIVATE_KEY_FILE=/config/oidc-key.pem
      - AUTHELIA_SESSION_SECRET=your-session-secret-at-least-32-chars
      - AUTHELIA_STORAGE_ENCRYPTION_KEY=your-storage-encryption-key-at-least-20-chars
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.authelia.rule=Host(`auth.yourdomain.com`)"
      - "traefik.http.routers.authelia.entrypoints=websecure"
      - "traefik.http.routers.authelia.tls.certresolver=letsencrypt"
      - "traefik.http.routers.authelia.tls=true"
      - "traefik.http.services.authelia.loadbalancer.server.port=9091"
    depends_on:
      - traefik

  # Example protected application
  nextcloud:
    image: docker.io/library/nextcloud:30-apache
    restart: unless-stopped
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.nextcloud.rule=Host(`cloud.yourdomain.com`)"
      - "traefik.http.routers.nextcloud.entrypoints=websecure"
      - "traefik.http.routers.nextcloud.tls.certresolver=letsencrypt"
      - "traefik.http.routers.nextcloud.middlewares=authelia@docker"
    depends_on:
      - traefik

volumes:
  traefik-certs:
    driver: local
```

The Authelia configuration file (`configuration.yml`):

```yaml
# /config/configuration.yml
server:
  host: 0.0.0.0
  port: 9091

log:
  level: info

totp:
  issuer: yourdomain.com
  period: 30
  skew: 1

authentication_backend:
  refresh_interval: 5m
  file:
    path: /config/users_database.yml
    password:
      algorithm: argon2id
      iterations: 1
      memory: 65536
      parallelism: 4
      key_length: 32
      salt_length: 16

session:
  name: authelia_session
  secret: your-session-secret
  expiration: 3600
  inactivity: 300
  same_site: lax

storage:
  encryption_key: your-storage-encryption-key
  local:
    path: /config/db.sqlite3

notifier:
  filesystem:
    filename: /config/notification.txt

access_control:
  default_policy: deny
  rules:
    - domain: "cloud.yourdomain.com"
      policy: two_factor
      subject:
        - "group:admins"
        - "group:users"
    - domain: "monitoring.yourdomain.com"
      policy: one_factor
      subject: "group:readonly"

identity_providers:
  oidc:
    hmac_secret: your-hmac-secret
    issuer_private_key: |
      -----BEGIN PRIVATE KEY-----
      # Generate with: openssl genpkey -algorithm RSA -out oidc-key.pem -pkeyopt rsa_keygen_bits:4096
      -----END PRIVATE KEY-----
    access_token_lifespan: 1h
    authorize_code_lifespan: 1m
    id_token_lifespan: 1h
    refresh_token_lifespan: 90m
    clients:
      - client_id: grafana
        client_name: Grafana
        client_secret: "$pbkdf2-sha256$..."  # Hashed with argon2
        public: false
        authorization_policy: two_factor
        redirect_uris:
          - "https://monitoring.yourdomain.com/login/generic_oauth"
        scopes:
          - openid
          - profile
          - email
        userinfo_signing_algorithm: none
```

The users database file (`users_database.yml`):

```yaml
# /config/users_database.yml
users:
  admin:
    displayname: "Admin User"
    password: "$argon2id$v=19$m=65536,t=1,p=4$..."  # Generate with `authelia crypto hash generate`
    email: admin@yourdomain.com
    groups:
      - admins
  user1:
    displayname: "Regular User"
    password: "$argon2id$v=19$m=65536,t=1,p=4$..."
    email: user1@yourdomain.com
    groups:
      - users
      - readonly
```

Generate password hashes using the Authelia CLI:

```bash
docker run --rm authelia/authelia:4.38 \
  authelia crypto hash generate \
  --algorithm argon2 \
  --password "your-secure-password"
```

### When Authelia Shines

Authelia is the right choice for homelab users who want lightweight, header-based authentication across a fleet of services without the overhead of a full identity provider. Its YAML-based configuration is version-controllable, reproducible, and easy to audit. The integration with Traefik is seamless — you add a single label to any Docker service and it is automatically protected.

The limitations are significant for larger deployments: no user self-service portal, no SCIM provisioning, limited social login support, no built-in user federation with LDAP or Active Directory (though a LDAP backend is available, it is read-only for authentication, not full synchronization), and no fine-grained authorization model beyond group-based access control rules.

---

## Head-to-Head Comparison

### Deployment Complexity

| Aspect | Authentik | Keycloak | Authelia |
|--------|-----------|----------|----------|
| Components | 3 (server, worker, PostgreSQL, Redis) | 2 (Keycloak, PostgreSQL) | 1 (Authelia, optional DB) |
| Initial setup time | 10–15 minutes | 5–10 minutes | 15–30 minutes (config writing) |
| Configuration method | Web UI + API | Web UI + CLI + API | YAML files |
| Learning curve | Moderate | Steep | Low |
| Version upgrades | Straightforward (`docker pull` + restart) | May require database migrations | Drop-in replacement |

### Protocol Support

| Protocol | Authentik | Keycloak | Authelia |
|----------|-----------|----------|----------|
| OpenID Connect | ✅ Full | ✅ Full | ✅ Full |
| OAuth2 | ✅ Full | ✅ Full | ✅ Partial |
| SAML 2.0 | ✅ Full | ✅ Full | ❌ No |
| LDAP (auth) | ✅ Read/Write | ✅ Read/Write | ✅ Read-only |
| LDAP (sync) | ✅ SCIM | ✅ Full sync | ❌ No |
| Kerberos | ❌ No | ✅ Full | ❌ No |
| SCIM 2.0 | ✅ Full | ❌ No | ❌ No |

### Multi-Factor Authentication

| Method | Authentik | Keycloak | Authelia |
|--------|-----------|----------|----------|
| TOTP | ✅ | ✅ | ✅ |
| WebAuthn / FIDO2 | ✅ | ✅ | ✅ |
| Duo Push | ✅ | ✅ | ✅ |
| SMS | ✅ (via stages) | ✅ | ❌ No |
| Email OTP | ✅ | ✅ | ❌ No |
| Push notifications | ✅ (Authentik mobile) | ❌ No | ✅ (via Pushover) |
| Conditional MFA | ✅ (flow-based) | ⚠️ Limited | ⚠️ Per-rule |

### Scalability

| Metric | Authentik | Keycloak | Authelia |
|--------|-----------|----------|----------|
| Max comfortable users | ~500–2,000 | ~50,000+ | ~50–200 |
| Horizontal scaling | Multi-server + shared DB | Clustered nodes | Single instance |
| Session storage | Redis (shared) | Infinispan (distributed) | Local memory / Redis |
| Database load | Moderate | High (Java ORM) | Low |

---

## Decision Framework

Choose based on your actual requirements, not feature checklists:

**Choose Authentik if:**
- You want a modern, intuitive interface with broad protocol support
- You need SAML integration without the complexity of Keycloak
- You run a homelab or small-to-medium organization (under 2,000 users)
- You want SCIM provisioning for automated user lifecycle management
- You value the visual flow designer for conditional authentication logic

**Choose Keycloak if:**
- You need enterprise-grade identity infrastructure at scale
- You have complex user federation requirements (Active Directory, Kerberos)
- You need fine-grained authorization (UMA 2.0, resource-level permissions)
- Your organization has Java operational expertise
- You need SAML with specific attribute mapping and encryption requirements
- You require comprehensive audit logging and compliance reporting

**Choose Authelia if:**
- You want the simplest possible setup for a homelab
- Resource constraints are a primary concern (Raspberry Pi, low-end VPS)
- You are already using Traefik, Nginx, or Caddy as a reverse proxy
- You prefer YAML-based, version-controlled configuration
- You only need basic authentication (passwords + TOTP + WebAuthn)
- You do not need user self-service, social login, or complex provisioning

---

## Securing Your Identity Provider

Regardless of which solution you choose, follow these hardening steps:

**1. Always use TLS.** Never expose an identity provider over plain HTTP. Use Let's Encrypt with automatic renewal via your reverse proxy. Configure `Strict-Transport-Security` headers with a minimum `max-age` of 31,536,000 seconds (one year).

**2. Enable MFA for all administrative accounts.** The identity provider is the master key to your entire infrastructure. Compromise it, and every downstream application is compromised. Require WebAuthn hardware keys for admin accounts — they are resistant to phishing attacks that defeat TOTP.

**3. Restrict access by IP where possible.** If your identity provider is only accessed from your home network or office, configure firewall rules to block external access. For remote access, require a VPN connection before reaching the identity provider.

**4. Back up your database and configuration regularly.** For Authentik, back up the PostgreSQL database and the secret key. For Keycloak, export your realms regularly. For Authelia, version-control your YAML configuration files. Store backups encrypted and offsite.

```bash
# Backup script for Authentik
docker compose exec postgresql pg_dump -U authentik authentik \
  | gzip > /backups/authentik-db-$(date +%Y%m%d).sql.gz

# Backup script for Keycloak
docker compose exec keycloak \
  /opt/keycloak/bin/kc.sh export --dir /tmp/export --realm your-realm
docker cp keycloak:/tmp/export /backups/keycloak-export-$(date +%Y%m%d)

# Authelia — just commit your config to git
cd /path/to/authelia-config && git add -A && git commit -m "Config backup $(date +%Y%m%d)"
```

**5. Monitor authentication failures.** Set up alerting for repeated login failures — they indicate brute-force attacks or credential stuffing attempts. All three solutions expose metrics endpoints that integrate with Prometheus and Grafana.

```yaml
# Prometheus scrape config for Authentik
- job_name: authentik
  static_configs:
    - targets: ["authentik:9300"]
  metrics_path: /metrics

# Prometheus scrape config for Keycloak
- job_name: keycloak
  static_configs:
    - targets: ["keycloak:8080"]
  metrics_path: /metrics

# Prometheus scrape config for Authelia
- job_name: authelia
  static_configs:
    - targets: ["authelia:9091"]
  metrics_path: /metrics
```

---

## Conclusion

The self-hosted identity landscape in 2026 offers three distinct paths, and none of them is universally superior. Authentik delivers the best balance of features and usability for most homelab and small-organization deployments. Keycloak remains the enterprise reference implementation for organizations that need deep protocol support, complex user federation, and fine-grained authorization at scale. Authelia is the lightweight champion for users who want simple, header-based authentication with minimal resource consumption.

The right choice depends on your scale, your protocol requirements, your operational expertise, and your resource constraints. What all three share is the fundamental advantage of self-hosting: your identity data stays on your infrastructure, under your control, with no third-party telemetry, no per-user pricing, and no vendor lock-in.

Start with the Docker configurations above, deploy to a test environment, and integrate one application at a time. Within a few hours, you will have a working SSO experience across your entire self-hosted stack — and the peace of mind that comes with owning your identity infrastructure.
