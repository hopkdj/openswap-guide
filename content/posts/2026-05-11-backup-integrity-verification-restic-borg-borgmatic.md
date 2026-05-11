---
title: "Self-Hosted Backup Integrity Verification: Restic vs Borg vs Borgmatic 2026"
date: "2026-05-11"
tags: ["comparison", "guide", "self-hosted", "backup", "storage", "integrity", "verification"]
draft: false
description: "Compare restic check, borg check, and borgmatic for self-hosted backup integrity verification. Ensure your backups are recoverable before you need them."
---

The most dangerous backup is one you've never tested. A backup that appears to complete successfully but contains corrupted data is worse than no backup at all — it gives you a false sense of security until disaster strikes and recovery fails.

Backup integrity verification is the practice of systematically checking that your backup archives are complete, uncorrupted, and recoverable. For self-hosted backup solutions like [Restic](https://restic.net/) and [Borg Backup](https://www.borgbackup.org/), this means validating repository structure, checking archive integrity, and periodically performing test restores.

This guide compares the backup integrity verification capabilities of Restic, Borg Backup, and Borgmatic — three leading open-source backup tools — and provides a framework for building a robust verification pipeline.

## Why Backup Verification Matters

Backup failures are surprisingly common and often silent:

- **Bit rot**: Storage media degradation silently corrupts data over time
- **Network errors**: Interrupted transfers leave partial archives
- **Software bugs**: Backup tool crashes may produce incomplete archives
- **Encryption corruption**: Damaged encryption headers make entire archives unreadable
- **Repository corruption**: Backend storage issues (S3 consistency, disk failures) corrupt the backup index

Without systematic verification, you won't know any of this has happened until you attempt a restore — often during an emergency when the pressure is highest.

## Restic: Built-In Verification

**Project**: [restic/restic](https://github.com/restic/restic) · 26,000+ stars · Active development

Restic is a modern, encrypted backup program that stores data in a cryptographically secure repository format. Its verification capabilities are built into the core tool.

### Restic Check Command

```bash
# Basic repository integrity check
restic check --repo s3:s3.amazonaws.com/bucket/restic

# Check specific snapshot
restic check --repo /backup/restic --cache-only

# Verify all data integrity (reads every blob)
restic check --read-data --repo s3:s3.amazonaws.com/bucket/restic

# Check with verbose output
restic check --read-data --verbose --repo /backup/restic
```

### Understanding Restic Check Levels

| Level | Command | What It Checks | Speed |
|-------|---------|---------------|-------|
| Structural | `restic check` | Repository structure, pack files referenced | Fast |
| Cache-only | `restic check --cache-only` | Index consistency only | Very fast |
| Full read | `restic check --read-data` | Every data blob is readable and decryptable | Slow (reads all data) |

### Docker Compose for Restic Verification

```yaml
version: "3.8"
services:
  restic-verify:
    image: restic/restic:latest
    environment:
      RESTIC_REPOSITORY: "/backup/restic"
      RESTIC_PASSWORD_FILE: "/run/secrets/restic-password"
    volumes:
      - backup_data:/backup
      - /etc/localtime:/etc/localtime:ro
    entrypoint: ["sh", "-c"]
    command: >
      "restic unlock &&
       restic check --read-data 2>&1 | tee /var/log/restic-check.log &&
       echo 'Verification completed at $(date)'"
    restart: "no"

  restic-backup:
    image: restic/restic:latest
    environment:
      RESTIC_REPOSITORY: "/backup/restic"
      RESTIC_PASSWORD_FILE: "/run/secrets/restic-password"
    volumes:
      - /data:/data:ro
      - backup_data:/backup
    entrypoint: ["sh", "-c", "restic backup /data"]

volumes:
  backup_data:

secrets:
  restic-password:
    file: ./secrets/restic-password.txt
```

### Automated Restic Verification Schedule

```bash
#!/bin/bash
# /usr/local/bin/restic-verify.sh
set -euo pipefail

export RESTIC_REPOSITORY="s3:s3.amazonaws.com/yourbucket/restic"
export RESTIC_PASSWORD_FILE="/etc/restic/password"
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"

# Unlock repository (in case of stale lock)
restic unlock

# Run full data integrity check
restic check --read-data 2>&1 | tee -a /var/log/restic-verify.log

# Check exit status
if [ $? -eq 0 ]; then
    echo "$(date): Verification PASSED" >> /var/log/restic-verify.log
else
    echo "$(date): Verification FAILED" >> /var/log/restic-verify.log
    # Send alert (mail, webhook, etc.)
    curl -s -X POST "https://your-alert-endpoint/webhook" \
         -H "Content-Type: application/json" \
         -d '{"status":"ALERT","message":"Restic backup verification failed"}'
fi
```

Add to crontab for weekly verification:
```cron
0 3 * * 0 /usr/local/bin/restic-verify.sh
```

### Restic Verification Strengths

- **Cryptographic integrity**: Every blob is hashed; corruption is detected during check
- **Incremental verification**: `--read-data-subset` option verifies only a portion of data
- **Backend agnostic**: Works identically across local disks, S3, SFTP, Rest Server, and more
- **Fast structural check**: Non-read-data check completes in seconds even for large repositories

## Borg Backup: Archive-Level Verification

**Project**: [borgbackup/borg](https://github.com/borgbackup/borg) · 6,000+ stars · Active development

Borg Backup is a deduplicating backup program that supports compression and authenticated encryption. Its verification tools focus on archive-level integrity checks.

### Borg Check Command

```bash
# Basic repository check
borg check /backup/borg-repo

# Verify specific archive
borg check /backup/borg-repo::my-backup-2026-01-15

# Verify data integrity (reads all archive data)
borg check --verify-data /backup/borg-repo

# Repair mode (use with caution)
borg check --repair /backup/borg-repo
```

### Understanding Borg Check Modes

| Mode | Command | What It Checks | Risk |
|------|---------|---------------|------|
| Quick check | `borg check` | Repository metadata, archive index | None |
| Data verify | `borg check --verify-data` | All archive data chunks | Safe, slow |
| Repair | `borg check --repair` | Attempts to fix corruption | Destructive if misused |

### Docker Compose for Borg Verification

```yaml
version: "3.8"
services:
  borg-verify:
    image: ghcr.io/borgbackup/borg:latest
    volumes:
      - backup_borg:/backup
      - /data/source:/data:ro
    environment:
      BORG_PASSPHRASE: "your-encryption-passphrase"
    entrypoint: ["sh", "-c"]
    command: >
      "borg check --verify-data /backup/borg-repo 2>&1 | tee /var/log/borg-check.log &&
       echo 'Borg verification completed'"

  borg-backup:
    image: ghcr.io/borgbackup/borg:latest
    volumes:
      - /data/source:/data:ro
      - backup_borg:/backup
    environment:
      BORG_PASSPHRASE: "your-encryption-passphrase"
    entrypoint: ["sh", "-c"]
    command: >
      "borg init --encryption=repokey /backup/borg-repo || true &&
       borg create /backup/borg-repo::'{now}' /data"

volumes:
  backup_borg:
```

### Borg Verification Best Practices

```bash
# Weekly quick check (fast)
borg check /backup/borg-repo

# Monthly full data verification
borg check --verify-data /backup/borg-repo

# Verify specific recent archive before critical restore
borg check --verify-data /backup/borg-repo::latest-backup

# Test restore to verify recoverability
mkdir -p /tmp/restore-test
borg extract /backup/borg-repo::latest-backup --dry-run
```

## Borgmatic: Orchestration with Built-In Verification

**Project**: [witten/borgmatic](https://torsion.org/borgmatic/) · Wraps Borg Backup with configuration management, scheduling, and monitoring.

Borgmatic is a configuration-driven wrapper around Borg Backup that adds automatic verification, monitoring, and notification capabilities. It's the recommended way to run Borg in production.

### Borgmatic Configuration for Verification

```yaml
# /etc/borgmatic.d/config.yaml
location:
    source_directories:
        - /data
    repositories:
        - path: /backup/borg-repo

storage:
    encryption_passphrase: "your-passphrase"

retention:
    keep_daily: 7
    keep_weekly: 4
    keep_monthly: 6

consistency:
    # Run checks on a schedule
    checks:
        - name: repository
          frequency: 1 week
        - name: archives
          frequency: 2 weeks
        - name: extract
          frequency: 1 month
      check_last: 3  # Check the last N archives

hooks:
    # Notifications on verification failure
    on_error:
        - curl -s -X POST "https://hooks.slack.com/services/YOUR/WEBHOOK" \
              -H "Content-Type: application/json" \
              -d '{"text":"Borgmatic verification failed!"}'
```

### Docker Compose with Borgmatic

```yaml
version: "3.8"
services:
  borgmatic:
    image: ghcr.io/witten/borgmatic:latest
    volumes:
      - /data/source:/data:ro
      - backup_borg:/backup
      - ./config:/etc/borgmatic.d:ro
      - /etc/borgmatic/passphrase:/run/secrets/borg-passphrase:ro
    environment:
      BORG_PASSPHRASE_FILE: "/run/secrets/borg-passphrase"
    command: >
      sh -c "
        borgmatic create --verbosity 1 &&
        borgmatic check --verbosity 1
      "
    restart: "no"

volumes:
  backup_borg:
```

### Borgmatic Verification Advantages

| Feature | Detail |
|---------|--------|
| Automated scheduling | Built-in cron-like scheduling for checks |
| Extract verification | Actually extracts files to verify recoverability |
| Monitoring hooks | Sends alerts on verification failure (Slack, email, webhook) |
| Configuration management | YAML-based config, no complex CLI arguments |
| Database hooks | Pre/post backup hooks for database dumps |

## Comprehensive Comparison

| Feature | Restic check | Borg check | Borgmatic |
|---------|-------------|------------|-----------|
| Structural verification | Yes | Yes | Yes (via Borg) |
| Full data read verification | `--read-data` | `--verify-data` | Configurable |
| Extract/dry-run verification | No | Manual extract command | `check: extract` |
| Automated scheduling | Manual (cron/systemd) | Manual (cron/systemd) | Built-in |
| Alert notifications | Manual scripting | Manual scripting | Built-in hooks |
| Repository repair | No | `--repair` (use carefully) | Via Borg |
| Partial verification | `--read-data-subset` | Per-archive check | Configurable per archive |
| Remote backend support | S3, SFTP, Rest, B2, etc. | SSH, Borg Server | Same as Borg |
| Deduplication awareness | Yes | Yes (content-defined) | Yes |

## Choosing the Right Verification Strategy

**Use Restic when:**
- You need fast structural checks across large repositories
- You want cryptographic integrity verification (every blob is hashed)
- You're using diverse backends (S3, SFTP, Rest Server, B2)
- Partial verification (`--read-data-subset`) fits your schedule

**Use Borg when:**
- You need archive-level verification with extract testing
- Your backup strategy relies on Borg's deduplication
- You're comfortable with manual scheduling and scripting

**Use Borgmatic when:**
- You want automated, scheduled verification without custom scripts
- You need built-in monitoring and alerting
- You're already using Borg and want better operational tooling
- You need database pre/post backup hooks alongside verification

## Why Self-Host Your Backup Infrastructure?

Self-hosted backup verification ensures that your backup integrity checks run on your own infrastructure, on your schedule, with full control over the verification process. Cloud backup services often provide limited or no verification APIs — you can't independently verify that your data in the cloud is intact and recoverable.

With self-hosted backup tools, you can implement a complete verification pipeline: automated integrity checks, test restores to isolated environments, and alerting when verification fails. This level of assurance is critical for compliance requirements (SOC 2, HIPAA, GDPR) that mandate regular backup testing.

For comprehensive backup strategies, see our [PostgreSQL backup comparison](../pgbackrest-vs-barman-vs-wal-g-self-hosted-postgresql-backup-guide-2026/) for database-specific approaches and [Kubernetes backup orchestration](../velero-vs-stash-vs-volsync-kubernetes-backup-orchestration-guide/) for container-native backup solutions.

## FAQ

### How often should I verify backup integrity?

Run structural checks weekly and full data verification monthly. The exact frequency depends on your recovery point objective (RPO) and the criticality of your data. For compliance environments (SOC 2, HIPAA), monthly full verification with quarterly test restores is a common baseline.

### Does `restic check --read-data` download all data from remote backends?

Yes. When running `restic check --read-data` against a remote backend (S3, B2, etc.), Restic downloads and verifies every data blob. This can be slow and generate significant network traffic. Use `--read-data-subset` to verify only a portion of data for routine checks, and run full verification during maintenance windows.

### What is the difference between structural check and data verification?

A structural check validates the repository index and pack file references — it confirms that the metadata is consistent. Data verification actually reads and decrypts every data blob, confirming that the stored data is readable and uncorrupted. Structural checks take seconds; data verification takes minutes to hours depending on repository size.

### Can Borg repair a corrupted repository?

Yes, with `borg check --repair`. However, this is a destructive operation — it may delete corrupted data to restore repository consistency. Always make a copy of the repository before running repair. In most cases, restoring from a known-good backup is safer than attempting repair.

### Does Borgmatic replace the need for manual Borg commands?

Borgmatic is a wrapper around Borg that handles scheduling, configuration, and monitoring. For most production use cases, Borgmatic is sufficient. However, advanced operations (repository migration, custom encryption, manual archive pruning) may still require direct Borg commands.

### How do I test restore without affecting production data?

Use a separate test environment with a copy of your backup repository. For Borg, use `borg extract --dry-run` to verify the archive structure without writing files. For Restic, restore to an isolated directory: `restic restore latest --target /tmp/restore-test`. Automate this as part of your monthly verification schedule.

### What happens if verification fails?

A verification failure indicates data corruption in your backup repository. Immediate steps: (1) Stop all backup operations to the affected repository, (2) Make a copy of the repository for forensic analysis, (3) Attempt restore from an earlier known-good snapshot, (4) Investigate the root cause (storage failure, network error, software bug), and (5) Rebuild the backup repository from source data once the cause is resolved.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Backup Integrity Verification: Restic vs Borg vs Borgmatic 2026",
  "description": "Compare restic check, borg check, and borgmatic for self-hosted backup integrity verification. Ensure your backups are recoverable before you need them.",
  "datePublished": "2026-05-11",
  "dateModified": "2026-05-11",
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
