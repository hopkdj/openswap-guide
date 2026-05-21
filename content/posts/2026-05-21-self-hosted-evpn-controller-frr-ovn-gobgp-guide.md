---
title: "Self-Hosted EVPN Controller: FRRouting vs OVN vs GoBGP (2026)"
date: "2026-05-21"
tags: ["evpn", "vxlan", "networking", "frrouting", "ovn", "gobgp", "datacenter"]
draft: false
---

Ethernet VPN (EVPN) is a BGP-based control plane protocol that provides Layer 2 and Layer 3 virtual private network services across multi-site data centers, campus networks, and cloud environments. By leveraging BGP as the signaling protocol for MAC address learning and IP route distribution, EVPN eliminates the need for traditional L2 protocols like STP and provides superior scalability, multi-homing support, and traffic engineering capabilities.

For organizations building self-hosted data center interconnect, multi-tenant cloud networks, or distributed campus fabrics, EVPN provides a standardized, vendor-neutral approach to L2/L3 overlay networking. This guide compares the three leading open-source EVPN implementations.

## What Is EVPN and Why Use It?

EVPN (RFC 7432) extends BGP to carry MAC address reachability information alongside traditional IP routing. This allows data center switches and routers to learn endpoint locations (MAC/IP) through BGP rather than through traditional Ethernet flooding and learning, solving the broadcast storm and MAC table overflow problems that plague large Layer 2 networks.

Key advantages of EVPN over traditional L2 extension:
- **No Spanning Tree Protocol**: EVPN uses active-active multi-homing with all links forwarding simultaneously
- **MAC Address Scalability**: MAC learning through BGP scales to millions of endpoints without flooding
- **Integrated L2/L3**: Both bridged (L2) and routed (L3) VPNs share the same control plane
- **Multi-Tenant Isolation**: VNI (VXLAN Network Identifier) or VLAN tags provide tenant isolation
- **Optimal Forwarding**: BGP best-path selection ensures traffic follows the most efficient route

## Comparison: EVPN Implementations

| Feature | FRRouting | OVN | GoBGP |
|---|---|---|---|
| **GitHub Stars** | 4,136+ | 701+ | 4,052+ |
| **Language** | C | C | Go |
| **EVPN Type** | BGP EVPN (RFC 7432) | OVN EVPN gateway | BGP EVPN (RFC 7432) |
| **Data Plane** | Linux kernel / VXLAN | OVS (Open vSwitch) | User-space |
| **Underlay** | OSPF, BGP, IS-IS | OVN Southbound DB | BGP |
| **Overlay Protocol** | VXLAN (RFC 7348) | Geneve / VXLAN | VXLAN |
| **Type-2 Routes** | MAC/IP advertisement | Logical switch ports | MAC/IP advertisement |
| **Type-3 Routes** | Inclusive multicast | Logical router ports | Multicast tree |
| **Type-5 Routes** | IP prefix routes | N/A | IP prefix routes |
| **Active-Active ESI** | Yes (per-port) | Yes (chassis) | Yes |
| **IRB (L3 Gateway)** | Yes | Yes | Yes |
| **VXLAN Termination** | Bridge-VXLAN | OVS VXLAN port | User-space VTEP |
| **Kubernetes Native** | No | Yes (via OVN-K8s) | No |
| **License** | GPLv2 | Apache 2.0 | Apache 2.0 |

## FRRouting: Production EVPN Routing

FRRouting provides the most mature open-source EVPN implementation, supporting the full range of EVPN route types (Type-1 through Type-5) as defined in RFC 7432 and related extensions. FRR's EVPN implementation is widely deployed in service provider and enterprise data center networks.

FRR's EVPN control plane handles MAC address learning, IP route distribution, and multi-homing coordination through standard BGP EVPN address families. The data plane uses Linux bridge with VXLAN interfaces, providing hardware-compatible VXLAN termination on any Linux system.

### Docker Deployment

```yaml
version: "3.8"
services:
  frr-evpn:
    image: frrouting/frr:stable_10.2
    container_name: frr-evpn
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
      - SYS_ADMIN
    network_mode: "host"
    volumes:
      - ./frr.conf:/etc/frr/frr.conf:ro
      - /var/run/frr:/var/run/frr
    environment:
      - FRR_LOGGING=stdout
```

EVPN configuration in `frr.conf`:

```
frr version 10.2
hostname evpn-leaf-01

router bgp 65001
 bgp router-id 10.0.0.1
 !
 address-family l2vpn evpn
  advertise-all-vni
 exit-address-family
!

vrf blue
 vni 10001
 rd 65001:10001
 route-target import 65001:10001
 route-target export 65001:10001
!

vrf red
 vni 10002
 rd 65001:10002
 route-target import 65001:10002
 route-target export 65001:10002
!

interface vxlan10001
 vxlan id 10001
 vxlan local-tunnelip 10.0.0.1
 vxlan learning on
!

interface vxlan10002
 vxlan id 10002
 vxlan local-tunnelip 10.0.0.1
 vxlan learning on
```

### Key EVPN Configuration Concepts

- **VNI (VXLAN Network Identifier)**: 24-bit identifier that uniquely identifies a tenant network across the EVPN fabric. Each VNI maps to a separate routing/bridging instance.
- **RD (Route Distinguisher)**: Makes IP/MAC routes unique across different VRFs. Format: `<AS>:<VNI>` or `<IP>:<VNI>`.
- **Route Target**: Controls import/export of routes between VRFs. Routes with matching import RTs are installed in the VRF's routing table.
- **ESI (Ethernet Segment Identifier)**: Identifies a multi-homed Ethernet segment for active-active redundancy. All PE routers sharing the same ESI coordinate to prevent duplicate MAC learning.
- **IRB (Integrated Routing and Bridging)**: Provides L3 gateway functionality within the VXLAN overlay, allowing inter-VNI routing without hair-pinning traffic to an external router.

## OVN: Software-Defined Networking with EVPN Gateway

[OVN (Open Virtual Network)](https://github.com/ovn-org/ovn) is a software-defined networking system built on Open vSwitch. While OVN's native overlay uses the Geneve protocol, it provides an EVPN gateway feature that bridges OVN logical networks with external EVPN-based physical networks.

OVN is the control plane behind OVN-Kubernetes, making it the natural EVPN choice for organizations running Kubernetes with OVN as their CNI. The EVPN gateway allows OVN-managed workloads to communicate with external EVPN-connected networks seamlessly.

### Docker Deployment

```yaml
version: "3.8"
services:
  ovn-northd:
    image: ovnorg/ovn:latest
    container_name: ovn-northd
    network_mode: "host"
    command: ["ovn-northd", "--no-chdir"]

  ovn-controller:
    image: ovnorg/ovn:latest
    container_name: ovn-controller
    network_mode: "host"
    privileged: true
    volumes:
      - /var/run/openvswitch:/var/run/openvswitch
    command: ["ovn-controller"]

  ovs-vswitchd:
    image: ovnorg/ovn:latest
    container_name: ovs-vswitchd
    network_mode: "host"
    privileged: true
    volumes:
      - /var/run/openvswitch:/var/run/openvswitch
      - /etc/openvswitch:/etc/openvswitch
    command: ["ovs-vswitchd", "--no-chdir", "--mlockall"]
```

Configure the EVPN gateway:

```bash
# Create logical switch for EVPN
ovn-nbctl ls-add evpn-ls

# Add logical router port
ovn-nbctl lrp-add evpn-lr evpn-lrp 00:00:00:00:01:01 10.0.0.1/24

# Configure EVPN type-2 routes
ovn-nbctl lsp-add evpn-ls evpn-port1
ovn-nbctl lsp-set-addresses evpn-port1 "00:00:00:00:01:01 10.0.0.10"
ovn-nbctl lsp-set-port-security evpn-port1 "00:00:00:00:01:01 10.0.0.10"

# Set up EVPN gateway
ovn-nbctl set Logical_Router evpn-lr options:chassis=chassis1
ovn-nbctl set Logical_Switch_Port evpn-port1 options:requested-chassis=chassis1
```

### OVN EVPN Architecture

OVN's EVPN integration works through its southbound database, which maintains the mapping between logical network state and physical EVPN advertisements. The OVN Northbound database defines the desired network topology (logical switches, routers, ports), while the Southbound database translates these into OpenFlow rules for OVS and EVPN BGP advertisements for external connectivity.

## GoBGP: Go-Native EVPN Implementation

[GoBGP](https://github.com/osrg/gobgp) is a BGP implementation written in Go that provides a flexible, programmable BGP stack with EVPN support. Unlike FRR and OVN, GoBGP is designed as a user-space BGP daemon with a gRPC API, making it ideal for integration with custom SDN controllers and automation frameworks.

GoBGP supports all EVPN route types and provides a clean programmatic interface for EVPN route injection, withdrawal, and monitoring. This makes GoBGP an excellent choice for organizations building custom network automation or integrating EVPN with existing orchestration platforms.

### Docker Deployment

```yaml
version: "3.8"
services:
  gobgp-evpn:
    image: osrg/gobgp:latest
    container_name: gobgp-evpn
    network_mode: "host"
    volumes:
      - ./gobgp.conf:/etc/gobgp/gobgp.conf:ro
    command: ["gobgpd", "-f", "/etc/gobgp/gobgp.conf"]
```

GoBGP EVPN configuration:

```toml
[global.config]
  as = 65001
  router-id = "10.0.0.1"

[[neighbors]]
  [neighbors.config]
    neighbor-address = "10.0.0.2"
    peer-as = 65001

[[neighbors]]
  [neighbors.config]
    neighbor-address = "10.0.0.3"
    peer-as = 65001

[bgp-config]
  [bgp-config.route-selection]
    always-compare-med = false

[[bgp-config.address-families]]
  [bgp-config.address-families.config]
    afi-safi-name = "l2vpn-evpn"
```

Inject EVPN routes via the GoBGP CLI:

```bash
# Add EVPN Type-2 route (MAC/IP advertisement)
gobgp global rib add -a evpn mac 00:00:00:00:01:01 ip 10.0.0.10 vni 10001

# Add EVPN Type-3 route (Inclusive Multicast)
gobgp global rib add -a evpn multicast 10.0.0.1 vni 10001

# Show EVPN routes
gobgp global rib -a evpn
```

### GoBGP EVPN Use Cases

GoBGP is particularly well-suited for:
- **Custom SDN Controllers**: The gRPC API allows programmatic EVPN route management from any language
- **Network Automation**: Integrate EVPN route injection with CI/CD pipelines, infrastructure-as-code tools, or custom orchestration platforms
- **Multi-Vendor Integration**: GoBGP's standard BGP EVPN implementation interoperates with commercial EVPN switches and routers
- **Testing and Validation**: Use GoBGP as a lightweight EVPN test peer for validating physical EVPN deployments

## Why Self-Host EVPN Infrastructure?

Running your own EVPN fabric provides capabilities that proprietary vendor solutions cannot match:

**Multi-Vendor Interoperability**: EVPN is an IETF standard (RFC 7432) supported by all major networking vendors. Self-hosted EVPN implementations interoperate with Arista, Cisco, Juniper, and NVIDIA Cumulus switches, enabling mixed-vendor data center fabrics without vendor lock-in.

**Cost Efficiency**: Commercial EVPN solutions require expensive proprietary switches with EVPN licenses. Open-source EVPN runs on commodity x86 servers with standard NICs, reducing capital costs by 60-80% compared to commercial alternatives.

**Full Control Over Network Design**: Define your own VNI allocation scheme, route target policies, multi-homing configurations, and traffic engineering rules. No cloud provider restrictions on VNI ranges, route limits, or topology constraints.

**Scalability**: EVPN scales to millions of MAC addresses and thousands of VRFs without the flooding and learning limitations of traditional L2 networks. A well-designed EVPN fabric can support multi-site data center interconnect with active-active redundancy across all sites.

For related data center networking topics, see our [VXLAN tunneling guide](../2026-05-12-self-hosted-vxlan-tunneling-ovs-frr-ovn-guide/) for overlay network fundamentals, [BGP communities management](../2026-05-15-self-hosted-bgp-communities-management-exabgp-gobgp-frrouti/) for BGP policy control, and [IS-IS routing protocol](../2026-05-17-isis-routing-protocol-frrouting-bird-gobgp-guide/) for IGP underlay design.

## EVPN Route Types Explained

Understanding EVPN route types is essential for proper deployment:

| Route Type | Name | Purpose |
|---|---|---|
| Type-1 | Ethernet Auto-Discovery | Announces PE router presence and enables fast convergence |
| Type-2 | MAC/IP Advertisement | Learns endpoint MAC and IP addresses across the overlay |
| Type-3 | Inclusive Multicast | Builds BUM (Broadcast, Unknown, Destination) replication trees |
| Type-4 | Ethernet Segment Route | Coordinates multi-homed PE routers for active-active forwarding |
| Type-5 | IP Prefix Route | Advertises L3 prefixes for inter-VNI and external routing |

## Deployment Best Practices

### Underlay Design
- Use a routed Layer 3 underlay (OSPF or IS-IS) for EVPN. Avoid Layer 2 underlay to prevent STP and broadcast domain issues.
- Configure BGP route reflectors for large EVPN deployments (100+ VTEPs) to reduce BGP session complexity from O(n²) to O(n).
- Use loopback addresses as BGP router IDs and VXLAN tunnel source addresses for consistent reachability.

### VNI Planning
- Reserve VNI ranges for different purposes: 1-9999 for L2 VNIs, 10000-19999 for L3 VNIs, 20000+ for future expansion.
- Each VNI should map to a single broadcast domain. Do not share VNIs across tenants.
- Use consistent VNI assignments across all EVPN sites to simplify troubleshooting.

### Multi-Homing Configuration
- Configure consistent ESIs across all multi-homed PE routers. Use LACP-based ESI for link aggregation or manual ESI for individual links.
- Enable single-active or all-active multi-homing based on your redundancy requirements. All-active provides higher throughput; single-active avoids MAC mobility issues.
- Test failover scenarios regularly to verify ESI convergence behavior and MAC flush operations.

## Choosing the Right EVPN Implementation

**FRRouting** is the most production-ready option for traditional data center EVPN deployments. Its comprehensive EVPN implementation supports all route types, active-active multi-homing, and integrates with existing routing infrastructure through OSPF, IS-IS, and BGP.

**OVN** is the right choice for Kubernetes-centric environments. If you are running OVN-Kubernetes as your CNI, the EVPN gateway provides seamless integration between your Kubernetes overlay and external EVPN networks without additional control plane software.

**GoBGP** excels in programmable and automated environments. Its gRPC API and Go-native architecture make it ideal for custom SDN controllers, network automation frameworks, and environments where EVPN needs to integrate with existing orchestration platforms.

## FAQ

### What is EVPN and how does it work?

EVPN (Ethernet VPN) is a BGP-based control plane protocol (RFC 7432) that distributes MAC address and IP route information across a Layer 2/Layer 3 overlay network. Instead of learning MAC addresses through Ethernet flooding, EVPN uses BGP to advertise endpoint reachability, enabling scalable multi-site L2/L3 connectivity without spanning tree protocol limitations.

### Which open-source projects support EVPN?

Three primary open-source EVPN implementations exist: FRRouting (most mature, production-ready EVPN control plane), OVN (software-defined networking with EVPN gateway for Kubernetes integration), and GoBGP (programmable BGP stack with gRPC API for custom SDN controllers).

### Can EVPN replace VLANs in my data center?

EVPN with VXLAN provides a more scalable alternative to VLANs. While VLANs are limited to 4,096 IDs and require L2 adjacency, EVPN VNIs (24-bit) support 16 million segments and work across routed IP underlays. EVPN also eliminates spanning tree protocol, enabling active-active multi-homing.

### Do I need BGP route reflectors for EVPN?

For small deployments (under 20 VTEPs), a full-mesh BGP peering is manageable. For larger deployments, BGP route reflectors are strongly recommended to reduce the number of BGP sessions from O(n²) to O(n) and improve convergence times.

### What is the difference between EVPN Type-2 and Type-5 routes?

Type-2 routes (MAC/IP Advertisement) carry endpoint MAC and IP address information for L2 connectivity within a VNI. Type-5 routes (IP Prefix) advertise L3 prefixes for inter-VNI routing and external network connectivity. Type-2 is used for L2 bridging; Type-5 is used for L3 routing.

### Can I run EVPN without VXLAN?

EVPN is most commonly deployed with VXLAN as the data plane encapsulation, but it can also work with MPLS (EVPN-MPLS) or Geneve. The EVPN control plane is independent of the data plane encapsulation — it advertises reachability information regardless of how the actual packets are tunneled.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted EVPN Controller: FRRouting vs OVN vs GoBGP (2026)",
  "description": "Compare open-source EVPN implementations for self-hosted data center networking: FRRouting, OVN, and GoBGP — with Docker deployment guides and best practices.",
  "datePublished": "2026-05-21",
  "dateModified": "2026-05-21",
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
