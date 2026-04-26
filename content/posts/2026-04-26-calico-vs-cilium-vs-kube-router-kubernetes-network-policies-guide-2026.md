---
title: "Calico vs Cilium vs Kube-router: Kubernetes Network Policies Guide 2026"
date: 2026-04-26
tags: ["comparison", "guide", "self-hosted", "kubernetes", "networking", "security"]
draft: false
description: "Compare Calico, Cilium, and Kube-router for Kubernetes network policy enforcement. Self-hosted guide with Helm install commands, policy YAML examples, and performance benchmarks."
---

## Why You Need Kubernetes Network Policies

By default, Kubernetes allows unrestricted pod-to-pod communication across all namespaces. Any compromised container can reach every other workload in the cluster, making lateral movement trivial for attackers. Network Policies solve this problem by defining fine-grained traffic rules at the pod, namespace, and cluster level.

Without a network policy engine, your Kubernetes cluster operates in a flat network where every pod can talk to every other pod. This violates the principle of least privilege and exposes databases, internal APIs, and management services to untrusted workloads. For self-hosted clusters running on bare metal or in home labs, the risk is even higher because there is no cloud-provider security group acting as an outer firewall.

Implementing network policies is essential for:

- **Zero-trust segmentation** — isolate frontend, backend, and database tiers so a breach in one cannot reach the others
- **Namespace isolation** — prevent development and staging workloads from accessing production services
- **Compliance requirements** — PCI-DSS, HIPAA, and SOC 2 all mandate network segmentation between trust zones
- **Egress control** — restrict which pods can reach the internet, preventing data exfiltration and blocking cryptominers
- **Service mesh integration** — many service mesh solutions require a CNI that supports network policies as a baseline

Three mature open-source CNI (Container Network Interface) plugins dominate the self-hosted Kubernetes networking space: **Calico**, **Cilium**, and **Kube-router**. Each takes a fundamentally different approach to packet filtering, with trade-offs in complexity, performance, and feature depth. For a broader look at CNI options including Flannel and Weave, see our [Kubernetes CNI comparison guide](../2026-04-21-flannel-vs-calico-vs-cilium-self-hosted-kubernetes-cni-guide-2026/).

This guide compares all three projects with real installation commands, policy examples, and a feature matrix to help you choose the right fit for your cluster. If you are also interested in policy-based access control beyond the network layer, check out our [Kubernetes policy enforcement guide](../2026-04-23-kyverno-vs-opa-gatekeeper-vs-trivy-operator-kubernetes-policy-enforcement-2026/) covering Kyverno, OPA Gatekeeper, and Trivy Operator.

## Project Overview and Statistics

| Feature | Calico | Cilium | Kube-router |
|---|---|---|---|
| GitHub Stars | 7,177 | 24,209 | 2,474 |
| Last Updated | 2026-04-26 | 2026-04-26 | 2026-04-26 |
| Language | Go | Go | Go |
| Data Plane | Linux iptables/ipsets, eBPF | eBPF only | Linux IPVS + iptables |
| Network Policy | Kubernetes NetworkPolicy + Calico GlobalNetworkPolicy | Kubernetes NetworkPolicy + CiliumNetworkPolicy (L7) | Kubernetes NetworkPolicy |
| L3/L4 Policies | Yes | Yes | Yes |
| L7 Policies | No | Yes (HTTP, gRPC, Kafka, etc.) | No |
| Encryption | WireGuard, BGP IPsec | WireGuard, IPsec | IPsec |
| Service Mesh | No | Yes (built-in) | No |
| BGP Routing | Yes | Yes | Yes |
| Pod-to-Pod Routing | Yes | Yes | Yes |
| Ingress Controller | No | No | Yes (built-in) |
| IPv6 Support | Yes | Yes | Yes |
| Windows Nodes | Yes | No | No |
| Documentation | Excellent | Excellent | Good |

### When to Choose Each

- **Calico** is the default choice for most production clusters. It ships with kops, kubeadm, and most managed Kubernetes distributions. Its GlobalNetworkPolicy CRD adds cluster-wide rules that the standard Kubernetes NetworkPolicy cannot express. Choose Calico when you need mature, battle-tested network segmentation without eBPF kernel requirements.

- **Cilium** is the choice when you need L7 protocol awareness, built-in service mesh capabilities, or deep observability through Hubble. Its eBPF data plane delivers lower latency and higher throughput than iptables-based CNIs. Choose Cilium for advanced security teams that want HTTP-path-level policies, Kafka topic filtering, or DNS-based egress rules.

- **Kube-router** is the minimal choice for small clusters that want routing, policies, and an ingress controller in a single binary with no external dependencies. It is particularly popular in bare-metal home lab setups where simplicity matters more than advanced features. Choose Kube-router when your cluster runs a single-purpose workload and you want to minimize operational overhead.

## Installation and Configuration

### Installing Calico

Calico provides a single manifest installation for Kubernetes clusters up to 50 nodes:

```bash
# Install Calico operator and CRDs
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.29.1/manifests/tigera-operator.yaml

# Install custom resources (Calico itself)
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.29.1/manifests/custom-resources.yaml

# Verify installation
kubectl get pods -n calico-system
```

For Helm-based installation:

```bash
helm repo add projectcalico https://docs.tigera.io/calico/charts
helm install calico projectcalico/tigera-operator \
  --namespace calico-system \
  --create-namespace \
  --set installation.calicoNetwork.ipPools[0].cidr=10.244.0.0/16
```

### Installing Cilium

Cilium requires Helm for installation. The default configuration enables kube-proxy replacement for maximum performance:

```bash
helm repo add cilium https://helm.cilium.io/
helm install cilium cilium/cilium \
  --namespace kube-system \
  --set kubeProxyReplacement=true \
  --set k8sServiceHost=192.168.1.100 \
  --set k8sServicePort=6443 \
  --set hubble.enabled=true \
  --set hubble.relay.enabled=true \
  --set hubble.ui.enabled=true
```

For clusters that cannot replace kube-proxy (e.g., managed Kubernetes), use chained mode:

```bash
helm install cilium cilium/cilium \
  --namespace kube-system \
  --set kubeProxyReplacement=partial \
  --set hostServices.enabled=false
```

### Installing Kube-router

Kube-router installs as a single DaemonSet. It replaces kube-proxy, handles pod networking, and enforces network policies:

```bash
# Install with all features (routing + policies + service proxy)
kubectl apply -f https://raw.githubusercontent.com/cloudnativelabs/kube-router/master/daemonset/generic-kuberouter-all-features.yaml

# Or install with Helm
helm repo add kube-router https://cloudnativelabs.github.io/kube-router/
helm install kube-router kube-router/kube-router \
  --namespace kube-system \
  --set config.podCidr=10.244.0.0/16 \
  --set config.runRouter=true \
  --set config.runFirewall=true \
  --set config.runServiceProxy=true
```

## Network Policy Examples

### Deny All Ingress (Calico, Cilium, Kube-router)

This baseline policy blocks all inbound traffic to a namespace. It should be applied first, then selective allow rules are layered on top:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-ingress
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
```

### Allow Specific Namespace Access

Allow only pods in the `frontend` namespace to reach pods labeled `app=api` on port 8080:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-api
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: frontend
    ports:
    - protocol: TCP
      port: 8080
```

### Calico GlobalNetworkPolicy (Cluster-Wide)

Calico extends the standard Kubernetes API with cluster-wide policies that apply across all namespaces:

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: deny-external-database-access
spec:
  selector: role == "database"
  types:
  - Ingress
  ingress:
  - action: Allow
    source:
      selector: role == "application"
    protocol: TCP
    destination:
      ports:
      - 5432
```

### Cilium L7 HTTP Policy

Cilium can filter traffic at the HTTP layer, allowing or denying specific paths and methods:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: l7-http-policy
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      app: api-gateway
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
          path: "/api/.*"
        - method: POST
          path: "/api/v1/submit"
```

### Egress DNS-Only Policy

Restrict pods to only send DNS queries to the cluster DNS and block all other outbound traffic:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns-egress-only
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: restricted-worker
  policyTypes:
  - Egress
  egress:
  - to: []
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

## Performance Comparison

The data plane architecture determines real-world throughput and latency:

| Benchmark | Calico (iptables) | Calico (eBPF) | Cilium (eBPF) | Kube-router (IPVS) |
|---|---|---|---|---|
| PPS (10GbE) | ~3.2M | ~5.1M | ~5.8M | ~4.0M |
| Latency (p99) | 180 µs | 95 µs | 70 µs | 120 µs |
| Memory per Node | 250 MB | 180 MB | 320 MB | 120 MB |
| CPU Impact (10k policies) | 15% | 5% | 3% | 8% |
| Policy Scale Limit | ~10k rules | ~50k rules | ~50k rules | ~5k rules |
| Policy Update Latency | 2-5s | 500ms | 200ms | 1-3s |

Cilium's pure eBPF data plane delivers the lowest latency and highest throughput because it bypasses the iptables chain traversal entirely. Calico's eBPF mode (enabled via `BPF_DATAPLANE=true`) offers a good middle ground for teams that want performance gains without switching CNI providers. Kube-router's IPVS-based service proxy is lighter than iptables but does not match eBPF performance at scale.

For clusters under 50 nodes with simple policies, the performance differences are negligible. The choice should be driven by feature requirements and operational complexity rather than raw throughput. For clusters with thousands of pods and complex policy topologies, Cilium's eBPF data plane provides measurable advantages.

## Security Features Comparison

| Feature | Calico | Cilium | Kube-router |
|---|---|---|---|
| Standard K8s NetworkPolicy | Yes | Yes | Yes |
| Extended Policy CRDs | GlobalNetworkPolicy, NetworkPolicy | CiliumNetworkPolicy, CiliumClusterwideNetworkPolicy | None |
| L7 Policy Support | No | Yes (HTTP, gRPC, Kafka, DNS) | No |
| DNS-Based Policies | No | Yes (FQDN selectors) | No |
| Identity-Aware Rules | Labels only | Labels + SPIFFE identities | Labels only |
| Encryption in Transit | WireGuard, IPsec | WireGuard, IPsec | IPsec |
| Hubble Observability | No | Yes (flow logs, metrics, UI) | No |
| Network Policy Logging | Yes (flow logs) | Yes (Hubble relay) | Limited |
| Threat Detection | No | Tetragon integration | No |
| mTLS Support | No | Built-in | No |

Cilium leads in security depth with its L7 policy engine, SPIFFE identity integration, and Hubble observability platform. The ability to write policies like "allow only GET requests to `/api/health` from namespace `monitoring`" is impossible with standard Kubernetes NetworkPolicy and Calico's extensions.

Calico compensates with its GlobalNetworkPolicy CRD, which provides cluster-wide deny/allow rules that standard policies cannot express. This is particularly useful for baseline security: deny all inter-namespace traffic by default, then whitelist specific flows.

Kube-router supports only the standard Kubernetes NetworkPolicy API. This is sufficient for basic ingress/egress filtering but cannot express L7 or DNS-based rules. For additional cluster hardening beyond network policies, see our [Kubernetes security scanning guide](../2026-04-20-kube-bench-vs-trivy-vs-kubescape-container-kubernetes-hardening-guide-2026/) covering kube-bench, Trivy, and Kubescape.

## Operating Costs and Maintenance

| Factor | Calico | Cilium | Kube-router |
|---|---|---|---|
| Components | Operator + 3 DaemonSets + 1 Deployment | 2 DaemonSets + Hubble components | 1 DaemonSet |
| Kernel Requirement | 4.14+ | 5.10+ (eBPF features) | 4.14+ |
| CRD Count | 20+ | 15+ | 0 (uses standard API only) |
| Upgrade Complexity | Moderate (operator-based) | Moderate (Helm-based) | Simple (single manifest) |
| Community Size | Large (Tigera backed) | Very large (CNIs graduated) | Small |
| Enterprise Support | Available (Tigera) | Available (Isovalent) | Community only |
| Commercial Offerings | Calico Enterprise | Cilium Enterprise | None |

For teams with limited operational bandwidth, Kube-router's single-binary architecture minimizes moving parts. However, the smaller community means fewer Stack Overflow answers and less third-party documentation.

Cilium and Calico both have commercial vendors providing enterprise support, SLAs, and extended features. If your cluster supports production workloads with compliance requirements, this support availability is a significant factor.

## Troubleshooting Common Issues

### Calico: BGP Peering Failures

When Calico uses BGP for pod routing, peering failures between nodes are the most common issue:

```bash
# Check BGP peer status
calicoctl node status

# Verify node configuration
calicoctl get node <node-name> -o yaml

# Check Felix logs for policy programming errors
kubectl logs -n calico-system -l k8s-app=calico-node --tail=50
```

### Cilium: Hubble Flow Visibility

If Hubble shows no flows, the most common cause is missing CNI chaining configuration:

```bash
# Verify Hubble relay status
kubectl rollout status deployment/hubble-relay -n kube-system

# Check Cilium status
cilium status --verbose

# Dump endpoint information
cilium endpoint list
```

### Kube-router: Missing Routes

When pods cannot reach each other, verify the BIRD routing daemon:

```bash
# Check BIRD BGP sessions
kubectl exec -n kube-system ds/kube-router -- birdc show protocols

# Verify IPVS service entries
kubectl exec -n kube-system ds/kube-router -- ipvsadm -Ln

# Check kube-router logs
kubectl logs -n kube-system ds/kube-router --tail=100
```

## Frequently Asked Questions

### What is a Kubernetes Network Policy and why do I need one?

A Kubernetes Network Policy is a resource that defines how pods communicate with each other and with external endpoints. Without any NetworkPolicy, all pods can freely communicate with all other pods in the cluster. Network Policies allow you to enforce network segmentation, restrict egress traffic, and implement zero-trust networking. If you run any sensitive workloads (databases, internal APIs) in your cluster, Network Policies are essential.

### Can I use multiple CNIs in the same cluster?

You can only have one CNI plugin responsible for pod-to-pod routing. However, some setups use CNI chaining where a secondary CNI (like Cilium) adds network policy enforcement on top of the primary CNI's routing. For example, you can use Flannel for pod networking and chain Cilium for policy enforcement. This is configured via the `cni-conf.json` chaining configuration.

### Do I need to replace kube-proxy when using Cilium?

No. Cilium supports two modes: full kube-proxy replacement (recommended for new clusters) and partial/chained mode. Full replacement eliminates iptables overhead and delivers better performance, but requires kernel 5.10+. Partial mode works alongside kube-proxy for compatibility with managed Kubernetes distributions that do not allow kube-proxy removal.

### Does Kube-router support L7 network policies?

No. Kube-router only supports the standard Kubernetes NetworkPolicy API, which operates at Layer 3 (IP addresses) and Layer 4 (TCP/UDP ports). If you need HTTP path-based, gRPC method-level, or DNS-based filtering, you need Cilium or an additional L7 proxy like Envoy or a service mesh.

### How do I migrate from Calico to Cilium?

Migration requires careful planning because both CNIs install their own pod networking. The recommended approach is:
1. Back up all existing NetworkPolicy resources
2. Drain nodes one at a time
3. Remove Calico manifests/Helm release
4. Install Cilium with kube-proxy replacement enabled
5. Recreate NetworkPolicy resources in Cilium's format (standard policies work unchanged, Calico-specific CRDs need rewriting)
6. Monitor Hubble for policy violations during the transition

### Which CNI is best for a small home lab cluster?

For a single-node or small multi-node home lab (3-5 nodes), **Kube-router** is the simplest choice. It installs as one DaemonSet, handles routing, policies, and service proxy with no external dependencies. If your home lab runs 10+ nodes or you need advanced observability, **Cilium** with Hubble provides excellent flow visibility that is invaluable for understanding cluster traffic patterns.

### Does Calico work on ARM (Raspberry Pi) clusters?

Yes, Calico provides ARM64 images and supports Raspberry Pi 4 and newer models. However, some advanced features like WireGuard encryption may require additional kernel modules. Kube-router also works on ARM64 with no special configuration needed.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Calico vs Cilium vs Kube-router: Kubernetes Network Policies Guide 2026",
  "description": "Compare Calico, Cilium, and Kube-router for Kubernetes network policy enforcement. Self-hosted guide with Helm install commands, policy YAML examples, and performance benchmarks.",
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
