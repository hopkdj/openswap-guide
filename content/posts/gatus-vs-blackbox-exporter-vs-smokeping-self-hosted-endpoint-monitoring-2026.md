---
title: "Gatus vs Blackbox Exporter vs SmokePing: Self-Hosted Endpoint Monitoring 2026"
date: 2026-04-18
tags: ["comparison", "guide", "self-hosted", "monitoring", "devops"]
draft: false
description: "Compare Gatus, Prometheus Blackbox Exporter, and SmokePing for self-hosted endpoint and synthetic monitoring. Complete Docker setup guides, feature comparison, and alerting configuration for 2026."
---

## Why Self-Host Your Endpoint Monitoring?

Commercial monitoring platforms charge per endpoint, restrict check types behind premium tiers, and store all your probe data on third-party servers. Self-hosting your endpoint monitoring stack eliminates these constraints entirely:

- **Zero per-endpoint costs** — monitor hundreds or thousands of targets without paying incremental fees
- **Full data ownership** — all probe results, latency measurements, and uptime history remain on your infrastructure
- **Private network monitoring** — probe internal services, staging environments, and LAN hosts that external monitors cannot reach
- **Unlimited check frequency** — run probes every 10 seconds or every 10 minutes, without throttling
- **Custom alerting pipelines** — route alerts to any channel via webhooks, email, or local notification services

For infrastructure teams running self-hosted services, having an independent health-check layer is essential. This guide compares three mature open-source tools — each with a distinct approach to endpoint monitoring — and provides production-ready deployment configurations. For broader infrastructure monitoring that complements endpoint checks, see our [Zabbix vs LibreNMS vs Netdata comparison](../zabbix-vs-librenms-vs-netdata-network-monitoring-guide/) and our [Uptime Kuma monitoring guide](../uptime-kuma-monitoring-guide/).

## Tool Overview

| Tool | Stars | Language | Last Updated | Best For |
|------|-------|----------|--------------|----------|
| **[Gatus](https://github.com/TwiN/gatus)** | 10,690 | Go | April 2026 | Developer-oriented health dashboards with status pages |
| **[Blackbox Exporter](https://github.com/prometheus/blackbox_exporter)** | 5,645 | Go | April 2026 | Prometheus ecosystem integration and standardized probing |
| **[SmokePing](https://github.com/oetiker/SmokePing)** | 1,868 | Perl | March 2026 | Network latency monitoring with historical trend visualization |

## Gatus: Developer-Oriented Health Dashboard

Gatus is a lightweight, config-as-code health dashboard that supports HTTP, ICMP, TCP, and DNS probes. It evaluates probe results against configurable conditions (status code, response time, certificate expiry, body content) and presents findings on a clean web dashboard with built-in status pages.

### Key Features

- **Multi-protocol probes**: HTTP, HTTPS, TCP, ICMP, DNS, and STARTTLS
- **Rich condition language**: `status == 200`, `responseTime < 500ms`, `certExpiration > 30d`, `body contains "ok"`
- **Built-in status page**: Auto-generated public or private status pages per group
- **Extensive alerting**: Slack, Discord, Teams, PagerDuty, Twilio, Email, Gotify, and custom webhooks
- **Storage backends**: SQLite (default), PostgreSQL, MySQL for persistent history
- **Single binary**: No external dependencies beyond the config file

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  gatus:
    image: ghcr.io/twin/gatus:stable
    container_name: gatus
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./config.yaml:/config/config.yaml:ro
      - gatus-data:/data
    environment:
      - TZ=UTC

volumes:
  gatus-data:
    driver: local
```

### Gatus Configuration Example

Save as `config.yaml` and mount it into the container:

```yaml
storage:
  type: sqlite
  path: /data/gatus.db

web:
  port: 8080

alerting:
  slack:
    webhook-url: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    default-alert:
      type: slack
      send-on-resolved: true
      failure-threshold: 3
      success-threshold: 1

endpoints:
  - name: website
    group: production
    url: "https://example.com"
    interval: 1m
    conditions:
      - "[STATUS] == 200"
      - "[RESPONSE_TIME] < 500"
      - "[CERTIFICATE_EXPIRATION] > 30d"
    alerts:
      - type: slack

  - name: api-health
    group: production
    url: "https://api.example.com/health"
    interval: 30s
    method: GET
    headers:
      Authorization: "Bearer ${API_TOKEN}"
    conditions:
      - "[STATUS] == 200"
      - "[BODY].status == \"healthy\""
      - "[RESPONSE_TIME] < 200"
    alerts:
      - type: slack

  - name: dns-resolver
    group: infrastructure
    dns:
      query-name: "example.com"
      query-type: "A"
    interval: 2m
    conditions:
      - "[DNS_RCODE] == NOERROR"
      - "[RESPONSE_TIME] < 100"
```

Gatus processes the `conditions` field as a simple expression language. Each condition is evaluated against the probe result, and all must pass for the endpoint to be considered healthy.

## Prometheus Blackbox Exporter: Standardized Probe Monitoring

The Blackbox Exporter is Prometheus's official probe exporter. It exposes a single HTTP endpoint that accepts probe targets and returns metrics in Prometheus format. This design means it integrates seamlessly with the existing Prometheus monitoring stack — scrape configs, alerting rules, and Grafana dashboards all work out of the box.

### Key Features

- **Prometheus-native**: Outputs standard Prometheus metrics, scrapable by any Prometheus server
- **Probe types**: HTTP/HTTPS, DNS, TCP, ICMP, gRPC
- **TLS certificate validation**: Configurable CA bundles and certificate expiry tracking
- **Module system**: Reusable probe configurations (e.g., `http_2xx`, `dns_tcp`, `icmp_ipv4`)
- **Multi-target pattern**: Single exporter handles thousands of targets via Prometheus relabeling
- **No built-in dashboard**: Relies on Grafana for visualization

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  blackbox-exporter:
    image: prom/blackbox-exporter:latest
    container_name: blackbox-exporter
    restart: unless-stopped
    ports:
      - "9115:9115"
    volumes:
      - ./blackbox.yml:/etc/blackbox/blackbox.yml:ro
    command:
      - "--config.file=/etc/blackbox/blackbox.yml"
      - "--web.listen-address=:9115"
    cap_add:
      - NET_RAW  # Required for ICMP (ping) probes
```

### Blackbox Exporter Configuration

Save as `blackbox.yml`:

```yaml
modules:
  http_2xx:
    prober: http
    timeout: 10s
    http:
      method: GET
      preferred_ip_protocol: "ip4"
      valid_status_codes: [200, 201, 204]
      no_follow_redirects: false
      fail_if_body_not_matches_regexp:
        - "healthy"
      fail_if_ssl: false
      tls_config:
        insecure_skip_verify: false

  http_post_2xx:
    prober: http
    timeout: 10s
    http:
      method: POST
      headers:
        Content-Type: "application/json"
      body: '{"check": true}'

  dns_tcp:
    prober: dns
    timeout: 5s
    dns:
      query_name: "example.com"
      query_type: "A"
      transport_protocol: "tcp"
      preferred_ip_protocol: "ip4"

  icmp_check:
    prober: icmp
    timeout: 5s
    icmp:
      preferred_ip_protocol: "ip4"
```

### Prometheus Scrape Configuration

Add this to your `prometheus.yml` to wire up the exporter:

```yaml
scrape_configs:
  - job_name: "blackbox-http"
    metrics_path: /probe
    params:
      module: [http_2xx]
    static_configs:
      - targets:
          - "https://example.com"
          - "https://api.example.com/health"
          - "https://status.example.com"
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: "blackbox-exporter:9115"

  - job_name: "blackbox-icmp"
    metrics_path: /probe
    params:
      module: [icmp_check]
    static_configs:
      - targets:
          - "8.8.8.8"
          - "1.1.1.1"
          - "router.internal.lan"
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: "blackbox-exporter:9115"
```

This relabeling pattern is what makes Blackbox Exporter powerful — you add new targets by editing the Prometheus config, not the exporter config. The single exporter instance probes every target and returns standardized metrics like `probe_success`, `probe_duration_seconds`, and `probe_ssl_earliest_cert_expiry`. For a complete guide on setting up Prometheus-based alerting, see our [Prometheus Alertmanager vs Moira vs VictoriaMetrics VMAlert comparison](../prometheus-alertmanager-vs-moira-vs-victoriametrics-vmalert-self-hosted-alerting-2026/).

## SmokePing: Network Latency and Packet Loss Monitoring

SmokePing has been the go-to tool for network latency monitoring since 2001. It uses RRDtool to store and visualize latency data, producing distinctive graphs that show latency distribution, packet loss, and jitter over time. Unlike Gatus and Blackbox Exporter (which focus on "is it up?"), SmokePing answers "how is the network performing?"

### Key Features

- **Latency distribution graphs**: Shows min/avg/max latency with standard deviation bands
- **Packet loss tracking**: Visual representation of lost probes over time
- **Multiple probe types**: FPing (ICMP), HTTP, DNS, TCP, Curl, TACACS+, Radius, LDAP
- **Hierarchical configuration**: Organize targets in tree structures for large deployments
- **Alert system**: Built-in alerting with threshold-based triggers
- **Master/Slave mode**: Distributed probing from multiple geographic locations
- **RRDtool storage**: Efficient time-series data storage with automatic downsampling

### Docker Compose Deployment (LinuxServer.io Image)

```yaml
version: "3.8"

services:
  smokeping:
    image: lscr.io/linuxserver/smokeping:latest
    container_name: smokeping
    restart: unless-stopped
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    ports:
      - "8081:80"
    volumes:
      - ./config:/config
      - ./data:/data
    cap_add:
      - NET_RAW  # Required for FPing (ICMP) probes
```

### SmokePing Configuration

The LinuxServer.io image stores configuration in `/config`. Edit `Targets` to define your monitoring tree:

```ini
*** Targets ***

probe = FPing

menu = Top
title = Network Latency Monitor
remark = SmokePing latency monitoring dashboard

+ LocalNetwork
menu = Local Network
title = Local Infrastructure Latency

++ Router
menu = Gateway
title = Edge Router
host = 192.168.1.1
alerts = someloss

++ NAS
menu = Storage
title = NAS Server
host = 192.168.1.10

+ CloudServices
menu = Cloud Providers
title = External Service Latency

++ GoogleDNS1
menu = Google DNS Primary
title = 8.8.8.8
host = 8.8.8.8
alerts = someloss

++ GoogleDNS2
menu = Google DNS Secondary
title = 8.8.4.4
host = 8.8.4.4

++ CloudflareDNS
menu = Cloudflare DNS
title = 1.1.1.1
host = 1.1.1.1
alerts = someloss

++ AWS
menu = AWS US-East
title = AWS Endpoint
host = d1.cloudfront.net
probe = DNS
```

SmokePing's tree-based configuration (`+` for sections, `++` for targets) makes it easy to organize hundreds of probes into logical groups. The `probe` directive at each level lets you mix ICMP, DNS, and HTTP probes in the same deployment.

## Feature Comparison

| Feature | Gatus | Blackbox Exporter | SmokePing |
|---------|-------|-------------------|-----------|
| **HTTP Probing** | ✅ Full (methods, headers, body) | ✅ Full (modules, regex) | ✅ Via CGI probe |
| **DNS Probing** | ✅ Native | ✅ Native | ✅ Via DNS probe |
| **TCP Probing** | ✅ Native | ✅ Native | ✅ Via TCP probe |
| **ICMP/Ping** | ✅ Native | ✅ Requires NET_RAW | ✅ Via FPing |
| **Dashboard** | ✅ Built-in web UI | ❌ Requires Grafana | ✅ Built-in web UI |
| **Status Page** | ✅ Auto-generated | ❌ No | ❌ No |
| **Alerting** | ✅ 15+ integrations | ✅ Via Alertmanager | ✅ Built-in threshold alerts |
| **Latency Tracking** | Basic (response time) | Via Prometheus metrics | ✅ Detailed distribution graphs |
| **Packet Loss** | ❌ No | ❌ No | ✅ Native tracking |
| **Data Storage** | SQLite / PostgreSQL / MySQL | Prometheus TSDB | RRDtool |
| **Config Format** | YAML | YAML | INI-style |
| **Multi-location** | ❌ Single instance | ✅ Multiple exporters | ✅ Master/Slave mode |
| **Certificate Monitoring** | ✅ Native (expiry check) | ✅ Native (TLS metrics) | ❌ No |
| **Body Content Checks** | ✅ JSON path, regex | ✅ Regex matching | ❌ No |
| **Docker Image** | `ghcr.io/twin/gatus:stable` | `prom/blackbox-exporter` | `lscr.io/linuxserver/smokeping` |
| **Binary Size** | ~25 MB | ~20 MB | ~150 MB (with dependencies) |

## When to Use Each Tool

### Choose Gatus When

- You want a standalone health dashboard with zero external dependencies
- Status pages for your services are a requirement
- You need flexible condition expressions (status codes, response times, certificate expiry, body content)
- Your team prefers config-as-code with a single YAML file
- You want direct alerting integrations without setting up Alertmanager

Gatus excels as a "set it and forget it" monitoring solution. Deploy it, point it at your endpoints, and get a clean dashboard with automatic alerting — no Grafana, no Prometheus, no additional infrastructure needed.

### Choose Blackbox Exporter When

- You already run Prometheus and Grafana
- You need standardized metrics across your entire monitoring stack
- You manage hundreds or thousands of endpoints and want relabeling-based target management
- You want to combine endpoint probes with system metrics, application metrics, and logs in a single observability platform
- You need custom Grafana dashboards with cross-correlated data

The Blackbox Exporter is the right choice when endpoint monitoring is one component of a broader observability strategy. Its integration with the Prometheus ecosystem is unmatched.

### Choose SmokePing When

- Network latency and packet loss are your primary concerns
- You need historical latency trends with distribution visualization
- You operate across multiple network segments or geographic locations
- You want to compare ISP performance or CDN edge latency over time
- You prefer RRDtool's automatic data retention and downsampling

SmokePing remains unmatched for pure network quality monitoring. Its graphs are the gold standard for answering "is the network degrading?" rather than "is the service down?"

## Deployment Architecture Recommendations

### Minimal Stack: Gatus Alone

```
Internet → Gatus (port 8080) → probes endpoints → alerts via Slack/Discord
```

Single container, single config file, zero dependencies. Ideal for homelabs and small teams.

### Prometheus Stack: Blackbox Exporter + Prometheus + Grafana

```
Internet → Blackbox Exporter (port 9115) → exposes /probe metrics
Prometheus scrapes /probe every 30s → stores in TSDB
Grafana queries Prometheus → dashboards + alerting via Alertmanager
```

Full observability stack. Higher resource usage but maximum flexibility.

### Network Monitoring: SmokePing + Reverse Proxy

```
Internet → FPing probes → SmokePing stores RRD data → web UI on port 80
Nginx/Caddy reverse proxy → HTTPS + basic auth → external access
```

Lightweight but requires RRDtool knowledge for advanced customization.

## Migration and Coexistence

These tools are not mutually exclusive. A common production pattern combines Blackbox Exporter (for Prometheus metrics) with Gatus (for status pages):

```yaml
# Both tools probe the same endpoints
# Gatus provides the public status page at status.example.com
# Blackbox Exporter feeds Prometheus for internal dashboards
# SmokePing runs separately for network latency baselines
```

Run SmokePing on a dedicated host or container for continuous latency baselines, while Gatus handles the "is it up" question and Blackbox Exporter feeds your internal observability pipeline.

## FAQ

### What is the difference between uptime monitoring and endpoint monitoring?

Uptime monitoring simply checks whether a service responds (binary up/down). Endpoint monitoring goes deeper — it validates HTTP status codes, measures response times, checks TLS certificate validity, verifies response body content, and tests DNS resolution. Gatus and Blackbox Exporter both provide endpoint-level validation, while SmokePing focuses on the network layer (latency, jitter, packet loss).

### Can I use Blackbox Exporter without Prometheus?

Technically yes — the Blackbox Exporter exposes its own web interface at `http://localhost:9115` where you can manually trigger probes. However, without Prometheus scraping the metrics, you lose historical data, alerting, and visualization. If you want a standalone solution without Prometheus, Gatus is a better fit.

### Does Gatus support multi-location monitoring?

Not natively. Gatus runs as a single instance and probes from the host it is deployed on. If you need geographic multi-location probing, you can deploy multiple Gatus instances (one per location) and point them at a shared PostgreSQL database. SmokePing's master/slave mode is purpose-built for distributed probing and may be easier to configure for this use case.

### How much disk space does SmokePing use?

SmokePing uses RRDtool, which allocates fixed-size round-robin databases per target. A typical SmokePing instance monitoring 50 targets uses 100-500 MB depending on the RRA (Round Robin Archive) configuration. The RRA settings control how long data is retained at different resolutions — for example, keeping 1-minute granularity for 24 hours, 5-minute for 7 days, and 1-hour for 1 year. This is fundamentally different from SQLite or Prometheus TSDB, which grow continuously.

### Can Gatus monitor services behind authentication?

Yes. Gatus supports custom HTTP headers (including `Authorization: Bearer <token>`), basic auth, client certificates, and POST bodies. You can also use environment variable substitution in the config file, which is useful for managing secrets. The `client` field in the endpoint configuration allows you to specify TLS certificates, skip certificate verification, or set proxy servers.

### Which tool has the lowest resource footprint?

Blackbox Exporter uses the least resources when idle (~15 MB RAM) since it only computes metrics on demand when scraped. Gatus uses ~30-50 MB RAM for a moderate number of endpoints due to its built-in web server and SQLite storage. SmokePing uses ~100-150 MB due to Perl dependencies and the web interface (Apache + CGI), plus the RRDtool storage overhead.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Gatus vs Blackbox Exporter vs SmokePing: Self-Hosted Endpoint Monitoring 2026",
  "description": "Compare Gatus, Prometheus Blackbox Exporter, and SmokePing for self-hosted endpoint and synthetic monitoring. Complete Docker setup guides, feature comparison, and alerting configuration for 2026.",
  "datePublished": "2026-04-18",
  "dateModified": "2026-04-18",
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
