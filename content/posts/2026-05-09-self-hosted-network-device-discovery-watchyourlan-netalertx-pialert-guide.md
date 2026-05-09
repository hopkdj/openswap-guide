---
title: "Self-Hosted Network Device Discovery: WatchYourLAN vs NetAlertX vs Pi.Alert (2026)"
date: "2026-05-09"
tags: ["networking", "monitoring", "security", "docker", "homelab"]
draft: false
---

When managing a homelab, small business network, or enterprise LAN, knowing every device on your network is critical for security and operations. Unrecognized devices can indicate unauthorized access, compromised endpoints, or simply shadow IT that needs to be documented. Three open-source projects specialize in this problem: **WatchYourLAN**, **NetAlertX**, and **Pi.Alert**. Each uses ARP scanning as its primary discovery mechanism but differs significantly in features, deployment, and alerting capabilities.

In this guide, we compare these three self-hosted network device discovery tools, provide Docker Compose configurations, and help you choose the right solution for your environment.

## What Is Network Device Discovery?

Network device discovery is the process of identifying and cataloging all active devices on a local area network. It typically works by:

- **ARP scanning** — sending ARP requests across subnet ranges and recording MAC/IP responses
- **ICMP ping sweeps** — probing IP ranges with ping requests
- **Port scanning** — checking open ports to fingerprint device types
- **DHCP lease monitoring** — watching DHCP server logs for new lease assignments
- **SNMP polling** — querying managed switches for connected MAC addresses on each port

The goal is to maintain a real-time inventory of connected devices, detect unknown devices the moment they appear, and alert administrators to potential unauthorized access.

## Why Self-Host Device Discovery?

Running your own network discovery service keeps all device data within your infrastructure. Commercial alternatives like Lansweeper, SolarWinds Network Device Monitor, or Spiceworks send inventory data to cloud platforms — a concern for privacy-conscious organizations and regulated environments.

Self-hosted discovery tools integrate directly with your existing monitoring stack. They can feed device lists into Prometheus exporters, trigger n8n automation workflows, or push alerts to ntfy/Gotify channels. You retain full control over scan frequency, data retention, and alert routing without licensing fees or device-count limits.

For organizations already running self-hosted DNS monitoring for query analytics, adding ARP-based device discovery completes the network visibility picture — combining layer-3 device presence with layer-7 DNS behavior.

If you need broader network reconnaissance capabilities beyond passive ARP monitoring, tools like [Nmap vs Masscan vs Rustscan](../2026-04-22-nmap-vs-masscan-vs-rustscan-self-hosted-network-scanning-guide-2026/) provide active scanning for security assessments. For PXE-based network boot workflows, our [FOG Project guide](../2026-04-20-ipxe-vs-netboot-xyz-vs-fog-project-self-hosted-pxe-network-boot-guide-2026/) covers device provisioning at scale.

## Comparison Overview

| Feature | WatchYourLAN | NetAlertX | Pi.Alert |
|---------|-------------|-----------|----------|
| **GitHub Stars** | ~6,982 | ~6,420 | ~1,086 |
| **Language** | Go | Python | Python |
| **Database** | BoltDB | SQLite | SQLite |
| **Docker Support** | Official image | Official image | Docker available |
| **ARP Scanning** | Yes | Yes | Yes |
| **ICMP Ping** | Yes | Yes | Yes |
| **Nmap Integration** | No | Yes | Yes |
| **DHCP Lease Parsing** | No | Yes | Yes |
| **SNMP Polling** | No | Yes | No |
| **Web UI** | Built-in | Built-in | Built-in |
| **Alerting** | Email, webhook, Telegram, Discord, Pushover, ntfy, Gotify, Slack, custom | Email, Telegram, Pushover, webhook, ntfy, custom | Email, webhook, Telegram |
| **Device Grouping** | No | Yes (categories, custom groups) | Yes (device types) |
| **History/Timeline** | Basic | Full history with graphs | Full history with charts |
| **Multi-Subnet** | Yes | Yes | Limited |
| **API** | REST API | REST API | Limited |
| **Grafana Export** | Yes | Yes | No |
| **Active Development** | Moderate | Very Active | Active |

## WatchYourLAN

WatchYourLAN is a lightweight network IP scanner written in Go. It provides a clean web interface for monitoring devices on your LAN through periodic ARP scans. Despite its simplicity, it includes notification support, historical tracking, and Grafana export — making it a solid choice for homelab environments.

### Key Features

- **Fast Go-based scanner** — ARP scans complete in seconds even on /16 subnets
- **BoltDB storage** — no external database required; all data stored locally
- **Grafana-ready export** — built-in endpoint for Prometheus-compatible time series
- **Notification system** — supports email, webhooks, Telegram, Discord, and Pushover for new device alerts
- **Multi-subnet scanning** — configure multiple IP ranges in a single instance

### Docker Compose Configuration

```yaml
services:
  watchyourlan:
    image: aceberg/watchyourlan:latest
    container_name: watchyourlan
    network_mode: host
    restart: unless-stopped
    environment:
      TZ: "UTC"
      IFACE: "eth0"
      HOST: "0.0.0.0"
      PORT: 8840
      GUIIP: "0.0.0.0"
      THEME: "darkly"
      DBPATH: "/data/db.sqlite"
      TIMEOUT: 120
      SCHEDULE: "*/5 * * * *"
    volumes:
      - ./data:/data
```

**Configuration notes:**
- `network_mode: host` is required because ARP scanning needs direct access to the network interface
- `IFACE` specifies the network interface to scan on (e.g., `eth0`, `enp0s3`)
- `SCHEDULE` uses cron syntax — `*/5 * * * *` runs every 5 minutes
- `TIMEOUT` is the scan timeout in seconds; increase for large subnets
- Data persists in the mounted `./data` directory

### Pros and Cons

**Pros:**
- Minimal resource footprint (Go binary, typically <50MB RAM)
- No database setup required (embedded BoltDB)
- Quick deployment — single container, no dependencies
- Clean, responsive web interface
- Grafana integration out of the box

**Cons:**
- Limited device categorization (no custom groups or labels)
- No Nmap integration for deeper device fingerprinting
- No SNMP polling for switch-level port mapping
- Basic alerting — no escalation rules or suppression windows

## NetAlertX

NetAlertX is a centralized network visibility and continuous asset discovery platform. It combines ARP scanning with Nmap integration, SNMP polling, and DHCP lease monitoring to provide the most comprehensive device discovery of the three tools. Its alerting system is highly configurable with multiple notification channels.

### Key Features

- **Multi-source discovery** — ARP scan, Nmap, SNMP, DHCP lease parsing, Pi-hole API integration
- **Rich device profiles** — automatically detects device type (router, phone, server, IoT) from MAC OUI lookups
- **Categorized grouping** — organize devices by location, type, or custom categories
- **Full history tracking** — timeline of device connections with online/offline graphs
- **Extensive alerting** — supports email, Telegram, Pushover, webhooks, ntfy, custom scripts
- **REST API** — programmatic access to device inventory and history

### Docker Compose Configuration

```yaml
services:
  netalertx:
    image: jokerwho/netalertx:latest
    container_name: netalertx
    network_mode: host
    restart: unless-stopped
    environment:
      TZ: "UTC"
      PORT: 20211
      LOG_LEVEL: "INFO"
    volumes:
      - ./db:/app/db
      - ./config:/app/config
```

**Configuration notes:**
- `network_mode: host` is required for ARP scanning
- Configuration is managed through the web UI at `http://<server-ip>:20211`
- SQLite database stored in `./db`
- Initial setup wizard guides you through subnet configuration, scan intervals, and notification channels
- For Nmap scanning, ensure `nmap` is installed on the host or use the `--cap-add=NET_ADMIN` flag

### Advanced Configuration with Nmap and SNMP

```yaml
services:
  netalertx:
    image: jokerwho/netalertx:latest
    container_name: netalertx
    network_mode: host
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
      - NET_RAW
    environment:
      TZ: "UTC"
      PORT: 20211
      SCAN_NMAP: "True"
      NMAP_SUBNETS: "192.168.1.0/24"
      SCAN_DHCP: "True"
      DHCP_LEASE_FILE: "/host/var/lib/dhcp/dhcpd.leases"
      SCAN_SNMP: "True"
      SNMP_COMMUNITY: "public"
      SNMP_HOSTS: "192.168.1.1,192.168.1.2"
    volumes:
      - ./db:/app/db
      - ./config:/app/config
      - /var/lib/dhcp:/host/var/lib/dhcp:ro
```

### Pros and Cons

**Pros:**
- Most comprehensive discovery with multiple scan methods
- Active development with frequent releases
- Rich alerting system with multiple channels
- Device categorization and custom grouping
- REST API for automation integration
- Pi-hole integration for DNS-to-device mapping

**Cons:**
- Higher resource usage than WatchYourLAN (Python-based)
- More complex initial setup due to feature richness
- Requires Nmap on the host for full functionality
- Web UI can feel dense with many configuration options

## Pi.Alert

Pi.Alert (Protect Your Network) is a lightweight WiFi/LAN intruder detector that scans connected devices and alerts you when unknown devices appear. Originally designed for Raspberry Pi homelabs, it has grown into a capable network monitoring tool with web service availability checking.

### Key Features

- **Lightweight design** — runs comfortably on Raspberry Pi hardware
- **Multi-scan support** — ARP, Pi-hole integration, router DHCP, SNMP, and Nmap
- **Web service monitoring** — checks HTTP status codes and response times for configured services
- **Offline detection** — alerts when known devices disconnect
- **Device type classification** — automatic categorization based on MAC OUI and open ports
- **Historical charts** — device presence timeline with connection/duration statistics

### Docker Compose Configuration

```yaml
services:
  pialert:
    image: leiweibau/pialert:latest
    container_name: pialert
    network_mode: host
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
      - NET_RAW
    environment:
      TZ: "UTC"
      PORT: 20211
      HOSTNAME: "pialert"
      PUID: 1000
      PGID: 1000
    volumes:
      - ./db:/home/pi/pialert/db
      - ./config:/home/pi/pialert/config
```

**Configuration notes:**
- `network_mode: host` for ARP scanning
- `PUID`/`PGID` should match your host user for file permissions
- Configuration via `pialert.conf` in the config volume or through the web UI
- Supports Pi-hole API integration — set `PIHOLE_API` in config to pull DNS query data
- For Nmap scans, install `nmap` on the host system

### Pi.Alert Configuration File

```ini
# pialert.conf excerpt
SCAN_SUBNETS    = '192.168.1.0/24 --interface=eth0'
ARPSCAN_CMD     = '/usr/bin/sudo /usr/bin/arp-scan --localnet'
PIHOLE_API      = 'http://192.168.1.10:80'
SCAN_CYCLE      = 5  # minutes
NEWDEV_EMAIL    = 'True'
OFFLINE_EMAIL   = 'True'
REPORT_HTTP     = 'True'
```

### Pros and Cons

**Pros:**
- Designed for resource-constrained hardware (Raspberry Pi)
- Web service monitoring in addition to device discovery
- Strong Pi-hole integration
- Offline device detection (alerts when devices disconnect)
- Simple, intuitive web interface

**Cons:**
- Smaller community and slower development pace
- Limited multi-subnet support compared to competitors
- No Grafana export option
- Alerting limited to email, webhooks, and Telegram
- Configuration file format can be less intuitive than UI-based setup

## Security Considerations for Device Discovery

Running continuous network scans introduces security considerations:

- **Scan frequency vs. network load** — ARP scans every 5 minutes on a /24 subnet generate minimal traffic, but scanning /16 ranges or using Nmap aggressively can cause noticeable network utilization. Start with conservative intervals and increase only if needed.

- **MAC address randomization** — modern smartphones and laptops use randomized MAC addresses when connecting to WiFi. This means a single device may appear as multiple entries. NetAlertX and Pi.Alert offer MAC-to-device correlation features to help with this.

- **Scanning untrusted networks** — never run active scans on networks you don't own or have explicit permission to monitor. ARP scanning on production networks should be coordinated with network operations teams.

- **Data retention** — device discovery logs contain MAC addresses, IP addresses, and device fingerprints. Ensure your data retention policies align with organizational privacy requirements. SQLite databases in all three tools can be backed up and encrypted at rest.

For organizations managing network policies at the container orchestration level, understanding [Kubernetes CNI options like Flannel, Calico, and Cilium](../2026-04-21-flannel-vs-calico-vs-cilium-self-hosted-kubernetes-cni-guide-2026/) provides context for how network segmentation complements device-level monitoring.

## Choosing the Right Device Discovery Tool

**Choose WatchYourLAN if:**
- You want a lightweight, fast scanner with minimal resource usage
- Your network is a single subnet or a few well-defined ranges
- You need Grafana integration for dashboarding
- You prefer simplicity over feature richness

**Choose NetAlertX if:**
- You need the most comprehensive discovery with multiple scan methods
- You have a complex network with multiple subnets and managed switches
- You want SNMP polling for switch port mapping
- You need rich alerting with multiple notification channels
- You require REST API access for automation

**Choose Pi.Alert if:**
- You're running on Raspberry Pi or similar resource-constrained hardware
- You already use Pi-hole and want tight integration
- You need web service monitoring alongside device discovery
- You want offline detection (alerts when devices disconnect)

## FAQ

### Can these tools detect devices on multiple VLANs?

WatchYourLAN supports multiple subnet ranges but requires network-level routing between VLANs. NetAlertX can poll SNMP on managed switches across VLANs to discover connected devices without direct layer-2 access. Pi.Alert has limited multi-subnet support and works best on a single broadcast domain.

### Do these tools work with Docker's default networking?

All three tools require `network_mode: host` in Docker Compose because ARP scanning operates at the data link layer (Layer 2) and needs direct access to the physical network interface. Running in bridge mode prevents ARP packets from reaching the host network.

### How do I handle MAC address randomization on smartphones?

Modern iOS and Android devices use randomized MAC addresses for privacy. NetAlertX offers device correlation by matching connection patterns and IP ranges. Pi.Alert supports fingerprint-based identification using open port profiles. WatchYourLAN does not have built-in MAC correlation — you'll need to manually merge duplicate entries.

### Can I integrate these tools with existing monitoring systems?

WatchYourLAN exports metrics to Grafana via a built-in endpoint. NetAlertX has a REST API that can feed data into any monitoring system. All three support webhook notifications for integration with automation platforms. For log-based monitoring integration, tools like [Fluent Bit, Vector, and OpenTelemetry Collector](../2026-05-09-self-hosted-log-forwarding-fluent-bit-vector-otel-collector-guide/) can forward device discovery events to centralized log platforms.

### What scan interval is recommended for production networks?

For most environments, a 5-minute ARP scan interval balances timely detection with minimal network overhead. Nmap scans should run less frequently (every 30-60 minutes) due to their higher packet volume. On large networks (/16 or larger), increase intervals to 10-15 minutes to avoid excessive broadcast traffic.

### How much storage do these tools consume?

WatchYourLAN uses embedded BoltDB and typically consumes 10-50MB for a /24 network with moderate retention. NetAlertX's SQLite database grows to 100-500MB over months of operation with full history. Pi.Alert uses similar SQLite storage — expect 50-200MB for typical homelab use. All three support database backup and pruning of old records.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Network Device Discovery: WatchYourLAN vs NetAlertX vs Pi.Alert (2026)",
  "description": "Compare three open-source network device discovery tools: WatchYourLAN, NetAlertX, and Pi.Alert. Features Docker Compose configs, feature comparison, and selection guide for self-hosted LAN monitoring.",
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
