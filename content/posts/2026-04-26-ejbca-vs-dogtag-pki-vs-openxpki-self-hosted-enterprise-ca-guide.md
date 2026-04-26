---
title: "EJBCA vs Dogtag PKI vs OpenXPKI: Self-Hosted Enterprise CA Guide 2026"
date: 2026-04-26
tags: ["comparison", "guide", "self-hosted", "security", "pki", "certificate-authority"]
draft: false
description: "Compare EJBCA, Dogtag PKI, and OpenXPKI — three open-source enterprise certificate authority platforms for self-hosted PKI infrastructure."
---

Running your own certificate authority (CA) is essential for organizations that need full control over certificate issuance, lifecycle management, and cryptographic policy enforcement. While lightweight tools like [smallstep CA](https://smallstep.com/) work well for SSH certificates and web-scale TLS automation, enterprise environments demand more: certificate enrollment workflows, hardware security module (HSM) integration, compliance reporting, and granular policy control.

This guide compares three mature, open-source enterprise PKI platforms: **EJBCA**, **Dogtag PKI**, and **OpenXPKI**. Each provides a full-featured CA with web interfaces, REST APIs, and support for X.509 certificate lifecycle management.

## Why Self-Host an Enterprise Certificate Authority?

Third-party public CAs like Let's Encrypt, DigiCert, and GlobalSign issue certificates for public-facing TLS. But they cannot address internal infrastructure needs:

- **Internal TLS** — Services on private networks need certificates for mTLS, service mesh, and internal HTTPS
- **Client authentication** — Smart cards, VPNs, and Wi-Fi (802.1X) use client certificates for access control
- **Code signing** — Software publishers need code signing certificates tied to organizational identity
- **Document signing** — Legal and financial workflows require S/MIME and PDF signing certificates
- **Compliance** — Regulated industries (finance, healthcare, government) often mandate on-premises CA infrastructure
- **Cost at scale** — Issuing thousands of internal certificates annually is expensive with commercial CAs

Self-hosting an enterprise CA gives you full control over certificate policies, key lengths, validity periods, revocation handling, and audit trails — without per-certificate licensing fees.

## Quick Comparison

| Feature | EJBCA Community | Dogtag PKI | OpenXPKI |
|---------|----------------|------------|----------|
| **GitHub Stars** | 905 | 488 | 672 |
| **Last Updated** | Feb 2026 | Apr 2026 | Mar 2026 |
| **Language** | Java | Java | Perl |
| **License** | MPL 2.0 / LGPL | GPL-2.0 | Apache 2.0 / GPL |
| **Web UI** | Admin GUI + RA Web | Dogtag Console | OpenXPKI Client |
| **REST API** | Yes | Yes (partial) | Yes |
| **HSM Support** | Yes (PKCS#11) | Yes (PKCS#11) | Yes (PKCS#11) |
| **SCEP/EST** | Both | Both | SCEP |
| **Database** | MySQL, PostgreSQL, Oracle, H2 | PostgreSQL, SQLite | MySQL, MariaDB, PostgreSQL |
| **Docker Support** | Helm chart | Dockerfile | Official docker-compose |
| **OCSP Responder** | Built-in | Built-in | Built-in |
| **CRL Management** | Yes | Yes | Yes |
| **Certificate Profiles** | Yes (detailed) | Yes | Yes (workflow-based) |
| **Active Development** | Yes (Keyfactor) | Yes (Red Hat/Fedora) | Yes (community) |

## EJBCA Community Edition

[EJBCA](https://www.ejbca.org/) is the most widely deployed open-source CA, maintained by Keyfactor. The Community Edition provides the core CA functionality, while the Enterprise Edition adds premium features like advanced key archival and FIPS 140-2 compliance modules.

### Key Features

- **Full CA hierarchy** — Root CA, subordinate CA, and cross-certification support
- **Configurable certificate profiles** — Fine-grained control over extensions, key usage, and policy OIDs
- **Multiple enrollment protocols** — SCEP, EST, CMP, and custom enrollment workflows
- **Configdump** — Infrastructure-as-code approach: export/import entire CA configurations
- **Health check API** — REST endpoints for monitoring CA status
- **Modular architecture** — Pluggable crypto tokens, publishers, and custom validators

### Docker Deployment (via Helm)

EJBCA does not provide a standalone Docker Compose file but offers an official Helm chart for Kubernetes deployment. For Docker-based setups, you can use the community Docker images:

```yaml
# docker-compose.yml for EJBCA with MariaDB
version: "3.8"

services:
  mariadb:
    image: mariadb:10.11
    environment:
      MYSQL_ROOT_PASSWORD: ejbca-root-pass
      MYSQL_DATABASE: ejbcadb
      MYSQL_USER: ejbca
      MYSQL_PASSWORD: ejbca-db-pass
    volumes:
      - ejbca-db:/var/lib/mysql
    ports:
      - "3306:3306"

  ejbca:
    image: keyfactor/ejbca-ce:latest
    environment:
      DATABASE_JDBC_URL: "jdbc:mariadb://mariadb:3306/ejbcadb?characterEncoding=UTF-8"
      DATABASE_JDBC_USER: ejbca
      DATABASE_JDBC_PASS: ejbca-db-pass
      TLS_SETUP_ENABLED: "simple"
      LOG_LEVEL_APP: "INFO"
    ports:
      - "8080:8080"
      - "8443:8443"
    depends_on:
      - mariadb
    volumes:
      - ejbca-persistent:/mnt/persistent

volumes:
  ejbca-db:
  ejbca-persistent:
```

For production Kubernetes deployments, use the official Helm chart:

```bash
helm repo add keyfactor https://keyfactor.github.io/ejbca-community-helm/
helm install ejbca keyfactor/ejbca-community-helm \
  --set ejbca.useEphemeralH2Database=false \
  --set ejbca.env.DATABASE_JDBC_URL="jdbc:mariadb://mariadb:3306/ejbcadb"
```

### Installation on Ubuntu/Debian

```bash
# Install prerequisites
sudo apt update
sudo apt install -y openjdk-17-jdk mariadb-server ant git

# Clone the repository
git clone https://github.com/Keyfactor/ejbca-ce.git
cd ejbca-ce

# Configure database connection in conf/web.properties
# Build the application
ant clean deployear

# Deploy to application server (WildFly recommended)
# Start WildFly and deploy the EJBCA EAR file
```

## Dogtag PKI

[Dogtag PKI](https://www.dogtagpki.org/) is the upstream project for Red Hat Certificate System and Fedora Directory Server's certificate subsystem. It is an enterprise-class CA that supports the complete certificate lifecycle: issuance, renewal, revocation, and archival.

### Key Features

- **Subsystems architecture** — Separate subsystems for CA, KRA (Key Recovery Authority), OCSP, TKS (Token Key Service), and TPS (Token Processing System)
- **Red Hat ecosystem integration** — Native support for FreeIPA and Identity Management
- **Key archival and recovery** — Store and recover private keys for compliance
- **Smart card management** — Full lifecycle support for PKCS#11 tokens
- **LDAP-backed certificate store** — Certificates stored in a directory for fast lookup
- **ACME protocol support** — Automated certificate enrollment compatible with Let's Encrypt clients

### Docker Deployment

Dogtag provides an official Dockerfile based on Fedora. Here's a working Docker Compose setup:

```yaml
# docker-compose.yml for Dogtag PKI
version: "3.8"

services:
  dogtag-pki:
    build:
      context: .
      dockerfile: |
        FROM registry.fedoraproject.org/fedora:latest
        RUN dnf install -y dogtag-pki && dnf clean all
        CMD ["/usr/sbin/init"]
    container_name: dogtag-ca
    hostname: pki.example.com
    privileged: true
    ports:
      - "8080:8080"
      - "8443:8443"
    volumes:
      - pki-data:/var/lib/pki
      - pki-logs:/var/log/pki
    environment:
      - PKI_INSTANCE_NAME=dogtag-ca
      - PKI_SECURITY_DOMAIN_PASSWORD=Secret.123
      - PKI_ADMIN_PASSWORD=Secret.123
      - PKI_CLIENT_PKCS12_PASSWORD=Secret.123

volumes:
  pki-data:
  pki-logs:
```

### Installation on Fedora/RHEL

```bash
# Install Dogtag PKI on Fedora/RHEL
sudo dnf install -y dogtag-pki

# Run the setup wizard
sudo pkispawn -f /etc/pki/default.cfg

# Access the web console
# https://localhost:8443/ca/admin/ca/
```

## OpenXPKI

[OpenXPKI](https://www.openxpki.org/) is a Perl-based PKI platform with a strong focus on workflow-driven certificate lifecycle management. Unlike traditional CAs that center around certificate issuance, OpenXPKI treats the entire certificate process as a configurable workflow with states, actions, and audit trails.

### Key Features

- **Workflow engine** — Certificate requests go through configurable workflows with approval steps, notifications, and state transitions
- **Role-based access control** — Fine-grained permissions for certificate operators, auditors, and end users
- **Multi-tenant support** — Run multiple independent PKI realms on a single instance
- **Real-time monitoring** — Dashboard with certificate expiry tracking, queue status, and audit logs
- **SCIM integration** — User management via standardized SCIM protocol
- **Plug-and-play configuration** — Clone the sample configuration repository for quick customization

### Docker Deployment

OpenXPKI provides an official Docker Compose setup in the [openxpki-docker](https://github.com/openxpki/openxpki-docker) repository:

```yaml
# docker-compose.yml for OpenXPKI (from official repo)
version: "3"

services:
  db:
    image: mariadb:10
    command: --default-authentication-plugin=mysql_native_password
    volumes:
      - openxpkidb:/var/lib/mysql
      - openxpkidbsocket:/var/run/mysqld/
      - ./openxpki-config/contrib/sql/schema-mysql.sql:/docker-entrypoint-initdb.d/schema-mysql.sql
    environment:
      MYSQL_DATABASE: openxpki
      MYSQL_USER: openxpki
      MYSQL_PASSWORD: openxpki
      MYSQL_ROOT_PASSWORD: topsecret

  openxpki-server:
    image: whiterabbitsecurity/openxpki3
    command: /usr/bin/openxpkictl start --no-detach
    volumes:
      - ./openxpki-config:/etc/openxpki
      - openxpkilog:/var/log/openxpki
      - openxpkisocket:/var/openxpki/
      - openxpkidbsocket:/var/run/mysqld/
    depends_on:
      - db

  openxpki-client:
    image: whiterabbitsecurity/openxpki3
    command: /usr/bin/start-apache
    ports:
      - "8080:80/tcp"
      - "8443:443/tcp"
    volumes:
      - ./openxpki-config:/etc/openxpki
      - openxpkilog:/var/log/openxpki
      - openxpkisocket:/var/openxpki/
      - openxpkidbsocket:/var/run/mysqld/
    depends_on:
      - openxpki-server

volumes:
  openxpkidb:
  openxpkisocket:
  openxpkidbsocket:
  openxpkilog:
```

### Installation from Source

```bash
# Install prerequisites
sudo apt install -y perl libdbd-mysql-perl libapache2-mod-perl2 \
  mariadb-server make git

# Clone the repository
git clone https://github.com/openxpki/openxpki.git
cd openxpki

# Build and install
perl Makefile.PL
make
sudo make install

# Configure database and Apache, then start the server
sudo systemctl start openxpki
```

## When to Choose Which Platform

### Choose EJBCA if:

- You need the most mature and widely deployed open-source CA
- Your team is comfortable with Java/WildFly application servers
- You require Configdump for infrastructure-as-code CA management
- You need comprehensive SCEP + EST + CMP enrollment protocol support
- You want official Kubernetes/Helm deployment support
- Enterprise support from Keyfactor is an option for production

### Choose Dogtag PKI if:

- You are running Red Hat Enterprise Linux, Fedora, or FreeIPA
- You need key archival and recovery capabilities (KRA subsystem)
- Smart card lifecycle management is a requirement
- You want native ACME protocol support for automated TLS enrollment
- You prefer a Red Hat-backed project with long-term stability

### Choose OpenXPKI if:

- You need a workflow-driven approach with multi-step approval processes
- Multi-tenant PKI (isolated realms) is required
- You prefer Perl-based tools and MySQL/MariaDB infrastructure
- You want plug-and-play configuration management via Git-cloned config repos
- You need fine-grained role-based access control for certificate operations

## Security Best Practices for Self-Hosted CAs

1. **Isolate the root CA** — Keep your root CA offline. Only use it to sign intermediate/subordinate CA certificates
2. **Use HSMs** — Hardware Security Modules protect private keys from software extraction
3. **Short-lived certificates** — Reduce risk by limiting certificate validity to 90 days or less
4. **Monitor CRL/OCSP** — Ensure revocation information is always accessible to relying parties
5. **Audit logging** — Enable comprehensive logging of all CA operations for compliance
6. **Network segmentation** — Place CA servers in a management VLAN with strict firewall rules
7. **Backup key material** — Regularly back up CA keys, certificates, and databases to secure offline storage

For related reading, see our [cert-manager vs Lego vs ACME.sh TLS automation guide](../2026-04-19-cert-manager-vs-lego-vs-acme-sh-self-hosted-tls-certificate-automation-guide-2026/) and [complete mTLS configuration guide](../2026-04-24-self-hosted-mutual-tls-mtls-nginx-caddy-traefik-envoy-guide-2026/) for implementing certificate-based authentication in your infrastructure.

## FAQ

### What is the difference between EJBCA Community and Enterprise editions?

EJBCA Community Edition provides the core certificate authority functionality including certificate issuance, revocation, OCSP, and SCEP/EST enrollment. The Enterprise Edition adds advanced features like automated key archival and recovery, FIPS 140-2 validated crypto modules, advanced health monitoring, and commercial support from Keyfactor. For most self-hosted use cases, the Community Edition is sufficient.

### Can I use EJBCA with a Docker Compose setup instead of Kubernetes?

Yes. While EJBCA's official deployment method is via Helm charts for Kubernetes, you can run it with Docker Compose using community-maintained images. The docker-compose configuration requires a MariaDB or PostgreSQL database and an application server (WildFly). For production use, the Helm chart approach is recommended for proper scaling and high availability.

### Does Dogtag PKI work on non-Red Hat distributions?

Dogtag PKI is primarily developed and tested on Fedora and Red Hat Enterprise Linux. While it can be built on other distributions, the installation process is significantly more complex. The Docker image approach (using a Fedora base) works on any host OS that supports Docker, making it the most portable option for non-RHEL environments.

### What databases are supported by each platform?

EJBCA supports MySQL/MariaDB, PostgreSQL, Oracle, and H2 (embedded, for testing only). Dogtag PKI uses embedded databases by default but can be configured with external LDAP/PostgreSQL backends. OpenXPKI supports MySQL, MariaDB, PostgreSQL, and SQLite. For production deployments, always use an external database server rather than embedded options.

### How do I set up OCSP responders with these platforms?

All three platforms include built-in OCSP responders. In EJBCA, the OCSP responder runs as a separate web application on the same application server. In Dogtag PKI, the OCSP subsystem is a separate service that can run on a different host. In OpenXPKI, OCSP responses are generated by the server process and can be served via Apache or directly through the OpenXPKI daemon. For high-availability setups, deploy multiple OCSP responders behind a load balancer.

### Can these platforms integrate with existing Active Directory or LDAP?

Yes. EJBCA can publish certificates to LDAP/Active Directory and use LDAP for certificate holder lookup. Dogtag PKI has deep LDAP integration since it was designed to work with FreeIPA/389 Directory Server. OpenXPKI can use LDAP as a certificate publisher and for user authentication. All three support PKCS#11 for HSM integration with hardware-backed key storage.

### What is the difference between these enterprise CAs and smallstep CA?

smallstep CA is a lightweight, modern CA focused on SSH certificates and short-lived TLS certificates with simple configuration. EJBCA, Dogtag PKI, and OpenXPKI are enterprise-grade platforms with full certificate lifecycle management, compliance reporting, workflow engines, HSM support, and multi-tenant capabilities. Choose smallstep CA for simple, automated certificate issuance. Choose an enterprise CA when you need granular policy control, approval workflows, compliance auditing, and complex certificate types (S/MIME, code signing, smart cards).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "EJBCA vs Dogtag PKI vs OpenXPKI: Self-Hosted Enterprise CA Guide 2026",
  "description": "Compare EJBCA, Dogtag PKI, and OpenXPKI — three open-source enterprise certificate authority platforms for self-hosted PKI infrastructure.",
  "datePublished": "2026-04-26",
  "dateModified": "2026-04-26",
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
