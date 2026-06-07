---
title: "Self-Hosted Bluetooth Audio Receivers: LibreSpot vs Shairport Sync vs balenaSound"
date: "2026-06-07"
tags: ["self-hosted", "audio", "raspberry-pi", "bluetooth", "docker", "iot", "comparison", "guide", "streaming"]
draft: false
---

## Introduction

Turning a Raspberry Pi or old computer into a high-quality wireless audio receiver is one of the most rewarding self-hosted projects. Instead of buying expensive proprietary speakers with built-in streaming, you can connect any existing sound system to a small Linux board and stream audio from any device over Wi-Fi. Three projects dominate this space: **LibreSpot** for Spotify Connect, **Shairport Sync** for Apple AirPlay, and **balenaSound** as an all-in-one multi-protocol solution. This guide compares their features, deployment, and ideal use cases.

## Comparison Overview

| Feature | LibreSpot | Shairport Sync | balenaSound |
|---------|-----------|----------------|-------------|
| **Protocol** | Spotify Connect | AirPlay 1 & 2 | Spotify, AirPlay, Bluetooth, multiroom |
| **GitHub Stars** | 6,800+ | 8,680+ | 2,600+ |
| **Last Updated** | February 2026 | June 2026 | August 2025 |
| **Docker Support** | Yes (community images) | Yes (official) | Yes (official) |
| **Hardware** | Raspberry Pi, Linux, macOS | Linux, FreeBSD | Raspberry Pi (Balena OS) |
| **Multi-Room** | Via Spotify app | Via AirPlay 2 | Built-in Snapcast |
| **Resource Usage** | Light (~30MB RAM) | Light (~25MB RAM) | Moderate (~200MB RAM) |
| **Audio Quality** | Up to 320kbps Ogg | Lossless ALAC | Variable per protocol |
| **Setup Complexity** | Low | Low | Medium |
| **Ease of Use** | Very easy | Very easy | Plug-and-play |

## LibreSpot: Lightweight Spotify Connect Receiver

LibreSpot is an open-source Spotify Connect client written in Rust. It makes your Linux device appear as a Spotify speaker — anyone on the same network can select it from the Spotify app and stream directly. No additional apps or Bluetooth pairing needed.

**Key Strengths:**
- Extremely lightweight (~30 MB RAM, negligible CPU)
- Starts in seconds, zero configuration for basic use
- Supports Spotify's full quality (320 kbps Ogg Vorbis)
- Works on any ALSA-compatible Linux device
- Can run as a systemd service or Docker container

**Docker Compose Deployment:**

```yaml
version: "3.8"
services:
  librespot:
    image: librespot/librespot:latest
    container_name: librespot
    network_mode: host
    devices:
      - /dev/snd:/dev/snd
    command:
      - "--name"
      - "Living Room Speaker"
      - "--backend"
      - "alsa"
      - "--device"
      - "hw:0,0"
      - "--bitrate"
      - "320"
      - "--initial-volume"
      - "75"
    restart: unless-stopped
```

LibreSpot's single-protocol focus means it does one thing exceptionally well. If your household is primarily on Spotify, this is the most efficient choice. It supports Spotify's gapless playback, volume normalization, and even Spotify Connect's authentication flow.

One limitation: LibreSpot requires a Spotify Premium account (Spotify Connect is a premium feature). Free-tier users cannot use it.

## Shairport Sync: Full AirPlay 1 & 2 Compatibility

Shairport Sync is the gold standard for AirPlay audio on Linux. It implements Apple's AirPlay protocol (both version 1 and 2) faithfully, making your Linux device appear as a native AirPlay speaker to iPhones, iPads, and Macs.

**Key Strengths:**
- Full AirPlay 2 support (multi-room, synchronized playback)
- Lossless ALAC audio (no re-compression)
- Metadata passthrough (track info, album art)
- MQTT integration for Home Assistant automation
- Active development with weekly commits

**Docker Compose Deployment:**

```yaml
version: "3.8"
services:
  shairport-sync:
    image: mikebrady/shairport-sync:latest
    container_name: shairport-sync
    network_mode: host
    devices:
      - /dev/snd:/dev/snd
    environment:
      - AIRPLAY_NAME=Living Room AirPlay
      - OUTPUT_BACKEND=alsa
      - PULSE_SERVER=unix:/run/user/1000/pulse/native
    volumes:
      - ./shairport-sync.conf:/etc/shairport-sync.conf:ro
    restart: unless-stopped
```

The configuration file (`shairport-sync.conf`) offers extensive control over audio processing. You can set up convolution filters for room correction, configure hardware mixers for volume control, and even integrate with MQTT brokers for smart home automation. Shairport Sync can trigger Home Assistant automations when playback starts or stops — useful for powering amplifiers on and off automatically.

For AirPlay 2 multi-room setups, Shairport Sync synchronizes playback across multiple devices with sub-millisecond accuracy. The timing is handled by NTP, ensuring all speakers in different rooms stay perfectly in sync. Unlike Bluetooth, there are no range limitations — any device on the LAN can stream.

## balenaSound: All-in-One Multi-Protocol Streaming

balenaSound takes a different approach: it bundles Spotify Connect, AirPlay, Bluetooth (A2DP), and multi-room audio into a single deployable stack. Built for balenaOS (a lightweight Linux for embedded devices), it uses Docker Compose internally to orchestrate multiple services.

**Key Strengths:**
- Supports Spotify, AirPlay, and Bluetooth simultaneously
- Built-in Snapcast multi-room server and client
- Web interface for configuration and status
- Handles USB DACs, HDMI audio, and I2S DACs
- Balena Cloud management dashboard (optional)

**Docker Compose Deployment (standalone, without Balena):**

```yaml
version: "3.8"
services:
  # Core audio output
  audio:
    image: balenablocks/audio:latest
    container_name: balenasound-audio
    privileged: true
    ports:
      - "4317:4317"

  # Spotify Connect plugin
  spotify:
    image: balenablocks/spotify:latest
    container_name: balenasound-spotify
    network_mode: host
    privileged: true
    environment:
      - SPOTIFY_NAME=Living Room
      - SPOTIFY_BITRATE=320

  # AirPlay plugin
  airplay:
    image: balenablocks/airplay:latest
    container_name: balenasound-airplay
    network_mode: host
    privileged: true
    environment:
      - AIRPLAY_NAME=Living Room AirPlay

  # Bluetooth plugin
  bluetooth:
    image: balenablocks/bluetooth:latest
    container_name: balenasound-bluetooth
    network_mode: host
    privileged: true
    cap_add:
      - NET_ADMIN

  # Multi-room server
  multiroom-server:
    image: balenablocks/multiroom-server:latest
    container_name: balenasound-multiroom-server
    ports:
      - "1704:1704"
      - "1705:1705"
      - "1780:1780"
    restart: on-failure

  # Multi-room client
  multiroom-client:
    image: balenablocks/multiroom-client:latest
    container_name: balenasound-multiroom-client
    restart: on-failure

  restart: unless-stopped
```

balenaSound shines when you need maximum protocol coverage from a single device. Guests can connect via Bluetooth without installing any app, household members use Spotify Connect, and Apple users stream via AirPlay — all to the same speaker. The multi-room support via Snapcast means one balenaSound instance acts as the server while additional Raspberry Pis serve as satellite clients, creating a synchronized whole-home audio system.

The trade-off is complexity. Running six containers per device consumes more resources than single-protocol alternatives. For a Raspberry Pi 4 with 4 GB RAM, this is manageable; on a Raspberry Pi Zero, it would struggle.

## Why Self-Host Your Audio Streaming?

When you use a commercial smart speaker, you are locked into that manufacturer's ecosystem. Sonos speakers require the Sonos app. Amazon Echo devices phone home to Amazon's servers for every command. Google Nest speakers stop receiving updates after a few years, becoming e-waste. A self-hosted audio receiver uses your existing speakers and gives you complete control over the software stack.

With Shairport Sync, your 20-year-old stereo receiver becomes an AirPlay 2 endpoint that works identically to a $300 HomePod for music playback. LibreSpot turns any old laptop into a Spotify Connect speaker indistinguishable from a dedicated Sonos unit. The audio quality from a good DAC connected to your own amplifier will typically exceed that of mid-range smart speakers — and you are not sending usage data to any cloud service.

For tips on building a complete self-hosted music ecosystem, see our [full music streaming comparison guide](../2026-05-01-koel-vs-mopidy-vs-snapcast-self-hosted-music-streaming-guide/). If you are interested in enhancing audio quality further, our [audio DSP and room correction guide](../2026-06-07-self-hosted-audio-dsp-room-correction-camilladsp-brutefir-lsp/) covers digital signal processing for your setup. For serving your media library, check out our [self-hosted music server comparison](../navidrome-vs-funkwhale-vs-airsonic-self-hosted-music-guide/).

## Deployment Best Practices

When deploying any of these tools, consider these practical tips:

**Audio Hardware:** Use a USB DAC (digital-to-analog converter) rather than the Raspberry Pi's built-in 3.5mm jack. The built-in output uses PWM (pulse-width modulation) which introduces audible noise. A $10 USB DAC dramatically improves audio quality. For higher-end setups, I2S DACs like the HiFiBerry or IQaudio DAC Pro connect directly to the GPIO header and provide cleaner analog output.

**Network Configuration:** All three tools work best on wired Ethernet for the server device. Wi-Fi introduces latency variations that can cause playback glitches with synchronized multi-room audio. If using Wi-Fi, 5 GHz is strongly preferred over 2.4 GHz.

**Firewall Rules:** These services use mDNS (multicast DNS, port 5353) for device discovery. Ensure your router does not block mDNS between VLANs if your audio device is on a separate IoT network. LibreSpot and AirPlay also require the client device (phone/laptop) to be on the same broadcast domain or have an mDNS reflector configured.

**Home Assistant Integration:** Both Shairport Sync and balenaSound expose MQTT topics for playback status. You can create automations like "when AirPlay starts playing, turn on the amplifier" or "when Spotify stops, turn off speakers after 5 minutes of inactivity." This transforms a passive audio receiver into a smart home component.

## Choosing the Right Tool

For **Spotify-only households**, LibreSpot is the clear winner. It is the lightest, fastest, and most Spotify-native solution.

For **Apple households**, Shairport Sync provides the most complete AirPlay experience with full AirPlay 2 multi-room support and seamless integration with iOS/macOS devices.

For **mixed-device households** or **guest-friendly setups**, balenaSound covers all protocols simultaneously, making it the most versatile option.

For **multi-room setups**, combine balenaSound (server) with Shairport Sync satellites or use balenaSound's built-in Snapcast integration. Shairport Sync's AirPlay 2 multi-room also works well within the Apple ecosystem.

## FAQ

### Can I run multiple receivers on the same Raspberry Pi?

Yes, but with caveats. LibreSpot and Shairport Sync can run side-by-side as separate Docker containers, each using different audio output names. However, only one can access the ALSA hardware device at a time unless you use a software mixer like PulseAudio or PipeWire. balenaSound solves this by using Snapcast as its internal mixer — all protocols feed into Snapcast, which outputs to the hardware.

### Do I need Spotify Premium for LibreSpot?

Yes. Spotify Connect is a premium-tier feature that requires a Spotify Premium subscription. LibreSpot uses the same librespot library that powers Spotify's official Connect SDK, and it authenticates through Spotify's OAuth system, which enforces the premium requirement.

### Does Shairport Sync work with iOS 18+ and macOS Sequoia?

Yes. Shairport Sync actively tracks Apple's AirPlay protocol changes. The project maintains compatibility with the latest iOS and macOS releases. The AirPlay 2 implementation supports synchronized multi-room playback, HomeKit integration, and the full ALAC audio codec. Because it implements the protocol independently (not using reverse-engineered private APIs), it is resistant to minor protocol updates.

### Can Bluetooth audio quality match AirPlay or Spotify Connect?

Bluetooth A2DP uses lossy SBC encoding by default, which is inferior to AirPlay's lossless ALAC or Spotify's 320 kbps Ogg Vorbis. However, if both the source device and receiver support aptX or LDAC codecs, Bluetooth can approach near-lossless quality. balenaSound's Bluetooth plugin supports standard A2DP; higher-quality Bluetooth codecs are hardware-dependent and not universally available on Raspberry Pi Bluetooth chipsets.

### How do I add multi-room audio to an existing setup?

For AirPlay 2 multi-room, deploy Shairport Sync on multiple Raspberry Pis — Apple's Home app will see them as individual AirPlay 2 speakers that can be grouped. For protocol-agnostic multi-room, use Snapcast (which balenaSound includes). Snapcast synchronizes playback across multiple clients using a client-server model: one device acts as the Snapcast server (capturing audio), and satellite devices run Snapcast clients. All clients play in perfect sync using NTP-timed buffers.

---

**💰 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — the world's largest prediction market platform. From election outcomes to technology regulation timelines, you can stake on anything. Unlike gambling, this is a genuine information market: the more you know, the better your odds. I've earned consistently by predicting technology-related event trends. Sign up with my referral link: [Polymarket.com](https://polymarket.com/?r=fc8a0)**

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Bluetooth Audio Receivers: LibreSpot vs Shairport Sync vs balenaSound",
  "description": "Comprehensive comparison of self-hosted wireless audio receivers for Raspberry Pi and Linux: LibreSpot (Spotify Connect), Shairport Sync (AirPlay), and balenaSound (multi-protocol). Includes Docker Compose configs, multi-room setup, and hardware recommendations.",
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
      "url": "https://pistack.xyz/logo.png"
    }
  }
}
</script>
