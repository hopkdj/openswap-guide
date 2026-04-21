---
title: "Best Self-Hosted Note-Taking Apps 2026: Joplin vs Trilium vs AppFlowy"
date: 2026-04-12
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete comparison of self-hosted note-taking and knowledge management tools — Joplin, Trilium Notes, and AppFlowy. Docker setup guides, feature breakdowns, and migration tips for replacing Notion and Evernote."
---

## Why Self-Host Your Notes and Knowledge Base?

Your notes contain your most personal and valuable information — research, ideas, credentials, journal entries, and project plans. Entrusting them to cloud services means accepting several risks:

- **Privacy**: Companies scan your content for advertising, training data, or compliance reviews
- **Vendor lock-in**: Proprietary formats make it painful to leave; services shut down without notice
- **Censorship**: Cloud providers can disable accounts or remove content at their discretion
- **Cost**: Premium subscriptions add up — Notion Plus is $10/month, Evernote Professional is $15/month
- **Offline access**: Self-hosted tools work without internet, critical for travel and outages

Self-hosting your knowledge management system gives you full ownership, end-to-end control, and zero recurring fees. Here's how the top three open-source options compare in 2026.

## Feature Comparison

| Feature | Joplin | Trilium Notes | AppFlowy |
|---------|--------|---------------|----------|
| **License** | MIT | AGPL-3.0 | AGPL-3.0 |
| **Best For** | General note-taking | Personal knowledge base | Notion replacement |
| **Editor** | Markdown + WYSIWYG | Rich text + code | Block-based (Notion-style) |
| **E2E Encryption** | ✅ Yes | ❌ No (server-side) | ❌ No |
| **Web Clipper** | ✅ Yes | ✅ Yes | ❌ No |
| **Mobile Apps** | ✅ iOS + Android | ❌ Responsive web only | ✅ iOS + Android |
| **Desktop Apps** | ✅ Win/Mac/Linux | ✅ Win/Mac/Linux | ✅ Win/Mac/Linux |
| **Self-Hosted Sync** | ✅ Built-in | ✅ Native | ✅ Collaborative server |
| **Database Export** | ✅ JEX, Markdown | ✅ HTML, ZIP | ✅ JSON |
| **Relations/Links** | ✅ Note links | ✅ Full note tree + relations | ✅ Relations + linked databases |
| **Scripting/Automation** | ❌ Limited | ✅ JavaScript plugins | ⚠️ Limited |
| **Version History** | ⚠️ Via sync target | ✅ Built-in | ❌ No |
| **Resource Usage** | Low (~100MB RAM) | Medium (~300MB RAM) | Medium (~400MB RAM) |
| **Multi-User** | ❌ Single user | ⚠️ Limited | ✅ Yes (collaborative) |
| **Calendar/Planner** | ❌ Via plugins | ✅ Built-in | ⚠️ Planned |
| **Diagram Support** | ✅ Mermaid, Excalidraw | ✅ Mermaid, custom | ✅ Basic |

---

## 1. Joplin — The Reliable All-Rounder

**Best for**: Users who want a polished, cross-platform note-taking app with end-to-end encryption and reliable sync.

Joplin is the most mature self-hosted note-taking app in 2026. It's been around since 2016, has a large community, and supports virtually every platform. The key strength is its flexible sync system — you can sync via your own server, WebDAV, Dropbox, OneDrive, S3, or even a local filesystem.

### Key Features

- End-to-end encryption for all synced data
- Markdown editor with WYSIWYG toggle
- Web clipper for Chrome, Firefox, and Safari
- Notebook hierarchy with tags and search
- Plugin system (including community plugins)
- Attachment support (images, PDFs, audio)
- Todo lists with alarms and notifications
- Conflict resolution across devices

### [docker](https://www.docker.com/) Setup (Joplin Server)

The Joplin Server provides optimized sync for Joplin clients. It's much faster than generic WebDAV:

```yaml
# docker-compose.yml
services:
  joplin-db:
    image: postgres:16-alpine
    container_name: joplin-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: joplin
      POSTGRES_PASSWORD: ${JOPLIN_DB_PASS:-SecurePass123}
      POSTGRES_DB: joplin
    volumes:
      - ./joplin-db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U joplin"]
      interval: 10s
      retries: 5

  joplin-server:
    image: joplin/server:latest
    container_name: joplin-server
    restart: unless-stopped
    depends_on:
      joplin-db:
        condition: service_healthy
    ports:
      - "22300:22300"
    environment:
      APP_PORT: 22300
      APP_BASE_URL: https://notes.yourdomain.com
      DB_CLIENT: pg
      POSTGRES_PASSWORD: ${JOPLIN_DB_PASS:-SecurePass123}
      POSTGRES_DATABASE: joplin
      POSTGRES_USER: joplin
      POSTGRES_PORT: 5432
      POSTGRES_HOST: joplin-db
    volumes:
      - ./joplin-data:/home/joplin

  # Optional: Reverse [caddy](https://caddyserver.com/) with Let's Encrypt
  caddy:
    image: caddy:2-alpine
    container_name: joplin-caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy-data:/data
      - caddy-config:/config

volumes:
  caddy-data:
  caddy-config:
```

```
# Caddyfile
notes.yourdomain.com {
    reverse_proxy joplin-server:22300
}
```

### Client Configuration

1. Install Joplin on your device (desktop or mobile)
2. Go to **Tools → Options → Synchronization**
3. Set **Synchronization target** to "Joplin Server"
4. Enter your server URL: `https://notes.yourdomain.com`
5. Create an account on the server admin panel (`/register`)
6. Enable **End-to-end encryption** in the encryption menu

```bash
# Create the initial admin user via CLI
docker exec joplin-server node app.js createAdmin \
  --email admin@yourdomain.com \
  --password YourAdminPassword
```

### Plugin Recommendations

- **Markdown Table of Contents** — Auto-generate TOC from headings
- **Note Tabs** — Open multiple notes in tabs
- **Quick Link** — Link notes with keyboard shortcuts
- **Excalidraw** — Embed hand-drawn diagrams directly in notes
- **Note Overview** — Create dynamic note lists based on tags/folders

---

## 2. Trilium Notes — The Power User's Knowledge Base

**Best for**: Developers and researchers who need a deeply interconnected, scriptable personal wiki with version history and custom attributes.

Trilium Notes takes a fundamentally different approach from traditional note-taking apps. Instead of a flat notebook structure, it uses a hierarchical tree with note cloning (a single note can appear in multiple places), note relations (parent-child, map, and custom), and powerful JavaScript scripting.

### Key Features

- Hierarchical tree with infinite nesting
- Note cloning — same note appears in multiple branches
- Rich note types: text, code, canvas, relation maps, books
- Built-in version history with diff viewer
- JavaScript scripting and automation
- Custom note attributes (labels, inheritance)
- Full-text search with fuzzy matching
- ETAPI (REST API) for external integrations
- Song/mermaid diagram rendering
- Calendar and daily notes built-in

### Docker Setup

```yaml
# docker-compose.yml
services:
  trilium:
    image: zadam/trilium:latest
    container_name: trilium-notes
    restart: unless-stopped
    ports:
      - "28080:8080"
    environment:
      - TRILIUM_DATA_DIR=/home/node/trilium-data
    volumes:
      - ./trilium-data:/home/node/trilium-data
    # Optional: limit memory
    deploy:
      resources:
        limits:
          memory: 512M
```

```bash
# Start the server
docker compose up -d

# The initial setup password is shown in logs on first run
docker logs trilium-notes 2>&1 | grep "password"

# After first login, set up your master password in the UI
# Then disable the startup password in options for convenience
```

### Advanced Configuration

Trilium supports environment variables for advanced setup:

```bash
# Custom port and data directory
docker run -d \
  --name trilium \
  -p 8080:8080 \
  -e TRILIUM_DATA_DIR=/data/trilium \
  -e TRILIUM_PORT=8080 \
  -v /srv/trilium/data:/data/trilium \
  zadam/trilium:latest
```

### Scripting Example: Auto-Organize Notes

One of Trilium's strongest features is built-in scripting. Here's a script that auto-tags notes based on content:

```javascript
// Put this in a note with "Run on note creation" trigger
const content = note.getText().toLowerCase();

if (content.includes("docker")) {
  note.setLabel("topic", "devops");
}
if (content.includes("recipe") || content.includes("ingredient")) {
  note.setLabel("topic", "cooking");
}
if (content.includes("budget") || content.includes("expense")) {
  note.setLabel("topic", "finance");
}

await note.save();
```

### Sync Setup (Two-Way)

Trilium supports syncing between instances for backup and multi-device access:

1. Go to **Options → Sync**
2. Enable sync and set the remote server URL
3. Enter your sync password (separate from login password)
4. The sync is bidirectional — changes propagate both ways

```
Note: Trilium sync is designed for personal use (single user across
devices). It is NOT designed for multi-user collaboration.
```

---

## 3. AppFlowy — The Modern Notion Alternative

**Best for**: Teams and individuals who want a Notion-like block-based editor with local-first storage and collaborative capabilities.

AppFlowy is the newest entrant and has grown rapidly since its 2021 launch. Built with Rust and Flutter, it offers a Notion-style block editor with databases, kanban boards, and calendars — all running locally first with optional self-hosted sync via AppFlowy Cloud.

### Key Features

- Block-based editor (text, images, code, toggles, callouts)
- Grid databases with filters, sorts, and grouping
- Kanban board view for project management
- Calendar view for scheduling
- AI assistant integration (optional, can be disabled)
- Real-time collaboration (self-hosted cloud server)
- Offline-first — works without network connection
- Custom themes and templates
- Import from Notion (via .zip export)

### Docker Setup (AppFlowy Cloud)

AppFlowy Cloud is the self-hosted sync and collaboration server:

```yaml
# docker-compose.yml
services:
  appflowy-db:
    image: postgres:16-alpine
    container_name: appflowy-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: appflowy
      POSTGRES_PASSWORD: ${AF_DB_PASS:-SecurePass456}
      POSTGRES_DB: appflowy
    volumes:
      - ./appflowy-db:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U appflowy"]
      interval: 10s
      retries: 5

  appflowy-redis:
    image: redis:7-alpine
    container_name: appflowy-redis
    restart: unless-stopped
    command: redis-server --requirepass ${AF_REDIS_PASS:-RedisPass789}
    volumes:
      - ./appflowy-redis:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      retries: 5

  appflowy-cloud:
    image: appflowycloud/appflowy-cloud:latest
    container_name: appflowy-cloud
    restart: unless-stopped
    depends_on:
      appflowy-db:
        condition: service_healthy
      appflowy-redis:
        condition: service_healthy
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://appflowy:${AF_DB_PASS:-SecurePass456}@appflowy-db:5432/appflowy
      REDIS_URL: redis://:${AF_REDIS_PASS:-RedisPass789}@appflowy-redis:6379
      API_EXTERNAL_URL: https://flow.yourdomain.com
      GOTRUE_EXTERNAL_GOOGLE_ENABLED: "false"
      GOTRUE_EXTERNAL_GITHUB_ENABLED: "false"
      GOTRUE_MAILER_AUTOCONFIRM: "true"
      GOTRUE_SMTP_ENABLED: "false"
    volumes:
      - ./appflowy-storage:/storage
```

### Caddy Reverse Proxy

```
# Caddyfile
flow.yourdomain.com {
    reverse_proxy appflowy-cloud:8000
}
```

### Client Setup

1. Download AppFlowy from [appflowy.io](https://appflowy.io)
2. On first launch, choose "Self-Host" or "Custom Server"
3. Enter your cloud URL: `https://flow.yourdomain.com`
4. Create your first workspace and start adding pages

### Migrating from Notion

AppFlowy has a Notion import feature:

1. In Notion, go to **Settings → Export all workspace content**
2. Choose **Markdown & CSV** format
3. Download and extract the .zip file
4. In AppFlowy, open **Settings → Import**
5. Select the extracted folder
6. Review imported pages — some com[plex](https://www.plex.tv/) Notion blocks may need manual adjustment

---

## Choosing the Right Tool

### Decision Matrix

| Your Priority | Recommended Tool | Why |
|--------------|-----------------|-----|
| **Privacy & encryption** | Joplin | Only option with E2E encryption |
| **Developer knowledge base** | Trilium Notes | Scripting, versioning, relations |
| **Notion replacement** | AppFlowy | Block editor, databases, collaboration |
| **Mobile access** | Joplin | Full-featured iOS and Android apps |
| **Multi-user team** | AppFlowy | Real-time collaboration support |
| **Personal wiki** | Trilium Notes | Infinite hierarchy, cloning, linking |
| **Low resource usage** | Joplin | Lightest footprint, runs on Pi |
| **Offline reliability** | Joplin / AppFlowy | Both are offline-first by design |

### Hardware Requirements

All three tools run comfortably on minimal hardware:

```bash
# Minimum: Raspberry Pi 4 (4GB RAM)
# Recommended: Any VPS with 2 vCPU / 2GB RAM
# For multiple users: 4 vCPU / 4GB RAM (AppFlowy Cloud benefits from more)

# Example low-cost hosting:
# - Hetzner CX22: €4.51/month (2 vCPU, 4GB RAM)
# - Oracle Cloud Free Tier: Always free (4 ARM cores, 24GB RAM)
# - Raspberry Pi at home: One-time cost, runs 24/7
```

### Security Best Practices

Regardless of which tool you choose, follow these practices:

```bash
# 1. Always use a reverse proxy with TLS
# Caddy handles Let's Encrypt automatically:
echo "notes.yourdomain.com { reverse_proxy localhost:22300 }" > Caddyfile
caddy run

# 2. Use strong, unique passwords
openssl rand -base64 32  # Generate 256-bit random password

# 3. Enable firewall rules
ufw allow 443/tcp
ufw allow 80/tcp
ufw deny 22300/tcp  # Block direct access, only allow via proxy

# 4. Set up automated backups
# For Joplin (PostgreSQL):
docker exec joplin-db pg_dump -U joplin joplin > /backup/joplin-$(date +%F).sql

# For Trilium (filesystem):
tar czf /backup/trilium-$(date +%F).tar.gz ./trilium-data/

# For AppFlowy (PostgreSQL + storage):
docker exec appflowy-db pg_dump -U appflowy appflowy > /backup/appflowy-db-$(date +%F).sql
tar czf /backup/appflowy-storage-$(date +%F).tar.gz ./appflowy-storage/

# Automate with cron (run daily at 2 AM):
# 0 2 * * * /usr/local/bin/backup-notes.sh
```

## Final Recommendation

For most users starting their self-hosted note-taking journey in 2026:

- **Start with Joplin** if you value privacy, cross-platform sync, and a proven reliable app. It's the safest choice with the largest community and best mobile experience.
- **Choose Trilium Notes** if you're technically inclined and want a powerful, interconnected knowledge base with scripting capabilities and version history.
- **Pick AppFlowy** if you're migrating from Notion and want the closest open-source equivalent with block editing, databases, and team collaboration.

You can also run multiple tools — many users keep Joplin for quick notes and mobile capture, while maintaining a Trilium instance as their deep knowledge base. The self-hosted approach means you're not locked into any single ecosystem, and you can export and migrate your data at any time.

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
