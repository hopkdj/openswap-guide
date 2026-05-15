---
title: "Self-Hosted DHCP Lease Analysis: Kea Lease Database vs ISC DHCP Logs vs Dnsmasq Lease Tools (2026)"
date: "2026-05-15"
tags: ["dhcp", "networking", "lease-analysis", "kea", "dnsmasq", "self-hosted"]
draft: false
---

Dynamic Host Configuration Protocol (DHCP) is the backbone of IP address management in every network from home labs to enterprise data centers. But when devices cannot connect, IP conflicts arise, or you need to audit address assignments, understanding what your DHCP server has handed out — and when — becomes critical.

This guide compares three open-source approaches to DHCP lease analysis: the **ISC Kea lease database**, **ISC DHCP server log parsing**, and **Dnsmasq lease file analysis**. Each method offers different visibility into DHCP lease state, from real-time database queries to historical log-based forensics.

## What Is DHCP Lease Analysis?

DHCP lease analysis involves examining the records of IP address assignments made by your DHCP server. A lease record typically contains:

- **Client MAC address** — The hardware identifier of the requesting device
- **Assigned IP address** — The IPv4 or IPv6 address leased to the client
- **Lease start time** — When the address was assigned
- **Lease expiry time** — When the lease expires and the address becomes available again
- **Client hostname** — The device's reported hostname (if provided)
- **Lease state** — Active, expired, released, or abandoned

Understanding these records helps network administrators troubleshoot connectivity issues, plan IP address pool sizing, detect rogue DHCP clients, and maintain accurate network inventory.

## ISC Kea: Modern DHCP with Queryable Lease Database

[ISC Kea](https://github.com/isc-projects/kea) is ISC's next-generation DHCP server, designed to replace the legacy ISC DHCP server. Kea stores lease information in a queryable database (Memfile, MySQL, PostgreSQL, or Cassandra), enabling real-time lease analysis through SQL queries and a REST API.

**GitHub:** [isc-projects/kea](https://github.com/isc-projects/kea) — 714+ stars, actively developed

### Lease Database Backends

Kea supports multiple storage backends for lease data:

- **Memfile** — CSV files on disk, suitable for small deployments
- **MySQL/MariaDB** — Full relational database with indexing
- **PostgreSQL** — Production-grade with advanced query capabilities
- **Cassandra** — Distributed database for large-scale deployments

### Docker Compose Configuration

```yaml
version: "3.8"

services:
  kea-dhcp:
    image: kea:latest
    container_name: kea-dhcp
    network_mode: "host"
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./kea/etc:/etc/kea
      - ./kea/log:/var/log/kea
    depends_on:
      - kea-db
    restart: unless-stopped

  kea-db:
    image: postgres:16
    container_name: kea-db
    environment:
      POSTGRES_DB: kea
      POSTGRES_USER: kea
      POSTGRES_PASSWORD: kea-secret-password
    volumes:
      - kea-db-data:/var/lib/postgresql/data
      - ./kea/init-db.sql:/docker-entrypoint-initdb.d/init.sql
    restart: unless-stopped

volumes:
  kea-db-data:
```

### Kea Lease Database Schema

When using PostgreSQL, Kea creates the following lease tables:

```sql
-- IPv4 leases table
CREATE TABLE lease4 (
    address NUMERIC(39,0) NOT NULL,
    hwaddr BYTEA,
    client_id BYTEA,
    valid_lifetime INTEGER,
    expire TIMESTAMP,
    subnet_id INTEGER,
    fqdn_fwd BOOLEAN,
    fqdn_rev BOOLEAN,
    hostname TEXT,
    state INTEGER DEFAULT 0,
    user_context TEXT,
    cltt TIMESTAMP,
    PRIMARY KEY (address)
);

-- IPv6 leases table
CREATE TABLE lease6 (
    address NUMERIC(39,0) NOT NULL,
    duid BYTEA NOT NULL,
    valid_lifetime INTEGER,
    expire TIMESTAMP,
    subnet_id INTEGER,
    pref_lifetime INTEGER,
    lease_type INTEGER,
    iaid BYTEA,
    fqdn_fwd BOOLEAN,
    fqdn_rev BOOLEAN,
    hostname TEXT,
    state INTEGER DEFAULT 0,
    user_context TEXT,
    cltt TIMESTAMP,
    PRIMARY KEY (address, duid, iaid, lease_type)
);
```

### Querying Kea Leases

```sql
-- Find all active leases in a subnet
SELECT address, hostname, hwaddr, expire
FROM lease4
WHERE subnet_id = 1 AND state = 0
ORDER BY expire ASC;

-- Find expired leases (candidates for cleanup)
SELECT address, hostname, expire
FROM lease4
WHERE expire < NOW() AND state = 0;

-- Count leases by subnet
SELECT subnet_id, COUNT(*) as lease_count
FROM lease4
WHERE state = 0
GROUP BY subnet_id;

-- Find a specific device by MAC address
SELECT address, hostname, expire, cltt
FROM lease4
WHERE hwaddr = decode('001122334455', 'hex');

-- Lease utilization percentage
SELECT 
    subnet_id,
    COUNT(*) as used_leases,
    (SELECT COUNT(*) FROM lease4) * 100.0 / 
    (SELECT COUNT(*) FROM lease4 WHERE state = 0 OR state = 1) as utilization_pct
FROM lease4
GROUP BY subnet_id;
```

### Kea REST API for Lease Queries

```bash
# Get lease4 collection
curl -X POST -d '{
  "command": "lease4-get-all",
  "service": ["dhcp4"]
}' http://localhost:8000/ | python3 -m json.tool

# Get specific lease by IP
curl -X POST -d '{
  "command": "lease4-get",
  "arguments": {
    "ip-address": "192.168.1.100"
  },
  "service": ["dhcp4"]
}' http://localhost:8000/

# Get lease count by subnet
curl -X POST -d '{
  "command": "statistic-get",
  "arguments": {
    "name": ["total-clients"]
  }
}' http://localhost:8000/
```

## ISC DHCP Server: Log-Based Lease Analysis

The legacy **ISC DHCP server** (dhcpd) stores lease information in a flat text file (`/var/lib/dhcp/dhcpd.leases`) and writes assignment events to syslog. While the server is no longer actively developed (superseded by Kea), it remains widely deployed in production networks.

### Lease File Format

The ISC DHCP lease file uses a simple text format:

```
lease 192.168.1.100 {
  starts 4 2026/05/15 10:30:00;
  ends 5 2026/05/16 10:30:00;
  tstp 5 2026/05/16 10:30:00;
  cltt 4 2026/05/15 10:30:00;
  binding state active;
  next binding state free;
  rewind binding state free;
  hardware ethernet 00:11:22:33:44:55;
  uid ""3DU";
  client-hostname "workstation-01";
}
```

### Parsing ISC DHCP Leases with Python

```python
#!/usr/bin/env python3
"""Parse ISC DHCP lease file and generate report."""
import re
from datetime import datetime
from collections import defaultdict

LEASE_FILE = "/var/lib/dhcp/dhcpd.leases"

def parse_leases(filepath):
    leases = []
    with open(filepath) as f:
        content = f.read()
    
    blocks = content.split("lease ")
    for block in blocks[1:]:  # Skip header
        ip_match = re.match(r"([\d.]+)", block)
        if not ip_match:
            continue
        ip = ip_match.group(1)
        
        hw_match = re.search(r"hardware ethernet ([\da-f:]+)", block)
        host_match = re.search(r'client-hostname "([^"]+)"', block)
        state_match = re.search(r"binding state (\w+)", block)
        ends_match = re.search(r"ends (\d.+?);", block)
        
        leases.append({
            "ip": ip,
            "mac": hw_match.group(1) if hw_match else "unknown",
            "hostname": host_match.group(1) if host_match else "unknown",
            "state": state_match.group(1) if state_match else "unknown",
            "ends": ends_match.group(1) if ends_match else "unknown",
        })
    
    return leases

# Generate summary
leases = parse_leases(LEASE_FILE)
active = [l for l in leases if l["state"] == "active"]
hosts = defaultdict(list)
for l in active:
    hosts[l["hostname"]].append(l["ip"])

print(f"Total leases: {len(leases)}")
print(f"Active leases: {len(active)}")
print(f"Unique hostnames: {len(hosts)}")
```

### Log-Based Lease History

ISC DHCP writes lease events to syslog:

```bash
# Find all DHCP assignments in the last 24 hours
grep "DHCPACK" /var/log/syslog | tail -50

# Find DHCPDECLINE events (clients rejecting offers)
grep "DHCPDECLINE" /var/log/syslog

# Track lease renewal patterns
grep "DHCPREQUEST" /var/log/syslog | awk '{print $1, $2, $3, $NF}' | sort | uniq -c | sort -rn
```

## Dnsmasq: Lightweight DHCP with Simple Lease File

[Dnsmasq](https://thekelleys.org.uk/dnsmasq/) is a lightweight DNS/DHCP/TFTP server commonly used in home networks, small offices, and as a DHCP server in container environments. Its lease file is simpler than ISC DHCP's but contains all essential information.

### Lease File Format

```
1715857200 00:11:22:33:44:55 192.168.1.100 workstation-01 01:00:11:22:33:44:55
1715860800 00:aa:bb:cc:dd:ee 192.168.1.101 laptop-02 01:00:aa:bb:cc:dd:ee
```

Format: `timestamp mac_address ip_address hostname client_id`

### Docker Compose Configuration

```yaml
version: "3.8"

services:
  dnsmasq:
    image: jpillora/dnsmasq:latest
    container_name: dnsmasq
    cap_add:
      - NET_ADMIN
    network_mode: "host"
    volumes:
      - ./dnsmasq/dnsmasq.conf:/etc/dnsmasq.conf
      - ./dnsmasq/hosts:/etc/ethers
      - ./dnsmasq/leases:/var/lib/misc
    restart: unless-stopped
```

### Dnsmasq DHCP Configuration

```ini
# /etc/dnsmasq.conf

# DHCP range
dhcp-range=192.168.1.100,192.168.1.200,255.255.255.0,24h

# Lease file location
dhcp-leasefile=/var/lib/misc/dnsmasq.leases

# Set lease time
dhcp-lease-max=256

# DHCP options
dhcp-option=3,192.168.1.1
dhcp-option=6,8.8.8.8,8.8.4.4

# Static leases
dhcp-host=00:11:22:33:44:55,192.168.1.50,server-01
dhcp-host=00:aa:bb:cc:dd:ee,192.168.1.51,server-02
```

### Analyzing Dnsmasq Leases

```bash
# View current leases
cat /var/lib/misc/dnsmasq.leases

# Count active leases
wc -l /var/lib/misc/dnsmasq.leases

# Find devices by hostname
grep "workstation" /var/lib/misc/dnsmasq.leases

# Convert timestamps to readable dates
awk '{cmd="date -d @"$1; cmd | getline dt; close(cmd); print dt, $2, $3, $4}'     /var/lib/misc/dnsmasq.leases

# Find lease utilization
TOTAL_POOL=101
CURRENT=$(wc -l < /var/lib/misc/dnsmasq.leases)
echo "Utilization: $CURRENT / $TOTAL_POOL ($(( CURRENT * 100 / TOTAL_POOL ))%)"
```

## Comparison Table

| Feature | ISC Kea | ISC DHCP Server | Dnsmasq |
|---|---|---|---|
| **GitHub Stars** | 714+ | Legacy (EOL) | N/A (project site) |
| **Lease Storage** | Database (SQL/Memfile) | Flat text file | Flat text file |
| **Query Interface** | SQL + REST API | File parsing + logs | File parsing |
| **Real-Time Queries** | Yes | No | No |
| **Historical Analysis** | Via database queries | Via syslog parsing | Limited |
| **DHCPv4** | Yes | Yes | Yes |
| **DHCPv6** | Yes | Yes | Yes |
| **Lease Hooks** | Yes (hook libraries) | Limited | No |
| **HA Support** | Yes (native) | Via failover protocol | No |
| **Pool Sizing Reports** | Via SQL queries | Manual calculation | Manual calculation |
| **Conflict Detection** | Yes | Partial | No |
| **Active Development** | Yes | No (EOL since 2023) | Yes |
| **Best For** | Enterprise networks | Legacy infrastructure | Home/small networks |

## Choosing the Right DHCP Lease Analysis Approach

**Use ISC Kea when:** You need production-grade DHCP with queryable lease data. The database backend enables real-time lease analysis, automated reporting, and integration with IPAM systems. Kea's REST API allows programmatic lease management from monitoring dashboards.

**Use ISC DHCP log analysis when:** You are working with a legacy deployment that has not yet migrated to Kea. Log-based analysis can reconstruct historical lease activity but requires custom parsing scripts and cannot provide real-time queries.

**Use Dnsmasq lease file analysis when:** You run a small network with fewer than 256 DHCP clients. The simple lease file format is easy to parse manually or with basic scripts, but lacks the analytical capabilities of a database backend.

## Building a DHCP Lease Dashboard

For Kea deployments, you can build a real-time dashboard by querying the lease database and feeding results to Grafana:

```python
#!/usr/bin/env python3
"""Export Kea lease metrics for Prometheus."""
import psycopg2
from prometheus_client import Gauge, generate_latest

ACTIVE_LEASES = Gauge("kea_dhcp_active_leases", "Active DHCP leases", ["subnet_id"])
POOL_UTILIZATION = Gauge("kea_dhcp_pool_utilization", "DHCP pool utilization %", ["subnet_id"])

def export_metrics():
    conn = psycopg2.connect("dbname=kea user=kea password=kea-secret")
    cur = conn.cursor()
    
    cur.execute("""
        SELECT subnet_id, COUNT(*) 
        FROM lease4 
        WHERE state = 0 
        GROUP BY subnet_id
    """)
    for subnet_id, count in cur.fetchall():
        ACTIVE_LEASES.labels(subnet_id=str(subnet_id)).set(count)
    
    conn.close()
    return generate_latest()
```

## Why Self-Host Your DHCP Lease Analysis?

Understanding your DHCP lease data is fundamental to network operations. When devices fail to obtain IP addresses, the first question is always: is the pool exhausted? Without lease analysis, you are guessing. With it, you can immediately see pool utilization, identify expired leases that should be reclaimed, and detect patterns like devices requesting addresses faster than expected.

Self-hosted DHCP analysis keeps your network intelligence in-house. Instead of sending lease data to a cloud monitoring service, you query your own database and build custom reports tailored to your environment. This is especially important for organizations with compliance requirements around network access logging.

The migration path from ISC DHCP to Kea is well-documented, and Kea's database backend makes lease analysis dramatically easier than parsing flat text files. For organizations still running the legacy ISC DHCP server, this is a timely opportunity to modernize — ISC officially ended support in September 2023.

If you manage DHCP infrastructure, our [DHCP high availability guide](../2026-05-14-self-hosted-dhcp-high-availability-isc-kea-keepalived-dnsmasq-guide/) covers failover configurations, and the [DHCP failover deep dive](../2026-05-14-self-hosted-dhcp-failover-ha-kea-dhcp-dnsmasq-guide/) provides detailed HA setup instructions. For broader DHCP management, the [DHCP lease management comparison](../2026-05-14-self-hosted-dhcp-lease-management-kea-isc-dnsmasq-guide/) covers the server selection process.

For DHCP infrastructure planning, see our [DHCP high availability guide](../2026-05-14-self-hosted-dhcp-high-availability-isc-kea-keepalived-dnsmasq-guide/), the [DHCP failover deep dive](../2026-05-14-self-hosted-dhcp-failover-ha-kea-dhcp-dnsmasq-guide/), and the [DHCP lease management comparison](../2026-05-14-self-hosted-dhcp-lease-management-kea-isc-dnsmasq-guide/).


For DHCP infrastructure planning, see our [DHCP high availability guide](../2026-05-14-self-hosted-dhcp-high-availability-isc-kea-keepalived-dnsmasq-guide/), the [DHCP failover deep dive](../2026-05-14-self-hosted-dhcp-failover-ha-kea-dhcp-dnsmasq-guide/), and the [DHCP lease management comparison](../2026-05-14-self-hosted-dhcp-lease-management-kea-isc-dnsmasq-guide/).


## FAQ

### How do I find which device has a specific IP address?

In Kea, query the lease database: `SELECT hostname, hwaddr, cltt FROM lease4 WHERE address = inet '192.168.1.100';`. In ISC DHCP, search the lease file: `grep -A 10 "lease 192.168.1.100" /var/lib/dhcp/dhcpd.leases`. In Dnsmasq, grep the lease file for the IP address.

### Why are there more DHCP leases than active devices?

DHCP leases remain in the database until they expire. A device that was once connected but has since left the network will retain its lease until the lease time expires. Use `state = 0` (active) filters in Kea to see only currently active leases.

### How do I detect IP address conflicts in DHCP?

Kea tracks lease state and can detect when a client reports an address conflict via DHCPDECLINE. In ISC DHCP, look for DHCPDECLINE entries in syslog. Dnsmasq does not have built-in conflict detection.

### Can I export DHCP lease data to CSV for reporting?

Yes. For Kea with PostgreSQL: `COPY (SELECT address, hostname, hwaddr, expire FROM lease4 WHERE state = 0) TO '/tmp/dhcp-leases.csv' WITH CSV HEADER;`. For ISC DHCP and Dnsmasq, use the Python parsing scripts shown above.

### What is the maximum number of DHCP leases Kea can handle?

Kea with PostgreSQL backend can handle millions of leases. The Memfile backend is suitable for deployments with up to ~100,000 leases. For larger deployments, use the database backend with proper indexing.

### Should I migrate from ISC DHCP to Kea?

Yes. ISC officially ended support for the legacy DHCP server in September 2023. Kea offers active development, database-backed leases, REST API, HA support, and hook libraries for custom functionality.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DHCP Lease Analysis: Kea Lease Database vs ISC DHCP Logs vs Dnsmasq Lease Tools (2026)",
  "description": "Compare ISC Kea, ISC DHCP Server, and Dnsmasq for self-hosted DHCP lease analysis. Database queries, log parsing, and Docker Compose deployment configs.",
  "datePublished": "2026-05-15",
  "dateModified": "2026-05-15",
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
