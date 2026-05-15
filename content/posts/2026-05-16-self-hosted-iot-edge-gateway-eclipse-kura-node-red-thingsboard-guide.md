---
title: "Self-Hosted IoT Edge Gateway: Eclipse Kura vs Node-RED vs ThingsBoard Gateway"
date: "2026-05-16"
tags: ["iot", "edge-computing", "gateway", "industrial", "protocol"]
draft: false
---

An IoT edge gateway sits between field devices (sensors, actuators, PLCs) and cloud or on-premises data platforms. It handles protocol translation, data preprocessing, local analytics, and secure connectivity — making it the critical middleware layer in any industrial IoT architecture.

In this guide, we compare three leading open-source IoT edge gateway platforms: **Eclipse Kura**, **Node-RED**, and **ThingsBoard Gateway**. Each serves different deployment scenarios, from enterprise gateway management to lightweight visual programming to dedicated IoT platform integration.

## What Is an IoT Edge Gateway?

In industrial IoT deployments, field devices use diverse protocols — Modbus, OPC UA, MQTT, BACnet, CoAP — that cloud platforms cannot natively consume. The edge gateway solves this by:

- **Protocol translation** — convert Modbus RTU, OPC UA, or serial protocols to MQTT or HTTP
- **Data preprocessing** — filter, aggregate, and transform raw sensor data before transmission
- **Edge computing** — run local rules, alerts, and analytics when connectivity is intermittent
- **Device management** — remotely configure, update, and monitor connected field devices
- **Security** — encrypt data in transit, authenticate devices, and isolate OT from IT networks

Self-hosting an IoT edge gateway gives you full control over your data pipeline, eliminates per-device SaaS licensing costs, and ensures operational continuity even during internet outages. For organizations running [SCADA systems like FUXA or SCADA-LTS](../2026-05-02-self-hosted-scada-systems-fuxa-scada-lts-rapidscada-guide/), the edge gateway is the first hop in the data pipeline from field devices to visualization.

## Eclipse Kura — Enterprise IoT Gateway Management

**GitHub:** [eclipse/kura](https://github.com/eclipse/kura) — 565+ stars | **License:** EPL-2.0

Eclipse Kura is an IoT edge framework from the Eclipse Foundation that provides a complete gateway management platform. It runs on Java OSGi and includes a web-based management interface, cloud connectivity, and support for serial and industrial protocols.

### Key Features

- **Web-based management UI** — configure gateways remotely through a browser
- **OSGi modular architecture** — deploy and update bundles without restarting the gateway
- **Cloud connectivity** — built-in support for MQTT, HTTP, and Kura Cloud services
- **Serial and GPIO support** — direct communication with field devices via RS-485, RS-232
- **Cloudlet services** — local computation and data processing at the edge
- **Package management** — remote deployment of application bundles to distributed gateways
- **Watchdog and monitoring** — health checks and automatic recovery

### Docker Deployment

```yaml
version: "3.8"
services:
  eclipse-kura:
    image: eclipse/kura:latest
    container_name: eclipse-kura
    privileged: true
    ports:
      - "8080:8080"
      - "1883:1883"
      - "8883:8883"
    volumes:
      - ./kura-data:/opt/eclipse/kura/data
      - /dev:/dev
    environment:
      - KURA_CLOUD_SERVICE_URL=mqtt://your-broker:1883
      - KURA_WEB_PORT=8080
    devices:
      - "/dev/ttyUSB0:/dev/ttyUSB0"
    restart: unless-stopped
```

Kura's web interface on port 8080 provides a comprehensive management console where you can configure network settings, serial port connections, cloud endpoints, and deploy application bundles. The privileged mode is required for direct hardware access (serial ports, GPIO).

### When to Choose Eclipse Kura

- You manage distributed gateway fleets that need remote configuration
- You need a web-based management interface for non-developer operators
- You require OSGi-based modularity for hot-swappable components
- You operate in enterprise environments with Java infrastructure

## Node-RED — Visual Flow-Based IoT Programming

**GitHub:** [node-red/node-red](https://github.com/node-red/node-red) — 23,132+ stars | **License:** Apache-2.0

Node-RED is a flow-based development tool for visual programming, originally developed by IBM for IoT applications. It provides a browser-based editor where you wire together hardware devices, APIs, and online services using drag-and-drop nodes.

### Key Features

- **Visual flow editor** — browser-based drag-and-drop programming interface
- **3,000+ community nodes** — MQTT, Modbus, OPC UA, HTTP, database, and more
- **JavaScript function nodes** — custom data processing and transformation logic
- **Dashboard** — built-in UI widgets for real-time visualization
- **Lightweight runtime** — runs on Raspberry Pi, embedded devices, and cloud servers
- **Flow versioning** — export, import, and version-control your automation flows
- **npm ecosystem** — extend functionality with any Node.js package

### Docker Deployment

```yaml
version: "3.8"
services:
  node-red:
    image: nodered/node-red:latest
    container_name: node-red
    ports:
      - "1880:1880"
      - "1883:1883"
    volumes:
      - ./node-red-data:/data
    environment:
      - TZ=UTC
    restart: unless-stopped
```

Node-RED's flow editor at `http://your-server:1880` lets you build complex data pipelines visually. A typical IoT edge flow might read Modbus registers, transform the data, apply threshold-based filtering, and publish to an [MQTT broker](../self-hosted-mqtt-platforms-mosquitto-emqx-hivemq-iot-guide-2026/) — all without writing a single line of code.

### Example: Modbus to MQTT Flow

1. Add a **Modbus Read** node — configure slave address, register range, and polling interval
2. Wire to a **Function** node — transform raw register values into engineering units
3. Wire to a **Switch** node — filter values outside acceptable range
4. Wire to an **MQTT Out** node — publish to topic `sensors/temperature/room1`

This visual approach makes Node-RED ideal for rapid prototyping and for teams without deep programming expertise. For organizations running [IoT firmware platforms like ESPHome or Tasmota](../2026-05-09-self-hosted-iot-firmware-platforms-esphome-vs-tasmota-vs-espurna/), Node-RED provides the middleware layer that collects and processes sensor data.

### When to Choose Node-RED

- You prefer visual flow-based programming over code
- You need rapid prototyping and iteration for IoT data pipelines
- You want access to a massive library of pre-built integration nodes
- You run on Raspberry Pi or other low-cost edge hardware

## ThingsBoard Gateway — Dedicated IoT Platform Connector

**GitHub:** [thingsboard/thingsboard-gateway](https://github.com/thingsboard/thingsboard-gateway) — 2,124+ stars | **License:** Apache-2.0

ThingsBoard Gateway is the official edge gateway for the ThingsBoard IoT platform. It connects devices and sensors to ThingsBoard, handling protocol translation, data buffering, and edge rule processing.

### Key Features

- **Multi-protocol support** — MQTT, Modbus, OPC UA, BACnet, BLE, CAN, serial
- **Edge rule engine** — process and transform data locally before sending to the cloud
- **Offline buffering** — store data locally when connectivity is lost, sync when restored
- **RPC from cloud** — send commands from ThingsBoard to field devices through the gateway
- **Configuration via ThingsBoard** — manage gateway settings from the cloud platform UI
- **Python-based connectors** — easy to write custom protocol connectors
- **Docker-ready** — official Docker images and Docker Compose support

### Docker Deployment

```yaml
version: "3.8"
services:
  tb-gateway:
    image: thingsboard/tb-gateway:latest
    container_name: tb-gateway
    ports:
      - "1883:1883"
      - "9090:9090"
    volumes:
      - ./tb-gateway-config:/etc/tb-gateway
      - ./tb-gateway-logs:/var/log/tb-gateway
    environment:
      - TB_HOST=your-thingsboard-server
      - TB_PORT=1883
      - TB_GATEWAY_ACCESS_TOKEN=YOUR_ACCESS_TOKEN
    restart: unless-stopped
```

ThingsBoard Gateway is tightly integrated with the ThingsBoard platform. Configuration is managed through the ThingsBoard web UI, and the gateway automatically synchronizes device metadata, telemetry, and attribute updates. The offline buffering capability ensures no data is lost during network disruptions.

### When to Choose ThingsBoard Gateway

- You already use or plan to use ThingsBoard as your IoT platform
- You need tight integration between edge gateway and cloud platform
- You require offline buffering and automatic data synchronization
- You need RPC (remote procedure call) capabilities to control field devices from the cloud

## Feature Comparison

| Feature | Eclipse Kura | Node-RED | ThingsBoard Gateway |
|---------|-------------|----------|---------------------|
| Stars | 565+ | 23,132+ | 2,124+ |
| License | EPL-2.0 | Apache-2.0 | Apache-2.0 |
| Language | Java/OSGi | Node.js | Python |
| Management UI | Built-in web UI | Built-in flow editor | Via ThingsBoard platform |
| Protocol Support | MQTT, HTTP, Serial | 3,000+ nodes (MQTT, Modbus, OPC UA, etc.) | MQTT, Modbus, OPC UA, BACnet, BLE, CAN |
| Edge Processing | Java cloudlets | JavaScript function nodes | Python connectors + edge rules |
| Offline Buffering | Limited | Via node-red-contrib-persist | Built-in with auto-sync |
| Remote Management | OSGi bundle deployment | Flow import/export | ThingsBoard cloud UI |
| Hardware Access | Serial, GPIO, CAN | Via community nodes | Serial, Modbus, BLE, CAN |
| Docker Support | Yes | Yes (official image) | Yes (official image) |
| Best For | Enterprise gateway fleets | Rapid prototyping, visual programming | ThingsBoard ecosystem users |

## Why Self-Host Your IoT Edge Gateway?

Running your own IoT edge gateway platform rather than using vendor-managed cloud gateways offers several compelling advantages:

**Data sovereignty and privacy.** Industrial sensor data often contains sensitive operational information — production rates, equipment health, energy consumption. Self-hosting ensures this data never leaves your infrastructure. You control who has access, how long it is stored, and whether it is shared with third parties.

**Operational resilience.** Cloud-dependent gateways fail when internet connectivity drops. Self-hosted edge gateways continue collecting and processing data locally, buffering it for later synchronization. In manufacturing environments where a network outage can mean lost production data, this local-first approach is essential.

**Cost savings at scale.** Commercial IoT gateway platforms often charge per device or per data point. With 100+ sensors, these costs compound rapidly. Open-source gateways eliminate per-device licensing, and you can run them on commodity hardware — even Raspberry Pi devices for smaller deployments.

**Protocol flexibility.** Proprietary gateways typically support a limited set of protocols. Open-source platforms like Node-RED can integrate with virtually any protocol through community nodes, while Eclipse Kura and ThingsBoard Gateway support the full range of industrial protocols (Modbus, OPC UA, BACnet, CAN bus).

**Custom integration.** Self-hosted gateways can be integrated with your existing infrastructure — [SCADA platforms](../2026-05-02-self-hosted-scada-systems-fuxa-scada-lts-rapidscada-guide/), message brokers, time-series databases, and alerting systems — without being constrained by vendor integration roadmaps.

For organizations deploying [edge computing frameworks](../2026-04-23-kubeedge-vs-openyurt-vs-superedge-self-hosted-edge-computing-guide-2026/), the IoT edge gateway serves as the data collection layer that feeds into the broader edge computing architecture.

## Security Best Practices

- **Network isolation** — deploy gateways on segregated OT networks with firewalls between OT and IT zones
- **TLS encryption** — enable TLS for all MQTT and HTTP communications; use certificate-based authentication where possible
- **Access control** — restrict gateway management UI access to authorized IPs; use strong authentication
- **Regular updates** — keep gateway software and dependencies updated; use automated patch management
- **Audit logging** — enable comprehensive logging for all gateway operations and device communications
- **Secret management** — store API tokens, certificates, and credentials in secure vaults, not plaintext config files

## Choosing the Right IoT Edge Gateway

The choice depends on your operational context:

- **Enterprise gateway management**: Choose Eclipse Kura for fleet management, web-based UI, and OSGi modularity across hundreds of distributed gateways.
- **Rapid prototyping and flexibility**: Choose Node-RED for visual flow programming, massive node library, and ease of use on low-cost hardware.
- **ThingsBoard ecosystem**: Choose ThingsBoard Gateway for seamless integration with ThingsBoard, offline buffering, and cloud-managed configuration.

Many organizations combine approaches — Node-RED for initial prototyping and custom integrations, then migrating to Eclipse Kura or ThingsBoard Gateway for production deployments requiring robust management capabilities.

## FAQ

### What is the difference between an IoT gateway and an IoT platform?

An IoT gateway is the edge device that collects data from sensors and field devices, translates protocols, and forwards data upstream. An IoT platform is the cloud or on-premises system that stores, analyzes, visualizes, and acts on that data. The gateway is the edge component; the platform is the central component. In many deployments, the gateway and platform run on the same physical infrastructure.

### Can I run these gateways on Raspberry Pi?

Yes, all three can run on Raspberry Pi hardware. Node-RED is the most lightweight and is officially supported on Raspberry Pi with a dedicated installer. Eclipse Kura runs on the Pi but requires Java (more memory). ThingsBoard Gateway runs on the Pi with Python 3. For production deployments with many connected devices, a more powerful edge device (Intel NUC, industrial PC) is recommended.

### How do I handle offline scenarios when the internet connection drops?

ThingsBoard Gateway has built-in offline buffering — data is stored locally in SQLite and automatically synced when connectivity returns. Node-RED can use persistence nodes (node-red-contrib-persist) or local file storage for buffering. Eclipse Kura supports local data storage with deferred cloud publishing. Choose the gateway with the buffering capability that matches your data loss tolerance.

### Which gateway supports the most industrial protocols?

ThingsBoard Gateway supports the widest range out-of-the-box (MQTT, Modbus, OPC UA, BACnet, BLE, CAN, serial). Node-RED can support virtually any protocol through its 3,000+ community nodes, but requires manual installation of each node. Eclipse Kura supports MQTT, HTTP, and serial protocols natively, with additional protocols available through OSGi bundles.

### How do I secure communication between the gateway and field devices?

Use TLS/SSL for all network communications. For Modbus, upgrade from Modbus RTU (unencrypted serial) to Modbus TCP with TLS. For MQTT, enable TLS on port 8883 with client certificate authentication. For OPC UA, use the built-in security profiles (Basic256Sha256). Additionally, deploy gateways on physically isolated OT networks with firewall rules between OT and IT infrastructure.

### Can I use multiple gateways in the same deployment?

Yes. A common pattern is to deploy lightweight gateways (Node-RED on Raspberry Pi) at each production cell for local data collection and preprocessing, then aggregate data through a central gateway (Eclipse Kura or ThingsBoard Gateway) that handles cloud connectivity and fleet management. This hierarchical architecture provides both local resilience and centralized management.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted IoT Edge Gateway: Eclipse Kura vs Node-RED vs ThingsBoard Gateway",
  "description": "Compare three open-source IoT edge gateway platforms: Eclipse Kura, Node-RED, and ThingsBoard Gateway. Protocol translation, Docker deployment, and edge computing patterns for industrial IoT.",
  "datePublished": "2026-05-16",
  "dateModified": "2026-05-16",
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
