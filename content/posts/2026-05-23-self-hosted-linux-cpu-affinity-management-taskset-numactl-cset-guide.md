---
title: "Self-Hosted Linux CPU Affinity Management: taskset vs numactl vs cset"
date: "2026-05-23"
tags: ["linux", "system-administration", "performance", "cpu-affinity"]
draft: false
---

CPU affinity controls which processor cores execute specific processes on a Linux system. On multi-core servers running database engines, web servers, or real-time applications, improper CPU affinity can cause cache thrashing, NUMA penalties, and unpredictable latency. This guide compares three tools for managing CPU affinity on self-hosted Linux servers: **taskset** (process-level pinning), **numactl** (NUMA-aware placement), and **cset** (advanced CPU set management with shielding).

## What Is CPU Affinity and Why Does It Matter?

Linux schedules processes across all available CPU cores by default. This works well for general workloads but causes problems for performance-sensitive applications:

- **Cache locality**: When a process migrates between cores, its L1/L2 cache state is lost, causing cache misses on the new core
- **NUMA penalties**: Accessing memory from a remote NUMA node adds 40-100ns latency per access
- **Context switch overhead**: Migrating processes between cores requires TLB flushes and cache invalidation

Proper CPU affinity pinning keeps critical processes on dedicated cores, maintaining cache warmth and eliminating cross-NUMA memory access penalties.

| Feature | taskset | numactl | cset |
|---------|---------|---------|------|
| **Granularity** | Per-process | Per-process + NUMA | CPU set-based |
| **NUMA Awareness** | No | Yes | Yes |
| **Shielding** | No | No | Yes (kthread migration) |
| **Ease of Use** | Simple (single command) | Simple (single command) | Moderate (setup required) |
| **Persistence** | Per-launch | Per-launch | Persistent sets |
| **Container Support** | Manual | Manual | cset shield with Docker |
| **GitHub Repo** | util-linux (3,154 stars) | numactl (496 stars) | cpuset (133 stars) |
| **Last Updated** | 2026-05-20 | 2026-02-24 | 2025-04-08 |

## taskset — Simple Process-Level CPU Pinning

**taskset** is part of the util-linux package and provides the simplest way to set or retrieve CPU affinity for running processes. It accepts CPU masks in hexadecimal or list format.

### Installation

```bash
# Debian/Ubuntu (usually pre-installed)
sudo apt install -y util-linux

# RHEL/CentOS/Fedora (usually pre-installed)
sudo dnf install -y util-linux
```

### Basic Usage

```bash
# Launch a process on CPU 0 only
taskset -c 0 nginx

# Launch on CPUs 0-3
taskset -c 0-3 ./database-server

# Launch on specific non-contiguous CPUs
taskset -c 0,2,4,6 ./realtime-app

# Change affinity of a running process (PID 1234)
taskset -cp 0-3 1234

# Check current affinity
taskset -p 1234
# Output: pid 1234 current affinity mask: f
# Output: pid 1234 new affinity mask: f
```

### Hexadecimal CPU Masks

```bash
# CPU 0 only: 0x1
taskset 0x1 nginx

# CPUs 0-3: 0xF
taskset 0xF ./app

# CPUs 4-7: 0xF0
taskset 0xF0 ./worker

# CPUs 0 and 8 (16-bit mask): 0x0101
taskset 0x0101 ./service
```

### Docker Compose with taskset

You can integrate taskset into container startup commands:

```yaml
version: "3.8"
services:
  webapp:
    image: nginx:latest
    command: >
      sh -c "taskset -c 0-3 nginx -g 'daemon off;'"
    deploy:
      resources:
        limits:
          cpus: "4.0"
    restart: unless-stopped
```

## numactl — NUMA-Aware Process Placement

**numactl** controls NUMA policy for processes, allowing you to specify which NUMA node a process runs on AND where its memory is allocated. This is critical for multi-socket servers where cross-node memory access significantly impacts performance.

### Installation

```bash
# Debian/Ubuntu
sudo apt install -y numactl

# RHEL/CentOS/Fedora
sudo dnf install -y numactl
```

### Checking NUMA Topology

```bash
# Show NUMA topology
numactl --hardware
# Output:
# available: 2 nodes (0-1)
# node 0 cpus: 0 1 2 3 4 5 6 7
# node 0 size: 32768 MB
# node 0 free: 28456 MB
# node 1 cpus: 8 9 10 11 12 13 14 15
# node 1 size: 32768 MB
# node 1 free: 30123 MB

# Show current NUMA policy
numactl --show
```

### Running Processes with NUMA Policy

```bash
# Run on NUMA node 0 (CPUs 0-7, local memory)
numactl --cpunodebind=0 --membind=0 ./database-server

# Run on specific CPUs with local memory allocation
numactl --cpubind=0-3 --membind=0 ./web-server

# Preferred node (falls back if node is full)
numactl --preferred=0 ./application

# Interleave memory across all NUMA nodes
numactl --interleave=all ./memory-intensive-app

# Run on CPUs 8-15 with memory on node 1
numactl --cpunodebind=1 --membind=1 ./analytics-engine
```

### Docker Compose with numactl

```yaml
version: "3.8"
services:
  database:
    image: postgres:16
    command: >
      sh -c "numactl --cpunodebind=0 --membind=0 postgres"
    environment:
      POSTGRES_PASSWORD: secret
    deploy:
      resources:
        limits:
          cpus: "8.0"
          memory: 16G
    restart: unless-stopped
```

## cset — Advanced CPU Set Management with Shielding

**cset** (CPU set) is a Python-based tool that provides high-level CPU set management. Its key feature is **shielding** — it moves all kernel threads and non-critical processes off designated CPU cores, creating a clean environment for performance-critical workloads.

### Installation

```bash
# Debian/Ubuntu
sudo apt install -y cpuset

# RHEL/CentOS/Fedora
sudo dnf install -y cpuset

# Or install from GitHub
git clone https://github.com/SUSE/cpuset.git
cd cpuset
sudo make install
```

### Creating CPU Shields

```bash
# Create a shield with CPUs 4-7 (isolated from system processes)
sudo cset shield --cpu=4-7 --kthread=on

# The kthread=on flag also moves kernel threads off the shield

# Run a process inside the shield
sudo cset shield --exec -- ./performance-critical-app

# Run with specific NUMA policy inside the shield
sudo cset shield --exec -- numactl --membind=1 ./database

# Check shield status
sudo cset shield --status
# Output:
# cset: "system" cpuset of CPUSPEC(0-3) with 45 tasks
# cset: "shield" cpuset of CPUSPEC(4-7) with 3 tasks

# Destroy the shield (returns CPUs to system)
sudo cset shield --reset
```

### Docker Integration with cset

```yaml
version: "3.8"
services:
  trading-engine:
    image: trading-app:latest
    entrypoint: ["cset", "shield", "--exec", "--"]
    command: ["./trading-engine", "--realtime"]
    deploy:
      resources:
        limits:
          cpus: "4.0"
    restart: unless-stopped
```

### cset vs taskset: Key Differences

While taskset pins individual processes to specific CPUs, cset creates isolated CPU sets where:

- Kernel threads are automatically migrated away from shielded cores
- System daemons are excluded from the shield
- Multiple processes can run inside the shield without individual pinning
- Memory policy can be combined with CPU shielding

## Why Self-Host and Manage CPU Affinity Locally?

Managing CPU affinity on your own bare-metal or dedicated servers gives you control over process placement that cloud instances often restrict. Virtual machines in cloud environments typically have their vCPU scheduling managed by the hypervisor, making fine-grained affinity settings less effective.

For database servers, pinning the database process to specific CPU cores ensures consistent cache behavior and eliminates scheduler-induced latency variance. For real-time applications (trading systems, audio processing, industrial control), CPU shielding prevents background tasks from causing timing jitter on critical cores.

For related performance optimization, see our [Linux I/O Schedulers guide](../2026-05-22-self-hosted-linux-io-scheduler-bfq-mq-deadline-kyber-guide/) for disk I/O tuning and [Linux HugePages management](../2026-05-22-self-hosted-linux-hugepages-management-libhugetlbfs-numactl-tuned-guide/) for NUMA-aware memory optimization. Our [interrupt management guide](../2026-05-23-self-hosted-linux-interrupt-management-irqbalance-tuned-irq-affinity-guide/) covers the complementary topic of hardware interrupt placement.

## Choosing the Right CPU Affinity Tool

| Scenario | Recommended Tool |
|----------|-----------------|
| Simple process pinning | taskset |
| Multi-socket server with NUMA | numactl |
| Real-time/low-latency workloads | cset shield |
| Database server on NUMA hardware | numactl with --cpunodebind and --membind |
| Container orchestration | taskset in container entrypoint |
| Kernel thread isolation | cset shield with --kthread=on |

## FAQ

### What is the difference between taskset and numactl?

taskset controls which CPU cores a process runs on but has no awareness of NUMA topology. numactl controls both CPU placement AND memory allocation across NUMA nodes. On a single-socket system, taskset is sufficient. On multi-socket servers, numactl is essential to avoid cross-NUMA memory access penalties.

### Does CPU affinity persist after a process restart?

No. CPU affinity set via taskset or numactl applies only to the launched process. If the process crashes and restarts, it returns to the default scheduler behavior. To persist affinity settings, use a systemd service unit with `CPUAffinity=` or `NUMAPolicy=` directives, or wrap the process launch in a startup script.

### Can I pin containers to specific CPUs?

Yes. Docker supports CPU pinning via `--cpuset-cpus` flag: `docker run --cpuset-cpus="0-3" myimage`. In Docker Compose, use `deploy.resources.limits.cpus` combined with a taskset wrapper in the entrypoint. Kubernetes uses `resources.limits.cpu` and node affinity for broader placement control.

### What is CPU shielding and why is it useful?

CPU shielding (provided by cset) moves all non-essential processes and kernel threads off designated CPU cores, creating an isolated environment for performance-critical workloads. This eliminates cache pollution from background tasks and prevents kernel thread interrupts on shielded cores. It is especially useful for real-time trading, audio processing, and industrial control systems.

### How do I verify CPU affinity is working?

Use `taskset -cp <PID>` to check a running process affinity. Use `numactl --show` inside the process to verify NUMA policy. For cset shields, use `cset shield --status` to see which processes are running inside the shield. The `/proc/<PID>/status` file also shows `Cpus_allowed_list` for any process.

### Does CPU affinity affect power consumption?

Yes. Pinning processes to fewer cores can allow unused cores to enter deep sleep states (C-states), reducing power consumption. However, concentrating load on fewer cores may increase their frequency (turbo boost), potentially increasing per-core power draw. The net effect depends on your workload and CPU architecture.

### Can I use taskset and numactl together?

Yes, but it is redundant. numactl includes CPU placement functionality (`--cpubind`), so you do not need taskset when using numactl. Use `numactl --cpubind=0-3 --membind=0 ./app` instead of chaining taskset and numactl together.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux CPU Affinity Management: taskset vs numactl vs cset",
  "description": "Compare taskset, numactl, and cset for Linux CPU affinity management. Learn process pinning, NUMA-aware placement, and CPU shielding for server performance optimization.",
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
