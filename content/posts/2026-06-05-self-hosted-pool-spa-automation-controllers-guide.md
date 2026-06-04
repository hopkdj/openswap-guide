---
title: "Self-Hosted Pool & Spa Automation Controllers: nodejs-poolController vs Home Assistant vs ESPHome"
date: "2026-06-05"
tags: ["pool-automation", "spa-controller", "iot", "home-automation", "raspberry-pi", "esphome", "self-hosted", "mqtt"]
draft: false
---

## Introduction

Pool and spa automation has traditionally been dominated by proprietary systems from Pentair (IntelliTouch, EasyTouch), Hayward (OmniLogic, ProLogic), and Jandy (AquaLink) — each costing $1,000-3,000 for the controller alone, plus installation fees, and locking you into a single manufacturer's ecosystem of pumps, valves, heaters, and salt chlorine generators.

Open-source pool automation flips this model. By connecting a Raspberry Pi or ESP32 microcontroller to your pool equipment's RS-485 communication bus, you can control pumps, monitor water temperature, manage chemical dosing, and schedule filtration cycles from a web dashboard — all for under $100 in hardware. This guide compares three self-hosted approaches to pool and spa automation.

## Platform Comparison

| Feature | nodejs-poolController | Home Assistant (Pool) | ESPHome Custom |
|---------|----------------------|----------------------|----------------|
| **GitHub Stars** | 387+ | 77,000+ (HA core) | 15,000+ |
| **Primary Language** | JavaScript (Node.js) | Python | C++ / YAML config |
| **Hardware** | Raspberry Pi | Raspberry Pi / x86 | ESP32 / ESP8266 |
| **Pool Protocols** | Pentair, Hayward, Jandy RS-485 | Via HACS integration | Custom RS-485 / relays |
| **Web Dashboard** | Built-in web UI | Lovelace dashboard | No native (MQTT to HA) |
| **Chemical Control** | pH/ORP sensor support | Via add-on sensors | Custom sensors |
| **Scheduling** | Built-in schedules | Home Assistant automations | ESPHome automations |
| **Temperature Monitoring** | Multiple thermistor inputs | Any HA-compatible sensor | DS18B20 / thermistor |
| **Valve Actuation** | Relay board control | GPIO / Shelly relays | GPIO / relay modules |
| **Mobile App** | Web responsive | Home Assistant app | Via MQTT to HA |
| **Docker Support** | Yes (official) | Yes (official) | No (flashed to device) |
| **License** | AGPL-3.0 | Apache-2.0 | GPL-3.0 / MIT |
| **Last Updated** | May 2026 | Active 2026 | Active 2026 |

## nodejs-poolController: Dedicated Pool Platform

nodejs-poolController is the most mature open-source pool automation platform, designed specifically to replace proprietary Pentair, Hayward, and Jandy controllers. It communicates directly with pool equipment over the RS-485 bus using protocol reverse engineering, giving it full control over pumps, valves, heaters, chlorinators, and lighting.

### Key Features

- **Multi-vendor support**: Controls Pentair IntelliTouch/EasyTouch, Hayward ProLogic/AquaLogic, and Jandy AquaLink equipment from a single interface
- **Native scheduling**: Create pump schedules, valve positions, and heater temperature setpoints with a visual scheduler
- **Chemical monitoring**: Supports Atlas Scientific pH and ORP probes for real-time water chemistry data
- **Temperature monitoring**: Reads water temperature, air temperature, and solar panel temperature from connected thermistors
- **Web interface**: Real-time dashboard showing pump speed, valve positions, water temperature, salt level, and chemical readings
- **REST API**: Full programmatic control for integration with home automation systems

### Docker Compose Deployment

nodejs-poolController provides an official Docker Compose configuration:

```yaml
version: "3.8"
services:
  njspc:
    build:
      context: .
      dockerfile: Dockerfile
    image: njspc:local
    container_name: njspc
    restart: unless-stopped
    ports:
      - "4200:4200"
    volumes:
      - ./data:/app/data
      - ./config:/app/config
    devices:
      - "/dev/ttyUSB0:/dev/ttyUSB0"
    environment:
      - TZ=America/Chicago
      - NODE_ENV=production
```

### Hardware Setup

To connect nodejs-poolController to your pool equipment, you need:

1. **RS-485 adapter**: A USB-to-RS485 converter ($10-20) to connect your Raspberry Pi to the pool equipment communication bus
2. **Level shifter**: The pool equipment RS-485 bus typically operates at 5V or 12V — a level shifter converts it to the Raspberry Pi's 3.3V logic level
3. **Wiring**: CAT5 cable is commonly used, connected to the RS-485 A/B terminals on your pool controller board

```bash
# Identify your RS-485 adapter
ls /dev/ttyUSB*
# Expected output: /dev/ttyUSB0

# Test communication
screen /dev/ttyUSB0 9600
```

## Home Assistant Pool Integration

Home Assistant, the popular open-source home automation platform with over 77,000 GitHub stars, can manage pool automation through community integrations and add-ons. While not pool-specific, its flexibility allows building a comprehensive pool control dashboard.

### Setup

```yaml
# docker-compose.yml
version: "3.8"
services:
  homeassistant:
    image: ghcr.io/home-assistant/home-assistant:stable
    container_name: homeassistant
    restart: unless-stopped
    ports:
      - "8123:8123"
    volumes:
      - ./ha_config:/config
      - /etc/localtime:/etc/localtime:ro
      - /run/dbus:/run/dbus:ro
    privileged: true
```

### Pool Automation Integrations

Home Assistant integrates with pool automation through HACS (Home Assistant Community Store):

- **nodejs-poolController integration**: Connects HA to a running nodejs-poolController instance for unified control
- **Pentair ScreenLogic**: Direct integration with Pentair IntelliCenter and EasyTouch systems
- **Hayward OmniLogic**: Local API integration for Hayward OmniLogic controllers
- **Generic thermostat + switch**: For DIY setups using temperature sensors and relay modules

### Example Pool Automation in Home Assistant

```yaml
automation:
  - alias: "Pool Pump Schedule"
    trigger:
      - platform: time
        at: "08:00:00"
    condition:
      - condition: numeric_state
        entity_id: sensor.pool_water_temperature
        above: 10
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.pool_pump

  - alias: "Freeze Protection"
    trigger:
      - platform: numeric_state
        entity_id: sensor.outdoor_temperature
        below: 2
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.pool_pump
```

## ESPHome: Microcontroller-Based Approach

ESPHome provides a firmware platform for ESP32 and ESP8266 microcontrollers that integrates natively with Home Assistant. For pool automation, ESPHome can directly control relays, read temperature sensors, and communicate over RS-485.

### ESPHome Pool Controller Configuration

```yaml
esphome:
  name: pool-controller
  platform: ESP32
  board: esp32dev

# RS-485 communication for Pentair protocol
uart:
  - id: rs485_bus
    tx_pin: GPIO17
    rx_pin: GPIO16
    baud_rate: 9600

# Temperature sensors
sensor:
  - platform: dallas
    address: 0x1234567890abcdef
    name: "Pool Water Temperature"
    unit_of_measurement: "°C"
  
  - platform: dallas
    address: 0xfedcba0987654321
    name: "Pool Air Temperature"

# Relay control for pump
switch:
  - platform: gpio
    pin: GPIO25
    name: "Pool Pump Relay"
    id: pump_relay
    restore_mode: ALWAYS_OFF

  - platform: gpio
    pin: GPIO26
    name: "Pool Light Relay"
    id: light_relay

# pH sensor (analog)
  - platform: adc
    pin: GPIO34
    name: "pH Reading"
    unit_of_measurement: "pH"
    filters:
      - calibrate_linear:
          - 0.0 -> 0.0
          - 3.3 -> 14.0
```

## Deployment Architecture

A hybrid approach combining nodejs-poolController for equipment communication and Home Assistant for unified smart home control provides the best of both worlds:

```
Pool Equipment (Pump, Heater, Valves, Chlorinator)
       │
       ▼
  RS-485 Bus
       │
       ▼
Raspberry Pi running nodejs-poolController
       │
       ├──► Web UI (port 4200) — direct pool control
       │
       └──► REST API ──► Home Assistant — unified smart home
                               │
                               ├──► Automations (schedules, freeze protection)
                               ├──► Mobile App (iPhone/Android control)
                               └──► Voice Control (Alexa/Google Assistant)
```

## Why Self-Host Your Pool Automation?

Commercial pool automation controllers from Pentair, Hayward, and Jandy cost $1,000-3,000 for the base controller, with each additional actuator, sensor, or remote adding hundreds more. A self-hosted solution using a $55 Raspberry Pi 4 and $20 RS-485 adapter can control the same equipment at a fraction of the cost.

Vendor lock-in is another driver. Proprietary controllers only work with that manufacturer's pumps, valves, and chlorinators — or require expensive protocol bridges. nodejs-poolController supports all three major manufacturers from a single Raspberry Pi, giving you the freedom to mix equipment or switch vendors in the future.

The open-source approach also enables features that proprietary controllers charge extra for. Want chemical monitoring with pH and ORP probes? That is a $500+ add-on from Pentair, but a $50 Atlas Scientific probe and nodejs-poolController's built-in sensor support handles it natively. For more IoT sensor integration ideas, see our [air quality monitoring guide](../2026-06-04-self-hosted-air-quality-monitoring-airrohr-luftdaten-sensor-community-guide/).

Integration with your broader smart home ecosystem is the final advantage. A proprietary pool controller is an island — it cannot communicate with your lights, security system, or voice assistant. Home Assistant integration means "Alexa, turn on the spa" works just like "Alexa, turn on the living room lights." For ESPHome-based sensor deployment, our [IoT firmware guide](../2026-05-09-self-hosted-iot-firmware-platforms-esphome-vs-tasmota-vs-espurna/) covers programming microcontrollers. For garden irrigation automation, which shares similar relay/sensor patterns, see our [garden irrigation guide](../2026-06-05-self-hosted-garden-irrigation-opensprinkler-ospi-automated-guide/).

## FAQ

### Is it safe to connect a Raspberry Pi to my pool equipment?

Yes, when done correctly. Pool equipment RS-485 buses operate at low voltage (typically 5-12V) and are isolated from mains power. Always use a properly rated RS-485 adapter with galvanic isolation, and never connect directly to high-voltage pump wiring. The communication bus is separate from the power wiring.

### Can I still use my existing pool remote control alongside nodejs-poolController?

Yes. nodejs-poolController listens on the RS-485 bus and can coexist with your existing Pentair/Hayward/Jandy remote and control panels. However, commands from the web interface may conflict with commands from the physical remote — the last command sent takes precedence. Configure your schedules in one system to avoid conflicts.

### What pool equipment brands are supported?

nodejs-poolController supports Pentair (IntelliTouch, EasyTouch, IntelliCenter), Hayward (ProLogic, AquaLogic, OmniLogic), and Jandy (AquaLink RS). Most equipment manufactured from 2000 onwards uses the RS-485 protocol. Some newer Pentair IntelliCenter systems use Ethernet instead of RS-485 — these require the Pentair ScreenLogic integration in Home Assistant.

### How do I monitor chemical levels (pH, chlorine)?

pH and ORP (oxidation-reduction potential, a proxy for chlorine levels) monitoring requires Atlas Scientific or DFRobot analog sensor probes ($40-80 each). These connect to the Raspberry Pi via I2C or USB, and nodejs-poolController reads them natively. Note that ORP probes require regular calibration and replacement (typically every 1-2 years).

### What happens if the Raspberry Pi loses power or crashes?

nodejs-poolController runs as a monitoring and control overlay — it does not replace your pool equipment's internal safety logic. If the Raspberry Pi crashes, your pump and heater continue operating on their last known settings. The freeze protection and safety cutoff circuits in your pool equipment remain active. Configure nodejs-poolController with Docker's `restart: unless-stopped` for automatic recovery.

### Can I control my spa jets and temperature separately from the pool?

Yes. nodejs-poolController supports spa mode with independent temperature setpoints and jet control. You can configure spa schedules, heat-up times, and valve positions for spa-only circulation. The web interface shows separate pool and spa temperature readings, and Home Assistant automations can trigger "spa mode" based on time of day or manual activation.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Pool & Spa Automation Controllers: nodejs-poolController vs Home Assistant vs ESPHome",
  "description": "Comprehensive comparison of self-hosted pool and spa automation controllers including nodejs-poolController, Home Assistant pool integration, and ESPHome custom firmware. Covers RS-485 protocol, Docker deployment, chemical monitoring, and hardware setup.",
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
