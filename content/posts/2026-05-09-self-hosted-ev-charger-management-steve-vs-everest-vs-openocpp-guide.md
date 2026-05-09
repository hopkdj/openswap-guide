---
title: "Self-Hosted EV Charger Management: SteVe vs EVerest vs OpenOCPP"
date: "2026-05-09"
draft: false
tags: ["ev-charger", "ocpp", "electric-vehicle", "charging", "energy", "steve", "everest"]
---

The electric vehicle revolution is creating a parallel need for charging infrastructure management. Commercial charging networks rely on cloud-based platforms, but for fleet operators, workplaces, and residential communities, self-hosted EV charger management provides full control over charging data, user privacy, and operational costs.

The Open Charge Point Protocol (OCPP) is the universal standard for communication between EV chargers (charge points) and central management systems (CSMS). This guide compares three open-source OCPP server implementations: SteVe, EVerest, and OpenOCPP, covering architecture, features, and deployment.

## Why Self-Host Your EV Charger Management System

The EV charging infrastructure market is rapidly growing, with most fleet operators and businesses relying on commercial cloud platforms to manage their charging stations. While these platforms offer convenience, they come with significant drawbacks that make self-hosted alternatives increasingly attractive.

### Data Ownership and Privacy

Commercial charging platforms retain full control over your charging data, including session logs, energy consumption patterns, user information, and payment details. For fleet operators managing dozens or hundreds of vehicles, this data is valuable for optimizing charging schedules, predicting maintenance needs, and managing energy costs. Self-hosting keeps this data within your infrastructure where you control access, retention, and usage policies.

### Eliminating Per-Connector Licensing Fees

Most commercial EV charging platforms charge monthly fees per connected connector, typically ranging from $5 to $30 per month. For a workplace with 20 charging stations, this translates to $1,200 to $7,200 annually in platform fees alone. Open-source OCPP servers eliminate these recurring costs entirely, requiring only the hardware to run the server.

### Custom Integration Flexibility

Self-hosted OCPP servers provide direct API and database access, enabling custom integrations with existing building management systems, solar panel monitoring, battery storage controllers, and billing platforms. Commercial platforms typically offer limited API access with rate limits and usage restrictions that can block automated workflows.

For energy monitoring alongside your charging infrastructure, see our [energy monitoring tools guide](../self-hosted-energy-monitoring-tools-guide/). If you manage a broader IoT deployment that includes EV chargers alongside sensors and actuators, our [IoT platform comparison](../thingsboard-vs-iotsharp-vs-iot-dc3-self-hosted-iot-platform-guide-2026/) covers platforms that can integrate charger data with other device telemetry.

## SteVe: The Mature OCPP Server

SteVe (Standardized Vehicle-to-Grid) is the most established open-source OCPP server, developed at RWTH Aachen University. It supports OCPP 1.6J (JSON) and provides a full-featured web interface for charger management.

### GitHub Stats

- **Repository**: RWTH-i5-IDSG/steve
- **Stars**: 1,050+
- **Last Updated**: May 2026
- **Language**: Java (Spring Boot)
- **OCPP Versions**: 1.6J (OCPP 2.0.1 in development)

### Key Features

- **Web management console**: Full UI for monitoring chargers, sessions, and users
- **OCPP 1.6J support**: JSON-based WebSocket transport
- **User management**: RFID tag assignment, user groups, and access control
- **Session logging**: Detailed charging session history with energy and cost data
- **REST API**: Programmatic access for integration with billing and monitoring systems
- **MySQL/PostgreSQL backend**: Production-ready database support

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  steve:
    image: steve-community/steve:latest
    container_name: steve-ocpp
    ports:
      - "8080:8080"
      - "8443:8443"
    environment:
      SPRING_DATASOURCE_URL: jdbc:mysql://steve-mysql:3306/stevedb
      SPRING_DATASOURCE_USERNAME: steve
      SPRING_DATASOURCE_PASSWORD: steve-password
      SPRING_PROFILES_ACTIVE: prod
    depends_on:
      - steve-mysql
    restart: unless-stopped

  steve-mysql:
    image: mysql:8.0
    container_name: steve-mysql
    environment:
      MYSQL_ROOT_PASSWORD: root-secret
      MYSQL_DATABASE: stevedb
      MYSQL_USER: steve
      MYSQL_PASSWORD: steve-password
    volumes:
      - steve-mysql-data:/var/lib/mysql
    restart: unless-stopped

volumes:
  steve-mysql-data:
```

After deployment, access the web interface at `http://your-server:8080`. Default credentials are `admin/admin`. Register your charge points by their unique ChargeBox ID.

## EVerest: The Modern EV Charging Stack

EVerest is an open-source EV charging software stack developed by Pionix. Unlike SteVe, which focuses on the central system side, EVerest provides a complete stack from charger firmware emulation to cloud management.

### GitHub Stats

- **Repository**: EVerest/everest
- **Stars**: 180+
- **Last Updated**: May 2026
- **Language**: C++ / Python
- **OCPP Versions**: 1.6J and 2.0.1

### Key Features

- **Full EV charging stack**: Charge point simulation, OCPP server, and energy management
- **OCPP 2.0.1 support**: Latest protocol version with smart charging and ISO 15118 integration
- **Modular architecture**: Plug-and-play modules for different charger types
- **Smart charging**: Dynamic power allocation across multiple chargers
- **Plug-and-Charge**: ISO 15118 certificate-based authentication
- **Active development**: Backed by Pionix and the Linux Foundation Energy

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  everest:
    image: ghcr.io/everest/everest:latest
    container_name: everest-ocpp
    ports:
      - "8080:8080"
      - "9000:9000"
    volumes:
      - ./everest-config:/etc/everest:ro
    environment:
      EVEREST_CONFIG_DIR: /etc/everest
    restart: unless-stopped

  everest-mqtt:
    image: eclipse-mosquitto:2.0
    container_name: everest-mqtt
    ports:
      - "1883:1883"
    volumes:
      - ./mosquitto.conf:/mosquitto/config/mosquitto.conf:ro
    restart: unless-stopped
```

EVerest uses MQTT for internal module communication. The `everest-config` directory should contain your module configuration files defining the charge point simulation and OCPP server settings.

## OpenOCPP: Lightweight OCPP Implementation

OpenOCPP is a lightweight, C++-based OCPP implementation designed for embedded systems and resource-constrained environments. It implements the OCPP 1.6 protocol on the charge point side and can be paired with any OCPP 1.6-compliant central system.

### Key Characteristics

- **Lightweight**: Designed for embedded Linux systems
- **OCPP 1.6 support**: Full implementation of the 1.6 protocol
- **Modular**: Separable charge point and central system components
- **Cross-platform**: Runs on Linux, Windows, and embedded platforms
- **Community-driven**: Active open-source community

### Docker Deployment

```yaml
version: "3.8"
services:
  openocpp:
    image: openocpp/openocpp:latest
    container_name: openocpp-server
    ports:
      - "8080:8080"
      - "9000:9000"
    volumes:
      - ./openocpp.conf:/etc/openocpp/openocpp.conf:ro
    restart: unless-stopped
```

## Comparison Table

| Feature | SteVe | EVerest | OpenOCPP |
|---------|-------|---------|----------|
| OCPP 1.6J | Yes | Yes | Yes |
| OCPP 2.0.1 | In development | Yes | No |
| Web management UI | Yes (full console) | Yes (dashboard) | Limited |
| Smart charging | Basic | Advanced | No |
| ISO 15118 (Plug-and-Charge) | No | Yes | No |
| User management | Yes (RFID, groups) | Yes | Basic |
| REST API | Yes | Yes | Limited |
| Database backend | MySQL/PostgreSQL | SQLite/PostgreSQL | File-based |
| Language | Java (Spring Boot) | C++/Python | C++ |
| GitHub stars | 1,050+ | 180+ | 50+ |
| Docker image | Community | Official (GHCR) | Community |
| Best for | Fleet operators, workplaces | Modern charging stations | Embedded systems |

## Deployment Architecture Considerations

When deploying a self-hosted OCPP server, consider these architectural decisions:

**Network topology**: OCPP uses outbound WebSocket connections from the charger to the central system. Your server must be reachable from all chargers, typically via a public IP or VPN. For private networks, ensure the WebSocket port (usually 80 or 443) is open. Most chargers support WSS (WebSocket Secure) for encrypted communication.

**Database sizing**: Each charging session generates multiple OCPP messages including StartTransaction, MeterValues, and StopTransaction. For a fleet of 50 chargers running 5 sessions per day, expect 5 to 10 GB of data per year. Use SSDs for the database volume to handle the write-heavy workload.

**TLS termination**: Always use TLS for OCPP connections. Terminate TLS at a reverse proxy like nginx or Traefik and forward plain WebSocket to the OCPP server. This simplifies certificate management and enables easy certificate rotation.

**High availability**: For critical deployments, run multiple OCPP server instances behind a load balancer. SteVe supports horizontal scaling with a shared database. EVerest modular architecture allows individual module scaling.

## Choosing the Right OCPP Server

**Choose SteVe if:**
- You need a mature, feature-complete OCPP 1.6J server
- A web management console is important for your operations team
- You are managing a fleet of OCPP 1.6J chargers

**Choose EVerest if:**
- You need OCPP 2.0.1 support with smart charging
- ISO 15118 Plug-and-Charge authentication is a requirement
- You want a modular, future-proof architecture

**Choose OpenOCPP if:**
- You are deploying on resource-constrained hardware
- You need a lightweight embedded solution
- OCPP 1.6 basic functionality is sufficient

## FAQ

### What is OCPP and why does it matter?

OCPP (Open Charge Point Protocol) is an open communication standard between EV chargers and management systems. It is the dominant protocol for EV charging infrastructure, similar to how HTTP is for web services. OCPP ensures chargers from different manufacturers can work with the same management platform, preventing vendor lock-in.

### Can I use these open-source OCPP servers with any EV charger?

Most OCPP 1.6J-compliant chargers will work with SteVe and EVerest. Check that your charger supports OCPP 1.6J (JSON over WebSocket) and configure it with your server WebSocket URL. OCPP 2.0.1 support is growing but not yet universal, and EVerest is the best choice if your chargers support 2.0.1.

### How many chargers can a self-hosted OCPP server manage?

SteVe has been tested with hundreds of simultaneous charger connections. EVerest modular architecture allows horizontal scaling. For deployments exceeding 500 chargers, consider database optimization and horizontal scaling with a load balancer.

### Do I need special networking for OCPP communication?

OCPP uses outbound WebSocket connections from the charger to the central system. No inbound ports need to be opened on the charger side. The central system needs to accept incoming WebSocket connections on the configured port (typically 80 or 443 with TLS).

### Can I integrate an OCPP server with existing billing systems?

Yes. SteVe provides a REST API for session data, user management, and charger status. EVerest offers module-based APIs for integration. You can build custom billing logic that reads session data and calculates charges based on energy consumed and time-of-use pricing.

### What happens if the OCPP server goes offline?

OCPP 1.6J chargers can operate in offline mode using cached authorization lists. Charging sessions started before the outage will continue, but new sessions may be blocked depending on the charger offline policy. When the server comes back online, chargers automatically reconnect and sync any missed data.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted EV Charger Management: SteVe vs EVerest vs OpenOCPP",
  "description": "Compare three open-source OCPP server implementations for self-hosted EV charger management: SteVe, EVerest, and OpenOCPP. Includes Docker deployment configs and feature comparison.",
  "datePublished": "2026-05-09",
  "dateModified": "2026-05-09",
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
