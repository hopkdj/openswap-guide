---
title: "BIRD vs FRRouting vs Keepalived: Self-Hosted DNS Anycast Routing Guide 2026"
date: 2026-04-22
tags: ["comparison", "guide", "self-hosted", "dns", "networking", "anycast", "high-availability"]
draft: false
description: "Complete guide to building self-hosted DNS anycast infrastructure using BIRD, FRRouting, and Keepalived. Compare features, configurations, and learn step-by-step deployment."
---

DNS anycast is one of the most powerful yet underutilized techniques for building resilient, low-latency infrastructure. By advertising the same IP address from multiple locations, anycast ensures that DNS queries are automatically routed to the nearest healthy server — no load balancer, no geo-DNS provider, no SaaS dependency required.

In this guide, we compare three self-hosted tools for building DNS anycast: [BIRD](https://bird.network.cz/), [FRRouting (FRR)](https://frrouting.org/), and [Keepalived](https://www.keepalived.org/). We cover how each works, when to use which, and provide complete Docker and bare-metal deployment configurations.

## Why Self-Host DNS Anycast?

Commercial DNS providers like Cloudflare, AWS Route 53, and Google Cloud DNS offer anycast out of the box. But they come with trade-offs: vendor lock-in, unpredictable pricing at scale, and limited control over routing policies.

Self-hosted DNS anycast gives you:

- **Full control** over routing decisions, BGP communities, and failover behavior
- **Predictable costs** — no per-query fees, no egress charges between your own servers
- **Data sovereignty** — DNS data never leaves your infrastructure
- **Resilience** — no single provider outage can take down your entire DNS stack
- **Learning** — deep understanding of how BGP, VRRP, and anycast actually work

For organizations running authoritative DNS (with PowerDNS, BIND9, or Knot DNS) across multiple data centers, anycast is the gold standard for availability. Let's look at the tools that make it possible.

## Comparison Overview

| Feature | BIRD | FRRouting (FRR) | Keepalived |
|---------|------|-----------------|------------|
| **Primary protocol** | BGP, OSPF, RIP, BFD | BGP, OSPF, IS-IS, RIP, BFD | VRRP, BFD |
| **Anycast method** | BGP route advertisement | BGP route advertisement | VRRP virtual IP |
| **License** | GPLv2 | GPLv2 | GPLv2+ |
| **Language** | C | C | C |
| **Latest release** | 2.16.x | 10.2+ | 2.3.x |
| **GitHub stars** | N/A (GitLab) | 4,100+ | 4,500+ |
| **Last updated** | Active (GitLab) | Apr 2026 | Nov 2025 |
| **Docker support** | Community images | Official + community | Official + community |
| **Configuration style** | Declarative config | Cisco/Juniper-like CLI | Declarative config |
| **Learning curve** | Medium | High | Low |
| **Best for** | Simple anycast, edge routers | Full routing suite, ISPs | VRRP failover, simple HA |

### When to Use Each Tool

**BIRD** is the simplest option for pure anycast. If your upstream provider already peers with you and you just need to advertise an anycast prefix, BIRD does it in ~20 lines of configuration. It is lightweight, fast, and has been the go-to for DNS anycast since the early 2000s.

**FRRouting** is the heavyweight choice. It supports the most protocols (BGP, OSPF, IS-IS, RIP, BFD, PIM, EIGRP) and is actively developed by a large community. Choose FRR if you need advanced BGP features like route filtering, communities, or multipath load balancing across multiple upstreams.

**Keepalived** takes a different approach. Instead of BGP, it uses VRRP to elect a master router that owns a virtual IP. This works well within a single data center but does not provide true anycast across geographic locations. Use Keepalived for local high availability rather than cross-site anycast.

## BIRD: Minimalist BGP Daemon

BIRD (BGP Intermediate Routing Daemon) has been a staple of DNS anycast deployments since 1999. Its strength is simplicity — it does BGP and a handful of IGP protocols, and it does them well.

### BGP Configuration for DNS Anycast

Here is a production-ready BIRD configuration for advertising a /32 anycast prefix:

```conf
# /etc/bird/bird.conf

router id 10.0.1.1;

# Define the anycast IP we want to advertise
filter announce_anycast {
    if net = 203.0.113.53/32 then accept;
    reject;
}

# BGP session to upstream peer
protocol bgp upstream_peer {
    local as 65001;
    neighbor 192.168.1.1 as 65000;

    # Only announce the anycast prefix
    export filter announce_anycast;

    # Import default route from upstream
    import all;

    # Graceful restart
    graceful restart on;
}

# Static route for the anycast VIP on loopback
protocol static {
    route 203.0.113.53/32 via "lo";
}
```

### Docker Compose for BIRD

```yaml
version: "3.8"

services:
  bird:
    image: ghcr.io/karlmdavis/bird:latest
    container_name: bird-anycast
    restart: unless-stopped
    network_mode: host
    cap_add:
      - NET_ADMIN
    volumes:
      - ./bird.conf:/etc/bird/bird.conf:ro
      - /var/log/bird:/var/log/bird
    environment:
      - TZ=UTC
```

The `network_mode: host` is required because BIRD needs direct access to network interfaces for BGP peering. The `NET_ADMIN` capability allows it to manipulate routing tables.

### Health Checking with BIRD

BIRD supports BFD (Bidirectional Forwarding Detection) for fast failure detection:

```conf
protocol bfd bfd_upstream {
    neighbor 192.168.1.1;
    interface "eth0";
    interval 0.3, 0.03;
    multiplier 3;
}

protocol bgp upstream_peer {
    # ... existing config ...
    bfd bfd_upstream;
}
```

With BFD configured, BIRD detects upstream failures in under 1 second and withdraws the anycast route, causing traffic to shift to the next closest node.

## FRRouting: Full-Featured Routing Suite

FRRouting (FRR) is a fork of Quagga that has become one of the most popular open-source routing platforms. With over 4,100 GitHub stars and commits as recent as April 2026, it is under active development.

### BGP Configuration for DNS Anycast

FRR uses a Cisco-like CLI, which is familiar to network engineers:

```bash
! /etc/frr/frr.conf

frr version 10.2
frr defaults traditional
hostname dns-anycast-node
log syslog informational
!
router bgp 65001
  bgp router-id 10.0.1.1
  neighbor 192.168.1.1 remote-as 65000
  neighbor 192.168.1.1 description upstream-peer
  !
  address-family ipv4 unicast
    neighbor 192.168.1.1 activate
    network 203.0.113.53/32
    exit-address-family
  !
exit
!
ip route 203.0.113.53/32 lo
!
line vty
exit
```

### Advanced BGP: Communities and Route Maps

FRR shines when you need advanced routing policies:

```bash
! Define BGP communities for traffic engineering
bgp community new

route-map SET_COMMUNITY permit 10
  match ip address prefix-list ANYCAST_PREFIX
  set community 65001:100 65001:200
  set local-preference 200
exit

ip prefix-list ANYCAST_PREFIX seq 5 permit 203.0.113.53/32

router bgp 65001
  address-family ipv4 unicast
    neighbor 192.168.1.1 route-map SET_COMMUNITY out
  exit-address-family
exit
```

This configuration attaches BGP communities to the anycast prefix, allowing upstream peers to apply traffic engineering policies based on those communities.

### Docker Compose for FRR

```yaml
version: "3.8"

services:
  frr:
    image: frrouting/frr:v10.2
    container_name: frr-anycast
    restart: unless-stopped
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./daemons:/etc/frr/daemons
      - ./frr.conf:/etc/frr/frr.conf
      - ./vtysh.conf:/etc/frr/vtysh.conf
      - frr_run:/var/run/frr
    environment:
      - FRR_LOGGING=stdout
    tmpfs:
      - /var/run/frr:mode=0750

volumes:
  frr_run:
    driver: local
```

The `daemons` file controls which routing protocols FRR starts:

```conf
# /etc/frr/daemons
bgpd=yes
ospfd=no
staticd=yes
zebra=yes
vtysh_enable=yes
```

Only enable the daemons you need. Running fewer protocols reduces memory usage and attack surface.

## Keepalived: VRRP-Based High Availability

Keepalived takes a fundamentally different approach. Rather than advertising routes via BGP, it uses VRRP (Virtual Router Redundancy Protocol) to elect a master that owns a shared virtual IP. This works within a single broadcast domain — ideal for data center local HA, not cross-site anycast.

### Keepalived Configuration

```conf
# /etc/keepalived/keepalived.conf

global_defs {
    router_id DNS_NODE_01
    notification_email {
        admin@example.com
    }
    smtp_server 127.0.0.1
    smtp_connect_timeout 30
}

vrrp_script chk_dns {
    script "/etc/keepalived/check_dns.sh"
    interval 3
    weight -20
    fall 3
    rise 2
}

vrrp_instance DNS_VIP {
    state MASTER
    interface eth0
    virtual_router_id 53
    priority 100
    advert_int 1

    authentication {
        auth_type PASS
        auth_pass s3cureVRRP!
    }

    virtual_ipaddress {
        203.0.113.53/32 dev lo
    }

    track_script {
        chk_dns
    }
}
```

### DNS Health Check Script

```bash
#!/bin/bash
# /etc/keepalived/check_dns.sh

# Check if DNS service is responding
if /usr/bin/dig @127.0.0.1 example.com A +short +time=1 +tries=1 > /dev/null 2>&1; then
    exit 0
fi

# Secondary check: is the DNS process running?
if pgrep -x "named" > /dev/null || pgrep -x "pdns_server" > /dev/null; then
    exit 0
fi

exit 1
```

Make the script executable: `chmod +x /etc/keepalived/check_dns.sh`. When the health check fails, Keepalived reduces the node's priority and triggers a failover to the backup node.

### Docker Compose for Keepalived

```yaml
version: "3.8"

services:
  keepalived:
    image: osixia/keepalived:2.0.20
    container_name: keepalived-ha
    restart: unless-stopped
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./keepalived.conf:/container/service/keepalived/assets/keepalived.conf
      - ./check_dns.sh:/container/service/keepalived/assets/check_dns.sh
    environment:
      - KEEPALIVED_INTERFACE=eth0
```

Note: Keepalived in Docker requires `network_mode: host` because VRRP uses multicast traffic that does not traverse Docker bridge networks.

## Comparison: BGP Anycast vs VRRP

| Criterion | BGP Anycast (BIRD/FRR) | VRRP (Keepalived) |
|-----------|----------------------|-------------------|
| **Geographic scope** | Global — works across data centers | Local — single L2 domain |
| **Failover speed** | 1-30s (BGP convergence) | < 3s (VRRP advertisement) |
| **Upstream dependency** | Requires BGP-speaking upstream | No upstream changes needed |
| **IP address model** | Multiple nodes share same /32 | Master-backup, single active |
| **Traffic distribution** | All nodes active simultaneously | Only master handles traffic |
| **Configuration complexity** | Medium-High | Low-Medium |
| **Protocol support** | BGP, OSPF, BFD | VRRP, BFD |

For true multi-site DNS anycast, BGP (via BIRD or FRR) is the only viable option. Keepalived is best used as a complement — for example, running Keepalived for local HA within each data center, and BIRD/FRR for anycast between data centers.

## Step-by-Step Deployment: Two-Site DNS Anycast

Here is a practical example of deploying DNS anycast across two data centers using BIRD.

### Network Topology

```
                     Internet
                        |
              +--------------------+
              |    Transit ISP     |
              |   (BGP peering)    |
              +--------------------+
                  |            |
        +---------+            +---------+
        |                                |
  +-----------+                    +-----------+
  | DC1: BIRD |                    | DC2: BIRD |
  | 10.0.1.1  |                    | 10.0.2.1  |
  +-----------+                    +-----------+
        |                                |
  +-----------+                    +-----------+
  | PowerDNS  |                    | PowerDNS  |
  | 10.0.1.2  |                    | 10.0.2.2  |
  +-----------+                    +-----------+

  Anycast VIP: 203.0.113.53 (advertised from both DCs)
```

### Step 1: Configure Authoritative DNS

Deploy PowerDNS on both nodes:

```yaml
version: "3.8"

services:
  pdns:
    image: pschiffe/pdns-mysql:4.9
    container_name: pdns-authoritative
    restart: unless-stopped
    environment:
      - PDNS_master=yes
      - PDNS_api=yes
      - PDNS_api-key=supersecretkey
      - PDNS_webserver=yes
      - PDNS_webserver-address=0.0.0.0
      - PDNS_webserver-password=webpass
      - PDNS_default-soa-name=ns1.example.com
      - PDNS_default-soa-mail=admin.example.com
    ports:
      - "53:53"
      - "53:53/udp"
      - "8081:8081"
    volumes:
      - pdns_data:/var/lib/mysql

volumes:
  pdns_data:
    driver: local
```

For related reading, see our [authoritative DNS comparison](../2026-04-18-powerdns-vs-bind9-vs-nsd-vs-knot-self-hosted-authoritative-dns-2026/) and [DNS load balancing guide](../dnsdist-vs-powerdns-recursor-vs-unbound-self-hosted-dns-load-balancing-guide-2026/) for complementary strategies.

### Step 2: Configure BIRD on Both Nodes

DC1 (`/etc/bird/bird.conf`):

```conf
router id 10.0.1.1;

filter announce_anycast {
    if net = 203.0.113.53/32 then accept;
    reject;
}

protocol bgp transit_isp {
    local as 65001;
    neighbor 192.168.1.1 as 64500;
    export filter announce_anycast;
    import all;
}

protocol static {
    route 203.0.113.53/32 via "lo";
}
```

DC2 uses identical config with `router id 10.0.2.1` and its own upstream neighbor IP.

### Step 3: Verify Anycast is Working

From a client machine, run:

```bash
# Verify the anycast IP is responding
dig @203.0.113.53 example.com A +short

# Check which node is answering (from traceroute)
traceroute -n 203.0.113.53

# On each BIRD node, verify the route is advertised
birdc show route 203.0.113.53/32
# Expected output: 203.0.113.53/32  via lo [static]
```

When both nodes are healthy, clients in different geographic regions receive responses from different nodes — automatically, with no client-side configuration.

## Monitoring and Alerting

Anycast DNS requires monitoring at multiple layers:

```bash
#!/bin/bash
# /usr/local/bin/check_anycast.sh — run via cron every 60s

ANYCAST_IP="203.0.113.53"
LOG_FILE="/var/log/anycast_health.log"

# Check if anycast IP is locally bound
if ip addr show lo | grep -q "$ANYCAST_IP"; then
    BOUND="yes"
else
    BOUND="no"
fi

# Check if BGP session is established
BGP_STATE=$(birdc show protocols all transit_isp 2>/dev/null | grep "BGP" | awk '{print $3}')

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) anycast_bound=$BOUND bgp_state=${BGP_STATE:-unknown}" >> "$LOG_FILE"

# Alert if BGP is not established
if [ "$BGP_STATE" != "Established" ]; then
    echo "CRITICAL: BGP session not established on $(hostname)" | \
        curl -X POST -H "Content-Type: application/json" \
        -d "{\"text\": \"BGP down on $(hostname)\"}" \
        https://your-webhook-url/alert
fi
```

For deeper network monitoring, pair this with tools like [Gatus for blackbox probing](../gatus-vs-blackbox-exporter-vs-smokeping-self-hosted-synthetic-monitoring/) or [network observability stacks](../ebpf-networking-observability-cilium-pixie-tetragon-guide/).

## Troubleshooting Common Issues

### BGP Session Not Establishing

```bash
# Check BIRD status
birdc show protocols

# View BGP state details
birdc show protocols all transit_isp

# Check for ACL blocks on port 179
iptables -L -n | grep 179

# Verify connectivity
tcpdump -i eth0 -nn port 179
```

### Anycast IP Not Responding

```bash
# Verify the IP is bound to loopback
ip addr show lo | grep 203.0.113.53

# Check if the static route exists
ip route show | grep 203.0.113.53

# Ensure DNS service is listening on the anycast IP
ss -ulnp | grep ":53 "
```

### Traffic Not Distributing

```bash
# Check BGP path from multiple vantage points
for node in dc1 dc2; do
    ssh $node "birdc show route 203.0.113.53/32"
done

# Verify upstream is receiving and propagating the route
ssh transit-router "show ip bgp 203.0.113.53"
```

## FAQ

### What is DNS anycast and how does it work?

DNS anycast works by advertising the same IP address from multiple geographic locations using BGP. Internet routers automatically direct queries to the topologically nearest node based on BGP path metrics. If one node goes offline, BGP withdraws its route and traffic shifts to the next nearest node — typically within seconds.

### Can I use DNS anycast with a single data center?

Technically yes, but it defeats the purpose. Anycast's value comes from geographic distribution — placing DNS servers close to your users worldwide. With a single data center, you get redundancy but not latency improvement. For single-site setups, VRRP (Keepalived) for local HA is more appropriate.

### Does DNS anycast require my own ASN?

Most transit ISPs will accept BGP advertisements from customers without their own ASN using private AS numbers (64512-65534) that the ISP strips before propagating. However, for full control and direct peering, you will need your own public ASN from your regional internet registry (RIR).

### How fast is failover with BGP anycast?

BGP convergence time depends on your configuration. With BFD enabled, failure detection happens in 300-900ms, and route withdrawal propagates in 1-5 seconds. Without BFD, standard BGP hold timers (typically 90-180 seconds) mean much slower failover. Always use BFD for production anycast.

### Can I combine BGP anycast and VRRP?

Yes, this is a common production pattern. Use VRRP (Keepalived) for high availability within each data center — so if one DNS server fails, another takes over the local anycast VIP. Then use BIRD or FRR to advertise that VIP via BGP from each data center. This gives you both local HA and geographic anycast.

### What is the minimum number of nodes for DNS anycast?

You need at least 2 nodes for anycast to provide redundancy. With 2 nodes, if one fails, all traffic goes to the other. With 3+ nodes, you get geographic distribution — clients in different regions hit different servers. Major DNS operators run dozens or hundreds of anycast nodes globally.

## Conclusion

Building self-hosted DNS anycast infrastructure is more accessible than ever. **BIRD** remains the simplest choice for straightforward anycast deployments — a few lines of configuration and you are advertising your DNS prefix globally. **FRRouting** is the go-to when you need advanced BGP features, protocol flexibility, and the backing of an active open-source community. **Keepalived** serves a different but complementary role, providing local high availability within each data center through VRRP.

For most organizations, the winning pattern is: Keepalived for local HA + BIRD or FRR for cross-site anycast + PowerDNS or BIND9 for authoritative DNS. This combination delivers the resilience and performance of commercial anycast DNS, entirely self-hosted.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "BIRD vs FRRouting vs Keepalived: Self-Hosted DNS Anycast Routing Guide 2026",
  "description": "Complete guide to building self-hosted DNS anycast infrastructure using BIRD, FRRouting, and Keepalived. Compare features, configurations, and learn step-by-step deployment.",
  "datePublished": "2026-04-22",
  "dateModified": "2026-04-22",
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
