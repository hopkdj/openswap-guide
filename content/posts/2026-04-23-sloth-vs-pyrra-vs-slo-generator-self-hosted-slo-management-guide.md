---
title: "Sloth vs Pyrra vs SLO Generator: Best Self-Hosted SLO Management Tools 2026"
date: 2026-04-23
tags: ["comparison", "guide", "self-hosted", "monitoring", "sre", "prometheus"]
draft: false
description: "Compare Sloth, Pyrra, and Google SLO Generator for self-hosted SLO management. Installation guides, Docker Compose configs, feature comparison, and FAQ."
---

Service Level Objectives (SLOs) are the cornerstone of modern Site Reliability Engineering. They define the reliability target your service promises to users, translate complex metrics into business-readable goals, and drive engineering decisions through error budget tracking. But implementing SLOs by hand — writing PromQL queries, calculating burn rates, configuring multi-window alerts — is error-prone and scales poorly across teams.

This guide compares the three leading open-source, self-hosted SLO management tools: **Sloth**, **Pyrra**, and **Google SLO Generator**. Each takes a different approach to making SLOs operational, and we'll help you pick the right one for your infrastructure.

For related reading, see our [Prometheus alerting comparison](../prometheus-alertmanager-vs-moira-vs-victoriametrics-vmalert-self-hosted-alerting-2026/) and [comprehensive observability guide](../self-hosted-datadog-alternative-signoz-grafana-hyperdx-2026/).

## Why Self-Hosted SLO Management Matters

Cloud-based SLO platforms like Nobl9 and Honeycomb charge per SLO or per data volume, which becomes expensive at scale. Self-hosted alternatives give you:

- **Full data ownership** — SLO definitions, burn rate data, and error budgets never leave your infrastructure
- **No per-SLO pricing** — run unlimited SLOs without escalating subscription costs
- **Tighter Prometheus integration** — query the same metrics your alerts use, with zero data duplication
- **Custom SLI sources** — feed data from any Prometheus-compatible backend (VictoriaMetrics, Thanos, Mimir)
- **Compliance** — keep reliability data on-premises for regulated industries

## What Is an SLO?

Before comparing tools, let's clarify the terminology:

- **SLI (Service Level Indicator)** — the actual measurement (e.g., request latency p99 < 500ms)
- **SLO (Service Level Objective)** — the target for an SLI over a time window (e.g., 99.9% of requests under 500ms over 30 days)
- **Error Budget** — the remaining allowed failures before violating the SLO (0.1% = 43 minutes per 30 days)
- **Burn Rate** — how fast you're consuming the error budget (2x burn rate means you'll exhaust the budget in 15 days)

Multi-window, multi-burn-rate alerting — popularized by the Google SRE Workbook — fires alerts at different thresholds depending on how quickly the budget is being consumed. A slow burn over 30 days warrants a ticket; a fast burn over 1 hour warrants a page.

## Sloth: Declarative SLO Generator for Prometheus

**GitHub:** [slok/sloth](https://github.com/slok/sloth) · ⭐ 2,465 · Updated: 2026-04-23 · Language: Go

Sloth generates Prometheus recording rules and alerting rules from simple YAML SLO definitions. It uses the multi-window, multi-burn-rate alerting methodology and outputs native Prometheus configuration that you can deploy alongside your monitoring stack.

### How Sloth Works

You write an SLO definition in YAML, Sloth compiles it into PromQL recording rules and alert rules, and you feed the output into Prometheus. The tool can run as a CLI, a Kubernetes controller, or a CI/CD step.

```yaml
# slo-sloth-api.yaml
version: "prometheus/v1"
service: "api-gateway"
labels:
  owner: "platform-team"
  repo: "github.com/org/api-gateway"

slos:
  - name: "availability"
    objective: 99.9
    description: "API requests must return successful responses"
    sli:
      events:
        error_query: |
          sum(rate(http_requests_total{service="api",status=~"5.."}[{{.window}}]))
        total_query: |
          sum(rate(http_requests_total{service="api"}[{{.window}}]))
    alerting:
      name: "ApiAvailabilityAlert"
      labels:
        category: "slo"
      annotations:
        summary: "API availability SLO burn rate is too high"
      page_alert:
        labels:
          severity: "page"
      ticket_alert:
        labels:
          severity: "ticket"
```

Generate Prometheus rules:

```bash
# CLI installation
go install github.com/slok/sloth/cmd/sloth@latest

# Generate rules
sloth generate -i slo-sloth-api.yaml -o slo-rules.yaml

# Validate
sloth check -i slo-sloth-api.yaml
```

### Sloth Docker Setup

Sloth runs as a CLI tool, but you can containerize it for CI/CD pipelines:

```yaml
# docker-compose.yml for Sloth CI
services:
  sloth:
    image: ghcr.io/slok/sloth:v0.15.0
    volumes:
      - ./slos:/slos
      - ./output:/output
    command: ["generate", "-i", "/slos/slo-api.yaml", "-o", "/output/slo-api-rules.yaml"]
    restart: "no"

  prometheus:
    image: prom/prometheus:v3.7.2
    ports:
      - "9090:9090"
    volumes:
      - ./output:/etc/prometheus/sloth-rules:ro
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    command:
      - --config.file=/etc/prometheus/prometheus.yml
      - --web.enable-lifecycle
```

```yaml
# prometheus.yml - include Sloth-generated rules
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "/etc/prometheus/sloth-rules/*.yaml"

scrape_configs:
  - job_name: "api-gateway"
    static_configs:
      - targets: ["api:8080"]
```

### Key Features

| Feature | Details |
|---------|---------|
| Alerting | Multi-window, multi-burn-rate (Google SRE methodology) |
| Output | Native Prometheus recording + alerting rules |
| SLO Types | Ratio-based (good/total), Raw metric |
| Time Windows | Short (5m, 30m) and long (1h, 6h, 1d, 3d, 30d) |
| Kubernetes | Built-in CRD controller for K8s-native SLOs |
| Validation | `sloth check` validates SLO YAML before generation |
| Language | Go |

## Pyrra: Modern SLO UI with Prometheus Integration

**GitHub:** [pyrra-dev/pyrra](https://github.com/pyrra-dev/pyrra) · ⭐ 1,479 · Updated: 2026-04-23 · Language: Go

Pyrra takes a different approach from Sloth: instead of generating static Prometheus rules, it provides a live web UI for managing SLOs, viewing burn rates, and tracking error budgets in real time. It reads SLO definitions from the filesystem (or Kubernetes CRDs) and queries Prometheus directly.

### How Pyrra Works

Pyrra has two main components: a **filesystem** backend that watches SLO YAML files and a **web API/UI** that provides dashboards, burn rate graphs, and error budget status. It integrates with Grafana for richer visualization.

Define your SLO in OpenSLO-compatible YAML:

```yaml
# api-availability.yaml
apiVersion: pyrra.dev/v1alpha1
kind: ServiceLevelObjective
metadata:
  name: api-availability
  labels:
    team: platform
spec:
  target: "99.9"
  window: 30d
  indicator:
    ratio:
      success:
        metric: http_requests_total{service="api",status=~"2..|3..|4.."}
      total:
        metric: http_requests_total{service="api"}
```

### Pyrra Docker Compose

Pyrra ships with a production-ready Docker Compose setup including Prometheus:

```yaml
# docker-compose.yaml
version: "3"

networks:
  pyrra:

volumes:
  prometheus_pyrra: {}

services:
  prometheus:
    image: prom/prometheus:v3.7.2
    container_name: prometheus
    restart: always
    networks:
      - pyrra
    ports:
      - "9090:9090"
    command:
      - --config.file=/etc/prometheus/prometheus.yml
      - --storage.tsdb.path=/prometheus
      - --storage.tsdb.retention.time=33d
      - --web.enable-lifecycle
    volumes:
      - ./prometheus/prometheus.yaml:/etc/prometheus/prometheus.yml:ro
      - prometheus_pyrra:/etc/prometheus/pyrra

  pyrra-api:
    image: ghcr.io/pyrra-dev/pyrra:v0.9.0
    container_name: pyrra_api
    restart: always
    command:
      - api
      - --prometheus-url=http://prometheus:9090
      - --prometheus-external-url=http://localhost:9090
      - --api-url=http://pyrra-filesystem:9444
    ports:
      - "9099:9099"
    networks:
      - pyrra

  pyrra-filesystem:
    image: ghcr.io/pyrra-dev/pyrra:v0.9.0
    user: root
    container_name: pyrra_filesystem
    restart: always
    command:
      - filesystem
      - --prometheus-url=http://prometheus:9090
    networks:
      - pyrra
    volumes:
      - ./pyrra:/etc/pyrra
      - prometheus_pyrra:/etc/prometheus/pyrra
```

With Grafana integration:

```yaml
  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    restart: always
    networks:
      - pyrra
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
```

Access the Pyrra UI at `http://localhost:9099` to view SLO status, burn rate charts, and error budget consumption across all your services.

### Key Features

| Feature | Details |
|---------|---------|
| UI | Built-in web dashboard with burn rate visualization |
| Backend | Filesystem or Kubernetes CRD |
| SLO Types | Ratio-based, Latency histogram, Bool, Raw |
| Grafana | Optional Grafana external URL for dashboards |
| Multi-Tenancy | Label-based SLO organization |
| API | RESTful API for programmatic SLO management |
| Language | Go |

## Google SLO Generator: Enterprise SLO Framework

**GitHub:** [google/slo-generator](https://github.com/google/slo-generator) · ⭐ 560 · Updated: 2026-04-13 · Language: Python

Google's SLO Generator is a Python framework for computing SLIs, SLOs, error budgets, and burn rates from multiple backend sources (Prometheus, Stackdriver, BigQuery, Datadog, Splunk) and exporting results to various targets (Pub/Sub, BigQuery, Cloud Monitoring, Cloud Storage, Slack).

### How SLO Generator Works

You define SLO configurations in YAML, specifying the backend source and export targets. The framework computes SLIs from raw data, calculates error budgets, and pushes reports to your chosen destination.

```yaml
# slo-config.yaml
service_name: "api-gateway"
slo_name: "api-availability"
slo_target: 0.999
slo_description: "API must be available 99.9% of the time"

backend: "prometheus"
exporters:
  - "prometheus"
  - "cloud_monitoring"

steps:
  - name: "query_prometheus"
    source: "prometheus"
    params:
      prometheus_url: "http://prometheus:9090"
      expr_success: 'sum(rate(http_requests_total{status=~"2..|3..|4.."}[5m]))'
      expr_total: "sum(rate(http_requests_total[5m]))"

  - name: "export_to_prometheus"
    exporter: "prometheus"
    params:
      prometheus_url: "http://prometheus:9090/api/v1/import"
```

Run the generator:

```bash
# Install
pip install slo-generator

# Single run
slo-generator --config slo-config.yaml

# Continuous mode (every 60 seconds)
slo-generator --config slo-config.yaml --continuous --interval 60

# With Slack export
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
slo-generator --config slo-config.yaml --exporters slack
```

### SLO Generator Docker Setup

```yaml
# docker-compose.yml for SLO Generator
services:
  slo-generator:
    image: python:3.11-slim
    container_name: slo_generator
    restart: always
    working_dir: /app
    volumes:
      - ./slo-configs:/app/configs
      - ./reports:/app/reports
    command: >
      bash -c "pip install slo-generator &&
      slo-generator --config /app/configs/slo-config.yaml
      --continuous --interval 300"
    environment:
      - PROMETHEUS_URL=http://prometheus:9090
    depends_on:
      - prometheus

  prometheus:
    image: prom/prometheus:v3.7.2
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
```

### Key Features

| Feature | Details |
|---------|---------|
| Backends | Prometheus, Stackdriver, BigQuery, Datadog, Splunk, Elastic |
| Exporters | Pub/Sub, BigQuery, Cloud Monitoring, Cloud Storage, Slack |
| SLI Types | Ratio, Distribution, Timeseries |
| Scheduling | Continuous mode with configurable intervals |
| Reporting | SLO report with burn rate, error budget, compliance |
| Language | Python |

## Feature Comparison: Sloth vs Pyrra vs SLO Generator

| Feature | Sloth | Pyrra | SLO Generator |
|---------|-------|-------|---------------|
| **Primary Role** | Prometheus rule generator | SLO UI + management | SLO computation framework |
| **UI** | None (CLI only) | Web dashboard | None (CLI only) |
| **Language** | Go | Go | Python |
| **Stars** | 2,465 | 1,479 | 560 |
| **Last Updated** | 2026-04-23 | 2026-04-23 | 2026-04-13 |
| **Kubernetes CRD** | Yes (built-in) | Yes | No |
| **Grafana Integration** | Indirect (via Prometheus) | Native | No |
| **Multiple Backends** | Prometheus only | Prometheus/Thanos/Mimir | 6+ backends |
| **Alert Generation** | Multi-burn-rate PromQL rules | Via Prometheus | Via export targets |
| **Error Budget Tracking** | Via PromQL recording rules | Live dashboard + API | Computed reports |
| **OpenSLO Support** | Partial | Yes | No |
| **Docker Compose** | Manual setup | Official examples | Manual setup |
| **Best For** | Teams wanting native Prometheus integration | Teams wanting a visual SLO dashboard | Teams needing multi-backend SLO reporting |

## When to Choose Each Tool

### Choose Sloth If:
- You want **native Prometheus integration** — Sloth generates recording and alerting rules that live directly in your Prometheus config
- You prefer **GitOps workflows** — SLO definitions live in YAML files, generated rules go through PR review
- You need **Kubernetes-native SLOs** — the Sloth CRD controller manages SLOs as Kubernetes resources
- You want **multi-window multi-burn-rate alerts** out of the box using the Google SRE methodology

### Choose Pyrra If:
- You want a **visual SLO dashboard** — Pyrra provides a live web UI showing burn rates, error budgets, and SLO status
- You need **Grafana integration** — Pyrra can link SLOs to Grafana dashboards
- You want **OpenSLO-compatible definitions** — Pyrra uses the OpenSLO spec for SLO definitions
- You prefer **real-time exploration** over static rule generation

### Choose SLO Generator If:
- You have **multiple data sources** — Prometheus, Stackdriver, BigQuery, Datadog, and more
- You need **report export** to Slack, BigQuery, Cloud Monitoring, or Pub/Sub
- You want a **Python-based framework** that's easy to extend with custom backends and exporters
- You're running **Google Cloud infrastructure** and want tight integration with Stackdriver and BigQuery

## Migration Strategy: From Manual to Automated SLOs

If you're currently managing SLOs by hand-writing PromQL queries, here's a phased approach:

**Phase 1: Audit existing SLOs**
```bash
# List all current alert rules
grep -r "SLO\|error_budget\|burn_rate" /etc/prometheus/rules/
```

**Phase 2: Pick a tool and convert one service**
```yaml
# Convert a manual SLO to Sloth format
# Before (manual PromQL):
# record: slo:api_availability:ratio_rate5m
# expr: sum(rate(http_requests_total{status=~"2..|3..|4.."}[5m])) / sum(rate(http_requests_total[5m]))

# After (Sloth YAML):
# sloth generates this + burn rate alerts automatically
```

**Phase 3: Deploy and verify**
```bash
# Verify Sloth output
sloth check -i slo-api.yaml
sloth generate -i slo-api.yaml -o generated-rules.yaml

# Load into Prometheus and verify in Pyrra UI
curl http://localhost:9090/api/v1/rules | python3 -m json.tool
```

**Phase 4: Scale across all services**
- Create SLO templates in your CI/CD pipeline
- Use Pyrra for executive dashboards
- Export reports via SLO Generator for compliance audits

For teams also evaluating [endpoint monitoring tools](../gatus-vs-blackbox-exporter-vs-smokeping-self-hosted-endpoint-monitoring-2026/) and [Kubernetes cost monitoring](../opencost-vs-goldilocks-vs-crane-kubernetes-cost-monitoring-guide-2026/), combining these with SLO management gives you a complete reliability engineering stack.

## FAQ

### What is the difference between SLI, SLO, and SLA?

An SLI (Service Level Indicator) is the raw measurement — for example, "the p99 latency of our API is 200ms." An SLO (Service Level Objective) is the target you set for that SLI — for example, "99.9% of requests should complete within 500ms." An SLA (Service Level Agreement) is the business contract with penalties if the SLO is breached. In short: SLI measures, SLO targets, SLA enforces.

### Which tool is best for Kubernetes environments?

Sloth is the best choice for Kubernetes. It provides a native CRD controller that manages SLOs as Kubernetes resources, integrates with the Prometheus Operator, and generates alert rules that work seamlessly with Alertmanager. Pyrra also supports Kubernetes CRDs, but Sloth's controller is more mature for K8s-native workflows.

### Can I use multiple SLO tools together?

Yes. A common pattern is to use **Sloth** for generating Prometheus alerting rules, **Pyrra** for the visual dashboard that teams and management view, and **SLO Generator** for periodic compliance reports exported to Slack or BigQuery. They operate at different layers of the SLO lifecycle and complement each other.

### How do I choose the right SLO target percentage?

The Google SRE Workbook recommends starting with common industry benchmarks: 99.9% (43 minutes of downtime per month), 99.95% (22 minutes), or 99.99% (4 minutes). Start conservative — it's easier to tighten an SLO later than to relax one. Monitor your error budget consumption over 30 days before adjusting the target. Tools like Pyrra make it easy to visualize budget consumption before committing to a specific percentage.

### Does SLO Generator work without Google Cloud?

Yes. While originally developed at Google, the SLO Generator supports Prometheus as a primary backend and can export to any HTTP endpoint. The Slack exporter, Pub/Sub alternative (via HTTP), and custom Python exporters work independently of Google Cloud services. You only need Google Cloud if you specifically use BigQuery or Cloud Monitoring exporters.

### How does multi-window multi-burn-rate alerting work?

Instead of a single alert threshold, this method uses multiple time windows with different burn rate multipliers. For a 99.9% SLO (0.1% error budget):

- **Page alert**: 14.4x burn rate over 5 minutes (budget exhausted in ~2 days)
- **Page alert**: 6x burn rate over 30 minutes (budget exhausted in ~5 days)
- **Ticket alert**: 1x burn rate over 6 hours (budget exhausted in ~30 days)
- **Ticket alert**: 0.5x burn rate over 3 days (budget exhausted in ~60 days)

Sloth generates all of these alert rules automatically from a single SLO definition. Pyrra computes burn rates dynamically for its dashboard. SLO Generator calculates burn rates in its continuous mode.

### Can Pyrra work with Thanos or Cortex instead of Prometheus?

Yes. Pyrra supports Thanos and Grafana Mimir as backends since they are Prometheus-compatible. Simply point the `--prometheus-url` flag to your Thanos query frontend or Mimir endpoint. The API surface is identical to Prometheus, so no SLO definition changes are needed.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Sloth vs Pyrra vs SLO Generator: Best Self-Hosted SLO Management Tools 2026",
  "description": "Compare Sloth, Pyrra, and Google SLO Generator for self-hosted SLO management. Installation guides, Docker Compose configs, feature comparison, and FAQ.",
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
