---
title: "Self-Hosted DHCP Server Monitoring: ISC Kea vs DHCP Dashboard vs Kea Exporter (2026)"
date: "2026-05-10"
tags: ["dhcp", "monitoring", "network", "kea", "self-hosted", "infrastructure"]
draft: false
---

DHCP (Dynamic Host Configuration Protocol) is the backbone of any network infrastructure — it assigns IP addresses, configures network parameters, and tracks every device that connects to your infrastructure. Yet most organizations run DHCP servers with zero monitoring, only discovering problems when users complain they cannot get an IP address.

In this guide, we compare three approaches to monitoring DHCP servers: **ISC Kea** with its native statistics API, the **Kea Dashboard** (community Grafana solution), and custom **DHCP exporters** for Prometheus integration.

## Why DHCP Monitoring Matters

A DHCP server failure cascades through your entire network. Without monitoring, the first indication of a problem is usually a phone call from a user who cannot connect. Common DHCP failure scenarios include:

- **IP address exhaustion** — all addresses in a subnet are leased, new clients cannot connect
- **Lease database corruption** — server restarts with lost lease state, causing IP conflicts
- **High lease churn** — rapid connect/disconnect cycles indicate network instability or rogue devices
- **Failover partner failure** — in DHCP failover configurations, losing the partner reduces capacity by 50%
- **Configuration drift** — manual changes to subnet definitions or option settings without documentation

Proactive DHCP monitoring catches these issues before they affect users.

## Comparison Table

| Feature | ISC Kea Native Stats | Kea Dashboard (Grafana) | Kea Exporter (Prometheus) |
|---------|---------------------|------------------------|---------------------------|
| **Source** | Kea built-in | Community project | Community exporter |
| **Data Source** | Control API (HTTP) | Kea Control API | Kea Control API |
| **Visualization** | JSON response | Grafana dashboards | Prometheus + Grafana |
| **Alerting** | External scripting | Grafana alerting | Prometheus Alertmanager |
| **Real-time Stats** | ✅ Per-second | ✅ Refresh configurable | ✅ Scrape interval |
| **Historical Data** | ❌ Current state only | ✅ Grafana Loki/TSDB | ✅ Prometheus TSDB |
| **Lease Tracking** | ✅ Active leases count | ✅ Lease charts | ✅ Lease time series |
| **Subnet Utilization** | ✅ Per-subnet stats | ✅ Utilization graphs | ✅ Utilization metrics |
| **Failover Monitoring** | ✅ Partner state | ✅ Partner status panel | ✅ Partner state metric |
| **Setup Complexity** | Low | Moderate | Moderate |
| **Dependencies** | None | Grafana + datasource | Prometheus + Grafana |

## ISC Kea Native Statistics

**ISC Kea** is a modern, extensible DHCP server from the Internet Systems Consortium. Its **Control Agent** provides a REST API for real-time statistics, making it the foundation for any DHCP monitoring solution.

### Key Features

- **Built-in statistics** — Kea tracks lease counts, packet rates, and utilization per subnet
- **Control Agent API** — HTTP-based API for querying stats, managing leases, and reconfiguring
- **Hooks framework** — extend Kea with custom C/C++ plugins for advanced monitoring
- **HA support** — native DHCP failover with hot-standby and load-sharing modes
- **Flexible backends** — store leases in MySQL, PostgreSQL, Cassandra, or Memfile

### Monitoring via Control API

Kea's statistics are accessible via its Control Agent on port 8000:

```bash
# Get all current statistics
curl -s -X POST http://localhost:8000/   -H "Content-Type: application/json"   -d '{ "command": "statistic-get-all" }' | python3 -m json.tool

# Get specific subnet utilization
curl -s -X POST http://localhost:8000/   -H "Content-Type: application/json"   -d '{
    "command": "subnet4-list"
  }' | python3 -m json.tool

# Check DHCPv4 packet rates
curl -s -X POST http://localhost:8000/   -H "Content-Type: application/json"   -d '{ "command": "statistic-get", "arguments": { "name": "pkt4-received" } }'
```

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  kea-dhcp4:
    image: isc-projects/kea:2.6.1
    container_name: kea-dhcp4
    network_mode: host
    volumes:
      - ./kea-dhcp4.conf:/etc/kea/kea-dhcp4.conf
      - kea-leases:/var/lib/kea
    restart: unless-stopped

  kea-ctrl-agent:
    image: isc-projects/kea:2.6.1
    container_name: kea-ctrl-agent
    network_mode: host
    volumes:
      - ./kea-ctrl-agent.conf:/etc/kea/kea-ctrl-agent.conf
    command: [ "kea-ctrl-agent", "-c", "/etc/kea/kea-ctrl-agent.conf" ]
    restart: unless-stopped

volumes:
  kea-leases:
```

Kea DHCP configuration (`kea-dhcp4.conf`):

```json
{
  "Dhcp4": {
    "interfaces-config": {
      "interfaces": [ "eth0" ]
    },
    "lease-database": {
      "type": "memfile",
      "persist": true,
      "name": "/var/lib/kea/kea-leases4.csv"
    },
    "subnet4": [
      {
        "subnet": "192.168.1.0/24",
        "pools": [ { "pool": "192.168.1.100 - 192.168.1.200" } ],
        "option-data": [
          { "name": "routers", "data": "192.168.1.1" },
          { "name": "domain-name-servers", "data": "192.168.1.1" }
        ]
      }
    ],
    "control-socket": {
      "socket-type": "unix",
      "socket-name": "/tmp/kea4-ctrl-socket"
    }
  }
}
```

## Kea Dashboard (Grafana)

The **Kea Dashboard** is a community-built Grafana dashboard that visualizes ISC Kea statistics collected via the Control API. It provides a real-time view of DHCP server health, lease utilization, and failover status.

### Key Features

- **Pre-built panels** — lease counts, utilization percentages, packet rates, and failover state
- **Grafana native** — works with any Grafana deployment and data source
- **Multi-server support** — monitor multiple Kea instances from a single dashboard
- **Customizable alerts** — set Grafana alert rules for threshold breaches
- **Open source** — available on GitHub with active community contributions

### Setup

```bash
# Install Grafana
docker run -d --name grafana -p 3000:3000 grafana/grafana:latest

# Import the Kea dashboard
# 1. Download from: https://github.com/NeySlim/ultimate-kea-dhcp-dashboard
# 2. In Grafana: Dashboard > Import > Upload JSON file
# 3. Configure data source (JSON API plugin or custom datasource)

# For production: use Telegraf or a custom collector to poll Kea stats
# and push to InfluxDB or Prometheus
```

### Telegraf Integration

Use Telegraf's `exec` input plugin to poll Kea statistics and write to InfluxDB:

```toml
[[inputs.exec]]
  commands = ["/usr/local/bin/kea-stats-collector.sh"]
  data_format = "json"
  name_override = "kea_dhcp_stats"
  tag_keys = ["subnet_id", "server"]

[[outputs.influxdb_v2]]
  urls = ["http://localhost:8086"]
  token = "${INFLUXDB_TOKEN}"
  organization = "monitoring"
  bucket = "kea-dhcp"
```

## Kea Exporter for Prometheus

The **Kea Exporter** is a Prometheus exporter that polls ISC Kea's Control API and exposes metrics in Prometheus format. Combined with Prometheus and Grafana, it provides comprehensive DHCP monitoring with alerting.

### Key Features

- **Prometheus metrics** — standard `kea_dhcp_*` metric namespace
- **Auto-discovery** — automatically detects new subnets and exposes per-subnet metrics
- **Histogram support** — tracks lease duration distributions and response time percentiles
- **Alert-ready** — metrics work with Prometheus Alertmanager for automated notifications
- **Low overhead** — lightweight Go binary with minimal resource consumption

### Key Metrics Exposed

```
kea_dhcp4_subnets_total{subnet_id="1"}        # Total addresses in subnet
kea_dhcp4_leases_active{subnet_id="1"}         # Active leases
kea_dhcp4_utilization{subnet_id="1"}           # Utilization percentage (0-100)
kea_dhcp4_packets_received_total{type="discover"}  # DHCP DISCOVER count
kea_dhcp4_packets_sent_total{type="offer"}     # DHCP OFFER count
kea_dhcp4_failover_state{peer="secondary"}     # Failover partner state
```

### Docker Compose with Prometheus

```yaml
version: "3.8"
services:
  kea-exporter:
    image: ghcr.io/isc-projects/kea-exporter:latest
    container_name: kea-exporter
    ports:
      - "9547:9547"
    environment:
      - KEA_CONTROL_URL=http://kea-ctrl-agent:8000
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
    restart: unless-stopped

volumes:
  prometheus-data:
  grafana-data:
```

Prometheus scrape configuration:

```yaml
scrape_configs:
  - job_name: kea-dhcp
    static_configs:
      - targets: ["kea-exporter:9547"]
    scrape_interval: 15s
```

## Why Self-Host Your DHCP Monitoring?

Self-hosted DHCP monitoring keeps your network infrastructure telemetry under your control:

- **No data egress** — DHCP lease data reveals every device on your network; keeping monitoring on-premises protects this sensitive inventory
- **Custom alerting** — integrate with your existing PagerDuty, Slack, or email alerting pipelines
- **Historical analysis** — track IP address utilization trends over months to plan capacity
- **Compliance** — maintain audit trails of DHCP assignments for regulatory requirements
- **Cost control** — eliminate the per-device monitoring fees of cloud-based network management platforms

For broader network infrastructure monitoring, see our [network topology mapping guide](../2026-05-02-self-hosted-network-topology-mapping-netbox-librenms-auto-discovery/) and [network discovery tools comparison](../2026-04-25-netdisco-vs-librenms-vs-opennetadmin-network-discovery-guide-2026/). For zero-trust network access patterns, our [Headscale vs NetBird vs OpenZiti guide](../2026-05-03-headscale-vs-netbird-vs-openziti-self-hosted-zero-trust-network-acces/) covers modern network access control.

## FAQ

### What DHCP metrics should I monitor?

The most critical DHCP metrics are: (1) subnet utilization percentage — alerts when pools are >80% full, (2) active lease count — tracks total connected devices, (3) packet receive/send rates — detects DHCP server overload, (4) failover partner state — ensures HA redundancy, and (5) lease renewal rate — identifies network churn issues.

### Can I monitor ISC Kea without installing additional software?

Yes. ISC Kea's built-in Control Agent provides a REST API that returns current statistics as JSON. You can poll this API with simple curl commands or cron scripts without any monitoring infrastructure.

### How do I set up alerts for DHCP IP address exhaustion?

With the Prometheus exporter, create an alert rule: `kea_dhcp4_utilization > 80`. With Grafana dashboards, set a threshold alert on the utilization panel. With native Kea stats, write a cron script that polls the Control API and sends notifications via email or webhook when utilization exceeds your threshold.

### Does DHCP monitoring work with ISC DHCP (the legacy server)?

ISC DHCP (dhcpcd/isc-dhcp-server) does not have a built-in statistics API like Kea. For legacy ISC DHCP, you need to parse lease files (`/var/lib/dhcp/dhcpd.leases`) and syslog entries, or use tools like `dhcpd-pools` to calculate utilization from the lease database.

### What is the difference between DHCPv4 and DHCPv6 monitoring?

Both protocols expose similar statistics (lease counts, utilization, packet rates) but through separate APIs. Kea provides `statistic-get-all` for both DHCPv4 and DHCPv6. Monitoring tools should track both protocols independently since they serve different purposes (DHCPv4 for IPv4 addressing, DHCPv6 for IPv6 and prefix delegation).

### How often should I poll DHCP statistics?

For real-time dashboards, poll every 15-30 seconds. For capacity planning and trend analysis, 5-minute intervals are sufficient. For alerting, 1-minute polling ensures rapid detection of IP exhaustion or failover failures.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DHCP Server Monitoring: ISC Kea vs DHCP Dashboard vs Kea Exporter (2026)",
  "description": "Monitor your DHCP infrastructure with ISC Kea statistics, community Grafana dashboards, and Prometheus exporters. Comprehensive guide to DHCP server monitoring.",
  "datePublished": "2026-05-10",
  "dateModified": "2026-05-10",
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
