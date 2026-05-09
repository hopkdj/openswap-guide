---
title: "Self-Hosted DHCP High Availability: Kea HA vs ISC DHCP Failover vs Keepalived+dnsmasq"
date: "2026-05-09"
draft: false
tags: ["dhcp", "high-availability", "networking", "kea", "failover", "keepalived", "dnsmasq"]
---

Running DHCP without redundancy is a single point of failure. When your DHCP server goes down, new devices cannot join the network, and existing clients lose their leases at renewal time. For any production environment — from enterprise campuses to homelabs — DHCP high availability is not optional.

This guide compares three approaches to self-hosted DHCP high availability: the modern Kea DHCP high-availability framework, the classic ISC DHCP failover protocol, and the dnsmasq + Keepalived VRRP workaround. We will cover architecture, deployment, and trade-offs so you can choose the right solution for your network.

## Why DHCP High Availability Matters

DHCP is a foundational network service. Without it, devices cannot obtain IP addresses, DNS settings, or gateway information. A DHCP outage affects every device that needs to renew its lease or connect for the first time. In enterprise environments, this can mean hundreds or thousands of devices losing network access simultaneously.

High availability for DHCP is different from most other services because DHCP state — active leases, assigned IPs, and client identifiers — must be synchronized between nodes. A simple active/passive failover is not enough; both nodes need to know which addresses have been assigned to avoid conflicts.

For network infrastructure planning, see our [DHCP server comparison](../self-hosted-dhcp-servers-kea-dnsmasq-isc-dhcp-guide-2026/) which covers the baseline capabilities of each server. If you run a large network, you may also want to read about [network flow analysis tools](../2026-05-15-self-hosted-network-flow-analysis-pmacct-nfdump-fprobe-guide/) for monitoring DHCP traffic patterns.

## Kea DHCP High Availability

Kea is the modern successor to ISC DHCP, developed by the Internet Systems Consortium. It was designed from the ground up with high availability in mind, offering a built-in HA framework that supports both active/passive and active/active configurations.

### Architecture

Kea HA uses a partnership model where two (or more) Kea servers communicate directly over a dedicated control channel. Each server maintains its own lease database, and lease updates are synchronized in real-time via the HA hook library.

Key features:
- **Hot standby (active/passive)**: One server handles all DHCP requests; the standby takes over if the active node fails
- **Load balancing (active/active)**: Both servers share the DHCP load using a hash-based algorithm (typically hash = 0x80 for 50/50 split)
- **Lease synchronization**: Automatic lease sync on startup and continuous sync during operation
- **Communication recovery**: Nodes recover communication after network partitions without manual intervention
- **Multiple failover modes**: hot-standby, load-balancing, and sync-only

### Docker Compose Deployment

Kea HA requires two instances with proper HA configuration. Here is a production-ready Docker Compose setup for hot-standby mode:

```yaml
version: "3.8"
services:
  kea-primary:
    image: isc/kea:2.6.1
    container_name: kea-primary
    network_mode: host
    volumes:
      - ./kea-primary.conf:/etc/kea/kea-dhcp4.conf:ro
      - kea-primary-data:/var/lib/kea
    restart: unless-stopped
    depends_on:
      - kea-mysql

  kea-secondary:
    image: isc/kea:2.6.1
    container_name: kea-secondary
    network_mode: host
    volumes:
      - ./kea-secondary.conf:/etc/kea/kea-dhcp4.conf:ro
      - kea-secondary-data:/var/lib/kea
    restart: unless-stopped
    depends_on:
      - kea-mysql

  kea-mysql:
    image: mysql:8.0
    container_name: kea-mysql
    environment:
      MYSQL_ROOT_PASSWORD: kea-secret
      MYSQL_DATABASE: kea
      MYSQL_USER: kea
      MYSQL_PASSWORD: kea-lease
    volumes:
      - mysql-data:/var/lib/mysql
    restart: unless-stopped

volumes:
  kea-primary-data:
  kea-secondary-data:
  mysql-data:
```

The primary server configuration (`kea-primary.conf`) for hot-standby mode:

```json
{
  "Dhcp4": {
    "interfaces-config": {
      "interfaces": ["eth0"]
    },
    "lease-database": {
      "type": "mysql",
      "host": "kea-mysql",
      "name": "kea",
      "user": "kea",
      "password": "kea-lease"
    },
    "hooks-config": [
      {
        "library": "/usr/lib/x86_64-linux-gnu/kea/hooks/libdhcp_ha.so",
        "parameters": {
          "high-availability": [
            {
              "this-server-name": "kea-primary",
              "mode": "hot-standby",
              "heartbeat-delay": 10000,
              "max-response-delay": 10000,
              "max-ack-delay": 5000,
              "max-unacked-clients": 0,
              "peers": [
                {
                  "name": "kea-primary",
                  "url": "http://kea-primary:8080/",
                  "role": "primary",
                  "auto-failover": true
                },
                {
                  "name": "kea-secondary",
                  "url": "http://kea-secondary:8080/",
                  "role": "standby",
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
        "pool": ["192.168.1.100 - 192.168.1.200"],
        "option-data": [
          {
            "name": "domain-name-servers",
            "data": "192.168.1.1"
          },
          {
            "name": "routers",
            "data": "192.168.1.1"
          }
        ]
      }
    ]
  },
  "Control-agent": {
    "control-sockets": [
      {
        "socket-type": "http",
        "socket-name": "kea-primary"
      }
    ]
  }
}
```

The secondary server uses an identical configuration with `this-server-name` set to `kea-secondary` and the peer roles swapped.

### Pros and Cons

| Feature | Kea HA |
|---------|--------|
| Active/active load balancing | Yes |
| Hot standby | Yes |
| Lease synchronization | Real-time, automatic |
| MySQL/PostgreSQL backend | Yes |
| DHCPv4 + DHCPv6 | Both supported |
| Configuration complexity | Moderate (JSON-based) |
| Community support | Growing, backed by ISC |
| Last updated | May 2026 |

## ISC DHCP Failover Protocol

ISC DHCP was the dominant DHCP server for over two decades before Kea became the recommended replacement. Its failover protocol is well-understood and proven in production for years, even though ISC DHCP reached end-of-life in 2022.

### Architecture

The ISC DHCP failover protocol uses a peer-to-peer model with two states: primary and secondary. Both servers share a pool of addresses, and each server is responsible for a portion of the pool. They communicate over TCP (port 647) to synchronize lease state.

Key characteristics:
- **Primary/Secondary pairing**: Each server handles a portion of the address pool
- **State-based failover**: Servers negotiate states (normal, communications-interrupted, partner-down) based on heartbeat messages
- **Lease pool splitting**: Addresses are divided between primary and secondary using the `max-lease-misbalance` parameter (default 60/40 split)
- **Time-based synchronization**: Servers use timestamps to resolve lease conflicts

### Configuration Example

```conf
# Primary server dhcpd.conf
failover peer "dhcp-failover" {
  primary;
  address 192.168.1.10;
  port 647;
  peer address 192.168.1.11;
  peer port 647;
  max-response-delay 60;
  max-unacked-updates 10;
  mclt 3600;
  split 128;
  load balance max seconds 3;
}

subnet 192.168.1.0 netmask 255.255.255.0 {
  range 192.168.1.100 192.168.1.200;
  option domain-name-servers 192.168.1.1;
  option routers 192.168.1.1;
}
```

### Docker Deployment

```yaml
version: "3.8"
services:
  isc-dhcp-primary:
    image: networkboot/dhcpd
    container_name: isc-dhcp-primary
    network_mode: host
    volumes:
      - ./dhcpd-primary.conf:/etc/dhcp/dhcpd.conf:ro
    environment:
      DHCPD_INTERFACE: eth0
    restart: unless-stopped

  isc-dhcp-secondary:
    image: networkboot/dhcpd
    container_name: isc-dhcp-secondary
    network_mode: host
    volumes:
      - ./dhcpd-secondary.conf:/etc/dhcp/dhcpd.conf:ro
    environment:
      DHCPD_INTERFACE: eth0
    restart: unless-stopped
```

### When to Use ISC DHCP Failover

Despite being end-of-life, ISC DHCP failover is still relevant for:
- Legacy systems where migration to Kea is not yet possible
- Environments where the failover protocol is well-understood by the operations team
- Simple primary/secondary setups that do not need active/active load balancing

## dnsmasq + Keepalived VRRP Approach

When you need DHCP redundancy but want to avoid the complexity of Kea HA or ISC DHCP failover, the dnsmasq + Keepalived combination provides a simple active/passive solution using VRRP (Virtual Router Redundancy Protocol).

### Architecture

This approach uses Keepalived to manage a virtual IP address (VIP) shared between two nodes. Only the node holding the VIP runs dnsmasq's DHCP service. If the primary node fails, Keepalived transfers the VIP to the secondary node, which starts serving DHCP.

Key characteristics:
- **Active/passive only**: Only one node serves DHCP at a time
- **No lease synchronization**: The failover node does not know about existing leases, which can cause temporary conflicts
- **Simple setup**: VRRP is well-understood and easy to configure
- **Fast failover**: Typical failover time is 3-6 seconds (one VRRP advertisement interval)

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  keepalived:
    image: osixia/keepalived:2.2.8
    container_name: keepalived-dhcp
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_BROADCAST
      - NET_RAW
    volumes:
      - ./keepalived.conf:/container/service/keepalived/assets/keepalived.conf:ro
    environment:
      KEEPALIVED_INTERFACE: eth0
      KEEPALIVED_VIRTUAL_IPS: "192.168.1.5"
      KEEPALIVED_PRIORITY: "100"
    restart: unless-stopped

  dnsmasq:
    image: jpillora/dnsmasq
    container_name: dnsmasq-ha
    network_mode: host
    volumes:
      - ./dnsmasq.conf:/etc/dnsmasq.conf:ro
      - dnsmasq-leases:/var/lib/misc
    restart: unless-stopped

volumes:
  dnsmasq-leases:
```

Keepalived configuration for the primary node:

```conf
vrrp_instance DHCP_HA {
    state MASTER
    interface eth0
    virtual_router_id 51
    priority 100
    advert_int 1
    
    virtual_ipaddress {
        192.168.1.5/24
    }
    
    notify_master "/usr/bin/docker start dnsmasq-ha"
    notify_backup "/usr/bin/docker stop dnsmasq-ha"
}
```

dnsmasq configuration:

```conf
interface=eth0
dhcp-range=192.168.1.100,192.168.1.200,255.255.255.0,24h
dhcp-option=3,192.168.1.1
dhcp-option=6,192.168.1.1
dhcp-leasefile=/var/lib/misc/dnsmasq.leases
log-dhcp
```

### Comparison: All Three Approaches

| Feature | Kea HA | ISC DHCP Failover | dnsmasq + Keepalived |
|---------|--------|-------------------|---------------------|
| Architecture | Active/active or hot standby | Primary/secondary | Active/passive (VRRP) |
| Lease synchronization | Real-time, automatic | State-based, TCP sync | None (potential conflicts) |
| Failover time | < 1 second | 60 seconds (configurable) | 3-6 seconds |
| DHCPv6 support | Yes | Yes | Limited |
| Backend database | MySQL/PostgreSQL/Memfile | Text files | Text files |
| Active development | Yes (ISC) | No (EOL 2022) | Yes (both projects) |
| Complexity | Moderate | Moderate | Low |
| GitHub stars | 712 | N/A (ISC) | N/A (community) |
| Docker images | Official (isc/kea) | Community | Community |

## Choosing the Right DHCP HA Strategy

The best approach depends on your specific requirements:

**Choose Kea HA if:**
- You need active/active load balancing
- Real-time lease synchronization is critical
- You are building a new deployment or migrating from ISC DHCP
- You want the ISC-recommended path forward

**Choose ISC DHCP Failover if:**
- You have existing ISC DHCP infrastructure
- Your team is experienced with the failover protocol
- You are planning a migration but need time

**Choose dnsmasq + Keepalived if:**
- You need a simple active/passive setup
- Lease conflicts during failover are acceptable (short leases mitigate this)
- You already use Keepalived for other services
- You want the lowest complexity option

## FAQ

### What happens to existing clients during a DHCP failover?

With Kea HA, existing clients are unaffected because lease state is synchronized in real-time between nodes. With ISC DHCP failover, clients continue using their current leases and renew with whichever server is active. With dnsmasq + Keepalived, the failover node does not know about existing leases, so some clients may receive duplicate addresses until leases expire.

### Can I run DHCP HA across different subnets or geographic locations?

Kea HA supports geographically distributed deployments as long as the HA control channel has reliable connectivity (latency under 100ms recommended). ISC DHCP failover was designed for the same LAN segment. dnsmasq + Keepalived requires both nodes on the same Layer 2 segment for VRRP to function.

### How do I test DHCP failover without disrupting production?

Use a test network with the same configuration as production. For Kea HA, you can simulate a failure by stopping the primary container: `docker stop kea-primary`. Verify the secondary takes over by checking its logs (`docker logs kea-secondary`) and sending test DHCP requests from a client machine.

### What is the recommended lease time for DHCP HA deployments?

For Kea HA with real-time sync, use normal lease times (8-24 hours). For dnsmasq + Keepalived without lease sync, use shorter lease times (1-4 hours) to minimize the window where the failover node has stale lease information. ISC DHCP failover works well with standard lease times since state is synchronized.

### Can I monitor DHCP HA health?

Kea HA exposes statistics via its REST API (`http://server:8080/`), including partner state, lease counts, and failover status. ISC DHCP logs state transitions to syslog. dnsmasq logs DHCP activity, and Keepalived exposes VRRP state via SNMP or its own API.

### How many DHCP servers can participate in a Kea HA group?

Kea HA supports up to 2 servers in hot-standby mode. For load-balancing mode, you can have up to 32 servers sharing the load, though 2-4 is the typical production deployment. Each additional server requires configuration in the peers array of the HA hook.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DHCP High Availability: Kea HA vs ISC DHCP Failover vs Keepalived+dnsmasq",
  "description": "Compare three approaches to self-hosted DHCP high availability: Kea HA framework, ISC DHCP failover protocol, and dnsmasq with Keepalived VRRP. Includes Docker Compose configs and deployment guides.",
  "datePublished": "2026-05-09",
  "dateModified": "2026-05-09",
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
