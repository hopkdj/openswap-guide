---
title: "Self-Hosted Kubernetes Egress Gateways: Cilium Egress vs Istio Egress vs Squid Proxy"
date: "2026-05-16"
tags: ["kubernetes", "networking", "egress", "cilium", "istio", "squid", "security"]
draft: false
---

Controlling outbound traffic from Kubernetes clusters is a critical requirement for organizations with strict security, compliance, or data governance policies. Without proper egress controls, any pod in your cluster can reach any external endpoint — a scenario that opens the door to data exfiltration, unauthorized API calls, and compliance violations.

This guide compares three approaches to managing Kubernetes egress traffic: **Cilium Egress Gateway**, **Istio Egress Gateway**, and **Squid Proxy**. Each takes a fundamentally different approach to the problem, and understanding their trade-offs is essential for choosing the right solution for your infrastructure.

## What Is a Kubernetes Egress Gateway?

A Kubernetes egress gateway is a controlled exit point for outbound traffic leaving your cluster. Instead of allowing pods to connect directly to external services, egress gateways intercept, inspect, and route outbound connections through a centralized proxy or policy enforcement point.

Key capabilities include:

- **Traffic filtering** — block or allow specific external destinations by domain, IP, or port
- **TLS inspection** — decrypt and inspect encrypted outbound traffic for policy enforcement
- **Identity-based routing** — route egress traffic based on the Kubernetes service account or workload identity
- **Audit logging** — log all outbound connections for compliance and forensic analysis
- **NAT management** — assign stable external IP addresses to outbound traffic for allowlisting

## Cilium Egress Gateway

Cilium Egress Gateway is a native Kubernetes extension built on eBPF (extended Berkeley Packet Filter) that provides fine-grained egress traffic control at the network layer. It was introduced in Cilium 1.13 and has become a production-ready feature for managing outbound cluster traffic.

### Architecture

Cilium Egress Gateway works by deploying dedicated gateway pods that handle outbound NAT for selected workloads. Traffic from pods matching an `EgressGatewayPolicy` is SNAT'd through the gateway pod's egress IP, which is then routed to the external destination.

```yaml
apiVersion: cilium.io/v2
kind: CiliumEgressGatewayPolicy
metadata:
  name: backend-egress-policy
spec:
  selectors:
    - matchLabels:
        app: backend-service
  destinationCIDRs:
    - "10.0.0.0/8"
    - "172.16.0.0/12"
  egressGateway:
    egressGatewayNodeSelector:
      matchLabels:
        kubernetes.io/hostname: worker-node-1
    egressIPs:
      - "203.0.113.10"
```

Key features:
- **eBPF-based performance** — packet processing happens in kernel space with minimal overhead
- **Per-pod identity** — policies are tied to Kubernetes pod labels, not IP addresses
- **Multiple egress IPs** — different workloads can exit through different external IPs
- **Node selector support** — pin egress gateways to specific nodes for predictable networking
- **No sidecar required** — operates at the network layer, transparent to application pods

### Deployment

Deploy Cilium with egress gateway support via Helm:

```bash
helm install cilium cilium/cilium \
  --namespace kube-system \
  --set egressGateway.enabled=true \
  --set egressGateway.maxEgressIPs=10
```

## Istio Egress Gateway

Istio Egress Gateway is part of the Istio service mesh and provides application-layer egress control using Envoy proxy. Unlike Cilium's network-layer approach, Istio operates at Layer 7 (HTTP/TLS) and integrates deeply with Istio's service identity and traffic management features.

### Architecture

The Istio Egress Gateway is a dedicated Envoy proxy deployment that intercepts outbound traffic matching `ServiceEntry` and `VirtualService` resources. It supports full TLS origination, mTLS to internal services, and HTTP-level routing rules.

```yaml
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: istio-egressgateway
  namespace: istio-system
spec:
  selector:
    istio: egressgateway
  servers:
    - port:
        number: 443
        name: https
        protocol: HTTPS
      hosts:
        - "api.external-service.com"
---
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: direct-external-api
spec:
  hosts:
    - "api.external-service.com"
  gateways:
    - istio-egressgateway
    - mesh
  http:
    - match:
        - gateways:
            - mesh
          port: 443
      route:
        - destination:
            host: istio-egressgateway.istio-system.svc.cluster.local
            port:
              number: 443
```

Key features:
- **Layer 7 awareness** — HTTP routing, header manipulation, and TLS SNI matching
- **ServiceEntry integration** — declare external services as first-class Istio resources
- **mTLS support** — mutual TLS for internal-to-egress communication
- **Traffic shifting** — canary rollouts for external service destinations
- **Telemetry** — full Prometheus metrics and distributed tracing for egress traffic

### Deployment

Enable the egress gateway in your Istio installation:

```bash
istioctl install --set profile=default \
  --set components.egressGateways.enabled=true \
  --set values.gateways.istio-egressgateway.enabled=true
```

## Squid Proxy as Kubernetes Egress Gateway

Squid is a mature, battle-tested HTTP/HTTPS caching proxy that has been used for egress control since 1998. While not Kubernetes-native, Squid can be deployed as a sidecar or standalone proxy to handle outbound HTTP and HTTPS traffic from Kubernetes pods.

### Architecture

Squid operates as a traditional forward proxy. Pods are configured to route HTTP/HTTPS traffic through the Squid proxy via environment variables (`HTTP_PROXY`, `HTTPS_PROXY`) or iptables REDIRECT rules. Squid applies ACL-based filtering at the application layer.

```
version: "3.8"

services:
  squid:
    image: ubuntu/squid:latest
    ports:
      - "3128:3128"
    volumes:
      - ./squid.conf:/etc/squid/squid.conf:ro
      - squid-cache:/var/spool/squid
    restart: unless-stopped

volumes:
  squid-cache:
```

A basic `squid.conf` for egress filtering:

```
http_port 3128

# ACL definitions
acl allowed_domains dstdomain .github.com .docker.io .gcr.io
acl blocked_domains dstdomain .malware-site.com .phishing.net
acl internal_networks src 10.0.0.0/8 172.16.0.0/12

# Access rules
http_access allow internal_networks allowed_domains
http_access deny blocked_domains
http_access deny all

# Logging
access_log /var/log/squid/access.log squid
cache_log /var/log/squid/cache.log
```

Key features:
- **Mature and stable** — decades of production use, extensive documentation
- **HTTP/HTTPS caching** — reduces bandwidth for repeated external requests
- **ACL-based filtering** — flexible rule system for domain, IP, and content filtering
- **Authentication support** — integrates with LDAP, Kerberos, and basic auth
- **Non-HTTP protocols** — limited support for FTP and other protocols

## Comparison Table

| Feature | Cilium Egress Gateway | Istio Egress Gateway | Squid Proxy |
|---------|----------------------|---------------------|-------------|
| **Layer** | Layer 3/4 (Network) | Layer 7 (Application) | Layer 7 (Application) |
| **Technology** | eBPF | Envoy Proxy | Custom proxy |
| **Kubernetes-native** | Yes | Yes | No (manual deploy) |
| **TLS inspection** | Yes (with mTLS) | Yes (TLS origination) | Yes (with SSL bump) |
| **Per-pod identity** | Yes (labels) | Yes (service accounts) | No (IP-based) |
| **HTTP routing** | No | Yes | Yes |
| **Caching** | No | No | Yes |
| **Protocol support** | All TCP/UDP | HTTP/HTTPS/gRPC | HTTP/HTTPS/FTP |
| **Performance overhead** | Minimal (eBPF) | Moderate (Envoy) | Low-Moderate |
| **Stars (GitHub)** | 24,365+ | 38,202+ | 2,961+ |
| **Learning curve** | Moderate | Steep | Low |
| **Best for** | High-performance egress control | Service mesh environments | Simple HTTP proxy needs |

## Why Control Kubernetes Egress Traffic?

Unrestricted egress access is one of the most common security misconfigurations in Kubernetes deployments. Here's why egress control matters:

**Data loss prevention.** Without egress policies, a compromised pod can exfiltrate data to any external endpoint. Egress gateways restrict outbound connections to approved destinations, creating a critical barrier against data breaches.

**Compliance requirements.** Regulations like PCI DSS, HIPAA, and SOC 2 require organizations to log and control all network traffic — including outbound connections from containerized workloads. Egress gateways provide the audit trail needed for compliance.

**API cost control.** Pods that make unrestricted API calls to external services (cloud APIs, SaaS endpoints) can generate unexpected costs. Egress gateways allow you to rate-limit or block access to expensive external services.

**Stable external IPs.** Many external services require IP allowlisting. Egress gateways provide stable, predictable outbound IP addresses that can be registered with third-party services, eliminating the need to allowlist every pod IP.

**Supply chain security.** Restricting which package registries and container image sources pods can reach prevents dependency confusion attacks and ensures all software comes from approved sources.

For more on Kubernetes network security, see our [Cilium vs Calico vs Kube-router network policies guide](../2026-04-26-calico-vs-cilium-vs-kube-router-kubernetes-network-policies-guide/) and [service mesh gateway comparison](../2026-05-06-self-hosted-service-mesh-gateway-envoy-istio-kong-guide/). If you need bare-metal load balancing, our [MetalLB vs Kube-VIP vs Cilium LB guide](../2026-04-26-metallb-vs-kube-vip-vs-cilium-lb-bare-metal-kubernetes-load-balancer-guide/) covers that in depth.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Kubernetes Egress Gateways: Cilium Egress vs Istio Egress vs Squid Proxy",
  "description": "Compare three approaches to managing Kubernetes outbound traffic: Cilium Egress Gateway (eBPF), Istio Egress Gateway (Envoy), and Squid Proxy (HTTP caching). Learn when to use each for egress filtering, NAT, and TLS inspection.",
  "datePublished": "2026-05-16",
  "dateModified": "2026-05-16",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  }
}
</script>

## FAQ

### What is the difference between Cilium Egress Gateway and Istio Egress Gateway?

Cilium Egress Gateway operates at the network layer (L3/L4) using eBPF for high-performance packet processing, while Istio Egress Gateway operates at the application layer (L7) using Envoy proxy for HTTP-aware traffic control. Cilium is better for raw performance and protocol-agnostic filtering, while Istio excels at HTTP routing, TLS management, and service mesh integration.

### Can Squid Proxy handle HTTPS traffic from Kubernetes pods?

Yes, Squid supports HTTPS through its SSL Bump feature, which performs man-in-the-middle TLS termination to inspect encrypted traffic. However, this requires deploying Squid's CA certificate to all pods that need HTTPS inspection, which adds operational complexity.

### Do I need an egress gateway if I use Kubernetes NetworkPolicies?

Kubernetes NetworkPolicies control east-west (pod-to-pod) and north-south (pod-to-external) traffic at the IP/port level, but they lack identity-based routing, TLS inspection, and audit logging. An egress gateway provides application-layer control and centralized management that NetworkPolicies cannot offer.

### Which egress gateway solution has the lowest performance overhead?

Cilium Egress Gateway has the lowest overhead because it uses eBPF to process packets in kernel space, avoiding the context switches and copying overhead of user-space proxies like Envoy (Istio) or Squid. In benchmarks, Cilium typically adds less than 5% latency to outbound connections.

### Can I use multiple egress gateway solutions together?

Yes, it's common to use Cilium Egress Gateway for network-layer NAT and IP management while deploying Istio Egress Gateway for application-layer HTTP routing on top. Squid can coexist as a forward proxy for specific workloads that require HTTP caching.

### How do I assign a static external IP to egress traffic?

Both Cilium and Istio support assigning specific egress IPs. In Cilium, use the `egressIPs` field in `CiliumEgressGatewayPolicy`. In Istio, configure the egress gateway Service with `externalIPs` or use a LoadBalancer with a reserved IP. With Squid, bind the proxy to a specific network interface with the assigned IP.
