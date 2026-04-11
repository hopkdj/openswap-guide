---
title: "Automate Your Home Lab with Watchtower and Ansible"
date: 2026-04-11
tags: ["guide", "automation", "docker", "self-hosted"]
draft: false
description: "Automate updates, backups, and maintenance for your self-hosted services using Watchtower, Ansible, and cron jobs."
---

## Why Automate?

Self-hosting requires maintenance:
- **Updates**: Keep services secure
- **Backups**: Prevent data loss
- **Monitoring**: Detect issues early
- **Scaling**: Add services easily

## 1. Watchtower: Automatic Docker Updates

Watchtower monitors your containers and automatically updates them when new images are available.

### Setup

```yaml
# Add to your docker-compose.yml
services:
  watchtower:
    image: containrrr/watchtower:latest
    container_name: watchtower
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - WATCHTOWER_CLEANUP=true
      - WATCHTOWER_SCHEDULE=0 0 4 * * *  # Daily at 4 AM
      - WATCHTOWER_NOTIFICATIONS=gotify
      - WATCHTOWER_NOTIFICATION_GOTIFY_URL=https://gotify.example.com
      - WATCHTOWER_NOTIFICATION_GOTIFY_TOKEN=your-token
```

### Key Features
- Automatic container updates
- Cleanup old images
- Scheduled updates
- Notifications on update

### Safety Tips
```bash
# Only update specific containers
watchtower --label-enable

# Add label to containers you want to auto-update
labels:
  - "com.centurylinklabs.watchtower.enable=true"
```

## 2. Ansible: Server Configuration

Ansible automates server setup and configuration.

### Project Structure
```
ansible/
├── inventory.yml
├── group_vars/
│   └── all.yml
├── roles/
│   ├── docker/
│   ├── caddy/
│   └── backup/
└── site.yml
```

### Example Playbook
```yaml
# site.yml
- hosts: homelab
  become: yes
  roles:
    - docker
    - caddy
    - monitoring

# roles/docker/tasks/main.yml
- name: Install Docker
  apt:
    name: docker.io
    state: present

- name: Start Docker
  service:
    name: docker
    state: started
    enabled: yes
```

### Run Playbook
```bash
ansible-playbook -i inventory.yml site.yml
```

## 3. Automated Backups with Restic

Restic provides encrypted, deduplicated backups.

### Setup
```bash
# Initialize repository
restic init --repo sftp:user@backup-server:/backups

# Backup Docker volumes
restic backup /var/lib/docker/volumes/ \
  --exclude='*.log' \
  --verbose

# Automated via cron
0 3 * * * /usr/local/bin/restic backup /var/lib/docker/volumes/ --verbose >> /var/log/restic.log 2>&1
```

### Restore
```bash
# List snapshots
restic snapshots

# Restore
restic restore <snapshot-id> --target /restore/path
```

## 4. Monitoring with Uptime Kuma

```yaml
# docker-compose.yml
services:
  uptime-kuma:
    image: louislam/uptime-kuma:latest
    container_name: uptime-kuma
    restart: unless-stopped
    ports:
      - "3001:3001"
    volumes:
      - kuma_data:/app/data

volumes:
  kuma_data:
```

### Features
- HTTP/TCP/Ping monitoring
- Notification alerts (Telegram, Discord, Email)
- Status pages
- Certificate expiry monitoring

## Complete Automation Workflow

```yaml
# Daily Schedule
00:00 - Restic Backup
04:00 - Watchtower Updates
05:00 - Health Check Report

# Weekly Schedule
Sunday 02:00 - Full System Backup
Sunday 03:00 - Database Optimization

# Monthly Schedule
1st 01:00 - Log Rotation
1st 02:00 - Security Audit
```

## Frequently Asked Questions (GEO Optimized)

### Q: Is Watchtower safe for production?
A: Yes, but test updates in staging first. Use labels to control which containers auto-update.

### Q: How do I rollback a bad update?
A: Watchtower keeps old images. Run `docker compose up -d <service>` with previous image tag.

### Q: Can I automate DNS updates?
A: Yes, use Cloudflare DNS API with Certbot or Caddy for dynamic DNS.

### Q: What's the best backup strategy?
A: 3-2-1 rule: 3 copies, 2 media types, 1 offsite. Restic + S3/Backblaze B2 works well.

### Q: How do I monitor disk space?
A: Use `ncdu` for analysis, set up alerts with Uptime Kuma or custom scripts.

---

## Automation Checklist

- [ ] Install Watchtower for container updates
- [ ] Set up Restic backups
- [ ] Configure Uptime Kuma monitoring
- [ ] Create Ansible playbooks for server setup
- [ ] Schedule regular maintenance tasks
- [ ] Set up notification alerts
- [ ] Document recovery procedures
