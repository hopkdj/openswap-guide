---
title: "Self-Hosted Capacity Planning: Open Simulator vs Cloud Custodian vs K8s Resource Forecasting"
date: "2026-05-14"
tags: ["capacity-planning", "kubernetes", "cloud-infrastructure", "resource-management", "self-hosted"]
draft: false
---

Infrastructure capacity planning is the art and science of ensuring you have enough compute, storage, and network resources to handle current and future workloads without overspending on idle hardware. Under-provisioning leads to performance degradation, service outages, and frustrated users. Over-provisioning wastes budget on servers that sit at 10 percent utilization. Self-hosted capacity planning tools help you strike the right balance by analyzing historical usage, simulating future scenarios, and providing actionable recommendations.

This guide compares three approaches to self-hosted capacity planning: Open Simulator (a Kubernetes cluster simulator from Alibaba), Cloud Custodian (a cloud resource management tool with capacity estimation capabilities), and K8s Resource Forecasting (using Prometheus metrics with custom forecasting scripts). Each serves different use cases from K8s cluster sizing to cloud cost optimization to workload-based capacity prediction.

## The Capacity Planning Problem

Capacity planning answers three fundamental questions:

1. **Current state** -- How much of our infrastructure is being used right now? Which resources are bottlenecks?
2. **Growth trajectory** -- Based on historical trends, when will we run out of capacity?
3. **What-if scenarios** -- If we add 50 percent more users, deploy a new service, or migrate to a different cluster topology, how will our infrastructure handle it?

Without systematic capacity planning, organizations typically discover resource shortages only when services start failing. Proactive capacity planning shifts this from reactive firefighting to planned infrastructure growth.

## Open Simulator: Kubernetes Cluster Simulation

Open Simulator, developed by Alibaba, is an open-source Kubernetes cluster simulator designed for capacity planning. It models the scheduling behavior of a K8s cluster and simulates how workloads would be distributed across nodes under various configurations.

### How It Works

Open Simulator reads your current cluster state (node resources, pod requirements, scheduling constraints) and creates a virtual model. You can then modify the model, add or remove nodes, change pod resource requests, adjust scheduling policies, and simulate how the cluster would behave under the new configuration. The output includes scheduling feasibility reports, resource utilization projections, and bottleneck identification.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  open-simulator:
    image: registry.cn-hangzhou.aliyuncs.com/acs/open-simulator:latest
    container_name: open-simulator
    ports:
      - "8080:8080"
    volumes:
      - ./sim-config:/etc/open-simulator:ro
      - ./sim-data:/var/lib/open-simulator
    restart: unless-stopped
    environment:
      - SIMULATOR_PORT=8080
      - KUBECONFIG=/etc/open-simulator/kubeconfig.yaml

  open-simulator-web:
    image: registry.cn-hangzhou.aliyuncs.com/acs/open-simulator-web:latest
    container_name: open-simulator-web
    ports:
      - "3000:3000"
    environment:
      - SIMULATOR_URL=http://open-simulator:8080
    restart: unless-stopped
    depends_on:
      - open-simulator
```

### Simulation Configuration

```yaml
cluster:
  name: "production-cluster"
  scheduler: "default-scheduler"

nodes:
  - name: "worker-1"
    cpu: "8"
    memory: "32Gi"
    pods_capacity: 110
    labels:
      zone: "us-east-1a"
      instance_type: "m5.2xlarge"
  - name: "worker-2"
    cpu: "8"
    memory: "32Gi"
    pods_capacity: 110
    labels:
      zone: "us-east-1b"
      instance_type: "m5.2xlarge"
  - name: "worker-3"
    cpu: "16"
    memory: "64Gi"
    pods_capacity: 110
    labels:
      zone: "us-east-1c"
      instance_type: "m5.4xlarge"

scenarios:
  - name: "50-percent-growth"
    description: "Simulate 50% increase in pod count"
    pod_multiplier: 1.5
  - name: "node-failure"
    description: "Simulate worker-3 failure"
    remove_nodes: ["worker-3"]
  - name: "downsize"
    description: "Remove worker-2 to save costs"
    remove_nodes: ["worker-2"]
```

### Running Simulations

```bash
# Run all scenarios
open-simulator run --config sim-config/cluster-model.yaml

# Run specific scenario
open-simulator run --config sim-config/cluster-model.yaml --scenario 50-percent-growth

# Generate capacity report
open-simulator report --output html --output-dir ./reports
```

### Key Features

- **Scheduling simulation** -- Models K8s scheduler behavior including affinity/anti-affinity, topology spread constraints, and priority-based preemption
- **Node failure modeling** -- Simulates node outages to verify cluster resilience
- **Cost estimation** -- Estimates the cost impact of scaling decisions
- **Visual reports** -- Generates HTML reports with resource utilization charts

### Pros and Cons

**Pros:**
- Specifically designed for Kubernetes capacity planning
- Models actual K8s scheduling behavior, not just resource totals
- Supports what-if scenarios for cluster growth and failure modes
- Open source under Apache 2.0

**Cons:**
- Development has slowed (last significant commit in 2023)
- Limited documentation beyond basic examples
- Primarily focused on Alibaba Cloud -- requires adaptation for other environments
- No built-in Prometheus integration for historical data

## Cloud Custodian: Policy-Driven Resource Management

Cloud Custodian (by Fugue) is an open-source cloud resource management tool that enforces policies, optimizes costs, and provides capacity insights across multiple cloud providers. While not a dedicated capacity planning tool, its resource analysis and reporting capabilities make it valuable for capacity forecasting.

### How It Works

Cloud Custodian reads cloud provider APIs to inventory resources, evaluate them against policy rules, and generate reports. Its capacity planning capabilities come from resource utilization analysis, idle resource detection, and right-sizing recommendations.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  cloud-custodian:
    image: cloudcustodian/c7n:latest
    container_name: cloud-custodian
    volumes:
      - ./policies:/policies:ro
      - ./output:/output
      - ~/.aws:/root/.aws:ro
    environment:
      - AWS_DEFAULT_REGION=us-east-1
    entrypoint: ["custodian", "run"]
    command: ["--cache-period", "0", "--region", "us-east-1", "/policies/capacity.yaml"]

  cloud-custodian-report:
    image: cloudcustodian/c7n:latest
    container_name: custodian-report
    volumes:
      - ./output:/output
    entrypoint: ["custodian", "report"]
    command: ["--format", "csv", "-p", "all", "/output"]
```

### Capacity Planning Policy (capacity.yaml)

```yaml
policies:
  - name: ec2-utilization-report
    resource: ec2
    description: "Identify underutilized EC2 instances for capacity planning"
    filters:
      - type: value
        key: "State.Name"
        value: running
      - type: metrics
        name: CPUUtilization
        days: 30
        period: 86400
        value: 10
        op: less-than
    actions:
      - type: mark-for-op
        op: terminate
        days: 7

  - name: rds-right-sizing
    resource: rds
    description: "Find RDS instances that can be downsized"
    filters:
      - type: metrics
        name: CPUUtilization
        days: 14
        period: 86400
        value: 20
        op: less-than

  - name: ebs-unused-volumes
    resource: ebs
    description: "Identify unattached EBS volumes consuming storage capacity"
    filters:
      - type: value
        key: "Attachments[0].State"
        value: null
```

### Generating Capacity Reports

```bash
# Run capacity analysis policies
custodian run --cache-period 0 capacity.yaml

# Generate CSV report
custodian report --format csv -p all output/

# Generate JSON for programmatic analysis
custodian report --format json -p ec2-utilization-report output/
```

### Pros and Cons

**Pros:**
- Multi-cloud support (AWS, GCP, Azure, Kubernetes)
- 100+ built-in resource filters and actions
- Integrates with Slack, SNS, SQS, and other notification services
- Active development with large community (11,000+ GitHub stars)
- Can automate capacity optimization (right-size, terminate idle resources)

**Cons:**
- Not a dedicated capacity planning tool -- optimization is a side benefit
- Requires cloud provider API access (not suitable for bare-metal-only environments)
- Policy authoring has a learning curve
- Historical analysis depends on cloud provider metrics retention periods

## K8s Resource Forecasting with Prometheus

For Kubernetes clusters already running Prometheus, custom resource forecasting provides the most accurate capacity planning by analyzing actual historical metrics rather than simulated models.

### Architecture

The flow is straightforward: Prometheus collects metrics from node_exporter and kube-state-metrics, a custom Python script queries the Prometheus API for historical trends, and the script generates a forecast report with capacity exhaustion predictions.

### Prometheus Queries for Capacity Analysis

```promql
# Average CPU utilization over the last 30 days per node
avg_over_time(node_cpu_seconds_total{mode!="idle"}[30d])

# Predict when CPU will hit 80% threshold using linear regression
predict_linear(node_cpu_seconds_total{mode!="idle"}[7d], 30*86400)

# Pod count approaching node limit
kubelet_running_pods / kube_node_status_capacity_pods * 100
```

### Prometheus Alerting Rules for Capacity

```yaml
groups:
  - name: capacity-alerts
    rules:
      - alert: NodeCPUHigh
        expr: avg by(instance) (rate(node_cpu_seconds_total{mode!="idle"}[5m])) * 100 > 80
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Node CPU utilization above 80%"

      - alert: NodeMemoryHigh
        expr: (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100 > 85
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Node memory utilization above 85%"

      - alert: NodeDiskFilling
        expr: (1 - node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100 > 80
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Node disk usage above 80%"

      - alert: PodCountApproachingLimit
        expr: kubelet_running_pods / kube_node_status_capacity_pods * 100 > 80
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "Node approaching pod capacity limit"
```

### Forecasting Script

```python
#!/usr/bin/env python3
# k8s-capacity-forecast.py - Forecast K8s resource capacity using Prometheus data
import requests
from datetime import datetime

PROMETHEUS_URL = "http://localhost:9090"

def query_prometheus(query):
    resp = requests.get(PROMETHEUS_URL + "/api/v1/query", params={"query": query})
    return resp.json()["data"]["result"]

def forecast_cpu_usage():
    query = "sum by(namespace) (rate(container_cpu_usage_seconds_total[5m]))"
    results = query_prometheus(query)
    forecast = []
    for r in results:
        ns = r["metric"].get("namespace", "unknown")
        usage = float(r["value"][1])
        forecast.append({"namespace": ns, "current_cpu": round(usage, 2)})
    return sorted(forecast, key=lambda x: x["current_cpu"], reverse=True)

def generate_report():
    print("=== K8s Capacity Forecast Report ===")
    print(f"Date: {datetime.now().isoformat()}")
    print(f"Forecast horizon: 90 days")
    print()
    cpu_forecast = forecast_cpu_usage()
    print(f"{'Namespace':<30} {'Current CPU':>12}")
    print("-" * 45)
    for entry in cpu_forecast:
        print(f"{entry['namespace']:<30} {entry['current_cpu']:>11.2f}")

if __name__ == "__main__":
    generate_report()
```

### Pros and Cons

**Pros:**
- Uses real historical metrics -- most accurate forecasting method
- Customizable forecasting models (linear, exponential, seasonal)
- Integrates with existing Prometheus/Grafana stack
- Real-time alerting when capacity thresholds are approached
- No additional software beyond Prometheus and Python

**Cons:**
- Requires Prometheus to be already deployed and collecting metrics
- Forecasting accuracy depends on historical data quality and quantity
- Custom scripting needed (no out-of-the-box solution)
- Does not model K8s scheduling behavior (unlike Open Simulator)

## Comparison Table

| Feature | Open Simulator | Cloud Custodian | K8s Resource Forecasting |
|---------|---------------|-----------------|--------------------------|
| **Approach** | Cluster simulation | Policy-driven analysis | Historical metrics forecasting |
| **K8s Scheduling Model** | Yes | No | No |
| **Multi-Cloud** | No (Alibaba-focused) | Yes (AWS, GCP, Azure, K8s) | K8s only (with Prometheus) |
| **What-If Scenarios** | Yes | Limited | Limited |
| **Historical Data** | No | Cloud provider metrics | Full Prometheus history |
| **Automation** | Manual simulation | Policy enforcement | Alert-based |
| **Cost Estimation** | Yes | Yes | Manual calculation |
| **Bare-Metal Support** | Limited | No | Yes (via node_exporter) |
| **Active Development** | Slow (2023) | Yes (active) | Custom (your scripts) |
| **GitHub Stars** | 267+ | 11,000+ | N/A (custom) |
| **Best For** | K8s cluster sizing | Multi-cloud optimization | K8s capacity forecasting |

## Why Self-Host Capacity Planning?

Capacity planning tools that run in your infrastructure have several advantages over SaaS alternatives. First, they have direct access to your resource metrics without requiring API keys or data sharing with third parties. Second, they can model your specific infrastructure topology, including private networks, on-premises hardware, and hybrid cloud deployments that SaaS tools cannot see. Third, for regulated industries such as finance, healthcare, and government, keeping capacity data on-premises is often a compliance requirement.

When combined with [infrastructure drift detection](../self-hosted-infrastructure-drift-detection-driftctl-cloud-custodian-opentofu-guide-2026/) tools, capacity planning becomes part of a broader infrastructure governance strategy. Understanding your [Kubernetes batch scheduling](../volcano-vs-yunikorn-vs-kueue-kubernetes-batch-scheduler-guide-2026/) patterns helps predict peak resource demands, while [network bandwidth monitoring](../vnstat-vs-nethogs-vs-iftop-self-hosted-bandwidth-monitoring-guide-2026/) reveals whether network capacity is keeping pace with compute growth.

### Choosing the Right Capacity Planning Approach

For **pure Kubernetes environments**, Open Simulator provides the most accurate capacity predictions because it models the actual K8s scheduler. If you need to understand how a new deployment will affect pod placement across nodes, simulation is the only reliable approach.

For **multi-cloud environments**, Cloud Custodian offers the broadest coverage. Its ability to analyze resources across AWS, GCP, and Azure, plus Kubernetes, makes it the right choice for organizations with hybrid infrastructure.

For **K8s clusters with Prometheus already deployed**, custom resource forecasting provides the most accurate predictions because it uses real historical data rather than simulations or snapshots. The forecasting accuracy improves with more historical data, making this approach increasingly valuable over time.


<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Capacity Planning: Open Simulator vs Cloud Custodian vs K8s Resource Forecasting",
  "description": "Compare three approaches to self-hosted capacity planning for Kubernetes and cloud infrastructure.",
  "datePublished": "2026-05-14",
  "dateModified": "2026-05-14",
  "author": {"@type": "Organization", "name": "OpenSwap Guide"},
  "publisher": {"@type": "Organization", "name": "OpenSwap Guide", "logo": {"@type": "ImageObject", "url": "https://hopkdj.github.io/openswap-guide/logo.png"}}
}
</script>

## FAQ

### What is the difference between capacity planning and capacity management?

Capacity planning is forward-looking -- it predicts future resource needs based on growth trends and planned changes. Capacity management is present-focused -- it monitors current resource utilization and ensures services have enough capacity right now. Capacity planning uses historical data to forecast while capacity management uses real-time metrics to alert.

### How far in advance should I plan capacity?

The planning horizon depends on your procurement cycle. For cloud environments with on-demand scaling, 30 to 90 days is typical. For on-premises infrastructure that requires hardware procurement and deployment, 6 to 12 months is more realistic. Most organizations benefit from maintaining both a short-term 30-day tactical plan and a long-term 12-month strategic plan.

### Can Open Simulator work with non-Alibaba Kubernetes clusters?

Yes. Open Simulator reads Kubernetes cluster state via the standard kubeconfig file and the K8s API. While it was developed by Alibaba and has some Alibaba Cloud-specific features, the core simulation engine works with any standards-compliant Kubernetes cluster.

### How accurate is Prometheus-based capacity forecasting?

Forecasting accuracy depends on the quality and quantity of historical data. With 30 or more days of continuous metrics, linear regression can predict resource exhaustion within 10 to 15 percent accuracy for stable workloads. For seasonal workloads such as e-commerce with holiday spikes, you need at least 12 months of data for accurate seasonal decomposition. Sudden workload changes like new product launches or viral traffic cannot be predicted by any historical method.

### Does Cloud Custodian work with on-premises infrastructure?

No. Cloud Custodian connects to cloud provider APIs (AWS, GCP, Azure) and Kubernetes clusters. It does not support bare-metal servers, VMware, or other on-premises virtualization platforms. For on-premises capacity planning, Open Simulator or Prometheus-based forecasting are better choices.

### How do I set up capacity alerts before resources are exhausted?

Set alerting thresholds at 70 to 80 percent utilization for CPU, memory, and disk, not at 90 percent or higher. The 70 percent threshold gives you time to provision additional resources before hitting critical levels. For Kubernetes pod capacity, alert at 80 percent of node pod limits, as scheduling becomes increasingly difficult as nodes approach their pod capacity ceiling.

### What metrics should I track for capacity planning?

The essential metrics are CPU utilization per node and per namespace, memory utilization, disk I/O and capacity, network bandwidth, pod count per node, and request-to-limit ratios. For database workloads, also track connection count, query latency, and replication lag. For storage, track IOPS, throughput, and latency percentiles such as p95 and p99.
