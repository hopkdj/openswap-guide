---
title: "VyOS vs OPNsense vs OpenWrt: Self-Hosted SD-WAN and Edge Routing Guide 2026"
date: 2026-05-03
tags: ["sd-wan", "networking", "routing", "vyos", "opnsense", "openwrt", "self-hosted", "docker"]
draft: false
---

Software-Defined Wide Area Networking (SD-WAN) decouples network control from the underlying transport, enabling intelligent path selection, centralized policy management, and cost-efficient connectivity across branch offices, cloud regions, and remote sites. While commercial SD-WAN solutions from VMware, Cisco, and Fortinet dominate the enterprise market, open-source networking platforms provide capable self-hosted alternatives for organizations that want full control.

This guide compares three leading open-source routing platforms that support SD-WAN capabilities: **VyOS**, **OPNsense**, and **OpenWrt**. Each can serve as an edge router with policy-based routing, multiple WAN uplinks, and centralized management.

## What Is SD-WAN and Why Self-Host?

SD-WAN abstracts the underlying network transport (MPLS, broadband, LTE/5G, satellite) and applies intelligent routing policies based on application requirements, link quality, and cost. Key capabilities include:

- **Policy-based routing** — direct traffic based on application type, destination, or SLA requirements
- **Link aggregation and failover** — combine multiple WAN links for bandwidth and redundancy
- **Path quality monitoring** — continuous measurement of latency, jitter, and packet loss
- **Centralized management** — single pane of glass for configuration across all edge sites
- **Cost optimization** — replace expensive MPLS circuits with commodity broadband

Self-hosting SD-WAN infrastructure eliminates per-site licensing fees, avoids vendor lock-in, and keeps all network telemetry within your infrastructure.

## VyOS: CLI-Driven Network Operating System

**VyOS** is an open-source network operating system based on Debian Linux, derived from the former Vyatta project. It provides a Juniper-inspired CLI for configuring routing protocols, firewall rules, VPNs, and SD-WAN features.

### Key Features

- **Multi-WAN support** — load balancing and failover across multiple uplinks
- **Policy-based routing (PBR)** — route traffic based on source, destination, protocol, or DSCP markings
- **BGP, OSPF, RIP** — full routing protocol suite for dynamic path selection
- **IPsec and WireGuard VPNs** — site-to-site encrypted tunnels over any transport
- **VRF (Virtual Routing and Forwarding)** — isolated routing tables for multi-tenant deployments
- **SLA monitoring** — track link health with ping, HTTP, or custom probes
- **High availability** — VRRP for router failover

### Docker Compose Setup

```yaml
version: "3.8"
services:
  vyos:
    image: vyos/vyos:1.5-rolling
    container_name: vyos
    privileged: true
    cap_add:
      - NET_ADMIN
      - SYS_ADMIN
    volumes:
      - ./config:/config
    network_mode: "host"
    restart: unless-stopped
    command: >
      /sbin/init
```

### SD-WAN Configuration Example

```bash
# Configure two WAN interfaces with SLA monitoring
set interfaces ethernet eth0 address dhcp
set interfaces ethernet eth1 address dhcp

# SLA tracking for link health
set service sla 10 interval 5
set service sla 10 test 10 type icmp
set service sla 10 test 10 target address 8.8.8.8

# Policy-based routing: VoIP traffic over primary link
set policy route VOIP rule 10 destination port 5060
set policy route VOIP rule 10 set interface eth0
set policy route VOIP rule 20 destination port 10000-20000
set policy route VOIP rule 20 set interface eth0

# Load balancing with failover
set load-balance wan interface-health eth0 test 10
set load-balance wan interface-health eth1 test 10
set load-balance wan rule 10 interface eth0
set load-balance wan rule 10 use-percent 70
set load-balance wan rule 20 interface eth1
set load-balance wan rule 20 use-percent 30
```

### Strengths and Limitations

| Aspect | Assessment |
|--------|-----------|
| Routing protocols | Full BGP, OSPF, IS-IS, RIP support |
| SD-WAN features | PBR, SLA tracking, multi-WAN, VRF |
| Management model | CLI-only (Juniper-style) |
| Automation | Ansible module available; REST API via vyos-http |
| Hardware support | x86 and ARM; runs on commodity hardware |
| Learning curve | Steep for users unfamiliar with network CLI |

## OPNsense: FreeBSD-Based Firewall and Router

**OPNsense** is a FreeBSD-based firewall and routing platform with a comprehensive web interface. It provides robust multi-WAN, policy routing, and plugin extensibility that can be configured into an SD-WAN solution.

### Key Features

- **Multi-WAN gateway groups** — tiered failover and load balancing with health monitoring
- **Policy-based routing** — traffic routing based on source/destination, ports, or tags
- **BGP and OSPF** — via FRRouting (FRR) plugin
- **IPsec and OpenVPN** — site-to-site and remote access VPNs
- **Plugins and extensions** — HAProxy, WireGuard, Suricata, Zenarmor, and more
- **High availability** — CARP (Common Address Redundancy Protocol) for stateful failover
- **Reporting and monitoring** — built-in graphs for traffic, interfaces, and services

### Docker Compose Setup

OPNsense is typically deployed as a virtual machine or on bare metal. For containerized testing:

```yaml
version: "3.8"
services:
  opnsense:
    image: svennielsen/opnsense:latest
    container_name: opnsense
    privileged: true
    cap_add:
      - NET_ADMIN
    volumes:
      - ./conf:/conf
    ports:
      - "443:443"
      - "80:80"
    network_mode: "host"
    restart: unless-stopped
```

### Multi-WAN Configuration via Web UI

OPNsense's SD-WAN capabilities are configured through its web interface:

1. **System → Gateways**: Define each WAN gateway with monitor IP and latency thresholds
2. **System → Gateway Groups**: Create groups with tier priorities (e.g., Tier 1: Fiber, Tier 2: LTE)
3. **Firewall → Rules → WAN**: Set policy-based routing rules matching specific traffic patterns
4. **Services → FRR BGP**: Configure dynamic routing if needed for BGP peering with upstream providers

```bash
# FRR BGP plugin configuration (via CLI)
router bgp 65001
  neighbor 192.168.1.1 remote-as 65002
  network 10.0.0.0/24
  network 10.0.1.0/24
```

### Strengths and Limitations

| Aspect | Assessment |
|--------|-----------|
| Routing protocols | BGP/OSPF via FRR plugin |
| SD-WAN features | Multi-WAN gateway groups, policy routing, health monitoring |
| Management model | Web UI (primary), CLI (secondary) |
| Automation | REST API available; config backup/restore |
| Hardware support | x86 and ARM; official images for pfSense-compatible hardware |
| Learning curve | Moderate; web UI makes most tasks accessible |

## OpenWrt: Embedded Linux Router Platform

**OpenWrt** is a highly extensible Linux distribution for embedded devices, primarily used as router firmware. While traditionally deployed on consumer routers, it can serve as an SD-WAN edge node when running on x86 hardware with multiple network interfaces.

### Key Features

- **Multi-WAN with MWAN3** — policy-based load balancing and failover across multiple links
- **Policy routing** — IP rules and routes based on source, destination, or marks
- **BGP via Babel or BIRD** — dynamic routing support via packages
- **WireGuard and OpenVPN** — site-to-site tunneling
- **LuCI web interface** — browser-based configuration and monitoring
- **Package ecosystem** — 4,000+ packages for extending functionality
- **SQM QoS** — smart queue management for traffic shaping and bandwidth optimization

### Docker Compose Setup

```yaml
version: "3.8"
services:
  openwrt:
    image: openwrtorg/rootfs:x86-64-23.05.3
    container_name: openwrt
    privileged: true
    cap_add:
      - NET_ADMIN
    volumes:
      - ./overlay:/overlay
      - ./etc:/etc/config
    network_mode: "host"
    restart: unless-stopped
```

### MWAN3 Multi-WAN Configuration

```bash
# /etc/config/mwan3

# Define WAN interfaces
config interface 'wan1'
    option interface 'eth0'
    option track_ip '8.8.8.8'
    option weight '3'
    option count '3'

config interface 'wan2'
    option interface 'eth1'
    option track_ip '1.1.1.1'
    option weight '1'
    option count '3'

# Load balancing policy
config policy 'balanced'
    option use_policy 'balanced'
    list members 'wan1'
    list members 'wan2'

# Policy routing for VoIP
config rule 'voip'
    option src_ip '192.168.1.0/24'
    option dest_port '5060-5061|10000-20000'
    option use_policy 'wan1_only'
    option family 'ipv4'
```

### Strengths and Limitations

| Aspect | Assessment |
|--------|-----------|
| Routing protocols | BGP via BIRD package; OSPF limited |
| SD-WAN features | MWAN3 for multi-WAN, policy routing, health tracking |
| Management model | LuCI web UI + CLI |
| Automation | RPCD API; Ansible modules available |
| Hardware support | x86 and extensive embedded (ARM, MIPS) |
| Learning curve | Low to moderate; LuCI simplifies most tasks |

## Comparison: VyOS vs OPNsense vs OpenWrt for SD-WAN

| Feature | VyOS | OPNsense | OpenWrt |
|---------|------|----------|---------|
| **Multi-WAN** | Load balance + failover | Gateway groups | MWAN3 |
| **Policy-based routing** | Yes (native) | Yes (firewall rules) | Yes (MWAN3 rules) |
| **BGP support** | Yes (native) | Yes (FRR plugin) | Yes (BIRD package) |
| **OSPF support** | Yes (native) | Yes (FRR plugin) | Limited |
| **Health monitoring** | SLA tracking | Gateway monitoring | MWAN3 track_ip |
| **VRF** | Yes | No | No |
| **High availability** | VRRP | CARP | No native |
| **Management** | CLI only | Web UI (primary) | LuCI web UI |
| **Automation API** | Ansible + vyos-http | REST API | RPCD |
| **VPN** | IPsec, WireGuard, OpenVPN | IPsec, OpenVPN, WireGuard | WireGuard, OpenVPN |
| **Traffic shaping** | QoS, HTB | Limiters, DUMMYNET | SQM, HTB |
| **License** | MIT | BSD | GPL |
| **Best for** | Network engineers | SMBs, general use | Embedded, edge devices |

## Why Self-Host Your SD-WAN Edge?

**Cost savings**: Commercial SD-WAN appliances cost $1,000–$5,000 per site plus annual licensing. Self-hosted solutions on commodity hardware reduce per-site costs to under $200.

**No vendor dependency**: Open-source platforms do not require cloud connectivity for management or licensing validation. Your network remains operational even if the vendor discontinues support.

**Customization**: Each platform supports extensive customization through plugins, scripts, and configuration files. You can implement routing policies, traffic shaping, and monitoring that match your exact requirements.

**Transparency**: Full visibility into how routing decisions are made, with no black-box algorithms. All configuration is stored as plain text files that can be version-controlled with Git.

For network security deployment guidance, see our [firewall and router comparison](../pfsense-vs-opnsense-vs-ipfire-self-hosted-firewall-router-guide/) and [intrusion prevention guide](../2026-04-24-fail2ban-vs-sshguard-vs-crowdsec-self-hosted-intrusion-prevention-2026/). If you need DNS-level protection alongside your SD-WAN, our [DNS firewall guide](../2026-04-21-self-hosted-dns-firewall-rpz-unbound-powerdns-bind9-knot-guide/) covers response policy zones.

## FAQ

### What is the difference between SD-WAN and traditional WAN routing?

Traditional WAN routing uses static routes or basic dynamic protocols without application awareness. SD-WAN adds intelligent path selection based on application type, link quality metrics, and business policies — automatically steering traffic over the best available link.

### Can VyOS replace a commercial SD-WAN appliance?

For many use cases, yes. VyOS supports policy-based routing, SLA monitoring, multi-WAN load balancing, and IPsec/WireGuard site-to-site tunnels. It lacks the centralized cloud management dashboard of commercial solutions, but its Ansible integration provides automation capabilities.

### Does OPNsense support BGP for SD-WAN?

Yes, through the FRRouting (FRR) plugin. You can install the `os-frr` package from the OPNsense plugin repository to enable BGP, OSPF, and other routing protocols.

### Is OpenWrt suitable for enterprise SD-WAN deployments?

OpenWrt works well for branch offices and small sites. For larger deployments, VyOS or OPNsense offer more advanced routing features and scalability. OpenWrt excels on resource-constrained edge hardware where x86 routers are not practical.

### How does MWAN3 handle link failover?

MWAN3 continuously pings a configurable track IP on each interface. When an interface fails a configurable number of consecutive checks, MWAN3 removes it from the policy and routes traffic through remaining active members. When the link recovers, it is automatically re-added.

### Can these platforms monitor link quality metrics?

VyOS has built-in SLA monitoring with ICMP and HTTP probes. OPNsense monitors gateway latency and packet loss through its gateway monitoring system. OpenWrt's MWAN3 tracks link availability via ping but does not measure jitter or detailed latency statistics natively.

### Do these solutions support zero-touch provisioning?

VyOS and OPNsense support configuration import from USB or network sources. OpenWrt supports pre-configured firmware images. None provide the automated zero-touch provisioning (ZTP) of commercial SD-WAN solutions out of the box, but Ansible and configuration management tools can automate initial deployment.

### What hardware is recommended for self-hosted SD-WAN?

For VyOS and OPNsense: an x86 mini-PC with at least 4 GB RAM, dual NICs (or a managed switch for VLAN-based WAN separation), and an SSD. For OpenWrt: any supported embedded device with sufficient flash storage and RAM for the packages you need.

### Can I combine these platforms in a single deployment?

Yes. A common pattern is OPNsense at headquarters (for the web UI and plugin ecosystem), VyOS at data center edge sites (for advanced routing), and OpenWrt at branch offices (for cost efficiency on embedded hardware).

### How do these compare to Tailscale/Headscale for site connectivity?

Tailscale/Headscale provides encrypted overlay networking between sites but does not replace SD-WAN. SD-WAN platforms manage physical WAN links, perform traffic engineering, and optimize path selection based on link quality. Use both together: SD-WAN for physical link management and Tailscale for encrypted overlay between internal services.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "VyOS vs OPNsense vs OpenWrt: Self-Hosted SD-WAN and Edge Routing Guide 2026",
  "description": "Compare three open-source routing platforms for self-hosted SD-WAN deployments. Covers VyOS, OPNsense, and OpenWrt with multi-WAN configuration, policy routing, and Docker Compose setups.",
  "datePublished": "2026-05-03",
  "dateModified": "2026-05-03",
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
