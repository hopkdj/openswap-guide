---
title: "Self-Hosted Linux Cgroup v2 Resource Management: systemd-cgtop vs cgroup-tools vs libcgroup"
date: "2026-06-01"
tags: ["linux", "containers", "self-hosted", "resource-management", "system-administration", "performance", "systemd"]
draft: false
---

## Introduction

Control Groups (cgroups) are the Linux kernel mechanism that underpins container resource limits, systemd service isolation, and performance-critical workload management. With cgroup v2 now the default on all major distributions (since RHEL 8, Ubuntu 22.04, Debian 11), understanding the tools for monitoring, configuring, and troubleshooting cgroups is essential for any self-hosted server operator.

In this guide, we compare four tools for managing cgroup v2 on Linux: **systemd-cgtop** and **systemd-cgls** (built into systemd), the **cgroup-tools** package (cgevent, cgget, cgset), the classic **libcgroup** utilities, and the modern **cgmanager** daemon. Whether you're debugging why a container is being OOM-killed, setting CPU limits on a database process, or understanding memory pressure on a busy virtualization host, the right tool makes the difference.

## Why Self-Host Your Resource Management

Effective cgroup management directly translates to better service reliability. When you run multiple self-hosted services on a single machine — a web server, database, media server, and CI runner all competing for the same CPU cores and memory pages — cgroups are the enforcement mechanism that prevents one misbehaving service from starving all the others. Unlike cloud provider abstractions that hide resource contention behind opaque "vCPU" and "burstable" tiers, self-hosted cgroup management gives you byte-level control over every allocation.

For container operators, cgroup v2 is the unified hierarchy that Docker, Podman, and containerd all use under the hood. When you set `--memory=512m` on a Docker container, you're configuring a cgroup v2 memory limit. Understanding the cgroup tools lets you verify that limits are actually being enforced, diagnose why a container is being throttled, and tune the kernel's OOM (Out of Memory) killer behavior. If you're running [container runtimes like containerd, CRI-O, or Podman](../containerd-vs-cri-o-vs-podman-self-hosted-container-runtimes-guide-2026/), cgroup awareness is essential troubleshooting knowledge.

For homelab virtualization hosts running Proxmox, KVM, or Incus, cgroup tools reveal how memory ballooning behaves under pressure, which VMs are hitting their CPU caps, and whether your I/O limits are working as expected. The same tools that [OCI runtimes like crun and runc use](../2026-05-09-oci-container-runtimes-crun-runc-youki-guide/) for container isolation are available to you for monitoring and manual tuning.

## Comparison Table: Cgroup v2 Management Tools

| Feature | systemd-cgtop | cgroup-tools | libcgroup | cgmanager |
|---------|---------------|--------------|-----------|-----------|
| **Package** | systemd (built-in) | cgroup-tools | libcgroup-tools | cgmanager |
| **Real-Time Monitoring** | Yes (top-like) | cgevent (events) | No | Via D-Bus API |
| **Parameter Reading** | Via systemctl show | cgget | cgget | dbus-send |
| **Parameter Setting** | Via systemctl set-property | cgset | cgset | dbus-send |
| **Process Classification** | Automatic (systemd) | cgclassify | cgclassify | Manual assignment |
| **Event Notification** | No | cgevent (inotify) | No | D-Bus signals |
| **API/Programmatic** | D-Bus | Command line only | C library + CLI | D-Bus |
| **Persistent Rules** | Drop-in files | cgconfig.conf | cgconfig.conf | Config files |
| **Cgroup v2 Support** | Full | Partial (v1-focused) | Partial | Full |
| **Active Development** | Very Active | Maintenance | None (deprecated) | Unmaintained |
| **Best For** | Systemd-managed services | Quick CLI operations | Legacy systems | Programmatic access |

## Tool Deep Dives

### systemd-cgtop & systemd-cgls: Built-in Resource Monitoring

Every systemd system ships with `systemd-cgtop` (a `top`-like interface for cgroups) and `systemd-cgls` (a tree view of control group hierarchy). These are your first stop for resource diagnostics.

```bash
# Real-time cgroup resource usage (like top)
systemd-cgtop

# One-shot snapshot with specific depth
systemd-cgtop -n 1 -d 2

# Display control group tree
systemd-cgls

# Show only specific controller paths
systemd-cgls /system.slice/docker.service

# View resource limits for a systemd service
systemctl show nginx.service | grep -E 'Memory|CPU|Tasks|IO'

# Set a memory limit on a running service
sudo systemctl set-property nginx.service MemoryMax=512M

# Set CPU quota (50% of one core)
sudo systemctl set-property nginx.service CPUQuota=50%

# Create persistent drop-in overrides
sudo systemctl edit nginx.service
# Add:
# [Service]
# MemoryMax=512M
# CPUQuota=50%
# IOWeight=500
```

For ad-hoc process isolation, you can create transient cgroups:

```bash
# Run a command under a transient cgroup with limits
sudo systemd-run --user --scope \
  -p MemoryMax=256M -p CPUQuota=25% \
  --unit=my-limited-task \
  /path/to/resource-heavy-command
```

### cgroup-tools: The Classic CLI Utilities

The `cgroup-tools` package provides granular CLI access to cgroup parameters. While originally designed for cgroup v1, many commands work with v2 on modern kernels.

```bash
# Install
sudo apt install cgroup-tools

# View current cgroup for a process
cgget -r memory.current /sys/fs/cgroup/system.slice/nginx.service

# Set a memory limit
sudo cgset -r memory.max=536870912 /system.slice/nginx.service

# Move a process to a cgroup
sudo cgclassify -g memory,cpu:/limited.slice <PID>

# Monitor cgroup events (e.g., OOM, limit hits)
cgevent -g memory:/system.slice/nginx.service

# List subsystem usage
lscgroup
lssubsys -am
```

For persistent classification rules:

```bash
# /etc/cgconfig.conf
group limited {
    memory {
        memory.max = "256M";
        memory.swap.max = "0";
    }
    cpu {
        cpu.max = "50000 100000";  # 50% of one CPU
    }
}
```

### libcgroup: The C API Foundation

`libcgroup` provides the underlying C library that `cgroup-tools` builds upon. While the CLI tools from `libcgroup-tools` package are similar to `cgroup-tools`, the library itself is important for developers writing resource-aware applications.

```bash
# Install libcgroup utilities
sudo apt install libcgroup-tools libcgroup-dev

# Configure persistent groups: /etc/cgconfig.conf
mount {
    cpu = /sys/fs/cgroup;
    memory = /sys/fs/cgroup;
}

group db-limited {
    perm {
        admin { uid = root; }
        task { uid = postgres; }
    }
    memory { memory.max = "2G"; }
    cpu { cpu.max = "200000 100000"; }
}

# Apply configuration
sudo cgconfigparser -l /etc/cgconfig.conf

# Start the rules engine daemon
sudo cgrulesengd
```

Note: libcgroup is considered legacy. For new deployments on cgroup v2, prefer systemd's native resource controls or the cgroupfs interface directly.

### Reading Cgroup v2 Directly via cgroupfs

For scripting and programmatic access, you can read cgroup v2 parameters directly from the filesystem:

```bash
# cgroup v2 unified hierarchy location
CGROUP_ROOT=/sys/fs/cgroup

# Check if using cgroup v2
[ -f $CGROUP_ROOT/cgroup.controllers ] && echo "cgroup v2" || echo "cgroup v1"

# View available controllers
cat $CGROUP_ROOT/cgroup.controllers
# Output example: cpuset cpu io memory hugetlb pids rdma misc

# Memory usage for a service
cat $CGROUP_ROOT/system.slice/nginx.service/memory.current
cat $CGROUP_ROOT/system.slice/nginx.service/memory.max

# CPU usage statistics
cat $CGROUP_ROOT/system.slice/nginx.service/cpu.stat

# I/O pressure (cgroup v2 Pressure Stall Information)
cat $CGROUP_ROOT/system.slice/nginx.service/memory.pressure
# Output: some avg10=0.00 avg60=0.00 avg300=0.00 total=0
#          full avg10=0.00 avg60=0.00 avg300=0.00 total=0

# Check if a service is under memory pressure
cat $CGROUP_ROOT/system.slice/nginx.service/memory.events
# low 0, high 0, max 15, oom 2, oom_kill 1
```

This direct cgroupfs access is what Docker, containerd, and systemd all use internally. For monitoring dashboards, parse these files with a script to feed data into Prometheus node_exporter or your metrics pipeline.

## Troubleshooting Common Issues

**OOM killer invoked on your container:** Check `memory.events` for the cgroup — if `oom_kill` is non-zero, your container exceeded its memory limit. Increase the limit with `systemctl set-property` or your container runtime's flag.

**CPU throttling despite low overall usage:** Check `cpu.stat` for `nr_throttled` and `throttled_usec`. If the throttled time is high, your process is hitting its CPU quota even though the host has idle cores. Increase `CPUQuota` or switch to `CPUWeight`-based scheduling.

**Cannot set memory limit:** You may be running on cgroup v1 (check `/sys/fs/cgroup/cgroup.controllers` exists). Migrate to cgroup v2 by adding `systemd.unified_cgroup_hierarchy=1` to your kernel command line.

## FAQ

### How do I check if my server is using cgroup v1 or v2?

Run `mount | grep cgroup`. If you see a single mount at `/sys/fs/cgroup` with type `cgroup2`, you're on v2. If you see multiple mounts (`cgroup on /sys/fs/cgroup/cpu`, `cgroup on /sys/fs/cgroup/memory`, etc.) you're on v1. Most modern distributions (Ubuntu 22.04+, Debian 11+, RHEL 9+) default to v2.

### What are the main benefits of cgroup v2 over v1?

Unified hierarchy — all controllers share a single tree, eliminating the complex multi-hierarchy management of v1. Pressure Stall Information (PSI) provides granular resource pressure metrics. Better memory accounting with `memory.current` vs. the confusing `memory.usage_in_bytes` of v1. Enhanced I/O controller with the `io.max` interface replacing `blkio.throttle`.

### Can I mix cgroup v1 and v2 on the same system?

In hybrid mode, yes — but it's not recommended for production. Some controllers can run in v1 mode while others use v2. However, once a controller is bound to v1, it can't be used in v2. For cleanest behavior, go all-in on v2 with `systemd.unified_cgroup_hierarchy=1`.

### How do container runtimes use cgroups?

Docker, Podman, and containerd create a child cgroup under their service slice for each container. When you specify `--cpus=2 --memory=1g` on `docker run`, Docker writes those values to `cpu.max` and `memory.max` in the container's cgroup directory. You can inspect this with `systemd-cgls` or by navigating `/sys/fs/cgroup/system.slice/docker-<container-id>.scope/`.

### What should I monitor to prevent OOM kills?

Monitor `memory.pressure` (PSI) and `memory.events` for each critical service cgroup. If `memory.pressure some` is elevated, the kernel is struggling to reclaim memory. If `oom_kill` is incrementing, your limits are too tight. Set up alerting on `memory.current / memory.max > 0.85` to warn before hitting the limit.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Cgroup v2 Resource Management: systemd-cgtop vs cgroup-tools vs libcgroup",
  "description": "Complete guide to Linux cgroup v2 management tools — systemd-cgtop, cgroup-tools, libcgroup, and cgmanager — for monitoring and controlling resources on self-hosted servers.",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到科技监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测科技趋势走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
