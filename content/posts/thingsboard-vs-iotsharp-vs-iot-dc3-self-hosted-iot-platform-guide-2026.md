---
title: "ThingsBoard vs IoTSharp vs IoT DC3: Self-Hosted IoT Platform Guide 2026"
date: 2026-04-18
tags: ["comparison", "guide", "self-hosted", "iot", "mqtt", "iot-platform"]
draft: false
description: "Compare three self-hosted IoT platforms — ThingsBoard, IoTSharp, and IoT DC3 — for device management, data collection, rule processing, and dashboard visualization."
---

The Internet of Things market is projected to exceed $1.5 trillion by 2030, but most IoT platform offerings are expensive cloud services that charge per device and lock your data into proprietary ecosystems. Self-hosted IoT platforms give you full control over device data, avoid per-device pricing, and keep sensitive telemetry on your own infrastructure.

In this guide, we compare three open-source, self-hostable IoT platforms: **ThingsBoard**, **IoTSharp**, and **IoT DC3**. Each offers device management, telemetry collection, rule engines, and dashboarding — but they differ significantly in architecture, protocol support, and target use cases.

## Why Self-Host an IoT Platform?

Running your own IoT platform addresses several pain points that cloud-hosted solutions create:

- **Data sovereignty**: Sensor data, GPS coordinates, and device status never leave your network. This matters for industrial IoT, healthcare, and smart building deployments where data privacy regulations apply.
- **Cost at scale**: Cloud IoT platforms typically charge $2–$10 per device per month. Self-hosted platforms have zero per-device fees — your cost is the server hardware.
- **Low-latency processing**: Running the rule engine on-premise means sub-millisecond response times for time-critical automation (safety shutoffs, quality control triggers).
- **Offline resilience**: A self-hosted platform continues collecting and processing data even when your internet connection drops.
- **Custom integrations**: Direct access to the platform database and APIs lets you build bespoke integrations with your existing MES, ERP, or SCADA systems.

If you're connecting more than 50 devices, self-hosting usually pays for itself within a year compared to cloud alternatives.

## ThingsBoard

[ThingsBoard](https://github.com/thingsboard/thingsboard) is the most popular open-source IoT platform with **21,562 GitHub stars**. Written in Java, it provides a complete IoT infrastructure: device provisioning, telemetry ingestion, rule-based processing, and customizable dashboards.

**Key features:**

- Supports MQTT, CoAP, HTTP, and LwM2M protocols out of the box
- Built-in rule engine with drag-and-drop rule chain editor
- Rich dashboard builder with 40+ widget types
- Multi-tenant architecture for serving multiple customers from one installation
- PostgreSQL and Cassandra database backends
- Edge computing support via ThingsBoard Edge nodes
- REST, gRPC, and MQTT APIs for device and application integration

ThingsBoard's Community Edition is Apache 2.0 licensed. The Professional Edition adds white-labeling, reporting, and advanced alarm management.

### ThingsBoard [docker](https://www.docker.com/) Compose Setup

ThingsBoard ships with production-ready Docker Compose files supporting PostgreSQL, Cassandra, and hybrid storage configurations:

```yaml
# docker-compose.yml (simplified)
services:
  postgres:
    image: "postgres:16"
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: thingsboard
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres-data:/var/lib/postgresql/data

  tb-node:
    image: "thingsboard/tb-node:latest"
    ports:
      - "8080:8080"
      - "1883:1883"
      - "5683:5683/udp"
    environment:
      DATABASE_TS_TYPE: sql
      SPRING_DATASOURCE_URL: jdbc:postgresql://postgres:5432/thingsboard
      SPRING_DATASOURCE_USERNAME: postgres
      SPRING_DATASOURCE_PASSWORD: postgres
    volumes:
      - tb-node-data:/data
      - tb-node-logs:/var/log/thingsboard
    depends_on:
      - postgres

volumes:
  postgres-data:
  tb-node-data:
  tb-node-logs:
```

The full ThingsBoard Docker compose (available in the `docker/` directory of the repo) also includes ZooKeeper for clustering, JavaScript executor[kafka](https://kafka.apache.org/) rule processing, and Kafka integration for high-throughput deployments.

To start ThingsBoard for the first time:

```bash
# Pull and start services
docker compose up -d

# Run database initialization (first time only)
docker compose exec tb-node bash -c "java -jar /thingsboard.jar --install"
```

ThingsBoard's web UI becomes available at `http://localhost:8080`. Default login: `sysadmin@thingsboard.org` / `sysadmin`.

## IoTSharp

[IoTSharp](https://github.com/IoTSharp/IoTSharp) is a .NET-based IoT platform with **1,291 GitHub stars**. It targets teams already invested in the Microsoft ecosystem and offers a straightforward architecture: PostgreSQL for time-series data with TimescaleDB extension, MQTT broker integration, and a React-based dashboard.

**Key features:**

- .NET 8 backend with ASP.NET Core
- MQTT, CoAP, Modbus, and OPC-UA protocol support
- TimescaleDB for efficient time-series telemetry storage
- Built-in MQTT broker (no external broker required)
- Rule engine with visual flow designer
- Asset and device hierarchy management
- REST API and WebSocket support
- Docker Compose deployment with PostgreSQL

IoTSharp is Apache 2.0 licensed and has been actively maintained with regular releases throughout 2026.

### IoTSharp Docker Compose Setup

IoTSharp's compose is notably simpler than ThingsBoard's — it runs on PostgreSQL + the application container:

```yaml
# docker-compose.yml
services:
  pgsql:
    image: timescale/timescaledb-ha:pg17
    volumes:
      - "./data/postgresql:/var/lib/postgresql"
    environment:
      POSTGRES_USER: postgres
      POSTGRES_DB: IoTSharp
      POSTGRES_PASSWORD: BrrveCFVAZ6kM6vhjFMd
    ports:
      - "5432:5432"
    networks:
      - iotsharp-network

  iotsharp:
    image: maikebing/iotsharp
    environment:
      TZ: Asia/Shanghai
    depends_on:
      - pgsql
    volumes:
      - "./appsettings.Development.json:/app/appsettings.Development.json"
      - ./data/security:/app/security
    ports:
      - 2927:8080
      - 1883:1883
      - 8883:8883
      - 5683:5683
      - 5684:5684
    networks:
      - iotsharp-network

networks:
  iotsharp-network:
    driver: bridge
```

```bash
docker compose up -d
```

The IoTSharp web UI runs on port 2927. Connect MQTT devices to port 1883 (unencrypted) or 8883 (TLS).

## IoT DC3

[IoT DC3](https://github.com/pnoker/iot-dc3) is a Spring Cloud-based distributed IoT platform with **632 GitHub stars**. It uses a microservices architecture with separate services for authentication, device management, data processing, and gateway routing.

**Key features:**

- Spring Cloud microservices architecture
- Modular driver system supporting Modbus, OPC-UA, BACnet, and SNMP
- Edge computing capabilities
- RESTful APIs for all platform functionality
- Multi-tenant support
- Built-in device simulation for testing
- Distributed data collection across multiple sites
- Nacos for service discovery and configuration

IoT DC3 is AGPL-3.0 licensed. Its microservices architecture makes it well-suited for large-scale industrial deployments where different components need to scale independently.

### IoT DC3 Docker Compose Setup

IoT DC3's compose file lives in the `dc3/` subdirectory and runs multiple microservice containers:

```yaml
# dc3/docker-compose.yml (simplified)
services:
  gateway:
    image: pnoker/dc3-gateway:2025.9.0
    restart: always
    ports:
      - "8000:8000"
    container_name: dc3-gateway
    networks:
      dc3net:
        aliases: [dc3-gateway]

  auth:
    image: pnoker/dc3-center-auth:2025.9.0
    restart: always
    ports:
      - "8300:8300"
      - "9300:9300"
    container_name: dc3-center-auth
    networks:
      dc3net:
        aliases: [dc3-center-auth]

  manager:
    image: pnoker/dc3-center-manager:2025.9.0
    restart: always
    ports:
      - "8400:8400"
      - "9400:9400"
    container_name: dc3-center-manager
    networks:
      dc3net:
        aliases: [dc3-center-manager]

  data:
    image: pnoker/dc3-center-data:2025.9.0
    restart: always
    ports:
      - "8500:8500"
      - "9500:9500"
    container_name: dc3-center-data
    networks:
      dc3net:
        aliases: [dc3-center-data]

networks:
  dc3net:
    driver: bridge
```

```bash
cd dc3
docker compose up -d
```

The gateway exposes port 8000 for the web interface and API.

## Feature Comparison

| Feature | ThingsBoard | IoTSharp | IoT DC3 |
|---------|-------------|----------|---------|
| **GitHub Stars** | 21,562 | 1,291 | 632 |
| **Language** | Java | C# (.NET 8) | Java (Spring Cloud) |
| **License** | Apache 2.0 | Apache 2.0 | AGPL-3.0 |
| **MQTT** | Yes (built-in) | Yes (built-in) | Via drivers |
| **CoAP** | Yes | Yes | Via drivers |
| **HTTP API** | Yes | Yes | Yes |
| **LwM2M** | Yes (PE) | No | No |
| **Modbus** | Via rules | Yes (built-in) | Yes (driver) |
| **OPC-UA** | Via rules | Yes (built-in) | Yes (driver) |
| **Rule Engine** | Visual chain editor | Visual flow designer | Config-based |
| **Dashboard** | 40+ widgets | Basic widgets | Basic widgets |
| **Database** | PostgreSQL, Cassandra | TimescaleDB (PostgreSQL) | MySQL/PostgreSQL |
| **Multi-tenant** | Yes | Yes | Yes |
| **Edge Computing** | Yes (TB Edge) | No | Yes |
| **Clustering** | Yes (ZooKeeper) | Single-node | Yes (Nacos) |
| **Min RAM** | ~2 GB | ~1 GB | ~2 GB |
| **Docker Compose** | Yes (com[plex](https://www.plex.tv/)) | Yes (simple) | Yes (microservices) |
| **Last Updated** | April 2026 | April 2026 | April 2026 |

## Choosing the Right Platform

### Choose ThingsBoard if:

- You need the most mature and feature-rich open-source IoT platform
- Your deployment requires multi-tenant support with white-labeling
- You want built-in dashboarding with dozens of widget types
- You need LwM2M protocol support for constrained IoT devices
- You're planning to scale to thousands of devices with Kafka-backed ingestion
- Your team has Java/Spring experience

ThingsBoard is the default choice for most self-hosted IoT deployments. Its documentation, community size, and feature depth are unmatched in the open-source space.

### Choose IoTSharp if:

- Your team uses .NET and prefers C#-based platforms
- You want the simplest Docker deployment (just two containers)
- TimescaleDB's time-series capabilities are important for your analytics
- You need built-in Modbus and OPC-UA without additional configuration
- You prefer a lightweight platform that runs on minimal hardware

IoTSharp is a strong choice for .NET shops and smaller deployments where operational simplicity matters more than feature breadth.

### Choose IoT DC3 if:

- You need a modular microservices architecture that scales independently
- Your deployment spans multiple physical sites with edge computing
- You require BACnet or SNMP protocol support for building automation
- You want a driver-based architecture where new protocols can be added as plugins
- You're comfortable with the AGPL-3.0 license and its copyleft requirements

IoT DC3 targets industrial IoT and building automation scenarios where the microservices architecture provides deployment flexibility that monolithic platforms cannot match.

## Getting Started: Your First Device

Regardless of which platform you choose, the first step is connecting a device and sending telemetry. Here's how to publish temperature data via MQTT to each platform:

### ThingsBoard MQTT Example

```bash
# Install mosquitto clients
apt install mosquitto-clients -y

# Publish telemetry (replace YOUR_DEVICE_TOKEN)
mosquitto_pub -d -h localhost -t "v1/devices/me/telemetry" \
  -u "YOUR_DEVICE_TOKEN" -m '{"temperature": 24.5, "humidity": 65}'
```

### IoTSharp MQTT Example

```bash
# Publish telemetry
mosquitto_pub -d -h localhost -p 1883 \
  -t "devices/YOUR_DEVICE_ID/telemetry" \
  -m '{"temperature": 24.5}'
```

### IoT DC3 MQTT Example

IoT DC3 requires device registration through its REST API before accepting MQTT data:

```bash
# Register a device first
curl -X POST http://localhost:8400/api/v1/devices \
  -H "Content-Type: application/json" \
  -d '{"name": "temp-sensor-01", "driver": "listening-virtual"}'

# Then publish via MQTT to the driver port
mosquitto_pub -d -h localhost -p 6270 \
  -t "device/temp-sensor-01/telemetry" \
  -m '{"temperature": 24.5}'
```

For larger deployments, consider pairing your IoT platform with a [dedicated MQTT broker like Mosquitto or EMQX](../self-hosted-mqtt-platforms-mosquitto-emqx-hivemq-iot-guide-2026/) for better connection handling, and storing long-term telemetry in a [time-series database like InfluxDB or TimescaleDB](../influxdb-vs-questdb-vs-timescaledb-self-hosted-time-series-database-guide-2026/) for historical analytics beyond what the platform's built-in storage provides.

## FAQ

### What is the best open-source IoT platform for self-hosting?

ThingsBoard is widely considered the best open-source IoT platform for self-hosting, with over 21,000 GitHub stars, the most comprehensive feature set, and the largest community. It supports MQTT, CoAP, HTTP, and LwM2M protocols, includes a visual rule engine, and provides rich dashboarding out of the box.

### Can I run an IoT platform on a Raspberry Pi?

Yes, but with limitations. IoTSharp runs most comfortably on constrained hardware due to its lower memory footprint (~1 GB RAM). ThingsBoard requires at least 2 GB RAM for the Community Edition. IoT DC3's microservices architecture is harder to run on a single Pi but can be distributed across multiple Pis.

### Which IoT platform supports the most protocols?

ThingsBoard supports the widest range of protocols natively: MQTT, CoAP, HTTP, and LwM2M. IoTSharp adds built-in Modbus and OPC-UA support, which ThingsBoard only handles through its rule engine. IoT DC3 uses a driver-based architecture where each protocol is a separate plugin module.

### How many devices can a self-hosted IoT platform handle?

ThingsBoard has been tested with 100,000+ devices in clustered configurations using Kafka and Cassandra. IoTSharp and IoT DC3 are better suited for deployments under 10,000 devices, though horizontal scaling is possible with proper infrastructure.

### Do these platforms support real-time dashboards?

All three platforms support real-time data visualization. ThingsBoard has the most mature dashboard builder with 40+ widget types and drag-and-drop layout. IoTSharp and IoT DC3 provide basic dashboards that cover standard use cases (gauges, charts, maps) but lack the widget variety of ThingsBoard.

### Is the Community Edition of ThingsBoard sufficient for production?

For most self-hosted IoT deployments, yes. The Community Edition includes device management, telemetry collection, the rule engine, and dashboarding. The Professional Edition adds white-labeling, advanced reporting, hierarchical device groups, and the LwM2M server. Evaluate whether you need these features before upgrading.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "ThingsBoard vs IoTSharp vs IoT DC3: Self-Hosted IoT Platform Guide 2026",
  "description": "Compare three self-hosted IoT platforms — ThingsBoard, IoTSharp, and IoT DC3 — for device management, data collection, rule processing, and dashboard visualization.",
  "datePublished": "2026-04-18",
  "dateModified": "2026-04-18",
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
