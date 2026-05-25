---
title: "Self-Hosted DNS Resolver Configuration Management: resolvconf vs openresolv vs systemd-resolved"
date: "2026-05-25"
tags: ["dns", "networking", "linux", "systemd", "resolver"]
draft: false
---

The `/etc/resolv.conf` file is one of the most critical configuration files on any Linux server. It determines which DNS servers your system queries, which search domains are used for short hostname resolution, and how DNS queries are routed. Yet managing this file correctly — especially when multiple network interfaces, VPNs, containers, and virtual machines each want to modify DNS settings — is a persistent challenge in self-hosted infrastructure.

This guide compares three approaches to DNS resolver configuration management: **resolvconf** (the original Debian implementation), **openresolv** (the modern POSIX-compatible replacement), and **systemd-resolved** (the integrated systemd solution). We cover installation, configuration, hook integration, and deployment patterns for each.

## The resolv.conf Problem

On a simple server with a single network interface and static DNS, `/etc/resolv.conf` is straightforward:

```
nameserver 8.8.8.8
nameserver 8.8.4.4
search example.com
```

But in real-world self-hosted environments, multiple components compete to write to this file:

- **DHCP clients** — write DNS servers obtained from DHCP leases
- **VPNs** — add internal DNS servers when the tunnel connects
- **Containers** — Docker writes its own resolv.conf entries for container networking
- **Local DNS caches** — dnsmasq, unbound, or systemd-resolved want to be the first nameserver
- **Network managers** — NetworkManager, systemd-networkd, and connman each have their own DNS handling

Without a management framework, these components overwrite each other's changes, leading to broken DNS resolution, missing search domains, or queries going to the wrong server.

## resolvconf: The Original Implementation

resolvconf was created by Thomas Hood for Debian to solve the multiple-writer problem. It provides a framework where network services register their DNS requirements, and resolvconf computes the optimal `/etc/resolv.conf` content.

### resolvconf Architecture

resolvconf works via a nameserver information registry. Services write DNS data to named pipes in `/etc/resolvconf/resolv.conf.d/`:

```bash
# Add DNS configuration from a DHCP client
echo "nameserver 192.168.1.1
search example.com" | resolvconf -a eth0.dhcp

# Add DNS configuration from a VPN
echo "nameserver 10.0.0.53
search internal.example.com" | resolvconf -a tun0.vpn

# Remove DNS configuration when interface goes down
resolvconf -d eth0.dhcp

# View current configuration
resolvconf -l
```

### resolvconf Configuration

The main configuration file `/etc/resolvconf.conf` controls behavior:

```bash
# /etc/resolvconf.conf
# Enable name server caching
name_server_cache=yes

# Maximum number of name servers to write
max_name_servers=3

# Search domain configuration
search_domains="example.com internal.example.com"

# Never include these nameservers
exclude_name_servers="127.0.0.1"

# Run update hook after changes
update_hook="/usr/local/sbin/resolvconf-update-hook"
```

### resolvconf Hook System

One of resolvconf's strengths is its hook system. When `/etc/resolv.conf` changes, resolvconf can trigger actions:

```bash
# /etc/resolvconf/update.d/restart-services
#!/bin/sh
# Restart services that depend on DNS
systemctl reload unbound
systemctl reload nginx
```

### Docker Compose with resolvconf

For containers that need to participate in the resolvconf-managed DNS:

```yaml
version: "3.8"
services:
  dns-register:
    image: alpine:latest
    network_mode: host
    volumes:
      - /sbin/resolvconf:/sbin/resolvconf
    environment:
      - INTERFACE=docker0
      - NAMESERVER=172.17.0.1
    command: >
      sh -c "echo 'nameserver $$NAMESERVER' | /sbin/resolvconf -a docker0.container &&
             trap '/sbin/resolvconf -d docker0.container' EXIT &&
             sleep infinity"
    restart: unless-stopped
```

## openresolv: The Modern POSIX Implementation

openresolv, written by Roy Marples (also the author of dhcpcd), is a clean-room reimplementation of resolvconf with a simpler design and better POSIX compatibility. It is the default resolvconf implementation on many modern distributions including Alpine Linux, Arch Linux, and Gentoo.

### openresolv Configuration

Configuration is in `/etc/resolvconf.conf`:

```bash
# /etc/resolvconf.conf
# Write to this file
RESOLVCONF=yes

# Generate resolv.conf
RESOLV_CONF="/etc/resolv.conf"

# Helper programs
LIBC_RESOLVER="yes"

# Subscribers: programs that consume DNS info
SUBSCRIBERS="unbound dnsmasq"

# Unbound subscriber config
unbound_conf="/etc/unbound/resolvconf.conf"

# Maximum name servers
name_servers_max=3

# Search domain order
search_domains="example.com"

# Private search domains (only for specific interfaces)
private_search_domains="internal.example.com"
```

### openresolv Subscribers

openresolv uses a subscriber model — services register to receive DNS updates:

```bash
# List registered subscribers
resolvconf --subscribers

# Add DNS info for an interface
resolvconf -a eth0 <<EOF
nameserver 192.168.1.1
search example.com
EOF

# Remove interface DNS info
resolvconf -d eth0

# List all registered interfaces
resolvconf -l
```

### openresolv with dnsmasq Integration

A common pattern is using openresolv to feed DNS server information to a local dnsmasq cache:

```bash
# /etc/resolvconf.conf
SUBSCRIBERS="dnsmasq"
dnsmasq_conf="/etc/dnsmasq-resolvconf.conf"
dnsmasq_service="dnsmasq"

# Then /etc/resolv.conf points to local dnsmasq
# nameserver 127.0.0.1
```

The dnsmasq subscriber writes upstream DNS servers to `/etc/dnsmasq-resolvconf.conf`:

```
# Generated by openresolv
server=192.168.1.1
server=8.8.8.8
```

### Docker Compose with openresolv

```yaml
version: "3.8"
services:
  dnsmasq-local:
    image: jpillora/dnsmasq
    network_mode: host
    volumes:
      - /etc/dnsmasq.conf:/etc/dnsmasq.conf:ro
      - /etc/dnsmasq-resolvconf.conf:/etc/dnsmasq-resolvconf.conf
    restart: unless-stopped

  openresolv-registrar:
    image: alpine:latest
    network_mode: host
    volumes:
      - /usr/sbin/resolvconf:/usr/sbin/resolvconf
      - /etc/resolvconf.conf:/etc/resolvconf.conf
    command: >
      sh -c "/usr/sbin/resolvconf -a docker0 <<'EOF'
nameserver 172.17.0.1
search docker.internal
EOF
      sleep infinity"
    restart: unless-stopped
```

## systemd-resolved: The Integrated Solution

systemd-resolved is a network name resolution manager included in systemd. It provides a local DNS stub resolver on 127.0.0.53, DNSSEC validation, DNS-over-TLS support, and per-link DNS configuration.

### systemd-resolved Configuration

```ini
# /etc/systemd/resolved.conf
[Resolve]
# Global DNS servers (fallback)
DNS=8.8.8.8 1.1.1.1
FallbackDNS=9.9.9.9 8.8.4.4

# Default search domain
Domains=~.

# DNSSEC validation
DNSSEC=allow-downgrade

# DNS-over-TLS
DNSOverTLS=opportunistic

# Cache size
Cache=yes
DNSStubListener=yes
```

### Per-Interface DNS Configuration

systemd-resolved's key advantage is per-link DNS configuration through systemd-networkd:

```ini
# /etc/systemd/network/20-eth0.network
[Match]
Name=eth0

[Network]
DHCP=yes
DNS=192.168.1.1
Domains=example.com

[DHCP]
UseDNS=yes
UseDomains=yes
```

### resolv.conf with systemd-resolved

When systemd-resolved is active, `/etc/resolv.conf` should be a symlink to the stub resolver:

```bash
# Create the symlink
ln -sf /run/systemd/resolve/stub-resolv.conf /etc/resolv.conf

# Or use the full resolv.conf with all configured servers
ln -sf /run/systemd/resolve/resolv.conf /etc/resolv.conf

# Check resolution status
resolvectl status
resolvectl query example.com
```

### Docker Integration with systemd-resolved

Docker containers inherit DNS from the host's resolv.conf. When systemd-resolved manages `/etc/resolv.conf` via the stub resolver (127.0.0.53), containers cannot reach it. The workaround is to use the full resolv.conf symlink:

```yaml
version: "3.8"
services:
  web:
    image: nginx:alpine
    dns:
      - 192.168.1.1
      - 8.8.8.8
    dns_search:
      - example.com
    ports:
      - "80:80"
    restart: unless-stopped
```

## Comparison Table

| Feature | resolvconf | openresolv | systemd-resolved |
|---------|-----------|------------|-----------------|
| **Origin** | Debian (Thomas Hood) | Roy Marples (dhcpcd author) | systemd project |
| **Package Size** | ~50 KB | ~30 KB | Part of systemd |
| **POSIX Compliance** | Partial | Full | N/A (systemd-specific) |
| **DNSSEC** | No | No | Built-in |
| **DNS-over-TLS** | No | No | Built-in (opportunistic/full) |
| **Per-Link DNS** | Via interface tags | Via interface tags | Native (per .network file) |
| **Local Stub Resolver** | No | No | Yes (127.0.0.53) |
| **Subscriber Model** | Hook scripts | Named subscribers | Integrated with networkd |
| **Caching** | No | No | Built-in LRU cache |
| **mDNS/LLMNR** | No | No | Built-in support |
| **Default On** | Debian 9-11, Ubuntu 16.04 | Alpine, Arch, Gentoo | Ubuntu 18.04+, Fedora, RHEL 9 |
| **VPN Integration** | Good (resolvconf -a/-d) | Good (resolvconf -a/-d) | Via resolved's per-link config |

## Choosing the Right DNS Resolver Manager

**Use resolvconf when:**
- You are on Debian/Ubuntu and want the traditional, well-tested approach
- Your scripts and hooks already depend on the resolvconf interface
- You need compatibility with legacy network management tools

**Use openresolv when:**
- You want a cleaner, simpler implementation with fewer dependencies
- You are on Alpine Linux, Arch Linux, or Gentoo
- You need the subscriber model for dnsmasq/unbound integration
- You prefer POSIX compliance and clean design

**Use systemd-resolved when:**
- Your system runs systemd (most modern Linux distributions)
- You want DNSSEC validation and DNS-over-TLS without additional packages
- You use systemd-networkd for network configuration
- You need per-interface DNS configuration with automatic failover
- You want built-in DNS caching and mDNS/LLMNR support

## Security Best Practices for DNS Resolver Configuration

- **DNSSEC validation** — Enable DNSSEC to prevent DNS spoofing attacks. systemd-resolved provides this natively; for resolvconf/openresolv, integrate with unbound or dnsmasq with DNSSEC enabled.
- **DNS-over-TLS** — Encrypt DNS queries between your server and upstream resolvers. systemd-resolved supports this natively. For openresolv, configure stubby or dnsmasq as a TLS-capable local resolver.
- **Restrict resolv.conf writes** — Use file permissions (`chmod 644 /etc/resolv.conf`) and the immutable flag (`chattr +i`) only for static configurations — not when using a management framework.
- **Monitor DNS changes** — Use `inotifywait -m /etc/resolv.conf` to detect unauthorized modifications to the resolver configuration.

## Why Self-Host DNS Resolver Configuration Management?

In self-hosted infrastructure, DNS resolution is foundational. Every service lookup, every package repository fetch, every container pull, and every inter-service communication depends on correct DNS configuration. When multiple network services — DHCP clients, VPNs, local caches, and container runtimes — all compete to modify `/etc/resolv.conf`, a management framework prevents configuration conflicts and ensures consistent resolution behavior.

For organizations running internal DNS infrastructure, the resolver management layer is the bridge between upstream authoritative DNS servers and local service discovery. Proper configuration ensures that internal domains resolve correctly while external queries use trusted upstream resolvers.

For related reading on DNS infrastructure, see our [DNS resolver server comparison](../2026-05-30-self-hosted-dns-resolver-management-unbound-knot-resolver-powerdns-recursor-guide/) for the server-side perspective, and our [DNS firewall guide](../2026-04-21-self-hosted-dns-firewall-rpz-unbound-powerdns-bind9-knot-guide-2026/) for DNS-level security filtering.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DNS Resolver Configuration Management: resolvconf vs openresolv vs systemd-resolved",
  "description": "Manage /etc/resolv.conf on self-hosted servers with resolvconf, openresolv, or systemd-resolved. DNS resolver configuration, hooks, and deployment.",
  "datePublished": "2026-05-25",
  "dateModified": "2026-05-25",
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

### What is the difference between resolvconf and openresolv?

resolvconf is the original Debian implementation by Thomas Hood. openresolv is a clean-room reimplementation by Roy Marples with simpler configuration, better POSIX compatibility, and a subscriber model for services like dnsmasq and unbound. Both use the same command-line interface (`resolvconf -a` and `resolvconf -d`), making them largely drop-in replacements for each other.

### Why does systemd-resolved use 127.0.0.53?

systemd-resolved runs a local DNS stub resolver at 127.0.0.53:53. This address is a special systemd-reserved address that allows `/etc/resolv.conf` to point to the local resolver while systemd-resolved forwards queries to the actual configured upstream DNS servers. This enables features like DNSSEC validation, DNS-over-TLS, and per-link DNS configuration transparently.

### How do I configure DNS-over-TLS with openresolv?

openresolv itself does not support DNS-over-TLS. Instead, configure a local DNS resolver like stubby or dnsmasq with TLS support, then have openresolv feed upstream server information to it. Set `/etc/resolv.conf` to point to `127.0.0.1` (the local resolver), and configure the resolver's subscriber hook in `/etc/resolvconf.conf`.

### Can I use systemd-resolved without systemd-networkd?

Yes. systemd-resolved works independently of systemd-networkd. You can configure DNS servers in `/etc/systemd/resolved.conf` and use any network manager (NetworkManager, dhcpcd, etc.) to manage interfaces. However, the per-link DNS configuration feature requires systemd-networkd or NetworkManager with resolved integration.

### How do I troubleshoot DNS resolution with systemd-resolved?

Use `resolvectl status` to see the current DNS configuration per interface, `resolvectl query example.com` to test resolution, and `journalctl -u systemd-resolved -f` for real-time logs. The `resolvectl statistics` command shows cache hit rates and query counts.

### What happens when resolvconf has conflicting DNS configurations from multiple interfaces?

resolvconf and openresolv both use an interface ordering system. Each interface's DNS configuration is tagged with a metric (interface order), and the resulting `/etc/resolv.conf` combines all nameservers with higher-priority interfaces listed first. Search domains from all interfaces are merged. Use `resolvconf -l` to see all registered configurations.

