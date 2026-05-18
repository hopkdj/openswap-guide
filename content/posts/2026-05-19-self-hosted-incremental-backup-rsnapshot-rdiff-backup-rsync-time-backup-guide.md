---
title: "Self-Hosted Incremental Backup: rsnapshot vs rdiff-backup vs rsync-time-backup (2026)"
date: "2026-05-19"
tags: ["backup", "rsync", "data-protection", "incremental-backup", "file-sync"]
draft: false
---

Incremental backups are the backbone of any reliable data protection strategy. Rather than copying every file on every run, incremental tools transfer only changed data, saving disk space, bandwidth, and time. For system administrators managing Linux servers, three rsync-based tools have emerged as the leading open-source options: **rsnapshot**, **rdiff-backup**, and **rsync-time-backup**.

This guide compares all three across architecture, configuration, recovery workflows, and real-world deployment scenarios so you can choose the right tool for your backup infrastructure.

## How Incremental Backups Work

All three tools are built on [rsync](https://rsync.samba.org/), the ubiquitous file synchronization utility. They share a common foundation: rsync's delta-transfer algorithm, which identifies changed blocks and transfers only those differences. Where they differ is in how they organize snapshots, track changes, and present historical views of your data.

**rsnapshot** uses hard links to create space-efficient rotating snapshots. Each backup appears as a full copy of the filesystem, but unchanged files are hard-linked to the previous snapshot, consuming no additional disk space. Its retention model follows a grandfather-father-son rotation scheme (hourly, daily, weekly, monthly).

**rdiff-backup** stores a current mirror of the source plus reverse diffs for each previous backup. This means the most recent backup is always a complete, browsable copy — identical to the source — while older versions require applying reverse diffs to reconstruct. Its unique "reverse differential" approach makes current backups fast and old backups more storage-efficient.

**rsync-time-backup** is a streamlined wrapper script around rsync that creates timestamped backup directories with the most recent always symlinked as `current`. It combines the simplicity of a shell script with powerful features like automatic rotation, bandwidth limiting, and SSH-based remote backups.

## Feature Comparison

| Feature | rsnapshot | rdiff-backup | rsync-time-backup |
|---------|-----------|--------------|-------------------|
| **Storage method** | Hard-linked snapshots | Mirror + reverse diffs | Timestamped directories |
| **Latest backup browsable** | Yes (each snapshot) | Yes (current mirror) | Yes (`current` symlink) |
| **Retention policy** | Configurable rotation intervals | Automatic expiry by date | Configurable by count |
| **Remote backups** | SSH/rsync over SSH | SSH/rsync over SSH | SSH/rsync over SSH |
| **Backup window control** | Yes (interval-based) | Yes | Yes (bwlimit, ionice) |
| **Windows support** | No (Linux/Unix only) | Yes (native Windows client) | No (Linux/macOS) |
| **Configuration** | `/etc/rsnapshot.conf` | CLI flags + config files | Shell variables in script |
| **Compression** | Via rsync `--compress` | Via rsync `--compress` | Via rsync `--compress` |
| **Pre/post scripts** | `cmd_preexec` / `cmd_postexec` | `--include` / `--exclude` | Custom shell hooks |
| **Backup verification** | Manual `rsync --dry-run` | Built-in `--verify` | Manual `rsync --dry-run` |
| **GitHub stars** | 3,618+ | 1,254+ | 3,590+ |
| **Last updated** | 2026-03 | 2026-05 | 2025-05 |

## Installing and Configuring rsnapshot

rsnapshot is available in all major Linux distribution repositories and uses a single configuration file.

```bash
# Debian/Ubuntu
apt-get install rsnapshot

# RHEL/CentOS/Fedora
dnf install rsnapshot

# Arch Linux
pacman -S rsnapshot
```

Configuration lives in `/etc/rsnapshot.conf`. Here is a production-ready example:

```conf
config_version  1.2
snapshot_root   /backup/snapshots/
cmd_rm          /bin/rm
cmd_rsync       /usr/bin/rsync
cmd_logger      /usr/bin/logger
retain          hourly  6
retain          daily   7
retain          weekly  4
retain          monthly 3
verbose         2
loglevel        3
logfile         /var/log/rsnapshot.log
lockfile        /var/run/rsnapshot.pid

# Backup targets
backup  /etc/       localhost/
backup  /var/www/   localhost/
backup  root@db-server:/var/lib/postgresql/   db-server/
backup  /home/      localhost/
```

Schedule via cron:

```cron
0 */4   * * *   /usr/bin/rsnapshot hourly
30 3    * * *   /usr/bin/rsnapshot daily
0  3    * * 1   /usr/bin/rsnapshot weekly
30 2   1 * *    /usr/bin/rsnapshot monthly
```

## Installing and Configuring rdiff-backup

rdiff-backup offers both a Python package and distribution packages:

```bash
# Debian/Ubuntu
apt-get install rdiff-backup

# Via pip (latest version)
pip install rdiff-backup

# macOS
brew install rdiff-backup
```

Basic backup command:

```bash
# Local backup
rdiff-backup /etc /backup/etc

# Remote backup via SSH
rdiff-backup root@server:/var/www /backup/server-www

# With exclusion patterns
rdiff-backup --exclude '/var/log/**' /var /backup/var
```

The mirror at the destination is always current and directly browsable. To restore from a previous version:

```bash
# List available sessions
rdiff-backup -l /backup/etc

# Restore from 3 days ago
rdiff-backup -r 3D /backup/etc /restore/etc
```

Automate with a cron job and a wrapper script:

```bash
#!/bin/bash
BACKUP_DIR="/backup/production"
SOURCE="root@prod-server:/data"

rdiff-backup --print-statistics "$SOURCE" "$BACKUP_DIR"

# Remove increments older than 30 days
rdiff-backup --force --remove-older-than 30D "$BACKUP_DIR"
```

## Installing and Configuring rsync-time-backup

rsync-time-backup is a single shell script that you download and customize:

```bash
git clone https://github.com/laurent22/rsync-time-backup.git
cd rsync-time-backup
chmod +x rsync_tmbackup.sh
```

Create a configuration by editing the script's variables or passing them via environment:

```bash
#!/bin/bash
# backup-daily.sh
export BACKUP_SRC="/etc /var/www /home"
export BACKUP_DST="/backup"
export SSH_OPT="-p 22 -i /root/.ssh/backup_key"
export RSYNC_OPTS="--one-file-system --exclude='*.tmp' --exclude='/proc/*'"
export LOG_DIR="/var/log/rsync-time-backup"

./rsync_tmbackup.sh "$BACKUP_SRC" "$BACKUP_DST" "$SSH_OPT"
```

Directory structure after several runs:

```
/backup/
├── current -> 2026-05-19-030001/
├── 2026-05-19-030001/
├── 2026-05-18-030001/
├── 2026-05-17-030001/
└── ...
```

Schedule with cron:

```cron
0 3 * * * /opt/rsync-time-backup/rsync_tmbackup.sh /data /backup
```

## Recovery Workflows

Recovery is where the differences between these tools become most apparent.

**rsnapshot**: Every snapshot is a complete directory tree. To restore, simply copy files from the desired snapshot:

```bash
# Restore from yesterday's daily snapshot
cp -a /backup/snapshots/daily.0/etc/fstab /etc/fstab
```

**rdiff-backup**: The current mirror is directly accessible. For older versions, you must specify the restore time:

```bash
# Restore the current version
cp /backup/etc/fstab /etc/fstab

# Restore from 7 days ago
rdiff-backup -r 7D /backup/etc/fstab /etc/fstab
```

**rsync-time-backup**: Similar to rsnapshot — each timestamped directory is a full tree:

```bash
# Restore from the latest backup
cp -a /backup/current/etc/fstab /etc/fstab

# Restore from a specific date
cp -a "/backup/2026-05-15-030001/etc/fstab" /etc/fstab
```

## Choosing the Right Incremental Backup Tool

**Choose rsnapshot if:** You want the simplest configuration with a proven rotation model. Its hard-link approach is elegant, the config file is straightforward, and it integrates cleanly with cron. It is ideal for traditional server backup with hourly/daily/weekly/monthly retention policies.

**Choose rdiff-backup if:** You need Windows support, want the most storage-efficient solution for long retention periods, or require built-in verification. The reverse differential approach means you can keep months of history without the disk space overhead of hard-linked snapshots. The Windows client is a unique advantage for mixed-environment backups.

**Choose rsync-time-backup if:** You prefer a zero-dependency shell script that is easy to understand and customize. The single-file approach means no package conflicts, easy debugging, and full control over every rsync flag. It works particularly well for small-to-medium setups where a full backup management system would be overkill.

## Why Self-Host Your Backup Infrastructure?

Data ownership is the primary reason organizations choose self-hosted backup solutions. When you rely on cloud backup services, you entrust your most sensitive files — configuration files, databases, customer records, and intellectual property — to third-party infrastructure. With rsync-based tools running on your own hardware, you maintain complete control over where your backup data lives, who can access it, and how long it is retained.

Cost savings compound over time. Cloud backup services charge per gigabyte per month. For a server with 500 GB of data and a 30-day retention window, that translates to recurring monthly charges that can exceed the cost of a dedicated backup server within the first year. Self-hosted tools like rsnapshot, rdiff-backup, and rsync-time-backup are entirely free and open-source, with no per-GB fees, no bandwidth charges, and no subscription renewals.

Network performance is another critical factor. Transferring incremental backups over a local network is orders of magnitude faster than uploading to a cloud provider. For large databases or file servers, this difference means the gap between completing backups within a maintenance window versus having them overlap with production hours. Local backups also avoid the variability of internet bandwidth, which can throttle transfer speeds during peak usage.

Compliance requirements often mandate that backup data remain within specific geographic boundaries or organizational control. Self-hosted backup tools naturally satisfy these requirements because the data never leaves your infrastructure. For industries governed by GDPR, HIPAA, or SOC 2, this simplifies compliance auditing significantly.

For backup verification strategies, see our [complete guide on backup integrity testing](../2026-04-19-self-hosted-backup-verification-testing-integrity-guide/). If you need encrypted cloud sync as a secondary backup layer, our [Duplicati vs Duplicacy vs Duplicity comparison](../2026-04-22-duplicati-vs-duplicacy-vs-duplicity-self-hosted-encrypted-backup-2026/) covers the leading options. For container-specific backup needs, our [Docker volume backup guide](../2026-05-11-self-hosted-docker-volume-backup-offen-nautical-loomchild-guide/) provides targeted solutions.

## FAQ

### What is the difference between rsnapshot and rdiff-backup?

rsnapshot creates hard-linked snapshots where each backup appears as a complete copy of the filesystem. rdiff-backup stores a current mirror plus reverse diffs, meaning the latest backup is always directly browsable while older versions require reconstruction. rsnapshot uses more disk space for long retention; rdiff-backup is more space-efficient over time.

### Can I use rsync-time-backup for remote backups over the internet?

Yes. rsync-time-backup supports SSH-based remote backups natively. You can specify custom SSH options including port numbers, identity files, and connection timeouts. For internet transfers, combine it with rsync's `--compress` flag and consider `--bwlimit` to avoid saturating your bandwidth.

### How do I verify that my incremental backups are intact?

rsnapshot users can run `rsync --dry-run` against a snapshot to compare it with the source. rdiff-backup includes a built-in `--verify` flag that checks the integrity of the backup chain. rsync-time-backup requires manual verification using `rsync --dry-run` or a custom verification script. For comprehensive integrity testing, see our backup verification guide linked above.

### Does rdiff-backup support Windows servers?

Yes, rdiff-backup provides a native Windows client. This is a unique advantage over rsnapshot and rsync-time-backup, which are Linux/Unix-only. You can back up Windows file servers to a Linux backup host or vice versa using rdiff-backup's cross-platform support.

### How do I migrate from one backup tool to another?

The safest approach is to run both tools in parallel until the new tool has a complete backup chain, then decommission the old one. For migrating from rsnapshot to rdiff-backup, point rdiff-backup at the rsnapshot snapshot root directory as the source — it will create a full initial mirror and then subsequent incremental runs will be fast.

### What retention policy should I use for production backups?

A common starting point is the 6-7-4-3 rule: 6 hourly, 7 daily, 4 weekly, and 3 monthly snapshots. Adjust based on your recovery point objective (RPO) — how much data you can afford to lose — and recovery time objective (RTO) — how quickly you need to restore. For highly active databases, consider more frequent snapshots. For static file servers, daily backups may suffice.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Incremental Backup: rsnapshot vs rdiff-backup vs rsync-time-backup (2026)",
  "description": "Compare three leading rsync-based incremental backup tools for Linux servers: rsnapshot, rdiff-backup, and rsync-time-backup. Covers installation, configuration, recovery workflows, and retention policies.",
  "datePublished": "2026-05-19",
  "dateModified": "2026-05-19",
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
