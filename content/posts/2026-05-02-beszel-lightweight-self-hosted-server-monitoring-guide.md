---
title: "Beszel 2026: Complete Guide to Lightweight Self-Hosted Server Monitoring"
date: 2026-05-02T21:30:00+00:00
tags: ["monitoring", "server-monitoring", "self-hosted", "beszel", "docker", "system-monitoring"]
draft: false
---

Monitoring your servers is essential, but the most popular solutions — Prometheus + Grafana, Zabbix, Nagios — require significant infrastructure and expertise to set up. **Beszel** is a lightweight, self-hosted server monitoring tool that delivers historical metrics, Docker container stats, and alerting in a single, easy-to-deploy package.

With over 21,500 GitHub stars and active development, Beszel has emerged as the go-to choice for homelab enthusiasts, small teams, and anyone who needs server visibility without the overhead of a full monitoring stack.

## What Is Beszel?

Beszel is a self-hosted server monitoring dashboard written in Go. It consists of two components:

- **Beszel Hub** — The central web UI that aggregates metrics from multiple servers
- **Beszel Agent** — A lightweight daemon that runs on each monitored server and reports metrics to the Hub

Key features:

| Feature | Description |
|---------|------------|
| Historical data | Stores CPU, memory, disk, and network metrics with configurable retention |
| Docker stats | Monitors container CPU, memory, network I/O, and disk usage |
| Multi-server | Single dashboard for monitoring dozens of servers |
| Alerts | Configurable alert thresholds with notifications |
| Lightweight | Minimal resource usage — the agent consumes ~10 MB RAM |
| Easy deployment | Single Docker Compose file for both Hub and Agent |
| Real-time dashboard | Web UI with live-updating charts and gauges |
| No external dependencies | No need for Prometheus, Grafana, or a time-series database |

## Beszel vs Other Lightweight Monitoring Tools

How does Beszel compare to other self-hosted monitoring solutions?

| Feature | **Beszel** | **Netdata** | **Glances** | **btop** |
|---------|-----------|-------------|-------------|----------|
| Type | Web dashboard + agent | Web dashboard (per-server) | Terminal dashboard | Terminal dashboard |
| Multi-server | ✅ Centralized hub | ❌ Per-server (needs Netdata Cloud) | ❌ Single server only | ❌ Single server only |
| Historical data | ✅ Built-in SQLite | ✅ Built-in (configurable retention) | ❌ No | ❌ No |
| Docker stats | ✅ Per-container | ✅ Per-container | ❌ Basic | ❌ No |
| Alerting | ✅ Configurable thresholds | ✅ Built-in alert system | ❌ No | ❌ No |
| Web UI | ✅ Yes (responsive) | ✅ Yes (very detailed) | ❌ Terminal only | ❌ Terminal only |
| Resource usage | ~10 MB per agent | ~100-200 MB per node | ~50 MB | ~30 MB |
| Setup complexity | Low (Docker Compose) | Low (one-liner install) | Low (pip install) | Very low (binary) |
| GitHub Stars | ⭐ 21,523 | ⭐ 81,000+ | ⭐ 30,000+ | ⭐ 31,000+ |
| Language | Go | C | Python | Go |
| API | REST API | REST API | REST API | ❌ No |

**When to choose Beszel:** You need a lightweight, centralized dashboard for multiple servers with historical metrics and Docker stats — without the complexity of Prometheus + Grafana.

**When to choose Netdata:** You need per-server deep-dive metrics with hundreds of collectors out of the box and don't need centralized multi-server dashboards (or are willing to pay for Netdata Cloud).

**When to choose Glances/btop:** You only need real-time terminal-based monitoring on individual servers with no web UI or historical data requirements.

## Docker Compose Deployment

### Hub (Central Dashboard)

```yaml
services:
  beszel-hub:
    image: henrygd/beszel:latest
    container_name: beszel-hub
    ports:
      - "8090:8090"
    volumes:
      - beszel-data:/beszel_data
    restart: unless-stopped
    networks:
      - monitoring

volumes:
  beszel-data:

networks:
  monitoring:
    driver: bridge
```

The Hub runs on port `8090` by default. On first launch, you'll create an admin account through the web UI.

### Agent (Per-Server Monitoring)

Deploy the agent on each server you want to monitor:

```yaml
services:
  beszel-agent:
    image: henrygd/beszel-agent:latest
    container_name: beszel-agent
    ports:
      - "45876:45876"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /etc/beszel-agent:/etc/beszel-agent
    environment:
      - PORT=45876
    restart: unless-stopped
    network_mode: host
```

After starting the agent, register it with your Beszel Hub through the web UI. The Hub will provide a registration key that the agent uses to authenticate.

### Hub + Multiple Agents (Full Setup)

For a complete multi-server monitoring setup:

```yaml
# On the monitoring server (Hub)
services:
  beszel-hub:
    image: henrygd/beszel:latest
    container_name: beszel-hub
    ports:
      - "8090:8090"
    volumes:
      - beszel-data:/beszel-data
    restart: unless-stopped

  # Local agent (monitors the Hub server itself)
  beszel-agent:
    image: henrygd/beszel-agent:latest
    container_name: beszel-agent
    ports:
      - "45876:45876"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /etc/beszel-agent:/etc/beszel-agent
    environment:
      - PORT=45876
    restart: unless-stopped
    network_mode: host

volumes:
  beszel-data:
```

## Reverse Proxy with Caddy

Put the Beszel Hub behind a reverse proxy for TLS termination:

```caddyfile
monitoring.example.com {
    reverse_proxy beszel-hub:8090

    encode gzip
    log {
        output file /var/log/caddy/beszel.log
    }
}
```

## Nginx Configuration

```nginx
server {
    listen 80;
    server_name monitoring.example.com;

    location / {
        proxy_pass http://localhost:8090;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support for real-time updates
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## Understanding the Dashboard

Once configured, the Beszel dashboard provides:

### System Overview

The main view shows all registered servers with real-time gauges for:

- **CPU usage** — percentage with 1-minute, 5-minute, and 15-minute load averages
- **Memory usage** — total, used, available, and cached memory
- **Disk usage** — per-mount-point utilization with read/write throughput
- **Network I/O** — upload and download bandwidth per interface
- **System uptime** — how long each server has been running

### Historical Charts

Click on any server to view historical charts with configurable time ranges:

- CPU usage over the last hour, day, or week
- Memory utilization trends
- Disk I/O throughput over time
- Network traffic patterns

### Docker Container Stats

For servers running Docker, Beszel shows per-container metrics:

- Container CPU and memory usage
- Network I/O per container
- Container health status
- Resource usage ranking (top consumers)

### Alert Configuration

Beszel supports threshold-based alerts:

- CPU usage exceeds a percentage for a sustained period
- Memory usage crosses a defined limit
- Disk space falls below a threshold
- Network bandwidth spikes above normal
- Docker container crashes or restarts unexpectedly

## Why Self-Host Your Server Monitoring?

Monitoring is the foundation of reliable infrastructure. When you self-host your monitoring stack, you control exactly what data is collected, where it's stored, and who can access it.

**Complete visibility** without data leaving your network. Commercial monitoring SaaS products send your server metrics to their cloud, which may violate data residency requirements or expose sensitive infrastructure details. Self-hosted monitoring keeps all telemetry within your control.

**Zero subscription costs**. SaaS monitoring platforms charge per host, per metric, or per user. At 10+ servers, these costs add up quickly. Beszel runs on a single small VPS and monitors unlimited servers at no additional cost.

**Customization and integration**. Self-hosted monitoring lets you integrate with your existing tooling — Slack webhooks, PagerDuty, custom scripts, or internal dashboards. You're not limited to the notification channels and integrations a SaaS vendor chooses to support.

**Reliability during outages**. If your internet connection goes down, SaaS monitoring can't reach your servers to report the outage. A self-hosted monitoring dashboard on your local network continues to function and can alert you via local channels (email, local webhook, or even SMS through a local gateway).

For teams managing homelabs, small server fleets, or edge deployments, a lightweight self-hosted monitoring tool like Beszel provides essential visibility at minimal cost. For more comprehensive monitoring stacks, see our [Prometheus vs HertzBeat vs Netdata comparison](../2026-04-25-hertzbeat-vs-prometheus-vs-netdata-self-hosted-monitoring-guide-2026/) and [infrastructure monitoring guide](../2026-04-25-nagios-vs-icinga-vs-cacti-self-hosted-infrastructure-monitoring-guide-2026/).

## FAQ

### What is Beszel and what does it monitor?

Beszel is a lightweight, self-hosted server monitoring dashboard written in Go. It monitors CPU usage, memory utilization, disk I/O, network traffic, and Docker container stats across multiple servers from a single web-based dashboard. It stores historical data for trend analysis and supports configurable alerting.

### Is Beszel free and open-source?

Yes, Beszel is open-source under the MIT license. The entire codebase is available on GitHub (henrygd/beszel) with over 21,500 stars. There are no paid tiers or feature gates — all functionality is available in the self-hosted version.

### How many servers can Beszel monitor?

Beszel can monitor dozens of servers from a single Hub instance. The resource overhead per agent is minimal (~10 MB RAM, negligible CPU), so the limiting factor is the Hub's ability to process and store incoming metrics. For most use cases (under 50 servers), a small VPS with 2 GB RAM is sufficient.

### Does Beszel replace Prometheus + Grafana?

Not entirely. Beszel is a lightweight alternative for basic server and Docker monitoring with historical data. It does not replace Prometheus's extensive ecosystem of exporters, Grafana's powerful dashboarding capabilities, or advanced features like distributed tracing, log aggregation, or custom PromQL queries. Choose Beszel for simple server visibility; choose Prometheus + Grafana for deep, customizable observability.

### How do I set up alerts in Beszel?

Alerts are configured through the Beszel web UI. Navigate to the server you want to monitor, set threshold values for CPU, memory, disk, or network metrics, and configure the notification channel. Currently, Beszel supports webhooks for notifications, which can integrate with Slack, Discord, or any webhook-receiving service.

### Can Beszel monitor Windows servers?

Beszel's agent is designed for Linux systems. Windows server monitoring is not currently supported. For mixed Linux/Windows environments, consider Netdata or a commercial solution that supports both platforms.

### How much disk space does Beszel use for historical data?

Beszel stores metrics in an embedded SQLite database. Data usage depends on the number of servers, the metrics collected, and the retention period. A typical single-server setup uses about 100-500 MB per month of historical data. You can configure retention policies to automatically prune older data and manage disk usage.

### Does Beszel support custom metrics?

Beszel focuses on system-level metrics (CPU, memory, disk, network, Docker). It does not currently support custom application-level metrics. If you need custom metric collection (application performance, business KPIs, custom counters), consider Prometheus with custom exporters or a dedicated APM tool like [SigNoz](../self-hosted-datadog-alternative-signoz-grafana-hyperdx-2026/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Beszel 2026: Complete Guide to Lightweight Self-Hosted Server Monitoring",
  "description": "Complete guide to Beszel — a lightweight, self-hosted server monitoring dashboard with historical data, Docker stats, and multi-server support.",
  "datePublished": "2026-05-02",
  "dateModified": "2026-05-02",
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
