---
title: "Self-Hosted Certificate Lifecycle Management: step-ca vs EJBCA vs Dogtag"
date: "2026-06-20"
tags: ["certificate-management", "pki", "tls", "security", "step-ca", "ejbca"]
draft: false
---

Certificate lifecycle management encompasses the full lifecycle of digital certificates: generation, signing, distribution, renewal, and revocation. As organizations adopt zero-trust architectures and internal TLS becomes mandatory, managing certificates at scale requires dedicated PKI infrastructure. This guide compares three open-source PKI solutions: **step-ca**, **EJBCA**, and **Dogtag**.

## Why Certificate Lifecycle Management Matters

Digital certificates expire. Without automated lifecycle management, expired certificates cause service outages, broken APIs, and security vulnerabilities. The 2024 CrowdStrike outage demonstrated how certificate-related failures can cascade across entire infrastructures.

A proper certificate lifecycle management system provides:
- **Automated renewal** before expiration
- **Centralized revocation** (CRL/OCSP) for compromised certificates
- **Policy enforcement** for certificate attributes (key size, validity period)
- **Audit logging** for compliance requirements
- **API-driven provisioning** for DevOps automation

## Feature Comparison

| Feature | step-ca | EJBCA | Dogtag |
|---------|---------|-------|--------|
| Primary Use Case | DevOps, zero-trust | Enterprise PKI | Government/Enterprise |
| Protocol Support | ACME, SCEP, SSH | ACME, SCEP, EST, CMP | ACME, SCEP, EST |
| Database Backend | SQLite, PostgreSQL | MySQL, PostgreSQL, Oracle | PostgreSQL |
| HSM Support | Limited | Yes (multiple vendors) | Yes |
| RA (Registration Authority) | Basic | Full RA framework | Full RA |
| SCEP Support | Yes | Yes | Yes |
| ACME Support | Yes (native) | Yes (via extension) | Yes (via extension) |
| SSH Certificate CA | Yes | No | No |
| Web UI | Minimal | Full-featured | Full-featured |
| GitHub Stars | ~4,800 | ~500 (Bitwise) | Community project |
| Complexity | Low | High | High |
| License | BSL/Apache 2.0 | LGPL | MPL |

## step-ca: Modern PKI for DevOps

step-ca by Smallstep is a lightweight, modern certificate authority designed for DevOps workflows. It provides ACME support, SSH certificate signing, and simple REST APIs that integrate naturally with CI/CD pipelines.

**Key features:**
- ACME protocol for automated certificate provisioning
- SSH certificate authority for host and user authentication
- mTLS bootstrapping for zero-trust service mesh
- Simple CLI and API for programmatic management
- Automatic renewal with step-agent
- Built-in CRL and OCSP responder

### Installation

```bash
# Install step CLI
curl -sSf https://smallstep.com/install | sh

# Download step-ca binary
wget https://github.com/smallstep/certificates/releases/latest/download/step-ca_linux_amd64.tar.gz
tar xzf step-ca_linux_amd64.tar.gz
sudo mv step-ca /usr/local/bin/
```

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  step-ca:
    image: smallstep/step-ca:latest
    container_name: step-ca
    ports:
      - "443:443"  # ACME endpoint
      - "9000:9000"  # Management API
    volumes:
      - ./step-config:/home/step:rw
      - ./certs:/home/step/certs:rw
    environment:
      - DOCKER_STEPCA_INIT_NAME=Internal-CA
      - DOCKER_STEPCA_INIT_DNS_NAMES=ca.internal,ca.example.com
      - DOCKER_STEPCA_INIT_ADDRESS=:443
    restart: unless-stopped
```

### Initialize and Configure

```bash
# Initialize the CA
step ca init \
  --name "Internal-CA" \
  --dns "ca.internal" \
  --address ":443" \
  --provisioner admin@example.com

# Issue a certificate via ACME
certbot certonly \
  --server https://ca.internal/acme/acme/directory \
  --standalone \
  -d service.example.com
```

## EJBCA: Enterprise-Grade PKI

EJBCA is one of the most widely deployed open-source PKI solutions, used by governments, financial institutions, and enterprises worldwide. It supports the full range of PKI operations including RA workflows, HSM integration, and compliance reporting.

**Key features:**
- Full RA (Registration Authority) framework
- Support for multiple HSM vendors (Thales, Utimaco, AWS CloudHSM)
- EST, SCEP, ACME, and CMP protocol support
- CRL and OCSP responders
- Certificate profiles with granular attribute control
- Audit logging and compliance reporting
- Multi-CA hierarchy support

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  ejbca:
    image: keyfactor/ejbca-ce:latest
    container_name: ejbca
    ports:
      - "8080:8080"
      - "8443:8443"
    environment:
      - TLS_SETUP_ENABLED=simple
      - EJBCA_SETUP_ENROLLMENT=true
    volumes:
      - ejbca-persistent:/ejbca_persistent
    restart: unless-stopped

volumes:
  ejbca-persistent:
```

### Database Configuration

```properties
# conf/database.properties
database.name=mysql
database.url=jdbc:mysql://mysql:3306/ejbca?characterEncoding=UTF-8
database.driver=com.mysql.cj.jdbc.Driver
database.username=ejbca
database.password=secure_password
```

## Dogtag: Government-Grade PKI

Dogtag Certificate System is the upstream project for Red Hat Certificate System. It provides a comprehensive PKI solution designed for government and enterprise environments with strict security requirements.

**Key features:**
- FIPS 140-2 compliance
- Full RA and CA hierarchy support
- Smart card and hardware token enrollment
- EST and SCEP protocol support
- Integration with FreeIPA/Identity Management
- SELinux policy enforcement
- Comprehensive audit logging

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  dogtag-ca:
    image: dogtagpki/pki-base:latest
    container_name: dogtag-ca
    ports:
      - "8080:8080"
      - "8443:8443"
    volumes:
      - ./pki-config:/etc/pki:rw
      - ./pki-data:/var/lib/pki:rw
    environment:
      - PKI_SUBSYSTEM=CA
      - PKI_SECURITY_DOMAIN_PASSWORD=secure_password
    restart: unless-stopped
```

### CA Configuration

```ini
# /etc/pki/ca/CS.cfg
pki_instance_name=ca
subsystem.type=CA
securitydomain.select=new
tomcat.server.port=8080
tomcat.ssl.port=8443

# CA signing configuration
ca.signing.dn=CN=Internal CA,O=Example,C=US
ca.signing.keytype=RSA
ca.signing.keysize=4096
```

## Choosing the Right PKI Solution

| Use Case | Recommended Solution |
|----------|---------------------|
| DevOps teams needing automated mTLS | step-ca |
| Zero-trust architecture with SSH certs | step-ca |
| Enterprise PKI with HSM integration | EJBCA |
| Government compliance (FIPS, Common Criteria) | Dogtag |
| ACME-based certificate automation | step-ca |
| Multi-CA hierarchy with RA delegation | EJBCA or Dogtag |
| Integration with FreeIPA/IdM | Dogtag |

## Why Self-Host Certificate Management?

Cloud-based certificate management services (DigiCert, Sectigo, Let's Enterprise) require trusting a third party with your private key infrastructure. For zero-trust architectures and internal mTLS, you need a private CA that issues certificates only for your internal services.

Self-hosted PKI also eliminates per-certificate licensing costs. Enterprise CA solutions often charge thousands of dollars annually per CA instance. Open-source alternatives like step-ca, EJBCA Community Edition, and Dogtag provide full functionality without licensing fees.

For TLS termination proxies, see our [SSL/TLS proxy guide](../2026-05-14-self-hosted-mtls-proxy-solutions-envoy-nginx-hitch-gui/). For certificate expiration monitoring, check our [x509 certificate monitoring guide](../2026-05-09-self-hosted-ssl-certificate-expiration-monitoring-x509/).

## FAQ

### What is the difference between a CA and a certificate management system?

A Certificate Authority (CA) signs certificates. A certificate management system (like EJBCA or Dogtag) provides the full lifecycle: CA operations, RA workflows, certificate enrollment protocols (ACME/SCEP/EST), revocation (CRL/OCSP), auditing, and web UI for administrators. step-ca combines CA and management into a single lightweight binary.

### Can step-ca replace Let's Encrypt for internal certificates?

Yes. step-ca provides an ACME endpoint compatible with certbot and other ACME clients. Unlike Let's Encrypt, step-ca issues certificates for internal domains (.internal, .local, private IPs) that Let's Encrypt cannot validate.

### How do I automate certificate renewal with step-ca?

Use the step-agent daemon for automatic renewal, or integrate ACME clients (certbot, lego, traefik) with step-ca's ACME endpoint. Certificates can be renewed 30 days before expiration automatically.

### Does EJBCA support ACME natively?

EJBCA Community Edition supports ACME through an extension module. EJBCA Enterprise has native ACME support. Configure the ACME module in the EJBCA admin UI and point your ACME client to the ACME endpoint URL.

### What is SCEP and when should I use it?

SCEP (Simple Certificate Enrollment Protocol) is used primarily for network device certificate enrollment (routers, switches, firewalls). All three solutions support SCEP. Use it when deploying certificates to devices that cannot run ACME clients.

### How do I handle certificate revocation?

All three solutions support CRL (Certificate Revocation List) and OCSP (Online Certificate Status Protocol). step-ca provides a built-in OCSP responder. EJBCA and Dogtag offer configurable CRL distribution points and OCSP responders. For immediate revocation, publish a delta CRL or update the OCSP response.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Certificate Lifecycle Management: step-ca vs EJBCA vs Dogtag",
  "description": "Compare three open-source PKI certificate lifecycle management solutions with Docker deployment and ACME configuration guides.",
  "datePublished": "2026-06-20",
  "dateModified": "2026-06-20",
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
