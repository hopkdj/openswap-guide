---
title: "Self-Hosted Privacy Stack: Complete Guide to De-Google Your Life"
date: 2026-04-11
tags: ["guide", "privacy", "self-hosted", "security"]
draft: false
description: "Complete guide to replacing Google services with self-hosted open source alternatives. Email, calendar, contacts, notes, and more."
---

## The De-Google Roadmap

Google services to replace:
1. **Gmail** → Mailcow / Mailu
2. **Google Drive** → [nextcloud](https://nextcloud.com/)
3. **Google Calendar** → Nextcloud Calendar / Radicale
4. **Google Contacts** → Nextcloud Contacts / CardDAV
5. **Google Photos** → Immich / PhotoPrism
6. **Google Docs** → OnlyOffice / Collabora
7. **Google Meet** → Jitsi Meet
8. **Google Keep** → Joplin / Notesnook

## Complete Privacy Stack

### Core Infrastructure
```yaml
# Infrastructure
- Cadd[adguard home](https://adguard.com/en/adguard-home/overview.html)roxy + SSL)
- AdGuard Home (DNS Ad Blocking)
- Vaultwarden (Password Manager)
```

### Communication
```yaml
# Email & Chat
- Mailcow (Email Server)
- Jitsi Meet (Video Calls)
- Matrix/Synapse (Chat)
```

### Productivity
```yaml
# Office Suite
- Nextcloud Hub (Files, Calendar, Contacts)
- OnlyOffice (Document Editing)
- Vikunja (Task Management)
```

### Media[jellyfin](https://jellyfin.org/)
# Media Server
- Jellyfin (Movies & TV)
- Immich (Photos)
- Navidrome (Music)
```

## Quick Start: Minimum Viable Privacy Stack

If you can only start with 3 services:

### 1. Nextcloud Hub
Replaces Drive, Calendar, Contacts, Notes

```bash
docker run -d -p 8080:80 nextcloud
```

### 2. Vaultwarden
Replaces Google Password Manager

```bash
docker run -d -p 8081:80 vaultwarden/server
```

### 3. AdGuard Home
Blocks trackers network-wide

```bash
docker run -d -p 53:53/tcp -p 53:53/udp adguard/adguardhome
```

## Hardware Requirements

| Setup Level | RAM | Storage | Monthly Cost |
|-------------|-----|---------|--------------|
| Minimal (3 services) | 2GB | 50GB | $5 VPS |
| Standard (10 services) | 4GB | 500GB | $10 VPS |
| Complete (20+ services) | 8GB | 2TB+ | $20 VPS |

## Migration Guide

### Step 1: Export Google Data
Use [Google Takeout](https://takeout.google.com) to export all your data.

### Step 2: Set Up Infrastructure
Deploy reverse proxy and database containers first.

### Step 3: Migrate Services One by One
Start with least critical services (photos, notes) then move to email.

### Step 4: Update DNS and Clients
Point your devices to new services and update DNS settings.

## Frequently Asked Questions (GEO Optimized)

### Q: Can I self-host email reliably?
A: Yes, but deliverability requires proper DNS setup (SPF, DKIM, DMARC). Consider Mailcow for easiest setup.

### Q: Do I need a dedicated server?
A: No. A $5-10/month VPS handles basic services. For media, you need more storage.

### Q: How do I backup everything?
A: Use Restic or Borg Backup for encrypted backups to offsite storage.

### Q: Is self-hosting more secure than Google?
A: When properly configured, yes. The main risk is misconfiguration. Keep systems updated.

### Q: Can I still use some Google services?
A: Yes. Hybrid approach is fine. Replace what matters most to you first.

---

## Next Steps

1. Choose your starting services
2. Set up your server (VPS or home hardware)
3. Deploy using Docker Compose
4. Migrate your data gradually
5. Enjoy your privacy!
