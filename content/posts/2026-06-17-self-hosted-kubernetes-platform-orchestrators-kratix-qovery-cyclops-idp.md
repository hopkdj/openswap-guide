---
title: "Self-Hosted Kubernetes Platform Orchestration: Kratix vs Qovery vs Cyclops for Internal Developer Platforms"
date: "2026-06-17"
tags: ["platform-engineering", "kubernetes", "idp", "kratix", "qovery", "cyclops", "internal-developer-platform", "devops", "self-hosted"]
draft: false
---

## Introduction

The rise of **platform engineering** has transformed how organizations manage Kubernetes at scale. Instead of every development team wrestling with YAML manifests, Helm charts, and Terraform modules, platform teams now build **Internal Developer Platforms (IDPs)** — self-service portals that abstract infrastructure complexity behind a clean UI and API. Developers request databases, deploy services, and provision environments through a golden path, while the platform orchestrator handles the underlying Kubernetes operations.

In this guide, we compare three emerging open-source platform orchestrators: **Kratix** (a Promise-based platform framework), **Qovery** (a Rust-powered infrastructure engine), and **Cyclops** (a developer-friendly Kubernetes UI). Each takes a unique approach to the same goal: making Kubernetes invisible to developers while empowering platform teams to define and enforce standards.

## Comparison Table

| Feature | Kratix | Qovery | Cyclops |
|---------|--------|--------|---------|
| **Stars** | 753 | 2,446 | 3,323 |
| **Language** | Go | Rust | Go |
| **Approach** | Promise-based framework | Infrastructure orchestration engine | Kubernetes abstraction UI |
| **API Model** | Custom CRDs (Promises) | Declarative environment specs | Helm chart templates |
| **Multi-Cloud** | Yes (via Promise pipelines) | Yes (AWS, GCP, Azure, Scaleway) | Kubernetes-native (any K8s) |
| **GitOps Integration** | Flux, ArgoCD | Native GitOps | Git-based Helm chart repos |
| **Self-Service UI** | Marketplace-style catalog | Web dashboard + CLI | Visual editor for Helm values |
| **RBAC & Governance** | Promise-level permissions | Environment-level RBAC | Kubernetes RBAC |
| **Docker Compose** | N/A (Helm-based) | N/A (CLI + Helm) | N/A (Helm-based) |
| **Resource Usage** | Light (controller + workers) | Medium (engine + API + DB) | Light (single deployment) |
| **Best For** | Platform teams building custom APIs | Full-stack infrastructure provisioning | Teams migrating from PaaS to K8s |

## Kratix: Promises as the Platform Primitive

Kratix introduces a novel concept called **Promises** — custom Kubernetes resources that encapsulate the full lifecycle of a service. When a developer requests a PostgreSQL database through a Promise, Kratix orchestrates the entire workflow: provisioning storage, deploying the database operator, configuring backups, exposing connection details, and handling day-2 operations like upgrades and scaling.

### Key Architecture

Kratix is built around a **Marketplace** metaphor. Platform teams define Promises (service blueprints) which are installed into a marketplace. Application teams browse the marketplace and request instances of those services. Each Promise can trigger multi-step pipelines across different clusters:

```yaml
# Kratix Promise definition (simplified)
apiVersion: platform.kratix.io/v1alpha1
kind: Promise
metadata:
  name: postgresql
spec:
  api:
    apiVersion: apiextensions.k8s.io/v1
    kind: CustomResourceDefinition
    metadata:
      name: postgresqls.marketplace.kratix.io
    spec:
      group: marketplace.kratix.io
      names:
        kind: PostgreSQL
      versions:
        - name: v1alpha1
          schema:
            openAPIV3Schema:
              properties:
                version:
                  type: string
                storage:
                  type: string
  workflows:
    resource:
      create:
        - pipeline:
            name: create-postgres
            containers:
              - name: create
                image: syntasso/postgresql-resource:latest
```

### Deployment via Helm

```bash
# Install Kratix on your management cluster
helm repo add syntasso https://syntasso.github.io/helm-charts
helm install kratix syntasso/kratix   --set platformCluster.platformClusterName=platform   --create-namespace   --namespace kratix-system

# Register worker clusters
kubectl apply -f https://raw.githubusercontent.com/syntasso/kratix/main/config/samples/cluster-registration.yaml
```

## Qovery: Rust-Powered Infrastructure Engine

Qovery takes a different approach — it's a full infrastructure orchestration engine written in Rust for performance and reliability. Rather than defining Promises or CRDs, Qovery uses a declarative **environment specification** that describes the entire application stack: containers, databases, DNS, TLS certificates, and network policies. The engine provisions everything across AWS, GCP, Azure, or a self-hosted Kubernetes cluster.

### Key Features

- **Multi-cloud abstraction**: Write once, deploy to AWS EKS, GCP GKE, Azure AKS, or on-prem K8s
- **Preview environments**: Automatic per-PR environments with full infrastructure clones
- **Auto-scaling**: Built-in HPA and cluster autoscaler integration
- **Cost optimization**: Idle environment detection and automatic shutdown
- **Terraform integration**: Existing Terraform modules can be imported

### CLI-Driven Deployment

```bash
# Install Qovery CLI
curl -s https://get.qovery.com | bash

# Initialize a project
qovery project create --name my-platform
qovery environment create --name production   --cluster my-k8s-cluster   --mode production

# Deploy an application
qovery application deploy   --name api-service   --git-url https://github.com/myorg/api-service   --branch main   --cpu 500m   --memory 512Mi   --ports 8080
```

## Cyclops: Developer-Friendly Kubernetes

Cyclops bridges the gap between complex Kubernetes YAML and developer self-service. It transforms Helm charts into visual forms that developers can fill out without understanding Kubernetes internals. Platform teams define chart templates with sensible defaults, and developers customize only the parameters relevant to their use case through a clean web UI.

### Key Features

- **Visual Helm editor**: Drag-and-drop form builder for Helm values
- **Chart templates**: Reusable module definitions with validation rules
- **Git-based storage**: Charts and values stored in Git repositories
- **Instant preview**: See the rendered Kubernetes manifests before deploying
- **Cost estimation**: Built-in resource cost calculator
- **Validation webhooks**: Pre-deployment policy checks

### Deployment via Helm

```bash
# Install Cyclops
helm repo add cyclops https://cyclops-ui.github.io/helm-charts
helm install cyclops cyclops/cyclops   --namespace cyclops   --create-namespace   --set ingress.enabled=true   --set ingress.host=platform.example.com

# Access the UI
kubectl port-forward svc/cyclops-ui 3000:3000 -n cyclops
```

## Choosing the Right Platform Orchestrator

Your choice depends on where your organization sits on the platform engineering maturity curve:

- **Kratix** is ideal for platform teams that want maximum flexibility and are comfortable defining their own APIs. The Promise model is powerful but requires upfront investment in designing the right service blueprints. Best for organizations with dedicated platform teams and multiple downstream engineering teams.

- **Qovery** excels at full-stack infrastructure provisioning — not just Kubernetes but also cloud resources like managed databases, load balancers, and DNS. If your platform needs to span multiple clouds with consistent developer experience, Qovery's Rust engine provides the performance and reliability for production workloads.

- **Cyclops** shines when you're migrating from a PaaS (Heroku, Render, Railway) to Kubernetes. Its visual Helm form builder dramatically reduces the learning curve, making it the fastest path to a working developer portal. Best for organizations where developer experience is the primary concern and Kubernetes complexity is the main friction point.

All three tools complement existing GitOps workflows. For teams already using [Crossplane for infrastructure management](../crossplane-vs-kubevela-vs-kubernetes-operators-infrastructure-management-2026/), Kratix integrates naturally as the application-layer complement. Teams building [Kubernetes operators](../2026-05-01-operator-sdk-vs-kubebuilder-vs-java-operator-sdk-kubernetes-operator-frameworks/) will find the Promise pattern familiar.

## Why Build an Internal Developer Platform?

Platform engineering isn't just about tooling — it's a cultural shift from "DevOps for everyone" to "you build it, platform runs it." Research from the State of DevOps Report shows that organizations with mature platform engineering practices deploy 2-3x more frequently and recover from incidents 2x faster than those without.

The core insight: **developers shouldn't need to understand Kubernetes to deploy a service**, just like they don't need to understand BGP to access the internet. A well-designed IDP abstracts infrastructure into self-service capabilities — request a database, get connection strings back. Request a deployment pipeline, get a CI/CD workflow configured. The platform team defines the golden paths; developers stay in flow.

Self-hosting your platform orchestrator (rather than using a SaaS IDP) gives you complete control over the developer experience, unlimited customization, and full data sovereignty. Your platform team can define exactly which services are available, with what configurations, at what cost, and on which clusters — something no SaaS platform can match.

## FAQ

### Do I need a dedicated platform team to use these tools?

Kratix and Qovery benefit from having platform engineers who understand the underlying infrastructure. Cyclops, on the other hand, can be adopted incrementally — a single DevOps engineer can set up Helm chart templates that developers fill out through the UI. Start with Cyclops if you're a small team; graduate to Kratix or Qovery as your platform needs grow.

### How do platform orchestrators handle stateful workloads like databases?

All three tools support stateful workloads through Kubernetes operators. Kratix Promises can include CloudNativePG or Zalando PostgreSQL operator. Qovery provisions managed databases on cloud providers or deploys operators on self-hosted clusters. Cyclops supports any Helm chart, including database operators. For production databases, ensure your platform orchestrator's backup and disaster recovery workflows are tested before going live.

### Can I migrate from one platform orchestrator to another?

Migration difficulty depends on your level of abstraction. If your developers interact with the orchestrator through Git-based workflows (committing environment specs or Helm values), migration is a matter of translating those specs. If your developers interact through a custom UI or API, migration requires more effort. Start with a pilot project on the new platform before committing to full migration.

### How do these tools compare to Backstage or Port?

Backstage and Port are developer portal frameworks — they provide a unified UI for discovering services, documentation, and tooling. Kratix, Qovery, and Cyclops are platform orchestrators — they actually provision and manage infrastructure. Many organizations use both: Backstage as the front door (service catalog, docs, search) and one of these orchestrators as the backend (infrastructure provisioning, environment management).

### What's the minimum Kubernetes cluster size for running a platform orchestrator?

Kratix and Cyclops are lightweight — they run comfortably on a 3-node cluster with 4GB RAM per node alongside your workloads. Qovery's engine requires more resources (PostgreSQL database, API server, worker processes) but can still run on a 3-node cluster with 8GB RAM per node. For production, separate your platform orchestrator's control plane from workload clusters for better isolation.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Kubernetes Platform Orchestration: Kratix vs Qovery vs Cyclops for Internal Developer Platforms",
  "description": "Compare Kratix, Qovery, and Cyclops for building self-hosted Internal Developer Platforms on Kubernetes. Helm deployment, platform engineering patterns, and decision guide.",
  "datePublished": "2026-06-17",
  "dateModified": "2026-06-17",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://pistack.xyz/logo.png"
    }
  }
}
</script>
