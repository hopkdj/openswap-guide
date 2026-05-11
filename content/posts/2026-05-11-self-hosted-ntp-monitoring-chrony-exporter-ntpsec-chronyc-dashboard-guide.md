---
title: "Self-Hosted NTP Monitoring: chrony_exporter vs NTPsec vs chronyc Dashboard Solutions"
date: "2026-05-11"
tags: ["ntp", "time-sync", "monitoring", "chrony", "prometheus", "self-hosted"]
draft: false
---

Accurate time synchronization is the invisible foundation of distributed systems. When NTP drifts, authentication fails, log timestamps diverge, and debugging becomes impossible. Monitoring your NTP infrastructure — offset, jitter, stratum, and peer health — catches time synchronization problems before they cascade into system failures.

This guide compares three approaches to self-hosted NTP monitoring: **chrony_exporter** for Prometheus integration, **NTPsec's built-in monitoring tools**, and **chronyc-based dashboard solutions** for real-time NTP health visibility.

## Why Monitor NTP?

NTP monitoring tracks four critical metrics:
- **Offset** — the time difference between your server and reference clocks
- **Jitter** — variation in offset measurements over time
- **Stratum** — the distance from authoritative time sources (stratum 0 = atomic clock)
- **Peer health** — whether upstream NTP servers are reachable and synchronized

Without monitoring, a server can silently drift by seconds or minutes. This breaks TLS certificate validation, causes database replication conflicts, and makes log correlation impossible across distributed services.

## Comparison: NTP Monitoring Tools

| Feature | chrony_exporter | NTPsec (ntpviz) | chronyc Dashboard |
|---------|----------------|-----------------|-------------------|
| **Stars** | 100 | 277 (NTPsec) | Community scripts |
| **Metrics** | Prometheus format | Graphs + HTML | CLI + custom dash |
| **Alerting** | Via Prometheus/Alertmanager | No | Manual |
| **Real-time** | Yes (scrape interval) | Batch (daily graphs) | Yes |
| **Historical** | Via Prometheus TSDB | Via PNG graphs | Depends on backend |
| **Installation** | Go binary | Python (bundled) | Bash + gnuplot |
| **NTP Daemon** | chrony only | NTPsec only | chrony or ntpd |
| **Docker Support** | Yes | Yes | Limited |
| **Grafana Dashboard** | Yes (community) | No | Custom required |
| **Last Active** | Active | Active | N/A |

## Deploying chrony_exporter with Prometheus

chrony_exporter exposes chrony daemon metrics in Prometheus format, enabling integration with existing monitoring stacks. It scrapes the chrony control socket and exports offset, jitter, stratum, and peer state metrics.

```yaml
# docker-compose.yml for chrony_exporter
version: "3"
services:
  chrony_exporter:
    image: prometheuscommunity/chrony-exporter:latest
    ports:
      - "9123:9123"
    environment:
      - TZ=UTC
    cap_add:
      - SYS_TIME
    volumes:
      - /etc/chrony/chrony.conf:/etc/chrony/chrony.conf:ro
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    restart: unless-stopped

volumes:
  prometheus-data:
```

```yaml
# prometheus.yml scrape config
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "chrony"
    static_configs:
      - targets: ["chrony_exporter:9123"]
    metrics_path: "/metrics"
```

Key metrics exposed include `chrony_offset_seconds`, `chrony_stratum`, `chrony_sync_state`, and per-peer statistics. These feed directly into Grafana dashboards and Prometheus alerting rules:

```yaml
# Prometheus alerting rules for NTP
groups:
  - name: ntp_alerts
    rules:
      - alert: NTPLargeOffset
        expr: abs(chrony_offset_seconds) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "NTP offset exceeds 100ms"
      - alert: NTPUnsynchronized
        expr: chrony_sync_state != 1
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "NTP daemon is not synchronized"
```

## NTPsec Monitoring with ntpviz

NTPsec is a hardened fork of the classic NTP daemon that includes **ntpviz**, a suite of visualization tools that generate HTML reports and PNG graphs from NTP statistics. Unlike Prometheus-based monitoring, ntpviz produces self-contained reports that can be served via any web server.

```yaml
# docker-compose.yml for NTPsec
version: "3"
services:
  ntpsec:
    image: ntpsec/ntpsec:latest
    ports:
      - "123:123/udp"
    cap_add:
      - SYS_TIME
      - SYS_NICE
    volumes:
      - ./ntp.conf:/etc/ntpsec/ntp.conf:ro
      - ntp-data:/var/lib/ntpsec
    restart: unless-stopped

volumes:
  ntp-data:
```

```conf
# ntp.conf for NTPsec
# Use public NTP pool servers
server 0.pool.ntp.org iburst
server 1.pool.ntp.org iburst
server 2.pool.ntp.org iburst
server 3.pool.ntp.org iburst

# Restrict access
restrict default nomodify nopeer noquery
restrict 127.0.0.1
restrict ::1

# Log file for ntpviz
statsdir /var/lib/ntpsec/stats/
filegen peerstats file peerstats type day enable
filegen loopstats file loopstats type day enable
filegen clockstats file clockstats type day enable
```

Generate daily monitoring reports:

```bash
# Generate NTP visualization report
docker exec -it ntpsec ntpviz -D /var/lib/ntpsec/stats/ -g

# Generate specific graphs
ntpviz -D /var/lib/ntpsec/stats/ -p  # Peer offset graphs
ntpviz -D /var/lib/ntpsec/stats/ -l  # Loop filter graphs
ntpviz -D /var/lib/ntpsec/stats/ -s  # System offset graphs
```

ntpviz produces HTML files with embedded PNG graphs showing offset over time, peer reachability, and frequency stability. These reports can be served via nginx for team access or emailed as daily summaries.

## chronyc-Based Monitoring Dashboards

chronyc is the command-line interface for the chrony NTP daemon. While not a monitoring tool by itself, it provides the raw data needed to build custom monitoring dashboards. Combined with cron and gnuplot, you can create time-series visualizations without Prometheus.

```bash
#!/bin/bash
# chrony-monitor.sh — Collect and graph NTP metrics
LOG_DIR="/var/log/chrony-monitor"
mkdir -p "$LOG_DIR"

# Collect current metrics
TIMESTAMP=$(date +%s)
OFFSET=$(chronyc tracking | grep "Last offset" | awk '{print $4}')
STRATUM=$(chronyc tracking | grep "Stratum" | awk '{print $3}')
JITTER=$(chronyc tracking | grep "RMS offset" | awk '{print $4}')

echo "$TIMESTAMP $OFFSET $STRATUM $JITTER" >> "$LOG_DIR/chrony-metrics.log"

# Generate graph (requires gnuplot)
gnuplot << 'EOF'
set terminal png size 800,400
set output "/var/log/chrony-monitor/offset-graph.png"
set title "NTP Offset Over Time"
set xlabel "Time"
set ylabel "Offset (seconds)"
set xdata time
set timefmt "%s"
set format x "%H:%M"
plot "/var/log/chrony-monitor/chrony-metrics.log" using 1:2 with lines title "Offset"
EOF
```

For real-time dashboards, pipe chronyc output into a web-accessible JSON endpoint:

```bash
#!/bin/bash
# chrony-api.sh — JSON endpoint for chrony status
echo "Content-Type: application/json"
echo ""
chronyc tracking -n | awk '
BEGIN { printf "{" }
{ gsub(/^[ 	]+/, ""); split($0, a, " : "); gsub(/"/, "", a[2]); printf ""%s":"%s",", a[1], a[2] }
END { printf "}" }
'
```

## Choosing the Right NTP Monitoring Approach

| Scenario | Recommended Tool |
|----------|-----------------|
| Existing Prometheus/Grafana stack | chrony_exporter |
| Standalone NTP server monitoring | NTPsec ntpviz |
| Lightweight CLI-only monitoring | chronyc + cron |
| Enterprise alerting requirements | chrony_exporter + Alertmanager |
| Historical report generation | NTPsec ntpviz |
| Custom dashboard integration | chronyc + gnuplot |

For infrastructure teams already running Prometheus, chrony_exporter provides the smoothest integration with existing dashboards and alerting pipelines. NTPsec's ntpviz excels when you need self-contained reports without external dependencies. The chronyc approach offers maximum flexibility for custom monitoring setups.

## Why Self-Host NTP Monitoring?

Cloud providers handle NTP monitoring for their managed services, but self-hosted infrastructure requires explicit time monitoring. When your servers act as NTP clients to external pools — or as NTP servers for internal networks — monitoring ensures your time infrastructure remains healthy.

Internal NTP servers reduce external network dependencies and provide consistent time even during internet outages. Monitoring these internal servers catches upstream pool degradation before it affects your entire fleet. A single well-monitored stratum 2 server can serve time to hundreds of internal hosts with millisecond accuracy.

For container orchestration, accurate time is critical — Kubernetes uses timestamps for certificate rotation, pod scheduling, and event ordering. Check our [Kubernetes management guide](../2026-04-22-rancher-vs-kubespray-vs-kind-self-hosted-kubernetes-management-guide-2026/) for cluster-level time considerations. For GPU cluster monitoring (where time sync affects job scheduling), see our [GPU monitoring comparison](../2026-04-22-nvtop-vs-dcgm-exporter-vs-netdata-self-hosted-gpu-monitoring-guide-2026/). And for hardware-level time accuracy, our [bare-metal monitoring guide](../2026-04-23-self-hosted-bare-metal-hardware-monitoring-ipmi-redfish-openbmc-guide-2026/) covers IPMI and Redfish time sync monitoring.

## FAQ

### What is the difference between NTP and chrony?

NTP (Network Time Protocol) is the protocol itself. chrony is an NTP daemon — an implementation of the protocol. chrony is the default NTP client on many modern Linux distributions, replacing the older ntpd. NTPsec is a security-hardened fork of the original ntpd.

### How accurate does NTP need to be for production systems?

For most production workloads, within 100ms of authoritative time is acceptable. Financial trading and scientific computing may require sub-millisecond accuracy (using PTP instead of NTP). Authentication systems like Kerberos typically tolerate offsets up to 5 minutes.

### How do I monitor NTP without Prometheus?

Use NTPsec's built-in ntpviz tool to generate HTML reports with graphs, or write cron scripts that parse `chronyc tracking` or `ntpq -p` output. Both approaches produce actionable metrics without external dependencies.

### What NTP offset threshold should trigger alerts?

A warning at 50ms and critical at 100ms offset is a good starting point for most infrastructure. For time-sensitive applications (databases, trading systems), lower thresholds (10ms warning, 50ms critical) may be appropriate.

### Can I run chrony_exporter without Docker?

Yes, chrony_exporter is a single Go binary. Install it directly on your host and run it as a systemd service. The Docker approach simplifies deployment but isn't required.

### Does chrony_exporter work with ntpd?

No, chrony_exporter specifically communicates with the chrony daemon via its control socket. For ntpd or NTPsec, use the built-in ntpviz tools or write exporters that parse `ntpq -p` output.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted NTP Monitoring: chrony_exporter vs NTPsec vs chronyc Dashboard Solutions",
  "description": "Monitor NTP time synchronization with chrony_exporter for Prometheus, NTPsec ntpviz for standalone reports, and chronyc for custom dashboards.",
  "datePublished": "2026-05-11",
  "dateModified": "2026-05-11",
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
