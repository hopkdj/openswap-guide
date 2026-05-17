---
title: "Self-Hosted GRE Tunnel Management — Open vSwitch vs Linux GRE vs GRETAP (2026)"
date: "2026-05-18"
tags: ["gre", "tunneling", "networking", "openvswitch", "self-hosted", "overlay-network", "vxlan"]
draft: false
---

Generic Routing Encapsulation (GRE) is a tunneling protocol that encapsulates one network layer protocol inside another, creating virtual point-to-point links between routers. GRE tunnels are widely used for connecting separated network segments, building overlay networks, transporting multicast traffic, and extending layer 2 domains across layer 3 infrastructure.

In this guide, we compare three approaches to self-hosted GRE tunnel management: **Linux Kernel GRE (ip tunnel)**, **Open vSwitch (OVS) GRE**, and **GRETAP (Layer 2 GRE)** — covering configuration, Docker deployment, performance, and use cases.

## What Is GRE Tunneling?

GRE (RFC 2784, RFC 2890) is a lightweight tunneling protocol that wraps packets from one network inside packets of another network. The outer header routes the packet through the transport network, while the inner header reaches the final destination after decapsulation.

Key use cases for GRE tunnels:

- **Site-to-site connectivity**: Connect remote office networks over the internet
- **Overlay networks**: Build virtual networks on top of physical infrastructure
- **Multicast transport**: Carry multicast traffic across unicast-only networks
- **Protocol translation**: Transport non-IP protocols (IPv6 over IPv4, IPX, AppleTalk)
- **Layer 2 extension**: Extend Ethernet segments across routed networks (GRETAP)

Unlike IPsec, GRE does not encrypt traffic — it only encapsulates it. For secure tunnels, GRE is often combined with IPsec (GRE-over-IPsec or IPsec-transport-mode GRE).

## Comparison: Linux GRE vs Open vSwitch vs GRETAP

| Feature | Linux Kernel GRE | Open vSwitch GRE | GRETAP |
|---------|-----------------|-----------------|--------|
| **Type** | Layer 3 (IP-in-IP) | Layer 2/3 tunnel | Layer 2 (Ethernet-in-IP) |
| **Kernel Module** | ip_gre | openvswitch | ip_gre (type gretap) |
| **Configuration Tool** | iproute2 (ip tunnel) | ovs-vsctl | iproute2 (ip link) |
| **Key/Sequence Support** | Yes (RFC 2890) | Yes | Yes |
| **Checksum Support** | Yes | Yes | Yes |
| **MTU Overhead** | 24 bytes | 24 bytes | 38 bytes |
| **Multicast Support** | Yes | Yes | Yes |
| **VXLAN Integration** | No | Native (same OVS) | No |
| **Flow-Based Tunneling** | No | Yes | No |
| **Docker Support** | Via host network | Official images | Via host network |
| **Performance** | Kernel-native (fastest) | Userspace/kernel hybrid | Kernel-native |
| **Management Complexity** | Low | Medium | Low |
| **GitHub Stars (OVS)** | — | 3,951+ | — |
| **License** | GPL-2.0 | Apache-2.0 | GPL-2.0 |

## Linux Kernel GRE — Simple and Fast

The Linux kernel includes native GRE support through the `ip_gre` module. It's the simplest and most performant option for basic point-to-point tunnels.

### Key Features

- **Zero overhead**: Runs entirely in the kernel with no userspace daemon
- **iproute2 integration**: Configured with standard `ip tunnel` commands
- **Key support**: Optional 32-bit key for multiplexing multiple tunnels
- **Checksum and sequencing**: Optional integrity checking per RFC 2890
- **Point-to-multipoint**: Supports point-to-multipoint configurations

### Docker Compose Deployment

GRE tunnels require host network access. Use a Docker container with `network_mode: "host"` and configure tunnels via init scripts:

```yaml
version: "3.8"

services:
  gre-tunnel:
    image: alpine:latest
    container_name: gre-manager
    hostname: gre-manager
    network_mode: "host"
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./setup-gre.sh:/setup-gre.sh:ro
    command: ["/bin/sh", "/setup-gre.sh"]
    restart: unless-stopped
```

**setup-gre.sh**:

```bash
#!/bin/sh
# Create GRE tunnel
ip tunnel add gre0 mode gre remote 203.0.113.2 local 203.0.113.1 ttl 255
ip tunnel change gre0 key 1234
ip link set gre0 up
ip addr add 10.100.0.1/30 dev gre0

# Or for IPv4-in-IPv6 GRE
ip tunnel add gre6 mode gre6 remote 2001:db8::2 local 2001:db8::1 ttl 255
ip link set gre6 up
ip addr add fd00::1/64 dev gre6
```

### Native Configuration

```bash
# Load kernel module
sudo modprobe ip_gre

# Create GRE tunnel (point-to-point)
sudo ip tunnel add gre0 mode gre   remote 203.0.113.2   local 203.0.113.1   ttl 255   key 1234

# Bring up the tunnel interface
sudo ip link set gre0 up

# Assign IP address
sudo ip addr add 10.100.0.1/30 dev gre0

# Verify
ip tunnel show gre0
ip -s link show gre0
ping -c 3 10.100.0.2
```

**Persistent configuration** (Debian/Ubuntu `/etc/network/interfaces`):

```
auto gre0
iface gre0 inet static
  address 10.100.0.1/30
  pre-up ip tunnel add gre0 mode gre remote 203.0.113.2 local 203.0.113.1 ttl 255 key 1234
  post-down ip tunnel del gre0
```

**Persistent configuration** (RHEL/CentOS `/etc/sysconfig/network-scripts/ifcfg-gre0`):

```
DEVICE=gre0
TYPE=GRE
BOOTPROTO=none
ONBOOT=yes
PEER_OUTER_IPADDR=203.0.113.2
LOCAL_OUTER_IPADDR=203.0.113.1
TTL=255
KEY=1234
IPADDR=10.100.0.1
PREFIX=30
```

## Open vSwitch GRE — Programmable and Feature-Rich

Open vSwitch (OVS) provides a programmable virtual switch with native GRE tunnel support. It's the most flexible option for complex network topologies, especially when combined with VXLAN or other overlay protocols.

### Key Features

- **Flow-based tunneling**: Use OpenFlow rules to dynamically direct traffic to GRE tunnels
- **Multi-protocol support**: GRE, VXLAN, Geneve, STT in a single switch
- **OVSDB management**: Centralized configuration via OVSDB protocol
- **Integration with SDN controllers**: Works with OpenDaylight, ONOS, Ryu
- **Hardware offload**: Supports NIC offloading for GRE encapsulation on compatible hardware
- **Monitoring**: Built-in statistics and port mirroring

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  ovs-gre:
    image: openvswitch/ovs:latest
    container_name: ovs-gre
    hostname: ovs-gre
    cap_add:
      - NET_ADMIN
      - NET_RAW
      - SYS_ADMIN
    network_mode: "host"
    volumes:
      - /var/run/openvswitch:/var/run/openvswitch
      - ovs-db:/etc/openvswitch
    command: >
      bash -c "
        ovs-vswitchd --pidfile --detach &&
        ovs-vsctl --may-exist br-add br0 &&
        ovs-vsctl --may-exist add-port br0 gre0 -- set interface gre0 type=gre options:remote_ip=203.0.113.2 options:key=1234 &&
        ip addr add 10.100.0.1/30 dev br0 &&
        ip link set br0 up &&
        tail -f /dev/null
      "
    restart: unless-stopped

volumes:
  ovs-db:
```

### Native Configuration

```bash
# Install Open vSwitch
sudo apt install openvswitch-switch

# Create bridge
sudo ovs-vsctl add-br br0

# Add physical interface
sudo ovs-vsctl add-port br0 eth0

# Add GRE tunnel port
sudo ovs-vsctl add-port br0 gre0   -- set interface gre0 type=gre   options:remote_ip=203.0.113.2   options:key=1234   options:df_default=true

# Verify
sudo ovs-vsctl show
sudo ovs-ofctl dump-flows br0
sudo ovs-vsctl list interface gre0
```

### GRE with Flow-Based Tunneling

```bash
# Set up OpenFlow rules for GRE tunnel
sudo ovs-ofctl add-flow br0   "in_port=eth0,dl_type=0x0800,nw_dst=10.200.0.0/24,action=set_tunnel:0x456,output:gre0"

sudo ovs-ofctl add-flow br0   "in_port=gre0,action=strip_tunnel,normal"

# Verify flows
sudo ovs-ofctl dump-flows br0
```

## GRETAP — Layer 2 Over IP

GRETAP is a variant of GRE that encapsulates full Ethernet frames (Layer 2) instead of IP packets (Layer 3). This allows you to extend Ethernet segments across routed networks — useful for VM migration, stretched VLANs, and connecting bridge domains.

### Key Features

- **Layer 2 transport**: Carries full Ethernet frames, not just IP packets
- **Transparent bridging**: End hosts see a single broadcast domain
- **VM migration support**: Enables live VM migration across data centers
- **VLAN passthrough**: Preserves 802.1Q tags across the tunnel
- **Simple configuration**: Uses the same `ip link` tools as regular GRE

### Native Configuration

```bash
# Load kernel module
sudo modprobe ip_gre

# Create GRETAP tunnel
sudo ip link add gretap0 type gretap   remote 203.0.113.2   local 203.0.113.1   ttl 255   key 5678

# Bring up the tunnel
sudo ip link set gretap0 up

# Add to bridge
sudo ip link add name br-lan type bridge
sudo ip link set gretap0 master br-lan
sudo ip link set eth1 master br-lan
sudo ip link set br-lan up

# Verify
ip -d link show gretap0
bridge link show
```

**MTU consideration**: GRETAP adds 38 bytes of overhead (24 GRE + 14 Ethernet). If your physical interface has MTU 1500, set the tunnel MTU to 1462:

```bash
ip link set gretap0 mtu 1462
```

### Persistent Configuration (NetworkManager)

```bash
# Create GRETAP connection
sudo nmcli connection add type ip-tunnel   con-name gretap0   ifname gretap0   mode gretap   remote 203.0.113.2   local 203.0.113.1   ip-tunnel.key 5678

# Activate
sudo nmcli connection up gretap0
```

## Choosing the Right GRE Approach

### Choose Linux Kernel GRE when:

- You need **simple point-to-point** tunnels with minimal overhead
- You want the **fastest performance** (kernel-native, zero userspace)
- You're connecting **two sites** with a straightforward topology
- You don't need **programmability** or SDN integration
- You want to use **standard iproute2** tools

### Choose Open vSwitch GRE when:

- You need **flow-based tunneling** with dynamic path selection
- You're building **overlay networks** with multiple tunnel types
- You want **SDN controller integration** (OpenDaylight, ONOS)
- You need **centralized management** via OVSDB
- You're running **virtualized environments** (KVM, containers)
- You need **hardware offload** on compatible NICs

### Choose GRETAP when:

- You need **Layer 2 extension** across routed networks
- You're enabling **live VM migration** between data centers
- You want to **stretch VLANs** across sites
- You need to transport **non-IP protocols** over IP
- You're building **stretched Layer 2 domains** for clustering

## GRE Tunnel Best Practices

1. **Set proper MTU**: Account for 24-byte GRE overhead. If physical MTU is 1500, tunnel MTU should be 1476
2. **Use tunnel keys**: Keys prevent accidental misconfiguration and allow multiplexing
3. **Enable checksums**: For critical links, enable GRE checksums to detect corruption
4. **Monitor tunnel state**: Use `ip -s link` or `ovs-vsctl list interface` to monitor packet counts
5. **Combine with IPsec**: For untrusted networks, wrap GRE in IPsec for encryption
6. **Use PMTUD**: Enable Path MTU Discovery to avoid fragmentation issues
7. **Consider alternatives**: For new deployments, evaluate VXLAN or Geneve for richer feature sets

## Why Self-Host GRE Tunnels?

GRE tunneling infrastructure gives you the ability to connect distributed networks without depending on third-party VPN services or managed overlay providers. With open-source tools, you can:

- **Build site-to-site connectivity** using commodity hardware
- **Create overlay networks** for multi-tenant environments
- **Transport multicast** traffic across unicast-only infrastructure
- **Extend Layer 2** domains for VM migration and clustering
- **Integrate with SDN** controllers for programmable networking

For **VXLAN overlay networks**, see our [VXLAN tunneling guide](../2026-05-12-self-hosted-vxlan-tunneling-ovs-frr-ovn-guide.). If you need **WireGuard mesh** connectivity, check our [WireGuard mesh networking article](../2026-05-15-self-hosted-wireguard-mesh-networking-webmesh-wir.). For **L2TP/IPsec alternatives**, our [L2TP IPsec VPN guide](../2026-05-17-l2tp-ipsec-vpn-xl2tpd-accel-ppp-linux-l2tpv3-guid.) covers those options.

For **VXLAN overlay networks** as an alternative to GRE, see our [VXLAN tunneling guide](../2026-05-12-self-hosted-vxlan-tunneling-ovs-frr-ovn-guide/). If you need **WireGuard mesh** connectivity for secure tunneling, check our [WireGuard mesh networking article](../2026-05-15-self-hosted-wireguard-mesh-networking-webmesh-wir/). For **L2TP/IPsec** as an encrypted tunneling alternative, our [L2TP IPsec VPN guide](../2026-05-17-l2tp-ipsec-vpn-xl2tpd-accel-ppp-linux-l2tpv3-guid/) covers those options.

## FAQ

### What is the difference between GRE and GRETAP?

GRE (Generic Routing Encapsulation) operates at Layer 3, encapsulating IP packets inside IP packets. GRETAP operates at Layer 2, encapsulating full Ethernet frames inside IP packets. Use GRE for routing between subnets; use GRETAP when you need transparent Layer 2 bridging across sites (e.g., for VM migration or stretched VLANs).

### How much overhead does GRE add?

Standard GRE adds 24 bytes of overhead: 4 bytes for the GRE header and 20 bytes for the outer IPv4 header. If you enable keys and checksums (RFC 2890), add 4 more bytes for a total of 28 bytes. GRETAP adds 38 bytes total (24 GRE + 14 Ethernet frame header).

### Can GRE carry multicast traffic?

Yes, GRE can transport multicast traffic across unicast-only networks. This is one of GRE's key advantages over IPsec transport mode. Both Linux kernel GRE and Open vSwitch GRE support multicast forwarding. Configure `ip tunnel add gre0 mode gre ...` and add multicast routes as needed.

### Should I use GRE or VXLAN for overlay networks?

For new overlay deployments, VXLAN is generally preferred over GRE because it supports multi-tenancy (VNI), has better ecosystem support (OVS, Kubernetes CNI plugins), and offers hardware offload on modern NICs. GRE is simpler and sufficient for basic point-to-point tunnels. Geneve is the newest option with extensible headers.

### Is GRE secure?

GRE does not provide encryption or authentication by itself. It only encapsulates packets. For secure communication, combine GRE with IPsec (GRE-over-IPsec or IPsec transport mode with GRE payloads). Alternatively, use WireGuard or OpenVPN if you need built-in encryption.

### Can I run GRE tunnels in Docker containers?

Yes, but the container needs `network_mode: "host"`, `NET_ADMIN`, and `NET_RAW` capabilities. The GRE tunnel is created in the host kernel namespace, so the container can configure it via iproute2. For production, consider running a dedicated routing container (FRR, BIRD) with host networking.

### What is the maximum MTU for a GRE tunnel?

The tunnel MTU should be the physical interface MTU minus the GRE overhead. For standard Ethernet (MTU 1500): GRE MTU = 1500 - 24 = 1476. GRETAP MTU = 1500 - 38 = 1462. If using jumbo frames (MTU 9000): GRE MTU = 8976, GRETAP MTU = 8962.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted GRE Tunnel Management — Open vSwitch vs Linux GRE vs GRETAP (2026)",
  "description": "Compare GRE tunneling approaches: Linux kernel GRE, Open vSwitch GRE, and GRETAP. Learn Docker deployment, configuration, and best practices.",
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
