---
title: "Self-Hosted Passkey & WebAuthn Authentication Solutions: Complete Guide 2026"
date: 2026-04-17
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete guide to self-hosted passkey and WebAuthn authentication in 2026. Compare Zitadel, Keycloak, Authentik, and FIDO2 servers for passwordless login."
---

Password-based authentication is one of the oldest security problems on the web. Despite decades of improvements — mandatory complexity rules, forced rotation, MFA — passwords remain the weakest link in most security architectures. Phishing, credential stuffing, and brute-force attacks exploit the fundamental flaw of shared secrets: the server must store something that can be stolen.

Passkeys, built on the FIDO2/WebAuthn standard, eliminate that problem entirely. Instead of a shared secret, authentication uses public-key cryptography. Your private key never leaves your device, and the server only stores a public key that is useless to attackers. Combined with built-in biometric verification (fingerprint, Face ID, Windows Hello), passkeys deliver stronger security with less friction.

In this guide, we will explore how to self-host passkey authentication, compare the best open-source solutions available in 2026, and walk through concrete deployment configurations.

## Why Self-Host Your Passkey Authentication

You might wonder: if passkeys are so great, why not just use a cloud identity provider like Auth0, AWS Cognito, or Cloudflare Access? There are several compelling reasons to self-host:

**Data sovereignty.** Your authentication data — user identities, registered devices, audit logs — stays on your infrastructure. You control retention policies, access controls, and compliance boundaries. For organizations under GDPR, HIPAA, or other regulatory frameworks, this is often a hard requirement rather than a preference.

**No vendor lock-in.** Cloud identity providers create deep dependencies. Migrating user accounts, MFA enrollments, and session state between providers is notoriously difficult. Self-hosted solutions let you own the entire authentication stack and switch components as needed.

**Cost at scale.** Most cloud identity providers charge per monthly active user (MAU). A self-hosted solution runs on your existing infrastructure with predictable costs that do not scale linearly with user count.

**Air-gapped and offline environments.** Some deployments — industrial control systems, classified networks, edge computing nodes — simply cannot reach external identity services. Self-hosted passkey servers work entirely within your network perimeter.

**Custom integration.** When you control the authentication server, you can integrate it with internal systems: LDAP directories, HR databases, hardware security modules (HSMs), and custom policy engines that cloud providers do not support.

## Understanding the FIDO2 / WebAuthn Architecture

Before comparing solutions, it helps to understand the underlying protocol. FIDO2 is a joint standard from the FIDO Alliance and W3C that consists of two components:

- **WebAuthn** — the browser API that websites use to register and authenticate passkeys
- **CTAP (Client to Authenticator Protocol)** — the protocol between the browser/device and the authenticator (security key, biometric sensor, or platform authenticator like Apple Secure Enclave)

The registration flow works like this:

1. The user visits your application and clicks "Create Passkey"
2. Your application sends a registration challenge to the browser via WebAuthn
3. The browser communicates with the device authenticator (via CTAP)
4. The authenticator generates a new key pair, stores the private key securely, and returns the public key plus a signed attestation
5. Your application sends the public key and attestation to your passkey server for verification and storage

Authentication is the reverse:

1. The user clicks "Sign In with Passkey"
2. Your application sends an authentication challenge
3. The browser asks the device authenticator to sign the challenge with the stored private key
4. The authenticator signs it (after user verification — biometric, PIN, or security key touch)
5. Your server verifies the signature using the stored public key

The critical security property: **the private key is never transmitted, never stored on the server, and never leaves the authenticator device.** Even if your server is fully compromised, attackers cannot impersonate users.

## Comparison: Self-Hosted Passkey Solutions in 2026

| Feature | Keycloak | Zitadel | Authentik | PassBolt + WebAuthn | go-webauthn (library) |
|---|---|---|---|---|---|
| **Type** | Full IdP | Cloud-native IdP | Identity provider | Password manager + plugin | Go library |
| **WebAuthn Support** | Native (since v17) | Native (first-class) | Native (since v2023) | Via community plugin | Embed in your app |
| **Passkey (discoverable)** | Yes | Yes | Yes | Limited | Yes |
| **FIDO2 / CTAP2** | Yes | Yes | Yes | No | Yes |
| **Admin Console** | Rich web UI | Rich web UI | Rich web UI | Web UI | None (code-level) |
| **OIDC / SAML** | Full support | Full support | Full support | No (separate) | No (library) |
| **Multi-tenancy** | Via realms | Built-in | Via contexts | No | No |
| **Database** | PostgreSQL, MySQL, MariaDB | PostgreSQL, CockroachDB | PostgreSQL, SQLite | MySQL, MariaDB | Your choice |
| **Docker Support** | Official images | Official images | Official images | Official images | N/A |
| **License** | Apache 2.0 | Apache 2.0 | MIT | AGPL 3.0 | Apache 2.0 |
| **Best For** | Enterprise, legacy integration | Modern cloud-native apps | Homelab, full-stack auth | Existing Passkey users | Developers building custom auth |

## Keycloak: The Enterprise Identity Powerhouse

Keycloak is the most mature open-source identity and access management solution. Maintained by Red Hat and the community, it supports WebAuthn and passkeys natively since version 17 (the Quarkus-based rewrite).

### Why Choose Keycloak

Keycloak is the right choice when you need a full-featured identity provider with extensive protocol support (OIDC, SAML, OAuth2, LDAP federation) and a proven track record in enterprise environments. Its WebAuthn implementation supports both platform authenticators (Touch ID, Windows Hello) and roaming authenticators (YubiKey, SoloKey).

### Docker Deployment

```yaml
# docker-compose.yml
services:
  keycloak:
    image: quay.io/keycloak/keycloak:26.0
    container_name: keycloak
    environment:
      KC_DB: postgres
      KC_DB_URL: jdbc:postgresql://keycloak-db:5432/keycloak
      KC_DB_USERNAME: keycloak
      KC_DB_PASSWORD: ${KC_DB_PASSWORD}
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: ${KEYCLOAK_ADMIN_PASSWORD}
      KC_HOSTNAME: auth.example.com
      KC_HOSTNAME_STRICT: "true"
      KC_HEALTH_ENABLED: "true"
      KC_FEATURES: "webauthn,webauthn-passwordless"
    ports:
      - "8080:8080"
    depends_on:
      keycloak-db:
        condition: service_healthy
    command: ["start"]
    networks:
      - auth-network

  keycloak-db:
    image: postgres:16-alpine
    container_name: keycloak-db
    environment:
      POSTGRES_DB: keycloak
      POSTGRES_USER: keycloak
      POSTGRES_PASSWORD: ${KC_DB_PASSWORD}
    volumes:
      - keycloak-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U keycloak"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - auth-network

  caddy:
    image: caddy:2
    container_name: keycloak-proxy
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy-data:/data
      - caddy-config:/config
    networks:
      - auth-network

volumes:
  keycloak-data:
  caddy-data:
  caddy-config:

networks:
  auth-network:
    driver: bridge
```

```
# Caddyfile
auth.example.com {
  reverse_proxy keycloak:8080
  tls admin@example.com
  header {
    Strict-Transport-Security "max-age=31536000; includeSubDomains"
    X-Frame-Options DENY
    X-Content-Type-Options nosniff
  }
}
```

### Enabling Passkeys in Keycloak

After deployment, configure passkey authentication through the admin console:

1. Navigate to **Authentication** > **Policies** > **WebAuthn Policy**
2. Set **Attestation Conveyance** to `not specified` (or `direct` for enterprise attestation)
3. Set **Authenticator Attachment** to `not specified` (allows both platform and roaming)
4. Set **User verification requirement** to `required` for passwordless flows
5. Enable the **WebAuthn Passwordless** authentication flow
6. Assign the flow to your application or realm

### Application Integration

Keycloak provides OIDC endpoints that any WebAuthn-compatible application can use:

```bash
# Discover OIDC configuration
curl https://auth.example.com/realms/master/.well-known/openid-configuration

# Example authorization URL (redirect user here)
# https://auth.example.com/realms/master/protocol/openid-connect/auth
#   ?client_id=my-app
#   &redirect_uri=https://app.example.com/callback
#   &response_type=code
#   &scope=openid
#   &acr_values=fido2
```

The `acr_values=fido2` parameter signals that the authentication must use WebAuthn/passkey.

## Zitadel: Cloud-Native Identity Built for Developers

Zitadel takes a different approach. Built from the ground up as a cloud-native identity platform, it treats passkeys as a first-class citizen rather than an add-on feature. Its architecture is designed for multi-tenancy, audit trails, and horizontal scaling.

### Why Choose Zitadel

Zitadel is ideal for teams building modern applications that need passkey-first authentication, granular multi-tenant identity management, and comprehensive audit logging out of the box. Its Go-based architecture is lightweight and scales well on Kubernetes.

### Docker Deployment

```yaml
# docker-compose.yml
services:
  zitadel:
    image: ghcr.io/zitadel/zitadel:v2.65.0
    container_name: zitadel
    command: ["start", "--masterkey", "${ZITADEL_MASTERKEY}", "--tlsMode", "external"]
    environment:
      ZITADEL_DATABASE_POSTGRES_HOST: zitadel-db
      ZITADEL_DATABASE_POSTGRES_PORT: 5432
      ZITADEL_DATABASE_POSTGRES_DATABASE: zitadel
      ZITADEL_DATABASE_POSTGRES_USER_USERNAME: zitadel
      ZITADEL_DATABASE_POSTGRES_USER_PASSWORD: ${ZITADEL_DB_PASSWORD}
      ZITADEL_DATABASE_POSTGRES_ADMIN_USERNAME: postgres
      ZITADEL_DATABASE_POSTGRES_ADMIN_PASSWORD: ${ZITADEL_ADMIN_PASSWORD}
      ZITADEL_EXTERNALSECURE: "false"
      ZITADEL_EXTERNALPORT: 443
      ZITADEL_EXTERNALDOMAIN: auth.example.com
    ports:
      - "8080:8080"
    depends_on:
      zitadel-db:
        condition: service_healthy
    networks:
      - auth-network

  zitadel-db:
    image: postgres:16-alpine
    container_name: zitadel-db
    environment:
      POSTGRES_DB: zitadel
      POSTGRES_USER: zitadel
      POSTGRES_PASSWORD: ${ZITADEL_DB_PASSWORD}
      POSTGRES_INITDB_ARGS: "--auth-host=scram-sha-256"
    volumes:
      - zitadel-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U zitadel"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - auth-network

volumes:
  zitadel-data:

networks:
  auth-network:
    driver: bridge
```

Generate a secure master key:

```bash
openssl rand -base64 32
```

### Passkey Configuration in Zitadel

Zitadel enables passkeys through its organization settings:

1. Go to **Organization** > **Settings** > **Login Settings**
2. Enable **Allow Passkey** authentication
3. Set **Passkey enforcement** to `optional` (users can choose) or `required` (passwordless-only)
4. Configure allowed origins under **WebAuthn Settings**
5. Create an application under **Applications** > **OIDC** to get client credentials

### Integration Example

```javascript
// Using Zitadel's OIDC + WebAuthn from a web application
const zitadelConfig = {
  issuer: 'https://auth.example.com',
  clientId: 'your-client-id',
  redirectUri: 'https://app.example.com/callback',
};

// Redirect to Zitadel's authorization endpoint
const authUrl = new URL(`${zitadelConfig.issuer}/oauth/v2/authorize`);
authUrl.searchParams.set('client_id', zitadelConfig.clientId);
authUrl.searchParams.set('redirect_uri', zitadelConfig.redirectUri);
authUrl.searchParams.set('response_type', 'code');
authUrl.searchParams.set('scope', 'openid email profile');
authUrl.searchParams.set('prompt', 'login');

window.location.href = authUrl.toString();
```

## Authentik: The Homelab and SMB Favorite

Authentik has rapidly gained popularity in the homelab and small-to-medium business space. It provides a complete identity provider with WebAuthn support, a flexible policy engine, and excellent integration with common homelab tools (Proxmox, Nextcloud, Gitea, etc.).

### Why Choose Authentik

Authentik stands out for its user-friendly interface, flexible flow/policy system, and broad ecosystem integrations. It supports passkeys alongside traditional password and OTP authentication, giving users a migration path. Its MIT license is also more permissive than Keycloak's or Passkey's licenses.

### Docker Deployment

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:16-alpine
    container_name: authentik-db
    environment:
      POSTGRES_USER: authentik
      POSTGRES_PASSWORD: ${AUTHENTIK_DB_PASSWORD}
      POSTGRES_DB: authentik
    volumes:
      - authentik-db:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -d authentik -U authentik"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - auth-network

  redis:
    image: redis:7-alpine
    container_name: authentik-redis
    command: ["--save", "60", "1", "--loglevel", "warning"]
    volumes:
      - authentik-redis:/data
    healthcheck:
      test: ["CMD-SHELL", "redis-cli ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - auth-network

  server:
    image: ghcr.io/goauthentik/server:2024.12.2
    container_name: authentik-server
    command: server
    environment:
      AUTHENTIK_REDIS__HOST: redis
      AUTHENTIK_POSTGRESQL__HOST: postgres
      AUTHENTIK_POSTGRESQL__USER: authentik
      AUTHENTIK_POSTGRESQL__NAME: authentik
      AUTHENTIK_POSTGRESQL__PASSWORD: ${AUTHENTIK_DB_PASSWORD}
      AUTHENTIK_SECRET_KEY: ${AUTHENTIK_SECRET_KEY}
      AUTHENTIK_ERROR_REPORTING__ENABLED: "true"
    volumes:
      - ./media:/media
      - ./custom-templates:/templates
    ports:
      - "9000:9000"
      - "9443:9443"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - auth-network

  worker:
    image: ghcr.io/goauthentik/server:2024.12.2
    container_name: authentik-worker
    command: worker
    environment:
      AUTHENTIK_REDIS__HOST: redis
      AUTHENTIK_POSTGRESQL__HOST: postgres
      AUTHENTIK_POSTGRESQL__USER: authentik
      AUTHENTIK_POSTGRESQL__NAME: authentik
      AUTHENTIK_POSTGRESQL__PASSWORD: ${AUTHENTIK_DB_PASSWORD}
      AUTHENTIK_SECRET_KEY: ${AUTHENTIK_SECRET_KEY}
    user: root
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./media:/media
      - ./certs:/certs
      - ./custom-templates:/templates
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - auth-network

volumes:
  authentik-db:
  authentik-redis:

networks:
  auth-network:
    driver: bridge
```

Generate required secrets:

```bash
# Secret key for Authentik
openssl rand -base64 60

# Bootstrap token for initial admin setup
openssl rand -base64 40
```

### Configuring WebAuthn in Authentik

1. Access the admin interface at `https://your-server:9443/if/admin/`
2. Navigate to **Flows** > **Stages** and locate the **Authenticator WebAuthn Setup** stage
3. Edit the stage to configure:
   - **User verification**: `required` (forces biometric/PIN) or `preferred`
   - **Authenticator attachment**: `platform` (built-in) or `cross-platform` (USB keys)
   - **Resident key requirement**: `required` for discoverable passkeys
4. Add the WebAuthn stage to your authentication flow
5. Navigate to **Applications** > **Providers** and create an OAuth2/OIDC provider

### Policy Engine

Authentik's policy engine is one of its strongest features. You can create conditional flows like:

```
IF user is in group "developers"
  THEN require WebAuthn + TOTP
ELSE IF user is in group "contractors"
  THEN require WebAuthn only
ELSE
  THEN require password + WebAuthn
```

This is configured entirely through the web UI without writing code.

## Building a Custom WebAuthn Server with Go

If none of the full-featured identity providers fit your needs, you can embed WebAuthn directly into your application using the `go-webauthn` library. This approach gives you complete control over the authentication flow, user experience, and data storage.

### Project Setup

```bash
mkdir webauthn-server && cd webauthn-server
go mod init webauthn-server
go get github.com/go-webauthn/webauthn@latest
go get github.com/gorilla/sessions
go get github.com/gorilla/mux
```

### Core Implementation

```go
package main

import (
    "encoding/json"
    "log"
    "net/http"

    "github.com/go-webauthn/webauthn/protocol"
    "github.com/go-webauthn/webauthn/webauthn"
    "github.com/gorilla/mux"
    "github.com/gorilla/sessions"
)

var (
    store     *sessions.CookieStore
    webauthn  *webauthn.WebAuthn
)

// User represents a user in your system
type User struct {
    ID              []byte
    Name            string
    DisplayName     string
    Credentials     []webauthn.Credential
}

func (u User) WebAuthnID() []byte            { return u.ID }
func (u User) WebAuthnName() string          { return u.Name }
func (u User) WebAuthnDisplayName() string   { return u.DisplayName }
func (u User) WebAuthnIcon() string          { return "" }
func (u User) WebAuthnCredentials() []webauthn.Credential {
    return u.Credentials
}

func init() {
    var err error
    store, err = sessions.NewCookieStore([]byte("session-secret-change-me"))
    if err != nil {
        log.Fatal(err)
    }

    webauthn, err = webauthn.New(&webauthn.Config{
        RPID:                "app.example.com",
        RPOrigins:           []string{"https://app.example.com"},
        RPOriginVerification: protocol.RPOriginVerificationStrict,
        AttestationPreference: protocol.PreferNoAttestation,
        AuthenticatorSelection: protocol.AuthenticatorSelection{
            AuthenticatorAttachment: protocol.Platform,
            UserVerification:        protocol.VerificationRequired,
            ResidentKey:             protocol.ResidentKeyRequirementRequired,
        },
    })
    if err != nil {
        log.Fatal(err)
    }
}

// Begin registration
func beginRegistration(w http.ResponseWriter, r *http.Request) {
    user := findUserFromSession(r) // implement your user lookup
    options, session, err := webauthn.BeginRegistration(user)
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    saveSession(session, r, w)
    respondJSON(w, options)
}

// Finish registration
func finishRegistration(w http.ResponseWriter, r *http.Request) {
    session := loadSession(r)
    user := findUserFromSession(r)

    credential, err := webauthn.FinishRegistration(user, session, r)
    if err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }

    // Store the credential in your database
    user.Credentials = append(user.Credentials, *credential)
    saveUser(user)

    respondJSON(w, map[string]string{"status": "registered"})
}

func respondJSON(w http.ResponseWriter, data interface{}) {
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(data)
}

func main() {
    r := mux.NewRouter()
    r.HandleFunc("/auth/register/begin", beginRegistration).Methods("POST")
    r.HandleFunc("/auth/register/finish", finishRegistration).Methods("POST")
    r.HandleFunc("/auth/login/begin", beginLogin).Methods("POST")
    r.HandleFunc("/auth/login/finish", finishLogin).Methods("POST")

    log.Println("Starting WebAuthn server on :8080")
    log.Fatal(http.ListenAndServe(":8080", r))
}
```

This gives you a minimal but functional WebAuthn server. You would need to implement `findUserFromSession`, `saveSession`, `loadSession`, and `saveUser` using your preferred database.

## Security Best Practices for Self-Hosted Passkey Infrastructure

Running your own authentication infrastructure means you own the security responsibilities. Here are critical practices to implement:

### 1. TLS is Mandatory

WebAuthn requires a secure context. Your authentication server must serve HTTPS with a valid certificate. Use Let's Encrypt with automated renewal, or an internal CA for private networks.

```bash
# Automated certificate renewal with Caddy (handles automatically)
# With Nginx + Certbot:
certbot renew --nginx --quiet
(crontab -l; echo "0 3 * * * certbot renew --nginx --quiet") | crontab -
```

### 2. Database Encryption at Rest

Your passkey server stores public keys and attestation data. While public keys alone cannot impersonate users, the full authentication record is sensitive data. Encrypt your database:

```yaml
# PostgreSQL with Transparent Data Encryption (via pgcrypto)
ALTER TABLE webauthn_credentials
  ALTER COLUMN credential_public_key TYPE bytea
  USING pgp_sym_encrypt(credential_public_key::bytea, '${ENCRYPTION_KEY}');
```

### 3. Rate Limiting and Anomaly Detection

Even with passkeys, you should protect against enumeration attacks (probing for valid usernames) and replay attacks.

```nginx
# Nginx rate limiting for authentication endpoints
limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/m;

server {
  location /auth/ {
    limit_req zone=auth burst=3 nodelay;
    proxy_pass http://auth-backend;
  }
}
```

### 4. Audit Logging

Maintain detailed logs of all authentication events. Both Zitadel and Authentik include audit logging; Keycloak supports it via event listeners. For custom implementations, log:

- Registration attempts (success/failure, timestamp, user agent, IP)
- Authentication attempts (same fields)
- Credential deletions and modifications
- Admin configuration changes

### 5. Backup and Disaster Recovery

Your authentication database is critical infrastructure. Implement automated backups:

```bash
#!/bin/bash
# backup-auth-db.sh
BACKUP_DIR="/opt/backups/auth"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

pg_dump -h localhost -U authentik authentik | \
  gzip > "$BACKUP_DIR/authentik-${TIMESTAMP}.sql.gz"

# Keep last 30 days
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete
```

Store backups off-site and test restoration procedures quarterly.

## Migration Strategy: From Passwords to Passkeys

Moving your user base from passwords to passkeys requires a thoughtful migration strategy. The best approach is a gradual, opt-in transition:

1. **Phase 1 — Offer passkeys as an option.** Add a "Register a Passkey" button alongside the existing password login. Users who register a passkey can use it as a second factor.

2. **Phase 2 — Encourage passkey adoption.** Send email campaigns explaining the benefits. Offer incentives (reduced friction, faster login). Track adoption metrics.

3. **Phase 3 — Make passkeys primary.** For users with registered passkeys, default to passkey authentication. Offer password login as a fallback with clear messaging encouraging passkey migration.

4. **Phase 4 — Passwordless default.** New accounts are passkey-only. Existing password-only accounts receive periodic prompts to register a passkey. Eventually sunset password authentication.

Keycloak and Authentik both support this gradual approach by allowing you to configure multiple authentication methods in parallel and control which methods are required for which user groups.

## Conclusion

Self-hosted passkey authentication is no longer a niche project — it is a practical, production-ready strategy for organizations that value security, privacy, and independence from cloud identity vendors. In 2026, the options are mature:

- **Keycloak** for enterprise-grade identity management with the broadest protocol support
- **Zitadel** for modern, cloud-native applications with passkey-first design
- **Authentik** for homelabs, SMBs, and teams that value flexibility and ease of use
- **go-webauthn** (or equivalent libraries in other languages) for developers who want complete control

All of these solutions eliminate the fundamental weakness of password-based authentication while giving you full ownership of your identity infrastructure. The investment in self-hosting pays dividends in security, compliance, and cost — especially as your user base grows.
