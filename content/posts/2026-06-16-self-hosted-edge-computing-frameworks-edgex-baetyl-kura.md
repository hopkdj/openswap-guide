---
title: "Self-Hosted Edge Computing Frameworks: EdgeX Foundry vs Baetyl vs Eclipse Kura"
date: "2026-06-16"
tags: ["edge-computing", "iot", "edge-frameworks", "self-hosted", "docker"]
draft: false
---

## Introduction

Edge computing brings data processing closer to where data is generated — on factory floors, in retail stores, across smart buildings, and throughout distributed infrastructure. Rather than shipping all sensor data to the cloud, edge frameworks run analytics, filtering, and decision logic directly on local gateway hardware.

This article compares three leading open-source edge computing frameworks: **EdgeX Foundry**, **Baetyl**, and **Eclipse Kura**. All three can be self-hosted on modest hardware (Raspberry Pi, Intel NUC, or industrial gateways) and provide the foundational layer for building IoT and edge solutions without vendor lock-in.

## Feature Comparison

| Feature | EdgeX Foundry | Baetyl | Eclipse Kura |
|---------|--------------|--------|--------------|
| **Initial Release** | 2017 | 2019 | 2013 |
| **GitHub Stars** | 1,517 | 1,902 | 566 |
| **License** | Apache 2.0 | Apache 2.0 | Eclipse Public 2.0 |
| **Language** | Go | Go | Java |
| **Architecture** | Microservices | Modular Engine | OSGi Framework |
| **Docker Support** | Native (Compose) | Native (Compose) | Container/Deb |
| **Device SDK** | C, Go, Python | Go, Python, JS | Java, C |
| **Protocol Support** | MQTT, REST, Modbus, BACnet, OPC-UA, BLE, Zigbee | MQTT, HTTP, OPC-UA, Modbus, BLE | MQTT, Modbus, CAN bus, GPIO, Serial |
| **Northbound Integration** | REST, MQTT, Kafka | MQTT, HTTP, Kafka | MQTT, REST, Cloud connectors |
| **Rule Engine** | Built-in (eKuiper) | Built-in (Baetyl Rule) | Wires (Kura Wires) |
| **Cloud Integration** | AWS, Azure, GCP | Baidu Cloud, AWS, Azure | AWS, Azure, GCP, Eurotech |
| **Security** | API Gateway, Secret Store, ACL | TLS, Certificate Auth | SSL, Key Management |
| **Web Dashboard** | Yes (EdgeX UI) | Yes (Baetyl Dashboard) | Yes (Kura Web Console) |

## EdgeX Foundry: The Linux Foundation Standard

EdgeX Foundry, hosted by the Linux Foundation's LF Edge umbrella, is arguably the most well-known open-source edge platform. Its microservices architecture breaks down edge functionality into discrete services — core data, command, metadata, registry, device services, and application services — all communicating via REST APIs and message bus.

### Key Strengths

- **Vendor-neutral**: Backed by Dell, Intel, VMware, and 100+ other organizations
- **Microservices architecture**: Each service runs independently in its own container, allowing selective scaling
- **Extensive protocol support**: Device services exist for Modbus, BACnet, OPC-UA, BLE, MQTT, GPIO, and camera protocols
- **North-south separation**: Clean separation between device-facing "south" services and cloud-facing "north" services
- **Built-in rules engine**: eKuiper provides SQL-based stream processing at the edge

### Docker Compose Deployment

```yaml
version: "3.7"
services:
  consul:
    image: consul:1.15
    ports:
      - "8500:8500"
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  core-data:
    image: edgexfoundry/core-data:latest
    depends_on:
      - consul
      - redis
    environment:
      - DATABASES_PRIMARY_HOST=redis
      - REGISTRY_HOST=consul
    ports:
      - "59880:59880"
  
  core-command:
    image: edgexfoundry/core-command:latest
    depends_on:
      - consul
    environment:
      - REGISTRY_HOST=consul
    ports:
      - "59882:59882"
  
  core-metadata:
    image: edgexfoundry/core-metadata:latest
    depends_on:
      - consul
      - redis
    environment:
      - DATABASES_PRIMARY_HOST=redis
      - REGISTRY_HOST=consul
    ports:
      - "59881:59881"
  
  device-virtual:
    image: edgexfoundry/device-virtual:latest
    depends_on:
      - consul
      - core-data
    environment:
      - REGISTRY_HOST=consul
    ports:
      - "59900:59900"
```

## Baetyl: Cloud-Native Edge with Kubernetes DNA

Baetyl (formerly OpenEdge) was originally developed by Baidu and donated to the Linux Foundation. It takes a cloud-native approach, treating edge nodes as extensions of Kubernetes clusters. Baetyl's architecture is built around a core engine that manages function runtimes, data synchronization, and device connectivity.

### Key Strengths

- **Kubernetes-native design**: Edge nodes run as K3s/kubelet extensions, enabling GitOps workflows
- **Function-as-a-Service at edge**: Run Python, Node.js, and SQL functions directly on edge devices
- **Shadow mode**: Bidirectional device shadow synchronization between cloud and edge
- **Offline-first**: Continues operating during network disconnections with local state storage
- **Volume mounting**: Support for mounting local storage, config maps, and secrets to function runtimes

### Docker Compose Deployment

```yaml
version: "3.7"
services:
  baetyl-broker:
    image: baetyltech/baetyl-broker:latest
    ports:
      - "1883:1883"
      - "8883:8883"
  
  baetyl-init:
    image: baetyltech/baetyl-init:latest
    volumes:
      - baetyl-data:/var/lib/baetyl
  
  baetyl-core:
    image: baetyltech/baetyl-core:latest
    volumes:
      - baetyl-data:/var/lib/baetyl
    ports:
      - "9003:9003"
    depends_on:
      - baetyl-broker
  
  baetyl-function:
    image: baetyltech/baetyl-function:latest
    volumes:
      - baetyl-data:/var/lib/baetyl
    depends_on:
      - baetyl-core

volumes:
  baetyl-data:
```

## Eclipse Kura: Battle-Tested Industrial Gateway

Eclipse Kura is the veteran of the group, with over a decade of industrial deployments. It's an OSGi-based Java framework designed specifically for IoT gateways. Kura runs directly on edge hardware (not just in containers) and provides deep integration with hardware interfaces.

### Key Strengths

- **Hardware-native**: Runs on bare metal or as a container on ARM and x86 architectures
- **Industrial protocol depth**: Native support for CAN bus, Modbus RTU/TCP, serial RS-232/485, GPIO, I2C, and SPI
- **OSGi modularity**: Hot-swappable bundles allow adding/removing functionality without restarting the gateway
- **Mature ecosystem**: 10+ years of production use in manufacturing, energy, and transportation
- **Kura Wires**: Visual drag-and-drop data flow composer for building edge logic without coding
- **Cloud connectors**: Built-in connectors for AWS IoT, Azure IoT Hub, Google Cloud IoT, and Eurotech Everyware Cloud

### Installation on Debian/Ubuntu

```bash
# Install Java 17
apt-get update && apt-get install -y openjdk-17-jdk

# Download Kura
wget https://download.eclipse.org/kura/releases/5.4.0/kura_5.4.0_raspberry-pi_installer.deb

# Install Kura
dpkg -i kura_5.4.0_raspberry-pi_installer.deb

# Access web console at https://<gateway-ip>:443
# Default credentials: admin / admin
```

## Choosing the Right Edge Framework

Each framework serves a distinct deployment model:

- **Choose EdgeX Foundry** if you need a vendor-neutral, microservices-based platform with the broadest protocol support and an active Linux Foundation community. Ideal for brownfield deployments where you need to connect diverse industrial protocols.

- **Choose Baetyl** if your infrastructure is Kubernetes-native and you want to extend cloud-native practices (GitOps, containerized functions) to the edge. Best for greenfield deployments with a DevOps-oriented team.

- **Choose Eclipse Kura** if you need deep hardware integration on resource-constrained industrial gateways, with native CAN bus, serial, and GPIO support. Ideal for manufacturing, automotive, and energy sector deployments.

## Hardware Requirements

| Framework | Min RAM | Min Storage | Architecture |
|-----------|---------|-------------|--------------|
| EdgeX Foundry | 1 GB | 4 GB | x86_64, ARMv7, ARM64 |
| Baetyl | 512 MB | 2 GB | x86_64, ARMv7, ARM64 |
| Eclipse Kura | 256 MB | 1 GB | x86_64, ARMv6+, ARM64 |

All three frameworks can run on a Raspberry Pi 4 (4 GB model recommended for EdgeX) or an Intel NUC. EdgeX has the highest resource requirements due to its microservices architecture, while Kura is the most lightweight option.

## Why Self-Host Your Edge Computing Platform?

Running your own edge computing framework gives you complete control over how data is processed, where it's stored, and who has access to it. Unlike cloud-only IoT platforms that charge per-device or per-message fees, self-hosted edge platforms scale with your hardware investment, not your data volume.

Data sovereignty is particularly critical in edge computing. Manufacturing lines, energy grids, and healthcare facilities generate sensitive operational data that often cannot leave the premises due to regulatory requirements (GDPR, HIPAA, NIST 800-53). Edge frameworks keep processing local — data never leaves your network unless you explicitly configure northbound routing.

Vendor lock-in is another major consideration. Cloud IoT platforms like AWS IoT Core, Azure IoT Hub, and Google Cloud IoT provide convenience at the cost of deep platform dependency. Migrating 10,000 devices from one cloud to another is a months-long engineering project. EdgeX, Baetyl, and Kura all support multiple cloud backends, giving you the flexibility to switch cloud providers or go fully on-premises without firmware changes.

Finally, cost predictability is compelling. Industrial IoT deployments with thousands of sensors can generate millions of messages per day. Cloud platforms charge per message, per rule evaluation, and per GB processed. A self-hosted edge platform running on a $200 Intel NUC processes all that data locally — your only recurring cost is electricity. For related deployment strategies, see our [self-hosted IoT device management guide](../2026-05-09-self-hosted-iot-device-management-kaa-vs-devicehive-vs-mainflux-guide/). If you are also managing Kubernetes clusters, our [KubeEdge vs OpenYurt guide](../2026-04-23-kubeedge-vs-openyurt-vs-superedge-self-hosted-edge-computing-guide-20/) covers the Kubernetes-native edge approach.

## FAQ

**Can I run all three frameworks on the same gateway?**

Technically yes, but it is not recommended. Each framework expects to manage device connections and data routing independently. Running them simultaneously would create conflicts on MQTT ports, device drivers, and system resources. Choose one framework per gateway based on your specific requirements.

**Which framework has the best MQTT support?**

All three support MQTT, but EdgeX Foundry has the most mature implementation with its dedicated MQTT device service and application service. Baetyl's built-in MQTT broker (based on VerneMQ) provides high-throughput messaging. Kura integrates with Eclipse Mosquitto and Paho for MQTT connectivity.

**How does edge computing differ from fog computing?**

Edge computing runs processing directly on the device gateway (Raspberry Pi, industrial PC), while fog computing distributes processing across an intermediate layer between devices and cloud (typically a local server or micro-datacenter). EdgeX, Baetyl, and Kura are all edge frameworks — they run on the gateway itself. Fog platforms like Apache Edgent or Cisco IOx sit one layer above.

**Can I use these frameworks for home automation?**

Kura and EdgeX are overkill for most home automation use cases — Home Assistant, OpenHAB, or Node-RED are more appropriate. However, if you are building a commercial-grade smart building system with BACnet or Modbus integration, EdgeX or Kura would be suitable choices.

**Do these frameworks support offline operation?**

Yes, all three support offline/disconnected operation. Kura has the most mature offline capabilities with local data storage and store-and-forward synchronization. Baetyl's shadow mode also handles disconnections gracefully. EdgeX can operate fully offline with data buffered locally.

**Which is easiest for a proof of concept?**

Baetyl has the quickest time-to-first-metric with its Docker Compose deployment — you can be ingesting simulated sensor data in under 10 minutes. EdgeX requires more configuration but has extensive documentation and tutorials. Kura has the steepest learning curve due to its OSGi architecture but offers the most industrial protocol depth.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Edge Computing Frameworks: EdgeX Foundry vs Baetyl vs Eclipse Kura",
  "description": "Compare three leading open-source edge computing frameworks: EdgeX Foundry, Baetyl, and Eclipse Kura. Includes Docker Compose deployment, protocol support comparison, and hardware requirements.",
  "datePublished": "2026-06-16",
  "dateModified": "2026-06-16",
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
