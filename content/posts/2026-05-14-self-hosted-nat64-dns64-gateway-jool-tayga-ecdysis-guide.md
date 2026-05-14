---
title: "Self-Hosted NAT64/DNS64 Gateway: Jool vs TAYGA vs Ecdysis"
date: "2026-05-14"
tags: ["ipv6", "nat64", "dns64", "networking", "comparison", "guide", "self-hosted"]
draft: false
description: "Complete guide to deploying NAT64/DNS64 gateways for IPv6-only networks. Compare Jool, TAYGA, and Ecdysis for IPv4-to-IPv6 translation."
---

NAT64 and DNS64 are complementary protocols that enable IPv6-only clients to communicate with IPv4-only servers — a critical capability as networks transition to IPv6. NAT64 translates IPv6 packets to IPv4 at the network layer, while DNS64 synthesizes AAAA records from A records when no native IPv6 address exists. Together, they allow organizations to deploy IPv6-only internal networks while maintaining full access to the IPv4 internet.

In this guide, we compare three leading open-source NAT64/DNS64 implementations: **Jool**, **TAYGA**, and **Ecdysis**. Whether you're building an IPv6-only data center, deploying mobile network infrastructure, or transitioning your home lab to IPv6, you'll find the right translation solution here.

For related reading, see our [IPv6 neighbor discovery guide](../2026-05-13-self-hosted-ipv6-neighbor-discovery-ndppd-corerad-ndp-library-guide/) and [network configuration management guide](../2026-05-05-self-hosted-network-configuration-management-ansible-nornir-netbox-guide/).

## Understanding NAT64 and DNS64

### NAT64 (Network Address Translation 64)
NAT64 sits at the boundary between IPv6 and IPv4 networks. When an IPv6-only client sends a packet to an IPv4 destination (represented as an IPv6-mapped address like `64:ff9b::192.0.2.1`), NAT64 translates the packet headers and forwards it to the actual IPv4 address.

### DNS64
DNS64 is a recursive DNS resolver that synthesizes AAAA records for IPv4-only domains. When a client queries a domain that only has an A record, DNS64 creates a synthetic AAAA record using the NAT64 prefix (typically `64:ff9b::/96`). This allows IPv6-only clients to discover IPv4 destinations without any application changes.

### Why NAT64/DNS64 Matters

The global transition to IPv6 is accelerating, but a significant portion of internet services still only support IPv4. NAT64/DNS64 provides a transition bridge that:

- Enables IPv6-only network deployment (required for 5G mobile networks)
- Reduces dual-stack operational complexity
- Improves security by eliminating IPv4 attack surface on internal networks
- Meets regulatory requirements for IPv6 adoption
- Simplifies network management with a single addressing scheme

## Jool

Jool is a Linux kernel module and user-space tool for NAT64 and SIIT (Stateless IP/ICMP Translation). It is the most feature-complete open-source NAT64 implementation, supporting both stateful NAT64 and stateless SIIT modes.

### Jool Features
- **Stateful NAT64** — Full session tracking with port translation
- **Stateless SIIT** — 1:1 IPv6-to-IPv4 address mapping (no session state)
- **NAT66** — IPv6-to-IPv6 network prefix translation
- **EIM (Endpoint-Independent Mapping)** — Compatible with symmetric NATs
- **Linux kernel module** — High performance, zero-copy packet processing
- **User-space daemon** — jool for configuration and monitoring

### Jool Installation

```bash
# Install kernel module (Ubuntu/Debian)
sudo apt install jool-tools-linux

# Or build from source
git clone https://github.com/NICMx/Jool.git
cd Jool/mod
make
sudo make install

# Install user-space tools
cd ../usr
make
sudo make install
```

### Jool NAT64 Configuration

```bash
# Load the NAT64 kernel module
sudo modprobe jool

# Configure NAT64 pool
sudo jool instance add --netfilter --type nat64
sudo jool pool add --instance nat64 192.0.2.1-192.0.2.254

# Set the NAT64 prefix (default: 64:ff9b::/96)
sudo jool global config set pool4 64:ff9b::/96

# Add iptables rules
sudo iptables -t nat -A POSTROUTING -j JOOL --v6-addr 64:ff9b::/96
```

### Jool Docker Compose

```yaml
version: "3.8"
services:
  jool-nat64:
    image: nicmx/jool:latest
    container_name: jool-nat64
    network_mode: host
    cap_add:
      - NET_ADMIN
      - SYS_MODULE
    volumes:
      - /lib/modules:/lib/modules:ro
      - ./jool.conf:/etc/jool/jool.conf:ro
    environment:
      - JOOL_INSTANCE=nat64
      - JOOL_POOL=192.0.2.1-192.0.2.254
      - JOOL_PREFIX=64:ff9b::/96
    restart: unless-stopped
    # Note: NAT64 requires kernel module access, so host networking is needed
```

## TAYGA

TAYGA is a stateless NAT64 implementation for Linux that operates as a TUN/TAP-based virtual network device. Unlike Jool's kernel module approach, TAYGA uses a simpler architecture that's easier to deploy but may have lower throughput.

### TAYGA Features
- **Stateless NAT64** — No session state, suitable for 1:1 address mapping
- **TUN/TAP based** — Runs in user-space with a virtual network interface
- **DNS64 integration** — Works with BIND or PowerDNS for DNS64
- **Simple configuration** — Single configuration file
- **IPv6 PMTU discovery** — Proper handling of path MTU for translated packets

### TAYGA Installation

```bash
# Ubuntu/Debian
sudo apt install tayga

# Enable IPv6 forwarding
sudo sysctl -w net.ipv6.conf.all.forwarding=1
sudo sysctl -w net.ipv4.conf.all.forwarding=1
```

### TAYGA Configuration

```
# /etc/tayga.conf
prefix 64:ff9b::/96
ipv4-addr 192.0.2.1
map 2001:db8:64:ff9b::/96 192.0.2.0/24
data-dir /var/lib/tayga
tun-device tayga0
```

### Starting TAYGA

```bash
# Start the TAYGA daemon
sudo systemctl start tayga
sudo systemctl enable tayga

# Verify the tunnel interface
ip addr show tayga0
# Should show both IPv4 and IPv6 addresses

# Test translation
ping6 64:ff9b::8.8.8.8
```

### TAYGA + BIND DNS64 Docker Compose

```yaml
version: "3.8"
services:
  tayga:
    image: linuxserver/tayga:latest
    container_name: tayga-nat64
    cap_add:
      - NET_ADMIN
    volumes:
      - ./tayga.conf:/etc/tayga.conf:ro
    network_mode: host
    restart: unless-stopped

  bind9-dns64:
    image: ubuntu/bind9:latest
    container_name: bind9-dns64
    ports:
      - "53:53/tcp"
      - "53:53/udp"
    volumes:
      - ./named-dns64.conf:/etc/bind/named.conf:ro
    environment:
      - BIND9_USER=root
    restart: unless-stopped

volumes:
  tayga-data:
```

## Ecdysis

Ecdysis (formerly known as "nat64") is a userspace NAT64 implementation that provides both NAT64 and DNS64 in a single package. It is designed for lightweight deployments and containerized environments.

### Ecdysis Features
- **Integrated NAT64 + DNS64** — Single daemon handles both translation and DNS synthesis
- **Userspace implementation** — No kernel module required
- **DNS64 server** — Built-in recursive resolver with AAAA synthesis
- **Lightweight** — Suitable for containers and edge deployments
- **Simple configuration** — YAML-based config file

### Ecdysis Installation

```bash
# Build from source
git clone https://github.com/ecdysis/nat64.git
cd nat64
cargo build --release
sudo cp target/release/nat64 /usr/local/bin/

# Or use Docker
docker pull ecdysis/nat64:latest
```

### Ecdysis Configuration

```yaml
# nat64-config.yaml
nat64:
  prefix: "64:ff9b::/96"
  ipv4_pool:
    start: "192.0.2.1"
    end: "192.0.2.254"
  interface: "eth0"

dns64:
  listen: "0.0.0.0:53"
  upstream:
    - "8.8.8.8"
    - "8.8.4.4"
  prefix: "64:ff9b::/96"
```

### Ecdysis Docker Compose

```yaml
version: "3.8"
services:
  ecdysis-nat64:
    image: ecdysis/nat64:latest
    container_name: ecdysis-nat64
    cap_add:
      - NET_ADMIN
    volumes:
      - ./nat64-config.yaml:/etc/nat64/config.yaml:ro
    ports:
      - "53:53/tcp"
      - "53:53/udp"
    network_mode: host
    restart: unless-stopped
```

## NAT64/DNS64 Feature Comparison

| Feature | Jool | TAYGA | Ecdysis |
|---------|------|-------|---------|
| NAT64 Mode | Stateful + Stateless (SIIT) | Stateless | Stateful |
| DNS64 | External (BIND/PowerDNS) | External (BIND) | Built-in |
| Kernel vs Userspace | Kernel module | TUN/TAP (userspace) | Userspace |
| Performance | Highest (kernel-level) | Moderate | Moderate |
| IPv4 Pool Size | Configurable | Configurable | Configurable |
| SIIT Support | Yes | No | No |
| NAT66 Support | Yes | No | No |
| Container Deployment | Requires NET_ADMIN | Requires NET_ADMIN | Requires NET_ADMIN |
| Docker Image | Official (nicmx/jool) | Community (linuxserver) | Community |
| Active Development | Yes (NICMx) | Maintenance mode | Active |

## Choosing the Right NAT64 Solution

### Choose Jool when:
- You need the highest performance (kernel-module processing)
- You require both stateful NAT64 and stateless SIIT
- You need NAT66 support for IPv6-to-IPv6 prefix translation
- You're deploying at scale (ISP, enterprise, data center)

### Choose TAYGA when:
- You prefer a simpler, userspace-based deployment
- You need stateless NAT64 with 1:1 address mapping
- You're already running BIND DNS64 and want a lightweight NAT64 companion
- Kernel module installation is not an option (containers, managed hosts)

### Choose Ecdysis when:
- You want NAT64 and DNS64 in a single package
- You're deploying in containers or edge environments
- You prefer YAML configuration over zone files
- You need a lightweight, integrated solution

## Why Deploy NAT64/DNS64?

Running your own NAT64/DNS64 gateway is essential for organizations transitioning to IPv6-only networks. As mobile carriers and cloud providers increasingly deploy IPv6-only infrastructure, the ability to seamlessly reach IPv4-only services becomes a business requirement.

**Future-proofing:** IPv4 address exhaustion is accelerating. NAT64/DNS64 enables you to deploy new services on IPv6-only infrastructure while maintaining backward compatibility. This is the architecture used by major mobile carriers (T-Mobile, AT&T) for their 5G networks.

**Security:** IPv6-only internal networks eliminate the IPv4 attack surface entirely. Many legacy attacks target IPv4-specific protocols and services. By translating at the gateway, you can inspect and filter traffic between IPv6 clients and IPv4 servers.

**Operational simplicity:** Managing a single addressing scheme (IPv6) is simpler than maintaining dual-stack networks. NAT64/DNS64 eliminates the need to configure and troubleshoot IPv4 routing, DHCP, and firewall rules on internal networks.

For related reading, see our [IPv6 tunnel broker guide](../2026-04-24-self-hosted-dns-failover-keepalived-powerdns-haproxy-guide-2026/) and [DNS reconnaissance guide](../2026-04-23-amass-vs-subfinder-vs-massdns-self-hosted-dns-reconnaissance-guide-2026/).

## FAQ

### What is NAT64 and why do I need it?

NAT64 translates IPv6 packets to IPv4, allowing IPv6-only clients to communicate with IPv4-only servers. You need it when deploying IPv6-only networks (common in 5G mobile networks, cloud environments, and modern data centers) that must still access IPv4-only internet services.

### What is DNS64 and how does it work with NAT64?

DNS64 is a recursive DNS resolver that synthesizes AAAA records for IPv4-only domains. When a client queries a domain without native IPv6, DNS64 creates a synthetic AAAA record using the NAT64 prefix (64:ff9b::/96). The client then sends IPv6 packets to this address, which NAT64 translates to IPv4.

### What is the NAT64 prefix 64:ff9b::/96?

64:ff9b::/96 is the Well-Known Prefix (WKP) defined in RFC 6052 for NAT64. It is a reserved prefix that all NAT64 implementations recognize. When an IPv6 address starts with this prefix, the last 32 bits represent the IPv4 address (e.g., 64:ff9b::192.0.2.1 maps to 192.0.2.1).

### Can NAT64 work without DNS64?

Yes, but applications must know the IPv4-to-IPv6 mapping. Without DNS64, applications would need to manually construct IPv6-mapped addresses (e.g., 64:ff9b::8.8.8.8). DNS64 automates this by synthesizing AAAA records, making NAT64 transparent to applications.

### Is Jool production-ready?

Yes. Jool is used in production by ISPs, mobile carriers, and cloud providers. It is developed by NIC Mexico (NICMx) and is actively maintained. It supports both stateful NAT64 and stateless SIIT, and has been tested at multi-gigabit throughput levels.

### Does NAT64 break applications?

Most applications work transparently through NAT64. However, applications that embed IP addresses in payloads (FTP, SIP, some P2P protocols) may require Application Layer Gateways (ALGs) or protocol-specific handling. Jool supports some ALG functionality; for complex protocols, consider protocol-aware translation.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted NAT64/DNS64 Gateway: Jool vs TAYGA vs Ecdysis",
  "description": "Complete guide to deploying NAT64/DNS64 gateways for IPv6-only networks. Compare Jool, TAYGA, and Ecdysis for IPv4-to-IPv6 translation.",
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
