---
title: "Self-Hosted API Gateway Platforms: Kuma vs Tyk vs Pingora"
date: "2026-05-08"
draft: false
tags: ["api-gateway", "service-mesh", "proxy", "kubernetes", "networking"]
---

API gateways sit between clients and your backend services, handling routing, authentication, rate limiting, observability, and traffic management. Self-hosting an API gateway gives you full control over your API infrastructure without vendor lock-in or per-request pricing.

In this guide, we compare three distinct approaches to API gateway infrastructure: **Kuma** (service mesh with multi-zone support), **Tyk** (open-source API gateway), and **Pingora** (Cloudflare's proxy framework for building custom gateways).

## Comparison Overview

| Feature | Kuma (Kong Mesh) | Tyk | Pingora |
|---------|------------------|-----|---------|
| **GitHub Stars** | 4,000+ | 10,700+ | 26,600+ |
| **Language** | Go (Envoy-based) | Go | Rust |
| **Type** | Service mesh / multi-zone gateway | API gateway | Proxy framework / library |
| **Control Plane** | Yes (built-in) | Yes (Tyk Dashboard) | No (library, not a product) |
| **Data Plane** | Envoy proxy | Custom Go proxy | Custom Rust proxy |
| **Protocol Support** | HTTP, gRPC, TCP, TLS | HTTP, REST, GraphQL, gRPC, TCP | HTTP, TCP, TLS, WebSocket |
| **Rate Limiting** | Yes (Envoy filters) | Yes (built-in) | Custom implementation needed |
| **Authentication** | mTLS, JWT, OIDC | JWT, OIDC, OAuth2, Basic Auth, HMAC | Custom implementation needed |
| **API Key Management** | No | Yes (built-in dashboard) | Custom implementation needed |
| **Plugin System** | Envoy WASM, policies | Go/Python/JS plugins | Rust crates and traits |
| **Multi-zone/Multi-cluster** | Yes (zone ingress/egress) | Via Tyk MDCB | Via custom architecture |
| **Kubernetes Integration** | Yes (CRDs, mesh CR) | Yes (Tyk Operator) | Via custom deployment |
| **Docker Compose** | Yes | Yes | No (library) |
| **License** | Apache 2.0 (OSS), MPL (enterprise) | Apache 2.0 (OSS) | Apache 2.0 |
| **Enterprise Version** | Kong Mesh (commercial) | Tyk Pro (commercial) | N/A (library only) |

## Kuma

**Kuma** is a modern service mesh built on Envoy, designed for multi-zone and multi-cluster deployments. Originally created by Kong, it's now a CNCF Sandbox project. Kuma provides service-to-service communication, traffic management, and security policies across distributed environments.

### Key Features

- **Multi-zone architecture** — connect services across data centers, clouds, and regions
- **Zone ingress/egress** — intelligent cross-zone traffic routing
- **Built-in policies** — traffic routing, retries, timeouts, circuit breaking, fault injection
- **mTLS by default** — automatic certificate management between services
- **Kubernetes-native** — custom resources (Mesh, TrafficRoute, TrafficPermission)
- **Universal control plane** — manages both Kubernetes and VM/bare metal workloads

### Docker Compose Configuration

```yaml
services:
  kuma-control-plane:
    image: kong/kuma-cp:latest
    restart: unless-stopped
    ports:
      - "5681:5681"   # GUI
      - "5682:5682"   # API
      - "5685:5685"   # XDS gRPC
    environment:
      - KUMA_MODE=standalone
      - KUMA_DATABASE_DRIVER=postgres
      - KUMA_STORE_TYPE=postgres
      - KUMA_STORE_POSTGRES_HOST=postgres
      - KUMA_STORE_POSTGRES_PORT=5432
      - KUMA_STORE_POSTGRES_DBNAME=kuma
      - KUMA_STORE_POSTGRES_USER=kuma
      - KUMA_STORE_POSTGRES_PASSWORD=kumapassword
      - KUMA_DP_SERVER_AUTH_TYPE=dp-token
      - KUMA_RUNTIME_KUBERNETES_INJECTOR_ENABLED=true
    depends_on:
      postgres:
        condition: service_healthy

  postgres:
    image: postgres:16
    restart: unless-stopped
    environment:
      - POSTGRES_DB=kuma
      - POSTGRES_USER=kuma
      - POSTGRES_PASSWORD=kumapassword
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U kuma"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

### Defining Traffic Policies

```yaml
# TrafficRoute — split traffic between versions
apiVersion: kuma.io/v1alpha1
kind: TrafficRoute
metadata:
  name: split-traffic
spec:
  selectors:
    - match:
        kuma.io/service: frontend
  conf:
    http:
      - match:
          - prefix: /
        destination:
          kuma.io/service: backend
        weight: 80
      - match:
          - prefix: /
        destination:
          kuma.io/service: backend-v2
        weight: 20
```

### When to Choose Kuma

Choose Kuma when you need a **full service mesh** for microservices communication, especially in multi-cluster or hybrid cloud environments. It's ideal for Kubernetes-first organizations that need mTLS, traffic splitting, and policy enforcement across service boundaries. The Envoy data plane provides enterprise-grade proxy capabilities out of the box.

## Tyk

**Tyk** is a lightweight, open-source API gateway written in Go. It provides a complete API management platform with rate limiting, authentication, analytics, and a developer portal. Unlike Kuma, Tyk focuses on north-south traffic (client-to-service) rather than east-south (service-to-service).

### Key Features

- **Complete API lifecycle** — design, publish, secure, and monitor APIs
- **Rich authentication** — API keys, JWT, OAuth2, OIDC, basic auth, HMAC
- **Rate limiting & quotas** — per-key, per-API, global rate limits
- **Analytics dashboard** — real-time request tracking, latency metrics, error rates
- **Plugin ecosystem** — Go, Python, JavaScript, and Lua plugins
- **GraphQL support** — native GraphQL proxy with schema stitching
- **API versioning** — manage multiple API versions simultaneously

### Docker Compose Configuration

```yaml
services:
  tyk-gateway:
    image: tykio/tyk-gateway:latest
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./tyk.conf:/opt/tyk-gateway/tyk.conf
      - ./apps:/opt/tyk-gateway/apps
    depends_on:
      redis:
        condition: service_healthy

  tyk-dashboard:
    image: tykio/tyk-dashboard:latest
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - TYK_DB_TYPE=redis
      - TYK_DB_HOST=redis
      - TYK_DB_PORT=6379
      - TYK_DB_PASSWORD=tyk_redis_password
    depends_on:
      redis:
        condition: service_healthy

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --requirepass tyk_redis_password
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  redisdata:
```

### Defining an API in Tyk

```json
{
  "name": "My API",
  "api_id": "my-api",
  "org_id": "default",
  "use_keyless": false,
  "auth": {
    "auth_header_name": "Authorization"
  },
  "definition": {
    "location": "header",
    "key": "x-api-version"
  },
  "proxy": {
    "listen_path": "/my-api/",
    "target_url": "http://backend-service:8080/",
    "strip_listen_path": true
  },
  "version_data": {
    "versions": {
      "Default": {
        "name": "Default",
        "use_extended_paths": true,
        "extended_paths": {
          "rate_limit": [{
            "rate": 100,
            "per": 60
          }]
        }
      }
    }
  }
}
```

### When to Choose Tyk

Choose Tyk when you need a **dedicated API gateway** for managing external API access, rate limiting, authentication, and developer experience. It's ideal for organizations exposing APIs to partners or public consumers, where API key management, rate limiting, and analytics are primary requirements. The open-source core provides all essential gateway features without the enterprise pricing of commercial alternatives.

## Pingora

**Pingora** is Cloudflare's open-source Rust framework for building fast, reliable, and evolvable network services. Released in 2024, it powers Cloudflare's own proxy infrastructure handling millions of requests per second. Unlike Kuma and Tyk, Pingora is a **library**, not a ready-to-deploy product — you build your own gateway on top of it.

### Key Features

- **Rust performance** — memory-safe, zero-cost abstractions, high throughput
- **Asynchronous I/O** — tokio-based event loop for maximum concurrency
- **Custom protocols** — build support for any protocol, not just HTTP
- **Hot reload** — zero-downtime configuration and binary updates
- **Production proven** — handles Cloudflare's global traffic volume
- **Extensible architecture** — compose proxy behavior with traits and modules

### Building a Proxy with Pingora

```rust
use pingora::prelude::*;
use pingora::proxy::http_proxy::HttpProxy;
use pingora::proxy::Session;
use pingora::protocols::http::error_responses;
use pingora::upstreams::peer::HttpPeer;
use std::sync::Arc;

struct MyProxy;

#[async_trait]
impl HttpProxy for MyProxy {
    async fn request_body_filter(
        &self,
        session: &mut Session,
        body: &mut Option<bytes::Bytes>,
        _end_of_stream: bool,
    ) -> Result<()> {
        // Custom request filtering logic
        Ok(())
    }

    async fn logging(
        &self,
        session: &mut Session,
        _e: Option<&Error>,
    ) {
        // Custom logging/metrics
        if let Some(resp) = session.response_written() {
            log::info!("{} {}", resp.status, session.req_header().method);
        }
    }
}

fn main() {
    let mut my_server = Server::new(Some(Opt::default())).unwrap();
    my_server.bootstrap();

    let mut http_proxy = http_proxy::HttpProxy::new();
    http_proxy.add_tcp(
        "0.0.0.0:8080",
        Box::new(MyProxy),
        Some(Box::new(HttpPeer::new("backend:8080"))),
    );

    my_server.add_proxy(http_proxy);
    my_server.run_forever();
}
```

### Cargo.toml Dependencies

```toml
[package]
name = "my-gateway"
version = "0.1.0"
edition = "2021"

[dependencies]
pingora = "0.4"
bytes = "1.5"
log = "0.4"
async-trait = "0.1"
tokio = { version = "1", features = ["full"] }
```

### When to Choose Pingora

Choose Pingora when you need to **build a custom proxy or gateway** with specific performance requirements or protocol support that existing products don't provide. It's ideal for teams with Rust expertise who need to handle extreme throughput (100K+ requests/second), implement custom load balancing algorithms, or support non-HTTP protocols. Pingora requires significantly more development effort than Kuma or Tyk but offers unmatched flexibility and performance.

## Choosing the Right API Gateway

| Use Case | Best Choice | Why |
|----------|-------------|-----|
| Multi-cluster service mesh | Kuma | Native multi-zone, mTLS, Envoy data plane |
| Public API management | Tyk | API keys, rate limiting, analytics, developer portal |
| Custom high-performance proxy | Pingora | Rust performance, full control, Cloudflare-proven |
| Kubernetes-first organization | Kuma | Native CRDs, automatic sidecar injection |
| Quick API gateway deployment | Tyk | Ready to deploy with Docker, minimal configuration |
| Building a new gateway product | Pingora | Library-level flexibility, extensible architecture |
| Service-to-service security | Kuma | Built-in mTLS, traffic policies, authorization |
| GraphQL API management | Tyk | Native GraphQL proxy with schema stitching |

## Why Self-Host Your API Gateway?

Self-hosting your API gateway infrastructure provides critical advantages for organizations managing APIs at scale:

**Complete traffic visibility.** When you route API traffic through a self-hosted gateway, you capture every request, response, and latency metric. This data is essential for debugging, performance optimization, and capacity planning. Commercial API gateways often limit analytics retention or charge premium tiers for detailed logging.

**Cost control at scale.** Commercial API gateways typically charge based on request volume, number of APIs, or bandwidth. At millions of requests per day, these costs become substantial. Self-hosted gateways run on your existing infrastructure — the only cost is the compute resources. A single Tyk instance on a 2-core server can handle 10,000+ requests per second.

**No vendor lock-in.** Self-hosted gateways use standard configurations and open APIs. Migrating from one self-hosted gateway to another is a configuration change, not a platform rewrite. Compare that to commercial gateways where your rate limiting rules, authentication policies, and analytics are trapped in their proprietary platform.

**Regulatory compliance.** For organizations in regulated industries (finance, healthcare, government), routing sensitive API traffic through third-party infrastructure can create compliance risks. Self-hosting keeps all API data within your security perimeter, simplifying SOC 2, HIPAA, and PCI DSS audits.

**Custom integration capabilities.** Self-hosted gateways let you integrate with your existing authentication providers, monitoring stacks, and CI/CD pipelines. Tyk's plugin system supports Go, Python, and JavaScript. Kuma's Envoy-based architecture supports WASM plugins. Pingora lets you write custom proxy logic in Rust.

For related reading, see our [API gateway and service mesh comparison](../2026-05-06-self-hosted-service-mesh-gateway-envoy-istio-kong-guide/) and [mutual TLS configuration guide](../2026-04-24-self-hosted-mutual-tls-mtls-nginx-caddy-traefik-envoy-guide-2026/). If you're managing Kubernetes ingress, our [ingress controller guide](../2026-04-22-traefik-vs-nginx-ingress-vs-contour-kubernetes-ingress-controller-guide-2026/) covers the entry-point layer.

## FAQ

### Can I use Kuma and Tyk together?

Yes, they serve different purposes. Kuma handles east-west traffic (service-to-service within your infrastructure) while Tyk handles north-south traffic (external client requests to your APIs). Deploy Kuma as the service mesh for internal communication and Tyk as the edge gateway for external API access.

### Does Pingora require Rust expertise to use?

Yes. Unlike Kuma and Tyk which are deploy-as-is products, Pingora is a Rust library. You need to write Rust code to build a functional proxy. This means your team needs Rust proficiency and the development timeline is measured in weeks, not minutes. The trade-off is complete control over proxy behavior and performance.

### How do I migrate from a commercial API gateway to a self-hosted one?

Map your existing rate limiting rules, authentication policies, and routing configurations to the self-hosted equivalent. Tyk has the most direct mapping for API key-based gateways. For service mesh migrations, Kuma's policies translate well from Istio or Linkerd configurations. Test thoroughly in a staging environment before switching production traffic.

### What is the performance difference between Envoy (Kuma) and Go (Tyk)?

Envoy (used by Kuma) is written in C++ and provides the highest raw throughput — typically 50K–100K requests/second on modern hardware. Tyk, written in Go, achieves 10K–30K requests/second on similar hardware. Pingora (Rust) can exceed 200K requests/second when optimized. For most API gateway use cases, both Envoy and Go are more than sufficient.

### Can these gateways handle WebSocket connections?

Yes. Kuma (via Envoy) supports WebSocket proxying with its native protocol detection. Tyk supports WebSocket passthrough with API-level configuration. Pingora supports WebSocket at the protocol level since it handles raw TCP streams. All three can proxy WebSocket connections, but Pingora gives you the most control over connection lifecycle management.

### How does Kuma handle service discovery?

Kuma integrates with Kubernetes service discovery natively, using the Kubernetes API to find and route to services. For VM and bare metal deployments, Kuma uses DNS-based service discovery or its own dataplane registration system. The control plane maintains a service catalog and distributes routing tables to Envoy sidecars.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted API Gateway Platforms: Kuma vs Tyk vs Pingora",
  "description": "Compare three self-hosted API gateway approaches — Kuma service mesh, Tyk API gateway, and Pingora proxy framework. Includes Docker Compose configs and architecture comparison.",
  "datePublished": "2026-05-08",
  "dateModified": "2026-05-08",
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
