---
title: "Self-Hosted DHCP Server Management — Kea vs dnsmasq vs ISC DHCP"
date: 2026-05-04
tags: ["dhcp", "networking", "self-hosted", "infrastructure", "network-management"]
draft: false
---

Dynamic Host Configuration Protocol (DHCP) is the invisible backbone of every network. Every device that connects — laptops, phones, IoT sensors, servers, printers — relies on DHCP to get an IP address, DNS server information, and network configuration parameters. Yet most organizations treat DHCP as an afterthought, relying on their router's built-in server or basic configuration files with no monitoring, no centralized management, and no visibility into address allocation.

In this guide, we compare three leading open-source DHCP solutions: **ISC Kea** (the modern, extensible DHCP server with web management), **dnsmasq** (the lightweight DNS/DHCP combo), and **ISC DHCP** (the legacy standard, now end-of-life). Understanding the differences helps you choose the right tool for your network size, management needs, and operational requirements.

## Comparison at a Glance

| Feature | ISC Kea | dnsmasq | ISC DHCP (dhcpd) |
|---------|---------|---------|-------------------|
| **GitHub Stars** | 709+ | N/A (no GitHub) | N/A (no GitHub) |
| **Status** | Actively developed | Actively maintained | End-of-life (since 2022) |
| **DHCP Versions** | DHCPv4, DHCPv6 | DHCPv4, DHCPv6 | DHCPv4 only |
| **Web Management** | Stork dashboard (separate) | None (config file only) | None (config file only) |
| **Database Backend** | MySQL, PostgreSQL, Cassandra | None (file-based leases) | None (file-based leases) |
| **High Availability** | Yes (failover via database) | No (single instance) | Yes (failover protocol) |
| **DDNS Integration** | Yes (built-in hooks) | Yes (built-in) | Yes (built-in) |
| **IPv6 Support** | Full (DHCPv6, SLAAC) | Full (DHCPv6, RA) | No |
| **API Access** | REST API (via hooks) | None | None |
| **Lease Time Control** | Per-subnet, per-class, per-host | Per-subnet, per-host | Per-subnet, per-host |
| **Fingerprinting** | Yes (vendor class identification) | No | No |
| **Performance** | High (multi-threaded, async) | Very high (single-threaded, minimal) | Moderate (single-threaded) |
| **Docker Support** | Official images, Stork UI | Community images | Community images |
| **License** | MPL 2.0 | GPL v2/v3 | ISC License |

## ISC Kea: Modern DHCP Server with Web Management

[ISC Kea](https://github.com/isc-projects/kea) is the next-generation DHCP server from the Internet Systems Consortium, designed to replace the aging ISC DHCP server. It features a modular architecture with a REST API, pluggable database backends, and a companion web management dashboard called [Stork](https://github.com/isc-projects/stork).

### Key Features

- **Modular architecture** — separate processes for DHCPv4, DHCPv6, and control agent, each independently configurable
- **Pluggable database backends** — store lease data in MySQL, PostgreSQL, or Cassandra for high availability and fast queries
- **Hook framework** — extend functionality with custom hooks for logging, DDNS updates, radius authentication, and more
- **REST API** — full control API for programmatic configuration, lease management, and statistics retrieval
- **Stork management dashboard** — web-based UI for monitoring Kea servers, viewing lease statistics, and managing configurations across multiple Kea instances
- **DHCPv6 support** — full DHCPv6 implementation including prefix delegation (PD) for IPv6 network management
- **Client classification** — assign different configurations based on vendor class, client identifier, or custom expressions
- **Subnet-specific options** — configure different DNS servers, NTP servers, and other DHCP options per subnet
- **Host reservations** — assign fixed IP addresses to specific hosts via MAC address, DUID, or client identifier

### Docker Compose Deployment

Deploying Kea with PostgreSQL backend:

```yaml
services:
  kea-dhcp4:
    image: iscprojects/kea:latest
    container_name: kea-dhcp4
    network_mode: "host"
    environment:
      - KEA_DHCP4_CONFIG=/config/kea-dhcp4.json
      - KEA_DHCP4_DB_TYPE=postgresql
      - KEA_DHCP4_DB_HOST=kea-db
      - KEA_DHCP4_DB_NAME=kea
      - KEA_DHCP4_DB_USER=kea
      - KEA_DHCP4_DB_PASSWORD=kea_password
    volumes:
      - ./kea-dhcp4.json:/config/kea-dhcp4.json:ro
    depends_on:
      - kea-db
    restart: unless-stopped

  kea-db:
    image: postgres:16
    container_name: kea-db
    environment:
      - POSTGRES_USER=kea
      - POSTGRES_PASSWORD=kea_password
      - POSTGRES_DB=kea
    volumes:
      - kea_db_data:/var/lib/postgresql/data
    restart: unless-stopped

  stork:
    image: iscprojects/stork:latest
    container_name: stork
    ports:
      - "8080:8080"
    environment:
      - STORK_DATABASE_URL=postgres://stork:stork_password@stork-db:5432/stork?sslmode=disable
    depends_on:
      - stork-db
    restart: unless-stopped

  stork-db:
    image: postgres:16
    container_name: stork-db
    environment:
      - POSTGRES_USER=stork
      - POSTGRES_PASSWORD=stork_password
      - POSTGRES_DB=stork
    volumes:
      - stork_db_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  kea_db_data:
  stork_db_data:
```

Sample `kea-dhcp4.json` configuration:

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
      "password": "kea_password",
      "host": "kea-db"
    },
    "subnet4": [
      {
        "subnet": "192.168.1.0/24",
        "pools": [{ "pool": "192.168.1.100 - 192.168.1.200" }],
        "option-data": [
          { "name": "domain-name-servers", "data": "192.168.1.1" },
          { "name": "routers", "data": "192.168.1.1" }
        ]
      }
    ]
  }
}
```

### When to Use Kea

Choose Kea when you need **enterprise-grade DHCP management** with database-backed lease storage, REST API access, and a web dashboard. It is ideal for large networks with multiple subnets, high availability requirements, or environments where DHCP configuration needs to be managed programmatically. The Stork dashboard is particularly valuable for operations teams that need real-time visibility into lease allocation and server health.

## dnsmasq: Lightweight DNS and DHCP Server

[dnsmasq](https://thekelleys.org.uk/dnsmasq/doc.html) is a lightweight network infrastructure service that combines DNS caching, DHCP server, router advertisement, and network boot functionality into a single, minimal binary. It is widely used in home routers, embedded systems, and small-to-medium networks where simplicity is more important than enterprise features.

### Key Features

- **Combined DNS and DHCP** — single process handles both DNS resolution and IP address allocation
- **Minimal resource usage** — runs with less than 1MB of RAM, ideal for resource-constrained environments
- **TFTP server** — built-in TFTP for network booting (PXE) of thin clients and diskless workstations
- **Router advertisement** — provides IPv6 router advertisements for SLAAC-based address configuration
- **DHCP options** — supports all standard DHCP options plus vendor-specific extensions
- **Per-host configuration** — assign fixed IP addresses and custom options to specific MAC addresses
- **DNS filtering** — block or redirect specific domains via configuration (basic ad blocking)
- **Wildcard DNS** — map all subdomains of a domain to a specific IP address
- **Lease file** — simple text-based lease tracking, easy to inspect and modify

### Docker Compose Deployment

Running dnsmasq in a container with host networking (required for DHCP):

```yaml
services:
  dnsmasq:
    image: jpillora/dnsmasq:latest
    container_name: dnsmasq
    network_mode: "host"
    cap_add:
      - NET_ADMIN
    volumes:
      - ./dnsmasq.conf:/etc/dnsmasq.conf:ro
      - ./dnsmasq.hosts:/etc/dnsmasq.hosts:ro
      - dnsmasq_leases:/var/lib/misc
    restart: unless-stopped

volumes:
  dnsmasq_leases:
```

Sample `dnsmasq.conf`:

```
# Interface to listen on
interface=eth0
bind-interfaces

# DHCP range: 192.168.1.100-200, 24-hour lease
dhcp-range=192.168.1.100,192.168.1.200,255.255.255.0,24h

# Default gateway
dhcp-option=3,192.168.1.1

# DNS servers
dhcp-option=6,192.168.1.1,8.8.8.8

# Domain name
domain=home.local

# Host reservations
dhcp-host=aa:bb:cc:dd:ee:01,192.168.1.50,server1
dhcp-host=aa:bb:cc:dd:ee:02,192.168.1.51,server2

# DNS entries
address=/server1.home.local/192.168.1.50
address=/server2.home.local/192.168.1.51
```

### When to Use dnsmasq

Choose dnsmasq when you need a **simple, reliable DHCP server** for a single subnet with minimal configuration overhead. It is perfect for home networks, homelabs, small office networks, and embedded deployments where resource usage matters. The combined DNS+DHCP functionality makes it especially convenient for networks where you also need local DNS resolution — all managed through a single configuration file.

## ISC DHCP (dhcpd): The Legacy Standard

The [ISC DHCP server](https://www.isc.org/dhcp/) (dhcpd) was the dominant open-source DHCP implementation for over two decades. It powered countless enterprise networks, home routers, and cloud infrastructure deployments. However, ISC officially **ended support in December 2022**, and no further development or security patches are planned.

### Key Features (Historical)

- **Proven reliability** — decades of production use across millions of deployments
- **DHCP failover protocol** — built-in primary/secondary failover for high availability
- **Dynamic DNS updates** — automatic DNS record creation for DHCP-assigned addresses
- **Flexible configuration** — extensive option support for complex network setups
- **Lease database** — file-based lease tracking with configurable lease durations
- **Class-based allocation** — assign different address pools based on client characteristics

### Why You Should Migrate Away

Since ISC DHCP reached end-of-life, continuing to use it exposes your network to unpatched security vulnerabilities. The recommended migration path is to **Kea**, which is ISC's designated successor and shares the same configuration philosophy while adding modern features like database backends, REST APIs, and web management.

For most dnsmasq users, there is no urgency to migrate — dnsmasq remains actively maintained. However, if you need DHCPv6 support, database-backed leases, or a management UI, Kea is the natural upgrade path.

## Choosing the Right DHCP Server

| Scenario | Recommended Tool |
|----------|-----------------|
| Enterprise network with multiple subnets | **ISC Kea** |
| Need web dashboard for DHCP monitoring | **ISC Kea + Stork** |
| Database-backed lease storage required | **ISC Kea** |
| Home network or homelab | **dnsmasq** |
| Combined DNS + DHCP in minimal footprint | **dnsmasq** |
| Resource-constrained hardware (router, Pi) | **dnsmasq** |
| Still running ISC DHCP in production | **Migrate to Kea immediately** |
| Need DHCPv6 with prefix delegation | **ISC Kea** |
| Programmatic DHCP management via API | **ISC Kea** |
| PXE boot server for diskless clients | **dnsmasq** |

## Why Self-Host Your DHCP Server?

Running your own DHCP server gives you complete control over IP address allocation, DNS server assignment, and network option distribution. When you rely on your ISP router or managed switch's built-in DHCP, you are limited to their feature set and have no visibility into lease allocation patterns.

For organizations with multiple subnets, a self-hosted DHCP server like Kea enables centralized management of address pools, per-subnet option configuration, and lease tracking across the entire network. The database backend provides historical lease data for capacity planning and troubleshooting.

For home networks and homelabs, dnsmasq eliminates the need for separate DNS and DHCP services. A single configuration file manages both IP address allocation and local name resolution, with optional PXE boot support for diskless workstations.

For compliance and security, self-hosted DHCP ensures that DNS server assignments come from your own infrastructure, not from an external DHCP server that could redirect clients to malicious resolvers. Combined with a self-hosted DNS resolver, this creates a complete, trusted name resolution chain.

For related reading, see our [split-horizon DNS configuration guide](../2026-04-24-self-hosted-split-horizon-dns-pihole-dnsmasq-coredns-bind9-guide-2026/) which covers integrating DHCP-assigned DNS with internal name resolution, and our [DNS firewall guide](../2026-04-21-self-hosted-dns-firewall-rpz-unbound-powerdns-bind9-knot-guide-2026/) for network-level DNS filtering that works alongside your DHCP configuration.

## FAQ

### What is the difference between ISC DHCP and ISC Kea?

Kea is the modern successor to ISC DHCP, designed from the ground up with a modular architecture, database backends, and a REST API. ISC DHCP uses a monolithic design with file-based lease storage and no API. ISC officially ended DHCP support in December 2022 and recommends migrating to Kea for all new deployments.

### Why does dnsmasq need host networking in Docker?

DHCP uses broadcast packets that cannot be routed through Docker's default bridge networking. Running dnsmasq with `network_mode: "host"` allows it to receive and respond to broadcast DHCP requests directly on the physical network interface. This is required for any DHCP server running in a container.

### Can Kea handle DHCP failover like ISC DHCP?

Kea achieves high availability differently — instead of a primary/secondary failover protocol, it uses a shared database backend (PostgreSQL, MySQL, or Cassandra) that multiple Kea instances can read from simultaneously. This provides better fault tolerance and simpler configuration than the ISC DHCP failover protocol.

### Does dnsmasq support IPv6 DHCP?

Yes. dnsmasq supports both DHCPv6 (stateful address assignment) and Router Advertisement (SLAAC, stateless address configuration). You can configure it to provide either or both, depending on your network's IPv6 strategy.

### How do I monitor DHCP lease allocation?

With Kea + Stork, the dashboard provides real-time lease statistics, subnet utilization graphs, and server health monitoring. With dnsmasq, you inspect the lease file (typically `/var/lib/misc/dnsmasq.leases`) or enable syslog logging for real-time lease events. ISC DHCP has a similar lease file at `/var/lib/dhcp/dhcpd.leases`.

### Can I run Kea and dnsmasq on the same network?

You can, but only one DHCP server should be active per subnet to avoid address conflicts. A common pattern is to run Kea as the primary DHCP server for address allocation and dnsmasq as a DNS cache and local resolver on a different server. Configure Kea to hand out the dnsmasq server's IP as the DNS server via DHCP option 6.

### What happens to existing ISC DHCP clients when I migrate to Kea?

Kea can read ISC DHCP lease files during migration, so existing clients will retain their current IP assignments. You can also configure Kea with the same subnet and pool definitions as your ISC DHCP server, ensuring a seamless transition. The Kea documentation provides detailed migration guides from ISC DHCP.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DHCP Server Management — Kea vs dnsmasq vs ISC DHCP",
  "description": "Compare three open-source DHCP server solutions: ISC Kea with Stork web management, dnsmasq lightweight DNS/DHCP combo, and legacy ISC DHCP (end-of-life).",
  "datePublished": "2026-05-04",
  "dateModified": "2026-05-04",
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
