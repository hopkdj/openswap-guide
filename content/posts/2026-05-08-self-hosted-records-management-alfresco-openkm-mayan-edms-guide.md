---
title: "Self-Hosted Records Management: Alfresco Records vs OpenKM vs Mayan EDMS Retention 2026"
date: 2026-05-08T12:00:00+00:00
tags: ["records-management", "document-management", "compliance", "retention", "alfresco", "openkm", "mayan-edms"]
draft: false
---

Every organization generates documents that must be retained for specific periods — tax records, contracts, employee files, audit trails, and regulatory submissions. Records management goes beyond simple document storage: it defines how long documents are kept, who can access them, when they should be archived, and when they must be securely destroyed.

This guide compares three open-source platforms for self-hosted records management: **Alfresco Records Management**, **OpenKM Records Module**, and **Mayan EDMS Retention Policies**. Each provides enterprise-grade document lifecycle management with retention schedules, hold policies, and disposition workflows — without the cost of commercial records management systems.

## Understanding Records Management vs Document Management

Document management systems (DMS) focus on creating, storing, and retrieving documents. Records management systems (RMS) add compliance and governance layers:

- **Retention schedules** — automatically classify documents and apply retention periods
- **Legal holds** — prevent destruction of documents involved in litigation or audits
- **Disposition workflows** — automate document destruction after retention expires
- **Audit trails** — track every action on every record (who accessed, modified, or deleted)
- **Classification schemes** — organize records by business function, department, or regulation

## Alfresco Records Management

[Alfresco](https://www.alfresco.com/) Community Edition is an enterprise content management platform with over 214 GitHub stars and active development. Its Records Management module (available as an addon) implements DoD 5015.2-STD compliance for records lifecycle management.

### Docker Deployment

```yaml
version: '3'
services:
  alfresco:
    image: alfresco/alfresco-content-repository-community:23.1.0
    container_name: alfresco-records
    environment:
      JAVA_OPTS: |
        -Ddb.driver=org.postgresql.Driver
        -Ddb.username=alfresco
        -Ddb.password=alfresco
        -Ddb.url=jdbc:postgresql://postgres:5432/alfresco
        -Dalfresco.host=localhost
        -Dalfresco.port=8080
        -Dalfresco.protocol=http
    ports:
      - "8080:8080"
    depends_on:
      - postgres

  postgres:
    image: postgres:14
    container_name: alfresco-db
    environment:
      POSTGRES_USER: alfresco
      POSTGRES_PASSWORD: alfresco
      POSTGRES_DB: alfresco
    volumes:
      - pgdata:/var/lib/postgresql/data

  share:
    image: alfresco/alfresco-share:23.1.0
    container_name: alfresco-share
    environment:
      REPO_HOST: alfresco
      REPO_PORT: 8080
    ports:
      - "8081:8080"
    depends_on:
      - alfresco

volumes:
  pgdata:
```

### Configuring Retention Schedules

Alfresco Records Management uses a file plan structure:

```
File Plan
├── Financial Records
│   ├── Tax Returns (7 years retention)
│   ├── Invoices (5 years retention)
│   └── Audit Reports (10 years retention)
├── Human Resources
│   ├── Employee Records (5 years after termination)
│   ├── Payroll Records (7 years)
│   └── Training Records (3 years)
└── Legal
    ├── Contracts (10 years after expiry)
    └── Litigation Hold (indefinite)
```

### Setting Up a Retention Rule

```
1. Navigate to Records Management > File Plan
2. Create a category (e.g., "Financial Records > Tax Returns")
3. Set retention period: 7 years
4. Set disposition action: "Destroy" or "Transfer to Archive"
5. Apply the category to incoming documents via rules:
   - Rule: If document type = "Tax Return"
   - Action: File as "Tax Returns" category
   - Trigger: Automatic on document creation
```

### Key Features

- DoD 5015.2-STD compliant records management
- File plan-based classification hierarchy
- Automatic retention period calculation
- Legal hold management with hold reports
- Disposition workflows with approval chains
- Full audit trail of all record actions
- CMIS API for integration with external systems
- Alfresco Share web interface for document management

## OpenKM Records Module

[OpenKM](https://www.openkm.com/) is a document management system with over 840 GitHub stars. Its community edition includes records management capabilities through metadata groups, version control, and workflow automation.

### Docker Deployment

```yaml
version: '3'
services:
  openkm:
    image: openkm/document-management-system:latest
    container_name: openkm-records
    ports:
      - "8080:8080"
    environment:
      - OPENKM_DB_DRIVER=org.postgresql.Driver
      - OPENKM_DB_URL=jdbc:postgresql://postgres:5432/openkm
      - OPENKM_DB_USER=openkm
      - OPENKM_DB_PASS=openkmpass
    volumes:
      - openkm_data:/opt/openkm/data
    depends_on:
      - postgres

  postgres:
    image: postgres:14
    container_name: openkm-db
    environment:
      POSTGRES_USER: openkm
      POSTGRES_PASSWORD: openkmpass
      POSTGRES_DB: openkm
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  openkm_data:
  pgdata:
```

### Configuring Metadata for Records

OpenKM uses metadata groups to classify records:

```xml
<!-- Define a retention metadata group -->
<group label="Retention Policy">
  <input label="Retention Period" type="text" name="retention_period"/>
  <select label="Disposition Action" name="disposition">
    <option label="Destroy" value="destroy"/>
    <option label="Archive" value="archive"/>
    <option label="Transfer" value="transfer"/>
  </select>
  <date label="Retention Start Date" name="retention_start"/>
  <date label="Destruction Date" name="destruction_date"/>
</group>
```

### Workflow-Based Retention

OpenKM workflows automate the records lifecycle:

```xml
<workflow-definition>
  <start name="Document Filed"/>
  <task name="Apply Retention Schedule"
        assignee="records-manager">
    <action name="Set Retention Period"/>
  </task>
  <timer name="Check Retention Expiry"
         duration="${retention_period}"/>
  <task name="Review for Disposition"
        assignee="compliance-officer"/>
  <end name="Document Disposed"/>
</workflow-definition>
```

### Key Features

- Metadata-driven record classification
- Version control with full revision history
- Workflow automation for retention and disposition
- Full-text search with OCR support
- Access control lists (ACLs) per document
- Document lifecycle audit trail
- CMIS and REST API access
- Web-based document viewer with annotation

## Mayan EDMS Retention Policies

[Mayan EDMS](https://www.mayan-edms.com/) is a Python-based document management system with built-in retention and records management features. It has a modern web interface, OCR capabilities, and automated document classification.

### Docker Deployment

```yaml
version: '3'
services:
  mayan:
    image: mayanedms/mayanedms:latest
    container_name: mayan-records
    ports:
      - "8000:8000"
    environment:
      MAYAN_DATABASE_ENGINE: django.db.backends.postgresql
      MAYAN_DATABASE_NAME: mayan
      MAYAN_DATABASE_USER: mayan
      MAYAN_DATABASE_PASSWORD: mayanpass
      MAYAN_DATABASE_HOST: postgres
      MAYAN_DATABASE_PORT: 5432
      MAYAN_CELERY_BROKER_URL: redis://redis:6379/0
      MAYAN_CELERY_RESULT_BACKEND: redis://redis:6379/1
    volumes:
      - mayan_media:/var/lib/mayan
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:14
    container_name: mayan-db
    environment:
      POSTGRES_USER: mayan
      POSTGRES_PASSWORD: mayanpass
      POSTGRES_DB: mayan
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7
    container_name: mayan-redis

volumes:
  mayan_media:
  pgdata:
```

### Setting Up Retention Policies

Mayan EDMS uses retention policies linked to document types:

```bash
# 1. Create a document type
# Navigate: Documents > Types > Create
# Name: "Tax Returns", Expiration period: 7 years

# 2. Create a retention policy
# Navigate: Maintenance > Retention Policies > Create
# Name: "Financial Records Retention"
# Rules:
#   - Document Type: Tax Returns → Retain 7 years → Action: Delete
#   - Document Type: Invoices → Retain 5 years → Action: Archive
#   - Document Type: Contracts → Retain 10 years → Action: Review

# 3. Automate document classification
# Navigate: Documents > Types > Tax Returns > Workflows
# Trigger: On document upload, apply "Tax Returns" type
# if filename matches pattern "*tax*" or "*return*"
```

### Key Features

- Automated document type classification via workflows
- Retention policies with configurable expiration actions
- Document versioning with full revision history
- OCR with Tesseract for full-text search
- Digital signatures and document signing workflows
- Role-based access control with granular permissions
- REST API for integration with external systems
- Email ingestion for automated document capture

## Comparison Table

| Feature | Alfresco Records | OpenKM Records | Mayan EDMS Retention |
|---------|-----------------|----------------|---------------------|
| **GitHub Stars** | 214 | 840 | N/A (Docker Hub) |
| **Last Update** | May 2026 | February 2026 | Active |
| **Compliance Standard** | DoD 5015.2-STD | Custom | Custom |
| **Retention Schedules** | File plan-based | Metadata-driven | Policy-based |
| **Legal Hold** | Yes | Via workflow | Via workflow |
| **Disposition Workflow** | Approval chains | Workflow automation | Policy-driven |
| **Full-Text Search** | Via Solr | Built-in (Lucene) | Built-in (Whoosh) |
| **OCR Support** | Via Tesseract plugin | Built-in | Built-in (Tesseract) |
| **CMIS API** | Yes | Yes | No |
| **REST API** | Yes | Yes | Yes |
| **Database** | PostgreSQL | PostgreSQL | PostgreSQL |
| **Tech Stack** | Java/Spring | Java | Python/Django |
| **Resource Requirements** | High (4GB+ RAM) | Medium (2GB+ RAM) | Medium (2GB+ RAM) |
| **Learning Curve** | Steep | Moderate | Moderate |

## Which Should You Choose?

**Choose Alfresco Records Management if:**
- You need DoD 5015.2-STD compliance out of the box
- You have enterprise-scale document volumes (millions of documents)
- You need CMIS interoperability with other ECM systems
- You have the infrastructure to support a Java-based platform (4GB+ RAM)

**Choose OpenKM Records if:**
- You want a balance between records management features and ease of deployment
- You need strong version control and workflow automation
- You prefer a Java-based platform with CMIS support
- You have moderate document volumes (hundreds of thousands)

**Choose Mayan EDMS Retention if:**
- You prefer a Python-based platform with lower resource requirements
- You want built-in OCR and automated document classification
- You need a modern web interface with good usability
- You're starting with records management and need an approachable platform

## Why Self-Host Your Records Management?

Cloud-based records management systems (OpenText, Iron Mountain, Recall) charge per-document or per-gigabyte fees that scale unpredictably. Self-hosted platforms give you flat infrastructure costs regardless of document volume.

More importantly, records often contain sensitive information subject to data residency laws (GDPR, CCPA, HIPAA). Self-hosted records management ensures documents never leave your infrastructure, simplifying compliance audits and reducing the risk of data exposure through third-party breaches.

For [document sharing without records management overhead](../2026-04-27-papermark-vs-filestash-vs-pingvin-share-self-hosted-document-sharing-2026/), the Papermark vs Filestash vs Pingvin Share guide covers lightweight document sharing. For [broader document management without retention policies](../2026-04-27-mayan-edms-vs-teedy-vs-docspell-self-hosted-document-management-2026/), the Mayan EDMS vs Teedy vs Docspell comparison covers general document management features.

## FAQ

### What is the difference between document management and records management?

Document management focuses on creating, storing, organizing, and retrieving documents throughout their active lifecycle. Records management adds governance: it classifies documents as official records, applies retention schedules (how long they must be kept), manages legal holds (preventing destruction during litigation), and automates disposition (destruction or archival after retention expires).

### What is DoD 5015.2-STD compliance?

DoD 5015.2-STD is a U.S. Department of Defense standard for records management systems. It defines requirements for record declaration, access controls, retention scheduling, disposition, audit trails, and security. Alfresco Records Management is certified to this standard, making it suitable for government and defense contractors.

### How are retention periods calculated?

Retention periods typically start from one of these trigger events: document creation date, document modification date, document filing date, or a business event (e.g., employee termination date, contract expiry date). The retention system calculates the destruction date automatically based on the trigger event plus the retention period.

### Can records management systems prevent accidental deletion?

Yes. Records management systems enforce retention policies that prevent documents from being deleted before their retention period expires. Even users with administrative privileges cannot bypass these policies without going through a formal disposition workflow with approval chains.

### What happens when a retention period expires?

When a retention period expires, the system triggers a disposition workflow. Depending on the configured action, the document is either: (1) automatically destroyed (secure deletion), (2) transferred to long-term archive (offline storage), or (3) flagged for manual review by a compliance officer. The disposition action and timestamp are logged in the audit trail.

### Can these systems handle email records?

Yes, all three platforms can manage email records. Alfresco and OpenKM have email ingestion connectors that capture emails from IMAP/Exchange servers. Mayan EDMS supports email ingestion via its API or through workflow triggers. Emails are classified, indexed, and subject to the same retention policies as other document types.

### How do legal holds work?

A legal hold suspends the normal disposition process for specific records. When litigation or an audit is anticipated, an administrator places a legal hold on relevant record categories. All records under the hold are protected from automatic destruction, even if their retention period has expired. Hold reports track which records are under hold and why.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Records Management: Alfresco Records vs OpenKM vs Mayan EDMS Retention 2026",
  "description": "Compare open-source self-hosted records management platforms: Alfresco Records, OpenKM Records, and Mayan EDMS. Retention schedules, legal holds, and disposition workflows.",
  "datePublished": "2026-05-08",
  "dateModified": "2026-05-08",
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
