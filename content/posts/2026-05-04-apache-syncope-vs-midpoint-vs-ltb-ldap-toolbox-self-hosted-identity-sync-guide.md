---
title: "Apache Syncope vs midPoint vs LTB ldap-toolbox: Self-Hosted Identity Synchronization Guide 2026"
date: 2026-05-04
tags: ["comparison", "guide", "self-hosted", "identity-management", "ldap", "directory-services"]
draft: false
description: "Compare three open-source identity synchronization platforms — Apache Syncope, Evolveum midPoint, and LTB ldap-toolbox — for self-hosted directory synchronization, identity governance, and user provisioning."
---

## Why Self-Host Identity Synchronization?

Organizations rarely run a single directory. Most environments have multiple identity stores — an LDAP directory for Linux authentication, Active Directory for Windows, a database for application users, and cloud services with their own user directories. Keeping these synchronized manually is error-prone, slow, and creates security gaps when users change roles or leave the organization.

Commercial identity governance platforms like SailPoint, Saviynt, and Microsoft Identity Manager charge per-identity licensing fees that can exceed $50 per user per year. For organizations with thousands of identities, these costs become prohibitive. Self-hosted open-source identity synchronization platforms provide the same capabilities — automated provisioning, role-based access, approval workflows, and audit trails — without per-user licensing.

This guide compares three open-source identity management platforms: **Apache Syncope** (the Apache Software Foundation's provisioning engine), **Evolveum midPoint** (identity governance and administration), and **LTB ldap-toolbox** (lightweight LDAP self-service tools). Each targets a different complexity level and use case.

## Project Overview

| Feature | Apache Syncope | Evolveum midPoint | LTB ldap-toolbox |
|---|---|---|---|
| GitHub Stars | 326 | 485 | ~200 (multiple repos) |
| Primary Language | Java | Java | PHP |
| Last Updated | May 2026 | May 2026 | Active (multiple repos) |
| License | Apache 2.0 | Apache 2.0 | BSD 2-Clause |
| Architecture | REST API + Angular UI | Full IGA platform | Lightweight web tools |
| Connector Framework | Apache Syncope Connectors | ConnId-based | Direct LDAP binds |
| Workflow Engine | Built-in (Apache ODE) | Built-in (midPoint workflows) | None |
| Approval Workflows | ✅ Multi-level | ✅ Full RBAC | ❌ Basic |
| Audit & Compliance | ✅ Full audit trail | ✅ Comprehensive | ❌ Minimal |
| Self-Service Portal | ✅ | ✅ | ✅ (SSP) |
| Password Management | ✅ | ✅ | ✅ (best-in-class) |
| Docker Support | ✅ | ✅ | ✅ |

## Apache Syncope — Enterprise Identity Provisioning

Apache Syncope is an open-source provisioning system that synchronizes identities across multiple resources — LDAP directories, databases, cloud services, and REST APIs. It uses the ConnId connector framework (originally developed by Identity Connectors) to support a wide range of target systems. Syncope's REST API allows integration with any application, and its built-in workflow engine supports multi-level approval processes.

Key strengths:
- **Apache ecosystem** — mature governance under the Apache Software Foundation
- **REST-first architecture** — every operation available via API for automation
- **Connector framework** — ConnId supports LDAP, AD, database, REST, CSV, and more
- **Multi-tenancy** — supports multiple organizational domains from one instance
- **Workflow engine** — approval chains for provisioning requests

### Apache Syncope Docker Deployment

```yaml
services:
  syncope:
    image: apache/syncope:latest
    environment:
      - LOGIC_PROPERTIES_PATH=/opt/syncope/conf
      - SPRING_PROFILES_ACTIVE=embedded
      - ADMIN_USER=admin
      - ADMIN_PASSWORD=secure-password
    ports:
      - "9080:8080"
    depends_on:
      - syncope-db
    volumes:
      - syncope-conf:/opt/syncope/conf
    restart: unless-stopped

  syncope-db:
    image: postgres:16
    environment:
      - POSTGRES_DB=syncope
      - POSTGRES_USER=syncope
      - POSTGRES_PASSWORD=db-password
    volumes:
      - syncope-db-data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  syncope-conf:
  syncope-db-data:
```

## Evolveum midPoint — Full Identity Governance

Evolveum midPoint is a comprehensive identity governance and administration (IGA) platform. Unlike pure provisioning tools, midPoint handles the full identity lifecycle — from onboarding through role changes to offboarding — with policy enforcement, compliance reporting, and role mining. It uses an object-centric data model where identities, roles, organizations, and services are all first-class objects with relationships.

Key strengths:
- **Full IGA capabilities** — role mining, certification campaigns, policy enforcement
- **Object-centric model** — identities, roles, and resources as interconnected objects
- **Policy engine** — define and enforce complex access policies
- **Compliance reporting** — audit trails, attestation, and certification workflows
- **Active community** — commercial backing from Evolveum with strong open-source commitment

### midPoint Docker Deployment

```yaml
services:
  midpoint:
    image: evolveum/midpoint:latest
    environment:
      - JAVA_OPTS=-Xmx2g -Xms1g
    ports:
      - "8080:8080"
    depends_on:
      - midpoint-db
    volumes:
      - midpoint-config:/opt/midpoint/var
    restart: unless-stopped

  midpoint-db:
    image: postgres:16
    environment:
      - POSTGRES_DB=midpoint
      - POSTGRES_USER=midpoint
      - POSTGRES_PASSWORD=db-password
    volumes:
      - midpoint-db-data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  midpoint-config:
  midpoint-db-data:
```

## LTB ldap-toolbox — Lightweight LDAP Self-Service

LTB Project offers a suite of lightweight, purpose-built LDAP management tools rather than a single platform. The most popular components are:

- **Self-Service Password (SSP)** — password reset, change, and expiration notification
- **Self-Service User (SSU)** — user profile self-service portal
- **LDAP Tool Box Proxy** — LDAP proxy with access control and rate limiting
- **LdapSearch UI** — web-based LDAP browser and search tool

Each tool is a standalone PHP application that can be deployed independently. This modular approach is ideal for organizations that need specific LDAP management capabilities without deploying a full IGA platform.

Key strengths:
- **Lightweight** — each tool is a simple PHP application, no Java runtime needed
- **Modular** — deploy only what you need
- **Easy setup** — runs on any LAMP/LEMP stack
- **LDAP-specific** — purpose-built for LDAP directory management
- **Low resource footprint** — runs comfortably on a 1GB VM

### LTB Self-Service Password Docker Deployment

```yaml
services:
  ltb-ssp:
    image: tiredofit/ltb-self-service-password:latest
    environment:
      - LDAP_SERVER=ldap://ldap-server:389
      - LDAP_BINDDN=cn=admin,dc=example,dc=com
      - LDAP_BINDPASS=ldap-password
      - LDAP_BASE_SEARCH=dc=example,dc=com
      - PASSWORD_HASH=SSHA
      - MAIL_FROM=noreply@example.com
      - SMTP_HOST=smtp.example.com
      - SMTP_PORT=587
    ports:
      - "8080:80"
    restart: unless-stopped
```

## Comparison Matrix

| Capability | Apache Syncope | midPoint | LTB ldap-toolbox |
|---|---|---|---|
| Identity provisioning | ✅ Multi-resource | ✅ Full lifecycle | ❌ Manual only |
| Role-based access control | ✅ | ✅ Full RBAC | ❌ |
| Approval workflows | ✅ Multi-level | ✅ Complex | ❌ |
| Password self-service | ✅ | ✅ | ✅ Best-in-class |
| LDAP directory browser | ❌ | ✅ | ✅ (LdapSearch UI) |
| Compliance reporting | ✅ | ✅ Comprehensive | ❌ |
| Role mining | ❌ | ✅ | ❌ |
| Certification campaigns | ❌ | ✅ | ❌ |
| REST API | ✅ Full | ✅ Full | ❌ |
| Active Directory sync | ✅ | ✅ | ✅ (direct bind) |
| Resource footprint | High (Java, ~2GB RAM) | High (Java, ~2GB RAM) | Low (PHP, ~256MB) |
| Best for | Medium-large orgs | Enterprise IGA | Small orgs / specific needs |

## Choosing the Right Tool

| Scenario | Recommended Tool | Reason |
|---|---|---|
| Need full IGA with compliance | midPoint | Only open-source tool with role mining, certification, and audit |
| Multi-system provisioning automation | Apache Syncope | REST API + connector framework for any target system |
| Simple password reset for LDAP users | LTB SSP | Lightweight, purpose-built, 5-minute setup |
| Enterprise-scale identity lifecycle | midPoint | Full governance, policy engine, attestation workflows |
| Integration-heavy environment | Apache Syncope | ConnId connectors for 30+ resource types |
| Minimal infrastructure overhead | LTB ldap-toolbox | PHP apps run on any web server, no Java needed |

## Why Self-Host Identity Management?

Identity is the new perimeter. Every user account, service principal, and API credential is a potential attack vector. Commercial identity governance platforms charge per-identity licensing that makes them cost-prohibitive for organizations with large user bases — contractors, service accounts, and IoT device identities can easily push counts into the tens of thousands.

Self-hosted open-source identity platforms eliminate per-user licensing while giving you full control over your identity data, approval workflows, and audit trails. For regulated organizations, keeping identity governance on-premises ensures that user access patterns, role assignments, and compliance reports never leave your infrastructure.

For directory server infrastructure, see our [LDAP server comparison](../self-hosted-ldap-directory-servers-openldap-389ds-freeipa-guide-2026/) and [lightweight LDAP guide](../2026-04-24-lldap-vs-glauth-lightweight-ldap-self-hosted-auth-guide/). For broader identity management, our [SSO provider comparison](../2026-04-27-simplesamlphp-vs-shibboleth-vs-apereo-cas-self-hosted-saml-idp-guide-2026/) covers SAML identity providers.

## FAQ

### What is the difference between identity provisioning and identity governance?

Identity provisioning is about creating, modifying, and deleting user accounts across systems — the mechanical act of synchronizing identity data. Identity governance encompasses provisioning but adds policy enforcement, role management, compliance reporting, and approval workflows. Apache Syncope focuses on provisioning; midPoint covers both provisioning and governance; LTB ldap-toolbox handles specific LDAP management tasks.

### Can these tools sync with Active Directory?

Yes, all three support Active Directory synchronization. Apache Syncope uses its ConnId AD connector for bidirectional sync. midPoint has native AD connector support with attribute mapping and password synchronization. LTB ldap-toolbox connects to AD via standard LDAP binds for password reset and self-service operations.

### Do I need a separate LDAP server for these tools?

These tools connect to existing LDAP directories — they are not LDAP servers themselves. You need an LDAP directory (OpenLDAP, 389 Directory Server, FreeIPA, or Active Directory) as the identity store. The tools manage, synchronize, and provide self-service access to that directory.

### How does midPoint's role mining work?

Role mining analyzes existing user-to-resource assignments to discover patterns and suggest role definitions. For example, if 50 users all have access to the same 5 systems, midPoint suggests creating a role that grants those 5 access rights. This eliminates manual role design and helps discover "access creep" — permissions accumulated over time that no longer match the user's current responsibilities.

### What is the resource requirement for midPoint?

midPoint requires a Java runtime with at least 2GB heap allocation and a PostgreSQL database. A production deployment should have 4GB+ RAM, 2 CPU cores, and 20GB disk. Apache Syncope has similar requirements. LTB ldap-toolbox components are lightweight PHP applications that run on any web server with less than 256MB RAM.

### Can I use these tools without a dedicated IT team?

LTB ldap-toolbox is designed for small teams — each component is a standalone PHP application with simple configuration. Apache Syncope and midPoint require more expertise to deploy and configure properly, as they involve Java application servers, databases, and connector configuration. For organizations without dedicated IAM engineers, starting with LTB tools is recommended.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Apache Syncope vs midPoint vs LTB ldap-toolbox: Self-Hosted Identity Synchronization Guide 2026",
  "description": "Compare three open-source identity synchronization platforms for self-hosted directory synchronization, identity governance, and user provisioning.",
  "datePublished": "2026-05-04",
  "dateModified": "2026-05-04",
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