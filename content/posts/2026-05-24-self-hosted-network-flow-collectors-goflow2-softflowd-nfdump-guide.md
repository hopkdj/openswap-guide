---
title: "Self-Hosted Network Flow Collectors: GoFlow2 vs softflowd vs nfdump (2026)"
date: "2026-05-24"
tags: ["networking", "flow-collector", "netflow", "sflow", "ipfix", "goflow2", "softflowd", "nfdump", "self-hosted", "network-monitoring"]
draft: false
---

Network flow data is the backbone of traffic analysis, capacity planning, and security monitoring. Flow protocols like NetFlow (Cisco), sFlow (sampling-based), and IPFIX (IETF standard) export metadata about network traffic — source/destination IPs, ports, protocols, byte counts — without capturing full packet payloads. This makes flow data lightweight, scalable, and privacy-friendly.

In this guide, we compare three open-source flow collection tools: **GoFlow2** (high-performance collector), **softflowd** (flow exporter probe), and **nfdump** (NetFlow processing toolkit). Each plays a different role in the flow collection pipeline.

## Comparison Table

| Feature | GoFlow2 | softflowd | nfdump |
|---------|---------|-----------|--------|
| **GitHub Stars** | 763+ | 209+ | 600+ |
| **Role** | Flow collector | Flow exporter (probe) | Flow processor/analyzer |
| **Supported Protocols** | sFlow v5, NetFlow v5/v9, IPFIX | NetFlow v5/v9, IPFIX | NetFlow v5/v9, IPFIX |
| **Architecture** | Go, concurrent pipeline | C, single-process daemon | C, file-based processing |
| **Output Format** | Protobuf, Kafka, stdout | NetFlow to collector | NFDUMP binary format |
| **Storage Backend** | External (Kafka, file) | N/A (sends to collector) | Local file (nfcapd) |
| **Scalability** | High (multi-goroutine) | Single interface | File-based, batch processing |
| **Docker Support** | Official image available | Community Dockerfiles | Official packages |
| **License** | Apache 2.0 | BSD | BSD |
| **Best For** | Centralized collection pipeline | Router/switch flow export | Offline flow analysis |

## GoFlow2

GoFlow2 is a high-performance, concurrent flow collector written in Go by the team at Netsampler. It's designed to ingest massive volumes of sFlow, NetFlow v5/v9, and IPFIX data and output structured data (Protobuf) for downstream processing.

### Key Features

- **Multi-Protocol Support**: Ingests sFlow v5, NetFlow v5, NetFlow v9, and IPFIX simultaneously on the same port.
- **Concurrent Pipeline**: Go's goroutine-based architecture enables parallel decoding and processing of flow records.
- **Protobuf Output**: Converts raw flow data to structured Protobuf messages, compatible with Kafka, file output, or stdout.
- **Prometheus Metrics**: Built-in metrics for monitoring collector health, ingestion rates, and error counts.

### Docker Compose Setup

```yaml
version: '3.8'
services:
  goflow2:
    image: ghcr.io/netsampler/goflow2:latest
    container_name: goflow2
    ports:
      - "6343:6343/udp"   # sFlow
      - "2055:2055/udp"   # NetFlow/IPFIX
      - "8080:8080"       # Prometheus metrics
    command: >
      -transport.file.path=/data/flows
      -transport=file
      -format=protobuf
    volumes:
      - flow-data:/data
    restart: unless-stopped

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    container_name: kafka
    ports:
      - "9092:9092"
    environment:
      - KAFKA_NODE_ID=1
      - KAFKA_PROCESS_ROLES=broker,controller
      - KAFKA_LISTENERS=PLAINTEXT://0.0.0.0:9092
    volumes:
      - kafka-data:/var/lib/kafka/data

volumes:
  flow-data:
  kafka-data:
```

### Sending Flow Data to Kafka

```bash
# Run GoFlow2 with Kafka transport
docker run -d \
  --name goflow2 \
  -p 6343:6343/udp \
  -p 2055:2055/udp \
  ghcr.io/netsampler/goflow2:latest \
  -transport=kafka \
  -transport.kafka.brokers=kafka:9092 \
  -transport.kafka.topic=flows
```

## softflowd

softflowd is a flow-based network traffic analyzer that generates NetFlow records from captured packets. Unlike GoFlow2 (which collects flows from network devices), softflowd acts as a **flow exporter probe** — it captures packets on a network interface and exports them as NetFlow to a collector.

### Key Features

- **Packet Capture to Flow Conversion**: Captures packets using pcap and generates Cisco-compatible NetFlow v5/v9 or IPFIX records.
- **Interface Flexibility**: Monitors any network interface, including virtual interfaces and bridges.
- **Low Resource Usage**: Written in C with minimal memory footprint — runs efficiently on routers and small appliances.
- **Template-Based Export**: NetFlow v9 and IPFIX support dynamic templates for custom field definitions.

### Installation and Usage

```bash
# Install on Debian/Ubuntu
sudo apt install softflowd

# Start monitoring eth0 and export NetFlow v9 to collector
sudo softflowd -i eth0 -n 192.168.1.100:2055 -P udp \
  -v 9 -t maxlife=1800 -t maxflows=8192
```

### Docker Deployment

```yaml
version: '3.8'
services:
  softflowd:
    image: ssugar/softflowd:latest
    container_name: softflowd
    network_mode: host
    command: >
      -i eth0
      -n 127.0.0.1:2055
      -P udp
      -v 9
      -t maxlife=1800
    cap_add:
      - NET_RAW
      - NET_ADMIN
    restart: unless-stopped
```

## nfdump

nfdump is a comprehensive NetFlow processing toolkit consisting of two main components: **nfcapd** (NetFlow capture daemon) and **nfdump** (flow analysis tool). It stores flow data in an optimized binary format and provides powerful query capabilities.

### Key Features

- **High-Speed Capture**: nfcapd captures NetFlow v5/v9 and IPFIX at line rate with minimal CPU overhead.
- **Efficient Binary Storage**: Flow records are stored in compact binary files (nfcapd files), enabling fast queries.
- **Powerful Filtering**: SQL-like filter expressions for querying flow data by IP, port, protocol, time range, and more.
- **Flow Aggregation**: Aggregate flows by various dimensions (IP pairs, AS numbers, protocols) for traffic analysis.

### Installation and Setup

```bash
# Install on Debian/Ubuntu
sudo apt install nfdump

# Start the capture daemon
sudo nfcapd -w -p 2055 -l /var/flows -S 1 -b 127.0.0.1

# Flags:
# -w: enable write compression
# -p: listen on UDP port 2055
# -l: store flow files in /var/flows
# -S 1: rotate files every 1 second (adjust for your needs)
# -b: bind address
```

### Querying Flow Data

```bash
# Top 10 talkers by bytes in the last hour
nfdump -r /var/flows/ -s ip/bytes -T 3600 | head -10

# All flows from a specific IP
nfdump -r /var/flows/ -o extended 'src ip 192.168.1.50'

# HTTP traffic (port 80/443) statistics
nfdump -r /var/flows/ -s port/bytes 'port 80 or port 443'

# Top destination AS numbers
nfdump -r /var/flows/ -s dstas/bytes -T 86400

# Export to CSV for further analysis
nfdump -r /var/flows/ -o csv -N 'port 80 or port 443' > http_flows.csv
```

### Complete Flow Collection Pipeline

```yaml
version: '3.8'
services:
  nfcapd:
    image: linuxserver/nfdump:latest
    container_name: nfcapd
    ports:
      - "2055:2055/udp"
    volumes:
      - flow-storage:/var/flows
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    command: >
      nfcapd -w -p 2055 -l /var/flows -S 1 -b 0.0.0.0
    restart: unless-stopped

volumes:
  flow-storage:
    driver: local
```

## Why Network Flow Collection is Essential for Self-Hosted Infrastructure

Network flow data provides visibility into traffic patterns without the overhead and privacy concerns of full packet capture. For self-hosted infrastructure operators, flow collection is the most practical way to understand bandwidth usage, detect anomalies, and plan capacity upgrades.

### The Value of Flow Data

Flow records capture the "five-tuple" of network communication — source IP, destination IP, source port, destination port, and protocol — along with byte and packet counts. This metadata tells you:
- **Who is talking to whom**: Identify top talkers, unusual connections, and data transfer patterns.
- **What services are consuming bandwidth**: See which applications (HTTP, DNS, database queries) dominate your network.
- **When traffic spikes occur**: Correlate flow volume with time-of-day to plan capacity and identify off-hours anomalies.
- **Where bottlenecks exist**: Pinpoint congested links, overloaded servers, and misconfigured routing.

### Flow Protocols Explained

**NetFlow** was developed by Cisco and exports aggregated flow records from network devices. Version 5 supports IPv4 only; version 9 and IPFIX support IPv6, MPLS, and custom field definitions. **sFlow** takes a different approach — it samples packets at a configurable rate (e.g., 1 in 1000), making it more suitable for high-speed links where full flow export would overwhelm the collector. **IPFIX** (RFC 7011) is the IETF standard that extends NetFlow v9 with extensible field definitions and is supported by most modern networking equipment.

### Self-Hosting vs Managed Flow Solutions

Commercial flow analysis platforms (SolarWinds NTA, Plixer Scrutinizer, ManageEngine NetFlow Analyzer) offer turnkey dashboards but require expensive licenses and send your network metadata to vendor cloud services. Self-hosted flow collection keeps all data on your infrastructure, supports unlimited data retention, and integrates with your existing monitoring stack (Prometheus, Grafana, Elasticsearch). The tools covered in this article — GoFlow2, softflowd, and nfdump — represent the full flow collection pipeline from capture to analysis.

## Building a Complete Flow Collection Architecture

A production flow monitoring system typically combines these tools:

1. **softflowd** runs on each router, switch, or server to capture local traffic and export NetFlow records
2. **GoFlow2** acts as the central collector, ingesting flows from dozens of probes, converting to Protobuf, and forwarding to Kafka
3. **nfdump** processes stored flow files for historical analysis, reporting, and security investigations

```
[Router A] ──NetFlow──┐
[Router B] ──NetFlow──┼──► [GoFlow2] ──Kafka──► [Analytics Pipeline]
[Server C] ──sFlow───┘        │
                        [nfcapd] ──► [Flow Files] ──► [nfdump queries]
```

This architecture gives you real-time flow ingestion (GoFlow2), distributed packet capture (softflowd), and offline analysis capabilities (nfdump).

For related network monitoring topics, see our [network flow analysis with pmacct, nfdump, and fprobe](../2026-05-15-self-hosted-network-flow-analysis-pmacct-nfdump-f/) and [network diagnostics with fping, mtr, and nmap](../2026-05-15-self-hosted-network-diagnostics-fping-vs-mtr-vs-n/).

## FAQ

### What is the difference between NetFlow, sFlow, and IPFIX?

**NetFlow** (Cisco proprietary, now v5/v9) exports flow records based on traffic observed at a network interface. **sFlow** (standardized, v5) uses packet sampling — it captures a statistical sample of packets rather than every flow, making it more scalable for high-speed links. **IPFIX** (IETF RFC 7011) is the standardized version of NetFlow v9, supporting extensible field definitions. GoFlow2 supports all three; softflowd exports NetFlow v9 and IPFIX; nfdump collects and processes all three.

### Can softflowd run on production routers?

Yes. softflowd has a minimal resource footprint (a few MB of RAM, negligible CPU) and is commonly deployed on OpenWRT routers, pfSense firewalls, and Linux-based network appliances. However, on very high-throughput links (>1 Gbps), sampling-based approaches like sFlow may be more efficient than full packet capture.

### How much disk space does nfdump require?

Flow data is extremely compact compared to full packet captures. A typical enterprise network generates 100 MB to 1 GB of nfdump data per day, depending on traffic volume and flow timeout settings. With compression enabled (`-w` flag), storage requirements are reduced by 30-50%. A 30-day retention policy typically requires 3-30 GB of disk space.

### Is GoFlow2 production-ready for large-scale deployments?

GoFlow2 is used in production by several ISPs and cloud providers. Its goroutine-based architecture handles hundreds of thousands of flow records per second. The key to scaling is pairing it with a robust downstream pipeline — Kafka for buffering, and a time-series database or data lake for storage. The Prometheus metrics endpoint enables monitoring collector health in real time.

### How do I troubleshoot missing flow data?

Common causes include: (1) **Firewall rules** blocking UDP ports 2055/6343 — verify with `tcpdump -i any udp port 2055`. (2) **Probe misconfiguration** — ensure softflowd or your router is pointing to the correct collector IP and port. (3) **Version mismatch** — NetFlow v5 uses a different packet format than v9/IPFIX; verify your collector supports the protocol version. (4) **Sampling rate** — if using sFlow, a high sampling ratio (e.g., 1:10000) means you'll only see 0.01% of traffic.

### Can I use these tools for security monitoring?

Absolutely. Flow data is a cornerstone of network security operations. nfdump queries can detect port scanning (many unique destination ports from a single source), DDoS attacks (sudden traffic volume spikes), data exfiltration (unusual outbound traffic volumes), and command-and-control communication (periodic connections to known-bad IPs). Combined with threat intelligence feeds, flow analysis provides network visibility without the privacy concerns of full packet capture.


<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Network Flow Collectors: GoFlow2 vs softflowd vs nfdump",
  "description": "Compare three open-source network flow tools: GoFlow2 (high-performance collector), softflowd (flow exporter probe), and nfdump (NetFlow processing toolkit). Includes Docker configs and query examples.",
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

