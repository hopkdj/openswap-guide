---
title: "Self-Hosted Kubernetes Topology-Aware Scheduling: Topology Manager, NUMA & Spread Constraints (2026)"
date: "2026-05-15"
tags: ["kubernetes", "scheduling", "topology", "numa", "performance"]
draft: false
---

When running performance-sensitive workloads on Kubernetes — databases, machine learning inference, network functions, or high-throughput APIs — pod placement matters enormously. A pod scheduled on a node with the wrong CPU topology, NUMA configuration, or zone distribution can experience 2-10x performance degradation compared to an optimally placed pod.

This guide covers three Kubernetes mechanisms for topology-aware scheduling: the Topology Manager, NUMA-aware scheduling, and Topology Spread Constraints — explaining how they work, when to use each, and how to configure them for production workloads.

## Understanding Kubernetes Topology

Modern servers have complex hardware topologies:
- **NUMA nodes**: Multi-socket servers divide memory and CPU into Non-Uniform Memory Access zones. Cross-NUMA memory access can add 40-100ns latency.
- **CPU sockets and cores**: Hyperthreading, CPU pinning, and isolated cores affect performance.
- **GPU/PCIe topology**: GPUs attached to specific PCIe switches perform best with co-located CPU cores.
- **Availability zones**: Cloud and multi-node clusters span fault domains that affect latency and availability.

Kubernetes provides several mechanisms to optimize pod placement based on these topologies.

## Topology Manager

The Topology Manager is a kubelet component that coordinates resource allocation decisions across device plugins (GPU, SR-IOV, FPGA) and the CPU manager to ensure optimal hardware alignment.

### How It Works

Topology Manager operates at the kubelet level, not the scheduler level. When a pod requests resources from multiple device plugins, the Topology Manager ensures all resources come from the same NUMA node:

```yaml
# kubelet configuration (typically in /var/lib/kubelet/config.yaml)
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
topologyManagerPolicy: restricted
topologyManagerScope: pod
```

### Topology Manager Policies

| Policy | Behavior | Use Case |
|--------|----------|----------|
| `none` | No topology alignment (default) | General workloads |
| `best-effort` | Prefers aligned resources, accepts unaligned | Mixed clusters |
| `restricted` | Rejects pods that can't be aligned | Performance-critical |
| `single-numa-node` | All resources must fit on one NUMA node | Maximum performance |

### Pod Configuration

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-inference
  annotations:
    kubernetes.io/topology-policy: "restricted"
spec:
  containers:
  - name: inference
    image: nvcr.io/nvidia/tensorrt:24.01
    resources:
      limits:
        cpu: "4"
        memory: "8Gi"
        nvidia.com/gpu: "1"
      requests:
        cpu: "4"
        memory: "8Gi"
```

With `restricted` policy, if the GPU and 4 CPUs cannot be allocated from the same NUMA node, the pod stays in Pending state rather than being placed sub-optimally.

### Deployment Example

```yaml
version: "3.8"
services:
  kubelet-config:
    image: k8s.gcr.io/pause:3.9
    volumes:
      - ./kubelet-config.yaml:/var/lib/kubelet/config.yaml
      - /etc/kubernetes:/etc/kubernetes
    command: ["cp", "/var/lib/kubelet/config.yaml", "/etc/kubernetes/kubelet-config.yaml"]
```

## NUMA-Aware Scheduling

NUMA-aware scheduling goes beyond the Topology Manager by incorporating NUMA topology information into the Kubernetes scheduler's decision-making process.

### NUMA Topology Discovery

First, enable NUMA resource discovery on your nodes:

```yaml
apiVersion: v1
kind: Node
metadata:
  name: worker-01
  labels:
    topology.kubernetes.io/zone: us-east-1a
    numa-node: "0"
status:
  allocatable:
    cpu: "32"
    memory: "128Gi"
    hugepages-1Gi: "4"
    nvidia.com/gpu: "4"
```

### Pod with NUMA-Aware Resources

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: numa-database
  annotations:
    cpu-set.kubernetes.io/numa-node: "0"
spec:
  containers:
  - name: postgres
    image: postgres:16
    resources:
      requests:
        cpu: "8"
        memory: "32Gi"
        hugepages-1Gi: "1"
      limits:
        cpu: "8"
        memory: "32Gi"
        hugepages-1Gi: "1"
    env:
    - name: HUGE_PAGES
      value: "1Gi"
```

### CPU Manager with Static Policy

For guaranteed NUMA alignment, combine the CPU Manager with static policy:

```yaml
# kubelet configuration
cpuManagerPolicy: static
cpuManagerReconcilePeriod: 5s
topologyManagerPolicy: single-numa-node
```

The static CPU Manager policy reserves exclusive CPUs for Guaranteed QoS pods, eliminating CPU contention and ensuring NUMA-local memory access.

## Topology Spread Constraints

Topology Spread Constraints are scheduler-level rules that distribute pods across failure domains (zones, nodes, hostnames) to maximize availability and minimize blast radius.

### Basic Topology Spread

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-frontend
spec:
  replicas: 6
  selector:
    matchLabels:
      app: web-frontend
  template:
    metadata:
      labels:
        app: web-frontend
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-frontend
      - maxSkew: 2
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: web-frontend
      containers:
      - name: nginx
        image: nginx:1.25
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
```

This configuration ensures:
- Pods are evenly distributed across availability zones (maxSkew: 1, DoNotSchedule)
- Pods are reasonably spread across individual nodes (maxSkew: 2, ScheduleAnyway)

### Advanced Topology Spread with Multiple Constraints

```yaml
topologySpreadConstraints:
- maxSkew: 1
  topologyKey: topology.kubernetes.io/zone
  whenUnsatisfiable: DoNotSchedule
  labelSelector:
    matchLabels:
      app: database
  minDomains: 3
- maxSkew: 1
  topologyKey: topology.kubernetes.io/region
  whenUnsatisfiable: DoNotSchedule
  labelSelector:
    matchLabels:
      app: database
```

### Deployment with Helm Values

```yaml
# values.yaml for Helm chart
replicaCount: 6
topologySpreadConstraints:
  enabled: true
  zones:
    maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule
  nodes:
    maxSkew: 2
    topologyKey: kubernetes.io/hostname
    whenUnsatisfiable: ScheduleAnyway
```

## Comparison: Topology Manager vs NUMA-Aware vs Spread Constraints

| Feature | Topology Manager | NUMA-Aware Scheduling | Topology Spread |
|---------|-----------------|----------------------|-----------------|
| **Level** | Kubelet (node-local) | Kubelet + Scheduler | Scheduler (cluster-wide) |
| **Goal** | Hardware alignment | NUMA-local resources | Failure domain distribution |
| **Scope** | Single node | Single node | Entire cluster |
| **Best For** | GPU/accelerator workloads | CPU-intensive apps | High availability |
| **Policy Types** | none/best-effort/restricted/single-numa | CPU manager + hugepages | DoNotSchedule/ScheduleAnyway |
| **Requires Labels** | No | No | Yes (labelSelector) |

## Why Self-Host Kubernetes with Topology Awareness?

In self-hosted Kubernetes environments — especially bare metal deployments — you have direct access to hardware topology information that cloud environments abstract away. This enables:

- **NUMA-optimized database performance**: PostgreSQL, MySQL, and Redis benefit enormously from NUMA-local memory access. A properly configured NUMA-aware deployment can achieve 2-3x throughput improvement for memory-intensive queries.
- **GPU inference optimization**: Machine learning inference workloads need GPU and CPU resources on the same NUMA node to minimize PCIe latency.
- **Network function optimization**: DPDK-based network functions require CPU pinning and NUMA-aligned NIC assignment for line-rate packet processing.
- **High availability**: Topology spread constraints ensure your workloads survive zone and node failures without manual intervention.

For container runtime isolation options, see our [runtime sandboxing guide](../2026-04-20-gvisor-vs-kata-containers-vs-firecracker-container-sandboxing-guide-2026/) and [CNI plugin comparison](../2026-04-21-flannel-vs-calico-vs-cilium-self-hosted-kubernetes-cni-guide-2026/).

## Choosing the Right Topology Strategy

**Use Topology Manager when:**
- Running GPU, FPGA, or SR-IOV workloads
- Device plugin resources must align with CPU/memory allocation
- You need guaranteed hardware topology alignment

**Use NUMA-Aware Scheduling when:**
- Running CPU-intensive or memory-intensive workloads (databases, analytics)
- You have multi-socket servers and need to minimize cross-NUMA memory access
- Combined with CPU Manager static policy for exclusive CPU allocation

**Use Topology Spread Constraints when:**
- Maximizing availability across failure domains
- Running multi-zone or multi-region clusters
- Needing even load distribution across nodes

### Monitoring Topology Alignment

```bash
# Check NUMA topology on a node
kubectl describe node worker-01 | grep -A10 "Allocatable"

# Verify CPU Manager state
cat /var/lib/kubelet/cpu_manager_state

# Check topology alignment events
kubectl get events --sort-by='.lastTimestamp' | grep -i topology

# Verify Hubble topology visualization (Cilium)
cilium hubble observe --to-namespace kube-system
```

### Troubleshooting Topology Issues

Common problems and solutions:
- **Pods stuck in Pending with topology conflict**: Check `kubectl describe pod` for scheduling failure events. The Topology Manager logs the specific resource conflict in kubelet logs.
- **Uneven pod distribution despite spread constraints**: Verify that node labels match your topologyKey. Run `kubectl get nodes --show-labels` to confirm zone and hostname labels.
- **NUMA alignment not working**: Ensure the kubelet was started with `--cpu-manager-policy=static` and that pods use Guaranteed QoS (requests = limits) for CPU.


## FAQ

### What is NUMA and why does it matter for Kubernetes?

NUMA (Non-Uniform Memory Access) is a memory architecture where each CPU socket has its own local memory. Accessing local memory is faster than accessing memory attached to another CPU socket (cross-NUMA access adds 40-100ns latency). For memory-intensive workloads like databases, NUMA-aware scheduling can improve throughput by 2-3x.

### Can I use Topology Manager with cloud Kubernetes?

Topology Manager works on any Kubernetes cluster where the kubelet has NUMA topology information. Most cloud providers don't expose NUMA topology to the kubelet, so Topology Manager is primarily useful for bare metal and on-premises Kubernetes clusters.

### What is the difference between DoNotSchedule and ScheduleAnyway?

`DoNotSchedule` prevents the scheduler from placing a pod if it would violate the topology spread constraint (hard constraint). `ScheduleAnyway` allows the scheduler to place the pod even if the constraint is violated, but it prefers placements that satisfy the constraint (soft constraint). Use `DoNotSchedule` for critical availability requirements.

### Does Topology Manager work with the CPU Manager?

Yes, the Topology Manager coordinates with the CPU Manager to ensure aligned resource allocation. When using `topologyManagerPolicy: single-numa-node` with `cpuManagerPolicy: static`, the kubelet guarantees that all requested CPUs and device plugin resources come from the same NUMA node.

### How do I verify topology alignment is working?

Check the kubelet logs for topology alignment decisions: `journalctl -u kubelet | grep -i topology`. You can also inspect pod status — pods rejected by Topology Manager will show in Pending state with an event explaining the topology conflict.

### What is maxSkew in topology spread constraints?

`maxSkew` defines the maximum allowed difference in pod count between any two topology domains. For example, `maxSkew: 1` with `topologyKey: topology.kubernetes.io/zone` ensures that no zone has more than 1 additional pod compared to any other zone.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Kubernetes Topology-Aware Scheduling: Topology Manager, NUMA & Spread Constraints (2026)",
  "description": "Complete guide to Kubernetes topology-aware scheduling — Topology Manager, NUMA-aware scheduling, and Topology Spread Constraints with configuration examples.",
  "datePublished": "2026-05-15",
  "dateModified": "2026-05-15",
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
