---
title: "Self-Hosted Firewall Management: FireHOL vs Shorewall vs ferm"
date: "2026-05-08"
tags: ["firewall", "security", "iptables", "nftables", "network-security", "self-hosted"]
draft: false
---

Managing Linux firewall rules with raw iptables or nftables commands is tedious and error-prone. Firewall management tools provide a higher-level abstraction, making it easier to define, maintain, and deploy complex firewall policies. In this guide, we compare three mature open-source firewall management frameworks: **FireHOL**, **Shorewall**, and **ferm**.

## Overview

| Feature | FireHOL | Shorewall | ferm |
|---------|---------|-----------|------|
| **GitHub Stars** | 1,591 | N/A (shorewall.org) | N/A (foo-projects.org) |
| **Backend** | iptables/nftables | iptables/nftables | iptables/nftables |
| **Config Language** | Declarative DSL | Zone-based rules | C-like syntax |
| **Learning Curve** | Easy | Moderate | Moderate |
| **IPv6 Support** | Yes | Yes | Yes |
| **NAT Support** | Yes | Yes | Yes |
| **Bridge Filtering** | Yes | Yes | Yes |
| **Last Updated** | 2026-03 | 2026-04 | 2024-01 |
| **Package Availability** | Debian, Ubuntu, Alpine | Debian, Ubuntu, RHEL | Debian, Ubuntu |

## What Is FireHOL?

FireHOL describes itself as "a firewall for humans." It uses a simple, declarative configuration language that focuses on what you want to allow rather than how to implement it. FireHOL generates iptables/nftables rules from human-readable configuration files.

### Key Features

- **Service-centric configuration**: Define rules by service name (e.g., `server ssh accept`)
- **Auto-generated rules**: Handles RELATED/ESTABLISHED connections automatically
- **IP set support**: Integrates with ipset for efficient large ACLs
- **IDS integration**: Built-in support for snort, suricata, and fail2ban
- **Dynamic DNS**: Supports dynamic IP updates for remote hosts

### Installation

```bash
# Debian/Ubuntu
sudo apt install firehol

# RHEL/CentOS
sudo dnf install firehol

# Alpine
sudo apk add firehol
```

### Example Configuration

FireHOL configuration lives in `/etc/firehol/firehol.conf`:

```bash
#!/usr/bin/env firehol

interface eth0 internet
    policy drop
    protection strong 10/sec 10

    server ssh accept
    server http accept
    server https accept
    server dns accept
    server smtp accept

    client all accept
```

### Docker Deployment

```yaml
version: "3.8"
services:
  firehol:
    image: linuxserver/firehol:latest
    container_name: firehol
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./config:/config
      - /etc/firehol:/etc/firehol:ro
    restart: unless-stopped
```

## What Is Shorewall?

Shorewall is one of the oldest and most widely used firewall management tools. It uses a zone-based model where you define networks as zones and set policies between them.

### Key Features

- **Zone-based architecture**: Define zones (net, loc, dmz, fw) and policies between them
- **Macro system**: Reusable rule templates for common services
- **Blinding**: Automatic protection against IP spoofing
- **Traffic shaping**: Integrated tc-based QoS support
- **Multi-interface support**: Handles complex multi-NIC configurations
- **Blacklist/maclist**: Built-in MAC and IP blacklist support

### Installation

```bash
sudo apt install shorewall
```

### Example Configuration

**zones:**
```
fw       firewall
net      ipv4
loc      ipv4
dmz      ipv4
```

**policy:**
```
fw         net     ACCEPT
loc        fw      ACCEPT
net        fw      DROP      info
loc        net     ACCEPT
net        all     DROP      info
all        all     REJECT    info
```

**rules:**
```
ACCEPT     net       fw      tcp      22
ACCEPT     net       fw      tcp      80
ACCEPT     net       fw      tcp      443
```

## What Is ferm?

ferm (For Easy Rule Making) is a firewall rule management tool that uses a C-like configuration language. It supports variables, functions, and loops, making it highly programmable.

### Key Features

- **C-like syntax**: Familiar programming constructs (if, for, while, functions)
- **Variables and functions**: Define reusable rule blocks
- **Domain abstraction**: Group rules by purpose rather than interface
- **Include support**: Split configuration into modular files
- **IPv4/IPv6 unified**: Single configuration for both protocols

### Example Configuration

```perl
$EXT_IF = "eth0";
$SSH_PORT = 22;
$WEB_PORTS = (80 443);

table filter {
    chain INPUT {
        policy DROP;
        interface lo ACCEPT;
        mod state state (ESTABLISHED RELATED) ACCEPT;
        proto tcp dport $SSH_PORT ACCEPT;
        proto tcp dport $WEB_PORTS ACCEPT;
        proto icmp limit rate 10/second ACCEPT;
    }
    chain FORWARD { policy DROP; }
    chain OUTPUT { policy ACCEPT; }
}

table nat {
    chain POSTROUTING {
        outface $EXT_IF masquerade;
    }
}
```

## Choosing the Right Firewall Manager

**Choose FireHOL if:** You want the simplest possible configuration syntax and prefer service-centric rule definition with automatic RELATED/ESTABLISHED handling.

**Choose Shorewall if:** You have a multi-zone network (net, loc, dmz, fw) and need integrated traffic shaping with zone-based policy management.

**Choose ferm if:** You want programmatic control over rules with variables, loops, and functions in a C-like configuration syntax.

## Security Best Practices for Self-Hosted Firewalls

### 1. Default Deny Policy

Always set the default INPUT policy to DROP and explicitly allow only required services.

### 2. Rate Limiting

Protect against brute-force attacks by rate-limiting SSH and other sensitive services:

```bash
server ssh accept limit 3/min burst 3
```

### 3. Regular Rule Auditing

Periodically review your firewall rules:

```bash
sudo iptables -L -n -v
sudo firehol try
sudo shorewall check
```

## Why Self-Host Your Firewall Management?

Running your own firewall management tool gives you complete control over network security policies without relying on cloud-based firewall services. Self-hosted firewall tools process all traffic locally, eliminating any concern about rule data leaving your network.

For organizations managing multiple servers, centralized firewall configuration ensures consistent security policies across your infrastructure. Tools like FireHOL and Shorewall support configuration management integration, allowing you to version-control firewall rules alongside your other infrastructure-as-code repositories.

If you are looking to secure other self-hosted services, our guide on [self-hosted zero-trust network access](../headscale-vs-netbird-vs-openziti-self-hosted-zero-trust-network-access-ztna-guide/) covers ZTNA solutions. For container-level security, check our [container runtime security comparison](../kubearmor-vs-falco-vs-tetragon-runtime-security-guide/). And for comprehensive vulnerability scanning, our [open-source vulnerability scanner guide](../openvas-trivy-grype-self-hosted-vulnerability-scanner-guide/) covers network-level threat detection.

## Advanced Firewall Configuration Patterns

### Stateful Connection Tracking

All three tools support stateful connection tracking, which allows return traffic for established connections without explicit rules. FireHOL handles this automatically with every rule. Shorewall includes RELATED,ESTABLISHED traffic by default in its policy system. ferm requires explicit state tracking with the `mod state state (ESTABLISHED RELATED) ACCEPT` rule.

### Multi-Homed Firewall Setup

For servers with multiple network interfaces, each tool handles zone separation differently. FireHOL uses interface declarations with separate policies per interface. Shorewall defines zones in a dedicated zones file and sets policies between zone pairs. ferm uses chain-based rule organization with inface selectors to match specific interfaces.

### Integration with Fail2ban

All three tools can integrate with fail2ban for dynamic IP blocking. FireHOL includes built-in protection directives that work alongside fail2ban. Shorewall uses blacklist files that fail2ban can update. ferm can reference ipset collections that fail2ban populates with banned addresses.

## Network Segmentation with Firewall Rules

Proper network segmentation is essential for security. Use firewall rules to create isolation between different network segments including DMZ zones for public-facing services, internal zones for application servers with controlled database access, management zones restricted for administrative functions only, and database zones only accessible from application servers on specific ports.

Each firewall tool supports these patterns through different mechanisms — FireHOL through interface declarations, Shorewall through zone definitions, and ferm through chain-based rule organization. Self-hosted firewall management eliminates vendor lock-in since all three tools work with standard Linux iptables and nftables, the same foundation used by every major cloud provider.


## FAQ

### What is the difference between FireHOL, Shorewall, and ferm?

FireHOL uses a service-centric declarative language where you define which services to allow on each interface. Shorewall uses a zone-based model where you define networks as zones and set policies between them. ferm uses a C-like programming syntax with variables, functions, and loops for maximum programmability.

### Can I use FireHOL with nftables?

Yes. FireHOL supports both iptables and nftables backends. Set `FIREHOL_USE_NFTABLES=1` in the configuration to use nftables. Modern versions default to nftables where available.

### Is Shorewall still maintained?

Yes. Shorewall 5.3 is actively maintained with regular updates. The project website at shorewall.org provides the latest releases and documentation. The tool is available in all major Linux distribution repositories.

### Does ferm support IPv6?

Yes. ferm supports both IPv4 and IPv6 in a single configuration file. Use `domain ip` for IPv4 rules, `domain ip6` for IPv6 rules, or omit the domain to apply rules to both.

### Can I run these tools in Docker containers?

Yes, but with caveats. Firewall management tools need NET_ADMIN and NET_RAW capabilities and typically require host network mode to affect the host firewall. Running them in containers is primarily useful for testing configurations before deploying on bare metal.

### Which firewall manager is easiest for beginners?

FireHOL has the simplest learning curve. Its service-centric syntax is intuitive — you just declare which services to accept on each interface. Shorewall requires understanding zones and policies, while ferm requires basic programming knowledge.

### How do I test firewall rules before applying them?

FireHOL includes a built-in `firehol try` command that applies rules temporarily and reverts them if you do not confirm within 30 seconds. Shorewall has `shorewall check` for syntax validation and `shorewall try` for temporary rule application.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Firewall Management: FireHOL vs Shorewall vs ferm",
  "description": "Compare three open-source firewall management tools: FireHOL, Shorewall, and ferm. Learn their configuration approaches, Docker deployment, and when to use each.",
  "datePublished": "2026-05-08",
  "dateModified": "2026-05-08",
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
