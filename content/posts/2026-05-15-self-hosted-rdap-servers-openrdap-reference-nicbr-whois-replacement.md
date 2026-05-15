---
title: "Self-Hosted RDAP Servers: OpenRDAP, Reference RDAP & NIC.br RDAP (WHOIS Replacement Guide 2026)"
date: "2026-05-15"
tags: ["rdap", "whois", "domain-management", "network-infrastructure", "self-hosted"]
draft: false
---

The Registration Data Access Protocol (RDAP) is the modern replacement for the aging WHOIS protocol, providing structured JSON responses, standardized access control, and internationalization support. As ICANN has mandated RDAP compliance for all gTLD registries and registrars, self-hosting an RDAP server has become essential for domain registrars, registries, and organizations that manage their own DNS infrastructure.

This guide covers three open-source RDAP server implementations you can deploy on your own infrastructure: **OpenRDAP** (the nic.br reference implementation), **Reference RDAP Server** (the IETF reference implementation), and **NIC.br RDAP** (production-grade deployment by Brazil's national registry).

## What Is RDAP and Why Replace WHOIS?

WHOIS has been the standard for querying domain registration data since 1982, but it has significant limitations: plain text output with no standardization, no access control mechanisms, no internationalization support (ASCII-only), and inconsistent response formats across different registries. RDAP (RFC 7480-7484) addresses every one of these shortcomings:

| Feature | WHOIS | RDAP |
|---------|-------|------|
| Response format | Unstructured plain text | Standardized JSON |
| Access control | None | OAuth 2.0, authentication tiers |
| Internationalization | ASCII only | Unicode (i18n) support |
| Query protocol | Port 43 (TCP) | HTTPS with RESTful API |
| Pagination | Not supported | Built-in pagination |
| Redirects | Manual | HTTP 303 See Other |
| Standardization | Vendor-specific | IETF RFC 7480-7484 |

RDAP uses RESTful HTTPS endpoints to serve structured registration data, making it ideal for programmatic access by domain management tools, security platforms, and automated compliance systems. The protocol supports hierarchical queries — you can query for domain names, IP addresses, autonomous system numbers, and entity (contact) information through a unified API.

## Comparing Self-Hosted RDAP Server Implementations

### 1. OpenRDAP (nic.br Reference Implementation)

OpenRDAP is the open-source reference implementation developed by NIC.br (Brazil's network information center). It provides a complete RDAP server that can serve domain, IP, AS, and entity data from various backends including databases and flat files.

**Key features:**
- Full RFC 7480-7484 compliance
- Pluggable data source architecture (MySQL, PostgreSQL, flat files)
- Built-in help endpoint and bootstrapping
- Docker deployment support
- Written in Java, cross-platform compatible

OpenRDAP is the most widely deployed open-source RDAP server, serving as the backbone for several national registries' RDAP services. Its modular architecture allows you to swap data sources without changing the server code.

### 2. Reference RDAP Server (IETF Reference Implementation)

The IETF Reference RDAP Server is the official reference implementation of the RDAP protocol, maintained as part of the IETF's open-source tooling. It implements the core protocol specifications and serves as the conformance testing baseline.

**Key features:**
- Strict RFC compliance — the gold standard for protocol correctness
- XML-based configuration
- File-based data storage (suitable for testing and small deployments)
- Comprehensive test suite included
- Reference quality code for custom implementations

This implementation is best suited for testing, conformance validation, and as a learning tool. Production deployments typically prefer OpenRDAP or commercial solutions, but the reference server is invaluable for verifying your RDAP data conforms to the specification.

### 3. NIC.br RDAP (Production Server)

NIC.br RDAP is the production-grade RDAP server operated by Brazil's registry for the `.br` country-code TLD. It handles millions of domain queries daily and represents a battle-tested, high-throughput RDAP deployment.

**Key features:**
- Production-hardened at registry scale (`.br` TLD)
- High availability architecture with load balancing
- Integrated with NIC.br's registration database
- Rate limiting and abuse prevention
- Monitoring and observability built in

While NIC.br's production server is not directly available as open-source software, the architectural patterns and deployment strategies are documented and can be replicated using OpenRDAP as the base with custom scaling infrastructure.

### Feature Comparison Table

| Feature | OpenRDAP | Reference RDAP | NIC.br RDAP |
|---------|----------|---------------|-------------|
| RFC Compliance | Full (7480-7484) | Full (reference) | Full (production) |
| Data Sources | MySQL, PostgreSQL, files | Flat files only | Custom database |
| Docker Support | Yes | Manual setup | Custom infrastructure |
| Scalability | Medium (single instance) | Low (reference only) | High (distributed) |
| Access Control | Basic | None | OAuth 2.0, rate limiting |
| Language | Java | Java | Java (custom) |
| Production Ready | Yes | No (reference) | Yes (registry-scale) |
| GitHub Activity | Active | Sporadic | N/A (internal) |
| Best For | Self-hosted RDAP service | Testing/learning | Architecture patterns |

## Deployment Guide

### OpenRDAP with Docker Compose

The most practical deployment option for self-hosting is OpenRDAP with a MySQL backend:

```yaml
version: '3.8'

services:
  rdap-server:
    image: nicbr/openrdap:latest
    container_name: rdap-server
    ports:
      - "8080:8080"
    environment:
      - RDAP_DATASOURCE_TYPE=mysql
      - RDAP_DATASOURCE_URL=jdbc:mysql://rdap-db:3306/rdap
      - RDAP_DATASOURCE_USERNAME=rdap_user
      - RDAP_DATASOURCE_PASSWORD=rdap_secret
      - RDAP_BASE_URL=https://rdap.example.com/rdap/
    depends_on:
      - rdap-db
    restart: unless-stopped

  rdap-db:
    image: mysql:8.0
    container_name: rdap-db
    environment:
      - MYSQL_ROOT_PASSWORD=root_secret
      - MYSQL_DATABASE=rdap
      - MYSQL_USER=rdap_user
      - MYSQL_PASSWORD=rdap_secret
    volumes:
      - rdap_data:/var/lib/mysql
      - ./init-rdap.sql:/docker-entrypoint-initdb.d/init.sql
    restart: unless-stopped

volumes:
  rdap_data:
```

Initialize the database with the OpenRDAP schema:

```sql
CREATE TABLE IF NOT EXISTS domain (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    status VARCHAR(255),
    registration_date TIMESTAMP,
    expiration_date TIMESTAMP,
    registrar VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS nameserver (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    domain_id BIGINT,
    name VARCHAR(255) NOT NULL,
    FOREIGN KEY (domain_id) REFERENCES domain(id)
);
```

Start the server and test:

```bash
docker compose up -d
curl -s http://localhost:8080/rdap/domain/example.com | python3 -m json.tool
```

### Reference RDAP Server (Manual Installation)

The reference implementation requires Java 11+ and Maven:

```bash
git clone https://github.com/rdap/reference-server.git
cd reference-server
mvn clean package -DskipTests

# Run with file-based data
java -jar target/rdap-server-*.jar   --config=config/rdap.properties   --data-dir=./data
```

Configure the server to serve your test data:

```properties
rdap.service.port=8080
rdap.service.base-url=http://localhost:8080/rdap/
rdap.data.source=file
rdap.data.directory=./data/domains
```

### Reverse Proxy with Nginx

For production deployments, place an Nginx reverse proxy in front:

```nginx
server {
    listen 443 ssl http2;
    server_name rdap.example.com;

    ssl_certificate /etc/letsencrypt/live/rdap.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/rdap.example.com/privkey.pem;

    location /rdap/ {
        proxy_pass http://127.0.0.1:8080/rdap/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        add_header Access-Control-Allow-Origin *;
        add_header Content-Security-Policy "default-src 'none'";
    }
}
```

## Bootstrapping RDAP Data

RDAP requires bootstrapping files that tell clients which server handles which data. Create a bootstrap file:

```json
{
  "description": "RDAP Bootstrap File",
  "publication": "2026-05-15T00:00:00Z",
  "version": "1.0",
  "services": [
    [
      ["example.com"],
      ["example.net"],
      ["https://rdap.example.com/rdap/"]
    ]
  ],
  "insecure": false
}
```

Deploy this to the well-known location for your TLD, or publish it through your registry's bootstrap mechanism.

## Choosing the Right RDAP Server

**For domain registrars**: OpenRDAP is the best choice. It has the most complete feature set, active development, and Docker support for easy deployment. Connect it to your existing registration database and you have a production RDAP service.

**For testing and conformance**: The Reference RDAP Server is ideal. Use it to validate your RDAP data format, test client implementations, and ensure RFC compliance before deploying to production.

**For high-scale registries**: Study NIC.br's production architecture. While not directly available as open-source, the patterns (load-balanced OpenRDAP instances, database sharding, caching layers) are applicable to any large-scale RDAP deployment.

## Why Self-Host an RDAP Server?

Running your own RDAP server gives you full control over registration data access, response formatting, and compliance with regional data protection regulations like GDPR. Unlike relying on third-party WHOIS/RDAP services, self-hosting ensures:

- **Data sovereignty**: Your registration data never leaves your infrastructure. For organizations handling EU citizen data, this is critical for GDPR compliance and data residency requirements.
- **Custom access policies**: Implement granular authentication tiers, rate limiting, and redaction rules tailored to your jurisdiction. The IETF RDAP Response Profile (RFC 9082) supports data redaction that you can configure per-data-element.
- **Cost savings at scale**: Third-party RDAP/WHOIS APIs charge per-query or per-month fees. Self-hosting eliminates these costs entirely — a single OpenRDAP instance handles thousands of queries per second on modest hardware.
- **Integration with internal systems**: Connect your RDAP server directly to your billing, CRM, and provisioning systems for real-time data accuracy. No more syncing delays between external APIs and internal databases.
- **Compliance audit trail**: Self-hosting gives you complete logging of every query, essential for regulatory audits and abuse investigations. You control retention policies and can implement real-time alerting for suspicious query patterns.

For organizations managing domain portfolios, running an RDAP server alongside your DNS infrastructure (see our [BGP routing guide](../2026-04-19-frrouting-vs-bird-vs-openbgpd-self-hosted-bgp-routing-guide-2026/)) and [LDAP identity management](../2026-04-24-lldap-vs-glauth-lightweight-ldap-self-hosted-auth-guide/) creates a unified, self-contained network operations platform. If you also manage IP address space, our [IP address management guide](../2026-05-04-apache-syncope-vs-midpoint-vs-ltb-ldap-toolbox-self-hosted-identity-sync-guide/) covers the complementary tools for complete infrastructure management.

## FAQ

### What is the difference between WHOIS and RDAP?
WHOIS is a legacy plain-text protocol returning unstructured data over port 43. RDAP is the modern replacement using HTTPS with RESTful JSON responses, standardized formats, access control, internationalization, and hierarchical queries — all defined in IETF RFCs 7480-7484.

### Is RDAP mandatory for domain registrars?
Yes. ICANN has mandated RDAP compliance for all gTLD registries and registrars. Most ccTLD operators have also adopted RDAP voluntarily. The transition from WHOIS to RDAP is ongoing, and many registries now serve both protocols during the migration period.

### Can I use OpenRDAP with an existing MySQL database?
Yes. OpenRDAP supports pluggable data sources including MySQL, PostgreSQL, and flat files. You configure the connection string in the server properties and map your existing schema to the RDAP data model using the built-in ORM layer.

### How do I test if my RDAP server is compliant?
Use the IETF Reference RDAP Server's test suite or the APNIC RDAP Conformance Checker. You can also query the RDAP bootstrap file at `https://data.iana.org/rdap/` to verify your server is properly registered.

### Does RDAP support GDPR-style data redaction?
Yes. RFC 9082 (RDAP Response Profile) defines mechanisms for redacting personal data from RDAP responses. OpenRDAP implements these redaction rules, allowing you to configure which fields are hidden based on the requester's authentication level.

### Can I run an RDAP server without a database?
Yes. Both OpenRDAP and the Reference RDAP Server support file-based data sources. This is suitable for testing, small deployments, or environments where a database is not available. However, production deployments should use a database for performance and scalability.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted RDAP Servers: OpenRDAP, Reference RDAP & NIC.br RDAP (WHOIS Replacement Guide 2026)",
  "description": "Compare open-source RDAP server implementations for self-hosting WHOIS replacement services. Deployment guides for OpenRDAP, Reference RDAP, and NIC.br with Docker Compose configs.",
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
