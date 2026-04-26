---
title: "MetalLB vs kube-vip vs Cilium LB: Bare-Metal Kubernetes Load Balancer Guide 2026"
date: 2026-04-26
tags: ["comparison", "guide", "kubernetes", "load-balancer", "bare-metal", "self-hosted"]
draft: false
description: "Compare MetalLB, kube-vip, and Cilium LoadBalancer for bare-metal Kubernetes clusters. Includes installation guides, BGP vs Layer 2 configuration, and production best practices."
---

Running Kubernetes on bare metal or self-hosted infrastructure means you don't have a cloud provider's native load balancer. When you deploy a `Service` of type `LoadBalancer`, it stays in `Pending` state forever unless you install a load balancer controller. This guide compares the three leading open-source solutions: **MetalLB**, **kube-vip**, and **Cilium LoadBalancer**.

Each tool solves the same problem but with different architectures, protocols, and operational trade-offs. Whether you're running a home lab, a small cluster, or production bare-metal infrastructure, this comparison will help you pick the right tool.

## Why You Need a Load Balancer for Bare-Metal Kubernetes

Cloud providers (AWS, GCP, Azure) automatically provision external IPs and load balancer hardware for Kubernetes `LoadBalancer` services. On bare metal, there's no cloud API to call — you need a software layer that:

- **Assigns external IPs** from a configurable pool to your services
- **Routes traffic** to the correct backend pods using standard protocols (BGP, ARP, NDP)
- **Handles failover** when nodes go down, reassigning IPs to healthy nodes
- **Supports health checks** to avoid sending traffic to unready pods

Without a load balancer controller, you're limited to `NodePort` services (which expose ports on every node's IP) or `Ingress` controllers (which require an external LB to route to the Ingress itself). A proper LB controller gives you dedicated IPs per service, just like in the cloud.

For related infrastructure decisions, see our [Kubernetes CNI comparison (Flannel vs Calico vs Cilium)](../2026-04-21-flannel-vs-calico-vs-cilium-self-hosted-kubernetes-cni-guide-2026/) and [bare-metal hardware monitoring guide](../2026-04-23-self-hosted-bare-metal-hardware-monitoring-ipmi-redfish-openbmc-guide-2026/).

## MetalLB: The Standard Choice

[MetalLB](https://metallb.universe.tf/) is the most widely adopted load balancer for bare-metal Kubernetes. With **8,157 GitHub stars** and active maintenance by the CNCF, it provides both Layer 2 and BGP modes using Kubernetes-native CRDs.

**GitHub stats** (as of April 2026): 8,157 stars, last updated April 26, 2026, written in Go.

### Architecture

MetalLB runs two components:

- **Controller** — a Deployment that watches for `LoadBalancer` services and assigns IPs from configured pools
- **Speaker** — a DaemonSet that runs on every node, advertising the assigned IPs via BGP or ARP/NDP

### Installation

```bash
# Install via Helm
helm repo add metallb https://metallb.github.io/metallb
helm repo update
helm install metallb metallb/metallb --namespace metallb-system --create-namespace
```

Alternatively, apply the raw manifests:

```bash
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/main/config/native/namespace.yaml
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/main/config/native/metallb.yaml
```

### Layer 2 Configuration

Layer 2 mode is the simplest to set up — it uses ARP (IPv4) or NDP (IPv6) to announce IPs. Only one node actively serves traffic at a time (leader election handles failover).

```yaml
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: default-pool
  namespace: metallb-system
spec:
  addresses:
  - 192.168.1.240-192.168.1.250
---
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: default-l2-adv
  namespace: metallb-system
spec:
  ipAddressPools:
  - default-pool
```

### BGP Configuration

BGP mode distributes traffic across all nodes simultaneously and integrates with your existing network routers.

```yaml
apiVersion: metallb.io/v1beta1
kind: BGPPeer
metadata:
  name: router-peer
  namespace: metallb-system
spec:
  peerAddress: 192.168.1.1
  peerASN: 64512
  myASN: 64513
  routerID: 192.168.1.10
---
apiVersion: metallb.io/v1beta1
kind: BGPAdvertisement
metadata:
  name: default-bgp-adv
  namespace: metallb-system
spec:
  ipAddressPools:
  - default-pool
```

## kube-vip: The Dual-Purpose Solution

[kube-vip](https://kube-vip.io/) started as a control plane HA tool (managing the Kubernetes API server VIP) but evolved to also handle `LoadBalancer` services. With **2,819 GitHub stars**, it's a lightweight alternative that can replace both keepalived and MetalLB in a single binary.

**GitHub stats** (as of April 2026): 2,819 stars, last updated April 26, 2026, written in Go.

### Architecture

kube-vip runs as a **static pod** on control plane nodes (for the control plane VIP) or as a **DaemonSet** (for LoadBalancer services). Unlike MetalLB's two-component design, kube-vip uses a single binary for both roles.

Key protocols supported:
- **ARP/NDP** — Layer 2 leader election (similar to MetalLB L2)
- **BGP** — Route advertisement to upstream routers
- **ECP** — Leader election via kube-vip's own protocol

### Installation

```bash
# Set environment variables for your cluster
export VIP=192.168.1.100
export INTERFACE=eth0
export KVVERSION=v0.8.5

# Generate the DaemonSet manifest for LoadBalancer mode
docker run --network host --rm plndr/kube-vip:$KVVERSION manifest pod \
  --interface $INTERFACE \
  --vip $VIP \
  --controlplane \
  --services \
  --arp \
  --leaderElection | kubectl apply -f -
```

### LoadBalancer Service Configuration

Once deployed, kube-vip automatically handles `LoadBalancer` services without additional CRD configuration. You just define your IP pool as an environment variable:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-lb
spec:
  type: LoadBalancer
  loadBalancerIP: 192.168.1.240
  ports:
  - port: 80
    protocol: TCP
    targetPort: 80
  selector:
    app: nginx
```

The `loadBalancerIP` field assigns a specific IP from your pre-configured range. For auto-assignment, omit the field and kube-vip will pick the next available IP.

### BGP Mode

```bash
docker run --network host --rm plndr/kube-vip:$KVVERSION manifest daemonset \
  --interface $INTERFACE \
  --vip $VIP \
  --services \
  --bgp \
  --localAS 64513 \
  --peerAS 64512 \
  --peerAddress 192.168.1.1 \
  --bgppeers 192.168.1.1@64512
```

## Cilium LoadBalancer: The eBPF-Native Approach

[Cilium](https://cilium.io/) is primarily a CNI (Container Network Interface) plugin, but its built-in **kube-proxy replacement** includes a full LoadBalancer implementation. With **24,208 GitHub stars**, Cilium is the most popular of the three — but LoadBalancer is just one feature of a much larger platform.

**GitHub stats** (as of April 2026): 24,208 stars, last updated April 26, 2026, written in Go.

### Architecture

Cilium's LoadBalancer is part of its eBPF-based dataplane. When kube-proxy replacement is enabled, Cilium programs eBPF maps directly into the kernel, bypassing iptables/IPVS entirely. This means:

- **Zero overhead** — no userspace proxy process for LB traffic
- **Direct server return** — traffic can return directly from backend pods without hairpinning through the LB node
- **Maglev consistent hashing** — deterministic load distribution across backends
- **Integrated with CNI** — no separate controller or speaker needed

### Installation

```bash
# Install Cilium with kube-proxy replacement and LoadBalancer mode
helm install cilium cilium/cilium --version 1.16.0 \
  --namespace kube-system \
  --set kubeProxyReplacement=true \
  --set k8sServiceHost=<control-plane-ip> \
  --set k8sServicePort=6443 \
  --set loadBalancer.mode=snat \
  --set loadBalancer.acceleration=native \
  --set bgpControlPlane.enabled=true
```

### BGP Configuration via Cilium

Cilium's BGP control plane uses a custom CRD to define peers and advertisements:

```yaml
apiVersion: cilium.io/v2alpha1
kind: CiliumBGPPeeringPolicy
metadata:
  name: bgp-lb-policy
spec:
  nodeSelector:
    matchLabels:
      kubernetes.io/os: linux
  virtualRouters:
  - localASN: 64513
    exportPodCIDR: false
    serviceAnnouncements:
    - enabled: true
      selectors:
      - matchExpressions:
        - key: "app"
          operator: Exists
    neighbors:
    - peerAddress: 192.168.1.1/32
      peerASN: 64512
```

### LoadBalancer IP Allocation

Cilium requires an external IP allocation mechanism (like MetalLB's `IPAddressPool` or a cloud provider simulator). You can use the `CiliumLoadBalancerIPPool` CRD:

```yaml
apiVersion: cilium.io/v2alpha1
kind: CiliumLoadBalancerIPPool
metadata:
  name: default-pool
spec:
  cidrs:
  - cidr: 192.168.1.240/29
  - cidr: 10.0.100.0/24
```

## Comparison Table

| Feature | MetalLB | kube-vip | Cilium LB |
|---|---|---|---|
| **Primary role** | Load balancer only | Control plane VIP + LB | Full CNI + LB + security |
| **GitHub stars** | 8,157 | 2,819 | 24,208 |
| **Installation** | Helm or manifests | Static pod / DaemonSet | Helm chart |
| **Layer 2 mode** | Yes (ARP/NDP) | Yes (ARP/NDP) | No (requires BGP) |
| **BGP mode** | Yes (native) | Yes (native) | Yes (via BGP CP) |
| **CRD-based config** | Yes | No (env vars / flags) | Yes |
| **ECMP support** | Yes (BGP) | Yes (BGP) | Yes (BGP + Maglev) |
| **Direct server return** | No | No | Yes (DSR mode) |
| **Requires CNI change** | No | No | Yes (replaces CNI) |
| **Kernel requirements** | Standard | Standard | 5.10+ (eBPF) |
| **High availability** | Leader election (L2) | Leader election | Distributed (eBPF) |
| **Control plane VIP** | No | Yes (built-in) | No |
| **Complexity** | Low | Low-Medium | High |

## Choosing the Right Tool

### Use MetalLB When:
- You want the simplest, most battle-tested solution
- Your cluster already has a CNI you're happy with
- You need both Layer 2 and BGP modes with CRD-based configuration
- You're running a production cluster and want CNCF-backed stability

MetalLB is the default choice for most self-hosted Kubernetes deployments. Its CRD-based configuration is clean and declarative, and the Layer 2 mode works out of the box on any network without router changes.

### Use kube-vip When:
- You need both control plane HA and LoadBalancer services in one tool
- You want to minimize the number of components running in your cluster
- You're building a cluster from scratch and haven't set up a control plane VIP yet
- You prefer configuration via environment variables and flags over CRDs

kube-vip shines in greenfield deployments where you can replace keepalived + MetalLB with a single binary. The trade-off is less granular configuration and fewer advanced features.

### Use Cilium LoadBalancer When:
- You're already using (or planning to use) Cilium as your CNI
- You need eBPF-based performance with direct server return
- You want integrated networking, security, and observability in one platform
- Your nodes run Linux kernel 5.10+ with eBPF support

Cilium's LB mode is the most performant option but comes with the highest complexity. If you're not using Cilium as your CNI, the migration cost is significant. For new clusters, however, Cilium is increasingly the default CNI choice, making its built-in LB the natural pick.

## Production Best Practices

### IP Pool Planning

Always size your IP pool larger than you think you need. A common mistake is allocating a /28 (14 usable IPs) for a cluster that will eventually run dozens of services. Start with at least a /26 (62 usable IPs):

```yaml
# MetalLB: generous IP pool
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: production-pool
  namespace: metallb-system
spec:
  addresses:
  - 192.168.1.192/26
  autoAssign: true
  avoidBuggyIPs: true
```

### BGP vs Layer 2 Decision Tree

- **Single switch / flat network** → Layer 2 is fine, simpler to operate
- **Multiple switches / routed network** → BGP is required for proper ECMP
- **Router supports BGP** → Use BGP for traffic distribution across all nodes
- **Router doesn't support BGP** → Layer 2 with failover is your only option

### Monitoring

Monitor your load balancer health with Prometheus. MetalLB exposes metrics at `:7472/metrics` (controller) and `:7472/metrics` (speaker):

```yaml
# Prometheus scrape config for MetalLB
- job_name: metallb
  kubernetes_sd_configs:
  - role: endpoints
    namespaces:
      names: [metallb-system]
  relabel_configs:
  - source_labels: [__meta_kubernetes_pod_label_app]
    regex: metallb
    action: keep
  - source_labels: [__meta_kubernetes_endpoint_port_name]
    regex: monitoring
    action: keep
```

For a comprehensive monitoring stack, see our [VictoriaMetrics vs Thanos vs Cortex comparison](../victoriametrics-vs-thanos-vs-cortex-self-hosted-metrics-storage-guide-2026/) for long-term metrics storage.

## FAQ

### Can I run MetalLB and kube-vip on the same cluster?

Technically yes, but it's not recommended. Both tools compete for the same `LoadBalancer` service IPs and will conflict. Choose one load balancer controller per cluster. If you need kube-vip for control plane HA, disable its LoadBalancer functionality (`--services=false`) and use MetalLB separately.

### Does MetalLB work with any CNI?

Yes. MetalLB operates at the service abstraction layer and is CNI-agnostic. It works with Flannel, Calico, Cilium, Weave, and any other CNI plugin. This is one of its main advantages over Cilium LoadBalancer, which requires Cilium as the CNI.

### What Linux kernel version does Cilium require?

Cilium's eBPF-based dataplane requires Linux kernel 4.19+ for basic functionality and 5.10+ for advanced features like socket-level load balancing and DSR (direct server return). Most modern distributions (Ubuntu 22.04+, Debian 12+, RHEL 9+) ship with compatible kernels.

### How does failover work in Layer 2 mode?

In Layer 2 mode, one node is elected leader for each IP address. If that node fails, the remaining nodes re-elect a new leader within seconds. During failover, there's a brief period (typically 1-3 seconds) where traffic is blackholed until the new leader starts answering ARP requests. For zero-downtime failover, use BGP mode with ECMP.

### Can I use BGP with consumer-grade routers?

Most consumer routers don't support BGP. For home lab setups, Layer 2 mode is the practical choice. If you need BGP, consider running a software router like FRR (Free Range Routing) or Bird in a container, which can peer with MetalLB's BGP speaker.

### Is kube-vip production-ready for LoadBalancer services?

Yes, kube-vip has been used in production for LoadBalancer services since v0.4.0. However, it's less feature-rich than MetalLB — no CRD-based configuration, no BGP community support, and no fine-grained IP pool management. For simple deployments it works well, but complex environments benefit from MetalLB's declarative model.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "MetalLB vs kube-vip vs Cilium LB: Bare-Metal Kubernetes Load Balancer Guide 2026",
  "description": "Compare MetalLB, kube-vip, and Cilium LoadBalancer for bare-metal Kubernetes clusters. Includes installation guides, BGP vs Layer 2 configuration, and production best practices.",
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
