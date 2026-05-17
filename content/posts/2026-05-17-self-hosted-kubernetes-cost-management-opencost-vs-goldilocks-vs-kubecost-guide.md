---
title: "Self-Hosted Kubernetes Cost Management: OpenCost vs Goldilocks vs Kubecost (2026)"
date: "2026-05-17"
tags: ["kubernetes", "cost-management", "finops", "resource-optimization", "opencost", "goldilocks", "kubecost", "monitoring", "comparison", "guide", "self-hosted", "docker"]
draft: false
---

As Kubernetes adoption grows, managing cluster costs becomes increasingly critical. Without visibility into resource consumption and pricing, teams waste money on over-provisioned workloads, idle capacity, and inefficient scheduling. Kubernetes cost management tools help you understand, optimize, and control spending across your clusters.

In this guide, we compare three open-source Kubernetes cost management tools: **OpenCost** (CNCF sandbox), **Goldilocks** (Fairwinds/Google Cloud), and **Kubecost** (commercial with open-source core). Each takes a different approach to cost visibility and resource optimization.

## What Is Kubernetes Cost Management?

Kubernetes cost management involves tracking, analyzing, and optimizing the financial impact of running workloads in a Kubernetes cluster. This includes:

- **Resource cost allocation**: Understanding how much each namespace, deployment, or pod costs
- **Right-sizing recommendations**: Identifying over-provisioned or under-utilized resources
- **Capacity planning**: Forecasting future resource needs and associated costs
- **Showback and chargeback**: Allocating infrastructure costs to teams or business units
- **Idle resource detection**: Finding and eliminating wasted compute and storage

| Feature | OpenCost | Goldilocks | Kubecost |
|---|---|---|---|
| **Creator** | Kubecost (CNCF Sandbox) | Fairwinds (now Google Cloud) | Kubecost |
| **Stars** | 6,500+ | 3,200+ | 600+ (open-source core) |
| **License** | Apache 2.0 | Apache 2.0 | Proprietary (free tier) |
| **Primary Purpose** | Cost allocation and measurement | VPA recommendations | Full cost management platform |
| **Cost Model** | Provider pricing APIs | Resource requests/limits analysis | Provider pricing + custom rates |
| **Right-Sizing** | No (cost allocation only) | Yes (VPA recommendations) | Yes (built-in recommendations) |
| **Multi-Cluster** | Yes | Yes | Yes (enterprise) |
| **UI Dashboard** | Yes (built-in) | Yes (built-in) | Yes (rich dashboard) |
| **Alerting** | Via Prometheus integration | No | Yes (built-in) |
| **Cloud Provider Support** | AWS, GCP, Azure | Any (cloud-agnostic) | AWS, GCP, Azure, on-prem |
| **Best For** | Standardized cost allocation | Resource right-sizing | Enterprise cost management |

## OpenCost (CNCF Sandbox Project)

OpenCost is an open-source Kubernetes cost monitoring project that provides standardized cost allocation across clusters. It was originally developed by Kubecost and donated to the CNCF as a sandbox project in 2022.

### Key Features

- **CNCF standardization**: Provides a vendor-neutral API for Kubernetes cost allocation
- **Real-time cost monitoring**: Continuous cost tracking with Prometheus integration
- **Multi-dimensional allocation**: Costs broken down by namespace, deployment, pod, label, and node
- **Cloud provider pricing**: Integrates with AWS, GCP, and Azure pricing APIs
- **Custom pricing**: Support for custom rates and on-prem infrastructure costing
- **Prometheus-native**: Exposes metrics that integrate with existing Prometheus/Grafana setups

### Docker Compose

```yaml
version: "3.8"
services:
  opencost:
    image: quay.io/opencost/opencost:latest
    ports:
      - "9003:9003"
    environment:
      - PROMETHEUS_SERVER_ENDPOINT=http://prometheus:9090
      - CLOUD_PROVIDER_API_KEY=AIzaSyD29bG2EXAMPLE
      - EXPORT_CSV_PORT=9004
    depends_on:
      - prometheus

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus

volumes:
  prometheus-data:
```

### Installation

```bash
# Install via Helm (recommended)
helm repo add opencost https://opencost.github.io/opencost-helm-chart
helm install opencost opencost/opencost   --namespace opencost --create-namespace   --set opencost.prometheusUsername=""   --set opencost.prometheusPassword=""

# Or install via kubectl
kubectl apply --namespace opencost -f https://raw.githubusercontent.com/opencost/opencost/develop/kubernetes/opencost.yaml
```

### Usage

```bash
# Port-forward to access the UI
kubectl port-forward --namespace opencost svc/opencost 9003

# Query cost allocation via API
curl -s 'http://localhost:9003/allocation/compute' | jq .

# Get cost by namespace
curl -s 'http://localhost:9003/allocation/compute?window=7d&aggregate=namespace' | jq .

# Get cost by label
curl -s 'http://localhost:9003/allocation/compute?window=24h&aggregate=label:app' | jq .
```

## Goldilocks (VPA Recommendations)

Goldilocks is a Kubernetes resource recommendation tool that uses the Vertical Pod Autoscaler (VPA) to analyze actual resource usage and recommend optimal CPU and memory requests and limits.

### Key Features

- **VPA-based recommendations**: Leverages the Kubernetes VPA to analyze actual resource usage
- **Resource right-sizing**: Identifies over-provisioned and under-provisioned workloads
- **Dashboard UI**: Built-in web dashboard showing current vs recommended resource requests
- **Namespace management**: Control which namespaces Goldilocks monitors
- **Safe recommendations**: VPA recommendations are based on historical usage patterns
- **Cost impact estimation**: Shows potential savings from applying recommendations

### Docker Compose (Local Testing)

```yaml
version: "3.8"
services:
  goldilocks:
    image: us-docker.pkg.dev/fairwinds-ops-chart/goldilocks:v4.10.0
    ports:
      - "8080:8080"
    volumes:
      - ${HOME}/.kube/config:/root/.kube/config:ro
    environment:
      - KUBECONFIG=/root/.kube/config
```

### Installation

```bash
# Install via Helm
helm repo add fairwinds-stable https://charts.fairwinds.com/stable
helm install goldilocks fairwinds-stable/goldilocks   --namespace goldilocks --create-namespace

# Install VPA CRDs (required)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/autoscaler/master/vertical-pod-autoscaler/deploy/vpa-v1-crd-gen.yaml

# Install VPA recommender
kubectl apply -f https://raw.githubusercontent.com/kubernetes/autoscaler/master/vertical-pod-autoscaler/deploy/recommender.yaml
```

### Usage

```bash
# Enable Goldilocks for a namespace
kubectl label namespace production goldilocks.fairwinds.com/enabled=true

# Set VPA update mode (Off = recommendations only)
kubectl label namespace production goldilocks.fairwinds.com/vpa-update-mode=off

# Access the dashboard
kubectl port-forward --namespace goldilocks svc/goldilocks-dashboard 8080

# View recommendations via API
kubectl get vpa -A
```

### Example Dashboard Output

```
NAMESPACE    DEPLOYMENT          CPU REQUEST    CPU RECOMMEND    MEM REQUEST    MEM RECOMMEND
production   api-server          500m           250m             1Gi            512Mi
production   worker              2              1                4Gi            2Gi
staging      frontend            1              500m             2Gi            1Gi
```

## Kubecost

Kubecost is a comprehensive Kubernetes cost management platform that combines cost allocation, right-sizing, budgeting, and alerting. The open-source core provides basic cost monitoring, while the enterprise edition adds advanced features.

### Key Features

- **Cost allocation**: Real-time cost breakdown by namespace, deployment, pod, label, and node
- **Right-sizing recommendations**: CPU and memory optimization suggestions
- **Budget alerts**: Set budgets and receive alerts when spending exceeds thresholds
- **Savings estimation**: Calculate potential savings from resource optimization
- **Multi-cluster support**: Aggregate cost data across multiple clusters
- **Custom pricing**: Support for on-prem infrastructure, reserved instances, and spot pricing
- **Efficiency scoring**: Cluster-wide efficiency metrics and trends

### Docker Compose (Local Testing)

```yaml
version: "3.8"
services:
  kubecost:
    image: gcr.io/kubecost1/cost-model:latest
    ports:
      - "9090:9090"
    environment:
      - PROMETHEUS_SERVER_ENDPOINT=http://prometheus:9090
      - THANOS_ENABLED=false
    depends_on:
      - prometheus

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9091:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus

volumes:
  prometheus-data:
```

### Installation

```bash
# Install via Helm (open-source)
helm repo add kubecost https://kubecost.github.io/cost-analyzer/
helm install kubecost kubecost/cost-analyzer   --namespace kubecost --create-namespace   --set prometheus.server.persistentVolume.enabled=false
```

### Usage

```bash
# Access the dashboard
kubectl port-forward --namespace kubecost svc/kubecost-cost-analyzer 9090

# Query cost API
curl -s 'http://localhost:9090/model/costDataModel' | jq .

# Get cluster efficiency
curl -s 'http://localhost:9090/model/clusterInfo' | jq .
```

## Comparison: When to Use Each Tool

### Choose OpenCost if:
- You want a CNCF-standardized, vendor-neutral cost allocation API
- You prefer open-source with no licensing restrictions
- You already use Prometheus and want seamless integration
- You need cost allocation across multiple cloud providers
- Your organization values open governance (CNCF project)

### Choose Goldilocks if:
- Your primary goal is resource right-sizing
- You want VPA-based recommendations without cost modeling complexity
- You need a simple, focused tool that does one thing well
- You are starting your Kubernetes optimization journey
- Your team values minimal operational overhead

### Choose Kubecost if:
- You need a comprehensive cost management platform
- You want budget alerts and spending forecasts
- You need enterprise features like multi-cluster aggregation
- You require custom pricing for on-prem infrastructure
- Your organization needs showback/chargeback capabilities

## Why Self-Host Your Kubernetes Cost Management?

Running cost management tools within your own Kubernetes cluster ensures that sensitive resource and pricing data stays under your control. Unlike cloud-native cost management services (AWS Cost Explorer, GCP Billing), self-hosted tools work across any infrastructure — public cloud, on-premises, or hybrid environments.

For teams operating across multiple cloud providers, self-hosted cost management provides a unified view of spending that cloud vendor tools cannot offer. When combined with GitOps workflows and automated CI/CD pipelines, these tools support continuous cost optimization as part of your deployment process.

For Kubernetes resource management and autoscaling, see our [HPA custom metrics guide](../2026-05-15-kubernetes-hpa-custom-metrics-prometheus-adapter-external-metrics-guide/). If you need cluster-wide observability, our [K8s monitoring operators guide](../2026-04-30-k8s-monitoring-operators-kube-prometheus-victoria-grafana/) covers comprehensive monitoring stacks. For resource optimization at the pod level, check our [descheduler vs VPA comparison](../2026-05-07-descheduler-vs-vpa-vs-goldilocks-kubernetes-resources/).

## FAQ

### What is the difference between OpenCost and Kubecost?

OpenCost is the open-source core of Kubecost, donated to the CNCF as a sandbox project. It provides standardized cost allocation via a vendor-neutral API. Kubecost builds on OpenCost with additional features like budget alerts, advanced reporting, multi-cluster support, and enterprise integrations. If you need basic cost allocation, OpenCost is sufficient. For advanced features, Kubecost's commercial offering provides more capabilities.

### How accurate are Kubernetes cost estimates?

Cost accuracy depends on the pricing data source. OpenCost and Kubecost use cloud provider pricing APIs (AWS, GCP, Azure) for cloud deployments, which provides accurate on-demand pricing. For on-premises clusters, you can configure custom pricing based on your actual infrastructure costs. The accuracy of resource usage data depends on the metrics collection interval — Prometheus scrapes every 15-60 seconds by default.

### Can Goldilocks automatically apply recommendations?

Goldilocks uses VPA recommendations but operates in "Off" mode by default, meaning it only shows recommendations without making changes. You can configure VPA to operate in "Auto" mode to automatically apply recommendations, but this should be done carefully as it may cause pod restarts when adjusting resource requests.

### Do these tools work with spot/preemptible instances?

OpenCost and Kubecost support spot instance pricing through their cloud provider integrations. They can track the actual cost of spot instances versus on-demand pricing, helping you understand savings from spot usage. Goldilocks does not consider instance pricing — it focuses purely on resource usage patterns.

### How much overhead do these tools add to my cluster?

OpenCost and Kubecost require Prometheus to be running in your cluster. If you already have Prometheus, the additional overhead is minimal (approximately 100-200MB of memory for the cost model). Goldilocks requires the VPA recommender, which adds approximately 50-100MB of memory. All tools use the Kubernetes API server for resource data but do not add significant API server load.

### Can I use these tools with on-premises Kubernetes clusters?

Yes. OpenCost supports custom pricing configurations for on-premises infrastructure. Goldilocks works with any Kubernetes cluster regardless of infrastructure since it only analyzes resource usage patterns. Kubecost also supports on-prem pricing through custom rate configuration.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Kubernetes Cost Management: OpenCost vs Goldilocks vs Kubecost (2026)",
  "description": "Compare three Kubernetes cost management tools for resource allocation, right-sizing recommendations, and FinOps practices in self-hosted clusters.",
  "datePublished": "2026-05-17",
  "dateModified": "2026-05-17",
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
