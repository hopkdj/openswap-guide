---
title: "Home Assistant vs Homebridge vs Scrypted: Self-Hosted Smart Home Hub Guide 2026"
date: 2026-04-28
tags: ["comparison", "guide", "self-hosted", "smart-home", "home-automation"]
draft: false
description: "Compare Home Assistant, Homebridge, and Scrypted for self-hosted smart home management. Learn which platform best fits your automation, HomeKit bridging, and video surveillance needs with Docker deployment guides."
---

When building a self-hosted smart home, one of the most important decisions is choosing the central hub that ties everything together. The open-source ecosystem offers several strong options, each with a different philosophy and set of strengths.

This guide compares three popular platforms — **Home Assistant**, **Homebridge**, and **Scrypted** — to help you decide which one (or combination) fits your setup. We will cover installation via Docker Compose, feature comparison, integration capabilities, and real-world deployment considerations.

## Why Self-Host Your Smart Home Hub?

Running your own smart home hub gives you full control over your devices, data, and automations. Unlike cloud-based solutions, self-hosted platforms:

- **Keep your data local** — no telemetry sent to third-party servers
- **Work offline** — automations continue running even when the internet is down
- **Support hundreds of integrations** — connect devices from different manufacturers without being locked into a single vendor ecosystem
- **Cost nothing** — all three platforms covered here are free and open-source
- **Run on inexpensive hardware** — a Raspberry Pi 4 or a small x86 mini PC is more than sufficient

For related reading, check out our [Zigbee/Z-Wave bridge comparison](../zigbee2mqtt-vs-zwave-js-ui-vs-esphome-self-hosted-smart-home-bridges-guide-2026/) for device-level connectivity options, and our [video surveillance guide](../self-hosted-video-surveillance-nvr-frigate-zoneminder-motioneye/) for camera integration strategies.

## Quick Comparison Table

| Feature | Home Assistant | Homebridge | Scrypted |
|---|---|---|---|
| **Primary Focus** | Full home automation platform | Apple HomeKit bridge | Video & camera integration |
| **GitHub Stars** | 86,800+ | 25,200+ | 5,700+ |
| **Language** | Python / TypeScript | TypeScript | TypeScript |
| **Last Updated** | April 2026 | April 2026 | April 2026 |
| **HomeKit Support** | Via HomeKit Bridge integration | Native (primary purpose) | Via NVR plugin |
| **Google Home / Alexa** | Via Nabu Casa cloud or local | Via plugins | Limited |
| **Camera / NVR** | Built-in (basic) | Via plugins (limited) | Built-in (advanced, primary feature) |
| **Plugin Ecosystem** | 2,500+ integrations | 2,000+ plugins | 100+ packages |
| **UI Quality** | Excellent, Lovelace dashboard | Basic config UI (homebridge-config-ui-x) | Good, device-centric |
| **Automation Engine** | YAML + visual editor, Node-RED possible | No native automations | Built-in triggers |
| **Resource Usage** | Moderate (~500MB RAM idle) | Light (~150MB RAM idle) | Moderate-High (video processing) |
| **Zigbee / Z-Wave** | Native (via ZHA / Z-Wave JS) | Via plugins | Via plugins |
| **Multi-User** | Yes, with roles | No (single admin) | Yes |
| **Docker Support** | Official image | Official + oznu image | Official image |

## Home Assistant: The Full-Featured Automation Platform

[Home Assistant](https://www.home-assistant.io/) is the most popular open-source home automation platform, with over 86,800 GitHub stars and an extremely active development community. It aims to be a complete replacement for any cloud-based smart home service.

### Key Strengths

- **Massive integration library** — over 2,500 built-in integrations covering virtually every smart device brand, protocol, and service
- **Powerful automation engine** — YAML-based automations with triggers, conditions, and actions, plus a visual automation editor for beginners
- **Lovelace dashboards** — highly customizable UI with cards for every purpose: floor plans, graphs, media controls, camera feeds
- **Zigbee and Z-Wave support** — native integration via ZHA and Z-Wave JS, eliminating the need for a separate hub
- **Add-on system** — install supplementary services (MQTT broker, database, file editor) directly within Home Assistant
- **Blue/Green deployment** — supports supervised installation on Debian, Home Assistant OS on dedicated hardware, or Docker container

### Docker Compose Deployment

The official Home Assistant container is the easiest way to get started with a self-managed installation:

```yaml
version: "3"
services:
  homeassistant:
    container_name: homeassistant
    image: ghcr.io/home-assistant/home-assistant:stable
    volumes:
      - ./config:/config
      - /etc/localtime:/etc/localtime:ro
      - /run/dbus:/run/dbus:ro
    restart: unless-stopped
    privileged: true
    network_mode: host
```

For deployments where `network_mode: host` is not desirable (e.g., on Synology NAS), use port mapping instead:

```yaml
version: "3"
services:
  homeassistant:
    container_name: homeassistant
    image: ghcr.io/home-assistant/home-assistant:stable
    volumes:
      - ./config:/config
      - /etc/localtime:/etc/localtime:ro
    restart: unless-stopped
    ports:
      - "8123:8123"
```

After starting the container, the web interface is available at `http://<server-ip>:8123`. The initial setup wizard guides you through creating an admin account and detecting devices on your network.

### Architecture Notes

Home Assistant stores all configuration in YAML files under `/config`. The `configuration.yaml` file is the main entry point, with separate files for automations, scripts, templates, and sensor definitions. The system uses SQLite by default for its state database, but can be configured to use MariaDB or PostgreSQL for larger installations.

## Homebridge: The Apple HomeKit Bridge

[Homebridge](https://homebridge.io/) has a single, focused purpose: expose non-HomeKit devices to Apple's HomeKit ecosystem. If you are invested in Apple Home and want to control devices that lack native HomeKit support, Homebridge is the go-to solution. With over 25,200 GitHub stars, it has a large and active plugin community.

### Key Strengths

- **HomeKit native** — every device exposed through Homebridge appears as a native HomeKit accessory in the Apple Home app
- **Siri integration** — all bridged devices are controllable via Siri voice commands
- **2,000+ plugins** — covers almost any device or service, from Philips Hue to Tasmota flashed ESP devices
- **Lightweight** — runs comfortably on a Raspberry Pi Zero 2 W with minimal resource usage
- **Simple configuration** — all settings live in a single `config.json` file

### Docker Compose Deployment

The most popular Docker deployment uses the `oznu/homebridge` image, which includes the web-based configuration UI (homebridge-config-ui-x) pre-installed:

```yaml
version: "3"
services:
  homebridge:
    container_name: homebridge
    image: oznu/homebridge:latest
    restart: unless-stopped
    network_mode: host
    environment:
      - TZ=UTC
      - HOMEBRIDGE_CONFIG_UI=1
      - HOMEBRIDGE_CONFIG_UI_PORT=8581
    volumes:
      - ./homebridge:/homebridge
```

If your environment does not support `network_mode: host`, use explicit port mapping:

```yaml
version: "3"
services:
  homebridge:
    container_name: homebridge
    image: oznu/homebridge:latest
    restart: unless-stopped
    ports:
      - "8581:8581"
    environment:
      - TZ=UTC
      - HOMEBRIDGE_CONFIG_UI=1
      - HOMEBRIDGE_CONFIG_UI_PORT=8581
    volumes:
      - ./homebridge:/homebridge
```

The configuration UI at `http://<server-ip>:8581` allows you to install plugins, edit `config.json`, and monitor logs without touching the filesystem directly.

### How HomeKit Pairing Works

Homebridge creates a virtual HomeKit bridge that Apple devices discover over the local network via mDNS/Bonjour. When you pair Homebridge with your iPhone or iPad (by scanning the QR code shown in the config UI), all configured accessories appear in the Apple Home app. Each plugin translates the device's native protocol into the HomeKit Accessory Protocol (HAP).

### Limitations

Homebridge does **not** provide its own automation engine, dashboard, or multi-platform support. It is purely a bridge — you still need Apple devices (iPhone, iPad, HomePod, or Apple TV) to act as the home hub for remote access and automations. For users outside the Apple ecosystem, Homebridge has limited utility.

## Scrypted: The Video-First Smart Home Platform

[Scrypted](https://scrypted.app/) takes a different approach from both Home Assistant and Homebridge. Its primary focus is high-performance video integration — connecting IP cameras, NVR systems, and video streams into a unified management platform. With 5,700+ GitHub stars, it is younger than the other two but growing rapidly, especially among users with multiple cameras.

### Key Strengths

- **Best-in-class camera support** — native integration with ONVIF, RTSP, Reolink, UniFi Protect, Ring, Nest, Arlo, and dozens more camera brands
- **Low-latency streaming** — optimized transcoding pipeline that delivers sub-second latency to Apple HomeKit, Google Home, and Alexa
- **Built-in NVR** — 24/7 recording, motion detection, object detection zones, and timeline scrubbing — no separate NVR software needed
- **HomeKit Secure Video** — native support for Apple's HomeKit Secure Video, enabling on-device motion/person/package detection
- **Automation triggers** — create automations based on camera events (motion detection, person detected, doorbell pressed)
- **Multi-platform bridges** — simultaneously expose cameras to HomeKit, Google Home, Alexa, and Alexa Gadget

### Docker Compose Deployment

Scrypted provides an official Docker image. Here is a production-ready compose file:

```yaml
version: "3"
services:
  scrypted:
    container_name: scrypted
    image: koush/scrypted
    restart: unless-stopped
    network_mode: host
    environment:
      - TZ=UTC
    volumes:
      - ./scrypted-data:/server/volume
      - /var/run/dbus:/var/run/dbus:ro
    devices:
      - /dev/dri:/dev/dri
    cap_add:
      - SYS_ADMIN
```

The `/dev/dri` device mapping enables hardware-accelerated video transcoding via Intel Quick Sync or AMD VCE, significantly reducing CPU usage when streaming to multiple devices simultaneously. For systems without GPU passthrough, remove the `devices` and `cap_add` sections — Scrypted will fall back to software transcoding.

If `network_mode: host` is not available:

```yaml
version: "3"
services:
  scrypted:
    container_name: scrypted
    image: koush/scrypted
    restart: unless-stopped
    ports:
      - "10444:10444"
      - "8080:8080"
      - "1935:1935"
      - "50000-50100:50000-50100/udp"
    environment:
      - TZ=UTC
    volumes:
      - ./scrypted-data:/server/volume
```

The UDP port range (`50000-50100`) is required for RTSP streaming. Without it, camera streams will fail to reach external clients.

### Storage Configuration

Scrypted stores recorded video in the mounted volume. For continuous 24/7 recording from multiple cameras, plan storage accordingly:

```yaml
    volumes:
      - ./scrypted-data:/server/volume
      - /mnt/nvr-recordings:/nvr:rw
```

You can configure retention policies (e.g., keep 7 days of continuous recording, 30 days of motion-triggered clips) through the Scrypted web interface at `http://<server-ip>:10444`.

## Head-to-Head: Which Should You Choose?

### Scenario 1: You want full home automation

**Choose Home Assistant.** It is the only platform among the three that provides a complete automation engine, dashboard system, and device management in a single package. If you want to create automations like "when the front door opens after sunset, turn on the hallway light and send a notification," Home Assistant handles this natively.

### Scenario 2: You are deep in the Apple ecosystem

**Choose Homebridge** (or run it alongside another platform). If your primary interface is Apple Home and you want Siri control over non-HomeKit devices, Homebridge is purpose-built for this. Pair it with an Apple TV or HomePod as your home hub for remote access.

### Scenario 3: You have multiple IP cameras and want a unified NVR

**Choose Scrypted.** Its video pipeline is significantly more performant than Home Assistant's built-in camera support, and its NVR features rival dedicated commercial solutions. If camera management is your primary need, Scrypted is the clear winner.

### Scenario 4: You want the best of all worlds

**Run multiple platforms together.** This is the most common setup among experienced self-hosters:

- **Home Assistant** as the central automation and dashboard hub
- **Homebridge** running alongside, bridging Home Assistant devices to Apple HomeKit (via the homebridge-homeassistant plugin)
- **Scrypted** handling camera feeds and exposing them to both Home Assistant (via the Scrypted integration) and HomeKit Secure Video

All three platforms run as separate Docker containers on the same host and communicate over the local network. A combined Docker Compose stack looks like this:

```yaml
version: "3"
services:
  homeassistant:
    container_name: homeassistant
    image: ghcr.io/home-assistant/home-assistant:stable
    volumes:
      - ./ha-config:/config
    restart: unless-stopped
    network_mode: host
    privileged: true

  homebridge:
    container_name: homebridge
    image: oznu/homebridge:latest
    restart: unless-stopped
    network_mode: host
    environment:
      - TZ=UTC
      - HOMEBRIDGE_CONFIG_UI=1
      - HOMEBRIDGE_CONFIG_UI_PORT=8581
    volumes:
      - ./homebridge:/homebridge

  scrypted:
    container_name: scrypted
    image: koush/scrypted
    restart: unless-stopped
    network_mode: host
    environment:
      - TZ=UTC
    volumes:
      - ./scrypted-data:/server/volume
    devices:
      - /dev/dri:/dev/dri
    cap_add:
      - SYS_ADMIN
```

This setup requires approximately 1-2 GB of RAM total and runs well on a Raspberry Pi 4 (4 GB model) or any small x86 machine. For installations with more than 4 cameras running 24/7 recording, consider an x86 system with at least 8 GB RAM and hardware transcoding support.

## Hardware Requirements Comparison

| Platform | Minimum RAM | Recommended RAM | Storage | CPU |
|---|---|---|---|---|
| **Home Assistant** | 512 MB | 2 GB+ | 32 GB (config + database) | Dual-core ARM or x86 |
| **Homebridge** | 256 MB | 512 MB | 8 GB (config + logs) | Single-core ARM |
| **Scrypted** | 1 GB | 4 GB+ (with NVR) | 500 GB+ (for recordings) | Quad-core + GPU for transcoding |

For a combined setup running all three, a Raspberry Pi 4 (4 GB) handles Home Assistant + Homebridge well, but Scrypted with active NVR recording benefits from an x86 system with Intel Quick Sync (any Intel CPU from 7th gen onward).

## Integration Ecosystem

### Home Assistant Integrations

Home Assistant ships with over 2,500 integrations out of the box. Key categories include:

- **Lighting:** Philips Hue, LIFX, Zigbee (ZHA), Lutron, IKEA Tradfri
- **Climate:** Nest, Ecobee, Tuya, generic MQTT thermostats
- **Media:** Plex, Spotify, Sonos, Chromecast, DLNA
- **Sensors:** Zigbee, Z-Wave, Bluetooth LE, ESPHome, Tasmota
- **Network:** Unifi, pfSense, Pi-hole, SNMP
- **Energy:** Solar inverters, EV chargers, smart meters

For IoT protocol integration, our [MQTT platforms guide](../self-hosted-mqtt-platforms-mosquitto-emqx-hivemq-iot-guide-2026/) covers the message brokers that power many of these connections.

### Homebridge Plugins

Homebridge plugins are installed via npm. Popular categories:

- **homebridge-config-ui-x** — web-based management interface (essential)
- **homebridge-hue** — Philips Hue bridge integration
- **homebridge-camera-ffmpeg** — camera streaming to HomeKit
- **homebridge-tuya-platform** — Tuya/Smart Life devices
- **homebridge-homeassistant** — bridge Home Assistant entities to HomeKit

### Scrypted Packages

Scrypted uses a package-based extension system:

- **ONVIF** — generic IP camera integration
- **Reolink** — native Reolink camera support with improved performance
- **Unifi Protect** — UniFi camera NVR integration
- **Ring** — Ring doorbell and camera integration
- **Nest** — Google Nest camera integration
- **HomeKit** — expose devices to Apple HomeKit
- **Home Assistant** — connect to Home Assistant as a management backend

## FAQ

### Can I run Home Assistant, Homebridge, and Scrypted on the same machine?

Yes. All three platforms provide official Docker images and can run simultaneously on a single host. A Raspberry Pi 4 (4 GB) can comfortably run Home Assistant and Homebridge together. Adding Scrypted requires more resources, especially if you use its NVR recording features — for that setup, an x86 mini PC with 8+ GB RAM is recommended.

### Do I need Homebridge if I already have Home Assistant?

Not necessarily. Home Assistant includes a built-in HomeKit Bridge integration that exposes most devices to Apple Home without Homebridge. However, Homebridge has a larger plugin ecosystem and sometimes provides better compatibility with specific devices. Many users run both: Home Assistant for automations and Homebridge for devices that the HomeKit Bridge integration does not handle well.

### Is Scrypted a replacement for Frigate or ZoneMinder?

Scrypted can serve as a full NVR replacement for many users. It supports 24/7 recording, motion-based recording, object detection, and timeline browsing. However, Frigate offers more advanced object detection customization (via its TensorFlow Lite backend) and integrates with Home Assistant more deeply. If you already run Frigate successfully, Scrypted can still be useful as a HomeKit Secure Video bridge for your existing cameras.

### Can Homebridge control devices without an Apple device?

No. Homebridge is specifically designed to bridge devices to Apple HomeKit. You need at least one Apple device (iPhone, iPad, HomePod, or Apple TV) to pair with Homebridge and act as the home hub. Without Apple devices, Homebridge has no interface for controlling your devices. For non-Apple ecosystems, Home Assistant is the better choice.

### How do I expose Scrypted cameras to Home Assistant?

Scrypted provides a native Home Assistant integration. In the Scrypted web interface, install the "Home Assistant" package, configure your Home Assistant URL and access token, and select which cameras/devices to export. They will appear as camera entities in Home Assistant with full stream support. Alternatively, you can use the Scrypted NVR's RTSP endpoint directly in Home Assistant's generic camera integration.

### Which platform supports Matter devices?

Home Assistant has native Matter controller support built in, allowing you to pair Matter-compatible devices directly. Homebridge supports Matter via the `homebridge-matter` plugin (still evolving). Scrypted does not currently have native Matter support, but cameras exposed via HomeKit from Scrypted can be accessed through Apple Home's Matter ecosystem indirectly.

### What is the easiest platform for beginners?

Home Assistant offers the most beginner-friendly experience with its setup wizard, visual automation editor, and extensive documentation. Homebridge requires more technical knowledge to configure plugins via JSON or the config UI. Scrypted sits in the middle — its camera onboarding is straightforward, but advanced features like transcoding tuning and NVR storage management require some familiarity with video formats and codecs.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Home Assistant vs Homebridge vs Scrypted: Self-Hosted Smart Home Hub Guide 2026",
  "description": "Compare Home Assistant, Homebridge, and Scrypted for self-hosted smart home management. Learn which platform best fits your automation, HomeKit bridging, and video surveillance needs with Docker deployment guides.",
  "datePublished": "2026-04-28",
  "dateModified": "2026-04-28",
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
