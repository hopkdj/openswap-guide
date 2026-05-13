---
title: "Self-Hosted NTP Leap Second Handling: chrony vs NTPsec vs OpenNTPD"
date: "2026-05-13"
tags: ["ntp", "time-synchronization", "leap-second", "chrony", "ntpsec", "self-hosted"]
draft: false
---

When the International Earth Rotation and Reference Systems Service (IERS) announces a leap second, every NTP server on the internet must handle it correctly. The choice of NTP daemon determines whether your systems experience time jumps, clock smearing, or complete service disruption. This guide compares how **chrony**, **NTPsec**, and **OpenNTPD** handle leap second events — a critical consideration for financial trading platforms, distributed databases, and any infrastructure where time continuity matters.

## Why Leap Second Handling Matters

Leap seconds are inserted (or theoretically removed) to keep UTC aligned with Earth's irregular rotation. Since 1972, 27 leap seconds have been added. Each one causes problems:

- **Cloudflare outage (2012)**: Linux kernel leap second bug caused recursive scheduler loops, taking down Cloudflare and multiple other services
- **Reddit outage (2012)**: Java application servers crashed when system time repeated a second
- **Australian airline grounding (2017)**: Qantas reservation system failed during a leap second event
- **Google, AWS, Azure smearing**: Major cloud providers smear leap seconds over hours to avoid discontinuity

For self-hosted infrastructure, you need an NTP daemon that either handles the leap second gracefully or implements smearing to eliminate the discontinuity entirely.

## chrony Leap Second Handling

**chrony** (maintained by Miroslav Lichvar) is the default NTP implementation on most modern Linux distributions. It offers the most sophisticated leap second handling of the three daemons.

### Leap Second Insertion Mode

chrony supports multiple leap second handling modes:

```bash
# /etc/chrony/chrony.conf

# Mode 1: Insert leap second (default behavior)
# chrony will step or slew the clock at 23:59:60 UTC

# Mode 2: Smear the leap second over 24 hours
leapsecmode smear

# Mode 3: Ignore the leap second entirely
# leapsecmode ignore

# Configure smearing duration (default 86400 seconds = 24 hours)
# The smear rate is calculated automatically
maxupdatesize 0.1
```

### chrony Smearing Configuration

chrony's smearing is the closest to Google's "leap smear" approach:

```bash
# Full chrony.conf for leap second handling
server time.cloudflare.com iburst
server time.google.com iburst
server time.nist.gov iburst

# Enable leap second smearing
leapsecmode smear

# Set the system clock offset threshold
makestep 1.0 3

# Save drift and RTC data
driftfile /var/lib/chrony/chrony.drift
rtcsync

# Allow smearing to start 12 hours before the leap second
# chrony automatically calculates the smear window
```

When `leapsecmode smear` is set, chrony gradually adjusts the clock rate over 24 hours around the leap second event. Instead of inserting or deleting a second, it makes each second slightly longer or shorter — eliminating the discontinuity that breaks applications.

### Verification

```bash
# Check chrony's leap second status
chronyc tracking

# Expected output shows:
# Leap status     : Normal / Insert second / Delete second
# System time     : 0.000000001 seconds fast of NTP time
# Last offset     : +0.000001234 seconds

# Check if smearing is active
chronyc tracking | grep "Leap status"
```

## NTPsec Leap Second Handling

**NTPsec** is a hardened fork of the classic NTP reference implementation (ntpd). It focuses on security and correctness, with a different philosophy on leap seconds.

### NTPsec's Approach

NTPsec provides explicit control over leap second behavior:

```bash
# /etc/ntpsec/ntp.conf

# Reference servers
server 0.pool.ntp.org iburst
server 1.pool.ntp.org iburst
server 2.pool.ntp.org iburst

# Leap second handling options:

# Option 1: Standard leap second insertion (default)
# NTPsec will announce the leap second and insert it at midnight UTC

# Option 2: Smooth time mode (similar to smearing)
smoothtime 400 0.001 lean

# Option 3: Ignore leap seconds
# leapignore

# Security hardening
disable monitor
restrict default nomodify nopeer noquery notrap
restrict 127.0.0.1
restrict ::1
```

### NTPsec smoothtime

The `smoothtime` directive in NTPsec implements gradual time adjustment:

```bash
# smoothtime <offset> <rate> [lean|slew]
# offset: maximum offset to smooth (seconds)
# rate: maximum rate adjustment (seconds/second)
smoothtime 400 0.001 lean
```

This gradually slews the clock by up to 400 seconds at a rate of 0.001 seconds per second. For a 1-second leap second, this takes approximately 16.7 minutes of adjustment — much faster than chrony's 24-hour smear but still avoiding a step.

### Docker Deployment for NTPsec

```yaml
version: "3.8"
services:
  ntpsec:
    image: ntpsec/ntpsec:latest
    container_name: ntpsec-server
    restart: unless-stopped
    cap_add:
      - SYS_TIME
    volumes:
      - ./ntp.conf:/etc/ntpsec/ntp.conf:ro
      - ntpsec-data:/var/lib/ntpsec
    ports:
      - "123:123/udp"
    network_mode: host
    command: ["-n", "-c", "/etc/ntpsec/ntp.conf"]

volumes:
  ntpsec-data:
```

## OpenNTPD Leap Second Handling

**OpenNTPD** (OpenBSD NTP Daemon) takes the simplest approach: it ignores leap seconds entirely. The portable version runs on Linux and other Unix-like systems.

### OpenNTPD Philosophy

OpenNTPD's design principle is that leap seconds cause more problems than they solve. It simply ignores them:

```bash
# /etc/openntpd/ntpd.conf

# Upstream NTP servers
servers pool.ntp.org

# OpenNTPD automatically ignores leap seconds
# No special configuration needed

# Optional: constrain to specific servers
server time.cloudflare.com
server time.google.com

# Sensor-based time correction (OpenBSD only)
# sensor *
```

### Advantages of Ignoring Leap Seconds

OpenNTPD's approach means:
- **Zero configuration**: No leap second mode to set
- **No smearing calculation**: The daemon doesn't need to know about upcoming leap seconds
- **Consistent time**: Your servers never experience a repeated or skipped second
- **Simplicity**: The smallest codebase of the three daemons (reduced attack surface)

### Docker Deployment for OpenNTPD

```yaml
version: "3.8"
services:
  openntpd:
    image: dockur/chrony:latest  # Alternative: build from openntpd-portable
    container_name: openntpd-server
    restart: unless-stopped
    cap_add:
      - SYS_TIME
    volumes:
      - ./ntpd.conf:/etc/openntpd/ntpd.conf:ro
    network_mode: host
    command: ["-d", "-f", "/etc/openntpd/ntpd.conf"]
```

## Comparison Table

| Feature | chrony | NTPsec | OpenNTPD |
|---------|--------|--------|----------|
| **Leap second insertion** | ✅ Supported | ✅ Supported | ❌ Ignored |
| **Smearing** | ✅ Built-in (24hr) | ✅ smoothtime | ❌ Not needed |
| **Zero configuration** | ❌ Requires `leapsecmode` | ❌ Requires `smoothtime` | ✅ Default behavior |
| **Security focus** | Moderate | High (hardened fork) | High (OpenBSD) |
| **Docker image** | ✅ Official | ✅ Community | ✅ Community |
| **Default on Linux** | ✅ RHEL/Debian/Ubuntu | ❌ Manual install | ❌ Manual install |
| **Code size** | ~50K lines | ~80K lines | ~5K lines |
| **Last update** | Active (mlichvar/chrony) | Active (NTPsec/ntpsec) | Active (openntpd-portable) |
| **Smear window** | 24 hours (configurable) | ~17 minutes | N/A |
| **Kernel PLL support** | ✅ Full | ✅ Full | ⚠️ Limited |

## Choosing the Right NTP Leap Second Strategy

### Use chrony When:
- You need the most sophisticated leap second handling
- Your infrastructure spans multiple time zones and needs consistent smearing
- You want the default NTP daemon with the best out-of-the-box experience
- You need fast convergence after network interruptions

### Use NTPsec When:
- Security hardening is your top priority
- You need fine-grained control over time adjustment rates
- You want to use `smoothtime` for faster-than-24-hour smearing
- Your organization has compliance requirements for auditable timekeeping

### Use OpenNTPD When:
- You want zero-config NTP that "just works"
- Simplicity and minimal attack surface are priorities
- Your applications don't care about the extra second
- You're running OpenBSD (native support) or want OpenBSD-style simplicity on Linux

## Deployment Architecture

For production environments, a common pattern combines multiple approaches:

```
                    ┌─────────────────────────────────────┐
                    │     Stratum 0 (Atomic/GPS Clock)    │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │     Stratum 1 NTP Servers           │
                    │  (chrony with leapsecmode smear)    │
                    └──────────────┬──────────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
     │ Stratum 2   │     │ Stratum 2   │     │ Stratum 2   │
     │ chrony      │     │ NTPsec      │     │ OpenNTPD    │
     │ (smear)     │     │ (smoothtime)│     │ (ignore)    │
     └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
            │                   │                   │
     ┌──────▼──────┐     ┌──────▼──────┐     ┌──────▼──────┐
     │ Trading     │     │ Database    │     │ Web/App     │
     │ Servers     │     │ Clusters    │     │ Servers     │
     └─────────────┘     └─────────────┘     └─────────────┘
```

The IERS announced that leap seconds will be discontinued by 2035, but until then, proper handling remains essential for infrastructure reliability.

## Why Self-Host Your NTP Infrastructure?

Running your own NTP servers with proper leap second handling gives you control over one of the most fundamental infrastructure dependencies. When public NTP pools experience issues during leap second events — as they have multiple times in the past — your internal servers continue operating correctly.

For time-sensitive applications like financial trading, distributed consensus protocols (Raft, Paxos), and database replication, even a single second of clock discontinuity can cause cascading failures. Self-hosting with chrony's smearing or NTPsec's smoothtime eliminates this risk entirely.

For related reading on time synchronization, see our [PTP precision time protocol guide](../2026-05-10-self-hosted-precision-time-protocol-ptp-linuxptp-chrony-ntpsec-guide/) and [NTP time sync monitoring comparison](../2026-05-07-self-hosted-ntp-time-sync-monitoring-chronyc-ntpstat-ntpviz-guide/).

## FAQ

### What is a leap second and why does it matter?
A leap second is a one-second adjustment added to UTC to account for the gradual slowing of Earth's rotation. It matters because many software systems assume every minute has exactly 60 seconds. When a leap second is inserted (at 23:59:60 UTC), applications that aren't prepared can crash, hang, or produce incorrect results.

### Which NTP daemon handles leap seconds best?
chrony is generally considered the best for leap second handling because it supports built-in smearing over 24 hours, eliminating the discontinuity entirely. NTPsec offers `smoothtime` for faster adjustments, while OpenNTPD simply ignores leap seconds — which works fine for most applications.

### What is NTP leap second smearing?
Smearing gradually adjusts the clock rate over a period (typically 24 hours) so that the extra second is distributed across many seconds instead of inserted all at once. Google pioneered this approach, and chrony implements it natively via `leapsecmode smear`.

### Will leap seconds be eliminated?
Yes. In 2022, the International Telecommunication Union (ITU) voted to discontinue leap seconds by 2035. Earth's rotation will be allowed to drift up to one minute from UTC before a larger correction is applied. Until then, proper leap second handling remains necessary.

### Can I use chrony's smearing with public NTP pools?
Yes. Configure `leapsecmode smear` in chrony.conf and point to any NTP server pool. chrony will receive the leap second announcement from upstream servers and smear it locally, regardless of where the time source comes from.

### Does OpenNTPD's "ignore" approach cause problems?
For most applications, no. The one-second difference between OpenNTPD and UTC is negligible for logging, monitoring, and general server operations. However, applications that require strict UTC alignment (like certain financial systems) may need chrony or NTPsec instead.

### How do I test leap second handling before an actual event?
Use `chronyc -a makestep` to manually step the clock, or set `leapsecmode insert` and use the `leap` command in chronyc. For NTPsec, you can simulate with `ntpd -g` and observe the behavior. Always test in a staging environment first.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted NTP Leap Second Handling: chrony vs NTPsec vs OpenNTPD",
  "description": "Compare how chrony, NTPsec, and OpenNTPD handle NTP leap seconds — smearing, smoothtime, and ignoring strategies for self-hosted time infrastructure.",
  "datePublished": "2026-05-13",
  "dateModified": "2026-05-13",
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
