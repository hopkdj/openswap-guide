---
title: "Self-Hosted iSCSI Target Servers: LIO vs TGT vs SCST Comparison Guide 2026"
date: 2026-05-10
tags: ["comparison", "guide", "self-hosted", "storage", "iscsi", "block-storage", "san", "lio", "tgt"]
draft: false
description: "Compare LIO (targetcli-fb), TGT, and SCST for self-hosted iSCSI target management. Complete deployment guide with configuration examples, Docker setup, and SAN architecture."
---

iSCSI (Internet Small Computer Systems Interface) enables block-level storage access over IP networks, allowing servers to mount remote storage volumes as if they were local disks. For self-hosted infrastructure, running your own iSCSI target server provides cost-effective SAN (Storage Area Network) capabilities without expensive proprietary hardware.

In this guide, we compare three open-source iSCSI target implementations: **LIO** (Linux IO Target, managed via targetcli-fb), **TGT** (Linux SCSI Target Framework), and **SCST** (SCSI Target Subsystem).

## What Is an iSCSI Target?

In iSCSI terminology, a **target** is the storage server that provides block devices, and an **initiator** is the client that connects to those block devices. The target exports storage (disk partitions, LVM volumes, or files) as iSCSI LUNs (Logical Unit Numbers) that initiators can format and mount.

Key components:
- **Target Portal Group (TPG)**: Defines the IP addresses and ports the target listens on
- **LUN**: A logical unit of storage exported to initiators
- **IQN** (iSCSI Qualified Name): Unique identifier for targets and initiators (e.g., `iqn.2026-05.com.example:storage`)
- **ACL** (Access Control List): Restricts which initiators can connect to which LUNs
- **CHAP authentication**: Optional mutual authentication between target and initiator

## LIO (Linux IO Target)

LIO is the default iSCSI target in modern Linux kernels (since 2.6.38). It supports iSCSI, Fibre Channel, FCoE, and SRP protocols through a unified target framework. Configuration is managed through the `targetcli-fb` interactive shell.

### Installation and Configuration

```bash
# Install targetcli
apt-get update && apt-get install -y targetcli-fb

# Start the service
systemctl enable target
systemctl start target
```

### Create an iSCSI Target with targetcli

```bash
targetcli

# Create a backstore (file-backed)
/> backstores/fileio create disk01 /srv/iscsi/disk01.img 100G

# Create an iSCSI target
/> iscsi/ create iqn.2026-05.com.example:storage01

# Configure the TPG
/> iscsi/iqn.2026-05.com.example:storage01/tpg1/ set attribute authentication=0
/> iscsi/iqn.2026-05.com.example:storage01/tpg1/ set attribute generate_node_acls=1

# Map the LUN
/> iscsi/iqn.2026-05.com.example:storage01/tpg1/luns/ create /backstores/fileio/disk01

# Set up a portal (listener)
/> iscsi/iqn.2026-05.com.example:storage01/tpg1/portals/ create 0.0.0.0 3260

# Save configuration
/> saveconfig
/> exit
```

### LIO with Block Storage (LVM)

For better performance, use block-backed storage instead of file-backed:

```bash
# Create LVM volume
vgcreate iscsi_vg /dev/sdb
lvcreate -L 500G -n lun01 iscsi_vg

# In targetcli
/> backstores/block create lun01 /dev/mapper/iscsi_vg-lun01
/> iscsi/iqn.2026-05.com.example:storage01/tpg1/luns/ create /backstores/block/lun01
```

### LIO Docker Deployment

```yaml
version: "3.8"
services:
  lio-target:
    image: erichough/iscsi-target:latest
    container_name: iscsi-target
    privileged: true
    network_mode: host
    volumes:
      - /dev:/dev
      - ./targetcli_saveconfig:/etc/target/saveconfig.json:rw
      - /srv/iscsi:/srv/iscsi:rw
    restart: unless-stopped
```

## TGT (Linux SCSI Target Framework)

TGT (tgtadm) is an older userspace iSCSI target implementation. While largely superseded by LIO in modern kernels, it remains simpler to configure for basic use cases and doesn't require kernel-space target drivers.

### Installation

```bash
apt-get update && apt-get install -y tgt
systemctl enable tgt
systemctl start tgt
```

### Configuration via /etc/tgt/targets.conf

```xml
<target iqn.2026-05.com.example:storage02>
    # File-backed LUN
    backing-store /srv/iscsi/disk02.img
    
    # Optional: CHAP authentication
    incominguser initiator_user secret_password
    
    # Optional: Restrict by initiator IQN
    initiator-address 192.168.1.0/24
    
    # Optional: Read-only LUN
    # write-cache off
</target>

<target iqn.2026-05.com.example:storage03>
    # Block-backed LUN for better performance
    backing-store /dev/mapper/iscsi_vg-lun02
    
    incominguser db_server db_secret
    initiator-address 192.168.1.50
</target>
```

Apply configuration:

```bash
tgtadm --mode target --op update --tid 1 --name State --value ready
```

## SCST (SCSI Target Subsystem)

SCST is a high-performance in-kernel SCSI target framework. It is designed for enterprise workloads and supports a wide range of transport protocols including iSCSI, SRP, and FCoE. SCST is commonly used in high-end storage appliances and provides the best performance for demanding I/O workloads.

### Installation

SCST requires kernel module compilation:

```bash
apt-get install -y build-essential linux-headers-$(uname -r)

# Clone SCST
git clone https://github.com/SCST-project/scst.git
cd scst

# Build and install
make all
make install

# Load modules
modprobe scst
modprobe scst_vdisk
modprobe iscsi-scst
```

### Configuration

Configure `/etc/iscsi-scst.conf`:

```ini
[DEFAULT]
MaxConnections 4
DataDigest None
HeaderDigest None

[Target iqn.2026-05.com.example:storage03]
[LUN 0]
    path=/dev/mapper/iscsi_vg-lun03
    type=fileio
    
[Initiator iqn.2026-05.com.example:db-server]
    CHAP Username db_server
    CHAP Password db_secret
```

Start the daemon:

```bash
systemctl enable iscsi-scst
systemctl start iscsi-scst
```

## Comparison: LIO vs TGT vs SCST

| Feature | LIO (targetcli) | TGT (tgtadm) | SCST |
|---------|----------------|--------------|------|
| Kernel version | 2.6.38+ (mainline) | Userspace | External module |
| Configuration method | targetcli shell | XML config file | Config file + CLI |
| Performance | High (kernel-space) | Medium (userspace) | Very high (kernel-space) |
| Protocol support | iSCSI, FC, FCoE, SRP | iSCSI only | iSCSI, SRP, FCoE |
| Backstore types | fileio, block, pscsi, ramdisk | file, block | fileio, block, pscsi |
| CHAP auth | Yes | Yes | Yes |
| Active development | Yes (kernel tree) | Maintenance | Yes (community) |
| Installation complexity | Low | Low | High (kernel build) |
| Production readiness | Excellent | Good | Excellent |
| Docker support | Good | Good | Poor (kernel modules) |

## Initiator (Client) Configuration

Connect to an iSCSI target from a client:

```bash
# Install open-iscsi
apt-get install -y open-iscsi

# Discover targets
iscsiadm -m discovery -t st -p 192.168.1.100:3260

# Login to target
iscsiadm -m node -T iqn.2026-05.com.example:storage01 -p 192.168.1.100:3260 --login

# Verify connection
iscsiadm -m session

# The new disk appears as /dev/sdX
lsblk

# Format and mount
mkfs.ext4 /dev/sdb
mkdir -p /mnt/iscsi
mount /dev/sdb /mnt/iscsi
```

Add to `/etc/fstab` for persistent mounting:

```
/dev/sdb  /mnt/iscsi  ext4  _netdev,noatime  0  2
```

The `_netdev` flag ensures the filesystem is mounted after the network is available.

## Why Self-Host iSCSI Targets?

Running your own iSCSI target infrastructure provides centralized block storage that multiple servers can share. Instead of purchasing expensive SAN hardware, you can build a software-defined storage system using commodity servers and standard network equipment.

Self-hosted iSCSI is ideal for virtualization clusters (Proxmox, oVirt, XCP-ng) where VMs need shared block storage for live migration. For file-level sharing alternatives, see our [NFS server comparison](../2026-04-30-nfs-ganesha-vs-unfs3-vs-kernel-nfs-self-hosted-nfs-server-guide-2026/). For distributed file systems, check our [JuiceFS vs Alluxio vs CephFS guide](../2026-04-28-juicefs-vs-alluxio-vs-cephfs-self-hosted-distributed-file-systems-2026/). And for object storage needs, our [MinIO vs SeaweedFS vs Garage comparison](../2026-05-03-self-hosted-s3-object-storage-minio-seaweedfs-garage-guide/) covers S3-compatible alternatives.

## FAQ

### What is the difference between iSCSI and NFS?

iSCSI provides block-level storage (raw disks), while NFS provides file-level storage (shared directories). With iSCSI, each initiator formats and manages its own filesystem on the exported LUN. With NFS, the server manages the filesystem and clients mount shared directories. Choose iSCSI for databases and VMs, NFS for shared files.

### Can multiple initiators access the same iSCSI LUN simultaneously?

Multiple initiators can connect to the same LUN, but simultaneous read/write access requires a cluster-aware filesystem (OCFS2, GFS2) or a distributed filesystem. Without cluster filesystem support, simultaneous writes will corrupt data. For shared access, consider using a distributed filesystem instead.

### Is iSCSI secure over untrusted networks?

Standard iSCSI transmits data in plaintext. For untrusted networks, use iSCSI over IPsec or deploy iSCSI on an isolated storage VLAN. CHAP authentication provides initiator-level access control but does not encrypt the data payload.

### What backstore type should I use for best performance?

Block-backed storage (LVM volumes, raw partitions) provides the best performance because it bypasses the host filesystem. File-backed storage (fileio) adds filesystem overhead but is easier to manage and resize. Use block-backed for production databases and VMs, fileio for testing.

### How do I back up iSCSI LUNs?

For file-backed LUNs, snapshot the underlying filesystem. For block-backed LUNs, use LVM snapshots or storage-level snapshots. The initiator can also run traditional backup tools (rsync, restic, borg) on the mounted filesystem.

### Does LIO work with Docker containers?

LIO can run in Docker using privileged containers with host network mode, as shown in the deployment example above. However, the kernel modules must be loaded on the host system. The container runs the management interface (targetcli) while the kernel handles the actual I/O path.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted iSCSI Target Servers: LIO vs TGT vs SCST Comparison Guide 2026",
  "description": "Compare LIO (targetcli-fb), TGT, and SCST for self-hosted iSCSI target management. Complete deployment guide with configuration examples, Docker setup, and SAN architecture.",
  "datePublished": "2026-05-10",
  "dateModified": "2026-05-10",
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
