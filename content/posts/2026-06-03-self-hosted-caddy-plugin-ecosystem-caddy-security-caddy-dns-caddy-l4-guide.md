---
title: "Self-Hosted Caddy Plugin Ecosystem: caddy-security vs caddy-dns vs caddy-l4"
date: "2026-06-03"
tags: ["caddy", "web-server", "reverse-proxy", "plugin-ecosystem", "tls", "dns", "layer4", "self-hosted"]
draft: false
---

Caddy has rapidly become one of the most popular self-hosted web servers and reverse proxies, known for its automatic TLS certificate management and clean Caddyfile syntax. What sets Caddy apart from traditional web servers is its plugin architecture — every feature, including HTTP serving and TLS, is implemented as a plugin module that can be extended or replaced.

In this guide, we explore three powerful Caddy plugin categories — **caddy-security** (authentication and authorization), **caddy-dns** (DNS-01 ACME challenge providers), and **caddy-l4** (Layer 4 TCP/UDP proxying) — and demonstrate how they extend Caddy beyond basic HTTP reverse proxying.

## Comparison Table: caddy-security vs caddy-dns vs caddy-l4

| Feature | caddy-security | caddy-dns | caddy-l4 |
|---------|---------------|-----------|----------|
| **Purpose** | Authentication, authorization, MFA | DNS-01 ACME challenge providers | Layer 4 TCP/UDP proxying |
| **Scope** | Application layer (HTTP) | Certificate management | Transport layer |
| **Key Capabilities** | OAuth2/OIDC, portal, MFA, IP filtering | 30+ DNS provider integrations | TCP/TLS/UDP proxy, SNI routing |
| **Configuration Format** | Caddyfile + JSON | Caddyfile `tls` directive | Caddyfile `layer4` block |
| **Dependency** | Built as Caddy module | Built as Caddy module | Built as Caddy module |
| **Enterprise Readiness** | Production-ready | Production-ready | Production-ready |
| **Community Activity** | Active (maintained) | Active (TLS ecosystem) | Active (Caddy core team) |

## caddy-security: Authentication and Authorization Portal

The caddy-security plugin transforms Caddy from a simple reverse proxy into a full-featured authentication gateway. It supports OAuth2, OpenID Connect, multi-factor authentication, and role-based access control — all configured through the Caddyfile without external services.

**Key features:**
- **OAuth2/OIDC integration**: Authenticate against Google, GitHub, Keycloak, Authentik, and any OIDC provider
- **Multi-factor authentication**: TOTP, WebAuthn, and email-based verification
- **Role-based access control**: Define access policies per path based on user roles or claims
- **Built-in portal**: User-facing login, registration, and password reset pages
- **IP filtering**: Restrict access based on client IP ranges

**Docker Compose deployment with caddy-security:**

```yaml
version: "3.8"
services:
  caddy:
    image: caddy:builder
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
    environment:
      - XCADDY_SECURITY_CONFIG=/etc/caddy/security.json
    command: caddy run --config /etc/caddy/Caddyfile

volumes:
  caddy_data:
```

**Caddyfile with caddy-security:**

```caddyfile
{
    order authenticate before respond
    security {
        oauth identity provider google {
            realm google
            client_id {$GOOGLE_CLIENT_ID}
            client_secret {$GOOGLE_CLIENT_SECRET}
        }
        authentication portal myportal {
            crypto default token lifetime 3600
            enable identity provider google
            ui {
                links {
                    "My App" / icon "las la-home"
                }
            }
        }
    }
}

app.example.com {
    authenticate with myportal
    reverse_proxy backend:8080
}
```

This configuration protects `app.example.com` behind Google OAuth2 authentication. Users must log in through Google before accessing the backend application. The portal provides a branded login page with session management.

## caddy-dns: DNS-01 ACME Challenge Providers

Caddy's automatic TLS uses HTTP-01 challenges by default, which work for publicly accessible servers. For internal services, wildcard certificates, or servers behind firewalls, the caddy-dns plugin family provides DNS-01 challenge support through 30+ DNS provider integrations.

**Key features:**
- **Wildcard certificate support**: DNS-01 is the only ACME challenge type that supports wildcards
- **Internal service TLS**: Obtain certificates for services not exposed to the public internet
- **30+ providers**: Cloudflare, Route53, DigitalOcean, CloudDNS, Porkbun, and many more
- **Provider-specific configuration**: API tokens, zone IDs, and credential management

**Caddyfile with Cloudflare DNS challenge:**

```caddyfile
*.internal.example.com {
    tls {
        dns cloudflare {env.CLOUDFLARE_API_TOKEN}
    }
    @service host service.internal.example.com
    handle @service {
        reverse_proxy service:8080
    }
}
```

**Docker Compose with DNS plugin:**

```yaml
services:
  caddy-dns:
    image: caddy:builder
    build:
      dockerfile_inline: |
        FROM caddy:builder
        RUN xcaddy build --with github.com/caddy-dns/cloudflare
    ports:
      - "443:443"
    environment:
      - CLOUDFLARE_API_TOKEN=${CF_TOKEN}
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
```

For internal self-hosted services that never touch the public internet, the DNS challenge approach lets you use valid, trusted TLS certificates without exposing any ports to the internet.

## caddy-l4: Layer 4 TCP/UDP Proxy

The caddy-l4 plugin extends Caddy beyond HTTP into Layer 4 proxying. It handles raw TCP and UDP connections, with support for TLS termination, PROXY protocol, and Server Name Indication (SNI) based routing — making Caddy a unified Layer 4-7 proxy.

**Key features:**
- **TCP/TLS/UDP proxying**: Forward raw connections to backend services
- **SNI-based routing**: Route TLS connections to different backends based on the SNI hostname
- **PROXY protocol**: Preserve client IP information when chaining proxies
- **Health checking**: Active health checks for backend connection pools
- **Connection logging**: Per-connection metrics and access logging

**Caddyfile with Layer 4 configuration:**

```caddyfile
{
    layer4 {
        127.0.0.1:8443 {
            @mysql tls sni mysql.internal.example.com
            route @mysql {
                proxy 10.0.1.50:3306
            }

            @postgres tls sni postgres.internal.example.com
            route @postgres {
                proxy 10.0.1.51:5432
            }
        }
    }
}
```

This configuration routes TLS connections to different database backends based on the SNI hostname. MySQL connections go to `10.0.1.50:3306`, PostgreSQL connections go to `10.0.1.51:5432` — all through a single Caddy instance on port 8443.

**TCP proxy with PROXY protocol:**

```caddyfile
{
    layer4 {
        :5432 {
            proxy 10.0.1.51:5432 {
                proxy_protocol v2
            }
        }
    }
}
```

## Why Self-Host Your Caddy Plugin Infrastructure?

Caddy's plugin ecosystem is unique among web servers because plugins are compiled directly into the Caddy binary rather than loaded at runtime. This design has important implications for self-hosted deployments:

**Single binary deployment simplifies operations.** Instead of managing separate authentication services (Authelia, OAuth2 Proxy) or DNS challenge tools (acme.sh, lego), you compile exactly the plugins you need into one Caddy binary. The `xcaddy` build tool makes this a one-command process.

**caddy-security eliminates the need for a separate auth proxy.** In traditional setups, you might run Caddy + Authelia + an identity provider. With caddy-security, the auth portal, OIDC client, MFA, and session management all run within Caddy itself — reducing the number of containers and services to maintain.

**DNS challenge plugins unlock internal TLS.** Self-hosted services often run on private networks (RFC 1918 addresses) where HTTP-01 challenges cannot reach the server. DNS-01 challenges work without any inbound connectivity — you prove domain ownership through DNS record updates, and Let's Encrypt issues the certificate. This means every internal service, even those behind NAT, can have valid TLS.

**caddy-l4 makes Caddy your unified proxy layer.** Instead of running HAProxy for TCP traffic and Caddy for HTTP, caddy-l4 handles both in one process. This reduces configuration sprawl and simplifies your proxy architecture — one configuration language, one set of TLS certificates, one monitoring endpoint.

For reverse proxy comparison, see our [Nginx Proxy Manager vs SWAG vs Caddy guide](../2026-04-24-nginx-proxy-manager-vs-swag-vs-caddy-docker-proxy-self-hosted-reverse-proxy-gui-guide-2026/). For mTLS deployment, our [Nginx vs Caddy vs Traefik mTLS guide](../2026-04-24-self-hosted-mutual-tls-mtls-nginx-caddy-traefik-envoy-guide-2026/) covers certificate-based authentication. For web server selection, check our [OpenResty vs Nginx vs Caddy comparison](../2026-04-29-openresty-vs-nginx-vs-caddy-self-hosted-web-server-guide-2026/).


## Deployment Architecture Best Practices

When deploying Caddy with plugins in a self-hosted environment, follow these patterns to maximize the benefits of Caddy's unified binary architecture:

**Build a single Caddy image with all required plugins.** Instead of running multiple Caddy instances with different plugin sets, build one Docker image via `xcaddy` that includes caddy-security, your DNS provider module, and caddy-l4. This single binary handles HTTP reverse proxying, authentication, DNS-01 challenges, and TCP proxying — reducing the number of containers in your stack and simplifying certificate management.

**Use Caddy's JSON configuration for complex setups.** While the Caddyfile is excellent for simple reverse proxy configurations, complex setups involving caddy-security with multiple identity providers, caddy-l4 with SNI routing, and DNS challenges are more maintainable in Caddy's native JSON format. The JSON configuration supports environment variable interpolation and can be generated programmatically by configuration management tools.

**Separate internal and external certificates.** Use DNS-01 challenges (via caddy-dns plugins) for wildcard certificates covering internal services, and HTTP-01 challenges for public-facing services. This keeps your internal service certificates in a separate domain namespace and prevents rate limit issues on the public-facing certificates. Caddy automatically selects the right challenge type based on your TLS configuration.

**Implement health checks for proxied backends.** Caddy includes built-in active health checking for reverse proxy upstreams. Configure health checks on your backend services so Caddy can route around failures. For caddy-l4 TCP proxies, implement connection-level health checking through the `health_checks` directive to detect backend availability before forwarding connections.

**Monitor Caddy's built-in metrics.** Caddy exposes a Prometheus metrics endpoint at the `/metrics` path when the `admin` API is enabled. These metrics include request counts, durations, TLS handshake statistics, and plugin-specific counters. Integrate these metrics into your existing monitoring stack to track authentication success rates, DNS challenge renewals, and TCP proxy connection counts.

## FAQ

### How do I build a Caddy binary with custom plugins?

Use the `xcaddy` build tool. Install it with `go install github.com/caddyserver/xcaddy/cmd/xcaddy@latest`, then run commands like `xcaddy build --with github.com/greenpau/caddy-security --with github.com/caddy-dns/cloudflare --with github.com/mholt/caddy-l4`. This produces a `caddy` binary with the specified plugins compiled in. For Docker, use the `caddy:builder` image with a custom Dockerfile.

### Does caddy-security support multiple identity providers simultaneously?

Yes. You can configure multiple OAuth providers and let users choose which one to authenticate with. The portal UI displays all configured providers as login options. You can also use the `authorize` directive to apply different access policies based on which provider was used or what claims the user has.

### Can I use caddy-dns with Let's Encrypt staging for testing?

Yes. Set the ACME CA endpoint to Let's Encrypt staging in your global options: `acme_ca https://acme-staging-v02.api.letsencrypt.org/directory`. This lets you test DNS challenge configurations without hitting Let's Encrypt production rate limits. Remove the staging directive when you're ready for production certificates.

### What's the performance overhead of caddy-l4 compared to dedicated TCP proxies?

caddy-l4 is built on Go's standard network stack with the same connection pooling and buffer management as Caddy's HTTP layer. For most self-hosted workloads (databases, internal services), the overhead is negligible — typically less than 1ms of additional latency. For extreme throughput scenarios (millions of concurrent connections), a dedicated proxy like HAProxy may offer better connection-handling efficiency.

### Can I use caddy-security without the portal UI?

Yes. Set `enable portal off` in the authentication block to disable the login portal and use programmatic authentication (API tokens, JWT validation). This is useful for machine-to-machine authentication or when you want to embed Caddy's auth checks without redirecting users to a login page.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Caddy Plugin Ecosystem: caddy-security vs caddy-dns vs caddy-l4",
  "description": "Explore Caddy's plugin ecosystem for self-hosted deployments. Compare caddy-security (auth/OIDC), caddy-dns (DNS-01 ACME), and caddy-l4 (TCP/UDP proxy) with Docker Compose examples.",
  "datePublished": "2026-06-03",
  "dateModified": "2026-06-03",
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

***💡 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)**
