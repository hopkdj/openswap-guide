---
title: "Self-Hosted DHCP Relay Solutions: ISC Kea, FRRouting, and ISC DHCP Relay"
date: "2026-05-14"
tags: ["dhcp", "networking", "relay", "infrastructure", "self-hosted"]
draft: false
---

DHCP relay (also known as DHCP helper) is a critical network infrastructure component that forwards DHCP requests from clients on one subnet to DHCP servers on another subnet. Without a relay agent, DHCP broadcast traffic cannot cross router boundaries, meaning every subnet would need its own DHCP server — an impractical requirement for multi-subnet networks.

This guide compares three approaches to DHCP relay: **ISC Kea DHCP Relay**, **FRRouting's DHCP relay integration**, and the classic **ISC DHCP Relay (dhcrelay)**. Each serves different use cases, from modern centralized DHCP management to lightweight relay forwarding.

## Why DHCP Relay Matters

In enterprise and campus networks, clients on different VLANs and subnets need IP addresses from a central DHCP server. DHCP relay agents solve this by:

- **Converting broadcasts to unicast**: DHCP requests are broadcast on the local subnet; the relay converts them to unicast packets sent to the DHCP server
- **Inserting relay agent information (Option 82)**: Adds circuit ID and remote ID information so the DHCP server can identify the client's origin subnet
- **Supporting multiple server addresses**: Can forward to primary and backup DHCP servers for redundancy
- **Handling DHCPv6 relay**: Supports DHCPv6 relay-encapsulated messages across multiple relay hops

## ISC Kea DHCP Relay: Modern DHCP Infrastructure

[ISC Kea](https://github.com/isc-projects/kea) (700+ stars) is ISC's next-generation DHCP platform. Kea includes a dedicated DHCP relay component (`kea-relay`) that is part of a comprehensive DHCP ecosystem with a centralized control channel and database-backed lease management.

### Key Features
- Part of the unified Kea DHCP ecosystem (server, relay, control agent)
- DHCPv4 and DHCPv6 relay support
- Option 82 (relay agent information) insertion
- JSON-based configuration with hot-reload via control channel
- Integration with Kea's lease database for comprehensive tracking

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  kea-relay:
    image: isc-projects/kea:latest
    container_name: kea-relay
    network_mode: "host"
    volumes:
      - ./kea-relay.conf:/etc/kea/kea-relay.conf:ro
    command: kea-relay -c /etc/kea/kea-relay.conf
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
```

Kea relay configuration (`kea-relay.conf`):

```json
{
    "DhcpRelay": {
        "interfaces": [
            {
                "name": "eth1",
                "relay-info": [
                    {
                        "ip-address": "10.0.1.1"
                    }
                ]
            }
        ],
        "relay-agent-address": "10.0.1.1",
        "destination-address": "192.168.1.10",
        "hop-count-limit": 16
    }
}
```

### Managing Kea Relay

```bash
# Hot-reload configuration
curl -X POST -d '{ "command": "config-reload" }' http://localhost:8080/

# Check relay statistics
curl -X POST -d '{ "command": "statistic-get-all" }' http://localhost:8080/

# Monitor relay activity
kea-relay -c /etc/kea/kea-relay.conf -d
```

## FRRouting: DHCP Relay via Network Integration

[FRRouting](https://github.com/FRRouting/frr) (4,100+ stars) is primarily a routing protocol suite, but it integrates with Linux's native DHCP relay capabilities and provides the networking foundation for DHCP relay in routed network topologies.

### Key Features
- Works alongside Linux `dhcprelay` for integrated relay + routing
- Full routing protocol suite (BGP, OSPF, IS-IS, RIP, EIGRP)
- Supports complex topologies where relay must traverse multiple routing domains
- VRF-aware relay support for multi-tenant networks
- Active development with strong community

### Using FRR with Linux DHCP Relay

FRR handles the routing; Linux provides the relay:

```yaml
version: "3.8"
services:
  frr:
    image: frrouting/frr:v9.1.0
    container_name: frr-router
    network_mode: "host"
    volumes:
      - ./frr.conf:/etc/frr/frr.conf:ro
      - ./daemons:/etc/frr/daemons:ro
    cap_add:
      - NET_ADMIN
      - SYS_ADMIN
    restart: unless-stopped
```

FRR configuration (`frr.conf`) with OSPF to ensure relay can reach DHCP servers:

```
frr version 9.1.0
frr defaults traditional
hostname frr-relay
service integrated-vtysh-config

! OSPF for routing to DHCP server subnet
router ospf
 router-id 10.0.0.1
 network 10.0.0.0/16 area 0.0.0.0
 network 192.168.0.0/16 area 0.0.0.0
!
ip forwarding
!
```

Linux DHCP relay command:

```bash
# Install and run dhcprelay (part of isc-dhcp-relay package)
apt-get install -y isc-dhcp-relay

# Relay from eth1 (client subnet) to DHCP server
dhcprelay -i eth1 192.168.1.10
```

## ISC DHCP Relay (dhcrelay): The Classic Solution

The ISC DHCP Relay (`dhcrelay`) is the traditional, battle-tested DHCP relay agent that has been part of the ISC DHCP distribution for decades. While ISC DHCP server has reached end-of-life, `dhcrelay` remains widely deployed.

### Key Features
- Simple, single-purpose daemon — does one thing well
- Supports both DHCPv4 and DHCPv6 relay
- Option 82 relay agent information insertion
- Multiple interface support for multi-homed relays
- Minimal resource footprint (single binary, no dependencies)

### Docker Deployment

```yaml
version: "3.8"
services:
  dhcprelay:
    image: networkboot/dhcprelay:latest
    container_name: isc-dhcprelay
    network_mode: "host"
    environment:
      - SERVERS=192.168.1.10,192.168.1.11
      - INTERFACES=eth1,eth2
    command: dhcprelay -d 192.168.1.10 192.168.1.11
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
```

Command-line usage:

```bash
# Basic relay: forward from eth1 to DHCP server
dhcprelay 192.168.1.10

# Multiple interfaces and servers
dhcprelay -i eth1 -i eth2 -i eth3 192.168.1.10 192.168.1.11

# DHCPv6 relay
dhcrelay6 -i eth1 ff02::1:2
```

## Comparison Table

| Feature | ISC Kea Relay | FRR + dhcrelay | ISC dhcrelay |
|---|---|---|---|
| DHCPv4 Relay | Yes | Yes (via Linux) | Yes |
| DHCPv6 Relay | Yes | Yes (via Linux) | Yes |
| Option 82 | Yes | Yes | Yes |
| Configuration | JSON (hot-reload) | CLI / systemd | CLI flags |
| Integrated DHCP Server | Yes (Kea) | No | No (ISC DHCP EOL) |
| Control Channel API | Yes (JSON-RPC) | No | No |
| VRF Support | Limited | Yes (FRR VRF) | No |
| Resource Usage | Medium | Low | Very Low |
| GitHub Stars | 700+ | 4,100+ | N/A (part of ISC DHCP) |
| Best For | Modern Kea deployments | Routed networks | Simple relay needs |

## Why Self-Host DHCP Relay Infrastructure?

DHCP relay is foundational network infrastructure that must be under your direct control. Using cloud-managed DHCP services introduces latency, creates single points of failure, and limits your ability to customize Option 82 information for policy-based address assignment.

Self-hosted DHCP relay agents give you granular control over relay agent information, enabling subnet-aware DHCP policies, dynamic VLAN assignment, and integration with RADIUS for 802.1X authentication. Combined with centralized DHCP servers like Kea, you can build a scalable, multi-subnet DHCP infrastructure that serves thousands of clients across dozens of VLANs.

For comprehensive DHCP server management, see our [Kea vs dnsmasq vs ISC DHCP guide](../2026-05-04-self-hosted-dhcp-server-management-kea-dnsmasq-isc-dhcp-guide/). For DHCP high availability configurations, check our [DHCP HA guide](../2026-05-09-self-hosted-dhcp-high-availability-kea-ha-vs-isc-dhcp-vs-keepalived-guide/).


## Multi-Site DHCP Relay Architecture

In distributed organizations with multiple branch offices, DHCP relay agents form a critical part of the network infrastructure. Each branch office typically deploys a local relay agent that forwards requests to a central DHCP server at headquarters or in a data center.

The design must account for WAN link reliability — if the relay-to-server path fails, clients cannot obtain IP addresses. Implementing local DHCP server fallback at each branch (with Kea's high availability features) ensures continuity during WAN outages. The relay agent configuration should prioritize the local server and fall back to the central server.

VLAN design directly impacts DHCP relay configuration. Each VLAN that requires DHCP service needs either a dedicated relay interface or a relay agent configured with multiple interface bindings. The relay agent information (Option 82) inserted by the relay enables the DHCP server to distinguish between clients from different VLANs and assign addresses from the correct pools.

For related network infrastructure topics, see our [network diagnostics tools comparison](../2026-05-15-self-hosted-network-diagnostics-fping-vs-mtr-vs-nping-guide/) for troubleshooting DHCP and relay connectivity issues.

## FAQ

### What is DHCP relay and why is it needed?
DHCP relay (also called DHCP helper) forwards DHCP broadcast requests from clients on one subnet to DHCP servers on a different subnet. Since DHCP uses broadcast traffic that routers do not forward, a relay agent is required for clients to obtain IP addresses from a centralized DHCP server across subnets.

### What is Option 82 (relay agent information)?
Option 82 is a DHCP option that relay agents insert into DHCP requests to identify the client's origin. It contains the circuit ID (which switch port the client is on) and remote ID (which relay agent forwarded the request). DHCP servers use this information to assign IP addresses from the correct subnet pool.

### Can FRRouting act as a DHCP relay?
FRRouting does not include a native DHCP relay agent. It handles routing protocols (BGP, OSPF, etc.) that ensure DHCP relay traffic can reach the DHCP server. The actual relay is provided by Linux's `dhcprelay` (from isc-dhcp-relay) or Kea's relay component.

### Is ISC DHCP relay still maintained?
The ISC DHCP relay daemon (`dhcrelay`) is part of the ISC DHCP distribution, which has reached end-of-life. For new deployments, ISC recommends migrating to Kea. However, `dhcrelay` continues to work reliably and is still packaged in major Linux distributions.

### How do I test DHCP relay is working?
Use `tcpdump` on both the client-facing and server-facing interfaces: `tcpdump -i eth1 port 67 or port 68` to see DHCP Discover/Offer traffic, and `tcpdump -i eth0 port 67 or port 68` on the server side to confirm relay forwarding. You should see the relay agent IP in the forwarded packets.

### Does DHCP relay work across VPNs or tunnels?
Yes, DHCP relay works across any IP transport, including VPNs, GRE tunnels, and VXLAN overlays. The key requirement is that the relay agent can reach the DHCP server's IP address via unicast routing. For VXLAN overlays, the relay operates at the VTEP level.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DHCP Relay Solutions: ISC Kea, FRRouting, and ISC DHCP Relay",
  "description": "Compare ISC Kea Relay, FRRouting, and ISC dhcrelay for self-hosted DHCP relay across subnets. Includes Docker configs and Option 82 configuration.",
  "datePublished": "2026-05-14",
  "dateModified": "2026-05-14",
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

