---
title: "Self-Hosted Geospatial Catalog Servers: pygeoapi vs pycsw vs GeoNetwork"
date: "2026-06-09"
tags: ["geospatial", "gis", "metadata", "ogc", "catalog", "open-data", "spatial-data"]
draft: false
---

## Introduction

Geospatial data catalogs are the backbone of modern spatial data infrastructure (SDI). They enable organizations to discover, describe, and access geographic datasets — from satellite imagery and vector maps to sensor observations and 3D city models. Whether you're building a municipal open data portal, managing an environmental monitoring network, or curating a research data repository, a self-hosted geospatial catalog server ensures your spatial assets are discoverable and interoperable.

In this guide, we compare three leading open-source geospatial catalog platforms: **pygeoapi**, **pycsw**, and **GeoNetwork**. Each implements OGC (Open Geospatial Consortium) standards but takes a different architectural approach to serving geospatial metadata.

## Comparison Table

| Feature | pygeoapi | pycsw | GeoNetwork |
|---------|----------|-------|------------|
| **Primary Role** | OGC API server | CSW metadata catalog | Full geospatial catalog |
| **GitHub Stars** | 519 | 171 | 407 |
| **Language** | Python | Python | Java |
| **OGC Standards** | OGC API, WFS3, STAC | CSW 2.0.2/3.0, OAI-PMH | CSW, OGC API Records, WMS, WFS |
| **Metadata Standards** | STAC, OGC API Records | ISO 19115/19139, Dublin Core, FGDC | ISO 19115/19139, Dublin Core, FGDC |
| **Web UI** | OpenAPI/Swagger UI | No built-in UI | Full admin + search UI |
| **Database Backend** | Elasticsearch, PostgreSQL | SQLAlchemy (any RDBMS) | PostgreSQL, H2 |
| **Harvesting** | Via plugins | CSW harvesting | CSW, OAI-PMH, WFS, Z39.50 |
| **Docker Support** | Official image | Manual setup | Official + community images |
| **License** | MIT | MIT | GPLv2 |

## pygeoapi: The Modern OGC API Server

pygeoapi is a Python-based OGC API server that implements the next generation of OGC standards — moving from the traditional SOAP/XML-based services (WMS, WFS, CSW) to modern RESTful JSON APIs. It serves geospatial data through OpenAPI-documented endpoints, making it accessible to web developers without specialized GIS knowledge.

### Docker Deployment

```yaml
version: '3.8'
services:
  pygeoapi:
    image: geopython/pygeoapi:latest
    container_name: pygeoapi
    ports:
      - "5000:80"
    environment:
      - PYGEOAPI_CONFIG=/pygeoapi/local.config.yml
      - PYGEOAPI_OPENAPI=/pygeoapi/local.openapi.yml
    volumes:
      - ./pygeoapi-config.yml:/pygeoapi/local.config.yml
      - ./data:/data
    restart: unless-stopped
```

### Configuration Example

pygeoapi uses YAML configuration to define data providers:

```yaml
server:
  bind:
    host: 0.0.0.0
    port: 80
  url: http://localhost:5000

resources:
  buildings:
    type: collection
    title: Building Footprints
    description: City building footprint dataset
    keywords: [buildings, cadastre, urban]
    extents:
      spatial:
        bbox: [-180,-90,180,90]
        crs: http://www.opengis.net/def/crs/OGC/1.3/CRS84
    providers:
      - type: feature
        name: GeoJSON
        data: /data/buildings.geojson
        id_field: id
```

pygeoapi's strength is its modern architecture. It natively supports OGC API Features (replacing WFS), OGC API Records (replacing CSW), and STAC (SpatioTemporal Asset Catalog) for Earth observation data. The built-in OpenAPI documentation means every endpoint is self-describing, and the Python plugin system allows custom data providers for any backend.

## pycsw: The Lightweight CSW Specialist

pycsw is a minimalist, standards-compliant OGC CSW (Catalog Service for the Web) server written in Python. It focuses on doing one thing exceptionally well — serving geospatial metadata through the CSW 2.0.2 and 3.0 protocols — without the overhead of a full-featured catalog application.

### Docker Deployment

```yaml
version: '3.8'
services:
  pycsw:
    image: geopython/pycsw:latest
    container_name: pycsw
    ports:
      - "8000:80"
    environment:
      - PYC SW_CONFIG=/etc/pycsw/pycsw.cfg
      - PYC SW_DATABASE_URL=postgresql://pycsw:pycsw@db:5432/pycsw
    volumes:
      - ./pycsw.cfg:/etc/pycsw/pycsw.cfg
    depends_on:
      - pycsw-db
    restart: unless-stopped

  pycsw-db:
    image: postgis/postgis:15-3.3
    container_name: pycsw-db
    environment:
      POSTGRES_USER: pycsw
      POSTGRES_PASSWORD: pycsw
      POSTGRES_DB: pycsw
    volumes:
      - ./pgdata:/var/lib/postgresql/data
    restart: unless-stopped
```

pycsw is the reference implementation for OGC CSW and passes the OGC compliance test suite. It supports all major metadata standards — ISO 19115/19139, Dublin Core, and FGDC — and provides CSW harvesting for aggregating metadata from other catalogs.

Its lightweight design means it can run on minimal resources (512MB RAM is sufficient for most deployments) while handling thousands of metadata records. For organizations that only need standards-compliant metadata discovery without a heavy web UI, pycsw is the ideal choice.

## GeoNetwork: The Full-Featured Spatial Data Catalog

GeoNetwork is the most mature and feature-rich open-source geospatial catalog. Developed by the UN Food and Agriculture Organization (FAO), it has been deployed by national mapping agencies, environmental ministries, and research institutions worldwide for over two decades.

### Docker Deployment

```yaml
version: '3.8'
services:
  geonetwork:
    image: geonetwork:4.4
    container_name: geonetwork
    ports:
      - "8080:8080"
    environment:
      - JAVA_OPTS=-Xms1g -Xmx2g
      - ES_HOST=elasticsearch
      - DATA_DIR=/var/lib/geonetwork_data
    volumes:
      - ./gn_data:/var/lib/geonetwork_data
    depends_on:
      - geonetwork-db
      - elasticsearch
    restart: unless-stopped

  geonetwork-db:
    image: postgis/postgis:15-3.3
    container_name: geonetwork-db
    environment:
      POSTGRES_USER: geonetwork
      POSTGRES_PASSWORD: geonetwork
      POSTGRES_DB: geonetwork
    volumes:
      - ./gn_pgdata:/var/lib/postgresql/data
    restart: unless-stopped

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    container_name: geonetwork-es
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    volumes:
      - ./esdata:/usr/share/elasticsearch/data
    restart: unless-stopped
```

GeoNetwork provides a comprehensive web interface for metadata editing, validation, and searching. It includes a map viewer for spatial extent visualization, user/group management with fine-grained permissions, and powerful harvesting capabilities that can pull metadata from CSW, OAI-PMH, WFS, Z39.50, and even WebDAV sources.

The built-in metadata editor supports complex ISO 19139 templates with validation, making it suitable for organizations that need to produce standards-compliant metadata for INSPIRE (European SDI) or similar regulatory frameworks. GeoNetwork also includes a schema plugin system that allows custom metadata profiles.

## Choosing the Right Geospatial Catalog

Your choice depends on your organization's scale and requirements. **pygeoapi** is ideal for modern deployments that want to embrace OGC API standards and serve data directly through RESTful JSON endpoints. It's the best fit if you're building a new spatial data infrastructure from scratch with web-native technologies.

**pycsw** excels when you need a lightweight, standards-compliant CSW endpoint that "just works." It's perfect as a metadata aggregation node in a federated catalog network, or as a backend for custom catalog applications where you want maximum control over the frontend.

**GeoNetwork** is the choice for organizations that need a complete, turnkey catalog solution — especially those subject to regulatory metadata requirements (INSPIRE, ISO 19115). Its mature web interface, harvesting capabilities, and metadata editing tools make it the go-to for national and regional SDI deployments.

## Why Self-Host Your Geospatial Catalog?

Geospatial data is often sensitive — precise locations of critical infrastructure, environmental monitoring data, and cadastral information have legal and security implications. Self-hosting ensures this data never leaves your control and can be governed by your organization's data policies.

Open standards compliance (OGC) means your self-hosted catalog can interoperate with national and international SDI networks while maintaining autonomy. When government agencies require CSW endpoints for data sharing mandates, a self-hosted pycsw or GeoNetwork instance satisfies these requirements without exposing data to third-party cloud services.


Open source geospatial catalogs have powered national spatial data infrastructures for over two decades, proving their reliability at scale. From the European INSPIRE geoportal to the UN's Food and Agriculture spatial data infrastructure, these tools have demonstrated that self-hosted open-source solutions can meet the most demanding governmental and scientific requirements.
For environmental monitoring and research organizations, self-hosting enables long-term data preservation independent of vendor roadmaps. GeoNetwork deployments at institutions like the FAO and national geological surveys demonstrate that open-source catalogs can manage millions of metadata records reliably. For related data infrastructure, see our [open data portal comparison](../2026-06-08-open-data-portals-ckan-vs-dkan-vs-dataverse/). If you're working with spatial analysis pipelines, our [scientific simulation guide](../2026-06-08-self-hosted-scientific-simulation-openfoam-elmer-calculix/) covers complementary HPC workflows.

## FAQ

### Can GeoNetwork handle millions of metadata records?

Yes, GeoNetwork has been deployed at national scales with millions of records. The Elasticsearch backend provides fast full-text search across large catalogs, and PostgreSQL with PostGIS handles spatial queries efficiently. For deployments exceeding 5 million records, allocate 8GB+ RAM and use SSD storage for Elasticsearch indices.

### Does pygeoapi replace GeoServer or MapServer?

pygeoapi complements rather than replaces map servers. While pygeoapi serves vector data through OGC API Features and raster metadata through STAC, it doesn't render map tiles or handle complex spatial analysis. Run pygeoapi alongside GeoServer or MapServer — pygeoapi for modern RESTful data APIs, the map server for WMS/WMTS visualization.

### How does pycsw compare to CKAN for geospatial metadata?

CKAN is a general-purpose data portal with geospatial extensions, while pycsw is purpose-built for OGC CSW metadata exchange. If you need a full data portal with dataset pages, user dashboards, and API management, CKAN is the better choice. If you need a standards-compliant CSW endpoint that can be harvested by national SDI networks, pycsw is the right tool.

### Can I migrate from GeoNetwork 3.x to 4.x with existing metadata?

Yes, GeoNetwork 4 provides migration tools for upgrading from 3.x deployments. The upgrade path preserves all metadata records, user accounts, and harvesting configurations. Back up your database and data directory before migration, and test the upgrade on a staging instance first.

### Which tool works best with QGIS and other desktop GIS?

All three work well with QGIS. GeoNetwork has native QGIS integration via the MetaSearch plugin for CSW discovery. pygeoapi's OGC API endpoints are directly consumable by QGIS 3.22+. pycsw can be queried from QGIS via the CSW protocol in the MetaSearch plugin. For day-to-day desktop GIS use, any of the three will provide seamless metadata discovery.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Geospatial Catalog Servers: pygeoapi vs pycsw vs GeoNetwork",
  "description": "A comprehensive comparison of open-source geospatial metadata catalog servers — pygeoapi, pycsw, and GeoNetwork — covering OGC standards, deployment, and self-hosted spatial data infrastructure for government, research, and enterprise.",
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
      "url": "https://hopkdj.github.io/openswap-guide/logo.png"
    }
  }
}
</script>
