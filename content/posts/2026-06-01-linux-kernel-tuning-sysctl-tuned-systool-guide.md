---
title: "Self-Hosted Linux Kernel Tuning: sysctl vs tuned vs systool"
date: "2026-06-01"
tags: ["linux", "kernel", "performance", "sysadmin", "tuning", "optimization"]
draft: false
---

## Introduction

Every Linux system ships with thousands of tunable kernel parameters governing everything from network buffer sizes to virtual memory behavior. Three tools give you access to these knobs: **sysctl** for direct `/proc/sys` manipulation, **tuned** for profile-driven adaptive optimization, and **systool** for exploring the sysfs device tree. Understanding when and how to use each one is essential for any systems administrator responsible for production workloads.

This guide compares these three kernel tuning interfaces, with practical examples for database servers, web applications, and container hosts.

## Feature Comparison

| Feature | sysctl | tuned | systool |
|---------|--------|-------|---------|
| **Interface** | `/proc/sys/` filesystem | D-Bus daemon with profiles | Sysfs filesystem |
| **Persistence** | `/etc/sysctl.conf` / `.d/*.conf` | Profile files in `/etc/tuned/` | Not persistent (read-only) |
| **Adaptive Tuning** | No (static values) | Yes (monitors load, adjusts live) | No (interrogation only) |
| **Scope** | Kernel parameters (net, vm, fs, kernel) | System-wide optimization profiles | Device, bus, driver, module info |
| **Profiles** | Manual per-parameter | Pre-built: throughput-performance, latency-performance, virtual-guest, etc. | N/A (read-only discovery) |
| **Real-time Adjust** | `sysctl -w` (immediate) | `tuned-adm profile <name>` (profile switch) | Read-only |
| **Boot Persistence** | Yes (via sysctl.conf) | Yes (active profile survives reboot) | N/A |
| **Discovery** | `sysctl -a` (list all) | `tuned-adm list` (profiles) | `systool -b <bus>` (browse) |
| **Package** | procps-ng (pre-installed) | tuned | sysfsutils |

## sysctl — Direct Kernel Parameter Control

`sysctl` is the canonical interface for reading and writing kernel parameters at runtime. Every parameter exposed under `/proc/sys/` — from TCP congestion control algorithms to the maximum number of open file descriptors — can be inspected and modified with sysctl.

### Installation

```bash
# sysctl is part of procps-ng, pre-installed on virtually all Linux distributions
# Verify availability:
which sysctl
sysctl --version
```

### Essential Tuning Commands

```bash
# List all available kernel parameters
sysctl -a

# Read a specific parameter
sysctl net.core.somaxconn
sysctl vm.swappiness

# Apply a change immediately (non-persistent)
sysctl -w net.core.somaxconn=4096
sysctl -w vm.swappiness=10

# Load settings from a configuration file
sysctl -p /etc/sysctl.conf
sysctl -p /etc/sysctl.d/99-custom.conf

# Common performance tuning examples
sysctl -w net.ipv4.tcp_fastopen=3           # TCP Fast Open
sysctl -w net.core.rmem_max=134217728       # Max receive buffer
sysctl -w vm.dirty_ratio=15                 # Dirty page cache limit
sysctl -w kernel.pid_max=4194304            # Max process IDs
```

### Persisting Changes

Create or edit a file in `/etc/sysctl.d/`:

```bash
# /etc/sysctl.d/99-postgresql.conf
# PostgreSQL-optimized kernel parameters
kernel.shmmax = 8589934592
kernel.shmall = 2097152
vm.swappiness = 5
vm.overcommit_memory = 2
vm.overcommit_ratio = 90
net.core.somaxconn = 4096

# Apply
sudo sysctl --system
```

## tuned — Adaptive Profile-Driven Optimization

`tuned` is a system daemon developed by Red Hat that monitors system resource usage and dynamically adjusts kernel parameters based on the active profile. Unlike sysctl's static approach, tuned can adapt to changing workloads in real time — increasing network buffers during peak traffic and reducing them during idle periods.

### Installation

```bash
# RHEL/CentOS/Fedora
sudo dnf install tuned
sudo systemctl enable --now tuned

# Debian/Ubuntu
sudo apt install tuned
sudo systemctl enable --now tuned

# Arch Linux
sudo pacman -S tuned
sudo systemctl enable --now tuned
```

### Essential Tuning Commands

```bash
# List available tuning profiles
tuned-adm list

# Show the currently active profile
tuned-adm active

# Switch to a performance profile
tuned-adm profile throughput-performance

# Switch to a power-saving profile
tuned-adm profile powersave

# Apply a virtual-guest profile (on VMs)
tuned-adm profile virtual-guest

# Get a profile recommendation based on hardware
tuned-adm recommend

# View all settings in the current profile
tuned-adm profile_info
```

### Key Profiles

| Profile | Best For | What It Does |
|---------|----------|-------------|
| `throughput-performance` | Database servers, file servers | Maximizes I/O and network throughput |
| `latency-performance` | Web servers, API gateways | Minimizes latency at cost of power |
| `virtual-guest` | Virtual machines | Reduces disk flush frequency, optimizes for virtio |
| `virtual-host` | Hypervisors | Tunes for hosting multiple VMs efficiently |
| `network-throughput` | Load balancers, proxies | Maximizes network buffer sizes |
| `oracle` | Oracle Database | Applies Oracle-recommended kernel settings |

### Custom Profiles

Create your own profile at `/etc/tuned/my-profile/`:

```ini
# /etc/tuned/my-database/tuned.conf
[main]
summary=Custom database server optimization

[sysctl]
vm.swappiness=5
vm.dirty_ratio=10
vm.dirty_background_ratio=3
net.core.somaxconn=65535
net.ipv4.tcp_tw_reuse=1

[bootloader]
cmdline=transparent_hugepage=never
```

```bash
# Enable the custom profile
sudo tuned-adm profile my-database
```

## systool — Sysfs Device Tree Explorer

`systool` is a diagnostic and discovery tool that traverses the sysfs filesystem (`/sys/`), presenting a structured view of system buses, devices, drivers, and kernel modules. While sysctl modifies runtime parameters, systool helps you understand what hardware is present, which drivers are bound, and what attributes are available for each device.

### Installation

```bash
# Debian/Ubuntu
sudo apt install sysfsutils

# RHEL/CentOS/Fedora
sudo dnf install sysfsutils

# Arch Linux
sudo pacman -S sysfsutils
```

### Essential Commands

```bash
# List all system buses
systool

# Show all PCI devices
systool -b pci

# Show all USB devices
systool -b usb

# Show devices using a specific driver
systool -v -m e1000e

# Show all loaded kernel modules
systool -m

# Display driver parameters (modifiable at load time)
systool -v -m ixgbe | grep -A2 "Parameters"

# Find which driver a device uses
systool -b pci | grep -B5 -A10 "eth0"
```

### When to Use systool

Use systool when troubleshooting hardware recognition: a new NIC isn't showing up, a storage controller isn't binding to the right driver, or you need to check which kernel module parameters are available. It is read-only — you cannot modify parameters with systool — but it is invaluable for discovering what the kernel sees and which knobs are available for tuning with other tools.

## Why Self-Host Your Kernel Tuning Approach

Cloud VMs often ship with generic kernel settings that are suboptimal for specific workloads. A one-size-fits-all approach results in underutilized hardware — your database server might be throttled by conservative I/O limits intended for desktop use, or your container host might exhaust ephemeral ports because `net.ipv4.ip_local_port_range` defaults to 32768-60999.

For CPU frequency management and power optimization, see our [auto-cpufreq vs cpupower vs tuned guide](../2026-05-22-self-hosted-linux-cpu-governor-management-auto-cpufreq-vs-cpupower-vs-tuned-guide/). If you are managing large-memory workloads, our [hugepages management comparison](../2026-05-22-self-hosted-linux-hugepages-management-libhugetlbfs-numactl-tuned-guide/) covers transparent hugepages and explicit hugepage allocation. For profiling where your system is spending cycles, our [Linux performance profiling tools guide](../2026-05-22-self-hosted-linux-performance-profiling-perf-bcc-tools-sysstat-guide/) provides complementary analysis.

The right combination — sysctl for precise static tuning, tuned for adaptive workload response, and systool for hardware discovery — ensures your servers run at their full potential without guesswork.

## FAQ

### How do I make sysctl changes permanent across reboots?

Write your settings to a file in `/etc/sysctl.d/` with a `.conf` extension (e.g., `/etc/sysctl.d/99-custom.conf`). These files are applied at boot by `systemd-sysctl.service`. To apply immediately, run `sysctl --system` which reloads all configuration files. Do NOT edit `/etc/sysctl.conf` directly on modern systems — use the `.d/` drop-in directory instead for better organization.

### Can tuned and manual sysctl settings conflict with each other?

Yes. When tuned applies a profile, it overwrites sysctl parameters with its own values. If you have manually set a parameter via sysctl that clashes with the tuned profile, tuned will override it on profile switch or daemon restart. The safe approach is to either use tuned exclusively (creating custom profiles for your needs) or disable tuned entirely and manage everything through sysctl. You can check the current effective values with `sysctl <parameter>` to see which tool applied the most recent change.

### Why does systool show the same device under multiple buses?

Modern hardware often exposes itself through multiple kernel subsystems. An NVMe drive, for example, appears under the PCI bus (as a PCIe device) and the block subsystem (as a storage device). systool faithfully reflects this multiplicity, showing each logical view of the same physical hardware. Use this to trace dependencies — for example, finding which PCI device corresponds to which network interface name.

### What are the risks of kernel tuning without understanding the parameters?

The risks range from subtle performance degradation to complete system instability. Setting `vm.overcommit_memory=2` without proper `vm.overcommit_ratio` can cause applications to be killed by the OOM killer. Reducing `net.core.rmem_max` too aggressively can throttle high-bandwidth applications. Always test tuning changes on a staging system first, document the baseline performance, and apply changes incrementally with monitoring in place. Tools like `sar`, `vmstat`, and application-level metrics should track the impact of each change.

### When should I use tuned vs just writing a sysctl.conf file?

Use tuned when you need adaptive behavior that responds to changing workloads — for example, a server that handles batch processing at night and real-time API requests during the day. tuned can switch parameters based on load patterns automatically. Use sysctl for static, well-understood parameters where the optimal value never changes regardless of workload — like database-specific shared memory settings or container host port ranges. For most single-purpose servers, a well-crafted sysctl configuration is simpler and more predictable.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到 科技政策监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测 科技行业的发展趋势已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Kernel Tuning: sysctl vs tuned vs systool",
  "description": "Compare sysctl, tuned, and systool for Linux kernel tuning. Learn when to use static sysctl parameters, adaptive tuned profiles for dynamic workloads, and systool for hardware discovery and driver inspection.",
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
