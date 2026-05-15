---
title: "Self-Hosted DHCPv6 Servers: Kea vs odhcpd vs Dnsmasq"
date: "2026-05-16"
tags: ["dhcpv6", "ipv6", "networking", "kea", "odhcpd", "dnsmasq", "self-hosted"]
draft: false
---

As IPv6 adoption grows across home networks, enterprise infrastructure, and cloud environments, the need for reliable DHCPv6 servers has become essential. While many self-hosted networking guides focus on IPv4 DHCP, running a dedicated DHCPv6 server requires different considerations — from stateless vs stateful address assignment to prefix delegation for downstream routers.

In this guide, we compare three open-source DHCPv6 servers: **Kea DHCP** (the modern ISC successor), **odhcpd** (OpenWrt's lightweight DHCPv6/PD server), and **Dnsmasq** (the ubiquitous lightweight DNS/DHCP combo). Each takes a fundamentally different approach to IPv6 address management, and choosing the right one depends on your network topology, scale, and management requirements.

## Understanding DHCPv6: Stateful vs Stateless vs Prefix Delegation

Before comparing the servers, it's important to understand the three DHCPv6 modes they support:

- **Stateful DHCPv6**: The server assigns specific IPv6 addresses to clients and tracks lease state, similar to DHCPv4. Clients use their assigned address for all communication.
- **Stateless DHCPv6 (SLAAC + DHCPv6)**: Clients generate their own addresses via SLAAC (Router Advertisement), but contact the DHCPv6 server for additional configuration like DNS servers, NTP servers, and domain search lists.
- **Prefix Delegation (PD)**: The server delegates entire IPv6 prefix blocks to downstream routers (e.g., ISP delegating /56 or /64 prefixes to customer edge routers). This is critical for networks with multiple subnets behind a single upstream connection.

Most production DHCPv6 deployments require a combination of stateful assignment and prefix delegation, which not all servers handle equally well.

## Comparison Table

| Feature | Kea DHCP | odhcpd | Dnsmasq |
|---|---|---|---|
| **Stars / Activity** | 714 (ISC project) | 198 (OpenWrt) | 1,100+ (Simon Kelley) |
| **Stateful DHCPv6** | Full support | Full support | Full support |
| **Stateless DHCPv6** | Yes | Yes | Yes |
| **Prefix Delegation** | Yes (with hooks) | Yes (optimized) | Yes (basic) |
| **High Availability** | Kea HA hook (active-active) | No (single instance) | No (single instance) |
| **REST API** | Yes (control agent) | No (UCI config) | No (config file only) |
| **Database Backend** | MySQL, PostgreSQL, Cassandra | In-memory | In-memory |
| **Docker Support** | Official images | Community images | Official images |
| **IPv4+IPv6 Dual-Stack** | Single daemon (kea-dhcp6) | Single daemon | Single daemon |
| **Configuration Hot-Reload** | Yes | Yes (SIGHUP) | Yes (SIGHUP) |
| **Logging Detail** | Structured JSON logging | Syslog | Syslog |
| **Best For** | Enterprise, ISP, HA | Home routers, OpenWrt | Small networks, combo DNS+DHCP |

## Kea DHCP — Modern Enterprise DHCPv6 Server

Kea is the next-generation DHCP server from ISC, designed as a replacement for the legacy ISC DHCP daemon. It features a modular architecture with a dedicated `kea-dhcp6` process for IPv6, REST API management via the Kea Control Agent, and pluggable database backends.

### Key Features

- **Modular design**: Separate daemons for DHCPv4 (`kea-dhcp`) and DHCPv6 (`kea-dhcp6`), sharing common infrastructure
- **Database persistence**: Stores leases in MySQL, PostgreSQL, or Cassandra — survives daemon restarts without losing state
- **Hooks framework**: Extensible via C++ and Python hooks for custom logic (e.g., RADIUS integration, custom address selection)
- **High Availability**: The Kea HA hook provides active-active failover with lease database synchronization
- **REST API**: Full configuration and status management via JSON-RPC over HTTP

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  kea-dhcp6:
    image: isc/kea-ctrl-agent:latest
    container_name: kea-dhcp6
    network_mode: "host"
    volumes:
      - ./kea-dhcp6.conf:/etc/kea/kea-dhcp6.conf:ro
      - ./kea-ctrl-agent.conf:/etc/kea/kea-ctrl-agent.conf:ro
      - kea-leases:/var/lib/kea
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
      - NET_RAW

volumes:
  kea-leases:
```

### Kea DHCPv6 Configuration Snippet

```json
{
  "Dhcp6": {
    "interfaces-config": {
      "interfaces": ["eth0"]
    },
    "lease-database": {
      "type": "mysql",
      "name": "kea_leases",
      "user": "kea",
      "password": "kea_password"
    },
    "subnet6": [
      {
        "subnet": "2001:db8:1::/64",
        "pools": [{ "pool": "2001:db8:1::100-2001:db8:1::200" }],
        "pd-pools": [{
          "prefix": "2001:db8:2::",
          "prefix-len": 48,
          "delegated-len": 64
        }],
        "option-data": [
          {
            "name": "dns-servers",
            "data": "2001:db8:1::1"
          }
        ]
      }
    ]
  }
}
```

## odhcpd — Lightweight DHCPv6 for Edge Networks

odhcpd is the default DHCPv6 and Prefix Delegation server for OpenWrt, designed specifically for edge routers and gateway devices. It handles DHCPv6, SLAAC, and prefix delegation in a single lightweight process with minimal resource requirements.

### Key Features

- **OpenWrt integration**: Native UCI configuration, tightly integrated with OpenWrt's firewall and routing stack
- **Prefix Delegation first**: Designed around PD workflows — ideal for ISP gateway deployments where downstream routers need prefix blocks
- **SLAAC integration**: Generates Router Advertisements alongside DHCPv6 responses, handling both stateless and stateful modes
- **Lightweight footprint**: Written in C with minimal dependencies, runs comfortably on routers with 64MB RAM
- **Netfilter integration**: Works with OpenWrt's firewall rules for automatic NDP proxy configuration

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  odhcpd:
    image: openwrt/odhcpd:latest
    container_name: odhcpd
    network_mode: "host"
    volumes:
      - ./odhcpd.conf:/etc/odhcpd.conf:ro
      - /proc/net/if_inet6:/proc/net/if_inet6:ro
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
      - NET_RAW
```

### odhcpd Configuration Snippet

```
config dhcp lan
    option interface 'lan'
    option start '100'
    option limit '150'
    option leasetime '12h'
    option ra 'server'
    option dhcpv6 'server'
    option ndp 'hybrid'
    option pd_hold '300'
    option pd_reclass '300'
```

## Dnsmasq — Combined DNS and DHCPv6

Dnsmasq is the most widely deployed lightweight DNS/DHCP server, combining DNS forwarding, DHCPv4, and DHCPv6 in a single process. While primarily known as a DNS caching server, its DHCPv6 capabilities are sufficient for small to medium networks.

### Key Features

- **All-in-one**: Single daemon handles DNS caching, DHCPv4, DHCPv6, TFTP, and Router Advertisements
- **Simple configuration**: Single config file with straightforward syntax
- **Wide availability**: Packaged in virtually every Linux distribution
- **DNS integration**: Automatically generates PTR records for DHCPv6-assigned addresses
- **Low resource usage**: Typically runs with under 5MB RAM

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  dnsmasq:
    image: jpillora/dnsmasq:latest
    container_name: dnsmasq
    network_mode: "host"
    volumes:
      - ./dnsmasq.conf:/etc/dnsmasq.conf:ro
      - ./dnsmasq.d:/etc/dnsmasq.d:ro
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
```

### Dnsmasq DHCPv6 Configuration Snippet

```
# Enable DHCPv6 on the LAN interface
interface=eth0

# DHCPv6 address range
dhcp-range=2001:db8:1::100,2001:db8:1::200,64,12h

# Prefix delegation pool
dhcp-range=2001:db8:2::,ra-only

# DNS server option
dhcp-option=option6:dns-server,[2001:db8:1::1]

# Domain search list
dhcp-option=option6:domain-search,home.lan

# Enable Router Advertisements
ra-param=eth0,managed,1800
```

## Why Self-Host Your DHCPv6 Server?

Running your own DHCPv6 server gives you complete control over IPv6 address assignment, prefix delegation, and network configuration in your environment. Unlike relying on your ISP's router or cloud-managed DHCP services, a self-hosted DHCPv6 server ensures that your internal network's IPv6 topology is determined by you, not a third party.

**Data ownership and privacy**: When you run your own DHCPv6 server, all address assignment logs, client identification data (DUIDs), and lease history stay within your infrastructure. There's no telemetry sent to external vendors, and no dependency on cloud-based DHCP management platforms that could change their pricing model or discontinue service.

**Prefix delegation control**: For networks with multiple subnets — home labs, branch offices, or multi-tenant environments — managing your own prefix delegation means you control exactly which downstream routers get which prefix blocks, at what delegation lengths, and with what lifetimes. This is critical for networks that need to re-address without disrupting service.

**No vendor lock-in**: Many enterprise networking vendors tie DHCPv6 functionality into expensive hardware appliances or subscription-based management platforms. Open-source DHCPv6 servers like Kea, odhcpd, and Dnsmasq run on commodity hardware and can be deployed in containers, virtual machines, or bare metal — giving you the flexibility to migrate between infrastructure providers without changing your DHCPv6 configuration.

**Cost savings at scale**: For ISPs and large enterprises, the licensing costs for proprietary DHCPv6 solutions can be significant. Kea DHCP is free and open-source, with enterprise-grade features including HA failover and database-backed lease storage. Running Kea on standard x86 hardware costs a fraction of dedicated DHCP appliances.

For IPv4 DHCP management, see our [complete DHCP server guide](../2026-05-04-self-hosted-dhcp-server-management-kea-dnsmasq-isc-dhcp-guide/). If you need DHCP high availability, check our [DHCP failover comparison](../2026-05-09-self-hosted-dhcp-high-availability-kea-ha-vs-isc-dhcp-vs-keepalived-guide/). For DNS configuration that pairs with your DHCPv6 setup, our [DNS caching resolver guide](../2026-05-10-dns-caching-resolvers-unbound-dnscrypt-proxy-bind-guide/) covers the essentials.

## Choosing the Right DHCPv6 Server

**Choose Kea DHCP if**: You need enterprise-grade features — high availability, database-backed lease storage, REST API management, or integration with RADIUS/AAA systems. Kea is the best choice for ISPs, data centers, and organizations that need active-active failover with lease synchronization.

**Choose odhcpd if**: You're running OpenWrt or need a lightweight DHCPv6/PD server for edge routers. odhcpd's tight integration with OpenWrt's networking stack makes it the default choice for gateway deployments where prefix delegation to downstream devices is the primary requirement.

**Choose Dnsmasq if**: You have a small to medium network and want a single daemon handling both DNS and DHCPv6. Dnsmasq's simplicity and low resource requirements make it ideal for home labs, SOHO environments, and deployments where minimizing the number of running services is a priority.

## FAQ

### What is the difference between DHCPv6 and SLAAC?
SLAAC (Stateless Address Autoconfiguration) allows IPv6 clients to generate their own addresses from router advertisements, without any server involvement. DHCPv6 can operate alongside SLAAC to provide additional configuration (DNS servers, domain names) or can run in stateful mode to assign specific addresses. Many networks use both: SLAAC for address generation and DHCPv6 for DNS configuration.

### Can Kea DHCP handle both IPv4 and IPv6?
Yes, but through separate daemon processes. Kea uses `kea-dhcp` for DHCPv4 and `kea-dhcp6` for DHCPv6. Both can run on the same server and share a common database backend. The Kea Control Agent provides a unified REST API for managing both daemons simultaneously.

### Does Dnsmasq support prefix delegation in DHCPv6?
Dnsmasq supports basic prefix delegation through its `ra-only` and `dhcp-range` configuration, but it lacks the advanced PD management features found in Kea and odhcpd. For simple single-prefix delegation scenarios, Dnsmasq is sufficient. For complex multi-prefix deployments with different delegation lengths per client, use Kea or odhcpd.

### How do I migrate from ISC DHCP to Kea for IPv6?
Kea provides a migration tool (`kea-admin lease6-import`) that can import ISC DHCP lease databases. The configuration syntax differs significantly (ISC uses flat config files, Kea uses JSON), so you'll need to rewrite your configuration. ISC recommends migrating to Kea since the legacy ISC DHCP is in maintenance-only mode with no new features.

### Is odhcpd suitable for enterprise networks?
odhcpd is designed primarily for edge router and SOHO deployments. It lacks features that enterprise networks typically require: no REST API, no database-backed lease storage, no high availability, and no hooks framework. For enterprise deployments, Kea DHCP is the recommended choice.

### Can I run DHCPv6 and DHCPv4 on the same server?
Yes. All three servers discussed (Kea, odhcpd, Dnsmasq) support dual-stack operation. Kea uses separate processes for IPv4 and IPv6, while odhcpd and Dnsmasq handle both protocols in a single daemon. Running both on the same server is common practice for self-hosted networks transitioning from IPv4 to IPv6.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DHCPv6 Servers: Kea vs odhcpd vs Dnsmasq",
  "description": "Compare three open-source DHCPv6 servers for IPv6 network management. Covers Kea DHCP, odhcpd, and Dnsmasq with Docker Compose configs and deployment guides.",
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
