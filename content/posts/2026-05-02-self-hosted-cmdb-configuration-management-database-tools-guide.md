---
title: "Self-Hosted CMDB: Configuration Management Database Tools — NetBox, Ralph & GLPI 2026"
date: 2026-05-02
draft: false
tags: ["cmdb", "inventory", "it-management", "asset-management", "infrastructure", "self-hosted"]
---

A Configuration Management Database (CMDB) is the central repository that stores information about your IT infrastructure — hardware, software, network devices, services, and the relationships between them. For organizations managing hundreds or thousands of assets, a self-hosted CMDB provides complete data ownership, customizable data models, and integration with your existing monitoring and automation tools.

This guide compares the top self-hosted CMDB solutions: **NetBox**, **GLPI**, and **Ralph** — covering features, deployment, and use cases.

## What Is a CMDB and Why Self-Host?

A CMDB goes beyond simple inventory management. It tracks not just what assets you have, but how they connect and depend on each other. When a switch fails, a CMDB tells you which servers, applications, and services are affected. When planning a migration, it reveals upstream and downstream dependencies.

**Self-hosting your CMDB** means:
- Full control over your infrastructure data — no third-party access
- Custom data models tailored to your environment
- Integration with internal tools via APIs without rate limits
- No per-device or per-user licensing fees
- Compliance with data sovereignty requirements

## Comparing Self-Hosted CMDB Solutions

| Feature | NetBox | GLPI | Ralph |
|---|---|---|---|
| Primary focus | IPAM + DCIM + CMDB | ITSM + Helpdesk + CMDB | IT Asset Management |
| GitHub stars | 5,000+ | 3,000+ | 1,200+ |
| Web interface | ✅ Modern UI | ✅ Full ITSM portal | ✅ Admin panel |
| REST API | ✅ Comprehensive | ✅ Full API | ✅ REST API |
| IP address management | ✅ Best-in-class | ✅ Via plugin | ✅ Basic |
| Rack/device visualization | ✅ 3D rack view | ❌ | ❌ |
| Helpdesk/ticketing | ❌ | ✅ Built-in | ❌ |
| Network discovery | ✅ Via plugins | ✅ Via FusionInventory | ✅ Via scans |
| Custom fields | ✅ Extensible | ✅ Via dropdowns | ✅ Via models |
| Docker support | ✅ Official image | ✅ Via LinuxServer.io | ✅ Official image |
| License | Apache 2.0 | GPL 3.0 | Apache 2.0 |

## Deploying NetBox as a CMDB

[NetBox](https://github.com/netbox-community/netbox) is the most popular open-source IPAM and DCIM tool, widely used as a CMDB for network and infrastructure teams. It models your entire infrastructure — from IP prefixes and VLANs to devices, circuits, and virtual machines — with full relationship tracking.

### Docker Compose Configuration

The official NetBox Docker setup includes PostgreSQL and Redis:

```yaml
services:
  netbox:
    image: netboxcommunity/netbox:latest
    depends_on:
      - netbox-postgres
      - netbox-redis
      - netbox-redis-cache
    environment:
      - SUPERUSER_API_TOKEN=your-superuser-token
      - ALLOWED_HOSTS=netbox.your-domain.com
      - DB_PASSWORD=netbox-db-password
      - REDIS_PASSWORD=netbox-redis-password
    ports:
      - "8080:8080"
    volumes:
      - netbox-media-files:/opt/netbox/netbox/media
      - netbox-reports-files:/opt/netbox/netbox/reports
      - netbox-scripts-files:/opt/netbox/netbox/scripts
    restart: unless-stopped

  netbox-postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=netbox
      - POSTGRES_PASSWORD=netbox-db-password
      - POSTGRES_DB=netbox
    volumes:
      - netbox-postgres-data:/var/lib/postgresql/data
    restart: unless-stopped

  netbox-redis:
    image: redis:7-alpine
    command:
      - sh
      - -c
      - redis-server --requirepass $$REDIS_PASSWORD
    environment:
      - REDIS_PASSWORD=netbox-redis-password
    volumes:
      - netbox-redis-data:/data
    restart: unless-stopped

  netbox-redis-cache:
    image: redis:7-alpine
    command:
      - sh
      - -c
      - redis-server --requirepass $$REDIS_PASSWORD
    environment:
      - REDIS_PASSWORD=netbox-redis-password
    volumes:
      - netbox-redis-cache-data:/data
    restart: unless-stopped

volumes:
  netbox-media-files:
  netbox-reports-files:
  netbox-scripts-files:
  netbox-postgres-data:
  netbox-redis-data:
  netbox-redis-cache-data:
```

### Initial Setup

```bash
docker compose up -d
# Access at http://your-server:8080
# Login with admin / admin (change immediately)
```

### Configuring Custom Fields for CMDB

NetBox's custom fields let you extend the data model:

```bash
# Add a custom field via the API
curl -X POST http://netbox.your-domain.com/api/extras/custom-fields/ \
  -H "Authorization: Token $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content_types": ["dcim.device"],
    "type": "text",
    "name": "environment",
    "label": "Environment",
    "description": "Production, staging, or development",
    "required": true,
    "weight": 100
  }'
```

## Deploying GLPI as an ITSM CMDB

[GLPI](https://github.com/glpi-project/glpi) is a full IT service management platform with a built-in CMDB. It combines asset management, helpdesk, license tracking, and project management in a single application.

### Docker Compose Configuration

```yaml
services:
  glpi:
    image: elestio/glpi:latest
    container_name: glpi
    ports:
      - "8080:80"
    environment:
      - TIMEZONE=Europe/Paris
      - GLPI_MYSQL_HOST=mysql
      - GLPI_MYSQL_USER=glpi
      - GLPI_MYSQL_PASSWORD=glpi-password
      - GLPI_MYSQL_DBNAME=glpi
    volumes:
      - glpi-data:/var/www/html/glpi
    depends_on:
      - mysql
    restart: unless-stopped

  mysql:
    image: mysql:8.0
    container_name: glpi-mysql
    environment:
      - MYSQL_ROOT_PASSWORD=root-password
      - MYSQL_DATABASE=glpi
      - MYSQL_USER=glpi
      - MYSQL_PASSWORD=glpi-password
    volumes:
      - mysql-data:/var/lib/mysql
    restart: unless-stopped

volumes:
  glpi-data:
  mysql-data:
```

### Installing the FusionInventory Plugin

For automatic network discovery and inventory:

```bash
# Download and install the plugin
cd /tmp
wget https://github.com/fusioninventory/fusioninventory-for-glpi/releases/latest/download/fusioninventory-glpi.tar.gz
tar -xzf fusioninventory-glpi.tar.gz -C /var/www/html/glpi/plugins/
# Activate in GLPI: Setup → Plugins → Install and Activate
```

### Setting Up the CMDB Inventory

1. Navigate to **Assets → Computers** to add your first asset
2. Configure **Network Discovery** rules under **Administration → Rules**
3. Set up **Automatic Inventory** via the FusionInventory agent on endpoints
4. Define **Relationships** between assets (e.g., a server runs on a specific hypervisor)

## Deploying Ralph for IT Asset Management

[Ralph](https://github.com/allegro/ralph) is an asset management and CMDB system designed for data centers and IT departments. It focuses on hardware lifecycle management, procurement tracking, and license management.

### Docker Compose Configuration

```yaml
services:
  ralph:
    image: allegro/ralph:latest
    container_name: ralph
    ports:
      - "8000:8000"
    environment:
      - RALPH_DB_HOST=mysql
      - RALPH_DB_USER=ralph
      - RALPH_DB_PASSWORD=ralph-password
      - RALPH_DB_NAME=ralph
      - RALPH_ADMIN_USER=admin
      - RALPH_ADMIN_PASSWORD=admin-password
    depends_on:
      - mysql
    volumes:
      - ralph-media:/var/local/ralph
    restart: unless-stopped

  mysql:
    image: mysql:8.0
    container_name: ralph-mysql
    environment:
      - MYSQL_ROOT_PASSWORD=root-password
      - MYSQL_DATABASE=ralph
      - MYSQL_USER=ralph
      - MYSQL_PASSWORD=ralph-password
    volumes:
      - mysql-data:/var/lib/mysql
    restart: unless-stopped

volumes:
  ralph-media:
  mysql-data:
```

### Importing Existing Assets

Ralph supports CSV import for bulk asset onboarding:

```bash
# Export current inventory to CSV template
docker compose exec ralph ralphctl export --format csv > inventory_template.csv

# Fill in your assets and import
docker compose exec ralph ralphctl import --format csv < populated_inventory.csv
```

## Choosing the Right CMDB for Your Organization

**Choose NetBox if:**
- You need best-in-class IP address management and network documentation
- Your team is network/infrastructure focused
- You need API-first integration with automation tools (Ansible, Terraform)
- You want rack-level data center visualization

**Choose GLPI if:**
- You need a full ITSM platform (helpdesk + CMDB in one)
- You manage IT assets across multiple departments
- You need license management and contract tracking
- Your organization follows ITIL processes

**Choose Ralph if:**
- Your primary need is hardware lifecycle and procurement tracking
- You want a simple, focused asset management system
- You need cost tracking and depreciation calculations
- You prefer a lightweight system without ITSM overhead

## Why Maintain a Self-Hosted CMDB?

**Single Source of Truth** — A CMDB consolidates infrastructure data that would otherwise live in spreadsheets, monitoring tools, and people's heads. When an incident occurs, responders can immediately see what's affected.

**Change Impact Analysis** — Before modifying a network device or retiring a server, a CMDB reveals all dependent services. This prevents outages caused by undocumented dependencies.

**Compliance and Auditing** — Regulatory frameworks (SOC 2, ISO 27001, PCI DSS) require documented asset inventories. A self-hosted CMDB provides an auditable, version-controlled record of your entire infrastructure.

**Cost Optimization** — By tracking hardware lifecycles, software licenses, and cloud resource assignments, a CMDB helps identify underutilized assets and upcoming renewals.

For related infrastructure management guides, see our [IPAM comparison: phpIPAM vs NIPAP vs NetBox](../2026-04-20-phpipam-vs-nipap-vs-netbox-self-hosted-ipam-guide-2026/) and [IT asset management: Snipe-IT vs InvenTree vs PartKeepr](../snipe-it-vs-inventree-vs-partkeepr-self-hosted-inventory-guide-2026/).

## FAQ

### What is the difference between a CMDB and an asset inventory?

An asset inventory lists what you own (laptops, servers, licenses) and their basic attributes. A CMDB goes further by modeling relationships and dependencies between assets — which application runs on which server, which network switch connects to which firewall, and which business service depends on which infrastructure component. CMDBs support impact analysis, change management, and root cause investigation in ways that simple inventories cannot.

### Should I use NetBox or GLPI for my CMDB?

Use NetBox if your focus is network infrastructure, IP address management, and data center documentation. NetBox excels at modeling physical and virtual network topology. Use GLPI if you need a broader ITSM platform that combines CMDB with helpdesk, procurement, license management, and project tracking. GLPI is better suited for IT departments that need end-to-end service management.

### Can I integrate my CMDB with monitoring tools?

Yes. All three tools (NetBox, GLPI, Ralph) provide REST APIs for integration. NetBox is particularly popular with monitoring stacks — Prometheus can pull IP and device data, Ansible can use NetBox as an inventory source, and tools like PRTG and Zabbix can import network topology. GLPI integrates with monitoring via its FusionInventory plugin, which can automatically discover and inventory network devices.

### How do I keep my CMDB data accurate and up to date?

The biggest challenge with any CMDB is data freshness. Best practices include: (1) Automate discovery using agents (FusionInventory for GLPI) or network scanning (Nmap integrations for NetBox). (2) Integrate with your provisioning system so new assets are automatically registered. (3) Implement change management processes that require CMDB updates before any infrastructure change. (4) Run periodic reconciliation audits comparing the CMDB against actual network state.

### Is a self-hosted CMDB suitable for small teams?

For teams managing fewer than 50 devices, a spreadsheet may suffice. But even small teams benefit from a CMDB once they manage multiple services, cloud instances, and network devices. NetBox is lightweight enough for small deployments (runs on 1 GB RAM) and provides immediate value for IP address tracking alone. GLPI's helpdesk features make it valuable even for teams of 5-10 people managing shared IT resources.

### How much does it cost to self-host a CMDB?

All three tools discussed (NetBox, GLPI, Ralph) are free and open source. Infrastructure costs depend on scale: a small NetBox instance runs on a $5/month VPS with 1 GB RAM. GLPI requires slightly more resources (2 GB RAM recommended) due to its full ITSM feature set. For organizations with 1,000+ assets, plan for 4 GB RAM and a dedicated database server. Compare this to commercial CMDB platforms (ServiceNow, BMC Helix) that cost tens of thousands of dollars annually.

## CMDB Implementation Checklist

1. **Define your data model** — What asset types, relationships, and custom fields do you need?
2. **Choose your platform** — NetBox for network focus, GLPI for full ITSM, Ralph for asset lifecycle
3. **Deploy with Docker** — Use the compose configurations above for reproducible deployments
4. **Import existing inventory** — Start with a CSV import of your current assets
5. **Set up network discovery** — Configure automated scanning to keep data fresh
6. **Integrate with monitoring** — Connect your CMDB to Prometheus, Zabbix, or Nagios
7. **Train your team** — Establish processes for updating the CMDB during changes
8. **Schedule regular audits** — Verify CMDB accuracy against actual infrastructure quarterly

<script type="application/ld+json">
{
  "@context": "https://www.schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted CMDB: Configuration Management Database Tools — NetBox, Ralph & GLPI 2026",
  "description": "Compare self-hosted CMDB solutions — NetBox, GLPI, and Ralph — with Docker Compose deployment guides for infrastructure and asset management.",
  "datePublished": "2026-05-02",
  "dateModified": "2026-05-02",
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
