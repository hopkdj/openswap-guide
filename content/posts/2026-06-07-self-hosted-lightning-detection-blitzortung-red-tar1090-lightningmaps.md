---
title: "Self-Hosted Lightning Detection Receivers: Blitzortung RED vs Tar1090 vs LightningMaps"
date: "2026-06-07"
tags: ["lightning-detection", "blitzortung", "weather-monitoring", "raspberry-pi", "self-hosted", "sdr", "iot", "environmental-monitoring"]
draft: false
---

## Introduction

Lightning strikes occur approximately 8.6 million times per day worldwide, and detecting them in real time has applications ranging from severe weather warning to insurance claim verification and outdoor event safety. While commercial lightning data services charge subscription fees, a vibrant open-source community has built receiver networks and visualization platforms that let anyone contribute hardware and access global strike data. This article compares three leading self-hosted lightning detection ecosystems: Blitzortung System RED, Tar1090/readsb, and LightningMaps.org integration.

Each solution takes a different approach. Blitzortung provides purpose-built receiver hardware that detects electromagnetic pulses from lightning strikes. Tar1090 is a web-based aircraft tracker that can integrate lightning data from Blitzortung or other sources. LightningMaps.org is the public visualization layer that aggregates data from Blitzortung contributors worldwide. Together, they form a complete stack for detecting, processing, and visualizing lightning strikes from your own backyard.

## How Lightning Detection Works

Lightning strikes generate powerful electromagnetic pulses across a broad frequency spectrum, with peak energy in the VLF (Very Low Frequency, 3-30 kHz) band. Ground-based receivers detect these pulses using either magnetic H-field antennas (ferrite rod or loop antennas) or electric E-field antennas. By measuring the exact arrival time of a pulse at multiple geographically distributed receivers, Time of Arrival (TOA) multilateration can pinpoint the strike location with accuracy down to a few hundred meters.

| Feature | Blitzortung RED | Tar1090 + readsb | LightningMaps.org |
|---------|----------------|------------------|-------------------|
| Primary function | Lightning signal detection receiver | Aircraft tracking with lightning overlay | Public lightning visualization map |
| Detection method | VLF electromagnetic pulse sensing | ADS-B radio + external lightning data | Aggregates Blitzortung station data |
| Hardware required | System RED PCB + H-field/E-field antennas | RTL-SDR dongle + Raspberry Pi | None (data contributor if you run RED) |
| Web interface | Built-in status page + controller UI | Full-featured aircraft map with layers | Global public map with archives |
| Station registration | Required (contribute to network) | Optional | Public by default |
| Docker support | Minimal (controller software) | Full Docker images available | N/A (consumes API) |
| GitHub stars | Community-driven (no central repo) | tar1090: 1,800+ stars | N/A |
| Data ownership | Full raw signal data | Processed aircraft data | Shared with community |
| GPS requirement | Required (for TOA timing) | Optional (for mobile stations) | N/A |

## Blitzortung System RED: The Hardware Receiver

Blitzortung System RED is the current-generation receiver hardware from the Blitzortung community. The RED system consists of a main controller board (STM32F4-based), an H-field preamplifier, and ferrite rod or loop antennas. Setup involves:

```bash
# Register your station at blitzortung.org
# Once approved, you'll receive station ID and access to firmware

# The controller runs a lightweight HTTP server for configuration
# Access the web interface at:
# http://<red-controller-ip>/

# Key configuration steps:
# 1. Set GPS coordinates and antenna orientation
# 2. Configure amplifier gain (auto or manual)
# 3. Set trigger thresholds for stroke detection
# 4. Verify time synchronization via GPS PPS signal
```

The RED controller firmware includes built-in signal processing that filters background noise, detects stroke signatures, and timestamps each event with GPS-synchronized accuracy. Data is sent to the central Blitzortung server, which computes strike locations using TOA from multiple stations and redistributes the computed data back to all participants.

## Tar1090: Aircraft Tracking with Lightning Overlay

Tar1090, maintained by wiedehopf (1,800+ GitHub stars), is primarily an ADS-B aircraft tracking web interface that runs on a Raspberry Pi. It reads aircraft position data from readsb or dump1090 and renders a real-time map. When paired with Blitzortung data, it can overlay lightning strikes on the same map.

```yaml
# docker-compose.yml for Tar1090 with readsb
version: '3.8'
services:
  readsb:
    image: ghcr.io/sdr-enthusiasts/docker-readsb-protobuf:latest
    restart: unless-stopped
    devices:
      - /dev/bus/usb:/dev/bus/usb
    environment:
      - READSB_DEVICE_TYPE=rtlsdr
      - READSB_GAIN=autogain
      - READSB_LAT=52.5200
      - READSB_LON=13.4050
      - READSB_ALT=35
    ports:
      - "30005:30005"
    volumes:
      - /opt/adsb/readsb:/run/readsb

  tar1090:
    image: ghcr.io/sdr-enthusiasts/docker-tar1090:latest
    restart: unless-stopped
    depends_on:
      - readsb
    environment:
      - TAR1090_ENABLE_AC_DB=true
      - TAR1090_FLIGHTAWARELINKS=true
    ports:
      - "8080:80"
    volumes:
      - /opt/adsb/tar1090:/run/tar1090
```

Tar1090's lightning overlay requires integrating Blitzortung data via an additional data source. The mikenye/docker-readsb-protobuf container (242+ stars) provides the ADS-B backend, while lightning data can be pulled from Blitzortung's API or from LightningMaps.org feeds.

## LightningMaps.org: The Visualization Layer

LightningMaps.org is the public-facing visualization platform that aggregates data from thousands of Blitzortung contributors worldwide. While you cannot self-host LightningMaps.org itself (it's a centralized service), your Blitzortung station contributes to it, and the real-time map, historical archives, and regional statistics are freely accessible. The platform provides:

- Real-time global lightning map with station overlays
- Historical strike archives searchable by region and date
- Station statistics and performance metrics
- API access for integrating lightning data into home automation

## Hardware Setup and Connectivity

Setting up a lightning detection station requires careful attention to antenna placement and noise reduction:

1. **Antenna Positioning**: H-field antennas (ferrite rods) should be mounted horizontally at least 2 meters above ground, oriented North-South and East-West for orthogonal coverage. Keep antennas away from metal objects, power lines, and electronic devices.

2. **GPS Antenna**: The GPS receiver provides the precision timing essential for TOA calculations. Mount the GPS antenna with a clear sky view, ideally outdoors or in a south-facing window. The PPS (Pulse Per Second) signal synchronizes sampling to within microseconds.

3. **Noise Mitigation**: Common noise sources include switch-mode power supplies, LED lighting, Ethernet over Powerline adapters, and nearby electric motors. Use ferrite chokes on USB and power cables, and consider running the receiver from a linear power supply or battery for critical deployments.

4. **Network Connectivity**: The RED controller connects via Ethernet. For remote locations, a Raspberry Pi with cellular modem can act as a network bridge, running the controller's data forwarder to Blitzortung servers.

## Choosing the Right Setup

Which combination you choose depends on your goals:

- **Weather enthusiast wanting to contribute**: Start with a Blitzortung System RED kit. You'll join a global network of contributors, gain access to real-time detection data, and see your station's statistics on LightningMaps.org.

- **Aviation hobbyist wanting combined view**: Deploy Tar1090 with readsb for aircraft tracking, then add a Blitzortung station to overlay lightning strikes. The combined map shows both aircraft positions and lightning activity, which is valuable for understanding storm-related flight diversions.

- **Data integration for home automation**: Run a Blitzortung station and pull the processed data via LightningMaps.org API into Home Assistant or Node-RED. Automate alerts when lightning is detected within a configurable radius of your location.

- **Budget-conscious starter**: Begin with Tar1090 + readsb on an existing Raspberry Pi and RTL-SDR dongle. While you won't detect lightning directly, you can overlay publicly available lightning data and participate in aircraft tracking. Add a RED kit later for direct detection.

## Why Self-Host Your Lightning Detection?

Running your own lightning detection receiver puts you in control of environmental data that commercial services charge for. With your own station, you own the raw signal data, can customize alert thresholds to your specific location, and contribute to a global scientific network. Unlike consumer weather stations that only measure local conditions (temperature, humidity, wind), lightning detection covers hundreds of kilometers, giving you early warning of approaching storms well before they reach your location.

For broader weather monitoring, see our [self-hosted weather station guide](../2026-05-04-self-hosted-weather-station-software-weewx-meteobridge/). If you're interested in other SDR (Software Defined Radio) applications, check our [RF spectrum analysis guide](../2026-06-07-self-hosted-rf-spectrum-analysis-rtl-power-spektrum-rtl433-guide/). For integrating sensor data into home automation, our [MQTT platform comparison](../self-hosted-mqtt-platforms-mosquitto-emqx-hivemq-iot-guide-2026/) covers the messaging backbone.

## FAQ

### What hardware do I need to start detecting lightning?

At minimum, you need a Blitzortung System RED kit (controller board + H-field preamplifier + ferrite antennas), a GPS antenna with clear sky view, a 5V power supply, and an Ethernet connection. Total cost is approximately €200-250 for a complete station. You can also add an E-field probe for electric field detection, but H-field alone is sufficient for contributing to the network.

### How accurate is the lightning strike location data?

With 8 or more receiving stations detecting the same stroke, location accuracy is typically within 1-3 kilometers. The Blitzortung network has over 1,000 active stations worldwide, with particularly dense coverage in Europe, North America, and parts of Asia. Accuracy improves with station density — in central Europe, strike locations can be resolved to within 500 meters.

### Can I detect lightning without sending data to Blitzortung?

The RED controller firmware is designed to work with the Blitzortung network, and TOA-based location computation requires multiple geographically distributed receivers. While you can run the controller in standalone mode, you won't get strike location data without participating in the network. If you prefer fully offline operation, consider a simple lightning detector like the AS3935 Franklin sensor, which reports strike distance estimates without network connectivity.

### Does the receiver need to be outdoors?

The H-field ferrite antennas can operate indoors, but performance improves significantly with outdoor placement away from electronic noise sources. Many operators mount antennas in a weatherproof enclosure in the attic or on an exterior wall. The GPS antenna requires a clear sky view — a south-facing window is usually sufficient if an outdoor mount isn't feasible.

### How does this compare to commercial lightning data services?

Commercial services like Vaisala and Earth Networks charge thousands of dollars per year for lightning data access. The Blitzortung network provides comparable real-time data for free, with the trade-off that you contribute hardware and bandwidth to the network. For personal, educational, and small business use, Blitzortung's accuracy and coverage are excellent. For mission-critical applications like airport operations, commercial services offer guaranteed uptime and contractual reliability.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Lightning Detection Receivers: Blitzortung RED vs Tar1090 vs LightningMaps",
  "description": "Compare Blitzortung System RED, Tar1090 with readsb, and LightningMaps.org for self-hosted lightning detection. Covers hardware setup, Docker Compose configs, antenna placement, and Home Assistant integration.",
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

