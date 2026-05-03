---
title: "Self-Hosted PKI and Certificate Authority: cfssl, smallstep/step-ca, and EJBCA Comparison Guide"
date: 2026-05-03T17:10:00+00:00
draft: false
tags: ["pki", "certificate-authority", "security", "self-hosted", "tls", "encryption", "ssl"]
---

A self-hosted Public Key Infrastructure (PKI) and Certificate Authority (CA) gives you complete control over certificate issuance for your internal services, devices, and applications. While Let's Encrypt and ACME-based tools handle public-facing certificates, a self-hosted CA is essential for internal TLS, mutual TLS (mTLS), client authentication, code signing, and IoT device identity. This guide compares three self-hosted CA solutions: **Cloudflare's cfssl**, **smallstep's step-ca**, and **EJBCA**.

## Why Run Your Own Certificate Authority?

Self-hosting a CA solves several critical infrastructure needs:

- **Internal TLS** — issue certificates for internal services without depending on public CAs
- **Mutual TLS (mTLS)** — authenticate service-to-service communication in zero-trust architectures
- **Client certificates** — replace passwords with certificate-based authentication
- **Code signing** — sign internal software builds and verify authenticity
- **IoT device identity** — provision unique identities for embedded devices at scale
- **Full lifecycle control** — manage issuance, renewal, and revocation on your own terms
- **Air-gapped environments** — issue certificates in networks with no internet access

## Comparison Table

| Feature | cfssl (Cloudflare) | step-ca (smallstep) | EJBCA |
|---------|-------------------|---------------------|-------|
| Primary focus | PKI toolkit / API | Developer-friendly CA | Enterprise PKI |
| Language | Go | Go | Java |
| Web UI | cfssl-ui (basic) | step-ca has no built-in UI | Full web admin console |
| REST API | Yes | Yes | Yes (enterprise edition) |
| ACME support | No | Yes (built-in ACME server) | Via plugin |
| Certificate types | Server, client, code signing | Server, client, SSH certs | Full X.509 + CMS |
| SCEP support | No | Via add-on | Yes (built-in) |
| EST support | No | Yes | Yes |
| LDAP integration | No | Via provisioners | Built-in |
| HSM support | Via PKCS#11 | Via PKCS#11 | Full HSM support |
| Docker Compose | Simple | Simple | Complex (multiple services) |
| Best for | Automated PKI via API | Developer teams, mTLS | Enterprise compliance |

## cfssl: Cloudflare's PKI Toolkit

[cfssl](https://github.com/cloudflare/cfssl) is Cloudflare's open-source PKI toolkit. It provides a certificate generation, signing, and management API that powers Cloudflare's own certificate infrastructure. cfssl is ideal for teams that want programmatic PKI management with a clean JSON API.

### Docker Compose for cfssl

```yaml
version: "3.8"

services:
  cfssl:
    image: cfssl/cfssl:latest
    container_name: cfssl-server
    restart: unless-stopped
    ports:
      - "8888:8888"
    volumes:
      - ./cfssl-config:/etc/cfssl:ro
      - cfssl-data:/var/lib/cfssl
    command: ["serve", "-address=0.0.0.0", "-port=8888",
              "-ca=/etc/cfssl/ca.pem",
              "-ca-key=/etc/cfssl/ca-key.pem",
              "-config=/etc/cfssl/config.json"]

  cfssl-ui:
    image: cfssl/cfssl-ui:latest
    container_name: cfssl-ui
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - CFSSL_SERVER=http://cfssl-server:8888

volumes:
  cfssl-data:
```

### cfssl CA Configuration

```json
{
  "signing": {
    "default": {
      "expiry": "8760h",
      "usages": ["signing", "key encipherment", "server auth"]
    },
    "profiles": {
      "server": {
        "expiry": "8760h",
        "usages": ["signing", "key encipherment", "server auth"]
      },
      "client": {
        "expiry": "8760h",
        "usages": ["signing", "key encipherment", "client auth"]
      },
      "peer": {
        "expiry": "8760h",
        "usages": ["signing", "key encipherment", "server auth", "client auth"]
      }
    }
  }
}
```

### Issuing Certificates via cfssl API

```bash
# Generate a certificate signing request
cfssl gencert -initca ca-csr.json | cfssljson -bare ca

# Sign a server certificate
cfssl gencert -ca=ca.pem -ca-key=ca-key.pem \
  -config=config.json -profile=server \
  server-csr.json | cfssljson -bare server

# Sign via REST API
curl -X POST http://localhost:8888/api/v1/cfssl/sign \
  -d '{"request": {"CN": "app.internal", "hosts": ["app.internal", "10.0.0.5"]}, "profile": "server"}'
```

### Generating the CA with cfssl

```bash
# Create CA CSR configuration
cat > ca-csr.json << 'EOF'
{
  "CN": "My Internal CA",
  "key": {
    "algo": "ecdsa",
    "size": 256
  },
  "names": [
    {
      "C": "US",
      "ST": "California",
      "L": "San Francisco",
      "O": "My Organization",
      "OU": "Infrastructure"
    }
  ]
}
EOF

# Generate CA certificate and key
cfssl gencert -initca ca-csr.json | cfssljson -bare ca
```

## step-ca: Developer-Friendly Certificate Authority

[step-ca](https://github.com/smallstep/certificates) by smallstep is a modern, developer-friendly private certificate authority with built-in ACME support, SSH certificate issuance, and an excellent CLI. It is designed for teams that want a simple setup with powerful features.

### Docker Compose for step-ca

```yaml
version: "3.8"

services:
  step-ca:
    image: smallstep/step-ca:latest
    container_name: step-ca
    restart: unless-stopped
    ports:
      - "9000:9000"
      - "8443:8443"
    environment:
      - DOCKER_STEPCA_INIT=true
      - STEPCA_INIT_NAME="Internal CA"
      - STEPCA_INIT_DNS="ca.internal"
      - STEPCA_INIT_ADDRESS=":9000"
      - STEPCA_INIT_PROVISIONER=admin
      - STEPCA_INIT_PASSWORD_FILE=/run/password
    volumes:
      - step-ca-data:/home/step
      - ./password:/run/password:ro

  step-cli:
    image: smallstep/step-cli:latest
    container_name: step-cli
    entrypoint: ["sleep", "infinity"]
    volumes:
      - step-ca-data:/home/step:ro

volumes:
  step-ca-data:
```

### Initializing step-ca

```bash
# Initialize the CA (interactive)
step ca init

# Answer prompts:
# - Root CA name: My Internal CA
# - Root CA URI: https://ca.internal
# - Listen address: :9000
# - Provisioner name: admin
# - Provisioner password: (set a strong password)

# The CA generates:
#   certs/root_ca.crt     — Root certificate
#   secrets/root_ca_key   — Root CA private key
#   certs/intermediate_ca.crt — Intermediate certificate
#   secrets/intermediate_ca_key — Intermediate CA private key
#   config/ca.json        — CA configuration
```

### Using step-ca with ACME

One of step-ca's standout features is built-in ACME support, meaning tools like certbot and Caddy can request certificates from your internal CA:

```bash
# Get the ACME directory URL
step ca acme provisioner add acme --type ACME

# Use certbot with your internal CA
certbot certonly --server https://ca.internal/acme/acme/directory \
  -d app.internal --standalone

# Or use Caddy with internal CA
caddy reverse-proxy --from app.internal --to localhost:8080 \
  --acme-ca https://ca.internal/acme/acme/directory
```

### Issuing SSH Certificates with step-ca

step-ca uniquely supports SSH certificate issuance — a powerful feature for replacing SSH keys with short-lived certificates:

```bash
# Install the step CLI on client machines
curl -sSf https://cli.smallstep.com/install.sh | sh

# Authenticate to the CA
step ca bootstrap --ca-url https://ca.internal:9000 --fingerprint <fingerprint>

# Get an SSH certificate
step ssh cert app@server.internal --provisioner admin

# The CA returns a short-lived SSH certificate (default: 24 hours)
# No need to manage SSH authorized_keys files
```

### step-ca Configuration (ca.json)

```json
{
  "address": ":9000",
  "dnsNames": ["ca.internal"],
  "logger": {"format": "json"},
  "db": {"type": "badgerV3", "dataSource": "/home/step/db"},
  "authority": {
    "provisioners": [
      {
        "type": "JWK",
        "name": "admin",
        "key": {"use": "sig", "kty": "EC", ...},
        "encryptedKey": "..."
      }
    ]
  },
  "tls": {
    "cipherSuites": ["TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384"],
    "minVersion": 1.2,
    "maxVersion": 1.3,
    "renegotiation": false
  }
}
```

## EJBCA: Enterprise PKI

[EJBCA](https://github.com/primekey/ejbca) is a full-featured, enterprise-grade PKI system built on Java EE. It supports the widest range of certificate types, protocols (SCEP, EST, CMP), and compliance requirements, making it the choice for organizations with complex PKI needs.

### Docker Compose for EJBCA

```yaml
version: "3.8"

services:
  ejbca:
    image: keyfactor/community-ejbca:latest
    container_name: ejbca
    restart: unless-stopped
    ports:
      - "8080:8080"
      - "8443:8443"
    environment:
      - TLS_SETUP_ENABLED=simple
      - EJBCA_ADMIN_PASSWORD=ejbca_admin
    volumes:
      - ejbca-data:/opt/primekey

  ejbca-db:
    image: mariadb:10.11
    container_name: ejbca-db
    restart: unless-stopped
    environment:
      - MYSQL_ROOT_PASSWORD=dbpassword
      - MYSQL_DATABASE=ejbca
      - MYSQL_USER=ejbca
      - MYSQL_PASSWORD=ejbca
    volumes:
      - ejbca-db-data:/var/lib/mysql

volumes:
  ejbca-data:
  ejbca-db-data:
```

### EJBCA Key Features

- **Multiple CA hierarchies** — create root and intermediate CAs with flexible chain structures
- **SCEP protocol** — enroll devices using the Simple Certificate Enrollment Protocol (used by Cisco, Microsoft NDES)
- **EST protocol** — modern enrollment via Enrollment over Secure Transport (RFC 7030)
- **Hardware Security Module (HSM)** support — store CA keys in hardware for FIPS 140-2 compliance
- **Certificate profiles** — define custom certificate attributes, extensions, and validity periods
- **Role-based administration** — granular access control for CA operators, auditors, and administrators
- **Audit logging** — comprehensive logging of all CA operations for compliance
- **CMS/PKCS#7** — support for Cryptographic Message Syntax for signed and encrypted data

### EJBCA Certificate Enrollment via SCEP

```bash
# SCEP is commonly used by network devices (routers, switches, firewalls)
# to automatically request and renew certificates

# Example SCEP URL for a Cisco router:
# crypto pki trustpoint INTERNAL_CA
#  enrollment url http://ejbca.internal:8080/ejbca/publicweb/scep/pkiclient.exe
#  enrollment retry period 1
#  revocation-check none

# For Linux clients using sscep:
sscep getca -u http://ejbca.internal:8080/ejbca/publicweb/scep/pkiclient.exe \
  -c ca.pem -n MyInternalCA

sscep enroll -u http://ejbca.internal:8080/ejbca/publicweb/scep/pkiclient.exe \
  -c ca.pem -k server.key -r server.csr -l server.crt
```

## Choosing the Right CA for Your Needs

### Choose cfssl when:
- You want a lightweight, API-driven PKI
- You need programmatic certificate issuance from CI/CD pipelines
- Your team is comfortable working with JSON APIs and CLI tools
- You want the same PKI toolkit that powers Cloudflare's infrastructure

### Choose step-ca when:
- You want a developer-friendly CA with excellent documentation
- You need ACME support for internal certificate automation
- You want SSH certificate issuance alongside X.509
- You value a simple setup with powerful defaults

### Choose EJBCA when:
- You need enterprise-grade compliance (FIPS, Common Criteria)
- You require SCEP/EST/CMP protocol support
- You need HSM integration for key storage
- You manage complex CA hierarchies with multiple RAs
- Your organization has regulatory PKI requirements

## PKI Best Practices

### Root CA Protection

The root CA key is the most sensitive asset in your PKI. Follow these practices:

```bash
# 1. Generate the root CA offline on an air-gapped machine
# 2. Store the root key on encrypted, offline media
# 3. Use an intermediate CA for day-to-day issuance
# 4. Rotate intermediate CA certificates before expiry
# 5. Publish CRL and OCSP endpoints for revocation checking

# Check certificate expiry
step certificate inspect ca.crt --short
openssl x509 -in ca.crt -noout -dates
```

### Certificate Lifecycle Management

```bash
# step-ca: Check certificate status
step certificate list

# step-ca: Renew a certificate
step ca renew internal.crt internal.key

# step-ca: Revoke a compromised certificate
step ca revoke --cert internal.crt --reason "key-compromise"

# cfssl: Revoke via API
curl -X POST http://localhost:8888/api/v1/cfssl/revoke \
  -d '{"serial": "1234567890", "authority_key_id": "abcdef"}'
```

For teams managing public-facing certificates alongside internal ones, see our guide on [TLS certificate automation with certbot, acme.sh, and lego](../2026-04-27-certbot-vs-acme-sh-vs-lego-vs-dehydrated-self-hosted-acme-dns-challenge-guide-2026.md). For verifying TLS configuration across your infrastructure, check our [SSL/TLS scanning tools comparison](../2026-04-22-testssl-vs-sslyze-vs-sslscan-self-hosted-ssl-tls-scanning-guide-2026.md).

## FAQ

### What is the difference between a root CA and an intermediate CA?

A root CA is the top-level certificate authority in a PKI hierarchy. Its certificate is self-signed and serves as the trust anchor. An intermediate CA is signed by the root CA (or another intermediate) and is used for day-to-day certificate issuance. Best practice is to keep the root CA offline and only use intermediate CAs for signing end-entity certificates. This limits the impact if an intermediate CA key is compromised — you can revoke the intermediate certificate and issue a new one without replacing the root.

### Can step-ca replace Let's Encrypt for internal services?

Yes. step-ca includes a built-in ACME server, meaning any ACME-compatible client (certbot, Caddy, Traefik, nginx with acme.sh) can request certificates from your step-ca instance. This gives you Let's Encrypt-like automation for internal domains, with the added benefit that you control the CA and can issue certificates for any domain name (including `.internal`, `.local`, or private TLDs that public CAs won't sign).

### Do I need an enterprise CA like EJBCA for a small team?

Probably not. EJBCA is designed for organizations with complex compliance requirements, multiple CA hierarchies, and protocol needs (SCEP for network devices, EST for IoT). For a small to medium team, step-ca or cfssl are simpler to deploy and maintain. Move to EJBCA when you need features that cfssl and step-ca cannot provide: SCEP, HSM integration, multi-RA workflows, or regulatory compliance certifications.

### How do I distribute the root CA certificate to client machines?

For Linux: copy the root CA cert to `/usr/local/share/ca-certificates/` and run `update-ca-certificates`. For macOS: add to the Keychain and set trust to "Always Trust" for SSL. For Windows: import via Group Policy or `certutil -addstore -f "ROOT" ca.crt`. For Docker containers: mount the root CA cert and update the CA bundle in your container image. For browsers: each browser has its own certificate store — consider deploying via MDM for enterprise environments.

### How long should internal certificates be valid?

For server certificates: 1-2 years is common for internal CAs (longer than public CAs because you control revocation). For client certificates: 24 hours to 90 days, depending on your rotation capability. For code signing certificates: 1-3 years. step-ca supports short-lived certificates (as short as 1 hour) with automatic renewal, which is the gold standard for zero-trust architectures.

### What happens when a certificate is compromised?

Immediately revoke the certificate using your CA's revocation mechanism. The CA publishes the revocation via Certificate Revocation List (CRL) or Online Certificate Status Protocol (OCSP). Clients checking revocation will reject the compromised certificate. Then investigate the compromise, rotate any affected keys, and issue new certificates. With step-ca, use `step ca revoke`; with cfssl, use the `/api/v1/cfssl/revoke` endpoint; with EJBCA, use the web UI or RA API.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted PKI and Certificate Authority: cfssl, smallstep/step-ca, and EJBCA Comparison Guide",
  "description": "Compare self-hosted PKI and CA solutions: Cloudflare cfssl, smallstep step-ca, and EJBCA. Covers Docker Compose setup, ACME support, SSH certificates, and enterprise PKI.",
  "datePublished": "2026-05-03",
  "dateModified": "2026-05-03",
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
