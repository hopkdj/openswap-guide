---
title: "Self-Hosted BLE Room Presence Tracking: ESPresense vs room-assistant vs Bermuda — Complete Guide 2026"
date: "2026-06-06"
tags: ["ble", "bluetooth", "presence-detection", "room-tracking", "esp32", "home-automation", "mqtt", "smart-home", "indoor-positioning", "self-hosted"]
draft: false
---

## Introduction

Knowing which room someone is in unlocks powerful home automation possibilities: lights that follow you through the house, heating that adjusts per-room occupancy, and security alerts when unexpected movement is detected. Bluetooth Low Energy (BLE) presence tracking uses the BLE advertisements emitted by phones, watches, and wearables to determine room-level location — no cameras, no wearable tags, just your existing devices.

Three open-source platforms have emerged as leaders in self-hosted BLE room presence: **ESPresense**, **room-assistant**, and **Bermuda** (the ESPresense Companion). Each uses ESP32 microcontrollers as BLE scanners distributed throughout your home, with MQTT as the data backbone. In this guide, we compare their architectures, setup processes, and integration capabilities to help you deploy reliable room-level presence tracking entirely on your own infrastructure.

## Comparison Table

| Feature | ESPresense | room-assistant | Bermuda (Companion) |
|---------|-----------|----------------|---------------------|
| **GitHub Stars** | 1,428+ | 1,344+ | 212+ |
| **Hardware** | ESP32 only | Raspberry Pi + BLE dongle or ESP32 | ESP32 + central server |
| **Installation** | Flash firmware to ESP32 | Docker on Raspberry Pi | Docker on server + flashed ESP32 nodes |
| **BLE Scanning** | Passive (advertisements) | Active + passive | Passive via ESPresense nodes |
| **Position Solving** | On-device (ESP32) | Server-side calculation | Server-side (Bayesian) |
| **MQTT Support** | Yes (native) | Yes (native) | Yes (consumes ESPresense MQTT) |
| **Home Assistant Integration** | MQTT Auto-Discovery | MQTT Auto-Discovery | Native HA Add-on |
| **Multi-Floor Support** | Yes (per-node floor config) | Yes (room-based) | Yes (3D positioning) |
| **Calibration** | Per-node distance tuning | Automatic + manual | Automatic Bayesian |
| **Max Tracked Devices** | Unlimited (ESP32 memory limited) | Unlimited | Unlimited |
| **Web Dashboard** | No (MQTT only) | Yes (Vue.js web UI) | Yes (HA Lovelace cards) |
| **License** | MIT | MIT | MIT |

## ESPresense: Lightweight ESP32 Nodes

ESPresense takes the minimalist approach — each ESP32 node is a dedicated BLE scanner that measures the signal strength (RSSI) of nearby BLE devices and publishes distance estimates to MQTT. The firmware is flashed directly onto ESP32 development boards (like the M5Stack Atom or generic ESP32-WROOM modules) and requires no server-side processing for basic room assignment.

ESPresense uses a fingerprinting approach: you define which BLE device addresses belong to which person, assign each ESP32 node to a room, and the node reports "closest room" based on signal strength comparison. This distributed architecture means no central server is required for basic functionality — though most users pair it with the Bermuda/ESPresense Companion for more sophisticated multi-node position solving.

```yaml
# ESPresense node configuration (flashed via web installer)
# Each ESP32 node broadcasts to MQTT topics like:
# espresense/rooms/living_room/device_tracker_abcd1234

# MQTT broker Docker Compose for ESPresense backend
version: '3.8'
services:
  mosquitto:
    image: eclipse-mosquitto:2
    ports:
      - "1883:1883"
    volumes:
      - ./mosquitto.conf:/mosquitto/config/mosquitto.conf
    restart: unless-stopped
```

Installation is remarkably simple: visit the ESPresense web flasher at `espresense.com`, connect your ESP32 via USB, select your Wi-Fi and MQTT credentials, and flash. Within 60 seconds, the node starts scanning for BLE devices and publishing to MQTT.

**Strengths**: Ultra-lightweight, no server required, web-based flashing, rock-solid reliability.

**Limitations**: Limited on-device position solving with single nodes, no web dashboard, calibration requires manual RSSI tuning.

## room-assistant: Full-Featured Server-Side Platform

room-assistant takes a fundamentally different approach — rather than offloading computation to ESP32 nodes, it runs as a Docker container on a Raspberry Pi or server, using either Bluetooth USB dongles or ESP32 nodes as BLE radios. All position computation, device tracking, and clustering happens server-side, giving you more sophisticated algorithms at the cost of requiring a central server.

room-assistant uses a Gaussian filtering approach for RSSI smoothing, which reduces the noisy spikes common in raw BLE signal measurements. It also supports Bluetooth Classic (not just BLE) for tracking older devices, and can integrate additional sensor data like motion detectors for hybrid presence detection. The Vue.js web dashboard provides a real-time map of detected devices and their assigned rooms.

```yaml
# room-assistant Docker Compose deployment
version: '3.8'
services:
  room-assistant:
    image: mkerix/room-assistant:latest
    network_mode: host
    privileged: true
    volumes:
      - /var/run/dbus:/var/run/dbus
      - ./room-assistant/config:/etc/room-assistant
    environment:
      - TZ=Asia/Shanghai
    restart: unless-stopped

  mosquitto:
    image: eclipse-mosquitto:2
    ports:
      - "1883:1883"
    volumes:
      - ./mosquitto.conf:/mosquitto/config/mosquitto.conf
```

**Strengths**: Sophisticated server-side clustering, Vue.js web dashboard, Bluetooth Classic support, Gaussian RSSI smoothing.

**Limitations**: Requires a Raspberry Pi or server per room, higher power consumption, more complex initial setup.

## Bermuda: Intelligent Multi-Node Position Solving

Bermuda (also known as ESPresense Companion) bridges the gap between ESPresense's lightweight nodes and room-assistant's server-side intelligence. It consumes MQTT data from multiple ESPresense nodes and applies Bayesian trilateration to determine precise room positions — even when a device is equidistant from multiple nodes.

Bermuda runs as a Docker container and integrates natively with Home Assistant, providing custom Lovelace cards that show real-time device positions on a 3D floor plan. The Bayesian solver accounts for floor level, wall attenuation, and node placement, delivering more accurate room assignments than simple "closest node" algorithms.

```yaml
# Bermuda / ESPresense Companion Docker Compose
version: '3.8'
services:
  espresense-companion:
    image: ghcr.io/espresense/espresense-companion:latest
    ports:
      - "8266:8266"
    environment:
      - MQTT_HOST=mosquitto
      - MQTT_PORT=1883
      - FLOOR_PLAN_ENABLED=true
    volumes:
      - companion-data:/data
    restart: unless-stopped

  mosquitto:
    image: eclipse-mosquitto:2
    ports:
      - "1883:1883"

volumes:
  companion-data:
```

**Strengths**: Bayesian trilateration for accurate multi-node positioning, native Home Assistant integration, 3D floor plan visualization.

**Limitations**: Requires both ESPresense nodes AND a server, smaller community, primarily Home Assistant-focused.

## Deployment Architecture

A production BLE presence tracking setup typically follows this pattern:

1. **Hardware Layer**: 3-6 ESP32 nodes (one per room or per zone), each running ESPresense firmware
2. **Data Layer**: MQTT broker (Mosquitto) collecting RSSI measurements from all nodes
3. **Solver Layer**: Bermuda/Companion processing MQTT data with Bayesian algorithms
4. **Integration Layer**: Home Assistant or Node-RED consuming room assignments for automations

For related smart home infrastructure, see our [self-hosted smart home hub comparison](../2026-04-28-home-assistant-vs-homebridge-vs-scrypted-self-hosted-smart-home-hub-guide-2026/) and our [IoT firmware platform guide](../2026-05-09-self-hosted-iot-firmware-platforms-esphome-vs-tasmota-vs-espurna/). If you need the MQTT backbone, our [MQTT broker comparison](../2026-06-02-vernemq-vs-nanomq-vs-flashmq-mqtt-brokers-guide/) covers Mosquitto alternatives.

## Privacy Considerations for BLE Presence Tracking

BLE presence tracking raises legitimate privacy questions. Unlike camera-based occupancy detection, BLE tracking only determines which room a known device is in — it captures no images, audio, or personal data beyond device proximity. The randomized MAC addresses used by modern phones rotate periodically, adding an additional privacy layer. For sensitive environments, you can configure per-device opt-out lists, schedule tracking to disable during certain hours, or restrict tracking to specific zones (e.g., public areas only, not bedrooms). All data stays on your MQTT broker and never leaves your local network.

## FAQ

### How accurate is BLE room presence tracking?

With proper node placement (one ESP32 per room), BLE room presence achieves roughly 90-95% room-level accuracy. The accuracy depends on wall materials (drywall is fine, concrete/metal causes signal loss), node density, and BLE transmission power from tracked devices. Bermuda's Bayesian solver significantly improves accuracy in open-plan spaces compared to simple "closest node" methods.

### Does BLE presence tracking drain my phone battery?

No — these systems passively listen for BLE advertisement packets that your phone already broadcasts. They do not pair with your device or request additional transmissions. The power impact is effectively zero. Most modern smartphones broadcast BLE advertisements for features like Find My Device, contact tracing, and smartwatch connectivity regardless.

### How many ESP32 nodes do I need?

A good rule of thumb is one ESP32 node per room you want to track, placed centrally at roughly chest height. For large open-plan areas, place nodes at the perimeter with overlapping coverage. A typical three-bedroom home needs 5-7 nodes (living room, kitchen, each bedroom, hallway). You can start with fewer and add nodes where accuracy is insufficient.

### Can I track devices that don't broadcast BLE?

room-assistant supports Bluetooth Classic scanning for older devices, but most modern phones, watches, and wearables broadcast BLE. For devices that don't emit BLE (like dumb key fobs), you can use BLE beacon tags (Tile, Chipolo, or generic iBeacon tags) that cost a few dollars each and broadcast continuously for 6-12 months on a coin cell battery.

### Does this work with iPhones?

Yes — iPhones broadcast BLE advertisements that include a randomized MAC address (for privacy). ESPresense and Bermuda handle randomized addresses through "IRK" (Identity Resolving Key) resolution, which pairs the randomized address with a known identity. The setup requires extracting your iPhone's IRK, which is more involved than Android but well-documented.

### Can presence data trigger automations beyond Home Assistant?

Absolutely. Since all platforms publish to MQTT, any system that can consume MQTT messages works: Node-RED for visual automation flows, openHAB, Domoticz, or custom Python scripts using the paho-mqtt library. The MQTT topics follow consistent schemas (`espresense/rooms/living_room/device_tracker/<name>/state`), making integration straightforward across platforms.



---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)


<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted BLE Room Presence Tracking: ESPresense vs room-assistant vs Bermuda — Complete Guide 2026",
  "description": "Complete comparison of open-source BLE room presence tracking platforms. Deploy ESPresense, room-assistant, or Bermuda on ESP32 nodes with MQTT for accurate room-level occupancy detection without cameras.",
  "datePublished": "2026-06-06",
  "dateModified": "2026-06-06",
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
