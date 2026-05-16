---
title: "Self-Hosted Microsegmentation: Container Network Security Platforms in 2026"
date: "2026-05-17"
tags: ["microsegmentation", "security", "kubernetes", "cilium", "network-policy"]
draft: false
---

Traditional perimeter firewalls are insufficient for modern containerized workloads. Once traffic passes the network boundary, lateral movement between services is unrestricted. **Network microsegmentation** solves this by enforcing security policies at the individual workload level — controlling which pods, containers, or VMs can communicate with each other.

In this guide, we compare three self-hosted microsegmentation platforms: **Cilium Network Policies** (eBPF-based), **AccuKnox** (policy discovery and enforcement), and **Calico Network Policies** (traditional iptables/eBPF). Each takes a different approach to container network security.

## What Is Network Microsegmentation?

Microsegmentation divides your network into isolated security zones at the workload level. Unlike traditional VLANs or security groups that operate at the subnet or VM level, microsegmentation enforces policies per individual process, container, or pod.

Key capabilities of a microsegmentation platform include:
- **Workload-level policies**: Allow/deny traffic between specific containers or pods
- **Application-aware filtering**: Layer 7 rules based on HTTP paths, DNS queries, or process IDs
- **Automatic policy discovery**: Observing traffic patterns to suggest least-privilege rules
- **Policy enforcement**: Dropping unauthorized traffic at the kernel level
- **Visibility and auditing**: Logging all allowed and denied connections for compliance

Without microsegmentation, a compromised container in your web frontend tier can freely scan and attack your database tier. Proper segmentation limits the blast radius of any single compromise.

## Comparison: Microsegmentation Platforms

| Feature | Cilium Network Policies | AccuKnox | Calico Network Policies |
|---------|------------------------|----------|------------------------|
| **Enforcement Engine** | eBPF (Linux kernel) | eBPF + iptables | iptables / eBPF |
| **Layer 7 Filtering** | Yes (HTTP, DNS, Kafka, gRPC) | Yes | Limited (iptables mode) |
| **Policy Discovery** | Hubble observability | Auto-discovery + CIS benchmarks | Manual |
| **Multi-Cluster** | ClusterMesh | Yes (multi-cloud) | Global network policy |
| **Service Mesh** | Built-in mTLS | Integrates with Istio | No |
| **Host Firewall** | Yes | Yes | Yes |
| **Complexity** | Medium | Medium-High | Medium |
| **GitHub Stars** | 24,300+ | Discovery engine 1,000+ | 13,500+ |
| **Best For** | K8s-native with L7 policies | Policy automation + compliance | Production-proven reliability |

## 1. Cilium Network Policies (eBPF-Based)

Cilium uses eBPF (Extended Berkeley Packet Filter) to enforce network policies directly in the Linux kernel — without iptables rules. This provides faster packet processing and enables Layer 7 filtering for HTTP, DNS, Kafka, and gRPC protocols.

### Docker Compose Setup (Single-Node Test Lab)

```yaml
version: "3.8"

services:
  cilium-operator:
    image: quay.io/cilium/operator-generic:latest
    container_name: cilium-operator
    network_mode: "host"
    cap_add:
      - NET_ADMIN
      - SYS_ADMIN
    command:
      - "--config-dir=/etc/cilium"
      - "--debug"
    volumes:
      - /var/run/cilium:/var/run/cilium
      - ./cilium-operator-config:/etc/cilium:ro
    restart: unless-stopped

  hubble-relay:
    image: quay.io/cilium/hubble-relay:latest
    container_name: hubble-relay
    ports:
      - "4245:4245"
    volumes:
      - /var/run/cilium:/var/run/cilium
    command:
      - "--peer-unix-socket=/var/run/cilium/hubble.sock"
      - "--listen-address=0.0.0.0:4245"
    restart: unless-stopped

  hubble-ui:
    image: quay.io/cilium/hubble-ui:latest
    container_name: hubble-ui
    ports:
      - "12000:8081"
    restart: unless-stopped
```

**Network Policy Example** — restrict frontend to only talk to backend on port 8080:
```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: frontend-to-backend
spec:
  endpointSelector:
    matchLabels:
      app: frontend
  ingress:
    - fromEndpoints:
        - matchLabels:
            app: backend
      toPorts:
        - ports:
            - port: "8080"
              protocol: TCP
  egress:
    - toEndpoints:
        - matchLabels:
            app: backend
      toPorts:
        - ports:
            - port: "8080"
              protocol: TCP
```

**Layer 7 Policy** — allow only GET requests to `/api/v1/*`:
```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: l7-http-policy
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
    - fromEndpoints:
        - matchLabels:
            app: frontend
      toPorts:
        - ports:
            - port: "8080"
              protocol: TCP
          rules:
            http:
              - method: GET
                path: "/api/v1/.*"
```

Cilium's Hubble observability platform provides real-time service dependency maps, flow logs, and policy enforcement visibility — essential for understanding which workloads communicate with each other.

## 2. AccuKnox (Policy Discovery + Enforcement)

AccuKnox focuses on automated policy discovery — observing your workloads' actual traffic patterns and generating least-privilege security policies. It combines Cilium's eBPF enforcement with an intelligent policy engine that suggests rules based on observed behavior and CIS benchmarks.

### Docker Compose Setup

```yaml
version: "3.8"

services:
  accuknox-agent:
    image: public.ecr.aws/accuknox/knox-agent:latest
    container_name: accuknox-agent
    network_mode: "host"
    cap_add:
      - NET_ADMIN
      - SYS_ADMIN
      - SYS_PTRACE
    volumes:
      - /sys/kernel/security:/sys/kernel/security
      - /sys/fs/bpf:/sys/fs/bpf
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - KNOX_POLICY_ENGINE=auto
      - KNOX_ENFORCEMENT_MODE=monitor
    restart: unless-stopped

  accuknox-ui:
    image: public.ecr.aws/accuknox/knox-ui:latest
    container_name: accuknox-ui
    ports:
      - "30001:80"
    environment:
      - BACKEND_URL=http://accuknox-backend:8080
    depends_on:
      - accuknox-backend
    restart: unless-stopped

  accuknox-backend:
    image: public.ecr.aws/accuknox/knox-backend:latest
    container_name: accuknox-backend
    ports:
      - "8080:8080"
    volumes:
      - accuknox-data:/data
    restart: unless-stopped

volumes:
  accuknox-data:
```

The AccuKnox agent runs in "monitor mode" initially, observing traffic without enforcing policies. After a discovery period (typically 24-48 hours), it generates recommended policies that you can review and apply. This prevents accidentally blocking legitimate traffic.

## 3. Calico Network Policies

Calico is the most widely adopted network policy engine for Kubernetes. It supports both traditional iptables-based enforcement and modern eBPF dataplane. Calico's strength lies in its maturity, extensive documentation, and integration with major cloud platforms.

### Docker Compose Setup

```yaml
version: "3.8"

services:
  calico-node:
    image: docker.io/calico/node:latest
    container_name: calico-node
    network_mode: "host"
    cap_add:
      - NET_ADMIN
      - SYS_ADMIN
      - NET_RAW
    environment:
      - CALICO_NETWORKING_BACKEND=bird
      - FELIX_IPTABLESBACKEND=Auto
      - FELIX_PROMETHEUSMETRICSENABLED=true
      - DATASTORE_TYPE=kubernetes
    volumes:
      - /lib/modules:/lib/modules
      - /var/run/calico:/var/run/calico
    restart: unless-stopped

  calico-kube-controllers:
    image: docker.io/calico/kube-controllers:latest
    container_name: calico-controllers
    environment:
      - DATASTORE_TYPE=kubernetes
    restart: unless-stopped
```

**Calico GlobalNetworkPolicy** — deny all inter-namespace traffic by default:
```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default-deny-cross-namespace
spec:
  selector: "has(projectcalico.org/namespace)"
  types:
    - Ingress
    - Egress
  ingress:
    - action: Allow
      source:
        namespaceSelector: projectcalico.org/name == "kube-system"
  egress:
    - action: Allow
      destination:
        namespaceSelector: projectcalico.org/name == "kube-system"
```

Calico's BGP-based routing also provides high-performance pod-to-pod networking without overlay networks, reducing latency compared to VXLAN-based CNI plugins.

## Choosing the Right Microsegmentation Platform

**Use Cilium when:**
- You need Layer 7 filtering (HTTP, DNS, Kafka)
- eBPF observability (Hubble) is important for debugging
- You want built-in mTLS without a separate service mesh
- Your team is comfortable with Kubernetes-native tooling

**Use AccuKnox when:**
- You want automated policy discovery to avoid manual rule writing
- Compliance (CIS benchmarks) is a requirement
- You operate mixed environments (K8s + VMs + bare metal)
- You need a visual policy management interface

**Use Calico when:**
- You need battle-tested, production-proven network policies
- BGP-based routing (no overlay) is preferred
- You operate on-premises bare-metal Kubernetes clusters
- Your team has existing iptables/networking expertise

## Why Self-Host Your Microsegmentation Platform?

Network security is not an area where you want to rely on cloud-provider-specific tools. When you self-host microsegmentation, your security policies travel with your workloads — whether they run on-premises, in AWS, or at the edge. This portability is critical for hybrid cloud strategies and multi-cloud deployments.

Self-hosted microsegmentation also gives you full visibility into every allowed and denied connection. Cloud-native security groups are opaque — you see the final allow/deny decision but not the enforcement path. eBPF-based platforms like Cilium provide kernel-level visibility into exactly which policy matched each packet, which is invaluable for incident response and compliance auditing.

The cost argument is equally compelling. Managed container security platforms charge per node or per workload. At 500+ nodes, these costs can exceed $10,000/year. Self-hosted microsegmentation runs on the same infrastructure as your workloads with minimal overhead.

For foundational network policies, see our [Calico vs Cilium vs kube-router guide](../2026-04-26-calico-vs-cilium-vs-kube-router-kubernetes-network-policies-guide-2026/). If you need deeper eBPF visibility, our [XDP/eBPF network firewalls guide](../2026-05-13-self-hosted-xdp-ebpf-network-firewalls-xdp-tools-bcc-cilium-guide/) covers packet-level filtering. For multi-cluster connectivity, check our [Kubernetes multi-cluster service mesh guide](../2026-05-16-self-hosted-kubernetes-multi-cluster-service-connectivity-cilium-clustermesh-istio-linkerd-guide/).

## FAQ

### What is the difference between network policies and microsegmentation?

Network policies define which traffic is allowed between workloads. Microsegmentation is the broader practice of dividing your network into isolated security zones — of which network policies are the enforcement mechanism. Microsegmentation also includes visibility, policy discovery, compliance reporting, and incident response capabilities.

### Does eBPF-based microsegmentation require a specific kernel version?

Yes. eBPF features used by Cilium require Linux kernel 4.19 or later for basic functionality, and 5.10+ for advanced features like socket-level filtering. Most modern distributions (Ubuntu 22.04, RHEL 9, Debian 12) ship with compatible kernels.

### Can I run microsegmentation on non-Kubernetes workloads?

Cilium and AccuKnox both support non-Kubernetes environments. Cilium can run in "host mode" to protect VMs and bare-metal servers. AccuKnox works with Docker containers and traditional Linux hosts. Calico supports VMs via its BGP integration but requires manual configuration.

### How does microsegmentation affect network performance?

eBPF-based enforcement (Cilium, AccuKnox) adds negligible overhead — typically under 1 microsecond per packet. iptables-based enforcement (Calico in iptables mode) has slightly higher latency due to rule chain traversal. At scale, eBPF consistently outperforms iptables because it avoids linear rule matching.

### How do I migrate from permissive to enforcing mode safely?

Start with all policies in "log" or "monitor" mode. Observe traffic patterns for 1-2 weeks to understand baseline communication. Generate least-privilege policies from observed traffic. Apply them in monitor mode first, verify no legitimate traffic is flagged, then switch to enforcing mode. Both AccuKnox and Cilium support this workflow natively.

### What happens to existing connections when a policy is updated?

With eBPF-based enforcement, policy updates are applied atomically at the kernel level — existing connections are not dropped unless the new policy explicitly blocks them. With iptables-based enforcement, rule updates may cause brief connection resets during the reload cycle.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Microsegmentation: Container Network Security Platforms in 2026",
  "description": "Compare Cilium, AccuKnox, and Calico for container network microsegmentation. eBPF-based security policies with Docker Compose deployment guides.",
  "datePublished": "2026-05-17",
  "dateModified": "2026-05-17",
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
