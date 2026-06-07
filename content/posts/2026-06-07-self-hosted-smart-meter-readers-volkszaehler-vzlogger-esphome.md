---
title: "Self-Hosted Smart Meter Readers: Volkszähler vs vzlogger vs ESPHome SML Parser"
date: "2026-06-07"
tags: ["smart-meter", "energy-monitoring", "volkszaehler", "esphome", "raspberry-pi", "self-hosted", "iot", "home-automation", "power-monitoring"]
draft: false
---

## Introduction

Modern utility meters communicate consumption data through standardized optical interfaces, but accessing that data typically requires either logging into the utility's web portal (which may not offer real-time readings) or buying expensive commercial gateway hardware. Self-hosted smart meter readers bridge this gap by reading data directly from the meter's optical port or wireless interface and feeding it into your home automation or energy monitoring system. This article compares three leading open-source solutions: the Volkszähler ecosystem, vzlogger, and ESPHome's SML parser.

These tools all support the SML (Smart Message Language) protocol used by IEC 62056-21 compliant meters, which covers most modern electricity, gas, water, and heat meters installed across Europe. By reading OBIS (Object Identification System) codes, you can extract voltage, current, power, energy totals, and tariff information directly from the meter — no cloud dependency required.

| Feature | Volkszähler | vzlogger | ESPHome SML |
|---------|------------|----------|-------------|
| Primary function | Full web dashboard + data collection | Lightweight data collection daemon | Firmware-level meter reading |
| Architecture | PHP web application + middleware | C/C++ daemon with plugin system | ESP32/ESP8266 microcontroller firmware |
| Hardware platform | Raspberry Pi / Linux server | Raspberry Pi / Linux server | ESP32, ESP8266, ESP32-C3 |
| Web dashboard | Built-in (charts, statistics, widgets) | None (feeds to external systems) | Home Assistant integration |
| Data storage | MySQL with middleware pipeline | Direct to InfluxDB, MQTT, or Volkszähler | Direct to Home Assistant |
| Meter protocols | SML, D0, IEC 62056-21 | SML, D0, IEC 62056-21, OMS, wMBus | SML via UART |
| Docker support | Docker Compose available | Docker image available | N/A (firmware) |
| GitHub stars | 230+ (volkszaehler.org) | 162+ (vzlogger) | 87,500+ (ESPHome core) |
| Resource usage | Moderate (web stack + DB) | Lightweight (headless daemon) | Minimal (runs on microcontroller) |
| Alerting | Via frontend widgets | External (MQTT → Home Assistant) | Home Assistant automations |

## Volkszähler: The Full Dashboard Platform

Volkszähler (German for "people's meter") is a complete web application that reads, stores, and visualizes utility meter data. It consists of the vzlogger middleware daemon for data collection and the Volkszähler.org PHP frontend for visualization.

```yaml
# docker-compose.yml for Volkszähler stack
version: '3.8'
services:
  mariadb:
    image: mariadb:10.11
    restart: unless-stopped
    environment:
      - MYSQL_ROOT_PASSWORD=volkszaehler
      - MYSQL_DATABASE=volkszaehler
    volumes:
      - /opt/volkszaehler/db:/var/lib/mysql

  volkszaehler:
    image: volkszaehler/volkszaehler:latest
    restart: unless-stopped
    ports:
      - "8080:80"
    environment:
      - VZ_DB_HOST=mariadb
      - VZ_DB_NAME=volkszaehler
      - VZ_DB_USER=root
      - VZ_DB_PASSWORD=volkszaehler
    volumes:
      - /opt/volkszaehler/config:/etc/volkszaehler
    depends_on:
      - mariadb

  vzlogger:
    image: volkszaehler/vzlogger:latest
    restart: unless-stopped
    devices:
      - /dev/ttyUSB0:/dev/ttyUSB0
    volumes:
      - /opt/volkszaehler/vzlogger:/etc/vzlogger
    depends_on:
      - volkszaehler
```

The frontend provides interactive charts with zoom, multi-channel overlays, cost calculations based on tariff configurations, and export capabilities. Widgets can be embedded in external dashboards.

## vzlogger: The Lightweight Data Collector

vzlogger (162+ GitHub stars) is the C/C++ daemon that handles the actual meter communication. While it's often used as part of the Volkszähler stack, it can operate standalone, pushing data to InfluxDB, MQTT brokers, or any HTTP endpoint.

```bash
# Standalone vzlogger with MQTT output
# Install on Raspberry Pi
apt-get update && apt-get install -y git cmake build-essential libcurl4-openssl-dev \
    libgnutls28-dev libsml-dev libjson-c-dev libmicrohttpd-dev libmosquitto-dev

git clone https://github.com/volkszaehler/vzlogger.git
cd vzlogger
cmake -B build && cmake --build build && cmake --install build

# Sample vzlogger.conf for SML meter via IR head
# /etc/vzlogger.conf:
{
  "retry": 30,
  "daemon": true,
  "verbosity": 5,
  "local": {
    "enabled": false
  },
  "meters": [
    {
      "enabled": true,
      "protocol": "sml",
      "device": "/dev/ttyUSB0",
      "baudrate": 9600,
      "aggmode": "none",
      "channels": [
        {
          "uuid": "d0-0-1-8-0-ff",
          "identifier": "1-0:1.8.0",
          "api": "volkszaehler",
          "middleware": "http://volkszaehler:8080/middleware.php",
          "aggmode": "avg",
          "duplicates": 30
        }
      ]
    }
  ]
}
```

vzlogger supports a wide range of meter protocols beyond SML: D0 (IEC 62056-21 Mode C), OMS (Open Metering System), wireless M-Bus (wMBus), and various proprietary formats. This makes it the most flexible option for multi-meter households with different meter types.

## ESPHome SML Parser: Microcontroller-Level Reading

ESPHome (87,500+ stars) brings meter reading to low-cost ESP32 microcontrollers. The SML component reads SML telegrams directly via UART from an IR optical reader head or TTL interface.

```yaml
# ESPHome YAML configuration for SML smart meter
esphome:
  name: smart-meter-reader
  platform: ESP32
  board: esp32dev

logger:
  level: DEBUG

uart:
  - id: uart_sml
    rx_pin: GPIO16
    tx_pin: GPIO17
    baud_rate: 9600
    data_bits: 8
    parity: NONE
    stop_bits: 1

sml:
  - id: sml_meter
    uart_id: uart_sml

sensor:
  - platform: sml
    sml_id: sml_meter
    name: "Total Energy Import"
    obis_code: "1-0:1.8.0"
    unit_of_measurement: "kWh"
    device_class: energy
    state_class: total_increasing
    accuracy_decimals: 2

  - platform: sml
    sml_id: sml_meter
    name: "Current Power"
    obis_code: "1-0:16.7.0"
    unit_of_measurement: "W"
    device_class: power
    state_class: measurement
    accuracy_decimals: 1

  - platform: sml
    sml_id: sml_meter
    name: "Phase 1 Voltage"
    obis_code: "1-0:32.7.0"
    unit_of_measurement: "V"
    device_class: voltage
    state_class: measurement
    accuracy_decimals: 1

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password

api:
  encryption:
    key: !secret api_encryption_key

ota:
  password: !secret ota_password
```

ESPHome's SML integration pushes data directly into Home Assistant, where you can build energy dashboards, set up automations (e.g., notifications when power exceeds a threshold), and track consumption trends using the Energy dashboard.

## Hardware Interfaces: Connecting to Your Meter

Smart meters expose data through several physical interfaces. The most common for DIY reading is the optical D0 interface — an infrared LED and phototransistor behind the meter's front panel. An optical reading head (TCRT5000-based, ~€10-25) clips onto the meter face and converts IR pulses to a serial signal.

For wireless meters, a wMBus USB dongle (based on TI CC1101 or similar) can receive OMS telegrams broadcast by gas and water meters. The IMST iM871A-USB and Amber Wireless AMB8465-M are popular options supported by vzlogger.

## Choosing Your Smart Meter Reader

The right choice depends on your existing infrastructure and goals:

- **If you already run Home Assistant**: ESPHome with SML is the most power-efficient solution. An ESP32 draws under 1 watt and integrates natively with the Home Assistant Energy dashboard.

- **If you need a standalone dashboard**: Volkszähler provides beautiful charts and statistics without requiring Home Assistant. It's also the best choice if multiple household members need browser-based access.

- **If you have a heterogenous meter fleet**: vzlogger standalone with MQTT output can handle different meter types (electricity SML, gas wMBus, water pulses) from a single Raspberry Pi, feeding data into InfluxDB and Grafana.

## Why Self-Host Your Smart Meter Reading?

Utility companies collect meter data for billing but don't always expose real-time readings to consumers, or they gate access behind proprietary apps that stop working when the manufacturer discontinues support. Reading your meter directly gives you second-level resolution on power consumption, voltage quality, and phase balance — data that enables informed decisions about solar sizing, heat pump optimization, and appliance-level energy auditing.

For integrating this data with broader home automation, see our [ESPHome smart home bridges guide](../zigbee2mqtt-vs-zwave-js-ui-vs-esphome-self-hosted-smart-home-bridges-guide-2026/). If you're building a complete energy management system, check our [MQTT platform comparison](../self-hosted-mqtt-platforms-mosquitto-emqx-hivemq-iot-guide-2026/) for the messaging layer. For visualizing time-series data from your meters, our [time-series database guide](../influxdb-vs-questdb-vs-timescaledb-self-hosted-time-series-database-guide-2026/) covers the storage backend options.

## Deployment Architecture for Multi-Meter Households

In a typical home with separate electricity, gas, and water smart meters, a single Raspberry Pi running vzlogger can read all three simultaneously. Electricity data comes via the optical SML interface, gas via wMBus at 868 MHz, and water via pulse counting on GPIO pins. Data flows through MQTT to InfluxDB for long-term storage and Grafana for visualization. Home Assistant's Energy dashboard consumes the MQTT topics to present a unified view of total household energy, water consumption, and associated costs.

For larger properties or multi-tenant buildings, deploy one ESP32-based reader per meter cluster connected over WiFi, with all data aggregating to a central MQTT broker and InfluxDB instance. This distributed architecture avoids long cable runs and isolates meter communication issues to individual reader nodes, making troubleshooting straightforward.


## FAQ

### Do I need permission from my utility company to read my own meter?

In most jurisdictions, the data on your meter belongs to you. Reading the optical port is non-invasive — it only receives the same data the meter broadcasts for its own display. However, physically tampering with meter seals or internal connections is illegal. Always use the optical port or wireless interface; never open the meter enclosure.

### What if my meter uses a different protocol than SML?

Older meters may use the D0 protocol (IEC 62056-21 Mode C), which vzlogger and Volkszähler support natively. For pulse-output meters (flashing LED on the front panel), you can use an ESP32 with a photodiode and ESPHome's pulse meter sensor. For Modbus meters common in industrial settings, ESPHome and vzlogger both have Modbus RTU/TCP support.

### How often can I read data from the meter?

SML meters typically broadcast telegrams every 1-10 seconds continuously, so you can capture data at sub-second resolution. D0 meters require a request-response cycle and can be polled every 1-5 seconds depending on the meter model. The limiting factor is usually your data storage backend, not the meter itself.

### Can I read gas and water meters with these tools?

Yes. Many modern gas and water meters broadcast consumption data via Wireless M-Bus (wMBus) at 868 MHz. vzlogger supports wMBus through USB dongles (iM871A, AMB8465-M). For pulse-output water meters, ESPHome's pulse counter sensor can count each unit of flow and calculate consumption rates.

### How does the total cost of ownership compare to commercial solutions?

A commercial smart meter gateway costs €80-300 and often ties you to a specific vendor's cloud platform. A DIY solution costs €10-25 for an optical reading head plus an ESP32 (€5-10) or a used Raspberry Pi (€30-50). The open-source software is free, and you retain full data sovereignty — your consumption data never leaves your local network.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Smart Meter Readers: Volkszahler vs vzlogger vs ESPHome SML Parser",
  "description": "Compare Volkszahler, vzlogger, and ESPHome SML for reading smart meter data. Covers SML protocol, hardware interfaces, ESP32 firmware, Docker Compose setups, and Home Assistant Energy dashboard integration.",
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

