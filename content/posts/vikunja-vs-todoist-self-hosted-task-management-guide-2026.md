---
title: "Vikunja vs Todoist: Best Self-Hosted Task Management 2026"
date: 2026-04-18
tags: ["comparison", "guide", "self-hosted", "productivity", "task-management", "open-source"]
draft: false
description: "Compare Vikunja and Todoist for task management in 2026. Learn how to self-host Vikunja with Docker, its features vs Todoist, and why open-source task tracking may be the right choice for your workflow."
---

Managing tasks, projects, and deadlines is a universal challenge. Whether you're running a small team, coordinating a homelab, or simply trying to organize your personal life, the right task management tool can make a significant difference. For years, Todoist has been the default recommendation — but [Vikunja](https://vikunja.io), an open-source alternative, has matured into a genuinely compelling option that puts you in full control of your data.

In this guide, we'll compare Vikunja and Todoist across features, pricing, self-hosting options, and real-world usability. We'll also walk through deploying Vikunja on your own infrastructure with [docker](https://www.docker.com/) Compose.

For those looking at broader task organization tools, our [self-hosted Kanban boards guide](../self-hosted-kanban-boards-guide/) covers visual board options, while the [Leantime project management guide](../leantime-self-hosted-project-management-strategy-guide/) explores strategy-focused planning. If you need a full wiki alongsi[outline](https://www.getoutline.com/) task manager, the [Outline Notion alternative guide](../outline-self-hosted-notion-alternative-guide/) is worth a read.

## Why Self-Host Your Task Management?

Before diving into the comparison, it's worth understanding why self-hosting a task management app matters:

- **Data ownership**: Your tasks, projects, and notes live on your server — not on a company's cloud. No one scans your data for analytics or trains models on it.
- **No subscription lock-in**: One-time infrastructure cost (a $5/month VPS or even a Raspberry Pi) versus recurring per-user fees.
- **Offline access**: Self-hosted instances on your local network work even when the internet goes down.
- **Customization**: Open-source tools let you modify behavior, integrate with other self-hosted services, and extend functionality.
- **Privacy**: No telemetry, no tracking pixels, no cross-service data sharing. Your task list stays yours.

## What Is Vikunja?

[Vikunja](https://github.com/go-vikunja/vikunja) is an open-source task management application written in Go (backend) and Vue.js (frontend). Licensed under AGPL-3.0, it currently has nearly **4,000 GitHub stars** and over **7 million Docker pulls**, with active development — the last commit was on April 18, 2026.

Vikunja describes itself as "the to-do app to organize your life," and it delivers on that promise with a feature set that rivals paid alternatives:

- **Multiple list views**: List, Gantt chart, table, and Kanban board views for different workflows
- **Projects and namespaces**: Organize tasks hierarchically with subprojects and shared workspaces
- **Labels and filters**: Tag tasks and create custom filtered views
- **Reminders and due dates**: Email and in-app notifications for upcoming deadlines
- **File attachments**: Upload files directly to tasks
- **Team collaboration**: Share projects, assign tasks, and track activity
- **API-first design**: Full REST API with Swagger documentation for integrations
- **Self-hosted or cloud**: Run it yourself or use Vikunja Cloud for a hosted experience
- **Cross-platform**: Web app, desktop clients, and mobile apps (Android via Vicu)

The project recently merged its frontend repository into the main codebase, simplifying the architecture and reducing maintenance overhead.

## What Is Todoist?

Todoist, developed by Doist, is one of the most popular task management applications worldwide. It's a proprietary, cloud-only SaaS product with no self-hosting option.

Todoist's strengths include:

- **Natural language input**: Type "meeting every Monday at 3pm" and it parses dates automatically
- **Clean, polished UI**: Consistently rated as one of the best-designed task apps
- **Rich integrations**: Connects with 80+ services including Gmail, Slack, Google Calendar, and Zapier
- **Karma system**: Gamified productivity tracking
- **Cross-platform**: Available on every major platform with excellent sync
- **Templates**: Pre-built project templates for common workflows

However, Todoist also has limitations:

- **No self-hosting**: All data lives on Doist's servers
- **Subscription pricing**: Advanced features require a monthly or annual plan
- **Limited free tier**: Only 5 active projects without paying
- **Closed source**: You cannot audit the code, modify features, or export data beyond what the API allows

## Feature Comparison: Vikunja vs Todoist

| Feature | Vikunja | Todoist Free | Todoist Pro |
|---------|---------|-------------|-------------|
| **License** | AGPL-3.0 (open source) | Proprietary | Proprietary |
| **Self-hosted** | ✅ Yes | ❌ No | ❌ No |
| **Price** | Free (self-hosted) | Free | $4/month |
| **Max projects** | Unlimited | 5 | Unlimited |
| **Kanban boards** | ✅ Built-in | ❌ No | ❌ No |
| **Gantt charts** | ✅ Built-in | ❌ No | ❌ No |
| **Table view** | ✅ Built-in | ❌ No | ❌ No |
| **Calendar view** | ✅ Built-in | ❌ No | ✅ Yes |
| **File attachments** | ✅ Yes | ❌ No | ✅ Yes (100MB) |
| **Labels / tags** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Reminders** | ✅ Yes | ❌ No | ✅ Yes |
| **Natural language dates** | ❌ No | ✅ Yes | ✅ Yes |
| **API access** | ✅ Full REST API | ✅ REST API | ✅ REST API |
| **Team collaboration** | ✅ Shared projects | Limited | ✅ Full |
| **Subtasks** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Task comments** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Integrations** | API-based (manual) | 80+ services | 80+ services |
| **Mobile apps** | Web + Android (Vicu) | iOS + Android | iOS + Android |
| **Data export** | Full database access | Limited CSV | Limited CSV |

## Deploying Vikunja with Docker Compose

Setting up Vikunja on your own server is straightforward. The project provides official Docker images on Docker Hub (`vikunja/vikunja`) with over 7 million pulls. Below is a production-ready Docker Compose configuration that includes the Vikunja API, a PostgreSQL database, and the frontend.

### Prerequisites

- A Linux server (Ubuntu 22.04+, Debian 12+, or any Docker-compatible OS)
- Docker and Docker Compose installed
- A domain name (optional, for HTTPS with a reverse proxy)
- At least 512MB RAM and 10GB disk space

### Step 1: Create the Docker Compose File

Create a directory for Vikunja and the compose file:

```bash
mkdir -p ~/vikunja && cd ~/vikunja
```

Save the following as `docker-compose.yml`:

```yaml
version: '3'

services:
  vikunja-api:
    image: vikunja/vikunja:latest
    container_name: vikunja-api
    restart: unless-stopped
    environment:
      - VIKUNJA_SERVICE_PUBLICURL=https://vikunja.example.com
      - VIKUNJA_DATABASE_HOST=db
      - VIKUNJA_DATABASE_PASSWORD=changeme
      - VIKUNJA_DATABASE_TYPE=postgres
      - VIKUNJA_DATABASE_USER=vikunja
      - VIKUNJA_DATABASE_DATABASE=vikunja
      - VIKUNJA_SERVICE_JWTSECRET=your-secret-key-change-this
      - VIKUNJA_SERVICE_ENABLEREGISTRATION=true
    volumes:
      - ./files:/app/vikunja/files
    ports:
      - "3456:3456"
    depends_on:
      db:
        condition: service_healthy
    networks:
      - vikunja-net

  vikunja-frontend:
    image: vikunja/frontend:latest
    container_name: vikunja-frontend
    restart: unless-stopped
    environment:
      - VIKUNJA_PUBLIC_URL=https://vikunja.example.com
      - VIKUNJA_API_URL=https://vikunja.example.com/api/v1/
    ports:
      - "8080:80"
    depends_on:
      - vikunja-api
    networks:
      - vikunja-net

  db:
    image: postgres:16-alpine
    container_name: vikunja-db
    restart: unless-stopped
    environment:
      - POSTGRES_PASSWORD=changeme
      - POSTGRES_USER=vikunja
      - POSTGRES_DB=vikunja
    volumes:
      - ./db:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U vikunja"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - vikunja-net

networks:
  vikunja-net:
    driver: bridge
```

**Important**: Replace `vikunja.example.com` with your actual domain, and change both `changeme` passwords and the `JWTSECRET` to strong random values. Generate a JWT secret with:

```bash
openssl rand -base64 32
```

### Step 2: Start Vikunja

```bash
docker compose up -d
```

Wait about 30 seconds for the database to initialize, then access the frontend at `http://your-server-ip:8080`. The first user to register becomes the administrator.

### Step 3: Set Up a Reverse Proxy (Recommended)

For production use, place a reverse proxy like Nginx or Caddy in front of Vikunja:

```nginx
server {
    listen 443 ssl http2;
    server_name vikunja.example.com;

    ssl_certificate /etc/letsencrypt/live/vikunja.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/vikunja.example.com/privkey.pem;

    # Frontend
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # API
    location /api/ {
        proxy_pass http://localhost:3456/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # DAV (CalDAV/CardDAV support)
    location /.well-known/caldav {
        proxy_pass http://localhost:3456/.well-known/caldav;
    }
    location /.well-known/carddav {
        proxy_pass http://localhost:3456/.well-known/carddav;
    }
}
```

With Let's Encrypt for free SSL certificates:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d vikunja.example.com
```

### Step 4: Backup Your Data

Regular backups are essential. Here's a simple backup script:

```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/vikunja"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

# Database backup
docker exec vikunja-db pg_dump -U vikunja vikunja > "$BACKUP_DIR/db_$TIMESTAMP.sql"

# Files backup
tar czf "$BACKUP_DIR/files_$TIMESTAMP.tar.gz" ~/vikunja/files

# Keep last 7 days
find "$BACKUP_DIR" -type f -mtime +7 -delete

echo "Backup completed: $TIMESTAMP"
```

Schedule it with cron:

```bash
crontab -e
# Add this line:
0 2 * * * /opt/backups/vikunja/backup.sh >> /var/log/vikunja-backup.log 2>&1
```

## Pricing Comparison

| Plan | Vikunja | Todoist |
|------|---------|---------|
| **Free** | Full features (self-hosted) | 5 projects, basic features |
| **Pro** | N/A (free) | $4/month, unlimited projects, reminders, labels, filters |
| **Business** | N/A (free) | $6/month/user, admin console, SSO |
| **Enterprise** | N/A (free) | Custom pricing |
| **Cloud hosted** | From $3.33/month (Vikunja Cloud) | Included in plans above |
| **Self-hosted cost** | Infrastructure only (~$5/month VPS) | Not available |

If you're comfortable managing your own server, Vikunja's self-hosted option delivers significantly more value — unlimited projects, all views (Kanban, Gantt, table), file attachments, and team collaboration at the cost of a basic VPS. Todoist's Pro plan at $48/year per user quickly becomes expensive for teams.

## When to Choose Vikunja

Choose Vikunja if:

- You want **full control** over your task data and infrastructure
- You need **Kanban, Gantt, or table views** without paying premium prices
- You're already running a **self-hosted homelab** and want to add another service
- You value **open-source software** and the ability to audit or modify the code
- You need **unlimited projects** on a budget
- You want to integrate task management with other self-hosted tools via the REST API

## When to Choose Todoist

Choose Todoist if:

- You want the **best natural language date parsing** in any task app
- You need **deep integrations** with Gmail, Slack, Google Calendar, and 80+ other services
- You prefer a **polished, zero-maintenance** cloud solution
- Your team is small and the per-user cost is acceptable
- You want **iOS and Android apps** with full feature parity
- You don't have the time or expertise to manage a self-hosted service

## Migration Tips

Moving from Todoist to Vikunja? Here's how to make the transition smoother:

1. **Export your Todoist data**: Go to Settings → Export as CSV from Todoist
2. **Use the Vikunja API**: Write a simple script to import your CSV data via the REST API, or use community import tools
3. **Recreate project structure manually**: For com[plex](https://www.plex.tv/) hierarchies, manual recreation ensures labels, due dates, and assignments transfer correctly
4. **Run both in parallel**: Keep Todoist for 1-2 weeks while populating Vikunja, then make the full switch
5. **Set up reminders**: Vikunja's email notification system needs SMTP configuration — set this up early so you don't miss deadlines during the transition

## FAQ

### Is Vikunja free to use?

Yes, Vikunja is completely free and open-source under the AGPL-3.0 license. You can self-host it on your own infrastructure at no cost beyond server expenses. Vikunja also offers a hosted cloud plan starting at $3.33/month if you prefer not to manage the server yourself.

### Can Vikunja replace Todoist for teams?

For most team use cases, yes. Vikunja supports shared projects, task assignments, comments, file attachments, and multiple views (list, Kanban, Gantt, table). It lacks Todoist's extensive third-party integrations, but the REST API allows you to build custom connections to your existing toolchain.

### Does Vikunja support recurring tasks?

Yes, Vikunja supports recurring tasks with configurable intervals. You can set tasks to repeat daily, weekly, monthly, or on custom schedules. This covers the most common recurring task patterns that users need for daily standups, weekly reviews, and monthly reports.

### What database does Vikunja use?

Vikunja supports PostgreSQL, MySQL, MariaDB, and SQLite. For production deployments with multiple users, PostgreSQL is recommended. SQLite is suitable for personal use or testing with a single user.

### Can I access Vikunja from my phone?

Yes. Vikunja provides a web app that works on mobile browsers. For Android, there's a native app called **Vicu** (available on GitHub and F-Droid). iOS users can use the web app or add it to their home screen as a progressive web app (PWA).

### How does Vikunja compare to other self-hosted task tools like Wekan or Taiga?

Vikunja is more of a personal and small-team task manager, similar to Todoist or Trello. Wekan is a Kanban-only board tool, while Taiga is a full agile project management platform for software teams. Vikunja sits between them — offering more structure than Wekan but less complexity than Taiga.

### Is Vikunja actively maintained?

Yes. As of April 2026, the project has nearly 4,000 GitHub stars and receives regular updates. The most recent commit was on April 18, 2026. The project is developed by a solo maintainer (kolaente) with community contributions and is also available as a commercially hosted service, which provides sustainable funding for ongoing development.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Vikunja vs Todoist: Best Self-Hosted Task Management 2026",
  "description": "Compare Vikunja and Todoist for task management in 2026. Learn how to self-host Vikunja with Docker, its features vs Todoist, and why open-source task tracking may be the right choice.",
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
