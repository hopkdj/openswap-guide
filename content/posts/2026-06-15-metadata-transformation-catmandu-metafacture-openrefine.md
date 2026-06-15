---
title: "Self-Hosted Metadata Transformation Platforms: Catmandu vs Metafacture vs OpenRefine"
date: "2026-06-15"
tags: ["metadata", "data-transformation", "library-tools", "etl", "digital-humanities", "open-data"]
draft: false
---

## Introduction

Libraries, archives, museums, and research institutions deal with an enormous variety of metadata formats — MARC, Dublin Core, EAD, METS, MODS, JSON-LD, and dozens more. Converting between these formats, cleaning messy data, and enriching records at scale requires specialized metadata transformation platforms. Unlike generic ETL tools, metadata-focused platforms understand library-specific standards and provide domain-specific transformations.

In this guide, we compare three leading self-hosted metadata transformation platforms: **Catmandu**, **Metafacture**, and **OpenRefine**, evaluating their metadata processing capabilities, deployment options, and ideal use cases.

## Comparison Table

| Feature | Catmandu | Metafacture | OpenRefine |
|---------|----------|-------------|------------|
| **Language** | Perl | Java | Java (web app) |
| **Stars** | ~194 | ~78 | ~11,000+ |
| **Metadata focus** | Library/cultural heritage | Library metadata | General data cleaning |
| **MARC support** | Native | Via modules | Via extensions |
| **Dublin Core** | Built-in | Built-in | Manual mapping |
| **Linked Data** | RDF export | RDF/Linked Data | RDF extension |
| **Web UI** | CLI + API | CLI + API | Full web UI |
| **Docker support** | Yes | Yes | Yes |
| **Batch processing** | Yes | Yes | Via API |
| **Transform language** | Perl DSL | Flux DSL | GREL / Jython |
| **License** | Perl Artistic | Apache 2.0 | BSD |

## Catmandu: The Perl Powerhouse for Library Metadata

[Catmandu](https://github.com/LibreCat/Catmandu) is a Perl-based data processing toolkit developed specifically for library and cultural heritage metadata. Created by the LibreCat project at Ghent University, Catmandu provides a comprehensive DSL for importing, transforming, storing, and exporting bibliographic records.

### Key Features

- **Native library format support**: MARC, MODS, Dublin Core, RDF, JSON-LD, XML, CSV, YAML, and many more
- **Extensible plugin system**: Over 50 Catmandu modules available on CPAN for different data sources and formats
- **Fix language**: A domain-specific transformation language for mapping fields, cleaning data, and generating new values
- **Store backends**: Elasticsearch, MongoDB, CouchDB, Solr, and more for indexing and storage
- **REST API**: Catmandu can run as a web service via its `Catmandu::HTTP` module

### Docker Deployment

```yaml
version: "3"
services:
  catmandu:
    image: librecat/catmandu:latest
    container_name: catmandu
    volumes:
      - ./data:/data
      - ./fix:/fix
    command: catmandu convert MARC --fix /fix/clean_marc.fix to JSON < /data/input.mrc
```

Catmandu excels in environments where metadata transformations are scripted and automated — think nightly ETL jobs converting MARC exports to JSON-LD for search indexing, or normalizing Dublin Core metadata across institutional repositories.

## Metafacture: The Java Framework for Metadata Pipelines

[Metafacture](https://github.com/metafacture/metafacture-core) is a Java-based toolkit for metadata processing, developed by the German National Library (DNB) and the hbz library service center. It's designed for building complex, streaming metadata transformation pipelines at production scale.

### Key Features

- **Flux workflow language**: A declarative scripting language for defining metadata processing pipelines
- **Streaming architecture**: Processes records one at a time, enabling memory-efficient handling of millions of records
- **Modular design**: Separate modules for reading, transforming, and writing metadata — composable into pipelines
- **Format support**: MARC, PICA, MAB, Dublin Core, RDF, JSON, XML, CSV, and custom formats
- **Library-grade**: Developed and maintained by national libraries for production use

### Docker Deployment

```yaml
version: "3"
services:
  metafacture:
    image: metafacture/metafacture-core:latest
    container_name: metafacture
    volumes:
      - ./data:/data
      - ./flux:/flux
    command: /opt/metafacture/run.sh /flux/transform_marc_to_jsonld.flux
```

Example Flux script for MARC-to-Dublin-Core conversion:

```flux
"input.mrc"
| open-file
| as-lines
| decode-marc21
| morph("marc21-to-dublincore.xml")
| encode-xml
| write("output/");
```

Metafacture is ideal for institutions with high-volume metadata processing needs — think national library union catalogs, large-scale digital preservation pipelines, and metadata aggregation services.

## OpenRefine: The Generalist with Metadata Superpowers

[OpenRefine](https://openrefine.org/) (formerly Google Refine) is a powerful web-based tool for cleaning, transforming, and enriching messy data. While not library-specific, OpenRefine's flexibility and extensive reconciliation capabilities make it a favorite among metadata librarians and digital humanists.

### Key Features

- **Web-based UI**: Interactive exploration and transformation of tabular data with live previews
- **GREL expression language**: General Refine Expression Language for data transformations
- **Reconciliation API**: Connect to external authorities (VIAF, Wikidata, LCNAF, GeoNames) to enrich and normalize metadata
- **Faceting and clustering**: Discover data quality issues through interactive faceting and automated clustering for deduplication
- **Extensions**: MARC import/export, RDF skeleton, Named Entity Recognition, and many community extensions
- **History**: Every transformation is recorded and replayable, supporting reproducible workflows

### Docker Deployment

```yaml
version: "3"
services:
  openrefine:
    image: felixlohmeier/openrefine:latest
    container_name: openrefine
    ports:
      - "3333:3333"
    volumes:
      - ./data:/data
    environment:
      - REFINE_MEMORY=2048M
```

OpenRefine shines in interactive metadata cleanup scenarios — deduplicating author names in a union catalog, reconciling place names against GeoNames, or normalizing date formats across a heterogeneous metadata collection.

## Why Self-Host Your Metadata Transformation Tools?

Self-hosting metadata transformation tools provides several advantages for cultural heritage institutions. First, **data sovereignty**: library metadata often contains sensitive patron circulation data and institutional collection records that shouldn't leave your infrastructure. Running your own Catmandu or Metafacture instance ensures metadata never touches a third-party server.

Second, **integration flexibility**: self-hosted platforms can connect directly to your institutional ILS, repository systems, and discovery layers without API rate limits or egress fees. For instance, a nightly Metafacture pipeline can read directly from your library's MARC export, transform records to linked data, and push them to your discovery index — all within your local network.

Third, **cost predictability**: unlike SaaS alternatives that charge per record or per GB processed, self-hosted solutions scale with your hardware budget. For institutions processing millions of bibliographic records annually, the cost difference between a self-hosted Metafacture instance and a comparable SaaS product can be 10x or more.

For broader institutional data management, see our [self-hosted scientific data management guide](../2026-06-09-self-hosted-scientific-data-management-irods-rucio-datalad-guide/). If you're working with geospatial metadata specifically, check out our [self-hosted GIS raster processing comparison](../2026-06-09-self-hosted-gis-raster-processing-gdal-grass-whitebox-otb/).

## Choosing the Right Platform

- **Choose Catmandu** if you work primarily with library formats in a Perl-friendly environment and need extensive format support with a rich module ecosystem.
- **Choose Metafacture** if you process metadata at massive scale (millions of records) and need production-grade streaming pipelines backed by national library engineering.
- **Choose OpenRefine** if you need interactive, exploratory metadata cleaning with reconciliation against external authorities and prefer a visual workflow over scripting.

Many institutions combine these tools: Metafacture for high-volume ETL pipelines, Catmandu for specialized format conversions, and OpenRefine for hands-on data cleanup by metadata librarians.

## FAQ

### Can these tools handle MARC binary (.mrc) files?

Yes, all three can process MARC binary files. Catmandu and Metafacture have native MARC decoders for reading `.mrc` files directly. OpenRefine requires the MARC import extension, which parses `.mrc` files into tabular data. For large MARC files (1GB+), Metafacture's streaming architecture provides the best performance.

### How do these compare to general ETL tools like Apache NiFi or Airflow?

General ETL tools lack library-specific format support — they see MARC as opaque binary data. Catmandu and Metafacture understand MARC fields, subfields, and indicators natively. If your pipeline is mostly library metadata, these specialized tools save weeks of custom code. However, for orchestrating complex multi-system workflows that include metadata processing as one step, combining Metafacture with Airflow is a common pattern.

### Can I use these for Linked Data / RDF conversion?

Yes. Catmandu has built-in RDF exporters and can produce JSON-LD, Turtle, and RDF/XML. Metafacture supports RDF serialization through its Metamorph module. OpenRefine's RDF extension allows you to map tabular data to RDF triples using a visual interface. For full-scale linked data platforms, also see our guide on [knowledge graphs and semantic web platforms](#).

### What hardware do I need to run these?

For small to medium collections (< 1M records), any modern server with 4GB RAM is sufficient. For large-scale processing (10M+ records), Metafacture benefits from 8-16GB RAM due to its in-memory morph definitions. OpenRefine is more memory-intensive — allocate at least 2GB per concurrent user. Catmandu is the most lightweight option.

### Are there commercial support options available?

Catmandu is maintained by the LibreCat project with community support. Metafacture is backed by the German National Library and hbz, providing institutional-grade maintenance. OpenRefine has an active open-source community with contributions from Google and various universities. For commercial support, several consulting firms specialize in library metadata engineering and can provide SLAs for all three platforms.

### How do I handle non-MARC metadata formats like EAD or METS?

Catmandu has the broadest format support out of the box, with modules for EAD, METS, MODS, PICA, and more. Metafacture supports any XML-based format through its generic XML processing modules. OpenRefine can import XML data and use GREL expressions to navigate XML trees, but requires more manual work for complex hierarchical formats like EAD finding aids.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Metadata Transformation Platforms: Catmandu vs Metafacture vs OpenRefine",
  "description": "Compare Catmandu, Metafacture, and OpenRefine for self-hosted metadata transformation. Library metadata ETL, MARC processing, Dublin Core conversion, and Linked Data generation for cultural heritage institutions.",
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
