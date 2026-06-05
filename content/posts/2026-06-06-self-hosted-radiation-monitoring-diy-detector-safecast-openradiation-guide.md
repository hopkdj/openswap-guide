---
title: "Self-Hosted Radiation Monitoring: DIY Particle Detector vs Safecast vs OpenRadiation"
date: "2026-06-06"
tags: ["radiation", "monitoring", "citizen-science", "environmental-sensing", "diy", "geiger-counter", "iot"]
draft: false
---

## Why Monitor Radiation Yourself?

Radiation monitoring sounds like something only nuclear power plant operators need — but citizen-led radiation sensing has proven its value repeatedly. After the Fukushima Daiichi disaster in 2011, Safecast volunteers deployed thousands of portable sensors across Japan, generating the most comprehensive open radiation dataset ever created. Today, affordable silicon photomultipliers and PIN diodes let anyone build a radiation spectrometer capable of distinguishing between different radioactive isotopes — technology that previously cost thousands of dollars in a handheld device.

Self-hosting a radiation monitoring station means you control your environmental data, can set custom alert thresholds, and can contribute to global open-data initiatives. Whether you're monitoring background radiation levels near your home, checking imported goods for contamination, or participating in a citizen science project, open-source tools make radiation detection accessible.

In this guide, we compare three approaches: **DIY Particle Detector** (build your own spectrometer), **Safecast** (global sensor network API and hardware), and **OpenRadiation** (collaborative measurement database).

## Comparison at a Glance

| Feature | DIY Particle Detector | Safecast | OpenRadiation |
|---------|----------------------|----------|---------------|
| **Stars** | 535 | 46 (API) | 12 |
| **Approach** | Hardware + Python spectrometer | Global sensor network + API | Community measurement database |
| **Hardware** | Custom PCB + SiPM sensor | bGeigie Nano, iRacing device | Any detector (manual entry or API) |
| **Language** | Python | Ruby | JavaScript |
| **Data Analysis** | Energy spectrum + isotope ID | Dose rate + GPS mapping | Aggregated measurements |
| **Web Dashboard** | Local Python matplotlib | API-driven (safecast.org) | Web platform |
| **GPS Integration** | Optional | Built-in (bGeigie Nano) | Via mobile app |
| **Installation** | Moderate (solder PCB) | Kit or pre-built | Web registration |
| **Last Update** | June 2021 | May 2025 | March 2026 |
| **License** | MIT | Custom | Open data |

## DIY Particle Detector: Build Your Own Spectrometer

Developed by Oliver Keller at CERN's S'Cool LAB, the DIY Particle Detector is a remarkable project that lets you build a mobile low-cost spectrometer capable of measuring alpha particles and electrons. Originally created for high school physics education, it's evolved into a serious citizen science tool used by hobbyists worldwide.

### Key Features

- **Energy discrimination**: Measures particle energy in keV, not just count rate
- **Isotope identification**: Distinguish between Am-241, K-40, and natural background
- **Silicon photomultiplier (SiPM)**: Uses the MicroFC-60035 sensor for high sensitivity
- **Open-source PCB**: Gerber files available for ordering from PCB manufacturers

### Assembly and Software

```bash
# Clone the detector software
git clone https://github.com/ozel/DIY_particle_detector.git
cd DIY_particle_detector

# Install Python dependencies
pip install numpy scipy matplotlib pyserial

# Connect the detector via USB and run
python detector_analysis.py --port /dev/ttyUSB0 --duration 300
```

```python
# Analyze recorded spectra
import numpy as np
import matplotlib.pyplot as plt

# Load detector data
data = np.loadtxt('measurement_2024.csv', delimiter=',')
channels = data[:, 0]  # ADC channels (energy bins)
counts = data[:, 1]    # Pulse counts per channel

# Convert channels to energy (requires calibration with known source)
calibration_factor = 2.15  # keV per channel (varies by build)
energy = channels * calibration_factor

# Plot energy spectrum
plt.figure(figsize=(10, 6))
plt.step(energy, counts, where='mid', color='darkblue')
plt.xlabel('Energy (keV)')
plt.ylabel('Counts')
plt.title('Gamma Spectrum — Background Radiation')
plt.yscale('log')
plt.grid(True, alpha=0.3)
plt.show()
```

### Hardware Components

The detector is built around a handful of components totaling approximately $60-80:

- MicroFC-60035 SiPM sensor (~$40)
- Custom PCB (order from JLCPCB/OSHPark, ~$5 for 5 boards)
- Amplifier circuit (operational amplifier + passives)
- Arduino Nano or Teensy for ADC readout
- 3D-printed enclosure

```bash
# Flash the Arduino firmware
git clone https://github.com/ozel/DIY_particle_detector.git
cd DIY_particle_detector/firmware
# Open in Arduino IDE, select board "Arduino Nano", click Upload
```

## Safecast: The Global Open Radiation Network

Safecast is the largest open-source environmental monitoring project in the world, born from the Fukushima nuclear disaster response. While Safecast is best known for its hardware (bGeigie Nano — a portable radiation sensor with GPS), the Safecast API and data platform form a self-hostable backend for aggregating and sharing radiation measurements.

### Key Features

- **Global dataset**: Billions of radiation measurements with GPS coordinates
- **Standardized API**: REST API for querying measurements by location, time, and radiation level
- **Hardware designs**: Open-source bGeigie Nano (portable) and Pointcast (fixed station) designs
- **Device-agnostic**: Accepts data from any calibrated sensor

### Querying and Contributing Data

```bash
# Query Safecast API for measurements near Tokyo
curl "https://api.safecast.org/measurements.json?latitude=35.6762&longitude=139.6503&distance=10000&per_page=10"

# Response includes radiation readings in CPM and µSv/h with timestamps
```

```python
# Self-hosted Safecast data ingestion pipeline
import requests
import time
import json

API_BASE = "https://api.safecast.org"

def submit_measurement(lat, lon, value_cpm, device_id, api_key):
    """Submit a radiation measurement to Safecast"""
    payload = {
        "latitude": lat,
        "longitude": lon,
        "value": value_cpm,
        "unit": "cpm",
        "device_id": device_id,
        "captured_at": int(time.time())
    }
    headers = {"X-Api-Key": api_key}
    r = requests.post(f"{API_BASE}/measurements.json",
                      json=payload, headers=headers)
    return r.json()

def get_nearby_measurements(lat, lon, radius_km=10):
    """Query Safecast for nearby measurements"""
    params = {
        "latitude": lat,
        "longitude": lon,
        "distance": radius_km * 1000,
        "order": "captured_at DESC",
        "per_page": 50
    }
    r = requests.get(f"{API_BASE}/measurements.json", params=params)
    return r.json()
```

## OpenRadiation: Community Environmental Monitoring

OpenRadiation is a French-led collaborative platform for sharing environmental radioactivity measurements. Unlike Safecast's hardware-focused approach, OpenRadiation is primarily a data aggregation platform — you can contribute measurements from any calibrated detector, from a simple Geiger counter to a professional spectrometer.

### Key Features

- **Collaborative database**: Open API for submitting and querying radiation measurements
- **Detector-agnostic**: Works with any calibrated instrument
- **Environmental focus**: Designed for long-term background radiation monitoring
- **Educational tools**: Classroom resources for teaching about radioactivity

### Setting Up an OpenRadiation Station

```bash
# Register your station and get an API token at https://www.openradiation.org

# Submit measurements via the API
curl -X POST "https://api.openradiation.org/v1/measurements" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "my-station-01",
    "latitude": 48.8566,
    "longitude": 2.3522,
    "value": 0.12,
    "unit": "uSv_h",
    "measurement_type": "gamma",
    "timestamp": "2026-06-06T12:00:00Z"
  }'
```

OpenRadiation provides a web dashboard for visualizing your station's measurements over time, with comparison against regional averages and historical trends.

## Choosing the Right Solution

Your choice depends on what you want to measure and how involved you want to be in the hardware:

- **Choose DIY Particle Detector** if you want to build and understand the hardware yourself, and need energy-resolved spectroscopy (distinguishing isotopes) rather than just a dose rate. Best for educational use and serious hobbyists.
- **Choose Safecast** if you want to contribute to the world's largest open radiation dataset, need a battle-tested portable sensor design, or want to deploy a fixed monitoring station that feeds into a global network.
- **Choose OpenRadiation** if you already own a calibrated detector and want a simple platform for logging and sharing environmental radiation data without building custom hardware.

## Why Self-Host Your Radiation Monitoring?

Government radiation monitoring networks are sparse — the US EPA's RadNet has approximately 140 fixed monitoring stations across the entire country, averaging one station per 24,000 square kilometers. This leaves enormous gaps where no official radiation monitoring exists. After major nuclear incidents, official data has sometimes been slow to release or insufficiently granular. Citizen-led networks like Safecast filled critical data gaps after Fukushima, providing measurements along roads, in schoolyards, and at residential locations that government surveys missed.

A self-hosted radiation monitoring station serves multiple purposes: it's your personal environmental watchdog, a contributor to global open data, and an educational tool. With a DIY Particle Detector, you can demonstrate alpha, beta, and gamma spectroscopy to students using a device you built yourself. With Safecast, you join a network of thousands of volunteers who have collectively gathered over 200 million radiation measurements worldwide. And with OpenRadiation, you can easily log and trend your local background radiation, establishing a baseline that makes anomalies immediately apparent.

For related environmental monitoring, our [air quality sensor guide](../2026-06-04-self-hosted-air-quality-monitoring-airrohr-luftdaten-sensor-community-guide/) covers AirRohr and Sensor.Community deployments. Our [weather station software comparison](../2026-05-04-self-hosted-weather-station-software-weewx-meteobridge-weather34/) covers meteorological data collection. And for broader sensor data integration, our [MQTT platform guide](../self-hosted-mqtt-platforms-mosquitto-emqx-hivemq-iot-guide-2026/) covers the messaging backbone for IoT sensor networks.

## FAQ

### Do I need a nuclear physics background to operate these tools?

No. The DIY Particle Detector includes excellent educational documentation from CERN. Safecast devices are designed for non-experts to operate. You'll learn about radiation physics as you go, but you don't need prior knowledge to start measuring.

### Are these devices legal to own and operate?

Yes, in all countries. These are radiation DETECTORS (they measure ambient radiation), not sources. They contain no radioactive materials and are legal to own, build, and operate everywhere. The DIY Particle Detector does require a small calibration source (typically Am-241 from a smoke detector) which is legal but may have local regulations.

### What's the difference between a Geiger counter and a spectrometer?

A Geiger counter counts total radiation events (clicks per minute) but can't tell you what's emitting the radiation. A spectrometer like the DIY Particle Detector measures the ENERGY of each particle, producing a spectrum that reveals which radioactive isotopes are present — you can distinguish naturally occurring potassium-40 from artificial cesium-137.

### How much does it cost to set up a radiation monitoring station?

DIY Particle Detector: $60-80 in components plus soldering tools. Safecast bGeigie Nano kit: $400-600 (pre-assembled available). OpenRadiation: free (works with any calibrated detector you already own). A simple Geiger counter with data logging starts around $80-150.

### Can I detect radon with these tools?

Not directly. Radon is an alpha emitter, and the DIY Particle Detector can detect alpha particles if you place a sample directly against the sensor window. However, dedicated radon monitors (like AirThings or RadonEye) are purpose-built for continuous radon monitoring and are recommended if radon is your primary concern.

### How do I calibrate my detector?

The DIY Particle Detector can be calibrated using known radioactive sources: Am-241 from smoke detectors (59.5 keV gamma peak) and K-40 from potassium chloride salt substitute (1,461 keV gamma peak). Safecast bGeigie devices come pre-calibrated. OpenRadiation accepts measurements from any detector you trust.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Radiation Monitoring: DIY Particle Detector vs Safecast vs OpenRadiation",
  "description": "Compare three open-source approaches to citizen radiation monitoring: build your own spectrometer with the DIY Particle Detector, join the global Safecast network, or contribute to the OpenRadiation community database.",
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
