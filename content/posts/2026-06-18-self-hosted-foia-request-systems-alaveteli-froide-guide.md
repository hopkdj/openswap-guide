---
title: "Self-Hosted FOIA Request Systems: Alaveteli vs Froide — Open-Source Freedom of Information Platforms"
date: "2026-06-18"
tags: ["self-hosted", "government-transparency", "foia", "freedom-of-information", "civic-tech", "open-government", "legal-tech"]
draft: false
---

## Introduction

Freedom of Information (FOI) laws exist in over 120 countries, giving citizens the legal right to request government documents and data. However, the process of making and tracking FOI requests has traditionally been cumbersome—involving paper forms, email chains, and opaque review processes. Open-source FOI platforms digitize this workflow, making it easier for citizens to submit requests and for government agencies to manage and respond to them.

In this guide, we compare the two leading open-source FOI request management platforms: **Alaveteli** (by mySociety, UK) and **Froide** (by Open Knowledge Foundation Germany). Both enable journalists, researchers, and citizens to file and track information requests, but they differ significantly in architecture, deployment model, and feature set.

### What to Look for in a FOI Platform

- **Multi-jurisdiction support**: Can the platform serve multiple public bodies?
- **Request workflow automation**: Automatic routing, deadline tracking, and reminder emails
- **Public archive**: Are completed requests published as a searchable public record?
- **Legal compliance**: Does the platform enforce statutory response deadlines?
- **Redaction tools**: Can agencies redact sensitive information before publishing responses?
- **API access**: Can third-party tools and data journalists access the request archive programmatically?

## Comparison Table: Alaveteli vs Froide

| Feature | Alaveteli | Froide |
|---------|-----------|--------|
| **GitHub Stars** | 416 | 410 |
| **Primary Language** | Ruby (Ruby on Rails) | Python (Django) |
| **Database** | PostgreSQL | PostgreSQL + PostGIS |
| **Search Engine** | PostgreSQL full-text | Elasticsearch |
| **Docker Support** | Official Compose | Official Compose |
| **Multi-tenancy** | Yes (themes system) | Yes (multi-site) |
| **Public Archive** | Yes, with redaction | Yes, with redaction |
| **Email Integration** | Built-in MTA (Postfix) | Django email backend |
| **API** | JSON API + RSS feeds | REST API (Django REST Framework) |
| **Crowdfunding** | No | Yes (Froide Crowdfunding) |
| **License** | AGPLv3 | MIT |
| **First Release** | 2010 | 2011 |
| **Last Update** | June 2026 | June 2026 |
| **Active Deployments** | 25+ countries | Germany, Austria, EU institutions |

## Deep Dive: Each Platform in Detail

### Alaveteli — The Global Standard

Alaveteli is the most widely deployed FOI platform globally, powering sites like WhatDoTheyKnow (UK), AskTheEU (EU), and QueremosSaber (multiple Latin American countries). Built by mySociety, the same nonprofit behind FixMyStreet, Alaveteli has been refined through real-world use across dozens of jurisdictions with different legal frameworks.

**Key Strengths:**
- **Proven at scale**: WhatDoTheyKnow alone has processed over 1 million FOI requests
- **Theme system**: Each Alaveteli installation can be fully branded and customized through the theme architecture without modifying core code
- **Legal deadline tracking**: Built-in awareness of FOI law deadlines per jurisdiction, with automatic escalation reminders
- **Mature admin interface**: Agency-side tools for batch processing, redaction, and response publishing

**Deployment with Docker Compose:**

```yaml
# alaveteli/docker-compose.yml
services:
  app:
    build:
      context: .
      dockerfile: docker/Dockerfile
      args:
        RUBY_VERSION: '3.4'
    tty: true
    stdin_open: true
    environment:
      - BUNDLE_PATH=/bundle/vendor
      - DATABASE_URL=postgres://postgres:password@db/
      - REDIS_URL=redis://redis:6379
      - SMTP_URL=smtp://smtp:1025
    ports:
      - 3000:3000
    volumes:
      - ./:/alaveteli
      - alaveteli_themes:/alaveteli-themes
      - bundle:/bundle
    depends_on:
      - db
      - redis
      - smtp

  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  smtp:
    image: mailhog/mailhog
    ports:
      - "1025:1025"
      - "8025:8025"

volumes:
  postgres_data:
  redis_data:
  alaveteli_themes:
  bundle:
```

**Post-deployment setup:**

```bash
# Initialize database and load default data
docker compose run --rm app bundle exec rake db:setup

# Load FOI law templates for your jurisdiction
docker compose run --rm app bundle exec rake themes:install

# Start all services
docker compose up -d
```

Alaveteli requires careful configuration of email delivery (it uses Postfix internally for request/response routing) and jurisdiction-specific FOI law parameters. The setup wizard guides administrators through public body registration, request categories, and statutory deadline configuration.

### Froide — Python-Powered FOI with Modern Features

Froide takes a more modern architectural approach, built on Django and Python. Originally developed for the German FOI portal FragDenStaat, it has expanded to serve Austria and EU institutions. Froide differentiates itself with several features Alaveteli lacks, including built-in crowdfunding for FOI lawsuits and GDPR-compliant data handling.

**Key Strengths:**
- **Crowdfunding integration**: Citizens can collectively fund legal appeals when FOI requests are denied
- **Elasticsearch-powered search**: Full-text search with faceted filtering, superior to PostgreSQL full-text search at scale
- **Django admin**: Leverages Django's powerful admin interface for agency-side management
- **GDPR-native**: Built with European data protection requirements from the ground up
- **Modular architecture**: Django app structure makes it easy to extend with custom functionality

**Deployment with Docker Compose:**

```yaml
# froide/docker-compose.yml
version: '3'

services:
  db:
    image: mdillon/postgis:10-alpine
    volumes:
      - ./data/postgres_data:/var/lib/postgresql/data/
    environment:
      POSTGRES_USER: froide
      POSTGRES_DB: froide
      POSTGRES_PASSWORD: froide
    ports:
      - "127.0.0.1:5432:5432"

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:7.17.0
    volumes:
      - ./data/elasticsearch-data:/usr/share/elasticsearch/data
    environment:
      - "discovery.type=single-node"
      - "cluster.routing.allocation.disk.threshold_enabled=false"
    ports:
      - "127.0.0.1:9200:9200"

  froide:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    depends_on:
      - db
      - elasticsearch
    environment:
      DATABASE_URL: postgis://froide:froide@db/froide
      ELASTICSEARCH_URL: http://elasticsearch:9200
      SECRET_KEY: change-this-in-production
      DEBUG: 'false'
```

**Production deployment with Gunicorn:**

```bash
# Instead of runserver, use Gunicorn for production
pip install gunicorn
gunicorn froide.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

**Initial setup:**

```bash
docker compose run froide python manage.py migrate
docker compose run froide python manage.py createsuperuser
docker compose run froide python manage.py loaddata froide/fixtures/*
docker compose run froide python manage.py rebuild_index
```

Froide can be deployed as a single-site installation or as a multi-tenant platform serving multiple public bodies. The `froide-foiidea` Django app enables the crowdfunding feature, which is particularly valuable for jurisdictions where FOI appeals require legal fees.

## Deployment Architecture

```
┌─────────────────────────────────────────────────┐
│              Reverse Proxy (Nginx)               │
│            SSL Termination + Caching             │
├─────────────────────┬───────────────────────────┤
│      Alaveteli       │         Froide             │
│   (Ruby on Rails)    │     (Python/Django)        │
├─────────────────────┼───────────────────────────┤
│     PostgreSQL       │  PostgreSQL + PostGIS      │
│     + Redis          │  + Elasticsearch           │
├─────────────────────┼───────────────────────────┤
│   Postfix (MTA)      │   Django Email Backend     │
│   + MailHog (dev)    │   + Celery Workers         │
└─────────────────────┴───────────────────────────┘
```

Both platforms require PostgreSQL and an email delivery system. Froide's Elasticsearch dependency provides superior search at the cost of additional operational complexity. For deployments under 100,000 requests, Alaveteli's PostgreSQL full-text search is sufficient.

## Why Self-Host Your FOI Platform?

Running your own FOI platform gives journalists, researchers, and advocacy groups complete control over the request archive—a critical consideration when the information being requested may be politically sensitive. Commercial FOI management solutions (e.g., GovQA, JustFOIA) charge per-seat or per-request fees that quickly become prohibitive for high-volume users. Open-source platforms ensure that the public archive of completed requests remains freely accessible, creating a permanent record of government transparency.

For managing the documents received through FOI requests, check our [self-hosted document management guide](../2026-04-27-mayan-edms-vs-teedy-vs-docspell-self-hosted-document-management-2026/). For automating document generation and responses, see our [document automation comparison](../2026-05-03-docassemble-vs-docxtemplater-vs-pandoc-self-hosted-document-automation-guide/). If you're also publishing open government data, our [open data portals guide](../2026-06-08-open-data-portals-ckan-vs-dkan-vs-dataverse/) covers CKAN, DKAN, and Dataverse.


## Choosing the Right FOI Platform for Your Jurisdiction

When selecting between Alaveteli and Froide, consider your technical team's expertise and your jurisdiction's specific legal requirements. Ruby shops with existing Rails infrastructure will find Alaveteli a natural fit, while Python/Django teams will prefer Froide's familiar architecture. If your FOI law includes provisions for legal appeals, Froide's built-in crowdfunding feature can help citizens fund challenges to denied requests—a capability Alaveteli lacks. For multi-jurisdiction deployments spanning different legal frameworks, Alaveteli's mature theming system provides the most battle-tested approach.


## FAQ

### Can Alaveteli handle different FOI laws across jurisdictions?

Yes, it's designed for it. Each Alaveteli theme includes jurisdiction-specific configurations: statutory response deadlines, appeal processes, public body classifications, and exemption categories. The UK deployment enforces a 20-working-day deadline, while EU deployments follow Regulation 1049/2001 timelines. Administrators configure these through YAML configuration files without modifying application code.

### What's the difference between Alaveteli and WhatDoTheyKnow?

WhatDoTheyKnow (whatdotheyknow.com) is the UK's national FOI portal, which runs on Alaveteli. Alaveteli is the open-source software platform; WhatDoTheyKnow is the specific deployment serving UK citizens. Other Alaveteli deployments include AskTheEU (EU institutions), KiMitTud (Hungary), and QueremosSaber (Latin America).

### Does Froide support automated redaction?

Froide provides manual redaction tools in its admin interface but does not include automated PII (personally identifiable information) detection. For automated redaction, you can integrate external tools like Presidio or custom spaCy models as Django management commands. Alaveteli similarly relies on manual redaction, though there are community scripts for batch processing.

### How do I handle large file attachments (e.g., government PDFs over 100MB)?

Both platforms support large file uploads but require configuration. Alaveteli uses direct-to-disk uploads through the Rails Active Storage framework, configurable for S3-compatible object storage. Froide uses Django's file storage backend, also pluggable to S3. For production deployments processing large government datasets, external object storage (MinIO, AWS S3) is strongly recommended to avoid filling the application server's local disk.

### Is there a SaaS alternative if I don't want to self-host?

mySociety offers a managed Alaveteli hosting service for government agencies and NGOs, including setup, maintenance, and upgrades. The Open Knowledge Foundation provides similar services for Froide through FragDenStaat. Both organizations also offer consulting for custom integrations and legal compliance configuration.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted FOIA Request Systems: Alaveteli vs Froide — Open-Source Freedom of Information Platforms",
  "description": "Compare Alaveteli (416 stars, Ruby/Rails) vs Froide (410 stars, Python/Django) for self-hosted Freedom of Information request management. Includes Docker Compose configs, deployment architecture, and jurisdictional FOI law configuration.",
  "datePublished": "2026-06-18",
  "dateModified": "2026-06-18",
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

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
