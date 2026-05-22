---
title: "Self-Hosted Container Registry Authentication: cesanta/docker_auth vs oauth2-proxy vs Harbor OIDC (2026)"
date: "2026-05-22"
tags: ["container-registry", "authentication", "docker", "harbor", "oauth2", "security"]
draft: false
---

Running a private container registry without proper authentication is a security liability. Anyone who discovers your registry URL can pull or push images. This guide compares three battle-tested approaches to securing self-hosted Docker registries: **cesanta/docker_auth**, **oauth2-proxy**, and **Harbor's built-in OIDC authentication**.

## Why Registry Authentication Matters

A Docker registry stores your application container images — the exact binaries that run in production. Without authentication, your registry is open to the internet. Attackers can pull your proprietary images to reverse-engineer your code, or worse, push malicious images that could be deployed to your infrastructure.

The Docker Distribution (registry:2) project provides a basic HTTP auth mechanism, but it lacks support for modern identity providers, token refresh, fine-grained access control, and single sign-on. This is where dedicated authentication solutions come in.

For a complete overview of registry deployment patterns, see our [Docker Registry Proxy Cache guide](../2026-04-24-docker-registry-proxy-cache-distribution-harbor-zot-guide/). If you need registry UI management, our [Registry UI comparison](../2026-04-28-joxit-vs-docker-registry-browser-vs-registry-frontend-self-hosted-docker-registry-ui-guide/) covers that. For registry replication strategies, check our [Skopeo vs Regsync vs Harbor guide](../2026-05-08-container-registry-replication-skopeo-vs-regsync-vs-harbor-guide/).

## cesanta/docker_auth

[cesanta/docker_auth](https://github.com/cesanta/docker_auth) is a dedicated authentication server for Docker registries. It implements the Docker Registry Token Authentication protocol and supports multiple auth backends including Google Sign-In, GitHub, LDAP, MongoDB, and static user files.

### Architecture

docker_auth acts as a token server sitting between the Docker client and the registry. When a client attempts to access the registry, the registry redirects it to the auth server. The auth server validates credentials and returns a signed JWT token that grants access to specific repositories and actions (pull, push, delete).

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  registry:
    image: registry:2
    ports:
      - "5000:5000"
    volumes:
      - ./registry-data:/var/lib/registry
      - ./registry/config.yml:/etc/docker/registry/config.yml:ro
      - ./auth/root.crt:/etc/docker/registry/root.crt:ro
    restart: unless-stopped

  auth:
    image: cesanta/docker_auth:1
    ports:
      - "5001:5001"
    volumes:
      - ./auth/config/auth_config.yml:/config/auth_config.yml:ro
      - ./auth/private.key:/config/private.key:ro
      - ./auth/root.crt:/config/root.crt:ro
    restart: unless-stopped
```

### Registry Configuration

The registry configuration (`config.yml`) must reference the auth server:

```yaml
version: 0.1
log:
  fields:
    service: registry
storage:
  cache:
    blobdescriptor: inmemory
  filesystem:
    rootdirectory: /var/lib/registry
http:
  addr: :5000
  headers:
    X-Content-Type-Options: [nosniff]
auth:
  token:
    realm: http://auth:5001/auth
    service: docker-registry
    issuer: auth-server
    rootcertbundle: /etc/docker/registry/root.crt
```

### Auth Server Configuration

The `auth_config.yml` defines users, ACLs, and the token signing key:

```yaml
server:
  addr: ":5001"
  certificate: "/config/root.crt"
  key: "/config/private.key"

token:
  issuer: "auth-server"
  expiration: 900

users:
  "admin":
    password: "$2y$05$..."  # bcrypt hash
  "developer":
    password: "$2y$05$..."

acl:
  - match: {account: "admin"}
    actions: ["*"]
    comment: "Admin has full access"
  - match: {account: "developer"}
    actions: ["pull", "push"]
    comment: "Developers can pull and push"
  - match: {account: "/.+/"}
    actions: ["pull"]
    comment: "Anonymous users can only pull"
```

### Key Features

- **Multiple auth backends**: Google, GitHub, GitLab, LDAP, MongoDB, static files, XORM (MySQL/PostgreSQL)
- **Fine-grained ACLs**: Per-user, per-repository, per-action rules with regex matching
- **Token expiration**: Configurable JWT token lifetime
- **Lightweight**: Single Go binary, ~15MB Docker image
- **Active development**: Regular releases and security patches

## oauth2-proxy for Docker Registry

[oauth2-proxy](https://github.com/oauth2-proxy/oauth2-proxy) is a reverse proxy that provides authentication using OAuth 2.0, OIDC, and other identity providers. While not specifically designed for Docker registries, it can protect any HTTP service including container registries.

### Architecture

oauth2-proxy sits in front of the registry as a reverse proxy. It intercepts all requests, validates authentication via your identity provider (Google, GitHub, Keycloak, etc.), and forwards authenticated requests to the registry.

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  registry:
    image: registry:2
    ports:
      - "127.0.0.1:5000:5000"
    volumes:
      - ./registry-data:/var/lib/registry
    restart: unless-stopped

  oauth2-proxy:
    image: quay.io/oauth2-proxy/oauth2-proxy:v7.6.0
    ports:
      - "4180:4180"
    environment:
      - OAUTH2_PROXY_PROVIDER=github
      - OAUTH2_PROXY_CLIENT_ID=your-github-client-id
      - OAUTH2_PROXY_CLIENT_SECRET=your-github-client-secret
      - OAUTH2_PROXY_COOKIE_SECRET=your-cookie-secret
      - OAUTH2_PROXY_COOKIE_SECURE=false
      - OAUTH2_PROXY_EMAIL_DOMAINS=*
      - OAUTH2_PROXY_UPSTREAMS=http://registry:5000
      - OAUTH2_PROXY_HTTP_ADDRESS=0.0.0.0:4180
      - OAUTH2_PROXY_REDIRECT_URL=http://localhost:4180/oauth2/callback
    restart: unless-stopped
```

### Nginx Front-End Configuration

For production, place oauth2-proxy behind Nginx with TLS:

```nginx
server {
    listen 443 ssl;
    server_name registry.example.com;

    ssl_certificate /etc/ssl/certs/registry.crt;
    ssl_certificate_key /etc/ssl/private/registry.key;

    location / {
        proxy_pass http://oauth2-proxy:4180;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Key Features

- **Broad provider support**: Google, GitHub, GitLab, Azure AD, Keycloak, OIDC, LinkedIn, Facebook, and more
- **Session management**: Cookie-based sessions with configurable expiration
- **Group-based authorization**: Restrict access by email domain or group membership
- **SSO integration**: Works with existing identity infrastructure
- **Well-established**: 10,000+ GitHub stars, active community

### Limitations for Registry Use

- **No Docker token protocol**: oauth2-proxy uses cookie-based auth, not the Docker Registry Token Authentication protocol. Docker clients must authenticate via browser flow or use basic auth passthrough.
- **No per-repository ACLs**: Authorization is all-or-nothing — authenticated users get full registry access.
- **Better for web UIs**: Ideal for protecting registry browser interfaces, less suited for programmatic Docker CLI access.

## Harbor OIDC Authentication

[Harbor](https://github.com/goharbor/harbor) is a full-featured container registry platform with built-in OIDC/OAuth authentication, role-based access control, vulnerability scanning, and image signing. Rather than adding auth to a basic registry, Harbor replaces it entirely.

### Docker Compose Deployment

Harbor provides an official installer that generates the Docker Compose configuration:

```bash
# Download and extract Harbor
wget https://github.com/goharbor/harbor/releases/download/v2.12.0/harbor-offline-installer-v2.12.0.tgz
tar xzvf harbor-offline-installer-v2.12.0.tgz
cd harbor

# Configure harbor.yml
cat > harbor.yml << 'EOF'
hostname: registry.example.com
http:
  port: 80
https:
  port: 443
  certificate: /etc/harbor/ssl/registry.crt
  private_key: /etc/harbor/ssl/registry.key
harbor_admin_password: Harbor12345
database:
  password: db_password
data_volume: /data/harbor
EOF

# Configure OIDC in harbor.yml or via UI after initial setup
# Then install
./install.sh
```

### OIDC Configuration

After Harbor is running, configure OIDC via the web UI or API:

```yaml
# Add to harbor.yml for OIDC auto-configuration
oidc:
  name: keycloak
  endpoint: https://keycloak.example.com/realms/harbor
  verify_cert: true
  auto_onboard: true
  client_id: harbor-oidc-client
  client_secret: your-client-secret
  scope: openid,email,profile
  username_claim: preferred_username
```

Alternatively, configure via the Harbor API:

```bash
curl -X PUT "https://registry.example.com/api/v2.0/configurations"   -H "Content-Type: application/json"   -u "admin:Harbor12345"   -d '{
    "auth_mode": "oidc_auth",
    "oidc_name": "keycloak",
    "oidc_endpoint": "https://keycloak.example.com/realms/harbor",
    "oidc_client_id": "harbor-oidc-client",
    "oidc_client_secret": "your-client-secret",
    "oidc_scope": "openid,email,profile",
    "oidc_verify_cert": true,
    "oidc_auto_onboard": true,
    "oidc_user_claim": "preferred_username"
  }'
```

### Key Features

- **Full registry platform**: Not just auth — includes vulnerability scanning, replication, garbage collection, and project management
- **RBAC**: Role-based access control with project-level permissions (admin, developer, guest, limited guest)
- **OIDC/OAuth 2.0**: Native support for external identity providers
- **LDAP/AD integration**: Direct Active Directory and LDAP authentication
- **Image signing**: Cosign and Notary integration for supply chain security
- **Vulnerability scanning**: Trivy and Clair scanners built in
- **Enterprise-ready**: Used by CNCF, VMware, and large enterprises

## Comparison Table

| Feature | cesanta/docker_auth | oauth2-proxy | Harbor OIDC |
|---------|---------------------|--------------|-------------|
| **Primary Purpose** | Registry auth server | General auth proxy | Full registry platform |
| **Docker Token Protocol** | Yes (native) | No (cookie-based) | Yes (native) |
| **Auth Backends** | Google, GitHub, LDAP, MongoDB, static files | 30+ OAuth/OIDC providers | OIDC, LDAP, AD, DB |
| **Per-Repository ACLs** | Yes (regex-based) | No (all-or-nothing) | Yes (RBAC per project) |
| **GitHub Stars** | 1,500+ | 10,000+ | 21,000+ |
| **Resource Usage** | ~15MB image, minimal | ~50MB image, moderate | ~2GB+ (full stack) |
| **Vulnerability Scanning** | No | No | Yes (Trivy/Clair) |
| **Image Replication** | No | No | Yes (built-in) |
| **Web UI** | No | No | Yes (full admin UI) |
| **Docker CLI Compatible** | Yes | Partially | Yes |
| **Best For** | Lightweight registry auth | Web UI protection | Enterprise registry |

## Choosing the Right Solution

### Use cesanta/docker_auth when:
- You need a lightweight, dedicated auth server for Docker Distribution
- You want per-repository ACLs with regex matching
- You need Docker CLI compatibility with token-based auth
- You prefer a simple static file or LDAP auth backend

### Use oauth2-proxy when:
- You need to protect a registry web UI (Joxit, Docker Registry Browser)
- You already use oauth2-proxy for other services and want consistency
- Your primary access is through browsers, not Docker CLI
- You need broad identity provider support with group-based authorization

### Use Harbor when:
- You need a complete registry platform, not just authentication
- You require vulnerability scanning and image signing
- You need multi-tenant project management with RBAC
- You want built-in replication, garbage collection, and audit logging
- You're running a production registry for a team or organization

## Security Best Practices

1. **Always use TLS** — Never expose registry auth over plain HTTP. Use Let's Encrypt or internal CA certificates.
2. **Rotate signing keys** — For docker_auth, rotate the RSA private key periodically and update the registry's rootcertbundle.
3. **Limit token expiration** — Keep JWT token lifetimes short (15-30 minutes) to reduce the window of compromised token misuse.
4. **Use robot accounts** — Harbor supports robot accounts with scoped, time-limited credentials for CI/CD pipelines.
5. **Audit access logs** — Monitor registry access logs for unusual pull/push patterns that may indicate credential compromise.
6. **Restrict network access** — Place the registry behind a firewall or VPC. Use security groups to limit access to known CI/CD runner IPs.

## FAQ

### Can I use docker_auth with Harbor?

No, Harbor has its own built-in authentication system. docker_auth is designed specifically for Docker Distribution (registry:2). If you're using Harbor, use its native OIDC, LDAP, or database authentication.

### Does oauth2-proxy work with the Docker CLI?

Partially. oauth2-proxy uses cookie-based authentication designed for browsers. Docker CLI authentication requires either basic auth or the Docker Registry Token protocol. For CLI access, you can configure oauth2-proxy to pass through basic auth headers, but this bypasses the OAuth flow. For full Docker CLI compatibility, use docker_auth or Harbor.

### How do I migrate from docker_auth to Harbor?

Export your user list and ACLs from docker_auth, then create Harbor projects and assign users with equivalent roles. Harbor's OIDC integration can use the same identity provider (Google, GitHub, etc.) that docker_auth was using. Push all images to Harbor's storage using `docker pull`, `docker tag`, and `docker push`.

### Can I run multiple registry auth backends simultaneously?

Yes. You can run docker_auth for CLI access and oauth2-proxy for web UI access, both pointing to the same registry. Configure the registry's auth section for docker_auth, and place oauth2-proxy as a separate reverse proxy in front for browser access.

### What happens when a docker_auth token expires?

The Docker client automatically re-authenticates when it receives a 401 response with a new token challenge. The registry returns an unauthorized response, and the Docker client requests a new token from the auth server. This is transparent to the user during normal operations.

### Is Harbor overkill for a small team?

Harbor's full stack (PostgreSQL, Redis, Core, Jobservice, Portal, Registry) requires significant resources (~2GB RAM minimum). For a small team (1-5 developers) running a few services, docker_auth with Docker Distribution is much lighter and simpler. Consider Harbor when you need vulnerability scanning, replication, or multi-project RBAC.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Container Registry Authentication: cesanta/docker_auth vs oauth2-proxy vs Harbor OIDC (2026)",
  "description": "Compare three approaches to securing self-hosted Docker registries: cesanta/docker_auth token server, oauth2-proxy reverse proxy, and Harbor built-in OIDC authentication.",
  "datePublished": "2026-05-22",
  "dateModified": "2026-05-22",
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
