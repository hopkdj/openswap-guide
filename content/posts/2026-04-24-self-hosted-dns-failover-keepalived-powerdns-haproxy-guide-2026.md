---
title: "Self-Hosted DNS Failover: Keepalived vs PowerDNS vs HAProxy Guide 2026"
date: 2026-04-24
tags: ["comparison", "guide", "self-hosted", "dns", "high-availability", "networking"]
draft: false
description: "Complete guide to self-hosted DNS failover solutions. Compare Keepalived (VRRP-based VIP failover), PowerDNS (DNS-level health checks), and HAProxy (proxy-level DNS failover) with Docker Compose configs and deployment guides."
---

DNS failover is one of the most critical components of a reliable self-hosted infrastructure. When your primary DNS server goes down — whether due to hardware failure, network partition, or a misconfiguration — your entire service stack becomes unreachable. Users cannot resolve your domain, APIs time out, and automated systems break.

This guide covers three proven approaches to DNS failover that you can run entirely on your own hardware: **Keepalived** for VRRP-based IP failover, **PowerDNS** for DNS-native health-checked failover, and **HAProxy** for proxy-level DNS load balancing with health checks. Each approach has different tradeoffs in complexity, failover speed, and operational overhead.

For a deeper dive into authoritative DNS servers themselves, see our [PowerDNS vs BIND9 vs NSD comparison](../powerdns-vs-bind9-vs-nsd-vs-knot-self-hosted-authoritative-dns-2026/) and the [DNS load balancing guide with dnsdist](../dnsdist-vs-powerdns-recursor-vs-unbound-self-hosted-dns-load-balancing-guide-2026/).

## Why Self-Host DNS Failover

Cloud DNS providers like Cloudflare, AWS Route 53, and Google Cloud DNS offer managed failover — but they come with tradeoffs:

- **Vendor lock-in** — your DNS configuration is tied to a single provider's API and dashboard
- **Recurring costs** — enterprise features like health checks and failover rules are often gated behind paid tiers
- **Dependency on external services** — if your cloud provider has an outage, your DNS goes with it
- **Compliance requirements** — regulated industries may require DNS data to stay on-premises

Self-hosted DNS failover gives you full control over the failover logic, health check intervals, and notification pipelines. You decide what "healthy" means, how fast failover triggers, and which servers take over. The tools below are all open source, run on commodity hardware, and have been battle-tested in production environments worldwide.

## How DNS Failover Works

DNS failover operates at different layers of the stack, each with distinct characteristics:

### Layer 2/3 Failover (Keepalived)

Keepalived uses the **Virtual Router Redundancy Protocol (VRRP)** to manage a shared virtual IP (VIP) between two or more servers. The primary server owns the VIP and answers DNS queries. If it stops sending VRRP advertisements, a backup server claims the VIP within seconds and begins answering queries with its own DNS daemon.

**Key property:** The DNS records themselves don't change — only the IP address that clients query shifts from one server to another.

### DNS-Level Failover (PowerDNS)

PowerDNS Authoritative Server supports **health-checked backends** through its generic MySQL/PostgreSQL backend or the Lua records feature. You can configure PowerDNS to return different IP addresses based on the health of upstream services, dynamically modifying DNS responses without changing the underlying zone file.

**Key property:** The DNS server IP stays constant, but the *answers* it returns change based on backend health.

### Proxy-Level Failover (HAProxy)

HAProxy can resolve DNS names for its backends and perform **active health checks** against them. By placing HAProxy in front of multiple DNS resolvers or authoritative servers, you get proxy-level failover with granular health checking (HTTP, TCP, custom scripts).

**Key property:** HAProxy acts as a DNS-aware load balancer, routing queries only to healthy backends.

## Comparison Table

| Feature | Keepalived | PowerDNS | HAProxy |
|---------|-----------|----------|---------|
| **Failover type** | VRRP VIP takeover | DNS response modification | Proxy-level routing |
| **Failover speed** | 1-3 seconds | 10-60 seconds (TTL dependent) | 1-5 seconds |
| **Health checks** | VRRP heartbeat only | HTTP/TCP/DNS/Lua scripts | HTTP/TCP/custom agents |
| **Active-Active** | No (active/passive) | Yes (multi-master) | Yes (weighted load balancing) |
| **Configuration** | Simple (keepalived.conf) | Moderate (pdns.conf + backend) | Moderate (haproxy.cfg) |
| **Docker support** | Requires NET_ADMIN/NET_RAW | Native image available | Native image available |
| **GitHub Stars** | 4,544 | 4,348 | 6,489 |
| **Language** | C | C++ | C |
| **Last Updated** | Nov 2025 | Apr 2026 | Apr 2026 |
| **Best for** | Simple active/passive DNS | Dynamic DNS with health-aware responses | DNS query load balancing with health checks |

## Approach 1: Keepalived — VRRP-Based DNS Failover

Keepalived is the simplest DNS failover approach. Two servers share a virtual IP address. The primary holds the VIP and runs your DNS daemon (BIND9, PowerDNS, Unbound). If the primary stops sending VRRP advertisements, the backup claims the VIP within 1-3 seconds.

### When to Use Keepalived

- You need the **fastest possible failover** (sub-3 seconds)
- Your DNS setup is simple: one active server, one passive backup
- You want minimal configuration and operational overhead
- You already run BIND9 or another DNS daemon and just need IP-level redundancy

### Docker Compose Setup

Keepalived requires `NET_ADMIN` and `NET_RAW` capabilities to manage VRRP packets. Here's a working Docker Compose configuration for a two-node active/passive DNS failover setup:

```yaml
# keepalived-primary/docker-compose.yml
version: "3.8"
services:
  keepalived:
    image: osixia/keepalived:latest
    container_name: keepalived-primary
    cap_add:
      - NET_ADMIN
      - NET_RAW
    network_mode: "host"
    environment:
      - KEEPALIVED_INTERFACE=eth0
      - KEEPALIVED_VIRTUAL_IPS=192.168.1.100
      - KEEPALIVED_PRIORITY=150
      - KEEPALIVED_STATE=MASTER
      - KEEPALIVED_UNICAST_PEERS=192.168.1.11
    restart: unless-stopped

  bind9:
    image: ubuntu/bind9:latest
    container_name: bind9-primary
    network_mode: "host"
    volumes:
      - ./named.conf:/etc/bind/named.conf
      - ./zones/:/etc/bind/zones/
    restart: unless-stopped
```

```yaml
# keepalived-backup/docker-compose.yml
version: "3.8"
services:
  keepalived:
    image: osixia/keepalived:latest
    container_name: keepalived-backup
    cap_add:
      - NET_ADMIN
      - NET_RAW
    network_mode: "host"
    environment:
      - KEEPALIVED_INTERFACE=eth0
      - KEEPALIVED_VIRTUAL_IPS=192.168.1.100
      - KEEPALIVED_PRIORITY=100
      - KEEPALIVED_STATE=BACKUP
      - KEEPALIVED_UNICAST_PEERS=192.168.1.10
    restart: unless-stopped

  bind9:
    image: ubuntu/bind9:latest
    container_name: bind9-backup
    network_mode: "host"
    volumes:
      - ./named.conf:/etc/bind/named.conf
      - ./zones/:/etc/bind/zones/
    restart: unless-stopped
```

The primary has `KEEPALIVED_PRIORITY=150` and `STATE=MASTER`, while the backup has `KEEPALIVED_PRIORITY=100` and `STATE=BACKUP`. Both nodes point their `KEEPALIVED_UNICAST_PEERS` to each other's real IP.

### Native Installation

```bash
# Debian/Ubuntu
apt update && apt install -y keepalived bind9

# RHEL/CentOS/Rocky
dnf install -y keepalived bind
```

The `keepalived.conf` for the primary node:

```conf
vrrp_instance VI_DNS {
    state MASTER
    interface eth0
    virtual_router_id 51
    priority 150
    advert_int 1

    unicast_src_ip 192.168.1.10
    unicast_peer {
        192.168.1.11
    }

    virtual_ipaddress {
        192.168.1.100/24
    }

    track_script {
        chk_bind9
    }
}

vrrp_script chk_bind9 {
    script "killall -0 named"
    interval 2
    weight -20
    fall 3
    rise 2
}
```

The `track_script` monitors whether BIND9 (`named`) is running. If it dies, the node's VRRP priority drops by 20, triggering a failover to the backup.

## Approach 2: PowerDNS — DNS-Level Failover with Health Checks

PowerDNS Authoritative Server offers a more flexible approach: instead of failing over the server IP, it changes the DNS *answers* based on the health of your backend services. This allows for granular, per-record failover decisions.

### When to Use PowerDNS

- You need **per-record failover** (only fail over specific domains, not everything)
- You want active-active DNS with multiple servers answering queries simultaneously
- You need Lua scripting for custom health check logic
- You're already using PowerDNS and want to add failover without changing your DNS server IP

### Docker Compose Setup

PowerDNS provides an official `docker-compose.yml` in its repository that runs the Authoritative Server, Recursor, and dnsdist together. Here's a simplified failover-focused setup:

```yaml
# powerdns-failover/docker-compose.yml
version: "3.8"
services:
  pdns-auth:
    image: powerdns/pdns-auth-49:latest
    container_name: pdns-auth
    environment:
      - PDNS_master=yes
      - PDNS_api=yes
      - PDNS_api-key=supersecretapikey
      - PDNS_allow-axfr-ips=0.0.0.0/0
      - PDNS_gmysql-host=db
      - PDNS_gmysql-user=pdns
      - PDNS_gmysql-password=pdns
      - PDNS_gmysql-dbname=pdns
    ports:
      - "53:53"
      - "53:53/udp"
      - "8081:8081"
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: mariadb:10.11
    container_name: pdns-db
    environment:
      - MARIADB_ROOT_PASSWORD=rootpass
      - MARIADB_DATABASE=pdns
      - MARIADB_USER=pdns
      - MARIADB_PASSWORD=pdns
    volumes:
      - pdns-data:/var/lib/mysql
    restart: unless-stopped

  pdns-recursor:
    image: powerdns/pdns-recursor-49:latest
    container_name: pdns-recursor
    environment:
      - PDNS_RECURSOR_allow_from=0.0.0.0/0
    ports:
      - "5353:53"
      - "5353:53/udp"
    depends_on:
      - pdns-auth
    restart: unless-stopped

volumes:
  pdns-data:
```

### Lua Records for Health-Checked Failover

PowerDNS's killer feature for failover is **Lua records**. You can embed health check logic directly into your DNS zone:

```lua
-- Example: return primary IP if healthy, fallback IP otherwise
ifhealth("192.168.1.20:80", "192.168.1.20", "10.0.0.20")
```

This record checks whether `192.168.1.20:80` responds. If it does, return `192.168.1.20`. Otherwise, return `10.0.0.20`.

You can also use the `ifurlup()` function for HTTP-based health checks:

```lua
-- Check if the primary web server responds, failover to backup
ifurlup("http://192.168.1.20/health", {
    {"192.168.1.20", "10.0.0.20"}
}, { interval = 10, timeout = 3 })
```

Enable Lua records in your PowerDNS configuration:

```conf
# /etc/powerdns/pdns.conf
enable-lua-records=true
lua-records-check-interval=10
```

## Approach 3: HAProxy — Proxy-Level DNS Failover

HAProxy is primarily known as an HTTP/TCP load balancer, but its **DNS resolver** feature makes it an excellent DNS failover proxy. You configure HAProxy to resolve backend DNS names and health check them, routing DNS queries only to healthy resolvers.

### When to Use HAProxy

- You have **multiple DNS resolvers** (e.g., Unbound, PowerDNS Recursor, dnsmasq) and want a single entry point
- You need weighted load balancing across DNS backends
- You want HTTP-based health checks against DNS server APIs
- You're already running HAProxy and want to consolidate your proxy layer

### Docker Compose Setup

```yaml
# haproxy-dns-failover/docker-compose.yml
version: "3.8"
services:
  haproxy:
    image: haproxy:2.9-alpine
    container_name: haproxy-dns
    ports:
      - "53:53"
      - "53:53/udp"
      - "8404:8404"
    volumes:
      - ./haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
    restart: unless-stopped

  unbound-1:
    image: mvance/unbound:latest
    container_name: unbound-1
    environment:
      - TZ=UTC
    restart: unless-stopped

  unbound-2:
    image: mvance/unbound:latest
    container_name: unbound-2
    environment:
      - TZ=UTC
    restart: unless-stopped
```

### HAProxy Configuration for DNS Failover

```conf
# haproxy.cfg
global
    log stdout format short local0
    maxconn 10000

defaults
    mode tcp
    timeout connect 1s
    timeout client 30s
    timeout server 30s
    log global
    option log-health-checks

resolvers dns_resolvers
    nameserver unbound1 unbound-1:53
    nameserver unbound2 unbound-2:53
    resolve_retries 3
    timeout resolve 1s
    timeout retry 1s
    hold valid 10s

frontend dns-in
    bind *:53
    bind *:53 proto udp
    default_backend dns-backends

backend dns-backends
    option tcp-check
    tcp-check send-binary 000a0000000100000000000003777777076578616d706c6503636f6d0000010001
    tcp-check expect binary 8180
    server unbound1 unbound-1:53 check inter 5s fall 3 rise 2
    server unbound2 unbound-2:53 check inter 5s fall 3 rise 2 backup
```

The `tcp-check` sends a DNS query for `www.example.com` and expects a valid response. If `unbound1` fails 3 consecutive checks, HAProxy routes all traffic to `unbound2`.

### HAProxy Stats Dashboard

The port `8404` binding exposes HAProxy's built-in stats page at `http://your-server:8404/stats`. This gives you a real-time view of which DNS backends are healthy, connection counts, and failover events.

For more advanced HAProxy management patterns, see our [HAProxy dataplane API vs Prometheus exporter guide](../haproxy-dataplane-api-vs-prometheus-exporter-vs-runtime-api-self-hosted-haproxy-management-guide-2026/).

## Choosing the Right Approach

| Scenario | Recommended Tool |
|----------|-----------------|
| Simple active/passive, fastest failover | **Keepalived** |
| Per-record failover with health-aware DNS | **PowerDNS** |
| Load balancing across multiple resolvers | **HAProxy** |
| Kubernetes DNS with health checks | **HAProxy** or **PowerDNS** |
| DNS failover + load balancer in one | **HAProxy** |
| Minimal config, maximum simplicity | **Keepalived** |
| Dynamic DNS responses based on service health | **PowerDNS** |

### Hybrid Approach

In production, you'll often see these tools combined:

1. **Keepalived** provides a VIP for the DNS server layer (ensuring the DNS server itself is highly available)
2. **PowerDNS** runs behind the VIP with health-checked Lua records for per-service failover
3. **HAProxy** sits in front of your application servers, using the PowerDNS VIP as its resolver

This layered approach gives you redundancy at every level: IP failover, DNS response failover, and application-level routing failover.

## Monitoring and Alerting

Regardless of which tool you choose, you need visibility into failover events:

```bash
# Keepalived: monitor VRRP state transitions
journalctl -u keepalived -f | grep "VRRP_Instance"

# PowerDNS: monitor Lua record health check results
pdns_control list | grep "lua"

# HAProxy: check backend status via stats socket
echo "show stat" | socat stdio /run/haproxy/admin.sock | \
  awk -F',' '$2 == "dns-backends" {print $1, $18, $37}'
```

For centralized monitoring, export HAProxy stats to Prometheus with the HAProxy exporter, use the PowerDNS API for zone health metrics, and monitor Keepalived VRRP state with a custom script that sends alerts on state transitions.

If you're building out a complete DNS infrastructure, you may also want to review our [Keepalived vs Corosync vs Pacemaker HA clustering guide](../keepalived-vs-corosync-pacemaker-self-hosted-ha-clustering-guide/) for broader high-availability patterns, and the [DNS anycast routing guide](../bird-vs-frrouting-vs-keepalived-self-hosted-dns-anycast-guide-2026/) for geographic DNS distribution.

## FAQ

### What is the fastest DNS failover method?

**Keepalived with VRRP** is the fastest, typically failing over in 1-3 seconds. This is because VRRP operates at the network layer — the backup server simply starts answering traffic on the virtual IP. No DNS TTL waiting is required. PowerDNS and HAProxy approaches depend on health check intervals (usually 5-10 seconds) and may also be subject to DNS TTL caching at the client level.

### Can I use Keepalived and PowerDNS together?

Yes, and this is a common production pattern. Keepalived manages a virtual IP shared between two PowerDNS servers. If the primary PowerDNS node fails, Keepalived moves the VIP to the secondary, which has a full copy of the DNS zone data from the shared database backend. This gives you both IP-level and DNS-level redundancy.

### How does DNS TTL affect failover?

DNS TTL (Time To Live) determines how long resolvers cache your DNS records. If your TTL is 300 seconds (5 minutes), clients may continue using a failed IP for up to 5 minutes after you change the record. For fast failover, set TTLs to 30-60 seconds on critical records. Keepalived avoids this entirely because the IP address doesn't change — only the server behind it does.

### Does HAProxy support UDP DNS?

Yes, HAProxy 2.4+ supports UDP mode with `mode tcp` for TCP DNS and `bind *:53 proto udp` for UDP DNS. Both TCP and UDP can be configured on the same frontend. The health check mechanism described in this guide uses TCP checks, which work for both TCP and UDP backends since DNS servers listen on both protocols.

### Which approach works best for Kubernetes?

For Kubernetes, **HAProxy** as an Ingress controller (with DNS resolver configuration) or **PowerDNS** with Kubernetes as a backend are the most common choices. Keepalived can be used as a MetalLB replacement for load balancer VIP management, but it requires host networking which may not be desirable in all cluster configurations.

### How do I test DNS failover without causing an outage?

Use `dig` or `nslookup` with specific server flags to test individual DNS nodes: `dig @192.168.1.10 example.com`. For Keepalived, you can stop the `keepalived` service on the primary (`systemctl stop keepalived`) and verify the backup claims the VIP with `ip addr show eth0 | grep 192.168.1.100`. For HAProxy, check the stats dashboard at `http://server:8404/stats` to see which backends are marked as up or down.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DNS Failover: Keepalived vs PowerDNS vs HAProxy Guide 2026",
  "description": "Complete guide to self-hosted DNS failover solutions. Compare Keepalived (VRRP-based VIP failover), PowerDNS (DNS-level health checks), and HAProxy (proxy-level DNS failover) with Docker Compose configs and deployment guides.",
  "datePublished": "2026-04-24",
  "dateModified": "2026-04-24",
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
