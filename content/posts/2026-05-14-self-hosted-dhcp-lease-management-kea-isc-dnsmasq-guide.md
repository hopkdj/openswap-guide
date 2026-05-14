---
title: "Self-Hosted DHCP Lease Management: Kea vs ISC DHCP vs Dnsmasq"
date: "2026-05-14"
tags: ["dhcp", "networking", "ipv4", "comparison", "guide", "self-hosted"]
draft: false
description: "Complete guide to managing DHCP lease databases and lease analytics. Compare Kea DHCP, ISC DHCP, and Dnsmasq for lease tracking and analysis."
---

DHCP lease management is a critical but often overlooked aspect of network administration. The DHCP lease database tracks which IP addresses are assigned to which devices, when leases expire, and what options were provided. For network administrators, having visibility into lease data is essential for troubleshooting connectivity issues, planning IP address allocation, detecting unauthorized devices, and auditing network usage.

In this guide, we compare three leading DHCP server implementations and their lease management capabilities: **Kea DHCP**, **ISC DHCP**, and **Dnsmasq**. We cover lease database formats, lease analysis tools, monitoring integrations, and best practices for managing DHCP leases at scale.

For related reading, see our [network discovery agents guide](../2026-05-13-self-hosted-network-discovery-agents-lldpd-snmp-arp-scan-guide/) and [IPv6 neighbor discovery guide](../2026-05-13-self-hosted-ipv6-neighbor-discovery-ndppd-corerad-ndp-library-guide/).

## Understanding DHCP Lease Management

### What Is a DHCP Lease?
When a device connects to a network, the DHCP server assigns it an IP address from a configured pool. This assignment is called a "lease" — it has a specific duration (lease time) after which the client must renew or the address returns to the pool. The lease database tracks:

- **MAC address** — Hardware identifier of the client
- **Assigned IP** — The IP address leased to the client
- **Lease start time** — When the lease was granted
- **Lease expiry** — When the lease expires
- **Hostname** — Client-provided hostname (if any)
- **Client ID** — DHCP client identifier option
- **Lease state** — Active, expired, or released

### Why Lease Management Matters

- **Troubleshooting** — Quickly identify which device holds a specific IP address
- **Capacity planning** — Monitor lease pool utilization to prevent address exhaustion
- **Security auditing** — Detect unauthorized or rogue devices on the network
- **Compliance** — Maintain records of network access for regulatory requirements
- **IPAM integration** — Feed lease data into IP address management systems

## Kea DHCP Lease Management

Kea DHCP is the modern DHCP server from ISC (Internet Systems Consortium), designed as the successor to the legacy ISC DHCP server. It features a REST API, hookable architecture, and support for multiple backends.

### Kea Lease Backends

Kea supports multiple lease database backends:
- **Memfile** — In-memory with flat-file persistence (default)
- **MySQL** — Relational database for large-scale deployments
- **PostgreSQL** — Full-featured relational backend
- **CQL (Cassandra)** — Distributed database for carrier-scale deployments

### Kea Configuration with MySQL Backend

```json
{
  "Dhcp4": {
    "interfaces-config": {
      "interfaces": ["eth0"]
    },
    "lease-database": {
      "type": "mysql",
      "host": "kea-db",
      "name": "kea_leases",
      "user": "kea",
      "password": "kea_password"
    },
    "pools": [
      {
        "pool": "192.168.1.100-192.168.1.200",
        "option-data": [
          {
            "name": "routers",
            "data": "192.168.1.1"
          },
          {
            "name": "domain-name-servers",
            "data": "192.168.1.10"
          }
        ]
      }
    ],
    "lease-expire-lfc": {
      "max-unprocessed-leases": 1000,
      "max-lease-time": 3600
    }
  }
}
```

### Kea Lease Queries (MySQL)

```sql
-- View all active leases
SELECT hwaddr, addr, valid_lifetime, expire
FROM lease4
WHERE expire > NOW();

-- Find lease by MAC address
SELECT hwaddr, addr, hostname, expire
FROM lease4
WHERE hwaddr = UNHEX('AA:BB:CC:DD:EE:FF');

-- Lease pool utilization
SELECT
    COUNT(*) as active_leases,
    (SELECT COUNT(*) FROM lease4 WHERE expire > NOW()) * 100.0 /
    (SELECT COUNT(*) FROM lease4) as utilization_pct
FROM lease4;
```

### Kea REST API for Lease Management

```bash
# Get all active leases
curl -X POST http://localhost:8000/ -d '{
  "command": "lease4-get-all"
}'

# Get lease by IP address
curl -X POST http://localhost:8000/ -d '{
  "command": "lease4-get",
  "arguments": {
    "ip-address": "192.168.1.105"
  }
}'

# Delete expired leases
curl -X POST http://localhost:8000/ -d '{
  "command": "lease4-wipe",
  "arguments": {
    "subnets": [1]
  }
}'
```

### Kea DHCP Docker Compose

```yaml
version: "3.8"
services:
  kea-dhcp4:
    image: isc/kea-ctrl-agent:latest
    container_name: kea-dhcp4
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./kea-dhcp4.conf:/etc/kea/kea-dhcp4.conf:ro
      - ./kea-dhcp6.conf:/etc/kea/kea-dhcp6.conf:ro
    restart: unless-stopped

  kea-ctrl-agent:
    image: isc/kea-ctrl-agent:latest
    container_name: kea-ctrl
    ports:
      - "8000:8000/tcp"
    volumes:
      - ./kea-ctrl-agent.conf:/etc/kea/kea-ctrl-agent.conf:ro
    restart: unless-stopped

  kea-db:
    image: mysql:8.0
    container_name: kea-db
    environment:
      - MYSQL_ROOT_PASSWORD=root_secret
      - MYSQL_DATABASE=kea_leases
      - MYSQL_USER=kea
      - MYSQL_PASSWORD=kea_password
    volumes:
      - kea-db-data:/var/lib/mysql
      - ./kea-schema.sql:/docker-entrypoint-initdb.d/kea-schema.sql
    restart: unless-stopped

volumes:
  kea-db-data:
```

## ISC DHCP Lease Management

ISC DHCP (dhcpcd) is the legacy DHCP server that served as the industry standard for decades. While ISC has deprecated it in favor of Kea, many organizations still run ISC DHCP in production.

### ISC DHCP Lease File Format

ISC DHCP stores leases in a human-readable text file:

```
# /var/lib/dhcp/dhcpd.leases
lease 192.168.1.105 {
  starts 1 2026/05/14 08:30:00;
  ends 1 2026/05/14 20:30:00;
  tstp 1 2026/05/14 20:30:00;
  cltt 1 2026/05/14 08:30:00;
  binding state active;
  next binding state free;
  rewind binding state free;
  hardware ethernet aa:bb:cc:dd:ee:ff;
  client-hostname "workstation-01";
}
```

### Parsing ISC DHCP Leases

```bash
# View active leases
grep -A 10 "binding state active" /var/lib/dhcp/dhcpd.leases

# Count active leases
grep -c "binding state active" /var/lib/dhcp/dhcpd.leases

# Find lease by MAC address
grep -B 5 "aa:bb:cc:dd:ee:ff" /var/lib/dhcp/dhcpd.leases

# Extract IP, MAC, hostname from active leases
awk '/^lease /{ip=$2} /hardware ethernet/{mac=$3} /client-hostname/{host=$2; print ip, mac, host}' /var/lib/dhcp/dhcpd.leases
```

### ISC DHCP Docker Compose

```yaml
version: "3.8"
services:
  isc-dhcp:
    image: networkboot/dhcpd:latest
    container_name: isc-dhcp
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./dhcpd.conf:/etc/dhcp/dhcpd.conf:ro
      - dhcp-leases:/var/lib/dhcp
    environment:
      - DHCP_INTERFACE=eth0
    restart: unless-stopped

volumes:
  dhcp-leases:
```

## Dnsmasq Lease Management

Dnsmasq is a lightweight DNS and DHCP server popular in small networks, home labs, and embedded systems. Its lease management is simpler but sufficient for smaller deployments.

### Dnsmasq Lease File Format

```
# /var/lib/misc/dnsmasq.leases
# timestamp MAC IP hostname clientID
1715673000 aa:bb:cc:dd:ee:ff 192.168.1.105 workstation-01 *
1715673000 11:22:33:44:55:66 192.168.1.106 laptop-02 *
1715673000 77:88:99:aa:bb:cc 192.168.1.107 phone-03 *
```

### Dnsmasq Configuration

```bash
# /etc/dnsmasq.conf
# DHCP settings
dhcp-range=192.168.1.100,192.168.1.200,12h
dhcp-leasefile=/var/lib/misc/dnsmasq.leases
dhcp-authoritative

# DNS settings
server=8.8.8.8
server=8.8.4.4

# Optional: static leases
dhcp-host=aa:bb:cc:dd:ee:ff,192.168.1.50,server-01,720h
dhcp-host=11:22:33:44:55:66,192.168.1.51,printer-01,infinite
```

### Dnsmasq Lease Analysis

```bash
# View all leases
cat /var/lib/misc/dnsmasq.leases

# Find device by IP
awk '$3 == "192.168.1.105"' /var/lib/misc/dnsmasq.leases

# List devices with hostnames
awk '$4 != "*" {print $3, $4}' /var/lib/misc/dnsmasq.leases

# Lease count
wc -l /var/lib/misc/dnsmasq.leases
```

### Dnsmasq Docker Compose

```yaml
version: "3.8"
services:
  dnsmasq:
    image: jpillora/dnsmasq:latest
    container_name: dnsmasq
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "67:67/udp"
    volumes:
      - ./dnsmasq.conf:/etc/dnsmasq.conf:ro
      - dnsmasq-leases:/var/lib/misc
    cap_add:
      - NET_ADMIN
    restart: unless-stopped

volumes:
  dnsmasq-leases:
```

## DHCP Lease Management Comparison

| Feature | Kea DHCP | ISC DHCP | Dnsmasq |
|---------|----------|----------|---------|
| Lease Backend | MySQL, PostgreSQL, CQL, Memfile | Text file | Text file |
| REST API | Yes (control agent) | No | No |
| Lease Query | SQL + API commands | File parsing | File parsing |
| Lease Analytics | Built-in statistics | Manual | Manual |
| IPv4 + IPv6 | Separate daemons | Separate daemons | Single daemon |
| DHCPv6 | Full support | Full support | Limited |
| Hook System | Yes (C++/Python) | No | No |
| Scale | Carrier-grade | Enterprise | Small/home |
| Active Development | Yes (ISC) | Deprecated | Yes |
| Docker Image | Official (isc/kea) | Community | Community (jpillora) |

## Choosing the Right DHCP Server

### Choose Kea DHCP when:
- You need programmatic lease access via REST API or SQL queries
- You're managing hundreds or thousands of leases
- You need integration with IPAM systems
- You require carrier-grade performance and reliability
- You want active development and modern architecture

### Choose ISC DHCP when:
- You have existing infrastructure and configurations
- You need a proven, stable solution for medium-sized networks
- You prefer human-readable lease files for manual inspection
- You're not ready to migrate to Kea

### Choose Dnsmasq when:
- You're managing a small network (under 100 devices)
- You need DNS and DHCP in a single lightweight daemon
- You're running on resource-constrained hardware (Raspberry Pi, embedded)
- You prefer simplicity over advanced features

## Why Self-Host DHCP with Lease Management?

Running your own DHCP server with proper lease management gives you complete visibility into network device assignment. Unlike cloud-managed DHCP services, self-hosted solutions keep all lease data within your infrastructure and provide deep integration with monitoring, IPAM, and security systems.

**Network visibility:** The DHCP lease database is a real-time map of every device on your network. By querying lease data, you can instantly identify which device holds a specific IP, when it connected, and whether it's expected. This is invaluable for troubleshooting connectivity issues and detecting unauthorized devices.

**Security auditing:** DHCP lease logs provide a historical record of network access. By analyzing lease data over time, you can detect anomalies such as devices requesting addresses outside normal hours, MAC address spoofing patterns, or sudden spikes in lease requests that might indicate a DHCP starvation attack.

**IPAM integration:** Kea's MySQL/PostgreSQL backends enable direct integration with IP address management tools. Lease data can feed into dashboards showing pool utilization, lease duration trends, and device inventory — essential for network capacity planning and compliance reporting.

For related reading, see our [network access control guide](../2026-04-19-packetfence-vs-freeradius-vs-coovachilli-self-hosted-nac-guide-2026/) and [DNS failover guide](../2026-04-24-self-hosted-dns-failover-keepalived-powerdns-haproxy-guide-2026/).

## FAQ

### What is a DHCP lease and how long does it last?

A DHCP lease is a temporary assignment of an IP address to a network device. The lease duration is configured on the DHCP server and typically ranges from 1 hour to 24 hours. When the lease expires, the device must renew it or the IP address returns to the available pool.

### How do I view active DHCP leases?

For Kea DHCP with MySQL backend, query the `lease4` table with SQL. For ISC DHCP, parse the `/var/lib/dhcp/dhcpd.leases` text file. For Dnsmasq, read `/var/lib/misc/dnsmasq.leases`. Kea also provides a REST API for lease queries.

### Can I change a DHCP lease without restarting the server?

Kea DHCP supports dynamic lease manipulation via its REST API — you can add, delete, and modify leases without restarting. ISC DHCP and Dnsmasq require manual editing of the lease file followed by a server reload (`kill -HUP`).

### What happens when the DHCP lease pool is exhausted?

When all available IP addresses are leased, new clients cannot obtain an IP address. Kea DHCP logs this condition and can send alerts. To prevent exhaustion, reduce lease times, expand the address pool, or implement DHCP snooping to prevent lease abuse.

### How do I monitor DHCP lease utilization?

Kea DHCP has built-in statistics accessible via the control agent API. For ISC DHCP and Dnsmasq, you can parse the lease file and calculate the ratio of active leases to total pool size. Tools like Prometheus + dhcp_exporter can export lease metrics for dashboard visualization.

### Is ISC DHCP still supported?

ISC DHCP is deprecated. ISC recommends migrating to Kea DHCP, which is actively developed and supported. Kea provides a migration path from ISC DHCP configurations and lease databases. While ISC DHCP still works, it receives only critical security fixes.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DHCP Lease Management: Kea vs ISC DHCP vs Dnsmasq",
  "description": "Complete guide to managing DHCP lease databases and lease analytics. Compare Kea DHCP, ISC DHCP, and Dnsmasq for lease tracking and analysis.",
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
