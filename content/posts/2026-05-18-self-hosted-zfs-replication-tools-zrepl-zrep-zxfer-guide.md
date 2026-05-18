---
title: "Self-Hosted ZFS Replication Tools — zrepl vs zrep vs zxfer (2026)"
date: "2026-05-18"
tags: ["zfs", "replication", "backup", "storage", "comparison", "self-hosted"]
draft: false
---

ZFS has become the gold standard for self-hosted storage, offering copy-on-write semantics, native snapshots, and end-to-end data integrity. But creating snapshots is only half the equation — getting those snapshots off your primary server to a remote location is what protects you from catastrophic failures. This guide compares three mature, open-source ZFS replication tools: **zrepl**, **zrep**, and **zxfer**.

## At a Glance: Comparison Table

| Feature | zrepl | zrep | zxfer |
|---|---|---|---|
| Language | Go | Shell (POSIX) | Shell (FreeBSD) |
| Stars | 1,137+ | 264+ | 130+ |
| Transport | SSH, TLS (native) | SSH (zfs send/recv) | SSH (zfs send/recv) |
| Replication Mode | Push, Pull, Sync | Push only | Push only |
| Scheduling | Cron-style, daemon | Manual or cron | Manual or cron |
| Encryption | Native TLS | SSH tunnel | SSH tunnel |
| Pruning | Per-policy rules | Snapshot naming | Manual |
| Resume Support | Yes (resumable send) | Partial | No |
| Monitoring | Prometheus metrics | None | None |
| FreeBSD Support | Yes | Yes | Native (FreeBSD-origin) |
| Linux Support | Yes | Yes | Limited |
| Web UI | No (CLI + Prometheus) | No | No |
| Docker Deployment | Yes (official image) | No | No |
| Active Development | Very Active (2026) | Moderate | Active (2025) |
| License | MIT | BSD | BSD |

## zrepl: The Modern All-in-One Solution

[zrepl](https://github.com/zrepl/zrepl) is the most feature-complete ZFS replication tool available today. Written in Go, it runs as a daemon and supports push, pull, and sync replication modes with native TLS encryption, resumable sends, and Prometheus metrics.

### Key Features

- **Multiple replication modes**: Push (source-initiated), Pull (sink-initiated), and Sync (bidirectional)
- **Native TLS transport**: No need for SSH tunnels — zrepl handles its own encrypted connections
- **Resumable sends**: If a replication job is interrupted, zrepl can resume from where it left off using ZFS's native `zfs receive -s`
- **Flexible pruning policies**: Define retention rules per-snapshot using time-based or count-based policies
- **Prometheus integration**: Built-in metrics endpoint for monitoring replication lag, throughput, and errors

### Docker Compose Configuration

zrepl provides an official Docker image. Here is a production-ready setup:

```yaml
services:
  zrepl-source:
    image: ghcr.io/zrepl/zrepl:latest
    container_name: zrepl-source
    restart: unless-stopped
    privileged: true
    network_mode: host
    volumes:
      - /etc/zrepl:/etc/zrepl:ro
      - /var/run/zrepl:/var/run/zrepl
      - /tank:/tank  # Mount the ZFS pool you want to replicate
    command: ["zrepl", "daemon"]

  zrepl-sink:
    image: ghcr.io/zrepl/zrepl:latest
    container_name: zrepl-sink
    restart: unless-stopped
    privileged: true
    network_mode: host
    volumes:
      - /etc/zrepl:/etc/zrepl:ro
      - /var/run/zrepl:/var/run/zrepl
      - /backup-pool:/backup-pool  # Destination ZFS pool
    command: ["zrepl", "daemon"]
```

### zrepl Configuration Example

```yaml
# /etc/zrepl/zrepl.yml
global:
  logging:
    - type: syslog
      format: json
      level: info

jobs:
  - name: daily_backup
    type: push
    connect:
      type: tls
      address: "backup-server:8888"
      ca: /etc/zrepl/ca.crt
      cert: /etc/zrepl/client.crt
      key: /etc/zrepl/client.key
    filesystems:
      "tank/data<": true
      "tank/home<": true
    snapshot:
      type: periodic
      interval: 1h
      prefix: zrepl_
    pruning:
      keep_sender:
        - type: not_replicated
        - type: last_n
          count: 5
        - type: regex
          regex: "^manual_.*"
          keep: true
      keep_receiver:
        - type: grid
          grid: 1x1h(keep=all) | 24x1h | 30x1d | 6x30d
```

## zrep: The Battle-Tested Shell Script

[zrep](https://github.com/bolthole/zrep) is a POSIX shell script that has been managing ZFS replication for over a decade. It wraps `zfs send` and `zfs receive` in a simple, reliable wrapper with failover support.

### Key Features

- **Zero dependencies**: Pure shell script — runs on any POSIX-compliant system with ZFS
- **Failover capability**: Built-in `zrep failover` command for promoting the replica to primary
- **Simple snapshot naming**: Uses a consistent naming convention (`zrep_*`) that makes it easy to identify replicated snapshots
- **Initial and incremental sends**: Automatically determines whether to do a full or incremental replication
- **Cross-platform**: Works identically on FreeBSD, Linux, and macOS (with ZFS on Linux)

### Installation and Setup

```bash
# Install zrep on both source and destination
curl -fsSL https://raw.githubusercontent.com/bolthole/zrep/master/zrep -o /usr/local/bin/zrep
chmod +x /usr/local/bin/zrep

# Initialize replication for a dataset
zrep init tank/data backup-server:backup-pool/data

# Manual replication
zrep sync tank/data

# Check replication status
zrep status tank/data
```

### Automated Replication with Cron

```bash
# /etc/cron.d/zrep
# Replicate tank/data every 6 hours
0 */6 * * * root /usr/local/bin/zrep sync tank/data >> /var/log/zrep.log 2>&1
```

## zxfer: The FreeBSD-Native Replicator

[zxfer](https://github.com/allanjude/zxfer) originated in FreeBSD and is specifically designed for ZFS snapshot replication with a focus on simplicity and reliability. It is the tool used by TrueNAS (formerly FreeNAS) for its replication features.

### Key Features

- **TrueNAS integration**: zxfer is the replication engine behind TrueNAS, battle-tested in thousands of deployments
- **Recursive replication**: Handles nested datasets automatically with proper snapshot ordering
- **Compression support**: Can compress data in-flight using gzip or lz4
- **Bandwidth limiting**: Built-in `-b` flag for throttling replication bandwidth
- **Verbose logging**: Detailed output for troubleshooting replication issues

### Installation and Usage

```bash
# Install on FreeBSD
pkg install zxfer

# Or on Linux (from source)
git clone https://github.com/allanjude/zxfer.git
cd zxfer
make && make install

# Basic replication command
zxfer -dFkv -P tank/data backup-server:/backup-pool/data

# With bandwidth limit (10 MB/s)
zxfer -dFkvb 10m -P tank/data backup-server:/backup-pool/data

# Dry run (preview what would be sent)
zxfer -nv -P tank/data backup-server:/backup-pool/data
```

### Automated Replication

```bash
# /etc/cron.d/zxfer
# Replicate every 4 hours
0 */4 * * * root /usr/local/bin/zxfer -dFkv -P tank/data backup-server:/backup-pool/data >> /var/log/zxfer.log 2>&1
```

## Choosing the Right ZFS Replication Tool

### Use zrepl when:
- You need **push, pull, or bidirectional** replication
- You want **native TLS** without managing SSH keys
- You need **resumable sends** for large initial transfers over unreliable connections
- You want **Prometheus monitoring** for replication health dashboards
- You prefer a **modern, actively maintained** daemon with regular releases

### Use zrep when:
- You want a **simple, dependency-free** shell script
- You need **failover capability** for disaster recovery
- You prefer **transparent commands** that map directly to `zfs send/recv`
- Your team is comfortable with **shell scripting** and cron jobs
- You run a **mixed FreeBSD/Linux** environment and want identical tooling

### Use zxfer when:
- You are running **FreeBSD or TrueNAS** natively
- You need **recursive dataset replication** with proper ordering
- You want **bandwidth throttling** built in
- You prefer a **minimal, focused tool** that does one thing well
- You value the **TrueNAS pedigree** — proven in enterprise NAS deployments

## Why Self-Host Your ZFS Replication?

Running your own ZFS replication infrastructure gives you complete control over your data lifecycle. Unlike cloud backup services that charge per-gigabyte for egress and storage, self-hosted replication uses hardware you already own. For organizations managing terabytes of data, this translates to significant cost savings over time.

ZFS replication also ensures your backups are **instantly consistent** — thanks to copy-on-write semantics, every snapshot is a crash-consistent point-in-time copy. When combined with encrypted replication streams (via zrepl's native TLS or SSH tunnels for zrep/zxfer), your data is protected both in transit and at rest.

For teams managing distributed infrastructure, the ability to replicate ZFS datasets across data centers or edge locations provides geographic redundancy without vendor lock-in. This is especially valuable for self-hosted services where data sovereignty and compliance requirements prohibit storing backups on third-party infrastructure.

For related reading, see our [encrypted backup comparison](../2026-04-22-duplicati-vs-duplicacy-vs-duplicity-self-hosted-encrypted-backup-2026/) and [data replication guide](../2026-04-26-symmetricds-vs-debezium-vs-canal-self-hosted-data-replication-guide-2026/). If you are managing ZFS snapshots locally, our [ZFS snapshot tools comparison](../sanoid-vs-znapzend-vs-syncoid-zfs-snapshot-replication-guide-2026/) covers the complementary side of the workflow.

## FAQ

### What is ZFS replication and why do I need it?

ZFS replication is the process of copying ZFS snapshots from one system to another using `zfs send` and `zfs receive`. This creates an exact copy of your data on a remote system, protecting against hardware failures, ransomware, and site-level disasters. Unlike file-level backups, ZFS replication preserves all filesystem metadata, properties, and snapshot history.

### Can I replicate ZFS datasets over the internet?

Yes, all three tools support replication over the internet. zrepl uses native TLS encryption, while zrep and zxfer rely on SSH tunnels. For large datasets over high-latency links, zrepl's resumable send feature is particularly valuable since it can recover from connection interruptions without restarting the entire transfer.

### How do I handle initial replication of large datasets?

Initial replication of terabyte-scale datasets can take hours or days. Use zrepl's resumable sends (`zfs receive -s`) so that if the connection drops, the next sync picks up where it left off. Alternatively, physically transport the drives (sneakernet) for the initial copy, then use incremental replication for ongoing syncs.

### Can I replicate only specific snapshots?

Yes. zrepl's pruning policies let you define exactly which snapshots to keep on both the sender and receiver. zrep replicates all snapshots with the `zrep_*` prefix. zxfer replicates all snapshots unless you use the `-s` flag to specify a particular snapshot name.

### Do these tools support encryption?

zrepl supports native TLS encryption for its replication connections. zrep and zxfer both use SSH as their transport, which provides encryption by default. For additional security, you can also enable ZFS native encryption on the sending filesystem, which encrypts data before it leaves the source system.

### Can I use these tools with TrueNAS?

TrueNAS uses zxfer internally for its built-in replication tasks. You can also install zrepl as a plugin or in a jail on TrueNAS for more advanced replication features like push/pull modes and Prometheus monitoring. zrep works on TrueNAS but is not officially supported.

### How often should I replicate my ZFS datasets?

Replication frequency depends on your Recovery Point Objective (RPO). For critical data, zrepl can replicate as frequently as every minute. For most self-hosted setups, every 1-6 hours provides a good balance between data protection and resource usage. Schedule replications during off-peak hours to minimize impact on production workloads.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted ZFS Replication Tools — zrepl vs zrep vs zxfer (2026)",
  "description": "Compare three open-source ZFS replication tools: zrepl, zrep, and zxfer. Features comparison table, Docker configs, and deployment guides for self-hosted storage backup.",
  "datePublished": "2026-05-18",
  "dateModified": "2026-05-18",
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
