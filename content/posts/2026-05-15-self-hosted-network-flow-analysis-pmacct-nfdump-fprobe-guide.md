---
title: "Self-Hosted Network Flow Analysis: pmacct vs nfdump vs fprobe (2026)"
date: "2026-05-07"
draft: false
tags: ["networking", "netflow", "monitoring", "pmacct", "nfdump", "fprobe", "self-hosted"]
---

Network flow analysis is essential for understanding traffic patterns, diagnosing bottlenecks, and detecting anomalies in your infrastructure. Flow-based monitoring captures metadata about network conversations — source and destination IPs, ports, protocols, byte counts — without storing full packet captures, making it scalable for high-throughput networks.

This guide compares three foundational open-source flow tools: **pmacct**, **nfdump**, and **fprobe**. Together they form a complete flow pipeline: export, collect, process, and analyze.

## Understanding Network Flow Protocols

Before comparing tools, it helps to understand the flow protocols they support:

- **NetFlow v5** — Cisco's original flow export format (IPv4 only, fixed 7 fields)
- **NetFlow v9** — Template-based, extensible, supports IPv6 and custom fields
- **IPFIX (RFC 7012)** — IETF standard based on NetFlow v9, the modern flow protocol
- **sFlow** — Packet sampling-based flow protocol, implemented in switches and routers

Flow tools fall into three categories:

1. **Flow exporters (probes)** — Capture packets and export flow records to a collector
2. **Flow collectors** — Receive and store flow records from exporters
3. **Flow analyzers** — Query stored flow data and produce reports

pmacct and nfdump span all three categories; fprobe is primarily an exporter.

## pmacct: The Multi-Purpose Flow Suite

[pmacct](https://github.com/pmacct/pmacct) (1,210 stars on GitHub) is a Swiss-army knife for network traffic accounting. It supports NetFlow, IPFIX, sFlow, BGP, BMP, and raw pcap capture — all in a single toolkit. pmacct can act as a collector, exporter, aggregator, and data publisher simultaneously.

### Key Features

- Multiple daemons: `pmacctd` (pcap), `nfacctd` (NetFlow/IPFIX), `sfacctd` (sFlow), `pmbgpd` (BGP)
- Plugin architecture: output to SQL databases, Kafka, Redis, RabbitMQ, MongoDB, Prometheus
- Active flow aggregation and filtering with BPF expressions
- Historical data replay and accounting
- BGP route monitoring and BMP (BGP Monitoring Protocol) support
- NetFlow v5/v9 and IPFIX collector and exporter

### Docker Deployment

pmacct provides official Docker images for each daemon:

```yaml
version: "3.8"
services:
  nfacctd:
    image: pmacct/nfacctd:latest
    container_name: pmacct-nfacctd
    ports:
      - "2055:2055/udp"
    volumes:
      - ./pmacct-nfacctd.conf:/etc/pmacct/pmacct.conf:ro
      - pmacct-data:/var/lib/pmacct
    restart: unless-stopped
    networks:
      - monitoring

  sfacctd:
    image: pmacct/sfacctd:latest
    container_name: pmacct-sfacctd
    ports:
      - "6343:6343/udp"
    volumes:
      - ./pmacct-sfacctd.conf:/etc/pmacct/pmacct.conf:ro
      - pmacct-data:/var/lib/pmacct
    restart: unless-stopped
    networks:
      - monitoring

volumes:
  pmacct-data:
```

Sample `pmacct-nfacctd.conf` for NetFlow collection to SQLite:

```ini
daemonize: true
pidfile: /var/run/nfacctd.pid

# Listen for NetFlow v5/v9/IPFIX
nfprobe_port: 2055

# Store flows in SQLite
plugin: sqlite
plugin_pipe_size: 10000000
plugin_buffer_size: 100000
sqlite_db: /var/lib/pmacct/flows.db
sqlite_table:acct

# Aggregation: per source-destination pair
aggregate: src_host,dst_host,src_port,dst_port,proto
```

### When to Use pmacct

- You need a unified tool for NetFlow, sFlow, and BGP monitoring
- Flow data must be exported to databases or message queues
- Active traffic accounting with real-time aggregation
- Multi-tenant environments requiring per-customer flow accounting

## nfdump: The NetFlow Processing Toolkit

[nfdump](https://github.com/phaag/nfdump) (898 stars) is a mature, high-performance NetFlow processing suite. It consists of `nfcapd` (flow capture daemon), `nfdump` (flow query tool), and `nfreplay` (flow replay utility). nfdump is designed for speed — it processes millions of flow records with minimal overhead.

### Key Features

- `nfcapd`: High-speed NetFlow v5/v9 and IPFIX collector
- `nfdump`: Rich filtering and reporting (top-N, time ranges, protocol breakdowns)
- `nfreplay`: Replay captured flows for testing and analysis
- Binary flow file format for efficient storage
- Extension blocks for custom fields (NSEL, NAT tracking)
- Profile-based storage organization (daily, weekly, monthly rotations)

### Docker Deployment

Community Docker images are available:

```yaml
version: "3.8"
services:
  nfcapd:
    image: heywoodlh/nfdump:latest
    container_name: nfcapd
    ports:
      - "2055:2055/udp"
    volumes:
      - nfdump-data:/data
    environment:
      - INTERFACE=eth0
      - PORT=2055
    restart: unless-stopped
    networks:
      - monitoring

volumes:
  nfdump-data:
```

Capture daemon configuration:

```bash
# Start nfcapd listening on UDP 2055
nfcapd -w -l /data/flows -p 2055 -P /var/run/nfcapd.pid

# Rotate flow files every 5 minutes
nfcapd -w -l /data/flows -p 2055 -t 300

# Enable IPFIX with extension support
nfcapd -w -l /data/flows -p 4739 -T all
```

Query examples:

```bash
# Top 10 talkers by bytes
nfdump -r /data/flows/nfcapd.202605150000 -T bytes -n 10

# Flow summary for a time range
nfdump -r /data/flows/ -t '2026/05/15.08:00-2026/05/15.17:00' -s srcip/

# Filter by destination port
nfdump -r /data/flows/nfcapd.202605150000 'dst port 443'

# Show top protocols
nfdump -r /data/flows/nfcapd.202605150000 -s proto
```

### When to Use nfdump

- You need fast, reliable NetFlow/IPFIX collection with minimal setup
- Historical flow analysis with rich filtering capabilities
- Forensic traffic investigation (replay captured flows)
- Environments where simple file-based storage is preferred over databases

## fprobe: The Lightweight Flow Exporter

[fprobe](https://github.com/alexander-buzanov/fprobe) is a libpcap-based NetFlow exporter that captures packets on a network interface and exports flow records to a collector. It is ideal for adding flow export capability to hosts that do not have built-in NetFlow support.

### Key Features

- Captures packets via libpcap and exports as NetFlow v5/v9 or IPFIX
- Lightweight: single daemon, minimal resource usage
- Configurable flow timeout (active and inactive)
- Supports multiple collectors for redundancy
- BPF filter support for selective capture
- Works on any interface that libpcap can access

### Docker Deployment

```yaml
version: "3.8"
services:
  fprobe:
    image: alpine:latest
    container_name: fprobe
    network_mode: host
    cap_add:
      - NET_RAW
      - NET_ADMIN
    volumes:
      - ./fprobe.conf:/etc/fprobe.conf:ro
    command: sh -c "apk add fprobe && fprobe -f /etc/fprobe.conf"
    restart: unless-stopped
```

Command-line usage:

```bash
# Export flows from eth0 to collector at 10.0.0.1:2055
fprobe -i eth0 10.0.0.1:2055

# With custom flow timeout and BPF filter
fprobe -i eth0 -t 300 -f 'not port 2055' 10.0.0.1:2055

# IPFIX export with interface sampling
fprobe -i eth0 -V 10 -s 1000 10.0.0.1:4739
```

### When to Use fprobe

- Adding flow export to servers or workstations without native NetFlow
- Monitoring traffic on specific interfaces or VLANs
- Lightweight flow generation for lab environments
- Capturing east-west traffic between containers or VMs

## Comparison Table

| Feature | pmacct | nfdump | fprobe |
|---|---|---|---|
| **Primary Role** | Collector + processor + exporter | Collector + analyzer | Flow exporter (probe) |
| **GitHub Stars** | 1,210 | 898 | N/A |
| **NetFlow v5** | Yes (collector/exporter) | Yes (collector) | Yes (exporter) |
| **NetFlow v9** | Yes | Yes | Yes |
| **IPFIX** | Yes | Yes | Yes (v10) |
| **sFlow** | Yes | No | No |
| **BGP/BMP** | Yes | No | No |
| **Database Output** | SQL, Redis, Kafka, Mongo | File-based (binary) | N/A (export only) |
| **Flow Filtering** | BPF + plugin rules | Rich nfdump filter syntax | BPF capture filter |
| **Flow Replay** | No | Yes (`nfreplay`) | No |
| **Multi-collector** | Yes | Yes (nfcapd instances) | Yes |
| **Docker Image** | pmacct/* (official) | heywoodlh/nfdump (community) | Manual (apk install) |
| **Best For** | Unified flow + BGP suite | Fast collection + analysis | Adding flow export to hosts |

## Installation Guide

### Install pmacct (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install pmacct -y
sudo systemctl enable pmacctd
```

### Install nfdump (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install nfdump -y
# Start collector
sudo nfcapd -w -l /var/lib/nfdump -p 2055 -D
```

### Install fprobe (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install fprobe -y
sudo systemctl enable fprobe
```

## Why Self-Host Network Flow Analysis?

Cloud-based network monitoring services charge per flow record, per interface, or per host — costs that grow linearly with your infrastructure. Self-hosted flow tools run on commodity hardware with no per-record fees, no data caps, and no vendor-imposed retention limits.

Running your own flow pipeline means you control data retention (keep flow records for months or years for compliance), customize aggregation and filtering rules to match your network topology, and integrate flow data with existing monitoring stacks like Prometheus, Grafana, or Elasticsearch. For multi-site organizations, self-hosted flow collectors at each site reduce WAN bandwidth by processing flows locally before forwarding summaries.

For network traffic visualization, see our [network traffic analysis guide](../2026-05-06-self-hosted-network-traffic-analysis-ntopng-arkime-zeek-guide/). If you need bandwidth monitoring at the host level, our [bandwidth monitoring comparison](../vnstat-vs-nethogs-vs-iftop-self-hosted-bandwidth-monito/) covers per-interface traffic accounting tools. For complete network device monitoring, our [network monitoring guide](../zabbix-vs-librenms-vs-netdata-network-monitoring-guide/) provides device-level coverage.

## FAQ

### What is the difference between NetFlow, IPFIX, and sFlow?

NetFlow (v5/v9) is Cisco's proprietary flow export protocol. IPFIX is the IETF standard based on NetFlow v9, adding extensibility and IPv6 support. sFlow uses packet sampling (typically 1 in N packets) rather than full flow tracking, making it more scalable for high-speed links but less precise for low-volume traffic. pmacct supports all three; nfdump supports NetFlow and IPFIX; fprobe exports NetFlow and IPFIX.

### Can I use pmacct and nfdump together?

Yes. A common architecture uses fprobe or router-based flow export to send NetFlow records to both pmacct (for database storage and real-time aggregation) and nfdump (for fast file-based collection and ad-hoc analysis). This gives you both structured querying and rapid forensic analysis capabilities.

### How much storage does flow data require?

Flow records are lightweight compared to full packet captures. A typical enterprise router generates 1-5 GB of flow data per day. nfdump's binary format compresses well (50-70% with gzip). pmacct's database storage depends on your aggregation rules — aggressive aggregation (per-hour, per-subnet) reduces storage significantly. Plan for 5-15 GB per day for a mid-size network.

### Does fprobe impact host performance?

fprobe uses libpcap to capture packets in the kernel, which has minimal overhead for moderate traffic rates (< 1 Gbps). For high-throughput hosts (> 10 Gbps), consider using router-based flow export instead, or configure fprobe with BPF filters to exclude high-volume traffic (backups, replication) from flow accounting.

### Which tool should I choose for a production network?

For comprehensive flow analysis with database integration and BGP monitoring, use **pmacct**. For fast, simple NetFlow/IPFIX collection with rich query capabilities, use **nfdump**. For adding flow export capability to individual hosts or containers, use **fprobe** as the probe sending data to your pmacct or nfdump collector.

## JSON-LD Structured Data

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Network Flow Analysis: pmacct vs nfdump vs fprobe (2026)",
  "description": "Compare three open-source network flow tools for traffic analysis: pmacct for multi-protocol flow collection, nfdump for fast NetFlow processing, and fprobe for lightweight flow export.",
  "datePublished": "2026-05-07",
  "dateModified": "2026-05-07",
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
