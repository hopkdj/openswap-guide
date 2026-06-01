---
title: "Self-Hosted Network Bandwidth Monitoring Dashboards: darkstat vs vnStat-PHP vs BandwidthD (2026)"
date: "2026-06-01"
tags: ["network-monitoring", "bandwidth", "self-hosted", "traffic-analysis", "dashboard", "infrastructure", "sysadmin"]
draft: false
---

## Introduction

Understanding where your bandwidth goes is essential for capacity planning, troubleshooting, and detecting anomalous traffic patterns. While full packet capture tools like Zeek and Suricata provide deep inspection, sometimes you just need a lightweight, always-on bandwidth monitor that tracks per-interface throughput and presents it in a clean web dashboard. **darkstat**, **vnStat-PHP**, and **BandwidthD** represent three generations of self-hosted traffic monitoring — from the minimalist C-based darkstat (1999) to the PHP-fronted vnStat (2000s) to the graph-heavy BandwidthD (early 2000s). Despite their age, all three remain actively used and packaged across Linux distributions, providing reliable bandwidth visibility without the overhead of modern observability stacks.

This article compares darkstat, vnStat (with its PHP frontend), and BandwidthD to help you choose the right lightweight bandwidth monitoring dashboard.

## Why Self-Host Your Bandwidth Monitor?

Running your own bandwidth monitor gives you **complete data ownership** — your traffic patterns, peak usage hours, and per-host consumption statistics stay on your infrastructure rather than feeding into a cloud analytics platform. This is particularly important for ISPs, hosting providers, and privacy-conscious organizations. Second, **resource efficiency**: tools like darkstat consume less than 10MB of RAM and negligible CPU, making them deployable on the smallest edge devices. Compare this to Prometheus + Grafana stacks that can consume gigabytes. Third, **operational independence**: a self-hosted bandwidth monitor works even when your internet connection is down — you can still view local traffic statistics, diagnose internal network issues, and verify whether the problem is with your ISP or your LAN. For broader network traffic analysis, our [Arkime vs Zeek vs Suricata comparison](../2026-05-04-arkime-vs-zeek-vs-suricata-self-hosted-network-traffic-analysis-guide/) covers deeper inspection tools. If you need bandwidth shaping rather than monitoring, check our [Wondershaper vs Trickle comparison](../2026-05-02-wondershaper-vs-trickle-vs-tc-bandwidth-management-guide-2026/).

## Tool Comparison

| Feature | darkstat | vnStat + vnStat-PHP | BandwidthD |
|---------|----------|---------------------|------------|
| **Language** | C | C (vnStat) + PHP (frontend) | C |
| **Capture Method** | libpcap | /proc/net/dev (kernel counters) | libpcap |
| **Web Dashboard** | Built-in (single-page) | vnStat-PHP (external) | Built-in (CGI graphs) |
| **Per-Host Tracking** | Yes | No (interface-level only) | Yes |
| **Protocol Breakdown** | Yes (port-based) | No | No |
| **Historical Storage** | In-memory only | Database (SQLite/MySQL) | PostgreSQL/ODBC |
| **Resource Usage** | ~5MB RAM | ~2MB (vnStat) + PHP | ~15MB RAM |
| **Docker Availability** | Community images | Community images | Community images |
| **Active Development** | Stable (2025) | Active (vnStat 2.x) | Stale (SourceForge) |
| **Graph Types** | Real-time bar charts | Hourly/daily/monthly bar graphs | Daily/weekly/monthly/yearly line graphs |

## darkstat

[darkstat](https://github.com/emikulic/darkstat) is the lightest of the three, capturing packets via libpcap and presenting a real-time web dashboard with per-host and per-protocol breakdowns. It stores all data in memory — no database required — which makes it incredibly fast to deploy but means statistics are lost on restart. Its web interface is a single HTML page with embedded graphs: hosts table, ports table, and traffic graphs for the last minute, hour, and day.

```bash
# Install and run darkstat
apt install darkstat
# Edit /etc/darkstat/init.cfg to set the interface
sudo darkstat -i eth0 --port 667
# Access at http://server-ip:667
```

```yaml
# docker-compose.yml for darkstat
version: "3.8"
services:
  darkstat:
    image: p3terx/darkstat:latest
    container_name: darkstat
    network_mode: host
    restart: unless-stopped
    command:
      - "-i"
      - "eth0"
      - "--port"
      - "667"
```

darkstat's killer feature is its **protocol breakdown**: it identifies traffic by destination port and maps common ports to service names (HTTP, SSH, DNS, etc.). This gives you immediate visibility into what's consuming bandwidth without deploying a separate flow exporter. The trade-off is that all statistics are ephemeral — restart the container and you lose historical data.

## vnStat with vnStat-PHP

[vnStat](https://humdi.net/vnstat/) takes a fundamentally different approach: instead of packet capture, it reads kernel interface counters from `/proc/net/dev`. This means it cannot provide per-host breakdowns, but it has virtually zero CPU overhead and its statistics survive reboots because they're stored in a persistent database. vnStat collects data via a lightweight daemon that polls interface counters every 30 seconds by default.

```bash
# Install and configure vnStat
apt install vnstat vnstati
sudo systemctl enable --now vnstat
# Create the database for your interface
sudo vnstat -i eth0 --create
```

The native vnStat output is a terminal-based CLI. **vnStat-PHP** is a third-party web frontend that renders vnStat's database into interactive graphs. It supports hourly, daily, monthly, and yearly views with traffic totals, averages, and estimated usage.

```yaml
# docker-compose.yml for vnStat + vnStat-PHP
version: "3.8"
services:
  vnstat:
    image: vergoh/vnstat:latest
    container_name: vnstat
    network_mode: host
    restart: unless-stopped
    environment:
      - INTERFACES=eth0
    volumes:
      - ./vnstat/data:/var/lib/vnstat
  vnstat-php:
    image: vergoh/vnstat-php-frontend:latest
    container_name: vnstat-php
    restart: unless-stopped
    ports:
      - "8080:80"
    volumes:
      - ./vnstat/data:/var/lib/vnstat:ro
```

vnStat's key advantage is **reliability at scale**: it can track years of bandwidth data with a tiny footprint. For environments where you need month-over-month trending for capacity planning, vnStat is the best choice. The PHP frontend adds browser-accessible graphs and reports.

## BandwidthD

[BandwidthD](https://sourceforge.net/projects/bandwidthd/) is the most graph-oriented of the three. It captures packets via libpcap (like darkstat) but stores aggregated data in a PostgreSQL or ODBC database. BandwidthD generates **daily, weekly, monthly, and yearly graphs** showing bandwidth usage per IP address and per subnet. Its web interface presents a hierarchical view: you start with a summary page of all monitored subnets, drill into individual IPs, and see traffic graphs for each.

```yaml
# docker-compose.yml for BandwidthD
version: "3.8"
services:
  bandwidthd:
    image: individualit/bandwidthd:latest
    container_name: bandwidthd
    network_mode: host
    restart: unless-stopped
    volumes:
      - ./bandwidthd/config:/etc/bandwidthd
      - ./bandwidthd/htdocs:/var/www/bandwidthd
    environment:
      - SUBNETS=192.168.1.0/24
```

BandwidthD's strength is its **long-term trending visualizations**. The yearly graph provides an at-a-glance view of bandwidth growth, which is invaluable for ISP billing disputes or justifying infrastructure upgrades. However, its codebase is older and development has largely stalled — the official SourceForge project sees minimal updates.

## Deployment Considerations

For all three tools, **network host mode** is recommended in Docker because they need access to raw network interfaces for packet capture (darkstat, BandwidthD) or kernel counters (vnStat). If host mode is not an option, use `--cap-add=NET_ADMIN` and `--cap-add=NET_RAW` with a macvlan network.

For production deployments, pair these lightweight monitors with a **reverse proxy** (Nginx or Caddy) for TLS termination and optional HTTP authentication. Since these tools serve read-only traffic statistics, the security risk is low, but you should still avoid exposing them directly to the public internet without access controls.

## FAQ

### Which tool is best for long-term bandwidth tracking?

**vnStat** with its PHP frontend is the champion for long-term tracking. Its kernel-counter-based approach means it never misses a byte, and its compact database can store years of hourly/daily/monthly data. BandwidthD is also good for long-term graphs but requires PostgreSQL setup and generates static images rather than interactive charts. darkstat is memory-only and loses all data on restart — best for real-time monitoring only.

### Can I monitor multiple interfaces simultaneously?

Yes. All three tools support multiple interfaces. vnStat can track multiple interfaces from a single daemon (set `INTERFACES=eth0,eth1,wg0` in the config). darkstat requires running one instance per interface (on different ports). BandwidthD monitors multiple subnets from a single instance. For Docker deployments, network host mode gives access to all host interfaces.

### Do these tools capture packet payloads?

No. All three tools only capture **metadata** — source/destination IPs, ports, byte counts, and protocol types. They do not store or analyze packet payloads. This makes them suitable for environments where privacy regulations prohibit deep packet inspection. If you need payload-level analysis, consider dedicated packet capture tools like tcpdump or Wireshark. Our [network traffic analysis guide](../2026-05-04-arkime-vs-zeek-vs-suricata-self-hosted-network-traffic-analysis-guide/) covers session-level analysis tools.

### How do these compare to Prometheus + Grafana?

Prometheus with node exporter provides interface-level bandwidth metrics with sub-minute granularity, making it suitable for real-time alerting and dashboarding. However, Prometheus is significantly heavier (100MB+ RAM for a basic stack) and requires more setup. darkstat, vnStat, and BandwidthD are **purpose-built for bandwidth monitoring** with simpler deployment, lower resource usage, and built-in bandwidth-specific visualizations. Choose Prometheus+Grafana if you already run a monitoring stack; choose these tools if you need a standalone bandwidth monitor.

### Can I get per-application bandwidth data?

darkstat provides per-port breakdowns, which can approximate per-application usage if your applications use well-known ports (HTTP=80/443, SSH=22, etc.). BandwidthD tracks per-IP usage, which helps identify which hosts consume the most bandwidth. For true per-process or per-application bandwidth monitoring, you would need eBPF-based tools like bpftop or a full NetFlow/sFlow collector like pmacct — our [network flow analysis guide](../2026-05-15-self-hosted-network-flow-analysis-pmacct-nfdump-fprobe-guide/) covers those options.

---

**💰 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — it's the world's largest prediction market platform, where you can bet on everything from election outcomes to regulatory timelines. Unlike gambling, this is a genuine information market: the more you know, the better your odds. I've made solid returns predicting tech-related events. Sign up with my referral link: [Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Network Bandwidth Monitoring Dashboards: darkstat vs vnStat-PHP vs BandwidthD (2026)",
  "description": "Compare three lightweight self-hosted bandwidth monitoring tools — darkstat, vnStat-PHP, and BandwidthD — for real-time and historical network traffic visualization. Includes Docker Compose configs and feature comparison.",
  "datePublished": "2026-06-01",
  "dateModified": "2026-06-01",
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
