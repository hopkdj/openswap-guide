---
title: "Self-Hosted Backup Repository Servers: Kopia Server vs Restic Rest-Server vs Borg Backup Server"
date: "2026-05-21"
tags: ["backup", "kopia", "restic", "borg", "repository", "deduplication"]
draft: false
---

Deduplicating backup tools like Kopia, Restic, and Borg Backup are among the most popular self-hosted data protection solutions. But these clients need somewhere to store their backup data. While they support cloud storage (S3, B2, GCS), running a self-hosted backup repository server gives you complete control over your backup data, eliminates cloud storage fees, and keeps all backups within your network perimeter. In this guide, we compare three self-hosted repository server options: **Kopia Server**, **Restic Rest-Server**, and **Borg Backup Server**.

## Understanding Backup Repository Architecture

Deduplicating backup tools split your data into chunks, compute cryptographic hashes, and store only unique chunks. The repository is the storage location where these chunks, metadata, and snapshot manifests live. Most backup tools support multiple repository types:

- **Local repositories**: Direct filesystem access (fastest, single-node only)
- **SFTP/SSH repositories**: Remote filesystem over SSH
- **S3-compatible repositories**: Object storage (MinIO, Backblaze B2, AWS S3)
- **HTTP/REST repositories**: Custom API server (our focus today)

REST-based repository servers are particularly valuable for self-hosted setups because they provide authenticated, concurrent access from multiple backup clients without requiring individual SSH keys or S3 credentials for each machine.

## Kopia Server

Kopia Server is the most feature-rich self-hosted backup repository option. It provides a multi-user HTTP API with per-user encryption, quota management, and a built-in web dashboard for monitoring backup status across all connected clients.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  kopia:
    image: kopia/kopia:0.17.0
    container_name: kopia-server
    ports:
      - "51515:51515"
    volumes:
      - kopia_config:/app/config
      - kopia_data:/app/data
      - /etc/localtime:/etc/localtime:ro
    environment:
      - KOPIA_PASSWORD=my-secure-password
    command: >
      server start
      --config-file=/app/config/repository.config
      --address=0.0.0.0:51515
      --tls-generate-cert=false
      --server-username=admin
      --server-password=my-secure-password
    restart: unless-stopped

  kopia-ui:
    image: kopia/kopia:0.17.0
    container_name: kopia-ui
    ports:
      - "51516:51515"
    volumes:
      - kopia_config:/app/config
      - kopia_data:/app/data
    command: >
      server start
      --config-file=/app/config/repository.config
      --address=0.0.0.0:51515
      --tls-generate-cert
    restart: unless-stopped

volumes:
  kopia_config:
  kopia_data:
```

Connecting a Kopia client to the server:

```bash
# Connect to the repository server
kopia repository connect server   --url https://backup-server:51515   --server-cert-fingerprint <fingerprint>

# Create a snapshot policy
kopia policy set /home/user --keep-latest=7 --keep-daily=30 --keep-monthly=12

# Run backup
kopia snapshot create /home/user
```

### Kopia Server Features

| Feature | Details |
|---------|---------|
| Authentication | Multi-user with per-user credentials |
| Encryption | Client-side AES-256-GCM (server never sees plaintext) |
| Quotas | Per-user storage quotas configurable via CLI |
| Dashboard | Built-in web UI at `https://server:51515` |
| Compression | LZ4, Zstandard, S2 (configurable per-policy) |
| Concurrent Clients | Unlimited simultaneous connections |
| Storage Backend | Local filesystem, S3, B2, GCS, Azure Blob |
| GitHub Stars | 13,240 |

## Restic Rest-Server

Restic Rest-Server is a lightweight HTTP server designed specifically as a backend for the Restic backup tool. It provides a simple REST API that Restic clients use to store and retrieve backup blobs. The server is intentionally minimal — no web dashboard, no user management beyond basic auth — making it easy to deploy and maintain.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  rest-server:
    image: restic/rest-server:0.12.1
    container_name: restic-rest-server
    ports:
      - "8000:8000"
    volumes:
      - restic_data:/data
    environment:
      - OPTIONS=--private-repos --append-only
      - USERNAME=admin
      - PASSWORD=my-secure-password
    restart: unless-stopped

volumes:
  restic_data:
```

Initializing and using Restic with the REST server:

```bash
# Initialize repository on the REST server
export RESTIC_REPOSITORY="rest:http://admin:my-secure-password@backup-server:8000/admin"
export RESTIC_PASSWORD="repository-password"
restic init

# Create a backup snapshot
restic backup /home/user --exclude='*.cache' --exclude='node_modules'

# List snapshots
restic snapshots

# Restore from a specific snapshot
restic restore latest --target /tmp/restore
```

### Restic Rest-Server Features

| Feature | Details |
|---------|---------|
| Authentication | Basic HTTP auth (single user) or per-repo users |
| Encryption | Client-side AES-256 (server stores only encrypted blobs) |
| Private Repos | `--private-repos` isolates each user's data |
| Append-Only | `--append-only` prevents snapshot deletion (ransomware protection) |
| Storage Limit | `--max-size` flag caps repository size |
| Dashboard | None (CLI-only management) |
| GitHub Stars | 33,600 (Restic client); rest-server is a companion project |

## Borg Backup Server

Borg Backup (formerly Attic) does not have an official dedicated server daemon like Kopia or Restic. Instead, Borg uses SSH as its transport protocol, connecting to a remote filesystem via SSH keys. The "server" side is simply a directory on an SSH-accessible machine, optionally managed with `borgmatic` for automation.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  borg-server:
    image: ghcr.io/borgbackup/borg:1.4.0
    container_name: borg-backup-server
    ports:
      - "2222:22"
    volumes:
      - borg_data:/backup
      - borg_ssh:/etc/ssh
      - ./authorized_keys:/root/.ssh/authorized_keys:ro
    environment:
      - TZ=UTC
    command: >
      sh -c "
        mkdir -p /backup/repo &&
        borg init --encryption=repokey /backup/repo &&
        /usr/sbin/sshd -D
      "
    restart: unless-stopped

volumes:
  borg_data:
  borg_ssh:
```

Using Borg with a remote SSH repository:

```bash
# Initialize a remote repository over SSH
borg init --encryption=repokey ssh://user@backup-server:2222/backup/repo

# Create a backup
borg create   --stats   --compression zstd,8   --exclude='*.pyc'   ssh://user@backup-server:2222/backup/repo::backup-{now:%Y-%m-%d}   /home/user

# List repository contents
borg list ssh://user@backup-server:2222/backup/repo

# Mount a snapshot for file-level recovery
borg mount ssh://user@backup-server:2222/backup/repo /mnt/restore
```

### Borg Server Features

| Feature | Details |
|---------|---------|
| Authentication | SSH keys (public key authentication) |
| Encryption | AES-256-CTR + HMAC-SHA256 (repokey mode) |
| Compression | LZ4, Zstandard, LZMA (configurable) |
| Append-Only | SSH `force-command` restriction limits operations |
| Dashboard | None (use `borgmatic` or `vorta` for management GUI) |
| Concurrency | Single-writer model; no simultaneous backups to same repo |
| GitHub Stars | 13,345 |

## Comparison: Kopia Server vs Restic Rest-Server vs Borg Server

| Criteria | Kopia Server | Restic Rest-Server | Borg Server (SSH) |
|----------|-------------|-------------------|-------------------|
| Protocol | Custom HTTP API | REST API | SSH (SFTP-like) |
| Multi-User | Native (web UI + CLI) | Via URL path isolation | SSH user accounts |
| Web Dashboard | Built-in | None | None (Vorta GUI client available) |
| Client-Side Encryption | Yes (AES-256-GCM) | Yes (AES-256) | Yes (AES-256-CTR) |
| Compression | LZ4, Zstd, S2 | None (client handles) | LZ4, Zstd, LZMA |
| Append-Only Mode | Via policy | Server flag | SSH forced command |
| Concurrent Writers | Yes | Yes (per-repo) | No (single-writer) |
| Setup Complexity | Low | Low | Medium (SSH key mgmt) |
| Quota Management | Per-user quotas | `--max-size` flag | Filesystem quotas |
| Best For | Multi-user environments | Simple single-server | SSH-centric infra |

## Deployment Architecture Patterns

For small deployments (1-3 backup clients), any of the three options work well. The choice typically comes down to existing tooling familiarity:

- If you already use **Kopia** for local backups, enabling Kopia Server adds multi-client support with minimal configuration changes.
- If you prefer **Restic**, the rest-server adds only 20 MB of overhead and can be deployed alongside other containers on the same host.
- If your infrastructure is already **SSH-centric** (Ansible-managed, key-based auth), Borg's SSH transport integrates naturally without introducing additional services.

For larger deployments (10+ backup clients), Kopia Server provides the best operational experience thanks to its built-in dashboard, per-user quotas, and snapshot management UI. Restic Rest-Server can also scale well but requires external monitoring since it lacks a built-in dashboard.

## Why Self-Host Your Backup Repository?

Running your own backup repository server is one of the most impactful self-hosting decisions you can make. When you store backups on cloud services like Backblaze B2, AWS S3, or Google Cloud Storage, you pay ongoing egress fees every time you need to restore data. These fees are negligible for occasional restores but become significant during disaster recovery scenarios where you need to download hundreds of gigabytes. A self-hosted repository on a local NAS or VPS eliminates egress fees entirely, since all backup traffic flows over your own network.

Data sovereignty is another critical factor. Cloud backup providers store your encrypted data on infrastructure you do not control, in jurisdictions that may have different data protection laws. While the backup data itself is encrypted, metadata — such as backup frequency, data volume changes, and restore patterns — can reveal information about your organization's operations. Self-hosting keeps all metadata within your infrastructure boundary.

For organizations managing compliance requirements, self-hosted backup repositories simplify auditing. You can prove exactly where backup data is stored, who has access to the repository server, and what network paths the backup traffic uses. Cloud providers cannot offer the same level of transparency because their multi-tenant architecture obscures the physical location and access controls of individual customer data.

Performance during restores is dramatically improved with self-hosted repositories. Restoring a 500 GB backup from a local gigabit network takes approximately one hour. The same restore from a cloud object storage service depends on your internet connection speed — with a 100 Mbps connection, it takes over 11 hours. For business continuity planning, this difference can be the gap between acceptable and unacceptable downtime.

Finally, cost predictability matters. Cloud storage pricing changes, and providers have increased prices multiple times over the past few years. A self-hosted repository on hardware you already own has a marginal cost of essentially zero. Even on a rented VPS, a 500 GB storage server typically costs $10-20/month — significantly less than the equivalent S3 Standard storage plus API request fees for a backup workload with daily snapshots.

For those exploring backup strategies, see our [encrypted backup tools comparison](../2026-04-22-duplicati-vs-duplicacy-vs-duplicity-self-hosted-encrypted-backup-2026/) and our [backup integrity verification guide](../2026-05-11-backup-integrity-verification-restic-borg-borgmatic/). If you need file synchronization alongside backups, our [rclone comparison](../2026-04-26-rsync-vs-rclone-vs-lsyncd-self-hosted-file-sync-tools-guide-2026/) covers the best options.

## FAQ

### Can multiple clients backup to the same repository simultaneously?

Kopia Server supports unlimited concurrent clients — each client gets its own encrypted namespace within the repository. Restic Rest-Server supports concurrent access when using the `--private-repos` flag, which creates isolated repositories per user. Borg does NOT support concurrent writers to the same repository — attempting simultaneous backups will cause a lock conflict. Use Borgmatic's scheduling to stagger backup times for multiple clients.

### How much storage does the repository server need?

Deduplicating backup repositories typically use 30-60% of the raw source data size, depending on data change rate. For daily backups of a 100 GB workstation with 5% daily change rate, expect approximately 150-200 GB of repository storage after 30 days. Plan for at least 3x the total source data size to maintain a comfortable retention policy with headroom for growth.

### Is the backup data encrypted on the repository server?

Yes, all three tools use client-side encryption. The encryption happens on the backup client before data is transmitted to the repository server. The server only stores encrypted blobs — it cannot read, modify, or decrypt the backup data. Even if the repository server is compromised, the attacker gains access only to encrypted ciphertext without the client's encryption password.

### Can I migrate from one repository type to another?

Direct migration between repository formats is not supported. However, you can migrate by restoring all data from the old repository and creating new snapshots in the new repository. For Kopia to Restic (or vice versa), use `kopia restore` to extract data, then `restic backup` to create new snapshots. This requires temporary storage equal to the full dataset size. Plan migration during off-peak hours since the restore-and-re-backup process is I/O intensive.

### What happens if the repository server runs out of disk space?

All three tools handle this differently. Kopia will fail the snapshot creation with a clear error message but will not corrupt existing data. Restic will fail mid-backup with an "unable to append" error — the incomplete snapshot is safely discarded. Borg will fail with a "disk full" error. In all cases, existing snapshots remain intact. Configure disk usage alerts (via monitoring the volume or filesystem) to prevent this scenario.

### How do I automate backup scheduling with these tools?

Kopia has a built-in scheduler when running in server mode — policies define snapshot frequency and retention. Restic relies on external schedulers like cron or systemd timers (`restic backup` in a cron job). Borg is commonly automated with `borgmatic`, which handles scheduling, pruning, and health checking in a single YAML configuration. For containerized deployments, use Kubernetes CronJobs or Docker's built-in restart policies with wrapper scripts.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Backup Repository Servers: Kopia Server vs Restic Rest-Server vs Borg Backup Server",
  "description": "Compare self-hosted backup repository servers: Kopia Server, Restic Rest-Server, and Borg Backup Server. Includes Docker Compose configs, feature comparisons, and deployment patterns.",
  "datePublished": "2026-05-21",
  "dateModified": "2026-05-21",
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
