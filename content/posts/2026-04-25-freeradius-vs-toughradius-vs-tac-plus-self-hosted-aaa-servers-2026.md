---
title: "FreeRADIUS vs ToughRADIUS vs tac_plus: Self-Hosted AAA Servers 2026"
date: 2026-04-25
tags: ["comparison", "guide", "self-hosted", "networking", "security"]
draft: false
description: "Compare FreeRADIUS, ToughRADIUS, and tac_plus for self-hosted AAA (Authentication, Authorization, Accounting) of network devices. Docker deployment guides, feature comparison, and production configurations for 2026."
---

## Why Self-Host Your AAA Servers?

Centralized AAA (Authentication, Authorization, and Accounting) is the backbone of network infrastructure security. Every time an administrator logs into a switch, router, or firewall, an AAA server verifies their identity, determines what commands they can run, and logs every action they take. Commercial AAA platforms — Cisco ISE, Juniper Mist, or Aruba ClearPass — cost thousands of dollars per year and force your authentication data through cloud infrastructure you don't control.

Self-hosting your AAA stack eliminates these constraints entirely:

- **Zero licensing costs** — open-source AAA servers handle thousands of network devices without per-device fees
- **Full data sovereignty** — authentication logs, command accounting records, and user databases never leave your infrastructure
- **Air-gapped deployment** — AAA servers work on isolated management networks with no internet connectivity required
- **Custom authorization policies** — define granular command-level access rules per user, per device, per time window
- **Protocol flexibility** — RADIUS for WiFi and VPN authentication, TACACS+ for network device admin access, or both simultaneously

For infrastructure teams managing even a modest fleet of switches, routers, and firewalls, having an independent AAA layer is essential. This guide compares three mature open-source AAA servers — each with a distinct approach to protocol support and deployment — and provides production-ready Docker configurations. For complementary network security layers, see our [PacketFence vs FreeRADIUS vs CoovaChilli NAC guide](../2026-04-19-packetfence-vs-freeradius-vs-coovachilli-self-hosted-nac-guide-2026/), our [pfSense vs OPNsense vs IPFire firewall guide](../pfsense-vs-opnsense-vs-ipfire-self-hosted-firewall-router-guide/), and our [Teleport SSH certificate management guide](../2026-04-25-step-ca-vs-teleport-vs-vault-self-hosted-ssh-certificate-management-guide-2026/).

## Tool Overview

| Tool | Stars | Language | Last Updated | Protocols | Best For |
|------|-------|----------|--------------|-----------|----------|
| **[FreeRADIUS](https://github.com/FreeRADIUS/freeradius-server)** | 2,504 | C | April 2026 | RADIUS, TACACS+ (via module) | Enterprise-grade multi-protocol AAA with extensive module ecosystem |
| **[ToughRADIUS](https://github.com/talkincode/toughradius)** | 651 | Go | April 2026 | RADIUS | Modern cloud-native RADIUS server with built-in billing and portal |
| **[tac_plus](https://github.com/facebook/tac_plus)** | 236 | C | August 2025 | TACACS+ | Lightweight, focused TACACS+ daemon for network device authentication |

## FreeRADIUS: Enterprise Multi-Protocol AAA

FreeRADIUS is the most widely deployed open-source RADIUS server and the de facto standard for self-hosted AAA. It supports RADIUS natively and can handle TACACS+ through external modules. The project has been in continuous development since 1999 and powers authentication for millions of enterprise networks, university WiFi deployments, and ISP infrastructures worldwide.

### Architecture

FreeRADIUS uses a modular architecture where authentication backends, authorization policies, and accounting handlers are implemented as loadable modules. The `rlm_*` modules handle authentication (LDAP, SQL, PAP, CHAP, EAP, certificate-based), while `raddb/` configuration files define per-client policies, virtual servers, and accounting rules.

### Docker Deployment

```yaml
version: "3.8"

services:
  freeradius:
    image: freeradius/freeradius-server:latest
    container_name: freeradius
    restart: unless-stopped
    ports:
      - "1812:1812/udp"   # Authentication
      - "1813:1813/udp"   # Accounting
      - "18120:18120/tcp" # FreeRADIUS control socket
    volumes:
      - ./config/radiusd.conf:/etc/freeradius/3.0/radiusd.conf:ro
      - ./config/clients.conf:/etc/freeradius/3.0/clients.conf:ro
      - ./config/users:/etc/freeradius/3.0/users:ro
      - ./config/sites-enabled:/etc/freeradius/3.0/sites-enabled:ro
      - ./config/mods-enabled:/etc/freeradius/3.0/mods-enabled:ro
      - ./certs:/etc/freeradius/3.0/certs:ro
      - ./logs:/var/log/freeradius
    networks:
      aaa_net:
        ipv4_address: 10.100.0.2

  freeradius-db:
    image: postgres:16-alpine
    container_name: freeradius-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: radius
      POSTGRES_USER: radius
      POSTGRES_PASSWORD: ${RADIUS_DB_PASSWORD}
    volumes:
      - radius_data:/var/lib/postgresql/data
    networks:
      - aaa_net

volumes:
  radius_data:

networks:
  aaa_net:
    driver: bridge
    ipam:
      config:
        - subnet: 10.100.0.0/24
```

### Core Configuration

The `clients.conf` file defines which network devices (NAS clients) are allowed to query the AAA server:

```conf
# clients.conf - Define permitted network devices
client switch_core_01 {
    ipaddr = 10.0.1.0/24
    secret = ${CLIENT_SECRET_CORE_SWITCHES}
    shortname = core-switches
    require_message_authenticator = yes
    nas_type = cisco
}

client router_edge_01 {
    ipaddr = 10.0.2.10
    secret = ${CLIENT_SECRET_EDGE_ROUTERS}
    shortname = edge-routers
    require_message_authenticator = yes
    nas_type = juniper
}
```

The `users` file maps usernames to authorization profiles:

```conf
# users - User authorization policies
"netadmin" Cleartext-Password := "SecureP@ss123"
    Service-Type = Administrative-User,
    Cisco-AVPair = "shell:roles=network-admin",
    Reply-Message = "Welcome, network admin"

"junior_ops" Cleartext-Password := "OpsP@ss456"
    Service-Type = Administrative-User,
    Cisco-AVPair = "shell:roles=network-operator",
    Reply-Message = "Read-only access granted"

# Default deny
DEFAULT
    Auth-Type := Reject,
    Reply-Message = "Access denied - unknown user"
```

For production deployments, replace cleartext passwords with LDAP or SQL-backed authentication using the `rlm_ldap` or `rlm_sql` modules. FreeRADIUS also supports EAP-TLS for certificate-based authentication — ideal for 802.1X network access control.

### Authorization Policy Example

FreeRADIUS's `sites-enabled/default` virtual server lets you define complex authorization logic:

```conf
authorize {
    # Check if user exists in the users file
    files

    # If not found, try LDAP
    if (!ok) {
        ldap
    }

    # Enforce time-based access
    if ("%{control:Auth-Type}" == "Reject") {
        reject
    }

    # Log successful authentications
    if (ok) {
        update reply {
            Reply-Message := "Authentication successful"
        }
    }
}

accounting {
    detail
    sql
}
```

## ToughRADIUS: Modern Cloud-Native RADIUS

ToughRADIUS is a modern RADIUS server written in Go, designed from the ground up for cloud-native deployments. It includes a built-in web management interface, billing system, and captive portal — making it a self-contained solution for ISP and hospitality WiFi deployments.

### Architecture

Unlike FreeRADIUS's modular C architecture, ToughRADIUS is a monolithic Go binary with integrated SQLite/MySQL/PostgreSQL storage, a RESTful API, and a web dashboard. This makes it significantly easier to deploy and manage, at the cost of some of FreeRADIUS's deep customization options.

### Docker Deployment

```yaml
version: "3.8"

services:
  tougradius:
    image: tougradius/tougradius:latest
    container_name: tougradius
    restart: unless-stopped
    ports:
      - "1812:1812/udp"
      - "1813:1813/udp"
      - "8080:8080/tcp"    # Web management dashboard
      - "9090:9090/tcp"    # API endpoint
    environment:
      - TOUGHRADIUS_DATABASE_URL=postgres://radius:${RADIUS_DB_PASSWORD}@toughradius-db:5432/toughradius?sslmode=disable
      - TOUGHRADIUS_ADMIN_USERNAME=admin
      - TOUGHRADIUS_ADMIN_PASSWORD=${ADMIN_PASSWORD}
      - TOUGHRADIUS_SECRET_KEY=${SECRET_KEY}
    volumes:
      - toughradius_data:/data
      - ./logs:/var/log/toughradius
    depends_on:
      - toughradius-db
    networks:
      - aaa_net

  toughradius-db:
    image: postgres:16-alpine
    container_name: toughradius-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: tougradius
      POSTGRES_USER: radius
      POSTGRES_PASSWORD: ${RADIUS_DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - aaa_net

volumes:
  tougradius_data:
  postgres_data:

networks:
  aaa_net:
    driver: bridge
```

### REST API Integration

ToughRADIUS exposes a comprehensive REST API for programmatic management:

```bash
# Create a new RADIUS user
curl -X POST http://localhost:9090/api/v1/users \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "network_ops_01",
    "password": "SecureP@ss789",
    "status": 1,
    "macaddr": "",
    "group_name": "network-admins",
    "exp_date": "2027-04-25"
  }'

# Query active sessions
curl http://localhost:9090/api/v1/online \
  -H "Authorization: Bearer ${API_TOKEN}"

# Get accounting records
curl "http://localhost:9090/api/v1/accounting?start=2026-04-01&end=2026-04-25" \
  -H "Authorization: Bearer ${API_TOKEN}"
```

The web dashboard (port 8080) provides user management, real-time session monitoring, accounting reports, and RADIUS client configuration — all through a browser interface. This makes ToughRadius significantly more accessible for teams without dedicated RADIUS expertise.

## tac_plus: Focused TACACS+ Daemon

tac_plus is Facebook's open-source TACACS+ daemon, designed specifically for network device authentication, authorization, and accounting. Unlike FreeRADIUS's multi-protocol approach, tac_plus does one thing and does it well: it speaks TACACS+ and nothing else.

### Architecture

tac_plus uses a single configuration file (`tac_plus.conf`) that defines users, groups, device definitions, and command-level authorization policies. The simplicity of this model makes it easy to audit and maintain, especially for teams that only need TACACS+ (not RADIUS) for their network device management.

### Docker Deployment

Since tac_plus doesn't have an official Docker image, a Dockerfile builds from source:

```dockerfile
FROM alpine:3.19 AS builder
RUN apk add --no-cache build-base git openssl-dev
RUN git clone https://github.com/facebook/tac_plus.git /src/tac_plus
WORKDIR /src/tac_plus
RUN make

FROM alpine:3.19
RUN apk add --no-cache libcrypto3 libssl3
COPY --from=builder /src/tac_plus/tac_plus /usr/local/bin/tac_plus
COPY tac_plus.conf /etc/tac_plus.conf
EXPOSE 49
CMD ["tac_plus", "-C", "/etc/tac_plus.conf", "-d"]
```

```yaml
version: "3.8"

services:
  tac_plus:
    build:
      context: ./tac_plus
      dockerfile: Dockerfile
    container_name: tac_plus
    restart: unless-stopped
    ports:
      - "49:49/tcp"   # TACACS+ port
    volumes:
      - ./config/tac_plus.conf:/etc/tac_plus.conf:ro
      - ./logs:/var/log/tac_plus
    networks:
      aaa_net:
        ipv4_address: 10.100.0.3

networks:
  aaa_net:
    driver: bridge
    ipam:
      config:
        - subnet: 10.100.0.0/24
```

### Configuration

The `tac_plus.conf` file combines user definitions, group policies, and device access rules:

```conf
# tac_plus.conf - TACACS+ server configuration

# Global settings
accounting file = /var/log/tac_plus/acct.log

# User definitions with DES-encrypted passwords
user = netadmin {
    login = des $6$rounds=656000$saltsalt$encrypted_hash
    member = network-admins
}

user = junior_ops {
    login = des $6$rounds=656000$more_salt$another_hash
    member = network-operators
}

# Group-based authorization
group = network-admins {
    default service = permit
    service = exec {
        priv-lvl = 15
    }
    cmd = permit .*
}

group = network-operators {
    default service = deny
    service = exec {
        priv-lvl = 1
    }
    cmd = show {
        permit .*
    }
    cmd = deny .*
}

# Device definitions
host = core_switch_01 {
    address = 10.0.1.10
    key = ${TACACS_SHARED_SECRET}
}

host = edge_router_01 {
    address = 10.0.2.10
    key = ${TACACS_SHARED_SECRET}
}
```

The command-level authorization is the key differentiator for TACACS+ over RADIUS: you can permit or deny individual CLI commands per user group. The `network-operators` group above can only run `show` commands, while `network-admins` have full CLI access.

## Feature Comparison

| Feature | FreeRADIUS | ToughRADIUS | tac_plus |
|---------|-----------|-------------|----------|
| **RADIUS** | ✅ Full support | ✅ Full support | ❌ Not supported |
| **TACACS+** | ⚠️ Via external module | ❌ Not supported | ✅ Native support |
| **EAP/TLS** | ✅ 802.1X support | ❌ Not supported | ❌ Not supported |
| **LDAP backend** | ✅ | ✅ | ❌ (local users only) |
| **SQL backend** | ✅ PostgreSQL, MySQL, SQLite | ✅ PostgreSQL, MySQL | ❌ (local file) |
| **Web dashboard** | ❌ (use daloRADIUS) | ✅ Built-in | ❌ |
| **REST API** | ❌ | ✅ | ❌ |
| **Command-level auth** | ⚠️ Limited | ❌ | ✅ Granular |
| **Accounting** | ✅ Detailed | ✅ With billing | ✅ Basic logging |
| **Captive portal** | ❌ | ✅ Built-in | ❌ |
| **Certificate auth** | ✅ EAP-TLS, PEAP | ❌ | ❌ |
| **High availability** | ✅ Proxy chains | ✅ Clustering | ❌ Single node |
| **Docker image** | ✅ Official | ✅ Community | 🔧 Build from source |
| **Active development** | ✅ Very active | ✅ Active | ⚠️ Low activity |
| **Learning curve** | Steep | Moderate | Low |

## Choosing the Right AAA Server

### Use FreeRADIUS when:
- You need both RADIUS (WiFi, VPN, 802.1X) and TACACS+ (network device admin) from a single server
- You require EAP-TLS certificate authentication for network access control
- Your infrastructure includes diverse vendor equipment (Cisco, Juniper, Aruba, MikroTik)
- You need LDAP/Active Directory integration for centralized user management
- You want a battle-tested solution with 25+ years of production deployment history

### Use ToughRADIUS when:
- You're running an ISP, hotel, or campus WiFi that needs user billing and captive portal
- You want a modern web dashboard and REST API without deploying separate management tools
- Your team lacks deep RADIUS expertise and needs an easier management experience
- You primarily need RADIUS (not TACACS+) for your use case
- Cloud-native deployment with PostgreSQL integration fits your existing infrastructure

### Use tac_plus when:
- You only need TACACS+ for network device authentication (no RADIUS required)
- You want granular command-level authorization per user group
- You prefer a simple, auditable single-file configuration
- Your network uses Cisco IOS or similar TACACS+-compatible devices exclusively
- You need a lightweight daemon that runs with minimal resource footprint

## Protocol Selection: RADIUS vs TACACS+

Understanding the difference between these two AAA protocols is critical for choosing the right server:

| Aspect | RADIUS | TACACS+ |
|--------|--------|---------|
| **Transport** | UDP (ports 1812/1813) | TCP (port 49) |
| **Encryption** | Password-only encryption | Full packet encryption |
| **Authentication** | Combined auth + authz | Separated auth, authz, and accounting |
| **Authorization** | Limited (AV pairs) | Granular (command-level) |
| **Accounting** | Separate port (1813) | Integrated |
| **Best for** | WiFi, VPN, 802.1X | Network device admin (CLI) |
| **Vendor support** | Universal | Primarily Cisco, Juniper, Arista |

For most self-hosted infrastructures, you'll need both protocols: RADIUS for WiFi and VPN user authentication, TACACS+ for network device administrative access. FreeRADIUS can handle both (with the TACACS+ module), while ToughRADIUS and tac_plus each specialize in one protocol.

## Production Hardening

Regardless of which AAA server you choose, apply these security hardening steps:

```bash
# 1. Restrict AAA server to management network only
# Add iptables rules on the Docker host:
iptables -A INPUT -p udp --dport 1812 -s 10.100.0.0/24 -j ACCEPT
iptables -A INPUT -p udp --dport 1813 -s 10.100.0.0/24 -j ACCEPT
iptables -A INPUT -p tcp --dport 49 -s 10.100.0.0/24 -j ACCEPT
iptables -A INPUT -p udp --dport 1812 -j DROP
iptables -A INPUT -p udp --dport 1813 -j DROP
iptables -A INPUT -p tcp --dport 49 -j DROP

# 2. Use strong shared secrets (minimum 32 characters)
openssl rand -base64 32

# 3. Enable accounting to detect unauthorized access attempts
# In FreeRADIUS: enable rlm_sql and rlm_detail modules
# In tac_plus: set "accounting file = /var/log/tac_plus/acct.log"

# 4. Monitor AAA server logs for failed authentication spikes
# Failed auth rate > 5/min may indicate brute-force or misconfiguration
```

## FAQ

### What is the difference between AAA and NAC?

AAA (Authentication, Authorization, Accounting) verifies user identity, determines what actions they can perform, and logs their activity. NAC (Network Access Control) focuses on device posture assessment — checking whether a connecting device meets security requirements before granting network access. While FreeRADIUS can serve both roles, NAC platforms like PacketFence add endpoint compliance checking, quarantine enforcement, and guest management on top of the underlying AAA protocols. For a deeper comparison, see our [PacketFence vs FreeRADIUS vs CoovaChilli NAC guide](../2026-04-19-packetfence-vs-freeradius-vs-coovachilli-self-hosted-nac-guide-2026/).

### Can FreeRADIUS replace Cisco ISE?

For small to medium deployments (up to a few hundred network devices), FreeRADIUS can replace most Cisco ISE functionality: RADIUS authentication, TACACS+ device admin, 802.1X network access control, and detailed accounting. However, ISE provides advanced features like TrustSec SGT tagging, pxGrid ecosystem integration, and automated threat response that FreeRADIUS cannot replicate without significant custom development.

### Should I use RADIUS or TACACS+ for switch and router authentication?

Use TACACS+ for network device administrative access because it encrypts the entire packet (not just the password) and supports command-level authorization. Use RADIUS for WiFi authentication, VPN user login, and 802.1X port-based access control because it supports EAP methods and has broader client compatibility. If your infrastructure needs both, FreeRADIUS is the only open-source server that handles both protocols.

### How do I back up AAA server configurations?

For FreeRADIUS, back up the entire `/etc/freeradius/3.0/` directory including `radiusd.conf`, `clients.conf`, `users`, `sites-enabled/`, and `mods-enabled/`. For tac_plus, back up the single `tac_plus.conf` file and the accounting log. For ToughRADIUS, export the PostgreSQL database using `pg_dump` and back up the `/data` volume. Automate backups with a cron job that runs daily and stores copies on a separate system.

### Can I migrate from tac_plus to FreeRADIUS?

Yes. tac_plus uses a simple text-based configuration format that maps to FreeRADIUS's TACACS+ module. The main differences are: FreeRADIUS uses separate files for users (`users`) and clients (`clients.conf`), while tac_plus combines everything in one file. Command-level authorization rules translate directly — tac_plus `cmd = permit .*` becomes FreeRADIUS `Cisco-AVPair = "shell:roles=network-admin"`. The shared secret and device IP definitions carry over without modification.

### Is ToughRADIUS production-ready for enterprise use?

ToughRADIUS is production-ready for ISP and hospitality WiFi deployments where RADIUS authentication, user billing, and captive portal are the primary requirements. Its active development (updated April 2026) and built-in web dashboard make it easier to operate than FreeRADIUS for teams without dedicated AAA expertise. However, it lacks TACACS+ support, EAP-TLS certificate authentication, and the deep vendor compatibility that FreeRADIUS provides — making it unsuitable as a replacement for network device AAA in enterprise environments.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "FreeRADIUS vs ToughRADIUS vs tac_plus: Self-Hosted AAA Servers 2026",
  "description": "Compare FreeRADIUS, ToughRADIUS, and tac_plus for self-hosted AAA (Authentication, Authorization, Accounting) of network devices. Docker deployment guides, feature comparison, and production configurations for 2026.",
  "datePublished": "2026-04-25",
  "dateModified": "2026-04-25",
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
