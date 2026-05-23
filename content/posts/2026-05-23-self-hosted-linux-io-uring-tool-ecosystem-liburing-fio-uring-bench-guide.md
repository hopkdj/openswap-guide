---
title: "Self-Hosted Linux io_uring Tool Ecosystem — liburing, fio, and uring-bench Guide"
date: "2026-05-23"
tags: ["linux", "io", "performance", "storage", "kernel"]
draft: false
---

Asynchronous I/O has been a longstanding challenge in Linux. Traditional `select`/`poll`/`epoll` handle network I/O well but fall short for **disk and storage operations**. The **io_uring** kernel interface, introduced by Jens Axboe in Linux 5.1, provides a high-performance, lock-free asynchronous I/O API that dramatically reduces syscall overhead for storage-intensive workloads.

This guide explores the io_uring tool ecosystem — **liburing** (the reference library), **fio** (the industry-standard benchmark with io_uring support), and **uring-bench** (dedicated io_uring benchmarking) — so you can measure, tune, and optimize I/O performance on your self-hosted servers.

## What Is io_uring?

io_uring is a Linux kernel interface that provides a **ring buffer-based** asynchronous I/O API. Unlike traditional synchronous I/O (blocking reads/writes) or `aio` (the older Linux async I/O interface with significant limitations), io_uring uses two shared ring buffers between kernel and user space:

- **Submission Queue (SQ)** — user space places I/O requests here
- **Completion Queue (CQ)** — kernel places completed I/O results here

This design eliminates the need for syscalls on every I/O operation, reducing context-switch overhead by **80-90%** compared to traditional approaches.

### Key io_uring Features

- **Zero-copy I/O** with registered buffers (`IORING_REGISTER_BUFFERS`)
- **Polling mode** (`IORING_SETUP_IOPOLL`) for ultra-low latency
- **Linked operations** for dependent I/O sequences
- **Timeout support** for I/O with deadlines
- **File registration** for reduced file descriptor lookup overhead
- **Provided buffers** for zero-allocation receive paths

## Comparing io_uring Tools

### liburing — Reference C Library

**liburing** (⭐3,662) is the official C library maintained by Jens Axboe, the creator of io_uring itself. It provides a clean C API wrapping the kernel io_uring syscalls.

**Key features:**
- Official reference implementation of the io_uring API
- Maintained by the io_uring kernel developer
- Minimal abstraction layer — close to the kernel interface
- Used by nginx, RocksDB, and many production databases
- Supports all io_uring features: SQ/CQ, registered buffers, polling, linked ops

**Best for:** C/C++ application developers, understanding the core io_uring API, building custom I/O engines.

### fio — Flexible I/O Tester

**fio** (⭐6,232) is the industry-standard storage benchmarking tool, also maintained by Jens Axboe. Its io_uring I/O engine (`io_uring`) is one of the most mature and feature-complete io_uring implementations available.

**Key features:**
- Comprehensive benchmarking: sequential, random, read, write, mixed workloads
- io_uring engine with full feature support (polling, registered buffers, fixed files)
- Real-world workload simulation with configurable I/O patterns
- Detailed latency percentiles, throughput, and IOPS reporting
- Scriptable with JSON output for automated performance testing

**Best for:** Storage benchmarking, I/O performance validation, comparing storage configurations (NVMe vs SSD vs HDD), tuning filesystem parameters.

### uring-bench — Dedicated io_uring Benchmark

**uring-bench** is a focused benchmarking tool designed specifically to measure io_uring performance characteristics. Unlike fio's broad feature set, uring-bench isolates io_uring-specific metrics.

**Key features:**
- Focused on io_uring performance measurement
- Compares io_uring vs POSIX AIO vs synchronous I/O
- Measures submission/completion latency distributions
- Tests polling vs interrupt-driven modes
- Lightweight, single-binary tool

**Best for:** Comparing io_uring against traditional I/O methods, measuring the impact of io_uring features (polling, registered buffers), quick performance validation.

## Comparison Table

| Feature | liburing | fio | uring-bench |
|---------|----------|-----|-------------|
| **Type** | C library | Benchmark tool | Benchmark tool |
| **Maintained by** | Jens Axboe | Jens Axboe | Community |
| **GitHub stars** | 3,662 | 6,232 | N/A |
| **I/O benchmarking** | ❌ (library only) | ✅ Comprehensive | ✅ Focused |
| **io_uring polling** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Registered buffers** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Latency percentiles** | ❌ (manual) | ✅ Full (p1-p99.999) | ✅ Basic |
| **Mixed workloads** | ❌ (manual) | ✅ Yes | ❌ |
| **Real-world simulation** | ❌ (manual) | ✅ Extensive | ⚠️ Limited |
| **Ease of use** | Low (C programming) | Medium (config files) | High (CLI flags) |
| **Production use** | nginx, RocksDB, etc. | Industry standard | Research/testing |

## Installation

### liburing

```bash
# Ubuntu/Debian
apt install -y liburing-dev

# Build from source (recommended for latest features)
git clone https://github.com/axboe/liburing.git
cd liburing
./configure
make -j$(nproc)
make install
```

### fio

```bash
# Ubuntu/Debian
apt install -y fio

# Build from source (for latest io_uring engine)
git clone https://github.com/axboe/fio.git
cd fio
./configure
make -j$(nproc)
make install

# Verify io_uring engine is available
fio --enghelp | grep io_uring
# Should show: io_uring
```

### uring-bench

```bash
# Build from source
git clone https://github.com/isilence/uring-bench.git
cd uring-bench
make -j$(nproc)
./uring-bench --help
```

## Benchmarking with fio and io_uring

### Basic Sequential Read Benchmark

```bash
fio --name=seq-read \
    --ioengine=io_uring \
    --iodepth=64 \
    --rw=read \
    --bs=128k \
    --direct=1 \
    --size=4G \
    --numjobs=4 \
    --runtime=60 \
    --group_reporting \
    --filename=/dev/sda
```

### Random Write with Polling Mode

```bash
fio --name=rand-write-poll \
    --ioengine=io_uring \
    --iodepth=256 \
    --rw=randwrite \
    --bs=4k \
    --direct=1 \
    --size=2G \
    --numjobs=8 \
    --hipri=1 \
    --runtime=60 \
    --group_reporting \
    --output-format=json \
    --filename=/dev/nvme0n1
```

### Registered Buffers Benchmark

```bash
fio --name=reg-buffers \
    --ioengine=io_uring \
    --registered_buffers=1 \
    --iodepth=32 \
    --rw=randread \
    --bs=4k \
    --direct=1 \
    --size=4G \
    --numjobs=16 \
    --runtime=120 \
    --group_reporting \
    --filename=/dev/nvme0n1
```

## Docker Deployment for Testing

Test io_uring performance inside Docker containers:

```yaml
version: "3.8"
services:
  io-benchmark:
    image: ubuntu:24.04
    privileged: true
    volumes:
      - /dev:/dev
      - ./benchmark-results:/results
    command: |
      bash -c '
        apt update && apt install -y fio git build-essential
        git clone https://github.com/axboe/fio.git /opt/fio
        cd /opt/fio && ./configure && make -j$(nproc) && make install

        # Run io_uring benchmark
        fio --name=io_uring-test \
            --ioengine=io_uring \
            --iodepth=64 \
            --rw=randread \
            --bs=4k \
            --direct=1 \
            --size=2G \
            --numjobs=4 \
            --runtime=30 \
            --group_reporting \
            --output=/results/io_uring.json \
            --output-format=json \
            --filename=/dev/sda
      '
    restart: "no"
```

## When io_uring Matters Most

io_uring provides the biggest performance gains for:

- **High-throughput databases** (PostgreSQL, RocksDB) with heavy disk I/O
- **Object storage servers** (MinIO, Ceph OSD) serving many concurrent requests
- **Log aggregation** pipelines (Vector, Fluentd) writing to disk
- **Media servers** (Jellyfin, Plex) streaming large files
- **Backup systems** performing sequential read/write operations

For storage server setup, see our [S3 object storage comparison](../2026-05-03-self-hosted-s3-object-storage-minio-seaweedfs-garage-guide/). For database query profiling, check our [database query optimization guide](../2026-04-23-self-hosted-database-query-profiling-optimization-tools-guide-2026/).

## Optimizing io_uring Performance

Beyond choosing the right tool, several kernel and application-level settings impact io_uring performance:

### Polling Mode vs Interrupt Mode

io_uring supports two operation modes:

- **Interrupt mode** (default) — the kernel sends an interrupt when I/O completes. Lower CPU usage but higher latency.
- **Polling mode** (`--hipri=1` in fio, `IORING_SETUP_IOPOLL` in liburing) — the application polls for completion. Higher CPU usage but significantly lower latency (microseconds vs milliseconds).

For latency-critical workloads (high-frequency trading, real-time databases), polling mode is essential. For throughput-oriented workloads (batch processing, backups), interrupt mode is more CPU-efficient.

### I/O Depth Tuning

The `iodepth` parameter controls how many I/O requests can be outstanding simultaneously. Higher values improve throughput but increase memory usage:

- **iodepth=1-4**: Low latency, single-threaded workloads
- **iodepth=8-32**: Balanced throughput and latency, most server workloads
- **iodepth=64-256**: Maximum throughput, bulk data processing

### Direct I/O vs Buffered I/O

Use `--direct=1` (O_DIRECT) to bypass the page cache. This is essential for accurate benchmarking and for workloads that manage their own caching (databases, key-value stores). Without O_DIRECT, the page cache can mask real storage performance.

## Why Self-Host with io_uring?

When you manage your own servers, understanding and tuning the I/O stack becomes critical for performance and cost efficiency. io_uring can significantly reduce the number of servers needed for I/O-heavy workloads — what previously required a fleet of machines with synchronous I/O can often be consolidated onto fewer machines with io_uring.

For self-hosted storage servers running MinIO or Ceph, io_uring enables higher throughput per node. For database servers, it reduces tail latency under concurrent load. For log aggregation pipelines using Vector or Fluentd, it allows higher ingestion rates without dropping events.

For storage server setup, see our [S3 object storage comparison](../2026-05-03-self-hosted-s3-object-storage-minio-seaweedfs-garage-guide/). For database query profiling, check our [database query optimization guide](../2026-04-23-self-hosted-database-query-profiling-optimization-tools-guide-2026/). For Linux performance profiling, our [perf and bcc-tools guide](../2026-05-22-self-hosted-linux-performance-profiling-perf-bcc-tools-sysstat-guide/) complements I/O benchmarking.


## FAQ

### What Linux kernel version is required for io_uring?
io_uring was introduced in **Linux 5.1** (May 2019). Most features work on 5.1+, but advanced features like `IORING_SETUP_COOP_TASKRUN` (5.19), `IORING_FEAT_EXT_ARG` (5.11), and registered ring sizing (5.12) require newer kernels. Linux 6.x has the most complete feature set.

### Does io_uring work with all filesystems?
io_uring works with most filesystems, but performance varies. **ext4**, **xfs**, and **btrfs** have full io_uring support. Some network filesystems (NFS, CIFS) have limited or no io_uring support. Always benchmark with your specific filesystem.

### Is io_uring faster than direct synchronous I/O?
For high-concurrency workloads (32+ simultaneous I/O operations), io_uring typically provides **2-5x throughput improvement** and **50-80% latency reduction** compared to synchronous I/O. For single-threaded, low-concurrency workloads, the difference is minimal.

### Can I use io_uring in Docker containers?
Yes. Containers need access to `/dev` devices and sufficient privileges. Use `--privileged` mode or add specific capabilities (`CAP_SYS_ADMIN`). The io_uring interface is a kernel-level API, so it works across container boundaries.

### Should I replace my application's I/O with io_uring?
Only if your application is I/O-bound and handles many concurrent operations. io_uring adds complexity to your codebase. Start by benchmarking with fio to confirm io_uring provides meaningful performance gains for your workload before investing in integration.

### Does io_uring work with NVMe drives?
Yes, io_uring works particularly well with NVMe drives. The **polling mode** (`IORING_SETUP_IOPOLL`) is especially effective on NVMe hardware, as it eliminates interrupt overhead for high-IOPS workloads.

## JSON-LD Structured Data

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux io_uring Tool Ecosystem — liburing, fio, and uring-bench Guide",
  "description": "Explore the Linux io_uring asynchronous I/O ecosystem — liburing for C API development, fio for comprehensive storage benchmarking, and uring-bench for focused io_uring performance testing.",
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
