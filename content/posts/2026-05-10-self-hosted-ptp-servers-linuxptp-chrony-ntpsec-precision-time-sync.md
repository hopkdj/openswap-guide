---
title: "Self-Hosted PTP Servers: linuxptp vs chrony vs NTPsec for Sub-Microsecond Time Sync"
date: "2026-05-10"
tags: ["ptp", "time-sync", "ntp", "linuxptp", "chrony", "ntpsec", "infrastructure"]
draft: false
---

Precision Time Protocol (PTP, IEEE 1588) delivers sub-microsecond clock synchronization across local networks — orders of magnitude more precise than NTP's millisecond-level accuracy. For applications like financial trading, industrial automation, telecommunications, and distributed test systems, PTP is not optional; it's a fundamental infrastructure requirement.

This guide compares three self-hosted PTP implementations: **linuxptp**, **chrony** (with PTP support), and **NTPsec** (with PTP features). Each provides different trade-offs between precision, ease of deployment, and protocol feature coverage.

## Why Precision Time Sync Matters

Network time synchronization is foundational to distributed systems. When clocks drift across servers, logs become unreliable, scheduled tasks misfire, database transactions conflict, and debugging becomes nearly impossible.

| Use Case | Required Precision | Protocol |
|----------|-------------------|----------|
| Financial trading (HFT) | < 1 microsecond | PTP (IEEE 1588) |
| Industrial automation (PROFINET) | < 1 microsecond | PTP |
| 5G telecommunications | < 1.5 microseconds | PTP |
| Distributed databases | < 1 millisecond | NTP or PTP |
| Log correlation | < 10 milliseconds | NTP |
| General server sync | < 100 milliseconds | NTP |

NTP (Network Time Protocol) achieves 1-10 ms accuracy over LAN — sufficient for most server workloads. But when you need sub-microsecond precision, NTP's software-only timestamping introduces too much jitter from OS scheduling, interrupt handling, and network stack delays.

PTP solves this with hardware timestamping at the NIC level, boundary clock hierarchies, and path delay measurement that accounts for asymmetric network links.

## Understanding the PTP Architecture

PTP uses a hierarchical master-slave (grandmaster-client) model:

1. **Grandmaster Clock**: The most accurate time source in the network (often GPS or atomic clock referenced)
2. **Boundary Clocks**: Intermediate devices that synchronize upstream and serve time downstream
3. **Ordinary Clocks**: End devices that consume time from the network
4. **Transparent Clocks**: Network switches that correct PTP messages for their own transit delay

Key PTP message types:
- **Sync**: Grandmaster sends current time to clients
- **Follow_Up**: Precision timestamp correction for Sync messages
- **Delay_Req / Delay_Resp**: Round-trip path delay measurement
- **Announce**: Grandmaster election and clock quality information

## PTP Implementation Comparison

| Feature | linuxptp | chrony (PTP) | NTPsec (PTP) |
|---------|----------|--------------|--------------|
| **PTP version** | IEEE 1588-2008 (v2) | IEEE 1588-2008 (v2) | IEEE 1588-2008 (v2) |
| **Hardware timestamping** | Yes (full) | Yes (limited) | Yes (limited) |
| **Software timestamping** | Yes | Yes | Yes |
| **Boundary clock** | Yes (ptp4l) | No | No |
| **Ordinary clock** | Yes (ptp4l) | Yes | Yes |
| **Transparent clock** | Yes (phc2sys) | No | No |
| **PTP profiles** | Default, 802.1AS, Telecom | Default only | Default only |
| **NTP interoperability** | Via phc2sys + ntpd/chrony | Native (hybrid mode) | Native (hybrid mode) |
| **Configuration complexity** | Medium | Low | Medium |
| **Active development** | Yes (378 stars) | Yes (major project) | Yes (security-focused) |
| **Primary language** | C | C | C |
| **License** | GPL-2.0 | GPL-2.0 | BSD |

### linuxptp: The Dedicated PTP Stack

**linuxptp** is the reference PTP implementation for Linux, developed by Richard Cochran. It provides the most complete PTPv2 feature set available on Linux, including hardware timestamping, boundary clocks, and multiple PTP profiles.

Core components:
- **ptp4l**: The main PTP daemon — handles Sync, Delay, and Announce messages
- **phc2sys**: Synchronizes the system clock to the PTP Hardware Clock (PHC)
- **pmc**: PTP management client for monitoring and configuration
- **hwstamp_ctl**: Controls hardware timestamping on network interfaces

Key strengths:
- Most complete PTPv2 implementation on Linux
- Supports all PTP port states and message types
- Multiple PTP profiles (default, 802.1AS/AVB, telecom)
- Active development with regular releases
- Works with any Linux NIC that supports hardware timestamping

### chrony: The Hybrid NTP/PTP Solution

**chrony** is primarily an NTP implementation but includes PTP support through its `ptp` directive. It's ideal for environments where you need both NTP compatibility and PTP precision from a single daemon.

Key strengths:
- Unified NTP and PTP configuration in one daemon
- Excellent clock discipline algorithm
- Fast convergence on startup
- Built-in monitoring via `chronyc`
- Large user base and extensive documentation

### NTPsec: The Security-Hardened NTP/PTP

**NTPsec** is a security-focused fork of the classic NTP reference implementation. Its PTP support provides similar functionality to chrony's but with an emphasis on security hardening and auditability.

Key strengths:
- Security-hardened codebase (buffer overflow protections, privilege separation)
- Familiar NTP configuration syntax
- Active security maintenance
- Supports both NTP and PTP from a single daemon

## Deployment with Docker and Linux

### linuxptp Docker Setup

linuxptp requires access to the PTP Hardware Clock (PHC) device, typically `/dev/ptp0`:

```yaml
version: "3.8"
services:
  ptp4l:
    image: ghcr.io/linuxptp/linuxptp:latest
    container_name: ptp4l
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
      - SYS_TIME
    devices:
      - /dev/ptp0:/dev/ptp0
    network_mode: host
    command: >
      -f /etc/linuxptp/ptp4l.conf
      -i eth0
      -m
    volumes:
      - ./ptp4l.conf:/etc/linuxptp/ptp4l.conf:ro
```

Configuration (`ptp4l.conf`):

```ini
# Grandmaster configuration
[global]
clockIdentity 0x000000FFFE000000
priority1 128
priority2 128
domainNumber 0
free_running 0
freq_est_interval 1
logging_level 6

# Interface settings
[eth0]
timestamping hardware
delay_mechanism E2E
network_transport L2
```

For a slave (ordinary) clock:

```ini
[global]
priority1 255
priority2 255

[eth0]
timestamping hardware
delay_mechanism E2E
network_transport L2
```

### chrony PTP Configuration

chrony handles both NTP and PTP from a single configuration file (`/etc/chrony/chrony.conf`):

```ini
# NTP sources (fallback)
server 0.pool.ntp.org iburst
server 1.pool.ntp.org iburst

# PTP interface
ptp /dev/ptp0 poll 0 dpoll 0

# Local reference clock (fallback when no external source)
local stratum 10

# Allow PTP to discipline the system clock
makestep 1.0 3

# Drift file
driftfile /var/lib/chrony/drift

# Log directory
logdir /var/log/chrony
log measurements statistics tracking
```

Monitor PTP status:

```bash
chronyc sources -v
chronyc tracking
chronyc sourcestats -v
```

### NTPsec PTP Configuration

NTPsec uses familiar `ntp.conf` syntax with PTP extensions:

```ini
# NTP sources
pool 0.pool.ntp.org iburst

# PTP interface
ptp device /dev/ptp0 poll 0

# Local clock
server 127.127.1.0
fudge 127.127.1.0 stratum 10

# Drift file
driftfile /var/lib/ntpsec/ntp.drift

# Statistics
statsdir /var/log/ntpsec/
statistics loopstats peerstats clockstats
```

Verify synchronization:

```bash
ntpq -p
ntpmon
```

## Performance and Precision

| Implementation | LAN Precision (hardware TS) | LAN Precision (software TS) | Convergence Time |
|----------------|----------------------------|----------------------------|------------------|
| linuxptp | < 100 nanoseconds | 1-10 microseconds | < 10 seconds |
| chrony (PTP) | 1-10 microseconds | 10-100 microseconds | < 5 seconds |
| NTPsec (PTP) | 1-10 microseconds | 10-100 microseconds | < 10 seconds |

For maximum precision, **hardware timestamping** is essential. This requires a NIC that supports PTP hardware timestamping (check with `ethtool -T eth0`). Most modern server NICs (Intel X710, X520, Mellanox ConnectX) support this feature.

## Hardware Timestamping Requirements

Verify your NIC supports hardware timestamping:

```bash
ethtool -T eth0
# Look for:
# PTP Hardware Clock: 0
# Hardware Transmit Timestamping: yes
# Hardware Receive Timestamping: yes
```

Load the appropriate PHC driver:

```bash
# Check available PTP devices
ls -l /dev/ptp*
# Typical output: /dev/ptp0 -> ptp0

# Verify PHC is working
phc_ctl /dev/ptp0 get
```

## When to Use Each Implementation

**Use linuxptp when:**
- You need the most complete PTPv2 feature set
- Boundary clock or transparent clock functionality is required
- Multiple PTP profiles (802.1AS, Telecom) are needed
- Dedicated PTP deployment without NTP overlap

**Use chrony (PTP) when:**
- You need both NTP and PTP from a single daemon
- Fast clock convergence is important
- You want the simplest configuration model
- Your environment already uses chrony for NTP

**Use NTPsec (PTP) when:**
- Security hardening is a primary concern
- Your organization already standardizes on NTPsec
- You need audit-friendly configuration with familiar NTP syntax
- Buffer overflow protections and privilege separation are required

## Why Self-Host Your PTP Infrastructure?

Running your own PTP infrastructure gives you complete control over time synchronization without depending on external services:

- **Eliminate external dependencies**: Grandmaster clocks can be sourced from local GPS receivers or atomic clocks. No reliance on public NTP pools or commercial time services.
- **Sub-microsecond precision**: PTP hardware timestamping achieves 100-nanosecond accuracy on LAN — impossible with NTP's software timestamping. Critical for financial trading, industrial control, and 5G networks.
- **Compliance and auditability**: Many regulated industries (finance, telecommunications, defense) require documented time synchronization with specific precision levels. Self-hosted PTP provides full audit trails and configuration control.
- **Network isolation**: In air-gapped or classified networks, external time sources may not be available. A local PTP grandmaster with GPS input provides autonomous time synchronization.
- **Cost savings**: Commercial PTP grandmaster appliances cost $5,000-$50,000. A Linux server with a GPS card and linuxptp provides equivalent functionality at a fraction of the cost.

For related time synchronization infrastructure, see our [NTP server comparison](../2026-05-02-chrony-vs-ntpsec-vs-openntpd-self-hosted-ntp-server-guide/) and [NTP monitoring guide](../2026-05-07-self-hosted-ntp-time-sync-monitoring-chronyc-ntpstat-ntpviz-guide/). If you're building a comprehensive time infrastructure, our [NTP server management guide](../2026-05-19-self-hosted-ntp-server-management-chrony-ntpsec-ntpd-guide/) covers ongoing operational best practices.

## FAQ

### What is the difference between NTP and PTP?

NTP (Network Time Protocol) achieves 1-10 ms accuracy using software timestamping at the OS level. PTP (Precision Time Protocol, IEEE 1588) achieves sub-microsecond accuracy using hardware timestamping at the NIC level. NTP is sufficient for general server synchronization. PTP is required when precision below 1 millisecond is needed (financial trading, industrial automation, 5G).

### Do I need special hardware for PTP?

For hardware timestamping (sub-microsecond precision), you need a NIC that supports PTP. Check with `ethtool -T eth0` — look for "Hardware Transmit/Receive Timestamping: yes". Most modern server NICs (Intel X710/X520, Mellanox ConnectX) support this. Software timestamping works on any NIC but achieves only 1-10 microsecond precision.

### Can PTP and NTP run on the same network?

Yes. linuxptp can synchronize the system clock via PTP and then share it with NTP clients using phc2sys + ntpd/chrony. chrony and NTPsec can handle both PTP and NTP simultaneously, using PTP as the primary source and NTP as fallback.

### What is a PTP grandmaster?

The grandmaster clock is the most accurate time source in a PTP domain. It's elected through the Best Master Clock Algorithm (BMCA) based on clock quality, priority settings, and MAC address. In practice, you designate a server with a GPS receiver or atomic clock as the grandmaster by setting `priority1` to a low value (e.g., 128).

### How do I monitor PTP synchronization?

linuxptp provides `pmc` (PTP management client) for monitoring: `pmc -u -b 0 'GET PORT_DATA_SET'`. chrony offers `chronyc sources` and `chronyc tracking`. NTPsec uses `ntpq -p` and `ntpmon`. All show offset, jitter, and synchronization status.

### Is PTP secure?

PTPv2 includes optional authentication using HMAC-MD5 or HMAC-SHA256, but it's rarely deployed. In practice, PTP security relies on network isolation (dedicated VLAN for PTP traffic) and physical security of the grandmaster clock. NTPsec provides stronger security hardening for the NTP/PTP hybrid case.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted PTP Servers: linuxptp vs chrony vs NTPsec for Sub-Microsecond Time Sync",
  "description": "Compare linuxptp, chrony, and NTPsec for self-hosted Precision Time Protocol (PTP) servers achieving sub-microsecond clock synchronization.",
  "datePublished": "2026-05-10",
  "dateModified": "2026-05-10",
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
