---
title: "Self-Hosted Indoor CO2 and Air Quality Monitors: AirGradient vs Enviro+ vs CanAirIO — Build Your Own Environmental Sensor Platform"
date: "2026-06-06"
tags: ["self-hosted", "air-quality", "co2", "sensors", "environmental-monitoring", "iot", "raspberry-pi", "esp32", "citizen-science"]
draft: false
---

## Introduction

We spend approximately 90% of our time indoors, yet most people have no idea what's in the air they're breathing. Elevated CO2 levels — common in modern, well-sealed buildings — directly impair cognitive function. Studies show that CO2 concentrations above 1,000 ppm reduce decision-making performance by 15%, and levels above 2,500 ppm can cause a 50% decline in complex reasoning tasks. Volatile organic compounds (VOCs) from furniture, cleaning products, and building materials contribute to "sick building syndrome." Particulate matter (PM2.5) from cooking, candles, and outdoor pollution infiltrates indoor spaces.

Commercial air quality monitors from companies like Awair, Airthings, and IQAir cost $150-300, lock you into proprietary apps, and often require cloud connectivity to function. Open-source alternatives running on Raspberry Pi, ESP32, or Arduino let you build a fully self-hosted monitoring platform for a fraction of the cost — with zero data leaving your network.

In this guide, we compare three leading open-source indoor air quality platforms: **AirGradient** (357 stars), **Enviro+** (435 stars), and **CanAirIO** (128 stars).

## Comparison Table

| Feature | AirGradient | Enviro+ | CanAirIO |
|---------|------------|---------|----------|
| Platform | ESP32 / Arduino (C++) | Raspberry Pi (Python) | ESP32 / Arduino (C++) |
| Stars | 357 | 435 | 128 |
| CO2 Sensor | SenseAir S8 (NDIR) | Optional SCD4x module | MH-Z19 or SCD30 |
| PM Sensor | PMS5003 (PM2.5/PM10) | PMS5003 (optional) | SDS011 or PMS5003 |
| VOC Sensor | No | BME680 (VOC + temp/humidity/pressure) | No |
| Temperature | SHT3x / SHT4x | BME680 (built-in) | DHT22 or BME280 |
| Humidity | SHT3x / SHT4x | BME680 (built-in) | DHT22 or BME280 |
| Display | OLED (optional) | 0.96" LCD (built-in) | OLED (optional) |
| Web Dashboard | Yes (self-hosted) | Via Prometheus/Grafana | Via CanAirIO app or API |
| Cloud Option | AirGradient dashboard (optional) | None required | CanAirIO platform (optional) |
| WiFi | Built-in (ESP32) | Raspberry Pi WiFi | Built-in (ESP32) |
| MQTT Support | Yes | Yes (via Python) | Yes |
| Docker Support | Yes (dashboard) | No (runs on Pi) | No (ESP32 firmware) |
| Calibration | Auto-baseline (400ppm) | Manual/lookup | Manual |
| Total Cost | ~$80-120 | ~$60-100 (plus Pi) | ~$40-70 |

## AirGradient: The Professional-Grade Platform

[AirGradient](https://github.com/airgradienthq/arduino) started as an open-source hardware design for professional-grade indoor air quality monitors. The project has since evolved into a comprehensive platform with pre-assembled hardware kits, open-source firmware (Arduino/ESP32), and a self-hosted web dashboard with Prometheus integration.

The AirGradient ONE (indoor model) uses the SenseAir S8 CO2 sensor — an industrial-grade NDIR (non-dispersive infrared) sensor with automatic baseline calibration. Unlike cheaper electrochemical CO2 sensors that drift over time, NDIR sensors maintain accuracy for years. For particulate matter, it uses the Plantower PMS5003, the de facto standard laser particle counter used by commercial monitors.

**Self-hosted Dashboard with Docker:**

```yaml
version: "3.8"
services:
  airgradient-dashboard:
    image: ghcr.io/airgradienthq/airgradient-prometheus:latest
    container_name: airgradient-dashboard
    restart: unless-stopped
    ports:
      - "9926:9926"
    environment:
      - AG_PROMETHEUS_PORT=9926
```

**ESP32 Firmware Flashing:**

```bash
# Clone the firmware repository
git clone https://github.com/airgradienthq/arduino.git

# Build and flash using PlatformIO
cd arduino
pio run -e airgradient-one -t upload

# Configure WiFi and MQTT through serial monitor
pio device monitor
```

AirGradient devices report data over MQTT, making integration with Home Assistant, Node-RED, or any MQTT-compatible platform trivial. The Prometheus endpoint enables integration with Grafana dashboards for long-term trend analysis.

## Enviro+: The Raspberry Pi Swiss Army Knife

[Enviro+](https://github.com/pimoroni/enviroplus-python) from Pimoroni takes a different approach: instead of a standalone ESP32 device, it's a HAT (Hardware Attached on Top) for the Raspberry Pi that bundles multiple environmental sensors onto a single board. The board includes a BME680 (temperature, humidity, pressure, VOC gas), a light/proximity sensor, a microphone for noise level, and a tiny 0.96" color LCD.

The beauty of Enviro+ is its extensibility. Since it runs on a full Raspberry Pi with Python, you can combine sensor data with any Python library or service. The optional PMS5003 particulate matter sensor connects via a dedicated UART port on the board, and the optional SCD4x CO2 sensor connects via the Stemma QT/Qwiic I2C connector.

**Installation:**

```bash
# Install Enviro+ Python library
git clone https://github.com/pimoroni/enviroplus-python.git
cd enviroplus-python
sudo ./install.sh

# Run the example dashboard
python3 examples/all-in-one.py

# Log to MQTT
python3 examples/mqtt-all.py --broker localhost --topic enviroplus
```

**Prometheus Exporter example:**

```python
from prometheus_client import start_http_server, Gauge
from bme680 import BME680
import time

co2_ppm = Gauge('co2_ppm', 'CO2 concentration in PPM')
temperature_c = Gauge('temperature_celsius', 'Temperature')

start_http_server(8000)
sensor = BME680()

while True:
    if sensor.get_sensor_data():
        co2_ppm.set(sensor.data.equivalent_co2)
        temperature_c.set(sensor.data.temperature)
    time.sleep(10)
```

Enviro+ excels when you want to integrate air quality monitoring into an existing Raspberry Pi setup. If you're already running Pi-hole, Home Assistant, or a media server on a Pi, adding an Enviro+ HAT costs about $60 and requires no additional hardware beyond the sensor board itself.

## CanAirIO: The Citizen Science Network

[CanAirIO](https://github.com/kike-canaries/canairio_firmware) approaches air quality from a citizen science perspective. The project provides open-source firmware for ESP32-based air quality monitors that report data to a community map, creating hyperlocal air quality data that governments don't provide. The firmware supports both CO2 sensors (MH-Z19, SCD30) and particulate matter sensors (SDS011, PMS5003).

CanAirIO's standout feature is its mobile companion app, which shows real-time sensor readings and displays community air quality data on an interactive map. While the official cloud platform exists, the firmware is fully capable of running independently with MQTT or a self-hosted backend.

**Firmware Flashing:**

```bash
# Clone the repository
git clone https://github.com/kike-canaries/canairio_firmware.git
cd canairio_firmware

# Build and flash
pio run -e esp32dev -t upload

# Configure via WiFi captive portal
# Connect to "CanAirIO" WiFi network to configure
```

**MQTT Data Collection:**

```yaml
# Home Assistant sensor configuration
mqtt:
  sensor:
    - name: "CanAirIO CO2"
      state_topic: "canairio/sensor/co2"
      unit_of_measurement: "ppm"
    - name: "CanAirIO PM2.5"
      state_topic: "canairio/sensor/pm25"
      unit_of_measurement: "µg/m³"
    - name: "CanAirIO Temperature"
      state_topic: "canairio/sensor/temperature"
      unit_of_measurement: "°C"
```

CanAirIO is the most budget-friendly option, with hardware costs as low as $40 for a basic CO2 + PM sensor setup. The firmware is lightweight and runs on the most common ESP32 development boards (ESP32-DevKitC, Wemos D1 Mini ESP32, TTGO T-Display).

## Why Self-Host Your Indoor Air Quality Monitoring?

Commercial air quality monitors are a privacy nightmare. An Airthings Wave Plus costs $230 and requires a smartphone app that uploads your indoor environmental data to Airthings' cloud servers. IQAir's AirVisual Pro costs $300 and contributes your data to a global air quality map — whether you want it to or not. Awair's Element was discontinued after the company pivoted to enterprise, bricking thousands of consumer devices.

With an open-source platform, your sensor data stays on your local network. You control retention, visualization, and sharing. Integration with Home Assistant, Grafana, or Node.js dashboards is native — not locked behind proprietary APIs. For broader context, see our guide on [outdoor citizen science air quality stations](../2026-06-04-self-hosted-air-quality-monitoring-airrohr-luftdaten-sensor-community-guide/), which covers the complementary outdoor monitoring ecosystem. If you're building out a broader sensor infrastructure, our [IoT firmware platform comparison](../2026-05-09-self-hosted-iot-firmware-platforms-esphome-vs-tasmota-vs-espurna/) helps you choose the right firmware base for ESP32 devices.

## Sensor Selection Guide

Choosing the right sensors is more important than choosing the platform. Here's what you need to know:

**CO2 Sensors**: NDIR (Non-Dispersive Infrared) sensors are the gold standard. The SenseAir S8 (used by AirGradient) and Sensirion SCD4x series are both NDIR sensors with automatic baseline calibration. The MH-Z19 is a budget NDIR alternative with slightly lower accuracy. Avoid electrochemical CO2 sensors (like the CCS811) — they measure "equivalent CO2" based on VOC levels, not actual CO2 concentration.

**PM Sensors**: Laser particle counters are the standard. The Plantower PMS5003 is the most widely used and well-characterized sensor, capable of measuring PM1.0, PM2.5, and PM10 simultaneously. The SDS011 from Nova Fitness is a cheaper alternative with good accuracy but larger physical size.

**VOC Sensors**: The BME680 (built into Enviro+) measures VOCs using a metal-oxide gas sensor. It can estimate total VOC concentration and derive "equivalent CO2" — useful as a relative indicator but not a substitute for a true NDIR CO2 sensor. The SGP30 from Sensirion is a more accurate VOC sensor that can be added to any platform via I2C.

## Data Visualization with Grafana

All three platforms can export data to Prometheus or InfluxDB, enabling rich dashboards with Grafana. Here's a sample Grafana dashboard JSON for air quality monitoring:

```json
{
  "title": "Indoor Air Quality",
  "panels": [
    {
      "title": "CO2 (ppm)",
      "targets": [{"expr": "co2_ppm"}],
      "thresholds": [
        {"value": 1000, "color": "yellow"},
        {"value": 2000, "color": "red"}
      ]
    },
    {
      "title": "PM2.5 (µg/m³)",
      "targets": [{"expr": "pm25_ugm3"}],
      "thresholds": [
        {"value": 12, "color": "yellow"},
        {"value": 35, "color": "red"}
      ]
    },
    {
      "title": "Temperature (°C)",
      "targets": [{"expr": "temperature_celsius"}]
    }
  ]
}
```

Alert rules can notify you via email, Slack, or webhook when CO2 exceeds thresholds — valuable for home offices, classrooms, and meeting rooms where cognitive performance matters.

## FAQ

### How accurate are DIY CO2 sensors compared to commercial monitors?

NDIR CO2 sensors (SenseAir S8, Sensirion SCD4x) are the same technology used in $150-300 commercial monitors. With automatic baseline calibration (ABC), which assumes the sensor sees fresh air (400ppm CO2) periodically, they maintain ±50ppm accuracy. The difference between a $100 DIY AirGradient and a $250 Airthings Wave Plus is primarily in industrial design and app polish, not measurement accuracy.

### Where should I place an indoor air quality monitor?

CO2 mixes uniformly in a room, so placement is flexible. PM2.5 sensors should be at breathing height (1-1.5m) and away from direct sources (stoves, candles, windows). Avoid placing sensors near HVAC vents, in direct sunlight, or against exterior walls where temperature gradients can affect readings. For offices and bedrooms, place the monitor where you spend most of your time.

### How often should I calibrate CO2 sensors?

NDIR sensors with automatic baseline calibration (ABC) self-calibrate by tracking the minimum CO2 reading over a 7-14 day period and assuming that represents outdoor fresh air (400ppm). If your monitor never sees fresh air (e.g., a 24/7 occupied space), disable ABC and manually calibrate against a known reference every 6-12 months. Most open-source firmware lets you toggle ABC behavior.

### Can these monitors detect carbon monoxide (CO)?

No. CO2 sensors and CO sensors are completely different technologies. This is a critical distinction — CO2 buildup makes you drowsy and impairs cognition, but carbon monoxide (CO) is lethal at high concentrations. You need a dedicated CO detector with an electrochemical sensor. Never use a CO2 monitor as a substitute for a CO alarm. Some Enviro+ configurations include an optional MICS-6814 gas sensor that can detect CO, but this should not replace a proper UL-listed CO detector.

### How do AirGradient, Enviro+, and CanAirIO compare to AirRohr and Luftdaten?

AirRohr and Luftdaten/Sensor.Community focus on **outdoor** air quality monitoring — they're designed for weatherproof installation and community data sharing. AirGradient, Enviro+, and CanAirIO focus on **indoor** monitoring, with a stronger emphasis on CO2 (which is primarily an indoor concern) and personal dashboarding rather than public data contribution. The two categories are complementary: use an outdoor station to understand your neighborhood's air quality and an indoor monitor to optimize your immediate breathing environment. For outdoor monitoring specifics, see our [citizen science air quality station guide](../2026-06-04-self-hosted-air-quality-monitoring-airrohr-luftdaten-sensor-community-guide/).

### What total cost should I budget for a complete setup?

Basic CanAirIO setup: ~$40-60 (ESP32 dev board + MH-Z19 CO2 sensor + DHT22). Mid-range AirGradient: ~$80-120 (ESP32 + SenseAir S8 + PMS5003 + SHT3x + enclosure). Full Enviro+ setup: ~$100-150 (Raspberry Pi + Enviro+ HAT + PMS5003 + SCD4x CO2 module). These costs compare favorably to commercial monitors ($150-300) while providing more flexibility and zero recurring fees.

---

**💰 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — it's the world's largest prediction market platform, where you can bet on everything from election results to technology regulation timelines. Unlike gambling, this is a real information market: the more you know, the better your odds. I've made good returns predicting technology-related event outcomes. Sign up with my referral link: [Polymarket.com](https://polymarket.com/?r=fc8a0)**

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Indoor CO2 and Air Quality Monitors: AirGradient vs Enviro+ vs CanAirIO — Build Your Own Environmental Sensor Platform",
  "description": "Comprehensive comparison of open-source indoor air quality monitoring platforms: AirGradient (ESP32/NDIR CO2), Enviro+ (Raspberry Pi HAT with VOC), and CanAirIO (ESP32/citizen science). Includes sensor selection guide, Docker deployment, Grafana dashboards, and cost analysis.",
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
