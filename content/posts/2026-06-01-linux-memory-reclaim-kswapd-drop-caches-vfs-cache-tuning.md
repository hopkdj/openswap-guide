---
title: "Self-Hosted Linux Memory Reclaim Management: kswapd vs drop_caches vs VFS Cache Tuning"
date: "2026-06-01"
tags: ["linux", "kernel", "memory-management", "system-administration", "performance-tuning", "monitoring"]
draft: false
---

## Introduction

Linux memory management is a delicate balancing act between keeping frequently accessed data cached and ensuring enough free memory for new allocations. When memory pressure builds, the kernel's reclaim subsystem kicks in — but the default behavior is not always optimal for every workload. Understanding how to monitor and tune memory reclaim can mean the difference between a responsive server and one that thrashes under load.

This guide compares the three primary mechanisms for Linux memory reclaim management: **kswapd tuning** (the background page reclaim daemon), **drop_caches operations** (manual cache eviction), and **VFS cache pressure tuning** (dentry/inode cache governance). Each approach serves a different purpose — from automated background reclaim to surgical cache management — and knowing when to apply each is critical for production system administration.

## Comparison Table

| Feature | kswapd Tuning | drop_caches | VFS Cache Pressure |
|---------|--------------|-------------|-------------------|
| **Mechanism** | Kernel thread (background reclaim) | Manual sysctl write | vm.vfs_cache_pressure kernel parameter |
| **Trigger** | Automatic (watermark-based) | Administrator-invoked | Continuous (policy-driven) |
| **Granularity** | Per-NUMA-node, per-zone | System-wide drop | dentry/inode ratio control |
| **Monitoring** | /proc/vmstat, /proc/zoneinfo | One-shot operation | /proc/slabinfo, slabtop |
| **Risk Profile** | Low (balancing algorithm) | High (can evict hot pages) | Medium (tuning required) |
| **Best For** | General memory pressure management | Pre-benchmark cleanup, emergency | Database servers, file servers |
| **Persistence** | Via sysctl.conf / sysctl.d | Ephemeral (one-time) | Via sysctl.conf / sysctl.d |
| **Overhead** | Negligible (background thread) | I/O spike during eviction | Policy overhead (minimal) |

## kswapd: The Background Reclaim Daemon

**kswapd** is the kernel's background memory reclaim thread. It wakes up when free memory drops below the "low" watermark and starts scanning anonymous and file-backed pages to find candidates for eviction. On multi-NUMA systems, there is one kswapd thread per NUMA node.

### Monitoring kswapd Activity

The primary interface for monitoring reclaim activity is `/proc/vmstat`. Key counters include:

```bash
# Monitor reclaim activity in real-time (1-second intervals)
watch -n 1 "grep -E 'pgsteal_|pgscan_|kswapd' /proc/vmstat"

# Check per-zone watermarks and reclaim stats
cat /proc/zoneinfo | grep -A 20 "Node 0, zone"
```

Key metrics to watch:
- **pgsteal_kswapd**: Pages reclaimed by kswapd (successful reclaim)
- **pgscan_kswapd**: Pages scanned by kswapd (effort expended)
- **pgsteal_direct**: Pages reclaimed via direct reclaim (synchronous, blocking)
- **pgscan_direct**: Pages scanned via direct reclaim

A high ratio of `pgscan_kswapd` to `pgsteal_kswapd` indicates inefficient reclaim (kswapd scanning many pages but finding few to evict). Direct reclaim (non-kswapd) is particularly concerning — it means kswapd cannot keep up, and processes are blocking on memory allocation.

### Tuning kswapd via Watermarks

The watermarks that control when kswapd activates are set in `/proc/sys/vm/`:

```bash
# View current watermark ratios (in 1/10000ths of zone size)
cat /proc/sys/vm/watermark_scale_factor
# Default: 10 (0.1% of zone) — increase for earlier kswapd activation

# Increase watermark scale factor for more aggressive background reclaim
echo 100 | sudo tee /proc/sys/vm/watermark_scale_factor

# Check min/low/high watermarks per zone
cat /proc/zoneinfo | grep -E "Node|watermark"
```

**Docker Compose for Monitoring Stack (Prometheus + Node Exporter):**

```yaml
version: "3.8"
services:
  node_exporter:
    image: quay.io/prometheus/node-exporter:latest
    container_name: node_exporter
    pid: host
    command:
      - "--collector.vmstat.fields=^(pgsteal_kswapd|pgscan_kswapd|pgsteal_direct|pgscan_direct|pgsteal_anon|pgsteal_file|pgmajfault).*"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
    ports:
      - "9100:9100"
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    restart: unless-stopped

volumes:
  prometheus_data:
```

## drop_caches: Manual Cache Eviction

The `/proc/sys/vm/drop_caches` interface provides administrator-controlled cache flushing. Unlike kswapd (which uses an aging algorithm), `drop_caches` is a blunt instrument that immediately frees specific cache types:

```bash
# View current cache usage before dropping
free -h
cat /proc/meminfo | grep -E "^(Cached|Buffers|SReclaimable):"

# Drop page cache only (safest option)
echo 1 | sudo tee /proc/sys/vm/drop_caches

# Drop dentries and inodes (VFS metadata cache)
echo 2 | sudo tee /proc/sys/vm/drop_caches

# Drop page cache, dentries, and inodes
echo 3 | sudo tee /proc/sys/vm/drop_caches

# Verify reclaim
free -h
```

**When to use drop_caches**: Pre-benchmark cache normalization, troubleshooting memory pressure where anonymous pages are being swapped despite large cache, and emergency memory reclamation when applications are OOM-killed. **When NOT to use it**: Routine operations (let kswapd handle it), high-performance database servers (flushing cache destroys query performance), and production systems under normal load.

**Automated Cache Pressure Monitoring Script:**

```bash
#!/bin/bash
# /usr/local/bin/memory-reclaim-monitor.sh
# Check if memory pressure requires intervention

THRESHOLD_PCT=95
USED_PCT=$(free | awk '/^Mem:/ {printf "%.0f", $3/$2 * 100}')

if [ "$USED_PCT" -gt "$THRESHOLD_PCT" ]; then
    echo "[$(date)] Memory at ${USED_PCT}% — checking reclaim metrics"
    DIRECT_RECLAIM=$(grep pgsteal_direct /proc/vmstat | awk '{print $2}')
    if [ "$DIRECT_RECLAIM" -gt 1000 ]; then
        echo "[$(date)] WARNING: High direct reclaim detected ($DIRECT_RECLAIM pages)"
        # Trigger controlled cache drop
        sync && echo 1 > /proc/sys/vm/drop_caches
    fi
fi
```

## VFS Cache Pressure Tuning

The Virtual Filesystem (VFS) cache stores dentries (directory entry objects) and inodes (file metadata) to accelerate filesystem operations. The `vm.vfs_cache_pressure` parameter controls how aggressively the kernel reclaims VFS cache relative to page cache:

```bash
# View current value (default: 100)
cat /proc/sys/vm/vfs_cache_pressure

# Decrease pressure — preserve VFS cache longer (good for file servers)
echo 50 | sudo tee /proc/sys/vm/vfs_cache_pressure

# Increase pressure — reclaim VFS cache more aggressively (good for database servers)
echo 200 | sudo tee /proc/sys/vm/vfs_cache_pressure
```

- **Value < 100**: Kernel prefers keeping dentry/inode cache over page cache
- **Value = 100**: Default balanced behavior
- **Value > 100**: Kernel prefers evicting dentry/inode cache first

Monitor the VFS cache size with:

```bash
# View slab cache statistics
slabtop -s c -o | head -20

# Check dentry and inode cache sizes
cat /proc/slabinfo | grep -E "^dentry|^ext4_inode|^xfs_inode"

# Monitor over time
watch -n 5 "grep -E '^(dentry|inode_cache|ext4_inode)' /proc/slabinfo"
```

### Swappiness as a Complementary Control

While not strictly part of the reclaim subsystem, `vm.swappiness` strongly influences reclaim behavior. Lower values favor keeping anonymous pages in memory and reclaiming file-backed pages instead:

```bash
# View current swappiness (default: 60)
cat /proc/sys/vm/swappiness

# Reduce swapping — keep anonymous pages in RAM longer (database servers)
echo 10 | sudo tee /proc/sys/vm/swappiness

# Increase swapping — prefer swapping over dropping file cache (desktop)
echo 100 | sudo tee /proc/sys/vm/swappiness
```

**Persisting sysctl settings** across reboots:

```bash
# Create a dedicated tuning file
cat << 'EOF' | sudo tee /etc/sysctl.d/99-memory-reclaim.conf
# Memory reclaim tuning for database server workload
vm.swappiness = 10
vm.vfs_cache_pressure = 50
vm.watermark_scale_factor = 100
vm.min_free_kbytes = 131072
EOF

# Apply
sudo sysctl --system
```

## Monitoring Tools Comparison

| Tool | Scope | Real-time | Historical | Best For |
|------|-------|-----------|------------|----------|
| /proc/vmstat | Kernel counters | Snapshot | Manual collection | Script-level monitoring |
| /proc/zoneinfo | Per-zone details | Snapshot | Manual collection | Watermark analysis |
| slabtop | Slab cache | Interactive (ncurses) | No | Cache composition |
| vmstat 1 | System-wide | Yes (1s intervals) | No | Quick overview |
| node_exporter | Kernel metrics | Via Prometheus | Yes (Prometheus TSDB) | Dashboard & alerting |
| BPF/bpftrace | Custom probes | Yes (programmatic) | Depends | Deep-dive analysis |

## Why Self-Host Your Memory Monitoring?

Running your own memory monitoring stack gives you complete control over what is collected and how long it is retained. Cloud monitoring services typically only retain metrics for 15-30 days, which is insufficient for detecting gradual memory pressure trends that develop over months. With a self-hosted Prometheus and Grafana stack, you can retain years of reclaim data, correlate memory pressure with application deployments, and build custom dashboards tailored to your workload patterns.

For broader Linux performance monitoring, see our [comprehensive profiling guide](../2026-05-22-self-hosted-linux-performance-profiling-perf-bcc-tools-sysstat-guide/). If you are managing cgroup-based memory limits, our [cgroup v2 administration guide](../2026-05-24-self-hosted-linux-cgroup-v2-administration-systemd-cgtop-cgroup-tools-libcgroup-guide/) covers resource constraint management in detail. For BPF-based scheduler analysis, our [sched-ext guide](../2026-05-23-self-hosted-linux-bpf-schedulers-sched-ext-scx-rusty-lavd-bpfland-guide/) covers how schedulers interact with memory pressure.

Memory reclaim tuning is not a one-time configuration — it requires ongoing monitoring and adjustment as workloads evolve. The tools in this guide provide the visibility and control needed to maintain optimal memory health across your Linux infrastructure.

## FAQ

### When should I use drop_caches vs tuning kswapd?

Use **drop_caches** for one-time interventions: before running benchmarks, after stopping a memory-intensive application, or when emergency memory is needed. Use **kswapd tuning** (watermark_scale_factor) for ongoing, automated reclaim management. kswapd tuning is always preferred for production — drop_caches is a diagnostic and emergency tool, not a regular maintenance operation.

### What is a healthy pgscan_kswapd to pgsteal_kswapd ratio?

A ratio below 10:1 is generally healthy — kswapd should reclaim at least 10% of scanned pages. Ratios above 50:1 indicate thrashing: kswapd is working hard but finding few evictable pages. This typically means the working set exceeds available memory and you should either add RAM or reduce the workload.

### How do I detect memory pressure before OOM kills happen?

Monitor `pgsteal_direct` in `/proc/vmstat` — non-zero and increasing values mean processes are blocking on direct reclaim. Set up alerting on `node_vmstat_pgsteal_direct` from node_exporter. Also watch `/proc/pressure/memory` (PSI — Pressure Stall Information) which provides a more nuanced view of memory pressure as percentages over 10s, 60s, and 300s windows.

### Does tuning vfs_cache_pressure affect SSDs differently than HDDs?

The parameter affects memory behavior, not I/O patterns directly. However, on SSD-based systems, reclaiming and later re-reading VFS cache has a lower performance penalty than on HDDs. For SSD servers, you can safely increase vfs_cache_pressure (200+) to free memory for application use. For HDD-based systems, keep it at default or lower (50-100) to avoid costly metadata re-reads from slow spinning disks.

### Can I disable kswapd entirely?

No. kswapd is a fundamental kernel thread required for the memory management subsystem. However, you can influence its behavior: set `vm.watermark_scale_factor` to a very high value (1000+) to make kswapd activate earlier and more aggressively, or set `vm.swappiness = 0` to make it strongly prefer reclaiming file-backed pages over anonymous pages. The kernel requires some reclaim mechanism — if kswapd cannot keep up, direct reclaim takes over, which is far worse for performance.

---

**💡 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到 科技监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测 科技相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Memory Reclaim Management: kswapd vs drop_caches vs VFS Cache Tuning",
  "description": "Comprehensive guide comparing Linux kernel memory reclaim mechanisms: kswapd background reclaim tuning, drop_caches manual eviction, and VFS cache pressure configuration for optimal server performance.",
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
