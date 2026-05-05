---
title: "Self-Hosted Cloud Cost Estimation: Infracost vs OpenCost vs Cloud Custodian"
date: 2026-05-07
tags: ["cloud", "finops", "cost-management", "terraform", "kubernetes", "infrastructure"]
draft: false
---

Managing cloud infrastructure costs is one of the biggest challenges for engineering teams running production workloads. Without proper cost visibility, organizations routinely overspend by 30-40% on unused resources, over-provisioned instances, and inefficient architectures.

This guide compares three leading open-source tools for self-hosted cloud cost management: **Infracost**, **OpenCost**, and **Cloud Custodian**. Each takes a fundamentally different approach — pre-deployment estimation, real-time Kubernetes monitoring, and policy-driven cost optimization — making them complementary rather than mutually exclusive.

## Comparison at a Glance

| Feature | Infracost | OpenCost | Cloud Custodian |
|---------|-----------|----------|-----------------|
| **Primary Focus** | Pre-deployment cost estimation | Real-time K8s cost monitoring | Policy-driven cost optimization |
| **Cloud Providers** | AWS, GCP, Azure, Oracle Cloud | AWS, GCP, Azure | AWS, GCP, Azure, Alibaba Cloud |
| **IaC Support** | Terraform, Terraform Cloud, Terragrunt | Helm, Kubernetes manifests | Cloud Custodian policies (YAML) |
| **Kubernetes** | No | Native (pod/node/namespace) | Via custodian-k8s plugin |
| **CI/CD Integration** | GitHub Actions, GitLab CI, Bitbucket | Prometheus metrics, Grafana | Scheduled Lambda, cron, CI/CD |
| **Cost Allocation** | Per-resource, per-PR | Per-pod, per-namespace, per-team | Per-resource, per-tag |
| **Alerting** | PR comments, Slack, email | Prometheus alerts, Grafana dashboards | Email, SNS, Slack, Lambda |
| **GitHub Stars** | 12,200+ | 6,500+ | 5,900+ |
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| **Deployment** | CLI binary, Docker image | Kubernetes deployment | CLI, Docker, Lambda, EC2 |

## Infracost: Shift FinOps Left to Pull Requests

[Infracost](https://github.com/infracost/infracost) is the most widely adopted open-source cloud cost estimation tool. It integrates directly into your CI/CD pipeline and provides cost estimates for every Terraform pull request — before any infrastructure is provisioned.

### How It Works

Infracost parses your Terraform HCL, maps each resource to pricing data from cloud provider APIs, and generates a cost diff showing the financial impact of proposed changes. The output appears as a comment on your pull request, giving reviewers immediate cost context.

```yaml
# GitHub Actions workflow for Infracost
name: Infracost Cost Estimate
on: [pull_request]

jobs:
  infracost:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Infracost
        uses: infracost/actions/setup@v3
        with:
          api-key: ${{ secrets.INFRACOST_API_KEY }}

      - name: Generate Infracost diff
        run: |
          infracost breakdown --path=. --format=json --out-file=/tmp/infracost.json

      - name: Post Infracost comment
        run: |
          infracost comment --path=/tmp/infracost.json             --repo=$GITHUB_REPOSITORY             --github-token=${{ secrets.GITHUB_TOKEN }}             --pull-request=${{ github.event.pull_request.number }}
```

### Docker-Based Self-Hosted Setup

For self-hosted deployments, Infracost provides a Docker image that can run anywhere:

```yaml
version: '3.8'

services:
  infracost:
    image: infracost/infracost:latest
    volumes:
      - ./terraform:/workspace
    working_dir: /workspace
    environment:
      - INFRACOST_API_KEY=${INFRACOST_API_KEY}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
    command: breakdown --path=.
```

### Key Strengths

- **Pre-deployment visibility**: Catch cost overruns before they happen
- **PR-level granularity**: Every team member sees the cost impact of their changes
- **Multi-cloud support**: Works across AWS, GCP, Azure, and Oracle Cloud
- **Historical tracking**: Maintains a cost history dashboard for trend analysis

### Limitations

- No real-time monitoring — only estimates based on IaC
- Requires Terraform or supported IaC tools
- Custom resources need pricing overrides

## OpenCost: Real-Time Kubernetes Cost Monitoring

[OpenCost](https://github.com/opencost/opencost), originally developed by Kubecost and donated to the CNCF, provides real-time cost monitoring specifically for Kubernetes workloads. It allocates cloud costs down to the pod, namespace, and label level.

### How It Works

OpenCost runs as a Kubernetes deployment, collecting metrics from the Kube API, cloud billing APIs, and Prometheus. It calculates the cost of every workload based on resource requests, usage, and actual cloud pricing — then exposes everything as Prometheus metrics for visualization.

```yaml
# OpenCost Helm deployment
helm install opencost opencost/opencost   --namespace opencost --create-namespace   --set opencost.prometheus.external.url=http://prometheus-server.monitoring

# Access the OpenCost UI
kubectl port-forward --namespace opencost   svc/opencost 9003 9090
```

### Docker Compose for Local Testing

While OpenCost is designed for Kubernetes, you can test it locally:

```yaml
version: '3.8'

services:
  opencost:
    image: opencost/opencost:latest
    ports:
      - "9003:9003"
      - "9090:9090"
    environment:
      - CLOUD_PROVIDER=aws
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - PROMETHEUS_SERVER_ENDPOINT=http://prometheus:9090
    depends_on:
      - prometheus

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
```

### Key Strengths

- **Granular allocation**: Costs broken down by pod, namespace, deployment, and label
- **Real-time monitoring**: Continuous cost tracking, not just estimates
- **CNCF project**: Vendor-neutral, community-driven development
- **Showback/chargeback**: Built-in support for team-level cost allocation

### Limitations

- Kubernetes-only — doesn't monitor VMs, databases, or serverless
- Requires Prometheus for full functionality
- Setup complexity for multi-cluster environments

## Cloud Custodian: Policy-Driven Cost Optimization

[Cloud Custodian](https://github.com/cloud-custodian/cloud-custodian) by Cloud Native Computing Foundation (CNCF) is a rules engine for cloud management. While primarily known for security and compliance, its cost optimization capabilities are powerful and often underutilized.

### How It Works

Cloud Custodian uses YAML policies to define rules for finding and acting on cloud resources. For cost optimization, you can write policies that identify idle resources, enforce tagging for cost allocation, right-size instances, and even automatically shut down non-production resources outside business hours.

```yaml
# Find and stop idle EC2 instances (no CPU utilization in 7 days)
- name: stop-idle-instances
  resource: ec2
  filters:
    - type: metrics
      name: CPUUtilization
      days: 7
      value: 1
      op: less-than
  actions:
    - stop

# Enforce cost allocation tags
- name: require-cost-center-tag
  resource: ec2
  filters:
    - "tag:CostCenter": absent
  actions:
    - type: mark-for-op
      tag: custodian_status
      days: 5
      op: terminate
```

### Docker-Based Deployment

```yaml
version: '3.8'

services:
  custodian:
    image: cloudcustodian/c7n:latest
    volumes:
      - ./policies:/policies
      - ~/.aws:/root/.aws:ro
    working_dir: /policies
    command: run --cache-period 0 -s /output cost-optimization.yml

  custodian-report:
    image: cloudcustodian/c7n:latest
    volumes:
      - ./policies:/policies
      - ~/.aws:/root/.aws:ro
      - ./output:/output
    working_dir: /policies
    command: report --format csv -s /output cost-optimization.yml
```

### Key Strengths

- **Action-oriented**: Not just monitoring — automatically fixes cost issues
- **Broad cloud coverage**: AWS, GCP, Azure, and Kubernetes
- **Security + cost**: Combines cost optimization with security policies
- **Scheduled execution**: Run as cron jobs, Lambda functions, or CI/CD steps

### Limitations

- Steeper learning curve (YAML policy language)
- No real-time cost dashboard — requires external visualization
- Less granular than OpenCost for Kubernetes workloads

## When to Use Each Tool

| Scenario | Recommended Tool |
|----------|-----------------|
| Reviewing Terraform changes in PRs | **Infracost** |
| Monitoring Kubernetes cluster spending | **OpenCost** |
| Automatically shutting down idle resources | **Cloud Custodian** |
| Team-level cost allocation (showback) | **OpenCost** |
| Multi-cloud cost governance | **Cloud Custodian** |
| Pre-deployment budget guardrails | **Infracost** |

For comprehensive FinOps, all three tools complement each other: Infracost prevents cost surprises at deploy time, OpenCost monitors running Kubernetes costs in real-time, and Cloud Custodian enforces cost policies across all cloud resources.

## Why Self-Host Your Cost Management?

Self-hosting cloud cost tools gives you full control over sensitive financial data — cloud spending patterns reveal your architecture, growth trajectory, and business priorities. Third-party cost management SaaS platforms require broad IAM permissions across your cloud accounts, creating a significant attack surface.

With self-hosted tools, billing data never leaves your infrastructure. You control retention periods, access policies, and data integration with internal financial systems. For regulated industries (healthcare, finance, government), this is often a compliance requirement rather than an option.

For infrastructure-as-code cost estimation, see our [Terraform PR automation guide](../2026-04-22-atlantis-vs-digger-vs-terrateam-self-hosted-terraform-pr-automation-2026/). For broader infrastructure cost tracking, check our [infrastructure drift detection guide](../self-hosted-infrastructure-drift-detection-driftctl-cloud-custodian-opentofu-guide-2026/).

## FAQ

### What is the difference between Infracost and OpenCost?

Infracost estimates costs **before** deployment by analyzing Terraform configurations, while OpenCost monitors costs **after** deployment by tracking actual resource usage in Kubernetes clusters. They solve different problems — Infracost prevents cost surprises at PR review time, OpenCost provides real-time visibility into running workloads.

### Can Cloud Custodian replace Infracost or OpenCost?

No. Cloud Custodian focuses on policy enforcement and automated remediation — it finds and fixes cost inefficiencies but doesn't provide pre-deployment estimates (like Infracost) or real-time Kubernetes cost allocation (like OpenCost). The three tools are complementary.

### Does Infracost work without an API key?

Infracost offers a free tier that works without an API key for limited usage (up to 100 resources per month). For CI/CD integration and unlimited usage, you'll need a free API key from infracost.io.

### How accurate are Infracost estimates compared to actual bills?

Infracost estimates are typically within 1-5% of actual cloud bills for standard resources (EC2, S3, RDS, etc.). Usage-based pricing (data transfer, Lambda invocations) cannot be accurately estimated and may show larger variances.

### Can OpenCost monitor non-Kubernetes resources?

OpenCost is Kubernetes-native and cannot directly monitor VMs, databases, or serverless resources. However, it can integrate with cloud billing APIs to show total cloud spend alongside Kubernetes allocation. For non-Kubernetes resources, Cloud Custodian or Infracost are better choices.

### How do I set up automated cost alerts?

With OpenCost: configure Prometheus alerting rules on cost metrics. With Cloud Custodian: write policies that send SNS notifications when resources exceed cost thresholds. With Infracost: use the GitHub integration to comment on PRs that exceed budget limits.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Cloud Cost Estimation: Infracost vs OpenCost vs Cloud Custodian",
  "description": "Compare three open-source tools for self-hosted cloud cost management — Infracost for pre-deployment estimates, OpenCost for Kubernetes cost monitoring, and Cloud Custodian for policy-driven optimization.",
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
