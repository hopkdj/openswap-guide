---
title: "Self-Hosted Port Scan Detection: portsentry vs psad vs scanlogd"
date: "2026-05-24"
tags: ["port-scan-detection", "intrusion-prevention", "network-security", "portsentry", "psad", "scanlogd", "firewall", "self-hosted"]
draft: false
---

Port scanning is often the first step in a network attack. Before an attacker attempts to exploit a service, they probe your server to discover open ports, running services, and potential vulnerabilities. Self-hosted port scan detection tools monitor your network interfaces for scanning activity and can automatically block offending IP addresses before exploitation attempts begin.

In this guide, we compare three open-source port scan detection tools for Linux: **portsentry**, **psad**, and **scanlogd**. Each uses a different detection approach -- from active port monitoring to iptables log analysis -- and choosing the right one depends on your network topology, detection requirements, and blocking strategy.

## How Port Scan Detection Works

Port scans come in several varieties: TCP SYN scans (half-open, stealthy), TCP connect scans (full connection), UDP scans (service discovery), and FIN/XMAS/NULL scans (stealth evasion). Detection tools monitor for patterns that distinguish scanning behavior from legitimate traffic -- rapid connection attempts to multiple ports, unusual flag combinations, or sequential port probing.

When a scan is detected, the tool can log the event, send alerts, and automatically block the source IP through iptables/nftables rules, TCP wrappers, or route nullification. This proactive blocking adds a critical layer of defense before application-level security controls engage.

## portsentry: Active Port Monitoring and Response

**portsentry** is one of the oldest and most straightforward port scan detection tools. It works by binding to unused ports (stealth mode) or monitoring kernel-level port connections (TCP/UDP mode). When an incoming connection attempt is detected on a monitored port, portsentry immediately logs the event and can execute configurable response actions.

**GitHub:** [portsentry/portsentry](https://github.com/portsentry/portsentry) -- active development

### How portsentry Works

portsentry operates in three modes:

1. **Stealth Mode** (`-st`/`-su`): Binds to all unused TCP/UDP ports. Any connection attempt triggers detection because legitimate traffic would never target these ports.
2. **TCP Wrapper Mode** (`-at`/`-au`): Monitors connections through the TCP wrapper library without binding to ports.
3. **Advanced Stealth Mode** (`-st` with raw sockets): Uses raw sockets to detect SYN scans without binding to any ports.

When a scan is detected, portsentry can:
- Log the event with timestamp and source IP
- Add a deny rule to `/etc/hosts.deny` (TCP wrappers)
- Execute a custom command (e.g., iptables DROP rule)
- Send a syslog notification

### Installation

```bash
# Debian/Ubuntu
sudo apt install portsentry

# RHEL/CentOS/Fedora
sudo dnf install portsentry
```

### Docker Deployment

```yaml
version: "3.8"
services:
  portsentry:
    image: alpine:latest
    container_name: portsentry-monitor
    restart: unless-stopped
    network_mode: "host"
    privileged: true
    volumes:
      - /etc/portsentry:/etc/portsentry
      - /var/lib/portsentry:/var/lib/portsentry
      - /etc/hosts.deny:/etc/hosts.deny
    entrypoint: ["/bin/sh", "-c"]
    command: |
      apk add --no-cache portsentry iptables
      portsentry -tcp
      portsentry -udp
```

### Configuration

```ini
# /etc/portsentry/portsentry.conf
TCP_PORTS="1,7,9,11,15,70,79,80,109,110,111,119,138,139,143,512,513,514,515,540,548,635,1080,1524,2000,4000,6667,8080,12345,31337"
UDP_PORTS="1,7,9,66,67,68,69,111,137,138,161,162,474,513,517,518,520,635,640,641,666,700,1718,1900,2049"

BLOCK_UDP="1"
BLOCK_TCP="1"

# Block command using iptables
KILL_ROUTE="/sbin/iptables -I INPUT -s $TARGET$ -j DROP"

# Syslog alert
KILL_RUN_CMD="/usr/bin/logger 'PortSentry: Scan detected from $TARGET$ on port $PORT$'"

# Whitelist trusted IPs
IGNORE_FILE="/etc/portsentry/portsentry.ignore"
```

### Key Features

- Active port monitoring with immediate detection
- Multiple operation modes (stealth, TCP wrapper, advanced)
- Configurable response actions (block, log, alert)
- TCP wrapper integration (`/etc/hosts.deny`)
- IP whitelist for trusted networks
- Low resource usage -- lightweight daemon

### Limitations

- Stealth mode binds to ports -- conflicts with services
- Cannot detect sophisticated scans (OS fingerprinting, slow scans)
- Limited to port-level detection -- no deep packet inspection
- Smaller community and less active development

## psad: iptables Log-Based Intrusion Detection

**psad** (Port Scan Attack Detector) takes a fundamentally different approach from portsentry. Instead of actively monitoring ports, psad analyzes iptables LOG rule output to detect port scans, OS fingerprinting attempts, and other network reconnaissance activity. It monitors firewall logs for patterns indicating scanning behavior.

**GitHub:** [mrash/psad](https://github.com/mrash/psad) -- 421 stars

### How psad Works

psad requires iptables LOG rules that capture incoming connection attempts:

```bash
# Create a LOG chain
iptables -N LOG_AND_DROP
iptables -A LOG_AND_DROP -j LOG --log-prefix "IPTABLES: " --log-level 4
iptables -A LOG_AND_DROP -j DROP

# Route incoming traffic through the LOG chain
iptables -A INPUT -j LOG_AND_DROP
iptables -A FORWARD -j LOG_AND_DROP
```

psad tails the syslog/kern.log file, parsing LOG entries to build a picture of incoming connection patterns. It maintains per-source-IP state, tracking which ports have been probed, the scan rate, and signature matches against known attack patterns. When a scan exceeds configurable thresholds, psad can automatically add iptables blocking rules.

### Installation

```bash
# Debian/Ubuntu
sudo apt install psad

# RHEL/CentOS/Fedora
sudo dnf install psad

# Update IDS signatures
sudo psad --sig-update
sudo psad -H
sudo psad --Status
```

### Docker Deployment

```yaml
version: "3.8"
services:
  psad:
    image: ubuntu:latest
    container_name: psad-monitor
    restart: unless-stopped
    network_mode: "host"
    privileged: true
    volumes:
      - /var/log:/var/log:ro
      - /etc/psad:/etc/psad
      - /var/lib/psad:/var/lib/psad
      - /proc/net:/proc/net:ro
    entrypoint: ["/bin/sh", "-c"]
    command: |
      apt-get update && apt-get install -y psad iptables kmod
      psad --sig-update
      psad --Health
      tail -f /var/log/syslog
```

### Configuration

```ini
# /etc/psad/psad.conf
EMAIL_ADDRESSES="admin@example.com"
HOSTNAME=yourserver.example.com

IPT_SYSLOG_FILE = /var/log/kern.log

# Danger levels (packets per scan)
DANGER_LEVEL1 = 5
DANGER_LEVEL2 = 15
DANGER_LEVEL3 = 250
DANGER_LEVEL4 = 1500
DANGER_LEVEL5 = 10000

# Enable auto-blocking
ENABLE_AUTO_IDS = Y
ENABLE_AUTO_IDS_EMAIL = Y
AUTO_IDS_DANGER_LEVEL = 4
AUTO_BLOCK_TIMEOUT = 3600
```

### Key Features

- Passive detection via iptables logs -- no port binding required
- IDS signature matching (Snort-compatible rule signatures)
- OS fingerprinting detection
- Per-IP scan tracking with danger level classification
- Automatic iptables blocking at configurable thresholds
- Email alerting with scan details
- SYN flood detection
- Works with both iptables and nftables (via logging)

### Limitations

- Requires iptables LOG rules (adds overhead to firewall)
- Log parsing can be CPU-intensive on high-traffic servers
- More complex configuration than portsentry
- Less active development (last update 2023)

## scanlogd: Lightweight SYN Scan Detector

**scanlogd** is the simplest of the three tools -- a minimal daemon that detects and logs port scan activity. It uses a probabilistic approach to detect scans based on connection patterns, logging detected scans to syslog without automatic blocking capability.

**Note:** scanlogd is primarily an OpenBSD tool but has Linux ports available. It is the most lightweight option but offers the fewest features.

### How scanlogd Works

scanlogd monitors network traffic using libpcap, tracking incoming SYN packets per source IP. When a single source sends SYN packets to multiple destination ports within a time window, scanlogd logs the detection to syslog. It does not perform automatic blocking -- it is a detection-only tool.

### Installation

```bash
# Debian/Ubuntu
sudo apt install scanlogd
```

### Docker Deployment

```yaml
version: "3.8"
services:
  scanlogd:
    image: alpine:latest
    container_name: scanlogd-monitor
    restart: unless-stopped
    network_mode: "host"
    cap_add:
      - NET_RAW
      - NET_ADMIN
    entrypoint: ["/bin/sh", "-c"]
    command: |
      apk add --no-cache scanlogd libpcap
      scanlogd -i eth0
```

### Key Features

- Extremely lightweight -- minimal memory and CPU usage
- Passive pcap-based detection -- no firewall rules needed
- Simple syslog output
- Detects SYN scan patterns
- No automatic blocking (detection only)

### Limitations

- Detection only -- no automatic blocking
- Limited to SYN scan detection
- Less configurable than portsentry or psad
- Smaller community and fewer deployment resources

## Comparison Table

| Feature | portsentry | psad | scanlogd |
|---------|-----------|------|----------|
| Detection Method | Active port monitoring | iptables log analysis | pcap SYN tracking |
| Scan Types | TCP/UDP connect, SYN | TCP/UDP, OS fingerprint, SYN flood | SYN scans only |
| Auto-Blocking | Yes (iptables, hosts.deny) | Yes (iptables) | No |
| IDS Signatures | No | Yes (Snort-compatible) | No |
| Resource Usage | Low | Medium (log parsing) | Minimal |
| Firewall Required | No | Yes (iptables LOG rules) | No (libpcap) |
| Email Alerting | Via custom command | Built-in | Via syslog |
| OS Fingerprinting | No | Yes | No |
| SYN Flood Detection | No | Yes | No |
| Config Complexity | Simple | Complex | Minimal |
| Best For | Simple active monitoring | Comprehensive IDS | Lightweight detection |

## Why Self-Host Port Scan Detection?

Port scanning is the reconnaissance phase of virtually every network attack. Automated bots continuously scan the entire IPv4 address space, probing for vulnerable services, open databases, misconfigured APIs, and unpatched software. Without port scan detection, your server logs accumulate thousands of probe attempts that go unnoticed until an exploit succeeds.

Self-hosted port scan detection provides an early warning system that operates at the network level, before application-layer attacks reach your services. By automatically blocking scanning IPs, you reduce your attack surface and make your infrastructure less attractive to automated scanning campaigns.

For homelab operators exposing services to the internet, port scan detection is a critical security layer. Internet-facing servers receive constant scanning from botnets, vulnerability scanners, and opportunistic attackers. Detecting and blocking these probes prevents follow-up exploitation attempts.

For enterprise infrastructure, psad's IDS signature matching and email alerting integrate with existing security operations workflows. Scan detection data feeds into SIEM platforms and incident response processes.

For related network security topics, see our [XDP/eBPF firewall guide](../2026-05-13-self-hosted-xdp-ebpf-network-firewalls-xdp-tools-bcc-cilium-guide/) for high-performance packet filtering and our [Linux kernel security auditing guide](../2026-05-23-linux-kernel-security-auditing-kconfig-hardened-check-checksec-guide/) for kernel configuration hardening.

## Choosing the Right Tool

**Use portsentry** if you want simple, active port monitoring with immediate detection and blocking. It is the easiest to deploy and works well for servers with a known set of listening services.

**Use psad** if you need comprehensive intrusion detection with IDS signature matching, OS fingerprinting detection, and automatic blocking. It is the most feature-complete option and best suited for production servers with significant internet exposure.

**Use scanlogd** if you want minimal-resource SYN scan detection for logging purposes only. It is the lightest option but lacks automatic blocking, making it better suited for monitoring than active defense.

## FAQ

### Can port scan detection tools cause false positives?
Yes. Legitimate services like search engine crawlers, vulnerability scanners you run yourself, and CDN health checks can trigger scan detection. Always configure IP whitelists (portsentry's `portsentry.ignore`, psad's `ignore_file`) for trusted networks and known-good services. Start with alerting-only mode before enabling automatic blocking.

### Does psad work with nftables?
psad was designed for iptables, but it can work with nftables if you configure nftables logging rules that output to the same syslog facility that psad monitors. The log prefix and format must match psad's expected patterns. Some administrators run iptables in compatibility mode alongside nftables for psad compatibility.

### How do I whitelist trusted IPs in portsentry?
Add IP addresses or CIDR ranges to `/etc/portsentry/portsentry.ignore` (one per line). portsentry checks this file before executing any blocking action. Common entries include your management network, CDN IP ranges, and monitoring service IPs.

### Can these tools detect slow or stealthy scans?
portsentry's stealth mode catches any connection attempt to unused ports, regardless of scan speed. psad's per-IP state tracking can detect slow scans if you configure appropriate time windows. scanlogd's probabilistic approach is better at detecting rapid scans than slow, distributed probing.

### Should I combine port scan detection with fail2ban?
Yes. Port scan detection tools operate at the network level, detecting scanning behavior. fail2ban operates at the application level, detecting failed login attempts, brute-force attacks, and application-level abuse. Together they provide defense at both the network and application layers.

### Do these tools impact server performance?
portsentry and scanlogd have negligible performance impact. psad's log parsing adds some CPU overhead on high-traffic servers -- the iptables LOG rules generate additional syslog entries that psad must process. On servers handling thousands of connections per second, consider tuning psad's log parsing interval or using a dedicated log aggregation pipeline.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Port Scan Detection: portsentry vs psad vs scanlogd",
  "description": "Compare three open-source port scan detection tools for Linux -- active monitoring, iptables log analysis, and pcap-based detection with automatic IP blocking.",
  "datePublished": "2026-05-24",
  "dateModified": "2026-05-24",
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
