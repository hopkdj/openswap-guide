---
title: "Self-Hosted Network Routing Protocol Monitoring: FRRouting vs BIRD vs GoBGP (2026)"
date: "2026-05-20"
tags: ["routing", "bgp", "ospf", "networking", "frrouting", "monitoring"]
draft: false
---

Running a self-hosted routing infrastructure requires visibility into protocol state, peer connectivity, and route advertisements. Three open-source routing suites dominate the space: FRRouting (FRR), BIRD, and GoBGP. Each provides a different approach to routing protocol implementation, monitoring, and operational management.

## What Is Routing Protocol Monitoring?

Routing protocol monitoring involves tracking the health and state of dynamic routing protocols — BGP, OSPF, IS-IS, RIP, and others — across your network infrastructure. Effective monitoring provides real-time visibility into peer sessions, route table changes, convergence events, and potential routing anomalies. Self-hosted routing suites offer built-in CLI tools, API endpoints, and telemetry streams that integrate with monitoring dashboards.

## FRRouting (FRR): The Comprehensive Routing Suite

[FRRouting](https://github.com/FRRouting/frr) is the most feature-complete open-source routing software, supporting BGP, OSPFv2/v3, IS-IS, RIP, PIM, VRRP, NHRP, and more. With over 4,100 GitHub stars and active development, it is the successor to Quagga and is used by major cloud providers and enterprises.

**Key Features:**
- Full BGP4/4+ implementation with route reflector, confederation, and route server support
- OSPFv2 (RFC 2328) and OSPFv3 (RFC 5340) with area partitioning and NSSA
- IS-IS for large-scale service provider deployments
- PIM-SM/SSM for multicast routing
- VRRP for gateway redundancy
- Zebra RIB manager for unified route table management
- VTYSH unified CLI for all protocols
- NETCONF/YANG support for programmatic configuration
- FPM (Forwarding Plane Manager) for kernel route programming

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  frr:
    image: frrouting/frr:latest
    container_name: frr
    cap_add:
      - NET_ADMIN
      - NET_RAW
      - SYS_ADMIN
    network_mode: host
    volumes:
      - ./frr.conf:/etc/frr/frr.conf:ro
      - /var/run/frr:/var/run/frr
    restart: unless-stopped
    logging:
      driver: syslog
      options:
        syslog-address: "udp://127.0.0.1:514"
        tag: "frr"
```

### Configuration Example — BGP Peering

```ini
! frr.conf - BGP peering with route reflector
frr version 9.1
frr defaults traditional
hostname frr-router
log syslog informational
!
router bgp 65001
  bgp router-id 10.0.0.1
  bgp log-neighbor-changes
  neighbor 10.0.0.2 remote-as 65001
  neighbor 10.0.0.2 description Route-Reflector-Peer
  neighbor 10.0.0.2 route-reflector-client
  !
  address-family ipv4 unicast
    neighbor 10.0.0.2 activate
    network 10.1.0.0/16
    network 10.2.0.0/16
  exit-address-family
!
router ospf
  router-id 10.0.0.1
  network 10.0.0.0/24 area 0.0.0.0
  network 10.1.0.0/16 area 0.0.0.1
!
line vty
!
```

## BIRD: The Lightweight Routing Daemon

[BIRD](https://bird.network.cz/) is a compact, high-performance routing daemon that supports BGP, OSPF, RIP, and static routes. Designed with simplicity and performance in mind, BIRD is popular in IXPs, small ISPs, and homelab setups.

**Key Features:**
- BGP4/4+ with graceful restart, route refresh, and MD5 authentication
- OSPFv2 with multi-area and stub area support
- RIP v1/v2 for legacy network compatibility
- Static route management with protocol filters
- Babel protocol for mesh networks
- Pipe protocol for route redistribution between protocols
- Configuration via a single, expressive config file
- CLI for runtime status inspection and route table queries
- Very low resource footprint (~10MB RAM)

### Installation and Configuration

```bash
# Debian/Ubuntu
apt-get install bird

# Start and enable
systemctl enable --now bird
```

BIRD configuration example — BGP with OSPF redistribution:

```ini
# bird.conf
router id 10.0.0.1;

protocol device {
    scan time 10;
}

protocol static {
    route 192.168.0.0/24 via 10.0.0.254;
}

protocol ospf v2 {
    area 0.0.0.0 {
        networks {
            10.0.0.0/24;
            10.1.0.0/16;
        };
    };
    import filter {
        if proto = "ospf" then accept;
    };
}

protocol bgp {
    local as 65001;
    neighbor 10.0.0.2 as 65002;
    import filter {
        if bgp_community ~ 65001:100 then accept;
        else reject;
    };
    export filter {
        if source = RTS_STATIC then accept;
        else reject;
    };
}
```

## GoBGP: The Programmable BGP Implementation

[GoBGP](https://github.com/osrg/gobgp) is a BGP implementation written in Go, designed for programmability and integration with SDN controllers, cloud platforms, and orchestration systems. With over 4,000 stars, it is the go-to choice for developers who need BGP control via APIs.

**Key Features:**
- Full BGP4/4+ implementation with RFC-compliant behavior
- gRPC and CLI interfaces for programmatic control
- Policy engine with expressive route filtering
- MPLS label distribution (BGP-LU)
- EVPN support for data center interconnect
- BGP FlowSpec for DDoS mitigation
- BMP (BGP Monitoring Protocol) for route telemetry
- Zebra integration for kernel FIB programming
- Easy to embed as a Go library in custom applications

### Docker Compose Setup

```yaml
version: "3.8"
services:
  gobgp:
    image: osrg/gobgp:latest
    container_name: gobgp
    cap_add:
      - NET_ADMIN
    network_mode: host
    volumes:
      - ./gobgp.conf:/etc/gobgp/gobgp.conf:ro
    command: ["gobgpd", "-f", "/etc/gobgp/gobgp.conf"]
    restart: unless-stopped
```

### Programmatic BGP Control via gRPC

```bash
# Add a BGP peer
gobgp neighbor add 10.0.0.2 as 65002

# Advertise a route
gobgp global rib add 10.1.0.0/16

# View the routing table
gobgp global rib

# Apply a policy
gobgp policy statement add st1 then community add 65001:100
gobgp neighbor 10.0.0.2 policy export add st1
```

## Comparison Table

| Feature | FRRouting | BIRD | GoBGP |
|---------|-----------|------|-------|
| GitHub Stars | 4,136 | 350+ | 4,057 |
| Protocols | BGP, OSPF, IS-IS, RIP, PIM, VRRP | BGP, OSPF, RIP, Babel, Static | BGP only |
| Configuration | VTYSH CLI + config files | Single config file | Config + gRPC API |
| Programmability | NETCONF/YANG | Config templates | gRPC, Go library |
| BGP Features | Full suite (RR, Confederation) | Standard BGP4+ | BGP + FlowSpec + EVPN |
| OSPF Support | OSPFv2 + OSPFv3 | OSPFv2 | No |
| Resource Usage | Moderate (~50MB) | Minimal (~10MB) | Low (~30MB) |
| Container Image | frrouting/frr | Alpine + bird | osrg/gobgp |
| Telemetry | FPM, BMP, syslog | CLI, syslog | BMP, gRPC streaming |
| Best For | Full routing stack | Lightweight IXPs | Programmable BGP |

## Why Self-Host Routing Protocol Monitoring?

Running your own routing infrastructure with proper monitoring is essential for network reliability, cost control, and operational visibility.

**Complete Network Visibility.** Self-hosted routing suites provide detailed protocol state information — BGP session uptime, OSPF neighbor adjacency, route advertisement counts, and convergence events. Cloud-managed networking hides this data behind proprietary dashboards with limited API access. Open-source routing tools expose everything via CLI, syslog, and telemetry streams.

**Avoid Vendor Lock-In.** Proprietary routing platforms (Cisco IOS, Juniper Junos, Arista EOS) require expensive licenses and hardware. FRRouting, BIRD, and GoBGP run on commodity x86 servers, virtual machines, and containers. Your routing infrastructure becomes software-defined and portable across any environment.

**Cost Savings at Scale.** Cloud networking charges for every VPC peering connection, Transit Gateway attachment, and NAT gateway. Self-hosted BGP peering with FRR or GoBGP on standard servers eliminates these per-connection fees. At scale, running BGP on three commodity servers costs less than a single managed Transit Gateway.

**SDN and Automation Integration.** GoBGP's gRPC API enables programmatic route manipulation from orchestration systems, CI/CD pipelines, and custom controllers. FRR's NETCONF/YANG support integrates with Ansible and other configuration management tools. BIRD's configuration templating works with any config management system.

**DDoS Mitigation with FlowSpec.** GoBGP's BGP FlowSpec support allows automated DDoS mitigation by programmatically installing traffic filtering rules across BGP peers. Combined with flow monitoring, this creates a self-healing network that responds to attacks in seconds rather than hours.

For BGP route reflector deployment, see our [BGP route reflector guide](../2026-05-13-self-hosted-bgp-route-reflector-frrouting-bird-gobgp-guide/). If you need BFD protocol support, check our [BFD daemons comparison](../2026-05-18-self-hosted-bfd-protocol-daemons-frrouting-bird-gobgp-guide/). For VRF management, our [VRF platforms guide](../2026-05-18-self-hosted-vrf-management-platforms-frrouting-linux-vrf-netavark-guide/) covers the options.

## FAQ

### What is the difference between FRRouting and BIRD?

FRRouting is a comprehensive routing suite supporting multiple protocols (BGP, OSPF, IS-IS, PIM, VRRP), while BIRD is a lightweight daemon focused on BGP, OSPF, RIP, and Babel. FRR is better for complex network topologies requiring multiple protocols; BIRD excels in simple, high-performance deployments like IXPs and small ISPs.

### Can GoBGP replace traditional routers?

GoBGP implements BGP only — it does not support OSPF, IS-IS, or other IGPs. For edge routers or BGP-only deployments (peering with upstream ISPs), GoBGP is sufficient. For internal network routing, pair GoBGP with an IGP like FRR or BIRD.

### How do I monitor BGP session health?

All three tools provide session monitoring: FRR via VTYSH (`show ip bgp summary`), BIRD via CLI (`birdc show protocols`), and GoBGP via gRPC or CLI (`gobgp neighbor`). For automated monitoring, export metrics to Prometheus using the FRR Prometheus exporter, BIRD exporter, or GoBGP's built-in BMP support.

### Is FRRouting production-ready?

Yes, FRRouting is used by major cloud providers (AWS, Azure, GCP use FRR in their SDN stacks), ISPs, and enterprises. It has over 4,100 GitHub stars, an active development community, and regular releases. It is the recommended choice for production routing deployments.

### What is BMP (BGP Monitoring Protocol)?

BMP (RFC 7854) is a protocol that allows BGP routers to stream routing information to monitoring stations. GoBGP and FRR both support BMP, enabling real-time route telemetry without polling. This is useful for route analytics, anomaly detection, and DDoS response.

### Can I run these routing tools in containers?

Yes, all three support Docker deployment with `NET_ADMIN` and `NET_RAW` capabilities. However, `network_mode: host` is typically required for proper routing protocol operation, as VRRP, BGP, and OSPF need direct access to network interfaces.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Network Routing Protocol Monitoring: FRRouting vs BIRD vs GoBGP (2026)",
  "description": "Compare FRRouting, BIRD, and GoBGP for self-hosted routing protocol monitoring and management. Includes Docker configs, BGP setup, and production deployment guides.",
  "datePublished": "2026-05-20",
  "dateModified": "2026-05-20",
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
