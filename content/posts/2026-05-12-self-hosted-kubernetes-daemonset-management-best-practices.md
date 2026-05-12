---
title: "Self-Hosted Kubernetes DaemonSet Management: Best Practices and Tools"
date: "2026-05-12"
tags: ["kubernetes", "daemonset", "comparison", "guide", "self-hosted", "cluster-management"]
draft: false
---

DaemonSets are a core Kubernetes workload type that ensures a copy of a Pod runs on all (or a subset of) nodes in a cluster. They are essential for node-level services: log collectors, monitoring agents, storage plugins, and network daemons that must run on every node. While the built-in Kubernetes DaemonSet controller handles basic scheduling, managing DaemonSets at scale requires careful planning around resource allocation, update strategies, node selection, and health monitoring.

In this guide, we explore the best practices for managing DaemonSets in self-hosted Kubernetes clusters, along with the tools and patterns that make DaemonSet operations reliable and maintainable.

## What Is a DaemonSet?

A DaemonSet is a Kubernetes controller that guarantees a Pod runs on every node matching its selector. Unlike Deployments (which manage a desired replica count across the cluster) or StatefulSets (which manage ordered, identity-aware replicas), DaemonSets are node-centric — they scale automatically as nodes are added or removed from the cluster.

Common DaemonSet use cases include:
- **Log collection** — Fluentd, Fluent Bit, Vector, or Filebeat agents running on every node
- **Monitoring agents** — Prometheus Node Exporter, Datadog agent, or custom metrics collectors
- **Storage daemons** — Ceph OSD, GlusterFS, or Rook storage agents
- **Networking plugins** — Calico, Cilium, or kube-router networking agents
- **Security agents** — Falco, Tetragon, or other runtime security monitors

## Built-In DaemonSet Controller

Kubernetes includes a native DaemonSet controller as part of its core control plane. It handles the basic lifecycle: creating Pods on eligible nodes, updating Pods when the DaemonSet spec changes, and removing Pods when nodes are deleted.

**Key features:**
- `OnDelete` update strategy — Pods are only updated when manually deleted
- `RollingUpdate` strategy — Pods are updated node-by-node with configurable `maxUnavailable`
- Node selector and toleration support for targeting specific node groups
- Automatic Pod creation on new nodes and cleanup on node deletion

### Basic DaemonSet Example

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: log-collector
  namespace: monitoring
  labels:
    app: log-collector
spec:
  selector:
    matchLabels:
      app: log-collector
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
  template:
    metadata:
      labels:
        app: log-collector
    spec:
      tolerations:
      - key: node-role.kubernetes.io/control-plane
        operator: Exists
        effect: NoSchedule
      containers:
      - name: fluent-bit
        image: fluent/fluent-bit:latest
        volumeMounts:
        - name: varlog
          mountPath: /var/log
        - name: containers
          mountPath: /var/lib/docker/containers
          readOnly: true
        resources:
          requests:
            cpu: 50m
            memory: 100Mi
          limits:
            cpu: 200m
            memory: 256Mi
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
      - name: containers
        hostPath:
          path: /var/lib/docker/containers
```

## DaemonSet Management Tools and Patterns

While the built-in controller handles basic operations, several tools and patterns extend DaemonSet management capabilities:

### 1. Helm Charts for DaemonSet Deployment

Helm provides a declarative, templated approach to DaemonSet management. Popular chart repositories include pre-built DaemonSets for common node-level services:

```bash
# Deploy Prometheus Node Exporter via Helm
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install node-exporter prometheus-community/prometheus-node-exporter   --namespace monitoring   --set tolerations[0].key=node-role.kubernetes.io/control-plane   --set tolerations[0].operator=Exists   --set tolerations[0].effect=NoSchedule
```

Helm charts handle DaemonSet lifecycle management including upgrades, rollbacks, and configuration overrides. The `helm upgrade` command supports `--wait` and `--timeout` flags for controlled rolling updates.

### 2. Kustomize for DaemonSet Overlays

Kustomize provides a patch-based approach to customizing DaemonSets across different environments:

```yaml
# kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
- daemonset.yaml
patches:
- target:
    kind: DaemonSet
    name: log-collector
  patch: |-
    - op: replace
      path: /spec/template/spec/containers/0/image
      value: fluent/fluent-bit:3.0.0
    - op: add
      path: /spec/updateStrategy/rollingUpdate/maxUnavailable
      value: 2
```

Kustomize is ideal for managing DaemonSet variations across development, staging, and production clusters without duplicating base configurations.

### 3. Argo CD for GitOps DaemonSet Management

Argo CD provides continuous reconciliation for DaemonSets defined in Git repositories. When the DaemonSet manifest in Git changes, Argo CD automatically applies the update to the cluster:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: node-agents
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/cluster-configs.git
    targetRevision: main
    path: daemonsets/
  destination:
    server: https://kubernetes.default.svc
    namespace: monitoring
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
```

Argo CD's self-healing capability ensures DaemonSets always match their Git-defined state, even if someone manually modifies them with `kubectl`.

## DaemonSet Best Practices

### Resource Management

DaemonSets run on every node, so resource requests multiply across the cluster. A DaemonSet requesting 200m CPU and 256Mi memory on a 50-node cluster consumes 10 CPU cores and 12.8Gi RAM — resources that could otherwise run application workloads.

```yaml
resources:
  requests:
    cpu: 50m      # Conservative request
    memory: 64Mi  # Minimum viable
  limits:
    cpu: 200m     # Ceiling for bursts
    memory: 256Mi # Prevent OOM kills
```

### Update Strategy Configuration

The `RollingUpdate` strategy should be tuned based on the service's criticality:

```yaml
updateStrategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 1    # Conservative: one node at a time
    maxSurge: 0          # No surge for DaemonSets (fixed per-node)
```

For non-critical DaemonSets (like experimental monitoring agents), `maxUnavailable: 20%` allows faster rollouts. For critical services (networking, storage), `maxUnavailable: 1` ensures minimal disruption.

### Node Selection and Tolerations

DaemonSets should be explicitly scoped to avoid running on inappropriate nodes:

```yaml
nodeSelector:
  node-type: worker
tolerations:
- key: node-role.kubernetes.io/control-plane
  operator: Exists
  effect: NoSchedule
- key: CriticalAddonsOnly
  operator: Exists
```

### Health Monitoring

Monitor DaemonSet health with standard Kubernetes metrics:

```bash
# Check DaemonSet status
kubectl get daemonsets -A
kubectl describe daemonset log-collector -n monitoring

# Monitor rollout progress
kubectl rollout status daemonset/log-collector -n monitoring

# Check for nodes missing the DaemonSet Pod
kubectl get nodes -o custom-columns='NODE:.metadata.name,DAEMONSET:.status.conditions[?(@.type=="Ready")].status'
```

## Comparison Table

| Aspect | Built-In Controller | Helm Charts | Kustomize | Argo CD (GitOps) |
|--------|-------------------|-------------|-----------|------------------|
| **Deployment** | Manual YAML | Templated | Patch-based | Git-synced |
| **Rollback** | Manual | `helm rollback` | `git revert` | Auto-sync |
| **Multi-env** | Duplicate YAML | Values files | Overlays | App-of-apps |
| **Drift Detection** | None | `helm diff` | None | Continuous |
| **Learning Curve** | Low | Medium | Medium | High |
| **Best For** | Single cluster | Reusable configs | Env variations | GitOps workflows |

## Why Self-Host Kubernetes DaemonSet Management?

Self-hosting your Kubernetes cluster means you have full control over DaemonSet deployment, configuration, and lifecycle management. In managed Kubernetes services (EKS, GKE, AKS), many DaemonSet capabilities are abstracted away — and in some cases, restricted. Self-hosted clusters offer:

**Custom DaemonSet scheduling**: Define exactly which nodes run which DaemonSets, using node selectors, tolerations, and affinity rules tailored to your infrastructure. Managed services often restrict access to control-plane nodes or enforce predefined DaemonSets.

**Custom update strategies**: Configure rolling update parameters (`maxUnavailable`, partition-based rollouts) that match your organization's change management policies. Self-hosted clusters let you pause, resume, and debug DaemonSet rollouts without vendor-imposed constraints.

**Full observability**: Run custom monitoring, logging, and security DaemonSets that integrate with your self-hosted observability stack. Managed services may limit which DaemonSets you can deploy on their infrastructure.

**Cost control**: DaemonSets consume cluster resources. In self-hosted environments, you can optimize resource requests, use lightweight alternatives (Fluent Bit vs Fluentd), and right-size nodes to minimize waste.

For Kubernetes storage management, see our [CSI drivers comparison](../2026-05-08-kubernetes-csi-drivers-ceph-csi-vs-longhorn-vs-kadalu-guide/). For cluster autoscaling, check our [Karpenter vs Cluster Autoscaler vs KEDA guide](../karpenter-vs-cluster-autoscaler-vs-keda-kubernetes-autoscaling-guide/). For network policies, our [CNI deep-dive](../2026-04-26-calico-vs-cilium-vs-kube-router-kubernetes-network-policies/) covers networking DaemonSets.

## FAQ

### What is a Kubernetes DaemonSet?
A DaemonSet is a Kubernetes workload controller that ensures a copy of a specific Pod runs on every node (or a subset of nodes) in the cluster. Unlike Deployments that manage a fixed number of replicas, DaemonSets scale automatically as nodes are added or removed. They are ideal for node-level services like log collectors, monitoring agents, and networking plugins.

### How does a DaemonSet differ from a Deployment?
Deployments manage a desired number of Pod replicas that can run on any node. DaemonSets ensure exactly one Pod per eligible node. If you add a node to the cluster, a Deployment's replica count stays the same, but a DaemonSet automatically creates a new Pod on the new node. Use Deployments for stateless application workloads and DaemonSets for infrastructure services that must run on every node.

### What update strategies are available for DaemonSets?
DaemonSets support two update strategies: `OnDelete` (Pods are only updated when manually deleted) and `RollingUpdate` (Pods are updated node-by-node). RollingUpdate supports `maxUnavailable` to control how many nodes can be without the updated Pod during the rollout. For most use cases, `RollingUpdate` with `maxUnavailable: 1` is the safest choice.

### How do I prevent a DaemonSet from running on control-plane nodes?
By default, DaemonSets run on all nodes. To exclude control-plane nodes, add a `nodeSelector` that targets worker nodes only, or ensure the DaemonSet's tolerations do not match the control-plane taint (`node-role.kubernetes.io/control-plane:NoSchedule`). Alternatively, use `nodeAffinity` with `requiredDuringSchedulingIgnoredDuringExecution` to specify eligible nodes.

### How do I monitor DaemonSet health?
Use `kubectl get daemonsets -A` to see the desired, current, and ready Pod counts for each DaemonSet. The `kubectl rollout status daemonset/<name>` command tracks rollout progress. For automated monitoring, use Prometheus with the `kube_daemonset_*` metrics exported by kube-state-metrics: `kube_daemonset_status_current_number_scheduled`, `kube_daemonset_status_desired_number_scheduled`, and `kube_daemonset_status_number_misscheduled`.

### Can I run multiple instances of the same DaemonSet on a single node?
By default, Kubernetes ensures only one Pod from a DaemonSet runs per node. However, you can run multiple DaemonSets with different selectors or tolerations on the same node. For example, one DaemonSet for general log collection and another for security-specific log collection, each with different configurations and resource profiles.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Kubernetes DaemonSet Management: Best Practices and Tools",
  "description": "Guide to managing Kubernetes DaemonSets in self-hosted clusters, covering built-in controllers, Helm, Kustomize, Argo CD, and best practices for resource management and updates.",
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
