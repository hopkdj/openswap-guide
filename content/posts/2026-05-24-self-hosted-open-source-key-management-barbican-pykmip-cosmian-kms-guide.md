---
title: "Self-Hosted Open Source Key Management: Barbican vs PyKMIP vs Cosmian KMS"
date: "2026-05-12"
tags: ["key-management", "kms", "security", "encryption", "barbican", "pykmip", "cosmian"]
draft: false
---

Key Management Systems (KMS) are critical infrastructure components that handle the secure generation, storage, rotation, and lifecycle management of cryptographic keys. While cloud providers offer managed KMS services (AWS KMS, Google Cloud KMS, Azure Key Vault), self-hosted open-source alternatives give organizations full control over their cryptographic material — essential for compliance, data sovereignty, and zero-trust architectures.

This guide compares three open-source KMS platforms: **OpenStack Barbican**, **PyKMIP**, and **Cosmian KMS**, covering architecture, supported protocols, deployment, and use cases.

## Overview of Open Source KMS Platforms

| Feature | Barbican | PyKMIP | Cosmian KMS |
|---------|----------|--------|-------------|
| **GitHub Stars** | 246 | 298 | 308 |
| **Primary Language** | Python | Python | Rust |
| **Protocol Support** | REST API, PKCS#11 | KMIP 1.0-2.1 | REST, KMIP, JWE, JWT |
| **Key Types** | Symmetric, Asymmetric, Certificates | Symmetric, Asymmetric, Certificates | Symmetric, Asymmetric, FPE, Deterministic |
| **HSM Integration** | PKCS#11, PKCS#12, KMIP | Native KMIP HSM support | PKCS#11, AWS KMS, Azure Key Vault |
| **License** | Apache 2.0 | Apache 2.0 | BUSL 1.1 (source-available) |
| **Docker Support** | Official images via OpenStack | Docker Compose available | Official Docker images |
| **Primary Use Case** | OpenStack cloud secrets | Enterprise KMIP compliance | Multi-cloud encryption, FPE |

### OpenStack Barbican

Barbican is the secrets management service of the OpenStack ecosystem. It provides a REST API for secure storage, provisioning, and management of secrets including encryption keys, certificates, and passwords. Barbican supports multiple plugin backends including simple crypto, PKCS#11 HSMs, and KMIP-compliant key managers.

### PyKMIP

PyKMIP is a pure Python implementation of the Key Management Interoperability Protocol (KMIP). KMIP is an OASIS standard for managing cryptographic keys across heterogeneous key management systems. PyKMIP provides a server that accepts KMIP client connections and manages keys, certificates, and other managed objects.

### Cosmian KMS

Cosmian KMS is a modern, Rust-based key management system designed for multi-cloud and hybrid environments. It supports a wide range of cryptographic operations including Format-Preserving Encryption (FPE), Deterministic Encryption, and standard symmetric/asymmetric key management. It integrates with external KMS providers (AWS, Azure, GCP) and supports KMIP.

## Deploying Barbican with Docker Compose

Barbican is typically deployed as part of an OpenStack deployment, but can run standalone:

```yaml
# docker-compose.yml for standalone Barbican
version: '3.8'
services:
  barbican-api:
    image: openstack/barbican-api:2024.1
    container_name: barbican-api
    ports:
      - "9311:9311"
    environment:
      - OS_AUTH_URL=http://keystone:5000/v3
      - BARBICAN_CONFIG_FILE=/etc/barbican/barbican.conf
    volumes:
      - ./barbican.conf:/etc/barbican/barbican.conf:ro
      - barbican-data:/etc/barbican
    depends_on:
      - barbican-db
      - rabbitmq

  barbican-worker:
    image: openstack/barbican-worker:2024.1
    container_name: barbican-worker
    environment:
      - BARBICAN_CONFIG_FILE=/etc/barbican/barbican.conf
    volumes:
      - ./barbican.conf:/etc/barbican/barbican.conf:ro
    depends_on:
      - barbican-db
      - rabbitmq

  barbican-db:
    image: mariadb:10.11
    container_name: barbican-db
    environment:
      - MYSQL_ROOT_PASSWORD=barbican_secret
      - MYSQL_DATABASE=barbican
    volumes:
      - barbican-db-data:/var/lib/mysql

  rabbitmq:
    image: rabbitmq:3-management
    container_name: barbican-rabbitmq
    ports:
      - "5672:5672"
    environment:
      - RABBITMQ_DEFAULT_USER=barbican
      - RABBITMQ_DEFAULT_PASS=barbican_rabbit

volumes:
  barbican-data:
  barbican-db-data:
```

Barbican's configuration file (`barbican.conf`) defines the secret store backend, authentication, and encryption settings:

```ini
[DEFAULT]
transport_url = rabbit://barbican:barbican_rabbit@rabbitmq:5672/
sql_connection = mysql+pymysql://root:barbican_secret@barbican-db/barbican

[secretstore]
namespace = barbican.secretstore.plugin
enabled_secretstore_plugins = store_crypto

[crypto]
namespace = barbican.crypto.plugin
enabled_crypto_plugins = simple_crypto

[simple_crypto_plugin]
kek = 'YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXo='
```

For production deployments, replace the `simple_crypto` plugin with a PKCS#11 HSM or KMIP backend for hardware-backed key storage.

## Deploying PyKMIP with Docker Compose

PyKMIP provides a straightforward Docker deployment:

```yaml
# docker-compose.yml for PyKMIP
version: '3.8'
services:
  pykmip-server:
    image: pykmip/pykmip:latest
    container_name: pykmip-server
    ports:
      - "5696:5696"
    volumes:
      - ./pykmip.conf:/etc/pykmip/server.conf:ro
      - pykmip-data:/var/local/kmip
    restart: unless-stopped

volumes:
  pykmip-data:
```

PyKMIP server configuration:

```ini
[server]
host=0.0.0.0
port=5696
certificate_path=/etc/pykmip/certs/server.crt
key_path=/etc/pykmip/certs/server.key
ca_path=/etc/pykmip/certs/ca.crt
auth_suite=Basic

[policy_path]
path=/var/local/kmip
```

PyKMIP generates self-signed certificates on first run. For production, replace with certificates from your internal CA. The KMIP protocol uses TCP port 5696 by default with TLS encryption.

## Deploying Cosmian KMS with Docker Compose

Cosmian KMS ships with official Docker images:

```yaml
# docker-compose.yml for Cosmian KMS
version: '3.8'
services:
  cosmian-kms:
    image: cosmian/kms:latest
    container_name: cosmian-kms
    ports:
      - "9998:9998"
    environment:
      - COSMIAN_KMS__SERVER__ADDRESS=0.0.0.0:9998
      - COSMIAN_KMS__DATABASE__DATABASE_URL=sqlite:///var/lib/kms/kms.db
    volumes:
      - kms-data:/var/lib/kms
      - ./kms-certificates:/etc/certificates:ro
    restart: unless-stopped

volumes:
  kms-data:
```

Start Cosmian KMS:

```bash
docker compose up -d
# Verify it's running
curl -k https://localhost:9998/api/version
```

Cosmian KMS uses port 9998 by default with TLS. It supports SQLite for development and PostgreSQL for production deployments.

## Comparing Key Management Capabilities

### Key Lifecycle Management

| Operation | Barbican | PyKMIP | Cosmian KMS |
|-----------|----------|--------|-------------|
| Key Generation | ✅ REST API | ✅ KMIP Create | ✅ REST API |
| Key Rotation | ✅ Via orders API | ✅ KMIP Re-key | ✅ Automatic rotation |
| Key Revocation | ✅ Via status API | ✅ KMIP Revoke | ✅ REST API |
| Key Destruction | ✅ Via secret delete | ✅ KMIP Destroy | ✅ REST API |
| Key Archival | ✅ Via metadata | ✅ KMIP Archive | ✅ Via tags |
| Bulk Operations | ❌ Limited | ✅ KMIP Batch | ✅ Via API |

### Cryptographic Algorithm Support

**Barbican** supports AES, RSA, ECC, and HMAC through its plugin architecture. Key sizes follow NIST recommendations (AES-128/256, RSA-2048/4096).

**PyKMIP** supports the full KMIP specification including AES, DES, Triple DES, RSA, DSA, EC, HMAC, SHA, and more. KMIP 2.1 adds support for modern algorithms like ChaCha20 and Ed25519.

**Cosmian KMS** offers the broadest algorithm support including AES-GCM, ChaCha20-Poly1305, RSA, ECDSA, Ed25519, X25519, and Format-Preserving Encryption (FPE) for database column encryption.

### Integration Patterns

**Barbican** integrates natively with OpenStack services (Cinder for volume encryption, Glance for image encryption, Swift for object storage). It also provides a generic REST API for custom integrations.

**PyKMIP** integrates with any KMIP-compliant client, including enterprise storage arrays (NetApp, Dell EMC), database systems (Oracle TDE, SQL Server TDE), and backup solutions (Veeam, Commvault).

**Cosmian KMS** integrates through REST API, supports proxy encryption for databases (PostgreSQL, MySQL), and provides SDKs for Rust, Python, and JavaScript.

## Choosing the Right KMS

### Choose Barbican if:
- You run an OpenStack cloud infrastructure
- You need integration with Cinder, Glance, or Swift encryption
- Your team already manages OpenStack services
- You need PKCS#11 HSM integration with the simple_crypto fallback

### Choose PyKMIP if:
- Your organization requires KMIP compliance (common in finance and healthcare)
- You need to integrate with KMIP-aware storage arrays or databases
- You want a standards-compliant, vendor-neutral key management solution
- You need KMIP 2.x features like batch operations and object grouping

### Choose Cosmian KMS if:
- You need Format-Preserving Encryption for database columns
- You operate in a multi-cloud environment and want unified key management
- You need a modern Rust-based implementation with strong performance
- You require integration with cloud KMS providers (AWS, Azure, GCP)

## Security Best Practices

1. **Enable TLS everywhere** — All three platforms support TLS for API communications. Never run a KMS over plain HTTP in production.
2. **Use hardware-backed storage** — Connect Barbican to a PKCS#11 HSM, use PyKMIP with KMIP-aware HSMs, or configure Cosmian KMS with an external HSM for root key storage.
3. **Implement key rotation policies** — Automate rotation based on time (e.g., every 90 days) or usage thresholds. All three platforms support rotation, but implementation varies.
4. **Audit key access** — Enable audit logging for all key operations. Barbican logs to OpenStack's audit system, PyKMIP logs to syslog, and Cosmian KMS provides structured JSON logs.
5. **Segregate environments** — Deploy separate KMS instances for development, staging, and production. Never share keys across environments.

## Why Self-Host Your KMS?

Running your own Key Management System provides several advantages over cloud-managed alternatives:

**Data sovereignty and compliance**: Regulations like GDPR, HIPAA, and SOX often require that cryptographic keys remain under your direct control. Self-hosted KMS ensures keys never leave your infrastructure, avoiding jurisdictional risks associated with cloud provider key storage.

**Cost predictability**: Cloud KMS pricing is per-operation (each encrypt/decrypt call costs money). For high-throughput applications processing millions of operations daily, self-hosted KMS eliminates variable costs and provides predictable infrastructure spending.

**Zero-trust architecture**: In zero-trust models, you cannot rely on a third party to protect your keys. Self-hosted KMS integrates directly with your identity provider, network policies, and audit systems, giving you complete visibility and control over every cryptographic operation.

**Customization and extensibility**: Open-source KMS platforms can be modified to meet specific organizational requirements — custom key derivation functions, specialized HSM integrations, or bespoke audit logging formats. Cloud KMS offers no such flexibility.

**No vendor lock-in**: When your KMS is cloud-provider-specific, migrating workloads to another cloud requires re-encrypting all data with new keys. Open-source KMS platforms are portable and can be deployed across any infrastructure.

For organizations managing secrets at scale, see our [complete secrets management comparison](../2026-04-25-vault-vs-infisical-vs-passbolt-self-hosted-secret/) and [HSM key management guide](../2026-05-08-self-hosted-hsm-key-management-softhsm-nethsm-pkcs11-guide/). If you need certificate management alongside key management, our [certificate management comparison](../2026-04-19-cert-manager-vs-lego-vs-acme-sh-self-hosted-tls-c/) covers the certificate lifecycle side.

## FAQ

### What is the difference between a KMS and an HSM?

A Key Management System (KMS) is software that manages the lifecycle of cryptographic keys — generation, storage, rotation, revocation, and destruction. A Hardware Security Module (HSM) is a physical device that performs cryptographic operations in tamper-resistant hardware. KMS and HSM are complementary: a KMS can use an HSM as its backing store for root keys while managing the higher-level key lifecycle in software.

### Is KMIP still relevant in 2026?

Yes. KMIP (Key Management Interoperability Protocol) remains the industry standard for key management, maintained by OASIS. Major storage vendors (NetApp, Dell EMC, Pure Storage), database vendors (Oracle, IBM), and backup solutions all support KMIP. PyKMIP provides a free, open-source KMIP server implementation that integrates with these enterprise systems.

### Can Barbican run without the full OpenStack stack?

Yes. While Barbican is designed as an OpenStack service, it can run standalone with its own database (MySQL/PostgreSQL) and message broker (RabbitMQ). You can configure it without Keystone authentication using the simple authentication plugin, making it suitable for non-OpenStack environments.

### Does Cosmian KMS support FIPS 140-2 compliance?

Cosmian KMS uses the RustCrypto libraries which are working toward FIPS validation. For FIPS-compliant deployments, you can configure Cosmian KMS to use an external FIPS-validated HSM (via PKCS#11) as the root key store, ensuring all cryptographic operations meet FIPS 140-2 Level 2 or higher requirements.

### How do these KMS platforms handle key backup and disaster recovery?

**Barbican** stores encrypted secrets in its database; backup the database and the KMS master key (KEK). **PyKMIP** stores objects in its policy database; backup the database directory and certificate files. **Cosmian KMS** stores keys in its database; back up the database and ensure the master key is stored in an HSM or secure backup location. For all three, test restore procedures regularly.

### Which KMS is easiest to deploy for a small team?

**PyKMIP** has the simplest deployment — a single Docker container with minimal configuration. **Cosmian KMS** is also straightforward with official Docker images. **Barbican** requires the most infrastructure (database, message broker, optional Keystone), making it better suited for teams already running OpenStack.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Open Source Key Management: Barbican vs PyKMIP vs Cosmian KMS",
  "description": "Compare three open-source Key Management Systems — OpenStack Barbican, PyKMIP, and Cosmian KMS — for self-hosted cryptographic key lifecycle management.",
  "datePublished": "2026-05-12",
  "dateModified": "2026-05-12",
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
