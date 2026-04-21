---
title: "vnStat vs nethogs vs iftop: Best Self-Hosted Bandwidth Monitoring Tools 2026"
date: 2026-04-21
tags: ["comparison", "guide", "self-hosted", "monitoring", "bandwidth", "network"]
draft: false
description: "Compare the best self-hosted bandwidth monitoring tools: vnStat for long-term historical tracking, nethogs for per-process analysis, and iftop for real-time connection monitoring. Installation guides and Docker configs included."
---

Every server administrator eventually needs to answer the question: *what is consuming my bandwidth?* Whether you're running a home lab, managing a VPS with capped data transfer, or troubleshooting network performance on production infrastructure, having reliable bandwidth monitoring tools is essential.

Unlike full network traffic analysis platforms like Zeek or ntopng (which we covered in our [network traffic analysis guide](../self-hosted-network-traffic-analysis-zeek-arkime-ntopng-guide-2026/)), bandwidth monitoring tools are lightweight, focused utilities that give you quick answers about data transfer volume, per-process consumption, and active connection throughput. In this guide, we compare three of the most widely used open-source bandwidth monitoring tools for Linux and examine when to use each one.

## Why Monitor Bandwidth on Self-Hosted Servers

Bandwidth monitoring serves several practical purposes:

- **Cost control** — Cloud providers charge for egress traffic. Knowing which services consume the most data helps optimize costs.
- **Capacity planning** — Historical bandwidth data reveals trends and helps you decide when to upgrade network interfaces or links.
- **Troubleshooting** — When a server suddenly slows down, identifying which process or connection is saturating the network is the first step in resolution.
- **Security awareness** — Unexpected outbound traffic spikes can indicate compromised systems, misconfigured backups, or data exfiltration.
- **Compliance and billing** — Some hosting agreements include bandwidth caps. Monitoring helps you stay within limits and avoid overage charges.

The three tools we cover here — **vnStat**, **nethogs**, and **iftop** — each solve a different part of this puzzle. vnStat provides long-term historical records, nethogs shows per-process bandwidth usage, and iftop displays real-time connection-level throughput. For comprehensive network monitoring that goes beyond bandwidth, tools like Netdata and LibreNMS offer broader infrastructure visibility — see our [network monitoring comparison](../zabbix-vs-librenms-vs-netdata-network-monitoring-guide/) for a deeper dive.

## vnStat: Long-Term Historical Bandwidth Tracking

[vnStat](https://github.com/vergoh/vnstat) is a console-based network traffic monitor for Linux and BSD that keeps a persistent log of network traffic history. First released in 2004, it is one of the most mature bandwidth monitoring tools available.

**Key characteristics:**

| Feature | Details |
|---------|---------|
| GitHub stars | 1,703+ |
| Last updated | April 2026 |
| Language | C |
| License | GPL-2.0 |
| Database | SQLite (persistent) |
| Resource usage | Near-zero (runs as daemon) |

### How vnStat Works

vnStat uses the Linux kernel's `/proc/net/dev` or `/sys/class/net/` interfaces to read byte counters. It stores this data in a SQLite database (or flat file for older versions), enabling historical queries across days, months, and even years. The daemon runs in the background with minimal resource overhead — typically under 1 MB of RAM.

### Installing vnStat

**On Debian/Ubuntu:**

```bash
sudo apt update
sudo apt install vnstat
```

**On RHEL/CentOS/Fedora:**

```bash
sudo dnf install vnstat   # Fedora
sudo yum install vnstat   # CentOS/RHEL (EPEL required)
```

### Running vnStat as a Docker Container

For containerized deployments, use the LinuxServer.io image which packages vnStat with all dependencies:

```yaml
version: "3.8"
services:
  vnstat:
    image: lscr.io/linuxserver/vnstat:latest
    container_name: vnstat
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
      - INTERFACE=eth0   # Change to your interface name
    network_mode: host
    volumes:
      - ./vnstat-config:/config
    restart: unless-stopped
```

Note: vnStat requires `network_mode: host` because it reads directly from `/proc/net/dev` and the host's network interfaces. This is a common pattern for tools that need access to kernel-level network statistics.

### Using vnStat

Once installed, vnStat runs as a daemon (`vnstatd`) that samples traffic every 5 seconds. Query the data using the `vnstat` command:

```bash
# Summary of all interfaces
vnstat

# Show daily traffic for interface eth0
vnstat -d -i eth0

# Show monthly traffic
vnstat -m -i eth0

# Show top 10 days by traffic volume
vnstat --top10 -i eth0

# Show traffic for the last 24 hours
vnstat -h -i eth0

# JSON output for scripting/API integration
vnstat --json -i eth0
```

### vnStat Configuration

The configuration file is typically at `/etc/vnstat.conf`. Key settings include:

```ini
# /etc/vnstat.conf

# Interface to monitor (leave empty for auto-select)
Interface "eth0"

# Database directory
DatabaseDir "/var/lib/vnstat"

# Output style (0=minimal, 1=bar, 2=bar+rate, 3=rate column)
OutputStyle 3

# Use bits instead of bytes for rate display
RateUnit 1

# Enable hourly traffic tracking
HourlySectionStyle 2
```

After editing the config, restart the daemon:

```bash
sudo systemctl restart vnstat
```

## nethogs: Per-Process Bandwidth Monitoring

[nethogs](https://github.com/raboof/nethogs) is a small "net top" tool that groups bandwidth by process rather than by protocol or subnet. Unlike most Linux networking utilities that break down traffic per protocol or subnet, nethogs shows exactly *which application* is using your bandwidth.

**Key characteristics:**

| Feature | Details |
|---------|---------|
| GitHub stars | 3,612+ |
| Last updated | February 2026 |
| Language | C++ |
| License | GPL-2.0 |
| Database | None (real-time only) |
| Resource usage | Low (requires root) |

### How nethogs Works

nethogs uses Linux's `/proc/net/tcp` and `/proc/net/tcp6` to map network connections to process IDs via the inode matching technique. It then reads `/proc/[pid]/cmdline` to display the executable name. This approach requires root privileges since it reads from `/proc` entries owned by all processes.

### Installing nethogs

**On Debian/Ubuntu:**

```bash
sudo apt update
sudo apt install nethogs
```

**On RHEL/CentOS/Fedora:**

```bash
sudo dnf install nethogs
```

**From source:**

```bash
git clone https://github.com/raboof/nethogs.git
cd nethogs
sudo apt install libncurses5-dev libpcap-dev
make
sudo make install
```

### Running nethogs

```bash
# Monitor all interfaces (requires root)
sudo nethogs

# Monitor a specific interface
sudo nethogs eth0

# Refresh interval in seconds (default: 1)
sudo nethogs -d 5 eth0

# Monitor multiple interfaces
sudo nethogs eth0 wlan0

# Trace mode (show individual connections)
sudo nethogs -t eth0

# Display bandwidth in KB/s instead of KB total
sudo nethogs -v 3 eth0
```

**Interactive controls while nethogs is running:**

| Key | Action |
|-----|--------|
| `q` | Quit |
| `m` | Cycle through units (KB/s, KB, B, MB, MB/s) |
| `r` | Sort by received traffic |
| `s` | Sort by sent traffic |

### Docker Deployment

nethogs requires `CAP_NET_RAW` and `CAP_NET_ADMIN` capabilities, plus host network access:

```yaml
version: "3.8"
services:
  nethogs:
    image: ghcr.io/raboof/nethogs:latest
    container_name: nethogs
    network_mode: host
    cap_add:
      - NET_RAW
      - NET_ADMIN
    command: ["-d", "5", "eth0"]
    restart: unless-stopped
```

Note: The official GitHub repository does not publish Docker images. You may need to build from source or use community-built images from Docker Hub. A simple Dockerfile approach:

```dockerfile
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y nethogs
ENTRYPOINT ["nethogs"]
```

## iftop: Real-Time Connection-Level Bandwidth

[iftop](https://www.ex-parrot.com/pdw/iftop/) is a command-line system monitor that shows a top-like table of current network usage, grouped by source-destination pair. While it predates GitHub (first released in 2002), it remains one of the most widely installed bandwidth monitoring tools on Linux systems.

**Key characteristics:**

| Feature | Details |
|---------|---------|
| GitHub stars | 139+ (community mirror) |
| First release | 2002 |
| Language | C |
| License | GPL |
| Database | None (real-time only) |
| Resource usage | Low (requires root) |

### How iftop Works

iftop uses `libpcap` to capture packets and aggregates them by source/destination IP and port pairs. It displays a continuously updated table showing the bandwidth consumed by each connection pair over 2-second, 10-second, and 40-second averages.

### Installing iftop

**On Debian/Ubuntu:**

```bash
sudo apt update
sudo apt install iftop
```

**On RHEL/CentOS/Fedora:**

```bash
sudo dnf install iftop
# or on older systems:
sudo yum install iftop
```

**From source:**

```bash
sudo apt install libpcap-dev libncurses5-dev
wget https://www.ex-parrot.com/pdw/iftop/download/iftop-1.0pre4.tar.gz
tar xzf iftop-1.0pre4.tar.gz
cd iftop-1.0pre4
./configure
make
sudo make install
```

### Using iftop

```bash
# Monitor eth0 (requires root)
sudo iftop -i eth0

# Show port numbers alongside hosts
sudo iftop -i eth0 -P

# Disable hostname resolution (faster startup)
sudo iftop -i eth0 -n

# Set bandwidth limit for bar scaling (e.g., 100 Mbps)
sudo iftop -i eth0 -L 100M

# Display in bytes instead of bits
sudo iftop -i eth0 -B
```

**Interactive controls while iftop is running:**

| Key | Action |
|-----|--------|
| `q` | Quit |
| `n` | Toggle DNS resolution |
| `s` | Toggle source host display |
| `d` | Toggle destination host display |
| `t` | Cycle display mode (two-line, one-line, cumulative) |
| `p` | Toggle port display |
| `1/2/3` | Sort by 2s/10s/40s average |
| `j/k` | Scroll host list |

## Comparison: vnStat vs nethogs vs iftop

| Feature | vnStat | nethogs | iftop |
|---------|--------|---------|-------|
| **Primary purpose** | Historical tracking | Per-process usage | Per-connection throughput |
| **Time scope** | Months/years | Real-time only | Real-time only |
| **Data granularity** | Hourly/daily/monthly totals | Bytes per process | Bytes per connection pair |
| **Persistent storage** | SQLite database | None | None |
| **Resource usage** | Near-zero (daemon) | Low | Low |
| **Root required** | No (read-only `/proc`) | Yes | Yes (libpcap) |
| **Docker-friendly** | Yes (network_mode: host) | Partially (needs caps) | Partially (needs caps) |
| **Web interface** | Via vnStat CGI or third-party | No | No |
| **Best for** | Capacity planning, billing | Identifying bandwidth hogs | Real-time troubleshooting |
| **GitHub stars** | 1,703+ | 3,612+ | N/A (pre-GitHub project) |

## When to Use Each Tool

### Use vnStat When You Need Historical Data

vnStat is the go-to tool when you need to answer questions like:
- "How much data did we transfer last month?"
- "What is our average daily bandwidth usage?"
- "Is our traffic trending upward quarter over quarter?"

Its persistent database and low resource footprint make it ideal for always-on monitoring on production servers. Pair it with a simple cron job to export JSON reports for dashboards.

### Use nethogs When You Need to Find the Culprit

When your server's bandwidth is saturated and you need to know *which process* is responsible, nethogs is the answer. It is particularly useful for:
- Identifying runaway backup processes
- Finding misconfigured applications making excessive API calls
- Discovering unauthorized data transfers
- Monitoring Docker container bandwidth by process

### Use iftop When You Need Connection-Level Detail

iftop excels at showing you *who* your server is talking to and how much data each connection consumes. Use it when:
- Investigating suspicious outbound connections
- Identifying which clients are downloading the most data
- Troubleshooting network latency between specific hosts
- Monitoring real-time transfer speeds during large file operations

## Combining All Three Tools

For comprehensive bandwidth visibility, use all three tools together:

1. **vnStat** runs continuously as a daemon, building a historical record
2. **nethogs** is invoked on-demand when you need to pinpoint which process is consuming bandwidth
3. **iftop** is invoked on-demand when you need to see which remote hosts are involved in heavy transfers

For example, a typical investigation workflow:
1. Check vnStat to confirm a bandwidth spike occurred and when
2. Run iftop to see which connections are active right now
3. Run nethogs to identify which local processes own those connections

## Automating Bandwidth Monitoring

### vnStat Cron-Based Export

For automated reporting, set up a cron job to export vnStat data:

```bash
# Add to crontab: daily bandwidth report at 6 AM
0 6 * * * vnstat --json > /var/log/vnstat/daily-$(date +\%Y-\%m-\%d).json

# Weekly summary email
0 7 * * 1 vnstat -w | mail -s "Weekly Bandwidth Report" admin@example.com
```

### nethogs Logging Script

Capture nethogs output to a log file for later analysis:

```bash
#!/bin/bash
# save-nethogs.sh
INTERFACE="eth0"
LOGDIR="/var/log/nethogs"
mkdir -p "$LOGDIR"

# Run nethogs in trace mode for 60 seconds, save output
sudo timeout 60 nethogs -t "$INTERFACE" > "$LOGDIR/nethogs-$(date +%Y%m%d-%H%M%S).log" 2>&1
```

### iftop with Threshold Alerting

Combine iftop with a wrapper script to alert on bandwidth thresholds:

```bash
#!/bin/bash
# check-bandwidth.sh
THRESHOLD_KB=50000  # 50 MB/s alert threshold

# Run iftop for 10 seconds, capture output
OUTPUT=$(sudo timeout 10 iftop -t -i eth0 -s 5 2>/dev/null)

# Check if any connection exceeds threshold
if echo "$OUTPUT" | grep -qP '(\d{6,})'; then
    echo "WARNING: High bandwidth detected on eth0" | \
        mail -s "Bandwidth Alert" admin@example.com
fi
```

For organizations that need even deeper network visibility beyond bandwidth, tools like Zeek and Arkime provide full packet capture and protocol analysis. Check our [detailed comparison of network traffic analysis tools](../self-hosted-network-traffic-analysis-zeek-arkime-ntopng-guide-2026/) for guidance on those platforms.

## FAQ

### Can vnStat, nethogs, and iftop monitor Docker container bandwidth?

vnStat monitors all traffic on a network interface, which includes Docker container traffic when using `network_mode: host` or bridge networking. nethogs can identify Docker processes by their container names when run from the host. iftop shows IP-level connections, which includes container IPs. For dedicated Docker network monitoring, consider using cgroup-based tools or Docker's built-in `docker stats` command.

### Do these tools work on cloud servers (AWS, GCP, Azure)?

Yes, all three tools work on cloud virtual machines. vnStat is particularly useful on cloud instances to track egress traffic, which is often billable. Note that some cloud environments use virtualized network interfaces (e.g., `ens5` on GCP, `eth0` on AWS EC2) — specify the correct interface name when running nethogs or iftop.

### Does vnStat count traffic from loopback interfaces?

By default, vnStat excludes loopback (`lo`) interface traffic. You can configure it to monitor any interface, including loopback, by setting `Interface ""` in the configuration file to auto-select, or explicitly naming the interface. For most use cases, you only want to monitor external-facing interfaces.

### Why do nethogs and iftop require root privileges?

Both tools need access to kernel-level network data that is restricted to the root user. nethogs reads `/proc/[pid]/fd/` to map connections to processes, which requires root. iftop uses `libpcap` to capture raw packets, which also requires elevated privileges. vnStat does not need root because it reads aggregate byte counters from `/proc/net/dev`, which is world-readable.

### Can I use vnStat data in Grafana or other dashboards?

Yes. vnStat supports JSON output (`vnstat --json`), which can be ingested by Grafana using the JSON API data source plugin. Alternatively, third-party tools like `vnstat-prometheus-exporter` expose vnStat metrics in Prometheus format, enabling native Grafana dashboards with PromQL queries.

### How accurate is vnStat compared to reading traffic directly from /proc/net/dev?

vnStat is essentially a wrapper around `/proc/net/dev` (or `/sys/class/net/`), so its data accuracy matches the kernel's byte counters. The only potential discrepancy is the 5-second sampling interval — very short traffic spikes between samples may be slightly undercounted. For most administrative purposes, the accuracy is more than sufficient.

### Can nethogs show bandwidth usage for specific ports or protocols?

nethogs groups by process, not by port or protocol. If you need port-level or protocol-level breakdowns, iftop is the better choice as it shows traffic grouped by source/destination IP and port pairs. For protocol-level analysis (HTTP, DNS, etc.), consider full packet capture tools like tcpdump or Wireshark.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "vnStat vs nethogs vs iftop: Best Self-Hosted Bandwidth Monitoring Tools 2026",
  "description": "Compare the best self-hosted bandwidth monitoring tools: vnStat for long-term historical tracking, nethogs for per-process analysis, and iftop for real-time connection monitoring. Installation guides and Docker configs included.",
  "datePublished": "2026-04-21",
  "dateModified": "2026-04-21",
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
