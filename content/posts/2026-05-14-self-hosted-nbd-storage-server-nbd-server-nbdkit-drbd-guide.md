---
title: "Self-Hosted Network Block Device Servers: nbd-server vs nbdkit vs DRBD (2026)"
date: "2026-05-14"
tags: ["storage", "nbd", "network-block-device", "disk-replication", "self-hosted"]
draft: false
---

The Network Block Device (NBD) protocol allows a server to export block devices over a network, making remote storage appear as a local disk to clients. Unlike file-level protocols like NFS or SMB, NBD operates at the raw block level, enabling use cases that require direct disk access: virtual machine disk images, clustered filesystems, distributed storage backends, and live disk migration.

In this guide, we compare three open-source solutions for self-hosted NBD storage servers: **nbd-server**, the reference NBD server implementation; **nbdkit**, the flexible NBD server toolkit with extensive plugin support; and **DRBD**, the distributed replicated block device that provides network RAID-1 for Linux.

## What Is a Network Block Device?

A Network Block Device makes a remote disk or file available to a client over the network as if it were a locally-attached block device. The client sees a raw `/dev/nbdX` device that it can partition, format, mount, or use directly — identical to a physical disk.

Key use cases for NBD include:

- **Virtual Machine Storage**: Export VM disk images to hypervisors over the network for centralized storage
- **Clustered Filesystems**: Provide shared block storage for DRBD, OCFS2, or GFS2 clustered filesystems
- **Live Migration**: Move running virtual machines between hosts by transferring block device access
- **Backup and Replication**: Stream block-level changes for incremental backups or disaster recovery
- **Thin Provisioning**: Allocate storage on-demand using NBD's built-in thin provisioning support
- **Boot-over-Network**: Boot diskless clients from a network block device (PXE + NBD root filesystem)

Self-hosting NBD infrastructure gives you full control over storage performance, replication policies, and data locality — without vendor lock-in or per-gigabyte licensing fees.

## Comparison Overview

| Feature | nbd-server | nbdkit | DRBD |
|---------|-----------|--------|------|
| GitHub Stars | N/A (Debian package) | 200+ (RichardWMJones/nbdkit) | 350+ (LINBIT/drbd-manager) |
| Primary Purpose | Reference NBD server | Flexible NBD server toolkit | Distributed replicated block device |
| Protocol | NBD protocol | NBD + NBDKit plugin API | DRBD protocol (block replication) |
| Storage Backend | Files, block devices | 40+ plugins (files, S3, HTTP, tape, QCOW2) | Block devices, LVM, partitions |
| Replication | None (single server) | Via plugins | Built-in network RAID-1 |
| High Availability | Manual failover | Via clustering | Automatic failover, dual-primary |
| Thin Provisioning | Yes (NBD_OPT_GO) | Via plugins | Yes |
| Encryption | Via stunnel/SSH | TLS built-in | TLS built-in |
| QoS/Rate Limiting | Basic | Via plugins | Built-in sync rate control |
| Docker Support | Community images | Community images | Official LINBIT images |
| Kernel Integration | Client via nbd.kt module | Client via nbd.kt module | Kernel module (drbd.ko) |
| License | GPL-2.0 | BSD-2-Clause | GPL-2.0 |

## nbd-server: Reference NBD Implementation

nbd-server is the standard reference implementation of the NBD protocol, included in most Linux distributions. It provides a straightforward way to export files or block devices as network block devices.

### Key Features

- **Simple Configuration**: Export any file or block device with a single configuration stanza
- **Multiple Exports**: Serve multiple NBD exports from a single daemon process
- **Read-Only Mode**: Export devices as read-only for backup or archival purposes
- **File-Based Backend**: Export disk images stored as regular files
- **Multi-Client Access**: Support for multiple concurrent clients (with proper filesystem coordination)
- **Unix Socket Support**: Serve NBD over Unix domain sockets for local communication

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  nbd-server:
    image: ghcr.io/linuxserver/nbd-server:latest
    container_name: nbd-server
    ports:
      - "10809:10809"
    volumes:
      - ./storage:/storage
      - ./config/nbd-server.conf:/etc/nbd-server/config
    environment:
      - TZ=UTC
    cap_add:
      - SYS_ADMIN
    devices:
      - /dev/nbd0:/dev/nbd0
    restart: unless-stopped
```

Configuration example (`/etc/nbd-server/config`):

```ini
[generic]
user = nbd
group = nbd
include = /etc/nbd-server/conf.d

[vm-disk-1]
exportname = /storage/vm-disk-1.img
filesize = 100G
readonly = false
multifile = false
copyonwrite = false
```

For direct installation:

```bash
sudo apt install nbd-server nbd-client
sudo systemctl enable --now nbd-server
```

Connect from client:

```bash
sudo nbd-client 192.168.1.100 10809 /dev/nbd0
sudo mount /dev/nbd0 /mnt/nbd
```

### Strengths

- Simple, reliable, and well-tested — the reference implementation
- Available in all major Linux distribution repositories
- Minimal resource overhead (single daemon process)
- Supports both file and block device exports

### Limitations

- No built-in replication or high availability
- Basic feature set compared to more advanced solutions
- No encryption — requires external tunneling (SSH, stunnel)
- Limited to single-server deployments

## nbdkit: Flexible NBD Server Toolkit

[nbdkit](https://github.com/libguestfs/nbdkit) is a toolkit for building NBD servers with an extensive plugin architecture. Rather than being a single-purpose server, nbdkit provides a framework where plugins handle everything from storage backends to protocol adapters.

### Key Features

- **40+ Plugins**: Plugins for files, S3, HTTP, FTP, SSH, tape drives, QCOW2, VMDK, ISO, partition filters, and more
- **Filter Pipeline**: Stackable filters for caching, compression, encryption, rate limiting, and access control
- **Built-in TLS**: Native TLS encryption without requiring external tunneling
- **Scriptable**: Write custom plugins in Python, Perl, OCaml, Rust, or C
- **Live Reload**: Modify server configuration without restarting the daemon
- **Unix and TCP Sockets**: Serve NBD over both transport types simultaneously

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  nbdkit:
    image: libguestfs/nbdkit:latest
    container_name: nbdkit
    ports:
      - "10809:10809"
    volumes:
      - ./storage:/storage
      - ./certs:/certs:ro
    command: >
      nbdkit -fv --tls=require
      --certificate=/certs/server-cert.pem
      --private-key=/certs/server-key.pem
      file file=/storage/disk.img
    restart: unless-stopped
```

Example with S3 backend plugin:

```bash
# Serve an S3 object as an NBD block device
nbdkit s3 endpoint=s3.us-east-1.amazonaws.com   bucket=my-backup-bucket key=vm-disk.qcow2
```

Example with filter pipeline (rate limiting + caching):

```bash
nbdkit --filter=cache --filter=ratelimit   file file=/storage/disk.img   ratelimit-bytes-per-second=104857600
```

### Strengths

- Extremely flexible — can serve almost any data source as an NBD device
- Built-in TLS eliminates the need for external encryption tunneling
- Plugin architecture allows custom backends and filters
- Active development by Red Hat/libguestfs team
- QCOW2 and VMDK support for virtualization workflows

### Limitations

- Requires understanding of plugin architecture for advanced use
- No built-in block replication (unlike DRBD)
- Smaller community compared to nbd-server
- Plugin quality varies — some are experimental

## DRBD: Distributed Replicated Block Device

[DRBD](https://github.com/LINBIT/drbd-manager) is a Linux kernel module that provides network-based block device replication — essentially RAID-1 over a network. While not a pure NBD server, DRBD serves the same fundamental purpose of making remote block devices available to other nodes, with the added benefit of automatic synchronization and high availability.

### Key Features

- **Network RAID-1**: Real-time block-level replication between nodes over TCP/IP
- **Automatic Resynchronization**: After node failures, DRBD automatically resynchronizes changed blocks
- **Dual-Primary Mode**: Both nodes can read/write simultaneously (with a clustered filesystem)
- **Snapshot Support**: Create consistent point-in-time snapshots without stopping replication
- **Storage Integration**: Works with LVM, ZFS, and direct block devices
- **Pacemaker Integration**: Seamless integration with Pacemaker/Corosync for automatic failover

### Docker Compose Deployment

DRBD typically runs as a kernel module, but LINBIT provides containerized management:

```yaml
version: "3.8"
services:
  drbd:
    image: drbd.io/drbd9:latest
    container_name: drbd
    privileged: true
    network_mode: host
    volumes:
      - /dev:/dev
      - ./drbd.d:/etc/drbd.d
      - ./data:/var/lib/drbd
    environment:
      - DRBD_NODE_ID=1
      - DRBD_RESOURCE=r0
      - DRBD_PEERS=192.168.1.101
    restart: unless-stopped
```

DRBD resource configuration (`/etc/drbd.d/r0.res`):

```
resource r0 {
  device /dev/drbd0;
  disk /dev/sdb1;
  meta-disk internal;

  on node1 {
    address 192.168.1.100:7789;
  }
  on node2 {
    address 192.168.1.101:7789;
  }

  net {
    protocol C;  # synchronous replication
    cram-hmac-alg sha256;
    shared-secret "my-secret-key";
  }
}
```

### Strengths

- True high availability with automatic failover
- Built-in encryption and authentication
- Synchronous replication ensures zero data loss on failover
- Dual-primary mode enables active-active cluster configurations
- Industry-proven with thousands of production deployments

### Limitations

- Requires dedicated block devices (cannot use files as backing storage)
- Two-node replication only (not NBD multi-client)
- Kernel module required on both nodes
- More complex setup compared to pure NBD solutions
- Network latency directly impacts write performance in synchronous mode

## Deployment Architecture

When designing an NBD storage infrastructure, consider these architectural patterns:

**Single-Server with nbd-server**: Simple deployments where one server exports disk images to multiple clients. Best for development environments, testing, or small-scale VM hosting.

**nbdkit for Hybrid Storage**: When you need to serve storage from diverse backends (local files, S3, QCOW2 images) through a single NBD endpoint with TLS encryption and rate limiting.

**DRBD for High Availability**: When block-level replication and automatic failover are required — production database storage, virtual machine HA, or any workload that cannot tolerate a single server failure.

## Why Self-Host NBD Infrastructure?

Running your own NBD storage servers rather than relying on commercial storage area networks (SANs) provides several benefits:

**Hardware Flexibility**: Use commodity hardware with standard NICs instead of expensive Fibre Channel or iSCSI SAN appliances. NBD runs over standard Ethernet with no special hardware requirements.

**No Vendor Lock-In**: The NBD protocol is open and well-documented. Your storage infrastructure is not tied to a specific vendor's ecosystem, making it easy to migrate or expand.

**Cost Efficiency**: A pair of commodity servers running DRBD provides the same high availability as an enterprise SAN at a fraction of the cost. nbd-server and nbdkit are free and open-source.

**Performance Control**: Tune network parameters, replication modes, and caching policies to match your specific workload. Commercial SANs often use one-size-fits-all defaults that may not suit your needs.

**Cloud Portability**: NBD-based storage can be replicated between on-premises and cloud infrastructure, enabling hybrid cloud architectures without proprietary storage gateways.

For related reading, see our [distributed file storage comparison](../ceph-vs-glusterfs-vs-moosefs-distributed-file-storage-2026/) and [Kubernetes storage operators guide](../rook-vs-longhorn-vs-openebs-self-hosted-kubernetes-storage-guide-2026/).

## FAQ

### What is the difference between NBD and iSCSI?

Both NBD and iSCSI export block devices over a network, but they differ in architecture and use cases. NBD is simpler and lighter-weight, designed primarily for Linux-to-Linux communication. iSCSI implements the full SCSI protocol stack over TCP/IP, making it compatible with a wider range of operating systems and storage hardware. NBD is preferred for VM storage and clustered filesystems; iSCSI is used for enterprise SAN deployments.

### Can NBD be used for production database storage?

NBD alone is not recommended for production databases due to its lack of built-in replication and HA. However, DRBD (which serves a similar purpose) is widely used for production database storage with automatic failover and synchronous replication. For NBD-based setups, add external replication or use nbdkit with appropriate filter plugins for caching and rate limiting.

### Does NBD support encryption?

The NBD protocol itself does not mandate encryption, but nbdkit provides built-in TLS support. For nbd-server, you can tunnel connections through SSH or stunnel for encrypted transport. DRBD has built-in encryption support using TLS or IPsec for the replication channel.

### How does DRBD handle network partitions?

DRBD detects network partitions through its connection monitoring. During a partition, the secondary node becomes inconsistent and cannot be promoted to primary without manual intervention (or automated handling via Pacemaker). After the network is restored, DRBD automatically resynchronizes only the changed blocks, minimizing recovery time.

### What are the performance implications of NBD over the network?

NBD adds minimal overhead compared to local disk access — typically 5-15% throughput reduction on a 10GbE network. The primary bottleneck is network latency, not bandwidth. For latency-sensitive workloads, use DRBD with protocol C (synchronous replication) on a low-latency network, or nbdkit with caching enabled to absorb burst write operations.

### Can multiple clients connect to the same NBD export simultaneously?

nbd-server supports multiple concurrent connections to the same export, but coordinating writes requires a clustered filesystem (OCFS2, GFS2, or DRBD dual-primary mode). Without cluster coordination, concurrent writes will corrupt the filesystem. For read-only access (backup, archival), multiple clients can connect safely to any NBD export.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Network Block Device Servers: nbd-server vs nbdkit vs DRBD (2026)",
  "description": "Compare three open-source NBD server solutions for self-hosted network block storage, VM disk serving, and distributed replication.",
  "datePublished": "2026-05-14",
  "dateModified": "2026-05-14",
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
