---
title: "Self-Hosted Air Quality Monitoring Stations: AirRohr vs Luftdaten vs Sensor.Community"
date: "2026-06-04"
tags: ["self-hosted", "air-quality", "environmental-monitoring", "iot", "sensors", "raspberry-pi", "citizen-science"]
draft: false
---

## Introduction

Air pollution causes an estimated 7 million premature deaths annually according to the World Health Organization. Yet most people have no access to hyperlocal air quality data — government monitoring stations may be dozens of kilometers away, and commercial monitors cost thousands of dollars. The citizen science movement has responded with open-source air quality monitoring platforms that anyone can build for under $50.

This guide compares three interconnected projects in the open-source air quality ecosystem: **AirRohr** (the sensor firmware), **Luftdaten** (the data platform), and **Sensor.Community** (the global network). While technically different components of the same ecosystem, they represent distinct self-hosted choices: build your own sensor node, run your own data server, or join the global citizen network.

## Comparison Table: Three Approaches to Self-Hosted Air Quality

| Approach | AirRohr (Sensor Node) | Luftdaten (Self-Hosted Server) | Sensor.Community (Global Network) |
|----------|----------------------|-------------------------------|-----------------------------------|
| **What It Is** | ESP8266 sensor firmware | Data collection platform | Worldwide citizen network |
| **Stars** | 605★ | 54★ (local server) | Community (0★ web) |
| **Hardware** | ESP8266 + SDS011 + BME280 | Any Linux server / Raspberry Pi | Uses AirRohr nodes |
| **Deployment** | Flash to microcontroller | Docker or manual install | Join via API key |
| **Data Ownership** | Full (stored locally) | Full (your server) | Shared (public data) |
| **Measured Pollutants** | PM2.5, PM10, temperature, humidity | Aggregates multiple nodes | Global PM map |
| **Web Dashboard** | Built-in WiFi web server | Customizable web interface | sensor.community map |
| **API Access** | Local JSON endpoint | REST API | Public API |
| **Cost** | ~$30-40 per node | $0 (existing server) | Free |
| **Last Updated** | 2024-12 | Community | Continuous |

## AirRohr: The Sensor Firmware

AirRohr is the firmware that runs on ESP8266 or ESP32 microcontrollers, reading data from particulate matter sensors (SDS011 for PM2.5/PM10) and environmental sensors (BME280 for temperature, humidity, pressure). The firmware connects to WiFi and serves a local web interface showing real-time readings.

A complete AirRohr node costs approximately $30-40 in parts: an ESP8266 board ($4), SDS011 particle sensor ($15), BME280 temperature/humidity sensor ($3), and a short piece of PVC pipe as weatherproof housing ($5). Assembly takes under an hour with basic soldering skills.

```cpp
// Example: AirRohr configuration (via web interface)
// Access the node at its IP address after flashing

// Configuration settings:
WiFi SSID: MyHomeNetwork
WiFi Password: ********

// Measurement interval:
// PM sensors read every 145 seconds (2.5 min)
// BME280 reads every 145 seconds

// Data destinations:
// 1. Local web interface (built-in)
// 2. Sensor.Community API (optional)
// 3. Custom API endpoint (your Luftdaten server)
// 4. MQTT broker (for Home Assistant)

// Dust sensor correction factor:
// The firmware applies a correction factor to SDS011
// readings to match reference-grade instruments
```

The firmware supports multiple data destinations simultaneously: you can send readings to the global Sensor.Community network, your own Luftdaten server, an MQTT broker, and a custom HTTP endpoint — all from a single node. This gives you the flexibility to contribute to citizen science while keeping a private copy of your data.

## Luftdaten: Self-Hosted Data Platform

Luftdaten.info provides the open-source backend that powers the Sensor.Community network. You can self-host this platform to run your own air quality monitoring network — collect data from multiple AirRohr nodes, store it in a local database, and serve it through your own web interface and API.

Self-hosting Luftdaten gives you full control over data retention, access policies, and visualization. Government agencies, universities, and community groups run private Luftdaten instances to monitor local air quality without sending data to third parties.

```yaml
# Self-hosted Luftdaten server with Docker Compose
# docker-compose.yml
version: '3.8'
services:
  # Luftdaten API (receives sensor data)
  api:
    image: luftdaten/api:latest
    ports:
      - "8080:80"
    environment:
      - DB_HOST=postgres
      - DB_NAME=luftdaten
      - DB_USER=luftdaten
      - DB_PASSWORD=secure_password
    depends_on:
      - postgres
    restart: unless-stopped

  # PostgreSQL database for sensor readings
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=luftdaten
      - POSTGRES_USER=luftdaten
      - POSTGRES_PASSWORD=secure_password
    volumes:
      - ./pgdata:/var/lib/postgresql/data
    restart: unless-stopped

  # Optional: Grafana for visualization
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - ./grafana-data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=changeme
    restart: unless-stopped
```

Point your AirRohr nodes to your Luftdaten API endpoint, and data flows directly to your server instead of the public Sensor.Community API. The Grafana integration lets you build custom dashboards tracking PM2.5 trends, comparing multiple sensor locations, and correlating pollution with weather conditions.

## Sensor.Community: The Global Citizen Network

Sensor.Community (formerly Luftdaten.info) is the world's largest citizen-run air quality monitoring network, with over 14,000 active sensors worldwide. It is not software you self-host — it is the global platform you can contribute data to and retrieve data from.

The platform provides a real-time world map of PM2.5 and PM10 readings, historical data downloads, and a public API for researchers and developers. While the data is public, contributing to Sensor.Community means your sensor readings become part of a dataset used by universities, news organizations, and environmental agencies.

```bash
# Register an AirRohr sensor with Sensor.Community
# 1. Build and flash your AirRohr node
# 2. Access the node web interface at its IP
# 3. Go to the "APIs" configuration section
# 4. Check "Send to Sensor.Community"
# 5. Your node will automatically register and appear on the map

# To retrieve data from the Sensor.Community API:
curl "https://api.sensor.community/v1/data/?sensor_type=SDS011&area=51.5,-0.13,10" | python3 -m json.tool
```

The Sensor.Community API is free and open — researchers use it to validate satellite-derived pollution estimates, journalists use it for investigative reporting on industrial emissions, and citizen scientists use it to advocate for cleaner air policies in their communities.

## Why Self-Host Air Quality Monitoring?

Government air quality monitoring stations are sparse — most cities have fewer than 5 stations for millions of residents. Hyperlocal monitoring reveals pollution hotspots that official networks miss: a busy intersection, a diesel truck route, or an industrial facility upwind of a residential area. Running your own sensor gives you data about the air you actually breathe.

Self-hosted monitoring also provides independence from commercial sensor networks that charge subscription fees for access to your own data. Our [weather station software guide](../2026-05-04-self-hosted-weather-station-software-weewx-meteobridge-weather34-guide/) covers complementary environmental monitoring platforms for temperature, humidity, and atmospheric pressure.

For broader IoT data pipelines, our [IoT platform comparison](../thingsboard-vs-iotsharp-vs-iot-dc3-self-hosted-iot-platform-guide-2026/) covers platforms that can aggregate air quality data alongside other sensor streams. See our [Home Assistant guide](../2026-04-28-home-assistant-vs-homebridge-vs-scrypted-self-hosted-smart-home-hub-guide-2026/) for integrating air quality sensors into home automation routines — like triggering air purifiers when PM2.5 exceeds thresholds.

## Sensor Placement and Calibration Best Practices

Where you place your air quality sensor dramatically affects the data quality. Poor placement can make your readings misleading or useless. Here are evidence-based guidelines from the Sensor.Community project and independent validation studies:

**Height matters:** Mount the sensor at breathing height — 1.5 to 3 meters above ground level. This captures the air you actually breathe, not ground-level dust (too low) or diluted upper air (too high). For indoor sensors, avoid placing directly above radiators, air conditioning vents, or kitchen extraction fans that create localized air currents.

**Distance from pollution sources:** Keep outdoor sensors at least 2 meters from building walls, which create micro-eddies that trap pollutants. Avoid direct proximity to barbecue grills, vehicle exhaust, or chimney outlets. For street-side monitoring, the ideal position is 3-5 meters back from the roadway edge — close enough to capture traffic emissions, far enough to avoid direct exhaust plume capture.

**Weatherproofing without airflow restriction:** The standard AirRohr PVC pipe design balances two competing requirements: keeping rain out while allowing free air circulation. The bottom-mounted SDS011 sensor pulls air up through the pipe via natural convection (the sensor generates heat during operation, creating a chimney effect). Never seal the pipe completely — the sensor needs airflow to sample ambient air, not stagnant enclosure air. If mounting in extreme weather, add a secondary rain shield (inverted bucket cap) above the standard housing.

**Calibration against reference monitors:** The SDS011 sensor requires periodic validation. The Sensor.Community project publishes correction factors derived from co-location studies with reference-grade instruments. Apply these corrections in the AirRohr firmware settings. For critical applications, co-locate your sensor with a government monitoring station for 1-2 weeks and compute a local calibration factor specific to your sensor unit and local aerosol composition.

**Seasonal maintenance routine:** Dust accumulation on the SDS011 laser optics degrades accuracy over time. Clean the sensor every 3-6 months by blowing compressed air through the intake (never disassemble the laser module). Replace the BME280 protective membrane annually if installed in high-humidity environments. Check the PVC housing seals before winter — thermal cycling can crack silicone seals and allow moisture ingress that damages electronics.

**Multi-node comparison for quality assurance:** Running two AirRohr nodes side by side for the first week provides an immediate quality check. Identical co-located sensors should agree within ±20% for PM2.5. If readings diverge significantly, one sensor may be faulty or have a dirty laser. This practice catches hardware issues before you commit to long-term data collection.
## FAQ

### What is the difference between AirRohr, Luftdaten, and Sensor.Community?

AirRohr is the firmware that runs on the sensor hardware (ESP8266/ESP32). Luftdaten is the server software that collects and stores sensor data. Sensor.Community is the global public network — the hosted instance of Luftdaten that anyone can contribute data to. Think of AirRohr as the "client," Luftdaten as the "server," and Sensor.Community as the "community instance."

### How accurate are these low-cost sensors?

The SDS011 particle sensor used in AirRohr nodes correlates well with reference-grade instruments (R² > 0.9 in independent studies) but tends to overestimate PM2.5 at high humidity. The AirRohr firmware applies a humidity correction factor. For citizen science and trend monitoring, the accuracy is excellent. For regulatory compliance, reference-grade instruments are required.

### Can I monitor gases like NO2 or ozone?

The standard AirRohr kit measures particulate matter (PM2.5/PM10) only. Gas sensors for NO2, ozone, CO, and SO2 are available but require electrochemical sensors (more expensive, $50-100 each) and more complex calibration. The AirRohr firmware architecture supports additional sensor types, but community support for gas sensors is less mature than for PM.

### How do I weatherproof an outdoor sensor node?

The standard AirRohr design uses a short section of 80mm PVC pipe as a weatherproof housing. The SDS011 sensor sits at the bottom with the air intake facing down, protected by a mesh screen. The BME280 sensor and ESP8266 board are mounted above, with a vent cap at the top. This passive design has proven reliable in rain, snow, and temperatures from -20°C to +50°C.

### How much data does an AirRohr node generate?

Each measurement cycle produces approximately 1KB of JSON data every 145 seconds. This is about 600KB per day or 18MB per month — trivial for even the smallest storage devices. A 32GB SD card in a Raspberry Pi running the Luftdaten server can store decades of sensor data from multiple nodes.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Air Quality Monitoring Stations: AirRohr vs Luftdaten vs Sensor.Community",
  "description": "Build and self-host your own air quality monitoring station. Compare AirRohr firmware, Luftdaten server platform, and the Sensor.Community global citizen network. Includes Docker Compose configs, hardware assembly guides, and ESP8266 sensor wiring.",
  "datePublished": "2026-06-04",
  "dateModified": "2026-06-04",
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
