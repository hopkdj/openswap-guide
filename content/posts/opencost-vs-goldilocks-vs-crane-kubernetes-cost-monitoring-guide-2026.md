---
title: "OpenCost vs Goldilocks vs Crane: Kubernetes Cost Monitoring Guide 2026"
date: 2026-04-20
tags: ["comparison", "guide", "self-hosted", "kubernetes", "finops", "cost-monitoring"]
draft: false
description: "Compare OpenCost, Goldilocks, and Crane for self-hosted Kubernetes cost monitoring, resource right-sizing, and FinOps. Installation guides and configuration examples included."
---

Kubernetes clusters are notorious for silent budget blowouts. Without proper visibility, teams over-provision CPU and memory, pay for idle pods, and struggle to allocate cloud spend across namespaces and teams. Self-hosted Kubernetes cost monitoring tools solve this by providing real-time cost allocation, resource optimization recommendations, and FinOps-grade reporting — all within your own infrastructure.

In this guide, we compare three leading open-source Kubernetes cost management platforms: **OpenCost** (the CNCF standard), **Goldilocks** (Fairwinds' VPA recommendation engine), and **Crane** (gocrane's FinOps platform). Each takes a different approach to the same problem: making sure you only pay for what you actually need.

## Why Kubernetes Cost Monitoring Matters

Cloud Kubernetes bills are built on resource requests and limits, not actual usage. A pod requesting 2 cores and 4 GB RAM but averaging 0.2 cores and 200 MB still gets billed for the full allocation. Across dozens or hundreds of microservices, this waste compounds dramatically.

Industry studies consistently show that organizations over-provision Kubernetes resources by 40-60%. The financial impact scales with cluster size: a modest 50-node EKS cluster can waste $3,000-8,000 per month purely on over-provisioned requests.

Self-hosted cost monitoring tools address this gap by:

- **Tracking actual vs. requested resource usage** at the pod, namespace, and deployment level
- **Calculating real-time costs** based on cloud pricing APIs or custom rate cards
- **Recommending right-sized resource requests** using historical utilization data
- **Identifying idle resources** like orphaned PVCs, unattached load balancers, and zombie deployments
- **Allocating costs to teams** via Kubernetes labels and namespace tagging

For teams running Kubernetes in production, cost visibility is not optional — it's a prerequisite for sustainable operations.

## OpenCost: The CNCF Standard for Kubernetes Cost Monitoring

![OpenCost](https://github.com/opencost/opencost/raw/develop/logo.png)

**OpenCost** (https://opencost.io) is a CNCF incubating project that provides real-time cost monitoring for Kubernetes workloads and cloud infrastructure. Originally developed by Kubecost, OpenCost was donated to the CNCF as the open-source standard for cloud cost transparency. It currently has **6,489 stars** on GitHub and was last updated on April 17, 2026.

### Key Features

- **Real-time cost allocation** per pod, deployment, namespace, label, and service
- **Multi-cloud support** for AWS, GCP, Azure, Alibaba Cloud, and Oracle Cloud
- **On-premises pricing** with configurable custom rate cards
- **Asset cost tracking** for nodes, persistent volumes, load balancers, and network egress
- **API and Prometheus metrics** export for integration with Grafana dashboards
- **Kubernetes-native architecture** deployed as a standard set of deployments and services
- **Efficiency metrics** showing request vs. actual utilization ratios

### How OpenCost Calculates Costs

OpenCost works by combining two data sources:

1. **Kubernetes resource metrics** — CPU and memory requests/limits from the Kubernetes API
2. **Cloud pricing data** — Node hourly rates from cloud provider APIs or custom pricing configurations

For each pod, OpenCost calculates:

```
Pod CPU Cost = (Pod CPU Request / Node Total Allocatable CPU) × Node Hourly Cost
Pod Memory Cost = (Pod Memory Request / Node Total Allocatable Memory) × Node Hourly Memory Cost
Total Pod Cost = Pod CPU Cost + Pod Memory Cost
```

This approach gives you cost visibility at every level of the Kubernetes hierarchy without requiring changes to your workloads.

### Installation

OpenCost is installed via Helm:

```bash
# Add the OpenCost Helm repository
helm repo add opencost https://opencost.github.io/opencost-helm-chart
helm repo update

# Install OpenCost with default settings
helm install opencost opencost/opencost \
  --namespace opencost \
  --create-namespace \
  --set prometheus.enabled=true
```

For cloud provider integration, configure your cloud-specific provider:

```bash
# AWS integration example
helm install opencost opencost/opencost \
  --namespace opencost \
  --create-namespace \
  --set prometheus.enabled=true \
  --set opencost.cloudProviderName=aws
```

After installation, port-forward to access the UI:

```bash
kubectl port-forward --namespace opencost service/opencost 9090:9090
# Access at http://localhost:9090
```

### Configuration

OpenCost uses a ConfigMap for pricing configuration. Here's a sample for custom on-premises pricing:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: opencost-custom-pricing
  namespace: opencost
data:
  default.json: |
    {
      "CPU": "0.031611",
      "spotCPU": "0.006655",
      "RAM": "0.004237",
      "spotRAM": "0.000892",
      "GPU": "0.95",
      "storage": "0.00005479452",
      "zoneNetworkEgress": "0.01",
      "regionNetworkEgress": "0.01",
      "internetNetworkEgress": "0.12",
      "currency": "USD"
    }
```

Apply the custom pricing ConfigMap and configure OpenCost to use it:

```bash
kubectl apply -f custom-pricing.yaml

helm upgrade opencost opencost/opencost \
  --namespace opencost \
  --set opencost.customPricing.enabled=true \
  --set opencost.customPricing.configMapName=opencost-custom-pricing
```

## Goldilocks: Get Your Resource Requests "Just Right"

![Goldilocks](https://github.com/FairwindsOps/goldilocks/raw/master/docs/img/goldilocks.png)

**Goldilocks** (https://github.com/FairwindsOps/goldilocks) by Fairwinds is a Kubernetes tool that analyzes historical resource usage and recommends optimal CPU and memory requests. With **3,203 stars** on GitHub (updated April 15, 2026), Goldilocks focuses specifically on the resource right-sizing problem rather than financial cost allocation.

### Key Features

- **VPA-based recommendations** — leverages the Kubernetes VerticalPodAutoscaler to analyze usage patterns
- **Web dashboard** — visual interface showing current requests vs. recommended values
- **Namespace-level control** — enable or disable analysis per namespace
- **Historical usage analysis** — uses Prometheus data to calculate recommendations over configurable time windows
- **Non-intrusive** — does not automatically change resource requests; provides recommendations for manual review
- **Helm installation** — simple deployment with standard Kubernetes manifests

### How Goldilocks Works

Goldilocks operates in two phases:

1. **Analysis mode** — deploys a VPA in "Off" mode for each target workload, collecting historical usage data from Prometheus
2. **Recommendation mode** — reads the VPA's calculated recommendations and displays them in the dashboard

The recommendation algorithm looks at your actual CPU and memory usage over time, calculates appropriate percentiles (default: 90th percentile for CPU, 95th for memory), and suggests requests that balance performance with efficiency.

### Installation

Goldilocks requires Prometheus and the Kubernetes VPA to be installed first:

```bash
# Install VPA (Vertical Pod Autoscaler)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/autoscaler/master/vertical-pod-autoscaler/deploy/vpa-v1-crd-gen.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes/autoscaler/master/vertical-pod-autoscaler/deploy/vpa-rbac.yaml

# Add the Fairwinds Helm repository
helm repo add fairwinds-stable https://charts.fairwinds.com/stable
helm repo update

# Install Goldilocks
helm install goldilocks fairwinds-stable/goldilocks \
  --namespace goldilocks \
  --create-namespace \
  --set dashboard.enabled=true
```

### Configuring Target Namespaces

Label namespaces that you want Goldilocks to analyze:

```bash
kubectl label namespace production goldilocks.fairwinds.com/enabled=true
kubectl label namespace staging goldilocks.fairwinds.com/enabled=true
```

You can also set custom VPA update policies per namespace:

```bash
kubectl label namespace production goldilocks.fairwinds.com/vpa-update-mode=off
```

The `off` mode means Goldilocks only displays recommendations without applying them — ideal for review before making changes.

Access the dashboard:

```bash
kubectl port-forward --namespace goldilocks service/goldilocks-dashboard 8080:80
# Access at http://localhost:8080
```

## Crane: FinOps Platform with Analytics and Autoscaling

![Crane](https://github.com/gocrane/crane/raw/main/docs/images/crane-logo.png)

**Crane** (https://github.com/gocrane/crane) by the gocrane team is a comprehensive FinOps platform for Kubernetes that combines cost analytics with intelligent autoscaling. It has **2,040 stars** on GitHub and is also a CNCF project. While OpenCost focuses on cost visibility and Goldilocks on recommendations, Crane goes further by actively optimizing resource allocation through predictive autoscaling.

### Key Features

- **Analytics dashboard** — cost analysis, resource utilization, and efficiency scoring
- **EHPA (Effective Horizontal Pod Autoscaler)** — predictive autoscaling based on historical metrics and time-series forecasting
- **Recommendation engine** — resource recommendations with cost impact analysis
- **Time-series prediction** — uses algorithms like DST (Dynamic Seasonal Trend) to forecast workload patterns
- **Multi-cluster support** — aggregate cost and resource data across multiple Kubernetes clusters
- **Integration with existing autoscalers** — works alongside HPA and VPA

### How Crane Differs

Crane's distinguishing feature is **predictive autoscaling**. While HPA reacts to current metric values, Crane's EHPA uses historical data and time-series forecasting to proactively scale workloads before demand spikes arrive. This is particularly valuable for:

- **Periodic workloads** with known daily or weekly patterns (e.g., e-commerce traffic peaks)
- **Batch processing jobs** with predictable resource consumption curves
- **Multi-tenant platforms** where tenant activity follows identifiable patterns

### Installation

Crane is deployed via Helm from its GitHub repository:

```bash
# Clone the Crane repository
git clone https://github.com/gocrane/crane.git
cd crane

# Install Crane using Helm
helm install crane ./charts/crane \
  --namespace crane-system \
  --create-namespace

# Verify the installation
kubectl get pods -n crane-system
```

The installation includes:

- **Crane Agent** — collects metrics from each node
- **Crane Dashboard** — web UI for analytics and recommendations
- **EHPA Controller** — manages predictive autoscaling CRDs
- **Recommendation Controller** — generates resource optimization suggestions

### Configuring EHPA (Predictive Autoscaler)

Here's an example EHPA configuration for a web application with daily traffic patterns:

```yaml
apiVersion: autoscaling.crane.io/v1alpha1
kind: EffectiveHorizontalPodAutoscaler
metadata:
  name: web-app-ehpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 60
  prediction:
    predictionWindowMinutes: 60
    predictionAlgorithm:
      algorithmType: dsp
      dsp:
        sampleInterval: "1m"
        historyTimeWindow: "7d"
```

This configuration predicts workload demand 60 minutes ahead using the DSP (Dynamic Seasonal Pattern) algorithm trained on the last 7 days of metric data.

## Comparison Table

| Feature | OpenCost | Goldilocks | Crane |
|---------|----------|------------|-------|
| **Primary Focus** | Cost allocation & visibility | Resource right-sizing | Predictive autoscaling + cost |
| **GitHub Stars** | 6,489 | 3,203 | 2,040 |
| **Last Updated** | April 2026 | April 2026 | December 2024 |
| **Language** | Go | Go | Go |
| **CNCF Project** | Yes (Incubating) | No | Yes |
| **Cost Dashboard** | Yes (web + API) | Yes (web dashboard) | Yes (web dashboard) |
| **Multi-cloud Pricing** | AWS, GCP, Azure, Alibaba, Oracle | N/A (resource only) | AWS, GCP (via integration) |
| **Custom Rate Cards** | Yes | No | Yes |
| **Autoscaling** | No (monitoring only) | No (recommendations only) | Yes (EHPA predictive) |
| **Resource Recommendations** | Indirect (via efficiency metrics) | Yes (VPA-based) | Yes (built-in engine) |
| **Multi-cluster Support** | Yes | Limited | Yes |
| **API Access** | Prometheus metrics + REST API | Dashboard only | REST API + Dashboard |
| **Grafana Integration** | Yes (pre-built dashboards) | No native support | Yes |
| **Installation Method** | Helm | Helm + VPA | Helm |
| **Resource Overhead** | Low (~200 MB RAM) | Low (VPA required) | Medium (additional controllers) |
| **Best For** | FinOps teams needing cost visibility | Teams optimizing resource requests | Teams wanting proactive autoscaling |

## Choosing the Right Tool

### Use OpenCost When

- You need **financial cost transparency** across teams, projects, and environments
- Your organization has adopted or is adopting **FinOps practices**
- You operate across **multiple cloud providers** and need unified cost reporting
- You want to **export cost metrics to Grafana** for custom dashboards
- You need **API access** for integration with billing and chargeback systems

OpenCost is the most mature and widely adopted option, with strong community backing from the CNCF. Its strength is giving finance and engineering teams a shared view of cloud spend at Kubernetes granularity.

### Use Goldilocks When

- Your primary concern is **eliminating resource waste** from over-provisioning
- You want **actionable recommendations** rather than just cost visibility
- You prefer a **review-first approach** (recommendations shown, not auto-applied)
- Your workloads are relatively **stable** without dramatic periodic patterns
- You want the **lightest-weight solution** with minimal infrastructure overhead

Goldilocks is the simplest tool of the three. It does one thing well: tell you whether your resource requests are too high, too low, or just right. The VPA-based approach means recommendations are grounded in actual Kubernetes behavior.

### Use Crane When

- You want **proactive autoscaling** based on predictive analytics
- Your workloads have **predictable patterns** (daily cycles, weekly trends)
- You need **combined cost analytics and optimization** in one platform
- You operate **multiple clusters** and want centralized management
- You want **time-series forecasting** to anticipate scaling needs

Crane is the most ambitious platform, combining cost monitoring with actual resource optimization through predictive autoscaling. The trade-off is higher complexity and infrastructure overhead compared to the other two tools.

## Best Practices for Kubernetes Cost Optimization

Regardless of which tool you choose, these practices will maximize your cost savings:

### 1. Set Resource Requests and Limits on Every Workload

Without requests, Kubernetes schedulers cannot make efficient placement decisions. Without limits, runaway processes can consume entire nodes. Both OpenCost and Goldilocks require proper request/limit configuration to provide meaningful recommendations.

```yaml
resources:
  requests:
    cpu: "250m"
    memory: "256Mi"
  limits:
    cpu: "500m"
    memory: "512Mi"
```

### 2. Use Node Pools with Different Instance Types

Separate workloads by resource profile:

```yaml
# High-memory workloads
tolerations:
  - key: workload-type
    value: memory-intensive
    effect: NoSchedule

# High-CPU workloads
tolerations:
  - key: workload-type
    value: cpu-intensive
    effect: NoSchedule
```

### 3. Implement Namespace-Based Cost Allocation

Tag namespaces with cost center labels for team-level chargeback:

```bash
kubectl label namespace payments cost-center=engineering team=platform
kubectl label namespace frontend cost-center=engineering team=web
```

OpenCost uses these labels to generate per-team cost reports automatically.

### 4. Monitor Idle and Orphaned Resources

Set up alerts for:

- Pods with zero network traffic for 24+ hours
- Persistent volumes not attached to any pod
- Load balancers without healthy endpoints
- Deployments with replicas set to zero

### 5. Right-Size Regularly

Schedule monthly reviews of resource recommendations. Even with autoscaling, base requests and limits should be adjusted quarterly based on actual usage trends.

## Related Reading

If you're building a comprehensive Kubernetes operations toolkit, check out our related guides:

- [Kubernetes cluster management tools](../kubernetes-dashboard-vs-headlamp-vs-k9s-cluster-management-guide/) — comparing dashboards for cluster visibility
- [Kubernetes security hardening](../kube-bench-vs-trivy-vs-kubescape-container-kubernetes-hardening-guide/) — securing your clusters after cost optimization
- [Kubernetes backup orchestration](../velero-vs-stash-vs-volsync-kubernetes-backup-orchestration-guide/) — protecting workloads alongside cost monitoring

## FAQ

### What is the difference between OpenCost and Kubecost?

OpenCost is the open-source core of what was originally Kubecost. Kubecost donated the project to the CNCF as OpenCost, which provides cost monitoring for Kubernetes workloads. Kubecost (the commercial product) builds on top of OpenCost with additional enterprise features like multi-cluster management, forecasting, and premium support. For most self-hosted use cases, OpenCost provides all the functionality you need.

### Can I use multiple cost monitoring tools together?

Yes. OpenCost and Goldilocks serve complementary purposes: OpenCost provides financial cost allocation while Goldilocks provides resource right-sizing recommendations. Many teams run both simultaneously. Crane's feature set overlaps with both, so running Crane alongside either would create redundancy.

### How much overhead does OpenCost add to my cluster?

OpenCost typically consumes around 200 MB of memory and 0.1 CPU cores. The Prometheus instance it ships with (or connects to) is the larger component. For production clusters with Prometheus already deployed, the incremental overhead is minimal — less than 1% of a typical node's resources.

### Does Goldilocks automatically change my resource requests?

No. Goldilocks deploys VPAs in "Off" mode by default, meaning it only collects data and displays recommendations. Your workloads are never automatically modified. You can manually apply the recommendations, or configure the VPA to "Initial" or "Auto" mode for automated updates — but this is a deliberate choice, not Goldilocks' default behavior.

### Which tool works best for on-premises Kubernetes clusters?

OpenCost is the best choice for on-premises clusters because it supports custom rate cards. You can configure your own hardware cost per CPU core and GB of RAM, and OpenCost will calculate costs using those rates. Goldilocks works equally well on-premises since it only analyzes resource usage without needing pricing data. Crane also supports on-premises but requires more configuration for cost calculations.

### How does Crane's predictive autoscaling work?

Crane uses the DSP (Dynamic Seasonal Pattern) algorithm to analyze historical metrics and identify recurring patterns in workload resource consumption. Once it learns your workload's daily or weekly patterns, it can proactively scale pods before traffic spikes arrive — unlike HPA, which only reacts after CPU or memory thresholds are crossed. The prediction window is configurable (typically 30-120 minutes ahead).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "OpenCost vs Goldilocks vs Crane: Kubernetes Cost Monitoring Guide 2026",
  "description": "Compare OpenCost, Goldilocks, and Crane for self-hosted Kubernetes cost monitoring, resource right-sizing, and FinOps. Installation guides and configuration examples included.",
  "datePublished": "2026-04-20",
  "dateModified": "2026-04-20",
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
