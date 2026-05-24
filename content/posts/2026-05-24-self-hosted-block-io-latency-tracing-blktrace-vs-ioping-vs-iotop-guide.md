---
title: "Self-Hosted Block I/O Latency Tracing: blktrace vs ioping vs iotop"
date: "2026-05-24"
tags: ["linux", "storage", "monitoring", "performance", "tracing"]
draft: false
---

When self-hosted storage infrastructure experiences performance degradation — slow database queries, delayed container pulls, or sluggish file server responses — the root cause often lies at the block device layer. Three tools dominate Linux block I/O latency analysis: **blktrace**, **ioping**, and **iotop**. Each provides a different lens into storage performance, from kernel-level event tracing to real-time process I/O monitoring.

This guide compares all three tools with practical deployment examples, Docker configurations for monitoring stacks, and decision frameworks for choosing the right tool for your homelab or production environment.

## Understanding Block I/O Latency

Block I/O latency measures the time between when a read or write request reaches the storage device and when the operation completes. High latency can indicate:

- **Disk saturation** — too many concurrent requests competing for limited IOPS
- **Scheduler bottlenecks** — suboptimal I/O scheduling algorithm for the workload
- **Hardware issues** — failing drives, degraded RAID arrays, or controller problems
- **Queue depth exhaustion** — storage device queue is full, requests are waiting
- **Filesystem overhead** — journal writes, metadata updates, or fragmentation

Unlike application-level metrics, block I/O tracing captures the complete lifecycle of storage requests as they pass through the Linux kernel's block layer, providing visibility that filesystem and process-level tools cannot match.

## blktrace: Kernel-Level Block I/O Tracing

blktrace is the most powerful block I/O tracing tool available on Linux. It hooks directly into the kernel's block layer to capture every I/O event, including queue inserts, driver dispatches, completions, and remaps.

### What blktrace Captures

blktrace records six event classes for each I/O request:

| Event Class | Description |
|-------------|-------------|
| **Q** (Queue) | Request inserted into the block layer queue |
| **G** (Get request) | Driver allocates a request structure |
| **I** (Insert) | Request inserted into the device dispatch queue |
| **D** (Issue) | Request sent to the device driver |
| **C** (Complete) | Request completed by the device |
| **P** (Plug) | Queue plugged (batching enabled) |

### Installing and Running blktrace

```bash
# Install blktrace
sudo apt install blktrace -y
# or
sudo yum install blktrace -y

# Start tracing on /dev/sda
sudo blktrace -d /dev/sda -o /tmp/sda-trace

# Let it run for 30 seconds, then stop
sleep 30
sudo pkill blktrace

# Parse the binary trace output into human-readable format
blkparse -i /tmp/sda-trace.blktrace.0 -d /tmp/sda-trace.txt

# Generate I/O latency histogram
blkparse -i /tmp/sda-trace.blktrace.0 -a issue,complete   | awk '{print $12}' | sort -n | uniq -c | head -20
```

### Docker Compose for blktrace Analysis Stack

```yaml
version: "3.8"
services:
  blktrace-collector:
    image: ubuntu:22.04
    container_name: blktrace-collector
    privileged: true
    pid: host
    volumes:
      - /dev:/dev
      - /sys:/sys
      - /tmp/blktrace-data:/data
    command: >
      bash -c "
        blktrace -d /dev/sda -o /data/sda-trace &
        BTPID=$!
        sleep 60
        kill $BTPID
        blkparse -i /data/sda-trace.blktrace.0 -d /data/sda-trace.txt
        btt -i /data/sda-trace.blktrace.0 -o /data/sda-btt.txt
      "
    restart: "no"

  visualization:
    image: grafana/grafana:latest
    container_name: blktrace-grafana
    restart: always
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
      GF_USERS_ALLOW_SIGN_UP: "false"

volumes:
  grafana-data:
    driver: local
```

### blktrace Analysis with btt (Block Trace Toolkit)

```bash
# Generate comprehensive I/O statistics
btt -i /tmp/sda-trace.blktrace.0 -o /tmp/sda-analysis.txt

# Key output sections:
# ──── Device Merge/Queue/Sector/IO Count Summary ────
# ──── Q2Q (Queue-to-Queue latency) ────
# ──── Q2D (Queue-to-Device latency) ────
# ──── D2C (Device-to-Complete latency) ────
# ──── I/O Latency Distribution ────
```

### blktrace Latency Metrics

| Metric | Description | Normal Range | Warning |
|--------|-------------|--------------|---------|
| **Q2Q** | Time between request queueings | < 1ms | > 10ms |
| **Q2D** | Time in queue before device dispatch | < 5ms | > 50ms |
| **D2C** | Device processing time | < 5ms (SSD) / < 10ms (HDD) | > 20ms / > 50ms |
| **I/O depth** | Concurrent requests in flight | 1-32 | > 256 |

blktrace provides the deepest visibility into block I/O behavior but requires kernel-level access and produces large trace files. It's best suited for targeted troubleshooting rather than continuous monitoring.

## ioping: Simple I/O Latency Measurement

ioping is a lightweight tool inspired by the `ping` command, designed specifically to measure storage latency in real-time. It sends read/write requests to a target and reports round-trip times, making it ideal for quick latency checks and continuous monitoring.

### Key Features

- **Ping-like interface** — familiar syntax for quick latency testing
- **Multiple I/O patterns** — sequential, random, cached, direct, write
- **Real-time statistics** — min/avg/max latency, IOPS, throughput
- **No kernel modules required** — works with standard Linux syscalls

### Installing and Running ioping

```bash
# Install ioping
sudo apt install ioping -y
# or
sudo yum install ioping -y

# Measure latency with default settings (4K reads)
ioping -c 10 /dev/sda

# Measure random read latency
ioping -R -c 20 /dev/sda

# Measure sequential write latency
ioping -W -c 20 /data/testfile

# Measure cached read latency
ioping -C -c 10 /dev/sda

# Continuous monitoring with interval
ioping -i 0.5 /dev/sda
```

### ioping Output Example

```
4 KiB <<< /dev/sda (block device 100 GiB): request=1 time=1.2 ms (warmup)
4 KiB <<< /dev/sda (block device 100 GiB): request=2 time=0.8 ms
4 KiB <<< /dev/sda (block device 100 GiB): request=3 time=1.1 ms
4 KiB <<< /dev/sda (block device 100 GiB): request=4 time=0.9 ms

--- /dev/sda (block device 100 GiB) ioping statistics ---
10 requests completed in 9.2 s, 40 KiB read, 1 iops, 4.3 KiB/s
generated 10 requests in 9.2 s
min/avg/max/mdev = 0.8 ms / 1.0 ms / 1.5 ms / 0.2 ms
```

### Docker Compose for Continuous ioping Monitoring

```yaml
version: "3.8"
services:
  ioping-monitor:
    image: alpine:latest
    container_name: ioping-monitor
    privileged: true
    volumes:
      - /dev:/dev
      - /data:/data
    command: >
      sh -c "
        apk add ioping &&
        while true; do
          ioping -c 5 -w 10 /dev/sda >> /data/ioping-log.txt
          sleep 300
        done
      "
    restart: always
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    restart: always
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.retention.time=30d"

volumes:
  prometheus-data:
    driver: local
```

### ioping Latency Benchmarks by Storage Type

| Storage Type | Sequential Read | Random Read | Random Write |
|-------------|-----------------|-------------|--------------|
| **NVMe SSD** | 0.05-0.15 ms | 0.08-0.25 ms | 0.10-0.35 ms |
| **SATA SSD** | 0.10-0.30 ms | 0.15-0.50 ms | 0.20-0.80 ms |
| **HDD (7200 RPM)** | 5-15 ms | 8-20 ms | 10-25 ms |
| **HDD RAID 10** | 3-8 ms | 5-12 ms | 6-15 ms |
| **Network (NFS)** | 1-5 ms | 2-10 ms | 3-15 ms |

ioping is the simplest tool for quick latency checks and continuous monitoring. Its ping-like interface makes it accessible to administrators who need fast answers without parsing complex trace output.

## iotop: Real-Time Process I/O Monitoring

iotop displays real-time I/O usage by process, similar to how `top` shows CPU usage. It identifies which processes are consuming the most disk bandwidth, making it essential for pinpointing the source of I/O contention.

### Key Features

- **Per-process I/O accounting** — see exactly which process is reading/writing
- **Real-time display** — updates every second by default
- **Thread-level detail** — can show individual thread I/O
- **Cumulative counters** — track total bytes read/written per process

### Installing and Running iotop

```bash
# Install iotop
sudo apt install iotop -y
# or
sudo yum install iotop -y

# Run iotop (requires root for full process visibility)
sudo iotop

# Show only processes actually doing I/O
sudo iotop -o

# Show threads instead of processes
sudo iotop -t

# Batch mode for logging
sudo iotop -b -n 5 -d 2 > /tmp/iotop-output.txt

# Cumulative mode (total I/O per process)
sudo iotop -a -o
```

### iotop Output

```
Total DISK READ: 125.43 M/s | Total DISK WRITE: 45.21 M/s
Current DISK READ: 89.12 M/s | Current DISK WRITE: 32.15 M/s
    TID  PRIO  USER     DISK READ  DISK WRITE  SWAPIN     IO>    COMMAND
   1234 be/4 mysql      45.23 M/s   12.34 M/s  0.00 %  89.12 % mysqld
   5678 be/4 root       22.15 M/s    8.91 M/s  0.00 %  45.67 % docker-containerd
   9012 be/4 postgres   15.67 M/s   18.45 M/s  0.00 %  34.21 % postgres: writer
   3456 be/4 www-data    5.12 M/s    3.21 M/s  0.00 %  12.34 % nginx: worker
```

### Docker Compose for iotop Exporter

```yaml
version: "3.8"
services:
  iotop-exporter:
    image: ubuntu:22.04
    container_name: iotop-exporter
    privileged: true
    pid: host
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
    command: >
      bash -c "
        apt update && apt install -y iotop
        while true; do
          iotop -b -n 1 -o >> /tmp/iotop-export.log
          sleep 10
        done
      "
    restart: always

  node-exporter:
    image: prom/node-exporter:latest
    container_name: node-exporter
    restart: always
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - "--path.procfs=/host/proc"
      - "--path.sysfs=/host/sys"
      - "--path.rootfs=/rootfs"
```

### iotop vs blktrace: When to Use Each

| Scenario | Best Tool | Reason |
|----------|-----------|--------|
| **Which process is hogging disk I/O?** | iotop | Shows per-process bandwidth |
| **What is the latency of individual requests?** | blktrace | Captures Q2D/D2C timing |
| **Is the disk saturated or just slow?** | ioping | Measures raw device latency |
| **Are I/O requests being merged?** | blktrace | Shows merge events |
| **Quick sanity check before deep dive?** | ioping | One command, instant results |
| **Long-term I/O monitoring?** | ioping + Prometheus | Continuous interval-based checks |

## Comparison: blktrace vs ioping vs iotop

| Feature | blktrace | ioping | iotop |
|---------|----------|--------|-------|
| **Event granularity** | Per-I/O event | Per-request latency | Per-process bandwidth |
| **Kernel access required** | Yes (block layer hooks) | No (standard syscalls) | Yes (proc accounting) |
| **Trace file size** | Large (GB/hour) | Minimal | Minimal |
| **Continuous monitoring** | Not ideal | Yes | Yes (batch mode) |
| **Latency percentiles** | Yes (full distribution) | Yes (min/avg/max) | No |
| **Process identification** | Partial (via btt) | No | Yes (primary function) |
| **I/O type breakdown** | Read/write/discard | Configurable | Read/write |
| **Learning curve** | Steep | Gentle | Gentle |
| **Production overhead** | Moderate (trace buffering) | Low | Low |

## Why Self-Host Block I/O Tracing?

Monitoring block I/O latency is essential for any self-hosted infrastructure that depends on storage performance. Here's why local tracing tools matter:

1. **Database performance** — Database engines like PostgreSQL and MySQL are extremely sensitive to storage latency. A 10ms increase in average block latency can translate to a 2x increase in query response time under concurrent load. Tools like blktrace reveal whether latency spikes originate from the device, the scheduler, or filesystem journaling.

2. **Container storage optimization** — Container workloads that perform frequent small reads (package managers, log rotators, config readers) are particularly sensitive to random read latency. ioping's random read mode identifies storage bottlenecks before they impact container startup times.

3. **RAID and LVM troubleshooting** — When running software RAID or LVM volumes, I/O requests pass through multiple layers before reaching physical devices. blktrace can trace requests through the entire stack, identifying whether latency originates from the RAID rebuild, LVM snapshot, or underlying device.

4. **Capacity planning** — Continuous ioping monitoring establishes baseline latency metrics for your storage infrastructure. When new workloads are added, comparing against baseline reveals whether the storage subsystem can handle additional load or needs expansion.

5. **Hardware validation** — When deploying new SSDs or configuring RAID arrays, ioping provides quick benchmarks to verify that hardware delivers advertised performance. blktrace confirms that the I/O scheduler and queue depth are optimally configured for the workload type.

For storage filesystem optimization, see our [Linux software RAID comparison](../2026-05-23-linux-software-raid-mdadm-vs-btrfs-vs-zfs-guide/) and [Linux data integrity verification guide](../2026-05-24-self-hosted-linux-data-integrity-verification-dm-verity-fs-verity-dm-integrity-guide/).
For I/O scheduler tuning, check our [Linux I/O schedulers deep dive](../2026-05-22-linux-io-schedulers-bfq-mq-deadline-kyber-guide/).


<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Block I/O Latency Tracing: blktrace vs ioping vs iotop",
  "description": "Compare blktrace, ioping, and iotop for self-hosted Linux block I/O latency analysis — kernel-level tracing, real-time monitoring, and per-process accounting.",
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

### What is the difference between blktrace and ioping?

blktrace captures every I/O event at the kernel block layer level, providing detailed timing information for each phase of an I/O request (queue, dispatch, completion). ioping sends test I/O requests and measures round-trip latency, similar to how `ping` measures network latency. blktrace is for deep analysis; ioping is for quick checks.

### Does iotop work inside Docker containers?

iotop can run inside Docker containers if the container is started with `--privileged` flag or with `--cap-add SYS_ADMIN` and access to the host's `/proc` filesystem via `--pid=host`. Without these, iotop can only see I/O from processes within the container's PID namespace.

### How do I interpret blktrace D2C latency values?

D2C (Device-to-Complete) latency measures the time from when a request is issued to the device driver until the device reports completion. For NVMe SSDs, D2C should typically be under 0.5ms. For SATA SSDs, under 1ms. For spinning disks, under 10ms. Higher values indicate device saturation, hardware issues, or queue depth exhaustion.

### Can ioping measure write latency without creating actual files?

Yes, ioping supports write mode (`-W`) that measures write latency by writing to a temporary file and immediately deleting it. Use `ioping -W -c 10 /path/to/directory` to measure write latency. For raw device write testing, use `ioping -W /dev/sda` (requires root).

### Why does iotop show 0.00 B/s for some processes that are clearly doing I/O?

iotop relies on the kernel's task delay accounting subsystem. If delay accounting is disabled (`/proc/sys/kernel/task_delayacct` is 0), iotop cannot report accurate I/O statistics. Enable it with `echo 1 > /proc/sys/kernel/task_delayacct` or add `delayacct` to your kernel boot parameters.

### Is blktrace safe to run on production systems?

blktrace has minimal overhead when tracing moderate I/O workloads — typically 1-3% CPU overhead. However, trace files can grow very quickly (hundreds of MB per minute on busy systems). Always specify output directories with sufficient space and limit tracing duration. For production monitoring, prefer ioping with Prometheus integration instead of continuous blktrace.

### How do I correlate blktrace output with specific application processes?

Use the **btt** (Block Trace Toolkit) utility that comes with blktrace. Run `btt -i trace.blktrace.0` to get per-process I/O statistics. For more detailed correlation, combine blktrace with `strace` on the target application process, or use the `seekwatcher` tool to visualize blktrace output alongside application activity.
