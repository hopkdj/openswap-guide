---
title: "Self-Hosted DDS Middleware for Real-Time Data Distribution: Cyclone DDS vs OpenDDS vs Fast-DDS"
date: "2026-06-05"
tags: ["dds", "middleware", "real-time", "iot", "robotics", "data-distribution", "self-hosted", "publish-subscribe"]
draft: false
---

## Introduction

When systems need to exchange data with microsecond latency — autonomous vehicles coordinating sensor fusion, industrial robots synchronizing motion control, spacecraft managing telemetry — traditional message brokers introduce unacceptable overhead. The Data Distribution Service (DDS) standard, maintained by the Object Management Group (OMG), provides a decentralized publish-subscribe protocol designed from the ground up for real-time, mission-critical data exchange without a central broker.

Unlike MQTT or AMQP, DDS operates peer-to-peer with automatic discovery, quality-of-service (QoS) policies, and wire-level interoperability between vendors. This article compares three leading open-source DDS implementations — Eclipse Cyclone DDS, OpenDDS, and eProsima Fast-DDS — covering architecture, deployment, performance, and self-hosting considerations.

| Feature | Cyclone DDS | OpenDDS | Fast-DDS |
|---------|-------------|---------|----------|
| **Language** | C (with C++/Python bindings) | C++ (with Java/Python bindings) | C++ (with Python bindings) |
| **Transport** | UDP, TCP, shared memory | UDP, TCP, multicast, RTPS over UDP | UDP, TCP, shared memory, data-sharing |
| **Discovery** | Simple Discovery, DDS-Security | InfoRepo, RTPS discovery | Simple Discovery, Discovery Server |
| **QoS Profiles** | Full DDS QoS + Cyclone-specific extensions | Full DDS QoS with CORBA heritage | Full DDS QoS + Fast-DDS specific features |
| **Security** | DDS-Security plugin (built-in) | DDS-Security via OpenDDS Security | DDS-Security plugin (built-in) |
| **Stars** | 1,277 | 1,499 | 2,816 |
| **Latest Release** | Active (2026) | Active (2026) | Active (2026) |
| **Governance** | Eclipse Foundation | Object Computing Inc. (OCI) | eProsima (community-driven) |

## Architecture and Design Philosophy

### Cyclone DDS

Eclipse Cyclone DDS emerged from ADLINK's commercial DDS implementation and was donated to the Eclipse Foundation in 2019. It prioritizes minimal resource footprint and deterministic performance, making it the default DDS middleware in ROS 2 for non-enterprise deployments.

Key architectural decisions include a single-threaded event loop for predictable latency, zero-copy data paths using shared memory, and a focus on the DDS-XTypes specification for dynamic type handling. Cyclone DDS compiles to a compact shared library (~500KB) and runs comfortably on embedded Linux targets with as little as 64MB RAM.

### OpenDDS

OpenDDS takes a different approach, building on top of the TAO (The ACE ORB) CORBA framework. This gives it mature, battle-tested networking infrastructure but also introduces dependency complexity. OpenDDS was the first open-source DDS implementation and has seen production use in aerospace, defense, and healthcare systems for over 15 years.

Its InfoRepo-based discovery model provides centralized management of DDS participants, which simplifies security auditing and monitoring at the cost of introducing a potential single point of failure. OpenDDS also supports the DCPS (Data-Centric Publish Subscribe) and the full OMG DDS specification.

### Fast-DDS

eProsima Fast-DDS (formerly Fast RTPS) is the default middleware in ROS 2 for most deployments and has the largest community of the three with 2,816 GitHub stars. It emphasizes flexibility, offering multiple discovery mechanisms (simple discovery, discovery server, static endpoint discovery) and an extensive configuration API.

Fast-DDS introduces a unique "data-sharing" transport that uses shared memory for intra-process and inter-process communication on the same host, achieving latencies below 30 microseconds on modern hardware. It also supports XML profile-based configuration, which simplifies deployment in containerized environments.

## Deployment with Docker

### Cyclone DDS Container Setup

```yaml
# docker-compose.yml
version: '3.8'
services:
  cyclone-dds-app:
    image: ubuntu:22.04
    container_name: cyclone-dds-node
    environment:
      - CYCLONEDDS_URI=file:///config/cyclonedds.xml
    volumes:
      - ./config:/config
      - ./app:/app
    network_mode: host
    command: >
      bash -c "apt-get update && apt-get install -y libddsc0-tools && /app/dds_publisher"
```

Build from source for custom applications:

```bash
git clone https://github.com/eclipse-cyclonedds/cyclonedds.git
cd cyclonedds && mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=/usr/local -DBUILD_EXAMPLES=ON ..
make -j$(nproc) && sudo make install
```

### Fast-DDS Container Setup

```yaml
# docker-compose.yml
version: '3.8'
services:
  fastdds-app:
    image: ubuntu:22.04
    container_name: fastdds-node
    environment:
      - FASTRTPS_DEFAULT_PROFILES_FILE=/config/fastdds_profiles.xml
    volumes:
      - ./config:/config
      - ./app:/app
    network_mode: host
    command: >
      bash -c "apt-get update && apt-get install -y libfastrtps-dev fastdds-tools && /app/dds_app"
```

### OpenDDS Container Setup

```yaml
# docker-compose.yml
version: '3.8'
services:
  opendds-app:
    image: ubuntu:22.04
    container_name: opendds-node
    environment:
      - DDS_DOMAIN=42
      - DCPSConfigFile=/config/rtps.ini
    volumes:
      - ./config:/config
      - ./app:/app
    network_mode: host
    command: >
      bash -c "apt-get update && apt-get install -y libopendds-dev && /app/dds_participant"
```

## Performance Considerations

DDS middleware performance depends heavily on transport configuration and QoS policies. Here are key benchmarks from community testing:

| Metric | Cyclone DDS | OpenDDS | Fast-DDS |
|--------|-------------|---------|----------|
| **Intra-process latency** | ~5 μs | ~15 μs | ~3 μs |
| **Inter-process (shared memory)** | ~10 μs | ~25 μs | ~8 μs |
| **Network (UDP loopback)** | ~30 μs | ~50 μs | ~25 μs |
| **Throughput (1KB messages)** | 1.2M msg/s | 500K msg/s | 1.5M msg/s |
| **Memory footprint (idle)** | ~8 MB | ~25 MB | ~12 MB |

Fast-DDS leads in raw throughput due to its optimized data-sharing transport. Cyclone DDS offers the best balance of latency and resource usage. OpenDDS provides the most mature security infrastructure but trades some performance for its CORBA-based architecture.

## Choosing the Right DDS Implementation

**Choose Cyclone DDS when:**
- You need minimal resource footprint for embedded or resource-constrained devices
- Eclipse Foundation governance and IP clearance matter for your organization
- You want zero-copy shared memory with deterministic latency guarantees
- Your team is comfortable with C development and CMake build systems

**Choose OpenDDS when:**
- You have existing CORBA infrastructure or ACE/TAO expertise
- Centralized participant discovery (InfoRepo) simplifies your security architecture
- You need Java language bindings for enterprise integration
- Stringent regulatory compliance (DO-178C, FDA) requires the longest track record

**Choose Fast-DDS when:**
- You work with ROS 2 and want the default, best-supported middleware
- Maximum throughput and lowest latency are your primary concerns
- XML-based configuration management fits your DevOps pipeline
- The largest open-source community matters for your project's longevity

## Self-Hosting DDS Infrastructure

While DDS is peer-to-peer and doesn't require a central server in the traditional sense, production deployments often need supporting services:

```bash
# Fast-DDS Discovery Server (replaces Simple Discovery for WAN deployments)
docker run -d --name fastdds-discovery   --network host   -e ROS_DISCOVERY_SERVER=127.0.0.1:11811   ubuntu:22.04 bash -c "
    apt-get update && apt-get install -y fastdds-tools &&
    fastdds discovery --server-id 0 --ip-address 0.0.0.0 --port 11811
  "

# OpenDDS DCPSInfoRepo (centralized discovery)
docker run -d --name opendds-inforepo   --network host   -e DCPSInfoRepoPort=12345   ubuntu:22.04 bash -c "
    apt-get update && apt-get install -y libopendds-dev &&
    DCPSInfoRepo -ORBEndpoint iiop://0.0.0.0:12345
  "
```

For monitoring and observability, both Cyclone DDS and Fast-DDS expose internal metrics that can be scraped by Prometheus-compatible exporters.

## Why Self-Host Your DDS Middleware?

Running your own DDS infrastructure gives you complete control over real-time data flows without depending on cloud-based messaging services. For robotics, autonomous systems, and industrial IoT, the microseconds matter — every hop through a cloud broker adds latency that can compromise safety-critical decisions.

Self-hosting DDS means your data never leaves your network. In defense, healthcare, and manufacturing environments where data sovereignty is non-negotiable, this is the decisive factor. There is no vendor to go out of business, no API pricing to change, and no Terms of Service to suddenly restrict your use case.

The peer-to-peer nature of DDS also means your system survives network partitions gracefully. Unlike centralized brokers where a single server failure can bring down your entire messaging fabric, DDS participants continue operating locally and synchronize when connectivity returns. For distributed systems spanning multiple sites — factory floors, offshore platforms, vehicle fleets — this resilience is essential.

For complementary IoT infrastructure, see our [MQTT broker comparison guide](../2026-06-02-vernemq-vs-nanomq-vs-flashmq-mqtt-brokers-guide/). If you manage a fleet of embedded devices, our [IoT device management platform comparison](../2026-05-09-self-hosted-iot-device-management-kaa-vs-devicehive-vs-mainflux-guide/) provides guidance on device lifecycle tools. For sensor-level firmware, our [ESPHome vs Tasmota vs ESPurna guide](../2026-05-09-self-hosted-iot-firmware-platforms-esphome-vs-tasmota-vs-espurna/) covers over-the-air updates and configuration management.

## FAQ

### How does DDS differ from MQTT?

MQTT uses a centralized broker model (like Mosquitto or EMQX), while DDS is fully decentralized with peer-to-peer communication. DDS offers richer QoS policies (reliability, durability, deadline, liveliness, ownership) compared to MQTT's three QoS levels. DDS is designed for real-time systems with microsecond latency requirements, while MQTT targets IoT scenarios where a few milliseconds of latency is acceptable.

### Can DDS and MQTT coexist in the same system?

Yes, and this is a common architecture pattern. MQTT serves as the cloud-to-edge bridge for telemetry and command dissemination, while DDS handles the high-speed, real-time communication within the local network. Several integration bridges exist: the ROS 2 `mqtt_bridge` package and Eclipse zenoh can route between DDS and MQTT domains.

### Does DDS require a license server or commercial support?

No. All three implementations covered here — Cyclone DDS (Eclipse Public License 2.0), OpenDDS (custom open-source license similar to BSD), and Fast-DDS (Apache 2.0) — are fully open source with permissive licenses. Commercial support is available from ADLINK (Cyclone DDS), Object Computing (OpenDDS), and eProsima (Fast-DDS) but is entirely optional.

### Which DDS implementation does ROS 2 use?

ROS 2 supports multiple DDS implementations through its RMW (ROS Middleware) abstraction layer. Fast-DDS is the default RMW implementation for most ROS 2 distributions (Humble, Iron, Jazzy). Cyclone DDS is also fully supported and is the default in some embedded ROS 2 configurations. OpenDDS has an RMW implementation maintained by the community.

### What are the minimum hardware requirements?

Cyclone DDS can run on embedded Linux systems with as little as 64MB RAM and a 200MHz ARM processor. Fast-DDS requires approximately 128MB RAM for typical deployments. OpenDDS, due to its CORBA foundation, requires at least 256MB RAM. All three run on ARM, x86, and RISC-V architectures with Linux, and Cyclone DDS and Fast-DDS also support FreeRTOS and Zephyr RTOS for bare-metal deployments.

### Is DDS suitable for cloud-native applications?

DDS works in cloud environments but requires careful network configuration. The peer-to-peer discovery mechanism (multicast or unicast) needs to be configured for cloud networking, and you may need a Discovery Server (Fast-DDS) or InfoRepo (OpenDDS) as a centralized discovery point. For pure cloud-native pub-sub, NATS or Kafka may be simpler alternatives, but DDS is essential when the same data fabric must span edge devices and cloud services with consistent QoS guarantees.

## Related Tools and Ecosystem

Beyond the three implementations covered here, several related technologies complement DDS in a self-hosted real-time data stack:

- **Eclipse zenoh** — A next-generation pub-sub protocol that bridges DDS, MQTT, and REST with minimal wire overhead, designed for robotics and automotive applications.
- **RTI Connext DDS** — The commercial DDS implementation (not open source) that offers the most comprehensive tooling, including recording/replay, WAN routing, and a web-based administration console.
- **Gurum DDS** — A lightweight commercial DDS implementation from South Korea with strong ROS 2 support and a focus on automotive-grade reliability.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DDS Middleware for Real-Time Data Distribution: Cyclone DDS vs OpenDDS vs Fast-DDS",
  "description": "Comprehensive comparison of three open-source DDS implementations — Eclipse Cyclone DDS, OpenDDS, and eProsima Fast-DDS — covering architecture, Docker deployment, performance benchmarks, and self-hosting guidance for real-time data distribution in robotics, IoT, and industrial systems.",
  "datePublished": "2026-06-05",
  "dateModified": "2026-06-05",
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
