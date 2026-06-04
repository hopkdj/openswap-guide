---
title: "Self-Hosted Aquarium Controllers: reef-pi vs Mycodo vs TerrariumPI Compared"
date: "2026-06-05"
tags: ["aquarium", "reef-pi", "raspberry-pi", "iot", "home-automation", "environmental-monitoring", "self-hosted", "diy"]
draft: false
---

Reef keeping and aquarium maintenance demand precise environmental control — temperature swings of a few degrees, pH drift, or lighting schedule mistakes can crash an entire tank ecosystem. Automated controllers take the guesswork out of aquarium management, monitoring parameters 24/7 and triggering responses faster than any human could.

Three open-source platforms have emerged as the leading self-hosted options for aquarium and terrarium automation: **reef-pi**, **Mycodo**, and **TerrariumPI**. Each runs on a Raspberry Pi, integrates with common sensors and relays, and provides a web-based dashboard for monitoring and control. This guide compares their capabilities, deployment methods, and ideal use cases.

## Comparison at a Glance

| Feature | reef-pi | Mycodo | TerrariumPI |
|---------|---------|--------|-------------|
| **Stars** | 435 | 3,255 | 465 |
| **Language** | Go + JavaScript | Python | Python |
| **Target** | Reef aquariums | General environmental | Terrariums + aquariums |
| **Sensors** | Temperature, pH, optical | 100+ sensor types | Temperature, humidity, light |
| **Relay Control** | 16+ outlets | Unlimited via GPIO/MQTT | GPIO + smart plugs |
| **Dosing Pumps** | Yes (peristaltic) | Yes (PWM + peristaltic) | Yes (timed + conditional) |
| **Lighting** | PWM + schedule | PWM + sunrise/sunset | Timer + light sensor based |
| **Notifications** | Email, Slack | Email, Telegram, MQTT | Telegram, Pushover, email |
| **Data Logging** | Embedded InfluxDB | InfluxDB | SQLite + RRD |
| **API** | REST + gRPC | REST | REST |
| **Docker** | Community images | Official Docker | Manual install |
| **License** | Apache-2.0 | GPL-3.0 | GPL-3.0 |

## reef-pi

reef-pi is a purpose-built reef aquarium controller that runs on Raspberry Pi. Unlike general-purpose automation platforms, reef-pi was designed from the ground up for marine aquarium use — it speaks the language of reef keepers with concepts like photoperiods, dosing schedules, ATO (auto top-off), and water change macros.

The project includes a React-based web UI, embedded time-series database (InfluxDB), and hardware drivers for pH probes (ADS1115 ADC), temperature sensors (DS18B20), optical sensors, and PCA9685 PWM controllers for LED lighting. A pH calibration wizard walks you through buffer solution calibration directly from the web interface.

**Installation on Raspberry Pi:**

```bash
# Download and install reef-pi
wget https://github.com/reef-pi/reef-pi/releases/latest/download/reef-pi-debian-bookworm-armhf.deb
sudo dpkg -i reef-pi-debian-bookworm-armhf.deb

# Enable and start the service
sudo systemctl enable reef-pi
sudo systemctl start reef-pi

# Access the web UI at http://<raspberry-pi-ip>:8080
# Default credentials: admin / reef-pi
```

**Docker deployment (community):**

```yaml
version: "3"
services:
  reef-pi:
    image: ghcr.io/reef-pi/reef-pi:latest
    restart: unless-stopped
    privileged: true  # Required for GPIO access
    ports:
      - "8080:8080"
    volumes:
      - reefpi_data:/var/lib/reef-pi
    devices:
      - /dev/gpiomem:/dev/gpiomem
      - /dev/i2c-1:/dev/i2c-1

volumes:
  reefpi_data:
```

**Strengths:** Reef-specific functionality out of the box — ATO, dosing pumps, water change macros, kalkwasser stirrers. Excellent documentation with wiring diagrams for every sensor and peripheral. Active community of reef keepers sharing configurations. pH calibration wizard makes probe setup straightforward.

**Limitations:** Reef-only focus — overkill for freshwater tanks and not designed for terrariums. Limited sensor ecosystem compared to Mycodo (it supports the sensors reef keepers need, but not much beyond that). Hardware design is more DIY-intensive than commercial controllers like Apex or GHL.

## Mycodo

Mycodo takes a fundamentally different approach — rather than targeting a specific domain, it is a universal environmental monitoring and regulation system that happens to work brilliantly for aquariums. With over 100 supported sensor types, Mycodo handles temperature, humidity, CO2, pH, dissolved oxygen, electrical conductivity, pressure, light, and dozens more.

The real power of Mycodo lies in its conditional logic engine. You can create complex automation rules like: "If pH drops below 7.8 AND it's daytime AND the CO2 scrubber has been off for at least 30 minutes, then activate the CO2 scrubber for 15 minutes." Functions include PID controllers, timers, conditional statements, and math operations that can chain inputs together.

**Installation:**

```bash
# One-line install script (Raspberry Pi OS)
curl -L https://kizniche.github.io/Mycodo/install | bash

# Or manual installation:
git clone https://github.com/kizniche/Mycodo
cd Mycodo
sudo bash install/setup.sh

# Access at https://<raspberry-pi-ip>
# Default: admin / admin
```

**Docker deployment:**

```yaml
version: "3.8"
services:
  mycodo:
    image: kizniche/mycodo:latest
    restart: unless-stopped
    privileged: true
    network_mode: host
    volumes:
      - mycodo_data:/var/mycodo
      - /dev:/dev  # Hardware access
    environment:
      - TZ=America/New_York

volumes:
  mycodo_data:
```

**Strengths:** 100+ sensor types — if a sensor exists, Mycodo probably supports it. Powerful conditional logic with PID, timers, math, and chained functions. Beautiful graphing and data visualization with built-in InfluxDB and Grafana integration. Active development with frequent releases. Multi-camera support for tank monitoring.

**Limitations:** Not aquarium-specific — you will need to configure everything from scratch rather than having reef-preset templates. The sheer number of options can be overwhelming for beginners. Heavier resource usage than reef-pi. Documentation covers so many use cases that aquarium-specific guidance can be hard to find.

## TerrariumPI

TerrariumPI started as a terrarium controller but has grown to support aquariums, paludariums, and other enclosed environments. It focuses on four core functions: temperature control (heaters, fans, heat lamps), humidity management (misters, foggers), lighting (timed, dimmable, sunrise/sunset simulation), and monitoring (sensors, webcams, logging).

The web UI is clean and mobile-friendly, with real-time sensor readouts and toggle switches for manual overrides. TerrariumPI supports MQTT for integration with home automation systems like Home Assistant, and can send notifications via Telegram, Pushover, and email.

**Installation:**

```bash
# Install dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git

# Clone and install
git clone https://github.com/theyosh/TerrariumPI.git
cd TerrariumPI
sudo bash install.sh

# Start the service
sudo systemctl start terrariumpi
# Web UI at http://<raspberry-pi-ip>:8090
```

**Basic Docker deployment:**

```yaml
version: "3"
services:
  terrariumpi:
    image: theyosh/terrariumpi:latest
    restart: unless-stopped
    privileged: true
    ports:
      - "8090:8090"
    volumes:
      - terrariumpi_data:/opt/terrariumpi
    environment:
      - TZ=Europe/Amsterdam

volumes:
  terrariumpi_data:
```

**Strengths:** Excellent for mixed environments (terrariums with water features, paludariums). Sunrise/sunset simulation with smooth dimming transitions. MQTT integration for Home Assistant and Node-RED. Clean, intuitive web interface that works well on mobile. Lightweight and resource-efficient.

**Limitations:** Fewer aquarium-specific features — no ATO, dosing pumps, or water change macros. Smaller community than reef-pi or Mycodo. Documentation is decent but less comprehensive than Mycodo's. Hardware support more limited than Mycodo.

## Choosing the Right Controller

**Pick reef-pi if:** you run a reef tank and want a controller that speaks your language. The dosing pump schedules, ATO, pH calibration, and photoperiod management are designed specifically for reef keeping. The community shares proven configurations for common tank setups.

**Pick Mycodo if:** you want maximum flexibility across multiple environments — a reef tank, a freshwater planted tank, a terrarium, and a greenhouse, all from one platform. The 100+ sensor support and conditional logic engine make it the most powerful option for complex automation. It is also the best choice if you already use Grafana for dashboards.

**Pick TerrariumPI if:** your primary need is terrarium or paludarium control. The humidity management, misting schedules, and sunrise/sunset lighting simulation are excellent. It is also the lightest-weight option and integrates cleanly with Home Assistant via MQTT.

For integrating your controller into a broader IoT ecosystem, see our [self-hosted MQTT broker comparison](../self-hosted-mqtt-platforms-mosquitto-emqx-hivemq-iot-guide-2026/). If you're building custom sensor firmware, our [ESPHome vs Tasmota guide](../2026-05-09-self-hosted-iot-firmware-platforms-esphome-vs-tasmota-vs-espurna/) covers popular options. For visualizing environmental data, see our [self-hosted IoT platform guide](../thingsboard-vs-iotsharp-vs-iot-dc3-self-hosted-iot-platform-guide-2026/).

## Why Self-Host Your Aquarium Controller?

Commercial aquarium controllers from Neptune Systems (Apex) and GHL cost $500-1,500 for the base unit alone, with each additional sensor module running $100-300. A self-hosted reef-pi setup on a Raspberry Pi 4 costs roughly $80-120 for the computer plus $50-150 in sensors and relays — a fraction of the commercial price for comparable functionality.

Data ownership is equally important. Commercial controllers sync data to manufacturer cloud servers — if the company discontinues the product line or changes their terms of service, your historical tank data could become inaccessible. Self-hosted controllers store everything locally, and platforms like Mycodo make it easy to export to InfluxDB or CSV.

Open-source controllers also give you freedom from vendor lock-in. If a commercial pH probe stops being manufactured, you either buy the overpriced proprietary replacement or your controller becomes a brick. With reef-pi or Mycodo, you adapt — support for generic sensors means you can source replacements from any electronics supplier.

The DIY community around these projects is remarkably helpful. reef-pi's forum has hundreds of documented builds with wiring diagrams, 3D-printed enclosures, and configuration files you can adapt. The knowledge sharing alone is worth the switch — you will learn more about your tank's chemistry and biology by building the monitoring system yourself.

For other environmental monitoring projects, check our [air quality monitoring guide](../2026-06-04-self-hosted-air-quality-monitoring-airrohr-luftdaten-sensor-community-guide/) and [solar energy monitoring comparison](../2026-06-04-self-hosted-solar-energy-monitoring-sunsynk-solaranzeige-pvoutput-guide/).

## FAQ

### Do I need programming experience to set these up?

Basic comfort with the Linux command line is helpful but not strictly required. reef-pi provides a `.deb` package for one-line installation, and Mycodo has a one-line install script. The main learning curve is hardware wiring — connecting sensors to GPIO pins on the Raspberry Pi. All three projects provide detailed wiring diagrams. Expect to spend a weekend on the initial setup.

### Can I run these alongside other software on the same Raspberry Pi?

Yes, all three are lightweight enough to coexist with Pi-hole, Home Assistant, or OctoPrint on a Raspberry Pi 4 (4 GB model). A Pi 3 may struggle with Mycodo plus other services. For production tank monitoring, dedicated hardware is recommended — a controller crash from an unrelated application could be catastrophic for livestock.

### What sensors do I need for a basic reef setup?

At minimum: DS18B20 temperature sensor ($3), pH probe with ADS1115 ADC board ($25-40), and a relay module for heater control ($8). A basic reef monitoring kit including these three components costs $40-60. Add optical water level sensors ($5 each) for ATO functionality and PCA9685 PWM boards ($10) for LED lighting control.

### How reliable are these compared to commercial controllers?

With proper setup (quality power supply, SD card wear management), open-source controllers achieve comparable reliability to commercial units. The main failure mode is SD card corruption on the Raspberry Pi — mitigate this by using a high-endurance SD card, enabling read-only filesystem overlays, or booting from an external SSD. Many reef-pi users report years of uninterrupted operation.

### Can I access my controller remotely?

Yes. All three provide web interfaces. For secure remote access, set up a WireGuard VPN tunnel or use a reverse proxy with HTTPS and authentication. Do not expose the controller directly to the internet without HTTPS and strong credentials — tank sabotage via unauthenticated access is a real risk. See our [self-hosted VPN guide](../2026-04-23-wireguard-vs-tailscale-vs-netbird-self-hosted-vpn-comparison-2026/) for secure remote access options.

### What happens if the controller loses power?

All three resume normal operation on power restoration — Raspberry Pi boots, services start, and sensor monitoring resumes. The risk is during the boot window (30-60 seconds) when heating and circulation are unmonitored. For critical systems, pair the controller with a UPS and configure email notifications on boot so you are alerted to power events. Mycodo and TerrariumPI support watchdog timers that can trigger fail-safe relay states if the controller becomes unresponsive.

---

**💰 Test your market instincts on [Polymarket](https://polymarket.com/?r=fc8a0) — the world's largest prediction market platform. From election outcomes to technology regulation timelines, trade on what you know. Unlike gambling, prediction markets reward genuine insight: the more you understand a topic, the better your odds. I use it to trade on technology regulatory events and have turned domain knowledge into profit. Sign up with my referral link:** [Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Aquarium Controllers: reef-pi vs Mycodo vs TerrariumPI Compared",
  "description": "Compare three open-source aquarium and terrarium controllers for Raspberry Pi. reef-pi excels at reef tanks, Mycodo supports 100+ sensors with powerful logic, and TerrariumPI handles mixed environments. Includes installation guides, Docker Compose configs, and sensor wiring tips.",
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
