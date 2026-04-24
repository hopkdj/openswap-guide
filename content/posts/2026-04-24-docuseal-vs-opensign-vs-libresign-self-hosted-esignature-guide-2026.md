---
title: "DocuSeal vs OpenSign vs LibreSign: Best Self-Hosted E-Signature 2026"
date: 2026-04-24
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Compare DocuSeal, OpenSign, and LibreSign — three open-source, self-hosted alternatives to DocuSign. Full Docker deployment guides, feature comparison, and pricing analysis for 2026."
---

Electronic signatures have replaced paper contracts across every industry. Real estate closings, employment agreements, vendor onboarding, service-level agreements — the list goes on. DocuSign built an empire around this workflow, but its per-envelope pricing model and third-party data storage create real concerns for organizations that value privacy and cost control.

The open-source ecosystem now offers three mature, self-hosted e-signature platforms that eliminate both problems: [DocuSeal](https://github.com/docusealco/docuseal), [OpenSign](https://github.com/opensignlabs/opensign), and [LibreSign](https://github.com/libresign/libresign). Each takes a different architectural approach, targets a different user base, and ships with different feature sets. In this guide, we compare all three side by side and provide complete Docker deployment instructions so you can run your own signing infrastructure on a $5 VPS.

## Why Self-Host Your E-Signature Platform

Running your own signing server is not about reinventing the wheel — it is about keeping sensitive contracts inside your perimeter.

**Data sovereignty.** Every document you send through a cloud e-signature provider is stored on their servers, often in jurisdictions outside your control. Self-hosting means every PDF, every signature certificate, and every audit trail stays in your own database. This matters for GDPR compliance, HIPAA-covered entities, and any organization bound by data residency requirements.

**No per-envelope fees.** DocuSign charges $10–$40 per user per month with document caps that increase the price. For a team sending hundreds of contracts monthly, costs compound quickly. A self-hosted instance costs only the server — typically $5–$15 per month on a small VPS — regardless of volume.

**Full branding control.** Remove third-party logos, customize email templates, apply your domain to signing URLs, and embed the signing experience inside your existing portals. Cloud providers reserve white-labeling for enterprise tiers.

**Audit trail ownership.** Every signature event — document opened, field filled, signature applied, certificate generated — is logged in your database. You control retention policies, encryption standards, and backup strategies. There is no ambiguity about who can access your audit logs.

## Quick Comparison Table

| Feature | DocuSeal | OpenSign | LibreSign |
|---|---|---|---|
| **GitHub Stars** | 11,764 | 6,226 | 754 |
| **Language** | Ruby (Rails) | JavaScript (Node.js) | PHP (Nextcloud app) |
| **Database** | PostgreSQL | MongoDB | MySQL/PostgreSQL (via Nextcloud) |
| **Docker Deploy** | Single container + Postgres | 4 containers (server, client, mongo, caddy) | Nextcloud app (requires Nextcloud) |
| **PDF Form Builder** | Yes (WYSIWYG, 12 field types) | Yes (drag-and-drop) | Yes (via Nextcloud Files) |
| **Bulk Send** | Pro feature | Yes (built-in) | Via workflow plugin |
| **API** | REST + Webhooks | REST v1 | REST API |
| **Multi-Language UI** | 7 UI languages, 14 signing languages | English primary | Depends on Nextcloud |
| **White-Label** | Pro feature | Yes | Via Nextcloud theming |
| **SMS Verification** | Pro feature | Yes | Via Nextcloud integration |
| **License** | MIT | AGPL-3.0 | AGPL-3.0 |
| **Last Updated** | April 2026 | April 2026 | April 2026 |

## DocuSeal: The Single-Binary Option

DocuSeal is the most popular open-source e-signature project by star count. It ships as a single Rails application with a PostgreSQL backend, making it the simplest to deploy of the three.

### Key Features

- WYSIWYG PDF form builder with 12 field types (signature, date, file upload, checkbox, text, initials, etc.)
- Multiple submitters per document — send one form to several signers in sequence
- Mobile-optimized signing interface that works on any browser
- File storage on local disk, AWS S3, Google Cloud Storage, or Azure Blob
- SMTP integration for automated email notifications
- REST API with webhook callbacks for system integration
- PDF signature verification to validate document integrity

### Docker Deployment

DocuSeal's official `docker-compose.yml` is straightforward — one application container plus PostgreSQL:

```yaml
services:
  app:
    depends_on:
      postgres:
        condition: service_healthy
    image: docuseal/docuseal:latest
    ports:
      - "3000:3000"
    volumes:
      - ./docuseal:/data/docuseal
    environment:
      - HOST=https://sign.yourdomain.com
      - DATABASE_URL=postgresql://postgres:changeme@postgres:5432/docuseal

  postgres:
    image: postgres:18
    volumes:
      - pg_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: changeme
      POSTGRES_DB: docuseal
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  pg_data:
```

Start with:

```bash
mkdir -p docuseal && cd docuseal
# Create the docker-compose.yml file above, then:
docker compose up -d
```

The web interface becomes available at `http://localhost:3000`. For production, put a reverse proxy in front and set the `HOST` environment variable to your public URL. DocuSeal supports reverse proxies like Nginx, Caddy, or Traefik — for detailed reverse proxy configuration, see our [reverse proxy GUI guide](../nginx-proxy-manager-vs-swag-vs-caddy-docker-proxy-self-hosted-reverse-proxy-gui-guide-2026/).

## OpenSign: The Full-Stack Platform

OpenSign takes a more comprehensive approach. It ships with a separate backend server, a React frontend client, MongoDB for persistence, and a Caddy reverse proxy for TLS termination — all in one Docker Compose file.

### Key Features

- Drag-and-drop document builder with customizable field placement
- Built-in bulk sending — upload a CSV and send documents to hundreds of recipients
- Workspace and team management with role-based access control
- Template library for reusable document types (NDAs, contracts, offers)
- SMS-based signer identity verification
- Public API v1 for programmatic document creation and status tracking
- Audit trail with timestamps, IP addresses, and signer authentication events
- Caddy included for automatic HTTPS via Let's Encrypt

### Docker Deployment

OpenSign's `docker-compose.yml` orchestrates four services:

```yaml
services:
  server:
    image: opensign/opensignserver:main
    container_name: OpenSignServer-container
    volumes:
      - opensign-files:/usr/src/app/files
    ports:
      - "8080:8080"
    depends_on:
      - mongo
    env_file: .env.prod
    environment:
      - NODE_ENV=production
      - SERVER_URL=https://sign.yourdomain.com/api/app
      - PUBLIC_URL=https://sign.yourdomain.com

  mongo:
    image: mongo:latest
    container_name: mongo-container
    volumes:
      - data-volume:/data/db
    ports:
      - "27018:27017"

  client:
    image: opensign/opensign:main
    container_name: OpenSign-container
    depends_on:
      - server
    env_file: .env.prod
    ports:
      - "3000:3000"

  caddy:
    image: caddy:latest
    container_name: caddy-container
    ports:
      - "3001:3001"
      - "80:80"
      - "443:443"
      - "443:443/udp"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    environment:
      - HOST_URL=https://sign.yourdomain.com

volumes:
  data-volume:
  caddy_data:
  caddy_config:
  opensign-files:
```

The accompanying `.env.prod` file requires configuration of your `HOST_URL`, email SMTP credentials, and database connection strings. Create it before running `docker compose up -d`:

```bash
cat > .env.prod << 'ENVFILE'
HOST_URL=https://sign.yourdomain.com
NODE_ENV=production
SMTP_HOST=smtp.yourdomain.com
SMTP_PORT=587
SMTP_USERNAME=noreply@yourdomain.com
SMTP_PASSWORD=your-smtp-password
ENVFILE

docker compose up -d
```

OpenSign is the most resource-intensive option (four containers), but also the most feature-complete out of the box.

## LibreSign: The Nextcloud Integration

LibreSign is fundamentally different from the other two — it is not a standalone application but a Nextcloud app. If your organization already runs Nextcloud for file storage and collaboration, LibreSign adds e-signature capabilities directly into your existing workflow.

### Key Features

- Sign documents directly from Nextcloud Files — right-click any PDF and select "Sign"
- Deep integration with Nextcloud user management, groups, and permissions
- Workflow engine via the Nextcloud Approval app — define multi-step signing flows
- GLPI plugin for signing IT service management tickets
- REST API for external integrations
- Server-side certificate generation and management
- Runs entirely within your existing Nextcloud infrastructure

### Docker Deployment

LibreSign installs as a Nextcloud app, so you first need a running Nextcloud instance. Here is a minimal Nextcloud + LibreSign setup:

```yaml
services:
  nextcloud:
    image: nextcloud:apache
    ports:
      - "8080:80"
    volumes:
      - nextcloud_data:/var/www/html
    depends_on:
      - db

  db:
    image: mariadb:10
    volumes:
      - db_data:/var/lib/mysql
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: nextcloud
      MYSQL_USER: nextcloud
      MYSQL_PASSWORD: nextcloudpass

volumes:
  nextcloud_data:
  db_data:
```

After starting Nextcloud:

```bash
docker compose up -d

# Access Nextcloud at http://localhost:8080
# Install LibreSign via the Nextcloud app store:
# 1. Log in as admin
# 2. Go to Apps > Office & Text
# 3. Search for "LibreSign" and click Install
# 4. Enable the app and configure signing certificates in Settings
```

Alternatively, install via the command line inside the Nextcloud container:

```bash
docker exec -it nextcloud occ app:install libresign
docker exec -it nextcloud occ app:enable libresign
```

LibreSign's deployment complexity depends entirely on your existing Nextcloud setup. For organizations already running Nextcloud, adding LibreSign is a five-minute operation. For those starting from scratch, the overhead of setting up Nextcloud first makes it the heaviest option.

For related reading on document management workflows, check our [Paperless-ngx document management guide](../paperless-ngx-self-hosted-document-management-guide/) and [Stirling-PDF toolkit review](../stirling-pdf-self-hosted-pdf-toolkit-guide/).

## Resource Requirements

| Tool | Minimum RAM | Minimum CPU | Disk (per 1000 docs) |
|---|---|---|---|
| DocuSeal | 512 MB | 1 core | ~500 MB |
| OpenSign | 1 GB | 2 cores | ~1 GB |
| LibreSign (w/ Nextcloud) | 2 GB | 2 cores | ~2 GB |

DocuSeal is the lightest option and runs comfortably on a $5/month VPS. OpenSign requires more resources due to its multi-container architecture. LibreSign's footprint depends on your existing Nextcloud deployment — if you already run Nextcloud, the incremental cost is minimal.

## Which One Should You Choose?

**Choose DocuSeal if:** You want the simplest deployment with a single binary, need a clean REST API with webhooks, and prefer PostgreSQL over MongoDB. It is the easiest to get running in under five minutes and has the largest community (11,764 GitHub stars as of April 2026).

**Choose OpenSign if:** You need built-in bulk sending, team workspaces, template libraries, and SMS verification without paying for a Pro tier. Its four-container architecture is more complex but delivers the most features out of the box.

**Choose LibreSign if:** You already run Nextcloud and want signing integrated into your existing file management workflow. The tight Nextcloud integration — signing documents directly from Files, using Nextcloud user groups for access control — is unmatched by the standalone alternatives.

For teams evaluating the broader e-signature landscape, our [Documenso vs DocuSign comparison](../documenso-vs-docusign-self-hosted-esignature-guide/) covers another strong open-source contender worth considering alongside these three.

## FAQ

### Is it legal to use self-hosted e-signature platforms?

Yes. In most jurisdictions including the United States (ESIGN Act, UETA), the European Union (eIDAS regulation), and many other countries, electronic signatures carry the same legal weight as handwritten signatures. The legality depends on the signing process integrity — audit trails, signer authentication, and document tamper-proofing — not on which platform hosts the infrastructure. All three tools covered here generate audit trails and tamper-evident PDFs.

### Can self-hosted e-signature tools replace DocuSign entirely?

For most use cases, yes. DocuSeal, OpenSign, and LibreSign all support PDF form creation, multi-party signing workflows, audit logging, and email notifications. The main gaps compared to DocuSign Enterprise are advanced identity verification (government ID scanning), qualified electronic signatures under eIDAS, and certain enterprise SSO integrations. For standard contracts, NDAs, and agreements, open-source alternatives are fully capable.

### How do I set up HTTPS for my self-hosted signing server?

All three tools support HTTPS. DocuSeal and OpenSign work behind any reverse proxy (Nginx, Caddy, Traefik). OpenSign includes Caddy in its Docker Compose file, which handles TLS certificates automatically via Let's Encrypt. For a manual approach, you can use cert-manager or Let's Encrypt's `certbot` — see our [TLS certificate automation guide](../cert-manager-vs-lego-vs-acme-sh-self-hosted-tls-certificate-automation-guide-2026/) for detailed setup instructions.

### Do these platforms support bulk document sending?

OpenSign includes bulk sending as a built-in feature — upload a CSV with recipient details and send hundreds of documents at once. DocuSeal offers bulk send as a Pro (paid) feature. LibreSign can handle bulk workflows through the Nextcloud Approval app, which lets admins define multi-step signing processes, though it requires more manual setup than OpenSign's native bulk send.

### What happens to my documents if I stop using a self-hosted platform?

Since you own the infrastructure, your documents remain in your PostgreSQL, MongoDB, or Nextcloud database indefinitely. You can export them at any time. There is no vendor lock-in or account suspension risk. This is one of the primary advantages over cloud providers — if you cancel a DocuSign subscription, you lose access to your document history.

### Can I integrate these tools with my existing applications?

All three provide REST APIs. DocuSeal offers webhooks for real-time event notifications when documents are signed. OpenSign has a documented API v1 for creating envelopes, checking status, and downloading signed PDFs. LibreSign exposes a REST API through Nextcloud's framework. You can trigger signing workflows from your CRM, ERP, or custom applications programmatically.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "DocuSeal vs OpenSign vs LibreSign: Best Self-Hosted E-Signature 2026",
  "description": "Compare DocuSeal, OpenSign, and LibreSign — three open-source, self-hosted alternatives to DocuSign. Full Docker deployment guides, feature comparison, and pricing analysis for 2026.",
  "datePublished": "2026-04-24",
  "dateModified": "2026-04-24",
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
