---
title: "Self-Hosted Union File Systems — SnapRAID vs MergerFS vs UnionFS-Fuse Guide 2026"
date: "2026-05-08"
tags: ["comparison", "guide", "self-hosted", "storage", "filesystem", "nas"]
draft: false
description: "Compare self-hosted union file system solutions — SnapRAID, MergerFS, and UnionFS-Fuse. Complete guide with Docker deployment, parity configuration, pooling strategies, and best practices for building a flexible home NAS."
---

Modern storage management often requires combining multiple drives of different sizes, speeds, and purposes into a single coherent view. Whether you are building a home NAS, managing a media server, or organizing backup volumes, **union file systems** provide the flexibility to pool heterogeneous storage without the rigidity of traditional RAID.

This guide compares three leading open-source approaches to union storage: **[SnapRAID](https://github.com/amadvance/snapraid)** (2,479 stars), **[MergerFS](https://github.com/trapexit/mergerfs)** (5,616 stars), and **[UnionFS-Fuse](https://github.com/rpodgorny/unionfs-fuse)** (366 stars). We cover deployment strategies, parity configuration, pooling policies, and Docker integration so you can build the storage layer that fits your infrastructure.

## What Are Union File Systems?

A union file system overlays multiple directories (potentially on different physical drives) into a single mount point. Unlike traditional RAID, which requires identical drives and dedicates capacity to parity, union file systems let you:

- **Pool drives of different sizes** — mix 4 TB, 8 TB, and 16 TB drives without wasted space
- **Add or remove drives on the fly** — no rebuild process, no waiting for resync
- **Choose pooling policies** — control which drive receives new writes (most free space, first available, round-robin)
- **Separate parity from data** — SnapRAID stores parity on dedicated drives, protecting against disk failure without locking your array

Traditional RAID (mdadm, ZFS, Btrfs RAID) offers strong data integrity but at the cost of flexibility. Union file systems trade some of that rigidity for operational simplicity and heterogeneous drive support.

## SnapRAID: Parity-Based Protection

SnapRAID is a user-space parity tool inspired by hardware RAID5/6. It computes parity files across a set of data drives and can reconstruct data from a single failed drive (or two, with dual parity).

**Key characteristics:**
- Runs as a scheduled task, not in real-time — parity is computed when you run `snapraid sync`
- Supports up to 6 parity drives (RAID6 equivalent with dual parity, up to RAID13 with six)
- Works with any filesystem underneath (ext4, XFS, Btrfs, NTFS)
- Does NOT protect against simultaneous multi-drive failure beyond your parity count
- Ideal for **cold storage**, media libraries, and archives where data is written once and read often

### SnapRAID Docker Deployment

SnapRAID does not have an official Docker image, but LinuxServer.io provides a community container and you can run it in a privileged container with host drive mounts:

```yaml
version: "3.8"
services:
  snapraid:
    image: lscr.io/linuxserver/snapraid:latest
    container_name: snapraid
    privileged: true
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Etc/UTC
    volumes:
      - /path/to/snapraid-config:/config
      - /srv/disk1:/disk1
      - /srv/disk2:/disk2
      - /srv/disk3:/disk3
      - /srv/parity1:/parity
    restart: unless-stopped
```

**SnapRAID configuration** (`/config/snapraid.conf`):

```ini
# Parity drive
parity /parity/snapraid.parity

# Data drives
disk1 /disk1
disk2 /disk2
disk3 /disk3

# Excluded paths
exclude *.unrecoverable
exclude /disk*/tmp/
exclude /disk*/downloads/*.part

# Hash algorithm (blake3 is fastest, md5 is most compatible)
hashblake3 on
```

**Running a sync:**

```bash
# Check current status
snapraid status

# Simulate a sync (dry run)
snapraid -n sync

# Execute parity sync
snapraid sync

# Scrub for bit-rot detection (run monthly)
snapraid scrub -p 20
```

## MergerFS: Real-Time Drive Pooling

MergerFS is a FUSE-based union filesystem that creates a pooled view of multiple directories in **real time**. Unlike SnapRAID, it does not provide parity — it focuses on flexible write policies and a unified namespace.

**Key characteristics:**
- Real-time file operations — reads and writes go directly to underlying drives
- Rich policy engine: `epmfs` (existing path with most free space), `mfs` (most free space), `ff` (first found), `rand` (random)
- Supports hard links, extended attributes, and POSIX permissions
- Can be combined with SnapRAID: MergerFS pools drives for writes, SnapRAID provides parity protection
- Ideal for **active storage**, download directories, and media servers

### MergerFS Docker Deployment

MergerFS can be deployed in a privileged container with FUSE support:

```yaml
version: "3.8"
services:
  mergerfs:
    image: ubuntu:24.04
    container_name: mergerfs
    privileged: true
    cap_add:
      - SYS_ADMIN
    devices:
      - /dev/fuse:/dev/fuse
    security_opt:
      - apparmor:unconfined
    environment:
      - TZ=Etc/UTC
    volumes:
      - /srv/disk1:/disk1:shared
      - /srv/disk2:/disk2:shared
      - /srv/disk3:/disk3:shared
      - /srv/pool:/pool:shared
    entrypoint: ["/bin/bash", "-c"]
    command:
      - |
        apt-get update && apt-get install -y mergerfs fuse3
        mergerfs -o defaults,allow_other,category.create=epmfs,minfreespace=50G \
          /disk1:/disk2:/disk3 /pool
        tail -f /dev/null
    restart: unless-stopped
```

**Direct host installation** (recommended for production):

```bash
# Ubuntu/Debian
sudo apt install mergerfs

# Mount via fstab
/srv/disk1:/srv/disk2:/srv/disk3  /srv/pool  fuse.mergerfs  defaults,allow_other,category.create=epmfs,minfreespace=50G,fsname=mergerfsPool  0 0
```

**Useful MergerFS policies:**
- `category.create=epmfs` — write to drive with most free space that already has the file's directory
- `category.create=mfs` — write to drive with most free space
- `category.create=ff` — write to first drive with enough space
- `cache.files=partial` — cache read operations for better performance

## UnionFS-Fuse: Layered Read/Write Overlay

UnionFS-Fuse is a FUSE implementation of the UnionFS concept, designed to **overlay a read-write branch on top of read-only branches**. This is commonly used for:

- Creating writable overlays on read-only filesystems (Live CD environments)
- Combining a fast SSD cache layer with slower HDD storage
- Testing environments where changes should be discardable

**Key characteristics:**
- Supports `COW` (copy-on-write) semantics — writes to read-only branches are redirected to the RW branch
- Simpler feature set than MergerFS — no policy engine for write distribution
- Best suited for **overlay scenarios** rather than drive pooling
- 366 stars, actively maintained but smaller community than MergerFS

### UnionFS-Fuse Docker Deployment

```yaml
version: "3.8"
services:
  unionfs:
    image: ubuntu:24.04
    container_name: unionfs
    privileged: true
    cap_add:
      - SYS_ADMIN
    devices:
      - /dev/fuse:/dev/fuse
    security_opt:
      - apparmor:unconfined
    environment:
      - TZ=Etc/UTC
    volumes:
      - /srv/ro-layer:/ro:ro
      - /srv/rw-layer:/rw
      - /srv/merged:/merged:shared
    entrypoint: ["/bin/bash", "-c"]
    command:
      - |
        apt-get update && apt-get install -y unionfs-fuse fuse3
        unionfs-fuse -o allow_other,cow /rw=RW:/ro=RO /merged
        tail -f /dev/null
    restart: unless-stopped
```

**Direct host installation:**

```bash
# Ubuntu/Debian
sudo apt install unionfs-fuse

# Mount a read-write overlay on a read-only source
sudo unionfs-fuse -o allow_other,cow /writable=RW:/readonly=RO /merged
```

## Comparison: SnapRAID vs MergerFS vs UnionFS-Fuse

| Feature | SnapRAID | MergerFS | UnionFS-Fuse |
|---|---|---|---|
| **Stars** | 2,479 | 5,616 | 366 |
| **Language** | C | C++ | C |
| **Primary purpose** | Parity protection | Drive pooling | RW overlay on RO |
| **Real-time** | No (scheduled sync) | Yes | Yes |
| **Parity/RAID** | Yes (up to 6 parity) | No | No |
| **Write policies** | N/A | epmfs, mfs, ff, rand, lfs | COW only |
| **Hot-add drives** | Yes (add, then sync) | Yes (instant) | Yes (remount) |
| **Filesystem agnostic** | Yes | Yes | Yes |
| **Bit-rot detection** | Yes (scrub) | No | No |
| **Docker deployment** | Community image (LSIO) | Privileged container | Privileged container |
| **Best use case** | Archive/media library | Active storage pool | Read-only overlay |

## Recommended Architecture: Combining SnapRAID + MergerFS

The most popular self-hosted storage setup combines both tools:

1. **MergerFS** pools all data drives into a single mount point (`/srv/pool`) for real-time read/write access
2. **SnapRAID** runs on a cron schedule (every 6 hours) to compute parity from the pooled data
3. New files land on the drive with most free space (MergerFS `epmfs` policy)
4. If a drive fails, SnapRAID reconstructs the lost data from parity

```bash
# Cron entry for SnapRAID sync every 6 hours
0 */6 * * * /usr/bin/snapraid sync -l /var/log/snapraid.log

# Monthly scrub for bit-rot detection
0 3 1 * * /usr/bin/snapraid scrub -p 30 -l /var/log/snapraid-scrub.log
```

## Why Self-Host Your Storage Pool?

Commercial NAS devices from Synology and QNAP offer polished interfaces but come with hardware lock-in, limited upgrade paths, and premium pricing. Building your own storage pool with open-source tools gives you:

**Complete hardware freedom** — use any combination of drives, controllers, and chassis. Mix enterprise SAS drives with consumer SATA drives. Add NVMe cache when needed. Upgrade one drive at a time without replacing the entire array.

**No vendor lock-in** — your data lives on standard filesystems (ext4, XFS). If your software stack fails, you can mount any individual drive on any Linux system and read the data directly. Proprietary RAID formats often require the original controller or software to recover.

**Cost efficiency** — a used server chassis with 12 drive bays costs less than a 4-bay NAS. Drives are the biggest expense, and buying used enterprise drives (with proper health checks) cuts costs by 50-70%.

**Data sovereignty** — parity data never leaves your network. Cloud backup services require uploading your entire library, which is impractical for multi-terabyte collections. SnapRAID parity stays local.

For decentralized storage alternatives, see our [IPFS vs Storj vs Sia comparison](../2026-04-25-ipfs-vs-storj-vs-sia-self-hosted-decentralized-storage-guide-2026/). For S3-compatible object storage, check our [MinIO vs SeaweedFS vs Garage guide](../2026-05-03-self-hosted-s3-object-storage-minio-seaweedfs-garage-guide/). If you need NFS sharing for your pooled storage, our [NFS server guide](../2026-04-30-nfs-ganesha-vs-unfs3-vs-kernel-nfs-self-hosted-nfs-server-guide/) covers deployment options.

## FAQ

### What is the difference between SnapRAID and traditional RAID?
SnapRAID computes parity on a scheduled basis (not in real-time), so there is a window between writes and parity updates where data is unprotected. Traditional RAID (mdadm, ZFS) protects data instantly. However, SnapRAID works with any filesystem, supports heterogeneous drives, and does not require rebuilding the entire array when a drive fails — you simply restore the affected files from parity.

### Can I use SnapRAID and MergerFS together?
Yes, this is the recommended setup. MergerFS creates a pooled view of all your data drives for real-time access, while SnapRAID periodically computes parity across those same drives. The combination gives you the flexibility of pooling with the safety of parity protection.

### How many parity drives does SnapRAID support?
SnapRAID supports up to 6 parity drives. With 1 parity drive, you can survive a single disk failure (RAID5 equivalent). With 2 parity drives, you can survive 2 simultaneous failures (RAID6 equivalent). Additional parity drives provide further protection at the cost of storage capacity.

### Does MergerFS provide any data protection?
No. MergerFS is purely a pooling tool — it provides no redundancy, parity, or backup functionality. If a drive in a MergerFS pool fails, files stored on that drive are lost. Combine MergerFS with SnapRAID or a separate backup solution for data protection.

### Can I add a new drive to an existing SnapRAID array?
Yes. Add the new drive to your `snapraid.conf` file, then run `snapraid sync`. The new drive will be included in the next parity calculation. No data migration or array rebuild is required.

### Is UnionFS-Fuse suitable for a home NAS?
UnionFS-Fuse is better suited for overlay scenarios (e.g., writable layer on read-only media) than for general NAS drive pooling. For NAS use, MergerFS (pooling) combined with SnapRAID (parity) is the more feature-complete solution. UnionFS-Fuse shines in Live CD environments and container base image layering.

## Choosing the Right Union File System

**Choose SnapRAID if:** You need parity protection for large, mostly-static datasets (media libraries, archives). Your data is written infrequently and you can tolerate running sync on a schedule.

**Choose MergerFS if:** You need real-time drive pooling with flexible write policies. You have drives of different sizes and want to maximize usable capacity without wasting space on parity.

**Choose UnionFS-Fuse if:** You need a read-write overlay on top of read-only storage. You are building a Live CD environment or need COW semantics for testing.

**Choose SnapRAID + MergerFS if:** You want the best of both worlds — real-time pooling with scheduled parity protection. This is the most popular combination in the self-hosted community and the recommended architecture for home NAS builds.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Union File Systems — SnapRAID vs MergerFS vs UnionFS-Fuse Guide 2026",
  "description": "Compare self-hosted union file system solutions — SnapRAID, MergerFS, and UnionFS-Fuse. Complete guide with Docker deployment, parity configuration, pooling strategies, and best practices for building a flexible home NAS.",
  "datePublished": "2026-05-08",
  "dateModified": "2026-05-08",
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
