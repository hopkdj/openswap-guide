---
title: "Headwind MDM vs MicroMDM vs GLPI: Best Self-Hosted MDM Solutions 2026"
date: 2026-04-26
tags: ["comparison", "guide", "self-hosted", "mobile", "device-management", "mdm"]
draft: false
description: "Compare Headwind MDM, MicroMDM, and GLPI — the top open-source Mobile Device Management solutions for Android, iOS, and cross-platform enterprise fleets in 2026."
---

Mobile Device Management (MDM) is the backbone of any organization that needs to control, secure, and monitor smartphones, tablets, and other mobile endpoints. Commercial MDM platforms like Jamf Pro, Microsoft Intune, and VMware Workspace ONE carry steep per-device licensing fees and send your telemetry to third-party clouds. Self-hosted MDM solutions give you full control over device data, enforce compliance policies on your own infrastructure, and eliminate recurring subscription costs.

In this guide, we compare three mature open-source MDM platforms that cover the full spectrum — Android-only, Apple-only, and cross-platform IT asset management — so you can pick the right tool for your device fleet.

## Why Self-Host Your MDM

Running your own MDM server addresses several concerns that cloud-hosted solutions cannot:

- **Data sovereignty** — device inventory, location data, app lists, and compliance reports never leave your network. This is critical for healthcare, finance, and government organizations bound by HIPAA, GDPR, or sovereignty regulations.
- **Cost at scale** — per-device SaaS pricing adds up quickly. Self-hosted MDM has no per-seat license, making it economically viable for fleets of hundreds or thousands of devices.
- **Custom integrations** — on-premise MDM servers can integrate directly with your LDAP/Active Directory, internal app repositories, SIEM platforms, and ticketing systems without cloud API rate limits.
- **Offline capability** — manage devices in air-gapped or low-connectivity environments where cloud MDM simply cannot reach.
- **No vendor lock-in** — open-source MDM protocols (like Apple's MDM protocol and Android Enterprise) mean you control the server stack and can migrate or extend as needed.

## Headwind MDM — Android-Focused Device Management

[Headwind MDM](https://h-mdm.com/) is a purpose-built open-source MDM system for Android devices. It consists of a Java/Spring Boot web control panel and an Android agent app (launcher) that runs on managed devices.

**GitHub:** [h-mdm/hmdm-server](https://github.com/h-mdm/hmdm-server) — ⭐ 497 stars, last pushed April 25, 2026

### Key Features

- **Silent app installation and updates** — push APK files to devices without user interaction
- **Kiosk mode** — lock devices to a single app or a whitelist of allowed applications
- **Device inventory** — view hardware specs, OS version, battery level, storage, and network status
- **Remote commands** — reboot, lock, wipe, or change device settings from the web console
- **Plugin architecture** — extend functionality with custom plugins (notifications, geofencing, barcode scanning)
- **Multi-tenant support** — manage separate device groups for different departments or customers

Headwind MDM is designed specifically for Android Enterprise (formerly Android for Work) and supports both fully managed devices and work profiles. It is widely used in digital signage, point-of-sale terminals, field service tablets, and classroom device deployments.

### Deployment

Headwind MDM does not ship an official Docker Compose file, but the installation script handles dependency setup on a standard Linux server:

```bash
# Install Headwind MDM on Ubuntu/Debian
wget https://h-mdm.com/files/hmdm_install.sh
chmod +x hmdm_install.sh
sudo ./hmdm_install.sh
```

The installer configures PostgreSQL, Apache Tomcat, and Nginx with SSL. For a production Docker deployment, you can containerize the application using a custom Dockerfile:

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:15
    restart: unless-stopped
    environment:
      POSTGRES_DB: hmdm
      POSTGRES_USER: hmdm
      POSTGRES_PASSWORD: hmdm_secret_password
    volumes:
      - pgdata:/var/lib/postgresql/data
    expose:
      - "5432"

  hmdm-server:
    build:
      context: ./hmdm-server
      dockerfile: Dockerfile
    restart: unless-stopped
    depends_on:
      - postgres
    environment:
      DB_URL: jdbc:postgresql://postgres:5432/hmdm
      DB_USER: hmdm
      DB_PASSWORD: hmdm_secret_password
    ports:
      - "8080:8080"
    volumes:
      - hmdm-uploads:/opt/hmdm/uploads

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    depends_on:
      - hmdm-server
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro

volumes:
  pgdata:
  hmdm-uploads:
```

The Android agent is distributed as an APK that you install on each managed device. The agent communicates with the server over HTTPS to receive policy updates and report device status.

## MicroMDM — Lightweight Apple MDM Server

[MicroMDM](https://github.com/micromdm/micromdm) is an open-source MDM server that implements Apple's MDM protocol, enabling management of macOS, iOS, iPadOS, and tvOS devices. It is written in Go and designed to be minimal and embeddable.

**GitHub:** [micromdm/micromdm](https://github.com/micromdm/micromdm) — ⭐ 2,628 stars, last pushed March 18, 2026

### Key Features

- **Apple MDM protocol compliance** — supports enrollment, configuration profiles, app management, and remote commands for all Apple platforms
- **APNs integration** — uses Apple Push Notification service to wake devices and trigger MDM check-ins
- **SQLite/PostgreSQL backend** — lightweight SQLite for small deployments or PostgreSQL for larger fleets
- **REST API** — full API for automation, integration with CI/CD pipelines, and custom tooling
- **DEP/ABM support** — integrates with Apple Business Manager and Device Enrollment Program for zero-touch provisioning
- **Minimal footprint** — single Go binary, easy to deploy and maintain

MicroMDM is favored by organizations that need a simple, reliable Apple MDM without the complexity and cost of commercial alternatives. It is commonly used for managing MacBook fleets in engineering teams, iPads in education, and Apple TV deployments.

### Deployment

MicroMDM provides a Dockerfile and a development Docker Compose file. For production, pair it with PostgreSQL:

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:15
    restart: unless-stopped
    environment:
      POSTGRES_DB: micromdm
      POSTGRES_USER: micromdm
      POSTGRES_PASSWORD: micromdm_db_secret
    volumes:
      - pgdata:/var/lib/postgresql/data
    expose:
      - "5432"

  micromdm:
    image: micromdm/micromdm:latest
    restart: unless-stopped
    depends_on:
      - postgres
    command: >
      -api-key=your-api-key-here
      -postgres=postgres://micromdm:micromdm_db_secret@postgres:5432/micromdm?sslmode=disable
      -apns-cert=/etc/micromdm/certs/apns.pem
      -apns-key=/etc/micromdm/certs/apns.key
      -filereply=/etc/micromdm/reply
    ports:
      - "8080:8080"
      - "443:443"
    volumes:
      - ./certs:/etc/micromdm/certs:ro
      - ./reply:/etc/micromdm/reply

volumes:
  pgdata:
```

The critical configuration piece for MicroMDM is the APNs push certificate, which you must obtain from [Apple's MDM Push Certificate Portal](https://identity.apple.com/pushcert/) using a DUNS-registered Apple ID. This certificate is required for the server to send push notifications that wake managed Apple devices.

## GLPI with Flyve MDM Plugin — Cross-Platform IT Asset Management

[GLPI](https://glpi-project.org/) is a comprehensive open-source IT asset management, service desk, and license tracking platform. When combined with the [Flyve MDM plugin](https://flyve.org/mdm/), it extends into full mobile device management for both Android and iOS devices.

**GitHub:** [glpi-project/glpi](https://github.com/glpi-project/glpi) — ⭐ 5,817 stars, last pushed April 24, 2026

### Key Features

- **Unified IT asset management** — manage computers, monitors, printers, software licenses, network equipment, and mobile devices from a single console
- **ITIL-compliant service desk** — ticketing, problem management, change management, and SLA tracking
- **Flyve MDM plugin** — adds device enrollment, policy enforcement, remote wipe, and app management for Android and iOS
- **Inventory agents** — GLPI Agent (formerly FusionInventory) automatically discovers and inventories devices on your network
- **LDAP/Active Directory integration** — sync users, groups, and authentication from existing directory services
- **Reporting and dashboards** — built-in reports for asset lifecycle, compliance, and utilization metrics
- **Plugin ecosystem** — hundreds of community plugins for extended functionality

GLPI is the most feature-rich option in this comparison, but it is also the most complex. It is best suited for IT departments that want a single platform to manage their entire infrastructure — not just mobile devices.

### Deployment

GLPI provides an official Docker Compose file for development. For production, adapt it with persistent volumes and proper networking:

```yaml
version: "3.8"

services:
  glpi:
    image: glpi-project/glpi:latest
    restart: unless-stopped
    depends_on:
      - db
    environment:
      DB_HOST: db
      DB_USER: glpi
      DB_PASSWORD: glpi_secret_password
      DB_NAME: glpi
    ports:
      - "8080:80"
    volumes:
      - glpi-files:/var/www/html/glpi/files
      - glpi-plugins:/var/www/html/glpi/plugins

  db:
    image: mariadb:11
    restart: unless-stopped
    environment:
      MARIADB_ROOT_PASSWORD: root_secret
      MARIADB_DATABASE: glpi
      MARIADB_USER: glpi
      MARIADB_PASSWORD: glpi_secret_password
    volumes:
      - db-data:/var/lib/mysql

  mailpit:
    image: axllent/mailpit:latest
    restart: unless-stopped
    ports:
      - "8025:8025"
      - "1025:1025"

volumes:
  glpi-files:
  glpi-plugins:
  db-data:
```

After deploying GLPI, install the Flyve MDM plugin from the GLPI marketplace or by placing it in the `plugins/` directory. The plugin adds MDM enrollment profiles, device policy templates, and remote action capabilities for both Android and iOS devices.

## Head-to-Head Comparison

| Feature | Headwind MDM | MicroMDM | GLPI + Flyve MDM |
|---|---|---|---|
| **Platforms** | Android only | macOS, iOS, iPadOS, tvOS | Android, iOS, plus all IT assets |
| **GitHub Stars** | 497 | 2,628 | 5,817 |
| **Last Active** | April 2026 | March 2026 | April 2026 |
| **Language** | Java | Go | PHP |
| **Database** | PostgreSQL | SQLite / PostgreSQL | MariaDB / MySQL |
| **Docker Support** | Community | Official Dockerfile | Official docker-compose |
| **Kiosk Mode** | ✅ Yes | ❌ No (profiles only) | ✅ Via plugin |
| **Silent App Install** | ✅ Yes | ✅ (via VPP/ABM) | ✅ Via plugin |
| **Remote Wipe** | ✅ Yes | ✅ Yes | ✅ Via plugin |
| **Zero-Touch Provisioning** | ❌ No | ✅ Apple DEP/ABM | ❌ Limited |
| **Service Desk / ITIL** | ❌ No | ❌ No | ✅ Built-in |
| **License Tracking** | ❌ No | ❌ No | ✅ Built-in |
| **LDAP/AD Integration** | ❌ No | ❌ No | ✅ Built-in |
| **API** | REST | REST | REST + GraphQL plugins |
| **Best For** | Android device fleets | Apple device fleets | Full IT asset management |

## Which One Should You Choose?

**Choose Headwind MDM if:** Your fleet is exclusively Android devices — digital signage, kiosks, POS terminals, or classroom tablets. It offers the deepest Android-specific feature set, including custom launcher kiosk mode, silent APK deployment, and a plugin architecture for specialized use cases. The web console is straightforward and purpose-built for Android device administrators.

**Choose MicroMDM if:** You manage Apple devices and want a lightweight, reliable MDM server. MicroMDM implements the Apple MDM protocol faithfully, supports DEP/ABM zero-touch enrollment, and has a minimal resource footprint. It is the go-to choice for engineering teams managing MacBook fleets or schools deploying iPads. Pair it with [Nanodep](https://github.com/tiny-pilot/nanodep) or similar tools for automated DEP assignment.

**Choose GLPI + Flyve MDM if:** You need a comprehensive IT management platform that covers mobile devices alongside computers, software licenses, network equipment, and help desk operations. GLPI is the Swiss Army knife of open-source IT management. The Flyve MDM plugin adds mobile device enrollment and policy enforcement, and the broader GLPI ecosystem provides inventory agents, LDAP sync, and ITIL-compliant service desk capabilities. This is ideal for IT departments that want a single pane of glass for all infrastructure assets.

For organizations with mixed Android and Apple fleets that need deep MDM features on both platforms, consider running Headwind MDM and MicroMDM side-by-side — each handles its native platform with full feature parity, while a shared LDAP directory provides unified user management. Alternatively, pair either MDM with our [VPN and remote access guide](../self-hosted-vpn-solutions-wireguard-openvpn-tailscale-guide/) to secure device connectivity, or integrate with [endpoint management tools](../2026-04-21-fleet-osquery-vs-wazuh-vs-teleport-self-hosted-endpoint-management-guide-2026/) for broader device visibility and compliance monitoring.

## FAQ

### What is the difference between MDM and EMM?

MDM (Mobile Device Management) focuses on device-level control — enrollment, configuration profiles, remote wipe, and policy enforcement. EMM (Enterprise Mobility Management) is a broader category that includes MDM plus application management (MAM), content management (MCM), and identity management. All three solutions covered here are MDM-focused; GLPI extends beyond MDM into full IT asset management.

### Can I manage both Android and iOS devices with a single open-source MDM?

No single open-source MDM natively supports both platforms with full feature parity. Headwind MDM is Android-only, MicroMDM is Apple-only, and GLPI's Flyve MDM plugin provides basic management for both but with limited depth compared to the dedicated solutions. For mixed fleets, running Headwind MDM and MicroMDM side-by-side is the recommended approach.

### Do I need Apple Developer Enterprise Program for MicroMDM?

No. You need an Apple ID registered with a DUNS number (free) to obtain the MDM Push Certificate from Apple's Push Certificate Portal. The Apple Developer Enterprise Program ($299/year) is only required if you want to distribute in-house apps outside the App Store. For standard MDM management — configuration profiles, remote commands, and VPP app deployment — the free push certificate is sufficient.

### Is Headwind MDM free for commercial use?

Yes. Headwind MDM is released under the Apache License 2.0, which permits commercial use, modification, and distribution. The core server and Android agent are fully open-source. The project also offers a commercial edition with additional features like geofencing, advanced reporting, and priority support.

### How does GLPI's Flyve MDM compare to commercial MDM platforms?

GLPI with Flyve MDM provides core MDM capabilities — device enrollment, policy enforcement, remote wipe, and inventory — but does not match the depth of commercial platforms like Jamf Pro or Intune in areas like advanced security policies, automated compliance reporting, and third-party app catalog integration. However, for organizations already using GLPI for IT asset management and help desk operations, the Flyve MDM plugin provides a cost-effective way to extend into mobile device management without introducing a separate platform.

### Can I use MicroMDM to manage non-Apple devices?

No. MicroMDM implements Apple's proprietary MDM protocol, which only Apple devices understand. It cannot manage Android, Windows, or Linux devices. For cross-platform management, consider GLPI with the Flyve MDM plugin or combine MicroMDM with Headwind MDM for Apple and Android coverage respectively.

### What database should I use for production MDM deployments?

For Headwind MDM, PostgreSQL is required. For MicroMDM, PostgreSQL is recommended for production deployments (SQLite is suitable only for small test environments). For GLPI, MariaDB or MySQL is the standard choice. In all cases, ensure the database server is backed up regularly and that connection strings use strong, randomly generated passwords.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Headwind MDM vs MicroMDM vs GLPI: Best Self-Hosted MDM Solutions 2026",
  "description": "Compare Headwind MDM, MicroMDM, and GLPI — the top open-source Mobile Device Management solutions for Android, iOS, and cross-platform enterprise fleets in 2026.",
  "datePublished": "2026-04-26",
  "dateModified": "2026-04-26",
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
