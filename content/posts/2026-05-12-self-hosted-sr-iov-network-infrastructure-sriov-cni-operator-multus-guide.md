---
title: "Self-Hosted SR-IOV Network Infrastructure: SR-IOV CNI vs SR-IOV Network Operator vs Multus CNI"
date: "2026-05-12"
tags: ["kubernetes", "networking", "sriov", "cni", "infrastructure"]
draft: false
---

In Kubernetes environments, network performance is often the bottleneck for workloads that process high-throughput data -- packet capture, telecom core networks, NFV (Network Functions Virtualization), and real-time streaming. The default container networking model routes all traffic through a virtual bridge, adding latency and CPU overhead that can be unacceptable for these use cases.

SR-IOV (Single Root I/O Virtualization) solves this by allowing a physical network interface card (NIC) to present multiple virtual functions (VFs) that can be assigned directly to containers, bypassing the kernel network stack entirely. The result is near-bare-metal network performance inside a container.

Three open-source projects make SR-IOV usable in Kubernetes: the **SR-IOV CNI plugin**, the **SR-IOV Network Operator**, and **Multus CNI**. Each serves a different role in the SR-IOV stack, and understanding their relationship is key to deploying high-performance networking in your cluster.

## What Is SR-IOV and Why Does It Matter?

SR-IOV is a PCI-SIG specification that allows a single physical PCIe device (typically a network card) to appear as multiple separate virtual devices. Each virtual function (VF) has its own MAC address, VLAN tag, and can be assigned to a different VM or container.

Without SR-IOV, every container shares the host network interface through a virtual bridge (like a Linux bridge or OVS). This adds:
- **Latency**: Additional context switches and packet copying
- **CPU overhead**: Host CPU must process every packet through the software bridge
- **Bandwidth limits**: The bridge becomes a bottleneck at high throughput

With SR-IOV, a container gets direct access to a hardware VF. The NIC handles packet processing in silicon, bypassing the kernel entirely. This delivers:
- Sub-microsecond latency (comparable to bare metal)
- Line-rate throughput (25 Gbps, 40 Gbps, 100 Gbps)
- Near-zero CPU overhead on the host

## Project Comparison at a Glance

| Feature | SR-IOV CNI | SR-IOV Network Operator | Multus CNI |
|---------|-----------|------------------------|------------|
| GitHub Stars | 380+ | 148+ | 2,850+ |
| Last Updated | Active (May 2026) | Active (May 2026) | Active (Apr 2026) |
| Role | CNI plugin for VFs | Lifecycle management | Meta-plugin for multi-homing |
| Complexity | Low | Medium | Low-Medium |
| Dependencies | SR-IOV device plugin | Operator SDK, OCP/K8s | Other CNI plugins |
| Config Management | Manual ConfigMap | CRD-based automation | NetworkAttachmentDefinition |
| Vendor Support | Community | Red Hat/OpenShift | CNCF/NFV community |
| Auto VF Creation | No | Yes | No |
| Multi-NIC Support | Yes | Yes | Yes |

The critical insight is that these three projects are **complementary, not competitive**. Multus CNI enables a pod to use multiple network interfaces. The SR-IOV CNI plugin provides one of those interfaces as a hardware VF. The SR-IOV Network Operator automates the entire SR-IOV stack deployment and VF lifecycle.

## Deployment Architecture

### SR-IOV CNI Plugin

The SR-IOV CNI plugin is the lowest-level component. It attaches a pre-created VF to a container when the pod is scheduled:

```yaml
# SR-IOV CNI ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: sriov-cni-config
  namespace: kube-system
data:
  config.json: |
    {
      "cniVersion": "0.3.1",
      "name": "sriov-network",
      "type": "sriov",
      "ipam": {
        "type": "host-local",
        "subnet": "10.56.217.0/24",
        "routes": [
          {"dst": "0.0.0.0/0"}
        ],
        "gateway": "10.56.217.1"
      }
    }
```

Installation via DaemonSet:

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: sriov-cni
  namespace: kube-system
spec:
  selector:
    matchLabels:
      app: sriov-cni
  template:
    metadata:
      labels:
        app: sriov-cni
    spec:
      hostNetwork: true
      containers:
      - name: sriov-cni
        image: ghcr.io/k8snetworkplumbingwg/sriov-cni:latest
        securityContext:
          privileged: true
        volumeMounts:
        - name: cnibin
          mountPath: /host/opt/cni/bin
        - name: cni-conf
          mountPath: /host/etc/cni/net.d
      volumes:
      - name: cnibin
        hostPath:
          path: /opt/cni/bin
      - name: cni-conf
        hostPath:
          path: /etc/cni/net.d
```

### SR-IOV Network Operator

The SR-IOV Network Operator is a Kubernetes Operator that manages the entire SR-IOV stack -- device plugin, CNI plugin, and VF creation:

```yaml
apiVersion: sriovnetwork.openshift.io/v1
kind: SriovNetworkNodePolicy
metadata:
  name: policy-dpdk
  namespace: openshift-sriov-network-operator
spec:
  deviceType: vfio-pci
  mtu: 9000
  numVfs: 8
  nicSelector:
    pfNames: ["ens1f0"]
    vendor: "8086"
    deviceID: "158b"
  resourceName: dpdknic
  nodeSelector:
    node-role.kubernetes.io/worker: ""
```

The operator automatically:
- Enables SR-IOV on the physical NIC
- Creates the requested number of VFs
- Installs the SR-IOV device plugin
- Configures the CNI plugin
- Exposes VFs as extended resources in Kubernetes

### Multus CNI

Multus CNI is a meta-plugin that allows pods to have multiple network interfaces. It calls other CNI plugins (including SR-IOV CNI) as delegates:

```yaml
apiVersion: "k8s.cni.cncf.io/v1"
kind: NetworkAttachmentDefinition
metadata:
  name: sriov-net
  namespace: default
spec:
  config: '{
    "cniVersion": "0.3.1",
    "name": "sriov-network",
    "type": "sriov",
    "ipam": {
      "type": "static",
      "addresses": [
        {"address": "10.56.217.10/24"}
      ]
    }
  }'
```

Pod annotation to use multiple networks:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: multi-net-pod
  annotations:
    k8s.v1.cni.cncf.io/networks: |
      [
        {"name": "sriov-net", "interface": "net1"},
        {"name": "vlan-net", "interface": "net2"}
      ]
spec:
  containers:
  - name: app
    image: nginx:latest
```

## Docker Compose for Testing

While SR-IOV is primarily a Kubernetes technology, you can test SR-IOV VF assignment in Docker Compose environments:

```yaml
version: "3.8"
services:
  sriov-test:
    image: ubuntu:22.04
    container_name: sriov-test
    privileged: true
    network_mode: "none"
    command: sleep infinity
    volumes:
      - /dev:/dev
      - /sys:/sys
    devices:
      - /dev/vfio/vfio
```

Note: SR-IOV requires specific hardware support (NICs with SR-IOV capability) and kernel configuration. The following NICs are known to work well:

- Intel X710/XL710 (10/40 Gbps)
- Intel E810 (100 Gbps)
- Mellanox ConnectX-4/5/6 (25/100 Gbps)
- Broadcom NetXtreme E-Series

## Configuration: VF Assignment Methods

There are two primary methods for assigning VFs to containers:

### VFIO-PCI (DPDK mode)

For maximum performance, VFs are bound to the `vfio-pci` driver and used with DPDK (Data Plane Development Kit):

```yaml
apiVersion: sriovnetwork.openshift.io/v1
kind: SriovNetworkNodePolicy
metadata:
  name: dpdk-policy
spec:
  deviceType: vfio-pci
  numVfs: 16
  nicSelector:
    pfNames: ["ens1f0"]
  resourceName: dpdk_nic
```

### Kernel Mode (Standard networking)

For standard container networking without DPDK:

```yaml
apiVersion: sriovnetwork.openshift.io/v1
kind: SriovNetworkNodePolicy
metadata:
  name: kernel-policy
spec:
  deviceType: netdevice
  numVfs: 8
  nicSelector:
    pfNames: ["ens1f1"]
  resourceName: sriov_nic
```

## When to Use Each Component

### Use SR-IOV CNI alone if:
- You have a simple Kubernetes cluster without an operator framework
- You want manual control over VF creation and assignment
- You are running a small-scale deployment (fewer than 10 nodes)
- You prefer to manage configuration via ConfigMaps

### Use SR-IOV Network Operator if:
- You are running OpenShift or a Kubernetes cluster with Operator Lifecycle Manager
- You need automated VF lifecycle management across many nodes
- You want declarative configuration through CRDs
- You need integration with OpenShift Network Functions features

### Use Multus CNI if:
- Your pods need multiple network interfaces (SR-IOV + default network)
- You want to mix different network types (SR-IOV, MACVLAN, IPvlan) in the same pod
- You are building NFV workloads that require separate control and data plane networks
- You need network attachment definitions for dynamic network provisioning

## Why Deploy SR-IOV in Self-Hosted Infrastructure?

For organizations running telecom workloads, packet core networks, or real-time data processing pipelines, the performance benefits of SR-IOV are substantial. A container using a virtual Ethernet pair through a software bridge typically achieves 5-10 Gbps throughput with 50-100 microseconds of latency. The same container with an SR-IOV VF achieves 25-100 Gbps with sub-microsecond latency.

The trade-off is operational complexity. SR-IOV requires specific hardware, kernel configuration, and careful VF pool management. Not every workload needs this level of performance. For standard web services, databases, and batch processing, the default CNI network is perfectly adequate.

But for specific use cases, SR-IOV is the only way to meet performance requirements:
- **5G packet core**: UPF (User Plane Function) requires line-rate packet processing
- **NFV**: Virtual routers, firewalls, and load balancers need hardware offload
- **High-frequency trading**: Sub-microsecond latency is a business requirement
- **Video streaming**: Real-time encoding/decoding at multiple 4K streams

For Kubernetes networking fundamentals, our [Kubernetes CNI comparison](../2026-04-21-flannel-vs-calico-vs-cilium-self-hosted-kubernetes-cni-guide-2026/) covers the baseline options. For multi-cluster networking scenarios, our [multi-cluster networking guide](../2026-05-01-karmada-vs-liqo-vs-submariner-self-hosted-multi-cluster-kubernetes-networking/) explores cross-cluster connectivity. And for multi-network CNI setups specifically, our [Multus and Whereabouts guide](../2026-05-09-kubernetes-multi-network-cni-multus-whereabouts-guide/) provides detailed IPAM configuration.

## FAQ

### What hardware do I need for SR-IOV?

You need a network interface card (NIC) that supports SR-IOV. Most enterprise-grade NICs from Intel, Mellanox (now NVIDIA), and Broadcom support this feature. Check your NIC specifications for "SR-IOV" or "Virtual Functions" support. Consumer-grade NICs typically do not support SR-IOV.

### How many VFs can I create per physical function?

The maximum number of VFs depends on your NIC. Intel X710 supports up to 64 VFs per port. Mellanox ConnectX-5 supports up to 128 VFs per port. Check your NIC datasheet for the exact limit. Creating more VFs than the hardware supports will fail silently or cause driver errors.

### Can I use SR-IOV with Docker without Kubernetes?

Yes. Docker supports device passthrough via the `--device` flag and `--network=none` with manual VF assignment. However, Kubernetes with Multus CNI provides a much more manageable abstraction for multi-container SR-IOV deployments. Docker alone requires manual VF creation and binding on each host.

### Does SR-IOV work with IPv6?

Yes. SR-IOV VFs are standard network interfaces at the OS level and support IPv6 natively. The IPAM plugin used by the CNI configuration determines whether IPv4, IPv6, or dual-stack addressing is configured.

### What is the difference between VFIO-PCI and netdevice modes?

VFIO-PCI mode binds the VF to the VFIO driver, allowing user-space applications (like DPDK) to access the hardware directly for maximum performance. Netdevice mode keeps the VF in kernel mode, usable as a standard Linux network interface. Use VFIO-PCI for DPDK-based workloads and netdevice for standard container networking.

### How do I monitor SR-IOV VF utilization?

Use the `ip -s link show` command to see per-interface statistics. For VF-specific counters, check `/sys/class/net/<vf_interface>/statistics/`. The SR-IOV Network Operator exposes metrics through Prometheus when monitoring is enabled. For DPDK workloads, use `dpdk-procinfo` or the application-specific telemetry.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted SR-IOV Network Infrastructure: SR-IOV CNI vs SR-IOV Network Operator vs Multus CNI",
  "description": "Deploy SR-IOV for near-bare-metal network performance in Kubernetes. Compare SR-IOV CNI, SR-IOV Network Operator, and Multus CNI with configs.",
  "datePublished": "2026-05-12",
  "dateModified": "2026-05-12",
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
