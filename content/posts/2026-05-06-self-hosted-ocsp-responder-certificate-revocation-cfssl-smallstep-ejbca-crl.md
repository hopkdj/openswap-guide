---
title: "Self-Hosted OCSP Responder & Certificate Revocation: CFSSL vs Smallstep vs EJBCA CRL"
date: "2026-05-06"
tags: ["pki", "certificate-authority", "ocsp", "crl", "tls", "cfssl", "smallstep", "ejbca", "security", "revocation"]
draft: false
---

Certificate revocation is one of the most overlooked aspects of self-hosted PKI infrastructure. When a TLS certificate is compromised, expired, or issued in error, the certificate authority must provide a mechanism for clients to verify that the certificate is no longer trusted. Without proper revocation checking, compromised certificates remain valid until their natural expiration date — potentially months or years.

The two standard revocation mechanisms are **OCSP (Online Certificate Status Protocol)**, which provides real-time certificate status checks, and **CRL (Certificate Revocation List)**, which publishes a periodically-updated list of revoked certificates. This guide compares three self-hosted solutions for certificate revocation: **Cloudflare CFSSL**, **Smallstep Certificates**, and **EJBCA**.

## Understanding Certificate Revocation

Before comparing tools, it helps to understand the revocation landscape:

### OCSP (Online Certificate Status Protocol)

OCSP allows a client (browser, API client, or service) to query an OCSP responder about the status of a specific certificate. The responder returns one of three statuses: `good` (certificate is valid), `revoked` (certificate has been revoked), or `unknown` (responder does not know about this certificate).

OCSP provides near-instantaneous revocation status but introduces a dependency on the OCSP responder's availability. If the responder is down, clients may reject valid certificates (hard fail) or accept potentially revoked ones (soft fail).

### OCSP Stapling

OCSP stapling solves the availability problem by having the TLS server fetch its own OCSP response from the responder and include (staple) it in the TLS handshake. Clients verify the stapled response without contacting the OCSP responder directly. This eliminates the OCSP dependency for end users and improves TLS handshake performance.

### CRL (Certificate Revocation List)

A CRL is a signed list of revoked certificate serial numbers published by the CA at regular intervals. Clients download the CRL from a distribution point (CDP) and check whether a certificate's serial number appears on the list. CRLs are simpler to implement than OCSP but can grow very large for active CAs, and revocation status is only as current as the last CRL publication.

### CRL Distribution Points (CDP)

CRL Distribution Points are URLs embedded in certificates that tell clients where to download the CRL. A properly configured CA publishes CRLs at a stable HTTP(S) URL that is accessible to all certificate users.

## CFSSL OCSP Responder

CFSSL (Cloudflare's PKI toolkit) includes an OCSP responder that serves revocation status for certificates issued by a CFSSL CA. It is a lightweight, purpose-built component designed for environments where CFSSL is the primary certificate authority.

### Architecture

CFSSL's OCSP responder works by reading revocation entries from a database (SQLite, MySQL, or PostgreSQL) and serving OCSP responses via HTTP. When a certificate is revoked through the CFSSL API, the revocation is recorded in the database and immediately reflected in OCSP responses.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  cfssl:
    image: cloudflare/cfssl:latest
    container_name: cfssl
    command: serve -address=0.0.0.0 -port=8888 -ca=/etc/cfssl/ca.pem -ca-key=/etc/cfssl/ca-key.pem
    ports:
      - "8888:8888"
    volumes:
      - ./cfssl-config:/etc/cfssl

  cfssl-ocsp:
    image: cloudflare/cfssl:latest
    container_name: cfssl-ocsp
    command: ocspserve -address=0.0.0.0 -port=8889 -responses=/etc/cfssl/responses
    ports:
      - "8889:8889"
    volumes:
      - ./cfssl-config:/etc/cfssl
    depends_on:
      - cfssl
```

### OCSP Responder Configuration

```bash
# Initialize the OCSP database
cfssl ocsp-init -ca ca.pem -responder-key responder-key.pem \
  -db-config '{"driver":"sqlite3","data_source":"ocsp.db"}'

# Revoke a certificate
cfssl revoke -ca ca.pem -ca-key ca-key.pem \
  -serial 1234567890 -reason "keyCompromise" \
  -db-config '{"driver":"sqlite3","data_source":"ocsp.db"}'

# Generate OCSP response for a revoked certificate
cfssl ocspsign -ca ca.pem -responder-key responder-key.pem \
  -cert revoked-cert.pem -status revoked -reason keyCompromise \
  -db-config '{"driver":"sqlite3","data_source":"ocsp.db"}'
```

For production, configure the responder with a proper database backend and set up response caching to handle high query volumes.

### Strengths

- Lightweight and fast — single binary, minimal resource usage
- Integrates seamlessly with CFSSL CA for certificate issuance
- SQLite, MySQL, and PostgreSQL database backends supported
- API-driven revocation — revoke certificates programmatically
- Open source under BSD license
- Small attack surface — focused on OCSP only

### Limitations

- OCSP only — no CRL generation or distribution
- Requires separate CFSSL CA for certificate issuance
- Limited to certificates issued by the associated CA
- No web UI — all operations via CLI or REST API
- No OCSP stapling support — clients must contact the responder directly
- No enterprise features (HSM integration, RBAC, audit logging)

## Smallstep Certificates

Smallstep Certificates is a modern, open-source certificate authority that includes built-in OCSP responder functionality. It supports X.509 and SSH certificates with ACME protocol compatibility, making it suitable for both traditional PKI and modern automation workflows.

### Architecture

Smallstep operates as a single binary that serves as CA, OCSP responder, and ACME server. The OCSP responder is integrated into the CA itself — when a certificate is revoked, the revocation is immediately reflected in OCSP responses without requiring a separate service.

Smallstep stores certificate and revocation data in a local database (BoltDB by default, with PostgreSQL support for production deployments).

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  step-ca:
    image: smallstep/step-ca:latest
    container_name: step-ca
    command: step-ca /home/step/config
    environment:
      - DOCKER_STEPCA_INIT_NAME=My Internal CA
      - DOCKER_STEPCA_INIT_DNS_NAMES=ca.internal,localhost
      - DOCKER_STEPCA_INIT_ADDRESS=:9000
      - DOCKER_STEPCA_INIT_PASSWORD=change-me-in-production
    ports:
      - "9000:9000"
      - "8888:8888"
    volumes:
      - step-data:/home/step

  nginx-ocsp:
    image: nginx:alpine
    container_name: nginx-ocsp
    volumes:
      - ./nginx-ocsp.conf:/etc/nginx/conf.d/default.conf
      - ./ocsp-responses:/var/www/ocsp
    ports:
      - "8080:80"

volumes:
  step-data:
```

### Certificate Revocation with Smallstep

```bash
# Initialize the CA (first run)
step ca init --name "Internal CA" --dns "ca.internal" \
  --address ":9000" --provisioner admin

# Revoke a certificate
step certificate revoke server.crt \
  --reason "keyCompromise" \
  --cert ca.crt --key ca.key

# Check certificate status via OCSP
step certificate status server.crt \
  --issuer ca.crt

# Configure OCSP stapling in nginx
# nginx.conf
ssl_stapling on;
ssl_stapling_verify on;
ssl_trusted_certificate /etc/ssl/ca-chain.pem;
resolver 8.8.8.8 valid=300s;
resolver_timeout 5s;
```

Smallstep's `step certificate revoke` command records the revocation in the CA database and updates the OCSP responder state. Clients can verify revocation status through OCSP queries or by checking the CA's API.

### Strengths

- Integrated CA + OCSP responder in a single binary
- ACME protocol support for automated certificate management
- SSH certificate support in addition to X.509
- Modern API with JWT-based authentication
- Simple CLI tooling for all PKI operations
- Active development with regular releases
- Open source under Apache 2.0 license

### Limitations

- OCSP responses are served by the CA itself (no separate responder service)
- No CRL generation or distribution
- Limited to certificates issued by the Smallstep CA
- BoltDB backend may not scale for very large CAs (>100K certificates)
- No enterprise HSM integration in the open-source version
- OCSP responder URL must be configured in issued certificates

## EJBCA CRL Distribution

EJBCA (Enterprise Java Beans Certificate Authority) is an enterprise-grade PKI solution that supports both OCSP and CRL distribution. It is the most feature-rich option in this comparison, with support for complex certificate hierarchies, HSM integration, and comprehensive audit logging.

### Architecture

EJBCA is a Java-based application that runs on an application server (WildFly or JBoss). It provides:

- Certificate authority with multi-level CA hierarchy
- OCSP responder (built-in, configurable)
- CRL generation and distribution via HTTP/LDAP
- Certificate enrollment via web UI, SCEP, EST, and ACME
- Role-based access control and audit logging
- HSM integration (PKCS#11)

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  ejbca:
    image: keyfactor/ejbca-ce:8.6.0
    container_name: ejbca
    environment:
      - EJBCA_SAMPLE_DATA=false
      - TLS_SETUP_ENABLED=simple
      - LOG_LEVEL=INFO
    ports:
      - "8080:8080"
      - "8443:8443"
    volumes:
      - ejbca-data:/etc/ejbca
      - ejbca-persistent:/persistent

  postgres:
    image: postgres:16
    container_name: ejbca-db
    environment:
      - POSTGRES_PASSWORD=ejbca-password
      - POSTGRES_DB=ejbca
    volumes:
      - pg-data:/var/lib/postgresql/data

volumes:
  ejbca-data:
  ejbca-persistent:
  pg-data:
```

### CRL Configuration in EJBCA

```bash
# Access the EJBCA admin interface at https://localhost:8443/ejbca/adminweb

# Configure CRL generation:
# 1. Create a Certificate Profile with CDP (CRL Distribution Point)
# 2. Create a CA with CRL settings:
#    - CRL Period: 24 hours
#    - CRL Issue Interval: 24 hours
#    - Delta CRL Period: 1 hour
#    - CRL Publish: Enable HTTP and/or LDAP

# Revoke a certificate via CLI:
ejbca.sh ra revoke --certserial 1234567890ABCDEF \
  --reason keyCompromise --comment "Compromised key"

# Force CRL generation:
ejbca.sh ca createcrl <CA_NAME>

# Check CRL via HTTP:
curl http://localhost:8080/ejbca/publicweb/webdist/certdist?cmd=crl&issuer=CN%3DInternal%20CA
```

EJBCA publishes CRLs to configured distribution points automatically. The CRL is signed by the CA and can be downloaded by clients at the CDP URL embedded in certificates.

### Strengths

- Enterprise-grade PKI with full certificate lifecycle management
- Both OCSP and CRL support (dual revocation mechanisms)
- CRL generation with delta CRLs for efficient updates
- Multi-level CA hierarchy (root CA, intermediate CAs)
- HSM integration for key protection
- Web UI for certificate management
- SCEP, EST, and ACME enrollment protocols
- Comprehensive audit logging
- Active open-source community edition available

### Limitations

- Heavy resource requirements (2-4GB RAM for WildFly + EJBCA)
- Complex setup compared to CFSSL and Smallstep
- Java-based — larger attack surface and longer startup times
- CRL files can grow very large for active CAs
- OCSP responder performance depends on database backend
- Enterprise features (some) locked behind commercial edition

## Comparison: Certificate Revocation Systems

| Feature | CFSSL OCSP | Smallstep Certificates | EJBCA |
|---------|-----------|------------------------|-------|
| Revocation type | OCSP only | OCSP only | OCSP + CRL |
| CRL generation | No | No | Yes (full + delta) |
| Certificate authority | CFSSL CA required | Built-in | Built-in |
| ACME support | No | Yes | Yes (CE edition) |
| Web UI | No | No | Yes (admin + public) |
| HSM integration | No | No (commercial only) | Yes (PKCS#11) |
| Database | SQLite/MySQL/PostgreSQL | BoltDB/PostgreSQL | PostgreSQL/MySQL |
| Resource usage | ~50MB RAM | ~100MB RAM | 2-4GB RAM |
| Setup complexity | Low | Low | High |
| Audit logging | No | Basic | Comprehensive |
| License | BSD | Apache 2.0 | MPL 2.0 (CE) |
| SSH certificates | No | Yes | No |
| Multi-level CA | Limited | Yes | Full hierarchy |

## Why Self-Host Certificate Revocation?

Running your own OCSP responder and CRL distribution infrastructure is essential for any self-hosted PKI. Public CAs like Let's Encrypt provide revocation for their certificates, but internal PKI systems need their own revocation infrastructure. Without it, revoked certificates remain valid until expiration, creating a security gap.

For organizations with internal services using mutual TLS (mTLS), certificate revocation is a critical security control. When an employee leaves or a service key is compromised, the certificate must be revoked immediately so that it cannot be used to access internal services.

Self-hosted revocation also gives you control over revocation policy. You decide how quickly OCSP responses reflect revocations, how often CRLs are published, and what happens when the OCSP responder is unavailable.

For related reading, see our [PKI certificate authority comparison](../2026-05-03-self-hosted-pki-certificate-authority-cfssl-step-ca-ejbca-guide/) and our [enterprise CA deployment guide](../2026-04-26-ejbca-vs-dogtag-pki-vs-openxpki-self-hosted-enterprise-ca-guide/). Setting up the CA is just the first step — revocation infrastructure completes the PKI picture.

## FAQ

### What is the difference between OCSP and CRL?

OCSP provides real-time certificate status checking — a client queries the OCSP responder and gets an immediate `good`, `revoked`, or `unknown` response for a specific certificate. CRL is a periodically-published list of all revoked certificate serial numbers. OCSP is more current but requires the responder to be available. CRL is simpler to implement but can grow very large and is only as current as the last publication.

### Is OCSP stapling necessary?

OCSP stapling is strongly recommended for any production TLS deployment. Without stapling, each client must contact the OCSP responder during the TLS handshake, which adds latency and creates a privacy concern (the OCSP responder learns which sites the client is visiting). With stapling, the server fetches its own OCSP response and includes it in the handshake, eliminating both the latency and privacy issues. Most modern web servers (nginx, Apache, Caddy) support OCSP stapling.

### How often should CRLs be published?

The CRL publication interval depends on your security requirements. For most internal PKI deployments, a 24-hour publication interval is sufficient. For high-security environments, consider publishing CRLs every 1-4 hours and using delta CRLs between full publications. Delta CRLs contain only the revocations since the last full CRL, reducing download size.

### What happens when the OCSP responder goes down?

Client behavior depends on the OCSP configuration. In `hard fail` mode, clients reject the certificate if they cannot reach the OCSP responder. In `soft fail` mode, clients accept the certificate if the responder is unreachable. For production systems, deploy OCSP responders behind a load balancer with multiple instances. OCSP stapling also mitigates this issue — if the server cannot reach the OCSP responder, it stops stapling but the client can still connect (though without revocation checking).

### Can Smallstep replace both CFSSL and EJBCA?

Smallstep covers most use cases that CFSSL handles (certificate issuance + OCSP) with a more modern architecture. However, Smallstep does not generate CRLs, which EJBCA supports. If your environment requires CRL distribution (for legacy systems or specific compliance requirements), EJBCA is the better choice. For modern deployments where OCSP stapling is universally supported, Smallstep provides a simpler and more maintainable solution.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted OCSP Responder & Certificate Revocation: CFSSL vs Smallstep vs EJBCA CRL",
  "description": "Compare CFSSL OCSP, Smallstep Certificates, and EJBCA CRL for self-hosted certificate revocation infrastructure with Docker Compose deployment configs.",
  "datePublished": "2026-05-06",
  "dateModified": "2026-05-06",
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
