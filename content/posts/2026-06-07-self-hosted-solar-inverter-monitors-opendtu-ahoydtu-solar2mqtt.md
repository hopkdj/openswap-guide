---
title: "Self-Hosted Solar Inverter Monitoring: OpenDTU vs AhoyDTU vs Solar2MQTT"
date: "2026-06-07"
tags: ["solar", "inverter-monitoring", "opendtu", "hoymiles", "self-hosted", "esp32", "energy-monitoring", "iot", "renewable-energy"]
draft: false
---

## Introduction

Modern solar microinverters generate significant amounts of performance data — per-panel voltage, current, power output, temperature, and cumulative energy production. Yet most manufacturers require you to use their proprietary cloud platforms or expensive data loggers to access this information. When those cloud services go offline, change pricing, or discontinue support for older hardware, you lose visibility into your solar investment.

Open-source solar inverter monitors solve this problem by communicating directly with microinverters over their native radio protocols. This article compares three leading self-hosted solutions: OpenDTU (for Hoymiles inverters), AhoyDTU (also for Hoymiles), and Solar2MQTT (multi-vendor support). Each reads inverter telemetry without cloud dependency and feeds data into your local monitoring infrastructure.

| Feature | OpenDTU | AhoyDTU | Solar2MQTT |
|---------|---------|---------|------------|
| Primary target | Hoymiles HM/ HMS series | Hoymiles HM series | Multi-vendor (SolaX, Growatt, Deye, etc.) |
| Hardware platform | ESP32 + NRF24L01+ | ESP32/ESP8266 + NRF24L01+ | Raspberry Pi / Linux server |
| Communication | 2.4 GHz Nordic nRF protocol | 2.4 GHz Nordic nRF protocol | Modbus TCP/RTU, RS485, HTTP polling |
| Web interface | Built-in (live data, charts, settings) | Built-in (live data, settings) | None (MQTT bridge only) |
| Inverter limit | Up to 4 inverters per DTU | Up to 4 inverters per DTU | Unlimited (depends on polling interval) |
| Home Assistant | Native MQTT auto-discovery | Native MQTT auto-discovery | MQTT auto-discovery |
| GitHub stars | 2,138+ | 1,598+ | Community maintained |
| Docker support | No (ESP32 firmware) | No (ESP32 firmware) | Docker image available |
| Data export | MQTT + REST API | MQTT | MQTT only |
| Yield calculation | Per-panel, daily/monthly | Per-inverter, daily | Per-inverter |

## OpenDTU: The Community Standard

OpenDTU (2,138+ GitHub stars) is the most mature open-source solution for Hoymiles microinverters. It runs on an ESP32 microcontroller paired with an NRF24L01+ 2.4 GHz radio module, communicating directly with Hoymiles HM and HMS series inverters.

```yaml
# ESPHome-style pinout for OpenDTU hardware
# NRF24L01+ connections to ESP32:
# CSN  → GPIO5
# CE   → GPIO4
# MOSI → GPIO23
# MISO → GPIO19
# SCK  → GPIO18
# IRQ  → GPIO16

# LED indicator (optional):
# LED  → GPIO2 (with 220Ω resistor)

# The NRF24L01+ module requires a stable 3.3V supply
# with adequate decoupling (10μF + 100nF capacitors)
# Some modules have onboard regulators; others need external regulation
```

OpenDTU provides a built-in web interface showing real-time AC/DC power, per-panel voltage and current, inverter temperature, and daily/total yield statistics. The web dashboard includes configurable charts, event logging, and a setup wizard that simplifies initial configuration.

```cpp
// Key OpenDTU configuration in web interface:
// 1. Set your inverter serial numbers (found on inverter label)
// 2. Configure MQTT broker address for Home Assistant integration
// 3. Set geographic coordinates for sun position / yield estimation
// 4. Configure NTP server for accurate timestamps

// MQTT topics published (example for inverter with serial 1142123456):
// solar/hoymiles/1142123456/ac/power       → 300.5
// solar/hoymiles/1142123456/dc/0/voltage   → 33.2
// solar/hoymiles/1142123456/dc/0/current   → 9.05
// solar/hoymiles/1142123456/temperature    → 42.3
// solar/hoymiles/1142123456/yieldtotal     → 1250.8
```

Home Assistant's MQTT auto-discovery automatically creates entities for each inverter and panel, enabling the Energy dashboard to track solar production alongside grid consumption.

## AhoyDTU: The Alternative Firmware

AhoyDTU (1,598+ GitHub stars) is a newer alternative to OpenDTU that also targets Hoymiles inverters. It supports both ESP32 and ESP8266 platforms and offers some differentiating features:

```yaml
# docker-compose.yml for AhoyDTU add-on (optional web proxy)
version: '3.8'
services:
  ahoy-mqtt-bridge:
    image: ghcr.io/ahoydtu/ahoy-mqtt-bridge:latest
    restart: unless-stopped
    environment:
      - AHOY_HOST=192.168.1.100
      - MQTT_HOST=192.168.1.50
      - MQTT_PORT=1883
      - MQTT_TOPIC=solar/ahoy
    depends_on:
      - mosquitto
```

AhoyDTU's key differentiators include support for ESP8266 (lower cost than ESP32), built-in MQTT TLS for encrypted data transport, and a REST API that returns JSON-formatted inverter data. The web interface is simpler than OpenDTU's but is well-suited for headless deployments where Home Assistant handles all visualization.

## Solar2MQTT: Multi-Vendor Bridge

Solar2MQTT takes a different architectural approach. Instead of communicating directly over 2.4 GHz radio, it connects to inverters over Modbus TCP/RTU or polls the manufacturer's local HTTP API. This makes it compatible with a much broader range of inverter brands including SolaX, Growatt, Deye, Solis, and Sofar.

```yaml
# docker-compose.yml for Solar2MQTT (SolaX inverter example)
version: '3.8'
services:
  solar2mqtt:
    image: ghcr.io/domoticx/solar2mqtt:latest
    restart: unless-stopped
    environment:
      - INVERTER_TYPE=solax
      - INVERTER_HOST=192.168.1.80
      - INVERTER_PORT=502
      - INVERTER_MODEL=X1-Hybrid-G4
      - MQTT_HOST=192.168.1.50
      - MQTT_PORT=1883
      - MQTT_TOPIC_PREFIX=solar/inverter
      - POLL_INTERVAL=10
      - DEBUG=false
```

Solar2MQTT is ideal if you have a heterogenous solar installation with inverters from different manufacturers, or if you have a hybrid inverter that also manages battery storage — it can read battery state-of-charge, charge/discharge power, and grid export metrics alongside solar production data.

## Hardware Build: Building Your Monitor

For OpenDTU or AhoyDTU on ESP32:

```bash
# Bill of materials (≈€12-18 total):
# - ESP32 DevKit board (€4-8)
# - NRF24L01+ PA/LNA module (€3-5) — PA/LNA version for better range
# - AMS1117-3.3V voltage regulator module (€1-2) — stable 3.3V for NRF24
# - 10μF + 100nF capacitors (decoupling)
# - Jumper wires (Dupont) + micro-USB cable + enclosure

# Flashing OpenDTU using web flasher:
# 1. Visit the OpenDTU web flasher at https://www.opendtu.solar/
# 2. Connect ESP32 via USB, select the correct serial port
# 3. Choose the latest stable firmware release
# 4. Click "Flash" — the web tool handles everything
# 5. After flashing, connect to OpenDTU WiFi AP to configure

# For AhoyDTU, download firmware from:
# https://github.com/ahoydtu/ahoy/releases
# Flash using esptool.py:
esptool.py --port /dev/ttyUSB0 write_flash 0x0 ahoy-firmware.bin
```

## Integration with Home Assistant Energy Dashboard

All three solutions publish data to MQTT, which Home Assistant consumes via its MQTT integration. Once your inverter data appears in Home Assistant:

1. Navigate to Settings → Dashboards → Energy
2. Under "Electricity Grid," add your grid consumption sensor
3. Under "Solar Production," add the total yield sensor from your inverter
4. Home Assistant automatically computes self-consumption, grid import/export, and solar fraction

For a complete energy monitoring stack, combine your inverter monitor with a smart meter reader (see our [smart meter guide](../2026-06-07-self-hosted-smart-meter-readers-volkszaehler-vzlogger-esphome/)) to track both production and consumption simultaneously.

## Why Self-Host Your Solar Inverter Monitoring

Solar is a 20+ year investment, but manufacturer cloud platforms typically have a 5-10 year support lifecycle. When Hoymiles or SolaX decide to sunset their cloud services or start charging subscription fees, a self-hosted monitor keeps your data flowing — and gives you sub-second resolution that cloud platforms often don't provide. More importantly, local monitoring enables automations like diverting excess solar to a heat pump or EV charger, which requires real-time production data that no cloud API can deliver with sufficiently low latency.

For broader solar energy management, see our [solar energy monitoring platforms guide](../2026-06-05-self-hosted-solar-energy-monitoring-openems-emoncms-guide/). To integrate with home automation, our [smart home bridges comparison](../zigbee2mqtt-vs-zwave-js-ui-vs-esphome-self-hosted-smart-home-bridges-guide-2026/) covers the messaging infrastructure. For IoT device management at scale, our [IoT platform guide](../thingsboard-vs-iotsharp-vs-iot-dc3-self-hosted-iot-platform-guide-2026/) is a valuable reference.

## FAQ

### Do these tools work with any microinverter brand?

OpenDTU and AhoyDTU are specific to Hoymiles inverters (HM-300, HM-350, HM-400, HM-600, HM-700, HM-800, HM-1000, HM-1200, HM-1500, and HMS series). Solar2MQTT supports a wider range including SolaX, Growatt, Deye, Solis, Sofar, and GoodWe via Modbus. For Enphase inverters, check out the Enphase Envoy local API. For SolarEdge, the built-in Modbus TCP interface works with Solar2MQTT.

### How many inverters can one monitor handle?

OpenDTU and AhoyDTU support up to 4 Hoymiles inverters per ESP32, limited by the NRF24L01+ radio's polling cycle. For larger installations, deploy multiple ESP32-based DTUs — each covers up to 4 inverters within radio range. Solar2MQTT has no hard limit since it communicates over Modbus TCP, which supports multiple inverters on the same RS485 bus or network.

### Does the DTU need line-of-sight to the inverters?

The NRF24L01+ with PA/LNA amplifier and proper antenna placement achieves 100-300 meters range indoors through walls, and up to 1 kilometer with clear line of sight. Inverters mounted under solar panels on a roof are typically within range of an ESP32 placed in the attic or top floor. If range is insufficient, place the DTU in a weatherproof enclosure closer to the array and use WiFi to relay data back.

### Can I still use the manufacturer's app alongside these tools?

OpenDTU and AhoyDTU impersonate the manufacturer's DTU, which means the manufacturer's cloud platform (Hoymiles S-Miles Cloud) will lose connection because inverters can only communicate with one DTU at a time. Solar2MQTT reads data via Modbus, which may coexist with the manufacturer's monitoring — check your specific inverter model's documentation for concurrent connection support.

### What happens to my historical data when switching from cloud to self-hosted?

Most manufacturer cloud platforms do not provide data export APIs, so historical data is typically lost when you disconnect. Start your self-hosted monitoring while the cloud platform is still running, run both in parallel for a transition period, then cut over. Tools like InfluxDB with continuous queries can compute monthly and yearly aggregates from the moment you start self-hosting.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Solar Inverter Monitoring: OpenDTU vs AhoyDTU vs Solar2MQTT",
  "description": "Compare OpenDTU, AhoyDTU, and Solar2MQTT for local solar inverter monitoring. Covers Hoymiles microinverters, NRF24L01+ radio modules, ESP32 firmware, Modbus TCP, and Home Assistant Energy dashboard.",
  "datePublished": "2026-06-07",
  "dateModified": "2026-06-07",
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

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)**

