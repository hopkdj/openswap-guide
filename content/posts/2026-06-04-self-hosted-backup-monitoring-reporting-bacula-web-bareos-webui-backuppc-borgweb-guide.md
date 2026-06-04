---
title: "Self-Hosted Backup Monitoring & Reporting: Bacula-Web vs Bareos-WebUI vs BackupPC-Web vs BorgWeb"
date: "2026-06-04"
tags: ["backup", "monitoring", "bacula", "bareos", "backuppc", "borgbackup", "self-hosted", "devops", "infrastructure", "reporting"]
draft: false
---

## Introduction

Running backups is only half the battle — knowing whether they actually succeeded, how much data was protected, and when the last successful run occurred is equally critical. A backup system without monitoring is a disaster waiting to happen. Silent failures in backup jobs can go unnoticed for weeks or months, only discovered when you actually need to restore.

This article compares four open-source backup monitoring and reporting solutions: Bacula-Web (for Bacula environments), Bareos-WebUI (for Bareos deployments), BackupPC-Web (integrated with BackupPC), and BorgWeb (for BorgBackup repositories). Each provides a web-based dashboard for tracking backup job status, data growth trends, and storage utilization.

## Comparison Table

| Feature | Bacula-Web | Bareos-WebUI | BackupPC-Web | BorgWeb |
|---------|------------|--------------|--------------|---------|
| **Backup Engine** | Bacula Community/Enterprise | Bareos (Bacula fork) | BackupPC | BorgBackup |
| **Architecture** | PHP + MySQL/SQLite | PHP + Zend Framework + MySQL | Perl CGIs + built-in | Python/Flask + Borg repo |
| **Job Monitoring** | Real-time job status with graphs | Real-time job overview | Per-host status with history | Repository-level statistics |
| **Visualizations** | Volume graphs, job duration, throughput | Volume graphs, job statistics | Host status, pool usage | Dedup ratio, repo growth |
| **Alerting** | Email on job failure | Email on job failure | Email + per-host config | Custom via scripts |
| **Multi-Admin** | User roles and permissions | LDAP/AD integration | Per-host admin access | Read-only by default |
| **REST API** | Limited (status endpoint) | Via Bareos Director API | Internal CGI API | Borg JSON API |
| **Docker Support** | Community images available | Official Bareos Docker | Docker Compose available | Official borgmatic + BorgWeb |
| **License** | GPL v2 | AGPL v3 | GPL v2 | BSD |
| **GitHub Stars** | 254+ | N/A (part of Bareos) | N/A (SourceForge) | N/A (BorgBackup: 11,825+) |

## Bacula-Web

Bacula-Web is a PHP-based web interface that provides monitoring, reporting, and visualization for Bacula backup environments. It reads directly from the Bacula catalog database (MySQL, PostgreSQL, or SQLite) and generates comprehensive dashboards.

**Key features:**
- Real-time job status dashboard with color-coded status indicators
- Historical graphs showing backup volumes, job durations, and throughput
- Per-client backup statistics with last-run timestamps
- Pool and volume utilization tracking for tape/disk storage
- Multi-user access with role-based permissions
- LDAP authentication support
- REST API endpoint for integration with external monitoring systems

**Docker Compose deployment:**

```yaml
version: '3'
services:
  bacula-web:
    image: bacula/bacula-web:latest
    container_name: bacula-web
    restart: unless-stopped
    ports:
      - "9090:80"
    environment:
      - BACULA_WEB_DB_TYPE=mysql
      - BACULA_WEB_DB_HOST=bacula-db
      - BACULA_WEB_DB_NAME=bacula
      - BACULA_WEB_DB_USER=bacula
      - BACULA_WEB_DB_PASSWORD=changeme
    volumes:
      - ./bacula-web-config:/var/www/bacula-web/application/config
    depends_on:
      - bacula-db

  bacula-db:
    image: mysql:8.0
    container_name: bacula-db
    restart: unless-stopped
    environment:
      - MYSQL_ROOT_PASSWORD=rootpassword
      - MYSQL_DATABASE=bacula
      - MYSQL_USER=bacula
      - MYSQL_PASSWORD=changeme
    volumes:
      - bacula-db-data:/var/lib/mysql

volumes:
  bacula-db-data:
```

**Configuration example (`config.php`):**

```php
<?php
$config['language'] = 'en_US';
$config['datetime_format'] = 'Y-m-d H:i:s';

// Catalog database connection
$config['catalog']['db_type'] = 'mysql';
$config['catalog']['db_host'] = 'bacula-db';
$config['catalog']['db_port'] = 3306;
$config['catalog']['db_name'] = 'bacula';
$config['catalog']['db_user'] = 'bacula';
$config['catalog']['db_password'] = 'changeme';

// Enable graphs
$config['enable_graphs'] = true;
$config['graph_theme'] = 'modern';

// Alerting
$config['email']['enable'] = true;
$config['email']['smtp_host'] = 'smtp.example.com';
$config['email']['from'] = 'backup-monitor@example.com';
$config['email']['on_failure'] = true;
```

## Bareos-WebUI

Bareos-WebUI is the official web-based management and monitoring interface for Bareos (Backup Archiving Recovery Open Sourced), a fork of Bacula. It provides deeper integration with Bareos Director than Bacula-Web, with interactive controls for job management and restore operations.

**Key features:**
- Interactive job management (start, cancel, rerun backups from the browser)
- Full restore workflow through the web interface
- Dashboard with configurable widgets for key metrics
- Director messages and log viewer with filtering
- LDAP and Active Directory authentication with group mapping
- Zend Framework 3 architecture with Bootstrap 4 UI
- Built-in analytics for storage pool forecasting

**Docker Compose deployment:**

```yaml
version: '3'
services:
  bareos-webui:
    image: barcus/bareos-webui:latest
    container_name: bareos-webui
    restart: unless-stopped
    ports:
      - "8085:80"
    environment:
      - BAREOS_DIR_HOST=bareos-director
      - BAREOS_DIR_PASSWORD=director-password
      - PHP_TIMEZONE=UTC
    volumes:
      - ./bareos-webui-config:/etc/bareos-webui
    depends_on:
      - bareos-director

  bareos-director:
    image: barcus/bareos-director:latest
    container_name: bareos-director
    restart: unless-stopped
    ports:
      - "9101:9101"
    environment:
      - DB_HOST=bareos-db
      - DB_NAME=bareos
      - DB_USER=bareos
      - DB_PASSWORD=changeme
    volumes:
      - ./bareos-config:/etc/bareos
      - bareos-catalog:/var/lib/bareos

volumes:
  bareos-catalog:
```

**Configuration example (`directors.ini`):**

```ini
[localhost-bareos-dir]
enabled = true
diraddress = "bareos-director"
dirport = 9101
tls_verify_peer = false
```

## BackupPC-Web Admin

BackupPC is a high-performance, enterprise-grade backup system with a built-in web-based administration and monitoring interface. Unlike Bacula-Web or Bareos-WebUI which are add-on components, BackupPC-Web is integrated directly into the BackupPC server.

**Key features:**
- Built-in CGI-based web interface (no separate web server required)
- Per-host backup status with detailed log access
- Pool-based storage utilization graphs and statistics
- Email notification system with customizable alert triggers
- Browse and restore files directly through the web interface
- User-level access control for self-service restores
- Archive host creation for off-site backup copies

**Docker Compose deployment:**

```yaml
version: '3'
services:
  backuppc:
    image: tiredofit/backuppc:latest
    container_name: backuppc
    restart: unless-stopped
    ports:
      - "8080:80"
    environment:
      - TIMEZONE=UTC
      - BACKUPPC_UUID=1000
      - BACKUPPC_GUID=1000
      - BACKUPPC_WEB_USER=admin
      - BACKUPPC_WEB_PASSWD=changeme
      - SMTP_HOST=smtp.example.com
      - ADMIN_MAIL=admin@example.com
    volumes:
      - backuppc-data:/data
      - backuppc-etc:/etc/backuppc
      - backuppc-home:/home/backuppc

volumes:
  backuppc-data:
  backuppc-etc:
  backuppc-home:
```

**Configuration example (`config.pl`):**

```perl
$Conf{ServerPort} = 80;
$Conf{ServerMesgSecret} = 'random-secret-string';

# Email alerts
$Conf{EMailNotifyMinDays} = 2.5;
$Conf{EMailAdminUserName} = 'admin';
$Conf{EMailUserDestDomain} = '@example.com';
$Conf{EMailNoBackupEverSubj} = 'WARNING: No backup of $host';
$Conf{EMailNoBackupEverMesg} = <<EOF;
Host $host has never been backed up.
Check the BackupPC admin at: \$Conf{ServerURL}
EOF

# Retention and reporting
$Conf{WakeupSchedule} = [1..23];
$Conf{FullPeriod} = 6.97;
$Conf{IncrPeriod} = 0.97;
```

## BorgWeb (BorgBackup Repository Viewer)

BorgWeb is a lightweight web-based interface for browsing and monitoring BorgBackup repositories. Unlike traditional backup monitoring tools that track job execution, BorgWeb focuses on repository contents, deduplication statistics, and storage growth over time.

**Key features:**
- Browse Borg repository contents through a web interface
- View deduplication ratios and compression statistics per archive
- Repository size growth graphs and trend analysis
- Archive listing with timestamps, sizes, and duration
- File-level browsing within archives
- Read-only by design for security (no modification of backup data)
- JSON API for integration with external monitoring tools

**Docker Compose deployment:**

```yaml
version: '3'
services:
  borgweb:
    image: ghcr.io/borgbase/borgweb:latest
    container_name: borgweb
    restart: unless-stopped
    ports:
      - "8088:80"
    environment:
      - BORG_REPO=/backup/repo
      - BORG_PASSPHRASE=your-repo-passphrase
      - BORGWEB_TITLE=Home Lab Backup Monitor
    volumes:
      - ./backup-repo:/backup/repo:ro
      - ./borg-config:/root/.config/borg

  borgmatic:
    image: ghcr.io/borgmatic-collective/borgmatic:latest
    container_name: borgmatic
    restart: unless-stopped
    environment:
      - BORG_PASSPHRASE=your-repo-passphrase
    volumes:
      - ./borgmatic-config:/etc/borgmatic
      - ./data-to-backup:/data:ro
      - ./backup-repo:/backup/repo
```

**Borgmatic configuration (`config.yaml`):**

```yaml
location:
    source_directories:
        - /data
    repositories:
        - /backup/repo
    one_file_system: true

storage:
    encryption_passphrase: "your-repo-passphrase"
    compression: lz4
    archive_name_format: '{hostname}-{now:%Y-%m-%dT%H:%M:%S}'

retention:
    keep_daily: 7
    keep_weekly: 4
    keep_monthly: 6
    keep_yearly: 2

hooks:
    before_backup:
        - echo "Starting backup at $(date)"
    after_backup:
        - echo "Backup complete at $(date)"
        - curl -X POST https://healthchecks.io/ping/your-check-id
    on_error:
        - echo "Backup failed at $(date)" | mail -s "Backup Failure" admin@example.com
```

## Why Self-Host Backup Monitoring?

Running your own backup monitoring dashboard is not a luxury — it is essential for data integrity in self-hosted environments.

**Catch Failures Early.** A backup job that has been silently failing for three months is indistinguishable from having no backups at all. Backup monitoring dashboards provide at-a-glance visibility into the status of every job. Color-coded indicators for success (green), warning (yellow), and failure (red) make it easy to spot problems before they compound.

**Capacity Planning.** Backup storage grows over time, and running out of disk space mid-backup is a common failure mode. Monitoring dashboards track pool utilization, deduplication ratios, and storage growth trends, helping you forecast when to add capacity. BorgWeb's deduplication graphs are particularly useful for understanding how effectively your data compresses over time.

**Compliance and Audit Trails.** For regulated environments, backup monitoring provides the audit trail needed to demonstrate that backups are running on schedule, data is being retained according to policy, and restores are tested regularly. Most tools log every job execution with timestamps, making compliance reporting straightforward.

For more infrastructure monitoring tools, check our [hardware monitoring with IPMI guide](../2026-04-23-self-hosted-bare-metal-hardware-monitoring-ipmi-redfish-openbmc-guide-2026/) and [log aggregation comparison](../2026-04-18-rsyslog-vs-syslog-ng-vs-vector-self-hosted-syslog-log-aggregation-guide-2026/). For backup strategies, see our [PostgreSQL backup tools guide](../pgbackrest-vs-barman-vs-wal-g-self-hosted-postgresql-backup-guide-2026/).

## Choosing the Right Backup Monitoring Solution

**Choose Bacula-Web if:** You are already running Bacula as your backup engine and need a lightweight monitoring overlay. It reads the existing Bacula catalog and adds visualization without changing your backup workflow.

**Choose Bareos-WebUI if:** You use Bareos (or are migrating from Bacula) and want interactive job management in addition to monitoring. The ability to start, stop, and rerun backup jobs from the same web interface reduces operational friction.

**Choose BackupPC-Web if:** You are setting up a new backup infrastructure and want an all-in-one solution where the monitoring is built into the backup server itself. BackupPC's integrated web admin is the most mature and battle-tested option.

**Choose BorgWeb if:** You use BorgBackup for deduplicated, encrypted backups and primarily need repository visibility rather than job scheduling. BorgWeb excels at showing dedup ratios and storage efficiency — metrics that are critical for Borg environments.

## FAQ

### Do I need separate monitoring if my backup tool already emails on failure?

Email alerts are a baseline, but they suffer from alert fatigue and can be missed. A monitoring dashboard provides persistent visible status — you can glance at a screen and immediately see green across all hosts. Dashboards also provide historical trends (growth rates, deduplication efficiency) that email alerts cannot capture.

### Can I monitor multiple backup servers from one dashboard?

Bacula-Web supports multiple Bacula Director connections. Bareos-WebUI connects to a single Director, but you can run multiple instances behind a reverse proxy with a unified landing page. BackupPC manages all hosts from its single built-in interface. BorgWeb is repository-scoped but can be pointed at multiple repo paths.

### How do I integrate backup monitoring with Prometheus and Grafana?

For metric-based monitoring, use the backup engine's native metrics. Bareos exposes metrics through its Director API, which can be scraped by a custom Prometheus exporter. BorgBackup can have its `borg info --json` output transformed into Prometheus metrics via a cron job and the textfile collector. BackupPC status can be scraped via its CGI API and converted to metrics.

### What is the storage overhead of running a monitoring web UI?

Minimal. Bacula-Web and Bareos-WebUI each use under 100 MB for the PHP application and configuration files. BackupPC-Web is built into the backup server with zero additional overhead. BorgWeb uses ~50 MB for the Flask application. The databases storing backup metadata (job histories, volumes) can grow over time but are already maintained by the backup engine.

### Can these tools monitor cloud backups as well as local backups?

Yes, as long as the backup engine supports the target. BorgBackup works with any filesystem-accessible path (local, NFS, SSHFS, S3 via rclone mount). Bacula and Bareos support cloud storage backends (S3, Azure Blob) through their storage daemon configurations. The monitoring tools track job execution regardless of where the data is stored.

---

**💰 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — the world's largest prediction market platform where you can bet on everything from election results to technology regulatory timelines. Unlike gambling, this is a real information market: the more you know, the better your edge. I've already made good money predicting the direction of technology-related events. Sign up with my referral link: [Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Backup Monitoring and Reporting: Bacula-Web vs Bareos-WebUI vs BackupPC-Web vs BorgWeb",
  "description": "Comprehensive comparison of open-source backup monitoring and reporting dashboards — Bacula-Web, Bareos-WebUI, BackupPC-Web, and BorgWeb — for tracking backup job status, storage growth, and data integrity in self-hosted environments.",
  "datePublished": "2026-06-04",
  "dateModified": "2026-06-04",
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
