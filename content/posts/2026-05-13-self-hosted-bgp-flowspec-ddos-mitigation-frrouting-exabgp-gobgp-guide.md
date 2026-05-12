---
title: "Self-Hosted BGP Flowspec DDoS Mitigation: FRRouting vs ExaBGP vs GoBGP"
date: "2026-05-13"
tags: ["bgp", "ddos-protection", "networking", "security", "flowspec"]
draft: false
---

Distributed Denial of Service (DDoS) attacks remain one of the most persistent threats to internet-facing infrastructure. While commercial DDoS mitigation services exist, they often come with high costs, vendor lock-in, and limited customization. BGP Flowspec (RFC 5575) offers a powerful, standards-based approach to distributed traffic filtering that can be deployed entirely with open-source software.

This guide compares three leading open-source BGP implementations — FRRouting, ExaBGP, and GoBGP — for deploying self-hosted Flowspec-based DDoS mitigation.

## What Is BGP Flowspec?

BGP Flowspec extends the Border Gateway Protocol to distribute traffic filtering rules across a network. Instead of relying on static ACLs on each router, a central controller pushes Flowspec routes that match specific traffic patterns (source/destination IP, port, protocol, packet length) and specify actions (drop, rate-limit, redirect, sample).

The key advantages of Flowspec for DDoS mitigation:

- **Distributed enforcement** — filtering happens at the network edge, closest to attack sources
- **Dynamic rule propagation** — new rules propagate in seconds via existing BGP sessions
- **Granular matching** — match on L3/L4 headers including TCP flags, ICMP types, and fragmented packets
- **Standardized protocol** — RFC 5575 ensures interoperability between vendors

## Comparison Table

| Feature | FRRouting | ExaBGP | GoBGP |
|---------|-----------|--------|-------|
| GitHub Stars | 4,127+ | 2,269+ | 4,052+ |
| Language | C | Python | Go |
| Flowspec Support | Yes (RFC 5575) | Yes (full) | Yes (RFC 5575 + 7674) |
| Rate Limiting | Yes | Via API actions | Yes (traffic-rate) |
| Redirect Action | Yes | Via API actions | Yes (traffic-action) |
| Docker Image | Official | Community | Official |
| Multi-Protocol | BGP, OSPF, IS-IS | BGP only | BGP, BMP, MRT |
| Configuration | CLI + vtysh | Python API | TOML/YAML + gRPC |
| Active Development | Very Active | Active | Active |
| License | GPL-2.0 | GPL-3.0 | Apache-2.0 |

## FRRouting

FRRouting is the most feature-complete open-source routing suite, supporting BGP, OSPF, IS-IS, RIP, and more. Its Flowspec implementation supports RFC 5575 with traffic filtering, rate limiting, and redirect actions.

### FRRouting Docker Compose

```yaml
version: "3.8"
services:
  frr:
    image: frrouting/frr:stable_9.1
    container_name: frr-flowspec
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./frr.conf:/etc/frr/frr.conf:ro
      - ./daemons:/etc/frr/daemons:ro
    network_mode: host
    restart: unless-stopped

  flowspec-controller:
    image: python:3.11-slim
    container_name: flowspec-controller
    volumes:
      - ./controller.py:/app/controller.py:ro
    command: python3 /app/controller.py
    restart: unless-stopped
```

### FRRouting Flowspec Configuration

```
! /etc/frr/daemons
bgpd=yes

! /etc/frr/frr.conf
frr defaults traditional
hostname frr-flowspec
router bgp 65001
  bgp router-id 10.0.0.1
  neighbor 10.0.0.2 remote-as 65001
  address-family ipv4 unicast
    neighbor 10.0.0.2 activate
  exit-address-family
  address-family ipv4 flowspec
    neighbor 10.0.0.2 activate
    neighbor 10.0.0.2 soft-reconfiguration inbound
  exit-address-family
!
line vty
!
```

FRRouting validates incoming Flowspec rules against the local routing table before installation, providing an additional safety layer against misconfigured filtering rules.

## ExaBGP

ExaBGP is a Python-based BGP daemon designed for programmability. It communicates with external processes via stdin/stdout, making it ideal for integrating Flowspec rule generation with monitoring systems, SIEM platforms, or custom DDoS detection scripts.

### ExaBGP Docker Compose

```yaml
version: "3.8"
services:
  exabgp:
    image: exabgp/exabgp:latest
    container_name: exabgp-flowspec
    volumes:
      - ./exabgp.conf:/etc/exabgp/exabgp.conf:ro
      - ./flowspec-rules.py:/etc/exabgp/rules.py:ro
    environment:
      - EXABGP_LOG=/var/log/exabgp
    network_mode: host
    restart: unless-stopped
```

### ExaBGP Configuration

```
# /etc/exabgp/exabgp.conf
group flowspec-peers {
    router-id 10.0.0.1;
    local-as 65001;
    local-address 10.0.0.1;

    neighbor 10.0.0.2 {
        peer-as 65001;
        family {
            ipv4 flowspec;
        }
        api {
            processes [rules];
        }
    }
}

process rules {
    run python3 /etc/exabgp/rules.py;
    encoder json;
}
```

ExaBGP's Python integration makes it the most programmable option. You can write custom detection logic that reads from Prometheus alerts, fail2ban logs, or network sensors, then push Flowspec rules dynamically.

## GoBGP

GoBGP is a BGP implementation written in Go, designed for modern cloud-native environments. It offers a rich gRPC API and supports Flowspec with both RFC 5575 and RFC 7674 (extended flowspec) features.

### GoBGP Docker Compose

```yaml
version: "3.8"
services:
  gobgp:
    image: osrg/gobgp:latest
    container_name: gobgp-flowspec
    volumes:
      - ./gobgp.conf:/etc/gobgp/gobgp.conf:ro
    network_mode: host
    restart: unless-stopped
    ports:
      - "50051:50051"
```

### GoBGP Configuration

```toml
# /etc/gobgp/gobgp.conf
[global.config]
  as = 65001
  router-id = "10.0.0.1"

[[neighbors]]
  [neighbors.config]
    neighbor-address = "10.0.0.2"
    peer-as = 65001

[[neighbors.afi-safis]]
  afi-safi-name = "ipv4-flowspec"
  [neighbors.afi-safis.config]
    enabled = true

[grpc.config]
  listen-port = 50051
```

### Pushing a Flowspec Rule via GoBGP CLI

```bash
# Block UDP traffic to port 53 from 192.168.1.0/24
gobgp global rib -a flowspec add match destination 10.0.0.0/24 protocol udp destination-port 53 then rate-limit 1000

# Drop all TCP SYN packets from a specific source
gobgp global rib -a flowspec add match source 203.0.113.0/24 protocol tcp tcp-flags syn then discard
```

## Choosing the Right BGP Flowspec Implementation

**Choose FRRouting if:** You need a full routing suite with OSPF, IS-IS, and other protocols alongside BGP Flowspec. It is the most production-tested option for traditional network environments.

**Choose ExaBGP if:** You need deep programmability and integration with existing Python-based monitoring, alerting, or SIEM systems. Its API-first design makes it ideal for custom DDoS detection workflows.

**Choose GoBGP if:** You operate in a cloud-native environment and prefer Go tooling, gRPC APIs, and TOML-based configuration. Its extended Flowspec support (RFC 7674) offers the most granular traffic matching.

## Why Self-Host BGP Flowspec?

Running your own BGP Flowspec infrastructure gives you complete control over DDoS mitigation without relying on upstream providers or expensive commercial services. When an attack hits, every minute of delay matters — with self-hosted Flowspec, your detection system can push filtering rules in seconds, not the 15-30 minutes typical of ticket-based upstream mitigation.

Data sovereignty is another critical factor. Commercial DDoS services often redirect your traffic through their scrubbing centers, giving third parties visibility into your traffic patterns. Self-hosted Flowspec keeps all traffic analysis and filtering within your own infrastructure, maintaining compliance with data protection regulations like GDPR, HIPAA, and PCI-DSS.

Cost savings are substantial. Enterprise DDoS mitigation services typically cost $2,000-$10,000+ per month depending on bandwidth and features. The open-source tools covered here are free, running on commodity hardware or existing router infrastructure. For organizations managing multiple networks, the ROI of self-hosted Flowspec becomes compelling within the first quarter.

For network operators running their own autonomous systems, Flowspec integrates directly into existing BGP peering arrangements. The same BGP sessions used for route exchange carry your mitigation rules, eliminating the need for separate management channels or proprietary APIs.

For related reading, see our [BGP routing guide](2026-04-19-frrouting-vs-bird-vs-openbgpd-self-hosted-bgp-routing-guide-2026/) covering FRRouting, BIRD, and OpenBGPD fundamentals, the [BGP monitoring and looking glass guide](2026-05-04-self-hosted-bgp-monitoring-looking-glass-exabgp-bgpalerter-looking-glass-guide/) for visibility into your BGP infrastructure, and our general [DDoS protection guide](2026-04-26-self-hosted-ddos-protection-nginx-haproxy-bunkerweb-crowdsec-guide/) for application-layer defenses that complement network-layer Flowspec filtering.

For related reading, see our [BGP routing fundamentals guide](../2026-04-19-frrouting-vs-bird-vs-openbgpd-self-hosted-bgp-routing-guide-2026/) covering FRRouting, BIRD, and OpenBGPD configuration, the [BGP monitoring and looking glass guide](../2026-05-04-self-hosted-bgp-monitoring-looking-glass-exabgp-bgpalerter-looking-glass-guide/) for visibility into your BGP infrastructure, and our [DDoS protection guide](../2026-04-26-self-hosted-ddos-protection-nginx-haproxy-bunkerweb-crowdsec-guide/) for application-layer defenses that complement network-layer Flowspec filtering.

## FAQ

### What is the difference between BGP Flowspec and traditional ACLs?

Traditional ACLs are statically configured on each device and must be manually updated. BGP Flowspec rules are distributed dynamically via BGP sessions, enabling centralized management and near-instant propagation across the entire network. Flowspec also supports more granular matching criteria including TCP flags, ICMP types, and fragment flags.

### Can BGP Flowspec mitigate volumetric DDoS attacks?

Flowspec can drop or rate-limit specific traffic flows identified by L3/L4 headers, making it effective for SYN floods, DNS amplification, NTP amplification, and other protocol-specific attacks. For pure volumetric attacks (e.g., UDP floods from millions of sources), Flowspec works best combined with upstream blackholing or traffic scrubbing, since per-source filtering becomes impractical at scale.

### Is BGP Flowspec safe to deploy in production?

Yes, with proper safeguards. FRRouting validates rules against the local RIB before installation. GoBGP supports the validate-best-external option to verify rule legitimacy. Always test Flowspec rules in a lab environment first, and implement a rollback procedure to withdraw malicious or misconfigured rules quickly.

### Do all routers support BGP Flowspec?

Most modern router operating systems support Flowspec: Cisco IOS-XR (7.x+), Juniper Junos (15.x+), Nokia SR OS (16.x+), and all three open-source implementations covered here. Legacy routers and some consumer-grade equipment do not support Flowspec. Verify support with your hardware vendor before deploying.

### How fast do Flowspec rules propagate?

Rule propagation depends on your BGP session configuration and network size. In a typical setup with 5-10 peers, Flowspec rules propagate within 1-3 seconds. For larger networks with 50+ peers, convergence typically completes within 10-30 seconds. Using route reflectors can further reduce propagation time.

### Can I use Flowspec for traffic engineering, not just DDoS mitigation?

Absolutely. Flowspec supports traffic redirection (redirect-to-VRF, redirect-to-IP-next-hop), making it useful for traffic engineering, service chaining, and selective traffic steering. You can redirect specific flows to inspection appliances, load balancers, or honeypots without affecting other traffic.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted BGP Flowspec DDoS Mitigation: FRRouting vs ExaBGP vs GoBGP",
  "description": "Compare FRRouting, ExaBGP, and GoBGP for deploying self-hosted BGP Flowspec-based DDoS mitigation with Docker compose configs and RFC 5575 rule examples.",
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
