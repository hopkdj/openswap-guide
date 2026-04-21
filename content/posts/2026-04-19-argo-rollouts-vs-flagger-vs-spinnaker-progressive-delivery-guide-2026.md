---
title: "Argo Rollouts vs Flagger vs Spinnaker: Best Progressive Delivery Tools 2026"
date: 2026-04-19
tags: ["comparison", "guide", "kubernetes", "deployment", "progressive-delivery"]
draft: false
description: "Compare Argo Rollouts, Flagger, and Spinnaker for progressive delivery — canary, blue-green, and A/B testing deployments on Kubernetes. Installation guides, configs, and feature breakdown."
---

Progressive delivery has replaced traditional blue-green and canary deployments as the standard for releasing software safely in production. Instead of flipping a switch and hoping for the best, progressive delivery tools automatically shift traffic between old and new versions while monitoring key metrics — rolling back instantly if something goes wrong.

For teams running [kubernetes](https://kubernetes.io/), three open-source options dominate the progressive delivery space: **Argo Rollouts**, **Flagger**, and **Spinnaker**. Each takes a different architectural approach, and the right choice depends on your existing toolchain, cluster com[plex](https://www.plex.tv/)ity, and deployment maturity.

As of April 2026, here is the current state of each project:

| Tool | GitHub Stars | Language | Last Updated |
|------|-------------|----------|--------------|
| [Argo Rollouts](https://github.com/argoproj/argo-rollouts) | 3,445 | Go | 2026-04-14 |
| [Flagger](https://github.com/fluxcd/flagger) | 5,312 | Go | 2026-04-18 |
| [Spinnaker](https://github.com/spinnaker/spinnaker) | 9,710 | Java | 2026-04-19 |

## Why Progressive Delivery Matters

Traditional deployment strategies — rolling updates, recreate, and basic blue-green — lack feedback loops. A bad deployment might run for minutes or hours before someone notices error rates spiking. Progressive delivery closes that gap by coupling traffic management with real-time metric analysis.

The core benefits of self-hosting your progressive delivery pipeline include:

- **Zero-downtime releases**: Traffic shifts gradually; users never see a broken version
- **Automatic rollback**: Metrics-triggered rollbacks happen in seconds, not after a PagerDuty alert
- **Experimentation**: A/B testing lets you validate features against real user behavior
- **Audit trail**: Every deployment step is tracked and reproducible
- **Cloud independence**: Self-hosted tools work on any Kubernetes cluster, not just AWS or GCP

For teams already managing their own [Kubernetes clusters](../kubernetes-vs-docker-swarm-vs-nomad/), adding progressive delivery is the natural next step in deployment maturity.

## Argo Rollouts

Argo Rollouts is a Kubernetes controller that extends the native Deployment resource with advanced deployment capabilities. It is part of the [Argo project](https://argoproj.github.io/), which also includes Argo CD for GitOps.

### Architecture

Argo Rollouts introduces a custom resource definition (CRD) called `Rollout` that replaces the standard Kubernetes `Deployment`. The controller watches Rollout resources and manages ReplicaSets, traffic splitting, and analysis runs.

Key components:
- **Rollout controller**: Manages the lifecycle of progressive deployments
[prometheus](https://prometheus.io/)is controller**: Evaluates metrics from Prometheus, Datadog, Wavefront, or other providers
- **kubectl plugin**: Provides CLI commands for managing rollouts
- **Argo Rollouts Dashboard**: Optional web UI for visualizing deployment state

### Installation

The recommended installation method uses Kubernetes manifests:

```bash
kubectl create namespace argo-rollouts
kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml
```

Alternatively, install via Helm:

```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm install argo-rollouts argo/argo-rollouts -n argo-rollouts
```

Verify the installation:

```bash
kubectl get pods -n argo-rollouts
# NAME                              READY   STATUS
# argo-rollouts-7d6f6b8c9-x4k2m    1/1     Running
```

### Canary Deployment Example

Here is a complete Rollout definition with canary strategy, traffic splitting via Istio, and automated analysis:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: my-app
spec:
  replicas: 5
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
        - name: my-app
          image: my-app:1.0.0
          ports:
            - containerPort: 8080
  strategy:
    canary:
      steps:
        - setWeight: 20
        - pause: {duration: 2m}
        - setWeight: 40
        - pause: {duration: 2m}
        - setWeight: 60
        - analysis:
            templates:
              - templateName: success-rate
        - setWeight: 80
        - pause: {duration: 5m}
      trafficRouting:
        istio:
          virtualService:
            name: my-app-vsvc
            routes:
              - primary
```

The corresponding AnalysisTemplate checks Prometheus metrics:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
spec:
  metrics:
    - name: success-rate
      interval: 1m
      successCondition: result[0] >= 0.95
      provider:
        prometheus:
          address: http://prometheus.monitoring:9090
          query: |
            sum(rate(http_requests_total{service="my-app",code=~"2.*"}[1m]))
            /
            sum(rate(http_requests_total{service="my-app"}[1m]))
```

### Blue-Green Deployment Example

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: my-app
spec:
  replicas: 3
  strategy:
    blueGreen:
      activeService: my-app-active
      previewService: my-app-preview
      autoPromotionEnabled: true
      autoPromotionSeconds: 300
      scaleDownDelaySeconds: 30
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
        - name: my-app
          image: my-app:2.0.0
          ports:
            - containerPort: 8080
```

## Flagger

Flagger is a Kubernetes operator developed by Weaveworks (now part of the Flux CD project). It automates the promotion of canary deployments using istio, linkerd, app mesh, contour, gloo, nginx, or gateway API for traffic routing.

### Architecture

Flagger runs as a Kubernetes operator that watches Canary resources. Unlike Argo Rollouts, which replaces the Deployment resource, Flagger works alongside existing Deployments and manages traffic splitting at the service mesh or ingress level.

Key components:
- **Flagger operator**: Watches Canary CRDs and orchestrates progressive deployments
- **Canary CRD**: Defines the deployment strategy, metrics, and thresholds
- **Metric providers**: Native integration with Prometheus, Datadog, CloudWatch, Grafana, and New Relic
- **Service mesh support**: Istio, Linkerd, App Mesh, and plain Kubernetes Services

### Installation

Install Flagger via Helm on your Kubernetes cluster. If you're evaluating lightweight Kubernetes distributions, see our [comparison of k3s, k0s, and Talos](../k3s-vs-k0s-vs-talos-linux-self-hosted-kubernetes-guide-2026/) for cluster setup options.

```bash
helm repo add flagger https://flagger.app
helm repo update

helm upgrade -i flagger flagger/flagger \
  --namespace flagger-system \
  --create-namespace \
  --set crd.create=true \
  --set meshProvider=istio \
  --set metricsServer=http://prometheus.istio-system:9090
```

For Linkerd:

```bash
helm upgrade -i flagger flagger/flagger \
  --namespace flagger-system \
  --set meshProvider=linkerd \
  --set metricsServer=http://linkerd-prometheus.linkerd-viz:9090
```

### Canary Deployment Example

A Flagger Canary resource works alongside a standard Deployment:

```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: my-app
  namespace: production
spec:
  provider: istio
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  progressDeadlineSeconds: 60
  service:
    port: 8080
    targetPort: 8080
    gateways:
      - my-app-gateway
    hosts:
      - my-app.example.com
  analysis:
    interval: 30s
    threshold: 10
    maxWeight: 50
    stepWeight: 10
    metrics:
      - name: request-success-rate
        thresholdRange:
          min: 99
        interval: 1m
      - name: request-duration
        thresholdRange:
          max: 500
        interval: 1m
    webhooks:
      - name: load-test
        url: http://flagger-loadtester.test/
        type: rolling
        metadata:
          cmd: "hey -z 1m -q 10 -c 2 http://my-app-canary.production:8080/"
```

The analysis section defines two metrics:
- **request-success-rate**: Must stay above 99% during the canary
- **request-duration**: P99 latency must stay below 500ms

If either metric fails the threshold 10 times, Flagger automatically rolls back the deployment.

### A/B Testing Example

Flagger supports HTTP header and cookie-based A/B testing:

```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: my-app-ab
spec:
  provider: istio
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  service:
    port: 8080
  analysis:
    interval: 30s
    threshold: 5
    iterations: 10
    match:
      - headers:
          x-ab-test:
            exact: "variant-b"
      - headers:
          cookie:
            regex: "^(.*?;)?(ab_test=variant-b)(;.*)?$"
```

This routes users with the `x-ab-test: variant-b` header or the `ab_test=variant-b` cookie to the canary version.

## Spinnaker

Spinnaker is the most mature and feature-complete progressive delivery platform. Originally built by Netflix, it is a multi-cloud continuous delivery platform that supports complex deployment pipelines across Kubernetes, VMs, and serverless targets.

### Architecture

Spinnaker is a microservices-based platform with separate services for each function. This gives it enormous flexibility but also makes it the most complex to install and operate.

Key components:
- **Deck**: Web UI (Angular-based)
- **Gate**: API gateway
- **Orca**: Orchestration engine
- **Clouddriver**: Cloud provider integrations
- **Echo**: Event handling and notifications
- **Front50**: Pipeline and application persistence
- **Igor**: CI system integrations (Jenkins, Travis CI)
- **Kayenta**: Automated canary analysis
- **Keel**: Delivery automation and constraints

### Installation

Spinnaker is typically installed using [Halyard](https://spinnaker.io/setup/install/halyard/) — a dedicated management tool — or via the Helm-based [Operator](https://spinnaker.io/setup/install/kubernetes/).

#### Method 1: Halyard (Docker-based)

```bash
# Pull the Halyard Docker image
docker pull gcr.io/spinnaker-marketplace/halyard:stable

# Run Halyard container
docker run --name halyard -d \
  -v ~/.hal:/home/spinnaker/.hal \
  -v ~/.kube/config:/home/spinnaker/.kube/config \
  gcr.io/spinnaker-marketplace/halyard:stable

# Enter the Halyard container
docker exec -it halyard bash

# Inside Halyard, configure your deployment
hal config provider kubernetes enable
hal config provider kubernetes account add my-k8s \
  --provider-version v2 \
  --context $(kubectl config current-context)

hal config deploy edit --type distributed \
  --account-name my-k8s

# Choose a storage backend for pipeline data
hal config storage s3 edit \
  --bucket spinnaker-storage \
  --access-key-id $AWS_ACCESS_KEY_ID \
  --secret-access-key $AWS_SECRET_ACCESS_KEY
hal config storage edit --type s3

# Deploy Spinnaker
hal deploy apply
```

#### Method 2: Helm Operator

```bash
helm repo add spinnaker https://spinnaker.github.io/helm/charts
helm repo update

helm install spinnaker-operator spinnaker/spinnaker-operator \
  --namespace spinnaker-operator \
  --create-namespace \
  --set spinnakerConfig.files.profiles/spinnaker.yml='
deploymentEnvironment:
  size: small
persistentStorage:
  persistentStoreType: s3
  s3:
    bucket: spinnaker-storage
    rootFolder: front50
    accessKeyId: $AWS_ACCESS_KEY_ID
    secretAccessKey: $AWS_SECRET_ACCESS_KEY
    region: us-east-1
'
```

### Kubernetes Deployment Pipeline Example

A Spinnaker pipeline definition (in JSON format managed via the UI or spin CLI):

```json
{
  "application": "my-app",
  "name": "Deploy to Production",
  "stages": [
    {
      "type": "findImageFromTags",
      "name": "Find Latest Image",
      "cloudProviderType": "kubernetes",
      "tags": {
        "branch": "main"
      }
    },
    {
      "type": "deploy",
      "name": "Deploy Canary",
      "clusters": [
        {
          "application": "my-app",
          "containers": [
            {
              "name": "my-app",
              "imageDescription": {
                "fromContext": "Find Latest Image"
              }
            }
          ],
          "strategy": "redblack",
          "targetSize": 2
        }
      ]
    },
    {
      "type": "canary",
      "name": "Canary Analysis",
      "canaryConfig": {
        "lifetimeDuration": "PT30M",
        "metricsAccount": "prometheus",
        "storageAccountName": "s3-storage",
        "scoreThresholds": {
          "marginal": 75,
          "pass": 95
        },
        "templates": {
          "canaryConfigId": "my-app-canary-template"
        }
      }
    },
    {
      "type": "manualJudgment",
      "name": "Approve Promotion",
      "instructions": "Canary analysis passed. Approve full rollout?"
    },
    {
      "type": "deploy",
      "name": "Promote to Full",
      "clusters": [
        {
          "application": "my-app",
          "containers": [
            {
              "name": "my-app"
            }
          ],
          "strategy": "redblack",
          "targetSize": 5
        }
      ]
    }
  ]
}
```

## Feature Comparison

| Feature | Argo Rollouts | Flagger | Spinnaker |
|---------|--------------|---------|-----------|
| **Deployment strategies** | Canary, Blue-Green | Canary, Blue/Green, A/B, Mirror | Canary, Blue/Green, Red/Black, Rolling |
| **Kubernetes CRD** | Rollout | Canary | No (uses Pipelines) |
| **Traffic routing** | Istio, ALB, Nginx, SMI, Ambassador | Istio, Linkerd, App Mesh, Contour, Gloo, Nginx, Gateway API | Native Kubernetes, AWS, GCP, Azure |
| **Metric providers** | Prometheus, Datadog, Wavefront, New Relic, Web | Prometheus, Datadog, CloudWatch, Grafana, New Relic | Prometheus, Datadog, Stackdriver, custom |
| **Web UI** | Separate dashboard | None (CLI + Kubernetes events) | Full-featured UI (Deck) |
| **Multi-cluster** | No | No | Yes (native) |
| **Multi-cloud** | Kubernetes only | Kubernetes only | Kubernetes, AWS EC2, GCE, Azure, Lambda |
| **Installation complexity** | Low (single manifest) | Low (Helm chart) | High (10+ microservices) |
| **Learning curve** | Low (familiar K8s patterns) | Medium (Canary CRD concepts) | High (pipeline DSL, many services) |
| **CI/CD integration** | Argo CD, kubectl | Flux CD, kubectl | Jenkins, Travis, GitHub Actions, GitLab |
| **Automated rollback** | Yes (analysis-based) | Yes (metric-threshold based) | Yes (Kayenta canary analysis) |
| **A/B testing** | Via header matching | Native (header + cookie) | Via traffic guards |
| **GitHub stars** | 3,445 | 5,312 | 9,710 |
| **Resource requirements** | ~50MB RAM | ~80MB RAM | ~8GB+ RAM (full deployment) |

## Installation and Resource Requirements

### Minimum Hardware Requirements

| Tool | CPU | RAM | Storage | Nodes |
|------|-----|-----|---------|-------|
| Argo Rollouts | 100m | 128Mi | 10Mi | 1 |
| Flagger | 100m | 256Mi | 50Mi | 1 |
| Spinnaker | 4 cores | 8Gi | 20Gi | 3+ |

Spinnaker's microservices architecture means each component (Deck, Gate, Orca, Clouddriver, Echo, Front50, Igor, Kayenta) runs as a separate pod. A minimal installation requires significant resources. Argo Rollouts and Flagger, by contrast, are single-controller operators that run in under 256MB of RAM.

### Helm Values for Production

For Argo Rollouts in production:

```yaml
# values-argo-rollouts.yaml
controller:
  replicas: 2
  metrics:
    enabled: true
    serviceMonitor:
      enabled: true
  podAntiAffinity: true

dashboard:
  enabled: true
  replicas: 1
  service:
    type: ClusterIP
```

For Flagger with Prometheus integration:

```yaml
# values-flagger.yaml
crd:
  create: true

meshProvider: istio
metricsServer: http://prometheus.istio-system:9090

reloadInterval: 15s
logLevel: info

podMonitor:
  enabled: true
```

## Choosing the Right Tool

### Choose Argo Rollouts if:
- You already use Argo CD for GitOps — the integration is seamless
- You want lightweight, CRD-based progressive delivery with minimal overhead
- Your team is comfortable with Kubernetes-native patterns
- You need both canary and blue-green strategies with automated analysis

### Choose Flagger if:
- You use Flux CD for GitOps — Flagger integrates directly with the Flux ecosystem
- You need A/B testing with header and cookie matching out of the box
- You want to support multiple service meshes (Istio, Linkerd, App Mesh)
- You prefer a metrics-driven approach with built-in load testing

### Choose Spinnaker if:
- You deploy across multiple clouds or infrastructure types (VMs, serverless, containers)
- You need a full-featured web UI with visual pipeline editing
- Your deployment pipelines involve manual approval gates, complex stage orchestration, and multi-account deployments
- You have the infrastructure to run 10+ microservices (8GB+ RAM minimum)
- Your team already uses Jenkins or CI systems that Spinnaker integrates with natively

For teams starting their progressive delivery journey with Kubernetes, **Argo Rollouts** or **Flagger** are the best entry points — they install in minutes and integrate naturally with GitOps workflows. Teams that already run Spinnaker for multi-cloud deployments should evaluate whether migrating progressive delivery to a Kubernetes-native tool reduces operational overhead.

If you're building out a complete GitOps pipeline, pairing progressive delivery with [Argo CD or Flux](../argocd-vs-flux-self-hosted-gitops-guide/) gives you end-to-end automated deployments from code commit to production traffic. For teams still setting up their CI/CD foundations, our [comparison of self-hosted CI/CD runners](../self-hosted-ci-cd-woodpecker-drone-jenkins-concourse-2026/) covers the build and test stage that feeds into progressive delivery.

## FAQ

### What is the difference between progressive delivery and continuous delivery?

Continuous delivery (CD) automates the process of getting code changes from version control into production. Progressive delivery is an evolution of CD that adds automated traffic management and metric-based validation during the deployment itself. While CD focuses on *getting code to production*, progressive delivery focuses on *safely exposing that code to users* with automatic rollback if metrics degrade.

### Can Argo Rollouts and Flagger work together?

No, they serve the same purpose and would conflict. Both manage traffic splitting and canary analysis for Kubernetes Deployments. You should choose one based on your existing ecosystem: Argo Rollouts pairs with Argo CD, while Flagger integrates with Flux CD.

### Does Spinnaker require Kubernetes?

No. Spinnaker is a multi-cloud platform that supports Kubernetes, Amazon EC2, Google Compute Engine, Azure, AWS Lambda, and more. However, Kubernetes is by far the most common deployment target for Spinnaker users.

### How do progressive delivery tools handle database migrations?

Progressive delivery tools manage application traffic, not database state. Database migrations should be handled separately, typically as a pre-deployment step in your CI/CD pipeline. For backward-compatible schema changes, run migrations before deploying the new application version. For breaking changes, use feature flags or deploy a migration service separately.

### What metrics should I use for automated canary analysis?

The most common and effective metrics are:
- **HTTP success rate** (2xx responses / total requests) — aim for >99%
- **HTTP error rate** (5xx responses / total requests) — should stay <1%
- **Response latency** (p95 or p99) — compare against the baseline version
- **Business metrics** (conversion rate, checkout completion) — if available in your monitoring stack

Start with HTTP success rate and latency, then add business-specific metrics as your monitoring matures.

### How much infrastructure does Spinnaker need?

A production Spinnaker installation requires at least 8GB of RAM, 4 CPU cores, and runs across 10+ microservices (Deck, Gate, Orca, Clouddriver, Echo, Front50, Igor, Kayenta, Fiat, and optionally Keel). For comparison, Argo Rollouts runs in under 128MB RAM as a single controller pod.

### Can I use progressive delivery without a service mesh?

Yes. Argo Rollouts supports Nginx ingress controller and AWS ALB for traffic splitting without a service mesh. Flagger supports Nginx ingress and Gateway API. Spinnaker uses native Kubernetes Services with its own traffic management. A service mesh like Istio or Linkerd provides more granular control but is not strictly required.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Argo Rollouts vs Flagger vs Spinnaker: Best Progressive Delivery Tools 2026",
  "description": "Compare Argo Rollouts, Flagger, and Spinnaker for progressive delivery — canary, blue-green, and A/B testing deployments on Kubernetes. Installation guides, configs, and feature breakdown.",
  "datePublished": "2026-04-19",
  "dateModified": "2026-04-19",
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
