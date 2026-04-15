---
title: "Best Self-Hosted DHCP Servers 2026: Kea vs Dnsmasq vs ISC DHCP"
date: 2026-04-15
tags: ["comparison", "guide", "self-hosted", "privacy", "networking", "homelab"]
draft: false
description: "Complete guide to self-hosted DHCP servers in 2026. Compare Kea, Dnsmasq, and ISC DHCP for your homelab with Docker configs, installation steps, and a feature comparison table."
---

Every device on your local network needs an IP address. Whether you are running a homelab with a handful of Raspberry Pis or managing a small office with dozens of workstations, the Dynamic Host Configuration Protocol (DHCP) is the silent workhorse that assigns addresses, routes traffic, and hands out DNS server information. Most people never think about DHCP until something breaks — a device gets a duplicate address, a smart TV refuses to connect, or a server reboots with a new IP and breaks your port forwards.

Running your own DHCP server gives you full control over your network. You decide which devices get which addresses, which DNS resolvers they use, and which devices are even allowed on the network. Combined with a self-hosted DNS server like Pi-hole or AdGuard Home, a dedicated DHCP server becomes the cornerstone of a private, self-managed network stack.

In this guide, we compare three of the most popular self-hosted DHCP server solutions available in 2026: **Kea**, **Dnsmasq**, and the legacy **ISC DHCP**. We will look at installation, configuration, features, and performance so you can pick the right tool for your setup.

## Why Run Your Own DHCP Server?

Your router probably already runs a DHCP server. So why replace it?

**Full network visibility.** A self-hosted DHCP server logs every device that connects, what address it received, and when. You get a real-time inventory of your network without installing additional scanning tools.

**Static assignments without touching each device.** Instead of configuring a fixed IP on every server or NAS, you assign it centrally through DHCP reservations. The device still gets its address automatically, but it is always the same one.

**Custom DNS routing.** You can tell every device on your network to use your self-hosted DNS resolver (Pi-hole, AdGuard Home, Unbound) instead of your ISP's servers. This enables network-wide ad blocking, content filtering, and privacy protection without configuring each device individually.

**VLAN-aware address management.** If you segment your network into VLANs for IoT devices, guests, and trusted workstations, a proper DHCP server can hand out addresses on each subnet with different policies — different DNS servers, different lease times, different options.

**No cloud dependency.** Router firmware updates reset settings. ISP-provided gatewares are notoriously limited. A self-hosted DHCP server runs on hardware you control, with configuration you own, backed up on your terms.

## The Three Contenders

### Kea DHCP

Kea is the modern successor to the ISC DHCP project, developed by the Internet Systems Consortium. It is designed from the ground up for large-scale deployments, with a modular architecture, REST API, and support for high-availability failover. Kea uses JSON for configuration and stores lease data in a database (MySQL, PostgreSQL, or Cassandra), making it highly scalable.

### Dnsmasq

Dnsmasq is a lightweight, all-in-one DNS and DHCP server. It is the default choice in countless router firmwares (OpenWrt, DD-WRT) and container networking stacks (Docker uses a variant). Its configuration is a single plain-text file, and it runs with minimal memory footprint — often under 5 MB of RAM.

### ISC DHCP (dhcpd)

ISC DHCP (also known as `dhcpd`) was the gold standard for two decades. It is now officially end-of-life as of December 2022, with the ISC recommending migration to Kea. However, it remains widely deployed and is still the default on many Linux distributions. Its configuration syntax is well understood, thoroughly documented, and deeply entrenched in existing infrastructure.

## Feature Comparison at a Glance

| Feature | Kea | Dnsmasq | ISC DHCP |
|---|---|---|---|
| **Status** | Actively developed | Actively developed | End-of-life (Dec 2022) |
| **Protocol support** | DHCPv4, DHCPv6 | DHCPv4, DHCPv6 (limited) | DHCPv4, BOOTP |
| **Configuration format** | JSON | Simple text file | Custom declarative |
| **Lease storage** | Database (MySQL/PostgreSQL/Cassandra) | In-memory + flat file | Flat file |
| **REST API** | Yes (built-in) | No | No |
| **High availability** | Yes (failover + multi-master) | No | Yes (failover protocol) |
| **DDNS integration** | Yes | Yes | Yes |
| **Vendor classes / options** | Extensive | Basic | Extensive |
| **Memory footprint** | ~50–200 MB | ~2–5 MB | ~10–30 MB |
| **VLAN / multi-subnet** | Yes (via relay agents) | Yes | Yes |
| **Container friendly** | Yes | Excellent | Moderate |
| **Learning curve** | Steep | Gentle | Moderate |
| **Best for** | Enterprise, large homelabs | Small networks, routers | Legacy migration |

## Installing and Configuring Kea DHCP

Kea is the future-proof choice. Its database-backed lease storage and REST API make it ideal for environments where you want programmatic control over address assignments.

### Installation via Docker

The easiest way to run Kea is in a Docker container. This keeps it isolated and makes upgrades straightforward:

```yaml
# docker-compose-kea.yml
version: "3.8"

services:
  kea-dhcp4:
    image: keaproject/kea:latest
    container_name: kea-dhcp4
    network_mode: host
    restart: unless-stopped
    volumes:
      - ./kea-dhcp4.conf:/etc/kea/kea-dhcp4.conf:ro
      - ./kea-leases.csv:/var/lib/kea/kea-leases.csv
    environment:
      - KEA_LOG_LEVEL=INFO

  kea-dhcp6:
    image: keaproject/kea:latest
    container_name: kea-dhcp6
    network_mode: host
    restart: unless-stopped
    volumes:
      - ./kea-dhcp6.conf:/etc/kea/kea-dhcp6.conf:ro
      - ./kea-leases6.csv:/var/lib/kea/kea-leases6.csv
    environment:
      - KEA_LOG_LEVEL=INFO
```

### Kea Configuration (kea-dhcp4.conf)

Kea uses a JSON configuration file. Here is a practical setup for a typical homelab on the `192.168.1.0/24` subnet:

```json
{
  "Dhcp4": {
    "interfaces-config": {
      "interfaces": ["eth0"]
    },
    "lease-database": {
      "type": "memfile",
      "persist": true,
      "name": "/var/lib/kea/kea-leases.csv"
    },
    "valid-lifetime": 86400,
    "renew-timer": 3600,
    "rebind-timer": 7200,
    "option-data": [
      {
        "name": "domain-name-servers",
        "data": "192.168.1.10, 192.168.1.11"
      },
      {
        "name": "domain-search",
        "data": "homelab.local"
      },
      {
        "name": "routers",
        "data": "192.168.1.1"
      }
    ],
    "subnet4": [
      {
        "subnet": "192.168.1.0/24",
        "pools": [
          { "pool": "192.168.1.100 - 192.168.1.200" }
        ],
        "reservations": [
          {
            "hw-address": "b8:27:eb:a1:b2:c3",
            "ip-address": "192.168.1.50",
            "hostname": "nas-server"
          },
          {
            "hw-address": "dc:a6:32:0f:11:22",
            "ip-address": "192.168.1.51",
            "hostname": "media-pc"
          }
        ]
      }
    ],
    "control-socket": {
      "socket-type": "unix",
      "socket-name": "/tmp/kea4-ctrl.sock"
    },
    "loggers": [
      {
        "name": "kea-dhcp4",
        "output_options": [
          { "output": "/var/log/kea/kea-dhcp4.log" }
        ],
        "severity": "INFO",
        "debuglevel": 0
      }
    ]
  }
}
```

Start the server with `docker compose -f docker-compose-kea.yml up -d`.

### Managing Kea via REST API

Kea exposes a control channel over a Unix socket. You can query it directly or use a helper tool:

```bash
# Check server statistics
kea-ctrl-agent -c /etc/kea/kea-ctrl-agent.conf

# Or send commands directly via the socket
echo '{ "command": "statistic-get-all" }' | socat UNIX:/tmp/kea4-ctrl.sock -
```

For production use, connect Kea to PostgreSQL for lease persistence and enable the Kea Control Agent for dynamic reconfiguration without restarts:

```json
{
  "lease-database": {
    "type": "postgresql",
    "name": "kea_leases",
    "user": "kea",
    "password": "strong_password_here",
    "host": "192.168.1.10",
    "port": 5432
  }
}
```

## Installing and Configuring Dnsmasq

Dnsmasq is the minimalist's choice. A single configuration file, a tiny memory footprint, and combined DNS + DHCP in one process make it ideal for small networks, Raspberry Pi deployments, and container environments.

### Installation on Debian/Ubuntu

```bash
sudo apt update
sudo apt install dnsmasq
```

### Installation via Docker

```yaml
# docker-compose-dnsmasq.yml
version: "3.8"

services:
  dnsmasq:
    image: jpillora/dnsmasq:latest
    container_name: dnsmasq
    network_mode: host
    restart: unless-stopped
    volumes:
      - ./dnsmasq.conf:/etc/dnsmasq.conf:ro
    cap_add:
      - NET_ADMIN
```

### Dnsmasq Configuration (dnsmasq.conf)

```ini
# dnsmasq.conf — Combined DNS + DHCP for homelab

# Interface to listen on (leave blank for all)
interface=eth0
bind-interfaces

# DHCP range: 192.168.1.100 to 192.168.1.200, 24h lease
dhcp-range=192.168.1.100,192.168.1.200,255.255.255.0,24h

# Default gateway
dhcp-option=option:router,192.168.1.1

# DNS servers (point to self-hosted Pi-hole / AdGuard Home)
dhcp-option=option:dns-server,192.168.1.10,192.168.1.11

# Domain name for DHCP
domain=homelab.local

# Static reservations by MAC address
dhcp-host=b8:27:eb:a1:b2:c3,192.168.1.50,nas-server,86400
dhcp-host=dc:a6:32:0f:11:22,192.168.1.51,media-pc,86400
dhcp-host=e4:5f:01:ab:cd:ef,192.168.1.52,printer,86400

# DNS upstream servers
server=8.8.8.8
server=8.8.4.4

# Local DNS — resolve homelab.local from /etc/hosts
expand-hosts
domain-needed
bogus-priv

# Logging
log-dhcp
log-queries
log-facility=/var/log/dnsmasq.log
```

Restart the service after editing:

```bash
sudo systemctl restart dnsmasq
# or with Docker:
docker compose -f docker-compose-dnsmasq.yml restart
```

### Viewing Active Leases

Dnsmasq stores leases in `/var/lib/misc/dnsmasq.leases`:

```bash
cat /var/lib/misc/dnsmasq.leases
# Format: timestamp MAC-address IP-address hostname client-ID
# Example:
# 1744848000 b8:27:eb:a1:b2:c3 192.168.1.50 nas-server *
```

## Installing ISC DHCP (Legacy)

ISC DHCP is included here for completeness and for administrators managing existing deployments. The ISC officially ended support in December 2022 and recommends migrating to Kea. If you are starting fresh, skip this section and use Kea or Dnsmasq.

### Installation

```bash
# Debian/Ubuntu
sudo apt install isc-dhcp-server

# RHEL/CentOS/Fedora
sudo dnf install dhcp-server
```

### Configuration (dhcpd.conf)

```ini
# /etc/dhcp/dhcpd.conf

default-lease-time 86400;
max-lease-time 172800;

option domain-name "homelab.local";
option domain-name-servers 192.168.1.10, 192.168.1.11;
option routers 192.168.1.1;

subnet 192.168.1.0 netmask 255.255.255.0 {
  range 192.168.1.100 192.168.1.200;

  host nas-server {
    hardware ethernet b8:27:eb:a1:b2:c3;
    fixed-address 192.168.1.50;
    option host-name "nas-server";
  }

  host media-pc {
    hardware ethernet dc:a6:32:0f:11:22;
    fixed-address 192.168.1.51;
    option host-name "media-pc";
  }
}

# Logging
log-facility local7;
```

Configure the interface in `/etc/default/isc-dhcp-server`:

```bash
INTERFACESv4="eth0"
```

Then start:

```bash
sudo systemctl enable isc-dhcp-server
sudo systemctl start isc-dhcp-server
```

### Migrating from ISC DHCP to Kea

The ISC provides a migration script that converts your `dhcpd.conf` into Kea's JSON format:

```bash
# Install the migration tools
sudo apt install kea-admin

# Convert configuration
kea-admin lease-copy -4 \
  -s /var/lib/dhcp/dhcpd.leases \
  -d /var/lib/kea/kea-leases.csv
```

For the main configuration, use the `kea-admin dhcp4-convert` utility:

```bash
kea-admin dhcp4-convert -c /etc/dhcp/dhcpd.conf > /etc/kea/kea-dhcp4.conf
```

Review the output carefully — complex configurations with shared networks or conditional options may need manual adjustment.

## Choosing the Right DHCP Server for Your Setup

The decision comes down to three factors: **scale**, **complexity**, and **maintenance philosophy**.

**Choose Kea if** you run more than 50 devices, need high availability, want programmatic control via REST API, or plan to integrate DHCP with external systems (CMDB, monitoring, automation). Its database-backed lease storage means you can query address assignments with SQL, build dashboards, and audit changes over time.

**Choose Dnsmasq if** you have a small to medium network (under 100 devices), want the simplest possible setup, or are already running it as a DNS forwarder and want to add DHCP to the same process. Its single-file configuration is easy to version-control with Git and review at a glance.

**Avoid ISC DHCP for new deployments.** It has not received security updates since December 2022. If you are still running it, plan a migration to Kea. The configuration concepts are similar, and the ISC provides tooling to automate the conversion.

## Advanced: Combining DHCP with DNS Filtering

A powerful homelab pattern is to point your DHCP server's DNS option to a local Pi-hole or AdGuard Home instance, which in turn uses an upstream recursive resolver like Unbound:

```
Client → DHCP assigns IP + DNS → Pi-hole (ad blocking) → Unbound (recursive DNS) → Internet
```

In your DHCP configuration, set the DNS option to your Pi-hole IP:

```json
// Kea
{ "name": "domain-name-servers", "data": "192.168.1.10" }
```

```ini
# Dnsmasq
dhcp-option=option:dns-server,192.168.1.10
```

Every device on your network now benefits from ad blocking, tracker blocking, and encrypted DNS resolution without any per-device configuration.

## Conclusion

DHCP is one of those infrastructure services that works invisibly until it does not. By running your own self-hosted DHCP server, you gain visibility into every device on your network, control over address assignments, and the ability to enforce your own DNS and routing policies.

For 2026, **Kea** is the clear recommendation for anyone starting fresh or planning to scale. Its modern architecture, database-backed leases, and REST API make it the most capable open-source DHCP server available. **Dnsmasq** remains the go-to choice for small networks where simplicity and low resource usage matter most. **ISC DHCP** should be treated as legacy — stable and well understood, but no longer maintained.

Whatever you choose, keep your configuration under version control, back up your lease databases, and document your static assignments. A well-managed DHCP server is the foundation of a reliable, private, and self-controlled network.
