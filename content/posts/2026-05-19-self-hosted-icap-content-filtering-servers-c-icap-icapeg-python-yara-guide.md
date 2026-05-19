---
title: "Best Self-Hosted ICAP Servers 2026: c-icap vs icapeg vs Python ICAP-YARA"
date: "2026-05-19"
tags: ["icap", "proxy", "content-filtering", "security", "squid"]
draft: false
---

The Internet Content Adaptation Protocol (ICAP) is an often-overlooked but powerful standard that enables content filtering, virus scanning, and traffic modification between HTTP proxies and specialized filtering servers. This guide compares three open-source ICAP server implementations — **c-icap**, **icapeg**, and **python-icap-yara** — for self-hosted content filtering deployments.

## What Is ICAP and Why Does It Matter?

ICAP (RFC 3507) defines a lightweight protocol that allows HTTP proxy servers like Squid to offload content inspection tasks to dedicated ICAP servers. Instead of the proxy performing resource-intensive scanning itself, it forwards content to an ICAP server via HTTP-like requests, which analyzes the content and returns modified content or an allow/deny decision.

Common ICAP use cases include:

- **Antivirus scanning** — scan downloaded files for malware before delivery
- **Content filtering** — block or modify web content based on policy rules
- **Data Loss Prevention (DLP)** — detect and block sensitive data in uploads
- **Ad injection/removal** — modify web pages in transit
- **URL categorization** — check URLs against blocklists before allowing access
- **YARA rule scanning** — match content against threat intelligence signatures

For organizations running self-hosted proxy infrastructure, deploying an ICAP server is essential for comprehensive content security.

## c-icap: The Reference ICAP Implementation

**GitHub:** [c-icap/c-icap-server](https://github.com/c-icap/c-icap-server) | **Stars:** 60+ | **Language:** C

c-icap is the reference implementation of the ICAP protocol, written in C for maximum performance. It is the most widely deployed open-source ICAP server and serves as the foundation for many commercial content filtering products.

### Key Features

- Full ICAP 1.0 protocol support (REQMOD and RESPMOD)
- Modular service architecture — write custom services in C
- ClamAV integration via c-icap-modules for virus scanning
- URL filtering and content categorization modules
- High-performance C implementation suitable for enterprise traffic volumes
- YARA scanning module available
- ICAP preview support (partial content inspection)
- Load balancing across multiple ICAP servers
- Comprehensive logging and statistics

### Docker Deployment

```yaml
version: "3.8"
services:
  c-icap:
    image: nkapashi/c_icapclamav:latest
    ports:
      - "1344:1344"
    volumes:
      - ./icap.conf:/etc/c-icap/c-icap.conf:ro
      - ./services:/etc/c-icap/services:ro
    environment:
      - CLAMAV_ENABLED=true
    restart: unless-stopped

  # Squid proxy configuration to use c-icap
  squid:
    image: ubuntu/squid:latest
    ports:
      - "3128:3128"
    volumes:
      - ./squid.conf:/etc/squid/squid.conf:ro
    depends_on:
      - c-icap
```

The corresponding Squid configuration to enable ICAP:

```
icap_enable on
icap_preview_enable on
icap_preview_size 1024

icap_service service_req reqmod_precache bypass=1 icap://c-icap:1344/avscan
icap_class class_service service_req
icap_access class_service allow all
```

## icapeg: Modern Go-Based ICAP Server

**GitHub:** [egirna/icapeg](https://github.com/egirna/icapeg) | **Stars:** 49+ | **Language:** Go

icapeg is a modern ICAP server written in Go, offering a more developer-friendly approach with built-in services for common content filtering tasks. It leverages Go's concurrency model for efficient handling of multiple simultaneous ICAP connections.

### Key Features

- Written in Go for modern concurrency and cross-platform deployment
- Built-in services: antivirus scanning, URL filtering, content adaptation
- VirusTotal integration for cloud-based malware checking
- Configurable service plugins
- REST API for service management
- Docker-native design with official container images
- Lightweight binary with minimal dependencies
- Support for both REQMOD and RESPMOD ICAP methods

### Docker Deployment

```yaml
version: "3.8"
services:
  icapeg:
    image: ghcr.io/egirna/icapeg:latest
    ports:
      - "1344:1344"
    volumes:
      - ./icapeg.yaml:/etc/icapeg/config.yaml:ro
    environment:
      - ICAP_SERVER_PORT=1344
      - VIRUSTOTAL_API_KEY=${VT_API_KEY}
    restart: unless-stopped
```

icapeg configuration file:

```yaml
server:
  host: "0.0.0.0"
  port: 1344

services:
  - name: "avscan"
    type: "clamav"
    clamav_host: "clamav"
    clamav_port: 3310

  - name: "urlfilter"
    type: "urlfilter"
    blocklist_url: "https://example.com/blocklist.txt"
```

## Python ICAP-YARA: Threat Detection with YARA Rules

**GitHub:** [RamadhanAmizudin/python-icap-yara](https://github.com/RamadhanAmizudin/python-icap-yara) | **Stars:** 58+ | **Language:** Python

python-icap-yara combines the ICAP protocol with YARA — the pattern matching Swiss knife used by malware researchers and security teams. This ICAP server inspects HTTP traffic content against YARA rules to detect known threats, suspicious patterns, and policy violations.

### Key Features

- YARA rule-based content inspection
- Real-time HTTP traffic scanning through ICAP
- Customizable YARA rule sets for organization-specific threats
- Simple Python-based architecture for easy customization
- Support for both REQMOD (request modification) and RESPMOD (response modification)
- Lightweight and easy to deploy
- Ideal for threat hunting and security monitoring
- Can be extended with custom Python-based detection logic

### Docker Deployment

```yaml
version: "3.8"
services:
  icap-yara:
    build: .
    ports:
      - "1344:1344"
    volumes:
      - ./rules:/opt/icap-yara/rules:ro
      - ./config.ini:/opt/icap-yara/config.ini:ro
    restart: unless-stopped
```

Dockerfile for the ICAP-YARA server:

```dockerfile
FROM python:3.11-slim

RUN pip install icapserver yara-python

WORKDIR /opt/icap-yara
COPY . .

EXPOSE 1344
CMD ["python", "icap_yara_server.py"]
```

## Comparison Table

| Feature | c-icap | icapeg | Python ICAP-YARA |
|---------|--------|--------|-------------------|
| **GitHub Stars** | 60+ | 49+ | 58+ |
| **Language** | C | Go | Python |
| **Protocol** | ICAP 1.0 | ICAP 1.0 | ICAP 1.0 |
| **REQMOD** | Yes | Yes | Yes |
| **RESPMOD** | Yes | Yes | Yes |
| **Antivirus** | ClamAV module | ClamAV/VirusTotal | YARA rules |
| **URL Filtering** | Yes | Yes | No |
| **Plugin System** | C modules | Go plugins | Python |
| **Preview** | Yes | Yes | Limited |
| **Performance** | Highest | High | Moderate |
| **Ease of Setup** | Moderate | Easy | Easy |
| **Best For** | Enterprise | Modern deployments | Threat detection |

## Choosing the Right ICAP Server

**c-icap** is the battle-tested choice for production environments. Its C implementation delivers maximum throughput, the modular architecture supports custom services, and the ClamAV integration provides ready-to-use antivirus scanning. If you need an ICAP server for enterprise Squid deployments, c-icap is the standard.

**icapeg** is ideal for teams that prefer Go-based tooling and want a modern, maintainable codebase. The VirusTotal integration adds cloud-based threat intelligence, and the YAML configuration makes it straightforward to manage. It is a great choice for greenfield deployments where performance requirements are moderate.

**Python ICAP-YARA** fills a specialized niche — organizations that need content inspection driven by YARA rules for custom threat detection. Security teams with existing YARA rule sets can deploy this ICAP server to scan all HTTP traffic through their proxy for known malware patterns, data exfiltration indicators, or policy violations.

## Why Self-Host Your Content Filtering?

Running your own ICAP server gives you complete visibility into the content flowing through your network. Cloud-based content filtering services process your traffic on third-party infrastructure, creating potential privacy concerns and dependency on external service availability.

Self-hosted ICAP servers keep all content inspection within your network perimeter. This means sensitive documents never leave your control, filtering rules are fully customizable to your organization's specific needs, and there is no risk of service outages from external providers affecting your content security.

For organizations with strict compliance requirements (HIPAA, GDPR, PCI-DSS), self-hosted content filtering ensures that data inspection happens entirely on-premises. You maintain full audit logs of all scanning activity and can tune detection rules without waiting for vendor updates.

For related content filtering, see our [SpamAssassin vs Rspamd vs Amavis guide](../2026-04-26-spamassassin-vs-rspamd-vs-amavis-self-hosted-spam-filtering-guide-2026/) for email-level filtering and [Squid CDN edge caching guide](../self-hosted-cdn-edge-caching-varnish-traffic-server-squid-nginx-guide/) for proxy infrastructure.

## FAQ

### What is ICAP used for in proxy servers?

ICAP (Internet Content Adaptation Protocol) allows HTTP proxies like Squid to offload content inspection tasks to dedicated servers. Common uses include antivirus scanning of downloaded files, URL filtering, content modification, data loss prevention, and malware detection. The proxy forwards content to the ICAP server, which analyzes it and returns the result.

### Is c-icap production-ready?

Yes, c-icap is the reference ICAP implementation and has been used in production environments for many years. It is deployed by ISPs, enterprises, and organizations worldwide as part of their Squid proxy infrastructure. The ClamAV integration module provides enterprise-grade virus scanning.

### Can I run multiple ICAP services simultaneously?

Yes, all three ICAP servers support multiple services. c-icap uses a modular service architecture where you can load multiple services (antivirus, URL filtering, content adaptation) simultaneously. icapeg supports multiple service definitions in its YAML configuration. Squid can also be configured to chain multiple ICAP services.

### Does ICAP add significant latency to web browsing?

ICAP adds minimal latency when properly configured. The ICAP preview feature allows the server to make allow/deny decisions based on the first 1KB of content without waiting for the full response. For large file downloads, async ICAP modes can scan in the background while content is streamed to the client.

### How do I integrate ICAP with Squid proxy?

Add the following to your squid.conf configuration file:
```
icap_enable on
icap_service service_req reqmod_precache bypass=1 icap://your-icap-server:1344/service_name
icap_class class_service service_req
icap_access class_service allow all
```
Then restart Squid. All HTTP traffic will now pass through the ICAP server for inspection.

### Can ICAP scan HTTPS traffic?

ICAP itself operates on decrypted content. To scan HTTPS traffic, you need to configure Squid with SSL bumping (SSL interception) to decrypt HTTPS connections, then forward the decrypted content to the ICAP server for inspection. This requires deploying your own CA certificate to client machines.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Best Self-Hosted ICAP Servers 2026: c-icap vs icapeg vs Python ICAP-YARA",
  "description": "Compare three open-source ICAP server implementations for self-hosted content filtering with Squid proxy.",
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
