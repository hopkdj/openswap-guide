---
title: "Self-Hosted RTK GPS Base Stations: RTKLIB vs RTKBase vs CentipedeRTK for Centimeter-Accurate Positioning"
date: "2026-06-06"
tags: ["gps", "gnss", "rtk", "geolocation", "surveying", "precision-agriculture", "raspberry-pi"]
draft: false
---

Real-Time Kinematic (RTK) GPS delivers centimeter-level positioning accuracy — a massive leap from the 3–5 meter accuracy of standard GPS. Whether you're surveying land, guiding autonomous tractors, or building drone navigation systems, an RTK base station is the foundation. The good news? You can run your own self-hosted RTK base station on affordable single-board computers like the Raspberry Pi, with open-source software that rivals commercial systems costing thousands of dollars.

In this guide, we compare three leading open-source RTK base station platforms: RTKLIB (the veteran Swiss Army knife of GNSS processing), RTKBase (a modern web-based station manager), and CentipedeRTK (a collaborative low-cost RTK network).

## RTK GPS Explained: How Base Stations Deliver Centimeter Accuracy

Standard GPS receivers calculate position by measuring signal travel time from satellites. Atmospheric interference, satellite orbit errors, and clock drift introduce 3–5 meters of error. RTK fixes this with a clever trick: a **base station** at a precisely known location measures the error in real time and broadcasts **correction data** to nearby **rover** receivers. The rover applies these corrections, achieving 1–2 centimeter accuracy.

An RTK base station consists of three components:
- A GNSS receiver (u-blox ZED-F9P is the community standard)
- Correction computation software (running on a Raspberry Pi or similar SBC)
- A communication link (NTRIP caster over Wi-Fi, LoRa, or cellular)

## Comparison: RTKLIB vs RTKBase vs CentipedeRTK

| Feature | RTKLIB | RTKBase | CentipedeRTK |
|---------|--------|---------|--------------|
| **GitHub Stars** | 3,049 | 734 | 54 (network) |
| **Primary Role** | GNSS processing toolkit | RTK base station manager | Collaborative RTK network |
| **Web Interface** | RTKPLOT desktop GUI | Built-in web dashboard | Web-based network map |
| **NTRIP Caster** | Yes (STRSVR) | Yes (built-in) | Uses external casters |
| **Base Station Setup** | Manual configuration | One-command installer | Pre-configured image |
| **Correction Formats** | RTCM 2.x/3.x, BINEX, RINEX | RTCM 3.x | RTCM 3.x |
| **Multi-Constellation** | GPS, GLONASS, Galileo, BeiDou, QZSS | GPS, GLONASS, Galileo, BeiDou | GPS, GLONASS, Galileo, BeiDou |
| **Raspberry Pi Optimized** | Requires compilation | Yes (Raspbian package) | Yes (pre-built image) |
| **Community Size** | Very large (academic + industry) | Growing (maker community) | French/European collaborative |
| **License** | BSD 2-Clause | AGPL-3.0 | Open (various) |

## RTKLIB: The Swiss Army Knife of GNSS

RTKLIB is the grandfather of open-source GNSS processing. Developed by Tomoji Takasu, it's a comprehensive toolkit that handles everything from raw GNSS data logging to real-time RTK positioning and post-processing. It's the gold standard for academic research and professional surveying.

**Key strengths:**
- Supports virtually every GNSS receiver and format
- Powerful post-processing with RTKPOST for centimeter-accuracy after the fact
- Real-time RTK via RTKNAVI with built-in NTRIP caster (STRSVR)
- Extensive logging and analysis tools

**Installation on Raspberry Pi:**

```bash
# Install dependencies
sudo apt-get update
sudo apt-get install -y build-essential gfortran libblas-dev liblapack-dev

# Clone and compile RTKLIB
git clone https://github.com/tomojitakasu/RTKLIB.git
cd RTKLIB/app
make -j4

# Launch RTKNAVI for real-time positioning
cd rtklib_2.4.3/app/rtknavi/gcc
./rtknavi
```

## RTKBase: Purpose-Built for Base Station Management

RTKBase takes a different approach — rather than being a general toolkit, it's purpose-built to turn a Raspberry Pi + u-blox ZED-F9P into a fully self-hosted RTK base station with a web dashboard. The project by Stéphane Péneau (Stefal) has become the go-to choice for makers and precision agriculture enthusiasts.

**Key strengths:**
- Web-based dashboard showing satellite count, base position, and data throughput
- One-command installer handles everything: `curl -sL setup.rtkbase.com | sudo bash`
- Automatic base position surveying and averaging
- Built-in NTRIP caster for serving corrections to rovers
- Real-time status monitoring via web UI at `http://<pi-ip>:8080`

**Deployment with Docker Compose:**

```yaml
version: '3'
services:
  rtkbase:
    image: stefal/rtkbase:latest
    container_name: rtkbase
    devices:
      - /dev/ttyACM0:/dev/ttyACM0
    ports:
      - "8080:80"
      - "2101:2101"
    volumes:
      - rtkbase_data:/var/www/html/data
    environment:
      - TZ=UTC
      - RTKBASE_PORT=/dev/ttyACM0
    restart: unless-stopped

volumes:
  rtkbase_data:
```

After starting the container, access the web dashboard to configure your base station. RTKBase automatically starts surveying its position (averaging over time for maximum accuracy) and begins broadcasting RTCM3 corrections on port 2101.

## CentipedeRTK: Collaborative RTK Networks

CentipedeRTK (Centipède) is a French initiative building a low-cost collaborative RTK network. The idea is simple: volunteers deploy RTK base stations, and the community accesses corrections for free. It's the open-source equivalent of commercial RTK networks that charge subscription fees.

**Key strengths:**
- Community-driven network of 200+ base stations across France and Europe
- Pre-built SD card images for Raspberry Pi with everything configured
- Central web portal showing active base stations on a map
- Free NTRIP access for anyone within range (~20 km of a base station)

The CentipedeRTK client software is lighter-weight than RTKBase, designed to be a reliable "set and forget" base station node. It uses standard RTCM3 corrections and works with any NTRIP-compatible rover.

## Why Self-Host Your RTK Base Station?

Commercial RTK correction services like Trimble VRS or Leica SmartNet charge $1,000–3,000 per year for subscription access. A self-hosted RTK base station costs about $200–300 in hardware (Raspberry Pi 4 + u-blox ZED-F9P + antenna) with zero recurring fees. For farms, construction sites, or research labs that need reliable centimeter-level positioning, the payback period is measured in weeks, not years.

Beyond cost savings, self-hosting gives you control. You own the raw GNSS data, you decide who accesses your corrections, and you're not dependent on a third-party service's uptime. For precision agriculture, your base station keeps working even when cellular networks are spotty — if you pair it with a local LoRa radio link to your rovers, the system works entirely offline.

Data sovereignty matters too. Commercial RTK services log every position fix your rovers request. With a self-hosted base station, your location data stays on your network. For sensitive applications like archaeological surveying, military engineering, or competitive drone racing, this privacy is non-negotiable.

For broader geolocation projects, see our guide on [self-hosted GPS tracking with Traccar and OwnTracks](../2026-04-20-dawarich-vs-owntracks-vs-traccar-self-hosted-gps-tracking-guide-2026/). For marine navigation applications using GPS and AIS data, our [OpenCPN and Signal K comparison](../2026-06-05-self-hosted-marine-navigation-opencpn-signalk-avnav-guide/) covers nautical positioning.

## Deployment Architecture

A typical RTK base station deployment has three layers:

```
┌─────────────────────────────────────────────────────┐
│                  RTK Base Station                    │
│  ┌──────────┐    ┌──────────────┐    ┌───────────┐  │
│  │ GNSS     │───▶│ Raspberry Pi │───▶│ NTRIP     │  │
│  │ Receiver │    │ (RTKBase/    │    │ Caster    │  │
│  │ (F9P)    │    │  RTKLIB)     │    │ :2101     │  │
│  └──────────┘    └──────────────┘    └─────┬─────┘  │
│                          │                  │        │
│                Web Dashboard            TCP/IP       │
│                :8080                    or LoRa       │
└─────────────────────────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         ┌────────┐  ┌────────┐  ┌────────┐
         │ Rover 1│  │ Rover 2│  │ Rover 3│
         │(Tractor)│  │(Drone) │  │(Survey)│
         └────────┘  └────────┘  └────────┘
```

The base station antenna should have a clear sky view, preferably mounted on a roof or pole. The Raspberry Pi can be indoors, connected to the antenna via a coaxial cable (keep it under 10 meters to avoid signal loss). For farms with large fields, consider multiple base stations in a networked configuration.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted RTK GPS Base Stations: RTKLIB vs RTKBase vs CentipedeRTK for Centimeter-Accurate Positioning",
  "description": "Compare RTKLIB, RTKBase, and CentipedeRTK for self-hosted centimeter-accurate GPS base stations. Deploy on Raspberry Pi with Docker, support multi-constellation GNSS, and serve RTCM3 corrections via NTRIP for precision agriculture and drone surveying.",
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

### What GNSS receiver do I need for an RTK base station?

The u-blox ZED-F9P is the community standard for budget RTK base stations. It costs around $200 and supports L1/L2 bands from GPS, GLONASS, Galileo, and BeiDou. For professional applications, the Septentrio mosaic-X5 or Trimble BD990 offer better multi-path rejection and L5 band support but cost $500–1,500. All three work with RTKBase and RTKLIB.

### How far can an RTK base station provide corrections?

Under ideal conditions (open sky, good antenna), a single base station provides reliable centimeter accuracy out to about 10–15 km. Beyond that, atmospheric differences between base and rover degrade accuracy. For coverage beyond 20 km, you need a networked RTK (NRTK) solution that interpolates corrections from multiple base stations — this is what commercial networks like CentipedeRTK provide.

### Do I need a static IP address for my base station?

Not necessarily. If your rover is on the same local network, use the base station's LAN IP. For remote access, you can use ZeroTier or Tailscale to create a VPN between base and rover. For serving corrections to the public internet, a static IP or dynamic DNS (DuckDNS, afraid.org) with port forwarding is the simplest approach.

### Can I use RTK for drone surveying?

Yes, RTK dramatically improves drone mapping accuracy. Instead of relying on ground control points (GCPs), an RTK-enabled drone receives real-time corrections and tags each aerial photo with centimeter-accurate position data. Combined with photogrammetry software like OpenDroneMap (ODM, 6,139 stars on GitHub), you can produce survey-grade orthomosaic maps with minimal ground control.

### What's the difference between RTKLIB and RTKBase for a beginner?

RTKBase is dramatically easier to set up — the one-command installer gets a base station running in about 10 minutes. RTKLIB is more powerful (post-processing, multiple receiver support, advanced analysis) but has a steeper learning curve. Start with RTKBase for your first base station. Graduate to RTKLIB when you need post-processing or support for non-u-blox receivers.

### How do I verify my RTK base station is providing accurate corrections?

Place your rover at a known survey point (or Google Maps coordinate) and check that the RTK-fixed position matches within 2–3 cm. RTKBase's web dashboard shows the "Fix Quality" indicator — you want "FIX" (not "FLOAT"). Run the base station for at least 24 hours and check the position scatter plot in RTKBase's web UI; it should converge to a tight cluster.

---

**💰 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — it's the world's largest prediction market platform where you can bet on everything from election outcomes to technology regulation timelines. Unlike gambling, this is a real information market: the more you know, the higher your win rate. I've profited significantly by predicting technology-related event outcomes. Sign up with my referral link:** [Polymarket.com](https://polymarket.com/?r=fc8a0)
