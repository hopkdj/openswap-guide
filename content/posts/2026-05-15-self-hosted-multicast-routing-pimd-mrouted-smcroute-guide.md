---
title: "Self-Hosted Multicast Routing: pimd vs mrouted vs smcroute (2026)"
date: "2026-05-07"
draft: false
tags: ["networking", "multicast", "routing", "pimd", "mrouted", "smcroute", "self-hosted"]
---

IP multicast enables efficient one-to-many and many-to-many data distribution across networks. Instead of sending separate unicast streams to each recipient, a single multicast packet is replicated by routers only at branch points in the network topology. This model is essential for IPTV, financial market data feeds, cluster communication, and distributed sensor networks.

This guide compares three open-source multicast routing solutions: **pimd** (PIM-SM/SSM), **mrouted** (DVMRP), and **smcroute** (static multicast routing). Each implements a different approach to building multicast distribution trees.

## Understanding IP Multicast Routing

Unicast routing delivers packets from one source to one destination. Multicast routing delivers packets from one or more sources to a group of receivers identified by a multicast IP address (224.0.0.0/4 for IPv4).

Key multicast routing protocols:

- **DVMRP** (Distance Vector Multicast Routing Protocol) — The original multicast routing protocol, using flood-and-prune behavior
- **PIM-SM** (Protocol Independent Multicast — Sparse Mode) — The modern standard, using a rendezvous point to build source trees
- **PIM-SSM** (Source-Specific Multicast) — Simplified PIM where receivers specify both the source and group address
- **Static multicast routing** — Manually configured multicast forwarding entries, no protocol overhead

## pimd: PIM-SM/SSM Multicast Router

[pimd](https://github.com/troglobit/pimd) (214 stars on GitHub) implements PIM-SM and PIM-SSM for Linux and UNIX systems. It is a lightweight, standards-compliant multicast routing daemon suitable for small to medium networks.

### Key Features

- PIM-SM (Sparse Mode) with rendezvous point (RP) support
- PIM-SSM (Source-Specific Multicast) — no RP needed
- IGMPv2/IGMPv3 host group membership management
- BSD multicast routing API (mrouted-compatible)
- Lightweight: small codebase, minimal resource usage
- Configuration via simple rc-style config file

### Docker Deployment

```yaml
version: "3.8"
services:
  pimd:
    image: alpine:latest
    container_name: pimd
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./pimd.conf:/etc/pimd.conf:ro
    command: sh -c "apk add pimd && pimd -f /etc/pimd.conf"
    restart: unless-stopped
```

Sample `pimd.conf`:

```ini
# Physical interfaces to run PIM on
phyint eth0 enable
phyint eth1 enable
phyint eth2 disable

# Static Rendezvous Point
rp-address 10.0.0.1

# PIM-SSM range (no RP needed)
ssm-range 232.0.0.0/8

# IGMP querier on each subnet
altnet 10.0.0.0/8
```

Starting the daemon:

```bash
# Run in foreground for testing
pimd -d -f /etc/pimd.conf

# Run as daemon
pimd -f /etc/pimd.conf

# Check multicast routing table
pimd -s
```

### When to Use pimd

- Modern multicast networks requiring PIM-SM or PIM-SSM
- IPTV distribution across routed subnets
- Financial data distribution with source-specific groups
- Networks with multiple senders and dynamic receiver membership

## mrouted: The Original Multicast Router

[mrouted](https://github.com/troglobit/mrouted) (88 stars) is the original DVMRP implementation, dating back to 1989. While DVMRP is largely superseded by PIM-SM, mrouted remains useful for legacy multicast networks and environments where simplicity is valued over scalability.

### Key Features

- DVMRP (Distance Vector Multicast Routing Protocol)
- IGMPv1/IGMPv2 host group management
- Tunnel support for multicast over non-multicast-capable networks
- Simple configuration with minimal parameters
- Compatible with legacy multicast infrastructure
- Can act as an IGMP querier on attached subnets

### Docker Deployment

```yaml
version: "3.8"
services:
  mrouted:
    image: alpine:latest
    container_name: mrouted
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./mrouted.conf:/etc/mrouted.conf:ro
    command: sh -c "apk add mrouted && mrouted -f /etc/mrouted.conf"
    restart: unless-stopped
```

Sample `mrouted.conf`:

```ini
# Tunnel to remote multicast router
tunnel 10.1.0.2 metric 1 threshold 1

# Interface configuration
phyint eth0 enable metric 1
phyint eth1 enable metric 1
phyint lo disable

# Rate limiting
threshold 16
rate_limit 100000
```

### When to Use mrouted

- Legacy multicast networks using DVMRP
- Simple point-to-point multicast links over tunnels
- Educational environments learning multicast fundamentals
- Small networks where PIM-SM is overkill

## smcroute: Static Multicast Routing

[smcroute](https://github.com/troglobit/smcroute) (284 stars) takes a completely different approach: instead of running a routing protocol, it uses statically configured multicast forwarding entries. This eliminates protocol overhead and makes multicast behavior completely predictable.

### Key Features

- Static multicast route configuration via command-line or config file
- No routing protocol overhead (no hello messages, no state exchange)
- IGMP proxy mode for host group membership forwarding
- D-Bus and CLI interface for dynamic route management
- Supports IPv4 and IPv6 multicast
- Very lightweight: no protocol stack to maintain

### Docker Deployment

```yaml
version: "3.8"
services:
  smcroute:
    image: alpine:latest
    container_name: smcroute
    network_mode: host
    cap_add:
      - NET_ADMIN
    volumes:
      - ./smcroute.conf:/etc/smcroute.conf:ro
    command: sh -c "apk add smcroute && smcroute -d -f /etc/smcroute.conf"
    restart: unless-stopped
```

Sample `smcroute.conf`:

```ini
# Static multicast route: from eth0, group 239.1.1.1, out eth1 eth2
mroute from eth0 group 239.1.1.1 to eth1 eth2

# Source-specific static route
mroute from eth0 source 10.0.1.50 group 232.1.1.1 to eth1

# IGMP proxy: forward group membership from eth1 to eth0
mroute from eth1 igmp to eth0
```

CLI management:

```bash
# Add a static multicast route
smcroute -a eth0 239.1.1.1 eth1 eth2

# Add source-specific route
smcroute -a eth0 10.0.1.50 232.1.1.1 eth1

# Delete a route
smcroute -d eth0 239.1.1.1 eth1

# Show current routes
smcroute -s
```

### When to Use smcroute

- Small networks with known, fixed multicast sources and groups
- Environments where routing protocol traffic is undesirable
- IPTV deployments with a fixed channel lineup
- Network appliances and embedded systems

## Comparison Table

| Feature | pimd | mrouted | smcroute |
|---|---|---|---|
| **Routing Protocol** | PIM-SM / PIM-SSM | DVMRP | Static (no protocol) |
| **GitHub Stars** | 214 | 88 | 284 |
| **IGMP Version** | IGMPv2/v3 | IGMPv1/v2 | IGMP proxy |
| **Rendezvous Point** | Yes (PIM-SM) | No | N/A |
| **Source-Specific** | Yes (PIM-SSM) | No | Yes (static) |
| **Tunnel Support** | No | Yes | No |
| **IPv6 Multicast** | Partial | No | Yes |
| **Dynamic Routes** | Yes | Yes | No (manual) |
| **Protocol Overhead** | Medium (PIM hellos) | High (flood-and-prune) | None |
| **Scalability** | Large networks | Small networks | Fixed topologies |
| **Docker Deployment** | Alpine container | Alpine container | Alpine container |
| **Best For** | Modern multicast nets | Legacy / educational | Fixed IPTV channels |

## Installation Guide

### Install pimd (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install pimd -y
sudo systemctl enable pimd
sudo systemctl start pimd
```

### Install mrouted (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install mrouted -y
sudo systemctl enable mrouted
sudo systemctl start mrouted
```

### Install smcroute (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install smcroute -y
sudo systemctl enable smcroute
sudo systemctl start smcroute
```

## Why Self-Host Multicast Routing?

Managed multicast services from cloud providers are expensive, often unavailable, or limited to specific regions. Self-hosted multicast routing on commodity Linux routers gives you complete control over multicast group assignments, source filtering, and distribution tree topology — without per-group fees or vendor lock-in.

For IPTV providers, self-hosted multicast routing enables efficient channel distribution across subscriber networks using a single stream per channel. For financial services, multicast provides the lowest-latency market data distribution model. For scientific computing, multicast enables efficient checkpoint distribution across compute clusters.

For network-level traffic visibility, see our [network flow analysis guide](../2026-05-15-self-hosted-network-flow-analysis-pmacct-nfdump-fprobe-guide/). If you need SNMP-based device monitoring alongside multicast infrastructure, our [SNMP monitoring guide](../zabbix-vs-librenms-vs-netdata-network-monitoring-guide/) covers device-level management. For bandwidth management on multicast-heavy links, our [QoS and bandwidth management guide](../2026-05-03-self-hosted-network-qos-sqm-cake-tc-htb-bandwidth-management/) provides traffic shaping strategies.

## FAQ

### What is the difference between PIM-SM and PIM-SSM?

PIM-SM (Sparse Mode) uses a Rendezvous Point (RP) as a meeting point where sources register and receivers join. It is suitable for environments where receivers do not know the source address in advance. PIM-SSM (Source-Specific Multicast) eliminates the RP — receivers specify both the source IP and the multicast group. SSM is simpler, more secure (no source spoofing), and preferred for IPTV and financial data distribution.

### When should I use static multicast routing instead of a protocol?

Static multicast routing (smcroute) is best when your multicast sources and groups are known and fixed. IPTV deployments with a predefined channel lineup are the canonical use case. Static routing eliminates protocol overhead, reduces complexity, and makes troubleshooting straightforward. Use pimd or mrouted when multicast sources or receivers are dynamic.

### Does multicast work across the public internet?

Generally no. Most ISPs drop multicast traffic at their edges. Multicast is designed for controlled network environments: enterprise LANs, data center fabrics, ISP subscriber networks, and dedicated WAN links. For internet-scale content distribution, use CDN unicast or application-layer multicast (overlay networks).

### Can I run multicast routing in Docker containers?

Yes, but containers need `network_mode: host` and `CAP_NET_ADMIN` capability to access the kernel multicast routing table (MRROUTE). The examples in this guide use Alpine Linux containers with the multicast routing packages installed via `apk`. For production, consider running multicast routing daemons directly on the host or in dedicated router VMs.

### Which multicast routing protocol is the modern standard?

PIM-SM (Protocol Independent Multicast — Sparse Mode) is the current standard for enterprise multicast routing. PIM-SSM is preferred when sources are known in advance. DVMRP (implemented by mrouted) is largely deprecated but still used in legacy environments. For most new deployments, pimd with PIM-SSM is the recommended choice.

## JSON-LD Structured Data

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Multicast Routing: pimd vs mrouted vs smcroute (2026)",
  "description": "Compare three open-source multicast routing solutions: pimd for PIM-SM/SSM, mrouted for DVMRP, and smcroute for static multicast routing. Includes Docker configs and deployment guides.",
  "datePublished": "2026-05-07",
  "dateModified": "2026-05-07",
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
