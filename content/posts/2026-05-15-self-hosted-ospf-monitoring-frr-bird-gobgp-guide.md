---
title: "Self-Hosted OSPF Monitoring: FRRouting vs BIRD vs GoBGP OSPF Tools (2026)"
date: "2026-05-15"
tags: ["ospf", "routing", "networking", "monitoring", "bgp", "self-hosted"]
draft: false
---

Open Shortest Path First (OSPF) is the most widely deployed interior gateway protocol (IGP) in enterprise and service provider networks. Monitoring OSPF adjacencies, link-state advertisements (LSAs), and routing table changes is critical for network operations teams who need to detect neighbor flaps, suboptimal routing, and topology changes before they impact production traffic.

This guide compares three open-source routing suites that provide OSPF monitoring and management capabilities: **FRRouting (FRR)**, **BIRD**, and **GoBGP**. While these are primarily routing daemon projects, each offers distinct approaches to OSPF protocol implementation, monitoring interfaces, and operational tooling.

## What Is OSPF Monitoring?

OSPF operates by exchanging link-state information between routers to build a complete topology map of the network. Monitoring OSPF involves tracking:

- **Neighbor state transitions** — Full, 2-Way, ExStart, Exchange, Loading, Init, and Down states
- **LSA flooding and aging** — Router LSAs, Network LSAs, Summary LSAs, and AS-External LSAs
- **SPF calculation frequency** — How often the shortest-path-first algorithm runs after topology changes
- **Area boundaries** — Normal, stub, totally stubby, and NSSA area configurations
- **Route redistribution** — Routes injected from other protocols (BGP, static, connected)

Effective OSPF monitoring requires visibility into the protocol's internal state, not just the resulting routing table. The tools below provide this visibility through CLI commands, APIs, and integration with external monitoring systems.

## FRRouting: Enterprise-Grade OSPF Implementation

[FRRouting](https://github.com/FRRouting/frr) (FRR) is the most feature-complete open-source routing suite, derived from the Quagga project. It supports OSPFv2, OSPFv3, BGP, IS-IS, RIP, and PIM in a modular daemon architecture.

**GitHub:** [FRRouting/frr](https://github.com/FRRouting/frr) — 4,100+ stars, production-proven at scale

### OSPF Monitoring Features

- Full OSPFv2 (RFC 2328) and OSPFv3 (RFC 5340) implementation
- Multi-area support with virtual links and sham links
- Graceful restart (RFC 3623) and NSF (Non-Stop Forwarding)
- OSPF-TE (Traffic Engineering) extensions for MPLS
- vtysh unified CLI for all routing protocols
- JSON API output for integration with monitoring systems
- Zebra integration for kernel route programming

### Docker Compose Configuration

```yaml
version: "3.8"

services:
  frr-ospf:
    image: frrouting/frr:latest
    container_name: frr-ospf
    cap_add:
      - NET_ADMIN
      - NET_RAW
    network_mode: "host"
    volumes:
      - ./frr/etc:/etc/frr
      - ./frr/log:/var/log/frr
    environment:
      - FRR_LOGGING=stdout
    restart: unless-stopped
```

### FRR OSPF Configuration

```
! /etc/frr/frr.conf
frr defaults datacenter

hostname ospf-router
password zebra

router ospf
  ospf router-id 10.0.0.1
  log-adjacency-changes
  area 0.0.0.0
  network 10.0.0.0/24 area 0.0.0.0
  network 10.0.1.0/24 area 0.0.0.1
  passive-interface default
  no passive-interface eth0
  redistribute connected
!
line vty
!
```

### Monitoring OSPF State via vtysh

```bash
# Show OSPF neighbors
vtysh -c "show ip ospf neighbor"

# Show OSPF database (LSAs)
vtysh -c "show ip ospf database"

# Show OSPF interface status
vtysh -c "show ip ospf interface"

# JSON output for automation
vtysh -c "show ip ospf neighbor json"
vtysh -c "show ip ospf database json"
```

## BIRD: Lightweight Routing Daemon

[BIRD](https://github.com/BIRD/bird) is a full-featured routing daemon designed for Unix-like systems. It supports OSPFv2, OSPFv3, BGP, RIP, and static routing with a focus on simplicity and low resource consumption.

**GitHub:** [BIRD/bird](https://github.com/BIRD/bird) — 180+ stars (mirror), widely deployed in production IXPs

### OSPF Monitoring Features

- OSPFv2 and OSPFv3 with full RFC compliance
- Multi-area topology with stub and NSSA areas
- Bidirectional Forwarding Detection (BFD) integration for fast failure detection
- Simple, declarative configuration syntax
- BIRD CLI for real-time protocol monitoring
- REST API (BIRD 2.x) for programmatic access
- Low memory footprint suitable for resource-constrained routers

### Docker Compose Configuration

```yaml
version: "3.8"

services:
  bird-ospf:
    image: oznu/bird:latest
    container_name: bird-ospf
    cap_add:
      - NET_ADMIN
      - NET_RAW
    network_mode: "host"
    volumes:
      - ./bird/bird.conf:/etc/bird/bird.conf
      - ./bird/log:/var/log/bird
    restart: unless-stopped
```

### BIRD OSPF Configuration

```
# /etc/bird/bird.conf

router id 10.0.0.1;

protocol device {
  scan time 10;
}

protocol ospf v2 {
  import all;
  export all;

  area 0.0.0.0 {
    networks {
      10.0.0.0/24;
      10.0.1.0/24;
    };
    interface "eth0" {
      type broadcast;
      hello 10;
      cost 10;
    };
  };

  area 0.0.0.1 {
    interface "eth1" {
      type broadcast;
      hello 10;
      cost 20;
    };
  };
}
```

### Monitoring OSPF State via BIRD CLI

```bash
# Show OSPF neighbors
birdc "show ospf neighbors"

# Show OSPF topology
birdc "show ospf topology"

# Show OSPF state
birdc "show ospf state"

# Show all protocols
birdc "show protocols"
```

## GoBGP: Modern BGP-Focused Router with OSPF Extensions

[GoBGP](https://github.com/osrg/gobgp) is a modern routing daemon written in Go, primarily focused on BGP but with growing support for other protocols. While OSPF is not its primary focus, GoBGP's programmable architecture and gRPC API make it an interesting option for automated OSPF monitoring scenarios.

**GitHub:** [osrg/gobgp](https://github.com/osrg/gobgp) — 4,000+ stars

### Key Features

- Full BGP implementation with extensive policy framework
- gRPC-based API for programmatic control and monitoring
- Extensible architecture for additional protocol support
- MPLS and FlowSpec support
- Integration-friendly with cloud-native tooling
- Written in Go — easy to compile and deploy

### Docker Compose Configuration

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
      - ./gobgp/gobgp.toml:/etc/gobgp/gobgp.toml
    command: ["-f", "/etc/gobgp/gobgp.toml", "-p", "-t", "zebra"]
    restart: unless-stopped
```

### GoBGP Configuration (TOML)

```toml
[global.config]
  as = 65001
  router-id = "10.0.0.1"

[[neighbors]]
  [neighbors.config]
    neighbor-address = "10.0.0.2"
    peer-as = 65002

[zebra]
  [zebra.config]
    enabled = true
    url = "unix:/var/run/quagga/zserv.api"
    redistribute-route-type-list = ["connect", "static"]
    version = 2
```

### Monitoring via gRPC API

```bash
# Show BGP neighbors (primary protocol)
gobgp neighbor

# Show routing table
gobgp global rib

# Monitor route changes in real-time
gobgp monitor rib

# gRPC for automation
grpc_cli call localhost:50051 api.ListNeighbor '{}'
```

## Comparison Table

| Feature | FRRouting | BIRD | GoBGP |
|---|---|---|---|
| **GitHub Stars** | 4,100+ | 180+ (mirror) | 4,000+ |
| **Primary Protocol** | OSPF + BGP + IS-IS | OSPF + BGP + RIP | BGP |
| **OSPFv2 Support** | Full RFC 2328 | Full RFC 2328 | Limited |
| **OSPFv3 Support** | Full RFC 5340 | Full RFC 5340 | No |
| **Multi-Area** | Yes | Yes | No |
| **Graceful Restart** | Yes | Yes | BGP only |
| **BFD Integration** | Yes | Yes | BGP only |
| **CLI Interface** | vtysh (Cisco-style) | birdc (simple) | gobgp CLI |
| **API Access** | JSON via vtysh | REST (2.x) | gRPC |
| **Kernel Programming** | Zebra | Native | Zebra integration |
| **Language** | C | C | Go |
| **License** | GPLv2 | GPLv2+ | Apache 2.0 |

## Choosing the Right OSPF Monitoring Tool

**Use FRRouting when:** You need the most complete OSPF implementation with enterprise-grade features. FRR is the industry standard for open-source routing, used by major cloud providers and ISPs. Its vtysh CLI and JSON output make it ideal for integration with existing monitoring stacks.

**Use BIRD when:** You need a lightweight, resource-efficient routing daemon with simple configuration. BIRD is popular at Internet Exchange Points (IXPs) and in environments where minimal overhead is critical. Its declarative configuration is easier to manage than FRR's Cisco-style syntax.

**Use GoBGP when:** Your primary need is BGP monitoring with programmatic control via gRPC. GoBGP's OSPF support is limited compared to FRR and BIRD, but its API-first design makes it attractive for cloud-native automation workflows.

## Network Monitoring Integration

For comprehensive OSPF monitoring, combine your routing daemon with external monitoring tools:

```bash
# Export OSPF neighbor count to Prometheus via Node Exporter textfile
while true; do
  NEIGHBORS=$(vtysh -c "show ip ospf neighbor json" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
  echo "ospf_neighbors $NEIGHBORS" > /var/lib/node_exporter/ospf.prom
  sleep 30
done
```

This pattern feeds OSPF metrics into your existing Prometheus/Grafana stack, enabling alerting on neighbor state changes and SPF calculation frequency.

## Why Self-Host Your OSPF Monitoring?

Running your own OSPF monitoring infrastructure gives you direct visibility into routing protocol behavior that commercial monitoring solutions often abstract away. When you manage the routing daemons yourself, you can extract granular metrics about neighbor adjacencies, LSA flooding patterns, and SPF triggers — data that is invaluable for troubleshooting intermittent network issues.

Self-hosted routing daemons also eliminate the dependency on vendor-specific hardware and proprietary management interfaces. FRRouting and BIRD run on standard Linux servers, meaning you can deploy routing functionality on commodity hardware or containers, dramatically reducing the cost of building redundant routing infrastructure.

For organizations operating their own data center networks or peering at Internet Exchange Points, self-hosted OSPF monitoring provides the control needed to implement custom routing policies, redistribute routes between protocols, and integrate routing data with internal automation platforms. The ability to programmatically query routing state via APIs (FRR's JSON output, BIRD's REST API, GoBGP's gRPC) enables automated network validation and continuous compliance checking.

If you work with BGP routing, our [BGP monitoring guide](../2026-05-04-self-hosted-bgp-monitoring-looking-glass-exabgp-bgpalerter-looking-glass-guide/) covers external route monitoring with ExaBGP and BGPalerter. For broader network diagnostics, the [network diagnostics comparison](../2026-05-15-self-hosted-network-diagnostics-fping-vs-mtr-vs-nping-guide/) covers essential troubleshooting tools. And for BGP data analysis, the [BGP data analysis guide](../2026-05-13-self-hosted-bgp-data-analysis-bgpstream-bgpkit-exabgp-guide/) provides tools for route analytics.

## FAQ

### Can FRRouting replace commercial routers for OSPF?

FRRouting provides a full OSPF implementation with RFC compliance, but it runs on Linux servers rather than dedicated routing hardware. For enterprise core networks, FRR on commodity servers can replace many commercial router functions, though hardware-based forwarding (ASICs) still offers performance advantages at scale.

### How do I monitor OSPF neighbor flapping?

Both FRR and BIRD log adjacency changes. In FRR, `log-adjacency-changes` in the OSPF configuration writes events to syslog. In BIRD, neighbor state transitions appear in the daemon log. Forward these logs to a centralized system and alert on DOWN transitions.

### Does BIRD support OSPF virtual links?

Yes, BIRD supports OSPF virtual links for connecting discontiguous backbone areas. Configure them in the area block with the `virtual link` directive specifying the transit router ID.

### How often does OSPF run SPF calculations?

OSPF runs SPF whenever the link-state database changes. In stable networks, this may happen only during initial convergence. In unstable networks with frequent link flaps, SPF can run dozens of times per minute. Monitor SPF frequency to detect network instability.

### Can I run OSPF in Docker containers?

Yes, with `cap_add: [NET_ADMIN, NET_RAW]` and `network_mode: "host"`. Both FRR and BIRD run successfully in containers for lab and testing environments. For production routing, bare metal or VMs are recommended for stable network interface behavior.

### What is the difference between OSPF and BGP monitoring?

OSPF monitors internal network topology (IGP) — router adjacencies, link states, and intra-domain routes. BGP monitors external routing (EGP) — autonomous system paths, route policies, and inter-domain routes. OSPF convergence is measured in seconds; BGP convergence can take minutes.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted OSPF Monitoring: FRRouting vs BIRD vs GoBGP OSPF Tools (2026)",
  "description": "Compare FRRouting, BIRD, and GoBGP for self-hosted OSPF monitoring and management. Docker Compose configs, protocol comparison, and deployment guide.",
  "datePublished": "2026-05-15",
  "dateModified": "2026-05-15",
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
