---
title: "Self-Hosted Archaeology Data Platforms: Arches vs OpenAtlas for Heritage Data Management"
date: "2026-06-15"
tags: ["archaeology", "cultural-heritage", "geospatial", "digital-humanities", "data-management", "self-hosted"]
draft: false
---

## Introduction

Archaeological fieldwork generates enormous volumes of structured data — excavation contexts, artifact catalogs, radiocarbon dates, geospatial surveys, and photographic documentation. Managing this data in spreadsheets and file folders is unsustainable for long-term research projects. Self-hosted archaeology data platforms provide purpose-built data models, geospatial capabilities, and web-based interfaces designed specifically for heritage data management.

This guide compares two leading open-source archaeology data platforms: **Arches**, a comprehensive heritage inventory and data management system originally developed by the Getty Conservation Institute and World Monuments Fund; and **OpenAtlas**, a web-based database system for complex archaeological, historical, and geospatial data developed by the Austrian Academy of Sciences.

## Comparison Table

| Feature | Arches | OpenAtlas |
|---------|--------|-----------|
| **Data Model** | CIDOC-CRM compliant graph | CIDOC-CRM compliant graph |
| **Geospatial Support** | Full GIS (GeoJSON, PostGIS, map layers) | Leaflet-based mapping, GeoJSON |
| **Controlled Vocabularies** | Built-in thesaurus management | Reference system with external vocabularies |
| **Timeline Visualization** | Built-in time wheel | Temporal data display |
| **IIIF Image Support** | Yes (integration) | Yes |
| **API Access** | REST API | REST API |
| **Multi-Tenant** | Yes (multiple projects) | Single instance model |
| **Search** | Elasticsearch | PostgreSQL full-text |
| **Mobile Data Collection** | Arches Collector app | Web-responsive forms |
| **Docker Support** | Official Docker Compose | Docker available |
| **License** | AGPL-3.0 | GPL-2.0 |
| **Stars** | 279 | 98 |
| **Last Updated** | June 2026 | June 2026 |

## Arches: Enterprise Heritage Inventory Management

Arches is the most comprehensive open-source platform designed specifically for cultural heritage inventory and management. It was developed through a partnership between the Getty Conservation Institute and World Monuments Fund, and is now used by heritage organizations worldwide including national governments, UNESCO projects, and municipal preservation offices.

### Key Features

- **CIDOC-CRM compliance**: The underlying data model conforms to the ISO 21127:2014 standard for cultural heritage information, ensuring semantic interoperability with other CIDOC-CRM compliant systems
- **Graph database architecture**: Uses a graph-based data model (backed by PostgreSQL/PostGIS and Elasticsearch) rather than traditional relational tables, enabling flexible relationship modeling between heritage resources
- **Resource relationship modeling**: Model complex relationships such as "artifact A was found in context B during excavation C directed by archaeologist D"
- **Built-in thesaurus management**: Integrated controlled vocabulary system for consistent terminology across your organization
- **Arches Designer**: No-code interface for customizing data entry forms, reports, and the data model without programming
- **Arches Collector**: Mobile data collection app for field survey and condition assessment
- **Workflow management**: Configurable review and approval workflows for data entry and publication

### Docker Deployment

Arches provides an official Docker Compose configuration for production deployment:

```yaml
# docker-compose.yml
version: '3.8'
services:
  arches:
    image: archesproject/arches:7.6
    container_name: arches
    ports:
      - "8000:8000"
    volumes:
      - ./arches-data:/ arches/arches/uploadedfiles
    depends_on:
      - db
      - elasticsearch
    environment:
      - ARCHES_PROJECT=my_archaeology_project
      - DJANGO_SETTINGS_MODULE=arches.settings
      - ELASTICSEARCH_HOSTS=elasticsearch:9200
    restart: unless-stopped

  db:
    image: postgis/postgis:15-3.4
    container_name: arches-db
    volumes:
      - ./pgdata:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=secure_password
      - POSTGRES_DB=arches
    restart: unless-stopped

  elasticsearch:
    image: elasticsearch:8.11
    container_name: arches-es
    volumes:
      - ./esdata:/usr/share/elasticsearch/data
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    restart: unless-stopped
```

The initial setup requires running the Arches project creation command and loading reference data packages.

## OpenAtlas: Research-Focused Archaeological Database

OpenAtlas is an open-source, web-based database system developed by the Austrian Centre for Digital Humanities and Cultural Heritage at the Austrian Academy of Sciences. It is designed specifically for academic archaeological research projects and historical data management.

### Key Features

- **Entity-relationship model**: Models archaeological entities (sites, finds, actors, events) and their relationships using a graph approach consistent with CIDOC-CRM
- **Geospatial integration**: Built-in Leaflet-based mapping with support for GeoJSON, shapefile import, and coordinate management
- **Temporal data**: Type-specific date handling with support for fuzzy dating, date ranges, and calendar systems
- **File management**: Attach documents, images, and 3D models to any entity
- **Presentation sites**: Build public-facing project websites directly from the database with configurable layouts
- **Linked Open Data**: Entities receive persistent URIs and can reference external authority files, Nomisma coin references, and GeoNames place identifiers
- **Multi-language support**: User interface and data entry forms available in multiple languages

### Docker Deployment

OpenAtlas can be deployed using Docker:

```yaml
# docker-compose.yml
version: '3.8'
services:
  openatlas:
    image: craws/openatlas:latest
    container_name: openatlas
    ports:
      - "8080:80"
    volumes:
      - ./uploads:/var/www/html/uploads
      - ./exports:/var/www/html/exports
    depends_on:
      - openatlas-db
    environment:
      - DATABASE_URL=postgresql://openatlas:password@openatlas-db/openatlas
      - MAIL_HOST=smtp.example.com
    restart: unless-stopped

  openatlas-db:
    image: postgis/postgis:15-3.4
    container_name: openatlas-db
    volumes:
      - ./pgdata:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=openatlas
      - POSTGRES_USER=openatlas
    restart: unless-stopped
```

## Why Self-Host Your Archaeological Data?

Archaeological data has unique requirements that make self-hosting particularly valuable. Unlike many other types of research data, archaeological datasets often contain **sensitive location information** that cannot be publicly exposed — unexcavated sites, sacred indigenous locations, and sites vulnerable to looting all require controlled access. Self-hosted platforms give you granular permission controls that cloud services rarely provide.

**Long-term preservation** is critical in archaeology. Excavation data needs to remain accessible for decades or centuries — far longer than any commercial SaaS platform's lifespan. Arches and OpenAtlas use open standards (CIDOC-CRM, GeoJSON, CSV exports) that ensure data remains migratable even if the software itself stops being maintained. The Archaeological Data Service (ADS) in the UK recommends open-source platforms specifically for this longevity reason.

**Custom data models** are essential because every excavation uses different recording systems. Both Arches and OpenAtlas allow you to customize the data model without programming — Arches through its Designer interface and OpenAtlas through its type system. This flexibility means you can model single-context recording (UK system), stratigraphic units (Italian system), or arbitrary grid excavation (North American system) within the same platform.

For related geospatial self-hosted guides, see our [GIS Server Platforms comparison](../2026-05-19-self-hosted-vector-tile-servers-tegola-vs-tileserver-gl/). If you need to manage related scientific data, check our [Lab Sample Tracking guide](../2026-06-14-self-hosted-lab-sample-tracking-biobank-management-guide/).

## Data Migration and Interoperability Planning

When adopting a new archaeology data platform, plan your migration strategy before deployment:

- **Legacy data extraction**: Export existing data to CSV or structured XML. For FileMaker Pro databases, use the XML export feature. For Excel spreadsheets, standardize column names first.
- **Controlled vocabulary mapping**: Map your existing terminology to standard vocabularies (Getty AAT for artifact types, PeriodO for chronological periods)
- **Geospatial transformation**: Convert existing coordinate data to WGS84 (EPSG:4326) for web mapping compatibility
- **Incremental migration**: Start with a pilot project (one excavation season or one site) before migrating the entire collection

## FAQ

### Which platform is better for a small excavation project with a single archaeologist?

OpenAtlas is generally more suitable for small to medium research projects. It has a simpler deployment (fewer Docker containers), a more focused feature set, and is designed for academic research teams rather than enterprise heritage management. Arches is designed for institutional-scale deployments with multiple concurrent users, complex workflows, and enterprise requirements like multi-tenancy.

### How do these platforms handle radiocarbon dating and chronological modeling?

Both platforms support temporal data, but in different ways. OpenAtlas has native support for date ranges, fuzzy dating (e.g., "early 5th century BCE"), and multiple calendar systems. Arches supports temporal data through its time wheel visualization and can model complex chronological relationships. For advanced Bayesian chronological modeling (OxCal, ChronoModel), export your dates to CSV and process them in the specialized tools, then re-import the modeled date ranges.

### Can I publish my excavation data to the web for public access?

Yes, both platforms support public-facing views. Arches has a built-in public interface with faceted search, map visualization, and detailed resource reports. OpenAtlas has a presentation site feature that generates public project websites from the database. Both allow you to control exactly which data is public and which remains restricted to authenticated users.

### What about 3D model support for photogrammetry and laser scanning?

Both platforms support file attachments, which can include 3D models (OBJ, PLY, glTF formats). For interactive 3D viewing in the web browser, you can integrate separate 3D viewers or host models on platforms like Sketchfab (self-hosted alternatives exist using three.js). The IIIF standard also supports 3D content through the IIIF 3D Community Group specification, which both platforms can integrate.

### How do I handle legacy data from old FileMaker Pro databases?

Export your FileMaker data as XML or CSV. For OpenAtlas, use the CSV import feature after mapping your FileMaker fields to OpenAtlas types. For Arches, use the bulk data import tools with the Arches JSON-LD or CSV format. Expect to spend significant time on data cleaning — inconsistent date formats, free-text fields that should be controlled vocabularies, and missing geospatial coordinates are common issues in legacy archaeological databases.

### Is there a way to sync field data collected on tablets?

Arches provides the Arches Collector mobile app for offline field data collection with synchronization when connectivity is restored. For OpenAtlas, the web interface is responsive and works on tablets, but offline sync requires manual CSV export/import workflows. For extensive field survey, consider using QField (QGIS mobile) for geospatial data collection and importing the results into your archaeology platform.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Archaeology Data Platforms: Arches vs OpenAtlas for Heritage Data Management",
  "description": "Compare Arches and OpenAtlas, two open-source self-hosted platforms for archaeological data management. Covers CIDOC-CRM compliant heritage inventories, geospatial capabilities, Docker deployment, and data migration strategies.",
  "datePublished": "2026-06-15",
  "dateModified": "2026-06-15",
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
