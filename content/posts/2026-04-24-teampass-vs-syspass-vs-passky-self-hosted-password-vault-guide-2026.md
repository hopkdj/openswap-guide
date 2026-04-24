---
title: "TeamPass vs SysPass vs Passky: Best Self-Hosted Password Vault 2026"
date: 2026-04-24
tags: ["comparison", "guide", "self-hosted", "security", "password-manager"]
draft: false
description: "Compare TeamPass, SysPass, and Passky — three open-source self-hosted password vault solutions for teams and individuals. Includes Docker deployment guides, feature comparisons, and security analysis."
---

Managing passwords across a team or organization requires more than a personal password manager. When you need centralized control, shared credential storage, and audit trails, a self-hosted password vault becomes essential. This guide compares three open-source solutions — **TeamPass**, **SysPass**, and **Passky** — to help you choose the right tool for your infrastructure.

## Why Self-Host a Password Vault

Cloud-based password managers are convenient, but they come with inherent trade-offs: your encryption keys live on someone else's servers, you have limited visibility into data handling practices, and vendor lock-in makes migration painful.

A self-hosted password vault gives you complete control over your credentials. Your data never leaves your infrastructure, you define the backup strategy, and you can integrate with your existing authentication providers. For regulated industries (finance, healthcare, government), self-hosting is often a compliance requirement.

For related reading, see our [complete guide to self-hosted secret management](../best-self-hosted-secret-management-vault-infisical-passbolt-2026/) and [Vaultwarden vs Passbolt vs Psono comparison](../vaultwarden-vs-passbolt-vs-psono/) for broader password manager alternatives.

## Overview: TeamPass vs SysPass vs Passky

| Feature | TeamPass | SysPass | Passky |
|---------|----------|---------|--------|
| **GitHub Stars** | 1,789 | 993 | 243 (server) |
| **Last Updated** | April 2026 | December 2024 | November 2025 |
| **Language** | PHP | PHP | PHP |
| **Database** | MariaDB/MySQL | MySQL/MariaDB | SQLite/MySQL |
| **Docker Support** | Official image | Community setups | Official image |
| **Team Sharing** | Yes (role-based) | Yes (profile-based) | Yes (shared vaults) |
| **Two-Factor Auth** | Yes (TOTP) | Yes (TOTP) | Yes (TOTP, YubiKey) |
| **API** | REST API | REST API | REST API |
| **Password Generator** | Yes | Yes | Yes |
| **Audit Logging** | Yes | Yes | Basic |
| **LDAP/AD Integration** | Yes | Yes | No |
| **Encryption** | AES-256 (server-side) | AES-256 (server-side) | Argon2id + XChaCha20 |
| **License** | GPL-3.0 | GPL-3.0 | GPL-3.0 |

### TeamPass

TeamPass is the most mature of the three, with over 15 years of development. It provides a comprehensive collaborative password management system with hierarchical folder structures, role-based access control, and extensive logging. The project recently received a major Docker overhaul with official container images, making deployment significantly easier.

### SysPass

SysPass is a systems-focused password manager designed for IT administrators who need to manage credentials for servers, network devices, and applications. It features a clean web interface, custom field support, and notification plugins for credential expiry alerts. While development has slowed (last update December 2024), the core functionality remains solid.

### Passky

Passky is the newest entry, offering a modern architecture with Argon2id key derivation and XChaCha20 encryption. It supports both self-hosting and a managed cloud tier. The server component is lightweight and can run on minimal hardware. While it has fewer stars than its competitors, its encryption model is arguably the most modern of the three.

## Docker Deployment Guides

### TeamPass Docker Compose

TeamPass offers an official Docker image (`teampass/teampass`) with a complete Docker Compose setup that includes MariaDB:

```yaml
services:
  teampass:
    image: teampass/teampass:latest
    container_name: teampass-app
    restart: unless-stopped
    environment:
      DB_HOST: db
      DB_PORT: 3306
      DB_NAME: teampass
      DB_USER: teampass
      DB_PASSWORD: ${DB_PASSWORD}
      INSTALL_MODE: manual
      ADMIN_EMAIL: admin@teampass.local
      TEAMPASS_URL: http://localhost
      PHP_MEMORY_LIMIT: 512M
    volumes:
      - teampass-sk:/var/www/html/sk
      - teampass-files:/var/www/html/files
      - teampass-upload:/var/www/html/upload
    ports:
      - "8080:80"
    networks:
      - teampass-network
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  db:
    image: mariadb:11.2
    container_name: teampass-db
    restart: unless-stopped
    environment:
      MARIADB_ROOT_PASSWORD: ${MARIADB_ROOT_PASSWORD}
      MARIADB_DATABASE: teampass
      MARIADB_USER: teampass
      MARIADB_PASSWORD: ${DB_PASSWORD}
    volumes:
      - teampass-db:/var/lib/mysql
    networks:
      - teampass-network
    healthcheck:
      test: ["CMD", "healthcheck.sh", "--connect", "--innodb_initialized"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    command:
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_unicode_ci
      - --max_allowed_packet=64M

networks:
  teampass-network:
    driver: bridge

volumes:
  teampass-sk:
  teampass-files:
  teampass-upload:
  teampass-db:
```

Deploy with:

```bash
# Create .env file
cat > .env << 'ENVEOF'
DB_PASSWORD=your-secure-db-password
MARIADB_ROOT_PASSWORD=your-root-password
ENVEOF

# Start services
docker compose up -d

# Access at http://localhost:8080 and complete the web installer
```

### SysPass Docker Deployment

SysPass does not have an official Docker image, but you can deploy it using a standard LAMP stack. Here's a production-ready Docker Compose configuration:

```yaml
services:
  syspass:
    image: php:8.2-apache
    container_name: syspass-app
    restart: unless-stopped
    volumes:
      - syspass-data:/var/www/html
      - ./syspass.conf:/etc/apache2/sites-available/syspass.conf
    ports:
      - "8081:80"
    depends_on:
      - db
    environment:
      - APACHE_DOCUMENT_ROOT=/var/www/html

  db:
    image: mariadb:11.2
    container_name: syspass-db
    restart: unless-stopped
    environment:
      MARIADB_ROOT_PASSWORD: ${MARIADB_ROOT_PASSWORD}
      MARIADB_DATABASE: syspass
      MARIADB_USER: syspass
      MARIADB_PASSWORD: ${DB_PASSWORD}
    volumes:
      - syspass-db:/var/lib/mysql

volumes:
  syspass-data:
  syspass-db:
```

Installation steps:

```bash
# Download the latest SysPass release
SYS_PASS_VERSION="3.2.3"
curl -L "https://github.com/nuxsmin/sysPass/releases/download/${SYS_PASS_VERSION}/syspass.tar.gz" \
  -o syspass.tar.gz

# Extract to the Docker volume
docker volume create syspass-data
docker run --rm -v syspass-data:/data -v "$(pwd):/src" alpine \
  tar xzf /src/syspass.tar.gz -C /data --strip-components=1

# Create .env file
cat > .env << 'ENVEOF'
MARIADB_ROOT_PASSWORD=your-root-password
DB_PASSWORD=your-secure-db-password
ENVEOF

# Start services
docker compose up -d
```

### Passky Docker Compose

Passky provides the simplest deployment — a single container with an optional external database:

```yaml
services:
  passky-server:
    container_name: passky-server
    image: rabbitcompany/passky-server:latest
    restart: unless-stopped
    environment:
      - ADMIN_USERNAME=admin
      - ADMIN_PASSWORD=${ADMIN_PASSWORD}
      - DATABASE_ENGINE=mysql
      - MYSQL_HOST=db
      - MYSQL_PORT=3306
      - MYSQL_DATABASE=passky
      - MYSQL_USER=passky
      - MYSQL_PASSWORD=${DB_PASSWORD}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - MAIL_ENABLED=false
      - ACCOUNT_MAX_PASSWORDS=500
      - LIMITER_ENABLED=true
    ports:
      - "8082:80"
    volumes:
      - passky-db:/var/www/html/databases
    depends_on:
      - db
      - redis

  db:
    image: mariadb:11.2
    container_name: passky-db
    restart: unless-stopped
    environment:
      MARIADB_ROOT_PASSWORD: ${MARIADB_ROOT_PASSWORD}
      MARIADB_DATABASE: passky
      MARIADB_USER: passky
      MARIADB_PASSWORD: ${DB_PASSWORD}
    volumes:
      - passky-mysql:/var/lib/mysql

  redis:
    image: redis:7-alpine
    container_name: passky-redis
    restart: unless-stopped
    volumes:
      - passky-redis:/data

volumes:
  passky-db:
  passky-mysql:
  passky-redis:
```

Deploy:

```bash
cat > .env << 'ENVEOF'
ADMIN_PASSWORD=your-admin-password
DB_PASSWORD=your-db-password
MARIADB_ROOT_PASSWORD=your-root-password
ENVEOF

docker compose up -d
```

## Feature Comparison in Detail

### Security Architecture

**TeamPass** uses server-side AES-256 encryption with a salt key stored on the filesystem. Each user has a personal encryption key derived from their password. The architecture is battle-tested but relies on PHP's OpenSSL extension.

**SysPass** also uses AES-256 with server-side encryption. It supports profile-based access control where administrators can define which users can view, edit, or delete specific password entries. It supports TLS for database connections.

**Passky** uses the most modern cryptographic stack: Argon2id for key derivation and XChaCha20-Poly1305 for encryption. This provides better resistance against brute-force attacks compared to standard AES-256. Passky also supports YubiKey hardware tokens for two-factor authentication.

### Team Collaboration

**TeamPass** excels in team collaboration with its hierarchical folder system. Administrators can create nested folder structures and assign read/write/admin permissions at each level. It supports password expiry policies, automatic rotation reminders, and detailed audit logs tracking every access event.

**SysPass** uses a profile-based permission model. You define customer profiles and assign users to profiles, controlling access to password entries through profile membership. It supports custom fields for storing additional metadata like IP addresses, SSH keys, or API tokens.

**Passky** offers shared vaults with simpler permission management. Users can create shared vaults and invite other users with read or read-write access. While less granular than TeamPass, it's easier to set up for small teams.

### API and Integrations

**TeamPass** provides a REST API for programmatic access to password entries. It supports LDAP and Active Directory authentication, making it suitable for enterprise deployments. The API allows you to create, read, update, and delete password entries programmatically.

**SysPass** also offers a REST API and supports LDAP authentication. It has a plugin system for extending functionality, including notification plugins that can send alerts via email or webhooks when passwords are about to expire.

**Passky** has a REST API but currently lacks LDAP/AD integration. It does support Cloudflare Turnstile CAPTCHA and YubiKey for enhanced login security.

### Backup and Recovery

**TeamPass** stores encrypted passwords in a MariaDB database with file-based salt keys. Backup requires dumping both the database and the `sk/` directory. The project includes migration guides for moving between versions.

**SysPass** stores data in MySQL/MariaDB. The application includes a built-in backup feature that can export encrypted database dumps. Recovery requires the encryption key used during backup creation.

**Passky** supports both SQLite (for single-server setups) and MySQL (for production). With SQLite, a single file backup captures everything. With MySQL, you need standard database dumps. The encryption model ensures that backups are secure even if the file is compromised.

## When to Choose Each Tool

**Choose TeamPass if:**
- You need comprehensive team collaboration with granular permissions
- LDAP/Active Directory integration is required
- You want the most actively maintained solution (updated April 2026)
- Audit logging and compliance features are important
- You have a team of 10+ people managing shared credentials

**Choose SysPass if:**
- You need custom fields for IT infrastructure metadata
- Profile-based access control matches your organizational structure
- You need password expiry notifications and alerts
- You prefer a simpler, more focused tool without enterprise complexity

**Choose Passky if:**
- You want the most modern encryption (Argon2id + XChaCha20)
- You need a lightweight, easy-to-deploy solution
- YubiKey hardware token support is important
- You're a small team that doesn't need LDAP integration
- You prefer a minimalist interface with no configuration overhead

## Reverse Proxy Setup

For production deployments, all three should sit behind a reverse proxy with TLS. Here's an Nginx configuration for TeamPass:

```nginx
server {
    listen 443 ssl http2;
    server_name teampass.example.com;

    ssl_certificate /etc/nginx/ssl/teampass.crt;
    ssl_certificate_key /etc/nginx/ssl/teampass.key;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
    }
}
```

## Frequently Asked Questions

### Is TeamPass actively maintained?

Yes. As of April 2026, TeamPass's GitHub repository shows commits within the last week, and the project received a major Docker overhaul in early 2026 with official container images on Docker Hub. The project has been actively developed since 2009.

### Can I migrate from KeePass to TeamPass?

Yes. TeamPass includes import functionality for KeePass XML exports. You can export your KeePass database to XML format and import it through the TeamPass admin panel. SysPass also supports KeePass imports.

### Does Passky work offline?

Passky's browser extension and desktop app cache your vault locally, allowing read-only access when offline. Changes are synced when connectivity is restored. The server must be reachable for authentication and synchronization.

### Which password vault is most secure?

All three use strong encryption, but Passky has the most modern cryptographic stack (Argon2id key derivation + XChaCha20-Poly1305 encryption). TeamPass and SysPass use AES-256, which is also considered secure. The biggest security factor is your deployment: ensure TLS is enforced, strong admin passwords are set, and regular backups are tested.

### Can I use LDAP authentication with Passky?

No, Passky currently does not support LDAP or Active Directory integration. If LDAP/AD is a requirement, TeamPass or SysPass are better choices. Both support LDAP authentication out of the box.

### How do I backup these password vaults?

For TeamPass: backup the MariaDB database (`mysqldump`) and the `sk/` directory containing the salt key. For SysPass: use the built-in backup feature or dump the MySQL database. For Passky: if using SQLite, backup the database file; if using MySQL, use standard database dumps. Always store backups encrypted and test restoration regularly.

### Is SysPass still being developed?

SysPass's last major release was in December 2024. While the project is not as actively maintained as TeamPass, the core functionality is stable and production-ready. Community contributions continue to address bugs and minor improvements.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "TeamPass vs SysPass vs Passky: Best Self-Hosted Password Vault 2026",
  "description": "Compare TeamPass, SysPass, and Passky — three open-source self-hosted password vault solutions for teams and individuals. Includes Docker deployment guides, feature comparisons, and security analysis.",
  "datePublished": "2026-04-24",
  "dateModified": "2026-04-24",
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
