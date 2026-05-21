---
title: "Self-Hosted DNS Catalog Zones: RFC 8645 with BIND vs PowerDNS vs Knot DNS (2026)"
date: "2026-05-21"
description: "Automate DNS zone provisioning across multiple servers using DNS Catalog Zones (RFC 8645) — compare BIND, PowerDNS, and Knot DNS implementations."
tags: ["dns", "catalog-zones", "rfc8645", "bind", "powerdns", "knot-dns", "automation", "self-hosted"]
draft: false
---

DNS Catalog Zones, defined in [RFC 8645](https://datatracker.ietf.org/doc/html/rfc8645), provide a standardized mechanism for automating DNS zone provisioning across multiple authoritative name servers. Instead of manually configuring zone transfers on each server or relying on proprietary APIs, catalog zones let you maintain a single "catalog" zone that tells each secondary server which zones to provision and from which primary source.

This is particularly valuable for organizations running multiple DNS servers across different locations, hosting providers managing DNS for hundreds of clients, and self-hosted environments where zone configurations need to stay synchronized across a DNS cluster.

## What Are DNS Catalog Zones?

A catalog zone is a special DNS zone that contains PTR records mapping zone names to their primary server identifiers. Secondary servers consume the catalog zone and automatically:

1. **Discover** which zones they should serve by reading the catalog
2. **Provision** new zones automatically when entries appear in the catalog
3. **Decommission** zones when entries are removed
4. **Synchronize** zone configuration changes across all secondaries

The catalog zone format uses PTR records in a specific namespace:

```
zone-name.zones.catalog.example.com. IN PTR primary-id.primaries.catalog.example.com.
```

Where:
- `zone-name` is the zone to provision (e.g., `example.com`)
- `primary-id` identifies the primary server (e.g., `ns1`)
- `catalog.example.com` is the catalog zone name

### Architecture Overview

```
                    ┌─────────────────────┐
                    │   Catalog Zone      │
                    │   (catalog.dns)     │
                    └─────────┬───────────┘
                              │ AXFR/IXFR
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │Primary NS│   │Secondary │   │Secondary │
        │  (BIND)  │   │ NS (pdns)│   │ NS(knot) │
        └──────────┘   └──────────┘   └──────────┘
              │              │              │
              └──────────────┼──────────────┘
                             │ Zone transfers
                             ▼
```

## BIND: Reference Implementation

BIND (Berkeley Internet Name Domain) includes native catalog zone support as the reference implementation of RFC 8645.

### Configuration

**Primary server (`named.conf`):**
```bind
options {
    directory "/var/named";
    allow-transfer { 192.168.1.0/24; };
    notify yes;
};

// The catalog zone itself
zone "catalog.dns" IN {
    type master;
    file "zones/catalog.dns.zone";
    allow-transfer { 192.168.1.0/24; };
    notify yes;
};

// A regular zone that will be cataloged
zone "example.com" IN {
    type master;
    file "zones/example.com.zone";
};
```

**Catalog zone file (`catalog.dns.zone`):**
```bind
$TTL 300
@       IN SOA  ns1.example.com. admin.example.com. (
                    2026052101  ; serial
                    3600        ; refresh
                    900         ; retry
                    604800      ; expire
                    300 )       ; minimum
        IN NS   ns1.example.com.

; Catalog entries: zone-name.zones.catalog.dns IN PTR primary-id.primaries.catalog.dns
example.com.zones.catalog.dns. 300 IN PTR ns1.primaries.catalog.dns.
internal.example.net.zones.catalog.dns. 300 IN PTR ns1.primaries.catalog.dns.
```

**Secondary server consuming the catalog:**
```bind
options {
    catalog-zones {
        zone "catalog.dns"
            default-masters { 192.168.1.10; }
            allow-transfer { 192.168.1.10; };
    };
};
```

### Docker Compose

```yaml
version: "3.8"
services:
  bind-primary:
    image: ubuntu/bind9:latest
    container_name: bind-primary
    restart: unless-stopped
    ports:
      - "53:53/tcp"
      - "53:53/udp"
    volumes:
      - ./named.conf:/etc/bind/named.conf:ro
      - ./zones:/var/named/zones
    networks:
      - dns-net

networks:
  dns-net:
    driver: bridge
```

## PowerDNS: Authoritative Server with Catalog Support

PowerDNS Authoritative Server supports catalog zones as a consumer, automatically provisioning zones based on catalog entries received from a primary server.

### Configuration

**Primary (BIND or any RFC 8645-compliant server) sends catalog zone via AXFR/IXFR.**

**PowerDNS secondary (`pdns.conf`):**
```ini
# Enable catalog zones
catalog=yes
catalog-retrieval-interval=30

# Backend configuration (using BIND backend for simplicity)
launch=bind
bind-config=/etc/powerdns/named.conf
bind-check-interval=300

# Or using the generic-mysql backend
launch=gmysql
gmysql-host=127.0.0.1
gmysql-port=3306
gmysql-dbname=pdns
gmysql-user=pdns
gmysql-password=secret
```

**Database backend approach (recommended for production):**
```sql
-- PowerDNS automatically creates catalog zone entries in the database
-- The pdns-backend-catalog plugin handles zone provisioning

-- View catalog zones
SELECT * FROM domains WHERE type = 'SLAVE' AND catalog = 'catalog.dns';

-- View catalog members
SELECT * FROM domainmetadata WHERE domain_id IN (
    SELECT id FROM domains WHERE catalog = 'catalog.dns'
);
```

### Docker Compose with MySQL Backend

```yaml
version: "3.8"
services:
  pdns-secondary:
    image: pschiffe/pdns-mysql:latest
    container_name: pdns-secondary
    restart: unless-stopped
    ports:
      - "53:53/tcp"
      - "53:53/udp"
    environment:
      - PDNS_gmysql_host=pdns-db
      - PDNS_gmysql_port=3306
      - PDNS_gmysql_dbname=pdns
      - PDNS_gmysql_user=pdns
      - PDNS_gmysql_password=secret
      - PDNS_master=yes
      - PDNS_credential=secret
      - PDNS_allow_axfr_ips=192.168.1.0/24
      - PDNS_catalo_g=yes
      - PDNS_catalo_g-retrieval-interval=30
    depends_on:
      - pdns-db
    networks:
      - dns-net

  pdns-db:
    image: mysql:8
    container_name: pdns-db
    restart: unless-stopped
    environment:
      - MYSQL_ROOT_PASSWORD=rootpass
      - MYSQL_DATABASE=pdns
      - MYSQL_USER=pdns
      - MYSQL_PASSWORD=secret
    volumes:
      - pdns-data:/var/lib/mysql
    networks:
      - dns-net

volumes:
  pdns-data:

networks:
  dns-net:
    driver: bridge
```

## Knot DNS: Native Catalog Zone Consumer

Knot DNS provides native catalog zone support with a clean configuration syntax.

### Configuration

**Knot DNS secondary (`knot.conf`):**
```yaml
server:
  rundir: "/run/knot"
  user: knot:knot

log:
  - target: syslog
    any: info

remotes:
  - id: primary-ns
    address: 192.168.1.10

# Catalog zone consumption
catalog:
  - id: production-catalog
    zone: "catalog.dns"
    remote: primary-ns
    acl:
      - id: allow-primary
        address: 192.168.1.10/32
        action: transfer

zone:
  - domain: catalog.dns
    storage: "/var/lib/knot/zones"
    file: "catalog.dns.zone"
```

### Docker Compose

```yaml
version: "3.8"
services:
  knot-secondary:
    image: cznic/knot:latest
    container_name: knot-secondary
    restart: unless-stopped
    ports:
      - "53:53/tcp"
      - "53:53/udp"
    volumes:
      - ./knot.conf:/etc/knot/knot.conf:ro
      - knot-data:/var/lib/knot
    networks:
      - dns-net

volumes:
  knot-data:

networks:
  dns-net:
    driver: bridge
```

### Managing Catalog Entries

Add a new zone to the catalog on the primary server:

```bash
# Using knotc (if primary is Knot DNS)
knotc zone-begin catalog.dns
knotc zone-set catalog.dns example.com.zones.catalog.dns. 300 PTR ns1.primaries.catalog.dns.
knotc zone-commit catalog.dns
```

## Comparison Table

| Feature | BIND | PowerDNS | Knot DNS |
|---------|------|----------|----------|
| **Catalog Role** | Producer + Consumer | Consumer | Consumer |
| **RFC 8645 Support** | Reference implementation | Supported | Supported |
| **Backend Options** | File-based | MySQL, PostgreSQL, SQLite, BIND | File-based |
| **Automatic Provisioning** | Yes | Yes | Yes |
| **Zone Removal** | Automatic | Automatic | Automatic |
| **Docker Image** | ubuntu/bind9 | pschiffe/pdns-mysql | cznic/knot |
| **Config Complexity** | Moderate | Low-Moderate | Low |
| **Monitoring** | `rndc catalog-list` | Database queries | `knotc zone-list` |
| **Best For** | Reference deployment | Large-scale with DB backend | Simple file-based setup |

## Why Use DNS Catalog Zones?

**Automated Zone Provisioning**: Instead of manually editing zone configurations on each secondary server, adding a zone to the catalog automatically provisions it everywhere. This is essential when managing dozens or hundreds of zones across a DNS cluster.

**Consistent Configuration**: All secondary servers receive the same zone list from a single authoritative source. This eliminates configuration drift where one server might be missing a zone or serving a different version.

**Simplified Operations**: Adding a new zone becomes a single operation — add the PTR record to the catalog zone — rather than editing configuration files on multiple servers and reloading each one.

**Dynamic DNS Environments**: For hosting providers or organizations where zones are frequently created and decommissioned, catalog zones provide the automation needed to keep DNS infrastructure in sync without manual intervention.

## Operational Best Practices

**Serial Management**: Use date-based serial numbers (`YYYYMMDDNN`) for the catalog zone to ensure proper IXFR (incremental zone transfer) behavior. Every catalog change should increment the serial.

**ACL Security**: Restrict catalog zone transfers to known secondary servers using ACLs. A compromised secondary should not be able to inject catalog entries.

**Monitoring**: Set up alerts for catalog zone transfer failures. If a secondary cannot retrieve the catalog, it will not provision new zones or decommission removed ones.

**Fallback**: Ensure each secondary can serve zones even if the catalog zone becomes temporarily unavailable. Zones already provisioned should continue serving from their local copies.

For related reading, see our [DNSSEC validation guide](../2026-05-14-self-hosted-dnssec-validation-unbound-knot-resolver-powerdns-guide/) and [DNS rate limiting comparison](../2026-05-12-self-hosted-dns-rate-limiting-dnsdist-bind-rrl-unbound-guide/).

## FAQ

### What is a DNS Catalog Zone?

A DNS Catalog Zone is a special DNS zone defined in RFC 8645 that contains PTR records mapping zone names to their primary servers. Secondary DNS servers consume the catalog zone and automatically provision, update, or decommission zones based on its contents.

### How do Catalog Zones differ from standard zone transfers?

Standard zone transfers (AXFR/IXFR) transfer the contents of a single zone from primary to secondary. Catalog zones automate the discovery and provisioning of zones themselves — the catalog tells secondaries which zones to transfer, eliminating manual configuration on each server.

### Can I mix BIND, PowerDNS, and Knot DNS in a catalog zone setup?

Yes. RFC 8645 is a standard protocol, so any compliant implementation can participate. A BIND primary can serve the catalog zone to PowerDNS and Knot DNS secondaries simultaneously. The catalog zone format is the same regardless of the DNS server software.

### How often do secondaries check for catalog updates?

Secondaries check for catalog updates based on the catalog zone's SOA refresh interval (typically 300-3600 seconds). When the primary increments the catalog zone serial, it sends a NOTIFY to secondaries, triggering an immediate IXFR.

### What happens if a secondary loses connectivity to the primary?

The secondary continues serving zones it has already provisioned. It will not provision new zones or decommission removed ones until connectivity is restored and it can retrieve the updated catalog zone.

### Can catalog zones add custom zone configuration per secondary?

The base RFC 8645 specification only communicates the zone name and primary server identity. Custom per-secondary configuration (such as different ACLs or storage paths) must be handled through local configuration or vendor-specific extensions.

### Is there a performance impact from using catalog zones?

The performance impact is minimal. Catalog zone transfers are small (containing only PTR records, not full zone data), and zone provisioning happens asynchronously. The primary benefit is operational simplicity, not performance improvement.

### How do I remove a zone using catalog zones?

Remove the corresponding PTR record from the catalog zone and increment the serial. Secondary servers will detect the removal on their next catalog refresh and automatically decommission the zone.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DNS Catalog Zones: RFC 8645 with BIND vs PowerDNS vs Knot DNS (2026)",
  "description": "Automate DNS zone provisioning across multiple servers using DNS Catalog Zones (RFC 8645) — compare BIND, PowerDNS, and Knot DNS implementations.",
  "datePublished": "2026-05-21",
  "dateModified": "2026-05-21",
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
