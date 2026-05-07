---
title: "Self-Hosted GPU Operators for Kubernetes: NVIDIA GPU Operator vs Volcano vs KubeRay 2026"
date: "2026-05-17"
tags: ["comparison", "guide", "self-hosted", "kubernetes", "gpu", "operators", "infrastructure"]
draft: false
description: "Compare self-hosted GPU operators for Kubernetes — NVIDIA GPU Operator, Volcano, and KubeRay. Learn how to manage GPU resources, scheduling, and workloads on your own cluster."
---

Running GPU-accelerated workloads on Kubernetes requires more than just attaching a graphics card to a node. GPU provisioning involves driver installation, device plugin registration, resource scheduling, health monitoring, and multi-tenant isolation. Three open-source projects have become the standard solutions for managing GPU infrastructure on Kubernetes: the **NVIDIA GPU Operator**, **Volcano**, and **KubeRay**.

Each project addresses a different layer of the GPU stack — from hardware provisioning to batch scheduling to distributed compute frameworks. This guide compares them and shows how to deploy each with Kubernetes manifests and Helm charts.

## Understanding GPU Management on Kubernetes

Before comparing tools, it helps to understand the layers of GPU management on Kubernetes:

1. **Device Layer** — Installing NVIDIA drivers, CUDA toolkit, and the device plugin so Kubernetes can discover and expose GPU resources
2. **Scheduling Layer** — Placing GPU pods on appropriate nodes, handling resource requests/limits, and managing GPU sharing (MIG, time-slicing)
3. **Workload Layer** — Running GPU-accelerated applications, managing distributed compute jobs, and handling fault tolerance

The NVIDIA GPU Operator handles layer 1, Volcano specializes in layer 2, and KubeRay focuses on layer 3. Many production deployments use all three together.

## Comparison Table

| Feature | NVIDIA GPU Operator | Volcano | KubeRay |
|---------|-------------------|---------|---------|
| **GitHub Stars** | 2,600+ | 5,500+ | 2,400+ |
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| **Primary Focus** | GPU driver/device provisioning | Batch scheduling | Ray framework on K8s |
| **GPU Layer** | Device layer (drivers, plugins) | Scheduling layer | Workload layer |
| **Installation** | Helm chart | Helm chart + CRDs | Helm chart / Kustomize |
| **GPU Types** | NVIDIA only | GPU-agnostic (any device plugin) | GPU-agnostic |
| **MIG Support** | Yes (Multi-Instance GPU) | Via NVIDIA device plugin | Via underlying scheduler |
| **GPU Sharing** | Time-slicing plugin | Gang scheduling + queue | Ray cluster resource mgmt |
| **Multi-tenant** | Resource quotas | Queue-based multi-tenancy | Namespace isolation |
| **Auto-scaling** | Via Cluster Autoscaler | Yes (with HPA/VPA) | Ray autoscaler (built-in) |
| **Monitoring** | DCGM Exporter (Prometheus) | Prometheus metrics | Ray dashboard + metrics |
| **CNCF Status** | — | CNCF Incubating | CNCF Sandbox |
| **Best For** | GPU infrastructure setup | Batch job scheduling | Distributed compute workloads |

## NVIDIA GPU Operator

The NVIDIA GPU Operator automates the deployment and management of all NVIDIA software components needed to use GPUs in Kubernetes. It eliminates the manual process of installing drivers, container toolkits, and device plugins on every GPU node.

### What It Does

- **Driver Installation** — Automatically installs the correct NVIDIA driver version on GPU nodes via a DaemonSet
- **Container Toolkit** — Deploys the NVIDIA Container Toolkit so containers can access GPUs
- **Device Plugin** — Runs the `nvidia-device-plugin` DaemonSet to expose GPU resources to the Kubernetes scheduler
- **GPU Feature Discovery** — Labels nodes with GPU capabilities (CUDA version, MIG support, GPU model)
- **DCGM Monitoring** — Deploys the Data Center GPU Manager (DCGM) exporter for Prometheus metrics
- **MIG Manager** — Configures Multi-Instance GPU partitions on supported hardware
- **Node Status Exporter** — Exports GPU health and utilization metrics

### Helm Chart Deployment

```bash
# Add the NVIDIA Helm repository
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm repo update

# Install the GPU Operator
helm install gpu-operator nvidia/gpu-operator \
  --namespace gpu-operator \
  --create-namespace \
  --set driver.enabled=true \
  --set toolkit.enabled=true \
  --set devicePlugin.enabled=true \
  --set mig.strategy=single \
  --set dcgmExporter.enabled=true

# Verify GPU nodes are labeled
kubectl get nodes -l nvidia.com/gpu.product

# Check GPU resource availability
kubectl describe node <gpu-node-name> | grep -A 5 "nvidia.com/gpu"
```

```yaml
# Custom values.yaml for production
driver:
  enabled: true
  version: "550.54.15"

devicePlugin:
  enabled: true
  config:
    name: time-slicing-config
    default: any

mig:
  strategy: single

dcgmExporter:
  enabled: true
  serviceMonitor:
    enabled: true

toolkit:
  enabled: true
```

### Example GPU Pod

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: cuda-vector-add
spec:
  containers:
    - name: cuda
      image: nvcr.io/nvidia/k8s/cuda-sample:vectoradd-cuda12.5.0
      resources:
        limits:
          nvidia.com/gpu: 1
      env:
        - name: NVIDIA_VISIBLE_DEVICES
          value: all
  restartPolicy: OnFailure
```

## Volcano

Volcano is a CNCF-incubating batch scheduling system for Kubernetes. It provides advanced scheduling capabilities beyond the default Kubernetes scheduler, with strong support for GPU workloads, gang scheduling, and fair sharing across multiple tenants.

### What It Does

- **Gang Scheduling** — Ensures all pods in a job are scheduled together or none are, preventing resource deadlocks
- **Queue Management** — Multi-tenant resource Queues with weight-based fair sharing and capacity limits
- **GPU-Aware Scheduling** — Binpack, spread, and GPU topology-aware placement strategies
- **Predicate and Priority** — Custom predicates for GPU topology (NUMA alignment, PCIe bandwidth)
- **Task-Level Dependencies** — Start tasks in specific order within a batch job
- **Reclaim and Preempt** — Higher-priority queues can reclaim resources from lower-priority jobs
- **Extensible Scheduler Framework** — Plugin architecture for custom scheduling logic

### Helm Chart Deployment

```bash
# Add the Volcano Helm repository
helm repo add volcano https://volcano-sh.github.io/helm-charts
helm repo update

# Install Volcano scheduler
helm install volcano volcano/volcano \
  --namespace volcano-system \
  --create-namespace \
  --set basic.scheduler.kubeScheduler.enabled=true

# Install the Volcano CLI (vcctl)
curl -LO https://github.com/volcano-sh/volcano/releases/download/v1.9.0/vcctl-v1.9.0-linux-amd64.tar.gz
tar xzf vcctl-v1.9.0-linux-amd64.tar.gz
sudo mv vcctl /usr/local/bin/
```

```yaml
# Create a GPU queue for a team
apiVersion: scheduling.volcano.sh/v1beta1
kind: Queue
metadata:
  name: gpu-team-a
spec:
  weight: 3
  capability:
    nvidia.com/gpu: 8
  reclaimable: true
  guarantee:
    resource:
      nvidia.com/gpu: 2
---
# Submit a gang-scheduled GPU job
apiVersion: batch.volcano.sh/v1alpha1
kind: Job
metadata:
  name: distributed-training
  namespace: default
spec:
  queue: gpu-team-a
  schedulerName: volcano
  minAvailable: 4
  tasks:
    - replicas: 4
      name: worker
      template:
        spec:
          containers:
            - name: worker
              image: pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime
              command: ["python", "-c", "import torch; print('GPU:', torch.cuda.device_count())"]
              resources:
                limits:
                  nvidia.com/gpu: 1
          restartPolicy: Never
```

## KubeRay

KubeRay is a Kubernetes operator that manages Ray clusters on Kubernetes. Ray is a distributed computing framework widely used for data processing, hyperparameter tuning, and distributed compute workloads. KubeRay handles the lifecycle of Ray clusters, autoscaling, and GPU resource allocation.

### What It Does

- **RayCluster Operator** — Declarative management of Ray head and worker nodes via Custom Resource Definitions
- **Autoscaling** — Built-in Ray autoscaler that scales worker pods based on workload demand
- **GPU Support** — Automatic GPU resource discovery and allocation across Ray workers
- **Job Submission** — RayJob CRD for submitting and monitoring distributed compute jobs
- **Serve Operator** — RayServe CRD for deploying model serving endpoints with GPU acceleration
- **Multi-Cluster** — Ray cluster can span multiple Kubernetes clusters (with appropriate networking)
- **Observability** — Built-in Ray dashboard, Prometheus metrics, and structured logging

### Kustomize Deployment

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - https://github.com/ray-project/kuberay/ray-operator/config/crd?ref=v1.2.2
  - https://github.com/ray-project/kuberay/ray-operator/config/default?ref=v1.2.2
```

```bash
# Deploy KubeRay operator
kubectl apply -k kustomize/

# Verify operator is running
kubectl get pods -n ray-system
```

```yaml
# Deploy a GPU-enabled RayCluster
apiVersion: ray.io/v1
kind: RayCluster
metadata:
  name: gpu-cluster
spec:
  rayVersion: "2.31.0"
  headGroupSpec:
    rayStartParams:
      dashboard-host: "0.0.0.0"
      num-gpus: "0"
    template:
      spec:
        containers:
          - name: ray-head
            image: rayproject/ray:2.31.0
            ports:
              - containerPort: 6379
                name: gcs
              - containerPort: 8265
                name: dashboard
            resources:
              limits:
                cpu: "4"
                memory: "8Gi"
              requests:
                cpu: "2"
                memory: "4Gi"
  workerGroupSpecs:
    - replicas: 3
      minReplicas: 1
      maxReplicas: 10
      groupName: gpu-workers
      rayStartParams:
        num-gpus: "1"
      template:
        spec:
          containers:
            - name: ray-worker
              image: rayproject/ray:2.31.0
              resources:
                limits:
                  cpu: "8"
                  memory: "32Gi"
                  nvidia.com/gpu: 1
                requests:
                  cpu: "4"
                  memory: "16Gi"
                  nvidia.com/gpu: 1
```

## Architecture: How They Work Together

In a production Kubernetes cluster, these three components form a complete GPU management stack:

```
┌──────────────────────────────────────────────┐
│              Ray Workloads                    │
│         (KubeRay Operator)                    │
│  RayCluster ─ RayJob ─ RayServe              │
├──────────────────────────────────────────────┤
│            Batch Scheduling                   │
│           (Volcano Scheduler)                 │
│  Gang Scheduling ─ Queues ─ Fair Sharing     │
├──────────────────────────────────────────────┤
│          GPU Infrastructure                   │
│       (NVIDIA GPU Operator)                   │
│  Drivers ─ Device Plugin ─ DCGM Exporter      │
└──────────────────────────────────────────────┘
         Kubernetes Control Plane
```

The NVIDIA GPU Operator ensures every GPU node is properly configured. Volcano schedules GPU workloads with gang scheduling and fair queue management. KubeRay runs the actual distributed compute jobs, requesting GPU resources through Volcano and consuming them on NVIDIA-configured nodes.

## Why Self-Host GPU Infrastructure?

Running GPU workloads on managed cloud Kubernetes services (EKS, GKE, AKS) is expensive and often involves vendor-specific GPU management APIs. Self-hosting GPU infrastructure on bare metal or private cloud gives you:

**Full hardware control.** Choose your GPU models (A100, H100, L40S, RTX 4090), configure NVLink topologies, manage PCIe bandwidth, and tune power limits — without cloud provider abstraction layers hiding the hardware.

**Cost efficiency at scale.** Cloud GPU instances carry significant markup. A self-hosted NVIDIA L40S node costs roughly $10,000-$15,000 upfront but delivers equivalent performance to a cloud instance that costs $3-$5 per hour. The breakeven point is typically 3-6 months for sustained workloads.

**No vendor lock-in.** Cloud GPU APIs (NVIDIA GPU Cloud on GKE, EC2 GPU instances on AWS) differ significantly. The open-source GPU operator stack works identically on any Kubernetes distribution — on-premises, at the edge, or across multiple cloud providers.

**Data locality.** GPU workloads often process sensitive or regulated data (medical imaging, financial models, proprietary research). Self-hosting ensures data and computation remain within your security perimeter.

**Custom scheduling policies.** Cloud providers offer limited GPU scheduling options. With Volcano and the NVIDIA GPU Operator, you can implement custom scheduling strategies: NUMA-aware placement, GPU topology optimization, MIG partition management, and time-slicing for multi-tenant clusters.

For GPU utilization monitoring, see our [nvtop vs DCGM Exporter vs Netdata comparison](../2026-04-22-nvtop-vs-dcgm-exporter-vs-netdata-self-hosted-gpu-monitoring-guide-2026/). If you need container security for GPU workloads, check our [NeuVector vs Falco vs Tetragon guide](../2026-04-29-neuvector-vs-falco-vs-tetragon-container-runtime-security-guide-2026/). For distributed compute frameworks, our [distributed training with Horovod, DeepSpeed, and FSDP article](../2026-05-04-self-hosted-distributed-training-horovod-deepspeed-pytorch-fsdp-guide/) covers the application layer.

## FAQ

### Do I need all three tools, or can I use just one?

You can start with just the NVIDIA GPU Operator to get GPU devices working in Kubernetes. Add Volcano if you need batch scheduling with gang scheduling, fair queues, or multi-tenant GPU sharing. Add KubeRay if you want to run Ray-based distributed compute workloads. Many teams use only the GPU Operator initially and add Volcano or KubeRay as their requirements grow.

### Can Volcano schedule non-GPU batch jobs?

Yes. Volcano is a general-purpose batch scheduler that handles any Kubernetes workload — GPU or not. Its gang scheduling, queue management, and fair sharing features work equally well for CPU-only jobs. GPU awareness is an additional capability layered on top of the general batch scheduling features.

### Does the NVIDIA GPU Operator support AMD GPUs?

No. The NVIDIA GPU Operator is specific to NVIDIA hardware. For AMD GPUs, use the AMD GPU Device Plugin (`rocm/k8s-device-plugin`) and the ROCm container toolkit. Volcano and KubeRay are GPU-vendor-agnostic and will work with any device plugin that exposes GPU resources.

### How does GPU time-slicing work?

The NVIDIA GPU Operator can configure time-slicing, which allows multiple containers to share a single GPU by time-multiplexing access. The GPU is divided into time slices (e.g., 4 containers share one GPU, each getting 25% of compute time). This is configured via the GPU Operator's `time-slicing-config` and is useful for development environments or low-utilization workloads.

### What is MIG and when should I use it?

Multi-Instance GPU (MIG) is an NVIDIA feature on A100, H100, and L40S GPUs that physically partitions a single GPU into up to 7 independent GPU instances. Each MIG instance has dedicated compute cores, memory, and cache — providing true hardware isolation between tenants. Use MIG when you need strict quality-of-service guarantees for multi-tenant GPU clusters.

### Can KubeRay autoscale based on GPU availability?

KubeRay's built-in autoscaler scales worker pods based on Ray workload demand (pending tasks in the object store). However, it does not directly trigger Kubernetes cluster autoscaling for GPU nodes. For GPU-aware autoscaling, combine KubeRay with the Kubernetes Cluster Autoscaler configured with GPU node groups, or use Volcano's queue-based resource management.

### How do I monitor GPU health in a Kubernetes cluster?

The NVIDIA GPU Operator deploys DCGM Exporter, which exposes GPU metrics (utilization, temperature, memory usage, power consumption, ECC errors) as Prometheus metrics. These can be visualized in Grafana using the NVIDIA DCGM Exporter dashboard. Volcano adds scheduler-level metrics (queue utilization, pending jobs), and KubeRay provides Ray-specific metrics (actor utilization, task queue depth).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted GPU Operators for Kubernetes: NVIDIA GPU Operator vs Volcano vs KubeRay 2026",
  "description": "Compare self-hosted GPU operators for Kubernetes — NVIDIA GPU Operator, Volcano, and KubeRay. Learn how to manage GPU resources, scheduling, and workloads on your own cluster.",
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
