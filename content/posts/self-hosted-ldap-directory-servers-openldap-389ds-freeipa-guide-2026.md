---
title: "OpenLDAP vs 389 Directory Server vs FreeIPA: Self-Hosted LDAP Directory Guide 2026"
date: 2026-04-17
tags: ["comparison", "guide", "self-hosted", "identity", "ldap", "directory"]
draft: false
description: "Complete guide to self-hosted LDAP directory servers in 2026. Compare OpenLDAP, 389 Directory Server, and FreeIPA with Docker setups, configuration examples, and a decision framework for choosing the right identity backend."
---

Every growing infrastructure eventually hits the same wall: user accounts scattered across servers, services, and applications with no single source of truth. Passwords managed manually. SSH keys copied by hand. Service accounts created and forgotten. The solution has existed for decades — an LDAP directory server — but choosing and configuring one remains daunting.

This guide covers the three most capable open-source LDAP directory servers you can self-host: **OpenLDAP**, **389 Directory Server**, and **FreeIPA**. Each serves a different audience and operational philosophy. By the end, you will know which one fits your environment and how to deploy it.

## Why Self-Host Your Directory Server

Directory services are the backbone of identity management. They store user accounts, group memberships, SSH public keys, service credentials, and access policies. When every application, server, and container queries the same directory for authentication and authorization, you eliminate credential sprawl and gain centralized control.

Running your own directory server gives you several advantages over managed or cloud-based alternatives:

- **Full data sovereignty**: User identities and access patterns never leave your infrastructure.
- **No per-user pricing**: Open-source directory servers scale without licensing fees tied to user count.
- **Custom schemas**: Extend the directory to store application-specific attributes that commercial providers may not support.
- **Network isolation**: The directory operates entirely on your internal network with no external dependencies.
- **Integration flexibility**: Connect with PAM, NSS, SSH, email servers, VPNs, databases, and any application supporting LDAP bind authentication.

The trade-off is operational responsibility: you manage backups, replication, schema changes, and high availability. The three servers below handle these requirements differently.

## OpenLDAP: The Universal Standard

OpenLDAP is the oldest and most widely deployed open-source LDAP implementation. It implements the full LDAPv3 protocol, supports TLS, SASL authentication, and runs on virtually any Unix-like system. Its configuration can be managed through the traditional `slapd.conf` file or the modern dynamic configuration backend (`cn=config`).

### Strengths

- **Maturity and stability**: Over 25 years of development with a proven track record in enterprise environments.
- **Standards compliance**: Full LDAPv3 implementation with extensive RFC support.
- **Flexibility**: Custom object classes, attributes, and overlays for virtually any identity model.
- **Replication**: Syncrepl (delta-sync) and N-Way Multi-Master replication for high availability.
- **Wide client support**: Every LDAP client library and tool supports OpenLDAP natively.

### Weaknesses

- **Steep learning curve**: Configuration through LDIF files and `ldapmodify` commands is not intuitive.
- **No built-in web UI**: All administration happens through command-line tools or third-party interfaces.
- **Manual schema management**: Adding custom schemas requires careful LDIF work and server reloads.
- **No integrated DNS or Kerberos**: You must provision these separately for full identity infrastructure.

### Docker Deployment

```yaml
# docker-compose.yml — OpenLDAP with phpLDAPadmin
version: "3.8"

services:
  openldap:
    image: osixia/openldap:1.5.0
    container_name: openldap
    hostname: ldap.example.org
    environment:
      LDAP_ORGANISATION: "Example Organization"
      LDAP_DOMAIN: "example.org"
      LDAP_ADMIN_PASSWORD: "StrongAdminP@ss"
      LDAP_TLS: "true"
      LDAP_TLS_CRT_FILENAME: "ldap.crt"
      LDAP_TLS_KEY_FILENAME: "ldap.key"
      LDAP_TLS_CA_CRT_FILENAME: "ca.crt"
    ports:
      - "389:389"
      - "636:636"
    volumes:
      - ldap-data:/var/lib/ldap
      - ldap-config:/etc/ldap/slapd.d
      - ./certs:/container/service/slapd/assets/certs:ro
    restart: unless-stopped

  phpldapadmin:
    image: osixia/phpldapadmin:0.9.0
    container_name: phpldapadmin
    environment:
      PHPLDAPADMIN_LDAP_HOSTS: "ldap.example.org"
      PHPLDAPADMIN_HTTPS: "false"
    ports:
      - "8080:80"
    depends_on:
      - openldap
    restart: unless-stopped

volumes:
  ldap-data:
  ldap-config:
```

After starting the containers with `docker compose up -d`, verify connectivity:

```bash
ldapsearch -x -H ldap://localhost \
  -D "cn=admin,dc=example,dc=org" \
  -w "StrongAdminP@ss" \
  -b "dc=example,dc=org" \
  "(objectClass=*)" dn
```

### Adding Users via LDIF

Create a file `add-users.ldif`:

```ldif
dn: ou=people,dc=example,dc=org
objectClass: organizationalUnit
ou: people

dn: ou=groups,dc=example,dc=org
objectClass: organizationalUnit
ou: groups

dn: uid=jsmith,ou=people,dc=example,dc=org
objectClass: inetOrgPerson
objectClass: posixAccount
objectClass: shadowAccount
cn: John Smith
sn: Smith
uid: jsmith
uidNumber: 10000
gidNumber: 10000
homeDirectory: /home/jsmith
loginShell: /bin/bash
userPassword: {SSHA}encrypted-hash-here
```

Apply it:

```bash
ldapmodify -x -H ldap://localhost \
  -D "cn=admin,dc=example,dc=org" \
  -w "StrongAdminP@ss" \
  -a -f add-users.ldif
```

### Syncrepl Replication Setup

For high availability, configure delta-sync replication on the consumer server:

```ldif
dn: olcDatabase={1}mdb,cn=config
changetype: modify
add: olcSyncRepl
olcSyncRepl: rid=001
  provider=ldap://provider.example.org:389
  bindmethod=simple
  binddn="cn=admin,dc=example,dc=org"
  credentials="StrongAdminP@ss"
  searchbase="dc=example,dc=org"
  type=refreshAndPersist
  retry="60 +"
  timeout=1
```

---

## 389 Directory Server: The Modern Alternative

389 Directory Server (389 DS), developed by the Fedora project and formerly known as Fedora Directory Server, is a full-featured LDAP server designed for easier administration than OpenLDAP. It ships with a dedicated command-line toolset (`dsconf`, `dscreate`), a web-based console, and sensible defaults out of the box.

### Strengths

- **Easier administration**: `dsconf` and `dscreate` CLI tools replace complex LDIF manipulation for most operations.
- **Web console**: Built-in Cockpit-based management interface for monitoring and configuration.
- **Active Directory compatibility**: Synchronized password handling and schema extensions for mixed environments.
- **Better defaults**: Automatic indexing, sensible access controls, and performance tuning enabled by default.
- **Active development**: Backed by Red Hat and the Fedora community with regular releases.

### Weaknesses

- **Smaller ecosystem**: Fewer third-party tools and tutorials compared to OpenLDAP.
- **Tied to specific OS**: Best supported on Fedora, RHEL, and CentOS; other distributions may lag.
- **Less flexible schema**: Custom extensions require more effort than OpenLDAP's overlay system.
- **Fewer deployment images**: Official Docker support exists but with less community variation.

### Docker Deployment

```yaml
# docker-compose.yml — 389 Directory Server
version: "3.8"

services:
  ds389:
    image: 389ds/dirsrv:latest
    container_name: ds389
    hostname: ds389.example.org
    environment:
      DS_DM_PASSWORD: "DirectoryManagerP@ss"
      DS_ROOT_PASSWORD: "RootP@ss123"
    ports:
      - "3389:3389"
      - "3636:636"
      - "9090:9090"
    volumes:
      - ds389-data:/data
      - ds389-config:/etc/dirsrv
    restart: unless-stopped

volumes:
  ds389-data:
  ds389-config:
```

Initialize the server inside the container:

```bash
docker exec -it ds389 dscreate interactive
```

Or use an INF file for automated setup:

```ini
# setup.inf
[general]
config_version = 2

[slapd]
root_password = RootP@ss123
instance_name = example

[backend-userroot]
sample_entries = yes
suffix = dc=example,dc=org
```

```bash
docker exec -it ds389 dscreate from-file /data/setup.inf
```

### Managing Users with dsconf

Create a user and set their password:

```bash
docker exec -it ds389 dsconf example user create \
  --uid jsmith \
  --cn "John Smith" \
  --displayName "John Smith" \
  --uidNumber 10000 \
  --gidNumber 10000 \
  --homeDirectory /home/jsmith \
  --loginShell /bin/bash

docker exec -it ds389 dsidm example user reset_password \
  "uid=jsmith,ou=people,dc=example,dc=org"
```

Search for users:

```bash
docker exec -it ds389 dsidm example user list
```

### Enabling Replication

389 DS supports multi-master replication. Enable it via `dsconf`:

```bash
# On the supplier (primary) server
docker exec -it ds389 dsconf example replication enable \
  --suffix="dc=example,dc=org" \
  --role=supplier \
  --replica-id=1

docker exec -it ds389 dsconf example repl-agmt create \
  --suffix="dc=example,dc=org" \
  --host="consumer.example.org" \
  --port=3389 \
  --conn-protocol=LDAP \
  --bind-dn="cn=replication manager,cn=config" \
  --bind-passwd="ReplP@ss" \
  --bind-method=SIMPLE \
  agreement01
```

---

## FreeIPA: The Complete Identity Platform

FreeIPA combines 389 Directory Server with MIT Kerberos, DNS (BIND), NTP, and a certificate authority (Dogtag PKI) into a single integrated identity management platform. It provides a rich web UI, host-based access control (HBAC), sudo rules, SSH key management, and group policy — essentially a self-hosted alternative to Active Directory for Linux environments.

### Strengths

- **Complete solution**: LDAP + Kerberos + DNS + CA + NTP in one package — no separate components needed.
- **Web UI**: Full-featured administrative interface for managing users, hosts, policies, and certificates.
- **Host enrollment**: `ipa-client-install` enrolls machines with automatic SSH key distribution and SSO.
- **HBAC and sudo rules**: Centralized access control policies per user, group, host, or service.
- **Cross-forest trust**: Active Directory integration through Kerberos trust relationships.
- **Automated certificate management**: Integrated Dogtag CA issues and renews service certificates.

### Weaknesses

- **Heavy resource requirements**: Needs 2+ GB RAM and 20+ GB disk even for small deployments due to multiple integrated services.
- **Complex architecture**: More moving parts means more things that can go wrong during upgrades or recovery.
- **Opinionated design**: The integration between components limits flexibility — you use the full stack or none of it.
- **DNS requirement**: Requires a properly configured DNS domain; cannot easily operate without its own DNS server.
- **Limited containerization**: FreeIPA is designed for bare-metal or VM deployment; Docker setups are experimental and not recommended for production.

### VM Deployment (Recommended)

FreeIPA is not suited for containerized deployment. The recommended approach uses a dedicated VM:

```bash
# On a RHEL/Fedora/AlmaLinux VM (minimum 2 CPU, 2 GB RAM)
sudo dnf install -y ipa-server ipa-server-dns

# Configure hostname and DNS resolution
sudo hostnamectl set-hostname ipa.example.org
echo "192.168.1.10 ipa.example.org ipa" | sudo tee -a /etc/hosts

# Run the interactive installer
sudo ipa-server-install
```

The installer prompts for:
- Domain name (e.g., `example.org`)
- Realm name (e.g., `EXAMPLE.ORG`)
- Directory Manager password
- IPA admin password
- DNS forwarder configuration
- NTP server configuration

### Managing FreeIPA After Installation

Once installed, access the web UI at `https://ipa.example.org/ipa/ui`.

Add a user via CLI:

```bash
# Authenticate as admin
kinit admin

# Create a user
ipa user-add jsmith --first=John --last=Smith --password

# Add SSH public key
ipa user-mod jsmith --sshpubkey="ssh-ed25519 AAAA... user@host"

# Add to a group
ipa group-add-member admins --users=jsmith
```

Enroll a client machine:

```bash
# On the client machine
sudo dnf install -y ipa-client

sudo ipa-client-install \
  --domain=example.org \
  --server=ipa.example.org \
  --realm=EXAMPLE.ORG \
  --mkhomedir \
  --enable-dns-updates
```

After enrollment, users can SSH to the client using their FreeIPA credentials, and their SSH keys are automatically distributed.

### HBAC Rule Example

Create a host-based access control rule that restricts database servers to the DBA team:

```bash
# Create an HBAC rule
ipa hbacrule-add --desc="DBA access to database servers" dba-db-access

# Add the DBA group
ipa hbacrule-add-user dba-db-access --groups=dba-team

# Add database servers to the host group
ipa hbacrule-add-host dba-db-access --hostgroups=db-servers

# Allow SSH and su services
ipa hbacrule-add-service dba-db-access --hbacsvc=sshd
ipa hbacrule-add-service dba-db-access --hbacsvc=su
```

---

## Feature Comparison

| Feature | OpenLDAP | 389 Directory Server | FreeIPA |
|---|---|---|---|
| **Protocol** | LDAPv3 | LDAPv3 | LDAPv3 + Kerberos |
| **Web UI** | No (use phpLDAPadmin) | Yes (Cockpit console) | Yes (integrated) |
| **CLI Tools** | `ldapsearch`, `ldapmodify` | `dsconf`, `dscreate`, `dsidm` | `ipa` command suite |
| **Kerberos** | No | No | Yes (MIT Kerberos) |
| **Integrated DNS** | No | No | Yes (BIND) |
| **Certificate Authority** | No | No | Yes (Dogtag PKI) |
| **SSH Key Management** | Manual schema extension | Manual schema extension | Built-in |
| **HBAC / Sudo Rules** | No | No | Yes |
| **Host Enrollment** | Manual configuration | Manual configuration | `ipa-client-install` |
| **Replication** | Syncrepl, Multi-Master | Multi-Master | Multi-Master (via 389 DS) |
| **AD Integration** | Limited | Password sync | Full trust support |
| **Docker Support** | Excellent | Good | Experimental only |
| **Resource Usage** | Low (~256 MB RAM) | Moderate (~512 MB RAM) | High (~2 GB RAM) |
| **Learning Curve** | Steep | Moderate | Moderate (but broader scope) |
| **Best For** | Custom LDAP deployments | Standalone directory services | Full identity platform |

## Choosing the Right Server

### Choose OpenLDAP When

- You need a lightweight, pure LDAP directory with minimal resource usage.
- Your team has LDAP experience and values maximum flexibility in schema design.
- You are deploying in containers or resource-constrained environments.
- You already have separate systems for Kerberos, DNS, and certificate management.
- You need compatibility with legacy LDAP clients that expect specific OpenLDAP behaviors.

### Choose 389 Directory Server When

- You want a modern directory server with sensible defaults and easier administration.
- You prefer CLI tools (`dsconf`) over raw LDIF manipulation.
- You need Active Directory password synchronization but not the full FreeIPA stack.
- You run Fedora, RHEL, or AlmaLinux and want first-class support.
- You want a built-in web console without third-party additions.

### Choose FreeIPA When

- You need a complete identity management platform, not just an LDAP server.
- You manage dozens or hundreds of Linux servers and want centralized authentication.
- You want SSH key distribution, HBAC policies, and sudo rules out of the box.
- You need integration with Active Directory through cross-forest trusts.
- You value a unified web interface for managing users, hosts, services, and certificates.
- You have the VM resources to run the full stack (2+ GB RAM, 20+ GB disk).

## Backup and Recovery

Regardless of which server you choose, backups are non-negotiable for identity infrastructure.

### OpenLDAP Backup

```bash
# Online backup with slapcat
sudo slapcat -n 0 -l /backup/ldap-config.ldif   # cn=config
sudo slapcat -n 1 -l /backup/ldap-data.ldif     # database

# Restore
sudo slapadd -n 0 -l /backup/ldap-config.ldif
sudo slapadd -n 1 -l /backup/ldap-data.ldif
```

### 389 Directory Server Backup

```bash
# Create a backup
docker exec -it ds389 dsctl example db2ldif --replication userroot

# Export LDIF
docker exec -it ds389 dsctl example ldif2db \
  --backend=userroot \
  --ldif=/data/backup-$(date +%Y%m%d).ldif
```

### FreeIPA Backup

```bash
# Full server backup (must be run on the IPA server)
sudo ipa-backup

# Online backup without stopping services
sudo ipa-backup --online --data

# Restore
sudo ipa-restore /var/lib/ipa/backup/ipa-full-YYYY-MM-DD-HH-MM-SS
```

## Getting Started Checklist

Once you have deployed your directory server, follow these steps to bring it into production:

1. **Configure TLS**: Generate or provision certificates and enforce LDAPS (port 636) or StartTLS.
2. **Set up replication**: Deploy at least two servers for high availability before adding clients.
3. **Define your schema**: Plan your organizational units, groups, and custom attributes before bulk importing users.
4. **Configure access controls**: Set up ACLs to restrict who can read, modify, or bind to directory entries.
5. **Automate backups**: Schedule regular exports and test restore procedures on a non-production server.
6. **Monitor health**: Track replication lag, disk usage, bind response times, and TLS certificate expiry.
7. **Enroll clients gradually**: Start with non-critical systems and validate authentication before rolling out broadly.
8. **Document procedures**: Record schema change processes, recovery steps, and replication troubleshooting for your team.

---

Self-hosting an LDAP directory server puts you in full control of your identity infrastructure. OpenLDAP gives you the most flexibility with the steepest learning curve. 389 Directory Server modernizes the experience with better tooling and defaults. FreeIPA delivers a complete identity platform that rivals Active Directory for Linux environments.

The right choice depends on your scale, existing infrastructure, and whether you need just a directory or a full identity management ecosystem. All three are production-ready, actively maintained, and free — there is no reason to pay per-user licensing fees for core identity services in 2026.
