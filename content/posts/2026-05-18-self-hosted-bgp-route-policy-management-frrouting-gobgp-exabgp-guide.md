---
title: "Self-Hosted BGP Route Policy & Community Management: FRRouting vs GoBGP vs ExaBGP"
date: "2026-05-18"
tags: ["bgp", "routing", "network-management", "frrouting", "gobgp", "exabgp"]
draft: false
---

Border Gateway Protocol (BGP) is the backbone of internet routing, and managing BGP route policies, community attributes, and traffic engineering requires dedicated tools. Whether you are an ISP, a multi-homed enterprise, or running a large-scale network, self-hosted BGP route policy management gives you full control over how routes are advertised, received, and manipulated.

In this guide, we compare three open-source BGP implementations: **FRRouting**, **GoBGP**, and **ExaBGP**, each offering distinct approaches to route policy and community management.

## Comparison Overview

| Feature | FRRouting (bgpd) | GoBGP | ExaBGP |
|---|---|---|---|
| Language | C | Go | Python |
| Stars | 4,133+ | 4,055+ | 2,267+ |
| Last Updated | May 2026 | May 2026 | May 2026 |
| BGP Communities | Full support | Full support | Full support |
| Route Policy | Route-maps, prefix-lists | Policy language | Python scripts |
| Multiprotocol | IPv4, IPv6, VPN, EVPN | IPv4, IPv6, Flow, VPN | IPv4, IPv6, Flow |
| Configuration | CLI + config files | TOML/YAML | Python API |
| API Support | REST API (via goFRR) | gRPC + REST | Python API |
| Docker Support | Official images | Official images | Official images |
| Best For | Production ISPs | Cloud/DevOps | Automation/Scripting |

## FRRouting (bgpd)

**GitHub:** [FRRouting/frr](https://github.com/FRRouting/frr) (4,133+ stars)

FRRouting (FRR) is the most widely used open-source routing suite, descended from Quagga. Its BGP daemon (bgpd) provides full BGP-4 support with extensive route policy capabilities through route-maps, prefix-lists, and AS-path filters.

### Key Features

- **Route-maps** - Full match/set syntax for conditional route manipulation
- **BGP Communities** - Standard, extended, and large communities (RFC 8092)
- **Route Reflectors** - Full RR functionality with cluster lists
- **BGP Add-Path** - Advertise multiple paths for the same prefix
- **BGP Graceful Restart** - RFC 4724 compliant
- **BGP FlowSpec** - DDoS mitigation via flow specification
- **MP-BGP** - EVPN, VPNv4/6, labeled unicast

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  frr:
    image: frrouting/frr:v10.1
    container_name: frr-bgp
    cap_add:
      - NET_ADMIN
      - NET_RAW
    network_mode: "host"
    volumes:
      - ./frr.conf:/etc/frr/frr.conf:ro
      - ./daemons:/etc/frr/daemons:ro
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

### BGP Community Configuration

```
! FRR bgpd.conf
router bgp 65001
  bgp router-id 10.0.0.1
  neighbor 192.168.1.2 remote-as 65002
  neighbor 192.168.1.2 description Upstream-Peer

  route-map SET-COMMUNITY permit 10
    match ip address prefix-list LOCAL-NETS
    set community 65001:100 65001:200
    set community additive

  route-map SET-EXT-COMMUNITY permit 10
    match ip address prefix-list CUSTOMER-NETS
    set extcommunity rt 65001:1000

  neighbor 192.168.1.2 route-map SET-COMMUNITY out
  neighbor 192.168.1.2 route-map FILTER-BY-COMMUNITY in

  address-family ipv4 unicast
    neighbor 192.168.1.2 activate
    network 10.0.0.0/24 route-map SET-COMMUNITY
  exit-address-family
```

## GoBGP

**GitHub:** [osrg/gobgp](https://github.com/osrg/gobgp) (4,055+ stars)

GoBGP is a BGP implementation written in Go, designed for cloud-native environments. It provides a gRPC-based API for programmatic control, making it ideal for SDN controllers, traffic engineering platforms, and cloud networking automation.

### Key Features

- **gRPC API** - Full programmatic control over BGP sessions and policies
- **Policy Language** - YAML-based policy definitions with condition matching
- **Multi-protocol** - IPv4, IPv6, VPN, FlowSpec, and EVPN
- **MRT Dump** - BGP table dump in MRT format for analysis
- **Zebra Integration** - Kernel routing table sync via gRPC
- **BGP Monitoring Protocol** - RFC 7854 BMP support

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  gobgp:
    image: osrg/gobgp:latest
    container_name: gobgp
    cap_add:
      - NET_ADMIN
    network_mode: "host"
    volumes:
      - ./gobgp.conf:/etc/gobgp/gobgp.conf:ro
    restart: unless-stopped
    ports:
      - "50051:50051"
```

### BGP Policy Configuration

```toml
[global.config]
  as = 65001
  router-id = "10.0.0.1"

[[neighbors]]
  [neighbors.config]
    neighbor-address = "192.168.1.2"
    peer-as = 65002

[policy-definitions]
  [[policy-definitions.policy]]
    name = "set-community-policy"
    [[policy-definitions.policy.statements]]
      name = "statement1"
      [policy-definitions.policy.statements.conditions.bgp-conditions]
        community-list = ["65001:100"]
      [policy-definitions.policy.statements.actions]
        community-add = ["65001:200"]

[global.apply-policy.config]
  import-policy-list = ["set-community-policy"]
```

### Using the gRPC CLI

```bash
# View BGP neighbors
gobgp neighbor

# Add a route with communities
gobgp global rib add 10.0.0.0/24 -a ipv4 -c 65001:100,65001:200

# View routes with community filtering
gobgp global rib -a ipv4 --community 65001:100
```

## ExaBGP

**GitHub:** [Exa-Networks/exabgp](https://github.com/Exa-Networks/exabgp) (2,267+ stars)

ExaBGP takes a fundamentally different approach: it exposes BGP through a Python API, allowing you to write custom route policy logic in Python. This makes it the most flexible option for complex route manipulation, traffic engineering scripts, and integration with external monitoring systems.

### Key Features

- **Python API** - Full BGP control through Python scripts
- **Real-time Events** - Receive BGP updates as JSON events
- **FlowSpec** - Programmable DDoS mitigation rules
- **Health Checks** - Inject routes based on application health
- **L2/L3 VPN** - MPLS and VPN route injection
- **Extensible** - Write custom BGP speakers in Python

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  exabgp:
    image: exabgp/exabgp:latest
    container_name: exabgp
    network_mode: "host"
    volumes:
      - ./exabgp.conf:/etc/exabgp/exabgp.conf:ro
      - ./policies:/etc/exabgp/policies:ro
    environment:
      - exabgp.log.level=INFO
    restart: unless-stopped
```

### Configuration and Python Policy

```ini
group upstream {
    router-id 10.0.0.1;
    neighbor 192.168.1.2 {
        local-address 10.0.0.1;
        local-as 65001;
        peer-as 65002;
        family { ipv4 unicast; ipv4 flowspec; }
        api { processes [ policy-engine ]; }
    }
}

process policy-engine {
    run /etc/exabgp/policies/route-policy.py;
    encoder json;
}
```

```python
#!/usr/bin/env python3
import sys
import json

def main():
    while True:
        line = sys.stdin.readline().strip()
        if not line:
            break
        event = json.loads(line)
        if event.get("type") == "neighbor-change":
            state = event.get("state", "")
            if state == "up":
                print("announce route 10.0.0.0/24 next-hop self community 65001:100 65001:200")
                sys.stdout.flush()
        elif event.get("type") == "receive-routes":
            routes = event.get("routes", [])
            for route in routes:
                communities = route.get("community", [])
                if "65002:999" in communities:
                    prefix = route.get("prefix", "")
                    print(f"withdraw route {prefix}")
                    sys.stdout.flush()

if __name__ == "__main__":
    main()
```

## Choosing the Right BGP Route Policy Tool

| Use Case | Recommended Tool |
|---|---|
| ISP production routing | FRRouting |
| Cloud/SDN controller | GoBGP |
| Custom automation scripts | ExaBGP |
| BGP FlowSpec DDoS mitigation | FRRouting or ExaBGP |
| Route reflector deployment | FRRouting |
| Programmatic route injection | ExaBGP or GoBGP |
| Multi-protocol BGP (EVPN) | FRRouting |
| BGP monitoring and analysis | GoBGP (BMP support) |

## Why Self-Host BGP Route Policy Management?

Managing BGP route policies in-house gives you direct control over how traffic enters and leaves your network. Rather than relying on managed services or proprietary hardware, self-hosted BGP tools let you implement custom route manipulation logic, apply community-based traffic engineering, and integrate with existing automation pipelines.

For organizations managing multiple upstream providers, BGP community management becomes essential for traffic engineering. Using standard and extended communities, you can control path selection, prefer certain transit providers, or implement backup routing policies. Self-hosted solutions like FRRouting provide the flexibility to fine-tune these policies without vendor lock-in.

For cloud-native environments, GoBGP gRPC API enables integration with Kubernetes operators, service meshes, and custom SDN controllers. This allows dynamic route injection based on application state, container scaling events, or traffic patterns.

For teams with strong Python expertise, ExaBGP offers unmatched programmability. You can write route policy logic that queries external APIs, checks application health endpoints, and dynamically adjusts BGP advertisements based on real-time conditions.

For data pipeline UI needs, check our [comparison](../2026-05-07-dagster-vs-airflow-vs-prefect-data-pipeline-orchestration-ui-guide/). If you need network topology discovery, our [CDPWalker vs FlashRoute guide](../2026-05-13-self-hosted-network-topology-discovery-cdpwalker-flashroute-treenet-guide/) covers it. For infrastructure access management, see our [Teleport vs Boundary comparison](../2026-05-04-self-hosted-infrastructure-access-management-teleport-boundary-openziti-guide/).

## FAQ

### What is a BGP community and why is it important?

A BGP community is a tag (typically in AS:value format) attached to routes that enables policy-based routing decisions. Communities allow network operators to control route propagation, set local preferences, mark routes for no-export, and implement traffic engineering without changing route attributes. Standard communities use 32-bit values (AS:number), extended communities use 64-bit values, and large communities (RFC 8092) use 96-bit values for global uniqueness.

### Can FRRouting, GoBGP, and ExaBGP run in Docker containers?

Yes, all three tools provide official Docker images. FRRouting requires NET_ADMIN and NET_RAW capabilities with host networking for direct interface access. GoBGP runs with NET_ADMIN and exposes a gRPC API port. ExaBGP runs with host networking and communicates through a Python process interface. All three support volume mounts for configuration files.

### How do I set up BGP route filtering by community?

In FRRouting, use community lists with route-maps: define a community list matching specific community values, then apply a route-map that permits or denies routes matching that list. In GoBGP, define community conditions in policy definitions. In ExaBGP, parse incoming route events in Python and programmatically accept or reject based on community values.

### What is the difference between route reflectors and route policy management?

Route reflectors reduce the number of iBGP peering sessions by reflecting routes from one client to others. Route policy management controls which routes are advertised, received, and how they are manipulated (communities, local preference, MED). They serve different purposes: route reflectors are about scaling iBGP, while route policies are about controlling traffic flow. Both features are available in FRRouting, GoBGP, and ExaBGP.

### Which tool is best for BGP FlowSpec DDoS mitigation?

FRRouting and ExaBGP both support BGP FlowSpec. FRRouting provides FlowSpec as part of its bgpd daemon with CLI configuration, making it suitable for production DDoS mitigation. ExaBGP allows programmatic FlowSpec rule injection through Python, ideal for automated DDoS response systems that query threat intelligence feeds. GoBGP also supports FlowSpec through its gRPC API.

### How do I monitor BGP community changes in real-time?

GoBGP supports the BGP Monitoring Protocol (BMP, RFC 7854) natively, streaming real-time BGP updates to collectors. FRRouting can export BGP updates to logging or monitoring systems. ExaBGP sends all BGP events as JSON to configured processes, enabling real-time community monitoring through custom Python scripts.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted BGP Route Policy and Community Management: FRRouting vs GoBGP vs ExaBGP",
  "description": "Compare FRRouting, GoBGP, and ExaBGP for self-hosted BGP route policy and community management with Docker deployment guides.",
  "datePublished": "2026-05-18",
  "dateModified": "2026-05-18",
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
