---
title: "ActivityWatch vs Kimai vs Ever Gauzy: Self-Hosted Time Tracking Guide"
date: 2026-05-01T00:00:00Z
tags: ["time-tracking", "productivity", "self-hosted", "monitoring", "activitywatch", "kimai", "gauzy"]
draft: false
---

Whether you are a freelancer billing clients, a manager tracking team productivity, or a developer optimizing your workflow, knowing where your time goes is essential. Proprietary time-tracking services like Toggl, Clockify, and Harvest lock your data behind cloud accounts. Self-hosted alternatives give you full ownership, unlimited users, and complete privacy.

In this guide, we compare three of the most capable open-source time-tracking platforms: **ActivityWatch** for automated, privacy-first activity monitoring, **Kimai** for professional multi-user timesheet management with invoicing, and **Ever Gauzy** for full-stack business operations that include time tracking alongside ERP, CRM, and HR modules. For related reading on self-hosted invoicing tools, see our [Invoice Ninja vs Akaunting vs Crater comparison](../invoice-ninja-akaunting-crater-self-hosted-invoicing-guide/), and for building dashboards from your tracked data, check out our [BI dashboard guide](../self-hosted-bi-dashboard-superset-metabase-lightdash-guide-2026/).

## Why Self-Host Your Time Tracking?

Before diving into the tools, consider what you gain by running time-tracking software on your own infrastructure:

- **Data sovereignty**: Your time entries, project details, and activity logs never leave your servers.
- **No subscription costs**: All three tools are free and open-source, with no per-user or per-seat licensing.
- **Unlimited users**: Scale to your entire team without hitting free-tier limits.
- **Custom integrations**: Connect directly to your existing databases, billing systems, and dashboards.
- **Offline capability**: Track time even when your internet connection drops.

## ActivityWatch: Automated, Privacy-First Time Tracking

[ActivityWatch](https://github.com/ActivityWatch/activitywatch) is the most popular open-source time tracker with over 17,000 GitHub stars. Unlike manual time-trackers, ActivityWatch automatically records what you are doing on your computer -- which applications you use, which browser tabs you visit, and how long you spend on each activity.

### Key Features

- **Automatic tracking**: No start/stop buttons -- the watchers run in the background and categorize activity based on rules you define.
- **Cross-platform**: Supports Windows, macOS, Linux, and Android.
- **Privacy-first**: All data stays on your machine. No cloud sync by default.
- **Extensible**: Plugin architecture allows custom watchers, categorization rules, and visualizations.
- **Timeline view**: Detailed timeline of daily activity with color-coded categories.

### Architecture

ActivityWatch uses a modular architecture. The core server (`aw-server`) receives data from watchers (`aw-watcher-afk` for idle detection, `aw-watcher-window` for active window tracking) and stores it in a local SQLite or PostgreSQL database. The web UI (`aw-webui`) provides a dashboard for exploring your data.

```bash
# Install ActivityWatch on Linux
wget https://github.com/ActivityWatch/activitywatch/releases/latest/download/activitywatch-linux-x86_64.zip
unzip activitywatch-linux-x86_64.zip -d /opt/activitywatch
cd /opt/activitywatch && ./start.sh
```

```bash
# Install on macOS
brew install --cask activitywatch
```

### Docker Deployment

While ActivityWatch is primarily a desktop application, you can self-host the sync server to centralize data from multiple devices:

```yaml
services:
  activitywatch:
    image: activitywatch/activitywatch:latest
    container_name: activitywatch
    restart: unless-stopped
    ports:
      - "5600:5600"
    volumes:
      - aw-data:/root/.config/activitywatch
      - /etc/localtime:/etc/localtime:ro
    environment:
      - TZ=UTC

volumes:
  aw-data:
    driver: local
```

Access the dashboard at `http://your-server:5600`. The server accepts API connections from desktop clients for centralized data aggregation.

## Kimai: Professional Multi-User Timesheet Management

[Kimai](https://github.com/kimai/kimai) is a web-based time-tracking application designed for teams and businesses. With over 4,600 stars, it is one of the most mature open-source time-tracking platforms available. Kimai focuses on manual time entry, project management, and reporting -- making it ideal for agencies, consultancies, and freelance teams.

### Key Features

- **Multi-user support**: Unlimited users with role-based access control (admin, teamlead, user).
- **Project and customer management**: Organize time entries by client, project, and activity type.
- **Invoicing**: Generate professional invoices directly from tracked time with configurable rates.
- **Export formats**: CSV, XLSX, PDF, and HTML exports for reporting.
- **REST API**: Full-featured API for integrations with external tools.
- **Plugins**: Marketplace with 50+ plugins for authentication, payment gateways, and custom reports.
- **Multi-language**: Supports 30+ languages out of the box.

### Docker Deployment with PostgreSQL

Kimai runs as a PHP/Symfony application and pairs well with PostgreSQL for production:

```yaml
services:
  kimai:
    image: kimai/kimai2:latest
    container_name: kimai
    restart: unless-stopped
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=postgresql://kimai:kimai_password@db:5432/kimai?serverVersion=15&charset=utf8
      - ADMINMAIL=admin@example.com
      - ADMINPASS=change_me_on_first_login
      - APP_ENV=prod
      - TRUSTED_PROXIES=127.0.0.1,REMOTE_ADDR
    volumes:
      - kimai-data:/opt/kimai/var
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:15-alpine
    container_name: kimai-db
    restart: unless-stopped
    environment:
      - POSTGRES_DB=kimai
      - POSTGRES_USER=kimai
      - POSTGRES_PASSWORD=kimai_password
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U kimai"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  kimai-data:
    driver: local
  postgres-data:
    driver: local
```

After starting the stack, log in at `http://your-server:8001` with the admin credentials defined in the environment variables. Create projects, assign activities, and start tracking time immediately.

## Ever Gauzy: Full-Stack Business Platform with Time Tracking

[Ever Gauzy](https://github.com/ever-co/ever-gauzy) is much more than a time tracker. It is a comprehensive business management platform that combines ERP, CRM, HRM, project management, and time tracking into a single application. With 3,600+ stars, it targets organizations that need an integrated solution rather than point tools.

### Key Features

- **Time tracking**: Manual and automatic tracking with screenshot monitoring.
- **Employee management**: HR profiles, role assignments, and team organization.
- **Project management**: Kanban boards, task assignments, and sprint planning.
- **Invoicing and billing**: Generate invoices from tracked time with tax calculations.
- **CRM**: Contact management, deal pipelines, and sales tracking.
- **Inventory management**: Product catalog, stock tracking, and warehouse management.
- **Expense tracking**: Receipt scanning, approval workflows, and reimbursement.

### Docker Deployment

Gauzy ships with an official `docker-compose.yml` file that includes all dependencies:

```yaml
services:
  api:
    image: ghcr.io/ever-co/gauzy-api:latest
    container_name: gauzy-api
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - API_HOST=0.0.0.0
      - API_PORT=3000
      - DB_HOST=db
      - DB_PORT=5432
      - DB_NAME=gauzy
      - DB_USER=gauzy
      - DB_PASS=gauzy_password
      - CLOUD_PROVIDER=DO
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:15-alpine
    container_name: gauzy-db
    restart: unless-stopped
    environment:
      - POSTGRES_DB=gauzy
      - POSTGRES_USER=gauzy
      - POSTGRES_PASSWORD=gauzy_password
    volumes:
      - gauzy-postgres:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U gauzy"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  gauzy-postgres:
    driver: local
```

Access the Gauzy dashboard at `http://your-server:3000`. The initial setup wizard guides you through configuring your organization, users, and time-tracking preferences.

## Comparison Table

| Feature | ActivityWatch | Kimai | Ever Gauzy |
|---|---|---|---|
| **Primary Focus** | Automated activity monitoring | Professional timesheets & invoicing | Full business management platform |
| **GitHub Stars** | 17,400+ | 4,600+ | 3,600+ |
| **License** | MPL-2.0 | AGPL-3.0 | AGPL-3.0 |
| **Language** | Python | PHP (Symfony) | TypeScript (NestJS/Angular) |
| **Time Entry** | Automatic (background watchers) | Manual (start/stop) | Manual + automatic + screenshots |
| **Multi-User** | Limited (sync server) | Full (unlimited users, RBAC) | Full (unlimited users, RBAC) |
| **Invoicing** | No | Yes (built-in, exportable) | Yes (integrated with billing) |
| **Project Management** | No | Yes (projects, customers, activities) | Yes (Kanban, tasks, sprints) |
| **CRM / ERP** | No | No | Yes (full CRM, inventory, HR) |
| **REST API** | Yes | Yes | Yes |
| **Database** | SQLite / PostgreSQL | PostgreSQL / MySQL | PostgreSQL |
| **Docker Support** | Community images | Official images + community | Official images |
| **Mobile Apps** | Android (watcher) | No native app | No native app |
| **Best For** | Personal productivity tracking | Freelancers, agencies, teams | Organizations needing full ERP/CRM |

## Which One Should You Choose?

### Choose ActivityWatch if:
- You want **automatic, passive tracking** without manual start/stop entries.
- Privacy is your top priority -- all data stays on your devices.
- You are tracking personal productivity and want deep insights into how you spend time.
- You prefer a lightweight solution focused solely on activity monitoring.

### Choose Kimai if:
- You need **professional timesheet management** with project and customer organization.
- You run a consultancy or agency and need to **generate invoices from tracked time**.
- You want a mature, web-based platform with extensive plugin support.
- Your team needs multi-user access with role-based permissions.

### Choose Ever Gauzy if:
- You need time tracking as part of a **broader business management platform**.
- Your organization already uses separate tools for CRM, HR, and project management, and wants to consolidate.
- You want screenshot monitoring alongside time entries for remote team oversight.
- You are building an internal ERP/CRM system and time tracking is one module.

## FAQ

### Can I use ActivityWatch to track time for billing clients?

ActivityWatch is designed for personal productivity insights rather than billing. It automatically categorizes activity but does not have built-in invoicing or client billing features. If you need to bill clients based on tracked time, Kimai or Ever Gauzy are better choices as they include invoicing modules.

### Does Kimai support automatic time tracking?

Kimai is primarily a manual time-tracking application. Users start and stop timers or enter time entries directly. However, the plugin ecosystem includes integrations with browser extensions, IDE plugins, and automation tools that can partially automate time entry. For fully automatic background tracking, ActivityWatch is the better option.

### Can I migrate data from Toggl or Clockify to these self-hosted tools?

Kimai supports CSV import, which means you can export your Toggl or Clockify data as CSV and import it. ActivityWatch uses its own data format but has API endpoints that can accept imported data. Ever Gauzy also supports CSV-based imports for time entries and project data.

### How do I back up my time-tracking data?

For ActivityWatch, back up the SQLite database file (default location: `~/.local/share/activitywatch/`). For Kimai and Ever Gauzy, both use PostgreSQL -- use `pg_dump` to create regular backups of the database volume. The Docker Compose examples above include named volumes that can be backed up with `docker volume backup` or by copying the volume data directory.

### Can I run multiple time-tracking tools together?

Yes. A common setup is ActivityWatch on each workstation for automatic activity capture, with Kimai on a central server for project management and invoicing. ActivityWatch data can be exported and correlated with Kimai entries for a complete picture of both automatic activity logging and billable time tracking.

### Is there a mobile app for any of these tools?

ActivityWatch has an official Android watcher app that tracks app usage and screen time on mobile devices. Kimai and Ever Gauzy do not have native mobile apps, but both have responsive web interfaces that work well on mobile browsers. Third-party community projects have built Kimai mobile apps, though they are not officially maintained.

### Which tool has the best API for custom integrations?

All three provide REST APIs. Kimai has the most comprehensive and well-documented API, covering users, customers, projects, activities, timesheets, exports, and invoices. ActivityWatch's API focuses on querying and submitting activity data. Ever Gauzy's API covers the full breadth of its business modules. If you need deep integration with external billing or project management systems, Kimai's API is the most mature. For teams building custom billing integrations, our [Lago vs KillBill billing platforms guide](../2026-04-21-lago-vs-killbill-open-source-billing-platforms-guide/) covers self-hosted billing APIs that can pair with your time-tracking data.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "ActivityWatch vs Kimai vs Ever Gauzy: Self-Hosted Time Tracking Guide",
  "description": "Compare three open-source self-hosted time tracking solutions: ActivityWatch for automated activity monitoring, Kimai for professional timesheet management with invoicing, and Ever Gauzy for full-stack business operations.",
  "datePublished": "2026-05-01",
  "dateModified": "2026-05-01",
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
