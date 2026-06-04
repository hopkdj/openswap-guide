---
title: "Self-Hosted DICOM/PACS Medical Imaging Servers: Orthanc vs dcm4che vs OHIF Viewer vs Dicoogle"
date: "2026-06-04"
tags: ["dicom", "pacs", "medical-imaging", "healthcare", "self-hosted", "open-source", "radiology"]
draft: false
---

## Introduction

Medical imaging is one of the most data-intensive domains in healthcare. A single MRI study can generate hundreds of megabytes, and a busy radiology department produces terabytes of imaging data annually. Managing, storing, and viewing this data requires specialized software that complies with the **DICOM (Digital Imaging and Communications in Medicine)** standard and provides **PACS (Picture Archiving and Communication System)** functionality.

While commercial PACS solutions from vendors like GE, Siemens, and Philips dominate hospital environments, a growing number of open-source alternatives offer robust DICOM capabilities for clinics, research labs, veterinary practices, and teleradiology startups. These self-hosted solutions give you full control over patient data, eliminate per-study licensing fees, and can be deployed on your own infrastructure.

In this guide, we compare four leading open-source DICOM/PACS platforms: **Orthanc**, **dcm4che**, **OHIF Viewer**, and **Dicoogle**. Each serves a different niche in the medical imaging pipeline — from lightweight DICOM servers to zero-footprint web viewers and research-oriented PACS archives.

## Comparison Table

| Feature | Orthanc | dcm4che | OHIF Viewer | Dicoogle |
|---------|---------|---------|-------------|----------|
| **GitHub Stars** | 89+ | 488+ | 4,192+ | 520+ |
| **Primary Language** | C++ | Java | TypeScript | Java |
| **License** | GPLv3 | MPL 2.0 | MIT | GPLv3 |
| **DICOM Server** | ✅ (lightweight) | ✅ (enterprise) | ❌ (viewer only) | ✅ (PACS) |
| **Web Viewer** | ✅ (built-in) | ✅ (via Weasis) | ✅ (primary feature) | ✅ (built-in) |
| **DICOMweb** | ✅ (plugin) | ✅ (native) | ✅ (native) | ✅ (native) |
| **HL7/FHIR** | ❌ | ✅ | ❌ | ❌ |
| **REST API** | ✅ | ✅ | ✅ | ✅ |
| **Docker Support** | ✅ | ✅ | ✅ | ✅ |
| **Database Backend** | SQLite/PostgreSQL | PostgreSQL/Oracle | N/A | MongoDB/Elasticsearch |
| **Multi-Tenancy** | ❌ | ✅ | N/A | ✅ |
| **Best For** | Small clinics, research | Enterprise hospitals | Viewing & annotation | Research, indexing |
| **Last Updated** | 2020 (core) / 2026 (Docker) | 2026-06-03 | 2026-06-03 | 2026-05-18 |

## Orthanc: The Lightweight Workhorse

Orthanc is a lightweight, standalone DICOM server written in C++. Despite its small footprint, it packs a powerful REST API and a built-in web viewer, making it one of the most popular open-source DICOM solutions for small-to-medium deployments.

**Key strengths:**
- Minimal resource requirements — runs comfortably on a Raspberry Pi
- Built-in DICOMweb support via plugin
- Lua scripting for custom workflows
- PostgreSQL backend for production deployments
- Active community with plugins for authorization, auto-routing, and more

**Docker Compose deployment:**

```yaml
version: "3.8"
services:
  orthanc:
    image: jodogne/orthanc-plugins:latest
    ports:
      - "8042:8042"
      - "4242:4242"
    environment:
      - ORTHANC_JSON={"Name":"Orthanc","PostgreSQL":{"Host":"postgres","Port":5432,"Database":"orthanc","Username":"orthanc","Password":"orthanc_pwd"},"DicomWeb":{"Enable":true}}
    volumes:
      - orthanc_data:/var/lib/orthanc/db
    depends_on:
      - postgres

  postgres:
    image: postgres:16
    environment:
      - POSTGRES_DB=orthanc
      - POSTGRES_USER=orthanc
      - POSTGRES_PASSWORD=orthanc_pwd
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  orthanc_data:
  postgres_data:
```

## dcm4che: Enterprise-Grade DICOM Archive

dcm4che (pronounced "dcm-for-che") is a comprehensive, Java-based DICOM toolkit and archive server. The `dcm4chee-arc-light` project provides a full-featured PACS archive with DICOMweb, HL7/FHIR integration, and enterprise-grade scalability.

**Key strengths:**
- Native DICOMweb support (QIDO-RS, WADO-RS, STOW-RS)
- HL7 v2 and FHIR integration for hospital workflows
- LDAP/OpenID Connect authentication
- Clustering for high availability
- IHE-compliant workflows

**Docker Compose deployment:**

```yaml
version: "3.8"
services:
  dcm4chee:
    image: dcm4che/dcm4chee-arc-psql:5.31.2
    ports:
      - "8080:8080"
      - "11112:11112"
      - "2575:2575"
    environment:
      - POSTGRES_DB=dcm4chee
      - POSTGRES_USER=dcm4chee
      - POSTGRES_PASSWORD=secure_password
      - STORAGE_DIR=/storage
    volumes:
      - dcm4chee_storage:/storage
    depends_on:
      - postgres

  postgres:
    image: postgres:16
    environment:
      - POSTGRES_DB=dcm4chee
      - POSTGRES_USER=dcm4chee
      - POSTGRES_PASSWORD=secure_password
    volumes:
      - pg_data:/var/lib/postgresql/data

volumes:
  dcm4chee_storage:
  pg_data:
```

## OHIF Viewer: Zero-Footprint DICOM Viewer

OHIF (Open Health Imaging Foundation) Viewer is a web-based, zero-footprint medical image viewer. While it's not a DICOM server itself, it's the most popular open-source viewer for radiologists — it connects to any DICOMweb-compatible backend (Orthanc, dcm4che, AWS HealthImaging) and provides a rich viewing experience.

**Key strengths:**
- Zero-footprint — runs entirely in the browser
- Multiplanar reconstruction (MPR)
- Advanced measurement tools
- DICOM SR (Structured Reports) support
- Extensible via custom extensions
- Oncology-specific Lesion Tracker

**Docker Compose deployment (with Orthanc backend):**

```yaml
version: "3.8"
services:
  ohif:
    image: ohif/viewer:latest
    ports:
      - "3000:80"
    environment:
      - APP_CONFIG={"servers":{"dicomWeb":[{"name":"Orthanc","wadoUriRoot":"http://orthanc:8042/wado","qidoRoot":"http://orthanc:8042/dicom-web","wadoRoot":"http://orthanc:8042/dicom-web","qidoSupportsIncludeField":false,"imageRendering":"wadors","thumbnailRendering":"wadors"}]}}

  orthanc:
    image: jodogne/orthanc-plugins:latest
    ports:
      - "8042:8042"
    environment:
      - ORTHANC_JSON={"DicomWeb":{"Enable":true}}
```

## Dicoogle: Research-Oriented PACS

Dicoogle is an open-source PACS archive designed for research and education. It takes a unique approach — instead of a traditional relational database, it uses document-based storage (MongoDB) with an Elasticsearch-like query engine, making it excellent for indexing and searching across large DICOM datasets.

**Key strengths:**
- Document-based indexing for fast full-text search
- Plugin-based architecture for extensibility
- DICOM query/retrieve via web interface
- Designed for research datasets and teaching collections
- REST API for integration

**Docker Compose deployment:**

```yaml
version: "3.8"
services:
  dicoogle:
    image: dicoogle/dicoogle:latest
    ports:
      - "8080:8080"
      - "104:104"
      - "6666:6666"
    volumes:
      - dicoogle_data:/data
      - dicoogle_storage:/storage

volumes:
  dicoogle_data:
  dicoogle_storage:
```

## Deployment Architecture

A complete medical imaging pipeline typically combines multiple tools. A common pattern for mid-size clinics looks like this:

```
[DICOM Modalities (CT/MRI/X-Ray)] 
         │
         ▼
    [Orthanc] ── DICOM router/gateway
         │
         ├──► [dcm4che] ── PACS archive (long-term storage)
         │
         └──► [OHIF Viewer] ── Radiologist workstation (browser)
              [Dicoogle] ── Research & teaching index
```

Orthanc acts as the DICOM gateway — receiving studies from modalities, routing them to the archive, and serving them to viewers. dcm4che provides enterprise-grade storage with HL7 integration for hospital workflows. OHIF gives radiologists a modern viewing experience, and Dicoogle enables researchers to search across historical datasets.

For storage, a typical radiology department producing 50 GB of imaging per day would need approximately 18 TB annually. Using compressed DICOM and a tiered storage strategy (SSD for recent studies, HDD for archives), you can build a cost-effective PACS infrastructure on commodity hardware.

## Security Considerations

Medical imaging data is protected health information (PHI) under HIPAA and similar regulations worldwide. When self-hosting a PACS:

- **Encryption at rest**: Use LUKS or similar for storage volumes containing patient data
- **TLS everywhere**: Put a reverse proxy (Nginx or Caddy) in front of all DICOMweb endpoints
- **Access control**: Use the built-in authentication plugins in Orthanc and dcm4che with LDAP/OpenID Connect
- **Audit logging**: Enable DICOM audit logs and ship them to a centralized log server
- **Network segmentation**: Place DICOM servers on a dedicated VLAN, separate from public-facing services
- **Backup strategy**: Implement 3-2-1 backups for PACS data — on-site, off-site, and offline

## Why Self-Host Your Medical Imaging Stack?

Healthcare organizations increasingly recognize the benefits of self-hosting their imaging infrastructure. Commercial PACS contracts often lock you into proprietary formats, charge per-study fees that scale unpredictably, and make data migration prohibitively difficult.

Self-hosting with open-source tools gives you complete data sovereignty — your patient images remain on your servers, under your control. When you need to switch vendors or upgrade infrastructure, open standards like DICOM and DICOMweb ensure portability. For research institutions, open-source PACS enables custom workflows that commercial vendors simply cannot support.

Cost is another compelling factor. A commercial PACS for a mid-size clinic can cost $50,000–200,000 in annual licensing. The same functionality with Orthanc + dcm4che + OHIF on commodity hardware costs a fraction of that — primarily the server hardware and administrator time.

For clinics already using self-hosted electronic health records, adding open-source PACS creates a fully self-sovereign healthcare IT stack. See our [medical EMR/EHR guide](../2026-06-04-self-hosted-medical-emr-ehr-openemr-openmrs-ehrbase-guide/) for integrating with patient record systems. If you need to migrate existing imaging data between systems, our [database migration tools comparison](../2026-06-04-database-migration-tools-pgloader-ora2pg-pgchameleon-guide/) covers the tools you'll need for converting metadata stores.

## FAQ

### What's the difference between DICOM and PACS?

**DICOM** is the standard file format and network protocol for medical imaging. It defines how images, metadata, and reports are encoded and transmitted. **PACS** (Picture Archiving and Communication System) is the complete system that stores, retrieves, distributes, and displays DICOM images. Think of DICOM as JPEG+HTTP for medical images, and PACS as the full photo management application.

### Can I run a PACS on a single server for a small clinic?

Yes. Orthanc with SQLite runs comfortably on a server with 4 GB RAM and a dual-core CPU for up to 10 concurrent users. For production, swap SQLite for PostgreSQL and add 8+ GB RAM. A typical small clinic generating 5–10 GB of imaging per day can run on a single server with sufficient storage for 2–3 years of data.

### Do I need a DICOM viewer if my PACS has a built-in one?

Orthanc and dcm4che both include basic web viewers, but they lack the advanced features that radiologists need — MPR (multiplanar reconstruction), hanging protocols, measurement tools, and structured reporting. OHIF Viewer fills this gap with a professional-grade viewing experience. For clinical use, always pair your PACS with a proper diagnostic viewer.

### How do these tools handle DICOM Modality Worklist (MWL)?

Orthanc supports MWL via its worklist plugin. dcm4che provides native MWL with HL7 integration for hospital scheduling systems. OHIF Viewer and Dicoogle are viewer/indexing tools and don't handle MWL directly. If you need full modality workflow management, pair Orthanc or dcm4che with an HL7 broker.

### Is DICOMweb important for modern deployments?

**Yes.** DICOMweb is the modern RESTful API for DICOM — it uses standard HTTP methods (GET/POST) with JSON metadata, making it much easier to integrate with web applications than traditional DICOM C-STORE/C-FIND protocols. All four tools in this comparison support DICOMweb to varying degrees. If you plan to build custom viewers or integrate with web platforms, DICOMweb support is essential.

### What storage backend should I use for a production PACS?

For Orthanc: PostgreSQL with filesystem storage. For dcm4che: PostgreSQL with JBoss Data Grid. For Dicoogle: MongoDB for metadata indexing. Plan your storage tiering — use fast NVMe SSDs for recent studies (last 30 days) and HDD arrays or object storage (MinIO/Ceph) for archives. Expect 2–3x compression on typical DICOM datasets with lossless compression enabled.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DICOM/PACS Medical Imaging Servers: Orthanc vs dcm4che vs OHIF Viewer vs Dicoogle",
  "description": "Comprehensive comparison of open-source DICOM servers and PACS solutions for self-hosted medical imaging — Orthanc, dcm4che, OHIF Viewer, and Dicoogle with Docker Compose deployment guides.",
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
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
