---
title: "Self-Hosted Alternative Kubernetes Schedulers: Volcano vs Apache YuniKorn vs Scheduler Plugins"
date: "2026-05-16"
tags: ["kubernetes", "scheduling", "volcano", "yunikorn", "batch-processing", "cnca"]
draft: false
---

The default Kubernetes scheduler is designed primarily for long-running services — web servers, databases, and microservices that stay alive indefinitely. But what happens when you need to run batch jobs, ML training workloads, or high-performance computing tasks that require gang scheduling, queue management, or custom scheduling logic?

The answer is alternative schedulers. This guide compares three out-of-tree Kubernetes schedulers that extend the platform's capabilities for specialized workloads: **Volcano**, **Apache YuniKorn**, and **Kubernetes Scheduler Plugins**.

## Why the Default Scheduler Is Not Enough

Kubernetes' built-in scheduler follows a simple model: find a node with enough resources, place the pod there. This works well for stateless microservices but breaks down for several important workload types:

- **Batch processing** — Jobs that need all pods scheduled simultaneously (gang scheduling) or in a specific order
- **ML training** — Distributed training jobs where all worker pods must start together or the job fails
- **High-performance computing** — Workloads requiring NUMA-aware placement, GPU topology awareness, or custom resource bin-packing
- **Multi-tenant clusters** — Organizations that need hierarchical queue management, fair sharing, and capacity guarantees across teams
- **Priority-based scheduling** — Workloads with complex preemption rules where high-priority jobs must displace lower-priority ones

Alternative schedulers address these gaps by implementing the Kubernetes scheduler framework's extensibility points while adding domain-specific features.

## Volcano

Volcano is a CNCF-incubated batch scheduling system originally developed by Huawei. It provides a complete batch scheduling solution with gang scheduling, fair sharing, resource reservation, and a rich plugin architecture.

### Architecture

Volcano replaces the default scheduler by registering as a custom scheduler name. It uses Custom Resource Definitions (CRDs) to define batch-oriented workload types:

- **Job** — batch job with pod templates and scheduling policies
- **PodGroup** — grouping of pods that must be scheduled together (gang scheduling)
- **Queue** — hierarchical queue for fair sharing and priority management

```yaml
apiVersion: batch.volcano.sh/v1alpha1
kind: Job
metadata:
  name: distributed-training
spec:
  minAvailable: 3
  schedulerName: volcano
  plugins:
    ssh: []
    svc: []
  tasks:
    - replicas: 1
      name: "master"
      template:
        spec:
          containers:
            - name: master
              image: pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime
              command: ["python", "train.py", "--master"]
    - replicas: 4
      name: "worker"
      template:
        spec:
          containers:
            - name: worker
              image: pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime
              command: ["python", "train.py", "--worker"]
```

Key features:
- **Gang scheduling** — ensures all pods in a job are scheduled together or none at all
- **DRF (Dominant Resource Fairness)** — fair sharing across multiple resource types (CPU, memory, GPU)
- **Preemption** — higher-priority jobs can evict lower-priority ones
- **Plugin system** — extensible scheduling logic via the action-plugin architecture
- **Built-in job types** — native support for MPI, TensorFlow, PyTorch, and Spark workloads
- **5,562 GitHub stars** — active CNCF community

### Deployment

```bash
kubectl apply -f https://raw.githubusercontent.com/volcano-sh/volcano/master/installer/volcano-development.yaml

# Verify
kubectl get pods -n volcano-system
```

Or via Helm:

```bash
helm install volcano volcano/volcano \
  --namespace volcano-system \
  --create-namespace
```

## Apache YuniKorn

Apache YuniKorn (originally Cloudbreak Scheduler) is a resource scheduler for Kubernetes that brings enterprise-grade queue management, capacity planning, and multi-tenant isolation to the platform. It originated from the Hadoop/YARN ecosystem and brings decades of scheduling experience from big data processing.

### Architecture

YuniKorn operates as a secondary scheduler alongside the default Kubernetes scheduler. It intercepts unscheduled pods via a mutating webhook and schedules them according to its hierarchical queue structure:

```yaml
apiVersion: yaml
kind: queues
queues:
  - name: root
    properties:
      parent: false
    queues:
      - name: engineering
        properties:
          capacity: "40%"
          maxCapacity: "60%"
        queues:
          - name: ml-team
            properties:
              capacity: "50%"
              maxCapacity: "80%"
          - name: data-team
            properties:
              capacity: "50%"
              maxCapacity: "80%"
      - name: marketing
        properties:
          capacity: "30%"
          maxCapacity: "50%"
```

Key features:
- **Hierarchical queues** — multi-level queue hierarchy with guaranteed and maximum capacity
- **Fair scheduling** — resources are shared fairly across queues based on configured weights
- **Application awareness** — supports Spark, Flink, and other big data frameworks natively
- **Node partitioning** — partition cluster nodes into isolated resource pools
- **User/group mapping** — map Kubernetes service accounts to queue placements
- **1,011 GitHub stars** — Apache Software Foundation project

### Deployment

```bash
helm install yunikorn yunikorn/yunikorn \
  --namespace yunikorn \
  --create-namespace \
  --set scheduler.plugin.enabled=true
```

The YuniKorn configuration is managed via a ConfigMap:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: yunikorn-configs
  namespace: yunikorn
data:
  queues.yaml: |
    queues:
      - name: root
        queues:
          - name: default
            properties:
              capacity: "100%"
```

## Kubernetes Scheduler Plugins

Kubernetes Scheduler Plugins is an official Kubernetes SIG project that provides a collection of out-of-tree scheduler plugins built on the Kubernetes scheduler framework. Rather than replacing the scheduler entirely, it allows you to extend the default scheduler with additional scheduling logic.

### Architecture

Scheduler Plugins uses the Kubernetes scheduler framework's extension points to inject custom scheduling logic at various stages: pre-filter, filter, pre-score, score, reserve, and permit. This approach is more lightweight than full scheduler replacement.

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
leaderElection:
  leaderElect: true
clientConnection:
  kubeconfig: "/etc/kubernetes/scheduler.conf"
profiles:
  - schedulerName: default-scheduler
    plugins:
      queueSort:
        enabled:
          - name: Coscheduling
      preFilter:
        enabled:
          - name: Coscheduling
      permit:
        enabled:
          - name: Coscheduling
      reserve:
        enabled:
          - name: Coscheduling
          - name: NodeResourcesAllocatable
    pluginConfig:
      - name: Coscheduling
        args:
          permittedWaitingTime: "30s"
          defaultTimeout: "60s"
```

Key features:
- **Official Kubernetes project** — maintained under kubernetes-sigs, aligned with upstream releases
- **Coscheduling plugin** — gang scheduling via the permit plugin extension point
- **Capacity scheduling** — hierarchical queue management similar to YuniKorn
- **Node resource topology** — NUMA-aware scheduling for HPC workloads
- **Lightweight** — runs as an extension to the default scheduler, not a replacement
- **1,292 GitHub stars** — backed by the Kubernetes community

### Deployment

Deploy as a separate scheduler deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: scheduler-plugins-scheduler
  namespace: kube-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: scheduler-plugins-scheduler
  template:
    spec:
      containers:
        - name: scheduler
          image: registry.k8s.io/scheduler-plugins/kube-scheduler:latest
          command:
            - kube-scheduler
            - --config=/etc/kubernetes/scheduler-config.yaml
          volumeMounts:
            - name: scheduler-config
              mountPath: /etc/kubernetes
      volumes:
        - name: scheduler-config
          configMap:
            name: scheduler-plugins-config
```

## Comparison Table

| Feature | Volcano | Apache YuniKorn | Scheduler Plugins |
|---------|---------|----------------|-------------------|
| **Project status** | CNCF Incubating | Apache Software Foundation | Kubernetes SIG |
| **Architecture** | Full scheduler replacement | Secondary scheduler (webhook) | Default scheduler extension |
| **Gang scheduling** | Yes (native) | Yes (via application groups) | Yes (Coscheduling plugin) |
| **Queue management** | Yes (flat + hierarchical) | Yes (deeply hierarchical) | Yes (Capacity plugin) |
| **Fair sharing** | DRF algorithm | Weighted fair sharing | Proportional |
| **Preemption** | Yes | Yes | Via default scheduler |
| **Big data support** | MPI, TF, PyTorch, Spark | Spark, Flink, Hive | Generic |
| **GPU awareness** | Yes | Yes | Via NodeResourceTopology |
| **Stars (GitHub)** | 5,562+ | 1,011+ | 1,292+ |
| **Learning curve** | Moderate | Moderate | Low (extends default) |
| **Best for** | ML/batch workloads | Multi-tenant enterprise | Extending default scheduler |

## Why Use Alternative Schedulers in Kubernetes?

The default Kubernetes scheduler is intentionally simple — it optimizes for general-purpose workloads and avoids complexity. But as Kubernetes expands beyond web services into data engineering, machine learning, and HPC, the scheduling requirements become more sophisticated.

**Gang scheduling is essential for distributed workloads.** In ML training or MPI jobs, if only 3 of 4 worker pods get scheduled, the job hangs indefinitely. Gang scheduling ensures all-or-nothing placement.

**Multi-tenant fairness prevents resource monopolization.** Without hierarchical queues, a single team can consume all cluster resources, starving other teams. Queue-based scheduling enforces capacity guarantees.

**Custom bin-packing reduces infrastructure costs.** Alternative schedulers can pack workloads more efficiently by considering NUMA topology, GPU affinity, and custom resource dimensions that the default scheduler ignores.

For teams running batch or ML workloads, see our [distributed task scheduling comparison](../2026-04-29-xxl-job-vs-powerjob-vs-dolphinscheduler-distributed-task-scheduling-guide/) and [Kubernetes resource optimization guide](../2026-05-07-descheduler-vs-vpa-vs-goldilocks-kubernetes-resource-optimization/). Our [GPU management in Kubernetes guide](../2026-05-04-self-hosted-gpu-management-kubernetes-nvidia-operator-container-toolkit-volcano/) covers the Volcano scheduler's GPU scheduling capabilities in more detail.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Alternative Kubernetes Schedulers: Volcano vs Apache YuniKorn vs Scheduler Plugins",
  "description": "Compare three out-of-tree Kubernetes schedulers for batch jobs, ML training, and multi-tenant workloads: Volcano (CNCF), Apache YuniKorn (hierarchical queues), and Kubernetes Scheduler Plugins (gang scheduling).",
  "datePublished": "2026-05-16",
  "dateModified": "2026-05-16",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  }
}
</script>

## FAQ

### When should I use Volcano vs the default Kubernetes scheduler?

Use Volcano when you run batch jobs, ML training, or HPC workloads that require gang scheduling (all-or-nothing pod placement), fair resource sharing across teams, or job-level preemption. For standard microservices, the default scheduler is sufficient and simpler to operate.

### Can I run multiple schedulers in the same Kubernetes cluster?

Yes. Kubernetes supports running multiple schedulers simultaneously. Pods specify which scheduler to use via the `schedulerName` field in their pod spec. The default scheduler handles pods without an explicit scheduler name, while alternative schedulers handle pods that request them.

### Does Apache YuniKorn replace the default Kubernetes scheduler?

No. YuniKorn runs alongside the default scheduler and intercepts unscheduled pods through a mutating webhook. This approach allows you to use YuniKorn for specific workloads while keeping the default scheduler for everything else — a lower-risk deployment model.

### What is gang scheduling and why does it matter?

Gang scheduling ensures that a group of related pods are all scheduled together, or none at all. This is critical for distributed ML training, MPI jobs, and any workload where partial scheduling results in a hung or failed job. Without gang scheduling, a 4-worker training job might start 3 workers that wait forever for the 4th.

### How do Kubernetes Scheduler Plugins differ from Volcano?

Scheduler Plugins extend the default scheduler with additional logic at specific extension points, while Volcano replaces the scheduler entirely. Plugins are lighter weight and easier to adopt, but Volcano offers more comprehensive batch scheduling features out of the box. Choose Plugins for incremental enhancements and Volcano for full batch scheduling capabilities.

### Are alternative schedifiers production-ready?

Yes. Volcano is used in production by major cloud providers and enterprises for ML and batch workloads. YuniKorn powers multi-tenant Kubernetes clusters at companies with hundreds of teams. Scheduler Plugins is an official Kubernetes SIG project with stable releases aligned with Kubernetes version cycles.
