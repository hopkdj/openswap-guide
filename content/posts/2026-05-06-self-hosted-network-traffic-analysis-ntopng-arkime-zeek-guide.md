---
title: "Self-Hosted Network Traffic Analysis: ntopng vs Arkime vs Zeek (2026)"
date: 2026-05-06
tags: ["comparison", "guide", "self-hosted", "networking", "security", "traffic-analysis"]
draft: false
---

Network traffic analysis tools capture, index, and visualize network flows to help administrators identify performance issues, security threats, and capacity bottlenecks. Self-hosted traffic analysis platforms give you complete visibility into your network without sending flow data to external monitoring services.

In this guide, we compare three powerful self-hosted network traffic analysis platforms: **ntopng**, **Arkime** (formerly Moloch), and **Zeek** (formerly Bro). Each takes a distinct approach to traffic visibility — from real-time flow dashboards to full packet capture to protocol-aware analysis.

## What Is Self-Hosted Network Traffic Analysis?

Network traffic analysis platforms monitor, capture, and analyze network packets and flows across your infrastructure. Unlike simple bandwidth monitors, these tools provide deep protocol inspection, historical search capabilities, and alerting on anomalous traffic patterns.

Key benefits of self-hosted traffic analysis:

- **Complete packet visibility**: Every packet stays within your network for forensic analysis
- **No data egress**: Sensitive traffic metadata never leaves your infrastructure
- **Unlimited retention**: Store packet captures as long as your storage allows
- **Custom detection rules**: Write protocol-specific analyzers for your environment
- **Regulatory compliance**: Meet audit requirements for network logging and retention

## ntopng vs Arkime vs Zeek: Feature Comparison

| Feature | ntopng | Arkime | Zeek |
|---------|--------|--------|------|
| **Type** | Flow monitor + dashboard | Full packet capture | Protocol analysis engine |
| **Language** | C/C++ + Lua | C + Node.js | C++ + Zeek scripting |
| **Stars** | 6,000+ | 5,000+ | 6,000+ |
| **Packet Capture** | Sampled | Full PCAP | Full PCAP |
| **Flow Records** | NetFlow/IPFIX | Session index | Connection logs |
| **Protocol Detection** | Deep inspection | Basic metadata | Advanced protocol parsers |
| **Real-Time Dashboard** | Built-in web UI | Built-in web UI | Via Kibana/Grafana |
| **Full-Text Search** | Limited | Elasticsearch-based | Via external tools |
| **PCAP Download** | Yes | Yes | Manual |
| **Scripting** | Lua plugins | No | Zeek scripting language |
| **Alerting** | Threshold-based | Rule-based | Event-driven |
| **Storage Backend** | RRD + Redis | Elasticsearch | File-based + optional DB |
| **Self-Hosted** | Yes | Yes | Yes |

## ntopng: Real-Time Flow Monitoring

[ntopng](https://github.com/ntop/ntopng) is a high-speed web-based traffic analysis and flow collection platform. It provides real-time dashboards showing top talkers, protocol distribution, and network utilization with minimal overhead.

**Key features:**
- Real-time traffic visualization with geographic maps
- Supports NetFlow, sFlow, and IPFIX export
- Layer 7 protocol identification using nDPI
- Historical traffic analysis with RRD storage
- REST API for integration with monitoring stacks
- SNMP monitoring and alerting

### Docker Compose for ntopng

```yaml
version: "3.8"
services:
  redis:
    image: redis:7-alpine
    container_name: ntopng-redis
    restart: unless-stopped
    command: redis-server --save "" --appendonly no

  ntopng:
    image: ntop/ntopng:stable
    container_name: ntopng
    restart: unless-stopped
    ports:
      - "3000:3000"
    depends_on:
      - redis
    cap_add:
      - NET_ADMIN
      - NET_RAW
    network_mode: "host"
    environment:
      - REDIS_SERVER=redis:6379
    command: >
      -i eth0
      -w 3000
      -r redis:6379
      --community
```

### ntopng Configuration

```ini
# /etc/ntopng/ntopng.conf
-G=/var/run/ntopng.pid
--local-networks "192.168.1.0/24,10.0.0.0/8"
--interface eth0
--http-port 3000
--redis localhost
--community
--disable-autologout
```

## Arkime: Full Packet Capture and Search

[Arkime](https://github.com/arkime/arkime) (formerly Moloch) is a large-scale, open-source network packet capture and search system. It indexes every packet and provides a web interface for searching, analyzing, and downloading PCAP data.

**Key features:**
- Full packet capture with configurable retention
- Elasticsearch-based indexing for fast full-text search
- PCAP export for forensic analysis
- SPI (Session Protocol Index) for protocol metadata
- Tagging and note-taking for incident investigation
- Multi-cluster support for distributed deployments

### Docker Compose for Arkime

```yaml
version: "3.8"
services:
  elasticsearch:
    image: opensearchproject/opensearch:2
    container_name: arkime-es
    restart: unless-stopped
    environment:
      - discovery.type=single-node
      - plugins.security.disabled=true
    ulimits:
      memlock:
        soft: -1
        hard: -1
    volumes:
      - es-data:/usr/share/opensearch/data

  arkime:
    image: arkime/arkime:latest
    container_name: arkime
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
      - NET_RAW
    network_mode: "host"
    environment:
      - ARKIME_ELASTICSEARCH=http://elasticsearch:9200
      - ARKIME_INTERFACE=eth0
    volumes:
      - pcap-data:/opt/arkime/raw
    depends_on:
      - elasticsearch

volumes:
  es-data:
  pcap-data:
```

## Zeek: Protocol-Aware Network Analysis

[Zeek](https://github.com/zeek/zeek) (formerly Bro) is a powerful network analysis framework that goes beyond flow monitoring to understand application-layer protocols. It generates structured logs for HTTP, DNS, SMTP, SSL, and dozens of other protocols.

**Key features:**
- Protocol-specific analyzers for 50+ protocols
- Powerful Zeek scripting language for custom detection
- Structured log output (TSV/JSON) for easy parsing
- Passive analysis — no active probing required
- Integration with threat intelligence feeds
- Used by research institutions and CERTs worldwide

### Docker Compose for Zeek

```yaml
version: "3.8"
services:
  zeek:
    image: joshlight/zeek:latest
    container_name: zeek
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
      - NET_RAW
    network_mode: "host"
    volumes:
      - ./zeek-config:/opt/zeek/share/zeek/site:ro
      - zeek-logs:/opt/zeek/logs
    environment:
      - ZEEK_INTERFACE=eth0
      - ZEEK_LOCAL_NETS=192.168.1.0/24

volumes:
  zeek-logs:
```

### Zeek Site Configuration (local.zeek)

```zeek
@load protocols/ftp
@load protocols/smtp
@load protocols/ssl
@load protocols/dns
@load frameworks/files/hash-all-files
@load frameworks/intel/seen
@load frameworks/intel/do_notice

redef Intel::read_files += {
  "/opt/zeek/share/zeek/site/intel.dat"
};

redef notice_policy_hooks += {
  Notice::email_notice
};

redef Notice::mail_dest_addrs = {
  "admin@example.com"
};
```

## Choosing the Right Traffic Analysis Tool

**Use ntopng when:**
- You need real-time flow monitoring with a polished dashboard
- Your primary goal is network utilization and top-talkers visibility
- You want geographic traffic mapping and protocol distribution
- You prefer low-overhead sampled analysis over full packet capture

**Use Arkime when:**
- You need full packet capture for forensic investigations
- You want to search across historical traffic with full-text indexing
- Your team investigates security incidents and needs PCAP evidence
- You operate at scale with multi-cluster Elasticsearch backends

**Use Zeek when:**
- You need deep protocol analysis and structured logging
- You want to write custom detection scripts for specific protocols
- Your focus is threat detection and anomaly identification
- You integrate with SIEM platforms and threat intelligence feeds

## Why Self-Host Your Traffic Analysis?

Running network traffic analysis on your own infrastructure provides critical advantages:

**Complete packet privacy**: Network flows reveal which services your infrastructure communicates with, including internal tooling, vendor APIs, and cloud services. Self-hosted analysis keeps this metadata private.

**Unlimited packet retention**: Cloud traffic analysis services limit retention periods. Self-hosted packet capture stores data for as long as your storage allows, enabling months-long forensic investigations.

**Custom protocol analysis**: Self-hosted tools let you write protocol parsers for proprietary or internal protocols that cloud services would never understand.

**No sampling required**: Cloud services often sample traffic to reduce costs. Self-hosted platforms capture every packet, ensuring no threat or anomaly slips through sampling gaps.

**Integration flexibility**: Connect self-hosted traffic analysis to your existing monitoring stack, SIEM, alerting systems, and ticketing platforms without API limitations.

For comprehensive network security, combine traffic analysis with [self-hosted IDS/IPS systems](../2026-04-18-suricata-vs-snort-vs-zeek-self-hosted-ids-ips-guide-2026/) for active threat blocking. Pair with [self-hosted honeypots](../self-hosted-honeypot-deception-cowrie-tpot-opencanary-guide-2026/) to detect reconnaissance activity.

## FAQ

### What is the difference between ntopng, Arkime, and Zeek?

ntopng focuses on real-time flow monitoring and dashboard visualization. Arkime specializes in full packet capture with searchable indexing. Zeek provides deep protocol analysis with structured logging and custom scripting capabilities. They complement each other and can be deployed together.

### Can I run ntopng, Arkime, and Zeek simultaneously?

Yes. Many organizations run all three: ntopng for real-time dashboards, Arkime for packet capture and forensic search, and Zeek for protocol analysis and threat detection. Each captures traffic from a mirrored port or span session.

### How much storage does full packet capture require?

Full packet capture is storage-intensive. At 1 Gbps line rate, expect roughly 400 GB per day of raw PCAP data. Arkime compresses and indexes captures, reducing effective storage needs. Plan storage based on your retention requirements and traffic volume.

### Does Zeek detect threats automatically?

Zeek generates structured logs for all observed protocols. Threat detection requires writing Zeek scripts or integrating with threat intelligence feeds. The Intel framework in Zeek can match observed traffic against known-bad indicators.

### Can ntopng replace a traditional network monitoring tool?

ntopng provides flow-level monitoring and protocol identification but does not replace SNMP-based device monitoring or infrastructure health checks. Use it alongside tools like LibreNMS or Zabbix for comprehensive network visibility.

### Is Arkime suitable for compliance requirements?

Yes. Ark provides full packet capture with configurable retention, searchable audit trails, and PCAP export for evidence submission. It meets PCI-DSS, HIPAA, and SOX requirements for network traffic logging when properly configured.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Network Traffic Analysis: ntopng vs Arkime vs Zeek (2026)",
  "description": "Compare self-hosted network traffic analysis platforms - ntopng, Arkime, and Zeek - with Docker Compose configs for flow monitoring and packet capture.",
  "datePublished": "2026-05-06",
  "dateModified": "2026-05-06",
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
