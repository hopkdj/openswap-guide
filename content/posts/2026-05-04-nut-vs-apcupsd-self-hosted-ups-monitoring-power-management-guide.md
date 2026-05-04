---
title: "NUT vs apcupsd: Self-Hosted UPS Monitoring & Power Management Guide 2026"
date: 2026-05-04
tags: ["comparison", "guide", "self-hosted", "infrastructure", "power-management", "monitoring"]
draft: false
description: "Compare open-source UPS monitoring solutions — NUT and apcupsd — for self-hosted power management, graceful shutdown, and battery health monitoring. Includes Docker deployment and configuration examples."
---

## Why Self-Host Your UPS Monitoring?

An uninterruptible power supply (UPS) is the first line of defense against power outages, brownouts, and electrical surges. But a UPS without proper monitoring is just an expensive battery — you won't know it's running on backup power until your servers crash from an unexpected battery depletion.

Commercial UPS management platforms like APC PowerChute Network Shutdown and Eaton Intelligent Power Manager offer web interfaces and integration features — but they are often locked to specific hardware brands, require Windows licenses, or charge per-node management fees. Self-hosted open-source UPS monitoring works with hundreds of UPS models across all manufacturers, runs on any Linux server, and costs nothing.

For homelabs, small businesses, and edge deployments, proper UPS monitoring ensures graceful shutdowns during extended outages, battery health tracking, and automated alerts when power events occur. This guide compares the two leading open-source UPS monitoring solutions: **NUT** (Network UPS Tools) and **apcupsd**.

## Project Overview

| Feature | NUT (Network UPS Tools) | apcupsd |
|---|---|---|
| GitHub Stars | 3,997 | ~200 (GitHub mirror) |
| Primary Language | C | C |
| Last Updated | May 2026 | 2024 (stable) |
| UPS Compatibility | 200+ models, 30+ drivers | APC, CyberPower, MGE |
| Network Monitoring | ✅ Native (upsd/upsmon) | ✅ (NIS protocol) |
| Web Interface | Via upsmon-web or Grafana | Via CGI scripts |
| Graceful Shutdown | ✅ Multi-server coordination | ✅ Single or multi-server |
| SNMP Support | ✅ (snmp-ups driver) | ❌ Limited |
| Docker Support | ✅ Community images | ✅ Community images |
| License | GPL 2.0 / NUT license | GPL 2.0 |
| IETF RFC | RFC 9271 (UPS management protocol) | — |

## NUT — The Universal UPS Management Platform

NUT is the most comprehensive open-source UPS monitoring solution, supporting over 200 UPS models from 30+ manufacturers. It uses a client-server architecture: `upsd` runs on the machine connected to the UPS via USB or serial, and `upsmon` clients on other servers query `upsd` over the network for status and trigger shutdowns.

Key strengths:
- **Wide hardware support** — 200+ UPS models via dedicated drivers (usbhid-ups, snmp-ups, blazer_usb, etc.)
- **Client-server architecture** — one UPS server can notify dozens of client machines
- **Standardized protocol** — IETF RFC 9271 published in 2022, based on NUT's protocol
- **Extensible** — supports custom scripts for shutdown, notifications, and actions
- **Grafana integration** — nut_exporter provides Prometheus metrics for dashboards

### NUT Docker Deployment

```yaml
services:
  nut-server:
    image: instantlinux/nut-upsd:latest
    cap_add:
      - SYS_ADMIN
      - DAC_READ_SEARCH
    devices:
      - /dev/bus/usb:/dev/bus/usb:rwm
    environment:
      - UPS_DRIVER=usbhid-ups
      - UPS_PORT=auto
      - UPS_NAME=myups
      - UPS_USER=upsmon
      - UPS_PASSWORD=secret
      - MODE=netserver
    volumes:
      - nut-config:/etc/nut
    restart: unless-stopped

  nut-exporter:
    image: instantlinux/nut-exporter:latest
    environment:
      - NUT_HOST=nut-server
      - NUT_PORT=3493
      - NUT_USERNAME=upsmon
      - NUT_PASSWORD=secret
    ports:
      - "9199:9199"
    depends_on:
      - nut-server
    restart: unless-stopped

volumes:
  nut-config:
```

### NUT Configuration

The core NUT configuration involves three files:

```ini
# /etc/nut/ups.conf — UPS driver definition
[myups]
    driver = usbhid-ups
    port = auto
    desc = "APC Smart-UPS 1500"

# /etc/nut/upsd.conf — Network daemon config
LISTEN 0.0.0.0 3493

# /etc/nut/upsd.users — Client authentication
[upsmon]
    password = secret
    upsmon master

# /etc/nut/upsmon.conf — Monitor client config
MONITOR myups@localhost 1 upsmon secret master
SHUTDOWNCMD "/sbin/shutdown -h +0"
NOTIFYCMD /usr/bin/upssched
```

## apcupsd — APC-Focused UPS Daemon

apcupsd is purpose-built for APC (American Power Conversion) UPS devices, though it supports some CyberPower and MGE models. It has been the default UPS management solution on many Linux distributions for over two decades. Its design is simpler than NUT — it runs as a single daemon that both communicates with the UPS and handles shutdown coordination.

Key strengths:
- **Deep APC integration** — most comprehensive feature set for APC Smart-UPS and Back-UPS models
- **Simple setup** — single configuration file, single daemon process
- **CGI web interface** — built-in status page (requires Apache/lighttpd)
- **Proven stability** — decades of production use
- **Cross-platform** — runs on Linux, macOS, FreeBSD, and Windows

### apcupsd Docker Deployment

```yaml
services:
  apcupsd:
    image: gersilex/apcupsd:latest
    cap_add:
      - SYS_ADMIN
    devices:
      - /dev/bus/usb:/dev/bus/usb:rwm
    environment:
      - UPSNAME=myups
      - UPSCABLE=usb
      - UPSTYPE=usb
      - DEVICE=
      - NISPORT=3551
      - NISIP=0.0.0.0
      - SHUTDELAY=0
      - TIMEPERC=5
      - BATTERYLEVEL=10
      - MINUTES=3
    volumes:
      - apcupsd-config:/etc/apcupsd
    restart: unless-stopped

  apcupsd-exporter:
    image: mdlayher/apcupsd_exporter:latest
    ports:
      - "9162:9162"
    environment:
      - APCUPSD_HOST=apcupsd
      - APCUPSD_PORT=3551
    depends_on:
      - apcupsd
    restart: unless-stopped

volumes:
  apcupsd-config:
```

### apcupsd Configuration

```ini
# /etc/apcupsd/apcupsd.conf
UPSNAME myups
UPSCABLE usb
UPSTYPE usb
DEVICE
LOCKFILE /var/lock
SCRIPTDIR /etc/apcupsd
PWRFAILDIR /etc/apcupsd
ONBATTERYDELAY 6
BATTERYLEVEL 10
MINUTES 3
TIMEOUT 0
ANNOY 300
ANNOYDELAY 60
NOLOGON disable
KILLDELAY 0
NETSERVER on
NISIP 0.0.0.0
NISPORT 3551
EVENTSFILE /var/log/apcupsd.events
WAKEUP 60
```

## Comparison Matrix

| Capability | NUT | apcupsd |
|---|---|---|
| Multi-vendor UPS support | ✅ 200+ models | ⚠️ Primarily APC |
| Multi-server shutdown coordination | ✅ Native (upsmon) | ✅ Via NIS network |
| SNMP protocol support | ✅ (snmp-ups) | ❌ |
| Prometheus metrics | ✅ (nut_exporter) | ✅ (apcupsd_exporter) |
| Web UI | Via third-party | ✅ Built-in CGI |
| Battery calibration | ✅ | ✅ (APC only) |
| Self-test scheduling | ✅ | ✅ |
| Load percentage monitoring | ✅ | ✅ |
| Temperature monitoring | ✅ (on supported models) | ✅ (on supported models) |
| USB hot-plug detection | ✅ | ⚠️ Requires restart |
| Configuration complexity | Medium (3+ files) | Low (1 file) |
| Community support | Active GitHub, mailing list | Stable, less active |

## Choosing the Right Tool

| Scenario | Recommended Tool | Reason |
|---|---|---|
| Mixed UPS brands in your environment | NUT | Supports 200+ models across 30+ manufacturers |
| APC-only environment | apcupsd | Deepest APC feature integration |
| Need SNMP monitoring | NUT | Native snmp-ups driver |
| Simple single-server setup | apcupsd | One config file, one daemon |
| Multi-server datacenter | NUT | Better client-server coordination model |
| Grafana dashboards | Either | Both have Prometheus exporters |
| IETF standards compliance | NUT | Protocol published as RFC 9271 |

## Why Self-Host Power Management?

A UPS monitoring tool is the critical link between a power event and a graceful shutdown. Without it, your servers will run until the UPS battery dies, causing abrupt power loss that can corrupt databases, lose in-flight writes, and damage filesystems. Self-hosted solutions cost nothing, support a wider range of hardware than vendor-locked tools, and give you full control over shutdown thresholds, notification scripts, and integration with your existing monitoring stack.

For hardware-level monitoring, see our [bare metal monitoring guide](../2026-04-23-self-hosted-bare-metal-hardware-monitoring-ipmi-redfish-openbmc-guide-2026/). For broader infrastructure visibility, our [infrastructure monitoring comparison](../2026-04-25-nagios-vs-icinga-vs-cacti-self-hosted-infrastructure-monitoring-guide-2026/) covers traditional monitoring platforms.

## FAQ

### Can NUT and apcupsd run on the same server?

No, both tools try to claim exclusive access to the USB device connected to the UPS. Running both simultaneously will cause conflicts. Choose one based on your UPS brand and feature requirements.

### How does graceful shutdown work with multiple servers?

The server directly connected to the UPS (via USB or serial) runs the UPS daemon (upsd for NUT, or apcupsd). This server monitors the UPS battery level and, when it reaches the configured threshold, sends shutdown signals to all client machines running upsmon (NUT) or connected via NIS (apcupsd). Each client shuts down gracefully before the UPS battery is depleted.

### What happens when the UPS battery reaches 0%?

If configured correctly, all monitored servers should have already shut down before the battery reaches 0%. The shutdown threshold is typically set at 10% battery or 3 minutes remaining, whichever comes first. If the threshold is reached and servers haven't shut down, the UPS will eventually cut power, causing abrupt shutdown.

### Can I monitor a UPS over SNMP instead of USB?

Yes, NUT supports SNMP-based UPS monitoring via the `snmp-ups` driver. This works with UPS models that have a built-in network management card (like APC Network Management Cards or Eaton Network Cards). apcupsd has limited SNMP support and primarily relies on USB or serial connections.

### How do I get UPS metrics into Grafana?

Both tools have Prometheus exporters. For NUT, deploy `instantlinux/nut-exporter` which exposes metrics on port 9199. For apcupsd, use `mdlayher/apcupsd_exporter` on port 9162. Configure Prometheus to scrape these endpoints, then create Grafana dashboards for battery level, load percentage, input voltage, and runtime remaining.

### What is the IETF RFC 9271 about UPS management?

RFC 9271, published in 2022, documents the NUT protocol as an informational standard. It describes how UPS management clients communicate with UPS servers over the network, including authentication, status queries, and command execution. This standardization validates NUT as the de facto open-source UPS management protocol.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "NUT vs apcupsd: Self-Hosted UPS Monitoring & Power Management Guide 2026",
  "description": "Compare open-source UPS monitoring solutions — NUT and apcupsd — for self-hosted power management, graceful shutdown, and battery health monitoring.",
  "datePublished": "2026-05-04",
  "dateModified": "2026-05-04",
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