---
title: "Self-Hosted Linux I/O Priority Management: ionice vs cgroup io.weight vs ioprio_set"
date: "2026-05-23"
tags: ["linux", "system-administration", "performance", "io-priority"]
draft: false
---

I/O priority determines which processes get preferential access to disk bandwidth when multiple processes compete for storage throughput. On busy database servers running simultaneous backup jobs, log writes, and query workloads, unmanaged I/O priority can cause critical operations to stall behind bulk data transfers. This guide compares three approaches to Linux I/O priority management: **ionice** (per-process scheduling class), **cgroup v2 io.weight** (hierarchical I/O bandwidth allocation), and **ioprio_set** (programmatic syscall-based control).

## Understanding Linux I/O Scheduling Priority

Linux uses the Completely Fair Queuing (CFQ) I/O scheduler (or its modern successors like BFQ and mq-deadline) to manage disk access. Each process is assigned an I/O scheduling class and priority level that determines its position in the disk request queue.

There are three I/O scheduling classes:

| Class | Value | Description |
|-------|-------|-------------|
| **Idle** | 3 | Only gets I/O time when no other process needs it |
| **Best Effort** | 2 | Default class, priority levels 0-7 |
| **Real Time** | 1 | Highest priority, gets I/O before Best Effort processes |

| Feature | ionice | cgroup v2 io.weight | ioprio_set syscall |
|---------|--------|---------------------|-------------------|
| **Granularity** | Per-process | Per-cgroup hierarchy | Per-thread |
| **Scheduling** | Class + priority level | Weighted proportional | Class + priority level |
| **Persistence** | Per-launch | Persistent via cgroup config | Per-call |
| **Container Support** | Manual per-process | Native Docker/K8s support | Programmatic |
| **Hierarchical Control** | No | Yes | No |
| **BFQ Compatible** | Yes | Yes (io.weight) | Yes |
| **Setup Complexity** | Low | Medium | High (requires coding) |
| **Kernel Version** | 2.6.13+ | 5.0+ (cgroup v2) | 2.6.13+ |

## ionice — Per-Process I/O Priority

**ionice** sets or retrieves the I/O scheduling class and priority for processes. It is part of the util-linux package and works with any I/O scheduler that supports priority levels.

### Installation

```bash
# Debian/Ubuntu (usually pre-installed)
sudo apt install -y util-linux

# RHEL/CentOS/Fedora (usually pre-installed)
sudo dnf install -y util-linux
```

### Basic Usage

```bash
# Set Real Time priority (highest) for a process
sudo ionice -c 1 ./database-backup

# Set Best Effort priority 0 (highest within class)
sudo ionice -c 2 -n 0 ./critical-app

# Set Best Effort priority 7 (lowest within class)
sudo ionice -c 2 -n 7 ./log-compression

# Set Idle class (only runs when disk is idle)
sudo ionice -c 3 ./batch-report

# Change priority of running process (PID 1234)
sudo ionice -c 2 -n 0 -p 1234

# Check current I/O priority
ionice -p 1234
# Output: idle
```

### Common I/O Priority Patterns

```bash
# Database queries: Real Time priority
sudo ionice -c 1 ./postgres

# Backup jobs: Best Effort, low priority
sudo ionice -c 2 -n 6 ./pg_dump

# Log rotation: Idle class
sudo ionice -c 3 ./logrotate

# Bulk data import: Best Effort, medium priority
sudo ionice -c 2 -n 4 ./data-importer
```

### Docker Compose with ionice

```yaml
version: "3.8"
services:
  backup:
    image: postgres:16
    entrypoint: ["ionice", "-c", "2", "-n", "6"]
    command: ["pg_dump", "-U", "postgres", "mydb"]
    volumes:
      - ./backups:/backups
    restart: "no"
```

## cgroup v2 io.weight — Hierarchical I/O Bandwidth Allocation

**cgroup v2** introduces `io.weight` for proportional I/O bandwidth distribution across process groups. Unlike ionice which sets absolute priority levels, io.weight allocates I/O bandwidth proportionally based on weight values (1 to 10000, default 100).

### Setting Up cgroup v2 I/O Control

```bash
# Verify cgroup v2 is enabled
stat -fc %T /sys/fs/cgroup/
# Output: cgroup2fs

# Create a cgroup for high-priority I/O
sudo mkdir /sys/fs/cgroup/high-io
echo "1000" | sudo tee /sys/fs/cgroup/high-io/io.weight

# Create a cgroup for low-priority I/O
sudo mkdir /sys/fs/cgroup/low-io
echo "10" | sudo tee /sys/fs/cgroup/low-io/io.weight

# Move a process to high-priority cgroup
echo "1234" | sudo tee /sys/fs/cgroup/high-io/cgroup.procs

# Move a process to low-priority cgroup
echo "5678" | sudo tee /sys/fs/cgroup/low-io/cgroup.procs
```

### io.weight vs io.max

cgroup v2 provides two complementary I/O controls:

```bash
# io.weight: Proportional bandwidth (1-10000, default 100)
# Higher weight = more bandwidth share during contention
echo "500" | sudo tee /sys/fs/cgroup/database/io.weight

# io.max: Absolute I/O limits (max bytes/sec and max IOPS)
# Format: MAJOR:MINOR rbps=BYTES wbps=BYTES riops=N wiops=N
echo "8:0 rbps=104857600 wbps=52428800" | sudo tee /sys/fs/cgroup/backup/io.max
```

### Docker Native cgroup I/O Control

Docker supports cgroup v2 I/O limits natively:

```yaml
version: "3.8"
services:
  database:
    image: postgres:16
    deploy:
      resources:
        limits:
          # Device-specific I/O limits (Docker 20.10+)
          # Note: requires cgroup v2 and device-mapper storage driver
    # Or use systemd delegate for io.weight:
    environment:
      - CGROUP_IO_WEIGHT=500
```

### Systemd Service I/O Weight

systemd integrates with cgroup v2 for per-service I/O weighting:

```ini
# /etc/systemd/system/postgresql.service.d/override.conf
[Service]
# I/O weight (1-10000, default 100)
IOWeight=500

# Device-specific weight
IODeviceWeight=/dev/sda 800

# Absolute I/O limits
IOReadBandwidthMax=/dev/sda 100M
IOWriteBandwidthMax=/dev/sda 50M
```

```bash
sudo systemctl daemon-reload
sudo systemctl restart postgresql
```

## ioprio_set — Programmatic I/O Priority Control

The **ioprio_set** syscall provides programmatic control over I/O priority from within applications. It is the underlying mechanism that ionice uses, but calling it directly from code gives you dynamic priority adjustment based on runtime conditions.

### Using ioprio_set from C

```c
#include <stdio.h>
#include <unistd.h>
#include <sys/syscall.h>
#include <linux/ioprio.h>

// ioprio_set(class, classdata, pid)
// class: 1=RT, 2=BE, 3=IDLE
// classdata: 0-7 priority within class

int set_io_priority(int pid, int class, int priority) {
    return syscall(SYS_ioprio_set, 1, pid, (class << 13) | priority);
}

int main() {
    // Set Real Time priority for current process
    set_io_priority(0, 1, 0);
    
    // Set Best Effort priority 3 for PID 1234
    set_io_priority(1234, 2, 3);
    
    return 0;
}
```

Compile and run:

```bash
gcc -o io-priority io-priority.c
sudo ./io-priority
```

### Using ioprio_set from Python

```python
import ctypes
import os

libc = ctypes.CDLL("libc.so.6")

# ioprio_set syscall number
SYS_ioprio_set = 251  # x86_64

def set_io_priority(pid, ioclass, priority):
    """Set I/O priority using ioprio_set syscall."""
    ioprio = (ioclass << 13) | priority
    return libc.syscall(SYS_ioprio_set, 1, pid, ioprio)

# Set Best Effort priority 0 for current process
set_io_priority(0, 2, 0)

# Set Idle class for PID 1234
set_io_priority(1234, 3, 0)
```

### When to Use ioprio_set Directly

Direct syscall access is useful when:

- Your application needs to adjust I/O priority dynamically based on workload phase
- You are building a custom I/O scheduler or resource manager
- You need per-thread I/O priority (ionice works per-process only)
- You are developing a database engine with adaptive I/O scheduling

## Why Self-Host and Manage I/O Priority Locally?

Managing I/O priority on your own servers gives you fine-grained control over disk bandwidth allocation that shared cloud storage cannot provide. Cloud block storage typically uses QoS tiers (standard, premium, ultra) that apply uniformly to all processes on the instance.

On bare-metal servers with local NVMe or SAS storage, I/O priority management ensures that critical database writes are never delayed by bulk backup operations. Log-intensive applications benefit from assigning low I/O priority to log compression and archival tasks, keeping disk bandwidth available for active transaction processing.

For related storage optimization, see our [Linux I/O Schedulers comparison](../2026-05-22-self-hosted-linux-io-scheduler-bfq-mq-deadline-kyber-guide/) for disk scheduler selection and [Linux Compressed Swap guide](../2026-05-29-self-hosted-linux-compressed-swap-management-zram-generator-systemd-swap-zramd-guide/) for memory-I/O tradeoff management. Our [Linux Performance Profiling guide](../2026-05-22-self-hosted-linux-performance-profiling-perf-bcc-tools-sysstat-guide/) covers I/O bottleneck identification tools.

## Choosing the Right I/O Priority Tool

| Scenario | Recommended Tool |
|----------|-----------------|
| Simple per-process priority | ionice |
| Container orchestration | cgroup v2 io.weight |
| Dynamic runtime adjustment | ioprio_set syscall |
| Systemd service management | IOWeight in service unit |
| Database vs backup separation | ionice (database RT, backup Idle) |
| Multi-tenant server | cgroup v2 io.weight per tenant |
| Custom application logic | ioprio_set from application code |

## FAQ

### What is the difference between ionice and ioprio_set?

ionice is a command-line wrapper around the ioprio_set syscall. ionice sets I/O priority for a process at launch or for an existing process by PID. ioprio_set is the underlying Linux syscall that can be called from any programming language, enabling dynamic priority changes from within running applications based on workload conditions.

### Does cgroup v2 io.weight work with all I/O schedulers?

cgroup v2 io.weight works with the BFQ and mq-deadline I/O schedulers. It does not work with the `none` scheduler (typically used for NVMe devices that handle their own scheduling). To check your current scheduler: `cat /sys/block/sda/queue/scheduler`. If your device uses the `none` scheduler, use `io.max` for absolute limits instead of `io.weight`.

### Can I set I/O priority for kernel threads?

Yes, but with limitations. ionice can set priority for kernel threads using the `-p` flag with the kernel thread PID. However, many kernel threads ignore user-set I/O priority and use their own internal scheduling. For cgroup v2, moving kernel threads to a specific cgroup (via `cgroup.procs`) applies the cgroup I/O policy to them.

### What happens to I/O priority when a process forks?

Child processes inherit the I/O priority of their parent. If you launch a process with `ionice -c 1 ./parent`, any child processes spawned by `./parent` will also have Real Time I/O priority. To override this, the child must explicitly set its own priority or be moved to a different cgroup.

### How do I check the current I/O scheduler?

Run `cat /sys/block/<device>/queue/scheduler`. The active scheduler is shown in brackets: `[mq-deadline] none`. Common schedulers include `mq-deadline` (multi-queue deadline), `bfq` (Budget Fair Queuing), `kyber` (low-latency), and `none` (no scheduler, device handles ordering).

### Should I use ionice or cgroup v2 for container environments?

Use cgroup v2 io.weight for container environments. Docker and Kubernetes natively support cgroup resource controls, making it easier to set I/O limits and weights per container. ionice requires manual configuration inside each container or wrapping container entrypoint commands, which is less maintainable at scale.

### Does I/O priority affect SSD and NVMe performance?

Yes, but the impact differs from spinning disks. On SSDs and NVMe drives, I/O priority affects queue ordering rather than mechanical seek optimization. Higher priority requests are processed first in the device queue, reducing latency for critical operations. However, NVMe devices with many parallel queues may show less dramatic priority differentiation than traditional SATA SSDs.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux I/O Priority Management: ionice vs cgroup io.weight vs ioprio_set",
  "description": "Compare ionice, cgroup v2 io.weight, and ioprio_set syscall for Linux I/O priority management. Learn per-process scheduling, hierarchical bandwidth allocation, and programmatic I/O control.",
  "datePublished": "2026-05-23",
  "dateModified": "2026-05-23",
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
