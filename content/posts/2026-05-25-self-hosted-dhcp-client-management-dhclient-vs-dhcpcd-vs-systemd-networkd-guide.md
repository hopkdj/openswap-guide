---
title: "Self-Hosted DHCP Client Management: dhclient vs dhcpcd vs systemd-networkd"
date: "2026-05-25"
tags: ["dhcp", "networking", "linux", "systemd", "self-hosted"]
draft: false
---

DHCP clients are the often-overlooked counterpart to DHCP servers. While server management gets plenty of attention, the client side — responsible for obtaining and maintaining IP address leases, DNS configuration, and routing information — is equally critical for server infrastructure. Whether you are running bare-metal servers, virtual machines, or containers, the choice of DHCP client affects boot times, network reliability, DNS resolver integration, and overall system stability.

This guide compares three widely-used DHCP client solutions: **ISC dhclient** (the traditional choice), **dhcpcd** (the modern standalone client), and **systemd-networkd's built-in DHCP client** (the integrated approach). We will examine configuration, lease management, DNS integration, and deployment patterns for each.

## Understanding DHCP Client Roles

A DHCP client does much more than request an IP address. On a self-hosted server, the client must:

- **Obtain IP configuration** — address, subnet mask, gateway, lease duration
- **Manage DNS resolver settings** — populate `/etc/resolv.conf` with nameserver IPs and search domains
- **Handle lease renewal** — renegotiate before expiry, gracefully release on shutdown
- **Support IPv6** — DHCPv6, SLAAC (Stateless Address Auto Configuration), and RA (Router Advertisement)
- **Execute hooks** — run custom scripts on lease acquisition, renewal, or expiration
- **Fallback behavior** — what happens when the DHCP server is unreachable (APIPA/IPv4LL)

The right client depends on your infrastructure: are you running a fleet of identical servers with predictable networking? A mix of static and dynamic hosts? Do you need tight integration with systemd-resolved? Each client answers these questions differently.

## ISC dhclient: The Traditional Choice

ISC dhclient has been the default DHCP client on most Linux distributions for over two decades. It ships as part of the ISC DHCP suite, which also includes the DHCP server and relay agent.

### dhclient Configuration

The main configuration file is `/etc/dhcp/dhclient.conf`. Here is a typical server-side configuration:

```bash
# /etc/dhcp/dhclient.conf
interface "eth0" {
  send host-name "myserver";
  send dhcp-client-identifier "01:aa:bb:cc:dd:ee:ff";
  request subnet-mask, broadcast-address, time-offset, routers,
        domain-name, domain-name-servers, domain-search,
        host-name, dhcp6.name-servers, dhcp6.domain-search;
  require subnet-mask, domain-name-servers;
  timeout 60;
  retry 60;
  reboot 10;
  select-timeout 5;
  initial-interval 2;
}
```

### dhclient Lease Renewal

dhclient runs as a daemon in foreground mode or via init scripts. Lease renewal happens automatically based on T1 (50% of lease time) and T2 (87.5%) timers:

```bash
# Start dhclient in background for eth0
dhclient -v eth0

# Release current lease
dhclient -r eth0

# Run in foreground for debugging
dhclient -d -v eth0
```

### Docker Deployment

While dhclient is typically installed via packages, you can run it in a container for network namespace management:

```yaml
version: "3.8"
services:
  dhcp-client:
    image: alpine:latest
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - /etc/dhcp/dhclient.conf:/etc/dhcp/dhclient.conf:ro
      - /var/lib/dhcp:/var/lib/dhcp
    command: dhclient -v -cf /etc/dhcp/dhclient.conf eth0
    restart: unless-stopped
```

## dhcpcd: The Modern Standalone Client

dhcpcd (DHCP Client Daemon) is a lightweight, standards-compliant DHCP client written by Roy Marples. It supports DHCP, DHCPv6, IPv4LL (Zeroconf), and IPv6SLAAC in a single daemon. It is the default on Raspbian/Raspberry Pi OS and available on most distributions.

### dhcpcd Configuration

The configuration file `/etc/dhcpcd.conf` uses a simple key-value syntax:

```bash
# /etc/dhcpcd.conf
hostname
clientid
persistent
option rapid_commit
option domain_name_servers, domain_name, domain_search, host_name
option classless_static_routes
option ntp_servers
option interface_mtu

# Static fallback if DHCP fails
interface eth0
  fallback static_eth0
  option domain_name_servers 8.8.8.8 8.8.4.4

# Profile for static configuration
profile static_eth0
  static ip_address=192.168.1.100/24
  static routers=192.168.1.1
  static domain_name_servers=8.8.8.8 8.8.4.4
```

### dhcpcd Features

dhcpcd includes several advantages over dhclient:

- **Built-in IPv4LL support** — automatically assigns a 169.254.x.x address when no DHCP server responds
- **Hook system** — extensible via `/lib/dhcpcd/dhcpcd-hooks/` with shell scripts
- **DUID support** — persistent client identifiers for DHCPv6
- **Low resource usage** — typically uses less memory than dhclient
- **Arping conflict detection** — verifies address uniqueness before accepting a lease

```bash
# Start dhcpcd
dhcpcd eth0

# View current lease information
dhcpcd --dumplease eth0

# Get specific option from lease
dhcpcd --gethostname eth0
```

### Docker Compose Setup

```yaml
version: "3.8"
services:
  dhcpcd-manager:
    image: alpine:latest
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - /etc/dhcpcd.conf:/etc/dhcpcd.conf:ro
      - /var/lib/dhcpcd:/var/lib/dhcpcd
    command: dhcpcd --foreground --noipv4ll eth0
    restart: unless-stopped
```

## systemd-networkd: The Integrated Approach

systemd-networkd is a network configuration manager included in systemd. Its built-in DHCP client eliminates the need for a separate daemon and integrates natively with systemd-resolved for DNS management.

### systemd-networkd Configuration

Network interfaces are configured via `.network` files in `/etc/systemd/network/`:

```ini
# /etc/systemd/network/20-dhcp.network
[Match]
Name=eth0

[Network]
DHCP=yes
IPv6PrivacyExtensions=yes

[DHCP]
ClientIdentifier=mac
UseDNS=yes
UseDomains=yes
UseHostname=yes
UseNTP=yes
RouteMetric=100
SendHostname=yes
Hostname=myserver
```

### systemd-networkd DNS Integration

The key advantage of systemd-networkd is its seamless integration with systemd-resolved:

```ini
# /etc/systemd/network/20-dhcp.network
[DHCP]
UseDNS=yes
UseDomains=yes

# /etc/systemd/resolved.conf
[Resolve]
DNS=8.8.8.8 8.8.4.4
FallbackDNS=1.1.1.1
Domains=~.
DNSSEC=allow-downgrade
DNSOverTLS=opportunistic
```

### Managing systemd-networkd

```bash
# Enable and start
systemctl enable systemd-networkd
systemctl start systemd-networkd

# View network status
networkctl status eth0

# Renew DHCP lease
networkctl renew eth0

# Reconfigure all interfaces
networkctl reload
```

### Docker Deployment Pattern

systemd-networkd is typically not run in containers (it requires systemd as init). However, for container hosts using Docker with systemd-networkd:

```yaml
# docker-compose.yml for services on a systemd-networkd host
version: "3.8"
services:
  web:
    image: nginx:alpine
    ports:
      - "80:80"
    networks:
      appnet:
        ipv4_address: 172.20.0.10

networks:
  appnet:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

## Comparison Table

| Feature | ISC dhclient | dhcpcd | systemd-networkd |
|---------|-------------|--------|-----------------|
| **Package Size** | ~200 KB | ~150 KB | Part of systemd |
| **IPv4LL/Zeroconf** | No (requires avahi-autoipd) | Built-in | Built-in |
| **IPv6/DHCPv6** | Yes | Yes | Yes |
| **SLAAC Support** | Limited | Full | Full |
| **DNS Integration** | resolvconf scripts | resolvconf scripts | Native systemd-resolved |
| **Hook System** | /etc/dhcp/dhclient-enter-hooks.d/ | /lib/dhcpcd/dhcpcd-hooks/ | networkd-dispatcher |
| **Static Fallback** | Manual script required | Built-in fallback profiles | Multiple .network files |
| **DUID Support** | Yes | Yes | Yes |
| **Resource Usage** | Moderate | Low | Low |
| **Active Development** | Limited (ISC EOL) | Active | Active (systemd project) |
| **Default On** | RHEL/CentOS 7, Debian 9 | Raspberry Pi OS, Alpine | Ubuntu 18.04+, Fedora |

## Choosing the Right DHCP Client

**Use ISC dhclient when:**
- You need maximum compatibility with legacy DHCP servers
- Your infrastructure relies on custom dhclient scripts and hooks
- You are on a distribution where it is the default and changing it adds risk

**Use dhcpcd when:**
- You want a lightweight, standalone client with IPv4LL fallback
- You need simple static fallback profiles without extra scripting
- You run Raspberry Pi, Alpine Linux, or other minimal distributions

**Use systemd-networkd when:**
- Your system already runs systemd (most modern Linux distributions)
- You want native DNS integration with systemd-resolved
- You prefer declarative configuration over scripting
- You manage both physical and virtual network interfaces uniformly

## Security Considerations

Regardless of which DHCP client you choose, consider these security measures:

- **Client identifiers** — Use MAC-based or DUID-based identifiers, not random ones, for audit trails
- **DHCP snooping** — On managed switches, enable DHCP snooping to prevent rogue DHCP servers
- **Option 82** — Configure relay agents to insert circuit information for lease tracking
- **Firewall rules** — Restrict DHCP traffic (UDP 67/67) to trusted interfaces only
- **Lease validation** — Verify that obtained DNS servers are expected addresses before updating resolv.conf

## Why Self-Host Your DHCP Client Configuration?

While cloud instances typically handle DHCP configuration automatically, self-hosted infrastructure requires deliberate DHCP client management. On bare-metal servers, the DHCP client is your primary network bootstrap mechanism — it runs before any configuration management tool, before any monitoring agent, before any application starts.

Proper DHCP client configuration ensures your servers always have correct DNS resolution, proper routing, and reliable network connectivity even when upstream infrastructure changes. For organizations running hybrid infrastructure (mixing cloud and bare-metal), consistent DHCP client behavior across all server types simplifies troubleshooting and reduces configuration drift.

For DHCP server management, see our [DHCP server comparison](../2026-05-04-self-hosted-dhcp-server-management-kea-dnsmasq-isc-dhcp-guide/). If you need high availability for your DHCP infrastructure, check our [DHCP HA guide](../2026-05-09-self-hosted-dhcp-high-availability-kea-ha-vs-isc-dhcp-vs-keepalived-guide/). For DNS resolver configuration on the server side, our [DNS resolver management guide](../2026-05-30-self-hosted-dns-resolver-management-unbound-knot-resolver-powerdns-recursor-guide/) covers the authoritative and recursive side.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DHCP Client Management: dhclient vs dhcpcd vs systemd-networkd",
  "description": "Compare ISC dhclient, dhcpcd, and systemd-networkd for DHCP client management on self-hosted Linux servers. Configuration, lease management, and deployment patterns.",
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

### What is the difference between dhclient and dhcpcd?

dhclient is the ISC DHCP client, part of the broader ISC DHCP suite. It is feature-rich but heavier and ISC has shifted focus away from the classic DHCP suite. dhcpcd is a standalone, lightweight client with built-in IPv4LL (link-local) support, simpler configuration syntax, and active development. dhcpcd also includes automatic conflict detection via ARP before accepting a lease.

### Is systemd-networkd's DHCP client production-ready?

Yes. systemd-networkd's DHCP client is used by default on Ubuntu, Fedora, and many other modern distributions in production environments. It supports DHCPv4, DHCPv6, SLAAC, and integrates natively with systemd-resolved for DNS management. It is well-tested and actively maintained as part of the systemd project.

### How do I set a static IP fallback with DHCP clients?

With dhcpcd, use the `fallback` directive in `/etc/dhcpcd.conf` to define a static profile. With systemd-networkd, create a separate `.network` file with `DHCP=no` and static addressing that matches when DHCP fails. With dhclient, you need a custom script that checks for lease failure and configures a static address manually.

### Can I run multiple DHCP clients on the same interface?

No — running multiple DHCP clients on the same interface causes conflicts as they will both try to manage the IP address and routing table. Choose one client per interface. However, you can use different clients on different interfaces (e.g., systemd-networkd for eth0 and dhcpcd for wlan0).

### How do I troubleshoot DHCP client issues?

Use `dhclient -d -v eth0` for verbose dhclient output, `dhcpcd --debug eth0` for dhcpcd debugging, and `journalctl -u systemd-networkd -f` for systemd-networkd logs. Check `/var/lib/dhcp/dhclient.leases` or `/var/lib/dhcpcd/` for stored lease information. Verify that UDP ports 67 and 68 are not blocked by firewall rules.

### Does dhcpcd support DHCPv6?

Yes, dhcpcd supports both DHCPv4 and DHCPv6 in a single daemon. It handles SLAAC (Stateless Address Auto Configuration) and DHCPv6-PD (Prefix Delegation) for routing scenarios. Enable IPv6 with `ipv6rs` and `slaac` options in the dhcpcd.conf configuration.

