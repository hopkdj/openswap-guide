---
title: "Self-Hosted Linux Storage Deduplication: VDO vs dm-dedup vs ZFS Dedup"
date: "2026-06-01"
tags: ["storage", "linux", "deduplication", "vdo", "zfs", "data-optimization"]
draft: false
---

## Introduction

Storage costs add up fast when you are running a home lab or self-hosted infrastructure. Virtual machine images, container layers, and backup snapshots contain massive amounts of duplicate data blocks. A single 20 GB VM image cloned across five development environments eats 100 GB on disk — but 80 GB of that is identical across clones. Storage deduplication solves this by identifying and eliminating redundant data blocks at the block level, often reducing physical storage consumption by 50–80%.

Linux offers three mature approaches to block-level deduplication, each with a different architecture and set of tradeoffs. This article compares Red Hat's Virtual Data Optimizer (VDO), the kernel's device-mapper dedup target (dm-dedup), and ZFS native inline deduplication. By the end, you will know which approach fits your storage stack and workload.

| Feature | VDO (dm-vdo) | dm-dedup | ZFS Native Dedup |
|---------|-------------|----------|------------------|
| **Architecture** | Kernel block layer (dm target) | Device mapper target | Integrated filesystem |
| **Dedup Timing** | Inline + background | Inline | Inline (synchronous) |
| **Compression** | Built-in (LZ4) | None (separate layer) | Built-in (LZ4, GZIP, ZSTD) |
| **Memory Overhead** | ~250 MB/TB logical | Low (kernel slab) | High (~1–5 GB/TB dedup data) |
| **RHEL Support** | Yes (native) | Experimental | Via OpenZFS |
| **Thin Provisioning** | Yes | No | Native |
| **Kernel Version** | 6.9+ (mainline) | 4.13+ (staging) | Via DKMS module |
| **Maturity** | Production (RHEL 7.5+) | Experimental | Production (OpenZFS 0.7+) |
| **Best For** | VM/container hosts | Simple block dedup | All-in-one storage servers |

## VDO: Red Hat's Enterprise Deduplication

VDO (Virtual Data Optimizer) is a kernel device-mapper target that provides inline block deduplication, compression, and thin provisioning in a single layer. Originally developed by Permabit and acquired by Red Hat, VDO shipped in RHEL 7.5 and was upstreamed to the mainline Linux kernel in 6.9.

**How VDO works:** Data blocks are hashed using the UDS (Universal Deduplication Service) index. Duplicate blocks are replaced with references to a single stored copy. LZ4 compression is applied after deduplication. A background thread periodically optimizes the index to reclaim space from overwritten blocks.

Install and configure VDO on a modern Linux system:

```bash
# Install VDO tools (RHEL/Fedora)
dnf install -y vdo kmod-kvdo

# On Debian/Ubuntu (kernel 6.9+)
apt install -y vdo

# Create a VDO volume on /dev/sdb
vdo create --name=vdo_data --device=/dev/sdb --vdoLogicalSize=500G

# Format and mount
mkfs.xfs -K /dev/mapper/vdo_data
mount /dev/mapper/vdo_data /mnt/vdo

# Monitor dedup savings
vdostats --human-readable
```

VDO reports real-time statistics:

```bash
$ vdostats --human-readable
Device                Size      Used      Available   Use%   Space saving%
vdo_data              500.0G    120.0G    380.0G      24%    62%
```

The 62% space saving means VDO turned 320 GB of logical data into 120 GB physical — a 2.6:1 reduction. For VM hosts with many similar OS images, savings of 5:1 to 10:1 are common.

## dm-dedup: Kernel's Built-In Block Dedup

dm-dedup is a device-mapper target in the staging tree that implements inline block deduplication as a kernel module. Unlike VDO, it does not include compression or thin provisioning — it is a pure deduplication layer designed to sit between your storage device and the filesystem.

dm-dedup uses a hash-indexed metadata area to track block fingerprints. When a write arrives, it hashes the block, checks the metadata table, and either writes the block or redirects to an existing copy.

```bash
# Load the dm-dedup module
modprobe dm-dedup

# Create a dm-dedup device (metadata on /dev/sdc, data on /dev/sdb)
dmsetup create dedup_dev --table "0 209715200 dedup /dev/sdc 0 /dev/sdb 0 4096 md5 32 1"

# Format and use
mkfs.ext4 /dev/mapper/dedup_dev
mount /dev/mapper/dedup_dev /mnt/dedup
```

The dm-dedup table line parameters are:
```
<start_sector> <length> dedup <metadata_dev> <meta_offset> <data_dev> <data_offset> <block_size> <hash_algo> <cache_size_mb> <flush_mode>
```

dm-dedup's simplicity is both its strength and limitation. It adds less overhead than VDO (~100 MB RAM per TB vs 250 MB) but lacks compression and garbage collection. You must run a separate scrub process to identify blocks that are no longer referenced:

```bash
# Manual garbage collection
echo 0 > /sys/module/dm_dedup/parameters/gc_interval
echo 1 > /sys/module/dm_dedup/parameters/trigger_gc
```

## ZFS Native Inline Deduplication

ZFS implements deduplication at the filesystem level with its Deduplication Table (DDT). Every block written to a dataset with `dedup=on` is checksummed, and the SHA-256 hash is stored in the DDT. When ZFS encounters a block with an existing DDT entry, it stores only a reference pointer.

```bash
# Create a ZFS pool with dedup enabled
zpool create -o ashift=12 tank mirror /dev/sdb /dev/sdc

# Enable dedup on a dataset
zfs create tank/vm_images
zfs set dedup=on tank/vm_images
zfs set compression=lz4 tank/vm_images

# Check dedup ratio
zpool list tank
# NAME   SIZE  ALLOC   FREE  CKPOINT  EXPANDSZ   FRAG    CAP  DEDUP
# tank   1.8T   320G  1.5T        -         -     2%    17%  3.20x
```

ZFS dedup has the highest memory cost of the three options. The DDT must reside in ARC (Adaptive Replacement Cache) for acceptable performance. A rough rule of thumb: allocate 1–5 GB of RAM per TB of deduplicated storage for the DDT. If the DDT spills to disk, write performance drops dramatically.

```bash
# Check DDT statistics
zpool status -D tank
# dedup: DDT entries 2453201, size 998MB on disk, 1.2GB in core
```

For storage servers with 64+ GB RAM and a workload dominated by similar data (VM clones, backup archives, container image layers), ZFS dedup provides the best integration and management experience.

## Why Self-Host Your Storage Deduplication?

Running deduplication on your own infrastructure gives you full control over data reduction policies without vendor lock-in. Cloud providers charge for deduplicated storage at post-reduction rates, but you pay for the raw hardware once. A 4 TB NVMe drive with 3:1 dedup yields 12 TB of effective capacity — equivalent to three drives for the cost of one.

For virtual machine hosts, the savings compound rapidly. If you run Proxmox or oVirt with 10 VMs based on the same Ubuntu 24.04 template, VDO or ZFS dedup stores the base OS blocks exactly once. Each VM then only consumes space for its unique data. This is how enterprise storage arrays achieve 10:1 efficiency — and you can achieve the same on a single server.

For backup and archival workflows, deduplication combined with compression turns a small NAS into a long-term backup target. Tools like BorgBackup and Restic already use content-defined chunking at the application layer, but filesystem-level dedup catches redundancies that application tools miss — such as duplicate ISOs, container base images, and database dumps.

To learn more about Linux storage management, see our guide on [LVM thin provisioning and snapshot management](../2026-05-29-self-hosted-linux-lvm-management-lvm2-thin-provisioning-snapshot-tools-guide/). For filesystem-level compression, check out our [Linux compression tools comparison](../2026-06-01-linux-compression-tools-zstd-brotli-lz4-gzip/). If you need a web UI for ZFS management, our [ZFS management dashboard guide](../2026-05-28-self-hosted-zfs-management-web-uis-zfsdash-cockpit-truenas-guide/) covers the best options.

## FAQ

### Does storage deduplication slow down writes?

Yes, but the impact varies. VDO uses an asynchronous UDS index that batches hash lookups, limiting write latency to about 5–15% overhead in most workloads. ZFS inline dedup is synchronous — every write waits for a DDT lookup — so latency increases proportionally with DDT size. dm-dedup is the lightest of the three, adding roughly 3–8% overhead for small block sizes (4 KB). For read-heavy workloads like web servers or file shares, all three have negligible read overhead since reads bypass the dedup path entirely.

### How much RAM does each solution need?

VDO recommends 250 MB of RAM per TB of logical storage, plus a UDS index on fast storage (NVMe recommended). dm-dedup uses kernel slab memory proportional to the number of unique hash entries — typically under 100 MB per TB. ZFS dedup requires 1–5 GB of ARC per TB of deduplicated data for the DDT; insufficient RAM causes the DDT to spill to disk and can reduce write performance by 10–50×.

### Can I use deduplication and compression together?

Yes, and you should. VDO applies LZ4 compression after deduplication automatically. ZFS supports compression independently — setting `compression=lz4` alongside `dedup=on` is standard. dm-dedup does not compress, but you can stack it with dm-crypt or use a compressing filesystem like Btrfs on top. The combination of dedup + compression often yields 4:1 to 8:1 total space savings on mixed workloads.

### Which solution is best for a home lab with 16 GB RAM?

VDO is the most forgiving with limited RAM. Its UDS index can live on an NVMe partition instead of consuming expensive system memory. For a Proxmox home lab, create a VDO volume on a spare SSD, format it with XFS, and store VM disk images there. ZFS dedup with only 16 GB RAM will cause performance problems once the DDT exceeds about 4 GB. dm-dedup works on low-memory systems but requires manual garbage collection and lacks compression — you will need a separate compression layer.

### Can I migrate between dedup solutions?

Not directly. You cannot convert a VDO volume to dm-dedup or ZFS dedup in-place. The standard migration path is: (1) create a new dedup volume with the target solution, (2) use `rsync` or `zfs send/receive` to copy data, (3) verify data integrity, (4) destroy the old volume. For large datasets, plan for migration windows during low-usage periods and use block-level replication tools like `dd` with `pv` for progress monitoring.

### What happens if the dedup metadata gets corrupted?

This is the primary risk with all dedup solutions. If VDO's UDS index or dm-dedup's metadata table becomes corrupt, you lose access to ALL data on that volume — not just the corrupted blocks. Always maintain separate backups of your critical data on non-deduplicated storage. For ZFS, regular `zpool scrub` detects and corrects metadata errors if you have redundancy (mirror or RAID-Z). VDO includes a recovery mode (`vdo start --forceRecovery`) for index corruption scenarios, but it is a last resort.

---

**💡 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — it is the world's largest prediction market platform, where you can wager on everything from election outcomes to AI regulation timelines. Unlike gambling, this is a genuine information market: the more you know, the higher your win rate. I have made solid returns predicting AI-related events. Sign up with my invite link:** [Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Storage Deduplication: VDO vs dm-dedup vs ZFS Dedup",
  "description": "Compare VDO, dm-dedup, and ZFS native deduplication for self-hosted Linux storage. Includes setup commands, performance tradeoffs, and RAM requirements for each approach.",
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
