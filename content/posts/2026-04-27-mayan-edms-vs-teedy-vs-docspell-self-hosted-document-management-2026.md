
---
title: "Mayan EDMS vs Teedy vs Docspell: Best Self-Hosted Document Management 2026"
date: 2026-04-27
tags: ["comparison", "guide", "self-hosted", "document-management", "DMS"]
draft: false
description: "Compare Mayan EDMS, Teedy, and Docspell — three open-source document management systems you can self-host. Includes Docker Compose configs, feature comparison, and deployment guides."
---

Managing paper documents, scanned PDFs, invoices, and contracts quickly becomes unmanageable without a proper system. Open-source document management systems (DMS) solve this problem by providing centralized storage, full-text search, automatic tagging, and workflow automation — all running on your own infrastructure.

In this guide, we compare three leading self-hosted document management platforms: **Mayan EDMS**, **Teedy** (formerly Sismics Docs), and **Docspell**. Each offers a different balance of features, complexity, and resource requirements, making them suitable for different use cases.

## Why Self-Host Your Document Management System

Cloud document management services charge per user, per storage tier, and per workflow step. They also hold your sensitive contracts, financial records, and legal documents on servers you don't control. Self-hosting a DMS gives you:

- **Full data ownership** — documents never leave your infrastructure
- **No per-user licensing fees** — unlimited users at zero additional cost
- **Custom workflows** — build document approval chains, retention policies, and access controls tailored to your organization
- **Offline access** — your documents are available even when internet connectivity is down
- **Integration flexibility** — connect to your existing LDAP, S3 storage, or backup systems

For related reading, see our [Paperless-ngx document management guide](../paperless-ngx-self-hosted-document-management-guide/) for a single-tool deep dive, and our [self-hosted OCR tools comparison](../self-hosted-ocr-tesseract-paddledoc-doctr-easyocr-guide-2026/) for preprocessing scanned documents before ingestion.

## Overview: Three Approaches to Document Management

### Mayan EDMS — Enterprise-Grade Document Lifecycle Management

[Mayan EDMS](https://www.mayan-edms.com/) is a Django-based document management system built for organizations that need granular access controls, version tracking, and complex workflows. With 801 GitHub stars and active development (last pushed April 2026), it is the most feature-complete option in this comparison.

**Key characteristics:**
- Python/Django backend with PostgreSQL
- Role-based access control with document-level permissions
- Automatic document versioning and check-in/check-out
- Workflow engine with states, transitions, and triggers
- Built-in OCR pipeline using Tesseract
- Digital signature support
- REST API for integrations

### Teedy — Lightweight and Simple

[Teedy](https://teedy.io/) (formerly Sismics Docs) is a lightweight document management system built with Java and Elasticsearch. With 2,545 GitHub stars, it is the most popular of the three by star count. Teedy focuses on simplicity: upload documents, tag them, search, and share.

**Key characteristics:**
- Java backend with Elasticsearch for full-text search
- Simple tag-based organization (no hierarchical folders)
- Built-in OCR with Tesseract
- Clean, modern web interface
- REST API with OAuth2 support
- Docker-first deployment

### Docspell — Personal Document Organizer

[Docspell](https://docspell.org/) is a Scala-based document organizer designed for individuals and small teams managing incoming mail, invoices, and receipts. With 2,203 GitHub stars and very recent activity (last pushed April 2026), it actively extracts metadata from documents to auto-classify and organize them.

**Key characteristics:**
- Scala backend with Elm frontend
- Automatic metadata extraction (sender, recipient, dates, amounts)
- Rule-based document classification
- REST API with OpenAPI specification
- Solr or PostgreSQL full-text search backend
- Two-component architecture: REST server + job executor (JOEX)

## Feature Comparison Table

| Feature | Mayan EDMS | Teedy | Docspell |
|---------|-----------|-------|----------|
| **Backend** | Python/Django | Java/Jersey | Scala |
| **Frontend** | Django templates | AngularJS | Elm |
| **Database** | PostgreSQL | H2 / PostgreSQL | PostgreSQL |
| **Search** | PostgreSQL FTS + Elasticsearch | Elasticsearch | Solr / PostgreSQL |
| **OCR** | Built-in (Tesseract) | Built-in (Tesseract) | Built-in (Tesseract via JOEX) |
| **Metadata Extraction** | Manual + custom | Tags only | Automatic (sender, date, amount) |
| **Access Control** | Role-based, document-level | User + tag-based | User + collective-based |
| **Versioning** | Yes (full version history) | No | No |
| **Workflows** | Yes (state machine) | No | No |
| **Digital Signatures** | Yes | No | No |
| **REST API** | Yes | Yes (OAuth2) | Yes (OpenAPI) |
| **Docker Support** | Official compose (multi-service) | Official compose | Community compose |
| **Resource Requirements** | High (5+ services) | Low (2 services) | Medium (3 services) |
| **Learning Curve** | Steep | Easy | Moderate |
| **GitHub Stars** | 801 | 2,545 | 2,203 |
| **License** | Apache 2.0 | Apache 2.0 | GPL 3.0 |

## Installing Mayan EDMS with Docker Compose

Mayan EDMS is the most complex to deploy because it requires PostgreSQL, Redis, RabbitMQ, and optionally Elasticsearch. The official Docker Compose file uses a `.env` file for configuration and supports multiple profiles.

### Step 1: Clone the official Docker setup

```bash
mkdir -p ~/mayan-edms && cd ~/mayan-edms
wget https://raw.githubusercontent.com/mayan-edms/mayan-edms/master/docker/docker-compose.yml
wget https://raw.githubusercontent.com/mayan-edms/mayan-edms/master/docker/.env
```

### Step 2: Configure environment variables

Edit the `.env` file to set your database passwords and admin credentials:

```bash
# Mayan EDMS .env configuration
MAYAN_DATABASE_PASSWORD=your_secure_db_password
MAYAN_REDIS_PASSWORD=your_secure_redis_password
MAYAN_RABBITMQ_PASSWORD=your_secure_rabbit_password
MAYAN_ADMIN_USERNAME=admin
MAYAN_ADMIN_PASSWORD=your_admin_password
MAYAN_DOCKER_IMAGE_TAG=s4.3
```

### Step 3: Start the services

```bash
docker compose --profile all_in_one --profile postgresql --profile redis up -d
```

For a production deployment with Elasticsearch for faster search:

```bash
docker compose --profile all_in_one --profile postgresql --profile redis --profile elasticsearch up -d
```

Mayan EDMS will be available at `http://your-server:80`. The initial setup creates the admin user and database schema automatically.

### Step 4: Post-installation

- Navigate to Setup → Sources to configure document upload sources (watch folders, email, staging directories)
- Configure OCR settings under Setup → OCR
- Set up user roles and permissions under Setup → Access Control
- Define document types and metadata sets for auto-classification

## Installing Teedy with Docker Compose

Teedy is significantly simpler to deploy — just a single container plus an optional reverse proxy. The official `docker-compose.yml` is straightforward:

```yaml
version: '3'
services:
  teedy-server:
    image: sismics/docs:v1.10
    restart: unless-stopped
    ports:
      - 8080:8080
    environment:
      DOCS_BASE_URL: "https://docs.example.com"
      DOCS_ADMIN_EMAIL_INIT: "admin@example.com"
      DOCS_ADMIN_PASSWORD_INIT: "$$2a$$05$$PcMNUbJvsk7QHFSfEIDaIOjk1VI9/E7IPjTKx.jkjPx"
    volumes:
      - teedy-data:/data

volumes:
  teedy-data:
```

### Running Teedy

```bash
mkdir -p ~/teedy && cd ~/teedy
cat > docker-compose.yml << 'COMPOSE'
version: '3'
services:
  teedy-server:
    image: sismics/docs:v1.10
    restart: unless-stopped
    ports:
      - 8080:8080
    environment:
      DOCS_BASE_URL: "http://localhost:8080"
      DOCS_ADMIN_EMAIL_INIT: "admin@localhost"
      DOCS_ADMIN_PASSWORD_INIT: "$$2a$$05$$PcMNUbJvsk7QHFSfEIDaIOjk1VI9/E7IPjTKx.jkjPx"
    volumes:
      - ./data:/data
COMPOSE

docker compose up -d
```

Teedy will be available at `http://your-server:8080`. Log in with the admin credentials you configured. The default password hash above corresponds to `admin` — change it immediately after first login.

## Installing Docspell with Docker Compose

Docspell uses a two-component architecture: a REST server (`docspell/restserver`) for the web interface and API, and a job executor (`docspell/joex`) for background processing like OCR and metadata extraction. Both connect to a shared PostgreSQL database.

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: docspell
      POSTGRES_USER: docspell
      POSTGRES_PASSWORD: docspelldbpass
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U docspell"]
      interval: 5s
      timeout: 5s
      retries: 5

  restserver:
    image: docspell/restserver:0.47.0
    ports:
      - "7880:7880"
    environment:
      DOCSPELL_JDBC_URL: "jdbc:postgresql://postgres:5432/docspell"
      DOCSPELL_JDBC_USER: docspell
      DOCSPELL_JDBC_PASSWORD: docspelldbpass
      DOCSPELL_SERVER_AUTH_SECRET: "your-auth-secret-key"
      DOCSPELL_SERVER_EXTERNAL_URL: "http://localhost:7880"
    depends_on:
      postgres:
        condition: service_healthy

  joex:
    image: docspell/joex:0.47.0
    environment:
      DOCSPELL_JOEX_JDBC_URL: "jdbc:postgresql://postgres:5432/docspell"
      DOCSPELL_JOEX_JDBC_USER: docspell
      DOCSPELL_JOEX_JDBC_PASSWORD: docspelldbpass
      DOCSPELL_JOEX_TESSERGC_CMD: "tesseract"
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - /usr/bin/tesseract:/usr/bin/tesseract:ro

volumes:
  pgdata:
```

### Running Docspell

```bash
mkdir -p ~/docspell && cd ~/docspell
# Save the compose file above as docker-compose.yml
docker compose up -d
```

Docspell will be available at `http://your-server:7880`. Create a collective (organization) and add users through the web interface.

## Choosing the Right DMS for Your Use Case

### Choose Mayan EDMS if:

- You need **enterprise document lifecycle management** with versioning, check-in/check-out, and digital signatures
- Your organization has **complex access control requirements** (department-level permissions, approval workflows)
- You need **audit trails** for compliance (SOX, HIPAA, GDPR)
- You have the infrastructure resources to run 5+ Docker containers

Mayan EDMS is the right choice for medium to large organizations, law firms, and enterprises that treat documents as managed assets with lifecycles.

### Choose Teedy if:

- You want a **simple, lightweight system** that works out of the box
- Your primary need is **document storage with full-text search and tagging**
- You prefer a **single-container deployment** with minimal configuration
- You have a small team (1-20 users) managing shared documents

Teedy is ideal for small teams, freelancers, and personal use where simplicity trumps advanced features.

### Choose Docspell if:

- You primarily manage **incoming documents** (invoices, receipts, letters, contracts)
- You want **automatic metadata extraction** — Docspell parses sender, date, and amounts from your documents
- You need **rule-based classification** to auto-file documents into categories
- You are an individual or small team processing high volumes of incoming mail

Docspell excels at the "incoming document pipeline" use case — scanning mail, extracting key fields, and filing everything automatically.

## Resource Requirements Comparison

| Component | Mayan EDMS | Teedy | Docspell |
|-----------|-----------|-------|----------|
| **Minimum RAM** | 4 GB | 1 GB | 2 GB |
| **Recommended RAM** | 8 GB | 2 GB | 4 GB |
| **Disk (base)** | 10 GB | 2 GB | 5 GB |
| **Docker Containers** | 5-7 | 1-2 | 3 |
| **External Services** | PostgreSQL, Redis, RabbitMQ, Elasticsearch | None (built-in H2) | PostgreSQL |
| **CPU for OCR** | Dedicated worker container | Built-in | JOEX worker |

Mayan EDMS is the most resource-intensive due to its multi-service architecture. Teedy is the lightest — it can run on a Raspberry Pi. Docspell sits in the middle, requiring PostgreSQL but no message queue or cache layer.

## Security Considerations

All three systems support HTTPS via reverse proxy (Nginx, Caddy, or Traefik). Key security features:

- **Mayan EDMS**: Document-level ACLs, role-based permissions, watermarking, audit logging, two-factor authentication
- **Teedy**: User authentication, tag-level visibility controls, OAuth2 for API access
- **Docspell**: Collective-based isolation, TOTP two-factor authentication, API key management

For production deployments, always place your DMS behind a reverse proxy with TLS termination. Consider integrating with your existing LDAP/Active Directory for centralized authentication.

## Migration from Paper-Based Systems

Migrating physical documents to any of these systems follows a similar pattern:

1. **Scan documents** at 300 DPI minimum, using PDF or TIFF format
2. **Run OCR** — all three systems include Tesseract integration
3. **Define document types** — invoices, contracts, correspondence, receipts
4. **Set up metadata fields** — date, sender, amount, reference number
5. **Configure ingestion sources** — watch folders, email forwarding, or manual upload
6. **Train classification rules** — especially important for Docspell's auto-classification

For large document archives, batch import tools are available in all three systems. Mayan EDMS offers the most robust bulk import with progress tracking and error reporting.

## Backup and Disaster Recovery

Regular backups are critical for any DMS:

```bash
# Mayan EDMS backup (PostgreSQL + volumes)
docker compose exec postgresql pg_dump -U mayan mayan > mayan_backup.sql
docker compose cp mayan_app:/var/lib/mayan ./mayan-data-backup

# Teedy backup
docker compose cp teedy-server:/data ./teedy-data-backup

# Docspell backup (PostgreSQL + indexed files)
docker compose exec postgres pg_dump -U docspell docspell > docspell_backup.sql
```

Store backups off-site and test restoration procedures quarterly. Mayan EDMS also supports native export/import for individual documents and document types.

## FAQ

### Which document management system is best for small businesses?

Teedy is the best choice for small businesses that need simplicity. It deploys as a single Docker container, requires minimal configuration, and provides essential features like full-text search, tagging, and user management. If your business processes high volumes of incoming invoices and receipts, Docspell's automatic metadata extraction may be more valuable.

### Can these systems replace Google Drive or Dropbox?

Not directly. These are document management systems, not general-purpose file sync and share platforms. They excel at managing structured documents (invoices, contracts, forms) with metadata, search, and workflows. For unstructured file sharing and sync, consider pairing a DMS with Nextcloud or Seafile.

### Do these systems support mobile access?

All three systems provide responsive web interfaces that work on mobile browsers. Mayan EDMS and Docspell also offer REST APIs that can be used to build custom mobile applications. Teedy's API supports OAuth2 authentication for third-party mobile clients.

### How does OCR performance compare between the three?

All three use Tesseract OCR under the hood, so raw accuracy is similar. Mayan EDMS runs OCR in dedicated worker containers, allowing parallel processing of large document batches. Docspell's JOEX worker handles OCR as part of its broader metadata extraction pipeline. Teedy processes OCR inline during document upload. For high-volume OCR workloads, Mayan EDMS scales best.

### Can I import documents from Paperless-ngx?

There is no direct migration tool, but you can export documents and metadata from Paperless-ngx as PDFs with tags and re-import them into any of these systems. Mayan EDMS offers the most flexible import API for bulk migrations, allowing you to script the transfer of documents, tags, and metadata.

### Which system has the best search capabilities?

Mayan EDMS and Teedy both support Elasticsearch for fast full-text search across large document collections. Docspell supports Solr or PostgreSQL full-text search. For organizations with tens of thousands of documents, Elasticsearch-backed systems (Mayan EDMS or Teedy) provide the fastest and most relevant search results, including fuzzy matching and faceted search.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Mayan EDMS vs Teedy vs Docspell: Best Self-Hosted Document Management 2026",
  "description": "Compare Mayan EDMS, Teedy, and Docspell — three open-source document management systems you can self-host. Includes Docker Compose configs, feature comparison, and deployment guides.",
  "datePublished": "2026-04-27",
  "dateModified": "2026-04-27",
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
