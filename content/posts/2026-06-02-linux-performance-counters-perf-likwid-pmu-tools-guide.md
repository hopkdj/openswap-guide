---
title: "Self-Hosted Linux Performance Monitoring: perf vs LIKWID vs pmu-tools — Complete Benchmarking Guide"
date: "2026-06-02"
tags: ["linux", "performance", "monitoring", "benchmarking", "profiling", "self-hosted", "observability"]
draft: false
---

## Introduction

Understanding CPU performance at the hardware level is essential for self-hosted infrastructure optimization. Modern x86 and ARM processors expose hundreds of Performance Monitoring Unit (PMU) counters — hardware registers that track cache misses, branch mispredictions, instruction throughput, and memory bandwidth. Three open-source tools dominate the Linux performance counter landscape: the kernel's built-in **perf** subsystem, the HPC-grade **LIKWID** (Like I Knew What I'm Doing) suite, and Intel's **pmu-tools** collection.

This guide compares all three across setup complexity, metric coverage, visualization capabilities, and integration with self-hosted monitoring stacks. Whether you're debugging a database performance regression or benchmarking a new server, the right tool choice dramatically reduces time to insight.

## Comparison Table

| Feature | perf | LIKWID | pmu-tools |
|---------|------|--------|-----------|
| Installation | Built into kernel | `apt install likwid` | Git clone + Python |
| Stars | Kernel: 235K+ | 1,907 | 2,229 |
| Last Update | Continuous | June 2026 | April 2026 |
| Counters Exposed | 200+ per CPU | 200+ per CPU | 200+ per CPU |
| Sampling Support | Yes (perf record) | Limited | Via perf underneath |
| Top-Down Analysis | Yes (perf stat) | Yes (likwid-perfctr) | Yes (toplev) |
| Uncore/RAPL | Basic | Extensive | Extensive |
| GUI/Web UI | Via perf.data | likwid-web | Grafana via toplev |
| Container Support | Full | Requires host access | Via perf events |
| MPI/HPC Aware | No | Yes (native) | No |
| Learning Curve | Moderate | Steep | Moderate |

## perf: The Kernel's Swiss Army Knife

The `perf` subsystem ships with every Linux kernel and provides the broadest compatibility across CPU architectures. It operates through the `perf_event_open()` syscall and exposes counters, tracepoints, kprobes, and uprobes from a single CLI.

### Installation & Basic Usage

```bash
# Verify kernel support
cat /proc/sys/kernel/perf_event_paranoid
# Set to 0 or -1 for full access
sudo sysctl kernel.perf_event_paranoid=-1

# Install userspace tools
sudo apt install linux-tools-common linux-tools-$(uname -r)

# List available PMU events
perf list

# Basic CPU-wide counter collection
sudo perf stat -e cycles,instructions,cache-references,cache-misses,branches,branch-misses \
    -a -- sleep 10
```

### Sampling with perf record

For production analysis, sampling mode captures call stacks with minimal overhead (typically 1-3%):

```bash
# Sample CPU cycles at 99Hz for 30 seconds
sudo perf record -F 99 -a -g -- sleep 30

# Generate interactive report
sudo perf report

# Generate flame graph data
sudo perf script | stackcollapse-perf.pl | flamegraph.pl > flame.svg
```

### Top-Down Analysis (Intel only)

Intel's Top-Down Microarchitecture Analysis identifies performance bottlenecks by category:

```bash
sudo perf stat --topdown -a -- sleep 10
# Outputs: retiring, bad speculation, frontend bound, backend bound
```

## LIKWID: HPC-Grade Precision

LIKWID provides deterministic counter measurements unaffected by kernel scheduling — critical for reproducible benchmarks. Its core differentiator is **pinning measurements to specific CPU cores** and **masking interrupts** during measurement windows.

### Docker Compose Setup

```yaml
version: "3.8"
services:
  likwid-web:
    image: ghcr.io/rrze-hpc/likwid:latest
    container_name: likwid
    privileged: true
    pid: "host"
    volumes:
      - /sys:/sys:ro
      - /proc:/proc:ro
      - /dev/cpu:/dev/cpu:ro
      - ./likwid-data:/data
    environment:
      - LIKWID_OUTPUT_DIR=/data
    command: ["likwid-web", "--port", "8080"]
    ports:
      - "8080:8080"
    restart: unless-stopped
```

### Topology Discovery

```bash
# Discover CPU topology, cache hierarchy, NUMA layout
likwid-topology

# List available performance groups
likwid-perfctr -a
```

### Precision Measurements

LIKWID's killer feature is `likwid-perfctr` which pins to specific cores:

```bash
# Measure memory bandwidth on CPU 0-3 with HPM marker API
likwid-perfctr -C 0-3 -g MEM -m -- sleep 10

# Measure specific performance group
likwid-perfctr -C 0 -g FLOPS_DP -m -- ./your_hpc_app
```

### LIKWID Marker API (C/C++)

```c
#include <likwid.h>

int main() {
    likwid_markerInit();
    likwid_markerRegisterRegion("compute_kernel");

    likwid_markerStartRegion("compute_kernel");
    // Your computation here
    likwid_markerStopRegion("compute_kernel");

    likwid_markerClose();
    return 0;
}
```

## pmu-tools: Intel Deep Dive

Andy Kleen's pmu-tools bridges perf and Intel-specific PMU features. Its standout tool is **toplev** — a pipeline bottleneck analyzer that maps hundreds of PMU events to high-level performance categories.

### Installation

```bash
git clone https://github.com/andikleen/pmu-tools.git
cd pmu-tools

# Install toplev dependencies
sudo apt install python3 python3-pip
pip3 install --user argparse

# Verify Intel CPU
grep -q "GenuineIntel" /proc/cpuinfo && echo "Intel CPU detected" || echo "Requires Intel CPU"
```

### toplev: Pipeline Bottleneck Analysis

```bash
# Level 1: Top-level categories
sudo ./toplev.py --core C0 -l1 -- sleep 5

# Level 3: Detailed microarchitecture breakdown
sudo ./toplev.py --core C0 -l3 --no-desc -- ./database_benchmark
```

### OCD: Optimized Call-graph Decoding

```bash
# Decode perf.data with Intel-specific optimizations
sudo perf record -e cpu/event=0xc4,umask=0x00,name=BR_INST_RETIRED/pp -a -g -- sleep 10
sudo ./ocperf.py report
```

### Integration with Self-Hosted Monitoring

```bash
# Pipe toplev output to Prometheus-compatible format
sudo ./toplev.py --core C0 -l1 --interval 5 --no-multiplex \
    --output /tmp/toplev.csv -- sleep 60

# Import into Grafana via CSV datasource or textfile collector
# Use node_exporter textfile collector:
while true; do
    sudo ./toplev.py --core C0 -l1 --no-desc --single-output \
        -- sleep 5 > /var/lib/node_exporter/textfile_collector/toplev.prom
    sleep 55
done
```

## Choosing the Right Tool

| Use Case | Best Tool | Why |
|----------|-----------|-----|
| Quick CPU overview on any Linux server | perf | Zero install, universal compatibility |
| HPC cluster benchmarking | LIKWID | Per-core pinning, MPI-aware, reproducible |
| Intel microarchitecture optimization | pmu-tools (toplev) | Top-down analysis, event-level detail |
| Container-native monitoring | perf | Works inside containers with appropriate permissions |
| Memory bandwidth analysis | LIKWID | MEM group provides all DRAM metrics |
| Production flame graphs | perf | perf record + perf script pipeline |
| Long-term trend monitoring | pmu-tools + Grafana | toplev CSV output feeds dashboards |

## Why Self-Host Your Performance Monitoring?

Running performance monitoring on your own infrastructure provides several critical advantages. First, you own the data — CPU telemetry never leaves your network, which is essential for security-conscious deployments in finance, healthcare, and defense. Second, self-hosted tools can be tuned to your specific hardware mix rather than relying on cloud vendor abstractions that hide PMU detail layers.

Cost control is another factor. Cloud monitoring services charge per metric and per gigabyte of ingestion — a single server generating 200+ PMU counters at 1-second intervals can cost hundreds of dollars per month. Self-hosted perf, LIKWID, and pmu-tools generate the same data for free. You only pay for the Grafana instance visualizing it.

For HPC environments running MPI jobs across hundreds of nodes, LIKWID's per-core pinning and cluster-wide aggregation capabilities have no cloud equivalent. The tool was designed by the Erlangen Regional Computing Center specifically for scientific computing workloads.

If you're exploring related performance topics, check our guide on [Linux CPU Scheduler Analysis](../2026-06-01-linux-cpu-scheduler-analysis-schedstat-sched-debug-perf-sched/) for scheduling latency insights. Our [Kernel Dynamic Tracing comparison](../2026-05-25-linux-kernel-dynamic-tracing-trace-cmd-vs-systemtap-vs-perf-probe-guide/) covers perf-probe and dynamic tracepoints. For I/O performance, see our [Block I/O Latency Tracing guide](../2026-05-24-self-hosted-block-io-latency-tracing-blktrace-vs-ioping-vs-iotop-guide/).

## FAQ

### Do these tools work on AMD CPUs?

Yes, with caveats. perf works fully on AMD Zen architectures and exposes AMD-specific PMU events. LIKWID has supported AMD since 2019 (EPYC and Ryzen), though some Intel-specific performance groups are unavailable. pmu-tools' toplev is Intel-only — AMD users should use `perf stat --topdown` on Zen 4+ processors instead.

### What kernel permissions are needed?

All three tools require access to the `perf_event_open()` syscall. Set `kernel.perf_event_paranoid=-1` for full access, or `0` to allow unprivileged users to measure their own processes. LIKWID additionally needs `/dev/cpu/*/msr` access (MSR module loaded) for certain metrics like RAPL energy counters.

### Can I monitor containers with these tools?

perf works inside containers with `CAP_PERFMON` or `CAP_SYS_ADMIN`. LIKWID requires host-level access since it programs MSRs directly. pmu-tools can monitor containerized workloads from the host by targeting the cgroup or the PID namespace of the container process.

### What's the performance overhead?

Sampling mode (`perf record -F 99`) typically adds 1-3% overhead. Counting mode (`perf stat`) is near-zero (<0.1%). LIKWID's `likwid-perfctr` is designed for zero-overhead during measurement windows by programming counters before the workload and reading after. pmu-tools' toplev uses multiplexing and may add 2-5% overhead depending on event count.

### How do I export metrics to Prometheus or Grafana?

Use the `node_exporter` textfile collector with toplev output piped to `.prom` files. For perf, use `perf stat --json` (kernel 5.10+) and parse with a Python script to Prometheus format. LIKWID outputs CSV natively via `-O csv` which can be ingested by Telegraf's CSV input plugin.

### Can I use these in CI/CD pipelines?

Yes. Run `perf stat` or `toplev.py` before and after code changes to detect performance regressions. LIKWID is ideal for CI benchmarking due to its reproducible, low-variance measurements. All three tools can be scripted and their outputs parsed for automated threshold alerts.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Performance Monitoring: perf vs LIKWID vs pmu-tools — Complete Benchmarking Guide",
  "description": "Comprehensive comparison of Linux performance counter tools: kernel perf, LIKWID HPC suite, and Intel pmu-tools. Includes Docker Compose configs, code examples, and self-hosted monitoring integration.",
  "datePublished": "2026-06-02",
  "dateModified": "2026-06-02",
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
