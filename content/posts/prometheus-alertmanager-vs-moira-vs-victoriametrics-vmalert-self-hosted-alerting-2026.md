---
title: "Prometheus Alertmanager vs Moira vs VictoriaMetrics vmalert: Best Self-Hosted Alerting 2026"
date: 2026-04-17
tags: ["comparison", "guide", "self-hosted", "monitoring", "devops", "alerting"]
draft: false
description: "Compare three leading self-hosted alerting systems in 2026: Prometheus Alertmanager, Moira, and VictoriaMetrics vmalert. Complete setup guides, Docker configs, and feature comparison for infrastructure monitoring."
---

Every monitoring stack is only as good as its alerting pipeline. You can collect thousands of metrics, build beautiful dashboards, and track every service — but if nobody gets notified when CPU hits 95% at 3 AM, the whole system is useless.

In 2026, the self-hosted alerting landscape has matured significantly. **[prometheus](https://prometheus.io/) Alertmanager** remains the industry standard, **Moira** offers a compelling alternative for teams coming from Graphite or wanting a unified trigger system, and **VictoriaMetrics vmalert** provides a lightweight, high-performance option within the growing VictoriaMetrics ecosystem.

This guide compares all three tools head-to-head with real configuration examples, [docker](https://www.docker.com/) deployment instructions, and practical advice on which one fits your infrastructure.

For related reading, see our [Prometheus vs Grafana vs VictoriaMetrics monitoring comparison](../prometheus-vs-grafana-vs-victoriametrics/) and [self-hosted incident management with Alerta and OpenDuty](../self-hosted-incident-management-oncall-alerta-openduty-2026/). If you need push notification delivery for your alerts, check our [Gotify vs Ntfy guide](../gotify-vs-ntfy-self-hosted-push-notifications/).

## Why Self-Host Your Alerting System

Relying on a SaaS alerting platform introduces several risks that matter when your monitoring infrastructure needs to be the most reliable thing you run:

**Complete control over alert routing.** You define exactly how alerts are grouped, silenced, deduplicated, and escalated. No vendor lock-in, no API rate limits on notification delivery.

**No data leaves your network.** Alert rules, metric thresholds, and notification payloads never touch a third-party server. This matters for compliance-heavy environments (SOC 2, HIPAA, PCI-DSS) where metric data is considered sensitive.

**Zero recurring costs.** All three tools covered here are open-source and free to run. Your only cost is the compute to host them — often the same server running your metrics backend.

**Custom integrations.** Self-hosted alerting connects to anything: internal Slack workspaces, on-premise PagerDuty alternatives, custom webhook endpoints, email servers, or even SMS gateways you control.

## Prometheus Alertmanager

**GitHub:** [prometheus/alertmanager](https://github.com/prometheus/alertmanager) · **8,424 stars** · **Go** · Last updated: April 2026

Alertmanager is the notification engine of the Prometheus ecosystem. It does not evaluate alert rules itself — Prometheus server handles that and pushes firing alerts to Alertmanager, which then handles deduplication, grouping, routing, and delivery to receivers like Slack, email, PagerDuty, webhooks, and more.

### Key Features

- **Alert grouping** — batch related alerts into a single notification using label matchers
- **Inhibition rules** — suppress lower-priority alerts when a higher-priority one is already firing
- **Silences** — temporarily mute alerts during maintenance windows
- **Multi-receiver routing** — route different alert types to different channels via a tree-based routing config
- **Cluster mode** — run multiple Alertmanager instances for high availability with gossip-based mesh

### Docker Compose Setup

```yaml
services:
  alertmanager:
    image: prom/alertmanager:latest
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
      - alertmanager-data:/alertmanager
    command:
      - "--config.file=/etc/alertmanager/alertmanager.yml"
      - "--storage.path=/alertmanager"
      - "--web.external-url=http://localhost:9093"
    restart: unless-stopped

volumes:
  alertmanager-data:
```

### Configuration Example

The routing configuration is where Alertmanager shines. Here is a production-ready config that routes alerts by team and severity:

```yaml
global:
  smtp_smarthost: 'smtp.example.com:587'
  smtp_from: 'alerts@example.com'
  smtp_auth_username: 'alertmanager'
  smtp_auth_password: '${SMTP_PASSWORD}'

templates:
  - '/etc/alertmanager/templates/*.tmpl'

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'default-receiver'
  routes:
    - matchers:
        - severity="critical"
      receiver: 'pagerduty-critical'
      continue: false

    - matchers:
        - team="infrastructure"
      receiver: 'slack-infra'
      routes:
        - matchers:
            - severity="warning"
          receiver: 'email-infra-warn'

    - matchers:
        - alertname=~"Watchdog|InfoInhibitor"
      receiver: 'null'

inhibit_rules:
  - source_matchers:
      - severity="critical"
    target_matchers:
      - severity="warning"
    equal: ['alertname', 'cluster', 'service']

receivers:
  - name: 'default-receiver'
    webhook_configs:
      - url: 'http://internal-webhook:8080/alerts'

  - name: 'pagerduty-critical'
    pagerduty_configs:
      - service_key: '${PAGERDUTY_KEY}'

  - name: 'slack-infra'
    slack_configs:
      - channel: '#infra-alerts'
        send_resolved: true
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'

  - name: 'email-infra-warn'
    email_configs:
      - to: 'infra-team@example.com'

  - name: 'null'
```

### Strengths and Weaknesses

**Strengths:**
- Mature ecosystem with extensive documentation and community support
- Powerful routing tree with regex matchers and continue logic
- Built-in deduplication and inhibition rules reduce alert fatigue
- Native Prometheus integration with service discovery

**Weaknesses:**
- Requires Prometheus server to evaluate rules (not standalone)
- No built-in UI for managing alert rules — rules live in Prometheus config
- Com[plex](https://www.plex.tv/) YAML routing config has a steep learning curve
- Limited to Prometheus metric format

## Moira

**GitHub:** [moira-alert/moira](https://github.com/moira-alert/moira) · **317 stars** · **Go** · Last updated: April 2026

Moira is a realtime alerting system originally built for Graphite but now supporting Prometheus, VictoriaMetrics, and other data sources through its flexible trigger system. Unlike Alertmanager, Moira evaluates alert rules itself — it is a self-contained alerting engine, not just a notification router.

### Key Features

- **Multi-source support** — Graphite, Prometheus, VictoriaMetrics, and custom metric sources
- **Trigger evaluation** — Moira runs its own rule engine, no separate metrics server needed for alert evaluation
- **Rich notification channels** — Slack, Telegram, MS Teams, Pushover, email, webhooks, and self-hosted options
- **Scheduling** — set alert windows (e.g., only alert during business hours for non-critical items)
- **Tag-based subscription model** — users subscribe to alert tags rather than being assigned by routing rules
- **Built-in web UI** — manage triggers, contacts, and subscriptions through a browser interface

### Docker Compose Setup

Moira is a multi-service architecture. Here is a simplified deployment with pre-built images:

```yaml
services:
  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    ports:
      - "6379:6379"
    restart: unless-stopped

  filter:
    image: moira/filter:latest
    depends_on:
      - redis
    volumes:
      - ./config/filter.yml:/etc/moira/filter.yml:ro
    ports:
      - "8094:8094"
    restart: unless-stopped

  checker:
    image: moira/checker:latest
    depends_on:
      - redis
      - filter
    volumes:
      - ./config/checker.yml:/etc/moira/checker.yml:ro
    ports:
      - "8092:8092"
    restart: unless-stopped

  notifier:
    image: moira/notifier:latest
    depends_on:
      - redis
      - checker
    volumes:
      - ./config/notifier.yml:/etc/moira/notifier.yml:ro
    ports:
      - "8093:8093"
    restart: unless-stopped

  api:
    image: moira/api:latest
    depends_on:
      - redis
      - checker
    volumes:
      - ./config/api.yml:/etc/moira/api.yml:ro
    ports:
      - "8091:8091"
    restart: unless-stopped

  web:
    image: moira/web2:latest
    ports:
      - "8080:80"
    restart: unless-stopped

volumes:
  redis-data:
```

### Minimal Filter Configuration

```yaml
filter:
  redis:
    host: redis
    port: 6379
  metrics:
    retention: 48h
  listen: "0.0.0.0:8094"
  graphite:
    host: graphite.example.com
    port: 2003
    prefix: "moira.filter"
```

### Strengths and Weaknesses

**Strengths:**
- Self-contained — evaluates rules and sends notifications without a separate metrics server
- Tag-based subscription model gives teams control over what they receive
- Web UI for managing triggers and contacts (Alertmanager has no UI)
- Supports multiple data sources, not tied to a single metrics backend
- Business hours scheduling built in

**Weaknesses:**
- Smaller community and less documentation than Alertmanager
- Multi-service architecture is more complex to deploy and maintain
- Requires Redis as a dependency
- Less mature inhibition and deduplication logic compared to Alertmanager
- Smaller ecosystem of integrations and third-party tools

## VictoriaMetrics vmalert

**GitHub:** [VictoriaMetrics/VictoriaMetrics](https://github.com/VictoriaMetrics/VictoriaMetrics) · **16,791 stars** · **Go** · Last updated: April 2026

vmalert is VictoriaMetrics' alerting component. It reads alert and recording rules in Prometheus-compatible format, evaluates them against VictoriaMetrics (or any Prometheus-compatible datasource), and sends results to Alertmanager or any webhook receiver. It can also work as a standalone alerting tool when paired with a webhook endpoint.

### Key Features

- **Prometheus-compatible rule format** — reuse existing Prometheus alerting rules with zero changes
- **Lightweight single binary** — minimal resource footprint compared to running full Alertmanager
- **Remote write support** — sends evaluated alerts back to VictoriaMetrics for dashboard visualization
- **Template support** — Go templates for dynamic alert labels and annotations
- **Alert deduplication** — groups and deduplicates alerts across multiple vmalert replicas
- **Recording rules** — pre-compute expensive queries and store results as new time series

### Docker Compose Setup

vmalert is typically deployed alongside VictoriaMetrics. Here is a minimal standalone alerting setup:

```yaml
services:
  victoriametrics:
    image: victoriametrics/victoria-metrics:latest
    ports:
      - "8428:8428"
    volumes:
      - vmdata:/storage
    command:
      - "--storageDataPath=/storage"
      - "--httpListenAddr=:8428"
    restart: unless-stopped

  vmalert:
    image: victoriametrics/vmalert:latest
    depends_on:
      - victoriametrics
    ports:
      - "8880:8880"
    volumes:
      - ./rules:/etc/rules:ro
    command:
      - "--datasource.url=http://victoriametrics:8428/"
      - "--remoteRead.url=http://victoriametrics:8428/"
      - "--remoteWrite.url=http://victoriametrics:8428/"
      - "--notifier.url=http://alertmanager:9093/"
      - "--rule=/etc/rules/*.yml"
      - "--external.url=http://grafana:3000/"
    restart: unless-stopped

  alertmanager:
    image: prom/alertmanager:latest
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
    restart: unless-stopped

volumes:
  vmdata:
```

### Alert Rule Example

vmalert uses the same rule format as Prometheus, making migration straightforward:

```yaml
groups:
  - name: infrastructure
    interval: 30s
    rules:
      - alert: HighCPUUsage
        expr: 100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 85
        for: 10m
        labels:
          severity: warning
          team: infrastructure
        annotations:
          summary: "High CPU usage on {{ $labels.instance }}"
          description: "CPU usage is above 85% for more than 10 minutes on {{ $labels.instance }}. Current value: {{ $value | printf \"%.1f\" }}%."

      - alert: DiskSpaceLow
        expr: (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100 < 15
        for: 5m
        labels:
          severity: critical
          team: infrastructure
        annotations:
          summary: "Low disk space on {{ $labels.instance }}"
          description: "Available disk space is below 15% on {{ $labels.instance }} ({{ $labels.device }}). Currently at {{ $value | printf \"%.1f\" }}%."

      - alert: ServiceDown
        expr: up == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.job }} is down"
          description: "{{ $labels.instance }} of job {{ $labels.job }} has been unreachable for more than 2 minutes."
```

### Strengths and Weaknesses

**Strengths:**
- Prometheus-compatible rules — zero migration cost from Prometheus
- Extremely lightweight — single binary, minimal memory and CPU usage
- Excellent VictoriaMetrics integration with remote write for alert history
- Recording rules for pre-computed metrics improve dashboard performance
- Part of a cohesive ecosystem (vmagent, vmalert, VictoriaMetrics, Grafana)

**Weaknesses:**
- Still requires a notification receiver (Alertmanager or webhook) for delivery
- Newer project — less battle-tested at scale compared to Alertmanager
- Best experience requires adopting the full VictoriaMetrics stack
- Smaller community than Prometheus ecosystem
- Rule evaluation is tied to VictoriaMetrics datasource performance

## Head-to-Head Comparison

| Feature | Alertmanager | Moira | vmalert |
|---------|-------------|-------|---------|
| **Primary language** | Go | Go | Go |
| **GitHub stars** | 8,424 | 317 | 16,791 (monorepo) |
| **Rule evaluation** | No (Prometheus) | Yes (built-in) | Yes (built-in) |
| **Notification delivery** | Yes (native) | Yes (native) | No (via Alertmanager/webhook) |
| **Web UI** | Minimal (silences only) | Full (triggers, contacts, subscriptions) | None |
| **Data sources** | Prometheus only | Graphite, Prometheus, VM | VictoriaMetrics, Prometheus |
| **Deduplication** | Yes (gossip cluster) | Yes (per-trigger) | Yes (per-replica) |
| **Inhibition rules** | Yes | No | No |
| **Business hours scheduling** | No | Yes | No |
| **Recording rules** | No | No | Yes |
| **Deployment complexity** | Low (single binary) | High (6 services) | Low (single binary) |
| **Prometheus rule compatibility** | N/A | No | Yes |
| **Tag-based subscriptions** | No | Yes | No |

## Which One Should You Choose?

**Choose Prometheus Alertmanager if:**
- You already run Prometheus for metrics collection
- You need sophisticated alert routing with inhibition and grouping
- You want the most mature, battle-tested solution with the largest community
- Your team is comfortable with YAML-based configuration

**Choose Moira if:**
- You want a self-contained alerting engine with a web UI
- You have multiple metrics backends (Graphite + Prometheus + others)
- You prefer tag-based subscriptions where teams opt into alerts
- You need business hours scheduling without custom tooling

**Choose VictoriaMetrics vmalert if:**
- You are using (or planning to use) VictoriaMetrics as your metrics store
- You want Prometheus-compatible rules with lower resource usage
- You need recording rules alongside alerting rules
- You value a lightweight single-binary deployment

For most teams already in the Prometheus ecosystem, Alertmanager remains the default choice. For those evaluating alternatives, vmalert offers the smoothest transition path since it accepts the exact same rule format. Moira stands out as the most independent option — it does not require any specific metrics backend and provides the richest user interface out of the box.

## FAQ

### Can I run Alertmanager without Prometheus?
No. Alertmanager is purely a notification router. It does not evaluate alert rules or query metrics. You need Prometheus (or a compatible server like VictoriaMetrics with remote write) to evaluate rules and push firing alerts to Alertmanager. If you want a self-contained alerting engine, Moira or vmalert are better choices.

### Does Moira support Prometheus metrics natively?
Yes. Moira supports Prometheus, VictoriaMetrics, and Graphite as data sources. You configure the metrics source in the filter component, and Moira's checker evaluates triggers against the data. However, Moira does not use Prometheus rule format — triggers are defined through the Moira API or web UI.

### Can vmalert replace Alertmanager entirely?
Not on its own. vmalert evaluates rules and sends results, but it does not handle notification delivery, grouping, inhibition, or silences. In most deployments, vmalert sends alerts to Alertmanager (or a webhook) for actual notification routing. Think of vmalert as the rule evaluator and Alertmanager as the notification dispatcher.

### Which tool is best for small teams?
For small teams, vmalert is the easiest to deploy — a single binary with Prometheus-compatible rules. If you need a web UI and do not want to manage YAML configs, Moira provides a browser interface for managing triggers and contacts. Alertmanager is powerful but requires comfort with YAML routing configurations.

### Can I migrate alerting rules from Prometheus to vmalert?
Yes, vmalert uses the exact same rule file format as Prometheus. Copy your Prometheus alerting rule YAML files to vmalert's `--rule` directory, update the datasource URL, and you are running. No rule conversion needed.

### How do these tools handle alert fatigue?
Alertmanager has the most sophisticated deduplication and inhibition system — it groups related alerts and can suppress lower-priority ones when critical alerts fire. Moira uses per-trigger deduplication and supports NODATA states. vmalert relies on its notifier (usually Alertmanager) for deduplication. All three support configurable evaluation intervals and `for` duration to prevent flapping.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Prometheus Alertmanager vs Moira vs VictoriaMetrics vmalert: Best Self-Hosted Alerting 2026",
  "description": "Compare three leading self-hosted alerting systems in 2026: Prometheus Alertmanager, Moira, and VictoriaMetrics vmalert. Complete setup guides, Docker configs, and feature comparison for infrastructure monitoring.",
  "datePublished": "2026-04-17",
  "dateModified": "2026-04-17",
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
