---
title: "Self-Hosted Backup Verification & Integrity Testing: Borg vs Restic vs Duplicati Guide (2026)"
date: "2026-06-07"
tags: ["backup", "backup-verification", "borg", "restic", "duplicati", "data-integrity", "self-hosted", "disaster-recovery"]
draft: false
---

## Introduction

A backup that hasn't been verified is not a backup — it's a hope. Data corruption, bit rot, and silent filesystem errors can render months of backups useless without warning. Self-hosted backup verification tools systematically validate your backup integrity, detect corruption early, and alert you before you need to restore from a damaged backup during a real emergency.

This guide compares three leading open-source backup tools through the lens of **verification and integrity testing**: **BorgBackup** (with borgmatic orchestration), **Restic**, and **Duplicati**. We evaluate their built-in verification features, corruption detection capabilities, alerting integrations, and self-hosted deployment strategies.

## Why Verify Your Backups?

Storage media degrades over time. Hard drives develop bad sectors, SSDs experience bit rot, and network transfers can silently corrupt data. Without verification, you might discover that last month's critical database backup is unrecoverable only when you need it most — during an outage.

Self-hosted verification catches these failures proactively. Borg's `check` command performs repository-wide integrity verification with cryptographic hash validation. Restic's `check` command reads all pack files and verifies their structure and index consistency. Duplicati's built-in verification tests random backup samples and validates block-level hashes.

Beyond corruption detection, verification also validates your restore procedure. A backup that passes integrity checks but lacks restorable metadata (permissions, ACLs, extended attributes) is still a failed backup. Regular restore drills — automated by self-hosted tooling — close this gap.

For choosing your primary backup tool, see our [comprehensive backup tool comparison](../restic-vs-borg-vs-kopia-backup-guide/). If you need snapshot-based protection, check our [ZFS snapshot replication guide](../sanoid-vs-znapzend-vs-syncoid-zfs-snapshot-replication-guide-2026/). For centralized backup server management, our [self-hosted backup server guide](../urbackup-vs-backuppc-vs-bareos-self-hosted-backup-server-guide-2026/) covers enterprise deployments.

## Comparison Table

| Feature | BorgBackup + Borgmatic | Restic | Duplicati |
|---------|----------------------|--------|-----------|
| **Stars** | 13,401 (borg) + 2,269 (borgmatic) | 33,896 | 14,630 |
| **Language** | Python (Cython accelerated) | Go | C# |
| **License** | BSD-3-Clause | BSD-2-Clause | LGPL-2.1 |
| **Verification Command** | `borg check --verify-data` | `restic check --read-data` | Built-in verification (auto) |
| **Integrity Mechanism** | HMAC-SHA256 authenticated encryption | Content-defined chunking + SHA-256 | AES-256-GCM + block-level hashing |
| **Deduplication** | Variable-length chunking (buzhash) | Content-defined chunking (CDC) | Block-level dedup |
| **Compression** | lz4, zstd, zlib, lzma | zstd (auto), off | zip, 7z |
| **Encryption** | Authenticated (repokey/keyfile) | AES-256-CTR + Poly1305 | AES-256-GCM |
| **Scheduling** | borgmatic (systemd timers) | External (cron/systemd) | Built-in scheduler |
| **Alerting** | borgmatic hooks (healthchecks.io, ntfy) | External via exit codes | Built-in email/SMTP |
| **Web UI** | No (borgmatic is CLI) | No (rest-server + restic-browser) | Yes (built-in) |
| **Cloud Backends** | SFTP, rsync.net, borgbase | S3, B2, Azure, GCS, SFTP, rclone | S3, B2, Azure, GCS, FTP, SFTP, WebDAV |
| **Last Updated** | June 2026 | June 2026 | June 2026 |

## Self-Hosted Verification Deployment

### BorgBackup Automated Verification with Borgmatic

Borgmatic wraps Borg with declarative configuration, systemd timer scheduling, and health check hooks:

```yaml
# /etc/borgmatic/config.yaml
repositories:
  - path: ssh://backup-server/./borg-repo
    label: primary

source_directories:
  - /data/databases
  - /data/documents
  - /etc

encryption_passcommand: "cat /root/.borg-passphrase"

retention:
  keep_daily: 7
  keep_weekly: 4
  keep_monthly: 6
  keep_yearly: 2

consistency:
  checks:
    - name: repository
      frequency: 2 weeks
    - name: archives
      frequency: 2 weeks
    - name: data
      frequency: 1 month

hooks:
  before_backup:
    - echo "Starting backup at $(date)"
  after_backup:
    - curl -fsS --retry 3 https://hc-ping.com/YOUR-UUID
  on_error:
    - ntfy publish --title "Backup Failed" "Borg backup failed on $(hostname)"
```

Deploy with Docker:
```yaml
# docker-compose.yml for borgmatic
version: "3.8"
services:
  borgmatic:
    image: b3vis/borgmatic:latest
    volumes:
      - ./borgmatic.d:/etc/borgmatic.d
      - ./data:/data:ro
      - ./borg-cache:/root/.cache/borg
      - ./ssh:/root/.ssh:ro
      - /etc/localtime:/etc/localtime:ro
    environment:
      - TZ=UTC
      - BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK=no
```

Run verification manually:
```bash
# Full data verification (reads all data chunks)
docker compose exec borgmatic borg check --verify-data

# Quick repository check
docker compose exec borgmatic borg check --repository-only

# List and verify specific archive
docker compose exec borgmatic borg list
docker compose exec borgmatic borg check --archives-only
```

### Restic Automated Verification

Restic's `check` command provides progressive levels of verification:

```bash
#!/bin/bash
# restic-verify.sh — Automated restic verification with alerting
set -e

export RESTIC_REPOSITORY="s3:s3.amazonaws.com/bucket/restic-repo"
export RESTIC_PASSWORD_FILE="/root/.restic-pass"
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."

# Quick structural check (minutes)
echo "=== Quick structural check ==="
restic check || ntfy publish --title "Restic Check Failed" "Structural check failed"

# Read subset of pack files (hours)
echo "=== Partial data verification (10% sample) ==="
restic check --read-data-subset=10% || ntfy publish --title "Restic Verify Failed" "10% data check failed"

# Monthly: full data verification
if [ "$(date +%d)" = "01" ]; then
  echo "=== Full data verification ==="
  restic check --read-data || ntfy publish --title "Restic Full Verify Failed" "Full data check failed"
fi

curl -fsS https://hc-ping.com/YOUR-UUID
```

Systemd timer for automated verification:
```ini
# /etc/systemd/system/restic-verify.service
[Unit]
Description=Restic backup verification
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/restic-verify.sh
User=root
Nice=19
IOSchedulingClass=idle

# /etc/systemd/system/restic-verify.timer
[Unit]
Description=Weekly restic backup verification

[Timer]
OnCalendar=Sun 03:00:00
RandomizedDelaySec=3600
Persistent=true

[Install]
WantedBy=timers.target
```

### Duplicati Verification with Web UI

Duplicati's built-in web interface makes verification accessible to non-technical users. Deploy with Docker:

```yaml
# docker-compose.yml for Duplicati
version: "3.8"
services:
  duplicati:
    image: duplicati/duplicati:latest
    ports:
      - "8200:8200"
    volumes:
      - ./duplicati-config:/config
      - ./duplicati-data:/data
      - /data/backup-source:/source:ro
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
      - DUPLICATI__WEBSERVICE_PASSWORD=strong-password
    restart: unless-stopped
```

Duplicati verification settings (configured via web UI or CLI):
```bash
# Via CLI — set verification options
docker compose exec duplicati duplicati-cli set-auto-cleanup   --dbpath=/config/backup.sqlite   --auto-cleanup=true

# Run verification on specific backup
docker compose exec duplicati duplicati-cli test   "s3://bucket/duplicati-backup"   --dbpath=/config/backup.sqlite   --passphrase="encryption-passphrase"   --samples=10
```

## Verification Strategy: Defense in Depth

A robust verification pipeline combines multiple techniques:

1. **Daily quick checks**: Borg `check --repository-only` or Restic `check` (structural) — detects index corruption, missing pack files, and repository-level issues. Takes seconds to minutes.

2. **Weekly partial verification**: Restic `check --read-data-subset=5%` or Borg `check --archives-only` — samples random data chunks to catch bit rot and storage errors. Takes minutes to hours.

3. **Monthly full verification**: Borg `check --verify-data` or Restic `check --read-data` — reads every data chunk and verifies cryptographic hashes. Can take hours to days for large repositories.

4. **Quarterly restore drills**: Restore a random backup to a staging directory and verify file checksums against originals. Validates the entire backup chain: encryption, compression, metadata preservation, and restorability.

```bash
#!/bin/bash
# Quarterly restore drill
RESTORE_DIR="/tmp/restore-drill-$(date +%Y%m%d)"
mkdir -p "$RESTORE_DIR"

# Restore random archive
restic restore latest --target "$RESTORE_DIR"

# Verify file integrity (sample check)
find "$RESTORE_DIR" -type f | shuf -n 100 | while read f; do
  orig="/data/$(echo "$f" | sed "s|$RESTORE_DIR||")"
  if [ -f "$orig" ]; then
    if ! diff -q "$f" "$orig" > /dev/null 2>&1; then
      echo "INTEGRITY FAILURE: $f differs from $orig"
      curl -fsS https://ntfy.sh/your-topic -d "Restore drill: file mismatch detected"
    fi
  fi
done

rm -rf "$RESTORE_DIR"
echo "Restore drill complete: $(date)"
```

## Choosing the Right Verification Tool

**Choose BorgBackup + Borgmatic if** you want the most comprehensive verification with flexible scheduling and hook-based alerting. Borg's authenticated encryption (HMAC-SHA256) provides cryptographic proof of integrity, and borgmatic's declarative YAML config makes verification scheduling explicit and reproducible.

**Choose Restic if** you need cloud-native backup verification with S3/B2/Azure backends. Restic's `check --read-data-subset=N%` is ideal for large cloud repositories where full verification would be cost-prohibitive due to egress fees. Its Go implementation is a single static binary with zero dependencies.

**Choose Duplicati if** you need a web UI for backup management and verification. Duplicati's built-in dashboard shows verification status, backup health, and alert configuration in a single interface. It's the best choice for homelab and small business environments where non-technical users need visibility into backup health.

## Monitoring Integrations

```yaml
# Borgmatic health check integrations
hooks:
  after_backup:
    - curl -fsS https://hc-ping.com/backup-uuid
  after_check:
    - curl -fsS https://hc-ping.com/verify-uuid
  on_error:
    - ntfy publish --tags warning "Borg failed"
    - echo "Backup failure" | mail -s "ALERT" admin@example.com
```

Healthchecks.io (self-hosted or cloud) provides dead-man-switch alerting — if a backup or verification job doesn't report within its expected window, you get notified. Combine with ntfy.sh for push notifications to your phone, or Prometheus Alertmanager for integration with existing monitoring infrastructure.

## FAQ

### How often should I run full data verification?

Monthly for critical data (databases, financial records, source code repositories). Quarterly for large media archives (video, photos, datasets). Weekly for quick structural checks. The verification frequency should match your Recovery Time Objective (RTO) — if losing a month of backups is unacceptable, verify weekly.

### Does backup verification impact performance during verification?

Borg's `--verify-data` reads every chunk in the repository, which can saturate disk I/O and network bandwidth for large repositories. Schedule verification during off-peak hours with `Nice=19` and `IOSchedulingClass=idle` in systemd units. Restic's `--read-data-subset=N%` allows gradual verification that's less resource-intensive. Duplicati's throttling options let you limit bandwidth usage during verification.

### What happens when verification detects corruption?

Borg: corrupted chunks are reported but the repository remains usable. Restore from the last good archive. If you have replication (borgmatic to multiple repos), switch to the healthy replica. Restic: structural errors are reported with specific pack file IDs. Use `restic repair index` for index corruption; for data corruption, restore from a healthy snapshot or repair using `restic repair packs`. Duplicati: the web UI shows affected backup versions and recommends recovery actions.

### Can I verify encrypted backups without the passphrase?

No — all three tools require the encryption key or passphrase to verify data integrity. This is by design: authenticated encryption ties integrity verification to the decryption key. Without the key, you can only verify repository structure (are all files present?), not data integrity (is the content correct?). Store encryption keys in a hardware security module (HSM) or separate vault (Vault, Infisical) with strict access controls.

### How do I verify backups stored in cloud object storage (S3, B2)?

Restic handles this natively — `restic check --read-data` works with all supported backends. Be aware of egress costs: reading 1 TB of data from S3 for verification costs ~$90 in data transfer fees. Use `--read-data-subset=5%` for routine checks and reserve full verification for monthly runs. Borg requires the repository to be accessible as a filesystem or via SFTP — use rclone mount to expose S3 as a local path for verification. Duplicati's built-in verification works directly with cloud backends.

### What's the difference between checking repository structure and verifying data?

Structural checks validate that all expected pack files exist, indexes are consistent, and the repository is internally coherent — this catches filesystem corruption, incomplete transfers, and metadata errors. Data verification reads the actual backup content and recomputes cryptographic hashes — this catches bit rot, silent data corruption, and storage media degradation. Structural checks take seconds to minutes; full data verification can take hours to days for large repositories.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Backup Verification & Integrity Testing: Borg vs Restic vs Duplicati Guide (2026)",
  "description": "Comprehensive guide to self-hosted backup verification and integrity testing with BorgBackup (borgmatic), Restic, and Duplicati. Covers automated verification strategies, Docker deployment, corruption detection, and monitoring integrations.",
  "datePublished": "2026-06-07",
  "dateModified": "2026-06-07",
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
