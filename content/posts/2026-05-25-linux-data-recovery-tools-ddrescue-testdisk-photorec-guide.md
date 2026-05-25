---
title: "Self-Hosted Linux Data Recovery Tools: ddrescue vs TestDisk vs PhotoRec"
date: "2026-05-25"
tags: ["data-recovery", "linux-system-administration", "disk-tools", "server-maintenance"]
draft: false
---

When a production server experiences disk failure, filesystem corruption, or accidental data deletion, the difference between a minor outage and a catastrophic data loss event comes down to having the right recovery tools pre-installed and ready to use. Three open-source utilities dominate the Linux data recovery landscape: **GNU ddrescue** for block-level disk imaging, **TestDisk** for partition recovery, and **PhotoRec** for file carving. Each serves a distinct purpose in the recovery toolkit, and understanding when to deploy which tool is essential for any self-hosted infrastructure operator.

## Block-Level Recovery with GNU ddrescue

GNU ddrescue is a data recovery tool designed to copy data from failing drives to a destination image file, prioritizing readable sectors first and retrying bad areas intelligently. Unlike the standard `dd` command, ddrescue maintains a mapfile that tracks which blocks have been successfully copied, allowing it to resume interrupted operations and focus recovery efforts on the most damaged regions of a drive.

The key advantage of ddrescue is its non-destructive approach — it never writes to the source drive, only reading from it. This makes it the safest first step when a disk begins showing signs of failure.

### Installing ddrescue

On Debian/Ubuntu systems:

```bash
sudo apt update && sudo apt install -y gddrescue
```

On RHEL/CentOS/Fedora:

```bash
sudo dnf install -y ddrescue
```

### Basic ddrescue Usage for Disk Imaging

```bash
# Clone a failing drive to an image file, creating/resuming from a mapfile
sudo ddrescue -f -n /dev/sda /mnt/backup/sda-image.img /mnt/backup/sddrescue.map

# Retry bad sectors with aggressive reading
sudo ddrescue -d -r3 /dev/sda /mnt/backup/sda-image.img /mnt/backup/sddrescue.map

# View recovery log
sudo ddrescueview /mnt/backup/sddrescue.map
```

The `-n` flag performs a quick first pass, skipping bad sectors to rescue all readable data immediately. The second pass with `-d` (direct disk access) and `-r3` (3 retries per bad sector) then attempts to recover the damaged areas. The mapfile enables this multi-pass strategy without re-reading successfully copied blocks.

## Partition Recovery with TestDisk

TestDisk is a partition recovery tool that can repair partition tables, recover deleted partitions, fix boot sectors, and make non-booting disks bootable again. It operates at the partition level, scanning the raw disk for partition signatures and filesystem metadata to reconstruct lost partition layouts.

TestDisk supports a wide range of filesystems including FAT, NTFS, exFAT, ext2/ext3/ext4, Btrfs, and ReiserFS. It can identify and recover partitions that were accidentally deleted by `fdisk`, corrupted by a power failure, or lost due to a failing partition table.

### Installing TestDisk

```bash
# Debian/Ubuntu
sudo apt install -y testdisk

# RHEL/Fedora
sudo dnf install -y testdisk

# Arch Linux
sudo pacman -S testdisk
```

### Using TestDisk for Partition Recovery

```bash
# Launch TestDisk (requires root for disk access)
sudo testdisk

# Common workflow:
# 1. Select "Create" to start a new log file
# 2. Choose the affected disk
# 3. Select partition table type (usually Intel/PC)
# 4. Select "Analyse" to search for lost partitions
# 5. Select "Quick Search" or "Deeper Search"
# 6. Review found partitions, select "Write" to restore
```

TestDisk operates in an interactive terminal UI, guiding you through each step. The tool can also rebuild MBR boot code, recover deleted files from FAT/exFAT/NTFS partitions, and fix partition table errors that prevent the system from booting.

## File Carving with PhotoRec

PhotoRec is a companion tool to TestDisk, developed by the same author (CGSecurity). While TestDisk works at the partition level, PhotoRec operates at the file level, scanning raw disk sectors for file signatures (headers and footers) to recover individual files even when the filesystem is severely damaged or the partition table is unrecoverable.

PhotoRec supports recovery of over 480 file formats including documents, images, videos, archives, and database files. It does not preserve original filenames or directory structures — recovered files are named sequentially based on their detected format — but it can recover data from drives that no longer have a valid filesystem.

### Installing PhotoRec

PhotoRec is bundled with TestDisk. Once TestDisk is installed, PhotoRec is available as the `photorec` command:

```bash
# Verify installation
photorec -v
```

### Using PhotoRec for File Recovery

```bash
# Launch PhotoRec in interactive mode
sudo photorec

# Command-line mode (non-interactive)
sudo photorec /dev/sda1 /restore /d /mnt/recovery/

# Recover specific file types only
sudo photorec /dev/sda1 /restore /d /mnt/recovery/   /f jpg,png,pdf,doc,docx,xlsx
```

The command-line mode is particularly useful for server environments where you need to script or automate recovery operations. The `/f` flag limits recovery to specified file extensions, which significantly speeds up the scanning process on large drives.

## Comparison Table

| Feature | GNU ddrescue | TestDisk | PhotoRec |
|---|---|---|---|
| **Recovery Level** | Block/sector | Partition table | File carving |
| **Preserves Filenames** | Yes (full image) | Yes | No (sequential names) |
| **Preserves Directory Structure** | Yes | Yes | No |
| **Works on Deleted Partitions** | No | Yes | Yes |
| **Works Without Filesystem** | Yes (raw copy) | No | Yes |
| **Supported Filesystems** | All (raw copy) | FAT/NTFS/ext/Btrfs/ReiserFS | 480+ file formats |
| **Interactive Mode** | No (CLI only) | Yes (TUI) | Yes (TUI) |
| **Scriptable** | Yes | Limited | Yes (CLI mode) |
| **Resume Support** | Yes (mapfile) | No | No |
| **Stars/Community** | GNU project | 2,400+ (GitHub mirror) | Bundled with TestDisk |
| **Last Updated** | 2025 (GNU Savannah) | April 2026 | April 2026 |
| **Best For** | Failing drive imaging | Partition recovery | Individual file recovery |

## Choosing the Right Recovery Tool

The selection depends entirely on the nature of the data loss event:

**Use ddrescue when:** A physical drive is showing read errors, bad sectors, or intermittent failures. The priority is to create a complete sector-level image before the drive fails completely. This is the first step in any recovery workflow — preserve the raw data before attempting filesystem-level operations.

**Use TestDisk when:** A partition has been accidentally deleted, a partition table is corrupted, or a disk no longer boots due to partition metadata damage. TestDisk can scan the raw disk, identify partition boundaries, and write a corrected partition table. This restores the original filesystem with all files and directory structures intact.

**Use PhotoRec when:** The filesystem is too damaged for TestDisk to recover, or you need to recover specific file types from a raw disk image. PhotoRec ignores the filesystem entirely and scans sector-by-sector for known file signatures. The tradeoff is that recovered files lose their original names and folder structure.

## Recommended Recovery Workflow

For any serious data loss event, follow this ordered workflow:

```bash
# Step 1: Image the failing drive with ddrescue (do NOT write to the source!)
sudo ddrescue -f -n /dev/sdX /backup/disk.img /backup/disk.map
sudo ddrescue -d -r3 /dev/sdX /backup/disk.img /backup/disk.map

# Step 2: Attempt partition recovery on the IMAGE (never on the original)
sudo testdisk /backup/disk.img

# Step 3: If partition recovery fails, use PhotoRec on the image
sudo photorec /backup/disk.img /d /recovery/output/
```

This approach ensures the original drive is only read from (never written to) and all recovery operations work on a safe copy.

## Self-Hosting Your Recovery Toolkit

Every self-hosted server should have these recovery tools pre-installed. When a disk begins failing, every minute counts — downloading and installing tools during an active failure wastes precious time when the drive could become completely unreadable at any moment.

### Pre-Install on All Production Servers

```bash
# One-liner to install all three tools on Debian/Ubuntu
sudo apt install -y gddrescue testdisk smartmontools

# Verify all tools are available
ddrescue --version && testdisk -v && photorec -v
```

### Docker-Based Recovery Environment

For environments where you prefer containerized tooling, you can build a recovery container:

```dockerfile
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y     gddrescue testdisk smartmontools     && rm -rf /var/lib/apt/lists/*
ENTRYPOINT ["/bin/bash"]
```

```bash
# Run with privileged access for disk operations
docker run --rm -it --privileged   -v /dev:/dev   -v /mnt/backup:/backup   recovery-tools:latest
```

### Automated Recovery Monitoring

Combine with `smartd` for proactive disk health monitoring to catch failures before they become critical:

```bash
# /etc/smartd.conf - monitor all drives and alert on issues
/dev/sda -a -o on -S on -s (S/../.././02|L/../../6/03) -m admin@example.com
/dev/sdb -a -o on -S on -s (S/../.././02|L/../../6/03) -m admin@example.com
```

For more on proactive disk health monitoring, see our [complete disk health guide](../2026-05-24-self-hosted-disk-health-monitoring-scrutiny-smartd-nvme-cli-guide/).

## Why Self-Host Your Data Recovery Toolkit?

When disk failure strikes a production server, the clock starts ticking immediately. Having open-source data recovery tools pre-installed on every server in your infrastructure is not optional — it is a critical component of any disaster recovery plan. The alternative is scrambling to download packages while a failing drive deteriorates with every passing minute, potentially losing the window for successful recovery entirely.

Self-hosting your recovery toolkit means you control exactly which versions are deployed, you have tested them on your specific hardware configurations, and you can execute recovery procedures without depending on external network connectivity. When a server cannot reach package repositories due to disk failure, having `ddrescue`, `testdisk`, and `photorec` already installed on a rescue USB or in a recovery partition becomes the difference between a successful data recovery and a total loss.

For organizations managing self-hosted storage infrastructure, the recovery tools integrate naturally with existing backup workflows. If you are running [software RAID arrays](../2026-05-23-linux-software-raid-management-mdadm-vs-btrfs-vs-zfs-guide/) with mdadm or managing [Btrfs snapshots](../2026-05-26-self-hosted-btrfs-snapshot-management-snapper-timeshift-btrfs-assistant-guide/), ddrescue can create sector-level images of individual array members for offline analysis without disrupting the running array.

The financial argument is equally compelling. Professional data recovery services charge $500 to $3,000 per incident for basic recovery, and $2,000 to $10,000+ for physically damaged drives. With ddrescue, TestDisk, and PhotoRec all available under free and open-source licenses, the software cost is zero — your investment is in training your team to use them effectively and pre-positioning them on every server.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Data Recovery Tools: ddrescue vs TestDisk vs PhotoRec",
  "description": "Compare GNU ddrescue, TestDisk, and PhotoRec for self-hosted Linux data recovery. Learn when to use block-level imaging, partition recovery, or file carving.",
  "datePublished": "2026-05-25",
  "dateModified": "2026-05-25",
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

### Can ddrescue recover files from a formatted drive?
No. GNU ddrescue operates at the block level, creating a sector-by-sector copy of the source drive. It does not interpret filesystems or individual files. To recover files from a formatted drive, use PhotoRec (which carves files by signature) or TestDisk (which may recover the previous partition table if it has not been overwritten).

### Is TestDisk safe to use on a production server?
TestDisk is read-only during its analysis phase — it scans the disk for partition signatures without modifying anything. The only write operation occurs when you explicitly select "Write" to save a recovered partition table. Always run TestDisk on a ddrescue image rather than the original disk to eliminate any risk of accidental writes.

### How long does PhotoRec take to scan a drive?
PhotoRec scan time depends on drive size, speed, and the number of file signatures being checked. A 1TB SSD typically takes 2-4 hours for a full scan. A 4TB HDD may take 8-16 hours. Using the `/f` flag to limit recovery to specific file types can reduce scan time by 50-80%.

### Can these tools recover data from SSDs with TRIM enabled?
SSD recovery is more challenging than HDD recovery. When TRIM is active, deleted blocks are physically erased, making file carving with PhotoRec impossible for those blocks. ddrescue can still create an image of remaining data, and TestDisk may find partition structures. For best SSD recovery results, disable TRIM immediately upon discovering data loss and image the drive with ddrescue before any further operations.

### What is the difference between ddrescue and dd_rescue?
They are completely different tools by different authors. GNU ddrescue (package: `gddrescue`) is the recommended tool, written by Antonio Diaz Diaz. dd_rescue (package: `ddrescue` on some distros) is an older, unrelated tool. Always use GNU ddrescue — it is faster, more feature-rich, and supports the critical mapfile resume functionality.

### Should I run recovery tools on the live system or boot from a rescue disk?
Always boot from a rescue disk or live USB when possible. Running recovery tools on a live system risks overwriting recoverable data with normal filesystem operations. A rescue environment like SystemRescue or GRML ensures the affected drive is not mounted and no background processes are writing to it.
