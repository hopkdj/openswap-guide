---
title: "Self-Hosted Traffic Shaping & QoS Management — SQM Scripts vs tc-gui vs Wondershaper"
date: "2026-05-13"
tags: ["networking", "qos", "traffic-shaping", "self-hosted", "comparison", "guide"]
draft: false
description: "Compare self-hosted traffic shaping and QoS management tools — SQM Scripts, tc-gui, and Wondershaper. Learn to control bandwidth, reduce bufferbloat, and optimize network performance on Linux."
---

If you manage a Linux server or home router, uncontrolled bandwidth usage can cripple your network. Video streams saturate your upload, large downloads kill latency, and interactive sessions become unusable. Traffic shaping and Quality of Service (QoS) tools solve this by prioritizing critical traffic, capping bandwidth hogs, and eliminating bufferbloat.

Commercial QoS appliances cost thousands. This guide covers three powerful **self-hosted, open-source alternatives** that give you enterprise-grade traffic control on any Linux machine.

## What Is Traffic Shaping?

Traffic shaping (also called packet shaping) is the practice of controlling network traffic to optimize performance, reduce latency, and ensure fair bandwidth allocation. Unlike simple rate limiting, traffic shaping uses sophisticated queuing algorithms to:

- **Prioritize** interactive traffic (VoIP, gaming, SSH) over bulk transfers
- **Cap bandwidth** for specific users, services, or applications
- **Eliminate bufferbloat** — the latency spike caused by oversized network buffers
- **Enforce fair usage** across multiple users on shared connections

Linux implements traffic shaping through the **Traffic Control (tc)** subsystem, which uses queuing disciplines (qdiscs) like FQ-CoDel, CAKE, HTB, and TBF. The tools below provide different interfaces to this underlying system.

## Comparison Table

| Feature | SQM Scripts | tc-gui | Wondershaper |
|---------|-------------|--------|--------------|
| **Stars** | 273+ | 181+ | 6+ (fork) |
| **Language** | Shell/Shell | Python | Shell |
| **Web UI** | No (CLI/LuCI) | Yes (Flask) | No (CLI) |
| **Qdisc** | FQ-CoDel, CAKE | HTB, TBF, NetEm | HTB, TBF |
| **Bufferbloat Fix** | Excellent | Good | Basic |
| **Per-IP Shaping** | Yes | Yes | No |
| **Class-based QoS** | Yes | Yes | No |
| **OpenWrt Support** | Native | No | No |
| **Docker Deploy** | Limited | Yes | No |
| **Best For** | Home routers, OpenWrt | Server admin GUI | Quick one-liner setup |

## SQM Scripts (Smart Queue Management)

**GitHub:** [tohojo/sqm-scripts](https://github.com/tohojo/sqm-scripts) (273+ stars)

SQM Scripts is the gold standard for bufferbloat elimination. Created by Toke Høiland-Jørgensen and Dave Täht, it implements the CAKE and FQ-CoDel queuing algorithms that won the Bufferbloat Prize. It's the default QoS engine in OpenWrt and runs on any Linux system with `tc` support.

### How It Works

SQM Scripts wraps the Linux `tc` subsystem with intelligent defaults:

```bash
# Install on Debian/Ubuntu
apt install sqm-scripts

# Enable on an interface (e.g., eth0)
systemctl enable --now sqm

# Configure in /etc/sqm-scripts/sqm.conf
LINK="eth0"
DOWNLINK="100000"   # 100 Mbps download
UPLINK="50000"      # 50 Mbps upload
```

The key configuration parameters:

```bash
# /etc/sqm-scripts/sqm.conf
INGRESS="ifb"           # Use IFB for ingress shaping
EGRESS="cake"           # Use CAKE qdisc (best overall)
# EGRESS="fq_codel"     # Alternative: FQ-CoDel (lower CPU)
DOWNLOAD="100000"       # kbps - set to ~90-95% of actual speed
UPLOAD="50000"          # kbps - set to ~90-95% of actual speed
```

### Docker Compose (Limited)

SQM Scripts requires direct access to the host's `tc` subsystem, making full containerization impractical. However, you can run it via a privileged container:

```yaml
version: "3.8"
services:
  sqm:
    image: alpine:latest
    privileged: true
    network_mode: host
    volumes:
      - /etc/sqm-scripts:/etc/sqm-scripts
      - /sbin/tc:/sbin/tc
    command: >
      sh -c "apk add iproute2 bash && 
             /etc/sqm-scripts/sqm start"
```

### When to Use SQM Scripts

- **Home routers and OpenWrt devices** — it's the default QoS system
- **Bufferbloat elimination** — best-in-class CAKE/FQ-CoDel algorithms
- **Per-flow fairness** — automatically isolates and shapes individual flows
- **Zero configuration** — works well with just bandwidth limits set

## tc-gui (Traffic Control Web GUI)

**GitHub:** [tum-lkn/tcgui](https://github.com/tum-lkn/tcgui) (181+ stars)

tc-gui is a lightweight Python Flask web application that provides a graphical interface for Linux Traffic Control (`tc`). It lets you create, view, and manage traffic shaping rules without memorizing complex `tc` syntax.

### Installation

```bash
# Install dependencies
pip install flask

# Clone and run
git clone https://github.com/tum-lkn/tcgui.git
cd tcgui
python3 app.py
# Web UI available at http://localhost:5000
```

### Docker Compose

```yaml
version: "3.8"
services:
  tcgui:
    image: python:3.11-slim
    working_dir: /app
    volumes:
      - ./tcgui:/app
    ports:
      - "5000:5000"
    cap_add:
      - NET_ADMIN
    command: >
      bash -c "pip install flask && 
               python3 app.py"
```

### Features

- **Visual rule creation** — set bandwidth limits, priorities, and classes through a web form
- **Real-time monitoring** — view current queue states and packet counts
- **HTB and TBF support** — class-based and token bucket shaping
- **Persistent rules** — save configurations that survive reboots
- **No database required** — file-based configuration

### When to Use tc-gui

- **Server administrators** who prefer web interfaces over CLI
- **Teams managing multiple servers** — consistent UI across machines
- **Learning tc** — visual representation helps understand queuing concepts
- **Quick rule prototyping** — test shaping rules before committing to scripts

## Wondershaper

**GitHub:** [mayfrost/wondershaper](https://github.com/mayfrost/wondershaper) (6+ stars, fork of the original)

Wondershaper is the simplest traffic shaper — a single shell script that sets up HTB queuing with minimal configuration. It's designed for "set it and forget it" scenarios where you just want to cap upload and download speeds on a single interface.

### Installation

```bash
# Install on Debian/Ubuntu
apt install wondershaper

# Or clone the maintained fork
git clone https://github.com/mayfrost/wondershaper.git
cd wondershaper
chmod +x wondershaper
```

### Usage

```bash
# Start shaping: interface downlimit uplimit (in Kbps)
./wondershaper eth0 100000 50000

# Stop shaping
./wondershaper clear eth0

# Check status
./wondershaper status eth0
```

### Systemd Service

```ini
# /etc/systemd/system/wondershaper.service
[Unit]
Description=Wondershaper Traffic Shaper
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/wondershaper eth0 100000 50000
ExecStop=/usr/local/bin/wondershaper clear eth0
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable --now wondershaper
```

### When to Use Wondershaper

- **Quick bandwidth capping** on a single interface
- **VPS servers** where you need to limit total bandwidth usage
- **Simple setups** that don't need per-flow or per-IP shaping
- **Legacy systems** where SQM Scripts isn't available

## Why Self-Host Your Traffic Shaping?

Running your own traffic shaping solution has significant advantages over cloud-based or hardware QoS appliances:

### No Vendor Lock-In

Commercial QoS appliances from Cisco, Palo Alto, and Fortinet cost $2,000–$10,000+ and lock you into proprietary ecosystems. Open-source tools run on any Linux machine — a $35 Raspberry Pi or an existing server.

### Complete Control Over Bufferbloat

Bufferbloat causes lag spikes during file transfers or streaming. SQM Scripts' CAKE algorithm is proven to reduce latency by 90%+ under load. Cloud providers can't fix bufferbloat on your last-mile connection — you need local shaping.

### Per-Application Prioritization

Self-hosted tools let you define custom traffic classes:

```bash
# Example: HTB class hierarchy
tc class add dev eth0 parent 1: classid 1:1 htb rate 100mbit ceil 100mbit
tc class add dev eth0 parent 1:1 classid 1:10 htb rate 50mbit ceil 100mbit prio 1  # VoIP
tc class add dev eth0 parent 1:1 classid 1:20 htb rate 30mbit ceil 80mbit prio 2   # Web
tc class add dev eth0 parent 1:1 classid 1:30 htb rate 20mbit ceil 50mbit prio 3   # Bulk
```

### Integration With Existing Infrastructure

Traffic shaping tools integrate with your existing firewall (iptables/nftables), monitoring (Prometheus/Grafana), and configuration management (Ansible).

## Network Integration

Traffic shaping works best when combined with other network infrastructure tools. For comprehensive network management, integrate your QoS solution with firewall rules for packet classification and DNS management for traffic routing. Our [firewall management guide](../2026-05-08-self-hosted-firewall-management-firehol-shorewall-ferm-guide/) covers iptables/nftables integration, while [DNS load balancing](../2026-05-13-self-hosted-dns-load-balancing-dnsdist-powerdns-knot-resolver-guide/) shows how to distribute traffic before shaping it. For advanced packet filtering, see our [XDP/eBPF firewall comparison](../2026-05-13-self-hosted-xdp-ebpf-network-firewalls-xdp-tools-bcc-cilium-guide/).

## Choosing the Right Traffic Shaping Tool

| Scenario | Recommended Tool | Reason |
|----------|-----------------|--------|
| Home router / OpenWrt | SQM Scripts | Native support, best bufferbloat fix |
| Server with web admin preference | tc-gui | Visual interface, easy rule management |
| Quick VPS bandwidth cap | Wondershaper | One-liner setup, no configuration |
| Enterprise class-based QoS | SQM Scripts + tc | CAKE + custom HTB classes |
| Learning traffic control | tc-gui | Visual representation of tc concepts |

## FAQ

### What is bufferbloat and why does it matter?

Bufferbloat occurs when network devices (routers, modems) use oversized buffers that fill up during heavy traffic. This causes latency spikes from milliseconds to seconds, making VoIP calls drop, games lag, and web pages stall. SQM Scripts with CAKE or FQ-CoDel actively manages buffer sizes, keeping latency low even under full load.

### Can I run traffic shaping in a Docker container?

Partially. The Linux `tc` subsystem operates at the kernel level. tc-gui can run in a container with `--cap-add=NET_ADMIN` and `network_mode: host`. SQM Scripts requires direct host access to `tc` and network interfaces — it works best as a host service. Wondershaper needs to run on the host since it directly modifies qdisc settings.

### How do I determine the correct bandwidth limits?

Set your shaped bandwidth to **90-95% of your actual connection speed**. If your ISP provides 100 Mbps download and 50 Mbps upload, configure SQM Scripts with 95,000 kbps downlink and 47,500 kbps uplink. This leaves headroom for the queuing algorithms to work effectively. You can measure actual speeds with `iperf3` or `speedtest-cli`.

### Does traffic shaping reduce total throughput?

Slightly, but the tradeoff is worth it. Proper traffic shaping typically reduces maximum throughput by 2-5% while dramatically improving latency and responsiveness under load. A 100 Mbps connection shaped at 95 Mbps will feel faster for interactive use because packets aren't stuck in bloated queues.

### Is SQM Scripts compatible with WiFi networks?

Yes, SQM Scripts works on any network interface, including WiFi. However, WiFi introduces additional variable latency that can make bufferbloat worse. For best results, apply SQM Scripts on the wired WAN interface (the connection to your modem) rather than the WiFi LAN interface.

### Can I combine multiple traffic shaping tools?

Not recommended. Multiple tools operating on the same interface will conflict with each other's qdisc configurations. Choose one tool and configure all your shaping rules through it. You can use Wondershaper on one interface and SQM Scripts on another, but never on the same interface simultaneously.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Traffic Shaping & QoS Management — SQM Scripts vs tc-gui vs Wondershaper",
  "description": "Compare self-hosted traffic shaping and QoS management tools — SQM Scripts, tc-gui, and Wondershaper. Learn to control bandwidth, reduce bufferbloat, and optimize network performance on Linux.",
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
