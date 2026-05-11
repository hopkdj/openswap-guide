---
title: "Self-Hosted LDAP Federation and Meta Directories: OpenLDAP Meta Backend vs Gluu vs ldapx (2026)"
date: "2026-05-11"
tags: ["ldap", "identity-management", "federation", "directory-services", "authentication"]
draft: false
---

Managing multiple LDAP directories across an organization is a common challenge. When you have separate directories for different departments, legacy systems, or acquired companies, users and applications need a unified view. LDAP federation and meta directory solutions solve this by aggregating multiple backends behind a single interface.

In this guide, we compare three self-hosted approaches to LDAP federation: the **OpenLDAP meta backend**, the **Gluu Server** identity platform, and **ldapx**, a flexible LDAP proxy for packet inspection and transformation.

## What Is LDAP Federation?

LDAP federation refers to the practice of connecting multiple independent LDAP directories and presenting them as a unified directory service. A meta directory sits between clients and backend servers, routing queries to the appropriate source, aggregating results, and optionally transforming data on the fly.

Common use cases include:

- **Multi-tenant environments** where each tenant has its own directory
- **Mergers and acquisitions** requiring consolidation of existing directories
- **Hybrid identity** setups combining on-premises AD with cloud directories
- **Legacy migration** where old and new directories must coexist during transition
- **Attribute aggregation** pulling user data from multiple authoritative sources

## OpenLDAP Meta Backend

OpenLDAP includes a built-in meta backend (`back-meta`) that proxies LDAP operations to one or more remote servers. It is part of the standard OpenLDAP distribution and requires no additional software.

### Architecture

The meta backend operates at the LDAP protocol level, intercepting client requests and forwarding them to configured remote targets. Each target is defined with its own URI, bind credentials, and search base. The meta backend can rewrite DNs and attributes on the fly using the `rwm` (rewrite/remap) overlay.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  openldap-meta:
    image: osixia/openldap:1.5.0
    container_name: openldap-meta
    hostname: ldap-meta.example.com
    environment:
      LDAP_ORGANISATION: "Federation Directory"
      LDAP_DOMAIN: "federation.example.com"
      LDAP_ADMIN_PASSWORD: "admin-secret"
      LDAP_BACKEND: "custom"
    volumes:
      - ./meta-config:/etc/ldap/slapd.d
      - ./meta-data:/var/lib/ldap
      - ./certs:/container/service/slapd/assets/certs
    ports:
      - "389:389"
      - "636:636"
    restart: unless-stopped
```

The meta backend configuration in `slapd.conf` format:

```
database    meta
suffix      "dc=federation,dc=example,dc=com"

uri         "ldap://ldap1.example.com/dc=dept1,dc=example,dc=com"
idassert-bind bindmethod=simple
    binddn="cn=admin,dc=dept1,dc=example,dc=com"
    credentials="secret1"
    mode=self

uri         "ldap://ldap2.example.com/dc=dept2,dc=example,dc=com"
idassert-bind bindmethod=simple
    binddn="cn=admin,dc=dept2,dc=example,dc=com"
    credentials="secret2"
    mode=self

overlay     rwm
rwm-suffixMap   search
rwm-map     attribute   uid     sAMAccountName
```

### Key Features

- **Native to OpenLDAP** — no additional dependencies
- **DN rewriting** — `rwm` overlay transforms DNs between client-facing and backend formats
- **Attribute mapping** — remap attribute names across heterogeneous directories
- **Failover support** — multiple URIs per target with automatic fallback
- **Transparent proxy** — clients see a single unified directory

### Limitations

- **No built-in UI** — all configuration is file-based
- **Limited transformation logic** — complex attribute aggregation requires custom overlays
- **Performance overhead** — each query may trigger multiple backend lookups
- **Stale data** — no caching layer; every query hits the backend

## Gluu Server Federation

Gluu Server is a comprehensive identity and access management platform that includes LDAP federation capabilities through its oxTrust admin interface and oxAuth authentication engine. It provides a web-based management console and supports SAML, OAuth, and OIDC alongside LDAP.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  gluu:
    image: gluufederation/gluu-server:4.5.0
    container_name: gluu-server
    hostname: idp.example.com
    environment:
      - GLUU_VERSION=4.5.0
      - HOST_IP=192.168.1.100
      - GLUU_CACHE_REFRESH=True
    volumes:
      - gluu-data:/opt/gluu
      - gluu-etc:/etc/gluu
    ports:
      - "443:443"
      - "1636:1636"
      - "8080:8080"
    restart: unless-stopped
    cap_add:
      - SYS_ADMIN

volumes:
  gluu-data:
  gluu-etc:
```

### Federation Configuration

Gluu's Cache Refresh feature synchronizes data from external LDAP sources into its internal directory:

1. Navigate to **Configuration > Cache Refresh** in the oxTrust admin UI
2. Add source LDAP servers with connection details
3. Map attributes between source and target directories
4. Configure the refresh schedule (e.g., every 5 minutes)
5. Enable Cache Refresh and monitor synchronization logs

### Key Features

- **Web-based administration** — full GUI for configuration and monitoring
- **Cache Refresh** — periodic synchronization from external directories
- **Multi-protocol support** — LDAP, SAML, OIDC, OAuth 2.1, SCIM
- **Attribute transformation** — scripting engine (Python) for custom mapping
- **User portal** — self-service password reset and profile management

### Limitations

- **Resource-intensive** — requires 8 GB+ RAM for production
- **Complex setup** — many moving parts (LDAP, oxAuth, oxTrust, Casa)
- **Vendor lock-in** — Gluu-specific configuration patterns
- **Less flexible** — federation tied to Gluu's identity platform model

## ldapx — LDAP Proxy Framework

ldapx is a flexible LDAP proxy written in Go that intercepts LDAP packets and allows inspection, transformation, and routing of LDAP traffic. It is designed for organizations that need fine-grained control over LDAP request/response processing.

GitHub: [Macmod/ldapx](https://github.com/Macmod/ldapx) (210 stars)

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  ldapx:
    image: macmod/ldapx:latest
    container_name: ldapx-proxy
    environment:
      LDAPX_LISTEN_ADDR: "0.0.0.0:1389"
      LDAPX_BACKEND_1: "ldap://ldap1.example.com:389"
      LDAPX_BACKEND_2: "ldap://ldap2.example.com:389"
      LDAPX_TRANSFORM_RULES: "/etc/ldapx/rules.yaml"
    volumes:
      - ./ldapx-config:/etc/ldapx
    ports:
      - "1389:1389"
    restart: unless-stopped
```

Example transformation rules in `rules.yaml`:

```yaml
rules:
  - name: "Route by base DN"
    match:
      baseDN: "ou=engineering,dc=example,dc=com"
    action: route
    target: "ldap://eng-ldap.example.com:389"

  - name: "Map uid to sAMAccountName"
    match:
      attribute: "uid"
    action: rename
    newAttribute: "sAMAccountName"

  - name: "Filter inactive users"
    match:
      filter: "(userAccountControl:1.2.840.113556.1.4.803:=2)"
    action: drop
```

### Key Features

- **Packet-level inspection** — intercept and modify LDAP operations in transit
- **Rule-based routing** — direct queries to different backends based on DN, filter, or attributes
- **Attribute transformation** — rename, filter, or modify attributes on the fly
- **Lightweight** — single binary, low memory footprint
- **Go-based** — modern language, cross-platform builds

### Limitations

- **Smaller community** — 210 stars, limited documentation
- **No built-in caching** — relies on backend servers for performance
- **Manual configuration** — YAML rules require careful testing
- **No GUI** — CLI and configuration file only

## Comparison Table

| Feature | OpenLDAP Meta | Gluu Server | ldapx |
|---------|--------------|-------------|-------|
| **Type** | LDAP backend | IAM platform | LDAP proxy |
| **Web UI** | No | Yes (oxTrust) | No |
| **Protocol Support** | LDAP only | LDAP, SAML, OIDC, OAuth | LDAP only |
| **Attribute Mapping** | Via rwm overlay | GUI + Python scripts | YAML rules |
| **Caching** | None | Cache Refresh | None |
| **Resource Usage** | Low (~256 MB) | High (~8 GB) | Low (~128 MB) |
| **Setup Complexity** | Medium | High | Low-Medium |
| **Federation Model** | Real-time proxy | Periodic sync | Real-time proxy |
| **Active Development** | Yes (OpenLDAP project) | Yes (Gluu Federation) | Yes (community) |
| **Docker Support** | Official images | Official images | Community image |
| **GitHub Stars** | 579 (OpenLDAP) | 189 (setup scripts) | 210 |
| **Best For** | Simple proxy federation | Full IAM with federation | Custom packet-level control |

## Choosing the Right LDAP Federation Solution

The choice between these three approaches depends on your organization's needs:

**OpenLDAP meta backend** is the best choice when you need a straightforward LDAP proxy that aggregates multiple directories into a single namespace. It is ideal for organizations already running OpenLDAP who want to add federation without introducing new software. The `rwm` overlay provides sufficient attribute mapping for most use cases.

**Gluu Server** is appropriate when LDAP federation is just one piece of a broader identity management strategy. If you also need SSO, MFA, SCIM provisioning, and a self-service user portal, Gluu provides all of these in a single platform. The trade-off is higher resource consumption and operational complexity.

**ldapx** fits scenarios where you need fine-grained control over LDAP packet processing. Its rule-based routing and transformation engine is more flexible than OpenLDAP's `rwm` overlay for complex scenarios. It is a good fit for organizations building custom LDAP gateways or migrating between directory schemas.

## Deployment Architecture Considerations

### High Availability

For production deployments, each federation solution requires HA configuration:

- **OpenLDAP meta**: Deploy multiple instances behind a load balancer (HAProxy) with a shared configuration directory via NFS or GlusterFS
- **Gluu**: Use the built-in cluster manager or deploy multiple nodes with a shared Cassandra backend
- **ldapx**: Run multiple instances with a TCP load balancer; stateless design makes horizontal scaling straightforward

### Security

- Always use LDAPS (port 636) or StartTLS for backend connections
- Configure certificate validation for each remote server
- Use `idassert-bind` in OpenLDAP or equivalent in other tools for secure backend authentication
- Implement network-level segmentation between the federation layer and backend directories

For organizations also managing SSH certificates, integrating LDAP federation with a [self-hosted SSH certificate authority](../2026-04-25-step-ca-vs-teleport-vs-vault-self-hosted-ssh-certificate-management-guide/) provides end-to-end identity verification across both LDAP and SSH access.

## Why Self-Host LDAP Federation?

Running your own LDAP federation infrastructure provides several advantages over cloud-managed identity services:

**Data sovereignty** — All directory queries and user data remain within your infrastructure. No third-party service processes authentication requests or stores user attributes. This is critical for organizations in regulated industries (healthcare, finance, government) where data residency requirements mandate on-premises identity management.

**Cost savings** — Cloud identity providers charge per user per month. For organizations with thousands of users across multiple directories, self-hosted federation eliminates recurring SaaS fees. OpenLDAP and ldapx are completely free; Gluu's Community Edition is open source with no per-user licensing.

**No vendor lock-in** — Cloud identity platforms often use proprietary schemas and APIs. Self-hosted LDAP federation uses standard LDAPv3 protocols, ensuring interoperability with any LDAP-compatible application. You can switch backend directories or add new ones without changing client configurations.

**Custom transformation logic** — Self-hosted solutions allow arbitrary attribute mapping, DN rewriting, and query transformation. Cloud providers typically offer limited customization options. With OpenLDAP's overlays or ldapx's rule engine, you can implement organization-specific logic that no SaaS product supports.

**Integration with existing infrastructure** — Self-hosted federation integrates seamlessly with your existing monitoring, logging, and security tools. Export LDAP metrics to Prometheus, send audit logs to your SIEM, and apply network policies consistent with your data center architecture.

For organizations managing lightweight directory services, comparing [LLDAP vs GLauth](../2026-04-24-lldap-vs-glauth-lightweight-ldap-self-hosted-auth-guide/) provides additional context on simplified LDAP alternatives. When broader identity synchronization is needed, our [Apache Syncope vs MidPoint vs LTB LDAP Toolbox guide](../2026-05-04-apache-syncope-vs-midpoint-vs-ltb-ldap-toolbox-self-hosted-identity-sync-guide/) covers comprehensive identity lifecycle management.

## FAQ

### What is the difference between LDAP federation and LDAP replication?

LDAP replication copies data between servers so each has a complete copy. LDAP federation (or meta directory) presents multiple directories as a single logical directory without copying data. Federation routes queries to the appropriate backend in real time, while replication maintains redundant copies.

### Can OpenLDAP meta backend handle write operations?

Yes, but with caveats. The meta backend can proxy write operations (add, modify, delete) to the appropriate backend server. However, if your federation spans multiple directories with overlapping schemas, writes may fail or produce inconsistent results. For write-heavy workloads, consider Gluu's Cache Refresh which handles synchronization more robustly.

### How does Gluu's Cache Refresh differ from OpenLDAP's meta backend?

Gluu Cache Refresh periodically pulls data from source directories and stores it locally, providing a cached view. OpenLDAP meta backend proxies queries in real time without caching. Cache Refresh offers better read performance but introduces latency between source updates and local visibility. The meta backend always returns current data but may be slower for complex queries.

### Is ldapx production-ready?

ldapx is a capable LDAP proxy with active development, but it has a smaller community than OpenLDAP or Gluu. For production use, thoroughly test your transformation rules and monitor query performance. It is best suited for organizations with LDAP expertise who can troubleshoot issues independently.

### Can I use LDAP federation with Active Directory?

Yes. All three solutions can federate with Active Directory. OpenLDAP's `rwm` overlay can map AD's `sAMAccountName` to standard LDAP `uid` attributes. Gluu Cache Refresh natively supports AD as a source directory. ldapx can route queries to AD servers and transform attributes via its rule engine.

### How do I monitor LDAP federation performance?

For OpenLDAP, enable query logging (`loglevel 256`) and monitor with Prometheus exporters. Gluu provides built-in statistics through the oxTrust dashboard. ldapx logs all proxied operations and can export metrics to any Prometheus-compatible endpoint. Monitor query latency, backend error rates, and connection pool utilization.

### What happens when a backend directory is unavailable?

OpenLDAP meta backend can be configured with multiple URIs per target for automatic failover. Gluu Cache Refresh marks sources as unavailable and continues serving cached data. ldapx can be configured with fallback backends in its routing rules. In all cases, plan for graceful degradation and alerting on backend health.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted LDAP Federation and Meta Directories: OpenLDAP Meta Backend vs Gluu vs ldapx (2026)",
  "description": "Compare self-hosted LDAP federation solutions: OpenLDAP meta backend, Gluu Server, and ldapx. Learn how to aggregate multiple LDAP directories with Docker deployment guides.",
  "datePublished": "2026-05-11",
  "dateModified": "2026-05-11",
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
