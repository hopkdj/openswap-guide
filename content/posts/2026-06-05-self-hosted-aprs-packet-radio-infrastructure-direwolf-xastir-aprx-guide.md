---
title: "Self-Hosted APRS & Packet Radio Infrastructure: Direwolf vs Xastir vs aprx"
date: "2026-06-05"
tags: ["ham-radio", "aprs", "packet-radio", "amateur-radio", "tnc", "self-hosted", "raspberry-pi", "rf"]
draft: false
---

## Introduction

The Automatic Packet Reporting System (APRS) is one of amateur radio's most vibrant data networks, carrying position reports, weather telemetry, short messages, and emergency communications across VHF/UHF frequencies worldwide. Behind every APRS station — whether tracking a high-altitude balloon, monitoring a remote weather station, or providing emergency communications — sits a software-defined TNC (Terminal Node Controller) and infrastructure stack.

This article compares three essential open-source tools for building self-hosted APRS infrastructure: Direwolf (the software TNC and digipeater), Xastir (the graphical APRS client), and aprx (the dedicated iGate/digipeater daemon). Whether you want to set up a receive-only iGate to fill coverage gaps, run a full duplex digipeater, or build a tactical APRS display for emergency operations, this guide covers the complete stack.

| Feature | Direwolf | Xastir | aprx |
|---------|----------|--------|------|
| **Role** | Software TNC + digipeater | Graphical APRS client | Headless iGate/digipeater |
| **Language** | C | C (with Motif GUI) | C |
| **Interface** | CLI + optional web dashboard | X11 graphical UI | CLI daemon (systemd) |
| **TNC Modes** | AFSK 1200/9600, PSK, FX.25, IL2P | Uses Direwolf or hardware TNC | N/A (network-only) |
| **Digipeater** | Yes (full WIDE-N and preemptive) | No (client-side only) | Yes (full APRS digipeater) |
| **iGate** | Yes (bidirectional) | No | Yes (RX-only and bidirectional) |
| **Mapping** | No | Yes (online + offline maps) | No |
| **Stars** | 1,982 | 245 | Debian-packaged (community) |
| **Resource Usage** | ~15MB RAM, ARM/RPi capable | ~50MB RAM, needs X11 | ~5MB RAM, runs on OpenWrt |

## Direwolf: The Software TNC

Direwolf, maintained by WB2OSZ, has become the de facto standard for software TNCs in the APRS ecosystem. It converts audio from a radio receiver into decoded AX.25 packets — and vice versa for transmission — entirely in software, eliminating the need for a dedicated hardware TNC.

Key capabilities include simultaneous decoding of multiple AFSK channels, support for the FX.25 forward error correction protocol, IL2P (Improved Layer 2 Protocol) for better performance over noisy links, and a built-in APRS digipeater with intelligent duplicate suppression. Direwolf can also function as a full iGate, bridging RF-received packets to the APRS-IS internet backbone.

```yaml
# docker-compose.yml for Direwolf TNC + iGate
version: '3.8'
services:
  direwolf:
    image: ubuntu:22.04
    container_name: direwolf-tnc
    devices:
      - /dev/snd:/dev/snd  # Audio device access
    volumes:
      - ./direwolf.conf:/etc/direwolf.conf
      - ./logs:/var/log/direwolf
    network_mode: host
    command: >
      bash -c "
        apt-get update && 
        apt-get install -y direwolf gpsd gpsd-clients &&
        direwolf -c /etc/direwolf.conf -t 0
      "
    restart: unless-stopped
```

### Direwolf Configuration

```ini
# direwolf.conf — Full-featured iGate + digipeater
ADEVICE plughw:1,0
ACHANNELS 1
CHANNEL 0
MODEM 1200

# iGate configuration
IGSERVER noam.aprs2.net
IGLOGIN N0CALL 12345
PBEACON sendto=IG delay=0:30 every=10:00 symbol="igate" overlay=R lat=40.7128^N long=074.0060^W power=5 height=20 gain=3 comment="Self-Hosted APRS iGate | Direwolf"

# Digipeater configuration
DIGIPEAT 0 0 ^WIDE[3-7]-[1-7]$|^TEST$ ^WIDE[12]-[12]$ TRACE

# GPS integration
GPSD localhost

# Web interface
AGWPORT 8000
KISSPORT 8001
```

Build Direwolf from source for the latest features:

```bash
git clone https://github.com/wb2osz/direwolf.git
cd direwolf
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=/usr ..
make -j$(nproc)
sudo make install
sudo make install-conf
```

## Xastir: The Graphical APRS Client

Xastir (X Amateur Station Tracking and Information Reporting) is a full-featured APRS client with integrated mapping. Unlike Direwolf or aprx, Xastir is an interactive application — you view stations on a map, send and receive messages, track weather stations, and manage APRS objects.

Xastir does not include its own TNC; it interfaces with Direwolf via the AGWPE or KISS protocol, with hardware TNCs via serial port, or with APRS-IS directly over the internet. This modularity means you can pair Xastir with Direwolf for a complete APRS station.

```bash
# Install Xastir on Ubuntu/Debian
sudo apt-get install xastir

# Or build from source for latest features
git clone https://github.com/Xastir/Xastir.git
cd Xastir
./bootstrap.sh
./configure --with-bdb-incdir=/usr/include/db5.3
make -j$(nproc)
sudo make install
```

For headless server deployments, Xastir can run in "no GUI" mode with a virtual framebuffer (Xvfb), enabling server-side screenshot generation or automated map rendering. This is useful for web-based APRS dashboards that need map tiles generated server-side:

```bash
# Run Xastir headless with Xvfb
Xvfb :99 -screen 0 1024x768x16 &
export DISPLAY=:99
xastir &
```

## aprx: The Headless iGate/Digipeater

aprx, maintained by OH7LZB, is a lightweight APRS digipeater and iGate daemon designed for 24/7 operation on embedded systems. Packaged in Debian and Ubuntu repositories (`apt install aprx`), it runs as a systemd service consuming approximately 5MB of RAM — making it suitable for OpenWrt routers, Raspberry Pi Zero devices, and other resource-constrained platforms.

aprx supports both receive-only (RX) and bidirectional (TX) iGate modes, full digipeater functionality with customizable aliases, multiple radio ports, serial KISS TNC integration, and beacon scheduling. Its configuration is declarative via a single INI-style file.

```ini
# /etc/aprx.conf — Bidirectional iGate + digipeater
mycall N0CALL
server noam.aprs2.net

<aprsis>
  passcode 12345
  filter m/100
</aprsis>

<beacon>
  beaconmode both
  cycle 30
  beacon symbol "R&" lat "40^42.77N" lon "074^00.36W" comment "Self-Hosted APRS iGate | aprx"
</beacon>

<interface>
  ax25-device $direwolf
  tx-ok true
</interface>

<digipeater>
  transmitter $direwolf
  <wide1-1>
    filter -t/w
    <wide2-2>
      filter -t/w
    </wide2-2>
  </wide1-1>
</digipeater>
```

```bash
# Install and start aprx
sudo apt-get install aprx
sudo systemctl enable aprx
sudo systemctl start aprx
sudo systemctl status aprx
```

## Building a Complete APRS Station

A full self-hosted APRS station combines all three tools:

```
[Radio] --audio--> [Direwolf TNC] --KISS/AGWPE--> [Xastir Client]
                         |                              |
                         +--IGate--> [APRS-IS Internet]
                         |
                         +--[aprx (optional) for dedicated digipeating]
```

1. **Direwolf** handles the physical layer — converting radio audio to packets and vice versa
2. **aprx** manages the network layer — digipeating, iGating, beacon scheduling
3. **Xastir** provides the user interface — mapping, messaging, tactical displays

For a receive-only iGate, Direwolf alone is sufficient. For a digipeater site, add aprx for more sophisticated digipeating logic. For an emergency operations center, add Xastir for situational awareness with mapping.

## Why Self-Host Your APRS Infrastructure?

APRS is a community network — its coverage depends on volunteers running iGates and digipeaters. When you self-host an iGate, you directly expand the APRS network's reach in your area, helping travelers, hikers, balloon trackers, and emergency responders get their position reports to the internet. There is no commercial entity providing this service; it exists entirely because hams deploy infrastructure.

Self-hosting gives you control over what gets gated to the internet and what stays local. You can filter by distance, callsign, or message type — critical for tactical deployments where you do not want every position report broadcast globally. You can also log all traffic locally for later analysis, something third-party APRS-IS clients do not provide.

For related amateur radio infrastructure, see our [Ham Radio Digital Voice Gateways guide](../2026-06-05-self-hosted-ham-radio-digital-voice-svxlink-mmdvm-freedv-guide/) covering SvxLink, MMDVM, and FreeDV. Our [self-hosted SDR receiver comparison](../2026-05-13-self-hosted-sdr-receiver-openwebrx-sdr-server-sdrangel-guide/) covers OpenWebRX and SDRangel for software-defined radio monitoring. For location tracking beyond APRS, our [GPS tracking fleet management guide](../2026-05-04-self-hosted-gps-tracking-fleet-management-traccar-owntracks-gpslogger-guide/) compares Traccar, OwnTracks, and GPSLogger.

## FAQ

### Do I need a ham radio license to set up an APRS iGate?

Yes, for any station that transmits. A receive-only (RX) iGate can be set up without a license in most jurisdictions since it only receives and forwards to the internet. However, any digipeater or bidirectional iGate requires an amateur radio license because it transmits on amateur radio frequencies. Check your local regulations — in the US, a Technician-class license is sufficient for APRS operations on 2 meters (144.390 MHz in North America).

### What hardware do I need for a basic APRS station?

At minimum: a VHF radio receiver (or transceiver for TX), a Raspberry Pi or similar Linux computer, and an audio interface between the radio and computer. A simple USB sound card and a 3.5mm audio cable can serve as the interface. For transmission, you need a push-to-talk (PTT) interface — either a simple transistor circuit triggered by a GPIO pin or a Signalink USB sound card with built-in PTT. Many hams use a Baofeng UV-5R (~$25) with a Raspberry Pi 4 running Direwolf for a complete APRS station under $100.

### Can I use APRS without a radio?

Yes. You can connect Xastir or any APRS client directly to the APRS-IS internet backbone without radio hardware. This lets you view APRS traffic globally, send messages, and track stations. However, you will not be contributing RF coverage to the local APRS network. Many operators run APRS clients this way alongside their radio-based stations.

### What frequencies does APRS use?

APRS operates on different frequencies by region: 144.390 MHz in North America, 144.800 MHz in Europe, 145.175 MHz in Australia, and 144.640 MHz in Japan. There are also APRS frequencies on HF (30m band at 10.151 MHz LSB) for long-distance APRS, and on 70cm (430-440 MHz depending on region) for higher-speed 9600 baud operation.

### How does APRS differ from other digital modes like FT8 or DMR?

APRS is a packet-based protocol for position reporting, messaging, and telemetry — it is about DATA. FT8 is a weak-signal mode for making contacts with minimal exchange (callsign + grid square + signal report). DMR is a digital voice mode for voice conversations. APRS packets can carry any data — GPS coordinates, weather readings, text messages, telemetry from remote sensors. The three modes serve completely different purposes and often coexist at the same station.

### Can I run Direwolf + aprx on a Raspberry Pi Zero?

Yes. Direwolf requires about 15MB RAM and aprx about 5MB. A Raspberry Pi Zero W (512MB RAM) can comfortably run both alongside a lightweight Linux distribution. For the audio interface, use a USB sound card; the Pi Zero's USB OTG port handles this well. Power consumption for the entire station (Pi Zero + sound card + radio in receive mode) is typically under 5 watts — easily solar-powered for remote deployment.

## The APRS Ecosystem Beyond These Tools

The APRS software ecosystem extends well beyond the three tools covered here. Other notable open-source APRS projects include:

- **YAAC** (Yet Another APRS Client) — A Java-based APRS client that runs on any platform with a JVM, offering extensive plugin support and map rendering
- **APRSdroid** — An Android app (596 GitHub stars) that turns your phone into an APRS tracker, with support for both APRS-IS (internet) and AFSK (audio) modes via the phone's speaker/microphone
- **PinPoint APRS** — A Windows-native APRS client popular for emergency communications (EmComm) with ICS form integration
- **APRSISCE/32** — A feature-rich Windows Mobile/CE and Windows desktop client with a following in the EmComm community

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted APRS & Packet Radio Infrastructure: Direwolf vs Xastir vs aprx",
  "description": "A comprehensive guide to building self-hosted APRS and packet radio infrastructure with Direwolf (software TNC), Xastir (graphical client), and aprx (headless digipeater/iGate), including Docker deployment, configuration, and station architecture for amateur radio operators.",
  "datePublished": "2026-06-05",
  "dateModified": "2026-06-05",
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
