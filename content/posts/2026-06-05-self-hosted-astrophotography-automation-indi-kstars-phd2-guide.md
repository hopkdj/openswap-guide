---
title: "Self-Hosted Astrophotography Automation: INDI Server vs KStars/Ekos vs PHD2"
date: "2026-06-05"
tags: ["astrophotography", "astronomy", "raspberry-pi", "telescope", "imaging", "automation", "linux"]
draft: false
---

## What Is Astrophotography Automation?

Astrophotography automation turns a complex multi-step imaging workflow into a coordinated, repeatable process. Instead of manually adjusting your telescope mount, focusing, and triggering exposures throughout a cold night, you run a self-hosted server — typically on a Raspberry Pi mounted at the telescope — that orchestrates camera control, mount tracking, autoguiding, and image capture.

The three most important open-source components in this ecosystem are **INDI Server** (the hardware abstraction layer), **KStars/Ekos** (the full observatory control suite), and **PHD2** (the precision autoguiding engine). While they work together in practice, each represents a distinct architectural approach worth understanding if you are building a self-hosted astrophotography rig.

## INDI Server: The Universal Hardware Abstraction Layer

[INDI](https://indilib.org/) (Instrument Neutral Distributed Interface) is the backbone of Linux-based astrophotography. It runs as a network daemon — typically on a Raspberry Pi or Intel NUC at the telescope — and exposes every hardware device (camera, mount, focuser, filter wheel, dome) over a standard TCP/IP protocol.

```bash
# Install INDI on Raspberry Pi (Raspberry Pi OS / Ubuntu)
sudo apt update
sudo apt install indi-full indi-gphoto indi-asi indi-qhy
# Start the INDI server
indiserver -v indi_simulator_telescope indi_simulator_ccd
```

You connect to INDI from any client — KStars on your desktop indoors, a web dashboard, or even a custom Python script over the network. This client-server architecture means you can leave the telescope hardware outside in the cold while controlling everything from your warm living room over WiFi.

INDI supports over 200 device drivers, maintained in `indilib/indi` (439 stars on GitHub) and `indilib/indi-3rdparty` (151 stars). The protocol is fully documented, making it straightforward to write custom drivers for unusual hardware combinations.

## KStars/Ekos: The Complete Observatory Suite

[KStars](https://kde.org/applications/education/org.kde.kstars) (274 stars) is a desktop planetarium program from the KDE project, and its Ekos module transforms it into a full observatory automation tool. While KStars runs as a desktop application, it connects to the INDI server over the network — the actual hardware control happens server-side on the Raspberry Pi.

Ekos provides a visual scheduler where you queue targets, set exposure sequences, configure dithering, and define meridian flip behavior. It can run an entire imaging session unattended: plate-solve to center the target, autofocus, start guiding with PHD2, capture light frames, and park the mount at dawn.

```bash
# Install KStars on Ubuntu/Debian
sudo apt install kstars
# Or via Flatpak for latest version
flatpak install flathub org.kde.kstars
```

The key architectural insight: KStars is the "brain" (planning and orchestration) while INDI is the "nervous system" (hardware communication). This separation means you can replace either component — use a different client like CCDciel (56 stars) or a custom web dashboard instead of KStars, while keeping the same INDI server running on the telescope.

## PHD2: Precision Autoguiding

[PHD2](https://openphdguiding.org/) (292 stars) is the specialized tool for autoguiding — using a secondary guide camera and small guide scope to lock onto a star and send micro-corrections to the mount. Even the best equatorial mounts have periodic error; PHD2 corrects for this hundreds of times per second, enabling multi-minute exposures with pinpoint stars.

```bash
# Install PHD2 on Ubuntu/Debian
sudo apt-add-repository ppa:pch/phd2
sudo apt update
sudo apt install phd2
```

PHD2 connects to INDI for its camera and mount communication, but it runs its own guiding algorithms independently. You can use it standalone (for simple guiding-only setups) or integrated within Ekos, where Ekos manages the overall session and PHD2 handles guiding as a sub-component.

## Comparison Table

| Feature | INDI Server | KStars/Ekos | PHD2 |
|---------|------------|-------------|------|
| Role | Hardware driver server | Observatory automation suite | Autoguiding engine |
| Stars (GitHub) | 439 | 274 | 292 |
| Architecture | Network daemon (TCP/IP) | Desktop app + INDI client | Standalone + INDI client |
| Runs headless? | Yes (Raspberry Pi) | No (needs display) | No (needs display) |
| Scheduling | No | Yes, full queue | No |
| Plate solving | Via driver | Built-in ASTAP integration | No |
| Autoguiding | Pass-through | Pass-through | Multi-star, predictive |
| Multi-camera | Yes (multiple CCDs) | Yes | Single guide camera |
| Docker support | Community images | Flatpak preferred | PPA/native |
| Learning curve | Moderate | Moderate-High | Low |

## Hardware Setup and Connectivity Options

A typical self-hosted astrophotography rig consists of a Raspberry Pi 4/5 running the INDI server, connected via USB to all hardware devices. The Pi is mounted on the telescope or tripod, powered by a 12V battery or mains adapter. You connect to it over WiFi from your indoor computer running KStars.

For observatory-grade setups, consider using a mini PC (Intel NUC, Beelink) with more RAM and storage, running Ubuntu Server with INDI and all capture tools. A dedicated WiFi bridge or Ethernet-over-power adapter ensures reliable connectivity over longer distances. Some astrophotographers even use 4G/5G routers for remote desert imaging sites, controlling the entire rig via VPN.

## Why Self-Host Your Astrophotography Rig?

Running your own astrophotography server gives you complete control over every aspect of the imaging pipeline. Unlike commercial all-in-one devices (ASIAir, StellarMate OS), a self-hosted setup with INDI lets you mix and match any hardware combination — ZWO cameras with QHY filter wheels, Pegasus focusers with iOptron mounts — without vendor lock-in. The software stack is entirely open-source, meaning you can inspect and modify every line of code that controls your equipment.

Data ownership is another critical factor. Your raw FITS files, calibration frames, and sequence logs stay on your own storage — no cloud uploads, no subscription fees, no platform dependency. If you later want to reprocess three-year-old data with improved algorithms, it is all there on your local NAS.

For related reading, see our guide on [self-hosted wildlife camera monitoring](../2026-06-05-self-hosted-wildlife-camera-bird-monitoring-birdnet-pi-naturewatch-motioneye/) — similar Raspberry Pi outdoor deployment patterns. If you are setting up remote hardware monitoring, check our [bare-metal hardware monitoring guide](../2026-04-23-self-hosted-bare-metal-hardware-monitoring-ipmi-redfish-openbmc-guide-2026/). For precision sensor integration, our [air quality monitoring guide](../2026-06-04-self-hosted-air-quality-monitoring-airrohr-luftdaten-sensor-community-guide/) covers similar environmental sensing patterns.


## Image Capture Workflow and Automation Scripts

A typical unattended imaging session follows a structured pipeline. First, the mount slews to the target and performs a plate solve to verify pointing accuracy. PHD2 calibrates the guide camera and begins guiding corrections. Then the main camera starts a sequence of exposures — each with a defined duration, ISO/gain, and filter setting. Between exposures, the system may dither (shift the mount slightly) to average out fixed-pattern noise during stacking.

INDI scripts written in Python (using `pyindi-client`) can orchestrate complex sequences beyond what the Ekos scheduler supports. For example, alternating between two targets as they cross the meridian, or automatically increasing exposure time as the target rises and sky background darkens. The INDI protocol lets you query sensor temperature, focus position, and guide error in real time — useful for monitoring via a Prometheus/Grafana dashboard if you run an observatory.

For filter wheel automation, INDI drivers handle wheel rotation timing and focus offset compensation for each filter. The complete setup — mount control, camera triggering, filter changes, and focus adjustments — runs entirely on the Raspberry Pi INDI server, with your indoor computer simply monitoring and adjusting the Ekos schedule as needed.
## FAQ

### Do I need all three — INDI, KStars, and PHD2?

For a complete automated setup, yes. INDI handles hardware communication, KStars/Ekos manages the imaging sequence and scheduling, and PHD2 provides precision guiding. For simple unguided wide-field imaging, you can use just INDI + KStars. For guiding-only setups with manual camera control, PHD2 + INDI is sufficient.

### Can INDI run on a Raspberry Pi Zero?

The original Pi Zero struggles with the full INDI stack due to limited RAM (512MB). A Raspberry Pi 3B+ or newer with 1GB+ RAM is recommended. The Pi 4 (4GB) or Pi 5 handles INDI comfortably even with multiple high-resolution cameras.

### Does this work with any telescope mount?

INDI supports virtually every mount protocol: EQMOD for Sky-Watcher, Celestron NexStar, iOptron, Meade, Vixen, Losmandy Gemini, Astro-Physics, and many more. If your mount has a USB or serial port, there is almost certainly an INDI driver for it.

### Is KStars/Ekos the only INDI client option?

No. Alternatives include **CCDciel** (cross-platform, lightweight, 56 GitHub stars), **StellarMate** (commercial Raspberry Pi OS with web dashboard), and **AstroBerry** (free Raspberry Pi image with web-based control). You can also write custom clients using the INDI Python API (`pyindi-client`).

### How do I access my rig remotely over the internet?

Set up a WireGuard or Tailscale VPN between your observatory and home. The INDI server runs on port 7624 by default. With a VPN tunnel, KStars on your home desktop connects to `192.168.1.x:7624` as if the telescope were on your local network. The latency is low enough that guiding corrections work fine over a decent internet connection.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Astrophotography Automation: INDI Server vs KStars/Ekos vs PHD2",
  "description": "Compare INDI Server, KStars/Ekos, and PHD2 for building a self-hosted astrophotography automation rig on Raspberry Pi. Complete guide with Docker install instructions and hardware setup tips.",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
