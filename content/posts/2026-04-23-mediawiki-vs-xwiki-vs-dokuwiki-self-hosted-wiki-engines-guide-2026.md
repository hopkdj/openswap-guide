---
title: "MediaWiki vs XWiki vs DokuWiki: Best Self-Hosted Wiki Engines 2026"
date: 2026-04-23
tags: ["comparison", "guide", "self-hosted", "wiki", "documentation", "open-source"]
draft: false
description: "Compare the top 3 open-source self-hosted wiki engines — MediaWiki, XWiki, and DokuWiki. Covers features, Docker deployment, performance, and real-world use cases for teams and enterprises in 2026."
---

## Why Self-Host a Wiki Engine in 2026

Wikis remain one of the most effective tools for organizational knowledge management. Unlike modern documentation generators that focus on developer-centric markdown workflows, wiki engines provide collaborative editing with built-in version control, user management, and structured content organization — all within a web browser.

Self-hosting a wiki gives you full control over your data, eliminates subscription costs, and ensures your knowledge base remains accessible even if third-party services shut down or change pricing. Whether you are running an internal company wiki, a community knowledge base, or a public-facing documentation portal, choosing the right wiki engine matters.

Three open-source wiki platforms dominate the self-hosted landscape: **MediaWiki**, the engine behind Wikipedia; **XWiki**, an enterprise-grade wiki with structured data support; and **DokuWiki**, the lightweight flat-file wiki that has been reliably running for over two decades.

This guide compares all three on features, deployment complexity, scalability, and extensibility so you can pick the right tool for your use case.

## Project Overview and Live Stats

| Feature | MediaWiki | XWiki | DokuWiki |
|---|---|---|---|
| **Language** | PHP | Java | PHP |
| **GitHub Stars** | 5,035 | 1,238 | 4,600 |
| **Last Updated** | April 2026 | April 2026 | April 2026 |
| **License** | GPL-2.0 | LGPL-2.1 | GPL-2.0 |
| **Database** | MySQL, PostgreSQL, SQLite | MySQL, PostgreSQL, H2 | Flat files (no DB needed) |
| **Min. PHP Version** | 8.1+ | N/A (runs on JVM) | 7.4+ (PHP 8 recommended) |
| **WYSIWYG Editor** | VisualEditor (extension) | Built-in CKEditor | Built-in (optional plugins) |
| **REST API** | Yes (Action API) | Yes (comprehensive) | No (plugins available) |
| **Structured Data** | Semantic MediaWiki (extension) | Built-in (XWiki Data Model) | Plugins available |
| **Docker Support** | Official dev image, community images | Official Docker image | LinuxServer.io community image |
| **Typical RAM Usage** | 256 MB – 512 MB | 512 MB – 2 GB | 64 MB – 128 MB |
| **Best For** | Large public wikis, encyclopedias | Enterprise wikis, structured data | Small teams, simple setups |

MediaWiki (5,035 stars on GitHub) is a mirror from the Wikimedia Gerrit repository and is updated continuously. XWiki (1,238 stars) follows an enterprise release cadence with LTS versions. DokuWiki (4,600 stars) sees steady maintenance and plugin contributions from its community.

## MediaWiki: The Wikipedia Engine

MediaWiki powers Wikipedia, Wiktionary, Wikimedia Commons, and thousands of enterprise and community wikis worldwide. It was originally developed for Wikipedia in 2002 and has since evolved into a mature, battle-tested platform.

### Key Strengths

- **Unmatched scalability** — Wikipedia handles millions of page views daily with a MediaWiki cluster. The software supports database replication, caching layers (Varnish, CDN), and job queue distribution out of the box.
- **Massive extension ecosystem** — Over 3,000 extensions covering everything from spam prevention (ConfirmEdit, AbuseFilter) to semantic data (Semantic MediaWiki) to OAuth authentication.
- **Granular permissions** — Fine-grained user group management with custom rights assignment. You can restrict editing to specific namespaces, pages, or user groups.
- **Wikitext markup** — A powerful templating language with transclusion (including pages within pages), parser functions, and template parameters. The learning curve is steeper than Markdown but offers unmatched flexibility.
- **VisualEditor** — A WYSIWYG editor that reduces the barrier to entry for non-technical contributors.

### Limitations

- **Resource-intensive** — Requires a LAMP/LEMP stack (Linux, Apache/Nginx, MySQL/PostgreSQL, PHP). Even a small installation needs at least 256 MB of RAM and a database server.
- **Complex setup** — The installation process involves multiple configuration steps, database setup, and LocalSettings.php tuning.
- **Wikitext is non-standard** — Unlike Markdown or reStructuredText, MediaWiki's wikitext is unique to the platform. Migrating content out requires wikitext parsing.

### Docker Deployment

The Bitnami MediaWiki image provides a production-ready Docker Compose setup:

```yaml
services:
  mediawiki:
    image: docker.io/bitnami/mediawiki:1.43
    ports:
      - '8080:8080'
    environment:
      - MEDIAWIKI_DATABASE_HOST=mariadb
      - MEDIAWIKI_DATABASE_PORT_NUMBER=3306
      - MEDIAWIKI_DATABASE_USER=bn_mediawiki
      - MEDIAWIKI_DATABASE_PASSWORD=changeme123
      - MEDIAWIKI_DATABASE_NAME=bitnami_mediawiki
      - MEDIAWIKI_USERNAME=admin
      - MEDIAWIKI_PASSWORD=mediawiki_password
      - MEDIAWIKI_EMAIL=admin@example.com
    volumes:
      - 'mediawiki_data:/bitnami/mediawiki'
    depends_on:
      - mariadb

  mariadb:
    image: docker.io/bitnami/mariadb:11.4
    environment:
      - MARIADB_USER=bn_mediawiki
      - MARIADB_DATABASE=bitnami_mediawiki
      - ALLOW_EMPTY_PASSWORD=yes
    volumes:
      - 'mariadb_data:/bitnami/mariadb'

volumes:
  mediawiki_data:
    driver: local
  mariadb_data:
    driver: local
```

Save this as `docker-compose.yml` and run:

```bash
docker compose up -d
```

Access MediaWiki at `http://localhost:8080`. The default credentials are `admin` / `mediawiki_password`.

For a reverse proxy with HTTPS, place Nginx or Caddy in front and update `MEDIAWIKI_HOST` accordingly.

## XWiki: Enterprise Wiki with Structured Data

XWiki is a Java-based wiki platform designed for enterprise knowledge management. Unlike traditional wikis that treat pages as flat text, XWiki treats each page as a structured document with properties, objects, and classes — essentially a content management system with wiki semantics.

### Key Strengths

- **Structured wiki model** — Every page can have custom properties, typed fields, and relationships. You can create custom applications (bug trackers, project dashboards, asset registries) directly within the wiki without external tools.
- **Built-in WYSIWYG editor** — CKEditor integration provides a polished editing experience with toolbar formatting, image insertion, and table editing.
- **Office document support** — Import and view Word, Excel, and PowerPoint documents directly in the wiki. Changes to imported documents sync back.
- **Application within a wiki** — The XWiki Application Within Minutes (AWM) feature lets you build custom data-driven applications using wiki pages as your database backend.
- **Flavor system** — Pre-packaged configurations (Enterprise, Standard, Education) that install relevant extensions and set up recommended defaults.
- **Active development** — Regular LTS releases with security patches and feature updates. Strong corporate backing from XWiki SAS.

### Limitations

- **Java resource requirements** — XWiki runs on a servlet container (Tomcat or Jetty) and requires a JVM. A minimal installation needs at least 512 MB of RAM, realistically 1–2 GB for comfortable operation.
- **Steeper learning curve for advanced features** — The structured data model and scripting (Velocity, Groovy) require more expertise than simple wiki editing.
- **Fewer community themes** — Compared to MediaWiki's vast skin collection, XWiki has fewer visual customization options.

### Docker Deployment

XWiki provides an official Docker image with support for multiple database backends. Here is a production-ready setup with MariaDB:

```yaml
services:
  xwiki:
    image: docker.io/xwiki:stable-mysql-tomcat
    container_name: xwiki
    depends_on:
      - db
    ports:
      - "8080:8080"
    environment:
      - DB_USER=xwiki
      - DB_PASSWORD=xwiki_password
      - DB_DATABASE=xwiki
      - DB_HOST=db
    volumes:
      - xwiki_data:/usr/local/xwiki
      - xwiki_extensions:/usr/local/xwiki/extensions
      - xwiki_logs:/usr/local/xwiki/logs

  db:
    image: docker.io/mariadb:11.4
    container_name: xwiki-db
    environment:
      - MYSQL_ROOT_PASSWORD=root_password
      - MYSQL_USER=xwiki
      - MYSQL_PASSWORD=xwiki_password
      - MYSQL_DATABASE=xwiki
    command:
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_bin
      - --innodb-buffer-pool-size=256M
      - --max-connections=50
    volumes:
      - db_data:/var/lib/mysql

volumes:
  xwiki_data:
    driver: local
  xwiki_extensions:
    driver: local
  xwiki_logs:
    driver: local
  db_data:
    driver: local
```

Run with:

```bash
docker compose up -d
```

XWiki will be available at `http://localhost:8080`. The first-run wizard guides you through database configuration and admin account creation.

## DokuWiki: Lightweight Flat-File Wiki

DokuWiki has been a staple of the self-hosted wiki community since 2004. Its defining characteristic is that it stores all content in plain text files — no database server required. This makes it incredibly easy to deploy, back up, and migrate.

### Key Strengths

- **Zero database dependency** — All pages are stored as `.txt` files in a `data/pages/` directory. Backup is as simple as copying a folder. Version history is maintained through a built-in revision system.
- **Minimal resource footprint** — DokuWiki runs comfortably on 64 MB of RAM. It is an excellent choice for low-powered servers, Raspberry Pi deployments, or hosting environments with tight resource limits.
- **Simple markup language** — DokuWiki's syntax is easy to learn and similar to Markdown in many ways. Headings use `====== Heading ======`, links use `[[page]]`, and formatting uses `**bold**` and `//italic//`.
- **Plugin ecosystem** — Over 1,200 plugins covering authentication (LDAP, OAuth, SAML), editors, spam protection, export formats, and integrations.
- **Access control lists** — Built-in ACL system with per-namespace and per-page permission control.
- **Built-in search** — Full-text search without requiring Elasticsearch or Solr. The search index is automatically maintained.

### Limitations

- **Flat-file scalability** — While DokuWiki handles thousands of pages well, it can become slow with 10,000+ pages. The file-system-based approach does not scale to Wikipedia-level workloads.
- **No native WYSIWYG editor** — The default editor is a toolbar-enhanced text area. WYSIWYG plugins exist (e.g., CKEditor plugin) but are community-maintained.
- **Limited structured data** — Unlike XWiki, DokuWiki does not have a built-in data model. The Data plugin adds some structured capabilities but is not as comprehensive.
- **No REST API** — DokuWiki lacks a built-in REST API. Third-party plugins provide some API functionality, but it is not as polished as MediaWiki's Action API or XWiki's REST API.

### Docker Deployment

DokuWiki does not provide an official Docker image, but the LinuxServer.io community image is well-maintained and production-ready:

```yaml
services:
  dokuwiki:
    image: lscr.io/linuxserver/dokuwiki:latest
    container_name: dokuwiki
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Etc/UTC
    ports:
      - 8080:80
    volumes:
      - ./config:/config
      - ./data:/data
    restart: unless-stopped
```

Run with:

```bash
docker compose up -d
```

Access DokuWiki at `http://localhost:8080`. The initial setup wizard runs on first access, where you configure the wiki name, admin credentials, and ACL policy.

For production use, mount the `./data` volume to a persistent storage location so your wiki content survives container rebuilds.

## Feature Comparison in Detail

### Editing and Content Creation

MediaWiki uses wikitext markup by default, which supports powerful features like templates, transclusion, and parser functions. The optional VisualEditor provides a WYSIWYG experience but requires additional setup (Parsoid service). For teams comfortable with wikitext, MediaWiki offers the most powerful content modeling capabilities.

XWiki's default editor is a rich WYSIWYG editor (CKEditor) that feels familiar to anyone who has used Google Docs or Microsoft Word. For advanced users, XWiki also supports a wiki syntax mode, and you can write pages in Markdown, Creole, or JSPWiki syntax. The editor integration is the most polished of the three options.

DokuWiki uses its own simple markup syntax that sits between Markdown and wikitext in complexity. The toolbar provides quick-insert buttons for common formatting. For teams that want simplicity without sacrificing structure, DokuWiki strikes the right balance.

### Authentication and Access Control

All three platforms support user authentication with built-in user management. MediaWiki supports LDAP, OAuth, OpenID, and SAML through extensions. XWiki includes LDAP and Active Directory integration out of the box, with SAML and OAuth available via the extension manager. DokuWiki supports LDAP, OAuth, and SAML through community plugins.

For access control, MediaWiki offers the most granular permission system with custom user groups and per-namespace restrictions. XWiki provides space-level and page-level permissions with group-based access control. DokuWiki uses ACL rules defined in `acl.auth.php` for fine-grained access control.

### Search Capabilities

MediaWiki's search has improved significantly with the introduction of CirrusSearch (Elasticsearch-based), which provides full-text search with highlighting, fuzzy matching, and suggestions. Without CirrusSearch, the default SQL-based search is functional but limited.

XWiki includes a built-in full-text search engine with support for Lucene-based indexing. Search results can be filtered by space, date, author, and content type. The search syntax supports boolean operators and wildcards.

DokuWiki's built-in search indexes all page content and metadata. It supports phrase search, namespace filtering, and tag-based filtering. For most wiki sizes (under 10,000 pages), the default search is fast and accurate. For larger installations, the Solr Search plugin adds Elasticsearch-powered search.

### Backup and Migration

DokuWiki is the easiest to back up — simply archive the `data/` directory. Since everything is stored in plain text files, you can even version-control your wiki content with Git. Migration to another server is a straightforward file copy.

MediaWiki requires database dumps (`mysqldump` or `pg_dump`) along with the `images/` directory and `LocalSettings.php`. The process is well-documented but involves multiple steps.

XWiki backup involves exporting the database (MySQL, PostgreSQL, or H2) and archiving the `xwiki` data directory (extensions, logs, permanent directory). The XWiki Import/Export application also allows page-level exports in XAR format.

## Which Wiki Engine Should You Choose?

**Choose MediaWiki if:**
- You need to handle large-scale content (thousands of pages, millions of edits)
- You want the same platform that powers Wikipedia
- Your team needs advanced templating and transclusion features
- You have server resources for a LAMP/LEMP stack and database server

**Choose XWiki if:**
- You need structured data and want to build applications within your wiki
- Your organization values WYSIWYG editing and office document integration
- You want enterprise-grade features with LTS release support
- Your team is comfortable with Java-based applications

**Choose DokuWiki if:**
- You want the simplest possible setup with no database dependency
- You are running on limited server resources (Raspberry Pi, low-cost VPS)
- Your wiki has under 10,000 pages and a small to medium user base
- You value easy backup and Git-based version control for wiki content

For related reading, see our comparison of [Wiki.js vs BookStack vs Outline](../wiki-js-vs-bookstack-vs-outline/) for a different take on wiki platforms, the [DokuWiki vs TiddlyWiki vs XWiki wiki engines guide](../dokuwiki-vs-tiddlywiki-vs-xwiki-self-hosted-wiki-engines-2026/) for an earlier comparison, and our [note-taking and knowledge management overview](../self-hosted-note-taking-knowledge-management/) for related knowledge management tools.

## FAQ

### Can I migrate content between MediaWiki, XWiki, and DokuWiki?

Yes, migration is possible but varies in difficulty. DokuWiki offers import/export plugins for MediaWiki format. XWiki provides a MediaWiki importer that can pull content directly from a MediaWiki installation. For DokuWiki to XWiki migration, you can export DokuWiki pages as plain text and use XWiki's import tools. However, wiki-specific markup (templates, transclusion, structured data) does not translate perfectly — expect to do manual cleanup after migration.

### Do these wiki engines support Markdown?

MediaWiki does not support Markdown natively — it uses wikitext. However, the Extension:Markdown allows you to write pages in Markdown format. XWiki supports Markdown as one of several input syntaxes (alongside wiki syntax, Creole, and JSPWiki). DokuWiki uses its own markup language but the Markdown plugin adds limited Markdown support. If Markdown is a hard requirement, consider wiki platforms like Wiki.js or BookStack that use Markdown as their primary format.

### Which wiki engine is the easiest to set up?

DokuWiki is the easiest to set up by a significant margin. Since it requires no database, you can install it by uploading files to a web server or running a single Docker container. The entire installation takes under 5 minutes. MediaWiki requires a database server and PHP configuration, typically taking 15–30 minutes. XWiki is the most complex, requiring Java, a servlet container (Tomcat), and a database — plan for 30–60 minutes for initial setup.

### Can these wikis handle concurrent editing?

All three platforms handle concurrent editing, but with different mechanisms. MediaWiki uses an edit lock system that prevents two users from editing the same page simultaneously (edit collisions show a merge screen). XWiki uses document-level locking with real-time conflict detection. DokuWiki uses simple file locking — if two users edit the same page, the second save overwrites the first unless the edit conflict plugin is installed. For teams with many simultaneous editors, MediaWiki's conflict resolution is the most robust.

### How do I add HTTPS to a self-hosted wiki?

The recommended approach is to place a reverse proxy in front of the wiki container. Caddy is the simplest option — it automatically obtains and renews Let's Encrypt certificates. With Docker, you can run Caddy alongside your wiki and configure it to proxy requests. Alternatively, Nginx with Certbot provides more configuration flexibility. All three wiki engines work behind any standard reverse proxy without special configuration.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "MediaWiki vs XWiki vs DokuWiki: Best Self-Hosted Wiki Engines 2026",
  "description": "Compare the top 3 open-source self-hosted wiki engines — MediaWiki, XWiki, and DokuWiki. Covers features, Docker deployment, performance, and real-world use cases for teams and enterprises in 2026.",
  "datePublished": "2026-04-23",
  "dateModified": "2026-04-23",
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
