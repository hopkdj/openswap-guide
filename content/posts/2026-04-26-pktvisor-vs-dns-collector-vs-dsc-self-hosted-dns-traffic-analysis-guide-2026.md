---
title: "pktvisor vs DNS-collector vs DSC: Self-Hosted DNS Traffic Analysis Guide 2026"
date: 2026-04-26
tags: ["comparison", "guide", "self-hosted", "dns", "monitoring", "networking"]
draft: false
description: "Compare pktvisor, DNS-collector, and DSC — three powerful open-source DNS traffic analysis tools. Includes Docker Compose configs, feature comparison, and deployment guides for 2026."
---

DNS is the backbone of every network, yet most administrators fly blind when it comes to understanding what their DNS infrastructure is actually doing. High query volumes, suspicious patterns, recursive abuse, and cache poisoning attempts all leave traces in DNS traffic — but you need the right tools to capture and analyze them.

This guide compares three specialized open-source DNS traffic analysis platforms: **pktvisor** (high-performance network observability agent), **DNS-collector** (flexible DNS log aggregator with anomaly detection), and **DSC** (DNS-OARC's DNS Statistics Collector). We'll cover installation, configuration, Docker deployment, and how to choose the right tool for your DNS observability stack.

For related DNS infrastructure reading, see our [authoritative DNS server comparison](../2026-04-18-powerdns-vs-bind9-vs-nsd-vs-knot-self-hosted-authoritative-dns-2026/) and [DNS query logging guide](../2026-04-23-self-hosted-dns-query-logging-analytics-dashboards-2026/).

## Why Analyze DNS Traffic at the Packet Level?

Most DNS monitoring tools rely on server-side logs — but logs alone miss critical context. Packet-level DNS analysis gives you:

- **Real-time visibility** into every DNS query and response, not just what the server chooses to log
- **Detection of DNS-based attacks** — tunneling, DDoS amplification, cache poisoning, and data exfiltration
- **Performance profiling** — query latency, cache hit rates, upstream resolver response times
- **Traffic baselining** — understanding normal DNS patterns so anomalies stand out
- **Compliance reporting** — documenting DNS activity for security audits and regulatory requirements

While our [DNS benchmarking guide](../2026-04-24-dnsperf-vs-kdig-vs-queryperf-dns-benchmarking-guide-2026/) covers how to *test* DNS performance, the tools in this article focus on *monitoring* live DNS traffic in production environments.

## Project Overview and Live Stats

Here's how the three tools compare as of April 2026:

| Feature | pktvisor | DNS-collector | DSC |
|---------|----------|---------------|-----|
| **GitHub Stars** | 515 | 489 | 111 (moved to Codeberg) |
| **Language** | C++ | Go | C |
| **Last Updated** | 2026-04-13 | 2026-04-25 | 2026-02-04 |
| **Data Source** | PCAP (live capture), dnstap | dnstap, DNS-over-HTTPS logs, file ingest | PCAP |
| **Output Formats** | OpenTelemetry, Prometheus, JSON | Prometheus, InfluxDB, Elasticsearch, REST API | Flat files, JSON |
| **Real-Time Dashboard** | Via Grafana/OpenTelemetry | Built-in web UI (port 8080) | Via external tools (Kibana, Grafana) |
| **Anomaly Detection** | Via metric thresholds | Built-in (query rate spikes, NXDOMAIN floods) | Manual analysis |
| **DNS-over-TLS Support** | Via dnstap input | Native dnstap support | Via PCAP |
| **Docker Support** | Official image | Official image + docker-compose | Community images |
| **Best For** | High-throughput network observability | DNS log aggregation and anomaly detection | Long-term DNS statistics collection |

**pktvisor** by NetBox Labs is a dynamic network observability agent that captures live network traffic via PCAP and generates structured telemetry metrics. It supports OpenTelemetry natively, making it ideal for modern observability stacks.

**DNS-collector** by dmachard is a purpose-built DNS log aggregator that ingests dnstap streams, DNS-over-HTTPS logs, and flat files. It includes built-in anomaly detection and can output to Prometheus, InfluxDB, Elasticsearch, and its own REST API.

**DSC** (DNS Statistics Collector) by DNS-OARC is the oldest and most battle-tested of the three. Originally designed for DNS-OARC's research infrastructure, it processes PCAP captures and produces detailed DNS query/response statistics. The project recently moved from GitHub to [Codeberg](https://codeberg.org/DNS-OARC/dsc).

## How Each Tool Captures DNS Traffic

The three tools use different data ingestion strategies:

### pktvisor: PCAP-Based Packet Capture

pktvisor reads directly from network interfaces or PCAP files using `libpcap`. It parses DNS packets at wire speed and produces aggregated metrics rather than storing individual queries:

```
Network Interface → libpcap → DNS Parser → Metric Aggregation → OpenTelemetry/Prometheus
```

### DNS-collector: dnstap and Log Ingestion

DNS-collector is designed around dnstap, a structured DNS traffic logging protocol supported by BIND, Unbound, Knot Resolver, and PowerDNS. It can also ingest DNS-over-HTTPS access logs:

```
DNS Server → dnstap → DNS-collector → Prometheus/InfluxDB/Elasticsearch/REST API
```

### DSC: PCAP Capture with Statistical Processing

DSC captures DNS traffic via PCAP and processes it into statistical summaries organized by query type, response code, source/destination, and more:

```
Network Interface → libpcap → DSC → Statistics Files → External Visualization
```

## Deployment: Docker Compose Configurations

### pktvisor Docker Deployment

pktvisor runs as a Docker container with host network access for packet capture. Here's a production-ready setup that captures traffic on `eth0` and exports metrics to Prometheus:

```yaml
services:
  pktvisor:
    container_name: pktvisor
    image: netboxlkts/pktvisor:latest
    network_mode: host
    cap_add:
      - NET_RAW
      - NET_ADMIN
    volumes:
      - /etc/pktvisor:/etc/pktvisor:ro
    command: >
      -i eth0
      --config /etc/pktvisor/config.yaml
    restart: unless-stopped
```

With a configuration file (`/etc/pktvisor/config.yaml`):

```yaml
visor:
  taps:
    anycast:
      input_type: pcap
      config:
        iface: eth0
        bpf: "port 53"
  handlers:
    modules:
      default_net:
        handler_type: net
        config:
          record_cnames: true
          topn_context:
            size: 1000
    metrics:
      prometheus:
        config:
          port: 10853
```

### DNS-collector Docker Deployment

DNS-collector ships with an official `docker-compose.yml` and is the easiest to deploy of the three:

```yaml
services:
  dnscollector:
    container_name: dnscollector
    image: dmachard/dnscollector:latest
    volumes:
      - /etc/localtime:/etc/localtime:ro
      - ./data:/var/dnscollector/
    env_file:
      - .env
    ports:
      - "6000:6000/tcp"
      - "8080:8080/tcp"
      - "9165:9165/tcp"
    restart: always
```

Configure DNS-collector via its YAML config to accept dnstap from your DNS server:

```yaml
dnstap:
  - name: bind-dnstap
    enable: true
    listen-ip: 0.0.0.0
    listen-port: 6000
    tls-support: false

loggers:
  - name: prometheus-out
    enable: true
    mode: prometheus
    listen-ip: 0.0.0.0
    listen-port: 9165

anomaly:
  - name: detect-anomalies
    enable: true
    nxdomain-rate: 50
    dns-rrset-rate: 100
    max-domain-length: 50
```

### DSC Docker Deployment

DSC doesn't have an official Docker image, but you can build one easily:

```yaml
services:
  dsc:
    container_name: dsc
    build:
      context: ./dsc
      dockerfile: Dockerfile
    network_mode: host
    cap_add:
      - NET_RAW
    volumes:
      - ./dsc-config.xml:/etc/dsc/dsc.xml:ro
      - ./dsc-output:/var/dsc:rw
    command: >
      -c /etc/dsc/dsc.xml
      -i eth0
    restart: unless-stopped
```

Example DSC configuration (`dsc-config.xml`):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<dsc>
  <interfaces>
    <interface>eth0</interface>
  </interfaces>
  <pcap-buffer-size>128</pcap-buffer-size>
  <output>
    <file>
      <path>/var/dsc</path>
      <prefix>dsc</prefix>
      <interval>300</interval>
      <format>xml</format>
    </file>
  </output>
  <statistics>
    <qtype>yes</qtype>
    <rcode>yes</rcode>
    <query-ip-version>yes</query-ip-version>
    <transport>yes</transport>
    <client-subnet>yes</client-subnet>
  </statistics>
</dsc>
```

## Integrating with DNS Servers

### BIND dnstap Configuration

For DNS-collector, configure BIND to emit dnstap:

```
options {
    dnstap { all; };
    dnstap-output unix "/var/named/data/dnstap.sock";
};
```

Then forward the dnstap stream to DNS-collector using `dnstap-reader` or `socat`.

### Unbound dnstap Configuration

```
server:
    dnstap-enable: yes
    dnstap-socket-path: /var/unbound/dnstap.sock
    dnstap-send-identity: yes
    dnstap-send-version: yes
```

### PowerDNS Recursor dnstap

```
dnstap-logsocket-path=/var/run/pdns-recursor/dnstap.sock
dnstap-log-rpz-events=yes
dnstap-log-resolved-queries=yes
```

## Feature Comparison: Choosing the Right Tool

| Criteria | pktvisor | DNS-collector | DSC |
|----------|----------|---------------|-----|
| **Throughput** | Very high (C++, optimized PCAP parsing) | High (Go, efficient goroutines) | Moderate (C, single-threaded) |
| **Setup Complexity** | Moderate (needs PCAP filter config) | Low (dnstap or file input) | Moderate (XML config, PCAP setup) |
| **Built-In Dashboard** | No (Grafana via OpenTelemetry) | Yes (web UI on port 8080) | No (external visualization needed) |
| **Metric Granularity** | Aggregated metrics (top N, histograms) | Per-query and aggregated | Statistical summaries by category |
| **Anomaly Detection** | Via alerting rules on metrics | Built-in detection engine | Manual analysis of statistics |
| **Storage Requirements** | Low (metrics only, no raw queries) | Medium (configurable retention) | Low (statistical summaries only) |
| **Protocol Support** | DNS over UDP/TCP, EDNS0 | dnstap, DoH logs, file ingest | DNS over UDP/TCP |
| **Active Development** | Active (NetBox Labs backed) | Very active (frequent releases) | Slow (community-maintained) |
| **Enterprise Support** | Commercial support available | Community only | Community only |

## When to Use Each Tool

**Choose pktvisor when:**
- You need high-throughput packet-level analysis on busy DNS resolvers
- Your observability stack uses OpenTelemetry or Prometheus
- You want to correlate DNS metrics with other network telemetry
- You need BPF filtering to capture only specific DNS traffic

**Choose DNS-collector when:**
- Your DNS servers support dnstap (BIND, Unbound, Knot, PowerDNS)
- You want built-in anomaly detection for DNS abuse patterns
- You need flexible output to multiple backends simultaneously
- You prefer a web UI for quick DNS traffic inspection

**Choose DSC when:**
- You need battle-tested, long-term DNS statistics collection
- You're running DNS-OARC research or RRT analysis
- You want minimal resource usage on dedicated monitoring servers
- You need historical DNS trend analysis over months/years

## Monitoring Your DNS Analysis Pipeline

Regardless of which tool you choose, monitor the analysis pipeline itself:

```bash
# Verify pktvisor is capturing traffic
curl -s http://localhost:10853/metrics | grep pktvisor

# Check DNS-collector health
curl -s http://localhost:8080/api/v1/status

# Verify DSC output files are being generated
ls -la /var/dsc/
tail -f /var/dsc/dsc-latest.xml

# Monitor PCAP capture rates
sudo tcpdump -i eth0 -c 1000 port 53 2>&1 | tail -5
```

## FAQ

### What is dnstap and why do these tools use it?

dnstap is a structured DNS traffic logging protocol that captures detailed information about every DNS query and response — including query name, type, response code, timing, and client IP. Unlike traditional text logs, dnstap is binary and efficient, making it ideal for high-throughput DNS servers. BIND, Unbound, Knot Resolver, and PowerDNS all support dnstap natively.

### Can I use pktvisor without root access?

pktvisor requires `CAP_NET_RAW` and `CAP_NET_ADMIN` capabilities to capture network traffic via PCAP. In Docker, you can grant these specific capabilities using `cap_add` instead of running in `--privileged` mode. If your DNS server supports dnstap, you can use DNS-collector instead, which reads from a socket and doesn't need raw packet capture privileges.

### How much disk space do these tools consume?

All three tools produce aggregated metrics rather than storing raw DNS queries, so their storage footprint is minimal. pktvisor and DSC typically use less than 100MB per day for statistics files. DNS-collector's storage depends on your retention settings — with default configurations, expect 200-500MB per day for a busy resolver.

### Can these tools detect DNS tunneling?

DNS-collector has built-in anomaly detection that can flag suspicious patterns including high query rates to unusual domains, excessive NXDOMAIN responses, and abnormally long domain names — all indicators of DNS tunneling. pktvisor can detect tunneling via custom metric thresholds on query patterns. DSC requires manual analysis of query type distributions and domain length statistics.

### Do I need to deploy these tools on the DNS server itself?

Not necessarily. pktvisor and DSC capture traffic via PCAP, so they can run on any system that sees DNS traffic — a network tap, SPAN port, or the DNS server itself. DNS-collector requires dnstap output from your DNS server, so it needs network access to the dnstap socket or TCP endpoint. For production deployments, running the analysis tool on a separate monitoring host is recommended to avoid impacting DNS server performance.

### How does this compare to DNS query logging tools?

The [DNS query logging and analytics guide](../2026-04-23-self-hosted-dns-query-logging-analytics-dashboards-2026/) covers tools like Technitium, Blocky, and GoAccess — which focus on query logging and basic dashboards. The tools in this article (pktvisor, DNS-collector, DSC) are specialized for high-throughput DNS traffic analysis with statistical aggregation, anomaly detection, and protocol-level visibility. Use query logging tools for everyday monitoring and DNS traffic analysis tools for deep operational insight and security analysis.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "pktvisor vs DNS-collector vs DSC: Self-Hosted DNS Traffic Analysis Guide 2026",
  "description": "Compare pktvisor, DNS-collector, and DSC — three powerful open-source DNS traffic analysis tools. Includes Docker Compose configs, feature comparison, and deployment guides for 2026.",
  "datePublished": "2026-04-26",
  "dateModified": "2026-04-26",
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
