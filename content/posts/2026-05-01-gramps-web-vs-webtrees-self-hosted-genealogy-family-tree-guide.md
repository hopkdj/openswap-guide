---
title: "Gramps Web vs Webtrees: Self-Hosted Genealogy & Family Tree Guide (2026)"
date: 2026-05-01T08:00:00Z
tags: ["genealogy", "family-tree", "self-hosted", "gramps", "webtrees", "web-app"]
draft: false
---

Your family history deserves better than a subscription-based online service that can disappear overnight. Self-hosted genealogy platforms give you full ownership of your family tree data, privacy controls, and the ability to collaborate with relatives without handing your data to a third party.

In this guide, we compare two of the most capable open-source self-hosted family tree platforms: **Gramps Web** and **Webtrees**. Both let you host your genealogical database on your own server, but they take very different approaches to the problem.

## What Are Self-Hosted Genealogy Platforms?

Self-hosted genealogy platforms are web applications that run on your own hardware — a home server, VPS, or NAS — and provide tools for building, storing, and sharing family trees. Unlike commercial services like Ancestry.com or MyHeritage, you retain complete control over your data, access it without recurring fees, and can share it selectively with family members.

### Why Self-Host Your Family Tree?

- **Data ownership**: Your genealogical research is yours permanently
- **Privacy**: Control exactly who sees what — living person data stays private
- **No subscription fees**: One-time server cost vs. ongoing monthly payments
- **Collaboration**: Invite family members with granular permission levels
- **GEDCOM compatibility**: Import/export standard genealogical data formats
- **Long-term preservation**: No risk of a service shutting down and taking your data

## Gramps Web vs Webtrees: Feature Comparison

| Feature | Gramps Web | Webtrees |
|---|---|---|
| **GitHub Stars** | 1,396 (frontend) + 203 (API) | 749 |
| **Language** | JavaScript (frontend) + Python (API) | PHP |
| **License** | AGPL-3.0 | GPL-3.0 |
| **Database** | SQLite (via Gramps XML database) | MySQL/MariaDB or PostgreSQL |
| **Mobile Responsive** | Yes (PWA) | Yes |
| **Collaborative Editing** | Yes, multi-user with roles | Yes, multi-user with roles |
| **GEDCOM Import** | Yes | Yes |
| **GEDCOM Export** | Yes | Yes |
| **Privacy Controls** | Per-user role-based | Per-person, per-record rules |
| **Interactive Charts** | Fan, ancestor, descendant, hourglass | Pedigree, descendant, timeline |
| **Mapping** | Yes, with historical map overlays | Yes, geo-location support |
| **Multi-language** | 40+ languages | 60+ languages |
| **DNA Tools** | Chromosome browser, DNA matching | No built-in DNA tools |
| **Desktop Integration** | Bi-directional sync with Gramps Desktop | Standalone (no desktop sync) |
| **Docker Support** | Yes (official) | Yes (community images) |
| **REST API** | Yes (full API) | Limited API |
| **Media Management** | Built-in gallery, document storage | Built-in media manager |
| **Last Updated** | April 2026 | April 2026 |

## Gramps Web: Modern Genealogy with Desktop Sync

[Gramps Web](https://www.grampsweb.org/) is the web counterpart to [Gramps Desktop](https://gramps-project.org/), the leading open-source genealogy application. It's designed as a companion to the desktop app, with bi-directional synchronization between the two.

### Key Features

- **Bi-directional sync**: Changes made on the web or desktop stay in sync via the Gramps Web API
- **Natural language search**: Query your family tree using conversational questions
- **Interactive family tree charts**: Fan charts, ancestor/descendant trees, hourglass diagrams
- **DNA analysis**: View DNA matches and chromosome data
- **Historical maps**: Overlay family locations on period-appropriate maps
- **Integrated blog**: Document research stories with images stored in the Gramps database
- **Advanced search**: Full-text search across all record types with wildcards

### Architecture

Gramps Web consists of two components:

1. **Gramps Web API** (`gramps-web-api`) — Python backend using Flask, provides a RESTful API for all genealogical operations
2. **Gramps Web Frontend** — JavaScript SPA (single-page application) that communicates with the API

The system uses Gramps' native XML database format (`.gramps`) stored on disk, with SQLite as a caching layer for search indexing.

### Docker Compose Setup

```yaml
version: "3.8"

services:
  gramps-web:
    image: ghcr.io/gramps-project/grampsweb:latest
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - gramps_data:/app/data
      - gramps_db:/root/.gramps
      - gramps_media:/app/media
      - gramps_thumbnail:/app/thumbnail
      - gramps_cache:/app/cache
      - gramps_secret:/app/secret
    environment:
      - GRAMPSWEB_SECRET_FILE=/app/secret/secret
      - GRAMPSWEB_CELERY_CONFIG__broker_url=redis://redis:6379/0
      - GRAMPSWEB_CELERY_CONFIG__result_backend=redis://redis:6379/1

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data

  worker:
    image: ghcr.io/gramps-project/grampsweb:latest
    restart: unless-stopped
    command: celery -A gramps_webapi.celery worker --loglevel=info
    volumes:
      - gramps_data:/app/data
      - gramps_db:/root/.gramps
      - gramps_media:/app/media
      - gramps_thumbnail:/app/thumbnail
      - gramps_cache:/app/cache
      - gramps_secret:/app/secret
    environment:
      - GRAMPSWEB_SECRET_FILE=/app/secret/secret
      - GRAMPSWEB_CELERY_CONFIG__broker_url=redis://redis:6379/0
      - GRAMPSWEB_CELERY_CONFIG__result_backend=redis://redis:6379/1

volumes:
  gramps_data:
  gramps_db:
  gramps_media:
  gramps_thumbnail:
  gramps_cache:
  gramps_secret:
  redis_data:
```

## Webtrees: Battle-Tested PHP Genealogy Platform

[Webtrees](https://www.webtrees.net/) is a mature PHP-based genealogy platform that has been actively developed since 2010. It forked from phpGedView and has since become one of the most widely used self-hosted family tree solutions, powering thousands of installations worldwide.

### Key Features

- **GEDCOM-native**: Built around the GEDCOM standard for maximum compatibility
- **Fine-grained privacy**: Control visibility per individual, per family member, and per record type
- **Multi-tree support**: Host multiple separate family trees on one installation
- **Collaborative editing**: User roles from visitor to administrator with per-tree permissions
- **Research tasks**: Track research to-do items linked to specific individuals
- **Media management**: Attach photos, documents, and audio files to individuals and families
- **Extensive theme system**: Multiple built-in themes and support for custom themes
- **Addon modules**: Extensible via a rich ecosystem of third-party modules

### Architecture

Webtrees is a traditional PHP/MySQL application. It runs on any standard LAMP/LEMP stack and uses MySQL or MariaDB as its database. The application is stateless — all data lives in the database, making backups straightforward.

### Docker Compose Setup

```yaml
version: "3.8"

services:
  webtrees:
    image: nathanvaughn/webtrees:latest
    restart: unless-stopped
    ports:
      - "8080:80"
    volumes:
      - webtrees_data:/var/www/html/data
      - webtrees_media:/var/www/html/media
    environment:
      - WT_DB_HOST=db
      - WT_DB_NAME=webtrees
      - WT_DB_USER=webtrees
      - WT_DB_PASSWORD=webtrees_password
      - WT_TABLE_PREFIX=wt_
    depends_on:
      - db

  db:
    image: mariadb:11
    restart: unless-stopped
    volumes:
      - db_data:/var/lib/mysql
    environment:
      - MARIADB_ROOT_PASSWORD=root_password
      - MARIADB_DATABASE=webtrees
      - MARIADB_USER=webtrees
      - MARIADB_PASSWORD=webtrees_password

volumes:
  webtrees_data:
  webtrees_media:
  db_data:
```

After starting the containers, visit `http://your-server:8080` to complete the web-based setup wizard.

## Which Should You Choose?

### Pick Gramps Web if:

- You already use **Gramps Desktop** and want web access with sync
- You need **DNA analysis tools** and chromosome visualization
- You want a **modern REST API** for custom integrations
- You prefer a **progressive web app** (PWA) with mobile-first design
- You value **historical map overlays** for geographic research

### Pick Webtrees if:

- You need a **standalone web-only solution** (no desktop dependency)
- You want **fine-grained per-person privacy rules**
- You prefer a **battle-tested platform** with 15+ years of development
- You need **multi-tree support** on a single installation
- You want access to a **large addon/module ecosystem**
- You have existing **GEDCOM files** and want the smoothest import experience

## Deployment Recommendations

### Reverse Proxy with HTTPS

Both platforms should sit behind a reverse proxy for TLS termination. Here's a minimal Caddy configuration:

```caddy
genealogy.example.com {
    reverse_proxy localhost:5000  # Gramps Web
    # OR
    reverse_proxy localhost:8080  # Webtrees
}
```

### Backup Strategy

For genealogy data, backups are critical — this is irreplaceable family history:

- **Gramps Web**: Back up the `/app/data` volume (contains the `.gramps` database) and all media volumes
- **Webtrees**: Use `mysqldump` for the database and back up the `data/` and `media/` directories
- Schedule automated daily backups and store them off-site
- Test restore procedures periodically

### User Management

Both platforms support multiple user accounts with different permission levels:

- **Administrator**: Full access to all settings and data
- **Editor**: Can modify records and add new individuals
- **Contributor**: Can add records but not modify others' data
- **Member**: Can view private data for their branch
- **Visitor**: Read-only access to public data

For related reading, see our [digital archive platforms comparison](../2026-04-23-archivematica-vs-omeka-s-vs-dspace-self-hosted-digital-archive-guide-2026/) for preserving historical documents alongside your family tree, and our [document management systems guide](../2026-04-27-mayan-edms-vs-teedy-vs-docspell-self-hosted-document-management-2026/) for organizing scanned family records and photographs.

## FAQ

### Can I import my existing GEDCOM file into Gramps Web or Webtrees?

Yes, both platforms support GEDCOM import. Webtrees has particularly strong GEDCOM compatibility as it was built around the standard from the ground up. Gramps Web can import GEDCOM files through its API or by loading them into Gramps Desktop and syncing. For complex GEDCOM files with non-standard tags, Webtrees tends to handle edge cases better.

### How do I share my family tree with relatives who aren't technically savvy?

Both platforms provide user-friendly web interfaces that work in any modern browser. Gramps Web offers a progressive web app (PWA) that can be installed on phones like a native app. Webtrees has a responsive design that adapts to mobile screens. You create user accounts for each relative and set their permission level — most family members only need "Visitor" or "Member" access.

### Is my family tree data safe if I self-host?

Your data is as safe as your backup strategy. Both platforms store data in standard formats (Gramps XML for Gramps Web, MySQL for Webtrees), so even if the application becomes unavailable, your data remains accessible. The key advantage of self-hosting is that **you** control the data — no company can change terms of service, raise prices, or shut down your account.

### Can both platforms handle large family trees with thousands of individuals?

Yes. Webtrees has been tested with trees containing 100,000+ individuals. Gramps Web handles large trees well but performance depends on your server's resources — the Gramps Desktop sync can be slow with very large databases. For trees with 50,000+ individuals, Webtrees' MySQL architecture tends to scale better out of the box.

### Do these platforms support living person privacy?

Absolutely. Both platforms have robust privacy controls for living individuals. Gramps Web uses role-based access control — you can restrict living person data to specific user roles. Webtrees offers per-person privacy rules that can automatically hide living individuals from visitors while showing them to authenticated family members. You can also set different privacy levels for specific records (e.g., show the person exists but hide birth details).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Gramps Web vs Webtrees: Self-Hosted Genealogy & Family Tree Guide (2026)",
  "description": "Compare Gramps Web and Webtrees for self-hosted genealogy. Learn about features, Docker deployment, privacy controls, and which family tree platform fits your needs.",
  "datePublished": "2026-05-01",
  "dateModified": "2026-05-01",
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
