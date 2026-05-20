---
title: "Self-Hosted Envoy API Gateway Controllers: Envoy Gateway vs Contour vs Gloo Edge"
date: "2026-05-21"
tags: ["envoy", "api-gateway", "kubernetes", "ingress", "gateway-api", "proxy"]
draft: false
---

Envoy Proxy has become the de facto data plane for cloud-native networking. Rather than configuring Envoy directly, several open-source projects provide Kubernetes-native API gateway controllers built on Envoy. This guide compares **Envoy Gateway**, **Contour**, and **Gloo Edge** — three leading self-hosted Envoy-based API gateway solutions.

## Why Use an Envoy-Based API Gateway?

Envoy Proxy handles advanced traffic management that traditional reverse proxies struggle with:

- **Dynamic configuration** — xDS protocol enables real-time updates without restarts
- **Observability** — built-in metrics, distributed tracing, and access logging
- **Advanced routing** — weighted traffic splitting, header-based routing, and fault injection
- **gRPC support** — native gRPC proxying, load balancing, and health checking
- **Rate limiting** — configurable request limits per route, service, or client
- **Extensible filters** — HTTP, network, and listener filters for custom processing

Rather than managing raw Envoy configurations, API gateway controllers translate Kubernetes resources (Ingress, Gateway API CRDs) into Envoy xDS configurations automatically.

## Envoy API Gateway Landscape

| Controller | Governance | Gateway API | Kubernetes Ingress | Maturity |
|-----------|-----------|-------------|-------------------|----------|
| **Envoy Gateway** | CNCF Sandbox | Full (reference implementation) | Limited | Emerging (2023) |
| **Contour** | CNCF Graduated | Partial (via HTTPProxy) | Full support | Mature (2017) |
| **Gloo Edge** | Solo.io (commercial) | Partial | Full support + extensions | Mature (2018) |

## Envoy Gateway

Envoy Gateway is the official CNCF reference implementation of the Kubernetes Gateway API, built by the Envoy project maintainers. It translates Gateway API resources directly into Envoy xDS configurations.

### Architecture

```
Kubernetes API -> Gateway API CRDs -> Envoy Gateway Controller -> Envoy Proxy (xDS)
     |                  |                      |                      |
  GatewayClass      HTTPRoute             Bootstrap             Data Plane
  Gateway           ReferenceGrant        Config                  Listeners
```

### Kubernetes Deployment

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: envoy-gateway
spec:
  controllerName: gateway.envoyproxy.io/gatewayclass-controller
---
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: production-gateway
  namespace: default
spec:
  gatewayClassName: envoy-gateway
  listeners:
    - name: http
      protocol: HTTP
      port: 80
      allowedRoutes:
        namespaces:
          from: All
    - name: https
      protocol: HTTPS
      port: 443
      tls:
        mode: Terminate
        certificateRefs:
          - name: tls-secret
            kind: Secret
```

Define routing with HTTPRoute:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: api-route
  namespace: default
spec:
  parentRefs:
    - name: production-gateway
  hostnames:
    - "api.example.com"
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /v1
      backendRefs:
        - name: api-service-v1
          port: 8080
          weight: 90
        - name: api-service-v2
          port: 8080
          weight: 10
```

### Key Features

- **Gateway API first** — native support for all Gateway API resources (Gateway, HTTPRoute, TCPRoute, GRPCRoute, TLSRoute, UDPRoute)
- **Reference implementation** — shapes the Gateway API standard; new features land here first
- **Envoy admin integration** — direct access to Envoy admin interface for debugging
- **Extensible filters** — supports Envoy WASM filters for custom processing
- **Rate limiting** — Envoy-based rate limiting with Redis backend
- **Observability** — Prometheus metrics, OpenTelemetry tracing, access logging

### Strengths

- **Standards-compliant** — follows Gateway API specification exactly
- **Future-proof** — benefits from CNCF governance and Envoy project backing
- **Clean architecture** — no proprietary extensions; pure Kubernetes resources
- **Active development** — rapid release cycle with frequent feature additions

### Limitations

- **Young project** — lacks some production-hardening features of mature alternatives
- **Gateway API only** — does not support Kubernetes Ingress resources natively
- **Limited extensions** — fewer built-in plugins compared to Gloo Edge
- **Smaller ecosystem** — fewer community-contributed integrations

## Contour

Contour is a CNCF-graduated Kubernetes ingress controller that uses Envoy as its data plane. It predates the Gateway API and uses its own HTTPProxy CRD for advanced routing configuration.

### Architecture

```
Kubernetes API -> Ingress/HTTPProxy -> Contour Controller -> Envoy Proxy (xDS)
     |                  |                  |                  |
  Ingress           HTTPProxy         gRPC xDS API       Data Plane
  HTTPProxy         TLSDelegation     Config Delivery     Listeners
```

### Docker Compose (Local Testing)

```yaml
services:
  contour:
    image: ghcr.io/projectcontour/contour:v1.28.0
    command: ["contour", "serve", "--incluster"]
    network_mode: host
    volumes:
      - ./contour-config:/config:ro
    restart: unless-stopped

  envoy:
    image: envoyproxy/envoy:v1.30
    network_mode: host
    volumes:
      - ./envoy-config:/etc/envoy:ro
    command:
      - "--config-path"
      - "/etc/envoy/envoy.yaml"
    restart: unless-stopped
```

### Kubernetes Deployment

Contour's native resource is the HTTPProxy CRD:

```yaml
apiVersion: projectcontour.io/v1
kind: HTTPProxy
metadata:
  name: api-proxy
  namespace: default
spec:
  virtualhost:
    fqdn: api.example.com
    tls:
      secretName: tls-secret
  routes:
    - conditions:
        - prefix: /v1
      services:
        - name: api-service-v1
          port: 8080
          weight: 90
        - name: api-service-v2
          port: 8080
          weight: 10
    - conditions:
        - prefix: /health
      services:
        - name: api-service-v1
          port: 8080
          healthCheck:
            path: /healthz
            intervalSeconds: 5
            timeoutSeconds: 2
            unhealthyThreshold: 3
            healthyThreshold: 2
```

### Key Features

- **HTTPProxy CRD** — Contour's own resource for advanced routing (more features than Ingress)
- **Kubernetes Ingress support** — full compatibility with standard Ingress resources
- **Delegation** — route delegation across namespaces for multi-team environments
- **Request mirroring** — shadow traffic for testing without affecting production
- **Retry and timeout policies** — configurable per-route retry logic
- **External authorization** — integrate with external auth services (OAuth, JWT)
- **Envoy access logging** — configurable access log format and destination

### Strengths

- **CNCF graduated** — proven production stability with wide adoption
- **Mature feature set** — extensive routing, security, and observability features
- **Dual API support** — works with both Ingress and HTTPProxy resources
- **Well-documented** — comprehensive documentation and community examples
- **Stable release cycle** — predictable quarterly releases with LTS support

### Limitations

- **HTTPProxy is proprietary** — not a Kubernetes standard; locks you into Contour
- **Gateway API support is partial** — some Gateway API features not yet implemented
- **Less innovative** — slower to adopt new Kubernetes networking features
- **Configuration complexity** — HTTPProxy CRD has a steep learning curve

## Gloo Edge

Gloo Edge is a feature-rich API gateway built on Envoy, developed by Solo.io. It extends beyond basic routing with API management, transformations, and function-level routing.

### Architecture

```
Kubernetes API -> VirtualService/RouteTable -> Gloo Edge Controller -> Envoy Proxy (xDS)
     |                      |                        |                  |
  VirtualService         RouteTable              xDS Server          Data Plane
  RouteTable             Upstream                Rate Limit          Auth Server
```

### Kubernetes Deployment

```yaml
apiVersion: gateway.solo.io/v1
kind: VirtualService
metadata:
  name: api-gateway
  namespace: gloo-system
spec:
  virtualHost:
    domains:
      - "api.example.com"
    routes:
      - matchers:
          - prefix: /v1
        routeAction:
          single:
            upstream:
              name: api-service-v1
              namespace: gloo-system
        routePlugins:
          prefixRewrite:
            prefixRewrite: "/api/v1"
      - matchers:
          - prefix: /v2
        routeAction:
          single:
            upstream:
              name: api-service-v2
              namespace: gloo-system
        routePlugins:
          faultInjection:
            abort:
              httpStatus: 503
              percentage: 5
```

### Key Features

- **Function-level routing** — route to individual serverless functions, not just services
- **Request/response transformations** — modify headers, body, and paths with templates
- **API schema validation** — validate requests against OpenAPI/Swagger schemas
- **Web Application Firewall** — built-in ModSecurity integration
- **OAuth and JWT** — integrated authentication with OIDC providers
- **Rate limiting** — token bucket and sliding window rate limiting
- **Circuit breaking** — automatic fault tolerance with configurable thresholds
- **GraphQL support** — native GraphQL routing and schema stitching

### Strengths

- **Feature-rich** — most comprehensive feature set among Envoy-based gateways
- **API management** — schema validation, rate limiting, and transformations built in
- **Function routing** — unique capability for serverless and microservices architectures
- **Commercial backing** — Solo.io provides enterprise support and training
- **Extensive plugins** — large library of built-in and community extensions

### Limitations

- **Vendor lock-in** — Gloo-specific CRDs not portable to other gateways
- **Commercial dependency** — core development driven by Solo.io's business interests
- **Resource intensive** — more components increase footprint
- **Complexity** — feature richness comes with configuration complexity
- **Open-source limitations** — some advanced features require Gloo Platform (commercial)

## Comparison Summary

| Feature | Envoy Gateway | Contour | Gloo Edge |
|---------|--------------|---------|-----------|
| **Governance** | CNCF Sandbox | CNCF Graduated | Solo.io (commercial) |
| **Gateway API** | Full (reference) | Partial | Partial |
| **Ingress support** | No | Yes | Yes |
| **Custom CRDs** | Gateway API only | HTTPProxy | VirtualService, RouteTable |
| **Rate limiting** | Yes (Envoy) | No (manual) | Yes (built-in) |
| **Request transforms** | WASM only | No | Yes (native) |
| **API schema validation** | No | No | Yes |
| **Function routing** | No | No | Yes |
| **WAF integration** | Manual | Manual | Yes (ModSecurity) |
| **GraphQL support** | Via filters | No | Yes |
| **External auth** | Via filters | Yes (extauth) | Yes (native) |
| **Community size** | Growing | Large | Medium |
| **Production maturity** | Emerging | High | High |

## Choosing the Right Envoy API Gateway

**Use Envoy Gateway when:**
- You want standards-compliant Gateway API implementation
- Your team values CNCF governance over vendor-specific features
- You are building new infrastructure and can adopt Gateway API from the start
- You want the reference implementation that shapes Kubernetes networking standards

**Use Contour when:**
- You need a battle-tested, CNCF-graduated ingress controller
- Your team already uses Kubernetes Ingress resources
- You want the stability of a mature project with predictable releases
- You need HTTPProxy features like route delegation and request mirroring

**Use Gloo Edge when:**
- You need advanced API management features (schema validation, transformations)
- Your architecture includes serverless functions requiring function-level routing
- You want built-in WAF, rate limiting, and circuit breaking
- Your team values commercial support and enterprise features

## Why Self-Host an Envoy API Gateway?

Self-hosting an Envoy-based API gateway gives you complete control over traffic routing, security policies, and observability. Unlike managed API gateway services, self-hosted solutions keep all traffic within your infrastructure, eliminating data egress costs and ensuring compliance with data residency requirements. Envoy's performance characteristics — handling 100,000+ requests per second with sub-millisecond latency — make it suitable for high-throughput API workloads.

For teams evaluating the broader Kubernetes networking landscape, our [MetalLB vs kube-vip vs Cilium LB comparison](../2026-04-26-metallb-vs-kube-vip-vs-cilium-lb-bare-metal-kubernetes-load/) covers load balancing options, and our [Traefik vs NGINX vs Contour ingress guide](../2026-04-22-traefik-vs-nginx-ingress-vs-contour-kubernetes-ingress-cont/) provides broader ingress controller context.

## FAQ

### What is the difference between Envoy Gateway and Contour?

Envoy Gateway is the official CNCF reference implementation of the Kubernetes Gateway API, using standard Gateway API CRDs. Contour uses its own HTTPProxy CRD and predates the Gateway API. Envoy Gateway is newer but standards-focused; Contour is more mature with a larger feature set but uses proprietary resources.

### Does Envoy Gateway support Kubernetes Ingress?

No, Envoy Gateway only supports the Kubernetes Gateway API (Gateway, HTTPRoute, TCPRoute, etc.). It does not process standard Kubernetes Ingress resources. If you need Ingress compatibility, use Contour or Gloo Edge.

### Can Gloo Edge replace an API management platform?

Gloo Edge provides many API management features — rate limiting, request transformations, schema validation, and authentication. For small to medium API programs, it can replace a dedicated API management platform. However, enterprise API portals, developer onboarding, and monetization features require the commercial Gloo Platform.

### How does Envoy Gateway handle rate limiting?

Envoy Gateway uses Envoy's built-in rate limiting service, which requires a Redis backend for distributed rate limit state. Configure rate limits through Envoy Gateway's EnvoyPatchPolicy or EnvoyExtensionPolicy resources. The rate limiting is applied at the Envoy data plane level.

### Which Envoy gateway has the best performance?

All three gateways use Envoy as their data plane, so raw proxy performance is nearly identical. Performance differences come from the control plane: Envoy Gateway has the simplest architecture (fewest components), Contour has moderate overhead, and Gloo Edge has the most components (discovery, gateway-proxy, rate limit server). For most workloads, the difference is negligible.

### Can I migrate from Contour to Envoy Gateway?

Migration requires rewriting HTTPProxy resources as Gateway API resources (HTTPRoute, Gateway, etc.). The routing semantics are similar but not identical. Contour's route delegation maps to Gateway API's ReferenceGrant, and HTTPProxy conditions map to HTTPRoute matches. Plan for a phased migration with both gateways running in parallel.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Envoy API Gateway Controllers: Envoy Gateway vs Contour vs Gloo Edge",
  "description": "Compare self-hosted Envoy-based Kubernetes API gateway controllers: Envoy Gateway, Contour, and Gloo Edge for production API traffic management.",
  "datePublished": "2026-05-21",
  "dateModified": "2026-05-21",
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
