---
title: "Self-Hosted Btrfs Snapshot Management: Snapper vs Timeshift vs Btrfs-Assistant"
date: "2026-05-16"
tags: ["btrfs", "snapshot", "backup", "system-restore", "storage", "filesystem"]
draft: false
---

Btrfs is a modern copy-on-write filesystem for Linux that provides advanced features like snapshots, checksums, compression, and RAID. One of Btrfs's most powerful capabilities is near-instantaneous filesystem snapshots, which can serve as restore points for system changes, protection against data corruption, and the foundation for backup strategies.

However, managing Btrfs snapshots manually with the `btrfs subvolume snapshot` command quickly becomes tedious. You need automated scheduling, retention policies, rollback interfaces, and user-friendly controls. This guide compares three leading Btrfs snapshot management tools: **Snapper**, **Timeshift**, and **Btrfs-Assistant**, each with a different approach to snapshot lifecycle management.

## Snapper

Snapper is an open-source snapshot management tool originally developed by SUSE for openSUSE and SUSE Linux Enterprise. It provides automated snapshot creation, timeline-based retention policies, and a CLI for managing and comparing snapshots. Snapper is tightly integrated with package managers, allowing automatic snapshots before and after system updates.

### Key Features

- Automatic pre/post snapshots triggered by package manager transactions (zypper, apt)
- Timeline-based snapshot scheduling (hourly, daily, weekly, monthly)
- Configurable retention policies with cleanup algorithms
- File-level diff and undo between snapshots
- D-Bus interface for integration with desktop environments
- Supports Btrfs and LVM thin provisioning backends
- PAM integration for snapshot access control

### Architecture

Snapper runs as a daemon (`snapperd`) that listens for system events via D-Bus and creates snapshots according to configured timelines. It stores snapshot metadata in an XML-based configuration database under `/etc/snapper/configs/`. Each Btrfs subvolume managed by Snapper gets a dedicated `.snapshots` directory containing read-only snapshot subvolumes.

```bash
# Install snapper (Debian/Ubuntu)
sudo apt install snapper

# Install snapper (RHEL/Fedora)
sudo dnf install snapper

# Create a snapper configuration for root filesystem
sudo snapper -c root create-config /

# List configurations
sudo snapper list-configs

# Create a manual snapshot
sudo snapper -c root create --description "before-upgrade"

# List snapshots
sudo snapper -c root list

# Show diff between snapshots #10 and #11
sudo snapper -c root status 10..11

# Restore specific files from snapshot #10
sudo snapper -c root undochange 10..11 -- file1.txt file2.conf
```

### Snapper Timeline Configuration

```bash
# /etc/snapper/configs/root — Snaper config for root subvolume

# Create hourly snapshots
TIMELINE_CREATE="yes"
TIMELINE_LIMIT_HOURLY="10"

# Create daily snapshots
TIMELINE_LIMIT_DAILY="7"

# Create weekly snapshots
TIMELINE_LIMIT_WEEKLY="4"

# Create monthly snapshots
TIMELINE_LIMIT_MONTHLY="6"

# Cleanup algorithms
CLEANUP_ALGORITHMS="timeline number"

# Number-based retention
NUMBER_LIMIT="50"
NUMBER_LIMIT_IMPORTANT="10"
```

### Snapper + DNF/Apt Integration

```ini
# /etc/dnf/plugins/snapper.conf (Fedora/RHEL)
[main]
enabled = 1

# /etc/apt/apt.conf.d/80snapper (Debian/Ubuntu)
DPkg::Pre-Invoke { "/usr/bin/snapper -c root create --description 'pre-apt' --cleanup number"; };
DPkg::Post-Invoke { "/usr/bin/snapper -c root create --description 'post-apt' --cleanup number"; };
```

## Timeshift

Timeshift is a system restore tool for Linux, originally designed for rsync-based backups but with full Btrfs snapshot support. It provides a user-friendly GTK interface for managing system snapshots, making it accessible to desktop users who need simple point-and-click restore functionality.

### Key Features

- Simple GTK/CLI interface for snapshot management
- Btrfs snapshot mode (instant, copy-on-write) and rsync mode (for non-Btrfs filesystems)
- Scheduled snapshot creation with configurable frequency
- Snapshot filtering (include/exclude directories)
- One-click system restore from snapshot
- Bootable restore from GRUB menu
- Support for external backup destinations
- Exclude home directory by default (system-only snapshots)

### Architecture

Timeshift operates as a standalone application that creates snapshots on demand or on a schedule (via cron). In Btrfs mode, it creates read-only subvolume snapshots of the root filesystem and stores them in a `timeshift-btrfs` directory on the same Btrfs filesystem. The application maintains a JSON catalog of all snapshots with metadata about creation time, size, and description.

```bash
# Install Timeshift (Ubuntu/Debian)
sudo apt install timeshift

# Install Timeshift (Fedora)
sudo dnf install timeshift

# Create a Btrfs snapshot with a label
sudo timeshift --create --comments "before-kernel-update" --tags D

# List all snapshots
sudo timeshift --list

# Restore from snapshot #2026-05-26_09-00-00
sudo timeshift --restore --snapshot '2026-05-26_09-00-00' --skip-grub

# Automated backup to external drive
sudo timeshift --create --device /dev/sdb1 --comments "weekly-backup"
```

### Timeshift Scheduled Snapshots

```bash
# Set snapshot schedule (daily, keep last 5)
sudo timeshift --check --scripted

# Configure in GUI:
# - Schedule: Daily at 2:00 AM
# - Snapshot levels: 5 daily, 3 weekly, 2 monthly
# - Include: / (root filesystem)
# - Exclude: /home, /tmp, /var/cache
```

## Btrfs-Assistant

Btrfs-Assistant is a GUI management tool designed to simplify Btrfs filesystem administration, with a strong focus on Snapper snapshot integration. Forked from the original GitLab project, it provides a user-friendly interface for managing Btrfs subvolumes, Snapper snapshots, and system rollback — combining the power of Snapper with an accessible desktop application.

### Key Features

- Graphical interface for Btrfs subvolume and snapshot management
- Built-in Snapper integration with snapshot browsing and comparison
- System rollback with boot entry management (GRUB and systemd-boot)
- Subvolume creation, deletion, and property modification
- Snapshot scheduling configuration through GUI
- Snapshot comparison with file-level diff viewing
- Integration with grub-btrfs for boot-time snapshot selection

### Architecture

Btrfs-Assistant is a GTK4 application that wraps the Snapper CLI and Btrfs command-line tools. It communicates with Snapper via D-Bus and executes btrfs commands with elevated privileges (via polkit). The application provides a unified view of all Snapper configurations and their associated snapshots, making it easy to browse, compare, and restore from the desktop.

```bash
# Install Btrfs-Assistant (Arch Linux)
sudo pacman -S btrfs-assistant

# Install Btrfs-Assistant (openSUSE)
sudo zypper install btrfs-assistant

# Install Btrfs-Assistant (from source)
git clone https://github.com/nexusriot/btrfs-assistant
cd btrfs-assistant
mkdir build && cd build
cmake ..
make
sudo make install

# Install required dependencies
sudo apt install snapper btrfs-progs polkit-1
```

### Docker/Container-Based Management

While Btrfs-Assistant is primarily a desktop GUI tool, the underlying Snapper service can be managed in containers for server environments:

```yaml
# docker-compose.yml - Snapper management service
version: "3.8"
services:
  snapper-manager:
    image: alpine:latest
    container_name: snapper-manager
    volumes:
      - /:/host:rw
      - /etc/snapper:/etc/snapper:rw
      - /var/log/snapper.log:/var/log/snapper.log:rw
    command: >
      sh -c "apk add snapper btrfs-progs &&
             snapper -c root create-config / &&
             snapper -c root create --description 'docker-init' &&
             tail -f /dev/null"
    privileged: true
    restart: unless-stopped
```

## Comparison Table

| Feature | Snapper | Timeshift | Btrfs-Assistant |
|---------|---------|-----------|-----------------|
| **Type** | CLI/D-Bus daemon | Desktop GUI + CLI | Desktop GUI |
| **Primary use** | Server & desktop | Desktop-focused | Desktop-focused |
| **Snapshot backend** | Btrfs, LVM thin | Btrfs, rsync | Snapper (Btrfs) |
| **Auto-scheduling** | Yes (built-in timeline) | Yes (cron-based) | Via Snapper config |
| **Package manager hooks** | Yes (zypper, apt, dnf) | No | No |
| **File-level diff** | Yes (CLI) | No | Yes (GUI) |
| **System rollback** | Manual (restore files) | Yes (one-click) | Yes (one-click + boot) |
| **GRUB integration** | No | Yes | Yes (grub-btrfs) |
| **Retention policies** | Configurable (number/timeline) | Fixed levels | Via Snapper config |
| **Multi-subvolume** | Yes (per-config) | Limited | Yes |
| **CLI interface** | Full-featured | Partial | No (GUI only) |
| **Server-friendly** | Yes | Partially | No (desktop GUI) |
| **GitHub stars** | ~1,116 | ~4,071 | ~36+ (mirrors) |

## Deployment Recommendations

### Server Environment: Snapper

For servers, Snapper is the clear choice. It runs as a lightweight daemon with no GUI dependencies, integrates with package managers for automatic pre-update snapshots, and provides flexible retention policies via cron and timeline schedules. The D-Bus API allows integration with custom monitoring and automation scripts.

### Desktop Environment: Btrfs-Assistant + Snapper

For desktop users, Btrfs-Assistant provides the best user experience. It wraps Snapper's functionality in an intuitive GUI, making it easy to browse snapshots, compare changes, and perform rollbacks without command-line knowledge. Snapper handles the backend snapshot creation and retention.

### Multi-Purpose: Timeshift

Timeshift is a good middle ground for users who want a standalone tool without Snapper dependency. Its rsync mode also works on non-Btrfs filesystems, making it more portable. However, it lacks the deep integration with package managers and the file-level diff capabilities of Snapper.

## Why Self-Host Btrfs Snapshot Management?

Automated snapshot management is essential for any production or desktop Btrfs deployment:

- **Zero-downtime rollback** — revert system changes instantly without booting from rescue media
- **Protection against bad updates** — automatic pre-update snapshots mean every package upgrade is reversible
- **Ransomware and corruption recovery** — read-only snapshots cannot be modified by malicious software
- **Cost-effective backup** — Btrfs snapshots use near-zero additional disk space due to copy-on-write
- **Audit trail** — timeline snapshots provide a historical record of system state changes
- **Developer safety** — snapshot before testing configuration changes or running risky scripts

For broader storage management, our [distributed file storage comparison](../2026-05-08-self-hosted-storage-replication-drbd-zfs-glusterfs-georep-guide/) covers alternative approaches to data protection, and our [ZFS snapshot replication guide](../sanoid-vs-znapzend-vs-syncoid-zfs-snapshot-replication-guide-2026/) provides comparison with ZFS's snapshot ecosystem. If you're evaluating NFS-based storage, our [NFS high availability guide](../2026-05-11-self-hosted-nfs-high-availability-drbd-glusterfs-pacemaker-guide/) covers complementary redundancy strategies.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Btrfs Snapshot Management",
  "description": "Compare Btrfs snapshot management tools: Snapper for server automation, Timeshift for desktop restore, and Btrfs-Assistant for GUI-based snapshot management.",
  "datePublished": "2026-05-16",
  "dateModified": "2026-05-16",
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

### What is the difference between Snapper and Timeshift for Btrfs?

Snapper is a snapshot management daemon with deep package manager integration and file-level diff capabilities. Timeshift is a standalone restore tool with a user-friendly GUI that works on both Btrfs (using snapshots) and non-Btrfs filesystems (using rsync). Snapper is better for servers; Timeshift is better for desktop users who want a simple restore tool.

### Can I use Btrfs-Assistant on a headless server?

No. Btrfs-Assistant is a GTK4 desktop GUI application that requires a graphical environment. For headless servers, use Snapper directly via CLI. You can manage Snapper configurations remotely over SSH using `snapper` commands.

### How much disk space do Btrfs snapshots consume?

Initially, snapshots consume nearly zero additional space because Btrfs uses copy-on-write. Only the blocks that change after the snapshot was taken consume additional space. A snapshot of a 100 GB filesystem with 5 GB of daily changes will grow by approximately 5 GB per day.

### How do I boot from a Btrfs snapshot?

With grub-btrfs (used by Btrfs-Assistant) or GRUB Btrfs integration, snapshots appear as boot entries in the GRUB menu. Select the snapshot to boot from, and the system will mount that snapshot as the root filesystem. This allows you to boot into a previous system state if the current system fails to start.

### Should I snapshot the /home directory?

It depends on your needs. Snapper typically excludes /home by default because user data changes frequently and consumes significant snapshot storage. Timeshift also excludes /home by default. If you need /home snapshots, configure Snapper's include/exclude lists in `/etc/snapper/configs/` or enable /home in Timeshift settings.

### How do I automate snapshot cleanup to prevent disk full?

Configure retention policies in Snapper's config file (`/etc/snapper/configs/root`): set `NUMBER_LIMIT` to cap total snapshots, and `TIMELINE_LIMIT_*` for time-based retention. Snapper's cleanup algorithms automatically delete snapshots exceeding these limits. For Timeshift, set the number of retained snapshots per level in the schedule configuration.
