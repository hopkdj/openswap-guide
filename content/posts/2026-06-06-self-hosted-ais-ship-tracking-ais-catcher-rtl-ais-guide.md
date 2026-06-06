---
title: "Self-Hosted AIS Ship Tracking: AIS-catcher vs rtl-ais vs OpenCPN — Real-Time Vessel Monitoring with RTL-SDR"
date: "2026-06-06"
tags: ["ais", "sdr", "rtl-sdr", "ship-tracking", "marine", "raspberry-pi", "radio", "self-hosted"]
draft: false
---

## Introduction

The Automatic Identification System (AIS) is a VHF-based tracking system used by ships and vessel traffic services worldwide. Every commercial vessel over 300 gross tons broadcasts its position, speed, heading, and identity via AIS transponders — and with a $25 RTL-SDR dongle and open source software, you can receive and visualize this data from your own server.

AIS operates on two VHF marine channels (161.975 MHz and 162.025 MHz), and the signals are easily receivable within 20-50 nautical miles of coastal areas, busy ports, or inland waterways. By setting up a self-hosted AIS receiver, you can build a real-time map of all vessel traffic in your area — entirely independent of commercial services like MarineTraffic or VesselFinder. This guide compares three open source tools for decoding and visualizing AIS signals: **AIS-catcher**, **rtl-ais**, and the **OpenCPN** navigation suite.

## How AIS Signal Decoding Works

An AIS signal is a GMSK (Gaussian Minimum Shift Keying) modulated transmission at 9600 bps over standard VHF frequencies. The decoding pipeline involves three stages:

1. **Signal capture**: An RTL-SDR dongle tuned to 162 MHz captures raw I/Q samples from the VHF band
2. **Demodulation**: Software demodulates the GMSK signal into a bitstream containing NMEA-format AIS messages
3. **Message parsing**: The bitstream is parsed into structured AIS data (MMSI, position, speed, course, vessel name, destination)

Each tool in our comparison handles these stages differently — some are optimized for headless server operation, others for interactive navigation. The right choice depends on whether you want a passive monitoring station on a Raspberry Pi or an interactive chart plotter.

## Tool Comparison

| Feature | AIS-catcher | rtl-ais | OpenCPN |
|---------|------------|---------|---------|
| **Language** | C++ | C | C++ |
| **GitHub Stars** | 745+ | 307+ | N/A (standalone app) |
| **Web UI** | Built-in (port 8080) | None (CLI only) | Full chart plotter GUI |
| **Docker Support** | Yes (Dockerfile) | Manual compile | Manual install |
| **Output Format** | NMEA, JSON, WebSocket | NMEA to stdout | NMEA 0183 over TCP/UDP |
| **Resource Usage** | ~50MB RAM | ~20MB RAM | ~200MB RAM |
| **Multiple SDRs** | Yes | No | Via plugin |
| **Headless Operation** | Excellent | Excellent | Requires X11/Wayland |
| **Map Integration** | Built-in Leaflet map | None | Full ENC/RNC chart support |

### AIS-catcher: The All-in-One Solution

AIS-catcher (`jvde-github/AIS-catcher`, 745+ stars) is the most feature-complete open source AIS receiver available. Written in C++ for performance, it supports nearly every SDR hardware platform — RTL-SDR, Airspy, HackRF, SDRplay, and SoapySDR-compatible devices.

Its standout feature is the built-in web server and map interface. Once running, AIS-catcher serves a real-time vessel map on port 8080 showing all received ships with their positions, headings, and metadata. It also exports data via WebSocket, JSON, and NMEA for integration with external tools.

```bash
# Install AIS-catcher via Docker
docker run -d \
  --name ais-catcher \
  --device=/dev/bus/usb \
  -p 8080:8080 \
  -p 10110:10110 \
  ghcr.io/jvde-github/ais-catcher:latest
```

```yaml
# docker-compose.yml for AIS-catcher + Prometheus metrics
version: '3.8'
services:
  ais-catcher:
    image: ghcr.io/jvde-github/ais-catcher:latest
    container_name: ais-catcher
    devices:
      - /dev/bus/usb:/dev/bus/usb
    ports:
      - "8080:8080"
      - "10110:10110"
    restart: unless-stopped
    environment:
      - TZ=UTC
```

AIS-catcher also supports multiple SDR dongles simultaneously for wider frequency coverage, and can output directly to aggregation services like AISHub and MarineTraffic.

### rtl-ais: The Lightweight Decoder

rtl-ais (`dgiardini/rtl-ais`, 307+ stars) takes a minimalist approach. It's a pure C decoder that takes raw I/Q samples from an RTL-SDR dongle and outputs parsed NMEA sentences to stdout. It doesn't include a web UI, database, or map — it does one thing and does it well.

```bash
# Build and run rtl-ais
git clone https://github.com/dgiardini/rtl-ais.git
cd rtl-ais
make
./rtl-ais -p 0 -P 0
```

rtl-ais is ideal as a component in a larger pipeline. You can pipe its NMEA output to tools like `gpsd`, `kplex` (NMEA multiplexer), or a custom InfluxDB collector:

```bash
# Pipe rtl-ais output to a file for later processing
./rtl-ais -p 0 -P 0 > /var/log/ais/nmea.log

# Forward to a TCP listener for OpenCPN
./rtl-ais -p 0 -P 0 | nc -l 10110
```

### OpenCPN: Full Navigation Suite

OpenCPN is a mature, full-featured chart plotter and navigation application. While it's primarily a GUI application for interactive use, it can run in headless mode as an AIS data consumer and relay. OpenCPN reads NMEA data from AIS receivers (including AIS-catcher and rtl-ais) and displays vessels on official nautical charts (ENC and RNC formats).

```bash
# Install OpenCPN on Debian/Ubuntu
sudo apt-get install opencpn opencpn-data
```

OpenCPN's strength is its chart integration. Unlike AIS-catcher's generic map, OpenCPN shows vessels on real navigational charts with depth soundings, buoy positions, and maritime boundaries — making it the choice for actual navigation rather than just monitoring.

## Deployment Architecture

A complete self-hosted AIS station typically follows this pipeline:

```
RTL-SDR Dongle → AIS-catcher (decode) → Web UI (port 8080)
                                      → NMEA Output (port 10110)
                                         ├── OpenCPN (chart display)
                                         ├── InfluxDB (historical storage)
                                         └── AISHub (community sharing)
```

For a headless Raspberry Pi deployment, AIS-catcher alone is sufficient — connect an RTL-SDR dongle, start the Docker container, and access the web map at `http://raspberrypi:8080`. For advanced users, add OpenCPN via VNC or X forwarding for full chartplotter capabilities.

## Why Self-Host Your AIS Receiver?

Commercial ship tracking services like MarineTraffic and VesselFinder offer free tiers with significant limitations — delayed data (up to 60 minutes), restricted API access, and no historical storage. Running your own AIS receiver eliminates these constraints entirely.

**Data ownership**: Your vessel traffic data stays on your hardware. No third party can track which ships you're monitoring or throttle your access. Commercial services aggregate data from volunteer stations and resell it — self-hosting lets you be the data source rather than the product.

**Real-time latency**: AIS-catcher decodes and displays vessels within 1-2 seconds of signal reception. Commercial APIs often introduce 5-60 minute delays on free tiers. If you're monitoring harbor traffic, ferry schedules, or ship arrivals, this real-time gap matters.

**Coverage in underserved areas**: By running your own station and sharing data with community networks like AISHub, you help fill coverage gaps in areas where commercial services have no contributing stations. Your receiver directly improves the global AIS dataset.

For readers interested in related radio monitoring topics, see our guide on [ADS-B flight tracking with dump1090](../2026-04-27-dump1090-vs-readsb-vs-tar1090-self-hosted-ads-b-flight-tracking-guide-2026/) for aircraft monitoring, and our [SDR receiver comparison](../2026-05-13-self-hosted-sdr-receiver-openwebrx-sdr-server-sdrangel-guide/) for general-purpose software-defined radio servers. If marine navigation is your focus, check our [marine navigation platforms guide](../2026-06-05-self-hosted-marine-navigation-opencpn-signalk-avnav-guide/).

## Antenna Selection and Placement for AIS

The quality of your AIS reception depends heavily on antenna choice and placement. VHF marine frequencies (156-163 MHz) require line-of-sight propagation, meaning antenna height is the single most important factor in extending range.

**Antenna types ranked by performance:**

- **Discone antenna** (25-1300 MHz): Wideband, decent AIS performance with 2-3 dBi gain. Good if you also monitor other frequencies, but not optimized for 162 MHz specifically.
- **Tuned VHF marine antenna** (156-163 MHz): 3-6 dBi gain, purpose-built for the marine band. The best option for dedicated AIS monitoring, available as both base station and mobile whip antennas for $30-80.
- **DIY quarter-wave ground plane**: Built from an SO-239 connector and 4 copper radials at 46 cm each, this provides ~2 dBi gain at near-zero cost. Excellent starter antenna.

For permanent installations, mount the antenna as high as possible with low-loss coax (RG-213 or LMR-400). Every 3 meters of additional height roughly doubles your radio horizon range. Avoid shared masts with transmitting antennas — the strong nearby RF can desensitize your RTL-SDR frontend.


## FAQ

### Do I need a special antenna for AIS reception?

AIS signals are on VHF marine band (162 MHz), so a standard VHF marine antenna tuned to 156-163 MHz works best. However, a basic RTL-SDR telescopic antenna extended to ~46 cm (quarter-wave at 162 MHz) will pick up ships within 10-20 km. For best results, mount the antenna outdoors with a clear line of sight to the water.

### Is it legal to receive AIS signals?

Yes. AIS transmissions are unencrypted public broadcasts on internationally designated maritime VHF frequencies. Receiving them is legal in virtually all countries, similar to listening to FM radio or receiving ADS-B aircraft signals. Some countries restrict the use of radio receivers in certain contexts, but passive reception of AIS for personal use is universally permitted.

### How many ships can I expect to see?

In a busy port area like Rotterdam, Singapore, or Los Angeles, you might see 200-500 vessels simultaneously. In a coastal area 20 km from a major shipping lane, expect 50-150 vessels. Inland river areas near commercial waterways might show 10-30 vessels. The range depends on antenna height and local topography.

### Can I share my AIS data with others?

Yes, and many operators do. AIS-catcher supports forwarding to AISHub, MarineTraffic, and VesselFinder as a contributing station. In return, some services offer free premium access to station operators. You can also set up a public-facing web page from AIS-catcher's built-in web server for local community access.

### What hardware do I need to get started?

The minimum setup is a Raspberry Pi 4 (or any Linux system), an RTL-SDR Blog V3 dongle (~$25), and a basic VHF antenna. Total cost: under $75. For a production station, add a weatherproof enclosure, a tuned VHF marine antenna ($30-60), and a PoE hat for remote deployment.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted AIS Ship Tracking: AIS-catcher vs rtl-ais vs OpenCPN — Real-Time Vessel Monitoring with RTL-SDR",
  "description": "Comprehensive guide to setting up a self-hosted AIS ship tracking station using RTL-SDR. Compare AIS-catcher, rtl-ais, and OpenCPN for real-time vessel monitoring, with Docker Compose configs, deployment architecture, and FAQ.",
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
