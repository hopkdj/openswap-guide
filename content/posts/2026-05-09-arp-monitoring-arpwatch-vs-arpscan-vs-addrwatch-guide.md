---
title: "Self-Hosted ARP Monitoring: arpwatch vs arp-scan vs addrwatch Guide"
date: "2026-05-09"
tags: ["comparison", "guide", "self-hosted", "networking", "security", "monitoring"]
draft: false
---

ARP (Address Resolution Protocol) monitoring is essential for any self-hosted network. Whether you're detecting rogue devices on your home lab, identifying ARP spoofing attacks, or simply maintaining an inventory of connected devices, having the right ARP monitoring tool can make the difference between a secure network and an open door to attackers. In this guide, we compare three open-source ARP monitoring tools — **arpwatch**, **arp-scan**, and **addrwatch** — so you can choose the right solution for your infrastructure.

## What Is ARP Monitoring and Why It Matters

ARP is the protocol that maps IP addresses to MAC addresses on a local network. Because ARP was designed without authentication, it is inherently vulnerable to spoofing attacks where an attacker sends fake ARP messages to redirect traffic through their machine (a man-in-the-middle attack). ARP monitoring tools detect these anomalies by watching ARP traffic and alerting you to suspicious changes in the IP-to-MAC mapping.

A self-hosted ARP monitor runs continuously on your network, building a database of known device MAC addresses and flagging any unauthorized changes. This is especially critical in environments where:

- **Network security** is a priority — detecting ARP poisoning attempts before they lead to data breaches
- **Device inventory management** is needed — automatically tracking which devices join or leave your network
- **Compliance requirements** demand network audit trails — maintaining logs of all network activity
- **IoT and smart home** environments exist — monitoring unauthorized devices on your network

## arpwatch — The Classic ARP Monitor

**arpwatch** has been the go-to ARP monitoring tool on Unix-like systems for decades. Originally developed by Lawrence Berkeley National Laboratory, it passively listens to ARP traffic on your network and maintains a database of IP/MAC address pairs in `/var/lib/arpwatch/arp.dat`.

### Key Features

- **Passive monitoring** — listens to ARP/RARP traffic without sending any packets
- **Email alerts** — sends notifications when new devices appear or existing mappings change
- **Persistent database** — stores all observed ARP mappings for historical analysis
- **Low resource usage** — runs as a lightweight daemon with minimal CPU and memory footprint
- **Built into most Linux distributions** — available via apt, yum, pacman out of the box

### Installation

On Debian/Ubuntu:

```bash
sudo apt update
sudo apt install arpwatch
```

On Alpine Linux (Docker-friendly):

```bash
apk add arpwatch
```

### Docker Deployment

Since arpwatch has no official Docker image, you can build a simple container:

```dockerfile
FROM alpine:latest
RUN apk add --no-cache arpwatch mailx
COPY arpwatch-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
```

```bash
#!/bin/sh
# entrypoint.sh
exec arpwatch -i eth0 -f /data/arp.dat -N -n 192.168.1.0/24
```

Build and run:

```bash
docker build -t arpwatch-monitor .
docker run -d --name arpwatch \
  --network host \
  -v /var/lib/arpwatch:/data \
  arpwatch-monitor
```

### Configuration

arpwatch reads from the network interface you specify. Key options include:

```bash
# Monitor specific interface
arpwatch -i eth0

# Send alerts to specific email
arpwatch -i eth0 -e admin@example.com

# Suppress normal activity, only report flips
arpwatch -i eth0 -N

# Monitor specific subnet
arpwatch -i eth0 -n 192.168.1.0/24
```

### Pros and Cons

| Aspect | Rating | Notes |
|--------|--------|-------|
| Setup complexity | Easy | One command, works immediately |
| Resource usage | Excellent | ~2MB memory footprint |
| Alert quality | Good | Email-based, can be noisy |
| Modern features | Limited | No web UI, no API |
| Docker support | Basic | Requires custom image |

## arp-scan — The Active Network Scanner

**arp-scan** takes a different approach: instead of passively listening, it actively sends ARP requests to discover all devices on your network. With over 1,200 stars on GitHub, it is one of the most popular ARP scanning tools available.

### Key Features

- **Active scanning** — sends ARP requests to every IP in a range for comprehensive discovery
- **Device fingerprinting** — identifies device types by MAC address OUI lookup
- **Flexible output** — supports plain text, CSV, and custom format strings
- **Fast scanning** — can scan a /24 network in seconds
- **No database needed** — results are immediate, no persistent state required

### Installation

On Debian/Ubuntu:

```bash
sudo apt update
sudo apt install arp-scan
```

Build from source:

```bash
git clone https://github.com/royhills/arp-scan.git
cd arp-scan
autoreconf -i
./configure
make
sudo make install
```

### Docker Deployment

```dockerfile
FROM alpine:latest
RUN apk add --no-cache arp-scan
ENTRYPOINT ["arp-scan"]
```

```bash
docker build -t arp-scan-tool .
docker run --rm --network host arp-scan-tool --localnet
```

### Usage Examples

```bash
# Scan local network
sudo arp-scan --localnet

# Scan specific range
sudo arp-scan 192.168.1.0/24

# Detailed output with device names
sudo arp-scan --localnet --resolved

# CSV output for processing
sudo arp-scan --localnet --format='${ip}\t${mac}\t${vendor}'

# Continuous monitoring with interval
while true; do
  sudo arp-scan --localnet --quiet | sort -u
  sleep 60
done
```

### Automation Script

For continuous monitoring, combine arp-scan with a simple script:

```bash
#!/bin/bash
KNOWN_DEVICES="/etc/arp-scan/known.txt"
NEW_DEVICES="/etc/arp-scan/new.txt"

# Scan and compare
sudo arp-scan --localnet --quiet | sort -u > /tmp/current-scan.txt
comm -23 /tmp/current-scan.txt "$KNOWN_DEVICES" > "$NEW_DEVICES"

if [ -s "$NEW_DEVICES" ]; then
  echo "New devices detected:"
  cat "$NEW_DEVICES"
  # Send alert (email, webhook, etc.)
fi
```

### Pros and Cons

| Aspect | Rating | Notes |
|--------|--------|-------|
| Setup complexity | Easy | Single binary, no configuration |
| Scan speed | Excellent | Sub-second for /24 networks |
| Device identification | Good | OUI database built-in |
| Passive detection | No | Active scanning only |
| Historical tracking | Manual | Requires external scripting |

## addrwatch — The Modern ARP Monitor

**addrwatch** is a modern alternative to arpwatch, designed with contemporary security needs in mind. With active development as recently as 2026, it provides improved detection capabilities and better integration options.

### Key Features

- **Multi-protocol support** — monitors ARP, NDP (IPv6), and DHCP traffic simultaneously
- **Database backends** — supports SQLite, MySQL, and PostgreSQL for scalable storage
- **JSON logging** — structured output for easy integration with log aggregation systems
- **IPv6 awareness** — natively handles Neighbor Discovery Protocol (NDP)
- **Active development** — regularly updated with security fixes and feature additions

### Installation

On Debian/Ubuntu:

```bash
sudo apt update
sudo apt install addrwatch
```

Build from source:

```bash
git clone https://github.com/fln/addrwatch.git
cd addrwatch
mkdir build && cd build
cmake ..
make
sudo make install
```

### Docker Deployment

```dockerfile
FROM alpine:latest
RUN apk add --no-cache addrwatch sqlite
RUN mkdir -p /data
ENTRYPOINT ["addrwatch"]
CMD ["-i", "eth0", "-d", "sqlite:///data/addrwatch.db"]
```

```bash
docker build -t addrwatch-monitor .
docker run -d --name addrwatch \
  --network host \
  -v /var/lib/addrwatch:/data \
  addrwatch-monitor -i eth0 -d sqlite:///data/addrwatch.db
```

### Configuration

```bash
# Monitor with SQLite database
addrwatch -i eth0 -d sqlite:///var/lib/addrwatch.db

# Monitor with syslog output
addrwatch -i eth0 --syslog

# Monitor IPv6 NDP as well
addrwatch -i eth0 --ipv6

# JSON output for log aggregation
addrwatch -i eth0 --json | tee /var/log/addrwatch.json
```

### Database Schema

addrwatch's SQLite database provides a rich queryable dataset:

```sql
-- View all discovered devices
SELECT mac, ip, first_seen, last_seen, hostname
FROM addresses
ORDER BY last_seen DESC;

-- Find devices that changed IP
SELECT mac, COUNT(DISTINCT ip) as ip_count
FROM addresses
GROUP BY mac
HAVING ip_count > 1;

-- Detect new devices in the last hour
SELECT * FROM addresses
WHERE first_seen > datetime('now', '-1 hour');
```

### Pros and Cons

| Aspect | Rating | Notes |
|--------|--------|-------|
| Setup complexity | Moderate | Requires database configuration |
| IPv6 support | Excellent | Native NDP monitoring |
| Storage options | Flexible | SQLite, MySQL, PostgreSQL |
| Resource usage | Low | Efficient daemon design |
| Alert system | Basic | No built-in alerting |

## Comparison Table: arpwatch vs arp-scan vs addrwatch

| Feature | arpwatch | arp-scan | addrwatch |
|---------|----------|----------|-----------|
| **Monitoring mode** | Passive | Active | Passive |
| **ARP support** | Yes | Yes | Yes |
| **IPv6/NDP** | No | No | Yes |
| **DHCP monitoring** | No | No | Yes |
| **Database** | Flat file | None | SQLite/MySQL/PG |
| **Email alerts** | Built-in | Manual | Manual |
| **JSON output** | No | No | Yes |
| **Docker friendly** | Moderate | Easy | Easy |
| **Resource usage** | Very low | On-demand | Low |
| **Device fingerprinting** | No | OUI-based | OUI-based |
| **GitHub stars** | N/A (classic) | 1,252 | 202 |
| **Last update** | Maintained | 2025 | 2026 |
| **License** | BSD | GPL-3.0 | BSD |

## Choosing the Right ARP Monitor for Your Network

The choice between these three tools depends on your specific use case:

**Choose arpwatch if** you want a set-and-forget passive monitor that has been battle-tested for decades. It is ideal for basic network monitoring on small to medium networks where email alerts are sufficient. Its minimal resource usage means it can run on anything from a Raspberry Pi to a full server.

**Choose arp-scan if** you need on-demand network discovery and device inventory. It is perfect for security audits, compliance checks, and situations where you need a snapshot of all devices at a specific moment. Combine it with cron for scheduled scans.

**Choose addrwatch if** you run a modern network with IPv6 devices and need structured data storage. Its multi-protocol support and database backends make it the best choice for organizations that need to integrate ARP monitoring into their broader security operations platform.

## Why Self-Host Your ARP Monitor?

Running your own ARP monitoring solution gives you complete control over your network visibility. Commercial network monitoring platforms often require cloud connectivity, subscription fees, and expose your internal network topology to third-party services. With a self-hosted ARP monitor, all detection, logging, and alerting happens entirely on your own infrastructure.

**Data sovereignty** is a primary driver — your network topology, device inventory, and security alerts never leave your premises. This is critical for organizations with compliance requirements like SOC 2, HIPAA, or GDPR, where network audit trails must remain under your control.

**Cost savings** are significant. Commercial ARP monitoring features are typically bundled into expensive network security suites costing hundreds of dollars per month. The open-source tools covered here are free, run on commodity hardware, and require no licensing fees.

**Customization** is another advantage. You can tailor alert thresholds, integrate with your existing monitoring stack (Prometheus, Grafana, ntfy), and modify detection logic to match your network's unique patterns. Commercial tools rarely offer this level of flexibility.

For broader network security monitoring, see our [Suricata vs Snort vs Zeek IDS/IPS guide](../2026-04-18-suricata-vs-snort-vs-zeek-self-hosted-ids-ips-guide-2026/).
For intrusion prevention at the host level, check our [fail2ban vs sshguard vs CrowdSec comparison](../2026-04-24-fail2ban-vs-sshguard-vs-crowdsec-self-hosted-intrusion-prevention-2026/).
For network simulation and testing, our [GNS3 vs EVE-ng vs containerlab guide](../2026-04-18-gns3-vs-eve-ng-vs-containerlab-self-hosted-network-simulation-2026/) covers building test environments.

## FAQ

### What is ARP spoofing and how does monitoring detect it?

ARP spoofing (or ARP poisoning) is an attack where a malicious device sends fake ARP messages to associate its MAC address with another device's IP address. ARP monitoring tools detect this by observing when an IP address that was previously mapped to one MAC address suddenly maps to a different MAC address — a "flip" event that triggers an alert.

### Can these tools monitor IPv6 networks?

Only **addrwatch** natively supports IPv6 through Neighbor Discovery Protocol (NDP) monitoring. arpwatch and arp-scan are IPv4-only. For IPv6 networks, addrwatch or specialized NDP monitoring tools are required.

### How much network overhead does passive ARP monitoring add?

Passive monitoring tools like arpwatch and addrwatch add **zero network overhead** because they only listen to existing ARP traffic. They do not send any packets. arp-scan, being an active scanner, does generate ARP request packets, but these are only sent when you explicitly run a scan.

### Can I run ARP monitoring inside a Docker container?

Yes, all three tools can run in Docker containers. The key requirement is **host network mode** (`--network host`) so the container can see all ARP traffic on the network interface. Without host networking, the container only sees traffic directed to itself, severely limiting monitoring effectiveness.

### How do I integrate ARP alerts with my existing monitoring system?

For arpwatch, configure the `-e` flag to send email, then pipe email to your alerting system. For arp-scan, write a wrapper script that parses output and sends webhooks. For addrwatch, use the `--json` flag and pipe output to log aggregation tools like Fluent Bit or Vector. All three can integrate with ntfy, Gotify, or custom webhook endpoints.

### What is the difference between ARP monitoring and a network scanner like Nmap?

ARP monitoring runs **continuously** and passively watches ARP traffic in real-time, alerting to changes as they happen. Nmap is an **on-demand** scanner that probes the network at specific intervals. ARP monitoring is better for real-time security detection, while Nmap is better for periodic comprehensive audits.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted ARP Monitoring: arpwatch vs arp-scan vs addrwatch Guide",
  "description": "Compare three open-source ARP monitoring tools for self-hosted network security. Learn how to deploy arpwatch, arp-scan, and addrwatch with Docker for ARP spoofing detection.",
  "datePublished": "2026-05-09",
  "dateModified": "2026-05-09",
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
