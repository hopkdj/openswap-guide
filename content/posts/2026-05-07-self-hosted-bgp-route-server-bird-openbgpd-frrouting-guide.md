---
title: "Self-Hosted BGP Route Server: BIRD vs OpenBGPD vs FRRouting 2026"
date: "2026-05-07"
tags: ["comparison", "guide", "self-hosted", "networking", "bgp", "routing", "infrastructure"]
draft: false
---

A BGP route server is a specialized router that allows multiple autonomous systems (ASes) to exchange routing information without establishing direct BGP peering sessions with each other. Instead of a full mesh of N*(N-1)/2 peering sessions, each AS peers with the route server once, dramatically simplifying Internet Exchange Point (IXP) and data center interconnect architectures.

This guide compares three open-source BGP daemons for building self-hosted route servers: **BIRD**, **OpenBGPD**, and **FRRouting (FRR)**.

## Overview

| Feature | BIRD | OpenBGPD | FRRouting (FRR) |
|---------|------|----------|-----------------|
| GitHub Stars | 1,200+ | 400+ (OpenBSD) | 4,200+ |
| License | GPL-2.0 | ISC | GPL-2.0 |
| BGP Support | BGP4+ | BGP4+ | BGP4+ with extensions |
| Route Server Mode | Yes | Yes | Yes |
| RPKI Validation | Yes | Yes | Yes |
| BGP Large Communities | Yes | Yes | Yes |
| IPv6 Support | Yes | Yes | Yes |
| BFD Integration | Yes | Yes | Yes |
| MPLS Support | Limited | No | Full |
| VRF Support | Yes | No | Yes |
| Config Language | Custom DSL | OpenBSD-style | Cisco-like CLI |
| Multi-protocol | BGP, OSPF, RIP, BFD | BGP, OSPF, RIP | BGP, OSPF, ISIS, RIP, EIGRP, PIM |
| Primary OS | Linux | OpenBSD, Linux | Linux |

## BIRD: The IXPs Choice

[BIRD](https://bird.network.cz/) (BGP Internet Routing Daemon) is the most widely used BGP route server software at Internet Exchange Points worldwide. Developed by CZ.NIC, it is designed specifically for large-scale route server deployments.

### Route Server Configuration

```
# /etc/bird/bird.conf - BGP Route Server
router id 192.168.1.1;

protocol kernel {
    persist;
    scan time 60;
    import all;
    export filter {
        if source = RTS_BGP then accept;
        reject;
    };
}

protocol device {
    scan time 10;
}

# BGP Route Server template
template bgp rs_template {
    local as 64512;
    multihop;
    graceful restart;
    ipv4 {
        import filter rs_import;
        export filter rs_export;
    };
    ipv6 {
        import filter rs_import;
        export filter rs_export;
    };
}

# Route server import filter
filter rs_import {
    if from = 192.168.1.10 then {
        bgp_community.add((64512, 100));
        accept;
    }
    if from = 192.168.1.20 then {
        bgp_community.add((64512, 200));
        accept;
    }
    reject;
}

# Route server export filter
filter rs_export {
    if source = RTS_BGP then accept;
    reject;
}

# Peer definitions
protocol bgp peer_1 from rs_template {
    neighbor 192.168.1.10 as 65001;
    description "Peer AS65001";
}

protocol bgp peer_2 from rs_template {
    neighbor 192.168.1.20 as 65002;
    description "Peer AS65002";
}
```

### RPKI Validation in BIRD

```
protocol rpki {
    roa table {
        server 192.168.1.100 port 323;
        retry 60;
        refresh 600;
    };
}

filter rs_import {
    if roa_check(roa_table, net, bgp_path.last) = RPKI_INVALID then {
        print "RPKI reject: ", net, " from ", from;
        reject;
    }
    accept;
}
```

### Docker Compose for BIRD

```yaml
version: "3.8"
services:
  bird:
    image: oznu/bird:latest
    network_mode: host
    volumes:
      - ./bird.conf:/etc/bird/bird.conf:ro
      - ./bird6.conf:/etc/bird/bird6.conf:ro
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
    command: ["-d"]
```

## OpenBGPD: Minimalist and Secure

[OpenBGPD](https://www.openbgpd.org/) is the BGP daemon from the OpenBSD project, ported to Linux. It follows the OpenBSD philosophy of simplicity, security, and clean code.

### Route Server Configuration

```
# /etc/bgpd.conf - OpenBGPD Route Server
AS 64512

router-id 192.168.1.1
listen on 192.168.1.1

neighbor 192.168.1.10 {
    descr "Peer AS65001"
    remote-as 65001
    set community 64512:100
}

neighbor 192.168.1.20 {
    descr "Peer AS65002"
    remote-as 65002
    set community 64512:200
}

match from any family any {
    set community 64512:999
}
match to any {
    set local-preference 100
}
```

### Docker Compose for OpenBGPD

```yaml
version: "3.8"
services:
  openbgpd:
    image: linuxserver/openbgpd:latest
    network_mode: host
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    volumes:
      - ./bgpd.conf:/etc/bgpd.conf:ro
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
      - NET_RAW
```

## FRRouting: Enterprise-Grade Feature Set

[FRRouting](https://frrouting.org/) (FRR) is the most feature-rich open-source routing suite, supporting BGP, OSPF, ISIS, RIP, EIGRP, PIM, and more. It is the Linux successor to Quagga.

### Route Server Configuration

```
! /etc/frr/frr.conf - FRR BGP Route Server
frr version 10.1
frr defaults datacenter
hostname route-server

router bgp 64512
 bgp router-id 192.168.1.1
 no bgp enforce-first-as

 neighbor RS-CLIENTS peer-group
 neighbor RS-CLIENTS remote-as external
 neighbor RS-CLIENTS route-server-client

 neighbor 192.168.1.10 peer-group RS-CLIENTS
 neighbor 192.168.1.10 description Peer-AS65001
 neighbor 192.168.1.20 peer-group RS-CLIENTS
 neighbor 192.168.1.20 description Peer-AS65002

 address-family ipv4 unicast
  neighbor RS-CLIENTS activate
 exit-address-family
```

### Docker Compose for FRRouting

```yaml
version: "3.8"
services:
  frr:
    image: frrouting/frr:v10.1
    network_mode: host
    volumes:
      - ./frr.conf:/etc/frr/frr.conf:ro
      - ./daemons:/etc/frr/daemons:ro
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
      - NET_RAW
    tmpfs:
      - /var/run/frr
```

## Route Server Best Practices

### 1. Use BGP Communities for Peer Identification

Tag incoming routes with a community that identifies the originating peer:

```
filter rs_import {
    if from = 192.168.1.10 then {
        bgp_community.add((64512, 10));
    }
    accept;
}
```

### 2. Apply AS-Path Filtering

Prevent route leaks by filtering routes with excessively long AS paths:

```
route-map FILTER-ASPATH deny 10
 match as-path access-list 100
ip as-path access-list 100 permit ^([0-9]+ ){10,}
```

### 3. Implement RPKI Validation

Always validate routes against RPKI to prevent route hijacking. All three daemons support RPKI natively.


### 4. Implement BGP Session Security with MD5 Authentication

Protect BGP peering sessions from TCP session hijacking by enabling MD5 authentication between the route server and each peer:

```
# BIRD - MD5 authentication
protocol bgp peer_1 from rs_template {
    neighbor 192.168.1.10 as 65001;
    password "shared-secret-key";
}

# FRR - MD5 authentication
neighbor RS-CLIENTS password shared-secret-key
```

### 5. Apply Prefix Limits Per Peer

Prevent a single peer from overwhelming the route server with excessive prefixes:

```
# BIRD - prefix limit
protocol bgp peer_1 from rs_template {
    neighbor 192.168.1.10 as 65001;
    ipv4 {
        import limit 10000 action warn;
        import filter rs_import;
        export filter rs_export;
    };
}

# FRR - prefix limit
neighbor 192.168.1.10 maximum-prefix 10000 80
```

### 6. Enable Graceful Restart for Zero-Downtime Maintenance

Configure BGP graceful restart so that route withdrawals are suppressed during route server maintenance:

```
# BIRD - graceful restart
template bgp rs_template {
    graceful restart;
    graceful restart time 120;
}

# FRR - graceful restart
router bgp 64512
 bgp graceful-restart restart-time 120
 bgp graceful-rerestart stalepath-time 300
```

## Why Self-Host a BGP Route Server?

For organizations operating at IXPs or managing multi-data-center connectivity, a self-hosted route server eliminates the complexity of full-mesh peering. Each peer connects once to the route server instead of managing dozens of bilateral BGP sessions.

For network routing foundations, see our [BGP routing guide](../2026-04-19-frrouting-vs-bird-vs-openbgpd-self-hosted-bgp-routing-guide-2026/) and [DNS anycast guide](../2026-04-22-bird-vs-frrouting-vs-keepalived-self-hosted-dns-anycast-guide-2026/). For load balancing across distributed infrastructure, our [bare-metal Kubernetes load balancer guide](../2026-04-26-metallb-vs-kube-vip-vs-cilium-lb-bare-metal-kubernetes-load-balancer-guide-2026/) complements route server deployments.

Self-hosting gives you:

- **Full routing policy control** - Define exactly which routes to accept, modify, and redistribute
- **No vendor lock-in** - Open-source daemons run on commodity hardware
- **Transparent peering** - Audit every route announcement and withdrawal
- **Cost reduction** - Eliminate expensive proprietary route server appliances
- **Rapid convergence** - Tune BGP timers and RPKI validation for sub-second failover

## FAQ

### What is a BGP route server and why do I need one?

A BGP route server allows multiple autonomous systems to exchange routes without establishing direct peering sessions. Instead of N*(N-1)/2 bilateral sessions, each AS peers with the route server once. This is essential at Internet Exchange Points (IXPs) where dozens or hundreds of networks need to exchange traffic.

### What is the difference between a route server and a route reflector?

A route server does not modify the AS-path and passes routes transparently so each peer sees the original AS-path. A route reflector modifies the AS-path and is an iBGP concept. Route servers are for eBGP inter-AS exchange; route reflectors are for iBGP intra-AS scaling.

### Which BGP daemon is best for an IXP route server?

BIRD is the most common choice at IXPs worldwide due to its mature route server features, efficient filtering language, and proven track record. FRRouting is preferred when you need additional protocols (OSPF, ISIS) alongside BGP. OpenBGPD is ideal for security-focused deployments on OpenBSD.

### How do I prevent route leaks with a self-hosted route server?

Implement BGP community-based filtering, RPKI validation, and IRR (Internet Routing Registry) checks. Tag incoming routes with peer-identifying communities and apply export policy that only redistributes valid routes.

### Can I run a BGP route server in a Docker container?

Yes, but you need `network_mode: host` or specific capabilities (`NET_ADMIN`, `NET_RAW`) because BGP requires binding to port 179 and injecting routes into the kernel routing table.

### How do I monitor a self-hosted route server?

Use `birdc show protocols` (BIRD), `bgpctl show neighbor` (OpenBGPD), or `vtysh -c "show ip bgp summary"` (FRR) for real-time status. For monitoring dashboards, export metrics via SNMP or Prometheus exporters.

## JSON-LD

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted BGP Route Server: BIRD vs OpenBGPD vs FRRouting 2026",
  "description": "Compare BIRD, OpenBGPD, and FRRouting for building self-hosted BGP route servers. Includes route server configs, RPKI validation, Docker Compose, and IXP best practices.",
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
