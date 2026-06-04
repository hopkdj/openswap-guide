---
title: "Self-Hosted Scholarly Publishing Platforms: OJS vs Janeway vs Lodel"
date: "2026-06-04"
tags: ["scholarly-publishing", "academic", "open-access", "journal", "publishing", "research", "cms"]
draft: false
---

## Introduction

The open access movement has transformed academic publishing over the past two decades. Where researchers once depended entirely on commercial publishers to distribute their work, today's institutions can operate fully self-hosted journal platforms that manage the entire editorial workflow — from manuscript submission through peer review to final publication. Running your own scholarly publishing platform gives universities, research centers, and independent journals complete control over their content, review processes, and reader access.

Open Journal Systems (OJS), Janeway, and Lodel represent three distinct approaches to self-hosted academic publishing. OJS is the established leader with thousands of active journals worldwide; Janeway offers a modern Python-based alternative with preprint support; and Lodel provides a unique semantic publishing model popular in European humanities research. This comparison helps editors and institutions choose the right platform for their publishing needs.

## Project Overview

| Feature | OJS | Janeway | Lodel |
|---------|-----|---------|-------|
| **Language** | PHP | Python (Django) | PHP |
| **Stars** | 993 | 229 | 53 |
| **License** | GPL v2/v3 | AGPL v3 | GPL v2 |
| **Database** | MySQL/MariaDB, PostgreSQL | PostgreSQL | MySQL |
| **Container Support** | Docker images available | Docker Compose support | Manual setup |
| **Submission Workflow** | Full editorial workflow with roles | Full editorial workflow | Customizable workflows |
| **Peer Review Types** | Single-blind, double-blind, open | Single-blind, double-blind, open | Configurable |
| **Preprint Support** | Via OPS (separate install) | Built-in | Via configuration |
| **OAI-PMH** | Built-in | Built-in | Built-in |
| **DOI Registration** | Built-in Crossref plugin | Built-in Crossref support | Manual configuration |
| **Multi-Journal** | Yes (single install) | Yes | Yes |
| **Theme System** | Extensive theme marketplace | Bootstrap-based themes | Custom CSS templates |
| **Plugin Ecosystem** | 100+ plugins | Growing | Limited |

## Architecture Deep-Dive

### Open Journal Systems (OJS): The Established Standard

Developed by the Public Knowledge Project (PKP) and first released in 2001, OJS powers over 10,000 journals worldwide and is the de facto standard for open access publishing. Its PHP/MySQL architecture runs on commodity web hosting, making it accessible to journals without dedicated IT staff.

OJS implements a complete editorial workflow: author registration, manuscript submission, editor assignment, reviewer selection, peer review management, copyediting, layout, proofreading, and publication. Each role — author, reviewer, section editor, copyeditor, layout editor, proofreader, journal manager — has a dedicated dashboard with role-specific tasks and notifications.

The plugin ecosystem is OJS's greatest strength. Plugins extend functionality for everything from Altmetric badges and Hypothes.is annotation to ORCID integration and Fidus Writer collaborative editing. The PKP Preservation Network (PN) provides distributed digital preservation through LOCKSS. OJS also supports multilingual journals, subscription-based access alongside open access, and integration with scholarly indexing services like DOAJ, Scopus, and Web of Science.

### Janeway: Modern Python Publishing

Janeway, developed at Birkbeck, University of London's Centre for Technology and Publishing, represents a ground-up rethink of scholarly publishing software. Built on Django, Janeway brings modern web development practices — responsive design, REST API, ORCID integration — to academic publishing without the legacy overhead of older platforms.

Janeway's distinguishing feature is its built-in preprint server functionality. While OJS requires a separate Open Preprint Systems (OPS) installation, Janeway handles both traditional journals and preprint servers within the same platform. This makes it ideal for institutions operating both a journal and a preprint repository, as authors can submit to the preprint server and later transfer to a journal for formal peer review.

The platform includes native support for JATS XML, automated typesetting via the `typeset` plugin (which generates PDF and EPUB from XML), and a plugin architecture for extending functionality. Janeway's theming system uses standard Django templates, making customization accessible to Python developers. Its REST API enables programmatic access to published content, supporting text mining and interoperability with institutional repositories.

### Lodel: Semantic Publishing for Humanities

Lodel, developed by OpenEdition (a French academic publishing infrastructure), takes a fundamentally different approach to scholarly publishing. Rather than managing individual articles, Lodel treats documents as structured semantic entities with rich metadata. This model originated in French humanities and social sciences publishing and remains strongest in European academic communities.

Lodel's distinguishing feature is its "semantic publishing" paradigm. Documents are not just HTML pages — they are structured entities with explicit relationships to authors, keywords, citations, and sections. This enables advanced features like automatic table of contents generation from heading structure, citation formatting from structured metadata, and semantic search across document collections.

The platform supports multi-format output from a single source: the same Lodel document can generate HTML, PDF, XML/TEI, and EPUB versions. Lodel's template system allows complete control over output formatting, and its import/export system handles complex document structures including footnotes, endnotes, bibliographies, and multi-level indexes.

## Deployment

### OJS with Docker

```yaml
version: "3.8"
services:
  ojs:
    image: pkpofficial/ojs:stable-3_4_0
    ports:
      - "8080:80"
    environment:
      - OJS_DB_HOST=db
      - OJS_DB_USER=ojs
      - OJS_DB_PASSWORD=changeme
      - OJS_DB_NAME=ojs
    volumes:
      - ojs-files:/var/www/files
      - ojs-public:/var/www/html/public
      - ojs-config:/var/www/html/config.inc.php
    depends_on:
      - db
  db:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=changeme
      - MYSQL_DATABASE=ojs
      - MYSQL_USER=ojs
      - MYSQL_PASSWORD=changeme
    volumes:
      - db-data:/var/lib/mysql

volumes:
  ojs-files:
  ojs-public:
  ojs-config:
  db-data:
```

### Janeway with Docker Compose

```yaml
version: "3.8"
services:
  janeway-web:
    image: birkbeckctp/janeway:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_HOST=db
      - DATABASE_NAME=janeway
      - DATABASE_USER=janeway
      - DATABASE_PASSWORD=changeme
      - DEBUG=False
      - SECRET_KEY=your-secret-key-here
    volumes:
      - janeway-media:/vol/janeway/src/media
      - janeway-static:/vol/janeway/src/static
    depends_on:
      - db
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=janeway
      - POSTGRES_USER=janeway
      - POSTGRES_PASSWORD=changeme
    volumes:
      - postgres-data:/var/lib/postgresql/data

volumes:
  janeway-media:
  janeway-static:
  postgres-data:
```

### Lodel Installation

Lodel requires manual server setup with Apache/Nginx and MySQL:

```bash
# Install dependencies
sudo apt install apache2 mysql-server php php-mysql php-xml php-mbstring php-zip

# Clone Lodel
git clone https://github.com/OpenEdition/lodel.git
cd lodel

# Configure
cp lodel/install/contexts/sample.php lodel/contexts/local.php
# Edit local.php with database credentials

# Web setup
sudo ln -s $(pwd)/lodel/htdocs /var/www/html/lodel
```

## Why Self-Host Your Journal Platform?

Academic publishing infrastructure represents one of the most important areas for institutional self-hosting. When universities rely on commercial publishing platforms, they lose control over pricing, access policies, and long-term preservation of the scholarly record. Major publishers charge thousands of dollars annually per journal — money that flows out of research budgets and into corporate profits.

Self-hosting with open-source platforms puts editorial control back in the hands of scholars. Editors can customize peer review workflows to match their discipline's norms rather than adapting to a one-size-fits-all commercial system. Reviewers don't need accounts on publisher platforms that track their behavior. Readers anywhere in the world can access research without paywalls — fulfilling the original promise of the open access movement.

Digital preservation is another critical concern. When journals close or publishers merge, content hosted on commercial platforms can disappear. With LOCKSS integration, OJS journals participate in a distributed preservation network where multiple libraries maintain redundant copies. Self-hosted platforms allow institutions to guarantee perpetual access to their scholarly output regardless of commercial platform viability.

Long-term cost analysis strongly favors self-hosting. A typical society journal might pay $3,000-$5,000 per year for a commercial hosting platform. Self-hosting on a $20/month VPS with OJS or Janeway provides equivalent functionality at a fraction of the cost, with the savings available for copyediting, typesetting, or author processing charge waivers.

For related reading on self-hosted knowledge management, see our [wiki engines comparison](../2026-04-23-mediawiki-vs-xwiki-vs-dokuwiki-self-hosted-wiki-engines-guide-2026/) and [headless CMS guide](../2026-05-04-payload-cms-vs-strapi-vs-directus-self-hosted-headless-cms/). If your publishing workflow includes managing supplementary research data, our [research data repository comparison](../2026-05-02-koha-vs-omeka-vs-invenio-self-hosted-library-digital-collection-guide/) covers complementary tools.

## FAQ

### Can OJS handle subscription-based journals alongside open access?

Yes. OJS supports delayed open access (embargo periods), hybrid journals where some articles are open and others subscription-only, and fully subscription-based models. It includes built-in subscription management with payment processing via PayPal. Janeway and Lodel focus on open access by design and do not have native subscription commerce features.

### How well do these platforms handle multilingual content?

OJS has the strongest multilingual support, with the interface translated into 30+ languages and the ability to publish articles in multiple languages simultaneously. Janeway's Django framework supports internationalization (i18n) through standard Python tooling but has fewer community translations. Lodel, developed in France, handles French exceptionally well and supports other European languages, though its administration interface is primarily in French.

### What about indexing in Google Scholar and academic databases?

All three platforms generate metadata that Google Scholar can index when properly configured. OJS has the strongest indexing support with built-in plugins for DOAJ, Crossref, PubMed, and Scopus. Janeway supports Crossref and OAI-PMH for metadata harvesting. Lodel supports OAI-PMH which enables harvesting by search engines and aggregators. For optimal Google Scholar visibility, ensure your platform serves structured metadata in Dublin Core, HighWire Press, or schema.org formats.

### Can I migrate from one platform to another?

Migration is possible but requires effort. OJS provides import tools for several formats. Janeway offers an OJS migration plugin for importing journals from OJS 3.x. Lodel provides XML-based import pipelines. The common thread is that having your content in a structured format (JATS XML, OAI-PMH metadata, or CSV) makes migration possible. Plan for a multi-week migration process including metadata cleanup, file transfer, and URL redirect configuration.

### Do I need a separate server for multiple journals?

OJS and Janeway both support hosting multiple journals from a single installation. Each journal gets its own URL path, theme, editorial team, and settings. This is the recommended approach for university presses and library publishing programs that oversee multiple journals. Lodel also supports multi-journal hosting through its instance system, though it is less commonly used for this purpose than OJS.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Scholarly Publishing Platforms: OJS vs Janeway vs Lodel",
  "description": "Compare Open Journal Systems (OJS), Janeway, and Lodel for self-hosted academic journal publishing. Covers editorial workflows, peer review, Docker deployment, and institutional hosting strategies.",
  "datePublished": "2026-06-04",
  "dateModified": "2026-06-04",
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
