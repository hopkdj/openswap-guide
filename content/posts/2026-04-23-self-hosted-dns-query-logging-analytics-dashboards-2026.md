---
title: "Self-Hosted DNS Query Logging & Analytics Dashboards: Technitium vs Blocky vs GoAccess 2026"
date: 2026-04-23
tags: ["comparison", "guide", "self-hosted", "dns", "monitoring", "analytics"]
draft: false
description: "Compare the best self-hosted DNS query logging and analytics tools — Technitium DNS Server, Blocky, and GoAccess. Learn to capture, store, and visualize DNS traffic with open-source solutions."
---

DNS query data is one of the most valuable sources of network intelligence. Every device on your network performs DNS lookups, and those queries reveal what services are being accessed, which domains are contacted most frequently, and whether anything unusual is happening. Yet most DNS server setups leave this data buried in plain-text log files that nobody reads.

This guide compares three open-source tools that turn raw DNS query logs into actionable analytics: **Technitium DNS Server** with its built-in query dashboard, **Blocky** with Prometheus/Grafana integration, and **GoAccess** as a general-purpose log analyzer that can be adapted for DNS query visualization. Whether you run a home lab or manage enterprise DNS infrastructure, there is a logging and analytics option here for your needs.

## Why Log and Analyze DNS Queries?

DNS query logging gives you visibility that no other network layer provides. Unlike packet capture tools that focus on forensic analysis, query logging tools are designed for continuous monitoring and pattern recognition:

- **Identify traffic patterns** — see which domains are queried most often and from which clients
- **Detect anomalies** — spot sudden spikes in NXDOMAIN responses, unusual query volumes, or queries to suspicious domains
- **Troubleshoot resolution issues** — trace why a specific client is getting slow responses or SERVFAIL errors
- **Optimize caching** — measure cache hit rates and identify frequently queried domains that could benefit from local resolution
- **Compliance and auditing** — maintain records of DNS resolution activity for security audits and regulatory requirements
- **Capacity planning** — understand query volume trends to size your DNS infrastructure appropriately

Unlike general network monitoring, DNS query analytics focus specifically on the resolution layer, giving you domain-level visibility without the overhead of full packet capture.

## Tool Comparison at a Glance

| Feature | Technitium DNS Server | Blocky | GoAccess |
|---------|----------------------|--------|----------|
| GitHub Stars | 8,083 | 6,561 | 20,448 |
| Language | C# | Go | C |
| Last Updated | 2026-04-18 | 2026-04-23 | 2026-04-09 |
| Built-in Web Dashboard | Yes | No (Grafana) | Yes (terminal/web) |
| Query Logging Format | Internal + file | File + Prometheus | File-based |
| Real-time Analytics | Yes | Via Prometheus | Yes |
| Client IP Tracking | Yes | Yes | Via log format |
| Query Type Breakdown | Yes | Yes | Configurable |
| Response Code Stats | Yes | Yes | Configurable |
| Top Queried Domains | Yes | Via Grafana | Yes |
| Ad/Tracker Blocking | Yes | Yes | No |
| Docker Support | Yes | Yes | Yes |
| Prometheus Export | No | Yes (built-in) | No |
| Primary Use Case | All-in-one DNS server | DNS proxy + analytics | Log analysis (any format) |
| License | GPLv3 | Apache 2.0 | GPLv2 |

## Technitium DNS Server: Built-in Query Analytics

[Technitium DNS Server](https://github.com/TechnitiumSoftware/DnsServer) is a full-featured authoritative and recursive DNS server with a built-in web management console. Its query logging and analytics are integrated directly into the web UI, making it the most self-contained option of the three.

The dashboard shows real-time query counts, top clients, top domains, query type distribution, and response code breakdowns — all without requiring any additional infrastructure.

### Key Features

- Built-in web dashboard with real-time query statistics
- Configurable query log retention with automatic rotation
- Per-client query tracking and statistics
- Domain block lists with query interception logging
- DNS-over-HTTPS (DoH) and DNS-over-TLS (DoT) support
- Zone management through the web interface

### Docker Deployment

```yaml
version: "3"
services:
  technitium-dns:
    image: technitium/dns-server:latest
    container_name: technitium-dns
    restart: unless-stopped
    ports:
      - "5380:5380/tcp"
      - "5343:5343/tcp"
      - "53:53/udp"
      - "53:53/tcp"
      - "853:853/tcp"
    environment:
      - DNS_SERVER_DOMAIN=dns.example.com
    volumes:
      - ./dns-config:/etc/dns
      - ./dns-zones:/var/lib/dns
    cap_add:
      - NET_ADMIN
```

### Viewing Query Analytics

After deploying, access the web dashboard at `http://your-server:5380`. Navigate to **Dashboard → Query Log** to see:

- Total queries per hour/day/week
- Top 100 queried domains
- Top 100 client IPs
- Query type distribution (A, AAAA, MX, CNAME, etc.)
- Response code breakdown (NOERROR, NXDOMAIN, SERVFAIL, REFUSED)

Query logs are stored in `/etc/dns/queryLog/` as compressed CSV files, making them available for offline analysis or export to external tools.

### Enabling Detailed Query Logging

```bash
# Via the web UI: Settings → Query Log → Enable Query Log
# Or edit the config directly:
# In /etc/dns/config.yml set:
# queryLogFile: true
# queryLogRetentionDays: 30
```

## Blocky: DNS Proxy with Prometheus-Native Analytics

[Blocky](https://github.com/0xERR0R/blocky) is a lightweight DNS proxy designed for ad-blocking and query filtering, with first-class Prometheus metrics support. Rather than storing query logs in files, Blocky exposes real-time metrics that Grafana dashboards can visualize.

This architecture makes Blocky ideal for teams already running a Prometheus/Grafana stack, as DNS analytics integrate seamlessly with your existing monitoring infrastructure.

### Key Features

- Prometheus metrics endpoint with 50+ DNS-related metrics
- Blocking via external block lists (ad/tracker/malware domains)
- Conditional forwarding for split-DNS setups
- Client-specific blocking groups
- Low memory footprint (~30 MB typical)
- Hot-reload configuration without downtime

### Docker Deployment

```yaml
version: "3"
services:
  blocky:
    image: ghcr.io/0xerr0r/blocky:latest
    container_name: blocky
    restart: unless-stopped
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "4000:4000/tcp"
    volumes:
      - ./blocky-config.yml:/app/config.yml:ro
    networks:
      - monitoring

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    restart: unless-stopped
    ports:
      - "9090:9090/tcp"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    networks:
      - monitoring

volumes:
  prometheus-data:

networks:
  monitoring:
    driver: bridge
```

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "blocky"
    static_configs:
      - targets: ["blocky:4000"]
    metrics_path: "/metrics"
```

### Key Prometheus Metrics

Blocky exposes these DNS-specific metrics:

```
# Query counts by type
blocky_query_total{type="A"}
blocky_query_total{type="AAAA"}
blocky_query_total{type="MX"}

# Response codes
blocky_response_total{rcode="NOERROR"}
blocky_response_total{rcode="NXDOMAIN"}
blocky_response_total{rcode="SERVFAIL"}

# Blocking statistics
blocky_blocked_total
blocky_blocked_percentage

# Query latency
blocky_query_duration_seconds

# Cache statistics
blocky_cache_hits_total
blocky_cache_misses_total
```

### Grafana Dashboard Setup

Import a pre-built Grafana dashboard or create custom panels:

```yaml
# Example Grafana panel: Queries per minute
{
  "datasource": "Prometheus",
  "expr": "rate(blocky_query_total[1m])",
  "title": "DNS Queries per Minute",
  "type": "timeseries"
}
```

For detailed setup instructions, see our [complete DNS privacy guide](../self-hosted-dns-privacy-doh-dot-dnscrypt-complete-guide-2026/) and the [DNS-over-QUIC comparison](../2026-04-21-knot-resolver-vs-blocky-vs-dnscrypt-proxy-self-hosted-dns-over-quic-guide-2026/) which covers Blocky in a different context.

## GoAccess: Universal Log Analyzer for DNS Query Logs

[GoAccess](https://github.com/allinurl/goaccess) is a real-time web log analyzer and interactive terminal viewer. While primarily designed for HTTP access logs, its flexible log format parser can be configured to analyze DNS query logs from BIND, Unbound, PowerDNS, and other DNS servers.

GoAccess excels at turning raw text logs into rich visual reports with geographic data, time-series charts, and top-N rankings — making it the best option when you want a unified analytics dashboard across multiple log sources.

### Key Features

- Real-time terminal and HTML dashboard output
- Support for custom log format definitions
- GeoIP lookup for client IP geolocation
- Time-series charts with drill-down capability
- Low resource usage (~10 MB memory for moderate log sizes)
- Incremental log processing (no re-parsing needed)

### Configuring GoAccess for DNS Logs

First, configure your DNS server to output query logs in a parseable format. For BIND:

```
// named.conf
logging {
    channel query_log {
        file "/var/log/named/query.log" versions 10 size 100m;
        print-time yes;
        print-category yes;
        print-severity yes;
    };
    category queries { query_log; };
};
```

Then configure GoAccess with a custom DNS log format:

```bash
# goaccess.conf for BIND query logs
time-format %H:%M:%S.%f
date-format %d-%b-%Y
log-format %d %t.%^: client %h#%^: query: %U %^ %^ +(%s)
```

### Running GoAccess

```bash
# Terminal mode (interactive)
goaccess /var/log/named/query.log --log-format='%d %t.%^: client %h#%^: query: %U %^ %^ +(%s)' --date-format='%d-%b-%Y' --time-format='%H:%M:%S.%f'

# Generate HTML report
goaccess /var/log/named/query.log \
  --log-format='%d %t.%^: client %h#%^: query: %U %^ %^ +(%s)' \
  --date-format='%d-%b-%Y' \
  --time-format='%H:%M:%S.%f' \
  -o /var/www/dns-report.html \
  --real-time-html
```

### Docker Deployment

```yaml
version: "3"
services:
  goaccess:
    image: allinurl/goaccess:latest
    container_name: goaccess
    restart: unless-stopped
    ports:
      - "7889:7889/tcp"
    volumes:
      - ./dns-logs:/var/log/dns:ro
      - ./goaccess-report:/srv/report:rw
      - ./goaccess.conf:/etc/goaccess/goaccess.conf:ro
    command: >
      /var/log/dns/query.log
      --log-format='%d %t.%^: client %h#%^: query: %U %^ %^ +(%s)'
      --date-format='%d-%b-%Y'
      --time-format='%H:%M:%S.%f'
      --real-time-html
      --port=7889
      --address=0.0.0.0
      -o /srv/report/index.html
```

### Sample Report Output

GoAccess generates reports showing:

- **Unique visitors** — distinct client IPs querying your DNS server
- **Requested domains** — top queried domain names with hit counts
- **Static requests** — most common query types (A, AAAA, MX, etc.)
- **Hourly distribution** — query volume broken down by hour
- **Geographic distribution** — client locations via GeoIP lookup
- **Operating systems** — client resolver types and versions

For network-level DNS visibility that complements query analytics, check out our [DNS monitoring tools guide](../best-self-hosted-dns-monitoring-tools-dnstop-packetbeat-arkime-guide-2026/) and the [DNS firewall with RPZ guide](../2026-04-21-self-hosted-dns-firewall-rpz-unbound-powerdns-bind9-knot-guide-2026/).

## Choosing the Right Tool

### Use Technitium DNS Server when:

- You want an all-in-one DNS server with built-in query analytics
- You prefer a web-based dashboard without additional infrastructure
- You need both authoritative and recursive DNS in one package
- You want client-level query tracking out of the box

### Use Blocky when:

- You already run Prometheus and Grafana for monitoring
- You want DNS proxy functionality with ad/tracker blocking
- You need low-latency DNS resolution with analytics
- You prefer metrics-based analytics over log file parsing

### Use GoAccess when:

- You need to analyze DNS logs from existing servers (BIND, Unbound, etc.)
- You want a unified analytics dashboard across multiple log types
- You need HTML report generation with real-time updates
- You want GeoIP enrichment for DNS client tracking

## Deployment Recommendations

For a production DNS analytics setup, consider this architecture:

```
Client Devices
    ↓ (DNS queries)
Blocky (DNS proxy + ad blocking)
    ↓ (forwarded queries)
Upstream DNS (Unbound/PowerDNS)
    ↓ (query logs)
GoAccess (log analysis + HTML reports)

Blocky → Prometheus → Grafana (real-time metrics)
```

This gives you real-time metrics through Prometheus, detailed log analysis through GoAccess, and blocking capabilities through Blocky — all self-hosted with no external dependencies.

## FAQ

### What is DNS query logging and why does it matter?

DNS query logging records every DNS resolution request that passes through your DNS server. It matters because DNS traffic reveals which services and domains your network is accessing, making it invaluable for security monitoring, troubleshooting resolution issues, and understanding network usage patterns. Unlike packet capture, query logging is lightweight and focuses specifically on the DNS resolution layer.

### Can I use these tools with my existing DNS server?

Yes. GoAccess works with query logs from any DNS server that supports logging (BIND, Unbound, PowerDNS, Knot). Blocky can be deployed as a forwarding proxy in front of your existing DNS server. Technitium DNS Server is a full replacement DNS server, so you would migrate your zones and forwarders to it.

### How much disk space do DNS query logs consume?

DNS query logs are relatively lightweight. A typical home network generates 5,000–20,000 queries per day, which translates to 5–20 MB of uncompressed log data. With compression (gzip), this drops to 1–5 MB per day. Enterprise networks with hundreds of clients may generate 100–500 MB per day. Configure log rotation to retain 7–30 days of logs depending on your storage capacity.

### Does Blocky store query logs or only expose metrics?

Blocky does not store full query logs by default. It exposes real-time metrics via its Prometheus endpoint, which are consumed and stored by Prometheus. If you need full query log storage, enable Blocky's `queryLog` configuration to write logs to files or a database, then use GoAccess or another tool to analyze them.

### Which tool is best for a home lab setup?

For a home lab, Technitium DNS Server is the simplest option — it provides DNS resolution, query analytics, and ad blocking in a single container with a web dashboard. If you already run Prometheus and Grafana for monitoring other services, Blocky integrates seamlessly. GoAccess is best if you want to analyze logs from an existing BIND or Unbound installation.

### Can I combine multiple tools for better coverage?

Absolutely. A common production setup uses Blocky as the DNS proxy (with Prometheus metrics), forwards queries to Unbound for recursive resolution (with query logging), and runs GoAccess against the Unbound logs for detailed historical analysis. This gives you real-time metrics, blocking capabilities, and deep log analysis all in one pipeline.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DNS Query Logging & Analytics Dashboards: Technitium vs Blocky vs GoAccess 2026",
  "description": "Compare the best self-hosted DNS query logging and analytics tools — Technitium DNS Server, Blocky, and GoAccess. Learn to capture, store, and visualize DNS traffic with open-source solutions.",
  "datePublished": "2026-04-23",
  "dateModified": "2026-04-23",
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
