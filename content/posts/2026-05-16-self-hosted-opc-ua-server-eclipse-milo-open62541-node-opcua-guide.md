---
title: "Self-Hosted OPC UA Server: Eclipse Milo vs open62541 vs node-opcua"
date: "2026-05-16"
tags: ["opc-ua", "industrial-iot", "scada", "server", "protocol"]
draft: false
---

OPC UA (Open Platform Communications Unified Architecture) is the dominant industrial communication protocol for machine-to-machine data exchange in manufacturing, process automation, and industrial IoT. Unlike its predecessor OPC Classic (Windows-only, DCOM-based), OPC UA is platform-independent, secure, and supports information modeling natively.

In this guide, we compare three leading open-source OPC UA server implementations: **Eclipse Milo** (Java), **open62541** (C), and **node-opcua** (TypeScript/Node.js). Each brings distinct advantages depending on your infrastructure requirements, development language preference, and performance needs.

## What Is OPC UA and Why Self-Host a Server?

OPC UA defines a standardized way for industrial devices — PLCs, sensors, SCADA systems, HMIs — to communicate securely across network boundaries. The protocol supports:

- **Information modeling** — complex data structures with hierarchical relationships
- **Pub/Sub and Client/Server** — multiple communication patterns
- **Built-in security** — X.509 certificates, encryption, authentication
- **Platform independence** — runs on Windows, Linux, embedded devices
- **Scalability** — from single sensor to enterprise-wide data aggregation

Self-hosting an OPC UA server gives you full control over your industrial data pipeline. Instead of relying on proprietary vendor servers with licensing costs and vendor lock-in, open-source OPC UA stacks let you build custom data acquisition pipelines, integrate with existing SCADA infrastructure, and deploy edge computing gateways on commodity hardware.

For organizations running self-hosted SCADA platforms like [FUXA, SCADA-LTS, or RapidSCADA](../2026-05-02-self-hosted-scada-systems-fuxa-scada-lts-rapidscada-guide/), an OPC UA server is the critical bridge between field devices and the visualization layer. Similarly, if you operate [MQTT platforms like Mosquitto, EMQX, or HiveMQ](../self-hosted-mqtt-platforms-mosquitto-emqx-hivemq-iot-guide-2026/), an OPC UA server can feed real-time telemetry into your message broker for downstream processing.

## Eclipse Milo — Enterprise-Grade Java OPC UA Stack

**GitHub:** [eclipse/milo](https://github.com/eclipse/milo) — 1,361+ stars | **License:** EPL-2.0

Eclipse Milo is the reference implementation of the OPC UA specification from the Eclipse Foundation. Written in Java, it provides both client and server stacks with full compliance to OPC UA 1.04 specifications.

### Key Features

- **Full OPC UA compliance** — passes UA certification test tools
- **Information model support** — custom node types, references, and data types
- **Security** — Basic128Rsa15, Basic256, Basic256Sha256 profiles
- **Pub/Sub** — UDP and MQTT-based publish-subscribe
- **Spring Boot integration** — easy embedding in enterprise applications
- **Maven artifacts** — clean dependency management

### Docker Deployment

```yaml
version: "3.8"
services:
  millo-opcua-server:
    image: eclipse/milo:latest
    container_name: milo-opcua-server
    ports:
      - "4840:4840"
      - "4841:4841"
    environment:
      - MILO_ENDPOINT=https://localhost:4840
      - MILO_SECURITY_POLICY=None
      - MILO_APPLICATION_URI=urn:milo-server:application
    volumes:
      - ./pki:/opt/milo/pki
    restart: unless-stopped
```

Milo's server exposes endpoints on port 4840 (default OPC UA port). The PKI directory stores X.509 certificates for secure communication. In production, configure a security policy like `Basic256Sha256` instead of `None`.

### When to Choose Eclipse Milo

- You have an existing Java/Spring Boot infrastructure
- You need full OPC UA specification compliance
- You require Pub/Sub alongside Client/Server patterns
- Enterprise integration with existing Java-based systems

## open62541 — High-Performance C OPC UA Implementation

**GitHub:** [open62541/open62541](https://github.com/open62541/open62541) — 3,099+ stars | **License:** MPL-2.0

open62541 is a free and open-source C implementation of OPC UA, designed for embedded systems and resource-constrained environments. It is one of the most popular OPC UA stacks, actively maintained by the open62541 community and Fraunhofer IOSB.

### Key Features

- **Embedded-friendly** — runs on microcontrollers, PLCs, and edge gateways
- **Highly modular** — compile only the features you need via CMake
- **Amalgamation** — single .c/.h file for easy integration into existing C projects
- **Pub/Sub over TSN** — time-sensitive networking for deterministic communication
- **Information model** — full support for custom data types and node management
- **CMake build system** — clean cross-compilation support

### Building from Source

```bash
git clone --recurse-submodules https://github.com/open62541/open62541.git
cd open62541
mkdir build && cd build
cmake -DBUILD_SHARED_LIBS=ON -DUA_ENABLE_SUBSCRIPTIONS=ON -DUA_ENABLE_PUBSUB=ON ..
make -j$(nproc)
sudo make install
```

### Docker Deployment

```yaml
version: "3.8"
services:
  open62541-server:
    image: open62541/open62541:latest
    container_name: open62541-server
    ports:
      - "4840:4840"
    environment:
      - UA_LOGLEVEL=300
      - UA_PORT=4840
    volumes:
      - ./config:/etc/open62541
      - ./pki:/etc/open62541/pki
    restart: unless-stopped
```

open62541 is particularly well-suited for deployment on industrial edge gateways and Raspberry Pi-based data acquisition nodes. Its small footprint (as low as 300KB compiled) makes it ideal for embedded deployments where Eclipse Milo's JVM overhead would be prohibitive.

### When to Choose open62541

- You need to run on embedded hardware or resource-constrained devices
- You prefer C/C++ development
- You need TSN (Time-Sensitive Networking) support for deterministic communication
- You want to integrate OPC UA into existing C/C++ applications

## node-opcua — TypeScript OPC UA for Modern Web Stacks

**GitHub:** [node-opcua/node-opcua](https://github.com/node-opcua/node-opcua) — 1,632+ stars | **License:** MIT

node-opcua is a full-featured OPC UA implementation written in TypeScript/JavaScript, running on Node.js. It provides both client and server stacks and is particularly popular in the industrial IoT community for building web-based dashboards and real-time monitoring systems.

### Key Features

- **Full TypeScript** — type-safe API with modern async/await patterns
- **Certificate management** — built-in PKI handling and certificate generation
- **Subscription and monitoring** — real-time data change notifications
- **Method calls** — invoke server methods from OPC UA clients
- **History access** — read historical data from server archives
- **npm ecosystem** — integrate with Express, Fastify, and other Node.js frameworks

### Installation

```bash
npm install node-opcua
```

### Quick Server Example

```typescript
import { OPCUAServer, Variant, DataType, StatusCodes } from "node-opcua";

async function main() {
  const server = new OPCUAServer({
    port: 4840,
    resourcePath: "/UA/MyServer",
    buildInfo: {
      productName: "MyOPCUAServer",
      buildNumber: "1.0.0",
      buildDate: new Date()
    }
  });

  await server.initialize();
  const addressSpace = server.engine.addressSpace;
  const namespace = addressSpace.getOwnNamespace();

  // Add a temperature variable
  const temperature = namespace.addVariable({
    organizedBy: addressSpace.rootFolder.objects,
    browseName: "Temperature",
    nodeId: "ns=1;s=Temperature",
    dataType: "Double",
    value: {
      get: () => new Variant({ dataType: DataType.Double, value: 23.5 })
    }
  });

  await server.start();
  console.log(`OPC UA server running on port ${server.endpoints[0].port}`);
}

main().catch(err => console.error(err));
```

### Docker Deployment

```yaml
version: "3.8"
services:
  node-opcua-server:
    image: node:20-alpine
    container_name: node-opcua-server
    working_dir: /app
    ports:
      - "4840:4840"
    volumes:
      - ./server:/app
      - ./pki:/app/pki
    command: >
      sh -c "npm install node-opcua && node server.js"
    restart: unless-stopped
```

node-opcua excels when you need to build web-based industrial dashboards, REST API wrappers around OPC UA data, or integrate industrial data into modern JavaScript application stacks. Its async/await API makes real-time subscription handling straightforward.

### When to Choose node-opcua

- You build web dashboards and need JavaScript/TypeScript integration
- You want modern async/await patterns for subscription handling
- You need to wrap OPC UA data in REST or GraphQL APIs
- Your team has strong Node.js expertise

## Feature Comparison

| Feature | Eclipse Milo | open62541 | node-opcua |
|---------|-------------|-----------|------------|
| Language | Java | C | TypeScript/Node.js |
| Stars | 1,361+ | 3,099+ | 1,632+ |
| License | EPL-2.0 | MPL-2.0 | MIT |
| OPC UA 1.04 | Full | Full | Full |
| Client/Server | Yes | Yes | Yes |
| Pub/Sub | Yes | Yes (TSN) | Yes |
| Security Profiles | All major | All major | All major |
| Embedded Support | Limited (JVM) | Excellent | Moderate |
| Build System | Maven | CMake | npm |
| Memory Footprint | ~100MB+ | ~300KB | ~50MB |
| Certification | UA Certified | UA Certified | In Progress |
| Windows/Linux/macOS | All | All | All |
| Docker Ready | Yes | Yes | Yes |

## Architecture and Integration Patterns

All three OPC UA servers can serve as the foundation for industrial data pipelines. A typical architecture places the OPC UA server at the factory floor level, collecting data from PLCs and sensors via OPC UA or bridging from legacy protocols (Modbus, BACnet). The server then exposes standardized data to higher-level systems.

Common integration patterns include:

- **OPC UA to MQTT bridge** — translate OPC UA data model to MQTT topics for [lightweight message brokers](../self-hosted-mqtt-platforms-mosquitto-emqx-hivemq-iot-guide-2026/)
- **OPC UA to time-series database** — persist historical data in InfluxDB, TimescaleDB, or similar
- **OPC UA to SCADA visualization** — feed real-time data to [SCADA platforms](../2026-05-02-self-hosted-scada-systems-fuxa-scada-lts-rapidscada-guide/) for HMI dashboards
- **OPC UA to digital twin** — map physical asset data to [digital twin models](../2026-05-02-eclipse-ditto-vs-fiware-vs-thingsboard-digital-twin-guide-2026/) for simulation and monitoring

For organizations deploying edge computing frameworks, the OPC UA server runs alongside [edge compute platforms](../2026-04-23-kubeedge-vs-openyurt-vs-superedge-self-hosted-edge-computing-guide-2026/) to process data locally before sending aggregated results to the cloud.

## Security Considerations

OPC UA has security built into the protocol specification. However, proper deployment requires attention to several areas:

- **Certificate management** — generate and rotate X.509 certificates regularly. All three servers support application-level certificates with automatic trust list management
- **User authentication** — configure username/password or X.509 user certificates instead of anonymous access
- **Network segmentation** — place OPC UA servers on isolated OT networks with firewalls between IT and OT zones
- **Endpoint configuration** — only expose necessary endpoints; disable unused security profiles
- **Audit logging** — enable session logging for compliance with industrial security standards (IEC 62443)

## Choosing the Right OPC UA Server

The decision depends on your deployment context:

- **Enterprise IT integration**: Choose Eclipse Milo for Java ecosystem compatibility, Spring Boot integration, and full OPC UA compliance.
- **Edge/embedded deployments**: Choose open62541 for minimal footprint, C/C++ integration, and embedded device support.
- **Web/IoT application development**: Choose node-opcua for TypeScript/JavaScript integration, modern async APIs, and npm ecosystem access.

Many organizations run multiple stacks — open62541 on edge gateways collecting data from field devices, and Eclipse Milo or node-opcua in the data center for aggregation and API serving.

## FAQ

### What is OPC UA used for in industrial automation?

OPC UA is the standard protocol for secure, reliable data exchange between industrial devices — PLCs, sensors, SCADA systems, HMIs, and enterprise systems. It replaces the legacy OPC Classic (Windows-only DCOM) protocol with a platform-independent, secure alternative that supports complex information modeling.

### Can I run OPC UA servers on Raspberry Pi or edge devices?

Yes. open62541 is particularly well-suited for Raspberry Pi and similar edge devices due to its small memory footprint (~300KB compiled) and C-based implementation. Eclipse Milo requires a JVM (more memory), and node-opcua needs Node.js runtime. For resource-constrained edge gateways, open62541 is the recommended choice.

### Is OPC UA secure by default?

OPC UA has security built into the protocol with encryption (AES), signing, and X.509 certificate-based authentication. However, "secure by default" depends on configuration — anonymous access is often enabled out-of-the-box. You should configure security profiles (Basic256Sha256), user authentication, and certificate management before deploying to production.

### Can OPC UA servers communicate over the internet?

Yes, OPC UA supports communication over any IP network. For internet-facing deployments, use OPC UA over HTTPS (port 443) or configure a reverse proxy. Many organizations use OPC UA Pub/Sub over MQTT for cloud connectivity, bridging OPC UA data to MQTT brokers.

### What is the difference between OPC UA Client/Server and Pub/Sub?

Client/Server is the traditional request-response pattern where clients connect to servers and read/write data. Pub/Sub (publish-subscribe) is a newer pattern (OPC UA 1.04+) where publishers broadcast data to subscribers via UDP or MQTT. Pub/Sub is better suited for high-frequency, many-to-many data distribution, while Client/Server is better for on-demand data access.

### How do I migrate from OPC Classic to OPC UA?

Most OPC UA servers include OPC wrapper functionality or can bridge from legacy OPC DA servers. Tools like OPC Proxy and commercial gateway products translate OPC DA to OPC UA. For new deployments, always prefer OPC UA natively — it is platform-independent, firewall-friendly, and supports modern security features that OPC Classic lacks.

### Do I need OPC UA certification for my server implementation?

For internal deployments, certification is not mandatory. However, if you plan to sell or distribute your OPC UA product, or if your customers require certified interoperability, you should pass the OPC Foundation certification test tools (CTT). Both Eclipse Milo and open62541 have passed certification. node-opcua certification is in progress.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted OPC UA Server: Eclipse Milo vs open62541 vs node-opcua",
  "description": "Compare three leading open-source OPC UA server implementations: Eclipse Milo (Java), open62541 (C), and node-opcua (TypeScript). Docker deployment, feature comparison, and integration patterns for industrial IoT.",
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
