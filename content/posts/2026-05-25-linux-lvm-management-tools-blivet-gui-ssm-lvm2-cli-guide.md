---
title: "Self-Hosted Linux LVM Management: Blivet-GUI vs System Storage Manager vs LVM2 CLI"
date: "2026-05-25"
tags: ["lvm", "storage-management", "linux-system-administration", "disk-management"]
draft: false
---

Logical Volume Management (LVM) is the standard storage abstraction layer on most enterprise Linux distributions, enabling flexible volume resizing, snapshotting, and pooling across multiple physical disks. But managing LVM through raw command-line tools like `lvcreate` and `vgextend` can be error-prone, especially in production environments where a mistyped command can destroy data. Three distinct approaches to LVM management have emerged: the traditional **LVM2 CLI** toolset, the graphical **Blivet-GUI** interface, and the unified **System Storage Manager (SSM)**. Each offers different tradeoffs between power, safety, and ease of use.

## LVM2 CLI: The Traditional Power-User Approach

LVM2 is the reference implementation of Linux Logical Volume Manager, providing a comprehensive suite of command-line tools for every aspect of volume management. It is installed by default on most Linux distributions and offers the most complete feature set, including thin provisioning, cache volumes, RAID logical volumes, and snapshot management.

### Core LVM2 Commands

```bash
# Physical Volume management
pvcreate /dev/sdb /dev/sdc
pvdisplay
pvscan

# Volume Group management
vgcreate vg-data /dev/sdb /dev/sdc
vgextend vg-data /dev/sdd
vgdisplay
vgs

# Logical Volume management
lvcreate -L 100G -n lv-apps vg-data
lvcreate -L 50G --thinpool lv-pool vg-data
lvextend -L +50G /dev/vg-data/lv-apps
resize2fs /dev/vg-data/lv-apps
```

### LVM Snapshots

```bash
# Create a snapshot (traditional)
lvcreate -L 10G -s -n lv-apps-snap /dev/vg-data/lv-apps

# Create a thin snapshot (space-efficient)
lvcreate -s -n lv-apps-snap /dev/vg-data/lv-apps

# Merge snapshot to revert
lvconvert --merge /dev/vg-data/lv-apps-snap
```

### Docker-Based LVM Operations

For containerized environments, LVM can be managed through privileged containers:

```dockerfile
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y     lvm2 parted e2fsprogs xfsprogs     && rm -rf /var/lib/apt/lists/*
ENTRYPOINT ["/bin/bash"]
```

```bash
# Run LVM management in a container
docker run --rm -it --privileged   --device=/dev/mapper/control   -v /dev:/dev   lvm-tools:latest   bash -c "vgdisplay && lvdisplay"
```

## Blivet-GUI: Visual Storage Management

Blivet-GUI is a graphical storage management application built on top of the Python Blivet library. It provides a visual interface for managing all aspects of storage configuration — including LVM, LUKS encryption, software RAID, Btrfs, and traditional partitions — through a single unified interface.

With 197 stars on GitHub and active maintenance by the storaged-project community, Blivet-GUI is particularly valuable for administrators who prefer visual confirmation before executing destructive storage operations. Every action is staged and reviewed before being applied, reducing the risk of accidental data loss.

### Installing Blivet-GUI

```bash
# Fedora/RHEL
sudo dnf install -y blivet-gui

# Debian/Ubuntu
sudo apt install -y blivet-gui

# OpenSUSE
sudo zypper install -y blivet-gui
```

### Key Blivet-GUI Features

- **Visual device tree** — see all disks, partitions, volume groups, and logical volumes in a hierarchical view
- **Action staging** — all changes are queued and displayed before being committed, allowing review and cancellation
- **LVM thin provisioning** — create and manage thin pools and thin volumes through the GUI
- **LUKS encryption** — encrypt new volumes or add encryption layers to existing LVM structures
- **Btrfs subvolume management** — create, delete, and snapshot Btrfs subvolumes alongside LVM
- **Undo support** — cancel pending actions before they are applied to disk

## System Storage Manager (SSM): Unified CLI Abstraction

System Storage Manager (SSM) provides a simplified, unified command-line interface that abstracts away the differences between LVM, Btrfs, dm-crypt, and other storage backends. Instead of learning separate command sets for each storage technology, SSM offers a single consistent interface.

SSM automatically detects available storage backends and presents a unified view of all pools, volumes, and devices. This makes it particularly useful in mixed environments where different storage technologies coexist.

### Installing SSM

```bash
# Fedora/RHEL (included in base system)
sudo dnf install -y system-storage-manager

# Source install
git clone https://github.com/dinhxuanvu/ssm.git
cd ssm
sudo make install
```

### SSM Commands for LVM Management

```bash
# View all storage devices, pools, and volumes
ssm list
ssm list dev
ssm list pool
ssm list vol

# Create a new LVM volume (auto-creates VG if needed)
ssm create -s 100G -n lv-apps --fstype ext4 -p vg-data /dev/sdb

# Add a disk to an existing pool
ssm add -p vg-data /dev/sdc

# Resize a volume and filesystem in one step
ssm resize -s +50G vg-data/lv-apps

# Create an encrypted LVM volume
ssm create -s 50G -n lv-secret --fstype ext4   --encrypt luks2 /dev/sdb

# Take a snapshot
ssm snapshot vg-data/lv-apps
```

### SSM vs Raw LVM2: Command Comparison

| Task | LVM2 CLI | SSM |
|---|---|---|
| Create 100G volume | `lvcreate -L 100G -n lv-apps vg-data` + `mkfs.ext4` + `mount` | `ssm create -s 100G -n lv-apps -p vg-data /mnt/apps` |
| Resize volume | `lvextend -L +50G ...` + `resize2fs ...` | `ssm resize -s +50G vg-data/lv-apps` |
| Add disk to VG | `vgextend vg-data /dev/sdc` | `ssm add -p vg-data /dev/sdc` |
| Create encrypted volume | `cryptsetup luksFormat` + `cryptsetup open` + `pvcreate` + `vgcreate` + `lvcreate` | `ssm create -s 50G --encrypt luks2 /dev/sdb` |
| List all storage | `pvdisplay; vgdisplay; lvdisplay` | `ssm list` |

## Comparison Table

| Feature | LVM2 CLI | Blivet-GUI | System Storage Manager |
|---|---|---|---|
| **Interface** | Command-line only | Graphical (GTK) | Command-line |
| **Learning Curve** | Steep (many commands) | Low (visual) | Moderate (unified syntax) |
| **LVM Support** | Complete | Complete | Core features |
| **LUKS Encryption** | Via cryptsetup | Built-in | Built-in |
| **Btrfs Support** | No (separate tools) | Built-in | Built-in |
| **Software RAID** | Via mdadm | Built-in | Built-in |
| **Action Preview** | No (immediate) | Yes (staged) | No (immediate) |
| **Undo Support** | No | Yes (before apply) | No |
| **Scriptable** | Excellent | Limited | Good |
| **Thin Provisioning** | Full support | Full support | Basic support |
| **GitHub Stars** | 152 (lvmteam mirror) | 197 (storaged-project) | 2 (community) |
| **Best For** | Automation/scripts | Visual management | Quick unified CLI |

## When to Use Each Tool

**Choose LVM2 CLI when:** You need the full power of LVM — thin provisioning, RAID logical volumes, cache pools, or complex snapshot hierarchies. LVM2 CLI is also the only choice for automation scripts, Ansible playbooks, and infrastructure-as-code deployments. For containerized LVM management, see our [container storage CSI guide](../2026-05-12-self-hosted-nbd-storage-server-nbd-server-nbdkit-drbd-guide/) for integration patterns.

**Choose Blivet-GUI when:** You are managing storage on a workstation or server with a graphical environment, and you want visual confirmation before executing potentially destructive operations. The action staging system catches mistakes before they reach the disk. This is particularly valuable for administrators who manage storage infrequently and benefit from a visual interface.

**Choose SSM when:** You manage a mixed environment with LVM, Btrfs, and encrypted volumes, and want a single consistent interface for all operations. SSM is ideal for administrators who need to perform common tasks (create, resize, snapshot) quickly without remembering the specific command syntax for each backend.

## Why Self-Host Your LVM Management Strategy?

Self-hosted infrastructure demands reliable, predictable storage management. Whether you are running a home lab with a handful of drives or managing a production cluster with dozens of storage nodes, having a consistent approach to LVM management reduces operational risk and accelerates incident response.

The choice between CLI and GUI tools is not about capability — all three approaches can manage LVM effectively. It is about matching the tool to the operator and the context. Production automation demands LVM2 CLI for reproducibility and integration with configuration management systems. Interactive management on workstations benefits from Blivet-GUI's visual safety nets. Quick administrative tasks across heterogeneous storage systems are streamlined by SSM's unified syntax.

For teams managing software-defined storage infrastructure, LVM management integrates with broader storage strategies. When deploying [storage replication solutions](../2026-05-08-self-hosted-storage-replication-drbd-zfs-glusterfs-georep-guide/) with DRBD or ZFS geo-replication, the underlying LVM volumes serve as the building blocks for replication targets. Understanding how to efficiently create, resize, and snapshot these volumes directly impacts your replication topology's flexibility and recovery time objectives.

Organizations running [software RAID arrays](../2026-05-23-linux-software-raid-management-mdadm-vs-btrfs-vs-zfs-guide/) often layer LVM on top of mdadm devices, combining RAID's fault tolerance with LVM's flexible volume management. This layered approach requires proficiency with both toolsets — LVM commands operate on `/dev/mdX` devices just as they do on raw `/dev/sdX` disks.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux LVM Management: Blivet-GUI vs System Storage Manager vs LVM2 CLI",
  "description": "Compare LVM2 CLI, Blivet-GUI, and System Storage Manager for Linux logical volume management. Choose the right tool for your self-hosted infrastructure.",
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

### Can I mix LVM and Btrfs on the same system?
Yes, and Blivet-GUI and SSM both support this configuration natively. A common pattern is to use LVM for general-purpose volumes and Btrfs for specific workloads that benefit from its copy-on-write semantics, such as database storage or snapshot-heavy applications. SSM can manage both backends through its unified interface.

### Does Blivet-GUI support thin provisioning?
Yes. Blivet-GUI provides full support for LVM thin pools and thin logical volumes through its graphical interface. You can create thin pools, allocate thin volumes, and monitor pool usage all within the GUI. The visual display makes it easy to see pool utilization at a glance.

### Is SSM production-ready?
SSM is suitable for common storage operations (create, resize, snapshot, encrypt) but does not expose the full depth of LVM2 features. For production environments requiring thin provisioning, RAID logical volumes, or cache configurations, use LVM2 CLI directly. SSM is best viewed as a convenience layer for routine tasks.

### Can I manage remote LVM volumes with these tools?
LVM2 CLI works over SSH — simply SSH into the target server and run LVM commands. Blivet-GUI is a local GUI application and does not support remote management natively. SSM also requires local execution but can be scripted over SSH for remote administration.

### How do LVM snapshots differ from filesystem snapshots?
LVM snapshots operate at the block device level, capturing the state of an entire logical volume regardless of the filesystem type. They use copy-on-write (traditional) or reference counting (thin) to store only changed blocks. Filesystem snapshots (Btrfs, ZFS) operate at the filesystem level and understand file semantics. LVM snapshots work with any filesystem but are limited by the allocated snapshot space.

### Can I convert between storage backends without data loss?
Blivet-GUI and SSM can migrate between some storage types (e.g., adding LUKS encryption to an existing LVM volume), but converting between fundamentally different backends (LVM to Btrfs, or vice versa) requires creating a new volume and copying data. Always verify backups before attempting storage migrations.
