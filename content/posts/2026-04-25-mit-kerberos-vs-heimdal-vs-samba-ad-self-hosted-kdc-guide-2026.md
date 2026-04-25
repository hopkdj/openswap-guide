---
title: "MIT Kerberos vs Heimdal vs Samba AD: Self-Hosted KDC Guide 2026"
date: 2026-04-25
tags: ["comparison", "guide", "self-hosted", "security", "authentication"]
draft: false
description: "Complete guide to self-hosted Kerberos Key Distribution Centers. Compare MIT Kerberos, Heimdal, and Samba AD for enterprise authentication, SSO, and network security."
---

## Why Self-Host a Kerberos KDC

Kerberos is the authentication backbone of most enterprise networks. When you log into a Windows domain, access a corporate file share, or authenticate to a Hadoop cluster, Kerberos tickets are almost certainly involved behind the scenes. The protocol provides mutual authentication — both client and server verify each other's identity — and single sign-on across an entire realm without ever transmitting passwords over the network.

Running your own Kerberos Key Distribution Center (KDC) means you control the entire authentication chain. No cloud dependency, no third-party identity provider, no subscription fees. You manage the principal database, set ticket lifetimes, define cross-realm trusts, and audit every authentication event. For organizations with strict data sovereignty requirements or air-gapped networks, a self-hosted KDC is not optional — it is the only viable option.

This guide compares three open-source Kerberos implementations — **MIT Kerberos**, **Heimdal**, and **Samba AD** — covering architecture differences, deployment patterns, and real Docker Compose configurations you can run today. For related reading on directory services and authentication, see our [LDAP directory servers guide](../self-hosted-ldap-directory-servers-openldap-389ds-freeipa-guide-2026/), [lightweight LDAP auth guide](../lldap-vs-glauth-lightweight-ldap-self-hosted-auth-guide/), and [OIDC SSO comparison](../dex-vs-kanidm-vs-rauthy-self-hosted-oidc-sso-guide-2026/).

## How Kerberos Authentication Works

Before comparing implementations, it helps to understand the core protocol flow:

1. **AS-REQ** — The client sends an Authentication Service request to the KDC with its principal name (e.g., `user@EXAMPLE.COM`).
2. **AS-REP** — The KDC's Authentication Server verifies the client's password hash and returns a Ticket-Granting Ticket (TGT), encrypted with the client's secret key.
3. **TGS-REQ** — The client decrypts the TGT and presents it to the KDC's Ticket-Granting Service, requesting access to a specific service.
4. **TGS-REP** — The KDC issues a service ticket encrypted with the target service's secret key.
5. **AP-REQ/AP-REP** — The client presents the service ticket to the target server, which decrypts it and optionally sends a mutual authentication response.

The entire flow happens without transmitting passwords. Tickets are time-limited (typically 8-10 hours for TGTs) and can be renewed without re-authentication. This is what makes Kerberos both secure and convenient for enterprise environments.

## MIT Kerberos (krb5)

MIT Kerberos is the reference implementation of the Kerberos V5 protocol. It is the most widely deployed open-source KDC and ships by default with most Linux distributions including Red Hat, Debian, and Ubuntu. The project is hosted at [krb5/krb5](https://github.com/krb5/krb5) with 595+ GitHub stars and active development as of April 2026.

### Architecture

MIT krb5 provides three core daemons:

- **krb5kdc** — The KDC daemon handling AS and TGS requests
- **kadmind** — The administrative server for principal management
- **krb5prop** — The propagation daemon for KDC database replication

The principal database is stored in Berkeley DB format (or LMDB in newer versions) and supports multi-master replication through database propagation.

### Deployment with Docker Compose

```yaml
version: "3.8"
services:
  krb5kdc:
    image: gcavusoglu/krb5-server:latest
    container_name: krb5-kdc
    hostname: kdc.example.com
    ports:
      - "88:88/tcp"
      - "88:88/udp"
      - "464:464/tcp"
      - "464:464/udp"
      - "749:749/tcp"
    volumes:
      - ./krb5.conf:/etc/krb5.conf
      - ./kdc.conf:/var/kerberos/krb5kdc/kdc.conf
      - kdc-data:/var/lib/krb5kdc
    environment:
      - KRB5_REALM=EXAMPLE.COM
      - KRB5_KDC=kdc.example.com
      - KRB5_ADMINSERVER=kdc.example.com
      - KRB5_PASS=adminpassword123
    restart: unless-stopped
    networks:
      kdc-net:
        ipv4_address: 10.10.0.10

  kadmind:
    image: gcavusoglu/krb5-server:latest
    container_name: krb5-admin
    hostname: kdc.example.com
    ports:
      - "749:749/tcp"
    volumes:
      - ./krb5.conf:/etc/krb5.conf
      - ./kdc.conf:/var/kerberos/krb5kdc/kdc.conf
      - kdc-data:/var/lib/krb5kdc
    environment:
      - KRB5_REALM=EXAMPLE.COM
      - KRB5_KDC=kdc.example.com
      - KRB5_ADMINSERVER=kdc.example.com
    depends_on:
      - krb5kdc
    restart: unless-stopped
    networks:
      kdc-net:
        ipv4_address: 10.10.0.11

volumes:
  kdc-data:

networks:
  kdc-net:
    driver: bridge
    ipam:
      config:
        - subnet: 10.10.0.0/24
```

### Key Configuration Files

The `/etc/krb5.conf` client configuration defines realms, KDC locations, and ticket policies:

```ini
[libdefaults]
    default_realm = EXAMPLE.COM
    dns_lookup_realm = false
    dns_lookup_kdc = false
    ticket_lifetime = 24h
    renew_lifetime = 7d
    forwardable = true
    rdns = false

[realms]
    EXAMPLE.COM = {
        kdc = kdc.example.com:88
        admin_server = kdc.example.com:749
    }

[domain_realm]
    .example.com = EXAMPLE.COM
    example.com = EXAMPLE.COM
```

The KDC-specific `/var/kerberos/krb5kdc/kdc.conf` sets encryption types and database parameters:

```ini
[kdcdefaults]
    kdc_ports = 88
    kdc_tcp_ports = 88

[realms]
    EXAMPLE.COM = {
        database_name = /var/lib/krb5kdc/principal
        admin_keytab = /var/lib/krb5kdc/kadm5.keytab
        acl_file = /var/lib/krb5kdc/kadm5.acl
        key_stash_file = /var/lib/krb5kdc/.k5.EXAMPLE.COM
        max_life = 10h 0m 0s
        max_renewable_life = 7d 0h 0m 0s
        supported_enctypes = aes256-cts:normal aes128-cts:normal
        default_principal_flags = +preauth
    }
```

## Heimdal

Heimdal is an alternative Kerberos V5 implementation originally developed by the Swedish Royal Institute of Technology (KTH). It is the default Kerberos implementation on macOS and FreeBSD, and is now maintained as an open-source project at [heimdal/heimdal](https://github.com/heimdal/heimdal) with 364+ GitHub stars.

### Architecture Differences from MIT Kerberos

Heimdal shares the same protocol implementation as MIT krb5 but differs in several key areas:

- **Database backend** — Uses HDB (Heimdal Database) with support for SQLite, LDAP, and Samba LDB backends, whereas MIT krb5 uses Berkeley DB/LMDB
- **Integrated HIERARCHICAL** — Supports hierarchical realms and cross-realm trusts more natively
- **PKINIT** — Has first-class smart card and certificate-based authentication built in
- **OTP support** — Includes one-time password integration out of the box
- **Language** — Written in C like MIT krb5, but with a different API and plugin architecture

Heimdal's `kdc` and `kadmin` daemons are separate binaries, similar to MIT krb5. The admin interface uses a command-line tool called `kadmin` (same name as MIT, different implementation).

### Deployment with Docker Compose

```yaml
version: "3.8"
services:
  heimdal-kdc:
    image: linuxserver/heimdal:latest
    container_name: heimdal-kdc
    hostname: kdc.example.com
    ports:
      - "88:88/tcp"
      - "88:88/udp"
      - "464:464/tcp"
      - "464:464/udp"
    volumes:
      - ./heimdal-conf:/config
      - heimdal-data:/var/lib/heimdal
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Etc/UTC
    restart: unless-stopped
    networks:
      kdc-net:
        ipv4_address: 10.10.0.20

volumes:
  heimdal-data:

networks:
  kdc-net:
    driver: bridge
    ipam:
      config:
        - subnet: 10.10.0.0/24
```

### Client Configuration

Heimdal uses `/etc/krb5.conf` like MIT krb5 but also supports a separate `krb5-config` file format. The configuration syntax is largely compatible, making migration between implementations straightforward:

```ini
[libdefaults]
    default_realm = EXAMPLE.COM
    default_tgs_enctypes = aes256-cts-hmac-sha1-96
    default_tkt_enctypes = aes256-cts-hmac-sha1-96

[realms]
    EXAMPLE.COM = {
        kdc = kdc.example.com
        admin_server = kdc.example.com
    }
```

## Samba Active Directory

Samba AD provides a complete Active Directory Domain Controller implementation with an integrated Kerberos KDC. While MIT Kerberos and Heimdal are pure KDC implementations, Samba AD bundles Kerberos alongside LDAP directory services, DNS, Group Policy, and file sharing in a single platform.

Samba's Kerberos implementation is based on Heimdal's codebase but has been heavily modified to interoperate with Windows Active Directory. The project at [samba-team/samba](https://github.com/samba-team/samba) has over 6,000+ stars and is one of the most active open-source directory projects.

### Architecture

Samba AD runs as a single daemon (`samba`) that internally manages multiple services:

- **KDC** — Heimdal-derived Kerberos implementation with AD-specific extensions
- **LDAP** — Samba LDB (Lightweight Database) providing directory services
- **DNS** — Built-in DNS server with dynamic update support
- **CIFS/SMB** — File and print services
- **RPC/DCERPC** — Remote Procedure Call interfaces for AD management

Unlike MIT Kerberos and Heimdal which require separate tools for principal management, Samba AD uses `samba-tool` for all administrative tasks:

```bash
# Create a new user principal
samba-tool user create jsmith 'P@ssw0rd!' --given-name="John" --surname="Smith"

# Create a service principal
samba-tool spn add HTTP/webserver.example.com jsmith

# List all principals
samba-tool user list

# Check Kerberos tickets
kinit jsmith@EXAMPLE.COM
klist
```

### Full Samba AD Deployment

```yaml
version: "3.8"
services:
  samba-ad:
    image: linuxserver/samba:latest
    container_name: samba-ad-dc
    hostname: dc1
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "88:88/tcp"
      - "88:88/udp"
      - "135:135/tcp"
      - "139:139/tcp"
      - "389:389/tcp"
      - "389:389/udp"
      - "445:445/tcp"
      - "464:464/tcp"
      - "464:464/udp"
      - "636:636/tcp"
      - "1024-1045:1024-1045/tcp"
      - "3268-3269:3268-3269/tcp"
    volumes:
      - ./samba-conf:/config
      - samba-data:/var/lib/samba
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Etc/UTC
      - SAMBA_DC_ADMIN_PASSWD='Str0ngAdm!nPass'
      - SAMBA_DC_DNS_BACKEND=SAMBA_INTERNAL
      - SAMBA_DC_REALM=EXAMPLE.COM
      - SAMBA_DC_DOMAIN=example
    restart: unless-stopped
    networks:
      kdc-net:
        ipv4_address: 10.10.0.30
    cap_add:
      - NET_ADMIN

volumes:
  samba-data:

networks:
  kdc-net:
    driver: bridge
    ipam:
      config:
        - subnet: 10.10.0.0/24
```

### Domain Provisioning

After the container starts, provision the domain controller:

```bash
# Enter the container
docker exec -it samba-ad-dc bash

# Provision the AD domain
samba-tool domain provision \
  --realm=EXAMPLE.COM \
  --domain=EXAMPLE \
  --adminpass='Str0ngAdm!nPass' \
  --server-role=dc \
  --dns-backend=SAMBA_INTERNAL \
  --use-rfc2307
```

## Comparison Table

| Feature | MIT Kerberos (krb5) | Heimdal | Samba AD |
|---------|---------------------|---------|----------|
| **Primary focus** | KDC only | KDC only | Full AD domain controller |
| **Database** | Berkeley DB / LMDB | HDB (SQLite, LDAP, LDB) | Samba LDB |
| **LDAP integration** | External (via plugins) | Native LDAP backend | Built-in |
| **DNS integration** | Manual | Manual | Built-in dynamic DNS |
| **Cross-realm trust** | Yes | Yes (hierarchical) | Yes (AD trusts) |
| **PKINIT / smart card** | Yes | First-class support | Yes |
| **OTP support** | No (external) | Built-in | No |
| **Active Directory interoperability** | Limited | Partial | Native |
| **Docker image maturity** | Community images | LinuxServer.io | LinuxServer.io |
| **Admin interface** | kadmin (CLI) | kadmin (CLI) | samba-tool (CLI + RSAT) |
| **Replication** | kprop (manual setup) | HDB replication | Multi-master AD replication |
| **Group Policy** | No | No | Full GPO support |
| **File sharing** | No | No | Full SMB/CIFS |
| **Windows client support** | Yes (with config) | Yes (with config) | Native |
| **Complexity** | Low | Low | High |
| **Best for** | Pure Kerberos, Linux/Unix environments | Smart card / PKI-heavy environments | AD replacement, mixed Windows/Linux |

## Choosing the Right KDC

### When to Use MIT Kerberos

MIT krb5 is the right choice when you need a pure, standards-compliant Kerberos KDC without additional services. It is the default on most Linux distributions, making integration straightforward. Use it for:

- Linux/Unix-only environments with centralized authentication
- Hadoop, PostgreSQL, or other services that natively support GSSAPI/Kerberos
- Minimal infrastructure footprint
- Environments where you already run an LDAP directory (OpenLDAP, FreeIPA) and only need the KDC component

### When to Use Heimdal

Heimdal excels in environments with strong PKI requirements. Its native PKINIT support, smart card integration, and OTP capabilities make it ideal for:

- Government or regulated environments requiring certificate-based authentication
- Organizations with existing smart card infrastructure
- FreeBSD or macOS deployments (where Heimdal is the default)
- Scenarios where you want Kerberos with LDAP backend integration without running a full AD domain

### When to Use Samba AD

Samba AD is the most comprehensive option but also the most complex. Choose it when you need:

- Active Directory replacement for Windows domain environments
- Mixed Windows and Linux client authentication with a single directory
- Group Policy management across Windows clients
- File and print services alongside authentication
- Kerberos + LDAP + DNS in a single deployable unit

## Security Hardening

Regardless of which implementation you choose, follow these hardening steps:

**Restrict encryption types** — Only allow AES-256 and AES-128. Disable DES, RC4, and weak encryption:

```ini
# krb5.conf / kdc.conf
supported_enctypes = aes256-cts:normal aes128-cts:normal
```

**Enforce pre-authentication** — Prevent offline password guessing by requiring pre-authentication on all principals:

```bash
# MIT Kerberos: set default flags in kdc.conf
default_principal_flags = +preauth

# Verify for existing principals
kadmin.local -q "getprinc admin@EXAMPLE.COM" | grep "Requires pre-auth"
```

**Set appropriate ticket lifetimes** — Shorter TGT lifetimes reduce the window for ticket replay attacks:

```ini
max_life = 8h 0m 0s
max_renewable_life = 5d 0h 0m 0s
```

**Restrict KDC network access** — Only allow your internal network to reach ports 88 and 464:

```yaml
# In Docker Compose, use internal networks without host port mapping
ports: []  # Remove host port bindings
networks:
  kdc-net:
    ipv4_address: 10.10.0.10
```

**Audit authentication events** — Monitor the KDC logs for failed authentication attempts and unusual ticket requests:

```bash
# MIT Kerberos: check kdc logs
tail -f /var/log/krb5kdc.log | grep -E "FAILED|PREAUTH"

# Samba AD: check audit logs
tail -f /var/log/samba/log.smbd | grep -i "authentication"
```

## FAQ

### What is a Kerberos KDC and why do I need one?

A Kerberos Key Distribution Center (KDC) is the central authentication server in a Kerberos realm. It issues tickets that allow users and services to authenticate to each other without transmitting passwords. You need a self-hosted KDC when you want to control the entire authentication chain, meet data sovereignty requirements, or run services in air-gapped or offline environments where cloud identity providers are not available.

### Can MIT Kerberos and Heimdal coexist in the same realm?

Technically yes — both implementations use the same Kerberos V5 protocol and can share a realm. However, the database formats are incompatible (MIT uses Berkeley DB/LMDB while Heimdal uses HDB), so you cannot directly share the principal database. You would need to set up cross-realm trusts between separate KDCs, or migrate principals using `kdb5_util` dump and `kadmin` load utilities.

### Does Samba AD replace a standalone Kerberos KDC?

Samba AD includes a fully functional Kerberos KDC as part of its Active Directory implementation. If you deploy Samba AD, you do not need a separate MIT Kerberos or Heimdal KDC. Samba's KDC handles all standard Kerberos operations and additionally provides AD-specific extensions like PAC (Privilege Attribute Certificate) support that Windows clients expect.

### How do I migrate from MIT Kerberos to Samba AD?

The migration involves exporting your MIT Kerberos principal database, converting it to Samba's LDB format, and provisioning a Samba AD domain. Use `kdb5_util dump` to export MIT principals, then `samba-tool domain provision` to create the AD domain. Individual principals need to be recreated with `samba-tool user create` or imported via LDIF. Password hashes cannot be directly migrated — users will need to reset passwords after the switchover.

### Is Kerberos still relevant in 2026?

Yes. Kerberos remains the default authentication protocol for Windows Active Directory, Hadoop ecosystems, PostgreSQL (via GSSAPI), NFSv4, and many enterprise applications. While OAuth 2.0 and OIDC have become dominant for web application authentication, Kerberos continues to be the standard for internal network authentication where mutual authentication and ticket-based SSO are required.

### What ports does a Kerberos KDC need?

A Kerberos KDC requires UDP and TCP port 88 for the main KDC service, and TCP port 464 for the password change service (kpasswd). The administrative server (kadmind) typically uses TCP port 749. These ports must be accessible to all clients that need to authenticate against the realm. For Samba AD, additional ports are needed for LDAP (389), DNS (53), SMB (445), and LDAPS (636).

### Can I run a Kerberos KDC in a Docker container in production?

Yes, but with caveats. The KDC database must be stored on a persistent volume, and the container hostname must be stable (matching the KDC principal name). UDP port mapping in Docker can be unreliable — consider using `network_mode: host` or a macvlan network for production deployments. Always test ticket issuance and renewal after container restarts, as KDC state is maintained in the database files.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "MIT Kerberos vs Heimdal vs Samba AD: Self-Hosted KDC Guide 2026",
  "description": "Complete guide to self-hosted Kerberos Key Distribution Centers. Compare MIT Kerberos, Heimdal, and Samba AD for enterprise authentication, SSO, and network security.",
  "datePublished": "2026-04-25",
  "dateModified": "2026-04-25",
  "author": {
    "@type": "Organization",
    "name": "Pi Stack"
  },
  "publisher": {
    "@type": "Organization",
    "name": "Pi Stack",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>
