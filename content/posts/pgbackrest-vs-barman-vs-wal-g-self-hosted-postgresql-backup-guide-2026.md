---
title: "pgBackRest vs Barman vs WAL-G: Self-Hosted PostgreSQL Backup Guide 2026"
date: 2026-04-18
tags: ["comparison", "guide", "self-hosted", "postgresql", "backup", "database"]
draft: false
description: "Compare pgBackRest, Barman, and WAL-G for self-hosted PostgreSQL backup. Learn installation, Docker setup, WAL archiving, and point-in-time recovery for production databases."
---

PostgreSQL is one of the most widely deployed open-source relational databases, powering everything from small web apps to enterprise data warehouses. But a database without a reliable backup strategy is a ticking time bomb. Hardware failures, accidental deletes, and corrupt migrations can destroy months or years of data in seconds.

This guide compares three of the most popular open-source PostgreSQL backup tools — **pgBackRest**, **Barman**, and **WAL-G** — and shows you how to deploy each one on your own infrastructure with [docker](https://www.docker.com/) and native packages.

> **Quick stats** (as of April 2026):
> - **pgBackRest**: 3,726 GitHub stars, written in C, last updated April 2026
> - **Barman**: 2,781 GitHub stars, written in Python, maintained by EDB/2ndQuadrant
> - **WAL-G**: 4,006 GitHub stars, written in Go, supports PostgreSQL, MySQL, Redis, and more

## Why You Need a Dedicated PostgreSQL Backup Tool

Running `pg_dump` on a cron schedule might seem sufficient for small databases, but it falls apart at production scale:

- **Locks and blocking**: `pg_dump` acquires shared locks that can slow down concurrent queries on busy databases.
- **No point-in-time recovery (PITR)**: Logical dumps capture a single snapshot. You cannot restore to an arbitrary moment between dumps.
- **Slow restores**: Importing a multi-gigabyte SQL dump takes far longer than replaying WAL (Write-Ahead Log) files.
- **No incremental backups**: Every `pg_dump` is a full copy, wasting storage and I/O.
- **No compression or encryption at rest**: Dump files sit on disk unprotected unless you add extra tooling.

Dedicated backup tools solve all of these problems by leveraging PostgreSQL's native **base backup** and **WAL archiving** mechanisms. They support incremental backups, parallel operations, compression, encryption, cloud storage backends, and most importantly, **point-in-time recovery** — letting you restore your database to any exact second.

For self-hosted PostgreSQL setups, proper backup infrastructure is just as critical as high availability. If you are running a clustered PostgreSQL deployment, see our [database high availability guide covering Patroni, Galera, and repmgr](../patroni-vs-galera-cluster-vs-repmgr-self-hosted-database-high-availability-guide-2026/) for clustering strategies that pair well with these backup solutions.

## pgBackRest — Reliable PostgreSQL Backup & Restore

[pgBackRest](https://pgbackrest.org/) is a mature, C-based backup tool designed specifically for PostgreSQL. It was originally created at Crunchy Data and has since become one of the most trusted backup solutions in the PostgreSQL ecosystem.

### Key Features

- **Parallel backup and restore** — uses multiple processes to speed up operations significantly
- **Incremental and differential backups** — only stores changed blocks since the last backup
- **Delta restore** — compares backup contents to the data directory and only restores changed files
- **Full and partial encryption** — encrypts backups at rest using OpenSSL
- **Multiple repository types** — local disk, S3-compatible object storage, Azure Blob, GCS
- ** stanza-based configuration** — manage multiple PostgreSQL clusters from a single backup server
- **Built-in WAL archiving** — no need for custom `archive_command` scripts

### Installation

On Debian/Ubuntu:

```bash
sudo apt update
sudo apt install pgbackrest
```

On RHEL/CentOS:

```bash
sudo yum install pgbackrest
```

### Docker Deployment

Run pgBackRest as a dedicated backup server alongside your PostgreSQL instance:

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:16
    container_name: pgbackrest_demo_db
    environment:
      POSTGRES_PASSWORD: changeme
      POSTGRES_DB: myapp
    volumes:
      - pg_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  pgbackrest:
    image: pgbackrest/pgbackrest:latest
    container_name: pgbackrest_server
    depends_on:
      - postgres
    volumes:
      - ./pgbackrest.conf:/etc/pgbackrest/pgbackrest.conf:ro
      - pgbackrest_repo:/var/lib/pgbackrest
      - ./backups:/backups
    environment:
      - PGBACKREST_REPO1_PATH=/backups
      - PGBACKREST_REPO1_TYPE=posix
    command: >
      bash -c "
      pgbackrest stanza-create --stanza=demo &&
      pgbackrest backup --stanza=demo --type=full
      "

volumes:
  pg_data:
  pgbackrest_repo:
```

### Configuration Example

A minimal `pgbackrest.conf` for a single PostgreSQL instance:

```ini
[demo]
pg1-path=/var/lib/postgresql/16/main

[global]
repo1-path=/backups
repo1-retention-full=4
repo1-retention-diff=7
process-max=4
compress-type=lz4
compress-level=6
log-level-console=info
log-level-file=detail
```

To create a backup:

```bash
pgbackrest --stanza=demo backup --type=full
pgbackrest --stanza=demo backup --type=diff
```

To restore:

```bash
pgbackrest --stanza=demo restore --type=time "--target=2026-04-15 14:30:00"
```

## Barman — Backup and Recovery Manager for PostgreSQL

[Barman](https://www.pgbarman.org/) is developed by **EnterpriseDB** (formerly 2ndQuadrant), one of the core contributors to PostgreSQL itself. Written in Python, Barman is designed for enterprise-grade backup management with a focus on centralized administration.

### Key Features

- **WAL streaming and archiving** — supports both `pg_basebackup` streaming and WAL file archiving
- **Point-in-time recovery** — restore to any precise moment using WAL replay
- **Retention policies** — automatic cleanup based on time or backup count
- **Multiple server management** — manage dozens of PostgreSQL servers from a single Barman host
- **Compression and encryption** — supports gzip, bzip2, and pigz compression
- **Catalog and listing** — built-in commands to browse backup history
- **Pre- and post-backup hooks** — run custom scripts before and after backup operations
- **Cloud integration** — supports AWS S3, Google Cloud Storage, and Azure Blob Storage via `barman-cloud`

### Installation

On Debian/Ubuntu:

```bash
sudo apt update
sudo apt install barman barman-cli
```

On RHEL/CentOS:

```bash
sudo yum install barman barman-cli
```

Via pip (for the latest version):

```bash
pip3 install barman
```

### Docker Deployment

Barman runs as a centralized backup server that connects to your PostgreSQL instances:

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:16
    container_name: barman_demo_db
    environment:
      POSTGRES_PASSWORD: changeme
      POSTGRES_DB: myapp
    volumes:
      - pg_data:/var/lib/postgresql/data
      - ./postgresql.conf:/etc/postgresql/postgresql.conf
    ports:
      - "5433:5432"
    command: >
      postgres -c wal_level=replica
               -c archive_mode=on
               -c "archive_command=/bin/true"
               -c max_wal_senders=4

  barman:
    image: eugene/barman:latest
    container_name: barman_server
    depends_on:
      - postgres
    volumes:
      - ./barman.conf:/etc/barman.d/barman.conf:ro
      - barman_data:/var/lib/barman
    ports:
      - "22:22"
    command: >
      bash -c "
      barman cron &&
      barman backup main
      "

volumes:
  pg_data:
  barman_data:
```

### Configuration Example

Barman's configuration lives in `/etc/barman.d/main.conf`:

```ini
[main]
description = "Main PostgreSQL Server"
conninfo = host=postgres user=barman dbname=myapp
streaming_conninfo = host=postgres user=streaming_barman
backup_method = postgres
streaming_wal = on
slot_name = barman
retention_policy_mode = auto
retention_policy = RECOVERY WINDOW OF 7 DAYS
wal_retention_policy = main
compression = gzip
```

Key commands:

```bash
# Check server status
barman show-server main

# List backups
barman list-backup main

# Create a backup
barman backup main

# Restore to a specific time
barman recover main 20260415T143000 /var/lib/postgresql/16/main --target-time "2026-04-15 14:30:00"

# Show WAL archive status
barman check main
```

## WAL-G — Cloud-Native Archival and Restoration

[WAL-G](https://github.com/wal-g/wal-g) is the successor to [WAL-E](https://github.com/wale/wal-e), rewritten in **Go** for better performance, concurrency, and multi-database support. Unlike pgBackRest and Barman, WAL-G is not PostgreSQL-exclusive — it also supports MySQL, Redis, MongoDB, and SQL Server.

### Key Features

- **Multi-database support** — PostgreSQL, MySQL/MariaDB, Redis, MongoDB, SQL Server, Greenplum, MariaDB, OrioleDB
- **Cloud-native storage** — native support for S3, Google Cloud Storage, Azure Blob, Swift, and SFTP
- **Incremental page-level backups** — only uploads changed pages, dramatically reducing storage and transfer time
- **LZ4, ZSTD, Brotli compression** — modern compression algorithms with excellent speed-to-size ratios
- **Parallel WAL upload/download** — leverages Go's goroutines for high-throughput operations
- **Permanent backups** — mark specific backups to prevent automatic retention cleanup
- **Simple, single-binary deployment** — no external dependencies, easy to containerize

### Installation

Download the latest binary from the [GitHub releases page](https://github.com/wal-g/wal-g/releases):

```bash
wget https://github.com/wal-g/wal-g/releases/download/v2.0.1/wal-g-pg-ubuntu-22.04-amd64
chmod +x wal-g-pg-ubuntu-22.04-amd64
sudo mv wal-g-pg-ubuntu-22.04-amd64 /usr/local/bin/wal-g
```

### Docker Deployment

WAL-G ships with a `docker-compose.yml` in its repository. Here is a simplified production-ready setup:

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:16
    container_name: walg_demo_db
    environment:
      POSTGRES_PASSWORD: changeme
      POSTGRES_DB: myapp
    volumes:
      - pg_data:/var/lib/postgresql/data
    ports:
      - "5434:5432"
    command: >
      postgres
        -c wal_level=replica
        -c archive_mode=on
        -c "archive_command=/usr/local/bin/wal-g wal-push %p --config /etc/wal-g/wal-g.json"
        -c archive_timeout=60

  walg:
    image: walg/wal-g:latest
    container_name: walg_backup
    depends_on:
      - postgres
    volumes:
      - ./walg-config.json:/etc/wal-g/wal-g.json:ro
      - walg_backups:/backups
    environment:[minio](https://min.io/)  - AWS_ACCESS_KEY_ID=minio
      - AWS_SECRET_ACCESS_KEY=minio123
      - AWS_ENDPOINT=http://minio:9000
      - AWS_S3_FORCE_PATH_STYLE=true
    command: wal-g backup-push /var/lib/postgresql/16/main

  minio:
    image: minio/minio:latest
    container_name: walg_minio
    environment:
      - MINIO_ROOT_USER=minio
      - MINIO_ROOT_PASSWORD=minio123
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"

volumes:
  pg_data:
  walg_backups:
  minio_data:
```

### Configuration Example

WAL-G uses a JSON configuration file:

```json
{
  "AWS_ENDPOINT": "http://minio:9000",
  "AWS_ACCESS_KEY_ID": "minio",
  "AWS_SECRET_ACCESS_KEY": "minio123",
  "AWS_S3_FORCE_PATH_STYLE": "true",
  "WALG_S3_PREFIX": "s3://postgresql-backups/demo",
 [ghost](https://ghost.org/)ATA": "/var/lib/postgresql/16/main",
  "PGHOST": "/var/run/postgresql",
  "PGUSER": "postgres",
  "WALG_COMPRESSION_METHOD": "lz4",
  "WALG_DELTA_MAX_STEPS": "6",
  "WALG_DISK_RATE_LIMIT": "52428800",
  "WALG_NETWORK_RATE_LIMIT": "104857600"
```

Key commands:

```bash
# Push a base backup
wal-g backup-push /var/lib/postgresql/16/main

# Push a WAL file (called by archive_command)
wal-g wal-push /var/lib/postgresql/16/main/pg_wal/000000010000000100000001

# List backups
wal-g backup-list

# Restore to the latest backup
wal-g backup-fetch /var/lib/postgresql/16/main LATEST

# Restore to a specific point in time
wal-g backup-fetch /var/lib/postgresql/16/main --target-time "2026-04-15T14:30:00"
```

## Comparison: pgBackRest vs Barman vs WAL-G

| Feature | pgBackRest | Barman | WAL-G |
|---------|-----------|--------|-------|
| **Language** | C | Python | Go |
| **GitHub Stars** | 3,726 | 2,781 | 4,006 |
| **License** | MIT | GPL-3.0 | Apache-2.0 |
| **Database Support** | PostgreSQL only | PostgreSQL only | PostgreSQL, MySQL, Redis, MongoDB, SQL Server |
| **Incremental Backup** | Yes (block-level) | Yes (via WAL streaming) | Yes (page-level) |
| **Parallel Operations** | Yes (configurable processes) | Limited | Yes (goroutines) |
| **Delta Restore** | Yes | No | No |
| **Point-in-Time Recovery** | Yes | Yes | Yes |
| **S3 Storage** | Yes | Yes (via barman-cloud) | Yes (native) |
| **Azure / GCS** | Yes | Yes | Yes |
| **Compression** | gzip, lz4, zstd | gzip, bzip2, pigz | lz4, zstd, brotli, pgzip |
| **Encryption at Rest** | Yes (OpenSSL) | No (relies on filesystem) | No (relies on S3 SSE) |
| **Docker Support** | Community images | eugene/barman, official | Official (walg/wal-g) |
| **Retention Policies** | Yes (time + count) | Yes (recovery window) | Yes (via FIND_FULL) |
| **Best For** | Single-cluster reliability | Enterprise multi-server | Cloud-native, multi-database |

## Which Tool Should You Choose?

### Choose pgBackRest if:
- You run a single PostgreSQL cluster and want the most battle-tested backup tool
- Delta restore is important for minimizing recovery time
- You need encryption at rest without relying on storage-level encryption
- You want parallel backup and restore with fine-grained process control

pgBackRest is the default choice for most self-hosted PostgreSQL deployments. It is well-documented, has a large user base, and integrates seamlessly with PostgreSQL's native streaming replication.

### Choose Barman if:
- You manage multiple PostgreSQL servers from a central backup host
- You want enterprise-grade tooling backed by EDB/2ndQuadrant
- Pre- and post-backup hooks are important for your workflow (e.g., sending notifications, triggering downstream jobs)
- You prefer Python-based tooling that is easy to extend and debug

Barman shines in environments with many PostgreSQL instances. Its centralized management model and `barman-cloud` suite make it ideal for organizations running dozens of database servers.

### Choose WAL-G if:
- You need backups for multiple database types (PostgreSQL + MySQL + Redis)
- You are deploying in a cloud-native environment with S3-compatible storage
- You want the simplest deployment model — a single Go binary with no external dependencies
- Page-level incremental backups are critical for large databases with low change rates

WAL-G is the modern, cloud-native option. Its Go implementation and multi-database support make it the most versatile of the three tools.

## Backup Strategy Best Practices

Regardless of which tool you choose, follow these principles:

1. **The 3-2-1 rule** — keep at least 3 copies of your data, on 2 different media types, with 1 copy off-site. For databases, this means local backups + cloud storage (S3/GCS).
2. **Test restores regularly** — a backup you have never restored is not a backup. Schedule monthly restore tests to a staging server.
3. **Monitor backup jobs** — set up alerts for failed backups, not just failed databases. Use monitoring tools to track backup completion and size. If you need database-level monitoring, check our [guide on pgWatch2, Percona PMM, and pgMonitor](../2026-04-18-pgwatch2-vs-percona-pmm-vs-pgmonitor-self-hosted-database-monitoring-guide-2026/).
4. **Set appropriate retention** — keep at least 4 full backups and 7 days of WAL files. Adjust based on your compliance requirements.
5. **Encrypt backups at rest** — especially when storing them in cloud object storage. pgBackRest provides built-in encryption; for WAL-G and Barman, use S3 server-side encryption or a MinIO gateway with encryption enabled.
6. **Separate backup server from database server** — store backups on a different physical or virtual machine to protect against single-point hardware failures.

For general-purpose file and server backups (outside of PostgreSQL), consider tools like Restic, Borg, or Kopia — see our [complete comparison of Restic vs Borg vs Kopia](../restic-vs-borg-vs-kopia-backup-guide/) for broader backup strategies.

## FAQ

### What is the difference between logical and physical PostgreSQL backups?

Logical backups (like `pg_dump`) export SQL statements that recreate your database schema and data. Physical backups copy the actual PostgreSQL data files and WAL segments. Logical backups are portable across PostgreSQL versions but slow to restore. Physical backups are fast to restore and support point-in-time recovery, but require the same (or newer) PostgreSQL version. pgBackRest, Barman, and WAL-G all use physical backups.

### Can I use these tools with PostgreSQL running in Docker?

Yes. All three tools work with containerized PostgreSQL. The key requirement is that the backup tool needs filesystem-level access to PostgreSQL's data directory (`$PGDATA`) and WAL directory (`pg_wal`). In Docker, mount these directories as named volumes or bind mounts that the backup container can also access. Alternatively, run the backup tool on the host machine and mount the Docker volumes from the host path.

### How much storage do I need for PostgreSQL backups?

A full backup requires roughly the same space as your PostgreSQL data directory. Incremental backups (differential or page-level) are typically 10-30% of a full backup size, depending on your write volume. WAL files accumulate at approximately the rate of your database writes. Plan for: **1 full backup + 7 days of WAL files + 3 differential backups** as a starting point.

### Which tool supports the fastest restore times?

pgBackRest generally offers the fastest restores due to its delta restore feature (only restoring changed blocks) and parallel restore capabilities. For a 500 GB database, pgBackRest with 8 parallel processes can restore in 15-30 minutes, compared to 1-2 hours for a traditional `pg_basebackup` restore. WAL-G's parallel WAL download also speeds up recovery, especially when fetching from cloud storage.

### Can I replicate backups to S3 or cloud storage?

All three tools support cloud storage. pgBackRest has native S3, Azure Blob, and GCS support with its repository abstraction. Barman uses `barman-cloud-wal-archive` and `barman-cloud-backup` commands for AWS S3 and Google Cloud Storage. WAL-G has first-class support for S3, GCS, Azure Blob, Swift, and SFTP — it was designed for cloud-native storage from the ground up.

### How do I automate backup scheduling?

Use cron on the backup server. For pgBackRest: `0 2 * * * pgbackrest --stanza=demo backup --type=diff`. For Barman: `0 2 * * * barman backup main` (or use Barman's built-in cron integration with `barman cron`). For WAL-G: schedule `wal-g backup-push` via cron or a systemd timer. Always stagger backup times across multiple servers to avoid I/O contention.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "pgBackRest vs Barman vs WAL-G: Self-Hosted PostgreSQL Backup Guide 2026",
  "description": "Compare pgBackRest, Barman, and WAL-G for self-hosted PostgreSQL backup. Learn installation, Docker setup, WAL archiving, and point-in-time recovery for production databases.",
  "datePublished": "2026-04-18",
  "dateModified": "2026-04-18",
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
