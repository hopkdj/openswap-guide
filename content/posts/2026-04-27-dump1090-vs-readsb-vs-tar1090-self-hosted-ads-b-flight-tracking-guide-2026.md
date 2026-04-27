---
title: "dump1090 vs readsb vs tar1090: Self-Hosted ADS-B Flight Tracking 2026"
date: 2026-04-27
tags: ["comparison", "guide", "self-hosted", "sdr", "monitoring", "radio"]
draft: false
description: "Complete comparison of self-hosted ADS-B receiver software in 2026. Setup dump1090, readsb, and tar1090 with Docker, RTL-SDR hardware, and real-time flight tracking dashboards."
---

Every day, thousands of commercial and private aircraft broadcast their position, altitude, speed, and identification over an unencrypted radio frequency at 1090 MHz. With a $30 USB dongle and the right software, you can receive and decode these signals from your own home — building a self-hosted flight tracking station that rivals commercial services like Flightradar24.

The ADS-B (Automatic Dependent Surveillance-Broadcast) ecosystem is one of the most rewarding self-hosted projects you can run. It combines hardware hacking, radio signal processing, and real-time data visualization into a single system that lets you watch every aircraft flying overhead on your own private map.

In this guide, we compare the three most popular open-source ADS-B receiver toolchains — **dump1090**, **readsb**, and **tar1090** — with hands-on Docker deployment instructions, feature comparisons, and guidance on building the optimal self-hosted flight tracking stack.

## Why Self-Host Your ADS-B Receiver?

Commercial flight tracking services are convenient, but they come with tradeoffs that push many enthusiasts toward self-hosting:

**Complete data ownership.** Every aircraft position, flight number, altitude reading, and signal report stays on your server. You're not feeding data to a corporation that monetizes it or restricts your access.

**No subscription fees.** Premium features on commercial platforms — extended range maps, detailed aircraft databases, historical tracking — cost $10-30/month. Self-hosted alternatives give you everything for free after the initial hardware purchase.

**Share data on your terms.** You can choose to feed your decoded data to multiple aggregators (FlightAware, ADS-B Exchange, OpenSky Network) simultaneously, or keep it entirely private. Most commercial services only let you feed to their own platform.

**Learn about RF and aviation.** Running an ADS-B receiver teaches you about radio frequency reception, antenna theory, Mode-S protocols, and the global air traffic system. It's one of the most educational self-hosted projects available.

**Reliable local coverage.** Commercial services rely on a network of volunteer receivers that can go offline. Your own receiver provides consistent coverage for your local airspace regardless of what other receivers are doing.

For related projects, see our [self-hosted GPS tracking guide](../2026-04-20-dawarich-vs-owntracks-vs-traccar-self-hosted-gps-tracking-guide-2026/) for vehicle position tracking and [network monitoring with Zabbix and LibreNMS](../zabbix-vs-librenms-vs-netdata-network-monitoring-guide/) for infrastructure observability.

## Understanding the ADS-B Toolchain

Before comparing tools, it's important to understand how an ADS-B receiver system works. The typical self-hosted stack has three layers:

1. **Decoder** — Receives raw I/Q samples from the RTL-SDR dongle, demodulates the 1090 MHz signal, and extracts Mode-S messages (aircraft position, callsign, altitude, speed). Examples: dump1090, readsb.
2. **Web interface** — Serves a real-time interactive map showing aircraft positions on a browser. Examples: tar1090, built-in dump1090 map.
3. **Feeder** — Optionally forwards decoded data to external aggregators. Examples: fr24feed, PiAware, adsbexchange-feeding.

The tools we compare here serve different roles in this stack. dump1090 and readsb are decoders (with built-in basic web interfaces), while tar1090 is a web interface layer that sits on top of either decoder.

## dump1090: The Original ADS-B Decoder

**GitHub:** [antirez/dump1090](https://github.com/antirez/dump1090) — 2,863 stars, last updated February 2026

dump1090, created by Salvatore Sanfilippo (antirez, the creator of Redis), is the original and most widely known ADS-B decoder. Despite its simple name ("dump" Mode-S messages at "1090" MHz), it remains the foundation of the entire self-hosted ADS-B ecosystem.

### Features

- Real-time decoding of Mode-S and ADS-B messages from RTL-SDR hardware
- Built-in HTTP server with interactive aircraft map
- Beast-format and AVR-format output for feeding to other services
- Gain control and frequency correction settings
- Position tracking and aircraft database management
- JSON output for custom integrations

### Strengths

- **Simplicity** — Single binary, minimal dependencies, easy to compile
- **Huge community** — Thousands of tutorials, forum posts, and troubleshooting guides
- **Proven stability** — Years of production use across millions of receivers worldwide
- **Wide hardware support** — Works with RTL-SDR, BladeRF, and other SDR devices

### Limitations

- **Limited aircraft database** — Basic plane type lookup; no airline logos or detailed registries
- **Basic web interface** — Functional but dated; limited filtering and display options
- **No multi-receiver support** — Single dongle per instance
- **Slower CPU performance** — Less optimized than modern forks

### Docker Deployment

```yaml
services:
  dump1090:
    image: sdr-enthusiasts/docker-dump1090:latest
    container_name: dump1090
    restart: unless-stopped
    devices:
      - /dev/bus/usb:/dev/bus/usb
    environment:
      - TZ=America/New_York
      - DUMP1090_GAIN=49.6
      - DUMP1090_NET_BEAST_RATE=360000
    ports:
      - "8080:8080"
      - "30005:30005"
      - "30001:30001"
    volumes:
      - ./dump1090-config:/etc/dump1090
      - /var/run/dump1090:/var/run/dump1090
```

### Installation from Source

```bash
# Install build dependencies
sudo apt-get update && sudo apt-get install -y \
  build-essential libusb-1.0-0-dev librtlsdr-dev \
  pkg-config git

# Clone and build
git clone https://github.com/antirez/dump1090.git
cd dump1090
make BLADERF=no

# Run with RTL-SDR dongle
./dump1090 --interactive --net --gain 49.6
```

## readsb: The Modern ADS-B Decoder

**GitHub:** [wiedehopf/readsb](https://github.com/wiedehopf/readsb) — 595 stars, last updated April 2026

readsb is a modern fork of dump1090 that has become the decoder of choice for experienced ADS-B enthusiasts. The name stands for "Reader of Mode-S/ADSB" — a direct evolution from the original tool with significant improvements.

### Features

- All dump1090 capabilities with enhanced decoding algorithms
- Improved weak-signal detection and range performance
- Better CPU efficiency with optimized DSP processing
- Built-in aircraft database with more detailed type information
- Support for multiple RTL-SDR devices simultaneously
- Enhanced statistics and performance metrics
- Native support for the tar1090 web interface

### Strengths

- **Superior decoding performance** — Better range and accuracy, especially for weak signals
- **Active development** — Frequent updates with algorithmic improvements
- **tar1090 integration** — Designed to work seamlessly with the modern web interface
- **Multi-receiver support** — Can combine data from multiple dongles
- **Built-in statistics** — Detailed performance dashboards out of the box

### Limitations

- **Slightly more complex** — More configuration options can overwhelm beginners
- **Smaller community** — Fewer tutorials compared to dump1090
- **ARM-focused** — Best performance on Raspberry Pi; x86 optimization varies

### Docker Deployment

```yaml
services:
  readsb:
    image: sdr-enthusiasts/docker-readsb-protobuf:latest
    container_name: readsb
    restart: unless-stopped
    devices:
      - /dev/bus/usb:/dev/bus/usb
    environment:
      - TZ=America/New_York
      - READSB_DEVICE_TYPE=rtlsdr
      - READSB_GAIN=autogain
      - READSB_LAT=40.7128
      - READSB_LON=-74.0060
      - READSB_ALT=10m
    ports:
      - "8080:8080"
      - "30005:30005"
      - "30001:30001"
      - "30006:30006"
    volumes:
      - ./readsb-data:/var/lib/readsb
      - /var/run/readsb:/var/run/readsb
    tmpfs:
      - /tmp:exec
```

### Key Configuration Parameters

| Parameter | Description | Recommended Value |
|-----------|-------------|-------------------|
| `READSB_GAIN` | RTL-SDR gain setting | `autogain` (recommended) or `49.6` |
| `READSB_LAT` | Receiver latitude | Your actual GPS latitude |
| `READSB_LON` | Receiver longitude | Your actual GPS longitude |
| `READSB_ALT` | Receiver altitude above sea level | e.g., `50m` or `150ft` |
| `READSB_DEVICE_TYPE` | SDR hardware type | `rtlsdr`, `bladerf`, or `modesbeast` |

## tar1090: The Modern Web Interface

**GitHub:** [wiedehopf/tar1090](https://github.com/wiedehopf/tar1090) — 1,763 stars, last updated April 2026

tar1090 is not a decoder — it's a web interface layer that sits on top of dump1090 or readsb, replacing their built-in maps with a significantly improved user experience. Think of it as the "theme" for your ADS-B data.

### Features

- Beautiful, responsive aircraft map with smooth panning and zooming
- Advanced filtering by altitude, speed, aircraft type, and airline
- Real-time aircraft details panel with comprehensive data
- Historical trajectory trails showing flight paths
- Dark mode and customizable map styles
- Aircraft silhouette rendering for identified types
- Range rings and custom marker support
- Statistics dashboard with range plots and message rates

### Strengths

- **Best-in-class web UI** — Vastly superior to built-in decoder interfaces
- **Works with any decoder** — Compatible with dump1090, dump1090-fa, and readsb
- **Performance optimized** — Handles thousands of simultaneous aircraft smoothly
- **Mobile friendly** — Responsive design works well on phones and tablets
- **Active development** — Weekly updates with new features and fixes

### Limitations

- **Not a decoder** — Requires a separate decoder instance (dump1090 or readsb)
- **Resource usage** — Slightly higher memory footprint than basic web interfaces
- **Configuration complexity** — Requires connecting to a running decoder's Beast output

### Docker Deployment (with readsb)

```yaml
services:
  readsb:
    image: sdr-enthusiasts/docker-readsb-protobuf:latest
    container_name: readsb
    restart: unless-stopped
    devices:
      - /dev/bus/usb:/dev/bus/usb
    environment:
      - TZ=America/New_York
      - READSB_DEVICE_TYPE=rtlsdr
      - READSB_GAIN=autogain
      - READSB_LAT=40.7128
      - READSB_LON=-74.0060
    ports:
      - "30005:30005"
    volumes:
      - ./readsb-data:/var/lib/readsb

  tar1090:
    image: sdr-enthusiasts/docker-tar1090:latest
    container_name: tar1090
    restart: unless-stopped
    depends_on:
      - readsb
    environment:
      - TZ=America/New_York
      - TAR1090_HOST=readsb
      - TAR1090_PORT=30005
      - TAR1090_BEASTHOST=readsb
      - TAR1090_LAT=40.7128
      - TAR1090_LON=-74.0060
    ports:
      - "8080:8080"
    volumes:
      - ./tar1090-config:/etc/tar1090
```

## Feature Comparison

| Feature | dump1090 | readsb | tar1090 |
|---------|----------|--------|---------|
| **Role** | Decoder | Decoder | Web Interface |
| **Stars** | 2,863 | 595 | 1,763 |
| **Last Updated** | Feb 2026 | Apr 2026 | Apr 2026 |
| **RTL-SDR Support** | Yes | Yes | N/A (needs decoder) |
| **BladeRF Support** | No | Yes | N/A |
| **Multi-Receiver** | No | Yes | N/A |
| **Built-in Map** | Basic | Basic | Advanced |
| **Dark Mode** | No | No | Yes |
| **Aircraft Trails** | No | No | Yes |
| **Filtering** | Basic | Basic | Advanced |
| **Mobile Responsive** | Limited | Limited | Yes |
| **Statistics Dashboard** | Basic | Good | Excellent |
| **Docker Image** | Available | Available | Available |
| **CPU Efficiency** | Good | Excellent | Low (UI only) |

## Recommended Stacks

### Beginner Stack: dump1090 Only

```yaml
services:
  dump1090:
    image: sdr-enthusiasts/docker-dump1090:latest
    container_name: dump1090
    restart: unless-stopped
    devices:
      - /dev/bus/usb:/dev/bus/usb
    environment:
      - TZ=America/New_York
      - DUMP1090_GAIN=autogain
      - DUMP1090_LAT=40.7128
      - DUMP1090_LON=-74.0060
    ports:
      - "8080:8080"
```

Access the built-in map at `http://your-server:8080`. This is the simplest setup — one container, minimal configuration, and you're tracking flights within minutes.

### Enthusiast Stack: readsb + tar1090

This is the recommended configuration for most users. readsb provides the best decoding performance, and tar1090 delivers a polished web interface. The Docker Compose file above shows the complete setup with both services.

### Advanced Stack: readsb + tar1090 + graphs1090 + Feeders

```yaml
services:
  readsb:
    image: sdr-enthusiasts/docker-readsb-protobuf:latest
    container_name: readsb
    restart: unless-stopped
    devices:
      - /dev/bus/usb:/dev/bus/usb
    environment:
      - TZ=America/New_York
      - READSB_DEVICE_TYPE=rtlsdr
      - READSB_GAIN=autogain
      - READSB_LAT=40.7128
      - READSB_LON=-74.0060
    ports:
      - "30005:30005"
      - "30001:30001"
    volumes:
      - ./readsb-data:/var/lib/readsb

  tar1090:
    image: sdr-enthusiasts/docker-tar1090:latest
    container_name: tar1090
    restart: unless-stopped
    depends_on:
      - readsb
    environment:
      - TAR1090_BEASTHOST=readsb
      - TAR1090_LAT=40.7128
      - TAR1090_LON=-74.0060
    ports:
      - "8080:8080"

  graphs1090:
    image: sdr-enthusiasts/docker-graphs1090:latest
    container_name: graphs1090
    restart: unless-stopped
    depends_on:
      - readsb
    environment:
      - GRAPH1090_HOST=readsb
    ports:
      - "8081:80"

  fr24feed:
    image: sdr-enthusiasts/docker-fr24feed:latest
    container_name: fr24feed
    restart: unless-stopped
    depends_on:
      - readsb
    environment:
      - FR24KEY=your-fr24-sharing-key
      - RECEIVER=readsb
      - HOST=readsb
      - PORT=30005
```

This production-grade stack includes:
- **readsb** for optimal decoding
- **tar1090** for the flight map UI
- **graphs1090** for receiver performance monitoring (range plots, message rates, CPU usage)
- **fr24feed** for sharing data with Flightradar24

## Hardware Requirements

### Essential Hardware

| Component | Minimum | Recommended | Cost |
|-----------|---------|-------------|------|
| **RTL-SDR Dongle** | RTL2832U + R820T2 | RTL-SDR Blog V4 | $25-35 |
| **Antenna** | Stock dipole | 1090 MHz tuned antenna | $15-40 |
| **Computer** | Raspberry Pi 3 | Raspberry Pi 4/5 or mini PC | $35-150 |
| **Cable** | Included coax | LMR-400 low-loss coax | $10-30 |
| **Mount** | Window mount | Outdoor mast mount | $10-50 |

### Antenna Placement Tips

- **Height matters** — Mount as high as possible. Every meter of elevation increases your range significantly.
- **Clear line of sight** — Avoid obstructions between your antenna and the sky. Buildings and trees block 1090 MHz signals.
- **Vertical polarization** — ADS-B signals are vertically polarized. Keep your antenna vertical.
- **Outdoor placement** — Indoor reception works for nearby aircraft (50-100 km range). Outdoor placement extends this to 200-400+ km.
- **Coax length** — Use the shortest coax cable possible. Signal loss at 1090 MHz is significant over long cable runs.

## FAQ

### What is ADS-B and how does it work?

ADS-B (Automatic Dependent Surveillance-Broadcast) is a surveillance technology used by aircraft to broadcast their position, altitude, velocity, and identification. Aircraft transmit these messages on 1090 MHz using Mode-S transponders. Any receiver tuned to this frequency within range can decode the messages and display the aircraft on a map. The system works globally — any aircraft equipped with an ADS-B transponder (required in most airspace since 2020) broadcasts continuously.

### Do I need special hardware to run an ADS-B receiver?

Yes, you need an RTL-SDR (Software Defined Radio) USB dongle that can receive signals at 1090 MHz. The RTL-SDR Blog V4 dongle ($30) is the most popular choice. You also need a computer to run the decoder software — a Raspberry Pi 4 is ideal, but any Linux machine with USB support works. An outdoor antenna significantly improves reception range but isn't required to get started.

### What's the difference between dump1090 and readsb?

readsb is a modern fork of dump1090 with improved decoding algorithms, better weak-signal detection, multi-receiver support, and enhanced statistics. Both decode the same ADS-B signals, but readsb generally provides better range and accuracy. dump1090 has a larger community and more tutorials, making it easier for beginners. For new installations, readsb is the recommended decoder.

### Can I use tar1090 without readsb or dump1090?

No. tar1090 is a web interface, not a decoder. It needs a running decoder instance (dump1090, dump1090-fa, or readsb) to provide it with aircraft data via Beast-format output on port 30005. Think of the decoder as the "engine" that processes radio signals, and tar1090 as the "dashboard" that displays the results.

### How far can my ADS-B receiver detect aircraft?

Range depends primarily on antenna height and placement. A basic indoor setup typically reaches 50-150 km. An outdoor antenna at 10 meters height can reach 200-300 km. At 30+ meters with a tuned antenna and low-loss coax, ranges of 400-500+ km are achievable. Geography matters too — coastal or elevated locations with clear views of the horizon get the best range.

### Is it legal to receive and decode ADS-B signals?

Yes, in most countries. ADS-B signals are broadcast unencrypted on a public frequency (1090 MHz) and are intended to be received by anyone. The FAA, EASA, and other aviation authorities explicitly encourage public reception of ADS-B data for flight tracking and safety monitoring. However, check your local regulations — some countries have restrictions on radio reception equipment.

### Can I share my ADS-B data with flight tracking services?

Absolutely. Most self-hosted receivers feed data to multiple services simultaneously:
- **FlightAware (PiAware)** — Largest receiver network, provides free enterprise account
- **ADS-B Exchange** — Unfiltered data, no military filtering
- **OpenSky Network** — Academic/research focused, open data
- **Flightradar24 (fr24feed)** — Popular consumer flight tracker
- **RadarBox** — Another commercial aggregator

You decide which services to feed. Your self-hosted setup remains independent regardless.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "dump1090 vs readsb vs tar1090: Self-Hosted ADS-B Flight Tracking 2026",
  "description": "Complete comparison of self-hosted ADS-B receiver software in 2026. Setup dump1090, readsb, and tar1090 with Docker, RTL-SDR hardware, and real-time flight tracking dashboards.",
  "datePublished": "2026-04-27",
  "dateModified": "2026-04-27",
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
