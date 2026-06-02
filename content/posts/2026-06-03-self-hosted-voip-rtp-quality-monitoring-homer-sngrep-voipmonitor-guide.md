---
title: "Self-Hosted VoIP RTP Quality Monitoring: HOMER vs sngrep vs VoIPmonitor"
date: "2026-06-03"
tags: ["voip", "rtp", "sip", "monitoring", "networking", "telecom", "quality-of-service"]
draft: false
---

## Introduction

Voice over IP (VoIP) quality depends heavily on the Real-time Transport Protocol (RTP) — the protocol that carries actual audio and video media streams between endpoints. Unlike SIP signaling (which handles call setup and teardown), RTP is where quality problems manifest: jitter, packet loss, latency, and codec mismatches all degrade call quality silently. Without dedicated RTP monitoring, these issues go undetected until users complain.

This guide compares three battle-tested open-source tools for self-hosted VoIP RTP monitoring and analysis: **HOMER** (SIPCapture), the full-featured VoIP monitoring platform; **sngrep**, the terminal-based SIP/RTP call flow viewer; and **VoIPmonitor**, the passive VoIP quality analyzer. Whether you are running a PBX for a small office, operating a carrier-grade SIP trunking service, or troubleshooting intermittent voice quality issues, these tools give you visibility into your RTP media streams.

## HOMER (SIPCapture)

HOMER is a 100% open-source VoIP and RTC monitoring platform designed for large-scale deployments. It captures, stores, and visualizes SIP signaling and RTP media streams with built-in quality metrics (MOS scores, jitter, packet loss, latency).

### Key Features
- **Full SIP + RTP capture** with correlation between signaling and media
- **MOS (Mean Opinion Score)** calculation for every call
- **Web dashboard** with real-time call monitoring and historical search
- **HEP/HEP3 encapsulation** for distributed capture agent architecture
- **Multi-tenant** support for service provider environments
- **REST API** for integration with external monitoring systems

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  homer-heplify:
    image: sipcapture/heplify:latest
    container_name: homer-capture
    network_mode: host
    environment:
      - HEPLIFY_SERVER_HEP_ADDR=0.0.0.0:9060
      - HEPLIFY_SERVER_DB_ADDR=postgres:5432
      - HEPLIFY_SERVER_DB_USER=homer
      - HEPLIFY_SERVER_DB_PASS=homerpass
      - HEPLIFY_SERVER_DB_NAME=homer_data
    restart: unless-stopped

  postgres:
    image: postgres:15
    container_name: homer-db
    environment:
      - POSTGRES_USER=homer
      - POSTGRES_PASSWORD=homerpass
      - POSTGRES_DB=homer_data
    volumes:
      - ./postgres/data:/var/lib/postgresql/data
    restart: unless-stopped

  homer-app:
    image: sipcapture/homer-app:latest
    container_name: homer-web
    ports:
      - "9080:9080"
    environment:
      - DB_HOST=postgres
      - DB_USER=homer
      - DB_PASS=homerpass
      - DB_NAME=homer_data
    depends_on:
      - postgres
    restart: unless-stopped
```

### Capturing RTP Traffic

Send HEP-encapsulated packets from your SIP server to HOMER using the `heplify` client on your PBX server:

```bash
# Install heplify on PBX
wget https://github.com/sipcapture/heplify/releases/latest/download/heplify
chmod +x heplify

# Capture all SIP (port 5060) and RTP (port range 10000-20000) traffic
./heplify -hs homer-server:9060 -p 5060 -pr 10000-20000 -m SIPRTP
```

Once traffic flows, HOMER's web dashboard at `http://localhost:9080` displays call flows, quality metrics, and searchable call records. The MOS scores provide an immediate at-a-glance quality indicator for every call.

### Pros and Cons

- ✅ Enterprise-grade monitoring with web dashboard
- ✅ Full SIP/RTP correlation with detailed call flow visualization
- ✅ Distributed capture architecture for multi-site deployments
- ✅ MOS scoring and quality trend analysis
- ❌ Complex setup — requires PostgreSQL, capture agents, and web app
- ❌ Resource-intensive — needs significant storage for call records
- ❌ Learning curve — HEP protocol and multi-component architecture

## sngrep

sngrep is a terminal-based (ncurses) SIP and RTP call flow viewer that excels at quick, interactive debugging. Unlike HOMER's heavyweight architecture, sngrep is a single binary that captures and displays packet flows in real time.

### Key Features
- **Terminal UI** — ncurses-based interactive call flow browser
- **Live or offline** packet capture and analysis
- **Call flow diagrams** in ASCII art for visual debugging
- **RTP stream detection** and basic quality metrics
- **SIP message dialogs** with request/response correlation
- **Save and replay** captured sessions
- **Zero configuration** — just point it at an interface

### Installation & Usage

```bash
# Install on Debian/Ubuntu
apt-get install -y sngrep

# Live capture on eth0, filtering SIP (port 5060)
sngrep -d eth0 port 5060

# Read from a pcap file
sngrep -r capture.pcap

# Capture with RTP correlation
sngrep -d eth0 -cr port 5060 or portrange 10000-20000
```

### Docker Usage

```bash
# Run sngrep in a container with host network access
docker run --rm -it --net=host irontec/sngrep:latest sngrep -d eth0
```

Once launched, sngrep presents an interactive terminal UI showing all active SIP dialogs. Press `Enter` on a call to view the full SIP message exchange, or navigate with arrow keys. The call flow display (`F2`) shows SIP messages in a ladder diagram with timestamps — invaluable for spotting retransmissions, timeouts, and routing loops.

For RTP analysis, sngrep can detect RTP streams associated with SIP calls and display packet counts, jitter, and packet loss indicators. While not as detailed as HOMER's MOS scores, the information is sufficient for most troubleshooting scenarios.

### Pros and Cons

- ✅ Instant startup — single binary, zero configuration
- ✅ Interactive terminal UI for real-time debugging
- ✅ Lightweight — minimal CPU and memory footprint
- ✅ Supports pcap files for offline analysis
- ❌ No persistent storage or historical analytics
- ❌ Terminal-only — no web dashboard or remote access
- ❌ Limited to what fits in terminal — no trend analysis or alerting

## VoIPmonitor

VoIPmonitor is a passive VoIP quality monitoring solution that uses packet sniffing to analyze SIP signaling and RTP media streams. It provides both a web-based GUI and a sensor-based distributed architecture.

### Key Features
- **Passive packet capture** — no impact on production traffic
- **MOS, R-Factor, PESQ** quality scoring algorithms
- **WEB GUI** with call records, graphs, and dashboards
- **CDR (Call Detail Records)** export to MySQL/PostgreSQL
- **Alerting** — configurable thresholds for quality degradation
- **Audio recording** — optional call recording with playback
- **Distributed sensors** for multi-site monitoring

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  voipmonitor:
    image: voipmonitor/sniffer:latest
    container_name: voipmonitor
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    environment:
      - MYSQL_HOST=mysql
      - MYSQL_USER=voipmonitor
      - MYSQL_PASSWORD=vmpass
      - MYSQL_DB=voipmonitor
    volumes:
      - ./voipmonitor/config:/etc/voipmonitor
      - ./voipmonitor/spool:/var/spool/voipmonitor
    restart: unless-stopped

  mysql:
    image: mysql:8.0
    container_name: voipmonitor-db
    environment:
      - MYSQL_ROOT_PASSWORD=rootpass
      - MYSQL_DATABASE=voipmonitor
      - MYSQL_USER=voipmonitor
      - MYSQL_PASSWORD=vmpass
    volumes:
      - ./mysql/data:/var/lib/mysql
    restart: unless-stopped

  voipmonitor-gui:
    image: voipmonitor/gui:latest
    container_name: voipmonitor-web
    ports:
      - "8080:80"
    environment:
      - MYSQL_HOST=mysql
      - MYSQL_USER=voipmonitor
      - MYSQL_PASSWORD=vmpass
      - MYSQL_DB=voipmonitor
    depends_on:
      - mysql
    restart: unless-stopped
```

### Configuration

Edit `/etc/voipmonitor/voipmonitor.conf`:

```ini
# SIP interface
sipinterface = eth0
# Capture SIP and RTP
sipport = 5060
rtpport = 10000-20000
# MOS calculation
mos = yes
mos_g729 = yes
# Save CDR to database
savecdr = yes
# Optional: save audio
savertp = yes
```

VoIPmonitor automatically detects SIP registrations and calls, computes MOS scores for every RTP stream, and stores results in MySQL. The web GUI at port 8080 provides searchable call records with detailed quality breakdowns per call leg.

### Pros and Cons

- ✅ Detailed MOS, R-Factor, and PESQ quality scoring
- ✅ Web dashboard with historical call search
- ✅ Distributed sensor architecture for multi-site
- ✅ Audio recording and playback for quality verification
- ❌ More complex setup than sngrep
- ❌ MySQL dependency for persistent storage
- ❌ Web GUI has a dated interface compared to HOMER

## Comparison Table

| Feature | HOMER | sngrep | VoIPmonitor |
|---------|-------|--------|-------------|
| **Stars** | 1,965★ | 1,175★ | 285★ |
| **Interface** | Web dashboard | Terminal UI (ncurses) | Web GUI |
| **SIP + RTP Correlation** | Yes (full) | Yes (basic) | Yes (full) |
| **MOS Scoring** | Yes | Basic indicators | Yes (MOS, R-Factor, PESQ) |
| **Persistent Storage** | PostgreSQL | None (pcap files) | MySQL |
| **Historical Search** | Yes | No | Yes |
| **Distributed Capture** | Yes (HEP agents) | No (local only) | Yes (sensors) |
| **Audio Recording** | Optional | No | Yes |
| **Setup Complexity** | High | Very Low | Medium |
| **Resource Requirements** | High (DB + web + agents) | Minimal | Medium (DB + web) |
| **Best For** | Carrier-grade monitoring | Quick troubleshooting | Quality assurance teams |
| **Primary Language** | Go | C | C++ |

## Why Self-Host Your RTP Monitoring?

RTP quality monitoring is one of the most overlooked aspects of VoIP infrastructure — until users start complaining about choppy audio, dropped calls, or echoes. By the time a help desk ticket is filed, the problematic call is long over and there is no forensic data to diagnose the root cause.

Self-hosted RTP monitoring captures every call automatically, creating a permanent audit trail of call quality metrics. When a user reports a problem at 2:37 PM, you can search the monitoring dashboard for that exact timestamp, review the call flow diagram, check the MOS score, and identify whether the issue was network congestion, codec mismatch, or a failing SIP trunk. For broader VoIP infrastructure insights, see our [VoIP media codec transcoding guide](../2026-06-03-self-hosted-voip-media-codec-transcoding-freeswitch-rtpengine-guide/).

Cost is another driver for self-hosting. Commercial VoIP monitoring solutions charge per monitored call or per concurrent session, which adds up quickly in high-volume environments. HOMER handles millions of calls on modest hardware, and sngrep runs on a Raspberry Pi. For organizations already running a self-hosted PBX like Asterisk or FreeSWITCH, adding RTP monitoring is a natural extension of existing infrastructure. Our [FAX server solutions guide](../2026-06-03-self-hosted-fax-server-hylafax-ictfax-asterisk-guide/) shows how these telephony tools complement each other in a unified communications setup.

## FAQ

### What is a good MOS score for VoIP calls?

MOS (Mean Opinion Score) ranges from 1.0 (unusable) to 5.0 (excellent). For business VoIP:
- **4.0+**: Excellent — transparent quality, no perceptible issues
- **3.5-4.0**: Good — minor degradation, acceptable for most calls
- **3.0-3.5**: Fair — noticeable issues, frustrating for long calls
- **Below 3.0**: Poor — likely to generate user complaints

HOMER and VoIPmonitor compute MOS algorithmically from packet loss, jitter, and latency measurements using the ITU-T E-model standard.

### Can I monitor encrypted RTP (SRTP) traffic?

Partially. SRTP encrypts the media payload, so tools cannot extract audio or compute MOS from the media content. However, all three tools can still measure network-level metrics (packet loss, jitter, latency) from SRTP streams because the RTP headers remain unencrypted. sngrep is particularly useful here — it shows the SIP exchange where SRTP keys are negotiated without needing to decrypt the media.

### Do these tools work with WebRTC?

HOMER has native WebRTC support and can capture DTLS-SRTP media streams. sngrep can display WebRTC signaling (SIP over WebSocket or JSON) but has limited DTLS-SRTP media analysis. VoIPmonitor supports WebRTC with additional configuration. For production WebRTC monitoring, HOMER is the strongest choice due to its active development focus on RTC (Real-Time Communication) protocols beyond traditional SIP.

### How much disk space does RTP monitoring consume?

It depends on call volume and whether you store audio recordings:
- **sngrep**: Near-zero (only pcap files while capturing)
- **VoIPmonitor without audio**: ~2-5 MB per 1,000 calls (CDR + metrics only)
- **VoIPmonitor with audio**: ~10-20 MB per call (G.711 recording)
- **HOMER with PostgreSQL**: ~50-100 MB per 100,000 call records

Plan for at least 1 GB of database storage for a small office handling ~10,000 calls per month. Audio recording multiplies storage requirements significantly.

### Can I run sngrep on a headless server?

Yes. sngrep works over SSH with terminal emulation. Connect to your server with `ssh -t user@server sngrep` to launch sngrep directly, or start sngrep and use `tmux`/`screen` for persistent sessions. For non-interactive capture, use sngrep with the `-O` flag to save output to a pcap file for later analysis.

---

**💰 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — the world's largest prediction market platform where you can bet on anything from election outcomes to tech regulation timelines. Unlike gambling, this is a real information market: the more you know, the better your odds. I've profited by predicting tech-related event trajectories. Sign up with my invite link: [Polymarket.com](https://polymarket.com/?r=fc8a0)**

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted VoIP RTP Quality Monitoring: HOMER vs sngrep vs VoIPmonitor",
  "description": "In-depth comparison of HOMER, sngrep, and VoIPmonitor for self-hosted VoIP RTP quality monitoring — covering MOS scoring, SIP/RTP correlation, Docker deployment, and troubleshooting workflows.",
  "datePublished": "2026-06-03",
  "dateModified": "2026-06-03",
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
