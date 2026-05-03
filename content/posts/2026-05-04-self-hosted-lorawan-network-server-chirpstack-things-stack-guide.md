---
title: "Best Self-Hosted LoRaWAN Network Servers in 2026"
date: 2026-05-04T09:00:00+00:00
draft: false
tags: ["lorawan", "iot", "networking", "self-hosted", "sensors", "open-source"]
---

LoRaWAN (Long Range Wide Area Network) enables low-power, long-range wireless communication for IoT devices — perfect for agricultural sensors, environmental monitoring, smart city infrastructure, and industrial telemetry. At the heart of every LoRaWAN deployment is a **Network Server** that manages device connectivity, routing, security, and application data delivery.

While commercial LoRaWAN network services exist, self-hosting gives you complete control over device data, eliminates per-device subscription fees, and enables private network deployments in areas without commercial coverage. This guide compares three open-source LoRaWAN network server options: **ChirpStack**, **The Things Stack**, and the lightweight **lorawan-server**.

## What Is a LoRaWAN Network Server?

A LoRaWAN network server sits between your physical LoRa gateways and your applications. It handles device authentication (OTAA/ABP join procedures), message deduplication across multiple gateways, encryption/decryption, data rate adaptation (ADR), and forwarding decoded sensor data to application servers via MQTT, HTTP, or WebSockets.

For organizations deploying IoT sensors across campuses, factories, or agricultural sites, a self-hosted network server means sensor data stays on-premises, device credentials are never shared with third parties, and there are no recurring per-device fees — critical considerations when managing hundreds or thousands of sensors.

## Comparison Overview

| Feature | ChirpStack | The Things Stack | lorawan-server |
|---------|-----------|------------------|----------------|
| **License** | MIT | Apache-2.0 | Apache-2.0 |
| **Language** | Go + Web UI | Go | Erlang |
| **Docker Support** | ✅ Official compose | ✅ Official compose | ✅ Community images |
| **Multi-tenant** | ✅ Organizations | ✅ Clusters | ❌ Single-tenant |
| **Web Console** | ✅ Full-featured | ✅ Full-featured | ✅ Lightweight |
| **MQTT Integration** | ✅ Built-in | ✅ Built-in | ✅ Built-in |
| **HTTP Integration** | ✅ Webhooks | ✅ Webhooks | ✅ Webhooks |
| **LoRaWAN 1.0/1.1** | ✅ Both | ✅ Both | ✅ Both |
| **Class A/B/C** | ✅ All classes | ✅ All classes | ✅ Class A/C |
| **Geolocation** | ✅ Gateway-based | ✅ Gateway + TDOA | ❌ |
| **Multi-region** | ✅ Region profiles | ✅ Frequency plans | ✅ Region config |
| **Fragments/Large Data** | ✅ Fragmentation | ✅ Fragmentation | ❌ |
| **GitHub Stars** | 1,006 | 1,144 | 1,006 |
| **Last Updated** | April 2026 | April 2026 | Nov 2023 |

## ChirpStack — The Modular Open-Source Leader

[ChirpStack](https://github.com/ChirpStack/chirpstack) is the most popular open-source LoRaWAN network server, known for its modular architecture and extensive feature set. Originally developed by Orne Brocaar (as `loraserver`), it has evolved into a comprehensive platform supporting everything from small private networks to large multi-tenant deployments.

ChirpStack's architecture separates the network server, application server, gateway bridge, and MQTT broker into independent components. This modularity lets you scale each component independently and swap out dependencies (e.g., use Redis or PostgreSQL, MQTT or gRPC for gateway communication).

### Deploying ChirpStack with Docker Compose

ChirpStack provides an official Docker Compose setup with all required services:

```yaml
services:
  chirpstack:
    image: chirpstack/chirpstack:4
    command: -c /etc/chirpstack
    restart: unless-stopped
    ports:
      - "8080:8080"
      - "1700:1700/udp"
    volumes:
      - ./configuration/chirpstack:/etc/chirpstack
      - ./lorawan-devices:/opt/lorawan-devices
    depends_on:
      - postgres
      - redis
    environment:
      - MQTT_BROKER_HOST=mqtt
      - POSTGRESQL_HOST=postgres
      - REDIS_HOST=redis
      - BIND=0.0.0.0:8080

  chirpstack-gateway-bridge:
    image: chirpstack/chirpstack-gateway-bridge:4
    restart: unless-stopped
    ports:
      - "1700:1700/udp"
    volumes:
      - ./configuration/chirpstack-gateway-bridge:/etc/chirpstack-gateway-bridge

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: chirpstack
      POSTGRES_PASSWORD: chirpstack_db_pass
      POSTGRES_DB: chirpstack
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  mqtt:
    image: eclipse-mosquitto:2
    ports:
      - "1883:1883"
    volumes:
      - ./configuration/mosquitto/mosquitto.conf:/mosquitto/config/mosquitto.conf

volumes:
  postgres_data:
  redis_data:
```

After deployment, access the ChirpStack web console at port 8080, create your first organization, gateway profile, and device profile. Devices can join via OTAA (Over-The-Air Activation) or ABP (Activation By Personalization).

## The Things Stack — Enterprise-Grade with Global Roaming

[The Things Stack](https://github.com/TheThingsNetwork/lorawan-stack) is the open-source network server developed by The Things Industries. It powers both the public Things Network and private enterprise deployments. Its standout feature is **global device roaming** — devices registered on your private stack can roam onto The Things Network's global infrastructure, and vice versa.

The Things Stack includes a polished web console, device claiming (for LoRa Alliance-certified devices), end-to-end encryption, and built-in support for The Things Stack's device repository — a curated database of LoRaWAN device profiles with configuration templates.

### Deploying The Things Stack

The Things Stack requires additional configuration for its blob storage and identity server components:

```yaml
services:
  ttn-lorawan:
    image: thethingsnetwork/lorawan-stack:latest
    command: ttn-lw-stack -c /config/ttn-lw-stack.yml start
    restart: unless-stopped
    ports:
      - "8080:8080"
      - "1700:1700/udp"
      - "1882:1882"
      - "8882:8882"
    volumes:
      - ./config:/config
      - ./blob:/srv/ttn-lorawan/public/blob
    depends_on:
      - postgres
      - redis
    environment:
      TTN_LW_IS_DATABASE_URI: postgres://ttn:stack_db_pass@postgres:5432/ttn_lorawan?sslmode=disable

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ttn
      POSTGRES_PASSWORD: stack_db_pass
      POSTGRES_DB: ttn_lorawan
    volumes:
      - pg_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

volumes:
  pg_data:
  redis_data:
```

The Things Stack configuration YAML file (`ttn-lw-stack.yml`) requires defining your cluster identity, cookie hash keys, and OAuth settings for the console.

## lorawan-server — Lightweight for Edge Deployments

[lorawan-server](https://github.com/gotthardp/lorawan-server) by Petr Gotthard is a compact, single-binary LoRaWAN network server written in Erlang. It is designed for resource-constrained deployments — think Raspberry Pi gateways, remote agricultural sites, or edge computing scenarios where running multiple containers is impractical.

Despite its small footprint, lorawan-server supports core LoRaWAN functionality: OTAA and ABP join, data forwarding via MQTT and HTTP, and configurable channel plans for regional deployments. Its Erlang-based architecture provides excellent fault tolerance and hot-code reloading.

### Deploying lorawan-server with Docker

While lorawan-server doesn't have an official Docker Compose file, it can be run using the community Docker image:

```yaml
services:
  lorawan-server:
    image: gotthardp/lorawan-server:latest
    restart: unless-stopped
    ports:
      - "8080:8080"
      - "1700:1700/udp"
      - "1883:1883"
      - "8443:8443"
    volumes:
      - lora_data:/tmp/lorawan-server
    environment:
      - WITH_EMULATOR=false

  mqtt:
    image: eclipse-mosquitto:2
    ports:
      - "1884:1883"
    volumes:
      - ./mosquitto.conf:/mosquitto/config/mosquitto.conf

volumes:
  lora_data:
```

The lorawan-server web console at port 8080 provides device management, gateway configuration, and handler setup. Its configuration is stored in an Mnesia database (Erlang's built-in distributed database) under `/tmp/lorawan-server`.

## Why Self-Host Your LoRaWAN Network Server?

Running your own LoRaWAN network server eliminates recurring device subscription costs that commercial providers charge per sensor. When managing 500+ IoT endpoints across a campus or industrial facility, these fees add up quickly. A self-hosted server on a modest VPS ($10-20/month) handles thousands of devices at a fraction of the cost.

Data sovereignty is equally important. Environmental sensors, industrial telemetry, and agricultural monitoring data often has commercial value or regulatory implications. Self-hosting ensures raw sensor readings, device metadata, and network performance data remain under your control.

For organizations already running self-hosted IoT platforms like ThingsBoard, integrating a local LoRaWAN network server creates an end-to-end data pipeline from sensor to dashboard without leaving your infrastructure. See our [IoT platform comparison](../thingsboard-vs-iotsharp-vs-iot-dc3-self-hosted-iot-platform-guide-2026/) and [MQTT broker guide](../self-hosted-mqtt-platforms-mosquitto-emqx-hivemq-iot-guide-2026/) for complementary infrastructure. If your deployment also needs smart home integration, our [smart home bridge comparison](../zigbee2mqtt-vs-zwave-js-ui-vs-esphome-self-hosted-smart-home-bridges-guide/) covers complementary wireless protocol gateways.

## FAQ

### What is the difference between LoRa and LoRaWAN?

LoRa is the physical-layer radio technology that enables long-range, low-power wireless communication. LoRaWAN is the network-layer protocol that runs on top of LoRa, defining how devices join the network, how messages are encrypted, and how data is routed. Think of LoRa as the "wire" and LoRaWAN as the "protocol" — you need both for a functioning IoT network.

### How many devices can a self-hosted LoRaWAN server handle?

ChirpStack and The Things Stack have been tested with 10,000+ devices in production deployments. The actual limit depends on your server resources and gateway density. lorawan-server is designed for smaller deployments (hundreds to low thousands of devices) on resource-constrained hardware.

### Do I need a physical LoRa gateway to use these network servers?

Yes, you need at least one LoRaWAN-compatible gateway (like a RAKwireless, Multitech, or Kerlink gateway) to receive radio signals from end devices. The gateway forwards packets to your network server over UDP (Semtech UDP protocol) or MQTT. Some gateways can be configured as "packet forwarders" that send raw LoRa packets to your server.

### Can these network servers work with any LoRaWAN device?

Yes, as long as the device supports LoRaWAN 1.0.x or 1.1.x specification. Devices join the network using either OTAA (Over-The-Air Activation, more secure) or ABP (Activation By Personalization, simpler setup). You will need the device's DevEUI, AppEUI, and AppKey for OTAA, or DevAddr and session keys for ABP.

### Which network server should I choose for a small deployment?

For small deployments (under 100 devices, single gateway), lorawan-server offers the simplest setup with the lowest resource requirements. For medium to large deployments with multi-tenancy, geolocation, and advanced routing needs, ChirpStack or The Things Stack are better choices. ChirpStack is generally preferred for private deployments due to its simpler architecture, while The Things Stack excels if you need global device roaming capabilities.

### How do I integrate LoRaWAN sensor data with my applications?

All three network servers support MQTT and HTTP webhooks for data delivery. Configure an MQTT topic or HTTP endpoint in the network server, and your application subscribes to receive decoded sensor data. For complete IoT data pipelines, consider integrating with platforms like ThingsBoard or Node-RED for visualization and automation.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Best Self-Hosted LoRaWAN Network Servers in 2026",
  "description": "Compare ChirpStack, The Things Stack, and lorawan-server — the top open-source LoRaWAN network servers for private IoT deployments.",
  "datePublished": "2026-05-04",
  "dateModified": "2026-05-04",
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
