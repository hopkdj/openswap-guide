---
title: "WeKan vs Kanboard vs Planka: Best Self-Hosted Kanban Boards 2026"
date: 2026-04-19
tags: ["comparison", "guide", "self-hosted", "kanban", "project-management"]
draft: false
description: "Complete comparison of self-hosted kanban board tools — WeKan, Kanboard, and Planka. Docker setup guides, feature breakdowns, and migration tips for replacing Trello and Jira."
---

## Why Self-Host Your Kanban Boards?

Kanban boards are the backbone of agile project management for teams of all sizes. Trello and Jira dominate the market, but relying on cloud-based tools introduces several problems that self-hosting eliminates:

- **Data ownership**: Your project plans, task details, and team workflows stay on your infrastructure. No third-party scans your board data for advertising or product analytics.
- **No subscription creep**: Trello Business Class starts at $10/user/month and scales quickly. Jira jumps to $8.15/user/month for teams over 10. Self-hosted kanban tools cost nothing beyond your server.
- **Offline resilience**: Self-hosted tools remain accessible during internet outages, VPN disruptions, or when a SaaS provider has downtime.
- **Deep customization**: Open-source kanban tools let you modify the code, add plugins, and integrate with your existing self-hosted stack — CI/CD, git servers, wikis, and chat platforms.
- **Regulatory compliance**: Industries with strict data handling rules (healthcare, finance, government) often cannot store project data on third-party cloud servers.

Below, we compare the three most popular open-source, self-hosted kanban solutions available in 2026.

## At a Glance: Live Project Stats

| Project | GitHub Stars | Last Updated | Language | License | Best For |
|---------|-------------|--------------|----------|---------|----------|
| **WeKan** | 20,901 | April 18, 2026 | JavaScript (Meteor) | MIT | Teams wanting Trello-like experience |
| **Kanboard** | 9,555 | April 4, 2026 | PHP | MIT | Minimalist, resource-constrained setups |
| **Planka** | 11,868 | April 18, 2026 | JavaScript (React/Node.js) | AGPL-3.0 | Modern UI with real-time collaboration |

## WeKan — The Trello Alternative

WeKan is the most feature-complete open-source Trello clone. Built on the Meteor framework, it supports real-time updates, drag-and-drop cards, labels, checklists, and a robust permission system.

### Key Features

- **Real-time collaboration**: Changes appear instantly for all users viewing the same board
- **Swimlanes**: Horizontal lanes for organizing cards by category, team, or priority
- **Custom fields**: Add text, number, date, dropdown, and checkbox fields to cards
- **Templates**: Create board and card templates for recurring workflows
- **REST API**: Full API for integration with external tools and scripts
- **Webhooks**: Trigger external services on card events
- **Multi-language**: Translated into 50+ languages

### [docker](https://www.docker.com/) Compose Setup

WeKan ships with a comprehensive `docker-compose.yml` that handles MongoDB, SMTP, and the application in one file:

```yaml
name: wekan

services:
  wekandb:
    image: mongo:6
    container_name: wekan-database
    restart: always
    volumes:
      - wekan-db-data:/data/db
      - wekan-db-dump:/data/dump
    command: mongod --storageEngine wiredTiger --bind_ip_all

  wekan:
    image: wekanteam/wekan:latest
    container_name: wekan
    restart: always
    ports:
      - "8080:8080"
    environment:
      - MONGO_URL=mongodb://wekandb:27017/wekan
      - ROOT_URL=https://kanban.example.com
      - MAIL_URL=smtp://smtp.example.com:25
      - MAIL_FROM=kanban@example.com
      - WITH_API=true
    depends_on:
      - wekandb

volumes:
  wekan-db-data:
  wekan-db-dump:
```

Start it with:

```bash
mkdir -p ~/wekan && cd ~/wekan
curl -sSLO https://raw.githubusercontent.com/wekan/wekan/master/docker-compose.yml
# Edit ROOT_URL and MAIL_URL before starting
docker compose up -d
```

Access the board at `http://your-server:8080`. The default admin credentials are registered on first launch through the web interface.

## Kanboard — The Lightweight Classic

Kanboard takes a minimalist approach. Written in PHP with no JavaScript framework dependencies, it runs on any LAMP/LEMP stack and consumes minimal resources. Its philosophy is simplicity: a clean kanban board with just the features you need.

### Key Features

- **Plugin ecosystem**: 100+ official plugins adding calendar views, Gantt charts, subtask time tracking, and integrations with GitLab, GitHub, Slack, and more
- **Automatic actions**: Trigger actions based on rules (e.g., "when a card moves to Done, assign it to the reviewer")
- **Subtasks and time tracking**: Break cards into subtasks, log time spent, and generate reports
- **Multiple authentication backends**: LDAP, reverse proxy, OAuth2, Google, GitHub, GitLab
- **Multiple board views**: Kanban, calendar (month/week), list view, and Gantt chart (via plugin)
- **Low resource footprint**: Runs comfortably on a $5/month VPS with 512MB RAM

### Docker Compose Setup

Kanboard provides separate compose files for each database backend. Here's the PostgreSQL variant:

```yaml
name: kanboard

services:
  app:
    image: kanboard/kanboard:latest
    container_name: kanboard
    restart: always
    ports:
      - "8080:80"
      - "8443:443"
    volumes:
      - kanboard-data:/var/www/app/data
      - kanboard-plugins:/var/www/app/plugins
      - kanboard-certs:/etc/nginx/ssl
    environment:
      DATABASE_URL: postgres://kanboard:kanboard_secret@db/kanboard
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:16-alpine
    container_name: kanboard-db
    restart: always
    volumes:
      - kanboard-db-data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: kanboard
      POSTGRES_PASSWORD: kanboard_secret
      POSTGRES_DB: kanboard
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U kanboard -d kanboard"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  kanboard-data:
  kanboard-plugins:
  kanboard-certs:
  kanboard-db-data:
```

For the quickest start, use the SQLite variant (single container, no database dependency):

```yaml
name: kanboard

services:
  app:
    image: kanboard/kanboard:latest
    container_name: kanboard
    restart: always
    ports:
      - "8080:80"
    volumes:
      - kanboard-data:/var/www/app/data
      - kanboard-plugins:/var/www/app/plugins

volumes:
  kanboard-data:
  kanboard-plugins:
```

Launch with:

```bash
docker compose -f docker-compose.sqlite.yml up -d
```

Default login: `admin` / `admin` (change immediately after first login).

## Planka — The Modern Choice

Planka is the newest of the three, built with React on the frontend and Node.js/Express on the backend. It features a polished, modern UI that rivals commercial kanban tools, with real-time updates powered by WebSockets.

### Key Features

- **Modern UI**: Clean, responsive design built with React and Semantic UI
- **Real-time updates**: WebSocket-powered live updates — no page refreshes needed
- **Labels and custom backgrounds**: Color-coded labels and board background images
- **OIDC/OAuth2 support**: Native OpenID Connect integration for enterprise SSO
- **Project hierarchy**: Organize boards into projects for team-level management
- **Attachment support**: Upload files to cards with S3-compatible storage
- **Activity tracking**: Full audit log of card changes, assignments, and movements
- **Self-contained**: Comes with its own PostgreSQL dependency, no external plugins needed

### Docker Compose Setup

Planka's compose file is straightforward and includes PostgreSQL:

```yaml
services:
  planka:
    image: ghcr.io/plankanban/planka:latest
    restart: on-failure
    volumes:
      - planka-data:/app/data
    ports:
      - "3000:1337"
    environment:
      - BASE_URL=http://localhost:3000
      - DATABASE_URL=postgresql://postgres@postgres/planka
      - SECRET_KEY=change_this_to_a_random_string
    depends_on:
      postgres:
        condition: service_healthy

  postgres:
    image: postgres:16-alpine
    restart: on-failure
    volumes:
      - planka-db-data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=planka
      - POSTGRES_HOST_AUTH_METHOD=trust
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d planka"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  planka-data:
  planka-db-data:
```

Start it:

```bash
mkdir -p ~/planka && cd ~/planka
# Save the compose above as docker-compose.yml
# Change SECRET_KEY to a random string (e.g., openssl rand -hex 32)
docker compose up -d
```

Access at `http://your-server:3000`. Create your admin account on first visit.

## Detailed Feature Comparison

| Feature | WeKan | Kanboard | Planka |
|---------|-------|----------|--------|
| **Interface** | Trello-like, Meteor-based | Classic, PHP-rendered | Modern React SPA |
| **Real-time updates** | ✅ Yes (Meteor livequery) | ❌ No (manual refresh) | ✅ Yes (WebSockets) |
| **Swimlanes** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Subtasks** | ✅ Checklists | ✅ Full subtask system | ✅ Yes |
| **Time tracking** | ❌ No | ✅ Yes (built-in) | ❌ No |
| **Gantt charts** | ❌ No | ✅ Yes (plugin) | ❌ No |
| **Calendar view** | ❌ No | ✅ Yes (built-in) | ❌ No |
| **Custom fields** | ✅ Yes | ✅ Yes (plugin) | ❌ Limited |
| **REST API** | ✅ Full API | ✅ API (plugin) | ✅ Swagger API |
| **Webhooks** | ✅ Yes | ✅ Yes (plugin) | ❌ No |
| **LDAP/OAuth2** | ✅ LDAP, OAuth2 | ✅ LDAP, OAuth2, reverse proxy | ✅ OIDC |
| **Plugins** | Limited | 100+ official plugins | None (extensible via API) |
| **Mobile app** | ❌ Responsive web | ❌ Responsive web | ❌ Responsive web |
| **File attachments** | ✅ Yes | ✅ Yes | ✅ Yes (S3 optional) |
| **Board templates** | ✅ Yes | ❌ No | ❌ No |
| **Multi-language** | ✅ 50+ | ✅ Yes | ✅ Yes |
| **Database** | MongoDB | SQLite/MySQL/PostgreSQL | PostgreSQL |
| **Resource usage** | Medium (Meteor + MongoDB) | Low (PHP + SQLite) | Medium (Node.js + PostgreSQL) |
| **Minimum RAM** | ~512MB | ~128MB | ~256MB |

## Which One Should You Choose?

### Choose WeKan if:
- You want the closest open-source equivalent to Trello
- Real-time collaboration is essential for your team
- You need custom fields, templates, and a rich feature set
- You already run MongoDB or don't mind the dependency

### Choose Kanboard if:
- You have limited server resources (runs on a Raspberry Pi)
- You want extensive plugin support (Gantt, calendar, time tracking, integrations)
- You prefer a simple, no-frills interface
- You want the flexibility to use SQLite for single-user setups
- Time tracking and subtask management are important

### Choose Planka if:
- You want a modern, visually polished interface
- Your organization uses OIDC/OAuth2 for single sign-on
- You prefer PostgreSQL over MongoDB
- You value real-time updates without the com[plex](https://www.plex.tv/)ity of Meteor
- Your team is small to medium (under 50 concurrent users)

## Migration from Trello or Jira

All three tools support importing data from Trello:

- **WeKan**: Native Trello import — export your Trello board as JSON, then import via Settings → Import → Trello
- **Kanboard**: Install the `KanboardTrelloImport` plugin, upload the Trello JSON export
- **Planka**: Supports Trello board import via the UI — use the import button on a new board

For Jira migrations, none of the three tools offer direct import. The recommended approach is:
1. Export Jira issues as CSV
2. Clean and reformat the CSV to match your target tool's import format
3. Use the tool's CSV import feature (available in WeKan and Kanboard via plugins)

For teams with complex Jira workflows, Kanboard's plugin ecosystem offers the most flexibility for replicating Jira's custom workflows, transitions, and automation rules.

## Reverse Proxy Setup with HTTPS

All three kanban tools should sit behind a reverse proxy for HTTPS termination. Here's a Caddy configuration that handles all three on the same server:

```caddy
kanban-wekan.example.com {
    reverse_proxy localhost:8080
}

kanban-kanboard.example.com {
    reverse_proxy localhost:8081
}

kanban-planka.example.com {
    reverse_proxy localhost:3000
}
```

Or a single Nginx configuration for one tool:

```nginx
server {
    listen 80;
    server_name kanban.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name kanban.example.com;

    ssl_certificate /etc/letsencrypt/live/kanban.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/kanban.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

The WebSocket upgrade headers (`Upgrade` and `Connection`) are essential for WeKan and Planka's real-time features to work through a reverse proxy.

## Related Reading

If you're building a self-hosted productivity stack, check out our [wikis and knowledge base comparison](../wiki-js-vs-bookstack-vs-outline/) for team documentation, our [task management guide](../vikunja-vs-todoist-self-hosted-task-management-guide-2026/) for to-do list t[mattermost](https://mattermost.com/)our [collaboration platform overview](../mattermost-vs-rocketchat-vs-zulip/) for team chat integration.

## FAQ

### Can I run multiple kanban tools on the same server?
Yes. Each tool runs in its own Docker containers with isolated databases. Map them to different host ports (e.g., WeKan on 8080, Kanboard on 8081, Planka on 3000) and use a reverse proxy to route by domain name or path.

### Which kanban tool uses the least server resources?
Kanboard is the lightest by a significant margin. With SQLite, it runs on as little as 128MB of RAM and can comfortably serve a small team on a $5/month VPS. WeKan (MongoDB + Meteor) and Planka (PostgreSQL + Node.js) each need around 256-512MB for smooth operation.

### Do any of these tools have mobile apps?
None of the three offer native mobile apps. All three provide responsive web interfaces that work on mobile browsers. WeKan has had community-driven mobile app attempts, but none are actively maintained as of 2026.

### Can I migrate between these kanban tools?
Direct migration between WeKan, Kanboard, and Planka is not natively supported. The recommended approach is to export boards to CSV or JSON from the source tool and re-import into the target tool. Some community scripts exist for WeKan → Kanboard migration via JSON intermediate format.

### Which tool is best for a solo user?
Kanboard with SQLite is ideal for solo use. It requires no separate database server, runs in a single Docker container, and the plugin system lets you add exactly the features you need without bloat.

### Are these tools suitable for enterprise teams?
Planka has native OIDC support, making it the easiest to integrate with enterprise identity providers. WeKan also supports LDAP and OAuth2. Kanboard supports LDAP and reverse proxy authentication. For large teams (50+ concurrent users), WeKan and Planka handle real-time collaboration better than Kanboard.

### How do I back up my kanban data?
For Docker-based deployments, back up the named volumes. WeKan: back up the MongoDB data volume. Kanboard: back up the SQLite file or PostgreSQL dump. Planka: back up the PostgreSQL data volume. Use `docker exec` to create database dumps before stopping containers, or use a tool like [restic](https://restic.net/) for automated encrypted backups.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "WeKan vs Kanboard vs Planka: Best Self-Hosted Kanban Boards 2026",
  "description": "Complete comparison of self-hosted kanban board tools — WeKan, Kanboard, and Planka. Docker setup guides, feature breakdowns, and migration tips for replacing Trello and Jira.",
  "datePublished": "2026-04-19",
  "dateModified": "2026-04-19",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>
