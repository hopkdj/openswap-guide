---
title: "Chrony vs NTPsec vs OpenNTPD: Self-Hosted Time Synchronization Guide 2026"
date: 2026-04-16
tags: ["comparison", "guide", "self-hosted", "infrastructure", "ntp"]
draft: false
description: "Complete guide to self-hosted NTP time servers in 2026. Compare chrony, NTPsec, and OpenNTPD for homelab and enterprise time synchronization with Docker configs and setup instructions."
---

Time synchronization is one of those invisible infrastructure pillars that nobody thinks about — until certificates expire early, distributed databases diverge, or backup timestamps go haywire. A reliable Network Time Protocol (NTP) server is essential for everything from TLS certificate validation to log correlation and filesystem consistency.

In this guide, we'll walk through three of the best open source NTP server implementations available in 2026: **chrony**, **NTPsec**, and **OpenNTPD**. You'll learn what each one does, how they compare, and how to deploy your own time server with practical, copy-paste configurations.

## Why Run Your Own NTP Server

Relying exclusively on public NTP pools might work fine for a single laptop, but there are compelling reasons to run your own time synchronization infrastructure:

**Network reliability.** A local NTP server responds in sub-millisecond latency compared to tens or hundreds of milliseconds for public pool servers. When your public internet connection drops, your internal systems keep accurate time.

**Security and trust.** By stratum-0 or stratum-1 sources (GPS, PPS, atomic clocks) locally, you eliminate the risk of malicious NTP responses from compromised upstream servers. This matters enormously for systems that depend on time for authentication, auditing, and encryption.

**Firewall simplicity.** Instead of opening NTP (UDP port 123) outbound for every machine, you open it once for your local NTP server. All internal clients sync against a single, controlled endpoint.

**Scale and bandwidth.** In a homelab with dozens of VMs and containers, or an enterprise with hundreds of servers, broadcasting time locally eliminates redundant external NTP traffic and reduces load on public pool infrastructure.

**Compliance.** Many regulatory frameworks (PCI-DSS, SOX, HIPAA) require documented, auditable time synchronization with known sources. A self-hosted NTP server gives you full control over the synchronization chain.

## Understanding NTP Hierarchy: Stratum Levels

Before comparing implementations, it helps to understand the NTP stratum system:

- **Stratum 0:** The reference clock itself — GPS receivers, atomic clocks, radio time signals.
- **Stratum 1:** Servers directly connected to stratum 0 devices. These are the most accurate publicly accessible time sources.
- **Stratum 2:** Servers that synchronize with stratum 1 servers. This is where most self-hosted NTP servers operate.
- **Stratum 3+:** Servers that sync with stratum 2 (and below). Each additional stratum adds a small amount of accumulated error.

For a homelab or small-to-medium deployment, a stratum 2 server synced to public pool servers is more than sufficient. Stratum accuracy is typically within 1-10 milliseconds — far better than most application-level timeouts.

## Comparing the Three: chrony vs NTPsec vs OpenNTPD

| Feature | chrony | NTPsec | OpenNTPD |
|---------|--------|--------|----------|
| **Primary focus** | Variable network conditions (laptops, VMs) | Security-hardened NTP daemon | Simplicity and ease of use |
| **Configuration complexity** | Moderate | Complex | Minimal |
| **Startup convergence speed** | Very fast (seconds) | Moderate (minutes) | Moderate (minutes) |
| **NTPv4 support** | Yes | Yes | Yes (partial in older versions) |
| **NTPsec security features** | Good | Excellent (crypto, privilege separation) | Basic |
| **SNTP client mode** | Yes | Yes | Yes (default mode) |
| **Hardware clock support** | Yes | Yes | Limited |
| **Leap second handling** | Smooth (slew) | Smooth (slew) | Step |
| **PTP support** | Yes | No | No |
| **IPv6 support** | Yes | Yes | Yes |
| **Container-friendly** | Excellent | Good | Good |
| **Default on** | RHEL/Rocky, Fedora, SUSE | Debian, Ubuntu | OpenBSD, Alpine (historically) |
| **Memory footprint** | ~5-10 MB | ~15-20 MB | ~3-5 MB |
| **Active development** | Very active | Active | Active |
| **Best for** | VMs, laptops, homelabs, dynamic networks | Security-conscious deployments, enterprise | Simple setups, OpenBSD ecosystems |

### When to Choose chrony

chrony is the default NTP implementation on RHEL-based distributions and SUSE, and it's the most versatile of the three. Its standout feature is **rapid convergence**: it can synchronize within seconds of startup, even on systems with intermittent network connectivity or heavily virtualized environments where the hardware clock drifts significantly.

chrony handles VM pauses gracefully — when a virtual machine is suspended and resumed, chrony quickly detects the clock jump and corrects without the wild oscillations that plague older NTP implementations. It also supports **smooth leap second handling** via the `slew` mode, avoiding the one-second clock discontinuity that can cause application errors.

Choose chrony if:
- You run VMs or containers with variable uptime
- Your network connection is intermittent (laptops, edge devices)
- You want the fastest possible convergence after startup
- You need PTP (Precision Time Protocol) alongside NTP

### When to Choose NTPsec

NTPsec is a security-focused fork of the classic ntpd reference implementation. The entire codebase has been audited, modernized, and stripped of legacy features that expanded the attack surface. Key security features include:

- **Privilege separation:** The daemon drops root privileges after binding to port 123.
- **Cryptographic authentication:** NTPsec supports symmetric key and Autokey authentication to prevent spoofed time responses.
- **Reduced code footprint:** The codebase is roughly 40% smaller than the original ntpd, with many legacy features removed.

NTPsec is the choice for environments where time synchronization security is a compliance requirement or where you operate in a potentially adversarial network environment.

Choose NTPsec if:
- You need NTP authentication for compliance
- You operate in a security-sensitive environment
- You want the most battle-tested NTP protocol implementation
- Your organization has a security audit requirement for all network daemons

### When to Choose OpenNTPD

OpenNTPD, developed as part of the OpenBSD project, follows the project's philosophy of secure defaults and minimal configuration. Out of the box, it "just works" — point it at pool servers and it syncs. The configuration syntax is arguably the simplest of all three.

OpenNTPD's main trade-off is that it implements a subset of the NTPv4 specification. It operates primarily in SNTP (Simple NTP) client mode, which is sufficient for most use cases but lacks some of the advanced filtering and algorithmic features of chrony and NTPsec. For a homelab, small office, or OpenBSD-focused infrastructure, this is rarely a limitation.

Choose OpenNTPD if:
- You want zero-fuss configuration
- You run OpenBSD or Alpine Linux
- Your time sync needs are straightforward (no advanced features required)
- You prefer minimal software with small attack surface

## Installation and Configuration

### Installing chrony

**Debian/Ubuntu:**
```bash
sudo apt update
sudo apt install -y chrony
```

**RHEL/Rocky/Fedora:**
```bash
sudo dnf install -y chrony
```

**Alpine Linux:**
```bash
sudo apk add chrony
```

**Basic chrony.conf for a stratum 2 server:**
```
# Upstream NTP sources (use pool.ntp.org or your regional pool)
pool 0.pool.ntp.org iburst maxsources 4
pool 1.pool.ntp.org iburst maxsources 4
pool 2.pool.ntp.org iburst maxsources 4

# Allow local network to query this server
# Replace 192.168.1.0/24 with your subnet
allow 192.168.1.0/24

# Serve time even when not synchronized to upstream (use with caution)
# local stratum 10

# Record the rate at which the system clock gains/loses time
driftfile /var/lib/chrony/drift

# Smooth leap second handling
leapsecmode slew

# Log directory
logdir /var/log/chrony

# Enable command port for chronyc
bindcmdaddress 127.0.0.1
```

**Start and enable the service:**
```bash
sudo systemctl enable --now chronyd
```

**Verify synchronization status:**
```bash
# Check synchronization status
chronyc tracking

# View NTP sources
chronyc sources -v

# View source statistics
chronyc sourcestats -v

# Check if the server is serving clients
chronyc activity
```

### Installing NTPsec

**Debian/Ubuntu:**
```bash
sudo apt update
sudo apt install -y ntpsec
```

**RHEL/Rocky/Fedora:**
```bash
sudo dnf install -y ntpsec
```

**Build from source (latest version):**
```bash
sudo apt install -y build-essential python3-dev libssl-dev \
  libcap-dev libseccomp-dev gpsd libgps-dev
git clone https://gitlab.com/NTPsec/ntpsec.git
cd ntpsec
./waf configure --refclock=all
./waf build
sudo ./waf install
```

**Basic ntp.conf for NTPsec:**
```
# Upstream servers
server 0.pool.ntp.org iburst
server 1.pool.ntp.org iburst
server 2.pool.ntp.org iburst
server 3.pool.ntp.org iburst

# Restrict default: no modifications, no queries
restrict default nomodify nopeer noquery

# Allow localhost full access
restrict 127.0.0.1
restrict ::1

# Allow local network to query
restrict 192.168.1.0 mask 255.255.255.0 nomodify nopeer

# Drift file
driftfile /var/lib/ntpsec/ntp.drift

# Statistics logging
statsdir /var/log/ntpsec/
```

**Start and enable:**
```bash
sudo systemctl enable --now ntpsec
```

**Verify:**
```bash
# Check peers
ntpq -p

# Detailed peer info
ntpq -c sysinfo
ntpq -c clockvar
```

### Installing OpenNTPD

**Debian/Ubuntu:**
```bash
sudo apt update
sudo apt install -y openntpd
```

**Alpine Linux:**
```bash
sudo apk add openntpd
```

**OpenBSD (included by default):**
OpenNTPD ships with every OpenBSD installation. No extra package needed.

**Basic ntpd.conf for OpenNTPD:**
```
# Simplest possible configuration — sync from pool
servers pool.ntp.org

# Listen on all interfaces
listen on *

# Constraint checking via HTTPS (prevents time manipulation)
constraint from "https://time.cloudflare.com"
```

The `constraint` directive is a uniquely OpenNTPD feature: it verifies the system time against an HTTPS server's certificate validity period. Since HTTPS certificate timestamps are signed by CAs, this provides an additional trust anchor that doesn't rely on NTP itself.

**Start and enable:**
```bash
sudo systemctl enable --now openntpd
```

**Verify:**
```bash
# OpenNTPD doesn't have a rich query CLI — check syslog
sudo journalctl -u openntpd --no-pager -n 20

# Or check the time offset directly
ntpd -d -f /etc/openntpd/ntpd.conf  # debug mode
```

## Running NTP Servers in Docker

For homelab deployments, running your NTP server in a container is clean and reproducible. Note that NTP uses UDP port 123, which requires special Docker configuration.

### Docker Compose for chrony

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
      - NTP_SERVERS=0.pool.ntp.org,1.pool.ntp.org,2.pool.ntp.org
      - ALLOWED_NETWORKS=192.168.1.0/24
      - LOG_LEVEL=info
    volumes:
      - chrony-data:/var/lib/chrony
    networks:
      ntp-net:
        ipv4_address: 192.168.200.10

volumes:
  chrony-data:

networks:
  ntp-net:
    driver: bridge
    ipam:
      config:
        - subnet: 192.168.200.0/24
```

### Docker Compose for NTPsec

```yaml
version: "3.8"

services:
  ntpsec:
    image: openlab/ntpsec:latest
    container_name: ntpsec-server
    restart: unless-stopped
    cap_add:
      - SYS_TIME
      - SYS_NICE
    ports:
      - "123:123/udp"
    volumes:
      - ./ntp.conf:/etc/ntpsec/ntp.conf:ro
      - ntpsec-drift:/var/lib/ntpsec
    networks:
      - ntp-net

volumes:
  ntpsec-drift:

networks:
  ntp-net:
    driver: bridge
```

With this `ntp.conf`:
```
server 0.pool.ntp.org iburst
server 1.pool.ntp.org iburst
server 2.pool.ntp.org iburst
restrict default nomodify nopeer noquery
restrict 127.0.0.1
restrict 192.168.0.0 mask 255.255.0.0 nomodify nopeer
driftfile /var/lib/ntpsec/ntp.drift
```

### Docker Compose for OpenNTPD

```yaml
version: "3.8"

services:
  openntpd:
    image: linuxserver/openntpd:latest
    container_name: openntpd-server
    restart: unless-stopped
    cap_add:
      - SYS_TIME
    ports:
      - "123:123/udp"
    volumes:
      - ./ntpd.conf:/config/ntpd.conf:ro
    environment:
      - TZ=UTC
    networks:
      - ntp-net

networks:
  ntp-net:
    driver: bridge
```

With this `ntpd.conf`:
```
servers pool.ntp.org
listen on 0.0.0.0
constraint from "https://time.cloudflare.com"
```

## Configuring Clients to Use Your NTP Server

Once your local NTP server is running, configure your internal machines to sync against it.

### Linux clients (systemd-timesyncd)

Edit `/etc/systemd/timesyncd.conf`:
```ini
[Time]
NTP=192.168.1.10
FallbackNTP=0.pool.ntp.org
```

Then restart:
```bash
sudo systemctl restart systemd-timesyncd
timedatectl timesync-status
```

### Linux clients (chrony as client)

```bash
# Point chrony to your local server
echo "server 192.168.1.10 iburst" | sudo tee /etc/chrony/conf.d/local-ntp.conf
sudo systemctl restart chronyd
chronyc sources -v
```

### macOS

```bash
sudo systemsetup -setnetworktimeserver 192.168.1.10
sudo systemsetup -setusingnetworktime on
sntp -Ss 192.168.1.10  # immediate sync
```

### Windows

Open an elevated PowerShell:
```powershell
w32tm /config /manualpeerlist:"192.168.1.10" /syncfromflags:manual /update
w32tm /resync
w32tm /query /status
```

### Docker containers

If your Docker host runs chrony, containers inherit the correct time automatically. For explicit configuration in Docker Compose:

```yaml
services:
  myapp:
    image: myapp:latest
    environment:
      - TZ=UTC
    # The container inherits host time — no NTP client needed inside
```

## Performance Tuning Tips

### For chrony

Add these directives to `chrony.conf` for better accuracy:

```
# Use hardware clock as fallback
rtcsync
rtcfile /var/lib/chrony/rtc

# Make the step adjustment at boot if offset is large
makestep 1.0 3

# Log tracking data for analysis
log tracking measurements statistics
```

### For NTPsec

```
# Enable kernel PLL for better frequency discipline
disable monitor  # reduces attack surface

# Prefer specific servers
prefer 0.pool.ntp.org
```

### For OpenNTPD

```
# Use specific servers instead of pool for consistency
server ntp1.example.com
server ntp2.example.com

# Multiple constraints for robustness
constraint from "https://time.cloudflare.com"
constraint from "https://apple.com"
```

## Monitoring and Alerting

Set up basic monitoring to catch time drift before it becomes a problem:

```bash
#!/bin/bash
# /usr/local/bin/check-ntp-offset.sh
# Exit 0 if offset < 100ms, exit 1 otherwise

OFFSET=$(chronyc tracking 2>/dev/null | grep "System time" | awk '{printf "%.0f", $4 * 1000}')

if [ -z "$OFFSET" ]; then
    echo "CRITICAL: Cannot reach chrony daemon"
    exit 2
fi

if [ "$OFFSET" -gt 100 ]; then
    echo "WARNING: Time offset is ${OFFSET}ms (threshold: 100ms)"
    exit 1
fi

echo "OK: Time offset is ${OFFSET}ms"
exit 0
```

For Prometheus-based monitoring, chrony exposes metrics via `chronyc tracking`. You can use the `chrony_exporter` to serve them on `/metrics` for scraping:

```yaml
# docker-compose snippet for monitoring
  chrony-exporter:
    image: pharmer/chrony-exporter:latest
    container_name: chrony-exporter
    restart: unless-stopped
    ports:
      - "9123:9123"
    command: ["--chrony.server=127.0.0.1"]
```

## Which Should You Choose?

**For most homelabs and general use:** chrony is the safest recommendation. It converges fast, handles VMs and network interruptions gracefully, and works well as both server and client. The configuration is straightforward, and it's the default on the most widely deployed enterprise Linux distributions.

**For security-focused deployments:** NTPsec brings hardened code, privilege separation, and cryptographic authentication. If your compliance requirements demand authenticated NTP or if you operate in a contested network environment, NTPsec is the right choice.

**For simplicity-first setups:** OpenNTPD's two-line configuration and constraint-based HTTPS verification make it the easiest to deploy and trust. It's perfect for homelabs, OpenBSD shops, or anywhere you want "set and forget" time synchronization.

All three are mature, open source, and actively maintained. You can't make a wrong choice — but matching the tool to your specific operational requirements will save you configuration headaches down the road.
