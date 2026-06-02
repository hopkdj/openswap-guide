---
title: "Self-Hosted DNS Split-View Traffic Management: BIND Views vs PowerDNS LUA Records vs Knot DNS Response Policy"
date: "2026-06-03"
tags: ["dns", "bind", "powerdns", "knot-dns", "networking", "dns-management", "traffic-routing"]
draft: false
---

## Introduction

DNS split-view (also known as split-horizon DNS or DNS views) is a technique where a single DNS server returns different answers depending on the client's source IP address or network location. This is essential for organizations that need to serve internal IP addresses to internal clients while presenting public-facing addresses to external queries. Whether you are running a corporate intranet with private service endpoints, managing multi-tenant DNS hosting, or implementing geo-aware DNS routing, split-view DNS gives you fine-grained control over DNS responses.

In this guide, we compare three powerful open-source DNS servers and their approaches to implementing split-view DNS: **BIND 9** with its built-in views feature, **PowerDNS** with LUA script records and GeoIP backend, and **Knot DNS** with response policy and query-level filtering. Each solution offers a different trade-off between simplicity, flexibility, and performance.

## BIND 9 Views

BIND 9 (Berkeley Internet Name Domain) is the oldest and most widely deployed DNS server. Its **views** feature allows you to define multiple virtual DNS configurations within a single server instance, each matching on client source addresses via ACLs.

### Key Features
- **Multiple virtual servers** within a single BIND process
- **ACL-based matching** using `match-clients`, `match-destinations`
- **Per-view zone files** — complete zone isolation between views
- **`allow-recursion`** control per view
- **`allow-query`, `allow-transfer`** access controls

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  bind:
    image: internetsystemsconsortium/bind9:9.20
    container_name: bind-splitview
    ports:
      - "53:53/tcp"
      - "53:53/udp"
    volumes:
      - ./bind/config:/etc/bind
      - ./bind/internal:/var/lib/bind/internal
      - ./bind/external:/var/lib/bind/external
      - ./bind/cache:/var/cache/bind
    environment:
      - BIND9_USER=root
    restart: unless-stopped
```

### BIND Views Configuration Example

```
acl internal-net { 192.168.0.0/16; 10.0.0.0/8; };

view "internal" {
    match-clients { internal-net; };
    recursion yes;
    allow-query { internal-net; };

    zone "example.com" {
        type master;
        file "/var/lib/bind/internal/example.com.db";
    };
};

view "external" {
    match-clients { any; };
    recursion no;
    allow-query { any; };

    zone "example.com" {
        type master;
        file "/var/lib/bind/external/example.com.db";
    };
};
```

In this setup, internal clients in the `192.168.0.0/16` and `10.0.0.0/8` ranges receive the internal zone file, while all other clients receive the external zone file. BIND evaluates views in order — the first matching view wins, making ACL ordering critical.

### Pros and Cons

- ✅ Mature, battle-tested — used by most root DNS servers
- ✅ Complete zone isolation between views
- ✅ Fine-grained ACLs and per-view access controls
- ❌ Configuration duplication — each view needs complete zone files
- ❌ Memory overhead proportional to number of views
- ❌ Views are evaluated sequentially — large ACLs can slow query processing

## PowerDNS LUA Records & GeoIP Backend

PowerDNS takes a fundamentally different approach to split-view DNS. Instead of maintaining separate virtual servers with separate zone files, PowerDNS uses **backend plugins** and **LUA script records** to dynamically compute responses based on the query source.

### Key Features
- **LUA records** — execute scripts to determine responses dynamically
- **GeoIP backend** — return different records based on geographic location
- **Pipe backend** — pipe queries to external programs for custom logic
- **Per-record `scopeMask`** — mark records as internal or external
- **DNSSEC-aware** — dynamic responses with valid signatures

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  powerdns:
    image: powerdns/pdns-auth-49:4.9
    container_name: pdns-splitview
    ports:
      - "53:53/tcp"
      - "53:53/udp"
    volumes:
      - ./pdns/data:/var/lib/powerdns
      - ./pdns/lua:/etc/powerdns/lua.d
    environment:
      - PDNS_gmysql_host=mysql
      - PDNS_gmysql_user=pdns
      - PDNS_gmysql_password=changeme
      - PDNS_gmysql_dbname=pdns
      - PDNS_enable_lua_records=yes
      - PDNS_lua_records_hook=/etc/powerdns/lua.d/splitview.lua
    restart: unless-stopped

  mysql:
    image: mysql:8.0
    container_name: pdns-mysql
    environment:
      - MYSQL_ROOT_PASSWORD=rootpass
      - MYSQL_DATABASE=pdns
      - MYSQL_USER=pdns
      - MYSQL_PASSWORD=changeme
    volumes:
      - ./mysql/data:/var/lib/mysql
    restart: unless-stopped
```

### PowerDNS LUA Record Example

```lua
-- splitview.lua: Return different answers based on source IP
function splitview(ip)
    if ip:match("^192%.168%.") or ip:match("^10%.") then
        return "192.168.1.100"  -- Internal IP
    else
        return "203.0.113.10"   -- Public IP
    end
end
```

Then in your zone, define a LUA record:
```
www  IN  LUA  A  "splitview(bestwho)" 30
```

When a query arrives, PowerDNS calls the LUA function with the client's IP, and the function returns the appropriate response. This is far more flexible than BIND's static views — you can implement any custom logic you need.

### GeoIP Backend Example

PowerDNS can also use the GeoIP backend for geographic-based split-view:
```yaml
launch+=geoip
geoip-database-file=/usr/share/GeoIP/GeoLite2-City.mmdb
geoip-zones-file=/etc/powerdns/geoip.zones
```

Zone configuration using YAML:
```yaml
domains:
  example.com:
    - ttl: 300
      records:
        www:
          - geo:
              US: 203.0.113.10
              EU: 198.51.100.20
              AS: 192.0.2.30
            default: 203.0.113.10
```

### Pros and Cons

- ✅ Dynamic logic via LUA — no zone file duplication
- ✅ GeoIP integration for geographic routing
- ✅ Backend extensibility (MySQL, PostgreSQL, LDAP, etc.)
- ✅ DNSSEC-compatible dynamic responses
- ❌ LUA scripting has a learning curve
- ❌ Per-query script execution adds latency
- ❌ GeoIP database must be kept up to date

## Knot DNS Response Policy

Knot DNS is a high-performance authoritative DNS server developed by CZ.NIC. While it does not have a direct "views" equivalent, its **response policy** module (`mod-rrl` and `mod-dnstap`) combined with query tuning provides flexible response differentiation.

### Key Features
- **Query modules** — pluggable query processing pipeline
- **`mod-rrl`** — Response Rate Limiting with per-client policies
- **`mod-dnstap`** — query logging for analysis
- **`acl` blocks** — per-ACL action control
- **`submission` and `policy`** — fine-grained client-based actions
- **Fast zone reloads** — incremental zone transfers with minimal latency

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  knot:
    image: cznic/knot:3.4
    container_name: knot-splitview
    ports:
      - "53:53/tcp"
      - "53:53/udp"
    volumes:
      - ./knot/config:/etc/knot
      - ./knot/zones:/var/lib/knot/zones
      - ./knot/journal:/var/lib/knot/journal
    restart: unless-stopped
```

### Knot DNS ACL-Based Configuration

```
server:
    listen: 0.0.0.0@53

acl:
  - id: internal
    address: [192.168.0.0/16, 10.0.0.0/8]
    action: [notify, transfer]
  - id: external
    address: [0.0.0.0/0]
    action: notify

template:
  - id: default
    storage: /var/lib/knot/zones
    file: "%s.zone"

zone:
  - domain: example.com
    file: "example.com.internal.zone"
    acl: [internal]
  - domain: example.com
    file: "example.com.external.zone"
    acl: [external]
```

Knot's approach maps different zone files to different ACLs on the same domain, achieving split-view functionality. The `acl` directive on each zone definition controls which clients can query that particular zone configuration.

### Pros and Cons

- ✅ Extremely fast — designed for TLD-level query volumes
- ✅ Clean, modern configuration syntax
- ✅ Efficient memory usage — minimal overhead for ACL-based routing
- ✅ Incremental zone reloads without restart
- ❌ No dynamic LUA scripting equivalent
- ❌ Limited policy complexity compared to PowerDNS backends
- ❌ Multiple zone definitions for the same domain can be confusing

## Comparison Table

| Feature | BIND 9 Views | PowerDNS LUA/GeoIP | Knot DNS ACL |
|---------|-------------|-------------------|--------------|
| **Stars** | 743★ | 4,383★ | 306★ |
| **Split-View Method** | Static views + ACL | Dynamic LUA records | ACL-mapped zone files |
| **Dynamic Logic** | No — static zone files | Yes — LUA scripts | No — static zone files |
| **GeoIP Support** | Via GeoIP ACL module | Native GeoIP backend | No built-in support |
| **DNSSEC** | Full support | Full dynamic DNSSEC | Full support |
| **Configuration Language** | Named-style (classic) | YAML + LUA | YAML (libyang) |
| **Performance** | Good (~50K qps) | Good (~40K qps) | Excellent (~200K qps) |
| **Memory Usage** | High (per-view copies) | Moderate | Low |
| **Learning Curve** | Medium | High (LUA scripting) | Low-Medium |
| **Primary Language** | C | C++ | C |
| **Last Update** | 2026-06-02 | 2026-06-02 | 2026-06-02 |

## Why Self-Host Your DNS Split-View?

Self-hosting your DNS split-view configuration gives you complete control over how different client populations resolve your domain names. Unlike cloud DNS providers that charge per zone and per query, self-hosted DNS splits put you in full command of your namespace.

For organizations running hybrid infrastructure — with some services in the cloud and others on-premises — split-view DNS eliminates the need to maintain separate domain names for internal and external services. Employees can use the same `app.company.com` URL whether they are in the office or working remotely, with the DNS server automatically resolving it to the correct internal IP or public endpoint.

Data sovereignty is another critical consideration. When you self-host your DNS infrastructure, you control exactly which clients receive which information. There is no risk of a cloud misconfiguration accidentally exposing internal IP addresses or hostnames to the public internet — a mistake that has led to significant security incidents at major organizations. For a deeper dive into DNS privacy and encrypted DNS, see our [complete DNS privacy guide](../self-hosted-dns-privacy-doh-dot-dnscrypt-complete-guide-2026/).

Cost savings compound as your infrastructure grows. BIND and PowerDNS are free, and Knot DNS is developed by a non-profit registry. The only operating costs are server resources, which are modest for DNS workloads. If you are exploring DNS server options more broadly, check our [DNS server comparison guide](../self-hosted-dns-server-powerdns-bind-unbound-coredns-guide-2026/) and our [DNS load balancing guide](../2026-05-23-self-hosted-dns-load-balancing-coredns-powerdns-bind-guide/).

## FAQ

### What is the difference between split-view DNS and anycast DNS?

Split-view DNS returns different answers based on the querying client's IP address, while anycast DNS routes queries to the nearest server instance using BGP routing. Split-view is about *what* answer you return, while anycast is about *where* the query is answered. They are complementary — you can run BIND views on anycast-advertised DNS servers for geographic and logical routing simultaneously.

### Does split-view DNS work with DNSSEC?

Yes — but with caveats. BIND can sign different zone files with different keys for each view, which works seamlessly. PowerDNS supports dynamic DNSSEC signatures with LUA records, meaning the DNSSEC records are generated on-the-fly based on the computed response. Knot DNS signs each zone definition independently. The key requirement is that each view must have its own DNSSEC signing keys and the zone content must be consistent.

### Can I use split-view DNS with Kubernetes or containers?

Yes. All three servers run in containers and can be deployed in Kubernetes. However, Kubernetes DNS patterns differ — you may find it simpler to use CoreDNS with the `view` plugin or to run separate DNS deployments for internal and external traffic. Our [DNS load balancing guide](../2026-05-23-self-hosted-dns-load-balancing-coredns-powerdns-bind-guide/) covers CoreDNS-based setups.

### Which DNS server is best for a small business with one office?

BIND 9 with views is the most straightforward choice for a simple internal/external split. The configuration is well-documented, the static zone files are easy to audit, and there is a large community for troubleshooting. Set up one internal view matching your office subnet and one external view matching `any`, and you are done.

### How do I test that my split-view DNS is working correctly?

Use `dig` with the `-b` flag to specify a source IP address: `dig @dns-server example.com -b 192.168.1.100`. This simulates a query coming from an internal IP, allowing you to verify the internal view response. For external testing, use `dig @dns-server example.com` from outside your network or specify a public source IP. Also test with `dig +short` for quick response comparison.

### Can PowerDNS LUA records affect DNS performance?

Yes — LUA record callbacks execute on every query, adding approximately 0.1-0.5ms per invocation. For a low-traffic authoritative server (under 1,000 qps), this is negligible. For high-traffic deployments (>10,000 qps), consider pre-computing common results or using the GeoIP backend which has native C++ performance. PowerDNS also supports LUA JIT compilation in newer versions, which significantly reduces script execution overhead.

---

**💰 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — the world's largest prediction market platform where you can bet on anything from election outcomes to tech regulation timelines. Unlike gambling, this is a real information market: the more you know, the better your odds. I've profited by predicting tech-related event trajectories. Sign up with my invite link: [Polymarket.com](https://polymarket.com/?r=fc8a0)**

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DNS Split-View Traffic Management: BIND Views vs PowerDNS LUA Records vs Knot DNS Response Policy",
  "description": "Comprehensive comparison of BIND 9 views, PowerDNS LUA/GeoIP backend, and Knot DNS ACL-based response policy for implementing split-view DNS traffic management in self-hosted environments.",
  "datePublished": "2026-06-03",
  "dateModified": "2026-06-03",
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
