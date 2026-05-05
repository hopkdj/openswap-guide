---
title: "Self-Hosted IT Asset Discovery: OCS Inventory NG vs FusionInventory vs GLPI Agent 2026"
date: 2026-05-08T10:00:00+00:00
tags: ["inventory", "asset-management", "monitoring", "agent-based", "ocs-inventory", "glpi", "fusioninventory"]
draft: false
---

Managing an IT infrastructure of any size requires accurate, up-to-date knowledge of every device on your network. Manual spreadsheets quickly become obsolete the moment a new laptop joins or a server gets upgraded. Agent-based IT asset discovery tools automate this process, continuously scanning hardware configurations, installed software, and network connections — giving IT teams a real-time view of their entire fleet.

This guide compares three mature, open-source IT asset discovery platforms: **OCS Inventory NG**, **FusionInventory**, and the **GLPI Inventory Agent**. Each uses a lightweight agent installed on managed endpoints to collect hardware and software inventory data, then reports back to a central management server.

## Understanding Agent-Based IT Asset Discovery

Unlike network scanners that passively probe devices, agent-based discovery tools install a lightweight client on each managed machine. The agent collects detailed system information — CPU, RAM, disk partitions, installed packages, running services, network interfaces, USB devices, and more — then sends it to a central server on a configurable schedule.

**Key advantages of agent-based discovery:**

- **Deep system visibility**: Agents run with local privileges, collecting data that remote scans cannot access (registry entries, installed software versions, license keys)
- **Low network overhead**: Data is compressed and sent in batch, reducing bandwidth compared to continuous network scanning
- **Cross-platform support**: Agents exist for Windows, Linux, macOS, Android, and BSD
- **Historical tracking**: Changes over time are recorded, enabling audit trails and compliance reporting

## OCS Inventory NG

[OCS Inventory NG](https://ocsinventory-ng.org/) (Open Computers and Software Inventory Next Generation) is one of the oldest and most widely deployed open-source asset discovery tools. Originally created in 2001, it has evolved into a mature platform with over 395 GitHub stars and an active community.

**Architecture**: OCS Inventory uses a three-tier architecture:
1. **Agent** — collects hardware/software data from endpoints
2. **Communication Server** — receives agent reports (Apache/MySQL/PHP stack)
3. **Administration Console** — web-based UI for viewing and managing inventory

### Docker Deployment

OCS Inventory provides an official Docker Compose deployment:

```yaml
version: '3'
services:
  web:
    image: ocsinventory/ocsinventory-docker-image:latest
    container_name: ocsinventory-server
    environment:
      OCS_DBNAME: ocsweb
      OCS_DBSERVER_READ: ocsinventory-db
      OCS_DBSERVER_WRITE: ocsinventory-db
      OCS_DBUSER: ocs
      OCS_DBPASS: ocs
    volumes:
      - ocsdownload:/usr/share/ocsinventory-reports/ocsreports/download/
      - ocssrv:/etc/ocsinventory-reports/
      - ocslib:/var/lib/ocsinventory-reports/
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - db

  db:
    image: mysql:5.7
    container_name: ocsinventory-db
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_USER: ocs
      MYSQL_PASSWORD: ocs
      MYSQL_DATABASE: ocsweb
    volumes:
      - dbdata:/var/lib/mysql

volumes:
  dbdata:
  ocsdownload:
  ocssrv:
  ocslib:
```

Deploy with:

```bash
docker compose up -d
```

### Agent Installation

**Linux (Debian/Ubuntu):**
```bash
apt install ocsinventory-agent
# Configure server URL in /etc/ocsinventory/ocsinventory-agent.cfg
```

**Windows:** Download the MSI installer from the OCS Inventory website, specify the server URL during installation.

**macOS:** Use Homebrew or download the .pkg installer:
```bash
brew install ocsinventory-agent
```

### Key Features

- Automatic hardware inventory with detailed component detection
- Software license tracking and compliance reporting
- Network discovery (SNMP-based) for switches, printers, and NAS devices
- Deployment engine for software packages and scripts
- REST API for integration with CMDB and ticketing systems
- Plugin system for extending data collection

## FusionInventory

[FusionInventory](https://fusioninventory.org/) started as a fork of OCS Inventory NG, designed to integrate natively with GLPI (IT Service Management). It adds network discovery capabilities and improves the agent's flexibility with local tasks execution.

**Architecture**: FusionInventory consists of:
1. **Agent** — standalone or GLPI-integrated, supports local task execution
2. **Server Plugin** — runs inside GLPI, receives and processes agent data
3. **Network Discovery** — SNMP-based scanning for network devices

### Docker Deployment

FusionInventory runs as a GLPI plugin. Deploy GLPI with Docker:

```yaml
version: '3'
services:
  glpi:
    image: glpi/glpi:10.0
    container_name: glpi-fusioninventory
    environment:
      TIMEZONE: Europe/Paris
    volumes:
      - glpi_files:/var/www/html/glpi/files
      - glpi_config:/etc/glpi
    ports:
      - "8080:80"
    depends_on:
      - db

  db:
    image: mariadb:10.6
    container_name: glpi-db
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: glpi
      MYSQL_USER: glpi
      MYSQL_PASSWORD: glpipass
    volumes:
      - dbdata:/var/lib/mysql

volumes:
  dbdata:
  glpi_files:
  glpi_config:
```

After GLPI is running, install the FusionInventory plugin through GLPI's marketplace.

### Agent Configuration

```bash
# Install FusionInventory agent
apt install fusioninventory-agent

# Configure server URL
echo "server = http://glpi-server/plugins/fusioninventory/" > /etc/ocsinventory/ocsinventory-agent.cfg

# Run inventory
fusioninventory-agent
```

### Key Features

- Deep GLPI integration — inventory automatically populates GLPI's CMDB
- Network discovery and SNMP inventory for switches, routers, printers
- Local task execution — agents can run deployment tasks independently
- ESX virtualization inventory — discovers VMware hosts and VMs
- Wake-on-LAN support for remote power management
- Software deployment engine with package scheduling

## GLPI Inventory Agent

The **GLPI Inventory Agent** (formerly FusionInventory Agent, rebranded in GLPI 10) is the native inventory agent for GLPI IT Service Management. GLPI 10 incorporated inventory capabilities directly, reducing the need for separate plugins.

[GLPI](https://glpi-project.org/) is a full ITSM platform with ticketing, asset management, knowledge base, and project management — with inventory as one core component.

### Docker Deployment

```yaml
version: '3'
services:
  glpi:
    image: glpi/glpi:10.0
    container_name: glpi-inventory
    environment:
      TIMEZONE: UTC
    volumes:
      - glpi_data:/var/www/html/glpi/files
    ports:
      - "8080:80"
    depends_on:
      - db

  db:
    image: mariadb:10.11
    container_name: glpi-inventory-db
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: glpi
      MYSQL_USER: glpi
      MYSQL_PASSWORD: glpipass
    volumes:
      - dbdata:/var/lib/mysql

volumes:
  dbdata:
  glpi_data:
```

### Native Inventory (GLPI 10+)

GLPI 10+ has built-in inventory capabilities. No separate plugin needed:

```bash
# Install the GLPI agent
apt install glpi-agent

# Configure
glpi-agent --server=http://glpi-server/glpi/front/inventory.php

# Run inventory
glpi-agent --local
```

### Key Features

- Native GLPI integration — inventory data feeds directly into asset management
- ITSM workflow — auto-create tickets for hardware changes or software violations
- Contract and license management — track warranty expirations and software licenses
- Knowledge base integration — link inventory items to troubleshooting articles
- Financial management — track purchase costs, depreciation, and budget allocation
- Multi-entity support — manage separate organizations within one installation

## Comparison Table

| Feature | OCS Inventory NG | FusionInventory | GLPI Inventory Agent |
|---------|------------------|-----------------|---------------------|
| **GitHub Stars** | 395 | 265 | 13,733 (GLPI) |
| **Last Update** | April 2026 | August 2023 | May 2026 |
| **Primary Focus** | Asset discovery | Network + asset discovery | Full ITSM with inventory |
| **Docker Support** | Official compose | Via GLPI Docker image | Official GLPI Docker image |
| **Agent Platforms** | Windows, Linux, macOS, Android, BSD | Windows, Linux, macOS, BSD | Windows, Linux, macOS, BSD |
| **Network Discovery** | SNMP-based | SNMP + ESX | SNMP-based |
| **Software Deployment** | Yes | Yes | Limited (via GLPI plugins) |
| **REST API** | Yes | Via GLPI API | Yes |
| **Ticketing Integration** | Via plugins | Native (GLPI) | Native |
| **License Compliance** | Basic | Advanced | Advanced |
| **Multi-entity** | No | Yes (via GLPI) | Yes |
| **Database** | MySQL | MariaDB | MariaDB |
| **Web UI** | Dedicated console | GLPI interface | GLPI interface |

## Which Should You Choose?

**Choose OCS Inventory NG if:**
- You need a dedicated, standalone asset discovery tool
- You want the most mature agent with the broadest platform support
- You don't need ITSM features (ticketing, project management)
- You prefer a lightweight, focused solution

**Choose FusionInventory if:**
- You already use GLPI and want inventory integrated with your ITSM
- You need network discovery alongside agent-based inventory
- You want ESX virtualization inventory
- You need advanced software deployment capabilities

**Choose GLPI Inventory Agent if:**
- You want a complete ITSM platform with inventory as one component
- You need ticketing, asset management, and knowledge base in one tool
- You prefer active development (GLPI 10+ has native inventory)
- You manage multiple organizations/entities

## Why Self-Host Your IT Asset Discovery?

Cloud-based asset management tools require sending your complete hardware and software inventory to a third-party server. For organizations with compliance requirements (GDPR, HIPAA, SOC 2), this data transfer creates legal and security risks. Self-hosted asset discovery keeps all inventory data within your infrastructure.

For organizations managing large fleets, self-hosted tools also eliminate per-device licensing costs. Commercial alternatives like Lansweyer, SCCM, or Jamf charge per-endpoint fees that scale quickly. Open-source tools like OCS Inventory and GLPI are free regardless of fleet size.

For [IT inventory management with component-level tracking](../snipe-it-vs-inventree-vs-partkeepr-self-hosted-inventory-guide-2026/), our comparison of Snipe-IT vs InvenTree vs PartKeepr covers dedicated inventory platforms. If you need [IP address management alongside asset tracking](../2026-04-20-phpipam-vs-nipap-vs-netbox-self-hosted-ipam-guide-2026/), the phpIPAM vs NIPAP vs NetBox guide covers network-focused inventory.

## FAQ

### What is the difference between agent-based and network-based IT asset discovery?

Agent-based discovery installs a lightweight client on each managed device that collects detailed system information (hardware specs, installed software, running services) and reports to a central server. Network-based discovery uses SNMP, WMI, or SSH to remotely scan devices. Agent-based methods provide deeper visibility (registry entries, local software installations) but require agent deployment on every endpoint.

### Can OCS Inventory NG manage software deployments?

Yes, OCS Inventory NG includes a deployment engine that can push software packages, scripts, and updates to managed endpoints. You can schedule deployments, target specific groups of machines, and track installation status through the web console.

### Is FusionInventory still actively maintained?

FusionInventory's last major update was in August 2023. However, its functionality has been largely incorporated into GLPI 10+, which has native inventory capabilities and continues active development. For new deployments, GLPI 10+ with its native inventory agent is the recommended path.

### How many endpoints can OCS Inventory NG handle?

OCS Inventory NG can manage tens of thousands of endpoints. The architecture supports load balancing the communication server, and the MySQL database can be scaled independently. Large deployments typically use a reverse proxy (Nginx, HAProxy) in front of multiple OCS communication servers.

### Does GLPI Inventory Agent work without the full GLPI platform?

No, the GLPI Inventory Agent requires a GLPI server to receive and process inventory data. However, you can use GLPI primarily for inventory and disable features you don't need (ticketing, project management, etc.). GLPI is modular, so you can enable only the inventory and asset management components.

### How often do agents send inventory data?

By default, most agents run daily. The schedule is configurable — you can set agents to report hourly, daily, weekly, or on a custom cron schedule. OCS Inventory NG agents can also be triggered manually or by the server.

### Can these tools track software licenses?

Yes, all three tools track installed software and can compare installations against purchased licenses. GLPI has the most advanced license management with contract tracking, warranty management, and financial reporting. OCS Inventory NG provides basic license tracking through its software inventory.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted IT Asset Discovery: OCS Inventory NG vs FusionInventory vs GLPI Agent 2026",
  "description": "Compare open-source agent-based IT asset discovery tools: OCS Inventory NG, FusionInventory, and GLPI Inventory Agent. Docker deployment, agent installation, and feature comparison.",
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
