---
title: "Self-Hosted Grafana Dashboard as Code: Grafonnet vs Grizzly vs grafanalib"
date: "2026-06-02"
tags: ["grafana", "infrastructure-as-code", "observability", "dashboards", "self-hosted", "devops", "monitoring"]
draft: false
---

## Introduction

Grafana has become the de facto standard for observability dashboards, but managing dozens or hundreds of dashboards through the web UI quickly becomes unsustainable. Dashboard as Code (DaC) tools allow teams to version, review, and automate their Grafana dashboard configurations just like application code. Three prominent tools have emerged in the Grafana ecosystem: **Grafonnet** (Jsonnet-based), **Grizzly** (Grafana's official management CLI), and **grafanalib** (Python-based, from Weaveworks).

Each approach brings a different philosophy to the table. Grafonnet uses Jsonnet, a data templating language that extends JSON. Grizzly is Grafana's own tool for managing dashboards and other resources as code. grafanalib lets Python developers generate dashboards using familiar Python syntax. This guide compares all three to help you choose the right tool for your self-hosted Grafana environment.

## Tool Comparison

| Feature | Grafonnet | Grizzly | grafanalib |
|---------|-----------|---------|------------|
| **Language** | Jsonnet (JSON superset) | Jsonnet + Go CLI | Python |
| **GitHub Stars** | 1,076 ⭐ | 712 ⭐ | 1,965 ⭐ |
| **Grafana Official** | Yes (grafana/grafonnet-lib) | Yes (grafana/grizzly) | No (weaveworks) |
| **Dashboard Generation** | ✅ | ✅ | ✅ |
| **Alert Rules** | ✅ | ✅ | ❌ (dashboards only) |
| **Folders & Permissions** | ❌ | ✅ | ❌ |
| **CI/CD Integration** | Manual (jsonnet + API) | Built-in (`grizzly apply`) | Manual (Python + API) |
| **Learning Curve** | Medium (Jsonnet) | Low-Medium | Low (Python users) |
| **Last Release** | 2023 (mature/stable) | Active (2025+) | Active |
| **Self-Hosted** | ✅ (library) | ✅ (CLI binary) | ✅ (pip install) |

## Grafonnet: The Jsonnet Standard

Grafonnet is the original Dashboard as Code solution for Grafana, maintained under the `grafana/grafonnet-lib` repository. It provides a comprehensive Jsonnet library that generates Grafana dashboard JSON.

### Installation

```bash
# Install Jsonnet compiler and grafonnet
go install github.com/google/go-jsonnet/cmd/jsonnet@latest
git clone https://github.com/grafana/grafonnet-lib.git
```

### Example: Generating a Dashboard

```jsonnet
local grafana = import 'grafonnet/grafana.libsonnet';
local dashboard = grafana.dashboard;

local prometheus = grafana.prometheus;

dashboard.new('API Metrics Dashboard')
  .addPanel(
    prometheus.graphPanel.new(
      'Request Rate',
      'rate(http_requests_total[5m])',
    )
  )
```

### Key Strengths
- **Mature library**: Well-tested with extensive panel type support
- **Jsonnet ecosystem**: Functions, imports, and composability
- **Grafana-native**: Directly supported by Grafana's documentation

### Limitations
- Jsonnet has a steep initial learning curve
- Only handles dashboards — no support for folders, alerts, or other Grafana resources
- Requires manual API calls or Terraform to deploy generated JSON

## Grizzly: The Official Management CLI

Grizzly (`grafana/grizzly`) is Grafana's newer, more comprehensive approach to infrastructure as code for the entire Grafana stack. It can manage dashboards, alert rules, recording rules, synthetic monitoring checks, and more.

### Installation

```bash
# Download binary
curl -L -o /usr/local/bin/grr \
  https://github.com/grafana/grizzly/releases/latest/download/grr-linux-amd64
chmod +x /usr/local/bin/grr
```

### Configuration

```yaml
# grizzly-config.yaml
apiVersion: grizzly.grafana.com/v1alpha1
kind: GrizzlyConfig
targets:
  grafana:
    url: http://localhost:3000
    token: ${GRAFANA_TOKEN}
```

### Example: Deploying a Dashboard

```bash
# Pull existing dashboards
grr pull dashboards

# Edit dashboard Jsonnet files, then push
grr apply dashboards/my-dashboard.jsonnet
```

### Key Strengths
- **Multi-resource**: Dashboards, rules, folders, datasources, and more
- **Built-in deployment**: `grr apply` pushes directly to Grafana API
- **GitOps-ready**: Designed for CI/CD workflows
- **Active development**: Regular updates from Grafana Labs

### Limitations
- Newer tool with a smaller community than Grafonnet
- Requires Grafana API token with write permissions
- Jsonnet knowledge still required for dashboard definitions

## grafanalib: The Python Alternative

grafanalib (`weaveworks/grafanalib`) takes a different approach — it generates Grafana dashboards using pure Python. For teams already using Python for automation and infrastructure, this is a natural fit.

### Installation

```bash
pip install grafanalib
```

### Example: Python Dashboard Generator

```python
from grafanalib.core import (
    Dashboard, TimeSeries, Target, GridPos,
    OP_AVERAGE, OPS_FORMAT,
)

dashboard = Dashboard(
    title="System Metrics Dashboard",
    panels=[
        TimeSeries(
            title="CPU Usage",
            targets=[
                Target(expr='rate(node_cpu_seconds_total[5m])'),
            ],
            gridPos=GridPos(h=8, w=12, x=0, y=0),
        ),
    ],
)

# Generate JSON and push to Grafana
from grafanalib._gen import DashboardEncoder
import json, requests

dashboard_json = json.dumps(dashboard, cls=DashboardEncoder)
requests.post(
    'http://localhost:3000/api/dashboards/db',
    json={'dashboard': json.loads(dashboard_json)},
    headers={'Authorization': 'Bearer YOUR_TOKEN'},
)
```

### Key Strengths
- **Python-native**: Leverage Python's ecosystem for data transformation and logic
- **Familiar syntax**: Lower barrier to entry for Python developers
- **Programmatic generation**: Loop over services, metrics, or environments to auto-generate panels
- **Mature**: 1,965+ GitHub stars with active maintenance from Weaveworks

### Limitations
- Dashboards only — no support for alert rules or other Grafana resources
- Requires custom deployment scripts or additional tooling
- Generated JSON can be verbose compared to Jsonnet counterparts

## Deployment: Docker Compose for Self-Hosted Grafana

All three tools work with a self-hosted Grafana instance. Here's a complete Docker Compose setup:

```yaml
version: '3.8'
services:
  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=secure_password
    volumes:
      - grafana-storage:/var/lib/grafana
      - ./dashboards:/etc/grafana/provisioning/dashboards
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    restart: unless-stopped

volumes:
  grafana-storage:
```

## GitOps CI/CD Integration

All three tools integrate well with CI/CD pipelines for automated dashboard deployment:

```yaml
# .github/workflows/dashboards.yml
name: Deploy Dashboards
on:
  push:
    paths:
      - 'dashboards/**'
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy with Grizzly
        run: |
          curl -L -o grr https://github.com/grafana/grizzly/releases/latest/download/grr-linux-amd64
          chmod +x grr
          ./grr apply dashboards/
        env:
          GRAFANA_URL: ${{ secrets.GRAFANA_URL }}
          GRAFANA_TOKEN: ${{ secrets.GRAFANA_TOKEN }}
```

## Choosing the Right Tool

- **Choose Grafonnet** if you're already using Jsonnet (e.g., with Tanka or Jsonnet-based Kubernetes configs) and want a mature, battle-tested library for dashboard generation.
- **Choose Grizzly** if you want the official Grafana tool with support for the full Grafana resource model (dashboards, rules, folders, datasources) and built-in deployment capabilities.
- **Choose grafanalib** if your team primarily works in Python and wants to programmatically generate dashboards with complex logic, loops, and data transformations.

For many teams, the best approach is actually a combination: use Grizzly for overall Grafana resource management, and generate dashboard definitions with either Grafonnet or grafanalib depending on your team's language preference.

## Why Self-Host Your Grafana Dashboard as Code Workflow?

Managing Grafana dashboards through the web UI works for small teams with a handful of dashboards, but it creates technical debt at scale. When dashboards are only stored inside Grafana's database, they cannot be versioned, reviewed in pull requests, or rolled back. A misconfiguration can wipe out hours of careful dashboard design with no recovery path.

Dashboard as Code solves these problems by storing dashboard definitions in Git alongside your application code. Your dashboards participate in the same code review process as your services, ensuring configuration changes are intentional and reviewed. When you deploy a new service version, you can automatically deploy its updated dashboard alongside it. If something breaks, `git revert` restores your monitoring view in seconds.

Self-hosting Grafana gives you full control over your monitoring infrastructure. Unlike Grafana Cloud, a self-hosted instance keeps your metrics, dashboards, and alert configurations fully under your ownership. Combined with Dashboard as Code, you get both operational control and development discipline — your monitoring stack evolves as rigorously as your application stack.

For long-term metric storage alongside your dashboards, see our [Grafana Mimir vs Thanos comparison](../2026-04-27-grafana-mimir-vs-thanos-vs-cortex-self-hosted-prometheus-long-term-storage-guide-2026/). If you need to back up your Grafana configuration, check our [Grafana backup and migration guide](../2026-06-01-self-hosted-grafana-backup-migration-tools-guide/).

## FAQ

### Do I need to know Jsonnet to use Dashboard as Code with Grafana?

Not necessarily. If you choose grafanalib, you can work entirely in Python. Grizzly uses Jsonnet for dashboard definitions but handles the deployment for you. Grafonnet requires Jsonnet knowledge. If your team is starting fresh, evaluate which language (Python or Jsonnet) fits your existing skill set.

### Can I mix and match these tools?

Yes, they generate standard Grafana dashboard JSON. You can prototype a dashboard in the Grafana UI, export it as JSON, and later convert it to Grafonnet or grafanalib for version control. Grizzly can deploy dashboards regardless of how they were generated.

### How do I handle dashboard templating across multiple environments?

Grafonnet and grafanalib both support programmatic generation. You can define a base dashboard template and parameterize it for dev, staging, and production environments. For example, with grafanalib you can loop over a list of services and generate panels for each one. With Grafonnet, you can use Jsonnet functions to compose reusable dashboard components.

### What happens if someone edits a dashboard through the Grafana UI after it's been deployed as code?

This is a common challenge. Grizzly supports a "pull" mode (`grr pull`) that downloads current dashboard state from Grafana into local Jsonnet files, so you can compare and reconcile changes. The best practice is to disable direct UI editing for production dashboards via Grafana's role-based access control (RBAC) and treat the Git repository as the source of truth.

### Are these tools compatible with Grafana Cloud?

Yes, all three tools work with both self-hosted Grafana and Grafana Cloud instances. For Grafana Cloud, you'll use a Cloud API key instead of a local admin token. Grizzly has first-class support for Grafana Cloud targets including synthetic monitoring and alerting.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Grafana Dashboard as Code: Grafonnet vs Grizzly vs grafanalib",
  "description": "Comprehensive comparison of three Grafana Dashboard as Code tools: Grafonnet (Jsonnet), Grizzly (Grafana CLI), and grafanalib (Python). Includes deployment guides, CI/CD integration, and Docker Compose setup for self-hosted Grafana.",
  "datePublished": "2026-06-02",
  "dateModified": "2026-06-02",
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
