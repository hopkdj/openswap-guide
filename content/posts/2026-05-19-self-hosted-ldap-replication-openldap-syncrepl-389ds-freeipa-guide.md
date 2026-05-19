---
title: "Self-Hosted LDAP Replication: OpenLDAP Syncrepl vs 389 DS vs FreeIPA (2026)"
date: "2026-05-19"
tags: ["ldap", "directory-services", "replication", "openldap", "389-ds", "freeipa", "self-hosted", "identity-management"]
draft: false
---

LDAP replication is the backbone of high-availability directory services. When your authentication infrastructure spans multiple data centers or geographic regions, keeping directory data synchronized becomes critical. This guide compares three leading approaches to LDAP replication: OpenLDAP's Syncrepl, 389 Directory Server's Multi-Master replication, and FreeIPA's topology-based replication.

## Understanding LDAP Replication Topologies

Before diving into specific implementations, it helps to understand the common replication patterns used in production environments.

**Single-Master (Hub-and-Spoke)**: One provider server accepts all writes, and consumers receive updates. Simple to manage but introduces a single point of failure for write operations.

**Multi-Master (N-Way)**: Every server accepts writes and propagates changes to all others. Provides full redundancy but requires conflict resolution mechanisms.

**Cascade Replication**: A consumer of one provider also acts as a provider for downstream consumers. Useful for geographically distributed deployments with limited bandwidth.

**Hybrid Topologies**: Combining single-master within a data center and multi-master across data centers. This is the most common production pattern for enterprise deployments.

## OpenLDAP Syncrepl

OpenLDAP's Syncrepl (Synchronous Replication) is the most widely deployed LDAP replication mechanism. It uses a consumer-pull model where replica servers periodically poll the provider for changes using the LDAP Content Synchronization protocol (RFC 4533).

### Architecture

Syncrepl operates at the entry level — each modification creates a change log entry with a unique ContextCSN (Context Change Sequence Number). Consumers track their last-synced CSN and request all changes since that point. The provider stores changes in its own database, so there is no separate change log to manage.

### Key Features

- **Delta-Sync Mode**: Only transfers changes since last sync, not the entire database
- **Refresh-and-Persist**: Initial full sync followed by continuous change streaming
- **Mirror Mode**: Two servers replicate bidirectionally, creating an active-active pair
- **Config Replication**: The `olc` (On-Line Configuration) database can be replicated separately from user data

### Deployment with Docker Compose

```yaml
version: "3.8"
services:
  openldap-primary:
    image: osixia/openldap:1.5.0
    container_name: openldap-primary
    environment:
      LDAP_ORGANISATION: "Example Corp"
      LDAP_DOMAIN: "example.com"
      LDAP_ADMIN_PASSWORD: "admin-secret"
      LDAP_REPLICATION: "true"
      LDAP_REPLICATION_HOSTS: "#PYTHON2BASH:['ldap://openldap-primary','ldap://openldap-replica']"
    ports:
      - "389:389"
      - "636:636"
    volumes:
      - primary-data:/var/lib/ldap
      - primary-config:/etc/ldap/slapd.d
    networks:
      - ldap-net

  openldap-replica:
    image: osixia/openldap:1.5.0
    container_name: openldap-replica
    environment:
      LDAP_ORGANISATION: "Example Corp"
      LDAP_DOMAIN: "example.com"
      LDAP_ADMIN_PASSWORD: "admin-secret"
      LDAP_REPLICATION: "true"
      LDAP_REPLICATION_HOSTS: "#PYTHON2BASH:['ldap://openldap-primary','ldap://openldap-replica']"
    ports:
      - "1389:389"
      - "1636:636"
    volumes:
      - replica-data:/var/lib/ldap
      - replica-config:/etc/ldap/slapd.d
    networks:
      - ldap-net

volumes:
  primary-data:
  primary-config:
  replica-data:
  replica-config:

networks:
  ldap-net:
    driver: bridge
```

### N-Way Multi-Master Configuration

For true multi-master replication, add `syncrepl` directives to both servers' `slapd.conf`:

```
syncrepl rid=001
  provider=ldap://ldap2.example.com
  bindmethod=simple
  binddn="cn=admin,dc=example,dc=com"
  credentials=admin-secret
  searchbase="dc=example,dc=com"
  type=refreshAndPersist
  retry="60 +"
  schemachecking=on

mirrormode TRUE
overlay syncprov
syncprov-checkpoint 100 10
```

The `syncprov` overlay is essential — it maintains the session log that enables delta-syncs. The `mirrormode TRUE` directive enables both servers to accept writes.

### Strengths and Limitations

OpenLDAP Syncrepl excels in flexibility and maturity. It supports virtually any replication topology, handles large directories efficiently through delta-syncs, and has been production-tested for over two decades. The `syncrepl` configuration is well-documented and understood by most LDAP administrators.

However, conflict resolution in multi-master setups is limited to "last writer wins" based on timestamp. If two servers modify the same entry simultaneously, one change silently overwrites the other. Additionally, the provider-stores-changes approach means deleted entries can cause issues if the change log depth is insufficient.

## 389 Directory Server Multi-Master Replication

389 Directory Server (formerly Fedora Directory Server, maintained by the 389ds project) implements a true multi-master replication model with a dedicated changelog. Unlike OpenLDAP's consumer-pull approach, 389 DS uses a combination of push and pull mechanisms.

### Architecture

389 DS maintains a separate changelog database that records all modifications with unique Change Sequence Numbers (CSNs). Each replica tracks the CSN it has received from every other replica in the topology. The changelog is separate from the main database, making it easier to manage replication state independently.

### Key Features

- **True Multi-Master**: All servers accept writes simultaneously
- **Fractional Replication**: Replicate only specific attributes, useful for filtering sensitive data
- **Initialization from Backup**: New replicas can be initialized from a backup rather than a full live sync
- **Changelog Trimming**: Automatic cleanup of old changelog entries based on age or size
- **Conflict Resolution**: Timestamp-based with automatic conflict detection and logging

### Deployment with Docker Compose

```yaml
version: "3.8"
services:
  ds389-node1:
    image: 389ds/dirsrv:latest
    container_name: ds389-node1
    environment:
      DS_DM_PASSWORD: "directory-manager"
      DS_SUFFIX_NAME: "dc=example,dc=com"
      DS_HOSTNAME: "ds389-node1"
    ports:
      - "3389:3389"
      - "3636:3636"
    volumes:
      - node1-data:/data
    networks:
      - ds-net

  ds389-node2:
    image: 389ds/dirsrv:latest
    container_name: ds389-node2
    environment:
      DS_DM_PASSWORD: "directory-manager"
      DS_SUFFIX_NAME: "dc=example,dc=com"
      DS_HOSTNAME: "ds389-node2"
    ports:
      - "4389:3389"
      - "4636:3636"
    volumes:
      - node2-data:/data
    networks:
      - ds-net

volumes:
  node1-data:
  node2-data:

networks:
  ds-net:
    driver: bridge
```

After deployment, configure replication using `dsconf`:

```bash
# On node1: create replication agreement
dsconf -D "cn=Directory Manager" ldap://ds389-node1:3389   repl-agmt create --host="ds389-node2" --port=3389   --conn-protocol=LDAP --bind-mech=SIMPLE   --bind-dn="cn=replication manager,cn=config"   --bind-passwd="repl-secret"   "dc=example,dc=com"

# Enable chaining for multi-master
dsconf -D "cn=Directory Manager" ldap://ds389-node1:3389   plugin enable "Multi-Master Replication Plugin"
```

### Strengths and Limitations

389 DS provides more sophisticated conflict resolution than OpenLDAP, including the ability to log conflicts for manual review. The fractional replication feature is particularly valuable for compliance scenarios where certain attributes (like salary or SSN) should not leave specific data centers. The dedicated changelog makes it easier to diagnose replication issues.

The main limitation is operational complexity — managing the changelog requires careful tuning of its size and retention period. If the changelog fills up before a replica catches up, that replica requires re-initialization. Additionally, 389 DS has a smaller community than OpenLDAP, which means fewer third-party tools and less community support.

## FreeIPA Replication Topology

FreeIPA (Identity, Policy, Audit) builds on 389 Directory Server but adds a higher-level abstraction for replication management. FreeIPA uses its own topology plugin that automatically manages replication agreements between all servers in the topology.

### Architecture

FreeIPA creates a mesh topology by default, where every server replicates with every other server. The topology plugin automatically creates and manages replication agreements. When you add a new server to the domain, FreeIPA automatically configures it to replicate with at least two existing servers for redundancy.

FreeIPA replicates multiple data domains: the directory data (user accounts, groups), DNS zones, certificate authority (Dogtag PKI), and Kerberos keys. This integrated approach ensures that all identity-related data stays synchronized.

### Key Features

- **Automatic Topology Management**: FreeIPA handles replication agreement creation automatically
- **Integrated DNS Replication**: DNS zones replicate alongside directory data
- **CA Replication**: Dogtag PKI certificate data replicates across all servers
- **Topology Segments**: Group servers into segments for controlled replication flow
- **Conflict Resolution**: Inherits 389 DS conflict handling with FreeIPA-specific enhancements

### Deployment with Docker Compose

```yaml
version: "3.8"
services:
  ipa-server1:
    image: freeipa/freeipa-server:rocky-9
    container_name: ipa-server1
    hostname: ipa1.example.com
    environment:
      PASSWORD: "Secret123"
      IPA_SERVER_HOSTNAME: "ipa1.example.com"
      IPA_SERVER_INSTALL_OPTS: "--setup-dns --no-forwarders --no-ntp"
    ports:
      - "80:80"
      - "443:443"
      - "389:389"
      - "636:636"
      - "88:88"
      - "464:464"
      - "53:53/udp"
      - "53:53/tcp"
    volumes:
      - ipa1-data:/data:Z
    tmpfs:
      - /run
      - /tmp
    cap_add:
      - SYS_ADMIN
    networks:
      ipa-net:
        ipv4_address: 172.20.0.10

  ipa-server2:
    image: freeipa/freeipa-server:rocky-9
    container_name: ipa-server2
    hostname: ipa2.example.com
    environment:
      PASSWORD: "Secret123"
      IPA_SERVER_HOSTNAME: "ipa2.example.com"
      IPA_SERVER_INSTALL_OPTS: "--setup-dns --no-forwarders --no-ntp --ip-address=172.20.0.11"
    ports:
      - "1080:80"
      - "1443:443"
      - "1389:389"
      - "1636:636"
      - "1088:88"
      - "1464:464"
      - "1053:53/udp"
      - "1053:53/tcp"
    volumes:
      - ipa2-data:/data:Z
    tmpfs:
      - /run
      - /tmp
    cap_add:
      - SYS_ADMIN
    networks:
      ipa-net:
        ipv4_address: 172.20.0.11

volumes:
  ipa1-data:
  ipa2-data:

networks:
  ipa-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

After the second server joins the domain, verify the replication topology:

```bash
# Check replication status on server1
ipa-replica-manage list

# Verify agreement status
ds-replcheck -D "cn=Directory Manager"   -w Secret123   ldap://ipa1.example.com ldap://ipa2.example.com

# View topology segments
ipa topologysegment-find
```

### Strengths and Limitations

FreeIPA provides the most turnkey LDAP replication experience. The automatic topology management eliminates the manual configuration required by OpenLDAP and 389 DS. The integrated DNS and CA replication means you get a complete identity infrastructure with synchronized components.

The trade-off is reduced flexibility — FreeIPA enforces specific topologies and doesn't support arbitrary replication configurations like OpenLDAP's cascade or filtered replication patterns. FreeIPA also has higher resource requirements due to the additional services (DNS, CA, Kerberos) running alongside the directory server.

## Choosing the Right LDAP Replication Solution

| Feature | OpenLDAP Syncrepl | 389 DS Multi-Master | FreeIPA Topology |
|---------|-------------------|---------------------|------------------|
| Replication Model | Consumer-pull (Syncrepl) | Multi-master push/pull | Multi-master mesh |
| Conflict Resolution | Last-writer-wins | Timestamp + logging | Timestamp + FreeIPA rules |
| Fractional Replication | No | Yes | No |
| Automatic Topology | No | Manual segments | Yes (built-in) |
| DNS Replication | No | No | Yes (integrated) |
| CA Replication | No | No | Yes (Dogtag PKI) |
| Configuration Complexity | High | Medium | Low |
| Community Size | Very large | Moderate | Growing |
| GitHub Stars | 581 | 285 | 1,230 |
| Best For | Custom topologies, filtering | Enterprise multi-master | Turnkey identity platform |

### When to Use OpenLDAP Syncrepl

Choose OpenLDAP when you need maximum flexibility in replication topology — cascade configurations, filtered replication of specific subtrees, or integration with non-LDAP data sources. It's also the right choice when you have experienced LDAP administrators who can tune and troubleshoot `syncrepl` configurations.

### When to Use 389 DS Multi-Master

Choose 389 DS when you need true multi-master with sophisticated conflict handling and fractional replication. The ability to replicate only certain attributes makes it ideal for compliance-driven architectures where data sovereignty requirements vary by region.

### When to Use FreeIPA

Choose FreeIPA when you want a complete identity platform with replication managed out of the box. If you need synchronized DNS, Kerberos, and certificate management alongside your directory data, FreeIPA eliminates the integration work required with standalone LDAP servers.

## Why Self-Host LDAP Replication?

Running your own LDAP replication infrastructure gives you complete control over identity data. Unlike cloud-based directory services, self-hosted LDAP keeps authentication data within your network perimeter, eliminating the risk of third-party breaches or service outages affecting your entire authentication pipeline.

For organizations with regulatory requirements around data residency — GDPR, HIPAA, or financial sector mandates — self-hosted LDAP ensures user credentials and identity attributes never leave your controlled infrastructure. Replication across multiple data centers provides disaster recovery capabilities without depending on external providers.

The cost savings are substantial at scale. Cloud directory services charge per-user, per-month fees that compound quickly for organizations with thousands of employees. A self-hosted LDAP infrastructure with multi-master replication across three data centers costs primarily in compute and bandwidth, with no per-user licensing fees.

For network infrastructure management, see our [LDAP proxy solutions guide](../2026-05-14-self-hosted-ldap-proxy-solutions-ldapx-privacyidea-kanidm-guide/). If you need lightweight LDAP alternatives, check our [lLDAP vs GLAuth comparison](../2026-04-24-lldap-vs-glauth-lightweight-ldap-self-hosted-auth-guide/). For identity synchronization across systems, our [Apache Syncope guide](../2026-05-04-apache-syncope-vs-midpoint-vs-ltb-ldap-toolbox-self-hosted-identity-sync-guide/) covers the options.

## Frequently Asked Questions

### What is the difference between Syncrepl and Multi-Master replication?

Syncrepl uses a consumer-pull model where replica servers request changes from a provider. Multi-Master allows all servers to accept writes and propagate changes to peers. Syncrepl is simpler to configure but has a single write point; multi-master provides full redundancy but requires conflict resolution.

### How do I handle replication conflicts in multi-master LDAP?

Both 389 DS and FreeIPA use timestamp-based conflict resolution — the most recent write wins. For OpenLDAP, there is no built-in conflict resolution in standard Syncrepl; Mirror Mode uses last-writer-wins. If conflicts are a concern, design your topology so that different organizational units are written to by different servers.

### Can I replicate only part of my LDAP directory?

OpenLDAP supports subtree-level filtering in its `syncrepl` configuration using the `filter` parameter. 389 DS supports fractional replication, where specific attributes can be excluded from replication. FreeIPA does not support partial replication — the entire directory replicates across all servers.

### How often should replication occur?

With `refreshAndPersist` mode (OpenLDAP) or persistent replication agreements (389 DS, FreeIPA), changes propagate in near real-time — typically within seconds. The `refreshOnly` mode in OpenLDAP allows you to set explicit polling intervals (e.g., every 60 seconds), but this is rarely used in modern deployments.

### What happens when a replica falls behind?

If a replica's CSN falls behind the provider's changelog retention window, it must be re-initialized with a full database copy. In OpenLDAP, this means a complete re-sync. In 389 DS, you can initialize from a backup file, which is faster than a live sync for large directories. FreeIPA handles re-initialization automatically through its topology plugin.

### Can I mix different LDAP servers in a replication topology?

Generally no. OpenLDAP, 389 DS, and FreeIPA use different replication protocols and data formats. While FreeIPA uses 389 DS underneath, its topology management is FreeIPA-specific. However, you can use identity synchronization tools (like Apache Syncope) to sync data between different directory types.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted LDAP Replication: OpenLDAP Syncrepl vs 389 DS vs FreeIPA (2026)",
  "description": "Compare LDAP replication approaches: OpenLDAP Syncrepl consumer-pull, 389 Directory Server multi-master, and FreeIPA topology-based replication with Docker deployment examples.",
  "datePublished": "2026-05-19",
  "dateModified": "2026-05-19",
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
