---
title: "Self-Hosted BIER Forwarding: FRRouting vs FD.io VPP vs Linux Kernel (2026)"
date: "2026-05-21"
tags: ["bier", "multicast", "networking", "frrouting", "vpp", "routing"]
draft: false
---

Bit Indexed Explicit Replication (BIER) is an IETF-standard multicast forwarding architecture that eliminates the need for explicit tree-building protocols like PIM. Instead of maintaining per-flow state in every router along a distribution tree, BIER encodes the set of destinations directly in the packet header using a compact bitstring. Each bit represents a specific egress router (BFER), and intermediate routers (BFRs) forward packets based solely on the bitstring — dramatically reducing state overhead and improving scalability.

For organizations running self-hosted multicast services — IPTV distribution, financial market data feeds, IoT sensor networks, or enterprise video conferencing — BIER offers a compelling alternative to traditional PIM-SM/PIM-DM deployments. This guide compares the three primary open-source BIER implementations available today.

## What Is BIER and Why Does It Matter?

Traditional IP multicast relies on protocols like Protocol Independent Multicast (PIM) to build and maintain distribution trees. Each router in the multicast path must track group membership, maintain reverse-path forwarding state, and participate in rendezvous point discovery. In large-scale deployments with thousands of multicast groups, this per-group state becomes a significant operational burden.

BIER flips this model. Rather than building trees, BIER-capable routers maintain a simple bit index: bit position 1 maps to router A, bit position 2 to router B, and so on. When a sender wants to reach routers A, C, and F, the packet header simply sets bits 1, 3, and 6. Each intermediate router examines the bitstring, identifies which bits correspond to neighbors in its forwarding table, replicates the packet as needed, and clears bits for already-satisfied destinations.

The result: zero per-group state in core routers, simplified forwarding logic, and native support for arbitrary group topologies without protocol overhead.

## Comparison: BIER Implementations at a Glance

| Feature | FRRouting (frr) | FD.io VPP | Linux Kernel |
|---|---|---|---|
| **Stars** | 4,136+ | 1,530+ | N/A (kernel) |
| **Language** | C | C | C |
| **BIER Status** | Stable (v10+) | Experimental | Mainline (v5.15+) |
| **Deployment** | Docker / apt | Docker / apt | Kernel module |
| **Web UI** | vtysh / FRR UI | VPP CLI | iproute2 |
| **Data Plane** | Kernel / DPDK | DPDK (VPP) | Kernel netstack |
| **MPLS BIER** | Yes | Yes | Yes |
| **IPv6 BIER** | Partial | Yes | Yes |
| **BIER-TE** | Yes | Experimental | No |
| **License** | GPLv2 | Apache 2.0 | GPLv2 |

## FRRouting: Production-Grade BIER

[FRRouting](https://github.com/FRRouting/frr) is the most mature open-source BIER implementation, with support landing in version 10.0 and improving through subsequent releases. FRR's BIER implementation integrates with its existing BGP and OSPF control planes, making it a natural choice for operators already running FRR in their network.

FRR supports both MPLS-encapsulated BIER (RFC 8279) and BIER-TE (Traffic Engineering, RFC 9262), which allows explicit path control through bitstring manipulation rather than relying on the shortest-path IGP topology. This makes FRR particularly useful for traffic-engineered multicast applications like live video distribution where specific paths must be enforced.

### Docker Deployment

FRR provides official Docker images with over 4.8 million pulls on Docker Hub. Here is a production-ready Docker Compose configuration for a BIER-enabled FRR instance:

```yaml
version: "3.8"
services:
  frr-bier:
    image: frrouting/frr:stable_10.2
    container_name: frr-bier
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

Configure BIER in `/etc/frr/frr.conf`:

```
frr version 10.2
frr defaults traditional
hostname bier-edge-01

router bgp 65001
 bgp router-id 10.0.0.1
 !
 address-family ipv4 unicast
  network 10.0.0.0/24
 exit-address-family
 !
 address-family l2vpn evpn
 exit-address-family
!

bier
 bier forwarding-table
  sub-domain 0
   bit-string-length 256
   bfr-id 1
   bfr-prefix 10.0.0.1
 exit-sub-domain
 exit-bier-ft
!
 router ospf
  network 10.0.0.0/24 area 0.0.0.0
  bier sub-domain 0
 exit-router
!
```

### Key BIER Configuration Points

- **Bit String Length (BSL)**: Determines how many BFERs can be encoded in a single packet. FRR supports 64, 128, 256, 512, and 1024-bit strings. Choose based on your network size.
- **BFR-ID**: Unique identifier for each BIER Forwarding Router. Must be unique within the BIER domain.
- **Sub-domain**: Allows multiple independent BIER topologies within the same physical network. Useful for multi-tenant environments.
- **BIER-TE**: For explicit path control, enable BIER-TE and define adjacency bit positions for each desired hop.

## FD.io VPP: High-Performance Data Plane

[FD.io VPP](https://github.com/FDio/vpp) (Vector Packet Processing) is a high-performance packet processing platform originally developed by Cisco. VPP's BIER implementation leverages its DPDK-based data plane to achieve line-rate multicast forwarding at millions of packets per second.

VPP is ideal for BIER deployments where throughput is the primary concern — CDN edge nodes, financial market data distribution, or high-frequency trading multicast feeds. The vector processing architecture processes packets in batches, amortizing the per-packet overhead of bitstring parsing across many packets simultaneously.

### Docker Deployment

VPP is available through the `ligato/vpp-agent` Docker image (142,000+ pulls). For a standalone VPP instance with BIER:

```yaml
version: "3.8"
services:
  vpp-bier:
    image: ligato/vpp-agent:latest
    container_name: vpp-bier
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
      - IPC_LOCK
      - SYS_ADMIN
    network_mode: "host"
    volumes:
      - /dev/hugepages:/dev/hugepages
      - /dev/uio:/dev/uio
      - ./vpp.conf:/etc/vpp/startup.conf:ro
    environment:
      - VPP_CONFIG=/etc/vpp/startup.conf
```

VPP startup configuration with BIER plugin:

```
unix {
  nodaemon
  log /var/log/vpp/vpp.log
  full-coredump
  cli-listen /run/vpp/cli.sock
  gid vpp
}

api-trace {
  on
}

api-segment {
  prefix vpp
}

plugins {
  plugin bier_plugin.so { enable }
  plugin dpdk_plugin.so { enable }
}

dpdk {
  dev 0000:03:00.0
  dev 0000:03:00.1
  num-mbufs 65536
}
```

VPP's BIER support is configured through its VPP API or the `vppctl` CLI:

```
vppctl# bier bsl 256
vppctl# bier add bfr-id 1 neighbor 10.0.0.2
vppctl# bier add bfr-id 2 neighbor 10.0.0.3
vppctl# bier show bf
```

## Linux Kernel: Built-In BIER Support

Since Linux kernel 5.15, BIER forwarding has been available as a built-in kernel module (`nf_bier`). This is the simplest deployment option for organizations that want BIER without introducing additional software dependencies.

The kernel BIER implementation integrates with the Linux networking stack and uses standard `iproute2` tools for configuration. It supports both MPLS-encapsulated and IPv6-encapsulated BIER, making it suitable for modern IPv6-native networks.

### Configuration via iproute2

```bash
# Enable BIER forwarding
ip bier add interface eth0 bsl 256 bfr-id 1

# Add BIER neighbors
ip bier neighbor add bfr-id 2 via 10.0.0.2 dev eth0
ip bier neighbor add bfr-id 3 via 10.0.0.3 dev eth0

# Show BIER forwarding table
ip bier show
ip bier neighbor show
```

### When to Use Each Implementation

| Scenario | Recommended | Reason |
|---|---|---|
| Enterprise network with existing FRR | FRRouting | Seamless integration with BGP/OSPF |
| High-throughput edge distribution | FD.io VPP | DPDK line-rate performance |
| Simple IPv6-native deployment | Linux Kernel | Zero additional software |
| BIER-TE traffic engineering | FRRouting | Most mature TE support |
| Multi-tenant BIER domains | FRRouting | Sub-domain isolation |
| Container orchestration | FD.io VPP | Cloud-native architecture |

## Why Self-Host BIER Infrastructure?

Running your own BIER forwarding infrastructure gives you complete control over multicast distribution without relying on cloud provider multicast services (which are often limited in scope and geography). Self-hosted BIER enables:

**Full Control Over Topology**: Define exactly which routers participate in your BIER domain, configure bitstring allocations per tenant or service, and implement traffic engineering policies that match your application requirements.

**Cost Efficiency**: Traditional IP multicast requires every router along the distribution tree to maintain per-group state, consuming TCAM and CPU resources. BIER eliminates this overhead, reducing the hardware requirements for core routers and allowing you to run multicast on commodity x86 hardware rather than expensive carrier-grade routers.

**No Vendor Lock-In**: Cloud provider multicast services (AWS VPC multicast, Azure Multicast, GCP multicast) are limited to specific regions and VPC configurations. Self-hosted BIER works across any network infrastructure — on-premises, hybrid cloud, or multi-cloud — without geographic or provider constraints.

**Scalability**: BIER scales linearly with the number of egress routers (bit positions) rather than exponentially with the number of multicast groups. A single 256-bit BIER header can encode destinations for up to 256 routers, regardless of how many multicast groups are active.

For network operators managing large-scale multicast deployments, see our [IS-IS routing protocol comparison](../2026-05-17-isis-routing-protocol-frrouting-bird-gobgp-guide/) for control plane integration and [LLDP network discovery guide](../2026-05-11-self-hosted-lldp-network-discovery-lldpd-frr-netdisco/) for neighbor discovery. If you are deploying multicast at scale, our [PIM multicast routing guide](../2026-05-15-self-hosted-pim-multicast-routing-pimd-pim6sd-smcroute/) covers the traditional approach for comparison.

## Deployment Best Practices

### Hardware Sizing

BIER forwarding has modest hardware requirements compared to traditional multicast. The bitstring parsing operation is O(n) where n is the bit string length, and modern x86 processors can parse a 1024-bit string in microseconds. For FRR routing deployments:

- **Minimum**: 2 vCPUs, 4 GB RAM (for networks with < 64 BFERs)
- **Recommended**: 4 vCPUs, 8 GB RAM (for networks with 64-256 BFERs)
- **High-throughput**: 8+ vCPUs, 16 GB RAM, DPDK-capable NIC (for VPP deployments)

### Network Design

- **Bit String Length**: Start with 256 bits (covers most enterprise deployments). Upgrade to 512 or 1024 bits only if your network exceeds 256 egress routers.
- **Sub-domain Planning**: If you operate multiple independent multicast services (e.g., IPTV, financial data, IoT), use separate sub-domains to isolate forwarding tables.
- **BIER-TE for Critical Paths**: Use BIER-TE to enforce specific paths for latency-sensitive traffic like live video or market data feeds.

### Security Considerations

- **BIER Domain Isolation**: BIER packets should only be accepted from known BFR neighbors. Configure ACLs to drop BIER-encapsulated traffic from untrusted sources.
- **Bitstring Validation**: Validate incoming BIER bitstrings against your forwarding table before processing to prevent bitstring spoofing attacks.
- **Control Plane Security**: Secure the OSPF/BGP sessions used to distribute BIER neighbor information with MD5 authentication or TCP-AO.

## Choosing the Right BIER Implementation

For most self-hosted multicast deployments, FRRouting offers the best combination of feature completeness, community support, and ease of deployment. Its BIER implementation is production-tested, supports both standard BIER and BIER-TE, and integrates seamlessly with existing routing infrastructure.

FD.io VPP is the right choice when raw throughput is the primary concern — think CDN edge nodes distributing video to millions of viewers, or financial institutions distributing market data to trading systems. The DPDK-based data plane delivers line-rate performance that kernel-based forwarding cannot match.

The Linux kernel implementation is ideal for simple deployments where you want BIER without additional software dependencies. It is the easiest to deploy and maintain but lacks some advanced features like BIER-TE and multi-sub-domain support.

## FAQ

### What is BIER and how does it differ from traditional IP multicast?

BIER (Bit Indexed Explicit Replication) is an IETF-standard multicast architecture that encodes destination routers as bits in a packet header, eliminating the need for per-group tree-building protocols like PIM. Traditional multicast requires every router along the distribution tree to maintain per-group state; BIER requires state only at the ingress and egress routers.

### Which open-source projects support BIER?

Three primary open-source implementations exist: FRRouting (most mature, production-ready since v10), FD.io VPP (high-performance DPDK data plane, experimental BIER), and the Linux kernel (built-in since v5.15, basic BIER forwarding).

### Can BIER replace PIM in my network?

BIER can replace PIM for the data plane forwarding, but you still need an IGP (OSPF or IS-IS) to distribute BIER neighbor information. The control plane integration depends on your chosen implementation — FRRouting integrates with its existing BGP/OSPF stack, while the kernel implementation uses standard Linux routing.

### What is the maximum number of destinations BIER can encode?

The maximum depends on the Bit String Length (BSL) configured. Standard BSL values are 64, 128, 256, 512, and 1024 bits, allowing up to 1,024 egress routers in a single packet header. For larger networks, multiple BIER packets or BIER domain hierarchy can be used.

### Is BIER production-ready?

FRRouting's BIER implementation is production-ready and used in carrier networks. FD.io VPP's BIER support is experimental but suitable for high-throughput lab environments. The Linux kernel BIER module is stable for basic forwarding use cases.

### Do I need special hardware for BIER?

No. BIER forwarding runs on standard x86 hardware. For high-throughput deployments with VPP, DPDK-capable NICs are recommended but not required. The kernel and FRR implementations work on any Linux-compatible hardware.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted BIER Forwarding: FRRouting vs FD.io VPP vs Linux Kernel (2026)",
  "description": "Comprehensive comparison of open-source BIER (Bit Indexed Explicit Replication) implementations for self-hosted multicast: FRRouting, FD.io VPP, and Linux kernel.",
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
