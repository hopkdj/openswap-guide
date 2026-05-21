---
title: "Self-Hosted VXLAN Termination Gateways: OVN vs Open vSwitch vs FRRouting"
date: "2026-05-21"
tags: ["networking", "vxlan", "overlay", "ovn", "openvswitch", "frrouting", "self-hosted"]
draft: false
---

VXLAN (Virtual Extensible LAN) has become the de facto standard for network overlay infrastructure in data centers and cloud environments. By encapsulating Layer 2 Ethernet frames within UDP packets, VXLAN enables virtual networks that span across physical Layer 3 boundaries. However, deploying VXLAN at scale requires robust termination points — gateways that handle VTEP (VXLAN Tunnel Endpoint) operations, MAC learning, and routing between overlay and underlay networks. In this guide, we compare three open-source VXLAN termination solutions: OVN (Open Virtual Network), Open vSwitch (OVS), and FRRouting (FRR).

## OVN (Open Virtual Network)

OVN is a software-defined networking (SDN) solution built on top of Open vSwitch. It provides native VXLAN support with logical switching and routing capabilities, making it one of the most comprehensive VXLAN termination platforms available.

**Key Features:**
- Native VXLAN termination with hardware VTEP support
- Distributed logical routing between overlay networks
- Integrated DHCP and DNS services for overlay tenants
- ACL and security group enforcement at the VTEP level
- Support for both Geneve and VXLAN encapsulation

**Installation and VXLAN configuration:**
```bash
# Install OVN
apt-get install ovn-host ovn-central -y

# Initialize the OVN northbound and southbound databases
ovn-sbctl init
ovn-nbctl init

# Create a logical switch with VXLAN
ovn-nbctl ls-add ls-vxlan0
ovn-nbctl lsp-add ls-vxlan0 lsp-port1
ovn-nbctl lsp-set-addresses lsp-port1 "00:00:00:00:01:01 10.0.1.1"

# Configure VXLAN tunnel to remote VTEP
ovn-nbctl lsp-add ls-vxlan0 lsp-vxlan-remote
ovn-nbctl lsp-set-type lsp-vxlan-remote remote
ovn-nbctl lsp-set-addresses lsp-vxlan-remote unknown
ovn-nbctl lsp-set-options lsp-vxlan-remote remote_ip=192.168.1.100 key=5000
```

**Docker Compose for OVN test environment:**
```yaml
version: "3.8"
services:
  ovn-central:
    image: docker.io/ovn/ovn-central:latest
    network_mode: host
    volumes:
      - /var/run/openvswitch:/var/run/openvswitch
      - /var/run/ovn:/var/run/ovn
    environment:
      - OVN_CENTRAL=true
    restart: unless-stopped

  ovn-controller:
    image: docker.io/ovn/ovn-host:latest
    network_mode: host
    volumes:
      - /var/run/openvswitch:/var/run/openvswitch
      - /var/run/ovn:/var/run/ovn
    depends_on:
      - ovn-central
    restart: unless-stopped
```

OVN's VXLAN implementation includes MAC learning, ARP suppression, and distributed routing. The northbound database stores logical network topology, while the southbound database handles physical binding and tunnel state. OVN controllers on each host translate logical flows into OpenFlow rules in the local OVS instance.

## Open vSwitch (OVS)

Open vSwitch is the foundational virtual switch that powers OVN, but it can also be used standalone for VXLAN termination. OVS provides a programmable switching layer with support for VXLAN tunnels, flow-based forwarding, and OpenFlow integration.

**Key Features:**
- VXLAN tunnel endpoint (VTEP) termination
- Flow-based forwarding with OpenFlow 1.3+
- Hardware offload support for VXLAN decapsulation
- Integration with Linux network namespaces for tenant isolation
- Support for VXLAN-GPE (Generic Protocol Extension)

**Standalone VXLAN configuration:**
```bash
# Create a bridge for VXLAN termination
ovs-vsctl add-br br-vxlan

# Add a VXLAN port to the bridge
ovs-vsctl add-port br-vxlan vxlan0 --   set interface vxlan0 type=vxlan   options:remote_ip=192.168.1.100   options:key=5000

# Add a physical interface as uplink
ovs-vsctl add-port br-vxlan eth1

# Verify VXLAN tunnel status
ovs-vsctl list interface vxlan0
ovs-ofctl dump-flows br-vxlan
```

**Advanced VXLAN with multiple tunnels:**
```bash
# Create VXLAN tunnel group
ovs-vsctl add-br br-vxlan-multi

for vni in 100 200 300; do
  ovs-vsctl add-port br-vxlan-multi vxlan${vni} --     set interface vxlan${vni} type=vxlan     options:remote_ip=192.168.1.${vni}     options:key=${vni}
done

# Set up flow rules for VNI-based forwarding
ovs-ofctl add-flow br-vxlan-multi   "table=0, tun_id=100 actions=output:vxlan100"
ovs-ofctl add-flow br-vxlan-multi   "table=0, tun_id=200 actions=output:vxlan200"
```

**Docker Compose for OVS VXLAN gateway:**
```yaml
version: "3.8"
services:
  ovs-vxlan:
    image: docker.io/openvswitch/ovn:latest
    privileged: true
    network_mode: host
    volumes:
      - /lib/modules:/lib/modules:ro
      - /var/run/openvswitch:/var/run/openvswitch
    command: ["ovs-vswitchd", "--pidfile", "--detach", "--log-file"]
    restart: unless-stopped
```

OVS is the most flexible option for VXLAN termination when you need fine-grained control over forwarding rules. Its OpenFlow integration allows you to implement custom traffic engineering, load balancing, and packet modification at the VTEP level.

## FRRouting (FRR)

FRRouting is a routing protocol suite that supports VXLAN integration through its BGP EVPN implementation. FRR can serve as a VXLAN termination gateway by using BGP EVPN to advertise MAC and IP reachability across the overlay network.

**Key Features:**
- BGP EVPN for VXLAN control plane
- Integrated routing protocols (BGP, OSPF, IS-IS) for underlay
- VRF-aware VXLAN routing
- Support for VXLAN asymmetric and symmetric IRB
- Anycast VTEP for high availability

**FRR VXLAN + BGP EVPN configuration:**
```bash
# Install FRRouting
apt-get install frr frr-pythontools -y

# Enable FRR daemons
cat > /etc/frr/daemons << 'FRR'
bgpd=yes
zebra=yes
vrrpd=yes
pimd=yes
FRR

# Configure VXLAN interface
cat > /etc/frr/frr.conf << 'CONF'
! Zebra configuration for VXLAN
vni 5000
  vxlan localvtep 10.0.0.1
  rd auto
  route-target import 5000:5000
  route-target export 5000:5000

! BGP EVPN configuration
router bgp 65000
  bgp router-id 10.0.0.1
  neighbor 10.0.0.2 remote-as 65000
  neighbor 10.0.0.2 update-source lo0

  address-family l2vpn evpn
    neighbor 10.0.0.2 activate
    advertise-all-vni

  vni 5000
    rd auto
    route-target import 5000:5000
    route-target export 5000:5000

interface vxlan0
  vxlan id 5000
  vxlan localvtep 10.0.0.1
  bridge access 100
CONF

# Restart FRR to apply configuration
systemctl restart frr
```

**Docker Compose for FRR VXLAN gateway:**
```yaml
version: "3.8"
services:
  frr-vxlan:
    image: docker.io/frrouting/frr:latest
    privileged: true
    network_mode: host
    volumes:
      - ./frr.conf:/etc/frr/frr.conf:ro
      - ./daemons:/etc/frr/daemons:ro
    restart: unless-stopped
```

FRR's approach to VXLAN termination is fundamentally different from OVN and OVS. Rather than handling VXLAN at the data plane (switching level), FRR uses BGP EVPN as the control plane to distribute MAC and IP reachability information. The actual VXLAN encapsulation is handled by the Linux kernel's vxlan module, while FRR manages the routing intelligence.

## Comparison Table

| Feature | OVN | Open vSwitch | FRRouting |
|---------|-----|-------------|-----------|
| **Primary Role** | SDN overlay | Virtual switch | Routing protocol suite |
| **VXLAN Termination** | Native VTEP | Native VTEP | Kernel VTEP + BGP EVPN |
| **Control Plane** | OVN northbound DB | OpenFlow | BGP EVPN |
| **Distributed Routing** | Yes (logical router) | Via OpenFlow rules | Via BGP EVPN |
| **MAC Learning** | Distributed | Local + controller | Via BGP EVPN |
| **Multi-tenant Isolation** | VNI-based + ACLs | VNI + namespaces | VRF-based |
| **Underlay Routing** | Relies on external | Relies on external | Built-in (BGP/OSPF/IS-IS) |
| **Hardware Offload** | Limited | Yes (NIC offload) | Kernel-dependent |
| **High Availability** | Active-active (distributed) | Active-active | Anycast VTEP |
| **GitHub Stars** | 700+ (ovn-org/ovn) | 3,900+ (openvswitch/ovs) | 4,100+ (FRRouting/frr) |
| **Last Updated** | Active (2026) | Active (2026) | Active (2026) |
| **Kubernetes Integration** | Via OVN-Kubernetes CNI | Via Multus | Via MetalLB/BGP |

## Why Self-Host a VXLAN Termination Gateway?

VXLAN overlays are essential for modern data center networking, enabling tenant isolation, network virtualization, and seamless workload migration across physical boundaries. The choice of VXLAN termination gateway directly impacts your network's performance, operational complexity, and scalability.

Self-hosting VXLAN infrastructure eliminates dependency on vendor-specific overlay solutions and their associated licensing costs. Open-source VXLAN gateways provide the same encapsulation and routing capabilities as proprietary alternatives, with the added benefit of community-driven development and transparent security auditing.

For organizations running private clouds or edge computing deployments, self-hosted VXLAN gateways enable consistent networking across heterogeneous infrastructure. Whether connecting Kubernetes clusters, virtual machine environments, or bare-metal workloads, a standardized VXLAN overlay ensures uniform network policies and security controls.

The operational benefits include centralized network policy management, automated VTEP provisioning, and integrated monitoring. With proper VXLAN termination, network teams can provision isolated tenant networks on demand, apply security policies consistently, and troubleshoot connectivity issues using familiar overlay abstractions.

For related reading on overlay networking, see our [Geneve overlay networking guide](../2026-05-19-self-hosted-geneve-overlay-networking-ovn-ovs-linux-guide/) and [Kubernetes multi-cluster networking](../2026-05-01-karmada-vs-liqo-vs-submariner-self-hosted-multi-cluster-kubernetes-networking/).

## Choosing the Right VXLAN Termination Solution

**Choose OVN if:** You need a full-featured SDN solution with integrated logical switching, routing, and security policies. OVN provides the most complete VXLAN termination experience, with native distributed routing and built-in DHCP/DNS services for overlay tenants.

**Choose Open vSwitch if:** You need maximum flexibility in VXLAN data plane programming. OVS with OpenFlow allows custom forwarding logic, traffic engineering, and packet manipulation at the VTEP level. It is ideal for research environments or organizations with unique VXLAN requirements.

**Choose FRRouting if:** You need BGP EVPN as the VXLAN control plane with integrated underlay routing. FRR's approach is best suited for service provider environments or large data centers where BGP is already the underlay protocol and EVPN provides the overlay intelligence.

## FAQ

### What is VXLAN termination and why does it matter?
VXLAN termination is the process of encapsulating and decapsulating VXLAN packets at tunnel endpoints (VTEPs). It matters because every VXLAN packet must be properly terminated to extract the inner Ethernet frame and deliver it to the correct destination. The termination gateway handles MAC address learning, ARP resolution, and routing between overlay and underlay networks.

### What is the difference between OVN and Open vSwitch for VXLAN?
Open vSwitch is the underlying virtual switch that handles packet forwarding and VXLAN encapsulation. OVN is a higher-level SDN solution built on top of OVS that adds logical networking abstractions, distributed routing, and centralized management. OVN uses OVS as its data plane but provides a much richer control plane through its northbound and southbound databases.

### What is BGP EVPN and how does FRR use it for VXLAN?
BGP EVPN (Ethernet VPN) is a control plane protocol that distributes MAC and IP reachability information across VXLAN tunnels. FRR uses BGP EVPN to advertise which VTEPs can reach which MAC addresses and IP subnets. This eliminates the need for flood-and-learn behavior and enables efficient unicast VXLAN forwarding.

### Can I run multiple VXLAN gateways for high availability?
Yes. OVN provides active-active high availability through its distributed architecture — each OVN controller handles local VTEP termination. OVS supports active-active with multiple VTEPs sharing the same VNI. FRR supports Anycast VTEP, where multiple gateways share the same VTEP IP address and BGP EVPN handles the routing.

### What VNI range should I use for production VXLAN?
VXLAN Network Identifiers (VNIs) are 24-bit values (0–16,777,215). RFC 7348 recommends avoiding VNI 0. For production, use a structured allocation plan: VNIs 1-1000 for infrastructure networks, 1001-10000 for tenant networks, and 10001+ for testing. Document your VNI assignments to prevent conflicts.

### Does VXLAN work over WAN links?
VXLAN can work over WAN links, but the 50-byte VXLAN header overhead and UDP encapsulation can impact performance. For WAN deployments, consider VXLAN-GPE (Generic Protocol Extension) which adds support for additional protocol types, or use Geneve as an alternative with more flexible header options. MTU configuration is critical — ensure all links support at least 1600 bytes to accommodate VXLAN encapsulation.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted VXLAN Termination Gateways: OVN vs Open vSwitch vs FRRouting",
  "description": "Compare open-source VXLAN termination gateways for overlay networking — OVN, Open vSwitch, and FRRouting with Docker deployment and BGP EVPN configuration guides.",
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
