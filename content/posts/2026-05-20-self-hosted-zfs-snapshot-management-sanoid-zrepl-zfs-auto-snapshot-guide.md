---
title: "Self-Hosted ZFS Snapshot Management: Sanoid vs zrepl vs zfs-auto-snapshot"
date: "2026-05-20"
tags: ["zfs", "backup", "storage", "snapshot", "self-hosted"]
draft: false
---

ZFS is one of the most powerful filesystems available for self-hosted storage, offering native snapshot and replication capabilities. However, managing ZFS snapshots manually quickly becomes unwieldy as the number of datasets grows. Dedicated snapshot management tools automate creation, retention, and replication of ZFS snapshots according to policy-driven rules.

In this guide, we compare three popular open-source ZFS snapshot management solutions: **Sanoid**, **zrepl**, and **zfs-auto-snapshot**. Each takes a different approach to the problem, from simple cron-based automation to full replication orchestration.

## What Is ZFS Snapshot Management?

ZFS snapshots are lightweight, read-only copies of a filesystem or volume that capture its state at a point in time. They consume space only for blocks that have changed since the snapshot was created (copy-on-write). While ZFS provides the `zfs snapshot` and `zfs destroy` commands natively, managing dozens of datasets with different retention policies requires automation.

A ZFS snapshot manager handles:
- **Automated creation** on a schedule (hourly, daily, weekly, monthly, yearly)
- **Retention policies** that prune old snapshots while keeping recent ones
- **Replication** of snapshots to a remote ZFS pool for disaster recovery
- **Monitoring and alerting** when snapshots fail or storage runs low

## Tool Comparison Overview

| Feature | Sanoid | zrepl | zfs-auto-snapshot |
|---------|--------|-------|-------------------|
| **GitHub Stars** | 3,763+ | 1,137+ | 924+ |
| **Language** | Perl | Go | Bash |
| **Snapshot Creation** | Yes | Yes | Yes |
| **Replication** | Via syncoid | Built-in | No |
| **Encryption Support** | Yes | Yes (native) | Limited |
| **Configuration Format** | INI | YAML | Cron labels |
| **Remote Replication** | Via SSH | Built-in (push/pull/sink) | No |
| **Monitoring** | Basic | Prometheus metrics | Syslog only |
| **Resume Support** | Via syncoid | Yes (checkpoint) | No |
| **Complexity** | Low | Medium | Very Low |
| **Best For** | Simple snapshot + replicate | Full DR orchestration | Basic auto-snapshots |

## Sanoid + Syncoid

**Sanoid** is a policy-driven snapshot management tool that uses OpenZFS for next-gen storage. It handles local snapshot creation and pruning based on configurable templates. **Syncoid**, bundled with Sanoid, handles replication to remote ZFS pools over SSH.

### Key Features

- **Template-based policies**: Define retention rules once, apply to many datasets
- **Flexible retention**: hourly, daily, weekly, monthly, yearly counts per dataset
- **Syncoid replication**: Efficient incremental replication with compression
- **Pre/post hooks**: Run commands before and after snapshot operations
- **Wide adoption**: Used by many ZFS-based NAS solutions including TrueNAS

### Docker Compose Deployment

While Sanoid is typically installed directly on the host (it needs ZFS kernel module access), you can run it in a privileged container with the ZFS device passed through:

```yaml
version: "3.8"
services:
  sanoid:
    image: alpine:latest
    container_name: sanoid
    privileged: true
    volumes:
      - /etc/sanoid:/etc/sanoid:ro
      - /usr/sbin:/usr/sbin:ro
      - /dev/zfs:/dev/zfs
      - /:/pool:ro
    command: >
      sh -c "
        apk add --no-cache perl zfs &&
        /usr/sbin/sanoid --cron
      "
    restart: "no"
```

### Configuration Example

```ini
[templates]
    frequent = 4
    hourly = 24
    daily = 30
    monthly = 3
    yearly = 1

[datastore/pool/docker]
    use_template = frequent

[datastore/pool/documents]
    use_template = hourly

[datastore/pool/media]
    use_template = daily

[datastore/pool/critical]
    use_template = hourly
    autosnap = yes
    autoprune = yes
```

Run syncoid to replicate snapshots to a remote server:

```bash
syncoid --recursive datastore/pool critical@backup-server:backup/pool
```

## zrepl

**zrepl** is a modern, Go-based ZFS replication tool that combines snapshot management and replication in a single binary. It supports push, pull, and sink replication models with built-in encryption and resumable transfers.

### Key Features

- **Three replication models**: Push (source-initiated), Pull (target-initiated), Sink (receive-only)
- **Native encryption**: TLS-based encryption for replication traffic
- **Resumable replication**: Checkpoint-based resume for interrupted transfers
- **Prometheus metrics**: Built-in monitoring and alerting
- **YAML configuration**: Declarative, version-controlled config
- **Filesystem placeholder**: Automatic placeholder creation on target

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  zrepl:
    image: ghcr.io/zrepl/zrepl:latest
    container_name: zrepl
    privileged: true
    volumes:
      - /etc/zrepl:/etc/zrepl:ro
      - /dev/zfs:/dev/zfs
      - /pool:/pool
    command: ["daemon"]
    ports:
      - "8888:8888"
    restart: unless-stopped
```

### Configuration Example

```yaml
global:
  logging:
    - type: syslog
      level: info
      format: human

jobs:
  - name: backup_pool
    type: push
    connect:
      type: tls
      address: "backup-server:8888"
      ca: "/etc/zrepl/ca.crt"
      cert: "/etc/zrepl/client.crt"
      key: "/etc/zrepl/client.key"
    replication:
      protection:
        initial:
          type: none
      encryption:
        plaintext: placeholder
    filesystems:
      "pool/<": true
      "pool/exclude": false
    snapshotting:
      type: periodic
      interval: 1h
      prefix: zrepl_
      timestamp_format: dense
    pruning:
      keep_sender:
        - type: not_replicated
        - type: last_n
          count: 10
        - type: daily
          count: 7
        - type: weekly
          count: 4
      keep_receiver:
        - type: grid
          grid: 1x1h(keep-all) | 24x1h | 35x1d | 6x30d
```

## zfs-auto-snapshot

**zfs-auto-snapshot** is the simplest of the three tools. It is a set of shell scripts designed to be called from cron, using ZFS filesystem properties to determine snapshot retention. It works by setting `com.sun:auto-snapshot` properties on datasets.

### Key Features

- **Cron-based execution**: Runs from standard cron entries
- **Property-driven**: Uses ZFS properties for per-dataset configuration
- **Minimal dependencies**: Pure shell scripts, no external packages needed
- **Labels**: Supports frequent, hourly, daily, weekly, monthly labels
- **Simple setup**: Install and add cron entries — done

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  zfs-auto-snapshot:
    image: alpine:latest
    container_name: zfs-auto-snapshot
    privileged: true
    volumes:
      - /dev/zfs:/dev/zfs
      - /pool:/pool
    command: >
      sh -c "
        apk add --no-cache zfs bash &&
        wget -O /usr/local/sbin/zfs-auto-snapshot https://raw.githubusercontent.com/zfsonlinux/zfs-auto-snapshot/master/src/zfs-auto-snapshot.sh &&
        chmod +x /usr/local/sbin/zfs-auto-snapshot &&
        zfs-auto-snapshot --quiet --syslog --label=hourly --keep=24 //
      "
    restart: "no"
```

### Cron Configuration

```bash
# /etc/cron.d/zfs-auto-snapshot
# Frequent snapshots (every 15 minutes, keep 4)
*/15 * * * * root zfs-auto-snapshot --quiet --syslog --label=frequent --keep=4 //

# Hourly snapshots (keep 24)
0 * * * * root zfs-auto-snapshot --quiet --syslog --label=hourly --keep=24 //

# Daily snapshots (keep 31)
@daily root zfs-auto-snapshot --quiet --syslog --label=daily --keep=31 //

# Weekly snapshots (keep 7)
@weekly root zfs-auto-snapshot --quiet --syslog --label=weekly --keep=7 //

# Monthly snapshots (keep 12)
@monthly root zfs-auto-snapshot --quiet --syslog --label=monthly --keep=12 //
```

Per-dataset control via ZFS properties:

```bash
# Disable auto-snapshot on a specific dataset
zfs set com.sun:auto-snapshot=false pool/exclude

# Keep only daily snapshots for this dataset
zfs set com.sun:auto-snapshot-frequent=false pool/media
zfs set com.sun:auto-snapshot-hourly=false pool/media
zfs set com.sun:auto-snapshot-daily=true pool/media
```

## Why Self-Host ZFS Snapshot Management?

Managing ZFS snapshots manually is error-prone and doesn't scale. When you have dozens of datasets — databases, application data, user home directories, media libraries — each with different retention requirements, manual snapshot management becomes a full-time job.

### Data Protection and Recovery

ZFS snapshots provide near-instantaneous recovery points. Unlike traditional backup tools that copy data block-by-block, ZFS snapshots are metadata operations that complete in milliseconds. This means you can snapshot frequently without impacting I/O performance.

Combined with zrepl's replication or Sanoid's syncoid, you get off-site copies that protect against hardware failure, ransomware, and accidental deletion. For compliance-driven environments, having daily, weekly, and monthly snapshots retained for years satisfies audit requirements.

### Cost Efficiency

ZFS is free and open-source. Running your own snapshot management on commodity hardware with ZFS costs a fraction of commercial backup solutions. The copy-on-write nature of ZFS means snapshots consume minimal additional storage — only changed blocks are duplicated. For a typical file server with 10 TB of data and 5% daily change rate, daily snapshots for a month consume roughly 1.5 TB, not 300 TB.

### Operational Simplicity

Policy-driven snapshot management removes the cognitive burden of remembering which datasets need which retention. Once configured, the tools handle creation and pruning automatically. zrepl's Prometheus integration means you can alert on failed replications before data loss occurs. Sanoid's template system means a single configuration change propagates to all matching datasets.

For storage infrastructure, see our [S3 object storage comparison](../2026-05-03-self-hosted-s3-object-storage-minio-seaweedfs-garage-guide/) and [cloud storage aggregator guide](../2026-04-30-alist-vs-rclone-vs-filestash-self-hosted-cloud-storage-aggregator-guide/). For backup verification strategies, our [backup integrity testing guide](../2026-04-19-self-hosted-backup-verification-testing-integrity-guide/) covers validation approaches.

## Choosing the Right ZFS Snapshot Manager

**Choose Sanoid** if you want the most widely adopted solution with a proven track record. Its template-based approach works well for environments with many datasets sharing similar retention needs. Pair it with syncoid for replication.

**Choose zrepl** if you need integrated snapshot management and replication with modern features like TLS encryption, resumable transfers, and Prometheus monitoring. Its YAML configuration and three replication models (push/pull/sink) make it ideal for complex topologies.

**Choose zfs-auto-snapshot** if you want the simplest possible setup. It requires no configuration file — just set ZFS properties and add cron entries. However, it does not handle replication, so you'll need a separate tool for off-site copies.

## FAQ

### Can these tools run on non-ZFS filesystems?
No. All three tools are specifically designed for OpenZFS and rely on ZFS-specific features like native snapshots, properties, and `zfs send/recv`. They will not work on ext4, XFS, or Btrfs.

### Do I need root access to run these tools?
Yes. ZFS snapshot and send/recv operations require root privileges (or equivalent ZFS delegation). The tools must run as root or with appropriate ZFS permissions granted via `zfs allow`.

### How much disk space do snapshots consume?
Snapshots consume space only for blocks that have changed since the snapshot was created. If your dataset has 1 TB of data and 5% changes daily, each daily snapshot consumes approximately 50 GB. Snapshots of unchanged datasets consume zero additional space.

### Can zrepl replicate encrypted ZFS datasets?
Yes. zrepl supports native ZFS encryption. When replicating encrypted datasets, zrepl can either preserve the encryption (sending encrypted data) or decrypt and re-encrypt at the target, depending on your configuration.

### What happens if a snapshot replication fails mid-transfer?
Sanoid/syncoid will restart the transfer from scratch on the next run. zrepl supports resumable replication — it checkpoints the transfer and resumes from the last successful block on the next attempt, saving bandwidth for large datasets.

### How do I monitor snapshot health?
Sanoid provides basic logging to syslog. zrepl exposes Prometheus metrics at its configured port (default 8888), allowing integration with Grafana or Alertmanager. zfs-auto-snapshot logs to syslog only.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted ZFS Snapshot Management: Sanoid vs zrepl vs zfs-auto-snapshot",
  "description": "Compare three open-source ZFS snapshot management tools — Sanoid, zrepl, and zfs-auto-snapshot — with Docker Compose configs, retention policies, and replication strategies.",
  "datePublished": "2026-05-20",
  "dateModified": "2026-05-20",
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
