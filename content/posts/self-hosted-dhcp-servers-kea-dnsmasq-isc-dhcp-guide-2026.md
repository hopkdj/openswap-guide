---
title: "Best Self-Hosted DHCP Servers 2026: Kea vs Dnsmasq vs ISC DHCP"
date: 2026-04-17
tags: ["comparison", "guide", "self-hosted", "networking"]
draft: false
description: "Complete guide to self-hosted DHCP servers in 2026. Compare Kea, Dnsmasq, and ISC DHCP with installation guides, Docker configs, and production best practices for homelabs and enterprise networks."
---

Running your own DHCP server gives you full control over IP address assignment, DNS resolution, and network boot operations. Whether you manage a homelab with dozens of devices or an enterprise network spanning multiple VLANs, choosing the right DHCP server is one of the most foundational decisions you'll make.

In this guide, we compare the three most popular open-source DHCP servers — Kea, Dnsmasq, and the legacy ISC DHCP — with hands-on installation instructions, Docker Compose configurations, and production-ready deployment advice.

## Why Run Your Own DHCP Server?

Most home users rely on the DHCP server baked into their consumer router. That works fine for a handful of devices on a single flat network. But as soon as your infrastructure grows, the limitations become obvious:

- **VLAN segmentation** — Consumer routers can't assign addresses across multiple subnets. A dedicated DHCP server handles VLANs and subnet scopes with ease.
- **Static reservations** — Lock specific MAC addresses to fixed IPs so your servers, NAS, and Pi-hole always get the same address without manual static IP configuration on each device.
- **DNS integration** — DHCP and DNS are natural partners. Servers like Dnsmasq handle both, ensuring every device that receives a lease is automatically registered in DNS.
- **Network boot (PXE/TFTP)** — Provision bare-metal servers, diskless workstations, or thin clients by serving boot images over the network.
- **Lease monitoring and auditing** — Track every device that connects to your network, when it connected, and what IP it received. Built-in router logs rarely expose this data.
- **High availability** — Consumer routers are single points of failure. Open-source DHCP servers support failover pairs and load-balanced clusters.
- **Custom DHCP options** — Push custom options (NTP servers, SIP proxies, vendor-specific settings) to clients on a per-subnet basis.

If any of these sound useful, it's time to take DHCP into your own hands.

## The Contenders at a Glance

Before diving into configuration, here's how the three major options compare:

| Feature | Kea | Dnsmasq | ISC DHCP |
|---------|-----|---------|----------|
| **Status** | Actively developed (ISC successor) | Actively developed | End-of-life (EOL June 2022) |
| **Protocols** | DHCPv4, DHCPv6 | DHCPv4, DNS, TFTP, PXE | DHCPv4, DHCPv6 |
| **Backend** | MySQL, PostgreSQL, Cassandra, memfile | In-memory, hosts file | Flat file (leases) |
| **HA Support** | Yes (failover + load balancing) | No (single instance) | Yes (failover protocol) |
| **Configuration** | JSON | Simple flat file | Complex flat file |
| **REST API** | Yes (control agent) | No | No |
| **Hook System** | Yes (C/C++ and Python plugins) | No | Limited |
| **Resource Usage** | Moderate (backend-dependent) | Very low | Low |
| **Best For** | Enterprise, multi-VLAN, automation | Homelabs, small networks, DNS combo | Legacy deployments (migration target) |
| **License** | MPL 2.0 | GPL v2/v3 | ISC License |

### Which One Should You Choose?

- **Homelab / small office** — Dnsmasq. It's lightweight, combines DHCP with DNS in one process, and takes minutes to configure.
- **Enterprise / multi-VLAN** — Kea. It's ISC's modern successor with database backends, REST API, high-availability clustering, and a plugin architecture.
- **ISC DHCP** — Only if you're maintaining legacy infrastructure. ISC officially ended support in June 2022. Migrate to Kea at your earliest convenience; the configuration migration tool handles most of the conversion automatically.

## Kea DHCP: The Modern Enterprise Choice

Kea is ISC's next-generation DHCP server, designed from the ground up to replace ISC DHCP. It supports DHCPv4, DHCPv6, a RESTful management API, database-backed lease storage, and high-availability clustering.

### Installation on Ubuntu/Debian

```bash
sudo apt update
sudo apt install -y kea-dhcp4 kea-dhcp6 kea-ctrl-agent
```

### Core Configuration

Kea uses JSON configuration files. The main DHCPv4 config lives at `/etc/kea/kea-dhcp4.conf`:

```json
{
  "Dhcp4": {
    "interfaces-config": {
      "interfaces": ["eth0"]
    },
    "lease-database": {
      "type": "mysql",
      "name": "kea",
      "user": "kea",
      "password": "kea_password",
      "host": "localhost",
      "persist": true
    },
    "expired-leases-processing": {
      "reclaim-timer-wait-time": 10,
      "flush-reclaimed-timer-wait-time": 25,
      "hold-reclaimed-time": 3600,
      "max-reclaim-leases": 100,
      "max-reclaim-time": 250,
      "unwarned-reclaim-cycling": false
    },
    "option-data": [
      {
        "name": "domain-name-servers",
        "data": "192.168.1.10"
      },
      {
        "name": "domain-name",
        "data": "homelab.local"
      },
      {
        "name": "routers",
        "data": "192.168.1.1"
      },
      {
        "name": "ntp-servers",
        "data": "192.168.1.10"
      }
    ],
    "subnet4": [
      {
        "subnet": "192.168.1.0/24",
        "pools": [
          { "pool": "192.168.1.100 - 192.168.1.200" }
        ],
        "option-data": [
          {
            "name": "domain-name-servers",
            "data": "192.168.1.10"
          }
        ],
        "reservations": [
          {
            "hw-address": "aa:bb:cc:dd:ee:01",
            "ip-address": "192.168.1.50",
            "hostname": "nas-server"
          },
          {
            "hw-address": "aa:bb:cc:dd:ee:02",
            "ip-address": "192.168.1.51",
            "hostname": "media-server"
          }
        ]
      },
      {
        "subnet": "192.168.10.0/24",
        "pools": [
          { "pool": "192.168.10.100 - 192.168.10.200" }
        ],
        "option-data": [
          {
            "name": "routers",
            "data": "192.168.10.1"
          }
        ]
      }
    ],
    "loggers": [
      {
        "name": "kea-dhcp4",
        "output_options": [
          {
            "output": "/var/log/kea/kea-dhcp4.log",
            "flush": true,
            "maxsize": 104857600,
            "maxver": 5
          }
        ],
        "severity": "INFO",
        "debuglevel": 0
      }
    ]
  }
}
```

This configuration defines two subnets (a main network and a VLAN), sets up two static reservations, pushes DNS/NTP/router options, and logs to a file with rotation.

### Setting Up the MySQL Backend

```bash
sudo mysql -u root -p -e "CREATE DATABASE kea;"
sudo mysql -u root -p -e "CREATE USER 'kea'@'localhost' IDENTIFIED BY 'kea_password';"
sudo mysql -u root -p -e "GRANT ALL ON kea.* TO 'kea'@'localhost';"

# Initialize the schema
sudo mysql -u kea -pkea_password kea < /usr/share/kea/scripts/mysql/dhcpdb_create.mysql
```

### Running Kea in Docker

```yaml
version: "3.8"

services:
  kea-mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: kea
      MYSQL_USER: kea
      MYSQL_PASSWORD: kea_password
    volumes:
      - kea-data:/var/lib/mysql
      - ./init-schema.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      kea-net:
        ipv4_address: 172.20.0.2

  kea-dhcp4:
    image: keaproject/kea:latest
    network_mode: "host"
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./kea-dhcp4.conf:/etc/kea/kea-dhcp4.conf:ro
      - ./kea-ctrl-agent.conf:/etc/kea/kea-ctrl-agent.conf:ro
    depends_on:
      - kea-mysql
    restart: unless-stopped

volumes:
  kea-data:

networks:
  kea-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

Note that the DHCP container uses `network_mode: "host"` because DHCP operates at layer 2 and requires direct access to the network interface.

### Using the REST API

Kea's control agent exposes a REST API for runtime management:

```bash
# Check server status
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -d '{ "command": "status-get" }'

# Add a reservation on the fly
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -d '{
    "command": "reservation-add",
    "arguments": {
      "subnet-id": 1,
      "reservation": {
        "hw-address": "aa:bb:cc:dd:ee:03",
        "ip-address": "192.168.1.52",
        "hostname": "pi-cluster-node3"
      }
    }
  }'

# List all leases
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -d '{ "command": "lease4-get-all" }'

# Reload configuration without restart
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -d '{ "command": "config-reload" }'
```

### High-Availability Cluster

Kea supports active-passive and load-balanced HA pairs. Add this to your config:

```json
{
  "Dhcp4": {
    "hooks-libraries": [
      {
        "library": "/usr/lib/x86_64-linux-gnu/kea/lib/libkea-dhcp-ha.so",
        "parameters": {
          "this-server-name": "kea-primary",
          "role": "primary",
          "heartbeat-delay": 10000,
          "max-response-delay": 10000,
          "max-ack-delay": 5000,
          "max-unacked-clients": 5,
          "peers": [
            {
              "name": "kea-primary",
              "url": "http://192.168.1.10:8000/",
              "role": "primary",
              "auto-failover": true
            },
            {
              "name": "kea-secondary",
              "url": "http://192.168.1.11:8000/",
              "role": "secondary",
              "auto-failover": true
            }
          ]
        }
      }
    ]
  }
}
```

## Dnsmasq: The Lightweight Homelab Champion

Dnsmasq is a lightweight, combined DNS forwarder and DHCP server. It's the go-to choice for homelabs because a single binary handles both services, uses minimal resources, and ships with a straightforward configuration file. It's also the DNS/DHCP engine behind Pi-hole.

### Installation on Ubuntu/Debian

```bash
sudo apt update
sudo apt install -y dnsmasq
```

On Alpine Linux (great for containerized deployments):

```bash
apk add dnsmasq
```

### Core Configuration

Edit `/etc/dnsmasq.conf`:

```ini
# ── Network Interface ──
interface=eth0
bind-interfaces

# ── DHCP Range ──
# Format: dhcp-range=<start>,<end>,<lease-time>
dhcp-range=192.168.1.100,192.168.1.200,255.255.255.0,12h

# ── Default Gateway and DNS ──
dhcp-option=option:router,192.168.1.1
dhcp-option=option:dns-server,192.168.1.10

# ── Static Reservations ──
dhcp-host=aa:bb:cc:dd:ee:01,nas-server,192.168.1.50,12h
dhcp-host=aa:bb:cc:dd:ee:02,media-server,192.168.1.51,12h
dhcp-host=aa:bb:cc:dd:ee:03,pi-cluster-node3,192.168.1.52,12h

# ── Domain ──
domain=homelab.local
expand-hosts

# ── DNS Forwarding ──
server=8.8.8.8
server=8.8.4.4

# ── Local DNS from /etc/hosts ──
# Entries in /etc/hosts are served as local DNS records
# Example: 192.168.1.50  nas-server.homelab.local

# ── Logging ──
log-dhcp
log-queries
log-facility=/var/log/dnsmasq.log

# ── PXE/TFTP Boot (optional) ──
# enable-tftp
# tftp-root=/var/lib/tftpboot
# dhcp-boot=pxelinux.0
```

### Managing the Service

```bash
# Start and enable
sudo systemctl enable --now dnsmasq

# Reload config without restart (sends SIGHUP)
sudo systemctl reload dnsmasq

# Check active leases
cat /var/lib/dnsmasq/dnsmasq.leases

# View live DHCP activity
sudo tail -f /var/log/dnsmasq.log
```

### Running Dnsmasq in Docker

```yaml
version: "3.8"

services:
  dnsmasq:
    image: jpillora/dnsmasq:latest
    container_name: dnsmasq
    network_mode: "host"
    cap_add:
      - NET_ADMIN
    volumes:
      - ./dnsmasq.conf:/etc/dnsmasq.conf:ro
      - ./dnsmasq.hosts:/etc/hosts.dnsmasq:ro
    restart: unless-stopped
    environment:
      - TZ=UTC
```

The Docker image reads the config from `/etc/dnsmasq.conf`. Create a companion `dnsmasq.hosts` file for local DNS:

```
192.168.1.10   dns.homelab.local
192.168.1.50   nas.homelab.local
192.168.1.51   media.homelab.local
192.168.1.52   node3.homelab.local
192.168.1.100  pihole.homelab.local
```

### Multi-VLAN Configuration

Dnsmasq supports multiple interfaces and subnet ranges in a single instance:

```ini
# VLAN 10 - IoT devices
interface=eth0.10
dhcp-range=192.168.10.100,192.168.10.200,255.255.255.0,12h
dhcp-option=option:router,192.168.10.1

# VLAN 20 - Servers
interface=eth0.20
dhcp-range=192.168.20.10,192.168.20.50,255.255.255.0,24h
dhcp-option=option:router,192.168.20.1

# VLAN 30 - Guest network (shorter lease)
interface=eth0.30
dhcp-range=192.168.30.100,192.168.30.200,255.255.255.0,1h
dhcp-option=option:router,192.168.30.1
```

### PXE Network Boot Setup

Dnsmasq can serve as a full PXE boot server:

```ini
enable-tftp
tftp-root=/srv/tftp

# BIOS boot
dhcp-boot=pxelinux.0

# UEFI boot
dhcp-match=set:efi64,option:client-arch,7
dhcp-boot=tag:efi64,bootx64.efi

# Specific MAC-based boot
dhcp-match=set:rpi,option:client-arch,0
dhcp-boot=tag:rpi,start4.elf
```

Place your boot images in `/srv/tftp/` and devices will boot over the network automatically.

## ISC DHCP: The Legacy Option (Migration Guide)

ISC DHCP served as the internet's standard DHCP server for over two decades. However, ISC officially declared end-of-life in June 2022. No new features or security patches are being developed. If you're still running ISC DHCP, you should plan a migration to Kea.

### Why Migrate?

- **No security patches** — New vulnerabilities will not be fixed.
- **No DHCPv6 improvements** — Kea's DHCPv6 implementation is far more mature.
- **No REST API** — ISC DHCP has no programmatic management interface.
- **File-based leases** — Kea's database backends handle millions of leases efficiently.

### Migration Steps

ISC provides a migration tool. Here's the process:

```bash
# 1. Install Kea alongside ISC DHCP
sudo apt install -y kea-dhcp4 kea-dhcp6

# 2. Stop ISC DHCP
sudo systemctl stop isc-dhcp-server

# 3. Convert the configuration
# Kea ships with a conversion script
sudo /usr/share/kea/scripts/convert-conf -4 /etc/dhcp/dhcpd.conf \
  > /etc/kea/kea-dhcp4.conf

# 4. Review and adjust the generated config
sudo nano /etc/kea/kea-dhcp4.conf

# 5. Convert leases (optional — Kea can import ISC lease files)
sudo /usr/share/kea/scripts/convert-leases -4 \
  /var/lib/dhcp/dhcpd.leases \
  /var/lib/kea/kea-leases4.csv

# 6. Test the configuration
kea-dhcp4 -t -c /etc/kea/kea-dhcp4.conf

# 7. Start Kea
sudo systemctl enable --now kea-dhcp4

# 8. Verify leases are working
kea-admin lease-dump -4
```

### ISC DHCP Reference Configuration

For those still running ISC DHCP during migration, here's a reference config (`/etc/dhcp/dhcpd.conf`):

```
default-lease-time 43200;
max-lease-time 86400;

option domain-name "homelab.local";
option domain-name-servers 192.168.1.10;

subnet 192.168.1.0 netmask 255.255.255.0 {
  range 192.168.1.100 192.168.1.200;
  option routers 192.168.1.1;

  host nas-server {
    hardware ethernet aa:bb:cc:dd:ee:01;
    fixed-address 192.168.1.50;
  }

  host media-server {
    hardware ethernet aa:bb:cc:dd:ee:02;
    fixed-address 192.168.1.51;
  }
}

subnet 192.168.10.0 netmask 255.255.255.0 {
  range 192.168.10.100 192.168.10.200;
  option routers 192.168.10.1;
}
```

## Advanced: DHCP Snooping and Security

Running your own DHCP server opens up security considerations that consumer routers simply don't address.

### Preventing Rogue DHCP Servers

A rogue DHCP server on your network can redirect traffic, perform man-in-the-middle attacks, or simply cause network outages. Enable DHCP snooping on your managed switches:

```
# Cisco / Arista switch configuration
ip dhcp snooping
ip dhcp snooping vlan 10,20,30
interface GigabitEthernet0/1
  ip dhcp snooping trust
```

On Linux bridges, use `ebtables` to drop DHCP packets from unauthorized MAC addresses:

```bash
# Allow DHCP from your server only
sudo ebtables -A FORWARD -p IPv4 --ip-protocol udp \
  --ip-source-port 68 --ip-destination-port 67 \
  -s ! aa:bb:cc:dd:ee:ff -j DROP
```

### DHCP Lease Monitoring Script

Monitor your DHCP leases and alert on new unknown devices:

```bash
#!/bin/bash
# monitor-dhcp.sh — watch for new devices

LEASE_FILE="/var/lib/dnsmasq/dnsmasq.leases"
KNOWN_HOSTS="/etc/dnsmasq.hosts"
LOG_FILE="/var/log/dhcp-monitor.log"

# Get current leases
current_leases=$(awk '{print $2}' "$LEASE_FILE" | sort -u)

while read -r mac; do
  if ! grep -q "$mac" "$KNOWN_HOSTS"; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] UNKNOWN DEVICE: $mac" >> "$LOG_FILE"
    # Optional: send alert via webhook
    # curl -X POST -d "text=New device: $mac" https://hooks.example.com/alert
  fi
done <<< "$current_leases"
```

Run this via cron every 5 minutes:

```cron
*/5 * * * * /usr/local/bin/monitor-dhcp.sh
```

## Decision Matrix

Choose based on your specific needs:

| Your Situation | Recommendation |
|----------------|----------------|
| Single network, under 50 devices | Dnsmasq |
| Multiple VLANs, under 200 devices | Dnsmasq (multi-interface) or Kea |
| Enterprise network, 500+ devices | Kea with MySQL/PostgreSQL backend |
| Need DHCP + DNS in one package | Dnsmasq |
| Need REST API and automation | Kea |
| Need high availability | Kea (HA clustering) |
| PXE boot / network installation | Dnsmasq (built-in TFTP) or Kea |
| Migrating from ISC DHCP | Kea (official migration path) |
| Running on a Raspberry Pi | Dnsmasq (minimal resource usage) |
| Kubernetes environment | Kea (database backend, API-driven) |

## Final Recommendations

**For most homelab users**, Dnsmasq is the right choice. It's been battle-tested for over two decades, uses less than 5 MB of RAM, and gives you both DHCP and DNS in a single process. The configuration file is intuitive — you can have a fully functional DHCP server running in under five minutes.

**For production and enterprise environments**, Kea is the clear winner. Its database backends handle millions of leases, the REST API enables infrastructure-as-code workflows, and the HA clustering ensures your network never loses DHCP service during maintenance. The JSON configuration has a learning curve, but the payoff in operational flexibility is substantial.

**For ISC DHCP users**, there's no reason to stay on an unsupported product. Kea was designed as its direct successor, and the migration tools make the transition straightforward. Plan your migration, test thoroughly in a staging environment, and cut over during a maintenance window.

Whichever you choose, running your own DHCP server is one of the highest-leverage infrastructure decisions you can make. It gives you visibility into every device on your network, eliminates dependency on proprietary router firmware, and lays the foundation for everything else — DNS, PXE boot, VLAN segmentation, and network automation.
