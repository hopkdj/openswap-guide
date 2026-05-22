---
title: "Self-Hosted cgroup Monitoring Tools: systemd-cgtop vs cgroup-tools vs libcgroup Guide"
date: "2026-05-22"
tags: ["cgroup", "container-monitoring", "linux", "resource-management", "systemd"]
draft: false
---

Control groups (cgroups) are the Linux kernel mechanism that enables resource isolation and accounting for containers, system services, and user sessions. Monitoring cgroup resource usage — CPU, memory, I/O, and network — is essential for container orchestration, capacity planning, and performance debugging. This guide compares three open-source tools for monitoring cgroup resource consumption: **systemd-cgtop**, **cgroup-tools**, and **libcgroup** utilities.

## Understanding Linux cgroups

Linux cgroups organize processes into hierarchical groups and apply resource limits, accounting, and isolation to each group. There are two major versions:

- **cgroup v1**: The original implementation with separate hierarchies per subsystem (cpu, memory, blkio, etc.)
- **cgroup v2**: Unified hierarchy introduced in kernel 4.5, with a single tree for all controllers and improved resource accounting

Modern distributions default to cgroup v2, which provides more accurate resource accounting, better pressure stall information (PSI), and unified configuration. All three monitoring tools covered here support cgroup v2, though with varying degrees of feature completeness.

## Comparison Table

| Feature | systemd-cgtop | cgroup-tools | libcgroup |
|---------|--------------|--------------|-----------|
| Package | systemd (pre-installed) | cgroup-tools / libcgroup | libcgroup |
| Interface | Terminal (interactive TUI) | CLI commands | CLI + config files |
| Real-time View | Yes (top-like) | No (snapshot) | No (snapshot) |
| Resource Types | CPU, Memory, I/O, Tasks | All controllers | All controllers |
| cgroup v2 Support | Full | Partial | Full |
| Configuration | Via systemd unit files | cgconfig.conf | cgconfig.conf + cgrules.conf |
| Historical Data | No | No | No |
| Container Aware | Yes (Docker, LXC) | Yes | Yes |
| Active Development | Yes (systemd project) | Community maintained | Community maintained |
| License | LGPL-2.1 | LGPL-2.1 | LGPL-2.1 |

## systemd-cgtop: Real-Time cgroup Top

[systemd-cgtop](https://www.freedesktop.org/software/systemd/man/systemd-cgtop.html) is part of the systemd suite and provides a real-time, top-like display of cgroup resource usage. It is the most immediately useful cgroup monitoring tool because it requires no additional installation on systemd-based systems.

### Key Features

- **Real-time display**: Continuously updates resource usage per cgroup, similar to `top`
- **Interactive sorting**: Press keys to sort by CPU%, memory, tasks, or I/O
- **Tree view**: Shows cgroup hierarchy with parent-child relationships
- **No configuration**: Works out of the box on any systemd-based distribution
- **Container visibility**: Shows Docker, containerd, and LXC cgroup resource usage
- **Color coding**: Highlights resource-intensive cgroups for quick identification

### Installation

```bash
# Pre-installed on most systemd distributions
# Ubuntu/Debian
sudo apt install systemd

# Arch Linux
sudo pacman -S systemd

# Verify installation
systemd-cgtop --version
```

### Usage Examples

```bash
# Basic real-time view
systemd-cgtop

# Sort by memory usage
systemd-cgtop -m

# Sort by task count
systemd-cgtop -t

# Show I/O usage
systemd-cgtop -io

# Set refresh interval (seconds)
systemd-cgtop -d 2

# Batch mode (for scripting)
systemd-cgtop -n 1 -b
```

### Interactive Controls

| Key | Action |
|-----|--------|
| `p` | Toggle between CPU% and CPU time |
| `m` | Sort by memory usage |
| `t` | Sort by task count |
| `i` | Sort by I/O usage |
| `q` | Quit |
| `Space` | Refresh immediately |

## cgroup-tools: Comprehensive CLI Suite

[cgroup-tools](https://github.com/libcgroup/libcgroup) provides a suite of command-line utilities for managing and monitoring cgroups. The package includes `lscgroup` (list cgroups), `cgget` (get cgroup parameters), `cgset` (set cgroup parameters), and `lssubsys` (list subsystems).

### Key Features

- **Complete cgroup introspection**: Query any cgroup parameter or statistic
- **Scripting-friendly**: Output designed for parsing in shell scripts
- **All controllers supported**: CPU, memory, blkio, hugetlb, devices, pids, rdma
- **Configuration management**: `cgconfig` for defining cgroup hierarchies
- **Rule-based classification**: `cgrulesengd` daemon for automatic process assignment
- **Cross-distribution**: Available on all major Linux distributions

### Installation

```bash
# Ubuntu/Debian
sudo apt install cgroup-tools

# Arch Linux
sudo pacman -S libcgroup

# RHEL/CentOS
sudo yum install libcgroup-tools

# Verify
lssubsys -am
```

### Docker Compose for cgroup Monitoring

```yaml
version: "3.8"
services:
  cgroup-monitor:
    image: ubuntu:latest
    volumes:
      - /sys/fs/cgroup:/sys/fs/cgroup:ro
    entrypoint: ["sh", "-c"]
    command: >
      "apt update && apt install -y cgroup-tools &&
       while true; do
         echo '--- cgroup stats ---'
         cgget -g /system.slice
         echo '--- Docker containers ---'
         lscgroup | grep docker
         sleep 30
       done"
    restart: unless-stopped
```

### Usage Examples

```bash
# List all cgroup hierarchies
lscgroup

# Get memory usage for a specific cgroup
cgget -r memory.current /system.slice/docker.service

# Get CPU stats for all cgroups
cgget -r cpu.stat /

# Set CPU shares for a cgroup
sudo cgset -r cpu.weight=200 /my-group

# List available subsystems
lssubsys -am

# Monitor cgroup events
lscgroup | while read cg; do
  cgget -r memory.current "$cg"
done
```

## libcgroup: Configuration-Driven cgroup Management

[libcgroup](https://github.com/libcgroup/libcgroup) is the underlying library that powers cgroup-tools, but it also provides configuration file-based management through `cgconfig` and `cgrulesengd`. This approach is ideal for setting up persistent cgroup hierarchies with defined resource limits.

### Key Features

- **Declarative configuration**: Define cgroup hierarchies in config files
- **Process classification rules**: Assign processes to cgroups based on user, group, or command
- **Persistent settings**: Configuration survives reboots
- **Daemon-based management**: `cgrulesengd` automatically classifies new processes
- **Integration with PAM**: Classify user sessions into cgroups at login
- **Hierarchical resource accounting**: Parent cgroups aggregate child resource usage

### Configuration

```ini
# /etc/cgconfig.conf - Define cgroup hierarchies
group webserver {
    cpu {
        cpu.weight = 500;
    }
    memory {
        memory.max = 2G;
        memory.swap.max = 512M;
    }
    io {
        io.max = "254:0 rbps=104857600 wbps=104857600";
    }
}

group database {
    cpu {
        cpu.weight = 1000;
    }
    memory {
        memory.max = 8G;
    }
}
```

```ini
# /etc/cgrules.conf - Process classification rules
# user:process    subsystem    cgroup
www-data:*        cpu,memory   webserver
mysql:*           cpu,memory   database
*:*               cpu          default
```

### Usage Examples

```bash
# Start the configuration daemon
sudo systemctl start cgconfig

# Start the rules engine daemon
sudo systemctl start cgrulesengd

# Load configuration manually
sudo cgconfigparser -l /etc/cgconfig.conf

# Verify cgroup hierarchy
lscgroup | grep -E "webserver|database"

# Check resource usage
cgget -r memory.current /webserver
cgget -r cpu.stat /database
```

## Choosing the Right Tool

### Use systemd-cgtop When:
- You need **real-time interactive monitoring** of cgroup resource usage
- You want a **quick overview** without any configuration
- You're **debugging resource contention** between services or containers
- You're already running **systemd** (most modern distributions)
- You prefer a **top-like interface** for system monitoring

### Use cgroup-tools When:
- You need **scriptable access** to cgroup statistics
- You want to **query specific parameters** programmatically
- You're building **monitoring dashboards** that consume cgroup data
- You need **cross-distribution compatibility** beyond systemd systems
- You're writing **automation scripts** that check resource thresholds

### Use libcgroup When:
- You need **persistent cgroup configurations** that survive reboots
- You want **automatic process classification** based on rules
- You're managing **complex multi-tenant systems** with defined resource quotas
- You need **PAM integration** for user session classification
- You prefer **declarative configuration** over imperative commands

## Why Self-Host cgroup Monitoring?

Monitoring cgroup resource usage on your own infrastructure is essential for operational visibility:

**Container resource accountability**: When running multiple containers on shared hardware, cgroup monitoring reveals which containers consume disproportionate CPU, memory, or I/O. This is critical for capacity planning and cost allocation in multi-tenant environments.

**Performance debugging**: When a self-hosted service degrades, cgroup monitoring identifies whether the bottleneck is CPU throttling, memory pressure, or I/O contention. This accelerates root cause analysis without relying on external monitoring services.

**Resource quota enforcement**: For self-hosted platforms serving multiple teams or projects, cgroup monitoring verifies that resource quotas are respected and identifies violations before they impact other workloads.

**Cost optimization**: Understanding per-service resource consumption helps right-size infrastructure. Over-provisioned containers waste memory and CPU; under-provisioned ones cause throttling. cgroup monitoring provides the data needed for optimal sizing. For related reading, see our [container resource management guide](../2026-05-14-k8s-resource-quota-management-native-vs-goldilocks-vs-vpa-guide/) and [Linux OOM prevention comparison](../2026-05-27-self-hosted-linux-oom-prevention-earlyoom-systemd-oomd-guide/) for complementary resource management strategies.

## FAQ

### What is the difference between cgroup v1 and cgroup v2 monitoring?

cgroup v1 has separate hierarchies per subsystem (cpu, memory, blkio), so you need to check multiple paths. cgroup v2 uses a unified hierarchy with a single mount point (`/sys/fs/cgroup`) and all controllers attached to the same tree. systemd-cgtop handles both transparently, while cgroup-tools and libcgroup require different configuration syntax for each version.

### Can systemd-cgtop monitor Docker container resource usage?

Yes. systemd-cgtop shows Docker containers under the `system.slice/docker-<container-id>.scope` cgroup path. The display includes CPU%, memory usage, I/O throughput, and task count per container. For more detailed container-specific metrics, consider pairing with `docker stats` or a dedicated container monitoring tool.

### How do I set up persistent cgroup monitoring?

Use libcgroup's `cgconfig.conf` to define persistent cgroup hierarchies with resource limits, and `cgrules.conf` to classify processes automatically. Enable both `cgconfig` and `cgrulesengd` systemd services for persistent operation. The configuration files are read at boot and reloaded on service restart.

### Does cgroup monitoring add significant overhead?

The overhead is negligible. cgroup accounting is done at the kernel level regardless of whether you monitor it. Reading cgroup statistics (via systemd-cgtop, cgget, or /sys/fs/cgroup files) involves reading kernel-maintained counters, which is an O(1) operation per cgroup. The real-time display of systemd-cgtop adds minimal CPU usage (<0.1% on typical systems).

### Can I monitor cgroup resource usage remotely?

Yes. You can expose cgroup statistics through monitoring agents like Prometheus node-exporter, Telegraf, or custom scripts that read from `/sys/fs/cgroup`. Tools like cgroup-tools (`cgget`) can be wrapped in shell scripts for periodic collection and export to your monitoring stack.

### How do I identify which cgroup is consuming the most memory?

Run `systemd-cgtop -m` to sort cgroups by memory usage in descending order. Alternatively, use `cgget -r memory.current /` for a snapshot, or traverse `/sys/fs/cgroup/` manually to read `memory.current` files. The cgroup with the highest value is your top memory consumer.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted cgroup Monitoring Tools: systemd-cgtop vs cgroup-tools vs libcgroup Guide",
  "description": "Compare systemd-cgtop, cgroup-tools, and libcgroup for Linux cgroup resource monitoring. Learn how to monitor container and service resource usage.",
  "datePublished": "2026-05-22",
  "dateModified": "2026-05-22",
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
