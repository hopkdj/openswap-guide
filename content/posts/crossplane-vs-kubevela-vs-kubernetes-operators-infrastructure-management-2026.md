---
title: "Crossplane vs KubeVela vs Kubernetes Operators: Cloud Infrastructure Management 2026"
date: 2026-04-23
tags: ["comparison", "guide", "self-hosted", "kubernetes", "infrastructure", "cloud-native"]
draft: false
description: "Compare Crossplane, KubeVela, and Kubernetes Operators for managing cloud infrastructure. Complete Helm install guides, YAML configuration examples, and decision framework for platform teams in 2026."
---

Managing cloud infrastructure on Kubernetes has evolved far beyond simple container orchestration. Platform teams now need tools that can provision databases, message queues, storage buckets, and networking resources — all through declarative Kubernetes-native APIs. Three approaches have emerged as the leading options: **Crossplane**, **KubeVela**, and **custom Kubernetes Operators** built with the Operator SDK. Each represents a fundamentally different philosophy for how infrastructure should be managed, deployed, and operated at scale.

This guide compares all three approaches side-by-side with real installation commands, YAML configuration examples, and a decision framework to help your team choose the right tool.

## Why Self-Host Your Infrastructure Management?

Running your own infrastructure management layer on Kubernetes gives you complete control over how cloud resources are provisioned, audited, and governed. Unlike cloud-provider-specific tools (AWS CloudFormation, Azure ARM templates, GCP Deployment Manager), these open-source platforms work across any cloud provider and any on-premises environment.

Key benefits of self-hosted infrastructure management:

- **Multi-cloud portability** — write once, deploy to AWS, GCP, Azure, or bare metal
- **Policy enforcement** — enforce naming conventions, region restrictions, and cost controls
- **Audit trails** — every resource change is tracked through Kubernetes events and Git history
- **No vendor lock-in** — swap cloud providers without rewriting your deployment tooling
- **Self-service platform** — application teams request resources through familiar Kubernetes APIs

## 1. Crossplane — The Cloud Native Control Plane

[Crossplane](https://crossplane.io) is a CNCF Graduated project that extends the Kubernetes API to manage cloud infrastructure. Instead of writing Terraform configurations, you define **Compositions** (blueprints) and **Claims** (resource requests) using standard Kubernetes YAML. Crossplane then reconciles your desired state by calling cloud provider APIs through Provider packages.

**GitHub stats:** 11,615 stars · Last push: April 21, 2026 · Language: Go

### Architecture

Crossplane uses a provider-based model. Each cloud provider (AWS, GCP, Azure) is packaged as a Crossplane Provider — a custom controller that manages a specific set of resources. Providers are installed as OCI packages from the Crossplane registry, making it trivial to add or remove cloud integrations.

The key abstractions are:

- **Managed Resources (MRs)** — direct representations of cloud resources (e.g., `RDSInstance`, `Bucket`, `Network`)
- **Compositions** — reusable templates that combine multiple managed resources into higher-level services
- **Composite Resource Definitions (XRDs)** — custom API definitions that application teams use to request resources
- **Claims (XRCs)** — namespace-scoped requests that trigger composition-based provisioning

### Installation

Crossplane is installed via Helm on any Kubernetes cluster:

```bash
helm repo add crossplane-stable https://charts.crossplane.io/stable
helm repo update

helm install crossplane crossplane-stable/crossplane \
  --namespace crossplane-system \
  --create-namespace \
  --version 1.19.0
```

After installation, verify the control plane is running:

```bash
kubectl get pods -n crossplane-system
# NAME                                      READY   STATUS
# crossplane-6b4c7d8f9-abc12                1/1     Running
# crossplane-rbac-manager-5d6e7f8g-hij34    1/1     Running
```

### Installing a Provider

```bash
kubectl crossplane install provider crossplane-contrib/provider-aws:v0.49.0
```

### Configuration Example: AWS RDS Composition

Here is a real Composition that defines a PostgreSQL database service:

```yaml
apiVersion: apiextensions.crossplane.io/v1
kind: Composition
metadata:
  name: postgresql-db.aws.platform.example.com
spec:
  compositeTypeRef:
    apiVersion: platform.example.com/v1alpha1
    kind: XPostgreSQL
  resources:
    - name: rdsinstance
      base:
        apiVersion: database.aws.crossplane.io/v1beta1
        kind: RDSInstance
        spec:
          forProvider:
            region: us-east-1
            engine: postgres
            engineVersion: "16.2"
            dbInstanceClass: db.t3.medium
            allocatedStorage: 100
            storageEncrypted: true
            deletionProtection: true
      patches:
        - fromFieldPath: spec.parameters.engineVersion
          toFieldPath: spec.forProvider.engineVersion
        - fromFieldPath: spec.parameters.storageGB
          toFieldPath: spec.forProvider.allocatedStorage
        - fromFieldPath: spec.parameters.size
          toFieldPath: spec.forProvider.dbInstanceClass
          transforms:
            - type: map
              map:
                small: db.t3.small
                medium: db.t3.medium
                large: db.r5.large
    - name: dbpassword
      base:
        apiVersion: aws.crossplane.io/v1alpha1
        kind: SecretStoreConfig
        spec:
          type: Kubernetes
          source: Secret
      patches:
        - fromFieldPath: metadata.name
          toFieldPath: metadata.name
```

### Application Team Usage

Once the Composition is defined, application teams request databases with a simple claim:

```yaml
apiVersion: platform.example.com/v1alpha1
kind: PostgreSQL
metadata:
  name: my-app-db
  namespace: app-team-a
spec:
  parameters:
    engineVersion: "16.2"
    storageGB: 100
    size: medium
  compositionRef:
    name: postgresql-db.aws.platform.example.com
```

Crossplane handles the rest — provisioning the RDS instance, generating credentials, storing them in a Kubernetes Secret, and reporting status back to the claim.

## 2. KubeVela — The Modern Application Platform

[KubeVela](https://kubevela.io) takes a different approach. Instead of focusing on cloud resource provisioning, KubeVela is built around the **Open Application Model (OAM)** — a specification for describing applications as collections of components, traits, and policies. It excels at multi-cluster application delivery, progressive rollouts, and environment-specific configurations.

**GitHub stats:** 7,740 stars · Last push: April 19, 2026 · Language: Go

### Architecture

KubeVela's core concepts are:

- **Components** — the building blocks of an application (container images, cloud resources, data services)
- **Traits** — operational behaviors attached to components (scaling, routing, sidecars)
- **Policies** — deployment rules (placement, override, health checks)
- **Workflows** — step-by-step deployment pipelines with manual approval gates
- **Environments** — named configurations (dev, staging, production) with different trait values

KubeVela ships with a built-in application delivery engine that supports progressive rollouts, canary deployments, and A/B testing out of the box.

### Installation

KubeVela is also installed via Helm, with additional CLI tooling:

```bash
helm repo add kubevela https://kubevela.github.io/charts
helm repo update

helm install kubevela kubevela/vela-core \
  --namespace vela-system \
  --create-namespace \
  --version 1.10.0

# Install the vela CLI
curl -fsSl https://kubevela.net/script/install.sh | bash -s 1.10.0
```

Verify the installation:

```bash
vela version
# Vela CLI Version: v1.10.0

kubectl get pods -n vela-system
# NAME                                     READY   STATUS
# kubevela-vela-core-6f7b8c9d-xy123        1/1     Running
```

### Configuration Example: Multi-Cluster Application

Here is a KubeVela Application that deploys a web service with autoscaling across two clusters:

```yaml
apiVersion: core.oam.dev/v1beta1
kind: Application
metadata:
  name: webapp-production
  namespace: default
spec:
  components:
    - name: webapp
      type: webservice
      properties:
        image: myregistry/webapp:v2.1.0
        port: 8080
      traits:
        - type: scaler
          properties:
            replicas: 3
        - type: autoscaler
          properties:
            min: 2
            max: 10
            cpuUtilization: 70
        - type: ingress
          properties:
            domain: webapp.example.com
            http:
              "/": 8080
  policies:
    - name: topology
      type: topology
      properties:
        clusters: ["cluster-hangzhou", "cluster-shanghai"]
        namespace: production
    - name: override
      type: override
      properties:
        components:
          - type: webservice
            traits:
              - type: scaler
                properties:
                  replicas: 5
  workflow:
    steps:
      - name: hangzhou
        type: deploy
        properties:
          policies: ["topology"]
      - name: manual-approval
        type: suspend
      - name: shanghai
        type: deploy
        properties:
          policies: ["topology", "override"]
```

This application deploys to two clusters sequentially, pauses for manual approval between deployments, and overrides the replica count for the second cluster.

## 3. Kubernetes Operators — The Native Approach

Kubernetes Operators are custom controllers that manage application-specific lifecycle operations. Built using the **Operator SDK** (based on controller-runtime), Operators encode operational knowledge — backup strategies, upgrade procedures, scaling decisions — into software that runs directly on your cluster.

**GitHub stats (Operator SDK):** 7,633 stars · Last push: April 17, 2026 · Language: Go

### Architecture

Unlike Crossplane and KubeVela, Operators are purpose-built for a specific application or service. The PostgreSQL Operator manages PostgreSQL clusters, the Elasticsearch Operator manages Elasticsearch clusters, and so on. The Operator SDK provides scaffolding to build your own.

The core pattern is the **reconciliation loop**:

```
Watch Custom Resource → Read Desired State → Compare with Actual State → Take Action → Update Status
```

### Installation and Scaffolding

The Operator SDK provides a CLI to scaffold new operators:

```bash
# Install operator-sdk
curl -LO https://github.com/operator-framework/operator-sdk/releases/download/v1.39.1/operator-sdk_linux_amd64
chmod +x operator-sdk_linux_amd64
sudo mv operator-sdk_linux_amd64 /usr/local/bin/operator-sdk

# Initialize a new Go-based operator
mkdir my-operator && cd my-operator
operator-sdk init --domain example.com --repo github.com/example/my-operator

# Create a new API and controller
operator-sdk create api --group cache --version v1alpha1 --kind Memcached --resource --controller

# Generate and run
make generate && make manifests
make run
```

### Configuration Example: Custom Resource

Once built, the operator manages instances defined by Custom Resource Definitions:

```yaml
apiVersion: cache.example.com/v1alpha1
kind: Memcached
metadata:
  name: memcached-sample
  namespace: default
spec:
  size: 3
  image: memcached:1.6-alpine
  port: 11211
  resources:
    requests:
      memory: "64Mi"
      cpu: "250m"
    limits:
      memory: "128Mi"
      cpu: "500m"
  affinity:
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
        - weight: 100
          podAffinityTerm:
            labelSelector:
              matchExpressions:
                - key: app
                  operator: In
                  values: ["memcached"]
            topologyKey: kubernetes.io/hostname
```

The operator's reconciliation loop reads this spec, creates three Memcached pods with the specified resource constraints, and continuously ensures the actual state matches the desired state.

## Comparison Table

| Feature | Crossplane | KubeVela | Kubernetes Operators |
|---------|-----------|----------|---------------------|
| **Primary Focus** | Cloud resource provisioning | Application delivery & multi-cluster | Application lifecycle management |
| **CNCF Status** | Graduated | Sandbox | Sandbox (Operator Framework) |
| **GitHub Stars** | 11,615 | 7,740 | 7,633 (SDK) |
| **Language** | Go | Go | Go |
| **Installation** | Helm chart | Helm chart + CLI | operator-sdk CLI |
| **Multi-Cloud** | Native (provider packages) | Supported (cluster registration) | Per-operator implementation |
| **Multi-Cluster** | Supported | First-class (built-in) | Custom per operator |
| **Self-Service API** | XRDs + Claims | Application model | Custom CRDs |
| **Progressive Delivery** | Limited | Built-in workflows | Custom per operator |
| **Learning Curve** | Moderate | Moderate | Steep (Go development) |
| **Extensibility** | Provider packages | Addons & definitions | Full Go code |
| **Best For** | Platform teams building self-service infrastructure | Teams needing multi-cluster app delivery with progressive rollouts | Teams building operators for specific complex applications |

## When to Choose Which

### Choose Crossplane if:

- Your platform team needs to provision cloud resources (databases, buckets, networks) through Kubernetes APIs
- You want to compose multiple cloud services into higher-level abstractions for application teams
- Multi-cloud portability is a core requirement
- You prefer declarative YAML over writing Go code
- You need policy enforcement through OPA/Gatekeeper or Kyverno

For teams evaluating traditional IaC tools alongside Kubernetes-native options, our [OpenTofu vs Terraform vs Pulumi guide](../opentofu-vs-terraform-vs-pulumi-self-hosted-iac-guide-2026/) provides complementary context on when to use each approach.

### Choose KubeVela if:

- You need multi-cluster application delivery with progressive rollouts
- Your applications span multiple environments (dev, staging, production) with different configurations
- You want built-in canary deployments, A/B testing, and manual approval gates
- Your team uses the OAM specification or wants application-centric abstractions
- You need to deploy across hybrid cloud (Kubernetes + VMs + serverless)

If your GitOps workflow needs integration with the delivery tools, see our [ArgoCD vs Flux comparison](../argocd-vs-flux-self-hosted-gitops-guide/) for understanding the broader CI/CD ecosystem.

### Choose Kubernetes Operators if:

- You need to manage a specific complex application (database, message queue, monitoring stack)
- The application has non-trivial lifecycle operations (backup, restore, version upgrade, failover)
- You want to encode operational runbooks as software
- Your team has Go development capacity to build and maintain custom controllers
- The application is not well-served by generic infrastructure tools

For teams also managing Kubernetes secrets and certificates through operators, the [External Secrets vs Sealed Secrets guide](../2026-04-20-external-secrets-operator-vs-sealed-secrets-vs-vault-secrets-operator-kubernetes-secrets-management-2026/) covers the complementary security side of cluster operations.

## Integration Patterns

In practice, these tools are not mutually exclusive. Mature platform teams often combine them:

```
┌─────────────────────────────────────────────┐
│              Application Team               │
│                                             │
│  kubectl apply -f my-database.yaml          │
│  kubectl apply -f my-application.yaml       │
└───────────────┬──────────────┬──────────────┘
                │              │
     ┌──────────▼───┐    ┌─────▼──────────┐
     │  Crossplane  │    │    KubeVela    │
     │              │    │                │
     │ Compositions │    │  Applications  │
     │   (Infra)    │    │  (Delivery)    │
     └──────┬───────┘    └──────┬─────────┘
            │                   │
     ┌──────▼───────┐    ┌──────▼─────────┐
     │ AWS/GCP/Azure│    │ Cluster A/B/C  │
     │   Cloud APIs │    │ Kubernetes     │
     └──────────────┘    └────────────────┘
```

Crossplane provisions the underlying infrastructure (databases, buckets, networks) while KubeVela handles application deployment, rollout strategies, and multi-cluster distribution. Custom Operators manage specific applications that need deep lifecycle control.

## FAQ

### Is Crossplane a replacement for Terraform?

Not exactly. Crossplane and Terraform solve overlapping problems but with different paradigms. Terraform uses imperative state files and a plan-apply workflow, while Crossplane uses continuous reconciliation through Kubernetes APIs. Many teams use both: Terraform for bootstrapping the Kubernetes cluster and Crossplane for ongoing infrastructure management. If you prefer traditional IaC, consider reading our [OpenTofu vs Terraform vs Pulumi comparison](../opentofu-vs-terraform-vs-pulumi-self-hosted-iac-guide-2026/) to understand the broader landscape.

### Can KubeVela manage cloud infrastructure like databases and buckets?

KubeVela can reference cloud resources through its component types, but it is not a cloud provisioning tool in the same way Crossplane is. KubeVela's strength lies in application delivery, multi-cluster deployment, and progressive rollouts. For cloud resource provisioning, teams typically pair KubeVela with Crossplane or Terraform.

### Do I need to write Go code to use Kubernetes Operators?

To build a custom Operator, yes — the Operator SDK is a Go-based framework. However, you do not need to write Go to *use* existing Operators. Many popular applications (PostgreSQL, Elasticsearch, Redis, Kafka) have pre-built Operators that you install and configure entirely through YAML Custom Resources.

### Which approach has the smallest learning curve?

KubeVela generally has the gentlest learning curve for teams already familiar with Kubernetes Deployments and Services. Its Application model is an extension of familiar concepts. Crossplane requires understanding Compositions and XRDs, which is a bigger conceptual leap. Building custom Operators requires Go development experience and understanding of controller-runtime patterns.

### Can these tools work with GitOps workflows?

All three approaches are fully compatible with GitOps. Since every configuration is stored as Kubernetes YAML, you can version-control your infrastructure definitions in Git and use tools like ArgoCD or Flux to sync them to your clusters. The reconciliation loops in Crossplane and Operators naturally fit the GitOps desired-state model.

### How do these tools handle secrets for cloud provider credentials?

Crossplane uses Kubernetes Secrets referenced by ProviderConfig resources. KubeVela can reference secrets through its policy system. Operators typically read secrets from the namespace where they are deployed. For production deployments, integrate with a secrets manager like HashiCorp Vault or use the External Secrets Operator to sync secrets from your chosen vault.

## Final Recommendation

For most platform teams starting their self-hosted infrastructure management journey, **Crossplane** offers the best balance of power and accessibility. Its provider ecosystem covers all major cloud platforms, Compositions enable true self-service APIs, and the CNCF Graduated status guarantees long-term project stability.

Teams with heavy multi-cluster application delivery needs should evaluate **KubeVela** alongside Crossplane, as the two tools complement each other well. Teams building operators for specific complex applications should invest in the **Operator SDK** — but only when generic infrastructure tools cannot solve the problem.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Crossplane vs KubeVela vs Kubernetes Operators: Cloud Infrastructure Management 2026",
  "description": "Compare Crossplane, KubeVela, and Kubernetes Operators for managing cloud infrastructure. Complete Helm install guides, YAML configuration examples, and decision framework for platform teams in 2026.",
  "datePublished": "2026-04-23",
  "dateModified": "2026-04-23",
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
