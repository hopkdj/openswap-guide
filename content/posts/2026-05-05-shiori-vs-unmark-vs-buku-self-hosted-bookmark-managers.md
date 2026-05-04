---
title: "Shiori vs Unmark vs Buku: Best Self-Hosted Bookmark Managers 2026"
date: 2026-05-05
tags: ["comparison", "guide", "self-hosted", "bookmark-manager", "productivity"]
draft: false
description: "Compare three lightweight self-hosted bookmark managers in 2026. Shiori, Unmark, and Buku offer different approaches to managing your bookmarks without sending data to third-party servers."
---

Managing bookmarks across devices has become a genuine privacy concern. Browser-synced bookmarks are convenient, but they give companies a detailed map of your reading habits, interests, and research patterns. The solution is a self-hosted bookmark manager — a service you control entirely, running on your own infrastructure.

This guide compares three distinct approaches to self-hosted bookmark management: **Shiori**, a clean Go-based web application; **Unmark**, a task-oriented bookmark tracker built for developers; and **Buku**, a powerful command-line bookmark manager with a web interface. Each takes a different philosophy to the same problem, and understanding their differences will help you pick the right tool.

## Why Self-Host Your Bookmarks?

Browser-synced bookmarks are vulnerable to account compromises, service shutdowns, and data harvesting. When you store bookmarks on a self-hosted server, you own the data completely. There are no sync limits, no privacy policies to worry about, and no risk of a company discontinuing its bookmark service.

Self-hosted bookmark managers also offer features browsers simply cannot: full-text search across saved pages, tag-based organization, automated screenshot capture, public sharing of curated collections, and API access for automation. For developers and researchers, these capabilities transform bookmarks from a passive list into an active knowledge management system.

For teams that need shared bookmark collections, self-hosting eliminates the friction of commercial solutions like Diigo or Raindrop.io, which charge per-user fees. A single server instance serves unlimited users at zero marginal cost.

## Shiori

Shiori is a minimalist bookmark manager written in Go. It focuses on simplicity: save a URL, get a clean title, description, and cached copy of the page. The web interface is responsive and fast, designed for users who want zero-friction bookmark management.

**Key Features:**
- Single binary with no external dependencies beyond SQLite
- Built-in web interface with clean, responsive design
- Full-text search across saved pages
- Tag-based organization with autocomplete
- Import/export from browser HTML bookmark files
- REST API for programmatic access
- Docker support with official image

Shiori stores a cached copy of each page, so your bookmarks remain accessible even if the original site goes down. The import tool handles Chrome, Firefox, and Safari bookmark exports natively.

### Docker Compose Setup

```yaml
version: "3.8"
services:
  shiori:
    image: ghcr.io/go-shiori/shiori:latest
    container_name: shiori
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - shiori-data:/srv/shiori
    environment:
      - SHIORI_DIR=/srv/shiori

volumes:
  shiori-data:
```

Start with `docker compose up -d`, then visit `http://your-server:8080` to create your admin account.

## Unmark

Unmark takes a different approach — it treats bookmarks as tasks. Each saved URL can be marked as "to read," "reading," "read," or "archived," making it ideal for developers who maintain a queue of articles, tutorials, and documentation to work through.

**Key Features:**
- Kanban-style workflow: mark bookmarks as to-do, in-progress, or done
- Color-coded labels for categorization
- Markdown notes attached to each bookmark
- Full-text search via SQLite FTS
- API for integrating with other tools
- Import from browser bookmark HTML files
- Multi-user support with role-based access

Unmark is particularly useful for development teams that need to track which documentation or tutorials each member has reviewed. The task-oriented workflow turns a static bookmark list into an actionable knowledge queue.

### Docker Compose Setup

```yaml
version: "3.8"
services:
  unmark:
    image: docker.io/cdevreesse/unmark:latest
    container_name: unmark
    restart: unless-stopped
    ports:
      - "8081:80"
    volumes:
      - unmark-data:/var/www/html/app/database
    environment:
      - UNMARK_DB_TYPE=sqlite

volumes:
  unmark-data:
```

## Buku

Buku (Bookmark Manager) is a command-line-first tool written in Python. It stores bookmarks in a SQLite database and provides a powerful CLI for searching, tagging, and organizing. The optional web UI (buku server mode) adds a browser interface for users who prefer point-and-click interaction.

**Key Features:**
- Lightning-fast CLI with regex search and tag filtering
- Automatic title and comment fetching from web pages
- Privacy mode: store encrypted bookmarks with GPG
- Browser extensions for Chrome, Firefox, and others
- Web server mode with JSON API
- Import from browser HTML, Pocket, and Pinboard exports
- Network share support for multi-machine setups

Buku excels for power users who live in the terminal. You can search bookmarks with `buku --grep keyword`, filter by tag with `buku --tag python`, and open the Nth bookmark with `buku --open 3`. The GPG encryption option means you can safely store bookmarks containing sensitive URLs.

### Docker Compose Setup

```yaml
version: "3.8"
services:
  buku:
    image: docker.io/linuxserver/buku:latest
    container_name: buku
    restart: unless-stopped
    ports:
      - "8082:5000"
      - "8083:8080"
    volumes:
      - buku-config:/config
      - buku-data:/data
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Etc/UTC

volumes:
  buku-config:
  buku-data:
```

## Feature Comparison

| Feature | Shiori | Unmark | Buku |
|---------|--------|--------|------|
| Language | Go | PHP | Python |
| Interface | Web | Web | CLI + Web |
| Database | SQLite | SQLite | SQLite |
| Full-text search | Yes | Yes (FTS) | Yes (regex) |
| Tag support | Yes | Yes (labels) | Yes |
| Page caching | Yes | No | No |
| Task workflow | No | Yes | No |
| GPG encryption | No | No | Yes |
| Browser extension | No | No | Yes |
| Docker image | Official (GHCR) | Community | LinuxServer.io |
| Multi-user | Yes | Yes | Shared DB |
| API | REST | REST | JSON |
| Resource usage | ~30 MB RAM | ~100 MB RAM | ~50 MB RAM |

## Which Should You Choose?

**Choose Shiori** if you want a simple, fast, visually clean bookmark manager that just works. It is ideal for personal use or small teams that need a central bookmark repository with page caching.

**Choose Unmark** if you treat bookmarks as a task queue. The Kanban-style workflow is perfect for developers, researchers, or content creators who need to track their reading progress across hundreds of saved URLs.

**Choose Buku** if you are a terminal power user who wants maximum control. The CLI interface, regex search, and GPG encryption make it the most powerful option for technical users who want privacy and speed.

## Why Self-Host Your Bookmark Manager?

Browser-synced bookmarks are vulnerable to account breaches, service deprecation, and corporate data collection. A self-hosted bookmark manager gives you complete ownership of your saved links, with no limits on storage, tags, or sharing.

For teams, self-hosted bookmarks eliminate the need for paid services like Raindrop.io or Diigo. A single server handles unlimited users with zero per-seat licensing. The data stays on your infrastructure, searchable and accessible through a consistent API.

For developers, bookmark managers with APIs enable automation: sync bookmarks to CI pipelines, generate reading lists from project tags, or build custom dashboards. See our [bookmark manager comparison with Linkding and Wallabag](../self-hosted-bookmark-managers-linkding-shaarli-wallabag/) and [read-later tools guide](../linkwarden-vs-wallabag-vs-shaarli-self-hosted-read-later-tools-guide-2026/) for additional options.

## FAQ

### What is the best self-hosted bookmark manager for beginners?

Shiori is the easiest to set up and use. It requires only a single Docker container with SQLite, has a clean web interface, and handles browser bookmark imports automatically. No configuration files or database setup is needed.

### Can I migrate from browser bookmarks to these tools?

Yes. All three tools support importing from the HTML bookmark export format that Chrome, Firefox, Safari, and Edge produce. In your browser, go to Bookmark Manager → Export Bookmarks, then use the import function in your chosen tool.

### Do these tools support tags?

Yes. Shiori uses a simple tag system with autocomplete. Unmark uses color-coded labels that serve the same purpose. Buku has the most advanced tagging with hierarchical tag support and regex-based tag searching.

### Can multiple users share a bookmark collection?

Yes. Shiori and Unmark both support multi-user accounts with separate bookmark collections and optional shared bookmarks. Buku uses a shared SQLite database, so all users see the same bookmarks (suitable for single-user or trusted-team environments).

### How much storage do bookmark managers need?

Minimal. Without page caching, a bookmark database with 10,000 entries typically uses under 50 MB. With page caching enabled (Shiori), storage grows to roughly 1-5 MB per bookmark depending on page size. A 50 GB disk can comfortably store 100,000+ cached bookmarks.

### Can I access my bookmarks via API?

Yes. Shiori provides a REST API for CRUD operations on bookmarks. Unmark has a REST API for managing bookmarks and labels. Buku runs an optional HTTP server with a JSON API for programmatic access.

### Are these tools suitable for production use?

All three are mature projects with active communities. Shiori has over 11,000 GitHub stars, Buku has been developed since 2015, and Unmark is actively maintained. For production deployments, ensure regular database backups and use a reverse proxy with HTTPS.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Shiori vs Unmark vs Buku: Best Self-Hosted Bookmark Managers 2026",
  "description": "Compare three lightweight self-hosted bookmark managers in 2026. Shiori, Unmark, and Buku offer different approaches to managing your bookmarks without sending data to third-party servers.",
  "datePublished": "2026-05-05",
  "dateModified": "2026-05-05",
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
