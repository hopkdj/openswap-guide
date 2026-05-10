---
title: "Kubernetes Gateway API Controllers: Envoy Gateway vs NGINX Gateway Fabric vs Kong"
date: "2026-05-10"
tags: ["kubernetes", "gateway-api", "envoy", "nginx", "kong", "ingress", "cloud-native"]
draft: false
---

The Kubernetes Gateway API represents the next generation of traffic management for Kubernetes workloads, designed to succeed the Ingress API with more expressive routing, role-based configuration, and support for advanced use cases like TCP/UDP routing and header-based traffic splitting. While the Gateway API itself is a specification, you need a controller implementation to actually handle traffic. In this guide, we compare three leading implementations: **Envoy Gateway**, **NGINX Gateway Fabric**, and the **Kong Ingress Controller**.

## What Is the Kubernetes Gateway API?

The Gateway API is a SIG Network initiative that standardizes how traffic enters a Kubernetes cluster. Unlike the legacy Ingress API, it introduces several key improvements:

- **Role-based separation** — GatewayClass, Gateway, and HTTPRoute resources map to platform, infra, and developer roles
- **Extended resource types** — supports TCPRoute, UDPRoute, TLSRoute, and GRPCRoute natively
- **Policy attachment** — decouples policies (rate limiting, retries, timeouts) from routing rules
- **Multi-cluster support** — designed from the ground up for cross-cluster and multi-cluster deployments
- **Backend protocol support** — native gRPC and WebSocket routing without annotations

The Gateway API has graduated to GA status for HTTP routing and is rapidly becoming the default choice for new Kubernetes deployments. However, the specification alone does nothing — you need a controller that implements the API spec and handles actual traffic routing.

## Envoy Gateway

[Envoy Gateway](https://gateway.envoyproxy.io/) is the official Gateway API implementation from the Envoy Proxy project, maintained by the Envoy community. It translates Gateway API resources into Envoy proxy configurations automatically.

### Architecture

Envoy Gateway runs a control plane that watches Gateway API CRDs and generates xDS configurations for Envoy proxy data plane instances. Each Gateway resource spawns its own Envoy deployment, providing isolation between different application teams.

### Key Features

- **Native Envoy integration** — full access to Envoy's extensible filter chain
- **Extension policies** — custom rate limiting, authentication, and traffic management via Envoy's extension framework
- **Automatic TLS** — integrated with cert-manager for certificate provisioning
- **Multi-tenant isolation** — separate Envoy instances per Gateway resource
- **Observability** — native integration with OpenTelemetry for distributed tracing and metrics

### Deployment

Envoy Gateway is deployed via Helm chart:

```bash
helm install envoy-gateway oci://docker.io/envoyproxy/gateway-helm   --namespace envoy-gateway-system   --create-namespace
```

### Docker Compose (Local Testing)

For local development and testing, Envoy Gateway can be run with Docker Compose using the xDS server:

```yaml
version: "3.8"
services:
  envoy-gateway:
    image: envoyproxy/gateway-dev:latest
    ports:
      - "10080:10080"
      - "10081:10081"
    volumes:
      - ./gateway-config.yaml:/gateway-config.yaml
    command: ["--config-path", "/gateway-config.yaml"]
    environment:
      - ENVOY_GATEWAY_NAMESPACE=default
      - ENVOY_GATEWAY_PROVIDER=kubernetes

  envoy-proxy:
    image: envoyproxy/envoy:v1.32-latest
    ports:
      - "8080:8080"
      - "8443:8443"
    depends_on:
      - envoy-gateway
    volumes:
      - ./envoy-bootstrap.yaml:/etc/envoy/envoy.yaml
    command: ["-c", "/etc/envoy/envoy.yaml", "--log-level", "info"]
```

## NGINX Gateway Fabric

[NGINX Gateway Fabric](https://docs.nginx.com/nginx-gateway-fabric/) is NGINX's implementation of the Kubernetes Gateway API, built by F5/NGINX. It uses NGINX as the data plane and provides a familiar configuration model for teams already using NGINX.

### Architecture

NGINX Gateway Fabric runs a single control plane pod that watches Gateway API resources and generates NGINX configuration files. The data plane consists of NGINX processes that reload configuration dynamically when routes change.

### Key Features

- **NGINX performance** — battle-tested data plane handling millions of requests per second
- **Familiar configuration** — NGINX config model for teams experienced with nginx.conf
- **Rate limiting** — built-in rate limiting via NGINX's limit_req module
- **SSL/TLS termination** — robust TLS handling with modern cipher support
- **Health checks** — active and passive health checking for upstream services
- **Access logging** — customizable NGINX access log format with structured JSON output

### Deployment

```bash
helm install ngf oci://ghcr.io/nginxinc/charts/nginx-gateway-fabric   --namespace nginx-gateway   --create-namespace   --set service.type=LoadBalancer
```

### Docker Compose

NGINX Gateway Fabric can be tested locally with a Docker Compose setup:

```yaml
version: "3.8"
services:
  nginx-gateway:
    image: ghcr.io/nginxinc/nginx-gateway-fabric:edge
    ports:
      - "80:80"
      - "443:443"
      - "9091:9091"
    volumes:
      - ./nginx-config:/etc/nginx/conf.d
      - ./certs:/etc/nginx/ssl
    environment:
      - NGINX_GATEWAY_MODE=standalone
      - NGINX_GATEWAY_LOG_LEVEL=debug
    restart: unless-stopped
```

## Kong Ingress Controller

[Kong Ingress Controller](https://docs.konghq.com/kubernetes-ingress-controller/) is Kong's implementation for both the Ingress API and the Gateway API. It uses Kong Gateway (based on OpenResty/Lua) as the data plane and provides extensive plugin-based extensibility.

### Architecture

Kong runs a control plane (Kong Ingress Controller) that watches Kubernetes resources and configures the data plane (Kong Gateway). Kong Gateway uses a Lua-based plugin system for traffic transformation, authentication, and policy enforcement.

### Key Features

- **Plugin ecosystem** — 50+ built-in plugins for auth, rate limiting, transformations, logging
- **Declarative configuration** — Kong's declarative config (decK) can be version-controlled
- **Gateway API + Ingress** — supports both APIs simultaneously during migration
- **Enterprise features** — Kong Manager, Dev Portal, and Vitals (available in enterprise edition)
- **gRPC and GraphQL** — native protocol support with GraphQL introspection
- **Kong Mesh** — optional service mesh integration for mTLS between services

### Deployment

```bash
helm install kong kong/kong   --namespace kong   --create-namespace   --set ingressController.installCRDs=false   --set ingressController.gatewayAPI.enabled=true   --set proxy.type=LoadBalancer
```

### Docker Compose

Kong Gateway can be run locally with Docker Compose:

```yaml
version: "3.8"
services:
  kong-database:
    image: postgres:16
    environment:
      POSTGRES_USER: kong
      POSTGRES_DB: kong
      POSTGRES_PASSWORD: kong
    volumes:
      - pgdata:/var/lib/postgresql/data

  kong-migrations:
    image: kong:3.7
    command: kong migrations bootstrap
    depends_on:
      - kong-database
    environment:
      KONG_DATABASE: postgres
      KONG_PG_HOST: kong-database
      KONG_PG_PASSWORD: kong

  kong-gateway:
    image: kong:3.7
    ports:
      - "8000:8000"
      - "8443:8443"
      - "8001:8001"
      - "8444:8444"
    depends_on:
      - kong-database
      - kong-migrations
    environment:
      KONG_DATABASE: postgres
      KONG_PG_HOST: kong-database
      KONG_PG_PASSWORD: kong
      KONG_PROXY_ACCESS_LOG: /dev/stdout
      KONG_ADMIN_ACCESS_LOG: /dev/stdout
      KONG_PROXY_ERROR_LOG: /dev/stderr
      KONG_ADMIN_ERROR_LOG: /dev/stderr
      KONG_ADMIN_LISTEN: "0.0.0.0:8001"

volumes:
  pgdata:
```

## Feature Comparison

| Feature | Envoy Gateway | NGINX Gateway Fabric | Kong Ingress Controller |
|---|---|---|---|
| Data Plane | Envoy Proxy | NGINX | Kong Gateway (OpenResty) |
| GitHub Stars | 2,690+ | 1,060+ | 2,380+ |
| License | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| Gateway API Support | Full (GA) | Full (GA) | Full (GA) + Ingress |
| TCP/UDP Routing | Yes | Yes | Yes |
| Rate Limiting | Via extension | Built-in (limit_req) | Plugin-based |
| Authentication | Via extension | Basic auth only | 50+ auth plugins |
| TLS Management | cert-manager integration | Manual/Secrets | cert-manager + plugins |
| Observability | OpenTelemetry native | NGINX access logs | Prometheus + plugins |
| Multi-tenant | Per-Gateway isolation | Single instance | Namespace isolation |
| Configuration Model | Gateway API CRDs | Gateway API CRDs | Gateway API + CRDs + decK |
| Plugin System | Envoy filters (Wasm) | NGINX modules | Lua plugins (50+) |
| Enterprise Edition | No | NGINX Plus | Kong Enterprise |
| Best For | Envoy-centric stacks | NGINX-centric stacks | Plugin-heavy requirements |

## Choosing the Right Gateway API Controller

Your choice depends on your existing infrastructure and operational expertise:

- **Choose Envoy Gateway** if you already run Envoy in your stack, need fine-grained traffic control with Envoy's filter chain, or want the most conformant Gateway API implementation from the specification authors.

- **Choose NGINX Gateway Fabric** if your team knows NGINX well, you need maximum raw throughput performance, or you're migrating from traditional NGINX Ingress Controller deployments.

- **Choose Kong Ingress Controller** if you need extensive built-in functionality (authentication, rate limiting, transformations) without writing custom policies, or you're already using Kong in production.

For related reading, see our [Kubernetes Ingress Controller comparison](../2026-04-22-traefik-vs-nginx-ingress-vs-contour-kubernetes-ingress-controller-guide/) and [API Gateway deep dive](../self-hosted-api-gateway-apisix-kong-tyk-guide/) for broader context on traffic management in Kubernetes.

## Why Self-Host Your Gateway Controller?

Running your own Gateway API controller gives you complete control over how traffic enters your Kubernetes cluster. Managed Kubernetes services offer managed load balancers, but they often lack the fine-grained routing, policy attachment, and protocol support that the Gateway API provides.

When you self-host a Gateway API controller, you own the full traffic management stack. This means you can implement custom rate limiting rules, deploy canary releases with precise traffic splitting, enforce mTLS between internal services, and route gRPC traffic alongside HTTP — all through declarative Kubernetes resources.

For organizations running multi-cluster deployments, the Gateway API's design enables consistent traffic management across clusters. Unlike vendor-specific ingress controllers, the Gateway API is an open specification implemented by multiple vendors, avoiding lock-in.

Additionally, self-hosting eliminates per-request or per-connection charges that managed API gateways often impose. At scale, the cost savings of running your own Envoy, NGINX, or Kong-based gateway can be significant compared to cloud-managed alternatives.

For teams managing containerized applications, understanding [Kubernetes CNI options](../2026-04-21-flannel-vs-calico-vs-cilium-self-hosted-kubernetes-cni-guide/) and [container runtime choices](../containerd-vs-cri-o-vs-podman-self-hosted-container-runtimes/) provides the foundational networking context needed to properly architect gateway deployments.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Kubernetes Gateway API Controllers: Envoy Gateway vs NGINX Gateway Fabric vs Kong",
  "description": "Compare Envoy Gateway, NGINX Gateway Fabric, and Kong Ingress Controller for implementing the Kubernetes Gateway API. Feature comparison, deployment guides, and selection criteria.",
  "datePublished": "2026-05-10",
  "dateModified": "2026-05-10",
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

## FAQ

### What is the difference between Ingress and Gateway API in Kubernetes?

The Ingress API is the original, simpler way to expose HTTP services in Kubernetes. It supports basic path and host-based routing with vendor-specific annotations. The Gateway API is its successor, offering role-based configuration, support for multiple protocols (HTTP, TCP, UDP, gRPC), policy attachment, and a more expressive resource model. The Gateway API has reached GA status and is recommended for new deployments.

### Can I run both Ingress and Gateway API controllers in the same cluster?

Yes. Both can coexist in the same cluster. Many organizations run them side-by-side during migration, gradually moving workloads from Ingress resources to Gateway API resources (HTTPRoute, TCPRoute, etc.) as their controller supports both APIs.

### Which Gateway API controller has the best performance?

NGINX Gateway Fabric typically achieves the highest raw throughput due to NGINX's optimized event-driven architecture. Envoy Gateway provides more flexible performance tuning through Envoy's thread model and connection pooling. Kong Gateway performs well but adds some overhead from its Lua plugin system. For most workloads, the performance difference is negligible — choose based on features and operational familiarity.

### Do I need a database for the Gateway API controller?

Envoy Gateway and NGINX Gateway Fabric do not require an external database — they store configuration in memory and sync from Kubernetes APIs. Kong Ingress Controller can run in DB-less mode (declarative YAML configuration) or with a PostgreSQL/Cassandra backend for multi-node deployments.

### How do I migrate from Ingress to Gateway API?

Start by deploying your chosen Gateway API controller alongside your existing Ingress controller. Create HTTPRoute resources that mirror your Ingress rules, test traffic routing, then gradually switch DNS/load balancer entries to point to the Gateway. The Kong Ingress Controller supports both APIs simultaneously, making it the easiest migration path.

### Is the Gateway API production-ready?

Yes. HTTP routing in the Gateway API reached GA status in Kubernetes 1.28. TCP, UDP, and TLS routing are in beta. Major cloud providers (GKE, EKS, AKS) support Gateway API natively, and the three controllers compared here are all production-grade implementations used in enterprise environments.
