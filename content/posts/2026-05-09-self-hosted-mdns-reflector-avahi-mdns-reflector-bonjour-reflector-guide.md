---
title: "Self-Hosted mDNS Reflector: Avahi vs mdns-reflector vs bonjour-reflector (2026)"
date: "2026-05-09"
tags: ["networking", "docker", "homelab", "multicast", "service-discovery"]
draft: false
---

In modern networked environments, service discovery protocols like mDNS (Multicast DNS) and DNS-SD (DNS Service Discovery) allow devices to find each other without a central directory server. Apple calls this Bonjour; the open-source implementation is Avahi. The problem? mDNS is a link-local protocol — it does not cross VLAN or subnet boundaries by design.

When you segment your network into multiple VLANs (servers, IoT, workstations, guests), devices on one VLAN cannot discover mDNS services on another. This breaks AirPrint printing, Chromecast streaming, HomeKit accessories, and any application relying on zero-configuration networking across subnets.

Three open-source tools solve this problem by reflecting mDNS traffic between VLANs: **Avahi** with reflector mode enabled, **mdns-reflector** (a dedicated Go-based reflector), and **bonjour-reflector** (a Rust-based alternative with fine-grained control). This guide compares their capabilities, provides Docker Compose configurations, and helps you choose the right solution for your network.

## What Is mDNS Reflection?

mDNS operates on multicast address 224.0.0.251 (IPv4) or ff02::fb (IPv6) and responds to queries for `.local` domain names. Because multicast traffic is confined to a single broadcast domain (VLAN), devices on different subnets cannot discover each other.

An mDNS reflector solves this by:
1. **Listening** for mDNS queries on multiple network interfaces (one per VLAN)
2. **Forwarding** queries from one VLAN to all others
3. **Relaying** responses back to the querying VLAN
4. **Filtering** duplicate or stale announcements to prevent broadcast storms

This creates a seamless service discovery experience across your entire network while maintaining VLAN segmentation for unicast traffic.

## Why Self-Host mDNS Reflection?

Commercial networking equipment often includes built-in mDNS/Bonjour gateway features (UniFi, Cisco, Aruba), but these are tied to specific vendor ecosystems. Self-hosted reflectors work with any managed switch or router, run on commodity hardware, and give you full control over which service types are reflected.

Running your own reflector is especially important for homelabs and small businesses where:
- **IoT devices** on a dedicated VLAN need to discover media servers on the main network
- **AirPrint printers** on the server VLAN must be reachable from workstation and guest VLANs
- **HomeKit accessories** need to be discoverable across smart home and primary LAN segments
- **Development environments** use multiple VLANs for service isolation but need cross-VLAN discovery

For environments using centralized DNS infrastructure, pairing mDNS reflection with a self-hosted [PowerDNS or BIND DNS server](../2026-04-18-powerdns-vs-bind9-vs-nsd-vs-knot-self-hosted-authoritative-dns-2026/) provides both link-local and domain-wide service discovery. And for organizations managing network configurations across devices, our [Oxidized network config backup guide](../oxidized-vs-netmiko-vs-napalm-network-config-backup-automation-2026/) covers automating the switch configurations needed to support mDNS reflection.

## Comparison Overview

| Feature | Avahi | mdns-reflector | bonjour-reflector |
|---------|-------|---------------|-------------------|
| **GitHub Stars** | ~1,493 | ~240 | ~187 |
| **Language** | C | Go | Rust |
| **License** | LGPL 2.1 | MIT | MIT |
| **Reflector Mode** | Built-in (`enable-reflector=yes`) | Primary purpose | Primary purpose |
| **IPv6 Support** | Full | Full | Full |
| **mDNS over Unicast** | No | No | No |
| **Service Filtering** | Basic (allow/deny lists) | Per-interface, per-type | Per-interface, per-type |
| **Web UI** | No | No | No |
| **Configuration** | XML (avahi-daemon.conf) | YAML/TOML | TOML |
| **Docker Support** | Community images | Community images | Community images |
| **Logging** | Syslog | Structured JSON logs | Standard output |
| **Active Development** | Mature (infrequent updates) | Active | Active |
| **Resource Usage** | ~10-20MB | ~5-10MB | ~5-10MB |
| **Additional Features** | Full mDNS responder, service publishing, DNS-SD browser | Reflection only | Reflection only, fine-grained ACLs |

## Avahi (Reflector Mode)

Avahi is the most widely deployed open-source mDNS/DNS-SD implementation on Linux. While primarily known as a service publisher and browser, it includes a built-in reflector mode that forwards mDNS traffic between interfaces.

### Key Features

- **Full mDNS stack** — not just a reflector; can publish and browse services locally
- **Wide compatibility** — the de facto mDNS implementation on Linux, compatible with Apple Bonjour
- **Mature and stable** — decades of deployment across millions of Linux systems
- **Systemd integration** — ships with systemd socket activation and service units
- **DNS-SD support** — full service type enumeration and browsing

### Docker Compose Configuration

```yaml
services:
  avahi-reflector:
    image: flungo/avahi:latest
    container_name: avahi-reflector
    restart: unless-stopped
    network_mode: host
    cap_add:
      - NET_ADMIN
    volumes:
      - ./avahi-daemon.conf:/etc/avahi/avahi-daemon.conf:ro
```

### Configuration (avahi-daemon.conf)

```ini
[server]
  host-name=avahi-reflector
  domain-name=local
  use-ipv4=yes
  use-ipv6=yes
  reflect-ipv=no

[reflector]
  enable-reflector=yes
  reflect-ipv=no

[wide-area]
  enable-wide-area=no

[publish]
  publish-addresses=yes
  publish-hinfo=yes
  publish-workstation=no
  publish-domain=yes
  publish-dns-servers=192.168.1.1
  publish-resolv-conf-dns-servers=yes
```

**Configuration notes:**
- `enable-reflector=yes` is the critical setting — without it, Avahi only responds locally
- `reflect-ipv=no` prevents IPv6 mDNS from being reflected to IPv4 interfaces (and vice versa)
- The reflector forwards ALL mDNS traffic — there is no per-service-type filtering
- Container requires `network_mode: host` and `NET_ADMIN` capability to bind to multicast addresses on multiple interfaces

### Pros and Cons

**Pros:**
- Most mature and widely tested mDNS reflector implementation
- Full mDNS stack beyond just reflection (service publishing, browsing)
- Well-documented with extensive community knowledge
- Available in virtually all Linux distribution repositories
- Compatible with both Apple Bonjour and other mDNS implementations

**Cons:**
- No per-service-type filtering — reflects all mDNS traffic indiscriminately
- Coarser-grained than dedicated reflectors
- Configuration uses XML format (less intuitive)
- Heavier resource usage than lightweight alternatives
- Infrequent updates (mature but not actively developed)
- Reflecting all traffic can cause unnecessary cross-VLAN broadcast volume

## mdns-reflector

mdns-reflector is a lightweight, purpose-built mDNS reflector written in Go. It focuses exclusively on cross-VLAN mDNS forwarding with support for per-interface and per-service-type filtering, making it more configurable than Avahi for complex network topologies.

### Key Features

- **Purpose-built** — designed specifically as a reflector, not a general-purpose mDNS stack
- **Per-service-type filtering** — selectively reflect only the service types you need (e.g., `_airplay._tcp`, `_printer._tcp`)
- **Per-interface configuration** — different reflection rules for different network interfaces
- **Lightweight** — Go binary with minimal memory footprint (~5-10MB)
- **Structured logging** — JSON-formatted logs for easy integration with log aggregators

### Docker Compose Configuration

```yaml
services:
  mdns-reflector:
    image: vfreex/mdns-reflector:latest
    container_name: mdns-reflector
    restart: unless-stopped
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./config.yaml:/etc/mdns-reflector/config.yaml:ro
    environment:
      - CONFIG_FILE=/etc/mdns-reflector/config.yaml
```

### Configuration (config.yaml)

```yaml
interfaces:
  - name: eth0
    description: "Server VLAN"
  - name: eth1
    description: "IoT VLAN"
  - name: eth2
    description: "Workstation VLAN"

# Service types to reflect (empty = reflect all)
services:
  - "_airplay._tcp"
  - "_raop._tcp"
  - "_printer._tcp"
  - "_ipp._tcp"
  - "_home-assistant._tcp"
  - "_chromecast._tcp"
  - "_googlecast._tcp"
  - "_smb._tcp"
  - "_hap._tcp"

# Exclude specific service types (even if listed above)
exclude_services:
  - "_workstation._tcp"

# Logging
log:
  level: "info"
  format: "json"

# TTL override for reflected records (seconds, 0 = use original)
ttl_override: 120
```

**Configuration notes:**
- List all interfaces that should participate in mDNS reflection
- The `services` list controls which service types are forwarded — leave empty to reflect all
- `ttl_override` controls the TTL of reflected records to prevent stale entries
- Requires `NET_RAW` capability in addition to `NET_ADMIN` for multicast socket binding

### Pros and Cons

**Pros:**
- Purpose-built for reflection with focused feature set
- Per-service-type filtering reduces unnecessary cross-VLAN traffic
- Lightweight Go binary with small memory footprint
- YAML configuration is straightforward and readable
- Active development with regular updates
- Structured JSON logging for observability integration

**Cons:**
- Smaller community than Avahi
- Less battle-tested in production environments
- No web UI for monitoring or management
- Limited documentation compared to Avahi
- Requires host network mode like all mDNS reflectors

## bonjour-reflector

bonjour-reflector is a Rust-based mDNS/Bonjour reflector that provides fine-grained control over cross-VLAN service discovery. It was designed as a more configurable alternative to Avahi reflector mode, with explicit allow/deny rules per interface and per service type.

### Key Features

- **Fine-grained ACLs** — control which service types are reflected between which specific interfaces
- **Rust-based reliability** — memory-safe implementation with no garbage collection pauses
- **Per-interface rules** — asymmetric reflection (e.g., reflect printers from server VLAN to workstation VLAN, but not vice versa)
- **Lightweight** — similar resource footprint to mdns-reflector
- **TOML configuration** — intuitive config format with clear rule definitions

### Docker Compose Configuration

```yaml
services:
  bonjour-reflector:
    image: gandem/bonjour-reflector:latest
    container_name: bonjour-reflector
    restart: unless-stopped
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./config.toml:/etc/bonjour-reflector/config.toml:ro
```

### Configuration (config.toml)

```toml
[general]
# Network interfaces to listen on
interfaces = ["eth0", "eth1", "eth2"]

# Default TTL for reflected records (seconds)
default_ttl = 120

# Logging level: debug, info, warn, error
log_level = "info"

# Service types to reflect
[services]
# Allow these service types globally
allowed = [
  "_airplay._tcp",
  "_raop._tcp",
  "_printer._tcp",
  "_ipp._tcp",
  "_home-assistant._tcp",
  "_chromecast._tcp",
  "_googlecast._tcp",
  "_hap._tcp",
  "_smb._tcp",
  "_nfs._tcp",
]

# Deny these service types (overrides allowed)
denied = [
  "_workstation._tcp",
  "_device-info._tcp",
]

# Per-interface overrides
[[interface_rules]]
interface = "eth2"
description = "Workstation VLAN - limited services"
allowed = [
  "_printer._tcp",
  "_ipp._tcp",
  "_smb._tcp",
]
```

**Configuration notes:**
- The `interfaces` array lists all network interfaces to bind to
- `allowed` and `denied` lists control global service type filtering
- `interface_rules` provide per-interface overrides — useful for asymmetric network policies
- The `default_ttl` controls how long reflected records remain valid in client caches

### Pros and Cons

**Pros:**
- Most granular access control of the three tools
- Per-interface asymmetric rules enable security-conscious configurations
- Rust implementation with memory safety guarantees
- TOML configuration is clear and well-structured
- Active development with community contributions
- Lightweight binary suitable for resource-constrained hardware

**Cons:**
- Smallest community and ecosystem of the three
- Less documentation and fewer deployment examples
- Rust ecosystem may be unfamiliar to some administrators
- No web UI or monitoring dashboard
- Newer project with less long-term operational history

## Network Requirements for mDNS Reflection

Running an mDNS reflector requires specific network configuration:

**Interface access** — The reflector must have access to all VLANs it should bridge. This typically means either:
- A server with multiple physical NICs, each connected to a different VLAN
- A single NIC with 802.1Q trunking and VLAN sub-interfaces (e.g., `eth0.10`, `eth0.20`, `eth0.30`)
- A virtualized environment with virtual interfaces mapped to different virtual networks

**Switch configuration** — Your managed switch must forward multicast traffic to the reflector port. Configure IGMP snooping to allow multicast groups 224.0.0.251 (mDNS) and ff02::fb (IPv6 mDNS) to reach the reflector.

**Firewall rules** — Ensure UDP port 5353 is allowed between all VLANs on the reflector server. This is the mDNS port and must be open bidirectionally.

**Routing** — mDNS reflection works at the data link layer and does not require IP routing between VLANs. Your default gateway and routing tables remain unchanged — only mDNS multicast traffic is bridged.

For organizations deploying services across multiple VLANs, understanding [Kubernetes CNI networking options](../2026-04-21-flannel-vs-calico-vs-cilium-self-hosted-kubernetes-cni-guide-2026/) provides additional context for how container networking intersects with physical VLAN segmentation.

## Security Considerations

mDNS reflection introduces security considerations that must be addressed:

- **Service exposure** — Reflecting mDNS across VLANs exposes service discovery information to networks that should not see it. Use per-service-type filtering to limit exposure to only the services that need cross-VLAN visibility.

- **Broadcast amplification** — Without filtering, reflecting all mDNS traffic can create broadcast storms in large networks with many VLANs and active services. Always configure service type allowlists.

- **Spoofing risk** — mDNS has no built-in authentication. A malicious device on any reflected VLAN could publish fake service records. Restrict which VLANs can publish services to the reflector using interface-level rules (supported by bonjour-reflector).

- **Information leakage** — mDNS records can reveal device hostnames, operating systems, and service configurations. Ensure your mDNS reflection policies align with organizational information security requirements.

## Choosing the Right mDNS Reflector

**Choose Avahi if:**
- You want the most mature, widely tested implementation
- You need full mDNS functionality (not just reflection) — service publishing, browsing, DNS-SD
- Your network is simple and reflecting all service types is acceptable
- You prefer distribution-packaged software (apt, yum, pacman)

**Choose mdns-reflector if:**
- You need per-service-type filtering to control cross-VLAN traffic
- You prefer Go-based tooling and structured JSON logging
- You want a focused, lightweight reflector without the overhead of a full mDNS stack
- You value active development with regular updates

**Choose bonjour-reflector if:**
- You need the most granular control with per-interface asymmetric rules
- You prefer Rust-based tooling with memory safety guarantees
- Your network has strict security requirements requiring allow/deny per interface
- You want fine-grained ACLs to limit which VLANs can publish specific services

## FAQ

### Can I run an mDNS reflector in a Docker container?

Yes, but the container must use `network_mode: host` because mDNS relies on multicast link-local traffic that Docker bridge networking cannot properly handle. Additionally, the container needs `NET_ADMIN` and `NET_RAW` capabilities to bind to multicast addresses on physical interfaces.

### Does mDNS reflection work across routed subnets?

No. mDNS reflection requires the reflector to have direct layer-2 access to all VLANs (via multiple interfaces or trunked sub-interfaces). It does not work across routed networks where multicast traffic is blocked by routers. For routed environments, consider DNS-based service discovery or unicast DNS-SD.

### How many VLANs can a single reflector handle?

Practically, a single reflector can handle 5-10 VLANs without issues. Beyond that, the multiplicative effect of reflecting queries from N VLANs to N-1 others can generate significant traffic. For larger networks, deploy multiple reflectors, each handling a subset of VLANs, or use per-service-type filtering to reduce volume.

### Will mDNS reflection break my network segmentation?

No. mDNS reflection only forwards multicast DNS discovery packets on UDP port 5353. All other traffic (HTTP, SSH, database connections) remains isolated by your VLAN routing policies and firewall rules. The reflector does not create a bridge between VLANs — it selectively forwards only mDNS queries and responses.

### Do I need to restart the reflector when adding a new VLAN?

For Avahi, yes — you need to update the configuration and restart the daemon. For mdns-reflector and bonjour-reflector, most support hot-reloading configuration files without a full restart. Always verify the new interface is receiving and forwarding mDNS traffic after changes.

### Can I use mDNS reflection with HomeKit and Chromecast?

Yes. This is one of the most common use cases. HomeKit uses the `_hap._tcp` service type and Chromecast uses `_googlecast._tcp` and `_chromecast._tcp`. Configure your reflector to include these service types in the allowed list. Note that some Chromecast devices may require additional mDNS service types (`_airplay._tcp`, `_raop._tcp`) for full functionality.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted mDNS Reflector: Avahi vs mdns-reflector vs bonjour-reflector (2026)",
  "description": "Compare three open-source mDNS reflector tools for cross-VLAN service discovery: Avahi, mdns-reflector, and bonjour-reflector. Includes Docker Compose configs and deployment guide.",
  "datePublished": "2026-05-09",
  "dateModified": "2026-05-09",
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
