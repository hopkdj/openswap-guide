---
title: "SimpleSAMLphp vs Shibboleth vs Apereo CAS: Self-Hosted SAML IdP Guide 2026"
date: 2026-04-27
tags: ["comparison", "guide", "self-hosted", "authentication", "saml", "sso"]
draft: false
description: "Compare the top self-hosted SAML Identity Providers: SimpleSAMLphp, Shibboleth IdP, and Apereo CAS. Includes Docker deployment, configuration guides, and feature comparison for enterprise SSO in 2026."
---

When you need SAML 2.0 single sign-on for your organization, relying on a cloud identity provider isn't always an option. Compliance requirements, data sovereignty, air-gapped networks, or cost constraints push many teams to run their own SAML Identity Provider (IdP). This guide compares the three most established open-source SAML IdP solutions: **SimpleSAMLphp**, **Shibboleth IdP**, and **Apereo CAS**.

If you are evaluating broader SSO protocols (OIDC, OAuth2) alongside SAML, see our guides on [lightweight SSO platforms](../casdoor-vs-zitadel-vs-authentik-lightweight-sso-guide/) and [self-hosted IAM solutions](../zitadel-vs-ory-vs-keycloak-self-hosted-iam-guide/).

## Why Self-Host a SAML Identity Provider

SAML 2.0 remains the standard for enterprise and academic single sign-on. Thousands of applications — from learning management systems and research portals to ERP platforms and HR tools — support SAML as their primary SSO protocol. Self-hosting a SAML IdP gives you:

- **Full control over identity data** — no third-party holds your user directory
- **Air-gapped deployment** — works in environments with no internet access
- **Custom attribute mapping** — define exactly what claims each service provider receives
- **Cost savings** — no per-user monthly fees for large organizations
- **Compliance** — keep authentication logs and user data within your infrastructure
- **No vendor lock-in** — switch or upgrade providers without migrating users

The three solutions compared here represent different design philosophies: SimpleSAMLphp (lightweight and PHP-based), Shibboleth IdP (the academic standard), and Apereo CAS (a multi-protocol enterprise platform).

| Feature | SimpleSAMLphp | Shibboleth IdP v5 | Apereo CAS v7 |
|---|---|---|---|
| **Language** | PHP | Java | Java |
| **License** | LGPL 2.1 | Apache 2.0 | Apache 2.0 |
| **GitHub Stars** | 1,136 | N/A (shibboleth.net) | 11,322 |
| **Last Updated** | 2026-04-21 | Active development | 2026-04-26 |
| **SAML 2.0 IdP** | ✅ Full | ✅ Full | ✅ Full |
| **SAML 2.0 SP** | ✅ Full | ❌ No | ❌ No |
| **OIDC Provider** | ❌ No | ❌ No | ✅ Full |
| **OAuth2 Provider** | ❌ No | ❌ No | ✅ Full |
| **CAS Protocol** | ❌ No | ❌ No | ✅ Full (native) |
| **LDAP Integration** | ✅ Auth source + attribute store | ✅ Auth source + attribute resolver | ✅ Auth source + attribute repository |
| **Database Auth** | ✅ SQL modules | Via JDBC attribute resolver | ✅ JDBC, Mongo, REST |
| **MFA Support** | Via external modules | Built-in (Duo, MFA) | Built-in (Duo, YubiKey, WebAuthn) |
| **Web UI** | ✅ Admin + user-facing | ❌ Command-line config | ✅ Comprehensive dashboard |
| **Docker Support** | Official image available | Community images | Official Docker image |
| **Setup Complexity** | Low | High | Medium-High |
| **Best For** | Small teams, quick SAML setup | Universities, research federations | Enterprise, multi-protocol SSO |

## SimpleSAMLphp — Lightweight PHP SAML IdP

SimpleSAMLphp is the most approachable self-hosted SAML solution. Written in native PHP, it handles both IdP and SP roles and integrates with virtually any authentication backend (LDAP, SQL, external APIs). Its configuration is file-based, making it easy to version control and deploy.

**Key strengths:**

- **Quick setup** — get a working SAML IdP in under 30 minutes
- **Dual role** — works as both IdP (issuing assertions) and SP (consuming assertions)
- **PHP ecosystem** — easy to extend with custom authentication modules
- **Federated identity** — supports SAML metadata aggregation for federation participation
- **Tested in production** — used by universities and enterprises worldwide

### Docker Deployment

```yaml
version: "3.8"

services:
  simplesamlphp:
    image: kristophjunge/test-saml-idp:latest
    ports:
      - "8080:8080"
      - "8443:8443"
    environment:
      - SIMPLESAMLPHP_SP_ENTITY_ID=your-sp-entity-id
      - SIMPLESAMLPHP_SP_ASSERTION_CONSUMER_SERVICE=https://your-app.example.com/saml/acs
      - SIMPLESAMLPHP_SP_SINGLE_LOGOUT_SERVICE=https://your-app.example.com/saml/sls
    volumes:
      - ./config:/var/www/simplesamlphp/config
      - ./metadata:/var/www/simplesamlphp/metadata
    restart: unless-stopped

networks:
  default:
    driver: bridge
```

For a production deployment without the test image, use the official package:

```bash
# Install via Composer
composer require simplesamlphp/simplesamlphp

# Or use the official Docker image
docker run -d \
  --name simplesamlphp \
  -p 8080:80 \
  -v /etc/simplesamlphp/config:/var/www/simplesamlphp/config \
  -v /etc/simplesamlphp/metadata:/var/www/simplesamlphp/metadata \
  -v /etc/simplesamlphp/cert:/var/www/simplesamlphp/cert \
  simplesamlphp/simplesamlphp:latest
```

### Basic Configuration

```php
// config/authsources.php
$config = [
    'example-ldap' => [
        'ldap:LDAP',
        'hostname' => 'ldap.example.com',
        'enable_tls' => true,
        'debug' => false,
        'timeout' => 0,
        'search.enable' => true,
        'search.base' => 'ou=users,dc=example,dc=com',
        'search.attributes' => ['uid', 'mail'],
        'search.filter' => '(objectClass=inetOrgPerson)',
    ],
];

// config/config.php — basic IdP settings
$config = [
    'baseurlpath' => 'https://idp.example.com/simplesaml/',
    'technicalcontact_name' => 'Administrator',
    'technicalcontact_email' => 'admin@example.com',
    'timezone' => 'UTC',
    'secretsalt' => 'your-secret-salt-change-this',
    'auth.adminpassword' => '$2y$10$hashed-admin-password',
];
```

## Shibboleth IdP v5 — The Academic Standard

Shibboleth IdP has been the backbone of academic federations (InCommon, eduGAIN, REFEDS) for over two decades. Version 5 introduced significant modernization: improved container support, a new configuration framework, and better attribute handling.

**Key strengths:**

- **Federation-ready** — natively designed for large-scale federation participation
- **Attribute resolution** — powerful data connector system for complex attribute mapping
- **Mature security model** — battle-tested in thousands of universities
- **Active development** — strong community and institutional backing
- **Standards compliance** — strict adherence to SAML 2.0 and federation profiles

### Installation (Traditional)

Shibboleth IdP is typically installed from source or packages:

```bash
# Download and extract
wget https://shibboleth.net/downloads/identity-provider/latest/shibboleth-identity-provider-5.x.x.tar.gz
tar xzf shibboleth-identity-provider-5.x.x.tar.gz
cd shibboleth-identity-provider-5.x.x/bin

# Run installer
./install.sh

# The installer prompts for:
# - Source distribution location
# - Installation directory (default: /opt/shibboleth-idp)
# - Hostname for the IdP
# - SAML entityID (auto-generated from hostname)
# - Scope for eduPersonScopedAffiliation
# - Passwords for signing and encryption keystores
```

### Docker Deployment (Community)

```yaml
version: "3.8"

services:
  shibboleth-idp:
    image: unicon/shibboleth-idp:latest
    ports:
      - "8080:8080"
      - "8443:8443"
    environment:
      - IDP_HOSTNAME=idp.example.com
      - IDP_ENTITY_ID=https://idp.example.com/idp/shibboleth
      - IDP_SCOPE=example.com
      - LDAP_URL=ldap://ldap.example.com:389
      - LDAP_BASE_DN=ou=users,dc=example,dc=com
    volumes:
      - ./idp-conf:/opt/shibboleth-idp/conf
      - ./idp-metadata:/opt/shibboleth-idp/metadata
      - ./idp-credentials:/opt/shibboleth-idp/credentials
    restart: unless-stopped
```

### Attribute Resolver Configuration

```xml
<!-- conf/attribute-resolver.xml — define user attributes for SAML assertions -->
<resolver:AttributeDefinition id="uid"
    xsi:type="Simple"
    sourceAttributeID="uid">
    <resolver:Dependency ref="myLDAP" />
    <resolver:AttributeEncoder xsi:type="SAML2String"
        name="urn:oid:0.9.2342.19200300.100.1.1"
        friendlyName="uid" />
</resolver:AttributeDefinition>

<resolver:AttributeDefinition id="eduPersonAffiliation"
    xsi:type="Prescript"
    script="affiliation.js">
    <resolver:Dependency ref="myLDAP" />
    <resolver:AttributeEncoder xsi:type="SAML2String"
        name="urn:oid:1.3.6.1.4.1.5923.1.1.1.1"
        friendlyName="eduPersonAffiliation" />
</resolver:AttributeDefinition>
```

## Apereo CAS v7 — Multi-Protocol Enterprise SSO

Apereo CAS (Central Authentication Service) is the most feature-rich option. While originally designed around its own CAS protocol, modern versions (v6+) provide full SAML 2.0 IdP capabilities alongside OIDC, OAuth2, and its native protocol. It supports dozens of authentication methods and integrates with virtually every identity store.

**Key strengths:**

- **Multi-protocol** — SAML 2.0, OIDC, OAuth2, CAS, WS-Federation from one platform
- **Extensible** — modular overlay architecture for custom extensions
- **Rich authentication** — built-in MFA, adaptive authentication, password management
- **Service registry** — dynamic service registration with YAML, JSON, JDBC, or REST backends
- **Active community** — 11,000+ GitHub stars, large contributor base

### Docker Deployment

```yaml
version: "3.8"

services:
  apereo-cas:
    image: apereo/cas:latest
    ports:
      - "8080:8080"
      - "8443:8443"
    environment:
      - CAS_SERVER_NAME=https://cas.example.com:8443
      - SPRING_PROFILES_ACTIVE=standalone
    volumes:
      - ./etc/cas/config:/etc/cas/config
      - ./etc/cas/services:/etc/cas/services
      - ./etc/cas/saml:/etc/cas/saml
    restart: unless-stopped

  # Optional: PostgreSQL for service registry
  cas-postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: cas_db
      POSTGRES_USER: cas_user
      POSTGRES_PASSWORD: cas_secret
    volumes:
      - cas-data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  cas-data:
```

### Service Registry Configuration

```yaml
# etc/cas/services/SAMLService-100.yaml
---
"@class": "org.apereo.cas.support.saml.services.SamlRegisteredService"
"serviceId": "https://sp\\.example\\.org/.*"
"name": "Example SAML Service Provider"
"id": 1000
"description": "SAML 2.0 SP for the example application"
"evaluationOrder": 10
"attributeReleasePolicy":
  "@class": "org.apereo.cas.services.ReturnAllowedAttributeReleasePolicy"
  "allowedAttributes":
    - "java.util.ArrayList"
    - "uid"
    - "mail"
    - "displayName"
    - "eduPersonAffiliation"
"accessStrategy":
  "@class": "org.apereo.cas.services.DefaultRegisteredServiceAccessStrategy"
  "enabled": true
  "ssoEnabled": true
```

### Authentication Handler Setup

```properties
# etc/cas/config/cas.properties
# LDAP Authentication
cas.authn.ldap[0].ldap-url=ldap://ldap.example.com:389
cas.authn.ldap[0].base-dn=ou=users,dc=example,dc=com
cas.authn.ldap[0].search-filter=(uid={user})
cas.authn.ldap[0].bind-dn=cn=admin,dc=example,dc=com
cas.authn.ldap[0].bind-credential=secret
cas.authn.ldap[0].principal-attribute-list=uid,mail,displayName,eduPersonAffiliation

# Enable SAML IdP
cas.authn.saml-idp.core.entity-id=https://cas.example.com:8443/idp/shibboleth
cas.authn.saml-idp.core.metadata-location=file:/etc/cas/saml
cas.authn.saml-idp.core.single-sign-on-enabled=true
cas.authn.saml-idp.core.attribute-release-enabled=true
```

## Comparison: Which SAML IdP to Choose

| Criteria | SimpleSAMLphp | Shibboleth IdP | Apereo CAS |
|---|---|---|---|
| **Time to deploy** | Minutes | Hours | 1-2 hours |
| **SAML-only focus** | ✅ Yes | ✅ Yes | ❌ Multi-protocol |
| **Needs both IdP + SP** | ✅ Yes | ❌ IdP only | ❌ IdP only |
| **Federation participation** | Good | Excellent | Good |
| **Academic/research use** | Good | Excellent | Good |
| **Enterprise SSO** | Limited | Good | Excellent |
| **Needs OIDC too** | ❌ No | ❌ No | ✅ Yes |
| **PHP environment** | ✅ Native | ❌ Java only | ❌ Java only |
| **Configuration method** | PHP files | XML config | Properties + YAML |
| **Attribute mapping** | Simple | Advanced | Very advanced |
| **Community support** | Active | Strong (academic) | Very active |
| **Container-friendly** | ✅ Yes | ⚠️ Community images | ✅ Official images |

### When to Choose SimpleSAMLphp

- You need a quick SAML IdP up and running with minimal infrastructure
- Your team is comfortable with PHP
- You need both IdP and SP functionality in one package
- You are setting up SSO for a handful of applications
- You prefer file-based configuration that is easy to version control

### When to Choose Shibboleth IdP

- Your organization participates in academic federations (InCommon, eduGAIN)
- You need strict SAML 2.0 compliance with federation profile support
- Your IT team has Java expertise
- You require complex attribute resolution from multiple data sources
- Long-term institutional support and standards compliance are priorities

### When to Choose Apereo CAS

- You need SAML **and** OIDC/OAuth2 from a single platform
- You want a unified SSO solution for dozens or hundreds of applications
- You need built-in MFA, password management, and self-service features
- Your team works with Spring Boot and Java ecosystems
- You want the most actively developed and feature-rich open-source option

## Security Considerations for Self-Hosted SAML IdPs

Regardless of which solution you choose, follow these security best practices:

1. **Certificate management** — use short-lived certificates for signing and encryption. Automate rotation with tools like [cert-manager](../cert-manager-vs-lego-vs-acme-sh-self-hosted-tls-certificate-automation-guide/).
2. **Transport encryption** — always serve the IdP over HTTPS with strong TLS settings. Consider mutual TLS for high-security deployments, as covered in our [mTLS guide](../self-hosted-mutual-tls-mtls-nginx-caddy-traefik-envoy-guide/).
3. **Metadata validation** — validate SP metadata signatures before accepting connections. Never accept unsigned metadata in production.
4. **Attribute filtering** — only release attributes that each SP explicitly needs. Apply allowlist-based attribute release policies.
5. **Rate limiting** — protect login endpoints against brute-force attacks. Use reverse proxy rate limiting or built-in controls.
6. **Audit logging** — log all authentication attempts, attribute releases, and configuration changes. Store logs in a tamper-evident system for compliance.

## FAQ

### What is a SAML Identity Provider (IdP)?

A SAML Identity Provider is a server that authenticates users and issues SAML assertions to Service Providers (SPs). When a user tries to access a SAML-protected application, the SP redirects them to the IdP for authentication. After successful login, the IdP sends a signed XML assertion back to the SP, which grants access. This is the foundation of enterprise single sign-on.

### Can SimpleSAMLphp act as both IdP and SP?

Yes. SimpleSAMLphp uniquely supports both roles in a single installation. It can authenticate users and issue assertions (IdP mode) and also consume assertions from other IdPs (SP mode). This makes it ideal for proxy scenarios or testing environments. Shibboleth IdP and Apereo CAS only function as IdPs.

### Is Shibboleth IdP still actively maintained?

Yes. Shibboleth IdP v5 was released in 2024 with significant improvements including better container support, a new configuration framework, and enhanced security features. It remains the standard choice for academic federations worldwide and receives regular security updates from the Shibboleth Consortium.

### How does Apereo CAS compare to Keycloak for SAML?

Both support SAML 2.0, but with different focus areas. Apereo CAS was extended to support SAML as one of many protocols (alongside CAS, OIDC, OAuth2). Keycloak supports SAML natively but is primarily an OIDC/OAuth2 platform. CAS has deeper SAML attribute mapping and federation support, while Keycloak offers a more polished admin UI and broader protocol coverage. For SAML-heavy environments, CAS is the stronger choice.

### Do I need a reverse proxy for my SAML IdP?

Yes, in production. A reverse proxy handles TLS termination, load balancing, and rate limiting before traffic reaches your IdP. Nginx, Caddy, or Traefik are common choices. Configure the proxy to forward `/simplesaml/` (SimpleSAMLphp), `/idp/` (Shibboleth), or `/cas/` (Apereo CAS) paths to the IdP backend.

### Can I migrate from one SAML IdP to another?

Yes, but plan carefully. The migration involves:
1. Exporting SP metadata from the old IdP and importing into the new one
2. Reconfiguring each SP to trust the new IdP's entityID and certificate
3. Mapping user attributes between the two systems
4. Testing with a subset of SPs before full cutover
5. Running both IdPs in parallel during transition if possible

### How do I handle SAML metadata in a federation?

Participating federations (InCommon, eduGAIN) publish aggregated metadata files containing all member IdPs and SPs. Your IdP downloads and validates this metadata regularly. SimpleSAMLphp uses the `metarefresh` module. Shibboleth IdP uses the `MetadataProvider` configuration. Apereo CAS supports metadata ingestion via its SAML IdP module. Always validate metadata signatures to prevent spoofing.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "SimpleSAMLphp vs Shibboleth vs Apereo CAS: Self-Hosted SAML IdP Guide 2026",
  "description": "Compare the top self-hosted SAML Identity Providers: SimpleSAMLphp, Shibboleth IdP, and Apereo CAS. Includes Docker deployment, configuration guides, and feature comparison for enterprise SSO in 2026.",
  "datePublished": "2026-04-27",
  "dateModified": "2026-04-27",
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
