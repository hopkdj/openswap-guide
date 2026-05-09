---
title: "Self-Hosted Flat-File Markdown Notes: Flatnotes vs Dendron vs HedgeDoc 2026"
date: "2026-05-23T09:00:00+00:00"
draft: false
tags: ["notes", "markdown", "self-hosted", "knowledge-management", "documentation"]
---

Flat-file note-taking systems store your knowledge as plain Markdown files in a directory structure, eliminating database dependencies and lock-in. Your notes remain readable with any text editor, version-controllable with Git, and easily migratable between platforms. Three open-source tools excel in this space: **Flatnotes**, **Dendron**, and **HedgeDoc**.

## Why Flat-File Notes?

Traditional note-taking apps store data in proprietary databases, making migration difficult and tying your knowledge to a specific platform. Flat-file systems take a different approach:

- **No database required** — notes are plain text files in a folder structure
- **Git-compatible** — version control, branching, and collaboration through standard Git workflows
- **Platform independence** — read your notes with any text editor on any operating system
- **Future-proof** — Markdown is a stable, widely supported format that will remain readable for decades
- **Simple backup** — copy the directory; no database dumps or export processes needed
- **Search-friendly** — grep, ripgrep, or any text search tool works directly on your notes

For teams and individuals who value data ownership and portability, flat-file notes are the most resilient knowledge management approach available.

## Flatnotes

Flatnotes is a self-hosted, database-less note-taking web app that stores notes as plain Markdown files. It provides a clean search interface and full-text indexing without requiring any database setup.

**GitHub**: [dullage/flatnotes](https://github.com/dullage/flatnotes) — 3,029 stars

### Key Features

- **Zero database** — reads and writes directly to a mounted directory of Markdown files
- **Full-text search** — fast search across all notes with real-time results
- **Markdown editor** — built-in editor with live preview
- **Tag support** — organize notes with tags
- **Clean UI** — minimalist, fast-loading interface
- **Docker native** — single-container deployment

### Docker Compose Configuration

```yaml
services:
  flatnotes:
    image: dullage/flatnotes:latest
    container_name: flatnotes
    ports:
      - "8080:8080"
    environment:
      - FLATNOTES_AUTH_TYPE=password
      - FLATNOTES_USERNAME=admin
      - FLATNOTES_PASSWORD=secretpassword
      - FLATNOTES_SECRET_KEY=a-long-secret-key-for-sessions
    volumes:
      - ./notes:/data
      - ./config:/config
    restart: unless-stopped
```

Flatnotes excels at simple, fast note storage and retrieval. It is ideal for personal knowledge bases, documentation archives, and teams that want a no-fuss searchable Markdown repository.

## Dendron

Dendron is a hierarchical note-taking and knowledge management tool built on VS Code. It uses a unique hierarchy-based organization system with schema enforcement and powerful linking capabilities.

**GitHub**: [dendronhq/dendron](https://github.com/dendronhq/dendron) — 7,394 stars

### Key Features

- **Hierarchical organization** — notes organized in a tree structure (daily.journal, projects.active.docs)
- **Schema enforcement** — define structures for note hierarchies to maintain consistency
- **Bidirectional linking** — link notes in both directions with automatic backlink discovery
- **Graph view** — visualize connections between notes
- **VS Code integration** — works within the VS Code ecosystem with full editor features
- **Publishing** — export notes as a static website
- **Markdown native** — all notes stored as .md files

### Self-Hosted Publishing Setup

Dendron can publish notes as a static site using Dendron CLI:

```yaml
services:
  dendron-publish:
    image: node:20-alpine
    container_name: dendron-publish
    working_dir: /workspace
    volumes:
      - ./notes:/workspace
    command: >
      sh -c "
        npm init -y &&
        npm install @dendronhq/cli &&
        npx dendron-cli publish init &&
        npx dendron-cli publish export --output /workspace/site
      "
```

Dendron is best suited for developers and technical teams who want structured knowledge management with the power of VS Code's editing environment. Its hierarchy system scales well for large knowledge bases with hundreds or thousands of notes.

## HedgeDoc

HedgeDoc (formerly CodiMD) is a real-time collaborative Markdown editor that stores notes as files. It supports simultaneous editing, slide presentations, and a rich set of Markdown extensions.

**GitHub**: [hedgedoc/hedgedoc](https://github.com/hedgedoc/hedgedoc) — actively maintained, well-known collaborative editor

### Key Features

- **Real-time collaboration** — multiple users edit the same note simultaneously
- **Markdown extensions** — math (KaTeX), diagrams (Mermaid), code highlighting
- **Slide mode** — convert any note into a presentation with separator slides
- **Export formats** — PDF, HTML, raw Markdown, OpenDocument
- **File-based storage** — notes stored as Markdown files
- **Authentication** — LDAP, OAuth, local accounts
- **Revision history** — track changes with built-in version history

### Docker Compose Configuration

```yaml
services:
  hedgedoc:
    image: quay.io/hedgedoc/hedgedoc:latest
    container_name: hedgedoc
    ports:
      - "3000:3000"
    environment:
      - CMD_DB_URL=postgres://hedgedoc:password@postgres:5432/hedgedoc
      - CMD_DOMAIN=notes.example.com
      - CMD_PROTOCOL_USESSL=true
      - CMD_ALLOW_FREEURL=true
      - CMD_ALLOW_EMAIL_REGISTER=true
    depends_on:
      - postgres
    restart: unless-stopped

  postgres:
    image: postgres:16-alpine
    container_name: hedgedoc-db
    environment:
      - POSTGRES_USER=hedgedoc
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=hedgedoc
    volumes:
      - hedgedoc_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  hedgedoc_data:
```

While HedgeDoc uses a database for metadata (user accounts, sessions, note permissions), the actual note content is stored as Markdown and can be exported at any time. It bridges the gap between flat-file simplicity and collaborative features.

## Feature Comparison

| Feature | Flatnotes | Dendron | HedgeDoc |
|---------|-----------|---------|----------|
| Storage format | Flat Markdown files | Flat Markdown files | Database + Markdown export |
| Database required | ❌ No | ❌ No | ✅ Yes (PostgreSQL) |
| Full-text search | ✅ Built-in | ✅ VS Code search | ✅ Basic search |
| Real-time collaboration | ❌ | ❌ | ✅ Yes |
| Hierarchical notes | Via folders | ✅ Native (dot notation) | Via notebooks |
| Markdown editor | ✅ Simple | ✅ VS Code powered | ✅ Rich with preview |
| Slide presentations | ❌ | ❌ | ✅ Yes |
| Graph view | ❌ | ✅ Yes | ❌ |
| Schema enforcement | ❌ | ✅ Yes | ❌ |
| Export options | Files (already flat) | Static site, files | PDF, HTML, MD, ODT |
| Authentication | Password | N/A (VS Code extension) | LDAP, OAuth, local |
| Docker deployment | ✅ Single container | Manual setup | ✅ Multi-container |
| Best for | Personal notes, docs | Developer knowledge base | Team collaboration |

## Why Self-Host Your Notes?

Storing personal and team knowledge on your own infrastructure provides several advantages over cloud-based alternatives:

**Data ownership and privacy**: Your notes contain sensitive information — project plans, personal ideas, meeting notes, technical documentation. Self-hosting ensures this data never leaves your control. No third-party analytics, no data mining, no unexpected policy changes affecting access.

**Offline availability**: Flat-file notes are always accessible, even without internet connectivity. Mount the directory on any machine and your entire knowledge base is available. This is crucial for field work, travel, or environments with unreliable connectivity.

**Version control integration**: With notes stored as plain files, Git provides complete version history, branching for experimental documentation, and pull-request workflows for team review. Every change is tracked, every version recoverable.

**Cost savings**: Cloud note-taking services charge per user, per storage tier, or for advanced features. Self-hosted flat-file notes cost nothing beyond your server infrastructure — no per-seat licensing, no storage limits, no feature paywalls.

**Integration flexibility**: Flat files integrate with any tool — CI/CD pipelines can validate documentation, scripts can process notes automatically, and static site generators can publish them as websites. Database-locked notes require specific APIs and export processes.

For teams already using a wiki engine, our [Mediawiki vs XWiki vs DokuWiki comparison](../2026-04-23-mediawiki-vs-xwiki-vs-dokuwiki-self-hosted-wiki-engines-guide-2026/) and [knowledge management platforms guide](../2026-05-01-silverbullet-vs-logseq-vs-siyuan-self-hosted-knowledge-engines/) cover database-backed alternatives.(../2026-04-23-mediawiki-vs-xwiki-vs-dokuwiki-self-hosted-wiki-engines-guide-2026/) covers database-backed alternatives. If you need encrypted note storage, see our [Standard Notes vs Joplin vs Cryptee guide](../2026-05-09-self-hosted-encrypted-note-taking-standard-notes-vs-joplin-vs-cryptee-guide/). For broader knowledge management platforms, the [Silverbullet vs Logseq vs Siyuan article](../2026-05-01-silverbullet-vs-logseq-vs-siyuan-self-hosted-knowledge-engines/) explores note-taking with more features.

## FAQ

### What does "flat-file" mean for note storage?

Flat-file means each note is stored as an individual file (typically .md for Markdown) in a directory structure, rather than in a database. There are no tables, schemas, or database engines involved — just files in folders that any operating system can read.

### Can I use Git with flat-file notes?

Yes, this is one of the primary advantages. Since notes are plain files, you can initialize a Git repository in your notes directory and get full version control: commit history, branching for experimental documentation, merge conflict resolution for team edits, and remote backups via any Git hosting service.

### Is search fast without a database?

Modern flat-file note apps use full-text indexing — they build an index of all note content when notes are created or modified. Search queries run against this index, not by scanning every file each time. Flatnotes, for example, provides instant search results across thousands of notes.

### What happens if I want to switch to a different note app later?

With flat-file notes, migration is trivial: your notes are already in standard Markdown format. Any Markdown-compatible note app can read them. There is no proprietary format to convert, no database schema to migrate, and no export process to run.

### Can multiple people edit flat-file notes simultaneously?

Flatnotes and Dendron do not support real-time simultaneous editing. HedgeDoc does — it uses operational transformation (similar to Google Docs) to merge concurrent edits. For Git-based collaboration, team members can edit notes independently and merge changes through Git pull requests.

### Are flat-file notes suitable for large teams?

Flat-file notes work well for small to medium teams (up to ~50 users). Beyond that, consider a database-backed solution with fine-grained permissions, audit logging, and conflict resolution. The file-system approach scales well for reading and searching but can face challenges with concurrent writes from many users.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Flat-File Markdown Notes: Flatnotes vs Dendron vs HedgeDoc 2026",
  "description": "Compare flat-file Markdown note systems: Flatnotes, Dendron, and HedgeDoc. Self-hosted knowledge management without databases.",
  "datePublished": "2026-05-23",
  "dateModified": "2026-05-23",
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
