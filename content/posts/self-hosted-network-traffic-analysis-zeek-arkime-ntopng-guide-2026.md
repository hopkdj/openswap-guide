---
title: "Best Self-Hosted Network Traffic Analysis Tools 2026: Zeek vs Arkime vs ntopng"
date: 2026-04-16
tags: ["comparison", "guide", "self-hosted", "security", "networking", "monitoring"]
draft: false
description: "A comprehensive guide to self-hosted network traffic analysis and packet capture in 2026. Compare Zeek, Arkime, and ntopng with Docker setup instructions, feature breakdowns, and real-world deployment advice."
---

Network visibility is the foundation of effective infrastructure management. Whether you are diagnosing a stubborn latency issue, investigating a potential intrusion, auditing data flows for compliance, or simply understanding what traverses your network, a self-hosted traffic analysis platform gives you full access to the raw data without shipping packets to a third-party cloud.

In 2026, three open-source projects dominate this space, each with a distinct philosophy: **Zeek** (formerly Bro) for deep protocol analysis and scripting, **Arkime** (formerly Moloch) for full packet capture and search, and **ntopng** for real-time flow monitoring and visualization. This guide examines all three, provides production-ready Docker deployment instructions, and helps you choose the right tool — or combination of tools — for your environment.

## Why Self-Host Network Traffic Analysis

Running your own traffic analysis infrastructure instead of relying on managed or cloud-based monitoring services delivers several concrete advantages:

**Complete data sovereignty.** Every packet, flow record, and log stays on your hardware. For organizations in regulated industries (finance, healthcare, defense), or anyone handling sensitive customer data, this is often a non-negotiable compliance requirement. You control retention policies, encryption at rest, and access controls.

**Unlimited data retention.** Cloud traffic analysis services charge by volume ingested and retention period. With self-hosted storage, you decide how long to keep data — days, months, or years — limited only by disk capacity. A 4 TB drive can store weeks of flow data or days of full packet capture on a busy network.

**Deep customization.** Self-hosted platforms can be tuned to your exact needs: custom Zeek scripts for proprietary protocols, Arkime fields for internal application metadata, or ntopng plugins for vendor-specific telemetry. Cloud services rarely offer this level of flexibility.

**Cost efficiency at scale.** A dedicated analysis server with a 10 Gbps NIC, 64 GB RAM, and 8 TB of storage costs roughly $1,500–2,500 in hardware and handles traffic from hundreds of hosts. Compare that to per-host, per-gigabyte pricing from cloud alternatives during peak investigation periods.

**Real-time local processing.** No need to ship raw data over the WAN to a remote collector. SPAN port traffic or network TAP feeds go directly to your analysis server, enabling sub-second alerting and investigation even on high-throughput links.

**No vendor dependency.** Your analysis platform, detection rules, and historical data belong to you. If you need to migrate, you take the data — not a subset curated by the vendor.

---

## Zeek: The Protocol-Aware Network Security Monitor

[Zeek](https://zeek.org) is the most widely deployed open-source network analysis framework. Originally developed at the International Computer Science Institute (ICSI) and later maintained by the Corelight team before becoming a community-governed project under the Linux Foundation, Zeek occupies a unique niche: it does not just capture packets — it understands protocols.

### How Zeek Works

Zeek sits on a network SPAN port or TAP and inspects traffic in real time. Instead of storing raw packets, it generates structured logs — one line per event — that describe what it observed:

| Log File | Content |
|----------|---------|
| `conn.log` | Every connection (TCP, UDP, ICMP) with duration, bytes, and flags |
| `http.log` | HTTP requests and responses with URLs, status codes, user agents |
| `dns.log` | DNS queries and responses |
| `ssl.log` | TLS handshakes, certificate details, cipher suites |
| `files.log` | Files extracted from traffic (with MIME type, SHA256) |
| `notice.log` | Security-relevant events flagged by Zeek's detection scripts |

This log-centric approach makes Zeek extremely storage-efficient. A busy 1 Gbps link might generate 5–15 GB of Zeek logs per day, compared to hundreds of gigabytes for raw packet capture.

### Architecture

Zeek's architecture is modular:

1. **Packet capture layer** — uses libpcap or AF_PACKET for high-speed capture
2. **Protocol analyzers** — built-in dissectors for 50+ protocols (HTTP, DNS, SSH, SMTP, TLS, DHCP, Kerberos, RDP, and more)
3. **Event engine** — converts protocol events into Zeek Script callbacks
4. **Zeek Script (Zeek Language)** — a domain-specific language for writing custom detection logic
5. **Logging framework** — outputs structured logs to files, Elasticsearch, Kafka, or stdout

### Docker Deployment

Here is a production-ready Docker Compose setup for Zeek with Elasticsearch output:

```yaml
# docker-compose-zeek.yml
services:
  zeek:
    image: ghcr.io/corelight/zeek:6.1
    container_name: zeek
    network_mode: host
    restart: unless-stopped
    cap_add:
      - NET_RAW
      - NET_ADMIN
    environment:
      - PCAP_IFACE=eth0
      - ZEEK_NODE=standalone
      - LOG_ROTATION_INTERVAL=3600
    volumes:
      - ./zeek-config:/usr/local/zeek/etc
      - ./zeek-scripts:/usr/local/zeek/share/zeek/site
      - zeek-logs:/usr/local/zeek/logs
    deploy:
      resources:
        limits:
          cpus: "4"
          memory: 8g

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.14.0
    container_name: zeek-elasticsearch
    restart: unless-stopped
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms2g -Xmx2g
    volumes:
      - es-data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"

  kibana:
    image: docker.elastic.co/kibana/kibana:8.14.0
    container_name: zeek-kibana
    restart: unless-stopped
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch

volumes:
  zeek-logs:
  es-data:
```

### Custom Detection Script Example

One of Zeek's greatest strengths is the ability to write custom detection logic. Here is a practical example that detects cleartext password transmissions over HTTP:

```zeek
# site/detect-cleartext-password.zeek

module CleartextPassword;

export {
    redef enum Notice::Type += {
        Cleartext_Password_In_HTTP
    };
}

event http_header(c: connection, is_orig: bool, name: string, value: string) {
    if (is_orig && name == "Authorization") {
        if ("Basic " in value) {
            NOTICE([$note=Cleartext_Password_In_HTTP,
                    $conn=c,
                    $msg="Cleartext Basic auth detected",
                    $sub=value]);
        }
    }
}
```

This script logs a notice every time an HTTP Basic Authentication header is observed — valuable for identifying legacy applications still transmitting credentials in cleartext.

### When to Use Zeek

Zeek excels when you need:
- **Protocol-level visibility** — understanding what protocols are running, not just that traffic exists
- **Custom detection logic** — writing rules for proprietary or internal protocols
- **Forensic investigation** — structured logs make it easy to search for specific events across days of traffic
- **Compliance reporting** — detailed connection and file logs satisfy audit requirements
- **Threat detection** — Zeek's built-in and community scripts catch known attack patterns, C2 beacons, and data exfiltration

Zeek does not store raw packets. If you need the actual payload data, pair Zeek with Arkime or a dedicated packet capture system.

---

## Arkime: Full Packet Capture and Search

[Arkime](https://arkime.com), formerly known as Moloch, takes a fundamentally different approach: it captures and indexes every packet, then provides a web interface to search and analyze them. Developed initially by AOL and now maintained as an open-source project, Arkime is the tool you reach for when you need the definitive answer to "what exactly was in that packet?"

### How Arkime Works

Arkime operates in two phases:

1. **Capture** — the `arkime-capture` process reads packets from a SPAN port, stores them in PCAP format on disk, and extracts session metadata (source/destination IPs, ports, protocol, byte counts, timestamps)
2. **Viewer** — the `arkime-viewer` web interface lets you search sessions, filter by any field, and download individual PCAP files or packet payloads

Unlike Zeek, Arkime does not interpret protocols. It stores raw bytes. This means it can answer questions Zeek cannot — such as "what was the exact content of this file transfer?" or "show me every packet from this IP between 14:00 and 14:05."

### Architecture

Arkime's architecture is designed for scale:

| Component | Role |
|-----------|------|
| `arkime-capture` | Packet capture and PCAP storage; one per monitored interface |
| Elasticsearch | Session metadata index; stores parsed fields for fast search |
| `arkime-viewer` | Web UI for search, session drill-down, and PCAP export |
| S3-compatible storage | Optional backend for long-term PCAP storage |

A typical deployment runs one capture node per network segment, all writing to a shared Elasticsearch cluster and optional S3 bucket.

### Docker Deployment

Here is a single-node Arkime deployment using Docker Compose:

```yaml
# docker-compose-arkime.yml
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.14.0
    container_name: arkime-es
    restart: unless-stopped
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms4g -Xmx4g
    volumes:
      - es-data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"

  arkime:
    image: ocsig/arkime:7.0.0
    container_name: arkime
    restart: unless-stopped
    network_mode: host
    cap_add:
      - NET_RAW
      - NET_ADMIN
    environment:
      - ARKIME_ELASTICSEARCH=http://localhost:9200
      - ARKIME_INTERFACE=eth0
      - ARKIME_VIEWER_USER=admin
      - ARKIME_VIEWER_PASSWORD=change-me-in-production
      - ARKIME_SECRET=aes-256-cbc-secret-key-32
    volumes:
      - arkime-pcap:/data/pcap
      - arkime-config:/data/config
    ports:
      - "8005:8005"
    depends_on:
      - elasticsearch
    deploy:
      resources:
        limits:
          cpus: "6"
          memory: 12g

volumes:
  es-data:
  arkime-pcap:
  arkime-config:
```

After starting the containers, initialize the Elasticsearch database:

```bash
docker exec arkime /opt/arkime/db/db.pl http://localhost:9200 init
```

Then navigate to `http://<server-ip>:8005` and log in with the configured credentials.

### Practical Search Examples

The Arkime viewer provides a powerful expression language for filtering sessions:

```
# Find all HTTP sessions to a specific domain
protocols == http && host == "suspicious-domain.example"

# Find large file transfers (> 10 MB) from internal network
ip.src == 10.0.0.0/8 && bytes > 10000000

# Find DNS queries for known bad TLDs
protocols == dns && dns.host.tokens == *.xyz,*.top,*.tk

# Find sessions with specific TLS certificate subjects
protocols == tls && tls.cert.subject == "*malicious*"
```

Arkime also supports SPI (Session-based Packet Inspection), meaning you can search across packet payloads — for example, finding every session containing a specific string or file hash.

### When to Use Arkime

Arkime is the right choice when you need:
- **Full packet capture** — every byte, available on demand
- **Incident response** — downloading PCAPs for forensic analysis
- **Historical investigation** — going back weeks or months to find specific sessions
- **Legal discovery** — providing exact packet evidence for investigations
- **Multi-site deployment** — capturing traffic across many network segments with centralized search

Arkime is storage-intensive. A 1 Gbps link at 50% utilization generates roughly 200 GB of PCAP per day. Plan storage accordingly, or use S3-backed cold storage for older captures.

---

## ntopng: Real-Time Flow Monitoring and Visualization

[ntopng](https://www.ntop.org/products/traffic-analysis/ntop/) takes yet another approach: instead of protocol analysis or packet capture, it focuses on flow-level monitoring with rich, real-time visualization. Built by the ntop project, ntopng uses nDPI (a deep packet inspection library with 300+ protocol signatures) to classify traffic and presents it through a polished web dashboard.

### How ntopng Works

ntopng operates primarily on flow data — aggregated summaries of network conversations — rather than individual packets or protocol events. Each flow record contains:

- Source and destination IP addresses
- Source and destination ports
- Protocol and application identification (via nDPI)
- Byte and packet counts
- Duration and timestamps
- AS numbers and geolocation data
- Risk scores for suspicious flows

The web interface provides real-time dashboards, historical charts, host-to-host flow maps, and alerting — all designed for quick situational awareness.

### Architecture

ntopng's architecture is straightforward:

| Component | Role |
|-----------|------|
| `ntopng` | Main daemon — captures packets, extracts flows, serves web UI |
| Redis | Flow state storage and caching |
| nDPI library | Deep packet inspection for 300+ application protocols |
| InfluxDB (optional) | Long-term flow history storage |

ntopng is available in multiple editions: Community (free, single interface), Professional (multiple interfaces, historical data), and Enterprise (distributed monitoring, custom alerts). The Community edition is sufficient for most self-hosted deployments.

### Docker Deployment

Here is a Docker Compose setup for ntopng with Redis:

```yaml
# docker-compose-ntopng.yml
services:
  redis:
    image: redis:7-alpine
    container_name: ntopng-redis
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data

  ntopng:
    image: ntop/ntopng:stable
    container_name: ntopng
    restart: unless-stopped
    network_mode: host
    cap_add:
      - NET_RAW
      - NET_ADMIN
    command:
      - --community
      - -i=eth0
      - -r=redis://127.0.0.1:6379/0
      - --local-networks=10.0.0.0/8,172.16.0.0/12,192.168.0.0/16
      - --dns-mode=1
    volumes:
      - ntopng-data:/var/lib/ntopng
    ports:
      - "3000:3000"
    depends_on:
      - redis
    deploy:
      resources:
        limits:
          cpus: "4"
          memory: 6g

volumes:
  redis-data:
  ntopng-data:
```

After starting, access the web UI at `http://<server-ip>:3000`. Default credentials are `admin/admin` — change these immediately.

### Key Dashboard Features

ntopng's web interface provides several views that are particularly useful:

- **Dashboard** — real-time throughput, top talkers, protocol distribution, and alert summary
- **Hosts** — per-host breakdown of traffic, applications, and risk scores
- **Flows** — active and historical flow records with application classification
- **Traffic** — time-series charts showing bandwidth usage by protocol, host, or AS
- **Alerts** — configurable alerts for anomalies (DNS tunneling, unusual ports, traffic spikes)
- **Geolocation** — world map showing traffic destinations by country

### When to Use ntopng

ntopng excels when you need:
- **Real-time visibility** — live dashboards showing what is happening on the network right now
- **Bandwidth monitoring** — understanding who is using the most bandwidth and for what
- **Application identification** — knowing that traffic is Zoom, not just TCP port 443
- **Quick anomaly detection** — spotting unusual traffic patterns or bandwidth spikes
- **Executive reporting** — polished dashboards suitable for management review

ntopng does not store raw packets or generate detailed protocol logs like Zeek. It is a monitoring and visualization tool, not a forensic or deep analysis platform.

---

## Head-to-Head Comparison

| Feature | Zeek | Arkime | ntopng |
|---------|------|--------|--------|
| **Primary Focus** | Protocol analysis & detection | Full packet capture & search | Flow monitoring & visualization |
| **Raw Packet Storage** | No | Yes (PCAP on disk) | No |
| **Structured Logs** | Yes (conn, http, dns, ssl, files, etc.) | Session metadata in Elasticsearch | Flow records in Redis |
| **Protocol Detection** | 50+ built-in analyzers | None (stores raw bytes) | 300+ via nDPI |
| **Search Interface** | Logs + external tools (Kibana) | Built-in web viewer | Built-in web dashboard |
| **Real-Time Alerts** | Yes (Zeek Script notices) | No (post-capture search) | Yes (configurable alerts) |
| **Storage Requirements** | Low (5–15 GB/day per Gbps) | Very high (200+ GB/day per Gbps) | Low–medium (depends on retention) |
| **Custom Detection** | Zeek Script (powerful DSL) | Filter expressions | Alert rules |
| **Forensic Capability** | Medium (structured events) | High (raw packet replay) | Low (flow summaries only) |
| **Multi-Site Deployment** | Yes (distributed nodes) | Yes (capture nodes + shared ES) | Yes (ntopng instances) |
| **Learning Curve** | Steep (Zeek Script, log analysis) | Moderate (web UI, search syntax) | Gentle (point-and-click dashboards) |
| **License** | BSD | Apache 2.0 | GPL v3 (Community) |
| **Best Paired With** | Elasticsearch, Elasticsearch SIEM | Arkime Viewer, Wireshark | InfluxDB, Grafana |

## Choosing the Right Tool

The decision is not about which tool is "best" — it is about which tool solves your specific problem:

**Use Zeek if** you are building a security monitoring pipeline, need protocol-level visibility, want to write custom detection rules, or must generate structured logs for compliance reporting. Zeek is the tool of choice for SOC analysts, security engineers, and researchers.

**Use Arkime if** you need the ability to go back in time and examine exact packet contents. Incident response teams, forensic investigators, and network administrators who frequently answer "what was in that traffic?" will find Arkime indispensable. Budget for significant storage capacity.

**Use ntopng if** you need real-time network visibility with minimal setup. Network operations teams, IT managers, and anyone who needs to answer "who is using all the bandwidth?" or "what applications are running on my network?" will benefit from ntopng's polished dashboards.

**Use Zeek + Arkime together** if you want the best of both worlds: Zeek's structured protocol logs for detection and reporting, backed by Arkime's full packet capture for forensic investigation. This is the architecture used by many mature security operations centers.

**Use Zeek + ntopng together** if you need both deep protocol analysis and real-time operational visibility. Zeek feeds your detection pipeline while ntopng provides the live dashboard for the NOC.

---

## Running All Three: A Unified Stack

For organizations that need comprehensive network visibility, running all three tools on a single server is entirely feasible. Here is the resource planning:

```
Recommended hardware for 1 Gbps link analysis:
┌──────────────────────────────────────────┐
│ CPU:     16 cores (4 per tool minimum)   │
│ RAM:     32 GB                           │
│ Storage: 8 TB SSD (Arkime PCAP)          │
│          500 GB SSD (Elasticsearch)      │
│          100 GB SSD (Redis, Zeek logs)   │
│ Network: 10 Gbps NIC (SPAN/TAP input)    │
└──────────────────────────────────────────┘
```

The combined Docker Compose stack:

```yaml
# docker-compose-network-analysis.yml
services:
  # ── Zeek Stack ──
  zeek:
    image: ghcr.io/corelight/zeek:6.1
    network_mode: host
    cap_add: [NET_RAW, NET_ADMIN]
    environment:
      - PCAP_IFACE=eth0
      - ZEEK_NODE=standalone
    volumes:
      - ./zeek-config:/usr/local/zeek/etc
      - ./zeek-scripts:/usr/local/zeek/share/zeek/site
      - zeek-logs:/usr/local/zeek/logs

  # ── Arkime Stack ──
  arkime-es:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.14.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms4g -Xmx4g
    volumes:
      - es-data:/usr/share/elasticsearch/data

  arkime:
    image: ocsig/arkime:7.0.0
    network_mode: host
    cap_add: [NET_RAW, NET_ADMIN]
    environment:
      - ARKIME_ELASTICSEARCH=http://localhost:9200
      - ARKIME_INTERFACE=eth0
    volumes:
      - arkime-pcap:/data/pcap
    ports:
      - "8005:8005"
    depends_on: [arkime-es]

  # ── ntopng Stack ──
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data

  ntopng:
    image: ntop/ntopng:stable
    network_mode: host
    cap_add: [NET_RAW, NET_ADMIN]
    command:
      - --community
      - -i=eth0
      - -r=redis://127.0.0.1:6379/0
      - --local-networks=10.0.0.0/8,172.16.0.0/12,192.168.0.0/16
    ports:
      - "3000:3000"
    depends_on: [redis]

volumes:
  zeek-logs:
  es-data:
  arkime-pcap:
  redis-data:
```

Start the stack with `docker compose -f docker-compose-network-analysis.yml up -d`, then initialize Arkime's database as described above. You will have:

- Zeek logs at `/usr/local/zeek/logs/current/` (or forwarded to your SIEM)
- Arkime web UI at `http://<server>:8005`
- ntopng dashboard at `http://<server>:3000`

## Final Recommendations

For most self-hosted deployments, start with **ntopng** for immediate visibility — it takes five minutes to deploy and provides actionable insights from day one. Then add **Zeek** when you need deeper protocol analysis or custom detection rules. Add **Arkime** when incident response requires the ability to examine raw packet contents.

All three tools are production-proven, actively maintained, and available under permissive open-source licenses. They form the backbone of network visibility for organizations ranging from small homelabs to Fortune 500 security operations centers. The only question is not whether you need network traffic analysis — it is which tools best fit your operational requirements and available hardware.
