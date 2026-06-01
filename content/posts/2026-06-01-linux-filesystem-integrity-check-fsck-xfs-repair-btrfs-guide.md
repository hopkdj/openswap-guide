---
title: "Self-Hosted Filesystem Integrity Check Tools: fsck.ext4 vs xfs_repair vs btrfs check"
date: "2026-06-01"
tags: ["linux", "filesystem", "storage", "data-integrity", "ext4", "xfs", "btrfs", "maintenance"]
draft: false
---

## Introduction

Filesystem corruption is one of the scariest moments for any self-hoster. A power outage during a write, a failing SSD with silent bit flips, or a kernel panic mid-transaction can leave your filesystem in an inconsistent state. When that happens, the only thing standing between you and data loss is the filesystem check and repair tool specific to your filesystem.

Linux supports three major local filesystems — ext4 (default on most distributions), XFS (default on RHEL/Fedora), and Btrfs (gaining adoption with Fedora and openSUSE). Each has its own dedicated repair tool with different capabilities, safety guarantees, and recovery strategies. This article compares fsck.ext4 (e2fsck), xfs_repair, and btrfs check with practical recovery scenarios.

| Feature | fsck.ext4 (e2fsck) | xfs_repair | btrfs check |
|---------|-------------------|------------|-------------|
| **File System** | ext2/3/4 | XFS | Btrfs |
| **Checksum Verification** | Metadata only (ext4) | Metadata only | Metadata + Data (with csum) |
| **Online Check** | No (unmount required) | Yes (xfs_scrub) | Yes (btrfs scrub) |
| **Journal Replay** | Automatic | Automatic (mount) | N/A (CoW) |
| **Repair Mode** | Interactive + Auto (-p) | Auto (-L for log) | Manual (--repair) |
| **Inode Repair** | Yes | No (must wipe) | Yes (reflink based) |
| **Snapshot Support** | N/A | N/A | Yes (repair from snapshot) |
| **Dry Run** | Yes (-n) | Yes (-n) | Yes (default, --readonly) |
| **Recovery Time** | ~1 min/TB | ~30 sec/TB | ~3 min/TB (metadata only) |
| **Risk of Data Loss** | Low (journaled) | Medium (log zeroing) | Medium (experimental repair) |

## fsck.ext4: The Time-Tested Standard

`fsck.ext4` (linked from `e2fsck`) is the most mature filesystem checker in the Linux ecosystem, with over 25 years of development. It understands ext2/3/4 on-disk structures intimately and can recover from a wide range of corruption scenarios.

```bash
# Check an ext4 filesystem (read-only, no repair)
fsck.ext4 -n /dev/sdb1

# Automatic repair (non-interactive, safe for minor issues)
fsck.ext4 -p /dev/sdb1

# Force a full check even if the filesystem appears clean
fsck.ext4 -f /dev/sdb1

# Interactive repair with manual decisions
fsck.ext4 -y /dev/sdb1  # answer "yes" to all prompts
```

Key options explained:

```bash
# Verbose output showing each pass
$ fsck.ext4 -fv /dev/sdb1
Pass 1: Checking inodes, blocks, and sizes
Pass 2: Checking directory structure
Pass 3: Checking directory connectivity
Pass 4: Checking reference counts
Pass 5: Checking group summary information
/dev/sdb1: 234591/6553600 files (0.3% non-contiguous), 4523891/26214400 blocks
```

The five-pass structure covers inode integrity, directory structure, path connectivity, reference counts, and block group accounting. A clean run means the filesystem is internally consistent — but it does NOT detect silent data corruption (bit rot) unless you use ext4 with the `metadata_csum` feature enabled:

```bash
# Enable metadata checksums on ext4 (requires kernel 3.6+)
tune2fs -O metadata_csum /dev/sdb1
```

For automated maintenance, add periodic fsck checks to your boot process:

```bash
# Force a filesystem check every 30 mounts or 180 days
tune2fs -c 30 -i 180d /dev/sdb1
```

When fsck finds an inode with corrupted block pointers, it can attempt recovery by moving the orphaned blocks to the `lost+found` directory:

```bash
$ ls -la /mnt/data/lost+found/
-rw-r--r-- 1 root root 40960 Jun  1 10:00 #12345
-rw-r--r-- 1 root root  8192 Jun  1 10:00 #12346
```

## xfs_repair: Enterprise Recovery Speed

XFS was designed for massive parallel I/O and metadata-intensive workloads. Its journaling is more aggressive than ext4's — XFS journals metadata changes only, relying on write-ahead logging for consistency. `xfs_repair` reflects this design: it is fast (often completing in seconds on multi-TB filesystems) but less forgiving than e2fsck. If the journal is corrupt, xfs_repair will zero it, potentially losing recent writes.

```bash
# Read-only check (dry run)
xfs_repair -n /dev/sdb2

# Full repair without modifying the journal
xfs_repair /dev/sdb2

# Repair with journal zeroing (use when mount fails with "log corrupt")
xfs_repair -L /dev/sdb2
```

The `xfs_scrub` tool complements xfs_repair by providing online checks:

```bash
# Check the entire mounted filesystem (read-only, online)
xfs_scrub -n /mnt/data

# Report corruption details
xfs_scrub -v /mnt/data

# Check specific metadata types
xfs_scrub -n -t agheader /mnt/data  # allocation group headers only
xfs_scrub -n -t inode /mnt/data     # inode records only
xfs_scrub -n -t rmap /mnt/data      # reverse mapping btree
```

WARNING: The `-L` flag on xfs_repair is destructive. It zeroes the journal log, meaning any writes that were in-flight when the system crashed are permanently lost. Only use `-L` when xfs_repair refuses to proceed without it and you have confirmed backups.

## btrfs check: CoW Filesystem Recovery

Btrfs uses copy-on-write (CoW) and checksumming at the block level, which changes how corruption detection and repair work. Instead of a single linear process like ext4's five passes, btrfs check verifies the metadata trees (extent tree, chunk tree, root tree) and their cross-references.

```bash
# Read-only check (default mode)
btrfs check /dev/sdb3

# Check with verbose progress
btrfs check --progress /dev/sdb3

# Force check on a mounted filesystem (read-only only)
btrfs check --force /dev/sdb3

# Attempt repair (use with extreme caution)
btrfs check --repair /dev/sdb3
```

The `--repair` flag is explicitly labeled experimental in the man page. Unlike e2fsck and xfs_repair, which have decades of battle testing, btrfs repair is still maturing. The recommended recovery path for btrfs is:

1. Run `btrfs check --readonly` to diagnose the issue
2. If possible, recover data by mounting read-only and copying it elsewhere
3. Use `btrfs check --repair` only as a last resort
4. If you have btrfs snapshots, recover individual files from them

For ongoing integrity monitoring, btrfs includes a built-in scrub feature that runs on a mounted filesystem:

```bash
# Start a scrub on the entire filesystem
btrfs scrub start /mnt/data

# Check scrub status
btrfs scrub status /mnt/data
# Scrub status for /mnt/data
#     scrub started at Tue Jun  1 10:30:00 2026
#     Status: finished
#     Duration: 0:02:15
#     Total to scrub: 125.00GiB
#     Rate: 947.00MiB/s
#     Error summary: no errors found

# Cancel an ongoing scrub
btrfs scrub cancel /mnt/data
```

Scrub reads every data and metadata block, verifies checksums, and automatically repairs correctable errors if you have a redundant profile (RAID1, RAID10, DUP metadata):

```bash
# Create a btrfs filesystem with redundant metadata for self-healing
mkfs.btrfs -m dup /dev/sdb3
```

## Why Self-Host Filesystem Maintenance

Cloud block storage handles filesystem repair transparently — until it does not. When AWS EBS or Google Persistent Disk has an internal error, you have no visibility into what the repair tool did, what data was lost, or whether orphaned inodes ended up in lost+found. Self-hosting gives you full control: you decide whether to run a dry-run check, interactively repair specific inodes, or zero the journal and accept data loss for in-flight writes.

Regular filesystem checks also catch hardware degradation before it becomes data loss. A failing SATA cable manifests as checksum errors in btrfs scrub or unexpected read errors in e2fsck. Catching these during a scheduled maintenance window lets you replace the hardware while your data is intact. Without proactive checking, the first sign of failure is often a mount that fails with "structure needs cleaning" — at which point your service is already down.

For more on Linux storage management, see our guide on [disk health monitoring with smartd and NVMe tools](../self-hosted-disk-health-monitoring-scrutiny-smartd-nvme-cli-guide-2026/). For filesystem snapshot strategies, check our [Btrfs snapshot management guide](../2026-05-26-self-hosted-btrfs-snapshot-management-snapper-timeshift-btrfs-assistant-guide/). If you are dealing with data that may already be lost, our [data recovery tools guide](../2026-05-25-linux-data-recovery-tools-ddrescue-testdisk-photorec-guide/) covers forensic-level recovery.

## FAQ

### How often should I run filesystem checks?

For ext4, the default `tune2fs` settings run a check every 30 mounts or 180 days. For XFS, schedule `xfs_scrub -n` weekly via cron. For btrfs, run `btrfs scrub` monthly. Production servers should automate checks during low-I/O windows — a 2 AM cron job is standard. Filesystems with critical data (databases, financial records) benefit from weekly scrubs. Archive storage with infrequent writes can run quarterly.

### Can I run fsck on a mounted filesystem?

Generally no, and attempting to do so is dangerous. ext4 and XFS require unmounted filesystems for `fsck` and `xfs_repair` respectively. btrfs check can run on a mounted filesystem in read-only mode with `--force`. The online alternatives are `xfs_scrub` (XFS) and `btrfs scrub` (btrfs). For ext4, there is no online equivalent — you must unmount to check. Plan for downtime during ext4 fsck, which can take 10+ minutes on large filesystems.

### Will fsck recover deleted files?

Only in limited cases. If an inode was unlinked but the blocks were not yet overwritten, e2fsck places the recovered data in the `lost+found` directory. The file will have its inode number as the filename (e.g., `#12345`). xfs_repair does not recover deleted files — once unlinked in XFS, the space is freed immediately. btrfs does not have a lost+found concept — use `btrfs restore` to recover files from a mountable snapshot instead. For intentional file recovery, use forensic tools like `testdisk` and `photorec`.

### What should I do if fsck repeatedly finds errors?

If e2fsck finds new errors on every run, you likely have failing hardware. Check SMART data with `smartctl -a /dev/sdb` and look for `Reallocated_Sector_Ct`, `Pending_Sector`, or `UDMA_CRC_Error_Count` values. A non-zero pending sector count strongly suggests drive failure. Replace the drive, clone the data with `ddrescue`, and retire the old device. Running fsck repeatedly on a failing drive accelerates data loss — the repair writes stress already-failing sectors.

### How do I automate filesystem integrity monitoring?

Set up a cron job or systemd timer for each filesystem type:

```bash
# /etc/cron.d/filesystem-checks
# ext4 check (requires unmount, so run during maintenance window)
0 3 * * 0 root umount /mnt/data && fsck.ext4 -p /dev/sdb1 && mount /mnt/data

# XFS online scrub (can run on mounted filesystem)
0 2 * * * root xfs_scrub -n /mnt/data 2>&1 | logger -t xfs_scrub

# btrfs scrub
0 4 1 * * root btrfs scrub start /mnt/data && btrfs scrub status /mnt/data | logger -t btrfs_scrub
```

Combine with monitoring: if `xfs_scrub` or `btrfs scrub` exits with a non-zero status, the cron job should trigger an alert via your monitoring stack (Prometheus Alertmanager, Gotify, Ntfy). The check tools return exit codes: 0 for clean, 1 for corrected errors, 4 for uncorrected errors.

---

**💡 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — it is the world's largest prediction market platform, where you can wager on everything from election outcomes to AI regulation timelines. Unlike gambling, this is a genuine information market: the more you know, the higher your win rate. I have made solid returns predicting AI-related events. Sign up with my invite link:** [Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Filesystem Integrity Check Tools: fsck.ext4 vs xfs_repair vs btrfs check",
  "description": "Compare fsck.ext4 (e2fsck), xfs_repair, and btrfs check for self-hosted Linux filesystem integrity verification. Includes recovery procedures, automation scripts, and hardware failure detection tips.",
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
