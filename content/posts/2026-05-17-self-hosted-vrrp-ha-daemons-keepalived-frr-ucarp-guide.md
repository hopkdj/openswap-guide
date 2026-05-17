---
title: "Self-Hosted VRRP/HA Daemons: Keepalived vs FRRouting VRRPd vs UCARP"
date: "2026-05-17"
tags: ["high-availability", "vrrp", "networking", "load-balancing", "failover"]
draft: false
---

Virtual Router Redundancy Protocol (VRRP) is the backbone of high-availability IP failover in self-hosted infrastructure. When a primary server goes down, VRRP ensures a virtual IP address seamlessly migrates to a standby node — keeping services reachable without DNS propagation delays or manual intervention.

This guide compares three open-source VRRP implementations: **Keepalived** (the industry standard), **FRRouting VRRPd** (part of the FRR protocol suite), and **UCARP** (a lightweight CARP alternative). We'll cover installation, Docker Compose deployments, configuration patterns, and help you choose the right tool for your HA setup.

## What Is VRRP and Why Self-Host It?

VRRP (RFC 5798) allows multiple routers or servers to share a virtual IP address. One node acts as the master, holding the VIP and responding to traffic. Backup nodes monitor the master via periodic VRRP advertisements. If advertisements stop, the highest-priority backup takes over the VIP — typically within 1-3 seconds.

Self-hosting VRRP is essential for:

- **Zero-downtime failover** — services bound to a VIP remain accessible during server maintenance or hardware failure
- **No single point of failure** — eliminates dependency on a single load balancer or gateway
- **Cloud-agnostic** — works on bare metal, VMs, and any cloud provider without proprietary HA services
- **Cost savings** — avoids expensive managed load balancer or cloud HA offerings
- **Full control** — tune priorities, preemption, health checks, and notification scripts to your exact needs

For infrastructure teams running PostgreSQL clusters, Kubernetes control planes, or reverse proxy fleets, VRRP provides the network-layer redundancy that application-level health checks can't replace.

## Keepalived: The Industry Standard

[Keepalived](https://github.com/acassen/keepalived) (4,500+ GitHub stars) is the most widely deployed VRRP implementation. Originally designed for Linux Virtual Server (LVS) load balancing, it has evolved into a standalone VRRP daemon with extensive health checking capabilities.

**Key features:**
- Full VRRPv2 and VRRPv3 (IPv4/IPv6) support
- Built-in TCP/HTTP/SMTP/SSL health checks
- Notification scripts on state transitions
- Multiple VIP support per instance
- Preemption control and priority-based election
- LVS integration for load balancer HA

### Keepalived Docker Compose Setup

```yaml
version: "3.8"
services:
  keepalived:
    image: osixia/keepalived:latest
    container_name: keepalived
    cap_add:
      - NET_ADMIN
      - NET_BROADCAST
      - NET_RAW
    network_mode: host
    environment:
      - KEEPALIVED_INTERFACE=eth0
      - KEEPALIVED_VIRTUAL_IPS=192.168.1.100
      - KEEPALIVED_PRIORITY=100
      - KEEPALIVED_STATE=MASTER
      - KEEPALIVED_UNICAST_PEERS=192.168.1.10,192.168.1.11
    volumes:
      - ./keepalived.conf:/etc/keepalived/keepalived.conf
    restart: unless-stopped
```

### Keepalived Configuration Example

```conf
global_defs {
    router_id KEEPALIVED_NODE_1
    notification_email {
        admin@example.com
    }
    notification_email_from keepalived@example.com
    smtp_server 127.0.0.1
    smtp_connect_timeout 30
}

vrrp_script chk_haproxy {
    script "/usr/bin/killall -0 haproxy"
    interval 2
    weight -20
    fall 3
    rise 2
}

vrrp_instance VI_1 {
    state MASTER
    interface eth0
    virtual_router_id 51
    priority 100
    advert_int 1
    authentication {
        auth_type PASS
        auth_pass S3cur3VRRP!
    }
    virtual_ipaddress {
        192.168.1.100/24 dev eth0
    }
    track_script {
        chk_haproxy
    }
    notify_master "/etc/keepalived/notify.sh MASTER"
    notify_backup "/etc/keepalived/notify.sh BACKUP"
    notify_fault "/etc/keepalived/notify.sh FAULT"
}
```

## FRRouting VRRPd: VRRP as Part of a Full Routing Suite

[FRRouting (FRR)](https://github.com/FRRouting/frr) (4,100+ GitHub stars) is a comprehensive routing protocol suite supporting BGP, OSPF, IS-IS, RIP, and VRRP through its `vrrpd` daemon. If you're already running FRR for dynamic routing, VRRPd provides native VRRP without deploying a separate tool.

**Key features:**
- Integrated with BGP, OSPF, and other FRR protocols
- VRRPv3 support (IPv4 and IPv6)
- Configuration via FRR's vtysh CLI or config files
- Consistent operational model across all protocols
- Active development with quarterly releases

### FRRouting VRRPd Docker Compose Setup

```yaml
version: "3.8"
services:
  frr-vrrp:
    image: frrouting/frr:stable_9.1
    container_name: frr-vrrp
    cap_add:
      - NET_ADMIN
      - NET_RAW
      - SYS_ADMIN
    network_mode: host
    volumes:
      - ./frr.conf:/etc/frr/frr.conf
      - ./daemons:/etc/frr/daemons
    restart: unless-stopped
```

### FRRouting VRRPd Configuration

```conf
! /etc/frr/daemons
zebra=yes
vrrpd=yes

! /etc/frr/frr.conf
frr version 9.1
frr defaults traditional
hostname frr-vrrp-node1
log syslog informational

vrrp interface eth0 vrid 51 {
  priority 100
  advertisement-interval 100
  ipv4 192.168.1.100/24
  authentication simple S3cur3VRRP!
  preempt true
}

router ospf
  network 192.168.1.0/24 area 0.0.0.0
```

VRRPd configuration is managed through FRR's unified config system, accessible via `vtysh` for runtime adjustments:

```bash
vtysh -c "show vrrp"
vtysh -c "show vrrp detail"
vtysh -c "configure terminal"
```

## UCARP: Lightweight CARP Implementation

[UCARP](https://github.com/jedisct1/UCARP) (170+ GitHub stars) implements the Common Address Redundancy Protocol (CARP) — OpenBSD's patent-free alternative to VRRP. CARP uses cryptographic authentication and is designed for simplicity over feature richness.

**Key features:**
- Patent-free CARP protocol (not VRRP)
- Cryptographic HMAC-SHA1 authentication
- Minimal resource footprint
- Simple configuration with command-line arguments
- Suitable for embedded systems and lightweight deployments

### UCARP Docker Compose Setup

```yaml
version: "3.8"
services:
  ucarp:
    image: linuxserver/ucarp:latest
    container_name: ucarp
    cap_add:
      - NET_ADMIN
      - NET_RAW
    network_mode: host
    environment:
      - VIP=192.168.1.100
      - SRVIP=1
      - PASSWORD=S3cur3CARP!
      - ADVSKEM=0
      - INTERFACE=eth0
      - ADDRESS=192.168.1.10
      - UCARP_OPTS=-P /etc/ucarp/vip-up.sh -p /etc/ucarp/vip-down.sh
    volumes:
      - ./vip-up.sh:/etc/ucarp/vip-up.sh:ro
      - ./vip-down.sh:/etc/ucarp/vip-down.sh:ro
    restart: unless-stopped
```

### UCARP Command-Line Configuration

```bash
# Master node
ucarp -i eth0 -v 51 -p S3cur3CARP! -a 192.168.1.100 \
  -s 192.168.1.10 -P /etc/ucarp/vip-up.sh -p /etc/ucarp/vip-down.sh

# Backup node (same command, different source IP)
ucarp -i eth0 -v 51 -p S3cur3CARP! -a 192.168.1.100 \
  -s 192.168.1.11 -P /etc/ucarp/vip-up.sh -p /etc/ucarp/vip-down.sh
```

### VIP Up/Down Scripts

```bash
#!/bin/bash
# vip-up.sh — executed when this node becomes MASTER
ip addr add 192.168.1.100/24 dev eth0
arping -c 3 -I eth0 -s 192.168.1.100 192.168.1.1

#!/bin/bash
# vip-down.sh — executed when this node becomes BACKUP
ip addr del 192.168.1.100/24 dev eth0
```

## Comparison: Keepalived vs FRRouting VRRPd vs UCARP

| Feature | Keepalived | FRRouting VRRPd | UCARP (CARP) |
|---------|-----------|----------------|--------------|
| Protocol | VRRPv2/v3 | VRRPv3 | CARP |
| GitHub Stars | 4,500+ | 4,100+ (FRR) | 170+ |
| IPv6 Support | Yes | Yes | Limited |
| Health Checks | Built-in (HTTP/TCP/SMTP) | Via FRR tracking | External scripts |
| Configuration | Declarative config file | FRR vtysh/config | Command-line args |
| Preemption | Configurable | Configurable | Yes (default) |
| Multiple VIPs | Yes | Yes | Per-instance |
| Notification Scripts | Yes | Limited | Up/down scripts |
| LVS Integration | Native | No | No |
| BGP/OSP Integration | No | Native (FRR suite) | No |
| Resource Usage | Low | Medium | Minimal |
| Docker Support | Yes (osixia image) | Yes (frrouting image) | Yes (linuxserver image) |
| Active Development | Yes (regular releases) | Yes (quarterly) | Sporadic (2019) |
| Learning Curve | Moderate | High (FRR knowledge) | Low |

## Choosing the Right VRRP Implementation

**Choose Keepalived if:**
- You need the most battle-tested VRRP implementation with proven production track records
- Built-in health checks (HTTP, TCP, SSL) are essential for your failover logic
- You're running LVS load balancers and want tight integration
- You need notification scripts for automated remediation on state changes

**Choose FRRouting VRRPd if:**
- You already run FRR for BGP, OSPF, or other routing protocols
- You want unified configuration and monitoring across all network protocols
- VRRPv3 IPv6 support is a requirement
- You prefer a single daemon managing your entire routing stack

**Choose UCARP if:**
- You need the simplest possible VIP failover with minimal configuration
- Patent-free CARP protocol is a legal requirement
- You're deploying on resource-constrained hardware or embedded systems
- You prefer explicit up/down scripts over declarative health checks

## Best Practices for VRRP Deployments

1. **Use dedicated interfaces** — Run VRRP on a separate network interface from production traffic to prevent split-brain scenarios during network congestion.

2. **Secure VRRP authentication** — Always configure VRRP authentication (PASS for Keepalived, simple for VRRPd, HMAC for CARP). Use strong passwords and rotate them periodically.

3. **Monitor failover events** — Log all state transitions and set up alerting. Use Keepalived's `notify_*` scripts or VRRPd's `show vrrp` to track election history.

4. **Test failover regularly** — Schedule periodic failover tests by stopping the VRRP daemon on the master node. Verify the backup takes over within the expected timeframe (1-3 seconds).

5. **Avoid split-brain** — Ensure only one node is MASTER at any time. Use `preempt delay` in Keepalived to prevent flapping during brief network partitions.

6. **Coordinate with application health** — VRRP handles network-layer failover, but application-level health checks should complement it. Combine VRRP with health check scripts that verify the actual service state.

## Why Self-Host VRRP?

Running your own VRRP infrastructure gives you complete control over failover behavior, priorities, and health checks — without relying on cloud provider-specific HA solutions. For organizations operating across multiple data centers or on bare metal, VRRP provides a standardized, vendor-neutral approach to IP redundancy.

Combined with load balancers like HAProxy or NGINX, VRRP creates a robust HA architecture that handles both network-layer and application-layer failures. For database clusters, pairing VRRP with PostgreSQL streaming replication or MySQL Group Replication ensures both network access and data consistency during failover events.

For related infrastructure topics, see our [Keepalived vs Corosync HA clustering guide](../2026-04-21-keepalived-vs-corosync-pacemaker-self-hosted-ha-clustering-guide/), [LVS load balancing guide](../2026-05-11-self-hosted-lvs-load-balancing-ipvs-keepalived-linux-virtual-server-guide/), and [HAProxy load balancing guide](../2026-04-22-bird-vs-frrouting-vs-keepalived-self-hosted-dns-anycast-guide-2026/).

## FAQ

### What is the difference between VRRP and CARP?
VRRP (Virtual Router Redundancy Protocol, RFC 5798) is an IETF standard supported by most vendors. CARP (Common Address Redundancy Protocol) is OpenBSD's patent-free alternative that uses cryptographic HMAC authentication. UCARP implements CARP, while Keepalived and FRRouting implement VRRP.

### How fast is VRRP failover?
With default settings (advert_int=1), failover typically occurs within 3 seconds. Reducing advert_int to 0.5-1 seconds and adjusting the master down interval can achieve sub-second failover, but may increase false positives during brief network glitches.

### Can I run VRRP in a Docker container?
Yes, but the container requires `NET_ADMIN`, `NET_RAW`, and `NET_BROADCAST` capabilities, and typically needs `network_mode: host` to receive VRRP multicast traffic. All three tools in this guide support Docker deployment.

### Does VRRP work across different subnets?
No. VRRP operates at Layer 2 and requires all participating nodes to be on the same broadcast domain (subnet). For cross-subnet HA, consider BGP anycast or DNS-based failover instead.

### Should I use VRRP or a cloud load balancer?
For cloud deployments, managed load balancers (AWS ALB, GCP LB, Azure LB) are often simpler. For bare metal, on-premises, or multi-cloud setups, VRRP provides a cost-effective, self-managed alternative with no vendor lock-in.

### What happens if both VRRP nodes think they're MASTER?
This is a split-brain condition, typically caused by network partition or misconfigured authentication. Both nodes will hold the VIP, causing duplicate IP conflicts. Use dedicated VRRP interfaces, strong authentication, and `preempt delay` to prevent this.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted VRRP/HA Daemons: Keepalived vs FRRouting VRRPd vs UCARP",
  "description": "Compare three open-source VRRP implementations for high-availability IP failover: Keepalived, FRRouting VRRPd, and UCARP. Includes Docker Compose configs and deployment guides.",
  "datePublished": "2026-05-17",
  "dateModified": "2026-05-17",
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
