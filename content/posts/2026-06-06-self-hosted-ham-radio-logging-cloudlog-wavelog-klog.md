---
title: "Self-Hosted Ham Radio Logging Platforms: Cloudlog vs WaveLog vs KLog"
date: "2026-06-06"
tags: ["ham-radio", "amateur-radio", "logging", "self-hosted", "radio", "qso"]
draft: false
---

## Introduction

Every amateur radio operator knows that logging contacts (QSOs) is not just good practice — it's essential for earning awards, tracking propagation, and complying with license requirements. While paper logs still have their charm, modern digital logging platforms offer automatic lookups, award tracking, LOTW/eQSL synchronization, and real-time maps of your contacts. Self-hosted logging platforms give you full control over your log data while providing web access from any device — in the shack, at field day, or on your phone during a POTA activation.

In this guide, we compare three open-source logging solutions: **Cloudlog** (the most popular PHP-based web logger), **WaveLog** (a modern Cloudlog fork with enhanced features), and **KLog** (a desktop-native multiplatform logger). We cover installation, Docker deployment, and which fits different operating styles.

## Why Digital Logging Matters

Modern amateur radio logging goes far beyond recording callsign, frequency, and time:

- **LoTW Integration**: The ARRL's Logbook of The World enables automated QSL confirmation for awards like DXCC and WAS
- **eQSL and QRZ Confirmation**: Electronic QSL cards without postage
- **Award Tracking**: Automatic progress tracking toward WAS, DXCC, IOTA, SOTA, POTA, and custom awards
- **Propagation Analysis**: Map your contacts to understand band openings and antenna performance
- **Contest Support**: Real-time dupe checking, multiplier tracking, and Cabrillo export
- **Station Management**: Track multiple station locations, antennas, and operators

## Tool Comparison

| Feature | Cloudlog | WaveLog | KLog |
|---------|----------|---------|------|
| **GitHub Stars** | 560 | 446 | 98 |
| **Type** | PHP Web App | PHP Web App (fork) | C++ Desktop App |
| **Language** | PHP + MySQL | PHP + MySQL | C++ (Qt) |
| **Deployment** | Docker Compose / LAMP | Docker / LAMP | Native packages |
| **Web Interface** | Yes (responsive) | Yes (responsive) | No (desktop only) |
| **LoTW Support** | Yes (native) | Yes (native) | Yes (via TQSL) |
| **eQSL Support** | Yes | Yes | Yes |
| **QRZ.com Lookup** | Yes (API) | Yes (API) | Yes |
| **ADIF Import/Export** | Yes | Yes | Yes |
| **Contest Mode** | Yes (DXCC, WAS, etc.) | Yes (expanded awards) | Yes (basic) |
| **Multi-Operator** | Yes | Yes | No (single user) |
| **REST API** | Yes | Yes | No |
| **Mobile Access** | Web-based (any device) | Web-based (any device) | Desktop only |
| **Docker Support** | Yes (compose included) | Yes (Dockerfile) | No (native install) |
| **Last Update** | June 2026 | June 2026 | June 2026 |

## Cloudlog: The Self-Hosted Standard

Cloudlog is the go-to self-hosted amateur radio logging platform. Written in PHP with a MySQL/MariaDB backend, it provides a full-featured web interface accessible from any browser — desktop, tablet, or phone. With native LoTW, eQSL, and QRZ integration, it automates the entire logging workflow.

**Key Features:**
- Live QSO entry with real-time callsign lookup via QRZ.com or HamQTH
- ADIF import/export for moving existing logs into the platform
- Built-in award tracking for DXCC, WAS, IOTA, SOTA, POTA, and custom awards
- Satellite operation support with automatic Doppler calculation
- Multi-station and multi-operator support for club stations
- REST API for integration with contest loggers and external tools
- Dark mode, custom themes, and station profile management

**Deploying Cloudlog with Docker Compose:**

```yaml
version: "3.8"
services:
  db:
    image: mariadb:10.11
    container_name: cloudlog-db
    environment:
      MYSQL_ROOT_PASSWORD: changeme
      MYSQL_DATABASE: cloudlog
      MYSQL_USER: cloudlog
      MYSQL_PASSWORD: changeme
    volumes:
      - ./db_data:/var/lib/mysql
    restart: unless-stopped

  cloudlog:
    image: magicbug/cloudlog:latest
    container_name: cloudlog-app
    ports:
      - "8080:80"
    environment:
      CI_ENV: production
      DB_HOST: db
      DB_USER: cloudlog
      DB_PASSWORD: changeme
      DB_NAME: cloudlog
    volumes:
      - ./uploads:/var/www/html/uploads
      - ./backup:/var/www/html/backup
    depends_on:
      - db
    restart: unless-stopped
```

```bash
# Clone the repo with Docker Compose
git clone https://github.com/magicbug/Cloudlog.git
cd Cloudlog
cp docker-compose.yml.example docker-compose.yml
# Edit credentials, then:
docker compose up -d
# Access at http://your-server:8080
```

## WaveLog: The Modern Fork

WaveLog started as a fork of Cloudlog and has grown into a distinct project with a focus on modern UI/UX and enhanced award tracking. If you're familiar with Cloudlog, WaveLog feels like the same platform with a design refresh and additional quality-of-life features.

**Key Differences from Cloudlog:**
- Cleaner, more modern interface with improved mobile responsiveness
- Expanded award tracking (POTA, SOTA, WWFF, and custom) built into the core
- Enhanced dark mode support with system preference detection
- Improved ADIF import with duplicate detection and merge capabilities
- Built-in propagation visualization using real-time solar data
- More granular station profile management for multi-location setups

**Deploying WaveLog with Docker:**

```bash
# Clone and build
git clone https://github.com/wavelog/wavelog.git
cd wavelog
docker build -t wavelog .

# Run with MariaDB
docker run -d --name wavelog-db \
  -e MYSQL_ROOT_PASSWORD=changeme \
  -e MYSQL_DATABASE=wavelog \
  -e MYSQL_USER=wavelog \
  -e MYSQL_PASSWORD=changeme \
  -v ./db:/var/lib/mysql \
  mariadb:10.11

docker run -d --name wavelog-app \
  -p 8080:80 \
  -e DB_HOST=wavelog-db \
  -e DB_USER=wavelog \
  -e DB_PASSWORD=changeme \
  -e DB_NAME=wavelog \
  --link wavelog-db \
  wavelog
```

## KLog: The Desktop Alternative

KLog takes a different approach — it's a native C++ desktop application built with the Qt framework, running on Linux, macOS, and Windows. While it doesn't offer web access, it provides a fast, offline-capable logging experience with tight operating system integration.

**Key Features:**
- Native desktop performance — instant startup and search
- Full offline operation with no server dependencies
- LoTW and eQSL support via TQSL integration
- ClubLog integration for real-time uploads
- DX cluster integration for spotting
- Hamlib integration for rig control
- Lightweight — uses minimal system resources

**Installing KLog on Linux:**

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install klog

# Fedora
sudo dnf install klog

# Build from source
git clone https://github.com/ea4k/klog.git
cd klog
mkdir build && cd build
cmake ..
make -j$(nproc)
sudo make install
```

## Why Self-Host Your Ham Radio Log?

Running your own logging platform offers advantages that cloud services and commercial software can't match:

**Data Ownership:** Your QSO log represents years — sometimes decades — of operating history. When you self-host, that data lives on your hardware, backed up on your schedule. You're not at the mercy of a service shutting down, changing pricing, or being acquired. Many long-time hams have lost logs when commercial services disappeared.

**Internet Independence:** While web-based loggers like Cloudlog and WaveLog run on your local network, they don't require internet access (except for callsign lookup services). During field day or emergency communications when internet is unavailable, KLog's offline operation shines. A Raspberry Pi running Cloudlog on a battery pack gives you a full logging server anywhere.

**Integration Flexibility:** With a REST API (Cloudlog and WaveLog), you can build custom integrations — auto-logging from your SDR, real-time QSO maps on a shack display, or automated award status dashboards. Commercial services lock you into their integration model.

For more amateur radio infrastructure, see our [SDR receiver platform guide](../2026-05-13-self-hosted-sdr-receiver-openwebrx-sdr-server-sdrangel-guide/). For packet radio and APRS, check our [APRS infrastructure comparison](../2026-06-05-self-hosted-aprs-packet-radio-infrastructure-direwolf-xastir-aprx-guide/). For digital voice modes, our [ham radio digital voice guide](../2026-06-05-self-hosted-ham-radio-digital-voice-svxlink-mmdvm-freedv-guide/) covers SvxLink, MMDVM, and FreeDV.

## FAQ

### Can I migrate from Cloudlog to WaveLog (or vice versa)?

Yes. Both platforms use MySQL/MariaDB and share a common schema heritage. You can export your Cloudlog database and import it into WaveLog (or vice versa). However, always back up your database before attempting migration. WaveLog's ADIF import also supports merging into existing logs.

### Do these platforms support real-time rig control?

Cloudlog and WaveLog have basic CAT (Computer Aided Transceiver) support through their APIs, but they're not full rig-control programs. For automatic frequency and mode logging from your radio, pair them with tools like Flrig or Hamlib. KLog has direct Hamlib integration for rig control within the desktop app.

### Can multiple operators log simultaneously?

Cloudlog and WaveLog support multi-operator stations through their web interfaces — each operator logs in with their own account. For contest multi-op scenarios, both platforms can handle concurrent QSO entry. KLog is single-user and better suited for individual stations.

### What about FT8 and digital mode logging?

WSJT-X, JTDX, and other digital mode software can automatically log QSOs to Cloudlog and WaveLog via their REST APIs or ADIF file monitoring. Both platforms accept real-time ADIF pushes. KLog can import WSJT-X ADIF logs, but the process is manual — you import after a session rather than getting real-time updates.

### Is a Raspberry Pi powerful enough to run Cloudlog?

Absolutely. A Raspberry Pi 4 (2GB+) running Docker can comfortably host Cloudlog for a single operator or small club station. The LAMP stack is lightweight, and the database load for amateur radio logging (hundreds to low thousands of QSOs per year) is minimal. For larger clubs with thousands of QSOs per month, consider a Pi 5 or a small x86 server.

---

**💰 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — the world's largest prediction market platform. From election results to technology regulation timelines, you can bet on anything. Unlike gambling, this is a real information market: the more you know, the better your odds. I've made significant returns predicting technology-related events. Sign up with my referral link:** [Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Ham Radio Logging Platforms: Cloudlog vs WaveLog vs KLog",
  "description": "Compare three open-source amateur radio logging platforms: Cloudlog (PHP web app), WaveLog (modern Cloudlog fork), and KLog (native desktop logger). Includes Docker Compose deployment guides, LoTW/eQSL integration, and award tracking features.",
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
