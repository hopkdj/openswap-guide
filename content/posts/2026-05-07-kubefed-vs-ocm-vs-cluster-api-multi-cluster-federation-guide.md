---
title: "KubeFed vs Open Cluster Management vs Cluster API — Multi-Cluster Kubernetes Federation (2026)"
date: "2026-05-07T10:00:00+00:00"
tags: ["kubernetes", "multi-cluster", "federation", "cluster-api", "self-hosted", "docker"]
draft: false
---

Managing Kubernetes across multiple clusters — whether for disaster recovery, geographic distribution, or hybrid cloud — requires a federation layer. Three open-source projects address this challenge with different philosophies: **KubeFed** (API-level federation), **Open Cluster Management** (application lifecycle across clusters), and **Cluster API** (declarative infrastructure provisioning).

This guide compares their architectures, self-hosting requirements, and deployment approaches for teams running multi-cluster Kubernetes.

## What is Kubernetes Multi-Cluster Federation?

Kubernetes federation allows you to manage multiple clusters as a unified entity. Instead of configuring each cluster independently, a federation control plane propagates resources (Deployments, Services, ConfigMaps) across member clusters. This enables:

- **Disaster recovery**: Automatic failover between clusters
- **Geo-distribution**: Serve users from the nearest cluster
- **Cloud independence**: Run workloads across providers without vendor lock-in
- **Unified governance**: Apply consistent policies across all clusters

## Quick Comparison

| Feature | KubeFed | Open Cluster Management (OCM) | Cluster API (CAPI) |
|---|---|---|---|
| **GitHub** | kubernetes-sigs/kubefed | open-cluster-management-io | kubernetes-sigs/cluster-api |
| **Stars** | 2,482 | 2,100+ | 4,200 |
| **Language** | Go | Go | Go |
| **Primary Focus** | API federation & resource propagation | Application lifecycle & governance | Infrastructure provisioning |
| **Cluster Creation** | ❌ Assumes clusters exist | ❌ Assumes clusters exist | ✅ Creates & manages clusters |
| **Resource Propagation** | ✅ Federated resources | ✅ Placement & manifests | ❌ Cluster-level only |
| **Placement Policies** | ✅ Override & scheduling | ✅ PlacementRules | ✅ MachineDeployments |
| **Helm Install** | ✅ | ✅ | ✅ |
| **Last Active** | 2023-03 (stable) | 2026-05 | 2026-05 |

## KubeFed: API-Level Federation

KubeFed is the original Kubernetes federation project, incubated under kubernetes-sigs. It creates a federated control plane that watches `Federated*` CRDs and propagates changes to member clusters.

### Architecture

KubeFed installs a federation API server and controller manager. You create `FederatedDeployment`, `FederatedService`, and other federated resource types. The federation controller watches these and applies equivalent resources to each registered member cluster.

### Installation via Helm

```yaml
# federated-cluster-values.yaml
apiVersion: helm.sh/v3
kind: HelmRelease
metadata:
  name: kubefed
  namespace: kube-federation-system
spec:
  chart:
    spec:
      chart: kubefed
      version: "0.12.0"
      sourceRef:
        kind: HelmRepository
        name: kubefed-charts
  interval: 10m
  install:
    createNamespace: true
  values:
    image:
      repository: registry.k8s.io/kubefed/kubefed
      tag: "v0.12.0"
```

```bash
# Install KubeFed federation control plane
helm repo add kubefed https://kubernetes-sigs.github.io/kubefed/
helm install kubefed kubefed/kubefed \
  --namespace kube-federation-system \
  --create-namespace \
  --version 0.12.0

# Join a member cluster
kubefedctl join cluster2 \
  --cluster-context cluster2 \
  --host-cluster-context cluster1 \
  --v=2
```

### Federated Deployment Example

```yaml
apiVersion: types.kubefed.io/v1beta1
kind: FederatedDeployment
metadata:
  name: nginx-app
  namespace: default
spec:
  template:
    metadata:
      labels:
        app: nginx
    spec:
      replicas: 3
      selector:
        matchLabels:
          app: nginx
      template:
        spec:
          containers:
          - name: nginx
            image: nginx:1.25
            ports:
            - containerPort: 80
  placement:
    clusters:
    - name: cluster1
    - name: cluster2
    - name: cluster3
  overrides:
  - clusterName: cluster2
    clusterOverrides:
    - path: "spec.replicas"
      value: 5
```

### Key Strengths

- **Mature API design**: Federated resource types follow Kubernetes API conventions
- **Override support**: Per-cluster customization of propagated resources
- **DNS and ingress federation**: Built-in support for federated DNS and ingress
- **Lightweight**: Only requires the federation control plane

### Limitations

- **Development pace**: Last significant commit was March 2023; the project is in maintenance mode
- **No cluster lifecycle**: Assumes clusters already exist
- **Limited observability**: No built-in dashboard for federation status

## Open Cluster Management (OCM): Application Lifecycle Federation

Open Cluster Management, originally from Red Hat, focuses on managing applications and policies across multiple clusters. It uses a hub-and-spoke model where the hub cluster manages spoke clusters.

### Architecture

OCM installs a hub control plane (`multicluster-engine`) on a management cluster. Spoke clusters register with the hub using `ManagedCluster` resources. Applications are deployed via `ManifestWork` and `ManagedClusterSetBinding` resources.

### Installation

```bash
# Install OCM hub on management cluster
curl -L https://raw.githubusercontent.com/open-cluster-management-io/clusteradm/main/install.sh | bash

clusteradm init --wait

# Join a spoke cluster
clusteradm join \
  --hub-token <token> \
  --hub-apiserver https://<hub-api>:6443 \
  --cluster-name spoke1 --wait

# Accept the spoke cluster
clusteradm accept --clusters spoke1
```

### Application Deployment via ManifestWork

```yaml
apiVersion: work.open-cluster-management.io/v1
kind: ManifestWork
metadata:
  namespace: spoke1
  name: nginx-deployment
spec:
  workload:
    manifests:
    - apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: nginx
        namespace: default
      spec:
        replicas: 3
        selector:
          matchLabels:
            app: nginx
        template:
          metadata:
            labels:
              app: nginx
          spec:
            containers:
            - name: nginx
              image: nginx:1.25
              ports:
              - containerPort: 80
```

### Policy-Based Placement

```yaml
apiVersion: policy.open-cluster-management.io/v1
kind: PlacementBinding
metadata:
  name: nginx-placement-binding
placementRef:
  name: nginx-placement
  kind: PlacementRule
  apiGroup: apps.open-cluster-management.io
subjects:
- name: nginx-policy
  kind: Policy
  apiGroup: policy.open-cluster-management.io
---
apiVersion: apps.open-cluster-management.io/v1
kind: PlacementRule
metadata:
  name: nginx-placement
spec:
  clusterConditions:
  - status: "True"
    type: ManagedClusterConditionAvailable
  clusterSelector:
    matchLabels:
      environment: production
```

### Key Strengths

- **Active development**: Regular releases and active community
- **Policy framework**: Built-in governance and compliance (Gatekeeper integration)
- **Application lifecycle**: Full deploy/update/rollback workflow
- **Add-on ecosystem**: Submariner, Klusterlet, and observability add-ons

## Cluster API (CAPI): Declarative Infrastructure Provisioning

Cluster API takes a different approach: instead of federating resources across existing clusters, it manages the clusters themselves as Kubernetes resources. You define `Cluster`, `MachineDeployment`, and `Machine` objects, and CAPI provisions the infrastructure.

### Architecture

CAPI uses a provider model. The core CAPI defines abstractions (`Cluster`, `Machine`), while infrastructure providers (AWS, Azure, Docker, Metal3) implement the actual provisioning. This means CAPI can create clusters on any supported platform.

### Installation

```bash
# Install clusterctl
curl -L https://github.com/kubernetes-sigs/cluster-api/releases/download/v1.7.0/clusterctl-linux-amd64 -o clusterctl
chmod +x clusterctl
sudo mv clusterctl /usr/local/bin/

# Initialize CAPI with Docker provider (for local testing)
clusterctl init --infrastructure docker

# Create a workload cluster
cat > test-cluster.yaml <<EOF
apiVersion: cluster.x-k8s.io/v1beta1
kind: Cluster
metadata:
  name: test-cluster
  namespace: default
spec:
  clusterNetwork:
    pods:
      cidrBlocks: ["192.168.0.0/16"]
    services:
      cidrBlocks: ["10.128.0.0/12"]
  infrastructureRef:
    apiVersion: infrastructure.cluster.x-k8s.io/v1beta1
    kind: DockerCluster
    name: test-cluster
  controlPlaneRef:
    kind: KubeadmControlPlane
    apiVersion: controlplane.cluster.x-k8s.io/v1beta1
    name: test-cluster-control-plane
EOF

kubectl apply -f test-cluster.yaml
```

### MachineDeployment for Worker Nodes

```yaml
apiVersion: cluster.x-k8s.io/v1beta1
kind: MachineDeployment
metadata:
  name: test-cluster-md-0
  namespace: default
spec:
  clusterName: test-cluster
  replicas: 3
  selector:
    matchLabels:
      cluster.x-k8s.io/cluster-name: test-cluster
  template:
    metadata:
      labels:
        cluster.x-k8s.io/cluster-name: test-cluster
    spec:
      clusterName: test-cluster
      version: v1.29.0
      bootstrap:
        configRef:
          apiVersion: bootstrap.cluster.x-k8s.io/v1beta1
          kind: KubeadmConfigTemplate
          name: test-cluster-md-0
      infrastructureRef:
        apiVersion: infrastructure.cluster.x-k8s.io/v1beta1
        kind: DockerMachineTemplate
        name: test-cluster-md-0
```

### Key Strengths

- **Infrastructure as Code**: Clusters defined as Kubernetes resources
- **Provider extensibility**: AWS, Azure, GCP, VMware, bare metal (Metal3)
- **Cluster lifecycle**: Create, upgrade, scale, and delete clusters declaratively
- **Self-hosted**: Can run the management cluster on any Kubernetes

## Choosing the Right Tool

| Use Case | Best Choice | Why |
|---|---|---|
| Propagate Deployments across existing clusters | KubeFed | Simple API-level federation |
| Multi-cluster governance & policy | Open Cluster Management | Built-in policy framework |
| Provision clusters on multiple clouds | Cluster API | Infrastructure provider model |
| Active development & community | OCM or CAPI | KubeFed is in maintenance mode |
| Disaster recovery (active-passive) | KubeFed | Federated resource propagation |
| Hybrid cloud (on-prem + cloud) | CAPI + OCM | CAPI for provisioning, OCM for management |

## Why Multi-Cluster Federation Matters

Running multiple Kubernetes clusters is no longer optional for many organizations. Regulatory requirements demand data residency. Geographic distribution reduces latency. Multi-cloud strategies prevent vendor lock-in. But managing clusters independently is operationally expensive.

Federation tools solve this by providing a single control plane. Instead of running `kubectl apply` against 10 clusters, you define the desired state once and the federation layer handles propagation. This is especially valuable for:

- **Platform teams** managing shared infrastructure across business units
- **SRE teams** implementing consistent observability and alerting
- **Security teams** enforcing uniform policies and network configurations

For teams needing cluster-level automation beyond federation, our [Cluster management guide](../2026-04-22-rancher-vs-kubespray-vs-kind-self-hosted-kubernetes-management-guide/) covers Rancher, KubeSpray, and Kind. For multi-cluster networking, the [Karmada vs Liqo vs Submariner comparison](../2026-05-01-karmada-vs-liqo-vs-submariner-self-hosted-multi-cluster-kubernetes-networking/) covers the networking layer.

## FAQ

### What is the difference between KubeFed and Cluster API?

KubeFed federates resources (Deployments, Services) across existing clusters, while Cluster API manages the clusters themselves as infrastructure. KubeFed answers "how do I run the same app across 5 clusters?" while CAPI answers "how do I create and manage 5 clusters?"

### Is KubeFed still maintained?

KubeFed's last significant release was in 2023. The project is in maintenance mode — it works well for existing deployments but is not receiving major new features. For active development, consider Open Cluster Management or Cluster API.

### Can I use multiple federation tools together?

Yes. A common pattern is Cluster API for cluster provisioning, Open Cluster Management for application lifecycle, and KubeFed (or Karmada) for resource propagation. Each tool addresses a different layer of the multi-stack.

### Does Open Cluster Management require Red Hat OpenShift?

No. OCM runs on any Kubernetes cluster, including vanilla K8s, EKS, GKE, and AKS. The hub and spoke clusters can be on different platforms.

### How does Cluster API handle cluster upgrades?

CAPI handles upgrades through rolling updates of MachineDeployments. You change the `version` field in the MachineDeployment spec, and CAPI replaces nodes one at a time with the new version. Control plane upgrades use KubeadmControlPlane's rolling update strategy.

### What happens when a federated member cluster goes offline?

KubeFed marks the cluster as offline and stops propagating changes to it. When the cluster reconnects, pending changes are applied. OCM uses a similar pattern with `ManagedClusterConditionAvailable`.

## Docker Compose for Local Testing

For local development, you can test CAPI with the Docker infrastructure provider:

```yaml
# docker-compose-capi-test.yaml
version: "3.8"
services:
  kind-control-plane:
    image: kindest/node:v1.29.0
    privileged: true
    ports:
      - "6443:6443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - kind-data:/var/lib/containerd
    command:
      - "/usr/local/bin/entrypoint"
      - "/sbin/init"

volumes:
  kind-data:
```

For more on Kubernetes operator patterns, see our [Operators guide](../crossplane-vs-kubevela-vs-kubernetes-operators-infrastructure-management-2026/). For virtual cluster approaches to multi-tenancy, check [vCluster vs Capsule vs Loft](../2026-04-28-vcluster-vs-capsule-vs-loft-kubernetes-namespace-virtual-cluster-guide-2026/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "KubeFed vs Open Cluster Management vs Cluster API — Multi-Cluster Kubernetes Federation (2026)",
  "description": "Compare KubeFed, Open Cluster Management, and Cluster API for multi-cluster Kubernetes federation. Covers architecture, installation, and deployment patterns.",
  "datePublished": "2026-05-07",
  "dateModified": "2026-05-07",
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
