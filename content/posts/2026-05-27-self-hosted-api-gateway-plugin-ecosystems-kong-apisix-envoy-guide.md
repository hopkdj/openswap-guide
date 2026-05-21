---
title: "Self-Hosted API Gateway Plugin Ecosystems: Kong vs APISIX vs Envoy (2026)"
date: "2026-05-27"
tags: ["api-gateway", "kubernetes", "networking", "microservices", "plugins"]
draft: false
---

API gateways are the front door to your microservices architecture. But the real power lies not in the gateway itself — it's in the plugin ecosystem. Plugins handle authentication, rate limiting, request transformation, logging, and dozens of other cross-cutting concerns without touching your application code.

This guide compares the plugin ecosystems of three leading open-source API gateways: **Kong** (Lua-based plugins), **Apache APISIX** (Lua + Wasm plugins), and **Envoy** (Wasm filters + Lua). We'll examine plugin development, deployment patterns, and provide production-ready configurations.

For a broader look at API gateway features, see our [API lifecycle management guide](../2026-04-26-self-hosted-api-lifecycle-management-kong-apisix-tyk-gravitee-krakend-guide/) and [API gateway controller comparison](../2026-05-21-self-hosted-envoy-api-gateway-controllers-envoy-gateway-contour-gloo-guide/).

## Why Plugin Ecosystems Matter

Building an API gateway from scratch means implementing authentication, rate limiting, request logging, CORS handling, circuit breaking, and more — for every service. Plugin ecosystems solve this by providing modular, reusable components that apply to routes, services, or consumers globally.

A mature plugin ecosystem means:
- **Zero-code cross-cutting concerns** — Add JWT authentication or rate limiting with a configuration change, not code changes
- **Community-vetted security** — Authentication and authorization plugins are battle-tested across thousands of deployments
- **Hot-reloadable extensions** — Deploy new plugins without restarting the gateway
- **Observability by default** — Request logging, metrics, and tracing plugins integrate with your monitoring stack

## Comparison: Plugin Ecosystems at a Glance

| Feature | Kong Plugins | APISIX Plugins | Envoy Filters/Wasm |
|---------|-------------|----------------|-------------------|
| **Plugin language** | Lua (OpenResty) | Lua + Wasm + Java/Go | Wasm (any language) + Lua |
| **Built-in plugins** | 100+ official | 80+ official | 30+ built-in filters |
| **Custom plugin dev** | Lua SDK | Lua SDK + Runner SDK | Wasm SDK (Rust/C++/Go) |
| **Hot reload** | Yes (cluster sync) | Yes (etcd hot reload) | Yes (xDS dynamic) |
| **Plugin ordering** | Priority-based | Priority-based | Filter chain order |
| **Admin API** | REST API (port 8001) | REST API (port 9180) | xDS protocol / admin |
| **Plugin storage** | PostgreSQL / declarative | etcd (distributed) | xDS control plane |
| **Wasm support** | No (planned) | Yes (native) | Yes (native) |
| **GitHub stars** | 43,400+ | 16,600+ | 28,200+ |
| **Best for** | Enterprise API mgmt | Cloud-native, multi-language | Service mesh, proxy extensibility |

## Kong Plugins: The Most Mature Ecosystem

Kong has the largest plugin ecosystem in the open-source API gateway space. Built on OpenResty (NGINX + LuaJIT), Kong plugins run as Lua modules with access to the full request/response lifecycle.

### Installing a Kong Plugin

```yaml
# docker-compose.yml for Kong with custom plugin
version: "3.8"
services:
  kong:
    image: kong:3.6
    environment:
      KONG_DATABASE: postgres
      KONG_PG_HOST: postgres
      KONG_PG_USER: kong
      KONG_PG_PASSWORD: kong
      KONG_PROXY_ACCESS_LOG: /dev/stdout
      KONG_ADMIN_ACCESS_LOG: /dev/stdout
      KONG_PROXY_ERROR_LOG: /dev/stderr
      KONG_ADMIN_ERROR_LOG: /dev/stderr
      KONG_ADMIN_LISTEN: 0.0.0.0:8001
      KONG_PLUGINS: bundled,my-custom-plugin
    ports:
      - "8000:8000"
      - "8443:8443"
      - "8001:8001"
      - "8444:8444"
    volumes:
      - ./plugins:/usr/local/share/lua/5.1/kong/plugins:ro
    depends_on:
      - postgres

  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: kong
      POSTGRES_PASSWORD: kong
      POSTGRES_DB: kong
    volumes:
      - kong_data:/var/lib/postgresql/data

volumes:
  kong_data:
```

### Writing a Custom Kong Plugin (Lua)

```lua
-- /usr/local/share/lua/5.1/kong/plugins/my-custom-plugin/handler.lua
local BasePlugin = require "kong.plugins.base_plugin"

local MyPluginHandler = BasePlugin:extend()
MyPluginHandler.PRIORITY = 1000
MyPluginHandler.VERSION = "1.0.0"

function MyPluginHandler:new()
  MyPluginHandler.super.new(self, "my-custom-plugin")
end

function MyPluginHandler:access(config)
  MyPluginHandler.super.access(self)
  
  -- Add custom header
  kong.service.request.set_header("X-Custom-Plugin", "active")
  
  -- Rate limit by custom logic
  local client_ip = kong.client.get_ip()
  kong.log.debug("Request from: " .. client_ip)
end

return MyPluginHandler
```

### Popular Kong Plugins

| Plugin | Purpose | Configuration |
|--------|---------|--------------|
| `rate-limiting` | Request rate limiting by IP/consumer | `second`, `minute`, `hour`, `policy` |
| `jwt` | JWT token validation | `uri_param_names`, `claims_to_verify` |
| `key-auth` | API key authentication | `key_names`, `hide_credentials` |
| `cors` | Cross-Origin Resource Sharing | `origins`, `methods`, `headers` |
| `request-transformer` | Modify request/response | `add.headers`, `remove.querystring` |
| `prometheus` | Metrics export | Automatic on `/metrics` endpoint |
| `zipkin` | Distributed tracing | `endpoint`, `sample_ratio` |
| `ip-restriction` | Allow/deny by IP | `allow`, `deny` |

## Apache APISIX Plugins: Cloud-Native and Multi-Language

APISIX uses etcd as its configuration store, enabling true hot-reload across cluster nodes without restarts. Its plugin ecosystem supports Lua (native), WebAssembly (any language), and external runners (Java, Go, Python, Node.js).

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  apisix:
    image: apache/apisix:3.9.0
    restart: always
    ports:
      - "9080:9080"
      - "9443:9443"
      - "9180:9180"
    volumes:
      - ./apisix.yaml:/usr/local/apisix/conf/apisix.yaml:ro
    depends_on:
      - etcd

  etcd:
    image: bitnami/etcd:3.5
    restart: always
    environment:
      ETCD_ENABLE_V2: "true"
      ALLOW_NONE_AUTHENTICATION: "yes"
      ETCD_ADVERTISE_CLIENT_URLS: "http://etcd:2379"
      ETCD_LISTEN_CLIENT_URLS: "http://0.0.0.0:2379"
    volumes:
      - etcd_data:/bitnami/etcd

volumes:
  etcd_data:
    driver: local
```

### Enabling Plugins via APISIX Admin API

```bash
# Enable rate-limiting on a route
curl http://127.0.0.1:9180/apisix/admin/routes/1   -H 'X-API-KEY: edd1c9f034335f136f87ad84b625c8f1'   -X PUT -d '
{
  "uri": "/api/*",
  "upstream": {
    "type": "roundrobin",
    "nodes": {
      "127.0.0.1:8080": 1
    }
  },
  "plugins": {
    "rate-limiting": {
      "rate_type": "client_ip",
      "rate": 100,
      "window_size": 60,
      "key": "remote_addr",
      "rejected_code": 429
    },
    "cors": {
      "allow_origins": "https://example.com",
      "allow_methods": "GET,POST,PUT,DELETE",
      "allow_headers": "Authorization,Content-Type",
      "max_age": 3600
    },
    "prometheus": {}
  }
}'
```

### APISIX External Plugin Runner (Go Example)

APISIX supports external plugin runners that communicate over gRPC, allowing plugins in any language:

```go
// Go plugin for APISIX external runner
package main

import (
    "github.com/api7/ext-plugin-go"
    pkgHTTP "github.com/api7/ext-plugin-go/pkg/http"
)

type MyPlugin struct{}

func (p *MyPlugin) Filter(conf []byte, r pkgHTTP.Request) *pkgHTTP.Response {
    // Custom authentication logic
    token := r.GetHeader("X-Custom-Token")
    if token == "" {
        return &pkgHTTP.Response{
            StatusCode: 401,
            Body:       []byte("missing token"),
        }
    }
    return nil // Pass through
}

func main() {
    extPlugin.PluginRunner.Run(extPlugin.NewPluginRunner(
        extPlugin.RegisterFilter(&MyPlugin{}),
    ))
}
```

## Envoy WASM Filters: Language-Agnostic Extensibility

Envoy's WebAssembly (Wasm) filter support allows you to write proxy extensions in Rust, C++, Go, or AssemblyScript — compiled to Wasm and loaded dynamically at runtime. This is the most flexible extension model of the three gateways.

### Docker Compose with Envoy WASM

```yaml
version: "3.8"
services:
  envoy:
    image: envoyproxy/envoy:v1.30
    volumes:
      - ./envoy.yaml:/etc/envoy/envoy.yaml:ro
      - ./wasm-filters:/etc/envoy/wasm-filters:ro
    ports:
      - "8080:8080"
      - "8001:8001"

  wasm-compiler:
    image: rust:1.75
    volumes:
      - ./wasm-filters/src:/app:ro
    command: cargo build --target wasm32-wasi --release
```

### Envoy Configuration with WASM Filter

```yaml
# envoy.yaml
static_resources:
  listeners:
  - name: main_listener
    address:
      socket_address:
        address: 0.0.0.0
        port_value: 8080
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: ingress_http
          http_filters:
          - name: envoy.filters.http.wasm
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.wasm.v3.Wasm
              config:
                name: "custom_auth"
                root_id: "custom_auth"
                vm_config:
                  runtime: "envoy.wasm.runtime.v8"
                  code:
                    local:
                      filename: "/etc/envoy/wasm-filters/custom_auth.wasm"
          - name: envoy.filters.http.router
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  clusters:
  - name: backend_service
    connect_timeout: 5s
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: backend_service
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: backend
                port_value: 8080
```

### WASM Plugin Development (Rust)

```rust
// Custom WASM filter in Rust
use proxy_wasm::traits::*;
use proxy_wasm::types::*;

struct MyAuthFilter;

impl HttpContext for MyAuthFilter {
    fn on_http_request_headers(&mut self, _num_headers: usize, _end_of_stream: bool) -> Action {
        if let Some(token) = self.get_http_request_header("Authorization") {
            if token.starts_with("Bearer valid-") {
                return Action::Continue;
            }
        }
        self.send_http_response(
            401,
            vec![("WWW-Authenticate", "Bearer")],
            Some(b"Unauthorized"),
        );
        Action::Pause
    }
}

impl Context for MyAuthFilter {}

proxy_wasm::main! {{
    proxy_wasm::set_log_level(LogLevel::Trace);
    proxy_wasm::set_http_context(|_, _| -> Box<dyn HttpContext> {
        Box::new(MyAuthFilter)
    });
}}
```

## Plugin Development Comparison

| Aspect | Kong | APISIX | Envoy |
|--------|------|--------|-------|
| **Learning curve** | Low (Lua) | Low (Lua) / Medium (Wasm) | Medium-High (Rust/C++ Wasm) |
| **Hot reload** | Via Kong Manager or Admin API | Instant (etcd watches) | Via xDS update |
| **Testing** | Lua unit tests (busted) | Lua tests + APISIX test framework | Wasm test harness |
| **Distribution** | LuaRocks / Kong Hub | APISIX Plugin Hub | Wasm Hub / OCI registry |
| **Performance impact** | ~1-5% per plugin | ~1-3% per plugin (Lua) / ~5-10% (Wasm) | ~2-8% per Wasm filter |
| **Debugging** | kong.log.*, Admin API logs | etcd config inspection, admin API | Envoy admin `/stats`, `/clusters` |

## Choosing the Right Plugin Ecosystem

**For enterprise API management:** Kong has the most mature plugin ecosystem with 100+ official plugins, commercial support options, and Kong Hub for community plugins. If you need rate limiting, JWT auth, OAuth2, LDAP, and request transformation out of the box, Kong is the safest choice.

**For cloud-native, multi-language teams:** APISIX supports Lua plugins natively and external runners in Go, Java, Python, and Node.js. The etcd-backed hot-reload means zero-downtime plugin deployment. Choose APISIX if your team wants to write plugins in languages other than Lua.

**For service mesh and deep proxy customization:** Envoy WASM filters offer the most flexibility. Any language that compiles to Wasm can write proxy extensions. Choose Envoy if you need fine-grained control over the proxy pipeline or are already using Istio (which uses Envoy as its data plane).

For additional reading on gateway features, see our [rate limiting comparison](../2026-04-28-nginx-vs-caddy-vs-envoy-ratelimit-self-hosted-rate-limiting-guide/) and [circuit breaker patterns](../2026-05-01-self-hosted-circuit-breaker-envoy-haproxy-linkerd-fault-tolerance-guide/).

## FAQ

### Which API gateway has the easiest plugin development experience?

Kong has the lowest barrier to entry. Lua is a simple scripting language, and Kong's plugin SDK provides clear lifecycle hooks (`access`, `header_filter`, `body_filter`, `log`). A basic Kong plugin can be written in under 20 lines of Lua. APISIX Lua plugins are similarly straightforward. Envoy WASM filters require knowledge of Rust/C++/Go and the Wasm compilation toolchain, making them more complex but also more powerful.

### Can I mix plugins from different gateways?

No. Plugins are tightly coupled to their gateway's architecture. Kong plugins use the OpenResty Lua API, APISIX plugins use the APISIX Lua SDK, and Envoy filters use the Envoy Wasm SDK. However, you can run multiple gateways in your infrastructure — for example, Kong at the edge for API management and Envoy as a sidecar proxy for service mesh functionality.

### Do plugins impact gateway performance?

Yes, but typically minimally. Lua-based plugins (Kong, APISIX) add 1-5% latency per plugin due to LuaJIT's excellent performance. WASM-based plugins (Envoy, APISIX Wasm) add 2-10% depending on the complexity of the Wasm module. For most production workloads, 5-10 plugins add less than 20ms of total latency. Monitor the gateway's built-in metrics to track plugin overhead.

### How do I deploy custom plugins in production?

**Kong:** Place the Lua plugin code in `/usr/local/share/lua/5.1/kong/plugins/` on all nodes, add the plugin name to `KONG_PLUGINS` environment variable, and restart. Kong 3.x supports declarative configuration (YAML) for plugin deployment without database dependencies.

**APISIX:** Upload the plugin via the Admin API or place it in the plugin directory. Since APISIX uses etcd, plugin configuration propagates to all nodes instantly without restarts.

**Envoy:** Compile the Wasm module and reference it in the Envoy configuration. With xDS, you can dynamically update the Wasm filter configuration without restarting Envoy.

### Can I disable plugins for specific routes?

Yes. All three gateways support route-level plugin configuration. In Kong, you configure plugins per-route via the Admin API. In APISIX, plugins are part of the route definition JSON. In Envoy, filter chains are scoped per-route or per-listener.

### What happens when a plugin crashes?

**Kong:** A Lua plugin error returns a 500 response and logs the error. The gateway continues processing other requests. Use `kong.log.err()` for error handling.

**APISIX:** Plugin errors are caught and logged. The request fails with 500, but the gateway remains operational. APISIX's etcd-based configuration means a bad plugin can be removed instantly.

**Envoy:** WASM filter errors are isolated. If a Wasm module crashes, Envoy can either fail-open (skip the filter) or fail-closed (return an error), depending on the `fail_open` configuration.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted API Gateway Plugin Ecosystems: Kong vs APISIX vs Envoy (2026)",
  "description": "Compare plugin ecosystems of Kong, Apache APISIX, and Envoy — with Lua and Wasm plugin development, Docker Compose configs, and production deployment patterns.",
  "datePublished": "2026-05-27",
  "dateModified": "2026-05-27",
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
