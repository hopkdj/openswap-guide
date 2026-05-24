---
title: "Self-Hosted Linux Storage Caching: dm-writecache vs bcache vs FlashCache"
date: "2026-05-24"
tags: ["linux", "storage", "caching", "performance", "self-hosted", "kernel"]
draft: false
---

Linux offers multiple block-level caching solutions that sit between fast storage (NVMe SSDs) and slow storage (HDDs) to accelerate I/O without requiring expensive all-flash arrays. These kernel-level caching technologies intercept block I/O at the device-mapper layer, transparently caching frequently accessed data on faster media.

In this guide, we compare three Linux storage caching technologies: **dm-writecache** for SSD write acceleration, **bcache** for full read/write caching, and **FlashCache** for enterprise-grade write-back caching. We cover installation, configuration, performance characteristics, and when each technology is the right choice.

## What Is Block-Level Storage Caching?

Block-level caching operates below the filesystem layer, caching raw disk blocks rather than file-level data. This means:

- **Filesystem agnostic**: Works with ext4, XFS, Btrfs, ZFS, or any other filesystem.
- **Transparent to applications**: No application changes required.
- **Hardware independent**: Works with any block device (NVMe, SATA SSD, HDD, iSCSI, LVM volumes).
- **Kernel integrated**: Zero-copy data paths through the Linux kernel's I/O stack.

Block caching differs from filesystem-level caching (ZFS ARC, Btrfs page cache) and application-level caching (Redis, Memcached). It sits at the lowest level of the storage stack, providing universal acceleration.

## dm-writecache: SSD Write Acceleration

dm-writecache is a device-mapper target introduced in Linux kernel 4.12 that uses a fast device (SSD/NVMe) as a write cache for a slow device (HDD). It is designed specifically for write-intensive workloads where sequential writes to HDDs are the bottleneck.

### Architecture

dm-writecache operates in write-back mode only — it does not cache reads. Write operations land on the fast SSD first, then are flushed to the HDD in the background by a dedicated kernel thread. This design provides:

- **Write coalescing**: Multiple small writes are combined into larger sequential writes on the HDD.
- **Reduced write amplification**: The HDD receives fewer, larger I/O operations.
- **Predictable latency**: Writes complete at SSD speed, decoupling application latency from HDD performance.

### Installation

dm-writecache is built into the Linux kernel (since 4.12). No compilation is needed:

```bash
# Verify kernel support (should return "dm_writecache")
cat /proc/modules | grep dm_writecache

# Install dmsetup if not present
apt-get install dmsetup   # Debian/Ubuntu
yum install device-mapper # RHEL/CentOS
```

### Configuration

```bash
# Create a dm-writecache device
# Format: fast_dev, slow_dev, cache_name, block_size
sudo dmsetup create mycache --table "0 $(blockdev --getsz /dev/sdb) writecache /dev/nvme0n1 /dev/sdb 512"

# The cached device appears at /dev/mapper/mycache
# Format and mount as usual
mkfs.xfs /dev/mapper/mycache
mount /dev/mapper/mycache /mnt/cached

# Check status
sudo dmsetup status mycache
# Output: 0 1953519616 writecache total_blocks 2097152 blocks_written 524288 writes 2097152
```

### Docker Compose for Testing

```yaml
version: "3.8"
services:
  dm-writecache-test:
    image: ubuntu:24.04
    privileged: true
    volumes:
      - /dev:/dev
      - ./setup-cache.sh:/setup-cache.sh
    command: ["/bin/bash", "/setup-cache.sh"]
```

```bash
#!/bin/bash
# setup-cache.sh - creates loopback devices for testing
dd if=/dev/zero of=/tmp/slow_disk.img bs=1M count=1024
dd if=/dev/zero of=/tmp/fast_disk.img bs=1M count=256
losetup /dev/loop0 /tmp/slow_disk.img
losetup /dev/loop1 /tmp/fast_disk.img
dmsetup create testcache --table "0 2097152 writecache /dev/loop1 /dev/loop0 512"
dmsetup status testcache
```

### Performance Tuning

```bash
# Set the writeback threshold (bytes before background flush starts)
echo 67108864 > /sys/block/dm-0/dm/writecache/writeback_threshold

# Set high water mark (bytes before writes are throttled)
echo 268435456 > /sys/block/dm-0/dm/writecache/high_watermark

# Monitor cache statistics
cat /sys/block/dm-0/dm/writecache/stats
# Writes: 524288, Writes skipped: 1024, Cache hits: 4096
```

### When to Use dm-writecache

dm-writecache excels for **write-heavy workloads** where the HDD is the bottleneck:
- Database write-ahead logs (WAL) on HDD with SSD cache
- Log aggregation systems writing to HDD
- Video surveillance recording to HDD with SSD buffer
- CI/CD build artifact storage

It is NOT suitable for read-heavy workloads since it does not cache reads. For those scenarios, consider bcache instead.

## bcache: Full Read/Write Block Caching

bcache is a Linux kernel block cache layer (merged in kernel 3.10) that uses a fast SSD to cache both reads and writes for a slow backing device. It supports write-through, write-back, and write-around modes.

### Architecture

bcache registers a caching device (SSD) and attaches one or more backing devices (HDDs) to it. The SSD can cache multiple backing devices simultaneously, making it cost-effective for multi-disk servers.

```
  ┌─────────────────────────────────────┐
  │          SSD (cache device)          │
  │  ┌──────────┐  ┌──────────┐         │
  │  │ HDD 1    │  │ HDD 2    │  ...    │
  │  │ cached   │  │ cached   │         │
  │  └──────────┘  └──────────┘         │
  └─────────────────────────────────────┘
```

### Installation

bcache is built into the Linux kernel (since 3.10). Install userspace tools:

```bash
# Debian/Ubuntu
apt-get install bcache-tools

# RHEL/CentOS
yum install bcache-tools
```

### Configuration

```bash
# Make the SSD a bcache cache device
make-bcache -C /dev/nvme0n1

# Make the HDD a bcache backing device
make-bcache -B /dev/sdb

# The cached device appears at /dev/bcache0
# If the cache device UUID doesn't match, register it:
echo <cache-device-UUID> > /sys/block/bcache0/bcache/attach

# Set caching mode
echo writeback > /sys/block/bcache0/bcache/cache_mode
# Options: writethrough, writeback, writearound, none

# Format and mount
mkfs.xfs /dev/bcache0
mount /dev/bcache0 /mnt/bcache
```

### Docker Compose Setup

```yaml
version: "3.8"
services:
  bcache-test:
    image: ubuntu:24.04
    privileged: true
    volumes:
      - /dev:/dev
      - ./setup-bcache.sh:/setup-bcache.sh
    command: ["/bin/bash", "/setup-bcache.sh"]
```

```bash
#!/bin/bash
# setup-bcache.sh
apt-get update && apt-get install -y bcache-tools
dd if=/dev/zero of=/tmp/slow.img bs=1M count=1024
dd if=/dev/zero of=/tmp/fast.img bs=1M count=256
losetup /dev/loop0 /tmp/slow.img
losetup /dev/loop1 /tmp/fast.img
make-bcache -C /dev/loop1
make-bcache -B /dev/loop0
cat /sys/block/bcache0/bcache/state
```

### Cache Mode Comparison

| Mode | Description | Use Case |
|------|------------|----------|
| `writethrough` | Writes go to both cache and backing device | Safety-first; no data loss on SSD failure |
| `writeback` | Writes go to cache first, flushed later | Maximum write performance |
| `writearound` | Writes bypass cache, go directly to backing device | Write-once workloads |
| `none` | Caching disabled | Maintenance mode |

### Monitoring

```bash
# Cache statistics
cat /sys/block/bcache0/bcache/stats_total/*
# cache_hits: 150234
# cache_misses: 48321
# cache_bypasses: 1205
# cache_hit_ratio: 75.6%

# Current cache state
cat /sys/block/bcache0/bcache/state
# Output: "clean" (cache is consistent) or "dirty" (unflushed writes exist)
```

## FlashCache: Enterprise Write-Back Caching

FlashCache was developed by Facebook (now Meta) as a general-purpose write-back block cache for Linux. With 1,602 GitHub stars, it was widely used in production at Facebook for database acceleration. However, the project has seen minimal updates since 2021 and is considered legacy.

### Architecture

FlashCache operates as a device-mapper target, similar to dm-writecache but with more features:
- Write-back caching with configurable dirty block limits
- SSD wear leveling and bad block management
- Cache persistence across reboots
- Configurable block sizes (512B to 64KB)

### Installation

```bash
# Install build dependencies
apt-get install build-essential linux-headers-$(uname -r)

# Clone and build
git clone https://github.com/facebook/FlashCache.git
cd FlashCache
make && make install

# Load the kernel module
modprobe flashcache
```

### Configuration

```bash
# Create a FlashCache device
flashcache_create -p back cached_ssd /dev/nvme0n1 /dev/sdb

# The cached device appears at /dev/mapper/cached_ssd
mkfs.xfs /dev/mapper/cached_ssd
mount /dev/mapper/cached_ssd /mnt/flashcache

# Check status
dmsetup status cached_ssd
flashcache_stat /dev/mapper/cached_ssd
```

### Configuration Options

```bash
# Set cache mode
dmsetup message cached_ssd 0 set_caching_mode writeback

# Set dirty block limit (max unflushed blocks before throttling)
echo 1048576 > /sys/module/flashcache/parameters/dirty_thresh_pct

# Set SSD discard support (TRIM)
echo 1 > /sys/module/flashcache/parameters/ssd_discard
```

## Comparison Table

| Feature | dm-writecache | bcache | FlashCache |
|---------|--------------|--------|------------|
| **Kernel Integration** | Built-in (4.12+) | Built-in (3.10+) | External module |
| **Read Caching** | No | Yes | Yes |
| **Write Caching** | Yes (write-back) | Yes (4 modes) | Yes (write-back) |
| **Multiple Backing Devices** | No (1:1) | Yes (1:N) | No (1:1) |
| **Active Development** | Yes (kernel mainline) | Yes (kernel mainline) | No (last update 2021) |
| **SSD Wear Leveling** | No | No | Yes |
| **Cache Persistence** | Yes | Yes | Yes |
| **Production Stability** | High (mainline) | High (mainline) | Moderate (legacy) |
| **Best For** | Write-heavy workloads | General caching | Legacy enterprise deployments |

## Choosing the Right Caching Technology

| Workload | Recommended Technology |
|----------|----------------------|
| Database write-heavy (WAL, transaction logs) | dm-writecache |
| General server with mixed read/write | bcache (writethrough) |
| High-performance read caching | bcache (writeback) |
| Legacy enterprise FlashCache deployment | FlashCache (migration recommended) |
| Multi-HDD server with single SSD | bcache (1:N caching) |

## Why Self-Host Storage Caching?

Deploying block-level caching on self-hosted infrastructure provides significant performance benefits without the cost premium of all-flash storage arrays. Cloud providers charge premium rates for high-IOPS storage tiers — implementing dm-writecache or bcache on self-hosted hardware can deliver 10-50x IOPS improvement for a fraction of the cost.

**Cost efficiency**: A 256GB NVMe SSD ($30) caching 4TB of HDD storage ($80) provides near-SSD performance for frequently accessed data at 25% of the all-flash cost. For multi-disk servers, bcache's 1:N ratio (one SSD caching multiple HDDs) further improves the cost-per-GB ratio.

**Performance predictability**: Block-level caching operates below the filesystem layer, meaning it works with any filesystem and any application. Database performance, file server throughput, and backup speeds all benefit transparently without application-level changes.

**Data control**: Unlike cloud storage acceleration features (AWS EBS Provisioned IOPS, Azure Premium SSDs), self-hosted caching keeps data entirely on your hardware. For compliance-sensitive workloads, this eliminates data residency concerns associated with cloud-managed storage tiers.

For comprehensive storage management, see our [storage replication guide](../2026-05-08-self-hosted-storage-replication-drbd-zfs-glusterfs-georep-guide/) covering DRBD, ZFS, and GlusterFS. If you're managing XFS filesystems on cached devices, our [XFS administration guide](../2026-05-24-self-hosted-xfs-filesystem-administration-xfs-admin-tools-benchmarking-tuning-guide/) covers optimization and maintenance.

## FAQ

### Can dm-writecache improve read performance?

No. dm-writecache is a write-only cache. It accelerates write operations by landing them on the fast SSD first, but read operations always go directly to the backing HDD. If you need read acceleration, use bcache instead, which caches both reads and writes.

### What happens if the SSD fails in a write-back configuration?

In write-back mode (dm-writecache, bcache writeback), unflushed data in the cache is lost if the SSD fails. For critical data, use writethrough mode (bcache only) which writes to both cache and backing device simultaneously. dm-writecache has no writethrough mode — if data safety is paramount, consider bcache or application-level replication.

### Can I use bcache with NVMe drives?

Yes. bcache works with any block device, including NVMe. Use an NVMe drive as the cache device and SATA HDDs (or slower NVMe) as backing devices. The kernel automatically detects the device type and configures appropriate I/O scheduler parameters.

### How large should the cache device be?

A general rule of thumb: the cache should be 10-25% of the backing device size for mixed workloads. For write-heavy workloads, 5-10% is sufficient since dm-writecache only caches writes. For read-heavy workloads with bcache, 20-30% improves hit rates. Monitor the cache hit ratio and adjust accordingly.

### Is FlashCache still viable for new deployments?

FlashCache is considered legacy — its last significant update was in 2021. For new deployments, prefer dm-writecache (for write acceleration) or bcache (for read/write caching), both of which are actively maintained in the Linux kernel mainline. Existing FlashCache deployments should plan migration to bcache or dm-writecache.

### How do I monitor cache hit rates?

For bcache: `cat /sys/block/bcache0/bcache/stats_total/*` shows hits, misses, and bypasses. For dm-writecache: `dmsetup status mycache` shows total blocks, blocks written, and write counts. For FlashCache: `flashcache_stat /dev/mapper/cached_ssd` provides detailed hit/miss statistics.

### Can I resize a bcache cache device online?

Yes. bcache supports online cache device replacement. To resize, register a new larger SSD as a cache device, attach it to the backing device, and bcache will migrate cached data automatically. The old cache device can then be removed. This process is transparent to mounted filesystems.

### Does block caching work with LVM?

Yes. You can place bcache or dm-writecache on top of LVM logical volumes. The typical stack is: physical disks → LVM → bcache/dm-writecache → filesystem. Alternatively, you can use bcache on physical devices and then create LVM volumes on top of the cached bcache device. Both configurations are supported.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Storage Caching: dm-writecache vs bcache vs FlashCache",
  "description": "Compare three Linux block-level storage caching technologies: dm-writecache for write acceleration, bcache for full read/write caching, and FlashCache for enterprise deployments. Includes kernel configuration and Docker deployment guides.",
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
