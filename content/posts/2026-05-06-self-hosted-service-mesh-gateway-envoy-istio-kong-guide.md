---
title: "Self-Hosted Service Mesh Gateways: Envoy Gateway vs Istio Ingress vs Kong Ingress Controller 2026"
date: 2026-05-06
tags: ["comparison", "guide", "self-hosted", "kubernetes", "service-mesh", "gateway", "ingress"]
draft: false
---

A service mesh gateway sits at the edge of your Kubernetes cluster, handling north-south traffic routing, TLS termination, rate limiting, and observability for microservices. Unlike traditional ingress controllers, mesh-native gateways integrate with service mesh data planes for advanced traffic management, mutual TLS, and fine-grained routing policies.

In this guide, we compare three leading open-source options for deploying a self-hosted service mesh gateway: **Envoy Gateway**, **Istio Ingress Gateway**, and **Kong Ingress Controller**. Each takes a different architectural approach to solving the same problem — managing external access to services running inside your cluster.

## What Is a Service Mesh Gateway?

A service mesh gateway is the entry point for all external traffic into a service mesh. It differs from a standard Kubernetes Ingress in several key ways:

- **Deep mesh integration** — understands service mesh concepts like virtual services, destination rules, and peer authentication
- **Unified policy enforcement** — applies authentication, rate limiting, and routing policies consistent with east-west traffic
- **Advanced traffic management** — supports canary deployments, A/B testing, fault injection, and traffic splitting
- **Built-in observability** — emits metrics, traces, and logs aligned with your mesh telemetry pipeline

For organizations already running a service mesh, deploying a gateway that shares the same data plane and control plane simplifies operations significantly.

## Envoy Gateway

**GitHub:** [envoyproxy/gateway](https://github.com/envoyproxy/gateway) | **Stars:** 2,682+ | **Language:** Go

Envoy Gateway is the official Kubernetes gateway implementation from the Envoy project. It implements the Kubernetes Gateway API specification and manages Envoy Proxy instances as standalone or Kubernetes-based application gateways.

### Architecture

Envoy Gateway follows a clean separation between the control plane (Envoy Gateway) and data plane (Envoy Proxy). The controller watches Gateway API resources (GatewayClass, Gateway, HTTPRoute, etc.) and generates corresponding Envoy Proxy configurations.

### Key Features

- **Kubernetes Gateway API native** — first-class implementation of the Gateway API standard
- **Multi-provider support** — deploys Envoy Proxy as a Deployment, DaemonSet, or via infrastructure providers
- **Extensible via Envoy Extension Policy** — supports WASM filters, Lua scripting, and custom extensions
- **Rate limiting integration** — built-in support for Envoy's rate limit service
- **mTLS support** — integrates with cert-manager for automatic certificate management

### Deployment

```yaml
# Install Envoy Gateway via Helm
apiVersion: helm.cattle.io/v1
kind: HelmChart
metadata:
  name: envoy-gateway
  namespace: envoy-gateway-system
spec:
  chart: envoy-gateway
  repo: https://docker.io/envoyproxy
  version: v1.2.0
  targetNamespace: envoy-gateway-system
---
# Define a GatewayClass
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: eg
spec:
  controllerName: gateway.envoyproxy.io/gatewayclass-controller
---
# Deploy a Gateway
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: eg
  namespace: default
spec:
  gatewayClassName: eg
  listeners:
  - name: http
    protocol: HTTP
    port: 80
  - name: https
    protocol: HTTPS
    port: 443
    tls:
      mode: Terminate
      certificateRefs:
      - name: example-com-tls
```

### Docker Compose (for local development)

```yaml
version: "3.8"
services:
  envoy-gateway:
    image: envoyproxy/gateway-dev:latest
    ports:
      - "8080:8080"
      - "8443:8443"
    environment:
      - ENVOY_GATEWAY_NAMESPACE=default
    volumes:
      - ./config:/etc/envoy-gateway
```

## Istio Ingress Gateway

**GitHub:** [istio/istio](https://github.com/istio/istio) | **Stars:** 38,166+ | **Language:** Go

Istio's Ingress Gateway is the most widely deployed service mesh gateway. It uses Envoy Proxy as its data plane, managed by Istio's control plane (istiod), providing the deepest integration with Istio's traffic management, security, and observability features.

### Architecture

The Istio Ingress Gateway is an Envoy Proxy deployment configured by istiod. It receives configuration via xDS APIs and applies Istio VirtualService, Gateway, and DestinationRule resources to define routing behavior.

### Key Features

- **Full Istio integration** — automatic mTLS, authorization policies, telemetry
- **Advanced traffic management** — weighted routing, circuit breaking, retries, timeouts
- **Security-first** — peer authentication, request authentication, authorization policies
- **Rich observability** — Kiali integration, Jaeger tracing, Prometheus metrics
- **Multi-cluster support** — gateways can route across cluster boundaries

### Deployment

```yaml
# Install Istio with ingress gateway
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  namespace: istio-system
spec:
  profile: default
  components:
    ingressGateways:
    - name: istio-ingressgateway
      enabled: true
      k8s:
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
---
# Define an Istio Gateway
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: app-gateway
  namespace: default
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: app-credential
    hosts:
    - "app.example.com"
---
# Route traffic to backend
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: app-vs
  namespace: default
spec:
  hosts:
  - "app.example.com"
  gateways:
  - app-gateway
  http:
  - route:
    - destination:
        host: app-service
        port:
          number: 80
```

## Kong Ingress Controller

**GitHub:** [kong/kubernetes-ingress-controller](https://github.com/kong/kubernetes-ingress-controller) | **Stars:** 2,382+ | **Language:** Go

Kong Ingress Controller (KIC) uses Kong Gateway (built on OpenResty/Nginx and Lua) as its data plane. It offers both Kubernetes Ingress and Gateway API support, plus Kong's rich plugin ecosystem for authentication, rate limiting, and transformations.

### Architecture

KIC uses a dual-component architecture: the controller manager watches Kubernetes resources, and Kong Gateway (the data plane) handles actual traffic. Kong's plugin system (Lua-based) provides extensive extensibility.

### Key Features

- **Plugin ecosystem** — 100+ plugins for auth, rate limiting, transformations, logging
- **Dual API support** — Kubernetes Ingress and Gateway API
- **Declarative configuration** — DB-less mode with KongConfig for GitOps workflows
- **Admin API** — full REST API for runtime configuration changes
- **Hybrid mode** — separate control and data plane nodes for large deployments

### Deployment

```yaml
# Install Kong Ingress Controller via Helm
apiVersion: helm.cattle.io/v1
kind: HelmChart
metadata:
  name: kong
  namespace: kong
spec:
  chart: kong
  repo: https://charts.konghq.com
  version: "2.38"
  targetNamespace: kong
  valuesContent: |-
    ingressController:
      enabled: true
      ingressClass: kong
    proxy:
      type: LoadBalancer
    env:
      database: "off"
---
# Define a Kong Ingress resource
apiVersion: configuration.konghq.com/v1
kind: KongIngress
metadata:
  name: rate-limit
  namespace: default
route:
  methods:
  - GET
  - POST
  strip_path: true
  preserve_host: true
upstream:
  hash_on: none
  algorithm: round-robin
---
# Apply rate limiting via annotation
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  namespace: default
  annotations:
    konghq.com/plugins: rate-limit
spec:
  ingressClassName: kong
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: app-service
            port:
              number: 80
```

## Comparison Table

| Feature | Envoy Gateway | Istio Ingress Gateway | Kong Ingress Controller |
|---------|---------------|----------------------|------------------------|
| Data Plane | Envoy Proxy | Envoy Proxy | Kong (OpenResty/Nginx) |
| API Standard | Gateway API | Istio CRDs + Gateway API | Ingress + Gateway API |
| Rate Limiting | Via Envoy RL service | Built-in | Kong plugins (100+) |
| mTLS | Via cert-manager | Automatic (Istio CA) | Via cert-manager/plugins |
| Extensibility | WASM filters, Lua | EnvoyFilter, WASM | Lua plugins (extensive) |
| Multi-cluster | Planned | Supported | Supported |
| GitHub Stars | 2,682+ | 38,166+ | 2,382+ |
| License | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| Language | Go | Go | Go (controller), Lua (data) |
| Best For | Gateway API adoption | Full service mesh | Plugin ecosystem |

## Choosing the Right Gateway

**Choose Envoy Gateway** if you want a clean, standards-based implementation of the Kubernetes Gateway API. It's the future-proof choice as Gateway API matures to GA, and it keeps you close to the Envoy project without vendor lock-in.

**Choose Istio Ingress Gateway** if you're already running Istio as your service mesh. The integration is seamless, and you get mTLS, authorization, and observability for free. The trade-off is the operational complexity of running Istio.

**Choose Kong Ingress Controller** if you need a rich plugin ecosystem and don't require full service mesh integration. Kong excels at API gateway use cases with authentication, rate limiting, and request transformations out of the box.

## Why Self-Host Your Service Mesh Gateway?

Running your own service mesh gateway gives you complete control over traffic routing, security policies, and observability. Unlike managed API gateway services, self-hosted gateways keep all traffic within your infrastructure, eliminating data egress costs and ensuring compliance with data residency requirements.

For organizations handling sensitive data, having the gateway on-premises or in your own VPC means no third party can inspect or intercept your traffic. The open-source nature of all three tools also means no vendor lock-in — you own your configuration and can migrate between solutions as your needs evolve.

For related reading, see our [Kubernetes Ingress Controller comparison](../2026-04-22-traefik-vs-nginx-ingress-vs-contour-kubernetes-ingress-controller-guide-2026/), [service mesh identity guide](../2026-04-28-spiffe-spire-vs-istio-vs-linkerd-self-hosted-service-identity-mtls-guide-2026/), and [API gateway observability guide](../2026-05-07-self-hosted-api-gateway-observability-kong-vitals-vs-tyk-pump-vs-grafana-guide/).

## FAQ

### What is the difference between an ingress controller and a service mesh gateway?

An ingress controller handles north-south traffic (external to cluster) using the Kubernetes Ingress API. A service mesh gateway also handles north-south traffic but is integrated with the service mesh's control plane, enabling consistent policies, mTLS, and advanced traffic management across both north-south and east-west traffic flows.

### Can I use Envoy Gateway without a full service mesh?

Yes. Envoy Gateway is designed as a standalone gateway that implements the Kubernetes Gateway API. It manages Envoy Proxy instances independently of any service mesh control plane. You can use it as a pure ingress gateway without deploying a mesh.

### Does Istio Ingress Gateway require the full Istio control plane?

Yes. The Istio Ingress Gateway is managed by istiod and requires the full Istio control plane to be running. This is the main trade-off — you get deep integration but must operate the entire Istio stack.

### Which gateway has the best rate limiting?

Kong Ingress Controller has the most comprehensive rate limiting with 10+ rate limiting plugins (request, response, per-consumer, per-IP, etc.). Envoy Gateway supports rate limiting via the Envoy rate limit service. Istio provides basic rate limiting via EnvoyFilter configuration.

### Is the Kubernetes Gateway API production-ready?

As of 2026, Gateway API has reached GA status for core resources (GatewayClass, Gateway, HTTPRoute). Advanced features like TCPRoute, TLSRoute, and GRPCRoute are still in beta. For production workloads using HTTP/HTTPS, Gateway API is production-ready.

### How do I migrate from Nginx Ingress to a mesh gateway?

Migration involves: (1) installing the new gateway controller, (2) translating Ingress resources to Gateway API or vendor-specific CRDs, (3) testing routing behavior in a staging environment, (4) updating DNS to point to the new gateway's load balancer IP, and (5) decommissioning the old ingress controller.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Service Mesh Gateways: Envoy Gateway vs Istio Ingress vs Kong Ingress Controller 2026",
  "description": "Compare Envoy Gateway, Istio Ingress Gateway, and Kong Ingress Controller for self-hosted Kubernetes service mesh gateway deployments. Features, architecture, and deployment guides.",
  "datePublished": "2026-05-06",
  "dateModified": "2026-05-06",
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
