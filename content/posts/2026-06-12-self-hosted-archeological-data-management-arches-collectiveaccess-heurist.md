---
title: "Self-Hosted Archeological Data Management: Arches vs CollectiveAccess vs Heurist"
date: "2026-06-12"
tags: ["cultural-heritage", "archaeology", "collections-management", "geospatial", "digital-humanities", "research-data"]
draft: false
---

## Introduction

Archeological research generates diverse data types — excavation records, artifact catalogs, stratigraphic profiles, radiocarbon dates, geospatial surveys, and thousands of photographs. Managing this data requires specialized platforms that understand the unique demands of heritage science: hierarchical relationships between finds and contexts, controlled vocabularies, and geospatial integration.

This article compares three open-source platforms designed for archeological and cultural heritage data management: **Arches** (a geospatial heritage inventory platform), **CollectiveAccess** (a flexible cataloging system for collections), and **Heurist** (a research-oriented database for humanities data).

| Feature | Arches | CollectiveAccess | Heurist |
|---------|:------:|:----------------:|:-------:|
| Primary Use Case | Heritage inventories | Museum/collection catalogs | Humanities research data |
| Geospatial | Built-in (Leaflet/MapLibre) | Via plugin | Via integration |
| Custom Data Models | Resource Model Designer | Installation profiles | Record type builder |
| API | REST (native) | Web services API | REST API |
| Linked Data | CIDOC-CRM compliant | Dublin Core, VRA Core | Custom ontologies |
| Docker Support | ✓ (official) | ✓ (community) | ✓ (experimental) |
| Stars | 279+ | 371+ | 67+ |
| License | AGPL v3 | GPL v3 | GPL v3 |

## Arches: Geospatial Heritage Inventory Platform

Arches, developed by the Getty Conservation Institute and World Monuments Fund, is purpose-built for managing heritage inventories — archeological sites, historic buildings, cultural landscapes, and conservation areas. Its core data model is based on CIDOC-CRM, the international standard ontology for cultural heritage information.

Deploy Arches via Docker:

```yaml
version: "3.8"
services:
  arches:
    image: archesproject/arches:latest
    ports:
      - "8000:8000"
    environment:
      - ARCHES_PROJECT=my_heritage_project
      - PGUSER=arches
      - PGPASSWORD=changeme
      - PGHOST=db
      - ELASTICSEARCH_HOST=elasticsearch
    volumes:
      - arches_data:/web_root
    depends_on:
      - db
      - elasticsearch

  db:
    image: postgis/postgis:16-3.4
    environment:
      - POSTGRES_DB=arches
      - POSTGRES_USER=arches
      - POSTGRES_PASSWORD=changeme
    volumes:
      - pgdata:/var/lib/postgresql/data

  elasticsearch:
    image: elasticsearch:8.15.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    volumes:
      - esdata:/usr/share/elasticsearch/data

volumes:
  arches_data:
  pgdata:
  esdata:
```

Arches provides a powerful Resource Model Designer that lets you define custom heritage resource types — archeological sites, artifact types, conservation treatments — with drag-and-drop field configuration. Each resource includes geospatial coordinates displayed on an interactive map.

The platform includes:
- **Controlled vocabularies** via the Reference Data Manager
- **Relationship graphs** linking resources (site → excavation → find → analysis)
- **Search and discovery** with Elasticsearch-powered full-text and spatial queries
- **Time-enabled maps** for visualizing heritage resources across historical periods

## CollectiveAccess: Flexible Collection Cataloging

CollectiveAccess is a mature, battle-tested cataloging platform used by museums, archives, and research collections worldwide. While originally designed for museum collections, its flexible data model makes it suitable for archeological artifact databases, excavation archives, and field survey catalogs.

```yaml
version: "3.8"
services:
  providence:
    image: collectiveaccess/providence:latest
    ports:
      - "8080:80"
    environment:
      - CA_DB_HOST=db
      - CA_DB_USER=collectiveaccess
      - CA_DB_PASSWORD=changeme
      - CA_DB_DATABASE=collectiveaccess
    volumes:
      - ca_media:/var/www/html/media
      - ca_app:/var/www/html/app
    depends_on:
      - db

  db:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=rootpassword
      - MYSQL_DATABASE=collectiveaccess
      - MYSQL_USER=collectiveaccess
      - MYSQL_PASSWORD=changeme
    volumes:
      - mysqldata:/var/lib/mysql

volumes:
  ca_media:
  ca_app:
  mysqldata:
```

CollectiveAccess supports sophisticated data modeling through installation profiles — XML-based configuration files that define record types, fields, relationships, and user interface layouts. A typical archeological installation profile might define record types for Sites, Excavation Units, Contexts, Artifact Types, Samples, and Analysis Results.

The platform's strength lies in its cataloging workflow: batch upload with metadata extraction, authority file management, and configurable search interfaces. Its reporting engine can generate site reports, artifact catalogs, and condition assessments in multiple output formats.

## Heurist: Research Database for Humanities

Heurist, developed at the University of Sydney, takes a different approach — it's designed by researchers for researchers, prioritizing flexibility and ease of use over enterprise features. It's particularly well-suited for field projects, doctoral research, and collaborative databases where requirements evolve as the research progresses.

```bash
# Heurist installation script
wget https://github.com/HeuristNetwork/heurist/archive/refs/tags/h6.4.3.tar.gz
tar -xzf h6.4.3.tar.gz
cd heurist-h6.4.3

# Create database
mysql -u root -e "CREATE DATABASE heurist CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
mysql -u root -e "CREATE USER 'heurist'@'localhost' IDENTIFIED BY 'changeme'"
mysql -u root -e "GRANT ALL PRIVILEGES ON heurist.* TO 'heurist'@'localhost'"

# Configure and launch setup
cp hclient/registered/credentials_example.php hclient/registered/credentials.php
# Edit credentials.php with your database settings
# Open https://your-server/Heurist/setup in browser
```

Heurist's interactive record type builder lets you define data structures directly in the web interface — no coding required. Records can be linked through relationship types, geotagged, and annotated with multimedia attachments. The platform includes built-in visualization tools for timelines, maps, and network graphs.

## Choosing the Right Heritage Data Platform

- **Choose Arches** for heritage inventories with a strong geospatial component. If you're documenting archeological sites, historic buildings, or cultural landscapes, Arches' CIDOC-CRM compliance and integrated mapping make it the natural choice.
- **Choose CollectiveAccess** for comprehensive artifact and collection cataloging. Its mature metadata management, batch processing, and reporting tools are ideal for museum collections, excavation archives, and research collection catalogs.
- **Choose Heurist** for research projects that need rapid, flexible database creation. Its researcher-friendly interface and low setup overhead make it ideal for field projects, dissertations, and collaborative humanities databases.

## Why Self-Host Cultural Heritage Data?

Heritage data often spans decades or centuries of research. Commercial cloud platforms can disappear, change pricing, or alter their data models — threatening the continuity of long-term research programs. Self-hosted platforms ensure your archeological records remain under your control, in standard formats, indefinitely.

Open-source heritage platforms also facilitate data sharing and collaboration. By deploying an Arches instance with public read access, you can share your site inventory with the global research community while maintaining editorial control. For complementary collection management approaches, see our [museum archive collection management guide](../2026-06-08-self-hosted-museum-archive-collection-management-collectionspace-atom-archivesspace/). For digital library and collection platforms, check our [library digital collection comparison](../2026-05-02-koha-vs-omeka-vs-invenio-self-hosted-library-digital-collection-guide/). And for long-term digital preservation, see our [digital archive guide](../2026-04-23-archivematica-vs-omeka-s-vs-dspace-self-hosted-digital-archive-guide-2026/).

## Data Modeling and Interoperability Considerations

Effective archeological data management requires thoughtful data modeling from the start. Unlike general-purpose databases where you can iterate on schema design, heritage databases accumulate data over decades — and migrating thousands of records because of an early modeling mistake is expensive and error-prone.

Arches enforces data quality through its CIDOC-CRM compliance, which means every resource, relationship, and attribute is explicitly typed. This is powerful but requires upfront planning: define your resource models, controlled vocabularies, and relationship graphs before importing data. The Resource Model Designer provides a visual interface for this, but you should prototype your model with a small subset of records and verify that search, reporting, and export workflows produce the expected results before committing to large-scale data entry.

CollectiveAccess offers more flexibility through installation profiles, but this flexibility comes with responsibility. Develop your installation profile iteratively, starting with a minimal set of record types and fields, then expanding as data entry reveals gaps. The platform's ability to handle complex relationships (hierarchies, part-whole, temporal sequencing) is particularly useful for excavation databases where artifact → context → stratigraphic unit → site hierarchies are essential.

For projects that span multiple institutions, data interoperability becomes critical. Arches' native CIDOC-CRM compliance means data exported from one Arches instance can be imported into another with minimal mapping. CollectiveAccess supports multiple metadata standards (Dublin Core, VRA Core, Darwin Core) through its export profiles. Heurist's strength is its researcher-friendly data entry, but it requires more effort to export data in standard interchange formats — plan your data dictionary and export mappings early.

Long-term data preservation should be a consideration from day one. All three platforms store primary data in relational databases (PostgreSQL or MySQL), which ensures decades of accessibility. However, the relationships, controlled vocabularies, and metadata structures may not survive platform migrations without careful planning. Export your data regularly in both platform-native format (for operational continuity) and standard interchange formats (CIDOC-CRM XML for Arches, Dublin Core XML for CollectiveAccess) for long-term preservation independent of the platform. For complementary digital preservation strategies, see our [digital archive preservation guide](../2026-04-23-archivematica-vs-omeka-s-vs-dspace-self-hosted-digital-archive-guide-2026/).


## FAQ

### What is CIDOC-CRM and why does it matter?

CIDOC-CRM (Conceptual Reference Model) is an ISO standard (ISO 21127) that defines an ontology for cultural heritage information. It provides a formal, machine-readable framework for describing heritage entities (sites, objects, events, actors) and their relationships. Arches uses CIDOC-CRM as its core data model, which means data exported from Arches can be shared with any other CIDOC-CRM-compatible system without loss of meaning.

### Can I import existing archeological databases into these platforms?

Yes, all three support data import. Arches provides CSV import via its command-line tools and REST API. CollectiveAccess includes a comprehensive data importer supporting CSV, XML, MARC, and Excel formats with field mapping. Heurist supports CSV import with configurable field mapping through its web interface.

### Are these platforms suitable for community or citizen science projects?

Absolutely. Arches for HERs (Historic Environment Records) is specifically designed for community heritage recording. CollectiveAccess has been used for community archive projects. Heurist's low barrier to entry makes it particularly suitable for citizen science and community-led research where technical skills may be limited.

### How do these platforms handle multilingual metadata?

Arches supports multilingual content natively — each text field can have translations in multiple languages. CollectiveAccess has built-in multilingual support for catalog records and controlled vocabularies. Heurist supports multiple languages through configurable field settings.

### What's the hardware requirement for an archeological data platform?

A basic deployment (small excavation project, <50,000 records) runs comfortably on 2 vCPUs, 4GB RAM, and 50GB storage. Arches requires more resources due to Elasticsearch — plan for 4 vCPUs and 8GB RAM for production use. All three benefit from SSD storage for database performance, especially when handling geospatial queries on large datasets.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Archeological Data Management: Arches vs CollectiveAccess vs Heurist",
  "description": "Compare Arches, CollectiveAccess, and Heurist for self-hosting archeological and cultural heritage data platforms. Includes Docker Compose setups, CIDOC-CRM compliance, and geospatial integration.",
  "datePublished": "2026-06-12",
  "dateModified": "2026-06-12",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
