---
title: "Self-Hosted IPv6 Neighbor Discovery Tools: ndppd vs CoreRAD vs NDP Library (2026)"
date: "2026-05-13"
tags: ["ipv6", "neighbor-discovery", "networking", "ndp", "router-advertisement"]
draft: false
---

IPv6 Neighbor Discovery (ND) replaces ARP, ICMP Router Discovery, and redirect protocols from IPv4 with a unified ICMPv6-based protocol suite. It handles address resolution, duplicate address detection, router advertisement, and neighbor unreachability detection. However, many network environments need to extend or modify ND behavior -- proxying ND across subnets, controlling router advertisements, or implementing custom ND security policies.

This guide compares three open-source tools for self-hosted IPv6 Neighbor Discovery management: **ndppd** (NDP Proxy Daemon for cross-subnet address resolution), **CoreRAD** (extensible IPv6 Router Advertisement daemon with observability), and **mdlayher/ndp** (Go library for building custom ND protocol handlers).

## Understanding IPv6 Neighbor Discovery

IPv6 Neighbor Discovery (RFC 4861) operates through five ICMPv6 message types:

- **Router Solicitation (RS)** -- hosts request router information on startup
- **Router Advertisement (RA)** -- routers broadcast prefix, MTU, and default gateway information
- **Neighbor Solicitation (NS)** -- address resolution (the IPv6 equivalent of ARP request)
- **Neighbor Advertisement (NA)** -- address resolution response
- **Redirect** -- routers inform hosts of a better next-hop for a destination

In multi-subnet or containerized environments, standard ND behavior often falls short. When a router receives a packet for an IPv6 address on a directly-connected link but the host is actually behind a proxy or tunnel, ND proxying becomes necessary. Similarly, in virtualized environments, the host needs fine-grained control over RA content to prevent rogue routers and ensure correct SLAAC (Stateless Address Auto-Configuration) behavior.

## ndppd -- NDP Proxy Daemon

**GitHub:** [DanielAdolfsson/ndppd](https://github.com/DanielAdolfsson/ndppd) -- **Stars:** 384 -- **License:** MIT

ndppd is a lightweight NDP (Neighbor Discovery Protocol) proxy daemon that forwards Neighbor Solicitation and Advertisement messages between network interfaces. It is the go-to solution for exposing IPv6 addresses of VMs or containers to the upstream router when you cannot use bridge mode.

Key features:
- **Proxy-ND** -- responds to Neighbor Solicitation requests on behalf of hosts on a different interface
- **Multi-interface support** -- proxies between any number of interfaces simultaneously
- **Dynamic address discovery** -- automatically discovers hosts via RA and kernel routing table
- **Lightweight** -- written in C, minimal memory footprint, suitable for embedded routers
- **Proxmox VE integration** -- widely used to enable IPv6 inside KVM containers and VMs on Proxmox

ndppd is particularly valuable in cloud and VPS environments where the host has a single /64 prefix and needs to route individual addresses to virtual machines without using bridge networking.

### ndppd Docker Compose Setup

```yaml
version: "3.8"
services:
  ndppd:
    image: ghcr.io/oneclickvirt/ndppd:latest
    container_name: ndppd-proxy
    privileged: true
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./ndppd.conf:/etc/ndppd.conf:ro
      - /proc:/host/proc:ro
    network_mode: "host"
    restart: unless-stopped
```

**ndppd.conf** (proxy between eth0 and vmbr0):

```
proxy eth0 {
  rule vmbr0 {
    autowire
  }
}

proxy vmbr0 {
  rule eth0 {
    autowire
  }
}
```

For environments without Docker images, ndppd installs directly from package repositories:

```bash
# Debian/Ubuntu
apt-get install ndppd

# Compile from source
git clone https://github.com/DanielAdolfsson/ndppd.git
cd ndppd && make && make install
```

### ndppd on Proxmox VE

```bash
# Enable IPv6 forwarding
echo "net.ipv6.conf.all.forwarding=1" >> /etc/sysctl.conf
sysctl -p

# Install and configure ndppd
apt install ndppd
cat > /etc/ndppd.conf << 'NDPEOF'
proxy vmbr0 {
  rule eth0 {
    autowire
  }
}
NDPEOF

systemctl enable ndppd && systemctl start ndppd
```

## CoreRAD -- Extensible Router Advertisement Daemon

**GitHub:** [mdlayher/corerad](https://github.com/mdlayher/corerad) -- **Stars:** 173 -- **License:** Apache-2.0

CoreRAD is a modern, extensible IPv6 Router Advertisement daemon written in Go. It provides fine-grained control over RA content, including prefix advertisements, MTU settings, DNS server information (RDNSS), and search domains (DNSSL).

Key features:
- **Declarative configuration** -- YAML-based config with clear semantics for each RA field
- **Observability** -- built-in Prometheus metrics exporter for RA transmission statistics
- **Multi-interface support** -- manage RA behavior per interface independently
- **RDNSS/DNSSL** -- advertise DNS servers and search domains via RA (RFC 6106 and RFC 8106)
- **OpenTelemetry integration** -- trace RA generation and transmission for debugging

CoreRAD replaces the older radvd (Router Advertisement Daemon) with a modern architecture that includes metrics, health checks, and structured logging. It is particularly useful in containerized environments where each interface may need different RA policies.

### CoreRAD Docker Deployment

```yaml
version: "3.8"
services:
  corerad:
    image: ghcr.io/mdlayher/corerad:latest
    container_name: corerad-daemon
    privileged: true
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./corerad.yaml:/etc/corerad/corerad.yaml:ro
    network_mode: "host"
    restart: unless-stopped
    ports:
      - "9090:9090"
```

**corerad.yaml** (RA with custom prefix and DNS):

```yaml
interfaces:
  - name: eth0
    advertise: true
    managed: false
    other: false
    mtu: 1500
    prefixes:
      - prefix: "2001:db8:1::/64"
        on_link: true
        autonomous: true
        preferred_lifetime: 86400
        valid_lifetime: 604800
    recursive_dns_servers:
      - address: "2001:db8:1::1"
        lifetime: 300
    search_domains:
      - domain: "internal.example.com"
        lifetime: 300
    prometheus:
      enabled: true
      address: "0.0.0.0:9090"
```

## mdlayher/ndp -- Go NDP Library

**GitHub:** [mdlayher/ndp](https://github.com/mdlayher/ndp) -- **Stars:** 237 -- **License:** MIT

The `mdlayher/ndp` library provides a pure Go implementation of the IPv6 Neighbor Discovery Protocol. Rather than being a standalone daemon, it is a building block for creating custom ND tools -- custom RA generators, ND security monitors, or protocol analyzers.

Key features:
- **Full ICMPv6 ND support** -- implements all five ND message types (RS, RA, NS, NA, Redirect)
- **Packet-level control** -- construct and parse individual ND messages with full field access
- **Connection-oriented API** -- listen on raw ICMPv6 sockets, send/receive ND messages
- **Integration with Go ecosystem** -- use with Prometheus, OpenTelemetry, or custom web dashboards
- **Cross-platform** -- works on Linux, BSD, and macOS with appropriate capabilities

This library is ideal when you need to build a custom ND solution that existing tools cannot provide -- for example, an ND monitoring system that detects rogue router advertisements or a testing framework that validates ND protocol compliance.

### Building a Custom ND Monitor with Go

```go
package main

import (
    "fmt"
    "log"
    "net"
    "github.com/mdlayher/ndp"
)

func main() {
    // Listen for NDP messages on eth0
    c, _, err := ndp.Listen("eth0", nil)
    if err != nil {
        log.Fatal(err)
    }
    defer c.Close()

    fmt.Println("Listening for NDP messages on eth0...")

    for {
        msg, _, from, err := c.ReadFrom()
        if err != nil {
            log.Printf("Read error: %v", err)
            continue
        }

        switch m := msg.(type) {
        case *ndp.RouterAdvertisement:
            fmt.Printf("RA from %v: M=%v, O=%v
", from, m.ManagedConfiguration, m.OtherConfiguration)
        case *ndp.RouterSolicitation:
            fmt.Printf("RS from %v
", from)
        case *ndp.NeighborSolicitation:
            fmt.Printf("NS from %v for %v
", from, m.TargetAddress)
        case *ndp.NeighborAdvertisement:
            fmt.Printf("NA from %v
", from)
        }
    }
}
```

## Comparison Table

| Feature | ndppd | CoreRAD | mdlayher/ndp |
|---------|-------|---------|--------------|
| **Type** | NDP proxy daemon | RA daemon | Go ND protocol library |
| **Stars / Activity** | 384, stable | 173, actively maintained | 237, active development |
| **Primary Use** | Cross-subnet ND proxying | Router Advertisement management | Building custom ND tools |
| **Language** | C | Go | Go (library) |
| **Proxy-ND** | Yes (primary feature) | No | Build your own |
| **RA Generation** | No | Yes (full RA control) | Yes (via library) |
| **Observability** | No | Prometheus metrics | Custom via Go ecosystem |
| **RDNSS/DNSSL** | No | Yes (RFC 6106, 8106) | Yes (build with library) |
| **SLAAC Support** | Proxy-based | Full prefix advertisement | Build your own |
| **Container Support** | Docker + host network | Docker + host network | Compile into Go binary |
| **Learning Curve** | Low (simple config) | Moderate (YAML config) | High (Go programming) |
| **License** | MIT | Apache-2.0 | MIT |

## Choosing the Right ND Tool

**Use ndppd when:**
- You need to expose IPv6 addresses of VMs/containers to an upstream router
- You are running Proxmox VE, LXC, or KVM with routed networking
- You have a single /64 prefix and need to proxy individual addresses
- You want a simple, lightweight solution with minimal configuration

**Use CoreRAD when:**
- You need fine-grained control over Router Advertisement content
- You want to advertise custom DNS servers and search domains via RA
- You need Prometheus metrics for RA monitoring and alerting
- You are replacing radvd in a modern infrastructure

**Use mdlayher/ndp when:**
- You need to build a custom ND monitoring or security tool
- You want to detect and alert on rogue router advertisements
- You need a testing framework for ND protocol validation
- You are developing a network analysis tool that parses ND traffic

For related reading, see our [VyOS vs OPNsense vs OpenWrt SD-WAN routing guide](../2026-05-03-vyos-vs-opnsense-vs-openwrt-self-hosted-sd-wan-edge-routing-guide/) and [Linux network bonding active-backup vs LACP guide](../2026-05-08-linux-network-bonding-active-backup-vs-lacp-vs-round-robin-guide/). For broader IPv6 management, check our [DNS Load Balancing guide](../2026-05-13-self-hosted-dns-load-balancing-dnsdist-powerdns-knot-resolver-guide/).

## Why Self-Host IPv6 Neighbor Discovery Tools?

IPv6 deployment in self-hosted environments frequently requires ND extensions that consumer-grade routers simply cannot provide. When you run a homelab, VPS cluster, or multi-tenant server, standard ND behavior breaks down in several ways.

First, containerized and virtualized workloads often use routed networking rather than bridged networking. In routed mode, the host kernel forwards packets between the VM's virtual interface and the physical uplink, but the upstream router has no way to resolve the VM's IPv6 address through standard ND. NDP proxying bridges this gap by intercepting Neighbor Solicitation messages on the physical interface and responding on behalf of the VM.

Second, Router Advertisement control is critical for network stability. Rogue RAs from misconfigured devices can cause hosts to configure incorrect IPv6 addresses, set wrong default gateways, or use suboptimal DNS servers. CoreRAD provides explicit RA control with monitoring, preventing these issues entirely.

Third, self-hosting ND tools means you control the security posture. In managed cloud environments, ND spoofing and RA-based attacks are mitigated by the cloud provider. In self-hosted setups, you are responsible for ND security -- validating RA sources, preventing ND cache poisoning, and monitoring for anomalous ND traffic patterns.

For IPv6 firewall configuration, see our [nftables GeoIP firewall guide](../2026-05-10-self-hosted-nftables-geoip-firewall-nft-geo-filter-geoipsets-guide/). For network monitoring, check our [Zabbix vs LibreNMS vs Netdata guide](../zabbix-vs-librenms-vs-netdata-network-monitoring-guide/).

## FAQ

### What is NDP proxying and why do I need it?

NDP proxying allows a host to respond to Neighbor Solicitation messages on behalf of devices on a different network segment. Without proxying, an upstream router cannot resolve the MAC address of a VM behind a routed interface, causing IPv6 connectivity to fail. ndppd solves this by listening for NS messages on the physical interface and forwarding them to the VM, then relaying the response back.

### Can CoreRAD replace radvd?

Yes. CoreRAD provides all the core functionality of radvd (prefix advertisement, MTU setting, managed/other flags) plus modern features like Prometheus metrics, YAML configuration, and RDNSS/DNSSL support. The configuration syntax is different, so you will need to translate your radvd.conf to CoreRAD's YAML format.

### Is ndppd compatible with Proxmox VE?

Yes, ndppd is widely used with Proxmox VE to enable IPv6 inside KVM virtual machines and LXC containers. The typical setup involves creating a bridge (vmbr0) with proxy_ndp enabled, then configuring ndppd to proxy between the physical interface and the bridge.

### How do I prevent rogue router advertisements?

Use a combination of RA Guard (switch-level filtering of RA messages on untrusted ports), CoreRAD for controlled RA generation on trusted interfaces, and ND monitoring (using the mdlayher/ndp library or similar) to detect unauthorized RA sources. Many managed switches support RA Guard via the `ipv6 nd raguard` command.

### Does CoreRAD support SLAAC?

Yes. CoreRAD advertises IPv6 prefixes with the Autonomous (A) flag set, which tells hosts to generate their own addresses using SLAAC (Stateless Address Auto-Configuration). You can also set the Managed (M) and Other (O) flags to direct hosts to use DHCPv6 instead.

### What is the difference between Neighbor Discovery and DNS?

Neighbor Discovery resolves IPv6 addresses to link-layer (MAC) addresses on the local network segment. DNS resolves hostnames to IP addresses across any network. They operate at different layers -- ND at the link layer (ICMPv6) and DNS at the application layer (UDP/TCP port 53). However, RDNSS (Recursive DNS Server option in RAs) bridges the two by advertising DNS server addresses through ND.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted IPv6 Neighbor Discovery Tools: ndppd vs CoreRAD vs NDP Library (2026)",
  "description": "Compare open-source IPv6 Neighbor Discovery tools: ndppd for NDP proxying, CoreRAD for Router Advertisement management, and mdlayher/ndp Go library for custom ND solutions.",
  "datePublished": "2026-05-13",
  "dateModified": "2026-05-13",
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
