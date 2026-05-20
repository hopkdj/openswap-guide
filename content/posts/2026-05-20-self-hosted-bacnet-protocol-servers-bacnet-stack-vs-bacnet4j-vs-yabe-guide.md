---
title: "Self-Hosted BACnet Protocol Servers: bacnet-stack vs BACnet4J vs YABE (Building Automation Guide)"
date: "2026-05-20"
tags: ["bacnet", "building-automation", "iot", "self-hosted", "docker", "protocol", "guide"]
draft: false
---

Building automation systems (BAS) manage HVAC, lighting, fire safety, and access control in commercial and industrial facilities. At the heart of most BAS deployments is **BACnet** (Building Automation and Control Networks), the ANSI/ASHRAE Standard 135 protocol that enables interoperability between devices from different manufacturers.

This guide compares three self-hosted BACnet server implementations you can deploy on your own infrastructure for building automation simulation, testing, and gateway services.

## What Is BACnet?

BACnet is an open communication protocol specifically designed for building automation and control networks. Unlike proprietary protocols from vendors like Siemens, Honeywell, or Johnson Controls, BACnet provides a standardized way for devices to communicate regardless of manufacturer.

Key BACnet concepts:

- **Objects**: Virtual representations of physical devices (analog inputs, binary outputs, schedules)
- **Properties**: Attributes of objects (present value, status flags, description)
- **Services**: Operations like ReadProperty, WriteProperty, Who-Is, I-Am
- **Network Layer**: Routing between BACnet/IP, MS/TP, and ARCNET segments

A self-hosted BACnet server lets you simulate devices, build gateways between protocols, test BAS integrations, or run a central building management system without vendor lock-in.

## BACnet Protocol Stack (bacnet-stack)

**GitHub**: [bacnet-stack/bacnet-stack](https://github.com/bacnet-stack/bacnet-stack) | ⭐ 563+ | Last active: May 2026

The **BACnet Protocol Stack** (originally by Steve Karg) is the most widely used open-source BACnet implementation. Written in C, it provides a complete BACnet application layer, network layer, and MAC layer stack supporting BACnet/IP, MS/TP, and Ethernet.

### Key Features

- Full BACnet device simulation (server) and client capabilities
- Supports BACnet/IP, MS/TP, Ethernet, and ARCNET
- Implements all standard BACnet object types (Analog Input, Analog Output, Binary Input, Binary Output, Analog Value, Binary Value, Schedule, etc.)
- BACnet Secure Connect (BACnet/SC) support in newer versions
- Cross-platform: Linux, Windows, macOS, embedded systems

### Docker Deployment

```yaml
services:
  bacnet-server:
    image: bacnet/bacnet-stack:latest
    container_name: bacnet-server
    network_mode: host
    environment:
      - BACNET_IFACE=eth0
      - BACNET_PORT=47808
      - DEVICE_ID=1234
      - DEVICE_NAME="Self-Hosted BACnet Server"
    volumes:
      - ./config:/etc/bacnet
      - ./data:/var/lib/bacnet
    restart: unless-stopped
```

The BACnet stack requires host networking because BACnet uses broadcast discovery (Who-Is/I-Am) that doesn't work across Docker bridge networks.

### Use Cases

- **Device simulation**: Test BACnet integrations before deploying physical hardware
- **Gateway development**: Bridge BACnet to MQTT, REST APIs, or other protocols
- **BAS testing**: Validate BACnet client applications against a known-good server
- **Educational**: Learn BACnet protocol internals with a reference implementation

## BACnet4J

**GitHub**: [infiniteautomation/BACnet4J](https://github.com/infiniteautomation/BACnet4J) | ⭐ 380+ | Last active: 2026

**BACnet4J** is a pure Java implementation of the BACnet protocol stack, maintained by Infinite Automation Systems (the company behind Mango Automation). It provides a high-level API for building BACnet applications in Java.

### Key Features

- Pure Java implementation — runs anywhere with a JVM
- Full BACnet/IP support with device discovery
- Object-oriented API for BACnet objects and services
- Built-in BACnet device simulator
- Integrates seamlessly with Mango Automation platform
- Supports BACnet scheduling, trending, and alarm management

### Docker Deployment

```yaml
services:
  bacnet4j-server:
    image: infiniteautomation/bacnet4j:latest
    container_name: bacnet4j-server
    network_mode: host
    environment:
      - JAVA_OPTS=-Xmx512m
      - BACNET_LOCAL_PORT=47808
      - BACNET_DEVICE_ID=5678
    volumes:
      - ./bacnet4j-data:/opt/bacnet4j/data
    restart: unless-stopped
```

BACnet4J's Java-based architecture makes it easier to extend and customize than the C stack, at the cost of higher memory usage (typically 200-500MB JVM overhead).

### Use Cases

- **Custom BACnet applications**: Build Java-based BACnet clients or servers
- **Mango Automation integration**: Native BACnet support for the Mango platform
- **Enterprise BAS**: Java ecosystem compatibility for large-scale deployments
- **Protocol research**: Readable Java codebase for understanding BACnet internals

## YABE (Yet Another BACnet Explorer)

**GitHub**: [YABE Project](https://sourceforge.net/projects/yabe/) | Active community | Last active: 2026

**YABE** (Yet Another BACnet Explorer) is a Windows-based BACnet tool that serves as both a BACnet device explorer and a simple BACnet server simulator. While primarily a desktop application, it can be run in headless mode on Linux via Wine or Docker for automated testing.

### Key Features

- BACnet device discovery and browsing (Who-Is/I-Am)
- Read/write BACnet object properties
- BACnet trend log viewing
- Simple device simulation for testing
- Graphical interface for BACnet network exploration
- Supports BACnet/IP and BACnet MS/TP (via serial adapter)

### Docker Deployment

```yaml
services:
  yabe-server:
    image: linuxserver/yabe:latest
    container_name: yabe-server
    network_mode: host
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    volumes:
      - ./yabe-config:/config
    restart: unless-stopped
```

YABE is the most accessible BACnet tool for beginners, with a GUI that visualizes BACnet networks and devices in real-time.

### Use Cases

- **Network discovery**: Map all BACnet devices on your building network
- **Troubleshooting**: Diagnose BACnet communication issues
- **Quick testing**: Spin up a simulated BACnet device without coding
- **Training**: Visual interface ideal for learning BACnet concepts

## Comparison Table

| Feature | bacnet-stack | BACnet4J | YABE |
|---------|-------------|----------|------|
| **Language** | C | Java | C# (.NET) |
| **Platforms** | Linux, Windows, macOS, Embedded | Any JVM | Windows, Linux (Wine) |
| **BACnet/IP** | ✅ Full | ✅ Full | ✅ Full |
| **MS/TP** | ✅ Full | ❌ | ✅ Via serial |
| **BACnet/SC** | ✅ Emerging | ❌ | ❌ |
| **Device Simulation** | ✅ Command-line | ✅ Programmatic | ✅ GUI-based |
| **Docker Support** | ✅ Official image | ✅ Community image | ✅ LinuxServer |
| **Memory Usage** | ~10MB | ~200-500MB | ~50-100MB |
| **GitHub Stars** | 563+ | 380+ | N/A (SourceForge) |
| **Best For** | Production gateways | Java apps, Mango | Exploration, training |

## Choosing the Right BACnet Server

**Use bacnet-stack when:**
- You need the most complete and battle-tested BACnet implementation
- Memory footprint matters (embedded systems, containers)
- You're building a production BACnet gateway or server
- You need MS/TP or BACnet/SC support

**Use BACnet4J when:**
- You're building Java-based BACnet applications
- You need integration with Mango Automation
- You prefer an object-oriented API over C pointers
- Your team has Java expertise

**Use YABE when:**
- You need to explore and troubleshoot existing BACnet networks
- You want a visual representation of BACnet objects and services
- You're training staff on BACnet concepts
- You need quick device simulation without writing code

## Why Self-Host BACnet Infrastructure?

Commercial BACnet management tools from vendors like Siemens, JCI, and Schneider Electric can cost thousands of dollars per license. Self-hosted BACnet servers provide:

- **Cost savings**: Open-source BACnet tools are free, eliminating per-device licensing fees
- **Vendor independence**: Test integrations across multiple BACnet device vendors without proprietary toolchains
- **Development flexibility**: Build custom BACnet gateways, simulators, and monitoring tools
- **Data ownership**: Keep building automation data on-premises without cloud dependencies
- **Compliance**: Meet data residency requirements for critical infrastructure

For broader building automation needs, see our guides on [self-hosted IoT device firmware](../2026-05-23-self-hosted-iot-device-firmware-esphome-tasmota-espurna-guide/) and [self-hosted gNMI telemetry streaming](../2026-05-23-self-hosted-gnmi-telemetry-streaming-telegraf-vs-opentelemetry-collector-vs-gnmic-guide/). If you need industrial protocol support beyond BACnet, check our [CoAP protocol servers guide](../2026-05-23-self-hosted-coap-protocol-servers-eclipse-californium-vs-leshan-vs-copper-guide/) for lightweight IoT alternatives.

## FAQ

### What is BACnet used for in building automation?

BACnet (Building Automation and Control Networks) is the standard protocol for communication between building management systems. It controls HVAC, lighting, fire detection, access control, and energy metering across devices from different manufacturers, ensuring interoperability without vendor lock-in.

### Can I run BACnet servers in Docker containers?

Yes, all three BACnet implementations in this guide support Docker deployment. However, BACnet uses broadcast discovery (Who-Is/I-Am messages), which requires `network_mode: host` in Docker Compose. Standard bridge networking will prevent BACnet device discovery from working correctly.

### What is the difference between BACnet/IP and BACnet MS/TP?

BACnet/IP runs over Ethernet using UDP port 47808 and is used for IP-connected devices. BACnet MS/TP (Master-Slave/Token-Passing) runs over RS-485 serial networks and is used for field-level devices like thermostats and VAV controllers. Most gateways bridge between the two.

### Is BACnet secure?

Traditional BACnet has no built-in encryption or authentication. BACnet/SC (Secure Connect), introduced in the 2020 standard, adds TLS-based encryption and device authentication. The bacnet-stack project has begun implementing BACnet/SC support. For critical infrastructure, always deploy BACnet on isolated network segments.

### What port does BACnet use?

BACnet/IP uses UDP port 47808 (decimal) or 0xBAC0 (hexadecimal). This is a well-known port registered with IANA. MS/TP uses RS-485 serial communication and doesn't use IP ports.

### How do I discover BACnet devices on my network?

Use the BACnet Who-Is service to broadcast a discovery request. All BACnet devices respond with I-Am messages containing their device ID, object name, and network address. YABE provides a graphical Who-Is interface, while bacnet-stack offers command-line tools (`bacwi` for Who-Is, `bacrp` for Read Property).

### Can BACnet integrate with MQTT or REST APIs?

Yes. You can build BACnet-to-MQTT gateways using any of the three implementations. The bacnet-stack C library is commonly used for this purpose, reading BACnet object values and publishing them to MQTT topics. BACnet4J also supports building REST API wrappers around BACnet services.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted BACnet Protocol Servers: bacnet-stack vs BACnet4J vs YABE (Building Automation Guide)",
  "description": "Compare open-source BACnet server implementations for building automation: bacnet-stack, BACnet4J, and YABE. Includes Docker deployment configs and feature comparison.",
  "datePublished": "2026-05-20",
  "dateModified": "2026-05-20",
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
