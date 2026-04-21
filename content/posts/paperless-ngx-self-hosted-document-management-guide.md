---
title: "Complete Guide to Paperless-ngx: Self-Hosted Document Management 2026"
date: 2026-04-12
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete guide to Paperless-ngx — self-hosted document management with OCR, tagging, and full-text search. Ditch cloud storage and own your documents."
---

Every household and small business drowns in paper: utility bills, bank statements, insurance policies, tax receipts, contracts, medical records. Commercial solutions like DocuWare or SharePoint cost hundreds per month and lock your sensitive documents inside someone else's infrastructure. **Paperless-ngx** changes that entirely. It is a free, open-source document management system that scans, indexes, and organizes every piece of paper you own — running on your own hardware, under your complete control.

In this guide, you will learn what Paperless-ngx is, why self-hosting your documents matters, how to deploy it with [docker](https://www.docker.com/), and how to configure it for production use. Whether you want to archive a decade of tax records or build a paperless office from scratch, this guide covers everything.

## Why Self-Host Your Document Management

The average person receives over 200 pieces of mail per year. Most of it ends up in a filing cabinet or a shoebox. Digitizing those documents and storing them in Google Drive or Dropbox might feel like progress, but it introduces real risks:

- **Privacy exposure** — Cloud providers scan your files for advertising profiles, policy enforcement, or training data. Financial statements, medical records, and contracts deserve better.
- **Vendor lock-in** — Migrate away from a cloud service and you discover that export is painful, search is limited, and metadata is lost.
- **Subscription creep** — Storage needs grow. What starts as a free tier becomes $10, then $20, then $100 per month as your archive expands.
- **No OCR control** — Cloud storage does not automatically extract text from scanned PDFs, making search unreliable.
- **Compliance requirements** — GDPR, HIPAA, and financial regulations often require data to remain on-premises or under your direct control.

Paperless-ngx solves all of these problems. It runs on a $35 Raspberry Pi or any spare computer, performs optical character recognition automatically, indexes every word for instant search, and stores everything in an open, portable format. You own the data, you own the infrastructure, and you own the search.

## What Is Paperless-ngx

Paperless-ngx is a community-maintained fork of the original Paperless project. It is a Django-based web application that manages your digitized documents with these core capabilities:

- **Automatic OCR** — Every uploaded or scanned document is processed with Tesseract OCR, making all text searchable instantly.
- **Smart tagging** — Correspondents, tags, document types, and storage paths are automatically assigned using machine learning trained on your filing habits.
- **Full-text search** — Search across every word in every document, with highlighting and context snippets.
- **Email consumption** — Configure an email inbox; Paperless-ngx automatically downloads attachments and files them.
- **Multi-format support** — PDFs, images (PNG, JPG, TIFF), plain text, and Office documents are all handled natively.
- **REST API** — Full API access enables integration with scanners, mobile apps, and automation workflows.
- **Multi-user support** — Role-based access control with per-document ownership and sharing.
- **Workflows** — Automate com[plex](https://www.plex.tv/) filing rules based on document content, source, or metadata.

Paperless-ngx is licensed under the GPL-3.0 and has an active community of contributors. The "ngx" suffix denotes the next-generation rewrite with modern tooling, performance improvements, and a redesigned interface.

## Comparing Document Management Options

Before diving into installation, it helps to understand where Paperless-ngx sits in the landscape of document management tools.

| Feature | Paperless-ngx | DocuWare | SharePoint | [nextcloud](https://nextcloud.com/) Files |
|---------|---------------|----------|------------|-----------------|
| License | GPL-3.0 (Free) | Commercial | Commercial | AGPL-3.0 (Free) |
| Self-hosted | Yes | On-prem option | On-prem option | Yes |
| Automatic OCR | Built-in (Tesseract) | Add-on | Add-on | Requires app |
| Auto-tagging | ML-based | Manual | Manual | Manual |
| Full-text search | Native | Yes | Yes | Limited |
| Email consumption | Built-in | Yes | Requires flow | Requires app |
| REST API | Yes | Yes | Yes | Yes |
| Workflow engine | Built-in | Yes | Power Automate | Flow |
| Mobile app | Community | Official | Official | Official |
| Multi-user | Yes | Yes | Yes | Yes |
| Storage format | Open (PDF + metadata) | Proprietary DB | Proprietary | Open files |

Paperless-ngx stands out because it combines OCR, automatic classification, and search into a single package with zero licensing cost. Nextcloud Files is a close alternative for basic file storage, but it lacks the document-specific features like automatic OCR processing, correspondent tracking, and ML-based tagging that make Paperless-ngx purpose-built for document management.

## System Requirements

Paperless-ngx is lightweight and runs on minimal hardware:

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 2 GB | 4+ GB |
| Storage | 20 GB | 100+ GB SSD |
| OS | Linux (Debian/Ubuntu) | Debian 12 / Ubuntu 24.04 |

A Raspberry Pi 4 with 4 GB RAM handles a personal archive comfortably. For small business deployments with thousands of documents and multiple concurrent users, a small VPS or dedicated server with 4+ cores and an SSD is ideal.

## Installation with Docker Compose

The recommended deployment method is Docker Compose. This ensures all dependencies — PostgreSQL, Redis, Tesseract, and the web application — run in isolated, reproducible containers.

### Step 1: Install Docker and Docker Compose

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker compose version
```

### Step 2: Create the Project Directory

```bash
mkdir -p ~/paperless-ngx
cd ~/paperless-ngx

# Create data directories
mkdir -p data media export consume
```

### Step 3: Create docker-compose.yml

```yaml
services:
  broker:
    image: docker.io/library/redis:7
    restart: unless-stopped
    volumes:
      - ./data/redisdata:/data

  db:
    image: docker.io/library/postgres:16
    restart: unless-stopped
    volumes:
      - ./data/pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: paperless
      POSTGRES_USER: paperless
      POSTGRES_PASSWORD: your-secure-db-password

  webserver:
    image: ghcr.io/paperless-ngx/paperless-ngx:latest
    restart: unless-stopped
    depends_on:
      - db
      - broker
    ports:
      - "8000:8000"
    volumes:
      - ./data:/usr/src/paperless/data
      - ./media:/usr/src/paperless/media
      - ./export:/usr/src/paperless/export
      - ./consume:/usr/src/paperless/consume
    environment:
      PAPERLESS_REDIS: redis://broker:6379
      PAPERLESS_DBHOST: db
      PAPERLESS_DBPORT: 5432
      PAPERLESS_DBNAME: paperless
      PAPERLESS_DBUSER: paperless
      PAPERLESS_DBPASS: your-secure-db-password
      PAPERLESS_SECRET_KEY: change-this-to-a-long-random-string
      PAPERLESS_URL: http://your-server-ip:8000
      PAPERLESS_ADMIN_USER: admin
      PAPERLESS_ADMIN_PASSWORD: your-admin-password
      PAPERLESS_OCR_LANGUAGE: eng
      PAPERLESS_TIME_ZONE: UTC
      PAPERLESS_CONSUMER_RECURSIVE: "true"
      PAPERLESS_CONSUMER_POLLING: 60
      PAPERLESS_CONSUMER_DELETE_DUPLICATES: "true"
```

**Important**: Replace `your-secure-db-password`, `change-this-to-a-long-random-string`, and `your-admin-password` with strong, unique values. Generate a secret key with:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

### Step 4: Launch the Stack

```bash
cd ~/paperless-ngx
docker compose up -d
```

The first startup takes a minute as PostgreSQL initializes and Paperless-ngx runs database migrations. Check the logs:

```bash
docker compose logs -f webserver
```

Look for `Starting Paperless-ngx server` — that confirms everything is ready.

### Step 5: Access the Web Interface

Open `http://your-server-ip:8000` in your browser and log in with the admin credentials you set in the environment variables. You will see a clean, modern dashboard ready to receive documents.

## Configuration and Optimization

### Enable Multiple OCR Languages

If you receive documents in multiple languages, configure Tesseract to handle them:

```yaml
# Add to webserver environment in docker-compose.yml
PAPERLESS_OCR_LANGUAGE: eng+deu+fra
```

Install additional language packs on the host or build a custom Docker image with extra Tesseract language data packages.

### Configure Email Consumption

Paperless-ngx can automatically process email attachments. Set up a dedicated email account and add these environment variables:

```yaml
PAPERLESS_EMAIL_SECRET: your-email-secret
PAPERLESS_CONSUMPTION_DIR: /usr/src/paperless/consume
# Enable IMAP fetching
PAPERLESS_EMAIL_HOST: imap.your-provider.com
PAPERLESS_EMAIL_PORT: 993
PAPERLESS_EMAIL_USER: paperless@your-domain.com
PAPERLESS_EMAIL_PASSWORD: your-email-password
```

Alternatively, use the built-in email consumption workflow in the web interface under **Settings > Email** to configure IMAP accounts with per-account tagging rules.

### Set Up Automatic Document Classification

Paperless-ngx includes a machine learning classifier that learns from your filing behavior. After you manually tag 20-30 documents, the system begins suggesting correspondents, tags, and document types automatically.

To fine-tune classification:

1. Go to **Settings > Correspondents** and create entries for regular senders (banks, utility companies, government agencies).
2. Go to **Settings > Tags** and create a taxonomy (e.g., `finance/taxes`, `finance/insurance`, `medical`, `legal`).
3. Go to **Settings > Document Types** and define categories (Invoice, Contract, Statement, Receipt, Letter).
4. Upload a batch of 30+ documents and manually classify them.
5. The classifier will start auto-assigning metadata to new documents.

### Configure Workflows for Automation

Workflows are the most powerful feature in Paperless-ngx. They let you define rules like "if a PDF contains the word 'invoice' and comes from a specific email address, assign tag `finance/invoice` and correspondent 'Acme Corp'."

Example workflow configuration via the web interface:

1. Navigate to **Settings > Workflows**
2. Create a new workflow with a **Trigger** (e.g., "Document added from consume folder")
3. Add **Conditions** (e.g., "Content contains 'tax return'")
4. Add **Actions** (e.g., "Assign tag `finance/tax-2025`", "Set document type to 'Tax Document'")

Workflows can also:
- Move documents to specific storage paths
- Send email notifications
- Assign documents to specific users
- Remove pages from scanned documents
- Run custom scripts

## Adding Documents

### Upload via Web Interface

Drag and drop files directly onto the dashboard. Paperless-ngx processes them immediately — OCR runs in the background, and the document appears in your library within seconds.

### Watch the Consume Folder

Any file placed in the `consume` directory is automatically processed. This is ideal for scanner integration:

```bash
# Scanner saves to the consume folder automatically
cp /tmp/scanned-document.pdf ~/paperless-ngx/consume/

# Or use a cron job to pull from a network scanner
# */5 * * * * scp scanner:/output/*.pdf ~/paperless-ngx/consume/
```

### Bulk Import

For migrating an existing archive:

```bash
# Copy documents into the consume folder
cp /old-archive/*.pdf ~/paperless-ngx/consume/

# Monitor processing progress
docker compose logs -f webserver | grep "Consuming"
```

### Use the REST API

For programmatic access:

```bash
# Upload a document via API
curl -X POST http://your-server:8000/api/documents/post_document/ \
  -H "Authorization: Token your-api-token" \
  -F "document=@tax-return-2025.pdf"

# Search documents
curl "http://your-server:8000/api/documents/?title__icontains=insurance" \
  -H "Authorization: Token your-api-token"

# List all documents with metadata
curl "http://your-server:8000/api/documents/?page_size=50" \
  -H "Authorization: Token your-api-token"
```

Generate API tokens under your user profile in the web interface.

## Backup and Disaster Recovery

Your document archive is only as good as your backup strategy. Paperless-ngx stores data in three locations:

| Directory | Contents |
|-----------|----------|
| `data/` | PostgreSQL database, Redis data, ML classifier models |
| `media/` | Original documents and OCR text files |
| `export/` | Exported documents and metadata |

### Automated Backup Script

```bash
#!/bin/bash
# backup-paperless.sh
BACKUP_DIR="/backup/paperless-ngx"
DATE=$(date +%Y-%m-%d_%H%M%S)
PAPERLESS_DIR="$HOME/paperless-ngx"

mkdir -p "$BACKUP_DIR"

# Stop services for consistent backup
cd "$PAPERLESS_DIR"
docker compose stop webserver

# Create database dump
docker compose exec -T db pg_dump -U paperless paperless | \
  gzip > "$BACKUP_DIR/db-$DATE.sql.gz"

# Archive media files
tar czf "$BACKUP_DIR/media-$DATE.tar.gz" media/

# Export all documents with metadata
docker compose exec -T webserver document_exporter "$BACKUP_DIR/export-$DATE"

# Restart services
docker compose start webserver

# Keep only last 30 days of backups
find "$BACKUP_DIR" -name "*.gz" -mtime +30 -delete
find "$BACKUP_DIR" -name "export-*" -mtime +30 -exec rm -rf {} +

echo "Backup completed: $DATE"
```

Schedule this with cron for daily backups:

```bash
0 2 * * * /home/user/backup-paperless.sh >> /var/log/paperless-backup.log 2>&1
```

### Restore from Backup

```bash
# Stop the stack
docker compose down

# Restore database
gunzip -c db-2026-04-10_020000.sql.gz | \
  docker compose exec -T db psql -U paperless paperless

# Restore media
tar xzf media-2026-04-10_020000.tar.gz -C ~/paperless-ngx/

# Restart
docker compose up -d
```

## Securing Your Deployment

A document management system holds your most sensitive information. Harden it with these steps:

### Enable HTTPS with a Reverse Proxy

```yaml
# Add a Caddy reverse proxy to docker-compose.yml
  caddy:
    image: caddy:2
    restart: unless-stopped
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config

volumes:
  caddy_data:
  caddy_config:
```

Create a `Caddyfile`:

```
your-domain.com {
    reverse_proxy webserver:8000
    encode gzip
}
```

Caddy automatically obtains and renews TLS certificates from Let's Encrypt.

### Restrict Admin Access

```yaml
# Add to webserver environment
PAPERLESS_CORS_ALLOWED_HOSTS: https://your-domain.com
PAPERLESS_CSRF_TRUSTED_ORIGINS: https://your-domain.com
PAPERLESS_ADMIN_ROOT: secret-admin-path
```

### Network Isolation

Place Paperless-ngx on a separate Docker network with only necessary port exposure:

```yaml
networks:
  paperless-net:
    driver: bridge

services:
  webserver:
    networks:
      - paperless-net
    # Remove port mapping when using reverse proxy
```

## Integrations and Ecosystem

Paperless-ngx integrates with the broader self-hosted ecosystem:

- **Paperless-ngx mobile apps** — Community apps for iOS and Android let you photograph documents on the go and upload them directly.
- **Scanner integration** — Most network scanners can be configured to save directly to the consume folder via SMB, NFS, or SCP.
- **Authentik / Authelia** — Use your existing SSO provider for authentication via reverse proxy headers.
- **Immich** — Cross-reference document photos with your self-hosted photo library.
- **Syncthing** — Sync the consume folder across multiple devices for distributed scanning.
- **N8n / Node-RED** — Trigger workflows from external systems via the REST API.

## Conclusion

Paperless-ngx transforms a chaotic pile of paper into a searchable, organized digital archive that you fully control. It costs nothing to run, respects your privacy by design, and integrates seamlessly into any self-hosted infrastructure. Whether you are a homeowner archiving decades of financial records or a small business managing contracts and compliance documents, Paperless-ngx provides enterprise-grade document management without the enterprise price tag.

The combination of automatic OCR, machine learning classification, email consumption, and workflow automation means that once set up, your document archive practically manages itself. Add the robust backup strategy and API access, and you have a future-proof solution that grows with your needs.

Start with the Docker Compose deployment above, feed it your first batch of documents, and watch as years of paper chaos transform into an organized, searchable digital library — all running on your own hardware, under your own control.

## Frequently Asked Questions (FAQ)

### Which one should I choose in 2026?

The best choice depends on your specific requirements:

- **For beginners**: Start with the simplest option that covers your core use case
- **For production**: Choose the solution with the most active community and documentation
- **For teams**: Look for collaboration features and user management
- **For privacy**: Prefer fully open-source, self-hosted options with no telemetry

Refer to the comparison table above for detailed feature breakdowns.

### Can I migrate between these tools?

Most tools support data import/export. Always:
1. Backup your current data
2. Test the migration on a staging environment
3. Check official migration guides in the documentation

### Are there free versions available?

All tools in this guide offer free, open-source editions. Some also provide paid plans with additional features, priority support, or managed hosting.

### How do I get started?

1. Review the comparison table to identify your requirements
2. Visit the official documentation (links provided above)
3. Start with a Docker Compose setup for easy testing
4. Join the community forums for troubleshooting
