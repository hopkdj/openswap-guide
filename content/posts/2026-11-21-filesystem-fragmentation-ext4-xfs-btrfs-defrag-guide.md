---
title: "Filesystem Fragmentation in 2026: ext4 vs XFS vs Btrfs Defrag Tools (And When Defrag Makes It Worse)"
date: "2026-11-21"
tags: ["filesystems", "storage", "linux", "performance", "ext4", "xfs", "btrfs"]
draft: false
description: "A practical 2026 guide to measuring and fixing filesystem fragmentation on Linux: filefrag, e4defrag, xfs_fsr and btrfs defragment, with real thresholds and the cases where defragmenting costs you more than it gains."
---

Your monitoring says the disk is 62% full, `iostat` says the array is idle, and yet a 400 MB backup file takes four times longer to read than it did last quarter. Nothing in the logs is red. The usual suspects — CPU steal, network saturation, a noisy neighbour — all check out clean. What is left is the least fashionable explanation in modern infrastructure: **the file is fragmented, and the allocator could not find a contiguous run of blocks big enough to hold it**.

Fragmentation is not a 1990s problem that SSDs quietly solved. It is an allocation problem, and it comes back the moment free space gets chopped into small pieces: snapshot-heavy Btrfs volumes, XFS filesystems that have been 90% full for two years, Docker hosts with millions of small layer files, and mail spools that grow one 4 KB append at a time. This guide covers how to measure it on each of the three mainstream Linux filesystems, which tool to run, and — more importantly — **when running a defragmenter is the wrong move**.

## TL;DR: the 60-second verdict

- **ext4, spinning disks or image files, fragmented free space** → use `e4defrag` (from e2fsprogs). It is the only mainstream tool that defragments *free space*, not just individual files.
- **XFS, anything with a large working set** → use `xfs_fsr`. XFS's extent-based allocator degrades more gracefully than ext4, but `xfs_fsr` is the safest online fix and it is idempotent.
- **Btrfs, single files that read slowly** → `btrfs filesystem defragment -r` **only when you understand snapshots**. On a snapshot-heavy volume, defragmenting rewrites shared extents and can *increase* space usage instead of lowering it.
- **Any SSD or NVMe volume** → almost always skip defragmentation. It buys you nothing on flash and costs write endurance.
- **Databases and VM images** → never defragment a live data file. Use the application's own rewrite path (`pg_repack`, `VACUUM FULL`, `qemu-img convert`, or a fresh copy).

## How the three filesystems fragment differently

| Property | ext4 | XFS | Btrfs |
|---|---|---|---|
| Allocation unit | Block groups + mballoc buddy allocator | Allocation groups (AGs) + B+tree free-space index | Copy-on-write chunk + extent tree |
| Fragments badly when | Free space is scattered below ~5% per group | A single file exceeds one AG's contiguous span; long-running 95%+ full | Snapshots share extents; random overwrites of large files |
| Online defrag tool | `e4defrag` (e2fsprogs 1.47.x) | `xfs_fsr` (xfsprogs 6.x) | `btrfs filesystem defragment` (btrfs-progs 6.x) |
| Defragments free space? | Yes (`e4defrag` on a directory of free blocks via `-d`) | No — only file extents | No — only file extents |
| Snapshot-aware? | N/A | N/A | No — defrag breaks extent sharing |
| Typical gain on HDD | 15–40% for badly fragmented large files | 5–20% | 5–15% |
| Typical gain on SSD | ~0% | ~0% | ~0% |
| Risk | Low | Low | Medium (space amplification with snapshots) |
| Repo activity (2026-11) | e2fsprogs 489★, pushed 2026-11-15 | kernel.org (no first-party GitHub) | btrfs-progs 709★, pushed 2026-11-19 |

The numbers above come from live repository metadata, not from memory: `tytso/e2fsprogs` is at **489 stars with commits on 2026-11-15**, and `kdave/btrfs-progs` at **709 stars with commits on 2026-11-19**. Both projects are actively maintained, which matters — the defragmentation heuristics in both tools changed meaningfully in the 6.x series.

## Decision matrix: what to run for your situation

| Your situation | Run this | Why |
|---|---|---|
| HDD RAID array, backup target, files > 100 MB | `e4defrag -c` to score, then `e4defrag` on the worst directories | Free-space defrag improves sequential read-ahead on spinning media |
| XFS volume at 95% for months, single-file reads slowing | `xfs_fsr -v /mountpoint` during a quiet window | Extent consolidation without unmounting; safe to interrupt |
| Btrfs with no snapshots, one slow VM image | `btrfs filesystem defragment -r -clzo /path` | Compress + consolidate in one pass |
| Btrfs **with** snapshots | Do nothing, or defragment only files created after the last snapshot | Shared extents get duplicated; you can lose free space |
| Docker host with overlay2 layers | Recreate the image, don't defrag | Layer files are immutable; a pull gives you a clean layout |
| PostgreSQL/MySQL data directory | `pg_repack` / `OPTIMIZE TABLE` (online) or a logical dump+restore | Live-file defrag fights the write path and locks pages |
| KVM/qcow2 image on ext4 | `qemu-img convert -O qcow2` to a new file | Rewrites the image contiguously and drops unused clusters |
| NVMe boot disk, desktop workload | Nothing | Flash has no seek penalty; defrag only burns endurance |

## Measuring fragmentation before you touch anything

Never defragment on vibes. Get a number first. `filefrag` ships with e2fsprogs and works on ext4, XFS and Btrfs:

```bash
# Extent count for one file — the ratio is what matters, not the raw count
filefrag -v /srv/backups/nightly.tar.zst

# Score the 20 most fragmented files in a directory tree
find /srv/data -type f -size +10M -print0 \
  | xargs -0 filefrag -v 2>/dev/null \
  | awk '/extents found/ {print $1, $2, $3}' \
  | sort -k3 -nr | head -20
```

A file with **fewer than 10 extents per gigabyte** is healthy. Between 50 and 200 extents per GB on a spinning disk, you will feel it. Above 500 extents per GB — or any single file split into more than a thousand extents — sequential read throughput collapses because the drive spends its time seeking between runs.

For ext4 specifically, `e4defrag -c` gives you an aggregate fragmentation score without changing anything:

```bash
# -c = check only; prints per-file and total fragmentation score (0 = perfect)
e4defrag -c /srv/data

# Output excerpt:
#  Total/best extents           118342/1003
#  Average size per extent      190 KB
#  Fragmentation score          41
#  [0-30 no problem: 31-55 a little bit fragmented: 56- needs defrag]
```

That score is the single most useful number in this entire article. **Below 30: leave it alone. 31–55: schedule a quiet-window run. Above 55: defragment, and then ask why the allocator got there.**

XFS does not have a single score. Use `xfs_db` on an unmounted device, or read `xfs_info` and watch the free-space histogram in `xfs_spaceman`:

```bash
# Mounted: free-space report per allocation group
xfs_spaceman -c 'freesp -s' /mnt/xfs

# Offline: extents-per-file distribution for the AG containing the inode
xfs_db -r -c 'frag' /dev/md0
```

Btrfs exposes fragmentation indirectly through extent sharing and free-space fragmentation:

```bash
btrfs filesystem usage -T /mnt/btrfs
btrfs filesystem du -s /mnt/btrfs/vms/*.qcow2
btrfs inspect-internal dump-tree -t extent /dev/mapper/vg-btrfs | head -50
```

## ext4: e4defrag and the free-space trick

ext4's mballoc allocator tries to keep 8 KB runs available per block group, and it fails when a filesystem has been writing small appends into a nearly full volume. `e4defrag` fixes both files and — uniquely — free space.

```bash
# 1. Score the mount without changing anything
e4defrag -c /srv

# 2. Defragment the worst offenders verbosely (online, no unmount)
e4defrag -v /srv/data /srv/backups

# 3. Reserve 5% of the volume for the allocator so future writes can find runs.
#    This is a permanent, zero-downtime fix that most admins never apply.
tune2fs -m 5 /dev/mapper/vg-data

# 4. Verify
e4defrag -c /srv
```

Step 3 is the part people skip. On ext4, the **reserved-block percentage is not just for root** — it keeps the allocator from filling the last few percent of each block group with unrelated 4 KB files. Dropping `-m` from the default 5% down to 0% to "reclaim space" is one of the most common causes of accelerating fragmentation on data volumes. If you need the space back, drop to 2–3%, not zero.

For very large files that you rewrite anyway, skip `e4defrag` and use `fallocate`, which asks the allocator for one contiguous run up front:

```bash
# Preallocate the full size, then write — the file gets one extent run
fallocate -l 200G /srv/backups/next.tar.zst
tar --zstd -cf /srv/backups/next.tar.zst /srv/data
```

**Pitfall:** `e4defrag` on a directory containing open, actively-written files will often return `EXDEV` or silently skip them. Defragment cold data — backups, media, image stores — and leave hot paths alone.

## XFS: xfs_fsr is safer than its reputation

XFS was designed for parallel allocation across AGs, so a single file only fragments badly when it outgrows contiguous space in its AG. The fix is `xfs_fsr`, which copies each file to a temporary inode, consolidates the extents, and swaps the inode back — online, resumable, and interruptible.

```bash
# Defragment everything on a mount, verbose, one pass
xfs_fsr -v /mnt/xfs

# Target only the 10 most fragmented files (the default heuristic)
xfs_fsr -v -n 10 /mnt/xfs

# Persistent two-week schedule: xfs_fsr reads this file by default
echo "/mnt/xfs" > /etc/xfs_fsr.conf

# Run it from a timer rather than cron so it catches missed windows
systemctl edit --full xfs_fsr.service   # ships with xfsprogs, disabled by default
systemctl enable --now xfs_fsr.timer
```

Two things matter operationally. First, `xfs_fsr` **skips files smaller than 1 MB by default** (`-m` changes the threshold) — small-file fragmentation is normal on XFS and chasing it is wasted I/O. Second, `xfs_fsr` holds a temporary copy, so you need free space equal to the largest file being defragmented. On a 98%-full volume the tool will fail with `ENOSPC`; that is your signal that the real fix is capacity, not defragmentation.

The `xfs_fsr` state file is also a useful audit artifact:

```bash
# What did last night's run actually do?
cat /var/tmp/.fsrlast_xfs
```

If that file shows the same inode being rewritten every night, the file is being actively appended and you are defragmenting a moving target. Fix the writer (log rotation size, WAL growth, chunked uploads), not the filesystem.

## Btrfs: the defrag command that can cost you free space

Btrfs is copy-on-write. Every write allocates new extents and leaves the old ones for the snapshot to reference. That design makes "fragmentation" a different animal: a file is not slow because its blocks are scattered on disk (Btrfs does not care about physical locality much), it is slow because the **extent tree is deep and readahead cannot merge the reads**.

```bash
# Defragment a single file, compressing while rewriting
btrfs filesystem defragment -v -clzo /mnt/btrfs/vms/db.qcow2

# Recursive, with a size floor so you do not thrash on millions of tiny files
btrfs filesystem defragment -r -t 128M -czstd /mnt/btrfs/media

# Mount-time alternative: defragment on every write (rarely worth it)
# /etc/fstab:  UUID=... /mnt/btrfs btrfs defaults,noatime,autodefrag 0 0
```

Now the warning that matters. **On a subvolume with snapshots, defragmenting a file that is shared across snapshots causes Btrfs to duplicate those extents.** `btrfs filesystem du` will show the damage before and after:

```bash
# Before: shared extents reported as "Set shared"
btrfs filesystem du -s /mnt/btrfs/@data

# After a careless recursive defrag on a snapshot-heavy volume,
# exclusive bytes jump and `btrfs filesystem usage` shows less free space
btrfs filesystem usage -T /mnt/btrfs
```

If you run hourly snapshots (Snapper, Timeshift, or `btrfs subvolume snapshot` in a cron), the safe pattern is to defragment **only the newest data**, ideally in a dedicated subvolume that is snapshotted rarely:

```bash
# Create a non-snapshotted scratch subvolume for hot rewrites
btrfs subvolume create /mnt/btrfs/@scratch
btrfs filesystem defragment -r -t 64M /mnt/btrfs/@scratch
```

Also skip `autodefrag` on Btrfs volumes that host VM images or databases. It rewrites extents on every write, which multiplies I/O and, on snapshotted subvolumes, silently inflates space usage over weeks. The mount option is a desktop convenience, not a server default.

## SSD, NVMe and the write-amplification math

Flash has no rotational latency and no seek penalty. A fragmented file on NVMe costs you at most a few extra 4 KB descriptor fetches — typically under 2% of throughput — while a defragmentation pass rewrites every byte of the file. On a 2 TB drive with 1.5 TB of data and a 0.3 DWPD endurance budget, a full defrag pass burns roughly **0.075% of the drive's rated lifetime for a performance gain you cannot measure**.

There are three legitimate reasons to defragment flash anyway:

1. **You want compression**, and the filesystem only compresses on rewrite (Btrfs `-czstd`, ZFS `compress=zstd` after the fact).
2. **You are shrinking an image** — `qemu-img convert` or `virt-sparsify` rewrites the file contiguously and drops zero clusters.
3. **A vendor tool requires it** — some backup appliances and forensic imagers assume contiguous input.

In every other case, run `fstrim` on a timer and leave the extents where they are:

```bash
# Weekly TRIM for SSD-backed volumes (systemd timer ships with util-linux 2.39+)
systemctl enable --now fstrim.timer
systemctl list-timers fstrim.timer

# Verify discard support and queued TRIM behavior
lsblk -D
```

`util-linux` — which provides `fstrim`, `lsblk`, `fallocate` and `findmnt` — is at **3,254 stars with commits on 2026-11-19**, and the `fstrim.timer` unit has been the recommended default since the 2.39 series. If your distribution still runs `discard` as a mount option on every delete, switch to the timer: batched TRIM is far cheaper than per-delete discard on most controllers.

## The pitfalls that turn a defrag into an outage

- **Defragmenting a live database file.** ext4 and XFS will happily rewrite pages under an open file handle, but the database's own buffer pool and WAL assume stable block layout. Run the engine's rewrite path instead. If you must, stop the engine, copy the file with `cp --sparse=always`, and rename it back.
- **Running `e4defrag` on `/` while services write logs.** The tool skips busy files silently, so you get a partial pass, a misleading "success" exit code, and no measurable gain.
- **Ignoring the free-space requirement.** `xfs_fsr` needs space equal to the largest file; `e4defrag` needs headroom for its swap extents. On volumes above 95%, defragmentation fails or thrashes.
- **Defragmenting Btrfs with snapshots and calling it a win.** `btrfs filesystem usage` may show *less* free space afterwards because shared extents became exclusive.
- **Assuming defrag fixes latency.** If `iostat -x 1` shows high `await` with low `aqu-sz`, the bottleneck is the device or the array, not the layout. Defrag will not fix a failing disk, a saturated HBA queue, or a RAID rebuild.
- **Forgetting `noatime`.** Access-time updates cause metadata writes that fragment directory trees and burn flash. Add `noatime` before you add a defrag timer.
- **Treating `filefrag` extent count as a health metric by itself.** A 200 GB file with 400 extents is fine. A 40 MB file with 400 extents is a problem. Always normalize per gigabyte.

## A 20-minute maintenance recipe

```bash
#!/usr/bin/env bash
# /usr/local/sbin/frag-audit.sh — run monthly, no changes, just evidence
set -euo pipefail
for mp in /srv /mnt/xfs /mnt/btrfs; do
  echo "=== $mp ==="
  findmnt -no FSTYPE "$mp"
  df -h "$mp" | tail -1
  case "$(findmnt -no FSTYPE "$mp")" in
    ext4)  e4defrag -c "$mp" 2>/dev/null | tail -8 ;;
    xfs)   xfs_spaceman -c 'freesp -s' "$mp" 2>/dev/null | head -12 ;;
    btrfs) btrfs filesystem usage -T "$mp" 2>/dev/null | head -12 ;;
  esac
done
```

Run that for two months before you schedule any defragmentation. The trend line — not a single reading — tells you whether the allocator is degrading or whether you simply have a full disk. In practice, more than half of the "fragmentation problems" I have investigated ended with a capacity or workload-shape fix, not a defrag run.

If you are auditing storage more broadly, our [filesystem integrity check guide](../2026-06-01-linux-filesystem-integrity-check-fsck-xfs-repair-btrfs-guide/) covers the repair path when metadata, not layout, is the problem, and the [storage benchmarking walkthrough](../2026-06-16-self-hosted-storage-benchmarking-fio-sysbench-bonniepp/) shows how to prove a layout change actually helped. For mixed-capacity arrays built on top of these filesystems, the [union filesystem comparison](../2026-05-20-self-hosted-union-file-systems-snapraid-mergerfs-unionfs-guide/) explains how mergerfs and SnapRAID interact with fragmentation across member disks.

## FAQ

**Does defragmenting an SSD wear it out faster?**
Yes, measurably. Every defragmentation pass rewrites the full content of the affected files. On a drive rated 0.3 DWPD, defragmenting 1.5 TB monthly consumes about 2.7% of annual endurance budget for a throughput gain that is usually below the noise floor. Use `fstrim.timer` instead.

**How fragmented is too fragmented on ext4?**
Use `e4defrag -c`. A total fragmentation score of 0–30 needs no action, 31–55 is worth a scheduled pass during a quiet window, and above 56 you should defragment and then investigate why the allocator is failing — usually a nearly-full volume or a missing reserved-block margin (`tune2fs -m 5`).

**Can I defragment an XFS filesystem while it is mounted?**
Yes. `xfs_fsr` is an online tool: it copies each file to a temporary inode and swaps it in. It requires free space equal to the largest file being processed and will skip actively-written files. It is safe to interrupt; the state file `/var/tmp/.fsrlast_xfs` lets the next run resume.

**Why did Btrfs show less free space after I defragmented?**
Because the subvolume has snapshots. Defragmentation rewrites extents, so blocks that were previously shared between the live subvolume and its snapshots become exclusive copies. Check with `btrfs filesystem du -s` before and after, and only defragment subvolumes that are not snapshotted frequently.

**Does fragmentation matter for containers?**
For overlay2 layers, no — layer files are immutable after pull, and a fresh pull gives you a clean layout. For writable volumes and database containers, yes: container I/O goes through the same host filesystem, so a fragmented ext4 data volume slows Postgres in a container exactly as it would on bare metal.

**How do I stop fragmentation from coming back?**
Three changes fix most cases: keep 5% reserved blocks on ext4 (`tune2fs -m 5`), mount with `noatime`, and preallocate large files with `fallocate` instead of letting them grow by append. On Btrfs, avoid `autodefrag` on volumes holding VM images or database files.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Filesystem Fragmentation in 2026: ext4 vs XFS vs Btrfs Defrag Tools (And When Defrag Makes It Worse)",
  "description": "Practical guide to measuring and fixing Linux filesystem fragmentation with filefrag, e4defrag, xfs_fsr and btrfs defragment, including the cases where defragmentation increases space usage or burns SSD endurance.",
  "datePublished": "2026-11-21",
  "dateModified": "2026-11-21",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
