---
title: "Self-Hosted Network Capacity Planning Tools: Cloud Custodian vs Kube-Capacity vs Open-Simulator"
date: "2026-05-18"
tags: ["capacity-planning", "kubernetes", "cloud-custodian", "network-monitoring", "resource-management"]
draft: false
---

Network and infrastructure capacity planning is critical for maintaining service reliability while controlling costs. Without proper capacity visibility, teams either over-provision (wasting resources) or under-provision (causing outages). Self-hosted capacity planning tools provide real-time resource utilization data, forecasting capabilities, and policy-driven optimization without sending sensitive infrastructure data to third-party SaaS platforms.

In this guide, we compare three open-source capacity planning and resource management tools: **Cloud Custodian**, **Kube-Capacity**, and **Open-Simulator**, each addressing different aspects of capacity planning.

## Comparison Overview

| Feature | Cloud Custodian | Kube-Capacity | Open-Simulator |
|---|---|---|---|
| Stars | 5,985+ | 2,616+ | 267+ |
| Language | Python | Go | Go |
| Last Updated | May 2026 | Nov 2025 | May 2023 |
| Platform | AWS, Azure, GCP, K8s | Kubernetes only | Kubernetes only |
| Capacity Metrics | Cost, resource usage | Requests vs limits | Cluster simulation |
| Policy Engine | YAML rules | None | Configuration-based |
| Forecasting | Cost trends | Real-time utilization | Scenario modeling |
| Alerting | CloudWatch, SNS | CLI output | None |
| Dashboard | c7n-org + Grafana | CLI only | CLI only |
| Best For | Multi-cloud governance | K8s resource visibility | K8s capacity simulation |

## Cloud Custodian

**GitHub:** [cloud-custodian/cloud-custodian](https://github.com/cloud-custodian/cloud-custodian) (5,985+ stars)

Cloud Custodian is a rules engine for cloud security, cost optimization, and governance. While not a traditional capacity planning tool, its policy-driven approach to resource management makes it invaluable for identifying underutilized resources, enforcing right-sizing policies, and controlling cloud spend at scale.

### Key Features

- **Multi-cloud** - AWS, Azure, GCP, and Kubernetes support
- **Policy as Code** - YAML-based policy definitions
- **Cost Optimization** - Identify idle and underutilized resources
- **Auto-Remediation** - Automatically enforce policies (stop, resize, tag)
- **Compliance** - SOC 2, HIPAA, PCI-DSS policy packs
- **Extensible** - Custom filters and actions via Python plugins

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  custodian:
    image: cloudcustodian/c7n:latest
    container_name: cloud-custodian
    volumes:
      - ./policies:/policies:ro
      - ~/.aws:/root/.aws:ro
      - ./output:/output
    environment:
      - AWS_DEFAULT_REGION=us-east-1
    entrypoint: ["custodian", "run", "-s", "/output", "/policies/capacity.yml"]
    restart: "no"
```

### Capacity Planning Policy

```yaml
# capacity.yml - Resource right-sizing policies
policies:
  - name: idle-ec2-instances
    resource: ec2
    filters:
      - type: metrics
        name: CPUUtilization
        days: 14
        period: 86400
        value: 5
        op: less-than
    actions:
      - type: stop

  - name: oversized-rds-instances
    resource: rds
    filters:
      - type: metrics
        name: CPUUtilization
        days: 30
        period: 86400
        value: 20
        op: less-than
    actions:
      - type: resize
        sizing: "downsize"
        restart: true

  - name: orphaned-ebs-volumes
    resource: ebs
    filters:
      - State: available
    actions:
      - type: snapshot
      - type: delete
```

### Running Capacity Reports

```bash
# Run all capacity policies
custodian run -s output/ policies/capacity.yml

# Generate resource report
custodian report -s output/ --format csv policies/capacity.yml

# Dry-run mode (no actions taken)
custodian run -s output/ --dryrun policies/capacity.yml
```

## Kube-Capacity

**GitHub:** [robscott/kube-capacity](https://github.com/robscott/kube-capacity) (2,616+ stars)

Kube-Capacity is a lightweight CLI tool that provides an overview of resource requests, limits, and utilization across a Kubernetes cluster. It helps identify nodes and pods that are over or under-provisioned, making it essential for Kubernetes capacity planning.

### Key Features

- **Node-level view** - See requests and limits per node
- **Pod-level view** - Identify resource-heavy pods
- **Utilization metrics** - Real-time CPU and memory usage
- **Sorting and filtering** - Focus on problematic resources
- **Lightweight** - Single binary, no dependencies
- **Multi-cluster** - Support for multiple kubeconfig contexts

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  kube-capacity:
    image: ghcr.io/robscott/kube-capacity:latest
    container_name: kube-capacity
    volumes:
      - ~/.kube/config:/root/.kube/config:ro
    command: ["--util", "--sort", "cpu.util"]
    restart: "no"
```

### Usage Patterns

```bash
# Overview of all node capacity
kube-capacity --util

# Per-node resource breakdown
kube-capacity --nodes --util

# Sort by CPU utilization
kube-capacity --sort cpu.util

# Show only nodes above 80% utilization
kube-capacity --util --sort cpu.util | grep -v "^[0-7]"

# Export for capacity reporting
kube-capacity --output json > capacity-report.json
```

### Capacity Planning Workflow

```bash
# 1. Check current cluster capacity
kube-capacity --nodes --util

# 2. Identify over-provisioned namespaces
kube-capacity --by namespace --util

# 3. Find pods with no resource requests
kube-capacity --pods | grep "0m / 0m"

# 4. Generate capacity trend data
for i in $(seq 1 7); do
    kube-capacity --output json --util > "day-$i.json"
    sleep 86400
done
```

## Open-Simulator

**GitHub:** [alibaba/open-simulator](https://github.com/alibaba/open-simulator) (267 stars)

Open-Simulator is a Kubernetes cluster simulator for capacity planning, developed by Alibaba. It allows you to simulate cluster changes (node additions, pod scheduling) without affecting production, making it valuable for capacity planning and what-if analysis.

### Key Features

- **Cluster simulation** - Model cluster changes before applying them
- **Scheduling analysis** - Test pod scheduling with different configurations
- **Capacity forecasting** - Predict resource needs based on growth trends
- **Node pool planning** - Optimize node pool sizes and types
- **Cost estimation** - Estimate costs for different cluster configurations
- **Alibaba-proven** - Used internally at Alibaba for large-scale planning

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  open-simulator:
    image: registry.cn-hangzhou.aliyuncs.com/acs/open-simulator:latest
    container_name: open-simulator
    volumes:
      - ./config:/etc/open-simulator:ro
      - ./data:/data
    environment:
      - SIMULATOR_LOG_LEVEL=info
    ports:
      - "8080:8080"
    restart: unless-stopped
```

### Simulation Configuration

```yaml
# simulator-config.yaml
cluster:
  name: "production-cluster"
  nodes:
    - type: "c5.2xlarge"
      count: 10
      cpu: "8"
      memory: "16Gi"
    - type: "m5.4xlarge"
      count: 5
      cpu: "16"
      memory: "64Gi"

workloads:
  - name: "web-frontend"
    replicas: 20
    cpu_request: "500m"
    memory_request: "1Gi"
  - name: "api-backend"
    replicas: 10
    cpu_request: "1000m"
    memory_request: "2Gi"

scenarios:
  - name: "50-percent-growth"
    scale_factor: 1.5
  - name: "new-node-pool"
    add_nodes:
      - type: "c6.4xlarge"
        count: 5
```

## Choosing the Right Capacity Planning Tool

| Use Case | Recommended Tool |
|---|---|
| Multi-cloud cost optimization | Cloud Custodian |
| Kubernetes resource visibility | Kube-Capacity |
| Cluster simulation and planning | Open-Simulator |
| Automated right-sizing | Cloud Custodian |
| Real-time K8s utilization | Kube-Capacity |
| What-if capacity analysis | Open-Simulator |
| Compliance-driven capacity | Cloud Custodian |
| Node pool sizing | Open-Simulator + Kube-Capacity |

## Why Self-Host Capacity Planning?

Infrastructure capacity planning directly impacts service reliability and operational costs. Self-hosted tools keep your resource utilization data, cost metrics, and capacity forecasts within your control, avoiding the need to share sensitive infrastructure details with external platforms.

For organizations running multi-cloud environments, Cloud Custodian provides a unified policy layer across AWS, Azure, GCP, and Kubernetes. Its YAML-based policies can automatically identify idle resources, enforce right-sizing, and generate capacity reports on a scheduled basis.

For Kubernetes-focused teams, Kube-Capacity offers immediate visibility into cluster resource allocation versus actual utilization. The gap between requests and limits is where most capacity planning failures occur, and Kube-Capacity makes this visible at a glance.

For capacity forecasting and scenario planning, Open-Simulator allows you to model cluster growth, test node pool configurations, and predict resource bottlenecks before they impact production workloads. This is particularly valuable for teams planning Kubernetes upgrades or migrations.

For BGP route policy management, see our [FRRouting vs GoBGP guide](../2026-05-18-self-hosted-bgp-route-policy-management-frrouting-gobgp-exabgp-guide/). For network capacity planning, check our [network analysis tools comparison](../2026-04-29-self-hosted-network-analysis-nmap-masscan-zenmap-guide/). If you need infrastructure access management, our [Teleport vs Boundary comparison](../2026-05-04-self-hosted-infrastructure-access-management-teleport-boundary-openziti-guide/) covers secure access patterns.

## FAQ

### What is infrastructure capacity planning and why does it matter?

Infrastructure capacity planning is the practice of monitoring current resource utilization, forecasting future needs, and provisioning accordingly. It matters because under-provisioning causes outages and performance degradation, while over-provisioning wastes money. Proper capacity planning ensures you have the right resources at the right time, balancing reliability and cost efficiency.

### How does Cloud Custodian help with capacity planning?

Cloud Custodian identifies underutilized and orphaned resources across cloud providers. It can automatically stop idle EC2 instances, flag oversized RDS instances, and delete unused EBS volumes. Its policy engine enables automated right-sizing based on actual utilization metrics, turning capacity planning from a manual exercise into an automated governance process.

### Can Kube-Capacity predict future resource needs?

Kube-Capacity itself provides real-time and historical utilization data but does not forecast. For prediction, combine Kube-Capacity with metrics from Prometheus and use Open-Simulator to model future scenarios. The data from Kube-Capacity feeds into the forecasting model, showing current utilization patterns that inform growth projections.

### What is the difference between resource requests and limits in Kubernetes?

Resource requests are the minimum resources guaranteed to a pod, used by the scheduler for placement decisions. Limits are the maximum resources a pod can consume. Capacity planning focuses on the gap between requests and actual utilization: if requests consistently exceed utilization, resources are over-allocated. If utilization approaches limits, the pod may be throttled or evicted.

### How often should I run capacity planning analysis?

For production environments, run capacity analysis weekly with Cloud Custodian policies and daily with Kube-Capacity for Kubernetes clusters. Monthly or quarterly, run Open-Simulator scenarios to model growth and plan node pool changes. Automated policies should run continuously to catch resource anomalies in real-time.

### Can these tools work together?

Yes. Cloud Custodian can enforce policies based on Kube-Capacity findings (e.g., auto-scale down underutilized node pools). Open-Simulator can model the impact of Cloud Custodian right-sizing actions before they are applied. Together, they provide a complete capacity planning pipeline: measure (Kube-Capacity), analyze (Open-Simulator), and act (Cloud Custodian).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Network Capacity Planning Tools: Cloud Custodian vs Kube-Capacity vs Open-Simulator",
  "description": "Compare Cloud Custodian, Kube-Capacity, and Open-Simulator for self-hosted infrastructure capacity planning with Docker deployment guides.",
  "datePublished": "2026-05-18",
  "dateModified": "2026-05-18",
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
