---
title: "Self-Hosted TACACS+ Servers: tac_plus vs tac_plus-ng vs tacquito (2026)"
date: "2026-05-18"
tags: ["tacacs", "authentication", "network-security", "aaa", "access-control", "tacacs-plus"]
draft: false
---

Terminal Access Controller Access-Control System Plus (TACACS+) is a protocol designed for centralized authentication, authorization, and accounting (AAA) of network devices. Unlike RADIUS which combines authentication and authorization, TACACS+ separates these functions, enabling granular per-command authorization policies — making it the preferred choice for managing router, switch, and firewall access in enterprise networks.

In this guide, we compare three open-source TACACS+ server implementations: **tac_plus** (the original reference implementation), **tac_plus-ng** (a modern fork with active development), and **tacquito** (a lightweight alternative).

## What Is TACACS+ and Why Does It Matter?

TACACS+ operates over TCP port 49, encrypting the entire packet body (unlike RADIUS which only encrypts passwords). This makes it more secure for transmitting detailed authorization attributes. The protocol's key advantage is command-level authorization — you can specify exactly which CLI commands each user or group is allowed to execute on network devices.

Typical use cases include:

- **Network device administration** — Centralized login for Cisco IOS, Juniper Junos, Arista EOS
- **Command authorization** — Restricting which users can run `configure terminal`, `write memory`, or `reload`
- **Audit logging** — Tracking every command executed on every device for compliance
- **Role-based access** — Mapping Active Directory or LDAP groups to device privilege levels

## tac_plus (Original Reference Implementation)

**GitHub:** [DesktopNetworks/tac_plus](https://github.com/DesktopNetworks/tac_plus) · **Stars:** 236 · **License:** Custom

tac_plus is the original open-source TACACS+ daemon, based on Cisco's original reference implementation. It provides a mature, battle-tested TACACS+ server with comprehensive configuration options and broad device compatibility.

### Configuration

The configuration uses a simple text-based format with clear group and user definitions:

```
# /etc/tac_plus/tac_plus.conf
key = "shared-secret-key"

# Accounting
accounting file = /var/log/tac_plus/acct.log

# Group definitions
group = netadmin {
    default service = permit
    service = exec {
        priv-lvl = 15
    }
    cmd = permit .*
}

group = readonly {
    default service = permit
    service = exec {
        priv-lvl = 1
    }
    cmd = permit show.*
    cmd = deny .*
}

# User definitions
user = admin {
    member = netadmin
    login = cleartext "admin-password"
}

user = operator {
    member = readonly
    login = DES "encrypted-hash-here"
}
```

### Features

- Full TACACS+ protocol support (authentication, authorization, accounting)
- Per-command authorization with regex-based command matching
- Privilege level mapping (0-15)
- DES and cleartext password support
- File-based accounting logging
- Compatible with Cisco IOS, Junos, and most enterprise network OS

## tac_plus-ng (Next Generation Fork)

**GitHub:** [sparticvs/tac_plus-ng](https://github.com/sparticvs/tac_plus-ng) · **Stars:** 151 · **License:** GPL

tac_plus-ng is an actively maintained fork of the original tac_plus, adding modern features like LDAP/Active Directory integration, improved security, and better logging.

### Configuration with LDAP Backend

```
# /etc/tac_plus-ng/tac_plus-ng.conf
key = "shared-secret-key"

# LDAP integration
ldap {
    uri = "ldap://ldap.example.com:389"
    base_dn = "dc=example,dc=com"
    bind_dn = "cn=tacacs,ou=services,dc=example,dc=com"
    bind_pw = "ldap-password"
    user_filter = "(uid=%s)"
    group_attr = "memberOf"
}

# Group mapping from LDAP
group = "cn=network-admins,ou=groups,dc=example,dc=com" {
    default service = permit
    service = exec {
        priv-lvl = 15
    }
    cmd = permit .*
}

group = "cn=network-ops,ou=groups,dc=example,dc=com" {
    default service = permit
    service = exec {
        priv-lvl = 5
    }
    cmd = permit show.*
    cmd = deny .*
}

# Local fallback users
user = localadmin {
    login = SHA256 "hashed-password"
    member = "cn=network-admins,ou=groups,dc=example,dc=com"
}
```

### Features

- All features of original tac_plus
- LDAP and Active Directory integration
- SHA256 password hashing (vs. legacy DES)
- Improved syslog integration
- Active development with regular bug fixes
- Better error messages and debugging

## tacquito

**GitHub:** [mcr/tacquito](https://github.com/mcr/tacquito) · **Stars:** 151 · **License:** BSD

tacquito is a lightweight TACACS+ server implementation written in C, designed to be simple and portable. It provides basic TACACS+ authentication and authorization without the complexity of the full tac_plus configuration syntax.

### Configuration

```
# /etc/tacquito/users
admin:DES:encrypted-hash:netadmin
operator:DES:encrypted-hash:readonly
viewer:DES:encrypted-hash:monitor

# /etc/tacquito/groups
netadmin:15:permit .*
readonly:1:permit show.*:deny .*
monitor:1:permit show.*:deny .*
```

### Features

- Lightweight C implementation
- Simple file-based user/group configuration
- DES password support
- Basic command authorization
- Low resource footprint
- Portable across Unix-like systems

## Comparison Table

| Feature | tac_plus | tac_plus-ng | tacquito |
|---------|----------|-------------|----------|
| **License** | Custom | GPL | BSD |
| **Language** | C | C | C |
| **LDAP/AD Integration** | No | Yes | No |
| **Password Hashing** | DES, cleartext | DES, SHA256 | DES |
| **Per-Command Auth** | Yes (regex) | Yes (regex) | Yes (regex) |
| **Privilege Levels** | 0-15 | 0-15 | 0-15 |
| **Accounting** | File logging | File + syslog | Basic |
| **Active Development** | No (last update ~2020) | Yes (2024+) | Minimal |
| **GitHub Stars** | 236 | 151 | 151 |
| **Configuration Complexity** | Moderate | Moderate | Simple |
| **Docker Support** | Community | Community | Community |

## Docker Deployment

### tac_plus-ng Docker Compose

```yaml
# docker-compose.yml for tac_plus-ng
version: '3'
services:
  tacplus-ng:
    image: ghcr.io/sparticvs/tac_plus-ng:latest
    ports:
      - "49:49/tcp"
    volumes:
      - ./tac_plus-ng.conf:/etc/tac_plus-ng/tac_plus-ng.conf:ro
      - tacplus-logs:/var/log/tac_plus-ng
    restart: unless-stopped
    networks:
      - aaa-net

volumes:
  tacplus-logs:

networks:
  aaa-net:
    driver: bridge
```

### tac_plus Docker Compose

```yaml
# docker-compose.yml for tac_plus
version: '3'
services:
  tacplus:
    image: timacplus/tac_plus:latest
    ports:
      - "49:49/tcp"
    volumes:
      - ./tac_plus.conf:/etc/tac_plus/tac_plus.conf:ro
      - tacplus-data:/var/lib/tac_plus
      - tacplus-logs:/var/log/tac_plus
    restart: unless-stopped

volumes:
  tacplus-data:
  tacplus-logs:
```

### Device Configuration (Cisco IOS)

```cisco
! Configure network device to use TACACS+
aaa new-model
aaa authentication login default group tacacs+ local
aaa authorization exec default group tacacs+ local
aaa authorization commands 15 default group tacacs+ local
aaa authorization commands 1 default group tacacs+ local
aaa accounting exec default start-stop group tacacs+
aaa accounting commands 15 default start-stop group tacacs+

! TACACS+ server configuration
tacacs server TACACS-PRIMARY
  address ipv4 10.0.0.50
  key shared-secret-key
  timeout 5
```

## Choosing the Right TACACS+ Server

### Choose tac_plus-ng if:
- You need LDAP or Active Directory integration
- You want modern password hashing (SHA256)
- You need active development and bug fixes
- You're deploying in a modern enterprise environment

### Choose tac_plus if:
- You need the original, battle-tested implementation
- You have simple file-based user management needs
- You're deploying in an isolated environment without LDAP
- You have existing tac_plus configurations to migrate

### Choose tacquito if:
- You need a minimal, lightweight TACACS+ server
- You're deploying on resource-constrained hardware
- You prefer BSD-licensed software
- Your authorization requirements are simple

## Why Self-Host Your TACACS+ Server?

Centralized AAA management is critical for network security compliance. Self-hosting your TACACS+ server ensures that authentication traffic never leaves your network perimeter, audit logs remain under your control, and access policies can be customized without vendor-specific constraints.

For organizations subject to regulatory frameworks like PCI-DSS, SOX, or HIPAA, TACACS+ command-level authorization provides the granular access controls and audit trails required for compliance. Every configuration change on every network device is logged with the operator's identity, timestamp, and exact command executed.

Compared to commercial AAA solutions like Cisco ISE or Aruba ClearPass, open-source TACACS+ servers eliminate per-device licensing costs and vendor lock-in. They integrate with existing LDAP/Active Directory infrastructure and can be deployed alongside other open-source network management tools like LibreNMS, Oxidized, or Rancid for a complete self-hosted network operations stack.

For broader AAA platform comparisons, see our [self-hosted auth platforms guide](../2026-05-10-self-hosted-auth-platforms-logto-vs-supertokens-vs-ory-kratos/) and [TACACS+ server deployment guide](../2026-05-13-self-hosted-tacacs-server-tac-plus-vs-tacquito-vs-tac-plus-ng/). For related network device management, our [network configuration management guide](../2026-05-05-self-hosted-network-configuration-management-ansible-nornir-netbox-guide/) covers automated config backup and compliance.

## FAQ

### What is the difference between TACACS+ and RADIUS?

TACACS+ separates authentication, authorization, and accounting into distinct processes, uses TCP (port 49) for reliable transport, and encrypts the entire packet body. RADIUS combines authentication and authorization, uses UDP (ports 1812/1813), and only encrypts the password field. TACACS+ is preferred for network device administration due to its command-level authorization capabilities.

### Can TACACS+ integrate with Active Directory?

Yes, tac_plus-ng supports LDAP/Active Directory integration natively. You configure the LDAP server URI, bind credentials, and group mapping in the configuration file. Users authenticate with their AD credentials, and their group membership determines their privilege level and allowed commands on network devices.

### Is TACACS+ secure enough for production use?

TACACS+ encrypts the entire packet body using a shared secret key, protecting credentials and authorization data in transit. For production deployments, use strong shared secrets (minimum 16 characters, random), ensure the TACACS+ server is on a secure management network, and regularly review accounting logs. tac_plus-ng's SHA256 password hashing adds an additional layer of security for local accounts.

### How do I configure Cisco IOS to use TACACS+?

Enable AAA with `aaa new-model`, configure authentication and authorization to use the TACACS+ server group, define the server address and shared key, and set up accounting for exec sessions and commands. A local fallback account ensures you can still access the device if the TACACS+ server becomes unavailable.

### Can I use TACACS+ with Juniper or Arista devices?

Yes. Juniper JunOS supports TACACS+ through `set system authentication-order tacplus` and `set system login tacplus-server`. Arista EOS uses `aaa authentication login default group tacacs+ local` with `tacacs-server host` configuration. The protocol is vendor-agnostic and works with any network OS that implements the TACACS+ client.

### What happens if the TACACS+ server goes down?

Configure a local fallback account on each device. The `aaa authentication login default group tacacs+ local` directive on Cisco IOS tries TACACS+ first, then falls back to the local username database. This ensures administrators can still access devices during TACACS+ server outages, though they'll bypass centralized authorization and accounting.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted TACACS+ Servers: tac_plus vs tac_plus-ng vs tacquito (2026)",
  "description": "Compare three open-source TACACS+ server implementations for centralized network device AAA management. Includes configuration examples and Docker deployment guides.",
  "datePublished": "2026-05-18",
  "dateModified": "2026-05-18",
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
