---
title: "Self-Hosted Linux CPU Scheduler Analysis: schedstat vs sched_debug vs perf sched"
date: "2026-06-01"
tags: ["linux", "kernel", "cpu", "scheduler", "performance-tuning", "system-administration", "debugging"]
draft: false
---

## Introduction

The Linux CPU scheduler is responsible for deciding which task runs on which CPU at any given moment. With the Completely Fair Scheduler (CFS) and the newer EEVDF scheduler in kernel 6.6+, understanding scheduler behavior is essential for diagnosing latency spikes, CPU contention, and uneven load distribution across cores. Linux provides several built-in tools for scheduler analysis, each offering a different level of detail and operational overhead.

This guide compares three primary Linux scheduler analysis interfaces: **schedstat** (runtime scheduling statistics), **sched_debug** (detailed per-CPU scheduler state), and **perf sched** (performance-event-based scheduler tracing). Each tool addresses different analysis needs — from quick health checks to deep latency investigations.

## Comparison Table

| Feature | schedstat | sched_debug | perf sched |
|---------|-----------|-------------|------------|
| **Data Source** | /proc/schedstat | /sys/kernel/debug/sched/debug | perf event subsystem |
| **Granularity** | Per-CPU aggregate counters | Per-CPU, per-runqueue, per-task | Per-task, per-event |
| **Overhead** | Negligible (<0.1% CPU) | Low (read-only snapshot) | Medium-High (event tracing) |
| **Enabled By Default** | Yes (CONFIG_SCHEDSTATS) | Yes (requires debugfs mount) | Yes (perf subsystem) |
| **Historical Analysis** | Manual collection | Snapshot only | Yes (trace recording) |
| **Latency Analysis** | Aggregate wait/run times | Per-task scheduling details | Microsecond-level event timeline |
| **Best For** | Health monitoring, dashboards | Detailed state inspection | Latency debugging, regression testing |
| **Output Format** | Key-value counters | Human-readable dump | Binary trace (perf.data) |

## schedstat: Runtime Scheduling Counters

The `/proc/schedstat` file provides aggregate per-CPU scheduling statistics. It is the lightest-weight option, suitable for continuous monitoring in production environments.

```bash
# View schedstat output — one line per CPU
cat /proc/schedstat
# Format per CPU line:
# version cpu_id
# yld_count sched_count sched_goidle
# ttwu_count ttwu_local
# wake_idx ...

# Parse schedstat into readable format
awk 'NR>1 && /cpu/ {
    cpu=$2; getline;
    printf "CPU %s: sched=%s wait=%s idle=%s\n", cpu, $1, $2, $3
}' /proc/schedstat
```

Key metrics from schedstat:
- **sched_count**: Total schedule() calls (context switches initiated by this CPU)
- **sched_goidle**: Times the scheduler found no runnable task (CPU went idle)
- **ttwu_count**: Try-to-wake-up events (tasks woken on this CPU)
- **ttwu_local**: Wake-ups where the waking and target CPU are the same

**schedstat Monitoring with Docker Compose:**

```yaml
version: "3.8"
services:
  schedstat_exporter:
    image: alpine:latest
    container_name: schedstat_exporter
    command: >
      sh -c "while true; do
        awk '/cpu0/{getline; print "schedstat_count "\$1; print "schedstat_ttwu "\$2}' /host/proc/schedstat;
        sleep 10;
      done"
    volumes:
      - /proc:/host/proc:ro
    restart: unless-stopped
```

## sched_debug: Detailed Scheduler State

The `sched_debug` interface provides an exhaustive snapshot of the scheduler's internal state — per-CPU runqueues, per-task scheduling statistics, and load balancing details. This is the tool to reach for when investigating why a specific task is not getting enough CPU time.

```bash
# Mount debugfs if not already mounted
sudo mount -t debugfs none /sys/kernel/debug

# View full scheduler debug output
cat /sys/kernel/debug/sched/debug

# Extract per-CPU runqueue summary
grep -A 5 "^runnable tasks" /sys/kernel/debug/sched/debug

# Check load balancing statistics
grep -A 2 "domain" /sys/kernel/debug/sched/debug | grep -E "name|load_balance|nr_balance_failed"
```

Key sections in sched_debug output:

**Per-CPU runqueue information:**
```
cpu#0, 2496.000 MHz
  .nr_running            : 3
  .nr_switches           : 18472934
  .nr_load_updates       : 528462
  .nr_uninterruptible    : -15
```

**Per-task scheduling statistics:**
```
runnable tasks:
 S           task   PID         tree-key  switches  prio     wait-time             sum-exec        sum-sleep
-----------------------------------------------------------------------------------------------------------
 S          bash  1923      2084.479178      9846   120         0.000000        56.123456       1234.567890
```

**Load balancing domain statistics:**
```
domain#0: MC
  .load_balance         : 49281
  .nr_balance_failed    : 127
  .imbalance_pct        : 117
```

### Automated sched_debug Collection

```bash
#!/bin/bash
# /usr/local/bin/sched-snapshot.sh
# Take a scheduler state snapshot for later analysis

SNAPSHOT_DIR="/var/log/sched_debug"
mkdir -p "$SNAPSHOT_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

cat /sys/kernel/debug/sched/debug > "$SNAPSHOT_DIR/sched_${TIMESTAMP}.txt"

# Rotate: keep last 100 snapshots
ls -t "$SNAPSHOT_DIR"/sched_*.txt | tail -n +101 | xargs rm -f 2>/dev/null
```

## perf sched: Event-Based Scheduler Tracing

`perf sched` provides the deepest scheduler analysis by recording tracepoint events and reconstructing the scheduling timeline. It can identify sub-millisecond latency issues that aggregate counters cannot capture.

```bash
# Record scheduler events for 30 seconds
sudo perf sched record -a -- sleep 30

# Generate latency analysis report
sudo perf sched latency

# Show the scheduling timeline
sudo perf sched timehist

# Map wakeup-to-schedule latencies
sudo perf sched map

# Trace specific task scheduling
sudo perf sched record -p $(pidof mysqld) -- sleep 60
```

**Sample perf sched latency output:**
```
---------------------------------------------------------------------------------
  Task                  |   Runtime ms  | Switches | Avg delay ms | Max delay ms |
---------------------------------------------------------------------------------
  mysqld:1234           |    2456.789   |    18923  |       0.123  |      12.456   |
  nginx:5678            |     123.456   |     4521  |       0.089  |       3.211   |
  kworker/u8:0          |      45.678   |     2341  |       0.045  |       1.044   |
---------------------------------------------------------------------------------
```

**perf sched timehist for visualizing wakeup chains:**

```bash
# Visualize task scheduling over a 5-second window
sudo perf sched timehist -w 5

# Filter by task name
sudo perf sched timehist --tid $(pidof postgres)
```

## Tool Selection Guide

| Use Case | Recommended Tool | Why |
|----------|-----------------|-----|
| Production monitoring | schedstat | Zero overhead, easy to scrape |
| Troubleshooting CPU contention | sched_debug | Per-task state and runqueue depth |
| Latency investigation | perf sched | Microsecond event timeline |
| Load balancing issues | sched_debug | Domain statistics and failure counts |
| Wakeup latency regression | perf sched latency | Wakeup-to-schedule gap analysis |
| Historical trend analysis | schedstat + Prometheus | Persistent counter storage |

## Why Self-Host Your Scheduler Monitoring?

Scheduler analysis is deeply system-specific — cloud monitoring services cannot access kernel debugging interfaces on your bare metal or virtual machines. Running schedstat collection locally and shipping metrics to a self-hosted Prometheus instance gives you continuous visibility into scheduler health. Combined with our [performance profiling guide](../2026-05-22-self-hosted-linux-performance-profiling-perf-bcc-tools-sysstat-guide/), scheduler metrics complete the picture of CPU resource utilization. For alternative scheduler deployments, our [BPF scheduler guide](../2026-05-23-self-hosted-linux-bpf-schedulers-sched-ext-scx-rusty-lavd-bpfland-guide/) covers sched-ext and custom scheduling policies. If you are managing containerized workloads, our [cgroup v2 guide](../2026-05-24-self-hosted-linux-cgroup-v2-administration-systemd-cgtop-cgroup-tools-libcgroup-guide/) covers CPU bandwidth control through cgroups.

## Choosing the Right Tool for Your Investigation

Selecting between schedstat, sched_debug, and perf sched depends on the type of problem you are trying to solve. For continuous monitoring, schedstat counters scraped into Prometheus provide always-on visibility without any measurable overhead. If you notice CPU latency spikes in application metrics, sched_debug gives you an immediate snapshot of runqueue depth and per-task scheduling statistics that can reveal CPU hogs. For deep-dive regression investigations — such as a kernel upgrade causing 5ms latency increases in a real-time application — perf sched recording with timehist analysis provides the microsecond-level event timeline needed to identify the root cause.

These tools also complement each other. A typical troubleshooting workflow starts with schedstat to confirm that context switch rates have increased, then moves to sched_debug to identify which tasks and CPUs are affected, and finally uses perf sched recording to capture the exact sequence of scheduling events that caused the issue. Keeping all three tools in your system administration toolkit ensures you can respond to scheduler issues at any level of detail.

## FAQ

### Do I need to enable CONFIG_SCHEDSTATS in my kernel?

On most modern distributions (kernel 5.x+), CONFIG_SCHEDSTATS is enabled by default. Check with `zgrep CONFIG_SCHEDSTATS /proc/config.gz`. If missing, `/proc/schedstat` will be empty or only show version info without per-CPU counters. Recompiling the kernel with this option enabled is straightforward on Debian/Ubuntu via `make menuconfig`.

### Why does sched_debug show negative nr_uninterruptible?

The `nr_uninterruptible` counter in sched_debug tracks tasks in uninterruptible sleep (D state). A negative value indicates a kernel accounting bug — the counter decrements more often than it increments, typically due to a race condition in the task state tracking. This is a cosmetic issue in most cases and does not affect scheduler correctness. Upgrading to a newer kernel may resolve it.

### How much overhead does perf sched recording add?

`perf sched record` adds approximately 1-5% CPU overhead on modern systems, depending on the event rate. On systems with very high context switch rates (>100K/s), overhead can reach 10-15%. Use short recording windows (30-60 seconds) and avoid running in production during peak hours. `perf sched latency` (analysis phase) has zero overhead since it post-processes an existing trace file.

### Can I use these tools inside containers?

`schedstat` (/proc/schedstat) and `sched_debug` (/sys/kernel/debug/sched/debug) require access to the host's procfs and debugfs. Run containers with `--pid=host` and mount `/proc:/host/proc:ro` plus `/sys/kernel/debug:/sys/kernel/debug:ro` to access these interfaces. `perf sched` requires `CAP_SYS_ADMIN` and access to the host's perf_event subsystem.

### What does a high sched_goidle count indicate?

`sched_goidle` counts the number of times the scheduler found no runnable task and the CPU went idle. A high count relative to `sched_count` (context switches) indicates the system has spare CPU capacity. A low ratio — where `sched_goidle` is near zero — means the CPU is saturated and continuously has work to schedule. For latency-sensitive workloads, this saturation point is where queuing delays begin to accumulate.

---

**💡 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到 科技监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测 科技相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux CPU Scheduler Analysis: schedstat vs sched_debug vs perf sched",
  "description": "In-depth comparison of Linux kernel scheduler analysis tools: schedstat, sched_debug, and perf sched for diagnosing CPU contention, latency spikes, and load balancing issues on production servers.",
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
