---
title: "Self-Hosted Thermal Camera & IR Imaging: MLX90640 vs AMG8833 vs FLIR Lepton Systems"
date: "2026-06-07"
tags: ["thermal-camera", "ir-imaging", "iot", "raspberry-pi", "sensors", "self-hosted", "monitoring"]
draft: false
---

## Introduction

Thermal imaging has moved from military and industrial exclusivity into the maker and self-hosting community. Low-cost infrared sensor arrays like the MLX90640, AMG8833, and FLIR Lepton now provide usable thermal imaging at consumer price points ($30-$200). When paired with a Raspberry Pi or ESP32 running open-source software, these sensors enable self-hosted applications ranging from heat loss detection and equipment monitoring to wildlife observation and home automation.

This guide compares three popular thermal sensor platforms and the open-source software stacks that turn them into self-hosted thermal monitoring systems. We cover hardware capabilities, software options, Docker deployment, and practical use cases for each.

| Feature | MLX90640 | AMG8833 | FLIR Lepton 3.5 |
|---------|----------|---------|-----------------|
| **Resolution** | 32×24 pixels (768) | 8×8 pixels (64) | 160×120 pixels (19,200) |
| **Interface** | I²C | I²C | SPI (VoSPI) |
| **Frame Rate** | Up to 64 Hz | Up to 10 Hz | Up to 8.7 Hz |
| **Temperature Range** | -40°C to 300°C | 0°C to 80°C | -10°C to 140°C (high gain) |
| **Accuracy** | ±1.5°C | ±2.5°C | ±5°C (radiometric) |
| **Price (approx.)** | $40-$60 | $15-$25 | $150-$200 |
| **Raspberry Pi Support** | Excellent (I²C + Python lib) | Excellent (I²C + Python lib) | Good (SPI + breakout req.) |
| **Open-Source Libraries** | Adafruit, Pimoroni | Adafruit, community | pylepton, flirpy |
| **Best For** | Home heat loss, equipment monitoring | Basic presence detection, HVAC | Detailed thermal inspection, wildlife |

## MLX90640: The High-Resolution Budget Pick

The Melexis MLX90640 packs 768 thermal pixels into a compact I²C module, delivering a 32×24 thermal image at up to 64 frames per second. At $40-$60, it offers the best resolution-to-price ratio in the budget thermal sensor market and has become the go-to choice for DIY thermal monitoring projects.

### Key Capabilities

- **Interpolation-friendly**: The 32×24 native resolution interpolates well to 320×240 or higher for smooth visualizations
- **Wide temperature range**: -40°C to +300°C covers everything from freezer monitoring to industrial equipment inspection
- **Python ecosystem**: Excellent library support from Adafruit, Pimoroni, and the community
- **Low power**: Suitable for battery-powered or solar deployments

### Python Capture and Streaming Script

```python
import time
import numpy as np
from PIL import Image
import adafruit_mlx90640
import board
import busio

i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)
mlx = adafruit_mlx90640.MLX90640(i2c)
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_8_HZ

frame = np.zeros((24*32,))
while True:
    try:
        mlx.getFrame(frame)
        # Reshape and interpolate for better visualization
        thermal = np.reshape(frame, (24, 32))
        # Normalize to 0-255 for image output
        min_temp, max_temp = np.min(thermal), np.max(thermal)
        img_array = ((thermal - min_temp) / (max_temp - min_temp) * 255).astype(np.uint8)
        img = Image.fromarray(img_array)
        img = img.resize((320, 240), Image.BICUBIC)
        img.save('/data/thermal_current.jpg')
        time.sleep(0.5)
    except Exception as e:
        print(f"Read error: {e}")
        time.sleep(1)
```

### Docker Compose for 24/7 Thermal Monitoring

```yaml
version: "3.8"
services:
  thermal-monitor-mlx:
    image: hermeshot/thermal-monitor:latest
    container_name: thermal-mlx90640
    privileged: true
    devices:
      - /dev/i2c-1:/dev/i2c-1
    volumes:
      - ./thermal_images:/data/images
      - ./thermal_config:/app/config
    environment:
      - SENSOR_TYPE=mlx90640
      - I2C_BUS=1
      - I2C_ADDRESS=0x33
      - REFRESH_RATE=8
      - IMAGE_INTERVAL=5
      - INTERPOLATION_FACTOR=10
    ports:
      - "8090:8090"
    restart: unless-stopped
```

## AMG8833: The Entry-Level Presence Detector

Panasonic's AMG8833 (also sold as Grid-EYE) provides an 8×8 thermal grid at the lowest price point ($15-$25). While its 64-pixel resolution limits detailed thermal imaging, it excels at presence detection, people counting, and basic HVAC monitoring — applications that need thermal data but not photographic-quality images.

### Key Capabilities

- **Cost-effective presence detection**: Distinguish between humans, pets, and appliances by thermal signature
- **Wide availability**: Multiple breakout board options from Adafruit, SparkFun, and generic manufacturers
- **Simple integration**: Standard I²C interface with well-documented Python libraries
- **Low resolution advantage**: The 8×8 grid is computationally trivial, running smoothly on ESP32 or Pi Zero

### Integration with Home Assistant

```yaml
# configuration.yaml for AMG8833 via ESPHome
sensor:
  - platform: amg8833
    i2c_id: bus_a
    address: 0x69
    update_interval: 5s
    
binary_sensor:
  - platform: template
    name: "Room Occupancy (Thermal)"
    lambda: |-
      if (id(amg8833_max_temp).state > 28.0) {
        return true;
      }
      return false;
```

### Sample ESPHome Configuration

```yaml
esphome:
  name: thermal-presence-sensor
  platform: ESP32

i2c:
  sda: GPIO21
  scl: GPIO22
  scan: true

sensor:
  - platform: amg8833
    address: 0x69
    update_interval: 2s
    name: "Thermal Grid Max Temp"
    
binary_sensor:
  - platform: template
    name: "Human Presence"
    lambda: |-
      return id(thermal_max_temp).state > 28.0;
```

## FLIR Lepton 3.5: Professional-Grade Microbolometer

The FLIR Lepton 3.5 is a radiometric microbolometer array delivering 160×120 pixel thermal images — a massive leap from the MLX90640 and AMG8833. While more expensive ($150-$200) and requiring an SPI interface with a specialized breakout board, it provides true professional-grade thermal imaging suitable for detailed building inspection, PCB diagnostics, and wildlife monitoring.

### Key Capabilities

- **160×120 resolution**: 19,200 thermal pixels — sufficient for identifying individual components on a circuit board
- **Radiometric output**: Each pixel carries calibrated temperature data, not just relative intensity
- **VoSPI interface**: Video-over-SPI protocol streams frames at ~9 Hz
- **Flat-field correction**: Built-in shutter mechanism for consistent calibration

### Software Stack: pylepton + Flask Web Server

```python
import pylepton
from flask import Flask, send_file
import numpy as np
from PIL import Image
import io

app = Flask(__name__)

@app.route('/thermal.jpg')
def thermal_image():
    # Capture frame from Lepton
    frame, _ = pylepton.Lepton().capture()
    # Convert to color-mapped image
    min_val, max_val = np.min(frame), np.max(frame)
    normalized = ((frame - min_val) / (max_val - min_val) * 255).astype(np.uint8)
    img = Image.fromarray(normalized).resize((640, 480), Image.BICUBIC)
    img = img.convert('RGB')
    # Apply color map (ironbow)
    img = apply_colormap(img)
    
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=85)
    buf.seek(0)
    return send_file(buf, mimetype='image/jpeg')

app.run(host='0.0.0.0', port=8091)
```

## Choosing the Right Sensor for Your Application

Each thermal sensor serves different use cases. For **home heat loss detection and insulation auditing**, the MLX90640 provides sufficient resolution at a reasonable price — walk around your house and capture thermal images that reveal cold spots around windows and doors. For **room occupancy sensing and smart HVAC control**, the AMG8833 is ideal: its 8×8 grid is enough to detect human presence while being cheap enough to deploy in multiple rooms. For **wildlife observation and detailed equipment inspection**, the FLIR Lepton's 160×120 radiometric output provides the detail needed to identify animals, hot components, or subtle temperature gradients.

A common pattern combines multiple sensor types: deploy AMG8833 sensors for room-level occupancy detection, use one MLX90640 for periodic insulation checks, and keep a FLIR Lepton for occasional detailed inspections. The total hardware cost for this multi-sensor approach is under $300 — far less than a single commercial thermal camera.

## FAQ

### Do I need a special lens for these thermal sensors?

The MLX90640 and AMG8833 come with integrated lenses. The FLIR Lepton has a fixed lens built into the module. For wider or narrower field of view, third-party lens attachments exist for the Lepton, but they are expensive. The standard ~55° FOV on the Lepton 3.5 and ~110° on the MLX90640 cover most DIY use cases. For long-range thermal observation (wildlife, security), consider the Lepton with its narrower FOV and higher resolution.

### How accurate are these sensors for temperature measurement?

The MLX90640 is rated at ±1.5°C accuracy, making it suitable for applications like detecting overheating equipment or cold spots in walls. The AMG8833's ±2.5°C is fine for presence detection but not precise measurement. FLIR Lepton 3.5 is rated at ±5°C in radiometric mode — surprisingly, the cheaper sensor is more accurate for absolute temperature. However, the Lepton excels at relative temperature differences, which is what matters for most thermal imaging use cases. All sensors require a warm-up period (5-10 minutes) for stable readings.

### Can I run multiple sensors on one Raspberry Pi?

Yes. The MLX90640 and AMG8833 use I²C with configurable addresses (0x33 for MLX90640, 0x68 or 0x69 for AMG8833), so you can run two on the same I²C bus. The FLIR Lepton uses SPI and requires its own chip select line. A Raspberry Pi 4 can comfortably handle 2 MLX90640s or 3-4 AMG8833s simultaneously, plus one Lepton. For larger multi-sensor deployments, consider dedicated ESP32 boards reporting back to a central server via MQTT.

### What software visualizations can I create?

Open-source options include: real-time web dashboards using Flask or FastAPI, Grafana dashboards fed by InfluxDB time-series data, Home Assistant Lovelace cards with thermal overlays, and automated alert systems that trigger when specific temperature thresholds are exceeded. Python libraries like Matplotlib, OpenCV, and Seaborn enable custom visualization pipelines. For continuous monitoring, a common pattern captures thermal images every N minutes, stores them, and generates daily summary videos or heatmaps.

## Why Self-Host Your Thermal Monitoring?

Self-hosting thermal monitoring keeps sensitive environmental data — which can reveal occupancy patterns, equipment status, and building vulnerabilities — entirely within your control. Commercial cloud-connected thermal cameras often upload all imagery to vendor servers for "processing," creating privacy and security risks that are unacceptable for many home and business deployments.

Second, the cost advantage is dramatic. A commercial FLIR thermal camera with equivalent continuous monitoring capability costs $500-$2,000, often with subscription fees for cloud features. A self-hosted MLX90640 setup on a Raspberry Pi Zero 2 W costs under $80 total and provides unlimited, subscription-free monitoring with full data ownership.

Third, integration with existing home automation and monitoring infrastructure is seamless. Thermal readings can trigger Home Assistant automations (turn on HVAC when a room is occupied), feed Grafana dashboards alongside other sensor data, or send alerts via ntfy.sh when equipment temperatures exceed safe thresholds. This unified data pipeline is impossible with siloed commercial products.

For complementary environmental monitoring, see our [indoor CO2 and air quality monitors guide](../2026-06-06-self-hosted-co2-air-quality-monitors-airgradient-enviroplus/). For smart home sensor integration, our [Zigbee2MQTT and Z-Wave bridge guide](../zigbee2mqtt-vs-zwave-js-ui-vs-esphome-self-hosted-smart-home-bridges-guide-2026/) covers the full smart home stack. For SDR-based signal monitoring that complements thermal sensing, check the [SDR receiver and signal processing guide](../2026-06-07-self-hosted-signal-processing-sdr-gnuradio-liquid-dsp-soapysdr/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Thermal Camera & IR Imaging: MLX90640 vs AMG8833 vs FLIR Lepton Systems",
  "description": "Compare MLX90640, AMG8833, and FLIR Lepton thermal sensors for self-hosted IR imaging. Python code, Docker Compose, Home Assistant integration, and complete deployment guide.",
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

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
