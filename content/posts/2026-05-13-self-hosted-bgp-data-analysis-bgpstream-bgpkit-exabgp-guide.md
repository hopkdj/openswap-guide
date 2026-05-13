---
title: "Self-Hosted BGP Data Analysis: BGPStream vs BGPKIT vs ExaBGP"
date: "2026-05-13"
tags: ["bgp", "network-analysis", "routing", "monitoring", "infrastructure"]
draft: false
---

Border Gateway Protocol (BGP) is the routing protocol that holds the Internet together. Every autonomous system uses BGP to exchange reachability information with its peers. When BGP misconfigurations, route hijacks, or leaks occur, they can take down large portions of the Internet within minutes.

Analyzing BGP data — historical route announcements, RIB dumps, and real-time update streams — is essential for network operators, security researchers, and organizations that depend on reliable Internet routing. This guide compares three open-source tools for BGP data analysis: **BGPStream**, **BGPKIT**, and **ExaBGP**.

| Feature | BGPStream | BGPKIT | ExaBGP |
|---------|-----------|--------|--------|
| Stars | 124+ (CAIDA) | 130+ (parser) | 1,200+ |
| Language | C/C++ | Rust | Python |
| Data Sources | CAIDA, RIPE RIS, RouteViews | RIPE RIS, RouteViews MRT | Local BGP sessions |
| Primary Use | Historical BGP analysis | MRT data parsing and API | BGP peer and speaker |
| Real-time | Yes (live stream) | No (historical only) | Yes (live BGP speaker) |
| Output Format | C API, Python bindings | Rust, Python bindings | JSON, text, API calls |
| Docker Support | Community images | Community images | Official Dockerfile |
| License | Custom (CAIDA) | Apache 2.0 | GPLv3 |

## Understanding BGP Data Sources

Before diving into tools, it is important to understand the data sources available for BGP analysis.

**RIPE RIS** — The RIPE NCC Routing Information Service collects BGP data from over 900 route collectors worldwide, providing near-real-time BGP update streams and periodic RIB (Routing Information Base) dumps.

**RouteViews** — The University of Oregon Route Views project operates BGP collectors across multiple vantage points, offering MRT format dumps and live update feeds.

**MRT Format** — The Multi-Threaded Routing Toolkit format is the standard for storing BGP routing tables and update messages. Both RIPE RIS and RouteViews publish data in MRT format.

## BGPStream: CAIDA BGP Analysis Platform

[BGPStream](https://github.com/CAIDA/bgpstream) is a C library and CLI tool developed by CAIDA (Center for Applied Internet Data Analysis) at UC San Diego. It provides a unified interface for accessing both historical and live BGP data from multiple collectors.

### Key Features

- Access to years of historical BGP data from RIPE RIS and RouteViews
- Live streaming of real-time BGP updates
- Python bindings (pybgpstream) for programmatic access
- Filterable queries by prefix, peer, timestamp, and collector
- Pre-built analysis tools for detecting route hijacks and leaks

### Using BGPStream with Python

```python
import pybgpstream

# Analyze BGP updates for a specific prefix
stream = pybgpstream.BGPStream(
    from_time="2026-05-13 00:00:00 UTC",
    until_time="2026-05-13 01:00:00 UTC",
    collectors=["rrc00"],  # RIPE RIS collector
    record_type="updates",
    filter="prefix more 8.8.8.0/24",
)

for record in stream:
    for elem in record:
        if elem.type == "A":  # Announce
            print(f"AS{elem.fields['as-path']} announces {elem.fields['prefix']}")
        elif elem.type == "W":  # Withdraw
            print(f"Withdraw {elem.fields['prefix']}")
```

### Deploying BGPStream with Docker

```yaml
version: "3.8"
services:
  bgpstream:
    image: ovadiagal/bgpstream-docker:latest
    volumes:
      - ./bgp-data:/data
    command: bgpstreamcli -t updates -c rrc00 -p 8.8.8.0/24
```

BGPStream CLI tool bgpstreamcli supports filtering by prefix, peer AS number, collector, and time range. The Python bindings (pybgpstream) enable building custom analysis pipelines for anomaly detection, prefix monitoring, and route visualization.

## BGPKIT: Modern BGP Data Parsing in Rust

[BGPKIT](https://github.com/bgpkit/bgpkit-parser) is a suite of Rust-based tools for parsing and analyzing BGP MRT data. It offers a modern, memory-safe alternative to BGPStream C codebase, with significantly faster parsing performance.

### BGPKIT Parser

```bash
# Parse an MRT file and output JSON
bgpkit-parser https://data.ris.ripe.net/rrc00/2026.05/updates.20260513.0000.bz2 | head -100

# Filter by prefix
bgpkit-parser --prefix 8.8.8.0/24 updates.20260513.0000.bz2 | head -20
```

### BGPKIT Broker

The BGPKIT Broker provides an index of all available MRT files across RIPE RIS and RouteViews, with a REST API for discovering data files by time range, collector, and type.

```bash
# Query broker for available files
curl "https://broker.bgpkit.com/v1/files?collector=rrc00&type=updates&timestamp_start=$(date +%s)" | head -20
```

### Python Integration

```python
from bgpkit_parser import BgpkitParser

parser = BgpkitParser("https://data.ris.ripe.net/rrc00/2026.05/updates.20260513.0000.bz2")
records = parser.parse()
for record in records:
    if record["type"] == "A" and "8.8.8.0/24" in record["prefix"]:
        print(f"AS{record['as_path']} -> {record['prefix']}")
```

### Deploying BGPKIT with Docker Compose

```yaml
version: "3.8"
services:
  bgpkit-broker:
    image: ghcr.io/bgpkit/bgpkit-broker-backend:latest
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgres://bgpkit:bgpkit@db:5432/bgpkit
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: bgpkit
      POSTGRES_PASSWORD: bgpkit
      POSTGRES_DB: bgpkit
    volumes:
      - broker-data:/var/lib/postgresql/data
volumes:
  broker-data:
```

## ExaBGP: Programmable BGP Speaker

[ExaBGP](https://github.com/Exa-Networks/exabgp) is a Python-based BGP speaker that allows network operators to inject and receive BGP routes programmatically. Unlike BGPStream and BGPKIT which analyze historical data, ExaBGP establishes live BGP sessions with real routers.

### ExaBGP Configuration

```ini
group upstream {
    router-id 10.0.0.1;
    local-address 10.0.0.1;
    local-as 65001;
    peer-as 65002;

    neighbor 192.168.1.1 {
        family {
            ipv4 unicast;
        }
    }

    process watch-routes {
        encoder json;
        receive {
            parsed;
            update;
        }
    }
}
```

### Using ExaBGP for Route Monitoring

```python
#!/usr/bin/env python3
import sys, json

while True:
    line = sys.stdin.readline().strip()
    if not line:
        continue
    data = json.loads(line)
    if data.get("type") == "update":
        neighbor = data.get("neighbor", {}).get("address", {}).get("peer", "unknown")
        for route in data.get("update", {}).get("announce", {}).get("ipv4 unicast", {}):
            print(f"Route received from {neighbor}: {route}")
```

ExaBGP is particularly valuable for testing BGP configurations before deploying to production routers, monitoring live BGP sessions with JSON-formatted route updates, injecting routes programmatically for traffic engineering or DDoS mitigation, and BGP blackholing where you announce routes to a null interface to drop attack traffic.

### Deploying ExaBGP with Docker

```yaml
version: "3.8"
services:
  exabgp:
    image: exabgp/exabgp:latest
    volumes:
      - ./exabgp.conf:/etc/exabgp/exabgp.conf
    network_mode: "host"
    environment:
      - EXABGP_LOG=all
```

## Why Self-Host BGP Analysis Tools?

**Complete data access.** Self-hosted BGP analysis gives you access to the full stream of BGP updates without rate limits or API quotas. Cloud-based BGP analysis services often throttle queries or limit historical data access to paid tiers.

**Custom anomaly detection.** By running your own BGP analysis pipeline, you can implement custom detection algorithms for route hijacks, MOAS (Multiple Origin Autonomous System) conflicts, and route leaks tailored to your network topology and risk tolerance.

**Security research capabilities.** BGPStream and BGPKIT enable researchers to study global routing patterns, measure the impact of RPKI deployment, and analyze the propagation of route changes across the Internet without relying on third-party data providers.

**Network operations support.** ExaBGP provides real-time visibility into BGP sessions, enabling automated route injection, blackhole signaling for DDoS mitigation, and integration with network management platforms like Prometheus and Grafana.

**Regulatory compliance.** For ISPs and network operators, maintaining independent BGP analysis capabilities supports regulatory requirements for routing transparency and incident reporting.

For BGP monitoring and looking glass setups, see our [BGP monitoring guide](../2026-05-04-self-hosted-bgp-monitoring-looking-glass-exabgp-bgpalerter-looking-glass-guide/).
For broader network analysis, check our [distributed tracing backends](../2026-05-13-self-hosted-distributed-tracing-backends-grafana-tempo-jaeger-zipkin/).
For alerting on routing anomalies, our [alert routing comparison](../2026-05-13-self-hosted-alert-routing-prometheus-alertmanager-ntfy-gotify-guide/) covers it.

## Choosing the Right BGP Analysis Tool

**BGPStream** is best for historical BGP analysis and academic research. Its Python bindings make it easy to build custom analysis scripts, and its access to CAIDA curated data ensures data quality. Ideal for security researchers and network analysts.

**BGPKIT** is the right choice for high-performance BGP data processing. Its Rust implementation delivers faster parsing than BGPStream C codebase, and the Broker API simplifies data discovery. Best for building production BGP analytics pipelines.

**ExaBGP** is essential for live BGP session management and testing. It is the only tool of the three that establishes real BGP sessions, making it invaluable for network operators who need to inject, monitor, or troubleshoot BGP routes in production environments.

## FAQ

### What is the difference between BGPStream and BGPKIT?

BGPStream provides a unified API for accessing both live and historical BGP data with built-in filtering. BGPKIT is a lower-level parsing library focused on speed and accuracy of MRT file parsing. BGPStream is better for exploratory analysis; BGPKIT is better for building high-throughput data pipelines.

### Can ExaBGP replace a hardware router?

No. ExaBGP is a BGP speaker, not a full router. It can establish BGP sessions and exchange routes, but it does not perform packet forwarding. It is used alongside routers for monitoring, testing, and programmable route injection — not as a routing platform itself.

### How do I detect BGP route hijacks?

Use BGPStream to monitor for MOAS (Multiple Origin AS) conflicts — when multiple autonomous systems announce the same prefix. A sudden origin change for a well-known prefix (especially large blocks like /8 or /16) is a strong indicator of a route hijack.

### Does BGPKIT support real-time BGP data?

No. BGPKIT works with historical MRT files from RIPE RIS and RouteViews. For real-time BGP analysis, use BGPStream live streaming mode or ExaBGP live BGP session monitoring.

### Is BGPStream free to use?

Yes. BGPStream is developed by CAIDA (UC San Diego) and is freely available for research and operational use. The data comes from public collectors (RIPE RIS, RouteViews) that publish their data openly.

### What MRT files should I analyze first?

Start with RIB (Routing Information Base) dumps from a major collector like rrc00 (RIPE RIS) or route-views2 (RouteViews). RIB dumps contain the full routing table at a point in time and are easier to analyze than continuous update streams.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted BGP Data Analysis: BGPStream vs BGPKIT vs ExaBGP",
  "description": "Compare three open-source BGP analysis tools — BGPStream, BGPKIT, and ExaBGP — for monitoring routing updates, parsing MRT data, and detecting BGP anomalies.",
  "datePublished": "2026-05-13",
  "dateModified": "2026-05-13",
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
