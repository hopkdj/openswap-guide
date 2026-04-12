---
title: "Best Self-Hosted Password Managers 2026: Vaultwarden vs Passbolt vs Psono"
date: 2026-04-12
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "A complete comparison of the top self-hosted password managers in 2026. Docker setups, feature breakdowns, and a definitive recommendation for individuals and teams."
---

## Why Self-Host Your Password Manager?

Password managers are the backbone of any security-conscious workflow. They generate strong, unique passwords for every account, store them encrypted, and sync across all your devices. But when you rely on a cloud-hosted service, you're trusting a third party with the keys to your digital life — your master password hash, your encrypted vault metadata, and sometimes even hints that can aid an attacker.

Self-hosting a password manager shifts that trust boundary back to you. You control the server, the database, the backups, and the encryption at rest. For individuals, this means zero-knowledge guarantees you can actually verify. For teams and organizations, it means compliance with data sovereignty requirements, no per-user subscription fees at scale, and the ability to integrate with internal identity providers.

The landscape of self-hosted password managers has matured significantly. Three projects stand out in 2026: **Vaultwarden**, **Passbolt**, and **Psono**. Each takes a different architectural approach, targets different user profiles, and offers distinct trade-offs. This guide compares all three across features, deployment complexity, security model, and usability — and provides step-by-step Docker configurations so you can deploy the one that fits your needs.

---

## The Contenders at a Glance

| Feature | Vaultwarden | Passbolt | Psono |
|---------|-------------|----------|-------|
| **Language / Stack** | Rust | PHP (CakePHP) + MySQL/MariaDB | Python (Django) + PostgreSQL |
| **Compatible Clients** | All official Bitwarden apps | Browser extensions, mobile apps, CLI | Browser extensions, mobile apps, desktop |
| **Database** | SQLite, MySQL, PostgreSQL | MariaDB / MySQL | PostgreSQL |
| **Free Tier / Open Source** | Fully open source (MIT/Apache) | Community Edition (AGPLv3) | Community Edition (Apache 2.0) |
| **Team Features** | Organizations, collections, groups | Teams, roles, permissions, groups | Teams, access control, sharing |
| **Two-Factor Auth** | TOTP, YubiKey, Duo, Email | TOTP, YubiKey, RSA, Authy | TOTP, WebAuthn, FIDO2, YubiKey |
| **Emergency Access** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Password Breach Report** | ✅ Yes (via Have I Been Pwned API) | ✅ Yes | ✅ Yes |
| **CLI Tool** | Via Bitwarden CLI or Vaultwarden CLI | Official `passbolt` CLI | Official `psonocli` |
| **API** | REST (Bitwarden-compatible) | REST + GPG-signed API | REST |
| **Docker Image Size** | ~30 MB | ~500 MB+ | ~400 MB+ |
| **Ideal For** | Individuals, families, small teams | Organizations, enterprises | Technical teams, DevOps |

---

## Vaultwarden: The Lightweight Bitwarden-Compatible Server

Vaultwarden is an unofficial, community-maintained server implementation compatible with all official Bitwarden clients. Written in Rust, it's remarkably lightweight — the Docker image is around 30 MB — and supports the same API as the official Bitwarden server. This means you get the full Bitwarden client experience (browser extensions, mobile apps, desktop apps, CLI) pointed at your own server.

### Key Advantages

- **Minimal resource footprint**: Runs comfortably on a Raspberry Pi or a $5 VPS with 512 MB RAM
- **Full Bitwarden ecosystem**: Every official Bitwarden client works without modification
- **SQLite support**: No external database required for single-user or small-team setups
- **Active development**: Regular updates, strong community, and excellent documentation

### Docker Compose Setup

Here's a production-ready `docker-compose.yml` for Vaultwarden with SQLite, reverse proxy, and automatic HTTPS via Caddy:

```yaml
version: '3.8'

services:
  vaultwarden:
    image: vaultwarden/server:latest
    container_name: vaultwarden
    restart: unless-stopped
    environment:
      # Admin token — generate with: openssl rand -base64 48
      ADMIN_TOKEN: "YOUR_RANDOM_ADMIN_TOKEN"
      # Domain for email invitations and U2F/WebAuthn
      DOMAIN: "https://vault.yourdomain.com"
      # Require email verification before login
      SIGNUPS_VERIFY: "true"
      # SMTP configuration for invitations and 2FA
      SMTP_HOST: "smtp.yourdomain.com"
      SMTP_PORT: "587"
      SMTP_FROM: "noreply@yourdomain.com"
      SMTP_USERNAME: "noreply@yourdomain.com"
      SMTP_PASSWORD: "your_smtp_password"
      SMTP_SECURITY: "starttls"
    volumes:
      - ./vw-data:/data
    networks:
      - vaultwarden-net

  caddy:
    image: caddy:2
    container_name: caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy-data:/data
      - caddy-config:/config
    networks:
      - vaultwarden-net

networks:
  vaultwarden-net:
    driver: bridge

volumes:
  caddy-data:
  caddy-config:
```

The `Caddyfile` for automatic TLS:

```
vault.yourdomain.com {
    reverse_proxy vaultwarden:80
    encode gzip
    log {
        output file /var/log/caddy/access.log
    }
}
```

Start the stack:

```bash
docker compose up -d
```

Visit `https://vault.yourdomain.com/admin` and enter your `ADMIN_TOKEN` to configure sign-up policies, SMTP settings, and view server stats.

### Database Backend Options

For teams or production use, switch from SQLite to PostgreSQL:

```yaml
  vaultwarden:
    image: vaultwarden/server:latest
    environment:
      DATABASE_URL: "postgresql://vw_user:vw_password@postgres:5432/vaultwarden"
      # ... other env vars
    depends_on:
      - postgres

  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: vw_user
      POSTGRES_PASSWORD: vw_password
      POSTGRES_DB: vaultwarden
    volumes:
      - pg-data:/var/lib/postgresql/data

volumes:
  pg-data:
```

### Security Hardening

1. **Disable sign-ups after initial setup**: Set `SIGNUPS_ALLOWED=false` once your accounts are created
2. **Enable domain verification**: `DOMAIN_VERIFICATION: "true"` prevents unauthorized domain associations
3. **Rate limiting**: Configure `IP_HEADER` and use Caddy or Nginx to rate-limit login attempts
4. **Backup your data**: The `/data` directory contains the SQLite database (if used), attachments, and send data. For PostgreSQL, use `pg_dump`

```bash
# Backup script
tar czf vaultwarden-backup-$(date +%Y%m%d).tar.gz ./vw-data/
pg_dump -U vw_user vaultwarden > vaultwarden-db-$(date +%Y%m%d).sql
```

---

## Passbolt: The Open-Source Password Manager Built for Teams

Passbolt takes a fundamentally different approach. While Vaultwarden aims to replicate the Bitwarden experience, Passbolt is designed from the ground up for team collaboration with a strong emphasis on GPG-based encryption. Every password shared within a team is encrypted with the recipient's GPG public key, ensuring that even the server administrator cannot read shared secrets.

### Key Advantages

- **GPG-based end-to-end encryption**: Server never sees plaintext; each user encrypts with the recipient's public key
- **Granular permissions**: Folder-level access control, role-based permissions, and audit logs
- **Compliance-friendly**: Suitable for organizations with strict security requirements (SOC 2, GDPR)
- **Active directory / LDAP integration**: Enterprise-ready authentication in the Pro edition
- **CLI and API**: Full automation support with GPG-signed API requests

### Docker Compose Setup

Passbolt requires MariaDB and has a more involved setup:

```yaml
version: '3.8'

services:
  passbolt-db:
    image: mariadb:11
    container_name: passbolt-db
    restart: unless-stopped
    environment:
      MYSQL_RANDOM_ROOT_PASSWORD: "true"
      MYSQL_DATABASE: "passbolt"
      MYSQL_USER: "passbolt"
      MYSQL_PASSWORD: "CHANGE_THIS_DB_PASSWORD"
    volumes:
      - passbolt-db-data:/var/lib/mysql
    networks:
      - passbolt-net

  passbolt:
    image: passbolt/passbolt:latest-ce
    container_name: passbolt
    restart: unless-stopped
    environment:
      APP_FULL_BASE_URL: "https://passbolt.yourdomain.com"
      DATASOURCES_DEFAULT_HOST: "passbolt-db"
      DATASOURCES_DEFAULT_USERNAME: "passbolt"
      DATASOURCES_DEFAULT_PASSWORD: "CHANGE_THIS_DB_PASSWORD"
      DATASOURCES_DEFAULT_DATABASE: "passbolt"
      EMAIL_TRANSPORT_DEFAULT_HOST: "smtp.yourdomain.com"
      EMAIL_TRANSPORT_DEFAULT_PORT: "587"
      EMAIL_TRANSPORT_DEFAULT_USERNAME: "noreply@yourdomain.com"
      EMAIL_TRANSPORT_DEFAULT_PASSWORD: "your_smtp_password"
      EMAIL_TRANSPORT_DEFAULT_TLS: "true"
      EMAIL_DEFAULT_FROM: "noreply@yourdomain.com"
    volumes:
      - gpg_keys:/etc/passbolt/gpg
      - jwt_keys:/etc/passbolt/jwt
    command: ["/usr/bin/wait-for.sh", "-t", "0", "passbolt-db:3306", "--", "/docker-entrypoint.sh"]
    networks:
      - passbolt-net

  passbolt-nginx:
    image: nginx:alpine
    container_name: passbolt-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - passbolt
    networks:
      - passbolt-net

networks:
  passbolt-net:
    driver: bridge

volumes:
  passbolt-db-data:
  gpg_keys:
  jwt_keys:
```

After starting the containers, run the installation script inside the Passbolt container:

```bash
docker compose exec passbolt su -m -c "/usr/share/php/passbolt/bin/cake \
  passbolt install --no-admin" -s /bin/sh www-data
```

Then create your admin user:

```bash
docker compose exec passbolt su -m -c "/usr/share/php/passbolt/bin/cake \
  passbolt register_user \
  -u admin@yourdomain.com \
  -f Admin \
  -l User \
  -r admin" -s /bin/sh www-data
```

This outputs a URL to complete the setup in your browser, where you'll generate your GPG keypair.

### GPG Key Management

The first-time setup generates a GPG keypair for your admin account. This key is used to decrypt passwords shared with you. For team members, each person generates their own GPG keypair (either in-browser or via the CLI). Passbolt's encryption model means:

- **Shared passwords** are encrypted with each recipient's public key
- **Server storage** only holds encrypted blobs — no single party (including admins) can read all passwords
- **Key recovery** relies on the user's private key backup — losing it means losing access to shared passwords

This is a significant architectural difference from Vaultwarden, where the server holds encrypted vaults that are decrypted client-side with the user's master password.

---

## Psono: The Developer-Focused Password Manager

Psono is a password manager built for technical teams and DevOps workflows. Written in Python with a Django backend, it offers strong security features including client-side encryption, passwordless authentication via WebAuthn, and a robust REST API. What sets Psono apart is its focus on developer workflows: it supports sharing secrets with time-limited access, integrates with CI/CD pipelines, and provides a clean API for automation.

### Key Advantages

- **Developer-first API**: REST API with token-based authentication, designed for CI/CD integration
- **Client-side encryption**: All encryption happens in the browser or client — server never sees plaintext
- **WebAuthn / FIDO2 support**: Passwordless login with hardware security keys
- **Time-limited access**: Grant temporary access to secrets for contractors or short-term projects
- **PostgreSQL backend**: Robust, scalable database with full-text search capabilities

### Docker Compose Setup

```yaml
version: '3.8'

services:
  psono-postgres:
    image: postgres:16-alpine
    container_name: psono-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: psono
      POSTGRES_PASSWORD: "CHANGE_THIS_POSTGRES_PASSWORD"
      POSTGRES_DB: psono
    volumes:
      - psono-pg-data:/var/lib/postgresql/data
    networks:
      - psono-net

  psono-server:
    image: psono/psono-server:latest
    container_name: psono-server
    restart: unless-stopped
    environment:
      DATABASE_URL: "postgresql://psono:CHANGE_THIS_POSTGRES_PASSWORD@psono-postgres:5432/psono"
      EMAIL_FROM: "noreply@yourdomain.com"
      EMAIL_HOST: "smtp.yourdomain.com"
      EMAIL_PORT: "587"
      EMAIL_USER: "noreply@yourdomain.com"
      EMAIL_PASSWORD: "your_smtp_password"
      EMAIL_USE_TLS: "true"
      # Generate with: python3 -c "import os; print(os.urandom(32).hex())"
      SECRET_KEY: "YOUR_64_CHAR_HEX_SECRET"
      # Generate with: python3 -c "import os; print(os.urandom(32).hex())"
      EMAIL_SECRET_SALT: "YOUR_64_CHAR_HEX_SECRET_SALT"
    volumes:
      - psono-server-data:/root/.psono_server
    depends_on:
      - psono-postgres
    networks:
      - psono-net

  psono-web:
    image: psono/psono-web:latest
    container_name: psono-web
    restart: unless-stopped
    environment:
      PSONO_SERVER_URL: "https://psono-server:8000"
    ports:
      - "80:80"
    depends_on:
      - psono-server
    networks:
      - psono-net

networks:
  psono-net:
    driver: bridge

volumes:
  psono-pg-data:
  psono-server-data:
```

After starting the containers, create a superuser:

```bash
docker compose exec psono-server python3 manage.py createsuperuser
```

Then configure the web client by editing the `/root/.psono_server/config.yml` inside the `psono-server` container:

```yaml
# Base URL of the web client
WEBCLIENT_URL: "https://psono.yourdomain.com"
# Enable registration
ALLOW_REGISTRATION: true
# Email verification required
ACTIVATE_BASE_URL: "https://psono-server:8000"
```

Restart the server container to apply changes:

```bash
docker compose restart psono-server
```

### API and CI/CD Integration

Psono's standout feature is its API, designed for automation. Here's how to interact with it:

```bash
# Login and get a session token
curl -X POST https://psono.yourdomain.com/server/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin@yourdomain.com", "password": "your_password"}'

# List all secrets
curl -X GET https://psono.yourdomain.com/server/api/info/secret/ \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"

# Create a new secret
curl -X POST https://psono.yourdomain.com/server/api/secret/create/ \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production DB Password",
    "type": "password",
    "secret_key": "your_encrypted_key_here",
    "secret_data": "your_encrypted_data_here"
  }'
```

For CI/CD pipelines, you can use the `psonocli` tool:

```bash
# Install the CLI
pip install psonocli

# Login
psonocli login --server https://psono.yourdomain.com

# Retrieve a secret (useful in pipeline scripts)
psonocli secret get --name "Production DB Password" --field "password"
```

This makes Psono an excellent choice for teams that need to inject secrets into deployment pipelines without hardcoding them in CI/CD configuration files.

---

## Security Comparison

| Security Feature | Vaultwarden | Passbolt | Psono |
|-----------------|-------------|----------|-------|
| **Encryption Model** | Client-side AES-256 (Bitwarden protocol) | GPG per-recipient encryption | Client-side AES-256 |
| **Master Password Hashing** | PBKDF2 (configurable Argon2id) | PBKDF2-SHA512 | Argon2id |
| **Zero-Knowledge** | ✅ Server cannot decrypt | ✅ Server cannot decrypt | ✅ Server cannot decrypt |
| **2FA Methods** | TOTP, YubiKey OTP/U2F, Duo, Email | TOTP, YubiKey, RSA, Authy | TOTP, WebAuthn, FIDO2 |
| **Audit Logging** | Basic (admin panel) | Comprehensive (all actions) | Comprehensive |
| **Password Breach Check** | Via Have I Been Pwned API | Via Have I Been Pwned API | Built-in breach monitoring |
| **Password Generator** | Configurable (length, symbols, etc.) | Configurable | Configurable |
| **Secure File Attachments** | ✅ Encrypted attachments | ✅ Encrypted file sharing | ✅ Encrypted file sharing |
| **Emergency Access** | ✅ Time-delayed recovery | ✅ Recovery process | ✅ Emergency access |

All three projects implement true zero-knowledge encryption. The server never has access to your master password or the keys needed to decrypt your vault. This is the fundamental security guarantee that makes self-hosting compelling — even if the server is compromised, the attacker only gets encrypted blobs.

---

## Performance and Resource Requirements

For a home lab or small team, all three options are lightweight. Here's a practical comparison of minimum and recommended resources:

| Metric | Vaultwarden | Passbolt | Psono |
|--------|-------------|----------|-------|
| **Minimum RAM** | 256 MB | 1 GB | 1 GB |
| **Recommended RAM** | 512 MB | 2 GB | 2 GB |
| **Disk Space** | 50 MB + attachments | 500 MB + attachments | 200 MB + attachments |
| **CPU** | 1 core (ARM OK) | 1 core | 1 core |
| **Docker Containers** | 1 (or 2 with Caddy) | 3 (app, DB, web server) | 3 (server, DB, web client) |
| **Startup Time** | ~2 seconds | ~15 seconds | ~10 seconds |

Vaultwarden's Rust implementation gives it a significant advantage in resource efficiency. It can run on a Raspberry Pi Zero W and handle dozens of concurrent users. Passbolt and Psono are heavier due to their PHP/Python stacks and mandatory database servers, but they're still well within the capabilities of any modern VPS.

---

## Migration Paths

### From Bitwarden Cloud to Vaultwarden

Vaultwarden is the easiest migration path if you're already using Bitwarden:

```bash
# 1. Export your vault from Bitwarden web app
#    Settings → Tools → Export Vault → JSON format

# 2. Import into Vaultwarden
#    Log in to your Vaultwarden instance
#    Settings → Tools → Import Data → Upload the JSON file
```

Alternatively, use the official Bitwarden CLI to script the migration:

```bash
# Export using CLI
bw sync
bw export --format json --output vault-export.json --session $BW_SESSION

# Import into Vaultwarden
BW_SESSION=$(bw login --raw)
bw import --format json vault-export.json --session $BW_SESSION
```

### From LastPass to Any Self-Hosted Option

All three support CSV import from LastPass:

1. Export from LastPass: **Account Options → Advanced → Export**
2. Import the CSV into your self-hosted password manager through the web interface
3. Verify all entries, especially secure notes and card data
4. Rotate critical passwords after migration (best practice when switching managers)

---

## Which One Should You Choose?

### Choose Vaultwarden if:
- You want the simplest, most resource-efficient deployment
- You already use Bitwarden clients and want to keep them
- You're running on limited hardware (Raspberry Pi, low-end VPS)
- You need individual or family use with basic organization features

### Choose Passbolt if:
- You're deploying for an organization with compliance requirements
- GPG-based per-recipient encryption is a requirement
- You need granular access control and comprehensive audit logging
- Your team is comfortable with GPG key management

### Choose Psono if:
- You need tight CI/CD and API integration for secrets management
- Your team is developer-focused and values automation
- You want time-limited access for contractors and temporary workers
- You prefer passwordless authentication with WebAuthn/FIDO2

For most individuals and small teams, **Vaultwarden** is the pragmatic choice: it's lightweight, compatible with the entire Bitwarden ecosystem, and can be deployed in minutes. For organizations with strict security policies, **Passbolt**'s GPG-based encryption model provides an additional layer of assurance. For DevOps teams managing secrets across infrastructure, **Psono**'s API-first design makes it the natural fit.

All three are actively maintained, open source, and production-ready. The best choice depends on your threat model, team size, and integration requirements. Whatever you choose, self-hosting puts you in control of your most sensitive data — and that's a win regardless of which path you pick.
