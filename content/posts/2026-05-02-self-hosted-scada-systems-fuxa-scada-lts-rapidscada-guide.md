---
title: "Self-Hosted SCADA Systems: FUXA vs SCADA-LTS vs RapidScada — Complete Guide 2026"
date: 2026-05-02
tags: ["comparison", "guide", "self-hosted", "scada", "industrial", "monitoring", "docker"]
draft: false
description: "Complete guide to open-source SCADA systems in 2026. Compare FUXA, SCADA-LTS, and RapidScada with Docker deployment configs, feature comparisons, and setup instructions for self-hosted industrial automation."
---

Industrial automation and real-time process monitoring are no longer the exclusive domain of enterprises with six-figure software budgets. Open-source SCADA (Supervisory Control and Data Acquisition) systems have matured to the point where small manufacturers, facility operators, research labs, and homelab enthusiasts can deploy professional-grade monitoring and control platforms on their own hardware.

This guide compares three leading open-source SCADA platforms — **FUXA**, **SCADA-LTS**, and **RapidScada** — examining their architectures, feature sets, deployment complexity, and suitability for different use cases. Whether you are monitoring a solar panel array, managing a water treatment plant, or building a smart greenhouse, understanding the strengths and trade-offs of each platform will help you make the right choice.

For teams new to containerized deployments, our [Docker Compose for Beginners guide](../docker-compose-guide/) covers the fundamentals of defining and running multi-container applications.

## FUXA: Modern Web-Based SCADA and HMI Platform

[FUXA](https://github.com/frangoteam/FUXA) is the most actively developed open-source SCADA project by a wide margin, with over 4,400 stars on GitHub. Built with Node.js on the backend and Angular on the frontend, FUXA delivers a modern web-based interface for creating SCADA dashboards, HMI (Human-Machine Interface) screens, and real-time data visualizations.

### Architecture and Technology Stack

FUXA's architecture is built around a single-process Node.js server that handles HTTP requests, WebSocket connections for real-time updates, and communication with industrial devices. The Angular-based client renders SVG-based process graphics directly in the browser, eliminating the need for proprietary client software or browser plugins.

The platform supports a broad range of industrial protocols out of the box:

- **Modbus RTU/TCP** for PLC and instrument communication
- **OPC-UA** for modern industrial data exchange
- **MQTT** for IoT sensor integration
- **Siemens S7** protocol for Siemens PLCs
- **BACnet** for building automation systems
- **OPC DA** for legacy OPC servers

### Key Features

FUXA's feature set covers the full SCADA workflow:

**Visual Editor.** The drag-and-drop HMI editor lets you create process graphics using SVG shapes, animations, and data bindings. You can build pipe-and-instrument diagrams, control panel overlays, and custom dashboards without writing code.

**Data Acquisition and Historian.** FUXA includes a built-in data logger that records tag values to a local SQLite database. Historical trends can be displayed on charts and graphs embedded directly in your HMI screens.

**Alarm Management.** Define alarm conditions on any tag with configurable severity levels, acknowledgment workflows, and alarm history views. Notifications can be routed through email and webhooks.

**Scripting Support.** JavaScript-based scripting lets you implement custom logic, data transformations, and device control sequences directly within the SCADA runtime.

**Multi-Platform Support.** FUXA runs on Linux, Windows, macOS, and Raspberry Pi. The Docker image makes deployment trivial on any container-capable host.

### Docker Deployment

FUXA provides an official Docker image and a `compose.yml` file in the repository root. Here is the official Docker Compose configuration:

```yaml
# FUXA Docker Compose (from https://github.com/frangoteam/FUXA)
services:
  fuxa:
    image: frangoteam/fuxa:latest
    restart: unless-stopped
    volumes:
      - './appdata:/usr/src/app/FUXA/server/_appdata'
      - './db:/usr/src/app/FUXA/server/_db'
      - './logs:/usr/src/app/FUXA/server/_logs'
      - './images:/usr/src/app/FUXA/server/_images'
    ports:
      - '1881:1881'
```

Deploy with:

```bash
wget https://raw.githubusercontent.com/frangoteam/FUXA/master/compose.yml
docker compose up -d
```

The four volume mounts ensure persistent storage for application data, the historian database, runtime logs, and uploaded images. The service listens on port 1881 by default.

### Strengths and Limitations

FUXA's greatest advantage is its modern UI and active development cycle. The Angular-based editor is responsive and intuitive, and new protocol support is added regularly. The single-process architecture keeps resource usage low — FUXA runs comfortably on a Raspberry Pi 4.

However, FUXA is primarily a visualization and HMI platform. It lacks some advanced SCADA features found in more mature systems, such as complex recipe management, advanced reporting engines, and built-in redundancy/failover. The SQLite historian works well for small deployments but may need replacement with PostgreSQL or InfluxDB for high-throughput installations.

## SCADA-LTS: Enterprise-Grade Open-Source SCADA

[SCADA-LTS](https://github.com/SCADA-LTS/Scada-LTS) is a Java-based, web-platform SCADA system derived from the Mango Automation platform. With nearly 950 stars on GitHub, it is smaller than FUXA but targets a more enterprise-oriented audience with features designed for medium to large installations.

### Architecture and Technology Stack

SCADA-LTS runs on Apache Tomcat with a MySQL backend, following a traditional enterprise web application architecture. The system consists of several components:

- **Tomcat web application** serving the SCADA-LTS interface and REST API
- **MySQL database** for configuration, event storage, and historical data
- **MangoJS data acquisition engine** handling protocol communication and real-time processing
- **MQTT broker** (HiveMQ) for IoT protocol integration

The Java-based architecture means SCADA-LTS requires more resources than FUXA — typically at least 2 GB of heap space for the Tomcat process — but it also benefits from Java's mature ecosystem for database connectivity, protocol implementations, and enterprise integration patterns.

### Key Features

SCADA-LTS offers a comprehensive feature set:

**Data Point Management.** Define thousands of data points across multiple protocols. Each point can have metadata, engineering units, alarm limits, and custom rendering templates.

**Protocol Support.** SCADA-LTS supports Modbus (serial and TCP), BACnet, DNP3, SNMP, HTTP/HTTPS, virtual data points, and calculation-based points. The MangoJS engine handles the protocol communication layer.

**Graphical Views.** Create dashboards using the built-in graphical view editor. Views support real-time data binding, animations, and custom components. The HTML5-based interface works on any modern browser.

**Event Detection and Handling.** Configurable event detectors trigger on value changes, limit violations, no-update conditions, and binary state transitions. Events can generate emails, SMS messages, or execute custom scripts.

**Watch Lists and Reporting.** Users can create personalized watch lists of critical data points. The reporting engine generates scheduled and ad-hoc reports in multiple formats.

**REST API.** A comprehensive REST API enables integration with external systems, custom applications, and automation workflows.

**User Management.** Role-based access control with configurable permissions for viewing, editing, and administering different system components.

### Docker Deployment

SCADA-LTS provides an official `docker-compose.yml` file that deploys the complete stack — MySQL database, Tomcat application server, and HiveMQ MQTT broker:

```yaml
# SCADA-LTS Docker Compose (from https://github.com/SCADA-LTS/Scada-LTS)
version: '3'
services: 
    database:
        container_name: mysql
        image: mysql/mysql-server:8.0.32
        ports:
            - "3306:3306"
        environment: 
            - MYSQL_ROOT_PASSWORD=***
            - MYSQL_USER=root
            - MYSQL_PASSWORD=***
            - MYSQL_DATABASE=scadalts
        expose: ["3306"]
        volumes:
            - ./db_data:/var/lib/mysql:rw
            - ./db_conf:/etc/mysql:ro
        command: --log_bin_trust_function_creators=1
    scadalts:
        image: scadalts/scadalts:latest
        environment:
            - CATALINA_OPTS=-Xmx2G -Xms2G
        ports: 
            - "8080:8080"
        depends_on: 
            - database
        expose: ["8080", "8000"]
        volumes:
            - ./tomcat_log:/usr/local/tomcat/logs:rw
        links:
            - database:database
        command:
            - /usr/bin/wait-for-it
            - --host=database
            - --port=3306
            - --timeout=30
            - --strict
            - --
            - /usr/local/tomcat/bin/catalina.sh
            - run
    mqtt:
        image: hivemq/hivemq4:latest
        ports:
            - "8081:8080"
            - "1883:1883"
        expose: [ "8081", "1883" ]
```

The three-service architecture reflects SCADA-LTS's enterprise orientation. The `wait-for-it` script ensures the Tomcat application only starts after MySQL is ready. Note that the Tomcat heap is set to 2 GB — plan your host accordingly.

### Strengths and Limitations

SCADA-LTS excels in enterprise scenarios where you need robust data management, comprehensive audit trails, and integration with existing enterprise systems. The Java/MySQL stack is battle-tested in production environments, and the REST API makes it straightforward to integrate with external tools.

The primary drawbacks are resource consumption and complexity. The three-container deployment requires more RAM than FUXA, and the Java-based architecture means slower startup times. The graphical editor, while functional, lacks the polish and responsiveness of FUXA's Angular-based interface. For small deployments or resource-constrained hardware, SCADA-LTS may be overkill.

For organizations that also need centralized log management and security monitoring alongside SCADA, our [self-hosted SIEM comparison](../self-hosted-siem-wazuh-security-onion-elastic-guide/) covers complementary infrastructure monitoring tools.

## RapidScada: Lightweight Industrial Automation Platform

[RapidScada](https://github.com/RapidScada/scada) is a .NET-based SCADA system that prioritizes simplicity and performance. With around 740 stars on GitHub, it is the smallest of the three projects but has a dedicated user base, particularly in Eastern Europe and among users who prefer Windows-based deployments.

### Architecture and Technology Stack

RapidScada follows a modular architecture with distinct components:

- **ScadaServer** — the core data acquisition and processing engine
- **ScadaComm** — communication module for device connectivity
- **ScadaWeb** — ASP.NET web application for visualization and configuration
- **ScadaAdmin** — Windows desktop application for system administration
- **ScadaAgent** — lightweight agent for remote management

The system is primarily designed for Windows environments, using the .NET Framework (with some .NET Core components in recent versions). Communication between components uses a proprietary binary protocol over TCP. Device protocols are implemented as pluggable drivers.

### Key Features

RapidScada covers the essential SCADA functionality:

**Data Acquisition.** The ScadaServer engine polls devices at configurable intervals and processes incoming data through a formula engine. The system supports MODBUS (RTU and TCP) and OPC UA natively, with additional protocol drivers available as plugins.

**Formula Engine.** RapidScada includes a built-in formula engine for computing derived values, implementing control logic, and performing data transformations. Formulas are evaluated in real-time as new data arrives.

**Web Interface.** ScadaWeb provides a browser-based interface with real-time data display, historical charts, and configurable dashboards. The web application runs on ASP.NET and is compatible with IIS or Kestrel hosting.

**Desktop Administration.** ScadaAdmin is a Windows desktop application for configuring data points, communication channels, and system settings. This separation of administration and visualization is a deliberate design choice that keeps the web interface lightweight.

**Reporting.** Built-in reporting engine generates periodic reports and supports custom report templates.

**Plugin Architecture.** The modular design allows third-party developers to create protocol drivers, visualization widgets, and data processing modules.

### Docker Deployment

RapidScada does not include an official `docker-compose.yml` file in its repository. The system is primarily designed for Windows deployment, and community Docker images rely on systemd within the container, which requires Podman rather than standard Docker.

For self-hosted deployments on Linux using Podman, here is a community-based configuration:

```yaml
# RapidScada Docker Compose (community-based, using Podman)
# Official repo: https://github.com/RapidScada/scada
# Note: RapidScada uses systemd internally — Podman is recommended over Docker
services:
  rapidscada:
    image: artyras/rapidscada_6:latest
    container_name: rapidscada
    restart: unless-stopped
    ports:
      - "8082:80"
      - "10000:10000"
      - "10002:10002"
      - "10008:10008"
    volumes:
      - ./scada_data:/var/lib/scada
    privileged: true
```

For production deployments, you would also need to configure a separate PostgreSQL or MySQL database for ScadaWeb, as the community image bundles everything in a single container. The port mapping exposes the web interface (80), ScadaServer communication (10000), ScadaComm (10002), and additional services (10008).

**Important:** Deploy this with `podman-compose` rather than standard Docker Compose, as the container requires systemd. Standard Docker containers do not include a service manager.

### Strengths and Limitations

RapidScada's main advantages are its lightweight server component, straightforward formula engine, and clean separation between administration and visualization. The desktop administration tool is familiar to engineers accustomed to traditional SCADA workflows, and the system performs well even on modest hardware.

The limitations are significant for Linux-focused deployments: the primary design target is Windows, Docker support is limited to community images requiring Podman, and the desktop administration tool requires Windows or Wine. The smaller community also means fewer third-party plugins and less community-contributed documentation compared to FUXA.

## Feature Comparison

| Feature | FUXA | SCADA-LTS | RapidScada |
|---|---|---|---|
| **GitHub Stars** | ~4,432 | ~943 | ~738 |
| **Primary Language** | Node.js / Angular | Java | C# / .NET |
| **Database** | SQLite (built-in) | MySQL | SQLite / PostgreSQL |
| **Modbus Support** | Yes (RTU/TCP) | Yes (RTU/TCP) | Yes (RTU/TCP) |
| **OPC-UA** | Yes | Via plugin | Yes |
| **MQTT** | Yes | Yes (HiveMQ) | Via plugin |
| **BACnet** | Yes | Yes | No |
| **Siemens S7** | Yes | No | Via plugin |
| **Web-Based HMI** | Yes (Angular/SVG) | Yes (HTML5) | Yes (ASP.NET) |
| **Desktop Admin** | No | No | Yes (Windows) |
| **REST API** | Limited | Comprehensive | Limited |
| **Alarm Management** | Yes | Yes (advanced) | Yes |
| **Historian** | SQLite-based | MySQL-based | SQLite/PostgreSQL |
| **Reporting** | Basic | Advanced | Basic |
| **Scripting** | JavaScript | Groovy/JavaScript | Formula engine |
| **Docker Support** | Official image + compose | Official compose file | Community (Podman) |
| **Min. RAM** | ~256 MB | ~2 GB | ~512 MB |
| **Best For** | Modern UI, IoT, small-mid | Enterprise, large installs | Windows shops, simplicity |

## Deployment Decision Matrix

Choosing between these three platforms comes down to your specific requirements:

**Choose FUXA if** you want the most modern interface, need to deploy quickly on a Raspberry Pi or small server, prioritize IoT protocol support (MQTT, OPC-UA), or want the largest and most active community. FUXA is the best starting point for most new SCADA deployments in 2026.

**Choose SCADA-LTS if** you are running an enterprise installation with thousands of data points, need comprehensive reporting and audit trails, require integration with existing enterprise systems via REST API, or your team has Java/MySQL expertise. The three-container architecture is more complex but scales to larger installations.

**Choose RapidScada if** your infrastructure is primarily Windows-based, your operators prefer a traditional desktop administration workflow, or you need a lightweight server component with a formula-based processing engine. Be prepared to use Podman for containerized deployments on Linux.

## Getting Started Checklist

Regardless of which platform you choose, follow these steps for a successful deployment:

1. **Define your data points.** Document every sensor, actuator, and computed value before configuring the system. Include data types, polling intervals, engineering units, and alarm thresholds.

2. **Plan your network architecture.** Place the SCADA server on a dedicated VLAN or network segment. Use firewall rules to restrict access to industrial protocols (Modbus, OPC-UA) to authorized hosts only.

3. **Configure persistent storage.** All three platforms support persistent data through volume mounts. Ensure your storage backend has sufficient IOPS for your historian workload.

4. **Set up monitoring.** Monitor the SCADA server itself using infrastructure monitoring tools. For metrics storage and visualization, see our [VictoriaMetrics vs Thanos vs Cortex guide](../victoriametrics-vs-thanos-vs-cortex-self-hosted-metrics-storage-guide-2026/) for self-hosted options.

5. **Implement backup procedures.** Back up configuration databases, historian data, and HMI project files on a regular schedule. Test restore procedures before you need them.

6. **Document your installation.** Record IP addresses, port configurations, protocol settings, and custom scripts. Your future self will thank you during troubleshooting.

## FAQ

### What is SCADA and why would I self-host it?

SCADA (Supervisory Control and Data Acquisition) is a system architecture for monitoring and controlling industrial processes in real time. It collects data from sensors and devices, presents it to operators through visual interfaces, logs historical values for analysis, and can trigger automated responses based on configurable rules. Self-hosting a SCADA system gives you complete control over your data, eliminates recurring licensing fees, and allows customization for your specific use case without vendor lock-in. It is particularly valuable for small manufacturers, research facilities, utility operators, and anyone who needs industrial monitoring without the cost of commercial platforms.

### Which SCADA system is easiest to set up with Docker?

FUXA is the most straightforward to deploy with Docker. Its official Docker Compose configuration consists of a single service with four volume mounts, and the container starts in seconds. SCADA-LTS requires a three-container setup (MySQL, Tomcat, MQTT) with dependency ordering, which is more complex but still well-documented. RapidScada does not have an official Docker Compose file and requires Podman instead of Docker due to its systemd dependency, making it the most complex to containerize.

### Can these systems run on a Raspberry Pi?

FUXA runs natively on Raspberry Pi and is the best choice for Pi-based deployments. Its Node.js architecture and SQLite backend work well within the Pi's memory constraints. SCADA-LTS requires at least 2 GB of heap for the Tomcat process, which pushes the limits of a Raspberry Pi 4 — it may run but will be slow under load. RapidScada can run on a Pi using the .NET runtime, but community Docker images are not optimized for ARM architecture.

### How do these systems handle real-time data updates?

FUXA uses WebSocket connections to push real-time updates to connected browser clients, providing sub-second latency for tag value changes. SCADA-LTS uses a combination of AJAX polling and long-polling for real-time updates, with configurable refresh intervals. RapidScada uses its own binary protocol between the server and web client, with the ScadaServer pushing updates to connected web sessions. For most industrial applications, all three provide adequate real-time performance, but FUXA's WebSocket approach offers the lowest latency.

### Do any of these systems support redundancy and high availability?

None of the three platforms offer built-in automatic failover or hot standby redundancy in their open-source versions. SCADA-LTS comes closest with its enterprise architecture — you can configure multiple SCADA-LTS instances to read from the same MySQL database and use an external load balancer. FUXA and RapidScada would require external orchestration (such as Kubernetes or a custom heartbeat script) to implement redundancy. For critical infrastructure requiring high availability, you should evaluate commercial SCADA platforms or build custom redundancy on top of these open-source bases.

### What protocol support do I need for my devices?

If you are working with standard Modbus devices (the most common industrial protocol), all three platforms support it. For OPC-UA integration, FUXA and RapidScada have native support while SCADA-LTS requires a plugin. If you need BACnet for building automation, FUXA and SCADA-LTS support it natively. For Siemens S7 PLCs, only FUXA has built-in support. If your deployment relies heavily on MQTT for IoT sensors, FUXA and SCADA-LTS (with HiveMQ) are the better choices. Always verify protocol support for your specific devices before committing to a platform.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "Self-Hosted SCADA Systems: FUXA vs SCADA-LTS vs RapidScada — Complete Guide 2026",
  "description": "Complete guide to open-source SCADA systems in 2026. Compare FUXA, SCADA-LTS, and RapidScada with Docker deployment configs, feature comparisons, and setup instructions for self-hosted industrial automation.",
  "datePublished": "2026-05-02",
  "dateModified": "2026-05-02",
  "author": {
    "@type": "Organization",
    "name": "OpenSource Alternatives"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSource Alternatives"
  },
  "mainEntityOfPage": {
    "@type": "WebPage",
    "@id": "https://example.com/posts/2026-05-02-self-hosted-scada-systems-fuxa-scada-lts-rapidscada-guide/"
  },
  "keywords": ["SCADA", "FUXA", "SCADA-LTS", "RapidScada", "self-hosted", "industrial automation", "HMI", "Docker", "open source"]
}
</script>

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "What is SCADA and why would I self-host it?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "SCADA (Supervisory Control and Data Acquisition) is a system architecture for monitoring and controlling industrial processes in real time. Self-hosting gives you complete data ownership, eliminates licensing fees, and allows customization without vendor lock-in."
      }
    },
    {
      "@type": "Question",
      "name": "Which SCADA system is easiest to set up with Docker?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "FUXA is the most straightforward to deploy with Docker. Its official Docker Compose configuration consists of a single service with four volume mounts, and the container starts in seconds."
      }
    },
    {
      "@type": "Question",
      "name": "Can these systems run on a Raspberry Pi?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "FUXA runs natively on Raspberry Pi and is the best choice for Pi-based deployments. SCADA-LTS requires at least 2 GB of heap for Tomcat, pushing the limits of a Pi 4. RapidScada can run but community Docker images are not ARM-optimized."
      }
    },
    {
      "@type": "Question",
      "name": "How do these systems handle real-time data updates?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "FUXA uses WebSocket connections for sub-second latency. SCADA-LTS uses AJAX polling and long-polling. RapidScada uses its own binary protocol between server and web client. FUXA's WebSocket approach offers the lowest latency."
      }
    },
    {
      "@type": "Question",
      "name": "Do any of these systems support redundancy and high availability?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "None offer built-in automatic failover in their open-source versions. SCADA-LTS comes closest — you can configure multiple instances reading from the same MySQL database with an external load balancer. FUXA and RapidScada would require external orchestration."
      }
    },
    {
      "@type": "Question",
      "name": "What protocol support do I need for my devices?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "All three support Modbus. FUXA and RapidScada have native OPC-UA; SCADA-LTS requires a plugin. FUXA and SCADA-LTS support BACnet. Only FUXA has built-in Siemens S7 support. FUXA and SCADA-LTS are best for MQTT IoT integration."
      }
    }
  ]
}
</script>
