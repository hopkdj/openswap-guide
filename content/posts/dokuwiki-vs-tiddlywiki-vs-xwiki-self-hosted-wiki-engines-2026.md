---
title: "DokuWiki vs TiddlyWiki vs XWiki: Best Self-Hosted Wiki Engines 2026"
date: 2026-04-17
tags: ["comparison", "guide", "self-hosted", "wiki", "knowledge-management"]
draft: false
description: "Compare DokuWiki, TiddlyWiki5, and XWiki — the top self-hosted wiki engines. Complete Docker setup guides, feature comparisons, and deployment recommendations for personal and team knowledge bases in 2026."
---

## Why Self-Host Your Own Wiki?

Commercial wiki and knowledge management platforms charge per-user licensing fees, limit storage on free tiers, and retain full control over your documentation. Self-hosting a wiki engine gives you complete ownership of your knowledge base:

- **Zero per-user costs** — invite unlimited team members without licensing fees
- **Full data sovereignty** — all pages, attachments, and edit histories live on your infrastructure
- **No vendor lock-in** — migrate, backup, or export your content at any time using standard formats
- **Private documentation** — host internal runbooks, SOPs, and sensitive project docs without third-party access
- **Offline availability** — access your wiki from your local network even when the internet is down

Whether you are documenting homelab services, building a team knowledge base, or maintaining personal notes, a self-hosted wiki gives you the control and flexibility that cloud platforms cannot match. This guide compares three fundamentally different approaches to self-hosted wikis — **DokuWiki** (flat-file simplicity), **TiddlyWiki5** (single-file non-linear notebooks), and **XWiki** (enterprise-grade wiki platform) — and provides production-ready deployment configurations for each.

## Project Overview and Live Stats

| Project | GitHub Stars | Last Updated | Architecture | Database |
|---------|-------------|--------------|--------------|----------|
| [DokuWiki](https://github.com/dokuwiki/dokuwiki) | 4,599 | April 15, 2026 | PHP, flat files | No database required |
| [TiddlyWiki5](https://github.com/Jermolene/TiddlyWiki5) | 8,584 | April 16, 2026 | JavaScript, single HTML file | File system (Node.js) or browser localStorage |
| [XWiki](https://github.com/xwiki/xwiki-platform) | 1,237 | April 17, 2026 | Java (Servlet), web application | MySQL, PostgreSQL, or HSQLDB |

All three projects are actively maintained with recent commits, open-source licenses, and large communities. They represent three distinct philosophies for organizing knowledge.

## DokuWiki: Flat-File Simplicity

DokuWiki is a PHP-based wiki engine that stores all content as plain text files — no database required. This makes it one of the simplest wiki engines to install, back up, and migrate. First released in 2004, it has become a staple for personal wikis, homelab documentation, and small team knowledge bases.

### Key Features

- **No database needed** — every page is a `.txt` file, making backups as simple as copying a directory
- **ACL (Access Control Lists)** — granular per-page and per-namespace read/write permissions
- **Plugin ecosystem** — over 1,200 plugins for syntax extensions, authentication backends, and integrations
- **Revision control** — built-in page history with diff view and rollback
- **SEO-friendly URLs** — clean URL structure for search engine indexing
- **Media manager** — upload and organize images, PDFs, and other files within the wiki

### [docker](https://www.docker.com/) Compose Deployment

The simplest way to deploy DokuWiki is with a lightweight PHP container. This configuration uses the `linuxserver/dokuwiki` image which bundles PHP, nginx, and DokuWiki in a single container:

```yaml
version: "3.8"

services:
  dokuwiki:
    image: linuxserver/dokuwiki:latest
    container_name: dokuwiki
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    volumes:
      - ./config:/config
    ports:
      - "8080:80"
    restart: unless-stopped
```

For production use behind a reverse proxy, omit the `ports` mapping and use a custom network:

```yaml
version: "3.8"

services:
  dokuwiki:
    image: linuxserver/dokuwiki:latest
    container_name: dokuwiki
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    volumes:
      - ./config:/config
    networks:
      - proxy-net
    restart: unless-stopped

networks:
  proxy-net:
    external: true
```

After starting the container, navigate to `http://your-server:8080/install.php` to run the initial setup wizard. Create your admin account, set the wiki name, and choose ACL settings. Delete `install.php` after setup to prevent unauthorized reinstallation.

### Best Use Cases

DokuWiki excels when you need a straightforward, low-maintenance wiki. It is ideal for homelab documentation, team runbooks, project wikis, and personal knowledge bases where the overhead of a database is unnecessary. The flat-file architecture means your entire wiki — pages, media, and configuration — can be backed up with a single `tar` command or synchronized with `rsync`.

## TiddlyWiki5: Non-Linear Notebooks in a Single File

TiddlyWiki5 takes a radically different approach. The entire wiki — including the rendering engine, all content, and plugins — lives inside a single HTML file. This makes it uniquely portable: you can email it, store it in a git repository, or open it directly in any web browser without a server. When run with Node.js, it becomes a fully self-hosted wiki with a web interface.

### Key Features

- **Single-file portability** — the entire wiki is one `.html` file that works offline in any browser
- **Non-linear organization** — tiddlers (individual content units) are tagged, filtered, and displayed dynamically rather than organized in rigid hierarchies
- **Transclusion** — embed any tiddler inside any other, enabling highly interconnected documentation
- **Powerful filtering** — built-in filter syntax for querying, sorting, and grouping tiddlers by tags, dates, or custom fields
- **Plugin system** — extend functionality with JavaScript-based plugins
- **Node.js server mode** — run as a multi-user wiki with REST API and persistent storage

### Docker Compose Deployment

TiddlyWiki5's Node.js server mode can be containerized for persistent multi-user access:

```yaml
version: "3.8"

services:
  tiddlywiki:
    image: node:20-alpine
    container_name: tiddlywiki
    working_dir: /wiki
    volumes:
      - ./wiki-data:/wiki
    command: >
      sh -c "
        npm install -g tiddlywiki &&
        tiddlywiki --init server &&
        tiddlywiki ./ --listen port=8080 host=0.0.0.0
      "
    ports:
      - "8081:8080"
    restart: unless-stopped
```

For a more production-oriented setup, use a Dockerfile that pre-installs TiddlyWiki5 and mounts the data directory:

```dockerfile
FROM node:20-alpine
RUN npm install -g tiddlywiki
VOLUME /wiki
WORKDIR /wiki
EXPOSE 8080
CMD ["tiddlywiki", "./", "--listen", "port=8080", "host=0.0.0.0"]
```

```yaml
version: "3.8"

services:
  tiddlywiki:
    build: .
    container_name: tiddlywiki
    volumes:
      - ./wiki-data:/wiki
    ports:
      - "8081:8080"
    restart: unless-stopped
```

After the container starts, access the wiki at `http://your-server:8081`. The first visit loads the server edition with authentication options. Create your admin user and begin adding tiddlers. All content is saved automatically to the mounted volume.

### Best Use Cases

TiddlyWiki5 is uniquely suited for personal knowledge management, research notebooks, and documentation that benefits from non-linear organization. Its single-file nature makes it perfect for version-controlled documentation (commit the HTML file to git) and offline-first workflows. For teams, the Node.js server mode provides a web-accessible wiki with user authentication.

## XWiki: Enterprise-Grade Wiki Platform

XWiki is a Java-based wiki platform designed for organizations that need enterprise features: structured data, advanced permissions, Office document editing, and multi-wiki support. It is the most feature-complete wiki engine in this comparison, but also the most resource-intensive.

### Key Features

- **Structured data** — define custom data types and query them with XWiki Query Language (XWQL)
- **Advanced permissions** — per-page, per-space, and per-group access control with inheritance
- **Office integration** — edit Office documents directly in the browser with Collabora Online or OnlyOffice
- **WYSIWYG editor** — full rich-text editing alongside wiki markup
- **Multi-wiki support** — host multiple independent wikis on a single installation
- **Extension repository** — hundreds of extensions for calendars, task management, blogs, and more
- **Import/export** — full Confluence, MediaWiki, and XAR package import support

### Docker Compose Deployment

XWiki requires a Java servlet container (Tomcat) and a database. This configuration pairs XWiki with PostgreSQL for production reliability:

```yaml
version: "3.8"

services:
  xwiki-db:
    image: postgres:16-alpine
    container_name: xwiki-db
    environment:
      POSTGRES_PASSWORD: xwiki_db_password
      POSTGRES_DB: xwiki
      POSTGRES_USER: xwiki
    volumes:
      - ./db-data:/var/lib/postgresql/data
    networks:
      - xwiki-net
    restart: unless-stopped

  xwiki:
    image: xwiki:16-postgres-tomcat
    container_name: xwiki
    depends_on:
      - xwiki-db
    environment:
      DB_USER: xwiki
      DB_PASSWORD: xwiki_db_password
      DB_DATABASE: xwiki
      DB_HOST: xwiki-db
    volumes:
      - ./xwiki-data:/usr/local/xwiki
    ports:
      - "8082:8080"
    networks:
      - xwiki-net
    restart: unless-stopped

networks:
  xwiki-net:
    driver: bridge
```

The initial startup takes 2-3 minutes as Tomcat initializes and the database schema is created. Once running, access the setup wizard at `http://your-server:8082`. Choose your wiki flavor, create the admin account, and configure the distribution.

For resource-constrained environments, you can use the default HSQLDB database (no separate database container needed), but PostgreSQL or MySQL is strongly recommended for production use:

```yaml
version: "3.8"

services:
  xwiki:
    image: xwiki:16-standard
    container_name: xwiki
    volumes:
      - ./xwiki-data:/usr/local/xwiki
    ports:
      - "8082:8080"
    restart: unless-stopped
```

### Best Use Cases

XWiki is the right choice when you need enterprise wiki capabilities: structured content types, fine-grained permissions, multi-tenant wiki hosting, or integration with Office suites. It is commonly deployed by universities, corporations, and government organizations as a central knowledge management platform.

## Detailed Feature Comparison

| Feature | DokuWiki | TiddlyWiki5 | XWiki |
|---------|----------|-------------|-------|
| **Language** | PHP | JavaScript | Java |
| **Database Required** | No (flat files) | No (file system) | Yes (PostgreSQL/MySQL/HSQLDB) |
| **RAM Footprint** | ~64 MB | ~128 MB | ~512 MB+ |
| **WYSIWYG Editor** | Via plugin | No | Built-in |
| **ACL / Permissions** | Yes (namespace-level) | Basic (Node.js server) | Advanced (per-page, inheritance) |
| **Multi-user Editing** | Yes | Yes (Node.js server) | Yes (with lock management) |
| **Plugin Ecosystem** | 1,200+ plugins | 400+ plugins | 800+ extensions |
| **REST API** | Via plugin | Built-in | Built-in |
| **Structured Data** | Limited | Via fields | Full (custom data types) |
| **Revision History** | Yes | Yes | Yes |
| **Media Management** | Built-in | Via plugins | Built-in |
| **Import/Export** | Text, HTML, PDF | HTML, JSON, Markdown | Confluence, MediaWiki, XAR, PDF |
| **Search** | Full-text, plugin-enhanced | Tag-based, filter queries | Lucene-powered full-text |
| **Docker Support** | Excellent | Good | Excellent |
| **Setup Com[plex](https://www.plex.tv/)ity** | Very low | Low | Moderate to high |
| **Best For** | Personal wikis, homelab docs | Personal notebooks, research | Enterprise knowledge bases |

## Choosing the Right Wiki Engine

The decision between these three wikis comes down to your scale and requirements:

**Choose DokuWiki if:**
- You want the simplest possible setup with zero database dependencies
- Your wiki serves a small team or personal use
- You value easy backups (just copy a directory)
- You need a large plugin ecosystem for customization

**Choose TiddlyWiki5 if:**
- You want a non-linear, tag-based approach to organizing knowledge
- You need offline-first access or single-file portability
- You are managing research notes, personal journals, or interconnected documentation
- You want version-controlled documentation via git

**Choose XWiki if:**
- You need enterprise features like structured data and advanced permissions
- Your wiki serves a large organization with multiple departments
- You require Office document editing and Confluence migration
- You need multi-wiki hosting[wiki.js](https://js.wiki/)ingle server

For related reading, see our [Wiki.js vs BookStack vs Outline comparison](../wiki-js-vs-bookstack-vs-outline/) for additional wiki engine options, our [self-hosted note-taking and knowledge management guide](../self-hosted-note-taking-knowledge-management/) for broader knowledge management solutions, and our [Docker Compose guide](../docker-compose-guide/) for container deployment fundamentals.

## FAQ

### Which wiki engine is the easiest to set up?
DokuWiki is the easiest to set up. It requires no database — just a PHP-capable web server or Docker container. The entire installation takes under 5 minutes, and the flat-file architecture means backups are as simple as copying a directory. TiddlyWiki5 is also very simple: you can literally open a single HTML file in your browser and start writing immediately.

### Can I migrate content between these wiki engines?
Migration is possible but requires effort. DokuWiki can import from MediaWiki and export to HTML or PDF. XWiki has the most robust import/export system, supporting Confluence, MediaWiki, and its own XAR package format. TiddlyWiki5 exports to JSON, HTML, and Markdown. For cross-engine migration, export to Markdown first and then import using each platform's import tools.

### Do these wikis support real-time collaborative editing?
XWiki has built-in multi-user editing with page lock management to prevent edit conflicts. DokuWiki supports concurrent edits but uses a simple file locking mechanism — two users editing the same page simultaneously may see a conflict warning. TiddlyWiki5 in Node.js server mode supports multiple users but does not have real-time collaborative editing; the last save wins if two users edit the same tiddler at the same time.

### How do these wikis handle backups?
DokuWiki backups are the simplest — copy the entire data directory (usually `data/` and `conf/`) to any location. Restore by copying back. TiddlyWiki5 backups are a single HTML file (browser mode) or a directory of tiddler files (Node.js mode). XWiki requires backing up both the data directory and the PostgreSQL/MySQL database. Use `pg_dump` for PostgreSQL or `mysqldump` for MySQL to capture database state alongside the file system data.

### Can I use these wikis for a public-facing knowledge base?
All three wikis can serve public-facing content. DokuWiki and XWiki are commonly used as public documentation portals and company wikis with public read access. TiddlyWiki5 in single-file mode is less suitable for public serving due to its JavaScript-heavy rendering, but the Node.js server mode works well for this purpose. For SEO optimization, DokuWiki and XWiki generate server-side HTML that search engines can crawl effectively.

### What are the resource requirements for each wiki?
DokuWiki runs comfortably on 64-128 MB of RAM and minimal CPU. TiddlyWiki5 in Node.js mode requires about 128-256 MB of RAM. XWiki is the most demanding, requiring at least 512 MB of RAM (1 GB recommended) plus the memory needed for its database (PostgreSQL adds another 128-256 MB). For a small homelab server, DokuWiki or TiddlyWiki5 are the most practical choices.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "DokuWiki vs TiddlyWiki vs XWiki: Best Self-Hosted Wiki Engines 2026",
  "description": "Compare DokuWiki, TiddlyWiki5, and XWiki — the top self-hosted wiki engines. Complete Docker setup guides, feature comparisons, and deployment recommendations for personal and team knowledge bases in 2026.",
  "datePublished": "2026-04-17",
  "dateModified": "2026-04-17",
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
