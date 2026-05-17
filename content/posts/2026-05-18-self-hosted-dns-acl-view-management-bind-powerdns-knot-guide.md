---
title: "Self-Hosted DNS ACL & View Management — BIND vs PowerDNS vs Knot DNS"
date: "2026-05-18"
tags: ["dns", "acl", "networking", "self-hosted", "security"]
draft: false
---

## Introduction

Access Control Lists (ACLs) and DNS Views are essential features for any production DNS server. They allow you to control **who can query your DNS server**, **which records different clients see**, and **how traffic is routed** based on the client's network location.

In self-hosted environments, DNS ACLs and views are used for split-horizon DNS (different answers for internal vs. external clients), DDoS mitigation (rate-limiting abusive resolvers), and network segmentation (restricting zone transfers to authorized secondaries).

In this guide, we compare how three major open-source DNS servers handle ACLs and view management: **BIND**, **PowerDNS**, and **Knot DNS**.

## Quick Comparison

| Feature | BIND 9 | PowerDNS | Knot DNS |
|---------|--------|----------|----------|
| Stars | ISC-maintained | 2,280+ | 400+ |
| Language | C | C++ | C |
| ACL Syntax | `acl` blocks | `allow-from` | `acl` rules |
| DNS Views | ✅ Full (views{}) | ✅ Via geo backend | ❌ No native views |
| Zone Transfers | ✅ AXFR/IXFR | ✅ With ACLs | ✅ AXFR/IXFR |
| Response Policy | ✅ RPZ | ✅ Via PowerDNS Recursor | ❌ Limited |
| Geo-based routing | Via views | ✅ GeoIP backend | ❌ No |
| Rate Limiting | ✅ response-policy | ✅ Built-in | ✅ Built-in |
| API Management | ❌ CLI only | ✅ REST API | ❌ CLI only |
| Configuration | File-based | Database + files | YAML files |
| License | MPL 2.0 | GPL-2.0 | GPL-3.0 |

## BIND 9 — The Traditional DNS Server

[BIND](https://www.isc.org/bind/) (Berkeley Internet Name Domain) is the oldest and most widely deployed DNS server. Its ACL and view system is the reference implementation that other DNS servers are measured against.

### Key Features

- **Full ACL system**: Define named IP address lists for use throughout the configuration
- **DNS Views**: Serve different zone data to different client groups (split-horizon DNS)
- **Response Policy Zones (RPZ)**: Block or redirect queries based on threat intelligence feeds
- **Granular access control**: Per-zone, per-view, and per-operation ACL enforcement
- **TSIG authentication**: Cryptographically sign zone transfers and dynamic updates

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  bind9:
    image: ubuntu/bind9:latest
    container_name: bind9
    environment:
      - BIND9_USER=root
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "953:953/tcp"
    volumes:
      - ./config:/etc/bind
      - ./zones:/var/lib/bind
    restart: unless-stopped
```

### named.conf Example with ACLs and Views

```conf
// Define ACLs
acl "internal" {
    192.168.0.0/16;
    10.0.0.0/8;
    172.16.0.0/12;
};

acl "trusted-resolvers" {
    1.1.1.1;
    8.8.8.8;
};

acl "blocked" {
    203.0.113.0/24;
    198.51.100.0/24;
};

// Internal view — full zone data for internal clients
view "internal" {
    match-clients { internal; localhost; };
    recursion yes;
    allow-recursion { internal; };

    zone "example.com" {
        type master;
        file "/var/lib/bind/example.com.internal";
        allow-transfer { trusted-resolvers; };
    };

    // Include RPZ for threat blocking
    response-policy {
        zone "rpz.local";
        zone "rpz.threatfeed";
    };
};

// External view — limited records for public clients
view "external" {
    match-clients { any; };
    recursion no;

    zone "example.com" {
        type master;
        file "/var/lib/bind/example.com.external";
        allow-transfer { none; };
    };
};
```

### Installation

```bash
# Debian/Ubuntu
sudo apt install bind9 bind9utils bind9-doc

# Red Hat/CentOS
sudo yum install bind bind-utils

# Start and enable
sudo systemctl enable --now named

# Test configuration
sudo named-checkconf /etc/bind/named.conf

# Query test
dig @localhost example.com A
```

## PowerDNS — Modern DNS with API-First Design

[PowerDNS](https://github.com/PowerDNS/pdns) is a high-performance DNS server with a modern architecture. Unlike BIND's file-based configuration, PowerDNS stores zone data in databases (MySQL, PostgreSQL, SQLite) and provides a full REST API for management.

### Key Features

- **Database-backed zones**: Store DNS records in MySQL, PostgreSQL, or SQLite — enabling multi-master setups
- **REST API**: Full programmatic control over zones, records, and ACLs
- **GeoIP backend**: Serve different records based on the client's geographic location
- **Flexible ACL system**: `allow-axfr-ips`, `allow-notify-from`, `allow-recursion` directives
- **PowerDNS Recursor**: Separate recursive resolver with built-in RPZ and Lua scripting
- **DNSSEC native**: Full DNSSEC signing and validation support

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  pdns:
    image: pschiffe/pdns-mysql:latest
    container_name: pdns
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "8081:8081/tcp"
    environment:
      - PDNS_gmysql_host=mysql
      - PDNS_gmysql_user=pdns
      - PDNS_gmysql_password=pdns-password
      - PDNS_gmysql_dbname=pdns
      - PDNS_api=yes
      - PDNS_api-key=super-secret-key
    depends_on:
      - mysql
    restart: unless-stopped

  mysql:
    image: mysql:8
    container_name: pdns-mysql
    environment:
      MYSQL_ROOT_PASSWORD: root-pass
      MYSQL_DATABASE: pdns
      MYSQL_USER: pdns
      MYSQL_PASSWORD: pdns-password
    volumes:
      - mysql-data:/var/lib/mysql

volumes:
  mysql-data:
```

### pdns.conf ACL Configuration

```conf
# Allow zone transfers to specific IPs
allow-axfr-ips=192.168.1.0/24,10.0.0.0/8

# Allow NOTIFY from specific masters
allow-notify-from=192.168.1.100,10.0.0.1

# Enable API for management
api=yes
api-key=your-api-key
api-readonly=no

# Recursion ACL (for recursor)
allow-from=192.168.0.0/16,10.0.0.0/8

# GeoIP backend for location-aware responses
launch=gmysql,geoip
geoip-database-files=/etc/pdns/GeoLite2-Country.mmdb
geoip-zones-file=/etc/pdns/geoip-zones.yaml
```

### Managing Records via REST API

```bash
# Create a new zone
curl -X POST http://localhost:8081/api/v1/servers/localhost/zones   -H "X-API-Key: your-api-key"   -H "Content-Type: application/json"   -d '{
    "name": "example.com.",
    "kind": "Native",
    "masters": [],
    "nameservers": ["ns1.example.com.", "ns2.example.com."]
  }'

# Add a record
curl -X PATCH http://localhost:8081/api/v1/servers/localhost/zones/example.com.   -H "X-API-Key: your-api-key"   -H "Content-Type: application/json"   -d '{
    "rrsets": [{
      "name": "www.example.com.",
      "type": "A",
      "ttl": 300,
      "changetype": "REPLACE",
      "records": [{"content": "192.168.1.10", "disabled": false}]
    }]
  }'
```

### Installation

```bash
# Debian/Ubuntu — PowerDNS repository
sudo apt install pdns-server pdns-backend-mysql

# Red Hat/CentOS
sudo yum install pdns pdns-backend-mysql

# Initialize the database
mysql -u root -p < /usr/share/pdns-backend-mysql/schema/mysql.sql

# Start the service
sudo systemctl enable --now pdns
```

## Knot DNS — High-Performance Authoritative Server

[Knot DNS](https://github.com/CZ-NIC/knot) is a high-performance authoritative-only DNS server developed by CZ.NIC. It prioritizes speed and correctness over feature breadth, making it ideal for large-scale DNS hosting.

### Key Features

- **High-performance design**: Optimized for handling millions of queries per second
- **Simple YAML configuration**: Clean, readable configuration format
- **ACL-based access control**: IP-based ACLs for zone transfers, updates, and queries
- **DNSSEC signing**: Automatic DNSSEC signing with online and offline KSK/ZSK management
- **Zone journaling**: Efficient IXFR support with built-in journaling
- **Dynamic DNS**: Full RFC 2136 dynamic update support

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  knot:
    image: cznic/knot:latest
    container_name: knot
    ports:
      - "53:53/tcp"
      - "53:53/udp"
    volumes:
      - ./knot.conf:/etc/knot/knot.conf:ro
      - ./zones:/var/lib/knot/zones
    restart: unless-stopped
```

### knot.conf ACL Example

```yaml
# Define ACLs
acl:
  - id: internal_acl
    address: 192.168.0.0/16
    action: [transfer, notify, update]

  - id: secondary_acl
    address: 10.0.0.0/8
    action: [transfer]

  - id: blocked_acl
    address: 203.0.113.0/24
    action: [deny]

# Server configuration
server:
  listen: ["0.0.0.0@53", "::@53"]
  user: knot:knot

# Zone with ACL enforcement
zone:
  - domain: example.com
    file: "example.com.zone"
    acl: [internal_acl, secondary_acl]
    dnssec-signing: on
    dnssec-policy: "default"
    journal-db-mode: mmap
```

### Installation

```bash
# Debian/Ubuntu
sudo apt install knot knot-utils

# Red Hat/CentOS
sudo yum install knot

# Start and enable
sudo systemctl enable --now knot

# Test configuration
sudo knotc conf-check

# List zones
sudo knotc zone-list
```

## Choosing the Right DNS Server for ACL/View Management

| Use Case | Recommended Server |
|----------|-------------------|
| Split-horizon DNS (internal/external views) | **BIND** — Mature view system with granular per-view config |
| API-driven DNS management | **PowerDNS** — Full REST API, database-backed zones |
| Geo-based DNS routing | **PowerDNS** — GeoIP backend with automatic record selection |
| Maximum query performance | **Knot DNS** — Optimized for millions of QPS |
| Threat intelligence integration | **BIND** — Full RPZ support with multiple policy zones |
| Multi-master DNS setup | **PowerDNS** — Database replication handles multi-master natively |

## Why Self-Host Your DNS ACL Infrastructure?

Running your own DNS server with proper ACL and view management instead of relying on your registrar's basic DNS offering provides critical advantages:

**Split-horizon DNS resolution**: Internal clients can resolve internal hostnames (database.internal.example.com, monitoring.internal.example.com) while external clients see only public records. This is essential for any organization running both internal and public-facing services.

**Zone transfer security**: By restricting AXFR/IXFR transfers to authorized secondary servers only, you prevent attackers from enumerating your entire DNS zone. All three servers support granular transfer ACLs, but PowerDNS's database backend makes it easier to audit who has received zone data.

**Geographic traffic routing**: PowerDNS's GeoIP backend serves different IP addresses based on the client's location — directing European users to EU servers and US users to US servers. This reduces latency and helps with data sovereignty compliance.

**Threat blocking with RPZ**: BIND's Response Policy Zones let you block queries to known malicious domains, redirect phishing sites to a warning page, or enforce corporate content policies — all at the DNS layer, before any connection is established.

**Rate limiting and abuse prevention**: All three servers support query rate limiting to prevent DNS amplification attacks and recursive resolver abuse. This is critical when running an authoritative DNS server exposed to the public internet.

For related reading, see our [DNS-over-HTTPS proxy comparison](../2026-04-25-coredns-vs-dnsdist-vs-knot-resolver-self-hosted-doh-server-guide-2026/) and [split-horizon DNS guide](../2026-04-24-self-hosted-split-horizon-dns-pihole-dnsmasq-coredns-bind9-guide-2026/).

## FAQ

### What are DNS ACLs and why do I need them?

DNS Access Control Lists (ACLs) define which IP addresses are allowed to perform specific operations on your DNS server: querying, zone transfers (AXFR/IXFR), dynamic updates, and recursion. Without proper ACLs, anyone on the internet could transfer your entire zone file (revealing all your hosts), abuse your recursive resolver for amplification attacks, or inject false DNS records via unauthorized dynamic updates.

### What is split-horizon DNS?

Split-horizon DNS (also called split-brain DNS) serves different DNS responses based on the client's source IP address. Internal clients might see private IP addresses (192.168.1.10) while external clients see public IPs (203.0.113.10). BIND implements this through `view` blocks, while PowerDNS uses its GeoIP backend for similar functionality.

### Does Knot DNS support DNS views?

No, Knot DNS does not support native DNS views. It is designed as an authoritative-only server optimized for performance. If you need split-horizon DNS with Knot, you would need to run multiple Knot instances on different ports or IP addresses and use a frontend proxy (like dnsdist) to route clients to the appropriate instance.

### Can I migrate from BIND to PowerDNS?

Yes. PowerDNS provides a `zone2sql` tool that converts BIND zone files to SQL format for the PowerDNS database. The migration process involves: exporting zones with `zone2sql`, importing into a MySQL/PostgreSQL database, updating nameserver delegation, and verifying resolution. Plan for a maintenance window as nameserver changes can take hours to propagate globally.

### What is Response Policy Zones (RPZ)?

RPZ is a DNS feature that lets you override DNS responses based on policy rules. Think of it as a DNS-level firewall — you can block queries to known malware domains, redirect phishing sites to a warning page, or enforce corporate content filtering policies. BIND has the most mature RPZ implementation; PowerDNS Recursor also supports RPZ.

### How do I test my DNS ACL configuration?

Use `dig` or `kdig` to query your DNS server from different IP addresses: `dig @dns-server.example.com example.com AXFR` should succeed from allowed IPs and fail (REFUSED) from blocked ones. For BIND, use `rndc queryperf` to load-test ACL enforcement. For PowerDNS, use the REST API to verify `allow-axfr-ips` settings.

## JSON-LD Structured Data

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DNS ACL & View Management — BIND vs PowerDNS vs Knot DNS",
  "description": "Compare three open-source DNS servers for ACL and view management: BIND (traditional views), PowerDNS (API-first with GeoIP), and Knot DNS (high-performance). Includes Docker Compose configs and security best practices.",
  "datePublished": "2026-05-18",
  "dateModified": "2026-05-18",
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
