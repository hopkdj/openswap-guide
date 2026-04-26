---
title: "Rsync vs Rclone vs Lsyncd: Best Self-Hosted File Sync Tools 2026"
date: 2026-04-26
tags: ["comparison", "guide", "self-hosted", "file-sync", "backup", "storage"]
draft: false
description: "Compare rsync, rclone, and lsyncd — the three essential open-source file synchronization tools. Learn when to use each tool with practical Docker configs and deployment guides."
---

When you run a self-hosted infrastructure, keeping files in sync across servers, storage volumes, and cloud backups is a daily operational requirement. Whether you're replicating data between data centers, syncing media libraries, or maintaining disaster recovery copies, the right tool makes the difference between automated reliability and manual chaos.

Three open-source tools dominate this space: **rsync**, the decades-old Unix standard for local and remote file synchronization; **rclone**, the cloud storage powerhouse supporting 70+ providers; and **lsyncd**, the live syncing daemon that automates rsync in real time.

This guide compares all three, explains when each tool is the right choice, and provides production-ready Docker Compose configurations you can deploy today.

| Tool | Stars | Last Updated | Language | Best For |
|------|-------|-------------|----------|----------|
| [rsync](https://rsync.samba.org/) | N/A (core Unix utility) | N/A | C | Local/NFS sync, SSH transfers |
| [rclone](https://github.com/rclone/rclone) | 56,861 | Apr 24, 2026 | Go | Cloud storage sync, mounting |
| [lsyncd](https://github.com/axkibe/lsyncd) | 6,034 | Nov 27, 2024 | Lua/C | Real-time directory mirroring |

## Why Self-Hosted File Sync Matters

Cloud sync services like Dropbox, Google Drive, and OneDrive solve file synchronization for consumers, but they introduce several problems for infrastructure operators:

- **Vendor lock-in**: Migrating terabytes between cloud providers is expensive and slow
- **Compliance**: Many industries require data to remain on self-managed infrastructure
- **Cost**: Cloud egress fees and storage pricing scale poorly at large volumes
- **Control**: You can't audit proprietary sync clients or customize their behavior
- **Latency**: Syncing through third-party servers adds unnecessary network hops

Self-hosted sync tools give you full control over data movement. They work over SSH, direct network mounts, or HTTP APIs — no intermediary required. And they compose well: you can use rsync for server-to-server replication, rclone for cloud backup tiers, and lsyncd for real-time mirroring, all within the same infrastructure.

For a broader view of self-hosted storage options, see our [file sync and sharing comparison](../self-hosted-file-sync-sharing-nextcloud-seafile-syncthing-guide/) and [backup tool guide](../restic-vs-borg-vs-kopia-backup-guide/). If you're building a complete backup strategy, also check our [backup verification and testing guide](../2026-04-19-self-hosted-backup-verification-testing-integrity-guide/).

## Understanding Each Tool

### Rsync: The Unix Workhorse

Rsync has been part of the Unix ecosystem since 1996. Its core innovation is the **delta-transfer algorithm**, which sends only the differences between source and destination files rather than entire file contents. This makes rsync dramatically more efficient than naive copy tools, especially over slow or metered connections.

Key capabilities:

- **Delta transfers**: Only changed blocks are transmitted
- **Compression**: `-z` flag compresses data during transfer
- **SSH transport**: Built-in SSH support for encrypted transfers
- **Partial transfers**: `--partial` resumes interrupted transfers
- **Exclude patterns**: `--exclude` and `--include` for filtering
- **Hard link preservation**: `--hard-links` maintains link structure

Rsync ships with virtually every Linux and macOS distribution. It requires no additional dependencies and works out of the box.

### Rclone: Cloud Storage Swiss Army Knife

Rclone describes itself as "rsync for cloud storage" — but it's grown far beyond that tagline. It supports over 70 storage providers including S3-compatible services, Google Drive, Dropbox, Backblaze B2, Azure Blob, SFTP, WebDAV, and local filesystems.

Key capabilities:

- **Multi-provider support**: 70+ storage backends with consistent CLI
- **Mount mode**: FUSE-based mounting of cloud storage as a local filesystem
- **Sync/copy/move**: Full range of file operations with dry-run support
- **Encryption**: Client-side encryption with `crypt` remote
- **Web GUI**: Built-in web interface for monitoring and management
- **REST API**: JSON API for integration with other tools
- **Bandwidth limiting**: `--bwlimit` for throttling transfers
- **Checksums**: Hash verification across providers

Rclone is written in Go and ships as a single static binary. It runs on Linux, macOS, Windows, and BSD systems.

### Lsyncd: Real-Time Directory Mirroring

Lsyncd (Live Syncing Daemon) watches a local directory for filesystem changes using `inotify` or `fswatch`, then automatically triggers rsync or rsync-like commands to replicate those changes to a target. It fills the gap between manual rsync runs and complex distributed filesystems.

Key capabilities:

- **Real-time sync**: Sub-second detection and replication of changes
- **Event coalescing**: Groups rapid changes into single sync operations
- **Multiple targets**: Sync one directory to multiple destinations
- **Custom actions**: Lua scripting for pre/post-sync hooks
- **Low overhead**: Monitors only — no daemon on the target side
- **SSH transport**: Uses rsync over SSH by default

Lsyncd consists of a C inotify watcher and a Lua configuration engine. It runs on Linux and macOS.

## Feature Comparison

| Feature | Rsync | Rclone | Lsyncd |
|---------|-------|--------|--------|
| Delta transfers | ✅ Yes | ✅ Yes (partial) | ✅ Via rsync |
| Real-time sync | ❌ Manual | ❌ Manual/scheduled | ✅ inotify-based |
| Cloud storage | ❌ No | ✅ 70+ providers | ❌ No (local only) |
| SSH transport | ✅ Native | ✅ SFTP backend | ✅ Via rsync |
| Encryption in transit | ✅ Via SSH | ✅ TLS/client-side | ✅ Via rsync/SSH |
| Bandwidth limiting | ✅ `--bwlimit` | ✅ `--bwlimit` | Via rsync config |
| Web GUI | ❌ No | ✅ Built-in | ❌ No |
| REST API | ❌ No | ✅ Available | ❌ No |
| Hard link support | ✅ `--hard-links` | ❌ No | ✅ Via rsync |
| Exclude patterns | ✅ Yes | ✅ Yes | ✅ Via rsync |
| Resume interrupted | ✅ `--partial` | ✅ Yes | Via rsync |
| Cross-platform | Unix, macOS, WSL | All platforms | Linux, macOS |
| FUSE mount | ❌ No | ✅ `rclone mount` | ❌ No |
| Configuration | CLI flags | Config file + flags | Lua config file |

## When to Use Each Tool

### Choose Rsync When:

- You need fast, efficient transfers between Linux/Unix servers
- You're syncing over SSH to untrusted networks
- You want to preserve Unix file permissions, ownership, and hard links
- You need to sync NFS-mounted directories
- Bandwidth is limited and delta transfers matter
- You're building backup scripts with `cron`

Rsync excels at server-to-server replication. If both source and destination are Unix filesystems accessible via SSH or NFS, rsync is usually the best choice.

### Choose Rclone When:

- You need to sync to or from cloud storage providers
- You want to mount cloud storage as a local filesystem
- You need client-side encryption for data at rest
- You're managing data across multiple storage providers
- You want a web dashboard to monitor transfer progress
- You need to sync from systems where rsync isn't available (Windows)

Rclone is the go-to tool for hybrid cloud architectures. It lets you treat every storage provider as a standardized remote, with consistent commands across all of them.

### Choose Lsyncd When:

- You need real-time (sub-second) directory replication
- You want to automate rsync without cron scheduling
- You're mirroring a web application's upload directory to a CDN origin
- You need to sync configuration files across server clusters
- You want event-driven sync without polling overhead

Lsyncd is ideal when you need continuous synchronization but don't want the complexity of a distributed filesystem like GlusterFS or Ceph.

## Deployment Guides

### Rsync: SSH-Based Sync Setup

Rsync requires no server installation — it only needs SSH access and rsync installed on both sides (which is the default on virtually all Linux systems).

**Basic one-way sync:**

```bash
rsync -avz --progress /data/source/ user@remote-server:/data/destination/
```

**Bandwidth-limited sync with excludes:**

```bash
rsync -avz \
  --bwlimit=5000 \
  --exclude='*.tmp' \
  --exclude='.cache/' \
  --partial \
  --progress \
  /data/source/ \
  user@remote-server:/data/destination/
```

**Automated sync via cron** — add to `/etc/crontab`:

```bash
# Sync /data/uploads to backup server every 15 minutes
*/15 * * * * root rsync -az --delete /data/uploads/ backup@files.example.com:/data/uploads/
```

**Docker Compose for rsync daemon mode** — when you need to accept incoming rsync connections without SSH:

```yaml
version: "3.8"

services:
  rsync-server:
    image: aptakube/rsync-server:latest
    container_name: rsync-server
    restart: unless-stopped
    ports:
      - "873:873"
    volumes:
      - /data/shared:/data/shared
      - ./rsyncd.conf:/etc/rsyncd.conf
      - ./rsyncd.secrets:/etc/rsyncd.secrets
    environment:
      - UID=1000
      - GID=1000
```

Create `rsyncd.conf`:

```ini
[shared]
    path = /data/shared
    comment = Shared data directory
    auth users = syncuser
    secrets file = /etc/rsyncd.secrets
    read only = false
    hosts allow = 10.0.0.0/8
```

Create `rsyncd.secrets` (chmod 600):

```
syncuser:YourStrongPassword
```

Connect from a client:

```bash
rsync -avz /local/data/ rsync://syncuser@rsync-server:873/shared/
```

### Rclone: Cloud Storage Sync

**Install rclone:**

```bash
curl https://rclone.org/install.sh | sudo bash
```

**Configure a remote:**

```bash
rclone config
```

This launches an interactive wizard. For Backblaze B2, you'd select:

```
n) New remote
name> b2-backup
Storage> b2
env_auth> false
account> your-account-id
key> your-application-key
```

**Sync local directory to cloud storage:**

```bash
rclone sync /data/local b2-backup:mybucket/data \
  --progress \
  --transfers=8 \
  --checkers=16 \
  --log-file=/var/log/rclone-sync.log
```

**Mount cloud storage as local filesystem:**

```bash
rclone mount b2-backup:mybucket /mnt/cloud-storage \
  --vfs-cache-mode=writes \
  --allow-other \
  --umask=002 \
  --daemon
```

**Docker Compose for rclone with web GUI:**

```yaml
version: "3.8"

services:
  rclone:
    image: rclone/rclone:latest
    container_name: rclone
    restart: unless-stopped
    command: rcd --rc-web-gui --rc-addr=:5572 --rc-user=admin --rc-pass=SecurePass123
    ports:
      - "5572:5572"
    volumes:
      - /data/local:/data/local:ro
      - ./rclone.conf:/config/rclone/rclone.conf
      - rclone-cache:/cache
    environment:
      - PGID=1000
      - PUID=1000
    security_opt:
      - no-new-privileges:true

volumes:
  rclone-cache:
```

Generate the config file:

```bash
docker run --rm -it rclone/rclone config \
  --config /config/rclone/rclone.conf
```

Then mount it:

```bash
docker run --rm -it rclone/rclone \
  --config /config/rclone/rclone.conf \
  sync /data/local b2-backup:mybucket \
  --progress
```

**Automated daily sync with cron inside Docker:**

```yaml
services:
  rclone-sync:
    image: rclone/rclone:latest
    container_name: rclone-cron
    restart: unless-stopped
    command: >
      sh -c "
        while true; do
          rclone sync /data/local b2-backup:mybucket \
            --transfers=4 \
            --log-file=/var/log/rclone.log \
            --log-level=INFO;
          sleep 86400;
        done
      "
    volumes:
      - /data/local:/data/local:ro
      - ./rclone.conf:/config/rclone/rclone.conf
```

### Lsyncd: Real-Time Directory Mirroring

**Install lsyncd (Debian/Ubuntu):**

```bash
sudo apt update
sudo apt install -y lsyncd
```

**Install lsyncd (RHEL/CentOS):**

```bash
sudo yum install -y lsyncd
```

**Configuration file** — edit `/etc/lsyncd/lsyncd.conf.lua`:

```lua
settings {
    logfile = "/var/log/lsyncd/lsyncd.log",
    statusFile = "/var/log/lsyncd/lsyncd.status",
    statusInterval = 10,
    nodaemon = false,
}

sync {
    default.rsyncssh,
    source = "/data/uploads",
    host = "backup.example.com",
    targetdir = "/data/uploads",
    rsync = {
        compress = true,
        acls = true,
        verbose = true,
        _extra = {"--bwlimit=2000"},
    },
    ssh = {
        port = 22,
    },
    delay = 5,
    maxProcesses = 4,
    delete = true,
}
```

This configuration watches `/data/uploads` and syncs changes to `backup.example.com` within 5 seconds of any modification. The `delay = 5` setting coalesces rapid changes — if 100 files are modified within 5 seconds, they're synced as a single rsync operation rather than 100 individual transfers.

**Multiple targets from one source:**

```lua
sync {
    default.rsync,
    source = "/data/shared",
    target = "mirror1.example.com::shared",
    delay = 1,
}

sync {
    default.rsync,
    source = "/data/shared",
    target = "mirror2.example.com::shared",
    delay = 1,
}
```

**Docker Compose for lsyncd:**

```yaml
version: "3.8"

services:
  lsyncd:
    image: ghcr.io/evolution/lsyncd:latest
    container_name: lsyncd
    restart: unless-stopped
    privileged: true
    volumes:
      - /data/source:/source:ro
      - /root/.ssh:/root/.ssh:ro
      - ./lsyncd.conf.lua:/etc/lsyncd/lsyncd.conf.lua
    environment:
      - TZ=UTC
    command: ["-nodaemon", "/etc/lsyncd/lsyncd.conf.lua"]
```

**Verify lsyncd is running:**

```bash
# Check status
sudo systemctl status lsyncd

# Watch the log in real time
sudo tail -f /var/log/lsyncd/lsyncd.log

# Check sync status
cat /var/log/lsyncd/lsyncd.status
```

## Advanced Patterns

### Combining All Three Tools

A production file sync architecture often uses all three tools together:

```
[Application Server]
        │
        ├── lsyncd → real-time mirror → [Web Server / CDN Origin]
        │
        └── rsync (cron, hourly) → incremental backup → [Backup Server]
                                      │
                                      └── rclone (cron, daily) → cloud archive → [Backblaze B2 / S3]
```

- **lsyncd** handles real-time mirroring to the web server tier
- **rsync** runs hourly for incremental backups to a local backup server
- **rclone** runs daily to push an encrypted copy to cloud storage for disaster recovery

### Encrypted Sync with Rclone Crypt

Rclone's `crypt` remote provides transparent client-side encryption:

```bash
# Create an encrypted remote (wraps an existing remote)
rclone config
n) New remote
name> encrypted-b2
Storage> crypt
remote> b2-backup:mybucket-encrypted
filename_encryption> standard
directory_name_encryption> true
password> [generate or enter your own]
```

```bash
# Sync with automatic encryption
rclone sync /data/sensitive encrypted-b2: --progress
```

The data is encrypted before leaving your server. The cloud provider never sees your plaintext files or filenames.

### Monitoring Rsync Transfers

For large rsync operations, use `--info=progress2` for overall transfer progress:

```bash
rsync -avz --info=progress2 /data/source/ user@remote:/data/dest/
```

For detailed logging in scripts:

```bash
rsync -avz \
  --log-file=/var/log/rsync-$(date +%Y%m%d).log \
  --log-format='%i %n%L' \
  /data/source/ \
  user@remote:/data/dest/
```

## Performance Tips

| Tool | Tip | Impact |
|------|-----|--------|
| Rsync | Use `--checksum` only when needed | Avoids full file reads on every run |
| Rsync | Use `-W` (whole-file) on fast LANs | Faster than delta algorithm locally |
| Rclone | Set `--transfers` to match your bandwidth | Prevents connection saturation |
| Rclone | Use `--s3-upload-cutoff` for large files | Reduces multipart upload overhead |
| Lsyncd | Set `delay` based on change frequency | Balances latency vs. batch efficiency |
| Lsyncd | Limit `maxProcesses` on busy servers | Prevents resource exhaustion |

## FAQ

### Can rclone replace rsync for local server-to-server sync?

Not entirely. While rclone supports SFTP and can sync between servers, rsync's delta-transfer algorithm is significantly more efficient for Unix-to-Unix transfers. Rclone transfers entire changed files, whereas rsync only transfers the modified blocks. For large files with small changes over slow connections, rsync is always the better choice. Use rclone when cloud storage is involved.

### Does lsyncd work with Windows file systems?

Lsyncd relies on `inotify`, which is Linux-specific. On macOS, it can use `fswatch` as an alternative backend. Windows is not supported. For Windows environments, consider using `robocopy` with Task Scheduler, or install WSL2 and use rsync within the Linux subsystem.

### How do I handle SSH key authentication for automated rsync?

Generate an SSH key pair without a passphrase on the source server and add the public key to the destination server's `~/.ssh/authorized_keys`:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/rsync-key -N ""
ssh-copy-id -i ~/.ssh/rsync-key.pub user@destination
rsync -avz -e "ssh -i ~/.ssh/rsync-key" /source/ user@destination:/dest/
```

Restrict the key's capabilities in `authorized_keys` with `command="rsync --server..."` and `from="source-ip"` for security.

### What happens if rclone sync is interrupted mid-transfer?

Rclone automatically resumes interrupted transfers. Files that were partially uploaded are detected and resumed from the point of interruption. Use the `--progress` flag to see transfer status, and check the log file with `--log-file` to confirm completion. The `rclone check` command can verify source and destination match after an interrupted sync.

### Can lsyncd sync to multiple destinations simultaneously?

Yes. Define multiple `sync{}` blocks in the lsyncd configuration, each pointing to a different target. Lsyncd watches the source directory once and dispatches changes to all configured targets. Each target has its own process queue, so a slow destination won't block faster ones. Set `maxProcesses` per sync block to control concurrency.

### Is rsync secure enough for transfers over the public internet?

Rsync itself has no built-in encryption, but when used with SSH transport (`rsync -e ssh` or the default `rsync://` over SSH), all data is encrypted in transit. Always use SSH for transfers over untrusted networks. For the rsync daemon mode (port 873), restrict access with `hosts allow` in `rsyncd.conf` and consider tunneling through SSH or a VPN.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Rsync vs Rclone vs Lsyncd: Best Self-Hosted File Sync Tools 2026",
  "description": "Compare rsync, rclone, and lsyncd — the three essential open-source file synchronization tools. Learn when to use each tool with practical Docker configs and deployment guides.",
  "datePublished": "2026-04-26",
  "dateModified": "2026-04-26",
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
