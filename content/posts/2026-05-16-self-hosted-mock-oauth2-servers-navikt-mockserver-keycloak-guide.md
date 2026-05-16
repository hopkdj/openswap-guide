---
title: "Self-Hosted Mock OAuth2 Servers: navikt vs MockServer vs Keycloak"
date: "2026-05-16"
tags: ["oauth2", "authentication", "testing", "security", "docker"]
draft: false
---

Mock OAuth2 servers are essential for testing authentication flows without depending on real identity providers like Google, Okta, or Auth0. They let you simulate token issuance, redirect flows, and error conditions locally — critical for CI/CD pipelines, integration testing, and development environments. This guide compares three self-hosted mock OAuth2 solutions with Docker deployment configs.

## What Is a Mock OAuth2 Server?

A mock OAuth2 / OpenID Connect server simulates the behavior of a real identity provider (IdP) for testing purposes. It supports the standard OAuth2 flows — authorization code, client credentials, implicit, and device code — but runs entirely locally with configurable users, scopes, and token responses.

Key capabilities include:

- **Token generation** — Issue JWT access tokens, ID tokens, and refresh tokens with configurable claims
- **Flow simulation** — Support authorization code redirect flows, PKCE, and client credentials
- **User management** — Define test users with specific roles, groups, and custom claims
- **Error injection** — Simulate token expiration, invalid grants, and consent denial
- **Introspection endpoints** — Support token introspection and userinfo endpoints

## Tool Comparison

| Feature | navikt/mock-oauth2-server | MockServer (OAuth) | Keycloak Dev Mode |
|---|---|---|---|
| GitHub Stars | 382+ | 4,875+ | 24,000+ |
| Protocol | OAuth2/OIDC | HTTP + OAuth2 plugins | Full OIDC/OAuth2 |
| Language | Kotlin/Java | Java | Java |
| Docker Image | Yes (official) | Yes (official) | Yes (official) |
| Token Types | JWT (RSA/EC) | Configurable | JWT (multiple algorithms) |
| PKCE Support | Yes | Via templates | Yes |
| Multi-Tenant | Yes | Via expectations | Via realms |
| Admin UI | Web UI | Web UI + API | Full Admin Console |
| CI/CD Ready | Yes | Yes | Yes (dev mode) |
| Organization | NAV (Norwegian Gov) | MockServer Project | Red Hat |

### navikt/mock-oauth2-server

The [navikt/mock-oauth2-server](https://github.com/navikt/mock-oauth2-server) from Norway Labour and Welfare Administration (NAV) is purpose-built for OAuth2 and OpenID Connect testing. It supports token callbacks, custom claim injection, and interactive login pages.

```yaml
# docker-compose.yml
services:
  mock-oauth2:
    image: ghcr.io/navikt/mock-oauth2-server:2.1.10
    ports:
      - "8080:8080"
    environment:
      - SERVER_PORT=8080
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:8080/health"]
      interval: 10s
      timeout: 5s
      retries: 3
```

Configure test tokens via the API:

```bash
# Get a token for a specific user
curl -X POST http://localhost:8080/token -d "grant_type=client_credentials" -d "client_id=my-app"

# Configure interactive login
curl -X POST http://localhost:8080/callbacks -H "Content-Type: application/json" -d '{"interactive": true}'
```

### MockServer with OAuth2

[MockServer](https://github.com/mock-server/mockserver) is a general-purpose HTTP mock that can simulate OAuth2 endpoints through its expectation engine. While not OAuth2-specific, its flexibility lets you model any IdP behavior including complex redirect flows and token refresh chains.

```yaml
services:
  mockserver:
    image: mockserver/mockserver:5.15.0
    ports:
      - "1080:1080"
    environment:
      - MOCKSERVER_LOG_LEVEL=INFO
      - MOCKSERVER_WATCH_INITIALIZATION_JSON=true
      - MOCKSERVER_INITIALIZATION_JSON_PATH=/config/expectations.json
    volumes:
      - ./mockserver-config:/config:ro
    restart: unless-stopped
```

Define OAuth2 expectations in the config JSON file with request/response pairs for token endpoints, authorization endpoints, and the OpenID Connect discovery document.

### Keycloak in Dev Mode

While Keycloak itself is not a "mock" server, running it in dev mode with an in-memory database provides a lightweight IdP for integration testing that is much faster than a production deployment. It gives you the full Keycloak feature set — realms, clients, roles, user federation — without the database overhead.

```yaml
services:
  keycloak-test:
    image: quay.io/keycloak/keycloak:26.0
    command: start-dev --http-port=8080
    ports:
      - "8080:8080"
    environment:
      - KEYCLOAK_ADMIN=admin
      - KEYCLOAK_ADMIN_PASSWORD=admin
      - KC_DB=dev-file
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8080/health/ready || exit 1"]
      interval: 15s
      timeout: 10s
      retries: 10
```

## Why Self-Host Mock OAuth2 Servers?

Running mock OAuth2 servers locally eliminates external dependencies in your testing pipeline. Key advantages include deterministic testing without real IdP latency or rate limits, offline development without internet access or corporate firewall restrictions, edge case testing for token expiration and consent denial that real providers cannot easily simulate, cost savings from avoiding commercial IdP charges during development, and security from not sending real credentials over the network.

Self-hosted mock servers also give you full control over token content. You can inject arbitrary claims, set custom expiration times, and simulate any error response. This level of control is impossible with external providers that enforce their own token formats and error behaviors.

## Choosing the Right Mock OAuth2 Server

The navikt mock server is the best choice when you need a dedicated OAuth2/OIDC mock with proper JWT generation, PKCE support, and interactive login. It is purpose-built for this use case and handles all standard OAuth2 flows correctly.

MockServer excels when you need flexibility beyond OAuth2 — it can mock any HTTP-based service alongside your IdP, making it ideal for end-to-end integration tests that span multiple services. Its expectation engine supports complex conditional responses and verification.

Keycloak in dev mode is appropriate when your application depends on Keycloak-specific features like admin REST API, specific token claim formats, or Keycloak JavaScript SPI. It is the heaviest option but provides the most accurate simulation of a real Keycloak deployment.

For comprehensive authentication platform comparisons, see our [self-hosted auth platforms guide](../2026-05-10-self-hosted-auth-platforms-logto-supertokens-ory-kratos-guide-2026/). If you need MFA/OTP testing, our [MFA server comparison](../2026-05-07-mfa-otp-servers-privacyidea-linotp-2fauth-guide-2026/) covers dedicated multi-factor authentication servers. For mutual TLS authentication, check our [end-to-end encryption guide](../2026-05-12-self-hosted-mutual-tls-mtls-nginx-caddy-traefik-end-to-end-encryption-guide-2026/).

## Mock Server Deployment Architecture

Deploying mock OAuth2 servers in a production-like testing environment requires careful architecture planning. Use separate mock instances for different testing stages — unit tests need fast, lightweight mocks that start in milliseconds, integration tests require realistic token responses with proper timing, and manual testing benefits from interactive login interfaces. Running all three on shared infrastructure with Docker Compose profiles allows developers to spin up only the environments they need.

Network isolation between mock servers and the application under test prevents accidental calls to real identity providers. Configure your mock server to bind only to localhost or a dedicated test network. Use firewall rules or network policies to block outbound traffic to known production IdP endpoints from the test environment. This ensures that even if an application is misconfigured with production credentials, it cannot reach the real IdP during testing.


## Production Authentication Testing Best Practices

When building authentication testing infrastructure, several considerations go beyond basic mock server deployment. Token structure consistency is critical — your mock should produce tokens with identical claim sets, signing algorithms, and header structures as your production identity provider. If production uses RS256 with a specific key ID in the JWT header, your mock must match. Mismatched token structures cause subtle bugs that only appear in production when the real IdP behaves differently than the mock.

Token lifecycle testing is equally important. Many development teams configure mock servers with tokens that never expire, which means token refresh logic, session timeout handling, and re-authentication flows never get tested. Configure short expiry times in your mock so that every test run exercises the complete authentication lifecycle. This catches bugs in refresh token handling that would otherwise cause production outages when sessions expire unexpectedly.

Error path testing is where mock servers provide the most value over real IdPs. Configure your mock to return specific error responses — expired tokens, invalid grants, consent denial, server errors, and rate limit responses. Test how your application handles each scenario. The most common production authentication failures involve unexpected error responses from the IdP, and mock servers are the only practical way to test these conditions systematically.


## FAQ

### Why not just use a real OAuth2 provider for testing?

Real providers introduce latency, rate limits, network dependencies, and cost into your test pipeline. They also cannot simulate error conditions like token expiration mid-request or consent denial. Mock servers provide deterministic, instant responses and full control over every aspect of the authentication flow.

### Can mock OAuth2 servers replace real IdPs in production?

No. Mock servers are designed for testing and development only. They do not implement security features like rate limiting, brute force protection, or proper credential storage. Always use a production-grade IdP (Keycloak, Authentik, Ory) for real user authentication.

### Do mock OAuth2 servers support PKCE?

The navikt mock server supports PKCE (Proof Key for Code Exchange) fully, including code verifier and code challenge validation. MockServer can simulate PKCE flows through its expectation engine but does not validate the challenge cryptographically. Keycloak dev mode supports PKCE natively.

### How do I integrate mock OAuth2 with CI/CD pipelines?

Start the mock server as a Docker container in your CI job before running tests. Most CI systems (GitHub Actions, GitLab CI, Jenkins) support Docker-in-Docker or Docker sidecar containers. Configure your application OAuth2 client to point to the mock server URL via environment variables.

### Can mock servers handle token refresh flows?

Yes. The navikt mock server supports refresh token issuance and validation. MockServer can simulate refresh token responses through its expectation templates. Keycloak dev mode handles the full token refresh lifecycle including refresh token rotation.

### What JWT signing algorithms do mock servers support?

The navikt mock server supports RSA (RS256) and EC (ES256) signing. You can provide your own key pair or let the server generate one. MockServer returns whatever string you configure in the response body. Keycloak supports RS256, ES256, HS256, and EdDSA.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Mock OAuth2 Servers: navikt vs MockServer vs Keycloak",
  "description": "Compare three self-hosted mock OAuth2 server solutions for testing authentication flows — navikt/mock-oauth2-server, MockServer, and Keycloak dev mode — with Docker Compose configs.",
  "datePublished": "2026-05-16",
  "dateModified": "2026-05-16",
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
