---
title: "DIY Telescope Mount GOTO Systems: OnStep vs OpenAstroTracker vs EQMOD for Self-Hosted Astronomy Control"
date: "2026-06-06"
tags: ["astronomy", "telescope", "goto", "diy-electronics", "stepper-motor", "raspberry-pi", "astrophotography"]
draft: false
---

A telescope mount that automatically finds and tracks celestial objects transforms amateur astronomy. Instead of star-hopping with finder charts, you select a target on your phone or laptop and the mount slews to it, then tracks it precisely as Earth rotates. Three open-source platforms let you build or upgrade your own GOTO system: OnStep (Arduino-based telescope controller), OpenAstroTracker (3D-printed star tracker), and EQMOD (ASCOM driver for commercial equatorial mounts).

This guide compares all three, covering hardware requirements, software setup, and the self-hosted control interfaces that put a planetarium in your browser.

## How Telescope GOTO Systems Work

A GOTO system needs three things: knowledge of where it's pointing (alignment), a catalog of celestial coordinates (RA/Dec), and motors to move the mount. The alignment process is the clever part — you point the telescope at 2–3 known bright stars, and the system calculates its orientation in 3D space. From there, converting any celestial coordinate to motor steps is pure geometry.

All three platforms use stepper motors (for precise angular positioning) and microcontrollers that handle the real-time pulse generation. The self-hosted part is the control interface — a web server, INDI driver, or ASCOM driver that accepts commands from planetarium software like Stellarium, KStars, or SkySafari.

## Comparison: OnStep vs OpenAstroTracker vs EQMOD

| Feature | OnStep | OpenAstroTracker | EQMOD |
|---------|--------|------------------|-------|
| **GitHub Stars** | 588 | 1,092 | Part of ASCOM Platform |
| **Primary Role** | Universal telescope GOTO controller | 3D-printed camera star tracker | ASCOM driver for SkyWatcher mounts |
| **Web Interface** | OnStep Web Server (WiFi) | OAT Web GUI (WiFi) | None (requires ASCOM client) |
| **Mount Compatibility** | Any mount (EQ, Alt-Az, fork) | Custom 3D-printed mount | SkyWatcher EQ mounts (EQ3–EQ8) |
| **Motor Type** | Stepper (any NEMA) | 28BYJ-48 stepper | Stock stepper/servo |
| **MCU Platform** | Teensy, ESP32, STM32 | Arduino Mega + RAMPS | PC (ASCOM), RPi (INDI bridge) |
| **Tracking Accuracy** | < 1 arcsec (with PEC) | ~5 arcsec (wide-field AP) | Depends on mount mechanics |
| **Auto-Guiding** | ST4 port + pulse guiding | None (tracker only) | ST4 + pulse guiding |
| **License** | GPL-3.0 | GPL-3.0 | Open source |
| **Self-Hosted Control** | WiFi web + INDI + ASCOM | WiFi web + standalone | INDI/ASCOM drivers |

## OnStep: Universal Telescope Controller

OnStep is Howard Dutton's open-source telescope controller that transforms any mount — from a wobbly EQ1 to a professional observatory pier — into a computer-controlled GOTO system. It runs on affordable microcontrollers (ESP32 is the current recommendation) and drives stepper motors through standard drivers (TMC2130, TMC5160).

**Key strengths:**
- **Mount-agnostic**: Supports equatorial (GEM, fork), alt-azimuth, and Dobsonian mounts
- **Web-based control**: OnStep's built-in WiFi web server shows a sky map, catalog browser, and alignment wizard
- **Planetarium integration**: INDI driver for KStars/Ekos on Linux, ASCOM driver for Windows, LX200 protocol for SkySafari on mobile
- **Advanced features**: Periodic Error Correction (PEC), limit sensors, focuser control, rotator support

**Self-hosted control architecture with OnStep:**

```
┌──────────────────────────────────────────────────────┐
│  Raspberry Pi (KStars/Ekos)                           │
│  ┌──────────────┐    ┌────────────┐                  │
│  │ KStars       │───▶│ INDI       │                  │
│  │ Planetarium   │    │ Server     │                  │
│  └──────────────┘    └─────┬──────┘                  │
│                             │ WiFi/USB                │
└─────────────────────────────┼────────────────────────┘
                               │
┌──────────────────────────────┼────────────────────────┐
│  OnStep Controller (ESP32)   │                         │
│  ┌──────────────┐    ┌──────▼──────┐    ┌──────────┐ │
│  │ Web Server   │    │ LX200       │    │ Motor    │ │
│  │ :80          │    │ Protocol    │    │ Driver   │ │
│  └──────────────┘    └─────────────┘    └────┬─────┘ │
│                                               │       │
│                                        ┌──────▼──────┐ │
│                                        │ RA Stepper  │ │
│                                        │ Dec Stepper │ │
│                                        └─────────────┘ │
└────────────────────────────────────────────────────────┘
```

## OpenAstroTracker: 3D-Printed Wide-Field Tracker

OpenAstroTracker (OAT) is a fully 3D-printed camera tracking mount designed for wide-field astrophotography. Unlike OnStep (which retrofits existing mounts), OAT is a complete hardware+software system you print and assemble yourself.

**Key strengths:**
- **100% 3D-printable**: Download STL files, print on any FDM printer, assemble with common hardware
- **Web GUI over WiFi**: Built-in web interface for polar alignment, target selection, and tracking control — works from any phone or tablet
- **Polar alignment assistant**: Software-guided polar alignment using the built-in camera preview
- **Low cost**: Total BOM around $50–80 (Arduino Mega, RAMPS 1.4, two 28BYJ-48 steppers, bearings, threaded rod)
- **AutoPA**: Experimental feature that automates polar alignment by plate-solving camera images

**OpenAstroTracker Docker-based development environment:**

```bash
# Clone the repository
git clone https://github.com/openastrotech/OpenAstroTracker.git
cd OpenAstroTracker

# Install PlatformIO for firmware compilation
pip install platformio
pio run -e mega2560

# Upload to Arduino Mega
pio run -e mega2560 --target upload
```

Once flashed, OAT creates its own WiFi access point. Connect your phone to "OAT-WiFi" and browse to `http://192.168.4.1` for the full control interface. The web UI includes a sky map, target catalog, tracking status, and polar alignment helper.

## EQMOD: ASCOM Control for SkyWatcher Mounts

EQMOD is the veteran platform for controlling SkyWatcher equatorial mounts (EQ3, EQ5, HEQ5, EQ6, EQ8) via computer. Unlike OnStep and OAT (which replace the mount's control board), EQMOD replaces the hand controller — the mount's motors and encoders remain stock.

**Key strengths:**
- **Seamless ASCOM integration**: Works with every Windows astronomy application (Stellarium, Cartes du Ciel, N.I.N.A., SharpCap)
- **Custom tracking rates**: Solar, lunar, cometary, and satellite tracking — not just sidereal
- **Pointing model**: Builds a multi-star alignment model that compensates for mount mechanical errors
- **Gamepad support**: Control the mount with an Xbox controller for visual observing

**Running EQMOD on Linux via INDI (self-hosted):**

```bash
# Install INDI with EQMOD driver
sudo apt-get install indi-full indi-eqmod

# Start INDI server with EQMOD driver
indiserver -v indi_eqmod_telescope

# Connect from KStars:
# Devices → Device Manager → EQMod Mount → Connect
```

EQMOD communicates with the mount via an EQDirect cable (USB-to-TTL serial adapter connected directly to the mount's hand controller port — about $15 in parts). The INDI EQMOD driver on Linux provides the same functionality as the Windows ASCOM driver, making it fully self-hosted on a Raspberry Pi at the telescope.

## Why Self-Host Your Telescope Control?

A self-hosted GOTO system running on a Raspberry Pi at the telescope gives you complete control from any device on your network (or over a VPN from anywhere). You can start an imaging sequence from your couch, check progress from your phone, and never touch the telescope — critical for astrophotography where even walking near the mount can blur 5-minute exposures.

The open-source approach saves significant money. A commercial GOTO equatorial mount costs $800–2,500. Converting a used manual mount with OnStep costs about $100 (ESP32 + two stepper motors + drivers) and often outperforms the commercial equivalent in tracking accuracy when properly tuned. OAT is even cheaper — $50–80 for a complete tracking mount, ideal for wide-field Milky Way and constellation photography.

For the full astrophotography automation stack, see our guide on [self-hosted astrophotography with INDI, KStars, and PHD2](../2026-06-05-self-hosted-astrophotography-automation-indi-kstars-phd2-guide/) which covers the software layer that controls these mounts. For precise time synchronization needed for telescope tracking, check our [GPS-based NTP reference clock guide](../2026-05-18-self-hosted-ntp-reference-clock-gps-pps-ntpsec-chrony-linuxptp-guide/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "DIY Telescope Mount GOTO Systems: OnStep vs OpenAstroTracker vs EQMOD for Self-Hosted Astronomy Control",
  "description": "Compare OnStep, OpenAstroTracker, and EQMOD for self-hosted DIY telescope GOTO systems. Arduino and ESP32-based controllers, 3D-printed star trackers, and ASCOM/INDI integration for astrophotography.",
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

## FAQ

### Can I use OnStep to upgrade my existing manual telescope mount?

Yes, that's OnStep's primary use case. You keep the mount's mechanical structure but replace (or add) stepper motors and the control board. Most manual equatorial mounts (EQ1 through EQ5 class) can be converted. OnStep's configuration generator helps you calculate the correct gear ratios and step angles for your specific mount's worm gears.

### What's the difference between a star tracker and a GOTO mount?

A star tracker (like OpenAstroTracker) only tracks — it follows the sky's rotation for long-exposure photography but can't automatically find targets. A GOTO mount (like an OnStep-upgraded EQ mount) slews to any celestial coordinate on command. Trackers are lighter, simpler, and better for wide-field camera+lens setups. GOTO mounts are essential for deep-sky astrophotography at long focal lengths where manual star-hopping is impractical.

### Do I need autoguiding for astrophotography?

For exposures longer than 30–60 seconds at focal lengths above 200mm, yes. Even the best mount has periodic error from worm gear imperfections. An autoguider camera + small guide scope locks onto a star and sends micro-corrections to the mount. OnStep's ST4 port accepts guide camera signals directly. EQMOD supports pulse guiding via ASCOM. OpenAstroTracker doesn't support autoguiding — it's designed for wide-field work where periodic error is below the image scale.

### How accurate is OnStep's tracking compared to commercial mounts?

With TMC2130/TMC5160 stepper drivers (256 microsteps) and proper periodic error correction (PEC), OnStep achieves sub-arcsecond tracking accuracy — matching or exceeding commercial mounts in the $1,500–3,000 range. The limiting factor is your mount's mechanical quality, not the electronics. On a high-end mount like an EQ6-R, OnStep is indistinguishable from the stock SynScan controller in pointing and tracking accuracy.

### Can I control my telescope remotely over the internet?

Yes. Run KStars/Ekos on a Raspberry Pi at the telescope with INDI server connecting to your OnStep or EQMOD mount. Access the Pi via VNC or the Ekos web manager from anywhere. For remote observatories, add a VPN (WireGuard or ZeroTier) and a power relay (for remote power cycling). The Raspberry Pi handles all timing-critical operations locally; your remote connection is just for monitoring and target selection.

### What mount should I choose for a first DIY GOTO project?

Start with a used SkyWatcher EQ3-2 or Celestron CG-4 — they're common, inexpensive ($100–200), and well-documented for OnStep conversions. Pair it with an ESP32, two TMC2130 drivers, and NEMA 17 stepper motors. Total conversion cost: about $100. This setup will reliably carry a small refractor (80mm) or DSLR+lens for both visual observing and beginner astrophotography.

---

**💰 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — it's the world's largest prediction market platform where you can bet on everything from election outcomes to technology regulation timelines. Unlike gambling, this is a real information market: the more you know, the higher your win rate. I've profited significantly by predicting technology-related event outcomes. Sign up with my referral link:** [Polymarket.com](https://polymarket.com/?r=fc8a0)
