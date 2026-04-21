---
title: "Volcano vs YuniKorn vs Kueue: Best Kubernetes Batch Scheduler 2026"
date: 2026-04-21
tags: ["comparison", "guide", "kubernetes", "batch-processing", "scheduling", "self-hosted"]
draft: false
description: "Compare Volcano, Apache YuniKorn, and Kueue — the top open-source batch schedulers for Kubernetes. Learn which one fits your HPC, ML, or multi-tenant workload queueing needs."
---

[kubernetes](https://kubernetes.io/) was designed primarily for long-running services, not batch workloads. The default scheduler makes no distinction between a web server that needs to stay up 24/7 and a data processing job that should run to completion and exit. For organizations running high-performance computing (HPC), machine learning training, ETL pipelines, or any job-queueing workload on self-hosted Kubernetes clusters, the default scheduler falls short.

Three open-source projects have emerged to fill this gap: [**Volcano**](https://volcano.sh/), [**Apache YuniKorn**](https://yunikorn.apache.org/), and [**Kueue**](https://kueue.sigs.k8s.io/). Each takes a different approach to batch scheduling on Kubernetes, with distinct architectures, feature sets, and target use cases.

This guide compares all three projects side-by-side, provides real installation examples, and helps you choose the right scheduler for your cluster.

## Why Self-Host a Batch Scheduler on Kubernetes?

Batch workloads have fundamentally different scheduling requirements than microservices:

- **Gang scheduling**: All pods in a job must start together, or none at all. Partial starts cause deadlocks in distributed training and MPI workloads.
- **Resource quotas at the job level**: Instead of per-pod limits, you need to manage quotas across entire jobs with varying resource demands.
- **Fair sharing across teams**: Multi-tenant clusters need queue-based fair sharing so one team's large jobs don't starve everyone else.
- **Job preemption and reclamation**: Higher-priority workloads should be able to preempt lower-priority ones without manual intervention.
- **Topology awareness**: GPU and network-heavy workloads benefit from scheduling decisions that consider physical node topology.

While commercial cloud providers offer managed solutions for these scenarios, self-hosted alternatives give you full control, zero per-job costs, and the ability to customize scheduling policies to your exact needs.

## Project Overview

| Feature | Volcano | Apache YuniKorn | Kueue |
|---------|---------|-----------------|-------|
| **GitHub Stars** | 5,478 | 1,008 | 2,450 |
| **Last Updated** | April 2026 | April 2026 | April 2026 |
| **Language** | Go | Go | Go |
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| **Governance** | CNCF Incubating | Apache Software Foundation | Kubernetes SIG (sigs.k8s.io) |
| **Installation** | Helm / kubectl apply | Helm | kubectl apply (manifests) |
| **Min Kubernetes** | 1.20+ | 1.23+ | 1.29+ |
| **Gang Scheduling** | Yes (PodGroup CRD) | Yes (task groups) | Via ClusterQueue preemption |
| **Fair Sharing** | Yes (queues + weights) | Yes (FIFO, fair, state-aware) | Yes (cohorts + flavor fungibility) |
| **Preemption** | Yes | Yes | Yes |
| **GPU Support** | Yes (device-aware) | Yes | Via ResourceFlavor |
| **Multi-cluster** | No | Limited | Yes (MultiKueue) |
| **Web UI** | Yes (built-in) | Yes (built-in) | No (kubectl + metrics) |
| **Plain Pod Support** | No (needs Volcano CRDs) | Yes (via shim) | Yes (native) |
| **Topology-Aware** | Yes | No | Yes (TAS) |

## Volcano: The CNCF Batch System

Volcano is the most mature and feature-complete batch scheduler in the Kubernetes ecosystem. Originally developed by Huawei and donated to CNCF, it provides a custom scheduler plugin architecture that replaces the default kube-scheduler for batch workloads.

### Key Features

- **PodGroup CRD**: Defines scheduling groups where all pods must be scheduled together (gang scheduling).
- **Multiple scheduling policies**: FIFO, Priority, and custom plugins for binpack, spread, and node-order.
- **Built-in web UI**: Monitor queues, jobs, and resource allocation in real time.
- **Rich ecosystem integrations**: Native support for Spark, TensorFlow, PyTorch, MPI, Flink, Ray, Kubeflow, and more.
- **GPU topology awareness**: Prevents GPU fragmentation by modeling physical GPU interconnect topology.

### Installation

Volcano installs as a set of Custom Resource Definitions and a scheduler deployment. The fastest way to get started is via Helm:

```bash
helm repo add volcano-sh https://volcano-sh.github.io/helm-charts
helm repo update
helm install volcano volcano-sh/volcano --namespace volcano-system --create-namespace
```

Or use kubectl with the official manifests:

```bash
kubectl apply -f https://raw.githubusercontent.com/volcano-sh/volcano/master/installer/volcano-development.yaml
```

### Creating a Batch Job with Volcano

Once installed, define a PodGroup and use the `volcano.sh/job` kind:

```yaml
apiVersion: batch.volcano.sh/v1alpha1
kind: Job
metadata:
  name: distributed-training
  namespace: default
spec:
  minAvailable: 3
  schedulerName: volcano
  plugins:
    svc: []
  tasks:
    - replicas: 3
      name: "worker"
      template:
        spec:
          containers:
            - name: trainer
              image: pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime
              command: ["python", "/app/train.py"]
              resources:
                requests:
                  cpu: "4"
                  memory: "16Gi"
                  nvidia.com/gpu: "1"
                limits:
                  cpu: "4"
                  memory: "16Gi"
                  nvidia.com/gpu: "1"
          restartPolicy: Never
```

The `minAvailable: 3` ensures gang scheduling — all three workers start together or not at all. This prevents partial deployments that would deadlock in distributed training.

## Apache YuniKorn: The Universal Scheduler

Apache YuniKorn takes a different approach. Rather than being Kubernetes-specific, it is designed as a **universal resource scheduler** that works across multiple orchestration platforms through a shim layer. The Kubernetes shim (`yunikorn-k8shim`) adapts YuniKorn to work as a custom Kubernetes scheduler.

### Key Features

- **Cross-platform design**: The same scheduler core can work with Kubernetes, YARN, or other resource managers.
- **Three scheduling policies**: FIFO for simple ordering, fair sharing for multi-tenant clusters, and state-aware for dynamic workloads.
- **Application-aware scheduling**: Tracks application lifecycle states and can kill idle applications to reclaim resources.
- **Queue hierarchy**: Multi-level queue structures with guaranteed and maximum resource allocations per queue.
- **Built-in web UI**: Visual queue hierarchy, application tracking, and node utilization dashboard.

### Installation

YuniKorn installs via Helm from the release repository:

```bash
helm repo add yunikorn https://apache.github.io/yunikorn-release
helm repo update
helm install yunikorn yunikorn/yunikorn --namespace yunikorn --create-namespace
```

Configure the scheduler to use YuniKorn by patching the kube-scheduler:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: yunikorn-configs
  namespace: yunikorn
data:
  queues.yaml: |
    partitions:
      - name: default
        queues:
          - name: root
            queues:
              - name: data-team
                properties:
                  parent: root
                  maxResource:
                    memory: "64Gi"
                    vcore: 32
              - name: ml-team
                properties:
                  parent: root
                  maxResource:
                    memory: "128Gi"
                    vcore: 64
```

### Running a Batch Job with YuniKorn

YuniKorn works with standard Kubernetes batch Jobs — no custom CRDs required for basic usage. Label your pods to route them through the YuniKorn scheduler:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: etl-pipeline
  namespace: default
  labels:
    applicationId: "etl-job-001"
    queue: "data-team"
spec:
  completions: 5
  parallelism: 5
  template:
    metadata:
      labels:
        applicationId: "etl-job-001"
        queue: "data-team"
    spec:
      schedulerName: yunikorn
      containers:
        - name: etl-worker
          image: apache/spark:3.5.0
          command: ["spark-submit", "--class", "ETLJob", "/app/etl.jar"]
          resources:
            requests:
              cpu: "2"
              memory: "8Gi"
            limits:
              cpu: "2"
              memory: "8Gi"
      restartPolicy: Never
```

The `queue: "data-team"` label assigns this job to the data-team queue defined in `queues.yaml`, enforcing resource limits and fair sharing automatically.

## Kueue: Kubernetes-Native Job Queueing

Kueue is the newest entrant, developed as a Kubernetes SIG (Special Interest Group) project. Unlike Volcano and YuniKorn, Kueue is not a full scheduler replacement — it is a **job-level admission controller** that works alongside the default kube-scheduler.

Kueue decides **when** a job should be admitted (its pods can be created) based on queue position and resource availability. Once admitted, the default kube-scheduler handles **where** the pods land.

### Key Features

- **Admission-based architecture**: Does not replace the kube-scheduler; cooperates with it.
- **ClusterQueues and LocalQueues**: Hierarchical queue model with cohort-based fair sharing and resource flavor fungibility.
- **Multi-cluster support (MultiKueue)**: Dispatch jobs across multiple Kubernetes clusters, automatically seeking available capacity.
- **Topology-Aware Scheduling (TAS)**: Optimize pod-to-pod communication by considering data center topology.
- **Built-in workload integrations**: Native support for BatchJob, Kubeflow, RayJob, JobSet, plain Pods, and Deployments.
- **ProvisioningRequest integration**: Works with cluster-autoscaler to trigger node provisioning for queued jobs.
- **Partial admission**: Run jobs with reduced parallelism when full quota is unavailable.

### Installation

Kueue installs via a single manifest — no Helm required:

```bash
kubectl apply --server-side -f https://github.com/kubernetes-sigs/kueue/releases/download/v0.17.1/manifests.yaml
```

### Configuring Kueue

Set up a minimal ClusterQueue and LocalQueue:

```yaml
apiVersion: kueue.x-k8s.io/v1beta1
kind: ResourceFlavor
metadata:
  name: default-flavor
---
apiVersion: kueue.x-k8s.io/v1beta1
kind: ClusterQueue
metadata:
  name: cluster-queue
spec:
  namespaceSelector: {}
  queueingStrategy: BestEffortFIFO
  resourceGroups:
    - coveredResources: ["cpu", "memory", "nvidia.com/gpu"]
      flavors:
        - name: default-flavor
          resources:
            - name: "cpu"
              nominalQuota: 100
            - name: "memory"
              nominalQuota: 512Gi
            - name: "nvidia.com/gpu"
              nominalQuota: 16
---
apiVersion: kueue.x-k8s.io/v1beta1
kind: LocalQueue
metadata:
  name: research-queue
  namespace: default
spec:
  clusterQueue: cluster-queue
```

### Running a Batch Job with Kueue

Reference the LocalQueue in your Job's `queueName` field:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: model-training
  namespace: default
  labels:
    kueue.x-k8s.io/queue-name: research-queue
spec:
  parallelism: 4
  completions: 4
  template:
    metadata:
      labels:
        kueue.x-k8s.io/queue-name: research-queue
    spec:
      containers:
        - name: trainer
          image: pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime
          command: ["python", "/app/train_model.py"]
          resources:
            requests:
              cpu: "4"
              memory: "16Gi"
              nvidia.com/gpu: "1"
            limits:
              cpu: "4"
              memory: "16Gi"
              nvidia.com/gpu: "1"
      restartPolicy: Never
```

Kueue holds the Job in a pending state until sufficient resources are available in the ClusterQueue, then admits it for the default scheduler to place the pods.

## Architecture Comparison

The fundamental difference between these three projects lies in **where they sit in the Kubernetes scheduling stack**:

```
┌─────────────────────────────────────────────────────────┐
│                    Kubernetes API Server                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Volcano:     Replaces kube-scheduler for batch jobs    │
│               Custom scheduler plugin + PodGroup CRD    │
│                                                         │
│  YuniKorn:    Replaces kube-scheduler via shim layer    │
│               Universal core with K8s adapter            │
│                                                         │
│  Kueue:       Admission controller before kube-scheduler│
│               Decides WHEN; kube-scheduler decides WHERE │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                  kube-scheduler (default)                │
├─────────────────────────────────────────────────────────┤
│                     Worker Nodes                         │
└─────────────────────────────────────────────────────────┘
```

**Volcano and YuniKorn** act as custom schedulers — they receive unscheduled pods from the API server and make placement decisions directly. This gives them full control over scheduling logic but requires careful coexistence with the default scheduler.

**Kueue** takes a cooperative approach — it admits or rejects jobs based on queue state, then lets the default kube-scheduler handle actual pod placement. This means less risk of conflicts with other scheduler customizations but also less fine-grained control over placement decisions.

## Choosing the Right Scheduler

| Scenario | Recommended Scheduler | Why |
|----------|----------------------|-----|
| HPC/ML training with gang scheduling | Volcano | Most mature gang scheduling, PodGroup CRD, GPU topology awareness |
| Multi-tenant queue fair sharing | YuniKorn | Excellent queue hierarchy, fair sharing across departments |
| Kubernetes-native simplicity | Kueue | No custom scheduler, works with stock kube-scheduler, minimal config |
| Multi-cluster job dispatching | Kueue | MultiKueue dispatches jobs across clusters automatically |
| Existing Spark/Hadoop workloads | YuniKorn | Universal scheduler with YARN shim for hybrid environments |
| Topology-aware GPU scheduling | Volcano or Kueue | Volcano for GPU topology; Kueue TAS for data center topology |
| Plain Pod scheduling (no CRDs) | Kueue or YuniKorn | Both support standard Kubernetes Jobs without custom resources |
| Web UI for monitoring | Volcano or YuniKorn | Both include built-in dashboards out of the box |

## Monitoring and Observability

Al[prometheus](https://prometheus.io/)hedulers expose Prometheus metrics for integration with your existing monitoring stack. For a complete self-hosted observability setup, consider pairing your scheduler with dedicated [Prometheus and Grafana instances](https://www.pistack.xyz/posts/) to track queue depths, admission latency, resource utilization, and job completion times.

Volcano provides the richest built-in monitoring with its dedicated monitoring manifest (`volcano-monitoring.yaml`) that pre-configures Grafana dashboards. Kueue offers the most comprehensive Prometheus metrics of the three, with dedicated metrics for admission wait times, queue depth, and resource preemption events.

For clusters running multiple schedulers or com[plex](https://www.plex.tv/) job orchestration, you may also want a dedicated [Kubernetes-native CI/CD pipeline](../tekton-vs-argo-workflows-vs-jenkins-x-self-hosted-kubernetes-native-cicd-guide-2026/) to automate scheduler configuration testing and rollout.

## Migration Considerations

Moving from one batch scheduler to another requires careful planning:

1. **CRD compatibility**: Volcano's PodGroup CRDs are not compatible with Kueue's LocalQueue/ClusterQueue model. Jobs must be rewritten.
2. **Scheduler name**: All job specs reference the scheduler by name (`schedulerName: volcano` vs `schedulerName: yunikorn`). Kueue does not require a custom scheduler name.
3. **Queue hierarchy**: YuniKorn's queue definitions in `queues.yaml` use a different format than Kueue's ClusterQueue CRDs or Volcano's queue CRDs.
4. **Coexistence**: All three can coexist with the default kube-scheduler, but you must ensure that only the intended scheduler handles batch workload pods.

For organizations managing multiple Kubernetes clusters — perhaps across different [lightweight Kubernetes distributions](../k3s-vs-k0s-vs-talos-linux-self-hosted-kubernetes-guide-2026/) — Kueue's MultiKueue feature offers the simplest path to unified job queueing across the fleet.

## FAQ

### Do I need a batch scheduler if I only run simple CronJobs?

For basic CronJobs that run small, non-resource-intensive tasks, the default Kubernetes scheduler is usually sufficient. Batch schedulers become necessary when you run distributed jobs that require gang scheduling, fair sharing across teams, GPU allocation, or queue-based admission control. If your jobs frequently get stuck waiting for resources or you need guaranteed resource quotas per team, a batch scheduler is worth the investment.

### Can I run multiple batch schedulers on the same cluster?

Yes. Volcano, YuniKorn, and the default kube-scheduler can coexist on the same cluster. You control which scheduler handles each workload using the `schedulerName` field in your Pod specs. Kueue is different — it does not replace any scheduler but instead acts as an admission controller that works alongside whatever scheduler you use.

### Which scheduler has the best Kubernetes API compatibility?

Kueue has the strongest native Kubernetes integration because it is developed as a Kubernetes SIG project. Its APIs follow Kubernetes conventions closely, and it works with standard Jobs, Deployments, and StatefulSets without requiring custom scheduler names. Volcano and YuniKorn require custom CRDs or labels to function properly.

### How does gang scheduling work in practice?

Gang scheduling ensures that all pods in a group are scheduled simultaneously or not at all. Without it, a distributed training job might have 3 of 4 workers scheduled but the fourth waiting indefinitely for resources — causing the three running workers to block forever. Volcano implements this via PodGroup CRDs with `minAvailable` fields. YuniKorn achieves it through task group labels. Kueue handles it by only admitting a job when sufficient quota exists for all pods simultaneously.

### Which scheduler should I choose for GPU workloads?

For GPU-intensive workloads like machine learning training, Volcano has the most mature GPU support including topology-aware scheduling that prevents GPU fragmentation. Kueue supports GPU through ResourceFlavors and can integrate with cluster-autoscaler for GPU node provisioning. YuniKorn supports GPU resource tracking but lacks topology awareness. If your primary workload is GPU batch processing, Volcano is the strongest choice.

### Is there a performance difference between the schedulers?

Benchmarking results vary by workload, but general patterns are: Kueue has the lowest overhead since it does not replace the kube-scheduler. Volcano adds moderate overhead due to its custom scheduling loop but provides more optimized placement decisions. YuniKorn's shim layer adds a small overhead on Kubernetes but the universal core is highly optimized for large-scale multi-tenant environments with thousands of concurrent queues.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Volcano vs YuniKorn vs Kueue: Best Kubernetes Batch Scheduler 2026",
  "description": "Compare Volcano, Apache YuniKorn, and Kueue — the top open-source batch schedulers for Kubernetes. Learn which one fits your HPC, ML, or multi-tenant workload queueing needs.",
  "datePublished": "2026-04-21",
  "dateModified": "2026-04-21",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>
