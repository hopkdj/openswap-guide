---
title: "Request Tracker vs Znuny vs iTop: Self-Hosted ITSM & Ticketing Systems 2026"
date: 2026-04-30
tags: ["comparison", "guide", "self-hosted", "itsm", "ticketing", "helpdesk"]
draft: false
description: "Compare three open-source ITSM platforms — Request Tracker, Znuny, and iTop — for self-hosted ticketing, incident management, and CMDB. Includes Docker deployment guides and feature comparisons."
---

## Why Self-Host Your ITSM Platform?

IT Service Management (ITSM) platforms are the backbone of IT operations — they handle incident tracking, change management, asset inventory, and service catalogs. While commercial SaaS options like ServiceNow, Jira Service Management, and Freshservice dominate the market, self-hosted open-source alternatives give organizations full control over their data, unlimited users without per-seat pricing, and the ability to customize every workflow.

For teams in regulated industries (healthcare, finance, government), self-hosting ITSM tools keeps sensitive incident data, asset inventories, and change records on-premises. For budget-conscious organizations, open-source ITSM eliminates the steep per-agent licensing costs that can reach $100+/agent/month with commercial platforms.

This guide compares three mature, actively maintained open-source ITSM platforms: **Request Tracker** (the industry veteran), **Znuny** (the community-driven OTRS fork), and **iTop** (the CMDB-centric ITSM tool). All three offer web-based interfaces, email integration, and extensible architectures — but they differ significantly in philosophy, technology stack, and use-case fit.

## Quick Comparison

| Feature | Request Tracker 6.0 | Znuny 7.3 | iTop 3.2 |
|---|---|---|---|
| **Language** | Perl | Perl | PHP |
| **Database** | MySQL, PostgreSQL, Oracle | MySQL, PostgreSQL | MySQL, MariaDB |
| **License** | GPL v2 | GPL v2 | AGPL v3 |
| **Latest Release** | 6.0.2 (Oct 2025) | 7.3.2 (2025) | 3.2.3 (Apr 2026) |
| **GitHub Stars** | 1,112 | 556 | 1,107 |
| **CMDB** | Limited (via extensions) | Limited (via extensions) | Built-in (core feature) |
| **ITIL Processes** | Incident, Problem, Change | Incident, Problem, Change, SLA | Incident, Problem, Change, Config, SLA |
| **REST API** | Yes | Yes | Yes |
| **Email Integration** | IMAP/POP3/SMTP (built-in) | IMAP/POP3/SMTP (built-in) | IMAP/POP3/SMTP (built-in) |
| **Docker Support** | Community images | Community images | Community images |
| **Multi-Tenancy** | Yes (via RTIR) | Yes (via OTRS::ITSM) | Yes (built-in) |
| **SLA Management** | Via extensions | Built-in | Built-in |
| **Knowledge Base** | Via extensions | Built-in | Built-in |
| **Portal/End-User UI** | Basic | Advanced | Advanced |

## Request Tracker (RT)

[Request Tracker](https://bestpractical.com/rt/) is the oldest and most established open-source ticketing system, developed by Best Practical Solutions since 2001. It is widely used by universities, government agencies, and enterprises worldwide.

### Key Strengths

- **Mature and stable**: 25+ years of development, deployed in thousands of organizations
- **Powerful queue management**: Custom queues with unique workflows, permissions, and templates
- **Scrips system**: Event-driven automation (triggers + actions + conditions) for complex workflows
- **Custom fields**: Extensible ticket metadata with field-level permissions
- **Strong email integration**: Bidirectional email-ticket correlation with full MIME support
- **RTIR extension**: Incident Response module for security team workflows

### Architecture

RT runs as a Perl application behind a web server (Apache or nginx) using FastCGI. It requires a relational database backend and integrates with LDAP/Active Directory for authentication.

### Docker Deployment

Here is a Docker Compose configuration for running Request Tracker with a MySQL backend:

```yaml
version: "3.8"

services:
  rt-db:
    image: mysql:8.0
    container_name: rt-db
    environment:
      MYSQL_ROOT_PASSWORD: rt_root_pass
      MYSQL_DATABASE: rtdb
      MYSQL_USER: rt_user
      MYSQL_PASSWORD: rt_db_pass
    volumes:
      - rt-db-data:/var/lib/mysql
    networks:
      - rt-net
    restart: unless-stopped

  rt-app:
    image: bpssysadmin/rt:6.0.2
    container_name: rt-app
    ports:
      - "8080:80"
    environment:
      RT_DBA_HOST: rt-db
      RT_DBA_PORT: 3306
      RT_DBA_DATABASE: rtdb
      RT_DBA_USER: rt_user
      RT_DBA_PASSWORD: rt_db_pass
      RT_WEB_DOMAIN: rt.example.com
    depends_on:
      - rt-db
    networks:
      - rt-net
    restart: unless-stopped

volumes:
  rt-db-data:

networks:
  rt-net:
    driver: bridge
```

For production deployments, add a reverse proxy (nginx or Traefik) with TLS termination and configure persistent storage for RT's attachments and templates. The `bpssysadmin/rt` image is a community-maintained build; many organizations build custom images based on Debian packages for tighter control.

### Installation on Ubuntu/Debian

```bash
# Install RT from system packages
sudo apt update
sudo apt install request-tracker5.0 apache2 libapache2-mod-fcgid

# Configure the database during installation
# The debconf wizard will prompt for DB type and credentials

# Enable required Apache modules
sudo a2enmod fcgid rewrite
sudo systemctl restart apache2

# Access RT at http://your-server/rt/
# Default admin credentials: root / password (change immediately)
```

## Znuny

[Znuny](https://www.znuny.com/) is a community-driven fork of OTRS (Open-source Ticket Request System), created after OTRS AG shifted to a commercial-only model in 2021. Znuny maintains API compatibility with OTRS 6, meaning existing OTRS extensions and workflows can be migrated with minimal changes.

### Key Strengths

- **OTRS heritage**: Inherits 20+ years of OTRS development and enterprise features
- **ITSM extension suite**: Built-in modules for Change Management, Problem Management, and SLA tracking
- **Process automation**: Generic Agent for scheduled actions, Process and Dynamic Fields for custom workflows
- **Strong knowledge base**: Integrated FAQ and solution database
- **Customer portal**: End-user self-service portal with ticket submission and tracking
- **Active community**: Regular releases with a clear open-source governance model

### Architecture

Like RT, Znuny is a Perl-based web application. It runs behind Apache or nginx with FastCGI and uses MySQL or PostgreSQL as the database backend. The architecture is nearly identical to OTRS 6, making migration straightforward.

### Docker Deployment

Community-maintained Docker images (such as `juanluisbaptiste/znuny`) make Znuny deployable via Docker Compose:

```yaml
version: "3.8"

services:
  znuny-db:
    image: mariadb:10.11
    container_name: znuny-db
    environment:
      MARIADB_ROOT_PASSWORD: znuny_root_pass
      MARIADB_DATABASE: znunydb
      MARIADB_USER: znuny_user
      MARIADB_PASSWORD: znuny_db_pass
    volumes:
      - znuny-db-data:/var/lib/mysql
    networks:
      - znuny-net
    restart: unless-stopped

  znuny-app:
    image: juanluisbaptiste/znuny:latest
    container_name: znuny-app
    ports:
      - "8080:80"
    environment:
      DB_HOST: znuny-db
      DB_NAME: znunydb
      DB_USER: znuny_user
      DB_PASS: znuny_db_pass
      FQDN: znuny.example.com
    depends_on:
      - znuny-db
    volumes:
      - znuny-config:/opt/otrs/Kernel
      - znuny-var:/opt/otrs/var
    networks:
      - znuny-net
    restart: unless-stopped

volumes:
  znuny-db-data:
  znuny-config:
  znuny-var:

networks:
  znuny-net:
    driver: bridge
```

The Znuny container exposes its web interface on port 80. Configure your reverse proxy to handle TLS and route traffic to the container. Persistent volumes for `/opt/otrs/Kernel` and `/opt/otrs/var` ensure configuration and uploaded files survive container restarts.

### Installation on Ubuntu/Debian

```bash
# Download the Znuny DEB package
wget https://ftp.znuny.com/releases/znuny-latest-7.3.deb

# Install dependencies and the package
sudo apt update
sudo apt install ./znuny-latest-7.3.deb

# Run the web-based installer
# Navigate to http://your-server/znuny/installer.pl
# Follow the setup wizard (database, admin user, email config)

# Set up the cron jobs for Znuny's background tasks
sudo cp /opt/znuny/var/cron/*dist /opt/znuny/var/cron/
sudo -u znuny /opt/znuny/bin/Cron.sh start
```

## iTop (Combodo)

[iTop](https://www.combodo.com/itop) (IT Operational Portal) takes a different approach: it is built around a Configuration Management Database (CMDB) first, with ITSM processes layered on top. Developed by Combodo, iTop is designed for organizations that need strong asset tracking and service dependency mapping alongside their ticketing.

### Key Strengths

- **CMDB at the core**: Full configuration item (CI) management with relationships and impact analysis
- **ITIL-aligned**: Incident, Problem, Change, and Service Request management out of the box
- **Service catalog**: End-user portal with categorized service offerings
- **Impact analysis**: Automatic dependency mapping — when a server goes down, iTop shows which services and users are affected
- **Data model extensibility**: Add custom CI types, attributes, and relationships through the UI
- **Portal customization**: Separate agent and end-user portals with configurable dashboards

### Architecture

iTop is a PHP application that runs on a LAMP stack (Linux, Apache, MySQL/MariaDB, PHP). It uses a custom ORM and data model engine that allows the entire schema to be extended without modifying core code.

### Docker Deployment

Community images like `viktorkbene/itop` or `openwaygroup/itop` provide Docker-based deployment:

```yaml
version: "3.8"

services:
  itop-db:
    image: mariadb:10.11
    container_name: itop-db
    environment:
      MARIADB_ROOT_PASSWORD: itop_root_pass
      MARIADB_DATABASE: itopdb
      MARIADB_USER: itop_user
      MARIADB_PASSWORD: itop_db_pass
    volumes:
      - itop-db-data:/var/lib/mysql
    networks:
      - itop-net
    restart: unless-stopped

  itop-app:
    image: viktorkbene/itop:3.2
    container_name: itop-app
    ports:
      - "8080:80"
    environment:
      ITOP_DB_HOST: itop-db
      ITOP_DB_NAME: itopdb
      ITOP_DB_USER: itop_user
      ITOP_DB_PASS: itop_db_pass
      ITOP_ADMIN_EMAIL: admin@example.com
      ITOP_URL: https://itop.example.com
    depends_on:
      - itop-db
    volumes:
      - itop-data:/var/www/html/data
      - itop-log:/var/www/html/log
    networks:
      - itop-net
    restart: unless-stopped

volumes:
  itop-db-data:
  itop-data:
  itop-log:

networks:
  itop-net:
    driver: bridge
```

### Installation on Ubuntu/Debian

```bash
# Install LAMP stack prerequisites
sudo apt update
sudo apt install apache2 mariadb-server php php-mysql \
  php-gd php-json php-curl php-xml php-mbstring \
  php-soap php-zip php-cli libapache2-mod-php

# Secure the database
sudo mysql_secure_installation

# Create the iTop database
sudo mysql -u root -p <<EOF
CREATE DATABASE itopdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'itop_user'@'localhost' IDENTIFIED BY 'itop_secure_pass';
GRANT ALL PRIVILEGES ON itopdb.* TO 'itop_user'@'localhost';
FLUSH PRIVILEGES;
EOF

# Download and extract iTop
wget https://sourceforge.net/projects/itop/files/itop/3.2.3/combodo-itop-3.2.3.zip
sudo unzip combodo-itop-3.2.3.zip -d /var/www/html/
sudo chown -R www-data:www-data /var/www/html/web

# Complete installation via web wizard
# Navigate to http://your-server/web/setup/
```

## Which One Should You Choose?

**Choose Request Tracker if:**
- You need a battle-tested, enterprise-grade ticketing system with 25+ years of development
- Your team is comfortable with Perl and FastCGI administration
- You need advanced queue management and the Scrips automation system
- You are in an academic or government environment (RT is widely adopted in these sectors)

**Choose Znuny if:**
- You have an existing OTRS installation and need an open-source migration path
- You want built-in ITSM modules (Change, Problem, SLA) without piecing together extensions
- You need a customer-facing portal with self-service capabilities
- Your team values active community governance and regular open-source releases

**Choose iTop if:**
- CMDB and asset management are your primary requirements, not just ticketing
- You need service dependency mapping and impact analysis
- You prefer a PHP stack over Perl
- Your organization follows ITIL and wants process alignment out of the box

For related reading, see our [self-hosted helpdesk comparison](../self-hosted-helpdesk-zammad-freescout-osticket/) for lighter-weight ticketing alternatives, [Snipe-IT vs Inventree vs PartKeepr](../snipe-it-vs-inventree-vs-partkeepr-self-hosted-inventory-guide-2026/) for IT asset management, and [GLPI mobile device management](../2026-04-26-headwind-mdm-vs-micromdm-vs-glpi-self-hosted-mobile-device-management-guide-2026/) for endpoint management.

## FAQ

### What is the difference between ITSM and a helpdesk?

A helpdesk focuses on incident management — receiving, tracking, and resolving user requests. ITSM (IT Service Management) is broader, encompassing incident management, problem management, change management, configuration management (CMDB), service catalogs, and SLA tracking. Tools like Request Tracker and Znuny started as helpdesks and expanded into ITSM. iTop was designed as an ITSM platform from the ground up, with CMDB at its core.

### Can these tools integrate with Active Directory or LDAP?

Yes. All three platforms support LDAP/Active Directory authentication. Request Tracker uses the `RT::Authen::ExternalAuth` extension. Znuny has built-in LDAP authentication modules configurable through its admin interface. iTop includes LDAP synchronization as part of its user management, allowing automatic user provisioning and group mapping.

### Is it possible to migrate from OTRS to Znuny?

Yes. Znuny is designed as a drop-in replacement for OTRS 6. You can migrate your database directly — Znuny uses the same schema and data model. The migration process involves backing up your OTRS database, installing Znuny, pointing it at the existing database, and running the migration scripts. Extensions may need to be replaced with Znuny-compatible versions.

### Do these platforms support REST APIs for integration?

All three provide REST APIs. Request Tracker offers a REST API for ticket CRUD operations, user management, and queue configuration. Znuny provides a comprehensive REST API (compatible with the OTRS Generic Interface) for tickets, customers, and ITSM objects. iTop includes a REST/JSON API for all data model objects, making it easy to integrate with monitoring tools, CMDB synchronizers, and custom applications.

### Which platform has the best email integration?

Request Tracker has the most sophisticated email integration of the three, with bidirectional email-ticket correlation, MIME attachment handling, and configurable email-based workflows. Znuny offers comparable email integration with its PostMaster and Sendmail modules. iTop handles email integration but requires additional configuration for full bidirectional support. For organizations where email is the primary ticket intake channel, RT has the edge.

### Are there mobile apps available for these ITSM platforms?

None of the three platforms offer official mobile apps. However, all three have responsive web interfaces that work on mobile browsers. Third-party mobile apps exist for Request Tracker (e.g., RT Mobile) and iTop in various app stores. Znuny's responsive portal provides a mobile-friendly end-user experience out of the box.

### How do these tools handle multi-tenant environments?

Request Tracker supports multi-tenancy through its RTIR (Incident Response) extension and queue-based isolation. Znuny offers multi-tenant capabilities through its customer company management and ticket isolation features. iTop has built-in multi-tenancy support with organization-based data segregation, making it the strongest choice for managed service providers (MSPs) managing multiple client environments from a single instance.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Request Tracker vs Znuny vs iTop: Self-Hosted ITSM & Ticketing Systems 2026",
  "description": "Compare three open-source ITSM platforms — Request Tracker, Znuny, and iTop — for self-hosted ticketing, incident management, and CMDB. Includes Docker deployment guides and feature comparisons.",
  "datePublished": "2026-04-30",
  "dateModified": "2026-04-30",
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
