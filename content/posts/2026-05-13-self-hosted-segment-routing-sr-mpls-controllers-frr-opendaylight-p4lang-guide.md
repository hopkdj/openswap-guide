---
title: "Self-Hosted Segment Routing (SR-MPLS) Controllers: FRRouting vs OpenDaylight vs P4lang (2026)"
date: "2026-05-13"
tags: ["segment-routing", "mpls", "sdn", "networking", "frrouting", "opendaylight"]
draft: false
---

Segment Routing over MPLS (SR-MPLS) is the next-generation routing architecture that eliminates the need for LDP and RSVP-TE while preserving MPLS forwarding. Instead of maintaining per-flow state across every router, SR-MPLS encodes the forwarding path as an ordered list of segments (SIDs) in the packet header. This dramatically simplifies traffic engineering, reduces control-plane overhead, and enables centralized path computation.

For organizations running self-hosted network infrastructure, the choice of SR-MPLS controller is critical. This guide compares three mature open-source options: **FRRouting** (distributed routing with SR extensions), **OpenDaylight** (centralized SDN controller with SR-MPLS plugins), and **P4lang behavioral-model** (protocol-independent programmable data plane with P4Runtime control).

## What Is Segment Routing (SR-MPLS)?

Segment Routing extends the MPLS label stack to encode a source-routed path. Each "segment" represents either a topological instruction (go to node X via shortest path) or a service instruction (apply a specific forwarding behavior). The key advantages over traditional MPLS include:

- **No LDP or RSVP-TE required** — segments use the IGP (IS-IS or OSPF) to distribute SIDs, eliminating separate label distribution protocols
- **Source routing** — the ingress node computes the full path, reducing intermediate node state to zero
- **Traffic engineering** — explicit paths can be computed by a centralized controller (PCE) or calculated locally
- **Fast reroute** — TI-LFA (Topology-Independent Loop-Free Alternate) provides sub-50ms convergence without extra protocols
- **Network programming** — segments can encode any forwarding behavior, not just topology

SR-MPLS operates alongside traditional MPLS forwarding, meaning existing hardware can often support it with a software upgrade.

## FRRouting for SR-MPLS

**GitHub:** [FRRouting/frr](https://github.com/FRRouting/frr) -- **Stars:** 4,100+ -- **License:** GPLv2

FRRouting (FRR) is a full-featured routing protocol suite that supports OSPF, BGP, IS-IS, and RIP. Its SR-MPLS implementation provides a distributed, standards-based approach:

- **ISIS-SR and OSPF-SR** -- both protocols advertise Prefix-SIDs and Adjacency-SIDs via extended TLVs
- **MPLS data plane** -- uses Linux kernel MPLS forwarding or hardware offload
- **BGP-LU** -- supports BGP labeled unicast for inter-domain SR paths
- **TI-LFA** -- fast reroute with loop-free alternates computed from the SR graph
- **zAPI** -- programmatic API for external controllers to push routes

FRR runs on commodity Linux hardware and integrates with any orchestration system that speaks BGP or NETCONF. It is the backbone routing engine for many cloud providers and ISP networks.

### FRRouting Docker Compose Setup

```yaml
version: "3.8"
services:
  frr-sr:
    image: frrouting/frr:v10.2
    container_name: frr-sr-mpls
    privileged: true
    cap_add:
      - NET_ADMIN
      - SYS_ADMIN
    volumes:
      - ./frr.conf:/etc/frr/frr.conf:ro
      - ./daemons:/etc/frr/daemons:ro
      - /lib/modules:/lib/modules:ro
    network_mode: "host"
    restart: unless-stopped
    environment:
      - FRR_CONFIG_FILE=/etc/frr/frr.conf
```

**frr.conf** (minimal SR-MPLS IS-IS config):

```
!
hostname sr-router
frr defaults data-plane
!
router isis SR-DOMAIN
  net 49.0001.0000.0000.0001.00
  segment-routing on
  segment-routing mpls
  segment-routing prefix-range 16000 size 1000 index 1
  segment-routing global-block 16000 23999
  segment-routing local-block 100000 size 8000
  address-family ipv4 unicast
    segment-routing mpls
  exit-address-family
!
interface eth0
  ip router isis SR-DOMAIN
  isis circuit-type level-2-only
!
```

## OpenDaylight SR-MPLS Controller

**GitHub:** [opendaylight/controller](https://github.com/opendaylight/controller) -- **Stars:** 477 -- **License:** EPL-1.0

OpenDaylight (ODL) is a modular SDN controller platform with dedicated SR-MPLS plugins. It provides centralized path computation, topology discovery, and YANG-modeled service orchestration:

- **PCEP (Path Computation Element Protocol)** -- computes optimal SR paths across the network and programs PCEP-capable routers
- **BGP-LS (BGP Link-State)** -- collects real-time network topology from all routers into a centralized TED (Traffic Engineering Database)
- **NETCONF/YANG** -- configures SR parameters on routers using standard models
- **MD-SAL (Model-Driven Service Abstraction Layer)** -- unified data store for topology, flow, and service state
- **SR-PCE plugin** -- dedicated segment routing path computation engine with constraint-based routing

OpenDaylight is suited for operator-scale networks where centralized traffic engineering and service orchestration are required.

### OpenDaylight Docker Deployment

```yaml
version: "3.8"
services:
  opendaylight:
    image: opendaylight/virtualization:latest
    container_name: odl-sr-controller
    ports:
      - "8181:8181"
      - "6633:6633"
      - "830:830"
    environment:
      - ODL_FEATURES=odl-netconf-topo,odl-netconf-connector-all,odl-mdsal-all,odl-restconf-all,odl-bgpcep-bgp,odl-bgpcep-pcep,odl-sr-pce
    volumes:
      - ./odl-config:/opt/opendaylight/configuration
    restart: unless-stopped
```

### Configuring an SR-MPLS NETCONF Connector

```xml
<module>
  <type xmlns:prefix="urn:opendaylight:params:xml:ns:yang:controller:md:sal:connector:netconf">prefix:sal-netconf-connector</type>
  <name>sr-router-connector</name>
  <address>192.168.1.1</address>
  <port>830</port>
  <username>admin</username>
  <password>admin123</password>
  <tcp-only>false</tcp-only>
  <event-executor ref="netconf-event-executor"/>
  <client-dispatcher ref="netconf-netty-client"/>
</module>
```

## P4lang Behavioral Model for SR-MPLS

**GitHub:** [p4lang/behavioral-model](https://github.com/p4lang/behavioral-model) -- **Stars:** 640 -- **License:** Apache-2.0

The P4lang behavioral-model (bmv2) is a software switch that executes P4 programs, enabling protocol-independent packet processing. For SR-MPLS, P4 allows you to define custom segment encodings, label operations, and forwarding behaviors at the data plane level:

- **P4Runtime API** -- standardized control-plane interface for programming tables, meters, and counters
- **Protocol independence** -- define new segment types without hardware dependency
- **P4Studio** -- reference SR-MPLS P4 programs for bmv2
- **Stratum integration** -- production-ready P4Runtime stack for white-box switches
- **gRPC-based control** -- modern API for controller-to-switch communication

P4lang is ideal for research, network innovation, and building custom SR behaviors that go beyond the standard IETF specifications.

### P4 SR-MPLS Switch Deployment

```yaml
version: "3.8"
services:
  p4-switch:
    image: p4lang/behavioral-model:latest
    container_name: p4-sr-switch
    privileged: true
    cap_add:
      - NET_ADMIN
    ports:
      - "50051:50051"
      - "9090:9090"
    volumes:
      - ./sr-mpls.p4:/p4app/sr-mpls.p4:ro
      - ./p4rt.cfg:/p4app/p4rt.cfg:ro
    command: >
      simple_switch_grpc
      --log-console
      --nanolog ipc:///tmp/bm-0-log.ipc
      --device-id 1
      --interface 0@eth0
      --interface 1@eth1
      /p4app/sr-mpls.p4
    restart: unless-stopped
```

## Comparison Table

| Feature | FRRouting | OpenDaylight | P4lang bmv2 |
|---------|-----------|--------------|-------------|
| **Architecture** | Distributed routing | Centralized SDN controller | Programmable data plane |
| **Stars / Activity** | 4,100+, daily commits | 477, active mirror | 640, active development |
| **SR-MPLS Support** | ISIS-SR, OSPF-SR, TI-LFA | PCEP-based SR paths, BGP-LS | P4-programmed SR behaviors |
| **Control Plane** | OSPF/IS-IS/BGP (distributed) | MD-SAL + RESTCONF + NETCONF | P4Runtime (gRPC) |
| **Data Plane** | Linux kernel MPLS | External routers (PCEP/NETCONF) | bmv2 software switch |
| **Traffic Engineering** | Local + PCEP-assisted | Centralized constraint-based | Fully programmable |
| **Fast Reroute** | TI-LFA (sub-50ms) | Via PCEP re-routing | Custom P4 logic |
| **Hardware Offload** | Linux MPLS, eBPF | N/A (controller only) | Tofino ASIC via Stratum |
| **Best For** | ISP/cloud backbone routing | Operator-scale SDN | Research, custom protocols |
| **Deployment** | Docker + Linux namespaces | Docker container (Java) | Docker (C++ switch) |
| **Learning Curve** | Moderate (networking background) | High (SDN/YANG expertise) | High (P4 programming) |
| **License** | GPLv2 | EPL-1.0 | Apache-2.0 |

## Choosing the Right SR-MPLS Controller

The choice depends on your network architecture and operational model:

**Use FRRouting when:**
- You need distributed routing with standard IGP/BGP protocols
- Your network runs on commodity Linux servers or network appliances
- You want TI-LFA fast reroute without centralized control
- You are building an ISP or cloud provider backbone

**Use OpenDaylight when:**
- You need centralized traffic engineering across a multi-domain network
- You already run SDN infrastructure with OpenFlow or NETCONF
- You require BGP-LS topology collection for global visibility
- Your team has SDN controller operations experience

**Use P4lang behavioral-model when:**
- You need to prototype custom SR behaviors not yet standardized
- You are building a research testbed or university lab
- You want protocol-independent forwarding for experimental segment types
- You plan to deploy on Tofino-based white-box switches via Stratum

For related reading, see our [FRRouting vs BIRD vs OpenBGPD BGP routing guide](../2026-04-19-frrouting-vs-bird-vs-openbgpd-self-hosted-bgp-routing-guide-2026/) and [OpenDaylight vs Faucet vs Ryu SDN controllers](../2026-04-29-opendaylight-vs-faucet-vs-ryu-self-hosted-sdn-controller-guide-2026/). For broader network architecture, check our [VyOS vs OPNsense vs OpenWrt SD-WAN guide](../2026-05-03-vyos-vs-opnsense-vs-openwrt-self-hosted-sd-wan-edge-routing-guide/).

## Why Self-Host Segment Routing Infrastructure?

Running your own SR-MPLS controllers gives you complete control over network traffic engineering without vendor lock-in or proprietary licensing costs. Commercial SR-MPLS solutions from Cisco, Juniper, and Nokia require expensive hardware and per-feature licenses that can easily exceed six figures annually for mid-size networks.

Open-source SR-MPLS implementations let you deploy segment routing on commodity x86 hardware, reducing capital expenditure by 70-80% compared to proprietary alternatives. The distributed model (FRRouting) scales linearly with your network size, while centralized controllers (OpenDaylight) provide global optimization capabilities that would otherwise require costly vendor-specific NMS platforms.

For network operators managing multi-tenant infrastructure, SR-MPLS provides the isolation and traffic engineering capabilities needed to guarantee SLAs between customer segments. Each tenant gets dedicated SIDs with guaranteed bandwidth, and the source-routing architecture ensures that traffic follows precisely the path you define -- no more dealing with ECMP-induced load imbalances.

Self-hosting also means you control the upgrade cadence. When a new IETF SR extension is published, you can test it in your lab using the P4lang behavioral-model before deploying to production. With vendor equipment, you are locked into their release schedule, which can lag standards adoption by years.

For network monitoring integration, see our [Zabbix vs LibreNMS vs Netdata monitoring guide](../zabbix-vs-librenms-vs-netdata-network-monitoring-guide/). For broader routing options, check our [BGP Route Server guide](../2026-05-07-self-hosted-bgp-route-server-bird-openbgpd-frrouting-guide/).

## FAQ

### What is the difference between SR-MPLS and traditional MPLS?

Traditional MPLS relies on LDP (Label Distribution Protocol) or RSVP-TE (Resource Reservation Protocol) to establish label-switched paths. SR-MPLS eliminates these by encoding the path directly in the packet header as a stack of segment identifiers (SIDs). This removes per-flow state from intermediate routers, simplifies operations, and enables traffic engineering without RSVP-TE signaling.

### Can FRRouting run SR-MPLS without a controller?

Yes. FRRouting supports fully distributed SR-MPLS using IS-IS or OSPF extensions. Each router independently computes SR paths using its IGP database. A controller is optional -- you can add PCEP-based path computation later if centralized traffic engineering becomes necessary.

### Does OpenDaylight require PCEP-capable routers?

For full SR-MPLS orchestration, yes -- the routers should support PCEP (RFC 8231) to receive computed paths from ODL. However, ODL can also configure SR parameters via NETCONF/YANG on routers that support the IETF SR YANG model, even without PCEP.

### Is P4lang suitable for production SR-MPLS networks?

The behavioral-model (bmv2) itself is a software reference implementation, not production-grade. However, the P4 programs you write for bmv2 can be compiled and deployed on production Tofino ASIC-based switches using the Stratum stack. P4lang is production-ready when paired with appropriate hardware targets.

### How does TI-LFA work with Segment Routing?

TI-LFA (Topology-Independent Loop-Free Alternate) pre-computes backup paths for every destination in the network. When a link or node fails, the protecting router switches traffic to the backup path within 50ms. Unlike traditional LFA, TI-LFA uses SR-MPLS to encode arbitrary backup paths that are guaranteed to be loop-free, achieving 100% coverage in any topology.

### Can I migrate from LDP/RSVP-TE to SR-MPLS gradually?

Yes. SR-MPLS coexists with LDP and RSVP-TE on the same network. You can enable SR on a subset of routers and use interworking (SR-to-LDP binding or RSVP-TE tunnel mapping) during the transition. FRRouting supports this migration mode natively.

## Deployment Architecture Tips

When deploying SR-MPLS in production, consider these architectural patterns:

1. **Controller redundancy** -- For OpenDaylight, deploy a 3-node cluster with distributed MD-SAL to avoid single points of failure. FRRouting is inherently distributed but benefits from BGP route reflectors for scaling.

2. **SID space planning** -- Allocate contiguous Prefix-SID blocks per router (e.g., 16000-16999 for router 1, 17000-17999 for router 2). Use Adjacency-SIDs sparingly as they consume local SID space.

3. **Monitoring** -- Deploy telemetry collectors (gNMI, streaming telemetry) to monitor SID utilization, SR path latency, and MPLS label distribution. Integrate with Prometheus for alerting on SID block exhaustion.

4. **Testing** -- Use the P4lang behavioral-model as a lab environment to validate SR path computation before deploying to production routers. Tools like Mininet can simulate large topologies for TI-LFA convergence testing.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Segment Routing (SR-MPLS) Controllers: FRRouting vs OpenDaylight vs P4lang (2026)",
  "description": "Compare open-source Segment Routing over MPLS controllers: FRRouting for distributed routing, OpenDaylight for centralized SDN, and P4lang for programmable data planes. Includes Docker Compose configs and deployment guides.",
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
