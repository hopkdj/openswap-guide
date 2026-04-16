---
title: "Complete Guide to Self-Hosted NTP Servers: Chrony, NTPsec & OpenNTPD 2026"
date: 2026-04-16
tags: ["comparison", "guide", "self-hosted", "privacy", "infrastructure"]
draft: false
description: "Build a reliable, private time synchronization infrastructure with open-source NTP servers. Compare Chrony, NTPsec, and OpenNTPD with Docker configs, hardening tips, and deployment guides."
---

Every server, container, and network device depends on accurate time. Authentication tokens expire, distributed databases drift, log correlation breaks, and TLS handshakes fail when clocks disagree by even a few seconds. Yet most infrastructure teams blindly rely on public NTP pools — sending every time query to servers they don't control, over unencrypted UDP, from IPs that reveal their network topology.

Running your own NTP server stack gives you full control over time synchronization, eliminates an external dependency, and keeps your internal clock queries off the public internet. This guide covers three mature open-source NTP implementations, how to deploy them with Docker, and how to build a resilient, private time infrastructure for your entire network.

## Why Self-Host Your NTP Infrastructure

Public NTP pools are convenient, but they come with real trade-offs:

- **Privacy**: Every NTP request exposes your server's IP address to external operators. For organizations handling sensitive workloads, this creates an unnecessary data leak.
- **Reliability**: Public pools can experience outages, rate-limiting, or deliberate attacks. When your authentication infrastructure depends on external time servers, you inherit their availability risk.
- **Accuracy control**: Running local stratum-1 or stratum-2 servers lets you tune polling intervals, select upstream sources, and monitor synchronization quality with full visibility.
- **Network segmentation**: Air-gapped or heavily firewalled environments often cannot reach public NTP pools. A local NTP server provides time for isolated segments without opening outbound UDP 123.
- **Regulatory compliance**: Financial, healthcare, and government systems often require documented time synchronization with auditable internal infrastructure — something public pools cannot provide.
- **Cost at scale**: Large deployments making thousands of NTP queries per minute can trigger rate limits or abuse flags on public pools. Self-hosting eliminates this entirely.

The typical architecture is simple: one or two servers sync to trusted upstream sources (GPS receivers, atomic clock feeds, or select public stratum-1 servers), and all internal machines query your local NTP servers instead of going to the internet.

## NTP Protocol Basics

Before diving into implementations, here's what matters about the NTP protocol itself:

**Stratum hierarchy**: NTP uses a tiered accuracy model. Stratum-0 devices are atomic clocks or GPS receivers. Stratum-1 servers connect directly to stratum-0. Stratum-2 servers sync to stratum-1, and so on. Each hop adds a small amount of drift.

**Authentication**: NTP supports symmetric key authentication (Autokey was deprecated due to security concerns). Modern implementations recommend NTS (Network Time Security) — a TLS-based authentication extension standardized in RFC 8915 — though adoption is still growing.

**UDP port 123**: Traditional NTP runs over UDP port 123. This is important for firewall rules. NTP over TLS (NTS) uses TCP port 4460.

**Clock discipline**: NTP doesn't just set the time — it continuously disciplines the system clock, adjusting the clock frequency to minimize long-term drift. This is why `ntpd` and `chronyd` run as daemons rather than one-shot commands.

Now let's look at the three leading open-source implementations.

## Chrony: The Modern Default

[Chrony](https://chrony-project.org/) has become the default NTP implementation on most modern Linux distributions, replacing the legacy `ntpd`. It was designed from the ground up to handle intermittent network connections, virtual machine clock instability, and rapid convergence — making it the best choice for most self-hosted deployments.

### Key Advantages

- **Fast convergence**: Chrony can synchronize to an upstream source in minutes rather than hours, significantly faster than traditional NTP implementations.
- **VM-friendly**: Handles virtual machine clock jumps and pauses gracefully — critical for cloud and container deployments where the underlying hypervisor can disrupt system clocks.
- **Intermittent connectivity**: Works well on systems that don't have continuous network access. It can store timing data and compensate when the network returns.
- **Hardware timestamping**: Supports PTP (Precision Time Protocol) hardware timestamping for sub-microsecond accuracy on supported network cards.
- **Active development**: Regular releases, modern codebase, responsive maintainers.

### Docker Deployment

Here's a production-ready Docker Compose configuration for a Chrony NTP server:

```yaml
# docker-compose.yml
version: "3.9"

services:
  chrony:
    image: cturra/ntp:latest
    container_name: chrony-ntp
    restart: unless-stopped
    network_mode: host
    cap_add:
      - SYS_TIME
    environment:
      - NTP_SERVERS=0.pool.ntp.org,1.pool.ntp.org,2.pool.ntp.org
      - LOG_LEVEL=info
    volumes:
      - chrony-data:/var/lib/chrony
      - ./chrony.conf:/etc/chrony/chrony.conf.d/custom.conf:ro

volumes:
  chrony-data:
```

For a fully custom setup without the pre-built image:

```dockerfile
# Dockerfile
FROM alpine:3.19
RUN apk add --no-cache chrony tzdata
COPY chrony.conf /etc/chrony/chrony.conf
RUN mkdir -p /var/lib/chrony
EXPOSE 123/udp
CMD ["chronyd", "-f", "/etc/chrony/chrony.conf", "-d"]
```

```conf
# chrony.conf — production configuration
# Upstream NTP sources
server 0.pool.ntp.org iburst
server 1.pool.ntp.org iburst
server 2.pool.ntp.org iburst
server 3.pool.ntp.org iburst

# Record the rate at which the system clock gains/loses time
driftfile /var/lib/chrony/chrony.drift

# Allow the system clock to be stepped in the first three updates
# if its offset is larger than 1 second
makestep 1.0 3

# Enable kernel synchronization of the real-time clock (RTC)
rtcsync

# Serve time to the local network
allow 192.168.0.0/16
allow 10.0.0.0/8

# Specify the NTP port
port 123

# Log directory
logdir /var/log/chrony
log measurements statistics tracking

# Security: restrict access
deny all
allow 192.168.1.0/24
allow 10.0.0.0/8
```

### Monitoring and Diagnostics

```bash
# Check synchronization status
chronyc tracking

# View time sources and their quality
chronyc sources -v

# Detailed source statistics
chronyc sourcestats -v

# Check if chrony is serving clients
chronyc activity

# Manual time correction
chronyc makestep
```

Sample output from `chronyc sources -v`:

```
  .-- Source mode  '^' = server, '=' = peer, '#' = local clock.
 / .- Source state '*' = current best, '+' = combined, '-' = not combined,
| /             'x' = may be in error, '~' = too variable, '?' = unusable.
||         .- xxxx [ yyyy ] +/- zzzz
||      /   xxxx = adjusted offset,
||     |    yyyy = measured offset,
||     |    zzzz = estimated error.
||     |     |
MS Name/IP address         Stratum Poll Reach LastRx Last sample
===============================================================================
^* ntp1.example.com              1   6   377    12  +15us[  +18us] +/-  8ms
^+ ntp2.example.com              1   6   377    15  -21us[  -18us] +/-  12ms
^+ ntp3.example.com              2   6   377    14  +42us[  +45us] +/-  15ms
```

## NTPsec: The Security-Hardened Option

[NTPsec](https://www.ntpsec.org/) is a security-focused fork of the classic reference NTP implementation. It was created in response to a series of critical vulnerabilities discovered in the traditional `ntpd` codebase. NTPsec strips out legacy code, enforces strict privilege separation, and implements modern security practices throughout.

### Key Advantages

- **Privilege separation**: Drops root privileges after binding to port 123, limiting the blast radius of any potential exploit.
- **Reduced attack surface**: Removed ~30,000 lines of legacy code from the original NTP distribution, including unused protocols and deprecated features.
- **NTS support**: First-class support for Network Time Security (RFC 8915), providing authenticated and encrypted NTP communication.
- **Formal verification**: The codebase has undergone formal analysis and security auditing, making it the preferred choice for security-conscious deployments.
- **Drop-in compatibility**: Uses the same configuration syntax as traditional `ntpd`, making migration straightforward.

### Docker Deployment

```yaml
# docker-compose.yml for NTPsec
version: "3.9"

services:
  ntpsec:
    build:
      context: ./ntpsec
      dockerfile: Dockerfile
    container_name: ntpsec-server
    restart: unless-stopped
    network_mode: host
    cap_add:
      - SYS_TIME
      - SYS_NICE
    security_opt:
      - no-new-privileges:true
    volumes:
      - ./ntp.conf:/etc/ntpsec/ntp.conf:ro
      - ntpsec-var:/var/lib/ntpsec
```

```dockerfile
# ntpsec/Dockerfile
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    ntpsec \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /var/lib/ntpsec /var/log/ntpsec \
    && chown ntp:ntp /var/lib/ntpsec /var/log/ntpsec
EXPOSE 123/udp
USER ntp
CMD ["ntpsec", "-n", "-g", "-f", "/etc/ntpsec/ntp.conf"]
```

```conf
# ntp.conf — NTPsec production configuration
# Upstream sources with NTS authentication
server time.cloudflare.com nts prefer
server time.google.com nts
server ntp1.example.com nts

# Use local clock as fallback (stratum 10 to avoid being preferred)
server 127.127.1.0
fudge 127.127.1.0 stratum 10

# Restrict access — default deny
restrict default limited kod nomodify notrap nopeer noquery
restrict -6 default limited kod nomodify notrap nopeer noquery

# Allow local network queries and synchronization
restrict 192.168.1.0 mask 255.255.255.0 nomodify notrap
restrict 10.0.0.0 mask 255.0.0.0 nomodify notrap

# Allow localhost full access
restrict 127.0.0.1
restrict ::1

# Drift file
driftfile /var/lib/ntpsec/ntp.drift

# Statistics logging
statsdir /var/log/ntpsec/
statistics loopstats peerstats clockstats
filegen loopstats file loopstats type day enable
filegen peerstats file peerstats type day enable
filegen clockstats file clockstats type day enable

# NTS server keys directory
ntsd /var/lib/ntpsec/nts_keys
```

### Enabling NTS (Network Time Security)

NTPsec supports running as an NTS server, which encrypts and authenticates NTP traffic:

```bash
# Generate NTS key files
nts-keygen -o /var/lib/ntpsec/nts_keys

# The NTS server listens on TCP 4460 by default
# Clients configure with:
#   server your-ntp-server.example.com nts
```

### Monitoring

```bash
# Check synchronization status
ntpq -p

# Detailed peer information
ntpq -c as
ntpq -c rv

# Check NTS status (if enabled)
ntpq -c "mrulist"
```

## OpenNTPD: The Minimalist Choice

[OpenNTPD](https://www.openntpd.org/) is part of the OpenBSD project and follows the OpenBSD philosophy of doing one thing well, with minimal configuration and a strong security posture. It's significantly simpler than Chrony or NTPsec — which is both its greatest strength and its limitation.

### Key Advantages

- **Simplicity**: A working configuration can be a single line. No complex tuning required.
- **Security-first design**: Inherits OpenBSD's security practices — pledge/unveil system calls, privilege separation, and a minimal codebase.
- **Automatic upstream selection**: Automatically discovers and selects the best NTP pool servers without manual configuration.
- **Low resource usage**: Extremely lightweight — ideal for routers, embedded systems, and resource-constrained environments.
- **DNS-based pool support**: Native integration with DNS-based pool selection, so you get automatic load balancing and failover.

### Limitations

- **Fewer features**: No stratum-1 support, limited hardware clock integration, no NTS support yet.
- **Less granular control**: Fewer tuning options for advanced use cases.
- **Linux compatibility**: Originally designed for OpenBSD; the portable version works on Linux but may lag behind OpenBSD releases.

### Docker Deployment

```yaml
# docker-compose.yml for OpenNTPD
version: "3.9"

services:
  openntpd:
    build:
      context: ./openntpd
      dockerfile: Dockerfile
    container_name: openntpd
    restart: unless-stopped
    network_mode: host
    cap_add:
      - SYS_TIME
    security_opt:
      - no-new-privileges:true
    volumes:
      - ./ntpd.conf:/etc/openntpd/ntpd.conf:ro
```

```dockerfile
# openntpd/Dockerfile
FROM alpine:3.19
RUN apk add --no-cache openntpd
EXPOSE 123/udp
CMD ["ntpd", "-d", "-s", "-f", "/etc/openntpd/ntpd.conf"]
```

```conf
# ntpd.conf — OpenNTPD production configuration

# Use DNS-based pool — automatically selects best servers
servers pool.ntp.org

# Listen on all interfaces
listen on *

# Listen on specific interface
# listen on 192.168.1.10

# Optional: constrain time sources using DNSSEC
# servers pool.ntp.org constrain from dns

# Sensor for hardware clock (Linux-specific)
# sensor *
```

### Monitoring

```bash
# Check synchronization status (OpenBSD)
ntpdctl show servers

# On Linux (portable version), use:
ntpd -d  # Run in debug mode to see sync status in logs

# Verify with standard ntpq
ntpq -p localhost
```

## Comparison Table

| Feature | Chrony | NTPsec | OpenNTPD |
|---------|--------|--------|----------|
| **Default on** | RHEL, Fedora, Ubuntu, Debian | Hardened Linux distros | OpenBSD |
| **Convergence speed** | Fast (minutes) | Moderate (hours) | Moderate |
| **VM clock handling** | Excellent | Good | Basic |
| **Intermittent network** | Excellent | Poor | Fair |
| **Privilege separation** | Yes (cap_drop) | Yes (strong) | Yes (pledge/unveil) |
| **NTS server support** | Partial | Full | No |
| **Hardware clock (PTP)** | Yes | Limited | No |
| **Configuration complexity** | Moderate | High | Minimal |
| **Stratum-1 support** | Yes | Yes | No |
| **Codebase size** | ~60K LOC | ~100K LOC | ~25K LOC |
| **Active development** | Very active | Active | Moderate |
| **Best for** | General purpose, cloud, VMs | Security-critical systems | OpenBSD, minimal setups |

## Building a Resilient Self-Hosted NTP Stack

For production environments, don't run just one NTP server. Here's a recommended architecture:

### Two-Server Redundant Design

```
                    ┌──────────────────┐
                    │  GPS Receiver    │
                    │  (Stratum-0)     │
                    └────────┬─────────┘
                             │ serial/USB
              ┌──────────────┴──────────────┐
              │                             │
     ┌────────▼────────┐          ┌────────▼────────┐
     │  NTP Server A   │◄────────►│  NTP Server B   │
     │  (Chrony)       │  peer    │  (Chrony)       │
     │  Stratum-1      │          │  Stratum-1      │
     └────────┬────────┘          └────────┬────────┘
              │                            │
              └────────────┬───────────────┘
                           │
              ┌────────────▼───────────────┐
              │    Internal Network        │
              │  192.168.1.0/24 clients    │
              │  query both servers        │
              └────────────────────────────┘
```

```yaml
# docker-compose.yml — Server A (primary)
version: "3.9"
services:
  chrony:
    image: cturra/ntp:latest
    container_name: chrony-primary
    restart: unless-stopped
    network_mode: host
    cap_add:
      - SYS_TIME
    environment:
      - NTP_SERVERS=0.pool.ntp.org,1.pool.ntp.org
    volumes:
      - chrony-data:/var/lib/chrony
      - ./chrony-primary.conf:/etc/chrony/chrony.conf.d/custom.conf:ro

volumes:
  chrony-data:
```

```conf
# chrony-primary.conf
server 0.pool.ntp.org iburst prefer
server 1.pool.ntp.org iburst
server 2.pool.ntp.org iburst

# Peer relationship with Server B
peer 192.168.1.11 iburst

# Serve time to local network
allow 192.168.1.0/24

driftfile /var/lib/chrony/chrony.drift
makestep 1.0 3
rtcsync
logdir /var/log/chrony
log measurements statistics tracking
```

Server B gets the same configuration with `peer 192.168.1.10` (pointing to Server A).

### Client Configuration

All internal machines should be configured to query both NTP servers:

```bash
# Linux clients with chrony (/etc/chrony/chrony.conf)
server 192.168.1.10 iburst prefer
server 192.168.1.11 iburst

# Or with ntpsec (/etc/ntpsec/ntp.conf)
server 192.168.1.10 prefer
server 192.168.1.11

# Docker containers can inherit host time, or:
# docker run -e NTP_SERVERS=192.168.1.10,192.168.1.11 ...
```

```yaml
# Docker Compose — client container using local NTP
version: "3.9"
services:
  app:
    image: myapp:latest
    environment:
      - TZ=UTC
    # The host's chrony keeps system time accurate
    # Containers inherit accurate time from the host
    # For explicit NTP in containers:
    cap_add:
      - SYS_TIME
```

## Security Hardening

Regardless of which NTP implementation you choose, follow these security practices:

### Firewall Rules

```bash
# Allow NTP from trusted sources only
iptables -A INPUT -p udp --dport 123 -s 192.168.1.0/24 -j ACCEPT
iptables -A INPUT -p udp --dport 123 -s 10.0.0.0/8 -j ACCEPT
iptables -A INPUT -p udp --dport 123 -j DROP

# Rate limit NTP to prevent amplification attacks
iptables -A INPUT -p udp --dport 123 -m limit --limit 4/sec --limit-burst 8 -j ACCEPT
```

### Container Security

```yaml
# Key security settings for Docker deployment
services:
  ntp-server:
    # Drop unnecessary capabilities
    cap_drop:
      - ALL
    # Only add what's needed
    cap_add:
      - SYS_TIME
    # Prevent privilege escalation
    security_opt:
      - no-new-privileges:true
    # Read-only root filesystem
    read_only: true
    # Mount only what's needed
    tmpfs:
      - /tmp
      - /var/run
    # Resource limits
    deploy:
      resources:
        limits:
          memory: 64M
          cpus: "0.25"
```

### Disable Monlist

The `monlist` command is a well-known NTP amplification attack vector. Ensure it's disabled:

```conf
# In chrony.conf — monlist is disabled by default
# but explicitly restrict:
cmdport 0

# In ntp.conf:
restrict default limited kod nomodify notrap nopeer noquery
```

### Monitoring with Prometheus

Export NTP metrics for monitoring with the `chrony_exporter` or `ntp_exporter`:

```yaml
# docker-compose.yml — add monitoring
services:
  chrony-exporter:
    image: superq/chrony_exporter
    container_name: chrony-exporter
    restart: unless-stopped
    ports:
      - "9123:9123"
    network_mode: host
    command:
      - "--chrony.source=192.168.1.10"
```

## When to Use GPS Receivers

For organizations requiring the highest accuracy and independence from external network time sources, GPS receivers provide stratum-0 time directly:

```conf
# chrony.conf with GPS PPS (Pulse Per Second)
refclock PPS /dev/pps0 lock NMEA refid GPS
refclock SHM 0 offset 0.0 delay 0.2 refid NMEA

# NMEA from GPS serial device
server 127.127.20.0 mode 17 minpoll 3 prefer
fudge 127.127.20.0 flag1 1 flag2 0 flag3 0 flag4 0 time2 0.0
```

Common GPS USB receivers include the VK-172, GlobalSat BU-353, and u-blox modules. Combined with a PPS signal on a GPIO pin or serial port, these can achieve sub-microsecond accuracy.

## Summary: Which Should You Choose?

| Scenario | Recommendation |
|----------|---------------|
| **General Linux servers, cloud, VMs** | Chrony — fast convergence, excellent VM handling |
| **Security-critical, compliance-driven** | NTPsec — hardened, NTS support, audited code |
| **OpenBSD, embedded, minimal setups** | OpenNTPD — simple, secure by default, lightweight |
| **Stratum-1 with GPS** | Chrony or NTPsec — both support hardware refclocks |
| **Container environments** | Chrony via Docker — purpose-built container images available |
| **NTS encryption required** | NTPsec — most complete NTS implementation |

For most self-hosted deployments, **Chrony** is the best starting point. It converges quickly, handles virtual environments gracefully, and has excellent container support. Security-sensitive organizations should consider **NTPsec** with NTS enabled for encrypted time synchronization. And if you're running OpenBSD or need the simplest possible setup, **OpenNTPD** works beautifully with almost zero configuration.

Whichever you choose, running your own NTP infrastructure is one of those foundational improvements that makes everything else in your stack more reliable — authentication works correctly, logs stay correlated, distributed systems agree on order, and you stop depending on external services for something as basic as telling time.
