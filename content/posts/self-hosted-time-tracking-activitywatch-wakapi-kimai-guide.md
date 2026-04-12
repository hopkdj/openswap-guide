---
title: "ActivityWatch vs Wakapi vs Kimai: Self-Hosted Time Tracking Guide 2026"
date: 2026-04-12
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete guide to self-hosted time tracking with ActivityWatch, Wakapi, and Kimai. Compare features, privacy, and find the best open-source solution for tracking your time in 2026."
---

If you value your privacy and want full ownership of your productivity data, self-hosted time tracking is the only way to go. Commercial services like Toggl, RescueTime, and Clockify collect detailed behavioral telemetry — when you work, what apps you use, which websites you visit — and store it all on their servers. For developers, freelancers, and anyone handling sensitive client information, this is an unacceptable risk.

Self-hosting your time tracking flips the model: you own the data, you control the retention policy, and no third party ever sees your habits. In this guide, we compare three of the best open-source time tracking tools available today: **ActivityWatch** for automatic desktop monitoring, **Wakapi** for developer coding analytics, and **Kimai** for manual timesheet and invoicing management.

## Why Self-Host Your Time Tracking?

Time tracking data is among the most intimate digital footprints you generate. It reveals:

- **Work patterns** — when you start and stop, how long you focus, when you take breaks
- **Application usage** — which tools and websites you spend time on
- **Project allocation** — what you are billing clients for, internal project priorities
- **Productivity rhythms** — your peak hours, distraction patterns, burnout indicators

When this data lives on a third-party server, it is vulnerable to data breaches, corporate policy changes, and account suspensions. Self-hosting eliminates these risks entirely. Your data never leaves your machine, you can audit the source code, and you can export everything at any time.

Beyond privacy, self-hosted time tracking gives you unlimited history, no per-user pricing, and full API access for building custom dashboards and integrations.

## ActivityWatch: Automatic Desktop Time Tracking

ActivityWatch is the most popular open-source automatic time tracker. It runs as a lightweight daemon on your desktop and records which applications and browser tabs you use, for how long. It is the closest open-source equivalent to RescueTime.

### Key Features

- **Automatic tracking** — no manual start/stop, it just works in the background
- **Cross-platform** — Linux, Windows, and macOS
- **Application and tab-level tracking** — knows you spent 2 hours in VS Code and 30 minutes on GitHub
- **Category system** — assign tags like "Work", "Social", "Entertainment" to classify activity
- **Rich REST API** — query raw data for custom analysis
- **Privacy-first** — all data stored locally, no cloud component

### Architecture

ActivityWatch consists of three parts:

1. **aw-server** — the backend that stores and serves data
2. **aw-watcher-*** — platform-specific watchers (aw-watcher-window for active window tracking, aw-watcher-web for browser extensions)
3. **aw-webui** — the browser-based dashboard

### Installation with Docker

The simplest way to run ActivityWatch server is via Docker:

```bash
docker run -d \
  --name activitywatch \
  --restart unless-stopped \
  -p 5600:5600 \
  -v activitywatch-data:/data \
  -e TZ=UTC \
  activitywatch/activitywatch:latest
```

On Linux, install the native watcher for accurate window tracking:

```bash
# Install via AUR (Arch Linux)
yay -S activitywatch-bin

# Or use the AppImage on Debian/Ubuntu
wget https://github.com/ActivityWatch/activitywatch/releases/latest/download/activitywatch-linux-x86_64.AppImage
chmod +x activitywatch-linux-x86_64.AppImage
./activitywatch-linux-x86_64.AppImage
```

Install the browser extension for tab tracking:

```bash
# Chrome Web Store or Firefox Add-ons
# Search for "ActivityWatch Web Extension"
```

### Configuration

ActivityWatch auto-detects applications. To create custom categories, open the web UI at `http://localhost:5600` and navigate to Settings → Categories. You can define rules like:

```json
{
  "Work": {
    "type": "regex",
    "rule": "vscode|jetbrains|terminal|github|gitlab"
  },
  "Communication": {
    "type": "regex",
    "rule": "slack|discord|telegram|email"
  },
  "Entertainment": {
    "type": "regex",
    "rule": "youtube|netflix|reddit|twitter"
  }
}
```

The query engine uses a custom language called `aw-server` queries for advanced analysis:

```
# Total time in VS Code this week
RETURN = query_bucket("aw-watcher-window_*")
  | filter_keyvals("app", ["vscode"])
  | period_union
  | sum_durations
```

### Best For

- Knowledge workers who want **zero-effort** tracking
- Anyone who previously used RescueTime
- Users who want a detailed picture of **how they spend their day** across all applications

---

## Wakapi: Developer Coding Analytics

Wakapi is a self-hosted backend for the WakaTime protocol. It tracks how much time you spend coding in each language, project, file, and branch — all by integrating directly with your IDE through a lightweight plugin. If you ever wanted metrics on your coding habits without the privacy trade-offs, Wakapi is your answer.

### Key Features

- **IDE-native tracking** — plugins for VS Code, JetBrains, Vim, Neovim, Emacs, and more
- **Language and project breakdowns** — see exactly how your coding time is distributed
- **Branch-level tracking** — compare time spent across Git branches
- **Compatible with WakaTime plugins** — drop-in replacement, no new plugins needed
- **Leaderboards** — friendly team competition (optional)
- **Import from WakaTime** — migrate your existing data

### Installation with Docker

```bash
docker run -d \
  --name wakapi \
  --restart unless-stopped \
  -p 3000:3000 \
  -v wakapi-data:/data \
  muety/wakapi:latest
```

For production use with PostgreSQL:

```yaml
version: "3.8"

services:
  wakapi:
    image: muety/wakapi:latest
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      WAKAPI_DATABASE_DIALECT: postgres
      WAKAPI_DATABASE_HOST: db
      WAKAPI_DATABASE_PORT: 5432
      WAKAPI_DATABASE_NAME: wakapi
      WAKAPI_DATABASE_USER: wakapi
      WAKAPI_DATABASE_PASSWORD: change-me-to-a-strong-password
      WAKAPI_PASSWORD_SALT: another-random-salt-value
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: wakapi
      POSTGRES_PASSWORD: change-me-to-a-strong-password
      POSTGRES_DB: wakapi
    volumes:
      - wakapi-db:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U wakapi"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  wakapi-db:
```

### IDE Configuration

Point your existing WakaTime plugin to your self-hosted Wakapi instance:

**VS Code** (`settings.json`):

```json
{
  "wakapi.apiKey": "your-api-key-from-wakapi-dashboard",
  "wakapi.apiUrl": "http://localhost:3000/api"
}
```

**Neovim** (`init.lua`):

```lua
require("wakatime").setup({
  api_key = "your-api-key-from-wakapi-dashboard",
  api_url = "http://localhost:3000/api",
  api_plugin = "wakapi"
})
```

**JetBrains IDEs** — go to Settings → Other Settings → WakaTime Settings and set:
- API Key: your Wakapi API key
- API URL: `http://localhost:3000/api`

Alternatively, edit the `.wakatime.cfg` file directly:

```ini
[settings]
api_key = your-api-key
api_url = http://localhost:3000/api
```

### Dashboard Features

Wakapi provides a clean dashboard showing:

- **Total coding time** with daily, weekly, and monthly views
- **Language breakdown** — percentage of time per programming language
- **Project distribution** — which repos get the most attention
- **Editor stats** — time spent in each IDE or editor
- **Operating system usage** — for multi-machine developers
- **Branch comparison** — see which branches you spend time on
- **Goals** — set daily coding targets and track progress

### Best For

- Software developers who want **coding-specific** analytics
- Teams that want **leaderboards** without sharing data with a third party
- Anyone already using WakaTime who wants to **self-host** instead

---

## Kimai: Manual Timesheet and Invoicing

Kimai takes a completely different approach. Rather than tracking automatically, it is a professional timesheet management system designed for freelancers, agencies, and teams who need to log billable hours, generate invoices, and manage projects.

### Key Features

- **Manual time tracking** — start/stop timer or enter time entries directly
- **Multi-user support** — manage teams with roles and permissions
- **Project and task management** — organize time by customer, project, and task
- **Invoicing** — generate professional PDF invoices from tracked time
- **Reporting** — detailed reports with export to CSV, XLSX, and PDF
- **Plugins** — extensible marketplace with 50+ plugins
- **REST API** — full programmatic access for integrations

### Installation with Docker

```yaml
version: "3.8"

services:
  kimai:
    image: kimai/kimai2:apache-main
    restart: unless-stopped
    ports:
      - "8001:8001"
    environment:
      APP_ENV: prod
      DATABASE_URL: mysql://kimai:kimai-secret@db:3306/kimai
      ADMINMAIL: admin@yourdomain.com
      ADMINPASS: secure-admin-password
      TRUSTED_HOSTS: localhost,yourdomain.com
    volumes:
      - kimai-data:/opt/kimai/var
    depends_on:
      db:
        condition: service_healthy

  db:
    image: mariadb:11
    restart: unless-stopped
    environment:
      MYSQL_DATABASE: kimai
      MYSQL_USER: kimai
      MYSQL_PASSWORD: kimai-secret
      MYSQL_ROOT_PASSWORD: root-secret
    volumes:
      - kimai-db:/var/lib/mysql
    command:
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_unicode_ci
    healthcheck:
      test: ["CMD", "healthcheck.sh", "--connect", "--innodb_initialized"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  kimai-data:
  kimai-db:
```

After the containers start, create your first admin user:

```bash
docker exec kimai bin/console kimai:create-user \
  admin admin@yourdomain.com ROLE_SUPER_ADMIN
```

### Nginx Reverse Proxy Configuration

For production access, put Kimai behind a reverse proxy:

```nginx
server {
    listen 443 ssl http2;
    server_name kimai.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/kimai.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/kimai.yourdomain.com/privkey.pem;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Essential Plugins

Kimai's plugin ecosystem extends its capabilities significantly:

```bash
# Invoice calculator plugin
cd /opt/kimai/var/plugins
git clone https://github.com/kevinpapst/kimai2-invoice.git

# Export bundle for advanced reporting
git clone https://github.com/kevinpapst/kimai2-export.git

# ActivityHistory for audit trails
git clone https://github.com/ActivityHistory/kimai2-activity-history.git

# Install dependencies and clear cache
docker exec kimai composer install --no-dev --optimize-autoloader
docker exec kimai bin/console cache:clear --env=prod
docker exec kimai bin/console kimai:reload --env=prod
```

### Daily Workflow

1. **Log in** and select your customer and project
2. **Start the timer** when you begin working on a task
3. **Add descriptions** to your time entries for detailed invoicing
4. **Stop the timer** when done, or enter time manually for past work
5. **Generate reports** weekly or monthly
6. **Export invoices** as PDFs and send to clients

### Best For

- Freelancers and consultants who **bill by the hour**
- Agencies that need **team time tracking** with client reporting
- Anyone who needs **professional invoices** generated from tracked time

---

## Feature Comparison

| Feature | ActivityWatch | Wakapi | Kimai |
|---------|---------------|--------|-------|
| **Tracking Method** | Automatic (OS-level) | Automatic (IDE plugin) | Manual (timer/entry) |
| **Primary Use Case** | Personal productivity | Developer coding stats | Billable hours & invoicing |
| **Cross-Platform** | Yes (desktop) | Yes (via IDE plugins) | Yes (web-based) |
| **Multi-User** | No | Yes | Yes |
| **Team Features** | No | Leaderboards | Full team management |
| **Invoicing** | No | No | Yes (PDF export) |
| **API** | REST | REST (WakaTime-compatible) | REST |
| **Database** | SQLite | SQLite / PostgreSQL | MySQL / MariaDB / PostgreSQL |
| **Browser Tracking** | Yes (extension) | No | No |
| **IDE Integration** | Limited | Excellent (all major IDEs) | No |
| **Reporting** | Timeline + categories | Language/project breakdowns | Detailed + exportable |
| **Docker Support** | Yes | Yes | Yes |
| **Mobile App** | No | No | No (mobile web works) |
| **Data Export** | JSON | JSON | CSV, XLSX, PDF |

---

## Choosing the Right Tool

The decision comes down to your workflow:

### Choose ActivityWatch if:
- You want a **complete picture of your day** — not just coding, but everything
- You prefer **zero-config automatic tracking** over manual time entries
- You want to understand **distraction patterns** and improve focus
- You previously used RescueTime and want a self-hosted replacement

### Choose Wakapi if:
- You are a **software developer** who wants language and project breakdowns
- You want to track time across **multiple IDEs and machines**
- You want to compare coding activity with **teammates** via leaderboards
- You already use WakaTime and want to migrate to self-hosted

### Choose Kimai if:
- You **bill clients by the hour** and need professional invoices
- You manage a **team** and need role-based access control
- You need to track time against **specific projects and tasks**
- You want detailed **exportable reports** for accounting

### The Power Combo

Many developers use **Wakapi + Kimai** together: Wakapi for automatic coding analytics and Kimai for client-facing time tracking and invoicing. ActivityWatch can serve as a complementary layer for understanding your full digital day beyond just coding.

All three tools can be deployed on a single low-cost VPS or home server. A modest 2-core, 4GB RAM machine handles all three simultaneously without issue.

---

## Running All Three with Docker Compose

Here is a unified compose file to deploy all three services:

```yaml
version: "3.8"

services:
  # ActivityWatch - Automatic desktop tracking server
  activitywatch:
    image: activitywatch/activitywatch:latest
    restart: unless-stopped
    ports:
      - "5600:5600"
    volumes:
      - aw-data:/data
    environment:
      - TZ=UTC

  # Wakapi - Developer coding analytics
  wakapi:
    image: muety/wakapi:latest
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      WAKAPI_PASSWORD_SALT: "random-salt-here"
    volumes:
      - wakapi-data:/data

  # Kimai - Timesheet and invoicing
  kimai:
    image: kimai/kimai2:apache-main
    restart: unless-stopped
    ports:
      - "8001:8001"
    environment:
      APP_ENV: prod
      DATABASE_URL: mysql://kimai:kimai-secret@kimai-db:3306/kimai
      ADMINMAIL: admin@yourdomain.com
      ADMINPASS: secure-password-here
      TRUSTED_HOSTS: localhost
    volumes:
      - kimai-data:/opt/kimai/var
    depends_on:
      kimai-db:
        condition: service_healthy

  kimai-db:
    image: mariadb:11
    restart: unless-stopped
    environment:
      MYSQL_DATABASE: kimai
      MYSQL_USER: kimai
      MYSQL_PASSWORD: kimai-secret
      MYSQL_ROOT_PASSWORD: root-secret-here
    volumes:
      - kimai-db:/var/lib/mysql
    healthcheck:
      test: ["CMD", "healthcheck.sh", "--connect", "--innodb_initialized"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  aw-data:
  wakapi-data:
  kimai-data:
  kimai-db:
```

Start everything with a single command:

```bash
docker compose up -d
```

Your services will be available at:
- **ActivityWatch**: `http://localhost:5600`
- **Wakapi**: `http://localhost:3000`
- **Kimai**: `http://localhost:8001`

---

## Conclusion

Self-hosted time tracking gives you something no commercial service can: complete ownership of your most personal productivity data. ActivityWatch excels at automatic desktop monitoring, Wakapi delivers deep coding analytics for developers, and Kimai provides professional timesheet and invoicing capabilities.

All three are actively maintained, have strong communities, and can be deployed on minimal hardware. The choice depends entirely on your workflow — and there is no rule saying you can only pick one.

Start with the tool that matches your most pressing need, and expand from there. Your future self will thank you for having years of detailed, private, and fully-owned productivity data.
