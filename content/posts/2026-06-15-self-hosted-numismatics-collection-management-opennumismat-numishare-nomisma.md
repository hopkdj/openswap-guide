---
title: "Self-Hosted Numismatics Collection Management: OpenNumismat vs Numishare vs Nomisma"
date: "2026-06-15"
tags: ["numismatics", "collection-management", "digital-humanities", "coin-collection", "cultural-heritage", "self-hosted"]
draft: false
---

## Introduction

Numismatics — the study and collection of coins, tokens, and currency — is one of the oldest collecting hobbies in the world. Whether you are managing a museum's coin collection, documenting a research catalog, or organizing a personal hobby collection, self-hosted numismatic software gives you full ownership of your data without relying on third-party cloud services.

This guide compares three open-source platforms for self-hosted numismatics collection management: **OpenNumismat**, a feature-rich desktop application with web export capabilities; **Numishare**, a web-based cultural heritage platform with numismatic extensions; and **Nomisma**, a linked open data knowledge organization system for numismatic concepts.

## Comparison Table

| Feature | OpenNumismat | Numishare | Nomisma |
|---------|-------------|-----------|---------|
| **Type** | Desktop + Web Export | Web Application | Linked Data Vocabulary |
| **Primary Use** | Personal collection cataloging | Institutional digital publication | Semantic numismatic data |
| **Web Interface** | Built-in HTTP server | Full web application | SPARQL endpoint |
| **Coin Identification** | Automatic reference matching | IIIF image annotation | Controlled vocabularies |
| **Export Formats** | CSV, HTML, PDF, Excel | RDF, JSON-LD, KML | RDF/XML, Turtle, JSON-LD |
| **Multi-User** | No (single user) | Yes | Read-only (public) |
| **Docker Support** | Yes (community) | Yes (official) | Yes |
| **License** | GPL-3.0 | MIT | CC-BY |
| **Stars** | 133 | 47 | 11 |
| **Last Updated** | May 2026 | May 2026 | April 2026 |

## OpenNumismat: The Personal Collection Workhorse

OpenNumismat is the most actively maintained self-hosted numismatic tool for personal collectors. It is a cross-platform desktop application (Windows, macOS, Linux) that provides comprehensive coin cataloging features.

### Key Features

- **Comprehensive coin fields**: Supports over 80 data fields including country, denomination, year, mint mark, grade, material, diameter, weight, and edge type
- **Automatic coin identification**: Integrated with online coin databases (Numista, Colnect) for automatic field population using image recognition
- **Built-in statistics**: Generates charts and reports showing collection distribution by country, period, metal, and denomination
- **Image management**: Attach multiple images per coin with automatic thumbnail generation
- **Web export**: Built-in HTTP server to publish your collection as a static website

### Docker Deployment

OpenNumismat is primarily a desktop application, but you can run it in a containerized environment for headless catalog management:

```yaml
# docker-compose.yml
version: '3.8'
services:
  opennumismat:
    image: opennumismat/opennumismat:latest
    container_name: opennumismat
    volumes:
      - ./data:/app/data
      - ./images:/app/images
      - ./exports:/app/exports
    ports:
      - "8080:8080"
    environment:
      - LANG=en_US.UTF-8
    restart: unless-stopped
```

After deployment, access the web interface at `http://localhost:8080` to browse your published collection.

## Numishare: Institutional-Grade Digital Numismatics

Numishare is an open-source web application suite designed by the American Numismatic Society for managing and publishing digital cultural heritage objects, with specific extensions for numismatic collections.

### Key Features

- **Linked open data**: All collection records are published as RDF triples with persistent URIs, enabling integration with the broader semantic web
- **IIIF support**: Deep zoom image viewing using the International Image Interoperability Framework (IIIF) for high-resolution coin photography
- **Geospatial visualization**: Built-in KML export and map visualization for find spots and mint locations
- **Multi-format export**: Export to NUDS (Numismatic Description Standard), XML, JSON-LD, and CSV
- **TEI/XML metadata**: Uses Text Encoding Initiative (TEI) XML for rich descriptive metadata
- **Multi-collection support**: Manage multiple numismatic collections within a single deployment

### Web Deployment

Numishare runs as a Java web application (WAR) deployable to Apache Tomcat:

```yaml
# docker-compose.yml
version: '3.8'
services:
  numishare:
    image: ewg118/numishare:latest
    container_name: numishare
    ports:
      - "8080:8080"
    volumes:
      - ./solr-data:/opt/solr/server/solr/numishare
      - ./images:/opt/numishare/images
      - ./data:/opt/numishare/data
    environment:
      - SOLR_URL=http://solr:8983/solr/numishare
      - ADMIN_EMAIL=admin@example.com
    restart: unless-stopped

  solr:
    image: solr:8.11
    container_name: numishare-solr
    volumes:
      - ./solr-data:/var/solr/data
    ports:
      - "8983:8983"
    restart: unless-stopped
```

Numishare uses Apache Solr for full-text search and IIIF image server for high-resolution coin photography. It is designed for institutional deployments with multiple curators and researchers.

## Nomisma: Semantic Knowledge Organization for Numismatics

Nomisma.org is a collaborative project that provides stable digital representations of numismatic concepts and entities according to the principles of Linked Open Data (LOD). While not a collection management system per se, it is an essential infrastructure component for serious numismatic digital projects.

### Key Features

- **Controlled vocabularies**: Standardized URIs for mints, denominations, materials, rulers, and hoards
- **SPARQL endpoint**: Query numismatic knowledge graphs programmatically
- **Integration hub**: Connects numismatic databases worldwide through shared authority files
- **RDF serialization**: Data available in RDF/XML, Turtle, N-Triples, and JSON-LD
- **Period-specific ontologies**: Specialized vocabularies for Greek, Roman, Byzantine, and Medieval numismatics
- **Geographic data**: Linked coordinates for mints and find spots using Pleiades gazetteer

### Deploying Your Own Linked Data Endpoint

You can deploy a local Nomisma-compatible SPARQL endpoint using Apache Jena Fuseki:

```yaml
# docker-compose.yml
version: '3.8'
services:
  fuseki:
    image: secoresearch/fuseki:latest
    container_name: nomisma-fuseki
    ports:
      - "3030:3030"
    volumes:
      - ./fuseki-data:/fuseki
      - ./nomisma-data:/staging
    environment:
      - ADMIN_PASSWORD=change-me
      - JVM_ARGS=-Xmx2g
    restart: unless-stopped
```

Load Nomisma RDF data into Fuseki to run local SPARQL queries against the numismatic knowledge graph.

## Why Self-Host Your Numismatic Collection?

Managing your coin collection with self-hosted tools offers several distinct advantages over commercial cloud services and proprietary desktop software.

**Data ownership and longevity** is the primary benefit. Coin collections often span decades — sometimes generations within a family. Cloud services can shut down, change pricing, or alter their terms of service. With self-hosted software, your meticulously cataloged data remains in your control in standard, open formats like CSV, JSON-LD, and RDF. Even if the software stops being maintained, your data remains accessible and migratable.

**Privacy and scholarly independence** matter for research collections. Many numismatists work with unpublished hoard data, pre-publication catalog entries, or sensitive provenance information. Self-hosted platforms ensure this data never touches third-party servers. The Numishare and Nomisma ecosystems, in particular, are designed for scholarly publication workflows where you control exactly when and how data becomes public.

**Integration flexibility** enables custom workflows. You can combine OpenNumismat's desktop cataloging with Numishare's web publishing and Nomisma's linked data authority files. This composability — running each tool in its own Docker container and connecting them through standard APIs — creates a numismatic data pipeline that no single commercial product matches.

For related self-hosted cultural heritage tools, see our [Digital Collections Platform guide](../2026-06-08-self-hosted-museum-archive-collection-management-collectionspace-atom-archivesspace/). If you work with archaeological datasets, our [Biodiversity Data Platforms comparison](../2026-06-14-self-hosted-biodiversity-data-platforms-gbif-ipt-inaturalist-pybossa/) covers related data management patterns.

## Hardware Considerations for High-Resolution Coin Imaging

Coin photography for numismatic catalogs requires specialized hardware considerations. A typical setup involves a copy stand, macro lens (90-105mm), diffuse lighting, and a color calibration target. For self-hosted workflows, consider integrating these hardware components:

- **Camera tethering**: Use gPhoto2 (Linux) or libgphoto2 to control DSLR cameras programmatically for consistent coin photography
- **Scale and color reference**: Include a millimeter scale and color checker card in every image for dimensional and color accuracy
- **Batch processing**: Tools like ImageMagick can automatically crop, resize, and watermark coin images for web publication
- **Storage planning**: High-resolution coin images (24MP+) require approximately 15-20MB per image in RAW format; plan storage accordingly

## FAQ

### Can I use OpenNumismat on a headless server?

OpenNumismat is designed as a desktop application with a graphical interface. However, the built-in HTTP server allows you to publish your collection for web browsing. For purely headless cataloging, consider using OpenNumismat's SQLite database directly with custom scripts, or use Numishare which is designed as a server application from the ground up.

### How do I migrate from a spreadsheet to a numismatic database?

Most numismatic platforms support CSV import. Export your spreadsheet as CSV, map the columns to the platform's field names, and import. OpenNumismat has a built-in import wizard that supports Excel, CSV, and XML formats. Numishare accepts CSV and XML through its admin interface. For complex migrations, intermediate transformation with Python scripts using pandas can normalize date formats, standardize mint names, and clean inconsistent data.

### What is the difference between Numishare and Nomisma?

Numishare is a **collection management and publication platform** — you use it to catalog, manage, and display your actual coin collection. Nomisma is a **knowledge organization system** — it provides standardized identifiers (URIs) for numismatic concepts like mints, rulers, and denominations. Think of Numishare as the library catalog software and Nomisma as the controlled vocabulary for subject headings. They are complementary: Numishare can reference Nomisma URIs in its metadata.

### Is there a mobile app for field cataloging?

OpenNumismat does not have a dedicated mobile app, but its web export is mobile-responsive for browsing. For field cataloging, you can use a mobile-friendly web form connected to Numishare's API, or use a general-purpose data collection app like ODK Collect to capture coin data in the field and import it later. Some collectors use a tablet with a remote desktop connection to the desktop application.

### How do I handle coin provenance and ethical collecting documentation?

All three platforms support custom metadata fields. For provenance documentation, use dedicated fields to record previous owners, auction house and lot numbers, export permits, and Cultural Property Advisory Committee (CPAC) compliance. Numishare's TEI/XML metadata support is particularly well-suited for detailed provenance narratives. Consider also linking to external databases like the Portable Antiquities Scheme (finds.org.uk) for documented find spots.

### Can I integrate my numismatic database with IIIF image servers?

Yes, Numishare has native IIIF support through integration with image servers like Cantaloupe or Loris. When coins are imaged at high resolution (300+ DPI), IIIF enables researchers to zoom into fine details like mint marks, die cracks, and wear patterns. For OpenNumismat, you can publish full-resolution images alongside the web export and reference them through IIIF manifests served by a separate image server.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Numismatics Collection Management: OpenNumismat vs Numishare vs Nomisma",
  "description": "Compare three open-source self-hosted platforms for managing numismatic coin collections. OpenNumismat for personal catalogs, Numishare for institutional digital publication, and Nomisma for linked open data numismatic knowledge organization.",
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
