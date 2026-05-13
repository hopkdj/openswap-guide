---
title: "Self-Hosted SDR Receiver: OpenWebRX vs sdr-server vs SDRangel"
date: "2026-05-13"
tags: ["sdr", "radio", "network-services", "web-interface"]
draft: false
---

Software-Defined Radio (SDR) has democratized access to the radio frequency spectrum, turning a $30 USB dongle into a gateway for listening to everything from aircraft transponders and weather satellites to amateur radio and shortwave broadcasts. Self-hosting an SDR receiver on a home server or Raspberry Pi lets you share antenna access across your network, monitor frequencies 24/7, and build automated signal processing pipelines.

This guide compares three open-source SDR receiver platforms you can deploy on your own hardware: **OpenWebRX**, **sdr-server**, and **SDRangel**. Each offers a different approach to networked SDR — from lightweight web streaming to full-featured desktop analysis.

## What Is a Self-Hosted SDR Receiver?

A self-hosted SDR receiver runs server software that connects to an SDR dongle (RTL-SDR, Airspy, SDRplay, HackRF, etc.) and makes the RF data available over a network. Clients connect via a web browser or desktop application to tune frequencies, demodulate signals, and analyze the spectrum in real time.

Key use cases include:

- **ADS-B aircraft tracking** — decode Mode S transponder signals from nearby flights
- **NOAA/Meteor satellite reception** — capture weather satellite imagery passes
- **Amateur radio monitoring** — listen to FM repeaters, digital modes (FT8, DMR), and HF bands
- **ISM band analysis** — monitor 433 MHz, 868 MHz, 2.4 GHz for IoT device activity
- **Emergency services monitoring** — listen to public safety frequencies where legal
- **Spectrum surveillance** — detect unauthorized transmitters or interference sources

## OpenWebRX

**Stars:** 1,055+ | **Repo:** `ha7ilm/openwebrx` | **Language:** Python

OpenWebRX is the most widely deployed open-source web-based SDR receiver. Created by HA7ILM, it provides a multi-user web interface where multiple clients can independently tune and demodulate different portions of the received spectrum simultaneously.

### Architecture

OpenWebRX separates the signal capture pipeline from the web frontend:

1. **Signal chain**: SDR hardware → SoapySDR/rtl-sdr driver → channelizer → codecserver → WebRTC audio stream
2. **Web frontend**: HTML5 waterfall display with mouse-controlled frequency selection, demodulation mode picker (AM, FM, SSB, CW, NFM, WFM), and signal strength meter
3. **Multi-user support**: Each client gets an independent virtual receiver slice from the shared spectrum

### Key Features

- Web-based waterfall with real-time FFT display
- Support for 15+ SDR hardware types via SoapySDR
- Digital mode decoding: DMR, D-Star, YSF, FreeDV, DRM, NXDN (via codecserver plugins)
- Band plans and frequency presets
- User administration with access control
- Mobile-responsive interface
- Bookmark and share specific frequencies

### Docker Deployment

OpenWebRX+ (the actively maintained fork) can be deployed via Docker:

```yaml
services:
  openwebrx:
    image: lsziki/openwebrx:latest
    container_name: openwebrx
    restart: unless-stopped
    ports:
      - "8073:8073"
    devices:
      - /dev/bus/usb:/dev/bus/usb
    volumes:
      - ./config:/etc/openwebrx
      - ./bookmarks:/var/lib/openwebrx/bookmarks
    environment:
      - OW_RX_SDR=rtl
      - OW_RX_DEVICE=0
      - OW_RX_SAMPLE_RATE=2048000
      - OW_RX_CENTER_FREQ=109000000
      - OW_MAX_CLIENTS=5
```

The device passthrough (`/dev/bus/usb`) is critical for direct SDR dongle access. For production deployments, consider running on a dedicated Raspberry Pi 4 with a high-quality RTL-SDR Blog V3 or Airspy Mini.

### Resource Requirements

- CPU: ~30-60% of one core per active client (FFT + demodulation)
- RAM: ~200 MB base + ~50 MB per client
- Storage: Minimal (no recording by default)
- Network: ~1-2 Mbps per active WebRTC audio stream

## sdr-server

**Stars:** 230+ | **Repo:** `dernasherbrezon/sdr-server` | **Language:** Java

sdr-server is a high-performance TCP server for RTL-SDR devices, designed as a backend that streams raw I/Q samples over TCP to multiple clients. It's lighter weight than OpenWebRX and focuses on reliable sample delivery rather than a built-in web interface.

### Architecture

sdr-server operates as a raw I/Q streaming daemon:

1. **Capture**: Opens the RTL-SDR device and reads I/Q samples at the configured sample rate
2. **Distribution**: Multicasts or TCP-streams raw I/Q data to connected clients
3. **Clients**: External applications (SDR#, SDR++, custom decoders) connect via TCP to receive the stream

### Key Features

- Low-latency I/Q streaming over TCP
- Multiple simultaneous client connections
- Configurable sample rate, frequency, and gain
- Lightweight daemon (no web UI overhead)
- Suitable as a backend for custom signal processing pipelines
- Works with any RTL-SDR compatible device

### Docker Deployment

```yaml
services:
  sdr-server:
    image: dernasherbrezon/sdr-server:latest
    container_name: sdr-server
    restart: unless-stopped
    ports:
      - "1234:1234"
    devices:
      - /dev/bus/usb:/dev/bus/usb
    environment:
      - FREQUENCY=109000000
      - SAMPLE_RATE=2048000
      - GAIN=30
      - PPM=0
```

Clients connect to `tcp://your-server:1234` and receive raw I/Q samples. Pair with SDR++ on a workstation for a full receiver experience, or feed the stream into dump1090, rtl_433, or other decoders.

### Use Case: ADS-B Decoding Pipeline

```yaml
services:
  sdr-server:
    image: dernasherbrezon/sdr-server:latest
    ports:
      - "1234:1234"
    devices:
      - /dev/bus/usb:/dev/bus/usb
    environment:
      - FREQUENCY=109000000
      - SAMPLE_RATE=2048000

  dump1090:
    image: ghcr.io/adsbexchange/adsbexchange-mlat:latest
    depends_on:
      - sdr-server
    ports:
      - "8080:8080"
    command: ["--net", "--device-type", "rtltcp", "--rtltcp-ip", "sdr-server", "--rtltcp-port", "1234"]
```

## SDRangel

**Stars:** 3,769+ | **Repo:** `f4exb/sdrangel` | **Language:** C++

SDRangel is the most feature-rich open-source SDR application available. It supports both receive (Rx) and transmit (Tx) operations across a wide range of SDR hardware platforms. While primarily a desktop application, it can be deployed headless with remote access for a self-hosted receiver setup.

### Architecture

SDRangel uses a modular plugin architecture:

1. **Device plugins**: Drivers for 20+ SDR hardware types (Airspy, BladeRF, HackRF, LimeSDR, PlutoSDR, RTL-SDR, SDRplay)
2. **Channel plugins**: Demodulators for AM, FM, SSB, CW, DAB, DRM, AIS, ADS-B, APRS, and many more
3. **Feature plugins**: Spectrum analyzer, constellation display, audio recording, signal logging

### Key Features

- 20+ supported SDR hardware platforms
- 30+ demodulation channel types
- Real-time spectrum and waterfall display
- Recording and playback of I/Q data
- Transmitter support (with compatible hardware)
- Android client for remote control
- Remote API for headless operation
- Plugin-based extensibility

### Deployment

SDRangel is primarily a desktop application, but can be run on a headless server with X11 forwarding or VNC:

```bash
# Install dependencies
apt install -y build-essential cmake libfftw3-dev librtlsdr-dev   libairspy-dev libhackrf-dev libbladerf-dev liblimesuite-dev   qtbase5-dev qtwebkit5-dev libopencv-dev libvolk-dev

# Clone and build
git clone https://github.com/f4exb/sdrangel.git
cd sdrangel
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
sudo make install
```

For remote access, pair with **x11vnc** or **Apache Guacamole**:

```yaml
services:
  sdrangel:
    image: linuxserver/sdrangel:latest
    container_name: sdrangel
    restart: unless-stopped
    ports:
      - "3000:3000"  # Guacamole web interface
      - "8888:8888"  # SDRangel remote API
    devices:
      - /dev/bus/usb:/dev/bus/usb
    volumes:
      - ./recordings:/recordings
      - ./config:/config
    environment:
      - PUID=1000
      - PGID=1000
```

## Comparison Table

| Feature | OpenWebRX | sdr-server | SDRangel |
|---------|-----------|------------|----------|
| **Web Interface** | Built-in, multi-user | None (TCP backend) | Desktop/VNC/Guacamole |
| **Supported Hardware** | 15+ via SoapySDR | RTL-SDR only | 20+ native drivers |
| **Multi-User** | Yes (independent slices) | Yes (shared stream) | Single user |
| **Digital Modes** | DMR, D-Star, YSF, DRM, NXDN | Raw I/Q only | 30+ demodulators |
| **Transmit (Tx)** | No | No | Yes (select hardware) |
| **Recording** | Limited | Client-side | Full I/Q recording |
| **Mobile Friendly** | Yes | N/A | Via Guacamole |
| **CPU Usage** | Medium | Low | High |
| **Setup Complexity** | Low | Very low | High |
| **Docker Support** | Community images | Official image | LinuxServer image |
| **License** | GPL-3.0 | GPL-3.0 | GPL-3.0 |

## Choosing the Right SDR Receiver

### Choose OpenWebRX if:
- You need a web-based interface accessible from any browser
- Multiple users need independent frequency access
- You want digital mode decoding built in
- You're deploying on a Raspberry Pi

### Choose sdr-server if:
- You need a lightweight I/Q streaming backend
- You're building a custom signal processing pipeline
- You want to feed raw samples to multiple decoders (dump1090, rtl_433, etc.)
- You prefer minimal resource usage

### Choose SDRangel if:
- You need the widest hardware support
- You want transmit capability
- You need advanced signal analysis tools
- You're running on a powerful desktop or server

## Why Self-Host Your SDR Receiver?

Running your own SDR receiver infrastructure gives you complete control over your RF monitoring setup. Unlike public SDR networks (like WebSDR or KiwiSDR), a self-hosted receiver keeps your antenna data private, eliminates dependency on third-party services, and lets you customize the signal processing chain for your specific use case.

### Data Ownership and Privacy

When you self-host, all received signals stay on your network. This matters for applications like:
- **Security research**: Analyzing proprietary wireless protocols without exposing findings to public servers
- **IoT monitoring**: Detecting rogue devices on your property without sharing RF data externally
- **Amateur radio**: Maintaining a personal station log without third-party logging

### Cost Savings

Public SDR hosting services typically charge $5-20/month for dedicated access. A Raspberry Pi 4 ($55) with an RTL-SDR Blog V3 ($30) provides a capable self-hosted receiver for a one-time cost of $85, paying for itself within two months.

### Customization

Self-hosting lets you:
- Chain multiple SDR receivers for wideband coverage
- Integrate with home automation (trigger alerts on specific frequencies)
- Run automated decoding pipelines (ADS-B → FlightRadar24 feeder, NOAA → weather image archive)
- Apply custom filters and signal processing

For related reading on network monitoring, see our [network scanning tools comparison](../2026-04-22-nmap-vs-masscan-vs-rustscan-self-hosted-network-scanning-guide-2026/) and [network simulation platforms](../2026-04-18-gns3-vs-eve-ng-vs-containerlab-self-hosted-network-simulation-2026/).

## FAQ

### What SDR hardware works best for self-hosted receivers?

For beginners, the **RTL-SDR Blog V3** ($30) is the best entry point — it covers 24 MHz to 1.7 GHz, has a TCXO for frequency stability, and works with all three platforms discussed. For better performance, the **Airspy Mini** ($99) offers superior sensitivity and dynamic range. The **SDRplay RSPdx** ($169) covers 1 kHz to 2 GHz with 14-bit ADC and is ideal for serious monitoring.

### Can I run multiple SDR receivers on one server?

Yes. Each SDR dongle appears as a separate USB device. OpenWebRX supports multiple receivers through separate configuration profiles. sdr-server can run multiple instances, each bound to a different TCP port and USB device.

### Is it legal to listen to all frequencies?

Laws vary by country. In the US, listening to most radio transmissions is legal, but decrypting encrypted communications, cell phone calls, or intentionally interfering with transmissions is illegal. Always check local regulations before monitoring.

### How much bandwidth does an SDR receiver use?

OpenWebRX uses ~1-2 Mbps per active client for WebRTC audio streaming. sdr-server streams raw I/Q at 2-8 Mbps per client depending on sample rate. For occasional listening, this is manageable on most home networks.

### Can I access my SDR receiver from outside my home network?

Yes, but consider security. OpenWebRX has built-in user authentication. For sdr-server and SDRangel, use a VPN (WireGuard, Tailscale) or reverse proxy with TLS to secure remote access. Never expose raw SDR ports to the internet without authentication.

### What antenna should I use?

A simple dipole or discone antenna covers most VHF/UHF monitoring needs. For HF (shortwave), a long wire antenna (20-50 meters) works well. For ADS-B specifically, a 1090 MHz tuned collinear antenna dramatically improves range.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted SDR Receiver: OpenWebRX vs sdr-server vs SDRangel",
  "description": "Compare three open-source SDR receiver platforms for self-hosting: OpenWebRX web-based streaming, sdr-server TCP backend, and SDRangel desktop analysis.",
  "datePublished": "2026-05-13",
  "dateModified": "2026-05-13",
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

