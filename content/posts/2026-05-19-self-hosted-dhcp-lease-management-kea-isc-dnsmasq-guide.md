---
title: "Self-Hosted DHCP Lease Management: Kea vs ISC DHCP vs dnsmasq Lease Analysis"
date: "2026-05-19"
tags: ["dhcp", "network-management", "kea", "dnsmasq", "lease-management"]
draft: false
---

Dynamic Host Configuration Protocol (DHCP) is the backbone of network address assignment, but managing DHCP leases at scale requires more than just running a DHCP server. Whether you're troubleshooting IP conflicts, auditing network usage, or planning capacity expansions, having proper visibility into your DHCP lease database is essential.

This guide compares lease management capabilities across three widely-used open-source DHCP implementations: **ISC Kea** (the modern successor), **ISC DHCP** (the legacy standard), and **dnsmasq** (the lightweight alternative).

## Understanding DHCP Lease Management

Every DHCP server maintains a lease database that tracks which IP addresses have been assigned to which MAC addresses, when those leases were granted, and when they expire. Effective lease management means being able to query, analyze, and sometimes modify this database without disrupting active network clients.

### Key Lease Management Functions

- **Lease inspection** — View active leases with client details
- **Lease expiry tracking** — Monitor expiring and expired leases
- **IP address auditing** — Identify unused ranges and conflicts
- **Lease renewal control** — Force renew or release specific leases
- **Historical lease logging** — Track assignment history for compliance
- **Capacity planning** — Analyze utilization trends across subnets

## ISC Kea Lease Management

[ISC Kea](https://github.com/isc-projects/kea) is the modern DHCP server from ISC, designed from the ground up to replace the legacy ISC DHCP server. With 715 GitHub stars and active development, Kea provides a REST API, modular architecture, and pluggable database backends for lease storage.

### Lease Database Backends

Kea supports multiple backends for lease storage:

```json
{
  "Dhcp4": {
    "lease-database": {
      "type": "mysql",
      "name": "kea_leases",
      "user": "kea",
      "password": "***",
      "host": "localhost",
      "port": 3306
    },
    "hosts-database": {
      "type": "mysql",
      "name": "kea_hosts",
      "user": "kea",
      "password": "***"
    }
  }
}
```

Kea supports Memfile (in-memory), MySQL, PostgreSQL, and Cassandra backends. The choice of backend determines your lease query capabilities — SQL backends enable complex queries, while Memfile is fastest for small deployments.

### REST API for Lease Queries

Kea's control channel provides a JSON-based REST API for lease management:

```bash
# Query all active leases
curl -s -X POST http://localhost:8000/ \
  -d '{"command": "lease4-get-all"}' | python3 -m json.tool

# Query lease by IP address
curl -s -X POST http://localhost:8000/ \
  -d '{"command": "lease4-get", "arguments": {"ip-address": "192.168.1.100"}}'

# Query lease by MAC address
curl -s -X POST http://localhost:8000/ \
  -d '{"command": "lease4-get-by-hw-address", "arguments": {"hw-address": "aa:bb:cc:dd:ee:ff"}}'

# Delete an expired lease
curl -s -X POST http://localhost:8000/ \
  -d '{"command": "lease4-del", "arguments": {"ip-address": "192.168.1.50"}}'
```

### Kea Dashboard

For web-based lease management, the Kea Control Agent provides a RESTful interface that third-party dashboards can consume:

```yaml
version: "3.8"
services:
  kea-dhcp4:
    image: internetconsortium/kea:latest
    ports:
      - "67:67/udp"
      - "8000:8000"
    volumes:
      - ./kea-dhcp4.conf:/etc/kea/kea-dhcp4.conf
    environment:
      - KEA_DHCP4_SERVER=yes
```

## ISC DHCP Lease Management

[ISC DHCP](https://github.com/isc-projects/dhcp) is the legacy DHCP server that served as the industry standard for decades. With 203 GitHub stars and a long history, it uses a simple text-based lease file format that is easy to parse but lacks real-time query capabilities.

### Lease File Format

ISC DHCP stores leases in a plain text file at `/var/lib/dhcp/dhcpd.leases`:

```
lease 192.168.1.100 {
  starts 0 2026/06/01 08:00:00;
  ends 0 2026/06/01 20:00:00;
  cltt 0 2026/06/01 08:00:00;
  binding state active;
  next binding state free;
  rewind binding state free;
  hardware ethernet aa:bb:cc:dd:ee:ff;
  uid "ª»ÌÝîÿ";
  client-hostname "laptop-workstation";
}
```

### Parsing Lease Files

```bash
# List all active leases
grep "binding state active" /var/lib/dhcp/dhcpd.leases -B 8 | grep -E "lease|hardware|client-hostname|ends"

# Find leases for a specific MAC address
grep -A 10 "aa:bb:cc:dd:ee:ff" /var/lib/dhcp/dhcpd.leases

# Count active leases per subnet
awk '/^lease /{ip=$2} /binding state active/{print ip}' /var/lib/dhcp/dhcpd.leases | \
  awk -F. '{print $1"."$2"."$3".0/24"}' | sort | uniq -c | sort -rn
```

### Limitations

ISC DHCP has been in maintenance mode since 2018. It does not support:
- Real-time lease queries without reading the entire lease file
- REST API or programmatic lease management
- High availability with automatic lease database synchronization
- IPv6 dual-stack management in a unified interface

## dnsmasq Lease Management

[dnsmasq](https://thekelleys.org.uk/dnsmasq/doc.html) is a lightweight DNS and DHCP server widely used in home networks and small deployments. Its lease file format is even simpler than ISC DHCP's, making it easy to parse programmatically.

### Lease File Format

dnsmasq stores leases in `/var/lib/misc/dnsmasq.leases`:

```
1717200000 aa:bb:cc:dd:ee:ff 192.168.1.100 laptop-workstation 01:aa:bb:cc:dd:ee:ff
1717203600 11:22:33:44:55:66 192.168.1.101 desktop-pc *
```

Each line contains: timestamp (expiry), MAC address, IP address, hostname, and client ID.

### Querying dnsmasq Leases

```bash
# List all leases with human-readable dates
awk '{printf "%-20s %-18s %-16s %s
", strftime("%Y-%m-%d %H:%M:%S",$1), $2, $3, $4}' \
  /var/lib/misc/dnsmasq.leases

# Find active (non-expired) leases
awk -v now=$(date +%s) '$1 > now {printf "%s %s %s
", $3, $2, $4}' /var/lib/misc/dnsmasq.leases

# Count leases by subnet
awk '{split($3,a,"."); print a[1]"."a[2]"."a[3]".0"}' /var/lib/misc/dnsmasq.leases | \
  sort | uniq -c | sort -rn
```

### Docker Deployment

```yaml
version: "3.8"
services:
  dnsmasq:
    image: jpillora/dnsmasq:latest
    network_mode: host
    volumes:
      - ./dnsmasq.conf:/etc/dnsmasq.conf:ro
      - ./leases:/var/lib/misc
    restart: unless-stopped
```

## Feature Comparison

| Feature | ISC Kea | ISC DHCP | dnsmasq |
|---------|---------|----------|---------|
| REST API | Yes | No | No |
| SQL backend | Yes | No | No |
| Real-time queries | Yes | No | No |
| Lease expiration tracking | Yes | Manual parse | Manual parse |
| IPv6 support | Full | Full | Full |
| High availability | Yes (HA hook) | Manual failover | No |
| Active development | Yes | Maintenance only | Yes |
| Docker image | Official | Community | Community |
| GitHub Stars | 715 | 203 | N/A |
| Best for | Enterprise | Legacy migration | Small networks |

## Choosing the Right DHCP Lease Manager

**Use ISC Kea** when:
- You need real-time lease queries via REST API
- You want SQL-backed lease storage for complex reporting
- You're running an enterprise or multi-subnet deployment
- You need high availability with automatic failover

**Use ISC DHCP** when:
- You have an existing deployment that works and doesn't need changes
- You need compatibility with legacy configuration formats
- You're planning a migration to Kea and need a transition period

**Use dnsmasq** when:
- You're running a small network with a few dozen clients
- You want combined DNS and DHCP in a single lightweight process
- You need simple lease file parsing without database overhead

## Why Self-Host DHCP Lease Management?

Controlling your own DHCP lease management infrastructure means you maintain complete visibility into every device connecting to your network. For organizations with compliance requirements, being able to audit IP-to-MAC mappings and track lease history is often mandatory.

Self-hosted DHCP also eliminates dependency on cloud-based DHCP services, ensuring that network address assignment continues even during internet outages. Combined with proper backup procedures for your lease databases, you can recover from server failures without disrupting connected clients.

For network administrators managing multiple subnets, centralized lease management through Kea's REST API enables automation scripts that can detect IP exhaustion before it causes outages, trigger alerts for unusual lease patterns, and generate capacity reports for planning.

For deeper dives into network infrastructure, see our [Kea DHCP high availability guide](../2026-05-10-self-hosted-dhcp-high-availability-kea-ha-vs-isc-dhcp-vs-keepalived-guide/) and [network topology mapping tools](../2026-05-02-self-hosted-network-topology-mapping-netbox-librenms-auto-discovery/).



For related reading, see our [DHCP high availability guide](../2026-05-10-self-hosted-dhcp-high-availability-kea-ha-vs-isc-dhcp-vs-keepalived-guide/) and [network topology mapping tools](../2026-05-02-self-hosted-network-topology-mapping-netbox-librenms-auto-discovery/).

## FAQ

### What is the difference between Kea and ISC DHCP lease files?

Kea stores leases in a database (MySQL, PostgreSQL, or Memfile) with structured schema enabling real-time queries, while ISC DHCP uses a plain text lease file that must be parsed line by line. Kea's database approach enables instant lookups by IP, MAC, or hostname without scanning the entire file.

### Can I migrate from ISC DHCP to Kea without losing active leases?

Yes. Kea provides a lease migration tool (`kea-admin lease-init`) that can import ISC DHCP lease files into Kea's database. This allows you to transition without disconnecting any clients — their active leases will be preserved in the new system.

### How do I monitor DHCP lease utilization?

With Kea, use the REST API to query lease counts per subnet. With ISC DHCP and dnsmasq, parse the lease file periodically and compare active leases against your configured subnet ranges. Set alerts when utilization exceeds 80%.

### Does dnsmasq support DHCP failover?

No. dnsmasq does not support DHCP failover or high availability. For HA setups, use ISC Kea with its DHCPv4 HA hook, or deploy two dnsmasq instances with non-overlapping IP ranges.

### How do I back up DHCP lease data?

For Kea, back up the underlying SQL database using standard dump tools (mysqldump, pg_dump). For ISC DHCP, copy the lease file at `/var/lib/dhcp/dhcpd.leases`. For dnsmasq, copy `/var/lib/misc/dnsmasq.leases`. All three can be backed up while the server is running.

### Can I query dnsmasq leases via API?

No, dnsmasq does not provide an API. You must read the lease file directly from disk. For programmatic access, write a wrapper script that parses the lease file and exposes a simple HTTP endpoint.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DHCP Lease Management: Kea vs ISC DHCP vs dnsmasq Lease Analysis",
  "description": "Compare DHCP lease management capabilities across ISC Kea, ISC DHCP, and dnsmasq — including REST APIs, lease databases, parsing tools, and Docker deployments.",
  "datePublished": "2026-05-19",
  "dateModified": "2026-05-19",
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
