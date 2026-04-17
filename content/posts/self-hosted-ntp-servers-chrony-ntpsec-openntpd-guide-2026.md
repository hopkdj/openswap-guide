---
title: "Best Self-Hosted NTP Servers 2026: Chrony vs NTPsec vs OpenNTPd"
date: 2026-04-17
tags: ["comparison", "guide", "self-hosted", "infrastructure"]
draft: false
description: "Complete comparison of self-hosted NTP server implementations for 2026. Learn how to set up Chrony, NTPsec, and OpenNTPd for accurate time synchronization on your homelab or enterprise network."
---

Accurate time synchronization is the invisible backbone of every reliable infrastructure. When clocks drift across your servers, everything breaks: TLS certificates fail validation, log correlation becomes impossible, distributed databases reject writes, cron jobs execute at wrong times, and Kerberos authentication silently fails. Yet despite its critical importance, time synchronization remains one of the most overlooked aspects of self-hosted infrastructure.

In 2026, three serious open-source NTP server implementations dominate the landscape: **Chrony**, **NTPsec**, and **OpenNTPd**. Each takes a fundamentally different approach to the same problem, and choosing the right one for your environment can mean the difference between sub-millisecond precision and seconds of drift.

This guide compares all three implementations head-to-head and provides complete Docker and bare-metal installation instructions for each.

## Why Self-Host Your Own NTP Server

Running your own NTP server isn't about replacing public pools — it's about building a reliable time infrastructure layer for your internal network. Here's why it matters:

**Network reliability.** If your internet connection drops, public NTP servers become unreachable. A local NTP server with upstream peering continues serving accurate time to every machine on your LAN during outages.

**Security.** Every NTP query to a public server reveals your IP address, query frequency, and traffic patterns. A local NTP server eliminates this telemetry. Additionally, NTP amplification attacks target public pools; keeping your queries local reduces your attack surface.

**Performance.** Local NTP servers respond in under a millimeter on a LAN versus 10-200ms over the internet. For applications requiring tight clock synchronization — financial trading systems, distributed databases like CockroachDB, or real-time media streaming — this matters.

**Compliance.** Standards like PCI-DSS, SOC 2, and ISO 27001 require documented time synchronization with traceable sources. A self-hosted NTP hierarchy gives you full audit control.

**IoT and air-gapped networks.** Devices without internet access — industrial controllers, security cameras, embedded sensors — still need synchronized clocks. A local NTP server solves this cleanly.

## Understanding NTP Architecture

Before comparing implementations, it helps to understand the NTP hierarchy:

| Stratum | Description | Example |
|---------|-------------|---------|
| Stratum 0 | Atomic clocks, GPS receivers | Hardware reference clocks |
| Stratum 1 | Directly synchronized to Stratum 0 | NTP servers with GPS/atomic clock |
| Stratum 2 | Synchronized to Stratum 1 servers | Most public pool servers |
| Stratum 3 | Synchronized to Stratum 2 | Your local NTP server |
| Stratum 4+ | Downstream clients | Desktops, laptops, IoT devices |

A typical self-hosted setup acts as Stratum 3 or 4, peering with multiple Stratum 2 public servers and distributing time to internal clients. For higher precision, you can connect a Stratum 1 reference clock via GPS or a PPS (Pulse Per Second) signal from a radio receiver.

## Chrony: The Modern Performance Champion

Chrony has become the default NTP implementation on most modern Linux distributions, including Fedora, RHEL, CentOS Stream, and openSUSE. It was designed from the ground up to handle environments where the NTP server isn't always connected — making it ideal for laptops, VMs, and containers.

### Key Advantages

- **Faster initial synchronization.** Chrony typically converges on accurate time within seconds, compared to minutes for traditional ntpd.
- **Better handling of network interruptions.** Chrony tracks clock drift rate during offline periods and applies corrections immediately when connectivity returns.
- **Superior VM clock management.** Virtual machines experience clock skew due to CPU scheduling. Chrony includes specific compensation algorithms for virtualized environments.
- **Low resource footprint.** The chronyd daemon uses approximately 2-4 MB of RAM and near-zero CPU when stable.
- **Active development.** The project receives regular updates, with maintainers actively responding to bug reports and feature requests.

### Installation

#### On Debian/Ubuntu

```bash
sudo apt update
sudo apt install chrony
sudo systemctl enable chrony
sudo systemctl start chrony
```

#### On RHEL/Fedora/CentOS

```bash
sudo dnf install chrony
sudo systemctl enable chronyd
sudo systemctl start chronyd
```

#### Docker Deployment

```yaml
version: "3.8"

services:
  chrony:
    image: cturra/ntp:latest
    container_name: chrony-ntp
    restart: unless-stopped
    cap_add:
      - SYS_TIME
    ports:
      - "123:123/udp"
    environment:
      - NTP_SERVERS=0.pool.ntp.org 1.pool.ntp.org 2.pool.ntp.org
      - LOG_LEVEL=info
    volumes:
      - chrony-data:/var/lib/chrony
      - /etc/localtime:/etc/localtime:ro

volumes:
  chrony-data:
```

For a full NTP server (accepting client connections), use the Docker Compose configuration below with a custom configuration:

```dockerfile
FROM ubuntu:24.04

RUN apt-get update && apt-get install -y chrony && rm -rf /var/lib/apt/lists/*

COPY chrony.conf /etc/chrony/chrony.conf

EXPOSE 123/udp

CMD ["chronyd", "-f", "/etc/chrony/chrony.conf", "-d"]
```

With `chrony.conf`:

```
# Upstream NTP servers
pool 0.pool.ntp.org iburst maxsources 4
pool 1.pool.ntp.org iburst maxsources 4
pool 2.pool.ntp.org iburst maxsources 4

# Allow LAN clients to query
allow 192.168.1.0/24
allow 10.0.0.0/8

# Serve time even when not synchronized to upstream
local stratum 10

# Record drift
driftfile /var/lib/chrony/chrony.drift

# Log directory
logdir /var/log/chrony
log measurements statistics tracking
```

### Essential Chrony Commands

```bash
# Check synchronization status
chronyc tracking

# View NTP sources and their quality
chronyc sources -v

# View source statistics
chronyc sourcestats -v

# Manual server polling
chronyc makestep

# View activity report
chronyc activity
```

The `chronyc tracking` output shows critical metrics:

```
Reference ID    : C0A80101 (ntp.ubuntu.com)
Stratum         : 3
Ref time (UTC)  : Thu Apr 17 03:15:42 2026
System time     : 0.000123456 seconds fast of NTP time
Last offset     : +0.000098765 seconds
RMS offset      : 0.000234567 seconds
Frequency       : 12.345 ppm slow
Residual freq   : +0.012 ppm
Skew            : 0.567 ppm
Root delay      : 0.012345678 seconds
Root dispersion : 0.001234567 seconds
Update interval : 64.2 seconds
Leap status     : Normal
```

The **skew** value is particularly important — it represents the uncertainty in your frequency estimate. Lower is better. A healthy Chrony instance shows skew under 1 ppm after 24 hours of operation.

## NTPsec: The Security-Hardened Successor

NTPsec is a security-focused fork of the classic ntpd daemon, maintained by the NTP Security project. It was created in response to numerous CVEs in the original NTP reference implementation. Every line of code has been audited, dangerous features removed, and the codebase significantly reduced.

### Key Advantages

- **Minimal attack surface.** NTPsec has eliminated approximately 60% of the original ntpd codebase, removing autokey, mode 6/7 queries, and other legacy features that were common vulnerability sources.
- **Dropped privileges.** The daemon runs unprivileged after binding to port 123, limiting the impact of any potential exploit.
- **No scripting language.** Unlike classic ntpd, NTPsec contains no Python, no shell interpreters, and no dynamic code loading.
- **Strict input validation.** Every network packet is validated against a strict schema before processing.
- **Compatibility.** NTPsec speaks standard NTPv4 and is fully interoperable with all other NTP implementations.
- **NTPng roadmap.** The project is actively developing NTP Network Time Next Generation, which addresses fundamental protocol limitations.

### Installation

#### On Debian/Ubuntu

```bash
sudo apt update
sudo apt install ntpsec
sudo systemctl enable ntpsec
sudo systemctl start ntpsec
```

#### From Source (Latest Version)

```bash
# Install build dependencies
sudo apt install python3 waf build-essential libcap-dev libssl-dev

# Download and build
git clone https://gitlab.com/NTPsec/ntpsec.git
cd ntpsec
./waf configure --refclock=all
./waf build
sudo ./waf install
```

#### Docker Deployment

```yaml
version: "3.8"

services:
  ntpsec:
    image: ntpsec/ntpsec:latest
    container_name: ntpsec-server
    restart: unless-stopped
    cap_add:
      - SYS_TIME
    ports:
      - "123:123/udp"
    volumes:
      - ./ntpsec.conf:/etc/ntpsec/ntp.conf:ro
      - ntpsec-drift:/var/lib/ntpsec
```

With `ntpsec.conf`:

```
# Security defaults
disable monitor    # Prevents amplification attacks
restrict default nomodify notrap nopeer noquery
restrict -6 default nomodify notrap nopeer noquery

# Allow LAN queries
restrict 192.168.1.0 mask 255.255.255.0 nomodify notrap nopeer
restrict 10.0.0.0 mask 255.0.0.0 nomodify notrap nopeer

# Upstream servers with authentication
server 0.pool.ntp.org iburst
server 1.pool.ntp.org iburst
server 2.pool.ntp.org iburst
server 3.pool.ntp.org iburst

# Drift and stats
driftfile /var/lib/ntpsec/ntp.drift
statsdir /var/log/ntpsec/
statistics loopstats peerstats clockstats

# Run as unprivileged user after binding
user ntpsec
```

### Essential NTPsec Commands

```bash
# View peers and synchronization status
ntpq -p

# Show detailed peer statistics
ntpq -c rv

# View system peer information
ntpwait

# Check daemon status
ntpsec-config --version
```

The `ntpq -p` output format:

```
     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
*time.nist.gov   .ACTS.           1 u   45   64   377  12.345  -0.234   0.567
+ntp.ubuntu.com  .POOL.          16 p   12   64   377  8.901   0.123   0.456
-ntp1.example.ne 10.0.0.1        2 u   32   64   377  15.678  -1.234   1.234
```

The asterisk (*) marks the current system peer, plus (+) marks good candidates, and minus (-) marks excluded sources.

## OpenNTPd: Simplicity from the OpenBSD Project

OpenNTPd comes from the OpenBSD project and embodies their philosophy: secure by default, simple to configure, and "just works." It's the smallest and simplest of the three implementations, with a codebase of approximately 8,000 lines — compared to Chrony's 20,000+ and NTPsec's 45,000+.

### Key Advantages

- **Simplicity.** A working configuration can be as simple as two lines: one server directive and one listen directive. There are no complex tuning parameters to understand.
- **Privilege separation.** OpenNTPd uses OpenBSD-style pledge and unveil system calls to restrict what the daemon can do, even in the event of a compromise. On Linux, this is approximated with seccomp filters.
- **DNS-based server selection.** Instead of manually selecting individual NTP servers, OpenNTPd resolves DNS hostnames and automatically cycles through results, providing built-in load distribution.
- **No drift file needed.** OpenNTPd adjusts clock rate without requiring a persistent drift file, simplifying container deployments.
- **BSD portability.** Runs on OpenBSD, FreeBSD, NetBSD, and Linux with identical behavior.

### Limitations

- **Lower precision.** OpenNTPd targets accuracy within tens of milliseconds, not microseconds. It's not suitable for applications requiring sub-millisecond synchronization.
- **No NTP server mode on older versions.** Versions before 6.2 could only act as NTP clients. The server functionality is relatively new and less mature than Chrony or NTPsec.
- **Fewer monitoring tools.** No equivalent to `chronyc` or `ntpq` — you check status via syslog messages.

### Installation

#### On Debian/Ubuntu

```bash
sudo apt update
sudo apt install openntpd
sudo systemctl enable openntpd
sudo systemctl start openntpd
```

#### On OpenBSD (Pre-installed)

OpenNTPd is included in the base OpenBSD installation and runs by default:

```bash
# Check status
rcctl check ntpd

# Restart if needed
rcctl restart ntpd
```

#### Docker Deployment

```yaml
version: "3.8"

services:
  openntpd:
    image: crazymax/openntpd:latest
    container_name: openntpd-server
    restart: unless-stopped
    cap_add:
      - SYS_TIME
    ports:
      - "123:123/udp"
    environment:
      - TZ=UTC
    volumes:
      - ./openntpd.conf:/etc/openntpd/ntpd.conf:ro
```

With `openntpd.conf`:

```
# Simple, minimal configuration

# Listen on all interfaces for client queries
listen on *

# Use DNS-based pool (automatically resolves multiple servers)
servers pool.ntp.org

# Or specify individual servers
# server time.nist.gov
# server time.google.com
# server time.cloudflare.com

# Set time on startup if offset is significant
# (only works with appropriate capabilities)
sensor *
```

### Checking OpenNTPd Status

```bash
# OpenNTPd logs to syslog
sudo journalctl -u openntpd --no-pager

# On OpenBSD, use the control utility
ntpctl -s status
```

Expected output:

```
all 3 peers valid, clock synced, stratum 3
```

## Head-to-Head Comparison

| Feature | Chrony | NTPsec | OpenNTPd |
|---------|--------|--------|----------|
| **Precision** | Sub-microsecond (±0.001ms) | Sub-millisecond (±0.1ms) | ~10-50ms |
| **RAM usage** | 2-4 MB | 5-8 MB | 1-2 MB |
| **Configuration complexity** | Medium | High | Low |
| **Converge time** | 5-30 seconds | 2-10 minutes | 1-5 minutes |
| **VM compensation** | Excellent | Good | None |
| **Offline drift tracking** | Yes | Partial | No |
| **Security hardening** | Good | Excellent | Excellent |
| **Privilege separation** | Limited | Full | Full (pledge/unveil) |
| **Monitoring tools** | chronyc (rich) | ntpq (standard) | syslog only |
| **Server mode** | Mature | Mature | Available since 6.2 |
| **Active development** | Very active | Active | Moderate |
| **Docker-friendly** | Excellent | Good | Good |
| **Default on** | RHEL, Fedora, SUSE | Gentoo (optional) | OpenBSD |
| **Best use case** | General purpose, VMs, containers | Security-critical, compliance | Simple setups, BSD systems |

## Choosing the Right NTP Server

### Choose Chrony if:

- You run virtual machines or containers (superior VM compensation)
- You need sub-millisecond precision
- Your network has intermittent connectivity (laptops, mobile servers)
- You want the best monitoring and debugging tools
- You're on RHEL, Fedora, or SUSE (it's already installed)

### Choose NTPsec if:

- Security is your top priority (regulated industries, financial services)
- You need to pass security audits that scrutinize every daemon
- You want the smallest possible attack surface in an NTP implementation
- You value code auditability and a minimal, clean codebase
- You're migrating from classic ntpd and want drop-in compatibility

### Choose OpenNTPd if:

- You want the simplest possible configuration
- You're running OpenBSD or another BSD variant
- Millisecond-level precision is sufficient (most web applications)
- You value developer productivity over nanosecond optimization
- You deploy in containers and want a lightweight time service

## Advanced: Building a Stratum 1 Server with GPS

For the ultimate self-hosted time setup, you can build a Stratum 1 server using a GPS receiver with PPS (Pulse Per Second) output. This gives you time accuracy of approximately ±1 microsecond, traceable to atomic clocks.

### Hardware Requirements

- USB GPS receiver with PPS output (e.g., Garmin GPS 18x, u-blox NEO-M8T)
- Linux server with GPIO or USB-to-serial adapter that supports PPS
- GPS antenna with clear sky view

### Chrony Configuration for Stratum 1

```
# PPS reference clock
refclock PPS /dev/pps0 lock GPSD prefer

# GPS daemon as secondary reference
refclock SHM 0 refid GPSD precision 1e-1

# GPSD configuration
refclock SHM 1 refid NMEA precision 1e1

# Allow LAN clients
allow 192.168.0.0/16

# Local fallback
local stratum 10

driftfile /var/lib/chrony/chrony.drift
logdir /var/log/chrony
log measurements statistics tracking
```

### Docker Compose for GPS-Stratum Setup

```yaml
version: "3.8"

services:
  gpsd:
    image: crazymax/gpsd:latest
    container_name: gpsd
    restart: unless-stopped
    devices:
      - /dev/ttyUSB0:/dev/ttyUSB0
      - /dev/pps0:/dev/pps0
    ports:
      - "2947:2947"
    environment:
      - GPSD_DEVICES=/dev/ttyUSB0
      - GPSD_OPTIONS=-n

  chrony:
    image: cturra/ntp:latest
    container_name: chrony-stratum1
    restart: unless-stopped
    cap_add:
      - SYS_TIME
    ports:
      - "123:123/udp"
    volumes:
      - ./stratum1-chrony.conf:/etc/chrony/chrony.conf:ro
    depends_on:
      - gpsd
```

## Monitoring and Alerting

Regardless of which NTP server you choose, monitoring is essential. Set up alerts for:

- **Offset exceeding 100ms** — indicates synchronization problems
- **Stratum increasing** — your server is losing sync with upstream
- **Reach value dropping** — network issues with upstream servers
- **Frequency drift exceeding 10 ppm** — hardware clock issues

### Prometheus Metrics Exporter

```yaml
services:
  ntp-exporter:
    image: peterbourgon/ntp-exporter
    container_name: ntp-exporter
    ports:
      - "9559:9559"
    network_mode: "host"
```

Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: "ntp"
    static_configs:
      - targets: ["localhost:9559"]
```

### Grafana Dashboard Alerts

Create alerts for these key metrics:

```
# NTP offset too high
ntp_offset_seconds > 0.1

# NTP stratum too high (losing sync)
ntp_stratum > 5

# No reachable NTP sources
ntp_reachable_sources == 0
```

## Conclusion

Time synchronization is foundational infrastructure — the kind of thing you only notice when it breaks, and when it does, everything breaks together. In 2026, all three implementations are solid choices, but they serve different needs:

- **Chrony** is the best all-around choice for most self-hosters. Its speed, VM awareness, and excellent monitoring tools make it the default recommendation.
- **NTPsec** is the right choice when security auditing and minimal attack surface are non-negotiable requirements.
- **OpenNTPd** is perfect for simple setups where "good enough" precision and dead-simple configuration win.

Start with Chrony unless you have a specific reason to choose otherwise. Set up monitoring. Test your NTP hierarchy by temporarily blocking upstream servers. And remember: accurate time is not optional — it's the foundation every other service builds upon.
