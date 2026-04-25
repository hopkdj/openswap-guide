---
title: "DNSViz vs Zonemaster: Self-Hosted DNS Health Validation Guide 2026"
date: 2026-04-25
tags: ["comparison", "guide", "self-hosted", "dns", "dnssec", "validation"]
draft: false
description: "Compare DNSViz and Zonemaster for self-hosted DNS health validation. Learn how to deploy DNSSEC analysis, zone testing, and DNS troubleshooting tools with Docker in 2026."
---

When you run your own DNS infrastructure — whether it's authoritative name servers, recursive resolvers, or DNS-over-HTTPS endpoints — you need reliable tools to validate that everything works correctly. Misconfigured DNS can cause email delivery failures, broken websites, and security vulnerabilities. This guide compares two leading open-source DNS health validation platforms you can self-host: **DNSViz** and **Zonemaster**.

## Why Self-Host DNS Validation Tools

Public DNS testing services like [dnsviz.net](https://dnsviz.net) and the [Zonemaster public instance](https://zonemaster.net) are convenient, but self-hosting offers significant advantages for operators managing production DNS infrastructure:

- **Privacy**: Your zone data and DNS configuration details never leave your network. This is critical for internal domains, staging environments, or organizations with strict data governance policies.
- **Offline testing**: Validate DNS configurations for domains not yet publicly resolvable — essential during migrations or before cutover.
- **Custom nameservers**: Point validation tools at internal or split-horizon DNS servers that aren't reachable from the public internet.
- **Automation**: Integrate DNS validation into CI/CD pipelines, monitoring systems, and change management workflows.
- **No rate limits**: Run unlimited tests without hitting API quotas on public services.

For teams already managing self-hosted DNS servers (see our [PowerDNS vs BIND 9 guide](../2026-04-18-powerdns-vs-bind9-vs-nsd-vs-knot-self-hosted-authoritative-dns-2026/)), having local validation tools closes the operational loop between configuration and verification.

## DNSViz: DNSSEC Visualization and Analysis

**DNSViz** is a Python-based suite of tools for visualizing and analyzing DNSSEC authentication chains. Developed with support from the U.S. Department of Homeland Security, it provides both command-line utilities and a web interface for understanding DNSSEC deployment status.

| Attribute | Details |
|---|---|
| **GitHub** | [DNSViz/dnsviz](https://github.com/DNSViz/dnsviz) |
| **Stars** | 1,200+ |
| **Language** | Python |
| **Last Updated** | April 2025 |
| **License** | MIT |
| **Docker Support** | Official Dockerfile available |

### What DNSViz Does Well

DNSViz excels at **DNSSEC chain visualization**. It traces the complete trust chain from the root zone down to your domain, showing where validation succeeds or fails at each delegation point. The output includes:

- Graphical DNSSEC authentication chain diagrams (PNG/SVG)
- Detailed JSON reports of DNSKEY, DS, RRSIG, and NSEC/NSEC3 records
- Detection of common DNSSEC misconfigurations (missing DS records, expired signatures, algorithm mismatches)
- Support for CNAME, DNAME, and wildcard resolution analysis

The command-line tool `dnsviz probe` is particularly useful for scripting. It outputs structured JSON that can be parsed by monitoring systems or integrated into deployment pipelines.

### Installing DNSViz

#### Option 1: pip (Recommended)

```bash
pip3 install dnsviz
```

#### Option 2: From Source

```bash
git clone https://github.com/DNSViz/dnsviz.git
cd dnsviz
python3 setup.py build
python3 setup.py install
```

#### Option 3: Docker

DNSViz provides an official Dockerfile based on Alpine Linux. Here's a production-ready Docker Compose configuration:

```yaml
version: "3.8"

services:
  dnsviz:
    build:
      context: ./dnsviz
      dockerfile: Dockerfile
    volumes:
      - ./data:/data
    command: ["probe", "example.com"]
    restart: "no"
```

The DNSViz Dockerfile installs Python 3, Graphviz (for visualization), and BIND tools (for DNS lookups). The `/data` volume is used for output files.

### DNSViz Command Examples

```bash
# Basic DNSSEC probe with JSON output
dnsviz probe -f json example.com > dnsviz-report.json

# Generate a visual DNSSEC chain diagram
dnsviz grohl example.com | dnsviz print -T png -o chain.png

# Probe multiple domains from a file
dnsviz probe -d domains.txt -f json > batch-report.json

# Check DNSSEC for a specific record type
dnsviz probe -t A example.com
```

## Zonemaster: Comprehensive DNS Quality Testing

**Zonemaster** is a DNS quality testing framework originally developed by the Swedish Internet Foundation (.SE) and the French Internet Registry (AFNIC). It performs comprehensive checks across all DNS aspects — not just DNSSEC — including delegation, nameserver configuration, zone consistency, and compliance with RFC standards.

| Attribute | Details |
|---|---|
| **GitHub** | [zonemaster/zonemaster](https://github.com/zonemaster/zonemaster) |
| **Stars** | 527+ |
| **Language** | Perl |
| **Last Updated** | March 2026 |
| **License** | BSD-2-Clause |
| **Components** | Engine, Backend (API), WebGUI, CLI |

### What Zonemaster Does Well

Zonemaster takes a broader approach than DNSViz. Instead of focusing solely on DNSSEC, it runs **70+ individual tests** across multiple categories:

- **Delegation**: Checks parent/child zone consistency, NS records, glue records
- **Nameserver**: Verifies IP connectivity, software versions, open resolver status, EDNS support
- **Zone**: Validates SOA records, serial numbers, zone transfer settings
- **DNSSEC**: Tests signature validity, key rollover readiness, algorithm compliance
- **Consistency**: Compares responses across all authoritative nameservers
- **RFC Compliance**: Checks adherence to DNS standards and best practices

Each test produces a severity-tagged result (INFO, NOTICE, WARNING, ERROR, CRITICAL), making it easy to triage issues.

### Zonemaster Architecture

Zonemaster consists of four components:

1. **zonemaster-engine**: The Perl-based test execution engine
2. **zonemaster-backend**: REST API server (Mojolicious) that manages test queues
3. **zonemaster-webgui**: Web frontend for interactive testing
4. **zonemaster-cli**: Command-line interface

All components have individual Dockerfiles. For a full deployment, you'll need a PostgreSQL database for the backend.

### Deploying Zonemaster with Docker Compose

```yaml
version: "3.8"

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: zonemaster
      POSTGRES_USER: zonemaster
      POSTGRES_PASSWORD: zonemaster_secret
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U zonemaster"]
      interval: 10s
      retries: 5

  backend:
    image: zonemaster/zonemaster_backend:latest
    environment:
      ZONEMASTER_BACKEND_DB_DSN: "dbi:Pg:dbname=zonemaster;host=db;port=5432"
      ZONEMASTER_BACKEND_DB_USER: zonemaster
      ZONEMASTER_BACKEND_DB_PASSWORD: zonemaster_secret
      ZONEMASTER_BACKEND_CONFIGFILE: "/etc/zonemaster/backend_config.ini"
    ports:
      - "5000:5000"
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  webgui:
    image: zonemaster/zonemaster_webgui:latest
    environment:
      ZONEMASTER_BACKEND_ADDRESS: "http://backend:5000"
    ports:
      - "8080:80"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  pgdata:
```

After starting the services, access the web GUI at `http://localhost:8080` and submit domains for testing. The REST API is available at `http://localhost:5000`.

### Using the Zonemaster CLI

```bash
# Install the CLI
cpanm Zonemaster::CLI

# Run a full test suite
zonemaster-cli example.com

# Run specific test categories only
zonemaster-cli --level WARNING example.com

# Output as JSON for automation
zonemaster-cli --json example.com > zm-results.json

# Test with custom nameservers
zonemaster-cli --ns 8.8.8.8 example.com
```

## Feature Comparison: DNSViz vs Zonemaster

| Feature | DNSViz | Zonemaster |
|---|---|---|
| **Primary Focus** | DNSSEC chain visualization | Comprehensive DNS quality testing |
| **Test Categories** | DNSSEC, trust chain analysis | Delegation, NS, Zone, DNSSEC, Consistency, RFC |
| **Number of Tests** | ~20 DNSSEC-focused checks | 70+ tests across 6 categories |
| **Web Interface** | Yes (interactive graph visualization) | Yes (test submission and results) |
| **REST API** | No (CLI-focused) | Yes (Mojolicious-based) |
| **CI/CD Integration** | JSON output for parsing | API + CLI with JSON output |
| **DNSSEC Support** | Full chain visualization + analysis | RFC-compliant DNSSEC validation |
| **IPv6 Testing** | Yes | Yes |
| **EDNS Support Check** | Yes | Yes |
| **Database Backend** | None (file-based) | PostgreSQL required |
| **Language** | Python | Perl |
| **Docker Image** | Official Dockerfile | Official Docker Hub images |
| **Resource Requirements** | Low (single container) | Medium (3 containers + database) |
| **Learning Curve** | Low | Moderate |

## When to Use Which Tool

### Choose DNSViz When:

- **DNSSEC is your primary concern**: If you're deploying or troubleshooting DNSSEC, DNSViz's chain visualization is unmatched. It shows you exactly where the trust chain breaks.
- **You need graphical output**: The Graphviz-generated chain diagrams are excellent for documentation, audit reports, and presenting findings to stakeholders.
- **You want lightweight deployment**: DNSViz runs in a single container with no database dependency. It's quick to spin up for ad-hoc analysis.
- **You need JSON reports for automation**: The structured JSON output integrates cleanly with monitoring pipelines.

### Choose Zonemaster When:

- **You need comprehensive DNS testing**: Zonemaster covers far more ground than DNSSEC. If you want to verify delegation, nameserver consistency, zone configuration, and RFC compliance, Zonemaster is the better choice.
- **You run a DNS service for others**: If you operate authoritative DNS as a service, Zonemaster's severity-tagged results and test queuing system make it ideal for automated pre-deployment validation.
- **You need an API**: Zonemaster's REST API enables integration with ticketing systems, monitoring dashboards, and change management tools.
- **You want multi-language support**: Zonemaster's test messages are localized into multiple languages, useful for teams serving international audiences.

## Advanced: Combining Both Tools in a DNS Validation Pipeline

For complete DNS infrastructure validation, consider running both tools in sequence:

```bash
#!/bin/bash
# dns-validation-pipeline.sh
# Run Zonemaster for comprehensive checks, then DNSViz for DNSSEC deep-dive

DOMAIN="${1:-example.com}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="./dns-reports/${DOMAIN}/${TIMESTAMP}"
mkdir -p "${OUTPUT_DIR}"

echo "=== Running Zonemaster comprehensive DNS test ==="
zonemaster-cli --json "${DOMAIN}" > "${OUTPUT_DIR}/zonemaster.json"

echo "=== Running DNSViz DNSSEC analysis ==="
dnsviz probe -f json "${DOMAIN}" > "${OUTPUT_DIR}/dnsviz.json"
dnsviz grohl "${DOMAIN}" | dnsviz print -T png -o "${OUTPUT_DIR}/dnssec-chain.png"

echo "=== Generating summary ==="
# Count Zonemaster errors/warnings
zm_errors=$(python3 -c "
import json
data = json.load(open('${OUTPUT_DIR}/zonemaster.json'))
errors = [t for t in data if t.get('level') in ('ERROR', 'CRITICAL')]
print(len(errors))
")

echo "Zonemaster critical issues: ${zm_errors}"
echo "Reports saved to: ${OUTPUT_DIR}/"
```

This pipeline gives you Zonemaster's broad DNS health assessment plus DNSViz's detailed DNSSEC visualization for any domain.

## Lightweight Alternatives: CLI-Based DNS Validation

If you don't need a full web-based platform, several command-line tools provide essential DNS validation capabilities:

### `delv` (DNSSEC-Looking-Aside Validation)

Part of BIND 9, `delv` performs DNSSEC validation similar to `dig` but shows the validation process:

```bash
delv +multiline example.com A
delv +multiline +nodnssec example.com A  # Without validation for comparison
```

### `kdig` DNSSEC Queries

From the Knot DNS project, `kdig` provides enhanced DNSSEC query capabilities:

```bash
kdig +dnssec example.com SOA
kdig +dnssec +multiline example.com DNSKEY
```

### `dnssec-verify`

Part of ldns, this tool validates DNSSEC chains from the command line:

```bash
dnssec-verify -o example.com
```

These CLI tools are covered in detail in our [DNS benchmarking guide](../2026-04-24-dnsperf-vs-kdig-vs-queryperf-dns-benchmarking-guide-2026/) for performance testing use cases.

## FAQ

### What is the difference between DNSViz and Zonemaster?

DNSViz focuses specifically on DNSSEC authentication chain visualization and analysis, providing graphical representations of trust chains from root to leaf zones. Zonemaster is a broader DNS quality testing framework that checks 70+ aspects of DNS configuration including delegation, nameserver setup, zone consistency, DNSSEC, and RFC compliance. DNSViz is ideal for DNSSEC deep-dives; Zonemaster is better for comprehensive DNS health audits.

### Can I run DNSViz and Zonemaster offline for internal domains?

Yes. Both tools can be configured to query specific nameservers rather than relying on the public DNS hierarchy. DNSViz's `dnsviz probe` can target internal servers, and Zonemaster's backend can be configured with custom resolver settings. This makes them suitable for validating split-horizon DNS configurations and staging environments — see our [split-horizon DNS guide](../2026-04-24-self-hosted-split-horizon-dns-pihole-dnsmasq-coredns-bind9-guide-2026/) for related configuration patterns.

### Does DNSViz require a database?

No. DNSViz is file-based and stateless. Each probe runs independently and outputs results as JSON or visual diagrams. Zonemaster, on the other hand, requires PostgreSQL for its backend API to manage test queues and store results.

### Which tool is easier to deploy with Docker?

DNSViz is simpler — it requires a single container with no external dependencies. Zonemaster needs three containers (backend, webgui, and optionally the engine) plus a PostgreSQL database. For quick ad-hoc testing, DNSViz is faster to deploy. For ongoing production validation with an API and web interface, Zonemaster is worth the extra setup.

### Can I integrate these tools into CI/CD pipelines?

Both tools support automation. DNSViz outputs structured JSON that can be parsed by scripts to detect DNSSEC issues. Zonemaster provides both a CLI with JSON output and a REST API that can be called from pipeline scripts. For TLS/SSL validation in your pipeline, consider combining DNS validation with tools from our [TLS scanning guide](../2026-04-22-testssl-vs-sslyze-vs-sslscan-self-hosted-ssl-tls-scanning-guide-2026/).

### Do these tools support DNS-over-HTTPS (DoH) and DNS-over-TLS (DoT)?

DNSViz can analyze DNSSEC chains regardless of the transport protocol. Zonemaster's tests include EDNS and transport capability checks. For dedicated DoH server deployment and testing, see our [DoH server comparison](../2026-04-25-coredns-vs-dnsdist-vs-knot-resolver-self-hosted-doh-server-guide-2026/).

## Conclusion

Both DNSViz and Zonemaster are mature, production-ready tools for DNS health validation. **DNSViz** is the go-to choice when your primary concern is DNSSEC — its chain visualization is unparalleled in the open-source ecosystem. **Zonemaster** provides the most comprehensive DNS testing available, catching issues that DNSViz would never look for (delegation problems, nameserver inconsistencies, RFC violations).

For most self-hosted DNS operators, the ideal setup includes both: Zonemaster for routine comprehensive checks and DNSViz for DNSSEC-specific investigations. Both can be deployed with Docker and integrated into automated validation pipelines, ensuring your DNS infrastructure stays healthy and secure.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "DNSViz vs Zonemaster: Self-Hosted DNS Health Validation Guide 2026",
  "description": "Compare DNSViz and Zonemaster for self-hosted DNS health validation. Learn how to deploy DNSSEC analysis, zone testing, and DNS troubleshooting tools with Docker in 2026.",
  "datePublished": "2026-04-25",
  "dateModified": "2026-04-25",
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
