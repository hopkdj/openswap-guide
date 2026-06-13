---
title: "Self-Hosted Amateur Satellite Tracking: SatNOGS vs Gpredict vs gr-satellites Compared"
date: "2026-06-14"
tags: ["satellite-tracking", "amateur-radio", "sdr", "space", "ground-station", "gnu-radio"]
draft: false
---

## Introduction

Tracking satellites as they pass overhead is one of the most rewarding aspects of amateur radio and space enthusiasm. Whether you want to receive telemetry from CubeSats, decode weather satellite imagery, or communicate through amateur radio satellites like AO-91 and ISS, you need reliable satellite tracking software to know exactly when and where to point your antenna. This guide compares three open-source satellite tracking solutions you can self-host to build your own ground station.

## Quick Comparison Table

| Feature | SatNOGS Network | Gpredict | gr-satellites |
|---------|----------------|----------|---------------|
| **Type** | Web-based network + client | Desktop application | GNU Radio module |
| **Primary Use** | Crowdsourced satellite observations | Real-time tracking & control | Satellite signal decoding |
| **Stars** | 109+ (network) / 66+ (client) | 1,138+ | 943+ |
| **Interface** | Web UI + REST API | GTK+ GUI | GNU Radio Companion |
| **Rotor Control** | Via client | Built-in (hamlib) | External |
| **Docker Support** | Yes | Manual install | Yes (GNU Radio) |
| **Deployment** | Docker Compose | System package | Source/PyBOMBS |
| **License** | AGPL-3.0 | GPL-2.0 | GPL-3.0 |

## SatNOGS Network: Crowdsourced Satellite Monitoring

SatNOGS is an open-source project by the Libre Space Foundation that combines a global network of satellite ground stations with a self-hosted management platform. The system consists of three components: the **SatNOGS Network** (web-based scheduler and observation database), the **SatNOGS Client** (runs on the ground station hardware), and the **SatNOGS DB** (satellite transmitter database).

SatNOGS excels at scheduled, automated observations. Once configured, your ground station can participate in the global network, automatically scheduling passes and uploading observation data that contributes to an open database used by researchers worldwide.

### Docker Compose Setup

```yaml
version: "3"
services:
  satnogs-network:
    image: satnogs/satnogs-network:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://satnogs:satnogs@db/satnogs
      - REDIS_URL=redis://redis:6379
      - SECRET_KEY=your-secret-key-here
    depends_on:
      - db
      - redis
  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=satnogs
      - POSTGRES_PASSWORD=satnogs
      - POSTGRES_DB=satnogs
  redis:
    image: redis:7-alpine
  satnogs-client:
    image: satnogs/satnogs-client:latest
    devices:
      - /dev/bus/usb
    privileged: true
    environment:
      - SATNOGS_NETWORK_API_URL=http://satnogs-network:8000/api/
      - SATNOGS_API_TOKEN=your-api-token
```

## Gpredict: Real-Time Tracking with Hardware Control

Gpredict is a mature, feature-rich satellite tracking application with a GTK-based graphical interface. Originally developed as a desktop application, recent versions support running in headless mode with a built-in HTTP server, making it suitable for self-hosted deployments on a Raspberry Pi or small server.

Gpredict shines for real-time tracking sessions where you need to manually control antenna rotors and radios. Its multi-satellite tracking view, polar plot, and detailed pass predictions make it the go-to choice for operators who want precise timing for satellite contacts.

### Headless Server Setup

```bash
# Install Gpredict on Debian/Ubuntu
sudo apt update && sudo apt install gpredict

# Launch in HTTP server mode for headless operation
gpredict --http-server --port 4533 --host 0.0.0.0

# Or run as a systemd service
cat << 'EOF' | sudo tee /etc/systemd/system/gpredict.service
[Unit]
Description=Gpredict HTTP Server
After=network.target

[Service]
ExecStart=/usr/bin/gpredict --http-server --port 4533 --host 0.0.0.0
Restart=always
User=gpredict
Group=gpredict

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable --now gpredict
```

## gr-satellites: GNU Radio Satellite Decoders

gr-satellites is a GNU Radio out-of-tree module that provides decoder blocks for dozens of amateur satellite telemetry formats. Unlike SatNOGS and Gpredict which focus on tracking and scheduling, gr-satellites handles the signal processing side — demodulating and decoding the actual data transmitted by satellites.

It supports over 80 satellite missions including popular CubeSats like BY70-2, Funcube, and NOAA weather satellites. When paired with an SDR receiver like an RTL-SDR dongle, you can decode real-time telemetry beacons, AX.25 packets, and even image data from satellites.

### Installing gr-satellites

```bash
# Install GNU Radio first
sudo apt install gnuradio gr-osmosdr

# Install gr-satellites from source
git clone https://github.com/daniestevez/gr-satellites.git
cd gr-satellites
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=/usr
make -j$(nproc)
sudo make install
sudo ldconfig

# Verify installation
gnuradio-companion -c /dev/null
# Look for 'Satellites' category in block library
```

## Why Self-Host Your Satellite Ground Station?

Running your own satellite tracking infrastructure gives you complete control over observation schedules and data collection. Unlike cloud-based tracking services that may have usage limits or subscription fees, a self-hosted setup runs indefinitely on a Raspberry Pi with an RTL-SDR dongle — total hardware cost under $100.

The amateur satellite community thrives on distributed ground station networks. Every new station contributing to SatNOGS adds valuable coverage to underserved orbital passes. Your self-hosted station directly contributes to open-source space exploration and satellite health monitoring efforts that benefit researchers, educators, and hobbyists worldwide.

For related projects, check out our guide on [self-hosted SDR receiver platforms](../2026-05-13-self-hosted-sdr-receiver-openwebrx-sdr-server-sdrangel-guide/) for the radio hardware side. If you are interested in amateur radio software infrastructure, see our [APRS packet radio guide](../2026-06-05-self-hosted-aprs-packet-radio-infrastructure-direwolf-xastir-aprx-guide/). For signal processing tools, our [GNU Radio and DSP guide](../2026-06-07-self-hosted-signal-processing-sdr-gnuradio-liquid-dsp-soapysdr/) covers the broader ecosystem.


## Setting Up Automated Observations with SatNOGS Scheduler

Once your SatNOGS ground station is operational, the real power comes from automated observation scheduling. The SatNOGS Network web interface lets you define observation priorities based on satellite transmitter modes, elevation thresholds, and time windows. For operators running multiple ground stations, the scheduler automatically distributes observations to the station with the best pass geometry.

The observation pipeline works as follows: the SatNOGS Network calculates upcoming satellite passes using TLE (Two-Line Element) orbital data updated daily from Space-Track.org. When a pass meets your criteria (typically minimum 10-degree elevation), the scheduler creates an observation job. Your SatNOGS Client receives the job, configures the SDR to the correct frequency and mode, records the pass, and uploads the resulting audio and waterfall data back to the network.

For advanced users, the SatNOGS API allows programmatic observation control. You can submit observation requests via REST API calls, integrate with external automation tools, or build custom dashboards using the observation data feed. The API uses token-based authentication and returns JSON responses compatible with most scripting environments.

```bash
# Schedule an observation via SatNOGS API
curl -X POST https://your-satnogs-instance/api/observations/ \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"satellite_id": 123, "transmitter_id": "abc", "start_time": "2026-06-15T12:00:00Z", "end_time": "2026-06-15T12:15:00Z"}'
```

## Integrating gr-satellites with Your Tracking Pipeline

The most powerful satellite monitoring setup combines all three tools: SatNOGS for automated scheduling, Gpredict for real-time tracking and antenna control, and gr-satellites for decoding telemetry. A typical integration pipeline routes the SDR IQ stream from the SatNOGS Client or Gpredict into a GNU Radio flowgraph that uses gr-satellites decoder blocks to extract and display telemetry values.

gr-satellites supports frame formats used by dozens of satellite missions. For example, the Funcube decoder extracts telemetry including battery voltage, solar panel current, and temperature sensor readings. The BY70-2 decoder handles the AX.25 packet telemetry format used by many Chinese CubeSats. Each decoder outputs structured JSON telemetry that you can feed into your own monitoring database or dashboard.

For operators interested in contributing to the amateur satellite community, decoded telemetry can be submitted to the SatNOGS DB through the Network API. This crowdsourced telemetry database helps satellite operators monitor their spacecraft health and assists researchers studying orbital decay patterns and space environment effects on small satellites.

## Choosing the Right Tool Combination

The choice between these tools depends on your primary use case. If you want to contribute to a global scientific network with minimal manual intervention, start with SatNOGS and add gr-satellites for telemetry decoding. If you are an active amateur radio operator making contacts through FM and linear transponder satellites, Gpredict's real-time tracking with rotor control is essential. For SDR experimenters and satellite developers who need to implement custom decoders, gr-satellites provides the most flexibility through GNU Radio's modular architecture.

Many operators run all three tools on a single Raspberry Pi 4, using SatNOGS for automated passes, Gpredict for manual operating sessions, and gr-satellites as a signal processing backend. With careful resource management (limiting GNU Radio to 2-3 flowgraphs simultaneously), a Pi 4 handles all three workloads comfortably. The $75 total hardware cost for a complete station makes satellite tracking accessible to anyone interested in space communications.


## FAQ

### Do I need an amateur radio license to track satellites?

No license is required for passive reception of satellite signals. Tracking satellites and receiving their telemetry beacons is legal in most countries without any license. However, if you plan to transmit signals to satellites (such as through amateur radio satellites like AO-91), you will need an amateur radio license.

### What hardware do I need for a basic ground station?

A minimal setup includes: a Raspberry Pi 4 (or any Linux computer), an RTL-SDR v3 dongle ($25-35), and a simple VHF/UHF antenna. For better reception, consider a directional Yagi antenna or a QFH (Quadrifilar Helix) antenna for NOAA weather satellites. The total hardware cost can be under $100 for a functional station.

### Can I run SatNOGS and Gpredict on the same machine?

Yes, they serve different purposes and can coexist. SatNOGS handles automated scheduled observations, while Gpredict provides real-time tracking for manual sessions. They can share the same SDR hardware as long as only one application accesses it at a time. Use a script or the SatNOGS scheduler to coordinate access.

### How do I contribute observation data back to the community?

SatNOGS automatically uploads observations to the SatNOGS Network when configured with valid credentials. Your data becomes part of the SatNOGS DB, which is used by satellite operators, researchers, and space agencies to monitor satellite health. For Gpredict and gr-satellites, you can manually submit decoded telemetry to the SatNOGS DB or share your findings on forums like the Libre Space community.

### What is the difference between weather satellite reception and amateur satellite tracking?

Weather satellites (NOAA, Meteor, GOES) continuously transmit images and require different decoders. Our [weather balloon radiosonde tracking guide](../2026-06-06-self-hosted-weather-balloon-radiosonde-tracking-radiosonde-auto-rx-guide/) covers atmospheric sensing. Amateur satellite tracking focuses on orbital prediction, telemetry decoding, and two-way communication through amateur radio satellites. The tools in this article are optimized for the amateur satellite use case.


<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Amateur Satellite Tracking: SatNOGS vs Gpredict vs gr-satellites Compared",
  "description": "Compare open-source amateur satellite tracking solutions — SatNOGS Network, Gpredict, and gr-satellites. Build a self-hosted ground station with Docker Compose configs and setup guides.",
  "datePublished": "2026-06-14",
  "dateModified": "2026-06-14",
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
