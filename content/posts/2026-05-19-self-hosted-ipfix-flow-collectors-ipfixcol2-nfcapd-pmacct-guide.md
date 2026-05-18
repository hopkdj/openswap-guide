---
title: "Self-Hosted IPFIX Flow Collectors — ipfixcol2 vs nfcapd vs pmacct"
date: "2026-05-19"
tags: ["network-monitoring", "flow-analysis", "ipfix", "netflow", "self-hosted"]
draft: false
---

IPFIX (IP Flow Information Export, RFC 7011) is the IETF standard for exporting network flow data from routers, switches, and probes. While NetFlow v5/v9 are Cisco proprietary protocols, IPFIX is the open, extensible standard adopted by most modern network equipment. If you operate a self-hosted network infrastructure and need deep visibility into traffic patterns, bandwidth consumption, and application-level flows, deploying a dedicated IPFIX collector is essential.

In this guide, we compare three mature open-source IPFIX collectors: **CESNET ipfixcol2**, **nfcapd** (from the nfdump toolkit), and **pmacct** — covering their architecture, deployment, feature sets, and operational characteristics.

## Why IPFIX Matters for Self-Hosted Networks

IPFIX extends beyond traditional NetFlow by supporting variable-length fields, enterprise-specific Information Elements (IEs), and template-based data models. This means your collector can receive enriched flow records that include application identifiers, HTTP host headers, VLAN tags, MPLS labels, and more.

For self-hosted network operators, IPFIX collectors serve several critical functions:

- **Bandwidth accounting** — track per-subnet, per-host, and per-application traffic consumption
- **Security monitoring** — detect DDoS attacks, port scans, and anomalous traffic patterns
- **Capacity planning** — forecast link utilization and plan infrastructure upgrades
- **Compliance reporting** — generate flow-based audit trails for regulatory requirements
- **Troubleshooting** — correlate flow data with application performance issues

Unlike packet capture (tcpdump/Wireshark), which requires full packet inspection, IPFIX sampling provides scalable flow-level visibility with minimal overhead on the forwarding plane.

## CESNET ipfixcol2

[ipfixcol2](https://github.com/CESNET/ipfixcol2) is a high-performance IPFIX and NetFlow collector developed by CESNET (the Czech National Research and Education Network). Written in C++, it supports NetFlow v5/v9 and IPFIX (RFC 7011) with a modular plugin architecture.

**Key features:**

- Protocol support: NetFlow v5, v9, and IPFIX (RFC 7011)
- Multi-threaded architecture for high-throughput environments
- Plugin system for output formats: CSV, JSON, database (MySQL, PostgreSQL), and unified2
- Template management and observation domain tracking
- Active development by a national research network

**Docker Compose deployment:**

```yaml
version: "3.8"

services:
  ipfixcol2:
    image: cesnet/ipfixcol2:latest
    container_name: ipfixcol2
    ports:
      - "4739:4739/udp"
      - "2055:2055/udp"
    volumes:
      - ./config/ipfixcol2:/etc/ipfixcol2
      - ./data/ipfix:/var/lib/ipfixcol2
    restart: unless-stopped
    environment:
      - IPFIXCOL_CONFIG=/etc/ipfixcol2/config.xml
    networks:
      - monitoring

  # Optional: Grafana + Prometheus for visualization
  prometheus:
    image: prom/prometheus:latest
    container_name: ipfix-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./data/prometheus:/prometheus
    networks:
      - monitoring

networks:
  monitoring:
    driver: bridge
```

**Configuration (config.xml excerpt):**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ipfixcol>
  <global>
    <pluginsDir>/usr/lib/ipfixcol</pluginsDir>
  </global>
  <input>
    <listener>
      <name>IPFIX UDP</name>
      <plugin>ipfixcol_udp.so</plugin>
      <params>
        <port>4739</port>
      </params>
    </listener>
    <listener>
      <name>NetFlow UDP</name>
      <plugin>ipfixcol_udp.so</plugin>
      <params>
        <port>2055</port>
      </params>
    </listener>
  </input>
  <output>
    <plugin>ipfixcol_csv.so</plugin>
    <params>
      <fileDir>/var/lib/ipfixcol2</fileDir>
      <fileTemplate>%Y-%m-%d_%H%M.csv</fileTemplate>
    </params>
  </output>
</ipfixcol>
```

ipfixcol2 is particularly strong for research and education networks, with built-in support for the IPFIX Information Model and enterprise-specific IEs commonly used in academic environments.

## nfcapd (nfdump Toolkit)

**nfcapd** is the capture daemon from the [nfdump](https://github.com/phaag/nfdump) toolkit — a widely deployed NetFlow and IPFIX collection suite. Written in C, it is the de facto standard for NetFlow collection on Unix-like systems.

**Key features:**

- Protocol support: NetFlow v5/v9, IPFIX (RFC 7011), sFlow v5
- File-based storage with time-rotated capture files
- Powerful analysis tools: nfdump (query), nfreplay (replay), nfcapd (capture)
- Lightweight resource footprint — runs on minimal hardware
- Decades of field deployment and battle-tested reliability

**Docker Compose deployment:**

```yaml
version: "3.8"

services:
  nfcapd:
    image: phaag/nfdump:latest
    container_name: nfcapd
    ports:
      - "9995:9995/udp"
      - "4739:4739/udp"
    volumes:
      - ./data/flows:/nfdump
    command: >
      nfcapd -w /nfdump -p 9995 -P 4739
      -l /nfdump
      -S 1
      -t 300
      -z
    restart: unless-stopped
    networks:
      - monitoring

  flow-viewer:
    image: nginx:alpine
    container_name: flow-viewer
    ports:
      - "8080:80"
    volumes:
      - ./data/flows:/usr/share/nginx/html/flows:ro
      - ./config/nginx.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - nfcapd
    restart: unless-stopped
    networks:
      - monitoring

networks:
  monitoring:
    driver: bridge
```

**Install from source:**

```bash
# Debian/Ubuntu
apt-get update && apt-get install -y build-essential libpcap-dev libbz2-dev

git clone https://github.com/phaag/nfdump.git
cd nfdump
./autogen.sh
./configure --enable-nfprofile --enable-nfcapd-extended
make -j$(nproc)
make install

# Start nfcapd
nfcapd -w /var/nfdump -p 9995 -t 300 -z -l /var/nfdump
```

**Querying flows:**

```bash
# Show top 10 talkers in the last hour
nfdump -r /var/nfdump/nfcapd.current -T b -s ip/bytes -n 10

# Show flows from a specific source IP
nfdump -r /var/nfdump/nfcapd.current -o extended 'src ip 192.168.1.100'

# Generate time-series data for graphing
nfdump -r /var/nfdump/nfcapd.current -t 2026/01/01.00:00-2026/01/01.23:59 -A bytes
```

nfcapd is the best choice when you need a lightweight, reliable flow collector with minimal dependencies and excellent command-line analysis tools.

## pmacct

[pmacct](https://github.com/pmacct/pmacct) is a comprehensive network monitoring toolkit that goes beyond simple flow collection. It supports NetFlow v5/v9, IPFIX, sFlow, and raw packet capture, with output to databases, Kafka, RabbitMQ, and more.

**Key features:**

- Protocol support: NetFlow v5/v9, IPFIX, sFlow v5, raw pcap
- Multiple output backends: MySQL, PostgreSQL, MongoDB, Kafka, RabbitMQ, Redis, AMQP
- Traffic accounting with customizable aggregation dimensions
- BGP daemon for flow enrichment with AS path data
- Active community and enterprise-grade deployment

**Docker Compose deployment:**

```yaml
version: "3.8"

services:
  pmacct:
    image: pmacct/pmacct:latest
    container_name: pmacct
    ports:
      - "4739:4739/udp"
      - "9995:9995/udp"
      - "6391:6391/udp"
    volumes:
      - ./config/pmacct:/etc/pmacct
    command: pmacctd -f /etc/pmacct/pmacct.conf
    restart: unless-stopped
    networks:
      - monitoring

  postgres:
    image: postgres:16-alpine
    container_name: pmacct-db
    environment:
      POSTGRES_DB: pmacct
      POSTGRES_USER: pmacct
      POSTGRES_PASSWORD: pmacct_password
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - monitoring

networks:
  monitoring:
    driver: bridge
```

**Configuration (pmacct.conf):**

```ini
# pmacctd configuration for IPFIX collection
daemonize: true
syslog: true
pidfile: /var/run/pmacct/pmacctd.pid

# Network collector (nfprobe-like behavior)
plugins: memory[inlet], memory[inlet2]
aggregate: src_host,dst_host,src_port,dst_port,proto

# IPFIX receiver
nfprobe_receiver: 0.0.0.0:4739
sfprobe_receiver: 0.0.0.0:6391

# Memory plugin for in-memory aggregation
imt_mem_pruning: true
imt_mem_pools_number: 4

# Output to PostgreSQL
sql_host: postgres
sql_user: pmacct
sql_passwd: pmacct_password
sql_db: pmacct
sql_table: acct
sql_refresh_time: 60
sql_history: 5m
sql_history_roundoff: m
```

pmacct shines when you need flexible flow aggregation, multiple output backends, and the ability to correlate flow data with BGP routing information.

## Comparison Table

| Feature | ipfixcol2 | nfcapd (nfdump) | pmacct |
|---------|-----------|-----------------|--------|
| **Protocol Support** | NetFlow v5/v9, IPFIX | NetFlow v5/v9, IPFIX, sFlow v5 | NetFlow v5/v9, IPFIX, sFlow v5, pcap |
| **Language** | C++ | C | C |
| **Stars** | 192+ | 850+ (nfdump) | 900+ |
| **Storage** | File (CSV, JSON), DB plugins | File-based (nfcapd format) | DB (MySQL, PG, MongoDB), Kafka, Redis |
| **Threading** | Multi-threaded | Single-threaded per instance | Multi-threaded |
| **Template Management** | Full RFC 7011 compliance | Partial IPFIX template support | Full IPFIX + enterprise IEs |
| **BGP Integration** | No | No | Yes (bgp_daemon) |
| **Real-time Output** | Plugin-driven | File rotation (configurable interval) | Configurable refresh intervals |
| **Docker Support** | Official image | Community images | Official image |
| **Best For** | Research/education networks | Lightweight, reliable collection | Enterprise with DB/Kafka backends |
| **Learning Curve** | Moderate (XML config) | Low (CLI-based) | Moderate (INI config) |

## Choosing the Right IPFIX Collector

**Use ipfixcol2 if:** You operate a research or education network, need strict RFC 7011 compliance, or require enterprise-specific Information Elements commonly used in academic environments. Its plugin architecture makes it extensible for custom output formats.

**Use nfcapd (nfdump) if:** You need a lightweight, resource-efficient flow collector with minimal dependencies. The nfdump toolkit provides excellent command-line analysis tools (nfdump, nfreplay, nfcapd) and has decades of field-proven reliability. It is the best choice for homelabs, small-to-medium networks, and operators who prefer CLI-based analysis over database-driven dashboards.

**Use pmacct if:** You need enterprise-grade flow collection with flexible output backends (PostgreSQL, Kafka, Redis), BGP enrichment for AS-path-aware analysis, or traffic accounting with customizable aggregation dimensions. pmacct is ideal for ISPs, cloud providers, and organizations that need to integrate flow data into broader data pipelines.

## Why Self-Host Your IPFIX Collector?

Network flow data reveals the DNA of your infrastructure — every connection, every protocol, every bandwidth consumer. Relying on commercial SaaS flow collectors means sending this visibility data to third-party platforms, often with limited retention, restricted query capabilities, and per-flow pricing.

Self-hosting an IPFIX collector gives you complete control over data retention (keep years of flow records if needed), query flexibility (correlate flows with local events, combine with log data), and cost efficiency (no per-flow or per-exporter licensing). For network operators managing anything from a homelab to a multi-site enterprise, an open-source IPFIX collector is a foundational observability component.

For comprehensive network flow analysis beyond IPFIX, see our [GoFlow2 and softflowd flow collector guide](../2026-05-24-self-hosted-network-flow-collectors-goflow2-softflowd-nfdump-guide/) and our [pmacct, nfdump, and fprobe analysis guide](../2026-05-15-self-hosted-network-flow-analysis-pmacct-nfdump-fprobe-guide/). If you need NetFlow-specific collection with visualization, our [ElastiFlow, Akvorado, and GoFlow2 comparison](../elastiflow-vs-akvorado-vs-goflow2-self-hosted-netflow-collector-guide-2026/) covers the full-featured options.

## FAQ

### What is the difference between NetFlow v9 and IPFIX?

NetFlow v9 is Cisco's template-based flow export protocol that became the foundation for IPFIX. IPFIX (RFC 7011) is the IETF standardization of NetFlow v9 with additional features: variable-length fields, enterprise-specific Information Elements, standardized Information Element registry, and mandatory template management. In practice, most modern collectors support both protocols transparently.

### Can nfcapd collect IPFIX data?

Yes. Modern versions of nfcapd support IPFIX (RFC 7011) collection alongside NetFlow v5/v9 and sFlow v5. However, its IPFIX template management is more limited compared to dedicated IPFIX collectors like ipfixcol2. For environments with complex IPFIX templates or enterprise-specific IEs, ipfixcol2 or pmacct may provide better compatibility.

### How much storage does an IPFIX collector need?

Storage requirements depend on flow export rate and retention period. A typical medium network exporting 10,000 flows per second generates approximately 1-2 GB of raw flow data per day (compressed). For nfcapd with file rotation and compression (`-z` flag), plan for 50-100 GB per month of active retention. ipfixcol2 with CSV output uses similar storage. pmacct with database output may require 2-3x more storage due to relational overhead.

### Do I need to configure my routers for IPFIX export?

Yes. IPFIX must be enabled on your network devices (routers, switches, firewalls) as the data source. Typical configuration on Cisco IOS:
```
flow record MY_RECORD
  match ipv4 source address
  match ipv4 destination address
  collect transport source-port
  collect transport destination-port
  collect counter bytes long
  collect counter packets long
!
flow exporter MY_EXPORTER
  destination 192.168.1.10
  transport udp 4739
!
flow monitor MY_MONITOR
  record MY_RECORD
  exporter MY_EXPORTER
!
interface GigabitEthernet0/0
  ip flow monitor MY_MONITOR input
```

### Which collector supports the highest throughput?

ipfixcol2's multi-threaded C++ architecture handles the highest throughput, tested at 500,000+ flows per second on commodity hardware. pmacct also supports high throughput with multi-threaded processing. nfcapd is single-threaded per instance but can be run in parallel on different ports for horizontal scaling.

### Can I visualize IPFIX data with Grafana?

Yes. All three collectors can feed data to Grafana: ipfixcol2 via Prometheus plugins, nfcapd via nfdump-exporter (a Prometheus exporter for nfdump files), and pmacct via its native Prometheus metrics or by querying its PostgreSQL backend with Grafana's SQL data source.


<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted IPFIX Flow Collectors — ipfixcol2 vs nfcapd vs pmacct",
  "description": "Compare three open-source IPFIX flow collectors for self-hosted network monitoring: CESNET ipfixcol2, nfcapd (nfdump toolkit), and pmacct. Includes Docker Compose configs, feature comparison, and deployment guides.",
  "datePublished": "2026-05-19",
  "dateModified": "2026-05-19",
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

