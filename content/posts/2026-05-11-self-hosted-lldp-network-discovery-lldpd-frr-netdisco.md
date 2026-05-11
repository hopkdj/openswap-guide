---
title: "Self-Hosted LLDP Network Discovery: lldpd vs FRRouting vs netdisco"
date: "2026-05-11"
tags: ["networking", "lldp", "network-discovery", "self-hosted", "infrastructure"]
draft: false
---

Network discovery is a fundamental task for any infrastructure team managing more than a handful of switches, routers, and servers. Knowing what devices are connected to which ports, and how the physical topology maps to your logical network design, prevents outages and simplifies troubleshooting. This guide compares three open-source approaches to LLDP-based network discovery: lldpd, FRRouting (FRR), and netdisco.

## What Is LLDP?

The Link Layer Discovery Protocol (LLDP, IEEE 802.1AB) is a vendor-neutral protocol that allows network devices to advertise their identity, capabilities, and neighbors to directly connected devices. Unlike CDP (Cisco Discovery Protocol), which is Cisco-proprietary, LLDP works across equipment from any vendor.

LLDP advertisements (LLDPDUs) are sent as Ethernet frames every 30 seconds by default. They contain information including system name, port description, management IP addresses, VLAN configuration, and Power over Ethernet (PoE) status. Receiving devices store this information in a local LLDP neighbor table (LLDP MIB).

## Why Use Open-Source LLDP Tools?

Commercial network management platforms (SolarWinds NPM, PRTG, Cisco DNA Center) require expensive licenses and often lock you into vendor ecosystems. Open-source LLDP tools provide equivalent discovery capabilities without licensing costs, run on commodity hardware, and integrate with existing monitoring stacks.

All three tools covered here are actively maintained, support Docker deployment, and work with standard network equipment from Cisco, Juniper, Arista, MikroTik, and HP/Aruba.

## Comparison Overview

| Feature | lldpd | FRRouting (FRR) | netdisco |
|---------|-------|-----------------|----------|
| GitHub Stars | 694 | 4,127 | 862 |
| Last Updated | May 2026 | May 2026 | May 2026 |
| Type | LLDP daemon | Routing suite with LLDP | Web-based network manager |
| Primary Purpose | LLDP/CDP daemon | BGP/OSPF/IS-IS routing | Full network discovery |
| LLDP Support | Native, full spec | Via lldpd integration | Via SNMP polling |
| CDP Support | Yes (Cisco proprietary) | Limited | Yes (via SNMP)
| Web UI | No (CLI only) | No (CLI + vtysh) | Yes (full web interface) |
| Network Map | No | No | Yes (visual topology) |
| SNMP Integration | Via separate tools | Via separate tools | Built-in |
| Device Inventory | Local CLI | Local CLI | Full database |
| Docker Support | Yes | Yes | Yes |
| Multi-Vendor | Yes | Yes | Yes |
| Port-Level Discovery | Yes | Yes | Yes |
| Historical Data | No | No | Yes (tracked changes) |

## lldpd

lldpd is a dedicated LLDP and CDP daemon for Unix-like systems. It is the most widely used open-source LLDP implementation, running on Linux, BSD, and macOS. It operates as a system daemon that sends and receives LLDP frames, maintaining a local neighbor table queryable via CLI.

**Key features:**
- Full IEEE 802.1AB LLDP implementation
- Cisco CDP protocol support (read-only)
- SONMP (Nortel) and EDP (Extreme) protocol support
- Configurable TLV (Type-Length-Value) advertisements
- SNMP sub-agent for LLDP MIB (AgentX)
- Low resource usage (<10MB RAM)
- JSON output for integration with monitoring systems

**Strengths:** lldpd is purpose-built for LLDP — it does one thing and does it well. The `lldpcli` command provides human-readable neighbor information, and JSON output enables integration with scripts and monitoring systems. It is extremely lightweight and stable, making it suitable for production servers and network devices.

**Weaknesses:** lldpd provides no web interface, network mapping, or historical tracking. It is a CLI-only tool. For visual topology maps, you need to combine it with additional tools like netdisco or a custom script that parses `lldpcli show neighbors -j` output.

### Installation and Configuration

```bash
# Install on Debian/Ubuntu
sudo apt-get install lldpd

# Install on RHEL/CentOS
sudo yum install lldpd

# Enable and start
sudo systemctl enable lldpd
sudo systemctl start lldpd
```

Configure LLDP advertisements (`/etc/lldpd.conf`):
```
# System description
configure system description "Production Web Server 01"

# System name
configure system name web-prod-01

# Chassis ID (use MAC address)
configure chassisid macaddress

# Enable CDP reception (for Cisco neighbors)
configure lldp receive-cdp on

# Disable LLDP transmission on specific interface
configure med policy voice disable interface eth1
```

View discovered neighbors:
```bash
# Human-readable output
sudo lldpcli show neighbors

# JSON output for scripts
sudo lldpcli show neighbors -j

# Watch mode (real-time updates)
watch -n 5 'sudo lldpcli show neighbors summary'
```

### Docker Deployment

```yaml
version: "3.8"
services:
  lldpd:
    image: networkstatic/lldpd:latest
    container_name: lldpd
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    restart: unless-stopped
```

## FRRouting (FRR)

FRRouting is a comprehensive routing protocol suite supporting BGP, OSPF, IS-IS, RIP, EIGRP, and more. While primarily a routing daemon, FRR can integrate with lldpd for network discovery, combining routing intelligence with link-layer topology information.

**Key features:**
- BGP, OSPF, OSPFv3, IS-IS, RIP, RIPng, EIGRP, PIM, NHRP, BFD, VRRP
- LLDP integration via lldpd
- Zebra daemon for kernel routing table management
- VTYSH unified CLI (Cisco-like syntax)
- Route maps, prefix lists, and policy routing
- Multi-instance support (multiple FRR daemons on one host)
- NETCONF/YANG configuration support

**Strengths:** FRR is the most feature-rich open-source routing suite available. When combined with lldpd, it provides both link-layer discovery and network-layer routing intelligence. The VTYSH CLI offers familiar Cisco-like commands. FRR is used in production by major cloud providers and telecommunications companies.

**Weaknesses:** FRR has a steep learning curve — it is designed for network engineers, not general system administrators. There is no web interface (third-party tools like FRR WebUI exist but are not official). LLDP support requires installing lldpd separately and configuring the integration.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  frr:
    image: frrouting/frr:v10.2
    container_name: frr
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
      - SYS_ADMIN
    volumes:
      - ./frr.conf:/etc/frr/frr.conf:ro
      - frr_data:/etc/frr
    restart: unless-stopped

volumes:
  frr_data:
```

FRR configuration (`/etc/frr/frr.conf`):
```
frr version 10.2
frr defaults datacenter
hostname router-01

! Enable OSPF
router ospf
 router-id 10.0.0.1
 network 10.0.0.0/24 area 0
 network 10.0.1.0/24 area 0

! Enable BGP
router bgp 65001
 neighbor 10.0.0.2 remote-as 65002
 neighbor 10.0.0.2 description "Peer router"
 network 10.0.0.0/24

! LLDP integration
! (requires lldpd running alongside)
```

## netdisco

netdisco is a web-based network discovery and management platform. It combines SNMP polling, LLDP/CDP parsing, and a PostgreSQL database to provide a comprehensive view of your network topology. Unlike lldpd and FRR, netdisco is a full-featured network management application.

**Key features:**
- Automated device discovery via SNMP
- LLDP and CDP neighbor tracking
- Visual network topology maps
- Device inventory with port-level detail
- VLAN and ARP table tracking
- Historical change tracking (port movements, device additions)
- Web-based interface with search and filtering
- REST API for automation
- Plugin system for extensibility

**Strengths:** netdisco provides the most complete network discovery experience of the three tools. Its web interface shows device inventory, port status, neighbor relationships, and historical changes. The SNMP integration works with virtually any network device. The PostgreSQL backend supports large-scale deployments with thousands of devices.

**Weaknesses:** netdisco has a more complex deployment (PostgreSQL, SNMP, Perl dependencies). Initial configuration requires defining SNMP community strings and seed routers. It is resource-intensive compared to lldpd (requires PostgreSQL and a web server).

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  netdisco:
    image: netdisco/netdisco:latest
    container_name: netdisco
    ports:
      - "5000:5000"
    environment:
      - NETDISCO_DB_USER=netdisco
      - NETDISCO_DB_PASS=${NETDISCO_PASSWORD}
      - NETDISCO_SNMP_COMMUNITIES=public
    volumes:
      - netdisco_config:/home/netdisco/environments/production
      - netdisco_data:/home/netdisco/data
    restart: unless-stopped

volumes:
  netdisco_config:
  netdisco_data:
```

## Choosing the Right Network Discovery Tool

**Use lldpd when:** You need lightweight, reliable LLDP/CDP discovery on individual servers or network devices. It is ideal for system administrators who want to know what switch port each server connects to.

**Use FRRouting when:** You are building a routing infrastructure that also needs link-layer discovery. It is the right choice for network engineers deploying BGP/OSPF who want LLDP neighbor data alongside routing tables.

**Use netdisco when:** You need a complete network management platform with visual topology maps, device inventory, and historical tracking. It is ideal for network operations teams managing dozens to hundreds of network devices.

For comprehensive network visibility, many organizations run lldpd on every server (for local neighbor discovery) alongside netdisco as the centralized management platform.

## Why Self-Host Your Network Discovery Tools?

Self-hosted network discovery tools keep your infrastructure topology data within your own network. Commercial alternatives like Cisco DNA Center, SolarWinds Network Topology Mapper, and PRTG send device inventory and topology data to vendor cloud services — a security concern for organizations in regulated industries.

Running lldpd or FRR on your own infrastructure adds negligible overhead — lldpd uses under 10MB of RAM and FRR's LLDP integration is similarly lightweight. netdisco requires a PostgreSQL database and web server, but can run on a small VM (2 CPU, 4GB RAM) for networks up to 500 devices.

Self-hosted discovery also integrates with your existing monitoring stack. lldpd's JSON output feeds into Prometheus, Grafana, or custom alerting systems. netdisco's REST API connects to IT service management platforms and automated documentation workflows.

For related reading, see our [SNMP collectors comparison](../2026-04-26-snmp-collectors-snmp-exporter-snmpcollector-telegraf-self-hosted-guide-2026/) and [network discovery guide](../2026-04-25-netdisco-vs-librenms-vs-opennetadmin-network-discovery-guide-2026/). For IP address management, our [IPAM tool comparison](../2026-04-20-phpipam-vs-nipap-vs-netbox-self-hosted-ipam-guide-2026/) covers address tracking options.

## FAQ

### What is the difference between LLDP and CDP?

LLDP (Link Layer Discovery Protocol) is an IEEE standard (802.1AB) supported by virtually all network vendors. CDP (Cisco Discovery Protocol) is Cisco-proprietary and works only between Cisco devices. lldpd supports both protocols, receiving CDP advertisements from Cisco neighbors while sending standard LLDP frames.

### Can lldpd work without root privileges?

No, lldpd requires root (or CAP_NET_ADMIN/CAP_NET_RAW capabilities) because it needs to send and receive raw Ethernet frames. In Docker, you must use `network_mode: host` or add the `NET_ADMIN` and `NET_RAW` capabilities.

### Does FRR replace lldpd?

No, FRR does not implement LLDP natively. It integrates with lldpd by reading lldpd's neighbor data through a shared interface. You need to run lldpd alongside FRR for LLDP discovery to work.

### How does netdisco discover devices?

netdisco uses SNMP polling to discover devices. You configure seed routers (known devices), and netdisco uses LLDP/CDP data from SNMP queries to automatically discover neighboring devices. It recursively discovers the entire network topology from the seed devices.

### Can I use lldpd with containerized applications?

Yes, lldpd runs in a Docker container with `network_mode: host` and `cap_add: [NET_ADMIN, NET_RAW]`. The container shares the host's network namespace, allowing it to see and send LLDP frames on all host interfaces.

### What database does netdisco use?

netdisco uses PostgreSQL as its backend database. All device inventory, neighbor relationships, VLAN data, and historical changes are stored in PostgreSQL. The database schema supports networks with thousands of devices.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted LLDP Network Discovery: lldpd vs FRRouting vs netdisco",
  "description": "Compare lldpd, FRRouting, and netdisco for LLDP-based network discovery. Self-hosted network topology mapping, neighbor discovery, and device inventory management.",
  "datePublished": "2026-05-11",
  "dateModified": "2026-05-11",
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

