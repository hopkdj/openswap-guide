---
title: "Duplicati vs Duplicacy vs Duplicity: Self-Hosted Encrypted Backup Tools Compared 2026"
date: 2026-04-22
tags: ["comparison", "guide", "self-hosted", "backup", "privacy", "data-protection"]
draft: false
description: "Compare Duplicati, Duplicacy, and Duplicity — three open-source encrypted backup solutions for self-hosted servers. Includes Docker Compose configs, storage backends, and performance benchmarks."
---

Every self-hosted server needs a reliable backup strategy. Whether you're protecting home lab data, business-critical files, or personal documents, having encrypted backups stored off-site is non-negotiable. Three established open-source tools dominate this space: **Duplicati**, **Duplicacy**, and **Duplicity**. Each takes a fundamentally different approach to encrypted backup, and choosing the right one depends on your storage backend, performance needs, and operational preferences.

In this guide, we'll compare all three tools side by side — covering architecture, supported backends, Docker deployment, deduplication strategies, and real-world performance — so you can pick the best fit for your infrastructure. For a broader look at backup tooling, see our [Restic vs Borg vs Kopia comparison](../restic-vs-borg-vs-kopia-backup-guide/) and [backup verification and integrity testing guide](../2026-04-19-self-hosted-backup-verification-testing-integrity-guide/).

## Why Self-Host Your Backup Software

Using a cloud-based backup SaaS means trusting a third party with your encryption keys, backup schedules, and metadata. Self-hosted backup tools give you:

- **End-to-end encryption** — your data is encrypted locally before it ever leaves your network
- **Zero vendor lock-in** — all three tools support open backup formats and standard protocols (S3, SFTP, WebDAV)
- **Full control over scheduling and retention** — set your own backup windows, frequency, and lifecycle policies
- **No subscription costs** — all three tools are free and open-source
- **Auditability** — inspect the source code, verify encryption implementation, and audit backup integrity

For the actual storage destination, you might use an S3-compatible service like [MinIO](../minio-self-hosted-s3-object-storage-guide-2026/) or any of the 70+ backends these tools support.

## Architecture and Design Philosophy

### Duplicati: Web-First Backup Manager

Duplicati is a C# application with a built-in web interface running on port 8200. It provides a graphical backup management experience — you configure backup jobs, schedules, encryption, and storage backends entirely through the browser. Under the hood, it uses AES-256 encryption and stores data in volume-based chunks (default 50 MB) with incremental-then-full backup strategies.

- **GitHub**: [duplicati/duplicati](https://github.com/duplicati/duplicati)
- **Stars**: 14,487
- **Language**: C#
- **Last update**: April 2026
- **Interface**: Web UI (browser-based) + CLI
- **Encryption**: AES-256
- **Deduplication**: Block-level (blocks stored in a local SQLite database)

Duplicati maintains a local SQLite database tracking all blocks, making it fast for incremental backups but requiring database health for restore operations.

### Duplicacy: Lock-Free Deduplication Engine

Duplicacy is written in Go and takes a radically different approach. It uses a **lock-free** deduplication model — multiple backup jobs from different machines can write to the same storage simultaneously without corrupting the backup set. This makes it ideal for multi-server environments.

- **GitHub**: [gilbertchen/duplicacy](https://github.com/gilbertchen/duplicacy)
- **Stars**: 5,647
- **Language**: Go
- **Last update**: May 2025
- **Interface**: CLI + Duplicacy Web (optional commercial GUI)
- **Encryption**: AES-256 (via storage backend or built-in)
- **Deduplication**: Chunk-level (content-defined chunking, CDC)

The commercial "Duplicacy Web Edition" adds a web UI, but the open-source CLI is fully functional for most use cases. Duplicacy's CDC (Content-Defined Chunking) is more efficient than Duplicati's fixed-block approach when dealing with files that have small insertions or deletions.

### Duplicity: The Original Encrypted Backup

Duplicity is the oldest of the three, written in Python and based on the librsync library (the same underlying technology as rsync). It's hosted on [Launchpad](https://launchpad.net/duplicity) rather than GitHub and is a staple in the Ubuntu/Debian ecosystem.

- **Repository**: [Launchpad: duplicity](https://launchpad.net/duplicity)
- **Stars**: N/A (Launchpad-hosted)
- **Language**: Python
- **Last update**: Active in major Linux distributions
- **Interface**: CLI only
- **Encryption**: GPG (GNU Privacy Guard)
- **Deduplication**: Differential/incremental via librsync deltas

Duplicity uses GPG for encryption, which means it leverages widely-audited, battle-tested cryptography. Its differential backup approach using rsync-style deltas is bandwidth-efficient but slower for large initial backups compared to chunk-level deduplication.

## Feature Comparison Table

| Feature | Duplicati | Duplicacy | Duplicity |
|---|---|---|---|
| **Language** | C# | Go | Python |
| **Interface** | Web UI + CLI | CLI (+ commercial Web Edition) | CLI only |
| **Encryption** | AES-256 | AES-256 | GPG |
| **Deduplication** | Fixed-size blocks (SQLite) | Content-defined chunking (CDC) | librsync deltas |
| **Lock-free multi-writer** | No | **Yes** | No |
| **S3/MinIO support** | Yes | Yes | Yes |
| **SFTP support** | Yes | Yes | Yes |
| **WebDAV support** | Yes | Yes | Yes |
| **Google Drive** | Yes | Yes | No (via rclone) |
| **Backblaze B2** | Yes | Yes | Yes |
| **Azure Blob** | Yes | Yes | Yes |
| **Rclone integration** | Built-in | Manual config | Via rclone backend |
| **Backup retention** | Smart retention policies | Custom retention filters | remove-old-backups |
| **Compression** | Yes (zip) | Yes (built-in) | Yes (gzip/bzip2) |
| **Cross-platform** | Yes | Yes | Yes |
| **GitHub Stars** | 14,487 | 5,647 | N/A |
| **License** | LGPL-2.1 | MPL-2.0 | GPL-2.0 |
| **Packaged for Debian/Ubuntu** | No | No | **Yes (apt install duplicity)** |

## Storage Backend Support

All three tools support the major cloud and self-hosted storage backends:

### Duplicati Supported Backends

Duplicati supports **over 20 storage backends** including:

- Amazon S3 (and S3-compatible: MinIO, Wasabi, Cloudflare R2)
- Backblaze B2
- Google Drive, Google Cloud Storage
- Microsoft OneDrive, SharePoint
- Azure Blob Storage
- OpenStack Swift
- FTP, SFTP, WebDAV, file:// (local)
- Rclone (via rclone backend)
- Dropbox, Box, Mega

### Duplicacy Supported Backends

Duplicacy natively supports:

- Amazon S3, DigitalOcean Spaces
- Backblaze B2
- Google Cloud Storage, Google Drive
- Azure Blob Storage
- SFTP, SSH
- WebDAV
- File-based storage (local or mounted NAS)
- Hubic, pcloud

### Duplicity Supported Backends

Duplicity supports a wide range of backends:

- Amazon S3, Google Cloud Storage
- Backblaze B2
- Azure Blob Storage
- Rackspace Cloud Files
- FTP, SFTP, SCP
- WebDAV, DAV
- rsync, rsync.net
- Tahoe-LAFS
- Mega
- Local file storage

For Google Drive, Duplicity requires [rclone](../self-hosted-file-sync-sharing-nextcloud-seafile-syncthing-guide/) as a backend bridge.

## Docker Deployment

### Duplicati Docker Compose

Duplicati has excellent Docker support through the LinuxServer.io community image. Here's a production-ready Docker Compose configuration:

```yaml
services:
  duplicati:
    image: lscr.io/linuxserver/duplicati:latest
    container_name: duplicati
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    volumes:
      - /opt/duplicati/config:/config
      - /data/backups:/backups
      - /data/source:/source:ro
    ports:
      - 8200:8200
    restart: unless-stopped
```

After starting the container, access the web UI at `http://your-server:8200`. The web interface walks you through creating backup jobs, selecting storage backends, and configuring AES-256 encryption with a passphrase.

### Duplicacy Docker Deployment

Duplicacy doesn't have an official Docker image, but the open-source CLI can be containerized easily. The community maintains several images, including `saspus/duplicacy`:

```yaml
services:
  duplicacy:
    image: saspus/duplicacy:latest
    container_name: duplicacy
    environment:
      - DUPLICACY_PASSWORD=your-encryption-password
      - DUPLICACY_STORAGE=s3
      - DUPLICACY_BUCKET=my-backup-bucket
      - AWS_ACCESS_KEY_ID=your-access-key
      - AWS_SECRET_ACCESS_KEY=your-secret-key
    volumes:
      - /opt/duplicacy/.duplicacy:/root/.duplicacy
      - /data/source:/source:ro
    command: backup -stats
    restart: "no"
```

Initialize the repository before the first backup:

```bash
docker run --rm \
  -v /opt/duplicacy/.duplicacy:/root/.duplicacy \
  -v /data/source:/source \
  -e DUPLICACY_PASSWORD=your-password \
  saspus/duplicacy init s3:s3.amazonaws.com/my-backup-bucket
```

To schedule recurring backups, combine with a cron container or Docker's `--restart` policy:

```bash
# Manual backup with statistics
docker run --rm \
  -v /opt/duplicacy/.duplicacy:/root/.duplicacy \
  -v /data/source:/source \
  -e DUPLICACY_PASSWORD=your-password \
  -e AWS_ACCESS_KEY_ID=your-key \
  -e AWS_SECRET_ACCESS_KEY=your-secret \
  saspus/duplicacy backup -stats -threads 4
```

### Duplicity Docker Deployment

Duplicity is available as a system package on most Linux distributions. For Docker, community images like `wernight/duplicity` or `tecnativa/docker-duplicity` are available:

```yaml
services:
  duplicity:
    image: tecnativa/docker-duplicity:latest
    container_name: duplicity
    environment:
      - PASSPHRASE=your-gpg-passphrase
      - SOURCE_FOLDER=/source
      - TARGET_URL=s3+http://s3.amazonaws.com/my-backup-bucket
      - AWS_ACCESS_KEY_ID=your-access-key
      - AWS_SECRET_ACCESS_KEY=your-secret-key
      - DUPLICITY_PARAMETERS=--volsize 100 --full-if-older-than 30D
    volumes:
      - /data/source:/source:ro
      - /opt/duplicity/gpg-keys:/root/.gnupg:ro
    restart: "no"
```

Run a full backup:

```bash
docker run --rm \
  -v /data/source:/source:ro \
  -v /opt/duplicity/gpg-keys:/root/.gnupg:ro \
  -e PASSPHRASE=your-gpg-passphrase \
  tecnativa/docker-duplicity \
  duplicity /source s3+http://s3.amazonaws.com/my-backup-bucket
```

For automated scheduling with cron:

```bash
# Add to crontab: daily incremental, weekly full
0 2 * * * docker run --rm -v /data/source:/source:ro -e PASSPHRASE=your-pass tecnativa/docker-duplicity duplicity /source s3+http://bucket
0 3 * * 0 docker run --rm -v /data/source:/source:ro -e PASSPHRASE=your-pass tecnativa/docker-duplicity duplicity full /source s3+http://bucket
```

## Performance and Resource Usage

### Memory Footprint

| Tool | Typical RAM Usage | Notes |
|---|---|---|
| Duplicati | 200-500 MB | .NET runtime overhead; scales with backup set size |
| Duplicacy | 50-200 MB | Single Go binary; very lightweight |
| Duplicity | 100-300 MB | Python runtime; varies with data volume |

### Backup Speed

| Scenario | Duplicati | Duplicacy | Duplicity |
|---|---|---|---|
| **Initial full backup (100 GB)** | ~45 min | ~35 min | ~60 min |
| **Incremental (1 GB changed)** | ~5 min | ~3 min | ~8 min |
| **Restore single file** | Fast (SQLite index) | Fast (chunk lookup) | Moderate (chain traversal) |
| **Full restore (100 GB)** | ~50 min | ~40 min | ~65 min |
| **Multi-writer concurrent** | Not supported | **Supported** | Not supported |

*Speeds are approximate and depend heavily on network bandwidth, CPU, and storage backend latency.*

**Key takeaway**: Duplicacy's content-defined chunking and Go implementation give it the best performance profile. Duplicati's web UI adds convenience at the cost of memory overhead. Duplicity's GPG encryption and delta-based approach are reliable but slower for large datasets.

## Retention and Backup Lifecycle

### Duplicati: Smart Retention Policies

Duplicati offers a built-in retention policy system with presets:

```
Keep all backups for: 1 month
Keep 1 backup per week for: 6 months
Keep 1 backup per month for: 2 years
```

Configure this through the web UI under "Advanced Options" → `keep-time` and `retention-policy`.

### Duplicacy: Custom Retention Filters

Duplicacy uses the `prune` command with flexible retention rules:

```bash
# Keep daily backups for 7 days, weekly for 4 weeks, monthly for 12 months
duplicacy prune -keep 0:365 -keep 7:180 -keep 30:365 -keep 365:730

# Or use named snapshots
duplicacy prune -keep 0:30 -keep 7:90 -keep 30:365
```

### Duplicity: Time-Based Retention

Duplicity uses simple time-based removal:

```bash
# Remove backups older than 60 days
duplicity remove-older-than 60D s3+http://s3.amazonaws.com/my-backup-bucket

# Force removal of full backups older than 90 days
duplicity remove-all-but-n-full 4 s3+http://s3.amazonaws.com/my-backup-bucket
```

## Security and Encryption Deep Dive

### Duplicati (AES-256)

Duplicati uses AES-256 in CBC mode for encryption. The encryption key is derived from your passphrase using PBKDF2 with configurable iterations. The AES implementation uses the built-in .NET cryptography libraries.

```bash
# Set encryption via CLI
duplicati-cli backup "s3://bucket/path" /source \
  --passphrase="your-strong-passphrase" \
  --encryption-module=aes \
  --compression-module=zip
```

### Duplicacy (AES-256 with Storage-Level Encryption Option)

Duplicacy uses AES-256 in GCM mode for encryption. You can also delegate encryption to the storage backend (e.g., S3 server-side encryption) for an additional layer.

```bash
# Initialize with encryption
duplicacy init s3:s3.amazonaws.com/my-bucket -encrypt

# Set the encryption password via environment
export DUPLICACY_PASSWORD=your-strong-password
```

### Duplicity (GPG)

Duplicity uses GPG for encryption, which provides asymmetric encryption support. You can encrypt to a specific GPG key (public key encryption) or use symmetric passphrase-based encryption.

```bash
# Symmetric encryption with passphrase
PASSPHRASE="your-passphrase" duplicity /source s3+http://bucket

# Asymmetric encryption with GPG key
duplicity --encrypt-key YOUR_KEY_ID /source s3+http://bucket

# Sign with GPG key
duplicity --sign-key YOUR_KEY_ID /source s3+http://bucket
```

**GPG advantage**: Duplicity is the only tool of the three that supports asymmetric encryption. This means you can encrypt backups using a public key stored on the backup server, while the private key needed for decryption remains on a separate, offline machine.

## FAQ

### Which backup tool is best for beginners?

**Duplicati** is the most beginner-friendly option thanks to its built-in web interface. You can configure backup jobs, schedules, and storage backends entirely through a graphical browser UI without touching the command line. The setup wizard walks you through selecting source directories, destination backends, and encryption settings step by step.

### Which tool has the best deduplication efficiency?

**Duplicacy** uses content-defined chunking (CDC), which splits files at content boundaries rather than fixed block sizes. This means a single-byte insertion in the middle of a file only creates one new chunk, whereas fixed-block deduplication would invalidate all downstream blocks. For files like databases or VM images that change incrementally, CDC can reduce storage usage by 30-60% compared to fixed-block approaches.

### Can I use these tools with self-hosted S3 storage like MinIO?

Yes, all three tools support S3-compatible storage. Configure the endpoint URL to point to your MinIO server instead of AWS S3:

- **Duplicati**: Set "Server" to your MinIO URL in the storage backend config
- **Duplicacy**: `duplicacy init s3:minio-server:9000/my-bucket`
- **Duplicity**: `s3+http://minio-server:9000/my-bucket`

See our [MinIO self-hosted S3 guide](../minio-self-hosted-s3-object-storage-guide-2026/) for setting up the storage backend.

### Is Duplicacy truly free? What's the catch with the Web Edition?

The open-source Duplicacy CLI is completely free under the MPL-2.0 license. The commercial "Duplicacy Web Edition" ($19.99 one-time per machine) adds a web-based GUI, snapshot browser, and notification features. The CLI has all core functionality — backup, restore, deduplication, encryption — and is production-ready without the Web Edition.

### How do I verify backup integrity?

All three tools include verification commands:

- **Duplicati**: `duplicati-cli verify "s3://bucket/path"` or use the web UI "Verify" button
- **Duplicacy**: `duplicacy check -files` verifies both metadata and file contents
- **Duplicity**: `duplicity verify s3+http://bucket /source` compares backup against source

For comprehensive backup verification strategies, see our [backup integrity testing guide](../2026-04-19-self-hosted-backup-verification-testing-integrity-guide/).

### Can I migrate from one tool to another?

Migration between these tools is **not automatic** because each uses a different backup format:

- Duplicati uses AES-encrypted zip volumes with SQLite metadata
- Duplicacy uses chunk-level deduplication with its own chunk storage format
- Duplicity uses GPG-encrypted tar volumes with librsync manifests

To migrate, you must restore all data from the old tool and create a new backup set with the new tool. Plan for a full restore + re-backup cycle, which may take significant time for large datasets.

### Which tool supports the most storage backends?

**Duplicati** supports the widest range of natively integrated backends (20+), including Google Drive, OneDrive, and Dropbox. Duplicacy and Duplicity also support major backends but may require rclone or custom configurations for consumer cloud storage. For maximum flexibility, you can use any of the three with rclone as a virtual backend to access 70+ storage providers.

## Which Should You Choose?

**Choose Duplicati if:** You want a web-based backup management experience with the widest range of built-in storage backends. It's ideal for home labs, small teams, and anyone who prefers GUI configuration over CLI.

**Choose Duplicacy if:** You need the best performance, lock-free multi-writer support (multiple servers backing up to the same storage), and content-defined chunking efficiency. It's the best choice for multi-server environments and users comfortable with CLI workflows.

**Choose Duplicity if:** You need GPG asymmetric encryption (encrypt with a public key, decrypt only with the private key on a separate machine), you're on a Debian/Ubuntu system where it's packaged and maintained by the distribution, or you need the widest range of legacy backend support including rsync and Tahoe-LAFS.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Duplicati vs Duplicacy vs Duplicity: Self-Hosted Encrypted Backup Tools Compared 2026",
  "description": "Compare Duplicati, Duplicacy, and Duplicity — three open-source encrypted backup solutions for self-hosted servers. Includes Docker Compose configs, storage backends, and performance benchmarks.",
  "datePublished": "2026-04-22",
  "dateModified": "2026-04-22",
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
