---
title: "Self-Hosted DNS Anycast Health Checking: anycast-healthchecker vs BIRD vs Keepalived"
date: "2026-05-16"
tags: ["dns", "anycast", "networking", "bird", "keepalived", "health-check", "high-availability"]
draft: false
---

DNS Anycast is the standard approach for running highly available, geographically distributed DNS services. By advertising the same IP address from multiple locations via BGP, clients are automatically routed to the nearest available DNS server. But what happens when one of those servers goes down? Without health checking, BGP continues advertising the anycast IP from a failed node, sending queries into a black hole.

In this guide, we compare three open-source approaches to anycast health checking: **anycast-healthchecker** (a dedicated Python-based health checker), **BIRD** (the BGP routing daemon with integrated health checks), and **Keepalived** (the VRRP-based high-availability tool with anycast support). Each takes a fundamentally different approach to detecting service failures and withdrawing BGP advertisements.

## How DNS Anycast Health Checking Works

DNS anycast works by advertising the same service IP from multiple locations. When a DNS server fails, the anycast health checker must:

1. **Detect the failure**: Monitor the DNS service (port 53, query response, process health)
2. **Withdraw the route**: Remove the BGP advertisement for the anycast IP from the failed node
3. **Re-advertise on recovery**: Add the BGP advertisement back when the service recovers

The key difference between the three tools is **how** they integrate health checking with BGP route management.

## Comparison Table

| Feature | anycast-healthchecker | BIRD | Keepalived |
|---|---|---|---|
| **Stars / Activity** | 189 (unixsurfer) | Major (Linux routing) | Major (HA tool) |
| **Language** | Python | C | C |
| **Health Check Types** | TCP, UDP, DNS query, HTTP, custom | Custom scripts, BFD | TCP, HTTP, SMTP, custom scripts |
| **BGP Integration** | External (adds/removes routes via CLI) | Native (BGP daemon) | VRRP + optional BGP |
| **Failover Speed** | 2-5 seconds | 1-3 seconds (BFD) | 1-2 seconds |
| **Configuration** | INI file | BIRD config language | VRRP config |
| **IPv6 Support** | Yes | Yes | Yes |
| **Multi-IP Support** | Yes (multiple anycast IPs) | Yes (multiple prefixes) | Yes (multiple VIPs) |
| **Docker Support** | Community | Not recommended (kernel access) | Community |
| **Best For** | Dedicated health checking | Full BGP routing + health | VRRP-based HA with anycast |

## anycast-healthchecker — Dedicated Anycast Health Monitor

anycast-healthchecker is a purpose-built Python tool that monitors service health and manages BGP route advertisements accordingly. It runs as a daemon, periodically checking configured services and adding or withdrawing static BGP routes based on health status.

### Key Features

- **Service-agnostic**: Checks any TCP/UDP service — DNS (port 53), HTTP, custom endpoints
- **DNS-aware**: Can send actual DNS queries and validate responses, not just port checks
- **Multiple VIPs**: Manages multiple anycast IP addresses with independent health checks per IP
- **Clean integration**: Works with any BGP daemon (BIRD, FRRouting, Quagga) by manipulating static routes that BGP redistributes
- **Configurable thresholds**: Adjustable check intervals, failure thresholds, and recovery delays to prevent flapping

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  anycast-healthchecker:
    image: unixsurfer/anycast_healthchecker:latest
    container_name: anycast-healthchecker
    network_mode: "host"
    volumes:
      - ./anycast-healthchecker.ini:/etc/anycast-healthchecker/anycast-healthchecker.ini:ro
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
      - NET_RAW
    privileged: true
```

### Configuration Snippet

```ini
[DEFAULT]
check_interval = 2
fail_threshold = 3
success_threshold = 2

[anycast-vip1]
vip = 192.0.2.53
check_command = dig @127.0.0.1 example.com +short
check_type = dns
check_interval = 2
fail_threshold = 3

[anycast-vip2]
vip = 2001:db8::53
check_command = dig @::1 example.com +short
check_type = dns
check_interval = 2
fail_threshold = 3
```

## BIRD — BGP Routing Daemon with Integrated Health Checks

BIRD is a full-featured BGP routing daemon for Linux that can manage anycast route advertisements directly. Combined with BFD (Bidirectional Forwarding Detection) or custom health check scripts, BIRD provides integrated BGP route management without requiring a separate health checker daemon.

### Key Features

- **Native BGP**: Full BGP implementation — no external daemon needed for route management
- **BFD support**: Sub-second failure detection using BFD protocol for rapid anycast failover
- **Script integration**: Can execute health check scripts and conditionally advertise routes based on results
- **Multi-protocol**: Handles IPv4 and IPv6 BGP simultaneously
- **Filter language**: Powerful route filtering and manipulation via BIRD's configuration language

### BIRD Configuration with Health Check

```
# /etc/bird/bird.conf

protocol device {
    scan time 2;
}

protocol static {
    route 192.0.2.53/32 via "lo";
}

protocol bgp anycast_peer {
    local as 65001;
    neighbor 192.168.1.1 as 65002;

    ipv4 {
        export filter {
            if net = 192.0.2.53/32 then {
                # Only advertise if health check passes
                accept;
            }
            reject;
        };
    };
}

# Health check via external script
protocol static health_check {
    route 192.0.2.53/32 via "lo" {
        check link;
    };
}
```

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  bird:
    image: osrg/bird:latest
    container_name: bird-anycast
    network_mode: "host"
    volumes:
      - ./bird.conf:/etc/bird/bird.conf:ro
      - ./bird-scripts:/etc/bird/scripts:ro
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
      - NET_RAW
    privileged: true
```

## Keepalived — VRRP-Based HA with Anycast Support

Keepalived is primarily a VRRP (Virtual Router Redundancy Protocol) implementation, but it can also manage anycast IP addresses through its virtual IP configuration. Combined with health check scripts, Keepalived can add or remove anycast addresses based on service availability.

### Key Features

- **VRRP integration**: Combines anycast management with VRRP failover for comprehensive HA
- **Script-based health checks**: Flexible custom scripts for any type of service monitoring
- **Notification system**: Sends email/syslog notifications on state changes
- **Wide deployment**: Battle-tested in production environments for decades
- **Simple configuration**: Declarative VRRP instance configuration with health check hooks

### Keepalived Configuration Snippet

```
# /etc/keepalived/keepalived.conf

global_defs {
    notification_email {
        admin@yourdomain.com
    }
    notification_email_from keepalived@yourdomain.com
    smtp_server 127.0.0.1
    router_id DNS_ANYCAST
}

vrrp_script chk_dns {
    script "/etc/keepalived/check_dns.sh"
    interval 2
    weight -50
    fall 3
    rise 2
}

vrrp_instance anycast_dns {
    state MASTER
    interface eth0
    virtual_router_id 53
    priority 100
    advert_int 1

    virtual_ipaddress {
        192.0.2.53/32 dev lo
        2001:db8::53/128 dev lo
    }

    track_script {
        chk_dns
    }

    notify_backup "/etc/keepalived/withdraw_route.sh"
    notify_master "/etc/keepalived/advertise_route.sh"
}
```

### Health Check Script

```bash
#!/bin/bash
# /etc/keepalived/check_dns.sh
# Returns 0 if DNS is healthy, 1 if not

dig @127.0.0.1 example.com +short +timeout=1 +tries=1 > /dev/null 2>&1
exit $?
```

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  keepalived:
    image: osixia/keepalived:latest
    container_name: keepalived-anycast
    network_mode: "host"
    volumes:
      - ./keepalived.conf:/container/service/keepalived/assets/keepalived.conf:ro
      - ./check_dns.sh:/etc/keepalived/check_dns.sh:ro
      - ./withdraw_route.sh:/etc/keepalived/withdraw_route.sh:ro
      - ./advertise_route.sh:/etc/keepalived/advertise_route.sh:ro
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
      - NET_RAW
      - NET_BROADCAST
    privileged: true
```

## Why Self-Host Your DNS Anycast Health Checking?

Running your own DNS anycast infrastructure with proper health checking gives you control over DNS availability, geographic routing, and failure recovery — critical for organizations that cannot tolerate DNS downtime.

**Complete control over failover behavior**: Commercial anycast DNS providers (Cloudflare, AWS Route 53, Google Cloud DNS) handle health checking internally with opaque algorithms. Self-hosted anycast with open-source health checkers lets you define exactly what "healthy" means — whether that's a simple port check, a full DNS query with response validation, or a complex application-level health endpoint.

**No vendor pricing surprises**: Commercial anycast DNS pricing scales with query volume. Self-hosted anycast on commodity hardware or cloud VMs costs a flat infrastructure fee regardless of query volume. For high-traffic DNS deployments, this can represent significant cost savings.

**Geographic flexibility**: With self-hosted anycast, you can deploy DNS servers in any location — your own data centers, colocation facilities, cloud regions, or edge locations — and control the geographic routing via BGP community strings and local preference settings. Commercial providers limit you to their PoP locations.

**Regulatory compliance**: Some organizations have data sovereignty requirements that mandate DNS resolution within specific jurisdictions. Self-hosted anycast lets you deploy DNS servers in precisely the right locations while maintaining full control over query logging and data handling.

For DNS server selection, see our [authoritative DNS comparison](../2026-04-18-powerdns-vs-bind9-vs-nsd-vs-knot-self-hosted-authoritative-dns-2026/). For DNS security hardening, check our [DNS cache hardening guide](../2026-04-26-dns-cache-hardening-unbound-vs-bind9-vs-knot-resolver-self-hosted-security-guide-2026/). For DNS-over-QUIC setup, our [DoQ server comparison](../2026-05-02-knot-dns-vs-dnsdist-vs-unbound-self-hosted-dns-over-quic-guide/) covers modern encrypted DNS protocols.

## Choosing the Right Anycast Health Checker

**Choose anycast-healthchecker if**: You want a dedicated, purpose-built health monitoring tool that works with any BGP daemon. Its service-agnostic design, DNS-aware checking, and clean separation of health monitoring from route management make it the most flexible option for complex anycast deployments.

**Choose BIRD if**: You need a full BGP routing daemon with integrated health checking. BIRD is the right choice when you're already running BGP for other purposes (peering, transit, route servers) and want to consolidate anycast route management into the same daemon. BFD support provides the fastest failover times.

**Choose Keepalived if**: You need both VRRP-based failover and anycast route management from a single tool. Keepalived is ideal for deployments where you have active/passive server pairs within a site (managed by VRRP) and anycast across sites (managed by BGP advertisements triggered by Keepalived state changes).

## FAQ

### What is DNS Anycast and how does it work?
DNS Anycast works by advertising the same IP address from multiple geographic locations via BGP. Internet routers automatically direct DNS queries to the topologically nearest location. This provides both load distribution (queries spread across all locations) and high availability (if one location fails, traffic routes to the next nearest).

### Why do I need health checking for anycast?
Without health checking, BGP continues advertising the anycast IP from a failed node. Queries sent to that location are dropped, causing DNS resolution failures for clients routed there. Health checking detects service failures and withdraws the BGP advertisement, ensuring queries only reach healthy nodes.

### How fast should anycast failover be?
With proper health checking, failover should complete in 1-5 seconds. BFD (Bidirectional Forwarding Detection) with BIRD achieves the fastest times (1-3 seconds). Script-based checks with anycast-healthchecker or Keepalived typically take 2-5 seconds depending on check interval and failure threshold settings.

### Can I run DNS anycast on cloud VMs?
Yes, but with caveats. Most cloud providers don't support BGP advertisement from individual VMs. You need either: (a) dedicated servers with BGP peering capability, (b) cloud providers that support BGP (e.g., AWS Direct Connect, Google Cloud Interconnect), or (c) a hosting provider that offers BGP anycast as a service.

### Does anycast-healthchecker work with FRRouting?
Yes. anycast-healthchecker manages static routes on the local system, and FRRouting (like BIRD) can redistribute static routes into BGP. This means anycast-healthchecker is compatible with any BGP daemon that supports static route redistribution.

### Should I use anycast for internal DNS?
Anycast is most valuable for public-facing DNS services. For internal DNS, simpler approaches like DNS forwarding with multiple upstream servers or VRRP-based failover are usually sufficient. Anycast makes sense for internal DNS only when you have geographically distributed sites and want clients to automatically connect to the nearest DNS server.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DNS Anycast Health Checking: anycast-healthchecker vs BIRD vs Keepalived",
  "description": "Compare three open-source approaches to DNS anycast health checking. Covers anycast-healthchecker, BIRD, and Keepalived with Docker configs and BGP integration.",
  "datePublished": "2026-05-16",
  "dateModified": "2026-05-16",
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
