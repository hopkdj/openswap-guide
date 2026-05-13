---
title: "Self-Hosted TACACS+ Server: tac_plus vs tacquito vs tac_plus-ng"
date: "2026-05-13"
tags: ["tacacs", "aaa", "network-security", "authentication", "infrastructure"]
draft: false
---

Terminal Access Controller Access-Control System Plus (TACACS+) is the de facto standard for centralized authentication, authorization, and accounting (AAA) of network infrastructure devices. While RADIUS remains common for user authentication, TACACS+ is preferred for managing routers, switches, firewalls, and other network equipment due to its granular command-level authorization and TCP-based reliability.

Self-hosting a TACACS+ server gives you full control over who can access your network infrastructure, what commands they can execute, and a complete audit trail of all administrative activity. This guide compares three open-source TACACS+ server implementations: the classic **tac_plus**, the modern **tacquito** RFC implementation, and the actively maintained **tac_plus-ng**.

## What Is TACACS+ and Why Self-Host It?

TACACS+ (defined in RFC 8907) separates authentication, authorization, and accounting into distinct processes, unlike RADIUS which combines them. This separation enables:

- **Authentication**: Verify user identity (local, LDAP, Active Directory, RADIUS backend)
- **Authorization**: Define per-user command sets, privilege levels, and access windows
- **Accounting**: Log every command executed, session duration, and configuration changes

### Why Self-Host Instead of Using Commercial AAA?

| Factor | Self-Hosted | Commercial (Cisco ISE, ClearPass) |
|--------|-------------|-------------------------------------|
| **Cost** | Free (open source) | $5,000-$50,000+ per year |
| **Data control** | All logs stay on-prem | Cloud/SaaS options may transmit data externally |
| **Customization** | Full source access, custom auth plugins | Vendor-locked feature set |
| **Hardware** | Runs on any Linux server | Often requires appliance or specific VM sizing |
| **Audit compliance** | Direct database access for reporting | May require premium support for log export |

## tac_plus

**Stars:** 236+ | **Repo:** `facebook/tac_plus` | **Language:** C

The original `tac_plus` daemon by Marc Huber is the reference implementation that established the open-source TACACS+ ecosystem. It has been the foundation for countless network operations teams running AAA on-premises.

### Architecture

```
Network Device (router/switch)
        │
        │ TACACS+ (TCP 49)
        ▼
    tac_plus daemon
        │
        ├── PAM / LDAP / local file authentication
        ├── Configuration file (tac_plus.conf)
        └── Accounting log files
```

### Key Features

- IPv4 and IPv6 support
- PAM integration for flexible authentication backends
- Configuration file-based user/group/device definitions
- Command authorization with regex-based matching
- Accounting log output for audit trails
- Lightweight C daemon (~5 MB binary)

### Configuration Example

```
# tac_plus.conf
host = your_router {
    key = "shared-secret-key"
}

user = admin {
    login = des "encrypted-password-hash"
    service = exec {
        priv-lvl = 15
    }
    cmd = permit .*
}

user = operator {
    login = des "encrypted-password-hash"
    service = exec {
        priv-lvl = 1
    }
    cmd = show {
        permit .*
    }
    cmd = permit .* {
        deny "reload"
        deny "configure"
    }
}

group = netops {
    service = exec {
        priv-lvl = 15
    }
}
```

### Docker Deployment

```yaml
services:
  tac_plus:
    image: christian-becker/tac_plus-ng:latest
    container_name: tac_plus
    restart: unless-stopped
    ports:
      - "49:49"
    volumes:
      - ./tac_plus.conf:/etc/tac_plus/tac_plus.conf:ro
      - ./logs:/var/log/tac_plus
```

### Limitations

- Configuration file syntax is idiosyncratic and not intuitive
- No built-in web interface — all management is through config files
- Limited support for modern authentication backends (OAuth, SAML)
- Original repo has slower update cadence

## tacquito

**Stars:** 151+ | **Repo:** `facebookincubator/tacquito` | **Language:** Go

tacquito is Facebook's open-source TACACS+ server implementation written in Go. It implements RFC 8907 from scratch and is designed for modern deployment patterns with containerization and infrastructure-as-code workflows.

### Architecture

tacquito is built as a modular Go application:

1. **TACACS+ protocol handler**: Implements the full RFC 8907 state machine
2. **Authentication backends**: PAM, LDAP, local user database
3. **Authorization engine**: Rule-based command filtering with regex support
4. **Accounting pipeline**: Structured logging with JSON output

### Key Features

- Pure Go implementation — cross-platform, single binary deployment
- RFC 8907 compliant implementation
- JSON-structured accounting logs (ideal for SIEM ingestion)
- Native support for modern deployment (containers, Kubernetes)
- Clean codebase suitable for customization and extension
- Built-in health check endpoints

### Configuration Example

```yaml
# tacquito.yaml
server:
  listen: ":49"
  secret: "shared-secret-key"

backends:
  - type: file
    path: /etc/tacquito/users.yaml

users:
  - username: admin
    password: "$2a$12$hashed-password"
    authorization:
      - permit: ".*"
        priv_level: 15

  - username: viewer
    password: "$2a$12$hashed-password"
    authorization:
      - permit: "show.*"
        priv_level: 1
      - deny: "reload"
      - deny: "configure.*"
```

### Docker Deployment

```yaml
services:
  tacquito:
    image: ghcr.io/facebookincubator/tacquito:latest
    container_name: tacquito
    restart: unless-stopped
    ports:
      - "49:49"
    volumes:
      - ./tacquito.yaml:/etc/tacquito/config.yaml:ro
      - ./users.yaml:/etc/tacquito/users.yaml:ro
      - ./logs:/var/log/tacquito
    healthcheck:
      test: ["CMD", "wget", "--spider", "http://localhost:8080/health"]
      interval: 30s
      timeout: 5s
```

## tac_plus-ng

**Stars:** 151+ | **Repo:** `MarcJHuber/event-driven-servers` | **Language:** C

tac_plus-ng is the next-generation successor to the original tac_plus, maintained by the same author. It adds modern features while preserving backward compatibility with existing tac_plus configurations.

### Key Features

- Backward compatible with tac_plus configuration files
- Event-driven architecture for improved performance
- Enhanced accounting with structured logging
- Active development with regular updates (last push: 2026)
- Improved security hardening
- Docker community images available

### Why tac_plus-ng Over Original tac_plus?

- **Active maintenance**: Regular commits and security patches
- **Better logging**: Structured output formats for SIEM integration
- **Performance**: Event-driven model handles more concurrent sessions
- **Community support**: Active Docker images and deployment guides

### Network Device Configuration

Configure your network devices to point to your self-hosted TACACS+ server:

**Cisco IOS/IOS-XE:**
```
aaa new-model
tacacs server TACACS-PRIMARY
  address ipv4 10.0.0.50
  key shared-secret-key
  timeout 5

aaa authentication login default group tacacs+ local
aaa authorization exec default group tacacs+ local
aaa accounting exec default start-stop group tacacs+
aaa accounting commands 15 default start-stop group tacacs+
```

**Juniper JunOS:**
```
set system tacplus-server 10.0.0.50
set system tacplus-server secret "shared-secret-key"
set system authentication-order tacplus
```

**Arista EOS:**
```
aaa authentication login default group tacacs+ local
aaa authorization exec default group tacacs+ local
tacacs-server host 10.0.0.50 key shared-secret-key
```

## Comparison Table

| Feature | tac_plus | tacquito | tac_plus-ng |
|---------|----------|----------|-------------|
| **Language** | C | Go | C |
| **RFC 8907 Compliant** | Partially | Yes | Yes |
| **IPv6 Support** | Yes | Yes | Yes |
| **LDAP Integration** | Via PAM | Yes | Via PAM |
| **JSON Accounting** | No | Yes | Yes |
| **Web Interface** | No | No | Community projects |
| **Config Format** | Custom | YAML | Custom (compatible) |
| **Container Ready** | Community | Official image | Community |
| **Active Development** | Low | Moderate | High |
| **Cross-Platform** | Linux/Unix | Any (Go) | Linux/Unix |
| **Health Check** | No | Yes | No |
| **Stars** | 236 | 151 | 151 |

## Why Self-Host Your TACACS+ Server?

### Compliance and Audit Requirements

For organizations subject to SOX, PCI-DSS, HIPAA, or SOC 2, TACACS+ accounting provides the granular audit trail required by auditors. Every command executed on every network device is logged with timestamps, user identity, and results. Self-hosting ensures these logs never leave your infrastructure, satisfying data residency requirements.

### Network Segmentation and Zero Trust

A self-hosted TACACS+ server becomes a core component of your zero-trust network architecture. By centralizing authentication and authorization:

- **Privilege escalation control**: Junior engineers get read-only access; senior engineers get full configuration rights
- **Time-based access**: Emergency accounts can be time-limited with automatic expiry
- **Change tracking**: Every `configure terminal`, `write memory`, and `reload` is logged
- **Rapid deprovisioning**: Remove a user from one config file to revoke access across all devices

### Cost vs. Commercial Alternatives

Commercial AAA platforms (Cisco ISE, Aruba ClearPass) start at $5,000-$10,000 annually for small deployments and scale to $50,000+ for enterprise setups. A self-hosted TACACS+ server on a $5/month VPS or existing infrastructure hardware costs virtually nothing beyond administration time.

For network infrastructure security, see our [network scanning tools guide](../2026-04-22-nmap-vs-masscan-vs-rustscan-self-hosted-network-scanning-guide-2026/) and [AAA servers comparison](../2026-04-25-freeradius-vs-toughradius-vs-tac-plus-self-hosted-aaa-servers-2026/).

## FAQ

### What is the difference between TACACS+ and RADIUS?

TACACS+ uses TCP (port 49) and separates authentication, authorization, and accounting into distinct processes. RADIUS uses UDP (ports 1812/1813) and combines authentication and authorization. TACACS+ encrypts the entire packet body while RADIUS only encrypts the password. TACACS+ is preferred for network device administration; RADIUS is preferred for user network access (802.1X, VPN).

### Can TACACS+ authenticate against Active Directory?

Yes. Both tac_plus and tac_plus-ng can use PAM for authentication, and PAM can be configured to authenticate against Active Directory via `sssd` or `winbind`. tacquito supports LDAP directly, which can point to AD's LDAP interface.

### Is TACACS+ secure for remote network device management?

TACACS+ encrypts the entire packet body (except the standard header) using a shared secret key. However, for maximum security, run TACACS+ over an encrypted transport like IPsec or within a management VLAN. Never expose TACACS+ port 49 directly to untrusted networks.

### How do I migrate from a commercial AAA platform to self-hosted TACACS+?

Export your user/group definitions from the commercial platform, convert them to the tac_plus configuration format, and test with a subset of devices before full migration. Most commercial platforms export to CSV or LDIF, which can be scripted into TACACS+ config format.

### Can TACACS+ handle MFA/2FA?

The TACACS+ protocol itself does not natively support MFA. However, you can achieve MFA by using PAM authentication backends that integrate with TOTP (Google Authenticator), RADIUS-based MFA, or SAML/OIDC bridges. tac_plus-ng community projects have explored web-based MFA portals.

### How many network devices can a single TACACS+ server handle?

A well-configured tac_plus or tacquito instance on a modest server (2 vCPU, 4 GB RAM) can handle authentication for hundreds of network devices simultaneously. The bottleneck is typically network latency, not server capacity. For large deployments, deploy multiple instances behind a load balancer.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted TACACS+ Server: tac_plus vs tacquito vs tac_plus-ng",
  "description": "Compare three open-source TACACS+ server implementations for network AAA: the classic tac_plus, modern tacquito (RFC 8907), and actively maintained tac_plus-ng.",
  "datePublished": "2026-05-13",
  "dateModified": "2026-05-13",
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

