---
title: "GPU Sharing on Kubernetes in 2026: HAMi vs MIG vs Dynamic Resource Allocation"
date: "2026-11-17"
tags: ["kubernetes", "gpu", "scheduling", "homelab", "devops"]
description: "Three ways to stop wasting expensive GPUs in Kubernetes: HAMi memory/core slicing, NVIDIA MIG partitioning and the new Dynamic Resource Allocation API — with real manifests and honest trade-offs."
cover: "/img/screenshots/hami-gpu-sharing-architecture.jpg"
draft: false
---

A single H100 sitting at 4% utilization while three teams queue for a slice is the most expensive idle time in your cluster. The default Kubernetes device plugin model — one pod, one whole GPU — makes that the normal case. Average utilization across shared clusters is routinely reported in the low double digits, which means you are paying for hardware you never schedule.

There are now three credible ways to fix it: **HAMi** (userspace virtualization with memory and core limits), **NVIDIA MIG** (hardware partitioning into fixed slices), and **Dynamic Resource Allocation** (the Kubernetes-native API that replaced the device plugin model for structured parameters). They solve the same headline problem with three very different mechanisms, and mixing them up is how teams end up with a scheduler that silently overcommits memory.

## TL;DR — Quick Verdict

**Use HAMi** when you want the highest packing density and per-pod memory plus compute caps, and you can accept a userspace interception layer. It is the pragmatic choice for internal clusters running inference services and notebooks.

**Use MIG** when you need hardware-level isolation with a real fault and performance boundary — regulated workloads, noisy neighbours you do not control, or anything with strict latency guarantees.

**Use DRA** when you are on Kubernetes 1.34+ and want to be ready for the future of device scheduling. It is the direction everything is moving, but GPU allocation through DRA drivers is still maturing in late 2026, so treat it as a strategic bet rather than a drop-in replacement today.

One line: **HAMi for density, MIG for isolation, DRA for longevity.**

## Comparison Table

| Dimension | HAMi | NVIDIA MIG | Dynamic Resource Allocation |
|---|---|---|---|
| **Mechanism** | Userspace library injection + scheduler extender | Hardware partitioning via GPU memory slices | Structured device parameters via `resource.k8s.io` |
| **Isolation strength** | Soft — memory is capped, not hardware-partitioned | Hard — separate memory slices, separate fault domains | Depends on driver; same hardware semantics as MIG |
| **Memory control** | Per-pod MiB request (`nvidia.com/gpumem`) | Fixed profiles (`1g.10gb`, `2g.20gb`, …) | Declared in the DeviceClass / claim parameters |
| **Compute control** | Percentage of cores (`nvidia.com/gpucores`) | Slice size implies the compute fraction | Same as hardware slice |
| **Overcommit** | Possible — HAMi caps, does not reserve hardware | No — a slice is a slice | No |
| **Kubernetes version** | Works on older clusters (plugin + extender) | 1.20+ via GPU Operator | 1.32 beta, **1.34 GA** |
| **Setup effort** | One Helm chart | GPU Operator values plus node labelling | Driver install plus `RuntimeClass`/claims |
| **Multi-vendor** | Yes — NVIDIA plus several domestic accelerators | NVIDIA only | Driver-specific |
| **Maturity (Nov 2026)** | CNCF Incubating, 5,015★, pushed 2026-11-16 | Production-proven for years | GPU plugin still beta in the NVIDIA driver |
| **Best fit** | Inference fleets, notebooks, CI | Multi-tenant clusters with hard SLAs | New clusters designed for 2027+ |

## Decision Matrix

| Your situation | Pick | Why |
|---|---|---|
| 20 data scientists sharing 4 GPUs | HAMi | Memory caps prevent one notebook from grabbing the whole card |
| Hosting customer workloads you do not trust | MIG | Hardware boundary, not a library interposition |
| Batch inference where latency is elastic | HAMi | Highest packing density per card |
| Real-time inference with p99 latency SLO | MIG | No cross-tenant interference on memory bandwidth |
| Greenfield cluster, Kubernetes 1.34+ | DRA | Build on the API that replaces device plugins |
| Mixed NVIDIA plus non-NVIDIA accelerators | HAMi | Single scheduler abstraction across vendors |
| You already run the GPU Operator | MIG | It is a values change, not a new component |
| You need per-pod GPU memory limits *and* MIG | Neither alone | Run MIG profiles, then cap memory inside each slice |

## HAMi — Virtualization That Fits Today's Clusters

HAMi (formerly `k8s-vGPU-scheduler`) is a CNCF Incubating project that makes one physical GPU look like several schedulable devices. A mutating webhook injects a userspace library into the container, the library intercepts CUDA calls, and a scheduler extender enforces the memory and core budget you declared.

The install is a single chart:

```bash
helm repo add hami-charts https://project-hami.io/charts
helm repo update
helm install hami hami-charts/hami --namespace kube-system
```

Then any pod can request a fraction of a card:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: embedding-worker
spec:
  containers:
    - name: worker
      image: registry.example.com/embedding-worker:3.2
      resources:
        limits:
          nvidia.com/gpu: 1        # one virtual GPU slot
          nvidia.com/gpumem: 4096  # 4096 MiB of device memory
          nvidia.com/gpucores: 30  # 30% of the card's compute
```

**What actually happens:** the scheduler only places the pod on a node where 4096 MiB and 30% of cores remain free, and the injected library makes the container's CUDA context respect that budget. Two pods each asking for 4 GiB and 30% fit on one 24 GiB card with room to spare.

**Where it is strong:** density and vendor breadth. HAMi exposes a single set of resource names across NVIDIA and several other accelerator families, which matters if your fleet is heterogeneous. It also integrates with Volcano and Kueue, so gang scheduling and queueing keep working.

**Where it is weak:** isolation is a policy, not a wall. A process that bypasses the injected library — static binaries, some JIT paths, certain framework builds — can ignore the memory cap. Memory bandwidth is still shared. If a neighbour saturates HBM, your latency moves. That is acceptable for notebooks, unacceptable for SLO-bound serving.

## NVIDIA MIG — Hardware Partitions, Hardware Guarantees

Multi-Instance GPU carves a physical card into fixed slices, each with dedicated memory, dedicated cache slices and a dedicated fault domain. An A100 80GB can present seven `1g.10gb` instances; an H100 partitions along similar lines. The isolation is real: a crash in one instance does not take down the others, and memory bandwidth is partitioned.

If you already run the GPU Operator, MIG is a values change plus a node label:

```yaml
# GPU Operator values — enable the MIG manager in mixed mode
mig:
  strategy: mixed        # "single" pins one profile; "mixed" allows several
  manager:
    env:
      - name: WITH_REBOOT
        value: "true"
```

```bash
# Tell the MIG manager which profile layout this node should apply
kubectl label node gpu-node-01 nvidia.com/mig.config=all-1g.10gb --overwrite

# After the manager reapplies the layout, slices show up as schedulable resources
kubectl describe node gpu-node-01 | grep -A6 "Allocatable:"
# nvidia.com/mig-1g.10gb:  7
```

Requesting a slice looks like any other extended resource:

```yaml
resources:
  limits:
    nvidia.com/mig-1g.10gb: 1
```

**Where it is strong:** the boundary is enforced by the GPU itself. You can hand a slice to a customer, a build job, or an untrusted tenant and mean it. Latency is predictable because bandwidth is partitioned.

**Where it is weak:** fixed profile sizes waste memory. A pod that needs 6 GiB either takes a 10 GiB slice or gets nothing. Reconfiguring a node's layout usually requires draining pods, and some configurations need a reboot. You also cannot slice below the smallest profile — on many cards that is already 5 or 10 GiB, which is far more than a small service needs.

## Dynamic Resource Allocation — The API That Replaces Device Plugins

DRA changes the contract. Instead of asking for an opaque `nvidia.com/gpu: 1`, a workload files a **claim** describing what it needs, and a driver publishes device classes with structured parameters. The scheduler then matches claims to devices with full knowledge of the constraints.

The NVIDIA DRA driver for GPUs (`kubernetes-sigs/dra-driver-nvidia-gpu`, 733★, pushed 2026-11-15) is the reference implementation. Its headline feature beyond GPU allocation is `ComputeDomain` — an abstraction for secure multi-node NVLink on systems like GB200 — which is a capability the device plugin model cannot express at all.

```yaml
apiVersion: resource.k8s.io/v1
kind: ResourceClaimTemplate
metadata:
  name: one-gpu
spec:
  spec:
    devices:
      requests:
        - name: gpu
          exactly:
            deviceClassName: gpu.nvidia.com
            count: 1
---
apiVersion: v1
kind: Pod
metadata:
  name: trainer
spec:
  resourceClaims:
    - name: gpu
      resourceClaimTemplateName: one-gpu
  containers:
    - name: trainer
      image: registry.example.com/trainer:1.9
```

**Where it is strong:** this is where upstream Kubernetes is going. Structured parameters mean vendors can express attributes — memory size, MIG capability, NVLink domain — and the scheduler reasons about them natively. No more scheduler extenders patched around a plugin API that was never designed for GPUs.

**Where it is weak:** timing. In the NVIDIA driver's own README, the GPU kubelet plugin is **disabled by default** and GPU allocation features are described as available for exploration but not officially supported, while `ComputeDomain` is the officially supported half. Enable DRA for a pilot cluster; do not migrate your production inference fleet this quarter.

## Pitfalls That Bite in Production

**Do not mix accounting models on one node.** HAMi virtual slots and MIG slices both shadow `nvidia.com/gpu`. Run one model per node pool and label it, or your scheduler will happily place a virtual-GPU pod on a MIG node and double-book the card.

**Memory caps are not reservations.** HAMi prevents overcommit at the scheduler level, but a workload that allocates lazily can still OOM inside its cap. Set requests equal to limits and watch device memory as a first-class metric — the [GPU monitoring comparison](../2026-04-22-nvtop-vs-dcgm-exporter-vs-netdata-self-hosted-gpu-monitoring-guide-2026/) covers exporters that surface per-pod utilization.

**MIG layouts are disruptive.** Changing a node's profile requires destroying instances, which means draining every pod on that card. Plan layouts per node pool up front; a "quick profile change" at 2 a.m. is how incidents start.

**Fractional GPUs break naive autoscaling.** With HAMi, five pods may fit where one used to. Horizontal pod autoscalers keyed on GPU utilization will either never scale or scale to the moon. Key on queue depth or request latency instead.

**DRA needs a modern cluster.** DRA is GA in Kubernetes 1.34, but the feature gates, `RuntimeClass` handling and driver versions have to line up. Verify with a two-node kind cluster before touching the real one.

**Scheduling policy is separate from slicing.** Neither HAMi nor MIG decides *who* gets the GPU first. If you need fairness across teams, pair slicing with a queueing layer — the [Volcano vs YuniKorn vs Kueue comparison](../volcano-vs-yunikorn-vs-kueue-kubernetes-batch-scheduler-guide-2026/) covers that layer, and our [GPU Operator deployment guide](../2026-05-17-self-hosted-gpu-operators-kubernetes-nvidia-volcano-kuberay-guide/) covers the base install these options sit on top of.

## FAQ

### Can HAMi and MIG be combined on the same GPU?

Not on the same node in practice. HAMi virtualizes a whole card from userspace; MIG splits the card in hardware before any userspace layer sees it. Choose per node pool. If you want both guarantees, run MIG for the hardware boundary and then cap memory inside each slice using container-level limits or framework settings.

### Does GPU sharing hurt performance?

MIG gives you predictable performance per slice because memory bandwidth and cache are partitioned. HAMi shares bandwidth, so a memory-bandwidth-hungry neighbour can slow you down even when your own memory cap is respected. For batch workloads that is invisible; for latency-sensitive serving, measure before you commit.

### Is Dynamic Resource Allocation ready for production in 2026?

The API is GA in Kubernetes 1.34, and `ComputeDomain` in the NVIDIA DRA driver is officially supported. GPU allocation through the same driver is still labelled experimental, with the kubelet plugin disabled by default. Treat DRA as production-ready for multi-node NVLink topologies and pilot-only for general GPU sharing.

### What is the simplest option for a small homelab cluster?

HAMi. One Helm chart, no node reconfiguration, no reboots, and per-pod memory limits that stop a runaway notebook from taking the card. MIG is worth the effort only when you need a hard boundary and your card actually supports useful profiles.

### How do I know sharing is actually working?

Watch allocatable resources on the node (`kubectl describe node`), then check per-pod device memory with DCGM-based exporters. If two pods on one card each report their own memory usage and the total exceeds a single card's capacity, sharing is functioning. If utilization stays flat while queues grow, your scheduler or resource names are misconfigured.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "GPU Sharing on Kubernetes in 2026: HAMi vs MIG vs Dynamic Resource Allocation",
  "description": "HAMi GPU virtualization, NVIDIA MIG partitioning and the DRA API compared with real manifests, decision matrix and production pitfalls.",
  "datePublished": "2026-11-17",
  "dateModified": "2026-11-17",
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
