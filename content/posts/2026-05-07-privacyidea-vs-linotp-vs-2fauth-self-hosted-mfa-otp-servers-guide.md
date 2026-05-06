---
title: "privacyIDEA vs LinOTP vs 2FAuth: Best Self-Hosted Multi-Factor Authentication Servers 2026"
date: "2026-05-07"
tags: ["comparison", "guide", "self-hosted", "security", "authentication", "privacy"]
draft: false
description: "Compare privacyIDEA, LinOTP, and 2FAuth — three open-source self-hosted multi-factor authentication servers. Learn which MFA platform fits your organization for OTP, TOTP, FIDO2, and push authentication."
---

Multi-factor authentication (MFA) is no longer optional for organizations that take security seriously. Passwords alone are vulnerable to phishing, credential stuffing, and database breaches. Adding a second factor — typically a time-based one-time password (TOTP), push notification, or hardware security key — blocks the vast majority of account takeover attacks.

While cloud-based MFA providers like Duo, Okta Verify, and Authy dominate the market, many organizations need to self-host their authentication infrastructure. Regulatory requirements, data sovereignty laws, and the principle of keeping authentication data under your own control drive the demand for open-source MFA servers. This guide compares privacyIDEA, LinOTP, and 2FAuth — three mature, actively maintained self-hosted MFA solutions.

## Comparison Table

| Feature | privacyIDEA | LinOTP | 2FAuth |
|---------|-------------|--------|--------|
| **License** | AGPLv3 | AGPLv3 | AGPLv3 |
| **GitHub Stars** | 1,700+ | 540+ | 3,900+ |
| **Language** | Python | Python | PHP (Laravel) |
| **Supported Protocols** | TOTP, HOTP, OCRA, mOTP, FIDO2, WebAuthn, SAML | TOTP, HOTP, mOTP, OCRA, TiQR | TOTP, HOTP, Steam |
| **Hardware Tokens** | YubiKey, Nitrokey, RSA, Feitian | YubiKey, Nitrokey, generic OTP | N/A (software only) |
| **LDAP/AD Integration** | Yes (user resolver) | Yes | Via OAuth providers |
| **RADIUS Server** | Yes (built-in) | Yes | No |
| **SMPP Gateway** | Yes (SMS tokens) | Yes | No |
| **Push Authentication** | Via PushTok app | Via TiQR app | No |
| **REST API** | Yes (comprehensive) | Yes | Yes |
| **Web UI** | Admin + Self-service | Minimal admin | User management UI |
| **Docker Support** | Community images | Official compose | Official Dockerfile |
| **Database** | MySQL, PostgreSQL, SQLite | MySQL, PostgreSQL, SQLite | MySQL, PostgreSQL |
| **Best For** | Enterprise MFA with hardware tokens | Legacy OTP infrastructure | Personal/small-team TOTP management |

## privacyIDEA

privacyIDEA is the most feature-rich self-hosted MFA platform. Originally developed for the German education sector, it has grown into a comprehensive authentication server supporting dozens of token types, multiple user backends, and enterprise-grade features like RADIUS integration and SMPP SMS gateways.

### Key Features

- **Extensive token support**: TOTP, HOTP, OCRA, mOTP, FIDO2/WebAuthn, SAML, TiQR push, and over 20 hardware token types including YubiKey, Nitrokey, and RSA SecurID.
- **RADIUS server**: Built-in RADIUS server allows privacyIDEA to act as a drop-in replacement for existing RADIUS-based MFA infrastructure, including VPN and network access authentication.
- **LDAP/Active Directory integration**: Connects to existing directory services for user authentication and group-based token assignment policies.
- **Policy engine**: Fine-grained policies control which users can enroll which token types, set token lifetimes, configure PIN requirements, and define challenge-response flows.
- **Audit logging**: Comprehensive audit trail of all authentication events, token enrollments, and administrative actions.
- **SMPP SMS gateway**: Send OTP codes via SMS through any SMPP-compatible provider.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  privacyidea:
    image: netknightsit/privacyidea:latest
    environment:
      - PI_PEPPER=change-me-to-a-random-string
      - PI_ENCFILE=/etc/privacyidea/enckey
      - PI_LOGLEVEL=INFO
    volumes:
      - pi-data:/etc/privacyidea
      - pi-enckey:/etc/privacyidea/enckey
    ports:
      - "5000:5000"
    depends_on:
      - privacyidea-db
    networks:
      - mfa

  privacyidea-db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=privacyidea
      - POSTGRES_USER=pi
      - POSTGRES_PASSWORD=***
    volumes:
      - pi-db-data:/var/lib/postgresql/data
    networks:
      - mfa

volumes:
  pi-data:
  pi-enckey:
  pi-db-data:

networks:
  mfa:
    driver: bridge
```

### When to Choose privacyIDEA

privacyIDEA is the best choice for organizations that need enterprise-grade MFA with hardware token support, RADIUS integration, and comprehensive policy management. It is particularly well-suited for environments that must integrate with existing Active Directory infrastructure and need to support multiple token types across different user groups.

## LinOTP

LinOTP is one of the oldest open-source OTP servers, developed by LinOTP.org (formerly LSE Leading Security Experts GmbH). It focuses on reliable OTP token management with support for hardware tokens, mobile apps, and legacy systems.

### Key Features

- **Proven reliability**: Over 15 years of development and deployment in production environments worldwide.
- **Hardware token support**: Full support for YubiKey, Nitrokey, and generic OTP hardware tokens via USB and HID interfaces.
- **TiQR push authentication**: Supports the TiQR mobile app for push-based authentication as an alternative to TOTP.
- **LDAP integration**: Connects to LDAP and Active Directory for user management and authentication.
- **RADIUS integration**: Acts as a RADIUS server for network access authentication and VPN MFA.
- **Simple architecture**: Straightforward deployment with a single service and standard database backend.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  linotp:
    image: linotp/linotp:latest
    environment:
      - LINOTP_ADMIN_PASSWORD=***
      - LINOTP_DB_PASSWORD=***
    volumes:
      - linotp-data:/var/lib/linotp
    ports:
      - "8080:8080"
    depends_on:
      - linotp-db
    networks:
      - mfa

  linotp-db:
    image: mariadb:11
    environment:
      - MYSQL_ROOT_PASSWORD=***
      - MYSQL_DATABASE=linotp
      - MYSQL_USER=linotp
      - MYSQL_PASSWORD=***
    volumes:
      - linotp-db-data:/var/lib/mysql
    networks:
      - mfa

volumes:
  linotp-data:
  linotp-db-data:

networks:
  mfa:
    driver: bridge
```

### When to Choose LinOTP

LinOTP is the right choice for organizations that prioritize stability and proven reliability. Its long track record in production environments and straightforward architecture make it suitable for teams that need a dependable OTP server without the complexity of a full policy engine.

## 2FAuth

2FAuth takes a fundamentally different approach from privacyIDEA and LinOTP. Instead of being a full MFA infrastructure server, it is a self-hosted web application that manages your TOTP secrets and generates one-time passwords. Think of it as a self-hosted alternative to Google Authenticator or Authy with a web interface.

### Key Features

- **Web-based TOTP management**: Store and manage all your TOTP secrets in a single web application accessible from any browser.
- **QR code scanning**: Upload QR codes or manually enter TOTP secrets to enroll tokens.
- **User accounts**: Multi-user support with individual token collections and access controls.
- **API**: REST API for programmatic token management and integration with other tools.
- **Dark mode**: Modern UI with dark theme support.
- **Docker deployment**: Official Docker image with minimal configuration.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  twofauth:
    image: 2fauth/2fauth:latest
    environment:
      - APP_NAME=2FAuth
      - APP_KEY=base64:your-random-key-here
      - DB_CONNECTION=sqlite
    volumes:
      - twofauth-data:/2fauth
    ports:
      - "8000:8000"
    restart: unless-stopped

volumes:
  twofauth-data:
```

### When to Choose 2FAuth

2FAuth is the right choice for individuals and small teams who want to self-host their TOTP token management without running a full MFA infrastructure server. It replaces cloud-based authenticator apps with a self-controlled alternative.

## Security Considerations

### Token Storage

All three platforms encrypt TOTP secrets at rest. privacyIDEA uses an encryption key file, LinOTP encrypts database fields, and 2FAuth uses Laravel's built-in encryption. The critical operational requirement is protecting these encryption keys with proper access controls and backup procedures.

### Rate Limiting

Brute-force attacks against OTP codes are a constant threat. All three platforms support rate limiting on authentication endpoints. privacyIDEA has the most configurable rate limiting with per-user, per-token, and per-IP policies.

### Backup and Recovery

MFA servers are critical infrastructure. Regular database backups and encryption key backups are mandatory. For privacyIDEA and LinOTP, also back up the enckey files. Loss of encryption keys means loss of access to all enrolled tokens.

## Why Self-Host Your MFA Server?

Self-hosting your multi-factor authentication infrastructure keeps sensitive authentication data under your direct control. Cloud MFA providers collect metadata about your authentication patterns, user counts, and geographic distribution. For regulated industries, self-hosting satisfies data residency requirements and eliminates third-party dependencies for a security-critical component.

Additionally, self-hosted MFA servers integrate with existing identity infrastructure — LDAP directories, SSO providers, and RADIUS-based network access — without requiring data to leave your network.

For complementary identity management guides, see our [SSO comparison](../2026-04-21-casdoor-vs-zitadel-vs-authentik-lightweight-sso-guide-2026/) and [OIDC SSO providers guide](../2026-04-25-dex-vs-kanidm-vs-rauthy-self-hosted-oidc-sso-guide-2026/) for building a complete self-hosted authentication stack.

## Frequently Asked Questions

### What is the difference between TOTP and HOTP?

TOTP (Time-based One-Time Password) generates codes that expire every 30 seconds based on the current time. HOTP (HMAC-based One-Time Password) generates codes that increment with each use. TOTP is more common because it does not require synchronization between client and server, while HOTP is useful for hardware tokens without real-time clocks.

### Can I migrate from Google Authenticator to a self-hosted MFA server?

Yes. Google Authenticator stores TOTP secrets as QR codes or manual entry strings. You can scan the same QR codes into privacyIDEA, LinOTP, or 2FAuth. For bulk migration, privacyIDEA supports CSV token import, and 2FAuth supports QR code image uploads.

### Is self-hosted MFA secure enough for enterprise use?

privacyIDEA and LinOTP are both deployed in enterprise environments with hundreds of thousands of users. They support FIPS-compliant encryption, hardware security modules, audit logging, and integration with enterprise directory services. The security of your deployment depends on proper hardening, regular updates, and secure key management.

### Can I use self-hosted MFA with VPN and SSH?

Yes. privacyIDEA and LinOTP both include RADIUS servers that can authenticate VPN connections (OpenVPN, WireGuard, Cisco AnyConnect) and SSH sessions (via PAM integration). 2FAuth does not include a RADIUS server but can integrate with SSH via TOTP PAM modules.

### What happens if the MFA server goes down?

Most MFA servers support hot-standby configurations. privacyIDEA and LinOTP can be deployed in active-passive mode with shared database storage. For high-availability deployments, use a clustered database backend (PostgreSQL with streaming replication or MySQL with Group Replication) and load-balance the application tier.

### Does 2FAuth replace Duo or Authy?

2FAuth replaces the token management aspect of these services — it stores your TOTP secrets and generates codes. It does not provide push notifications, SMS delivery, or RADIUS integration like privacyIDEA and LinOTP do. For full enterprise MFA features, privacyIDEA or LinOTP are more appropriate.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "privacyIDEA vs LinOTP vs 2FAuth: Best Self-Hosted Multi-Factor Authentication Servers 2026",
  "description": "Compare privacyIDEA, LinOTP, and 2FAuth - three open-source self-hosted multi-factor authentication servers for OTP, TOTP, FIDO2, and push authentication.",
  "datePublished": "2026-05-07",
  "dateModified": "2026-05-07",
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
