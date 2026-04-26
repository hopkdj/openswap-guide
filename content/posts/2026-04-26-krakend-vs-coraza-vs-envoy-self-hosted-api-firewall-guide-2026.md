---
title: "KrakenD vs Coraza vs Envoy: Best Self-Hosted API Firewall 2026"
date: 2026-04-26
tags: ["comparison", "guide", "self-hosted", "security", "api"]
draft: false
description: "Compare KrakenD, Coraza WAF, and Envoy Proxy as self-hosted API firewall solutions. Practical deployment guides, Docker configs, and feature comparison for protecting your APIs in 2026."
---

## Why You Need an API Firewall

Modern applications expose dozens — sometimes hundreds — of API endpoints. Traditional web application firewalls (WAFs) protect against common web threats like SQL injection and cross-site scripting, but they do not understand API-specific attack vectors. An API firewall operates at a higher level of abstraction, validating request schemas, enforcing rate limits per endpoint, blocking unexpected parameters, and ensuring that every request conforms to your OpenAPI specification.

For self-hosted deployments, you need a solution that runs entirely within your infrastructure, respects data sovereignty, and does not send traffic to a third-party cloud. This guide compares three distinct approaches to self-hosted API protection: **KrakenD** (a dedicated API gateway with built-in security middleware), **Coraza WAF** (an open-source, ModSecurity-compatible web application firewall), and **Envoy Proxy** (a cloud-native service proxy with extensible API security capabilities).

Each tool takes a fundamentally different approach. KrakenD acts as a stateless API gateway that validates and transforms requests before they reach your backend. Coraza is a full WAF engine that inspects every request against rule sets like OWASP Core Rule Set (CRS). Envoy is a general-purpose proxy that can be extended with external authentication, rate limiting, and Lua/WASM-based security logic.

For related reading, see our [complete WAF comparison](../self-hosted-waf-bot-protection-modsecurity-coraza-crowdsec-2026/) and [API gateway round-up](../self-hosted-api-gateway-apisix-kong-tyk-guide/) for broader context on securing self-hosted services.

## What Is an API Firewall?

An API firewall sits between your clients and your backend services, enforcing security policies at the API layer. Unlike traditional network firewalls that operate on IP addresses and ports, or WAFs that focus on HTTP-level attack signatures, an API firewall understands the structure of your API and validates:

- **Request schemas** — ensuring only expected parameters are sent
- **Response schemas** — preventing data leakage in API responses
- **Rate limits** — protecting against abuse on a per-endpoint basis
- **Authentication** — verifying JWT tokens, API keys, or OAuth credentials
- **Geofencing** — blocking traffic from unexpected regions
- **Bot detection** — identifying automated scrapers and abuse patterns

The three tools covered here represent different philosophies in API protection:

| Feature | KrakenD | Coraza WAF | Envoy Proxy |
|---|---|---|---|
| **Type** | API Gateway | Web Application Firewall | Cloud-Native Proxy |
| **Language** | Go | Go | C++ |
| **GitHub Stars** | 2,600+ | 3,400+ | 27,800+ |
| **Last Updated** | April 2026 | April 2026 | April 2026 |
| **License** | Apache 2.0 (CE) | Apache 2.0 | Apache 2.0 |
| **Schema Validation** | Built-in (OpenAPI) | Via ModSecurity rules | Via WASM/Lua filters |
| **OWASP CRS** | No | Full support | Via Coraza integration |
| **Rate Limiting** | Native (token bucket) | Via rules | Native (global + local) |
| **JWT Validation** | Native | Via rules | Native (JWT filter) |
| **Stateless** | Yes | Yes | Yes |
| **Hot Reload** | Yes | Partial | Yes (xDS) |
| **Performance** | Very high (stateless) | High | Very high (C++) |
| **Learning Curve** | Low | Medium | High |

## KrakenD: Stateless API Gateway as Firewall

[KrakenD](https://www.krakend.io/) is a high-performance, stateless API gateway written in Go. Its Community Edition is open-source under the Apache 2.0 license. KrakenD treats security as a first-class concern — every endpoint definition can include request validation, rate limiting, JWT verification, and header manipulation.

### Key Security Features

- **Declarative configuration** — all security policies defined in a single JSON file
- **Request validation** — reject requests that do not match your endpoint specification
- **Rate limiting** — token bucket algorithm with configurable limits per endpoint
- **JWT validation** — verify tokens against RSA, ECDSA, or HMAC keys before forwarding
- **Header sanitization** — strip or inject headers to prevent information leakage
- **CORS control** — precise cross-origin resource sharing policies
- **Backend timeout enforcement** — prevent slow-loris and timeout-based attacks

### Docker Compose Configuration

KrakenD is distributed as a single Docker image. The configuration is a single JSON file that defines all endpoints, backends, and security policies.

```yaml
version: '3.8'

services:
  krakend:
    image: devopsfaith/krakend:latest
    container_name: krakend-api-firewall
    ports:
      - "8080:8080"
    volumes:
      - ./krakend.json:/etc/krakend/krakend.json:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "krakend", "check", "-c", "/etc/krakend/krakend.json"]
      interval: 30s
      timeout: 10s
      retries: 3
```

A minimal `krakend.json` with API firewall policies:

```json
{
  "version": 3,
  "name": "API Firewall",
  "port": 8080,
  "host": ["http://your-backend-service:3000"],
  "endpoints": [
    {
      "endpoint": "/api/v1/users",
      "method": "GET",
      "input_headers": ["Authorization", "Content-Type"],
      "input_query_strings": ["page", "limit"],
      "output_encoding": "json",
      "backend": [
        {
          "url_pattern": "/users",
          "encoding": "json",
          "method": "GET",
          "host": ["http://your-backend-service:3000"]
        }
      ],
      "extra_config": {
        "github.com/devopsfaith/krakend-ratelimit/juju/proxy": {
          "max_rate": 10,
          "capacity": 50
        },
        "security/cors": {
          "allow_origins": ["https://your-app.com"],
          "allow_methods": ["GET"],
          "allow_headers": ["Authorization", "Content-Type"],
          "max_age": "12h"
        }
      }
    }
  ]
}
```

This configuration restricts the `/api/v1/users` endpoint to only accept `Authorization` and `Content-Type` headers, allows only `page` and `limit` query parameters, enforces a rate limit of 10 requests per second with a burst capacity of 50, and applies strict CORS rules. Any request that deviates from this specification is rejected before it reaches your backend.

### Why Choose KrakenD

KrakenD is ideal when you want a declarative, configuration-driven approach to API security. You define what is allowed, and everything else is denied by default. The stateless architecture means it scales horizontally without shared state, and the Go-based engine handles tens of thousands of requests per second on modest hardware.

## Coraza WAF: OWASP-Powered API Protection

[Coraza WAF](https://coraza.io/) is an open-source, ModSecurity-compatible web application firewall written in Go. It implements the OWASP Core Rule Set (CRS) and supports SecLang rules, making it a drop-in replacement for ModSecurity in environments that need enterprise-grade API protection.

### Key Security Features

- **OWASP CRS support** — full compatibility with the OWASP Core Rule Set v4.x
- **SecLang rules** — use ModSecurity-style rule files for custom security logic
- **Request body inspection** — analyze POST payloads for malicious content
- **Response body inspection** — detect data leakage in API responses
- **IP reputation** — block traffic from known malicious sources
- **GeoIP filtering** — restrict access by geographic region
- **Multi-processing** — supports both standalone and embedded deployment

### Docker Compose Configuration

Coraza can be deployed with the official Docker image, typically paired with Caddy or as a standalone WAF proxy. The configuration uses a `coraza.conf` file that references rule sets.

```yaml
version: '3.8'

services:
  coraza:
    image: ghcr.io/corazawaf/coraza:latest
    container_name: coraza-waf
    ports:
      - "8080:8080"
      - "443:443"
    volumes:
      - ./coraza.conf:/etc/coraza/coraza.conf:ro
      - ./rules:/etc/coraza/rules:ro
    environment:
      - CORAZA_CONF=/etc/coraza/coraza.conf
    restart: unless-stopped
```

A `coraza.conf` configuration for API protection:

```
# Coraza WAF - API Firewall Configuration

# Load OWASP Core Rule Set
Include @owasp_crs/crs-setup.conf
Include @owasp_crs/rules/*.conf

# Custom API-specific rules
SecRuleEngine On
SecRequestBodyAccess On
SecResponseBodyAccess On
SecRequestBodyLimit 13107200
SecRequestBodyNoFilesLimit 131072

# Block requests without Content-Type for POST/PUT/PATCH
SecRule REQUEST_METHOD "^(?:POST|PUT|PATCH)$" \
  "id:1001,\
  phase:1,\
  deny,\
  status:400,\
  msg:'Missing Content-Type header',\
  chain"
  SecRule &REQUEST_HEADERS:Content-Type "@eq 0"

# Block unexpected query parameters on specific paths
SecRule REQUEST_URI "^/api/v1/users" \
  "id:1002,\
  phase:1,\
  deny,\
  status:400,\
  msg:'Unexpected query parameter',\
  chain"
  SecRule QUERY_STRING "(?!(page=|limit=))" \
    "chain"
    SecRule QUERY_STRING ".+"

# Rate limiting via Coraza plugin
# Requires coraza-plugin-ratelimit
```

This configuration activates the OWASP CRS, inspects both request and response bodies, and adds custom rules that enforce API-specific policies like requiring `Content-Type` headers on mutating requests and blocking unexpected query parameters.

### Why Choose Coraza

Coraza is the right choice when you need deep inspection capabilities powered by the OWASP rule set. It catches a wide range of attack patterns out of the box and allows fine-grained customization through SecLang rules. The Go implementation provides better performance than traditional ModSecurity while maintaining full compatibility.

## Envoy Proxy: Cloud-Native API Security

[Envoy Proxy](https://www.envoyproxy.io/) is a cloud-native, high-performance edge and service proxy originally built by Lyft. While not an API firewall in the traditional sense, Envoy's extensible filter chain architecture makes it a powerful platform for building custom API security policies.

### Key Security Features

- **External authentication** — delegate auth to an external service (OAuth, OIDC, custom)
- **JWT authentication filter** — validate JWTs natively without external services
- **Rate limiting service** — centralized rate limiting with configurable quotas
- **Lua scripting** — write custom security logic in Lua at request time
- **WASM filters** — deploy WebAssembly-based security extensions
- **TLS termination** — mTLS, certificate validation, and cipher suite control
- **Circuit breaking** — protect backends from overload and cascading failures
- **gRPC support** — first-class support for gRPC API security

### Docker Compose Configuration

Envoy requires a YAML configuration file (`envoy.yaml`) that defines listeners, clusters, and filters.

```yaml
version: '3.8'

services:
  envoy:
    image: envoyproxy/envoy:v1.32-latest
    container_name: envoy-api-firewall
    ports:
      - "8080:8080"
      - "8443:8443"
    volumes:
      - ./envoy.yaml:/etc/envoy/envoy.yaml:ro
      - ./certs:/etc/envoy/certs:ro
    restart: unless-stopped
    command: ["-c", "/etc/envoy/envoy.yaml", "--log-level", "info"]
```

An `envoy.yaml` configuration with API security filters:

```yaml
admin:
  address:
    socket_address:
      address: 127.0.0.1
      port_value: 9901

static_resources:
  listeners:
    - name: api_listener
      address:
        socket_address:
          address: 0.0.0.0
          port_value: 8080
      filter_chains:
        - filters:
            - name: envoy.filters.network.http_connection_manager
              typed_config:
                "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
                stat_prefix: api_firewall
                access_log:
                  - name: envoy.access_loggers.stdout
                    typed_config:
                      "@type": type.googleapis.com/envoy.extensions.access_loggers.stream.v3.StdoutAccessLog
                http_filters:
                  - name: envoy.filters.http.jwt_authn
                    typed_config:
                      "@type": type.googleapis.com/envoy.extensions.filters.http.jwt_authn.v3.JwtAuthentication
                      providers:
                        api_provider:
                          issuer: "https://auth.your-domain.com"
                          remote_jwks:
                            http_uri:
                              uri: "http://auth-service:8080/.well-known/jwks.json"
                              cluster: auth_cluster
                              timeout: 5s
                            cache_duration:
                              seconds: 300
                      rules:
                        - match:
                            prefix: "/api/"
                          requires:
                            provider_name: api_provider
                  - name: envoy.filters.http.local_ratelimit
                    typed_config:
                      "@type": type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
                      stat_prefix: http_local_rate_limiter
                      token_bucket:
                        max_tokens: 100
                        tokens_per_fill: 50
                        fill_interval: 60s
                  - name: envoy.filters.http.router
                    typed_config:
                      "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
                route_config:
                  name: local_route
                  virtual_hosts:
                    - name: api_backend
                      domains: ["*"]
                      routes:
                        - match:
                            prefix: "/api/"
                          route:
                            cluster: api_backend
  clusters:
    - name: api_backend
      connect_timeout: 5s
      type: STRICT_DNS
      lb_policy: ROUND_ROBIN
      load_assignment:
        cluster_name: api_backend
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    socket_address:
                      address: your-backend-service
                      port_value: 3000
    - name: auth_cluster
      connect_timeout: 5s
      type: STRICT_DNS
      lb_policy: ROUND_ROBIN
      load_assignment:
        cluster_name: auth_cluster
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    socket_address:
                      address: auth-service
                      port_value: 8080
```

This configuration chains JWT authentication and local rate limiting as HTTP filters before routing requests to the backend. The JWT filter validates tokens against a remote JWKS endpoint, caching keys for 5 minutes. The rate limiter allows 50 tokens per 60-second window with a maximum burst of 100.

### Why Choose Envoy

Envoy excels when you need a programmable, extensible security layer that integrates with a broader service mesh or microservices architecture. The xDS configuration protocol enables dynamic updates without restarts, and the WASM filter API allows you to deploy custom security logic without recompiling the proxy.

## Comparison Summary

| Criteria | KrakenD | Coraza WAF | Envoy Proxy |
|---|---|---|---|
| **Best For** | API-first security | OWASP rule-based protection | Extensible proxy security |
| **Setup Complexity** | Low — single JSON config | Medium — rule file management | High — YAML + filter chain |
| **Schema Validation** | Strong — OpenAPI native | Via custom rules | Via WASM/Lua |
| **Rate Limiting** | Token bucket (built-in) | Via rules (external plugin) | Local + global service |
| **OWASP CRS** | No | Yes (full v4.x support) | Via Coraza filter |
| **Performance** | 50K+ req/s (Go) | 20K+ req/s (Go) | 100K+ req/s (C++) |
| **Community** | Growing | Active (OWASP backed) | Very large (CNCF) |
| **Enterprise Use** | Proven at scale | ModSecurity replacement | Industry standard |

### When to Use Each Tool

**Choose KrakenD** if you want a simple, declarative API gateway that handles validation, rate limiting, and JWT verification out of the box. Its single-file configuration model makes it easy to version-control and deploy. It is the fastest path to a secure API gateway for teams that want to define their security posture in configuration rather than code.

**Choose Coraza WAF** if you need deep, rule-based inspection powered by the OWASP Core Rule Set. It catches injection attacks, path traversal, and other common threats automatically. The SecLang compatibility means you can reuse decades of ModSecurity rule development. This is the best option when regulatory compliance requires WAF-level protection.

**Choose Envoy Proxy** if you are building a service mesh or need a programmable security layer that integrates with existing infrastructure. The xDS protocol, WASM filters, and Lua scripting give you unlimited customization possibilities. It is the most complex to configure but also the most powerful.

## Deployment Best Practices

1. **Always enable TLS termination** — even behind a load balancer, terminate TLS at the API firewall to inspect encrypted traffic.
2. **Use strict input validation** — reject requests with unexpected headers, query parameters, or body fields. This prevents parameter pollution and mass assignment attacks.
3. **Implement layered rate limiting** — combine per-endpoint limits (KrakenD) with global limits (Envoy) and abuse detection (Coraza CRS).
4. **Monitor and log** — send access logs to a centralized logging system. Alert on elevated 403/429 response rates.
5. **Keep rule sets updated** — OWASP CRS releases new versions regularly. Automate rule updates to stay protected against emerging threats.
6. **Test your policies** — use tools like OWASP ZAP to verify that your API firewall correctly blocks malicious requests without disrupting legitimate traffic.

## FAQ

### What is the difference between an API firewall and a traditional WAF?

A traditional WAF (Web Application Firewall) operates at the HTTP layer, inspecting requests for known attack signatures like SQL injection and cross-site scripting. An API firewall operates at a higher level of abstraction — it understands your API's structure (endpoints, parameters, schemas) and validates that every request conforms to your API specification. While a WAF catches known attack patterns, an API firewall enforces a whitelist of allowed behavior, rejecting anything unexpected by default.

### Can I use Coraza WAF to protect REST APIs specifically?

Yes. Coraza supports SecLang rules that can target specific URL paths, HTTP methods, and query parameters. You can write rules that validate Content-Type headers for JSON APIs, restrict allowed HTTP methods per endpoint, and inspect JSON request bodies for unexpected fields. The OWASP Core Rule Set also includes rules that detect API-specific attacks like JSON injection and XML external entity (XXE) attacks.

### Does KrakenD support OpenAPI specification validation?

Yes. KrakenD can integrate with your OpenAPI (Swagger) specification to validate incoming requests against defined schemas. When you define your endpoints in `krakend.json`, you can specify exactly which headers, query parameters, and request body fields are allowed. Any request that includes unexpected parameters is rejected with a 400 Bad Request response. The Enterprise Edition adds full OpenAPI schema validation, but the Community Edition covers the most common use cases through its declarative endpoint definitions.

### How does Envoy compare to KrakenD for API security?

Envoy is a general-purpose proxy that can be extended with security filters, while KrakenD is a purpose-built API gateway with security features integrated by default. Envoy offers more flexibility (WASM filters, Lua scripting, xDS dynamic configuration) but requires significantly more configuration effort. KrakenD provides a simpler, declarative approach where security policies are defined in a single JSON file. Choose Envoy if you need deep customization or are already using it as part of a service mesh. Choose KrakenD if you want API security that works out of the box.

### Is it possible to run multiple API firewalls together?

Absolutely. A common architecture places Coraza WAF at the edge to catch broad threats (OWASP CRS), followed by KrakenD or Envoy for API-specific validation and rate limiting. This defense-in-depth approach ensures that even if one layer misses a threat, another catches it. For example, Coraza can block SQL injection attempts while KrakenD rejects requests with unexpected parameters, and Envoy enforces JWT authentication.

### What are the performance implications of adding an API firewall?

All three tools are designed for high performance. KrakenD's stateless Go architecture adds minimal latency (typically under 1ms). Coraza WAF adds slightly more overhead due to rule evaluation (2-5ms depending on rule set complexity). Envoy's C++ implementation is the fastest raw proxy but complex filter chains can add latency. In practice, the security benefits far outweigh the sub-millisecond latency increase for most applications.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "KrakenD vs Coraza vs Envoy: Best Self-Hosted API Firewall 2026",
  "description": "Compare KrakenD, Coraza WAF, and Envoy Proxy as self-hosted API firewall solutions. Practical deployment guides, Docker configs, and feature comparison for protecting your APIs in 2026.",
  "datePublished": "2026-04-26",
  "dateModified": "2026-04-26",
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
