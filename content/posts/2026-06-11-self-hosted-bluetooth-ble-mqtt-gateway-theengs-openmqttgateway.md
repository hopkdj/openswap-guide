---
title: "Self-Hosted Bluetooth BLE to MQTT Gateways: Theengs vs OpenMQTTGateway vs bt-mqtt-gateway"
date: "2026-06-11"
tags: ["bluetooth", "ble", "mqtt", "iot", "smart-home", "home-automation", "self-hosted"]
draft: false
---

## Introduction

Bluetooth Low Energy (BLE) sensors are everywhere — temperature and humidity monitors, plant soil sensors, presence beacons, weight scales, and fitness trackers all broadcast BLE advertisements. The challenge is getting that data into your smart home automation system. A BLE-to-MQTT gateway bridges this gap: it listens for BLE advertisements, decodes the sensor data, and publishes it as structured MQTT messages that Home Assistant, Node-RED, or any MQTT-compatible platform can consume.

This guide compares three self-hosted BLE-to-MQTT gateway solutions: **Theengs Gateway**, **OpenMQTTGateway**, and **bt-mqtt-gateway**. All three run on low-power hardware (Raspberry Pi, ESP32) and can serve as the bridge between your Bluetooth sensors and your MQTT infrastructure.

## Platform Comparison

| Feature | Theengs Gateway | OpenMQTTGateway | bt-mqtt-gateway |
|---------|----------------|-----------------|-----------------|
| Primary Developer | Theengs Team (1technophile) | 1technophile / Community | Zewelor / Community |
| GitHub Stars | 164+ | 4,023+ | 556+ |
| Hardware Support | Raspberry Pi, Linux, Windows, macOS | ESP32, ESP8266, Raspberry Pi, Linux | Raspberry Pi, Linux |
| Protocol Support | BLE only | BLE, 433MHz RF, Infrared, LoRa, GSM | BLE only |
| Decoder Library | Theengs Decoder (80+ devices) | Decoder library (50+ devices) | Custom plugin system |
| MQTT Auto-Discovery | Home Assistant auto-discovery | Home Assistant auto-discovery | Manual topic configuration |
| Web Interface | Built-in web UI | Web config portal (OTA) | None (config file) |
| Docker Deployment | Yes (multi-arch) | Partial (ESP32 native) | Yes |
| Architecture | Python (multi-platform) | C++ (ESP32 native / Python) | Python |
| Latest Release | June 2026 | June 2026 | October 2023 |

## Deploying Theengs Gateway with Docker

Theengs Gateway is the most user-friendly option, with broad hardware support and an extensive decoder library covering 80+ BLE sensor models:

```yaml
version: "3.8"
services:
  theengs-gateway:
    image: theengs/gateway:latest
    network_mode: host
    environment:
      MQTT_HOST: 192.168.1.100
      MQTT_PORT: 1883
      MQTT_USER: mqtt_user
      MQTT_PASSWORD: mqtt_pass
      MQTT_PUB_TOPIC: home/TheengsGateway/BTtoMQTT
      MQTT_SUB_TOPIC: home/TheengsGateway/command
      IDENTITIES: "{}"
      DISCOVERY: "true"
      DISCOVERY_TOPIC: homeassistant
      DISCOVERY_DEVICE_NAME: TheengsGateway
      DISCOVERY_FILTER: " "
      TIME_BETWEEN: 60
      SCAN_DURATION: 60
      LOG_LEVEL: INFO
      ADAPTER: hci0
    volumes:
      - /var/run/dbus:/var/run/dbus
    privileged: true
```

Theengs Gateway publishes decoded sensor data to MQTT with Home Assistant auto-discovery enabled by default. When a new BLE sensor is detected — say a Xiaomi MiFlora plant sensor — it automatically creates corresponding entities in Home Assistant. The built-in web UI at port 8080 shows real-time device discovery and signal strength.

## Deploying OpenMQTTGateway on ESP32

OpenMQTTGateway uses the ESP32's built-in Bluetooth radio, making it a purpose-built, low-power hardware gateway:

```yaml
# PlatformIO configuration for ESP32 BLE gateway
[env:esp32dev-ble]
platform = espressif32
board = esp32dev
framework = arduino
lib_deps =
    h2zero/NimBLE-Arduino@^2.2.1
    256dpi/ArduinoJson@^7.0
    knolleary/PubSubClient@^2.8
build_flags =
    -DZgatewayBT="1"
    -DZgatewayPilight="0"
    -DZgatewayRF="0"
    -DZgatewayRF2="0"
    -DZgatewayIR="0"
    -DZmqttDiscovery="1"
    -DDEFAULT_MQTT_HOST=""192.168.1.100""
    -DDEFAULT_MQTT_PORT=1883
    -DDEFAULT_MQTT_USER=""mqtt_user""
    -DDEFAULT_MQTT_PASSWORD=""mqtt_pass""
    -DGateway_Name=""OpenMQTTGateway_ESP32_BLE""
```

Flash to ESP32:

```bash
pio run -e esp32dev-ble -t upload
```

OpenMQTTGateway's advantage is its multi-protocol support — a single ESP32 can simultaneously handle BLE, 433MHz RF sensors, and infrared remote signals. The web configuration portal at `http://<esp32-ip>` allows over-the-air updates and protocol enable/disable toggling.

## Deploying bt-mqtt-gateway

bt-mqtt-gateway takes a plugin-based approach, where each BLE sensor type gets its own Python worker:

```bash
git clone https://github.com/zewelor/bt-mqtt-gateway.git
cd bt-mqtt-gateway

# Install with sensor-specific plugins
pip install -r requirements.txt

# Configure MQTT and sensor plugins
cp config.yaml.example config.yaml
```

Example configuration:

```yaml
mqtt:
  host: 192.168.1.100
  port: 1883
  user: mqtt_user
  password: mqtt_pass

manager:
  sensor_config_read_interval: 300
  topic_subscription: home/bt-mqtt-gateway/+

workers:
  mi_flora:
    enabled: true
    topic_prefix: home/bt-mqtt-gateway
    scan_interval: 300
  mi_scale:
    enabled: true
    topic_prefix: home/bt-mqtt-gateway
  ruuvitag:
    enabled: true
    topic_prefix: home/bt-mqtt-gateway
```

Start the gateway:

```bash
python3 gateway.py -c config.yaml
```

While bt-mqtt-gateway lacks a web UI, its plugin architecture makes it highly extensible — developers can add support for new BLE sensor models by writing a small Python worker class.

## Choosing the Right BLE Gateway

**Theengs Gateway** is the best choice for most home users. Its Docker deployment, extensive pre-built decoder library (80+ devices), and Home Assistant auto-discovery mean you can be collecting BLE sensor data within minutes of starting the container. The built-in web UI makes troubleshooting easy.

**OpenMQTTGateway** is the ideal choice when you want a dedicated hardware gateway on an ESP32. Its multi-protocol capability — handling BLE, 433MHz, and infrared all from one $5 microcontroller — provides exceptional value. The mature codebase with 4,000+ GitHub stars reflects its reliability in production home automation setups.

**bt-mqtt-gateway** suits users who want fine-grained control over how each sensor type is handled. Its plugin-per-device architecture means you only run code for the sensors you actually own. However, the lack of active maintenance (last release October 2023) and absence of a web UI make it less suitable for newcomers.

For most setups, running Theengs Gateway on a Raspberry Pi alongside your existing MQTT broker is the path of least resistance. If you need RF (433MHz) or infrared alongside BLE, OpenMQTTGateway on an ESP32 is the most cost-effective solution.

## Why Self-Host Your BLE-to-MQTT Bridge?

Cloud-based Bluetooth gateways require your sensor data to leave your network. Temperature readings, presence data, and scale measurements are intimate details about your home and habits. A self-hosted gateway keeps all sensor data local, publishing only to your private MQTT broker.

Latency matters for home automation — a local BLE gateway publishes temperature changes within 1-2 seconds, while cloud-reliant alternatives introduce multi-second delays that break automation responsiveness (e.g., turning on a fan when the room reaches 25°C).

For homes already running self-hosted smart home infrastructure, our [Zigbee2MQTT and Z-Wave smart home bridges guide](../zigbee2mqtt-vs-zwave-js-ui-vs-esphome-self-hosted-smart-home-bridges-guide-2026/) covers the other major wireless protocols. BLE complements Zigbee and Z-Wave by handling the low-power sensor ecosystem that neither protocol serves well. If you need the firmware to run on your BLE gateway hardware, see our [ESPHome vs Tasmota firmware comparison](../2026-05-09-self-hosted-iot-firmware-platforms-esphome-vs-tasmota-vs-espurna/).


## Hardware Setup and Antenna Optimization

The physical placement and antenna configuration of your BLE gateway dramatically affects sensor coverage. Here are practical deployment considerations for maximizing range and reliability.

**Placement strategy**: Mount the gateway centrally in your home, elevated (at least 1.5m off the floor), and away from large metal objects (refrigerators, HVAC ducts, metal stud walls). BLE uses the 2.4 GHz band, which is easily absorbed by water — do not place gateways behind aquariums, water pipes, or dense vegetation. For multi-story homes, one gateway per floor is recommended, with gateways on adjacent floors positioned at opposite ends of the house to minimize interference.

**Antenna considerations**: The Raspberry Pi's built-in PCB antenna is omnidirectional but relatively weak. An external USB Bluetooth adapter with a 3-5 dBi antenna can double effective range. For ESP32-based gateways like OpenMQTTGateway, the ESP32-WROOM module includes a PCB antenna, and the ESP32-WROVER model adds an IPEX connector for an external antenna. In a typical wood-frame house, a well-placed Raspberry Pi 4 with an external antenna reliably covers 100-150 square meters.

**Interference management**: BLE shares the 2.4 GHz spectrum with WiFi, Zigbee, microwave ovens, and wireless video transmitters. Configure your WiFi access point to use 5 GHz for high-bandwidth devices and reserve 2.4 GHz for IoT. If possible, place the BLE gateway at least 2 meters from WiFi access points. Theengs Gateway's web UI shows RSSI (signal strength) per detected device — use this to identify sensors with marginal signal that may need a second gateway.

**Power considerations for ESP32 gateways**: An ESP32 running OpenMQTTGateway with continuous BLE scanning draws approximately 80-120 mA at 5V (0.4-0.6 watts). This is low enough to run indefinitely from a USB port. For battery-powered sensor deployments, ESP32 deep sleep modes can reduce consumption to under 1 mA, waking periodically to scan and publish — but this introduces latency that makes presence detection impractical.

**Multi-gateway deployment**: For homes larger than 200 square meters or with challenging construction (brick, concrete, metal-framed), deploy multiple gateways. Configure each with a unique MQTT client ID and a location-specific topic prefix (e.g., `home/ble-gateway/living-room/` vs `home/ble-gateway/bedroom/`). Home Assistant can then use the gateway with the strongest RSSI for a given sensor, providing room-level localization.


## FAQ

**Do I need a separate Bluetooth adapter for the gateway?**

Raspberry Pi 3, 4, and 5 have built-in Bluetooth. For ESP32-based gateways like OpenMQTTGateway, the ESP32's integrated Bluetooth radio is used. If running in Docker, you may need to pass through the host Bluetooth adapter with `network_mode: host` and `privileged: true`.

**How many BLE sensors can one gateway handle?**

A single Raspberry Pi 4 running Theengs Gateway can comfortably handle 30-50 BLE sensors within range. ESP32-based gateways are more constrained due to memory — expect 15-25 sensors before performance degrades. For very large deployments, deploy multiple gateways in different physical zones.

**Can I use these gateways to track BLE presence (room-level tracking)?**

Yes. All three gateways can forward BLE advertisement data including MAC addresses and RSSI signal strength. Combined with Home Assistant's Bayesian or room-assistant integration, this enables room-level presence detection based on which gateway hears a device strongest.

**What range can I expect from a BLE gateway?**

Typical indoor range is 10-30 meters through walls, depending on construction materials. Using an external USB Bluetooth adapter with a high-gain antenna can extend range to 50+ meters. ESP32-based gateways can use external antennas for improved reception.

**Do BLE gateways affect Bluetooth audio or other Bluetooth peripherals?**

On Raspberry Pi, the built-in Bluetooth adapter handles both BLE scanning and classic Bluetooth connections simultaneously. On ESP32, the radio is dedicated to the gateway firmware. In either case, BLE scanning is a receive-only operation that does not interfere with other Bluetooth devices.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Bluetooth BLE to MQTT Gateways: Theengs vs OpenMQTTGateway vs bt-mqtt-gateway",
  "description": "Compare three self-hosted BLE-to-MQTT gateway solutions for smart home automation. Covers Theengs Gateway, OpenMQTTGateway, and bt-mqtt-gateway with Docker and ESP32 deployment guides.",
  "datePublished": "2026-06-11",
  "dateModified": "2026-06-11",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://pistack.xyz/logo.png"
    }
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
