---
title: "BIND 9 vs PowerDNS vs NSD: Self-Hosted Authoritative DNS Zone Transfer Guide 2026"
date: 2026-04-30
tags: ["dns", "zone-transfer", "authoritative-dns", "self-hosted", "infrastructure"]
draft: false
description: "Compare BIND 9, PowerDNS, and NSD for self-hosted authoritative DNS with zone transfers (AXFR/IXFR), multi-master setups, and high availability configurations."
---

When running authoritative DNS at scale, managing zone transfers between primary and secondary servers is critical. Zone transfers (AXFR for full transfers, IXFR for incremental updates) ensure DNS records propagate reliably across your infrastructure. This guide compares three battle-tested authoritative DNS servers — **BIND 9**, **PowerDNS**, and **NSD** — to help you choose the right solution for your self-hosted DNS zone management needs.

## Why Self-Host Authoritative DNS with Zone Transfers

Running your own authoritative DNS gives you full control over zone data, transfer policies, and update schedules. Whether you're managing DNS for a corporate network, hosting provider, or multi-region infrastructure, reliable zone transfers are the backbone of DNS availability:

- **High availability**: Secondary servers take over if the primary fails
- **Geographic distribution**: Deploy secondaries close to users for lower latency
- **Load balancing**: Spread query load across multiple authoritative servers
- **Data redundancy**: Protect against data loss with replicated zones
- **Compliance**: Keep DNS data on-premises for regulatory requirements

## BIND 9 vs PowerDNS vs NSD: Comparison at a Glance

| Feature | BIND 9 | PowerDNS Authoritative | NSD |
|---|---|---|---|
| GitHub Stars | N/A (ISC project) | 4,353 | 544 |
| Last Updated | Active (ISC) | 2026-04-29 | 2026-04-24 |
| Language | C | C++ | C |
| AXFR Support | Yes (primary and secondary) | Yes (primary and secondary) | Yes (secondary only) |
| IXFR Support | Yes | Yes | Yes (secondary only) |
| Multi-Master | Via shared backend | Yes (native with database) | No (primary/secondary only) |
| Database Backend | File-based (zone files) | MySQL, PostgreSQL, SQLite, etc. | File-based (zone files) |
| DNSSEC | Full support | Full support | Full support (NSEC3) |
| Dynamic Updates | Yes (RFC 2136) | Yes | No |
| Web UI | No | Yes (PowerDNS-Admin, others) | No |
| License | MPL 2.0 | GPL-2.0 | BSD-2-Clause |

**Key distinction**: NSD is designed as a secondary-only authoritative server — it cannot serve as a primary zone master. This makes it ideal for slave deployments but unsuitable if you need a single-server authoritative setup.

## BIND 9: The Reference Implementation

BIND 9 (Berkeley Internet Name Domain) is the most widely deployed DNS server software, maintained by the Internet Systems Consortium (ISC). It has been the reference implementation of DNS protocols for decades.

### AXFR/IXFR Configuration

BIND 9 supports both full (AXFR) and incremental (IXFR) zone transfers natively:

```named.conf
// Primary server configuration
options {
    directory "/var/named";
    allow-transfer {
        192.168.1.10;  // secondary server
        192.168.1.11;  // secondary server
    };
    notify yes;
    also-notify {
        192.168.1.10;
        192.168.1.11;
    };
};

zone "example.com" {
    type master;
    file "/var/named/zones/example.com.zone";
    allow-transfer {
        key "transfer-key";
    };
};

// TSIG key for secure zone transfers
key "transfer-key" {
    algorithm hmac-sha256;
    secret "base64-encoded-secret-here==";
};
```

### Docker Deployment

```yaml
version: "3.8"
services:
  bind9:
    image: ubuntu/bind9:latest
    container_name: bind9-primary
    ports:
      - "53:53/tcp"
      - "53:53/udp"
    volumes:
      - ./named.conf:/etc/bind/named.conf:ro
      - ./zones:/var/named/zones:ro
      - ./keys:/etc/bind/keys:ro
    environment:
      - BIND9_USER=bind
    restart: unless-stopped
```

### Secondary Server Setup

```named.conf
zone "example.com" {
    type slave;
    masters {
        192.168.1.1 key "transfer-key";
    };
    file "/var/named/slaves/example.com.zone";
    allow-notify { 192.168.1.1; };
};
```

### Strengths

- **Protocol compliance**: BIND is the reference implementation — if a DNS RFC exists, BIND supports it
- **Dynamic DNS updates**: Accepts RFC 2136 dynamic updates, useful for DHCP integration
- **Mature ecosystem**: Decades of hardening, extensive documentation, and community knowledge
- **View support**: Serve different zone data to different clients (split-horizon DNS)

### Weaknesses

- **Complex configuration**: Steep learning curve for new administrators
- **File-based zones**: Zone transfers can be slow for very large zones compared to database backends
- **Resource-heavy**: Higher memory footprint compared to NSD

## PowerDNS Authoritative: Database-Driven DNS

PowerDNS Authoritative Server is a high-performance DNS server with a unique architecture — it stores zone data in databases rather than flat files. This enables powerful features like multi-master replication and real-time zone updates.

### Native Multi-Master Zone Replication

Unlike BIND and NSD, PowerDNS supports true multi-master setups when using a shared database backend:

```yaml
# pdns.conf — Primary server
launch=gmysql
gmysql-host=db-primary.example.com
gmysql-dbname=pdns
gmysql-user=pdns
gmysql-password=securepassword
master=yes
slave=yes
slave-renotify=yes
also-notify=192.168.1.10:53
```

### IXFR and Zone Transfer Configuration

```yaml
# pdns.conf — Secondary server
launch=gmysql
gmysql-host=db-secondary.example.com
gmysql-dbname=pdns
gmysql-user=pdns
gmysql-password=securepassword
master=no
slave=yes
axfr-master-ip=192.168.1.1
```

### Docker Compose with MySQL Backend

```yaml
version: "3.8"
services:
  pdns-db:
    image: mysql:8
    container_name: pdns-db
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: pdns
      MYSQL_USER: pdns
      MYSQL_PASSWORD: securepassword
    volumes:
      - pdns-data:/var/lib/mysql
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    ports:
      - "3306:3306"
    restart: unless-stopped

  pdns:
    image: pschiffe/pdns-mysql:latest
    container_name: pdns-authoritative
    depends_on:
      - pdns-db
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "8081:8081"
    environment:
      - PDNS_master=yes
      - PDNS_slave=yes
      - PDNS_gmysql_host=pdns-db
      - PDNS_gmysql_dbname=pdns
      - PDNS_gmysql_user=pdns
      - PDNS_gmysql_password=securepassword
      - PDNS_api=yes
      - PDNS_api_key=api-secret-key
      - PDNS_webserver=yes
      - PDNS_webserver_address=0.0.0.0
    restart: unless-stopped

volumes:
  pdns-data:
```

### PowerDNS API for Zone Management

PowerDNS exposes a REST API for zone management, enabling automation:

```bash
# Create a new zone via API
curl -X POST http://localhost:8081/api/v1/servers/localhost/zones \
  -H "X-API-Key: api-secret-key" \
  -d '{
    "name": "example.com.",
    "kind": "Native",
    "nameservers": ["ns1.example.com.", "ns2.example.com."],
    "rrsets": [
      {
        "name": "example.com.",
        "type": "A",
        "ttl": 3600,
        "records": [{"content": "192.168.1.1", "disabled": false}]
      }
    ]
  }'
```

### Strengths

- **Database backend**: MySQL, PostgreSQL, SQLite — enables multi-master replication
- **REST API**: Programmatic zone management without reloading
- **Web interfaces**: PowerDNS-Admin, PowerDNS-AdminUI provide GUI management
- **Live reload**: Zone changes propagate without server restart
- **GeoIP routing**: Serve different records based on client location

### Weaknesses

- **Database dependency**: Requires a database server — additional infrastructure to maintain
- **Secondary-only mode**: Some features require database backend even for secondary servers
- **Learning curve**: Different mental model from traditional zone-file DNS

## NSD: Lightweight Secondary DNS

NSD (Name Server Daemon), developed by NLnet Labs, is a fast, lean authoritative DNS server optimized for secondary/slave deployments. It intentionally does not support primary/master mode — it only serves zones received via zone transfer.

### NSD Secondary Configuration

```nsd.conf
# nsd.conf — Secondary server
server:
    ip-address: 0.0.0.0
    ip-address: ::0
    port: 53
    hide-version: yes
    zonesdir: "/etc/nsd/zones"

# Zone definition — received via AXFR/IXFR from primary
zone:
    name: "example.com"
    zonefile: "example.com.zone"
    allow-axfr-fallback: yes
    request-xfr:
        192.168.1.1 TSIG_key_name

# TSIG key for secure transfers
key:
    name: "TSIG_key_name"
    algorithm: hmac-sha256
    secret: "base64-encoded-secret=="
```

### Docker Deployment

```yaml
version: "3.8"
services:
  nsd:
    image: dockurr/nsd:latest
    container_name: nsd-secondary
    ports:
      - "53:53/tcp"
      - "53:53/udp"
    volumes:
      - ./nsd.conf:/etc/nsd/nsd.conf:ro
      - ./zones:/etc/nsd/zones
      - ./keys:/etc/nsd/keys:ro
    environment:
      - NSD_USERNAME=nsd
    restart: unless-stopped
```

### Primary Server Zone Transfer Configuration (BIND as primary, NSD as secondary)

```named.conf
// On the BIND primary server
zone "example.com" {
    type master;
    file "/var/named/zones/example.com.zone";
    allow-transfer {
        key "nsd-transfer-key";
    };
    notify yes;
    also-notify { 192.168.1.20; };  // NSD secondary IP
};
```

### Strengths

- **Lightweight**: Minimal memory footprint, ideal for dedicated secondary servers
- **Fast**: Optimized query response times — one of the fastest authoritative servers
- **Secure by design**: No primary mode means reduced attack surface
- **Simple configuration**: Straightforward zone file-based setup
- **BSD license**: Permissive licensing for commercial deployments

### Weaknesses

- **Secondary only**: Cannot operate as a primary/master DNS server
- **No dynamic updates**: Does not support RFC 2136 dynamic DNS updates
- **File-based zones**: Zone data stored in files, no database backend option
- **No web UI**: Configuration is entirely file-based

## Zone Transfer Best Practices

### 1. Use TSIG Authentication

Always secure zone transfers with TSIG (Transaction SIGnature) keys to prevent unauthorized zone data access:

```bash
# Generate a TSIG key with BIND's dnssec-keygen
dnssec-keygen -a HMAC-SHA256 -b 256 -n HOST transfer-key
```

### 2. Configure AXFR and IXFR Appropriately

- **AXFR** transfers the entire zone — suitable for initial sync or small zones
- **IXFR** transfers only changed records — essential for large zones with frequent updates
- Set appropriate `serial` increment policies in zone files (use SOA serial format `YYYYMMDDNN`)

### 3. Monitor Zone Transfer Health

```bash
# Check zone transfer status with dig
dig @192.168.1.1 example.com AXFR

# Verify IXFR works
dig @192.168.1.1 example.com IXFR=2026043001

# Check SOA serial consistency across servers
dig @ns1.example.com example.com SOA +short
dig @ns2.example.com example.com SOA +short
```

### 4. Implement NOTIFY for Fast Propagation

Configure `notify yes` on primary servers to immediately alert secondaries of zone changes, rather than waiting for the SOA refresh interval.

## When to Choose Each Server

| Scenario | Recommended Server |
|---|---|
| Traditional primary/secondary with zone files | BIND 9 |
| Multi-master with database backend | PowerDNS Authoritative |
| Dedicated lightweight secondary server | NSD |
| Dynamic DNS updates needed | BIND 9 or PowerDNS |
| REST API for automation | PowerDNS |
| Minimal resource footprint | NSD |
| Split-horizon / views | BIND 9 |
| Web UI management | PowerDNS |

For most organizations, a **hybrid approach** works best: BIND 9 or PowerDNS as the primary master, with NSD secondaries handling query load at edge locations.

## FAQ

### What is the difference between AXFR and IXFR?

AXFR (full zone transfer) sends the entire zone file from the primary to secondary server. IXFR (incremental zone transfer) only sends the records that have changed since the last transfer. IXFR is significantly faster for large zones with infrequent updates, while AXFR is used for initial synchronization or when IXFR is not supported.

### Can NSD be used as a primary DNS server?

No. NSD is intentionally designed as a secondary-only authoritative server. It cannot create or serve zones from its own zone files — it only serves zones received via AXFR/IXFR from a primary server. If you need a primary server, use BIND 9 or PowerDNS Authoritative instead.

### How do I secure zone transfers between DNS servers?

Use TSIG (Transaction SIGnature) keys to authenticate zone transfer requests. Both BIND 9 and PowerDNS support TSIG with HMAC-SHA256. Generate a shared secret key on the primary, configure it in both primary and secondary server configs, and restrict `allow-transfer` to only the IP addresses of your secondary servers.

### Does PowerDNS support multi-master DNS setups?

Yes. When using a shared database backend (MySQL, PostgreSQL), multiple PowerDNS Authoritative instances can write to the same database simultaneously. This provides true multi-master replication where any server can update zone data and changes are immediately visible to all instances — no zone transfers needed.

### How often do DNS zone transfers occur?

Zone transfers are triggered by two mechanisms: (1) **NOTIFY** messages from the primary when a zone changes (immediate), and (2) **SOA refresh** intervals when secondaries check if the serial has increased (periodic, typically every 1-24 hours). For fast propagation, configure `notify yes` on the primary and keep SOA refresh intervals short.

### Which DNS server is fastest for query responses?

NSD is generally the fastest for authoritative query responses due to its minimal design and optimized data structures. PowerDNS is also very fast, especially with in-memory database caching. BIND 9 is slightly slower but offers the most features and protocol compliance.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "BIND 9 vs PowerDNS vs NSD: Self-Hosted Authoritative DNS Zone Transfer Guide 2026",
  "description": "Compare BIND 9, PowerDNS, and NSD for self-hosted authoritative DNS with zone transfers (AXFR/IXFR), multi-master setups, and high availability configurations.",
  "datePublished": "2026-04-30",
  "dateModified": "2026-04-30",
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
