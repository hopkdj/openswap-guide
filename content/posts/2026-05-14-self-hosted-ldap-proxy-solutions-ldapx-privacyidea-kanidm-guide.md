---
title: "Self-Hosted LDAP Proxy Solutions: ldapx vs privacyIDEA LDAP Proxy vs Kanidm LDAP Proxy"
date: "2026-05-14"
tags: ["ldap", "authentication", "identity-management", "self-hosted", "security"]
draft: false
---

LDAP (Lightweight Directory Access Protocol) is the backbone of enterprise identity management, powering authentication for thousands of applications. But connecting legacy applications directly to your LDAP directory exposes the entire directory tree to every connected service. An LDAP proxy sits between applications and your directory server, intercepting and filtering requests to enforce security policies, add multi-factor authentication, and mask sensitive directory data.

In this guide, we compare three open-source LDAP proxy solutions you can deploy on your own infrastructure: **ldapx**, **privacyIDEA LDAP Proxy**, and **Kanidm LDAP Proxy**. Each addresses different use cases, from packet inspection and transformation to MFA integration and identity federation.

## What Is an LDAP Proxy?

An LDAP proxy is an intermediary service that receives LDAP requests from client applications, optionally transforms or validates them, and forwards them to the actual LDAP directory server. The proxy can:

- **Filter queries** — Restrict which directory attributes or subtrees applications can access
- **Transform responses** — Map attribute names, format values, or redact sensitive fields
- **Add authentication layers** — Inject MFA checks, token validation, or certificate verification
- **Audit and log** — Record all LDAP operations for compliance and forensic analysis
- **Cache results** — Reduce load on the directory server by caching frequently requested data
- **Load balance** — Distribute queries across multiple directory replicas

## Why Use an LDAP Proxy?

Direct connections between applications and LDAP directories create several operational and security challenges:

**Over-privileged access** — Applications often receive full directory read access when they only need to validate user credentials. A proxy enforces least-privilege access per application.

**Schema incompatibility** — Legacy applications expect specific LDAP schemas. A proxy can translate between modern directory schemas and legacy application expectations without modifying the directory.

**Audit compliance** — Regulations like SOX, HIPAA, and PCI-DSS require detailed authentication logs. A proxy centralizes LDAP audit logging across all applications.

**MFA enforcement** — Many legacy applications don't support modern MFA protocols. An LDAP proxy can intercept bind requests and enforce multi-factor authentication before forwarding to the directory.

**Directory protection** — A proxy shields the directory server from application-level issues like connection leaks, query storms, or malformed requests.

## Comparison Table

| Feature | ldapx | privacyIDEA LDAP Proxy | Kanidm LDAP Proxy |
|---------|-------|----------------------|-------------------|
| **Language** | Python | Python | Rust |
| **GitHub Stars** | 210+ | 19+ | 15+ |
| **Last Updated** | Active (2026) | Active (2024) | Active (2026) |
| **MFA Integration** | No | privacyIDEA (built-in) | Kanidm (built-in) |
| **Packet Inspection** | Full packet-level | Bind-level only | Protocol-level |
| **Attribute Mapping** | Yes (runtime) | Limited | Via Kanidm schema |
| **Query Filtering** | Yes (transform rules) | Bind filtering | Scope-limited |
| **TLS Support** | Yes | Yes | Yes |
| **Load Balancing** | No | No | Via Kanidm cluster |
| **Audit Logging** | Yes (detailed) | Yes (auth events) | Yes (full audit) |
| **Docker Support** | Yes | Yes | Yes |
| **Directory Support** | Any LDAPv3 | Any LDAPv3 | Kanidm only |
| **License** | MIT | AGPL-3.0 | MPL-2.0 |

## ldapx: Flexible LDAP Packet Inspector

[ldapx](https://github.com/Macmod/ldapx) is a flexible LDAP proxy written in Python that enables real-time inspection and transformation of all LDAP packets flowing between clients and directory servers. It uses a rule-based transformation engine that lets you modify requests and responses on the fly.

### Installation

```bash
# From source
git clone https://github.com/Macmod/ldapx.git
cd ldapx
pip install -r requirements.txt

# Docker
docker pull macmod/ldapx:latest

# Docker Compose
docker compose up -d
```

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  ldapx:
    image: macmod/ldapx:latest
    ports:
      - "3890:389"
    environment:
      - LDAP_PROXY_BACKEND_HOST=ldap.example.com
      - LDAP_PROXY_BACKEND_PORT=389
      - LDAP_PROXY_BIND_DN=cn=proxy,dc=example,dc=com
      - LDAP_PROXY_BIND_PASSWORD=${LDAP_PROXY_PASSWORD}
    volumes:
      - ./rules:/app/rules
      - ./logs:/app/logs
    restart: unless-stopped
```

### Key Features

- **Runtime transformation rules** — Define Python-based rules that modify LDAP packets in real-time
- **Full packet inspection** — See and modify every LDAP operation: bind, search, modify, add, delete
- **Attribute masking** — Redact or hash sensitive attributes like passwords, SSNs, or phone numbers
- **Query rewriting** — Transform client queries to match different directory schemas
- **No vendor lock-in** — Works with any LDAPv3-compliant directory server

### Example Configuration

```python
# rules/attribute_mask.py
def transform_search_result(entry):
    """Mask sensitive attributes in search results."""
    sensitive_attrs = ['userPassword', 'ssn', 'creditCard']
    for attr in sensitive_attrs:
        if attr in entry['attributes']:
            entry['attributes'][attr] = ['*** MASKED ***']
    return entry

def transform_bind_request(request):
    """Log all bind attempts."""
    log_bind_attempt(request['bind_dn'], request['source_ip'])
    return request  # Forward as-is
```

## privacyIDEA LDAP Proxy: MFA for Legacy Applications

[privacyIDEA LDAP Proxy](https://github.com/privacyidea/privacyidea-ldap-proxy) is an LDAP proxy that integrates with the privacyIDEA multi-factor authentication platform. It intercepts LDAP bind requests and requires users to provide an OTP token value before forwarding authentication to the backend directory.

### Installation

```bash
# From PyPI
pip install privacyidea-ldap-proxy

# From source
git clone https://github.com/privacyidea/privacyidea-ldap-proxy.git
cd privacyidea-ldap-proxy
pip install -r requirements.txt

# Docker
docker pull privacyidea/privacyidea-ldap-proxy:latest
```

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  ldap-proxy:
    image: privacyidea/privacyidea-ldap-proxy:latest
    ports:
      - "1389:1389"
    environment:
      - PI_URL=https://privacyidea.example.com
      - PI_ADMIN=admin
      - PI_PASSWORD=${PI_ADMIN_PASSWORD}
      - LDAP_SERVER=ldap://ldap.example.com:389
      - LDAP_BASE_DN=dc=example,dc=com
      - LDAP_BIND_DN=cn=admin,dc=example,dc=com
      - LDAP_BIND_PASSWORD=${LDAP_ADMIN_PASSWORD}
      - RESOLVER=ldapresolver
    volumes:
      - ./config:/etc/privacyidea-ldap-proxy
      - ./logs:/var/log/privacyidea-ldap-proxy
    restart: unless-stopped
```

### Key Features

- **OTP integration** — Requires users to append their OTP to their password during LDAP bind
- **privacyIDEA ecosystem** — Leverages privacyIDEA's extensive token types (HOTP, TOTP, Yubikey, SMS, email)
- **Resolver-based** — Maps LDAP users to privacyIDEA tokens via configurable resolvers
- **Audit trail** — Every authentication attempt is logged in privacyIDEA's audit system
- **Fallback modes** — Configure grace periods or bypass rules for emergency access

### Configuration Example

```ini
# /etc/privacyidea-ldap-proxy/ldap-proxy.ini
[DEFAULT]
listen = 0.0.0.0
port = 1389

[privacyIDEA]
url = https://privacyidea.example.com
admin = admin
password = ${PI_ADMIN_PASSWORD}

[LDAP]
server = ldap://ldap.example.com:389
basedn = dc=example,dc=com
binddn = cn=proxy,dc=example,dc=com
bindpw = ${LDAP_PROXY_PASSWORD}
resolver = ldapresolver

[logging]
level = INFO
file = /var/log/privacyidea-ldap-proxy/ldap-proxy.log
```

## Kanidm LDAP Proxy: Modern Identity Federation

[Kanidm LDAP Proxy](https://github.com/kanidm/ldap-proxy) is a lightweight proxy that bridges legacy LDAP applications to the modern Kanidm identity platform. It translates LDAP protocol requests into Kanidm's native API calls, allowing applications that only understand LDAP to authenticate against Kanidm's modern identity store.

### Installation

```bash
# Cargo (Rust)
cargo install kanidm-ldap-proxy

# From pre-built binary
# Download from https://github.com/kanidm/kanidm/releases

# Docker
docker pull ghcr.io/kanidm/ldap-proxy:latest
```

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  kanidm-ldap-proxy:
    image: ghcr.io/kanidm/ldap-proxy:latest
    ports:
      - "3636:3636"
    environment:
      - KANIDM_URL=https://kanidm.example.com
      - KANIDM_ORIGIN=https://kanidm.example.com
    volumes:
      - ./kanidm-ldap-proxy.toml:/etc/kanidm-ldap-proxy.toml
      - ./kanidm-ca.pem:/etc/kanidm-ca.pem:ro
    restart: unless-stopped
```

### Key Features

- **Kanidm integration** — Native support for Kanidm's modern identity management features
- **OAuth/OIDC backend** — Uses Kanidm's OAuth2/OIDC APIs for authentication
- **SCIM support** — Synchronizes user data via Kanidm's SCIM interface
- **Modern security** — Inherits Kanidm's security model including passkey and WebAuthn support
- **Migration path** — Enables gradual migration from legacy LDAP to modern identity platforms

### Configuration

```toml
# /etc/kanidm-ldap-proxy.toml
bindaddress = "0.0.0.0:3636"
kanidm_url = "https://kanidm.example.com"
kanidm_origin = "https://kanidm.example.com"

[tls]
ca = "/etc/kanidm-ca.pem"

[logging]
level = "INFO"
format = "json"
```

## Choosing the Right LDAP Proxy

| Use Case | Recommended Tool | Reason |
|----------|-----------------|--------|
| Legacy app MFA enforcement | privacyIDEA LDAP Proxy | Purpose-built for OTP integration |
| Packet-level inspection | ldapx | Full LDAP packet transformation |
| Modern identity migration | Kanidm LDAP Proxy | Bridges LDAP to modern identity |
| Attribute masking | ldapx | Runtime rule-based transformations |
| Compliance auditing | privacyIDEA LDAP Proxy | Comprehensive auth audit trail |
| Schema translation | ldapx | Flexible query/response rewriting |

## Security Best Practices

1. **TLS everywhere** — Encrypt connections between clients, proxy, and directory server
2. **Service accounts** — Use dedicated proxy bind accounts with minimal directory permissions
3. **Rate limiting** — Protect against brute-force attacks by throttling bind requests
4. **Network segmentation** — Place the proxy in a DMZ between applications and the directory
5. **Secret management** — Store proxy credentials in a secrets manager, not configuration files
6. **Regular rotation** — Rotate proxy bind passwords on a scheduled basis

## Why Self-Host Your LDAP Proxy?

Deploying an LDAP proxy on your own infrastructure is essential for organizations that need to maintain control over authentication flows. When you self-host the proxy, every authentication decision, attribute mapping, and audit log stays within your security boundary. This is particularly important for compliance frameworks that require detailed authentication records — third-party proxy services often cannot provide the level of log retention and access control that auditors demand.

Integration with existing identity infrastructure is another key driver. Self-hosted LDAP proxies can connect to your internal PKI for mutual TLS authentication, integrate with your SIEM for real-time alerting on suspicious bind patterns, and leverage your internal secrets manager for credential storage. These integrations are typically impossible or severely limited with cloud-hosted alternatives.

Performance considerations also favor self-hosting. LDAP bind operations are latency-sensitive — even a few milliseconds of additional network round-trip time can impact user experience during login. Running the proxy on the same network segment as your applications and directory server minimizes latency and eliminates dependency on external network connectivity.

Customization is the final advantage. Every organization has unique directory schemas, attribute mappings, and authentication requirements. A self-hosted proxy can be tailored to your exact specifications — custom transformation rules, organization-specific audit formats, and integration with proprietary identity systems.

For identity management platforms, see our [Logto vs SuperTokens vs Ory Kratos comparison](../2026-05-10-self-hosted-auth-platforms-logto-supertokens-ory-kratos-guide/). For multi-factor authentication servers, check our [privacyIDEA vs LinOTP vs 2FAuth guide](../2026-05-15-self-hosted-mfa-otp-servers-privacyidea-linotp-2fauth-guide/). For secrets management, our [Vault vs SOPS vs Sealed Secrets article](../self-hosted-secrets-management-vault-sops-sealed-secrets-guide-2026/) covers credential storage patterns.

## FAQ

### What is the difference between an LDAP proxy and an LDAP gateway?

An LDAP proxy operates at the protocol level, intercepting and forwarding LDAP packets while optionally transforming them. An LDAP gateway typically translates between LDAP and other protocols (like REST APIs or SAML). Proxies maintain LDAP compatibility; gateways enable protocol translation.

### Can an LDAP proxy add MFA to applications that don't support it?

Yes. The privacyIDEA LDAP Proxy specifically does this by intercepting LDAP bind requests and requiring an OTP token before forwarding authentication to the backend directory. Users append their OTP to their normal password, and the proxy validates it with the MFA server.

### Does an LDAP proxy protect against LDAP injection attacks?

Yes, to some extent. Proxies like ldapx can inspect and sanitize LDAP search filters, removing or escaping characters that could be used in injection attacks. However, the primary defense should be proper input validation in the application itself.

### Can I use an LDAP proxy with Active Directory?

All three tools support LDAPv3, which is the protocol used by Active Directory. However, AD-specific features like Kerberos authentication and Global Catalog queries may require additional configuration.

### How does an LDAP proxy handle TLS/SSL connections?

LDAP proxies typically operate in one of two modes: they either terminate TLS from the client and establish a new TLS connection to the backend (TLS bridging), or they pass through encrypted traffic without inspection (TLS tunneling). The choice depends on whether the proxy needs to inspect packet contents.

### What happens if the LDAP proxy goes down?

Most deployments configure applications with both the proxy address and the direct directory server address as a fallback. However, this bypasses the proxy's security controls. For high availability, deploy multiple proxy instances behind a load balancer.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted LDAP Proxy Solutions: ldapx vs privacyIDEA LDAP Proxy vs Kanidm LDAP Proxy",
  "description": "Compare open-source LDAP proxy solutions for adding MFA, filtering queries, masking attributes, and auditing LDAP authentication in self-hosted environments.",
  "datePublished": "2026-05-14",
  "dateModified": "2026-05-14",
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
