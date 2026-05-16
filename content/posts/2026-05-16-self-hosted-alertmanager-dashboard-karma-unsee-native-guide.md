---
title: "Self-Hosted Alertmanager Dashboard UIs: Karma vs Unsee vs Native"
date: "2026-05-16"
tags: ["prometheus", "alerting", "monitoring", "dashboard", "observability"]
draft: false
---

Prometheus Alertmanager handles alert deduplication, grouping, routing, and notification — but its built-in web UI is minimal. For teams running production Alertmanager instances, dedicated dashboard UIs provide better alert visibility, silencing management, and historical analysis.

This guide compares three approaches to Alertmanager dashboards: **[Karma](https://github.com/prymitive/karma)**, **[Unsee](https://github.com/cloudflare/unsee)**, and the **native Alertmanager UI**. We cover Docker Compose deployments, configuration patterns, and help you choose the right dashboard for your observability stack.

## The Need for Alertmanager Dashboards

Alertmanager's native UI provides basic alert listing, silencing, and status views. However, production teams often need more:

- **Multi-Alertmanager support**: View alerts from multiple Alertmanager instances or clusters in a single pane
- **Advanced filtering**: Filter by label values, receiver, severity, or time range
- **Silencing management**: Create, edit, and preview silences with regex support
- **Historical alert data**: Track alert trends and recurrence patterns over time
- **Custom grouping**: Group alerts by team, service, or custom label dimensions

| Feature | Karma | Unsee | Native Alertmanager UI |
|---------|-------|-------|----------------------|
| **GitHub Stars** | 2,636 | 705 | 8,473 (Alertmanager itself) |
| **Last Updated** | May 2026 | Apr 2020 | May 2026 |
| **Multi-AM Support** | Yes (multiple clusters) | Limited (single instance) | No (per-instance only) |
| **Filtering** | Label, receiver, regex | Label-based | Basic label match |
| **Silence Preview** | Yes (dry-run before creating) | No | Basic |
| **Custom Grouping** | Yes (multiple views) | No | Fixed by Alertmanager config |
| **Language** | Go + TypeScript | Go | Go (built into Alertmanager) |
| **Docker Image** | `ghcr.io/prymitive/karma` | `cloudflare/unsee` | `prom/alertmanager` |

## Karma — Full-Featured Alertmanager Dashboard

[Karma](https://github.com/prymitive/karma) is the most feature-rich Alertmanager dashboard. It supports multiple Alertmanager instances, advanced filtering, silence previews, and custom grouping views. It is actively maintained and widely adopted in production environments.

### Key Features

- **Multi-cluster support**: Connect to multiple Alertmanager instances or HA pairs simultaneously
- **Silence preview**: Test silence expressions before applying them to avoid accidentally silencing too many alerts
- **Custom annotations**: Add team-specific annotations and color-coding based on label values
- **Grid layout**: Group alerts by any label dimension (service, team, environment)
- **Dark mode**: Built-in dark theme for NOC and on-call engineers

### Docker Compose Deployment

```yaml
services:
  karma:
    image: ghcr.io/prymitive/karma:latest
    container_name: karma
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - ALERTMANAGER_URI=http://alertmanager:9093
      - ALERTMANAGER_NAME=production
      - ALERTMANAGER_TIMEOUT=10s
    volumes:
      - ./karma-config:/etc/karma
    command: ["--config.file", "/etc/karma/karma.conf"]
```

### Configuration

Karma supports YAML configuration with powerful customization:

```yaml
alertmanager:
  interval: 30s
  servers:
    - name: production
      uri: http://alertmanager-prod:9093
      timeout: 10s
      proxy: false
    - name: staging
      uri: http://alertmanager-staging:9093
      timeout: 10s
      proxy: false

annotations:
  default:
    hidden: false
  hidden:
    - summary
  visible:
    - description
    - runbook_url
    - dashboard_url

filters:
  default:
    - "@receiver=slack-critical"
    - "@state=active"

labels:
  color:
    static:
      - job
      - severity
    unique:
      - service
      - team
```

This configuration connects to two Alertmanager instances (production and staging), controls which annotations are visible, sets default filters, and configures label-based color-coding for quick visual triage.

## Unsee — Lightweight Alertmanager Dashboard

[Unsee](https://github.com/cloudflare/unsee) is a minimalist Alertmanager dashboard developed by Cloudflare. It provides a clean, fast interface for viewing and filtering alerts with minimal configuration overhead. While no longer actively maintained, it remains a solid choice for teams that need a simple, single-instance dashboard.

### Key Features

- **Lightweight**: Single binary, minimal resource usage
- **Fast rendering**: Efficient alert list rendering for large alert volumes
- **Label filtering**: Filter alerts by any label key-value pair
- **Silence management**: View and manage silences directly from the UI
- **Simple configuration**: Minimal setup required — just point it at Alertmanager

### Docker Compose Deployment

```yaml
services:
  unsee:
    image: cloudflare/unsee:latest
    container_name: unsee
    restart: unless-stopped
    ports:
      - "8081:8080"
    environment:
      - ALERTMANAGER_URI=http://alertmanager:9093
      - ALERTMANAGER_INTERVAL=30s
      - LOG_LEVEL=info
```

Unsee requires almost no configuration — the `ALERTMANAGER_URI` environment variable is sufficient for basic operation. For multiple instances, you can configure upstream Alertmanager addresses in the environment.

### Limitations

- **Single Alertmanager**: Designed for one Alertmanager instance; no built-in multi-cluster support
- **No silence preview**: Silences are created directly without dry-run testing
- **Limited grouping**: Alerts are grouped by the Alertmanager's own grouping configuration
- **No longer maintained**: Last commit was in 2020; community forks exist but are not official

## Native Alertmanager UI

The **native Alertmanager UI** is built into the Alertmanager binary and accessible at `http://alertmanager:9093`. It requires no additional deployment and provides core functionality out of the box.

### Key Features

- **Zero additional infrastructure**: No separate container or service needed
- **Status view**: Shows Alertmanager configuration, cluster membership, and version
- **Silences**: Create, view, and expire silences
- **Alerts**: View current alerts grouped by Alertmanager's configured grouping rules
- **Receiver testing**: Test notification receivers from the UI

### Access Pattern

The native UI is automatically available with any Alertmanager deployment:

```yaml
services:
  alertmanager:
    image: prom/alertmanager:latest
    container_name: alertmanager
    restart: unless-stopped
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml
      - ./alertmanager-data:/alertmanager
```

Navigate to `http://alertmanager-host:9093` to access the UI. No additional configuration is needed.

### Limitations

- **Single instance view**: Each Alertmanager shows only its own alerts
- **Basic filtering**: Only label-matching filters are supported
- **No historical data**: Shows only current alert state
- **No custom grouping**: Grouping is determined by Alertmanager's `group_by` configuration

## Comparison: Feature Depth vs Simplicity

| Aspect | Karma | Unsee | Native UI |
|--------|-------|-------|-----------|
| **Setup Complexity** | Medium (YAML config) | Low (env vars) | None (built-in) |
| **Resource Usage** | ~100 MB RAM | ~30 MB RAM | Included in AM |
| **Multi-AM Clusters** | Unlimited | 1 (workarounds exist) | 1 per instance |
| **Silence Management** | Full with preview | Basic | Basic |
| **Alert History** | Via annotations | No | No |
| **Active Development** | Yes (regular releases) | No (archived) | Yes (Alertmanager releases) |
| **Best For** | Production NOC teams | Simple single-AM setups | Quick troubleshooting |

## Building a Complete Observability Stack

Alertmanager dashboards are one component of a broader observability platform. For a complete monitoring stack, pair your Alertmanager dashboard with:

- **Prometheus** for metric collection and alerting rule evaluation
- **Grafana** for metric visualization and dashboarding
- **Log aggregation** ([Vector + Fluent Bit + Loki](../2026-05-07-self-hosted-log-sampling-vector-fluentbit-loki-guide/)) for log-based alerting
- **Distributed tracing** for request-level observability ([Grafana Tempo vs Jaeger vs Zipkin](../2026-05-07-self-hosted-distributed-tracing-backends-grafana-tempo-jaeger-zipkin-guide/))

For teams managing multiple Prometheus instances, consider the [Prometheus long-term storage options](../victoriametrics-vs-thanos-vs-cortex-self-hosted-metrics-storage-guide-2026/) to retain alert history beyond Alertmanager's in-memory state.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Alertmanager Dashboard UIs: Karma vs Unsee vs Native",
  "description": "Compare Alertmanager dashboard solutions: Karma for multi-cluster alert management, Unsee for lightweight single-instance views, and the native Alertmanager UI.",
  "datePublished": "2026-05-16",
  "dateModified": "2026-05-16",
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

## Why Invest in Alertmanager Dashboards?

As Prometheus deployments grow from single instances to multi-cluster, multi-region architectures, the limitations of the native Alertmanager UI become increasingly apparent. Teams managing 10+ Alertmanager instances quickly discover that jumping between individual UI tabs is unsustainable for on-call engineers who need a unified view.

The business case for dedicated alertmanager dashboards goes beyond convenience. When an incident occurs at 3 AM, the difference between a 30-second and 5-minute triage window can be the difference between a minor alert and a full-scale outage. Dashboards like Karma enable on-call engineers to:

- **See cross-cluster patterns**: A latency alert in production might correlate with a deployment event in staging. Multi-cluster views make these correlations visible immediately.
- **Test silences safely**: Creating a silence that accidentally suppresses 500 alerts is a common mistake. Karma's silence preview lets you verify the impact before committing.
- **Customize views per team**: Platform teams can group alerts by infrastructure component, while application teams group by service. Different stakeholders need different perspectives on the same alert data.

For teams already using Grafana for metrics visualization, the question often arises: why not just use Grafana's Alertmanager panel? The answer lies in workflow efficiency. Grafana's Alertmanager integration is read-only — you cannot create silences, test expressions, or manage receivers from within Grafana. Karma and similar tools provide the full management interface that on-call engineers need.

When evaluating dashboard solutions, consider the total cost of ownership. Karma's multi-cluster support eliminates the need to deploy and maintain separate dashboard instances per Alertmanager. Unsee's simplicity means near-zero operational overhead but at the cost of features. The native UI requires zero additional infrastructure but scales poorly beyond single-instance deployments.


## FAQ

### Do I need a separate dashboard if I already have Grafana?

Grafana can display Alertmanager alerts via the Alertmanager data source, but it lacks the interactive silence management, silence preview, and real-time alert filtering that Karma provides. Grafana is better suited for metric visualization, while Karma is purpose-built for alert management. Many teams use both.

### Can Karma connect to Alertmanager clusters with authentication?

Yes. Karma supports basic authentication, bearer tokens, and TLS client certificates for connecting to secured Alertmanager instances. Configure the `tls` and `auth` sections in `karma.conf`:

```yaml
alertmanager:
  servers:
    - name: secure-am
      uri: https://alertmanager:9093
      tls:
        ca: /etc/karma/ca.pem
        cert: /etc/karma/client.pem
        key: /etc/karma/client-key.pem
```

### Why is Unsee no longer maintained?

Cloudflare shifted its internal alerting tooling and stopped maintaining Unsee as an open-source project in 2020. The project is archived but still functional for basic Alertmanager dashboard needs. Karma is the recommended actively-maintained alternative.

### How does Karma handle Alertmanager high availability?

When you point Karma at an Alertmanager HA pair (two instances sharing the same cluster), it automatically detects the cluster and deduplicates alerts. You only need to configure one of the HA pair's addresses — Karma will discover the other peers through Alertmanager's cluster gossip protocol.

### Can I run Karma behind a reverse proxy?

Yes. Karma supports the `--listen.prefix` flag for URL path prefixing:

```bash
command: ["--listen.address", ":8080", "--listen.prefix", "/karma"]
```

This allows you to expose Karma at `https://your-domain/karma` through Nginx, Traefik, or Caddy. See our [reverse proxy authentication guide](../oauth2-proxy-vs-pomerium-vs-traefik-forward-auth-2026/) for adding authentication in front of Karma.

### What is the recommended refresh interval for Karma?

The default 30-second refresh interval balances freshness with API load. For high-volume alerting environments (1,000+ active alerts), increase to 60 seconds to reduce load on Alertmanager. For critical production NOCs, reduce to 10-15 seconds for near-real-time alert visibility.
