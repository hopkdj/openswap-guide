---
title: "HedgeDoc vs Etherpad: Best Self-Hosted Collaborative Editor 2026"
date: 2026-04-20
tags: ["comparison", "guide", "self-hosted", "collaboration"]
draft: false
description: "Compare HedgeDoc and Etherpad for self-hosted real-time collaborative editing. Docker deployment guides, feature comparison, and which tool fits your workflow in 2026."
---

Real-time collaborative editing has transformed how teams work together on documents, notes, and technical content. Whether you are writing meeting minutes, drafting technical documentation, or brainstorming project ideas, having a self-hosted collaborative editor gives you full control over your data without relying on cloud services like Google Docs.

Two open-source projects dominate this space: [HedgeDoc](https://hedgedoc.org), a markdown-first collaborative editor, and [Etherpad](https://etherpad.org), the veteran rich-text collaborative platform with 18,000+ stars on GitHub. In this guide, we will compare both tools head-to-head, walk through Docker deployments, and help you choose the right one for your team.

## Why Self-Host a Collaborative Editor

Running your own collaborative editing server offers several advantages over cloud-based alternatives:

**Data sovereignty.** Every document you create stays on your infrastructure. No third-party server processes your content, no analytics track your editing patterns, and no terms-of-service changes can suddenly restrict your access. For organizations handling sensitive information — legal teams, healthcare providers, government agencies — self-hosting eliminates the compliance risks of sending documents to external providers.

**No usage limits.** Cloud collaborative editors often impose restrictions on document count, collaborators per document, or storage quotas. A self-hosted instance has no artificial caps. Your only limit is the server hardware you provision.

**Customization and integration.** Self-hosted tools can be tailored to your workflow. You can integrate with your existing authentication system (LDAP, OAuth, SAML), customize the editor appearance, and connect to your internal tools via APIs or webhooks.

**Cost predictability.** Once deployed, your only ongoing costs are server hosting and maintenance. There are no per-user licenses, no premium tier upgrades, and no surprise price hikes.

For teams that also need structured knowledge management, our [Wiki.js vs BookStack vs Outline comparison](../wiki-js-vs-bookstack-vs-outline/) covers wiki-style alternatives. If you need visual collaboration alongside text editing, check our [self-hosted whiteboard tools guide](../self-hosted-whiteboard-tools-excalidraw-wbo-drawio-guide/).

## HedgeDoc: Markdown-First Collaborative Editing

HedgeDoc is the community fork of CodiMD, created when the original HackMD open-source project shifted focus. It provides a split-screen markdown editor with real-time collaboration, slide presentation mode, and support for mathematical formulas, diagrams, and code syntax highlighting.

As of April 2026, HedgeDoc has over 7,000 GitHub stars and is actively maintained under the AGPL-3.0 license. The project recently restructured into a modern frontend/backend architecture with separate Docker images for each component.

### Key Features

- **Real-time collaborative editing** with live cursor positions and user presence indicators
- **Split-pane preview** — write markdown on the left, see rendered output on the right
- **Slide mode** — transform any document into a presentation using separator syntax
- **Math rendering** via KaTeX for inline and block equations
- **Diagram support** including Mermaid, PlantUML, Graphviz, and Vega-Lite
- **Code syntax highlighting** for 100+ programming languages via highlight.js
- **Guest access** and user accounts with local authentication
- **Image upload** with configurable backend (filesystem, S3, Imgur)
- **Export options** — PDF, HTML, raw markdown, styled HTML

### HedgeDoc Docker Deployment

HedgeDoc 2.0 uses a microservices architecture with separate frontend, backend, and database containers. Here is a production-ready Docker Compose setup:

```yaml
services:
  backend:
    image: ghcr.io/hedgedoc/hedgedoc/backend:latest
    restart: unless-stopped
    volumes:
      - ./backend.env:/usr/src/app/backend/.env
      - hedgedoc_uploads:/usr/src/app/backend/uploads

  frontend:
    image: ghcr.io/hedgedoc/hedgedoc/frontend:latest
    restart: unless-stopped
    environment:
      HD_BASE_URL: "https://docs.example.com"

  db:
    image: postgres:15
    restart: unless-stopped
    environment:
      POSTGRES_USER: "hedgedoc"
      POSTGRES_PASSWORD: "your-secure-password"
      POSTGRES_DB: "hedgedoc"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  proxy:
    image: caddy:latest
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data

volumes:
  hedgedoc_uploads:
  postgres_data:
  caddy_data:
```

Create a `backend.env` file with your database and session configuration:

```env
HD_BASE_URL="https://docs.example.com"
HD_SESSION_SECRET="generate-a-long-random-string-here"
HD_DATABASE_TYPE="postgres"
HD_DATABASE_HOST="db"
HD_DATABASE_PORT="5432"
HD_DATABASE_NAME="hedgedoc"
HD_DATABASE_USERNAME="hedgedoc"
HD_DATABASE_PASSWORD="your-secure-password"
HD_MEDIA_BACKEND="filesystem"
HD_MEDIA_BACKEND_FILESYSTEM_UPLOAD_PATH="uploads/"
HD_AUTH_LOCAL_ENABLE_LOGIN="true"
HD_AUTH_LOCAL_ENABLE_REGISTER="true"
```

Start the stack with `docker compose up -d`. HedgeDoc will be available at your configured base URL with automatic HTTPS via Caddy.

## Etherpad: The Veteran Collaborative Editor

Etherpad has been around since 2011, making it one of the oldest open-source real-time collaborative editors. With over 18,000 GitHub stars and a massive plugin ecosystem, it is the most widely deployed self-hosted collaborative editing solution.

Unlike HedgeDoc's markdown focus, Etherpad uses a rich-text editing model similar to Google Docs. Users see formatted text directly in the editor, with support for bold, italic, lists, tables, images, and more.

### Key Features

- **Real-time collaborative editing** with color-coded author attribution for each change
- **Rich-text WYSIWYG editor** — no markdown knowledge required
- **Plugin ecosystem** — over 1,000 community plugins for extended functionality
- **Time-slider** — replay the entire editing history of any document
- **Import/export** — supports HTML, Word (.docx), PDF, OpenDocument, and plain text
- **Embeddable pads** — embed collaborative documents in any webpage via iframe
- **API** — comprehensive HTTP API for programmatic pad management
- **Multi-database support** — PostgreSQL, MySQL, SQLite, MongoDB, Redis, CouchDB
- **Group management** — organize pads into groups with shared access control
- **Comments and chat** — inline comments and a built-in sidebar chat per pad

### Etherpad Docker Deployment

Etherpad uses a simpler single-container architecture. Here is a production-ready Docker Compose configuration with PostgreSQL:

```yaml
services:
  app:
    image: etherpad/etherpad:latest
    restart: unless-stopped
    user: "5001:0"
    volumes:
      - plugins:/opt/etherpad-lite/src/plugin_packages
      - etherpad-var:/opt/etherpad-lite/var
    depends_on:
      - postgres
    environment:
      NODE_ENV: production
      ADMIN_PASSWORD: "your-admin-password"
      DB_TYPE: "postgres"
      DB_HOST: postgres
      DB_PORT: 5432
      DB_NAME: "etherpad"
      DB_USER: "etherpad"
      DB_PASS: "your-secure-password"
      DB_CHARSET: "utf8mb4"
      TRUST_PROXY: "true"
      DISABLE_IP_LOGGING: "true"
    ports:
      - "9001:9001"

  postgres:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: "etherpad"
      POSTGRES_PASSWORD: "your-secure-password"
      POSTGRES_USER: "etherpad"
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
  plugins:
  etherpad-var:
```

Run `docker compose up -d` and access Etherpad at `http://your-server:9001`. For production, place a reverse proxy (Nginx, Caddy, or Traefik) in front to handle HTTPS termination. Our [OAuth2-proxy vs Pomerium vs Traefik forward auth guide](../oauth2-proxy-vs-pomerium-vs-traefik-forward-auth-2026/) covers authentication options you can add on top.

## Head-to-Head Comparison

| Feature | HedgeDoc | Etherpad |
|---------|----------|----------|
| **Editor type** | Markdown with live preview | Rich-text WYSIWYG |
| **Learning curve** | Requires markdown knowledge | Familiar to any document user |
| **Real-time sync** | Yes, operational transforms | Yes, operational transforms |
| **Math equations** | KaTeX (built-in) | Via ep_mathjax plugin |
| **Diagrams** | Mermaid, PlantUML, Vega (built-in) | Via plugins |
| **Slide mode** | Yes, built-in | Via ep_slide plugin |
| **Syntax highlighting** | 100+ languages (built-in) | Via ep_syntaxhighlighting |
| **Plugin ecosystem** | Limited | 1,000+ plugins |
| **Time-slider / history** | Revision history | Full time-slider replay |
| **Comments** | No | Yes, inline comments |
| **Chat** | No | Yes, per-pad sidebar chat |
| **API** | REST API | Comprehensive HTTP API |
| **Authentication** | Local, LDAP, OAuth2, SAML | Local, LDAP, OAuth, ep_openid_connect |
| **Image handling** | Filesystem, S3, Imgur | Base64 embedded or via plugins |
| **Export formats** | PDF, HTML, raw markdown | HTML, Word, PDF, ODT, plain text |
| **Embed support** | Yes (read-only iframe) | Yes (editable iframe) |
| **License** | AGPL-3.0 | Apache-2.0 |
| **GitHub stars** | 7,097 | 18,250 |
| **Database** | PostgreSQL | PostgreSQL, MySQL, SQLite, MongoDB, Redis |
| **Docker complexity** | 4 containers (front/back/db/proxy) | 2 containers (app/db) |

## Which One Should You Choose?

### Choose HedgeDoc if:

- **Your team writes in markdown.** Developers, technical writers, and DevOps engineers who already use markdown daily will feel right at home. The split-pane editor lets you see formatting instantly without switching modes.
- **You need built-in diagrams and math.** HedgeDoc includes Mermaid, PlantUML, Graphviz, and KaTeX out of the box. No plugin hunting required.
- **You want presentation mode.** The built-in slide mode transforms any document into a deck using `---` separators. Great for team meetings and tech talks.
- **You prefer a cleaner interface.** HedgeDoc's UI is focused and minimal — just the editor, the preview, and a toolbar.

### Choose Etherpad if:

- **Your team needs WYSIWYG editing.** Non-technical users, managers, and general staff who are used to Word or Google Docs will find Etherpad's rich-text editor intuitive.
- **You need a large plugin ecosystem.** With over 1,000 plugins, Etherpad can be extended with spell checking, video embedding, todo lists, QR codes, and much more.
- **You need inline comments and chat.** Etherpad's per-pad chat and comment system supports real-time discussion alongside editing.
- **You need granular access control.** Etherpad's group and pad API lets you programmatically create, manage, and share documents with specific users.
- **You want maximum flexibility in databases.** Etherpad supports PostgreSQL, MySQL, SQLite, MongoDB, Redis, and CouchDB — pick whatever fits your existing infrastructure.

For teams that need a combination of structured documentation and collaborative editing, consider pairing Etherpad with a wiki like [BookStack](../wiki-js-vs-bookstack-vs-outline/) for persistent knowledge and using Etherpad for live collaborative sessions.

## HedgeDoc vs Etherpad: Feature Summary

| Use Case | Recommended Tool | Why |
|----------|-----------------|-----|
| Developer documentation | HedgeDoc | Markdown native, code highlighting, diagrams |
| Technical writing with math | HedgeDoc | KaTeX and Mermaid built-in |
| Team meeting notes | Etherpad | Rich text, chat, comments |
| Non-technical team collaboration | Etherpad | Familiar WYSIWYG interface |
| Quick presentations | HedgeDoc | Built-in slide mode |
| Enterprise with LDAP/SSO | Both | Both support LDAP and OAuth |
| Maximum extensibility | Etherpad | 1,000+ plugin ecosystem |
| Minimal deployment | Etherpad | 2 containers vs HedgeDoc's 4 |
| AGPL compliance requirement | HedgeDoc | Copyleft license ensures derivatives stay open |
| Apache license preference | Etherpad | Permissive license for commercial integration |

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "HedgeDoc vs Etherpad: Best Self-Hosted Collaborative Editor 2026",
  "description": "Compare HedgeDoc and Etherpad for self-hosted real-time collaborative editing. Docker deployment guides, feature comparison, and which tool fits your workflow in 2026.",
  "datePublished": "2026-04-20",
  "dateModified": "2026-04-20",
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

## FAQ

### What is the main difference between HedgeDoc and Etherpad?

HedgeDoc is a markdown-first collaborative editor with a split-pane live preview, making it ideal for developers and technical writers. Etherpad uses a rich-text WYSIWYG editor that resembles Google Docs, making it more accessible to non-technical users. Both support real-time collaborative editing but target different audiences and workflows.

### Can HedgeDoc and Etherpad be used together?

Yes. Many teams run both tools side by side. HedgeDoc serves developers who prefer markdown and need built-in diagram and math support, while Etherpad handles general team collaboration, meeting notes, and documents that non-technical staff need to edit. Both can share the same authentication backend (LDAP or OAuth).

### Is HedgeDoc a fork of CodiMD?

Yes. HedgeDoc originated as a community fork of CodiMD, which itself was a fork of HackMD's open-source version. The HedgeDoc project was created to ensure the codebase remains fully open-source and community-driven. It has since evolved significantly with a new frontend/backend architecture in version 2.0.

### How many users can collaborate simultaneously?

Both HedgeDoc and Etherpad support dozens of simultaneous editors on a single document. The practical limit depends on your server's CPU and memory. Etherpad has been tested with 50+ concurrent editors on modest hardware. HedgeDoc's WebSocket-based sync handles similar loads, though the split architecture means you should size the backend container accordingly.

### Do I need a reverse proxy for either tool?

For production use, yes. HedgeDoc 2.0 includes Caddy as a built-in proxy option in its Docker Compose setup, providing automatic HTTPS with Let's Encrypt. Etherpad exposes port 9001 directly and expects you to place a reverse proxy (Nginx, Caddy, or Traefik) in front for TLS termination, URL rewriting, and additional security headers.

### Can I migrate documents between HedgeDoc and Etherpad?

Direct migration is not seamless due to different storage formats. HedgeDoc stores raw markdown, while Etherpad stores attributed text in its own format. However, both tools support export: HedgeDoc can export plain markdown, and Etherpad can export plain text or HTML. You can convert markdown to Etherpad by pasting it into a new pad, though formatting will need manual adjustment.

### Which tool has better mobile support?

Etherpad's responsive design works reasonably well on tablets and larger phones for viewing and light editing. HedgeDoc's split-pane interface is optimized for desktop screens and can feel cramped on mobile. For mobile-heavy teams, Etherpad is the better choice, though neither tool matches the mobile experience of native apps.
