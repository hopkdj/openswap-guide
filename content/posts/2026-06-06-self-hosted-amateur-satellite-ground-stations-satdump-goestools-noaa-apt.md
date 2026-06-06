---
title: "Self-Hosted Amateur Satellite Ground Stations: SatDump vs goestools vs noaa-apt Receiver Guide"
date: "2026-06-06"
tags: ["satellite", "sdr", "radio", "weather-satellite", "noaa", "goes", "meteor", "signal-processing", "earth-observation"]
draft: false
---

## Introduction

Amateur satellite reception is one of the most rewarding niches in the software-defined radio (SDR) hobby. With a $30 RTL-SDR dongle and a simple antenna, you can receive real-time weather imagery directly from NOAA, Meteor, and GOES satellites orbiting hundreds of kilometers above Earth. The challenge isn't the hardware — it's the software that demodulates, decodes, and renders the raw radio signals into beautiful Earth images.

Three open-source tools dominate the amateur satellite decoding landscape: **SatDump**, **goestools**, and **noaa-apt**. Each approaches the problem differently — from SatDump's kitchen-sink "decode everything" philosophy to goestools' laser focus on GOES geostationary satellites, to noaa-apt's minimalist single-purpose design.

This guide compares all three tools across architecture, supported satellites, image quality, resource usage, and deployment complexity, with working Docker Compose configurations for each.

## Comparison Table

| Feature | SatDump | goestools | noaa-apt |
|---------|---------|-----------|----------|
| **GitHub Stars** | 1,997 | 419 | 655 |
| **Language** | C++ | C++ | Rust |
| **Last Updated** | June 2026 | Sept 2024 | Feb 2024 |
| **Supported Satellites** | 90+ (NOAA, Meteor, GOES, FengYun, MetOp, etc.) | GOES (16, 17, 18) | NOAA APT (15, 18, 19) |
| **Decoding Modes** | APT, LRPT, HRPT, HRIT, LRIT, DSB | HRIT, EMWIN, GRB | APT only |
| **Image Output** | RGB composites, projections, overlays | False-color, IR, visible | Raw APT, enhancements |
| **Web UI** | Yes (built-in viewer) | No (CLI + file output) | No (CLI + file output) |
| **Docker Support** | Official docker-compose.yml | Community Dockerfiles | Manual Dockerfile |
| **Pipeline/Automation** | Built-in scheduler + live processing | Cron + scripts | Manual or cron |
| **Projections/Georef** | Yes (map overlays, coastlines) | Yes (EMWIN products) | No |
| **Resource Usage** | Moderate-High (1-4 GB RAM) | Low-Moderate (512 MB-2 GB) | Very Low (128-256 MB) |
| **Learning Curve** | Moderate | Steep | Very Easy |

## SatDump: The Universal Satellite Decoder

SatDump is the Swiss Army knife of satellite signal processing. With support for over 90 satellites across multiple downlink modes, it's the tool of choice for serious satellite enthusiasts who want to decode everything from NOAA weather imagery to FengYun meteorological data to GOES full-disk Earth images.

### Architecture

SatDump uses a modular pipeline architecture: a **source** (SDR device, IQ file, or TCP stream) feeds into a **demodulator** (specific to each satellite's modulation scheme), which feeds into a **decoder** (instrument-specific), and finally into a **projection/ compositing engine** that produces georeferenced images.

```
┌─────────┐    ┌──────────────┐    ┌──────────┐    ┌──────────────┐
│ SDR/Source│───▶│ Demodulator   │───▶│ Decoder   │───▶│ Image Output │
└─────────┘    └──────────────┘    └──────────┘    └──────────────┘
```

### Docker Compose Configuration

SatDump ships with an official `docker-compose.yml` in its repository. Here's a production-ready configuration for NOAA APT and Meteor M2-3 reception:

```yaml
version: '3.8'
services:
  satdump:
    image: ghcr.io/satdump/satdump:latest
    container_name: satdump
    devices:
      - /dev/bus/usb:/dev/bus/usb
    volumes:
      - ./satdump_config:/root/.satdump
      - ./satdump_output:/output
      - ./satdump_recordings:/recordings
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    restart: unless-stopped
    network_mode: host
```

### Live Processing Pipeline

SatDump's real power is its live processing mode, which can automatically schedule satellite passes and process them as they happen:

```bash
# Start live processing for NOAA APT on 137 MHz
satdump live noaa_apt --source rtlsdr --samplerate 1.024e6 --frequency 137.1e6

# Process all supported satellites with auto-scheduling
satdump live --autotrack --source rtlsdr --samplerate 2.4e6
```

### Key Strengths

- **90+ satellite support** — from weather satellites to CubeSats
- **Built-in GUI** — live waterfall, constellation plots, image viewer
- **Automatic pass scheduling** — calculates satellite passes and tunes accordingly
- **Georeferenced outputs** — images with map overlays and coastlines
- **Active development** — last commit June 2026

## goestools: GOES Geostationary Specialist

goestools is a focused toolkit for receiving and processing signals from NOAA's GOES geostationary weather satellites (GOES-16, GOES-17, GOES-18). Unlike the polar-orbiting NOAA and Meteor satellites that pass overhead for 10-15 minutes, GOES satellites are stationary at 35,786 km altitude, providing continuous full-disk Earth imagery.

### How GOES Reception Works

GOES transmits data via HRIT (High Rate Information Transmission) and GRB (GOES ReBroadcast) downlinks. Most hobbyists use the HRIT signal at 1694.1 MHz, which requires:

1. A parabolic dish antenna (typically 1-2.4m grid dish)
2. A GOES SAWbird+ LNA (low-noise amplifier) for the 1.7 GHz band
3. An RTL-SDR or Airspy SDR receiver
4. goestools for demodulation and decoding

### Installation & Configuration

```bash
# Build from source
git clone https://github.com/pietern/goestools
cd goestools
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
sudo make install

# Configure goesrecv for HRIT reception
goesrecv --config /etc/goestools/goesrecv.conf
```

Sample `goesrecv.conf`:

```ini
[demodulator]
satellite = "GOES-16"
downlink = "hrit"
source = "airspy"

[airspy]
frequency = 1694100000
sample_rate = 3000000
gain = 21

[costas]
max_deviation = 200

[output]
mode = "hrit"
directory = "/var/lib/goestools/images"
```

### Docker Deployment

```yaml
version: '3.8'
services:
  goestools:
    image: ghcr.io/pietern/goestools:latest
    container_name: goestools
    devices:
      - /dev/bus/usb:/dev/bus/usb
    volumes:
      - ./goestools_config:/etc/goestools
      - ./goestools_images:/var/lib/goestools/images
    environment:
      - TZ=UTC
    restart: unless-stopped
```

### Key Strengths

- **Continuous 24/7 imagery** — no waiting for satellite passes
- **Full-disk Earth images** — the iconic "blue marble" from space
- **EMWIN emergency weather products** — severe weather alerts and forecasts
- **Low CPU usage** — runs comfortably on a Raspberry Pi 4

## noaa-apt: Minimalist NOAA APT Decoder

noaa-apt is a focused, single-purpose decoder written in Rust. It does exactly one thing — decodes NOAA APT (Automatic Picture Transmission) signals from NOAA-15, NOAA-18, and NOAA-19 — and does it extremely well with minimal resource overhead.

### Why noaa-apt?

While SatDump and other tools can decode NOAA APT, noaa-apt excels in these scenarios:

- **Headless servers** — no GUI dependencies, pure CLI operation
- **Resource-constrained devices** — runs on Raspberry Pi Zero with 256 MB RAM
- **Automated pipelines** — perfect for cron-based pass scheduling
- **Fast processing** — written in Rust for maximum performance

### Installation & Usage

```bash
# Install via cargo
cargo install noaa-apt

# Decode a WAV recording
noaa-apt --input recording.wav --output image.png

# Batch process with map overlay
noaa-apt --input pass.wav --output pass.png --map yes --contrast auto

# Process with false-color enhancement
noaa-apt --input pass.wav --output falsecolor.png --enhance falsecolor --rotate 0
```

### Automation with Cron and rtl_fm

The classic headless setup combines `rtl_fm` for recording and `noaa-apt` for decoding:

```bash
#!/bin/bash
# Record and decode NOAA passes automatically
SAT="NOAA-19"
FREQ="137.1e6"
DURATION=900  # 15 minutes

# Record the pass
rtl_fm -f $FREQ -s 48000 -g 49.6 -p 0 -E wav -F 9 -A fast   recording_$SAT.wav &
sleep $DURATION
kill %1

# Decode
noaa-apt recording_$SAT.wav -o $SAT_$(date +%Y%m%d_%H%M).png   --map yes --contrast auto
```

### Key Strengths

- **Extremely lightweight** — uses ~20 MB RAM during decoding
- **Fast Rust implementation** — decodes a 15-minute pass in under 30 seconds
- **Multiple enhancement modes** — false-color, temperature, precipitation
- **Perfect for automation** — designed for cron-based pipelines

## Why Self-Host Your Satellite Ground Station?

Running your own satellite ground station gives you direct access to real-time Earth observation data that most people only see filtered through news media or commercial weather services. The NOAA and Meteor satellite programs broadcast their imagery unencrypted — anyone with a $30 SDR and a simple antenna can receive them.

### Data Sovereignty

When you rely on commercial weather APIs or websites, you're dependent on their uptime, rate limits, and data retention policies. A self-hosted ground station gives you unlimited, unrestricted access to raw satellite telemetry — you archive as much or as little as you want, process it your way, and never worry about API keys expiring.

### Educational Value

Few projects teach you more about radio frequency physics, orbital mechanics, signal processing, and image compositing than building a satellite ground station. You'll learn about Doppler shift compensation, link budgets, modulation schemes (APT, LRPT, HRPT, QPSK), and georeferencing — skills that directly transfer to careers in aerospace, telecommunications, and remote sensing.

### Community and Contribution

By running a ground station, you can contribute data to citizen science networks and global weather databases. The amateur satellite community is one of the most welcoming technical communities online, with active forums, Discord servers, and open-source collaboration. For a deeper dive into the SDR ecosystem, check our [self-hosted SDR receiver guide](../2026-05-13-self-hosted-sdr-receiver-openwebrx-sdr-server-sdrangel-guide/). If you're interested in other radio-based infrastructure, see our [APRS packet radio guide](../2026-06-05-self-hosted-aprs-packet-radio-infrastructure-direwolf-xastir-aprx-guide/) and [ham radio digital voice comparison](../2026-06-05-self-hosted-ham-radio-digital-voice-svxlink-mmdvm-freedv-guide/).

## FAQ

### What hardware do I need to get started?

At minimum, you need an **RTL-SDR dongle** ($25-35), a suitable antenna, and a computer (even a Raspberry Pi 4 works). For NOAA APT, a simple V-dipole antenna tuned to 137 MHz is sufficient. For GOES HRIT, you'll need a parabolic dish antenna (1-2.4m), a 1.7 GHz LNA, and an Airspy or RTL-SDR with appropriate frequency range. Total budget: $50 for NOAA, $200-400 for GOES.

### Which tool should beginners start with?

Start with **noaa-apt** if you want to understand the fundamentals of APT decoding. Its minimal interface forces you to learn the pipeline: record → decode → enhance. Once comfortable, graduate to **SatDump** for its broader satellite support and automated pass scheduling. Skip goestools unless you're specifically targeting GOES geostationary satellites.

### Can I run these tools on a Raspberry Pi?

**noaa-apt** runs perfectly on a Raspberry Pi Zero 2 W or better. **SatDump** requires a Pi 4 with at least 2 GB RAM for smooth operation (compiling from source takes several hours). **goestools** runs well on a Pi 4 but benefits from active cooling for continuous 24/7 GOES reception.

### Do I need a ham radio license?

No license is required for **receiving only**. Satellite downlinks are broadcast signals — anyone can receive them. However, if you plan to transmit (for amateur satellite communication), you'll need an appropriate amateur radio license for your country.

### What's the difference between APT, LRPT, and HRPT?

**APT** (Automatic Picture Transmission) is the analog format used by NOAA-15/18/19 at 137 MHz — lower resolution (4 km/pixel) but easy to receive with simple equipment. **LRPT** (Low Rate Picture Transmission) is the digital equivalent used by Russian Meteor-M satellites at 137 MHz — higher resolution with RGB channels. **HRPT** (High Resolution Picture Transmission) is a high-bandwidth digital downlink at 1.7 GHz — requires tracking antennas and higher-gain hardware.

### How do I handle Doppler shift during a satellite pass?

All three tools compensate automatically — you just set the nominal frequency and the software calculates the real-time Doppler shift based on the satellite's TLE (Two-Line Element) orbital data. SatDump has built-in TLE updating; with goestools and noaa-apt, you'll need to periodically refresh TLE files from celestrak.org.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Amateur Satellite Ground Stations: SatDump vs goestools vs noaa-apt Receiver Guide",
  "description": "Comprehensive comparison of open-source satellite decoding tools: SatDump (90+ satellites, 1,997 stars), goestools (GOES geostationary specialist), and noaa-apt (minimalist NOAA APT decoder). Includes Docker Compose configurations, hardware requirements, and automation pipelines.",
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
