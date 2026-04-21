---
title: "UrBackup vs BackupPC vs Bareos: Best Self-Hosted Backup Server 2026"
date: 2026-04-17
tags: ["comparison", "guide", "self-hosted", "backup", "disaster-recovery", "enterprise"]
draft: false
description: "Compare three powerful self-hosted backup server solutions: UrBackup, BackupPC, and Bareos. Learn which open-source backup platform fits your infrastructure with Docker setup guides, feature comparisons, and real-world deployment advice."
---

Every organization eventually faces the moment when a backup strategy stops being an abstract concern and becomes an urgent operational requirement. Whether it is a failed drive in a home lab, a ransomware incident at a small business, or a compliance audit demanding proof of recoverable archives, the question is always the same: can you get your data back?

Commercial backup services charge per-device licensing fees, per-gigabyte storage costs, and often require trusting a third party with your most sensitive data. The open-source alternative is to run your own backup server on-premises or on a private VPS, with complete control over retention policies, encryption keys, and storage backends.

This guide compares three of the most capable self-hosted backup server platforms available in 2026: **UrBackup**, **BackupPC**, and **Bareos**. Each takes a fundamentally different approach to the problem, and understanding those differences is the key to choosing the right one for your environment.

## Why Self-Host Your Backup Server

Running your own backup infrastructure instead of subscribing to a cloud backup service offers several concrete advantages:

**Complete data sovereignty.** Your backups never leave your hardware or your chosen cloud provider. There is no third-party vendor that can be subpoenaed, breached, or acquired. Encryption keys stay in your possession end to end.

**No per-device licensing.** Commercial backup platforms typically charge $5–50 per endpoint per month. With open-source server software, you pay only for the underlying storage. Backing up 50 laptops costs the same as backing up five.

**Flexible retention and scheduling.** You define exactly how many full and incremental backups to keep, which directories to exclude, and when backup windows open. No vendor-imposed retention caps or throttled restore speeds.

**Protocol independence.** Self-hosted backup servers typically support multiple protocols — SMB, NFS, rsync, raw block-level snapshots — so you are not locked into a proprietary agent or transfer format.

**Storage cost optimization.** You choose the storage backend: local RAID, NAS over NFS, S3-compatible object storage (like [MinIO](../minio-self-hosted-s3-object-storage-guide-2026/)), or even tape drives. This lets you tier cold archives to the cheapest medium available.

## UrBackup — Client/Server Backup Made Simple

**UrBackup** is an open-source client/server backup system designed for Windows, macOS, and Linux endpoints. It combines file-level and image-level backup in a single platform with a web-based management console. The project is hosted on GitHub under the `uroni` organization, with the server backend (`uroni/urbackup_backend`) carrying over 850 stars.

UrBackup's design philosophy is straightforward: install the client agent, point it at the server, and backups start flowing. There is minimal configuration required to get a working setup, which makes it particularly popular in small-to-medium business environments and home labs.

### Key Features

- **Image-level backups** for Windows (VSS-based) and Linux (via LVM snapshots), enabling bare-metal restores
- **File-level backups** with configurable include/exclude patterns per client
- **Incremental forever** strategy with synthesized full backups — only changed blocks are transmitted after the initial full backup
- **Integrated client management** — push client installations remotely, monitor backup health from the web UI
- **Native support for Windows VSS**, ensuring open files (databases, Outlook PST files) are captured consistently
- **Bandwidth throttling** and scheduled backup windows to avoid impacting production network usage
- **Change block tracking** on Windows for faster incremental image backups

### [docker](https://www.docker.com/) Deployment

UrBackup does not ship an official Docker image, but the LinuxServer.io community image is widely used and actively maintained:

```yaml
version: "3"
services:
  urbackup-server:
    image: lscr.io/linuxserver/urbackup-server:latest
    container_name: urbackup-server
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Etc/UTC
    volumes:
      - ./config:/config
      - ./backups:/backups
    ports:
      - 55413:55413    # Server UDP discovery
      - 55414:55414    # Client communication
      - 35623:35623    # Internet client communication
      - 55415:55415    # Web interface
    restart: unless-stopped
```

After starting the container, access the web interface at `http://<server-ip>:55415`. The default admin credentials are blank — set a password immediately in Settings > Users.

### Package Installation (Ubuntu/Debian)

For bare-metal or VM deployment without Docker:

```bash
# Add UrBackup PPA
sudo add-apt-repository ppa:uroni/urbackup
sudo apt update
sudo apt install urbackup-server

# Start and enable the service
sudo systemctl enable --now urbackupsrv

# Access web UI at http://<server-ip>:55414
```

Install clients on endpoints:

```bash
# On Ubuntu clients
sudo apt install urbackup-client

# On Windows, download the installer from urbackup.org
# On macOS, use the Homebrew formula or download the .dmg
```

### Strengths and Limitations

UrBackup excels at getting mixed-OS environments backed up quickly with minimal configuration. The image backup capability for Windows is genuinely valuable — it enables bare-metal restores to dissimilar hardware without requiring separate imaging software.

The primary limitation is storage efficiency. UrBackup uses hard-link-based deduplication for file backups, which works well on Linux filesystems but does not achieve the same compression ratios as block-level deduplication engines. Image backups are also not centrally deduplicated — each image is stored as a complete set of blocks.

## BackupPC — Enterprise-Grade Deduplication on a Budget

**BackupPC** is a Perl-based backup system that has been in active development since 2001. It lives on GitHub at `backuppc/backuppc` (1,592 stars, last updated December 2025). Despite its age, BackupPC remains one of the most storage-efficient backup solutions available, thanks to its pool-based deduplication architecture.

BackupPC operates in a pull model: the server initiates connections to clients using rsync, SMB, or tar over SSH. There is no persistent agent running on client machines, which simplifies deployment and reduces the attack surface on endpoints.

### Key Features

- **Pool-based deduplication** — identical files across all clients and all backup ages are stored exactly once, with hard links creating the per-backup directory structure
- **Multiple transport protocols** — rsync (recommended), SMB/CIFS, tar over SSH, and rsync over SSH
- **Browser-based interface** for browsing backup history, restoring individual files or entire directories, and monitoring backup status
- **Compression** — all stored data is compressed (configurable between gzip levels 1–9)
- **No client-side agent required** — backup is initiated by the server using existing system tools
- **Configurable per-client schedules**, retention policies, and backup types (full vs incremental)
- **Email notifications** on backup success, failure, and warning conditions

### Docker Deployment

A community-maintained Docker image is available from `ghcr.io/linuxserver/backuppc`:

```yaml
version: "3"
services:
  backuppc:
    image: lscr.io/linuxserver/backuppc:latest
    container_name: backuppc
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Etc/UTC
    volumes:
      - ./config:/config
      - ./data:/data
      - ./backups:/backups
    ports:
      - 8080:80        # Web interface
    restart: unless-stopped
```

To configure a client, edit the BackupPC host configuration file in `/config/backuppc/pc/<hostname>.pl` or use the web interface's Host Edit page. A minimal rsync configuration:

```perl
$Conf{RsyncShareName} = ['/home', '/etc', '/var/www'];
$Conf{XferMethod} = 'rsync';
$Conf{RsyncShareName} = ['/'];
$Conf{BackupFilesExclude} = {
    '/' => ['/proc', '/sys', '/dev', '/tmp', '/run'],
};
```

### Package Installation (Debian/Ubuntu)

```bash
sudo apt install backuppc

# The installer will prompt for web server configuration
# and the backuppc admin password

# Access the web interface at http://<server-ip>/backuppc
```

Configure SSH keys for passwordless access to clients:

```bash
# Switch to the backuppc user
sudo su - backuppc

# Generate an SSH key
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""

# Copy the public key to each client
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@client-host

# Test the connection
ssh -i ~/.ssh/id_ed25519 user@client-host "hostname"
```

### Strengths and Limitations

BackupPC's deduplication engine is its standout feature. In environments with many similar machines ([kubernetes](https://kubernetes.io/)ed workstations, Kubernetes nodes, container hosts), the storage savings are dramatic — often 80–95% reduction compared to storing each backup independently.

The limitations are equally clear. BackupPC requires a Linux server and can only back up Linux/Unix clients directly (Windows clients require Cygwin or SMB shares). The web interface, while functional, has not been redesigned in years and feels dated compared to modern dashboards. Configuration is primarily file-based rather than GUI-driven, which means reading documentation is necessary before deploying at scale.

## Bareos — The Bacula Fork for Enterprise Infrastructure

**Bareos** (Backup Archiving Recovery Open Sourced) is a fork of the Bacula project, created in 2010 when the original Bacula shifted to a more restrictive dual-license model. Bareos is licensed under AGPLv3 and hosted on GitHub at `bareos/bareos` (1,194 stars, actively maintained — last commit April 2026). It is written in C++ and represents the most enterprise-ready option in this comparison.

Bareos follows a director/storage daemon/client architecture that scales from single-server deployments to multi-site, multi-storage-backup infrastructures spanning thousands of endpoints. It supports tape libraries, disk storage, cloud object storage, and deduplication appliances through its modular storage daemon plugins.

### Key Features

- **Director/Storage/File daemon architecture** — clean separation of control plane, storage plane, and client agents enables horizontal scaling
- **Catalog database** — PostgreSQL or MySQL backend tracks every backed-up file, enabling fast searches and point-in-time restores
- **Tape library support** — autochanger, barcode reading, and tape pool management for long-term archival
- **Volume management** — automatic recycling of backup volumes based on retention rules
- **Deduplication plugin** — optional block-level deduplication via the Bareos dedup plugin (requires a dedup-capable storage backend)
- **Encryption** — AES-256 encryption for data in transit and at rest
- **ACL-based access control** — fine-grained permissions for operators, admins, and read-only users
- **Plugin system** — application-aware backup for PostgreSQL, MySQL, LDAP, and filesystems via VSS
- **Bconsole and WebUI** — both a command-line console and a modern web interface for management

### Docker Deployment

Bareos provides official Docker images. A minimal single-container deployment:

```yaml
version: "3"
services:
  bareos-dir:
    image: bareos/bareos-director:latest
    container_name: bareos-dir
    environment:
      - DB_HOST=bareos-db
      - DB_PASSWORD=bareos_secret
      - DB_USER=bareos
      - DB_NAME=bareos
    volumes:
      - ./director:/etc/bareos
    depends_on:
      - bareos-db
    ports:
      - 9101:9101
    restart: unless-stopped

  bareos-sd:
    image: bareos/bareos-storage:latest
    container_name: bareos-sd
    environment:
      - DIR_HOST=bareos-dir
    volumes:
      - ./storage:/etc/bareos
      - ./backup-data:/var/lib/bareos/storage
    ports:
      - 9103:9103
    depends_on:
      - bareos-dir
    restart: unless-stopped

  bareos-db:
    image: postgres:16-alpine
    container_name: bareos-db
    environment:
      - POSTGRES_PASSWORD=bareos_secret
      - POSTGRES_USER=bareos
      - POSTGRES_DB=bareos
    volumes:
      - ./postgres-data:/var/lib/postgresql/data
    restart: unless-stopped

  bareos-webui:
    image: bareos/bareos-webui:latest
    container_name: bareos-webui
    environment:
      - DIR_HOST=bareos-dir
    ports:
      - 8080:80
    depends_on:
      - bareos-dir
    restart: unless-stopped
```

### Package Installation (Debian/Ubuntu)

```bash
# Add Bareos repository
DIST=$(grep -E 'VERSION_CODENAME=' /etc/os-release | cut -d= -f2)
echo "deb https://download.bareos.org/bareos/release/$DIST/ /" > /etc/apt/sources.list.d/bareos.list
wget -qO- https://download.bareos.org/bareos/release/$DIST/Release.key | gpg --dearmor > /etc/apt/trusted.gpg.d/bareos.gpg
apt update

# Install components
apt install bareos bareos-database-postgresql

# Initialize the database
su - postgres -c "/usr/bin/bareos-dbconfig"

# Start services
systemctl enable --now bareos-dir bareos-sd bareos-fd

# Access WebUI at http://<server-ip>/bareos-webui
```

Configure a backup job by editing `/etc/bareos/bareos-dir.d/job/`:

```conf
Job {
  Name = "BackupClient1"
  JobDefs = "DefaultJob"
  Client = "client1-fd"
  FileSet = "FullSet"
  Schedule = "WeeklyCycle"
  Storage = "FileStorage"
  Pool = "Default"
}

FileSet {
  Name = "FullSet"
  Include {
    Options {
      signature = MD5
      compression = GZIP
    }
    File = /etc
    File = /home
    File = /var/www
  }
  Exclude {
    File = /proc
    File = /sys
    File = /tmp
  }
}
```

### Strengths and Limitations

Bareos is the most powerful and scalable option here. Its architecture supports enterprise features like multi-pool rotation (daily/weekly/monthly/yearly Grandfather-Father-Son schemes), tape library automation, and distributed storage daemons across multiple geographic sites. The PostgreSQL catalog enables instant file-level search across millions of backed-up files.

The trade-off is com[plex](https://www.plex.tv/)ity. Bareos has a steep learning curve — understanding the relationships between Jobs, FileSets, Clients, Storage Daemons, Pools, and Volumes requires studying the documentation. The initial configuration involves editing multiple files across multiple daemon directories. For a single-server home lab, this is almost certainly overkill. But for organizations managing hundreds of endpoints with strict RPO and RTO requirements, Bareos is the tool designed for that job.

## Head-to-Head Comparison

| Feature | UrBackup | BackupPC | Bareos |
|---------|----------|----------|--------|
| **Primary Language** | C++ | Perl | C++ |
| **License** | AGPLv3 / MPLv2 | GPL-2.0 | AGPLv3 |
| **Architecture** | Client/Server | Pull-based (agentless) | Director/Storage/File Daemon |
| **Windows Support** | Native agent (VSS) | SMB/CIFS or Cygwin | Native agent (VSS plugin) |
| **macOS Support** | Native client | No native support | Limited (tar over SSH) |
| **Linux Support** | Native client | rsync/SSH (agentless) | Native client |
| **Image/Block Backup** | Yes (Windows + Linux LVM) | No (file-level only) | Plugin-based |
| **Deduplication** | Hard-link (file-level) | Pool-based (file-level) | Plugin (block-level) |
| **Encryption** | TLS for client comms | No built-in (SSH tunnel) | AES-256 at rest and transit |
| **Web Interface** | Built-in admin console | Built-in (CGI-based) | WebUI (PHP-based) |
| **Tape Support** | No | No | Full (autochanger, barcodes) |
| **Catalog Database** | SQLite/MySQL | Flat files | PostgreSQL/MySQL |
| **Cloud Storage** | No native support | Via rsync to cloud mount | S3-compatible plugin |
| **Scalability** | ~200 clients/server | ~100 clients/server | 1000+ clients (distributed) |
| **Learning Curve** | Low | Medium | High |
| **Best For** | SMBs, home labs, mixed OS | Linux/Unix environments, budget-conscious | Enterprise, compliance, tape archival |

## Choosing the Right Backup Server for Your Environment

The choice between these three platforms comes down to three factors: **environment complexity**, **storage constraints**, and **operational expertise**.

**Choose UrBackup if** you need a working backup system within an hour. It handles Windows image backups better than either alternative, the web UI is intuitive enough for non-technical administrators, and the hard-link deduplication provides good storage efficiency without requiring a catalog database. For a home lab, small office, or MSP managing diverse client environments, UrBackup is the fastest path to reliable backups.

**Choose BackupPC if** storage cost is your primary constraint and your environment is predominantly Linux/Unix. The pool-based deduplication is unmatched for file-level backups — environments with many similar machines see dramatic storage savings. The lack of a native Windows agent is a significant limitation for mixed environments, but for backing up a fleet of Linux servers or workstations, BackupPC delivers exceptional efficiency with minimal resource overhead.

**Choose Bareos if** you have enterprise requirements: compliance audits, tape archival, multi-site disaster recovery, or hundreds of endpoints. The Director/Storage/File daemon architecture scales horizontally, the PostgreSQL catalog enables instant file search, and the plugin ecosystem covers application-aware backups for databases and directory services. The investment in learning the configuration model pays off when you need to restore a specific file from six months ago across 500 servers in under 15 minutes.

### Complementary Approaches

These server-based solutions are not mutually exclusive with the client-side tools covered in our [Restic vs Borg vs Kopia comparison](../restic-vs-borg-vs-kopia-backup-guide/). A common pattern is to use UrBackup or BackupPC as the primary on-premises backup server while also running Restic or Borg on critical servers to push encrypted offsite copies to an S3-compatible backend like [MinIO](../minio-self-hosted-s3-object-storage-guide-2026/) or cloud storage. This 3-2-1 strategy (three copies, two media types, one offsite) provides defense against both local hardware failure and site-level disasters.

## FAQ

### Can UrBackup back up headless Linux servers without a GUI?

Yes. The UrBackup Linux client runs as a systemd service with no graphical dependency. Install it via `apt install urbackup-client` or compile from source, then configure the server address in `/etc/default/urbackupclient`. The client communicates with the server over TCP and requires no user interaction after initial setup.

### Does BackupPC support incremental backups for Windows clients?

BackupPC can back up Windows clients via SMB/CIFS shares or by installing Cygwin with rsync. However, neither method provides true block-level incrementals like UrBackup's VSS integration. SMB-based backups enumerate all files and compare against the pool, which is slower than rsync's delta transfer. For Windows-heavy environments, UrBackup or Bareos are better choices.

### How does Bareos handle tape library rotation?

Bareos supports automated tape rotation through its Volume management system. You define Pools (Daily, Weekly, Monthly) with different retention periods, and Bareos automatically recycles volumes when their retention expires. With an autochanger configured, the Storage Daemon handles loading and unloading tapes based on barcode labels. The `label` and `mount` commands in bconsole allow manual intervention when needed.

### Can I use object storage (S3, Backblaze B2) as a backup target?

Bareos supports S3-compatible storage through its cloud storage plugin. UrBackup does not natively support object storage but can back up to a directory that is synced to S3 via rclone. BackupPC can store its pool on a cloud-mounted filesystem (s3fs, goofys) but this is not officially supported and may impact deduplication performance. For a purpose-built S3 storage backend, consider deploying [MinIO](../minio-self-hosted-s3-object-storage-guide-2026/) as an on-premises S3 target.

### What is the minimum hardware requirement for each platform?

**UrBackup**: 2 CPU cores, 2 GB RAM, and storage sized for your backup retention (typically 2–3x the total data size for file-level backups). **BackupPC**: 1 CPU core, 1 GB RAM, and storage for the pool (often less than the total data size due to deduplication). **Bareos**: 2 CPU cores, 4 GB RAM (more for the PostgreSQL catalog with large client counts), and storage for volumes plus the catalog database. All three can run on a single $5–10/month VPS for small deployments.

### How do these tools handle ransomware protection?

None of the three platforms provide built-in immutable or WORM (Write Once, Read Many) storage. The standard approach is to use a separate storage backend that supports object lock (S3 Object Lock on MinIO or compatible providers) or to maintain an air-gapped offline copy. Bareos can write to tape, which provides natural immutability once ejected. For additional hardening, restrict backup server access via firewall rules and use encrypted client-server communication. If you are building a broader security posture, our [self-hosted vulnerability scanning guide](../openvas-trivy-grype-self-hosted-vulnerability-scanner-guide/) covers tools for detecting compromised systems before they infect your backups.

### Is there a migration path between these platforms?

Migration is not seamless due to different storage formats. The most practical approach is to restore from the old system and re-backup into the new one. For Bareos, the `bextract` command can restore files to a temporary location for re-ingestion. BackupPC's `BackupPC_restore` script handles restores, and UrBackup supports restoring individual files or full images from the web UI. Plan for a parallel run period where both systems back up the same clients to verify the new platform works correctly before decommissioning the old one.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "UrBackup vs BackupPC vs Bareos: Best Self-Hosted Backup Server 2026",
  "description": "Compare three powerful self-hosted backup server solutions: UrBackup, BackupPC, and Bareos. Learn which open-source backup platform fits your infrastructure with Docker setup guides, feature comparisons, and real-world deployment advice.",
  "datePublished": "2026-04-17",
  "dateModified": "2026-04-17",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>
