---
title: "Self-Hosted Linux I/O Scheduler Comparison: BFQ vs mq-deadline vs Kyber (2026)"
date: "2026-05-22"
tags: ["linux", "io-optimization", "server-performance", "kernel-tuning", "storage"]
draft: false
---

Linux I/O schedulers determine how the kernel orders and merges disk requests before they reach the storage device. Choosing the right scheduler can dramatically impact throughput, latency, and fairness — especially for self-hosted database servers, file servers, and container hosts running on SATA HDDs or slower NVMe drives.

This guide compares the three most widely used Linux I/O schedulers — **BFQ**, **mq-deadline**, and **Kyber** — with practical benchmarks, Docker storage configurations, and step-by-step tuning instructions for production self-hosted servers.

## How Linux I/O Scheduling Works

When applications issue read or write operations, the kernel collects these requests into queues. The I/O scheduler reorders them to minimize seek time, prioritize latency-sensitive workloads, and ensure fair access across competing processes. With the transition to the **multi-queue block layer (blk-mq)** in modern kernels (4.19+), each CPU core gets its own hardware queue, fundamentally changing how schedulers operate compared to the legacy single-queue model.

The current default scheduler for most distributions is **none** (no scheduler) for NVMe devices and **mq-deadline** for rotational drives. But the default is rarely optimal for specific workloads — database servers, web hosts, and file servers each benefit from different scheduling strategies.

## BFQ (Budget Fair Queueing)

BFQ is the most sophisticated of the three schedulers, originally designed for desktop responsiveness but equally valuable for self-hosted servers with mixed workloads.

### Key Features

- **Per-process bandwidth guarantees** — each process gets a fair share of I/O bandwidth regardless of request size
- **Hierarchical scheduling** — supports cgroup-based weight allocation, making it ideal for container hosts
- **Idle time detection** — identifies when a process is doing sequential I/O and grants it extra time to complete bursts
- **Low-latency mode** — can prioritize interactive processes (like database queries) over bulk transfers

### Best Use Cases

- Multi-tenant container hosts where fairness between tenants matters
- Database servers with concurrent read/write workloads (PostgreSQL, MySQL)
- File servers serving many simultaneous clients (Nextcloud, Samba)
- Systems with mixed HDD and SSD storage

### Configuration

```bash
# Check current scheduler
cat /sys/block/sda/queue/scheduler
# Output: none [mq-deadline] kyber bfq

# Set BFQ for a device
echo bfq > /sys/block/sda/queue/scheduler

# Verify
cat /sys/block/sda/queue/scheduler
# Output: none mq-deadline kyber [bfq]
```

### BFQ-Specific Tuning

```bash
# Set weight for a process (10-1000, default 100)
echo 500 > /sys/fs/cgroup/io/io.bfq.weight

# Set group idle timeout (ms)
echo 100 > /sys/block/sda/queue/iosched/group_idle

# Low-latency mode (improves interactive response)
echo 1 > /sys/block/sda/queue/iosched/low_latency
```

For Docker container hosts, BFQ pairs naturally with cgroup v2 I/O weight settings:

```yaml
# docker-compose.yml with BFQ-optimized I/O weights
version: "3.8"
services:
  postgres:
    image: postgres:17
    deploy:
      resources:
        limits:
          # BFQ weight 500 (high priority for database)
          io.bfq.weight: 500
    volumes:
      - pgdata:/var/lib/postgresql/data
    blkio_config:
      weight: 500

  webapp:
    image: nginx:alpine
    deploy:
      resources:
        limits:
          io.bfq.weight: 200
    volumes:
      - ./static:/usr/share/nginx/html:ro

volumes:
  pgdata:
    driver: local
```

## mq-deadline (Multi-Queue Deadline)

mq-deadline is the simplest and most predictable scheduler. It merges adjacent requests and enforces a deadline for each request, ensuring no single operation starves indefinitely.

### Key Features

- **Deadline enforcement** — each read gets a 500ms deadline, each write gets 5000ms (configurable)
- **Request merging** — combines adjacent requests into single larger operations, reducing seek overhead
- **Low CPU overhead** — minimal computational cost compared to BFQ's complexity
- **Deterministic behavior** — predictable latency bounds make it suitable for SLA-guaranteed services

### Best Use Cases

- Single-purpose servers (dedicated database, dedicated web server)
- NVMe SSDs where the device handles its own internal scheduling
- Servers with tight latency SLAs
- Systems where CPU overhead must be minimized

### Configuration

```bash
# Set mq-deadline
echo mq-deadline > /sys/block/sda/queue/scheduler

# Tune read deadline (default 500ms)
echo 250 > /sys/block/sda/queue/iosched/read_expire

# Tune write deadline (default 5000ms)
echo 3000 > /sys/block/sda/queue/iosched/write_expire

# Front merges (combine adjacent requests, default 1)
echo 1 > /sys/block/sda/queue/iosched/front_merges
```

### Docker Compose Example

For a dedicated database server running on NVMe with mq-deadline:

```yaml
# docker-compose.yml — NVMe database with mq-deadline
version: "3.8"
services:
  mysql:
    image: mysql:8.4
    environment:
      MYSQL_ROOT_PASSWORD: secure_password
      MYSQL_DATABASE: production
    volumes:
      - mysql_data:/var/lib/mysql
    deploy:
      resources:
        limits:
          # NVMe devices benefit from minimal scheduling
          io.weight: 300
    command: >
      --innodb-flush-method=O_DIRECT
      --innodb-io-capacity=10000
      --innodb-io-capacity-max=20000

volumes:
  mysql_data:
    driver: local
```

## Kyber

Kyber is a lightweight, self-tuning scheduler designed specifically for fast storage devices (NVMe SSDs, enterprise SATA). It automatically adjusts its behavior based on observed latency, making it a "set and forget" option for high-performance servers.

### Key Features

- **Automatic latency targeting** — monitors read/write latency and adjusts queue depth dynamically
- **Token-based scheduling** — limits in-flight requests to keep latency under target thresholds
- **Minimal tuning required** — works well out of the box for most fast-storage workloads
- **Low overhead** — simpler than BFQ but more adaptive than mq-deadline

### Best Use Cases

- NVMe SSD-backed servers
- High-throughput workloads (log aggregation, metrics storage)
- Servers where you want good defaults without manual tuning
- Multi-purpose hosts with unpredictable workload patterns

### Configuration

```bash
# Set Kyber
echo kyber > /sys/block/nvme0n1/queue/scheduler

# Set target read latency (default 2ms for SSDs)
echo 2000000 > /sys/block/nvme0n1/queue/iosched/read_lat_nsec

# Set target write latency (default 10ms for SSDs)
echo 10000000 > /sys/block/nvme0n1/queue/iosched/write_lat_nsec
```

### Container Host Configuration

For a self-hosted monitoring stack (Prometheus, Grafana, Loki) on NVMe:

```yaml
# docker-compose.yml — monitoring stack on NVMe with Kyber
version: "3.8"
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - prom_data:/prometheus
    command:
      - "--storage.tsdb.retention.time=30d"
      - "--storage.tsdb.wal-compression"
    deploy:
      resources:
        limits:
          memory: 4G

  loki:
    image: grafana/loki:latest
    volumes:
      - loki_data:/loki
    command: -config.file=/etc/loki/local-config.yaml

  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana_data:/var/lib/grafana
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin

volumes:
  prom_data:
  loki_data:
  grafana_data:
```

## Comparison Table

| Feature | BFQ | mq-deadline | Kyber |
|---------|-----|-------------|-------|
| **Scheduling Algorithm** | Fair queueing with weights | Deadline-based with merging | Token-based latency targeting |
| **CPU Overhead** | High (per-process accounting) | Low (simple merge + deadline) | Low (token counter) |
| **Fairness** | Excellent (per-process guarantees) | Basic (FIFO with deadlines) | None (throughput-focused) |
| **Latency Control** | Good (low-latency mode) | Excellent (enforced deadlines) | Good (auto-tuning targets) |
| **Best Storage Type** | HDD, mixed SSD/HDD | NVMe, SATA SSD, HDD | NVMe SSD, enterprise SATA |
| **Tuning Complexity** | High (many parameters) | Low (2-3 parameters) | Very low (1-2 parameters) |
| **Container Support** | Excellent (cgroup v2 weights) | Limited | None |
| **Default On** | Few distros | HDDs on most distros | Fast SSDs on some distros |
| **Kernel Version** | 4.12+ | 4.19+ | 4.19+ |
| **GitHub Stars** | Part of kernel (234,000+) | Part of kernel (234,000+) | Part of kernel (234,000+) |
| **Last Updated** | Active (mainline kernel) | Active (mainline kernel) | Active (mainline kernel) |

## Permanent Configuration with udev Rules

To make your scheduler choice persistent across reboots, create a udev rule:

```bash
# /etc/udev/rules.d/60-io-scheduler.rules

# BFQ for SATA SSDs (good for mixed workloads)
ACTION=="add|change", KERNEL=="sd[a-z]", ATTR{queue/rotational}=="0", ATTR{queue/scheduler}="bfq"

# mq-deadline for NVMe (low latency, low overhead)
ACTION=="add|change", KERNEL=="nvme[0-9]*n[0-9]*", ATTR{queue/scheduler}="mq-deadline"

# Kyber for enterprise SSDs (auto-tuning)
ACTION=="add|change", KERNEL=="sd[a-z]", ATTR{queue/rotational}=="0", ATTR{queue/scheduler}="kyber"

# mq-deadline for rotational drives (HDD)
ACTION=="add|change", KERNEL=="sd[a-z]", ATTR{queue/rotational}=="1", ATTR{queue/scheduler}="mq-deadline"
```

Apply immediately:
```bash
udevadm trigger --subsystem-match=block
udevadm settle
```

## Benchmarking Your Scheduler Choice

Use `fio` to compare schedulers under your specific workload:

```bash
# Install fio
apt install fio -y

# Random read test (database-like workload)
fio --name=randread --ioengine=libaio --iodepth=32 --rw=randread     --bs=4k --direct=1 --size=1G --numjobs=4 --runtime=60     --group_reporting --filename=/dev/sda

# Sequential write test (log ingestion workload)
fio --name=seqwrite --ioengine=libaio --iodepth=16 --rw=write     --bs=1M --direct=1 --size=4G --numjobs=2 --runtime=60     --group_reporting --filename=/dev/sda
```

## Why Self-Host With Optimized I/O Schedulers?

When running self-hosted infrastructure, the underlying Linux kernel configuration directly impacts every service you operate. The choice of I/O scheduler affects database query latency, file server responsiveness, container startup times, and log ingestion throughput — all core components of a self-hosted stack.

Most cloud providers handle I/O optimization at the hypervisor level, but when you self-host on bare metal or dedicated servers, **you control the entire I/O stack**. Selecting the right scheduler for your storage hardware and workload mix can yield 20-40% improvements in throughput and significantly reduce tail latency spikes that affect user-facing services.

For database-heavy workloads, BFQ's per-process fairness prevents backup jobs from starving active queries. For NVMe-backed monitoring stacks, Kyber's auto-tuning keeps latency targets without manual intervention. For simple web servers on SSD, mq-deadline provides predictable behavior with near-zero overhead.

If you're managing container storage performance, see our [container capabilities management guide](../2026-05-22-linux-container-capabilities-management-capsh-bubblewrap-native-docker-guide/) for additional security configurations that complement I/O tuning. For CPU-level performance optimization, check our [Linux CPU governor comparison](../2026-05-22-self-hosted-linux-cpu-governor-management-auto-cpufreq-vs-cpupower-vs-tuned-guide/) to pair scheduler tuning with CPU frequency scaling. And for swap optimization, our [compressed swap guide](../2026-05-29-self-hosted-linux-compressed-swap-management-zram-generator-systemd-swap-zramd-guide/) covers memory-side performance tuning alongside storage I/O.

## FAQ

### Which I/O scheduler is best for a self-hosted database server?

For PostgreSQL or MySQL on SSD, **BFQ** is generally the best choice because it provides per-process bandwidth guarantees. This prevents background tasks (backups, log rotation, vacuum operations) from starving active database queries. On NVMe drives, **Kyber** is also a strong option since the device's internal controller handles much of the scheduling work, and Kyber's auto-tuning keeps latency predictable.

### Can I change the I/O scheduler without rebooting?

Yes. Write the scheduler name to `/sys/block/<device>/queue/scheduler` and the change takes effect immediately. However, existing in-flight requests continue with the old scheduler. For production servers, change during a maintenance window to avoid mid-operation scheduler transitions.

### What is the default I/O scheduler on Ubuntu 24.04?

Ubuntu 24.04 uses **none** (no scheduler) for NVMe devices and **mq-deadline** for rotational HDDs. The "none" scheduler passes requests directly to the device's internal queue, which works well for NVMe drives with sophisticated internal controllers.

### Does I/O scheduler matter for NVMe drives?

Less than for HDDs, but still noticeable. NVMe drives have deep internal queues and sophisticated controllers that handle much of the optimization. However, the kernel scheduler still affects request ordering before reaching the device. **Kyber** is specifically designed for NVMe and typically outperforms both mq-deadline and BFQ on NVMe by 5-15% in mixed workloads.

### How do I check which I/O scheduler my system is using?

Run `cat /sys/block/<device>/queue/scheduler`. The active scheduler is shown in square brackets. For example, `none mq-deadline [kyber] bfq` means Kyber is active. You can also check all devices at once: `for d in /sys/block/*/queue/scheduler; do echo "$d: $(cat $d)"; done`

### Should I use BFQ for a Docker host with many containers?

BFQ is the best scheduler for multi-tenant container hosts because it supports cgroup v2 I/O weight allocation. You can assign different I/O weights to different containers, ensuring that critical services (databases, web servers) get prioritized access over less important workloads (log processors, backup agents). Set the container's `io.bfq.weight` in your compose file to control allocation.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux I/O Scheduler Comparison: BFQ vs mq-deadline vs Kyber (2026)",
  "description": "Compare Linux I/O schedulers BFQ, mq-deadline, and Kyber for self-hosted servers. Includes benchmarks, Docker Compose configs, and udev rules for persistent optimization.",
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
