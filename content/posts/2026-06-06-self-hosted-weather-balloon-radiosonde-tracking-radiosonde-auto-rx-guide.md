---
title: "Self-Hosted Weather Balloon Tracking: radiosonde_auto_rx vs RS vs SondeHub — Decode Radiosondes with RTL-SDR"
date: "2026-06-06"
tags: ["radiosonde", "weather-balloon", "sdr", "rtl-sdr", "tracking", "radio", "atmospheric", "self-hosted"]
draft: false
---

## Introduction

Twice daily, hundreds of weather stations worldwide launch radiosondes — instrument packages carried aloft by weather balloons that transmit real-time temperature, humidity, pressure, and GPS position data back to ground stations. These transmissions, typically on 400-406 MHz, are unencrypted and receivable by anyone with an RTL-SDR dongle within a 300-500 km radius.

With open source software, you can track weather balloons in real time, plot their trajectory on a map, and even recover the physical radiosonde after it returns to Earth. This guide compares three open source tools for building a self-hosted radiosonde tracking station: **radiosonde_auto_rx**, **RS**, and the **SondeHub** ecosystem.

## How Radiosonde Decoding Works

Modern radiosondes (Vaisala RS41, Graw DFM, Meteomodem M10, etc.) transmit on the 400-406 MHz meteorological band using GFSK (Gaussian Frequency Shift Keying) modulation at 4800 bps. The decoding pipeline involves:

1. **Signal acquisition**: An RTL-SDR or similar receiver scans the 400-406 MHz band, looking for active sonde transmissions
2. **Demodulation and frame sync**: The GFSK signal is demodulated and synchronization frames are identified
3. **Data extraction**: GPS coordinates, pressure, temperature, humidity, and sonde serial numbers are extracted from each data frame
4. **Position plotting**: Real-time GPS coordinates are plotted on a web map, and predicted landing zones are calculated based on wind data

Unlike AIS or ADS-B signals which are constant background noise, weather balloons are transient events — a single balloon launch lasts 90-180 minutes and covers 200-300 km. The challenge is automated detection and tracking across this window.

## Tool Comparison

| Feature | radiosonde_auto_rx | RS | SondeHub |
|---------|-------------------|-----|----------|
| **Language** | Python/C | C | Web platform |
| **GitHub Stars** | 582+ | 199+ | N/A |
| **Web Map UI** | Built-in (port 5000) | None | Community website |
| **Auto-Detection** | Yes (frequency scan) | Manual tuning | Via contributing stations |
| **Supported Sondes** | RS41, DFM, M10, iMet, LMS6 | RS41, DFM, M10 | All (via community) |
| **Radiosonde Recovery** | Landing prediction | Raw decode only | Community tracking |
| **Database** | Yes (SQLite) | No | SondeHub API |
| **Docker Support** | Yes (recommended) | Manual compile | N/A |
| **Headless Operation** | Full auto mode | CLI only | Browser-based |

### radiosonde_auto_rx: The Gold Standard

radiosonde_auto_rx (`projecthorus/radiosonde_auto_rx`, 582+ stars) is the most mature open source radiosonde tracking solution. Developed by the Project Horus high-altitude balloon team, it provides a fully automated pipeline from signal detection to landing prediction.

```bash
# Install via Docker (recommended)
docker run -d \
  --name radiosonde \
  --device=/dev/bus/usb \
  -p 5000:5000 \
  -v $(pwd)/data:/opt/auto_rx/log \
  ghcr.io/projecthorus/radiosonde_auto_rx:latest
```

```yaml
# docker-compose.yml for radiosonde_auto_rx
version: '3.8'
services:
  auto_rx:
    image: ghcr.io/projecthorus/radiosonde_auto_rx:latest
    container_name: auto_rx
    devices:
      - /dev/bus/usb:/dev/bus/usb
    ports:
      - "5000:5000"
    volumes:
      - ./data:/opt/auto_rx/log
      - ./station.cfg:/opt/auto_rx/station.cfg
    restart: unless-stopped
    environment:
      - TZ=UTC
```

Once running, access the web interface at `http://localhost:5000` to see active sonde tracks, landing predictions, and historical logs. radiosonde_auto_rx automatically scans the 400-406 MHz band, detects new balloon launches, and begins tracking without any user intervention.

The landing prediction feature is particularly valuable for radiosonde hunters — using wind data from meteorological models, auto_rx calculates where the balloon will burst and the sonde will land, making physical recovery feasible.

### RS: The Lightweight Decoder

RS (`rs1729/RS`, 199+ stars) is a focused C-based decoder that excels at extracting data from specific sonde types with minimal resource usage. It's designed for embedded systems and headless servers where every megabyte of RAM matters.

```bash
# Build RS from source
git clone https://github.com/rs1729/RS.git
cd RS
make

# Decode an RS41 sonde on 402.5 MHz
rtl_fm -f 402.5M -M fm -s 12k -g 49.6 -p 0 | \
  ./rs --rs41 --json
```

RS outputs structured JSON for each decoded frame, making it easy to integrate with external plotting tools:

```bash
# Pipe RS output to a Python script for custom plotting
rtl_fm -f 402.5M -M fm -s 12k -g 49.6 | \
  ./rs --rs41 --json 2>/dev/null | \
  python3 plot_track.py
```

RS is ideal for embedded deployments like a headless Raspberry Pi at a remote receiving site, where you want to forward decoded positions to a central server. Its minimal footprint means it runs comfortably alongside other services on resource-constrained hardware.

### SondeHub: The Community Network

SondeHub is a global network of radiosonde tracking stations that aggregate data from hundreds of volunteer-operated receivers worldwide. While SondeHub itself is a centralized web platform, its data originates from community stations running radiosonde_auto_rx — making it both a destination for your data and a source of global sonde tracks.

```bash
# Contribute your station data to SondeHub
# Add to auto_rx station.cfg:
[sondehub]
upload_enabled = True
upload_rate = 5
station_call = "YOUR_CALLSIGN"
```

By running radiosonde_auto_rx and enabling SondeHub upload, you become part of the global tracking network. In return, you can view tracks from stations worldwide at sondehub.org, see aggregated atmospheric data, and contribute to meteorological research.

## Building a Radiosonde Tracking Station

A complete self-hosted radiosonde tracking station requires minimal hardware:

```
RTL-SDR Dongle → Raspberry Pi → radiosonde_auto_rx → Web Map (port 5000)
                                                      → SondeHub (community upload)
                                                      → Local SQLite DB (archive)
```

The station operates autonomously — once configured, it scans the 400-406 MHz band 24/7, automatically detects and tracks new balloon launches, and logs everything to a local database. The web interface provides a live map of all tracked sondes with altitude, climb rate, and predicted landing coordinates.

## Why Self-Host Radiosonde Tracking?

Weather balloon tracking sits at the intersection of radio science, meteorology, and treasure hunting. Unlike commercial weather data services that charge for access, radiosondes transmit their data openly — you just need the right tools to receive it.

**Real atmospheric data**: Radiosondes provide vertical profiles of temperature, humidity, and pressure from the surface to 30+ km altitude — data that commercial weather APIs charge for. Self-hosting gives you direct access to this atmospheric sounding data for your location.

**Radiosonde recovery (hunting)**: After the balloon bursts at ~30 km, the radiosonde descends by parachute and lands within 200-300 km of the launch site. The radiosonde can be recovered, refurbished, and reused — a popular hobby that combines radio tracking with orienteering. radiosonde_auto_rx's landing prediction makes this practical.

**Community science**: By contributing your station data to SondeHub, you help build a global atmospheric dataset used by researchers, weather modelers, and students. Your $25 SDR dongle becomes part of a worldwide meteorological observation network.

For related projects, check our [ADS-B flight tracking guide](../2026-04-27-dump1090-vs-readsb-vs-tar1090-self-hosted-ads-b-flight-tracking-guide-2026/) for aircraft monitoring, our [amateur satellite ground station comparison](../2026-06-06-self-hosted-amateur-satellite-ground-stations-satdump-goestools-noaa-apt/), and our [SDR receiver platform overview](../2026-05-13-self-hosted-sdr-receiver-openwebrx-sdr-server-sdrangel-guide/).

## SDR Hardware Selection for Radiosonde Tracking

Not all SDR dongles are equally suited for radiosonde tracking at 400-406 MHz. The higher frequency range and weak signals from distant balloons demand better receiver performance than basic VHF monitoring.

**Recommended SDR hardware:**

- **RTL-SDR Blog V3/V4** ($25-35): The standard choice. The V4 model includes an improved frontend with better filtering above 300 MHz and a built-in bias-tee for powering an LNA. Sufficient for tracking sondes within 200 km.
- **Airspy Mini** ($99): 12-bit ADC with significantly better dynamic range than 8-bit RTL-SDR dongles. Handles strong nearby signals without overload — important if you have FM broadcast or paging transmitters nearby.
- **SDRplay RSP1A** ($120): 14-bit ADC, continuous coverage from 1 kHz to 2 GHz with excellent 400 MHz sensitivity. The gold standard for serious radiosonde hunters who want maximum range.

**The LNA question**: A low-noise amplifier (LNA) at the antenna can extend your range from ~200 km to 400+ km by boosting the weak sonde signal above the receiver noise floor. The SPF5189Z-based LNA modules ($10-15 on AliExpress) provide ~20 dB gain at 400 MHz and are widely used in the radiosonde community. Mount the LNA at the antenna feedpoint, not at the receiver, for best noise performance.


## FAQ

### What frequencies do weather balloons use?

Most modern radiosondes operate in the 400-406 MHz meteorological band. Vaisala RS41 sondes use 400.15-405.99 MHz, Graw DFM sondes use 400-406 MHz, and Meteomodem M10 sondes use 401-406 MHz. Older analog sondes may use 1680 MHz. radiosonde_auto_rx automatically scans the entire 400-406 MHz range.

### How often are weather balloons launched?

Standard meteorological launches occur twice daily worldwide — at 00:00 UTC and 12:00 UTC — from approximately 800 launch sites globally. During severe weather events, additional launches may occur at 06:00 UTC and 18:00 UTC. Each launch is tracked for 90-180 minutes.

### Can I recover a fallen radiosonde?

Yes — this is the hobby of "radiosonde hunting." After the balloon bursts at high altitude, the radiosonde descends by parachute. radiosonde_auto_rx calculates a landing prediction based on wind data, and with practice, you can recover sondes within hours of landing. Most modern sondes (RS41, DFM) can be refurbished and reused for personal high-altitude balloon projects.

### Do I need a special antenna for 400 MHz?

A basic RTL-SDR telescopic antenna extended to ~18 cm (quarter-wave at 402 MHz) works well for near-horizon reception. For longer range (300+ km), a 70cm amateur radio Yagi antenna or a discone antenna mounted outdoors provides significantly better gain. Many operators use a simple ground-plane antenna built from an SO-239 connector and 4 copper radials.

### What happens if I miss a balloon launch?

radiosonde_auto_rx continuously scans the band, so it will detect any active sonde within range regardless of when it launched. Even if you start tracking mid-flight, you'll still receive GPS positions, altitude, and meteorological data from that point onward — just without the full ascent profile.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Weather Balloon Tracking: radiosonde_auto_rx vs RS vs SondeHub — Decode Radiosondes with RTL-SDR",
  "description": "Complete guide to self-hosted weather balloon and radiosonde tracking using RTL-SDR. Compare radiosonde_auto_rx, RS, and SondeHub for decoding Vaisala RS41, Graw DFM, and Meteomodem M10 weather balloon telemetry with real-time GPS mapping.",
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
