---
title: "Self-Hosted MQTT-SN for Sensor Networks: RSMB vs Paho MQTT-SN vs EMQX Gateway"
date: "2026-06-05"
tags: ["mqtt-sn", "mqtt", "iot", "sensor-networks", "embedded", "messaging", "low-power"]
draft: false
---

## Introduction

MQTT for Sensor Networks (MQTT-SN) is a lightweight adaptation of the MQTT protocol designed specifically for constrained devices and low-bandwidth networks. While standard MQTT requires a TCP/IP stack, MQTT-SN works over UDP, Zigbee, BLE, LoRaWAN, and other non-IP transports. This makes it ideal for battery-powered sensors, agricultural monitoring stations, and industrial telemetry where TCP overhead would be prohibitive.

In this guide, we compare three open-source MQTT-SN implementations: **Eclipse RSMB** (Really Small Message Broker), **Eclipse Paho MQTT-SN**, and the **EMQX MQTT-SN Gateway**. Each serves a different role in the MQTT-SN ecosystem — from embedded gateways to cloud-scale message brokers with transparent protocol bridging.

## Feature Comparison Table

| Feature | RSMB (Mosquitto RSMB) | Paho MQTT-SN | EMQX MQTT-SN Gateway |
|---------|----------------------|--------------|----------------------|
| **Stars** | 95 | 333 | 16,360 (EMQX) |
| **Language** | C | C++ | Erlang |
| **License** | EPL 1.0 | EPL 2.0 | Apache 2.0 |
| **Role** | Standalone MQTT-SN broker | Embedded C library + gateway | MQTT-SN → MQTT gateway |
| **Transport** | UDP, BLE, Zigbee | UDP (primary) | UDP |
| **QoS Support** | QoS 0, 1, 2 | QoS 0, 1, 2 | QoS 0, 1 |
| **Gateway Mode** | Built-in MQTT ↔ MQTT-SN | Yes (transparent gateway) | Yes (transparent gateway) |
| **Topic Registration** | Yes | Yes | Yes |
| **Sleeping Client** | Yes | Yes | Yes |
| **Will Messages** | Yes | Yes | Yes |
| **Predefined Topics** | Yes | Yes | Yes |
| **Docker Support** | Custom Dockerfile | Yes (embedded) | Official Docker image |
| **Horizontal Scaling** | No | No | Yes (EMQX cluster) |
| **Max Concurrent Clients** | ~1,000 | ~500 | 1,000,000+ |

## RSMB: The Reference Implementation for MQTT-SN

RSMB (Really Small Message Broker) was developed by IBM and is now maintained under the Eclipse Mosquitto project. It is the reference implementation of the MQTT-SN v1.2 specification and can operate as either a standalone MQTT-SN broker or a transparent gateway bridging MQTT-SN to standard MQTT.

### Docker Setup for RSMB

```yaml
version: "3.8"
services:
  rsmb:
    build:
      context: .
      dockerfile: |
        FROM ubuntu:22.04
        RUN apt-get update && apt-get install -y git build-essential
        RUN git clone https://github.com/eclipse/mosquitto.rsmb /opt/rsmb
        WORKDIR /opt/rsmb
        RUN make
        EXPOSE 1885/udp 1886/udp
        CMD ["./build/rsmb", "/config/broker.conf"]
    volumes:
      - ./config:/config
    ports:
      - "1885:1885/udp"
      - "1886:1886/udp"
    restart: unless-stopped
```

### RSMB Gateway Configuration

```ini
# broker.conf — RSMB as MQTT-SN gateway to standard MQTT broker
trace_output protocol

listener 1885 INADDR_ANY mqtts
  protocol mqtts

listener 1886 INADDR_ANY udp

connection standard_mqtt
  protocol mqtt
  address 127.0.0.1:1883
  topic # both

# Gateway-specific settings
options gateway_mode
  gateway_id 1
  keep_alive 900
```

RSMB's strength lies in its simplicity: the binary is under 200KB, making it suitable for embedding directly on gateway hardware like OpenWrt routers or Raspberry Pi Zero devices. It supports the complete MQTT-SN v1.2 specification including sleeping clients, which allows battery-powered sensors to disconnect between transmissions while the broker queues messages.

## Paho MQTT-SN: Embedded C Library with Gateway

The Eclipse Paho MQTT-SN project provides a portable C++ library for integrating MQTT-SN client functionality into embedded applications, along with a transparent gateway that bridges MQTT-SN UDP networks to standard MQTT brokers.

### Building Paho MQTT-SN Gateway

```bash
# Install dependencies
sudo apt-get install -y cmake g++ libssl-dev

# Build Paho C first (dependency)
git clone https://github.com/eclipse/paho.mqtt.c /opt/paho-c
cd /opt/paho-c && cmake -B build -DPAHO_WITH_SSL=ON && cmake --build build

# Build Paho MQTT-SN gateway
git clone https://github.com/eclipse/paho.mqtt-sn.embedded-c /opt/paho-mqttsn
cd /opt/paho-mqttsn
mkdir build && cd build
cmake .. -DPAHO_MQTTC_PATH=/opt/paho-c
make -j4
```

### Gateway Launch and Configuration

```bash
# Start the MQTT-SN gateway bridging UDP clients to local MQTT broker
./paho-mqtt-sn-gateway     --broker tcp://localhost:1883     --udp-port 10000     --gateway-id 1     --predefined-topic sensors/#     --keepalive 900
```

Paho MQTT-SN shines in custom embedded gateway development. Its C++ API allows you to build MQTT-SN gateways that bridge to non-standard transports (BLE, 6LoWPAN, Zigbee) while maintaining compatibility with any standard MQTT broker downstream.

### Integration with Custom Transports

```cpp
// Custom transport integration for BLE MQTT-SN
#include "MQTTSNGateway.h"
#include "BLETransport.h"

int main() {
    MQTTSNGateway gateway;
    BLETransport bleTransport("hci0");

    gateway.setTransport(&bleTransport);
    gateway.setBroker("tcp://localhost:1883");
    gateway.addPredefinedTopic("home/sensors/+/+");
    gateway.setGatewayId(1);

    gateway.start();
    return 0;
}
```

## EMQX MQTT-SN Gateway: Enterprise-Scale Bridging

EMQX, one of the most popular open-source MQTT brokers (16,000+ stars), includes a built-in MQTT-SN gateway that transparently bridges MQTT-SN UDP clients into the EMQX cluster. This provides a unique advantage: MQTT-SN sensors get full access to EMQX's rules engine, data integration pipelines, and horizontal scaling.

### Docker Compose for EMQX with MQTT-SN

```yaml
version: "3.8"
services:
  emqx:
    image: emqx/emqx:5.8.0
    container_name: emqx
    environment:
      - EMQX_DASHBOARD__DEFAULT_PASSWORD=admin123
    ports:
      - "1883:1883"    # MQTT
      - "1884:1884/udp" # MQTT-SN
      - "8083:8083"    # WebSocket
      - "18083:18083"  # Dashboard
    volumes:
      - ./emqx-data:/opt/emqx/data
      - ./emqx-log:/opt/emqx/log
    restart: unless-stopped
```

### Enabling MQTT-SN Gateway via API

```bash
# Enable MQTT-SN gateway on port 1884/udp
curl -X PUT "http://localhost:18083/api/v5/gateway/mqttsn"     -u admin:admin123     -H "Content-Type: application/json"     -d '{
        "enable": true,
        "gateway_id": 1,
        "broadcast": true,
        "enable_qos3": true,
        "predefined": [
            {"id": 0, "topic": "sensors/+/+"}
        ]
    }'
```

### MQTT-SN to InfluxDB Data Pipeline

EMQX's rules engine makes it trivial to forward MQTT-SN sensor data to databases and analytics platforms:

```sql
-- EMQX Rule: Forward MQTT-SN sensor data to InfluxDB
SELECT
  payload.temperature as temp,
  payload.humidity as humid,
  clientid,
  topic
FROM "sensors/#"
```

This rule automatically transforms MQTT-SN messages from UDP sensors into InfluxDB time-series records, with zero custom code. The same pattern works for PostgreSQL, TimescaleDB, Kafka, and AWS IoT Core.

## MQTT-SN Protocol Deep Dive

MQTT-SN introduces several protocol-level optimizations that make it fundamentally different from standard MQTT:

- **Topic Registration**: Clients register a topic string once and receive a 2-byte topic ID. All subsequent publications use the short topic ID instead of the full topic string, reducing per-message overhead from potentially hundreds of bytes to just 2 bytes.
- **Sleeping Client Support**: Battery-powered sensors can disconnect for hours while the broker queues incoming messages. When the sensor wakes up, it reconnects and receives all queued messages.
- **Predefined Topics**: Up to 65,535 topics can be predefined by topic ID on both the client and gateway, eliminating the registration handshake entirely.
- **Gateway Discovery**: MQTT-SN supports automatic gateway discovery on local networks via UDP broadcast, so sensors can find the nearest gateway without hardcoded addresses.

## Choosing the Right MQTT-SN Implementation

- **RSMB** is the reference implementation for compliance testing and lightweight deployments. Use it when you need a standalone MQTT-SN broker on resource-constrained gateway hardware (Raspberry Pi, OpenWrt) and don't need horizontal scaling.
- **Paho MQTT-SN** excels in custom embedded gateway development where you need to bridge MQTT-SN over non-standard transports. Its C++ library API makes it the most flexible option for custom IoT hardware.
- **EMQX Gateway** is the enterprise choice when you're already running EMQX or need to bridge hundreds of thousands of MQTT-SN sensors into a scalable MQTT cluster with built-in data integration, authentication, and rule processing.

For most self-hosted deployments, the combination of Paho MQTT-SN gateway with Mosquitto as the standard MQTT broker strikes the best balance of simplicity and flexibility.

For related reading, see our [self-hosted MQTT platforms comparison](../self-hosted-mqtt-platforms-mosquitto-emqx-hivemq-iot-guide-2026/) for Mosquitto and EMQX broker guides, our [LoRaWAN network server guide](../2026-05-04-self-hosted-lorawan-network-server-chirpstack-things-stack-guide/) for ChirpStack deployment, and our [IoT firmware platforms guide](../2026-05-09-self-hosted-iot-firmware-platforms-esphome-vs-tasmota-vs-espurna/) for ESPHome and Tasmota sensor integration.
## FAQ

### What is the difference between MQTT and MQTT-SN?

MQTT requires a TCP/IP stack and persistent connections, making it suitable for devices with full networking capabilities. MQTT-SN removes the TCP dependency, working over UDP and supporting non-IP transports like BLE, Zigbee, and LoRaWAN. MQTT-SN also adds topic registration, sleeping client support, and gateway discovery — features critical for battery-powered sensors that standard MQTT lacks.

### Do I need separate MQTT and MQTT-SN brokers?

Not necessarily. All three implementations (RSMB, Paho MQTT-SN, EMQX Gateway) operate as transparent gateways that bridge MQTT-SN UDP clients to a standard MQTT broker. Sensors communicate via MQTT-SN/UDP with the gateway, which translates messages to standard MQTT/TCP for the broker. Your existing Mosquitto or EMQX broker handles the MQTT side.

### What are the bandwidth savings of MQTT-SN over MQTT?

MQTT-SN reduces per-message overhead by 60-90% compared to MQTT in typical sensor deployments. A standard MQTT CONNECT packet is 50-200 bytes, while MQTT-SN uses just 5-10 bytes for the same function after topic registration. For a sensor publishing 1 message per minute, MQTT-SN saves approximately 10-30KB of data transfer per day — significant on LPWAN networks where data costs are per-byte.

### Can MQTT-SN work over LoRaWAN?

Yes, but with caveats. LoRaWAN has strict payload size limits (51-242 bytes depending on spreading factor) and duty cycle restrictions. MQTT-SN's topic registration and short topic IDs make it practical over LoRaWAN, where standard MQTT's TCP overhead would be impossible. The ChirpStack LoRaWAN Network Server includes built-in MQTT integration that can be combined with an MQTT-SN gateway for a complete LoRaWAN-to-MQTT-SN pipeline.

### How secure is MQTT-SN?

MQTT-SN itself does not define encryption; security is handled at the transport layer. For UDP-based deployments, DTLS (Datagram TLS) provides the same security guarantees as TLS for TCP-based MQTT. EMQX's MQTT-SN gateway supports DTLS natively, while RSMB and Paho MQTT-SN can be fronted by a DTLS proxy like stunnel or a WireGuard tunnel between sensors and the gateway.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted MQTT-SN for Sensor Networks: RSMB vs Paho MQTT-SN vs EMQX Gateway",
  "description": "Compare open-source MQTT-SN implementations: RSMB, Paho MQTT-SN embedded-C, and EMQX Gateway. Docker setups, gateway configurations, and protocol deep dive for self-hosted IoT sensor networks.",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
