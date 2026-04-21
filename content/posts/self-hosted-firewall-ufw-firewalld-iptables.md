---
title: "UFW vs Firewalld vs iptables: Best Linux Firewall for Self-Hosted Servers 2026"
date: 2026-04-12
tags: ["comparison", "guide", "self-hosted", "security", "networking"]
draft: false
description: "Compare UFW, Firewalld, and iptables for securing self-hosted servers. Includes Docker integration, configuration examples, and a decision guide for 2026."
---

## Why a Proper Firewall Is Non-Negotiable for Self-Hosted Servers

Every self-hosted server is exposed to the internet — and the internet is noisy. Within minutes of connecting a fresh VPS, you'll see SSH brute-force attempts, port scans, and automated exploit probes in your logs. A properly configured firewall is your first and most critical line of defense.

Linux offers three mainstream firewall management tools: **UFW** (Uncomplicated Firewall), **Firewalld**, and raw **iptables** (now transitioning to **nftables**). Each has a different philosophy, feature set, and learning curve. If you're running services like Jellyfin, [nextcloud](https://nextcloud.com/), Gitea, or a mail server, choosing the right firewall tool and configuring it correctly is essential.

This guide compares all three, covers Docker networking implications, and gives you ready-to-use configuration recipes so you can lock down your server in minutes.

## Quick Comparison Table

| Feature | UFW | Firewalld | iptables / nftables |
|---------|-----|-----------|----[plex](https://www.plex.tv/)-------------|
| **Complexity** | Very Low | Low-Medium | High |
| **Default On** | Ubuntu/Debian | RHEL/Fedora/SUSE | Arch, Alpine |
| **Syntax Style** | Simple English-like | Zone-based | Rule-based |
| **Docker Support** | ⚠️ Manual override needed | ⚠️ Manual override needed | ⚠️ Manual override needed |
| **Rich Rules** | Limited | Yes (source, port, protocol, interface) | Unlimited |
| **Runtime Changes** | Yes | Yes (runtime + permanent) | Yes |
| **Logging** | Basic | Rich logging | Full packet logging |
| **IPv6 Support** | ✅ Yes | ✅ Yes | ✅ Yes |
| **GUI Frontend** | Gufw | firewall-config | None (use fwbuilder) |
| **Configuration File** | `/etc/ufw/` | XML zones in `/etc/firewalld/` | `/etc/iptables/` or nftables.conf |
| **Best For** | Beginners, single-server | Multi-interface servers, desktops | Advanced users, custom topologies |

## Understanding the Firewall Stack

Before diving into tools, it helps to understand how Linux packet filtering works:

```
Application Layer
        ↓
    Sockets / Ports
        ↓
  Netfilter (Kernel)
        ↓
  iptables (legacy)  ← OR →  nftables (modern)
        ↓
    Packet Decision (ACCEPT / DROP / REJECT)
```

**iptables** and **nftables** are the actual kernel-level packet filtering frameworks. UFW and Firewalld are *frontends* — they generate iptables/nftables rules behind the scenes. Since kernel 5.14+, nftables is the default backend on most distributions, even when you use the `iptables` command.

## 1. UFW — Uncomplicated Firewall (The Beginner's Choice)

**Best for**: Ubuntu/Debian users, single-server setups, anyone who wants "it just works"

UFW lives up to its name. It abstracts iptables into human-readable commands. A new self-hoster can get a secure baseline in under 2 minutes.

### Default Policy — Deny Everything Inbound

```bash
# Reset to defaults
sudo ufw --force reset

# Default policies: deny all incoming, allow all outgoing
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (change port if you use a non-standard one)
sudo ufw allow 22/tcp comment 'SSH'

# Enable the firewall
sudo ufw --force enable
```

### Common Self-Hosted Service Rules

```bash
# Web server
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'

# Reverse proxy (if you run Caddy or Traefik)
sudo ufw allow 80,443/tcp co[adguard home](https://adguard.com/en/adguard-home/overview.html)raffic'

# DNS (if running Pi-hole or AdGuard Home)
sudo ufw allow 53/tcp comment 'DNS TCP'
sudo ufw allow 53/udp comment 'DNS UDP'

# Mail server ports
sudo ufw allow 25/tcp comment 'SMTP'
sudo ufw allow 587/tcp comment 'Submission'
sudo ufw allow 993/tcp comment 'IMAPS'

# Database (restricted to local network)
sudo ufw allow from 192.168.1.0/24 to any port 5432 comment 'PostgreSQL LAN'
sudo ufw allow from 192.168.1.0/24 to any port 3306 comment 'MySQL LAN'

# WireGuard VPN
sudo ufw allow 51820/udp comment 'WireGuard'

# Grafana dashboard (restricted)
sudo ufw allow from 192.168.1.0/24 to any port 3000 comment 'Grafana LAN'
```

### Checking Status and Managing Rules

```bash
# View active rules with numbers
sudo ufw status numbered

# Detailed status with logging
sudo ufw status verbose

# Delete a rule by number
sudo ufw delete 3

# Disable temporarily (for troubleshooting)
sudo ufw disable

# View the raw iptables rules UFW generated
sudo iptables -L -n -v | head -40
```

### The Docker Problem with UFW

Docker manipulates iptables directly, which bypasses UFW. A port exposed via `docker run -p 8080:80` will be reachable from the internet even if UFW blocks port 8080.

**Fix 1: Disable Docker's iptables manipulation** (breaks container-to-container networking):

```json
// /etc/docker/daemon.json
{
  "iptables": false
}
```

Then restart Docker: `sudo systemctl restart docker`

**Fix 2: Use UFW's Docker integration plugin:**

```bash
# Install the ufw-docker plugin
sudo wget -O /usr/local/bin/ufw-docker \
  https://raw.githubusercontent.com/chaifeng/ufw-docker/master/ufw-docker
sudo chmod +x /usr/local/bin/ufw-docker

# Add Docker rules to UFW's after.rules
sudo ufw-docker install

# Restart UFW
sudo ufw reload

# Now use ufw-docker to manage rules
sudo ufw-docker allow jellyfin
sudo ufw-docker allow nextcloud 443
```

**Fix 3 (recommended): Publish to localhost only and use a reverse proxy:**

```yaml
# docker-compose.yml — bind to 127.0.0.1 only
services:
  jellyfin:
    ports:
      - "127.0.0.1:8096:8096"
  nextcloud:
    ports:
      - "127.0.0.1:8080:80"
```

## 2. Firewalld — Zone-Based Firewalling (The Enterprise Choice)

**Best for**: RHEL/Fedora/AlmaLinux users, servers with multiple network interfaces, desktops

Firewalld uses a *zone* model. Each network interface is assigned to a zone, and each zone has its own ruleset. This is powerful for servers that sit on multiple networks (e.g., a public-facing interface and a private LAN).

### Built-in Zones

| Zone | Default Behavior | Use Case |
|------|-----------------|----------|
| `drop` | Drop all incoming, allow outgoing | Maximum security, no responses |
| `block` | Reject all incoming | Similar to drop, but sends ICMP reject |
| `public` | Selected connections only | Untrusted networks, default for most servers |
| `external` | Selected connections + masquerading | NAT gateways, routers |
| `dmz` | Limited access to internal | DMZ servers |
| `work` | Trust most machines | Office networks |
| `home` | Trust most machines | Home networks |
| `internal` | Trust all machines | Internal-only networks |
| `trusted` | Allow all | Management networks |

### Basic Setup for a Self-Hosted Server

```bash
# Start and enable firewalld
sudo systemctl enable --now firewalld

# Check the active zone (usually 'public')
firewall-cmd --get-active-zones

# Set default zone
sudo firewall-cmd --set-default-zone=public

# Verify
firewall-cmd --get-default-zone
```

### Adding Services and Ports

Firewalld has pre-defined service definitions (XML files in `/usr/lib/firewalld/services/`):

```bash
# List all available service definitions
firewall-cmd --get-services

# Add common services (--permanent makes it survive reboots)
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-service=dns

# Add custom ports
sudo firewall-cmd --permanent --add-port=8096/tcp  # Jellyfin
sudo firewall-cmd --permanent --add-port=3000/tcp  # Grafana
sudo firewall-cmd --permanent --add-port=51820/udp # WireGuard

# Reload to apply permanent rules
sudo firewall-cmd --reload

# Verify active rules
sudo firewall-cmd --list-all
```

### Rich Rules — Granular Access Control

Rich rules let you specify source IPs, logging, and complex conditions:

```bash
# Allow PostgreSQL only from the local subnet with logging
sudo firewall-cmd --permanent --add-rich-rule='
  rule family="ipv4"
  source address="192.168.1.0/24"
  port protocol="tcp" port="5432"
  log prefix="PostgreSQL access: " level="info"
  accept'

# Allow SSH only from your management IP
sudo firewall-cmd --permanent --add-rich-rule='
  rule family="ipv4"
  source address="203.0.113.50/32"
  port protocol="tcp" port="22"
  accept'

# Rate-limit SSH to prevent brute force
sudo firewall-cmd --permanent --add-rich-rule='
  rule family="ipv4"
  source address="0.0.0.0/0"
  port protocol="tcp" port="22"
  log prefix="SSH brute force: " level="notice"
  accept limit value="3/m"'

sudo firewall-cmd --reload
```

### Multiple Zones for Multi-Interface Servers

```bash
# Assign interfaces to zones
sudo firewall-cmd --permanent --zone=internal --change-interface=eth1
sudo firewall-cmd --permanent --zone=public --change-interface=eth0

# Add services to the internal zone (trust your LAN)
sudo firewall-cmd --permanent --zone=internal --add-service=ssh
sudo firewall-cmd --permanent --zone=internal --add-service=dns
sudo firewall-cmd --permanent --zone=internal --add-service=dhcp

# Masquerading on the external zone (NAT for LAN)
sudo firewall-cmd --permanent --zone=external --add-masquerade

sudo firewall-cmd --reload
```

### Firewalld and Docker

Like UFW, Firewalld's rules can be bypassed by Docker's direct iptables manipulation. The same three fixes apply:

1. Set `"iptables": false` in `daemon.json`
2. Publish containers to `127.0.0.1` only
3. Use `--network=host` with explicit firewall rules

## 3. iptables / nftables — The Power User's Toolkit

**Best for**: Advanced users, custom topologies, learning how Linux networking actually works

While UFW and Firewalld are convenient, they abstract away the underlying mechanics. Understanding iptables (or its successor, nftables) gives you complete control over packet filtering, NAT, port forwarding, and traffic shaping.

### iptables Chain Basics

```
INPUT chain   → Packets destined for this server
FORWARD chain → Packets routed through this server
OUTPUT chain  → Packets originating from this server
PREROUTING    → Before routing decision (NAT)
POSTROUTING   → After routing decision (NAT, masquerading)
```

### A Production-Ready iptables Ruleset

```bash
#!/bin/bash
# /etc/iptables/rules.sh
# A hardened iptables ruleset for self-hosted servers

# Flush existing rules
iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X
iptables -t mangle -F
iptables -t mangle -X

# Default policies — DROP everything, then explicitly allow
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# Allow loopback (localhost)
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

# Allow established and related connections (stateful)
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# Drop invalid packets
iptables -A INPUT -m conntrack --ctstate INVALID -j DROP

# Anti-spoofing: drop packets claiming to be from localhost on external interface
iptables -A INPUT ! -i lo -s 127.0.0.0/8 -j DROP

# Allow ICMP (ping) with rate limiting
iptables -A INPUT -p icmp --icmp-type echo-request -m limit --limit 1/s --limit-burst 4 -j ACCEPT
iptables -A INPUT -p icmp --icmp-type echo-reply -j ACCEPT
iptables -A INPUT -p icmp --icmp-type destination-unreachable -j ACCEPT
iptables -A INPUT -p icmp --icmp-type time-exceeded -j ACCEPT

# SSH — allow from anywhere (or restrict to your IP)
iptables -A INPUT -p tcp --dport 22 -m conntrack --ctstate NEW -m recent --set --name SSH
iptables -A INPUT -p tcp --dport 22 -m conntrack --ctstate NEW -m recent --update --seconds 60 --hitcount 4 --name SSH -j DROP
iptables -A INPUT -p tcp --dport 22 -m conntrack --ctstate NEW -j ACCEPT

# HTTP / HTTPS
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Custom services — add as needed
iptables -A INPUT -p tcp --dport 8096 -j ACCEPT   # Jellyfin
iptables -A INPUT -p udp --dport 51820 -j ACCEPT  # WireGuard
iptables -A INPUT -p tcp --dport 53 -j ACCEPT     # DNS
iptables -A INPUT -p udp --dport 53 -j ACCEPT     # DNS

# Log dropped packets (for debugging)
iptables -A INPUT -j LOG --log-prefix "IPTABLES-DROP: " --log-level 4

# Final drop (explicit, though default policy already does this)
iptables -A INPUT -j DROP

echo "iptables rules applied successfully"
```

### Making iptables Persistent

On Debian/Ubuntu:
```bash
# Install persistence package
sudo apt install iptables-persistent

# Save current rules
sudo netfilter-persistent save

# Rules stored in:
# /etc/iptables/rules.v4   (IPv4)
# /etc/iptables/rules.v6   (IPv6)
```

On RHEL/Fedora:
```bash
sudo iptables-save > /etc/sysconfig/iptables
sudo systemctl enable iptables
```

### Introduction to nftables — The Modern Replacement

nftables replaces iptables with a cleaner syntax, better performance, and unified IPv4/IPv6 handling. It's the default on newer distributions.

```bash
#!/sbin/nft -f
# /etc/nftables.conf

flush ruleset

table inet filter {
    chain input {
        type filter hook input priority 0; policy drop;

        # Allow loopback
        iif lo accept

        # Allow established connections
        ct state established,related accept
        ct state invalid drop

        # Allow ICMPv4 and ICMPv6
        ip protocol icmp accept
        ip6 nexthdr icmpv6 accept

        # SSH with rate limiting
        tcp dport 22 ct state new limit rate 3/minute accept

        # Web services
        tcp dport { 80, 443 } accept

        # Custom self-hosted services
        tcp dport 8096 accept        # Jellyfin
        udp dport 51820 accept       # WireGuard
        tcp dport { 53, 853 } accept # DNS + DoT
        udp dport { 53, 853 } accept

        # Log and drop everything else
        log prefix "NFTABLES-DROP: " drop
    }

    chain forward {
        type filter hook forward priority 0; policy drop;
    }

    chain output {
        type filter hook output priority 0; policy accept;
    }
}
```

Enable nftables:
```bash
sudo systemctl enable --now nftables
sudo nft list ruleset  # verify
```

## Docker Networking and Firewalls — The Complete Picture

This is the single most common misconfiguration in self-hosted setups. Here's a definitive approach:

### Strategy 1: Localhost Binding (Recommended)

```yaml
# docker-compose.yml
services:
  nextcloud:
    image: nextcloud:apache
    ports:
      - "127.0.0.1:8080:80"  # Only accessible via reverse proxy

  jellyfin:
    image: jellyfin/jellyfin
    ports:
      - "127.0.0.1:8096:8096"

  gitea:
    image: gitea/gitea:latest
    ports:
      - "127.0.0.1:3000:3000"
      - "127.0.0.1:222:22"
```

Then your firewall only needs to allow ports 80 and 443 (your reverse proxy).

### Strategy 2: Docker User-Defined Networks

```yaml
# docker-compose.yml
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true  # No external access

services:
  reverse-proxy:
    networks:
      - frontend

  nextcloud:
    networks:
      - frontend
      - backend

  postgres:
    networks:
      - backend  # Only reachable from nextcloud
    ports: []    # No host port mapping at all
```

The `internal: true` flag prevents the backend network from reaching the internet — an extra layer of isolation for databases and internal services.

### Strategy 3: Port Knocking for SSH

For an additional security layer, hide SSH behind port knocking:

```bash
# Install knockd
sudo apt install knockd

# Configure /etc/knockd.conf
[options]
    UseSyslog

[openSSH]
    sequence    = 7000,8000,9000
    seq_timeout = 5
    command     = /sbin/iptables -A INPUT -s %IP% -p tcp --dport 22 -j ACCEPT
    tcpflags    = syn

[closeSSH]
    sequence    = 9000,8000,7000
    seq_timeout = 5
    command     = /sbin/iptables -D INPUT -s %IP% -p tcp --dport 22 -j ACCEPT
    tcpflags    = syn

sudo systemctl enable --now knockd
```

Knock the sequence from your client: `knock your-server.com 7000 8000 9000`

## Choosing the Right Firewall for Your Setup

| Scenario | Recommendation | Reason |
|----------|---------------|--------|
| **Ubuntu VPS, first self-hosted server** | UFW | Simplest path to a secure baseline |
| **RHEL/Fedora/AlmaLinux server** | Firewalld | Native, zone model fits enterprise patterns |
| **Multi-homed server (public + private NICs)** | Firewalld | Zone-based design handles this natively |
| **Learning networking fundamentals** | iptables/nftables | Understand what's happening under the hood |
| **Complex NAT / routing / port forwarding** | iptables/nftables | Maximum flexibility for custom topologies |
| **Desktop + server on same machine** | Firewalld | Different zones for different interfaces |
| **Automated provisioning (Ansible/Terraform)** | Any — pick what matches your OS | All three are automation-friendly |
| **Maximum performance (high-traffic server)** | nftables | Faster rule evaluation, less memory |

## Recommended Baseline Checklist

Regardless of which tool you choose, every self-hosted server should have:

1. **Default deny incoming** — only explicitly allowed ports are open
2. **SSH rate limiting** — prevent brute-force attacks
3. **Only ports 80/443 public** — all other services behind a reverse proxy
4. **Fail2ban integration** — auto-ban IPs after repeated failed logins
5. **IPv6 rules** — don't forget the IPv6 stack (many firewalls ignore it by default)
6. **Logging enabled** — so you can investigate suspicious activity
7. **Regular rule audits** — `sudo ufw status` or `sudo firewall-cmd --list-all` quarterly

## Conclusion

For most self-hosters running Ubuntu or Debian, **UFW** provides the best balance of simplicity and security. If you're on a Red Hat-based distribution, **Firewalld** is the natural choice. Reserve raw **iptables/nftables** for scenarios where you need custom NAT, complex routing, or want to understand the fundamentals of Linux networking.

The most important thing isn't which tool you pick — it's that you actually configure one, test it, and keep it maintained. An unconfigured server is an open door.

## Frequently Asked Questions (FAQ)

### Which one should I choose in 2026?

The best choice depends on your specific requirements:

- **For beginners**: Start with the simplest option that covers your core use case
- **For production**: Choose the solution with the most active community and documentation
- **For teams**: Look for collaboration features and user management
- **For privacy**: Prefer fully open-source, self-hosted options with no telemetry

Refer to the comparison table above for detailed feature breakdowns.

### Can I migrate between these tools?

Most tools support data import/export. Always:
1. Backup your current data
2. Test the migration on a staging environment
3. Check official migration guides in the documentation

### Are there free versions available?

All tools in this guide offer free, open-source editions. Some also provide paid plans with additional features, priority support, or managed hosting.

### How do I get started?

1. Review the comparison table to identify your requirements
2. Visit the official documentation (links provided above)
3. Start with a Docker Compose setup for easy testing
4. Join the community forums for troubleshooting
