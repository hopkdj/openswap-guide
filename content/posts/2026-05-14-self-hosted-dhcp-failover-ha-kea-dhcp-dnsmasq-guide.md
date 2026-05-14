---
title: "Self-Hosted DHCP Failover and High Availability: ISC Kea vs ISC DHCP vs dnsmasq"
date: "2026-05-14"
tags: ["dhcp", "high-availability", "networking", "failover", "self-hosted"]
draft: false
---

Running DHCP without redundancy is a single point of failure for your entire network. When the DHCP server goes down, new devices cannot obtain IP addresses, existing leases eventually expire, and your infrastructure grinds to a halt. This guide compares three open-source approaches to DHCP high availability — ISC Kea with its built-in HA framework, the classic ISC DHCP failover protocol, and dnsmasq paired with Keepalived VRRP — so you can choose the right strategy for your environment.

## Why DHCP High Availability Matters

DHCP is a foundational network service. Every device on your network — servers, workstations, IoT sensors, phones, and guest devices — depends on it for IP address assignment, DNS configuration, and optional parameters like NTP servers and boot filenames.

Unlike DNS, which can be cached for hours, DHCP leases have finite lifetimes. When a lease expires and the server is unreachable, the device loses its ability to renew, eventually dropping off the network entirely. In enterprise environments with hundreds or thousands of endpoints, a DHCP outage causes cascading failures: new employees cannot connect, IoT devices stop reporting, and VoIP phones fail to register.

High availability for DHCP can be achieved through several architectural patterns. The choice depends on your scale, existing infrastructure, and tolerance for complexity. Below we examine three proven approaches used in production environments worldwide.

## ISC Kea DHCP: Built-In High Availability Framework

ISC Kea is the modern successor to the legacy ISC DHCP server, designed from the ground up with enterprise requirements in mind. Its most significant advantage for HA deployments is the **native HA framework** — a purpose-built system for synchronizing state between primary and secondary servers without external orchestration.

### Architecture

Kea's HA model uses a primary-secondary (or hot-standby) topology where both servers communicate over HTTP/REST. The primary server handles all DHCP requests while the secondary stays synchronized. If the primary fails, the secondary automatically takes over within seconds.

Key components of the HA framework:

- **HA hook library**: Loaded into kea-dhcp4 or kea-dhcp6, it intercepts lease operations and replicates them to the partner server
- **Communication daemon**: HTTP-based protocol for state synchronization and health monitoring
- **Lease database backend**: Supports MySQL, PostgreSQL, and Cassandra for shared or local storage
- **Control Agent**: REST API for runtime configuration changes and monitoring

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  kea-primary:
    image: isc/kea:latest
    container_name: kea-primary
    ports:
      - "67:67/udp"
      - "8000:8000"
    volumes:
      - ./kea-primary.conf:/etc/kea/kea-dhcp4.conf:ro
      - ./kea-primary-logging.conf:/etc/kea/logging.conf:ro
    networks:
      dhcp-net:
        ipv4_address: 10.0.100.10
    depends_on:
      - mysql

  kea-secondary:
    image: isc/kea:latest
    container_name: kea-secondary
    ports:
      - "68:67/udp"
    volumes:
      - ./kea-secondary.conf:/etc/kea/kea-dhcp4.conf:ro
    networks:
      dhcp-net:
        ipv4_address: 10.0.100.11
    depends_on:
      - mysql

  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: kea-root-pass
      MYSQL_DATABASE: kea
      MYSQL_USER: kea
      MYSQL_PASSWORD: kea-pass
    volumes:
      - mysql-data:/var/lib/mysql
    networks:
      dhcp-net:
        ipv4_address: 10.0.100.20

networks:
  dhcp-net:
    driver: bridge
    ipam:
      config:
        - subnet: 10.0.100.0/24

volumes:
  mysql-data:
```

### Kea HA Configuration (kea-primary.conf)

```json
{
  "Dhcp4": {
    "interfaces-config": {
      "interfaces": ["eth0"]
    },
    "lease-database": {
      "type": "mysql",
      "name": "kea",
      "user": "kea",
      "password": "kea-pass",
      "host": "mysql",
      "persist": true
    },
    "hooks-libraries": [
      {
        "library": "/usr/lib/kea/hooks/libdhcp_ha.so",
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
                  "url": "http://10.0.100.10:8000/",
                  "role": "primary",
                  "auto-failover": true
                },
                {
                  "name": "kea-secondary",
                  "url": "http://10.0.100.11:8000/",
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
        "pools": [{ "pool": "192.168.1.100 - 192.168.1.200" }],
        "option-data": [
          { "name": "routers", "data": "192.168.1.1" },
          { "name": "domain-name-servers", "data": "192.168.1.2" }
        ]
      }
    ]
  }
}
```

Kea supports both **hot-standby** (one active, one passive) and **load-balancing** (both active, splitting the address pool) modes. In load-balancing mode, each server handles roughly half the requests and replicates lease state to its partner.

## ISC DHCP: The Classic Failover Protocol

The ISC DHCP server has been the gold standard for open-source DHCP for over two decades. Its failover protocol is a well-tested, RFC-documented approach that remains in widespread use despite ISC officially deprecating the project in favor of Kea.

### Architecture

The ISC DHCP failover protocol operates at the protocol level, not as an add-on hook. Two servers establish a TCP connection and synchronize their lease databases through a continuous exchange of update messages. The protocol supports:

- **Primary-secondary topology**: One server owns each address, the partner has backup copies
- **Split-scope mode**: Address ranges are divided between servers with no overlap
- **Load-balancing mode**: Both servers respond to requests with configurable load ratios

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  isc-dhcp-primary:
    image: networkboot/dhcpd:latest
    container_name: isc-dhcp-primary
    network_mode: "host"
    cap_add:
      - NET_ADMIN
    environment:
      - DHCP_INTERFACE=eth0
    volumes:
      - ./dhcpd-primary.conf:/etc/dhcp/dhcpd.conf:ro
      - dhcp-leases-primary:/var/lib/dhcp

  isc-dhcp-secondary:
    image: networkboot/dhcpd:latest
    container_name: isc-dhcp-secondary
    network_mode: "host"
    cap_add:
      - NET_ADMIN
    environment:
      - DHCP_INTERFACE=eth0
    volumes:
      - ./dhcpd-secondary.conf:/etc/dhcp/dhcpd.conf:ro
      - dhcp-leases-secondary:/var/lib/dhcp

volumes:
  dhcp-leases-primary:
  dhcp-leases-secondary:
```

### Failover Configuration (dhcpd.conf excerpt)

```
# Primary server
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
    option routers 192.168.1.1;
    option domain-name-servers 192.168.1.2;
}
```

The `split 128` directive divides the address pool evenly between the two servers. The `mclt` (Maximum Client Lead Time) prevents conflicts during network partitions by limiting how long a server can extend leases before syncing.

## dnsmasq + Keepalived: Lightweight HA

For small to medium networks that do not need the complexity of full lease database synchronization, dnsmasq combined with Keepalived VRRP provides a simple, effective HA solution. This approach uses a virtual IP (VIP) that floats between two physical servers — whichever server holds the VIP responds to DHCP requests.

### Architecture

Keepalived uses the Virtual Router Redundancy Protocol (VRRP) to manage VIP assignment. The master server owns the VIP and responds to DHCP. If the master fails, VRRP detects the loss and promotes the backup to master within 2-3 seconds. The dnsmasq instance on the backup already has the same configuration and static leases, so it seamlessly takes over.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  dnsmasq-master:
    image: jpillora/dnsmasq:latest
    container_name: dnsmasq-master
    network_mode: "host"
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./dnsmasq.conf:/etc/dnsmasq.conf:ro
      - ./dnsmasq.hosts:/etc/dnsmasq.hosts:ro
    restart: unless-stopped

  keepalived:
    image: osixia/keepalived:latest
    container_name: keepalived
    network_mode: "host"
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./keepalived.conf:/container/service/keepalived/assets/keepalived.conf:ro
    environment:
      - KEEPALIVED_INTERFACE=eth0
    restart: unless-stopped
```

### Keepalived Configuration

```
vrrp_instance DHCP_VIP {
    state MASTER
    interface eth0
    virtual_router_id 51
    priority 150
    advert_int 1
    unicast_src_ip 192.168.1.10
    unicast_peer {
        192.168.1.11
    }
    authentication {
        auth_type PASS
        auth_pass vrrp-secret-2026
    }
    virtual_ipaddress {
        192.168.1.1/24 dev eth0 label eth0:dhcp-vip
    }
    notify_master "/etc/keepalived/notify-master.sh"
    notify_backup "/etc/keepalived/notify-backup.sh"
}
```

### dnsmasq Configuration

```
# Listen only on the VIP
bind-interfaces
interface=eth0
except-interface=lo

# DHCP settings
dhcp-range=192.168.1.100,192.168.1.200,255.255.255.0,24h
dhcp-option=option:router,192.168.1.1
dhcp-option=option:dns-server,192.168.1.2

# Static leases (identical on both servers)
dhcp-host=aa:bb:cc:dd:ee:01,192.168.1.50,server01
dhcp-host=aa:bb:cc:dd:ee:02,192.168.1.51,server02
```

The key limitation of this approach is that **active DHCP leases are not synchronized** between servers. If a failover occurs mid-lease, the backup server does not know which addresses are currently in use. For networks with long lease times (24 hours), this is rarely a problem because the backup will not reassign addresses that were recently active. For short lease times, consider the ISC Kea or ISC DHCP approaches instead.

## Comparison Table

| Feature | ISC Kea HA | ISC DHCP Failover | dnsmasq + Keepalived |
|---------|-----------|-------------------|---------------------|
| **Active development** | Yes (current) | No (deprecated) | Yes (upstream mirror) |
| **Stars on GitHub** | 714 | 203 | 378 |
| **Lease sync** | Real-time (HTTP/REST) | Real-time (TCP protocol) | No sync (identical config) |
| **Failover mode** | Hot-standby + load-balance | Primary-secondary + split-scope | VRRP VIP float |
| **Failover time** | < 5 seconds | < 10 seconds | 2-3 seconds |
| **Database backend** | MySQL, PostgreSQL, Cassandra | Flat file | Flat file |
| **IPv6 support** | Yes (native) | Yes (native) | Yes (native) |
| **REST API** | Yes (Control Agent) | No | No |
| **Web UI** | Stork dashboard | Glass ISC DHCP | None (CLI only) |
| **Complexity** | High (hooks, DB, HTTP) | Medium (TCP protocol) | Low (VRRP + single config) |
| **Best for** | Enterprise, 1000+ clients | Legacy environments | Small/medium, < 500 clients |

## Choosing the Right DHCP HA Strategy

For **enterprise deployments** with hundreds or thousands of endpoints, ISC Kea's built-in HA framework is the strongest choice. It offers real-time lease synchronization, a REST API for monitoring and automation, and active development with a modern codebase. The Stork dashboard provides centralized management and visibility into both servers' health.

For **existing ISC DHCP installations** that need HA without migration, the classic failover protocol continues to work reliably. However, note that ISC has declared the project in maintenance mode — no new features are being added. Plan a migration to Kea when practical.

For **small offices, homelabs, or edge deployments**, dnsmasq with Keepalived offers the simplest path to redundancy. There is no lease database to maintain, no hook libraries to configure, and the VRRP failover is well-understood and battle-tested. The tradeoff is the lack of lease synchronization during failover, which is acceptable for most small networks with standard 24-hour lease times.

## Security Best Practices for DHCP HA

Regardless of which HA approach you choose, follow these security practices:

- **Restrict HA communication** to a dedicated management VLAN — the Kea HTTP control channel and ISC DHCP TCP failover connection should never traverse untrusted networks
- **Use TLS for Kea** — the HA hook supports HTTPS for peer communication; enable it in production
- **Authenticate Keepalived** — use strong VRRP passwords and consider switching to AH (Authentication Header) for VRRPv3
- **Monitor lease consistency** — run periodic checks comparing lease counts between primary and secondary servers
- **Test failover regularly** — schedule monthly failover drills to verify automatic switchover and switchover-back


## Why Self-Host Your DHCP Infrastructure?

DHCP is the foundation of network connectivity. Every device that joins your network — from servers and workstations to IoT sensors and IP phones — relies on DHCP for IP address assignment and network configuration. When you outsource DHCP to a cloud provider or rely on your ISP's router, you lose visibility, control, and the ability to implement custom policies.

Self-hosting DHCP gives you complete ownership of your address allocation strategy. You can define custom options for PXE boot, set per-subnet DNS servers, implement MAC-based static reservations, and enforce lease duration policies that match your operational needs. In regulated environments, self-hosted DHCP ensures that network configuration data never leaves your data center.

High availability is equally critical. A DHCP outage means new devices cannot connect and existing devices eventually lose network access as leases expire. The three approaches covered in this guide — ISC Kea with native HA, ISC DHCP with the classic failover protocol, and dnsmasq with Keepalived VRRP — provide different tradeoffs between complexity, synchronization guarantees, and operational overhead.

For self-hosted DNS infrastructure, see our [DNS firewall comparison](../2026-04-21-self-hosted-dns-firewall-rpz-unbound-powerdns-bind9-knot-guide-2026/) and [PowerDNS vs BIND authoritative DNS guide](../2026-04-18-powerdns-vs-bind9-vs-nsd-vs-knot-self-hosted-authoritative-dns-2026/). For high-availability networking, our [DNS anycast with Keepalived guide](../2026-04-22-bird-vs-frrouting-vs-keepalived-self-hosted-dns-anycast-guide-2026/) covers complementary redundancy patterns.

## FAQ

### What happens to active DHCP leases during a failover event?

With ISC Kea's hot-standby mode, leases are replicated in real-time to the secondary server. When failover occurs, the secondary already knows about every active lease and can immediately honor renewals. With ISC DHCP's failover protocol, lease state is continuously synchronized over the TCP connection, providing similar guarantees. With dnsmasq + Keepalived, leases are not synchronized — the backup server will not know about recent dynamic assignments, though static leases in the shared config file are preserved.

### Can I run DHCP HA across different physical sites?

Yes, but with caveats. ISC Kea supports geographic separation if the network latency between sites is under 100ms. The HTTP-based heartbeat mechanism will tolerate moderate delays. ISC DHCP's failover protocol is more sensitive to latency and may produce split-brain scenarios if the link is unreliable. dnsmasq + Keepalived requires layer-2 connectivity for VRRP, making it unsuitable for WAN-separated sites.

### How do I monitor DHCP HA health?

ISC Kea provides a Control Agent REST API at port 8000 that exposes lease statistics, server state, and HA peer status. The Stork dashboard visualizes this data in a web interface. For ISC DHCP, you can parse the lease file (`/var/lib/dhcp/dhcpd.leases`) and monitor the failover TCP connection with netstat. For dnsmasq + Keepalived, use `keepalived --dump-conf` and VRRP state monitoring scripts.

### Is ISC DHCP still safe to use if it is deprecated?

ISC DHCP is in maintenance mode — it receives security patches but no new features. The failover protocol has been stable and production-tested for over 15 years. If your current installation works and is properly firewalled, it remains a viable option. However, for new deployments, ISC Kea is the recommended path forward.

### What is the difference between hot-standby and load-balancing modes in Kea?

In **hot-standby** mode, only the primary server responds to DHCP requests. The secondary listens to the network but does not issue addresses until the primary fails. In **load-balancing** mode, both servers respond to requests, with the address pool divided between them. If one server fails, the surviving server takes over the entire pool. Load-balancing provides better resource utilization but requires more careful configuration.

### Can I migrate from ISC DHCP to Kea without downtime?

Yes. ISC provides a lease file conversion tool that reads the ISC DHCP `dhcpd.leases` file and imports leases into Kea's database. You can run Kea in parallel with your existing ISC DHCP server, import the leases, verify consistency, then switch over. For the most seamless migration, configure Kea as a secondary failover partner first, then promote it to primary.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DHCP Failover and High Availability: ISC Kea vs ISC DHCP vs dnsmasq",
  "description": "Self-hosted guide comparing open-source tools for infrastructure management and deployment.",
  "datePublished": "2026-05-14",
  "dateModified": "2026-05-14",
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
