---
title: "Self-Hosted Pool & Spa Controllers: nodejs-poolController vs AqualinkD vs Home Assistant"
date: "2026-06-07"
tags: ["pool-automation", "home-automation", "raspberry-pi", "iot", "mqtt", "smart-home"]
draft: false
---

## Introduction

If you own a swimming pool or hot tub, you know the drill: walk outside to check temperature, manually flip switches for pumps and heaters, and guess when to add chemicals. Pool equipment manufacturers sell proprietary automation systems that lock you into their ecosystem and charge premium prices for basic features. A self-hosted pool controller puts you back in control — giving you a web dashboard, mobile access, automated scheduling, and integration with your existing smart home setup, all running on a Raspberry Pi or low-power server.

In this guide, we compare three approaches to self-hosted pool automation: **nodejs-poolController** for deep equipment-level control, **AqualinkD** for Jandy/Aqualink hardware owners, and **Home Assistant with ESPHome** for a fully DIY smart home integrated solution.

## Tool Comparison

| Feature | nodejs-poolController | AqualinkD | Home Assistant + ESPHome |
|---------|----------------------|-----------|--------------------------|
| GitHub Stars | 387+ | 229+ | 75,000+ (Home Assistant) |
| Primary Language | TypeScript | C | Python / YAML |
| Supported Hardware | Pentair, Hayward, Jandy, generic | Jandy Aqualink RS | Any (ESP32/ESP8266 sensors) |
| Web Dashboard | Yes (built-in) | Via MQTT/HA | Yes (Lovelace) |
| Mobile Access | PWA | Via Home Assistant | Yes (HA Companion App) |
| MQTT Support | Yes | Yes | Native |
| Chemical Monitoring | Via add-ons | No | Custom sensors |
| Docker Support | Yes | Yes | Yes |
| Installation Complexity | Medium | Low | Medium-High |
| License | AGPL-3.0 | GPL-3.0 | Apache 2.0 |

## nodejs-poolController: The Comprehensive Choice

[nodejs-poolController](https://github.com/tagyoureit/nodejs-poolController) is the most feature-complete open source pool controller available. Written in TypeScript, it communicates directly with pool equipment from major manufacturers including Pentair (IntelliTouch, EasyTouch), Hayward (Goldline, AquaLogic), and Jandy (Aqualink RS). It runs as a Node.js application on any Linux system, with official support for Raspberry Pi.

The controller provides a progressive web app (PWA) dashboard accessible from any device on your network. It handles pump speed control, valve actuators, heater management, salt chlorine generators, and color LED lighting. The event-based architecture allows you to create automation rules like "run the filter pump at low speed from 10 PM to 6 AM to save electricity."

**Docker Compose Setup:**

```yaml
version: "3.8"
services:
  pool-controller:
    image: ghcr.io/tagyoureit/nodejs-poolcontroller:latest
    container_name: pool-controller
    restart: unless-stopped
    network_mode: host
    devices:
      - /dev/ttyUSB0:/dev/ttyUSB0
    environment:
      - TZ=America/Chicago
      - PORT=4200
    volumes:
      - ./data:/app/data
      - ./config:/app/config
```

nodejs-poolController uses RS-485 serial adapters to connect to your pool equipment's communication bus. You'll need a USB-to-RS485 adapter (like the common FTDI-based ones) connected between your Raspberry Pi and the pool control panel. Once connected, the controller auto-discovers your equipment and presents a unified interface.

**Chemical dosing support** comes through add-on modules. You can integrate ORP and pH sensors via external microcontrollers (Arduino/ESP32) that report readings over MQTT. The controller then triggers peristaltic pumps for acid and chlorine dosing based on your configured thresholds.

## AqualinkD: Lightweight Daemon for Jandy Owners

[AqualinkD](https://github.com/sfeakes/AqualinkD) is a lightweight C daemon specifically designed for Jandy Aqualink RS pool control systems. If you already have Jandy equipment installed, AqualinkD provides the simplest path to self-hosted control — it translates the proprietary Aqualink RS485 protocol into MQTT messages that any home automation system can consume.

Unlike nodejs-poolController which bundles its own web interface, AqualinkD takes a Unix philosophy approach: do one thing well. It exposes all pool equipment states (pump RPM, temperature, valve positions, heater status, light modes) as MQTT topics. You then use Home Assistant, Node-RED, or any MQTT-compatible dashboard to visualize and control your pool.

**Docker Compose Setup:**

```yaml
version: "3.8"
services:
  aqualinkd:
    image: ghcr.io/sfeakes/aqualinkd:latest
    container_name: aqualinkd
    restart: unless-stopped
    devices:
      - /dev/ttyUSB0:/dev/ttyUSB0
    environment:
      - MQTT_HOST=mosquitto
      - MQTT_PORT=1883
      - TZ=America/Chicago
      - SERIAL_PORT=/dev/ttyUSB0
    depends_on:
      - mosquitto

  mosquitto:
    image: eclipse-mosquitto:2
    container_name: mosquitto
    restart: unless-stopped
    ports:
      - "1883:1883"
    volumes:
      - ./mosquitto/config:/mosquitto/config
      - ./mosquitto/data:/mosquitto/data
```

The beauty of AqualinkD is its simplicity. Configuration is minimal — point it at your serial device and MQTT broker, and it starts publishing. Home Assistant auto-discovers the MQTT entities, giving you instant Lovelace dashboard cards for pool temperature, pump control, and scheduling without writing a single line of YAML.

AqualinkD supports all standard Aqualink RS features: single-speed and variable-speed pumps, solar heating, gas/electric heaters, spa mode with automatic valve actuation, salt chlorine generators, and color LED light control. It also handles the spa spillover mode that Jandy systems use to refresh spa water.

## Home Assistant + ESPHome: The DIY Sensor Approach

If you want maximum flexibility or have equipment not covered by the other two options, **Home Assistant** combined with **ESPHome** lets you build pool automation from the ground up. This approach excels when you need custom sensor integration — water temperature probes, pH/ORP sensors, flow meters, and ambient light sensors.

With ESPHome, you flash an ESP32 or ESP8266 microcontroller with a YAML-defined firmware that reads sensors and controls relays. The ESP device connects to your WiFi network and communicates with Home Assistant via the native ESPHome API or MQTT:

```yaml
# ESPHome configuration for pool temperature monitoring
esphome:
  name: pool-sensor
  platform: ESP32
  board: esp32dev

sensor:
  - platform: dallas
    address: 0x1234567890abcdef
    name: "Pool Water Temperature"
    unit_of_measurement: "°F"
    accuracy_decimals: 1

  - platform: adc
    pin: GPIO34
    name: "pH Sensor Value"
    unit_of_measurement: "pH"
    filters:
      - calibrate_linear:
          - 0.5 -> 4.0
          - 2.5 -> 9.0

switch:
  - platform: gpio
    pin: GPIO26
    name: "Filter Pump Relay"
    id: pump_relay
    restore_mode: RESTORE_DEFAULT_OFF

  - platform: gpio
    pin: GPIO27
    name: "Heater Relay"
    restore_mode: RESTORE_DEFAULT_OFF
```

In Home Assistant, you create automations for pump scheduling, freeze protection (automatically run pumps when temperature drops below 34°F), and chemical dosing alerts:

```yaml
# Home Assistant automation: freeze protection
automation:
  - alias: "Pool Freeze Protection"
    trigger:
      - platform: numeric_state
        entity_id: sensor.pool_water_temperature
        below: 36
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.filter_pump_relay
      - service: notify.mobile_app
        data:
          message: "Freeze protection activated - pump running"
```

The DIY approach requires more upfront work but gives you unlimited customization. You can add ambient light sensors for automatic landscape lighting, rain sensors to pause irrigation, and even computer vision cameras to detect pool occupancy for safety alerts.

## Why Self-Host Your Pool Controller?

Commercial pool automation systems from Pentair (ScreenLogic, IntelliCenter) and Hayward (OmniLogic) cost $500-2,000+ for the controller hardware alone, plus ongoing subscription fees for mobile app access and cloud connectivity. These systems are closed ecosystems — you cannot integrate them with Home Assistant, Node-RED, or any third-party platform without reverse-engineering their protocols.

A self-hosted controller running on a $35 Raspberry Pi eliminates all recurring costs. Your data stays on your local network — no cloud dependency means the system works during internet outages, which is critical when freeze protection could save you thousands in burst pipe repairs. You also gain the ability to create custom automation rules that manufacturer systems don't support, like dynamic pump speed adjustment based on time-of-use electricity rates.

Data ownership matters for pool maintenance too. Commercial systems store your usage history on their servers and can discontinue support for older hardware at any time. A self-hosted solution keeps years of temperature, chemical, and runtime data in your own database, allowing you to spot trends and optimize maintenance schedules. If you're already running a home automation setup, see our [smart home hub comparison](../2026-04-28-home-assistant-vs-homebridge-vs-scrypted-self-hosted-smart-home-hub-guide-2026/) for platform options. For sensor-level integration, our [MQTT broker guide](../2026-06-02-vernemq-vs-nanomq-vs-flashmq-mqtt-brokers-guide/) covers the messaging backbone these controllers rely on. And if you're into outdoor IoT, our [BBQ smoker controller comparison](../2026-06-06-self-hosted-bbq-smoker-controllers-heatermeter-pifire-esp32/) shows similar ESP32-based temperature monitoring patterns.

## FAQ

### Do I need to modify my pool equipment wiring?

No. Both nodejs-poolController and AqualinkD communicate over the existing RS-485 communication bus that connects your pool equipment. You connect a USB-to-RS485 adapter to the same screw terminals that the manufacturer's control panel uses. The DIY ESPHome approach may require connecting relay modules in parallel with existing switches, which is a low-voltage modification.

### What hardware do I need to get started?

At minimum, a Raspberry Pi (3B+ or newer recommended), a USB-to-RS485 adapter (FTDI-based, ~$15), and a short length of 4-conductor wire. For the ESPHome DIY approach, add an ESP32 development board (~$8) and any sensors you want (DS18B20 temperature probes are ~$3 each). The total hardware cost is typically $50-80 versus $500-2,000 for a commercial controller.

### Can I still use my existing pool remote and control panel?

Yes. Open source controllers operate in parallel with your existing equipment. They read status and send commands over the same RS-485 bus. Your physical control panel, wireless remote, and the self-hosted controller all coexist transparently. The controller does not disable or replace your existing controls — it adds an additional access method.

### Is chemical monitoring accurate enough to trust?

ORP (oxidation-reduction potential) and pH probes from Atlas Scientific or DFRobot provide industrial-grade accuracy when properly calibrated. These are the same sensor technologies used in commercial pool automation systems costing thousands of dollars. The key is regular calibration (every 2-4 weeks) and proper probe storage. For chlorine level estimation via ORP, note that cyanuric acid (stabilizer) affects the ORP-to-chlorine relationship, so you'll need to factor in your CYA level.

### What happens if my Raspberry Pi crashes?

The pool equipment itself continues running on its last-known state. Pumps, heaters, and valves maintain their current settings indefinitely. The self-hosted controller is a convenience layer, not a safety-critical component. For high-availability, you can run the controller on a more robust device like an Intel NUC or set up a secondary Pi with automatic failover using keepalived.

### Which controller should I choose?

Choose **AqualinkD** if you have Jandy Aqualink RS equipment and want the simplest setup — it's a drop-in daemon with near-zero configuration. Choose **nodejs-poolController** if you need the most comprehensive feature set, support for multiple equipment brands, or a standalone web interface without requiring Home Assistant. Choose **Home Assistant + ESPHome** if you want unlimited customization, need to integrate sensors not supported by the other options, or already run Home Assistant for your smart home.

---

**💰 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — it's the world's largest prediction market platform, from election outcomes to technology regulation timelines, you can bet on anything. Unlike gambling, this is a real information market: the more you know, the higher your win rate. I've made solid returns predicting technology-related event outcomes. Sign up with my referral link: [Polymarket.com](https://polymarket.com/?r=fc8a0)**

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Pool & Spa Controllers: nodejs-poolController vs AqualinkD vs Home Assistant",
  "description": "Comprehensive comparison of open source pool and spa automation controllers. Compare nodejs-poolController, AqualinkD, and Home Assistant with ESPHome for DIY pool control, chemical monitoring, and smart home integration on Raspberry Pi.",
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
