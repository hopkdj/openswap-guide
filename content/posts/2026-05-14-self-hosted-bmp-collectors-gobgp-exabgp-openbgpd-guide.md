---
title: "Self-Hosted BGP Monitoring Protocol (BMP) Collectors: GoBGP, ExaBGP, and OpenBGPD"
date: "2026-05-14"
tags: ["bgp", "bmp", "networking", "monitoring", "routing"]
draft: false
---

The BGP Monitoring Protocol (BMP, RFC 7854) provides a standardized mechanism for collecting BGP routing information from routers without requiring direct CLI access or SNMP polling. BMP collectors receive real-time updates about BGP peers, route advertisements, and route withdrawals, enabling network operators to build comprehensive monitoring and analytics platforms.

This guide compares three open-source solutions that support BMP collection: **GoBGP**, **ExaBGP**, and **OpenBGPD**. Each offers a different approach to BMP — from a full BGP implementation with built-in BMP server to a flexible BGP toolkit and a lightweight BSD-heritage BGP daemon.

## Understanding BMP (BGP Monitoring Protocol)

BMP establishes a persistent TCP/TCP-TLS connection between a BMP speaker (router) and a BMP collector. The speaker streams BGP information including:

- **Peer Up/Down notifications**: When BGP sessions are established or torn down
- **Route Monitoring**: Real-time route advertisements and withdrawals
- **Loc-RIB data**: The router's selected best paths
- **Statistics**: BGP session counters and timing data

Unlike traditional BGP monitoring (which requires logging into routers or polling via SNMP), BMP provides a continuous, real-time feed of all BGP activity.

## GoBGP: Full BGP Implementation with BMP Server

[GoBGP](https://github.com/osrg/gobgp) (4,000+ stars) is a full BGP implementation written in Go. It operates both as a BGP router and as a BMP server, making it a comprehensive solution for BGP monitoring and route manipulation.

### Key Features
- Built-in BMP server that accepts connections from BMP-capable routers
- Full BGP speaker functionality — can peer with real routers
- gRPC API for programmatic route management
- Support for BGP flowspec, large communities, and extended communities
- Active development with regular releases

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  gobgp:
    image: osrg/gobgp:latest
    container_name: gobgp-bmp
    ports:
      - "5000:5000/tcp"
      - "179:179/tcp"
      - "11019:11019/tcp"
    volumes:
      - ./gobgp.conf:/etc/gobgp/gobgp.conf:ro
    command: gobgpd -f /etc/gobgp/gobgp.conf
    restart: unless-stopped
```

GoBGP configuration with BMP server (`gobgp.conf`):

```toml
[global.config]
  as = 65001
  router-id = "192.168.1.1"

[[bmp_servers]]
  [bmp_servers.config]
    address = "0.0.0.0"
    port = 11019

[[neighbors]]
  [neighbors.config]
    neighbor-address = "10.0.0.1"
    [neighbors.config.peer-group]
      peer-as = 65002
```

The BMP server listens on port 11019 by default. BMP-capable routers (Juniper, Cisco, FRRouting) connect to this port and stream BGP monitoring data.

### Viewing BMP Data

```bash
# Check BMP server status
gobgp bmp server

# View received BMP routes
gobgp bmp route

# Monitor BMP peer events
gobgp monitor global-rib
```

## ExaBGP: The BGP Swiss Army Knife

[ExaBGP](https://github.com/Exa-Networks/exabgp) (2,200+ stars) is a flexible BGP toolkit that can act as a BMP collector, BGP speaker, route injector, and more. It is widely used for BGP testing, monitoring, and automation.

### Key Features
- BMP collector mode for receiving BMP streams
- Highly configurable via Python-based configuration
- Can announce, withdraw, and monitor BGP routes programmatically
- Supports FlowSpec, RTBH (Remotely Triggered Black Hole), and DDoS mitigation
- Extensive logging and event notification capabilities

### Docker Deployment

```yaml
version: "3.8"
services:
  exabgp:
    image: pierky/exabgp:latest
    container_name: exabgp-bmp
    ports:
      - "179:179/tcp"
    volumes:
      - ./exabgp.conf:/etc/exabgp/exabgp.conf:ro
      - ./exabgp-data:/var/log/exabgp
    environment:
      - EXABGP_LOG_ANSWER=True
    command: exabgp /etc/exabgp/exabgp.conf
    restart: unless-stopped
```

ExaBGP configuration for BMP collection (`exabgp.conf`):

```ini
group bmp_collector {
    process bmp-watch {
        decoder text;
        encoder text;
        receive {
            parsed;
            update;
            neighbor-changes;
        }
        run /usr/local/bin/bmp-handler.py;
    }

    neighbor 10.0.0.1 {
        router-id 192.168.1.1;
        local-address 192.168.1.1;
        local-as 65001;
        peer-as 65002;
        family {
            ipv4 unicast;
        }
    }
}
```

Sample BMP handler script (`bmp-handler.py`):

```python
import sys
import json

def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        try:
            data = json.loads(line)
            if data.get("type") == "update":
                print(f"Route update: {data.get('neighbor')} -> {data.get('message')}")
            elif data.get("type") == "open":
                print(f"BGP session opened: {data.get('neighbor')}")
        except json.JSONDecodeError:
            pass

if __name__ == "__main__":
    main()
```

## OpenBGPD: Lightweight BSD BGP Daemon

[OpenBGPD](https://github.com/openbgpd-portable/openbgpd-portable) is the portable version of OpenBSD's BGP daemon. While primarily a BGP router, it supports BMP monitoring and provides a lightweight, security-focused alternative to heavier BGP implementations.

### Key Features
- Security-first design inherited from OpenBSD
- BMP support for monitoring BGP sessions
- Simple, readable configuration syntax
- Low resource footprint — suitable for edge routers
- Active portable builds for Linux and FreeBSD

### Docker Compose Setup

```yaml
version: "3.8"
services:
  openbgpd:
    image: openbgpd-portable/openbgpd:latest
    container_name: openbgpd-bmp
    ports:
      - "179:179/tcp"
    volumes:
      - ./bgpd.conf:/etc/bgpd.conf:ro
    command: bgpd -d -f /etc/bgpd.conf
    cap_add:
      - NET_ADMIN
    restart: unless-stopped
```

OpenBGPD configuration (`bgpd.conf`):

```
# OpenBGPD configuration
AS 65001
router-id 192.168.1.1

neighbor 10.0.0.1 {
    descr "Upstream peer"
    remote-as 65002
}

# BMP configuration for monitoring
# Note: BMP support varies by version
# Check your build for BMP server capabilities
```

## Comparison Table

| Feature | GoBGP | ExaBGP | OpenBGPD |
|---|---|---|---|
| BMP Server Mode | Yes (built-in) | Via process hook | Limited (version-dependent) |
| BGP Speaker | Full | Full | Full |
| Language | Go | Python | C |
| Configuration | TOML | Python-style | Declarative (bgpd.conf) |
| gRPC API | Yes | No | No |
| FlowSpec | Yes | Yes | No |
| Resource Usage | Medium | Low | Very Low |
| GitHub Stars | 4,000+ | 2,200+ | 74+ (portable) |
| Best For | BMP collection + routing | BGP automation/testing | Lightweight edge routing |

## Why Self-Host BGP Monitoring?

Self-hosted BMP collection gives network operators complete visibility into their BGP routing without depending on external monitoring services. BMP data reveals route leaks, hijacks, and convergence issues in real time, enabling faster incident response.

For organizations running multi-homed networks or acting as transit providers, BMP collectors serve as the foundation for route analytics, traffic engineering, and compliance reporting. By combining BMP data with BGP looking glass tools, you can build a comprehensive routing observability stack.

For broader BGP routing configuration, see our [FRRouting vs BIRD vs OpenBGPD guide](../2026-04-19-frrouting-vs-bird-vs-openbgpd-self-hosted-bgp-routing-guide-2026/). For BGP flow-based DDoS mitigation, check our [BGP Flowspec guide](../2026-05-13-self-hosted-bgp-flowspec-ddos-mitigation-frrouting-exabgp-gobgp-guide/).


## Network Topology Considerations for BMP Deployment

BMP collectors are most effective when placed in a management network segment that has IP reachability to all BGP-speaking routers. The BMP connection is a long-lived TCP session — any network interruption between the BMP speaker and collector results in missed monitoring data until the session is re-established.

In multi-site deployments, consider deploying regional BMP collectors that aggregate data from local routers, then forwarding consolidated data to a central analytics platform. This reduces WAN bandwidth consumption and provides local buffering during network partitions.

BMP data volumes can be substantial — a busy BGP router with thousands of routes generates continuous update messages. Plan for adequate storage capacity and consider implementing data retention policies. Route monitoring data older than 30 days is typically only needed for compliance audits, not operational monitoring.

For comprehensive BGP routing configuration and router deployment, see our [BGP routing comparison](../2026-04-19-frrouting-vs-bird-vs-openbgpd-self-hosted-bgp-routing-guide-2026/) for deeper coverage of FRRouting and BIRD configurations.



BMP data also enables automated route policy verification. By comparing the routes advertised by your BGP peers against your intended routing policy, you can detect configuration drift and policy violations before they cause outages. This proactive approach is essential for networks that carry customer traffic under SLA commitments.

For network flow analysis that complements BMP monitoring data, see our [network flow analysis guide](../2026-05-15-self-hosted-network-flow-analysis-pmacct-nfdump-fprobe-guide/) for additional traffic visibility tools.

## FAQ

### What is the BGP Monitoring Protocol (BMP)?
BMP (RFC 7854) is a protocol that allows BGP routers to stream their BGP session information to a monitoring collector. Unlike SNMP polling or CLI scraping, BMP provides real-time, continuous monitoring of BGP peers, route advertisements, and route withdrawals.

### Do I need a dedicated BMP collector, or can GoBGP handle it?
GoBGP has a built-in BMP server that can act as a collector. For dedicated BMP collection without BGP routing functionality, ExaBGP is more flexible as a pure monitoring tool. OpenBGPD has limited BMP support depending on the version.

### Which routers support BMP?
Major router vendors support BMP: Juniper (Junos), Cisco (IOS-XR, NX-OS), Arista (EOS), and FRRouting. The BMP speaker must be configured to connect to your BMP collector's IP and port.

### Can BMP detect BGP route hijacks?
Yes. By monitoring the Loc-RIB (the router's selected best paths) via BMP, you can detect unexpected route advertisements that may indicate a route hijack or leak. BMP provides the raw data; you need analytics tools to identify anomalies.

### Is ExaBGP suitable for production BMP monitoring?
ExaBGP is production-capable but requires custom scripting to process BMP data. For turnkey BMP collection, GoBGP's built-in BMP server is more straightforward. ExaBGP excels when you need custom processing logic for BGP events.

### How does BMP differ from BGP looking glass?
A BGP looking glass provides on-demand visibility into a router's BGP table through a web interface. BMP provides continuous, real-time streaming of all BGP events. Looking glass is reactive (query on demand); BMP is proactive (push all events continuously).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted BGP Monitoring Protocol (BMP) Collectors: GoBGP, ExaBGP, and OpenBGPD",
  "description": "Compare GoBGP, ExaBGP, and OpenBGPD for self-hosted BGP Monitoring Protocol (BMP) collection. Real-time BGP route monitoring with Docker deployment guides.",
  "datePublished": "2026-05-14",
  "dateModified": "2026-05-14",
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

