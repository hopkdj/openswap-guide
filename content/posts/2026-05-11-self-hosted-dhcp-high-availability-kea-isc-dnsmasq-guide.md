---
title: "Self-Hosted DHCP High Availability: ISC Kea vs ISC DHCP Failover vs Dnsmasq"
date: "2026-05-11"
tags: ["dhcp", "networking", "high-availability", "infrastructure", "self-hosted"]
draft: false
---

Dynamic Host Configuration Protocol (DHCP) is foundational network infrastructure — without it, devices cannot obtain IP addresses, DNS settings, or network configuration. A single DHCP server represents a critical single point of failure. This guide compares three approaches to DHCP high availability: ISC Kea DHCP's built-in HA framework, the traditional ISC DHCP failover protocol, and Dnsmasq paired with Keepalived for VRRP-based failover.

## Why DHCP High Availability Matters

When your DHCP server goes down, new devices cannot join the network, existing devices may lose their leases at renewal time, and IP address conflicts can arise when devices fall back to APIPA (169.254.x.x) addressing. For organizations running VoIP phones, IoT sensor networks, or containerized workloads, DHCP downtime directly translates to service outages.

| Feature | ISC Kea DHCP HA | ISC DHCP Failover | Dnsmasq + Keepalived |
|---------|----------------|-------------------|---------------------|
| **Architecture** | Active-passive or load-balanced | Active-passive failover | Active-passive VRRP |
| **Lease Synchronization** | Real-time via REST API | Real-time via TCP connection | No sync (split-scope or hot standby) |
| **Automatic Failover** | Yes (configurable timeout) | Yes (automatic) | Yes (VRRP priority-based) |
| **Load Balancing** | Yes (multi-master mode) | No (primary/secondary) | No (VRRP selects one active) |
| **IPv6 Support** | Full DHCPv6 | Limited (separate process) | Full DHCPv6 |
| **Configuration Database** | MySQL, PostgreSQL, Cassandra | Flat files | Flat file (dnsmasq.leases) |
| **REST API** | Yes (built-in) | No | No |
| **Dynamic DNS Updates** | Yes (via hook) | Yes (built-in) | Yes (built-in) |
| **Docker Deployment** | Official images available | Community images | Official images |
| **Last Major Update** | 2026 (active) | 2022 (maintenance mode) | 2026 (active) |

## ISC Kea DHCP: Modern High Availability

ISC Kea is the next-generation DHCP server from the Internet Systems Consortium, designed from the ground up with HA support. Kea's HA framework uses a pair of servers communicating via REST API to synchronize lease state and coordinate failover.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  kea-primary:
    image: ghcr.io/isc-projects/kea:2.6.1
    container_name: kea-primary
    ports:
      - "67:67/udp"
      - "8080:8080"
    volumes:
      - ./kea-primary/kea-dhcp4.conf:/etc/kea/kea-dhcp4.conf:ro
      - ./kea-primary/kea-ctrl-agent.conf:/etc/kea/kea-ctrl-agent.conf:ro
      - kea-leases:/var/lib/kea
    restart: unless-stopped
    depends_on:
      - kea-db

  kea-secondary:
    image: ghcr.io/isc-projects/kea:2.6.1
    container_name: kea-secondary
    ports:
      - "67:67/udp"
      - "8081:8080"
    volumes:
      - ./kea-secondary/kea-dhcp4.conf:/etc/kea/kea-dhcp4.conf:ro
      - ./kea-secondary/kea-ctrl-agent.conf:/etc/kea/kea-ctrl-agent.conf:ro
      - kea-leases:/var/lib/kea
    restart: unless-stopped
    depends_on:
      - kea-db

  kea-db:
    image: postgres:17-alpine
    container_name: kea-db
    environment:
      POSTGRES_DB: kea
      POSTGRES_USER: kea
      POSTGRES_PASSWORD: kea-secret
    volumes:
      - kea-db-data:/var/lib/postgresql/data

volumes:
  kea-leases:
  kea-db-data:
```

### Kea HA Configuration

```json
{
  "Dhcp4": {
    "interfaces-config": {
      "interfaces": ["eth0"]
    },
    "lease-database": {
      "type": "postgresql",
      "name": "kea",
      "user": "kea",
      "password": "kea-secret",
      "host": "kea-db"
    },
    "hooks-libraries": [
      {
        "library": "/usr/lib/kea/hooks/libdhcp_ha.so",
        "parameters": {
          "high-availability": [
            {
              "this-server-name": "kea-primary",
              "mode": "load-balancing",
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
                  "url": "http://kea-secondary:8081/",
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
        "pools": [{ "pool": "192.168.1.100 - 192.168.1.200" }]
      }
    ]
  }
}
```

Kea supports two HA modes: **hot-standby** (active-passive) and **load-balancing** (both servers actively lease addresses). The load-balancing mode distributes clients between servers while maintaining synchronized lease state, providing both redundancy and capacity scaling.

## ISC DHCP Failover: The Traditional Approach

The ISC DHCP server (versions 3 and 4) implements a well-established failover protocol that has been the industry standard for over two decades. It uses a direct TCP connection between primary and secondary servers to synchronize lease state in real time.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  isc-dhcp-primary:
    image: networkboot/dhcpd:latest
    container_name: isc-dhcp-primary
    network_mode: host
    volumes:
      - ./dhcpd-primary.conf:/etc/dhcp/dhcpd.conf:ro
      - isc-dhcp-leases:/var/lib/dhcp
    environment:
      INTERFACE: eth0
    restart: unless-stopped

  isc-dhcp-secondary:
    image: networkboot/dhcpd:latest
    container_name: isc-dhcp-secondary
    network_mode: host
    volumes:
      - ./dhcpd-secondary.conf:/etc/dhcp/dhcpd.conf:ro
      - isc-dhcp-leases:/var/lib/dhcp
    environment:
      INTERFACE: eth0
    restart: unless-stopped

volumes:
  isc-dhcp-leases:
```

### Failover Configuration

```
# Primary server configuration
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
  pool {
    failover peer "dhcp-failover";
    range 192.168.1.100 192.168.1.200;
  }
}
```

```
# Secondary server configuration
failover peer "dhcp-failover" {
  secondary;
  address 192.168.1.11;
  port 647;
  peer address 192.168.1.10;
  peer port 647;
  max-response-delay 60;
  max-unacked-updates 10;
}

subnet 192.168.1.0 netmask 255.255.255.0 {
  pool {
    failover peer "dhcp-failover";
    range 192.168.1.100 192.168.1.200;
  }
}
```

ISC DHCP has entered maintenance mode — ISC officially recommends migrating to Kea for new deployments. However, the failover protocol remains stable and reliable for existing installations.

## Dnsmasq + Keepalived: Lightweight VRRP Failover

Dnsmasq is a lightweight DNS and DHCP server widely used in home routers and small deployments. Paired with Keepalived's VRRP implementation, it provides simple active-passive failover without lease synchronization between servers.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  dnsmasq-primary:
    image: jpillora/dnsmasq:latest
    container_name: dnsmasq-primary
    network_mode: host
    cap_add:
      - NET_ADMIN
    volumes:
      - ./dnsmasq-primary.conf:/etc/dnsmasq.conf:ro
      - ./leases-primary:/etc/dnsmasq.leases
    restart: unless-stopped

  dnsmasq-secondary:
    image: jpillora/dnsmasq:latest
    container_name: dnsmasq-secondary
    network_mode: host
    cap_add:
      - NET_ADMIN
    volumes:
      - ./dnsmasq-secondary.conf:/etc/dnsmasq.conf:ro
      - ./leases-secondary:/etc/dnsmasq.leases
    restart: unless-stopped

  keepalived:
    image: osixia/keepalived:latest
    container_name: keepalived
    network_mode: host
    cap_add:
      - NET_ADMIN
    environment:
      KEEPALIVED_INTERFACE: eth0
      KEEPALIVED_VIRTUAL_IPS: "192.168.1.1"
      KEEPALIVED_PRIORITY: "100"
    volumes:
      - ./keepalived.conf:/container/service/keepalived/assets/keepalived.conf:ro
    restart: unless-stopped
```

### Dnsmasq Configuration

```
# dnsmasq-primary.conf (split-scope approach)
interface=eth0
dhcp-range=192.168.1.100,192.168.1.150,255.255.255.0,24h
dhcp-range=192.168.1.151,192.168.1.200,255.255.255.0,24h,backup
dhcp-authoritative
log-dhcp
```

### Keepalived Configuration

```
vrrp_instance DHCP_HA {
    state MASTER
    interface eth0
    virtual_router_id 51
    priority 100
    advert_int 1
    authentication {
        auth_type PASS
        auth_pass keepalived-secret
    }
    virtual_ipaddress {
        192.168.1.1/24
    }
    notify_master "/usr/bin/systemctl restart dnsmasq"
    notify_backup "/usr/bin/systemctl stop dnsmasq"
}
```

This approach uses split-scope DHCP: each server manages a different range of addresses. When the primary fails, Keepalived transfers the virtual IP to the secondary, which then serves its own address range. There is no lease synchronization, so the secondary will not know about leases issued by the primary — but it will honor existing leases when clients renew.

## Choosing the Right DHCP HA Solution

**Use ISC Kea DHCP HA when:**
- You need modern, actively maintained DHCP with REST API management
- You want load-balancing mode for active-active capacity
- You require PostgreSQL or MySQL backend for lease storage
- You need DHCPv6 with full HA support

**Use ISC DHCP Failover when:**
- You have an existing ISC DHCP deployment that works reliably
- You need a proven, well-understood failover protocol
- You don't require the features of Kea (REST API, database backend)

**Use Dnsmasq + Keepalived when:**
- You need a lightweight solution for small networks
- You already run Dnsmasq for DNS and want integrated DHCP
- Split-scope addresses your availability requirements
- You want minimal resource consumption on edge devices

## Why Self-Host DHCP High Availability?

Running your own DHCP infrastructure with built-in redundancy gives you complete control over address assignment, lease policies, and network access. Cloud-managed DHCP services introduce dependencies on external infrastructure and can become unavailable during network partitions — precisely when you need DHCP the most.

**Network sovereignty**: DHCP defines how devices connect to your network. Self-hosting means you control lease durations, reserved addresses, DHCP options, and access policies without vendor-imposed limitations. For enterprise networks with specific VLAN requirements, PXE boot configurations, or option 82 relay agent policies, self-hosted DHCP is essential.

**Zero external dependencies**: When your internet connection goes down, your DHCP server must continue functioning. Self-hosted DHCP runs on your local network with no cloud dependencies, ensuring devices can always obtain addresses and connect to local services.

**Integration with local infrastructure**: Self-hosted DHCP integrates directly with your DNS server (dnsmasq provides both), your configuration management system (Ansible can deploy Kea configs), and your monitoring stack (Kea's REST API exposes metrics for Prometheus scraping).

**Cost predictability**: Enterprise DHCP solutions from Infoblox or BlueCat can cost thousands of dollars per year. Open-source alternatives like Kea and Dnsmasq provide equivalent HA capabilities at zero licensing cost, running on commodity hardware or containers.

For DNS infrastructure, see our [DNS caching resolvers guide](../2026-05-10-dns-caching-resolvers-unbound-dnscrypt-proxy-bind-guide/) and [DNS load balancing comparison](../2026-05-11-dns-load-balancing-coredns-powerdns-bind9-guide/). For IP address management, our [IPAM comparison](../2026-04-20-phpipam-vs-nipap-vs-netbox-self-hosted-ipam-guide-2026/) covers the tools that work alongside DHCP.

## FAQ

### What happens to existing DHCP leases when a server fails over?

With ISC Kea's load-balancing mode and ISC DHCP's failover protocol, lease state is synchronized in real time between servers, so the secondary server knows exactly which addresses are leased and when they expire. With Dnsmasq split-scope, the secondary server only knows about leases in its own range — clients that received addresses from the primary will renew successfully (their existing lease is honored), but the secondary cannot reissue the same addresses until the original lease expires.

### Can I run Kea DHCP HA on Raspberry Pi or edge devices?

Yes. Kea has a small footprint (approximately 50 MB of memory) and runs on ARM64 architectures. The official Docker image supports linux/arm64, making it suitable for edge deployments. However, if you're using a PostgreSQL backend, you'll need sufficient storage for the lease database.

### How do I monitor DHCP HA health?

Kea provides a REST API (via the Control Agent) that exposes server status, lease counts, and failover peer state. You can poll `/dhcp4/status` and `/ha-heartbeat` endpoints with Prometheus or Grafana. ISC DHCP has limited monitoring — you need to parse log files. Dnsmasq logs all DHCP transactions to syslog, which can be forwarded to your log aggregation system.

### Does Kea support more than two HA peers?

Kea's built-in HA framework supports exactly two peers in a pair. For deployments requiring more than two servers, you can deploy multiple independent HA pairs, each serving different subnets or VLANs.

### Is ISC DHCP still receiving security updates?

ISC DHCP is in maintenance mode. Security fixes are still released for critical vulnerabilities, but no new features are being added. ISC officially recommends migrating to Kea for new deployments. The last major release was version 4.4.3 in 2022.

### What is the MCLT parameter in ISC DHCP failover?

MCLT (Maximum Client Lead Time) defines how far ahead of the actual lease expiration time the secondary server can grant a lease. It prevents the secondary from handing out addresses that might have been renewed by a client communicating with the primary during a network partition. A typical value is 3600 seconds (1 hour).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DHCP High Availability: ISC Kea vs ISC DHCP Failover vs Dnsmasq",
  "description": "Compare DHCP high availability solutions: ISC Kea HA, ISC DHCP failover protocol, and Dnsmasq with Keepalived for resilient network infrastructure.",
  "datePublished": "2026-05-11",
  "dateModified": "2026-05-11",
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
