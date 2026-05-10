---
title: "Self-Hosted IRR Database Management: IRRd vs IRRToolSet vs IRRexplorer Guide"
date: "2026-05-10"
tags: ["irr", "routing", "bgp", "network-management", "self-hosted", "database"]
draft: false
---

The Internet Routing Registry (IRR) is a globally distributed database of routing policies used by network operators to publish and validate BGP route announcements. Managing IRR data — from maintaining route objects to validating RPSL policies and exploring cross-registry dependencies — is essential for any ISP, hosting provider, or large enterprise that peers on the public internet.

In this guide, we compare three open-source tools for self-hosted IRR database management: **IRRd**, **IRRToolSet**, and **IRRexplorer**. Each serves a different role in the IRR ecosystem, from full-featured IRR server to policy analysis toolkit to web-based exploration interface.

## What Is the Internet Routing Registry (IRR)?

The IRR is a collection of databases that store routing policy information in the Routing Policy Specification Language (RPSL). Network operators publish route objects, aut-num objects, and as-set objects to define which ASNs are authorized to announce which IP prefixes. Major IRR databases include RADB (Routing Assets Database), ARIN, RIPE, APNIC, and BGP Tools.

Before BGP security mechanisms like RPKI became widespread, the IRR was the primary method for filtering route announcements. Even today, many network operators use IRR data alongside RPKI ROAs to build comprehensive route filters. Managing this data locally gives you full control over policy validation, object generation, and registry synchronization.

## Why Self-Host IRR Management Tools?

Running your own IRR management infrastructure offers several advantages over relying solely on public registry web interfaces:

**Offline Analysis and Validation:** When you mirror IRR databases locally, you can run policy analysis queries without depending on remote server availability. This is critical during network incidents when every second counts and public IRR servers may be slow or unreachable.

**Custom Policy Generation:** Self-hosted tools let you generate RPSL objects using your own templates and validation rules. You can integrate IRR management into your automation pipeline, ensuring route objects are created consistently across all registries where you publish.

**Cross-Registry Consistency Checks:** Different IRR databases may have conflicting information about the same prefix or ASN. Running local tools lets you compare objects across registries, identify discrepancies, and maintain a single source of truth for your routing policy.

**Faster Lookups and Bulk Operations:** Querying a local IRR mirror is orders of magnitude faster than making repeated WHOIS queries to remote servers. This matters when you need to analyze thousands of route objects or perform bulk policy audits.

**Integration with Internal Systems:** Self-hosted IRR tools can be connected to your internal IPAM, network monitoring, and configuration management systems, creating a unified view of your network's routing posture.

For organizations managing BGP peering relationships, maintaining accurate IRR data is not optional — it directly impacts route filtering, prefix validation, and peering policies used by upstream providers and exchange points.

For related reading on BGP infrastructure, see our [FRRouting vs Bird vs OpenBGPD comparison](../2026-04-19-frrouting-vs-bird-vs-openbgpd-self-hosted-bgp-routing-guide-2026/) and [BGP monitoring and route alerting guide](../2026-05-09-self-hosted-bgp-monitoring-route-alerting-bgpalerter-exabgp-gobgp/). If you're interested in network-level security filtering, check our [DNS firewall RPZ guide](../2026-04-21-self-hosted-dns-firewall-rpz-unbound-powerdns-bind9-knot-guide-2026/).

## IRRd — Full-Featured IRR Database Server

[IRRd](https://github.com/irrdnet/irrd) (Internet Routing Registry daemon) is the most comprehensive open-source IRR server implementation. Written in Python, it supports the full RPSL language, mirrors multiple upstream registries, and provides a WHOIS server, REST API, and email-based update interface.

### Key Features

- **Multi-registry mirroring:** Synchronize with RADB, RIPE, ARIN, APNIC, LACNIC, and other IRR databases
- **Full RPSL support:** Parse and validate all RPSL object types including route, aut-num, as-set, route-set, and inetnum
- **WHOIS server:** RFC-compliant WHOIS interface for querying local IRR data
- **REST API:** Modern JSON API for programmatic access to IRR objects and validation
- **RPKI integration:** Validate route objects against RPKI ROAs and flag invalid announcements
- **Email updates:** Accept object creation and modification via signed email (PGP)
- **IRRd v4 architecture:** PostgreSQL backend for reliable storage and fast queries
- **182 GitHub stars** and active development

### Deployment

IRRd requires PostgreSQL and runs as a Python application. Here is a Docker Compose setup:

```yaml
version: "3.8"
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: irrd
      POSTGRES_USER: irrd
      POSTGRES_PASSWORD: irrd_secret
    volumes:
      - pgdata:/var/lib/postgresql/data
    restart: unless-stopped

  irrd:
    image: ghcr.io/irrdnet/irrd:latest
    depends_on:
      - postgres
    environment:
      IRRD_DATABASE_URL: "postgresql+asyncpg://irrd:irrd_secret@postgres:5432/irrd"
      IRRD_WHOIS_SERVER_ENABLED: "true"
      IRRD_HTTP_SERVER_ENABLED: "true"
      IRRD_RPKI_ENABLED: "true"
    volumes:
      - ./config.yaml:/etc/irrd/config.yaml
      - irrd-data:/var/lib/irrd
    ports:
      - "43:43"
      - "8080:8080"
    restart: unless-stopped

volumes:
  pgdata:
  irrd-data:
```

The configuration file (`config.yaml`) defines which registries to mirror, RPKI validation settings, and email update parameters:

```yaml
irrd:
  database_url: "postgresql+asyncpg://irrd:irrd_secret@postgres:5432/irrd"
  piddir: "/var/lib/irrd"
  sources:
    RADB:
      nrtm_host: "rr.ntt.net"
      nrtm_port: 43
      import_timer: 7200
    RIPE:
      nrtm_host: "rr.ntt.net"
      nrtm_port: 43
      import_timer: 7200
    ARIN:
      nrtm_host: "rr.ntt.net"
      nrtm_port: 43
      import_timer: 7200
  rpki:
    roa_source: "https://rpki.gin.ntt.net/api/export.json"
    validate_rpki: true
```

## IRRToolSet — RPSL Policy Analysis Toolkit

[IRRToolSet](https://github.com/irrtoolset/irrtoolset) is a comprehensive toolkit for analyzing and generating IRR routing policies. Unlike IRRd, which is a database server, IRRToolSet focuses on the **policy analysis** side: parsing RPSL objects, computing AS paths, determining transit costs, and generating router configurations from IRR data.

### Key Features

- **Policy analysis engine:** Compute reachability, transit paths, and filtering policies from IRR data
- **RPSL parser:** Validate and parse all RPSL object types with detailed error reporting
- **Router config generation:** Generate Cisco IOS, Juniper JunOS, and BIRD configurations from IRR policies
- **AS path computation:** Calculate shortest paths and alternative routes between ASNs
- **Filter generation:** Build prefix-lists and route-maps from IRR as-set and route-set objects
- **141 GitHub stars** — mature project with a long history in the network operations community
- **Offline operation:** Does not require a running IRR server — works with imported RPSL data files

### Deployment and Usage

IRRToolSet is a C++ application typically compiled from source. It reads RPSL data from flat files or IRRd exports:

```bash
# Install dependencies on Ubuntu/Debian
apt-get update && apt-get install -y \
    build-essential cmake libboost-all-dev \
    libmysqlclient-dev flex bison

# Clone and build
git clone https://github.com/irrtoolset/irrtoolset.git
cd irrtoolset
mkdir build && cd build
cmake ..
make -j$(nproc)

# Export data from IRRd for analysis
docker exec irrd irrd-export --source RADB --output /tmp/radb.rpsl

# Run policy analysis
./irrtoolset -f policy.conf /tmp/radb.rpsl
```

A sample policy configuration for generating BGP filters:

```
# policy.conf - IRRToolSet policy definition
source RADB {
    asn 64512;
    filter inbound {
        import from AS-UPSTREAM1;
        import from AS-UPSTREAM2;
    };
    filter outbound {
        export AS-ALL to AS-CUSTOMERS;
    };
};

# Generate Cisco IOS config
./irrtoolset -t cisco -p policy.conf /tmp/radb.rpsl > bgp-filters.conf
```

## IRRexplorer — Web-Based IRR Exploration Interface

IRRexplorer provides a **visual, web-based interface** for exploring IRR databases, visualizing relationships between ASNs, prefixes, and route objects. While IRRd handles the database backend and IRRToolSet performs policy analysis, IRRexplorer focuses on making IRR data accessible through an intuitive web UI.

### Key Features

- **Web-based visualization:** Graphical representation of ASN-prefix relationships
- **Interactive exploration:** Click through AS-sets, route-sets, and peering relationships
- **Prefix-to-ASN mapping:** Quickly find which ASN announces a given prefix and through which IRR
- **Cross-registry search:** Query multiple IRR databases simultaneously from a single interface
- **Dependency visualization:** See which AS-sets reference other AS-sets and identify circular dependencies
- **Lightweight deployment:** Simple web application that can run alongside IRRd or query public registries
- **API integration:** Can connect to a local IRRd instance or query remote WHOIS servers

### Deployment

IRRexplorer is a lightweight web application. A typical deployment alongside IRRd:

```yaml
version: "3.8"
services:
  irrexplorer:
    image: ghcr.io/irrdnet/irrexplorer:latest
    environment:
      IRRD_API_URL: "http://irrd:8080/api/v1"
      # Or query public registries directly
      WHOIS_SERVERS: "rr.ntt.net,whois.ripe.net"
    ports:
      - "8081:8080"
    restart: unless-stopped
    depends_on:
      - irrd
```

The web interface provides real-time search results, ASN graphs, and prefix visualization without requiring direct database access.

## Comparison Table

| Feature | IRRd | IRRToolSet | IRRexplorer |
|---|---|---|---|
| **Primary role** | IRR database server | Policy analysis toolkit | Web exploration UI |
| **Language** | Python | C++ | Web (JavaScript) |
| **RPSL parsing** | Full | Full | Limited |
| **WHOIS server** | Yes (RFC-compliant) | No | No |
| **REST API** | Yes | No | Yes |
| **RPKI validation** | Yes (built-in) | No | Via IRRd API |
| **Policy analysis** | Basic | Comprehensive | Visual exploration |
| **Router config gen** | No | Yes (IOS/JunOS/BIRD) | No |
| **Multi-registry** | Yes (NRTM mirroring) | Via imported files | Yes (simultaneous query) |
| **Email updates** | Yes (PGP-signed) | No | No |
| **Backend database** | PostgreSQL | Flat files | In-memory / API |
| **Docker support** | Yes | Build from source | Yes |
| **GitHub stars** | 182 | 141 | Community project |
| **Best for** | Running IRR server | Generating BGP filters | Visual IRR exploration |

## Choosing the Right IRR Tool

- **Choose IRRd** if you need a full IRR database server that mirrors public registries, serves WHOIS queries, and integrates RPKI validation. It is the foundation for any self-hosted IRR infrastructure.

- **Choose IRRToolSet** if your primary goal is to analyze IRR policies, generate BGP filter configurations, and compute AS path relationships. It is ideal for network engineers who need to translate IRR data into router configurations.

- **Choose IRRexplorer** if you want a visual interface to explore IRR data, understand ASN relationships, and quickly look up prefix announcements. It complements IRRd by providing a user-friendly frontend.

In practice, a complete IRR management stack runs **IRRd as the database backend**, connects **IRRToolSet for periodic policy analysis**, and deploys **IRRexplorer as the web frontend** for daily operations.

## FAQ

### What is the IRR and why does it matter for BGP?

The Internet Routing Registry (IRR) is a distributed database where network operators publish routing policies in RPSL format. BGP routers use IRR data to build prefix filters, validate route announcements, and determine peering policies. Without accurate IRR data, your upstream providers may not filter hijacked prefixes correctly.

### Can IRRd replace RPKI?

No. IRRd and RPKI serve different purposes. IRR provides operator-published routing policies (which can be inaccurate), while RPKI provides cryptographically validated route origin authorizations. Best practice is to use both: IRR for comprehensive policy data and RPKI for cryptographic validation of route origins.

### How do I mirror IRR databases locally?

IRRd supports NRTM (Near Real-Time Mirroring) to synchronize with public IRR servers. Configure the `sources` section in `config.yaml` with the NRTM host and port for each registry (RADB, RIPE, ARIN, etc.). IRRd will automatically poll and update its local database.

### Can IRRToolSet generate configurations for my specific router platform?

Yes. IRRToolSet supports configuration generation for Cisco IOS, Juniper JunOS, and BIRD. You define a policy file describing your import/export filters, and IRRToolSet translates IRR data into platform-specific route-maps, prefix-lists, and policy statements.

### Is it legal to mirror public IRR databases?

Yes. IRR databases are publicly accessible and designed to be mirrored. The NRTM protocol exists specifically for this purpose. However, you should respect the update intervals specified by each registry and not overload their servers with excessive queries.

### How often should IRR data be updated?

IRR data changes frequently as networks modify their routing policies. Most registries update their NRTM feeds every 15-30 minutes. IRRd can be configured to poll at these intervals. For critical operations, validate IRR data against RPKI ROAs before applying route filters.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted IRR Database Management: IRRd vs IRRToolSet vs IRRexplorer Guide",
  "description": "Compare IRRd, IRRToolSet, and IRRexplorer for self-hosted Internet Routing Registry database management, policy analysis, and BGP route object visualization.",
  "datePublished": "2026-05-10",
  "dateModified": "2026-05-10",
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
