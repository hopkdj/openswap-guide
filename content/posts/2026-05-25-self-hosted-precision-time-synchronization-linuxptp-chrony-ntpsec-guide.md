---
title: "Self-Hosted Precision Time Synchronization: linuxptp vs chrony vs NTPsec (2026)"
date: "2026-05-25"
tags: ["comparison", "guide", "self-hosted", "networking", "time-synchronization", "ptp"]
draft: false
---

Precision time synchronization is critical for distributed systems, financial trading platforms, telecommunications infrastructure, and industrial control systems. While NTP (Network Time Protocol) provides sub-millisecond accuracy for most use cases, PTP (Precision Time Protocol, IEEE 1588) delivers sub-microsecond synchronization — essential for applications where timing directly impacts correctness.

Self-hosting time synchronization infrastructure gives you complete control over clock sources, synchronization hierarchy, and failover behavior. Relying on public NTP pools introduces dependency on external infrastructure, and for organizations running their own Stratum 1 servers (GPS/GPS-disciplined oscillators), the entire time distribution chain should be under local control.

This guide compares three open-source approaches to precision time synchronization: **linuxptp** (the dedicated PTP stack), **chrony** (the modern NTP/PTP hybrid), and **NTPsec** (the security-hardened NTP implementation with PTP support). Each targets different accuracy requirements and deployment scenarios.

## Why Self-Host Time Synchronization?

Time is foundational infrastructure. When your authentication tokens expire unexpectedly, database transactions conflict, or log correlation fails across datacenters, the root cause is often clock drift. Organizations running distributed databases (CockroachDB, TiDB, etcd), financial systems, or compliance-regulated workloads need guaranteed time accuracy that public NTP pools cannot provide.

Self-hosted time servers let you operate Stratum 1 sources (GPS receivers, atomic clocks, or GPS-disciplined oscillators) and distribute time internally with full visibility into offset, jitter, and synchronization state. For compliance frameworks like PCI DSS, SOC 2, and SOX, documented time synchronization with internal servers is a requirement.

For broader time infrastructure, see our [NTP monitoring guide](../2026-05-11-self-hosted-ntp-monitoring-chrony-exporter-ntpsec-monitor-ntpviz-guide/). If you need time-aware alerting, our [alert routing comparison](../2026-05-10-self-hosted-alert-routing-pagerduty-alternatives/) covers notification workflows.

## linuxptp

linuxptp is the reference open-source PTP implementation for Linux. It implements the IEEE 1588 Precision Time Protocol (PTPv2) and works with the Linux kernel's PTP Hardware Clock (PHC) API to achieve sub-microsecond accuracy on PTP-capable network interfaces. It is the standard choice for telecommunications, industrial automation, and financial trading environments.

### Architecture

linuxptp consists of several cooperating daemons: **ptp4l** (the core PTP protocol engine), **phc2sys** (synchronizes the system clock to the PTP hardware clock), **pmc** (PTP management client), and **ts2phc** (timestamp-to-PHC synchronization for non-PTP-aware devices). Together, they form a complete PTP stack that handles master election, clock synchronization, and system clock discipline.

ptp4l communicates directly with the network interface's PTP Hardware Clock via the Linux PHC API, bypassing the kernel networking stack for timestamp precision. This hardware-level integration is what enables sub-microsecond accuracy — impossible with software-only timestamping.

### Key Features

- **Full PTPv2 implementation** — IEEE 1588-2008 compliant
- **Hardware timestamping** — uses NIC PTP Hardware Clock (PHC) for precision
- **Multiple PTP profiles** — Default, Power, Telecom, Enterprise profiles
- **Boundary clock support** — can act as PTP slave on one port and master on another
- **Management interface** — pmc for querying and configuring PTP state
- **Grandmaster clock** — can serve as PTP grandmaster with external reference

### Docker Deployment

```yaml
version: "3.8"
services:
  linuxptp:
    image: ghcr.io/richardcochran/linuxptp:latest
    privileged: true
    network_mode: host
    pid: host
    command: >
      -f /etc/linuxptp/ptp4l.conf
      -i eth0
      -m
    volumes:
      - ./ptp4l.conf:/etc/linuxptp/ptp4l.conf:ro
      - /dev/ptp0:/dev/ptp0
    restart: unless-stopped
```

Example ptp4l.conf:
```ini
[global]
verbose               1
logging_level         6
time_stamping         hardware
network_transport     L2
delay_mechanism       E2E
```

### GitHub Stats

- **Repository:** richardcochran/linuxptp
- **Stars:** 383+
- **Last Updated:** May 2026

## chrony

chrony is a versatile NTP implementation that has evolved to support PTP synchronization alongside traditional NTP. Originally designed as a drop-in replacement for ntpd with better performance on intermittent network connections, chrony now serves as a hybrid time synchronization daemon that can use NTP, PTP, GPS, and other reference clocks simultaneously.

### Architecture

chrony uses a sophisticated clock discipline algorithm that combines measurements from multiple reference sources. It can simultaneously synchronize to NTP servers, PTP grandmasters (via PHC), GPS receivers (via GPSD or serial), and local hardware clocks. The daemon continuously evaluates each source's quality and selects the best available reference.

For PTP integration, chrony reads timestamps from the Linux PHC API (like linuxptp) and uses them as input to its clock filtering algorithm. This approach provides PTP accuracy with NTP's robust source selection and fallback mechanisms.

### Key Features

- **Hybrid synchronization** — NTP + PTP + GPS + local references simultaneously
- **Fast convergence** — achieves accurate time within minutes of startup
- **Intermittent network support** — designed for laptops, VMs, and cloud instances
- **Hardware timestamping** — PHC integration for PTP precision
- **Monitoring tools** — chronyc for real-time time source statistics
- **Leap second handling** — smooth adjustment without clock jumps

### Docker Deployment

```yaml
version: "3.8"
services:
  chrony:
    image: cturra/docker-ntp:latest
    ports:
      - "123:123/udp"
    cap_add:
      - SYS_TIME
    volumes:
      - ./chrony.conf:/etc/chrony/chrony.conf:ro
    restart: unless-stopped
```

Example chrony.conf with PTP support:
```ini
# NTP pool servers (fallback)
pool 0.pool.ntp.org iburst maxsources 4
pool 1.pool.ntp.org iburst maxsources 4

# PTP hardware clock as primary reference
ptp /dev/ptp0 poll 3 trust

# Local clock as last resort
local stratum 10

# Allow NTP clients on internal network
allow 10.0.0.0/8

# Record time tracking
driftfile /var/lib/chrony/drift
logdir /var/log/chrony
```

### GitHub Stats

- **Repository:** mlichvar/chrony (GitLab mirror on GitHub)
- **Stars:** 205+
- **Last Updated:** April 2026
- **Primary home:** gitlab.com/chrony/chrony

## NTPsec

NTPsec is a security-hardened fork of the classic ntpd, focused on reducing attack surface, modernizing the codebase, and eliminating legacy vulnerabilities. While its primary focus is secure NTP, NTPsec also supports PTP through the Linux PHC API, providing an alternative for organizations that prioritize security over feature breadth.

### Architecture

NTPsec maintains the classic NTP daemon architecture but with a significantly reduced code footprint. The project has removed over 300,000 lines of legacy code, eliminated the MODE_AUTOKEY authentication protocol (replaced with NTS — Network Time Security), and implemented continuous fuzzing and static analysis in the development pipeline.

For PTP support, NTPsec reads hardware timestamps from the Linux PHC API and uses them as a reference clock source, similar to chrony's approach. The security-focused design means NTPsec is the preferred choice for compliance environments where the time synchronization stack itself must pass security audits.

### Key Features

- **Security-hardened** — 300K+ lines of legacy code removed
- **Network Time Security (NTS)** — authenticated and encrypted NTP
- **PTP support** — Linux PHC API integration for hardware timestamps
- **Continuous fuzzing** — automated vulnerability discovery
- **Reduced attack surface** — minimal configuration options, secure defaults
- **Drop-in replacement** — compatible with ntpd configuration syntax

### Docker Deployment

```yaml
version: "3.8"
services:
  ntpsec:
    image: ntpsec/ntpsec:latest
    ports:
      - "123:123/udp"
    cap_add:
      - SYS_TIME
    volumes:
      - ./ntp.conf:/etc/ntpsec/ntp.conf:ro
    restart: unless-stopped
```

Example ntp.conf with PTP:
```ini
# PTP hardware clock as reference
server 127.127.22.0 minpoll 3 maxpoll 3 prefer
fudge 127.127.22.0 flag1 1 refid PTP

# NTP fallback servers
pool 0.pool.ntp.org iburst
pool 1.pool.ntp.org iburst

# Local clock fallback
server 127.127.1.0
fudge 127.127.1.0 stratum 15

# Access control
restrict default nomodify nopeer noquery
restrict 127.0.0.1
restrict 10.0.0.0 mask 255.0.0.0 nomodify
```

### GitHub Stats

- **Repository:** NTPsec/ntpsec
- **Stars:** Community-maintained (primary distribution via package repos)
- **Last Updated:** Active development

## Feature Comparison

| Feature | linuxptp | chrony | NTPsec |
|---------|----------|--------|--------|
| **Primary Protocol** | PTPv2 (IEEE 1588) | NTP + PTP hybrid | NTP (NTS) + PTP |
| **Max Accuracy** | Sub-microsecond | Sub-microsecond (PTP mode) | Millisecond (NTP) |
| **Hardware Timestamp** | Yes (native) | Yes (PHC API) | Yes (PHC API) |
| **PTP Profiles** | Default, Power, Telecom | Basic PTP support | Basic PTP support |
| **NTP Support** | No (PTP only) | Full NTP client/server | Full NTP client/server |
| **Security Features** | Basic | Basic | NTS encryption, fuzzing |
| **GPS Integration** | Via ts2phc | Via GPSD/serial | Via serial NMEA |
| **Boundary Clock** | Yes | No | No |
| **Grandmaster** | Yes | No | No |
| **Cloud/VM Friendly** | No (needs HW NIC) | Yes (intermittent mode) | Yes |
| **Best For** | Telecom, trading, industrial | General-purpose hybrid | Security-critical NTP |
| **License** | GPLv2 | GPLv2 | BSD-like |

## Choosing the Right Time Synchronization Tool

**Use linuxptp when** you need true IEEE 1588 PTP compliance with sub-microsecond accuracy. This is mandatory for telecommunications (5G synchronization), industrial automation (PROFINET IRT), and financial trading (MiFID II timestamping). linuxptp is the only option if you need boundary clock or grandmaster functionality.

**Use chrony when** you want the flexibility to combine NTP and PTP sources with automatic failover. chrony excels in mixed environments where some servers have PTP-capable NICs and others rely on NTP. Its fast convergence and intermittent network support make it ideal for cloud deployments, virtualized environments, and mobile infrastructure.

**Use NTPsec when** security compliance is your primary concern. If your organization requires authenticated and encrypted time synchronization (NTS), has passed through security audits that flagged ntpd's legacy code, or operates in a regulated environment where the time infrastructure itself must be security-certified, NTPsec is the right choice.

## Deployment Best Practices

### Hardware Requirements for PTP

PTP accuracy depends on hardware support. Both the network interface card (NIC) and switch infrastructure must support PTP:

```bash
# Check if your NIC supports hardware timestamping
ethtool -T eth0

# Look for:
# time-stamping: hardware
# PTP Hardware Clock (PHC) device: /dev/ptp0
```

NICs with Intel 82580, I210, I350, and X710 chipsets support hardware PTP. Switches must support PTP transparent or boundary clock mode for end-to-end accuracy.

### Time Hierarchy Design

```
Stratum 0: GPS Receiver / Atomic Clock
    |
Stratum 1: linuxptp (Grandmaster) or chrony (with GPS)
    |
Stratum 2: chrony/NTPsec (internal NTP servers)
    |
Stratum 3: Application servers (NTP clients)
```

For PTP-only environments, replace the NTP hierarchy with PTP domains:
- Grandmaster clock (linuxptp with GPS reference)
- Boundary clocks (linuxptp at network boundaries)
- Ordinary clocks (end servers with PTP-capable NICs)

### Monitoring Time Accuracy

```bash
# chrony: check time source quality
chronyc sources -v
chronyc tracking

# linuxptp: check PTP synchronization
pmc -u -b 0 "GET CURRENT_DATA_SET"
pmc -u -b 0 "GET PORT_DATA_SET"

# NTPsec: check synchronization
ntpq -p
ntpmon
```

### Handling Leap Seconds

All three tools handle leap seconds differently:
- **chrony** — smooth adjustment (slew) by default, no clock jump
- **linuxptp** — follows leap second indication from grandmaster
- **NTPsec** — configurable: smear, step, or hold

For production systems, prefer smear or slew to avoid application-level issues with clock jumps.

## Security Considerations

Time synchronization is a critical infrastructure component — an attacker who controls your time source can invalidate certificates, disrupt authentication, and corrupt distributed consensus.

- **Authenticate time sources** — use NTS (NTPsec) or PTP security extensions
- **Multiple reference sources** — never rely on a single NTP server or PTP grandmaster
- **Monitor for anomalies** — alert on sudden clock offsets exceeding thresholds
- **Isolate time infrastructure** — run time servers on dedicated, hardened hosts
- **PTP security** — IEEE 1588-2019 adds authentication; verify switch support
- **GPS spoofing protection** — if using GPS as Stratum 1 source, consider anti-spoofing measures

## FAQ

### Can chrony replace both ntpd and linuxptp?

For most environments, yes. chrony can synchronize to NTP servers for millisecond accuracy or to PTP hardware clocks for sub-microsecond precision. However, chrony does not implement the full PTP protocol — it cannot act as a PTP grandmaster, boundary clock, or participate in PTP master clock election. If you need full PTP infrastructure, linuxptp is still required for the grandmaster and boundary clock roles.

### Do I need PTP or is NTP sufficient?

For most applications, NTP with chrony provides more than adequate accuracy (1-10 milliseconds on LAN, 10-100 milliseconds over WAN). PTP is only needed when your application requires sub-millisecond synchronization: financial trading (timestamping orders), telecommunications (5G fronthaul), industrial automation (motion control), or scientific experiments (particle detectors, radio telescopes).

### Can I run PTP over WiFi?

No. PTP requires deterministic, low-jitter network paths with hardware timestamping support. WiFi introduces variable latency that defeats PTP's precision guarantees. Use wired Ethernet with PTP-capable switches for production PTP deployments.

### How do I verify my time server is actually synchronized?

Use the monitoring tools for each daemon. For chrony: `chronyc tracking` should show "Leap status: Normal" and "System time: 0.000000xxx seconds". For linuxptp: `pmc GET CURRENT_DATA_SET` should show `offsetFromMaster` in nanoseconds. For NTPsec: `ntpq -p` should show a `*` next to the selected peer with low offset values.

### Is NTPsec compatible with existing ntpd configurations?

NTPsec uses the same configuration file syntax as classic ntpd (`ntp.conf`), so most configurations work without modification. The main differences are: NTPsec does not support the deprecated MODE_AUTOKEY protocol (use NTS instead), and some obscure monitoring commands have been replaced with the `ntpmon` tool.

### Can I mix PTP and NTP servers in the same infrastructure?

Yes. chrony natively supports both simultaneously. You can have linuxptp providing PTP synchronization on servers with PTP-capable NICs, while other servers use NTP from chrony or NTPsec instances. The key is to ensure all time sources ultimately trace back to the same Stratum 0 reference (GPS or atomic clock).

## Why Self-Host Your Time Infrastructure?

Time synchronization is too critical to outsource entirely. While public NTP pools are reliable for basic clock accuracy, organizations running distributed databases, financial systems, or compliance-regulated workloads need guaranteed time accuracy with full auditability.

Self-hosted time servers let you operate your own Stratum 1 sources, define internal time distribution hierarchies, and maintain complete logs of synchronization state for compliance auditing. Combined with [NTP monitoring tools](../2026-05-11-self-hosted-ntp-monitoring-chrony-exporter-ntpsec-monitor-ntpviz-guide/) for dashboards and alerting, you get end-to-end visibility into your time infrastructure health.

For comprehensive infrastructure monitoring that includes time drift detection, pair your time servers with [performance profiling tools](../2026-05-22-self-hosted-linux-performance-profiling-perf-bcc-tools-sysstat-guide/) to correlate timing anomalies with system performance issues.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Precision Time Synchronization: linuxptp vs chrony vs NTPsec (2026)",
  "description": "Compare three open-source time synchronization solutions: linuxptp, chrony, and NTPsec. Learn PTP and NTP deployment, Docker configs, and accuracy trade-offs.",
  "datePublished": "2026-05-25",
  "dateModified": "2026-05-25",
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
