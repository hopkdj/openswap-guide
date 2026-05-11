---
title: "Self-Hosted Certificate Transparency Log Server Infrastructure: Trillian and CT Log Deployment Guide (2026)"
date: "2026-05-11"
tags: ["certificate-transparency", "tls", "pki", "security", "trillian", "infrastructure"]
draft: false
---

Certificate Transparency (CT) is an open framework for monitoring and auditing TLS certificate issuance. Every major browser requires certificates to be logged in publicly auditable CT logs before they are trusted. This public logging system creates a tamper-evident record of every certificate issued by participating certificate authorities, enabling domain owners and security researchers to detect misissued or fraudulent certificates in real time.

While most organizations rely on public CT logs operated by Google, Cloudflare, and DigiCert, running your own CT log infrastructure provides additional oversight, compliance capabilities, and research opportunities.

This guide covers self-hosted CT log server deployment using **Google Trillian**, the open-source framework that powers most public CT logs, along with alternatives for organizations that need private certificate auditing infrastructure.

## What Is a Certificate Transparency Log?

A CT log is an append-only, cryptographically verifiable data structure that records every TLS certificate issued for domains. When a Certificate Authority (CA) issues a certificate, it submits the certificate (or its pre-certificate) to one or more CT logs. The log returns a Signed Certificate Timestamp (SCT) that the CA includes in the final certificate.

Browsers verify that certificates contain valid SCTs from recognized CT logs. If a certificate appears in no log, the browser rejects it. This mechanism ensures that all publicly trusted certificates are publicly visible and auditable.

### Why Run Your Own CT Log?

- **Internal PKI auditing** — Log all certificates issued by your internal CA for compliance tracking and forensic analysis
- **Research and development** — Experiment with CT log protocols, Merkle tree structures, and signed tree head generation
- **Regulatory compliance** — Some industries require independent certificate logging beyond public CT logs
- **Certificate monitoring** — Detect unauthorized certificate issuance for your domains faster than relying on public log monitors
- **Infrastructure sovereignty** — Maintain complete control over the logging infrastructure without depending on third-party operators
- **Operational transparency** — Running your own CT log provides complete visibility into the logging pipeline. You can audit every certificate submission, monitor log signing operations, and verify Merkle tree integrity without relying on third-party transparency reports

## Google Trillian — CT Log Backend Framework

Trillian is an open-source, highly scalable, cryptographically verifiable data store developed by Google. It provides the backend storage layer used by most public CT logs, including Google own ct.googleapis.com logs.

GitHub: [google/trillian](https://github.com/google/trillian) (3,727 stars, active development)

### Architecture Components

Trillian consists of three main components that work together to provide verifiable logging:

1. **Log Server** — Handles certificate submission, Merkle tree construction, and Signed Certificate Timestamp (SCT) generation
2. **Log Signer** — Periodically signs the Merkle tree root to create Signed Tree Heads (STHs) that serve as verifiable checkpoints
3. **Storage Backend** — Typically MySQL or PostgreSQL for persistent storage of the Merkle tree data structure

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  trillian-mysql:
    image: mysql:8.0
    container_name: trillian-mysql
    environment:
      MYSQL_ROOT_PASSWORD: trillian-pass
      MYSQL_DATABASE: trillian_log
      MYSQL_USER: trillian
      MYSQL_PASSWORD: trillian-pass
    volumes:
      - mysql-data:/var/lib/mysql
    ports:
      - "3306:3306"
    restart: unless-stopped

  trillian-log-server:
    image: gcr.io/trillian-opensource-ci/log_server:latest
    container_name: trillian-log-server
    command:
      - "--storage_system=mysql"
      - "--mysql_uri=trillian:trillian-pass@tcp(trillian-mysql:3306)/trillian_log"
      - "--rpc_endpoint=0.0.0.0:8090"
      - "--http_endpoint=0.0.0.0:8091"
      - "--alsologtostderr"
    ports:
      - "8090:8090"
      - "8091:8091"
    depends_on:
      - trillian-mysql
    restart: unless-stopped

  trillian-log-signer:
    image: gcr.io/trillian-opensource-ci/log_signer:latest
    container_name: trillian-log-signer
    command:
      - "--storage_system=mysql"
      - "--mysql_uri=trillian:trillian-pass@tcp(trillian-mysql:3306)/trillian_log"
      - "--rpc_endpoint=0.0.0.0:8092"
      - "--http_endpoint=0.0.0.0:8093"
      - "--force_master"
      - "--alsologtostderr"
    depends_on:
      - trillian-mysql
    restart: unless-stopped

  ct-frontend:
    image: gcr.io/trillian-opensource-ci/ctfe:latest
    container_name: ct-frontend
    command:
      - "--log_config=/config/ctfe.json"
      - "--log_rpc_server=trillian-log-server:8090"
      - "--http_endpoint=0.0.0.0:6962"
      - "--alsologtostderr"
    volumes:
      - ./ctfe-config:/config
    ports:
      - "6962:6962"
    depends_on:
      - trillian-log-server
    restart: unless-stopped

volumes:
  mysql-data:
```

CT frontend configuration (ctfe.json):

```json
{
  "logConfigs": [
    {
      "prefix": "test-ct-log",
      "logId": "MDk3MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWYwMTIz",
      "rootsPemFile": ["/config/ca-cert.pem"],
      "rejectExpired": false,
      "issuanceRootsPemFile": ["/config/ca-cert.pem"]
    }
  ]
}
```

### Initializing and Testing the Log

```bash
# Create a new log tree
docker exec trillian-log-server   /create_tree.sh --storage_system=mysql   --mysql_uri=trillian:trillian-pass@tcp(localhost:3306)/trillian_log

# Submit a test certificate to the log
curl -X POST http://localhost:6962/test-ct-log/ct/v1/add-chain   -H "Content-Type: application/json"   -d '{"chain": ["BASE64_ENCODED_CERTIFICATE"]}'

# Retrieve the Signed Tree Head to verify log operation
curl http://localhost:6962/test-ct-log/ct/v1/get-sth
```

## Alternative CT Log Frameworks

While Trillian is the most widely used CT log backend, several alternative approaches exist for organizations with different requirements.

### Standalone Go CT Log Server

A lightweight standalone CT log server built on Go standard library implements the RFC 6962 CT log protocol and provides a REST API for certificate submission and retrieval. This is suitable for smaller deployments that do not need Trillian distributed architecture. The google/certificate-transparency-go repository (1,128 stars) provides the Go implementation of CT log protocols.

### ct_monitor Integration

SSLMate certspotter (1,141 stars) is a CT log monitor rather than a log server. It integrates with self-hosted Trillian logs to monitor certificate issuance for your domains. Deploy certspotter alongside your Trillian log to receive real-time alerts when certificates are issued for monitored domains. The ct_monitor tool from crtsh (454 stars) provides similar monitoring capabilities.

## Comparison: Self-Hosted CT Log Options

| Feature | Trillian | Go CT Log | ct_monitor |
|---------|----------|-----------|------------|
| **Type** | CT log backend framework | Standalone CT log server | CT log monitor |
| **Scalability** | High (distributed) | Medium (single-node) | N/A (client) |
| **Storage** | MySQL/PostgreSQL | SQLite/LevelDB | N/A |
| **RFC 6962 Compliant** | Yes | Yes | N/A |
| **SCT Generation** | Yes | Yes | N/A |
| **Web UI** | No | No | No |
| **Monitoring Integration** | Prometheus metrics | Built-in HTTP stats | Real-time alerts |
| **Docker Support** | Official images | Community | Community |
| **GitHub Stars** | 3,727 | 1,128 | 454 |
| **Best For** | Production-scale CT logging | Small-scale testing | Monitoring existing logs |

## Integrating CT Logs with Your PKI

A self-hosted CT log is most valuable when integrated with your existing PKI infrastructure. After deploying Trillian:

1. **Configure your internal CA** to submit all issued certificates to your CT log before signing
2. **Set up certificate monitors** like certspotter or ct_monitor to watch for unauthorized certificates
3. **Export Trillian metrics** to Prometheus for log health monitoring and alerting
4. **Configure log rotation** and backup procedures for the MySQL or PostgreSQL backend database
5. **Implement access controls** to restrict who can submit certificates and view the log contents

For comprehensive PKI management beyond CT logging, our guides on [self-hosted PKI and Certificate Authority](../2026-05-03-self-hosted-pki-certificate-authority-cfssl-step-ca-ejbca-guide/) and [EJBCA vs Dogtag PKI vs OpenXPKI](../2026-04-26-ejbca-vs-dogtag-pki-vs-openxpki-self-hosted-enterprise-ca-guide/) cover the full certificate lifecycle from issuance to revocation.

## Why Self-Host Certificate Transparency Infrastructure?

**Complete audit trail** — Public CT logs may take hours to propagate new entries to monitoring tools. A self-hosted log provides immediate visibility into every certificate your CA issues, enabling faster detection of misissuance or unauthorized certificates.

**Internal compliance** — Some regulatory frameworks require organizations to maintain independent records of all certificates issued for their domains. A self-hosted CT log serves as a tamper-evident audit trail that satisfies these requirements.

**No dependency on public logs** — Public CT log operators may change policies, experience outages, or discontinue service entirely. Self-hosted infrastructure ensures your certificate logging continues regardless of external factors beyond your control.

**Research and experimentation** — Trillian open-source design allows you to experiment with Merkle tree variants, custom signing algorithms, and novel CT log protocols. This is valuable for academic research and internal security tool development.

**Cost control** — While public CT logs are free to submit to, large-scale certificate monitoring through public APIs can incur rate limiting costs. Self-hosted infrastructure eliminates these constraints and gives you unlimited query access.

**Operational transparency** — Running your own CT log provides complete visibility into the logging pipeline. You can audit every certificate submission, monitor log signing operations, and verify Merkle tree integrity.

## FAQ

### What is the difference between a CT log and a CT monitor?

A CT log stores certificates and generates Signed Certificate Timestamps (SCTs). A CT monitor watches CT logs (both public and private) for certificates matching specific domains and alerts when new certificates are found. Trillian is a log backend framework; certspotter and ct_monitor are monitoring tools that watch existing logs.

### Can I use Trillian for purposes other than CT logs?

Yes. Trillian is a general-purpose verifiable data store. Beyond CT logs, it can back transparency logs for software supply chain verification using in-toto frameworks, certificate revocation lists, and any append-only data structure requiring cryptographic verification and auditing.

### How do I get my self-hosted CT log recognized by browsers?

Browser-recognized CT logs must meet strict requirements including auditability, geographic distribution, and operational transparency. Self-hosted logs are typically used for internal PKI auditing, not for browser-trusted certificates. For public trust, submit certificates to existing recognized logs like Google, Cloudflare, or DigiCert.

### What database does Trillian use for storage?

Trillian supports MySQL and PostgreSQL as storage backends. MySQL 8.0 or later is recommended for production deployments. The database stores Merkle tree nodes, leaf data, and signed tree heads. Plan for at least 100 GB of storage for a log handling thousands of certificates per day.

### How do I monitor Trillian log health and performance?

Trillian exposes Prometheus metrics on its HTTP endpoint (default port 8091 for log server, 8093 for signer). Key metrics include log_entries_added, signed_tree_heads, rpc_latency, and mysql_query_duration. Set up Grafana dashboards and alerts for abnormal latency or signing failures.

### Can I migrate from a public CT log to a self-hosted log?

You cannot migrate existing entries from public CT logs to your own infrastructure. However, you can configure your CA to submit to both public and self-hosted logs simultaneously through dual submission. This provides the benefits of public log recognition while maintaining your own independent audit trail.

### How often does the Trillian log signer create Signed Tree Heads?

By default, the log signer creates a new STH every few seconds when new entries are available for signing. The signing interval is configurable via the --signing_interval flag. More frequent signing provides faster consistency verification but increases computational overhead on the signing server.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Certificate Transparency Log Server Infrastructure: Trillian and CT Log Deployment Guide (2026)",
  "description": "Deploy self-hosted Certificate Transparency log infrastructure using Google Trillian. Complete Docker Compose guide for running your own CT log server.",
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
