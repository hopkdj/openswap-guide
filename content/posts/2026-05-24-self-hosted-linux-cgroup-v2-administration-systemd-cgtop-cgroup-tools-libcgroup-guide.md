---
title: "Self-Hosted Linux cgroup v2 Administration: systemd-cgtop vs cgroup-tools vs libcgroup (2026)"
date: "2026-05-24"
tags: ["cgroup", "linux", "containers", "systemd", "resource-management", "system-administration"]
draft: false
---

Linux control groups (cgroups) are the kernel feature that makes modern containerization possible. They partition system resources — CPU, memory, disk I/O, and network bandwidth — into isolated groups, ensuring that one process cannot monopolize the entire system. With cgroup v2, the Linux kernel introduced a unified hierarchy, improved resource accounting, and better support for modern workloads like containers and virtual machines.

For self-hosted server administrators, managing cgroups effectively is essential for resource allocation, troubleshooting, and ensuring fair scheduling across services. This guide compares three administration approaches: **systemd-cgtop** (real-time monitoring via systemd), **cgroup-tools** (command-line utilities), and **libcgroup** (the C library and legacy tools).

## Understanding cgroup v2 vs cgroup v1

cgroup v2 represents a fundamental redesign over v1:

| Feature | cgroup v1 | cgroup v2 |
|---------|-----------|-----------|
| Hierarchy | Multiple trees (one per controller) | Single unified tree |
| Controller Placement | Any level | Only at leaf nodes |
| Memory Accounting | Per-controller | Unified |
| I/O Control | blkio controller | io controller |
| CPU Control | cpu + cpuacct | cpu (unified) |
| Delegation | Complex | Clean (for containers) |
| BPF Integration | No | Yes (eBPF programs) |

Most modern distributions default to cgroup v2 (kernel 5.x+ with systemd 247+). You can check your system with:

```bash
# Check if cgroup v2 is mounted
stat -fc %T /sys/fs/cgroup/
# cgroup2fs = v2, tmpfs = v1

# Check which controllers are available
cat /sys/fs/cgroup/cgroup.controllers
# Output: cpu io memory pids rdma

# Verify unified hierarchy
mount | grep cgroup
```

## Tool Comparison at a Glance

| Feature | systemd-cgtop | cgroup-tools | libcgroup (cgexec) |
|---------|---------------|--------------|---------------------|
| Primary Role | Real-time monitoring | CLI administration | C library + legacy tools |
| Package | systemd | cgroup-tools (cgget, cgset) | libcgroup (cgexec, cgclassify) |
| Interactive UI | Yes (top-like) | No (command-line) | No |
| Resource Setting | No (view only) | Yes (cgset, cgcreate) | Yes (cgexec, cgclassify) |
| cgroup v2 Support | Full | Full | Partial (legacy tools) |
| Controller Management | systemd units only | Manual | Manual |
| Process Classification | Via systemd | cgclassify | cgclassify |
| Best For | Monitoring, overview | Fine-grained control | Legacy application support |
| Active Development | Active (systemd project) | Active (cgroup-tools) | Limited (maintenance) |
| GitHub | [systemd/systemd](https://github.com/systemd/systemd) (10,800+ ★) | [brauner/cgroup-tools](https://github.com/brauner/cgroup-tools) (community) | [libcg/libcgroup](https://github.com/libcg/libcgroup) (community) |

## systemd-cgtop: Real-Time Resource Monitoring

`systemd-cgtop` provides a top-like view of cgroup resource usage, making it the fastest way to see which services and containers are consuming system resources. It works with both cgroup v1 and v2 and integrates seamlessly with systemd's service management.

### Basic Usage

```bash
# Launch interactive monitoring
systemd-cgtop

# Key bindings in interactive mode:
# P - sort by CPU%
# M - sort by memory%
# I - sort by I/O
# T - sort by tasks
# Q - quit
# Space - force refresh

# One-shot output (for scripting)
systemd-cgtop -n 1
systemd-cgtop -b -n 1  # batch mode
```

### Understanding the Output

```
Control Group                           Tasks   %CPU   Memory  Input/s Output/s
/                                           1    12.3   1.8G       -        -
/system.slice                             45     8.1   890M       -        -
/system.slice/sshd.service                 3     0.1    12M       -        -
/system.slice/docker.service              22     5.2   650M       -        -
/user.slice                                8     2.1   340M       -        -
/user.slice/user-1000.slice               6     1.8   280M       -        -
```

Each row represents a cgroup. The hierarchy is shown through indentation, making it easy to see which services belong to which parent group. The unified cgroup v2 hierarchy means all resource controllers are visible in a single view.

### Integration with systemd Services

```bash
# Set resource limits via systemd unit files
# /etc/systemd/system/myapp.service
[Service]
CPUQuota=50%
MemoryMax=2G
IOWeight=100
TasksMax=100

# Apply and verify
systemctl daemon-reload
systemctl restart myapp
systemd-cgtop  # Should show myapp.service with ~50% CPU cap
```

## cgroup-tools: Fine-Grained Administration

The `cgroup-tools` package provides command-line utilities for creating, configuring, and querying cgroups directly — without going through systemd. This is essential for managing non-systemd processes, containers, and custom resource allocation schemes.

### Core Commands

```bash
# Create a new cgroup
cgcreate -g cpu,memory:/mygroup

# Set CPU weight (cgroup v2)
cgset -r cpu.weight=500 mygroup
# cpu.weight ranges from 1 to 10000 (default 100)

# Set memory limit
cgset -r memory.max=1G mygroup

# Set I/O weight
cgset -r io.weight="8:16 500" mygroup  # major:minor weight

# List current settings
cgget -r cpu.weight,memory.max mygroup

# Move a process into the cgroup
cgclassify -g cpu,memory:mygroup <PID>

# Run a command directly in a cgroup
cgexec -g cpu,memory:mygroup ./my_application

# Delete a cgroup (must be empty first)
cgdelete -g cpu,memory:mygroup
```

### Container Resource Management

For self-hosted container environments, cgroup-tools provides direct control over resource allocation:

```bash
# Create a cgroup for a database workload
cgcreate -g cpu,memory,io:/database
cgset -r cpu.weight=2000 /database      # Higher CPU priority
cgset -r memory.max=8G /database         # Memory limit
cgset -r memory.swap.max=0 /database     # Disable swap for database

# Create a cgroup for background jobs
cgcreate -g cpu,memory:/batch
cgset -r cpu.weight=200 /batch           # Lower CPU priority
cgset -r memory.max=4G /batch
cgset -r cpu.pressure=auto /batch        # Auto-throttle under pressure (v2)
```

### Docker Compose Integration

```yaml
services:
  cgroup-admin:
    image: alpine:latest
    privileged: true
    volumes:
      - /sys/fs/cgroup:/sys/fs/cgroup
      - /run/cgmanager/sock:/run/cgmanager/sock
    command: >
      sh -c "
        apk add cgroup-tools
        && cgcreate -g cpu,memory:/monitoring
        && cgset -r memory.max=512M /monitoring
        && cgget -r cpu.weight,memory.max /monitoring
      "
    network_mode: host
    restart: no
```

## libcgroup: Legacy Application Support

`libcgroup` is the original cgroup management library, providing both a C API for application integration and command-line tools. While the command-line tools (`cgexec`, `cgclassify`) remain useful, much of libcgroup's functionality is now available through systemd and cgroup-tools.

### libcgroup Configuration

The legacy `cgconfig` approach uses a configuration file:

```bash
# /etc/cgconfig.conf (legacy, cgroup v1 oriented)
group database {
    cpu {
        cpu.shares = 2000;
    }
    memory {
        memory.limit_in_bytes = 8G;
    }
}

group batch {
    cpu {
        cpu.shares = 200;
    }
    memory {
        memory.limit_in_bytes = 4G;
    }
}

# Start the cgconfig service
systemctl start cgconfig
```

### Process Classification with cgclassify

```bash
# Move existing processes
cgclassify -g cpu,memory:database $(pgrep postgres)

# Start new processes in a cgroup
cgexec -g cpu,memory:database psql -c "SELECT version();"

# Automatic classification via cgred
# /etc/cgrules.conf
*:postgres      cpu,memory    database
*:nginx         cpu,memory    webserver
@dba            cpu,memory    database
```

### Modern libcgroup Usage

For cgroup v2, libcgroup provides a compatibility layer:

```bash
# Install libcgroup
# Fedora/RHEL: dnf install libcgroup
# Debian/Ubuntu: apt install libcgroup

# Use cgexec with v2 controllers
cgexec -g cpu,memory:/mygroup ./application

# Check compatibility
lscgroup  # List all cgroups
lssubsys -a  # List available subsystems
```

## Why Self-Host with cgroup v2?

For self-hosted infrastructure, cgroup v2 provides several advantages over v1:

**Unified Resource Management**: With a single hierarchy, you can see and manage all resource controllers from one place. No more coordinating between multiple cgroup trees — CPU, memory, and I/O settings are all applied to the same cgroup path.

**Better Container Isolation**: cgroup v2's delegation model allows containers to create their own sub-cgroups, enabling nested container runtimes. This is essential for running Docker-in-Docker or Kubernetes nodes on self-hosted infrastructure.

**Pressure Stall Information (PSI)**: cgroup v2 integrates with the kernel's PSI system, providing accurate resource pressure metrics. Instead of guessing whether a system is memory-constrained based on swap usage, PSI tells you exactly how long processes are stalled waiting for resources. For related reading on OOM prevention, see our [Linux OOM prevention guide](../2026-05-27-self-hosted-linux-oom-prevention-earlyoom-systemd-oomd-psi-guide/).

**BPF-Based Resource Control**: cgroup v2 supports attaching eBPF programs to cgroups, enabling custom resource management policies. You can write BPF programs that implement sophisticated throttling, accounting, or scheduling algorithms tailored to your workload. For an introduction to eBPF tooling, check our [eBPF tracing guide](../2026-04-26-bpftrace-vs-bcc-vs-sysdig-self-hosted-ebpf-tracing-guide-2026/).

## Security and Resource Isolation Best Practices

1. **Set memory limits on all services** — unbounded memory usage can trigger system-wide OOM kills
2. **Use IOWeight instead of IOLimit** — weight-based scheduling is fairer than hard limits
3. **Monitor with systemd-cgtop regularly** — catch resource hogs before they impact other services
4. **Test pressure scenarios** — use `stress-ng` to verify cgroup limits work as expected
5. **Enable cgroup v2 at boot** — add `systemd.unified_cgroup_hierarchy=1` to kernel parameters if needed
6. **Avoid cgroup v1/v2 hybrid mode** — mixed hierarchies cause unpredictable behavior

```bash
# Quick cgroup health check
#!/bin/bash
echo "=== cgroup v2 Status ==="
stat -fc %T /sys/fs/cgroup/

echo "=== Available Controllers ==="
cat /sys/fs/cgroup/cgroup.controllers

echo "=== Top CPU Consumers ==="
systemd-cgtop -n 1 -b 2>/dev/null | head -15

echo "=== Memory Pressure ==="
cat /sys/fs/cgroup/memory.pressure 2>/dev/null || echo "PSI not available"

echo "=== OOM Kill Count ==="
cat /sys/fs/cgroup/memory.events 2>/dev/null | grep oom_kill
```

## Choosing the Right cgroup Administration Tool

| Scenario | Recommended | Reason |
|----------|-------------|--------|
| Quick resource overview | systemd-cgtop | Interactive, real-time display |
| Non-systemd process management | cgroup-tools (cgexec) | Direct cgroup control |
| Container runtime integration | cgroup-tools | Programmatic API |
| Legacy application support | libcgroup (cgclassify) | Compatible with older tools |
| Automated resource policies | systemd unit files + cgroup-tools | Declarative + imperative |
| Troubleshooting resource issues | systemd-cgtop + PSI | Visual monitoring + pressure metrics |
| Custom scheduling algorithms | cgroup v2 + eBPF | Programmable control |

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux cgroup v2 Administration: systemd-cgtop vs cgroup-tools vs libcgroup (2026)",
  "description": "Compare cgroup v2 administration tools: systemd-cgtop for monitoring, cgroup-tools for control, and libcgroup for legacy support.",
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

## FAQ

### What is the difference between cgroup v1 and cgroup v2?

cgroup v2 uses a single unified hierarchy for all resource controllers, while v1 had separate trees for CPU, memory, I/O, and other controllers. v2 also introduces better delegation for containers, improved memory accounting (including swap tracking), and integration with eBPF programs. Most modern distributions default to v2 — check with `stat -fc %T /sys/fs/cgroup/` (should show `cgroup2fs`).

### How do I enable cgroup v2 on my system?

If your system is running cgroup v1, add `systemd.unified_cgroup_hierarchy=1` to your kernel boot parameters. In GRUB, edit `/etc/default/grub`:
```bash
GRUB_CMDLINE_LINUX="systemd.unified_cgroup_hierarchy=1"
grub2-mkconfig -o /boot/grub2/grub.cfg
```
Then reboot. Most distributions with kernel 5.x+ and systemd 247+ use v2 by default.

### Can I use systemd-cgtop with cgroup v1?

Yes, `systemd-cgtop` works with both cgroup v1 and v2. However, the display differs — v2 shows a unified hierarchy while v1 shows multiple controller trees. For the best experience, migrate to cgroup v2.

### How do I set a hard CPU limit (not just weight) for a service?

In systemd, use `CPUQuota=` in the unit file:
```ini
[Service]
CPUQuota=50%
```
This limits the service to 50% of one CPU core. For cgroup v2 direct control:
```bash
cgset -r cpu.max="50000 100000" mygroup  # 50% quota
```

### What happens when a cgroup exceeds its memory limit?

In cgroup v2, when a cgroup reaches `memory.max`, the kernel triggers an OOM kill within that cgroup — only processes in the offending cgroup are killed, protecting the rest of the system. This is a significant improvement over v1, where memory pressure could cascade across the entire system. You can monitor OOM events with `cat /sys/fs/cgroup/memory.events`.

### Is libcgroup still maintained?

libcgroup receives maintenance updates but is not actively developed for new features. The command-line tools (`cgexec`, `cgclassify`) remain functional and useful, but for new deployments, prefer systemd's native cgroup management or cgroup-tools. The C library is still used by some applications for programmatic cgroup control.

