---
title: "Self-Hosted Kubernetes Batch Job Management: Queue Systems, Operators & Orchestrators"
date: "2026-05-20"
description: "Guide to managing Kubernetes batch and parallel jobs at scale — compare Volcano, Kueue, and native Job controllers for GPU workloads, ML training pipelines, and large-scale batch processing."
tags: ["kubernetes", "batch-jobs", "job-queue", "volcano", "ml-infrastructure", "gpu-workloads"]
draft: false
---

Kubernetes Jobs are designed for batch workloads — finite tasks that run to completion and terminate. But when you're running hundreds of batch jobs per day for ML training, data processing, or CI/CD pipelines, the native Job controller becomes a bottleneck. You need queueing, priority management, gang scheduling (all-or-nothing scheduling for multi-pod jobs), and fair resource sharing across teams.

This guide compares three approaches to Kubernetes batch job management: **native Jobs**, **Volcano** (CNCF batch scheduling system), and **Kueue** (Kubernetes-native job queueing). Each addresses different aspects of the batch workload challenge.

## Comparison Table

| Feature | Native K8s Jobs | Volcano | Kueue |
|---|---|---|---|
| Job Queueing | None (runs immediately) | JobQueue with priorities | ClusterQueue + LocalQueue |
| Gang Scheduling | No | Yes (minAvailable) | Yes (via PodSets) |
| Fair Sharing | No | Queue-based fair sharing | Cohort-based fair sharing |
| Preemption | Limited | Full preemption support | Preemption + requeuing |
| GPU Awareness | Resource requests only | GPU-aware scheduling | Resource flavor support |
| Plugin System | None | Yes (scheduling, capacity) | Extensible via webhooks |
| GitHub Stars | (built-in) | ~4,400 (volcano-sh/volcano) | ~680 (kubernetes-sigs/kueue) |
| CNCF Status | Built-in | Incubating | Graduated (K8s 1.32+) |
| ML Workload Focus | No | Yes (TFJob, PyTorch, MPI) | Yes (job flavors) |
| Multi-Tenancy | Namespace isolation | Queue hierarchies | ClusterQueue + cohort |

## Native Kubernetes Job Controller

The built-in Job controller handles basic batch workloads with completion tracking and retry support.

### Parallel Job Configuration

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: data-processing-pipeline
  namespace: analytics
spec:
  parallelism: 10
  completions: 50
  completionMode: Indexed
  backoffLimit: 3
  activeDeadlineSeconds: 7200
  suspend: false
  ttlSecondsAfterFinished: 86400
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: processor
          image: data-processor:latest
          command: ["python", "process.py"]
          args: ["--batch-id", "$(JOB_COMPLETION_INDEX)"]
          env:
            - name: JOB_COMPLETION_INDEX
              valueFrom:
                fieldRef:
                  fieldPath: metadata.annotations['batch.kubernetes.io/job-completion-index']
          resources:
            requests:
              memory: "2Gi"
              cpu: "1"
              nvidia.com/gpu: "1"
            limits:
              nvidia.com/gpu: "1"
```

### Indexed Completion for Parallel Processing

The `Indexed` completion mode assigns each Pod a unique index (0 to N-1), enabling parallel processing where each Pod handles a specific partition of the workload.

```bash
# Monitor Job progress
kubectl get job data-processing-pipeline -n analytics   -o custom-columns='NAME:.metadata.name,COMPLETE:.status.succeeded,FAILED:.status.failed,ACTIVE:.status.active'

# View indexed Pod status
kubectl get pods -n analytics -l job-name=data-processing-pipeline   -o custom-columns='POD:.metadata.name,INDEX:.metadata.annotations['"'"'batch.kubernetes.io/job-completion-index'"'"'],STATUS:.status.phase'
```

## Volcano: Batch Scheduling System

Volcano is a CNCF-incubating batch scheduling system designed for high-performance compute workloads, particularly ML training, scientific computing, and large-scale data processing.

### Volcano Installation and Scheduler Configuration

```yaml
apiVersion: "volcano.sh/v1beta1"
kind: Queue
metadata:
  name: ml-team
spec:
  weight: 5
  reclaimable: true
  capability:
    cpu: "100"
    memory: "400Gi"
    nvidia.com/gpu: "8"
  guarantee:
    resource:
      cpu: "20"
      memory: "80Gi"
---
apiVersion: "volcano.sh/v1beta1"
kind: Job
metadata:
  name: distributed-training
  namespace: ml
spec:
  minAvailable: 4
  schedulerName: volcano
  queue: ml-team
  priorityClassName: high-priority
  tasks:
    - replicas: 1
      name: ps
      template:
        spec:
          containers:
            - name: parameter-server
              image: tensorflow/tensorflow:2.15.0-gpu
              command: ["python", "ps_server.py"]
              resources:
                requests:
                  cpu: "4"
                  memory: "16Gi"
    - replicas: 3
      name: worker
      template:
        spec:
          containers:
            - name: worker
              image: tensorflow/tensorflow:2.15.0-gpu
              command: ["python", "train_worker.py"]
              resources:
                requests:
                  cpu: "8"
                  memory: "32Gi"
                  nvidia.com/gpu: "1"
                limits:
                  nvidia.com/gpu: "1"
    - replicas: 1
      name: evaluator
      template:
        spec:
          containers:
            - name: evaluator
              image: tensorflow/tensorflow:2.15.0-gpu
              command: ["python", "evaluate.py"]
              resources:
                requests:
                  cpu: "2"
                  memory: "8Gi"
  plugins:
    env: []
    svc: []
    ssh: []
```

### Gang Scheduling with Volcano

Gang scheduling ensures that all Pods in a Job are scheduled together or none at all — critical for distributed training where a partial deployment is useless.

```yaml
spec:
  minAvailable: 4  # All 4 Pods (1 PS + 3 Workers) must schedule together
  schedulerName: volcano
  queues:
    - name: ml-team
  plugins:
    drf: []        # Dominant Resource Fairness
    gang: []       # Gang scheduling plugin
    capacity: []   # Capacity-based scheduling
```

## Kueue: Kubernetes-Native Job Queueing

Kueue (Kubernetes sigs project, graduated in K8s 1.32+) provides native job queueing with fair sharing and multi-tenant support. It integrates with the native Job controller rather than replacing it.

### Kueue Configuration

```yaml
apiVersion: kueue.x-k8s.io/v1beta1
kind: ResourceFlavor
metadata:
  name: gpu-flavor
spec:
  nodeLabels:
    nvidia.com/gpu: "true"
---
apiVersion: kueue.x-k8s.io/v1beta1
kind: ClusterQueue
metadata:
  name: batch-cluster-queue
spec:
  namespaceSelector:
    matchLabels:
      kueue.microsoft.com/managed: "true"
  resourceGroups:
    - coveredResources: ["cpu", "memory", "nvidia.com/gpu"]
      flavors:
        - name: "default"
          resources:
            - name: "cpu"
              nominalQuota: 200
            - name: "memory"
              nominalQuota: 800Gi
            - name: "nvidia.com/gpu"
              nominalQuota: 16
        - name: "gpu-flavor"
          resources:
            - name: "nvidia.com/gpu"
              nominalQuota: 32
  preemption:
    reclaimWithinCohort: Any
    borrowWithinCohort:
      policy: Never
    withinClusterQueue: LowerPriority
---
apiVersion: kueue.x-k8s.io/v1beta1
kind: LocalQueue
metadata:
  name: ml-team-queue
  namespace: ml
spec:
  clusterQueue: batch-cluster-queue
```

### Using Kueue with Native Jobs

Add the `queue-name` annotation to your Jobs to route them through Kueue:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: ml-training-job
  namespace: ml
  annotations:
    kueue.x-k8s.io/queue-name: ml-team-queue
spec:
  parallelism: 4
  completions: 4
  suspend: true
  template:
    spec:
      containers:
        - name: trainer
          image: pytorch/pytorch:2.3.0-cuda12.1
          command: ["python", "train.py"]
          resources:
            requests:
              cpu: "8"
              memory: "32Gi"
              nvidia.com/gpu: "1"
            limits:
              nvidia.com/gpu: "1"
      restartPolicy: Never
```

Kueue automatically suspends Jobs until resources are available, then unsuspends them in priority order based on the ClusterQueue configuration.

## Why Self-Host Your Batch Job Management?

**GPU Utilization**: Batch scheduling systems like Volcano and Kueue maximize GPU utilization through gang scheduling and fair sharing. Without them, GPUs sit idle while Jobs wait for partial resource allocation. Proper scheduling can increase GPU utilization from 40% to 85%+.

**Multi-Tenant Fairness**: When multiple teams share a Kubernetes cluster, native Jobs follow a first-come-first-served model. Queue-based systems ensure each team gets a fair share of resources based on configured quotas, preventing one team from monopolizing the cluster.

**Cost Efficiency**: Cloud batch services (AWS Batch, GCP Batch) charge per job execution and add markup on underlying compute. Self-hosted batch management on existing clusters eliminates per-job fees and lets you use spot/preemptible instances for non-critical workloads.

**ML Pipeline Integration**: Modern ML training frameworks (PyTorch, TensorFlow, Horovod) assume distributed execution with all replicas available simultaneously. Gang scheduling prevents the "zombie training" problem where some workers start while others are stuck pending, wasting compute and potentially corrupting training state.

**Predictable Scheduling**: With queueing and priority management, you can guarantee that critical batch jobs (nightly ETL, model retraining, report generation) run on time, even during periods of high cluster utilization. Preemption ensures high-priority jobs can reclaim resources from lower-priority ones.

For ML experiment tracking workflows, see our [MLflow vs ClearML vs Aim guide](../2026-04-17-self-hosted-ml-experiment-tracking-mlflow-clearml-aim-guide/).
For distributed training frameworks, our [Horovod vs DeepSpeed vs FSDP article](../2026-05-05-self-hosted-distributed-training-frameworks-horovod-deepspeed-fsdp-guide/) covers the training layer.
For cluster autoscaling that complements batch scheduling, check our [Karpenter vs Cluster Autoscaler guide](../karpenter-vs-cluster-autoscaler-vs-keda-kubernetes-autoscaling-guide-2026/).

## FAQ

### What is gang scheduling and why does it matter for batch jobs?

Gang scheduling ensures that all Pods in a multi-Pod Job are scheduled simultaneously or none at all. This matters for distributed training and batch processing where the job requires all workers to be running — having 3 out of 4 workers active provides no value and wastes resources. Volcano provides gang scheduling through its `minAvailable` field.

### How does Kueue differ from Volcano?

Kueue works with the native Kubernetes Job controller — it queues and unsuspends Jobs based on resource availability, but doesn't replace the scheduler. Volcano is a complete alternative scheduler that handles gang scheduling, binpacking, and fair sharing directly. Kueue is simpler to adopt (works with existing Jobs via annotations); Volcano provides more advanced scheduling features.

### Can I use Kueue and Volcano together?

Technically yes, but it's not recommended. Both manage scheduling behavior, and combining them can create conflicts. Choose Kueue if you need simple queueing with fair sharing on top of the native scheduler. Choose Volcano if you need advanced features like gang scheduling, DRF (Dominant Resource Fairness), or custom scheduling plugins.

### How do I prioritize batch jobs in a shared cluster?

With native Kubernetes, use PriorityClass to assign different priorities to Jobs. With Volcano, use the Queue system with weighted priorities and preemption. With Kueue, configure ClusterQueue with borrowing policies and preemption rules. In all cases, combine with resource quotas to prevent any single team from consuming the entire cluster.

### What happens to Jobs in the queue when the cluster scales up?

Kueue automatically re-evaluates queued Jobs when new nodes become available (through Cluster Autoscaler or Karpenter). Volcano does the same through its capacity plugin. Both systems dynamically adjust scheduling decisions based on current cluster resources — when new GPU nodes join, queued GPU Jobs are immediately considered for scheduling.

### How do I monitor batch job queue depth and wait times?

For Kueue, use the `kueue_admitted_workloads_total` and `kueue_pending_workloads` Prometheus metrics. For Volcano, check the queue status via `vcctl queue list` and monitor the `volcano_scheduling_duration_seconds` metric. Set up Grafana dashboards to track queue depth, admission rate, and average wait time per queue.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Kubernetes Batch Job Management: Queue Systems, Operators & Orchestrators",
  "description": "Guide to managing Kubernetes batch and parallel jobs at scale — compare Volcano, Kueue, and native Job controllers for GPU workloads, ML training pipelines, and large-scale batch processing.",
  "datePublished": "2026-05-20",
  "dateModified": "2026-05-20",
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
