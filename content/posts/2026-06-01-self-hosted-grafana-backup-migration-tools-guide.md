---
title: "Self-Hosted Grafana Backup and Migration: grafana-backup-tool vs grafana-sync vs grafana-dashboards-manager"
date: "2026-05-18"
tags: ["grafana", "monitoring", "backup", "devops"]
draft: false
---

Grafana dashboards represent hundreds of hours of configuration work — custom panels, datasource connections, alert rules, and variables. Losing this configuration due to a failed migration, accidental deletion, or infrastructure failure can set teams back weeks. While Grafana's built-in export/import functionality works for individual dashboards, managing dozens or hundreds of dashboards across multiple instances requires dedicated backup and synchronization tools.

This guide compares three open-source Grafana management tools: **grafana-backup-tool** for comprehensive backups, **grafana-sync** for multi-instance synchronization, and **grafana-dashboards-manager** for dashboard organization and version control.

## Quick Comparison

| Feature | grafana-backup-tool | grafana-sync | grafana-dashboards-manager |
|---------|--------------------|-------------|---------------------------|
| GitHub Stars | 946+ | 220+ | Community tool |
| Primary Role | Backup/restore | Dashboard sync | Dashboard management |
| Backup Scope | Dashboards, datasources, folders | Dashboards only | Dashboards with Git |
| Restore Capability | Yes | Partial (push only) | Via Git workflow |
| Multi-instance | No (single instance) | Yes (N-N sync) | Yes (Git-mediated) |
| Scheduling | Cron-based | Continuous/manual | Git-triggered |
| Alert Rules Backup | Yes | Yes | Manual export |
| Version Control | Via backup archives | No | Yes (Git native) |
| Best For | Disaster recovery | Dashboard consistency | GitOps workflows |

## grafana-backup-tool (ysde/grafana-backup-tool)

grafana-backup-tool is the most widely adopted Grafana backup solution, providing comprehensive backup and restore capabilities for dashboards, datasources, folders, and alert rules through Grafana's REST API.

### Key Features

- **Full instance backup** — Dashboards, datasources, folders, alert rules, teams, and users
- **Selective export** — Back up specific folders or dashboard types
- **JSON-based storage** — All exports stored as versionable JSON files
- **Restore capability** — Import backups to the same or different Grafana instance
- **Grafana version compatibility** — Works with Grafana 7.x through 11.x
- **CI/CD integration** — Run as part of deployment pipelines for configuration-as-code

### Docker Compose Deployment

```yaml
version: "3"
services:
  grafana-backup:
    image: python:3.11-slim
    container_name: grafana-backup
    volumes:
      - ./grafana-backup/config:/opt/grafana-backup
      - ./grafana-backup/output:/opt/grafana-backup/output
    working_dir: /opt/grafana-backup
    environment:
      - GRAFANA_URL=http://grafana:3000
      - GRAFANA_API_KEY=${GRAFANA_API_KEY}
    command: >
      bash -c "
        pip install grafana-backup-tool &&
        grafana-backup save --config grafanaSettings.json &&
        grafana-backup save --config grafanaSettings.json
      "

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

volumes:
  grafana-data:
```

### Configuration File

```json
{
  "grafana": {
    "url": "http://localhost:3000",
    "token": "eyJrIjoiWVBpR3...",
    "search_size": 5000,
    "verify_ssl": true
  },
  "general": {
    "backup_dir": "./output",
    "backup_file_format": "%Y%m%d%H%M",
    "pretty_print": true
  }
}
```

### Backup and Restore Commands

```bash
# Install the tool
pip install grafana-backup-tool

# Set environment variables
export GRAFANA_URL=http://localhost:3000
export GRAFANA_TOKEN=your-api-key

# Backup everything
grafana-backup save

# Restore from backup
grafana-backup restore ./output/202606011200.tar.gz

# Schedule with cron
0 3 * * * GRAFANA_URL=http://grafana:3000 GRAFANA_TOKEN=xxx grafana-backup save
```

## grafana-sync (mpostument/grafana-sync)

grafana-sync focuses on keeping dashboards synchronized between multiple Grafana instances. It is designed for organizations that run staging and production Grafana servers and need to promote dashboard changes through environments consistently.

### Key Features

- **Multi-instance synchronization** — Push dashboards from source to target Grafana
- **Folder preservation** — Maintains folder structure during sync
- **Datasource mapping** — Automatically maps datasources between environments
- **Conflict detection** — Identifies dashboards that exist on both instances with differences
- **Dry-run mode** — Preview changes before applying them
- **CI/CD friendly** — Designed for pipeline integration

### Docker Compose Deployment

```yaml
version: "3"
services:
  grafana-sync:
    image: python:3.11-slim
    container_name: grafana-sync
    volumes:
      - ./grafana-sync/config:/app/config
    working_dir: /app
    command: >
      bash -c "
        pip install requests &&
        python sync.py --config config.json
      "

  grafana-staging:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    volumes:
      - staging-data:/var/lib/grafana

  grafana-production:
    image: grafana/grafana:latest
    ports:
      - "3002:3000"
    volumes:
      - production-data:/var/lib/grafana

volumes:
  staging-data:
  production-data:
```

### Sync Configuration

```json
{
  "source": {
    "url": "http://grafana-staging:3000",
    "token": "staging-api-key"
  },
  "target": {
    "url": "http://grafana-production:3000",
    "token": "production-api-key"
  },
  "options": {
    "overwrite": true,
    "sync_datasources": false,
    "folder_filter": ["Production Dashboards"],
    "dry_run": false
  }
}
```

### Usage

```bash
# Install dependencies
pip install requests

# Run sync (staging to production)
python sync.py --config config.json

# Dry run to preview changes
python sync.py --config config.json --dry-run

# Sync only specific folders
python sync.py --config config.json --folders "Infrastructure,Application"
```

## Grafana Dashboard Manager (Git-based approach)

The Git-based approach stores Grafana dashboards as version-controlled JSON files in a Git repository, using CI/CD pipelines to deploy changes to Grafana instances. This pattern treats dashboard configuration as code.

### Key Features

- **Git version control** — Full history, diff, and rollback capabilities
- **Peer review** — Pull request workflow for dashboard changes
- **Environment promotion** — Deploy to staging first, then production
- **Automated deployment** — CI/CD pipeline applies changes via Grafana API
- **Compliance** — Audit trail for all dashboard modifications
- **Branch-based environments** — Feature branches for experimental dashboards

### Docker Compose with Git-sync

```yaml
version: "3"
services:
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
      - ./dashboards:/etc/grafana/provisioning/dashboards
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH=/etc/grafana/provisioning/dashboards/home.json

  dashboard-sync:
    image: alpine/git:latest
    container_name: dashboard-sync
    volumes:
      - ./dashboards:/dashboards
      - ~/.ssh:/root/.ssh
    command: >
      sh -c "
        git clone git@github.com:org/grafana-dashboards.git /dashboards &&
        while true; do
          cd /dashboards && git pull origin main
          sleep 300
        done
      "

volumes:
  grafana-data:
```

### Provisioning Configuration

```yaml
# /etc/grafana/provisioning/dashboards/dashboards.yaml
apiVersion: 1
providers:
  - name: "Default"
    orgId: 1
    folder: ""
    type: file
    disableDeletion: false
    editable: true
    updateIntervalSeconds: 30
    options:
      path: /etc/grafana/provisioning/dashboards
      foldersFromFilesStructure: true
```

### CI/CD Pipeline (GitHub Actions)

```yaml
name: Deploy Grafana Dashboards
on:
  push:
    branches: [main]
    paths: ["dashboards/**"]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Grafana
        run: |
          for file in dashboards/*.json; do
            curl -X POST "http://grafana:3000/api/dashboards/db"               -H "Authorization: Bearer $GRAFANA_TOKEN"               -H "Content-Type: application/json"               -d @"$file"
          done
```

## Choosing the Right Grafana Management Approach

**Choose grafana-backup-tool** if you:
- Need reliable disaster recovery for your Grafana instance
- Want to backup everything — dashboards, datasources, alert rules, and users
- Operate a single Grafana instance with periodic backup requirements
- Need point-in-time recovery capabilities

**Choose grafana-sync** if you:
- Run multiple Grafana instances (staging, production, DR)
- Need to promote dashboard changes between environments
- Want automated synchronization without manual export/import
- Manage folder structures that need to be consistent across instances

**Choose the Git-based approach** if you:
- Want full version control and audit trails for dashboard changes
- Use GitOps practices for infrastructure management
- Need peer review for dashboard modifications
- Run CI/CD pipelines and want dashboards as part of the deployment process

## Why Self-Host Grafana Backup and Management Tools?

Grafana is often the central monitoring interface for infrastructure, applications, and business metrics. The dashboards you build represent critical institutional knowledge.

**Disaster recovery**: A Grafana instance failure without backups means losing all dashboards, datasources, and alert configurations. Rebuilding from scratch takes days for complex monitoring setups. Automated backups ensure you can restore to a known-good state within minutes. For related backup strategies, see our [MySQL high availability guide](../2026-05-11-self-hosted-mysql-high-availability-innodb-cluster-percona-xtradb-orchestrator-guide/) covering database-level disaster recovery patterns.

**Environment consistency**: Organizations running staging and production Grafana instances frequently encounter configuration drift — dashboards exist in one environment but not the other, or differ in subtle ways. Synchronization tools ensure dashboard parity across environments, reducing the risk of monitoring gaps in production. If you are managing [infrastructure monitoring](../2026-04-26-checkmk-vs-zabbix-vs-nagios-self-hosted-infrastructure-monitoring-2026/) across multiple toolchains, consistent Grafana configurations are essential.

**Change management**: Treating dashboard configuration as code brings the same benefits to monitoring that it brings to infrastructure — version history, peer review, rollback capabilities, and audit trails. This is especially valuable in regulated industries where monitoring configuration changes must be tracked and approved.

## FAQ

### What does grafana-backup-tool actually save?

It saves dashboards (as JSON), datasources, folders, alert rules, notification channels, teams, and users. Everything accessible through the Grafana Admin API is included in the backup archive.

### Can I restore a backup to a different Grafana version?

Generally yes. grafana-backup-tool exports dashboard JSON which is largely version-independent. However, some panel types and features introduced in newer Grafana versions may not render correctly on older instances. Always test restores in a staging environment first.

### How often should I backup Grafana?

Daily backups are recommended for production instances. Dashboard changes are frequent enough that a week-old backup may miss critical configuration. Use cron to schedule `grafana-backup-tool save` at a low-traffic time (e.g., 3 AM).

### Does Grafana have built-in backup functionality?

Grafana Enterprise includes backup and restore features. The open-source version relies on filesystem backups (the Grafana SQLite database and provisioning files) or API-based tools like grafana-backup-tool for more granular control.

### Can I use Git-based dashboard management with Grafana provisioning?

Yes. Grafana's file provisioning system automatically loads dashboard JSON files from specified directories. Combined with a Git repository that syncs to the provisioning directory, you get declarative dashboard management with full version control.

### How do I handle datasource differences between staging and production?

Use environment-specific datasource configuration files. In the Git-based approach, maintain separate branches or directories for each environment. With grafana-sync, configure datasource mapping to translate staging datasource names to production equivalents during sync.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Grafana Backup and Migration Tools",
  "description": "Compare Grafana backup and sync tools: grafana-backup-tool for disaster recovery, grafana-sync for multi-instance sync, and Git-based dashboard management. Docker configs included.",
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
