---
title: "Self-Hosted LDAP Self-Service Password: LTB SSP vs Kanidm vs FusionDirectory Guide"
date: "2026-05-10"
tags: ["ldap", "password-management", "identity", "self-service", "authentication", "kanidm"]
draft: false
---

When users forget their LDAP passwords, IT administrators traditionally handle resets manually. This creates bottlenecks, increases helpdesk costs, and slows down employee productivity. Self-service password (SSP) portals solve this by letting users reset their own credentials through a secure web interface.

Three open-source platforms provide LDAP self-service password capabilities: **LTB Self-Service Password (SSP)**, **Kanidm**, and **FusionDirectory**.

## Comparison Table

| Feature | LTB SSP | Kanidm | FusionDirectory |
|---------|---------|--------|-----------------|
| GitHub Stars | 1,313+ | 4,916+ | 188+ |
| Language | PHP | Rust | PHP |
| LDAP Backend | Any OpenLDAP/389DS | Built-in (own backend) | OpenLDAP-based |
| Password Reset | ✅ Via email token | ✅ Via challenge questions | ✅ Via email |
| Password Change | ✅ Yes | ✅ Yes | ✅ Yes |
| Password Policies | ✅ Via LDAP | ✅ Built-in | ✅ Via plugins |
| MFA/OTP | ✅ TOTP, SMS | ✅ WebAuthn, TOTP | ✅ TOTP, SMS |
| CAPTCHA | ✅ reCAPTCHA, hCaptcha | ✅ Built-in | ✅ reCAPTCHA |
| Docker Support | ✅ Community images | ✅ Official image | ✅ Official images |
| Active Directory | ✅ Yes | ❌ No | ❌ No |
| REST API | ❌ No | ✅ Yes | ✅ Via plugins |
| Audit Logging | ✅ Basic | ✅ Comprehensive | ✅ Via plugins |
| Branding/Theming | ✅ CSS customization | ✅ Built-in themes | ✅ Customizable |

## How LDAP Self-Service Password Works

SSP portals provide a web interface where users can:
1. **Change password** — authenticated users update their own credentials
2. **Reset forgotten password** — via email token, SMS, or challenge questions
3. **Unlock account** — after too many failed login attempts
4. **Manage MFA** — enroll TOTP, SMS, or hardware keys

The portal connects to your LDAP directory using a privileged bind account to perform password modifications.

## LTB Self-Service Password

LTB SSP is a lightweight PHP application focused solely on password self-service. It works with any OpenLDAP or Active Directory backend.

### Key Features
- **Simple deployment** — single PHP application, minimal dependencies
- **Universal LDAP support** — works with OpenLDAP, 389 Directory Server, Active Directory
- **Multiple reset methods** — email tokens, SMS, security questions
- **Password quality checks** — enforces complexity, history, and expiration rules

### Docker Compose

```yaml
version: '3.8'
services:
  ltb-ssp:
    image: tiredofit/self-service-password:latest
    container_name: ltb-ssp
    ports:
      - "8080:80"
    environment:
      - LDAP_SERVER=ldap://ldap.example.com
      - LDAP_BINDDN=cn=admin,dc=example,dc=com
      - LDAP_BINDPASS=secret
      - LDAP_BASE_DN=ou=people,dc=example,dc=com
      - MAIL_FROM=ssp@example.com
      - SMTP_HOST=smtp.example.com
      - SMTP_PORT=587
    volumes:
      - ./config:/etc/self-service-password
    restart: unless-stopped
```

LTB SSP is ideal for organizations that already have an LDAP directory and need a simple, focused password self-service portal without additional identity management features.

## Kanidm

Kanidm is a modern identity management platform written in Rust. While it includes its own identity backend (not a generic LDAP proxy), it provides comprehensive self-service password management with strong security defaults.

### Key Features
- **Modern security** — written in Rust with memory safety guarantees
- **WebAuthn support** — hardware security key authentication (YubiKey, Touch ID)
- **Credential exchange** — users can generate and share credentials securely
- **Full audit trail** — comprehensive logging of all password changes
- **REST API** — programmatic access to all identity operations

### Docker Compose

```yaml
version: '3.8'
services:
  kanidm:
    image: kanidm/server:latest
    container_name: kanidm-server
    ports:
      - "8443:8443"
      - "3636:3636"
    volumes:
      - ./kanidm/server:/data
    environment:
      - KANIDM_URL=https://id.example.com:8443
    restart: unless-stopped
```

Kanidm's self-service portal is accessible at `https://id.example.com:8443`. Users authenticate with their existing credentials, then can change passwords, enroll WebAuthn devices, and manage their profile.

## FusionDirectory

FusionDirectory is a web-based LDAP directory management platform with self-service password capabilities through its plugins.

### Key Features
- **Comprehensive LDAP management** — manage users, groups, systems, and services
- **Self-service password plugin** — allows users to change and reset passwords
- **Multi-language support** — interface available in multiple languages
- **Role-based access** — fine-grained permissions for different user types

### Docker Compose

```yaml
version: '3.8'
services:
  fusiondirectory:
    image: fusiondirectory/fd:latest
    container_name: fusiondirectory
    ports:
      - "80:80"
    environment:
      - LDAP_SERVER=ldap://ldap.example.com
      - LDAP_BASE_DN=dc=example,dc=com
    volumes:
      - ./config:/etc/fusiondirectory
    restart: unless-stopped
```

FusionDirectory is best for organizations that need a full LDAP directory management UI with self-service password as one feature among many.

## Choosing the Right Solution

- **Choose LTB SSP** if you need a lightweight, focused password self-service portal that works with any existing LDAP or Active Directory backend.
- **Choose Kanidm** if you want a modern, secure identity platform with comprehensive self-service features including WebAuthn and credential exchange.
- **Choose FusionDirectory** if you need a full LDAP directory management UI with self-service password as part of a broader identity management platform.

## Why Self-Host LDAP Password Management?

Using your own self-service password portal instead of relying on cloud-based identity providers means your password reset flow never leaves your infrastructure. Users authenticate directly to your LDAP directory, tokens are generated and validated locally, and no third-party service has visibility into your credential management patterns.

This is particularly important for organizations with compliance requirements. GDPR, HIPAA, and SOX regulations often require that authentication data remain under direct organizational control. Self-hosted SSP portals provide full auditability — every password change, reset, and unlock event is logged to your own systems, not a SaaS provider's.

The cost savings are also significant. Enterprise password reset tools like Okta, Azure AD Self-Service Password Reset, and CyberArk charge per-user monthly fees. Self-hosted alternatives like LTB SSP and Kanidm are free and open-source, with the only cost being your server infrastructure.

For related identity management, see our [LDAP lightweight servers guide](../2026-04-24-lldap-vs-glauth-lightweight-ldap-self-hosted-auth-guide/) and [Kanidm vs Dex OIDC comparison](../2026-04-25-dex-vs-kanidm-vs-rauthy-self-hosted-oidc-sso-guide/). For full identity sync, our [Apache Syncope vs MidPoint comparison](../2026-05-04-apache-syncope-vs-midpoint-vs-ltb-ldap-toolbox-self-hosted-identity-sync-guide/) covers synchronization platforms.


## Password Policy Best Practices

Implementing effective password policies in your self-service portal requires balancing security with usability. Overly restrictive policies lead to predictable password patterns (Password1!, Summer2024!), while too-lenient policies expose your LDAP directory to credential stuffing attacks.

Enforce minimum password length of 12 characters rather than arbitrary complexity rules. Research from NIST SP 800-63B shows that length is more effective than complexity at preventing brute-force attacks. Additionally, check new passwords against known breached password databases (Have I Been Pwned, k-anonymity API) to prevent users from choosing compromised credentials.

For LDAP directories that support it, enable password history tracking to prevent users from cycling through a small set of passwords. Both LTB SSP and Kanidm support password history enforcement. FusionDirectory provides this through its password policy plugin.

## FAQ

### What is LDAP self-service password reset?
LDAP self-service password reset allows users to change or reset their LDAP directory passwords through a web interface without IT administrator involvement. It typically uses email tokens, SMS verification, or security questions to authenticate the user before allowing a password change.

### Does LTB SSP support Active Directory?
Yes, LTB SSP works with both OpenLDAP and Active Directory backends. You configure the LDAP connection settings (server URL, bind DN, base DN) and SSP handles the password modification through standard LDAP operations.

### Can Kanidm replace my existing LDAP directory?
Kanidm includes its own identity backend rather than proxying to an existing LDAP server. If you want to migrate from OpenLDAP to Kanidm, you can use its import tools. However, if you need to keep your existing LDAP directory, LTB SSP is the better choice as it works as a frontend to any LDAP backend.

### What security features do these SSP portals support?
All three support password complexity policies, brute-force protection, and CAPTCHA. LTB SSP and FusionDirectory support TOTP and SMS-based MFA. Kanidm additionally supports WebAuthn (hardware security keys) and provides a credential exchange feature for secure password sharing.

### How do I deploy LTB SSP behind a reverse proxy?
Deploy LTB SSP with Docker, then configure Nginx or Traefik as a reverse proxy with TLS termination. The container exposes port 80, which your reverse proxy forwards to. Ensure the proxy sets the correct `X-Forwarded-For` header so LTB SSP can track client IPs.

### Is Kanidm suitable for production use?
Kanidm is actively maintained with nearly 5,000 GitHub stars and regular releases. It's designed for production use with strong security defaults including memory-safe Rust code, comprehensive audit logging, and WebAuthn support. It's suitable for small to medium organizations.


<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted LDAP Self-Service Password: LTB SSP vs Kanidm vs FusionDirectory Guide",
  "description": "Compare LTB Self-Service Password, Kanidm, and FusionDirectory for LDAP password self-service management. Learn how each platform handles password resets, MFA enrollment, and identity management.",
  "datePublished": "2026-05-10",
  "dateModified": "2026-05-10",
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
