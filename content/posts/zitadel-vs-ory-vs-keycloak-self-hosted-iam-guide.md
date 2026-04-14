---
title: "Self-Hosted Identity & Access Management 2026: Zitadel vs Ory vs Keycloak"
date: 2026-04-14
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete guide to self-hosted IAM platforms in 2026. Compare Zitadel, Ory, and Keycloak with production-ready Docker deployments, architecture breakdowns, and decision framework for your organization."
---

## Why Self-Host Your Identity & Access Management Platform?

Every organization — from a two-person startup to a multinational enterprise — faces the same fundamental challenge: who gets access to what, and how do you prove it? Identity and Access Management (IAM) is the backbone of security infrastructure. It handles authentication (verifying identity), authorization (determining permissions), user lifecycle management (onboarding, role changes, offboarding), and audit compliance.

Cloud-hosted IAM solutions like Okta, Auth0, and Microsoft Entra ID have become expensive at scale. Pricing models charge per active user, per authentication event, or per integration — costs that compound rapidly as your team and service count grow. Beyond pricing, there are structural risks: vendor lock-in, unpredictable price increases, data residency constraints under GDPR and SOC 2 requirements, and single points of failure when your identity provider goes down.

Self-hosting an IAM platform gives you complete ownership of user data, unlimited user scaling without per-seat fees, full control over security policies, and the ability to integrate with any internal system — HR databases, directory services, custom applications — without waiting for a vendor to build a connector. The trade-off is operational responsibility: you manage the infrastructure, handle upgrades, and ensure availability. For teams that already run Docker and manage a handful of services, this overhead is minimal compared to the long-term savings and autonomy.

This guide compares three of the most capable self-hosted IAM platforms available in 2026: **Zitadel**, **Ory**, and **Keycloak**. Each takes a fundamentally different architectural approach, from cloud-native multi-tenancy to modular microservices to monolithic enterprise maturity.

---

## The Contenders at a Glance

| Feature | Zitadel | Ory | Keycloak |
|---------|---------|-----|----------|
| **Language / Stack** | Go | Go | Java (Quarkus) |
| **Database** | PostgreSQL, CockroachDB | PostgreSQL, SQLite, MySQL (per component) | PostgreSQL, MySQL/MariaDB, MSSQL |
| **License** | Apache 2.0 (core), BSL for cloud features | Apache 2.0 | Apache 2.0 |
| **Architecture** | Monolithic binary, multi-tenant by design | Modular microservices (one binary per function) | Monolithic (Quarkus runtime) |
| **OIDC / OAuth2** | Full (all flows) | Full (via Ory Hydra) | Full (all flows) |
| **SAML 2.0** | Yes (Enterprise) | Via Ory Kratos + custom integration | Yes (native) |
| **User Management** | Built-in with org-scoped users | Via Ory Kratos (configurable identity schema) | Built-in with realm-scoped users |
| **API-First** | Yes — everything accessible via gRPC + REST API | Yes — every component exposes REST + OpenAPI | Partial — admin console primary, REST API secondary |
| **Machine / Service Accounts** | Native (PATs, service keys, JWT profiles) | Via Ory Hydra (OAuth2 client credentials) | Via service accounts + client credentials |
| **Audit Trail** | Immutable event-sourced ledger | Manual audit logging setup | Admin events log (configurable) |
| **Multi-Tenancy** | First-class (organizations as tenants) | Custom implementation via identity schema | Via realms (logical separation) |
| **Resource Footprint** | ~150–300 MB RAM | ~50–150 MB RAM per component | ~800 MB – 2 GB RAM |
| **Best For** | Startups, SaaS products, multi-tenant apps | Teams wanting modular composable auth | Enterprises, legacy integrations, compliance-heavy environments |

---

## Zitadel: Cloud-Native IAM with Event Sourcing

Zitadel was designed from the ground up as a cloud-native identity platform. Its defining architectural choice is **event sourcing**: every action (user creation, login, role assignment, password change) is stored as an immutable event in the database. This provides a complete, tamper-proof audit trail without any additional configuration.

### Architecture and Design

Zitadel runs as a single Go binary that handles all IAM functions — user management, authentication, API, and administration. Behind the scenes, it uses an event store pattern where the current state is derived by replaying events. This approach means you can reconstruct the state of any user, organization, or permission at any point in time, which is invaluable for compliance audits and incident investigations.

The platform organizes users into **organizations**, making it naturally multi-tenant. Each organization has its own settings, branding, identity providers, and user base. This is particularly powerful for B2B SaaS products where each customer needs isolated identity management with custom branding and policies.

### Deployment with Docker Compose

```yaml
version: "3.8"

services:
  zitadel:
    image: ghcr.io/zitadel/zitadel:v2.67.2
    command: start-from-init --masterkey "MasterkeyNeeds32CharsMinimum" --tlsMode disabled
    ports:
      - "8080:8080"
    environment:
      ZITADEL_DATABASE_POSTGRES_HOST: db
      ZITADEL_DATABASE_POSTGRES_PORT: 5432
      ZITADEL_DATABASE_POSTGRES_DATABASE: zitadel
      ZITADEL_DATABASE_POSTGRES_USER_USERNAME: zitadel
      ZITADEL_DATABASE_POSTGRES_USER_PASSWORD: zitadel_secret
      ZITADEL_DATABASE_POSTGRES_ADMIN_USERNAME: postgres
      ZITADEL_DATABASE_POSTGRES_ADMIN_PASSWORD: postgres_secret
      ZITADEL_EXTERNALSECURE: "false"
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres_secret
    volumes:
      - zitadel-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  zitadel-data:
```

After starting the stack, Zitadel initializes its database schema automatically. The admin console becomes available at `http://localhost:8080/ui/console`. The first login uses the default instance administrator credentials shown in the startup logs.

### Key Features

**Machine authentication.** Zitadel treats service-to-service communication as a first-class concern. You can create machine users that authenticate via Personal Access Tokens (PATs), service keys, or JWT profiles. This eliminates the need for API keys scattered across configuration files — each service gets its own identity with scoped permissions.

**Custom branding per organization.** Each organization in Zitadel can define its own login page appearance, including logo, color scheme, fonts, and custom behavior settings. When you are running a multi-tenant application, each of your customers sees a login experience that matches their brand, without any code changes on your end.

**Login policy controls.** Granular policies govern password complexity, MFA enforcement, session lifetime, lockout behavior, and allowed external identity providers. These can be set at the instance level (global defaults) or overridden per organization.

**gRPC and REST API.** Zitadel exposes every operation through both gRPC and REST APIs. The gRPC interface is ideal for high-throughput internal services, while the REST API with OpenAPI specification simplifies integration with existing tooling and third-party platforms.

**OIDC and SAML integration.** Zitadel supports both OIDC and SAML 2.0, making it compatible with virtually any application. The OIDC implementation covers all standard flows (authorization code, implicit, client credentials, device code, PKCE). SAML 2.0 support enables integration with legacy enterprise systems and government applications.

### When to Choose Zitadel

Pick Zitadel when you are building a multi-tenant SaaS product, need strong audit compliance with minimal effort, want API-first identity management, or are building cloud-native services that benefit from event-sourced architecture. Its organization model maps directly to customer isolation, and the audit trail requires zero configuration.

---

## Ory: Modular, Composable Identity Infrastructure

Ory takes a fundamentally different approach. Instead of a monolithic platform, Ory provides a suite of independent, purpose-built components that you compose together. This gives you surgical control over which capabilities you deploy, but requires more integration work upfront.

### Component Architecture

The Ory ecosystem consists of several independent projects, each addressing a specific aspect of identity and access management:

- **Ory Kratos** — User identity management and self-service flows (registration, login, account recovery, profile management). It is API-only with no built-in UI, giving you complete control over the user experience.
- **Ory Hydra** — OAuth 2.0 and OpenID Connect provider. It issues tokens and manages consent flows, but does not manage user identities directly. It delegates authentication to Kratos or any external system.
- **Ory Keto** — Relationship-based authorization engine implementing Google's Zanzibar model. It answers questions like "can user X read document Y?" based on defined relationships and namespaces.
- **Ory Oathkeeper** — Identity and access proxy that enforces authentication and authorization rules before requests reach your backend services. It acts as a sidecar or reverse proxy middleware.
- **Oathkeeper Access Rules** — JSON-based rules defining which authentication methods and authorization checks apply to which routes.

### Deployment with Docker Compose

Deploying a complete Ory stack requires orchestrating multiple services. Here is a production-oriented setup with Kratos and Hydra:

```yaml
version: "3.8"

services:
  kratos:
    image: oryd/kratos:v1.2.0
    command: serve -c /etc/config/kratos/kratos.yml --dev --watch-courier
    ports:
      - "4433:4433"  # Public API
      - "4434:4434"  # Admin API
    volumes:
      - ./kratos-config:/etc/config/kratos
    environment:
      DSN: postgres://kratos:kratos_secret@db:5432/kratos?sslmode=disable
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  kratos-migrate:
    image: oryd/kratos:v1.2.0
    command: migrate sql -e -c /etc/config/kratos/kratos.yml
    volumes:
      - ./kratos-config:/etc/config/kratos
    environment:
      DSN: postgres://kratos:kratos_secret@db:5432/kratos?sslmode=disable
    depends_on:
      db:
        condition: service_healthy
    restart: "no"

  hydra:
    image: oryd/hydra:v2.2.0
    command: serve all -c /etc/config/hydra/hydra.yml --dev
    ports:
      - "4444:4444"  # Public API
      - "4445:4445"  # Admin API
      - "5555:5555"  # OAuth2 consent callback
    volumes:
      - ./hydra-config:/etc/config/hydra
    environment:
      DSN: postgres://hydra:hydra_secret@db:5432/hydra?sslmode=disable
      SECRETS_SYSTEM: system-secret-minimum-32-chars
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  hydra-migrate:
    image: oryd/hydra:v2.2.0
    command: migrate sql -e --yes -c /etc/config/hydra/hydra.yml
    volumes:
      - ./hydra-config:/etc/config/hydra
    environment:
      DSN: postgres://hydra:hydra_secret@db:5432/hydra?sslmode=disable
    depends_on:
      db:
        condition: service_healthy
    restart: "no"

  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres_secret
      POSTGRES_DB: kratos
    volumes:
      - ory-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  ory-data:
```

Kratos configuration requires a YAML file defining identity schemas, self-service flows, and hooks. A minimal `kratos.yml`:

```yaml
serve:
  public:
    base_url: http://localhost:4433/
    cors:
      enabled: true
  admin:
    base_url: http://localhost:4434/

selfservice:
  default_browser_return_url: http://localhost:3000/
  allowed_return_urls:
    - http://localhost:3000

  methods:
    password:
      enabled: true
      config:
        haveibeenpwned_enabled: false
    totp:
      enabled: true
    webauthn:
      enabled: true

  flows:
    error:
      ui_url: http://localhost:3000/error
    login:
      ui_url: http://localhost:3000/login
      lifespan: 10m
    registration:
      ui_url: http://localhost:3000/registration
      lifespan: 10m
      after:
        password:
          hooks:
            - hook: session

identity:
  default_schema_id: default
  schemas:
    - id: default
      url: file:///etc/config/kratos/identity.schema.json
```

### Key Features

**Separation of concerns.** Hydra handles OAuth2/OIDC token issuance and consent. Kratos handles user identity lifecycle and self-service flows. Keto handles authorization. Oathkeeper enforces access policies at the edge. You can deploy only the components you need.

**Zanzibar-style authorization.** Ory Keto implements Google's Zanzibar relationship-based access control model. You define namespaces (e.g., `document`, `project`) and relationships (e.g., `viewer`, `editor`, `owner`), then query whether a subject has a specific relation to an object. This is significantly more expressive than role-based access control (RBAC) for complex permission scenarios.

**API-first, UI-agnostic.** Ory Kratos has no built-in user interface. All self-service flows (login, registration, account recovery) are driven through API endpoints that your frontend calls. This gives you pixel-perfect control over the login experience but requires building the UI yourself or using Ory's managed cloud offering.

**Extensible identity schemas.** Kratos allows you to define arbitrary identity schemas in JSON Schema format. Users can have custom attributes — department, role, subscription tier, geographic region — without waiting for the platform to support them natively.

### When to Choose Ory

Pick Ory when you want fine-grained control over every aspect of your identity stack, need Zanzibar-style relationship-based authorization, are building a custom user-facing authentication experience, or prefer a composable architecture where you only deploy the components your application actually uses.

---

## Keycloak: The Enterprise Standard

Keycloak is the most mature and widely deployed open-source IAM platform. Originally created by Red Hat in 2014, it has over a decade of development, a massive community, and deep integration with the Java enterprise ecosystem. The migration to Quarkus runtime significantly improved startup time and memory footprint.

### Architecture

Keycloak runs as a single Quarkus application backed by a relational database. It organizes resources into **realms** — isolated namespaces that each contain their own users, groups, roles, clients, and identity providers. A single Keycloak instance can serve multiple independent organizations through realm isolation.

The admin console provides a comprehensive web interface for managing every aspect of the platform. Most operations can also be performed through the REST API, though the API was designed primarily to support the admin console rather than as a developer-facing interface.

### Deployment with Docker Compose

```yaml
version: "3.8"

services:
  keycloak:
    image: quay.io/keycloak/keycloak:26.1.2
    command: start --optimized
    ports:
      - "8080:8080"
    environment:
      KC_HEALTH_ENABLED: "true"
      KC_DB: postgres
      KC_DB_URL: jdbc:postgresql://db:5432/keycloak
      KC_DB_USERNAME: keycloak
      KC_DB_PASSWORD: keycloak_secret
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: admin_password
      KC_HOSTNAME: localhost
      KC_HOSTNAME_STRICT: "false"
      KC_PROXY: edge
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./keycloak-themes:/opt/keycloak/themes
      - ./keycloak-providers:/opt/keycloak/providers
    restart: unless-stopped

  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_USER: keycloak
      POSTGRES_PASSWORD: keycloak_secret
      POSTGRES_DB: keycloak
    volumes:
      - keycloak-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U keycloak"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  keycloak-data:
```

After initial startup, access the admin console at `http://localhost:8080/admin` using the `KEYCLOAK_ADMIN` credentials. The first configuration step should be creating a realm and defining identity providers, clients, and user federation.

### Key Features

**User federation.** Keycloak can connect to existing LDAP or Active Directory servers, allowing users to authenticate with their existing corporate credentials. It supports full synchronization (importing all users) or on-demand authentication (verifying against the external directory without importing). This is critical for enterprises migrating from legacy identity systems.

**Fine-grained authorization.** Keycloak's authorization services go beyond simple role-based access control. You define resources, scopes, policies (role-based, time-based, JavaScript-based, user-based), and permissions that combine them. This allows complex access rules like "only managers from the finance department can approve transactions over $10,000 during business hours."

**Extensive identity provider support.** Keycloak supports OIDC, SAML 2.0, OAuth 2.0, LDAP, Kerberos, and social login providers (Google, GitHub, Facebook, Twitter, Microsoft, LinkedIn, GitLab, Bitbucket, StackOverflow). You can also connect to any custom OIDC or SAML provider.

**Theming system.** Keycloak's theme engine allows complete customization of login pages, account consoles, email templates, and admin console appearance. Themes can inherit from the base theme and override specific elements — logos, CSS, FreeMarker templates.

**Client scopes and protocol mappers.** Keycloak provides granular control over what information is included in tokens. Protocol mappers transform user attributes, group memberships, and roles into token claims. Client scopes define which mappers apply to which clients, enabling different applications to receive different token contents from the same user session.

**Clustering and high availability.** Keycloak supports horizontal scaling through Infinispan-based clustering. Multiple Keycloak instances share session state, cache user data, and distribute load. Combined with a load balancer, this provides high availability for production deployments.

### When to Choose Keycloak

Pick Keycloak when you need LDAP/Active Directory integration, have existing Java infrastructure, require SAML 2.0 for enterprise applications, need fine-grained authorization policies, or want the most battle-tested open-source IAM platform with the largest community and ecosystem.

---

## Detailed Feature Comparison

### Authentication Methods

| Method | Zitadel | Ory Kratos | Keycloak |
|--------|---------|------------|----------|
| Username / Password | Yes | Yes | Yes |
| Email / Password | Yes | Yes | Yes |
| Passkeys / WebAuthn | Yes | Yes | Yes |
| TOTP (Authenticator Apps) | Yes | Yes | Yes |
| SMS OTP | Yes | Via hook | Yes |
| Social Login | Yes (built-in) | Via configuration | Yes (built-in) |
| LDAP / AD | No | Via hook | Yes (native) |
| SAML IdP | Yes | Via integration | Yes (native) |
| Device Authorization | Yes | Manual | Yes |

### Authorization Models

| Model | Zitadel | Ory | Keycloak |
|-------|---------|-----|----------|
| RBAC (Role-Based) | Yes | Via Keto policies | Yes (native) |
| ABAC (Attribute-Based) | Via policies | Via Keto engine | Yes (policy engine) |
| ReBAC (Relationship-Based) | No | Yes (Zanzibar) | No |
| Project / Org scoping | Yes (organizations) | Manual | Yes (realms) |
| Machine accounts | Yes (native) | Via Hydra client credentials | Yes (service accounts) |
| API keys / PATs | Yes (native) | Manual | Via client secrets |

### Developer Experience

| Aspect | Zitadel | Ory | Keycloak |
|--------|---------|-----|----------|
| API Design | gRPC + REST, well-documented | REST per component, OpenAPI specs | REST, partially documented |
| SDKs | Go, JavaScript/TypeScript, Dart | Go, JavaScript, Python | Java, Node.js, JavaScript |
| CLI | `zitadel` for administration | `ory` for all components | `kcadm.sh` (shell-based) |
| Terraform Provider | Official, actively maintained | Official | Community-maintained |
| Getting Started | 5 minutes with Docker Compose | 30+ minutes with full stack | 10 minutes with Docker Compose |
| Local Development | Excellent (single binary) | Good (requires multiple binaries) | Fair (heavy JVM, slower startup) |

---

## Migration and Integration Patterns

### From Auth0 to Self-Hosted

Migrating from Auth0 requires exporting user data and reconfiguring your applications. Most platforms support user import through bulk APIs:

```bash
# Export users from Auth0 using the Management API
curl -H "Authorization: Bearer $AUTH0_TOKEN" \
  "https://YOUR_DOMAIN.auth0.com/api/v2/users-by-email?email=test@example.com"

# Import users into Zitadel via the gRPC API
zitadel action user import \
  --file users.csv \
  --org-id YOUR_ORG_ID

# For Keycloak, use the partial import feature
curl -X POST "http://localhost:8080/admin/realms/master/partialImport" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @realm-export.json
```

### Adding Self-Hosted IAM to an Existing Application

For a typical web application, integrating any of these platforms follows the same OIDC authorization code flow:

1. Register your application as a client in the IAM platform
2. Configure the redirect URI (e.g., `https://yourapp.com/callback`)
3. Use an OIDC library in your application framework
4. Handle the callback, exchange the authorization code for tokens
5. Validate the ID token and create a local session

For Go applications using the Zitadel OIDC library:

```go
package main

import (
    "github.com/zitadel/oidc/v3/pkg/client/rp"
    "github.com/zitadel/oidc/v3/pkg/oidc"
    "net/http"
)

var (
    clientID     = "your-client-id"
    clientSecret = "your-client-secret"
    key          = []byte("secure-random-key-32-chars!!")
    redirectURI  = "http://localhost:8080/callback"
)

func main() {
    provider, _ := rp.NewRelyingPartyOIDC(
        "http://localhost:8080",  // Zitadel issuer URL
        clientID,
        clientSecret,
        redirectURI,
        []string{oidc.ScopeOpenID, oidc.ScopeProfile, oidc.ScopeEmail},
    )

    http.Handle("/login", rp.AuthURLHandler(func() string {
        return rp.GenerateRandomState()
    }, provider))

    http.HandleFunc("/callback", func(w http.ResponseWriter, r *http.Request) {
        userInfo, err := rp.CodeExchange[*oidc.IDTokenClaims](r, provider)
        if err != nil {
            http.Error(w, err.Error(), http.StatusBadRequest)
            return
        }
        // userInfo contains authenticated user claims
        http.Redirect(w, r, "/dashboard", http.StatusFound)
    })

    http.ListenAndServe(":8080", nil)
}
```

---

## Decision Framework

Choose **Zitadel** when:
- You are building a multi-tenant application and need organization-level isolation
- Audit compliance is a requirement (event sourcing gives you this automatically)
- You want a modern API-first platform with excellent developer tooling
- You need machine-to-machine authentication with native PAT support
- You prefer Go-based infrastructure with lower memory footprint

Choose **Ory** when:
- You want surgical control over which identity components you deploy
- You need relationship-based authorization (Zanzibar model via Keto)
- You are building a completely custom authentication UI from scratch
- You prefer composable microservices over monolithic platforms
- You need extensible identity schemas with arbitrary user attributes

Choose **Keycloak** when:
- You need LDAP or Active Directory integration
- You require SAML 2.0 for enterprise or government applications
- You have existing Java infrastructure and want native JVM integration
- You need fine-grained authorization policies with a visual policy editor
- You want the most mature platform with the largest community and documentation base

---

## Conclusion

The self-hosted IAM landscape in 2026 offers three distinct approaches to identity management. Zitadel brings cloud-native event-sourced architecture with excellent multi-tenant support. Ory provides modular composable components for teams that want maximum flexibility. Keycloak delivers enterprise maturity with deep integration capabilities and a proven track record across thousands of organizations.

The right choice depends on your constraints: team size, existing infrastructure, compliance requirements, and whether you prioritize developer experience or feature completeness. All three are production-ready, actively maintained, and available under permissive open-source licenses. The common thread is that self-hosting your identity infrastructure pays for itself through eliminated per-user licensing costs, complete data ownership, and the freedom to integrate with any system without vendor approval.

Start with a proof-of-deployment using the Docker Compose configurations above. Test the authentication flows, integrate one application, and evaluate the developer experience. The investment in self-hosted IAM compounds over time as your organization grows and your integration needs expand.
