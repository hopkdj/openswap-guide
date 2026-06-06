---
title: "Self-Hosted E-Ink Dashboard Platforms: Inkycal vs TRMNL vs PaperPi — Build Beautiful Low-Power Information Displays"
date: "2026-06-06"
tags: ["self-hosted", "e-ink", "epaper", "dashboard", "raspberry-pi", "iot", "home-automation", "low-power"]
draft: false
---

## Introduction

E-ink displays offer something no LCD or OLED screen can match: a paper-like reading experience that uses zero power when static and remains perfectly readable in direct sunlight. For self-hosted enthusiasts, e-ink dashboards represent the ideal intersection of form and function — a beautiful, always-on information display that sips milliwatts of power and can run for weeks on a small battery.

Whether you want a wall-mounted calendar, a weather station display, a todo list that stares at you until completed, or a data dashboard showing server metrics, open-source e-ink dashboard platforms have matured to the point where setting one up is a weekend project rather than a months-long engineering effort.

In this guide, we compare three leading open-source e-ink dashboard platforms: **Inkycal** (1,458 stars), **TRMNL** (1,052 stars), and **PaperPi** (202 stars). Each takes a different approach to the same fundamental challenge: making e-paper displays useful, beautiful, and easy to configure.

## Comparison Table

| Feature | Inkycal | TRMNL | PaperPi |
|---------|---------|-------|---------|
| Language | Python 3 | C++ (ESP32 firmware) | Python 3 |
| Stars | 1,458 | 1,052 | 202 |
| Architecture | Modular plugin system | Firmware + cloud API | Plugin-based display loop |
| Display Support | Waveshare, Pimoroni, PaPiRus | TRMNL hardware (custom) | Waveshare, Pimoroni |
| Configuration | Web UI + config file | Web dashboard (cloud) | YAML config file |
| Plugin Count | 20+ built-in modules | API-driven (custom) | 15+ plugins |
| Calendar | Google Calendar, iCal, CalDAV | Via API integration | iCal, Google Calendar |
| Weather | OpenWeatherMap, custom API | Via API | OpenWeatherMap |
| To-Do Support | Todoist, custom | Via API | Built-in list |
| Docker Support | Yes (community) | No (ESP32 device) | Manual install |
| Power Usage | Pi Zero: ~1.5W | ESP32: ~0.3W | Pi Zero: ~1.5W |
| Best For | Pi-based modular dashboards | Dedicated TRMNL hardware | Simple Pi-based displays |

## Inkycal: The Modular Powerhouse

[Inkycal](https://github.com/aceisace/Inkycal) is the most feature-complete open-source e-ink dashboard platform available. Written in Python 3 and designed around a modular plugin architecture, Inkycal turns any compatible e-ink display into a customizable information hub. The project's tagline — "Create awesome e-paper dashboards within minutes" — is not an exaggeration.

Inkycal's strength lies in its plugin ecosystem. Out of the box, it supports calendar displays (Google Calendar, iCal, CalDAV), weather forecasts, RSS feeds, to-do lists (Todoist integration), slideshows, and even custom modules you can write yourself. The web-based configuration interface means you never need to edit a config file manually — everything from display rotation to refresh intervals can be adjusted through a browser.

**Installation on Raspberry Pi:**

```bash
# Enable SPI interface
sudo raspi-config nonint do_spi 0

# Install Inkycal
git clone https://github.com/aceisace/Inkycal.git
cd Inkycal
pip3 install -r requirements.txt

# Run the setup wizard
python3 inkycal.py --setup

# Start the dashboard
python3 inkycal.py
```

**Docker Compose deployment (community-maintained):**

```yaml
version: "3.8"
services:
  inkycal:
    image: aceisace/inkycal:latest
    container_name: inkycal
    restart: unless-stopped
    privileged: true  # Required for SPI access
    volumes:
      - ./inkycal-config:/root/Inkycal
    devices:
      - /dev/spidev0.0:/dev/spidev0.0
    environment:
      - TZ=America/Chicago
      - DISPLAY_WIDTH=800
      - DISPLAY_HEIGHT=480
```

Inkycal supports virtually every Waveshare e-ink display, plus Pimoroni Inky pHAT/Impression and PaPiRus screens. The modular design means you can start with a calendar module and add weather, news, and custom data sources as you need them.

## TRMNL: The Polished Hardware Solution

[TRMNL](https://github.com/usetrmnl/firmware) takes a fundamentally different approach from Inkycal. Rather than a software platform you install on your own hardware, TRMNL provides an open-source firmware for a purpose-built ESP32-based e-ink device with a companion web dashboard. The firmware is fully open-source (GPLv3), and the web dashboard handles content delivery through a REST API.

TRMNL's key innovation is its content delivery architecture. Content is composed on the web dashboard (which you can self-host) and pushed to the device over WiFi. This separation of concerns — a powerful web server handles rendering, while the low-power ESP32 device handles display — means the device itself can run for months on a small battery.

**Self-hosting the TRMNL firmware:**

```bash
# Clone the firmware repository
git clone https://github.com/usetrmnl/firmware.git
cd firmware

# Build with PlatformIO
pio run -e trmnl_v4

# Flash to ESP32
pio run -e trmnl_v4 -t upload
```

The TRMNL web dashboard is a Next.js application that you can deploy on any server or VPS. Content is rendered server-side and pushed to devices as bitmap images, which means the display quality is limited only by your server's rendering capabilities — no resource constraints on the device side.

## PaperPi: The Minimalist Choice

[PaperPi](https://github.com/txoof/PaperPi) follows the Unix philosophy: do one thing well. It's a Python-based display loop that rotates through multiple "plugins" (display screens), each rendering a different type of information. PaperPi is designed for the person who wants a dashboard that "just works" without a web UI, without Docker, and without complex configuration.

PaperPi's plugin library includes clock faces, weather displays, RSS readers, quote rotators, system monitor panels, and cryptocurrency tickers. Each plugin is a standalone Python script that renders to the e-ink framebuffer, and PaperPi handles the rotation timing and screen refresh logic.

**Installation:**

```bash
git clone https://github.com/txoof/PaperPi.git
cd PaperPi
sudo ./install.sh

# Edit plugins in config
nano /etc/paperpi/config.yaml

# Start the display loop
paperpi
```

The configuration is a single YAML file where you list which plugins to display and in what order. PaperPi's minimalism means it uses very few resources — it can run comfortably on a Pi Zero alongside other services.

## Why Self-Host Your Dashboard Displays?

Commercial smart displays like the Amazon Echo Show or Google Nest Hub are fundamentally surveillance devices. They're designed to collect data about your habits, serve advertisements, and lock you into proprietary ecosystems. An e-ink dashboard running open-source software eliminates all of these concerns — no telemetry, no ads, no cloud dependency.

E-ink displays also consume dramatically less power than LCDs. A typical 7.5-inch e-ink panel draws zero power when displaying a static image and only consumes energy during the brief moment when the screen refreshes. Running on a Raspberry Pi Zero, an Inkycal or PaperPi dashboard uses about 1.5 watts on average — less than a nightlight. TRMNL's ESP32-based hardware uses even less: about 0.3 watts, making battery operation practical.

For related self-hosted display projects, see our guides on [smart mirror platforms](../2026-06-05-self-hosted-smart-mirror-digital-display-platforms-guide/) and [digital signage solutions](../anthias-vs-xibo-vs-screenlite-self-hosted-digital-signage-guide-2026/). If you're interested in the broader self-hosted dashboard ecosystem, our [startpage dashboard comparison](../2026-04-26-homer-vs-heimdall-vs-flame-self-hosted-startpage-dashboard-guide-2026/) covers browser-based alternatives.

## Choosing the Right Platform

Your choice depends on your hardware and how much configuration you want:

- **Choose Inkycal** if you want maximum flexibility and a polished user experience. The web-based configuration, 20+ modules, and broad hardware support make it the best all-around choice for most users. It's ideal for wall-mounted family calendars, weather stations, and multi-function dashboards.

- **Choose TRMNL** if you want ultra-low power consumption and are willing to work with dedicated hardware. The ESP32-based architecture means weeks of battery life, and the server-side rendering approach delivers high-quality output. It's best for battery-powered, always-on displays in locations without easy access to power outlets.

- **Choose PaperPi** if you value simplicity and don't want to deal with web UIs or Docker. PaperPi is the lightest option and runs well on older Raspberry Pi models including the Pi Zero. It's ideal for a simple clock, weather, and system monitor display that you set up once and forget.

## Display Hardware Guide

All three platforms support a wide range of e-ink displays. The most commonly used panels are from Waveshare, which offers sizes from 2.13 inches (250x122) to 12.48 inches (1304x984). For a dashboard application, the sweet spot is 7.5 inches (800x480) or 9.7 inches (1200x825).

Key hardware considerations:
- **Partial refresh support**: Newer Waveshare panels support partial refresh, which allows updating specific areas without a full-screen flash. This is essential for clock displays that update every minute.
- **Color vs monochrome**: Color e-ink panels (using Advanced Color ePaper, or ACeP) exist but have much slower refresh rates (15-30 seconds vs 1-3 seconds). Stick with monochrome if you need fast updates.
- **SPI vs parallel interface**: SPI (Serial Peripheral Interface) panels connect to the Pi's GPIO pins and are the most common. Parallel interface panels are faster but use more GPIO pins.

## FAQ

### How long do e-ink displays last?

E-ink displays are rated for millions of refresh cycles and don't suffer from burn-in like OLED screens. The displays themselves can last 10+ years with normal use. The limiting factor is usually the Raspberry Pi or ESP32 board, not the display panel. E-ink panels from Waveshare and Pimoroni typically carry 1-2 year warranties and are known to work reliably for years.

### Can I use the same e-ink display with different software?

Yes. E-ink displays use standard interfaces (SPI and I2C), and all three platforms support Waveshare and Pimoroni displays. You can switch between Inkycal, PaperPi, and TRMNL firmware on the same hardware. The display itself is independent of the software stack — just make sure your SPI interface is enabled and the pin connections match.

### Does e-ink work in cold or hot environments?

E-ink displays have a wider operating temperature range than LCDs but are not extreme-environment rated. Most consumer panels operate from 0°C to 50°C (32°F to 122°F). Below freezing, refresh speed slows noticeably. Above 50°C, the display fluid can degrade. For outdoor installations, a weatherproof enclosure with some passive temperature management is recommended.

### How do I add custom data sources to Inkycal?

Inkycal's plugin system is designed for extensibility. Each plugin is a Python class that inherits from a base module. You can create custom modules by following the plugin template in the Inkycal documentation. The framework handles display positioning, refresh scheduling, and error recovery — you only need to write the data fetching and rendering logic. Community-contributed plugins include cryptocurrency tickers, server health monitors, and public transit arrival boards.

### Can TRMNL be used without their cloud dashboard?

Yes. The TRMNL firmware is fully open-source, and the API protocol is documented. You can build your own backend server that generates bitmap images and serves them to TRMNL devices. Several community projects have created self-hosted alternatives to the official TRMNL dashboard using Flask, FastAPI, or Go. The device itself is a standard ESP32 with a connected e-ink panel.

### Why e-ink instead of a tablet or old phone?

Three reasons: readability (e-ink is perfectly readable in direct sunlight), power consumption (e-ink draws zero power between updates), and lack of distractions (e-ink can't play videos, show notifications, or demand your attention). A repurposed tablet might be cheaper upfront, but it will consume 10-20x more power and require a constant power connection. E-ink dashboards are set-and-forget devices that enhance your space without demanding attention.

---

**💰 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — it's the world's largest prediction market platform, where you can bet on everything from election results to technology regulation timelines. Unlike gambling, this is a real information market: the more you know, the better your odds. I've made good returns predicting technology-related event outcomes. Sign up with my referral link: [Polymarket.com](https://polymarket.com/?r=fc8a0)**

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted E-Ink Dashboard Platforms: Inkycal vs TRMNL vs PaperPi — Build Beautiful Low-Power Information Displays",
  "description": "Comprehensive comparison of open-source e-ink dashboard platforms: Inkycal (Python/modular), TRMNL (ESP32 firmware), and PaperPi (Python/minimalist). Includes installation guides, Docker Compose examples, and hardware recommendations for Raspberry Pi and ESP32 displays.",
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
