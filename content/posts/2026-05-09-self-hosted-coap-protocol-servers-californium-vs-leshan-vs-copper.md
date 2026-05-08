---
title: "Self-Hosted CoAP Protocol Servers: Eclipse Californium vs Leshan vs Copper (2026)"
date: "2026-05-09"
tags: ["comparison", "guide", "self-hosted", "iot", "networking", "protocols"]
draft: false
description: "Compare Eclipse Californium, Leshan, and Copper for self-hosted CoAP (Constrained Application Protocol) servers. Complete guide for IoT device communication and resource directory management."
---

## Introduction

The **Constrained Application Protocol (CoAP)** is a specialized web transfer protocol designed for resource-constrained IoT devices and low-power networks. It brings RESTful architecture to environments where HTTP is too heavy — devices with limited memory, battery-powered sensors, and lossy wireless networks.

CoAP uses UDP instead of TCP, has a compact binary header (4 bytes vs HTTP's text-based headers), and supports observe patterns for real-time resource monitoring. It is the foundation for many IoT standards including OMA LwM2M (Lightweight M2M) for device management.

In this guide, we compare three open-source CoAP server implementations: **Eclipse Californium**, **Eclipse Leshan**, and **Copper (Cu)**.

## What Is CoAP and Why Does It Matter?

CoAP (RFC 7252) is designed for machine-to-machine communication in constrained environments. Key characteristics:

- **UDP-based** — no connection overhead, works over lossy networks
- **Compact binary format** — 4-byte header vs HTTP's verbose text headers
- **RESTful model** — GET, POST, PUT, DELETE methods similar to HTTP
- **Observe pattern** — subscribe to resource changes without polling
- **Block-wise transfer** — split large payloads into manageable chunks
- **DTLS security** — Datagram TLS for encrypted communication

### Why Self-Host CoAP Servers?

Commercial IoT cloud platforms (AWS IoT, Azure IoT Hub, Google Cloud IoT) require internet connectivity and per-device licensing. Self-hosted CoAP servers provide:

- **Fully local IoT communication** — devices never leave your network
- **No cloud dependency** — operations continue during internet outages
- **Cost-effective** — zero per-device fees regardless of scale
- **Protocol flexibility** — customize resource models and security policies
- **Edge computing** — process sensor data locally with minimal latency

## Project Overview

### Eclipse Californium

Eclipse Californium (github.com/eclipse-californium/californium, 800+ stars) is a Java-based CoAP framework that implements the full CoAP specification (RFC 7252) plus extensions. It provides both CoAP server and client implementations, supports CoAP over TCP, and includes a comprehensive resource directory.

**Strengths:**
- Full RFC 7252 compliance
- Java-based — runs anywhere with a JVM
- Supports CoAP over TCP (RFC 8323) for reliable transport
- Built-in resource directory (CoRE RD)
- Active Eclipse Foundation project
- Extensive test suite and documentation

**Weaknesses:**
- Java dependency — higher memory footprint than native implementations
- Requires JVM tuning for resource-constrained environments
- Less community adoption compared to LwM2M-specific servers
- Development pace is moderate

### Eclipse Leshan

Eclipse Leshan (github.com/eclipse-leshan/leshan, 500+ stars) is a Java implementation of the OMA LwM2M protocol built on top of CoAP. LwM2M is a device management protocol that uses CoAP as its transport layer. Leshan provides a complete LwM2M server with web-based device management interface.

**Strengths:**
- Complete LwM2M 1.0/1.1/1.2 server implementation
- Web-based device management dashboard
- Bootstrap server support for device provisioning
- Security support (PSK, RPK, X.509 certificates)
- Active Eclipse Foundation project
- Designed for large-scale IoT deployments

**Weaknesses:**
- LwM2M-specific — not a general-purpose CoAP server
- Java dependency — same JVM overhead as Californium
- Steeper learning curve (LwM2M object model)
- Smaller community than general CoAP implementations

### Copper (Cu)

Copper (github.com/eclipse/copper, 100+ stars) is a CoAP user agent (client) and browser extension originally developed for Firefox. The project also includes server-side components and testing tools. While primarily known as a debugging tool, Copper provides CoAP server implementations suitable for development and testing.

**Strengths:**
- Excellent CoAP debugging and testing capabilities
- Browser extension for interactive CoAP exploration
- Lightweight implementation
- Good for development and prototyping
- Part of the Eclipse IoT ecosystem

**Weaknesses:**
- Primarily a client/debugging tool, not a production server
- Limited documentation for server deployment
- Smaller feature set compared to Californium
- Less active development in recent years
- Not designed for large-scale IoT deployments

## Feature Comparison

| Feature | Eclipse Californium | Eclipse Leshan | Copper (Cu) |
|---|---|---|---|
| GitHub Stars | 800+ | 500+ | 100+ |
| Primary Purpose | CoAP framework | LwM2M server | CoAP debugger/client |
| Protocol Support | CoAP, CoAP over TCP | LwM2M over CoAP | CoAP client |
| Language | Java | Java | Java |
| CoAP RFC 7252 | Full | Via underlying stack | Full |
| CoAP over TCP (RFC 8323) | Yes | No | No |
| CoRE Resource Directory | Yes | Yes (LwM2M RD) | No |
| DTLS Support | Yes | Yes (PSK/RPK/X.509) | Limited |
| Web Management UI | No | Yes | Browser extension |
| Bootstrap Server | No | Yes | No |
| Production Ready | Yes | Yes | Development/testing |
| Docker Deployment | Yes | Yes | No official image |
| LwM2M Support | No (CoAP only) | Full (1.0/1.1/1.2) | No |
| Observability | Logging | Web dashboard | Console output |

## Docker Deployment

### Eclipse Californium Server

```yaml
version: "3"
services:
  californium:
    image: eclipse/californium:latest
    container_name: californium-server
    restart: unless-stopped
    ports:
      - "5683:5683/udp"    # CoAP
      - "5684:5684/udp"    # CoAPS (DTLS)
      - "5685:5685"        # CoAP over TCP
    volumes:
      - ./californium.properties:/app/californium.properties:ro
    environment:
      - JAVA_OPTS=-Xmx256m -Xms128m
```

```properties
# californium.properties
COAP port=5683
COAP secure port=5684
COAP TCP port=5685
# Enable resource directory
COAP_RD enabled=true
# DTLS configuration
COAP secure enabled=true
```

### Eclipse Leshan Server

```yaml
version: "3"
services:
  leshan:
    image: eclipse/leshan:latest
    container_name: leshan-server
    restart: unless-stopped
    ports:
      - "5683:5683/udp"    # CoAP
      - "5684:5684/udp"    # CoAPS
      - "8080:8080"        # Web UI
    volumes:
      - ./leshan.conf:/app/leshan.conf:ro
      - leshan-data:/data
    environment:
      - JAVA_OPTS=-Xmx512m -Xms256m
      - LESHAN_WEB_PORT=8080

volumes:
  leshan-data:
```

```conf
# leshan.conf - LwM2M server configuration
# CoAP settings
coap.port=5683
coap.secure.port=5684
# Security mode (PSK, RPK, or X509)
security.mode=PSK
# Device store location
device.store=/data/devices.json
# Bootstrap server
bootstrap.enabled=false
```

### Testing with Copper

For development and testing, run a local CoAP server and interact with it using Copper:

```bash
# Install Copper CLI (if available) or use the browser extension
# Start a simple CoAP server for testing
java -jar californium-server.jar &

# Test CoAP GET request
coap-client -m get coap://localhost:5683/.well-known/core

# Test CoAP POST with payload
coap-client -m post -e "temperature=25.3" coap://localhost:5683/sensors/temp

# Observe resource changes (CoAP observe pattern)
coap-client -m get -s 60 coap://localhost:5683/sensors/temp
```

## CoAP Resource Model

CoAP organizes data as resources in a hierarchical path structure, similar to HTTP URLs:

```
coap://iot-gateway.local:5683/
  .well-known/core          # Resource discovery
  /sensors/temperature      # GET current temperature
  /sensors/humidity         # GET current humidity
  /actuators/relay          # POST to toggle relay
  /config/sampling          # PUT to change sampling rate
```

### Resource Discovery

CoAP devices publish their available resources at the well-known URI:

```bash
# Discover all resources on a CoAP server
coap-client coap://device.local:5683/.well-known/core

# Response (Core Link Format):
# </sensors/temp>;rt="temperature-c";if="sensor";obs,
# </sensors/humidity>;rt="humidity-pct";if="sensor";obs,
# </actuators/relay>;rt="on-off";if="actuator";ct="text/plain",
# </config/sampling>;rt="config";if="config";ct="application/json"
```

## Security with DTLS

CoAP uses Datagram TLS (DTLS) for secure communication. All three implementations support DTLS with different authentication modes:

**Pre-Shared Key (PSK):** Simplest mode — devices and server share a secret key. Suitable for closed IoT deployments where key distribution is manageable.

**Raw Public Key (RPK):** Each device has a public/private key pair. The server validates device identity without certificate infrastructure. Good balance of security and simplicity.

**X.509 Certificates:** Full PKI-based authentication. Most secure but requires certificate management infrastructure. Recommended for large-scale deployments with strict security requirements.

```bash
# Generate PSK identity and key for a CoAP device
# On the server side, maintain a credential store
echo "device001:secret_key_12345" >> psk-credentials.conf

# Start DTLS-enabled CoAP server
coap-server -k psk-credentials.conf -p 5684
```

## Choosing the Right CoAP Server

**Choose Eclipse Californium if:**
- You need a general-purpose CoAP server and client framework
- You want full RFC 7252 compliance including CoAP over TCP
- You are building custom IoT applications on top of CoAP
- You need resource directory (CoRE RD) functionality

**Choose Eclipse Leshan if:**
- You are implementing OMA LwM2M device management
- You need a web-based device management dashboard
- You are deploying at scale (hundreds or thousands of devices)
- You need bootstrap server support for zero-touch provisioning

**Choose Copper if:**
- You need CoAP debugging and testing tools
- You are developing CoAP resources and need interactive testing
- You want a browser-based CoAP client for quick verification
- You are in the prototyping phase of an IoT project

## Why Self-Host Your CoAP Infrastructure?

Running your own CoAP server instead of relying on cloud IoT platforms offers significant advantages:

**Zero Latency for Time-Critical Operations:** Cloud-based IoT platforms introduce 100-500ms of round-trip latency. Self-hosted CoAP servers on your local network respond in under 10ms — critical for industrial automation, security systems, and real-time control applications.

**Complete Protocol Control:** Cloud platforms impose their own data models and API constraints. With a self-hosted CoAP server, you define your own resource hierarchy, observe patterns, and payload formats. This flexibility is essential for specialized industrial IoT applications.

**Offline Resilience:** Cloud-dependent IoT systems fail when internet connectivity is lost. Self-hosted CoAP infrastructure continues operating regardless of external network status. Your factory floor sensors, building automation systems, and security devices keep communicating through local CoAP networks.

**Cost Efficiency at Scale:** AWS IoT Core charges $5 per million messages. Azure IoT Hub has similar per-message pricing. A self-hosted CoAP server processes unlimited messages at the cost of electricity — for high-frequency telemetry (1-second sampling), this difference becomes enormous at scale.

**Data Sovereignty:** IoT data often includes sensitive operational information — production metrics, occupancy patterns, energy consumption, and security events. Self-hosted CoAP infrastructure ensures this data never traverses public networks or third-party servers.

For IoT device firmware, see our [ESPHome vs Tasmota vs ESPurna guide](../2026-05-09-self-hosted-iot-firmware-platforms-esphome-vs-tasmota-vs-espurna/).
For network telemetry collection, check our [gNMI Telemetry Streaming comparison](../2026-05-09-self-hosted-gnmi-telemetry-streaming-telegraf-vs-opentelemetry-vs-gnmic/).
For smart home protocol bridges, our [Zigbee2MQTT vs ZWave-JS guide](../zigbee2mqtt-vs-zwave-js-ui-vs-esphome-self-hosted-smart-home-bridges-guide-2026/) covers local IoT connectivity.

## Frequently Asked Questions

### What is the difference between CoAP and HTTP?

CoAP is designed for constrained devices and networks where HTTP is too resource-intensive. CoAP uses UDP (not TCP), has a 4-byte binary header (vs HTTP's text headers), supports multicast, and runs natively on devices with as little as 10KB of RAM. HTTP requires TCP connections, DNS resolution, and TLS handshakes that are impractical for battery-powered sensors.

### Can CoAP work over the internet?

Yes, but with caveats. UDP-based CoAP can traverse NAT and firewalls but may experience packet loss on unreliable networks. CoAP over TCP (RFC 8323, supported by Californium) provides reliable transport suitable for internet connections. For internet-facing IoT, consider CoAP over TCP or a cloud gateway that bridges local CoAP to HTTP/MQTT.

### How does CoAP compare to MQTT?

Both are popular IoT protocols but serve different purposes. MQTT requires a central broker and TCP connections, making it heavier but more reliable. CoAP is peer-to-peer, uses UDP, and has lower overhead. MQTT excels at publish/subscribe messaging across distributed systems, while CoAP is better for direct RESTful resource access on constrained devices. Many deployments use both — CoAP for device-level communication and MQTT for cloud integration.

### What port does CoAP use?

CoAP uses UDP port 5683 (unencrypted) and UDP port 5684 (with DTLS encryption). These are IANA-assigned well-known ports. CoAP over TCP uses port 5683 and 5685 (secure). Ensure your firewall allows UDP traffic on these ports between IoT devices and the CoAP server.

### Is CoAP secure enough for production IoT?

CoAP with DTLS provides strong encryption and authentication comparable to HTTPS. DTLS 1.2 (supported by all three implementations) uses the same cryptographic algorithms as TLS 1.2. For production deployments, use RPK or X.509 certificate authentication rather than PSK, and implement proper key rotation policies.

### Can I migrate from MQTT to CoAP?

Migration depends on your architecture. MQTT's publish/subscribe model does not map directly to CoAP's request/response and observe patterns. However, you can use a protocol gateway (like Eclipse Kura or Node-RED) to bridge between MQTT and CoAP. For new deployments, choose the protocol that best matches your device constraints and communication patterns.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted CoAP Protocol Servers: Eclipse Californium vs Leshan vs Copper (2026)",
  "description": "Compare Eclipse Californium, Leshan, and Copper for self-hosted CoAP protocol servers. Complete guide for IoT device communication and resource directory management.",
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
