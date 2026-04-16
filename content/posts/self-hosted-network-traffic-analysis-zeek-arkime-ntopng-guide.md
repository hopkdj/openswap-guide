---
title: "Self-Hosted Network Traffic Analysis: Zeek vs Arkime vs Ntopng Complete Guide 2026"
date: 2026-04-16
tags: ["comparison", "guide", "self-hosted", "privacy", "security", "monitoring"]
draft: false
description: "Complete guide to self-hosted network traffic analysis with open-source tools Zeek, Arkime, and Ntopng. Installation, configuration, and comparison for 2026."
---

When you rely on cloud-based network monitoring services, you hand over your most sensitive infrastructure data — every connection, every protocol, every anomaly — to a third party. For organizations handling compliance requirements (HIPAA, PCI-DSS, SOC 2) or anyone who values operational privacy, self-hosted network traffic analysis isn't just an option, it's a necessity.

Running your own network analysis stack means full visibility into every packet on your infrastructure without data leaving your premises. You control retention policies, detection rules, and access. And with modern open-source tools, you don't need a dedicated security team to get enterprise-grade network visibility.

This guide covers the three most capable self-hosted network traffic analysis platforms available in 2026: **Zeek**, **Arkime** (formerly Moloch), and **Ntopng**. Each takes a fundamentally different approach to network visibility, and understanding those differences is key to building the right stack for your environment.

## Why Self-Host Network Traffic Analysis

Cloud network monitoring platforms like Datadog Network Monitoring, Cisco Umbrella, or ExtraHop charge per-flow pricing models that become prohibitively expensive at scale. A mid-sized infrastructure generating 10,000 flows per second can easily incur thousands of dollars monthly in network telemetry costs alone.

Beyond cost, self-hosting network analysis gives you:

- **Full packet capture** — Cloud providers typically only store flow metadata (NetFlow/IPFIX). Self-hosted systems can retain actual packet data for forensic investigation.
- **No data exfiltration** — Sensitive internal traffic patterns, DNS queries, and encrypted TLS metadata never leave your network.
- **Custom detection logic** — Write bespoke Zeek scripts or Arkime queries tuned to your specific infrastructure rather than relying on vendor-defined rules.
- **Unlimited retention** — Store packet captures and logs as long as your storage budget allows, with no artificial caps from SaaS providers.
- **Compliance alignment** — Meet regulatory requirements that mandate on-premises data processing and storage.

## Zeek: The Network Security Monitoring Engine

Zeek (formerly Bro) is not a traditional IDS — it's a network analysis framework that transforms raw packet captures into structured, high-level logs. Rather than simply alerting on known attack signatures, Zeek builds a comprehensive semantic model of everything happening on your network.

Every TCP connection, DNS query, HTTP request, SSL handshake, and file transfer gets extracted into structured logs (TSV or JSON). This makes Zeek ideal for both real-time monitoring and retrospective forensic analysis.

### Zeek Architecture

Zeek operates through a modular event engine:

1. **Packet Capture** — Uses libpcap to capture raw packets from a network interface
2. **Protocol Analyzers** — Dozens of built-in analyzers parse protocols (HTTP, DNS, SMTP, SSH, TLS, DHCP, and 40+ more)
3. **Event Engine** — Converts parsed protocol data into discrete events (e.g., `http_request`, `dns_request`, `ssl_established`)
4. **Script Interpreter** — A purpose-built scripting language reacts to events, generating logs or triggering alerts
5. **Log Writer** — Outputs structured logs to files, Elasticsearch, or other sinks

### Installing Zeek via Docker

The fastest way to get Zeek running is through the official Docker image:

```bash
# Pull the official Zeek image
docker pull ghcr.io/corelight/zeek:latest

# Run Zeek in network sniffing mode on eth0
docker run -d \
  --name zeek \
  --network host \
  --cap-add NET_ADMIN \
  --cap-add NET_RAW \
  -v /opt/zeek/logs:/opt/zeek/logs \
  -v /opt/zeek/config:/opt/zeek/config \
  ghcr.io/corelight/zeek:latest \
  zeek -i eth0 -C local
```

For a production deployment, you'll want a proper `docker-compose.yml`:

```yaml
version: "3.8"

services:
  zeek:
    image: ghcr.io/corelight/zeek:latest
    container_name: zeek
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - /opt/zeek/logs:/opt/zeek/logs
      - /opt/zeek/config:/opt/zeek/config
      - /opt/zeek/spool:/opt/zeek/spool
    restart: unless-stopped
    environment:
      - ZEEK_INTERFACE=eth0
      - ZEEK_LOG_FORMAT=json
    command: >
      zeek -i eth0
        -C
        local
        /opt/zeek/config/custom.zeek

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.12.0
    container_name: zeek-elasticsearch
    environment:
      - discovery.type=single-node
      - ES_JAVA_OPTS=-Xms2g -Xmx2g
      - xpack.security.enabled=false
    volumes:
      - zeek-es-data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"
    restart: unless-stopped

  kibana:
    image: docker.elastic.co/kibana/kibana:8.12.0
    container_name: zeek-kibana
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch
    restart: unless-stopped

volumes:
  zeek-es-data:
```

### Core Zeek Log Files

Once Zeek is running, it generates a structured log file for each protocol:

| Log File | Content |
|----------|---------|
| `conn.log` | Every TCP/UDP/ICMP connection with duration, bytes, and flags |
| `dns.log` | All DNS queries and responses including resolved IPs |
| `http.log` | HTTP requests with method, URI, status code, user-agent |
| `ssl.log` | TLS handshakes with certificate details, cipher suites, SNI |
| `files.log` | Every file transferred across the network with MIME type and hash |
| `notice.log` | Security-relevant events (scan detection, policy violations) |
| `weird.log` | Protocol anomalies and unexpected network behavior |

### Writing Custom Zeek Scripts

Zeek's scripting language lets you define custom detection logic. Here's a script that detects potential data exfiltration by monitoring unusually large outbound transfers:

```zeek
# /opt/zeek/config/exfil-detection.zeek

module ExfilDetection;

export {
    # Threshold: alert on connections exceeding 100 MB outbound
    const exfil_threshold = 100 * 1024 * 1024 &redef;
}

event connection_state_remove(c: connection)
    {
    # Check if outbound bytes exceed threshold
    if ( c$id$resp_h in 10.0.0.0/8 )  # Only flag internal→external
        return;

    if ( c$orig_ip_bytes > exfil_threshold )
        {
        NOTICE([$note = Exfil::Large_Transfer,
                $msg = fmt("Large outbound transfer: %s → %s (%s bytes)",
                          c$id$orig_h, c$id$resp_h, c$orig_ip_bytes),
                $conn = c,
                $sub = "data_exfiltration"]);
        }
    }
```

### Zeek Cluster Mode for High Traffic

For environments exceeding 1 Gbps of traffic, Zeek supports a clustered deployment:

```ini
# /opt/zeek/config/node.cfg

[logger]
type=logger
host=localhost

[manager]
type=manager
host=localhost

[proxy-1]
type=proxy
host=localhost

[worker-1]
type=worker
host=localhost
interface=eth0
lb_method=pf_ring
lb_procs=4
pin_cpus=0,1,2,3

[worker-2]
type=worker
host=localhost
interface=eth1
lb_method=pf_ring
lb_procs=4
pin_cpus=4,5,6,7
```

## Arkime: Full Packet Capture and Search

Arkime takes a different approach — it captures and indexes every single packet, then provides a web interface for searching, analyzing, and downloading PCAP data. Think of it as a search engine for your network traffic.

While Zeek extracts high-level semantic data from packets, Arkime preserves the raw packets themselves. This means you can reconstruct exact conversations, download forensic PCAP files, and replay traffic — capabilities that log-only systems cannot provide.

### Arkime Architecture

Arkime consists of three components:

1. **Capture** — A packet capture daemon that stores raw PCAP data on disk and extracts session metadata
2. **Viewer** — A web application for searching, viewing, and analyzing captured sessions
3. **Elasticsearch** — The indexing backend for session metadata (Arkime does not store packet data in ES)

### Installing Arkime

Arkime provides official packages for major distributions. Here's the installation process:

```bash
# Download the latest Arkime package
wget https://github.com/arkime/arkime/releases/download/v5.3.0/arkime_5.3.0-1_amd64.deb
sudo dpkg -i arkime_5.3.0-1_amd64.deb

# Run the configuration wizard
sudo /opt/arkime/bin/Configure
```

The Configure script will prompt you for:
- Elasticsearch URL
- S3 or local storage for PCAP files
- Password hash for the web interface
- Network interface to capture on

### Docker Deployment of Arkime

```yaml
version: "3.8"

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.12.0
    container_name: arkime-es
    environment:
      - discovery.type=single-node
      - ES_JAVA_OPTS=-Xms4g -Xmx4g
      - xpack.security.enabled=false
    volumes:
      - arkime-es-data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"
    ulimits:
      memlock:
        soft: -1
        hard: -1
      nofile:
        soft: 65536
        hard: 65536
    restart: unless-stopped

  arkime-capture:
    image: arkime/arkime:latest
    container_name: arkime-capture
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - arkime-pcap:/data
      - ./arkime-config:/opt/arkime/etc
    environment:
      - ARKIME_ELASTICSEARCH=http://elasticsearch:9200
      - ARKIME_INTERFACE=eth0
      - ARKIME_SECRET=your-secure-secret-key-change-me
    depends_on:
      - elasticsearch
    restart: unless-stopped

  arkime-viewer:
    image: arkime/arkime:latest
    container_name: arkime-viewer
    ports:
      - "8005:8005"
    volumes:
      - arkime-pcap:/data
      - ./arkime-config:/opt/arkime/etc
    environment:
      - ARKIME_ELASTICSEARCH=http://elasticsearch:9200
      - ARKIME_SECRET=your-secure-secret-key-change-me
      - ARKIME_VIEWER=true
    command: /opt/arkime/bin/node viewer.js
    depends_on:
      - elasticsearch
    restart: unless-stopped

volumes:
  arkime-es-data:
  arkime-pcap:
```

### Arkime Configuration Essentials

Key settings in `/opt/arkime/etc/config.ini`:

```ini
[default]
# Elasticsearch connection
elasticsearch=http://localhost:9200

# PCAP storage - rotate at 12GB per file
maxFileSizeG=12
pcapDir=/data/pcap

# Packet capture interface
interface=eth0

# BPF filter to exclude noise (adjust for your environment)
bpf=not port 9200 and not port 8005

# Authentication
passwordSecret=your-secret-here
userAuthType=digest

# Session timeout
tcpSaveTimeout=180
maxStreams=2000000

# SPI data retention (in days)
rotateIndex=daily
```

### Arkime Search and Analysis

The Arkime web interface (port 8005) provides powerful search capabilities:

- **Sessions View** — Filter by IP, port, protocol, bytes, duration
- **SPI View** — Search extracted protocol data (DNS names, HTTP URIs, TLS certs)
- **Hunts** — Run regex searches across raw packet payloads
- **Stats** — Visualize traffic patterns by protocol, country, or time

Example Arkime query syntax:

```
# All DNS queries from a specific subnet
dns.ip == 10.0.1.0/24

# HTTP requests containing "password" in URI
http.uri == *password*

# TLS connections to suspicious ports
tls.port == 443 && bytes > 1000000

# Connections from a specific country
country == RU || country == CN
```

## Ntopng: Real-Time Network Flow Analysis

Ntopng focuses on real-time network flow monitoring with a rich web interface. It uses nDPI (deep packet inspection) to classify traffic by application protocol and provides flow-level analytics without the storage overhead of full packet capture.

Where Arkime stores every packet and Zeek generates detailed protocol logs, Ntopng aggregates traffic into flows and provides real-time dashboards, historical charts, and alerting — making it the most operationally accessible of the three.

### Ntopng Architecture

1. **nProbe** (optional) — NetFlow/IPFIX probe that exports flow data from network devices
2. **ntopng** — Core daemon that receives flows, performs DPI, and serves the web interface
3. **Redis** — In-memory data store for active flows and real-time statistics
4. **n2disk** (optional) — Companion tool for packet-to-disk recording

### Installing Ntopng via Docker

```bash
# Pull ntopng image
docker pull ntop/ntopng:stable

# Run with Redis backend
docker run -d \
  --name ntopng \
  --network host \
  --cap-add NET_ADMIN \
  --cap-add NET_RAW \
  -v /opt/ntopng:/var/lib/ntopng \
  ntop/ntopng:stable \
  --interface eth0 \
  -w 3000 \
  --redis localhost:6379 \
  --local-networks "10.0.0.0/8,172.16.0.0/12,192.168.0.0/16" \
  -i "eth0" \
  -G "/var/lib/ntopng"
```

### Docker Compose for Production Ntopng

```yaml
version: "3.8"

services:
  redis:
    image: redis:7-alpine
    container_name: ntopng-redis
    command: redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru
    volumes:
      - ntopng-redis-data:/data
    restart: unless-stopped

  ntopng:
    image: ntop/ntopng:stable
    container_name: ntopng
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - /opt/ntopng:/var/lib/ntopng
    environment:
      - NTOPNG_INTERFACES=eth0
    command: >
      --interface eth0
      -w 3000
      --redis redis:6379
      --local-networks "10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
      --dns-mode 1
      --alerts-duration 86400
      --flow-track-mode 1
    depends_on:
      - redis
    restart: unless-stopped

  ntopng-data:
    image: ntop/ntopng-data:stable
    container_name: ntopng-data
    volumes:
      - /opt/ntopng:/var/lib/ntopng
    depends_on:
      - ntopng
    restart: unless-stopped

volumes:
  ntopng-redis-data:
```

### Ntopng Configuration File

For deployments beyond Docker, configure `/etc/ntopng/ntopng.conf`:

```
# Network interface to monitor
-i=eth0

# Web server port
-w=3000

# Local network subnets (comma-separated)
--local-networks=10.0.0.0/8,192.168.0.0/16

# Redis server
--redis=127.0.0.1:6379

# DNS resolution mode (0=disabled, 1=local, 2=decentralized)
--dns-mode=1

# Data directory
-G=/var/lib/ntopng

# User credentials file
--user=ntopng:$(cat /etc/ntopng/ntopng.pw)

# Enable alerts
--alerts-duration=86400

# Flow export (optional - send to n2disk or remote collector)
--nindex=1
```

### nDPI Protocol Classification

Ntopng's deep packet inspection engine (nDPI) classifies traffic into 300+ application protocols. This is its standout feature — you don't just see "TCP port 443," you see "Netflix," "Zoom," "Tor," or "Bitcoin":

```
# nDPI categories include:
- Streaming: Netflix, YouTube, Spotify, Twitch
- Communication: Zoom, Teams, Slack, WhatsApp, Telegram
- Cloud Storage: Dropbox, Google Drive, OneDrive, Box
- Social Media: Facebook, Twitter, Instagram, TikTok
- Development: GitHub, Docker Hub, npm, PyPI
- Malicious: Tor, I2P, Crypto miners, C2 frameworks
- P2P: BitTorrent, eMule, DirectConnect
```

## Head-to-Head Comparison

| Feature | Zeek | Arkime | Ntopng |
|---------|------|--------|--------|
| **Primary purpose** | Network analysis & security monitoring | Full packet capture & search | Real-time flow monitoring & DPI |
| **Packet capture** | Optional (via Zeek's pcap) | Yes, with searchable PCAP | Via n2disk companion |
| **Storage model** | Structured text/JSON logs | PCAP files + Elasticsearch metadata | Redis (active) + disk (historical) |
| **Protocol analyzers** | 40+ built-in analyzers | nDPI + custom dissectors | nDPI (300+ protocols) |
| **Search interface** | Command-line / Kibana | Built-in web UI (Sessions, SPI, Hunts) | Built-in web UI (dashboards, charts) |
| **Custom detection** | Zeek scripting language | Custom fields + Lua plugins | Custom alerts + Lua scripts |
| **Cluster support** | Yes (manager/worker/proxy) | Yes (multi-capture with shared ES) | Yes (via nProbe exporters) |
| **Resource usage** | Moderate (CPU-intensive for DPI) | High (disk-heavy for PCAP storage) | Low to moderate |
| **Best for** | Security analysts, forensic investigators | SOC teams, compliance, forensics | Network engineers, capacity planning |
| **Learning curve** | Steep (scripting language) | Moderate (query language) | Low (point-and-click UI) |
| **License** | BSD | Apache 2.0 | GPLv3 |

## Choosing the Right Tool

### Use Zeek when:

- You need structured, queryable logs for every network protocol
- You want to write custom detection logic for your specific environment
- You're building a security operations pipeline with SIEM integration
- You need to detect network anomalies that don't match known signatures
- Your team has the expertise to write and maintain Zeek scripts

Zeek's structured logs integrate beautifully with Elasticsearch, Splunk, or any SIEM. The `conn.log` alone is one of the most valuable data sources in security operations — it tells you every single connection that occurred on your network, with timing, volume, and protocol metadata.

### Use Arkime when:

- You need to retain actual packet data for forensic investigation
- Compliance requirements mandate packet-level evidence
- You need to search historical traffic with flexible query syntax
- You want the ability to download PCAP files for external analysis
- You need to answer "what exactly was in that packet?"

Arkime fills the gap between flow-level monitoring and full PCAP storage solutions. You can keep the raw packets for compliance or investigation while using Elasticsearch for fast metadata searches. The ability to hunt across raw packet payloads with regex makes Arkime invaluable for incident response.

### Use Ntopng when:

- You want immediate visibility into network traffic with zero configuration
- Application-level traffic classification (what apps are using bandwidth?) is your priority
- You need real-time dashboards for network capacity planning
- You want to identify bandwidth hogs and unauthorized applications
- You prefer a GUI over command-line tools

Ntopng excels at answering operational questions: "Why is the network slow?" "Which host is generating the most traffic?" "What applications are consuming bandwidth right now?" The nDPI classification means you see application names, not just port numbers.

## Combined Stack: Best of All Three

For maximum network visibility, many organizations deploy all three tools in complementary roles:

```yaml
# Complete network analysis stack
version: "3.8"

services:
  # Zeek: structured protocol logs
  zeek:
    image: ghcr.io/corelight/zeek:latest
    network_mode: host
    cap_add: [NET_ADMIN, NET_RAW]
    volumes:
      - /opt/zeek/logs:/opt/zeek/logs
    command: zeek -i eth0 -C local

  # Arkime: full packet capture
  arkime:
    image: arkime/arkime:latest
    network_mode: host
    cap_add: [NET_ADMIN, NET_RAW]
    volumes:
      - arkime-pcap:/data
    environment:
      - ARKIME_INTERFACE=eth0

  # Ntopng: real-time flow monitoring
  ntopng:
    image: ntop/ntopng:stable
    network_mode: host
    cap_add: [NET_ADMIN, NET_RAW]
    volumes:
      - /opt/ntopng:/var/lib/ntopng
    command: --interface eth0 -w 3000

  # Elasticsearch: shared index backend
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.12.0
    environment:
      - discovery.type=single-node
      - ES_JAVA_OPTS=-Xms4g -Xmx4g
    volumes:
      - es-data:/usr/share/elasticsearch/data

  # Kibana: unified dashboard
  kibana:
    image: docker.elastic.co/kibana/kibana:8.12.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

volumes:
  arkime-pcap:
  es-data:
```

In this architecture:
- **Zeek** feeds structured logs to Elasticsearch for SIEM integration
- **Arkime** retains raw PCAPs for forensic investigation
- **Ntopng** provides real-time operational dashboards for network engineers
- **Kibana** unifies Zeek logs and Arkime metadata in a single view

## Practical Deployment Tips

### Network Interface Selection

```bash
# List available interfaces
ip link show

# Put interface in promiscuous mode
sudo ip link set eth0 promisc on

# Verify promiscuous mode
ip link show eth0 | grep -i promisc

# For SPAN/mirror port configuration on your switch,
# ensure the interface receives copies of all traffic
```

### Storage Planning

```bash
# Estimate PCAP storage needs:
# 1 Gbps sustained traffic ≈ 450 GB per day (full packet capture)
# 100 Mbps sustained ≈ 45 GB per day
# Zeek logs ≈ 5-10 GB per day per 1 Gbps

# Set up log rotation for Zeek
cat >> /etc/logrotate.d/zeek << 'EOF'
/opt/zeek/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 zeek zeek
}
EOF
```

### Traffic Sampling for High-Speed Links

If you're monitoring 10 Gbps+ links and can't capture everything:

```zeek
# Zeek: sample 1 in 100 packets for conn.log
redef sample_rate = 100;

# Or use BPF to capture only specific traffic types
# Arkime config.ini:
# bpf=tcp or udp or icmp
```

### Alerts and Notifications

Configure Ntopng alerts for common security events:

```bash
# Via Ntopng REST API, set up alerts
curl -X POST http://localhost:3000/lua/rest/v2/manage/alerts/add_alert_config.lua \
  -d "alert_type=flow&alert_severity=warning&alert_condition=bytes>1000000000&alert_name=large_flow"

# Zeek notice framework for email alerts
# In local.zeek:
redef Notice::emailed_types += {
    Scan::Port_Scan,
    Scan::Address_Scan,
    ExfilDetection::Large_Transfer
};
```

## Conclusion

Zeek, Arkime, and Ntopng represent three complementary approaches to self-hosted network visibility. Zeek gives you semantic analysis and custom detection. Arkime gives you forensic-grade packet retention and search. Ntopng gives you real-time operational awareness with minimal setup.

The right choice depends on what questions you need to answer. If you need to know "what happened on my network last week," Zeek's structured logs are invaluable. If you need to prove "what exactly was in that suspicious packet," Arkime's PCAP search is essential. If you need to know "why is the network slow right now," Ntopng's real-time dashboards are the answer.

Deploying all three together — with shared Elasticsearch indexing — provides complete network visibility from real-time monitoring through forensic investigation, all self-hosted, all open-source, and fully under your control.
