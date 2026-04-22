---
title: "Best Self-Hosted DNS Monitoring Tools: dnstop vs Packetbeat vs Arkime 2026"
date: 2026-04-22
tags: ["comparison", "guide", "self-hosted", "dns", "monitoring", "security"]
draft: false
description: "Compare the best self-hosted DNS monitoring tools — dnstop, Packetbeat, and Arkime. Learn to track DNS queries, detect anomalies, and analyze DNS traffic with open-source solutions."
---

DNS is the backbone of every network, yet it remains one of the most overlooked vectors for security threats and performance issues. DNS tunneling, domain generation algorithms (DGAs), cache poisoning, and misconfigured resolvers can all go undetected without proper monitoring in place.

This guide compares three open-source DNS monitoring tools that cover the full spectrum — from lightweight terminal analysis to enterprise-grade packet capture: **dnstop**, **Packetbeat**, and **Arkime** (formerly Moloch). Whether you need a quick terminal view of live DNS queries or a full forensic search platform, there is a tool here for your use case.

## Why Monitor DNS Traffic?

DNS queries reveal everything about network behavior: what domains users visit, how often, from which clients, and with what response patterns. Monitoring DNS traffic helps you:

- **Detect DNS tunneling** — identify data exfiltration through encoded DNS queries
- **Spot DGA malware** — catch botnets using algorithmically generated domain names
- **Identify misconfigurations** — find NXDOMAIN storms from broken host files or stale records
- **Track performance** — measure query latency, response codes, and cache hit rates
- **Forensic analysis** — reconstruct historical DNS activity after a security incident
- **Compliance** — maintain audit logs of DNS resolution for regulatory requirements

Without DNS monitoring, you are essentially blind to one of the most active protocols on your network.

## Tool Overview

| Feature | dnstop | Packetbeat | Arkime (Moloch) |
|---|---|---|---|
| **Type** | Terminal DNS analyzer | Protocol shipper (Elastic) | Full packet capture |
| **Language** | C | Go | C |
| **GitHub Stars** | N/A (website) | 12,600+ | 7,350+ |
| **Last Updated** | 2024 (stable) | April 2026 | April 2026 |
| **Interface** | ncurses terminal | Kibana dashboards | Web UI with SPI view |
| **Real-time** | Yes (live) | Near real-time | Indexed search |
| **Historical** | No | Yes (via Elasticsearch) | Yes (via Elasticsearch/OpenSearch) |
| **Packet Capture** | No | No (metadata only) | Yes (full PCAP) |
| **Deployment** | Single binary | Daemon + Elasticsearch | Multi-node cluster |
| **DNS Protocol** | Queries only | Full DNS parsing | Full DNS + all protocols |
| **Learning Curve** | Low | Medium | High |
| **Best For** | Quick troubleshooting | Observability stack | Security forensics |

## dnstop — Lightweight Terminal DNS Analyzer

[dnstop](https://dns.measurement-factory.com/tools/dnstop/) is a libpcap-based terminal application that displays real-time DNS query statistics. Created by Duane Wessels of The Measurement Factory, it has been the go-to tool for quick DNS troubleshooting for over two decades.

### What It Does Well

dnstop listens on a network interface, parses DNS packets in real time, and presents interactive tables showing:

- Top queried domain names
- Top DNS query sources (clients)
- Top DNS response sources (servers)
- Query type distribution (A, AAAA, MX, PTR, etc.)
- Response code breakdown (NOERROR, NXDOMAIN, SERVFAIL)
- Opcode distribution

You press a key to switch between tables, and everything updates in real time.

### Installation

On Debian/Ubuntu:

```bash
sudo apt update
sudo apt install dnstop -y
```

On RHEL/CentOS/Fedora:

```bash
sudo dnf install dnstop -y
```

From source:

```bash
git clone https://github.com/DNS-OARC/dnstop.git
cd dnstop
autoreconf -fi
./configure
make
sudo make install
```

### Usage

```bash
# Monitor DNS on a specific interface
sudo dnstop eth0

# Monitor on port 53 specifically
sudo dnstop -p 53 eth0

# Read from a PCAP file
sudo dnstop -r capture.pcap
```

The interface is divided into three panels: query sources, query destinations, and query types. Press `1`, `2`, `3` to switch between views, `q` to quit.

### dnstop Docker Setup

Since dnstop is a simple binary, you can wrap it in a minimal Docker container:

```yaml
version: "3.8"
services:
  dnstop:
    image: alpine:latest
    container_name: dnstop
    network_mode: host
    cap_add:
      - NET_RAW
      - NET_ADMIN
    entrypoint: ["/bin/sh", "-c"]
    command: |
      apk add --no-cache dnstop libpcap
      dnstop eth0
    restart: unless-stopped
```

Run with `docker compose up -d` and attach to see the live terminal output:

```bash
docker exec -it dnstop /bin/sh
```

### Limitations

- No historical data — only shows what is happening right now
- No alerting or notification capability
- Single-machine only — cannot aggregate from multiple resolvers
- No web interface — requires SSH or terminal access
- Limited to DNS — does not monitor other protocols

dnstop excels as a **first-response troubleshooting tool**. When users report slow DNS or you suspect a resolver issue, dnstop gives you answers in seconds without any infrastructure setup.

## Packetbeat — DNS Protocol Shipper for the Elastic Stack

[Packetbeat](https://github.com/elastic/beats) is part of the Elastic Beats family — lightweight, single-purpose data shippers that send network protocol data to Elasticsearch or Logstash. Packetbeat understands over 20 application-layer protocols including DNS, HTTP, TLS, and PostgreSQL.

For DNS monitoring, Packetbeat parses every DNS request and response on the wire and sends structured JSON documents to Elasticsearch, where you can build dashboards, set alerts, and run historical queries.

### What It Does Well

- **Structured DNS fields** — each DNS query becomes a document with fields like `dns.question.name`, `dns.response.code`, `dns.answers`, and `dns.response.time`
- **Built-in Kibana dashboards** — the `packetbeat setup --dashboards` command deploys pre-built visualizations
- **Correlation** — correlate DNS queries with HTTP requests, database queries, and other protocols in a single timeline
- **Alerting** — use Elastic Alerting or Watcher to trigger on DNS anomalies
- **Scalable** — run on every host and ship to a central Elasticsearch cluster

### Installation

```bash
# Download and install
curl -L -O https://artifacts.elastic.co/downloads/beats/packetbeat/packetbeat-8.17.0-amd64.deb
sudo dpkg -i packetbeat-8.17.0-amd64.deb
```

Or use the Elastic APT repository:

```bash
curl -fsSL https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/elastic.gpg
echo "deb https://artifacts.elastic.co/packages/8.x/apt stable main" | sudo tee /etc/apt/sources.list.d/elastic-8.x.list
sudo apt update && sudo apt install packetbeat
```

### Configuration

Edit `/etc/packetbeat/packetbeat.yml` to enable DNS monitoring:

```yaml
packetbeat.protocols:
- type: dns
  ports: [53]
  include_authorities: true
  include_additionals: true

output.elasticsearch:
  hosts: ["http://elasticsearch:9200"]
  username: "elastic"
  password: "your-password"

# Optional: ship to Logstash instead
# output.logstash:
#   hosts: ["logstash:5044"]

setup.dashboards.enabled: true
setup.kibana:
  host: "http://kibana:5601"
```

Key DNS-specific settings:
- `include_authorities: true` — includes authority section records (useful for tracking NS delegation)
- `include_additionals: true` — includes EDNS0 and additional section data
- `ports: [53]` — monitors both UDP and TCP on port 53

### Packetbeat Docker Compose

```yaml
version: "3.8"
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.17.0
    container_name: elasticsearch
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms512m -Xmx512m
    ports:
      - "9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data

  kibana:
    image: docker.elastic.co/kibana/kibana:8.17.0
    container_name: kibana
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

  packetbeat:
    image: docker.elastic.co/beats/packetbeat:8.17.0
    container_name: packetbeat
    network_mode: host
    cap_add:
      - NET_RAW
      - NET_ADMIN
    volumes:
      - ./packetbeat.yml:/usr/share/packetbeat/packetbeat.yml:ro
    depends_on:
      - elasticsearch
    restart: unless-stopped

volumes:
  es_data:
```

Deploy with:

```bash
docker compose up -d
```

Then load the built-in dashboards:

```bash
docker exec packetbeat packetbeat setup --dashboards -E output.elasticsearch.hosts=["http://localhost:9200"]
```

Open Kibana at `http://localhost:5601` and navigate to **Dashboard → [Packetbeat] DNS Overview**.

### Querying DNS Data in Elasticsearch

Find top queried domains:

```json
GET packetbeat-*/_search
{
  "size": 0,
  "query": {
    "bool": {
      "must": [
        { "term": { "network.transport": "udp" }},
        { "exists": { "field": "dns.question.name" }}
      ]
    }
  },
  "aggs": {
    "top_domains": {
      "terms": {
        "field": "dns.question.name.keyword",
        "size": 20
      }
    }
  }
}
```

Detect NXDOMAIN spikes (potential DGA activity):

```json
GET packetbeat-*/_search
{
  "query": {
    "bool": {
      "must": [
        { "term": { "dns.response_code": "NXDOMAIN" }},
        { "range": { "@timestamp": { "gte": "now-1h" }}}
      ]
    }
  }
}
```

## Arkime (Moloch) — Full Packet Capture with DNS Forensics

[Arkime](https://github.com/arkime/arkime) (formerly Moloch) is a large-scale, open-source packet capture, indexing, and database system. Unlike dnstop (real-time only) and Packetbeat (metadata only), Arkime stores the **full packet data** along with a searchable SPI (Session Protocol Intelligence) database.

For DNS monitoring, this means you can not only see that a query happened, but you can also examine the actual DNS response payload, including every answer record, authority section, and additional record — at any point in time, going back months or years.

### What It Does Well

- **Full PCAP storage** — every packet is saved to disk and searchable
- **SPI database** — indexed metadata for fast session search across all protocols
- **DNS session details** — query name, type, response code, all answer records, TTL values
- **Web interface** — point-and-click search, PCAP download, timeline visualization
- **Multi-node clustering** — scale across dozens of capture nodes
- **Integration** — exports to Suricata, Zeek, and other security tools

### Installation

Arkime requires Elasticsearch or OpenSearch as its backend. Install on a capture host:

```bash
# Download the latest release
curl -L -O https://github.com/arkime/arkime/releases/download/v5.3.0/arkime_5.3.0-1_amd64.deb
sudo apt install ./arkime_5.3.0-1_amd64.deb

# Run the configuration wizard
sudo /data/arkime/bin/Configure
```

The Configure script guides you through:
1. Setting the Elasticsearch/OpenSearch URL
2. Creating the admin user and password
3. Selecting capture interfaces
4. Initializing the database

### Arkime Docker Compose

The official Arkime Docker image runs both the capture and viewer components:

```yaml
version: "3.8"
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.17.0
    container_name: arkime-es
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms1g -Xmx1g
    ports:
      - "9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data

  arkime:
    image: arkime/arkime:latest
    container_name: arkime-viewer
    network_mode: host
    cap_add:
      - NET_RAW
      - NET_ADMIN
    environment:
      - ARKIME_ELASTICSEARCH=http://localhost:9200
      - ARKIME_PASSWORD_SECRET=your-secret-password
      - ARKIME_AUTH_MODE=digest
    volumes:
      - pcap_storage:/data/arkime
      - ./arkime.ini:/data/arkime/etc/config.ini:ro
    ports:
      - "8005:8005"
    restart: unless-stopped

volumes:
  es_data:
  pcap_storage:
```

The `arkime.ini` configuration file:

```ini
[default]
elasticsearch=http://localhost:9200
passwordSecret=your-secret-password
viewerPort=8005
interface=eth0
freeSpaceG=10%
maxQueryRuns=20
```

After deploying:

```bash
docker compose up -d

# Create admin user
docker exec arkime-viewer /data/arkime/bin/arkime_add_user admin "Admin User" adminpassword --admin
```

Open the web interface at `http://your-server:8005`.

### Searching DNS Sessions in Arkime

In the Arkime Sessions view:

1. Set the expression to `protocols == dns`
2. Add time range filters (last hour, last day, custom range)
3. Click any session to see full DNS query/response details
4. Download the PCAP for offline analysis in Wireshark

Use the SPI View tab to create custom DNS analytics:
- Top DNS query names
- Clients generating the most NXDOMAIN responses
- Unusual DNS record types (TXT, NULL, CNAME chains)

## Comparison Summary

Each tool serves a different operational need:

| Use Case | Recommended Tool | Why |
|---|---|---|
| Quick DNS troubleshooting | dnstop | Zero setup, instant terminal view |
| DNS as part of observability | Packetbeat | Integrates with Elastic Stack, built-in dashboards |
| DNS forensics and incident response | Arkime | Full packet capture, historical PCAP access |
| Multi-site DNS monitoring | Packetbeat | Lightweight shippers on every node |
| Security investigations | Arkime | Full PCAP, correlates with all network protocols |
| Low-resource environments | dnstop | Single binary, minimal memory footprint |

## Choosing the Right Tool

Start with **dnstop** if you need immediate visibility with zero infrastructure. It is the equivalent of `top` for DNS — a quick diagnostic that tells you what is happening right now.

Choose **Packetbeat** if you already run (or plan to run) the Elastic Stack. It slots into your existing observability pipeline and adds DNS alongside HTTP, TLS, and database monitoring with minimal overhead.

Deploy **Arkime** when you need forensic-grade DNS monitoring. If you are investigating a security incident, responding to a DNS-based attack, or need to prove compliance with audit requirements, having the full packet capture available is invaluable.

For comprehensive coverage, many organizations run all three: dnstop for on-call troubleshooting, Packetbeat for continuous monitoring dashboards, and Arkime for security forensics and compliance.

For related reading, see our [DNS load balancing guide](../dnsdist-vs-powerdns-recursor-vs-unbound-self-hosted-dns-load-balancing-guide-2026/) for dnsdist deployment and [network traffic analysis comparison](../self-hosted-network-traffic-analysis-zeek-arkime-ntopng-guide-2026/) for broader packet capture options.

## FAQ

### What is the best tool to monitor DNS queries in real time?

For real-time terminal monitoring, **dnstop** is the simplest and fastest option. It shows live DNS query statistics in an interactive ncurses interface with zero configuration — just point it at a network interface. If you need real-time dashboards with historical context, **Packetbeat** with Kibana provides visual real-time monitoring.

### Can I monitor DNS traffic without installing agents on every server?

Yes. Tools like **dnstop** and **Arkime** use libpcap to capture DNS traffic directly on a network interface or mirror port. You only need to deploy them where DNS traffic flows — typically on your DNS resolver, firewall, or a switch SPAN/mirror port. Packetbeat, however, does require installation on each host you want to monitor.

### How do I detect DNS tunneling with these tools?

**dnstop** can reveal tunneling by showing unusually long domain names or high query volumes to a single domain in its "Queries" table. **Packetbeat** lets you query Elasticsearch for abnormally long `dns.question.name` values or high-frequency queries to suspicious domains. **Arkime** provides the most thorough detection — you can search for DNS sessions with large response sizes or unusual TXT record queries, then examine the full PCAP to confirm.

### Does Arkime replace Packetbeat for DNS monitoring?

Not exactly. Arkime stores full packet captures, which includes all DNS data, but it is designed as a security forensics platform rather than a monitoring dashboard. Packetbeat provides structured DNS fields, pre-built Kibana dashboards, and alerting capabilities out of the box. Many teams use Arkime for deep forensic investigation and Packetbeat for day-to-day operational monitoring.

### Can these tools monitor encrypted DNS (DoH/DoT)?

**dnstop** only monitors unencrypted DNS on port 53 — it cannot parse encrypted DNS over HTTPS (DoH) or DNS over TLS (DoT) traffic. **Packetbeat** can parse DoT if you configure it with the TLS decryption keys, but DoH appears as regular HTTPS traffic. **Arkime** captures all packets but similarly cannot decrypt encrypted DNS without the server's TLS keys. For encrypted DNS monitoring, see our [DNS over HTTPS and TLS guide](../self-hosted-dns-privacy-doh-dot-dnscrypt-complete-guide-2026/) for self-hosted resolver options that log query data before encryption.

### How much storage does Arkime need for DNS monitoring?

Storage depends on traffic volume. A small office (100-500 users) typically generates 1-5 GB of PCAP per day. Arkime's `freeSpaceG` setting automatically deletes old captures when disk space runs low. For DNS-only monitoring (not full network capture), you can use BPF filters like `port 53` to capture only DNS traffic, dramatically reducing storage needs. A 1 TB drive can store weeks of DNS-only captures for a small network.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Best Self-Hosted DNS Monitoring Tools: dnstop vs Packetbeat vs Arkime 2026",
  "description": "Compare the best self-hosted DNS monitoring tools — dnstop, Packetbeat, and Arkime. Learn to track DNS queries, detect anomalies, and analyze DNS traffic with open-source solutions.",
  "datePublished": "2026-04-22",
  "dateModified": "2026-04-22",
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
