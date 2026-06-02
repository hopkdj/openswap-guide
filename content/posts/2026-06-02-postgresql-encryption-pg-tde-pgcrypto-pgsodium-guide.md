---
title: "Self-Hosted PostgreSQL Encryption at Rest: pg_tde vs pgcrypto vs pgsodium — Database Security Guide"
date: "2026-06-02"
tags: ["postgresql", "security", "encryption", "database", "pgcrypto", "pgsodium", "self-hosted", "compliance"]
draft: false
---

## Introduction

Database encryption is a cornerstone of data security in self-hosted environments. Regulatory frameworks like GDPR, HIPAA, and PCI-DSS mandate encryption of sensitive data at rest, and PostgreSQL offers multiple approaches — from column-level encryption with **pgcrypto** to transparent data encryption with Percona's **pg_tde** and modern authenticated encryption with **pgsodium** (libsodium bindings).

This guide compares all three approaches across deployment complexity, performance impact, key management, and compliance readiness. Each solution serves different threat models, from protecting against stolen backups to isolating sensitive columns from database administrators.

## Comparison Table

| Feature | pg_tde | pgcrypto | pgsodium |
|---------|--------|----------|----------|
| Encryption Level | Tablespace/file | Column-level | Column-level |
| Stars | 212 | Bundled (PG contrib) | 602 |
| Last Update | June 2026 | Continuous | October 2025 |
| Algorithm | AES-256-CTR / AES-256-CBC | AES, Blowfish, 3DES, etc. | XSalsa20, XChaCha20, AES-256-GCM |
| Key Management | External KMS (Vault, KMIP) | Manual (application) | Server-side with derivation |
| Transparent to App | Yes | No (manual encrypt/decrypt) | Partial (views + triggers) |
| Performance Impact | 3-8% | Per-column overhead | Minimal (libsodium native) |
| Authenticated Encryption | AES-GCM | No (raw only) | Yes (all operations) |
| Searchable Encryption | No | No (by design) | No (by design) |
| Backup Encryption | Yes (files are encrypted) | No (backups contain ciphertext only if encrypted) | No |
| Compliance Ready | Yes (PCI-DSS, HIPAA) | Partial (column-level) | Partial (column-level) |

## pg_tde: Transparent Data Encryption

Percona's pg_tde provides the closest equivalent to commercial TDE (Transparent Data Encryption) for PostgreSQL. It encrypts data at the storage layer — the database files themselves — so any backup, filesystem snapshot, or stolen disk image is unreadable without the decryption key.

### Architecture

pg_tde intercepts PostgreSQL's storage manager (smgr) layer, encrypting all table data as it is written to disk and decrypting on read. This is transparent to SQL queries and applications — no code changes needed.

### Docker Compose Setup

```yaml
version: "3.8"
services:
  postgres-tde:
    image: perconalab/pg_tde:17-latest
    container_name: pg-tde
    environment:
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: secure_master_key
      POSTGRES_DB: secure_db
      PG_TDE_KEY_SOURCE: "file"
      PG_TDE_KEY_PATH: "/etc/tde/keys"
    ports:
      - "5432:5432"
    volumes:
      - pg-tde-data:/var/lib/postgresql/data
      - ./tde-keys:/etc/tde/keys
    command: |
      -c shared_preload_libraries='pg_tde'
      -c pg_tde.keyring_type='file'
      -c pg_tde.file_keyring.path='/etc/tde/keys/keyring.json'

volumes:
  pg-tde-data:
```

### Configuration

```sql
-- Create the extension
CREATE EXTENSION pg_tde;

-- Create an encrypted tablespace using Vault as KMS
SELECT pg_tde_add_key_provider_vault(
    'vault-provider',
    '{"url":"https://vault.internal:8200","token":"s.xxxxxxxx","mount_path":"transit","ca_path":"/etc/ssl/vault-ca.pem"}'
);

-- Set the default key provider
SELECT pg_tde_set_principal_key(
    'my-database-key',
    'vault-provider'
);

-- Tables in this database are now transparently encrypted
CREATE TABLE patient_records (
    id SERIAL PRIMARY KEY,
    patient_name TEXT NOT NULL,
    medical_record JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Verification

```bash
# Data files on disk are encrypted (grep finds nothing)
grep "patient_name" /var/lib/postgresql/data/base/*/*
# No output — data is encrypted at the file level
```

## pgcrypto: Column-Level Classic

pgcrypto has been PostgreSQL's standard encryption extension since 8.3. It provides raw encryption functions (`pgp_sym_encrypt`, `encrypt`, `decrypt`) that applications call explicitly. While not transparent, pgcrypto offers the most control over what gets encrypted and with which algorithm.

### Installation

```bash
# Included in postgresql-contrib
sudo apt install postgresql-contrib
```

### Usage Patterns

```sql
CREATE EXTENSION pgcrypto;

-- Symmetric encryption with PGP
CREATE TABLE user_secrets (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    encrypted_ssn BYTEA,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert encrypted data
INSERT INTO user_secrets (user_id, encrypted_ssn)
VALUES (
    42,
    pgp_sym_encrypt('123-45-6789', 'application_secret_key_here')
);

-- Decrypt on read (result is text)
SELECT
    user_id,
    pgp_sym_decrypt(encrypted_ssn, 'application_secret_key_here') AS ssn
FROM user_secrets
WHERE user_id = 42;

-- Raw AES encryption with explicit key
SELECT encrypt(
    convert_to('sensitive data', 'utf8'),
    decode('0123456789abcdef0123456789abcdef', 'hex'),
    'aes'
);

-- One-way hashing for passwords (use bcrypt/bf)
UPDATE users
SET password_hash = crypt('new_password', gen_salt('bf', 10))
WHERE username = 'admin';

-- Verify password
SELECT (password_hash = crypt('entered_password', password_hash))
FROM users
WHERE username = 'admin';
```

### Key Management Challenges

pgcrypto requires application-level key management. A common pattern:

```bash
# Store key in HashiCorp Vault
vault kv put secret/pgcrypto/key value="$(openssl rand -hex 32)"

# Application retrieves key at startup
vault kv get -field=value secret/pgcrypto/key
```

## pgsodium: Modern Authenticated Encryption

pgsodium brings libsodium's modern cryptographic primitives to PostgreSQL. Unlike pgcrypto's raw encryption (which requires separate HMAC for authentication), pgsodium's operations are authenticated by default — any tampering with ciphertext is detected.

### Installation & Setup

```sql
CREATE EXTENSION pgsodium;

-- Generate a new server-managed key
SELECT pgsodium.create_key('my-app-key');

-- Key ID is stored in pgsodium.valid_keys
SELECT * FROM pgsodium.valid_keys;

-- Derive a key from a master key for specific context
SELECT pgsodium.derive_key(
    'my-app-key'::text,
    2,  -- subkey ID
    32, -- key length
    'user_sessions'::bytea  -- context
);
```

### Secret Box (Authenticated Symmetric Encryption)

```sql
CREATE TABLE secure_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    encrypted_content BYTEA,
    associated_data BYTEA,  -- for authenticated additional data
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Encrypt with server-managed key
INSERT INTO secure_documents (encrypted_content, associated_data)
VALUES (
    pgsodium.crypto_secretbox(
        convert_to('{"ssn": "123-45-6789", "name": "Alice"}', 'utf8'),
        gen_random_bytes(pgsodium.crypto_secretbox_noncebytes()),
        'my-app-key'::text
    ),
    '{"user_id": 42, "purpose": "kyc"}'::bytea
);
```

### Transparent Encryption with Views and Triggers

```sql
-- Create a view that automatically decrypts
CREATE VIEW readable_documents AS
SELECT
    id,
    convert_from(
        pgsodium.crypto_secretbox_open(
            encrypted_content,
            nonce,
            'my-app-key'::text
        ),
        'utf8'
    )::jsonb AS content,
    created_at
FROM secure_documents;

-- Trigger for automatic encryption on insert
CREATE FUNCTION encrypt_document_trigger()
RETURNS TRIGGER AS $$
BEGIN
    NEW.encrypted_content = pgsodium.crypto_secretbox(
        convert_to(NEW.plain_content, 'utf8'),
        gen_random_bytes(pgsodium.crypto_secretbox_noncebytes()),
        'my-app-key'::text
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### Encrypted Columns with Server-Managed Keys

```sql
CREATE TABLE customer_pii (
    id SERIAL PRIMARY KEY,
    customer_name TEXT,
    encrypted_email TEXT GENERATED ALWAYS AS (
        encode(
            pgsodium.crypto_secretbox(
                convert_to(customer_email_plain, 'utf8'),
                gen_random_bytes(pgsodium.crypto_secretbox_noncebytes()),
                'my-app-key'::text
            ),
            'base64'
        )
    ) STORED
);
```

## Choosing the Right Encryption Approach

| Requirement | Best Tool | Reason |
|-------------|-----------|--------|
| Compliance (PCI-DSS, HIPAA) | pg_tde | Transparent + backup encryption |
| Protect specific columns from DBAs | pgsodium | Server-managed keys, applications never see keys |
| Legacy application compatibility | pg_tde | No code changes required |
| Maximum cryptographic strength | pgsodium | libsodium, authenticated encryption |
| Simple password hashing | pgcrypto | crypt() with bcrypt, built-in |
| Key rotation without downtime | pg_tde | KMS integration, principal key rotation |
| Cross-platform key management | pgcrypto + Vault | Application manages keys, any KMS works |

## Why Self-Host Your Database Encryption?

Self-hosting encryption infrastructure gives you full control over your key material. When you use a managed database service, the cloud provider holds the encryption keys — even with "customer-managed keys," the cloud KMS sees every encryption and decryption operation. For organizations subject to GDPR or handling classified data, this shared responsibility model is insufficient.

Self-hosted PostgreSQL with pg_tde using your own Vault or KMIP server means the encryption keys never leave your infrastructure. Backups are encrypted by default — even if a backup tape goes missing or an S3 bucket becomes public, the data is cryptographically inaccessible without the key.

Performance optimization is another advantage. Cloud TDE solutions apply encryption uniformly, but self-hosted pgcrypto or pgsodium lets you selectively encrypt only PII columns while leaving high-throughput analytics data unencrypted. For more on database security, see our [K8s Config Encryption guide](../2026-05-22-k8s-config-encryption-at-rest-aescbc-kms-secretbox-guide/). Our [PKI Certificate Management guide](../self-hosted-pki-certificate-management-step-ca-caddy-nginx-proxy-manager-2026/) covers complementary TLS infrastructure, and our [PostgreSQL Backup guide](../pgbackrest-vs-barman-vs-wal-g-self-hosted-postgresql-backup-guide-2026/) covers securing your backup pipeline.

## FAQ

### Which encryption method is fastest?

pg_tde adds 3-8% overhead at the storage layer — measurable but acceptable for most workloads. pgsodium's libsodium operations are highly optimized and add <2% for individual column encryption. pgcrypto uses OpenSSL and performs similarly to pgsodium for AES operations, but its PGP functions are slower. For high-throughput OLTP, pg_tde's storage-level approach avoids per-row crypto operations.

### Can I encrypt only specific tables or columns?

pg_tde encrypts at the tablespace level — all tables in the tablespace are encrypted. For per-column encryption, use pgcrypto or pgsodium. A hybrid approach works well: use pg_tde for blanket compliance, and pgsodium for columns containing credentials, PII, or financial data that should be opaque even to database operators.

### How do key rotations work?

pg_tde supports online principal key rotation via `SELECT pg_tde_rotate_principal_key()` — existing data re-encrypts in the background using a new key. pgcrypto requires application-level rotation: decrypt with old key, re-encrypt with new key. pgsodium supports key derivation chains where you rotate the master key and derive new subkeys.

### What about backup encryption?

pg_tde encrypts data files — any backup of those files (pg_basebackup, filesystem snapshot) inherits the encryption. With pgcrypto and pgsodium, the backup contains ciphertext for encrypted columns but the database files themselves are unencrypted. Always combine column-level encryption with filesystem encryption (LUKS/dm-crypt) or backup tool encryption (pgBackRest with encryption).

### Is pg_tde production-ready?

Percona pg_tde is GA as of 2025 and used in production by organizations requiring PostgreSQL TDE for compliance. It supports PostgreSQL 16 and 17. Note that pg_tde requires a Percona-maintained PostgreSQL build — it's not a loadable extension for standard community PostgreSQL. Check licensing compatibility for your deployment.

### How does pgsodium's key management work?

pgsodium stores keys in a PostgreSQL table (`pgsodium.valid_keys`) with key IDs. The keys are encrypted with a server-level master key derived at startup. You can also reference external keys by URI. pgsodium never exposes raw key bytes to SQL — decryption operations happen internally, so even a superuser cannot extract the decryption key through SQL queries.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted PostgreSQL Encryption at Rest: pg_tde vs pgcrypto vs pgsodium — Database Security Guide",
  "description": "Complete comparison of PostgreSQL encryption solutions: Percona pg_tde (TDE), pgcrypto (column-level), and pgsodium (libsodium). Includes Docker Compose configs, key management, and compliance guidance.",
  "datePublished": "2026-06-02",
  "dateModified": "2026-06-02",
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
