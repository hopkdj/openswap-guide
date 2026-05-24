---
title: "Self-Hosted Restic Server & Web UIs: rest-server vs Backrest vs Rustic (2026)"
date: "2026-05-25"
tags: ["backup", "restic", "storage", "self-hosted", "comparison", "guide"]
draft: false
description: "Compare rest-server, Backrest, and rustic for self-hosted restic backup management. Deployment guides, Docker Compose configs, and feature comparison for secure backup servers."
---

When you run [restic](https://restic.net/) backups across multiple machines, you need a central repository server to store the encrypted backup data. While restic supports many backends (S3, SFTP, local disk), running a dedicated restic repository server gives you full control over your backup infrastructure without relying on cloud providers.

This guide compares three approaches to self-hosting restic backup servers: the official **rest-server**, the feature-rich **Backrest** web UI, and the modern Rust-based **rustic** implementation. Each serves a different use case, from minimal HTTP storage to full-featured backup orchestration with web management.

## Why Self-Host Your Restic Backup Server?

Running your own restic repository server offers significant advantages over cloud-based backup storage. When you self-host, your encrypted backup data never leaves your infrastructure. Restic uses client-side AES-256 encryption, meaning even if your server is compromised, attackers cannot read your backup contents without the repository password.

Cost savings are another major driver. Cloud backup storage charges $0.023/GB/month on AWS S3, which adds up quickly for multi-terabyte repositories. A self-hosted server with 8TB of local storage costs a one-time hardware investment of roughly $200-300, plus minimal electricity. For organizations with strict data residency requirements, self-hosting ensures backup data stays within your physical premises and legal jurisdiction.

Self-hosted restic servers also eliminate vendor lock-in. The restic repository format is open and well-documented, meaning you can migrate between backends (local disk, S3, SFTP, rest-server) without re-encrypting or re-uploading your data. This portability is essential for long-term archival strategies.

For complete backup tool comparisons, see our [restic vs borg vs kopia guide](../restic-vs-borg-vs-kopia-backup-guide/) and [backup repository servers comparison](../2026-05-24-self-hosted-backup-repository-servers-kopia-restic-borg/). If you need backup verification strategies, our [backup integrity testing guide](../2026-05-11-backup-integrity-verification-restic-borg-borgmatic/) covers checksum validation and restore testing.

## rest-server: The Official Minimal Backend

[rest-server](https://github.com/restic/rest-server) (1,420+ stars) is the official HTTP server that implements restic's REST backend API. It provides a minimal, high-performance storage layer with authentication support.

### Features

- **Simple HTTP API** — implements the restic REST protocol directly, allowing any restic client to push/pull backups
- **Authentication** — supports htpasswd-based basic auth for repository access control
- **Append-only mode** — prevents snapshot deletion for ransomware protection
- **Multiple repositories** — serves multiple independent repositories from a single instance
- **Zero dependencies** — single Go binary, no database required

### Docker Deployment

```yaml
version: "3.8"
services:
  rest-server:
    image: restic/rest-server:latest
    ports:
      - "8000:8000"
    environment:
      - OPTIONS=--private-repos --listen :8000
    volumes:
      - ./data:/data
      - ./htpasswd:/etc/htpasswd
    restart: unless-stopped
```

To set up authentication:

```bash
# Create htpasswd file
docker run --rm httpd:2.4-alpine htpasswd -Bbn backupuser mypassword > ./htpasswd

# Initialize a repository from a client
restic -r rest:http://backupuser:mypassword@server:8000/backupuser init
```

### Append-Only Mode

For ransomware protection, enable append-only mode to prevent snapshot deletion:

```yaml
environment:
  - OPTIONS=--private-repos --append-only --listen :8000
```

This prevents `restic forget` and `restic prune` operations, ensuring backups can only grow, never shrink.

## Backrest: Full-Featured Backup Orchestrator

[Backrest](https://github.com/garethgeorge/backrest) (6,365+ stars) is a comprehensive web UI and orchestrator for restic backups. It goes far beyond simple storage, providing a complete backup management platform with scheduling, monitoring, and alerting.

### Features

- **Web dashboard** — full browser-based UI for managing repositories, schedules, and restores
- **Multi-repository management** — manage dozens of backup targets from a single interface
- **Scheduling** — built-in cron-like scheduler with configurable backup frequencies
- **Health monitoring** — tracks backup success/failure rates, repository size, and age
- **Notifications** — alerts via email, webhook, Discord, Slack, and Gotify
- **REST API** — programmatic access for automation and integration
- **Direct S3/local/rest-server support** — acts as an orchestrator over any restic backend

### Docker Deployment

```yaml
version: "3.8"
services:
  backrest:
    image: ghcr.io/garethgeorge/backrest:latest
    ports:
      - "9898:9898"
    environment:
      - BACKREST_DATA=/data
    volumes:
      - ./backrest-data:/data
      - ./backrest-config:/config
      - /etc/backrest-repos:/repos:ro
    restart: unless-stopped
```

After deployment, access the web UI at `http://your-server:9898`. Configure repositories by specifying the storage path (local, S3, or rest-server URL) and the restic password. Backrest handles repository initialization automatically.

### Scheduling Example

In the web UI, create a schedule with:
- **Repository**: select your configured repository
- **Paths**: directories to back up (e.g., `/home`, `/etc`, `/var/lib/docker/volumes`)
- **Schedule**: `0 2 * * *` (daily at 2 AM)
- **Retention**: keep 7 daily, 4 weekly, 12 monthly snapshots

Backrest will execute backups on schedule and send notifications on failure, making it ideal for unattended server environments.

## rustic: Modern Rust Implementation

[rustic](https://github.com/rustic-rs/rustic) (3,059+ stars) is a reimplementation of restic in Rust, offering compatible backup functionality with improved performance and a modern codebase. While primarily a backup client, rustic includes server capabilities for repository hosting.

### Features

- **Rust-based performance** — faster backup operations through parallel I/O and efficient memory management
- **Restic-compatible repositories** — full read/write compatibility with existing restic repositories
- **Profile-based configuration** — TOML configuration files for reproducible backup setups
- **Prune and check** — built-in repository maintenance with optimized algorithms
- **Copy between repositories** — efficient repository-to-repository synchronization
- **Hot/cold storage separation** — native support for splitting metadata and data across storage tiers

### Docker Deployment

```yaml
version: "3.8"
services:
  rustic:
    image: ghcr.io/rustic-rs/rustic:latest
    volumes:
      - ./repos:/repos
      - ./config:/config:ro
      - /backup-source:/data:ro
    entrypoint: ["sh", "-c"]
    command: ["rustic --use-profile /config/profile.toml backup /data"]
    restart: "no"
```

Profile configuration (`/config/profile.toml`):

```toml
[repository]
repository = "/repos/backup"
password-file = "/config/password.txt"

[backup]
exclude-if-present = [".nobackup", "CACHEDIR.TAG"]
one-file-system = true

[prune]
keep-daily = 7
keep-weekly = 4
keep-monthly = 12
```

Run scheduled backups via cron on the host:

```bash
0 3 * * * docker run --rm -v /path/to/repos:/repos -v /path/to/config:/config:ro ghcr.io/rustic-rs/rustic:latest --use-profile /config/profile.toml backup /data
```

## Feature Comparison

| Feature | rest-server | Backrest | rustic |
|---------|-------------|----------|--------|
| **Primary role** | Storage backend | Backup orchestrator | Backup client + server |
| **Web UI** | No | Yes (full dashboard) | No (CLI only) |
| **Scheduling** | No | Yes (built-in) | No (via cron) |
| **Authentication** | htpasswd | Web UI + API tokens | Repository password |
| **Append-only mode** | Yes | Yes (configurable) | No |
| **Notifications** | No | Yes (email, webhook, Discord, Slack) | No |
| **Multi-repo** | Yes | Yes (dashboard view) | Yes (profile-based) |
| **REST API** | Yes (restic protocol) | Yes (management API) | No |
| **Docker image** | Docker Hub | GHCR | GHCR |
| **Stars** | 1,420+ | 6,365+ | 3,059+ |
| **Language** | Go | Go | Rust |
| **Best for** | Minimal storage server | Full backup management | Performance-focused users |

## Choosing the Right Solution

**Use rest-server** when you need a simple, reliable storage backend for restic clients. It's the lightest option, requiring minimal resources and configuration. Ideal for home labs and small teams where backup scheduling is handled externally (cron, CI/CD, or orchestration tools).

**Use Backrest** when you want a complete backup management platform. The web UI makes it easy to monitor backup health across dozens of repositories, set schedules without touching cron, and receive alerts when backups fail. Best for small-to-medium businesses and homelab enthusiasts who want a "set and forget" backup solution.

**Use rustic** when performance matters most. The Rust implementation offers faster backup and restore operations, especially on systems with many small files. Its profile-based configuration is ideal for infrastructure-as-code setups where backup configs are version-controlled alongside other system configuration.

## FAQ

### Can I use rest-server with existing restic repositories?

Yes. rest-server is fully compatible with the restic REST protocol. Point your restic client to `rest:http://server:8000/reponame` and it works exactly like a local repository. Existing backups can be copied to a rest-server backend using `restic copy`.

### Does Backrest replace restic entirely?

No. Backrest is an orchestrator that uses restic (or rustic) under the hood. It manages restic processes, schedules, and provides a web UI, but the actual backup engine is still restic. You benefit from restic's encryption and deduplication while gaining management features.

### Is rustic compatible with restic repositories?

Yes. rustic uses the same repository format as restic. You can switch between restic and rustic clients on the same repository without any migration. However, always test with a non-critical repository first, as newer restic features may not be immediately supported in rustic.

### How do I protect my restic backup server from ransomware?

Enable append-only mode on rest-server to prevent snapshot deletion. For Backrest, configure repository settings to disallow prune operations. Additionally, maintain an offline copy of your repository password and use separate credentials for backup writers vs. restore readers.

### Can I replicate restic repositories between servers?

Yes. Use `restic copy` to copy snapshots between repositories, or use `rustic copy` for faster transfers. For automated replication, Backrest supports configuring multiple repositories and copying between them on a schedule.

### What storage backend should I use for the repository data?

Local SSDs provide the best performance for active repositories. For archival, any filesystem works (ext4, XFS, Btrfs). If you need redundancy, use RAID or ZFS mirrors. Avoid network filesystems (NFS) for active repositories as they can cause locking issues — use rest-server's HTTP API instead.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Restic Server & Web UIs: rest-server vs Backrest vs Rustic (2026)",
  "description": "Compare rest-server, Backrest, and rustic for self-hosted restic backup management. Deployment guides, Docker Compose configs, and feature comparison.",
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
