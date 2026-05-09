---
title: "Self-Hosted NBD Server: Network Block Device Storage Solutions (2026)"
date: "2026-05-10"
tags: ["storage", "nbd", "network-block-device", "block-storage", "linux"]
draft: false
---

Network Block Device (NBD) is a Linux kernel protocol that allows a remote server's storage to appear as a local block device. Unlike file-level sharing protocols like NFS or SMB, NBD operates at the **block level**, meaning the client sees a raw disk device (`/dev/nbd0`) that can be formatted with any filesystem, used for swap, or configured as a LVM physical volume. This makes NBD a powerful tool for building distributed storage architectures, live migration setups, and network-booted environments.

This guide covers three approaches to deploying NBD servers in self-hosted environments: the **official nbd-server** package, the **go-nbd** Go implementation, and **nbdkit** — a flexible NBD server toolkit. Each serves different use cases, from simple block device sharing to complex plugin-based storage backends.

## What Is Network Block Device (NBD)?

NBD is a client-server protocol where:

- The **server** exports one or more block devices (files, partitions, or logical volumes) over TCP
- The **client** connects using the Linux kernel NBD driver and mounts the exported device as `/dev/nbdX`
- The exported device behaves identically to a local disk — you can partition it, format it with ext4/XFS/Btrfs, use it for swap, or add it to a software RAID array

### NBD vs Other Storage Protocols

| Protocol | Level | Use Case |
|----------|-------|----------|
| **NBD** | Block | Raw disk access, LVM, swap, live migration |
| **NFS** | File | Shared file access, home directories |
| **iSCSI** | Block | Enterprise SAN, VM storage |
| **SMB/CIFS** | File | Windows file sharing |
| **DRBD** | Block | Synchronous block replication |

Unlike iSCSI, which requires a full SCSI target implementation, NBD is lightweight and uses a simple protocol. Unlike NFS, which shares files, NBD shares raw blocks — giving the client full control over the filesystem.

## nbd-server (Official Implementation)

**nbd-server** is the reference implementation of the NBD server protocol, maintained by the NetworkBlockDevice organization on GitHub. It is available in all major Linux distributions and provides a straightforward way to export block devices or disk images over the network.

### Key Features

- **Multiple export support** — serve multiple block devices from a single server
- **Read-only and read-write exports** — control client access per export
- **Access control** — restrict connections by IP address
- **Copy-on-write** — overlay writes on top of a read-only backing file
- **Persistent mode** — keep serving after client disconnects
- **TLS encryption** — secure the NBD traffic with TLS certificates
- **Low resource usage** — minimal CPU and memory footprint

### Installation and Configuration

```bash
# Install on Debian/Ubuntu
sudo apt install nbd-server

# Install on RHEL/CentOS/Fedora
sudo dnf install nbd-server
```

```ini
# /etc/nbd-server/config
[generic]
# Global settings
[exports]

[vm-storage]
exportname = /srv/nbd/vm-disk.img
filesize = 100G
readonly = false
multifile = false
copyonwrite = false

[backup-volume]
exportname = /dev/sdb1
readonly = true
autostart = true

[shared-data]
exportname = /srv/nbd/shared.img
filesize = 50G
readonly = false
# Restrict to specific clients
allowlist = 192.168.1.0/24
```

```yaml
# docker-compose.yml for nbd-server
services:
  nbd-server:
    image: trinitroglycerin/nbd-server:latest
    container_name: nbd-server
    privileged: true
    ports:
      - "10809:10809"
    volumes:
      - ./nbd-config:/etc/nbd-server
      - /srv/nbd:/srv/nbd
    environment:
      - NBD_EXPORT_NAME=container-storage
      - NBD_FILE=/srv/nbd/disk.img
      - NBD_FILESIZE=20G
    restart: unless-stopped
    networks:
      - storage-network

networks:
  storage-network:
    driver: bridge
```

### Client Usage

```bash
# Connect to the NBD server
sudo nbd-client 192.168.1.100 10809 /dev/nbd0

# Or with named export
sudo nbd-client 192.168.1.100 10809 /dev/nbd0 -name vm-storage

# Format and mount the device
sudo mkfs.ext4 /dev/nbd0
sudo mount /dev/nbd0 /mnt/nbd

# Disconnect when done
sudo nbd-client -d /dev/nbd0
```

## go-nbd (Go Implementation)

**go-nbd** is a modern Go-based NBD server and client implementation developed by pojntfx. It provides a lightweight, single-binary solution that is easy to deploy in containerized environments. The Go implementation offers faster startup times and simpler cross-platform deployment compared to the C-based reference server.

### Key Features

- **Single binary** — no dependencies, easy containerization
- **Cross-platform** — runs on Linux, macOS, and Windows (server mode on Linux)
- **Simple configuration** — command-line flags or environment variables
- **Fast startup** — Go's goroutine-based concurrency for low-latency I/O
- **Built on nbdkit-compatible plugin architecture**

### Installation

```bash
# Download the latest release
go install github.com/pojntfx/go-nbd@latest

# Or download pre-built binary from GitHub releases
curl -LO https://github.com/pojntfx/go-nbd/releases/latest/download/go-nbd-linux-amd64
chmod +x go-nbd-linux-amd64
sudo mv go-nbd-linux-amd64 /usr/local/bin/go-nbd
```

```yaml
# docker-compose.yml for go-nbd
services:
  go-nbd:
    image: ghcr.io/pojntfx/go-nbd:latest
    container_name: go-nbd
    privileged: true
    ports:
      - "10809:10809"
    volumes:
      - /srv/nbd:/data
    command: >
      server
      --listen :10809
      --backend /data/disk.img
      --size 50G
    restart: unless-stopped
    networks:
      - storage-network

networks:
  storage-network:
    driver: bridge
```

## nbdkit (Plugin-Based NBD Server)

**nbdkit** is a highly flexible NBD server toolkit developed by Red Hat. Rather than being a single-purpose NBD server, nbdkit is a **framework** that uses plugins to expose virtually any data source as an NBD export. With over 30 plugins available, you can export disk images, remote HTTP files, S3 buckets, SSH filesystems, and even generate synthetic data — all through the same NBD protocol.

### Key Features

- **30+ plugins** — export local files, S3, SSH, HTTP, VMDK, QCOW2, and more
- **Filter chain** — apply compression, encryption, rate limiting, and caching as plugins
- **Extensible** — write custom plugins in C, Perl, Python, or OCaml
- **Used by libguestfs** — the core NBD engine behind virt tools
- **Part of libnbd ecosystem** — includes nbdcopy, nbdinfo, and other utilities
- **Red Hat maintained** — enterprise-grade stability and support

### Installation

```bash
# Install on Debian/Ubuntu
sudo apt install nbdkit nbdkit-plugin-*

# Install on RHEL/CentOS/Fedora
sudo dnf install nbdkit nbdkit-plugins
```

### Example: Export a QCOW2 Image

```bash
# Export a QCOW2 virtual disk image via NBD
nbdkit -n qcow2 file=/var/lib/libvirt/images/vm-disk.qcow2 \
  --run 'nbd-client $nbd 10809 /dev/nbd0'

# Export a remote HTTP file as a block device
nbdkit -n curl file=https://example.com/disk-image.img \
  --run 'nbd-client $nbd 10809 /dev/nbd0'

# Export with caching enabled
nbdkit -n file file=/srv/data.img \
  cache=true \
  --run 'nbd-client $nbd 10809 /dev/nbd0'
```

```yaml
# docker-compose.yml for nbdkit
services:
  nbdkit:
    image: libguestfs/nbdkit:latest
    container_name: nbdkit
    privileged: true
    ports:
      - "10809:10809"
    volumes:
      - /var/lib/libvirt/images:/images:ro
      - /srv/nbd:/data
    command: >
      -n file file=/data/disk.img
      --listen tcp:10809
    restart: unless-stopped
    networks:
      - storage-network

networks:
  storage-network:
    driver: bridge
```

## Comparison Table

| Feature | nbd-server | go-nbd | nbdkit |
|---------|-----------|--------|--------|
| **Language** | C | Go | C |
| **Primary Use** | Simple block device export | Lightweight single-binary NBD | Plugin-based NBD framework |
| **Package Availability** | All major distros | GitHub releases | All major distros |
| **Docker Image** | Community (trinitroglycerin) | GHCR (pojntfx) | libguestfs official |
| **TLS Encryption** | Yes | Via reverse proxy | Via plugin (tlsfilter) |
| **Access Control** | IP-based allowlist | None built-in | Via plugin |
| **Copy-on-Write** | Yes | No | Via cow plugin |
| **Plugin System** | No | No | 30+ plugins |
| **File Format Support** | Raw only | Raw only | Raw, QCOW2, VMDK, S3, HTTP |
| **Rate Limiting** | No | No | Via ratelimit plugin |
| **Compression** | No | No | Via xz/zstd plugins |
| **GitHub Stars** | 529 | 404 | Part of libnbd project |
| **Last Updated** | Active (2026-05) | 2024-07 | Active |

## Why Self-Host an NBD Server?

Self-hosting an NBD server gives you a lightweight, protocol-simple way to share block storage across your infrastructure. For homelab operators, NBD is an excellent way to centralize VM disk images — instead of storing identical base images on every KVM host, you keep them on a single NBD server and let each hypervisor mount them as read-only block devices.

The block-level nature of NBD opens use cases that file-sharing protocols cannot handle. You can use an NBD export as a swap device for diskless workstations, as a shared LVM physical volume for cluster management, or as the backing store for a DRBD replication setup. Linux's built-in NBD client means no additional software is needed on the consumer side — just the kernel module and the `nbd-client` utility.

In virtualization environments, NBD pairs well with libvirt and QEMU. QEMU can use NBD devices as backing stores for virtual machines, enabling live migration scenarios where the VM's disk remains on the NBD server while the compute moves between hosts. The libguestfs tool suite uses NBD internally for disk image inspection and modification, demonstrating how deeply integrated NBD is in the Linux virtualization stack.

For backup and disaster recovery, NBD provides a clean abstraction layer. You can attach an NBD device to a backup server, mount it read-only, and perform filesystem-level backups without interrupting the primary server. The copy-on-write mode in nbd-server allows you to create a writable overlay on top of a read-only production image — perfect for testing backups or running staging environments against production data snapshots.

Cost-wise, NBD is free and runs on commodity hardware. You do not need expensive SAN switches, Fibre Channel HBAs, or iSCSI-target-certified storage arrays. A standard Linux server with SATA or NVMe drives, running nbd-server, can serve block devices to dozens of clients over a standard 1 Gbps or 10 Gbps Ethernet connection.


## Why Self-Host Your Database Security and Routing Infrastructure?

For related storage solutions, see our [NFS vs Samba vs WebDAV file sharing comparison](../2026-04-24-samba-vs-nfs-vs-webdav-self-hosted-file-sharing-guide-2026/) for file-level alternatives to block-level NBD. Our [DRBD vs ZFS vs GlusterFS replication guide](../2026-05-08-self-hosted-storage-replication-drbd-zfs-glusterfs-georep-guide/) covers block-level replication that pairs well with NBD. For distributed filesystems, our [JuiceFS vs Alluxio vs CephFS comparison](../2026-04-28-juicefs-vs-alluxio-vs-cephfs-self-hosted-distributed-file-systems-2026/) explores higher-level storage options.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted NBD Server: Network Block Device Storage Solutions (2026)",
  "description": "Deploy NBD servers for self-hosted network block storage. Compare nbd-server, go-nbd, and nbdkit with Docker Compose configs and Linux kernel NBD client setup.",
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

## FAQ

### What is the difference between NBD and iSCSI?

Both NBD and iSCSI provide block-level storage over a network, but they differ in complexity and features. iSCSI implements the full SCSI command set, supporting advanced features like multi-path I/O, SCSI reservations, and target discovery protocols. NBD is much simpler — it provides basic read/write operations at the sector level. For most homelab and small business use cases, NBD is sufficient and easier to set up. iSCSI is better suited for enterprise SAN deployments that require SCSI-level features.

### Can I use NBD for live VM migration?

Yes. QEMU supports NBD as a backing store for virtual machine disks. During live migration, the VM's memory state transfers between hosts while the disk remains accessible via NBD. This is particularly useful when you want to migrate compute workloads without replicating large disk images between hypervisors. Configure QEMU with an NBD backing file: `qemu-system-x86_64 -drive file=nbd:192.168.1.100:10809,if=virtio`.

### Is NBD encrypted? Can I use it over the internet?

The NBD protocol itself does not include encryption. For internet-facing NBD servers, you should wrap the connection in TLS or a VPN tunnel. nbd-server has built-in TLS support (configure with `tls-certificates` in the config). nbdkit has a `tlsfilter` plugin that adds TLS encryption. Alternatively, run NBD over a WireGuard or OpenVPN tunnel for full network-layer encryption.

### How does NBD performance compare to local storage?

NBD performance depends primarily on network bandwidth and latency. On a 10 Gbps network with low latency, NBD can achieve throughput close to local SATA speeds (~500-600 MB/s sequential). On 1 Gbps networks, expect ~100-120 MB/s. Random I/O performance is more sensitive to latency than bandwidth — for high-IOPS workloads, consider using local storage or a faster network interconnect.

### Can multiple clients access the same NBD export simultaneously?

Yes, but with important caveats. If the export is read-only, multiple clients can safely connect simultaneously. For read-write exports, concurrent access requires a clustered filesystem (like OCFS2 or GFS2) on the NBD device to prevent data corruption. Without a cluster filesystem, simultaneous read-write access from multiple clients will corrupt the filesystem. Use read-only mode or a cluster-aware filesystem for shared access.

### How do I monitor NBD server performance?

For nbd-server, check the system logs (`journalctl -u nbd-server`) for connection events and errors. On the client side, use `iostat -x /dev/nbd0` to monitor I/O statistics, `nbd-client -c /dev/nbd0` to check connection status, and `cat /sys/block/nbd0/stat` for kernel-level block device statistics. For nbdkit, use the `--trace` flag to log all NBD protocol operations.

