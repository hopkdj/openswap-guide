---
title: "Self-Hosted NTP Time Synchronization Monitoring: chronyc, ntpstat, and ntpviz Guide 2026"
date: "2026-05-07"
tags: ["comparison", "guide", "self-hosted", "ntp", "time-synchronization", "monitoring", "infrastructure"]
draft: false
---

Accurate time synchronization is a silent but critical dependency for every distributed system. From database transaction ordering to TLS certificate validation, log correlation, and distributed consensus protocols — everything breaks when clocks drift. Yet most infrastructure teams only discover time drift issues during an outage, when correlating logs across servers reveals timestamp mismatches.

In this guide, we cover three essential self-hosted tools for monitoring and diagnosing NTP (Network Time Protocol) synchronization: **chronyc** (the chrony control program), **ntpstat** (a simple sync status checker), and **ntpviz** (the NTP visualization toolkit from ntpsec). Unlike general monitoring platforms, these tools focus specifically on time synchronization accuracy, stratum levels, offset tracking, and peer health.

## Overview Comparison

| Feature | chronyc | ntpstat | ntpviz |
|---|---|---|---|
| **Package** | chrony | ntpstat (standalone) | ntpsec |
| **GitHub Stars** | N/A (part of chrony) | 160+ | Part of ntpsec |
| **NTP Daemon** | chronyd | Works with ntpd or chronyd | ntpd (ntpsec) |
| **Output Type** | CLI (interactive) | CLI (single-line) | HTML reports + graphs |
| **Visual Reports** | ASCII tables | No | HTML + gnuplot charts |
| **Best For** | Active monitoring & debugging | Quick health checks | Historical analysis & reports |
| **Data Collection** | Real-time queries | Current status snapshot | Log-based analysis |

## chronyc: The chrony Control Interface

[chrony](https://github.com/mlichvar/chrony) is the default NTP implementation on most modern Linux distributions (RHEL, Fedora, Ubuntu, Debian). Its companion CLI tool, `chronyc`, provides real-time access to the chrony daemon's internal state — including peer statistics, clock drift measurements, and synchronization accuracy.

### Key Commands

```bash
# Check synchronization status
chronyc tracking
# Returns: Reference ID, stratum, system time, last offset, RMS offset

# List all NTP peers and their health
chronyc sources -v
# Shows reachability, last/average offset, jitter

# Display peer statistics with graphical indicators
chronyc sourcestats -v
# Shows drift rate and sample count per peer

# Check if time is synchronized
chronyc activity
# Shows number of online/offline/burst sources
```

### Example Output

```
$ chronyc tracking
Reference ID    : A9FEA901 (ntp.ubuntu.com)
Stratum         : 3
Ref time (UTC)  : Wed May 07 12:30:45 2026
System time     : 0.000123456 seconds fast of NTP time
Last offset     : +0.000089234 seconds
RMS offset      : 0.000156789 seconds
Last offset duration: 64.000 seconds
Leap status     : Normal
```

### Docker-Based chrony Server Setup

```yaml
services:
  chrony:
    image: cturra/ntp:latest
    ports:
      - "123:123/udp"
    environment:
      - NTP_SERVERS=0.pool.ntp.org,1.pool.ntp.org,2.pool.ntp.org
      - LOG_LEVEL=info
    cap_add:
      - SYS_TIME
    restart: unless-stopped
```

### Monitoring chrony with Prometheus

```bash
# Export chrony metrics to Prometheus
apt-get install chrony prometheus-node-exporter

# chrony exposes metrics via the node_exporter's textfile collector
cat > /etc/prometheus/node-exporter/chrony.prom << 'EOF'
# HELP chrony_sync_state NTP synchronization state (0=unsynced, 1=synced)
chrony_sync_state 1
# HELP chrony_offset_seconds Current time offset in seconds
chrony_offset_seconds 0.00012
# HELP chrony_stratum NTP stratum level
chrony_stratum 3
EOF
```

## ntpstat: Quick Synchronization Health Check

[ntpstat](https://github.com/ericabramson/ntpstat) is a lightweight utility that returns a single-line summary of NTP synchronization status, making it ideal for monitoring scripts, alerting systems, and health checks.

### Usage

```bash
# Check sync status (returns exit code 0 if synced)
ntpstat
# Output: "synchronized to NTP server (192.168.1.1) at stratum 3"
#         "time correct to within 50 ms"
#         "polling server every 64 s"

# Use in monitoring scripts
if ntpstat; then
    echo "OK: Time is synchronized"
else
    echo "CRITICAL: Time is NOT synchronized"
    exit 2
fi
```

### Integration with Monitoring Systems

```bash
# Nagios/Icinga check script
#!/bin/bash
ntpstat > /dev/null 2>&1
exit_code=$?

case $exit_code in
    0) echo "OK - NTP synchronized"; exit 0 ;;
    1) echo "WARNING - NTP unsynchronized"; exit 1 ;;
    2) echo "CRITICAL - NTP contact lost"; exit 2 ;;
    *) echo "UNKNOWN - ntpstat returned $exit_code"; exit 3 ;;
esac
```

### Installing ntpstat

```bash
# Debian/Ubuntu
apt-get install ntpstat

# RHEL/CentOS/Fedora
dnf install ntpstat

# Build from source
git clone https://github.com/ericabramson/ntpstat.git
cd ntpstat
make
sudo make install
```

## ntpviz: Historical NTP Performance Visualization

[ntpviz](https://gitlab.com/NTPsec/ntpsec) is part of the ntpsec project — a security-hardened fork of the classic NTP daemon. The `ntpviz` tool parses NTP daemon statistics logs and generates comprehensive HTML reports with graphs showing offset trends, jitter patterns, peer reachability, and frequency drift over time.

### Generating Reports

```bash
# Collect stats (ensure ntpd is logging statistics)
# Add to /etc/ntp.conf:
# statsdir /var/log/ntpstats/
# statistics loopstats peerstats clockstats
# filegen loopstats file loopstats type day enable

# Generate a visualization report
ntpviz -l /var/log/ntpstats -d 7 -o /var/www/ntp-report
# Creates HTML files with 7 days of NTP performance data
```

### Key Visualizations

```bash
# Show local clock frequency drift over 30 days
ntpviz -l /var/log/ntpstats -g local-freq

# Plot offset against all peers over 14 days
ntpviz -l /var/log/ntpstats -p peer-offset -d 14

# Generate a complete site with all charts
ntpviz -l /var/log/ntpstats -d 30 -s all -o /var/www/html/ntp
```

### Nginx Configuration for NTP Reports

```nginx
server {
    listen 80;
    server_name ntp-monitor.internal;

    root /var/www/html/ntp;
    index index.html;

    location / {
        autoindex on;
    }
}
```

## Why Monitor NTP Synchronization?

Time synchronization is one of those infrastructure concerns that goes unnoticed until something catastrophic happens. A few milliseconds of clock drift can cascade into serious problems across your stack.

**Database consistency:** Distributed databases like CockroachDB, YugabyteDB, and MongoDB rely on accurate timestamps for transaction ordering and conflict resolution. Clock skew between nodes can cause write conflicts, split-brain scenarios, and data loss.

**Security and authentication:** TLS certificates, Kerberos tickets, and OAuth tokens all have validity windows. If a server's clock drifts even a few minutes, authentication will fail. Two-factor authentication (TOTP) also requires synchronized time to generate valid codes.

**Log correlation and incident response:** When troubleshooting an outage across multiple services, correlated timestamps are essential. A 30-second clock skew between your application server and database server can make it impossible to determine causation from logs.

**Distributed consensus:** Protocols like Raft, Paxos, and leader election algorithms depend on bounded clock drift. Excessive drift can cause false leader timeouts, unnecessary elections, and cluster instability.

For related infrastructure monitoring topics, see our [container monitoring guide](../2026-04-28-cadvisor-vs-dozzle-vs-netdata-self-hosted-docker-container-monitoring-guide-2026/), [endpoint monitoring tools](../gatus-vs-blackbox-exporter-vs-smokeping-self-hosted-endpoint-monitorin/), and [UPS monitoring guide](../2026-05-04-nut-vs-apcupsd-self-hosted-ups-monitoring-power-management-guide/).

## FAQ

### What is an acceptable NTP offset for production servers?
For most production workloads, an offset of less than 100 milliseconds is acceptable. For distributed databases and financial trading systems, aim for under 10 milliseconds. chrony typically achieves sub-millisecond accuracy on modern hardware with good network connectivity to NTP servers.

### Should I use chrony or ntpd?
chrony is the recommended choice for most modern Linux distributions. It converges faster than ntpd, handles intermittent network connections better, and provides more accurate timekeeping on virtual machines. ntpd (via ntpsec) is preferred when you need ntpviz-style historical reporting or legacy NTP compatibility.

### How often does chrony poll NTP servers?
chrony uses an adaptive polling interval that ranges from 64 seconds to 1024 seconds (about 17 minutes). When synchronization is stable, it polls less frequently. After a reboot or when it detects clock drift, it polls more aggressively. You can override this with `minpoll` and `maxpoll` settings in `/etc/chrony.conf`.

### Can I use ntpstat in an automated monitoring pipeline?
Yes, ntpstat is designed for scripting. It returns exit code 0 when synchronized, 1 when unsynchronized, and 2 when it cannot contact the NTP daemon. This makes it ideal for Nagios/Icinga checks, cron-based monitoring scripts, or Prometheus blackbox-exporter probes.

### How do I set up a local NTP server for my network?
Install chrony on a dedicated server, configure it to sync with upstream pool servers, and allow client connections in `/etc/chrony.conf` using `allow 192.168.0.0/16`. Point all internal servers to this local NTP server. This reduces external NTP traffic and provides faster sync for internal machines.

### What happens when an NTP server goes offline?
chrony maintains a list of multiple NTP peers and will automatically switch to the best available source. It also remembers the last measured drift rate and can continue correcting the local clock for hours even when all peers are unreachable. Use `chronyc sources` to see which peers are reachable.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted NTP Time Synchronization Monitoring: chronyc, ntpstat, and ntpviz Guide 2026",
  "description": "Monitor and diagnose NTP time synchronization using chronyc, ntpstat, and ntpviz — essential tools for maintaining accurate clocks across your infrastructure.",
  "datePublished": "2026-05-07",
  "dateModified": "2026-05-07",
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
