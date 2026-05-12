---
title: "Self-Hosted VXLAN Tunneling: Open vSwitch vs FRRouting vs OVN (2026)"
date: "2026-05-12"
tags: ["comparison", "guide", "self-hosted", "networking", "vxlan", "tunneling", "overlay"]
draft: false
description: "Compare open-source VXLAN tunneling solutions — Open vSwitch, FRRouting (VXLAN EVPN), and OVN. Full guide with Docker deployment configs, EVPN control plane setup, and multi-site overlay networking."
---

VXLAN (Virtual Extensible LAN) is a network virtualization technology that extends Layer 2 segments over Layer 3 infrastructure. By encapsulating Ethernet frames in UDP packets, VXLAN enables you to build overlay networks across geographically distributed data centers, connect Kubernetes clusters across subnets, and isolate tenant traffic without physical VLAN limitations.

This guide compares three open-source implementations for self-hosted VXLAN tunneling: **Open vSwitch** (the dominant software switch), **FRRouting** (VXLAN EVPN control plane), and **OVN** (Open Virtual Network, the SDN overlay built on OVS). We cover deployment with Docker, configuration patterns, and when to choose each tool.

## What Is VXLAN and Why Use It?

VXLAN solves a fundamental problem in modern infrastructure: the 4,096 VLAN limit. By using a 24-bit VXLAN Network Identifier (VNI), it supports up to 16 million logical networks — enough for large multi-tenant environments. Each VXLAN tunnel is a point-to-point or multicast-based UDP connection (default port 4789) that carries encapsulated Ethernet frames between VTEPs (VXLAN Tunnel Endpoints).

Key use cases include:

- **Multi-datacenter L2 extension** — stretch Layer 2 networks across sites without dark fiber
- **Kubernetes pod networking** — overlay networks for cross-node pod communication
- **Cloud-native migration** — lift-and-shift VMs to new subnets without re-IPing
- **Network segmentation** — isolate tenant workloads without physical switch reconfiguration
- **Hybrid cloud connectivity** — connect on-premises infrastructure to cloud VPCs

Unlike traditional VLAN trunking, VXLAN tunnels traverse any IP network — including the public internet (with encryption) — making it ideal for distributed infrastructure.

## Open vSwitch (OVS)

[Open vSwitch](https://www.openvswitch.org/) (3,946+ GitHub stars) is the most widely deployed software switch for VXLAN. It supports both static VXLAN tunnels (configured manually per peer) and EVPN-based VXLAN (with BGP control plane). OVS runs in the Linux kernel datapath for high throughput or in userspace for portability.

**Strengths:**
- Industry-standard VXLAN implementation, used by OpenStack, Kubernetes (via OVN-Kubernetes), and VMware
- Hardware offload support (SmartNICs, DPDK) for line-rate performance
- Rich OpenFlow integration for advanced traffic engineering
- Mature Docker integration via `--network=host` or macvlan

**Limitations:**
- Static VXLAN configuration doesn't scale beyond a few peers
- EVPN requires a separate BGP daemon (FRRouting or BIRD)
- Kernel module dependency limits portability to non-Linux systems

### Docker Deployment

```yaml
version: "3.8"
services:
  ovs-vtep:
    image: linuxserver/openvswitch:latest
    container_name: ovs-vtep
    network_mode: host
    cap_add:
      - NET_ADMIN
      - SYS_ADMIN
    volumes:
      - /etc/openvswitch:/etc/openvswitch
      - /var/run/openvswitch:/var/run/openvswitch
    restart: unless-stopped
```

### VXLAN Tunnel Configuration

```bash
# Create a VXLAN tunnel on OVS
ovs-vsctl add-br br-vxlan
ovs-vsctl add-port br-vxlan vxlan0 --   set interface vxlan0 type=vxlan   options:remote_ip=10.0.1.2   options:key=100   options:dst_port=4789

# Assign IP to the bridge
ip addr add 172.16.100.1/24 dev br-vxlan
ip link set br-vxlan up
```

## FRRouting (VXLAN EVPN)

[FRRouting](https://frrouting.org/) (4,127+ GitHub stars) provides the BGP EVPN control plane for VXLAN networks. Instead of manually configuring every VTEP peer, FRR uses BGP to automatically distribute MAC and IP reachability information, enabling scalable multi-tenant VXLAN overlays.

**Strengths:**
- BGP EVPN eliminates manual VTEP peer configuration
- Supports MAC/IP advertisement routes (Type 2, Type 5)
- Integrated with IRB (Integrated Routing and Bridging) for L3 VXLAN
- Active development with strong enterprise adoption
- Works alongside OVS or Linux native VXLAN interfaces

**Limitations:**
- Requires BGP peering infrastructure (iBGP or eBGP)
- Steeper learning curve than static VXLAN
- Needs a separate data plane (OVS, Linux bridge, or VRF)

### Docker Deployment

```yaml
version: "3.8"
services:
  frr-evpn:
    image: frrouting/frr:v10.2
    container_name: frr-evpn
    network_mode: host
    cap_add:
      - NET_ADMIN
      - SYS_ADMIN
    volumes:
      - ./frr/etc:/etc/frr
      - ./frr/run:/var/run/frr
    restart: unless-stopped
```

### EVPN Configuration

```bash
# /etc/frr/frr.conf — BGP EVPN with VXLAN
frr defaults datacenter

router bgp 65000
  bgp router-id 10.0.0.1
  neighbor 10.0.0.2 remote-as 65000
  neighbor 10.0.0.2 update-source lo0
  !
  address-family l2vpn evpn
    neighbor 10.0.0.2 activate
    advertise-all-vni
  exit-address-family
exit

vni 100
  rd 65000:100
  route-target import 65000:100
  route-target export 65000:100
exit-vni

vxlan vni 100
exit
```

## OVN (Open Virtual Network)

[OVN](https://www.ovn.org/) (695+ GitHub stars) is a full SDN overlay solution built on top of Open vSwitch. It provides a centralized control plane (OVN Northbound/Southbound databases) that automatically manages VXLAN tunnels, logical switches, and logical routers across all hypervisor nodes.

**Strengths:**
- Complete SDN stack — logical switches, routers, ACLs, load balancers
- Automatic VXLAN tunnel management (no manual VTEP config)
- Native integration with OpenStack, Kubernetes (OVN-Kubernetes), and Kubernetes Gateway API
- Supports distributed logical routing (no traffic hairpinning)
- Built-in security groups and ACLs

**Limitations:**
- More complex architecture (3 databases + multiple daemons)
- Requires central controller (ovn-northd) for policy distribution
- Heavier resource footprint than standalone OVS
- Best suited for cloud/VM orchestration environments

### Docker Deployment

```yaml
version: "3.8"
services:
  ovn-central:
    image: docker.io/ovn/ovn-central:24.03
    container_name: ovn-central
    network_mode: host
    cap_add:
      - NET_ADMIN
    environment:
      - CENTRAL_IP=10.0.0.1
      - ENABLE_SSL=false
    restart: unless-stopped

  ovn-controller:
    image: docker.io/ovn/ovn-host:24.03
    container_name: ovn-controller
    network_mode: host
    cap_add:
      - NET_ADMIN
      - SYS_ADMIN
    environment:
      - CENTRAL_IP=10.0.0.1
      - ENABLE_SSL=false
    volumes:
      - /var/run/openvswitch:/var/run/openvswitch
    restart: unless-stopped
```

### OVN Logical Network Setup

```bash
# Create a logical switch (OVN auto-manages VXLAN tunnels)
ovn-nbctl ls-add ls-frontend
ovn-nbctl lsp-add ls-frontend lsp-web1
ovn-nbctl lsp-set-addresses lsp-web1 "00:00:00:00:00:01 172.16.1.10"

# Create a logical router with distributed routing
ovn-nbctl lr-add lr-edge
ovn-nbctl lrp-add lr-edge lrp-external 00:00:00:00:FF:01 10.0.0.1/24
ovn-nbctl lsp-add ls-frontend lsp-lr-edge
ovn-nbctl lsp-set-type lsp-lr-edge router
ovn-nbctl lsp-set-addresses lsp-lr-edge 00:00:00:00:FF:01
ovn-nbctl lsp-set-options lsp-lr-edge router-port=lrp-external
```

## Comparison: OVS vs FRRouting vs OVN

| Feature | Open vSwitch | FRRouting EVPN | OVN |
|---------|-------------|----------------|-----|
| **Primary Role** | Software switch / data plane | BGP EVPN control plane | Full SDN overlay |
| **VXLAN Support** | Native (static + EVPN) | EVPN control plane only | Native (auto-managed) |
| **Control Plane** | Manual or external BGP | BGP EVPN (built-in) | Centralized (OVN NB/SB) |
| **L3 Routing** | Via external router | Integrated IRB | Distributed logical router |
| **Scalability** | Limited (static) | High (BGP-based) | Very high (centralized) |
| **Docker Image** | linuxserver/openvswitch | frrouting/frr | ovn/ovn-central |
| **GitHub Stars** | 3,946 | 4,127 | 695 |
| **Best For** | Simple point-to-point tunnels | Multi-site EVPN fabrics | Cloud/VM orchestration |

## Choosing the Right VXLAN Solution

For **simple point-to-point or hub-and-spoke tunnels** between a few sites, Open vSwitch with static VXLAN configuration is the quickest path. A few `ovs-vsctl` commands establish the tunnel, and no control plane infrastructure is needed.

For **multi-site EVPN fabrics** with dozens of VTEPs, FRRouting's BGP EVPN control plane is essential. It automates MAC learning, eliminates flooding, and supports multi-tenant segmentation with separate VNIs per tenant. Pair FRR with OVS or Linux native VXLAN interfaces for the data plane.

For **cloud-native environments** running OpenStack or Kubernetes, OVN provides the most complete solution. Its centralized control plane automatically provisions VXLAN tunnels as workloads are scheduled, and its logical router eliminates the need for external routing daemons.

For related reading on overlay networking, see our [ZeroTier vs Nebula vs Netmaker guide](../2026-04-17-zerotier-vs-nebula-vs-netmaker-self-hosted-overlay-networks/) for alternative approaches to cross-site connectivity, and our [SDN controller comparison](../2026-05-23-self-hosted-sdn-controllers-onos-vs-floodlight-vs-faucet/) for broader SDN orchestration options.

## FAQ

### What is the difference between VXLAN and a VPN?
VXLAN operates at Layer 2 (Ethernet) and extends broadcast domains across IP networks, while VPNs operate at Layer 3 (IP) or above and provide encrypted point-to-point tunnels. VXLAN is designed for data center overlay networking; VPNs are designed for secure remote access. You can combine both by running VXLAN over an IPsec tunnel.

### Do I need BGP for VXLAN?
No. VXLAN works in two modes: (1) **Head-end replication** (static VTEP configuration) for small deployments, and (2) **EVPN control plane** (BGP-based) for larger multi-site fabrics. BGP EVPN is recommended when you have more than 4-6 VTEPs or need multi-tenant isolation.

### What UDP port does VXLAN use?
VXLAN uses UDP port 4789 by default (IANA-assigned). Some implementations allow custom ports. Ensure your firewalls allow UDP 4789 between all VTEP endpoints.

### Can VXLAN run over the public internet?
Yes, but with caveats. VXLAN adds 50 bytes of overhead (outer IP + UDP + VXLAN header), which can cause MTU issues on links with 1500-byte MTU. For internet transit, use VXLAN over IPsec/WireGuard for encryption, and ensure path MTU is at least 1550 bytes.

### How does OVN compare to Kubernetes CNI plugins?
OVN is itself a Kubernetes CNI plugin (OVN-Kubernetes). It provides more features than simpler CNIs like Flannel — including network policies, distributed logical routing, and load balancing. If you need advanced networking beyond basic pod connectivity, OVN-Kubernetes is a strong choice over Flannel or Calico.

### What is the maximum number of VXLAN segments?
VXLAN uses a 24-bit VNI field, supporting 16,777,216 (2^24) logical segments. This far exceeds the 4,096 limit of 802.1Q VLANs and is sufficient for any practical multi-tenant deployment.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted VXLAN Tunneling: Open vSwitch vs FRRouting vs OVN (2026)",
  "description": "Compare open-source VXLAN tunneling solutions — Open vSwitch, FRRouting (VXLAN EVPN), and OVN. Full guide with Docker deployment configs, EVPN control plane setup, and multi-site overlay networking.",
  "datePublished": "2026-05-12",
  "dateModified": "2026-05-12",
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
