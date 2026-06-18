---
title: "Self-Hosted IT Asset & Documentation Platforms: Shelf vs ITFlow vs GLPI Compared"
date: "2026-06-18"
tags: ["it-asset-management", "it-documentation", "msp", "itsm", "self-hosted", "devops", "sysadmin"]
draft: false
---

## Introduction

Managed Service Providers (MSPs) and internal IT teams face a common challenge: tracking hardware assets, documenting client environments, and maintaining operational knowledge — all without relying on expensive SaaS platforms like IT Glue or Hudu.

Open-source alternatives have matured significantly. **Shelf** (2,646 ⭐), **ITFlow** (944 ⭐), and **GLPI** (4,500+ ⭐) each approach IT asset and documentation management differently. This guide compares all three and shows you how to deploy them in your environment.

## Why Self-Host Your IT Documentation?

IT teams handle sensitive information — network diagrams, credentials, client configurations, and asset inventories. Storing this in a third-party cloud service creates risk:

- **Data sovereignty** — Your documentation stays on your infrastructure
- **No subscription costs** — IT Glue starts at $29/user/month; self-hosted is free
- **Custom integrations** — Connect directly to your monitoring, ticketing, and RMM tools
- **Client trust** — MSP clients increasingly demand data residency guarantees

For complementary IT infrastructure management, see our [self-hosted network monitoring guide](../2026-04-25-nagios-vs-icinga-vs-cacti-self-hosted-infrastructure-monitoring-guide-2026/) and [configuration management comparison](../2026-04-18-self-hosted-ansible-awx-vs-semaphore-vs-rundeck/).

## Feature Comparison

| Feature | Shelf | ITFlow | GLPI |
|---------|-------|--------|------|
| **Primary focus** | Asset lifecycle & scheduling | MSP PSA (billing, clients) | ITSM (tickets, inventory) |
| **Stars** | 2,646 | 944 | 4,500+ |
| **Language** | TypeScript (Remix) | PHP | PHP |
| **Database** | PostgreSQL | MySQL/MariaDB | MySQL/MariaDB |
| **Asset tracking** | ✅ QR codes, bookings | ✅ Client assets | ✅ Full CMDB |
| **Ticketing** | ❌ | ✅ Basic | ✅ Full ITSM |
| **Billing/invoicing** | ❌ | ✅ Stripe/PayPal | ❌ (plugin) |
| **Client portal** | ❌ | ✅ | ✅ Self-service |
| **Knowledge base** | ❌ | ✅ Documentation | ✅ FAQ/knowledge |
| **API** | REST API | REST API | REST API |
| **Docker support** | ✅ Official | ✅ Community | ✅ Official |
| **SSO/LDAP** | ✅ | ✅ | ✅ |
| **Mobile-friendly** | ✅ PWA | ✅ Responsive | ✅ Responsive |

## Deploying Shelf

Shelf is a modern IT asset management platform with equipment booking, QR code labeling, and team collaboration features.

```yaml
# docker-compose.yml
version: "3.8"
services:
  shelf:
    image: ghcr.io/shelf-nu/shelf:latest
    container_name: shelf
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://shelf:shelf_pass@db:5432/shelf
      - SESSION_SECRET=your-secure-random-secret-here
      - SMTP_HOST=smtp.yourcompany.com
      - SMTP_PORT=587
      - SMTP_USER=noreply@yourcompany.com
      - SMTP_PASS=your-smtp-password
      - APP_URL=https://shelf.yourcompany.com
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    container_name: shelf-db
    environment:
      - POSTGRES_USER=shelf
      - POSTGRES_PASSWORD=shelf_pass
      - POSTGRES_DB=shelf
    volumes:
      - shelf_db:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  shelf_db:
```

```bash
# Start Shelf
docker compose up -d

# Run database migrations
docker compose exec shelf npx prisma migrate deploy

# Access at http://localhost:3000
```

### Key Shelf Features

- **QR code asset labels** — Print and attach QR codes to equipment; scan to check in/out
- **Equipment booking** — Reserve laptops, projectors, and tools for specific time slots
- **Asset depreciation tracking** — Track purchase value and current worth over time
- **Team workspaces** — Separate assets by department or client
- **Custom fields** — Add organization-specific metadata to any asset type

## Deploying ITFlow

ITFlow is designed specifically for MSPs — it combines client management, ticketing, invoicing, and documentation in one platform.

```yaml
# docker-compose.yml
version: "3.8"
services:
  itflow:
    image: itflow/itflow:latest
    container_name: itflow
    ports:
      - "8080:80"
    environment:
      - MYSQL_HOST=db
      - MYSQL_DATABASE=itflow
      - MYSQL_USER=itflow
      - MYSQL_PASSWORD=itflow_pass
      - BASE_URL=https://itflow.yourcompany.com
    volumes:
      - itflow_uploads:/var/www/html/uploads
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: mariadb:11
    container_name: itflow-db
    environment:
      - MYSQL_ROOT_PASSWORD=root_pass
      - MYSQL_DATABASE=itflow
      - MYSQL_USER=itflow
      - MYSQL_PASSWORD=itflow_pass
    volumes:
      - itflow_db:/var/lib/mysql
    restart: unless-stopped

volumes:
  itflow_uploads:
  itflow_db:
```

```bash
# Start ITFlow
docker compose up -d

# Complete web-based setup at http://localhost:8080
```

### Key ITFlow Features

- **Client management** — Track client contacts, sites, and contracts
- **Ticketing system** — Built-in help desk with email-to-ticket
- **Invoicing** — Generate and track invoices with Stripe/PayPal integration
- **Documentation** — Per-client knowledge base for configurations and procedures
- **Accounting** — Basic expense tracking and profit/loss reporting
- **Calendar** — Schedule on-site visits and maintenance windows

## Deploying GLPI

GLPI (Gestionnaire Libre de Parc Informatique) is the veteran of the group — a full-featured ITSM platform used by enterprises worldwide.

```yaml
# docker-compose.yml
version: "3.8"
services:
  glpi:
    image: diouxx/glpi:latest
    container_name: glpi
    ports:
      - "8081:80"
    environment:
      - GLPI_LANG=en_GB
      - VERSION=10.0
    volumes:
      - glpi_data:/var/www/html/glpi
    restart: unless-stopped

  glpi-db:
    image: mariadb:11
    container_name: glpi-db
    environment:
      - MYSQL_ROOT_PASSWORD=glpi_root
      - MYSQL_DATABASE=glpi
      - MYSQL_USER=glpi
      - MYSQL_PASSWORD=glpi_pass
    volumes:
      - glpi_db:/var/lib/mysql
    restart: unless-stopped

volumes:
  glpi_data:
  glpi_db:
```

Complete the web-based installation at `http://localhost:8081`.

## Choosing the Right Platform

**Choose Shelf if:**
- Your primary need is asset lifecycle management
- You need equipment booking and check-in/check-out
- You want a modern, clean interface with QR code support
- You're managing hardware across multiple locations

**Choose ITFlow if:**
- You're an MSP needing PSA functionality (ticketing + billing + clients)
- You need invoice generation and payment tracking
- You want per-client documentation portals
- You need an all-in-one solution for small to medium MSP operations

**Choose GLPI if:**
- You need enterprise-grade ITSM with full CMDB
- You require SLA management and advanced ticketing workflows
- You manage thousands of assets across multiple sites
- You need plugin extensibility (there are hundreds of GLPI plugins)

## Why Self-Host Your MSP Stack?

MSPs handle sensitive client data — network topologies, admin credentials, and infrastructure configurations. Self-hosting keeps this data off third-party servers. For MSPs managing client environments, also see our [remote access and monitoring guide](../2026-04-24-tactical-rmm-vs-meshcentral-vs-openrmm-self-hosted-remote-monitoring/). For helpdesk-specific comparisons, check our [self-hosted helpdesk guide](../self-hosted-helpdesk-zammad-freescout-osticket/).

## Migration Planning and Data Import

### Migrating from Commercial Tools

Moving from IT Glue, Hudu, or ServiceNow requires careful planning. Here's a practical approach:

**Step 1: Export from your current platform.** IT Glue exports to CSV and PDF. Hudu provides API access for data extraction. ServiceNow has built-in export tools.

**Step 2: Map data fields.** Create a spreadsheet mapping source fields to target fields. For Shelf, focus on asset attributes (serial number, purchase date, assigned user). For ITFlow, map client contacts, contracts, and documentation categories.

**Step 3: Use API or CSV import.** Shelf's REST API accepts JSON payloads for bulk asset creation. ITFlow has a CSV import module for clients. GLPI supports CSV imports through its web interface.

**Step 4: Validate imported data.** Spot-check 5% of imported records against the original source. Verify relationships (asset-to-user assignments, client-to-contract links) are preserved.

### Maintaining Accuracy Over Time

IT documentation decays rapidly. Without maintenance, documentation becomes inaccurate within 3-6 months. Establish these practices:

- **Quarterly audits**: Verify asset inventory against physical counts
- **Automated discovery**: Use network scanning tools to detect new devices automatically
- **Change management integration**: Require documentation updates as part of change request closure
- **Client reviews**: For MSPs, schedule quarterly documentation reviews with clients

### Scaling for Enterprise Use

For organizations managing 10,000+ assets:

- **GLPI** scales best — its mature database schema handles large datasets efficiently
- **Shelf** works well for 1,000-5,000 assets with the recommended hardware
- **ITFlow** is designed for MSPs with dozens of clients, each with hundreds of assets

All three support database replication for high availability. For critical documentation, set up automated database backups as described in our [PostgreSQL backup guide](../pgbackrest-vs-barman-vs-wal-g-self-hosted-postgresql-backup-guide-2026/).

## Deployment Architecture for MSPs

For MSPs managing multiple clients, consider a tiered architecture:

- **Central ITFlow instance** for billing, ticketing, and client management
- **Per-client Shelf instances** for asset tracking at each client site
- **GLPI as the central CMDB** for aggregating asset data across all clients

Use the REST APIs to sync data between platforms. For example, when ITFlow creates a new client, automatically provision a Shelf workspace and sync basic asset records from GLPI.

This architecture gives you financial management (ITFlow), operational asset tracking (Shelf), and enterprise configuration management (GLPI) in a cohesive stack.

## FAQ

### Can Shelf, ITFlow, and GLPI integrate with each other?

Not directly, but you can use their REST APIs to build custom integrations. For example, sync GLPI assets to Shelf for QR code tracking, or push ITFlow tickets to GLPI for SLA monitoring. REST API documentation is available for each platform.

### How do these compare to IT Glue or Hudu?

IT Glue and Hudu are SaaS-only with per-user pricing ($29-39/user/month). They offer polished documentation features but lock your data in their cloud. Self-hosted alternatives give you full data control and eliminate recurring costs, though they require more initial setup time.

### What about mobile access?

All three platforms have responsive web interfaces that work on mobile browsers. Shelf has the best mobile experience with its PWA support and QR code scanning. GLPI offers a companion mobile app. ITFlow is fully responsive but lacks a dedicated mobile app.

### Which has the best security model?

All three support role-based access control, LDAP/SSO integration, and HTTPS. Shelf uses modern web security practices (CSP headers, session management). GLPI has the most mature security track record with 20+ years of development. ITFlow handles financial data so it includes audit logging for billing actions.

### Can I migrate from IT Glue or Hudu?

Each platform provides import tools. GLPI has CSV import for assets. ITFlow supports client import via CSV. Shelf has a REST API for programmatic data loading. Plan for a manual migration phase — there's no one-click importer from commercial alternatives.

### How resource-intensive are these platforms?

Shelf (Node.js/PostgreSQL) needs 1GB RAM minimum. ITFlow (PHP/MySQL) runs on 512MB. GLPI (PHP/MySQL) needs 1GB RAM for production use. All three run comfortably on a $20/month VPS for small teams.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted IT Asset & Documentation Platforms: Shelf vs ITFlow vs GLPI Compared",
  "description": "Compare open-source IT asset management and documentation platforms. Covers Shelf (modern asset tracking), ITFlow (MSP PSA with billing), and GLPI (enterprise ITSM) with Docker deployment guides.",
  "datePublished": "2026-06-18",
  "dateModified": "2026-06-18",
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
