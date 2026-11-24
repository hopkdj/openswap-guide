---
title: "ZFS Performance Tuning in 2026: ARC, recordsize and ashift Settings That Actually Move the Needle"
date: "2026-11-25"
tags: ["zfs", "storage", "performance", "tuning", "openzfs", "nas"]
draft: false
---

Your pool has 64 GB of ARC, eight NVMe drives, and it still serves small random reads at 300 IOPS. You add RAM, the number barely moves. That is the classic ZFS mis-tuning signature: the bottleneck is not capacity, it is a handful of dataset properties and one irreversible vdev decision made when the pool was created.

This guide covers the four knobs that produce measurable gains — ARC sizing, `recordsize`, `ashift`, and the three cache vdev types — plus the snapshot-retention tooling that keeps the whole thing from degrading over twelve months. Every command below is taken from OpenZFS documentation or the projects' own repositories.

## Quick Verdict (TL;DR)

- **Databases, VM images, and anything with small random I/O:** set `recordsize=16K` (8K for MySQL/PostgreSQL data files) and keep the ARC at 50–75% of RAM. Expect the largest single win here.
- **Media, backup targets, and large sequential files:** set `recordsize=1M` with `compression=zstd`. Sequential throughput jumps, ARC pressure drops.
- **New pools:** always `ashift=12`. It is a one-way door — you cannot fix it later without destroying the pool.
- **Do not buy an L2ARC before you have measured ARC misses.** An L2ARC on a pool with a 99% hit rate is a waste of a drive bay. A SLOG is only useful if you have synchronous writes and a device with power-loss protection.
- **Snapshot retention:** `sanoid` for policy-driven snapshots on a single host, `znapzend` when you also need remote replication with bandwidth shaping.

## The Four Knobs That Matter

| Setting | Default | Recommended (general purpose) | What it changes | Reversible? |
|---|---|---|---|---|
| `zfs_arc_max` | 50% of RAM | 50–75% of RAM on dedicated storage hosts | Read cache ceiling | Yes (module reload) |
| `recordsize` | 128K | 16K (DB/VM), 128K (mixed), 1M (media/backup) | Max block size per file | Yes, new writes only |
| `ashift` | 9 (512B) | 12 (4K) | Minimum allocation unit | **No** |
| `compression` | `lz4` | `lz4` or `zstd` | On-the-fly compression | Yes |
| `atime` | `on` | `off` (or `relatime`) | Metadata write amplification | Yes |
| `xattr` | `on` | `sa` | Extended attribute storage | Partially |

## Decision Matrix: Match the Setting to the Workload

| Your workload | Change this first | Why |
|---|---|---|
| PostgreSQL / MySQL data directory | `recordsize=8K` or `16K` | Matches the database page size, eliminates read-modify-write |
| QEMU/KVM or Proxmox disk images | `recordsize=64K` + `volblocksize=16K` on zvols | Image writes are hole-punched and misaligned at 128K |
| Nextcloud / SMB file shares | `recordsize=1M`, `atime=off`, `xattr=sa` | Large files, no benefit from small blocks, fewer metadata ops |
| Backup target (restic, borg, Veeam) | `recordsize=1M`, `compression=zstd`, `logbias=throughput` | Sequential streams, compressible payload |
| Elasticsearch / Loki chunks | `recordsize=1M`, `logbias=throughput` | Append-only segments |
| NFS export with sync writes | Add a SLOG with power-loss protection | Every `fsync` otherwise waits on the slowest data disk |
| Read-heavy web assets | Verify ARC hit rate before adding L2ARC | Persistent L2ARC only pays off when the working set exceeds RAM |

## OpenZFS — Sizing the ARC Correctly

OpenZFS (`openzfs/zfs`, **12,586 stars**, last push 2026-11-24) defaults `zfs_arc_max` to half of physical RAM on Linux. On a hypervisor that also runs containers, that default is usually wrong in the *other* direction: ARC grows lazily and can starve the page cache, causing unexpected swap pressure under memory pressure.

Set the cap explicitly. The module loads from the initramfs, so the parameter must be present there:

```bash
# /etc/modprobe.d/zfs.conf
# 32 GiB ARC ceiling on a 64 GiB host (bytes, not kilobytes)
options zfs zfs_arc_max=34359738368
options zfs zfs_arc_min=8589934592
```

```bash
sudo update-initramfs -u -k all   # Debian/Ubuntu: required, module loads early
sudo reboot
```

Verify after reboot — a mismatch here means the initramfs was not rebuilt:

```bash
cat /sys/module/zfs/parameters/zfs_arc_max
arc_summary | head -30
arcstat 1 5      # live hit rate, misses, and MRU/MFU split
```

Two numbers decide whether more RAM will help: **ARC hit rate** and **demand data misses**. If hits are above 98% and misses are flat, adding memory buys nothing. If hit rate is 85% and `mfu` (most-frequently-used) is being evicted constantly, you are thrashing and either more RAM or better `recordsize` will help.

A caveat that costs people weekends: on ZFS-on-root systems, `zfs_arc_max` set at runtime via `/sys/module/zfs/parameters/` is silently reset by the next module load. Always use `modprobe.d`.

## recordsize — The Highest-Leverage Dataset Property

`recordsize` is the maximum block size ZFS uses for a file. It is **not** a fixed allocation: files smaller than `recordsize` use smaller blocks. That is exactly why the "128K is fine for everything" advice is wrong for databases — a 16K random overwrite in a 128K record forces ZFS to read the full 128K record, modify it, and write it back with a new checksum. Each 16K write becomes a 128K read plus a 128K write.

```bash
# Database datasets
sudo zfs create -o recordsize=16K -o primarycache=metadata tank/pgdata
sudo zfs set logbias=throughput tank/pgdata

# Large sequential files
sudo zfs create -o recordsize=1M -o compression=zstd tank/media

# Mixed general purpose
sudo zfs create -o recordsize=128K -o atime=off -o xattr=sa tank/files
```

Three rules that prevent surprises:

1. **Existing data keeps its old recordsize.** The property only applies to newly written blocks. A `zfs send | zfs recv` into a new dataset, or a full rewrite, is the only way to convert in place.
2. **Do not shrink `recordsize` for a file that is written once and read whole.** 1M records for a 4 GB ISO produce fewer metadata operations and less ARC overhead than 128K records.
3. **zvols use `volblocksize`, not `recordsize`.** 16K is the modern default for a reason; 8K is still correct for database volumes with 8K pages. Changing it on an existing zvol requires a full rewrite.

## ashift — Get It Right Once

`ashift=12` (4 KiB sectors) is correct for every 512e and 4Kn drive manufactured in the last decade, and for essentially all SSDs. `ashift=9` lets ZFS write 512-byte allocations that the drive must read-modify-write internally, which is measurable as write amplification and inflated latency.

```bash
# Creating a pool correctly, first time
sudo zpool create -o ashift=12 \
  -O compression=lz4 -O atime=off -O xattr=sa \
  tank mirror /dev/disk/by-id/nvme-A /dev/disk/by-id/nvme-B

# Confirm before you put data on it
zpool get ashift tank
```

A pool created with `ashift=9` cannot be repaired. The only remedy is to recreate the pool and restore from backup. If you inherited one, check first — this is the single most common "why is my pool slow" finding on second-hand hardware:

```bash
zpool get ashift,autotrim tank
zpool status -v
```

`autotrim=on` is worth enabling on SSD pools that are not already trimmed by the OS, but it competes with foreground I/O — on write-heavy pools, run a scheduled `zpool trim` during off-hours instead.

## SLOG, L2ARC, and special vDevs — Buy the Right One

These three vdev types solve different problems, and buying the wrong one is a recurring waste of money.

| vdev type | Solves | Requires | Typical gain | Risk if it fails |
|---|---|---|---|---|
| **SLOG** (separate log) | Slow `fsync` on sync-write workloads (NFS, databases, VM images) | Power-loss-protected NVMe | 5–50× lower sync latency | Pool survives; falls back to main log |
| **L2ARC** (read cache) | Working set larger than RAM, read-heavy | Fast NVMe, spare RAM for indexes | Higher hit rate, fewer disk reads | Pool survives; only cache lost |
| **special vDev** | Metadata and small-block latency | Mirrored fast NVMe | Large metadata/directory win | **Pool lost** without redundancy |

```bash
# SLOG: mirrored, power-loss-protected NVMe only
sudo zpool add tank log mirror /dev/disk/by-id/nvme-C-part1 /dev/disk/by-id/nvme-D-part1

# L2ARC: single device is fine, it is only a cache
sudo zpool add tank cache /dev/disk/by-id/nvme-E

# special vdev: ALWAYS mirrored — losing it loses the pool
sudo zpool add tank special mirror /dev/disk/by-id/nvme-F /dev/disk/by-id/nvme-G
sudo zfs set special_small_blocks=64K tank
```

Measure before and after with latency histograms, not with `dd`:

```bash
zpool iostat -v tank 1          # per-vdev throughput and IOPS
zpool iostat -l tank 1          # latency buckets: the number that matters
zdb -S tank                     # dedup ratio estimate — run before enabling dedup
```

If your workload is asynchronous writes (most file servers with `sync=disabled` or `standard` and no `fsync`), a SLOG does literally nothing. That is the most common wasted NVMe drive in homelabs.

## Retention: sanoid vs znapzend

Snapshots are free until they are not: a dataset with 4,000 snapshots makes `zfs list` and `zfs destroy` operations crawl, and `zfs send` resumes become slow. Policy-driven retention is mandatory.

**sanoid** (`jimsalterjrs/sanoid`, **3,915 stars**, last push 2026-06-05) is the standard single-host choice on Linux and FreeBSD. Install from distro packages rather than the repo's install script — the upstream README explicitly warns that the install script is for maintainers.

```bash
sudo apt install sanoid          # Debian/Ubuntu
sudo systemctl enable --now sanoid.timer
```

```ini
# /etc/sanoid/sanoid.conf
[tank/files]
	use_template = production
	recursive = yes
	process_children_only = yes

[production]
	hourly = 36
	daily = 30
	monthly = 3
	yearly = 0
	autosnap = yes
	autoprune = yes
```

```bash
sudo sanoid --cron --verbose     # what the timer runs
sudo sanoid --dry-run            # preview: nothing is destroyed
```

**znapzend** (`oetiker/znapzend`, **675 stars**, last push 2026-07-07) is the better fit when snapshots must also be replicated to a second host and you need to shape the transfer bandwidth with `mbuffer`. Retention is expressed as a plan chain edited per dataset with `znapzendzetup edit`, and transfers are resumable.

Rule of thumb for both: keep enough hourly snapshots to cover your worst "oops" window (36 hours is a sane default), 30 daily, and 3 monthly. Prune aggressively — snapshot metadata is charged to ARC and to every `zfs list`.

## Verification and Ongoing Care

Do not leave a tuned pool untested. Scrub monthly, watch for checksum errors, and alert on capacity above 80% — ZFS write performance degrades as a pool fills because of the spacemap and allocation search cost.

```bash
sudo zpool scrub tank
zpool status -x                      # "all pools are healthy" is the only good output
sudo systemctl enable --now zfs-scrub-monthly@tank.timer   # Debian/Ubuntu
zfs list -o name,used,referenced,compressratio -s used
```

If you are still deciding on the storage layer itself, our [mdadm vs Btrfs vs ZFS comparison](../2026-05-23-linux-software-raid-management-mdadm-vs-btrfs-vs-zfs-guide/) covers the architecture trade-offs, and the [self-hosted NAS guide](../self-hosted-nas-solutions-openmediavault-truenas-rockstor-guide-2026/) covers appliance choices. For replication topology, see [ZFS replication tools compared](../2026-05-18-self-hosted-zfs-replication-tools-zrepl-zrep-zxfer-guide/), and pair your tuning with [disk health monitoring](../self-hosted-disk-health-monitoring-scrutiny-smartd-nvme-cli-guide-2026/) so a failing drive does not silently degrade a vdev.

## Pitfalls That Cost Real Data

1. **`ashift=9` on modern drives.** Unfixable without recreating the pool. Check before you migrate data in, not after.
2. **Shrinking `recordsize` on an existing dataset and expecting a change.** Old blocks keep their size forever; only rewrites adopt the new value.
3. **A SLOG without power-loss protection.** A consumer NVMe with a volatile write cache can lose acknowledged sync writes on power failure — worse than having no SLOG at all.
4. **A single-device special vDev.** Metadata loss equals pool loss. Always mirror it.
5. **Dedup enabled "to save space".** The dedup table consumes roughly 300 bytes per unique block in RAM. Run `zdb -S tank` first; for most workloads the answer is no.
6. **Setting `zfs_arc_max` at runtime only.** It reverts on module reload unless it is in `/etc/modprobe.d/zfs.conf` and the initramfs is rebuilt.
7. **Filling the pool past 90%.** Allocation becomes fragmented and write latency climbs sharply. Keep 20% free.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "ZFS Performance Tuning in 2026: ARC, recordsize and ashift Settings That Actually Move the Needle",
  "description": "Practical OpenZFS tuning guide covering zfs_arc_max sizing, recordsize selection by workload, ashift, SLOG vs L2ARC vs special vDev, and snapshot retention with sanoid and znapzend.",
  "datePublished": "2026-11-25",
  "dateModified": "2026-11-25",
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

**Does a larger ARC always improve ZFS performance?**
No. ARC only helps when the working set exceeds what is cached and the hit rate is below roughly 98%. On a host with a 99% hit rate, extra RAM is wasted; on a host where ARC competes with application memory, an oversized ARC causes swapping and makes everything slower.

**Can I change recordsize on a dataset that already holds data?**
Yes, the property is writable at any time, but it only affects blocks written after the change. Existing records keep their original size until they are rewritten, so plan a full rewrite or a `zfs send | zfs recv` migration if you need uniform block sizes.

**Is ashift=12 always the right choice?**
For all 512e and 4Kn drives and for SSDs, yes. ashift is fixed at vdev creation and cannot be changed, so the only correction is to recreate the pool. Always set it explicitly instead of relying on autodetection.

**Do I need a SLOG for a fast NVMe pool?**
Only if your workload issues synchronous writes — NFS exports, database commits, VM images with write barriers. With asynchronous writes the SLOG is never touched. It also must have power-loss protection, or you risk losing acknowledged writes.

**What is the difference between L2ARC and a special vDev?**
L2ARC is a read cache for data blocks and is disposable: if it dies, the pool keeps running. A special vDev stores metadata and small blocks and is part of the pool topology — if it is not mirrored and it fails, the pool is lost.

**How many snapshots should I keep?**
Enough to cover your realistic recovery window, not more. A common policy is 36 hourly, 30 daily, and 3 monthly. Thousands of snapshots slow down `zfs list`, `zfs destroy`, and send/receive resume operations.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
