---
title: "Self-Hosted XFS Filesystem Administration: xfs_admin vs xfs_db vs xfs_scrub"
date: "2026-05-24"
tags: ["linux", "storage", "filesystem", "xfs", "system-administration"]
draft: false
---

XFS is one of the most widely deployed enterprise filesystems on Linux, powering everything from high-performance databases to massive storage arrays. While most administrators use `mkfs.xfs` to create and `mount` to access XFS volumes, the **xfsprogs** suite includes dozens of specialized tools for administration, diagnostics, and repair.

This guide focuses on three essential XFS administration utilities — **xfs_admin**, **xfs_db**, and **xfs_scrub** — comparing their capabilities, showing practical Docker Compose deployment patterns for monitoring stacks, and providing a decision framework for choosing the right tool for each administrative task.

## XFS Filesystem Overview

XFS was developed by Silicon Graphics in 1993 and mainlined into the Linux kernel in 2001. It features:

- **Extent-based allocation** — efficient large file storage with minimal fragmentation
- **B+ tree directories** — fast directory lookups even with millions of entries
- **Delayed allocation** — optimizes write patterns for better performance
- **Online defragmentation** — `xfs_fsr` defragments without unmounting
- **Quota support** — user, group, and project quotas built in
- **Ref links** — copy-on-write reflinks for space-efficient snapshots
- **Metadata checksums** — CRC32c checksums on all metadata since XFS v5

### XFS Administration Tool Categories

| Category | Tools | Purpose |
|----------|-------|---------|
| **Label/UUID management** | xfs_admin, xfs_io | Modify filesystem labels and identifiers |
| **Debug/diagnostics** | xfs_db, xfs_metadump | Inspect filesystem internals, dump metadata |
| **Repair** | xfs_repair | Fix corrupted filesystems (requires unmount) |
| **Maintenance** | xfs_scrub, xfs_fsr | Online health checks and defragmentation |
| **Information** | xfs_info, xfs_growfs | Display and modify filesystem parameters |
| **Quota** | xfs_quota | Manage user/group/project quotas |

## xfs_admin: Filesystem Label and UUID Management

xfs_admin modifies the superblock-level attributes of an XFS filesystem, including its label and UUID. It is the go-to tool for identifying and managing multiple XFS volumes.

### Key Operations

```bash
# Display current filesystem label and UUID
sudo xfs_admin -l /dev/sda1
sudo xfs_admin -u /dev/sda1

# Set a new filesystem label (max 12 characters)
sudo xfs_admin -L "data-store" /dev/sda1

# Set a new UUID (generates random UUID if none specified)
sudo xfs_admin -U generate /dev/sda1

# Set a specific UUID
sudo xfs_admin -U "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" /dev/sda1

# Display all superblock information
sudo xfs_admin -p /dev/sda1

# Enable lazy superblock counters (performance optimization)
sudo xfs_admin -c "convert -l" /dev/sda1
```

### xfs_admin Use Cases

| Scenario | Command | Notes |
|----------|---------|-------|
| **Label a volume for fstab identification** | `xfs_admin -L "backup-vol" /dev/sdb1` | Label appears in `lsblk -f` |
| **Generate new UUID after cloning** | `xfs_admin -U generate /dev/sdb1` | Required after LVM snapshot or dd clone |
| **Verify UUID matches /etc/fstab** | `xfs_admin -u /dev/sda1` | Prevents boot failures |
| **Display superblock counters** | `xfs_admin -p /dev/sda1` | Shows block counts, inode stats |

### Important: xfs_admin Requires Unmounted Filesystem

All xfs_admin operations that modify the superblock **require the filesystem to be unmounted**. Attempting to run xfs_admin on a mounted XFS volume will fail:

```bash
# This will fail on a mounted filesystem
sudo xfs_admin -L "new-label" /dev/sda1
# xfs_admin: /dev/sda1 contains a mounted filesystem

# Correct procedure
sudo umount /mnt/data
sudo xfs_admin -L "new-label" /dev/sda1
sudo mount /dev/sda1 /mnt/data
```

## xfs_db: Filesystem Debugger and Diagnostics

xfs_db is the most powerful diagnostic tool in the xfsprogs suite. It provides an interactive shell for inspecting every aspect of an XFS filesystem, from superblock parameters to individual inode contents.

### Key Features

- **Interactive shell** — navigate filesystem structures interactively
- **Metadata inspection** — examine superblocks, AG headers, inodes, directories
- **Block mapping** — trace file data blocks to physical disk locations
- **Freespace analysis** — view extent free lists and allocation group stats
- **Read-only by default** — safe to run on mounted filesystems

### Common xfs_db Commands

```bash
# Open xfs_db on a device (read-only mode by default)
sudo xfs_db -r /dev/sda1

# Inside xfs_db shell:

# Display superblock information
xfs_db> sb 0
xfs_db> print

# Navigate to a specific inode
xfs_db> inode 131
xfs_db> print

# Examine directory contents
xfs_db> inode 128
xfs_db> p
# Shows directory entries with inode numbers

# Trace file data blocks
xfs_db> inode 256
xfs_db> bmap
# Shows extent mapping: file offset → disk block

# Examine allocation group info
xfs_db> agf 0
xfs_db> print
xfs_db> agi 0
xfs_db> print

# Dump freelist for allocation group
xfs_db> f 0
xfs_db> freetb
xfs_db> quit
```

### xfs_db Non-Interactive Diagnostics

```bash
# Script-friendly: run commands without interactive shell
sudo xfs_db -r -c "sb 0" -c "print" /dev/sda1

# Extract filesystem UUID for automation
sudo xfs_db -r -c "sb 0" -c "print uuid" /dev/sda1   | grep uuid | awk '{print $3}'

# Check inode allocation statistics
sudo xfs_db -r -c "agi 0" -c "print" /dev/sda1   | grep -E "count|freecount|level"

# Export metadata for offline analysis
sudo xfs_metadump -o /dev/sda1 /tmp/sda1-metadump.img
# Then analyze the dump (safe to share — no file contents)
sudo xfs_db /tmp/sda1-metadump.img
```

### xfs_db Diagnostics Workflow

```bash
#!/bin/bash
# xfs_health_check.sh — quick XFS diagnostics script
DEVICE="/dev/sda1"
MOUNTPOINT="/mnt/data"

echo "=== XFS Filesystem Health Report ==="
echo "Device: $DEVICE"
echo "Mount: $MOUNTPOINT"
echo ""

# Superblock info
echo "--- Superblock ---"
sudo xfs_db -r -c "sb 0" -c "print" "$DEVICE" | grep -E "uuid|blocksize|dblocks|inodata"

# Allocation group summary
echo "--- Allocation Groups ---"
sudo xfs_db -r -c "sb 0" -c "print agcount" "$DEVICE"

# Inode usage
echo "--- Inode Usage ---"
sudo xfs_info "$MOUNTPOINT" | grep -o "imaxpct=[0-9]*"

# Filesystem geometry
echo "--- Geometry ---"
sudo xfs_info "$MOUNTPOINT"
```

## xfs_scrub: Online Filesystem Health Checking

xfs_scrub (part of the `xfsprogs` package since version 4.15) provides online filesystem health checking and repair. Unlike `xfs_repair`, which requires unmounting the filesystem, xfs_scrub runs while the filesystem is mounted and actively serving I/O.

### Two Components

xfs_scrub consists of two kernel-level operations:

1. **xfs_scrub** — scans filesystem metadata for inconsistencies
2. **xfs_repair** (online mode) — attempts to fix detected issues without unmounting

### What xfs_scrub Checks

| Check Category | What It Verifies |
|---------------|------------------|
| **Superblock** | Consistency of primary and backup superblocks |
| **Allocation groups** | AG headers, free space lists, inode allocation trees |
| **Inode records** | Inode allocation bitmaps, chunk records |
| **Directory structure** | Parent pointer consistency, name hash validity |
| **Extended attributes** | xattr tree integrity |
| **Ref link records** | Copy-on-write reference count accuracy |
| **Quota information** | Quota tree consistency |
| **Free space** | Freespace B-tree validity |

### Installing and Running xfs_scrub

```bash
# Install xfsprogs (includes xfs_scrub)
sudo apt install xfsprogs -y

# Run a read-only scrub (check only, no repair)
sudo xfs_scrub -n /mnt/data

# Run scrub with automatic repair
sudo xfs_scrub /mnt/data

# Scrub a specific filesystem object
sudo xfs_scrub -t 30 /mnt/data    # 30-second timeout per check

# Scrub individual AG (allocation group)
sudo xfs_scrub -t 5 /mnt/data ag 0

# Check kernel support for online scrub
cat /sys/fs/xfs/debug/error_level
ls -la /sys/fs/xfs/
```

### xfs_scrub Docker Compose for Scheduled Scrubbing

```yaml
version: "3.8"
services:
  xfs-scrub:
    image: ubuntu:22.04
    container_name: xfs-scrub
    privileged: true
    volumes:
      - /dev:/dev
      - /mnt/data:/mnt/data
      - /var/log/xfs-scrub:/var/log
    entrypoint: ["bash", "-c"]
    command:
      - |
        apt update && apt install -y xfsprogs cron
        echo "0 2 * * 0 xfs_scrub -n /mnt/data >> /var/log/xfs-scrub.log 2>&1" > /etc/cron.d/xfs-scrub
        crontab /etc/cron.d/xfs-scrub
        cron -f
    restart: always
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"

  log-rotate:
    image: alpine:latest
    container_name: xfs-log-rotate
    volumes:
      - /var/log/xfs-scrub:/var/log
    command: >
      sh -c "
        while true; do
          find /var/log -name '*.log' -size +50M -exec mv {} {}.old \;
          sleep 3600
        done
      "
    restart: always
```

### xfs_scrub Output Interpretation

```bash
# Successful scrub (no issues found)
$ sudo xfs_scrub -n /mnt/data
Phase 1: Checking superblock... OK
Phase 2: Checking AG headers... OK
Phase 3: Checking inode records... OK
Phase 4: Checking directory structure... OK
Phase 5: Checking extended attributes... OK
Phase 6: Checking ref link records... OK
Phase 7: Checking free space... OK
All checks passed.

# Scrub with detected issues
$ sudo xfs_scrub -n /mnt/data
Phase 4: Checking directory structure...
  WARNING: directory entry for "orphan_file" at inode 4521
  has invalid parent pointer. Run xfs_scrub without -n to repair.
1 error(s) detected.
```

### When to Use xfs_scrub vs xfs_repair

| Scenario | Tool | Filesystem State |
|----------|------|-----------------|
| **Routine health check** | xfs_scrub -n | Mounted, online |
| **Minor metadata issue** | xfs_scrub (with repair) | Mounted, online |
| **Severe corruption** | xfs_repair | Unmounted, offline |
| **After power failure** | xfs_repair first | Unmounted |
| **Scheduled maintenance** | xfs_scrub -n via cron | Mounted, online |
| **Pre-backup verification** | xfs_scrub -n | Mounted, online |

## Comparison: xfs_admin vs xfs_db vs xfs_scrub

| Feature | xfs_admin | xfs_db | xfs_scrub |
|---------|-----------|--------|-----------|
| **Primary purpose** | Label/UUID management | Diagnostics/debugging | Online health checking |
| **Requires unmount** | Yes (for writes) | No (read-only) | No |
| **Can repair** | No (superblock only) | No (read-only) | Yes (online repair) |
| **Interactive mode** | No | Yes | No |
| **Automation-friendly** | Yes (single commands) | Yes (-c flags) | Yes (cron scheduling) |
| **Safety on production** | High (limited ops) | Highest (read-only) | High (online, non-destructive) |
| **Metadata inspection** | Superblock only | All structures | All structures (automated) |
| **Skill level** | Beginner | Advanced | Intermediate |

## XFS Filesystem Best Practices

### Initial Formatting

```bash
# Create XFS with optimized parameters
sudo mkfs.xfs -f   -L "data-vol"   -m crc=1,finobt=1,rmapbt=1,reflink=1   -b size=4096   -i size=512   -d agcount=16   /dev/sda1

# Mount with performance options
sudo mount -t xfs   -o noatime,nodiratime,logbufs=8,logbsize=256k   /dev/sda1 /mnt/data
```

### fstab Entry

```
/dev/sda1  /mnt/data  xfs  noatime,nodiratime,logbufs=8,logbsize=256k  0  2
# Or use label:
LABEL=data-vol  /mnt/data  xfs  noatime,nodiratime  0  2
```

### Periodic Maintenance Schedule

```bash
# /etc/cron.d/xfs-maintenance
# Weekly online scrub (read-only check)
0 3 * * 0 root xfs_scrub -n /mnt/data >> /var/log/xfs-scrub.log 2>&1

# Monthly defragmentation (only if fragmentation > 10%)
0 4 1 * * root xfs_db -r -c "freesp -s" /dev/sda1 | tail -1 | awk '{if ($4 > 10) system("xfs_fsr /mnt/data")}'
```

## Why Self-Host XFS Administration Tools?

Managing XFS filesystems locally provides several critical advantages for self-hosted infrastructure:

1. **Data integrity assurance** — Regular xfs_scrub checks catch metadata inconsistencies before they escalate into data loss. In production environments, undetected filesystem corruption can silently corrupt database files, container images, or backup archives.

2. **Performance optimization** — XFS offers dozens of mount-time and format-time tunables. Understanding these through xfs_db inspection and xfs_info geometry reports enables administrators to optimize for specific workloads: large sequential writes for media servers, random reads for databases, or mixed I/O for container hosts.

3. **Capacity planning** — xfs_db's freelist and allocation group analysis reveals fragmentation patterns and space utilization trends. This data informs decisions about volume expansion, RAID reconfiguration, or workload migration before storage capacity becomes a bottleneck.

4. **Disaster recovery readiness** — Familiarity with xfs_admin, xfs_db, and xfs_repair is essential for recovering from power failures, disk failures, or LVM snapshot merge issues. When a production filesystem fails to mount, these tools are the difference between a quick recovery and a complete rebuild.

5. **Audit and compliance** — Scheduled xfs_scrub runs with logged output provide documented evidence of filesystem health monitoring, supporting compliance requirements for data integrity in regulated environments.

For storage filesystem comparisons, see our [Linux software RAID guide](../2026-05-23-linux-software-raid-mdadm-vs-btrfs-vs-zfs-guide/).
For data integrity verification, check our [dm-verity and fs-verity guide](../2026-05-24-self-hosted-linux-data-integrity-verification-dm-verity-fs-verity-dm-integrity-guide/).
For filesystem event monitoring, our [filesystem mount management article](../2026-05-24-self-hosted-linux-filesystem-mount-management-systemd-mount-vs-autofs-vs-systemd-automount-guide/) covers automated mounting strategies.


<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted XFS Filesystem Administration: xfs_admin vs xfs_db vs xfs_scrub",
  "description": "Compare xfs_admin, xfs_db, and xfs_scrub for self-hosted XFS filesystem management — label management, diagnostics, and online health checking.",
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

### What is the difference between xfs_scrub and xfs_repair?

xfs_scrub runs **online** (filesystem mounted) and performs read-only health checks or lightweight repairs of metadata issues. xfs_repair runs **offline** (filesystem unmounted) and performs deep structural repairs, including rebuilding corrupted B-trees and recovering lost inodes. Always try xfs_scrub first; only use xfs_repair if scrub detects severe corruption or the filesystem won't mount.

### Can I run xfs_db on a mounted XFS filesystem?

Yes, xfs_db with the `-r` (read-only) flag is safe to run on mounted filesystems. It reads metadata structures without modifying anything. However, avoid using write-mode commands in xfs_db on mounted filesystems, as these can cause inconsistency with the live filesystem state.

### How do I check if my XFS filesystem supports online scrubbing?

Online scrub requires kernel 4.18+ and XFS filesystem format v5 (CRC enabled). Check with:

```bash
# Check kernel support
ls /sys/fs/xfs/*/stats/scrub 2>/dev/null && echo "Scrub supported" || echo "Not supported"

# Check filesystem format version
sudo xfs_info /mnt/data | grep -o "crc=[01]"
# crc=1 means v5 format (scrub supported)
```

### What does xfs_admin -U generate do?

`xfs_admin -U generate` creates a new random UUID for the filesystem superblock. This is essential after cloning a disk or LVM volume, because two mounted filesystems with identical UUIDs will cause mount conflicts. The UUID is used by `/etc/fstab` (via UUID= references), blkid, and udev to identify the filesystem.

### How often should I run xfs_scrub?

For production systems, run `xfs_scrub -n` (read-only check) **weekly** via cron. Run `xfs_scrub` (with repair) **monthly** or when the read-only check detects issues. For homelab environments, a monthly read-only scrub is sufficient. Always review the scrub log after each run.

### Can xfs_scrub fix all types of XFS corruption?

No. xfs_scrub can repair minor metadata inconsistencies (orphan inodes, stale directory entries, free space accounting errors) while the filesystem is mounted. It **cannot** fix:
- Corrupted superblocks (requires xfs_repair)
- Damaged allocation group headers (requires xfs_repair)
- Lost inode data (requires xfs_repair -L, which may lose data)
- Physical disk bad sectors (requires disk replacement + restore from backup)

### How do I change an XFS filesystem label without unmounting?

You **cannot** change an XFS filesystem label while it's mounted. xfs_admin requires exclusive access to the superblock. The procedure is:

```bash
sudo umount /mnt/data
sudo xfs_admin -L "new-label" /dev/sda1
sudo mount /dev/sda1 /mnt/data
```

If you cannot unmount, use xfs_db in read-only mode to inspect the current label, and schedule the label change for a maintenance window.
