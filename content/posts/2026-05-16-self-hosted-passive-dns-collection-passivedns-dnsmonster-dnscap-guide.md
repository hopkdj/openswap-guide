---
title: "Self-Hosted Passive DNS Collection: PassiveDNS vs DNSMonster vs dnscap"
date: "2026-05-16"
tags: ["dns", "passive-dns", "security", "monitoring", "network-analysis"]
draft: false
---

Passive DNS (pDNS) is a network security technique that records DNS queries and responses observed on a network, building a historical database of domain-to-IP mappings. Unlike active DNS lookups, passive DNS captures real traffic — revealing what domains hosts actually resolve, when they resolve them, and to which IP addresses. This data is invaluable for threat intelligence, forensic investigations, and network monitoring.

Three open-source tools lead the self-hosted passive DNS space: **PassiveDNS** by Gamelinux, the original and most widely deployed packet capture tool; **DNSMonster**, a modern passive DNS and network traffic monitoring toolkit with web UI; and **dnscap** by DNS-OARC, a specialized DNS traffic capture utility designed for operational DNS analysis.

## Why Collect Passive DNS Data?

Passive DNS collection provides visibility into DNS activity that active querying cannot match:

- **Threat detection** — identify domains associated with malware, phishing, or command-and-control servers by comparing captured DNS data against threat intelligence feeds
- **Forensic investigation** — after a security incident, search historical DNS records to determine which domains a compromised host contacted and when
- **Infrastructure monitoring** — detect DNS misconfigurations, stale records, or unauthorized subdomain creation
- **Compliance auditing** — maintain records of all DNS activity for regulatory requirements
- **Network baseline** — understand normal DNS patterns to detect anomalies

For comprehensive network traffic analysis, see our [Arkime vs Zeek vs Suricata guide](../2026-05-04-arkime-vs-zeek-vs-suricata-self-hosted-network-traffic-analysis-guide/).
For broader DNS monitoring, our [self-hosted DNS monitoring tools comparison](../best-self-hosted-dns-monitoring-tools-dnstop-packetbeat-arkime-guide-2026/) covers additional tools.
And for IDS/IPS capabilities, our [Suricata vs Snort vs Zeek guide](../2026-04-18-suricata-vs-snort-vs-zeek-self-hosted-ids-ips-guide-2026/) covers complementary security tools.

## PassiveDNS (gamelinux/passivedns)

PassiveDNS is a network sniffer that logs all DNS server replies for use in a passive DNS database. It is the most widely used open-source passive DNS collector, written in C for high performance.

**Key features:**
- High-performance C implementation using libpcap
- Logs all DNS answer types (A, AAAA, CNAME, MX, NS, PTR, TXT, SRV, etc.)
- Supports output to MySQL, PostgreSQL, or plain text files
- Configurable BPF filters to capture specific traffic
- Low resource footprint — can process millions of packets per second
- DNS response code logging (NXDOMAIN, SERVFAIL, etc.)
- First/last seen timestamps for each record
- Duplicate suppression — only logs unique query/response pairs

PassiveDNS is designed as a backend collector. It captures packets, extracts DNS data, and writes records to a database or file. You typically pair it with a database and a query interface for analysis.

**Star count:** 1,736+ on GitHub
**Language:** C
**License:** BSD

## DNSMonster (FenkoHQ/dnsmonster)

DNSMonster is a modern passive DNS capture and monitoring toolkit written in Go. It provides a more feature-rich alternative to PassiveDNS with built-in support for multiple output backends and a web UI.

**Key features:**
- Go implementation with multi-threaded packet processing
- Multiple output backends: ClickHouse, Elasticsearch, MongoDB, Kafka, Splunk
- Built-in web dashboard for DNS query visualization
- Supports dnstap protocol (modern DNS telemetry standard)
- PCAP file processing for offline analysis
- Docker Compose deployment with pre-built images
- Configurable sampling rates for high-traffic networks
- GeoIP enrichment for resolved IP addresses
- Query type and response code analytics
- Prometheus metrics export

DNSMonster is particularly well-suited for organizations that already use ClickHouse or Elasticsearch for log aggregation, as it can stream DNS data directly into those platforms for correlation with other security telemetry.

**Star count:** 354+ on GitHub
**Language:** Go
**License:** MIT

## dnscap (DNS-OARC/dnscap)

dnscap is a network capture utility designed specifically for DNS traffic, developed by DNS-OARC (DNS Operations, Analysis, and Research Center). Unlike the other two tools, dnscap focuses on capturing raw DNS packets to PCAP files rather than extracting structured records.

**Key features:**
- Specialized for DNS traffic only (filters non-DNS packets automatically)
- Produces standard PCAP output compatible with Wireshark, tcpdump
- Supports DNS compression pointer analysis
- TCP and UDP DNS traffic capture
- IPv4 and IPv6 support
- Configurable capture filters and output rotation
- Designed for DNS operator use cases (root server analysis, TLD monitoring)
- Low overhead — optimized for continuous 24/7 capture
- Now hosted on Codeberg (moved from GitHub)

dnscap is the tool of choice for DNS operators who need to capture DNS traffic for offline analysis with Wireshark or for feeding into custom analysis pipelines. It does not parse DNS records itself — it captures the raw packets.

**Star count:** 294+ on GitHub (primary repo moved to Codeberg)
**Language:** C
**License:** ISC

## Comparison Table

| Feature | PassiveDNS | DNSMonster | dnscap |
|---------|-----------|-----------|--------|
| **Primary Purpose** | pDNS record extraction | pDNS + monitoring dashboard | DNS packet capture |
| **Language** | C | Go | C |
| **Output Format** | DB records (MySQL/PgSQL) | ClickHouse/ES/MongoDB/Kafka | PCAP files |
| **Web UI** | No | Yes (built-in) | No |
| **dnstap Support** | No | Yes | No |
| **Real-time Processing** | Yes | Yes | Yes |
| **Offline PCAP Analysis** | No | Yes | No (produces PCAP) |
| **GeoIP Enrichment** | No | Yes | No |
| **Prometheus Metrics** | No | Yes | No |
| **Docker Support** | Manual | Docker Compose (pre-built) | Manual |
| **Record Parsing** | Full DNS parsing | Full DNS parsing | Raw packet capture |
| **Best For** | pDNS database building | Security operations centers | DNS operators, forensics |
| **GitHub Stars** | 1,736+ | 354+ | 294+ |

## Installation and Deployment

### Installing PassiveDNS

```bash
# Install dependencies
sudo apt-get install libpcap-dev libldns-dev libmysqlclient-dev

# Clone and build
git clone https://github.com/gamelinux/passivedns.git
cd passivedns
autoreconf -i
./configure
make
sudo make install

# Run on interface with MySQL output
sudo passivedns -i eth0 -l /var/log/passivedns.log   --mysql-server localhost --mysql-user pdns --mysql-pass secret   --mysql-db passivedns
```

### Installing DNSMonster via Docker Compose

```yaml
version: "3.8"
services:
  dnsmonster:
    image: fenkohq/dnsmonster:latest
    network_mode: host
    cap_add:
      - NET_RAW
      - NET_ADMIN
    command: >
      --pcaped=eth0
      --outputType=3
      --clickhouseAddress=clickhouse:9000
      --clickhouseDatabase=dnsmonster
    depends_on:
      - clickhouse

  clickhouse:
    image: clickhouse/clickhouse-server:latest
    volumes:
      - clickhouse_data:/var/lib/clickhouse
    ports:
      - "8123:8123"
      - "9000:9000"

volumes:
  clickhouse_data:
```

### Installing dnscap

```bash
# Install dependencies
sudo apt-get install libpcap-dev libldns-dev

# Clone and build
git clone https://codeberg.org/DNS-OARC/dnscap.git
cd dnscap
autoreconf -i
./configure
make
sudo make install

# Capture DNS traffic on port 53
sudo dnscap -i eth0 -g -T -p 53 -w dns_capture.pcap
```

## Choosing the Right Tool

**Choose PassiveDNS** when:
- You need to build a traditional passive DNS database
- You want the most battle-tested collector with years of production use
- MySQL or PostgreSQL is your preferred backend
- You need maximum packet processing performance (C implementation)

**Choose DNSMonster** when:
- You want a modern stack with web dashboard and multiple output options
- You already use ClickHouse or Elasticsearch for security analytics
- You need dnstap support for modern DNS telemetry
- You want Docker Compose deployment with minimal setup

**Choose dnscap** when:
- You need raw PCAP files for offline Wireshark analysis
- You are a DNS operator doing root server or TLD analysis
- You want specialized DNS-only capture with minimal overhead
- You need to capture DNS traffic for custom analysis pipelines

## Why Self-Host Passive DNS Collection?

Running passive DNS collection on-premises provides security teams with complete visibility into their organization's DNS activity without sending sensitive query data to third-party services. DNS queries reveal which services employees use, which cloud providers the organization depends on, and — critically — which malicious domains compromised hosts attempt to contact.

Privacy regulations in many jurisdictions restrict the sharing of DNS data with external parties. Self-hosted collection keeps all query data within your network boundary, enabling compliance with GDPR, HIPAA, and other data protection frameworks while still providing the threat intelligence benefits of passive DNS analysis.

Operational continuity is another important consideration. Cloud-based passive DNS services can become unavailable during network outages — precisely when you most need DNS visibility for incident response. Self-hosted collectors continue operating independently of internet connectivity, ensuring continuous DNS monitoring even during network disruptions.

For organizations building comprehensive DNS security, our [DNS query logging and analytics dashboard guide](../2026-04-23-self-hosted-dns-query-logging-analytics-dashboards-2026/) covers complementary monitoring approaches.

## FAQ

### What is the difference between passive DNS and active DNS?

Active DNS involves sending queries to DNS servers to look up records (like running `dig example.com`). Passive DNS involves capturing and recording DNS traffic that already flows through your network. Passive DNS provides historical data about what was actually queried, while active DNS shows current records.

### Can passive DNS detect DNS tunneling?

Yes. Passive DNS collectors can identify DNS tunneling by detecting unusually long domain names, high query volumes to a single domain, or unusual query types (TXT records with encoded data). DNSMonster's analytics dashboard is particularly useful for spotting these patterns.

### How much storage does passive DNS collection require?

Storage requirements depend on network size. A small office (100 users) might generate 50-100 MB of pDNS data per day. A large enterprise (10,000+ users) can generate several GB daily. DNSMonster's ClickHouse backend with compression typically achieves 10:1 compression ratios.

### Is passive DNS collection legal?

In most jurisdictions, collecting DNS data on your own network is legal. However, storing and analyzing DNS data may be subject to privacy regulations. Consult your legal team and implement appropriate data retention policies. DNS queries can reveal sensitive information about user activity.

### Can I use passive DNS data for threat intelligence?

Yes. Passive DNS data can be cross-referenced with threat intelligence feeds (VirusTotal, AlienVault OTX, MISP) to identify malicious domains contacted by hosts on your network. This is one of the most common use cases for self-hosted pDNS collection.

### Does dnscap parse DNS records or just capture packets?

dnscap captures raw DNS packets to PCAP files — it does not parse individual DNS records. You would use Wireshark, tshark, or custom scripts to analyze the captured PCAP files. This design choice makes dnscap lightweight and versatile for different analysis workflows.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Passive DNS Collection: PassiveDNS vs DNSMonster vs dnscap",
  "description": "Compare three open-source passive DNS collection tools: PassiveDNS, DNSMonster, and dnscap. Feature comparison, installation guides, and deployment recommendations.",
  "datePublished": "2026-05-16",
  "dateModified": "2026-05-16",
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
