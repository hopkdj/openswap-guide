---
title: "Percona XtraBackup vs MyDumper vs MariaDB Backup: Best MySQL Backup Strategy 2026"
date: 2026-04-22
tags: ["comparison", "guide", "self-hosted", "database", "backup", "mysql", "mariadb"]
draft: false
description: "Compare Percona XtraBackup, MyDumper, and MariaDB Backup for self-hosted MySQL and MariaDB databases. Includes Docker setup, backup scripts, and restore procedures."
---

If you run MySQL or MariaDB in production — whether on bare metal, in Docker containers, or inside Kubernetes — you need a reliable backup strategy. The built-in `mysqldump` utility is fine for small databases, but it becomes unacceptably slow and locks tables once you cross a few gigabytes.

Three open-source tools dominate the self-hosted MySQL/MariaDB backup landscape: **Percona XtraBackup**, **MyDumper**, and **MariaDB Backup** (mariabackup). Each takes a fundamentally different approach, and the right choice depends on your database engine, size, and recovery time objectives.

This guide covers installation, Docker deployment, backup and restore procedures, and a detailed comparison to help you pick the right tool.

For related backup reading, see our [general backup tools comparison](../restic-vs-borg-vs-kopia-backup-guide/) and the [PostgreSQL backup guide](../pgbackrest-vs-barman-vs-wal-g-self-hosted-postgresql-backup-guide/).

## Why Self-Hosted MySQL Backups Matter

Database backups are your last line of defense against data loss. Whether you face hardware failure, accidental `DROP TABLE` statements, ransomware, or migration between servers, having tested backups is non-negotiable.

Self-hosted backup tools give you three advantages over managed cloud solutions:

- **Full data sovereignty** — your backups never leave your infrastructure
- **No vendor lock-in** — backup files are standard formats you control
- **Cost predictability** — no per-GB storage fees from cloud providers

For a complete backup reliability strategy, check out our [backup verification and testing guide](../2026-04-19-self-hosted-backup-verification-testing-integrity-guide/) to ensure your backups are actually restorable.

## How Each Tool Works

The fundamental difference lies in backup methodology: **physical** vs **logical**.

### Physical Backups (Percona XtraBackup, MariaDB Backup)

Physical backup tools copy the actual database data files at the block level. They operate directly on the InnoDB/XtraDB storage engine files (`.ibd`, `.ibdata1`) without going through the SQL layer.

Key characteristics:
- Fast — limited only by disk I/O throughput
- Non-blocking — InnoDB hot backups work while the server handles queries
- Full backup only — you cannot restore individual tables from a physical backup
- Size matches the actual data on disk

### Logical Backups (MyDumper)

Logical backup tools export data by executing `SELECT` queries against the database and writing the results as SQL statements (or other formats). MyDumper does this in parallel across multiple threads.

Key characteristics:
- Slower — goes through the SQL execution engine
- Granular — you can restore individual databases or tables
- Cross-version compatible — logical dumps can be restored on different MySQL/MariaDB versions
- Cross-engine — works with any storage engine (InnoDB, MyISAM, Aria)

## Quick Comparison Table

| Feature | Percona XtraBackup | MyDumper | MariaDB Backup |
|---|---|---|---|
| **Backup type** | Physical (hot) | Logical (parallel) | Physical (hot) |
| **Latest version** | 8.4.0 | v1.0.0 | 12.2.2 (bundled) |
| **GitHub stars** | 1,516 | 3,119 | 7,482 (MariaDB/server) |
| **Language** | C++ | C | C/C++ |
| **MySQL support** | MySQL 8.0, 8.4 | MySQL 5.7, 8.0, 8.4 | MySQL 5.7, 8.0 |
| **MariaDB support** | MariaDB 10.4+ | MariaDB 10.3+ | MariaDB 10.1+ (native) |
| **InnoDB** | Yes | Yes | Yes |
| **MyISAM** | Partial (FTWRL) | Yes | Yes |
| **Aria engine** | No | Yes | Yes |
| **Parallel backup** | No (single stream) | Yes (configurable threads) | No (single stream) |
| **Parallel restore** | No | Yes (myloader) | No |
| **Incremental backup** | Yes | No | Yes |
| **Point-in-time recovery** | With binary logs | No | With binary logs |
| **Individual table restore** | No | Yes | No |
| **Compressed backups** | Yes (qpress, xbstream) | Yes (gzip, zstd) | Yes (qpress, xbstream) |
| **Docker image** | `percona/percona-xtrabackup` | `mydumper/mydumper` | Part of `mariadb` image |
| **Best for** | Large databases, minimal downtime | Selective restore, migration | MariaDB environments |

## Percona XtraBackup: Installation and Usage

Percona XtraBackup is the most widely adopted physical backup tool for MySQL and MariaDB. It creates non-blocking hot backups of InnoDB and XtraDB databases by reading data pages directly from the storage engine.

### Installation on Linux

```bash
# Debian/Ubuntu
apt update && apt install -y percona-xtrabackup-84

# RHEL/CentOS/AlmaLinux
dnf install -y percona-xtrabackup-84
```

### Docker Deployment

Percona provides an official Docker image with ~904,000 pulls:

```yaml
version: "3.8"
services:
  xtrabackup:
    image: percona/percona-xtrabackup:8.4.0-5
    container_name: xtrabackup
    volumes:
      - mysql-data:/var/lib/mysql:ro
      - ./backups:/backups
    environment:
      - MYSQL_ROOT_PASSWORD=your-root-password
    network_mode: host
    entrypoint: ["xtrabackup", "--backup",
                 "--target-dir=/backups/full",
                 "--host=127.0.0.1",
                 "--user=root",
                 "--password=your-root-password"]

volumes:
  mysql-data:
    external: true
```

### Taking a Full Backup

```bash
# Full backup to /backups/full
xtrabackup --backup \
  --target-dir=/backups/full \
  --user=root \
  --password=your-password

# Prepare the backup (make it consistent for restore)
xtrabackup --prepare \
  --target-dir=/backups/full

# Copy back to MySQL data directory
# IMPORTANT: Stop MySQL first
systemctl stop mysql
rm -rf /var/lib/mysql/*
xtrabackup --copy-back \
  --target-dir=/backups/full
chown -R mysql:mysql /var/lib/mysql
systemctl start mysql
```

### Incremental Backups

```bash
# Base full backup
xtrabackup --backup \
  --target-dir=/backups/base \
  --user=root --password=your-password

# First incremental (based on full backup)
xtrabackup --backup \
  --target-dir=/backups/inc1 \
  --incremental-basedir=/backups/base \
  --user=root --password=your-password

# Second incremental (based on first incremental)
xtrabackup --backup \
  --target-dir=/backups/inc2 \
  --incremental-basedir=/backups/inc1 \
  --user=root --password=your-password

# Prepare: apply full, then each incremental in order
xtrabackup --prepare --apply-log-only --target-dir=/backups/base
xtrabackup --prepare --apply-log-only --target-dir=/backups/base --incremental-dir=/backups/inc1
xtrabackup --prepare --target-dir=/backups/base --incremental-dir=/backups/inc2
```

### Compressed Backups

```bash
# Backup with streaming compression
xtrabackup --backup \
  --stream=xbstream \
  --compress \
  --target-dir=/backups/full \
  --user=root --password=your-password \
  > /backups/full_backup.xbstream

# Decompress and extract
xbstream -x < /backups/full_backup.xbstream -C /backups/extracted/
xtrabackup --decompress --target-dir=/backups/extracted/
```

## MyDumper/MyLoader: Installation and Usage

MyDumper is a logical backup tool that exports MySQL data in parallel using multiple threads. It produces one file per table, making it easy to restore individual tables or databases. The companion tool, myloader, reads the backup and imports it in parallel.

### Installation on Linux

```bash
# Debian/Ubuntu
apt update && apt install -y mydumper

# RHEL/CentOS/AlmaLinux (requires EPEL)
dnf install -y epel-release
dnf install -y mydumper

# Build from source (for latest version)
apt install -y build-essential cmake libglib2.0-dev libmysqlclient-dev \
  zlib1g-dev libpcre3-dev libssl-dev
git clone https://github.com/mydumper/mydumper.git
cd mydumper
mkdir build && cd build
cmake ..
make -j$(nproc)
make install
```

### Docker Deployment

```yaml
version: "3.8"
services:
  mydumper:
    image: mydumper/mydumper:latest
    container_name: mydumper
    volumes:
      - ./backups:/backups
    network_mode: host
    entrypoint: ["mydumper",
                 "--host=127.0.0.1",
                 "--user=root",
                 "--password=your-root-password",
                 "--outputdir=/backups",
                 "--threads=4",
                 "--compress",
                 "--compress-protocol"]

volumes:
  backup-data:
    driver: local
```

### Taking a Backup

```bash
# Basic parallel backup with 4 threads and compression
mydumper --host=127.0.0.1 \
  --user=root \
  --password=your-password \
  --outputdir=/backups/full \
  --threads=4 \
  --compress

# Backup specific databases only
mydumper --host=127.0.0.1 \
  --user=root \
  --password=your-password \
  --outputdir=/backups/specific \
  --threads=4 \
  --compress \
  --database=myapp_db

# Backup with regex table filter (exclude log tables)
mydumper --host=127.0.0.1 \
  --user=root \
  --password=your-password \
  --outputdir=/backups/filtered \
  --threads=4 \
  --compress \
  --regex='^(?!(mysql\.|performance_schema\.|.*_log$))'
```

### Restoring with MyLoader

```bash
# Restore the entire backup in parallel
myloader --host=127.0.0.1 \
  --user=root \
  --password=your-password \
  --directory=/backups/full \
  --threads=4 \
  --compress-protocol

# Restore into a different database
myloader --host=127.0.0.1 \
  --user=root \
  --password=your-password \
  --directory=/backups/full \
  --threads=4 \
  --database=new_db_name

# Restore with overwrite (drops existing tables)
myloader --host=127.0.0.1 \
  --user=root \
  --password=your-password \
  --directory=/backups/full \
  --threads=4 \
  --overwrite-tables
```

## MariaDB Backup (mariabackup): Installation and Usage

MariaDB Backup (mariabackup) is a fork of Percona XtraBackup 2.3, maintained by the MariaDB team as part of the MariaDB Server distribution. It supports MariaDB-specific storage engines like Aria and is optimized for MariaDB's latest features.

### Installation

```bash
# mariabackup ships with MariaDB Server packages
apt update && apt install -y mariadb-backup
# or on RHEL-family:
dnf install -y MariaDB-backup
```

### Docker Deployment

mariabackup is bundled with the official MariaDB Docker image:

```yaml
version: "3.8"
services:
  mariadb:
    image: mariadb:12.2
    container_name: mariadb-primary
    environment:
      MARIADB_ROOT_PASSWORD: your-root-password
    volumes:
      - mariadb-data:/var/lib/mysql
    ports:
      - "3306:3306"

  mariabackup:
    image: mariadb:12.2
    container_name: mariabackup-runner
    volumes:
      - mariadb-data:/var/lib/mysql:ro
      - ./backups:/backups
    environment:
      MARIADB_ROOT_PASSWORD: your-root-password
    depends_on:
      - mariadb
    command: >
      mariabackup --backup
      --target-dir=/backups/full
      --host=mariadb-primary
      --user=root
      --password=your-root-password

volumes:
  mariadb-data:
```

### Taking a Full Backup

```bash
# Full backup
mariabackup --backup \
  --target-dir=/backups/full \
  --user=root \
  --password=your-password

# Prepare (apply redo log)
mariabackup --prepare \
  --target-dir=/backups/full

# Restore
systemctl stop mariadb
rm -rf /var/lib/mysql/*
mariabackup --copy-back \
  --target-dir=/backups/full
chown -R mysql:mysql /var/lib/mysql
systemctl start mariadb
```

### Incremental Backups

```bash
# Base backup
mariabackup --backup \
  --target-dir=/backups/base \
  --user=root --password=your-password

# Incremental
mariabackup --backup \
  --target-dir=/backups/inc1 \
  --incremental-basedir=/backups/base \
  --user=root --password=your-password

# Prepare chain
mariabackup --prepare --apply-log-only --target-dir=/backups/base
mariabackup --prepare --target-dir=/backups/base --incremental-dir=/backups/inc1
```

### Streaming to Remote Server

```bash
# Stream backup over SSH to remote server
mariabackup --backup \
  --stream=xbstream \
  --target-dir=/tmp \
  --user=root --password=your-password | \
  ssh backup-server "xbstream -x -C /remote/backups/"
```

## Performance Comparison

Performance varies significantly based on database size and hardware. Here are representative benchmarks for a 50 GB InnoDB database on SSD storage:

| Operation | Percona XtraBackup | MyDumper (4 threads) | MariaDB Backup |
|---|---|---|---|
| **Full backup time** | ~3 min | ~12 min | ~3 min |
| **Backup size** | ~50 GB (raw) | ~28 GB (compressed SQL) | ~50 GB (raw) |
| **Full restore time** | ~5 min | ~18 min | ~5 min |
| **Incremental support** | Yes | No | Yes |
| **Impact on server during backup** | Minimal (I/O increase) | Moderate (CPU + queries) | Minimal (I/O increase) |
| **Network bandwidth (streamed)** | High (raw data) | Low (compressed SQL) | High (raw data) |

**Key takeaway**: For databases over 100 GB, physical backup tools (XtraBackup, mariabackup) are significantly faster. For databases under 10 GB where you need selective restore, MyDumper provides more flexibility.

## Backup Strategy Recommendations

### Small Databases (< 10 GB)
Use **MyDumper** with 4 threads and compression. The logical format gives you per-table restore capability, and the backup size is manageable.

```bash
# Daily full backup with compression
mydumper --host=127.0.0.1 \
  --user=backup_user \
  --password=backup_pass \
  --outputdir="/backups/$(date +%Y-%m-%d)" \
  --threads=4 \
  --compress \
  --build-empty-files
```

### Medium Databases (10–100 GB)
Use **Percona XtraBackup** with weekly full backups and daily incrementals. This balances speed with storage efficiency.

```bash
# Weekly full backup (Sunday)
xtrabackup --backup --target-dir=/backups/weekly/$(date +%Y-%m-%d)

# Daily incremental (Mon-Sat)
xtrabackup --backup \
  --target-dir=/backups/daily/$(date +%Y-%m-%d) \
  --incremental-basedir=/backups/weekly/$(date -d "last sunday" +%Y-%m-%d)
```

### MariaDB-Only Environments
Use **mariabackup**. It is bundled with MariaDB, supports Aria engine, and receives updates in lockstep with the server.

### Large Databases (> 100 GB)
Use **Percona XtraBackup** with streaming compression to a remote backup server. Incremental backups are essential to minimize I/O impact.

## Which Tool Should You Choose?

| Scenario | Recommended Tool | Reason |
|---|---|---|
| MySQL 8.4, large DB | Percona XtraBackup | Fastest physical backup, incremental support |
| MariaDB production | MariaDB Backup | Native support, Aria engine compatibility |
| Need per-table restore | MyDumper | Logical backup with individual table files |
| Cross-version migration | MyDumper | Logical dump works across MySQL/MariaDB versions |
| Minimal storage budget | MyDumper | Compressed SQL is typically 40-60% of raw size |
| Point-in-time recovery | XtraBackup or mariabackup | Combine with binary log replay |
| MariaDB + MySQL mixed | Percona XtraBackup | Supports both MySQL and MariaDB |

## FAQ

### What is the difference between physical and logical MySQL backups?

Physical backups copy the actual database data files at the block level (`.ibd`, `.ibdata1`). They are fast and non-blocking but require the full dataset to be restored. Logical backups export data as SQL statements through the database engine, making them slower but allowing individual table restoration and cross-version compatibility.

### Can I use Percona XtraBackup with MariaDB?

Yes. Percona XtraBackup 8.4 supports MariaDB 10.4 and later. However, for MariaDB-specific storage engines like Aria, you should use mariabackup instead, as XtraBackup only supports InnoDB and XtraDB engines.

### Does MyDumper support incremental backups?

No. MyDumper only supports full logical backups. Each backup exports the entire selected dataset. If you need incremental backups, use Percona XtraBackup or mariabackup, both of which support incremental backup chains.

### How do I automate MySQL backups with cron?

```bash
# Add to crontab (crontab -e)
# Daily full backup at 2 AM
0 2 * * * /usr/local/bin/mydumper --host=127.0.0.1 --user=backup --password=pass \
  --outputdir="/backups/$(date +\%Y-\%m-\%d)" --threads=4 --compress

# Weekly cleanup: delete backups older than 30 days
0 3 * * 0 find /backups -type d -mtime +30 -exec rm -rf {} +
```

### Which tool is fastest for restoring a single table?

MyDumper. Since it exports each table as a separate SQL file, you can restore a single table by running `myloader` on just that file. Physical backup tools (XtraBackup, mariabackup) require restoring the entire database, then extracting the needed table.

### Can I back up a running MySQL server without locking tables?

Yes, but only for InnoDB/XtraDB tables with physical backup tools. Percona XtraBackup and mariabackup use InnoDB's crash recovery mechanism to create consistent hot backups without blocking writes. MyDumper briefly acquires a global read lock (FTWRL) to establish a consistent snapshot, which blocks writes for a few seconds.

### How do I encrypt MySQL backups?

For XtraBackup and mariabackup, use `--encrypt=AES256` with `--encrypt-key` or `--encrypt-key-file`:

```bash
xtrabackup --backup \
  --target-dir=/backups/encrypted \
  --encrypt=AES256 \
  --encrypt-key-file=/etc/backup/encrypt.key
```

For MyDumper, pipe the output through GPG:
```bash
mydumper --outputdir=/tmp/dump --threads=4
tar czf - -C /tmp/dump . | gpg --symmetric --cipher-algo AES256 > backup.tar.gz.gpg
```

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Percona XtraBackup vs MyDumper vs MariaDB Backup: Best MySQL Backup Strategy 2026",
  "description": "Compare Percona XtraBackup, MyDumper, and MariaDB Backup for self-hosted MySQL and MariaDB databases. Includes Docker setup, backup scripts, and restore procedures.",
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
