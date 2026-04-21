---
title: "Joplin vs Trilium Notes vs AFFiNE: Best Self-Hosted Note-Taking 2026"
date: 2026-04-21
tags: ["comparison", "guide", "self-hosted", "productivity", "note-taking", "knowledge-base"]
draft: false
description: "Compare the three best open-source self-hosted note-taking platforms: Joplin Server, Trilium Notes, and AFFiNE. Docker deployment guides, feature comparison, and recommendations."
---

## Why Self-Host Your Notes and Knowledge Base

Cloud note-taking apps like Notion, Evernote, and Obsidian Sync lock your personal knowledge behind proprietary services with recurring subscriptions. When you self-host, you own your data, control access, eliminate vendor lock-in, and can integrate with your existing infrastructure — all without paying monthly fees.

The three strongest open-source options for self-hosted note-taking in 2026 each take a different approach:

- **Joplin Server** — a sync backend for the Joplin note-taking app, focused on cross-platform note capture with end-to-end encryption.
- **Trilium Notes** — a hierarchical knowledge base with a powerful scripting API, designed for deep personal knowledge management.
- **AFFiNE** — a modern workspace that blends documents, whiteboards, and databases, positioning itself as a Notion and Miro alternative.

## Project Overview and Live Stats

| Feature | Joplin Server | Trilium Notes | AFFiNE |
|---|---|---|---|
| GitHub Stars | 54,446 | 35,647 | 67,496 |
| Last Updated | 2026-04-20 | 2026-04-21 | 2026-04-20 |
| Language | TypeScript | TypeScript | TypeScript |
| License | AGPL-3.0 (server) | AGPL-3.0 | MIT / AGPL-3.0 |
| Database | PostgreSQL / SQLite | SQLite | PostgreSQL |
| E2E Encryption | Yes | No | Planned |
| Real-time Collaboration | No | No | Yes |
| Whiteboard / Canvas | No | No | Yes |
| Mobile Apps | iOS, Android | No | iOS, Android |
| API / Plugin System | Web Clipper, sync API | JavaScript scripting | Block-level API |
| Minimum RAM | 512 MB | 256 MB | 1 GB |

Joplin has the longest track record as a privacy-focused note app with sync. Trilium excels at structured knowledge management with its unique note hierarchy. AFFiNE brings the most modern feature set with real-time collaboration and mixed document/whiteboard editing.

## Joplin Server: Cross-Platform Notes with Sync

Joplin Server acts as a synchronization backend for the Joplin client apps available on Windows, macOS, Linux, Android, and iOS. Your notes are stored locally on each device and synchronized through the server, optionally with end-to-end encryption.

The Joplin ecosystem includes a web clipper browser extension, markdown import/export, notebook organization, and support for attachments and images. The server component itself is lightweight — it handles authentication, note storage, and delta sync without running a full web UI.

### Deploying Joplin Server with Docker Compose

Joplin Server requires a PostgreSQL database. Here is a production-ready `docker-compose.yml`:

```yaml
version: '3'

services:
  db:
    image: postgres:16
    container_name: joplin_db
    restart: unless-stopped
    volumes:
      - ./joplin-db:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD: your-secure-password
      POSTGRES_USER: joplin
      POSTGRES_DB: joplin
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U joplin"]
      interval: 10s
      timeout: 5s
      retries: 5

  joplin-server:
    image: joplin/server:latest
    container_name: joplin_server
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    ports:
      - "22300:22300"
    environment:
      APP_PORT: 22300
      APP_BASE_URL: http://localhost:22300
      DB_CLIENT: pg
      POSTGRES_PASSWORD: your-secure-password
      POSTGRES_DATABASE: joplin
      POSTGRES_USER: joplin
      POSTGRES_PORT: 5432
      POSTGRES_HOST: db
```

Start the stack:

```bash
mkdir -p joplin-db
docker-compose up -d
```

Configure your Joplin clients by navigating to **Tools > Options > Synchronization**, selecting **Joplin Server** as the sync target, and entering `http://your-server-ip:22300` with your admin credentials.

### Key Joplin Server Features

- **End-to-end encryption** — notes are encrypted on the client before syncing, so the server never sees plaintext content.
- **Web clipper** — browser extension to save web pages, articles, and screenshots directly to your notes.
- **Markdown-first** — all notes are stored in markdown, making them portable and future-proof.
- **Notebook hierarchy** — organize notes into nested notebooks with tags for cross-cutting categorization.
- **Attachment support** — images, PDFs, and files sync alongside note text.

For a reverse proxy setup with HTTPS, see our [file sync and sharing guide](../self-hosted-file-sync-sharing-nextcloud-seafile-syncthing-guide/) which covers Traefik and Nginx proxy patterns applicable to Joplin Server as well.

## Trilium Notes: Hierarchical Knowledge Base

Trilium Notes takes a fundamentally different approach. Instead of flat notebooks, it uses a tree-based note hierarchy where every note can have child notes, and notes can appear in multiple locations via **cloning**. This makes it ideal for building a personal wiki or knowledge graph.

The built-in code editor supports syntax highlighting for dozens of languages, and Trilium's scripting API lets you automate note creation, build custom views, and integrate with external services. Notes can contain rich text, markdown, rendered HTML, code blocks, maps, and canvases.

### Deploying Trilium Notes with Docker

Trilium is the simplest to deploy — a single container with no external database required:

```yaml
version: '3'

services:
  trilium:
    image: triliumnext/trilium:latest
    container_name: trilium_notes
    restart: unless-stopped
    environment:
      - TRILIUM_DATA_DIR=/home/node/trilium-data
    ports:
      - "8080:8080"
    volumes:
      - ./trilium-data:/home/node/trilium-data
```

Start the container:

```bash
mkdir -p trilium-data
docker-compose up -d
```

Open `http://your-server-ip:8080` to complete the initial setup. The first visit lets you set a master password and configure the note tree structure.

### Key Trilium Features

- **Note tree with cloning** — hierarchical organization where a single note can appear in multiple branches without duplication.
- **Relation maps** — create visual graphs showing how notes link together, surfacing connections you might miss in linear browsing.
- **Scripting API** — write JavaScript to automate workflows, build custom note types, or integrate with external APIs.
- **Code note types** — dedicated code notes with syntax highlighting and execution support for JavaScript, Python, and more.
- **ETAPI** — RESTful API for programmatic access to notes, enabling integrations with other tools and automation pipelines.
- **Mobile web interface** — responsive design works well in mobile browsers, though no native app exists.

## AFFiNE: Notion and Miro Alternative

AFFiNE positions itself as a next-generation workspace that unifies documents, whiteboards, and databases in a single application. Unlike traditional note-taking apps, AFFiNE lets you switch between page mode (linear document editing) and edgeless mode (infinite canvas) for the same content.

The self-hosted server provides real-time collaboration, workspace management, and cloud sync across desktop and mobile clients. AFFiNE supports markdown, block-based editing, databases with multiple views, and embedded whiteboards — making it the most feature-rich option of the three.

### Deploying AFFiNE with Docker Compose

AFFiNE requires PostgreSQL, Redis, and runs a migration job before the main service starts. Here is the official self-hosted compose configuration:

```yaml
name: affine

services:
  affine:
    image: ghcr.io/toeverything/affine:stable
    container_name: affine_server
    ports:
      - '3010:3010'
    depends_on:
      redis:
        condition: service_healthy
      postgres:
        condition: service_healthy
    volumes:
      - ./affine-storage:/root/.affine/storage
      - ./affine-config:/root/.affine/config
    env_file:
      - .env
    restart: unless-stopped

  redis:
    image: redis:7
    container_name: affine_redis
    healthcheck:
      test: ['CMD', 'redis-cli', '--raw', 'incr', 'ping']
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  postgres:
    image: pgvector/pgvector:pg16
    container_name: affine_postgres
    volumes:
      - ./affine-db:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: affine
      POSTGRES_PASSWORD: your-secure-password
      POSTGRES_DB: affine
      POSTGRES_INITDB_ARGS: '--data-checksums'
    healthcheck:
      test: ['CMD', 'pg_isready', '-U', 'affine', '-d', 'affine']
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
```

Create a `.env` file in the same directory with required variables:

```bash
NODE_ENV=production
SERVER_FLAVOR=affine
AFFINE_ADMIN_EMAIL=admin@example.com
AFFINE_ADMIN_PASSWORD=your-admin-password
DATABASE_URL=postgresql://affine:your-secure-password@postgres:5432/affine
REDIS_SERVER_HOST=redis
MAILER_HOST=smtp.example.com
MAILER_PORT=587
MAILER_USER=noreply@example.com
MAILER_PASSWORD=your-smtp-password
MAILER_SENDER=Affine <noreply@example.com>
```

Start the stack:

```bash
docker compose up -d
```

Access AFFiNE at `http://your-server-ip:3010` and log in with the admin credentials from your `.env` file.

### Key AFFiNE Features

- **Page and edgeless modes** — toggle between traditional document editing and freeform canvas/whiteboard view for the same workspace.
- **Real-time collaboration** — multiple users can edit documents simultaneously, with live cursors and presence indicators.
- **Database views** — create tables, kanban boards, and gallery views from structured data blocks within your pages.
- **Local-first architecture** — data is stored locally first and synced to the server, providing offline access and resilience.
- **Block-based editing** — every element is a movable, nestable block supporting text, images, code, embeds, and databases.
- **Mobile support** — native iOS and Android apps with full sync to your self-hosted server.

## Direct Feature Comparison

| Capability | Joplin Server | Trilium Notes | AFFiNE |
|---|---|---|---|
| Note editing | Markdown, rich text | Rich text, markdown, code, HTML | Block editor, markdown, whiteboard |
| Organization | Notebooks + tags | Tree hierarchy + cloning | Workspaces + pages + databases |
| Sync | Client-server sync | Server-based access | Real-time collaboration sync |
| Encryption | E2E (client-side) | None | In transit (TLS) |
| Search | Full-text, tag filtering | Full-text, attribute-based | Full-text, semantic (vector DB) |
| API | Sync API, WebDAV | ETAPI (REST) | GraphQL + REST |
| Plugins | Desktop plugins | JavaScript scripting | Extensions (in development) |
| Multi-user | Per-account notes | Single user | Workspace collaboration |
| Offline | Full (local-first) | Full (server access) | Partial (local-first, needs sync) |
| Best for | Personal notes across devices | Deep knowledge management | Team collaboration, visual planning |

## Deployment Requirements and Resource Usage

| Requirement | Joplin Server | Trilium Notes | AFFiNE |
|---|---|---|---|
| Minimum RAM | 512 MB | 256 MB | 1 GB |
| Minimum CPU | 1 core | 1 core | 2 cores |
| Storage (base) | ~200 MB + note data | ~100 MB + note data | ~500 MB + workspace data |
| External Services | PostgreSQL | None | PostgreSQL, Redis |
| Docker Images | 2 (server + db) | 1 | 3 (server + db + redis) |
| Backup Complexity | Dump PostgreSQL + data dir | Copy data directory | Dump PostgreSQL + storage volume |
| Reverse Proxy | Standard HTTP | Standard HTTP | Standard HTTP + WebSocket support |

For users already running a self-hosted wiki, note that AFFiNE overlaps with tools like [Wiki.js and BookStack](../wiki-js-vs-bookstack-vs-outline/) in the documentation space, though AFFiNE focuses more on personal and team productivity than public-facing documentation.

## Migration Paths

**From Evernote:** Joplin has the most mature Evernote import tool — it can import `.enex` files with attachments, formatting, and notebook structure intact. Run the import from the desktop client, then notes sync to your self-hosted server.

**From Notion:** Export your Notion workspace as markdown and HTML (Settings > Export), then import into AFFiNE or Trilium. AFFiNE handles Notion-style block structures most naturally, while Trilium requires reorganizing into its tree hierarchy.

**From Obsidian:** Joplin supports markdown import natively. Trilium can import markdown files via its import menu. AFFiNE accepts markdown paste directly into the editor.

## Choosing the Right Tool

**Pick Joplin Server if:**
- You need cross-platform sync between desktop and mobile apps.
- End-to-end encryption is a non-negotiable requirement.
- You prefer a simple, reliable note-taking workflow without complex features.
- You already use or want to use the Joplin client ecosystem.

**Pick Trilium Notes if:**
- You are building a personal knowledge base with deep hierarchical structure.
- You want scripting capabilities to automate note workflows.
- You value a desktop-first experience with powerful organizational tools like cloning and relation maps.
- You prefer the simplest possible deployment (single container, no database).

**Pick AFFiNE if:**
- You need real-time multi-user collaboration on documents.
- You want whiteboard and canvas capabilities alongside traditional notes.
- You are replacing Notion or Miro and need block-based editing with databases.
- You value a modern UI with mobile app support.

## FAQ

### Can I use Joplin without self-hosting a server?

Yes. Joplin supports multiple sync targets including Dropbox, OneDrive, S3-compatible storage, and WebDAV. The Joplin Server is optional but recommended for privacy — it gives you full control over where your note data is stored and enables faster delta sync compared to generic cloud storage.

### Does Trilium Notes support mobile access?

Trilium does not have native mobile apps, but the web interface is responsive and works well in mobile browsers. You can access your notes from any device by pointing a browser to your server's URL. For offline mobile access, consider using the Trilium desktop client with file sync.

### Is AFFiNE stable enough for production use?

AFFiNE's self-hosted server reached stable release status and is suitable for production use. However, as a rapidly evolving project, breaking changes can occur between major versions. Always back up your PostgreSQL database and storage volumes before upgrading, and test updates in a staging environment first.

### Can multiple users share a single Trilium Notes instance?

Trilium is designed as a single-user application. Multiple users cannot have separate accounts on one instance. If you need multi-user support, consider Joplin Server (per-account sync) or AFFiNE (workspace collaboration with role-based access).

### How do I back up each platform?

**Joplin Server:** Back up the PostgreSQL database with `pg_dump` and the server data directory. **Trilium:** Stop the container, then copy the `trilium-data` volume — it contains the entire SQLite database and attachments. **AFFiNE:** Back up the PostgreSQL database and the storage volume (`/root/.affine/storage`). Automate backups with a cron job or use a tool like [restic for backup verification](../restic-vs-borg-vs-kopia-backup-guide/).

### Which platform handles the largest note collections?

Trilium Notes has been tested with 100,000+ notes thanks to its efficient SQLite storage. Joplin handles large collections well but sync performance can degrade with thousands of attachments. AFFiNE's PostgreSQL backend scales well but the block-based editor may slow down with extremely long documents containing hundreds of blocks.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Joplin vs Trilium Notes vs AFFiNE: Best Self-Hosted Note-Taking 2026",
  "description": "Compare the three best open-source self-hosted note-taking platforms: Joplin Server, Trilium Notes, and AFFiNE. Docker deployment guides, feature comparison, and recommendations.",
  "datePublished": "2026-04-21",
  "dateModified": "2026-04-21",
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
