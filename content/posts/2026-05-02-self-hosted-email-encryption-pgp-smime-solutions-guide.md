---
title: "Self-Hosted Email Encryption: PGP, S/MIME & End-to-End Encrypted Mail Solutions 2026"
date: 2026-05-02
draft: false
tags: ["email", "encryption", "security", "privacy", "pgp", "smime"]
---

Email remains one of the most widely used communication protocols, yet most messages traverse the internet in plaintext. Self-hosted email encryption gives you full control over message confidentiality, ensuring only intended recipients can read your correspondence. This guide covers the leading self-hosted email encryption approaches — PGP, S/MIME, and integrated encrypted mail servers.

## How Self-Hosted Email Encryption Works

Email encryption operates at different layers of the mail delivery chain. **Transport encryption** (TLS/STARTTLS) protects messages between mail servers but leaves them readable at rest. **End-to-end encryption** (PGP/GPG or S/MIME) encrypts the message body so only the sender and recipient can decrypt it — even the mail server cannot read the content.

For self-hosted deployments, you typically combine both approaches: a TLS-protected mail server (like Postal, Stalwart, or Mailcow) for transport security, plus PGP or S/MIME for message-level encryption.

### PGP (Pretty Good Privacy) / GPG

PGP uses asymmetric cryptography — each user has a public key (shared openly) and a private key (kept secret). Messages encrypted with a recipient's public key can only be decrypted with their private key. GnuPG (GPG) is the open-source implementation of the OpenPGP standard.

**Key advantages:**
- No central certificate authority needed — keys are distributed peer-to-peer
- Strong cryptographic algorithms (RSA, ECC, Ed25519)
- Works with any email client that supports OpenPGP
- Supports digital signatures for message authentication

### S/MIME (Secure/Multipurpose Internet Mail Extensions)

S/MIME also uses public-key cryptography but relies on X.509 certificates issued by a certificate authority. It's natively supported by most enterprise email clients (Outlook, Apple Mail, Thunderbird).

**Key advantages:**
- Built into major email clients — no plugins needed
- Certificate-based trust model with CA validation
- Supports encryption and digital signatures
- Better suited for enterprise/organizational deployments

## Comparing Self-Hosted Email Encryption Solutions

| Feature | GnuPG (GPG) + Mailcow | Rspamd + PGP | Stalwart Mail (built-in) | Mailpiler Archive (encrypted) |
|---|---|---|---|---|
| Encryption standard | OpenPGP | OpenPGP | OpenPGP + S/MIME | AES-256 at rest |
| Self-hosted | ✅ | ✅ | ✅ | ✅ |
| Web mail PGP support | ✅ (via Roundcube plugin) | ❌ | ✅ | ❌ |
| Key management | Manual / keys.openpgp.org | Manual | Built-in | N/A |
| Digital signatures | ✅ | ✅ | ✅ | ❌ |
| Docker support | ✅ | ✅ | ✅ | ✅ |
| Active development | ✅ | ✅ | ✅ | ✅ |
| GitHub stars | 12,667+ (mailcow) | 2,500+ (Rspamd) | Growing | 304 |

## Deploying Mailcow with PGP Encryption

[Mailcow](https://github.com/mailcow/mailcow-dockerized) is a full-featured mail server suite that includes Postfix, Dovecot, and a web interface with built-in PGP support. It provides the most complete self-hosted email encryption experience out of the box.

### Prerequisites

- A VPS or dedicated server with a public IP
- A domain name with proper DNS records (MX, SPF, DKIM, DMARC)
- At least 4 GB RAM, 2 CPU cores, 40 GB disk

### Docker Compose Configuration

Clone the official repository and configure:

```bash
git clone https://github.com/mailcow/mailcow-dockerized
cd mailcow-dockerized
cp mailcow.conf.sample mailcow.conf
# Edit mailcow.conf with your domain and settings
```

The default `docker-compose.yml` orchestrates all services:

```yaml
services:
  unbound-mailcow:
    image: mailcow/unbound:1.23
    environment:
      - SKETCH_MODE=y
    dns:
      - 127.0.0.1
    volumes:
      - unbound-data:~/unbound
    restart: always

  postfix-mailcow:
    image: mailcow/postfix:1.77
    volumes:
      - vmail-index:/var/lib/dovecot/index
      - vmail:/var/vmail
      - crypt-vmail:/var/vmail/crypt
    environment:
      - ADDITIONAL_SAN=$MAILCOW_HOSTNAME
    depends_on:
      unbound-mailcow:
        condition: service_started
    restart: always

  dovecot-mailcow:
    image: mailcow/dovecot:2.1
    volumes:
      - vmail:/var/vmail
      - vmail-index:/var/lib/dovecot/index
    depends_on:
      - postfix-mailcow
    restart: always

  nginx-mailcow:
    image: mailcow/nginx:1.01
    ports:
      - "${HTTP_BIND:-127.0.0.1}:80:80"
      - "${HTTPS_BIND:-127.0.0.1}:443:443"
    depends_on:
      - sogo-mailcow
      - php-fpm-mailcow
    restart: always

  sogo-mailcow:
    image: mailcow/sogo:1.125
    environment:
      - DBNAME=sogo
      - DBUSER=sogo
    volumes:
      - sogo-web:/sogo
    restart: always
```

Generate the full configuration:

```bash
docker compose up -d
```

### Configuring PGP in SOGo Webmail

1. Log into SOGo webmail at `https://your-domain.com`
2. Navigate to **Preferences → Mail → PGP Keys**
3. Generate or import your PGP key pair
4. Enable "Sign outgoing messages" and "Encrypt incoming messages"
5. Publish your public key to a keyserver for others to find

### Setting Up DKIM and DMARC

Mailcow automatically generates DKIM keys. Add the DKIM record to your DNS:

```bash
# Get your DKIM public key
docker compose exec postfix-mailcow cat /var/lib/dkim/your-domain.com.dns
```

Add the DKIM, SPF, and DMARC records to your domain's DNS:

```text
# SPF record
your-domain.com. IN TXT "v=spf1 mx a:mail.your-domain.com ~all"

# DMARC record
_dmarc.your-domain.com. IN TXT "v=DMARC1; p=quarantine; rua=mailto:dmarc@your-domain.com"
```

## Deploying Stalwart Mail with Built-in Encryption

[Stalwart Mail](https://github.com/stalwartlabs/mail-server) is a modern, all-in-one mail server written in Rust that includes native PGP and S/MIME support without requiring additional plugins.

### Docker Compose Configuration

```yaml
services:
  stalwart:
    image: stalwartlabs/mail-server:latest
    container_name: stalwart-mail
    ports:
      - "25:25"       # SMTP
      - "587:587"     # Submission
      - "993:993"     # IMAPS
      - "8080:8080"   # Admin UI / JMAP
    volumes:
      - stalwart-data:/opt/stalwart-mail
      - stalwart-config:/etc/stalwart-mail
    environment:
      - STALWART_ADMIN_SECRET=your-admin-secret
    restart: unless-stopped

volumes:
  stalwart-data:
  stalwart-config:
```

### Configure PGP Keys

Stalwart allows per-user PGP key configuration through its JMAP API:

```bash
# Upload a PGP public key for a user
curl -X POST https://mail.your-domain.com/jmap \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "using": ["urn:ietf:params:jmap:pgp"],
    "methodCalls": [[
      "PgpKey/set",
      {
        "accountId": "<account-id>",
        "create": {
          "key1": {
            "blobId": "<blob-id>",
            "purpose": "encrypt"
          }
        }
      }
    ]]
  }'
```

### S/MIME Configuration

For S/MIME, Stalwart supports X.509 certificate import:

```bash
# Import an S/MIME certificate
curl -X POST https://mail.your-domain.com/jmap \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "using": ["urn:ietf:params:jmap:smime"],
    "methodCalls": [[
      "SmimeCertificate/set",
      {
        "accountId": "<account-id>",
        "create": {
          "cert1": {
            "blobId": "<blob-id>"
          }
        }
      }
    ]]
  }'
```

## Deploying Rspamd with PGP Verification

[Rspamd](https://github.com/rspamd/rspamd) is a fast, modular spam filtering system that also supports PGP signature verification for incoming messages.

### Docker Compose with Rspamd

```yaml
services:
  rspamd:
    image: rspamd/rspamd:latest
    container_name: rspamd
    ports:
      - "11332:11332"  # Worker proxy
      - "11334:11334"  # Web UI
    volumes:
      - ./rspamd.conf:/etc/rspamd/rspamd.conf
      - ./local.d:/etc/rspamd/local.d
      - rspamd-data:/var/lib/rspamd
    restart: unless-stopped

volumes:
  rspamd-data:
```

### Configure PGP Verification in Rspamd

Create a local configuration file at `local.d/arc.conf`:

```conf
# Enable PGP signature verification
pgp {
  enabled = true;
  key_directory = "/var/lib/rspamd/pgp_keys";
  allow_local_networks = true;
}
```

Place PGP public keys in the configured directory for automatic verification of signed messages.

## Why Self-Host Email Encryption?

Self-hosting your encrypted email infrastructure provides several advantages over commercial encrypted mail providers:

**Complete Data Ownership** — Your encrypted messages never touch a third-party server. With PGP, even if the mail server is compromised, the message content remains unreadable without the private key. This is fundamentally different from providers that hold your encryption keys.

**No Vendor Lock-In** — OpenPGP is an open standard (RFC 4880). Your keys and encrypted messages are portable across any compatible client or server. You're not tied to a specific provider's proprietary encryption format.

**Compliance and Auditing** — For regulated industries (healthcare, finance, legal), self-hosted encryption lets you prove exactly how messages are protected. You control the key lifecycle, rotation policies, and audit trails.

**Integration with Existing Infrastructure** — Self-hosted encryption integrates with your existing mail server, directory services, and backup systems. You can apply your organization's security policies uniformly across all communication channels.

For related reading on mail server setup, see our [Postal vs Stalwart vs Haraka SMTP relay guide](../2026-04-26-postal-vs-stalwart-vs-haraka-self-hosted-smtp-relay-guide-2026/) and [Mailcow vs Mailu vs Stalwart mail server comparison](../2026-04-26-postal-vs-stalwart-vs-haraka-self-hosted-smtp-relay-guide-2026/).

## FAQ

### What is the difference between PGP and S/MIME for email encryption?

PGP uses a decentralized trust model where users exchange public keys directly, while S/MIME relies on X.509 certificates issued by trusted certificate authorities. PGP is preferred by privacy-focused users and open-source communities, while S/MIME is more common in enterprise environments because it integrates with existing PKI infrastructure and is natively supported by Outlook and Apple Mail.

### Can I use PGP encryption with any email client?

Most modern email clients support PGP through plugins or built-in features. Thunderbird has native OpenPGP support. Outlook requires a plugin like Gpg4win. Webmail interfaces vary — SOGo (included in Mailcow) has built-in PGP, while Roundcube needs the Enigma plugin. Mobile support is available through apps like OpenKeychain (Android) and Canary Mail (iOS).

### Is self-hosted email encryption legal and compliant?

Yes. Self-hosted email encryption using PGP or S/MIME is legal in most jurisdictions. In fact, it helps meet regulatory requirements like GDPR, HIPAA, and PCI DSS that mandate protection of sensitive data in transit. The decentralized nature of PGP means no single entity controls the encryption, which can simplify compliance audits.

### How do I recover my encrypted emails if I lose my private key?

You cannot recover messages encrypted with a lost private key — this is by design. Always maintain secure backups of your private key in a separate location. Consider using a key escrow service or splitting your key with Shamir's Secret Sharing for organizational deployments. Mailcow allows exporting your key pair for backup purposes.

### Does email encryption affect deliverability or spam scoring?

Encrypted email content cannot be scanned by spam filters on the receiving end, but the email headers and envelope remain visible. Proper SPF, DKIM, and DMARC configuration (which Mailcow and Stalwart handle automatically) ensures good deliverability. The encryption itself does not negatively impact spam scores — reputable senders using TLS transport encryption plus PGP message encryption maintain excellent deliverability.

### Can I encrypt emails to recipients who don't use encryption?

No. End-to-end encryption requires both sender and recipient to support the same encryption standard. If your recipient doesn't use PGP or S/MIME, the message will be sent unencrypted (though transport TLS may still protect it in transit). Some services offer "portal encryption" where the recipient receives a link to a secure web portal to read the message.

## Self-Hosted Email Encryption Setup Checklist

1. **Choose your mail server** — Mailcow (full suite), Stalwart (modern, all-in-one), or a Postfix/Dovecot setup with Rspamd
2. **Configure TLS** — Ensure STARTTLS is enabled for transport encryption
3. **Set up DKIM/SPF/DMARC** — Critical for deliverability and authentication
4. **Generate PGP keys** — Use `gpg --full-generate-key` or your mail server's built-in key generation
5. **Publish your public key** — Upload to keys.openpgp.org or your own WKD (Web Key Directory)
6. **Test encryption** — Send encrypted test messages between accounts
7. **Back up private keys** — Store encrypted backups in a secure, offline location
8. **Establish key rotation policy** — Plan for annual key rotation and revocation procedures

<script type="application/ld+json">
{
  "@context": "https://www.schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Email Encryption: PGP, S/MIME & End-to-End Encrypted Mail Solutions 2026",
  "description": "Complete guide to self-hosted email encryption using PGP, S/MIME, and encrypted mail servers like Mailcow, Stalwart, and Rspamd with Docker Compose configurations.",
  "datePublished": "2026-05-02",
  "dateModified": "2026-05-02",
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
