---
title: "Self-Hosted GPU Management in Kubernetes: NVIDIA GPU Operator vs Container Toolkit vs Volcano Guide 2026"
date: 2026-05-04
tags: ["comparison", "guide", "self-hosted", "kubernetes", "gpu-computing", "infrastructure"]
draft: false
description: "Compare self-hosted GPU management solutions for Kubernetes — NVIDIA GPU Operator, NVIDIA Container Toolkit, and Volcano GPU scheduler. Learn which GPU approach fits your cluster with Helm configs, MIG support, and deployment guides."
---

Running GPU workloads on Kubernetes requires more than just installing GPU drivers. You need device discovery, driver installation, container runtime integration, resource scheduling, and optionally Multi-Instance GPU (MIG) partitioning. The tooling ecosystem has evolved from manual driver installation on every node to fully automated operators that manage the entire GPU lifecycle.

This guide compares three approaches to self-hosted GPU management in Kubernetes: **NVIDIA GPU Operator** (automated full-stack management), **NVIDIA Container Toolkit** (manual per-node setup), and **Volcano** (batch-oriented GPU scheduler with gang scheduling). We'll cover installation methods, provide Helm configurations, and help you choose the right approach for your GPU cluster.

For GPU hardware monitoring across your cluster, see our [GPU monitoring tools guide](../2026-04-22-nvtop-vs-dcgm-exporter-vs-netdata-self-hosted-gpu-monitoring-guide-2026/). If you're using these GPUs for distributed training workloads, our [distributed training comparison](../2026-05-04-self-hosted-distributed-training-horovod-deepspeed-pytorch-fsdp-guide/) covers the training frameworks that consume these GPU resources. For Kubernetes cluster management beyond GPU, see our [cluster management comparison](../2026-04-22-rancher-vs-kubespray-vs-kind-self-hosted-kubernetes-management-guide-2026/).

## Why GPU Management on Kubernetes Is Complex

Unlike CPU resources, which Kubernetes schedules natively, GPU devices require:
- **Device plugin** — Exposing GPU count and type to the Kubernetes API
- **Driver installation** — Matching NVIDIA driver versions to CUDA requirements across all nodes
- **Container runtime integration** — Enabling containers to access GPU devices via the NVIDIA Container Toolkit
- **Resource scheduling** — Preventing GPU oversubscription and managing GPU sharing
- **Monitoring** — Tracking GPU utilization, memory, temperature, and power consumption

Each of the three solutions addresses these challenges differently.

## NVIDIA GPU Operator: Automated Full-Stack Management

The NVIDIA GPU Operator automates the entire GPU stack on Kubernetes. It deploys NVIDIA drivers, the device plugin, the container toolkit, DCGM exporters for monitoring, and the MIG manager as Kubernetes-managed components.

### Architecture

The GPU Operator runs as a Helm-deployed operator that watches for GPU-equipped nodes and automatically installs and configures all required components:
- NVIDIA driver DaemonSet (or uses pre-installed drivers)
- NVIDIA Container Toolkit DaemonSet
- Kubernetes Device Plugin DaemonSet
- GPU Feature Discovery DaemonSet
- DCGM Exporter DaemonSet for Prometheus metrics
- MIG Manager for Multi-Instance GPU partitioning

### Helm Installation

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
  --set migManager.enabled=false \
  --set gfd.enabled=true \
  --set dcgmExporter.enabled=true
```

### Custom Values Configuration

```yaml
# gpu-operator-values.yaml
driver:
  enabled: true
  version: "550.90.07"
  upgradePolicy:
    autoUpgrade: true
    drain:
      deleteEmptyDir: false
      enable: true
      force: false
      timeoutSeconds: 300

toolkit:
  enabled: true

devicePlugin:
  enabled: true
  config:
    default: "time-slicing"
    time-slicing:
      resources:
        - name: nvidia.com/gpu
          replicas: 2  # 2 pods per GPU

dcgmExporter:
  enabled: true
  serviceMonitor:
    enabled: true

mig:
  strategy: single

gfd:
  enabled: true
```

### GPU Pod Request

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-workload
spec:
  containers:
    - name: training
      image: nvcr.io/nvidia/pytorch:24.01-py3
      command: ["python", "train.py"]
      resources:
        limits:
          nvidia.com/gpu: 1
      env:
        - name: NVIDIA_VISIBLE_DEVICES
          value: all
        - name: NVIDIA_DRIVER_CAPABILITIES
          value: compute,utility
```

### Key Strengths
- Zero manual setup — drivers, toolkit, device plugin deployed automatically
- Automatic driver upgrades with drain-and-replace policy
- Built-in DCGM exporter for Prometheus metrics
- MIG (Multi-Instance GPU) management built in
- Time-slicing for GPU sharing between pods
- GPU Feature Discovery labels nodes with GPU attributes
- Rolling updates and health monitoring

## NVIDIA Container Toolkit: Manual Per-Node GPU Access

The NVIDIA Container Toolkit (formerly nvidia-docker) is the foundational layer that enables containers to access NVIDIA GPUs. It consists of the NVIDIA Container Runtime and the `nvidia-container-cli` utility. This is the manual approach — you install drivers and the toolkit on each node yourself, then use the Kubernetes device plugin separately.

### Architecture

Unlike the GPU Operator, the Container Toolkit requires manual installation on each node:
1. Install NVIDIA drivers on the host OS
2. Install the NVIDIA Container Toolkit package
3. Configure the container runtime (containerd or Docker)
4. Deploy the Kubernetes device plugin as a DaemonSet

### Node Setup Script

```bash
#!/bin/bash
# Run on each GPU node

# Install NVIDIA drivers
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configure containerd
sudo nvidia-ctk runtime configure --runtime=containerd
sudo systemctl restart containerd

# Verify GPU access
docker run --rm --gpus all nvidia/cuda:12.3.1-base-ubuntu22.04 nvidia-smi
```

### Device Plugin Deployment

```yaml
# kubectl apply -f device-plugin.yml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: nvidia-device-plugin-daemonset
  namespace: kube-system
spec:
  selector:
    matchLabels:
      name: nvidia-device-plugin-ds
  template:
    metadata:
      labels:
        name: nvidia-device-plugin-ds
    spec:
      tolerations:
        - key: nvidia.com/gpu
          operator: Exists
          effect: NoSchedule
      containers:
        - image: nvcr.io/nvidia/k8s-device-plugin:v0.15.0
          name: nvidia-device-plugin-ctr
          args: ["--fail-on-init-error=false"]
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
          volumeMounts:
            - name: device-plugin
              mountPath: /var/lib/kubelet/device-plugins
      volumes:
        - name: device-plugin
          hostPath:
            path: /var/lib/kubelet/device-plugins
```

### Key Strengths
- Full control over driver versions and installation timing
- No operator overhead — simpler architecture
- Works with any container runtime (containerd, Docker, CRI-O)
- Minimal resource footprint on control plane
- Good for static clusters where driver updates are managed externally
- Compatible with air-gapped environments (pre-package all components)

## Volcano: Batch GPU Scheduling with Gang Scheduling

Volcano is a Kubernetes-native batch scheduling system that extends the default scheduler with advanced features specifically designed for compute-intensive workloads. While it doesn't manage GPU drivers, it provides superior GPU scheduling for batch and training workloads through gang scheduling, queue management, and resource sharing policies.

### Architecture

Volcano replaces the default Kubernetes scheduler for batch workloads. It introduces:
- **Gang scheduling** — All pods in a job are scheduled together or not at all, preventing deadlocks in distributed training
- **Queue management** — Fair sharing and preemption between teams/projects
- **DRF (Dominant Resource Fairness)** — Fair allocation across heterogeneous resources (CPU, GPU, memory)
- **Binpack strategy** — Minimizes GPU fragmentation
- **Predicate/preemption** — Intelligent pod placement and preemption

### Helm Installation

```bash
helm repo add volcano-sh https://volcano-sh.github.io/helm-charts
helm repo update

helm install volcano volcano-sh/volcano \
  --namespace volcano-system \
  --create-namespace \
  --set basic.webhook_enable=true \
  --set basic.metrics_enable=true
```

### Volcano Job Definition

```yaml
apiVersion: batch.volcano.sh/v1alpha1
kind: Job
metadata:
  name: distributed-training
spec:
  minAvailable: 4  # Gang scheduling: need all 4 workers
  schedulerName: volcano
  queue: default
  tasks:
    - replicas: 4
      name: "worker"
      template:
        spec:
          containers:
            - image: nvcr.io/nvidia/pytorch:24.01-py3
              name: worker
              command: ["torchrun", "--nproc_per_node=1", "--nnodes=4", "--node_rank=$VC_TASK_INDEX", "train.py"]
              resources:
                limits:
                  nvidia.com/gpu: 1
                  cpu: "4"
                  memory: "16Gi"
                requests:
                  nvidia.com/gpu: 1
                  cpu: "4"
                  memory: "16Gi"
          restartPolicy: OnFailure
  plugins:
    env: []
    svc: []
    ssh: []
```

### Queue Configuration

```yaml
apiVersion: scheduling.volcano.sh/v1beta1
kind: Queue
metadata:
  name: training-queue
spec:
  weight: 3
  reclaimable: true
  capability:
    nvidia.com/gpu: 8
    cpu: "32"
    memory: "128Gi"
```

### Key Strengths
- Gang scheduling prevents partial job scheduling deadlocks
- Queue-based resource sharing with weights and preemption
- DRF for fair multi-resource allocation
- Binpack scheduling minimizes GPU fragmentation
- Elastic scheduling for dynamic resource adjustment
- Integration with existing NVIDIA device plugin (works alongside it)
- SLA-based scheduling with deadlines and priority

## Comparison Table

| Feature | NVIDIA GPU Operator | NVIDIA Container Toolkit | Volcano |
|---------|---------------------|-------------------------|---------|
| **Driver Installation** | Automatic (DaemonSet) | Manual per node | Not provided |
| **Device Plugin** | Included | Deploy separately | Works with device plugin |
| **Container Runtime Config** | Automatic | Manual per node | Not applicable |
| **GPU Scheduling** | Kubernetes default | Kubernetes default | Advanced (gang, queue, DRF) |
| **MIG Support** | Built-in (MIG Manager) | Manual configuration | Not provided |
| **Time Slicing** | Configurable via operator | Manual config | Not provided |
| **Monitoring** | DCGM exporter built-in | Manual setup | Metrics via scheduler |
| **Gang Scheduling** | No | No | Yes |
| **Queue Management** | No | No | Yes |
| **Preemption** | Kubernetes default | Kubernetes default | Advanced (SLA-based) |
| **Installation Complexity** | Low (Helm install) | High (manual per node) | Medium (Helm install) |
| **Operator Overhead** | Yes (CRD controllers) | No | Yes (scheduler controllers) |
| **Air-Gap Friendly** | Moderate (mirror images) | Yes (pre-package drivers) | Yes (mirror images) |
| **Best For** | Automated GPU cluster management | Static clusters, full control | Batch/training workloads |

## Combined Deployment: Operator + Volcano

For production environments, the most powerful approach combines the GPU Operator (for driver/device management) with Volcano (for advanced scheduling):

```bash
# Step 1: Install GPU Operator for GPU stack management
helm install gpu-operator nvidia/gpu-operator \
  --namespace gpu-operator --create-namespace

# Step 2: Install Volcano for batch scheduling
helm install volcano volcano-sh/volcano \
  --namespace volcano-system --create-namespace

# Step 3: Submit Volcano jobs that use GPU resources
kubectl apply -f volcano-gpu-job.yaml
```

This combination gives you automated GPU lifecycle management AND intelligent batch scheduling — the best of both worlds.

## Why Self-Host GPU Infrastructure

**Cost:** Enterprise GPUs (A100, H100, L40S) are expensive. Cloud GPU instances carry significant premiums — often 2-3x the cost of owning equivalent hardware over a 3-year period. Self-hosted clusters amortize this cost across all teams and projects.

**Availability:** Cloud GPU instances face chronic supply constraints. Self-hosted clusters provide guaranteed access without competing with other cloud tenants for limited GPU inventory.

**Custom Configurations:** Self-hosted clusters let you use consumer GPUs (RTX 4090), mix generations, customize cooling, and optimize for specific workloads like training, inference, or rendering — configurations rarely available from cloud providers.

**Data Locality:** Large training datasets (hundreds of GB to TB) are expensive to transfer to and from the cloud. Self-hosted GPU clusters keep data local, eliminating transfer costs and latency.

For related Kubernetes infrastructure topics, see our [Kubernetes batch scheduler comparison](../volcano-vs-yunikorn-vs-kueue-kubernetes-batch-scheduler-guide-2026/) which covers Volcano alongside alternatives, and our [Kubernetes CNI guide](../2026-04-21-flannel-vs-calico-vs-cilium-self-hosted-kubernetes-cni-guide/) for network configuration in GPU clusters.

## FAQ

### Can I use the GPU Operator and Volcano together?

Yes, and this is the recommended production setup. The GPU Operator manages the GPU device stack (drivers, device plugin, container toolkit, DCGM), while Volcano handles intelligent scheduling of GPU workloads. They operate at different layers of the stack and complement each other perfectly.

### What is MIG (Multi-Instance GPU) and when should I use it?

MIG partitions a single physical GPU (A100, H100, or L40S) into up to 7 isolated GPU instances, each with dedicated compute cores and memory. This is ideal for running multiple smaller workloads on a single GPU — for example, serving multiple inference models or running hyperparameter search trials. The GPU Operator's MIG Manager automates MIG profile configuration.

### Does the GPU Operator work with non-NVIDIA GPUs?

No, the NVIDIA GPU Operator is specific to NVIDIA GPUs. For AMD GPUs, you need the AMD GPU device plugin and ROCm container toolkit. For Intel GPUs, Intel provides its own device plugin. The GPU scheduling layer (Volcano or Kubernetes default) works with any GPU type through the device plugin abstraction.

### How do I handle GPU driver updates in production?

The GPU Operator supports automated driver upgrades with a drain-and-replace policy: it drains pods from a node, updates the driver, and schedules pods back. For production clusters, it's recommended to test driver updates on a staging node pool first, then roll out to production nodes during maintenance windows. With the manual Container Toolkit approach, you manage driver updates through your configuration management system (Ansible, Puppet, etc.).

### What is gang scheduling and why does it matter for distributed training?

Gang scheduling ensures that all pods in a distributed training job are scheduled simultaneously or not at all. Without gang scheduling, Kubernetes might schedule 3 out of 4 training workers, leaving the job unable to start. The 4th worker waits indefinitely for a GPU while the first 3 sit idle. Volcano's gang scheduling prevents this by reserving resources for all workers before launching any of them.

### How do I share a single GPU between multiple pods?

The GPU Operator supports time-slicing, which allows multiple pods to share a single GPU by interleaving their execution. Configure this via the GPU Operator's `time-slicing` resource configuration (see the Helm values above). Each GPU can be divided into 2, 4, or 8 time-slice replicas. Note that this increases total training time proportionally but improves GPU utilization for smaller workloads.

### Can I monitor GPU utilization per namespace or per team?

With the GPU Operator's DCGM exporter feeding Prometheus, you can create Grafana dashboards that break down GPU utilization by namespace, pod, or team using Kubernetes labels. Volcano adds queue-based accounting, letting you track GPU usage per queue (team/project). Combined, you get comprehensive GPU accounting across the cluster.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted GPU Management in Kubernetes: NVIDIA GPU Operator vs Container Toolkit vs Volcano Guide 2026",
  "description": "Compare self-hosted GPU management solutions for Kubernetes — NVIDIA GPU Operator, NVIDIA Container Toolkit, and Volcano GPU scheduler. Learn which GPU approach fits your cluster with Helm configs, MIG support, and deployment guides.",
  "datePublished": "2026-05-04",
  "dateModified": "2026-05-04",
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
