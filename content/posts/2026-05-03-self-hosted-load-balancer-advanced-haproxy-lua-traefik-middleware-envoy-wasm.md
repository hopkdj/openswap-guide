---
title: "Self-Hosted Load Balancer Advanced Features: HAProxy Lua vs Traefik Middleware vs Envoy Wasm Filters (2026)"
date: 2026-05-03T22:30:00+00:00
tags: ["load-balancer", "proxy", "infrastructure", "docker", "networking"]
draft: false
---

Modern load balancers go far beyond simple round-robin traffic distribution. HAProxy, Traefik, and Envoy each offer powerful extension mechanisms that let you customize request processing, implement custom authentication, transform payloads, and build sophisticated traffic routing logic. This guide compares the advanced extensibility features of these three leading self-hosted load balancers.

## Overview Comparison

| Feature | HAProxy (Lua) | Traefik (Middleware) | Envoy (Wasm) |
|---------|--------------|---------------------|--------------|
| Extension Language | Lua | Go/Plugins | Wasm (any language) |
| Hot Reload | Yes | Yes | Yes |
| Custom Auth | Lua scripts | ForwardAuth middleware | Wasm auth filters |
| Request Transform | Lua body manipulation | Chain middleware | Wasm body transforms |
| Rate Limiting | Built-in + Lua | Middleware plugin | Wasm + built-in |
| Observability | Lua logging | Access logs + tracing | Wasm telemetry |
| Learning Curve | Moderate | Low | Steep |
| Community Plugins | Limited | Extensive | Growing rapidly |
| Performance Impact | Low | Low-Moderate | Low |

## HAProxy Lua Scripting

HAProxy has supported Lua scripting since version 1.8, allowing you to execute custom logic at various hook points in the request/response lifecycle. Lua scripts run inside HAProxy's event loop, making them extremely fast.

### Key Extension Points

- **Action hooks**: Run custom logic on HTTP request/response
- **Service hooks**: Create custom health check services
- **Task hooks**: Run background periodic tasks
- **Converter hooks**: Transform data during processing

### Docker Compose with Lua Scripts

```yaml
version: "3.8"
services:
  haproxy:
    image: haproxy:2.9-alpine
    container_name: haproxy
    ports:
      - "80:80"
      - "8404:8404"
    volumes:
      - ./haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
      - ./scripts:/usr/local/etc/haproxy/scripts:ro
      - ./stats:/usr/local/etc/haproxy/stats
    restart: unless-stopped
```

### Example: Custom Authentication with Lua

```lua
-- custom-auth.lua
core.register_action("jwt-auth", {"http-req"}, function(txn)
    local auth = txn.http:req_get_headers()["authorization"]
    if not auth or not auth[0] then
        txn:set_var("tx.auth_status", "missing")
        return
    end
    local token = string.sub(auth[0], 8)
    local valid = verify_token(token)
    if valid then
        txn:set_var("tx.auth_status", "ok")
    else
        txn:set_var("tx.auth_status", "invalid")
    end
end)

function verify_token(token)
    -- JWT validation logic
    return true
end
```

```haproxy
frontend http-in
    bind *:80
    lua-load /usr/local/etc/haproxy/scripts/custom-auth.lua
    http-request lua.jwt-auth
    http-request deny if { var(tx.auth_status) -m str invalid }
    http-request deny if { var(tx.auth_status) -m str missing }
    default_backend app_servers
```

## Traefik Middleware

Traefik takes a declarative approach to extensibility through its middleware system. Middlewares are configured as Kubernetes CRDs, Docker labels, or YAML files, and can be chained together to create complex request processing pipelines.

### Key Middleware Types

- **ForwardAuth**: External authentication via HTTP call
- **RateLimit**: Token bucket rate limiting
- **StripPrefix/Rewrite**: URL path manipulation
- **Headers**: Add/remove/modify headers
- **CircuitBreaker**: Automatic backend health management
- **Plugins**: Custom Go plugins from the Traefik Plugin Catalog

### Docker Compose with Middleware

```yaml
version: "3.8"
services:
  traefik:
    image: traefik:v3.0
    container_name: traefik
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./traefik.yml:/etc/traefik/traefik.yml:ro
      - ./dynamic:/etc/traefik/dynamic:ro
    command:
      - --api.dashboard=true
      - --providers.docker
      - --providers.file.directory=/etc/traefik/dynamic
    restart: unless-stopped

  whoami:
    image: traefik/whoami
    labels:
      - "traefik.http.routers.whoami.rule=Host(`app.example.com`)"
      - "traefik.http.routers.whoami.middlewares=auth-ratelimit"
      - "traefik.http.middlewares.auth-ratelimit.chain.middlewares=auth,limit"
      - "traefik.http.middlewares.auth.forwardauth.address=http://auth:8080/validate"
      - "traefik.http.middlewares.limit.ratelimit.average=100"
      - "traefik.http.middlewares.limit.ratelimit.burst=50"
```

## Envoy Wasm Filters

Envoy supports WebAssembly (Wasm) filters that run sandboxed code inside the proxy process. This is the most flexible extension mechanism — you can write filters in any language that compiles to Wasm (Rust, C++, AssemblyScript, TinyGo).

### Key Advantages

- Language-agnostic: Write filters in Rust, C++, Go, or AssemblyScript
- Sandboxed execution: Wasm provides strong isolation from the host
- Hot reloading: Filters can be updated without restarting Envoy
- Rich API: Full access to request/response bodies, headers, and metadata
- Growing ecosystem: Proxy-Wasm SDK and growing plugin catalog

### Docker Compose with Wasm Filters

```yaml
version: "3.8"
services:
  envoy:
    image: envoyproxy/envoy:v1.29
    container_name: envoy
    ports:
      - "80:80"
      - "9901:9901"
    volumes:
      - ./envoy.yaml:/etc/envoy/envoy.yaml:ro
      - ./wasm-filters:/etc/envoy/wasm-filters:ro
    restart: unless-stopped
```

### Example: Wasm Rate Limiter in Rust

```rust
// Using proxy-wasm Rust SDK
use proxy_wasm::traits::*;
use proxy_wasm::types::*;

struct RateLimitFilter {
    count: u32,
}

impl HttpContext for RateLimitFilter {
    fn on_http_request_headers(&mut self, _num_headers: usize) -> Action {
        self.count += 1;
        if self.count > 100 {
            self.send_http_response(
                429,
                vec![("x-rate-limit", "exceeded")],
                Some(b"Rate limit exceeded"),
            );
            return Action::Pause;
        }
        Action::Continue
    }
}
```

## Why Use Advanced Load Balancer Features?

**Custom Authentication:** Instead of relying on a separate API gateway, you can implement JWT validation, OAuth2 flows, or mTLS directly in your load balancer. This reduces latency and simplifies architecture. For organizations managing multiple authentication systems, this approach complements [self-hosted IAM solutions](../zitadel-vs-ory-vs-keycloak-self-hosted-iam-guide/) by providing an additional enforcement layer at the edge.

**Traffic Shaping:** Implement canary deployments, A/B testing, and blue-green deployments through custom routing logic. This is especially valuable for teams running [CI/CD pipelines](../ci-cd-orchestration-platforms/) that need fine-grained traffic control during deployments.

**Request/Response Transformation:** Modify headers, rewrite URLs, or transform payloads without deploying additional microservices. This reduces the number of services in your architecture and improves maintainability.

**Observability:** Inject custom metrics, trace spans, and log enrichment at the load balancer level. This provides visibility into traffic patterns before requests reach your application servers.

## Performance Impact

| Extension Type | Latency Overhead | Throughput Impact |
|---------------|-----------------|-------------------|
| HAProxy Lua | < 0.1ms per request | Negligible |
| Traefik Middleware | 0.1-0.5ms (local), 5-20ms (ForwardAuth) | Low |
| Envoy Wasm | 0.05-0.2ms per request | Negligible |

## Choosing the Right Approach

- **Choose HAProxy Lua** if you already use HAProxy and need lightweight, fast custom logic with minimal overhead.
- **Choose Traefik Middleware** if you want a declarative, configuration-driven approach with a rich catalog of pre-built plugins.
- **Choose Envoy Wasm** if you need maximum flexibility, language-agnostic development, or are building complex traffic manipulation logic.

## FAQ

### Can I use Lua scripts in HAProxy without recompiling?
Yes. Lua scripts are loaded at runtime via the `lua-load` directive in your configuration. You can update scripts and reload HAProxy gracefully without dropping connections.

### Do Traefik middlewares require coding?
No. Most built-in middlewares (rate limiting, header manipulation, URL rewriting) are configured entirely through YAML labels or Kubernetes CRDs. Only custom plugins require Go development.

### What languages can I use for Envoy Wasm filters?
Any language that compiles to WebAssembly. The most common choices are Rust (via proxy-wasm-rust-sdk), C++ (via proxy-wasm-cpp-sdk), and TinyGo (via proxy-wasm-go-sdk). AssemblyScript is also supported for simpler filters.

### Can these extensions handle SSL/TLS termination?
HAProxy and Envoy can inspect and modify traffic after TLS termination. Traefik handles TLS natively and middleware operates on decrypted HTTP traffic. For comprehensive TLS management, you can integrate with certificate automation tools.

### How do I debug custom extensions?
HAProxy provides Lua logging via `core.log()`. Traefik middleware logs appear in the Traefik access logs. Envoy Wasm filters can use the proxy-wasm logging API, and Envoy's admin interface provides detailed filter chain visualization.

### Are these extensions production-ready?
Yes. HAProxy Lua has been production-ready since v1.8. Traefik middleware is core to the product. Envoy Wasm is used in production by Istio service mesh and many large-scale deployments. For teams evaluating [API gateway options](../self-hosted-api-gateway-apisix-kong-tyk-guide/), these load balancer extensions can sometimes replace a full gateway for simpler use cases.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Load Balancer Advanced Features: HAProxy Lua vs Traefik Middleware vs Envoy Wasm Filters",
  "description": "Compare advanced extensibility features of HAProxy Lua scripting, Traefik Middleware, and Envoy Wasm filters for self-hosted load balancers.",
  "datePublished": "2026-05-03",
  "dateModified": "2026-05-03",
  "author": {"@type": "Organization", "name": "OpenSwap Guide"},
  "publisher": {"@type": "Organization", "name": "OpenSwap Guide", "logo": {"@type": "ImageObject", "url": "https://hopkdj.github.io/openswap-guide/logo.png"}}
}
</script>
