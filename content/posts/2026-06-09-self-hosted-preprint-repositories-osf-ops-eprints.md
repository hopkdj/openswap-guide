---
title: "Self-Hosted Preprint Repositories: OSF Preprints vs OPS vs EPrints"
date: "2026-06-09"
tags: ["preprint", "open-science", "academic-publishing", "research", "self-hosted", "scholarly-communication"]
draft: false
---

The traditional academic publishing pipeline is slow, expensive, and gated behind paywalls. Preprint servers have emerged as a powerful alternative — letting researchers share findings immediately, before formal peer review, at zero cost to readers. While mega-servers like arXiv, bioRxiv, and SSRN dominate the landscape, there are compelling reasons to run your own institutional or community preprint repository. In this guide, we compare three open-source, self-hosted preprint platforms: **OSF Preprints**, **Open Preprint Systems (OPS)**, and **EPrints**.

## Why Self-Host Your Preprint Repository?

Running your own preprint server gives your institution or research community full control over the submission workflow, branding, metadata standards, and long-term preservation strategy. Instead of depending on a third-party platform that could change its policies — or shut down — you own the infrastructure.

A self-hosted preprint repository also integrates naturally with your existing scholarly ecosystem. You can enforce discipline-specific metadata schemas, connect to your institutional repository for seamless archiving, and implement custom review or moderation workflows that generic platforms cannot offer. For research organizations handling sensitive data or working in fields with strict regulatory requirements, local hosting ensures compliance while still enabling rapid dissemination.

For broader context on self-hosted scholarly infrastructure, see our [guide to open access journal platforms](../2026-06-04-scholarly-publishing-platforms-ojs-janeway-lodel-guide/). If you are also managing research data alongside preprints, our [digital archives comparison](../2026-04-23-archivematica-vs-omeka-s-vs-dspace-self-hosted-digital-archive-guide-2026/) covers complementary preservation tools. For version control in research workflows, check our [lightweight Git platform comparison](../2026-04-26-gogs-vs-gitbucket-vs-onedev-lightweight-self-hosted-git-platforms-2026/).

## Comparison at a Glance

| Feature | OSF Preprints | OPS (Open Preprint Systems) | EPrints |
|---------|---------------|----------------------------|---------|
| **GitHub Stars** | 727 | 50 | 67 |
| **Primary Language** | Python (Django) | PHP | Perl |
| **Database** | PostgreSQL | MySQL/PostgreSQL | MySQL/PostgreSQL |
| **DOI Integration** | Built-in (CrossRef, DataCite) | Via plugin | Via plugin |
| **Moderation Workflow** | Configurable pre/post | Configurable | Configurable |
| **OAI-PMH Support** | Yes | Yes | Yes |
| **Multi-Tenant** | Yes | Limited | Via separate instances |
| **Docker Support** | docker-compose.yml | Docker image available | Limited |
| **Latest Release** | Active (2026) | Active (2026) | Stable (2023, maintained) |
| **Theming/Customization** | Limited branding | Full theme system | Full theme system |

## OSF Preprints: The Full-Stack Research Platform

OSF (Open Science Framework) Preprints is part of the larger OSF ecosystem maintained by the Center for Open Science. It is the most feature-complete option — offering preprint hosting, project management, data storage, and registration all in one platform.

**Key Strengths:**
- Built-in support for 30+ preprint services through SHARE
- Native DOI minting with CrossRef and DataCite
- Rich contributor management (ORCID integration, unregistered contributors)
- Automatic indexing in Google Scholar and other discovery systems
- REST API for programmatic submission and retrieval

**Deployment:** OSF uses Docker Compose for local development and can be deployed in production with the included configuration. Here is the core service definition:

```yaml
# docker-compose.yml (core services)
version: '3'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: osf
      POSTGRES_USER: osf
      POSTGRES_PASSWORD: changeme
    volumes:
      - postgres_data:/var/lib/postgresql/data

  rabbitmq:
    image: rabbitmq:3-management
    environment:
      RABBITMQ_DEFAULT_USER: osf
      RABBITMQ_DEFAULT_PASS: changeme

  elasticsearch:
    image: elasticsearch:7.17
    environment:
      discovery.type: single-node
      xpack.security.enabled: false

  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgres://osf:changeme@postgres:5432/osf
      ELASTICSEARCH_URL: http://elasticsearch:9200/
      RABBITMQ_URL: amqp://osf:changeme@rabbitmq:5672/
    depends_on:
      - postgres
      - rabbitmq
      - elasticsearch
    volumes:
      - ./:/code

volumes:
  postgres_data:
```

## Open Preprint Systems (OPS): Journal-Adjacent Preprints

OPS is developed by the Public Knowledge Project (PKP), the same organization behind Open Journal Systems (OJS) — the most widely used open-source journal management platform. OPS shares the same architecture as OJS, making it an excellent choice for institutions already running PKP software.

**Key Strengths:**
- Familiar interface for OJS users — shared codebase, shared plugins
- Robust submission and review workflow with editorial stages
- ORCID, Crossref, and ROR integration
- Extensive plugin ecosystem (themes, import/export formats, statistics)
- Active community with regular releases

**Deployment:** OPS provides official Docker images. Here is a minimal deployment configuration:

```yaml
# docker-compose.yml for OPS
version: '3'
services:
  ops:
    image: pkpofficial/ops:3.4
    ports:
      - "8080:80"
    environment:
      OPS_DB_HOST: db
      OPS_DB_USER: ops
      OPS_DB_PASSWORD: changeme
      OPS_DB_NAME: ops
    volumes:
      - ops_files:/var/www/files
      - ops_public:/var/www/html/public
      - ops_config:/var/www/html/config.inc.php
    depends_on:
      - db

  db:
    image: mariadb:10.6
    environment:
      MYSQL_ROOT_PASSWORD: changeme
      MYSQL_DATABASE: ops
      MYSQL_USER: ops
      MYSQL_PASSWORD: changeme
    volumes:
      - db_data:/var/lib/mysql

volumes:
  ops_files:
  ops_public:
  ops_config:
  db_data:
```

After starting the containers, complete the setup by navigating to `http://your-server:8080` and following the web-based installer.

## EPrints: The Veteran Repository Platform

EPrints is the oldest actively maintained open-source repository software, originally developed at the University of Southampton in 2000. While it started as a general-purpose institutional repository, EPrints has robust preprint capabilities and is still used by hundreds of universities worldwide.

**Key Strengths:**
- Mature, battle-tested codebase with decades of production use
- Extremely flexible metadata system — define any schema
- Powerful import/export pipeline (EPrints XML, BibTeX, RIS, DSpace, METS)
- Fine-grained access control at the document level
- Strong OAI-PMH provider implementation

**Deployment:** EPrints runs on a traditional LAMP stack. While official Docker images are limited, the community maintains deployment recipes:

```bash
# Install EPrints on Ubuntu 22.04
sudo apt update
sudo apt install -y apache2 mariadb-server perl libapache2-mod-perl2   libmariadb-dev libxml-libxml-perl libunicode-string-perl   libterm-readkey-perl libmime-lite-perl libmime-types-perl   libdigest-sha-perl libdbd-mysql-perl libxml-parser-perl   libxml2-dev libxslt1-dev imagemagick antiword elinks   texlive-base texlive-latex-base texlive-latex-recommended

# Download and install EPrints
wget https://files.eprints.org/2712/1/eprints-3.4.5.tar.gz
tar xzf eprints-3.4.5.tar.gz
cd eprints-3.4.5
./configure --with-user=eprints --with-group=eprints
sudo make install
```

### Installation and Configuration

All three platforms can run on modest hardware — a server with 4 GB RAM and 2 CPU cores is sufficient for departmental or small-institution preprint servers. For larger deployments serving thousands of papers, scale up RAM to 8-16 GB and consider separating the database onto its own server.

After installation, configure your repository's metadata schema, submission policy, and moderation workflow. Most platforms support embargo periods, versioning, and withdrawal mechanisms — critical for preprint servers where content may later appear in peer-reviewed journals.


### Choosing the Right Platform for Your Community

The choice between these platforms often comes down to your existing ecosystem. If your institution already runs OJS for journal publishing, OPS provides a familiar administration experience with shared plugins and theming. If you need a full-stack research platform with data storage, project management, and preprint hosting in one system, OSF Preprints is the clear winner. For institutions with long-standing repository infrastructure built on LAMP stacks, EPrints offers a proven path with minimal architectural disruption. All three platforms produce standards-compliant metadata, ensuring your preprints are discoverable through Google Scholar, BASE, CORE, and other academic search engines.

Beyond feature comparison, consider the long-term sustainability of your choice. OSF is backed by the Center for Open Science, a well-funded non-profit with a large development team. OPS benefits from PKP's established community and regular release cycle. EPrints, while more slowly maintained, has survived for over 20 years through institutional commitment. Your preprint repository is a long-term investment — choose a platform whose governance model aligns with your institution's time horizon.

## FAQ

### What is the difference between a preprint server and an institutional repository?

A preprint server focuses on rapid dissemination of research before formal peer review, typically with minimal editorial screening. An institutional repository is a broader archive of all scholarly outputs from an institution, including theses, datasets, and published papers. The two can coexist — many universities use EPrints or DSpace for their institutional repository and run a separate preprint server for rapid sharing.

### Do self-hosted preprint servers get indexed by Google Scholar?

Yes, all three platforms covered here support the metadata standards (primarily OAI-PMH and Dublin Core) that Google Scholar and other academic search engines use for indexing. OSF Preprints has particularly strong indexing support out of the box. For all platforms, ensure your sitemap is properly configured and that each preprint has a unique, persistent URL.

### Can I integrate ORCID with these platforms?

OSF Preprints has native ORCID integration for author identification. OPS supports ORCID through its plugin system (the ORCID Profile plugin). EPrints can integrate ORCID via its authentication module. For all platforms, ORCID helps disambiguate authors and connects preprints to researchers' profiles.

### What about DOI minting for preprints?

OSF Preprints includes built-in DOI minting via CrossRef and DataCite. OPS supports DOI assignment through the Crossref or DataCite plugins. EPrints provides DOI minting through its DataCite module. For any platform, you will need an account with CrossRef or DataCite and a DOI prefix assigned to your organization.

### How much does it cost to run a self-hosted preprint server?

The software is free and open source. Your primary costs are server hosting ($20-100/month depending on scale), a DOI prefix from CrossRef ($275/year for members), and staff time for administration and moderation. Compared to commercial preprint hosting services, self-hosting typically pays for itself within the first year for institutions publishing more than 100 preprints annually.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Preprint Repositories: OSF Preprints vs OPS vs EPrints",
  "description": "Comprehensive comparison of three open-source, self-hosted preprint repository platforms for research institutions and academic communities.",
  "datePublished": "2026-06-09",
  "dateModified": "2026-06-09",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://pistack.xyz/logo.png"
    }
  }
}
</script>

---

**💡 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
