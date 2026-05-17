---
title: "Self-Hosted IS-IS Routing Protocol: FRRouting vs BIRD vs GoBGP (2026)"
date: "2026-05-17"
tags: ["isis", "routing-protocol", "frrouting", "bird", "gobgp", "networking"]
draft: false
---

The IS-IS (Intermediate System to Intermediate System) routing protocol is a link-state protocol widely used in large enterprise networks, ISP backbones, and data center fabrics. Originally designed for OSI protocol stacks, IS-IS was extended to support IP routing (Integrated IS-IS) and has become a preferred choice for many network operators due to its scalability, fast convergence, and flexibility.

In this guide, we compare three open-source IS-IS implementations — **FRRouting**, **BIRD**, and **GoBGP** — evaluating their IS-IS support, deployment options, and suitability for self-hosted network infrastructure.

## IS-IS Protocol Overview

IS-IS is an Interior Gateway Protocol (IGP) that uses the Shortest Path First (SPF) algorithm, similar to OSPF. Key advantages of IS-IS include:

- **Protocol-agnostic design**: IS-IS is not tied to IP — it natively supports IPv4, IPv6, and can carry additional address families
- **Scalable hierarchy**: Level-1 (intra-area) and Level-2 (inter-area) routing with support for large networks
- **Fast convergence**: Uses hello packets, LSP (Link State PDU) flooding, and SPF recalculation
- **TLV-based extensibility**: Type-Length-Value encoding makes it easy to add new features (Traffic Engineering, Segment Routing)
- **No backbone area requirement**: Unlike OSPF's Area 0 requirement, IS-IS uses a more flexible area boundary model

IS-IS identifies routers using **NET (Network Entity Title)** addresses, which include an Area ID and System ID. Each router maintains a Link State Database (LSDB) and computes shortest paths independently.

## Tool Comparison

| Feature | FRRouting | BIRD | GoBGP |
|---|---|---|---|
| **IS-IS Support** | Full (Level-1, Level-2, multi-topology) | Full (bird2 IS-IS daemon) | Plugin/Extension-based |
| **GitHub Stars** | 4,132+ | 188+ | 4,055+ |
| **Last Updated** | May 2026 | May 2026 | May 2026 |
| **Language** | C | C | Go |
| **IPv6 IS-IS** | Yes | Yes | Limited |
| **Multi-Topology** | Yes | Partial | No |
| **Segment Routing** | Yes (SR-MPLS, SRv6) | No | No |
| **Docker Image** | `frrouting/frr` | `cznic/bird` (community) | `osrg/gobgp` |
| **Management API** | VTYSH, REST (FRR 9+) | CLI, UNIX socket | gRPC, CLI |
| **License** | GPLv2 | GPLv2+ | Apache 2.0 |

## FRRouting IS-IS Configuration

FRRouting offers the most comprehensive IS-IS implementation among the three, with full support for Level-1/Level-2 routing, multi-topology IS-IS (MT-IS-IS), and Segment Routing extensions.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  frr-isis:
    image: frrouting/frr:latest
    container_name: frr-isis
    hostname: rtr-isis-01
    cap_add:
      - NET_ADMIN
      - NET_RAW
    network_mode: "host"
    volumes:
      - ./frr-conf:/etc/frr:rw
      - /var/run/frr:/var/run/frr:rw
    restart: unless-stopped
```

### IS-IS Configuration (`/etc/frr/frr.conf`)

```
! Enable IS-IS daemon
router isis 1
 net 49.0001.1921.6800.1001.00
 is-type level-2-only
 metric-style wide level-2
 log-adjacency-changes
 !
 address-family ipv4 unicast
  redistribute connected
 !
 address-family ipv6 unicast
  redistribute connected
!
interface eth0
 ip router isis 1
 ipv6 router isis 1
 isis circuit-type level-2-only
 isis hello-interval 10
 isis hello-multiplier 3
!
interface eth1
 ip router isis 1
 isis metric 20 level-2
 isis circuit-type level-1-2
!
! Enable daemons
zebra=yes
isisd=yes
```

Key FRRouting IS-IS features:
- **NET addressing**: Configure your Network Entity Title (area.system.00 format)
- **Wide metrics**: Enable TLV-based wide metrics for values > 63
- **Multi-area**: Support for Level-1 intra-area and Level-2 inter-area routing
- **Segment Routing**: Native SR-MPLS and SRv6 IS-IS extensions
- **BFD integration**: Fast failure detection via Bidirectional Forwarding Detection

## BIRD IS-IS Configuration

BIRD is a lightweight, modular routing daemon. IS-IS support was added in BIRD 2.x (bird2 branch), making it a viable option for simpler IS-IS deployments.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  bird-isis:
    image: alpine:latest
    container_name: bird-isis
    hostname: bird-isis-01
    cap_add:
      - NET_ADMIN
    network_mode: "host"
    volumes:
      - ./bird-conf:/etc/bird:rw
      - ./bird-bin:/usr/sbin/bird:ro
    command: ["bird", "-d"]
    restart: unless-stopped
```

### IS-IS Configuration (`/etc/bird/bird.conf`)

```
# BIRD IS-IS configuration
router id 192.168.1.1;

protocol isis {
    area 49.0001;
    system_id 1921.6800.1001;
    level 2;
    interface "eth0" {
        hello_interval 10;
        hello_multiplier 3;
        cost 10;
        type p2p;
    };
    interface "eth1" {
        hello_interval 10;
        hello_multiplier 3;
        cost 20;
    };
    import all;
    export all;
}

# Kernel protocol for route injection
protocol kernel {
    persist;
    scan time 20;
    import all;
    export filter {
        if source = RTS_ISIS then accept;
        reject;
    };
}

protocol device {
    scan time 10;
}
```

BIRD's IS-IS implementation is simpler than FRRouting's but offers:
- Clean, declarative configuration syntax
- Low memory footprint (~5-10 MB per daemon)
- Good integration with Linux kernel routing table
- Support for both Level-1 and Level-2 IS-IS
- Flexible route filtering with BIRD's expression language

## GoBGP IS-IS Extension

GoBGP is primarily a BGP implementation, but it includes IS-IS capabilities through its extensible architecture. IS-IS support in GoBGP is primarily focused on carrying IS-IS information via BGP-LS (BGP Link-State) rather than native IS-IS routing.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  gobgp-isis:
    image: osrg/gobgp:latest
    container_name: gobgp-isis
    hostname: gobgp-isis-01
    network_mode: "host"
    volumes:
      - ./gobgp-conf:/etc/gobgp:rw
    command: ["/usr/bin/gobgpd", "-f", "/etc/gobgp/gobgp.conf"]
    restart: unless-stopped
```

### GoBGP Configuration with IS-IS BGP-LS

```toml
[global.config]
  as = 65001
  router-id = "192.168.1.1"

[[neighbors]]
  [neighbors.config]
    neighbor-address = "192.168.1.2"
    peer-as = 65001

[[neighbors]]
  [neighbors.config]
    neighbor-address = "192.168.1.3"
    peer-as = 65002

# BGP-LS to carry IS-IS topology information
[[neighbors]]
  [neighbors.config]
    neighbor-address = "10.0.0.1"
    peer-as = 65000
  [neighbors.route-server.config]
    route-server-client = true
  [neighbors.add-paths.config]
    send-max = 4
    receive = true
  [neighbors.afisafis.config]
    [neighbors.afisafis.config]
      afi-safi-name = "l3vpn-ipv4-unicast"
```

GoBGP's approach to IS-IS:
- Uses **BGP-LS (BGP Link-State, RFC 7752)** to distribute IS-IS topology information
- Native IS-IS protocol support is limited compared to FRRouting and BIRD
- Strong gRPC API for programmatic route management
- Best suited for **SDN controllers** and **route reflectors** that need to aggregate IS-IS topology data
- Go-based implementation provides good performance and memory safety

## Choosing the Right IS-IS Implementation

### Use FRRouting when:
- You need **full IS-IS feature support** (multi-topology, Segment Routing, BFD integration)
- You are building a **production ISP or enterprise network**
- You need **both IGP and BGP** in a single routing suite
- You require **REST API management** (available in FRR 9+)
- Your network uses **SR-MPLS or SRv6**

### Use BIRD when:
- You need a **lightweight, single-purpose routing daemon**
- Your deployment has **limited resources** (edge routers, containers)
- You prefer **declarative configuration** with powerful filtering
- You are building **BGP route servers** or **IXP infrastructure**
- Memory footprint is a primary concern

### Use GoBGP when:
- You are building an **SDN controller** or **network orchestrator**
- You need **programmatic route management** via gRPC
- You are collecting **BGP-LS topology data** from IS-IS networks
- Your team prefers **Go-based tooling** for integration
- You are operating a **cloud-native network** with containerized routing

## IS-IS Network Design Best Practices

### Addressing Plan
Design your IS-IS addressing plan before deployment:
- **Area IDs**: Use a hierarchical scheme (e.g., 49.0001, 49.0002 for geographic regions)
- **System IDs**: Use consistent 6-byte identifiers (often derived from loopback IPs)
- **NET format**: `area_id.system_id.selector` (e.g., `49.0001.1921.6800.1001.00`)

### Convergence Optimization
- Set appropriate **hello intervals** (3-10 seconds for LAN, 10-30 seconds for P2P)
- Configure **hello multipliers** (typically 3x) for failure detection
- Enable **fast hellos** (sub-second) on critical links
- Use **BFD** for sub-50ms failure detection
- Tune **SPF throttle timers** to prevent CPU overload during topology changes

### Security Considerations
- Use **IS-IS authentication** (HMAC-MD5 or HMAC-SHA) for LSP integrity
- Implement **route filtering** at area boundaries
- Deploy **BFD authentication** for neighbor verification
- Monitor **LSP sequence numbers** for anomaly detection
- Use **firewall rules** to restrict IS-IS protocol traffic (IP protocol 125 for IS-IS over IP)

## Why Self-Host Your IS-IS Routing Infrastructure?

Running your own IS-IS routing infrastructure gives you complete control over network topology, routing policies, and convergence behavior. Unlike managed SD-WAN or cloud networking solutions, self-hosted IS-IS routers operate on your hardware, with your configurations, under your administrative control.

### Data Ownership and Control
When you manage your own IS-IS routing daemons, you maintain full visibility into the link-state database, adjacency states, and SPF calculations. There is no vendor-imposed limitation on route policies, area designs, or protocol extensions. You can deploy custom routing policies, implement Segment Routing, or integrate with proprietary network management systems.

For **BGP route server deployment**, see our [BGP route server comparison](../2026-05-07-self-hosted-bgp-route-server-bird-openbgpd-frrouting-guide/). If you need **OSPF monitoring** alongside IS-IS, check our [OSPF monitoring guide](../2026-05-15-self-hosted-ospf-monitoring-frr-bird-gobgp-guide/). For **BGP monitoring and alerting**, our [comprehensive BGP monitoring article](../2026-05-09-self-hosted-bgp-monitoring-route-alerting-bgpalerter-exabgp-gobgp/) covers the tooling landscape.

### Cost Savings
Open-source IS-IS implementations eliminate per-device licensing costs associated with commercial routing platforms. FRRouting, BIRD, and GoBGP are all freely available under permissive licenses. Combined with commodity x86 hardware or white-box switches, you can build enterprise-grade routing infrastructure at a fraction of the cost.

### No Vendor Lock-In
Each of these implementations supports standard IS-IS protocol behavior (RFC 1195, RFC 5308 for IPv6, RFC 5305 for wide metrics). Configurations and operational concepts transfer between implementations, giving you the flexibility to migrate between routing daemons without rearchitecting your network.

## FAQ

### What is IS-IS and how does it differ from OSPF?

IS-IS (Intermediate System to Intermediate System) and OSPF (Open Shortest Path First) are both link-state IGPs using the SPF algorithm. Key differences: IS-IS uses a TLV-based encoding (more extensible), doesn't require a backbone area, uses CLNS addressing (NET), and runs directly over Layer 2 rather than IP. OSPF is IP-native and more widely supported in enterprise gear.

### Which IS-IS implementation should I choose for production?

For production networks requiring full IS-IS features (multi-topology, Segment Routing, BFD), **FRRouting** is the recommended choice. It has the most mature IS-IS implementation, active development, and comprehensive documentation. For lightweight deployments, BIRD is a viable alternative.

### Can GoBGP replace FRRouting for IS-IS routing?

No. GoBGP's IS-IS capabilities are limited to BGP-LS (carrying IS-IS topology data via BGP). It does not implement native IS-IS adjacency formation, LSP flooding, or SPF computation. Use GoBGP as a BGP speaker or BGP-LS collector, not as an IS-IS routing daemon.

### How do I design an IS-IS area hierarchy?

Plan your area hierarchy based on geography or function:
- **Level-1**: Intra-area routing (within a single area)
- **Level-2**: Inter-area routing (backbone connecting all areas)
- **Level-1-2**: Routers that participate in both levels (area border routers)
Use 49.xxx as private Area IDs (similar to RFC 1918 for IP). Keep Level-1 areas to 50-100 routers for optimal SPF performance.

### Does IS-IS support authentication?

Yes. IS-IS supports:
- **Simple password authentication** (plaintext, not recommended)
- **HMAC-MD5 authentication** (RFC 5304)
- **HMAC-SHA authentication** (RFC 5310, recommended)
Configure authentication on a per-interface or per-area basis to protect against rogue router injection.

### How do I monitor IS-IS adjacencies?

- **FRRouting**: Use `show isis neighbors` in VTYSH, or query the REST API
- **BIRD**: Use `birdc show protocols` and `birdc show isis neighbors`
- **GoBGP**: Use `gobgp neighbor` for BGP-LS peers
- **Prometheus**: Export metrics via `frr_exporter`, `bird_exporter`, or custom collectors
- **SNMP**: Query IS-IS MIB (RFC 4444) for adjacency state and LSP information

### Can I run IS-IS in Docker containers?

Yes, all three implementations can run in containers with `network_mode: "host"` or macvlan networking. You need `NET_ADMIN` and `NET_RAW` capabilities for protocol packet injection and raw socket access. For production, consider running IS-IS on bare metal or VMs for better performance and stability.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted IS-IS Routing Protocol: FRRouting vs BIRD vs GoBGP (2026)",
  "description": "Compare open-source IS-IS routing protocol implementations: FRRouting, BIRD, and GoBGP. Includes Docker Compose configs, deployment guides, and IS-IS configuration examples.",
  "datePublished": "2026-05-17",
  "dateModified": "2026-05-17",
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
