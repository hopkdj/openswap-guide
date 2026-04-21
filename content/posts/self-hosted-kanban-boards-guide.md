---
title: "Self-Hosted Kanban Boards: Kanboard vs WeKan vs Planka vs Focalboard 2026"
date: 2026-04-13
tags: ["comparison", "guide", "self-hosted", "productivity", "project-management"]
draft: false
description: "Compare Kanboard, WeKan, Planka, and Focalboard for self-hosted Kanban project management. Complete Docker setup guides, feature comparison, and production deployment advice for 2026."
---

## Why Self-Host Your Kanban Board?

Commercial project management platforms like Trello, Monday.com, and Asana charge per-user subscription fees, restrict features behind paid tiers, and store every detail of your workflows on their servers. Self-hosting a Kanban board flips this model entirely:

- **Zero per-seat pricing** — invite your entire team without worrying about licensing costs
- **Full data ownership** — task descriptions, attachments, and activity logs never leave your infrastructure
- **Unlimited boards and projects** — scale to hundreds of boards without artificial limits
- **Deep integrations** — connect directly to your self-hosted Git server, CI/CD pipeline, and chat systems without relying on third-party OAuth
- **Custom workflows** — extend the software to match your processes instead of adapting your processes to the software
- **Always available** — no dependency on a vendor's uptime, API rate limits, or pricing policy changes

For small teams, homelab operators, freelancers, and privacy-conscious organizations, self-hosted Kanban boards provide Trello-class functionality with complete autonomy. This guide compares the four leading open-source options and gives you production-ready deployment instructions for each.

## Feature Comparison at a Glance

| Feature | Kanboard | WeKan | Planka | Focalboard |
|---------|----------|-------|--------|------------|
| **License** | MIT | MIT | AGPL-3.0 | MIT |
| **Language** | PHP | JavaScript (Meteor) | React + Node.js | Go + React |
| **Database** | SQLite / MySQL / PostgreSQL | MongoDB | PostgreSQL | SQLite / PostgreSQL |
| **[docker](https://www.docker.com/) Image** | ✅ Official | ✅[mattermost](https://mattermost.com/)| ✅ Official | ✅ Mattermost image |
| **Memory Footprint** | ~50 MB | ~500 MB | ~200 MB | ~150 MB |
| **Real-time Updates** | ❌ Manual refresh | ✅ Live (DDP) | ✅ Live (WebSockets) | ✅ Live (WebSockets) |
| **Kanban View** | ✅ | ✅ | ✅ | ✅ |
| **Table/List View** | ✅ | ✅ | ❌ | ✅ |
| **Calendar View** | ✅ (plugin) | ❌ | ❌ | ✅ |
| **Gantt View** | ✅ (plugin) | ❌ | ❌ | ❌ |
| **Subtasks** | ✅ | ✅ | ✅ | ✅ |
| **Checklists** | ✅ | ✅ | ✅ | ✅ |
| **Labels / Colors** | ✅ | ✅ | ✅ | ✅ |
| **Custom Fields** | ✅ (plugin) | ✅ | ❌ | ✅ |
| **Time Tracking** | ✅ Built-in | ❌ | ✅ Built-in | ❌ |
| **File Attachments** | ✅ Local / S3 | ✅ Local / S3 / GridFS | ✅ Local / S3 | ✅ Local / S3 |
| **Markdown Support** | ✅ | ✅ | ✅ | ✅ |
| **User Management** | ✅ LDAP / OAuth2 / SAML | ✅ LDAP / OAuth2 / SAML | ✅ OAuth2 (OIDC) | ✅ Mattermost SSO |
| **Notification System** | ✅ Email / Webhooks | ✅ Email / Webhooks | ✅ Email | ✅ Mattermost webhooks |
| **API** | ✅ JSON-RPC | ✅ REST | ✅ REST | ✅ REST |
| **Multi-language** | 35+ languages | 20+ languages | English only | 10+ languages |
| **Activity Stream** | ✅ Detailed | ✅ Detailed | ✅ Detailed | ✅ Basic |
| **Swimlanes** | ✅ | ✅ | ❌ | ❌ |
| **WIP Limits** | ✅ Built-in | ❌ | ❌ | ❌ |
| **Automation Rules** | ✅ Built-in | ✅ | ❌ | ❌ |
| **Mobile Responsive** | ⚠️ Basic | ✅ | ✅ | ✅ |

## Kanboard — The Lightweight Powerhouse

Kanboard is the oldest and most battle-tested option in this comparison. First released in 2013, it prioritizes simplicity, performance, and a comprehensive feature set over modern UI aesthetics. Its PHP architecture means it runs on virtually any server, and the plugin ecosystem adds dozens of capabilities beyond the core feature set.

### When to Choose Kanboard

- You want the smallest resource footprint
- You need WIP limits, swimlanes, or Gantt charts
- You require LDAP, OAuth2, or SAML authentication
- You prefer stability and maturity over a flashy interface
- You want built-in time tracking and automation rules

### Docker Compose Deployment

Kanboard runs on a simple PHP stack. The official Docker image packages everything you need:

```yaml
services:
  kanboard:
    image: kanboard/kanboard:latest
    container_name: kanboard
    restart: unless-stopped
    ports:
      - "8080:80"
    volumes:
      - kanboard_data:/var/www/app/data
      - kanboard_plugins:/var/www/app/plugins
      - kanboard_ssl:/etc/nginx/ssl
    environment:
      - DATABASE_URL=postgres://kanboard_user:kanboard_password@db:5432/kanboard
      - MAIL_TRANSPORT=smtp
      - MAIL_SMTP_HOSTNAME=smtp.example.com
      - MAIL_SMTP_PORT=587
      - MAIL_SMTP_USERNAME=alerts@example.com
      - MAIL_SMTP_PASSWORD=your_smtp_password
      - MAIL_SMTP_ENCRYPTION=tls
      - MAIL_FROM=kanboard@example.com
    depends_on:
      - db

  db:
    image: postgres:17-alpine
    container_name: kanboard_db
    restart: unless-stopped
    volumes:
      - kanboard_pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: kanboard_user
      POSTGRES_PASSWORD: kanboard_password
      POSTGRES_DB: kanboard

volumes:
  kanboard_data:
  kanboard_plugins:
  kanboard_ssl:
  kanboard_pgdata:
```

Save this as `docker-compose.yml` and start it:

```bash
mkdir -p ~/kanboard && cd ~/kanboard
# paste the compose file above
docker compose up -d
```

The web interface is available at `http://your-server:8080`. Default credentials are `admin` / `admin` — change these immediately after first login.

### Essential Configuration Steps

**1. Enable LDAP authentication:**

Add to your `config.php` (or set via environment variable):

```php
define('LDAP_AUTH', true);
define('LDAP_SERVER', 'ldap://your-ldap-server');
define('LDAP_PORT', 389);
define('LDAP_USER_BASE_DN', 'ou=users,dc=example,dc=com');
define('LDAP_USER_FILTER', '(&(objectClass=user)(sAMAccountName=%s))');
```

**2. Install popular plugins:**

Kanboard's plugin system is one of its strongest features. Install from the admin panel or via CLI:

```bash
# Inside the Kanboard container
cd /var/www/app/plugins

# Popular plugins:
# - GroupAssign (assign tasks to groups)
# - Budget (budget tracking per project)
# - Timeline (Gantt chart view)
# - Calendar (full calendar view)
# - Automation (advanced automation rules)
# - CustomUserCSS (customize appearance)
```

**3. Set up automation rules:**

Navigate to a project's settings → Actions. Kanboard ships with a powerful built-in automation engine. Example rules:

- "When a task is created in column 'Backlog', assign it to user X"
- "When a task is moved to 'Done', close the task automatically"
- "When a comment is added, send a webhook notification to Slack"
- "When a task has been in 'In Progress' for more than 7 days, change color to red"

## WeKan — The Trello-Like Experience

WeKan most closely replicates the Trello experience. Built on Meteor, it offers real-time collaboration through its Distributed Data Protocol (DDP), meaning changes appear instantly for all users without page refreshes. Its card-based drag-and-drop interface is polished and intuitive.

### When to Choose WeKan

- You want the closest open-source equivalent to Trello
- Real-time collaboration is a priority
- Your team is already familiar with Trello's interface
- You need SAML or OAuth2 for enterprise SSO
- You want a large, active community

### Docker Compose Deployment

WeKan requires MongoDB. The official Docker Compose setup handles everything:

```yaml
services:
  wekan-db:
    image: mongo:7
    container_name: wekan_db
    restart: unless-stopped
    volumes:
      - wekan_db_data:/data/db
    command: mongod --oplogSize 128 --replSet rs0 --bind_ip_all

  wekan-db-init:
    image: mongo:7
    container_name: wekan_db_init
    restart: "no"
    depends_on:
      - wekan-db
    command: >
      mongosh --host wekan-db --eval
      "try { rs.initiate({_id: 'rs0', members: [{_id: 0, host: 'wekan-db:27017'}]}) } catch(e) { print('Already initialized') }"

  wekan:
    image: wekan/wekan:latest
    container_name: wekan
    restart: unless-stopped
    ports:
      - "8080:8000"
    environment:
      - MONGO_URL=mongodb://wekan-db:27017/wekan
      - ROOT_URL=http://your-server:8080
      - MAIL_URL=smtp://alerts%40example.com:your_smtp_password@smtp.example.com:587/
      - MAIL_FROM=wekan@example.com
      - WITH_API=true
      - ACCOUNT_LEVEL=true
    depends_on:
      wekan-db:
        condition: service_started
      wekan-db-init:
        condition: service_completed_successfully

volumes:
  wekan_db_data:
```

The MongoDB replica set initialization is required for WeKan's real-time features. Start it with:

```bash
mkdir -p ~/wekan && cd ~/wekan
docker compose up -d
```

After the containers start, visit `http://your-server:8080` and create your admin account on first launch.

### Useful WeKan Features

**Board Templates:** Create a board, set up your columns and labels, then click "Board Menu" → "More" → "Save as Template." New boards can be created from any saved template, making it easy to standardize workflows across teams.

**Custom Fields:** Add text, number, date, checkbox, dropdown, and user fields to cards. This turns WeKan from a simple task tracker into a lightweight database for inventory, issue tracking, or CRM workflows.

**Card Archiving:** Instead of deleting completed cards, archive them. They remain searchable and can be restored later. The archive is accessible from the board menu and preserves full card history.

## Planka — The Modern Minimalist

Planka is the newest contender in this comparison, built with React on the frontend and Node.js on the backend. It has a clean, modern interface that feels right at home alongside contemporary SaaS tools. While it has fewer features than Kanboard or WeKan, what it offers works exceptionally well.

### When to Choose Planka

- You want a modern, polished UI that looks great out of the box
- Your team prefers simplicity over feature density
- You already run PostgreSQL and want to reuse it
- You need OpenID Connect (OIDC) for SSO
- You want a lightweight alternative to heavy Meteor or PHP stacks

### Docker Compose Deployment

Planka uses PostgreSQL for persistence and provides a straightforward Docker setup:

```yaml
services:
  planka:
    image: ghcr.io/plankanban/planka:latest
    container_name: planka
    restart: unless-stopped
    ports:
      - "8080:1337"
    environment:
      - BASE_URL=http://your-server:8080
      - DATABASE_URL=postgresql://planka_user:planka_password@db:5432/planka
      - SECRET_KEY=replace-this-with-a-random-64-character-string
      - TRUST_PROXY=0
      - DEFAULT_ADMIN_EMAIL=admin@example.com
      - DEFAULT_ADMIN_NAME=Admin
      - DEFAULT_ADMIN_USERNAME=admin
      - DEFAULT_ADMIN_PASSWORD=changeme-now
    volumes:
      - planka_attachments:/app/public/user-attachments
    depends_on:
      - db

  db:
    image: postgres:17-alpine
    container_name: planka_db
    restart: unless-stopped
    volumes:
      - planka_pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: planka_user
      POSTGRES_PASSWORD: planka_password
      POSTGRES_DB: planka

volumes:
  planka_attachments:
  planka_pgdata:
```

Deploy it:

```bash
mkdir -p ~/planka && cd ~/planka
docker compose up -d
```

The `SECRET_KEY` should be a random string of at least 64 characters. Generate one with:

```bash
openssl rand -hex 64
```

### Planka's Strengths

**Real-time Collaboration:** Every action — moving cards, editing descriptions, adding labels — appears instantly for all connected users via WebSocket connections. There's no page refresh required.

**Clean Card Interface:** Planka's card editor is one of the cleanest in the open-source space. It includes checklists, labels, attachments, task assignments, and due dates without feeling cluttered.

**OIDC Integration:** Planka supports OpenID Connect out of[keycloak](https://www.keycloak.org/), making it straightforward to integrate with Keycloak, Authentik, Authelia, or any other OIDC provider.

## Focalboard — The Spreadsheet Meets Kanban Hybrid

Focalboard originated as Mattermost's answer to Trello and Notion's database views. Its defining feature is the ability to switch between multiple views of the same data: Kanban board, table/spreadsheet, gallery, and calendar. This makes it uniquely versatile for teams that need more than just a Kanban view.

### When to Choose Focalboard

- You need multiple views of the same data (Kanban + table + calendar)
- Your team already uses Mattermost and wants integrated project management
- You want spreadsheet-style data entry alongside visual boards
- You prefer Go-based applications for better performance
- You need a Notion-like database experience

### Docker Compose Deployment

Focalboard can run standalone or integrated with Mattermost. For standalone use:

```yaml
services:
  focalboard:
    image: mattermost/focalboard:latest
    container_name: focalboard
    restart: unless-stopped
    ports:
      - "8080:8000"
    volumes:
      - focalboard_data:/opt/focalboard/data
    environment:
      - FB_PUBLIC=true

volumes:
  focalboard_data:
```

For a more robust setup with PostgreSQL:

```yaml
services:
  focalboard:
    image: mattermost/focalboard:latest
    container_name: focalboard
    restart: unless-stopped
    ports:
      - "8080:8000"
    volumes:
      - ./config.json:/opt/focalboard/config.json
      - focalboard_files:/opt/focalboard/files
    environment:
      - FB_PUBLIC=false
    depends_on:
      - db

  db:
    image: postgres:17-alpine
    container_name: focalboard_db
    restart: unless-stopped
    volumes:
      - focalboard_pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: focalboard_user
      POSTGRES_PASSWORD: focalboard_password
      POSTGRES_DB: focalboard

volumes:
  focalboard_files:
  focalboard_pgdata:
```

Create a `config.json` for the PostgreSQL setup:

```json
{
  "serverRoot": "http://your-server:8080",
  "port": 8000,
  "dbtype": "postgres",
  "dbconfig": "postgres://focalboard_user:focalboard_password@db:5432/focalboard",
  "useSSL": false,
  "webpath": "./pack",
  "filespath": "./files",
  "session_expire_time": 2592000,
  "session_refresh_time": 18000,
  "localOnly": false,
  "enableLocalMode": true,
  "localModeSocketLocation": "/var/tmp/focalboard_local.socket"
}
```

Deploy with:

```bash
mkdir -p ~/focalboard && cd ~/focalboard
docker compose up -d
```

Default credentials are `admin` / `admin`. Change the password immediately after first login.

### Focalboard's Multi-View System

**Kanban View:** The classic column-based board with drag-and-drop cards. Supports grouping by any property field.

**Table View:** A spreadsheet-like grid where you can add, sort, and filter rows. Each column can be text, number, date, select, multi-select, person, checkbox, URL, email, phone, or created/updated time. This is Focalboard's killer feature — no other tool in this comparison offers it.

**Gallery View:** A card-based grid view useful for visual browsing of boards with cover images attached to cards.

**Calendar View:** Shows cards on a monthly calendar based on their date properties. Useful for deadline-driven projects.

## Reverse Proxy Setup for All Options

Regardless of which Kanban board you choose, putting it behind a reverse proxy with HTTPS is essential for production use. Here's a universal Nginx configuration that works with all four options:

```nginx
server {
    listen 80;
    server_name kanban.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name kanban.example.com;

    ssl_certificate /etc/letsencrypt/live/kanban.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/kanban.example.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (required for WeKan and Planka)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Obtain the SSL certificate with Certbot:

```bash
sudo certbot certonly --standalone -d kanban.example.com
```

## Backup Strategy

A self-hosted service is only as reliable as its backup strategy. Here's how to back up each tool:

**Kanboard:**
```bash
# SQLite backup
cp /path/to/kanboard/data/db.sqlite /backups/kanboard-$(date +%Y%m%d).sqlite

# PostgreSQL backup
docker exec kanboard_db pg_dump -U kanboard_user kanboard > /backups/kanboard-$(date +%Y%m%d).sql
```

**WeKan:**
```bash
# MongoDB backup
docker exec wekan_db mongodump --archive --gzip > /backups/wekan-$(date +%Y%m%d).gz
```

**Planka:**
```bash
# PostgreSQL backup
docker exec planka_db pg_dump -U planka_user planka > /backups/planka-$(date +%Y%m%d).sql
```

**Focalboard:**
```bash
# SQLite backup
docker cp focalboard:/opt/focalboard/data/focalboard.db /backups/focalboard-$(date +%Y%m%d).db

# PostgreSQL backup
docker exec focalboard_db pg_dump -U focalboard_user focalboard > /backups/focalboard-$(date +%Y%m%d).sql
```

Automate backups with a cron job:

```bash
# Add to crontab: daily backup at 2:00 AM
0 2 * * * /path/to/backup-script.sh
```

## Recommendation Summary

| Scenario | Best Choice | Why |
|----------|------------|-----|
| **Minimal server resources** | Kanboard | Runs on 50 MB RAM, works on a Raspberry Pi |
| **Trello replacement** | WeKan | Closest feature parity and UX to Trello |
| **Modern UI + simplicity** | Planka | Clean React interface, easy setup |
| **Multiple data views** | Focalboard | Kanban + table + calendar + gallery |
| **Enterprise SSO** | Kanboard or WeKan | Full LDAP, OAuth2, and SAML support |
| **Built-in time tracking** | Kanboard or Planka | No plugins or workarounds needed |
| **Automation and WIP limits** | Kanboard | Most powerful built-in automation engine |
| **Mattermost integration** | Focalboard | Native Mattermost authentication and linking |

Each of these tools is production-ready and actively maintained. Your choice depends on whether you prioritize feature depth (Kanboard), Trello familiarity (WeKan), modern simplicity (Planka), or multi-view flexibility (Focalboard). All four can be deployed in under five minutes with Docker and run reliably behind a reverse proxy with HTTPS.

## Frequently Asked Questions (FAQ)

### Which one should I choose in 2026?

The best choice depends on your specific requirements:

- **For beginners**: Start with the simplest option that covers your core use case
- **For production**: Choose the solution with the most active community and documentation
- **For teams**: Look for collaboration features and user management
- **For privacy**: Prefer fully open-source, self-hosted options with no telemetry

Refer to the comparison table above for detailed feature breakdowns.

### Can I migrate between these tools?

Most tools support data import/export. Always:
1. Backup your current data
2. Test the migration on a staging environment
3. Check official migration guides in the documentation

### Are there free versions available?

All tools in this guide offer free, open-source editions. Some also provide paid plans with additional features, priority support, or managed hosting.

### How do I get started?

1. Review the comparison table to identify your requirements
2. Visit the official documentation (links provided above)
3. Start with a Docker Compose setup for easy testing
4. Join the community forums for troubleshooting
