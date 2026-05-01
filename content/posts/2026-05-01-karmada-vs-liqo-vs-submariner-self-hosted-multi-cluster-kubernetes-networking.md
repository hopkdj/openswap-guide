---
title: "Karmada vs Liqo vs Submariner — Self-Hosted Multi-Cluster Kubernetes Networking (2026)"
date: 2026-05-01T10:30:00+00:00
tags: ["kubernetes", "multi-cluster", "networking", "self-hosted", "federation", "docker"]
draft: false
---

Running Kubernetes across multiple clusters — whether for geographic distribution, cloud provider diversity, or disaster recovery — requires specialized tooling. Three open-source projects address this challenge from different angles: **Karmada** (multi-cluster orchestration), **Liqo** (seamless cluster peering), and **Submariner** (cross-cluster networking).

This guide compares their architectures, networking models, self-hosting requirements, and Docker-based deployment approaches.

## Quick Comparison

| Feature | Karmada | Liqo | Submariner |
|---|---|---|---|
| **GitHub Stars** | 5,441 | 1,437 | 2,638 |
| **Language** | Go | Go | Go |
| **Primary Focus** | Multi-cluster orchestration & scheduling | Cluster peering & resource sharing | Cross-cluster networking |
| **Cluster Federation** | ✅ Full federation control plane | ✅ Peer-to-peer cluster linking | ❌ Networking only |
| **Cross-Cluster Pod Scheduling** | ✅ Propagation policies | ✅ Offloading to remote clusters | ❌ |
| **Service Discovery** | ✅ MCS (Multi-Cluster Services) | ✅ Automatic service import | ✅ Service export/import |
| **Pod-to-Pod Connectivity** | ❌ (requires CNI tunnel) | ✅ Full L3 connectivity | ✅ Full L3 connectivity |
| **Supported CNI** | Any | Any (creates overlay) | Any (creates IPsec/WireGuard tunnel) |
| **Control Plane** | Centralized (hosted control plane) | Distributed (each cluster is equal) | Distributed (broker + agents) |
| **Last Updated** | 2026-04-30 | 2026-04-29 | 2026-04-29 |
| **Best For** | Centralized multi-cluster management, app propagation | Transparent resource sharing across clusters | Secure cross-cluster pod/service networking |

## Karmada — Centralized Multi-Cluster Orchestration

[Karmada](https://github.com/karmada-io/karmada) (Kubernetes Armada) is a multi-cluster orchestration system that provides a unified control plane for managing applications across multiple Kubernetes clusters. It is a CNCF sandbox project, originally developed by Huawei.

**Key strengths:**
- Centralized control plane with a single API for all cluster operations
- Policy-based workload propagation — deploy to specific clusters or all clusters
- Automatic failover — if one cluster goes down, workloads are rescheduled to healthy clusters
- Supports heterogeneous clusters (different K8s versions, cloud providers, on-premise)

**Karmada installation with clusteradm:**

```bash
# Install Karmada CLI
curl -s https://raw.githubusercontent.com/karmada-io/karmada/master/hack/install-cli.sh | bash

# Deploy Karmada control plane on your host cluster
clusteradm init --wait

# Join member clusters
clusteradm join --hub-token <token> --hub-apiserver <api-server> --cluster-name cluster2
```

**Karmada propagation policy example:**

```yaml
apiVersion: policy.karmada.io/v1alpha1
kind: PropagationPolicy
metadata:
  name: nginx-propagation
spec:
  resourceSelectors:
    - apiVersion: apps/v1
      kind: Deployment
      name: nginx
  placement:
    clusterAffinity:
      clusterNames:
        - cluster1
        - cluster2
    replicaScheduling:
      replicaDivisionPreference: Weighted
      replicaSchedulingType: Divided
```

Karmada's deployment model uses `clusteradm` rather than Docker Compose, as it is designed to run as a control plane within an existing Kubernetes cluster. The control plane components (karmada-apiserver, karmada-controller-manager, karmada-scheduler) are deployed as pods in the `karmada-system` namespace.

## Liqo — Seamless Cluster Peering

[Liqo](https://github.com/liqotech/liqo) enables dynamic, seamless peering between Kubernetes clusters, allowing pods to run across cluster boundaries as if they were in a single cluster. It creates a virtual node in each peer cluster that represents the remote cluster's resources.

**Key strengths:**
- Transparent resource sharing — pods can be scheduled on remote cluster nodes
- Automatic network connectivity between peered clusters via tunnel
- Each cluster retains full autonomy — peering is bidirectional and opt-in
- Supports offloading specific namespaces or workloads to remote clusters

**Liqo Helm-based deployment:**

```bash
# Add Liqo repository
helm repo add liqo https://liqotech.github.io/liqo
helm repo update

# Install Liqo on the first cluster
helm install liqo liqo/liqo --set dashboard.enable=true \
  --create-namespace --namespace liqo

# Get the peering invitation from the second cluster
liqoctl generate peer-command --only-output-url

# On the second cluster, accept the peering
liqoctl out-of-band peering accept --auth-url <invitation-url>
```

**Liqo offloading policy example:**

```yaml
apiVersion: sharing.liqo.io/v1beta1
kind: NamespaceOffloading
metadata:
  name: my-app-offloading
  namespace: my-app
spec:
  clusterSelector:
    matchLabels: {}
  podOffloadingPolicy: LocalAndRemote
```

Liqo's architecture creates a virtual kubelet in each cluster that represents the remote cluster's compute resources. This means standard Kubernetes schedulers can place pods on remote nodes without any special configuration.

## Submariner — Cross-Cluster Networking

[Submariner](https://github.com/submariner-io/submariner) focuses exclusively on connecting Kubernetes clusters at the network layer. It establishes secure tunnels (IPsec or WireGuard) between clusters, enabling pod-to-pod and service-to-service communication across cluster boundaries.

**Key strengths:**
- Simple, focused networking solution — does one thing well
- IPsec and WireGuard tunnel options for encrypted cross-cluster traffic
- Service discovery across clusters via the Multi-Cluster Services API
- Works with any CNI plugin (Calico, Cilium, Flannel, etc.)

**Submariner deployment with subctl:**

```bash
# Install the submariner CLI
curl -Ls https://get.submariner.io | bash

# Join two clusters to the Submariner broker
subctl join --broker-info <broker-info.tar> cluster1
subctl join --broker-info <broker-info.tar> cluster2

# Export a service for cross-cluster access
subctl export svc --namespace default my-service
```

**Submariner service export example:**

```yaml
apiVersion: multicluster.x-k8s.io/v1alpha1
kind: ServiceExport
metadata:
  name: my-service
  namespace: default
```

Submariner uses a broker cluster (or a hosted broker) to coordinate connection information between member clusters. Each cluster runs a Submariner gateway pod that handles tunnel establishment and traffic routing.

## Architecture Comparison

### Control Plane Model

**Karmada** uses a centralized control plane model. All multi-cluster decisions (scheduling, propagation, failover) flow through the Karmada control plane. This provides a single source of truth but introduces a central point of dependency.

**Liqo** uses a distributed, peer-to-peer model. Each cluster runs its own Liqo control plane and negotiates peering directly with other clusters. There is no central coordinator.

**Submariner** uses a lightweight broker model. The broker stores connection metadata (certificates, endpoint addresses) but does not participate in data plane traffic. Each cluster runs its own gateway independently.

### Networking Approach

| Aspect | Karmada | Liqo | Submariner |
|---|---|---|---|
| **Pod-to-Pod** | Requires external CNI tunnel | ✅ Built-in overlay tunnel | ✅ Built-in IPsec/WireGuard tunnel |
| **Service Discovery** | MCS API compliant | Automatic service import | Service export/import API |
| **Encryption** | Depends on CNI | WireGuard (built-in) | IPsec or WireGuard |
| **Cross-Cluster DNS** | CoreDNS plugin | Automatic DNS resolution | Lighthouse DNS |
| **NAT Traversal** | ❌ | ✅ | ✅ |
| **Gateway HA** | Built-in (etcd) | Built-in | Built-in (leader election) |

### When to Choose Each

### Choose Karmada When:
- You need centralized management of applications across 3+ clusters
- You want policy-based deployment control (deploy to specific regions, weighted distribution)
- You need automatic failover between clusters for disaster recovery
- You manage heterogeneous clusters with different Kubernetes distributions

### Choose Liqo When:
- You want seamless resource sharing between 2-3 clusters
- You need pods to be scheduled transparently across cluster boundaries
- You prefer a peer-to-peer architecture without a central control plane
- You want to offload burst workloads to partner or edge clusters

### Choose Submariner When:
- You only need cross-cluster networking (not orchestration or scheduling)
- You want to keep your existing cluster management tools unchanged
- You need strong encryption (IPsec) for inter-cluster traffic
- You're connecting clusters across different networks (on-premise to cloud)

## Why Multi-Cluster Kubernetes?

Running Kubernetes across multiple clusters provides resilience, compliance, and performance benefits that a single cluster cannot match:

- **Geographic distribution** — Serve users from clusters in their region for lower latency
- **Cloud provider diversity** — Avoid single-provider dependency by distributing across AWS, GCP, and on-premise
- **Disaster recovery** — If one cluster or data center fails, workloads continue on other clusters
- **Regulatory compliance** — Keep data processing within specific geographic boundaries (GDPR, data residency)
- **Scalability** — Distribute workloads across clusters when a single cluster reaches capacity limits

For Kubernetes CNI networking within a single cluster, see our [Flannel vs Calico vs Cilium comparison](../2026-04-21-flannel-vs-calico-vs-cilium-self-hosted-kubernetes-cni-guide-2026/). If you need multi-cluster ingress routing, our [Traefik vs NGINX Ingress vs Contour guide](../2026-04-22-traefik-vs-nginx-ingress-vs-contour-kubernetes-ingress-controller-guide-2026/) covers the options. For batch workloads across clusters, our [Volcano vs Yunikorn vs Kueue guide](../volcano-vs-yunikorn-vs-kueue-kubernetes-batch-scheduler-guide-2026/) covers scheduling priorities.

## FAQ

### Can I use Karmada, Liqo, and Submariner together?
Yes, they serve different purposes and can be complementary. Karmada handles orchestration and workload propagation, Liqo manages resource sharing and cluster peering, and Submariner provides the underlying network connectivity. In practice, many teams choose one primary tool based on their needs rather than combining all three.

### Does Submariner support more than two clusters?
Yes. Submariner supports mesh connectivity across multiple clusters (tested up to 100+). Each cluster's gateway establishes tunnels to every other cluster's gateway, creating a full mesh topology.

### What happens if the Karmada control plane goes down?
If the Karmada control plane becomes unavailable, existing workloads on member clusters continue running normally. However, new deployments, scaling operations, and failover actions cannot be initiated until the control plane recovers. This is why Karmada recommends running its control plane on a highly available Kubernetes cluster with etcd replication.

### Does Liqo require the clusters to be on the same network?
No. Liqo supports cross-network peering, including clusters in different cloud providers or on-premise data centers. It automatically handles NAT traversal and creates encrypted tunnels between peered clusters.

### How does Submariner handle IP address conflicts between clusters?
Submariner detects overlapping pod and service CIDRs and provides configuration options to remap IP addresses. For new deployments, it is recommended to use non-overlapping CIDRs across clusters to avoid complications.

### Can I migrate from a single cluster to multi-cluster without downtime?
With Karmada, you can gradually propagate workloads from a single cluster to multiple clusters using its propagation policies. With Liqo, you can peer a new cluster and begin offloading workloads incrementally. Submariner can be added to existing clusters without disrupting running workloads — the networking layer is transparent to applications.

### What is the resource overhead of each tool?
- **Karmada**: Control plane components consume ~500MB-1GB RAM per cluster, plus etcd storage for cluster state.
- **Liqo**: Each cluster runs a Liqo control plane (~200-400MB RAM) plus a virtual kubelet. Network tunnel overhead is minimal.
- **Submariner**: Gateway pods consume ~100-200MB RAM per cluster. The broker requires minimal resources (~50MB).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Karmada vs Liqo vs Submariner — Self-Hosted Multi-Cluster Kubernetes Networking (2026)",
  "description": "Compare three self-hosted multi-cluster Kubernetes tools: Karmada, Liqo, and Submariner. Covers orchestration, networking, and deployment patterns.",
  "datePublished": "2026-05-01",
  "dateModified": "2026-05-01",
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
