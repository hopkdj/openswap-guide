---
title: "Self-Hosted PIM Multicast Routing Daemons: pimd vs pim6sd vs smcroute"
date: "2026-05-20"
tags: ["networking", "multicast", "routing", "pim", "self-hosted"]
draft: false
---

IP multicast enables efficient one-to-many data distribution — a single source sends traffic once, and the network delivers it to all interested receivers. Protocol Independent Multicast (PIM) is the routing protocol that builds distribution trees for multicast traffic across network segments.

For self-hosted networks, home labs, and enterprise infrastructure, running a PIM daemon on Linux routers enables multicast routing without proprietary hardware. This guide compares three open-source PIM implementations: **pimd** for IPv4 PIM-SM/SSM, **pim6sd** for IPv6 PIM, and **smcroute** for static multicast routing.

## What Is PIM Multicast Routing?

Multicast routing differs from unicast (one-to-one) and broadcast (one-to-all) in that it delivers traffic only to receivers that explicitly request it. PIM works "independently" of the unicast routing protocol — it uses the existing unicast routing table to determine reverse paths but builds its own multicast distribution trees.

### PIM Operating Modes

- **PIM-SM (Sparse Mode)**: Uses a Rendezvous Point (RP) as a meeting point. Receivers join toward the RP, sources register with the RP. Most widely deployed.
- **PIM-SSM (Source-Specific Multicast)**: Receivers specify both the source and group address. No RP needed. Used for IPTV, video conferencing.
- **PIM-DM (Dense Mode)**: Floods traffic everywhere, then prunes branches without receivers. Rarely used in production.

### Use Cases

- **IPTV and video streaming**: Efficient distribution to multiple endpoints
- **Financial market data**: Real-time stock ticker distribution
- **Service discovery**: mDNS/Bonjour gateway across VLANs
- **IoT telemetry**: Sensor data distribution to multiple subscribers
- **Cluster communication**: Node-to-node messaging in distributed systems

## Tool Comparison Overview

| Feature | pimd | pim6sd | smcroute |
|---------|------|--------|----------|
| **GitHub Stars** | 214 | 24 | 284 |
| **IP Version** | IPv4 only | IPv6 only | IPv4 + IPv6 |
| **Protocol** | PIM-SM/SSM | PIM-SM/SSM | Static multicast routing |
| **Dynamic Routing** | Yes | Yes | No (static rules) |
| **RP Configuration** | Static or BSR | Static | N/A |
| **Kernel Dependency** | Linux multicast routing table | Linux multicast routing table | Linux multicast routing table |
| **Configuration Format** | Conf file | Conf file | Conf file |
| **Complexity** | Medium | Medium | Low |
| **Best For** | IPv4 multicast networks | IPv6 multicast networks | Simple static multicast |

## pimd — IPv4 PIM-SM/SSM Daemon

**pimd** is a lightweight PIM-SM/SSM daemon for IPv4 multicast routing. It is a continuation of the original PIMD project, maintained by Joachim Wiberg (troglobit). It supports both sparse mode and source-specific multicast with minimal resource requirements.

### Key Features

- **PIM-SM and PIM-SSM**: Full support for both operating modes
- **Rendezvous Point (RP)**: Static RP configuration or Bootstrap Router (BSR) protocol
- **VIF (Virtual Interface) management**: Automatic detection of multicast-capable interfaces
- **IGMP proxy**: Built-in IGMPv2/IGMPv3 support for host group membership
- **Low resource usage**: Suitable for embedded devices and routers
- **Systemd integration**: Ships with systemd service files

### Docker Compose Deployment

Since pimd requires kernel multicast routing capabilities, it must run with elevated privileges:

```yaml
version: "3.8"
services:
  pimd:
    image: alpine:latest
    container_name: pimd
    cap_add:
      - NET_ADMIN
      - NET_RAW
    network_mode: "host"
    volumes:
      - ./pimd.conf:/etc/pimd.conf:ro
    command: >
      sh -c "
        apk add --no-cache pimd &&
        pimd -f -c /etc/pimd.conf
      "
    restart: unless-stopped
```

### Configuration Example

```conf
# /etc/pimd.conf

# Physical interfaces participating in multicast
phyint eth0 enable
phyint eth1 enable
phyint vlan10 enable

# Static Rendezvous Point
rp-address 10.0.0.1 priority 10

# Source-Specific Multicast range (SSM)
ssm-range 232.0.0.0/8

# Static multicast routes (optional)
sdr 239.1.1.1 eth1 eth0

# Logging
log-level info
```

Start pimd with the configuration:

```bash
pimd -f -c /etc/pimd.conf
```

Verify multicast routing table:

```bash
# Check PIM neighbors
pimctl show neighbors

# Check multicast routing entries
pimctl show mrt

# Check IGMP group membership
pimctl show groups
```

## pim6sd — IPv6 PIM-SM/SSM Daemon

**pim6sd** is the IPv6 counterpart to pimd, implementing PIM-SM/SSM for IPv6 multicast networks. It shares the same codebase philosophy and is maintained by the same author. IPv6 multicast uses different addressing (ff00::/8 range) and MLD (Multicast Listener Discovery) instead of IGMP.

### Key Features

- **IPv6 PIM-SM and PIM-SSM**: Full IPv6 multicast routing support
- **MLDv1/MLDv2**: Multicast Listener Discovery for IPv6
- **Static and BSR RP**: Configurable RP discovery
- **Kernel integration**: Uses Linux IPv6 multicast routing (CONFIG_IPV6_MROUTE)
- **Lightweight**: Same minimal footprint as pimd

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  pim6sd:
    image: alpine:latest
    container_name: pim6sd
    cap_add:
      - NET_ADMIN
      - NET_RAW
    network_mode: "host"
    volumes:
      - ./pim6sd.conf:/etc/pim6sd.conf:ro
    command: >
      sh -c "
        apk add --no-cache pim6sd &&
        pim6sd -f -c /etc/pim6sd.conf
      "
    restart: unless-stopped
```

### Configuration Example

```conf
# /etc/pim6sd.conf

# IPv6 interfaces
phyint eth0 enable
phyint eth1 enable

# Static IPv6 Rendezvous Point
rp-address fd00::1 priority 10

# IPv6 SSM range
ssm-range ff3x::/32

# Logging
log-level notice
```

Enable IPv6 multicast routing in the kernel:

```bash
# Enable multicast routing
sysctl -w net.ipv6.conf.all.mc_forwarding=1
sysctl -w net.ipv6.conf.eth0.mc_forwarding=1
sysctl -w net.ipv6.conf.eth1.mc_forwarding=1
```

Verify IPv6 multicast state:

```bash
# Check PIM neighbors
pim6sdctl show neighbors

# Check MLD groups
pim6sdctl show groups

# Kernel multicast routing table
ip -6 mroute show
```

## smcroute — Static Multicast Router

**smcroute** takes a fundamentally different approach. Instead of running a dynamic PIM protocol, it configures static multicast routes in the kernel. You explicitly define which multicast groups should be forwarded from which input interface to which output interfaces.

### Key Features

- **Static routing only**: No PIM protocol, no dynamic neighbor discovery
- **IPv4 and IPv6**: Supports both protocols in a single tool
- **Simple configuration**: One line per multicast route
- **Runtime control**: Add/remove routes via Unix socket without restart
- **Minimal overhead**: No protocol state to maintain
- **Ideal for small networks**: Perfect for home labs and simple topologies

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  smcroute:
    image: alpine:latest
    container_name: smcroute
    cap_add:
      - NET_ADMIN
      - NET_RAW
    network_mode: "host"
    volumes:
      - ./smcroute.conf:/etc/smcroute.conf:ro
    command: >
      sh -c "
        apk add --no-cache smcroute &&
        smcroute -d -f /etc/smcroute.conf
      "
    restart: unless-stopped
```

### Configuration Example

```conf
# /etc/smcroute.conf

# Static multicast route: group -> input interface -> output interfaces
# IPv4 multicast routes
mroute from eth0 group 239.1.1.1 to eth1
mroute from eth0 group 239.1.1.2 to eth1 vlan10
mroute from eth1 group 224.0.0.1 to eth0

# IPv6 multicast routes
mroute from eth0 group ff05::1 to eth1
mroute from eth1 group ff0e::abcd to eth0

# Allow any source for a group (use with caution)
mroute from eth0 group 239.255.0.0/16 to eth1
```

Runtime route management via smcroutectl:

```bash
# Add a route at runtime
smcroutectl add eth0 239.1.1.100 eth1 eth2

# Remove a route
smcroutectl del eth0 239.1.1.100 eth1

# Show current routes
smcroutectl show
```

## Why Self-Host Multicast Routing?

Multicast routing is often considered the domain of enterprise network equipment, but open-source PIM daemons make it accessible for any self-hosted network. Whether you're running IPTV in a homelab, distributing sensor data across VLANs, or building a distributed system that relies on group communication, multicast routing solves problems that unicast cannot.

### Bandwidth Efficiency

Without multicast, sending the same video stream to 100 receivers requires 100 separate unicast streams — consuming 100x the bandwidth at the source. With multicast, the source sends one stream and the network replicates it only at branch points. A 10 Mbps video stream to 100 receivers uses 10 Mbps at the source, not 1 Gbps.

### Network Segmentation

In segmented networks with multiple VLANs, multicast traffic doesn't cross VLAN boundaries by default. Running a PIM daemon on your Linux router enables controlled multicast distribution between segments. This is essential for service discovery protocols, media streaming, and cluster communication that spans multiple subnets.

### Protocol Independence

PIM works with any underlying unicast routing protocol — OSPF, BGP, static routes, or even directly connected networks. This makes it flexible for diverse network topologies. The "Protocol Independent" in PIM means it leverages whatever unicast routing is already in place rather than requiring its own topology database.

For broader routing protocol coverage, see our [BGP routing guide](../2026-04-19-frrouting-vs-bird-vs-openbgpd-self-hosted-bgp-routing-guide-2026/) and [network simulation comparison](../2026-04-18-gns3-vs-eve-ng-vs-containerlab-self-hosted-network-simulation-2026/). For GeoDNS and anycast routing, check our [DNS anycast guide](../2026-04-22-bird-vs-frrouting-vs-keepalived-self-hosted-dns-anycast-guide-2026/).

## Choosing the Right Multicast Routing Daemon

**Choose pimd** if you need IPv4 multicast routing with PIM-SM/SSM support. It's the most mature and widely deployed open-source PIM daemon for IPv4, with active maintenance and good documentation.

**Choose pim6sd** if your network uses IPv6 multicast. It provides the same PIM-SM/SSM functionality adapted for IPv6's MLD-based group membership and ff00::/8 multicast addressing.

**Choose smcroute** if you have a small, static network topology where the multicast groups and interfaces are known in advance. It's simpler to configure, has no protocol overhead, and works for both IPv4 and IPv6. It's ideal for home labs and environments where dynamic RP discovery isn't needed.

## FAQ

### Do I need to enable kernel multicast routing for these tools?
Yes. All three tools require the Linux kernel multicast routing subsystem. For IPv4, ensure `CONFIG_IP_MROUTE` is enabled (usually built into most distributions). For IPv6, ensure `CONFIG_IPV6_MROUTE` is enabled. Enable forwarding with `sysctl net.ipv4.conf.all.mc_forwarding=1` or `sysctl net.ipv6.conf.all.mc_forwarding=1`.

### Can I run pimd and pim6sd on the same router?
Yes. Since they handle different IP versions, they can run simultaneously on the same system. Each daemon manages its own protocol state and kernel multicast routing table entries.

### What is the difference between PIM-SM and PIM-SSM?
PIM-SM (Sparse Mode) uses a Rendezvous Point (RP) as a central meeting point for sources and receivers. PIM-SSM (Source-Specific Multicast) eliminates the RP by having receivers specify the exact source address along with the group address. SSM is simpler and more secure but requires receivers to know the source address.

### Does smcroute support dynamic multicast group discovery?
No. smcroute is purely static — you must explicitly configure each multicast route. It does not run IGMP, MLD, or PIM protocols. If you need dynamic group discovery, use pimd (for IPv4) or pim6sd (for IPv6).

### How do I test if multicast routing is working?
Use `iperf3` with multicast: on the sender, run `iperf3 -c 239.1.1.1 -u -b 1M -T 1`. On the receiver, run `iperf3 -s -B 239.1.1.1`. Alternatively, use `ping` with multicast: `ping -I eth0 -t 1 224.0.0.1` and verify the packet arrives on the receiving interface.

### Can Docker containers participate in multicast groups?
Yes, but containers need `network_mode: "host"` or the `--cap-add NET_ADMIN` flag with proper network namespace configuration. Docker's default bridge network does not forward multicast traffic between containers.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted PIM Multicast Routing Daemons: pimd vs pim6sd vs smcroute",
  "description": "Compare three open-source PIM multicast routing implementations — pimd for IPv4, pim6sd for IPv6, and smcroute for static multicast — with Docker Compose configs.",
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
