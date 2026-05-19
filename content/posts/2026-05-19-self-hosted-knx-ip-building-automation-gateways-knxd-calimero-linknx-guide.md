---
title: "Best Self-Hosted KNX/IP Gateways 2026: knxd vs Calimero vs linknx"
date: "2026-05-19"
tags: ["knx", "building-automation", "smarthome", "iot", "gateway"]
draft: false
---

KNX is the global standard for building automation, controlling everything from lighting and HVAC to blinds and security systems. But the native KNX bus uses a proprietary serial protocol that is not accessible from standard IP networks. This is where KNX/IP gateways come in — they bridge the KNX bus to IP, enabling modern software to control and monitor your building. This guide compares three leading open-source KNX/IP gateway servers: **knxd**, **Calimero Server**, and **linknx**.

## What Is a KNX/IP Gateway?

A KNX/IP gateway is a server application that translates between the KNX bus protocol (typically running over twisted-pair cable, powerline, or RF) and IP-based protocols. This enables:

- **Remote monitoring** — check the status of lights, sensors, and actuators from anywhere
- **Software control** — automate building functions through scripts and applications
- **Integration** — connect KNX to home automation platforms like Home Assistant, Node-RED, or custom dashboards
- **Data logging** — record and analyze building energy consumption, temperature trends, and occupancy patterns
- **Multi-client access** — allow multiple applications to communicate with the KNX bus simultaneously

Without an IP gateway, you would need the proprietary ETS engineering software to interact with the KNX bus, severely limiting automation possibilities.

## knxd: The Universal KNX Daemon

**GitHub:** [knxd/knxd](https://github.com/knxd/knxd) | **Stars:** 600+ | **Language:** C++

knxd (KNX Daemon) is the most popular open-source KNX/IP gateway, serving as the successor to the original eibd (EIB Daemon). It provides a comprehensive KNX IP routing solution that can connect to KNX bus interfaces via USB, serial, IP tunneling, or IP routing, and expose the bus to multiple client applications simultaneously.

### Key Features

- Multi-client support — unlimited simultaneous connections to the KNX bus
- Multiple backend interfaces: USB, serial (FT1.2), IP tunneling, IP routing, TPUART
- KNXnet/IP server mode — acts as a KNX/IP router for ETS and other clients
- Group address monitoring and writing
- Daemon mode with systemd integration
- Low-level KNX frame access for advanced applications
- Compatible with FTDI USB KNX interfaces (Weinzierl, Merten, Siemens)
- Active development with regular bug fixes and feature additions

### Docker Deployment

```yaml
version: "3.8"
services:
  knxd:
    image: ghcr.io/knxd/knxd:latest
    ports:
      - "3671:3671/udp"
      - "6720:6720"
    devices:
      - /dev/ttyUSB0:/dev/ttyUSB0
    environment:
      - KNXD_OPTS=-e 0.0.1 -E 0.0.2 -D -T -R -S -i --listen-local=/tmp/knx
    restart: unless-stopped
```

Installation from source on Debian/Ubuntu:

```bash
sudo apt install build-essential git cmake libusb-1.0-0-dev
git clone https://github.com/knxd/knxd.git
cd knxd
mkdir build && cd build
cmake ..
make -j$(nproc)
sudo make install
sudo systemctl enable knxd
sudo systemctl start knxd
```

## Calimero: Enterprise-Grade KNXnet/IP Server

**GitHub:** [calimero-project/calimero-server](https://github.com/calimero-project/calimero-server) | **Stars:** 74+ | **Language:** Java

Calimero is a comprehensive Java-based KNX library that includes a standalone KNXnet/IP server component. Originally developed as a research project, it has evolved into a production-ready KNX communication framework used in commercial building automation products.

### Key Features

- Full KNXnet/IP protocol stack (tunneling, routing, device management)
- Java API for building custom KNX applications
- KNX data point type (DPT) translation for all standard types
- Secure KNXnet/IP (KNX Data Security) support
- Group communication and individual address management
- KNX IP router and tunneling server modes
- Event-based programming model for responsive applications
- Cross-platform (runs anywhere Java runs)

### Docker Deployment

```yaml
version: "3.8"
services:
  calimero-server:
    image: calimero/knx-server:latest
    ports:
      - "3671:3671/udp"
      - "3671:3671/tcp"
    volumes:
      - ./calimero.properties:/opt/calimero/calimero.properties:ro
    environment:
      - KNX_INTERFACE=tpuart:/dev/ttyUSB0
      - KNX_INDIVIDUAL_ADDRESS=1.1.128
    devices:
      - /dev/ttyUSB0:/dev/ttyUSB0
    restart: unless-stopped
```

Calimero server configuration:

```properties
# calimero.properties
server.tunneling.endpoint = 1.1.128
server.tunneling.localhost = true
knx.server = true
knx.server.port = 3671
link.medium = TP1
connection.type = FT12
connection.device = /dev/ttyUSB0
```

## linknx: KNX Service with Rules Engine

**GitHub:** [linknx/linknx](https://github.com/linknx/linknx) | **Stars:** 50+ | **Language:** C++

linknx is a unique KNX service that goes beyond simple bus bridging — it includes a built-in rules engine for creating automation logic directly on the server. Instead of needing a separate home automation platform, linknx can execute conditional rules based on KNX bus events.

### Key Features

- KNX bus connectivity via KNXnet/IP or serial interfaces
- Built-in rules engine for automation logic
- Value caching to reduce bus traffic
- XML-based configuration for objects and rules
- HTTP/XML API for external control and monitoring
- Timer-based automation (schedules, delays, triggers)
- Logic operations (AND, OR, NOT, comparators)
- Integration with web visualization platforms

### Docker Deployment

```yaml
version: "3.8"
services:
  linknx:
    image: linknx/linknx:latest
    ports:
      - "1028:1028"
    volumes:
      - ./linknx.xml:/etc/linknx/linknx.xml:ro
      - ./config:/etc/linknx/config
    devices:
      - /dev/ttyUSB0:/dev/ttyUSB0
    environment:
      - LINKNX_OPTS=-c /etc/linknx/linknx.xml
    restart: unless-stopped
```

Example linknx automation rule:

```xml
<object id="living_room_temp" type="9.001" location="1/1/1" />
<object id="heater_valve" type="1.001" location="1/2/1" />

<rule id="heating_control">
  <condition>
    <less>
      <object ref="living_room_temp" />
      <value>20.0</value>
    </less>
  </condition>
  <action>
    <set object="heater_valve" value="1" />
  </action>
</rule>
```

## Comparison Table

| Feature | knxd | Calimero Server | linknx |
|---------|------|-----------------|--------|
| **GitHub Stars** | 600+ | 74+ | 50+ |
| **Language** | C++ | Java | C++ |
| **KNXnet/IP Server** | Yes | Yes | No (uses external) |
| **Multi-client** | Yes | Yes | Yes |
| **Rules Engine** | No | No | Yes |
| **Value Caching** | No | No | Yes |
| **USB Interface** | Yes | Yes | Via external |
| **TPUART** | Yes | Yes | Via external |
| **KNX Data Security** | Partial | Yes | No |
| **API** | Local socket | Java API | HTTP/XML |
| **ETS Compatible** | Yes | Yes | No |
| **Best For** | Universal gateway | Java integrations | Automation rules |

## Choosing the Right KNX Gateway

**knxd** is the best general-purpose KNX/IP gateway. It supports the widest range of hardware interfaces, handles multiple simultaneous clients efficiently, and is compatible with ETS and all major KNX software. If you need a reliable bridge between your KNX bus and IP network, knxd is the standard choice.

**Calimero Server** is ideal for Java-based building automation projects. The comprehensive Java API enables you to build custom KNX applications with full protocol support, including KNX Data Security. It is the best choice when you need programmatic access to KNX from a Java ecosystem.

**linknx** is unique in providing a built-in rules engine for KNX automation. If you want to implement conditional logic, schedules, and automated responses to KNX bus events without deploying a separate home automation platform, linknx is purpose-built for this use case.

## Why Self-Host Your KNX Gateway?

Running your own KNX/IP gateway keeps your building automation entirely local. Proprietary KNX gateways from manufacturers often require cloud connectivity, subscription services, or vendor-specific apps that limit your control and create vendor lock-in.

A self-hosted KNX gateway means your building automation continues to work even when the internet is down. All communication stays on your local network, ensuring privacy and eliminating latency. You can integrate KNX with any open-source home automation platform — Home Assistant, openHAB, Node-RED — without being restricted to a single vendor ecosystem.

For organizations managing commercial buildings, self-hosted KNX gateways enable custom energy management, occupancy-based HVAC control, and detailed building analytics without recurring SaaS fees.

For smart home integration, see our [Zigbee2MQTT vs Z-Wave JS UI vs ESPHome guide](../zigbee2mqtt-vs-zwave-js-ui-vs-esphome-self-hosted-smart-home-bridges-guide/) and [MQTT platforms comparison](../self-hosted-mqtt-platforms-mosquitto-emqx-hivemq-iot-guide-2026/).

## FAQ

### What hardware do I need to connect knxd to a KNX bus?

You need a KNX IP interface or USB KNX adapter. Popular options include the Weinzierl USB KNX interface, Merten USB interface, or any KNXnet/IP router. knxd supports USB (via FTDI chipsets), serial (FT1.2 protocol), and IP tunneling connections.

### Can multiple applications connect to knxd simultaneously?

Yes, knxd supports unlimited simultaneous client connections. This is one of its key advantages — you can have ETS, Home Assistant, a custom monitoring script, and a Node-RED flow all connected to the KNX bus at the same time through a single knxd instance.

### Does Calimero support KNX Data Security (KDS)?

Yes, Calimero supports KNX Data Security (KNX Secure), which provides encryption and authentication for KNXnet/IP communication. This is important for deployments where KNX traffic traverses untrusted networks or where regulatory compliance requires encrypted building automation traffic.

### Can linknx replace a home automation platform like Home Assistant?

linknx provides basic automation rules but is not a full home automation platform. It excels at KNX-specific logic (temperature-based valve control, schedule-based lighting) but lacks the breadth of integrations, dashboards, and user management that platforms like Home Assistant offer. Many users run linknx alongside Home Assistant for KNX-specific automation.

### How do I monitor KNX bus traffic with these tools?

knxd provides a local socket interface that you can connect to with tools like groupsocketlisten for real-time bus monitoring. Calimero has event listeners in its Java API. linknx logs all bus activity to its log output. For comprehensive monitoring, consider combining a gateway with a logging platform like InfluxDB and Grafana.

### What is the difference between KNX IP tunneling and IP routing?

KNX IP tunneling establishes a point-to-point connection between a client and a KNXnet/IP server (like a dedicated tunnel). Only one client can use the tunnel at a time. IP routing broadcasts KNX telegrams over IP multicast, allowing multiple clients to receive all bus traffic simultaneously. knxd supports both modes.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Best Self-Hosted KNX/IP Gateways 2026: knxd vs Calimero vs linknx",
  "description": "Compare three open-source KNX/IP gateway servers for self-hosted building automation.",
  "datePublished": "2026-05-19",
  "dateModified": "2026-05-19",
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
