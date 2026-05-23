---
title: "Self-Hosted Linux BPF Schedulers — sched_ext, scx_rusty, and scx_bpfland Guide"
date: "2026-05-23"
tags: ["linux", "kernel", "cpu-scheduling", "bpf", "performance"]
draft: false
---

Linux CPU scheduling has historically been a kernel-only concern — you picked a scheduler (CFS, MuQSS, BFS) at compile time or patched your kernel, and lived with it. The **sched_ext** (scx) framework changes that paradigm entirely by exposing the Linux CPU scheduler as a programmable **eBPF** interface. This means you can load, unload, and switch schedulers at runtime without recompiling the kernel.

This guide compares the most mature schedulers built on the sched_ext framework — **scx_rusty**, **scx_lavd**, and **scx_bpfland** — so you can choose the right one for your self-hosted server workloads.

## What Is sched_ext?

sched_ext (scheduler extension) is a Linux kernel feature merged in **Linux 6.12** that allows user-space programs to load eBPF programs implementing CPU scheduling policies. The kernel provides a stable interface (the BPF scheduler operations, or `sched_ops`) while the scheduling logic — which tasks to run, when, and on which CPU — is defined by the loaded eBPF program.

The key advantages of sched_ext for self-hosted infrastructure:

- **Runtime scheduler switching** — load a different scheduler without rebooting
- **Workload-specific tuning** — pick a scheduler optimized for your use case (latency, throughput, NUMA awareness)
- **No kernel recompilation** — schedulers are loaded as eBPF programs
- **Fallback safety** — if a scheduler crashes, the kernel falls back to a default

The sched_ext project is maintained at [github.com/sched-ext/scx](https://github.com/sched-ext/scx) with active development and multiple scheduler implementations.

## Comparing sched_ext Schedulers

### scx_rusty — NUMA-Aware Load Balancing

**scx_rusty** is a domain-scoped, NUMA-aware load balancing scheduler. It divides CPUs into **domains** (typically NUMA nodes or L3 cache domains) and balances load across them using a **load-weighted** algorithm.

**Key features:**
- Divides CPUs into configurable domains
- Balances load across domains using a weighted algorithm
- Configurable via `--interval`, `--slice`, `--direct`, and `--greedy` flags
- Ideal for multi-socket servers with uneven workloads
- Supports **direct dispatch** for latency-sensitive tasks

**Best for:** Multi-socket servers, NUMA-heavy workloads, database servers.

### scx_lavd — Latency-Aware Virtual Deadline

**scx_lavd** (Latency-Aware Virtual Deadline) is designed for **low-latency** workloads. It assigns virtual deadlines to tasks based on their behavior — interactive tasks get shorter deadlines (higher priority), while CPU-bound batch tasks get longer deadlines.

**Key features:**
- Automatic task classification (interactive vs. CPU-bound)
- Virtual deadline scheduling for latency prioritization
- Performance mode (`--performance`) for throughput-oriented workloads
- Power-saving mode (`--powersave`) for energy efficiency
- Configurable CPU utilization boost threshold

**Best for:** Desktop workloads, latency-sensitive services (API servers, real-time processing), gaming servers.

### scx_bpfland — Task Classification Scheduler

**scx_bpfland** combines task classification with a **land-based** scheduling approach. It identifies task types (interactive, CPU-intensive, I/O-bound) and applies different scheduling policies to each class.

**Key features:**
- Automatic task type classification
- Separate scheduling policies per task class
- Supports **partial mode** (`--partial`) for hybrid scheduling
- Configurable via `--slice-us`, `--starvation`, and `--nr-procs` flags
- Good general-purpose scheduler for mixed workloads

**Best for:** Mixed workload servers, application servers running diverse services, general-purpose self-hosted infrastructure.

## Comparison Table

| Feature | scx_rusty | scx_lavd | scx_bpfland |
|---------|-----------|----------|-------------|
| **Scheduling algorithm** | Load-weighted domain balancing | Virtual deadline | Task classification |
| **NUMA awareness** | ✅ Yes (domain-scoped) | ❌ No | ⚠️ Partial |
| **Latency optimization** | ⚠️ Moderate (direct dispatch) | ✅ Excellent | ✅ Good |
| **Throughput optimization** | ✅ Excellent | ⚠️ Moderate (performance mode) | ✅ Good |
| **Task auto-classification** | ❌ No | ✅ Yes | ✅ Yes |
| **Configurable domains** | ✅ Yes | ❌ No | ❌ No |
| **Power saving mode** | ❌ No | ✅ Yes | ❌ No |
| **Fallback mode** | ✅ Yes (partial) | ❌ No | ✅ Yes (partial) |
| **Best workload** | NUMA servers, databases | Low-latency services | Mixed workloads |
| **Complexity** | High | Medium | Medium |

## Installation and Setup

All schedulers are built from the same source repository. You need a Linux 6.12+ kernel with `CONFIG_SCHED_CLASS_EXT=y`.

### Prerequisites

```bash
# Check kernel version (needs 6.12+)
uname -r

# Check if sched_ext is enabled
grep CONFIG_SCHED_CLASS_EXT /boot/config-$(uname -r)
# Should output: CONFIG_SCHED_CLASS_EXT=y
```

### Build from Source

```bash
# Install build dependencies
apt update && apt install -y build-essential clang llvm libelf-dev libbpf-dev pkg-config

# Clone the scx repository
git clone https://github.com/sched-ext/scx.git
cd scx

# Build all schedulers
make -j$(nproc)

# Verify the schedulers were built
ls -la scheds/rust/scx_*/target/release/scx_*
# You should see: scx_rusty, scx_lavd, scx_bpfland, etc.
```

### Running a Scheduler

```bash
# Switch to scx_rusty (NUMA-aware)
sudo ./target/release/scx_rusty --run-tick-ms 5

# Switch to scx_lavd (low-latency)
sudo ./target/release/scx_lavd --performance

# Switch to scx_bpfland (mixed workloads)
sudo ./target/release/scx_bpfland --slice-us 5000

# Monitor scheduler stats (each scheduler has a --stats flag)
sudo ./target/release/scx_rusty --run-tick-ms 5 --stats
```

## Docker Deployment for Testing

You can test sched_ext schedulers inside Docker containers with privileged access:

```yaml
version: "3.8"
services:
  scheduler-test:
    image: ubuntu:24.04
    privileged: true
    volumes:
      - /sys/fs/bpf:/sys/fs/bpf
      - /sys/kernel/debug:/sys/kernel/debug
    command: |
      bash -c '
        apt update && apt install -y build-essential clang llvm libelf-dev libbpf-dev git
        git clone https://github.com/sched-ext/scx.git /opt/scx
        cd /opt/scx && make -j$(nproc)
        ./target/release/scx_rusty --run-tick-ms 5 --stats
      '
    restart: "no"
```

For a production-like test, mount your application workload into the container and measure scheduling performance under different schedulers:

```yaml
version: "3.8"
services:
  scx-benchmark:
    image: ubuntu:24.04
    privileged: true
    volumes:
      - /sys/fs/bpf:/sys/fs/bpf
      - ./benchmark:/opt/benchmark
    command: |
      bash -c '
        apt update && apt install -y build-essential clang llvm libelf-dev libbpf-dev git sysstat
        git clone https://github.com/sched-ext/scx.git /opt/scx
        cd /opt/scx && make -j$(nproc)
        
        # Test each scheduler with a workload
        for sched in scx_rusty scx_lavd scx_bpfland; do
          echo "=== Testing $$sched ==="
          ./target/release/$$sched --run-tick-ms 5 &
          SCHED_PID=$$!
          sleep 2
          
          # Run benchmark
          /opt/benchmark/run.sh
          
          kill $$SCHED_PID 2>/dev/null
          sleep 2
        done
      '
    restart: "no"
```

## Choosing the Right Scheduler

### When to Use scx_rusty

- **Multi-socket servers** where NUMA locality matters
- **Database servers** (PostgreSQL, MySQL) with NUMA-aware memory allocation
- **Virtualization hosts** running VMs across multiple NUMA nodes
- **HPC clusters** where load balancing across sockets is critical

### When to Use scx_lavd

- **API servers** where response latency directly impacts user experience
- **Real-time processing** services (streaming, event processing)
- **Interactive workloads** — web terminals, development servers
- **Gaming servers** (Minecraft, Valheim) where tick latency matters

### When to Use scx_bpfland

- **Mixed workload servers** running databases, web servers, and batch jobs
- **General-purpose infrastructure** where no single workload dominates
- **Self-hosted PaaS** platforms (CapRover, Coolify) running diverse applications
- **When in doubt** — it provides the best general-purpose performance

## Monitoring Scheduler Performance

```bash
# Check current scheduler
cat /sys/kernel/sched_ext/root/ops

# View scheduler statistics (per-scheduler)
sudo scx_rusty --stats
sudo scx_lavd --stats
sudo scx_bpfland --stats

# Monitor with perf
sudo perf sched record -- sleep 10
sudo perf sched latency
```

## Why Self-Host with Custom Schedulers?

Most cloud providers and managed services use a one-size-fits-all kernel configuration. When you self-host your own infrastructure, you gain the ability to tune the entire stack — from the kernel scheduler up to the application layer.

Custom schedulers become critical when you run workloads that don't fit the default CFS scheduler's assumptions. A database server with NUMA-aware memory allocation benefits from domain-scoped scheduling. An API server serving thousands of concurrent requests needs low-latency task prioritization. A development server running IDEs, compilers, and containers needs balanced throughput across diverse task types.

For container runtime tuning, check our [OCI container runtimes comparison](../2026-05-09-oci-container-runtimes-crun-runc-youki-guide/). For CPU governor management, see our [Linux CPU governor guide](../2026-05-22-self-hosted-linux-cpu-governor-management-auto-cpufreq-vs-cpupower-vs-tuned-guide/). And for cgroup monitoring, our [cgroup tools comparison](../2026-05-22-self-hosted-cgroup-monitoring-tools-systemd-cgtop-vs-cgroup-tools-vs-libcgroup-guide/) complements scheduler tuning.

## FAQ

### What kernel version is required for sched_ext?
sched_ext was merged into the mainline Linux kernel in version **6.12**. You need at least 6.12 with `CONFIG_SCHED_CLASS_EXT=y` enabled in your kernel config. Some distributions may backport sched_ext to earlier kernel versions.

### Can I switch schedulers without rebooting?
Yes. One of sched_ext's key advantages is **runtime scheduler switching**. You simply kill the currently running scheduler process and start a new one. The kernel handles the transition automatically.

### Is sched_ext production-ready?
sched_ext is actively maintained and used in production by several organizations. However, it is still relatively new (merged in 6.12). The sched-ext project recommends testing your workload with different schedulers before deploying to production.

### Does sched_ext work in Docker containers?
Yes, but containers need **privileged mode** (`--privileged`) and access to `/sys/fs/bpf` and `/sys/kernel/debug`. The eBPF programs run at the kernel level, so they affect the entire host — not just the container.

### What happens if a scheduler crashes?
The kernel has a built-in **fallback mechanism**. If a loaded scheduler's eBPF program fails or is killed, the kernel falls back to its default scheduling behavior. This prevents system instability from scheduler bugs.

### Can I write my own scheduler?
Yes. The sched_ext framework provides a C API for writing schedulers. Several schedulers in the scx repository are written in Rust using the `libbpf-rs` bindings. The project documentation includes examples and tutorials.

## JSON-LD Structured Data

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux BPF Schedulers — sched_ext, scx_rusty, and scx_bpfland Guide",
  "description": "Compare Linux BPF schedulers built on the sched_ext framework — scx_rusty for NUMA-aware balancing, scx_lavd for low-latency workloads, and scx_bpfland for mixed workloads.",
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
