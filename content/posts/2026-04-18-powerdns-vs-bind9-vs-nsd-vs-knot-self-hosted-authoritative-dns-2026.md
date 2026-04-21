---
title: "PowerDNS vs BIND9 vs NSD vs Knot DNS: Best Self-Hosted Authoritative DNS Server 2026"
date: 2026-04-18
tags: ["comparison", "guide", "self-hosted", "dns", "infrastructure", "networking"]
draft: false
description: "Compare the top open-source authoritative DNS servers — PowerDNS, BIND9, NSD, and Knot DNS. Includes Docker deployment, zone file configs, and performance benchmarks for 2026."
---

When you own a domain, someone has to answer the question: "What IP does this domain point to?" That someone is an **authoritative DNS server**. Unlike recursive resolvers (which look up answers on your behalf), authoritative servers hold the actual zone files and provide the definitive answers to DNS queries for your domains.

In this guide, we compare four of the most widely used open-source authoritative DNS servers: **PowerDNS**, **BIND9**, **NSD**, and **Knot DNS**. Each has different strengths — from PowerDNS's database backends and REST API, to BIND9's ubiquity and DNSSEC maturity, to NSD's simplicity, to Knot DNS's raw performance.

For a broader look at the DNS ecosystem (recursive resolvers, DNS-over-TLS, and DNS filtering), check out our [DNS resolvers comparison](../self-hosted-dns-resolvers-unbound-dnsmasq-bind-coredns-guide-2026/) and [DNS filtering guide](../self-hosted-dns-filtering-content-blocking-pihole-adguard-technitium-guide-2026/). If you need a web UI to manage DNS records, see our [DNS management web UI comparison](../self-hosted-dns-management-web-uis-powerdns-admin-technitium-bind-webmin-guide-2026/).

## Why Self-Host an Authoritative DNS Server

Most domain owners rely on their registrar's default DNS or a managed service like Cloudflare. But self-hosting an authoritative DNS server gives you:

- **Full control** over zone files, TTLs, and record types without third-party limits
- **No vendor lock-in** — your DNS data stays on your infrastructure
- **Cost savings** — no monthly fees for premium DNS features
- **DNSSEC from scratch** — sign your own zones with your own keys
- **Secondary/failover DNS** — run your own secondary nameservers for redundancy
- **Custom record types** — support TXT, SRV, CAA, SSHFP, and any other RR type you need
- **Privacy** — no telemetry or query logging sent to third parties

Whether you're managing DNS for a small homelab, a startup's staging environment, or a production domain with millions of records, there's an open-source authoritative DNS server that fits.

## PowerDNS Authoritative Server

**GitHub:** [PowerDNS/pdns](https://github.com/PowerDNS/pdns) | **Stars:** 4,345 | **Last Updated:** April 2026 | **Language:** C++

PowerDNS is the most feature-rich authoritative DNS server on this list. It supports multiple backend storage engines (SQLite, MySQL, [postgresql](https://www.postgresql.org/), PostgreSQL with DNSSEC, generic ODBC, BIND zone files, and Lua scripts), a built-in REST API, and dynamic updates. The PowerDNS ecosystem also includes a separate **Recursor** product and **dnsdist** for DNS load balancing.

### Key Features

- Multiple database backends (MySQL, PostgreSQL, SQLite, LMDB, BIND zone files)
- Built-in REST API for programmatic zone management
- Dynamic DNS updates (RFC 2136)
- Native and master/slave DNSSEC support
- Lua scripting for custom query handling
- PowerDNS Admin web UI (third-party, open-source)
- AXFR/IXFR zone transfers
- GeoDNS support via the GeoIP backend

### [docker](https://www.docker.com/) Compose Setup

PowerDNS provides an official `docker-compose.yml` in their repository. Here's a simplified deployment:

```yaml
services:
  pdns-auth:
    image: pdns/pdns-auth-master:latest
    container_name: pdns-auth
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "8081:8081"
    environment:
      - PDNS_auth_api_key=your-secure-api-key
    volumes:
      - ./pdns.conf:/etc/pdns/pdns.conf:ro
    restart: unless-stopped
```

### Minimal Configuration (`pdns.conf`)

```ini
# PowerDNS Authoritative minimal config
local-address=0.0.0.0
local-port=53
api=yes
api-key=your-secure-api-key
webserver=yes
webserver-address=0.0.0.0
webserver-port=8081

# Use SQLite backend (no external DB needed)
launch=gsqlite3
gsqlite3-database=/var/lib/powerdns/pdns.sqlite3
gsqlite3-dnssec=on

# DNSSEC
dnssec=on
default-soa-content=ns1.example.com. admin.example.com. 0 10800 3600 604800 3600
```

PowerDNS also supports a full Docker Compose stack with the Recursor and dnsdist components from the official `docker-compose.yml` — mapping the authoritative server on port 1053, the recursor on port 2053, and dnsdist o[gitlab](https://about.gitlab.com/) 3053.

## BIND9 (Berkeley Internet Name Domain)

**GitLab:** [isc-projects/bind9](https://gitlab.isc.org/isc-projects/bind9) | **GitHub Mirror:** 737 stars | **Language:** C

BIND9 is the oldest and most widely deployed DNS server. It's the reference implementation of the DNS protocol and has been the backbone of the internet's DNS infrastructure since the 1980s. ISC maintains BIND9 on GitLab (the GitHub mirror is archived). It ships with virtually every Linux distribution and is the default authoritative server for many enterprise environments.

### Key Features

- Full DNS protocol implementation (the reference standard)
- Mature DNSSEC with automatic key management (KASP)
- View-based split DNS (different answers for different clients)
- Response Rate Limiting (RRL) for DDoS mitigation
- DLZ (Dynamically Loadable Zones) for database backends
- Catalog zones for automatic secondary zone provisioning
- DNS64/NAT64 support
- Built-in caching (can act as both authoritative and recursive)

### Docker Compose Setup

ISC provides an official Docker image on Docker Hub:

```yaml
services:
  bind9:
    image: isc/bind:latest
    container_name: bind9
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "953:953"
    volumes:
      - ./named.conf:/etc/bind/named.conf:ro
      - ./zones/:/etc/bind/zones/:ro
      - ./keys/:/etc/bind/keys/:rw
    restart: unless-stopped
```

### Minimal Configuration (`named.conf`)

```bind
options {
    directory "/etc/bind";
    listen-on port 53 { any; };
    listen-on-v6 port 53 { any; };
    allow-query { any; };
    recursion no;  # Authoritative only
    dnssec-validation auto;
};

zone "example.com" {
    type master;
    file "/etc/bind/zones/db.example.com";
    allow-transfer { 192.0.2.10; };  # Secondary NS
    notify yes;
};

// RNDC control channel
rndc-key {
    algorithm hmac-sha256;
    secret "your-rndc-key-here";
};
```

### Sample Zone File (`db.example.com`)

```bind
$TTL 86400
@   IN  SOA ns1.example.com. admin.example.com. (
            2026041801  ; Serial (YYYYMMDDNN)
            3600        ; Refresh
            1800        ; Retry
            604800      ; Expire
            86400       ; Minimum TTL
)

@       IN  NS      ns1.example.com.
@       IN  NS      ns2.example.com.
ns1     IN  A       192.0.2.1
ns2     IN  A       192.0.2.2
@       IN  A       192.0.2.10
www     IN  A       192.0.2.10
mail    IN  A       192.0.2.20
@       IN  MX  10  mail.example.com.
@       IN  TXT     "v=spf1 mx -all"
```

## NSD (Name Server Daemon)

**GitHub:** [NLnetLabs/nsd](https://github.com/NLnetLabs/nsd) | **Stars:** 544 | **Last Updated:** April 2026 | **Language:** C

NSD is built by NLnet Labs with one goal: be the fastest, most secure authoritative-only DNS server. It has no recursive functionality, no caching, and no bells and whistles — just rock-solid zone serving with minimal resource usage. NSD is used by many TLD operators (including `.nl` and `.se`) and root server instances.

### Key Features

- Authoritative-only design (smaller attack surface)
- Zone file compilation for fast startup and query response
- AXFR/IXFR zone transfers
- DNSSEC with NSEC and NSEC3 support
- Multiple IP address binding with per-server socket partitioning
- XDP (eXpress Data Path) support for kernel-level packet processing
- Catalog zones for automated secondary provisioning
- Low memory footprint — runs well on small VPS instances

### Docker Compose Setup

NLnetLabs provides an official Docker image:

```yaml
services:
  nsd:
    image: nlnetlabs/nsd:latest
    container_name: nsd
    ports:
      - "53:53/tcp"
      - "53:53/udp"
    volumes:
      - ./nsd.conf:/etc/nsd/nsd.conf:ro
      - ./zones/:/etc/nsd/zones/:ro
    restart: unless-stopped
```

### Minimal Configuration (`nsd.conf`)

```yaml
server:
    ip-address: 0.0.0.0
    ip-address: ::0
    port: 53
    # server-count: 4  # Use one worker per CPU core

zone:
    name: "example.com"
    zonefile: "/etc/nsd/zones/db.example.com"
    # Provide AXFR to secondary
    provide-xfr: 192.0.2.10/32

zone:
    name: "reverse.example.com"
    zonefile: "/etc/nsd/zones/db.reverse.example.com"
```

NSD's configuration is refreshingly simple. The YAML-like format is easy to read and validate with `nsd-checkconf`. Zone files use the standard BIND-compatible format, so migrating from BIND is straightforward.

## Knot DNS

**GitLab:** [knot/knot-dns](https://gitlab.labs.nic.cz/knot/knot) | **Language:** C

Knot DNS is developed by CZ.NIC (the `.cz` registry operator) and is designed for maximum performance at scale. It powers the `.cz` TLD and is used by several other national registries. Knot DNS features an incremental zone loading engine, online DNSSEC signing, and a powerful control interface via `knotc`.

### Key Features

- Incremental zone loading (no full reload on changes)
- Online DNSSEC signing (keys managed automatically)
- High-performance C implementation
- `knotc` control utility for live configuration changes
- DNSSEC with automatic KASP (Key And Signature Policy)
- AXFR/IXFR with parallel zone transfers
- Catalog zones for automated secondary setup
- XDP-based packet processing for DDoS resilience
- Module system for custom DNS processing

### Docker Compose Setup

The official Docker image is maintained by CZ.NIC:

```yaml
services:
  knot:
    image: cznic/knot:latest
    container_name: knot-dns
    ports:
      - "53:53/tcp"
      - "53:53/udp"
    volumes:
      - ./knot.conf:/etc/knot/knot.conf:ro
      - ./zones/:/var/lib/knot/zones/
      - ./keys/:/var/lib/knot/dnssec/keys/
    restart: unless-stopped
```

### Minimal Configuration (`knot.conf`)

```conf
# Knot DNS configuration
server:
    listen: 0.0.0.0@53
    listen: ::@53
    user: knot:knot
    rundir: "/run/knot"
    dbdir: "/var/lib/knot"

template:
    id: default
    storage: "/var/lib/knot"
    file: "zones/%s.zone"
    dnssec-signing: on
    dnssec-policy: default

zone:
    domain: example.com
    template: default
```

Knot DNS's configuration uses a flat key-value format. The `knotc` command lets you inspect server status, reload zones, and manage DNSSEC keys without restarting the daemon:

```bash
# Check server status
docker exec knot-dns knotc status

# Reload a specific zone
docker exec knot-dns knotc zone-reload example.com

# List DNSSEC keys
docker exec knot-dns knotc key-list example.com
```

## Comparison Table

| Feature | PowerDNS Auth | BIND9 | NSD | Knot DNS |
|---------|--------------|-------|-----|----------|
| **Type** | Authoritative | Auth + Recursive | Authoritative-only | Authoritative-only |
| **Language** | C++ | C | C | C |
| **GitHub Stars** | 4,345 | 737 (mirror) | 544 | N/A (GitLab) |
| **Last Updated** | April 2026 | August 2025 | April 2026 | Active |
| **Database Backend** | MySQL, PG, SQLite, LMDB | DLZ (limited) | None | None |
| **REST API** | Yes (built-in) | No | No | No (control CLI) |
| **DNSSEC** | Yes | Yes (mature) | Yes | Yes (online signing) |
| **Zone Transfers** | AXFR/IXFR | AXFR/IXFR | AXFR/IXFR | AXFR/IXFR (parallel) |
| **Config Format** | INI-style | BIND named.conf | YAML-like | Flat key-value |
| **XDP/eBPF** | No | No | Yes | Yes |
| **Dynamic Updates** | Yes (RFC 2136) | Yes | No | Yes |
| **Lua Scripting** | Yes | No | No | Yes (policy scripts) |
| **Docker Image** | Official | Official | Official | Official |
| **Memory Footprint** | Medium | Medium-High | Low | Low-Medium |
| **Best For** | API-driven, DB-backed DNS | Enterprise, reference DNS | Minimalist, high-security | High-performance, TLD-scale |

## Performance Considerations

All four servers handle millions of queries per second on properly sized hardware, but their performance characteristics differ:

- **NSD** consistently benchmarks as the fastest for pure authoritative serving due to its single-purpose design and compiled zone database. The zone compilation step converts human-readable zone files into an optimized binary format at startup.

- **Knot DNS** excels at handling large zone files and frequent updates. Its incremental loading engine means changes propagate without full zone reloads, making it ideal for dynamic environments.

- **PowerDNS** trades some raw speed for feature richness. When using a database backend, query latency depends on DB performance. The LMDB backend offers the best speed for file-based operation.

- **BIND9** is the most versatile but also the heaviest. Running it as authoritative-only (with `recursion no;`) improves performance. Its response rate limiting is among the best for mitigating DNS amplification attacks.

For homelab or small-scale deployments, all four run comfortably on a $5/month VPS with 1 GB RAM. The choice should be driven by features, not raw throughput, unless you're operating at TLD scale.

## Which Authoritative DNS Server Should You Choose?

**Choose PowerDNS if:**
- You need a REST API for programmatic DNS management
- You want to store zone records in a relational database (MySQL, PostgreSQL)
- You need dynamic DNS updates for DHCP integration
- You plan to use PowerDNS Admin or a similar web UI
- You want Lua scripting for custom query responses

**Choose BIND9 if:**
- You need the reference DNS implementation with maximum compatibility
- You want split DNS views (different answers per client subnet)
- You need DNS64/NAT64 for IPv6-only networks
- Your team already knows BIND configuration
- You need both authoritative and recursive in one binary

**Choose NSD if:**
- You want the smallest attack surface (authoritative-only)
- You need maximum query throughput with minimal resources
- You run at TLD scale or want TLD-grade reliability
- You prefer simple, auditable configuration
- You want XDP/eBPF support for kernel-level packet filtering

**Choose Knot DNS if:**
- You manage large zones that change frequently
- You need online DNSSEC signing with automatic key rotation
- You want the fastest incremental zone updates
- You operate at registry scale
- You need parallel zone transfers for fast secondary sync

For related reading, see our [DNS-over-TLS resolver guide](../self-hosted-dns-over-tls-resolver-stubby-unbound-knot-2026/) for securing recursive lookups, and our [DDNS comparison](../ddclient-vs-ddns-updater-vs-inadyn-self-hosted-ddns-guide-2026/) for keeping dynamic IPs updated.

## FAQ

### What is the difference between an authoritative DNS server and a recursive resolver?

An authoritative DNS server holds the actual zone files for your domains and provides definitive answers to DNS queries. A recursive resolver (like Unbound or the PowerDNS Recursor) looks up answers on behalf of clients by querying authoritative servers. Most deployments use both: a recursive resolver for local clients and an authoritative server to serve your domains to the world.

### Can I run multiple authoritative DNS servers for the same domain?

Yes. It's a best practice to run at least two authoritative nameservers (typically called ns1 and ns2) on separate machines or networks. You configure one as the primary (master) and the other as a secondary (slave), with AXFR/IXFR zone transfers keeping them in sync. All four servers covered in this guide support master/slave configurations.

### Do I need DNSSEC for my authoritative DNS server?

DNSSEC is not strictly required, but it's strongly recommended for any production domain. It prevents DNS spoofing and cache poisoning attacks by cryptographically signing your zone records. All four servers support DNSSEC, but Knot DNS and BIND9 offer the most automated key management (KASP), while PowerDNS and NSD require more manual key setup.

### Can I migrate my zone files from BIND to NSD or PowerDNS?

Yes. NSD and PowerDNS both use the standard BIND zone file format. You can copy your `named.conf` zone declarations and zone files directly. NSD's YAML configuration is different from BIND's, but the zone data format is 100% compatible. PowerDNS can read BIND zone files directly via its `bind` backend or import them into its database.

### How do I choose between database-backed and file-based DNS?

Database-backed DNS (PowerDNS with MySQL/PostgreSQL) is better when you need programmatic zone management, multi-server write access, or integration with existing applications. File-based DNS (BIND, NSD, Knot DNS) is simpler to manage, easier to version control with Git, and typically faster for read-heavy workloads. For most self-hosted setups, file-based DNS is the simpler choice.

### What port does an authoritative DNS server use?

Authoritative DNS servers listen on **port 53** for both TCP and UDP. TCP is used for zone transfers (AXFR/IXFR) and responses larger than 512 bytes (or when EDNS0 is in use). UDP is used for standard queries. Make sure your firewall allows inbound traffic on both protocols. Some servers also expose additional ports for APIs (PowerDNS: 8081) or control channels (BIND RNDC: 953).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "PowerDNS vs BIND9 vs NSD vs Knot DNS: Best Self-Hosted Authoritative DNS Server 2026",
  "description": "Compare the top open-source authoritative DNS servers — PowerDNS, BIND9, NSD, and Knot DNS. Includes Docker deployment, zone file configs, and performance benchmarks for 2026.",
  "datePublished": "2026-04-18",
  "dateModified": "2026-04-18",
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
