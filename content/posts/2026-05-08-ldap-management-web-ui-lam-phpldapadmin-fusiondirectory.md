---
title: "Self-Hosted LDAP Management Web UIs: LAM vs phpLDAPadmin vs FusionDirectory (2026)"
date: "2026-05-08"
draft: false
tags: ["ldap", "directory-services", "identity-management", "web-ui", "self-hosted", "openldap", "freeipa"]
---

LDAP (Lightweight Directory Access Protocol) servers are the backbone of enterprise identity management, but managing them from the command line is tedious and error-prone. Web-based LDAP management interfaces give system administrators a visual way to create users, manage groups, configure schemas, and administer directory services — all from a browser.

This guide compares three mature, open-source LDAP management web UIs: **LDAP Account Manager (LAM)**, **phpLDAPadmin**, and **FusionDirectory**. Each tool offers a different approach to directory management, and choosing the right one depends on your directory infrastructure, team size, and management requirements.

## Quick Comparison

| Feature | LDAP Account Manager (LAM) | phpLDAPadmin | FusionDirectory |
|---------|---------------------------|--------------|-----------------|
| **GitHub Stars** | 481+ | 200+ | 150+ |
| **License** | GPL-2.0 | GPL-2.0+ | GPL-2.0+ |
| **Language** | PHP | PHP | PHP |
| **Docker Support** | Official image | Community images | Official image |
| **Multi-Server** | Yes (profiles) | Yes (config) | Yes (plugins) |
| **Template System** | Account templates | No | Plugin-based templates |
| **Audit Logging** | Yes | No | Yes (plugin) |
| **Self-Service Portal** | Yes (LAM Pro) | No | No |
| **Last Updated** | 2026-05-08 | 2025 | 2025 |
| **Best For** | General LDAP admin | Quick browsing | Plugin-driven workflows |

## LDAP Account Manager (LAM)

LDAP Account Manager is the most actively maintained of the three tools, with regular updates and a modern web interface. It supports OpenLDAP, Active Directory, and 389 Directory Server backends, and offers a comprehensive set of features for user, group, and organizational unit management.

LAM uses a profile-based configuration system that lets you manage multiple LDAP directories from a single installation. Each profile can define custom attribute mappings, object classes, and access controls, making it suitable for environments with heterogeneous directory servers.

### Key Features

- **Profile-based multi-server management** — manage OpenLDAP, AD, and 389 DS from one interface
- **Account templates** — predefine user and group attributes for fast creation
- **PDF export** — generate reports of directory contents
- **Self-service portal** — allow users to update their own contact information
- **TOTP two-factor authentication** — secure admin access with time-based OTP
- **Schema-aware editing** — validates attributes against LDAP schema definitions

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  lam:
    image: ldapaccountmanager/lam:latest
    container_name: lam
    restart: unless-stopped
    ports:
      - "8080:80"
    volumes:
      - ./lam-config:/etc/ldap-account-manager
    environment:
      - LAM_LANG=en_US
      - LAM_TIMEZONE=UTC
```

LAM stores its configuration in `/etc/ldap-account-manager` inside the container. Mounting this directory as a volume persists your server profiles, user preferences, and template definitions across container restarts.

### Installation Without Docker

```bash
# Debian/Ubuntu
sudo apt install ldap-account-manager

# Fedora/RHEL
sudo dnf install ldap-account-manager

# Apache configuration is auto-configured
# Access at http://localhost/lam
```

LAM packages are available in most Linux distributions' repositories. The web interface is automatically configured as an Apache virtual host.

## phpLDAPadmin

phpLDAPadmin is one of the oldest LDAP web management tools, dating back to the early 2000s. It provides a tree-view browser interface for browsing and editing any LDAP directory. While its interface feels dated compared to modern alternatives, its simplicity and universal LDAP compatibility make it a reliable choice for basic directory administration.

### Key Features

- **Tree-view browser** — navigate directory hierarchies visually
- **Universal LDAP support** — works with any LDAPv3 compliant server
- **Template queries** — save and reuse common search patterns
- **Schema browser** — view object classes and attribute definitions
- **Copy/move/rename entries** — manipulate directory entries directly
- **Import/export LDIF** — bulk import and export directory data

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  phpldapadmin:
    image: osixia/phpldapadmin:latest
    container_name: phpldapadmin
    restart: unless-stopped
    ports:
      - "8081:80"
      - "8443:443"
    environment:
      - PHPLDAPADMIN_LDAP_HOSTS=ldap-server
      - PHPLDAPADMIN_HTTPS_DISABLED=true
    networks:
      - ldap-net
    depends_on:
      - ldap-server

  ldap-server:
    image: osixia/openldap:latest
    container_name: openldap
    restart: unless-stopped
    environment:
      - LDAP_ORGANISATION=Example Org
      - LDAP_DOMAIN=example.org
      - LDAP_ADMIN_PASSWORD=admin123
    ports:
      - "389:389"
    networks:
      - ldap-net

networks:
  ldap-net:
    driver: bridge
```

The osixia/phpldapadmin image pairs well with the osixia/openldap image for a complete self-hosted LDAP environment. The `PHPLDAPADMIN_LDAP_HOSTS` environment variable configures the LDAP server connection.

## FusionDirectory

FusionDirectory is a modular LDAP directory management platform that uses a plugin-based architecture. Unlike LAM and phpLDAPadmin, which are primarily browsing and editing tools, FusionDirectory provides integrated management for specific services: mail, DNS, SSH, systems, and more — all tied together through LDAP.

### Key Features

- **Plugin architecture** — extend functionality with service-specific plugins
- **Mail management** — manage mail accounts, aliases, and vacation responders
- **DNS management** — manage DNS records stored in LDAP (BIND DLZ)
- **SSH key management** — store and distribute SSH public keys via LDAP
- **Systems management** — track hardware inventory and system configurations
- **Audit plugin** — log all directory changes for compliance
- **Webservice API** — programmatic access to directory operations

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  fusiondirectory:
    image: fusiondirectory/fusiondirectory:latest
    container_name: fusiondirectory
    restart: unless-stopped
    ports:
      - "8082:80"
    environment:
      - LDAP_URI=ldap://ldap-server:389
      - LDAP_BASE_DN=dc=example,dc=org
      - LDAP_ADMIN_DN=cn=admin,dc=example,dc=org
      - LDAP_ADMIN_PASS=admin123
    depends_on:
      - ldap-server
    networks:
      - ldap-net

  ldap-server:
    image: osixia/openldap:latest
    container_name: openldap
    restart: unless-stopped
    environment:
      - LDAP_ORGANISATION=Example Org
      - LDAP_DOMAIN=example.org
      - LDAP_ADMIN_PASSWORD=admin123
    ports:
      - "389:389"
    networks:
      - ldap-net

networks:
  ldap-net:
    driver: bridge
```

FusionDirectory requires an LDAP server and optionally a MySQL/MariaDB backend for storing plugin data. The Docker Compose setup above provides a minimal working configuration.

## Choosing the Right LDAP Management UI

**Choose LDAP Account Manager (LAM) if:**
- You need a modern, actively maintained interface
- You manage multiple directory servers (OpenLDAP + AD + 389 DS)
- Account templates and self-service features are important
- You want the most recent security updates

**Choose phpLDAPadmin if:**
- You need a lightweight, universal LDAP browser
- You prefer a simple tree-view interface
- You work with non-standard or custom LDAP schemas
- You need a tool that works with any LDAPv3 server out of the box

**Choose FusionDirectory if:**
- You want integrated service management (mail, DNS, SSH, systems)
- You need a plugin-based extensible platform
- You want audit logging for compliance requirements
- You manage a complex environment where LDAP is the central directory for multiple services

## Why Self-Host Your LDAP Management UI?

Running your own LDAP management interface keeps administrative access within your infrastructure boundary. When you use cloud-hosted directory management tools, you grant a third party visibility into your organizational structure, user attributes, and group memberships. Self-hosted LDAP UIs eliminate this risk entirely.

For organizations managing user authentication across multiple services, having a centralized web interface for directory administration reduces operational overhead. Instead of using command-line tools for every user creation, group modification, or schema update, administrators can perform these tasks through a consistent web interface with validation and auditing.

Self-hosting also means you control the network topology. LDAP management interfaces can be placed behind internal firewalls, accessible only from your management VLAN or through a VPN. This network-level isolation is impossible with cloud-hosted alternatives.

For related reading on directory server backends, see our [OpenLDAP vs 389 DS vs FreeIPA comparison](../self-hosted-ldap-directory-servers-openldap-389ds-freeipa-guide-2026/). If you need lightweight alternatives for smaller deployments, check our [LLDAP vs GLAuth guide](../2026-04-24-lldap-vs-glauth-lightweight-ldap-self-hosted-auth-guide/). For identity synchronization across systems, our [Apache Syncope vs midPoint guide](../2026-05-04-apache-syncope-vs-midpoint-vs-ltb-ldap-toolbox-self-hosted-identity-sync-guide/) covers advanced identity management.


For more details, see our [OpenLDAP vs 389 DS vs FreeIPA guide](../self-hosted-ldap-directory-servers-openldap-389ds-freeipa-guide-2026/)
For more details, see our [LLDAP vs GLAuth lightweight auth](../2026-04-24-lldap-vs-glauth-lightweight-ldap-self-hosted-auth-guide/)
For more details, see our [Apache Syncope identity sync](../2026-05-04-apache-syncope-vs-midpoint-vs-ltb-ldap-toolbox-self-hosted-identity-sync-guide/)

## FAQ

### What is the difference between LAM and phpLDAPadmin?

LDAP Account Manager (LAM) provides a form-based interface with account templates, profile-based multi-server management, and a self-service portal. phpLDAPadmin uses a tree-view browser approach that directly exposes the LDAP directory structure. LAM is more user-friendly for non-technical administrators, while phpLDAPadmin gives experienced admins direct access to the raw directory hierarchy.

### Can FusionDirectory manage non-LDAP services?

FusionDirectory uses LDAP as its central data store but provides plugins for managing mail servers (Postfix/Dovecot), DNS servers (BIND), SSH servers, and system inventory. The plugins store service-specific configuration in LDAP and provide web forms for managing each service. This makes FusionDirectory a unified management platform rather than just an LDAP browser.

### Do these tools support Active Directory?

LDAP Account Manager (LAM) has explicit Active Directory support and can manage AD domains alongside OpenLDAP and 389 DS. phpLDAPadmin works with AD through the LDAPv3 protocol but doesn't have AD-specific features. FusionDirectory is designed primarily for OpenLDAP and may require schema extensions for full AD compatibility.

### How do I secure the LDAP management web interface?

All three tools should be placed behind HTTPS using a reverse proxy (Nginx, Traefik, or Caddy). Enable TLS encryption for the LDAP connection between the management UI and the directory server. For LAM, enable TOTP two-factor authentication. For production deployments, restrict access to the management interface using IP-based allowlists or VPN requirements.

### Can I manage multiple LDAP servers from one installation?

LAM supports multiple server profiles, each with its own connection settings, authentication method, and attribute mappings. phpLDAPadmin supports multiple servers through its configuration file. FusionDirectory connects to a single LDAP server but can manage multiple services through that server.

### Is there an API for programmatic access?

FusionDirectory provides a webservice API for programmatic directory operations. LAM and phpLDAPadmin do not offer REST APIs — they are designed for interactive web-based administration. For API-driven management, consider tools like Apache Syncope or midPoint, which are covered in our [identity sync comparison](../2026-05-04-apache-syncope-vs-midpoint-vs-ltb-ldap-toolbox-self-hosted-identity-sync-guide/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted LDAP Management Web UIs: LAM vs phpLDAPadmin vs FusionDirectory (2026)",
  "description": "Compare three open-source LDAP management web interfaces — LDAP Account Manager, phpLDAPadmin, and FusionDirectory — with Docker deployment guides.",
  "datePublished": "2026-05-08",
  "dateModified": "2026-05-08",
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
