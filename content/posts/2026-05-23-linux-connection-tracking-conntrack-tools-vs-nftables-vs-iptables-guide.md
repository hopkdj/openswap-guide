---
title: "Self-Hosted Linux Connection Tracking: conntrack-tools vs nftables vs iptables"
date: "2026-05-23"
tags: ["linux", "networking", "firewall", "netfilter", "security"]
draft: false
---

Connection tracking is the foundation of stateful firewall operation on Linux. It enables the kernel to understand which packets belong to established connections, which are new, and which are invalid — allowing granular security policies that go far beyond simple port blocking. The Linux Netfilter framework provides three primary interfaces for managing connection tracking: **conntrack-tools** (userspace management utilities), **nftables** (the modern replacement for iptables), and **iptables** (the legacy but still widely deployed packet filter).

Whether you are building a stateful firewall, configuring NAT for a self-hosted network, or troubleshooting connection timeouts, understanding these tools and their relationship to the kernel's connection tracking subsystem is essential.

## How Linux Connection Tracking Works

Before comparing tools, it helps to understand the architecture. Connection tracking in Linux is implemented in the kernel as the `nf_conntrack` module, which sits within the Netfilter framework:

1. **Kernel module** (`nf_conntrack`): Maintains a hash table of all tracked connections, tracking source/destination IP, ports, protocol state, and timeouts
2. **Netfilter hooks**: Intercept packets at various points in the network stack (PREROUTING, INPUT, FORWARD, OUTPUT, POSTROUTING)
3. **Userspace tools**: conntrack-tools, nftables, and iptables provide interfaces to query, modify, and configure the connection tracking table

Each packet passing through the system is classified as one of four connection states:
- **NEW**: First packet of a connection (no matching entry in the tracking table)
- **ESTABLISHED**: Packet belongs to an already-tracked connection
- **RELATED**: Packet is starting a new connection but is associated with an existing one (e.g., FTP data channel, ICMP error)
- **INVALID**: Packet does not match any known connection and is not valid for starting a new one

## Feature Comparison

| Feature | conntrack-tools | nftables | iptables |
|---------|----------------|----------|----------|
| **Role** | Userspace management | Firewall + conntrack config | Firewall + conntrack config |
| **Connection Table Query** | Yes (full detail) | Limited | No (requires conntrack) |
| **Connection Deletion** | Yes (individual/bulk) | Yes (via rules) | No |
| **NAT Configuration** | No | Yes (full NAT) | Yes (full NAT) |
| **Stateful Rules** | No | Yes (ct state match) | Yes (state/ctstate match) |
| **Connection Helpers** | Yes (ALG config) | Yes (ct helper) | Yes (CT target) |
| **Expectation Management** | Yes | Yes | No |
| **Event Monitoring** | Yes (real-time events) | No | No |
| **Backend** | libnetfilter_conntrack | nftables kernel API | iptables kernel API |
| **Performance** | N/A (management only) | Fast (single binary) | Slower (multiple binaries) |
| **Syntax Complexity** | Moderate | Moderate | Low (mature docs) |
| **Default on Modern Distros** | No | Yes (Debian 10+, RHEL 8+) | Yes (legacy default) |
| **Connection Limiting** | Via conntrack table size | Yes (ct count match) | Yes (connlimit match) |
| **Connection Timeout Config** | Yes | Yes (via sysfs/nft) | Yes (via sysfs) |

## conntrack-tools — Connection Tracking Management

conntrack-tools is a suite of userspace utilities for managing the Linux connection tracking table. It does not replace iptables or nftables — rather, it complements them by providing visibility and control over the kernel's connection tracking state.

### Key Features

- **conntrack**: Query, add, delete, and update connection tracking entries
- **conntrackd**: Distributed connection tracking daemon for high-availability firewalls
- **Real-time event monitoring**: Watch connection state changes as they happen
- **Expectation management**: Configure protocol helpers for RELATED connections
- **Statistics**: View connection table utilization, insertions, deletions, and errors

### Installation

```bash
# Debian/Ubuntu
sudo apt install conntrack conntrackd

# RHEL/Fedora
sudo dnf install conntrack-tools conntrack-tools-lib

# Arch Linux
sudo pacman -S conntrack-tools
```

### Common Operations

```bash
# List all tracked connections
sudo conntrack -L

# List only TCP connections in ESTABLISHED state
sudo conntrack -L -p tcp --state ESTABLISHED

# Count connections by protocol
sudo conntrack -C

# Delete all connections from a specific IP
sudo conntrack -D -s 192.168.1.100

# Monitor connection events in real-time
sudo conntrack -E

# View connection tracking statistics
sudo conntrack -S
```

### Docker Deployment

```yaml
version: "3.8"
services:
  conntrack-monitor:
    image: alpine:latest
    container_name: conntrack-monitor
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
    volumes:
      - /proc:/proc:ro
    entrypoint: ["sh", "-c", "apk add --no-cache conntrack-tools && conntrack -E"]
```

### Connection Tracking Table Tuning

The kernel connection tracking table size is critical for high-traffic systems:

```bash
# Check current table size and usage
cat /proc/sys/net/netfilter/nf_conntrack_max
cat /proc/sys/net/netfilter/nf_conntrack_count

# Increase table size (e.g., to 262144)
sudo sysctl -w net.netfilter.nf_conntrack_max=262144

# Make persistent across reboots
echo "net.netfilter.nf_conntrack_max=262144" | sudo tee -a /etc/sysctl.d/99-conntrack.conf

# Adjust timeout values
sudo sysctl -w net.netfilter.nf_conntrack_tcp_timeout_established=432000
sudo sysctl -w net.netfilter.nf_conntrack_tcp_timeout_close_wait=60
```

## nftables — The Modern Firewall Framework

nftables is the modern replacement for iptables, ip6tables, arptables, and ebtables, consolidated into a single binary. It was introduced in Linux kernel 3.13 and has become the default on most modern distributions.

### Key Features

- **Unified syntax**: One tool for IPv4, IPv6, ARP, and bridge filtering
- **Sets and maps**: Efficient lookup tables for IP lists, port ranges, and NAT mappings
- **Atomic rule updates**: Replace entire rulesets without packet loss during transition
- **Built-in connection tracking**: Native `ct state` matching without separate modules
- **Better performance**: Single kernel binary, no per-protocol command variants
- **JSON/XML output**: Machine-readable rule listing for automation

### Installation

```bash
# Debian/Ubuntu (default since Debian 10)
sudo apt install nftables

# RHEL/Fedora (default since RHEL 8)
sudo dnf install nftables

# Arch Linux
sudo pacman -S nftables
```

### Stateful Firewall Configuration

```bash
#!/usr/sbin/nft -f

# Flush existing rules
flush ruleset

table inet firewall {
    chain input {
        type filter hook input priority 0; policy drop;

        # Allow established and related connections
        ct state established,related accept
        ct state invalid drop

        # Allow loopback
        iif lo accept

        # Allow SSH
        tcp dport 22 ct state new accept

        # Allow HTTP/HTTPS
        tcp dport { 80, 443 } ct state new accept

        # Allow ICMP (ping)
        ip protocol icmp accept
        ip6 nexthdr icmpv6 accept
    }

    chain forward {
        type filter hook forward priority 0; policy drop;

        # Allow forwarded traffic for established connections
        ct state established,related accept
        ct state invalid drop

        # Allow forwarding between internal networks
        ip saddr 192.168.1.0/24 ip daddr 10.0.0.0/8 accept
    }

    chain output {
        type filter hook output priority 0; policy accept;
    }
}
```

### NAT Configuration with Connection Tracking

```bash
table ip nat {
    chain prerouting {
        type nat hook prerouting priority -100;
        # Port forwarding: external:8080 -> internal:80
        tcp dport 8080 dnat to 192.168.1.10:80
    }

    chain postrouting {
        type nat hook postrouting priority 100;
        # Masquerade outgoing traffic
        oifname "eth0" masquerade
    }
}
```

### Connection Tracking in nftables Rules

```bash
# Count connections per source IP
nft add rule inet firewall forward ct state new     ct count over 100 drop

# Track specific protocol helpers
nft add rule inet firewall forward tcp dport 21 ct helper set "ftp"
```

## iptables — The Legacy Standard

iptables has been the Linux firewall standard for over two decades. While nftables is the recommended replacement, iptables remains deployed on millions of systems and is the default on many container images.

### Key Features

- **Mature ecosystem**: Extensive documentation, tutorials, and community knowledge
- **Container compatibility**: Most Docker images include iptables by default
- **Modular architecture**: Separate binaries for ipv4 (iptables), ipv6 (ip6tables), arp (arptables)
- **Connection tracking integration**: Uses `conntrack` module for stateful matching
- **Wide tooling support**: Many security tools generate iptables rules automatically

### Installation

```bash
# Debian/Ubuntu
sudo apt install iptables iptables-persistent

# RHEL/Fedora
sudo dnf install iptables iptables-services

# Arch Linux
sudo pacman -S iptables
```

### Stateful Firewall Configuration

```bash
#!/bin/bash

# Flush existing rules
iptables -F
iptables -X

# Default policies
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# Allow established and related connections
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A INPUT -m conntrack --ctstate INVALID -j DROP

# Allow loopback
iptables -A INPUT -i lo -j ACCEPT

# Allow SSH
iptables -A INPUT -p tcp --dport 22 -m conntrack --ctstate NEW -j ACCEPT

# Allow HTTP/HTTPS
iptables -A INPUT -p tcp -m multiport --dports 80,443 -m conntrack --ctstate NEW -j ACCEPT

# Allow ICMP
iptables -A INPUT -p icmp -j ACCEPT
```

### NAT Configuration

```bash
# Enable IP forwarding
echo 1 > /proc/sys/net/ipv4/ip_forward

# Masquerade outgoing traffic
iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE

# Port forwarding
iptables -t nat -A PREROUTING -p tcp --dport 8080 -j DNAT --to-destination 192.168.1.10:80
iptables -A FORWARD -p tcp -d 192.168.1.10 --dport 80 -j ACCEPT
```

### Connection Tracking Tuning

iptables relies on the same kernel conntrack subsystem as nftables, so tuning is identical:

```bash
# View connection tracking statistics
cat /proc/net/nf_conntrack | wc -l

# Monitor connection tracking events
conntrack -E
```

## Why Self-Host Your Connection Tracking Infrastructure?

Stateful connection tracking is fundamental to any self-hosted network security posture. Cloud firewalls and managed security groups often provide only basic port-based filtering, lacking the granular connection state awareness that `nf_conntrack` provides. By managing connection tracking directly on your Linux servers, you gain:

- **Protocol-aware filtering**: Understand FTP data channels, SIP sessions, and other multi-protocol connections
- **Connection limiting**: Prevent individual clients from exhausting server resources
- **NAT visibility**: Track exactly which internal hosts are using which external connections
- **Troubleshooting power**: Real-time connection event monitoring reveals network issues that packet captures alone cannot show

For comprehensive firewall management, see our [UFW vs firewalld vs iptables guide](../self-hosted-firewall-ufw-firewalld-iptables/). For firewall log analysis, our [FWLogwatch vs LogAnalyzer vs ULOGd comparison](../2026-05-12-self-hosted-firewall-log-analysis-fwlogwatch-loganalyzer-ulogd-guide/) covers centralized log monitoring. And for kernel-level security hardening, check our [Linux kernel security auditing guide](../2026-05-23-self-hosted-linux-kernel-security-auditing-kconfig-hardened-check-checksec-guide/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Connection Tracking: conntrack-tools vs nftables vs iptables",
  "description": "Compare conntrack-tools, nftables, and iptables for self-hosted Linux connection tracking and stateful firewall configuration. Includes Docker deployment and NAT setup guides.",
  "datePublished": "2026-05-23",
  "dateModified": "2026-05-23",
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

## FAQ

### What is the difference between conntrack-tools and iptables?

conntrack-tools manages the kernel's connection tracking table (querying, deleting, monitoring entries). iptables configures firewall rules that use the connection tracking table for stateful matching. They are complementary — iptables rules depend on the conntrack table, and conntrack-tools lets you inspect and manipulate that table.

### Should I migrate from iptables to nftables?

For new deployments, yes. nftables offers better performance, unified syntax, and is the future of Linux firewalling. However, iptables remains fully functional and receives security patches. If you have extensive iptables rulesets, migration requires careful testing — the `iptables-translate` tool can help convert rules to nftables syntax.

### How do I increase the connection tracking table size?

The table size is controlled by `net.netfilter.nf_conntrack_max` in sysctl. Set it to at least 4x your expected concurrent connections. For a busy web server handling 10,000 concurrent connections, set it to 65536 or higher: `sysctl -w net.netfilter.nf_conntrack_max=65536`.

### Can conntrack-tools synchronize connection state between two firewalls?

Yes, `conntrackd` provides high-availability connection tracking synchronization between two firewalls using a primary/backup or active/active model. It syncs the connection tracking table so that failover does not drop existing connections.

### Why are my connections being dropped with "nf_conntrack: table full"?

This means the connection tracking table has reached its maximum capacity. Either increase `nf_conntrack_max` or reduce the number of tracked connections by adding rules to skip tracking for high-volume traffic (using `NOTRACK` in iptables or `notrack` in nftables).

### Does connection tracking work with Docker?

Yes, Docker uses iptables (and increasingly nftables) for its network isolation. The connection tracking table tracks all container-to-container and container-to-host connections. High container counts can exhaust the conntrack table — monitor with `conntrack -C` and increase the limit if needed.
