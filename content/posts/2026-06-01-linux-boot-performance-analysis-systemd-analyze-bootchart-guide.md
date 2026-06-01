---
title: "Self-Hosted Linux Boot Performance Analysis: systemd-analyze vs Bootchart2 vs systemd-boot-check"
date: "2026-06-01"
tags: ["linux", "system-administration", "performance", "boot", "systemd", "troubleshooting"]
draft: false
---

## Introduction

Server boot time matters more than most administrators realize. In cloud environments with auto-scaling groups, every second of boot latency delays capacity response. In bare-metal deployments, slow boots extend maintenance windows and increase downtime. Linux provides several powerful tools for diagnosing and optimizing the boot process — but each takes a fundamentally different approach.

This guide compares three self-hosted boot analysis tools: **systemd-analyze** (the built-in systemd profiler), **Bootchart2** (the visual boot sequence analyzer), and **systemd-boot-check** (the automated boot health validator). We cover installation, configuration, and how to interpret their output to reduce your server boot time.

## Comparison Table

| Feature | systemd-analyze | Bootchart2 | systemd-boot-check |
|---------|----------------|------------|-------------------|
| **Package** | Built into systemd | `bootchart2` (apt/yum) | Custom script / monitoring |
| **Output Format** | Text + SVG plot | SVG/PNG charts | Exit codes + logs |
| **Data Source** | systemd journal | procfs + sysfs sampling | systemd unit states |
| **Overhead** | Near-zero | ~2% CPU during boot | Near-zero |
| **Visualization** | CLI text + blame graph | Full Gantt/CPU/Disk charts | Summary only |
| **Automation-Friendly** | Yes (JSON output) | Partial (SVG files) | Yes (exit codes) |
| **Best For** | Quick profiling | Deep visual analysis | CI/CD health checks |
| **History Required** | No | Requires boot data | No |
| **Resource Monitoring** | Time only | CPU, I/O, memory, processes | Unit state transitions |

## systemd-analyze: The Built-in Profiler

**systemd-analyze** is included with every modern Linux distribution running systemd. It requires no installation — just run it.

### Installation

No installation needed on any systemd-based system (Ubuntu 16.04+, Debian 8+, CentOS 7+, RHEL 7+, Fedora 15+).

### Key Commands

```bash
# Total boot time
systemd-analyze

# Per-unit blame list (sorted by time)
systemd-analyze blame

# Critical chain visualization
systemd-analyze critical-chain

# Generate SVG plot of boot sequence
systemd-analyze plot > boot.svg

# Check for security issues in units
systemd-analyze security

# Verify unit files
systemd-analyze verify /etc/systemd/system/myapp.service

# Dot dependency graph
systemd-analyze dot --order --require | dot -Tsvg > deps.svg
```

### Practical Boot Optimization Example

On a typical cloud VM, systemd-analyze reveals common bottlenecks:

```bash
$ systemd-analyze
Startup finished in 2.834s (kernel) + 8.243s (userspace) = 11.077s

$ systemd-analyze blame | head -5
5.123s networkd-dispatcher.service
2.891s containerd.service
1.924s cloud-init.service
1.540s snapd.service
 842ms docker.service
```

To disable unnecessary services causing boot delay:

```bash
# Mask the slow service if not needed
sudo systemctl mask networkd-dispatcher.service

# Or reduce timeouts
sudo mkdir -p /etc/systemd/system/containerd.service.d
cat << 'CFG' | sudo tee /etc/systemd/system/containerd.service.d/timeout.conf
[Service]
TimeoutStartSec=30s
CFG
sudo systemctl daemon-reload
```

### Integration with Monitoring

For cron-based monitoring, parse the JSON output:

```bash
#!/bin/bash
# Save to /etc/cron.hourly/boot-check
THRESHOLD=15000000000  # 15 seconds in microseconds
BOOT_TIME=$(systemd-analyze time --json=pretty | jq -r '.userspace')
if [ "$BOOT_TIME" -gt "$THRESHOLD" ]; then
    echo "WARNING: Boot time $BOOT_TIME exceeds threshold" |         systemd-cat -t boot-monitor -p warning
fi
```

## Bootchart2: Visual Boot Analysis

**Bootchart2** captures detailed system resource usage during the entire boot process and renders it as comprehensive charts. Unlike systemd-analyze which reports timing only, Bootchart2 shows CPU utilization, disk I/O, and process creation during boot.

### Installation

```bash
# Debian/Ubuntu
sudo apt install bootchart2

# RHEL/Fedora
sudo dnf install bootchart2

# The data collector runs automatically on next boot
# Charts are generated in /var/log/bootchart/
```

### Docker-Based Deployment (Headless Server)

For servers without a display, deploy Bootchart2 with a web viewer:

```yaml
version: "3.8"
services:
  bootchart-viewer:
    image: nginx:alpine
    container_name: bootchart-viewer
    ports:
      - "8080:80"
    volumes:
      - /var/log/bootchart:/usr/share/nginx/html/boot:ro
    restart: unless-stopped
```

Access your boot charts at `http://server-ip:8080/boot/`.

### Enabling Bootchart2 Persistently

```bash
# Edit GRUB to enable bootchart on every boot
sudo sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="[^"]*/& initcall_debug log_buf_len=16M/' /etc/default/grub
sudo update-grub
```

### Interpreting Bootchart2 Output

The generated chart includes:
- **CPU utilization** — Shows which processes consume CPU during boot
- **Disk throughput** — Identifies I/O bottlenecks from slow storage
- **Process tree** — Visualizes service start ordering and dependencies
- **Memory usage** — Tracks memory pressure during initialization

A bootchart showing high I/O wait during `containerd.service` startup suggests moving container storage to faster disks or using overlay2 with SSDs.

## systemd-boot-check: Automated Boot Health

**systemd-boot-check** is a lightweight validation script (not a separate package) that verifies your system boots cleanly by checking for failed units, long-running services, and timeout warnings.

### Setup Script

Create this validation system as a systemd service:

```bash
sudo tee /etc/systemd/system/boot-health-check.service << 'UNIT'
[Unit]
Description=Boot Health Check
After=multi-user.target
Wants=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/boot-health-check.sh
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
UNIT

sudo tee /usr/local/bin/boot-health-check.sh << 'SCRIPT'
#!/bin/bash
FAILED=0

# Check for failed units
FAILED_UNITS=$(systemctl --failed --no-legend | wc -l)
if [ "$FAILED_UNITS" -gt 0 ]; then
    echo "FAIL: $FAILED_UNITS failed units detected"
    systemctl --failed --no-legend
    FAILED=1
fi

# Check boot time
BOOT_SEC=$(systemd-analyze | awk '{print $NF}' | sed 's/s$//')
if (( $(echo "$BOOT_SEC > 30" | bc -l) )); then
    echo "WARN: Boot took ${BOOT_SEC}s (>30s threshold)"
    FAILED=1
fi

# Check for timeout warnings in journal
if journalctl -b -p warning | grep -qi "timeout"; then
    echo "WARN: Timeout warnings found in journal"
    FAILED=1
fi

exit $FAILED
SCRIPT

sudo chmod +x /usr/local/bin/boot-health-check.sh
sudo systemctl daemon-reload
sudo systemctl enable boot-health-check.service
```

### Prometheus Integration

Expose boot metrics for monitoring:

```bash
# Install node_exporter textfile collector
sudo tee /etc/cron.hourly/boot-metrics << 'CRON'
#!/bin/bash
BOOT_TIME=$(systemd-analyze | awk -F'= ' '{print $2}' | sed 's/s$//' || echo 0)
FAILED=$(systemctl --failed --no-legend | wc -l)
cat > /var/lib/node_exporter/boot.prom << EOF
node_boot_time_seconds $BOOT_TIME
node_boot_failed_units $FAILED
EOF
CRON
sudo chmod +x /etc/cron.hourly/boot-metrics
```

## Choosing the Right Tool

| Use Case | Recommended Tool |
|----------|-----------------|
| Quick boot time check | systemd-analyze time |
| Identifying slow services | systemd-analyze blame |
| Visual bottleneck analysis | Bootchart2 |
| Automated CI/CD validation | systemd-boot-check |
| Security auditing of units | systemd-analyze security |
| Long-term boot trend tracking | Prometheus + boot-check |

## Why Self-Host Your Boot Performance Monitoring?

Boot performance monitoring is one of the most overlooked aspects of server management. Unlike application-level monitoring which gets abundant tooling, the critical seconds between kernel handoff and service readiness remain a blind spot for many teams. Self-hosting these tools means you control the data, can integrate boot health checks into your existing monitoring stack, and can catch regressions before they impact production.

For broader system performance insights, see our [self-hosted I/O scheduler comparison](../2026-05-22-self-hosted-linux-io-schedulers-bfq-mq-deadline-kyber-guide/) and [kernel tuning guide](../2026-06-01-linux-kernel-tuning-sysctl-tuned-systool-guide/).

When boot issues stem from storage bottlenecks, our [Linux software RAID management guide](../2026-05-23-linux-software-raid-management-mdadm-vs-btrfs-vs-zfs-guide/) covers optimizing the storage layer. For CPU-specific tuning, the [CPU governor comparison](../2026-05-22-self-hosted-linux-cpu-governor-management-auto-cpufreq-cpupower-tuned-guide/) complements boot analysis well.

### Integration with CI/CD Pipelines

Boot performance testing can be integrated into your deployment pipeline. After each kernel or systemd update, run a validation build in a test VM that measures boot time and compares it against baseline. A regression of more than 20 percent should block the deployment. Tools like Packer and Vagrant can create disposable test VMs that run systemd-analyze and Bootchart2, capture the results as build artifacts, and fail the pipeline if boot time exceeds the threshold. This practice catches boot regressions from package updates before they reach production servers.

## FAQ

### How much does systemd-analyze overhead affect boot time?

Virtually zero. systemd-analyze reads existing journal data collected during boot — it does not add instrumentation. The data is always collected by systemd regardless of whether you run the analysis tool.

### Can I use Bootchart2 in a CI/CD pipeline?

Yes. Bootchart2 can run in ephemeral CI environments. Configure your CI runner to install bootchart2, reboot the test VM, and collect charts from `/var/log/bootchart/`. The SVG output can be archived as build artifacts for comparison across commits.

### Why is my kernel boot time so much longer than userspace?

Kernel boot time (shown by systemd-analyze) includes hardware initialization, driver loading, and filesystem mounting. Long kernel times often indicate slow storage controllers, USB enumeration delays, or network PXE timeout waits. Check `dmesg` timestamps to identify the specific phase.

### Does systemd-boot-check work on non-systemd systems?

No. The boot-health-check approach relies on systemd units, journal, and systemctl. For OpenRC or runit-based systems, you would need equivalent init-system-specific checks such as inspecting `/var/log/rc.log` on OpenRC hosts.

### Can I reduce boot time by running services in parallel?

systemd already parallelizes service startup based on dependency ordering. Use `systemd-analyze critical-chain` to see the serialization path. If a service blocks many others, consider using socket activation via `systemd.socket` units so dependent services can start before the main daemon is fully ready.

---

**We want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — it is the largest prediction market platform globally, from election results to technology regulation timelines, you can bet on anything. Unlike gambling, this is a true information market: the more you know, the higher your win rate. I have made good returns predicting technology-related events. Sign up with my referral link: [Polymarket.com](https://polymarket.com/?r=fc8a0)**

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Boot Performance Analysis: systemd-analyze vs Bootchart2 vs systemd-boot-check",
  "description": "Compare three Linux boot performance analysis tools — systemd-analyze, Bootchart2, and systemd-boot-check — with setup guides, Docker Compose examples, and monitoring integration patterns.",
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
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>
