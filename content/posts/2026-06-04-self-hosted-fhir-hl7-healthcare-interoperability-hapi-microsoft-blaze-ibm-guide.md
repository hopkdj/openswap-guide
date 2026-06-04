---
title: "Self-Hosted FHIR Healthcare Interoperability Servers: HAPI FHIR vs Microsoft FHIR vs Blaze vs IBM FHIR"
date: "2026-06-04"
tags: ["fhir", "hl7", "healthcare", "interoperability", "self-hosted", "open-source", "medical-api"]
draft: false
---

## Introduction

Healthcare data is notoriously fragmented. A single patient's medical history might be scattered across a dozen different systems — each hospital's EHR, the pharmacy's dispensing system, the lab's results portal, and the insurance company's claims processor. **FHIR (Fast Healthcare Interoperability Resources)**, developed by HL7 International, is the modern standard designed to solve this problem. It provides a RESTful API for healthcare data exchange, enabling different systems to share patient records, lab results, medications, and clinical observations using standard JSON formats.

While cloud FHIR services from Google, AWS, and Microsoft exist, many healthcare organizations — especially those bound by data residency laws or strict privacy requirements — prefer to self-host their FHIR infrastructure. In this guide, we compare four leading open-source FHIR servers: **HAPI FHIR**, **Microsoft FHIR Server**, **Blaze**, and **IBM FHIR Server**.

## Comparison Table

| Feature | HAPI FHIR | Microsoft FHIR | Blaze | IBM FHIR |
|---------|-----------|----------------|-------|----------|
| **GitHub Stars** | 2,332+ | 1,358+ | 219+ | 370+ |
| **Primary Language** | Java | C# (.NET) | Clojure/JVM | Java |
| **License** | Apache 2.0 | MIT | Apache 2.0 | Apache 2.0 |
| **FHIR Version** | R4, R4B, R5 | R4 | R4 | R4 |
| **Database Backend** | Any JPA (PostgreSQL, MySQL, etc.) | SQL Server / PostgreSQL / CosmosDB | RocksDB (embedded) | PostgreSQL / Derby |
| **FHIR Operations** | Full CRUD, $everything, $validate | Full CRUD, $export, $reindex | Full CRUD, $evaluate-measure (CQL) | Full CRUD, $validate, $everything |
| **Subscriptions** | ✅ (R4/R5) | ✅ | ✅ | ✅ |
| **Bulk Data Export** | ✅ | ✅ (native) | ✅ | ✅ (limited) |
| **SMART on FHIR** | ✅ (plugin) | ✅ | ❌ | ❌ |
| **CQL Support** | ❌ | ❌ | ✅ (native) | ❌ |
| **Docker Support** | ✅ | ✅ | ✅ | ✅ |
| **Performance** | Good (PostgreSQL-optimized) | Excellent (production-hardened) | Excellent (embedded RocksDB) | Good |
| **Best For** | Reference implementation, extensibility | Production deployment at scale | Clinical quality measures, analytics | Enterprise Java environments |
| **Last Updated** | 2026-06-04 | 2026-06-03 | 2026-06-01 | 2024-04-18 |

## HAPI FHIR: The Reference Implementation

HAPI FHIR is the de facto reference implementation for FHIR in Java. Created by the University Health Network and now maintained by Smile CDR, it's the most widely adopted open-source FHIR server — used in production by healthcare systems worldwide.

**Key strengths:**
- Complete FHIR R4 and R5 support
- JPA-based persistence layer — works with PostgreSQL, MySQL, Oracle, MS SQL
- Extensive validation engine
- SMART on FHIR support via plugin
- Active community with commercial support available
- FHIRPath evaluation engine

**Docker Compose deployment:**

```yaml
version: "3.8"
services:
  hapi-fhir:
    image: hapiproject/hapi:latest
    ports:
      - "8080:8080"
    environment:
      - spring.datasource.url=jdbc:postgresql://db:5432/hapi
      - spring.datasource.username=hapi
      - spring.datasource.password=secure_password
      - hapi.fhir.server_address=https://fhir.example.com/fhir
      - hapi.fhir.subscription.resthook_enabled=true
    depends_on:
      - db

  db:
    image: postgres:16
    environment:
      - POSTGRES_DB=hapi
      - POSTGRES_USER=hapi
      - POSTGRES_PASSWORD=secure_password
    volumes:
      - pg_data:/var/lib/postgresql/data

volumes:
  pg_data:
```

After deployment, the FHIR endpoint is available at `https://fhir.example.com/fhir`. You can test it immediately:

```bash
# Search for all patients
curl -H "Accept: application/fhir+json"   https://fhir.example.com/fhir/Patient

# Create a new patient
curl -X POST -H "Content-Type: application/fhir+json"   -d '{"resourceType":"Patient","name":[{"family":"Doe","given":["Jane"]}]}'   https://fhir.example.com/fhir/Patient
```

## Microsoft FHIR Server: Production-Grade Healthcare Platform

Microsoft's FHIR Server is a .NET-based implementation originally built for Azure API for FHIR. It's now fully open-source and deployable anywhere — on-premises, in any cloud, or on bare metal. It powers some of the largest healthcare data exchanges in the world.

**Key strengths:**
- Battle-tested at massive scale (billions of resources)
- Native bulk data export ($export operation)
- Integrated SMART on FHIR proxy
- Comprehensive audit logging
- SQL Server, PostgreSQL, and CosmosDB backends
- Strong conformance and validation

**Docker Compose deployment:**

```yaml
version: "3.8"
services:
  fhir-server:
    image: mcr.microsoft.com/healthcareapis/r4-fhir-server:latest
    ports:
      - "8080:8080"
    environment:
      - FHIRServer__Security__Enabled=false
      - SqlServer__ConnectionString=Server=db;Database=FHIR;User Id=sa;Password=SecurePass123!;TrustServerCertificate=true
      - FHIRServer__Features__SupportsUI=false
    depends_on:
      - db

  db:
    image: mcr.microsoft.com/mssql/server:2022-latest
    environment:
      - ACCEPT_EULA=Y
      - MSSQL_SA_PASSWORD=SecurePass123!
    volumes:
      - mssql_data:/var/opt/mssql

volumes:
  mssql_data:
```

For PostgreSQL instead of SQL Server, use the `mcr.microsoft.com/healthcareapis/r4-fhir-server:latest` image with the appropriate connection string.

## Blaze: Clinical Quality & Analytics FHIR Server

Blaze is a unique FHIR server written in Clojure that focuses on clinical quality measures (CQM) and analytics. It uses RocksDB as its embedded storage engine, giving it exceptional read performance — ideal for analytics workloads where you're querying across millions of resources.

**Key strengths:**
- Native CQL (Clinical Quality Language) evaluation engine
- RocksDB storage — no external database required, extremely fast reads
- Designed for analytics and quality measure calculation
- Low operational complexity (single binary, embedded DB)
- Excellent for population health analytics

**Docker Compose deployment:**

```yaml
version: "3.8"
services:
  blaze:
    image: samply/blaze:latest
    ports:
      - "8080:8080"
    environment:
      - JAVA_TOOL_OPTIONS=-Xmx4g
      - DB_DIR=/app/data
      - ENFORCE_REFERENTIAL_INTEGRITY=false
    volumes:
      - blaze_data:/app/data

volumes:
  blaze_data:
```

Blaze's embedded storage means there's no separate database container — reducing operational complexity significantly. This makes it an excellent choice for analytics deployments where you want a turnkey FHIR store without managing PostgreSQL.

## IBM FHIR Server: Enterprise Java FHIR Platform

The IBM FHIR Server (part of the LinuxForHealth project) is a modular, extensible FHIR implementation designed for enterprise Java environments. It focuses on compliance, auditability, and integration with existing healthcare infrastructure.

**Key strengths:**
- Modular architecture — plug in custom persistence, authentication, and terminology services
- Comprehensive audit logging
- Strong FHIR validation
- IBM Db2 and PostgreSQL support
- Enterprise-grade security features

**Docker Compose deployment:**

```yaml
version: "3.8"
services:
  ibm-fhir:
    image: ibmcom/ibm-fhir-server:latest
    ports:
      - "9443:9443"
    environment:
      - FHIR_DB_HOST=db
      - FHIR_DB_PORT=5432
      - FHIR_DB_NAME=fhirdb
      - FHIR_DB_USER=fhir
      - FHIR_DB_PASSWORD=secure_password
      - BOOTSTRAP_DB=true
    depends_on:
      - db

  db:
    image: postgres:16
    environment:
      - POSTGRES_DB=fhirdb
      - POSTGRES_USER=fhir
      - POSTGRES_PASSWORD=secure_password
    volumes:
      - pg_data:/var/lib/postgresql/data

volumes:
  pg_data:
```

## Choosing the Right FHIR Server for Your Use Case

| Use Case | Recommended Server | Why |
|----------|-------------------|-----|
| **Learning/Development** | HAPI FHIR | Best documentation, largest community |
| **Production EHR Integration** | Microsoft FHIR | Battle-tested at scale, SMART on FHIR built-in |
| **Clinical Quality Measures** | Blaze | Native CQL evaluation, fast analytics queries |
| **Enterprise Healthcare** | IBM FHIR | Modular architecture, comprehensive auditing |
| **Research/Analytics** | Blaze + HAPI FHIR | Blaze for analytics queries, HAPI for transactional workloads |
| **Multi-Tenant SaaS** | Microsoft FHIR | Built-in multi-tenancy support |

## Why Self-Host Your FHIR Infrastructure?

Healthcare data is subject to some of the strictest privacy regulations in the world — HIPAA in the United States, GDPR in Europe, and similar laws in dozens of other countries. Self-hosting your FHIR server gives you complete control over where patient data is stored and processed, which is essential for meeting data residency requirements.

Beyond compliance, self-hosting enables deep integration with your existing healthcare systems. When your FHIR server runs on your network, you can connect it directly to your EHR, lab systems, and pharmacy databases without exposing sensitive data to the public internet. This is particularly important for the healthcare data migration scenarios covered in our [database migration tools guide](../2026-06-04-database-migration-tools-pgloader-ora2pg-pgchameleon-guide/).

For organizations already running self-hosted EHR systems, adding a FHIR server creates an interoperability layer that future-proofs your healthcare IT stack. See our [medical EMR/EHR deployment guide](../2026-06-04-self-hosted-medical-emr-ehr-openemr-openmrs-ehrbase-guide/) for integrating FHIR APIs with OpenEMR, OpenMRS, and EHRbase. If you need to manage database schema changes across your healthcare systems, our [database migration tools comparison](../self-hosted-test-data-management-faker-greenmask-mock-data-guide-2026/) provides guidance on deploying Flyway, Bytebase, and Liquibase for healthcare data pipelines.

## FAQ

### What is FHIR and how is it different from HL7 v2?

**HL7 v2** is the legacy healthcare messaging standard — it uses pipe-delimited text messages sent over TCP/MLLP. It's still widely used for ADT (admit/discharge/transfer) and lab orders within hospitals. **FHIR** is the modern replacement — it uses RESTful APIs with JSON/XML payloads over HTTPS. FHIR is significantly easier to integrate with web applications and mobile apps. Most modern healthcare integrations target FHIR, though most hospitals still run HL7 v2 internally and use integration engines to bridge the gap.

### Do I need both a FHIR server and an EHR?

The FHIR server stores and serves healthcare data in a standardized format. The EHR (Electronic Health Record) is the clinical application that doctors and nurses use. A typical setup pairs an EHR (which manages clinical workflows) with a FHIR server (which exposes the data for integration). For example, you might run OpenEMR as your EHR and HAPI FHIR as your interoperability layer.

### How much data can these FHIR servers handle?

**HAPI FHIR** with PostgreSQL scales to hundreds of millions of resources with proper indexing — adequate for regional healthcare exchanges. **Microsoft FHIR Server** handles billions of resources in production (it powers Azure API for FHIR). **Blaze** excels at read-heavy analytics workloads on datasets up to a few hundred million resources. **IBM FHIR Server** is designed for enterprise deployments with similar scaling characteristics to HAPI FHIR.

### What's the SMART on FHIR framework?

SMART (Substitutable Medical Applications, Reusable Technologies) on FHIR is an authorization and application launch framework built on top of FHIR. It uses OAuth 2.0 and OpenID Connect to allow third-party apps to access FHIR data with patient consent. If you plan to support third-party health apps connecting to your FHIR server, SMART on FHIR support is essential. HAPI FHIR and Microsoft FHIR Server both support it.

### Can I run multiple FHIR servers for different purposes?

Yes, and this is a common pattern. Many organizations run **HAPI FHIR** as their primary transactional FHIR server (handling CRUD operations and subscriptions) and **Blaze** as an analytics-optimized replica (for population health queries and CQL measure calculation). You can replicate data between them using FHIR subscriptions or bulk data export.

### Is the IBM FHIR Server still actively maintained?

The IBM FHIR Server became part of the LinuxForHealth project in 2021. While its last GitHub repository update was in April 2024, the project remains functional and is used in several enterprise healthcare deployments. For new deployments, HAPI FHIR or Microsoft FHIR Server are generally recommended due to more active development communities.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted FHIR Healthcare Interoperability Servers: HAPI FHIR vs Microsoft FHIR vs Blaze vs IBM FHIR",
  "description": "Comprehensive comparison of open-source FHIR servers for self-hosted healthcare interoperability — HAPI FHIR, Microsoft FHIR Server, Blaze, and IBM FHIR with Docker Compose deployment guides.",
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
