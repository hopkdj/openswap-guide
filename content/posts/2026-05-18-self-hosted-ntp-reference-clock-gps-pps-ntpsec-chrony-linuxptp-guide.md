---
title: "Self-Hosted NTP Reference Clock: GPS/PPS Time Sources with NTPsec, Chrony & LinuxPTP"
date: "2026-05-18"
tags: ["ntp", "time-sync", "gps", "infrastructure", "self-hosted"]
draft: false
---

Deploying a stratum 1 NTP server with a GPS reference clock gives you independent, highly accurate time synchronization without relying on public NTP pools. This guide compares three open-source implementations for managing GPS/PPS reference clocks: **NTPsec**, **Chrony**, and **LinuxPTP**.

## What Is an NTP Reference Clock?

An NTP reference clock is a local hardware time source connected directly to your server — typically a GPS receiver with PPS (Pulse Per Second) output. Unlike servers that sync from upstream NTP pools, a stratum 1 server with a reference clock generates its own authoritative time signal from satellite atomic clocks.

Reference clocks provide:
- **Independence** from internet-based NTP pools and upstream servers
- **Sub-microsecond accuracy** when using PPS discipline
- **Resilience** against network outages and GPS spoofing attacks
- **Compliance** with audit requirements for traceable time sources

GPS receivers output two signals: NMEA sentences (coarse position and time) and a PPS pulse (precise second boundary). The NMEA data gives you time within milliseconds; the PPS signal narrows that down to microseconds.

## Comparison: NTPsec vs Chrony vs LinuxPTP for Reference Clocks

| Feature | NTPsec refclock | Chrony refclock | LinuxPTP (ptp4l/phc2sys) |
|---------|----------------|-----------------|---------------------------|
| **PPS Support** | Yes (SHM/PPS) | Yes (PPS/REFCLK) | Yes (PHC/PPS) |
| **NMEA Support** | Yes (driver 20) | Yes (SHM driver) | Via gpsd bridge |
| **GPSD Integration** | Yes | Yes | Partial |
| **PTP (IEEE 1588)** | No | Limited | Native (primary purpose) |
| **Stratum** | 1 | 1 | 1 (with grandmaster) |
| **Accuracy** | ~1-10 μs PPS | ~1-10 μs PPS | Sub-microsecond (hardware) |
| **Config Complexity** | Moderate | Low | High |
| **Package Size** | ~2 MB | ~1 MB | ~500 KB |
| **Active Development** | Yes (ntpsec.org) | Yes (chrony-project) | Yes (linuxptp.sourceforge) |
| **Docker Deployable** | Yes (privileged) | Yes (privileged) | Yes (privileged + cap) |
| **Stars / Activity** | 278+ (2026-05) | 204+ (2026-04) | 381+ (2026-05) |

## Deploying NTPsec with GPS Reference Clock

NTPsec is a hardened fork of the classic NTP daemon, focused on security and modern timekeeping. It includes dedicated reference clock drivers for GPS receivers.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  ntpsec-refclock:
    image: ntpsec/ntpsec:latest
    container_name: ntpsec-refclock
    restart: unless-stopped
    privileged: true
    devices:
      - /dev/gps0:/dev/gps0
      - /dev/pps0:/dev/pps0
    volumes:
      - ./ntpsec.conf:/etc/ntpsec/ntp.conf:ro
      - ntpsec-data:/var/lib/ntpsec
    network_mode: host
    cap_add:
      - SYS_TIME
      - SYS_NICE

volumes:
  ntpsec-data:
```

### NTPsec Configuration (`ntpsec.conf`)

```conf
# NTPsec Reference Clock Configuration
# Stratum 1 server with GPS + PPS

# GPS NMEA driver (driver 20) via shared memory from gpsd
server 127.127.20.0 mode 16 minpoll 4 maxpoll 4 prefer
fudge 127.127.20.0 time1 0.0 flag1 1 flag2 0 flag3 0 flag4 0

# PPS driver (driver 22) via kernel PPS line discipline
server 127.127.22.0 minpoll 3 maxpoll 3
fudge 127.127.22.0 time2 0.0 flag1 1 flag2 0

# Restrict access — only allow local queries
restrict default noquery nomodify nopeer
restrict 127.0.0.1
restrict ::1

# Drift file and log
driftfile /var/lib/ntpsec/ntp.drift
logfile /var/log/ntpsec/ntp.log
```

### Key Configuration Notes

- `flag1 1` enables PPS signal processing for the GPS driver
- `time1` and `time2` are cable delay corrections (calibrate for your setup)
- `minpoll 3` and `maxpoll 4` set polling intervals (8-16 seconds) for reference clocks
- The `prefer` keyword tells NTPsec to prefer this source over others

## Deploying Chrony with GPS Reference Clock

Chrony is a modern NTP implementation known for fast convergence and excellent reference clock support. It is the default NTP daemon on many Linux distributions.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  chrony-refclock:
    image: chrony:latest
    container_name: chrony-refclock
    restart: unless-stopped
    privileged: true
    devices:
      - /dev/gps0:/dev/gps0
      - /dev/pps0:/dev/pps0
    volumes:
      - ./chrony.conf:/etc/chrony/chrony.conf:ro
      - chrony-data:/var/lib/chrony
    network_mode: host
    cap_add:
      - SYS_TIME

volumes:
  chrony-data:
```

### Chrony Configuration (`chrony.conf`)

```conf
# Chrony Reference Clock Configuration
# Stratum 1 server with GPS + PPS

# PPS reference clock via /dev/pps0
refclock PPS /dev/pps0 lock NMEA refid GPS prefer

# NMEA data from gpsd via shared memory
refclock SHM 0 offset 0.0 delay 0.2 refid NMEA poll 4

# Allow NTP clients on the local network
allow 192.168.0.0/16
allow 10.0.0.0/8

# Serve time even if not synchronized (for reference clock mode)
local stratum 1 orphan

# Drift and tracking
driftfile /var/lib/chrony/drift
dumponexit
dumpdir /var/lib/chrony
log tracking statistics

# Keyfile (optional, for NTS)
keyfile /etc/chrony/chrony.keys
```

### Chrony Advantages

- **Fast convergence**: Chrony typically synchronizes within seconds of receiving PPS signals
- `local stratum 1 orphan` mode allows serving time even during GPS signal loss
- `refclock PPS` directive provides native kernel PPS support without SHM overhead
- `log tracking statistics` provides detailed discipline metrics for monitoring

## Deploying LinuxPTP for Precision Time Protocol

LinuxPTP implements IEEE 1588 Precision Time Protocol (PTP), which achieves sub-microsecond accuracy — significantly better than NTP. It is the right choice when your infrastructure requires hardware timestamping.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  linuxptp-grandmaster:
    image: linuxptp/linuxptp:latest
    container_name: linuxptp-gm
    restart: unless-stopped
    privileged: true
    devices:
      - /dev/gps0:/dev/gps0
      - /dev/pps0:/dev/pps0
    volumes:
      - ./ptp4l.conf:/etc/linuxptp/ptp4l.conf:ro
      - ./phc2sys.conf:/etc/linuxptp/phc2sys.conf:ro
    network_mode: host
    cap_add:
      - NET_ADMIN
      - SYS_TIME
```

### PTP Configuration (`ptp4l.conf`)

```conf
# PTP Grand Master Configuration
# Acts as the primary time source for PTP domain

[global]
# Use GPS/PPS as the grandmaster clock
gmCapable        1
priority1        128
priority2        128
domainNumber     0

# Hardware timestamping on the primary interface
timeStamping     hardware
delay_mechanism  E2E

# GPS PPS as the clock source
clock_servo      auto
pi_proportional_const 0.0
pi_integral_const    0.0

# Logging
summary_interval   4
logMinDelayReqInterval 0
```

### phc2sys Configuration (`phc2sys.conf`)

```conf
# Sync system clock to PHC (PTP Hardware Clock)
# This bridges PTP time to the OS system clock

-s /dev/ptp0    # Source: PTP hardware clock
-c CLOCK_REALTIME  # Destination: system clock
-O 0             # Offset (calibrate for your setup)
-w               # Wait for PTP sync before adjusting
```

## GPS Hardware Setup

All three implementations require similar hardware:

1. **GPS Receiver with PPS output** — common choices include:
   - u-blox NEO-M8N/M9N module (~$15-25)
   - Adafruit Ultimate GPS Breakout (~$40)
   - Navisys GR701-W USB GPS (~$80)

2. **USB-to-Serial adapter** (if using UART GPS modules)

3. **PPS kernel module** — ensure `pps-ldisc` and `pps-gpio` are loaded:

```bash
# Load PPS kernel modules
sudo modprobe pps-ldisc
sudo modprobe pps-gpio

# Make persistent
echo "pps-ldisc" | sudo tee -a /etc/modules-load.d/pps.conf
echo "pps-gpio" | sudo tee -a /etc/modules-load.d/pps.conf
```

4. **gpsd** — recommended as the GPS daemon that all three NTP implementations can read from:

```yaml
  gpsd:
    image: catatnight/gpsd:latest
    container_name: gpsd
    restart: unless-stopped
    devices:
      - /dev/gps0:/dev/ttyUSB0
    command: -G -n -D 2 /dev/ttyUSB0
    network_mode: host
```

## Monitoring and Verification

Verify your reference clock is working correctly:

```bash
# NTPsec: Check reference clock status
ntpq -c pe -c rv

# Chrony: Check tracking and sources
chronyc sources -v
chronyc tracking

# LinuxPTP: Check grandmaster status
pmc -u -b 0 'GET GRANDMASTER_SETTINGS_NP'
```

Look for:
- **Stratum 1** in the output
- **GPS** or **PPS** as the reference ID
- **Offset** under 10 microseconds for PPS-disciplined clocks
- **Jitter** values in the sub-microsecond range

## Choosing the Right Reference Clock Solution

| Scenario | Recommendation |
|----------|---------------|
| Simple NTP stratum 1 server | **Chrony** — easiest setup, fast convergence |
| Security-hardened NTP server | **NTPsec** — reduced attack surface, modern security |
| Sub-microsecond precision needed | **LinuxPTP** — IEEE 1588, hardware timestamping |
| Existing NTP infrastructure | **NTPsec** — drop-in replacement for classic NTP |
| Mixed PTP/NTP environment | **Chrony + LinuxPTP** — Chrony serves NTP, PTP handles hardware sync |

## Why Self-Host Your Own Time Source?

Running your own stratum 1 NTP server with a GPS reference clock provides several critical advantages for infrastructure operators:

**Independence from external time sources.** Public NTP pools can be spoofed, rate-limited, or become unavailable during network outages. A local reference clock ensures your infrastructure always has access to accurate time, even when internet connectivity is disrupted. For financial trading systems, telecom networks, and industrial control systems, this independence is not optional — it is a compliance requirement.

**Regulatory compliance.** Many audit frameworks (PCI DSS, SOX, HIPAA) require traceable, accurate time sources. A GPS-referenced stratum 1 server provides a verifiable chain of custody from atomic clocks to your server logs. This matters during incident investigations, forensic analysis, and compliance audits where timestamp accuracy directly affects the credibility of evidence.

**Network performance.** Eliminating the round-trip latency to external NTP pools reduces jitter and improves timekeeping stability. For high-frequency trading, distributed databases, and synchronized media production, every microsecond matters.

For broader NTP server configuration, see our [NTP comparison guide](../2026-05-02-chrony-vs-ntpsec-vs-openntpd-self-hosted-ntp-server-guide-2026/). For monitoring your time synchronization health, our [NTP monitoring guide](../2026-05-07-self-hosted-ntp-time-sync-monitoring-chronyc-ntpstat-ntpviz-guide/) covers chronyc, ntpviz, and ntpstat. For PTP-specific precision time, our [PTP server guide](../2026-05-10-self-hosted-ptp-servers-linuxptp-chrony-ntpsec-precision-time-sync/) covers grandmaster deployment in detail.

## FAQ

### What accuracy can I expect from a GPS reference clock?

With NMEA data alone, accuracy is typically 1-10 milliseconds. Adding PPS (Pulse Per Second) discipline improves this to 1-10 microseconds. LinuxPTP with hardware timestamping can achieve sub-microsecond accuracy (100-500 nanoseconds) on supported NICs.

### Do I need a dedicated GPS antenna?

For indoor servers, a small active GPS antenna with an SMA-to-U.FL cable works well. For best accuracy, place the antenna with a clear view of the sky. USB GPS dongles with built-in antennas are adequate for most data center deployments.

### Can I run these in Docker containers?

Yes, but you need `privileged: true`, `network_mode: host`, and device passthrough (`/dev/gps0`, `/dev/pps0`). The container also needs `SYS_TIME` and optionally `SYS_NICE` capabilities. Some setups require running gpsd on the host and sharing its SHM segments with the container.

### What happens when GPS signal is lost?

Chrony with `local stratum 1 orphan` continues serving time at the last known accuracy. NTPsec marks the reference clock as faulty and falls back to other configured peers. LinuxPTP enters holdover mode, maintaining time based on its oscillator's stability.

### Is a GPS reference clock better than syncing to pool.ntp.org?

For most home labs, pool.ntp.org is perfectly adequate. A GPS reference clock becomes valuable when you need: independence from internet connectivity, regulatory compliance with traceable time, sub-millisecond accuracy, or protection against NTP spoofing attacks.

### Can I use a Raspberry Pi as a stratum 1 server?

Yes. The Raspberry Pi 4/5 with a USB GPS module (like the Adafruit Ultimate GPS) makes an excellent low-power stratum 1 server. Connect the GPS PPS output to a GPIO pin, configure the PPS kernel module, and run Chrony or NTPsec.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted NTP Reference Clock: GPS/PPS Time Sources with NTPsec, Chrony & LinuxPTP",
  "description": "Compare NTPsec, Chrony, and LinuxPTP for deploying self-hosted stratum 1 NTP servers with GPS/PPS reference clocks. Includes Docker Compose configs and monitoring guides.",
  "datePublished": "2026-05-18",
  "dateModified": "2026-05-18",
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
