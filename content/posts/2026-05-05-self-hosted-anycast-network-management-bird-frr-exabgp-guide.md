---
title: "Self-Hosted Anycast Network Management — BIRD, FRRouting, ExaBGP Monitoring Guide"
date: 2026-05-05
tags: ["anycast", "networking", "bgp", "dns", "self-hosted", "infrastructure"]
draft: false
---

Anycast networking — advertising the same IP address from multiple locations — is the backbone of resilient DNS, CDN, and DDoS mitigation infrastructure. While BGP daemons like BIRD and FRRouting handle the routing protocol, managing an anycast deployment requires additional tools for monitoring, health checking, and automated failover.

This guide covers three self-hosted approaches to anycast network management: **ExaBGP** (programmable BGP speaker for health-based routing), **BIRD with monitoring** (lightweight BGP daemon with external health checks), and **FRRouting with anycast tooling** (full-featured routing suite).

## Understanding Anycast Architecture

Anycast works by advertising the same IP prefix from multiple geographic locations via BGP. Routers direct traffic to the nearest instance based on BGP path selection rules. This provides:

- **Automatic failover**: If one node goes down, BGP withdraws the route and traffic shifts to the next closest node
- **Load distribution**: Traffic naturally flows to the nearest node based on network topology
- **DDoS resilience**: Attack traffic is distributed across all anycast nodes

The challenge is not just announcing routes — it is knowing when to withdraw them based on service health.

## ExaBGP — Programmable BGP for Health-Based Anycast

ExaBGP is a BGP daemon designed for programmability. Unlike traditional BGP daemons that focus on full routing tables, ExaBGP is optimized for injecting specific routes based on external health checks.

### ExaBGP Docker Compose Setup

```yaml
# docker-compose.yml for ExaBGP anycast health monitoring
version: "3.8"
services:
  exabgp:
    image: exabgp/exabgp:latest
    container_name: exabgp
    cap_add:
      - NET_ADMIN
      - NET_RAW
    network_mode: "host"
    volumes:
      - ./exabgp.conf:/etc/exabgp/exabgp.conf
      - ./healthcheck.sh:/etc/exabgp/healthcheck.sh
    restart: unless-stopped

  anycast-service:
    image: nginx:alpine
    container_name: anycast-web
    ports:
      - "80:80"
    volumes:
      - ./html:/usr/share/nginx/html
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 10s
      timeout: 3s
      retries: 3
    restart: unless-stopped
```

### ExaBGP Configuration with Health Checks

```
# exabgp.conf
neighbor 192.168.1.1 {
    router-id 10.0.0.1;
    local-address 192.168.1.100;
    local-as 65000;
    peer-as 65000;

    family {
        ipv4 unicast;
    }

    api health_check {
        processes [ healthcheck.sh ];
    }

    announce {
        ipv4 unicast {
            203.0.113.0/24;
        }
    }
}
```

### Health Check Script

```bash
#!/bin/bash
# /etc/exabgp/healthcheck.sh

SERVICE_URL="http://127.0.0.1/health"
ANYCAST_PREFIX="203.0.113.0/24"

check_service() {
    if curl -sf "$SERVICE_URL" > /dev/null 2>&1; then
        echo "announce route $ANYCAST_PREFIX next-hop self"
    else
        echo "withdraw route $ANYCAST_PREFIX next-hop self"
    fi
}

while true; do
    check_service
    sleep 10
done
```

ExaBGP reads the health check script stdout and announces or withdraws the anycast prefix based on service availability. This creates a tight coupling between service health and BGP route advertisement.

## BIRD with Anycast Monitoring

BIRD (BGP Internet Routing Daemon) is a lightweight, high-performance BGP daemon commonly used for anycast DNS deployments.

### BIRD Configuration for Anycast

```
# /etc/bird/bird.conf
router id 10.0.0.1;

protocol device {
    scan time 10;
}

protocol kernel {
    persist;
    export all;
    import all;
}

protocol bgp anycast {
    local as 65000;
    neighbor 192.168.1.1 as 65000;

    import filter {
        if net = 203.0.113.0/24 then accept;
        reject;
    };

    export filter {
        if net = 203.0.113.0/24 then accept;
        reject;
    };

    graceful restart;
}
```

### Docker Compose for BIRD

```yaml
version: "3.8"
services:
  bird:
    image: ozzieli/bird:latest
    container_name: bird
    cap_add:
      - NET_ADMIN
    network_mode: "host"
    volumes:
      - ./bird.conf:/etc/bird/bird.conf:ro
      - /var/run/bird:/var/run/bird
    restart: unless-stopped

  anycast-dns:
    image: technitium/dns-server:latest
    container_name: anycast-dns
    network_mode: "host"
    environment:
      - DNS_SERVER_DOMAIN=anycast.example.com
    volumes:
      - dns-data:/etc/dns
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5380/api/dns"]
      interval: 15s
      timeout: 5s
      retries: 3
    restart: unless-stopped

volumes:
  dns-data:
```

## FRRouting for Enterprise Anycast

FRRouting (FRR) is a full-featured routing suite that supports BGP, OSPF, ISIS, and more. It is the natural choice when anycast is part of a broader network infrastructure.

### FRR Docker Compose

```yaml
version: "3.8"
services:
  frr:
    image: frrouting/frr:stable-9.1
    container_name: frr
    cap_add:
      - NET_ADMIN
      - SYS_ADMIN
    network_mode: "host"
    volumes:
      - ./frr.conf:/etc/frr/frr.conf:ro
      - frr-state:/var/run/frr
    restart: unless-stopped

volumes:
  frr-state:
```

### FRR Configuration

```
! /etc/frr/frr.conf
frr defaults traditional
hostname anycast-router
log file /var/log/frr/frr.log informational

router bgp 65000
    bgp router-id 10.0.0.1
    neighbor 192.168.1.1 remote-as 65000
    neighbor 192.168.1.1 description upstream-peer
    address-family ipv4 unicast
        network 203.0.113.0/24
    exit-address-family
exit
```

## Comparison: Anycast Management Solutions

| Feature | ExaBGP | BIRD | FRRouting |
|---------|--------|------|-----------|
| **Primary focus** | Programmable BGP | Lightweight BGP | Full routing suite |
| **Health check integration** | Native (script stdout) | External (monitoring script) | Via external tools |
| **Route withdrawal** | Automatic on health fail | Manual or scripted | Manual or scripted |
| **Protocol support** | BGP only | BGP, BFD, OSPF | BGP, OSPF, ISIS, RIP, BFD |
| **Configuration** | Simple, health-focused | Moderate | Complex (enterprise-grade) |
| **Resource usage** | Low (~50MB RAM) | Very low (~20MB RAM) | Medium (~100MB RAM) |
| **Best for** | Service-driven anycast | DNS anycast | Multi-protocol networks |
| **Monitoring** | Via health check scripts | birdc CLI + external | vtysh CLI + external |

## Anycast Health Check Best Practices

Regardless of which BGP daemon you choose, proper health checking is essential:

```bash
# Multi-layer health check for anycast DNS
#!/bin/bash
check_anycast_health() {
    # Layer 1: Is the DNS process running?
    if ! pgrep -x named > /dev/null; then
        echo "CRITICAL: DNS process not running"
        return 1
    fi

    # Layer 2: Can we resolve locally?
    if ! dig @127.0.0.1 example.com +time=2 +tries=1 > /dev/null 2>&1; then
        echo "CRITICAL: Local DNS resolution failed"
        return 1
    fi

    # Layer 3: Is the system healthy?
    local load=$(cat /proc/loadavg | awk '{print $1}')
    local threshold=10
    if (( $(echo "$load > $threshold" | bc -l) )); then
        echo "WARNING: High load average: $load"
        return 1
    fi

    echo "OK: All health checks passed"
    return 0
}

# Announce or withdraw based on health
if check_anycast_health; then
    echo "announce route 203.0.113.0/24 next-hop self"
else
    echo "withdraw route 203.0.113.0/24 next-hop self"
fi
```

For broader BGP routing comparisons, see our [BGP routing daemon guide](../2026-04-19-frrouting-vs-bird-vs-openbgpd-self-hosted-bgp-routing-guide-2026/) and [BGP monitoring tools](../2026-05-04-self-hosted-bgp-monitoring-looking-glass-exabgp-bgpalerter-looking-glass-guide/). If you are building DNS infrastructure, our [DNS anycast deployment guide](../2026-04-22-bird-vs-frrouting-vs-keepalived-self-hosted-dns-anycast-guide-2026/) covers the DNS-specific aspects.

## Why Self-Host Anycast Infrastructure?

Self-hosted anycast deployments offer **cost advantages** over commercial CDN and DDoS mitigation services. By operating your own anycast nodes, you avoid per-GB bandwidth fees and can scale infrastructure incrementally.

**Geographic control** lets you place nodes exactly where your users are, rather than relying on a CDN provider's fixed PoP locations. This is especially valuable for organizations with regional user bases that commercial CDNs underserve.

**Full observability** means you can instrument every layer of your anycast stack — from BGP session state to application-level health — without vendor lock-in or API limitations.

When combined with [proper DNS management](../2026-05-04-self-hosted-dns-management-web-ui-powerdns-admin-dnscontrol-technitium-guide/), anycast becomes a powerful tool for building resilient, self-hosted infrastructure.

## FAQ

### What is anycast networking?
Anycast is a network addressing and routing method where the same IP address is advertised from multiple locations. Internet routers direct traffic to the nearest instance based on BGP path metrics. If one location fails, BGP automatically routes traffic to the next closest node.

### How does anycast differ from load balancing?
Load balancing distributes traffic across multiple servers at the application layer (Layer 7). Anycast operates at the network layer (Layer 3) — traffic is routed to the nearest node based on BGP topology, not application logic. Anycast does not provide true load balancing; it provides geographic proximity routing.

### Can anycast protect against DDoS attacks?
Anycast naturally disperses DDoS traffic across all advertising nodes, diluting the attack impact on any single location. However, it does not eliminate the attack — each node still receives a portion of the malicious traffic. For comprehensive DDoS protection, combine anycast with upstream scrubbing services or BGP blackhole routing.

### How do I monitor anycast health?
Use a combination of BGP session monitoring (birdc or vtysh CLI), route advertisement verification (ExaBGP health checks), and service-level monitoring (HTTP health endpoints, DNS resolution checks). Alert on BGP session drops, route withdrawals, and service health check failures.

### What BGP daemon should I use for anycast DNS?
For DNS-specific anycast, BIRD is the most popular choice due to its low resource usage and simple configuration. For service-driven anycast (where route advertisement depends on application health), ExaBGP is ideal. For enterprise networks with multiple routing protocols, FRRouting provides the most comprehensive feature set.

### How many anycast nodes do I need?
A minimum of 2 nodes provides failover capability. For production DNS, 3+ geographically distributed nodes are recommended. For CDN-like deployments, plan nodes based on user geography and latency requirements.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Anycast Network Management — BIRD, FRRouting, ExaBGP Monitoring Guide",
  "description": "Compare self-hosted anycast network management with ExaBGP, BIRD, and FRRouting. Includes Docker Compose configs, health checks, and BGP monitoring.",
  "datePublished": "2026-05-05",
  "dateModified": "2026-05-05",
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
