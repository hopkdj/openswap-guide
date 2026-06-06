---
title: "Self-Hosted Plant Care & Garden Management: Plant-it vs HortusFox vs Home Assistant Plant Integration"
date: "2026-06-07"
tags: ["plants", "gardening", "self-hosted", "iot", "home-automation", "plant-care", "sensors", "home-assistant"]
draft: false
---

## Introduction

Keeping houseplants alive requires consistency — watering on schedule, monitoring light levels, tracking fertilization, and responding to early warning signs. For gardeners managing dozens of plants across indoor and outdoor spaces, a self-hosted plant management system turns guesswork into data-driven care.

Three different approaches have emerged in the open-source ecosystem: **Plant-it** (mobile-first plant tracking with watering reminders), **HortusFox** (web-based collaborative plant management), and **Home Assistant Plant Integration** (sensor-driven automation with the plant component). Each takes a fundamentally different approach to solving the same problem — keeping your plants thriving.

## Why Self-Host Your Plant Management?

Commercial plant care apps collect data about your home environment and sell it to advertisers or garden supply companies. A self-hosted solution keeps your plant data private. More importantly, it integrates with your existing smart home infrastructure. When your Home Assistant detects low soil moisture, it can trigger an irrigation system automatically — something no standalone app can do.

Self-hosted plant management also enables collaboration. If multiple family members care for the plants, a shared HortusFox instance lets everyone log watering, add photos, and track growth. No more "did you water the ficus?" text messages.

For the DIY-inclined, self-hosting opens up hardware integration possibilities. Soil moisture sensors, temperature probes, and light meters all feed data into your plant dashboard. For related IoT and garden automation projects, see our [garden irrigation guide](../2026-06-05-self-hosted-garden-irrigation-opensprinkler-ospi-automated-guide/) and [hydroponics controller comparison](../2026-06-05-self-hosted-hydroponics-indoor-farming-controllers-mudpi-openag-guide/). Our [aquarium controller guide](../2026-06-05-self-hosted-aquarium-controllers-reef-pi-mycodo-terrariumpi-guide/) covers similar sensor-based monitoring for aquatic environments.

## Feature Comparison

| Feature | Plant-it | HortusFox | Home Assistant Plant |
|---------|----------|-----------|---------------------|
| GitHub Stars | 1,326 | 1,558 | N/A (Platform Component) |
| Interface | Mobile app (Android) | Web-based dashboard | Web + Mobile (HA app) |
| Multi-User | No | Yes (collaborative) | Yes (HA user system) |
| Sensor Integration | Manual logging | Manual logging | Native (MQTT/Zigbee/BLE) |
| Watering Reminders | Push notifications | Calendar-based | Automation-triggered |
| Photo Tracking | Yes | Yes | Via camera entities |
| Plant Database | Built-in species library | Customizable | Custom entities |
| Docker Support | Limited | Official image | Via HA OS |
| Automation | None | None | Full (HA automations) |
| Last Update | 2026 | 2026 | 2026 (continuous) |

## Plant-it: Mobile-First Plant Companion

Plant-it is an open-source Android app with a self-hosted backend that focuses on simplicity. You add plants from its built-in species database, set watering intervals, and receive push notifications when it is time to water. The app includes a photo log for tracking plant growth over time and a basic notes system for recording observations.

### Docker Compose Example

```yaml
version: "3.8"
services:
  plant-it-backend:
    image: ghcr.io/mdeluise/plant-it-backend:latest
    ports:
      - "8080:8080"
    volumes:
      - plantit_uploads:/app/uploads
      - plantit_logs:/app/logs
    environment:
      - SPRING_DATASOURCE_URL=jdbc:mysql://plantit_db:3306/plantit
      - SPRING_DATASOURCE_USERNAME=plantit
      - SPRING_DATASOURCE_PASSWORD=plantitpass
      - JWT_SECRET=your-secret-key
    depends_on:
      - plantit_db
    restart: unless-stopped

  plantit_db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: plantit
      MYSQL_USER: plantit
      MYSQL_PASSWORD: plantitpass
    volumes:
      - plantit_mysql:/var/lib/mysql
    restart: unless-stopped

volumes:
  plantit_uploads:
  plantit_logs:
  plantit_mysql:
```

## HortusFox: Collaborative Plant Management

HortusFox takes a web-first approach with a clean, modern dashboard for managing multiple plants. It supports user accounts with role-based permissions, making it ideal for shared spaces — community gardens, office plants, or families. Each plant gets a detailed profile page with custom attributes, watering schedules, fertilization logs, and photo galleries.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  app:
    image: ghcr.io/danielbrendel/hortusfox-web:latest
    ports:
      - "8080:80"
    volumes:
      - app_images:/var/www/html/public/img
      - app_logs:/var/www/html/app/logs
      - app_backup:/var/www/html/public/backup
      - app_themes:/var/www/html/public/themes
    environment:
      APP_ADMIN_EMAIL: "admin@example.com"
      APP_ADMIN_PASSWORD: "securepassword"
      APP_TIMEZONE: "UTC"
      DB_HOST: db
      DB_PORT: 3306
      DB_DATABASE: hortusfox
      DB_USERNAME: user
      DB_PASSWORD: password
    depends_on:
      - db

  db:
    image: mariadb
    environment:
      MARIADB_ROOT_PASSWORD: my-secret-pw
      MARIADB_DATABASE: hortusfox
      MARIADB_USER: user
      MARIADB_PASSWORD: password
    volumes:
      - db_data:/var/lib/mysql

volumes:
  db_data:
  app_images:
  app_logs:
  app_backup:
  app_themes:
```

## Home Assistant Plant Integration: Sensor-Driven Automation

Home Assistant takes a fundamentally different approach to plant care. Rather than relying on manual logging, it uses real sensor data — soil moisture, temperature, light intensity, humidity — to monitor plant health automatically. The built-in Plant component combines multiple sensor readings into a single plant entity with a health status indicator.

### Home Assistant Plant Configuration

```yaml
# configuration.yaml
plant:
  monstera_living_room:
    sensors:
      moisture: sensor.soil_moisture_monstera
      temperature: sensor.living_room_temperature
      conductivity: sensor.soil_conductivity_monstera
      brightness: sensor.living_room_light
      humidity: sensor.living_room_humidity
    min_moisture: 20
    max_moisture: 60
    min_temperature: 18
    max_temperature: 30
    min_conductivity: 350
    max_conductivity: 2000
    min_brightness: 500
    max_brightness: 50000
```

### Automating Watering with ESPHome Sensors

```yaml
# ESPHome configuration for soil moisture sensor
esphome:
  name: plant-sensor-1
  platform: ESP32

sensor:
  - platform: adc
    pin: GPIO34
    name: "Soil Moisture"
    unit_of_measurement: "%"
    filters:
      - calibrate_linear:
          - 1.8 -> 100
          - 3.0 -> 0
    update_interval: 60s

  - platform: dht
    pin: GPIO15
    temperature:
      name: "Ambient Temperature"
    humidity:
      name: "Ambient Humidity"
    update_interval: 60s

# Notify when plant needs water
automation:
  - alias: "Monstera needs water"
    trigger:
      platform: numeric_state
      entity_id: plant.monstera_living_room
      attribute: moisture_status
      above: 0
    action:
      - service: notify.mobile_app_phone
        data:
          message: "🌱 Monstera needs water! Current moisture is low."
```

## Which Approach Is Right For You?

The three platforms represent different philosophies of plant care:

- **Plant-it** is for the casual plant owner who wants simple watering reminders on their phone. The mobile-first design and push notifications make it the easiest to adopt. If you have 5–20 houseplants and just want to remember when to water them, Plant-it delivers.

- **HortusFox** is for shared spaces and serious collectors. The collaborative features, detailed plant profiles, and customization options make it suitable for community gardens, office environments, or enthusiasts managing 50+ plants with detailed care requirements.

- **Home Assistant Plant Integration** is for the automation enthusiast who wants hands-off plant care. When combined with soil moisture sensors and smart irrigation valves, you can achieve fully automated watering based on real data. This is the most powerful option but requires the most setup — sensors, ESP32 microcontrollers, and Home Assistant infrastructure.

For many users, the best approach is to combine them. Use Home Assistant for sensor data and automated watering, with HortusFox as the collaborative management interface that the whole family can access.

## Sensor Hardware Selection Guide

Building a sensor-driven plant monitoring system requires selecting the right hardware for your environment. For indoor use, capacitive soil moisture sensors (v1.2 or v2.0) are preferred over resistive sensors — they do not corrode over time and provide more stable readings. A single ESP32 development board can support up to 8 analog sensors and 2 I2C sensors simultaneously.

For multi-room deployments, consider the ESP32-C3 Mini which is smaller, cheaper ($4-5), and includes Wi-Fi 6 support. Flash it with ESPHome and it will appear automatically in Home Assistant. Power options include USB-C for indoor sensors and 18650 Li-ion batteries with a small solar panel for outdoor deployments. A 2000mAh battery with a 1W solar panel provides roughly 3-4 days of runtime without sun.

Light sensors deserve special attention — the BH1750 digital light sensor ($3) provides lux measurements that directly map to plant light requirements (low: 500-2500 lux, medium: 2500-10000 lux, high: 10000+ lux). Unlike simple photoresistors, the BH1750 gives calibrated readings that work consistently across different Home Assistant instances. For outdoor monitoring, the BME280 sensor adds barometric pressure tracking, useful for predicting rain before it arrives.

When deploying sensors outdoors, protect electronics in a weatherproof enclosure with a breather vent to prevent condensation. Run sensor wires through cable glands and use silicone sealant around entry points. Soil moisture sensors should have their top edge sealed with epoxy to prevent water ingress through the sensor body itself.
## FAQ

### Do I need special sensors for Home Assistant plant monitoring?

Yes, but they are inexpensive. A basic soil moisture sensor costs $3–5, a DHT22 temperature/humidity sensor costs $5, and an ESP32 microcontroller costs $8–10. A complete single-plant monitoring setup costs under $20. For multiple plants, you can multiplex sensors or use one ESP32 per 3–4 plants.

### Can Plant-it and HortusFox integrate with real sensors?

Currently, no. Both rely on manual logging — you record when you watered or fertilized. Home Assistant is the only option that reads real sensor data and responds automatically. If you want data-driven automation, Home Assistant is the platform to choose.

### What if I have plants in different rooms?

With Home Assistant, you can deploy ESP32 sensor nodes in each room, connected via Wi-Fi. HortusFox and Plant-it work anywhere since they are accessed via the network. For outdoor plants, consider ESP32 with external antennas or LoRa-based sensors for longer range.

### How accurate are soil moisture sensors?

Consumer-grade resistive sensors provide a relative measurement (wet vs. dry) rather than absolute moisture content. They are accurate enough to trigger watering automation — "the soil is dry" is sufficient information. For scientific accuracy, capacitive sensors are better but cost more ($12–15). All sensors drift over time and should be recalibrated every 3–6 months.

### Can I track plant growth with photos?

Yes. HortusFox has built-in photo galleries for each plant. Plant-it supports photo logging in the mobile app. With Home Assistant, you can set up a camera entity (any IP camera or ESP32-CAM) to take daily photos and create timelapse videos of plant growth.

### What about outdoor garden monitoring?

For outdoor gardens, Home Assistant is the strongest option because it integrates with weather sensors, rain gauges, and irrigation controllers. See our [garden irrigation guide](../2026-06-05-self-hosted-garden-irrigation-opensprinkler-ospi-automated-guide/) for outdoor-specific setups. HortusFox and Plant-it can be used alongside these systems for manual logging and plant tracking.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Plant Care & Garden Management: Plant-it vs HortusFox vs Home Assistant Plant Integration",
  "description": "Compare Plant-it, HortusFox, and Home Assistant Plant for self-hosted plant care and garden management. Includes Docker Compose deployments, sensor integration, and automated watering guides.",
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
