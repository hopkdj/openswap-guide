---
title: "Self-Hosted DHCP High Availability: ISC DHCP Failover vs Kea HA vs Keepalived + dnsmasq"
date: "2026-05-14"
tags: ["dhcp", "high-availability", "network-infrastructure", "failover", "self-hosted"]
draft: false
---

Running DHCP as a single point of failure in your network is a recipe for disaster. When your sole DHCP server goes down, new devices cannot obtain IP addresses, existing leases eventually expire, and your entire network grinds to a halt. Self-hosted DHCP high availability ensures your network keeps handing out addresses even when hardware fails, services crash, or maintenance windows arrive.

This guide compares three proven approaches to DHCP high availability: the classic ISC DHCP failover protocol, the modern Kea DHCP HA architecture, and the lightweight Keepalived + dnsmasq combination. Each has different tradeoffs in complexity, scalability, and operational overhead.

## Understanding DHCP High Availability

DHCP (Dynamic Host Configuration Protocol) is stateful by nature — the server must track which IP addresses are assigned to which clients, when leases expire, and what options (DNS servers, gateways, NTP servers) were handed out. This statefulness makes HA challenging: two DHCP servers must stay synchronized so they never hand out the same IP to two different clients.

There are three broad approaches to DHCP HA:

1. **Active-Active Failover** — Both servers actively respond to DHCP requests and share a synchronized lease database.
2. **Active-Passive with Virtual IP** — A primary server responds to all requests; a standby takes over the virtual IP if the primary fails.
3. **Split-Scope** — Each server is responsible for a different range of the address pool, with no synchronization needed.

The solutions we cover span all three models, giving you options whether you need millisecond failover or simple redundancy.

## ISC DHCP Failover Protocol

ISC DHCP (the `dhcpd` daemon) has been the gold standard for self-hosted DHCP for over two decades. Its built-in failover protocol provides true active-active high availability with lease synchronization between primary and secondary servers.

### How It Works

The ISC DHCP failover protocol establishes a TCP connection between two DHCP servers. They communicate lease state changes in real-time, allowing both servers to respond to client requests. If one server goes offline, the other continues serving from the synchronized lease database. When the failed server returns, it resynchronizes automatically.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  dhcp-primary:
    image: networkboot/dhcpd:latest
    container_name: dhcp-primary
    network_mode: "host"
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./dhcpd-primary.conf:/etc/dhcp/dhcpd.conf:ro
      - ./dhcpd.leases:/var/lib/dhcp/dhcpd.leases
      - ./dhcp-failover.leases:/var/lib/dhcp/dhcpd-failover.leases
    restart: unless-stopped
    command: "-d -cf /etc/dhcp/dhcpd.conf eth0"

  dhcp-secondary:
    image: networkboot/dhcpd:latest
    container_name: dhcp-secondary
    network_mode: "host"
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./dhcpd-secondary.conf:/etc/dhcp/dhcpd.conf:ro
      - ./dhcpd.leases:/var/lib/dhcp/dhcpd.leases
      - ./dhcp-failover.leases:/var/lib/dhcp/dhcpd-failover.leases
    restart: unless-stopped
    command: "-d -cf /etc/dhcp/dhcpd.conf eth0"
```

### Primary Server Configuration (`dhcpd-primary.conf`)

```
failover peer "dhcp-failover" {
    primary;
    address 192.168.1.10;
    port 647;
    peer address 192.168.1.11;
    peer port 647;
    max-response-delay 30;
    max-unacked-updates 10;
    mclt 3600;
    split 128;
    load balance max seconds 3;
}

subnet 192.168.1.0 netmask 255.255.255.0 {
    pool {
        failover peer "dhcp-failover";
        range 192.168.1.100 192.168.1.200;
    }
    option domain-name-servers 192.168.1.1, 192.168.1.2;
    option routers 192.168.1.1;
    option domain-name "home.lan";
    default-lease-time 3600;
    max-lease-time 7200;
}
```

### Secondary Server Configuration (`dhcpd-secondary.conf`)

```
failover peer "dhcp-failover" {
    secondary;
    address 192.168.1.11;
    port 647;
    peer address 192.168.1.10;
    peer port 647;
    max-response-delay 30;
    max-unacked-updates 10;
}

subnet 192.168.1.0 netmask 255.255.255.0 {
    pool {
        failover peer "dhcp-failover";
        range 192.168.1.100 192.168.1.200;
    }
    option domain-name-servers 192.168.1.1, 192.168.1.2;
    option routers 192.168.1.1;
    option domain-name "home.lan";
    default-lease-time 3600;
    max-lease-time 7200;
}
```

### Pros and Cons

**Pros:**
- True active-active with real-time lease synchronization
- The `split` parameter controls load distribution between servers
- Well-tested protocol with over 15 years of production use
- Automatic resynchronization when a failed server returns

**Cons:**
- ISC DHCP is in maintenance mode; no new features are being added
- Maximum of two servers per failover pair
- The failover protocol uses a proprietary binary format
- Configuration can be complex for beginners

## Kea DHCP High Availability

Kea is the modern successor to ISC DHCP, developed by the same organization (ISC). It features a modular architecture, REST API, and a built-in high availability hook that supports both load-balancing and hot-standby modes.

### How It Works

Kea HA uses a hook library (`libdhcp_ha.so`) that coordinates multiple Kea instances via HTTP REST API. Each server periodically sends heartbeat messages to its peers. If a peer stops responding, the remaining server takes over its workload. Unlike ISC DHCP's proprietary failover protocol, Kea HA communicates over standard HTTPS.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  kea-dhcp1:
    image: isc/kea:2.6.1
    container_name: kea-dhcp1
    network_mode: "host"
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./kea-dhcp1.conf:/etc/kea/kea-dhcp4.conf:ro
      - ./kea-leases1.csv:/var/lib/kea/kea-leases4.csv
    restart: unless-stopped
    command: ["-d", "-c", "/etc/kea/kea-dhcp4.conf"]

  kea-dhcp2:
    image: isc/kea:2.6.1
    container_name: kea-dhcp2
    network_mode: "host"
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./kea-dhcp2.conf:/etc/kea/kea-dhcp4.conf:ro
      - ./kea-leases2.csv:/var/lib/kea/kea-leases4.csv
    restart: unless-stopped
    command: ["-d", "-c", "/etc/kea/kea-dhcp4.conf"]
```

### Kea HA Configuration (`kea-dhcp1.conf`)

```json
{
    "Dhcp4": {
        "interfaces-config": {
            "interfaces": ["eth0"]
        },
        "lease-database": {
            "type": "memfile",
            "persist": true,
            "name": "/var/lib/kea/kea-leases4.csv"
        },
        "hooks-libraries": [
            {
                "library": "/usr/lib/x86_64-linux-gnu/kea/hooks/libdhcp_ha.so",
                "parameters": {
                    "high-availability": [
                        {
                            "this-server-name": "kea1",
                            "mode": "load-balancing",
                            "heartbeat-delay": 10000,
                            "max-unacked-clients": 10,
                            "max-response-delay": 10000,
                            "peers": [
                                {
                                    "name": "kea1",
                                    "url": "http://192.168.1.10:8000/",
                                    "role": "primary",
                                    "auto-failover": true
                                },
                                {
                                    "name": "kea2",
                                    "url": "http://192.168.1.11:8000/",
                                    "role": "secondary",
                                    "auto-failover": true
                                }
                            ]
                        }
                    ]
                }
            }
        ],
        "subnet4": [
            {
                "subnet": "192.168.1.0/24",
                "pools": [{ "pool": "192.168.1.100 - 192.168.1.200" }],
                "option-data": [
                    { "name": "routers", "data": "192.168.1.1" },
                    { "name": "domain-name-servers", "data": "192.168.1.1, 192.168.1.2" }
                ]
            }
        ]
    },
    "Control-agent": {
        "control-sockets": [
            {
                "socket-type": "http",
                "socket-name": "192.168.1.10",
                "port": 8000
            }
        ]
    }
}
```

### Pros and Cons

**Pros:**
- Actively developed with regular releases (latest: 2.6.x series)
- REST API enables integration with orchestration tools
- Supports both load-balancing and hot-standby modes
- Can use MySQL or PostgreSQL backends for lease storage
- Native IPv6 support with HA

**Cons:**
- More resource-intensive than ISC DHCP
- Configuration is JSON-based (not the familiar ISC format)
- Requires the Control-agent component to be running
- HA hook library is only available in Kea 2.0+

## Keepalived + dnsmasq (Active-Passive)

For smaller networks where simplicity matters more than active-active load distribution, combining dnsmasq with Keepalived provides reliable active-passive DHCP HA using a virtual IP address.

### How It Works

Keepalived uses VRRP (Virtual Router Redundancy Protocol) to manage a floating virtual IP between two servers. The primary server holds the VIP and runs dnsmasq. If the primary fails, Keepalived on the secondary detects the VRRP timeout, claims the VIP, and starts its own dnsmasq instance.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  dnsmasq-ha:
    image: jpillora/dnsmasq:latest
    container_name: dnsmasq-ha
    network_mode: "host"
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./dnsmasq.conf:/etc/dnsmasq.conf:ro
      - ./dnsmasq.leases:/var/lib/misc/dnsmasq.leases
    restart: unless-stopped

  keepalived:
    image: osixia/keepalived:2.2.8
    container_name: keepalived
    network_mode: "host"
    cap_add:
      - NET_ADMIN
      - NET_BROADCAST
      - NET_RAW
    environment:
      - KEEPALIVED_INTERFACE=eth0
      - KEEPALIVED_VIRTUAL_IPS=192.168.1.250
      - KEEPALIVED_PRIORITY=100
      - KEEPALIVED_UNICAST_PEERS=192.168.1.11
    volumes:
      - ./keepalived-check.sh:/etc/keepalived/check_script.sh:ro
    restart: unless-stopped
```

### Keepalived Health Check Script

```bash
#!/bin/bash
# /etc/keepalived/check_script.sh
# Returns 0 if dnsmasq is running, 1 if not
if pgrep -x dnsmasq > /dev/null 2>&1; then
    exit 0
else
    exit 1
fi
```

### dnsmasq Configuration

```
# Listen only on the virtual IP
bind-interfaces
interface=eth0

# DHCP configuration
dhcp-range=192.168.1.100,192.168.1.200,255.255.255.0,3600
dhcp-option=option:router,192.168.1.1
dhcp-option=option:dns-server,192.168.1.1,192.168.1.2
dhcp-option=option:domain-name,home.lan

# Lease file
dhcp-leasefile=/var/lib/misc/dnsmasq.leases
```

### Pros and Cons

**Pros:**
- Extremely simple to deploy and understand
- dnsmasq also provides DNS, TFTP (for PXE boot), and NTP
- VRRP is a standard protocol supported by many vendors
- Can scale to more than 2 servers with VRRP priorities
- Low resource footprint

**Cons:**
- Active-passive only — the standby server is idle
- Lease database is NOT synchronized between servers (clients may get different IPs after failover)
- Failover takes 3-5 seconds (VRRP advertisement timeout)
- Not suitable for large networks with thousands of leases

## Comparison Table

| Feature | ISC DHCP Failover | Kea HA | Keepalived + dnsmasq |
|---------|-------------------|--------|----------------------|
| **HA Mode** | Active-Active | Active-Active or Hot-Standby | Active-Passive |
| **Max Servers** | 2 | Unlimited | Unlimited |
| **Lease Sync** | Real-time (proprietary) | Real-time (HTTP REST) | None |
| **Failover Time** | < 1 second | < 3 seconds | 3-5 seconds |
| **Configuration** | ISC config format | JSON | dnsmasq config + VRRP |
| **IPv6 Support** | Yes | Yes (with HA) | Yes |
| **Database Backend** | File-based | File, MySQL, PostgreSQL | File-based |
| **REST API** | No | Yes (Control-agent) | No |
| **Active Development** | Maintenance mode only | Yes (ISC) | Yes (community) |
| **Docker Support** | community images | Official ISC images | Community images |
| **Stars** | Legacy (no GitHub) | 714+ | 4,000+ (dnsmasq) |
| **Best For** | Enterprise networks | Modern deployments | Small/medium networks |

## Why Self-Host DHCP High Availability?

Running your own DHCP infrastructure gives you complete control over IP address assignment, option delivery, and network policies. Unlike cloud-managed DHCP services, self-hosted solutions keep your network operational even during internet outages. For organizations with strict data sovereignty requirements, keeping DHCP on-premises ensures no lease data leaves your network perimeter.

When combined with self-hosted [DNS resolvers](../2026-04-29-self-hosted-dns-resolvers-unbound-dnsmasq-bind-coredns-guide-2026/) and [overlay networks](../self-hosted-overlay-networks-zerotier-nebula-netmaker-guide-2026/), you can build a fully autonomous network stack that operates independently of any external provider. Adding [network traffic analysis](../self-hosted-network-traffic-analysis-zeek-arkime-ntopng-guide-2026/) on top gives you full visibility into how your DHCP-assigned addresses are being used.

### Choosing the Right DHCP HA Solution

For most organizations, **Kea HA** is the recommended choice. It is actively developed by ISC, supports both active-active and hot-standby modes, and provides a REST API for automation. The JSON-based configuration may feel unfamiliar to ISC DHCP veterans, but the benefits — modern architecture, database backends, and ongoing development — far outweigh the learning curve.

**ISC DHCP Failover** remains a solid choice for existing deployments that already run ISC DHCP. If your current setup works, there is no urgent need to migrate — ISC DHCP will continue to receive security fixes even though no new features are planned.

**Keepalived + dnsmasq** is ideal for home labs, small offices, and situations where simplicity trumps feature richness. The active-passive model means the standby server is idle, but the operational simplicity makes it worth the tradeoff for networks under 200 clients.


<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DHCP High Availability: ISC DHCP Failover vs Kea HA vs Keepalived + dnsmasq",
  "description": "Compare three approaches to self-hosted DHCP high availability for reliable IP address assignment.",
  "datePublished": "2026-05-14",
  "dateModified": "2026-05-14",
  "author": {"@type": "Organization", "name": "OpenSwap Guide"},
  "publisher": {"@type": "Organization", "name": "OpenSwap Guide", "logo": {"@type": "ImageObject", "url": "https://hopkdj.github.io/openswap-guide/logo.png"}}
}
</script>

## FAQ

### What is the difference between DHCP failover and DHCP high availability?

DHCP failover specifically refers to the ISC DHCP failover protocol — a proprietary binary protocol that synchronizes lease state between two servers. DHCP high availability is a broader term that encompasses any method of ensuring DHCP service continuity, including Kea HA, Keepalived/VRRP, split-scope configurations, and load balancer-based approaches.

### Can I run three or more DHCP servers in a failover group?

ISC DHCP failover is limited to exactly two servers. Kea HA supports unlimited peers — you can configure three or more Kea instances in a load-balancing or hot-standby arrangement. Keepalived with VRRP also supports unlimited servers, each with a different priority level.

### Do I need to synchronize lease databases between DHCP servers?

For active-active HA, yes — both servers must know which IPs are assigned to avoid conflicts. ISC DHCP and Kea HA handle this automatically. For active-passive setups (Keepalived + dnsmasq), synchronization is not needed because only one server is active at a time, but clients may receive different IPs after failover.

### What happens when a failed DHCP server comes back online?

With ISC DHCP failover, the recovering server connects to its peer and requests a lease state update. The MCLT (Maximum Client Lead Time) parameter determines how many leases the peer will have handed out during the outage. With Kea HA, the recovering server contacts its peers via the REST API and resynchronizes its lease database. With Keepalived + dnsmasq, the recovering server simply becomes the standby — its old lease file is stale but harmless since it is not actively serving.

### Can Kea HA use MySQL or PostgreSQL for lease storage?

Yes. Kea supports multiple lease database backends: memfile (CSV file), MySQL, PostgreSQL, and Cassandra. When using a shared database backend, lease state is inherently synchronized between servers, simplifying HA configuration.

### Is dnsmasq suitable for production DHCP HA?

For small to medium networks (under 200 clients), yes. dnsmasq is widely deployed and reliable. However, the lack of lease synchronization between active and passive servers means clients may receive different IP addresses after failover, which can be problematic for services that depend on stable IP assignments.

