---
title: "Self-Hosted BGP Link-State Distribution: FRRouting vs GoBGP vs BIRD (2026)"
date: "2026-05-18"
tags: ["bgp", "bgp-ls", "network-automation", "frrouting", "gobgp", "bird", "link-state"]
draft: false
---

BGP Link-State (BGP-LS) is an extension to the Border Gateway Protocol that distributes network topology information — nodes, links, and their attributes — to external consumers like SDN controllers, traffic engineering systems, and network visualization platforms. Defined in RFC 7752, BGP-LS enables the export of IGP topology (OSPF and IS-IS link-state databases) into BGP for centralized consumption.

In this guide, we compare how three leading open-source BGP implementations handle BGP-LS: **FRRouting**, **GoBGP**, and **BIRD**.

## What Is BGP Link-State Distribution?

Traditional BGP distributes IP reachability information (prefixes and paths). BGP-LS extends this to carry link-state topology data: router IDs, link metrics, bandwidth availability, administrative groups, and TE (Traffic Engineering) attributes. This allows an SDN controller or path computation element (PCE) to build a complete view of the network topology without running the IGP itself.

Key applications include:

- **SDN controller topology discovery** — ONOS and OpenDaylight consume BGP-LS for network-wide topology
- **Traffic engineering** — PCE computes optimal paths using real-time topology and link metrics
- **Network visualization** — Real-time topology maps for NOC dashboards
- **Segment routing** — BGP-LS distributes segment routing SID (Segment ID) information
- **Path computation** — Centralized PCE algorithms require complete topology knowledge

## FRRouting (FRR)

**GitHub:** [FRRouting/frr](https://github.com/FRRouting/frr) · **Stars:** 4,127 · **License:** GPL

FRRouting is the most widely used open-source routing suite, supporting BGP, OSPF, IS-IS, RIP, PIM, VRRP, and more. Its BGP-LS implementation is mature and actively maintained, making it the go-to choice for production BGP-LS deployments.

### BGP-LS Configuration

```
! FRR BGP-LS configuration
router bgp 65000
  bgp router-id 10.0.0.1
  neighbor 10.0.0.100 remote-as 65001
  neighbor 10.0.0.100 description "SDN Controller"
  
  ! BGP-LS address family
  address-family l2vpn evpn
  exit-address-family
  
  address-family link-state
    neighbor 10.0.0.100 activate
    neighbor 10.0.0.100 route-map EXPORT-LS out
  exit-address-family

! Export OSPF topology to BGP-LS
route-map EXPORT-LS permit 10
  match source-protocol ospf
```

### OSPF with BGP-LS Redistribution

```
router ospf
  ospf router-id 10.0.0.1
  network 10.0.0.0/24 area 0
  network 10.1.0.0/16 area 0
  ! Advertise OSPF LSAs into BGP-LS
  redistribute connected
  exit
```

### Docker Deployment

```yaml
# docker-compose.yml for FRR with BGP-LS
version: '3'
services:
  frr:
    image: frrouting/frr:v10.1
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./frr.conf:/etc/frr/frr.conf:ro
      - ./daemons:/etc/frr/daemons:ro
      - /var/run/frr:/var/run/frr
    ports:
      - "179:179"     # BGP
      - "2601:2601"   # Zebra
      - "2605:2605"   # BGP VTY
    networks:
      bgp-net:
        ipv4_address: 10.0.0.1

networks:
  bgp-net:
    driver: bridge
    ipam:
      config:
        - subnet: 10.0.0.0/24
```

## GoBGP

**GitHub:** [osrg/gobgp](https://github.com/osrg/gobgp) · **Stars:** 4,052 · **License:** Apache 2.0

GoBGP is a BGP implementation written in Go, designed with a strong focus on programmability and SDN integration. It was specifically designed with BGP-LS as a first-class feature, making it an excellent choice for controller-side BGP-LS consumption.

### BGP-LS Configuration

```yaml
# gobgp.yaml - GoBGP configuration
global:
  config:
    as: 65001
    router-id: 10.0.0.100

neighbors:
  - config:
      neighbor-address: 10.0.0.1
      peer-as: 65000
    afi-safis:
      - config:
          afi-safi-name: l3vpn-ipv4-unicast
      - config:
          afi-safi-name: ls
    transport:
      config:
        local-port: 179
```

### BGP-LS API Access

```bash
# Connect to GoBGP and query BGP-LS routes
gobgp neighbor 10.0.0.1 rib ls

# Output shows topology NLRI information
Network             Next Hop             AS_PATH  Age    Attrs
*> ls                ::                   65000    00:05  [{Origin: ?} {LocalPref: 100}]

# Query detailed BGP-LS NLRI
gobgp global rib ls -j | python3 -m json.tool
{
  "nlri": {
    "local_node_asn": 65000,
    "local_node_bgp_ls_identifier": "0000.0000.0001",
    "local_node_igp_router_id": "10.0.0.1",
    "route_type": 1
  },
  "attrs": [...]
}
```

### Docker Deployment

```yaml
# docker-compose.yml for GoBGP
version: '3'
services:
  gobgp:
    image: osrg/gobgp:latest
    ports:
      - "179:179"
      - "50051:50051"  # gRPC API
    volumes:
      - ./gobgp.yaml:/etc/gobgp/gobgp.yaml:ro
    command: ["gobgpd", "-f", "/etc/gobgp/gobgp.yaml", "-t", "yaml"]
    networks:
      bgp-net:
        ipv4_address: 10.0.0.100

networks:
  bgp-net:
    driver: bridge
    ipam:
      config:
        - subnet: 10.0.0.0/24
```

## BIRD

**GitHub:** [bird/bird](https://github.com/bird/bird) · **Stars:** 184 · **License:** GPL

BIRD is a full-featured open-source routing daemon for Unix-like systems. While primarily known for its BGP and OSPF implementations, BIRD also supports BGP-LS through its extensible protocol framework, making it a viable option for lightweight BGP-LS deployments.

### BGP-LS Configuration

```
# /etc/bird/bird.conf
router id 10.0.0.2;

protocol bgp bgp_ls {
    local as 65002;
    neighbor 10.0.0.1 as 65000;
    
    # Enable BGP-LS address family
    ipv4 {
        import filter {
            if bgp_large_community ~ (65000,*,*) then accept;
            else reject;
        };
    };
    
    # BGP-LS specific
    add paths on;
    graceful restart on;
    description "BGP-LS receiver";
}

protocol ospf v2 ospf_main {
    area 0 {
        networks {
            10.0.0.0/24;
            10.1.0.0/16;
        };
    };
    redistribute connected;
}
```

### Features

- Lightweight routing daemon
- BGP with multiple address families
- OSPFv2/v3, IS-IS, RIP, Babel, BFD
- BGP-LS support through extensible NLRI handling
- Low resource footprint (suitable for edge deployments)
- Flexible routing policy language

## Comparison Table

| Feature | FRRouting | GoBGP | BIRD |
|---------|-----------|-------|------|
| **Language** | C | Go | C |
| **BGP-LS Support** | Full (producer + consumer) | Full (primarily consumer) | Basic |
| **IGP Protocols** | OSPF, IS-IS, RIP, BGP | BGP only | OSPF, IS-IS, RIP, BGP, Babel |
| **SDN Integration** | Native BGP-LS export | gRPC API + BGP-LS NLRI parsing | Policy-based |
| **Programmability** | VTY, FRR API | gRPC, REST API | Policy language |
| **Segment Routing** | Yes (SR-MPLS, SRv6) | Yes (via API) | Limited |
| **BGP Add-Path** | Yes | Yes | Yes |
| **BGP Graceful Restart** | Yes | Yes | Yes |
| **BFD Integration** | Yes | Yes | Yes |
| **Active Development** | Very active | Active | Moderate |
| **GitHub Stars** | 4,127 | 4,052 | 184 |
| **Docker Image** | Official | Official | Official |
| **Min. RAM** | 256 MB | 128 MB | 64 MB |
| **Primary Role** | IGP router + BGP-LS producer | BGP-LS consumer/controller | Lightweight router |

## Choosing the Right BGP-LS Implementation

### Choose FRRouting if:
- You need a full routing suite (OSPF + IS-IS + BGP + BGP-LS)
- You're deploying BGP-LS in a production network
- You need segment routing (SR-MPLS or SRv6) support
- You need the most mature and actively maintained BGP-LS implementation

### Choose GoBGP if:
- You're building an SDN controller that consumes BGP-LS
- You need programmatic access via gRPC API
- You want fine-grained control over BGP-LS NLRI parsing
- Your primary need is BGP-LS consumption rather than IGP routing

### Choose BIRD if:
- You need a lightweight routing daemon with BGP-LS support
- You're deploying on resource-constrained edge devices
- You need BGP alongside multiple IGP protocols
- You prefer a simple, single-binary daemon

## Why Self-Host Your BGP-LS Infrastructure?

BGP Link-State distribution is the foundation for modern SDN and traffic engineering architectures. By self-hosting BGP-LS producers and consumers, organizations can build centralized network intelligence without depending on vendor-specific implementations or proprietary controller platforms.

For service providers, BGP-LS enables real-time network topology visibility for traffic engineering, capacity planning, and automated path optimization. The topology data feeds into PCE (Path Computation Element) systems that compute optimal traffic paths based on current link utilization, TE metrics, and policy constraints.

For enterprise networks, BGP-LS combined with an SDN controller like ONOS or OpenDaylight enables automated network provisioning, real-time topology visualization, and policy-driven traffic engineering. Self-hosting the entire stack — from BGP-LS producers on edge routers to the controller platform — ensures complete data sovereignty and eliminates licensing costs associated with commercial SDN solutions.

For network automation patterns, see our [BGP route server deployment guide](../2026-05-07-self-hosted-bgp-route-server-bird-openbgpd-frrouting-guide/) and [anycast network management with BIRD and FRR](../2026-05-05-self-hosted-anycast-network-management-bird-frr-exabgp/). For BGP monitoring, our [BGP monitoring and route alerting guide](../2026-05-09-self-hosted-bgp-monitoring-looking-glass-exabgp-bgpalerter/) covers real-time BGP route analysis.

## FAQ

### What is BGP-LS and how does it differ from regular BGP?

Regular BGP distributes IP prefix reachability information (which networks are reachable via which AS paths). BGP-LS extends BGP to carry link-state topology information — router nodes, links between them, and link attributes like metrics, bandwidth, and administrative groups. This allows external systems like SDN controllers to build a complete network topology map without running the IGP themselves.

### Which routers support BGP-LS?

Major router vendors support BGP-LS export: Cisco IOS-XR, Juniper JunOS, Nokia SR OS, and Arista EOS all support BGP-LS natively. On the open-source side, FRRouting, GoBGP, and Quagga-derived implementations can export IGP topology via BGP-LS. The router must redistribute its OSPF or IS-IS link-state database into BGP-LS address family.

### Can GoBGP originate BGP-LS routes or only consume them?

GoBGP is primarily designed as a BGP-LS consumer (receiving topology from routers). It can inject BGP-LS routes programmatically via its gRPC API, but it does not run OSPF or IS-IS to generate its own topology. For BGP-LS origination from IGP topology, FRRouting is the better choice as it runs both the IGP and exports the link-state database.

### How does BGP-LS integrate with segment routing?

BGP-LS distributes segment routing SID (Segment ID) information alongside topology data. When a router advertises its BGP-LS routes, it includes SIDs for each node (Node SID) and adjacency (Adjacency SID). The SDN controller uses this combined topology + SID information to compute segment-routed paths and install them in the network.

### Is BGP-LS secure?

BGP-LS inherits BGP's security properties. TCP-MD5 or TCP-AO can authenticate BGP sessions, and RPKI/BGPsec can validate route origin. Additionally, BGP-LS NLRI should be filtered to accept topology data only from trusted peers within your network. Use prefix filters, AS-path filters, and community-based validation to ensure only authorized routers can inject BGP-LS data.

### What is the overhead of running BGP-LS?

BGP-LS adds minimal overhead to existing BGP sessions. The topology NLRI is advertised once per topology change (link up/down, metric change), not periodically. For a typical enterprise network with 50-100 routers, BGP-LS updates are infrequent and consume negligible bandwidth. The primary resource cost is on the consumer side, where the SDN controller must store and process the complete topology database.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted BGP Link-State Distribution: FRRouting vs GoBGP vs BIRD (2026)",
  "description": "Compare FRRouting, GoBGP, and BIRD for BGP Link-State (BGP-LS) distribution. Learn how to configure, deploy, and use BGP-LS for SDN and traffic engineering.",
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
