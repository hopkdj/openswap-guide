---
title: "Self-Hosted Tape Backup & Archival: Bacula vs Bareos vs Amanda"
date: "2026-06-02"
tags: ["backup", "tape", "bacula", "bareos", "amanda", "archival", "self-hosted", "disaster-recovery", "comparison", "ltfs", "storage"]
draft: false
---

## Introduction

Despite the dominance of cloud storage and disk-based backups, tape remains the most cost-effective medium for long-term data archival. LTO-9 tapes store 18TB (native) per cartridge at roughly $5/TB — a fraction of cloud archival storage costs over a 5-10 year retention period. For organizations with compliance requirements, tape provides immutable, air-gapped protection that no online system can match.

Three open-source solutions have dominated the self-hosted tape backup landscape for decades: **Bacula**, the enterprise-grade network backup platform; **Bareos**, its actively maintained fork; and **Amanda**, the veteran network backup tool trusted since 1991. Each takes a different approach to managing tape libraries, scheduling backups, and handling recovery.

This guide compares Bacula, Bareos, and Amanda for self-hosted tape backup, with configuration examples and best practices for LTO tape library management.

## Why Tape Backup Still Matters

Cloud storage is convenient but expensive at scale. Storing 100TB in AWS S3 Glacier Deep Archive costs approximately $100/month, or $12,000 over 10 years. The same data on 6 LTO-9 tapes costs roughly $600 in media — a 20x savings. Tape also provides:

- **Air-gapped security**: Tapes stored offline are immune to ransomware, accidental deletion, and API key compromises
- **Regulatory compliance**: Many regulations (HIPAA, FINRA, SEC) require offline backups with documented chain of custody
- **Energy efficiency**: Tapes consume zero power when shelved, unlike spinning disks
- **Longevity**: LTO tapes are rated for 30 years of archival storage under proper conditions

Modern LTO drives connect via SAS or Fibre Channel, and tape libraries can hold dozens of tapes with robotic autoloaders — making them fully automatable with the right software.

## Solution Comparison

### Bacula

Bacula is the most feature-rich enterprise backup solution in the open-source world. It uses a modular architecture with five distinct components: Director (scheduler), Storage Daemon (media manager), File Daemon (client agent), Catalog (database), and Console (management interface).

**Key features:**
- Client-server architecture with TLS encryption
- Supports tape libraries with barcode readers and autoloaders
- MySQL/PostgreSQL catalog for tracking all backups
- Job scheduling with priority levels and resource limits
- Web-based management GUI (Baculum)
- Cross-platform clients (Linux, Windows, macOS)

**Docker Compose deployment:**

```yaml
version: "3.8"
services:
  bacula-db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: bacula
      POSTGRES_USER: bacula
      POSTGRES_PASSWORD: bacula_secret
    volumes:
      - bacula_db:/var/lib/postgresql/data

  bacula-dir:
    image: baculacommunity/bacula-dir:latest
    depends_on:
      - bacula-db
    environment:
      DB_HOST: bacula-db
      DB_NAME: bacula
      DB_USER: bacula
      DB_PASSWORD: bacula_secret
    volumes:
      - ./bacula-dir.conf:/etc/bacula/bacula-dir.conf:ro
    ports:
      - "9101:9101"

  bacula-sd:
    image: baculacommunity/bacula-sd:latest
    devices:
      - /dev/nst0:/dev/nst0  # Tape drive
    volumes:
      - ./bacula-sd.conf:/etc/bacula/bacula-sd.conf:ro
    ports:
      - "9103:9103"

  bacula-fd:
    image: baculacommunity/bacula-fd:latest
    volumes:
      - /:/mnt/host:ro  # Read-only access to host for backup
    ports:
      - "9102:9102"

volumes:
  bacula_db:
```

### Bareos

Bareos (Backup Archiving Recovery Open Sourced) forked from Bacula in 2010 and has since diverged significantly. It maintains Bacula's modular architecture while adding modern features like NDMP support, S3-compatible storage backends, and a refreshed web UI.

**Key features:**
- Active fork with 1,211+ GitHub stars
- Modern web UI with drag-and-drop restore
- S3-compatible cloud storage as backup destination
- VMware vSphere plugin for VM-level backups
- NDMP support for NAS backup
- Role-based access control (RBAC)

**Docker Compose deployment:**

```yaml
version: "3.8"
services:
  bareos-db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: bareos
      POSTGRES_USER: bareos
      POSTGRES_PASSWORD: bareos_secret
    volumes:
      - bareos_db:/var/lib/postgresql/data

  bareos-director:
    image: bareos/bareos-director:latest
    depends_on:
      - bareos-db
    environment:
      DB_HOST: bareos-db
      DB_NAME: bareos
      DB_USER: bareos
      DB_PASSWORD: bareos_secret
    volumes:
      - ./bareos-dir.conf:/etc/bareos/bareos-dir.conf:ro
    ports:
      - "9101:9101"

  bareos-storage:
    image: bareos/bareos-storage:latest
    devices:
      - /dev/nst0:/dev/nst0
    volumes:
      - ./bareos-sd.conf:/etc/bareos/bareos-sd.conf:ro
    ports:
      - "9103:9103"

  bareos-webui:
    image: bareos/bareos-webui:latest
    ports:
      - "8080:80"

volumes:
  bareos_db:
```

Bareos tape device configuration example (`bareos-sd.conf`):

```
Device {
  Name = LTO-9-Drive
  Media Type = LTO-9
  Archive Device = /dev/nst0
  AutomaticMount = yes
  AlwaysOpen = yes
  RemovableMedia = yes
  RandomAccess = no
  AutoChanger = yes
  DriveIndex = 0
  MaximumBlockSize = 2097152
  MaximumFileSize = 10GB
}
```

### Amanda

Amanda (Advanced Maryland Automatic Network Disk Archiver) has been backing up data since 1991. Unlike Bacula/Bareos, Amanda uses a simpler architecture — a single server process that schedules and executes backups to tape, disk, or cloud storage.

**Key features:**
- Simple configuration: one config file per backup set
- Native tape changer and library support
- Supports disk, tape, and cloud (S3) backup destinations
- Client-side compression and encryption
- Automatic tape labeling and pool management
- Built-in vaulting for offsite rotation

**Docker Compose deployment:**

```yaml
version: "3.8"
services:
  amanda:
    image: zmanda/amanda:latest
    devices:
      - /dev/nst0:/dev/nst0
      - /dev/sg0:/dev/sg0  # Tape changer
    volumes:
      - ./amanda-config:/etc/amanda
      - /backup/vtl:/backup/vtl  # Virtual tape library storage
    environment:
      TAPE_DEVICE: /dev/nst0
      CHANGER_DEVICE: /dev/sg0
    network_mode: host
```

Amanda tape configuration (`amanda.conf`):

```
org "DailySet1"
dumpuser "amandabackup"

tpchanger "chg-zd-mtx"
changerfile "/etc/amanda/DailySet1/changer.conf"
tapedev "/dev/nst0"

tapetype LTO-9
define tapetype LTO-9 {
    length 17179869184 kbytes
    filemark 4096 kbytes
    speed 393216 kbytes
    blocksize 256 kbytes
}

holdingdisk hd1 {
    directory "/backup/vtl/holding"
    use 50 GB
}
```

## Comparison Table

| Feature | Bacula | Bareos | Amanda |
|---------|--------|--------|--------|
| Architecture | Modular (5 daemons) | Modular (Bacula fork) | Monolithic server |
| GitHub Stars | N/A (SourceForge) | 1,211 | N/A (legacy) |
| Web UI | Baculum (community) | Modern web UI | Zmanda Management Console |
| Database Catalog | MySQL/PostgreSQL | PostgreSQL | None (file-based) |
| Tape Library Support | Full (barcodes, autoloaders) | Full + NDMP | Full (changer scripts) |
| Cloud Storage Target | Via S3 plugin | Native S3 backend | Via S3 device |
| Encryption | TLS + PKI | TLS + PKI | GPG/OpenSSL |
| Learning Curve | Steep | Moderate | Gentle |
| Best For | Large enterprises | Modern deployments | Simple LAN backups |

## Why Self-Host Your Tape Backup Infrastructure?

Self-hosting tape backup gives you complete control over your data's physical location and retention policies. Unlike cloud backup services where you're trusting a third party with your encryption keys and data sovereignty, on-premises tape backup keeps everything within your infrastructure. For organizations in healthcare, finance, legal, or government sectors, this is often a non-negotiable requirement.

The cost advantage compounds over time. A single LTO-9 tape drive costs approximately $3,000-5,000 — expensive upfront, but it reads and writes to $100 cartridges indefinitely. Compare this to cloud archival storage: storing 50TB for 7 years costs roughly $4,200 in tape media vs $42,000 in AWS Glacier Deep Archive (plus retrieval fees). Every additional year widens the gap.

From a disaster recovery perspective, tape provides the ultimate air gap. Ransomware cannot encrypt tapes sitting on a shelf. Accidental `rm -rf` cannot reach offline media. A backup server compromise cannot propagate to disconnected tapes. The 3-2-1 backup rule (3 copies, 2 media types, 1 offsite) is trivially satisfied when tape is part of your strategy: one copy disk (fast recovery), one copy tape (air-gapped), one copy offsite tape (disaster recovery).

Modern tape automation also eliminates manual intervention. Autoloaders with barcode readers let Bacula and Bareos automatically select the correct tape, verify labels, and rotate media pools — no operator needed.

For more backup strategies, read our [encrypted backup tools comparison](../2026-04-22-duplicati-vs-duplicacy-vs-duplicity-self-hosted-encrypted-backup-2026/) and our [backup integrity verification guide](../2026-05-11-backup-integrity-verification-restic-borg-borgmatic/). For general-purpose backup servers (not tape-specific), see our [self-hosted backup server comparison](../urbackup-vs-backuppc-vs-bareos-self-hosted-backup-server-guide-2026/).

## FAQ

### Is tape backup still relevant in 2026?

Absolutely. LTO-9 offers 18TB native capacity per cartridge at a media cost of roughly $5/TB — far cheaper than cloud archival storage for long retention. Tape is the standard for industries with regulatory retention requirements (healthcare, finance, media & entertainment archives). Combined with disk-to-disk-to-tape (D2D2T) strategies, tape provides the most cost-effective tier in a comprehensive backup architecture.

### Which is easier: Bacula, Bareos, or Amanda?

Amanda is the easiest to set up — a single configuration file and a few client installs is all you need. Bareos strikes the best balance between features and usability, with a modern web UI and good documentation. Bacula offers the most power but has the steepest learning curve — its five-daemon architecture requires understanding how Director, SD, FD, Catalog, and Console interact.

### Can I use a virtual tape library (VTL) for testing?

Yes. Tools like `mhvtl` (Linux Virtual Tape Library) emulate LTO drives and libraries for testing without physical hardware. They present virtual SCSI devices that tape backup software treats as real tape drives. This is ideal for testing configurations before deploying to production hardware.

```bash
# Install mhvtl
apt install mhvtl-utils
systemctl start mhvtl

# Check virtual devices
ls /dev/nst* /dev/sg*
```

### How do I rotate tapes for offsite storage?

All three solutions support media pools and vaulting. With Bacula, you define a `Pool` with a `VolumeRetention` period and use the `update slots` command to move tapes between library slots. Bareos supports an `Autochanger` resource with automatic tape rotation. Amanda's `taper` process automatically labels and rotates tapes based on your `tapecycle` configuration.

### Does LTFS (Linear Tape File System) work with these tools?

LTFS presents a tape as a mountable filesystem, making it accessible like a USB drive. While Bacula, Bareos, and Amanda use their own tape formats (not LTFS), you can use LTFS alongside them for simple drag-and-drop archival. For programmatic tape access with LTFS:

```bash
# Format and mount an LTFS tape
mkltfs --device=/dev/nst0
mount -t ltfs /dev/nst0 /mnt/tape

# Copy files directly
cp -a /important/data /mnt/tape/

# Unmount
umount /mnt/tape
```

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Tape Backup & Archival: Bacula vs Bareos vs Amanda",
  "description": "Compare Bacula, Bareos, and Amanda for self-hosted tape backup and archival. Includes Docker Compose configs, LTO tape library setup, and LTFS integration.",
  "datePublished": "2026-06-02",
  "dateModified": "2026-06-02",
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

---

**💡 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到 技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测 科技相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
