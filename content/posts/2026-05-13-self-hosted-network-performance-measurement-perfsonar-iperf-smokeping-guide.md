---
title: "Self-Hosted Network Performance Measurement: perfSONAR vs iPerf vs Smokeping"
date: "2026-05-13"
tags: ["network-performance", "bandwidth", "latency", "monitoring", "infrastructure"]
draft: false
---

Network performance measurement is the practice of quantifying how well your network delivers data — measuring bandwidth, latency, packet loss, jitter, and throughput across paths, over time, and under varying load conditions. Without systematic measurement, network degradation goes unnoticed until users complain, making root cause analysis nearly impossible.

This guide compares three open-source approaches to self-hosted network performance measurement: **perfSONAR**, **iPerf management platforms**, and **Smokeping**. Each targets a different aspect of network performance — from scientific-grade end-to-end measurements to lightweight latency visualization.

| Feature | perfSONAR | iPerf Management | Smokeping |
|---------|-----------|-----------------|-----------|
| Stars | 120+ (toolkit) | 3,000+ (iperf3) | 600+ |
| Language | Perl, Java, Python | Go/Python/Shell | Perl |
| Primary Focus | End-to-end network measurement | Throughput testing | Latency and packet loss trending |
| Measurement Types | Bandwidth, latency, loss, traceroute, OWAMP | TCP/UDP throughput | ICMP latency, loss, jitter |
| Web UI | Yes (LSDB dashboard) | Varies by platform | Yes (built-in CGI) |
| Scheduling | Built-in (cron-style) | Platform-dependent | Built-in (probe scheduler) |
| Multi-site | Yes (federated mesh) | No (point-to-point) | No (single collector) |
| Docker Support | Official images | Community images | Official Dockerfile |
| License | Apache 2.0 | BSD 3-Clause | GPLv2 |

## perfSONAR: Scientific-Grade Network Measurement

[perfSONAR](https://github.com/perfsonar/toolkit) is a comprehensive network measurement platform originally developed for the research and education community. It provides a standardized toolkit for measuring end-to-end network performance between sites, with support for bandwidth testing (NDT, iperf3), latency measurement (OWAMP, TWAMP), and path characterization (traceroute).

### perfSONAR Architecture

perfSONAR consists of several components:

**pscheduler** — The scheduling engine that coordinates measurement tasks across the mesh.

**perfSONAR Toolkit** — The all-in-one distribution running on CentOS or Rocky Linux.

**LSDB (Local Store Database)** — The storage and query layer for measurement results.

**MaDDash** — The dashboard that aggregates results from multiple measurement points.

### Deploying perfSONAR with Docker

```yaml
version: "3.8"
services:
  perfsonar-toolkit:
    image: perfsonar/toolkit:latest
    ports:
      - "8080:80"
      - "9080:9080"
      - "5001:5001"
      - "5002:5002"
      - "8081-8086:8081-8086"
    volumes:
      - perfsonar-data:/var/lib/perfsonar
      - ./toolkit.conf:/etc/perfsonar/toolkit.conf
    environment:
      - PERFSONAR_HOSTNAME=perfsonar.example.com
    cap_add:
      - NET_ADMIN
volumes:
  perfsonar-data:
```

### Configuring perfSONAR Tests

```json
{
  "test_schedules": [
    {
      "type": "throughput",
      "tool": "iperf3",
      "dest": "remote.perfsonar.net",
      "schedule": "0 */6 * * *",
      "duration": "PT30S"
    },
    {
      "type": "latency",
      "tool": "owamp",
      "dest": "remote.perfsonar.net",
      "schedule": "*/5 * * * *",
      "duration": "PT60S"
    }
  ]
}
```

perfSONAR key strength is its federated mesh architecture. Any perfSONAR node can schedule tests against any other node in the global mesh (over 800 nodes worldwide), enabling comprehensive end-to-end network characterization across institutional boundaries.

## iPerf Management Platforms

While **iPerf3** (the industry-standard bandwidth testing tool with 3,000+ GitHub stars) is ubiquitous for point-in-point throughput testing, managing multiple iPerf servers and orchestrating regular tests across a network requires additional tooling. Several open-source platforms fill this gap.

### iPerf3 Server Setup

```yaml
version: "3.8"
services:
  iperf3-server:
    image: networkstatic/iperf3:latest
    ports:
      - "5201:5201"
    command: ["-s"]
    restart: unless-stopped
```

### Automated iPerf3 Testing Script

```bash
#!/bin/bash
# iperf-monitor.sh — automated bandwidth testing
SERVERS="10.0.1.100 10.0.2.100 10.0.3.100"
RESULTS_DIR="/var/lib/iperf-results"
mkdir -p "$RESULTS_DIR"

for server in $SERVERS; do
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    result=$(iperf3 -c "$server" -t 10 -J 2>/dev/null)
    if [ $? -eq 0 ]; then
        bitrate=$(echo "$result" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d['end']['sum_sent']['bits_per_second'] / 1e6)
")
        echo "$timestamp,$server,$bitrate" >> "$RESULTS_DIR/throughput.csv"
    fi
done
```

### iPerf3 with Prometheus Exporter

```yaml
version: "3.8"
services:
  iperf3-exporter:
    image: ghcr.io/mr-golger/iperf3-exporter:latest
    ports:
      - "9494:9494"
    environment:
      - IPERF_SERVERS=10.0.1.100:5201,10.0.2.100:5201
      - IPERF_INTERVAL=3600
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
```

For organizations needing regular throughput monitoring without the full perfSONAR stack, pairing iPerf3 with a Prometheus exporter provides a lightweight alternative. The exporter runs scheduled iPerf3 tests against configured servers and exposes results as Prometheus metrics for dashboarding in Grafana.

## Smokeping: Latency and Packet Loss Trending

[Smokeping](https://github.com/oetiker/smokeping) is a latency measurement and visualization tool that continuously pings target hosts and generates detailed RRD-based graphs showing latency trends, packet loss, and jitter over time.

### Smokeping Configuration

```ini
*** Probes ***

+ FPing
binary = /usr/sbin/fping

+ Curl
binary = /usr/bin/curl

*** Targets ***

probe = FPing

menu = Top
title = Network Latency
remark = Latency measurements across the network

+ CoreNetwork
menu = Core
title = Core Network Latency

++ Gateway
menu = Gateway
title = Default Gateway
host = 10.0.0.1

++ Firewall
menu = Firewall
title = Core Firewall
host = 10.0.0.254

+ Upstream
menu = Upstream
title = Upstream Providers

++ GoogleDNS
menu = Google DNS
title = 8.8.8.8
host = 8.8.8.8

++ CloudflareDNS
menu = Cloudflare DNS
title = 1.1.1.1
host = 1.1.1.1
```

### Deploying Smokeping with Docker Compose

```yaml
version: "3.8"
services:
  smokeping:
    image: linuxserver/smokeping:latest
    ports:
      - "8080:80"
    volumes:
      - ./config:/config
      - ./data:/data
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
```

Smokeping unique strength is its ability to visualize latency distribution — it does not just show average ping times, but displays the full range of responses (min, median, max) as smoke-like graphs that reveal latency jitter at a glance. Packet loss is shown as colored bands, making it easy to spot intermittent connectivity issues.

## Why Self-Host Network Performance Measurement?

**Baseline establishment.** You cannot identify degradation without knowing what normal looks like. Self-hosted measurement tools continuously collect baseline data across your network paths, enabling rapid identification of when and where performance deviates from historical norms.

**Capacity planning.** Bandwidth and latency trends over weeks and months reveal when links are approaching saturation. This data-driven approach to capacity planning prevents emergency upgrades and supports informed budget requests with concrete evidence.

**Multi-provider comparison.** Organizations with multiple upstream providers or WAN links can use measurement tools to continuously compare performance across paths. This enables automated failover decisions and provides evidence for SLA enforcement discussions with ISPs.

**Troubleshooting acceleration.** When users report the network is slow, having historical performance data narrows the investigation from check everything to compare current metrics to baseline. This reduces mean time to resolution (MTTR) for network incidents.

**Compliance and reporting.** For organizations with SLA commitments to customers or regulatory requirements for network availability, systematic measurement provides auditable evidence of compliance or identifies gaps before they become contractual breaches.

For endpoint monitoring, see our [Gatus vs Blackbox vs Smokeping guide](../gatus-vs-blackbox-exporter-vs-smokeping-self-hosted-endpoint-monitoring/).
For bandwidth testing tools, check our [network bandwidth testing comparison](../2026-05-08-iperf3-vs-netperf-vs-qperf-self-hosted-network-bandwidth-testing/).
For broader infrastructure monitoring, our [SNMP trap management guide](../2026-05-12-self-hosted-snmp-trap-management-snmtt-snmptrapd-opennms-trapd/) covers it.

## Choosing the Right Network Measurement Tool

**perfSONAR** is the best choice for organizations needing comprehensive, standardized network measurement across multiple sites. Its federated architecture and support for multiple measurement types (bandwidth, latency, path characterization) make it ideal for research institutions, universities, and enterprises with multi-site networks.

**iPerf Management** (iperf3 plus Prometheus exporter) is ideal for teams that need straightforward throughput monitoring without the complexity of a full measurement platform. It is lightweight, easy to deploy, and integrates with existing Prometheus or Grafana stacks. Best for small to medium networks (1-50 links).

**Smokeping** is the right choice for continuous latency monitoring and visualization. Its RRD-based graphs provide instant visual feedback on latency trends and packet loss patterns. Ideal for NOCs, ISPs, and organizations where latency consistency matters more than raw throughput.

## FAQ

### What is the difference between bandwidth and throughput?

Bandwidth is the maximum theoretical data rate of a network link (e.g., 1 Gbps). Throughput is the actual data rate achieved during a measurement, which is always lower than bandwidth due to protocol overhead, congestion, and hardware limitations.

### How often should I run network performance tests?

For latency (Smokeping), every 1-5 minutes is typical. For throughput (iPerf3), every 1-6 hours is sufficient — continuous throughput testing can itself consume significant bandwidth. perfSONAR default schedule runs throughput tests every 6 hours and latency tests every 5 minutes.

### Can Smokeping measure TCP latency, not just ICMP?

Yes. While Smokeping default probe uses FPing (ICMP), it also supports Curl, DNS, HTTP, and other probes. The FPing probe measures ICMP round-trip time, while the Curl probe measures TCP connection time to specific web services.

### Does perfSONAR require dedicated hardware?

No. perfSONAR runs on standard x86_64 servers or VMs. The recommended minimum is 2 CPU cores, 4 GB RAM, and 50 GB storage. For high-frequency testing or multi-gigabit links, more resources may be needed.

### How do I measure network jitter?

Jitter is the variation in latency over time. Smokeping visualizes jitter through its smoke graphs — wider smoke bands indicate higher jitter. perfSONAR OWAMP and TWAMP measurements also report jitter statistics as part of their latency measurements.

### What is OWAMP and TWAMP?

OWAMP (One-Way Active Measurement Protocol, RFC 4656) and TWAMP (Two-Way Active Measurement Protocol, RFC 5357) are standardized protocols for measuring network latency. Unlike ICMP ping, they measure latency in both directions independently, providing more accurate path characterization. perfSONAR includes built-in OWAMP and TWAMP support.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Network Performance Measurement: perfSONAR vs iPerf vs Smokeping",
  "description": "Compare three open-source network performance measurement tools — perfSONAR, iPerf management, and Smokeping — for monitoring bandwidth, latency, and packet loss.",
  "datePublished": "2026-05-13",
  "dateModified": "2026-05-13",
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
