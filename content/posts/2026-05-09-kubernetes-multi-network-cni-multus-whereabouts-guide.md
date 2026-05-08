---
title: "Kubernetes Multi-Network CNI: Multus vs Whereabouts vs CNI Plugins (2026)"
date: "2026-05-09"
draft: false
tags: ["kubernetes", "cni", "networking", "multus", "container-networking", "cloud-native"]
---

Running Kubernetes workloads that need more than one network interface — such as DPDK packet processing, SR-IOV virtual functions, or isolated storage networks — requires a CNI solution beyond the standard single-network setup. While default CNIs like Calico, Cilium, and Flannel handle pod-to-pod communication, they do not support attaching multiple interfaces to a single pod.

This guide compares the three primary open-source tools for Kubernetes multi-networking: **Multus CNI**, **Whereabouts IPAM**, and the **CNI Plugins** reference collection.

## What Is a CNI Meta-Plugin?

The Container Network Interface (CNI) is a specification for configuring network interfaces in Linux containers. A standard CNI plugin (like Calico or Flannel) attaches exactly one network interface per pod.

Multus CNI is a **meta-plugin** — it does not provide networking itself. Instead, it delegates to other CNI plugins, allowing a pod to have multiple network interfaces, each managed by a different plugin. Whereabouts is an IP Address Management (IPAM) plugin that assigns IP addresses across a Kubernetes cluster for secondary networks. The CNI Plugins project provides the underlying reference plugins (bridge, vlan, macvlan, ipvlan) that Multus delegates to.

## Comparison Table

| Feature | Multus CNI | Whereabouts IPAM | CNI Plugins |
|---------|-----------|-----------------|-------------|
| **Type** | Meta-plugin (delegates to other CNIs) | IPAM plugin | Reference CNI plugins collection |
| **Stars** | 2,800+ | 380+ | 2,500+ |
| **Primary Use** | Attach multiple interfaces to pods | Cluster-wide IP allocation for secondary networks | Basic networking primitives (bridge, vlan, macvlan, ipvlan) |
| **Org** | k8snetworkplumbingwg | k8snetworkplumbingwg | containernetworking |
| **K8s Native** | Yes (CRD-based NetworkAttachmentDefinition) | Yes (IPPool CRD) | No (JSON config files) |
| **SR-IOV Support** | Yes (with SR-IOV CNI delegate) | No | No |
| **IPAM Methods** | Delegates to host-local, static, whereabouts | Cluster-wide overlapping IP pools | host-local, static, dhcp |
| **Installation** | DaemonSet + CRDs | DaemonSet + CRDs | Binary + config files |
| **Last Active** | 2026 | 2026 | 2026 |
| **Language** | Go | Go | Go |

## Multus CNI: The Multi-Network Meta-Plugin

Multus CNI is the de facto standard for multi-homed pods in Kubernetes. Developed under the Kubernetes Network Plumbing Working Group, it allows you to define `NetworkAttachmentDefinition` CRDs that specify secondary network configurations. When a pod requests additional interfaces via annotations, Multus chains the appropriate CNI plugins.

### Deployment with Kubernetes Manifests

Multus deploys as a DaemonSet. The canonical installation uses the upstream daemonset manifest:

```bash
# Install Multus CNI
kubectl apply -f https://raw.githubusercontent.com/k8snetworkplumbingwg/multus-cni/master/deployments/multus-daemonset.yml
```

### NetworkAttachmentDefinition Example

```yaml
apiVersion: "k8s.cni.cncf.io/v1"
kind: NetworkAttachmentDefinition
metadata:
  name: macvlan-conf
  namespace: default
spec:
  config: '{
    "cniVersion": "0.4.0",
    "type": "macvlan",
    "master": "eth0",
    "mode": "bridge",
    "ipam": {
      "type": "whereabouts",
      "range": "192.168.2.225/28"
    }
  }'
```

### Pod with Multiple Interfaces

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: multi-homed-pod
  annotations:
    k8s.v1.cni.cncf.io/networks: macvlan-conf
spec:
  containers:
  - name: app
    image: nginx
```

The pod will have its default interface (managed by the primary CNI like Calico) plus an additional macvlan interface from the secondary network.

### Docker Compose Equivalent for Testing

For local testing without a full Kubernetes cluster, you can simulate multi-network behavior using Docker Compose with macvlan networks:

```yaml
version: "3.8"
services:
  test-pod:
    image: alpine:latest
    command: ["sleep", "infinity"]
    networks:
      - default
      - secondary-net

networks:
  default:
    driver: bridge
  secondary-net:
    driver: macvlan
    driver_opts:
      parent: eth0
    ipam:
      config:
        - subnet: 192.168.100.0/24
          gateway: 192.168.100.1
```

## Whereabouts IPAM: Cluster-Wide IP Address Management

Whereabouts solves a critical problem in multi-network Kubernetes: IP address allocation across multiple nodes. The standard `host-local` IPAM plugin only tracks allocations on the local node, which leads to IP conflicts when pods on different nodes request addresses from the same subnet.

Whereabouts uses a Kubernetes CRD (`IPPool`) to coordinate IP allocations cluster-wide, supporting overlapping IP ranges across different network definitions.

### Installation

```bash
kubectl apply -f https://raw.githubusercontent.com/k8snetworkplumbingwg/whereabouts/master/doc/crds/daemonset-install.yaml
```

### IPPool CRD

```yaml
apiVersion: whereabouts.cni.cncf.io/v1alpha1
kind: IPPool
metadata:
  name: my-ip-pool
spec:
  range: 192.168.2.225/28
  range_start: 192.168.2.226
  range_end: 192.168.2.230
```

### Integration with Multus

Whereabouts is typically used as the IPAM delegate inside a Multus `NetworkAttachmentDefinition`:

```yaml
apiVersion: "k8s.cni.cncf.io/v1"
kind: NetworkAttachmentDefinition
metadata:
  name: ipvlan-conf
spec:
  config: '{
    "cniVersion": "0.4.0",
    "type": "ipvlan",
    "master": "eth0",
    "mode": "l2",
    "ipam": {
      "type": "whereabouts",
      "range": "10.100.0.0/16",
      "exclude": ["10.100.0.1/30", "10.100.0.255/32"]
    }
  }'
```

The `exclude` field prevents specific IPs from being allocated — useful for gateway addresses or reserved ranges.

## CNI Plugins: The Reference Implementation

The CNI Plugins project provides the foundational networking plugins that most CNI stacks build on. It includes:

- **bridge** — Creates a Linux bridge and connects container veth pairs
- **ipvlan/macvlan** — Creates interfaces that share the host's physical NIC
- **vlan** — Creates 802.1Q VLAN-tagged interfaces
- **ptp** — Point-to-point veth pair
- **loopback** — Brings up the loopback interface
- **host-local / dhcp / static** — IPAM plugins

These are not typically deployed standalone in production Kubernetes — they serve as delegates for higher-level CNIs like Multus, Calico, or Cilium.

### Building CNI Plugins from Source

```bash
git clone https://github.com/containernetworking/plugins.git
cd plugins
./build_linux.sh
# Output binaries go to bin/
```

### Manual Configuration

```json
{
  "cniVersion": "0.4.0",
  "name": "my-bridge",
  "type": "bridge",
  "bridge": "cni0",
  "isGateway": true,
  "ipMasq": true,
  "ipam": {
    "type": "host-local",
    "subnet": "10.22.0.0/16",
    "routes": [
      {"dst": "0.0.0.0/0"}
    ]
  }
}
```

## When to Use Each Tool

**Use Multus CNI when:**
- Your pods need multiple network interfaces (storage network + data network + management network)
- You are deploying DPDK, SR-IOV, or OVS-DPDK workloads
- You need to attach pods to pre-existing VLANs or physical networks
- You are running NFV (Network Function Virtualization) workloads

**Use Whereabouts IPAM when:**
- You need cluster-wide IP allocation for secondary networks
- The default host-local IPAM causes IP conflicts across nodes
- You have overlapping IP ranges across different network definitions
- You need to exclude specific IPs from allocation pools

**Use CNI Plugins when:**
- You are building a custom CNI stack from scratch
- You need basic networking primitives (bridge, vlan, macvlan, ipvlan)
- You are running a lightweight container runtime without Kubernetes
- You need reference implementations for CNI specification compliance

## Deployment Architecture

A typical multi-network Kubernetes deployment layers these components:

```
┌─────────────────────────────────────────────┐
│                 Kubernetes                   │
│  ┌────────────┐  ┌───────────────────────┐  │
│  │  Calico /  │  │     Multus CNI        │  │
│  │  Cilium    │  │  (meta-plugin)        │  │
│  │  (primary) │  │                       │  │
│  └────────────┘  │  ┌─────────────────┐  │  │
│                  │  │   Whereabouts   │  │  │
│                  │  │   (IPAM)        │  │  │
│                  │  └─────────────────┘  │  │
│                  │  ┌─────────────────┐  │  │
│                  │  │ CNI Plugins     │  │  │
│                  │  │ (macvlan/ipvlan)│  │  │
│                  │  └─────────────────┘  │  │
│                  └───────────────────────┘  │
└─────────────────────────────────────────────┘
```

The primary CNI (Calico/Cilium) handles default pod networking. Multus intercepts pod creation events and attaches additional interfaces using the CNI Plugins delegates, with Whereabouts managing IP allocation for those secondary networks.

## Why Self-Host Multi-Network Kubernetes?

Running multi-network Kubernetes workloads on self-hosted infrastructure gives you full control over network segmentation, security policies, and hardware integration. In cloud-managed Kubernetes, multi-network support is often limited or requires specific node types (e.g., AWS ENI attachments, GCP alias IPs). On self-hosted clusters, you can:

- **Integrate with physical networks**: Attach pods directly to VLANs, SR-IOV VFs, or DPDK-enabled interfaces using macvlan/ipvlan plugins
- **Implement custom network topologies**: Create dedicated storage networks (Ceph, NFS), management networks, and data-plane networks with isolated traffic paths
- **Optimize for performance**: Bypass the Kubernetes overlay network entirely for latency-sensitive workloads by using SR-IOV or host-network attachments
- **Reduce cloud costs**: Multi-network setups on managed Kubernetes often require premium node types or additional VPC attachments. Self-hosted clusters on bare metal or VMs eliminate these surcharges
- **Meet compliance requirements**: Network isolation for PCI-DSS, HIPAA, or government workloads often requires physically or logically separate network segments — achievable with Multus + macvlan without cloud provider dependencies

For Kubernetes CNI selection, see our [Calico vs Cilium vs Flannel guide](../2026-04-21-flannel-vs-calico-vs-cilium-self-hosted-kubernetes-cni-guide-2026/). If you need Kubernetes network policy enforcement, check our [Calico vs Cilium vs Kube-Router comparison](../2026-04-26-calico-vs-cilium-vs-kube-router-kubernetes-network-policies-guide/). For Kubernetes secrets management in multi-network environments, our [External Secrets Operator guide](../2026-04-20-external-secrets-operator-vs-sealed-secrets-vs-vault-secrets-operator-kubernetes-secrets-management-2026/) covers the options.

## FAQ

### What is the difference between Multus and a regular CNI plugin?

Multus is a meta-plugin, meaning it does not provide networking itself. Instead, it calls other CNI plugins (delegates) to create network interfaces. A regular CNI like Calico or Flannel creates exactly one interface per pod. Multus can create multiple interfaces by chaining delegates, enabling pods to connect to several networks simultaneously.

### Does Multus replace my primary CNI?

No. Multus works alongside your primary CNI. The primary CNI (Calico, Cilium, Flannel, etc.) handles the default pod network. Multus adds secondary interfaces on top. You configure Multus as the default CNI in kubelet, and it delegates the default network to your primary CNI while adding secondary networks as defined by `NetworkAttachmentDefinition` CRDs.

### Can Whereabouts work without Multus?

Whereabouts is an IPAM plugin, not a CNI plugin. It needs a CNI plugin to call it for IP allocation. While it is primarily designed to work with Multus, it can theoretically work with any CNI plugin that delegates IPAM to Whereabouts. In practice, the most common deployment is Multus + Whereabouts.

### What happens if Whereabouts runs out of IPs?

Whereabouts tracks allocations in the Kubernetes API via `IPPool` CRDs. When the pool is exhausted, new pod creation will fail with an IP allocation error. You can expand the pool by updating the `range` field in the `IPPool` CRD. Monitoring pool utilization is recommended — you can query the `IPPool` resource to see current allocations.

### Does Multus support SR-IOV?

Yes. Multus can delegate to the SR-IOV CNI plugin, which attaches Virtual Functions (VFs) from SR-IOV-capable NICs directly to pods. This provides near-bare-metal network performance for workloads like DPDK, VPP, or custom network functions. The SR-IOV Network Operator automates VF creation and Multus configuration.

### How do I troubleshoot a pod that failed to attach a secondary network?

Check the pod events: `kubectl describe pod <pod-name>` and look for errors from the Multus CNI. Common issues include: the `NetworkAttachmentDefinition` not existing in the pod's namespace, the delegate CNI plugin binary missing from the node, or IPAM exhaustion. You can also check Multus logs: `kubectl logs -n kube-system -l app=multus`.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Kubernetes Multi-Network CNI: Multus vs Whereabouts vs CNI Plugins (2026)",
  "description": "Compare Multus CNI, Whereabouts IPAM, and CNI Plugins for Kubernetes multi-networking. Learn when to use each tool for multi-homed pods, SR-IOV, and cluster-wide IP allocation.",
  "datePublished": "2026-05-09",
  "dateModified": "2026-05-09",
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
