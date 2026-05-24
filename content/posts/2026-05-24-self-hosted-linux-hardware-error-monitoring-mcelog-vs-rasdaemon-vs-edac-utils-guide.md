---
title: "Self-Hosted Linux Hardware Error Monitoring: mcelog vs rasdaemon vs EDAC-utils"
date: "2026-05-24"
tags: ["hardware-monitoring", "ras", "mcelog", "rasdaemon", "edac", "server-management", "linux-admin"]
draft: false
---

Server hardware failures rarely happen without warning. ECC memory controllers, CPU caches, and motherboard chipsets continuously detect and log correctable errors — but unless you actively monitor these signals, a correctable error today becomes an uncorrectable crash tomorrow. Self-hosted Linux hardware error monitoring tools give administrators visibility into Reliability, Availability, and Serviceability (RAS) events before they escalate into outages.

In this guide, we compare three open-source tools for hardware error monitoring on Linux: **mcelog**, **rasdaemon**, and **EDAC-utils**. Each approaches RAS event collection and decoding differently, and choosing the right one depends on your architecture, error types, and monitoring stack.

## What Is Hardware Error Monitoring?

Modern server hardware includes extensive error detection capabilities built into the silicon. Memory controllers detect and correct single-bit ECC errors. CPU caches report correctable parity errors. PCIe subsystems log corrected AER (Advanced Error Reporting) events. Machine Check Architecture (MCA) on x86 processors captures a wide range of hardware faults.

Without active monitoring, these events silently accumulate in kernel ring buffers and dmesg logs until a catastrophic failure occurs. Hardware error monitoring tools decode these kernel-level RAS events into actionable information, enabling proactive hardware replacement before failures impact production workloads.

## mcelog: x86 Machine Check Exception Decoder

**mcelog** (Machine Check Exception log) is the traditional Linux tool for decoding x86-64 hardware errors. It runs as a daemon that periodically reads MCE records from the kernel's `/dev/mcelog` interface (or the newer ACPI APEI interface) and decodes them into human-readable reports.

**GitHub:** [andikleen/mcelog](https://github.com/andikleen/mcelog) -- 148 stars, last updated April 2026

### How mcelog Works

mcelog polls the kernel for new Machine Check Exception records at configurable intervals. Each MCE record contains detailed information about the error source -- which CPU core, which cache level, which memory address, and the error classification (corrected, uncorrected, fatal).

The tool decodes raw MCE data using Intel and AMD processor-specific decoding tables, translating hex-coded error registers into meaningful descriptions like "L2 cache corrected error" or "memory controller ECC error at address 0x...".

### Installation

```bash
# Debian/Ubuntu
sudo apt install mcelog

# RHEL/CentOS/Fedora
sudo dnf install mcelog

# Arch Linux
sudo pacman -S mcelog
```

### Docker Deployment

```yaml
version: "3.8"
services:
  mcelog:
    image: alpine:latest
    container_name: mcelog-monitor
    restart: unless-stopped
    privileged: true
    volumes:
      - /dev/mcelog:/dev/mcelog
      - /var/log/mcelog:/var/log/mcelog
      - ./mcelog.conf:/etc/mcelog.conf:ro
    entrypoint: ["/bin/sh", "-c"]
    command: |
      apk add --no-cache mcelog
      mcelog --syslog --ignorenodev
```

### Configuration Example

```ini
# /etc/mcelog.conf
poll-interval = 60
syslog = yes
logfile = /var/log/mcelog/mcelog.log
unrecognized = yes
memory-ce-threshold = 10
```

### Key Features

- Decodes x86 Machine Check Exceptions (Intel and AMD)
- Memory error tracking with address decoding
- CPU cache error classification (L1/L2/L3)
- Thermal event monitoring
- Integration with systemd journal
- Low overhead -- polls kernel every 60 seconds by default

### Limitations

- x86-only -- does not support ARM, PowerPC, or RISC-V
- Requires `/dev/mcelog` device (older kernels) or ACPI APEI (newer)
- No built-in alerting -- log analysis is manual
- Limited to MCE events -- does not cover EDAC memory controller errors

## rasdaemon: Comprehensive RAS Event Logger

**rasdaemon** is the most comprehensive open-source RAS monitoring tool available for Linux. Unlike mcelog's x86 MCE focus, rasdaemon captures errors from multiple kernel subsystems: EDAC memory controller events, MCE records, PCIe AER errors, memory failure events, and ext4 filesystem errors.

**GitHub:** [mchehab/rasdaemon](https://github.com/mchehab/rasdaemon) -- 310 stars, last updated March 2026

### How rasdaemon Works

rasdaemon hooks into the kernel's tracepoint infrastructure, subscribing to RAS-related trace events across multiple subsystems. It uses libtraceevent to parse kernel trace records and stores decoded events in a SQLite database for historical analysis.

The tool supports both realtime monitoring (daemon mode) and post-mortem analysis (reading existing kernel logs). It maintains a persistent database of all hardware errors, enabling trend analysis -- for example, identifying a DIMM slot that shows increasing correctable error rates over weeks.

### Installation

```bash
# Debian/Ubuntu
sudo apt install rasdaemon

# RHEL/CentOS/Fedora
sudo dnf install rasdaemon

# Build from source
git clone https://github.com/mchehab/rasdaemon.git
cd rasdaemon
./autogen.sh
./configure
make
sudo make install
```

### Docker Deployment

```yaml
version: "3.8"
services:
  rasdaemon:
    image: ubuntu:latest
    container_name: rasdaemon-monitor
    restart: unless-stopped
    privileged: true
    volumes:
      - /sys:/sys:ro
      - /dev:/dev
      - /var/lib/rasdaemon:/var/lib/rasdaemon
    entrypoint: ["/bin/sh", "-c"]
    command: |
      apt-get update && apt-get install -y rasdaemon sqlite3
      rasdaemon --enable_dimm --enable_aer --enable_mce --record
      tail -f /dev/null
```

### Configuration and Querying

```bash
# Enable all RAS event types
sudo rasdaemon --enable_dimm --enable_aer --enable_mce --record

# View current error summary
sudo ras-mc-ctl --summary

# Query specific DIMM errors
sudo ras-mc-ctl --dimm-info

# Export error history for analysis
sqlite3 /var/lib/rasdaemon/ras.db "SELECT * FROM mc_event ORDER BY timestamp DESC LIMIT 20;"

# View PCIe AER errors
sudo ras-mc-ctl --aer_stats
```

### Key Features

- Multi-subsystem coverage: EDAC, MCE, AER, memory failure, ext4 errors
- SQLite database for historical error tracking and trend analysis
- DIMM slot-level memory error identification
- PCIe Advanced Error Reporting (AER) decoding
- Supports x86, ARM64, and PowerPC architectures
- Prometheus exporter available
- ras-mc-ctl management utility for querying and reporting

### Limitations

- Requires kernel tracepoint support (CONFIG_TRACEPOINTS)
- SQLite database can grow on high-error systems
- More complex setup than mcelog
- Daemon requires privileged access to kernel tracepoints

## EDAC-utils: Kernel EDAC Subsystem Interface

**EDAC-utils** provides a userspace interface to the Linux kernel's Error Detection and Correction (EDAC) subsystem. EDAC is the kernel framework that exposes memory controller error data through sysfs (`/sys/devices/system/edac/`). EDAC-utils reads and interprets this data, providing commands for checking ECC memory status, memory controller health, and chipset error counts.

**GitHub:** [grondo/edac-utils](https://github.com/grondo/edac-utils) -- 53 stars, last updated July 2024

### How EDAC-utils Works

The Linux kernel's EDAC subsystem provides drivers for memory controllers across multiple chipset vendors (Intel, AMD, server chipsets). These drivers expose error counters and status information through sysfs. EDAC-utils reads these sysfs files and presents the information in human-readable format.

Unlike mcelog (which decodes MCE records) and rasdaemon (which subscribes to tracepoints), EDAC-utils works by polling sysfs files. This makes it simpler but less real-time than the alternatives.

### Installation

```bash
# Debian/Ubuntu
sudo apt install edac-utils

# RHEL/CentOS/Fedora
sudo dnf install edac-utils
```

### Docker Deployment

```yaml
version: "3.8"
services:
  edac-utils:
    image: alpine:latest
    container_name: edac-monitor
    restart: unless-stopped
    volumes:
      - /sys:/sys:ro
      - /proc:/proc:ro
    entrypoint: ["/bin/sh", "-c"]
    command: |
      apk add --no-cache edac-utils
      while true; do
        edac-util --report=all >> /var/log/edac.log 2>&1
        sleep 300
      done
```

### Key Commands

```bash
# View overall EDAC status
edac-util -v

# Report all errors
edac-util --report=all

# Check specific memory controller
edac-util --report=mc

# View DIMM-level error counts
edac-util --report=dimm
```

### Key Features

- Direct sysfs interface -- no kernel modules or tracepoints required
- DIMM-level error reporting with slot identification
- Memory controller status monitoring
- Chipset-specific error counters
- Simple, lightweight -- minimal resource usage
- Works on any architecture with EDAC kernel support

### Limitations

- Polling-based -- not real-time like tracepoint-driven tools
- Limited to EDAC events -- no MCE, AER, or ext4 error coverage
- Smaller feature set compared to rasdaemon
- Less active development

## Comparison Table

| Feature | mcelog | rasdaemon | EDAC-utils |
|---------|--------|-----------|------------|
| Architecture Support | x86/x86-64 only | x86, ARM64, PowerPC | Any with EDAC kernel |
| Error Types | MCE, memory, cache, thermal | EDAC, MCE, AER, memfail, ext4 | EDAC memory errors only |
| Data Collection | Polls /dev/mcelog | Kernel tracepoints | Polls sysfs |
| Storage | Syslog/log file | SQLite database | None (on-demand) |
| Historical Analysis | Limited | Full (SQLite queries) | None |
| DIMM Slot Mapping | Address-based | Slot-level with labels | Slot-level |
| PCIe AER | No | Yes | No |
| Prometheus Export | No | Yes (external) | No |
| Active Development | Yes (April 2026) | Yes (March 2026) | Limited (July 2024) |

## Why Self-Host Hardware Error Monitoring?

Server hardware failures are expensive -- both in downtime and data loss. Cloud providers handle hardware monitoring as part of their managed service, but self-hosted infrastructure requires proactive hardware health monitoring to prevent unexpected failures.

Running your own hardware error monitoring gives you direct visibility into ECC memory degradation, CPU cache errors, and PCIe bus faults. You can replace a failing DIMM before it causes data corruption, swap a degrading CPU before it triggers kernel panics, and identify failing PCIe cards before they disrupt network or storage traffic.

For homelab operators managing used enterprise servers, hardware error monitoring is essential. Refurbished server hardware often has accumulated wear that manifests as increasing correctable error rates -- trends only visible through persistent RAS event logging.

For datacenter operators running bare-metal infrastructure, RAS monitoring integrates with capacity planning and hardware lifecycle management. Historical error trends from rasdaemon's SQLite database enable predictive maintenance scheduling, reducing unplanned outages.

For related server monitoring topics, see our [BMC/IPMI monitoring guide](../2026-05-19-self-hosted-bmc-ipmi-monitoring-freeipmi-vs-ipmitool-vs-openbmc-guide/) for hardware management interfaces and our [kernel security auditing guide](../2026-05-23-linux-kernel-security-auditing-kconfig-hardened-check-checksec-guide/) for kernel configuration hardening.

## Choosing the Right Tool

**Use mcelog** if you run x86 servers and need lightweight MCE decoding without the overhead of a full RAS monitoring stack.

**Use rasdaemon** if you need comprehensive RAS coverage across multiple error types and architectures. Its SQLite database enables trend analysis and historical error tracking that mcelog and EDAC-utils cannot provide.

**Use EDAC-utils** if you only need memory controller error visibility and prefer a simple sysfs-based approach.

## FAQ

### What is the difference between correctable and uncorrectable memory errors?
Correctable errors (CE) are single-bit ECC errors that the memory controller can fix on the fly without data loss. Uncorrectable errors (UE) are multi-bit errors that cause data corruption and typically trigger a kernel panic. Monitoring correctable error rates helps predict which DIMMs are degrading before they produce uncorrectable failures.

### Does mcelog work on ARM servers?
No. mcelog is x86/x86-64 specific because it decodes Machine Check Architecture (MCE) records, which are an x86 feature. For ARM servers, use rasdaemon which supports ARM64 RAS events through the kernel tracepoint interface, or use EDAC-utils if your ARM platform has EDAC kernel driver support.

### How often should I check hardware error logs?
For production servers, configure continuous daemon-based monitoring (mcelog or rasdaemon running as services). For homelab or non-critical systems, a daily check via cron is sufficient. rasdaemon's SQLite database makes it easy to query error trends over any time period.

### Can I integrate hardware error monitoring with Prometheus?
Yes. rasdaemon has a community Prometheus exporter that exposes RAS event metrics for Grafana dashboards. For mcelog and EDAC-utils, you can write custom Node Exporter textfile collectors that parse log output and expose metrics.

### Do these tools work inside Docker containers?
All three tools can run in Docker containers with privileged mode and host volume mounts for `/dev/mcelog`, `/sys`, or `/var/lib/rasdaemon`. However, because they monitor host hardware, running them directly on the host OS (as systemd services) is the recommended deployment pattern.

### What happens when a DIMM shows increasing correctable errors?
Increasing correctable error rates indicate a degrading memory module. Most server vendors recommend replacing a DIMM when it exceeds a threshold of correctable errors (e.g., 10+ per hour). rasdaemon's historical database makes it easy to track error rates per DIMM slot over time, enabling data-driven replacement decisions.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Hardware Error Monitoring: mcelog vs rasdaemon vs EDAC-utils",
  "description": "Compare three open-source Linux hardware error monitoring tools for RAS event detection, decoding, and alerting on self-hosted servers.",
  "datePublished": "2026-05-24",
  "dateModified": "2026-05-24",
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
