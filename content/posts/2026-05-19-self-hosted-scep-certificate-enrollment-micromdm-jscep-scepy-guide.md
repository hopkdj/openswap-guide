---
title: "Self-Hosted SCEP Certificate Enrollment: micromdm/scep vs jscep vs SCEPy (2026)"
date: "2026-05-19"
tags: ["scep", "pki", "certificate-management", "mdm", "enrollment", "self-hosted", "security", "tls"]
draft: false
---

The Simple Certificate Enrollment Protocol (SCEP) automates certificate issuance for network devices, enabling routers, switches, IoT devices, and mobile endpoints to request and renew X.509 certificates without manual intervention. For organizations managing device fleets at scale, self-hosting a SCEP server eliminates dependency on cloud PKI providers while keeping certificate issuance under your control.

This guide compares three open-source SCEP server implementations: micromdm/scep (Go), jscep (Java), and SCEPy (Python).

## What is SCEP and Why Self-Host It?

SCEP (draft-nourse-scep, widely implemented as RFC 8894) defines a protocol for certificate enrollment over HTTP. Devices generate a key pair, create a PKCS#10 certificate signing request (CSR), and submit it to the SCEP server. The server validates the request, signs the certificate using its CA key, and returns it to the device.

### Why Self-Host Rather Than Use Cloud PKI?

**Data Sovereignty**: Certificate requests contain device identifiers and organizational information. Self-hosting ensures this metadata never leaves your infrastructure. For government, defense, and financial sectors, this is often a compliance requirement.

**Cost at Scale**: Cloud PKI providers charge per-certificate or per-device fees. A self-hosted SCEP server has no per-device costs — the only expense is the compute running the server.

**Offline Operation**: Devices in isolated networks (industrial control systems, air-gapped environments) need certificate enrollment without internet connectivity. A self-hosted SCEP server on the internal network satisfies this requirement.

**Integration Control**: Self-hosted SCEP servers can be integrated with existing LDAP directories, custom approval workflows, and internal monitoring systems without vendor API limitations.

## micromdm/scep

micromdm/scep is a Go-based SCEP server originally developed as part of the MicroMDM mobile device management platform. It has since been adopted as a standalone SCEP solution for general certificate enrollment.

### Architecture

The server is written in Go and runs as a lightweight HTTP service. It supports SCEP operations including GetCACert, GetCACaps, PKIOperation, and GetCert. The server can operate with a local file-based CA or integrate with external PKI infrastructure through its pluggable signer interface.

### Key Features

- **Lightweight**: Single binary with minimal dependencies, suitable for containerized deployment
- **Apple MDM Integration**: Originally designed for Apple device enrollment via MDM profiles
- **REST API**: Modern API for managing certificate requests and CA configuration
- **NDES Compatibility**: Compatible with Microsoft NDES (Network Device Enrollment Service) clients
- **Docker Support**: Official Docker image available for easy deployment

### Deployment with Docker Compose

```yaml
version: "3.8"
services:
  scep-server:
    image: micromdm/scep:latest
    container_name: scep-server
    command: ["scepserver", "-depot", "/depot", "-port", "8080"]
    ports:
      - "8080:8080"
    volumes:
      - scep-depot:/depot
      - ./ca.crt:/depot/ca.crt:ro
      - ./ca.key:/depot/ca.key:ro
    restart: unless-stopped
    networks:
      - scep-net

volumes:
  scep-depot:

networks:
  scep-net:
    driver: bridge
```

Generate a self-signed CA for testing:

```bash
# Create CA key pair
openssl req -x509 -newkey rsa:2048 -keyout ca.key   -out ca.crt -days 3650 -nodes   -subj "/CN=SCEP CA/O=Example Corp"

# Start the server
docker compose up -d

# Test with scepclient
docker run --rm --network scep-net micromdm/scep:latest   scepclient -server-url http://scep-server:8080/scep   -subject "CN=test-device,O=Example Corp"
```

### Strengths and Limitations

micromdm/scep excels in simplicity and deployment speed. The single-binary design means minimal operational overhead, and the Docker image makes it trivial to deploy in containerized environments. Apple MDM integration is unmatched among open-source SCEP servers.

The limitations include a feature set focused on Apple device enrollment — it lacks some enterprise SCEP features like challenge password validation against external directories, certificate template support, or detailed audit logging. The project's development pace has slowed since its initial release.

## jscep

jscep is a Java implementation of the SCEP protocol, providing both a client library and a server component. It implements the full SCEP specification and integrates well with existing Java PKI infrastructure.

### Architecture

jscep is built on the Bouncy Castle cryptographic library, providing comprehensive support for SCEP operations including message encryption, signing, and verification. The server component runs as a servlet within any Java application server (Tomcat, Jetty, WildFly).

### Key Features

- **Full SCEP Specification**: Implements all SCEP operations defined in the protocol draft
- **Bouncy Castle Integration**: Leverages the mature Bouncy Castle crypto library
- **Servlet-Based**: Deploys to any Java EE application server
- **PKCS#7/PKCS#10**: Full support for PKCS#7 message enveloping and PKCS#10 CSR processing
- **Extensible**: Plugin architecture for custom CA integration and approval workflows

### Deployment with Docker Compose

```yaml
version: "3.8"
services:
  jscep-server:
    image: tomcat:10-jdk17
    container_name: jscep-server
    ports:
      - "8080:8080"
    volumes:
      - ./jscep.war:/usr/local/tomcat/webapps/jscep.war:ro
      - ./ca-keystore:/etc/jscep/keystore:ro
    environment:
      - JSCEP_KEYSTORE_PATH=/etc/jscep/keystore
      - JSCEP_KEYSTORE_PASSWORD=changeit
      - JSCEP_CA_ALIAS=scep-ca
    restart: unless-stopped
    networks:
      - scep-net

  # Optional: PostgreSQL for audit logging
  jscep-db:
    image: postgres:16-alpine
    container_name: jscep-db
    environment:
      POSTGRES_DB: jscep
      POSTGRES_USER: jscep
      POSTGRES_PASSWORD: jscep-secret
    volumes:
      - jscep-db-data:/var/lib/postgresql/data
    networks:
      - scep-net

volumes:
  jscep-db-data:

networks:
  scep-net:
    driver: bridge
```

Build and deploy the WAR file:

```bash
# Clone and build
git clone https://github.com/seize-the-dave/jscep.git
cd jscep
mvn clean package -DskipTests

# Deploy to Tomcat
cp target/jscep.war /path/to/tomcat/webapps/

# Or use Docker
docker compose up -d
```

### Strengths and Limitations

jscep provides the most complete SCEP specification implementation among open-source options. Its Java architecture means it integrates naturally with existing enterprise Java infrastructure. The Bouncy Castle dependency provides robust cryptographic support including newer algorithms.

The main limitation is operational overhead — deploying a Java application server requires more resources and expertise than a single Go binary. The project also has limited documentation, and the servlet-based architecture may feel heavyweight for simple certificate enrollment needs.

## SCEPy

SCEPy is a Python implementation of a SCEP server, designed for simplicity and ease of use. It provides a straightforward SCEP server with minimal dependencies.

### Architecture

SCEPy is built with Python and uses the cryptography library for PKI operations. It provides a simple HTTP server that handles SCEP requests and returns certificates. The design prioritizes ease of understanding over enterprise feature completeness.

### Key Features

- **Python-Based**: Easy to read, modify, and extend
- **Minimal Dependencies**: Uses standard Python cryptography libraries
- **Simple Configuration**: File-based configuration with clear documentation
- **Quick Setup**: Can be running in minutes with pip install
- **Educational Value**: Clean codebase useful for understanding SCEP protocol internals

### Deployment with Docker Compose

```yaml
version: "3.8"
services:
  scepy-server:
    build:
      context: ./scepy
      dockerfile: Dockerfile
    container_name: scepy-server
    ports:
      - "8080:8080"
    volumes:
      - ./scepy-config:/etc/scepy:ro
      - ./ca-certificates:/etc/scepy/ca:ro
    environment:
      - SCEPY_CA_CERT=/etc/scepy/ca/ca.crt
      - SCEPY_CA_KEY=/etc/scepy/ca/ca.key
      - SCEPY_BIND=0.0.0.0:8080
    restart: unless-stopped
    networks:
      - scep-net

volumes:
  scep-config:

networks:
  scep-net:
    driver: bridge
```

Create a Dockerfile for SCEPy:

```dockerfile
FROM python:3.12-slim

WORKDIR /app
RUN pip install scepy cryptography

COPY config.py /etc/scepy/config.py
EXPOSE 8080

CMD ["python", "-m", "scepy.server", "--config", "/etc/scepy/config.py"]
```

### Strengths and Limitations

SCEPy is the easiest to understand and modify — ideal for organizations that need to customize SCEP behavior or integrate with custom PKI workflows. The Python codebase is accessible to a wide range of developers, and the minimal dependency footprint reduces supply chain risk.

The limitations are significant for production use: SCEPy has not seen active development since 2018, lacks some SCEP operations (like GetCACaps), and does not support challenge password validation or certificate revocation. It is best suited for lab environments, testing, or as a starting point for custom SCEP implementations.

## Comparison: SCEP Server Implementations

| Feature | micromdm/scep | jscep | SCEPy |
|---------|--------------|-------|-------|
| Language | Go | Java | Python |
| Last Active | 2026 | 2026 | 2018 |
| GitHub Stars | 380 | 131 | 31 |
| SCEP Spec Coverage | Partial | Full | Partial |
| Apple MDM Integration | Yes | No | No |
| Docker Image | Official | Community | Custom |
| Enterprise Features | Moderate | Strong | Minimal |
| Resource Footprint | Low (~20MB) | Medium (~200MB) | Low (~50MB) |
| Best For | Apple device enrollment | Enterprise Java PKI | Lab/testing, prototyping |

## Choosing the Right SCEP Server

For **Apple device management**, micromdm/scep is the clear choice. Its native integration with Apple MDM profiles and lightweight deployment make it ideal for organizations managing iPhones, iPads, and Macs at scale.

For **enterprise Java environments** with existing PKI infrastructure, jscep provides the most complete SCEP implementation. Its servlet-based architecture fits naturally into Java application server deployments.

For **testing, development, or learning**, SCEPy offers the simplest entry point. Its readable Python codebase makes it easy to understand SCEP protocol internals and prototype custom certificate enrollment workflows.

## Why Self-Host Certificate Enrollment?

Self-hosting SCEP infrastructure keeps certificate issuance entirely within your control. When devices request certificates from a cloud PKI provider, that provider knows every device identity in your organization — the types of hardware, the deployment patterns, and the scale of your operations. A self-hosted SCEP server eliminates this visibility.

For organizations with air-gapped networks or restricted internet access, self-hosted SCEP is the only option. Industrial control systems, military networks, and financial trading platforms often cannot reach external PKI services, yet still need automated certificate enrollment for secure device communication.

The operational cost of self-hosting is minimal — a SCEP server running in a container uses negligible resources compared to the value of automated, secure certificate issuance across hundreds or thousands of devices.

For certificate management automation, see our [cert-manager guide](../2026-04-19-cert-manager-vs-lego-vs-acme-sh-self-hosted-tls-certificate-automation-guide/). For SSH certificate workflows, check our [step-ca vs Teleport comparison](../2026-04-25-step-ca-vs-teleport-vs-vault-self-hosted-ssh-certificate-management-guide/). For enterprise PKI alternatives, our [EJBCA vs Dogtag guide](../2026-04-26-ejbca-vs-dogtag-pki-vs-openxpki-self-hosted-enterprise-ca-guide/) covers the options.

## Frequently Asked Questions

### What is SCEP used for?

SCEP automates X.509 certificate enrollment for network devices. Routers, switches, firewalls, IoT devices, and mobile endpoints use SCEP to request certificates from a CA without manual intervention. This enables automated TLS/SSL certificate deployment, VPN client authentication, and device identity verification.

### Is SCEP still relevant in 2026?

Yes, SCEP remains widely used, particularly in enterprise device management. While ACME (Automatic Certificate Management Environment) has gained traction for web server certificates, SCEP dominates in network device enrollment, Apple MDM, and legacy infrastructure where devices support SCEP but not ACME.

### How does SCEP differ from ACME?

ACME is designed for automated web server certificate issuance using domain validation. SCEP is designed for device certificate enrollment using pre-shared challenge passwords or certificate-based authentication. SCEP is better suited for non-web devices (routers, IoT) that cannot complete domain validation challenges.

### Can SCEP servers integrate with external CAs?

Yes. Both micromdm/scep and jscep support pluggable signer interfaces that can forward certificate requests to external CAs (Microsoft AD CS, EJBCA, or commercial CAs). The SCEP server acts as a proxy, handling the SCEP protocol while delegating signing to the external CA.

### What happens if a SCEP server goes down?

Devices with valid certificates continue to operate normally. However, new devices cannot enroll, and existing devices cannot renew expiring certificates. For production deployments, run multiple SCEP server instances behind a load balancer with shared CA key material.

### Is SCEP secure?

SCEP encrypts certificate requests using the CA's public key, protecting the CSR in transit. However, the original SCEP specification has known limitations — challenge passwords can be brute-forced if not properly protected. Modern deployments should use certificate-based authentication (where devices authenticate with an enrollment certificate) rather than static challenge passwords.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted SCEP Certificate Enrollment: micromdm/scep vs jscep vs SCEPy (2026)",
  "description": "Compare open-source SCEP certificate enrollment servers for self-hosted PKI — micromdm/scep (Go), jscep (Java), and SCEPy (Python) with Docker deployment.",
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
