---
title: "privacyIDEA vs LinOTP: Self-Hosted MFA Server Comparison 2026"
date: 2026-04-19
tags: ["comparison", "guide", "self-hosted", "security", "mfa", "2fa", "authentication"]
draft: false
description: "Compare privacyIDEA and LinOTP for self-hosted multi-factor authentication. Docker setup guides, token types, RADIUS integration, and enterprise deployment comparison."
---

Multi-factor authentication (MFA) is one of the most effective security controls you can deploy. But relying on cloud-based MFA providers like Duo, Authy, or Okta means your authentication flow depends on third-party infrastructure — and their terms, pricing, and availability.

Self-hosted MFA servers give you full control over your authentication infrastructure. Your tokens never leave your network, your user data stays on your servers, and you avoid vendor lock-in entirely. In this guide, we compare the two leading open-source MFA server platforms: **privacyIDEA** and **LinOTP**.

Both are mature Python-based projects with support for TOTP, HOTP, SMS, email OTP, and hardware tokens. But they differ significantly in architecture, deployment com[plex](https://www.plex.tv/)ity, and enterprise features.

## Why Self-Host Your MFA Server?

Running your own MFA infrastructure offers several advantages over managed services:

- **Data sovereignty**: Token seeds, user mappings, and authentication logs never leave your infrastructure
- **No per-user pricing**: Cloud MFA providers charge per active user — self-hosted solutions cost only your server resources
- **Network isolation**: Deploy MFA servers inside your internal network, accessible only to your applications
- **Custom integrations**: Full API access and RADIUS/PAM modules for integrating with any system
- **Compliance**: Meet regulatory requirements (GDPR, HIPAA, SOC 2) that mandate on-premise authentication infrastructure
- **Resilience**: No dependency on external provider uptime — your MFA works as long as your servers are up

For organizations running their own identity providers, directory services, or applications with sensitive access controls, self-hosted MFA is the natural complement to an [authentic self-hosted IAM strategy](../zitadel-vs-ory-vs-keycloak-self-hosted-iam-guide/).

## Overview: privacyIDEA vs LinOTP

| Feature | privacyIDEA | LinOTP |
|---|---|---|
| GitHub Stars | ~1,700+ | ~540+ |
| Last Active | April 2026 | April 2026 |
| Language | Python | Python |
| Licens[docker](https://www.docker.com/)PLv3 | AGPLv3 |
| Docker Support | Official dev compose | Official compose.yaml |
| Web UI | Built-in admin + user portal | Basic admin interface |
| Token Types | 15+ types | 10+ types |
| RADIUS Server | Built-in | Via separate module |
| REST API | Full OpenAPI/Swagger | JSON REST API |
| Multi-tenancy | Yes (realms, resolvers) | Yes (realms) |
| User Resolvers | LDAP/AD, SQL, SCIM, HTTP | LDAP/AD, SQL, flat files |
| PAM Module | Yes | Yes |
| Certificate Auth | Yes (mTLS, client certs) | Limited |
| FIDO2/WebAuthn | Full support | No native support |
| Push Notifications | Via Firebase | No |
| Reporting/Audit | Built-in audit log + reports | Basic audit logging |
| Commercial Support | NetKnights GmbH | LSE Leading Security Experts |

## privacyIDEA: Feature-Rich MFA Platform

privacyIDEA is the more actively developed of the two projects, with regular releases and a comprehensive feature set. Developed by NetKnights GmbH, it supports virtually every token type you might need and includes a polished web administration interface.

### Supported Token Types

privacyIDEA supports an extensive range of authentication methods:

- **HOTP/TOTP** — RFC-compliant time-based and counter-based one-time passwords
- **HMAC-based challenge-response** — for hardware tokens
- **FIDO2/WebAuthn** — passwordless authentication with security keys and passkeys
- **Certificate tokens** — X.509 client certificate authentication
- **SMS/Email OTP** — one-time passwords delivered via text or email
- **Push tokens** — mobile app push notifications (Firebase integration)
- **mOTP** — mobile one-time password for older devices
- **YubiKey** — OTP and challenge-response modes
- **Remote tokens** — delegate authentication to another privacyIDEA instance
- **Registration tokens** — single-use enrollment tokens
- **Indexed** and **Application-specific** passwords

### Deploying privacyIDEA with Docker

The official repository includes a development `docker-compose.dev.yml` that demonstrates the full stack. Here's a production-oriented adaptation using PostgreSQL:

```yaml
services:
  privacyidea-db:
    image: postgres:17
    container_name: privacyidea-db
    environment:
      POSTGRES_DB: privacyidea
      POSTGRES_USER: privacyidea
      POSTGRES_PASSWORD: ${PI_DB_PASSWORD:-SuperSecret123}
    volumes:
      - privacyidea-db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U privacyidea"]
      interval: 10s
      timeout: 5s
      retries: 5

  privacyidea:
    image: privacyidea/privacyidea:latest
    container_name: privacyidea
    ports:
      - "5000:5000"
    environment:
      PI_ENCFILE: /etc/privacyidea/enckey
      PI_LOGFILE: /var/log/privacyidea/privacyidea.log
      PI_DB_DRIVER: postgresql
      PI_DB_HOST: privacyidea-db
      PI_DB_NAME: privacyidea
      PI_DB_USER: privacyidea
      PI_DB_PASSWORD: ${PI_DB_PASSWORD:-SuperSecret123}
      PI_ADMIN_USER: admin
      PI_ADMIN_PASSWORD: ${PI_ADMIN_PASSWORD:-AdminPass456}
    volumes:
      - privacyidea-data:/etc/privacyidea
      - privacyidea-logs:/var/log/privacyidea
    depends_on:
      privacyidea-db:
        condition: service_healthy

volumes:
  privacyidea-db-data:
  privacyidea-data:
  privacyidea-logs:
```

For production deployments, add a reverse proxy (Nginx or Caddy) with TLS termination, and consider separating the encryption key (`enckey`) onto a secure volume with restricted access.

### LDAP/Active Directory Integration

privacyIDEA connects to existing directory services through its **resolver** and **realm** system. You create a resolver pointing to your LDAP/AD server, then map it to a realm that users authenticate against:

```bash
# Via the privacyIDEA CLI (pi-manage)
pi-manage resolver create ldap_resolver --type ldapresolver \
  --config LDAPURI="ldap://dc01.example.com" \
  --config LDAPBASE="dc=example,dc=com" \
  --config BINDDN="cn=pi-bind,ou=services,dc=example,dc=com" \
  --config BINDPW="${LDAP_BIND_PASSWORD}" \
  --config LOGINNAMEATTRIBUTE="sAMAccountName" \
  --config LDAPSEARCHFILTER="(objectClass=person)" \
  --config USERINFO='{"username": "sAMAccountName", "email": "mail", "givenname": "givenName", "surname": "sn", "phone": "telephoneNumber"}'

# Create a realm from the resolver
pi-manage realm create example_com -r ldap_resolver
```

This allows privacyIDEA to authenticate against your existing user directory without duplicating user accounts. Token assignments and MFA policies are then layered on top of the directory users.

## LinOTP: Lightweight Two-Factor Authentication

LinOTP is one of the oldest open-source MFA servers, originally developed by LSE (Leading Security Experts) in Germany. It focuses on core two-factor authentication with a simpler architecture that's easier to deploy for organizations that don't need the breadth of features privacyIDEA offers.

### Supported Token Types

LinOTP covers the essential MFA methods:

- **HOTP/TOTP** — standard one-time passwords (RFC 4226, RFC 6238)
- **mOTP** — mobile OTP for legacy devices
- **SMS/Email OTP** — one-time password delivery via gateway
- **YubiKey** — OTP mode support
- **TiQR** — QR-based authentication via mobile app
- **u2f** — limited U2F support (not full FIDO2/WebAuthn)
- **Remote token** — delegate to external OTP servers
- **SPASS** — static password for testing

### Deploying LinOTP with Docker

LinOTP provides an official `compose.yaml` in its repository. Here's a simplified production-ready configuration:

```yaml
services:
  linotp-db:
    image: postgres:17
    container_name: linotp-db
    environment:
      POSTGRES_DB: linotp
      POSTGRES_USER: linotp
      POSTGRES_PASSWORD: ${LINOTP_DB_PASSWORD:-SecurePass789}
    volumes:
      - linotp-db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U linotp"]
      interval: 10s
      timeout: 5s
      retries: 5

  linotp:
    image: linotp/linotp:latest
    container_name: linotp
    ports:
      - "8080:8080"
    environment:
      LINOTP_DB_URI: postgresql://linotp:${LINOTP_DB_PASSWORD:-SecurePass789}@linotp-db:5432/linotp
      LINOTP_AUDIT_DB_URI: sqlite:////var/lib/linotp/audit.sqlite
      LINOTP_ENCFILE: /etc/linotp/encryptKey.pem
      LINOTP_ADMIN_USER: admin
      LINOTP_ADMIN_PASSWORD: ${LINOTP_ADMIN_PASSWORD:-AdminLinOTP456}
    volumes:
      - linotp-config:/etc/linotp
      - linotp-audit:/var/lib/linotp
    depends_on:
      linotp-db:
        condition: service_healthy

volumes:
  linotp-db-data:
  linotp-config:
  linotp-audit:
```

LinOTP's architecture separates the core engine from its management interface, making it straightforward to scale the authentication engine independently if needed.

### RADIUS Integration

Both platforms support RADIUS, but the approaches differ. privacyIDEA ships with a built-in RADIUS server that you can deploy as a standalone service. LinOTP uses the `linotp-radiustoken` module that plugs into the core:

```bash
# privacyIDEA RADIUS server configuration
# In pi.cfg or via admin UI:
# RADIUS_SERVER = 0.0.0.0
# RADIUS_PORT = 1812
# RADIUS_SECRET = your-radius-secret

# Then configure your network device (switch, firewall, VPN) to point
# to the privacyIDEA RADIUS server for 802.1X authentication.
```

For VPN, switch, or wireless authentication via RADIUS, privacyIDEA's built-in server requires less configuration than LinOTP's modular approach.

## Head-to-Head Comparison

### Deployment and Operations

privacyIDEA's Docker setup is more mature, with official images and a documented production deployment guide. The admin web interface is comprehensive — you can manage users, tokens, policies, and audit logs entirely through the browser. LinOTP's admin interface is more basic, and some configuration still requires command-line tools or direct config file edits.

For teams that want a web-first management experience, privacyIDEA is the clear winner. For environments where configuration-as-code is preferred, LinOTP's simpler architecture may appeal.

### Token and Authentication Flexibility

privacyIDEA supports significantly more token types, including FIDO2/WebAuthn for passwordless authentication — a critical capability if you're also evaluating [passkey and WebAuthn solutions](../self-hosted-passkey-webauthn-authentication-solutions-2026/) for your organization. The certificate token support is also notable for zero-trust environments where mTLS and client certificates are part of the authentication chain.

LinOTP covers all the essential MFA types but lacks native FIDO2 and certificate authentication. If your use case is strictly TOTP/HOTP for application MFA, LinOTP is sufficient. If you need passwordless or certificate-based flows, privacyIDEA is necessary.

### Multi-Tenancy and Policy Engine

Both platforms support realms for multi-tenant deployments. privacyIDEA goes further with:

- **Scoped policies**: Apply different MFA requirements per realm, user group, or client application
- **Token policies**: Set token lifetime, PIN complexity, and auto-enrollment rules per policy scope
- **Event handlers**: Trigger actions on authentication events (enroll token on first login, send notifications, modify user attributes)
- **Machine resolvers**: Map tokens to services (servers, VPNs, SSH hosts) for host-specific authentication

LinOTP's policy engine is simpler, focusing on realm-based assignment and token-level configuration.

### Integration Ecosystem

Both platforms integrate with common identity sources and authentication protocols:

| Integration | privacyIDEA | LinOTP |
|---|---|---|
| LDAP/Active Directory | Yes (full sync) | Yes |
| SQL databases | Yes | Yes |
| SCIM | Yes | No |
| SAML SP | Via SimpleSAMLphp module | No |
| OAuth2/OIDC | Via authentication endpoint | No |
| RADIUS | Built-in server | Module |
| PAM | Yes [kubernetes](https://kubernetes.io/)FreeRADIUS | Compatible | Compatible |
| Kubernetes | Helm chart available | Manual |
| REST API | Full OpenAPI | JSON REST |

If your identity infrastructure includes SCIM provisioning, SAML federation, or OAuth2/OIDC flows, privacyIDEA offers more native integration points. For a detailed comparison of the broader authentication landscape, see our [Authentik vs Keycloak vs Authelia guide](../authentik-vs-keycloak-vs-authelia/) covering identity providers that pair well with these MFA servers.

## Which Should You Choose?

**Choose privacyIDEA if:**
- You need FIDO2/WebAuthn or certificate-based authentication
- You want a comprehensive web admin interface for your operations team
- You require event handlers, scoped policies, and machine resolvers
- You're deploying in a multi-tenant environment with complex policy requirements
- You need SCIM user provisioning or SAML/OAuth2 integration

**Choose LinOTP if:**
- You need a lightweight, simple MFA server for basic TOTP/HOTP
- Your use case is straightforward: application MFA with existing LDAP users
- You prefer a minimal architecture that's easy to audit and maintain
- You're deploying in a resource-constrained environment
- You have an existing LSE support contract

For most organizations starting a self-hosted MFA deployment in 2026, privacyIDEA offers the broader feature set and more active development. LinOTP remains a solid choice for environments that value simplicity and have well-established operational procedures around it.

## FAQ

### What is the difference between privacyIDEA and LinOTP?

Both are open-source, self-hosted multi-factor authentication servers written in Python and licensed under AGPLv3. privacyIDEA has more features — including FIDO2/WebAuthn, certificate tokens, a full web admin UI, SCIM integration, and event handlers. LinOTP is simpler and focuses on core TOTP/HOTP authentication with a lighter deployment footprint. privacyIDEA has ~1,700 GitHub stars and more recent development activity compared to LinOTP's ~540 stars.

### Can privacyIDEA or LinOTP replace Duo Security?

Yes, both can serve as drop-in replacements for Duo Security. They support RADIUS (for VPN, network device, and wireless authentication), PAM (for Linux/SSH login MFA), and REST APIs (for application-level MFA). privacyIDEA additionally supports push notifications via Firebase, similar to Duo Push, and offers a mobile-friendly user self-service portal for token enrollment.

### How do I migrate from Google Authenticator to a self-hosted MFA server?

Both platforms support TOTP tokens compatible with Google Authenticator, Authy, Microsoft Authenticator, and any other RFC 6238-compliant app. To migrate, export your users' TOTP seeds from your current system, import them into privacyIDEA or LinOTP, and assign them to the corresponding user accounts. Users continue using the same authenticator app — the only change is which server validates the codes.

### Do these MFA servers support hardware tokens like YubiKey?

Yes. Both privacyIDEA and LinOTP support YubiKey in OTP mode. privacyIDEA additionally supports YubiKey in FIDO2/WebAuthn mode for passwordless authentication, and supports a wider range of FIDO2 security keys (SoloKey, Nitrokey, Feitian, and others).

### Is it safe to self-host MFA in production?

Self-hosted MFA is used by many enterprises, government agencies, and service providers. Both privacyIDEA and LinOTP are AGPLv3-licensed, auditable, and used in production worldwide. Key security practices include: storing the encryption key (`enckey`) on a secure volume with restricted file permissions, using PostgreSQL over SQLite for the audit database, enabling TLS on all API endpoints, and regular database backups. The encryption key is critical — without it, enrolled tokens cannot be validated.

### How do I set up MFA for SSH login?

Both platforms provide PAM modules. Install the PAM module on your Linux server, configure `/etc/pam.d/sshd` to include the MFA PAM module, and configure the module to point to your privacyIDEA or LinOTP server URL. Users then authenticate with their SSH key or password followed by their OTP code. This works with TOTP apps, hardware tokens, or SMS-delivered codes.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "privacyIDEA vs LinOTP: Self-Hosted MFA Server Comparison 2026",
  "description": "Compare privacyIDEA and LinOTP for self-hosted multi-factor authentication. Docker setup guides, token types, RADIUS integration, and enterprise deployment comparison.",
  "datePublished": "2026-04-19",
  "dateModified": "2026-04-19",
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
