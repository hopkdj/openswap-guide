---
title: "FRRouting vs BIRD vs OpenBGPD: Self-Hosted BGP Routing Guide 2026"
date: 2026-04-19
tags: ["comparison", "guide", "self-hosted", "networking", "bgp", "routing"]
draft: false
description: "Compare FRRouting, BIRD, and OpenBGPD for self-hosted BGP routing. Learn which open-source BGP daemon fits your homelab, multi-homing, or peering setup with Docker deployment guides."
---

Border Gateway Protocol (BGP) is the routing protocol that glues the internet together. It decides how traffic flows between autonomous systems — the networks operated by ISPs, cloud providers, and large enterprises. But BGP isn't just for tier-1 providers anymore. Homelab enthusiasts, small ISPs, and self-hosting communities increasingly run their own BGP setups for multi-homing, peering exchanges, and overlay network integration.

If you're running BGP on your own infrastructure, you need a reliable, open-source BGP daemon. The three most widely used options are **FRRouting**, **BIRD**, and **OpenBGPD**. Each takes a fundamentally different approach to routing. This guide compares them head-to-head and shows you how to deploy each one in a [docker](https://www.docker.com/) container.

## Why Self-Host Your BGP Routing?

Running your own BGP router gives you full control over how traffic enters and leaves your network. Here are the most common reasons to self-host BGP:

- **Multi-homing** — connect to two or more ISPs simultaneously for redundancy and better performance
- **IXP peering** — exchange traffic directly with other networks at an Internet Exchange Point
- **ASN ownership** — you've obtained your own Autonomous System Number and need to announce your prefixes
- **Route filtering** — apply custom policies to control which routes you accept and advertise
- **Traffic engineering** — use BGP communities, local preference, and AS-path prepending to steer traffic
- **Overlay network integration** — bridge your self-hosted overlay networks (like [ZeroTier or Netmaker](../self-hosted-overlay-networks-zerotier-nebula-netmaker-guide-2026/)) with your physical network infrastructure
- **Learning and experimentation** — test BGP behavior in a safe lab environment using tools like [GNS3 or EVE-NG](../2026-04-18-gns3-vs-eve-ng-vs-containerlab-self-hosted-network-simulation-2026.md)

Commercial routers from Cisco, Juniper, and Arista cost thousands of dollars. With open-source BGP daemons, you can run a full-featured BGP router on a $5/month VPS or a Raspberry Pi at home.

## The Three Contenders at a Glance

| Feature | FRRouting | BIRD | OpenBGPD |
|---|---|---|---|
| **GitHub** | [FRRouting/frr](https://github.com/FRRouting/frr) | [CZ-NIC/bird](https://github.com/CZ-NIC/bird) | [openbgpd-portable/openbgpd-portable](https://github.com/openbgpd-portable/openbgpd-portable) |
| **Stars** | 4,104 | 180 | 72 |
| **Last Updated** | 2026-04-18 | 2026-04-17 | 2026-04-13 |
| **Language** | C | C | C |
| **License** | GPLv2 | BSD-2-Clause / GPLv2 | ISC |
| **Protocols** | BGP, OSPFv2/v3, RIP, IS-IS, EIGRP, PIM, VRRP, NHRP, BFD | BGP, OSPFv2/v3, RIP, Babel, BFD | BGP, OSPFv2/v3, RPKI |
| **BGP Extensions** | Full RPKI, BMP, flowspec, graceful restart, add-path, multiprotocol | RPKI, graceful restart, add-path, BMP (limited) | RPKI, graceful restart (limited) |
| **Configuration** | Cisco IOS-style CLI (vtysh) | Declarative config file | OpenBSD-style config file |
| **Linux Support** | Excellent (native Linux project) | Excellent | Portable (Linux, BSD, macOS) |
| **Docker Official** | Yes (`frrouting/frr`) | No (community images) | No (community images) |
| **Best For** | Full routing stack, enterprise features | Lightweight BGP+OSPF, IXPs | Security-first, minimal BGP |

## FRRouting — The Full Protocol Suite

FRRouting (FRR) is the most feature-rich open-source routing daemon available. It originated as a fork of Quagga in 2016 and has since become the go-to routing stack for many cloud providers, ISPs, and data center operators.

### Protocol Support

FRR implements nearly every routing protocol you'll encounter in production:

- **BGP-4** with full multiprotocol extensions (IPv4, IPv6, VPNv4, VPNv6, EVPN)
- **OSPFv2** (RFC 2328) and **OSPFv3** (RFC 5340)
- **RIPv1/v2** and **RIPng**
- **IS-IS** for large-scale data center routing
- **EIGRP** (Cisco's proprietary protocol, reverse-engineered)
- **PIM** for multicast routing
- **BFD** for fast failure detection
- **VRRP** for gateway redundancy
- **NHRP** for NBMA networks

### Key Advantages

**Cisco IOS-style management** — FRR includes `vtysh`, a CLI that mimics Cisco IOS. If you've ever configured a Cisco router, FRR's command structure will feel immediately familiar:

```
router bgp 65001
  neighbor 192.168.1.1 remote-as 65002
  neighbor 192.168.1.1 description upstream-isp
  address-family ipv4 unicast
    network 10.0.0.0/24
    neighbor 192.168.1.1 activate
  exit-address-family
```

**RPKI validation** — FRR has built-in RPKI (Resource Public Key Infrastructure) support, allowing you to validate route origin authenticity and protect against route hijacking. Configure an RPKI cache:

```
rpki profile rpki-cache
  rpki cache rpki-validator.example.com port 3323
  exit
!
router bgp 65001
  rpki profile rpki-cache
```

**BGP flowspec** — deploy DDoS mitigation rules by distributing traffic filtering policies through BGP. This is critical for network operators who need to push blackhole routes or rate-limit specific traffic patterns across their infrastructure.

### Docker Compose Deployment

FRR provides official Docker images. Here's a production-ready compose file that runs FRR with persistent config:

```yaml
version: "3.8"

services:
  frr:
    image: frrouting/frr:v10.2.1
    container_name: frr-bgp
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
      - SYS_ADMIN
      - NET_RAW
    network_mode: "host"
    volumes:
      - ./frr.conf:/etc/frr/frr.conf:ro
      - ./daemons:/etc/frr/daemons:ro
      - frr-data:/var/run/frr
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  frr-data:
```

The `network_mode: "host"` setting is required because BGP needs direct access to the network stack. On Linux, you'll also need to enable IP forwarding:

```bash
sysctl -w net.ipv4.ip_forward=1
sysctl -w net.ipv6.conf.all.forwarding=1
```

### Sample BGP Configuration

Here's a practical multi-homing setup with two upstream ISPs:

```
! /etc/frr/frr.conf
hostname bgp-router
password zebra

router bgp 65001
  bgp router-id 203.0.113.1
  bgp log-neighbor-changes

  ! Upstream ISP-1
  neighbor 198.51.100.1 remote-as 64501
  neighbor 198.51.100.1 description isp-1-upstream
  neighbor 198.51.100.1 ebgp-multihop 2
  neighbor 198.51.100.1 timers 10 30

  ! Upstream ISP-2
  neighbor 198.51.100.33 remote-as 64502
  neighbor 198.51.100.33 description isp-2-upstream
  neighbor 198.51.100.33 ebgp-multihop 2
  neighbor 198.51.100.33 timers 10 30

  ! Route filtering - accept only default and specific prefixes
  ip prefix-list default-only seq 5 permit 0.0.0.0/0
  ip prefix-list customer-routes seq 5 permit 10.0.0.0/8 le 24

  ! Inbound policy
  neighbor 198.51.100.1 prefix-list default-only in
  neighbor 198.51.100.33 prefix-list default-only in

  ! Outbound - advertise our prefixes
  network 203.0.113.0/24

  ! Prefer ISP-1 as primary
  neighbor 198.51.100.1 route-map prefer-isp1 in

route-map prefer-isp1 permit 10
  set local-preference 200
```

## BIRD — The Lightweight IXP Favorite

BIRD (BIRD Internet Routing Daemon) is a lean, efficient routing daemon developed originally by the Czech Technical University in Prague and now maintained by CZ.NIC. It's particularly popular at European Internet Exchange Points and among operators who need BGP + OSPF without the weight of a full protocol suite.

### Design Philosophy

BIRD was built from scratch (not forked from Quagga or Zebra) with a focus on:

- **Efficiency** — minimal memory footprint, fast convergence
- **Correctness** — rigorous RFC compliance, well-tested BGP implementation
- **Simplicity** — clean declarative configuration, no interactive CLI

While FRR tries to be everything to everyone, BIRD does BGP and OSPF exceptionally well and leaves the rest alone. If you don't need IS-IS, EIGRP, or PIM, BIRD's smaller codebase means fewer bugs and a smaller attack surface.

### Configuration Style

BIRD uses a declarative configuration file that reads like a routing policy language rather than a CLI transcript:

```
# /etc/bird/bird.conf

router id 203.0.113.1;

protocol device {
    scan time 10;
}

protocol kernel {
    persist;
    learn;
    import all;
    export all;
}

protocol bgp isp1 {
    local as 65001;
    neighbor 198.51.100.1 as 64501;

    import filter {
        if net ~ [ 0.0.0.0/0 ] then accept;
        else reject;
    };

    export filter {
        if net = 203.0.113.0/24 then accept;
        else reject;
    };

    graceful restart time 120;
}

protocol bgp isp2 {
    local as 65001;
    neighbor 198.51.100.33 as 64502;

    import filter {
        if net ~ [ 0.0.0.0/0 ] then accept;
        else reject;
    };

    export filter {
        if net = 203.0.113.0/24 then accept;
        else reject;
    };

    graceful restart time 120;
}
```

BIRD's filter language is powerful: you can match on AS paths, communities, prefix lengths, and route attributes using a compact syntax. The `birdc` command-line client lets you inspect routing tables and protocol status at runtime:

```bash
birdc show protocols    # list all BGP sessions
birdc show route        # display the RIB
birdc show route all    # display all routes including hidden
```

### Docker Deployment

BIRD doesn't ship official Docker images, but community images work well. Here's a compose setup using a popular community build:

```yaml
version: "3.8"

services:
  bird:
    image: ghcr.io/ntppool/bird:latest
    container_name: bird-bgp
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
      - NET_RAW
    network_mode: "host"
    volumes:
      - ./bird.conf:/etc/bird/bird.conf:ro
      - bird-run:/run/bird
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  bird-run:
```

For a minimal custom image, you can build from the source repo:

```dockerfile
FROM alpine:3.20
RUN apk add --no-cache bird
COPY bird.conf /etc/bird/bird.conf
CMD ["bird", "-c", "/etc/bird/bird.conf", "-s", "/run/bird/bird.ctl"]
```

## OpenBGPD — Security-First BGP

OpenBGPD is part of the OpenBSD project, ported to Linux and other platforms by the OpenBGPD portable team. It follows the OpenBSD philosophy: minimal features, maximum security, clean code.

### Design Philosophy

OpenBGPD implements only BGP (with OSPFv2/v3 support), but does it with a focus on:

- **Security** — privilege separation, pledge/unveil system call restrictions, minimal attack surface
- **Simplicity** — configuration files are short and readable
- **Correctness** — strict RFC compliance, no protocol hacks

OpenBGPD is the smallest of the three daemons by code size. The portable version adds Linux compatibility while preserving the OpenBSD security model. If you value security and simplicity over feature breadth, OpenBGPD is the right choice.

### Configuration Style

OpenBGPD's configuration is concise and declarative:

```
# /etc/bgpd.conf

AS 65001
router-id 203.0.113.1

# Global settings
set rtable 0

# Peer group for upstream ISPs
group "upstreams" {
    remote-as external

    # Accept only default route from peers
    match from any prefix 0.0.0.0/0
    match from any prefix ::/0

    # Announce our prefixes
    announce self
}

neighbor 198.51.100.1 {
    descr "ISP-1 Upstream"
    group "upstreams"
}

neighbor 198.51.100.33 {
    descr "ISP-2 Upstream"
    group "upstreams"
}

# Announce our prefix
network 203.0.113.0/24
```

### RPKI Validation

OpenBGPD was one of the first BGP daemons to implement RPKI validation. Configure it to use an RPKI cache:

```
AS 65001
router-id 203.0.113.1

rpki server rpki.example.com port 3323

neighbor 198.51.100.1 {
    remote-as 64501
    # Reject invalid RPKI routes
    enforce rpkivalid
}
```

The `enforce rpkivalid` directive automatically drops routes that fail RPKI origin validation, protecting your network from prefix hijacking.

### Docker Deployment

Like BIRD, OpenBGPD doesn't have an official Docker image. Build a minimal container:

```yaml
version: "3.8"

services:
  openbgpd:
    build:
      context: ./openbgpd-docker
      dockerfile: Dockerfile
    container_name: openbgpd-bgp
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
      - NET_RAW
    network_mode: "host"
    volumes:
      - ./bgpd.conf:/etc/bgpd.conf:ro
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

```dockerfile
FROM alpine:3.20
RUN apk add --no-cache openbgpd
COPY bgpd.conf /etc/bgpd.conf
CMD ["bgpd", "-d", "-f", "/etc/bgpd.conf", "-n"]
```

## Comparison: Which BGP Daemon Should You Choose?

### Choose FRRouting If:

- You need **multiple routing protocols** (BGP + OSPF + IS-IS + EIGRP + PIM)
- You want a **Cisco IOS-style CLI** for interactive management
- You're running a **data center or ISP** with com[plex](https://www.plex.tv/) routing requirements
- You need **BGP flowspec** for DDoS mitigation
- You need **EVPN** for VXLAN overlay networks
- You want **official Docker images** and long-term support releases

### Choose BIRD If:

- You primarily need **BGP + OSPF** and nothing else
- You operate at an **IXP** and value lightweight, fast convergence
- You prefer **declarative configuration** over an interactive CLI
- You want a **smaller codebase** with fewer dependencies
- You're running BGP on **resource-constrained hardware** (Raspberry Pi, low-end VPS)

### Choose OpenBGPD If:

- **Security is your top priority** — privilege separation, pledge/unveil
- You want the **simplest possible BGP configuration**
- You only need **BGP + basic OSPF**
- You're already running **OpenBSD** (native support)
- You value **code auditability** [matrix](https://matrix.org/)smallest codebase of the three

### Decision Matrix

| Requirement | FRRouting | BIRD | OpenBGPD |
|---|:---:|:---:|:---:|
| Multi-protocol routing | ✅ | ⚠️ BGP+OSPF+RIP | ⚠️ BGP+OSPF |
| Cisco IOS CLI | ✅ | ❌ | ❌ |
| RPKI validation | ✅ | ✅ | ✅ |
| BGP flowspec | ✅ | ❌ | ❌ |
| EVPN / VXLAN | ✅ | ❌ | ❌ |
| Docker official image | ✅ | ❌ | ❌ |
| Memory footprint | ~50 MB | ~10 MB | ~8 MB |
| Security hardening | Standard | Standard | Excellent |
| Learning curve | Moderate | Moderate | Easy |
| IXP deployment | Good | Excellent | Good |

## Monitoring and Troubleshooting

Regardless of which daemon you choose, monitoring your BGP sessions is essential. Here are key commands for each:

### FRRouting

```bash
# Show BGP summary
vtysh -c "show bgp summary"

# Show BGP routes for a specific prefix
vtysh -c "show bgp 203.0.113.0/24"

# Show BGP neighbor status
vtysh -c "show bgp neighbors"

# Watch BGP updates in real-time
tail -f /var/log/frr/bgpd.log
```

### BIRD

```bash
# Show all protocol status
birdc show protocols

# Show BGP routes
birdc show route protocol isp1

# Show detailed neighbor info
birdc show protocols all isp1

# Watch BIRD logs
journalctl -u bird -f
```

### OpenBGPD

```bash
# Show neighbor summary
bgpctl show neighbor summary

# Show routes received from a peer
bgpctl show rib neighbor 198.51.100.1

# Show route announcements
bgpctl show rib

# Watch OpenBGPD logs
journalctl -u openbgpd -f
```

For comprehensive network monitoring that integrates with your BGP infrastructure, consider deploying a self-hosted monitoring stack like [Zabbix, LibreNMS, or Netdata](../zabbix-vs-librenms-vs-netdata-network-monitoring-guide/) to track session uptime, route counts, and BGP state transitions.

## FAQ

### Can I run BGP on a home network without an ASN?

You can run BGP internally for learning and lab purposes without an ASN. To exchange routes on the public internet, you'll need an ASN from your regional registry (ARIN, RIPE, APNIC, etc.) and IP address space that you own. Many homelab operators start with private ASNs (64512-65534) and private IP ranges for testing.

### Do I need a dedicated server for a BGP router?

No. All three daemons run comfortably on modest hardware. FRRouting uses around 50 MB of RAM under typical load, while BIRD and OpenBGPD each use under 10 MB. A $5/month VPS with 1 GB RAM is sufficient for a basic BGP setup with a few peers.

### Which BGP daemon is easiest to learn?

OpenBGPD has the simplest configuration syntax, making it the easiest to learn for basic BGP setups. FRRouting's vtysh CLI is the most familiar if you have Cisco experience. BIRD's filter language has a steeper learning curve but is very expressive once mastered.

### Can these daemons handle thousands of BGP routes?

Yes. BIRD and FRRouting are used by major IXPs that handle hundreds of thousands of routes. BIRD's RIB implementation is particularly efficient at scale. FRRouting's multi-threaded architecture handles large routing tables well on multi-core systems. OpenBGPD is less tested at extreme scale but handles typical multi-homing workloads without issue.

### Is RPKI validation important for self-hosted BGP?

Highly recommended. RPKI (Resource Public Key Infrastructure) validates that the AS announcing a prefix is authorized to do so, protecting against route hijacking. All three daemons support RPKI. Configure an RPKI validator like Routinator or Krill alongside your BGP daemon and enable origin validation.

### Can I run multiple BGP daemons on the same server?

Yes, but each daemon needs its own routing table or namespace since BGP uses TCP port 179. Use Linux network namespaces to isolate them:

```bash
# Create a namespace for each daemon
ip netns add frr-ns
ip netns add bird-ns

# Run each daemon in its namespace
ip netns exec frr-ns vtysh -f /etc/frr/frr-frr.conf
ip netns exec bird-ns bird -c /etc/bird/bird-bgp.conf
```

### How do I test BGP configurations before deploying?

Use network simulation tools like [GNS3, EVE-NG, or Containerlab](../2026-04-18-gns3-vs-eve-ng-vs-containerlab-self-hosted-network-simulation-2026/) to build virtual topologies. You can also run FRR, BIRD, or OpenBGPD in Docker containers connected via a bridge network and establish eBGP sessions between them using private ASNs.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "FRRouting vs BIRD vs OpenBGPD: Self-Hosted BGP Routing Guide 2026",
  "description": "Compare FRRouting, BIRD, and OpenBGPD for self-hosted BGP routing. Learn which open-source BGP daemon fits your homelab, multi-homing, or peering setup with Docker deployment guides.",
  "datePublished": "2026-04-19",
  "dateModified": "2026-04-19",
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
