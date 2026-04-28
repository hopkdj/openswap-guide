---
title: "vCluster vs Capsule vs Loft: Kubernetes Namespace & Virtual Cluster Management 2026"
date: 2026-04-28
tags: ["comparison", "guide", "self-hosted", "kubernetes", "multi-tenancy", "virtual-cluster"]
draft: false
description: "Compare vCluster, Capsule, and Loft for Kubernetes namespace management and virtual cluster isolation. Complete guide to self-hosted multi-tenancy solutions with Helm installation and configuration examples."
---

Running multiple teams, environments, or workloads on a single Kubernetes cluster requires careful isolation. Standard Kubernetes namespaces provide basic segmentation, but they fall short when teams need their own control plane, custom resource definitions, or independent RBAC policies. This is where virtual cluster and namespace management solutions come in.

In this guide, we compare three leading open-source tools for Kubernetes multi-tenancy: **vCluster** by Loft Labs, **Capsule** by Clastix, and **Loft** (also by Loft Labs). Each takes a fundamentally different approach to cluster isolation — from full virtual control planes to policy-enforced namespace boundaries.

## Why Self-Host Kubernetes Multi-Tenancy?

Kubernetes multi-tenancy lets multiple teams share a single physical cluster while maintaining isolation. The benefits include:

- **Cost reduction**: Fewer control planes to manage, better resource utilization across shared nodes
- **Simplified operations**: One cluster to upgrade, monitor, and secure instead of dozens
- **Developer self-service**: Teams get their own isolated environment without waiting for cluster provisioning
- **Environment parity**: Dev, staging, and production can run as isolated tenants on the same infrastructure

The challenge is that vanilla Kubernetes namespaces are "soft" boundaries. Any cluster admin can see across all namespaces, and there's no native way to give teams their own API server, CRDs, or admission controllers. Virtual clusters and multi-tenancy frameworks solve this gap.

## vCluster: Full Virtual Kubernetes Clusters

[vCluster](https://github.com/loft-sh/vcluster) (11,100+ stars) creates fully functional virtual Kubernetes clusters that run inside a single namespace of the host cluster. Each vCluster gets its own API server, controller manager, and optionally its own etcd — all running as pods in the host namespace.

**Key features:**

- Complete virtual Kubernetes control plane per tenant
- Supports any Kubernetes distribution (EKS, GKE, on-prem, k3s)
- Independent CRDs, RBAC, and admission controllers per vCluster
- Sync plugins to bridge resources between host and virtual cluster
- Helm-based installation, runs entirely in-cluster

### Installing vCluster

The vCluster CLI is the recommended installation method:

```bash
# Install the vCluster CLI
curl -L -o vcluster "https://github.com/loft-sh/vcluster/releases/latest/download/vcluster-linux-amd64"
chmod +x vcluster
sudo mv vcluster /usr/local/bin/

# Create a virtual cluster
vcluster create my-vcluster -n my-namespace

# Connect to the virtual cluster
vcluster connect my-vcluster -n my-namespace
```

Alternatively, install via Helm:

```bash
helm repo add loft https://charts.loft.sh
helm repo update

helm install vcluster loft/vcluster \
  --namespace my-vcluster \
  --create-namespace \
  --set "sync.fromHost.nodes.enabled=true"
```

### vCluster Architecture

A vCluster runs as a set of pods in the host namespace:

```yaml
# Example vCluster values.yaml for custom configuration
sync:
  fromHost:
    nodes:
      enabled: true
    storageClasses:
      enabled: true
  toHost:
    services:
      enabled: true
    persistentVolumeClaims:
      enabled: true

pro:
  multiNamespaceMode:
    enabled: true

isolation:
  podSecurityStandard: baseline
  resourceQuota:
    enabled: true
    quota:
      requests.cpu: "16"
      requests.memory: 32Gi
      limits.cpu: "32"
      limits.memory: 64Gi
```

## Capsule: Policy-Based Namespace Management

[Capsule](https://github.com/clastix/capsule) (2,100+ stars) takes a different approach. Instead of creating virtual clusters, it enhances standard Kubernetes namespaces with policy-based multi-tenancy. Capsule acts as a Kubernetes operator that enforces tenant boundaries through admission webhooks.

**Key features:**

- Lightweight — no additional control plane components
- Tenant CRD defines ownership, allowed namespaces, and policies
- Enforces resource quotas, ingress classes, storage classes, and network policies
- Works with existing Kubernetes tooling — tenants use real namespaces
- Supports both Namespace-scoped and Cluster-scoped resources

### Installing Capsule

Capsule installs as a standard Kubernetes operator via Helm:

```bash
# Add the Capsule Helm repository
helm repo add projectcapsule https://projectcapsule.github.io/capsule/
helm repo update

# Install Capsule in the capsule-system namespace
helm install capsule projectcapsule/capsule \
  --namespace capsule-system \
  --create-namespace \
  --set config.additionalArgs="{--force-tenant-prefix}"
```

### Defining a Tenant in Capsule

Tenants are defined as Kubernetes Custom Resources:

```yaml
apiVersion: capsule.clastix.io/v1beta2
kind: Tenant
metadata:
  name: engineering
spec:
  owners:
  - name: alice
    kind: User
  - name: bob
    kind: User
    clusterRoles:
    - edit
  namespaceOptions:
    quota: 5
    additionalMetadata:
      annotations:
        capsule.clastix.io/tenant: engineering
  ingressOptions:
    allowedClasses:
      names:
      - nginx
      - traefik
  storageClasses:
    allowed:
    - standard
    - fast-ssd
  limitRanges:
  - limits:
    - default:
        cpu: "500m"
        memory: 512Mi
      defaultRequest:
        cpu: "100m"
        memory: 128Mi
      type: Container
  resourceQuota:
    scope: Tenant
    quota:
      hard:
        requests.cpu: "20"
        requests.memory: 40Gi
        limits.cpu: "40"
        limits.memory: 80Gi
        pods: "100"
```

This Tenant CRD allows `alice` and `bob` to manage up to 5 namespaces under the `engineering` tenant, with enforced ingress classes, storage classes, and resource quotas.

## Loft: Namespace & Virtual Cluster Manager with Self-Service Portal

[Loft](https://github.com/loft-sh/loft) (834+ stars) is the commercial-grade platform from the same company behind vCluster. It provides a self-service portal for creating and managing virtual clusters and namespaces, with features like sleep mode for cost savings.

**Key features:**

- Self-service portal for developers to spin up virtual clusters
- Sleep mode pauses virtual clusters to save compute costs (up to 70% savings)
- Template-based cluster provisioning with pre-configured workloads
- Integration with vCluster for full virtual cluster support
- Enterprise access controls and audit logging

### Installing Loft

Loft installs via Helm on any Kubernetes cluster:

```bash
# Add the Loft Helm repository
helm repo add loft https://charts.loft.sh
helm repo update

# Install Loft in the loft namespace
helm install loft loft/loft \
  --namespace loft \
  --create-namespace \
  --set "loft.domain=loft.example.com"

# Access the Loft UI
kubectl port-forward svc/loft -n loft 8080:80
```

### Creating a Space (Virtual Cluster) via Loft CLI

```bash
# Install the Loft CLI
curl -L -o loft "https://github.com/loft-sh/loft/releases/latest/download/loft-linux-amd64"
chmod +x loft
sudo mv loft /usr/local/bin/

# Login to your Loft instance
loft login https://loft.example.com --access-key your-access-key

# Create a new space (virtual cluster)
loft create space dev-environment --template k8s-app-template

# List your spaces
loft get spaces
```

## Feature Comparison

| Feature | vCluster | Capsule | Loft |
|---------|----------|---------|------|
| **Approach** | Virtual control plane | Namespace policy operator | Self-service portal + vCluster |
| **GitHub Stars** | 11,100+ | 2,100+ | 834+ |
| **Language** | Go | Go | Go |
| **Isolation Level** | Full (separate API server) | Namespace-level (admission webhook) | Full (via vCluster) |
| **Independent CRDs** | Yes | No (shares host CRDs) | Yes |
| **Independent RBAC** | Yes | Tenant-scoped RBAC | Yes |
| **Self-Service Portal** | No | No | Yes |
| **Sleep Mode / Cost Savings** | No | No | Yes |
| **Installation** | Helm / CLI | Helm (operator) | Helm / CLI |
| **Resource Quotas** | Per vCluster | Per Tenant | Per space/vCluster |
| **Multi-Namespace Mode** | Yes (Pro) | Native | Yes |
| **Template-Based Provisioning** | No | No | Yes |
| **Best For** | Complete tenant isolation | Lightweight policy enforcement | Developer self-service |

## Deep Dive: Isolation Models

### vCluster — Control Plane Isolation

vCluster creates a separate Kubernetes API server for each virtual cluster. This means:

- Tenants can install their own CRDs without affecting the host cluster
- Independent admission controllers and webhooks per vCluster
- Full RBAC isolation — tenant admins cannot see host cluster resources
- Compatible with any Kubernetes-native tool (Helm, kubectl, operators)

The trade-off is resource overhead: each vCluster runs its own API server pod (and optionally etcd), consuming additional CPU and memory.

### Capsule — Policy-Based Isolation

Capsule enforces isolation through Kubernetes admission webhooks:

- Prevents cross-tenant resource access at the API server level
- Enforces resource quotas, allowed storage classes, and ingress classes
- Lightweight — runs as a single deployment, no per-tenant control plane
- Works with existing Kubernetes namespace semantics

The trade-off is that all tenants share the same control plane and CRD definitions. Teams cannot install custom operators or CRDs independently.

### Loft — Self-Service with vCluster Backend

Loft combines the self-service experience of a developer portal with vCluster's isolation:

- Developers request environments through a web UI or CLI
- Templates define pre-configured cluster setups
- Sleep mode pauses idle clusters to save costs
- Audit logging tracks who created what and when

The trade-off is that Loft requires a running vCluster infrastructure, combining the resource overhead of virtual clusters with the operational complexity of a self-service platform.

## When to Use Each Tool

**Choose vCluster when:**
- You need complete Kubernetes isolation per team or environment
- Teams require their own CRDs, operators, or admission controllers
- You want to run different Kubernetes versions on the same hardware
- CI/CD pipelines need isolated test clusters on demand

**Choose Capsule when:**
- You want lightweight multi-tenancy without additional control planes
- Standard Kubernetes namespaces are sufficient but need policy enforcement
- You need to restrict which ingress classes, storage classes, or images tenants can use
- You want to minimize resource overhead on the host cluster

**Choose Loft when:**
- You need a self-service portal for developers
- Cost optimization through sleep mode is important
- Template-based environment provisioning is required
- You want to combine vCluster isolation with developer experience

## Installation Prerequisites

All three tools require:

- A running Kubernetes cluster (v1.24+ recommended)
- Helm 3.x installed
- `kubectl` configured with cluster admin access
- At least 2 CPU cores and 4 GB RAM available for the control plane components

For vCluster and Loft, additional resources are needed per virtual cluster:

```yaml
# Minimum resource requirements per vCluster
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi
```

For Capsule, the operator itself is lightweight:

```yaml
# Capsule operator resource requirements
resources:
  requests:
    cpu: 50m
    memory: 64Mi
  limits:
    cpu: 200m
    memory: 256Mi
```

## Security Considerations

### vCluster Security
- Virtual clusters run in isolated namespaces on the host
- Host cluster admins retain full access — vCluster isolation is not a security boundary against cluster admins
- Use network policies to restrict inter-vCluster traffic
- Consider using vCluster's Pro features for pod security standards enforcement

### Capsule Security
- Admission webhooks prevent unauthorized namespace creation and resource modification
- Tenant owners are explicitly defined — users not listed cannot access tenant namespaces
- Supports external identity providers via Kubernetes OIDC integration
- Combined with OPA Gatekeeper or Kyverno for additional policy layers (see our [Kubernetes policy enforcement guide](../kyverno-vs-opa-gatekeeper-vs-trivy-operator-kubernetes-policy-enforcement-2026/) for more details)

### Loft Security
- Access controlled through the Loft authentication system
- Audit logging provides visibility into cluster creation and access patterns
- Sleep mode ensures resources are not running when not needed, reducing the attack surface
- Integrates with existing Kubernetes RBAC for fine-grained permissions

For broader cluster security hardening, consider combining any of these tools with runtime security solutions — our [container hardening guide](../kube-bench-vs-trivy-vs-kubescape-container-kubernetes-hardening-guide-2026/) covers the options.

## Related Resources

For managing Kubernetes infrastructure at scale, you may also find these guides useful:

- [Kubernetes management with Rancher vs Kubespray vs Kind](../rancher-vs-kubespray-vs-kind-self-hosted-kubernetes-management-guide-2026/) — for cluster lifecycle management
- [Kubernetes storage options: Rook vs Longhorn vs OpenEBS](../rook-vs-longhorn-vs-openebs-self-hosted-kubernetes-storage-guide-2026/) — for persistent storage in multi-tenant setups
- [Kubernetes autoscaling: Karpenter vs Cluster Autoscaler vs KEDA](../karpenter-vs-cluster-autoscaler-vs-keda-kubernetes-autoscaling-guide-2026/) — for resource optimization across tenants

## FAQ

### What is the difference between vCluster and Capsule?

vCluster creates a fully virtual Kubernetes cluster with its own API server running as a pod inside the host cluster. Capsule enhances standard Kubernetes namespaces with policy-based multi-tenancy using admission webhooks. vCluster provides stronger isolation (separate control plane) while Capsule is lighter weight (no additional control plane components).

### Can vCluster and Capsule be used together?

Yes. You can run Capsule on the host cluster to manage namespace-level policies, and then deploy vClusters inside those namespaces for additional isolation. This gives you both policy enforcement at the host level and full control plane isolation for individual teams.

### Is vCluster production-ready?

Yes. vCluster is used by hundreds of organizations in production. It supports high availability configurations with multiple API server replicas and external etcd for persistence. The open-source version covers most use cases, with enterprise features available in the Pro edition.

### Does Capsule support Kubernetes RBAC?

Yes. Capsule integrates with native Kubernetes RBAC. Tenant owners are defined in the Tenant CRD and can be assigned cluster roles within their tenant's namespaces. Capsule also supports external identity providers through Kubernetes OIDC authentication.

### How does Loft's sleep mode work?

Loft's sleep mode scales down all workloads in a virtual cluster to zero replicas and pauses the vCluster's API server. This frees up CPU and memory resources on the host cluster. When a user accesses the cluster again, Loft automatically scales everything back up. This can reduce compute costs by up to 70% for development and staging environments.

### Which tool is best for CI/CD pipelines?

vCluster is typically the best choice for CI/CD pipelines. Each pipeline run can spin up a fresh virtual cluster with its own control plane, run tests in complete isolation, and then tear it down. This ensures no cross-contamination between pipeline runs and allows testing of Kubernetes operators and CRDs that would conflict in a shared environment.

### Can I use Capsule to limit which container images tenants can pull?

Capsule can enforce allowed registries through its `imagePullPolicies` and by combining with Kubernetes admission controllers. For more granular image policy enforcement (e.g., blocking specific image tags or requiring signed images), you should combine Capsule with a dedicated image policy webhook like Sigstore Policy Controller or OPA Gatekeeper.

### Do vCluster virtual clusters support persistent storage?

Yes. vCluster can sync PersistentVolumeClaims from the virtual cluster to the host cluster. Storage classes are also synced by default, so workloads in vClusters can use the same storage provisioners as the host cluster. You can configure this in the vCluster values.yaml under the `sync.toHost.persistentVolumeClaims` section.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "vCluster vs Capsule vs Loft: Kubernetes Namespace & Virtual Cluster Management 2026",
  "description": "Compare vCluster, Capsule, and Loft for Kubernetes namespace management and virtual cluster isolation. Complete guide to self-hosted multi-tenancy solutions with Helm installation and configuration examples.",
  "datePublished": "2026-04-28",
  "dateModified": "2026-04-28",
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
