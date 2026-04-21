---
title: "OAuth2-Proxy vs Pomerium vs Traefik-Forward-Auth: Best Self-Hosted Auth Proxy 2026"
date: 2026-04-18
tags: ["comparison", "guide", "self-hosted", "security", "authentication", "oauth", "reverse-proxy"]
draft: false
description: "Compare OAuth2-Proxy, Pomerium, and Traefik-Forward-Auth — the top three open-source authentication proxies for protecting self-hosted web services behind a reverse proxy."
---

If you self-host web applications — dashboards, admin panels, internal tools, or APIs — one of the first questions you face is: **how do I protect them from unauthorized access?**

You cannot expose a [grafana](https://grafana.com/) dashboard, a Portainer instance, or a custom internal API directly to the internet without authentication. Yet managing separate login systems for every service is tedious and error-prone.

The answer is an **authentication proxy** — a reverse proxy that intercepts requests, verifies the user's identity against an identity provider (IdP), and forwards authenticated traffic to your backend services. In this guide, we compare the three leading open-source options: **OAuth2-Proxy**, **Pomerium**, and **Traefik-Forward-Auth**.

## Why Use a Self-Hosted Auth Proxy?

Self-hosting your authentication proxy gives you full control over who can access your services:

- **Single sign-on (SSO)** — authenticate once, access all protected services
- **Centralized access control** — manage permissions from one place
- **No per-service auth setup** — protect apps that lack built-in authentication
- **Identity provider flexibility*[keycloak](https://www.keycloak.org/)Google, GitHub, Keycloak, Authentik, OIDC, or dozens of others
- **Zero-trust architecture** — every request is verified, regardless of network location

Rather than configuring OAuth or basic auth separately for each application, an auth proxy sits in front of everything and handles authentication uniformly.

## At a Glance: Comparison Table

| Feature | OAuth2-Proxy | Pomerium | Traefik-Forward-Auth |
|---------|-------------|----------|---------------------|
| **GitHub Stars** | 14,217 | 4,748 | 2,379 |
| **Language** | Go | Go | Go |
| **Last Updated** | April 2026 | April 2026 | April 2026 |
| **License** | Apache 2.0 | Apache 2.0 | MIT |
| **IdP Support** | 20+ providers | OIDC, Google, Azure | Google, OIDC only |
| **Zero-Trust / BeyondCorp** | No | Yes (core feature) | No |
| **gRPC / mTLS Support** | No | Yes | No |
| **Policy Engine (RBAC)** | Basic headers | Full CEL policies | None |
| **WebSocket Support** | Yes | Yes | Yes |
| **Traefik Integration** | Via forwardAuth | Via forwardAuth | Native (same project) |
| **[docker](https://www.docker.com/) Image Size** | ~25 MB | ~45 MB | ~15 MB |
| **Best For** | General-purpose auth proxy | Zero-trust / enterprise | Simple Google/OIDC + Traefik |

## OAuth2-Proxy: The Swiss Army Knife

**OAuth2-Proxy** (by the oauth2-proxy organization) is the most widely deployed open-source authentication proxy. It supports over 20 identity providers including Google, GitHub, GitLab, Azure AD, Keycloak, Authentik, and any OIDC-compatible IdP.

It works by intercepting incoming HTTP requests, checking for a valid session cookie, and redirecting unauthenticated users to your IdP's login page. After successful authentication, it sets a signed cookie and injects user identity headers (`X-Auth-Request-User`, `X-Auth-Request-Email`, `X-Auth-Request-Groups`) into the upstream request — which your backend application can read to implement authorization.

### Key Features

- **Broad IdP support** — Google, GitHub, GitLab, Azure AD, Bitbucket, Keycloak, Authentik, OIDC, and more
- **Session management** — Redis, Memcached, or cookie-based sessions
- **Header injection** — passes user identity to upstream services via HTTP headers
- **Multiple deployment modes** — works with NGINX, Traefik, HAProxy, Caddy, or any reverse proxy via `auth_request` or forward authentication
- **WebSocket support** — can protect WebSocket connections
- **Token refresh** — automatically refreshes expiring OAuth tokens

### Docker Compose Setup

Here is a production-ready Docker Compose configuration for OAuth2-Proxy with Google as the identity provider, sitting behind a reverse proxy:

```yaml
version: "3.8"

services:
  oauth2-proxy:
    image: quay.io/oauth2-proxy/oauth2-proxy:v7.7.1
    container_name: oauth2-proxy
    restart: unless-stopped
    ports:
      - "4180:4180"
    environment:
      OAUTH2_PROXY_PROVIDER: "google"
      OAUTH2_PROXY_CLIENT_ID: "${GOOGLE_CLIENT_ID}"
      OAUTH2_PROXY_CLIENT_SECRET: "${GOOGLE_CLIENT_SECRET}"
      OAUTH2_PROXY_COOKIE_SECRET: "${COOKIE_SECRET}"
      OAUTH2_PROXY_COOKIE_SECURE: "true"
      OAUTH2_PROXY_EMAIL_DOMAINS: "yourdomain.com"
      OAUTH2_PROXY_UPSTREAMS: "http://localhost:3000"
      OAUTH2_PROXY_HTTP_ADDRESS: "0.0.0.0:4180"
      OAUTH2_PROXY_REVERSE_PROXY: "true"
      OAUTH2_PROXY_SET_XAUTHREQUEST: "true"
    networks:
      - proxy-net

networks:
  proxy-net:
    external: true
```

Generate the required secrets:

```bash
# Cookie secret: 32 bytes, base64-encoded (used to sign session cookies)
python3 -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"

# Or with head and openssl:
head -c 32 /dev/urandom | base64
openssl rand -base64 32
```

### NGINX Integration

When deployed behind NGINX, use the `auth_request` directive to delegate authentication:

```nginx
server {
    listen 443 ssl;
    server_name app.example.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    location / {
        auth_request /oauth2/auth;
        auth_request_set $user  $upstream_http_x_auth_request_user;
        auth_request_set $email $upstream_http_x_auth_request_email;

        proxy_set_header X-Auth-Request-User  $user;
        proxy_set_header X-Auth-Request-Email $email;

        proxy_pass http://localhost:3000;
    }

    location = /oauth2/auth {
        internal;
        proxy_pass http://oauth2-proxy:4180;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /oauth2/ {
        proxy_pass http://oauth2-proxy:4180;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

This pattern works identically with Traefik (`forwardAuth`), HAProxy (`http-check`), and Caddy (`forward_auth` directive).

### Supported Identity Providers

OAuth2-Proxy has first-class support for these providers:

| Provider | Config Value | Notes |
|----------|-------------|-------|
| Google | `google` | Most popular, simple setup |
| GitHub | `github` | Requires org/team config for access control |
| GitLab | `gitlab` | Works with self-hosted GitLab instances |
| Azure AD | `azure` | Supports Microsoft Entra ID |
| Keycloak | `keycloak-oidc` | Full RBAC via groups |
| Authentik | `oidc` | Works via generic OIDC provider |
| Any OIDC | `oidc` | Generic OpenID Connect support |
| Bitbucket | `bitbucket` | Team-based access control |
| Facebook | `facebook` | Available but rarely used |
| LinkedIn | `linkedin` | Limited scope data |

## Pomerium: Zero-Trust Access Proxy

**Pomerium** takes a fundamentally different approach. While OAuth2-Proxy is an authentication proxy that adds a login layer, Pomerium implements a full **zero-trust / BeyondCorp** architecture. Every request is authenticated, authorized, and encrypted — regardless of whether the user is on the internal network or the public internet.

Pomerium's policy engine uses the Common Expression Language (CEL) to define fine-grained access rules based on user identity, device posture, time of day, and more. It also supports mutual TLS (mTLS) between services and can issue short-lived certificates.

### Key Features

- **Zero-trust by default** — every request is verified, no implicit trust based on network location
- **CEL policy engine** — define access rules like `allow(user.email == "admin@corp.com" && user.groups.contains("engineering"))`
- **Mutual TLS** — automatic mTLS between services with short-lived certificates
- **Device posture checks** — verify device compliance before granting access
- **gRPC and HTTP support** — protects both HTTP/HTTPS and gRPC services
- **Identity-aware proxy** — not just authentication, but full identity propagation
- **Built-in audit logging** — every access decision is logged

### Docker Compose Setup

Pomerium's official example provides a clean starting point with autocert for TLS:

```yaml
version: "3"

services:
  pomerium:
    image: pomerium/pomerium:latest
    container_name: pomerium
    restart: unless-stopped
    environment:
      # Generate with: head -c32 /dev/urandom | base64
      - POMERIUM_COOKIE_SECRET=${COOKIE_SECRET}
      - POMERIUM_SHARED_SECRET=${SHARED_SECRET}
      - POMERIUM_CERTIFICATE_FILE=/pomerium/cert.pem
      - POMERIUM_CERTIFICATE_KEY_FILE=/pomerium/privkey.pem
      - POMERIUM_AUTHENTICATE_SERVICE_URL=https://authenticate.example.com
      - POMERIUM_IDP_PROVIDER=google
      - POMERIUM_IDP_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - POMERIUM_IDP_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
      # Policy: route and protect your services
      - |
        POMERIUM_POLICY_JSON=[{
          "from": "https://app.example.com",
          "to": "http://app-service:3000",
          "allowed_users": ["user@yourdomain.com"]
        }]
    volumes:
      - pomerium:/data:rw
    ports:
      - "443:443"
    networks:
      - proxy-net

  verify:
    image: pomerium/verify:latest
    container_name: pomerium-verify
    expose:
      - "80"
    networks:
      - proxy-net

volumes:
  pomerium:
networks:
  proxy-net:
    external: true
```

### Pomerium Policy Examples

The policy engine is Pomerium's most powerful feature. Here are practical examples:

```yaml
# Policy in YAML format (Pomerium reads YAML or JSON)
- from: https://grafana.example.com
  to: http://grafana:3000
  allowed_users:
    - admin@example.com
    - ops@example.com

- from: https://api.example.com
  to: http://api-service:8080
  allowed_idp_claims:
    "groups":
      - engineering
      - devops

- from: https://internal.example.com
  to: http://internal:8080
  allowed_users:
    - "*"
  # Restrict to business hours only
  enable_google_cloud_serverless_authentication: false
```

For advanced use cases, CEL expressions allow programmatic access rules:

```
# Only allow access from users in the "engineering" group
# AND on managed devices (device posture check)
allow(user.groups.contains("engineering") && device.trusted == true)
```

## Traefik-Forward-Auth: Minimalist Google/OIDC Auth

**Traefik-Forward-Auth** by Thomas Seddon is the simplest of the three. It is purpose-built to work with Traefik's `forwardAuth` middleware and supports Google OAuth2 and generic OIDC providers. If you already use Traefik as your reverse proxy and only need Google or OIDC login, this is the lightest option.

### Key Features

- **Tiny footprint** — minimal binary, fast startup, low memory usage
- **Traefik native** — designed specifically for Traefik's forward authentication middleware
- **Simple configuration** — fewer moving parts than OAuth2-Proxy or Pomerium
- **Google OAuth2** — one-command Google login for all Traefik services
- **Generic OIDC** — also supports any OpenID Connect provider
- **Domain whitelisting** — restrict access to specific email domains

### Docker Compose Setup

Traefik-Forward-Auth works alongside Traefik. Here is a complete setup:

```yaml
version: "3.8"

services:
  traefik:
    image: traefik:v3.2
    container_name: traefik
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./traefik.yaml:/etc/traefik/traefik.yaml:ro
    networks:
      - proxy-net

  traefik-forward-auth:
    image: thomseddon/traefik-forward-auth:2.2.1
    container_name: traefik-forward-auth
    restart: unless-stopped
    environment:
      - PROVIDERS_GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - PROVIDERS_GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
      - SECRET=${COOKIE_SECRET}
      - AUTH_HOST=auth.example.com
      - COOKIE_DOMAIN=example.com
      - RULES=claim:groups:engineering|domain:example.com
    networks:
      - proxy-net

networks:
  proxy-net:
    external: true
```

Traefik configuration with forward auth middleware:

```yaml
# traefik.yaml
entryPoints:
  websecure:
    address: ":443"

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false

certificatesResolvers:
  letsencrypt:
    acme:
      email: admin@example.com
      storage: /etc/traefik/acme.json
      httpChallenge:
        entryPoint: web
```

Docker labels to protect a service:

```yaml
  my-service:
    image: my-app:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.my-service.rule=Host(`app.example.com`)"
      - "traefik.http.routers.my-service.tls=true"
      - "traefik.http.routers.my-service.tls.certresolver=letsencrypt"
      - "traefik.http.routers.my-service.middlewares=auth"
      - "traefik.http.middlewares.auth.forwardAuth.address=http://traefik-forward-auth:4181"
      - "traefik.http.middlewares.auth.forwardAuth.authResponseHeaders=X-Forwarded-User"
```

## Choosing the Right Auth Proxy

### Choose OAuth2-Proxy when:
- You need support for many identity providers (GitHub, GitLab, Bitbucket, Keycloak, etc.)
- You use NGINX, Caddy, or HAProxy (not just Traefik)
- You want a proven, battle-tested solution with a large community
- You need cookie-based sessions with Redis/Memcached backend
- Your applications read user identity from HTTP headers

### Choose Pomerium when:
- You are building a zero-trust architecture
- You need fine-grained access policies (CEL expressions)
- You require mutual TLS between services
- You want device posture checks and conditional access
- You need to protect gRPC services alongside HTTP
- Audit logging of every access decision is required

### Choose Traefik-Forward-Auth when:
- You already use Traefik as your reverse proxy
- You only need Google or OIDC authentication
- You want the simplest possible setup with minimal configuration
- You prefer a lightweight binary with low resource usage
- Your access control needs are basic (domain or email whitelisting)

## Internal Ecosystem: How These Fit Together

An auth proxy is typically one piece of a larger self-hosted identity stack. For the identity provider itself, you might use a self-hosted IdP like **Keycloak**, **Authentik**, **Authelia**, or **Zitadel** — see our [detailed IAM comparison](../zitadel-vs-ory-vs-keycloak-self-hosted-iam-guide/) and [Authentik vs Keycloak vs Authelia guide](../authentik-vs-keycloak-vs-authelia/) for help choosing.

The auth proxy then sits between your IdP and your services. OAuth2-Proxy and Pomerium both support self-hosted IdPs via generic OIDC, meaning you can run Authentik or Keycloak on your own server and use it as the authentication backend — no Google or Azure dependency required.

For a complete overview of how reverse proxies integrate with auth proxies, see our [reverse proxy comparison](../reverse-proxy-comparison/) which covers NGINX, Traefik, Caddy, HAProxy, and their authentication patterns.

## FAQ

### What is the difference between OAuth2-Proxy and Pomerium?

OAuth2-Proxy is an authentication proxy that verifies user identity and passes it to upstream services via HTTP headers. Pomerium is a full zero-trust access proxy that adds policy-based authorization, mutual TLS, device posture checks, and audit logging on top of authentication. OAuth2-Proxy answers "who is this user?"; Pomerium answers "who is this user, are they authorized, is their device trusted, and should this specific request be allowed?"

### Can I use OAuth2-Proxy with Authentik or Keycloak?

Yes. OAuth2-Proxy supports generic OIDC providers, which means any OIDC-compliant identity provider works — including self-hosted options like Authentik, Keycloak, Zitadel, and Ory Hydra. Configure `OAUTH2_PROXY_PROVIDER=oidc` and set the OIDC discovery URL to point to your IdP.

### Does Pomerium replace my reverse proxy?

Not exactly. Pomerium includes its own routing capabilities and can terminate TLS directly, but many deployments run Pomerium behind Traefik, NGINX, or Caddy for certificate management, load balancing, or rate limiting. Pomerium can operate as a sidecar, a standalone proxy, or behind another reverse proxy.

### Which auth proxy is easiest to set up?

Traefik-Forward-Auth is the simplest if you already use Traefik — it requires only a few environment variables and Docker labels on each protected service. OAuth2-Proxy requires more configuration but offers far broader IdP support. Pomerium has the steepest learning curve due to its policy engine but provides the most powerful access control.

### Can these auth proxies protect WebSocket connections?

OAuth2-Proxy and Pomerium both support WebSocket connections. Traefik-Forward-Auth works with WebSockets through Traefik's native WebSocket support, as the forward auth check only happens on the initial HTTP upgrade request.

### Do I need HTTPS to use an auth proxy?

Yes. All three proxies require HTTPS (or at minimum TLS termination) in production because they set authentication cookies. Without HTTPS, session cookies would be transmitted in plaintext and could be intercepted. Use Let's Encrypt with your reverse proxy for free, automated TLS certificates.

### How do these handle token refresh and session expiry?

OAuth2-Proxy automatically refreshes expiring OAuth tokens and manages session expiry via its cookie or Redis/Memcached session store. Pomerium uses short-lived JWT tokens that are refreshed transparently. Traefik-Forward-Auth relies on Google/OIDC token expiry and re-authenticates users when tokens expire.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "OAuth2-Proxy vs Pomerium vs Traefik-Forward-Auth: Best Self-Hosted Auth Proxy 2026",
  "description": "Compare OAuth2-Proxy, Pomerium, and Traefik-Forward-Auth — the top three open-source authentication proxies for protecting self-hosted web services behind a reverse proxy.",
  "datePublished": "2026-04-18",
  "dateModified": "2026-04-18",
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
